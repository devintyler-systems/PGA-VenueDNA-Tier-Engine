# Round-Analysis Schema Synchronization Report

**Date:** 2026-08-12  
**Scope:** Read-only reconciliation of the round-analysis producer and the exact documentation sources named in `scripts/handoffs/2026-08-12_round_analysis_schema_sync.md`.  
**Active event:** `NO_ACTIVE_EVENT` confirmed from `config/active_event.json`.  
**Local / remote commit:** `bfd2f20153766d0ad82add3667ef3019472ef834` for both local `HEAD` and `origin/main`; worktree was clean before inspection.

## Executive finding

`engine/build_round_analysis.py` is the executable source for the detailed current payload. It emits a schema-1.1 round artifact and a distinct schema-1.0 cumulative-learning artifact. The README explicitly points to `library/engine/ROUND_ANALYSIS_SCHEMA.md` as the complete field-by-field reference, and that document describes most of the producer's original structure.

There is, however, a protected-contract decision: canonical `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` declares a materially different, flatter round-analysis and cumulative-learning interface while stating that it implements this producer. `docs/data_contracts.md` separately requires a generic live-artifact envelope that this producer does not emit. Resolving which interface is authoritative would require changes to protected producer and/or doctrine/contract files, so this report records the evidence only.

Confidence: **high** for emitted fields and field-level differences (direct assignments in the producer); **high** for doctrine conflicts (direct schema examples); **medium** for intended consumer compatibility because no active deploy surface was inspected under the `NO_ACTIVE_EVENT` boundary.

## Producer inventory

Evidence base: `engine/build_round_analysis.py:1025-1266`, `1500-1596`, `1599-1886`, and `1936-2027`.

### Round artifact: top level

| Field | Type / computed meaning |
|---|---|
| `schema_version` | string, fixed `"1.1"` |
| `generated_at` | ISO date string |
| `build_timestamp` | ISO local datetime string |
| `round` | integer 1-4 |
| `event_slug` | string CLI/config event key |
| `enrichment_used` | boolean: course-insights CSV loaded |
| `metadata` | object described below |
| `round_sources` | string array of source filenames actually used |
| `course_insights_loaded` | boolean |
| `enrichment_summary` | object or null: source, player match/total counts, upgraded and confirmed trait arrays |
| `live_lean_notes` | object described below |
| `match_summary` | object: `matched` integer, `total_r1` integer, `unmatched` string array, `match_rate_pct` number |
| `model_performance` | object: `spearman_rho` number and `groups` object |
| `sg_leader_averages` | object of `top10`, `top18`, `full_field`; each contains nullable numeric `sg_ott`, `sg_app`, `sg_arg`, `sg_putt`, `sg_tot` |
| `trait_audit` | object keyed by canonical trait; each entry described below |
| `risers` | array of up to 12 player-summary objects with positive rank delta |
| `slippage` | array of up to 10 player-summary objects with negative rank delta among pre-event top 35 |
| `weekend_risers` | player-summary array with `thesis_score` integer and `thesis_note` string |
| `slippage_risk` | player-summary array with `risk_flags` string array |
| `leaderboard_snapshot` | all joined player records, described below |
| `dimension_leaders` | object keyed `sg_app`, `sg_putt`, `sg_ott`, `sg_arg`, each an array of up to five `{r1_name, r1_pos, value, r1_score}` objects |
| `live_probability_engine` | object described below |
| `course_stats` | hole object array (empty when source absent) |
| `easiest_holes` / `hardest_holes` | derived subsets of `course_stats` |

`metadata` contains `event_name` string, `course_name` string, `par` integer, `round_label` string, `is_final` boolean, `is_full_tournament` boolean, plus weather/wave fields: `favored_wave` string, `wx_speed_kts` number, `wx_direction` string, `wx_wave_delta` number, `wx_tide` string (`1936-1955`).

`model_performance.groups` contains `pt_top10`, `pt_top20`, `tier1`, `tier2`, `tier1_2`, and `all_field`; each has `n`, `avg_r1_pos`, `avg_r1_score`, `in_r1_top10`, and `in_r1_top20` (`965-987`).

### Trait, live-proxy, and enrichment detail

Every `trait_audit` entry initially emits `venue_weight`, `top10_trait_avg`, `field_trait_avg`, `trait_delta`, `sg_proxy`, `sg_top10`, `sg_field`, `sg_delta`, `signal`, `sample_n_top10`, and `sample_n_field` (`1025-1037`). The canonical ten-trait padding also emits `source_confidence` and unavailable `enrichment` for absent configuration keys (`1268-1284`).

Further optional/derived nested detail is emitted as follows:

- `app_150_200.brie_z`: `schema_version`, `available`, counts and field averages, `course_rough_penalty`, wave-bonus count, `note`; fallback is `available`, `schema_version`, `error` (`1039-1093`).
- Live-proxy augmentation: `source_confidence`, `proxy_source`, `live_proxy_label`, `live_proxy_top10_avg`, `live_proxy_field_avg`; no source yields `not_testable` / null proxy source (`1095-1174`).
- `enrichment`: when course insights exist, `available`, `source`, `primary_field`, `direction`, top10/field primary and secondary values, deltas, `enrichment_signal`, `upgraded_signal`; otherwise `{available, reason}` (`1200-1260`). `signal_upgraded_by_enrichment` is emitted only when applicable.

### Live notes, leaderboard, probability, and hole detail

`live_lean_notes` contains `round`, nullable `next_round`, `lean_up_traits` array, `lean_down_traits` array, `putt_caution` boolean, `putt_outliers` objects (`player`, `sg_putt`, `sg_app`), `watch_next_round` objects, `wave_risk_annotation` array, `wave_scoring_averages` object, and `rho_note` string (`1500-1514`). Wave annotations hold player/position/wave evidence and an explanatory note (`934-963`).

The common player-summary fields are selected from `r1_name`, `norm_name`, `r1_pos`, `r1_pos_str`, `r1_score`, `pt_rank`, `pt_tier`, `pt_vts`, `pt_flags`, `pt_driver`, `rank_delta`, `sg_ott`, `sg_app`, `sg_arg`, `sg_putt`, `sg_tot`, `wave` (`1289-1296`). A `leaderboard_snapshot` adds canonical `player_id`, nullable/derived `vs_proj`, `live_win_pct`, `live_top5_pct`, `live_top10_pct`, `live_top20_pct`, `v_p_t`, `cumulative_sg_tot`, `wave_draw`, and `wave_penalty`; Round 2 may also add `heat_stress_penalty` and `heat_index_peak` (`1599-1688`, `1862-1886`).

`live_probability_engine` provides `round`, `gamma`, `field_vts_mean`, `field_avg_cum_sg`, temperature map, `prior_rounds_used`, population sizes, and `wave_penalty_params` (`1982-2000`). The latter has `wx_speed_kts`, `wx_delta_strokes`, `disadvantaged_wave`, `wind_severity`, `latent_penalty`, and `players_penalized`.

Each `course_stats` row uses integer `hole`, `par`, `yards`, `rank`, `birdies`, `pars`, `bogeys`, `dbl`, and numeric `avg`, `plus_minus` (`1888-1908`).

### Cumulative-learning artifact

The producer writes a separate `schema_version: "1.0"` object to `{slug}_cumulative_learning.json` and deploy `cumulative_learning.json` (`1516-1596`, `2024-2027`). It has `event_slug`, `created_at`, `last_updated`, `updated_at`, `rounds_completed`, `is_final`, `rounds_present`, `per_round`, and `cumulative_signals`.

- `per_round[N]`: `round`, `generated_at`, `spearman_rho`, `trait_signals` (each `signal`, `source_confidence`, `trait_delta`, `sg_delta`, `enrichment_signal`), `model_hits`, `risers`, `slippage`, `wave_annotation_n`.
- `cumulative_signals[trait]`: `rounds_observed`, `signal_history`, `confidence_history`, `delta_history`, `consensus`, `consensus_confidence`.

## Documentation inventory

| Source | What it documents or references | Evidence / confidence |
|---|---|---|
| `library/engine/ROUND_ANALYSIS_SCHEMA.md` | Detailed schema 1.1 round top level, metadata, match/model/trait/live-note/leaderboard structures, and cumulative schema 1.0. | Lines 1-328; high. |
| `README.md` | Round output locations and build workflow; at line 252 states verbatim: “See `library/engine/ROUND_ANALYSIS_SCHEMA.md` for the complete field-by-field definition of the `rN_analysis.json` and `cumulative_learning.json` structures.” | `README.md:49, 71-85, 172-193, 232-252, 349-365`; high. |
| `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` | Canonical learning-loop doctrine and its own flatter round/cumulative examples: top-level `event`, direct `spearman_rho`, `spearman_p_value`, `rho_interpretation`, `players_in_correlation`, `board`, `trait_validation`, `round_notes`; cumulative `event`, `rounds_complete`, `rho_by_round`, `trait_validation_summary`, `tier_hit_rates`, `model_accuracy_notes`, `council_flags`. | Lines 5, 68, 108-190; high. |
| `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` | General schema-version policy and generic live-artifact required metadata, not a detailed rN/cumulative field list. | Lines 9-16 and live-artifact section; high. |
| `standards/VENUEDNA_CODEX_SCHEMA.md` | Typed pre-event and audit contracts; no detailed rN analysis or cumulative-learning schema and no path reference to the detailed schema. | Lines 28-438; high. |
| `docs/data_contracts.md` | Generic live-artifact envelope (`event_slug`, `round`, `generated_at`, `pre_event_artifact`, `authoritative_spine`, `player_updates`, `conditions_context`, `scenario_fencing`, `diagnostics`) plus deploy dynamic paths. It does not enumerate the producer's rN/cumulative fields. | Lines 485-510, 544-589; high. |

## Discrepancy reconciliation

| Classification | Finding | Evidence and confidence |
|---|---|---|
| Producer-emitted field absent from all documentation | `build_timestamp`; `enrichment_used`; full `metadata` extensions (`is_full_tournament`, favored-wave and all `wx_*` values); `live_probability_engine`; leaderboard live probability/vector fields; `wave_draw`, `wave_penalty`; optional heat fields; trait `brie_z` and live-proxy fields; `wave_risk_annotation`, `wave_scoring_averages`; cumulative `updated_at`, `is_final`, `rounds_present`, per-round `wave_annotation_n`. | Producer lines 1025-1266, 1500-1596, 1599-2004; none appear in detailed schema or canonical source inventories. High. |
| Type, meaning, or nesting mismatch | `standards/03` says rho is top-level and cumulative `rho_by_round` (`:68`); producer nests rho in `model_performance.spearman_rho` and per-round entries (`:1520-1541`, `:1966-1969`). | High. |
| Type, meaning, or nesting mismatch | `standards/03` models live player state as `board[]`, `trait_validation`, and `round_notes` (`:108-141`); producer instead emits `leaderboard_snapshot[]`, quantitative `trait_audit{}`, and `live_lean_notes{}` (`:1500-1514`, `:1599-1886`, `:1975-1980`). | High. |
| Type, meaning, or nesting mismatch | `docs/data_contracts.md` requires generic live keys including `pre_event_artifact`, `authoritative_spine`, `player_updates`, `conditions_context`, `scenario_fencing`, and `diagnostics` (`:489-502`); producer emits none of these exact keys, using `round_sources`, snapshots, and diagnostics-like nested objects instead. | High. |
| Type, meaning, or nesting mismatch | `standards/03` cumulative schema is v1.1 and uses `rounds_complete`, `rho_by_round`, `trait_validation_summary`, tier rates and Council fields (`:144-190`); producer is v1.0 with `rounds_completed`, `per_round`, and `cumulative_signals` (`:1520-1596`). | High. |
| Documented field absent from producer (stale doc) | Detailed schema lists `trait_audit.enrichment.proxy_fields`, `enrichment_note`, `n_top10_ci`, `n_field_ci`; producer does not assign them. It instead has secondary values/deltas and live proxy detail. | Detailed schema `:143-184`; producer `:1200-1239`. High. |
| Documented field absent from producer (stale doc) | Detailed schema's `model_performance.groups` examples include `in_r1_top30`; producer group stats stops at `in_r1_top20`. | Detailed schema `:105-116`; producer `:965-981`. High. |
| Documented field absent from producer (stale doc) | `standards/03` fields absent from producer: `event`, `spearman_p_value`, `rho_interpretation`, `players_in_correlation`, `board`, `trait_validation`, `round_notes`, and all distinct cumulative fields noted above. | `standards/03:108-190`; producer assembly `:1936-2004`, cumulative `:1520-1596`. High. |
| Documented field absent from producer (stale doc) | `docs/data_contracts.md` generic live-envelope fields listed above are absent from the producer's emitted JSON. | `docs/data_contracts.md:489-502`; producer `:1936-2004`. High. |
| Authority conflict | README presents `library/engine/ROUND_ANALYSIS_SCHEMA.md` as the complete detailed definition (`README.md:252`), while canonical `standards/03` says it implements the producer but supplies a non-compatible schema. `docs/data_contracts.md` adds a third incompatible live envelope. | High; this is the protected-contract decision requiring operator/doctrine authority. |

## Path verification

| Reference | Result |
|---|---|
| `library/engine/ROUND_ANALYSIS_SCHEMA.md` in `README.md:252` | Resolves to the current inspected file. |
| `docs/data_contracts.md` required by the handoff | Resolves at the documented `docs/` location. No reviewed round-analysis reference in README, standards/03, standards/04, or VENUEDNA_CODEX_SCHEMA points to a moved alternate. |
| `engine/build_round_analysis.py` referenced by `standards/03:5` | Resolves to the current producer. |
| Round output names in README and standards/03 | Producer writes `{slug}_rN_analysis.json` / `{slug}_final_analysis.json` and `{slug}_cumulative_learning.json` (`engine/build_round_analysis.py:2007-2027`), which agrees with the surviving file-name references. |
| Detailed-schema build examples | The library schema uses `python engine/build_round_analysis.py --round N` without mandatory `--event_slug`; current parser requires `--event_slug` (`engine/build_round_analysis.py:58-63`). This is a stale command-interface reference, not a file-path failure. |

## Alternatives (no resolution performed)

### A. Retain `library/engine/ROUND_ANALYSIS_SCHEMA.md` as detailed interface authority and update it to match the producer

**Pros:** It is already the README-linked detailed schema; its broad top-level shape matches the producer. This is the smallest documentation-only reconciliation for emitted weather/wave, probability, and enrichment additions.

**Cons:** It leaves a detailed interface below canonical `standards/03`, which already asserts a conflicting canonical schema. Updating only the library document would not resolve the standards/03 or `docs/data_contracts.md` conflicts.

### B. Migrate/reconcile the detailed schema into canonical `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`

**Pros:** `standards/03` is already canonical and explicitly says it implements `engine/build_round_analysis.py`; it uniquely owns round cadence and cumulative learning. Replacing its incompatible examples with a reconciled detailed schema creates a single authority tier for learning-loop outputs. `standards/04` should continue to govern cross-artifact policy and `docs/data_contracts.md` the generic producer-consumer boundary.

**Cons:** This is a protected canonical-doctrine change and would require coordinated review of `standards/03`, the producer, the README-linked schema, and likely `docs/data_contracts.md`, plus consumer/test validation. It cannot be performed in this handoff.

### C. Minimal-safe evidence-supported model: retain the detailed schema temporarily, but amend canonical `standards/03` and `docs/data_contracts.md` to explicitly defer their detailed rN/cumulative shapes pending a versioned contract migration

**Pros:** This directly addresses the authority collision without asserting that legacy detailed fields are canonical forever. Evidence supports it because README already relies on the detailed schema, while standards/03 and data_contracts provide incompatible schemas. It permits an ordered migration decision without silently changing current payloads.

**Cons:** It preserves two documents until the migration completes and still requires a protected-contract decision/change.

**Recommendation:** **B**, with the migration explicitly covering `docs/data_contracts.md`'s generic live envelope and preserving `standards/04` as the cross-artifact policy layer. The evidence is strongest for `standards/03` because it is the canonical document specifically scoped to this producer and cumulative learning. No action is authorized here.

## Validation evidence

```text
git status
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean

git log -1 --format=%H
bfd2f20153766d0ad82add3667ef3019472ef834

git fetch origin && git log origin/main -1 --format=%H
bfd2f20153766d0ad82add3667ef3019472ef834

python tools/validate_scoring_doctrine.py
[info] RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED events/2026_wyndham_championship: Wyndham event directory recognized as the sole authorized retrospective-development fixture: NO_ACTIVE_EVENT is preserved, all required fence markers are present, and no output, deploy, or live artifact exists under the fixture root.
SCORING DOCTRINE PASSED (1 warnings)

python -m pytest tests/test_doctrine_contract.py -q
121 passed in 13.14s

git diff --check
(no output; exit 0)
```

## Unresolved / blocked

No protected file was edited. The reconciliation is blocked from any resolution by the handoff's protected-file rule and `SYSTEM_HANDOFF_SPEC.md` conflict-resolution rule: the exact conflict is among `engine/build_round_analysis.py`, `library/engine/ROUND_ANALYSIS_SCHEMA.md`, canonical `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`, and `docs/data_contracts.md`. A follow-up needs explicit authorization for a versioned contract/doctrine decision before modifying any of them.

