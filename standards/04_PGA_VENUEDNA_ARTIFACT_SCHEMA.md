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
Genuine numeric `0.0` in `total_mean` is valid observed data. `null`, `none`, empty, absent, unparseable, or otherwise unavailable `total_mean` values remain missing and must not be silently converted to numeric zero. Represent unavailable values using the schema's applicable missing-value convention (`null` for optional JSON scalars, blank or documented null-equivalent for CSV numeric fields, or `"unknown"` where this schema requires that string for a required field). Missingness may affect eligibility, confidence, completeness, or layer-specific fallback rules, but must not masquerade as observed zero performance.

A present similar-course row with `rounds_played: 0` is a distinct DEBUT observation when `total_mean` is finite or when it retains a documented source-native null sentinel (`null`, `NULL`, or an empty source cell under the normalized missing-value convention). The null remains null; it is not observed zero and is never converted to numeric `0.0`. A missing source row, a positive-round row with null/blank/malformed/non-finite `total_mean`, or a zero-round row with malformed/non-finite non-null `total_mean` is incomplete evidence, not DEBUT. Likewise, formula-v2.0.0's neutral `VenueHistoryDeltaRaw = 0.0` is an explicit canonical contribution pending an approved bounded history transform; it is not raw-history zero filling. Any zero-filling in historical production behavior is legacy nonconforming implementation behavior only.

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

### 3E. Detailed Live Artifact Interface Authority (Decision D)

This standard is the canonical detailed, versioned-interface authority for
round-analysis (`rN_analysis`), final-analysis, and `cumulative_learning` artifact
types. Each type is independently versioned; a future versioned migration must
declare its own required and optional fields, nesting, missing-value behavior,
producer obligations, compatibility policy, and consumer validation.

The generic Live Artifact envelope in `docs/data_contracts.md` is an abstract
interface class, not a requirement that these detailed artifact types directly emit
one shared top-level JSON shape. A future consumer that requires that generic
envelope must use an explicitly versioned adapter/wrapper or an approved producer
change. This authority assignment does not create either mechanism, select
field-level content, select a current schema-version compatibility policy, or alter
any current producer output.

Current producer payloads and the README-linked
`library/engine/ROUND_ANALYSIS_SCHEMA.md` remain compatibility evidence pending a
separately authorized versioned migration. Archived consumers are evidence only and
cannot establish present consumer compatibility or adapter requirements.

---

### 3F. Detailed Round, Final, and Cumulative Interface Policy

This section is the canonical detailed-interface policy for the three Live Artifact
families below. They remain beneath the abstract Live Artifact envelope in
`docs/data_contracts.md`; that envelope does not require a shared producer wire
format. This policy does not create a typed contract, adapter/wrapper, producer
change, migration, deploy change, or README/library transition.

The general schema-version policy in §1 applies within each artifact family. It does
not require independently versioned families in this section to use the same version
identifier. No new schema-version identifier is selected here. The current producer
versions are compatibility baselines only: round/final output is currently `"1.1"`
and cumulative-learning state is currently `"1.0"`.

#### 3F.1 Family boundary and authority

| Family | Detailed interface role | Current compatibility locations |
|---|---|---|
| `rN_analysis` | One detailed round-analysis family for R1 through R4. | `events/{slug}/output/{slug}_r{N}_analysis.json`; `events/{slug}/deploy/data/r{N}_analysis.json` |
| `final_analysis` | An independently versioned terminal-analysis family. It is not an alias for `r4_analysis`, even though the current producer constructs it from the same base payload. | `events/{slug}/output/{slug}_final_analysis.json`; `events/{slug}/deploy/data/final_analysis.json` |
| `cumulative_learning` | An independently versioned, persistent state document, not a collection of interchangeable round artifacts. | `events/{slug}/output/{slug}_cumulative_learning.json`; `events/{slug}/deploy/data/cumulative_learning.json` |

This standard owns the detailed fields, types, nesting, requiredness,
source-contingent missing behavior, family versions, compatibility/deprecation and
translation rules, producer obligations, and consumer-validation requirements for
these families. `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` owns cadence,
interpretation, audit, Council, and write-back behavior. `docs/data_contracts.md`
owns the producer-consumer boundary, immutable pre-event spine, abstract envelope,
and general JSON rules.

#### 3F.2 Member-treatment vocabulary

Every detailed member in this section is classified as one of the following:

| Treatment | Rule |
|---|---|
| Required | Always present with the specified type/shape. |
| Optional but stable | May be absent only where this section says so; its name, type, and meaning are compatibility commitments when present. |
| Source-contingent | Presence or value depends on documented input evidence. Unavailable optional scalars use `null`, no-result collections use `[]`, and an unavailable tagged object uses its declared `available: false` form. A member is absent only where this section expressly permits absence. |
| Legacy compatibility member | A current member whose name or shape is preserved for compatibility pending an approved replacement/deprecation window. |
| Unresolved | No field-level choice is made. A later explicit decision is required before a producer or consumer change. |

#### 3F.3 `rN_analysis` interface

R1 through R4 share one detailed `rN_analysis` version line. The required integer
`round` and stable metadata identify the round instance. A future split is allowed
only when a round requires a different required member, type, nesting,
missing-value rule, or consumer obligation that cannot be represented as an optional
stable or source-contingent member without obscuring meaning. Different source
values, an event condition, or a new optional diagnostic do not by themselves justify
a version-line split.

| Member or member group | Treatment | Detailed policy |
|---|---|---|
| `schema_version`, `generated_at`, `build_timestamp`, `round`, `event_slug` | Required | Top-level metadata. `round` is an integer. A later versioned contract must specify timestamp representation without changing the current baseline by implication. |
| `enrichment_used`, `course_insights_loaded`, `round_sources` | Required | The first two are booleans. `round_sources` is an array of source identifiers. |
| `metadata` | Required object | Required members: `event_name`, `course_name`, `par`, `round_label`, `is_final`, `is_full_tournament`, `favored_wave`, `wx_speed_kts`, `wx_direction`, `wx_wave_delta`, and `wx_tide`. Current unknown weather direction/tide use `"N/A"`; their detailed domains remain a compatibility commitment pending later refinement. |
| `enrichment_summary` | Source-contingent | Always present as either `null` when course insights are unavailable/unmatched, or an object with `source`, `player_match_n`, `player_total`, `traits_upgraded`, and `traits_confirmed`. |
| `live_lean_notes` | Required object | Required members: `round`, `next_round`, `lean_up_traits`, `lean_down_traits`, `putt_caution`, `putt_outliers`, `watch_next_round`, `wave_risk_annotation`, `wave_scoring_averages`, and `rho_note`. `next_round` is `null` for final state; no-result collections are `[]`. Conditions-specific lean records may add optional-stable members such as `multiplier`. |
| `match_summary` | Required object | Required members: `matched`, `total_r1`, `unmatched`, and `match_rate_pct`. `unmatched` is `[]` when empty. `total_r1` is a legacy compatibility member, including outside R1. |
| `model_performance` | Required object | Required `spearman_rho` and `groups`. `groups` has fixed current keys `pt_top10`, `pt_top20`, `tier1`, `tier2`, `tier1_2`, and `all_field`; each has `n`, `avg_r1_pos`, `avg_r1_score`, `in_r1_top10`, and `in_r1_top20`. The `r1`-prefixed group names are legacy compatibility members. |
| `sg_leader_averages` | Required object | Required `top10`, `top18`, and `full_field` SG maps. Their SG scalar values are source-contingent and may be `null`. |
| `trait_audit` | Required object | All ten canonical trait keys are required, including padded not-testable entries. Per-trait base members are `venue_weight`, `top10_trait_avg`, `field_trait_avg`, `trait_delta`, `sg_proxy`, `sg_top10`, `sg_field`, `sg_delta`, `signal`, `sample_n_top10`, `sample_n_field`, `source_confidence`, and `enrichment`. Evidence scalars may be `null`; padded entries retain their current zero/null/not-testable behavior. |
| `trait_audit[*].enrichment` | Source-contingent tagged object | The member is present. Unavailable form is `{ "available": false, "reason": "..." }`; available form carries its primary/secondary values and signal fields. Do not substitute `null` for this tagged-object state. |
| `trait_audit[*].brie_z` | Source-contingent absent member | Present only when the applicable trait/source provides it. Its failure form remains an object with `available: false`, current nested version evidence, and `error`; successful form carries availability, counts, averages, penalty, and note evidence. |
| `trait_audit[*]` live-proxy and upgrade detail | Source-contingent absent/null members | `proxy_source`, `live_proxy_label`, `live_proxy_top10_avg`, `live_proxy_field_avg`, and `signal_upgraded_by_enrichment` remain optional source evidence. `proxy_source` is `null` when the live source is absent; upgrade flag is absent unless an upgrade occurs. |
| `risers`, `slippage`, `weekend_risers`, `slippage_risk` | Required arrays | No-result behavior is `[]`. Item base members are source-contingent joined-record fields. `weekend_risers` may add `thesis_score`/`thesis_note`; `slippage_risk` may add `risk_flags`. |
| `leaderboard_snapshot` | Required array | Each record retains current identity, position, pre-event, SG, and wave evidence when available. `player_id` and `vs_proj` may be `null`. `r1_name`, `wave`, and `wave_penalty` are current consumer compatibility evidence. |
| `leaderboard_snapshot[*]` live extensions | Optional but stable | `live_win_pct`, `live_top5_pct`, `live_top10_pct`, `live_top20_pct`, `v_p_t`, `cumulative_sg_tot`, `wave_draw`, and `wave_penalty` retain their current meanings; unavailable numeric values may be `null`. |
| `dimension_leaders` | Required object | Fixed SG keys `sg_app`, `sg_putt`, `sg_ott`, and `sg_arg`; each maps to an array, possibly `[]`, of current leader records. |
| `live_probability_engine` | Required compatibility object | Required current members are `round`, `gamma`, `field_vts_mean`, `field_avg_cum_sg`, `temperatures`, `prior_rounds_used`, `population_anchor_size`, `active_field_size`, `eliminated_frozen_count`, and `wave_penalty_params`; the latter retains its current parameter members. Exact scalar domains are unresolved pending a later explicit decision. |
| `course_stats`, `easiest_holes`, `hardest_holes` | Required source-contingent arrays | Each is `[]` when course-stat input is absent. When present, course-stat records retain current hole, par, yardage, scoring, and result fields. |

#### 3F.4 `final_analysis` terminal interface

`final_analysis` is independently versioned because it is the terminal family, even
though its current producer reuses the `rN_analysis` construction. Unless and until a
later detailed decision states otherwise, all `rN_analysis` member treatments apply
to the current final baseline, plus these required terminal metadata rules:

| Member | Treatment | Rule |
|---|---|---|
| `round` | Required | Must be integer `4`. |
| `metadata.is_final` | Required | Must be `true`. |
| `metadata.is_full_tournament` | Required final-family discriminator | Must be `true` for `final_analysis`; current `r4_analysis` retains `false`. |
| `metadata.round_label` | Legacy compatibility member | Current final value is `"Final Tournament"`; current R4 value is `"Final Round"`. Preserve both until a later vocabulary decision. |
| Final-only summary/audit members | Unresolved | `standards/03` describes final analytical purpose but does not select detailed placement. This section does not add terminal-only summary, audit, or cross-reference members. |

The current R4-parity boundary is exact: current final output has the same base shape
as current round output except filename/location and
`metadata.is_full_tournament`/`metadata.round_label`. Whether future final analysis
must retain full shape parity, require terminal-only summaries, or reference a
separate audit artifact is unresolved and requires a later explicit decision.

#### 3F.5 `cumulative_learning` state interface

`cumulative_learning` is a persistent state document. Its compatibility obligations
include initialization and read/update/write behavior, not only JSON member shape.

| Member or behavior | Treatment | Rule |
|---|---|---|
| `schema_version`, `event_slug`, `created_at`, `per_round`, `cumulative_signals` | Required initialization members | A fresh state begins with these members. `per_round` is an object and `cumulative_signals` contains the canonical trait state records. |
| Read precedence | Required state behavior | Read existing output state first; if absent, read deploy fallback; if both are absent, initialize fresh state. A future change must preserve or explicitly replace this precedence. |
| `last_updated`, `updated_at`, `rounds_completed`, `is_final`, `rounds_present` | Required persisted members | Update on every write. `rounds_present` is a sorted unique integer history; `is_final` records terminal state. |
| `per_round["N"]` | Required processed-round entry | Each processed round entry has `round`, `generated_at`, `spearman_rho`, `trait_signals`, `model_hits`, `risers`, `slippage`, and `wave_annotation_n`. Riser/slippage are `[]` when empty. |
| `per_round[*].trait_signals[*]` | Required per observed canonical trait | Required members are `signal`, `source_confidence`, `trait_delta`, `sg_delta`, and `enrichment_signal`; evidence scalar values may be `null`. |
| `per_round[*].model_hits` | Required | Retains `pt_top10_in_top10`, `pt_top10_in_top20`, and `tier1_2_in_top20`. The `r1`-prefixed source terminology is legacy compatibility semantics. |
| `cumulative_signals[*]` | Required canonical trait state | Required members are `rounds_observed`, `signal_history`, `confidence_history`, `delta_history`, `consensus`, and `consensus_confidence`. Fresh consensus values are `null`; after update, consensus values are the latest corresponding history values. |
| Reprocessed round | Required update behavior | If a round is already observed, replace its history values at that existing index rather than append duplicates. |
| Final state | Required terminal behavior | Terminal state sets `is_final: true`, terminal `rounds_completed`, and persists the terminal-round snapshot. Whether final analysis links, embeds, or only coexists with state is unresolved. |
| State upgrade | Required migration prerequisite | No unversioned in-place reinterpretation is allowed. A future versioned migration must specify source-version detection, version-dispatched upgrade/translation, history preservation or deterministic reconstruction, idempotence/retry, and validation before write. No upgrade mechanism is created here. |

#### 3F.6 Independent compatibility policy

| Policy | Rule |
|---|---|
| Non-breaking | Add a documented optional-stable member with exact absent/null/empty behavior, or clarify prose without semantic change. For cumulative state, old state must remain valid and read/update results unchanged. |
| Breaking | Removing, renaming, retyping, moving/nesting, changing requiredness, enum semantics, or null/empty/absent behavior of a compatibility member is breaking. For final it also includes changing terminal/R4 discriminators; for cumulative it also includes read precedence, keying, histories, consensus derivation, or update behavior. |
| Deprecation | Retain the legacy member during an approved compatibility window, document a replacement mapping, and validate selected non-archived consumers. Cumulative deprecation must not silently discard history. |
| Translation | A translator/adapter requires an explicitly versioned source/target mapping and a verified consumer or approved migration need. A cumulative translator must be idempotent, preserve or deterministically reconstruct history, and validate before persistence. |
| Future migration prerequisites | Freeze current producer field inventory and representative samples; identify non-archived consumers; approve detailed contract/test/producer scope; settle final-versus-R4 parity; and, for cumulative state, validate fresh initialization, output/deploy fallback, repeated-round update, partial history, terminal state, and version upgrade. |

#### 3F.7 Consumer, typed-contract, and adapter boundaries

Current producer payloads, the README-linked
`library/engine/ROUND_ANALYSIS_SCHEMA.md`, non-archived validators/shims, and
non-archived runtime/template consumers remain compatibility evidence. They do not
authorize changing producer output or deprecating the library/README reference. Any
future preservation, transition, or deprecation requires an approved complete
detailed replacement, resolved producer/documentation deltas, explicit disposition of
each non-archived consumer/template, compatibility validation, and a separately
authorized README/library task.

`standards/VENUEDNA_CODEX_SCHEMA.md` may later mirror this detailed authority only
after fields, types, enum/null behavior, final discriminator, cumulative
state/update/upgrade rules, naming, and validation cases are approved. No typed
definition is established here.

**NO ADAPTER CURRENTLY JUSTIFIED.** No verified non-archived runtime consumer
requires the abstract envelope as an actual JSON boundary. A future adapter/wrapper
requires an explicit versioned contract and either verified consumer need or approved
producer change. This section designs and creates neither.

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

---

## 8. VENUE INTELLIGENCE ARTIFACTS

### 8A. {venue_slug}_intelligence_{year}_v{n}.json

Path: `library/venues/{venue_slug}/{venue_slug}_intelligence_{year}_v{n}.json`

First introduced: `detroit_golf_club_intelligence_2026_v1.json` (2026 Rocket Classic)

**Required top-level keys:**
```json
{
  "venue":                  "Detroit Golf Club",
  "venue_slug":             "detroit_golf_club",
  "season":                 2026,
  "schema_version":         "venue-intelligence-v1",
  "governance_version":     "v1",
  "generated_at":           "<ISO 8601 UTC>",
  "frozen_payload_policy":  "READ_ONLY",
  "scoring_rebuild_required_for_changes": true,
  "dominant_tripod":        {},
  "dominant_tripod_governance": {}
}
```

**`dominant_tripod` block:**
```json
{
  "label":          "Detroit Tripod",
  "scoring_impact": "NONE",
  "components": [
    { "trait": "sg_approach",   "weight": 0.40, "source_label": "SG: Approach",  "availability_field": "trait_approach_raw" },
    { "trait": "app_150_200",   "weight": 0.25, "source_label": "App 150-200",   "availability_field": "trait_long_iron_raw" },
    { "trait": "total_driving", "weight": 0.20, "source_label": "Total Driving", "availability_field": "ott_true" }
  ],
  "subset_weight_total": 0.85,
  "eligibility_gate":    "usable_for_badges"
}
```

**`dominant_tripod_governance` block:**
```json
{
  "status":      "NOT_ACTIVE",
  "description": "Proposed V2 enhancement — documented for future governance only",
  "effect_on_current_ranks":         "NONE",
  "effect_on_current_tiers":         "NONE",
  "effect_on_current_probabilities": "NONE"
}
```

**Hard rules:**
- `dominant_tripod.scoring_impact` must always equal `"NONE"` until a formal V2 governance vote is recorded
- `dominant_tripod_governance.status` must be `"NOT_ACTIVE"` until explicitly activated by the council
- This file is documentation only; it never affects VTS scores, tiers, or probabilities

---

## §3F. {slug}_tripod_audit.json (READ_ONLY_AUDIT_COMPANION)

Path: `events/{slug}/output/{slug}_tripod_audit.json`
Deploy copy: `events/{slug}/deploy/data/{slug}_tripod_audit.json`

First introduced: `2026_rocket_classic_tripod_audit.json`

**Purpose:** Analytical enrichment layer joined to the frozen event payload by `player_id`. Does not modify, recompute, or replace any field in the frozen payload. Zero impact on ranks, tiers, VTS, or probabilities.

**Required top-level keys:**
```json
{
  "metadata":               {},
  "percentile_thresholds":  {},
  "players":                []
}
```

**`metadata` required fields:**
```json
{
  "artifact_type":           "READ_ONLY_AUDIT_COMPANION",
  "scoring_effect":          "NONE",
  "tier_effect":             "NONE",
  "probability_effect":      "NONE",
  "source_payload":          "{slug}_event_payload.json",
  "source_payload_schema":   "<schemaVersion from payload>",
  "source_payload_hash":     "<SHA-256 hex of frozen payload>",
  "join_key":                "player_id",
  "field_size_expected":     147,
  "frozen_output_preserved": true,
  "v2_governance_status":    "NOT_ACTIVE",
  "v2_governance_note":      "PROPOSED_V2 rules have zero effect on current ranks, tiers, VTS, and probabilities."
}
```

**Per-player record fields:**

| Field | Type | Notes |
|---|---|---|
| `player_id` | string | Join key — must match frozen payload |
| `tripod_eligibility` | `"ELIGIBLE"` \| `"UNAVAILABLE"` | Determined by `usable_for_badges` gate on all three components |
| `tripod_qualified` | bool \| null | True if all 3 components ≥ 60th percentile; null if UNAVAILABLE |
| `tripod_supported` | bool \| null | True if weighted score ≥ 65th percentile AND ≥ 2/3 components qualify; null if UNAVAILABLE |
| `component_percentiles` | object \| null | `{sg_approach, app_150_200, total_driving}` — present for ELIGIBLE only |
| `weighted_tripod_score` | float \| null | `(sg*0.40 + app*0.25 + drv*0.20) / 0.85`; null if UNAVAILABLE |
| `weighted_tripod_percentile` | float \| null | Percentile within eligible pool; null if UNAVAILABLE |
| `recent_form_risk_flag` | bool \| null | True if `true_sg_l20 < 0` for tripod-qualified players; null otherwise |
| `t2g_no_red_flag` | null | Always null — `arg_true` not materialized as numeric field in payload |
| `current_engine_effect` | `"NONE"` | Always `"NONE"` — no scoring effect |
| `proposed_v2_effect` | `"NONE — NOT ACTIVE"` | Always this exact string |
| `source_availability_reason` | string \| null | Populated for UNAVAILABLE players only |
| `audit_interpretation` | string | Human-readable interpretation of tripod status |

**Eligibility gate (per-component, using `trait_availability` metadata):**

```
sg_approach   → trait_availability.trait_approach_raw.usable_for_badges == True
app_150_200   → trait_availability.trait_long_iron_raw.usable_for_badges == True
total_driving → trait_availability.ott_true.usable_for_badges == True
```

All three must be `True` for a player to be ELIGIBLE. UNSCORED players (`data_depth == "UNSCORED"`) are always UNAVAILABLE regardless of availability metadata.

**Percentile pools:** Computed over ELIGIBLE players only. UNAVAILABLE players are excluded from all pools and thresholds.

**Build script:** `events/{slug}/output/build_tripod_audit.py`
**Pre-build validation:** `events/{slug}/output/preflight_check.py`
**Post-build validation:** `events/{slug}/output/validate_tripod_audit.py`
**Sidecar parity verification:** `events/{slug}/output/verify_tripod_audit_parity.py`

**Deploy/sidecar parity contract:**
- When a `deploy/data/` mirror of the audit companion exists, the validated output audit and the deploy copy must have identical SHA-256 hashes before release.
- Deploy copies are read-only mirrors. Verification must not silently rewrite or synchronize them — hash mismatch is a release-blocking artifact-integrity failure and must be investigated manually.
- Run `verify_tripod_audit_parity.py` as part of every release validation sequence.

---

## 9. SOURCE MANIFEST CONTRACT (schema_version 1.0) — Phase 4.1 contract, Phase 4.2 narrow producer integration

**Status: contract canonical since Phase 4.1; a narrow, event-neutral producer integration is implemented as of Phase 4.2.** The resolver/validator at `engine/source_manifest_resolver.py` (Phase 4.2, standalone, no event/producer dependency) and its integration into `engine/enrich_cards.py`'s path-binding step (also Phase 4.2) both exist. After `EventContext` validation and the existing capability gate (`require_supported_context()`, still scoped to `2026_3m_open` / `tpc_twin_cities`, unchanged by this integration) succeed, `engine/enrich_cards.py` reads and JSON-decodes a `source_manifest.json` at the active event's own `input/` root (§9.2), resolves it via `resolve_source_manifest()`, and binds every one of the thirteen required logical source roles (§9.5) to its manifest-declared physical path — never a hardcoded physical filename (`ALL_COURSES_FILES`, `SIM_COURSES_FILES`, `tpc_twin_cities_CH.csv`, etc., which remain defined only as historical/illustrative reference, per `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §2A) and never a filename inferred, constructed, or guessed from `event_slug`/`venue_slug`. A missing manifest, unreadable manifest, invalid JSON, non-object JSON root, or any resolver blocker fails release before any source file is opened, before identity resolution, before scoring, and before output/deploy directory creation or any write. This integration changes no payload shape, `schemaVersion`, deploy filename, formula metadata, rank, tier, probability, penalty, gate, or scoring rule; creates no real `source_manifest.json` instance under any event directory (synthetic instances exist only inside `tests/test_enrich_cards.py`'s `tmp_path` fixtures); and does not generalize this producer to another event or venue — the capability gate above still fails a mismatched event/venue before source-manifest lookup is ever attempted. The physical input-file references in `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §2 remain accurate, current documentation of the historical export shape. Reconciling this contract with either pre-existing use of the term "source_manifest" (below) remains a separately authorized, still-deferred decision — not resolved by this integration.

**Naming note — do not confuse with two pre-existing, unrelated uses of "source_manifest":**
1. This document's own §3D lists a `"source_manifest": {}` key inside the aspirational `{slug}_event_payload.json` *output* shape. That key, if ever implemented, is an output-side summary embedded in the payload. It is not this schema and is not required to have this shape.
2. `engine/build_event_package.py` (a separate, non-`enrich_cards.py` producer) already emits a payload-side `source_manifest` object: a per-literal-hardcoded-filename `"EXISTS"`/`"MISSING"` presence map, assembled in memory and then written verbatim into the `source_manifest` key of its own output `{slug}_event_payload.json` (the same key named in §3D above). It carries no logical role, identity, encoding, integrity, or provenance metadata, is keyed by literal filename rather than logical role, and is not this schema.

Reconciling either of those with this schema is an explicitly deferred, separately-authorized decision — not resolved here.

### 9.1 Purpose

A `source_manifest` maps event-neutral **logical source roles** (what the scoring pipeline needs) to **physical event input files** (what a specific event's DataGolf/manual export happens to be named). Physical filenames are event-specific and historically accreted ad hoc (`pga_sg_query_3Mopen_similar_l6.csv`, `tpc_twin_cities_CH.csv`); logical roles are not. A source manifest is the seam a future producer would read instead of a hardcoded filename dict, without requiring every event's exports to share one venue's naming convention.

### 9.2 Location (approved default; no instance authorized)

```text
events/{event_slug}/input/source_manifest.json
```

This is the sole location `engine/enrich_cards.py` reads after Phase 4.2's integration — derived directly from `EventContext.event_root / "input"`, with no `config/active_event.json` pointer field, no CLI argument, and no fallback location. No file of this name may be created under any real `events/` directory by this contract or by the Phase 4.2 integration. Creation of an actual manifest instance for a real event remains a separate, explicitly authorized step.

### 9.3 Top-level shape

```json
{
  "schema_version": "1.0",
  "event_slug": "2026_3m_open",
  "venue_slug": "tpc_twin_cities",
  "as_of": "2026-08-05T00:00:00Z",
  "sources": []
}
```

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | Exactly `"1.0"` for this contract. |
| `event_slug` | string | Lowercase snake_case. Must equal the active `EventContext.event_slug` at build time (Rule 4). |
| `venue_slug` | string | Lowercase snake_case. Must equal the active `EventContext.venue_slug` at build time (Rule 4). |
| `as_of` | string | ISO 8601 UTC timestamp of manifest authoring — diagnostic provenance only, never a freshness gate on its own. |
| `sources` | array | One entry per physical input file declared below. |

### 9.4 Source entry shape

```json
{
  "role":              "venue_fit.similar_sg.6m",
  "path":              "pga_sg_query_3Mopen_similar_l6.csv",
  "required":          true,
  "missing_behavior":  "block_release",
  "schema_id":         "venuedna.source.sg_total_horizon.v1",
  "identity_key":      "player_name",
  "encoding":          "utf-8",
  "sha256":            null,
  "row_count":         null,
  "metadata": {
    "similar_course_set_id": "tpc_twin_cities_similar_v1",
    "set_version":            1,
    "set_provenance":         "manual_datagolf_export_2026",
    "horizon_months":         6
  }
}
```

| Field | Type | Rule |
|---|---|---|
| `role` | string | One of the required logical roles (§9.5) or a documented additional role. Unique within `sources` (Rule 5). |
| `path` | string | Relative to `events/{event_slug}/input/` (Rule 2). Never absolute, never containing a backslash, never containing `..`, never containing an archived/finished-event path segment (Rule 3) — checked lexically before resolution, then again on the resolved path. The resolved target must additionally be a regular file that stays inside `EventContext.event_root / "input"` specifically (not merely somewhere inside the repository) — validated with the same path-safety approach `engine/event_context.py` already applies to manifest path fields (`resolve()` + `relative_to()`, never string prefixes), extended with this schema's own source-file containment root. A resolved target reached through a symlink or filesystem junction is rejected on the same basis as `engine/event_context.py` already rejects one for its own manifest fields: containment is checked against the resolved physical path, never the declared textual path alone. |
| `required` | boolean | `true` when the pipeline cannot produce a valid scored record for the affected layer without this source. |
| `missing_behavior` | string enum | `"block_release"` \| `"neutral_skill_horizon_incomplete"` \| `"venue_fit_horizon_incomplete"` \| `"venue_history_missing"` \| `"widen_confidence"` \| `"skip_layer"` \| `"warn_only"`. Each of the thirteen required logical roles (§9.5) has exactly one permitted `required`/`missing_behavior` combination, fixed by the table in §9.5A — it is not an open per-event choice. `"skip_layer"` and `"warn_only"` are reserved for a documented additional role beyond the thirteen; neither is permitted for any of the thirteen, because neither maps to a defined `standards/02` §7.5 outcome and both risk implying an unauthorized cross-layer or core-rank effect. Every label in this enum is a documentation pointer that delegates its actual effect to `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §7.5 — this schema defines no missing-data arithmetic of its own. |
| `schema_id` | string | Versioned identifier for this source's expected row/column shape, so a future column-shape change can be detected without renaming the manifest itself. |
| `identity_key` | string enum | `"dg_id"` \| `"player_name"` \| `"dg_id+player_name"` — declares which identity column(s) this physical source actually carries. Documentation only; does not alter `engine/identity_resolver.py`'s resolution precedence (Rule 11). |
| `encoding` | string | `"utf-8"` or `"utf-8-sig"`, matching the CSV Rules already declared in `docs/data_contracts.md`. |
| `sha256` | string \| null | `null`, or a lowercase 64-character hexadecimal SHA-256 digest of the exact physical file bytes. A non-null value is a declared integrity assertion: a future validator must independently compute this digest over the physical regular file's raw bytes and require an exact match; any mismatch is a release-blocking validation failure, not a warning. `null` means the assertion was not supplied — it is neither a pass nor a failure and must be reported as `not_asserted` (§9.4A), never a validated success. A validator is read-only with respect to this field: it must never write, normalize, replace, infer, or backfill a `sha256` value into the manifest, consistent with the existing deploy-profile integrity convention in `docs/data_contracts.md`. A source file that cannot be read or hashed is a release-blocking validation failure (`unable_to_validate`, §9.4A) — never treated as null-equivalent or silently skipped. No validator exists yet — this row defines future validation semantics only. |
| `row_count` | integer \| null | `null`, or a non-negative integer count of data rows in the physical file, excluding the header row. A non-null value is a declared integrity assertion: a future validator must independently count the physical file's data rows deterministically, under this entry's declared `encoding`, and require an exact match against the supplied value; any mismatch is a release-blocking validation failure, not a warning. A blank line counts as a data row; `row_count` asserts row cardinality, not row-shape validity, so a row that is malformed relative to this entry's `schema_id` is still counted, never dropped or estimated. `null` means the assertion was not supplied — it is neither a pass nor a failure and must be reported as `not_asserted` (§9.4A), never a validated success. A validator is read-only with respect to this field: it must never write, normalize, replace, infer, or backfill a `row_count` value into the manifest. A source file that cannot be read or counted is a release-blocking validation failure (`unable_to_validate`, §9.4A) — never treated as null-equivalent or silently skipped. No validator exists yet — this row defines future validation semantics only. |
| `metadata` | object | Free-form, source-specific. Must never contain an API credential or secret key of any kind (Rule 12). Required sub-fields for specific roles are listed in §9.5/§9.6. |

### 9.4A Integrity assertion validation semantics

`sha256` and `row_count` are independent, optional integrity assertions on one source entry. Neither field's presence or absence is a `required`/`missing_behavior` outcome under §9.5A — that table governs source *presence*, not integrity *verification*, and the two are not the same concern.

A future validator must report each field's outcome as exactly one of these four states — no other value is valid:

| State | Meaning |
|---|---|
| `verified` | A non-null value was supplied and the validator's independently computed value matched it exactly. |
| `mismatch` | A non-null value was supplied and the validator's independently computed value did not match it. Release-blocking. |
| `not_asserted` | The field was `null`. No assertion was supplied; the validator performed no comparison. Never reported as `verified`. |
| `unable_to_validate` | The source file could not be read, opened, hashed, or parsed for row counting, regardless of whether `sha256`/`row_count` was supplied. Release-blocking. |

A validator defined against this contract is read-only with respect to `sha256` and `row_count`: it must never write, normalize, replace, infer, or backfill either field's value in the manifest, whether the prior value was `null`, correct, or stale. Detecting and reporting a mismatch or an unreadable file is the validator's entire responsibility toward these two fields; correcting the manifest is a separate, human-authored edit outside validation.

No validator exists yet — this subsection defines future validation semantics only, consistent with §9.1's contract-only status.

### 9.5 Required logical roles

Every valid `source_manifest` must declare exactly these thirteen roles (each `required: true` unless the event's own scoring depth genuinely cannot supply it, per Rule 9):

```text
field
neutral_skill.sg_total.6m
neutral_skill.sg_total.12m
neutral_skill.sg_total.24m
venue_fit.similar_sg.6m
venue_fit.similar_sg.12m
venue_fit.similar_sg.24m
traits.approach.sg_per_shot.12m
traits.approach.proximity.12m
performance.sg_categories.season
benchmark.decomposition
venue_history
recent_form.trending
```

Illustrative (non-authoritative, backward-compatibility-only) mapping of these roles onto the current archived `2026_3m_open` input files, shown to prove the thirteen roles are sufficient to describe the current producer's actual inputs without inventing a new one:

| Role | Current physical file (`events/2026_Finished_Events/2026_3m_open/input/`) |
|---|---|
| `field` | `pga_field.csv` |
| `neutral_skill.sg_total.6m` | `pga_sg_query_allcourses_l6.csv` |
| `neutral_skill.sg_total.12m` | `pga_sg_query_allcourses_l12.csv` |
| `neutral_skill.sg_total.24m` | `pga_sg_query_allcourses_l24.csv` |
| `venue_fit.similar_sg.6m` | `pga_sg_query_3Mopen_similar_l6.csv` |
| `venue_fit.similar_sg.12m` | `pga_sg_query_3Mopen_similar_l12.csv` |
| `venue_fit.similar_sg.24m` | `pga_sg_query_3Mopen_similar_l24.csv` |
| `traits.approach.sg_per_shot.12m` | `app_skill_l12_sg.csv` |
| `traits.approach.proximity.12m` | `app_skill_l12_prox.csv` |
| `performance.sg_categories.season` | `dg_performance_2026.csv` |
| `benchmark.decomposition` | `dg_decomposition.csv` |
| `venue_history` | `tpc_twin_cities_CH.csv` |
| `recent_form.trending` | `pga_field_trending_table.csv` |

This table is documentation evidence only. No file named `source_manifest.json` may be added to this or any other event directory as part of this contract phase, and none of the listed archived physical files may be renamed, copied, or moved.

### 9.5A Deterministic role contract — required and missing_behavior

Every logical role's `required` value and `missing_behavior` value are fixed by this table, not chosen per event or per manifest author. The "§7.5-delegated outcome" column restates the controlling rule already stated in `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §7.5; this table creates no new scoring rule, changes no missing-data arithmetic, and authorizes no scorer change.

| Logical role | `required` | `missing_behavior` | §7.5-delegated outcome |
|---|---|---|---|
| `field` | `true` | `block_release` | No field roster, no build. Release blocks before identity resolution or any artifact write. |
| `neutral_skill.sg_total.6m` | `true` | `neutral_skill_horizon_incomplete` | This source's own absence never blocks release by itself and is never treated as numeric zero. Per §7.5, whether the player can still be scored is a NeutralSkill-composite-level determination: with two valid horizons, the missing horizon is omitted and the remaining weights renormalize within NeutralSkill; with fewer than two valid horizons, the player is `UNSCORED`. |
| `neutral_skill.sg_total.12m` | `true` | `neutral_skill_horizon_incomplete` | Same §7.5 composite-level rule as the 6m entry above. |
| `neutral_skill.sg_total.24m` | `true` | `neutral_skill_horizon_incomplete` | Same §7.5 composite-level rule as the 6m entry above. |
| `venue_fit.similar_sg.6m` | `true` | `venue_fit_horizon_incomplete` | VenueFit has a fixed three-horizon formula (§7.5). Incomplete VenueFit evidence is non-computable — never weight-renormalized, never silently converted to a zero `VenueFitDeltaRaw`. A present zero-round row is `DEBUT` only with a finite mean or preserved documented source-native null sentinel; malformed/non-finite values and missing rows remain incomplete. |
| `venue_fit.similar_sg.12m` | `true` | `venue_fit_horizon_incomplete` | Same §7.5 rule as the 6m entry above. |
| `venue_fit.similar_sg.24m` | `true` | `venue_fit_horizon_incomplete` | Same §7.5 rule as the 6m entry above. |
| `venue_history` | `false` | `venue_history_missing` | Missing raw venue-history data remains missing — never synthesized, zero-filled, or marked present. Only `venue_history` confidence may widen (`THIN` below eight relevant starts or when structured evidence is absent, per §7.5). The canonical `VenueHistoryDeltaRaw = 0.0` is a separate, explicit neutral model contribution under §7.5 pending an approved bounded transform — it does not satisfy source presence and does not convert missing evidence into observed data. |
| `traits.approach.sg_per_shot.12m` | `false` | `widen_confidence` | Scoped only to this role's own approach-trait evidence/confidence outcome. Missing optional trait data does not redistribute weight into `NeutralSkillRaw`, `VenueFitDeltaRaw`, or `VenueHistoryDeltaRaw`, and never substitutes for core rank. |
| `traits.approach.proximity.12m` | `false` | `widen_confidence` | Same scoping rule as the row above, limited to this role's own proximity-evidence outcome. |
| `performance.sg_categories.season` | `false` | `widen_confidence` | Scoped only to this role's own performance-context outcome; never redistributed into a scored layer or core rank. |
| `benchmark.decomposition` | `false` | `widen_confidence` | Scoped only to this role's own benchmark-context outcome (DG benchmark fields render `"unknown"` per §6). DG fields remain read-only context under `standards/02` §14 and never determine official rank regardless of this source's presence. |
| `recent_form.trending` | `false` | `widen_confidence` | Scoped only to this role's own recent-form-context outcome; never redistributed into a scored layer or core rank. |

This table is the sole authority for `required`/`missing_behavior` combinations on the thirteen roles. A manifest declaring a different combination for one of these thirteen roles is a release-blocking manifest defect.

### 9.6 Cross-field rules

1. **Physical filenames are arbitrary and never inferred from event names.** A conforming resolver must read `path` literally from the manifest; it must never construct a filename by string-substituting `event_slug` or `venue_slug` into a pattern (the exact defect `SIM_COURSES_FILES`'s `3Mopen`-named literals represent today).
2. **Paths are relative to the active event input directory** (`events/{event_slug}/input/`), never to the repository root or any other directory.
3. **Absolute, traversal, archived, and repository-escape paths are invalid; the resolved target must be a regular file inside the event's own input root.** A conforming resolver must reject `path` under the same path-safety approach `engine/event_context.py` already applies to manifest path fields — no leading `/`, no drive prefix, no backslash, no `..` segment, no `2026_Finished_Events`/`Finished_Events` segment, checked lexically (before resolution) and again on the resolved path (after resolution) — plus this schema's own additional requirement that the resolved target (a) is a regular file, not a directory or other filesystem object, and (b) stays inside `EventContext.event_root / "input"` specifically, not merely somewhere inside the repository. Containment is established with `resolve()` + `relative_to()` against that input root, exactly as `engine/event_context.py` already does against the repository root, so a symlink or filesystem junction that resolves outside `EventContext.event_root / "input"` is rejected on the same basis, not merely on its declared textual path. This is the existing `EventContext` safety approach extended with source-file containment, not a separate path-safety system.
4. **`event_slug` and `venue_slug` must match `EventContext`.** A source manifest's declared `event_slug`/`venue_slug` must equal the values already validated by `engine/event_context.py`'s `EventContext` for the active build; a mismatch is release-blocking, the same way `require_supported_context()` already blocks a mismatched event/venue pairing today.
5. **Logical roles are unique.** Two entries declaring the same `role` in one manifest is a release-blocking manifest defect.
6. **All three similar-course horizons must share one provenance identity and declare their own horizon.** The `metadata` of `venue_fit.similar_sg.6m`, `venue_fit.similar_sg.12m`, and `venue_fit.similar_sg.24m` must each declare `similar_course_set_id`, `set_version`, `set_provenance`, and `horizon_months`. All three entries must declare the identical `similar_course_set_id`, `set_version`, and `set_provenance` — three horizons of one inconsistent similar-course methodology is a data-integrity defect, not three independent choices. `horizon_months` must be an integer equal to `6`, `12`, or `24`, matching that entry's own role suffix (`venue_fit.similar_sg.6m` → `6`, and so on) — a mismatch between `horizon_months` and the role suffix is a release-blocking manifest defect.
7. **`venue_history` metadata must match the active venue.** The `venue_history` entry's `metadata` must carry a `venue_slug` sub-field equal to the manifest's top-level `venue_slug`, exactly. This field is mandatory and deterministic — no alternate or equivalent field is a substitute — so a resolver checks it by direct equality rather than inferring venue identity from prose; a course-history file for the wrong venue must never be silently accepted.
8. **`missing_behavior: block_release` sources block before identity resolution or artifact writes; the six composite-deferred horizon roles resolve at the composite level instead.** For any source whose fixed `missing_behavior` (§9.5A) is `block_release` — currently only `field` — a conforming resolver must stop before `engine/identity_resolver.py` runs and before any output or deploy write, the same fail-closed ordering `engine/event_context.py` already enforces for manifest/context validation. The six `neutral_skill.sg_total.*` and `venue_fit.similar_sg.*` roles are `required: true` but their fixed `missing_behavior` is `neutral_skill_horizon_incomplete` or `venue_fit_horizon_incomplete` (§9.5A), not `block_release`; a single missing horizon among these six does not by itself stop the build — the composite-level §7.5 outcome (renormalize, `UNSCORED`, or non-computable `VenueFitDeltaRaw`) governs instead.
9. **`required: false` sources affect only their own declared confidence or context component.** Per §9.5A, `venue_history`, both `traits.approach.*` roles, `performance.sg_categories.season`, `benchmark.decomposition`, and `recent_form.trending` are `required: false` with a fixed `missing_behavior` of `venue_history_missing` or `widen_confidence`. A missing source among these six widens only its own named confidence or context component; it must never widen an unrelated component's confidence, redistribute weight into a scored layer, substitute for core rank, or block an otherwise-scorable player.
10. **Missing data is not numeric zero.** Consistent with §2C of this document: an absent or unparseable source value remains missing (`null` / documented null-equivalent), never a silently substituted `0.0`.
11. **`dg_id` remains the preferred identity key; names remain fallback only.** `identity_key` is descriptive metadata about what a physical source carries — it does not change, override, or duplicate `engine/identity_resolver.py`'s existing exact-`dg_id` → crosswalk → exact-name → encoding-fallback precedence.
12. **No credentials.** `metadata` (or any other manifest field) must never contain a DataGolf API key, token, or other secret. A manifest containing one is a release-blocking security defect, not a warning.
13. **Existing archived 3M physical files remain immutable.** Nothing in this contract authorizes renaming, copying, or moving any file under `events/2026_Finished_Events/2026_3m_open/input/` or `library/venues/tpc_twin_cities/`.
14. **Backward compatibility uses explicit manifest entries for legacy filenames; no implicit 3M fallback is authorized.** If a manifest is ever authored for the archived `2026_3m_open` event, every `path` must explicitly name the existing legacy file (for example `"pga_sg_query_3Mopen_similar_l6.csv"`) verbatim. A resolver must never infer that filename from `event_slug` or `venue_slug` — the explicit `path` value is the only authority, precisely so a future non-3M event's manifest cannot accidentally inherit a 3M-shaped filename pattern.
15. **This contract does not change the current producer.** It defines schema only. `engine/enrich_cards.py`'s payload shape, `schemaVersion` values, deploy filenames, `formulaMetadata`, ranks, tiers, probabilities, penalties, gates, and scoring arithmetic are unaffected until a separately authorized implementation phase.
16. **`required` and `missing_behavior` are fixed per role, not chosen per event.** Every entry's `required` value and `missing_behavior` value must match §9.5A exactly for its role. A manifest declaring a different combination for one of the thirteen roles is a release-blocking manifest defect, and `skip_layer`/`warn_only` are not permitted for any of the thirteen (see the `missing_behavior` field rule in §9.4).
