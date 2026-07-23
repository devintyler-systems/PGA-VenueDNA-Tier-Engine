# 04 — PGA VenueDNA Artifact Schema

**Version:** 1.1
**Status:** Canonical
**Scope:** All input/output file contracts, field mappings, exact CSV column orders

---

## 1. SCHEMA VERSION POLICY

Current canonical schema: **1.1**

Schema version must appear in every generated output:
- JSON artifacts: `"schema_version": "1.1"` or `"schemaVersion": "..."` at top level
- CSV artifacts: documented here; no inline version field
- All artifacts generated in a single event build must share the same schema version

---

## 2. INPUT FILE CONTRACTS

### 2A. pga_field.csv

Source: PGA Tour / DataGolf field list
Path: `events/{slug}/input/pga_field.csv`

**Exact headers (as observed):**
```
event_name, course_name, player_name, dg_id, player_num, dg_rank, owgr_rank, tour_rank,
r1_teetime, r1_wave, r1_starthole, r2_teetime, r2_wave, r2_starthole
```

**Field mapping to output schema:**
```
pga_field.csv header  →  Output field name
dg_id                 →  dg_id
r1_teetime            →  r1_tee_time
r1_wave               →  r1_wave
r1_starthole          →  r1_start_hole
r2_teetime            →  r2_tee_time
r2_wave               →  r2_wave
r2_starthole          →  r2_start_hole
```

Note: The build prompt lists camelCase source names (e.g., `dgid`, `r1teetime`). The actual CSV uses underscore format (`dg_id`, `r1_teetime`). Use the exact headers from the actual CSV file, not the prompt's mapping labels.

### 2B. dg_decomposition.csv

Source: DataGolf prediction decomposition export
Path: `events/{slug}/input/dg_decomposition.csv`

**Exact headers (as observed):**
```
player_name, sample_size, baseline, country_adj, age, age_adj, true_sg_adj, timing_adj,
sg_category_adj, course_history_adj, driving_dist_adj, driving_acc_adj, fit_other_adj,
course_fit_total_adj, final_prediction, std_dev, event_name, course_name
```

**Field mapping to output schema:**
```
dg_decomposition.csv header  →  Output DG benchmark field
baseline                     →  DG_baseline_benchmark
timing_adj                   →  DG_timingadj_benchmark
sg_category_adj              →  DG_sgcategoryadj_benchmark
course_history_adj           →  DG_coursehistoryadj_benchmark
driving_dist_adj             →  DG_drivingdistadj_benchmark
driving_acc_adj              →  DG_drivingaccadj_benchmark
course_fit_total_adj         →  DG_coursefittotaladj_benchmark
final_prediction             →  DG_finalprediction_benchmark
std_dev                      →  DG_stddev_benchmark
```

Note: The build prompt's mapping labels (`timingadj`, `sgcategoryadj`, etc.) are the canonical output field suffix names. The source column headers in the actual CSV use underscores (`timing_adj`, `sg_category_adj`, etc.).

### 2C. pga_sg_query_allcourses_l{6,12,24}.csv and pga_sg_query_{slug}_similar_l{6,12,24}.csv

**Required columns (all 6 files):**
```
player_name, rounds_played, total_mean
```

Additional columns may exist and are ignored. Only these three are consumed by `enrich_cards.py`.
Values of `"null"`, `"none"`, or `""` in `total_mean` are treated as 0.0.

### 2D. datagolf.csv

Source: DataGolf prediction summary
**Consumed fields:** player_name, current prediction rank, win probability (used as benchmark only)

### 2E. dg_course_table.csv

Source: DataGolf course history table
**Consumed fields:** player_name, course_history rounds/results (used for VenueDNA_trait_course_history)

### 2F. dg_performance_2026.csv

Source: DataGolf in-season performance summary
**Consumed fields:** player_name, recent SG splits by category (used for trait scoring and form context)

### 2G. pga_field_trending_table.csv

Source: PGA Tour trending/momentum data
**Consumed fields:** player_name, trend indicators (used for VenueDNA_trait_recent_form_context)

### 2H. app_skill_l12_*.csv (5 files)

Source: Approach skill detail exports
Files: `app_skill_l12_sg.csv`, `app_skill_l12_gh.csv`, `app_skill_l12_bad.csv`, `app_skill_l12_great.csv`, `app_skill_l12_prox.csv`
**Consumed fields:** player_name + primary metric column (approach SG, GIR%, bad shot rate, great shot rate, proximity)
**Used for:** `VenueDNA_trait_approach`, `VenueDNA_trait_long_iron_150_225`

---

## 3. OUTPUT FILE CONTRACTS

### 3A. {slug}_trait_form_matrix.csv

Path: `events/{slug}/output/{slug}_trait_form_matrix.csv`

**Exact column order (do not change):**
```
player_name,dg_id,event_name,course_name,
VenueDNA_neutral_skill,VenueDNA_venue_fit_delta,VenueDNA_venue_history_delta,
VenueDNA_penalties_total,VenueDNA_final_projection,VenueDNA_tier,VenueDNA_rank,
VenueDNA_confidence_band,VenueDNA_variance_class,
VenueDNA_trait_approach,VenueDNA_trait_long_iron_150_225,VenueDNA_trait_total_driving,
VenueDNA_trait_driving_accuracy,VenueDNA_trait_driving_distance,VenueDNA_trait_par5_scoring,
VenueDNA_trait_easy_green_putting,VenueDNA_trait_course_history,
VenueDNA_trait_closing_hole_composure,VenueDNA_trait_debut_adjustment,
VenueDNA_trait_recent_form_context,
VenueDNA_flag_accuracy_risk,VenueDNA_flag_short_game_only,VenueDNA_flag_putting_dependency,
VenueDNA_flag_long_iron_deficit,VenueDNA_flag_debut_uncertainty,
VenueDNA_penalty_notes,VenueDNA_rule_reference,VenueDNA_penalty_impact,
tags,anti_pattern_flags,search_blob,
DG_baseline_benchmark,DG_timingadj_benchmark,DG_sgcategoryadj_benchmark,
DG_coursehistoryadj_benchmark,DG_drivingdistadj_benchmark,DG_drivingaccadj_benchmark,
DG_coursefittotaladj_benchmark,DG_finalprediction_benchmark,DG_stddev_benchmark
```

**Field value rules:**
- VenueDNA trait scores: integer 0–100 or `"unknown"` if data not available
- VenueDNA flags: `true` / `false` / `"unknown"`
- DG benchmark fields: float as-is from source CSV, or `"unknown"` if player not in dg_decomposition.csv
- `VenueDNA_confidence_band`: `"high"` / `"medium"` / `"low"` (based on data_depth and sample size)
- `VenueDNA_variance_class`: `"low"` / `"medium"` / `"high"` (based on DG_stddev_benchmark)
- `tags`: pipe-separated string, e.g., `"T1|approach_elite|par5_upside"`
- `anti_pattern_flags`: pipe-separated string or empty
- `search_blob`: concatenated searchable text (name + tags + flags)

### 3B. {slug}_vts_full.csv

Path: `events/{slug}/output/{slug}_vts_full.csv`

**Exact column order (do not change):**
```
player_name,dg_id,event_name,course_name,
VenueDNA_rank,VenueDNA_tier,VenueDNA_final_projection,VenueDNA_neutral_skill,
VenueDNA_venue_fit_delta,VenueDNA_venue_history_delta,VenueDNA_penalties_total,
VenueDNA_confidence_band,
VenueDNA_primary_case,VenueDNA_key_risk,VenueDNA_failure_condition,VenueDNA_conviction,
VenueDNA_trait_approach,VenueDNA_trait_long_iron_150_225,VenueDNA_trait_total_driving,
VenueDNA_trait_par5_scoring,VenueDNA_trait_easy_green_putting,VenueDNA_trait_course_history,
anti_pattern_flags,risk_flags,tags,
r1_tee_time,r1_wave,r1_start_hole,r2_tee_time,r2_wave,r2_start_hole,
DG_finalprediction_benchmark,DG_stddev_benchmark,DG_coursefittotaladj_benchmark
```

### 3C. {slug}_player_briefs.json

Path: `events/{slug}/output/{slug}_player_briefs.json`

Structure: JSON object keyed by normalized `"Last, First"` player name.

**Required keys per player object:**
```json
{
  "player_name":              "Scheffler, Scottie",
  "VenueDNA_rank":            1,
  "VenueDNA_tier":            "T1",
  "summary_label":            "Elite approach precision + par-5 power",
  "why_it_fits_structurally": "...",
  "exact_mechanism":          "...",
  "key_risk_vector":          "...",
  "named_failure_condition":  "...",
  "conviction_level":         "high",
  "penalty_context":          "none" ,
  "venue_history_context":    "...",
  "debut_context":            "not_applicable",
  "official_model_status":    "VenueDNA_authority",
  "tags":                     ["T1", "approach_elite"],
  "anti_pattern_flags":       [],
  "benchmark_context":        "DG_finalprediction_benchmark: 2.827"
}
```

`conviction_level`: `"high"` / `"medium"` / `"low"` / `"unknown"`
`debut_context`: `"not_applicable"` / `"debut_no_similar_course_data"` / text description
`official_model_status`: always `"VenueDNA_authority"` (never DG)

### 3D. {slug}_event_payload.json

Path: `events/{slug}/output/{slug}_event_payload.json`

**Required top-level keys:**
```json
{
  "schema_version":        "1.1",
  "generated_at":          "<ISO 8601 UTC>",
  "event_metadata":        {},
  "venue_lock":            {},
  "conditions":            {},
  "scoring_metadata":      {},
  "official_model":        {},
  "benchmark_model":       {},
  "five_tier_projection":  {},
  "tier_1_briefs":         [],
  "tier_2_briefs":         [],
  "anti_pattern_flags":    [],
  "risk_register":         {},
  "probability_view":      {},
  "model_council_findings":{},
  "source_manifest":       {},
  "deploy_manifest":       {},
  "blockers":              []
}
```

**Hard rules for event_payload.json:**
- `official_model.official_rank_driver` must equal `"VenueDNA_final_projection"`
- `benchmark_model.use_restrictions` must state: `"DG fields are read-only benchmark context and do not determine official ranks, tiers, or projections"`
- `blockers` must list every missing file, field, or schema gap discovered during the build
- If a field value is unknown, write `"unknown"` — never invent a value

### 3E. {slug}_links.json

Path: `events/{slug}/output/{slug}_links.json`

**Structure:**
```json
{
  "schema_version": "1.1",
  "event": "2026 3M Open",
  "links": [
    {
      "player_name": "...",
      "link_type":   "official_bio|tournament_history|sg_profile",
      "url":         "...",
      "label":       "...",
      "source":      "PGA Tour|DataGolf|FantasyPros"
    }
  ]
}
```

---

## 4. DEPLOY DATA CONTRACTS

Files copied from `output/` to `deploy/data/`:
```
{slug}_event_payload.json   → deploy/data/{slug}_event_payload.json
{slug}_vts_full.csv         → deploy/data/{slug}_vts_full.csv
{slug}_player_briefs.json   → deploy/data/{slug}_player_briefs.json
{slug}_links.json           → deploy/data/{slug}_links.json
```

`deploy/data/board_export.json` is written directly by `engine/enrich_cards.py`. It is not a copy of any output file — it is the primary runtime UI payload.

---

## 5. AUDIT PLACEHOLDER CONTRACTS

```
events/{slug}/audit/{slug}_r1_diagnostics.json   ← populated after R1
events/{slug}/audit/{slug}_audit_log.json        ← running build log
events/{slug}/audit/{slug}_council_review.md     ← council synthesis (markdown)
```

Pre-tournament: all audit files are placeholders with `"status": "pending"`.

---

## 6. UNKNOWN VALUE POLICY

| Situation                      | Write            |
|--------------------------------|------------------|
| Player not in source CSV       | `"unknown"`      |
| Field not computable           | `"unknown"`      |
| Boolean flag not evaluable     | `"unknown"`      |
| Numeric trait not scorable     | `"unknown"`      |
| DG field missing for player    | `"unknown"`      |

Never write `null`, `NaN`, `undefined`, or empty string for a required field. Always write the string `"unknown"`.

---

## 7. SCHEMA MISMATCH REPORTING

Any discovered mismatch between expected and actual CSV headers must be logged in `event_payload.blockers` with:
```json
{
  "type": "schema_mismatch",
  "file": "dg_decomposition.csv",
  "expected": "timingadj",
  "actual": "timing_adj",
  "resolution": "mapped timing_adj → DG_timingadj_benchmark"
}
```
