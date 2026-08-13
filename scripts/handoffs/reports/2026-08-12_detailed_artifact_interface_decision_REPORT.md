# Detailed Artifact Interface Decision Report

**Date:** 2026-08-12  
**Mode:** Event-neutral, decision-only, report-only  
**Decision status:** Proposed canonical model for a future `standards/04` change; no repository interface is changed by this report.

## Decision summary

The proposed canonical model has three detailed, independently versioned artifact families under the abstract Live Artifact interface:

1. `rN_analysis` is one detailed version line shared by R1–R4.
2. `final_analysis` is an independently versioned terminal family, currently built from the same detailed shape as a round artifact but distinguished by existing terminal metadata and filename.
3. `cumulative_learning` is an independently versioned state document, not a round-artifact variant.

No new schema number is selected. The current implementation is the compatibility baseline only: round/final artifacts emit `schema_version: "1.1"`; cumulative emits `schema_version: "1.0"`. The future detailed contract must classify every current member before any producer, adapter, typed-contract, deploy, README, library, or migration action is authorized.

**Recommended narrowest next decision:** a standards-only, field-level `standards/04` interface implementation that adopts or revises these matrices and defines compatibility policy, while holding producer, typed, adapter, deploy, README, library, and migration work for separate handoffs.

## Preflight

The required synchronization gate ran before discovery:

```text
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
Test-Path scripts/handoffs/2026-08-12_detailed_artifact_interface_decision.md

Result:
  branch: main
  pull: Already up to date
  initial git status --short: empty
  HEAD:        7fd41ae74cf9d4c3afb7457989ca0e2ccd12e0a3
  origin/main: 7fd41ae74cf9d4c3afb7457989ca0e2ccd12e0a3
  handoff present: True
```

`config/active_event.json` was read first and remains `NO_ACTIVE_EVENT`; event and deploy pointers are null. No root `deploy/` directory exists. No archived board was opened or used as current-consumer authority. The protected `events/2026_wyndham_championship/` fixture was not opened or modified.

## Authority hierarchy

| Authority | Path / section | Decision effect |
|---|---|---|
| Task handoff | This committed handoff | Authorizes only this report and the proposed decision model. |
| Repository governance | `AGENTS.md` System Contracts and Active Event Protocol; `CLAUDE.md`; `SYSTEM_HANDOFF_SPEC.md` | `standards/04` owns artifact structure, `standards/03` owns learning behavior, and no event work is permitted. |
| Detailed interface authority | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §3E | The three families are independently versioned; a future migration must declare members, missing behavior, producer obligations, compatibility, and consumer validation. |
| Learning behavior | `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` §§2, 5–7 | Owns cadence, interpretation, audit, and write-back; defers detailed interface to `standards/04`. |
| Boundary rules | `docs/data_contracts.md` Authority, Live Artifact Envelope, JSON Rules | Envelope is abstract; durable JSON has version/event/generation metadata, snake_case, `null` optional scalars, and `[]` empty collections. |
| Typed-contract boundary | `standards/VENUEDNA_CODEX_SCHEMA.md` §§1–7 | Governs future typed mirrors but supplies only projection/audit types now. |
| Compatibility evidence | Producer, shim, validator, post-mortem, template, README, library schema, and committed discovery/Decision D reports named below | Establishes behavior but does not override doctrine. |

No material authority conflict exists. `PERPLEXITY_OPERATING_PROTOCOL.md` governs Perplexity's handoff publication/commit behavior; this handoff expressly permits one uncommitted local report.

## Current compatibility baseline and non-archived consumer evidence

`engine/build_round_analysis.py:1936-2027` constructs one `output` object with current version `"1.1"`. Normal mode writes `{slug}_r{N}_analysis.json` plus `deploy/data/r{N}_analysis.json`; `--final` writes `{slug}_final_analysis.json` plus `deploy/data/final_analysis.json`. The same producer creates/updates separate cumulative state at `1516-1596`, current version `"1.0"`.

- `engine/build_r1_analysis.py:1-49` is a CLI shim only.
- `engine/verify_live_feed.py:198-239` requires R1 version `1.1`, the canonical trait-key set, `match_summary.matched`/`total_r1`, and `leaderboard_snapshot[*].r1_name`.
- `engine/build_post_mortem.py:117-132` reads only `leaderboard_snapshot[*].r1_name`, `.wave`, and `.wave_penalty`.
- `library/ui_templates/template_app.js:1898-2188` is a reusable, non-deployed template. It reads detailed round data (`metadata`, `live_lean_notes`, `match_summary`, `model_performance`, `leaderboard_snapshot`) and cumulative `rounds_completed`, `is_final`, `cumulative_signals[*].signal_history`, `.delta_history`, `.consensus`, and `.consensus_confidence`.
- `README.md:250-252` directly links `library/engine/ROUND_ANALYSIS_SCHEMA.md`; the library document describes much but not all currently emitted data.

There is no active non-archived deployed board: the manifest deploy pointer is null and root `deploy/` is absent. Archived boards were not inspected. Full browser-consumer compatibility is therefore **INSUFFICIENT EVIDENCE**.

## Proposed `rN_analysis` family matrix

**Decision:** R1–R4 share a single detailed `rN_analysis` version line. `round` plus stable metadata represents the instance. Split only if a round requires a different required member, type, nesting, missing-value rule, or consumer obligation that cannot be represented by an optional stable/source-contingent member. Different source values, an event condition, or a new optional diagnostic are not a split condition.

| Member | Classification | Evidence / exact behavior |
|---|---|---|
| `schema_version`, `generated_at`, `build_timestamp`, `round`, `event_slug` | Required | Always emitted at `build_round_analysis.py:1936-1942`; current version is `"1.1"`, `round` is integer. |
| `enrichment_used`, `course_insights_loaded`, `round_sources` | Required | Always emitted (`1942`, `1956-1958`); booleans describe source availability, and source list is an array. |
| `metadata` | Required | Required current members: `event_name`, `course_name`, `par`, `round_label`, `is_final`, `is_full_tournament`, `favored_wave`, `wx_speed_kts`, `wx_direction`, `wx_wave_delta`, `wx_tide` (`1943-1955`). Unknown weather direction/tide use current `"N/A"` fallback. |
| `enrichment_summary` | Source-contingent | Always present; exact `null` without loaded/matched insights, otherwise object `{source, player_match_n, player_total, traits_upgraded, traits_confirmed}` (`1887-1901`). |
| `live_lean_notes` | Required | Always emitted; nested classification below. |
| `match_summary` | Required | Fixed members: integers `matched`, legacy compatibility `total_r1`, string array `unmatched`, numeric `match_rate_pct` (`1961-1966`). Empty unmatched is `[]`. |
| `model_performance` | Required | Numeric `spearman_rho`; required group map keyed `pt_top10`, `pt_top20`, `tier1`, `tier2`, `tier1_2`, `all_field`, with `n`, `avg_r1_pos`, `avg_r1_score`, `in_r1_top10`, `in_r1_top20` (`950-973`). `r1` names are legacy compatibility members. |
| `sg_leader_averages` | Required | Keys `top10`, `top18`, `full_field`; each SG map has `sg_ott`, `sg_app`, `sg_arg`, `sg_putt`, `sg_tot`. Scalars are source-contingent `null` when unavailable. |
| `trait_audit` | Required | Ten canonical trait keys are enforced/padded (`1260-1284`) and required by the verifier. Nested classification below. |
| `risers`, `slippage`, `weekend_risers`, `slippage_risk` | Required arrays | Always emitted; no-result behavior is `[]`. Item members come from available joined data; weekend records add `thesis_score`/`thesis_note`, slippage-risk records add `risk_flags` (`1290-1445`). |
| `leaderboard_snapshot` | Required array | All joined records. `player_id` and `vs_proj` are emitted and can be `null`; pre-event/SG members are source-contingent. Current post-mortem relies on `r1_name`, `wave`, `wave_penalty`. |
| `dimension_leaders` | Required | Fixed keys `sg_app`, `sg_putt`, `sg_ott`, `sg_arg`; each is an array, possibly `[]`, of `{r1_name, r1_pos, value, r1_score}` (`1698-1704`). |
| `live_probability_engine` | Required; compatibility member | Always emitted (`1983-2000`) but absent from library documentation. Preserve it pending an explicit detailed disposition. |
| `course_stats`, `easiest_holes`, `hardest_holes` | Required source-contingent arrays | Always emitted. Without source data each is exactly `[]`; course-stat records have `hole`, `par`, `yards`, `avg`, `rank`, `plus_minus`, `birdies`, `pars`, `bogeys`, `dbl` (`1887-1912`). |

### Material `rN_analysis` nested members

| Parent / member set | Classification | Exact behavior |
|---|---|---|
| `live_lean_notes.round`, `.next_round`, `.lean_up_traits`, `.lean_down_traits`, `.putt_caution`, `.putt_outliers`, `.watch_next_round`, `.wave_risk_annotation`, `.wave_scoring_averages`, `.rho_note` | Required | All built at `1498-1513`; `.next_round` is exactly `null` at final, and no-result collections are `[]`. Firm/fast lean records can add `multiplier`: source/conditions-contingent. |
| `trait_audit[*]` base members | Required per canonical trait | `venue_weight`, trait/SG averages and deltas, `sg_proxy`, `signal`, sample counts, `source_confidence`, and `enrichment` are produced/padded at `995-1029`, `1251-1284`. Evidence numbers can be `null`; padded traits have exact zero/null/not-testable values. |
| `trait_audit[*].enrichment` | Source-contingent tagged object | Always present after padding: unavailable is `{available: false, reason: string}`; available object has primary/secondary values and signal fields; no direct proxy uses unavailable form (`1178-1223`). Do not replace this behavior with `null`. |
| `.brie_z` | Source-contingent absent member | Added only for configured `app_150_200`; success object has availability/count/averages/penalty/note, failure is `{available: false, schema_version: "1.1", error: string}` (`1032-1093`). |
| `.proxy_source`, `.live_proxy_label`, `.live_proxy_top10_avg`, `.live_proxy_field_avg`, `.signal_upgraded_by_enrichment` | Source-contingent absent/null members | Live-proxy detail appears only with a live-stats source; `proxy_source` is `null` without it; upgrade flag exists only after an upgrade (`1095-1223`). |
| `leaderboard_snapshot[*]` live extensions | Optional but stable compatibility members | `live_win_pct`, `live_top5_pct`, `live_top10_pct`, `live_top20_pct`, `v_p_t`, `cumulative_sg_tot`, `wave_draw`, `wave_penalty` are appended to each record (`1870-1886`). Values may be nullable; post-mortem reads `wave_penalty`. |
| `live_probability_engine` | Required object with source-contingent contents | Current fixed keys: `round`, `gamma`, `field_vts_mean`, `field_avg_cum_sg`, `temperatures`, `prior_rounds_used`, `population_anchor_size`, `active_field_size`, `eliminated_frozen_count`, `wave_penalty_params`; the latter has six members. Exact value domains are unresolved for detailed specification. |

## Proposed `final_analysis` family matrix

**Decision:** `final_analysis` is an independently versioned terminal family, not an alias of `r4_analysis`. It currently reuses the round construction but has a distinct filename and terminal purpose in `standards/03` §2.

| Member set | Classification | Decision / evidence |
|---|---|---|
| All `rN_analysis` members | Provisionally same classifications | `build_round_analysis.py:1936-2021` writes the same `output` object in final mode. Preserve current shared baseline unless a future contract explicitly differs. |
| `round: 4` | Required terminal metadata | `--final` makes `ROUND = 4`. |
| `metadata.is_final: true` | Required terminal metadata | Current final output sets true; ordinary R4 also sets true. |
| `metadata.is_full_tournament: true` | Required final-family discriminator | Current final output sets true only for `--final`; R4 writes false. This is the proposed minimum existing discriminator. |
| `metadata.round_label: "Final Tournament"` | Required legacy compatibility member | Ordinary R4 emits `"Final Round"`. Preserve both current vocabulary values pending a future vocabulary decision. |
| Final-only summary/audit members | Unresolved and requiring later explicit decision | `standards/03` §7 identifies final rho, tier hit rate, trait consensus, and audit purpose but not placement. No final-only member is added by this decision. |

**Exact R4-parity boundary:** current payload-shape parity holds except filename/location and `metadata.is_full_tournament`/`metadata.round_label`. This report does not decide future total-shape parity, terminal-only required summaries, or a final-to-audit reference; no current non-archived consumer establishes those choices.

## Proposed `cumulative_learning` family matrix

**Decision:** `cumulative_learning` is a persistent, independently versioned state document with one event identity, per-round snapshots, and per-trait histories.

| Member / behavior | Classification | Evidence and proposed requirement |
|---|---|---|
| `schema_version`, `event_slug`, `created_at`, `per_round`, `cumulative_signals` | Required initialization members | Fresh state initializes them at `1516-1565`, with current `"1.0"`, event slug, date, empty per-round map, and canonical signal records. |
| Read precedence | Required state behavior | Read output state first, deploy fallback second, initialize last (`1536-1565`). Future contract must preserve this precedence or explicitly replace it. |
| `last_updated`, `updated_at`, `rounds_completed`, `is_final`, `rounds_present` | Required persisted members | Set every build at `1567-1577`; `rounds_present` is sorted unique integer history. |
| `per_round["N"]` | Required processed-round state | Each entry has `round`, `generated_at`, `spearman_rho`, `trait_signals`, `model_hits`, `risers`, `slippage`, `wave_annotation_n` (`1520-1534`). Riser/slippage arrays are `[]` when empty. |
| `per_round[*].trait_signals[*]` | Required per observed canonical trait; source-contingent scalar values | Required keys are `signal`, `source_confidence`, `trait_delta`, `sg_delta`, `enrichment_signal`; the final three may be `null`. |
| `per_round[*].model_hits` | Required | Fixed integer members: `pt_top10_in_top10`, `pt_top10_in_top20`, `tier1_2_in_top20`; `r1` source names are legacy compatibility semantics. |
| `cumulative_signals[*]` | Required canonical trait map | Required members: `rounds_observed`, `signal_history`, `confidence_history`, `delta_history`, `consensus`, `consensus_confidence` (`1554-1562`, `1579-1596`). Fresh consensus is `null`; updated consensus is latest history value. |
| Reprocessed observed round | Required update behavior | Existing index is replaced, not appended (`1587-1594`). Future state contract must state this explicitly. |
| State upgrade | Required migration prerequisite | No unversioned reinterpretation. Future migration must specify source-version detection, version-dispatched upgrade/translation, per-round/history preservation or deterministic reconstruction, idempotence/retry, and validation before write. No mechanism is designed here. |
| Final-state semantics | Required terminal behavior | Final state has `is_final: true`, terminal `rounds_completed`, and persisted terminal snapshot. Whether final analysis links, embeds, or only coexists is unresolved. |

## Proposed independent compatibility policy

| Term | `rN_analysis` | `final_analysis` | `cumulative_learning` |
|---|---|---|---|
| Non-breaking | Add a documented optional member with exact absent/null/empty behavior; clarify prose without semantic change. | Same, retaining terminal invariants. | Add an optional member only if old state remains valid and read/update output is unchanged. |
| Breaking | Remove, rename, retype, move/nest, change requiredness/enums, or change null/empty/absent behavior. | Same, plus changing final/R4 discriminator or terminal invariants. | Same, plus changing read precedence, keying, histories, consensus derivation, or update behavior. |
| Deprecation | Keep legacy member through approved compatibility window, replacement mapping, and selected consumer validation. | Same. | Keep/read old state through window; never silently discard history. |
| Translation | Versioned mapping only after verified consumer or migration need; declare source/target versions and semantic mapping. | Same. | Translator must be idempotent, preserve/reconstruct history deterministically, and validate before persistence. |
| Prerequisites | Freeze producer field inventory/samples; select non-archived consumers; approve tests and scope. | Also settle final/R4 parity. | Also test fresh initialization, output/deploy fallback, repeat update, partial history, terminal state, upgrade. |

## Authority, adapter, typed, and library decisions

- `standards/04` should own detailed fields/types/nesting/requiredness, source-contingent behavior, versions, compatibility, producer obligations, and consumer-validation requirements.
- `standards/03` should retain cadence, correlation/trait interpretation, audit, Council, and write-back; it should not duplicate detailed payload tables.
- `docs/data_contracts.md` should retain the immutable pre-event spine, abstract envelope, producer-consumer boundary, and JSON rules; it should not assert a shared producer wire shape.
- **NO ADAPTER CURRENTLY JUSTIFIED.** No non-archived runtime consumer requires abstract-envelope members as a literal boundary. An adapter would need explicit versioning and a verified consumer requirement or approved producer change.
- A future `VENUEDNA_CODEX_SCHEMA.md` mirror needs approved detailed member/type/enum/null tables, final discriminator, cumulative state/update/upgrade rules, approved naming, and producer/selected-consumer validation. No typed definition is created here.
- Preserve `library/engine/ROUND_ANALYSIS_SCHEMA.md` and README reference unchanged. Transition/deprecation requires all of: approved complete `standards/04` replacement; resolved producer/library deltas; consumer/template dispositions; compatible validation; and separately authorized link/path migration.

## Non-actions, blockers, and validation

No standard, contract, code, test, producer, adapter/wrapper, typed definition, README, library schema, deploy asset, database, active-event file, event, archive, fixture, migration, branch, Git configuration, commit, or push changed. No archived board was inspected and no Wyndham fixture path was opened or modified.

Open blockers: no active non-archived board for full browser-consumer evidence; no approved final-specific member set beyond current metadata; no approved detailed replacement for the partially stale library schema.

After creation, the required validation commands are:

```text
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
git status --short
git diff --name-only
git diff -- scripts/handoffs/reports/2026-08-12_detailed_artifact_interface_decision_REPORT.md
```

Exact results are recorded in the completion response.
