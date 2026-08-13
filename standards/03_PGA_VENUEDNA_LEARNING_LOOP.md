# 03 — PGA VenueDNA Learning Loop

**Version:** 1.2
**Status:** Canonical
**Implements:** Post-round analysis pipeline as deployed in engine/build_round_analysis.py

---

## 1. OVERVIEW

The VenueDNA Learning Loop is the post-round analysis cycle that runs after each completed round (R1–R4) of a tournament. It:
- Overlays live scoring onto the pre-tournament VTS board
- Computes Spearman rank correlation between VTS rank and actual scoring rank
- Validates each canonical trait against observed round outcomes
- Accumulates findings across rounds into a single cumulative learning object
- Feeds the Model Council with empirical evidence for post-event synthesis

The learning loop is strictly read-after-write: it consumes pre-tournament output files and produces new round-specific artifacts. It never modifies the pre-tournament canonical files.

---

## 2. ROUND CADENCE

```
Round   Trigger                  Output files
R1      After R1 scorecards      {slug}_r1_analysis.json
R2      After R2 scorecards      {slug}_r2_analysis.json
R3      After R3 scorecards      {slug}_r3_analysis.json  (CUT applied)
R4      After final scorecards   {slug}_r4_analysis.json
                                 {slug}_cumulative_learning.json
                                 {slug}_council_findings.json
                                 {slug}_final_analysis.json
```

CUT rule: After R2 completion, players who missed the cut receive `status: "CUT"` in all subsequent round artifacts and are excluded from ranking correlation calculations for R3/R4.

---

## 3. SPEARMAN RANK CORRELATION

After each round, compute the Spearman rank correlation (rho) between:
- Pre-tournament VTS rank (`VenueDNA_rank`, ascending = best)
- Actual tournament position after round N (ascending = best)

```python
from scipy.stats import spearmanr

def compute_spearman(pre_ranks, actual_positions):
    rho, p_value = spearmanr(pre_ranks, actual_positions)
    return round(rho, 4), round(p_value, 4)
```

If scipy is unavailable, use the manual Spearman formula:
```
rho = 1 - (6 × Σd²) / (n × (n² - 1))
where d = difference in paired ranks, n = number of players (made-cut players for R3/R4)
```

**Interpretation thresholds:**
```
rho ≥ 0.60   — Strong validation (model tracking field well)
rho ≥ 0.40   — Moderate validation
rho ≥ 0.20   — Weak / noise range
rho < 0.20   — No meaningful correlation
rho < 0.00   — Inverse (flag for council review)
```

Rho must be preserved in the applicable round-analysis and cumulative-learning
artifacts according to their detailed, independently versioned interface contract in
`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`. This learning-loop standard does not
prescribe its field placement or nesting.

---

## 4. TRAIT VALIDATION SIGNALS

Each canonical VenueDNA trait is validated against the round outcome. Validation status values:

| Status      | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `validated` | Trait showed positive directional correlation this round       |
| `mixed`     | Trait showed inconsistent signal (positive in some players, negative in others) |
| `neutral`   | No meaningful correlation detected                             |
| `weak`      | Trait signal was systematically uncorrelated or inversely correlated |

**Assignment logic:**
- For each trait, compute the mean trait score for players who gained vs. lost strokes vs. field this round.
- If top-quartile trait players outperformed bottom-quartile by > 0.3 SG/round: `validated`
- If top-quartile outperformed by 0.1–0.3: `mixed`
- If difference < 0.1: `neutral`
- If bottom-quartile outperformed top-quartile: `weak`

**Traits tracked:**
```
VenueDNA_trait_approach
VenueDNA_trait_long_iron_150_225
VenueDNA_trait_total_driving
VenueDNA_trait_driving_accuracy
VenueDNA_trait_driving_distance
VenueDNA_trait_par5_scoring
VenueDNA_trait_easy_green_putting
VenueDNA_trait_course_history
VenueDNA_trait_closing_hole_composure
VenueDNA_trait_recent_form_context
```

Note: `VenueDNA_trait_debut_adjustment` is flagging context only and is not directly validatable via round outcomes.

---

## 5. ROUND-ANALYSIS INTERFACE AUTHORITY

Round-analysis artifacts are produced after each completed round and preserve the
learning-loop evidence described in this standard. Their detailed, independently
versioned interface — including field names, types, nesting, missing-value behavior,
and compatibility rules — is governed by
`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`.

This standard governs cadence, interpretation, and audit use of those artifacts; it
does not independently prescribe a detailed round-analysis JSON payload. Current
producer payloads and the README-linked library schema remain compatibility evidence
pending a separately authorized versioned migration. Archived consumers are evidence
only and do not establish present consumer compatibility or adapter requirements.

---

## 6. CUMULATIVE-LEARNING INTERFACE AUTHORITY

The cumulative-learning artifact records round-over-round learning and is updated
through the tournament lifecycle. Its detailed, independently versioned interface —
including field names, types, nesting, missing-value behavior, and compatibility
rules — is governed by `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`.

This standard governs what the learning loop must assess and when it runs; it does
not independently prescribe a detailed cumulative-learning JSON payload. No
field-level schema decision, current schema-version compatibility decision,
producer-output migration, adapter/wrapper, or consumer implementation requirement
is made by this authority assignment.

---

## 7. FINAL ANALYSIS ARTIFACT

The detailed, independently versioned final-analysis interface is governed by
`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`. Functionally, the final analysis is
produced after R4 and contains:
- Final Spearman rho across all 4 rounds
- Tier hit rate summary
- Top-10 coverage: fraction of actual top-10 finishers who were VenueDNA T1 or T2
- Trait consensus validation across all rounds
- Named over-performers (players who outperformed VenueDNA_rank significantly)
- Named under-performers (players who underperformed significantly)
- Key learnings for venue library update consideration

---

## 8. SCHEMA UPDATE RULES

Cumulative learning findings may trigger schema updates only under these conditions:

1. **Trait addition**: A new trait may be added to the canonical schema if at minimum 2 consecutive events at similar venues show `validated` consensus. Requires Model Council approval (see `05_MODEL_COUNCIL_GOVERNANCE.md`).

2. **Trait removal**: A trait may be removed if it shows `neutral` or `weak` consensus in 3+ consecutive events at the same venue type. Requires Model Council approval.

3. **Weight adjustment**: Decay weights (Base: 0.20/0.30/0.50; Delta: 0.50/0.30/0.20) may be adjusted in `engine/enrich_cards.py` only after council review with Spearman rho evidence across ≥3 events.

4. **Threshold adjustment**: Tier boundaries (T1:1-5, etc.) and cut probability formula are frozen at schema version 1.1 until a full cross-event audit produces a change recommendation.

No schema changes take effect mid-tournament. Changes apply to the next event build only.

---

## 9. LEARNING LOOP VERIFICATION

After each round analysis run:
```
pytest tests/  # all engine tests must still pass
```

Spearman rho below 0.20 for two consecutive rounds is a model health flag requiring council review before R3 or R4 analysis proceeds.

---

## 10. ROCKET CLASSIC 2026 LEARNING ENTRY

**Status:** Provisional one-event evidence and guidance; not a permanent global engine rule.
**Mirrored in:** `02_PGA_VENUEDNA_SCORING_SPEC.md` §17 (ROCKET CLASSIC 2026 INACTIVE RESEARCH HYPOTHESES) and §18 (INACTIVE ROCKET-DERIVED LIVE-BADGE HYPOTHESIS (ALPHA/BETA/GAMMA)).

**Context:** 2026 Rocket Classic (Detroit Golf Club). Approach-driven venue with renovated corridors and bunker pressure, bentgrass greens, birdie-heavy upside but real penalty strokes off the tee. Variance class: medium–high (birdie race with punishment).

### 10.1 Variance and CeilingIndex

**Problem:** The winner and key podium finishers (Thorbjornsen, Riley, Højgaard) came from T4/T5 with modest VTS but real upside that the pre-event model did not capture.

**Provisional guidance:** Evaluate a `CeilingIndex` hypothesis from recent tee-to-green form, volatility, and venue scoring fit; it may be tested as `vtsceil` and live-badge context in a separately authorized implementation.

**Hypothesis:** T3–T5 players with high CeilingIndex may warrant provisional review for elevated live badges or `vtsceil` context even when baseline VTS is modest.

### 10.2 Badge Governance

**Finding:** Iron Surgeon and Detroit Veteran validated as strong support signals in Rocket. Hot Streak and Par-5 Predator underperformed.

**Provisional guidance:** Iron Surgeon and Detroit Veteran are support hypotheses only when structural traits and venue rules agree; Hot Streak and Par-5 Predator remain low-weight or narrative candidates until cross-event back-testing shows better hit rates.

### 10.3 Approach Deficit Flag Recency

**Problem:** Højgaard's "Approach Deficit" flag contradicted his actual SG:APP and recent form.

**Provisional guidance:** Test full approach-deficit treatment only when both long- and short-window data show weakness; otherwise retain a watchlist hypothesis when the most recent window is neutral or positive.

### 10.4 Trait Concentration Cap

**Problem:** SG:APP + App 150–200 consumed ~65% of VTS at Detroit.

**Provisional guidance:** Treat the concentration finding as a candidate for a future direct-trait submodel; it does not override formula v2.0.0, which has no active direct trait block.

### 10.5 T2 Tier Risk Tag

**Problem:** T2 "average-good, badge-inflated" profiles (Clark, Gotterup, Spaun) busted more than tiers suggested.

**Provisional guidance:** Evaluate a `T2RiskTag` candidate for Tier 2 players with no trait score above a high threshold and multiple badges; any confidence or live-badge treatment requires separately authorized testing.

### Governance and deployment rules

- One event cannot create a permanent global engine rule. Rocket findings may become venue-specific hypotheses, provisional guidance, audit flags, or candidates for future testing.
- Global scoring-weight, schema, gate, or doctrine changes require the applicable multi-event threshold: at least three relevant or sufficiently similar events by default, unless a higher governing standard applies.
- Model Council approval and explicit operator authorization remain required before an authorized implementation change. Mirroring a rule in `02_PGA_VENUEDNA_SCORING_SPEC.md` alone is not implementation authority.
- Formula v2.0.0 is not overridden by Rocket observations. The evidence may support future bounded research but does not directly alter canonical v2 scoring.
- Council governance tracks whether these hypotheses improve Tier 1/T2 accuracy and whether ceiling/variance handling reduces "winner from T4/T5 with no conviction" misses.
- Rocket Classic 2027 (if played) is the primary test venue for these Detroit-specific learnings; other medium–high variance, approach-driven venues are secondary test beds.

---

## 11. FINAL-AUDIT AND PROPOSED WRITE-BACK DISCIPLINE

This section governs the final accountability review after the R4/final analysis is available. It complements, and does not replace, the round cadence and artifact rules above. The canonical pre-event projection and each prior-round artifact remain read-only evidence; an audit never rewrites them.

### 11.1 Tier accountability review

Review Tier 1 and Tier 2 against final outcomes, including their final position or finish band, made-cut status where applicable, and the model evidence actually available in the frozen artifacts. Review tier shape as well as the winner: Tier 1 Top-10 coverage, Tier 2 contender/Top-20 coverage, and material underperformance or overperformance must be assessed without inventing an outcome band, probability, or player evidence that was not emitted.

An audit finding may identify whether the available evidence supports a structural confirmation, a structural miss, an incomplete-evidence finding, or variance. It must not retroactively change the official pre-event rank, tier, score, or probability.

### 11.2 Material-miss classification

Each material miss must receive one primary classification and may receive a secondary contributing classification. Use the narrowest layer supported by the evidence:

- `NeutralSkill`
- `VenueFitDelta`
- `VenueHistoryDelta`
- `penalty_gate`
- `debut_framework`
- `data_completeness`
- `conditions`
- `variance`
- `Model_Council`

`penalty_gate` is a classification layer, not authority to activate a penalty or gate. Under formula v2.0.0, `penalty_gate_set_id: venuedna_v2_none` remains in force unless a separately approved scoring change updates the canonical formula. Likewise, `VenueHistoryDelta` review must preserve its current approved neutral contribution until a bounded transform is separately authorized.

Classify `data_completeness` when source absence, identity resolution, sample sufficiency, or unavailable structured evidence prevents a reliable layer verdict. Classify `conditions` when realized weather or setup materially differs from the documented conditions evidence; do not turn a conditions finding into an unsupported score adjustment. A finding that cannot be classified from available evidence must be recorded as incomplete evidence rather than inferred from reputation, market, salary, or generic form.

### 11.3 Anti-pattern and risk-mechanism review

Review an anti-pattern only when a documented flag, structural mechanism, or conditions-sensitive modifier exists in the frozen event evidence. For each reviewed case, record:

- direction: whether the stated mechanism was supported, contradicted, or indeterminate;
- magnitude: whether the recorded effect or non-effect was proportionate to the evidence available;
- setup and conditions: whether documented firmness, weather, routing, rough, green speed, or other approved modifier evidence materially affected the mechanism; and
- uncertainty: whether sample size, data quality, or confounding variance prevents a stable conclusion.

No audit may create an anti-pattern, penalty magnitude, score adjustment, or gate from an outcome alone. The same rule applies to named risk mechanisms: review whether the mechanism was evidenced and whether the existing emitted probability or confidence treatment was appropriately calibrated, but do not invent probabilities or rerank players after the fact.

### 11.4 Probability-calibration review

Where the canonical artifacts emitted probability vectors, compare their stated bands with realized frequencies by tier and conditions class. Review calibration separately from rank ordering and distinguish an overconfident or underconfident distribution from a scoring-layer miss. Do not use derivative-market, odds, salary, ownership, DFS, or betting outcomes as core-model evidence, and do not infer probability values that the producer did not emit.

### 11.5 Finding decisions and proposed actions

Every material finding must end with exactly one recorded decision status:

| Status | Meaning |
|---|---|
| `confirm` | Evidence supports the existing structural interpretation. |
| `downgrade` | Evidence lowers confidence in a documented interpretation or hypothesis; it does not retroactively alter a frozen projection. |
| `promote` | Evidence elevates a documented hypothesis for bounded future research; it does not activate an engine rule. |
| `hold` | Evidence is mixed, insufficient, or materially confounded; retain the current doctrine unchanged. |
| `proposed_venue_write_back` | Evidence supports a venue-specific candidate change, pending operator approval. |
| `proposed_engine_rule_research` | Evidence supports a cross-venue research flag, not an engine change. |
| `logged_no_change` | The finding was reviewed and recorded with no doctrine or venue action proposed. |

The decision status records the audit ruling only. It does not authorize a rewrite of frozen artifacts, an immediate venue-profile edit, a scoring change, or a new payload field.

### 11.6 Evidence thresholds and write-back separation

Every material finding must state its evidence basis, applicable evidence threshold, confidence or uncertainty, and whether it is venue-specific or potentially cross-venue. One-event anecdotes do not change venue doctrine or engine doctrine.

Venue-specific evidence may produce only a `proposed_venue_write_back`; it must identify the proposed target layer and remain unimplemented until operator approval. Cross-venue evidence may produce only a `proposed_engine_rule_research` flag. Any scoring, weight, tier, penalty, gate, probability, or schema change must follow the applicable evidence threshold and change authority in `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` and `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`, including the required Council review and operator authorization.

These are policy requirements for final-audit content, not a new JSON or CSV schema. Existing artifact locations, field names, source-manifest behavior, identity handling, and deploy contracts remain governed by `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` and their current implementations.

### 11.7 Model Council role at audit

At final audit, the Model Council is a challenge layer. It pressure-tests evidence quality, duplicate reasoning, uncertainty, and proposed venue or engine research; it does not replace canonical scoring, cure missing evidence, or turn consensus, DG benchmark, market, salary, ownership, DFS, or betting information into core-rank changes.

The Council may record a challenge, confirmation, or no-change ruling and may require a proposal to remain in `hold` status. It may not apply a write-back or alter formula v2.0.0 without the separately required authority and approval path.
