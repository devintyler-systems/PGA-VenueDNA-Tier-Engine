# par5_badge_input_contract.md

**Contract version:** 1.0
**Engine:** `events/2026_rocket_classic/engine/enrich_cards.py`
**Badge:** `par5_predator` (policy: `config/badge_policy.v1.json`)

---

## Source Files Consumed

| File | Year | Encoding | Columns Used |
|---|---|---|---|
| `2026_par5_scoring_average.csv` | 2026 | Latin-1 | `PLAYER`, `AVG`, `TOTAL STROKES`, `TOTAL HOLES` |
| `2025_par5_scoring_average.csv` | 2025 | Latin-1 | `PLAYER`, `AVG`, `TOTAL HOLES` |
| `2026_par5_birdieorbetter_leaders.csv` | 2026 | Latin-1 | `PLAYER`, `%`, `PAR 5 BIRDIES OR BETTER`, `PAR 5 HOLES` |
| `2025_par5_birdieorbetter_leaders.csv` | 2025 | Latin-1 | `PLAYER`, `%`, `PAR 5 HOLES` |
| `2026_par5_eagle_leaders.csv` | 2026 | Latin-1 | `PLAYER`, `TOTAL`, `TOTAL PAR 5 HOLES` |
| `2025_par5_eagle_leaders.csv` | 2025 | Latin-1 | `PLAYER`, `TOTAL`, `TOTAL PAR 5 HOLES` |

All files must be opened with `encoding="latin-1"`.

---

## Excluded Fields

- `TOTAL HOLE OUT` (eagle CSV): semantics unknown — do not consume
- `*_par5_performance.csv` files: non-canonical — do not ingest
- SG: Par-5 (strokes gained on par 5s): not used — this badge uses *outcome* stats only
- Driving distance, bogey avoidance: not used

---

## Eagle Rate Formula

```
eagle_rate = TOTAL / TOTAL_PAR_5_HOLES
```

Both `TOTAL` and `TOTAL_PAR_5_HOLES` must be non-null and `TOTAL_PAR_5_HOLES > 0`.

---

## Normalized Record Schema (`par5_records[player_id]`)

| Field | Type | Notes |
|---|---|---|
| `scoring_avg_2026` | float | `AVG` from scoring CSV |
| `total_strokes_2026` | int | `TOTAL STROKES` |
| `total_holes_2026` | int | `TOTAL HOLES` — primary eligibility denominator |
| `birdie_pct_2026` | float | `%` (already in percentage form, e.g. 55.2) |
| `birdies_2026` | int | `PAR 5 BIRDIES OR BETTER` |
| `birdie_holes_2026` | int | `PAR 5 HOLES` |
| `eagles_2026` | int | `TOTAL` from eagle CSV |
| `eagle_holes_2026` | int | `TOTAL PAR 5 HOLES` |
| `eagle_rate_2026` | float | Computed: `eagles / holes`; None if row absent or malformed |
| `scoring_avg_2025` | float | `AVG` from 2025 scoring CSV |
| `total_holes_2025` | int | 2025 `TOTAL HOLES` |
| `birdie_pct_2025` | float | 2025 `%` |
| `birdie_holes_2025` | int | 2025 `PAR 5 HOLES` |
| `eagle_rate_2025` | float | Computed from 2025 eagle CSV |
| `has_eagle_2026` | bool | True if player appeared in eagle CSV |
| `has_eagle_2025` | bool | True if player appeared in 2025 eagle CSV |
| `source_name_normalized` | str | Normalized CSV name used for resolution |
| `denom_ok_scoring_2026` | bool/None | `AVG ≈ TOTAL_STROKES/TOTAL_HOLES` within ±0.005 |
| `denom_ok_birdie_2026` | bool/None | `% ≈ BIRDIES/HOLES*100` within ±0.05 |
| `denom_cross_ok_2026` | bool/None | `scoring TOTAL_HOLES ≈ birdie PAR5_HOLES` within ±2 |
| `denom_cross_delta_2026` | int/None | Absolute difference for cross-file check |
| `eagle_denom_ok_2026` | bool/None | `eagle TOTAL_PAR5_HOLES ≈ scoring TOTAL_HOLES` within ±5 |

---

## Denominator Validation Rules

Three required 2026 checks — any `False` quarantines the player (badge ineligible):

1. **Scoring avg cross-check:** `|AVG - TOTAL_STROKES/TOTAL_HOLES| <= 0.005`
2. **Birdie pct cross-check:** `|% - BIRDIES/HOLES*100| <= 0.05`
3. **Cross-file denominator:** `|scoring_TOTAL_HOLES - birdie_PAR5_HOLES| <= 2`

Eagle cross-file check (tolerance ±5) is informational only — does not block eligibility.

---

## Coverage Statuses

| Status | Meaning |
|---|---|
| `FULL` | All 6 components measured and used |
| `CURRENT_FULL_HISTORICAL_PARTIAL` | All 2026 components measured (including eagle); some 2025 stabilization component(s) absent — current data is complete |
| `DEGRADED_NO_2026_EAGLE` | Player absent from 2026 eagle CSV; eagle_rate_2026=None; 2026 eagle weight redistributed |
| `UNAVAILABLE` | Required 2026 data missing or quarantined; `usable_for_badges=False` |
| `UNMATCHED` | Player not resolved from par-5 CSVs to event field |

---

## Identity Resolution

- **Method:** Deterministic alias only — no fuzzy matching
- **Payload format:** `"Knapp, Jake"` (last, first)
- **CSV format:** `"Jake Knapp"` (first last)
- **Steps:** payload name reversed to first-last → `normalize_name()` applied → exact dict lookup
- `normalize_name()`: strips diacritics (NFD decomposition, remove Mn category), lowercases, removes periods
- **Ambiguity:** if two event players produce the same normalized key, value is set to `None` (AMBIGUOUS); AMBIGUOUS keys are never matched to any player

---

## Eligibility Gate

Player must satisfy ALL of the following to be `usable_for_badges=True`:

1. Matched to event field (MATCHED resolution)
2. `scoring_avg_2026` is not None
3. `birdie_pct_2026` is not None
4. `total_holes_2026 >= 150`
5. `denom_ok_scoring_2026` is not False
6. `denom_ok_birdie_2026` is not False
7. `denom_cross_ok_2026` is not False

---

## Composite Score Formula

```
composite = sum(weight_i * z_i) / sum(weight_i_present)
```

Where z-scores are computed per-component among eligible cohort only:

| Component | Sign | Weight |
|---|---|---|
| scoring_avg_2026 | -1 (lower = better) | 0.45 |
| birdie_pct_2026 | +1 | 0.25 |
| eagle_rate_2026 | +1 | 0.15 |
| scoring_avg_2025 | -1 | 0.10 |
| birdie_pct_2025 | +1 | 0.03 |
| eagle_rate_2025 | +1 | 0.02 |

Weights renormalized if any components are absent (partial coverage allowed).
