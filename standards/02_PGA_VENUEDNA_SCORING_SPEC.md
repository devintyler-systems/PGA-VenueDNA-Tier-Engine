# 02 — PGA VenueDNA Scoring Specification

**Version:** 1.1
**Status:** Canonical
**Implements:** Dual-Vector True SG pipeline as deployed in engine/enrich_cards.py

---

## 1. OVERVIEW

VenueDNA scoring produces `VenueDNA_final_projection` (VTS) for each player by:
1. Computing per-horizon SG vectors from All Courses and Similar Courses CSVs
2. Applying sample-weight regression to suppress thin venue samples
3. Blending across three time horizons with decoupled decay weights
4. Z-score scaling to a fixed normal (mean=50, std=15, clamped [0,100])
5. Computing tempered softmax probability vectors for Win/Top5/Top10/Top20
6. Deriving Make Cut probability and enforcing monotonicity

All steps are implemented in `engine/enrich_cards.py`. This document is the authoritative specification; the Python implementation must match it exactly.

---

## 2. INPUT FILES

Six CSV files are required. All use the same three-column schema:

```
player_name   — string; normalized to "Last, First" format; strip surrounding quotes and whitespace
rounds_played — integer; number of qualifying rounds in the horizon window
total_mean    — float; mean strokes gained per round across the horizon
```

Files (relative to `events/{slug}/input/`):
```
pga_sg_query_allcourses_l6.csv    — All Courses, last 6 months
pga_sg_query_allcourses_l12.csv   — All Courses, last 12 months
pga_sg_query_allcourses_l24.csv   — All Courses, last 24 months
pga_sg_query_{slug}_similar_l6.csv  — Similar Courses, last 6 months
pga_sg_query_{slug}_similar_l12.csv — Similar Courses, last 12 months
pga_sg_query_{slug}_similar_l24.csv — Similar Courses, last 24 months
```

If `total_mean` contains the string `"null"` or `"none"`, treat as 0.0.

---

## 3. NAME NORMALIZATION

```python
def normalize_name(s):
    return (s or "").strip().strip('"').strip("'").strip()
```

Canonical format: `"Last, First"` (DataGolf convention). All lookups use normalized names.

---

## 4. PLAYER UNIVERSE

Union of all player names appearing in any of the 6 input CSVs. Players missing from a given file receive a debut row: `{rounds: 0, total_mean: 0.0}`.

---

## 5. PER-HORIZON COMPUTATION

For each time horizon h ∈ {6m, 12m, 24m}:

```
SG_Base_h   = total_mean from allcourses_lh CSV (debut: 0.0)
N_Sim_h     = rounds_played from similar_lh CSV (debut: 0)
SG_Sim_h    = total_mean from similar_lh CSV (debut: 0.0)

Sample weight:
  W_h = min(1.0, N_Sim_h / 20.0)
  Interpretation: 0 when no similar-course rounds; 1.0 when ≥20 rounds

Regressed similar-course SG:
  SG_Sim_Reg_h = (W_h × SG_Sim_h) + ((1 - W_h) × SG_Base_h)
  Interpretation: Falls back to baseline when N_Sim is thin

Delta Fit per horizon:
  Delta_Fit_h = SG_Sim_Reg_h - SG_Base_h
```

---

## 6. COMPOSITE BLENDING — DECOUPLED DECAY

Two composites are computed independently with different decay schedules:

**SG Base Composite (stability-heavy):**
```
SG_Base_Comp = 0.20 × SG_Base_6m + 0.30 × SG_Base_12m + 0.50 × SG_Base_24m
```
Rationale: Long-term skill is more predictive than short-term form on neutral baseline.

**Delta Fit Composite (recency-heavy):**
```
Delta_Fit_Raw = 0.50 × Delta_Fit_6m + 0.30 × Delta_Fit_12m + 0.20 × Delta_Fit_24m
Delta_Fit_Comp = clamp(Delta_Fit_Raw, -0.50, +0.50)
```
Rationale: Recent venue-type performance is a stronger signal than historical. The ±0.50 clamp prevents extreme thin-sample outliers from dominating.

**SG Similar Composite:**
```
SG_Sim_Comp = SG_Base_Comp + Delta_Fit_Comp
```

---

## 7. VTS RAW SCORE

```
VTS_Raw = SG_Sim_Comp  (same as SG_Base_Comp + Delta_Fit_Comp)
```

VTS_Raw is the latent ranking signal. It is not exposed directly; it is only used as input to Z-score scaling and probability computation.

---

## 8. Z-SCORE SCALING

Applied independently to VTS_Raw and SG_Base_Comp to produce the two display scores:

```
vts_final         = z_score_scale(all VTS_Raw values)
neutralSkillIndex = z_score_scale(all SG_Base_Comp values)
```

Z-score formula:
```python
def z_score_scale(values, mean=50.0, std=15.0):
    if not values: return []
    mu  = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd  = sqrt(var) if var > 0 else 1.0
    return [max(0.0, min(100.0, mean + std * (v - mu) / sd)) for v in values]
```

Output range: [0, 100], hard-clamped. Mean of the field maps to exactly 50.0.

`vts_final` is what the UI displays as "VTS". It is the official ranking signal for `VenueDNA_rank` (descending sort on vts_final).

---

## 9. PROBABILITY VECTORS — TEMPERED SOFTMAX

Four independent probability vectors are computed over the full field using VTS_Raw scores:

| Output     | Temperature T | N_positions |
|------------|--------------|-------------|
| winPct     | 3.5          | 1           |
| top5Pct    | 5.0          | 5           |
| top10Pct   | 7.0          | 10          |
| top20Pct   | 10.0         | 20          |

Formula (applied per output):
```python
def tempered_softmax(scores, T, n_positions):
    max_s = max(scores)                              # numerical stability
    exps  = [exp((s - max_s) / T) for s in scores]
    total = sum(exps)
    return [min(99.9, (e / total) * n_positions * 100) for e in exps]
```

Each player receives an independent percentage. Field sum ≈ n_positions × 100%.
Hard cap: 99.9 per player per outcome.

Monotonicity is enforced after softmax:
```python
def enforce_monotonicity(p):
    p["top5Pct"]  = max(p["top5Pct"],  p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])
```

---

## 10. CUT PROBABILITY

```
makeCutPct = min(98.0, max(20.0, top20Pct × 1.25 + 10.0))
missCutPct = 100.0 - makeCutPct
```

---

## 11. TIER ASSIGNMENT

Based on `VenueDNA_rank` (ascending rank from vts_final sort):

```
T1: ranks 1–5
T2: ranks 6–12
T3: ranks 13–25
T4: ranks 26–40
T5: ranks 41+
```

---

## 12. DATA DEPTH FLAG

```
data_depth = "FULL"  if any similar-course CSV had rounds > 0 for this player
data_depth = "DEBUT" if no similar-course CSV had any rounds for this player
```

DEBUT players receive W_h = 0 for all horizons, meaning SG_Sim_Comp collapses to SG_Base_Comp and Delta_Fit_Comp = 0.

---

## 13. BOARD EXPORT SCHEMA

`deploy/data/board_export.json` envelope:
```json
{
  "schemaVersion": "3m-dual-vector-v1.0",
  "generatedAt":  "<ISO 8601 UTC timestamp>",
  "event":        "2026 3M Open",
  "venue":        "TPC Twin Cities",
  "players":      [ ... ]
}
```

Per-player object (canonical field order):
```json
{
  "rank":                 1,
  "player":               "Scheffler, Scottie",
  "tier":                 "T1",
  "vts_final":            87.4,
  "neutralSkillIndex":    85.1,
  "sg_base_composite":    2.824,
  "sg_similar_composite": 2.910,
  "delta_fit":            0.086,
  "data_depth":           "FULL",
  "winPct":               18.5,
  "top5Pct":              42.1,
  "top10Pct":             58.3,
  "top20Pct":             74.6,
  "makeCutPct":           92.0,
  "missCutPct":           8.0
}
```

All float fields: 1 decimal for vts_final/neutralSkillIndex/probabilities; 4 decimals for sg_* and delta_fit.

---

## 14. VENUEDNA vs. DG FIELD AUTHORITY

| VenueDNA Field                  | Drives          |
|---------------------------------|-----------------|
| vts_final / VenueDNA_final_projection | Official rank |
| VenueDNA_tier                   | Official tier   |
| VenueDNA_rank                   | Row ordering    |
| VenueDNA_neutral_skill          | NSI display     |
| delta_fit / VenueDNA_venue_fit_delta | Venue fit signal |

| DG Benchmark Field              | Role            |
|---------------------------------|-----------------|
| DG_finalprediction_benchmark    | Audit comparison |
| DG_baseline_benchmark           | Skill decomp    |
| DG_coursefittotaladj_benchmark  | Course fit audit |
| All other DG_* fields           | Read-only context |

DG fields must never be used to derive official ranks. If VenueDNA and DG disagree, VenueDNA wins. Disagreements should be logged in council findings.

---

## 15. VERIFICATION

After running `engine/enrich_cards.py --event {slug}`:

```
pytest tests/test_enrich_cards.py   # 27 pure-function tests must pass
node --check events/{slug}/deploy/app.js  # JS syntax must be clean
```

Output validation:
- Player count must match union of all 6 SG CSVs
- Rank 1 must have highest vts_final
- All top20Pct ≥ top10Pct ≥ top5Pct ≥ winPct
- All makeCutPct in [20.0, 98.0]
- All vts_final and neutralSkillIndex in [0.0, 100.0]
