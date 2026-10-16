#!/usr/bin/env python3
"""Zero-shot LLM-free baseline classifier for ESG message triage (Q3b).

Uses Hugging Face zero-shot classification (facebook/bart-large-mnli) to predict
issue_category and (separately) urgency. Produces the same schema as the LLM
output for direct comparison. THIS IS THE GENUINE MODEL RUN - execute it to
regenerate results/zero_shot_baseline.json.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "messages.jsonl"

LABELS = [
    "environment_facilities",
    "energy_waste",
    "waste_contamination",
    "unsafe_disposal_environment_risk",
    "supplier_governance",
    "accessibility_inclusion",
    "general_enquiry_feedback",
]

HYPOTHESES = {
    "environment_facilities": "a building facilities issue such as a water leak, flooding or damage",
    "energy_waste": "energy is being wasted, such as lights or air conditioning running unnecessarily",
    "waste_contamination": "waste or recycling bins are contaminated or misused",
    "unsafe_disposal_environment_risk": "hazardous material was dumped or spilled, creating environmental or safety risk",
    "supplier_governance": "a supplier or procurement practice may breach sustainability policy",
    "accessibility_inclusion": "an accessibility barrier or inclusion issue is reported",
    "general_enquiry_feedback": "a general question, piece of feedback or informational note",
}

URGENT_HYPS = {
    "LOW": "this is a routine matter that can wait several days",
    "MEDIUM": "this should be fixed today but no active damage is occurring",
    "HIGH": "active damage or repeated waste is happening now",
    "CRITICAL": "people or the environment are at immediate risk right now",
}


def main() -> None:
    from transformers import pipeline

    clf = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    out = []
    for line in DATA.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cat = clf(row["text"], candidate_labels=LABELS, hypothesis_template="This message reports {}.")
        urg = clf(row["text"], candidate_labels=list(URGENT_HYPS),
                  hypothesis_template="Regarding urgency: {}.")
        # urgency pipeline: pick the label whose hypothesis best matches
        urg_scores = dict(zip(urg["labels"], urg["scores"]))
        urgency = max(urg_scores, key=urg_scores.get)
        cat_top = cat["labels"][0]

        out.append({
            "id": row["id"],
            "message": row["text"],
            "issue_category": cat_top,
            "issue_confidence": round(cat["scores"][0], 3),
            "top3": [{"label": l, "score": round(s, 3)} for l, s in zip(cat["labels"], cat["scores"])],
            "urgency": urgency,
            "urgency_scores": {k: round(v, 3) for k, v in urg_scores.items()},
        })
        print(f"[{row['id']:>2}] {cat_top} ({cat['scores'][0]:.2f}) / urgency {urgency} ({urg_scores[urgency]:.2f})")

    dest = Path(__file__).resolve().parents[1] / "results" / "zero_shot_baseline.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nSaved {len(out)} rows -> {dest}")


if __name__ == "__main__":
    main()
