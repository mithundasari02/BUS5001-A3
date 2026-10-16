# Q4 — Live session evidence log & screenshot plan

Execute in one sitting (~45–60 min) with the 4 test sources loaded.

## Source loading

| # | Source | Format | Notes |
|---|---|---|---|
| 1 | La Trobe Environmental Sustainability Policy | PDF (public web copy) | university policy |
| 2 | GRI Universal Standards excerpts | PDF (gri.org) | standards doc |
| 3 | ASX-listed company FY2025 sustainability report | PDF | disclosure-style doc |
| 4 | Course lecture notes — "Cloud analytics for ESG" | PDF (own slides) | teaching material |

## Live demo executions

| Demo | Feature to exercise | Prompt / click | Screenshot to save |
|---|---|---|---|
| D1 | Grounded Q&A with citations | "Under the university policy, what are our stated energy-reduction commitments and how do they map to GRI 302?" | `D1-qa-citations.png` (must show citation pills) |
| D2 | Automatic summary | click Summary on source 2 | `D2-summary.png` |
| D3 | Multi-source synthesis | "Compare how the university policy and the corporate sustainability report define materiality." | `D3-comparison.png` |
| D4 | Briefing doc generation | Studio → Briefing | `D4-briefing.png` |
| D5 | Notes + Q&A loop | Pin a note, then ask chat | `D5-notes.png` |
| D6 | Privacy/how-it-works | open notebook settings/information | `D6-privacy.png` |

## Observation log (fill during session)

| Time | Feature | Prompt/click | What was returned | Accuracy observation (correct/wrong/partial) |
|---|---|---|---|---|
| | D1 | | | |
| | D2 | | | |
| | D3 | | | |
| | D4 | | | |
| | D5 | | | |
| | D6 | | | |

## Accuracy probe (important for part c) — 3 extra questions to catch hallucination/out-of-scope behaviour

1. **Out-of-scope probe:** "What is the university's policy on free speech?" — is it in the sources? Observe whether the model declines or drifts to general knowledge → evidence for "confident generic answer" risk.
2. **Table probe:** ask about a figure that is inside a table in the corporate report → check citation precision.
3. **Modality probe:** ask whether GRI uses "must" or "should" for a specific clause → check whether nuance (mandatory vs voluntary) survives.

Log answers + your verdict in the same table above (add rows as needed).
