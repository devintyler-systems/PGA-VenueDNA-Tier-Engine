# Round and Cumulative Schema Strategy Discovery Handoff

- **Date:** 2026-08-12
- **Mode:** Read-only, evidence-driven discovery and decision report
- **Active event:** Must remain `NO_ACTIVE_EVENT`; this is event-neutral governance work.
- **Branch:** `main`
- **Repository:** `devintyler-systems/PGA-VenueDNA-Tier-Engine`

## Objective

Produce a path-attributed decision report establishing the evidence required before any detailed schema migration, typed-artifact contract, producer change, adapter/wrapper, README transition, or library-schema transition can be authorized for `rN_analysis`, final-analysis, and `cumulative_learning`.

This task authorizes discovery and the sole report artifact below. It does not authorize a schema version selection, field-level detailed schema, migration plan implementation, code change, test change, contract or doctrine edit, README or library edit, adapter/wrapper creation, deploy change, database change, active-event change, event artifact, projection, live analysis, or archival action.

## Required synchronization gate

Before any local inspection, run:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
Test-Path scripts/handoffs/2026-08-12_round_cumulative_schema_strategy_discovery.md
```

Do not begin unless all conditions hold:

- `config/active_event.json` states `NO_ACTIVE_EVENT`.
- `HEAD` equals `origin/main`.
- `git status --short` is empty before execution.
- This exact committed handoff exists locally after the pull.

## Files to inspect

### Authority and governance

- `config/active_event.json`
- `AGENTS.md`
- `CLAUDE.md`
- `PERPLEXITY_OPERATING_PROTOCOL.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `README.md`

### Current producer and compatibility evidence

- `engine/build_round_analysis.py`
- `engine/build_r1_analysis.py`
- `engine/verify_live_feed.py`
- `engine/build_event_package.py`
- `library/engine/ROUND_ANALYSIS_SCHEMA.md`
- Relevant non-archived tests, validation tools, shared adapters, CLI entry points, fixtures, and current deploy/consumer code discovered through bounded repository search.

### Prior evidence and Decision D baseline

- `scripts/handoffs/reports/2026-08-12_library_engine_reconciliation_REPORT.md`
- `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md`
- `scripts/handoffs/reports/2026-08-12_round_analysis_schema_authority_decision_REPORT.md`
- `scripts/handoffs/2026-08-12_live_artifact_envelope_abstract_contract.md`
- `scripts/handoffs/reports/2026-08-12_live_artifact_envelope_abstract_contract_REPORT.md`

## Discovery rules

- Inspect only non-archived consumer/adapter evidence as current-consumer authority.
- Do not inspect or rely on archived event boards as current authority.
- `events/2026_wyndham_championship/` is a protected retrospective fixture: test-only, non-deployable, and not eligible for ordinary archival. Do not modify it.
- Treat `engine/build_round_analysis.py` as implementation truth for emitted payloads, not doctrine authority.
- Treat the generic Live Artifact envelope as an abstract logical interface. It is not evidence that all live producers must emit one common top-level JSON object.
- Treat `standards/04` as the future canonical home for detailed versioned interfaces; treat `standards/03` as the authority for learning-loop cadence, audit, interpretation, and write-back behavior.
- Treat prior reports as evidence, not governing authority.

## Required evidence questions

The report must answer each question with exact paths, relevant symbols or sections, finding, uncertainty, and recommendation or an explicit `INSUFFICIENT EVIDENCE` ruling.

1. **Detailed schema-version strategy.** What distinct artifact families exist or are implied for `rN_analysis`, final-analysis, and `cumulative_learning`? Should their detailed version lines remain independent, share only compatibility policy, or be grouped only under the abstract Live Artifact interface?
2. **Current-payload compatibility.** Which producer-emitted top-level fields, nested blocks, types, optionality rules, file names, and locations must be preserved prior to a future versioned migration?
3. **Representative consumer discovery.** Which non-archived files actually parse, validate, fetch, transform, or otherwise depend on these artifacts? Classify each as executable/runtime consumer, producer, adapter, validator/test, CLI/shim, documentation, or historical evidence.
4. **Generic-envelope adapter/wrapper.** Does a verified current non-archived consumer require the generic Live Artifact envelope? If not, rule `NO ADAPTER CURRENTLY JUSTIFIED`. If a future adapter could be justified, define only a possible responsibility boundary: metadata/classification exposure, field transformation, version translation, or producer mutation. Do not design or implement it.
5. **Typed-contract suitability.** Does `standards/VENUEDNA_CODEX_SCHEMA.md` have sufficient structure and authority to eventually gain typed round/final/cumulative artifact definitions? Identify prerequisites, appropriate placement, versioning conventions, and validation implications without drafting types.
6. **Library schema and README transition.** Determine the evidence conditions for preserving, transitioning, or eventually deprecating `library/engine/ROUND_ANALYSIS_SCHEMA.md` and its README references. No deprecation recommendation may be made without an approved detailed replacement, compatibility audit, and confirmed current-consumer disposition.
7. **Migration readiness.** Identify the smallest next decision after this report: detailed canonical field-level schema, typed-contract design, compatibility-test design, adapter decision, or library/README transition plan.

## Authorized output

The only file that may be created or modified is:

```text
scripts/handoffs/reports/2026-08-12_round_cumulative_schema_strategy_discovery_REPORT.md
```

The report must include:

- Synchronization and active-event preflight evidence.
- Source hierarchy and any conflicts.
- Producer-to-documentation compatibility matrix.
- Consumer/adapter discovery inventory classified by authority.
- Envelope-adapter decision with evidence.
- Typed-contract readiness ruling.
- `ROUND_ANALYSIS_SCHEMA.md` and README preservation/transition/deprecation decision criteria.
- Explicit non-actions and unresolved blockers.
- Narrowest authorized next decision.

## Protected files

Do not modify:

- `standards/**`
- `docs/data_contracts.md`
- `README.md`
- `library/engine/ROUND_ANALYSIS_SCHEMA.md`
- `engine/**`
- `tests/**`
- `config/active_event.json`
- `data/**` and database/configuration files
- `deploy/**` and `events/**/deploy/**`
- All event inputs, outputs, audits, and archived events
- `events/2026_wyndham_championship/**`
- Existing handoffs and reports

## Validation

Run after producing the report:

```powershell
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
git status --short
git diff --name-only
git diff -- scripts/handoffs/reports/2026-08-12_round_cumulative_schema_strategy_discovery_REPORT.md
```

The closeout evidence must show that the new report is the only local modification. State any unavailable command, failure, or environmental blocker exactly; do not remediate outside scope.

## Stop conditions

Stop, make no remediation, and report `BLOCKED` if:

- The active event is not `NO_ACTIVE_EVENT`.
- The local worktree is not clean before execution, `HEAD` differs from `origin/main`, or the committed handoff is absent locally after pull.
- Required governance files conflict materially on ownership or synchronization.
- A proposed current consumer is found only in archived events, stale plans, historical artifacts, or documentation without executable/runtime evidence.
- A payload-shape conflict cannot be assigned to an authority under the stated hierarchy.
- Any conclusion requires a field-level schema, typed-code definition, adapter implementation, producer change, README/library edit, deploy change, or migration decision.
- The Wyndham fixture cannot be demonstrated untouched.

## Commit and push boundaries

- Perplexity has committed this handoff to establish the shared control-plane task.
- The local worktree must pull and verify this exact handoff before execution.
- The executor may write only the authorized report locally.
- Codex/Claude must not commit, push, create a branch, change Git configuration, or modify protected files.
- The report must remain uncommitted until the repository owner separately approves a specific commit action.
- No follow-on implementation is authorized by this handoff.

## Required final report

Return:

1. Files changed.
2. Behavior changed.
3. Files intentionally not changed.
4. Synchronization and validation commands with results.
5. Data-contract impact.
6. Migration requirement.
7. Manual deploy or artifact-copy step.
8. Open risk or unresolved dependency.
9. The report's recommended narrowest next decision.
