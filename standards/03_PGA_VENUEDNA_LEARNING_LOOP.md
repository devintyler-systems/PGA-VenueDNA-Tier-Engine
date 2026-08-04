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

Rho is written into `{slug}_r{N}_analysis.json` under `spearman_rho` and into `cumulative_learning.json` under `rho_by_round`.

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

## 5. ROUND ANALYSIS ARTIFACT SCHEMA

`{slug}_r{N}_analysis.json`:
```json
{
  "schema_version": "1.1",
  "event": "2026 3M Open",
  "round": 1,
  "generated_at": "<ISO 8601 UTC>",
  "spearman_rho": 0.4821,
  "spearman_p_value": 0.0012,
  "rho_interpretation": "moderate",
  "players_in_correlation": 156,
  "board": [
    {
      "VenueDNA_rank": 1,
      "player_name": "Scheffler, Scottie",
      "VenueDNA_tier": "T1",
      "VenueDNA_final_projection": 87.4,
      "r1_score": -6,
      "r1_position": 3,
      "r1_sg_total": 4.21,
      "status": "active"
    }
  ],
  "trait_validation": {
    "VenueDNA_trait_approach": "validated",
    "VenueDNA_trait_long_iron_150_225": "mixed",
    "VenueDNA_trait_total_driving": "neutral"
  },
  "round_notes": []
}
```

---

## 6. CUMULATIVE LEARNING SCHEMA

`{slug}_cumulative_learning.json` is appended after each round and finalized after R4:
```json
{
  "schema_version": "1.1",
  "event": "2026 3M Open",
  "generated_at": "<ISO 8601 UTC>",
  "rounds_complete": 4,
  "rho_by_round": {
    "R1": 0.48,
    "R2": 0.51,
    "R3": 0.55,
    "R4": 0.52
  },
  "trait_validation_summary": {
    "VenueDNA_trait_approach": {
      "R1": "validated", "R2": "validated", "R3": "validated", "R4": "validated",
      "consensus": "validated"
    },
    "VenueDNA_trait_easy_green_putting": {
      "R1": "neutral", "R2": "mixed", "R3": "neutral", "R4": "neutral",
      "consensus": "neutral"
    }
  },
  "tier_hit_rates": {
    "T1": { "top10_rate": 0.60, "top20_rate": 0.80, "made_cut_rate": 1.00 },
    "T2": { "top10_rate": 0.29, "top20_rate": 0.57, "made_cut_rate": 0.86 }
  },
  "model_accuracy_notes": [],
  "council_flags": []
}
```

---

## 7. FINAL ANALYSIS ARTIFACT

`{slug}_final_analysis.json` is produced after R4 and contains:
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
