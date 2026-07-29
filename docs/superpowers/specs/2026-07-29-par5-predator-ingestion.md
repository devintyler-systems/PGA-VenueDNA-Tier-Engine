# Par-5 Predator Badge — Ingestion Spec

**Date:** 2026-07-29
**Event:** 2026 Rocket Classic / Detroit Golf Club
**Schema:** rocket-classic-v1.4
**Badge ID:** `par5_predator`

---

## Goal and Scope

Add data-driven `par5_predator` badge emission to the Rocket Classic pipeline.

**Uses:** Outcome-based par-5 scoring statistics (scoring average, birdie-or-better %, eagle rate).

**Does NOT use:**
- SG: Par-5 (strokes-gained split) — not available in par-5 source files
- Driving distance — not a par-5 scoring outcome
- Bogey avoidance — not a par-5 scoring outcome
- `TOTAL HOLE OUT` column — semantics unknown, excluded

---

## Composite Score Formula

### Components and Weights

| Component | Sign | Weight | Source Column |
|---|---|---|---|
| `scoring_avg_2026` | -1 (lower is better) | 0.45 | `AVG` in `2026_par5_scoring_average.csv` |
| `birdie_pct_2026` | +1 | 0.25 | `%` in `2026_par5_birdieorbetter_leaders.csv` |
| `eagle_rate_2026` | +1 | 0.15 | `TOTAL/TOTAL_PAR_5_HOLES` in `2026_par5_eagle_leaders.csv` |
| `scoring_avg_2025` | -1 | 0.10 | `AVG` in `2025_par5_scoring_average.csv` |
| `birdie_pct_2025` | +1 | 0.03 | `%` in `2025_par5_birdieorbetter_leaders.csv` |
| `eagle_rate_2025` | +1 | 0.02 | `TOTAL/TOTAL_PAR_5_HOLES` in `2025_par5_eagle_leaders.csv` |

### Z-score Computation

For each component, z-scores computed independently among the eligible cohort (players meeting eligibility gate). Signed values used: `sign * raw_value`.

```
z_i = (signed_value_i - mean_i) / std_i
composite = sum(weight_i * z_i) / sum(weight_i)
```

Denominator `sum(weight_i)` uses only weights of components with a measured value — partial-coverage renormalization is automatic.

---

## Degraded Fallback and Renormalization

If a player has no 2026 eagle row (`eagle_rate_2026 = None`), the 0.15 eagle weight is dropped and the composite is renormalized across remaining components. Coverage status is set to `DEGRADED_NO_2026_EAGLE`.

Missing 2025 data similarly causes renormalization over whichever components are present. This is not a blocking condition.

---

## Qualification Threshold

```json
"threshold": { "field_percentile_min": 89 }
```

A player must be in the **89th percentile or above** of par-5 composite scores across the scored field.

---

## Volume Gate

Minimum **150 par-5 holes played in 2026** (`total_holes_2026 >= 150`) to be eligible. Players below this threshold receive `coverage_status = "UNAVAILABLE"` and are excluded from the percentile cohort.

---

## Identity Resolution

- Payload names are `"Last, First"` format; par-5 CSVs use `"First Last"`
- Reversal is deterministic: `"Knapp, Jake"` → `"Jake Knapp"`
- `normalize_name()` applied: strips diacritics, lowercases, removes periods
- Exact normalized string match only — **no fuzzy matching**
- Ambiguous keys (two event players with same normalized first-last) are excluded

---

## Denominator Validation

Three required cross-checks on 2026 data. Any `False` quarantines the player:

1. `|AVG - TOTAL_STROKES/TOTAL_HOLES| <= 0.005`
2. `|% - BIRDIES/HOLES*100| <= 0.05`
3. `|scoring_TOTAL_HOLES - birdie_PAR5_HOLES| <= 2`

Eagle cross-check (±5 tolerance) is informational only.

---

## Provenance

- Badge input carries full provenance string: e.g., `scoring_avg_2026=4.400; birdie_pct_2026=55.00%; eagle_rate_2026=0.0890`
- Qualification reason includes: composite z-score, field percentile, threshold, coverage status, 2026 holes, provenance string, source filenames

---

## Rebuild Commands

```bash
# Run engine (from repo root)
python events/2026_rocket_classic/engine/enrich_cards.py

# Validate badge emission
python events/2026_rocket_classic/output/validate_badge_emission.py

# Run preflight
python events/2026_rocket_classic/output/preflight_check.py

# Run tests
python -m pytest tests/test_par5_badge_inputs.py tests/test_par5_predator_qualification.py tests/test_badge_qualification.py -v
```

---

## Known Limitations

1. **`birdie_pct_2026` tolerance:** The `%` field in the birdie CSV includes a `%` suffix in some rows (e.g., `"59.72%"`). The CSV reader strips this via `float()` conversion which handles the suffix. Verify if source format changes.

2. **Eagle CSV coverage:** Not all players in the scoring/birdie CSVs appear in the eagle CSV. This is expected and handled gracefully via `DEGRADED_NO_2026_EAGLE` coverage.

3. **2025 data:** Used for stabilization only (combined weight 0.15). Players with no 2025 data still qualify if 2026 required inputs are present.

4. **Par-5 hole count skew:** Players with fewer total rounds played in 2026 may have lower hole counts even if they score well per hole. The 150-hole minimum is a hard gate to ensure statistical reliability.

5. **No SG: Par-5:** This badge intentionally avoids strokes-gained splits. It is an outcome-first badge measuring real scoring results on par 5s, not an SG decomposition.
