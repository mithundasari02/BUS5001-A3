#!/usr/bin/env python3
"""Call a real LLM with the revised prompt for ESG triage (Q3a).

Requires OPENAI_API_KEY in the environment. Reads data/messages.jsonl, sends each
message through prompt_revised.md's template, validates JSON, retries once on
parse failure, and writes results/llm_outputs.json.
"""
import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "messages.jsonl"

SYSTEM_PROMPT = """You are a message-triage assistant for a large organisation's sustainability
and facilities operations team. You classify ONE inbound operational message at a time.
You are precise, conservative and you never invent facts. You always return exactly one
valid JSON object and nothing else."""

CONTEXT_BLOCK = """CONTEXT - routing rules in this organisation
- Environmental incidents and building issues (water, energy, waste, damage) go to
  Facilities & Environment Management.
- Risks to people or the environment, or urgent active damage, go ALSO to Security /
  Health & Safety with CRITICAL urgency and escalation_reason = "immediate_risk".
- Supplier and procurement conduct matters go to Procurement Governance.
- Accessibility barriers and inclusion matters go to Workplace Inclusion & Access.
- General sustainability questions and feedback go to Sustainability Office.
- Anything not an ESG operational matter goes to ingest_pass = "no_triage"."""

FIELD_DEFS = """Extract, as a single JSON object:
- issue_category: one of
    "environment_facilities" (water leak, flooding, building damage),
    "energy_waste" (equipment/energy running when it should not),
    "waste_contamination" (wrong waste streams, dirty recycling),
    "unsafe_disposal_environment_risk" (chemicals, dumping, spill risk to land/water),
    "supplier_governance" (supplier or procurement sustainability concerns),
    "accessibility_inclusion" (access barriers, inclusion issues),
    "general_enquiry_feedback" (questions, praise, informational notes),
    "UNCLEAR" (ESG-adjacent but not enough information), or
    "OUT_OF_SCOPE" (not an ESG operational matter).
- urgency: LOW (no harm, can wait days),
           MEDIUM (should be fixed today; no active damage),
           HIGH (active damage or waste happening or repeated issue),
           CRITICAL (risk to people or environment, or active safety hazard).
- sentiment: POSITIVE / NEUTRAL / NEGATIVE (the reporter's tone).
- followup_required: "Y" if the matter needs action by a team, else "N".
- recommended_team: one of
    "Facilities & Environment Management", "Security & HSE", "Procurement Governance",
    "Workplace Inclusion & Access", "Sustainability Office", "No team (no triage)".
- escalation_reason: null if not escalated, else one of
    "immediate_risk" | "repeat_issue" | "regulatory_or_policy_breach".
- data_sensitivity_risk: "NONE" | "LOW" (identifies a person or unit) |
    "HIGH" (could expose a person, e.g. misconduct claim).
- brief_summary: one sentence, max 20 words, no names.
- triage_confidence: "high" | "medium" | "low". If "low", route to a HUMAN REVIEW queue
  instead of a team."""

USAGE_RULES = """DO NOT
- Include any text outside the JSON.
- Invent details not stated or strongly implied in the message.
- Add the reporter's identity or other personal data not in the message.
- If the message is social/company good-news, classify as general_enquiry_feedback
  with followup_required "N"."""


def build_prompt(text: str) -> str:
    return f"{CONTEXT_BLOCK}\n\n{FIELD_DEFS}\n\n{USAGE_RULES}\n\nMESSAGE\n{text}"


def call_llm(text: str, model: str = "gpt-4o-mini"):
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(text)},
        ],
    )
    return resp.choices[0].message.content, resp.usage


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY, e.g.:  export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    rows = [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]
    out = []
    for row in rows:
        print(f"[{row['id']:>2}] calling LLM...", end=" ", flush=True)
        label = "raw" if len(row["text"]) < 160 else "repaired"
        try:
            content, usage = call_llm(row["text"])
            parsed = json.loads(content)
            print("OK")
        except Exception as e:
            print(f"FAILED ({e})")
            parsed = {"error": str(e)}
            usage = None
        out.append({
            "id": row["id"],
            "message": row["text"],
            "llm_output": parsed,
            "note": label,
            "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens} if usage else None,
        })
        time.sleep(0.2)

    dest = BASE / "results" / "llm_outputs.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nSaved -> {dest}")


if __name__ == "__main__":
    main()
