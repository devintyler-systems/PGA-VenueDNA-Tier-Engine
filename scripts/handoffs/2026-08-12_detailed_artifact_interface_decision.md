# Detailed Artifact Interface Decision Handoff

- **Date:** 2026-08-12
- **Mode:** Event-neutral, decision-only, report-only
- **Active event:** Must remain `NO_ACTIVE_EVENT`.
- **Repository:** `devintyler-systems/PGA-VenueDNA-Tier-Engine`
- **Branch:** `main`

## Objective

Produce a path-attributed decision report defining the proposed detailed canonical interface model that may later be incorporated into `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` for `rN_analysis`, `final_analysis`, and `cumulative_learning`.

This task decides the proposed interface model only. It does not authorize editing `standards/04`, any other standard, code, tests, contracts, README, library schema, deploy surface, database, event state, payload, adapter/wrapper, typed contract, or migration.

## Required synchronization gate

Before local discovery, run:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
Test-Path scripts/handoffs/2026-08-12_detailed_artifact_interface_decision.md
```

Do not begin unless `HEAD` equals `origin/main`, the worktree is clean, the handoff exists locally, and `config/active_event.json` remains `NO_ACTIVE_EVENT`.

## Required authority and evidence

Inspect:

- `config/active_event.json`
- `AGENTS.md`, `CLAUDE.md`, `PERPLEXITY_OPERATING_PROTOCOL.md`, and `SYSTEM_HANDOFF_SPEC.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `README.md`
- `library/engine/ROUND_ANALYSIS_SCHEMA.md`
- `engine/build_round_analysis.py`
- the committed discovery handoff and report at `scripts/handoffs/2026-08-12_round_cumulative_schema_strategy_discovery.md` and `scripts/handoffs/reports/2026-08-12_round_cumulative_schema_strategy_discovery_REPORT.md`
- the Decision D handoff and report
- relevant non-archived producer, validator, shim, consumer, template, and test evidence discovered by bounded search.

Do not inspect or use archived boards as current consumer authority. Do not open or modify `events/2026_wyndham_championship/`.

## Required decisions

The report must provide a proposed canonical interface matrix for each family, backed by producer paths/symbols and classifying every top-level and material nested member as one of:

- required;
- optional but stable;
- source-contingent with exact null, empty-array, or absent-member behavior;
- legacy compatibility member; or
- unresolved and requiring a later explicit decision.

It must decide or explicitly hold the following:

1. Whether R1-R4 share one `rN_analysis` detailed version line and the precise condition for a future split.
2. Whether `final_analysis` is an independently versioned family, a terminal variant, or another defined relationship; include the proposed minimum final-specific metadata and the exact unresolved R4-parity boundary.
3. The independent `cumulative_learning` state-document interface: initialization, read/update/write behavior, version persistence, state upgrade requirements, and final-state semantics.
4. Proposed compatibility policy per family: what constitutes non-breaking, breaking, deprecation, translation, and future migration prerequisites. Do not choose a new schema number.
5. The division of authority: `standards/04` detailed field/interface/version policy; `standards/03` cadence, interpretation, audit, and write-back; `docs/data_contracts.md` producer-consumer and abstract-envelope boundary.
6. Typed-contract readiness boundary: what a later `VENUEDNA_CODEX_SCHEMA.md` mirror would need, while creating no typed definitions.
7. Preservation conditions for `library/engine/ROUND_ANALYSIS_SCHEMA.md` and README references; no transition/deprecation action.
8. Generic-envelope ruling. Preserve `NO ADAPTER CURRENTLY JUSTIFIED` unless newly verified non-archived runtime evidence proves a concrete consumer requirement. No adapter design or implementation.

## Authorized output

Only create or modify:

```text
scripts/handoffs/reports/2026-08-12_detailed_artifact_interface_decision_REPORT.md
```

The report must include: preflight; authority hierarchy; current compatibility baseline; three proposed family matrices; final-versus-R4 ruling; independent compatibility policies; envelope/adapter ruling; typed-contract boundary; library/README preservation conditions; non-actions; blockers; and the narrowest follow-on implementation decision.

## Protected files

Do not modify `standards/**`, `docs/data_contracts.md`, `README.md`, `library/engine/ROUND_ANALYSIS_SCHEMA.md`, `engine/**`, `tests/**`, `config/**`, `data/**`, `deploy/**`, `events/**`, existing handoffs/reports, or any database/configuration file.

## Validation

```powershell
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
git status --short
git diff --name-only
git diff -- scripts/handoffs/reports/2026-08-12_detailed_artifact_interface_decision_REPORT.md
```

The report must be the sole local modification. State any unavailable command or failure; do not remediate outside scope.

## Stop conditions

Stop and report `BLOCKED` without remediation if active state changes; sync/clean/handoff gates fail; governing authorities conflict; current evidence is only archival/stale documentation; a decision requires a producer, adapter, schema, library, README, or deploy change; or the Wyndham fixture cannot be demonstrated untouched.

## Commit and push boundaries

Perplexity commits this handoff only. The local worktree must pull and verify it before execution. Codex/Claude may write only the authorized report locally and may not commit, push, create branches, alter Git configuration, or make any other change. The report remains uncommitted pending separate repository-owner approval.

## Required final response

Return files changed, behavior changed, intentionally unchanged files, preflight and validation results, data-contract impact, migration requirement, deploy/manual steps, open risks, and recommended narrowest next decision.