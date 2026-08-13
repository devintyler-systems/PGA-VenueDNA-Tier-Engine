# Round and Cumulative Schema Strategy Discovery Report

**Date:** 2026-08-12
**Mode:** Read-only, evidence-driven discovery
**Decision status:** This report authorizes no detailed schema, typed contract, producer, adapter, migration, README, library, deploy, database, or event change.

## Executive ruling

Three detailed artifact families exist: round analysis (`rN_analysis`), final analysis (`final_analysis`), and cumulative learning (`cumulative_learning`). Decision D assigns their future detailed, independently versioned interfaces to `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §3E. They should retain independent version lines while sharing only an explicitly approved compatibility policy in a later migration. The generic Live Artifact envelope is an abstract logical interface, not a fourth producer payload.

`engine/build_round_analysis.py` establishes the current compatibility baseline: round and final artifacts emit `schema_version: "1.1"`; a separately read-modify-written cumulative artifact emits `schema_version: "1.0"`. The README-linked `library/engine/ROUND_ANALYSIS_SCHEMA.md` documents much but not all of that baseline. No verified non-archived runtime consumer requires the generic envelope: **NO ADAPTER CURRENTLY JUSTIFIED**.

**Recommended narrowest next decision:** a decision-only, detailed field-level canonical-interface handoff for the three families in `standards/04`, including independent version/compatibility policy and final-versus-R4 treatment. It must not authorize code, typed contracts, adapters, deploy, README, library, or migration implementation.

## Synchronization and active-event preflight

The required synchronization gate ran before local inspection:

```text
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
Test-Path scripts/handoffs/2026-08-12_round_cumulative_schema_strategy_discovery.md

Result:
  branch: main
  pull: Already up to date
  initial git status --short: empty
  HEAD:        81f089c813ac099ca152337cc5cb17e38e424857
  origin/main: 81f089c813ac099ca152337cc5cb17e38e424857
  handoff present: True
```

`config/active_event.json` was read first and is exactly `NO_ACTIVE_EVENT`; its event and deploy pointers are null. Root `deploy/` does not exist. `events/2026_wyndham_championship/` was not opened or modified; final diff scope demonstrates it remains untouched.

## Source hierarchy and conflict check

| Authority | Relevant finding | Ruling |
|---|---|---|
| Explicit committed handoff | Authorizes discovery and this report only. | Governs task scope. |
| `AGENTS.md` System Contracts and Active Event Protocol | `standards/04` governs artifact structure/names/packaging; `standards/03` governs learning/write-back; `NO_ACTIVE_EVENT` permits event-neutral work. | Governs repository behavior. |
| `SYSTEM_HANDOFF_SPEC.md` Handoff Publication and Sync / Conflict Resolution | Requires a committed synchronized handoff and a stop for unresolved conflict. | Gate passed. |
| `docs/data_contracts.md` Authority and Live Artifact Envelope | The envelope is abstract; its authority is below typed contracts and `standards/04`. A real boundary needs a future versioned adapter/wrapper or approved producer change. | No common producer wire shape follows. |
| `standards/04` §3E and `standards/03` §§2, 5–7 | §3E owns detailed future interfaces; §3 retains cadence, audit, interpretation, and write-back while deferring detailed payload. | No material contract conflict remains. |
| `standards/VENUEDNA_CODEX_SCHEMA.md` §§1–7 | Provides typed schema, dataclass, naming, and validation patterns only for projection/audit today. | Possible future typed mirror, not current detailed authority. |
| Implementation, tests, templates, and prior reports | Establish current behavior and compatibility evidence. | Do not override canonical doctrine. |

No material ownership conflict was found. `PERPLEXITY_OPERATING_PROTOCOL.md` governs Perplexity's handoff publication/commit behavior; this committed handoff specifically delegates one uncommitted local report to the executor. `CLAUDE.md` and `AGENTS.md` agree on the relevant hierarchy.

## Detailed schema-version strategy

| Family | Exact path / symbol | Finding and recommendation | Uncertainty |
|---|---|---|---|
| `rN_analysis` | `engine/build_round_analysis.py:1936-2021`; `library/engine/ROUND_ANALYSIS_SCHEMA.md:1-268` | Fixed `"1.1"`; writes `{slug}_r{N}_analysis.json` and `deploy/data/r{N}_analysis.json`. Use an independent round-analysis version line; R1–R4 can share it only if a future detailed contract says so. | No approved required/optional or compatibility policy exists. |
| `final_analysis` | `engine/build_round_analysis.py:1936-2021`; `standards/03` §2 | `--final` reuses current round-payload construction, marks final metadata, and writes `{slug}_final_analysis.json` and `deploy/data/final_analysis.json`. Use an independent final-analysis version line. | **INSUFFICIENT EVIDENCE** whether it should remain structurally identical to R4. |
| `cumulative_learning` | `engine/build_round_analysis.py:1516-1596, 2024-2027`; `ROUND_ANALYSIS_SCHEMA.md:270-300` | Fixed `"1.0"`, stateful load/update/write document; writes `{slug}_cumulative_learning.json` and `deploy/data/cumulative_learning.json`. Use an independent cumulative version line. | Future migration must define state upgrade/prior-version behavior. |
| Generic envelope | `docs/data_contracts.md:485-508`; `standards/04` §3E | Group the families only as an abstract logical interface. | It creates no shared payload/version line. |

## Producer-to-documentation compatibility matrix

| Artifact and locations | Producer-emitted compatibility baseline | Documentation evidence | Required future disposition |
|---|---|---|---|
| Round analysis: `events/{slug}/output/{slug}_rN_analysis.json`; `events/{slug}/deploy/data/r{N}_analysis.json` | `build_round_analysis.py:1936-2004` emits `schema_version` (`"1.1"`), `generated_at`, `build_timestamp`, integer `round`, `event_slug`, booleans `enrichment_used`/`course_insights_loaded`, maps (`metadata`, `enrichment_summary`, `live_lean_notes`, `match_summary`, `model_performance`, `sg_leader_averages`, `trait_audit`, `live_probability_engine`, `dimension_leaders`), arrays (`round_sources`, riser/slippage arrays, `leaderboard_snapshot`, course/hole arrays). Source-driven data uses absent nested members, `null`, empty arrays, and booleans. | `ROUND_ANALYSIS_SCHEMA.md:9-268` covers most original fields; README §§Tournament Learning and Schema Reference call it complete. | A migration must preserve, translate, or explicitly deprecate every member/empty/null behavior. Library omissions include `build_timestamp`, `enrichment_used`, weather/wave metadata, and `live_probability_engine`; detailed nested optionality needs audit. |
| Final analysis: `events/{slug}/output/{slug}_final_analysis.json`; `events/{slug}/deploy/data/final_analysis.json` | Same top-level construction/version; final distinction is `metadata.is_final` and `metadata.is_full_tournament`. | `standards/03` §2 names final analysis; library schema documents R1–R4 rather than an independent final file. | Preserve paths/flags until a detailed version decision. A final-specific field contract is **INSUFFICIENT EVIDENCE**. |
| Cumulative learning: `events/{slug}/output/{slug}_cumulative_learning.json`; `events/{slug}/deploy/data/cumulative_learning.json` | `build_round_analysis.py:1516-1596` initializes/loads `schema_version`, `event_slug`, timestamps, `per_round`, `cumulative_signals`, then updates `last_updated`, `updated_at`, `rounds_completed`, `is_final`, and `rounds_present`. Per-round records contain integer round, timestamp, nullable rho, trait-signal map, model hits, and riser/slippage arrays; signal histories are arrays with consensus fields. | `ROUND_ANALYSIS_SCHEMA.md:270-300`; README §Tournament Learning. | Preserve current stateful read precedence and all observed fields until migration. The library omits some current fields, so migration requires a stateful compatibility/upgrade test. |
| Generic envelope | No inspected producer emits the abstract concern names as a shared top-level object. | `docs/data_contracts.md:485-508`; `standards/04` §3E. | Do not synthesize a wrapper by inference. |

## Consumer and adapter discovery inventory

The search was bounded to non-event paths (`rg` excluded `events/**`) and did not open archived boards or the Wyndham fixture.

| Path and symbol | Classification | Finding | Authority / uncertainty |
|---|---|---|---|
| `engine/build_round_analysis.py:1516-1596, 1936-2027` | Producer | Sole inspected shared producer. | Current emitted-payload truth, not doctrine. |
| `engine/build_r1_analysis.py:40-49` | CLI/shim | Delegates R1 invocation to the shared producer. | Does not parse/adapt payload. |
| `engine/verify_live_feed.py:198-239` | Validator/test harness | Reads `r1_analysis.json`; validates version `1.1`, `trait_audit`, `match_summary.matched`/`total_r1`, and `leaderboard_snapshot` names. Backs up/restores cumulative files. | Executable evidence for this narrow R1 subset, not an envelope consumer. |
| `engine/build_post_mortem.py:117-132` | Executable/CLI consumer | Optionally reads `r1_analysis.json` and uses `leaderboard_snapshot[*].r1_name`, `.wave`, and `.wave_penalty`. | Verified non-archived narrow R1 consumer; no final/cumulative/envelope use. |
| `library/ui_templates/template_app.js:148-154, 1898-2020` | Reusable template / potential consumer | Fetches placeholder-prefixed final, round, and cumulative filenames and renders detailed round members including `metadata`, `live_lean_notes`, `match_summary`, `model_performance`, and `leaderboard_snapshot`. | Not an active deployed board; template-only evidence. Its prefixed names differ from shared producer deploy names. |
| `tools/build_deploy_profile.py`; `tests/test_build_deploy_profile.py` | Tool and validator/test | Discover/integrity-cover dynamic fetch paths in temporary trees; no payload-field parsing. | Filename-contract evidence only. |
| `docs/data_contracts.md`; `library/templates/deploy_payload_manifest.json`; `README.md`; `ROUND_ANALYSIS_SCHEMA.md` | Documentation/template | Defines abstract envelope, generic fetch patterns, artifact purpose, and a README-linked detailed reference. | Documentation cannot by itself establish runtime compatibility. |
| `config/deploy_contracts/archived/*.json`, stale plans, archived boards | Historical/profile evidence | Filename references exist. | Excluded from current authority. |

There is no verified non-archived deployed `app.js`: active `deploy_root` is null and root `deploy/` is absent. Full browser-consumer compatibility is therefore **INSUFFICIENT EVIDENCE**, not a reason to inspect archived boards.

## Envelope-adapter decision

**NO ADAPTER CURRENTLY JUSTIFIED.** No non-archived runtime consumer or adapter implementation requires the abstract envelope fields. Verified consumers parse detailed round members or filenames only. Under `docs/data_contracts.md:504-508` and `standards/04` §3E, a future adapter/wrapper must be explicitly versioned or backed by an approved producer change.

If future evidence warrants one, select only one explicit responsibility boundary: metadata/classification exposure, field transformation, version translation, or producer mutation. This report selects, designs, and implements none.

## Typed-contract readiness

**Conditionally suitable; insufficiently specified for implementation.** `standards/VENUEDNA_CODEX_SCHEMA.md` has the appropriate authority and patterns: JSON artifact sections (§§1–2), dataclasses (§4), naming (§5), and validation (§7). It has no round/final/cumulative type today.

After detailed authority is approved, a future typed-contract task could add an artifact-family section alongside projection/audit, matching representations in §4, approved naming only if needed, and family validation in §7. It must mirror—not duplicate—the `standards/04` detailed contract.

Prerequisites: approved `standards/04` field interfaces; independent version/compatibility policies for the current `1.1` and `1.0` baselines; a non-archived producer/consumer audit including cumulative state behavior; a purpose decision (documentation, runtime validation, or producer interface); and a focused approved validation plan.

## Library schema and README transition criteria

**Preserve now; no transition or deprecation recommendation.** `README.md:250-252` directly links `library/engine/ROUND_ANALYSIS_SCHEMA.md`, which remains substantial producer compatibility evidence despite partial staleness.

Any future preservation, transition, or deprecation requires: (1) an approved detailed replacement in `standards/04`, including final and null/optional treatment; (2) resolved producer-to-contract deltas; (3) disposition for every verified non-archived consumer/template; (4) an appropriate compatibility test/design; and (5) an expressly authorized README/library transition with link/path validation. Without all five, deprecation is **BLOCKED**.

## Non-actions and unresolved blockers

- No field, type, nesting, optionality, missing-value, version, or compatibility decision was made.
- No code, test, adapter/wrapper, deploy asset, README, library schema, database, event, archive, fixture, migration, branch, Git configuration, commit, or push changed.
- No archived board was inspected or used as authority; no Wyndham fixture path was opened or modified.
- No active event/non-archived deployed board exists to establish complete browser compatibility.
- The final artifact currently reuses a round construction, but final-specific detailed required/optional rules are absent.

## Required validation and final diff evidence

After this report was created, the handoff requires these commands:

```text
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
git status --short
git diff --name-only
git diff -- scripts/handoffs/reports/2026-08-12_round_cumulative_schema_strategy_discovery_REPORT.md
```

Their exact results and final diff evidence are recorded in the completion response.
