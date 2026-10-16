#!/usr/bin/env python3
"""Rule-based baseline classifier for ESG message triage (Q3b).

Deliberately simple, transparent keywords/regex rules -> issue_category, urgency,
escalation, team. Serves as the comparison baseline against the LLM outputs.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "messages.jsonl"

RULES = [
    ("unsafe_disposal_environment_risk", r"chemical|solvent|drum|dump|spill|creek|drain|toxic"),
    ("water",                            r"water leak|leak|flood|dripp|tap"),
    ("energy_waste",                     r"air conditioning|heating|lights? (on|stay)|overnight|energy"),
    ("waste_contamination",              r"recycl|bin|contaminat|waste"),
    ("supplier_governance",              r"supplier|procure|vendor|policy breach"),
    ("accessibility_inclusion",          r"accessib|entrance blocked|access blocked|inclusive|barrier for"),
    ("general_enquiry_feedback",         r"where can|question|great job|keep it up|thanks|policy for catering"),
]

URGENT_WORDS = r"safety risk|fire hazard|slippery|electrical|immediately|running all (morning|night)|dumped behind"

TEAMS = {
    "unsafe_disposal_environment_risk": "Security & HSE",
    "water":                            "Facilities & Environment Management",
    "energy_waste":                     "Facilities & Environment Management",
    "waste_contamination":              "Facilities & Environment Management",
    "supplier_governance":              "Procurement Governance",
    "accessibility_inclusion":          "Workplace Inclusion & Access",
    "general_enquiry_feedback":         "Sustainability Office",
}


def classify(text: str) -> dict:
    low = text.lower()
    cat = "UNCLEAR"
    for name, pattern in RULES:
        if re.search(pattern, low):
            cat = name
            break

    urgent = bool(re.search(URGENT_WORDS, low))
    if urgent:
        urgency = "CRITICAL" if cat in ("unsafe_disposal_environment_risk",) else "HIGH"
        escalation = "immediate_risk"
        followup = "Y"
    elif cat in ("UNCLEAR", "general_enquiry_feedback"):
        urgency = "LOW"
        escalation = None
        followup = "N"
    else:
        urgency = "MEDIUM"
        escalation = None
        followup = "Y"

    sentiment = "POSITIVE" if re.search(r"great|keep it up|thanks|good", low) else "NEGATIVE" if re.search(r"leak|contaminat|damage|blocked|waste|dump", low) else "NEUTRAL"

    return {
        "issue_category": cat,
        "urgency": urgency,
        "sentiment": sentiment,
        "followup_required": followup,
        "recommended_team": TEAMS.get(cat, "Sustainability Office"),
        "escalation_reason": escalation,
        "data_sensitivity_risk": "NONE",
        "brief_summary": text[:80],
        "triage_confidence": "high" if cat != "UNCLEAR" else "low",
    }


def main() -> None:
    out = []
    for line in DATA.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.append({"id": row["id"], "message": row["text"], **classify(row["text"])})
    dest = Path(__file__).resolve().parents[1] / "results" / "baseline_rule_based.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"Wrote {len(out)} classified rows -> {dest}")


if __name__ == "__main__":
    main()
