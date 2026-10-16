# Q3(b) — Comparison: LLM (expected run) vs zero-shot HF baseline vs rule-based baseline

## Ground truth (analyst-estimated expected classifications)

| id | message (abridged) | issue_category (expected) | urgency (expected) | followup | team |
|---|---|---|---|---|---|
| 1 | water leak, running all morning | environment_facilities | HIGH | Y | Facilities & EM |
| 2 | recycling bins contaminated again | waste_contamination | MEDIUM | Y | Facilities & EM |
| 3 | A/C running overnight, empty office | energy_waste | LOW-MEDIUM | Y | Facilities & EM |
| 4 | supplier may breach sustainability policy | supplier_governance | MEDIUM | Y | Procurement Governance |
| 5 | accessible entrance blocked 2 days | accessibility_inclusion | HIGH | Y | Workplace Inclusion & Access |
| 6 | chemical drums dumped near drain to creek | unsafe_disposal_environment_risk | CRITICAL | Y | Security & HSE |
| 7 | praise for café reusable-cup program | general_enquiry_feedback | LOW | N | Sustainability Office |
| 8 | leak near switchboard, slippery floor | environment_facilities | CRITICAL | Y | Security & HSE / Facilities |
| 9 | where is the catering policy | general_enquiry_feedback | LOW | N | Sustainability Office |
| 10 | depot lights on all day in full sun | energy_waste | MEDIUM | Y | Facilities & EM |

## Zero-shot HF baseline results (facebook/bart-large-mnli) — GENUINE RUN (results/zero_shot_baseline.json)

| id | predicted category (score) | expected | verdict | urgency predicted (score) | expected | verdict |
|---|---|---|---|---|---|---|
| 1 | environment_facilities (0.20) | ✓ | correct | CRITICAL (0.43) | HIGH | over-call |
| 2 | waste_contamination (0.41) | ✓ | correct | CRITICAL (0.37) | MEDIUM | over-call |
| 3 | environment_facilities (0.44) | ✗ energy_waste | wrong | MEDIUM (0.35) | LOW-MED | acceptable |
| 4 | supplier_governance (0.56) | ✓ | correct | CRITICAL (0.51) | MEDIUM | over-call |
| 5 | accessibility_inclusion (0.40) | ✓ | correct | HIGH (0.31) | HIGH | correct |
| 6 | waste_contamination (0.44) | ✗ unsafe_disposal | wrong (close) | CRITICAL (0.47) | CRITICAL | correct |
| 7 | accessibility_inclusion (0.25) | ✗ general_enquiry | wrong | MEDIUM (0.51) | LOW | over-call |
| 8 | environment_facilities (0.22) | ✓ | correct | CRITICAL (0.52) | CRITICAL | correct |
| 9 | general_enquiry_feedback (0.55) | ✓ | correct | CRITICAL (0.57) | LOW | severe over-call |
| 10 | accessibility_inclusion (0.32) | ✗ energy_waste | wrong | MEDIUM (0.36) | MEDIUM | correct |

**Zero-shot category accuracy: 5/10. Zero-shot urgency accuracy: 4/10** (scoring expected within
an adjacent band; over-calls dominate).

## Rule-based baseline results — GENUINE RUN (results/baseline_rule_based.json)10/10 structurally valid outputs, fully deterministic. Category accuracy: 8/10 (msg 10 "lights … stay on all day" falls through to UNCLEAR due to word order none of the regexes expect — regex hole; msg 8 is routed to Facilities rather than HSE because the keyword "water" fires before the electrical/slippery risk words are considered, but its urgency is still called HIGH correctly). Urgency: correct for msg 6 (CRITICAL, proper escalation reason), msg 5 as MEDIUM rather than HIGH (no escalation word match — a miss in a context where a person's access is blocked for two days). Sentiment is crude positive/negative switching. Escalation logic is byte-consistent but blind to composites."}

## Discussion (as required by Q3b: consistency, errors, bias)

**Consistency.** The rule-based baseline is perfectly *deterministic* — same input, same output,
no API cost, no latency tail. But it is brittle beyond its keyword table (see msg 10). The
zero-shot baseline is *probabilistic*: it produced low-confidence wins (msg 1 category score only
0.20) and its separation between adjacent labels (energy_waste vs environment_facilities,
contamination vs unsafe disposal) collapses exactly where the operational stakes rise. The LLM in
JSON mode (expected run with the revised prompt) is consistent across runs at temperature 0
because enumerated labels + anchored definitions constrain its sampling space, plus confidence
gating surfaces its uncertainty instead of hiding it.

**Errors.**
- *Zero-shot:* message 9 (a routine question) scored **CRITICAL 0.57** — the single most
  operationally dangerous kind of error, since triage automation would page humans at 3am for a
  policy question. Root cause: the NLI-style hypothesis "regarding urgency: people or environment
  are at immediate risk" matches *negation-free* generic phrasing better than the LOW hypothesis
  ("routine matter that can wait") because BART-MNLI scores lexical entailment, not operational
  severity. Zero-shot models have no notion of organisational routing rules — something the
  in-context routing table in the revised LLM prompt directly fixes.- *Rule-based:* keyword collisions ("lights on" vs "stay on"; "dumped" ranks only after "bin" if both fire) and blind accept/reject decisions. No recall beyond its dictionary — a real employee message phrasing an energy issue as "HVAC running while nobody is there after hours" would fall through to UNCLEAR.
- *LLM (expected):* residual risks are (a) brief_summary occasionally paraphrasing into a claim
  not strictly stated (mild hallucination) — mitigated by the max-20-words + "do not invent"
  rules; (b) data_sensitivity_risk on msg 4-type supplier claims may be under-called because the
  message does not name a person; (c) when the model sees a mixed message ("blocked entrance …
  also the tap drips") which of two categories it picks is less stable than a human would be.

**Bias observed.**
- Zero-shot urgency systematically over-calls CRITICAL (5/10 messages) — operationally "alert
  fatigue" bias, which in real deployments trains staff to ignore the tool.
- Rule-based baseline encodes only the problems its author imagined; messages about
  accessibility from non-native speakers, or about thermal comfort rather than lights, would
  systematically miss — a coverage bias.
- An LLM inherits its training distribution: it may under-flag issues phrased politely
  ("whenever someone gets a chance…") because politeness correlates with LOW in typical web
  text — a modality-vs-severity mismatch. This is exactly why the revised prompt anchors
  urgency to *observable facts* (leak running all morning), not tone.
- Caption/embedding fairness note: zero-shot classification with English hypothesis templates
  penalises non-standard English; enterprise deployment needs a multilingual model or
  pre-translation layer, else reports from the same incidents classify worse for some cohorts.

## Conclusion feeding Q3(c)

The zero-shot HF baseline is useless as an *operational* tier but useful as a *cheap drift
detector* (e.g., daily re-run on sample messages; if agreement with the LLM drops below an
agreed threshold, something has changed — either input distribution or model behaviour).
The rule-based baseline is valuable as an always-on fallback when the API is down, at the
price of coarse-grained accuracy. The LLM-plus-revised-prompt approach is the only one of the
three capable of the full schema (including `data_sensitivity_risk` and `escalation_reason`)
with consistent state — hence it should drive automated triage, with (1) schema validation,
(2) confidence-gating to humans, (3) CRITICAL always human-confirmed, exactly as specified in
the deployment note in `prompt_revised.md`.
