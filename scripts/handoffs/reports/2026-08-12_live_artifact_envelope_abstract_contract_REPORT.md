# Live Artifact Envelope Abstract Contract — Decision D Report

**Date:** 2026-08-12
**Decision:** D — define the generic Live Artifact envelope abstractly before an active consumer exists.
**Active event:** `NO_ACTIVE_EVENT` confirmed from `config/active_event.json`.
**Local / remote commit before changes:** `d711a99bdf4eb0ab92587a9b878bfc8861675561` for both local `HEAD` and `origin/main`; initial worktree was clean.

## Result

Decision D is implemented as a doctrine/contract boundary only. The generic Live Artifact envelope is now a logical wrapper/interface class, not a declaration that every live producer must directly emit its members as one shared top-level JSON object.

Detailed, independently versioned `rN_analysis`, final-analysis, and `cumulative_learning` artifact interfaces are assigned to `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`. `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` now governs cadence, interpretation, audit, and write-back doctrine without independently prescribing conflicting detailed round or cumulative JSON shapes.

## Files changed

- `docs/data_contracts.md`
  - Replaced the former direct generic Live Artifact JSON envelope with an abstract interface-class definition.
  - States that future consumers needing the generic boundary require an explicitly versioned adapter/wrapper or approved producer change.
  - States that archived consumers are evidence only and do not establish current compatibility or adapter requirements.

- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
  - Added §3E, making this standard the canonical detailed, versioned-interface authority for round analysis, final analysis, and cumulative learning.
  - Preserves future decisions on fields, compatibility, adapters, and producers for a separately authorized migration.

- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
  - Replaced incompatible detailed round and cumulative schema examples with normative references to `standards/04`.
  - Preserved learning-loop behavior, cadence, interpretation thresholds, final-audit doctrine, and write-back discipline.

No test file changed. A focused assertion was not necessary because the change establishes an abstract contract boundary rather than introducing a new executable validation rule or payload behavior.

## Authority evidence

- `AGENTS.md` assigns artifact structure, names, and packaging to `standards/04`; it requires stopping rather than silently blending conflicting authority.
- `SYSTEM_HANDOFF_SPEC.md` requires explicit conflict resolution before implementation.
- `docs/data_contracts.md` resolves contract conflicts beneath `AGENTS.md`, `SYSTEM_HANDOFF_SPEC.md`, `standards/VENUEDNA_CODEX_SCHEMA.md`, and `standards/04`; it also treats historical artifacts as non-canonical.
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md` establishes the round-analysis layer and filenames but not detailed field shape.
- `standards/VENUEDNA_CODEX_SCHEMA.md` defines typed pre-event and audit contracts only; no conflicting detailed round/cumulative type exists.
- The two prior committed reconciliation reports established that the existing producer and README-linked library schema are compatibility evidence, while `standards/03` and the former generic live envelope were incompatible at field/nesting level.

## Resulting abstract-contract rules

1. The generic Live Artifact envelope describes logical live-artifact concerns, not a universal top-level payload shape.
2. `standards/04` owns detailed, independently versioned interfaces for `rN_analysis`, final-analysis, and `cumulative_learning`.
3. `standards/03` owns learning-loop behavior and refers to the `standards/04` interface authority rather than duplicate detailed payload definitions.
4. A future consumer requiring the generic envelope must receive it through an explicitly versioned adapter/wrapper or an approved producer change.
5. No adapter, wrapper, producer change, field-level schema, current compatibility policy, or consumer implementation is created or selected by Decision D.
6. Current producer output and the README-linked `library/engine/ROUND_ANALYSIS_SCHEMA.md` remain compatibility evidence pending a separately authorized versioned migration.
7. Archived consumers remain evidence only and cannot establish present compatibility or adapter requirements.

## Explicit non-goals and preserved contracts

- `engine/build_round_analysis.py` was not changed; payload behavior is preserved.
- No deploy asset, payload, active-event setting, event, archive, fixture, database, source manifest, README, library schema, or `standards/VENUEDNA_CODEX_SCHEMA.md` file changed.
- No current schema version was selected or reinterpreted.
- No field-level `rN_analysis`, final-analysis, or cumulative-learning interface was defined.
- No active consumer was inferred or selected.
- No adapter/wrapper was created.

## Validation evidence

```text
git status
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified: docs/data_contracts.md
  modified: standards/03_PGA_VENUEDNA_LEARNING_LOOP.md
  modified: standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md

git log -1 --format=%H
d711a99bdf4eb0ab92587a9b878bfc8861675561

git fetch origin && git log origin/main -1 --format=%H
d711a99bdf4eb0ab92587a9b878bfc8861675561

python tools/validate_scoring_doctrine.py
[info] RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED events/2026_wyndham_championship: Wyndham event directory recognized as the sole authorized retrospective-development fixture: NO_ACTIVE_EVENT is preserved, all required fence markers are present, and no output, deploy, or live artifact exists under the fixture root.
SCORING DOCTRINE PASSED (1 warnings)

python -m pytest tests/test_doctrine_contract.py -q
121 passed in 12.80s

git diff --check
Exit 0 (no whitespace errors; Git emitted only local LF-to-CRLF advisory warnings)
```

## Diff and scope summary

The implementation diff modifies only the three authorized existing doctrine/contract files. This report is the only newly created file. No files were staged, committed, pushed, stashed, reset, cleaned, moved, renamed, or deleted.

## Future decision gates

Before a detailed schema migration can be authorized, the repository owner must decide:

1. The specific field-level round, final-analysis, and cumulative-learning interface and its per-artifact version policy.
2. Current-payload compatibility requirements and the representative non-archived consumer(s) to validate.
3. Whether a generic-envelope adapter/wrapper is required, and whether it belongs in a consumer, deploy builder, or producer.
4. Any producer/output, deploy-consumer, typed-contract, test, README, and library-reference transition scope.
5. The compatibility/deprecation disposition for `library/engine/ROUND_ANALYSIS_SCHEMA.md` without altering it prematurely.
