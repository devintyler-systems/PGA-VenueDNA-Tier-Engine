# Codex Handoff — Round-Analysis Schema Authority Decision (READ-ONLY)

- **Date:** 2026-08-12
- **Author:** Perplexity (planning/control plane)
- **Executor:** Claude Code / Codex
- **Mode:** READ-ONLY, DECISION-ONLY GOVERNANCE REVIEW
- **Active-event requirement:** Re-confirm `config/active_event.json` is `NO_ACTIVE_EVENT` before starting. This is event-neutral work. Do not initialize an event, create projections, or create an event-bound/live artifact.

## Objective

Produce a governance decision report that confirms or rejects the proposed authority model for detailed round-analysis and cumulative-learning interfaces before any remediation is authorized. This task may document a recommended future contract/migration plan; it must not edit doctrine, contracts, code, tests, payloads, deploy files, event state, or legacy files.

The prior evidence baseline is committed at `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md` in commit `2e83b0fbf4c439c4a345d967cc56f34ddc31dc92`. Treat it as evidence, not as governing authority. Its implementation facts are: `engine/build_round_analysis.py` emits the current detailed schema-1.1 round artifact and schema-1.0 cumulative-learning artifact; `library/engine/ROUND_ANALYSIS_SCHEMA.md` is README-linked but stale; `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` and `docs/data_contracts.md` specify materially incompatible shapes.

## Proposed Authority Model to Evaluate

1. `engine/build_round_analysis.py` is implementation truth for fields currently emitted; it is not doctrine authority.
2. `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` is the proposed eventual canonical, versioned detailed-interface authority for `rN_analysis` / final analysis and `cumulative_learning` artifacts.
3. `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` governs learning-loop behavior, cadence, interpretation, audit/write-back rules, and references the detailed artifact contract instead of duplicating it.
4. `docs/data_contracts.md` governs producer-consumer boundaries and must eventually state whether its generic live-artifact envelope applies directly, is adapted by a wrapper, or is inapplicable to round-analysis payloads; it may not silently conflict with the detailed versioned artifact interface.
5. `library/engine/ROUND_ANALYSIS_SCHEMA.md` remains a preserved README-linked compatibility reference until a separately authorized migration completes. Do not rename, deprecate, move, or edit it in this pass.
6. `README.md` remains navigation only and must not declare a lower-tier document the complete interface authority after a future canonical migration.

## Required Pre-Execution Checks

1. Confirm `config/active_event.json` status is exactly `NO_ACTIVE_EVENT`; otherwise stop.
2. Confirm the local handoff file exists and local `HEAD` is synchronized to the commit containing it, per `SYSTEM_HANDOFF_SPEC.md`. Run `git status`, `git log -1 --format=%H`, `git fetch origin && git log origin/main -1 --format=%H`, and `git status --porcelain`.
3. If the worktree is not clean before the review, stop and report. Do not stash, discard, or commit unrelated work.

## Exact Files to Inspect

- `AGENTS.md`
- `CLAUDE.md`
- `PERPLEXITY_OPERATING_PROTOCOL.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `README.md`
- `library/engine/ROUND_ANALYSIS_SCHEMA.md`
- `engine/build_round_analysis.py`
- `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md`

Repository code governs implementation facts. Canonical standards govern doctrine. Apply the established authority hierarchy; if any source conflicts with the proposed model, identify the higher governing authority and stop short of remediation.

## Required Analysis

1. Verify whether the proposed `standards/04` detailed-interface authority conflicts with a higher-ranked instruction, standard, or typed contract.
2. Deliver a precise ownership matrix for `standards/03`, `standards/04`, `docs/data_contracts.md`, `VENUEDNA_CODEX_SCHEMA.md`, `engine/build_round_analysis.py`, `library/engine/ROUND_ANALYSIS_SCHEMA.md`, and `README.md`. Distinguish doctrine, detailed schema, generic boundary contract, implementation truth, and navigation/reference roles.
3. State a recommended migration sequence with explicit dependency ordering. Cover, at minimum: versioning, backward compatibility, read/write producer obligations, adapter/envelope decision, consumer/deploy discovery, tests, README/library-reference transition, and legacy-file preservation.
4. Determine whether any producer change is necessary now. Expected default: no producer change in this decision-only pass; separate required changes into deferred, conditional, and explicitly out-of-scope categories.
5. Produce a protected-file change matrix for a future implementation handoff. For each candidate file, state why it might change, what decision must precede that change, validation required, and whether its change is mandatory, conditional, or prohibited.
6. Identify exact decision gates that must be approved by the repository owner before a future implementation handoff can be drafted.

## Protected Files and Actions

Do not edit any existing file. Do not change code, tests, payloads, deploy assets, schemas, standards, README, event state, database, source manifests, library files, archived data, or fixtures. Do not initialize an event. Do not run `git add`, `git commit`, `git push`, `git stash`, `git reset`, `git clean`, or any destructive command.

The only authorized file creation is the final report named below.

## Validation / Inspection Commands

Run and record results; do not remediate failures:

```text
git status
git log -1 --format=%H
git fetch origin && git log origin/main -1 --format=%H
git status --porcelain
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
```

## Stop Conditions

Stop and issue only a blocked report if:

- Active-event status is not `NO_ACTIVE_EVENT`.
- The local worktree is not synchronized with the handoff’s remote commit.
- The worktree is not clean at review start.
- The proposed authority model conflicts with a higher governing source and the conflict cannot be resolved by interpretation alone.
- A recommendation would require modifying a protected contract to establish its own premise.
- Evidence needed to decide whether the generic live envelope applies is absent; name the missing consumer/adapter evidence rather than inferring it.

## Required Final Report

Create only:

`script/handoffs/reports/2026-08-12_round_analysis_schema_authority_decision_REPORT.md`

**Correction:** The exact authorized output path is:

`scripts/handoffs/reports/2026-08-12_round_analysis_schema_authority_decision_REPORT.md`

Include: executive ruling; authority-hierarchy evidence; ownership matrix; proposed-model verdict; future migration sequence; producer-change classification; future protected-file change matrix; decision gates; validation evidence; and blockers/unknowns. Clearly distinguish facts from recommendations.

## Commit / Push Authorization

None. Codex may create the report locally only. It must not stage, commit, or push the report. The repository owner must separately review and explicitly authorize any report commit or implementation handoff.
