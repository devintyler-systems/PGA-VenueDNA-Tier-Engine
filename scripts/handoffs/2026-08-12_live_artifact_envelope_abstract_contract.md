# Codex Handoff — Abstract Live Artifact Envelope Contract (Decision D)

- **Date:** 2026-08-12
- **Mode:** Decision-authorized, non-code doctrine/contract reconciliation
- **Active event:** Must remain `NO_ACTIVE_EVENT`; this is event-neutral work.
- **Decision basis:** Repository owner selected Decision D: define the generic Live Artifact envelope relationship abstractly before an active consumer exists. Evidence baseline: `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md` and `scripts/handoffs/reports/2026-08-12_round_analysis_schema_authority_decision_REPORT.md`.

## Objective

Implement Decision D only. Establish a canonical abstract distinction between the generic Live Artifact envelope/interface class and detailed, independently versioned round-analysis and cumulative-learning artifact types. Do not infer a current consumer, create an adapter, alter a producer payload, select a field-level migration, or change an active event/deploy surface.

## Required Prechecks

1. Confirm `config/active_event.json` is exactly `NO_ACTIVE_EVENT`; otherwise stop.
2. Confirm local handoff presence, local/remote synchronization, and a clean worktree under `SYSTEM_HANDOFF_SPEC.md`.
3. Inspect the exact authority and evidence files below before editing anything.

## Files to Inspect

- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `PERPLEXITY_OPERATING_PROTOCOL.md`
- `config/active_event.json`
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `tests/test_doctrine_contract.py`
- `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md`
- `scripts/handoffs/reports/2026-08-12_round_analysis_schema_authority_decision_REPORT.md`

## Authorized Files

Only these existing files may be modified, and only for the bounded Decision D objective:

- `docs/data_contracts.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `tests/test_doctrine_contract.py` — only if a focused doctrine-contract assertion is required by the approved abstract authority/boundary decision

The executor may also create only this report:

- `scripts/handoffs/reports/2026-08-12_live_artifact_envelope_abstract_contract_REPORT.md`

## Required Contract Outcome

1. Define the generic Live Artifact envelope as a logical wrapper/interface class, not an assertion that every live producer directly emits that exact top-level JSON shape.
2. Assign detailed, versioned `rN_analysis`, final-analysis, and cumulative-learning artifact interfaces to `standards/04` as independently versioned artifact types.
3. State that a future consumer requiring the generic envelope must use an explicitly versioned adapter/wrapper or an approved producer change; no adapter, wrapper, or producer change is authorized now.
4. Reconcile `standards/03` so it retains learning-loop cadence, interpretation, audit, and write-back doctrine but does not independently prescribe a conflicting detailed payload. Use a precise normative reference to the authority in `standards/04`; do not introduce detailed round/cumulative field tables in standards/03.
5. Preserve current producer payload behavior and the README-linked library schema as compatibility evidence pending a separate authorized versioned migration.
6. State explicitly that archived consumers are evidence only and cannot establish present consumer compatibility or adapter requirements.
7. Do not decide field-level round/cumulative schema content, current schema-version compatibility, producer output migration, or consumer implementation requirements.

## Protected Files and Prohibitions

Do not modify: `engine/build_round_analysis.py`; any other code; `deploy/` or `deploy/data/`; `README.md`; `library/engine/ROUND_ANALYSIS_SCHEMA.md`; `standards/VENUEDNA_CODEX_SCHEMA.md`; source manifests; databases; `events/`; archives; fixtures; `config/active_event.json`; or any unrelated test/document.

Do not initialize an event. Do not create a payload, adapter, wrapper, deploy asset, schema sample, event artifact, or code. Do not move, rename, deprecate, or delete a file. Do not use archived consumers as an authority source.

## Validation

Run and record:

```text
git status
git log -1 --format=%H
git fetch origin && git log origin/main -1 --format=%H
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
```

Also inspect the final diff and verify it modifies only authorized files and the authorized report.

## Stop Conditions

Stop and issue a blocked report only if:

- active event is not `NO_ACTIVE_EVENT`;
- local/remote or clean-worktree checks fail;
- a higher authority conflicts with Decision D;
- resolving the abstract boundary requires field-level payload decisions, a producer/adapter/deploy change, or selection of an archived consumer as current authority;
- the required wording would alter any protected file.

## Required Final Report

Create `scripts/handoffs/reports/2026-08-12_live_artifact_envelope_abstract_contract_REPORT.md` with: exact files changed; authority evidence; resulting abstract-contract rules; explicit non-goals/preserved contracts; test and validation output; diff summary; no-change confirmation for protected files; and future decision gates for detailed schema migration.

## Commit / Push Authorization

No commit or push is authorized. Codex may leave only the authorized file modifications and report in the local worktree for owner review. The owner must separately authorize any commit after reviewing the report and diff.
