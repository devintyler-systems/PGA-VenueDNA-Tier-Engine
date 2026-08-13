# Blocked Report — Round-Analysis Schema Authority Decision

**Date:** 2026-08-12  
**Mode:** read-only governance review  
**Status:** **BLOCKED — no authority decision made**

## Executive ruling

The proposed model is directionally consistent with the repository hierarchy: `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` is a canonical artifact-contract standard and is the appropriate proposed future home for a versioned detailed `rN_analysis` / final-analysis and `cumulative_learning` interface. `engine/build_round_analysis.py` remains implementation truth, not doctrine; `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` should own cadence and learning/audit behavior rather than independently define an incompatible payload; and `README.md` should be navigation only after a canonical migration.

However, this review cannot decide whether `docs/data_contracts.md`'s generic **Live Artifact** envelope applies directly to round-analysis JSON, requires an adapter/wrapper, or is inapplicable. The manifest is `NO_ACTIVE_EVENT` and declares no `deploy_root`; inspection found only archived board consumers. Archived consumers are evidence only under `docs/data_contracts.md:15-26`, not current authoritative consumer evidence. No non-archived consumer/parser or adapter contract establishes the generic envelope's relationship to the round-analysis payload.

This is the handoff's stated stop condition: **evidence needed to decide whether the generic live envelope applies is absent**. Per the instruction, this report stops short of remediation and records no final authority decision.

## Pre-execution and validation evidence

| Check | Result |
|---|---|
| `config/active_event.json` | `status: "NO_ACTIVE_EVENT"` |
| Handoff present locally | Yes: `scripts/handoffs/2026-08-12_round_analysis_schema_authority_decision.md` |
| Local / remote synchronization | `HEAD` = `origin/main` = `29b965735961b50638714198389333320d6efcad` |
| Initial worktree | Clean (`git status --porcelain` empty) |
| `python tools/validate_scoring_doctrine.py` | Passed; one informational `RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED` finding |
| `python -m pytest tests/test_doctrine_contract.py -q` | `121 passed in 13.47s` |
| `git diff --check` | Exit 0; no output |

## Authority-hierarchy evidence

Facts:

- `AGENTS.md` places canonical standards ahead of repository implementation and requires stopping when governing authorities conflict. It identifies `standards/04` as the artifact-structure authority and `docs/data_contracts.md` as a producer-consumer contract.
- `SYSTEM_HANDOFF_SPEC.md` requires conflict identification, governing-authority selection, and no code change before resolution (`SYSTEM_HANDOFF_SPEC.md:181-186`).
- `docs/data_contracts.md:10-26` says it governs interface shape, directs artifact packaging to `standards/04`, typed contracts to `standards/VENUEDNA_CODEX_SCHEMA.md`, and resolves conflicts in the order: approved migration, `AGENTS.md`, `SYSTEM_HANDOFF_SPEC.md`, `VENUEDNA_CODEX_SCHEMA`, `standards/04`, then `docs/data_contracts.md`, current `app.js`, and historical artifacts.
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md:75-81, 131-157` establishes the round-analysis layer and canonical output filenames but not a detailed field contract.
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md:5, 11-18, 108-190` is canonical learning-loop doctrine and currently duplicates a detailed interface that conflicts with the producer.
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:4-16, 259-280` is canonical, scoped to input/output file contracts and deploy-data contracts, and owns schema-version policy. It does not yet enumerate the detailed round-analysis fields.
- `standards/VENUEDNA_CODEX_SCHEMA.md:28-438` defines typed pre-event and audit artifacts, but no detailed round-analysis/cumulative-learning type. It therefore presents no direct typed-schema conflict with the proposed `standards/04` ownership.

Interpretation (not a change): no higher source prohibits a future `standards/04` detailed-interface section. The unresolved issue is instead the lower-ranked but still canonical `docs/data_contracts.md` generic Live Artifact envelope (`docs/data_contracts.md:485-510`), whose applicability must be explicitly decided rather than silently overridden.

## Ownership matrix

| Source | Current role / fact | Proposed future role | Decision status |
|---|---|---|---|
| `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` | Canonical learning cadence, interpretation, audit/write-back policy; currently duplicates a conflicting detailed schema. | Doctrine: cadence, interpretation, audit discipline; reference the detailed contract rather than duplicate it. | Conditional on owner approval. |
| `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` | Canonical artifact packaging, naming, versioning, deploy-data policy; no detailed rN schema now. | Versioned detailed artifact authority for `rN_analysis`, final analysis, and cumulative learning. | Directionally supported; blocked pending envelope decision. |
| `docs/data_contracts.md` | Generic producer-consumer boundary contract; its live-artifact envelope conflicts with the detailed producer shape. | Explicitly define one of direct applicability, wrapper/adapter applicability, or inapplicability to round analysis. | **Undecided / blocker.** |
| `standards/VENUEDNA_CODEX_SCHEMA.md` | Typed contract for pre-event projections and audits; no rN/cumulative type. | Retain typed-code scope unless owner directs a companion typed round schema. | Conditional / no conflict found. |
| `engine/build_round_analysis.py` | Implementation truth: emits schema-1.1 round and schema-1.0 cumulative artifacts. | Continue to implement the approved detailed contract. | No change authorized or necessary in this decision pass. |
| `library/engine/ROUND_ANALYSIS_SCHEMA.md` | README-linked detailed compatibility reference; partially stale. | Preserve unchanged until the future canonical migration and transition are completed. | Protected / prohibited now. |
| `README.md` | Navigation and legacy operator guidance; names the library file as the complete detailed definition (`README.md:252`). | Navigation only; point to the canonical standard after a versioned migration. | Conditional future change. |

## Proposed-model verdict

**Partially confirmed, but not approved for implementation.** The proposed allocation to `standards/04` does not conflict with a higher-ranked standard or typed contract on the inspected evidence. It cannot become a complete authority model until the generic Live Artifact envelope relationship is approved. The repository owner must make that choice before an implementation handoff is drafted.

## Future migration sequence (recommendation only; deferred)

1. Owner decides the envelope relationship: direct detailed payload, adapter/wrapper, or explicitly inapplicable; identify the intended non-archived consumer.
2. Inventory the selected consumer/parser and deploy fetch targets; freeze compatibility requirements and existing artifact samples.
3. Define the target versioning strategy, including explicit compatibility behavior for the current round schema 1.1 and cumulative schema 1.0.
4. Author the detailed interface in `standards/04`, including final-analysis relationship, required/optional fields, null/missing policy, and producer read/write obligations.
5. Amend `standards/03` to retain behavioral doctrine and refer to the versioned interface; reconcile or remove duplicate examples only as part of the same approved migration.
6. Amend `docs/data_contracts.md` to record the approved envelope/adapter decision and producer-consumer boundary.
7. Update or add typed contracts/tests, then validate producer output and every selected board consumer before changing navigation in `README.md` or the preserved library reference.
8. Make the README/library-reference transition only after compatibility validation; retain the library file unchanged until the approved deprecation/preservation decision is complete.

## Producer-change classification

| Category | Determination |
|---|---|
| Necessary now | **None.** This pass authorizes no producer change, and existing output is the implementation evidence baseline. |
| Deferred | Any normalization, field addition/removal, schema-version revision, output rename, or envelope/wrapper emission. |
| Conditional | Producer change only if the owner selects direct generic-envelope compliance or an adapter that must be emitted at producer time, after consumer discovery and migration approval. |
| Explicitly out of scope | Scoring logic, event activation, deploy payload mutation, archived artifact changes, database changes, and remediation of legacy documents. |

## Future protected-file change matrix

| Candidate file | Why it might change | Required preceding decision | Validation | Status |
|---|---|---|---|---|
| `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` | Add the detailed, versioned round/cumulative interface. | Approve `standards/04` ownership and envelope treatment. | Doctrine contract tests; representative artifact validation. | Conditional, likely mandatory after approval. |
| `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` | Remove/reconcile duplicate detailed examples; retain cadence and policy. | Approve the 03/04 boundary and target contract version. | Doctrine tests; review that cadence/audit rules survive. | Conditional, likely mandatory after approval. |
| `docs/data_contracts.md` | State direct, adapter, or inapplicable envelope relationship. | Owner selects envelope treatment and identified consumer evidence supports it. | Contract tests plus consumer/deploy validation. | **Mandatory prerequisite; blocked.** |
| `standards/VENUEDNA_CODEX_SCHEMA.md` | Add typed rN/cumulative objects only if typed-code coverage is selected. | Owner determines typed-contract scope. | Type/schema tests. | Conditional. |
| `engine/build_round_analysis.py` | Align output/version or emit adapter only if target contract requires it. | Approved target shape and compatibility plan. | Targeted builder test, representative regression, output-schema check. | Conditional; prohibited now. |
| `tests/test_doctrine_contract.py` and focused new tests | Enforce approved ownership/path/schema rules. | Approved migration scope. | Relevant pytest subset and full contract suite. | Conditional. |
| Active event deploy `index.html`, `app.js`, `styles.css`, `deploy/data/*` | Update consumers only if discovery finds a contract impact. | Active event, named deploy scope, and compatibility decision. | Fetch/payload checks and board validation at required widths. | Conditional; prohibited now. |
| `README.md` | Replace lower-tier “complete authority” link after canonical interface is live. | Documentation transition and preservation plan approved. | Link/path verification. | Conditional; prohibited now. |
| `library/engine/ROUND_ANALYSIS_SCHEMA.md` | Preserve, update pointer, or deprecate only after transition. | Explicit preservation/deprecation decision. | Link/path and compatibility reference checks. | Conditional; prohibited now. |

## Required repository-owner decision gates

1. Does `docs/data_contracts.md`'s generic Live Artifact envelope apply directly to round-analysis payloads, through a wrapper/adapter, or not at all?
2. What current, non-archived board/API/consumer is the compatibility authority for that answer? If none exists, should a canonical abstract contract be defined before an event consumer is introduced?
3. Approve `standards/04` as the detailed, versioned interface authority and `standards/03` as behavioral doctrine that references it.
4. Choose the version and compatibility policy for current round schema 1.1 and cumulative schema 1.0, including whether they remain supported unchanged.
5. Decide whether `VENUEDNA_CODEX_SCHEMA.md` must gain typed round/cumulative objects.
6. Authorize the future protected-file scope, test plan, representative event/fixture, and any deploy consumer changes.
7. Decide the eventual README/library transition and the preserved legacy reference's final status.

## Missing evidence / blocker detail

The following required evidence is absent:

- An active event deploy root and active `app.js` parser: `config/active_event.json` has `event_slug` and `deploy_root` set to `null`.
- A current adapter/wrapper implementation or contract that maps the generic `docs/data_contracts.md` live envelope to `engine/build_round_analysis.py` output.
- A non-archived consumer declaring whether it reads generic envelope fields (`pre_event_artifact`, `authoritative_spine`, `player_updates`, `conditions_context`, `scenario_fencing`, `diagnostics`) or the detailed round fields.

Archived `2026_3m_open`, `2026_the_open_championship`, `2026_GenesisScottishOpen`, and `2026_TravelersChampionship` boards fetch `rN_analysis.json` and/or `cumulative_learning.json`, which supports historical compatibility only. Under `docs/data_contracts.md:15-26`, these cannot settle a current authoritative consumer decision.

No existing file was modified. No Git staging, commit, push, stash, reset, or clean operation was run.
