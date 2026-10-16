#!/usr/bin/env python3
"""Local open-source LLM triage run for Q3(a) — no API key required.

Runs Qwen2.5-1.5B-Instruct (CPU, transformers) against the full revised prompt
from prompt_revised.md for all 10 ESG messages. Temperature 0 (greedy), JSON
validation, one repair-retry, writes results/local_llm_outputs.json, plus a
detailed generation log (results/local_llm_run.log) for evidence.
"""
import json
import time
import re
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "messages.jsonl"
RESULTS = BASE / "results"

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

SYSTEM_PROMPT = (
    "You are a message-triage assistant for a large organisation's sustainability and "
    "facilities operations team. You classify ONE inbound operational message at a time. "
    "You are precise, conservative and you never invent facts. You always return exactly "
    "one valid JSON object and nothing else."
)

CONTEXT_BLOCK = """CONTEXT - routing rules in this organisation
- Environmental incidents and building issues (water, energy, waste, damage) go to Facilities & Environment Management.
- Risks to people or the environment, or urgent active damage, go ALSO to Security & HSE with CRITICAL urgency and escalation_reason = "immediate_risk".
- Supplier and procurement conduct matters go to Procurement Governance.
- Accessibility barriers and inclusion matters go to Workplace Inclusion & Access.
- General sustainability questions and feedback go to Sustainability Office.
- Anything not an ESG operational matter is NOT classified: output issue_category "OUT_OF_SCOPE" instead."""

FIELD_DEFS = """Extract, as a single JSON object:
- issue_category: one of
    "environment_facilities" (water leak, flooding, building damage),
    "energy_waste" (equipment/energy running when it should not),
    "waste_contamination" (wrong waste streams, dirty recycling),
    "unsafe_disposal_environment_risk" (chemicals, dumping, spill risk to land/water),
    "supplier_governance" (supplier or procurement sustainability concerns),
    "accessibility_inclusion" (access barriers, inclusion issues),
    "general_enquiry_feedback" (questions, praise, informational notes), or
    "OUT_OF_SCOPE" (not an ESG operational matter).
- urgency: LOW (no harm, can wait days),
           MEDIUM (should be fixed today; no active damage),
           HIGH (active damage or waste happening or will repeat),
           CRITICAL (risk to people or environment, or active safety hazard).
- sentiment: POSITIVE / NEUTRAL / NEGATIVE (the reporter's tone).
- followup_required: "Y" if the matter needs action by a team, else "N".
- recommended_team: one of
    "Facilities & Environment Management", "Security & HSE", "Procurement Governance",
    "Workplace Inclusion & Access", "Sustainability Office".
- escalation_reason: null if not escalated, else "immediate_risk" | "repeat_issue" | "regulatory_or_policy_breach".
- data_sensitivity_risk: "NONE" | "LOW" | "HIGH".
- brief_summary: one sentence, max 20 words, no names.
- triage_confidence: "high" | "medium" | "low"."""

USAGE_RULES = """DO NOT
- Include any text outside the JSON.
- Invent details not stated or strongly implied in the message.
- Add the reporter's identity or other personal data not in the message.
- If the message is social/company good-news, classify as general_enquiry_feedback with followup_required "N"."""


def build_prompt(text: str) -> str:
    return f"{CONTEXT_BLOCK}\n\n{FIELD_DEFS}\n\n{USAGE_RULES}\n\nMESSAGE\n{text}"


def extract_json(raw: str):
    """Parse a JSON object leniently: finds the outermost {...} block."""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("no JSON object found in model output")
    return json.loads(m.group(0))


def main() -> None:
    t_start = time.time()
    log_lines = [f"Local LLM run — {MODEL_ID} on CPU (torch {torch.__version__}, temperature 0 / greedy)",
                 "=" * 70]
    print(f"Loading {MODEL_ID} ...", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=torch.float32)
    model.eval()

    rows = [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]
    out = []
    for row in rows:
        t1 = time.time()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(row["text"])},
        ]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok([text], return_tensors="pt")
        with torch.no_grad():
            out_ids = model.generate(**inputs, max_new_tokens=220, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
        resp = tok.decode(out_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

        # validation + one repair-retry
        parsed, note = None, "ok"
        try:
            parsed = extract_json(resp)
        except Exception as e:
            note = f"parse failed ({e}); retrying"
            log_lines.append(f"[{row['id']}] {note}")
            messages[1]["content"] += "\n\nIMPORTANT: Output ONLY valid JSON. No prose, no markdown fences."
            text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tok([text], return_tensors="pt")
            with torch.no_grad():
                out_ids = model.generate(**inputs, max_new_tokens=220, do_sample=False,
                                         pad_token_id=tok.eos_token_id)
            resp = tok.decode(out_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            try:
                parsed = extract_json(resp)
                note = "repaired"
            except Exception as e2:
                note = f"failed-both-attempts: {e2}"
                parsed = {"error": str(e2)}

        dt = time.time() - t1
        out.append({
            "id": row["id"],
            "message": row["text"],
            "llm_output": parsed,
            "raw_response": resp,
            "note": note,
            "gen_seconds": round(dt, 1),
        })
        log_lines.append(f"\n[{row['id']}] ({dt:.0f}s) {note}\nPROMPT: {build_prompt(row['text'])[:200]}...\nRAW: {resp}\nPARSED: {json.dumps(parsed)}")
        print(f"[{row['id']:>2}] {dt:5.1f}s {note} -> {json.dumps(parsed)[:90]}", flush=True)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "local_llm_outputs.json").write_text(json.dumps(out, indent=2))
    log_lines.append(f"\nTotal wall time: {(time.time()-t_start)/60:.1f} min")
    (RESULTS / "local_llm_run.log").write_text("\n".join(log_lines))
    print(f"\nDone in {(time.time()-t_start)/60:.1f} min. Wrote results/local_llm_outputs.json and local_llm_run.log")


if __name__ == "__main__":
    main()
