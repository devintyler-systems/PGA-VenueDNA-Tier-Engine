# Codex Handoff — Round-Analysis Schema Synchronization (READ-ONLY)

- **Date:** 2026-08-12
- **Author:** Perplexity (planning/control plane)
- **Executor:** Claude Code / Codex
- **Mode:** READ-ONLY INVESTIGATION — no code, doctrine, schema, or contract changes authorized
- **Active event status:** `NO_ACTIVE_EVENT` (verified in `config/active_event.json` prior to drafting this handoff). This task is event-neutral. Do not initialize an event, create projections, or create any event-bound or live artifact as part of this work.

## Objective

Produce a field-level reconciliation report on the round-analysis schema: what `engine/build_round_analysis.py` actually emits versus what is documented across `library/engine/ROUND_ANALYSIS_SCHEMA.md`, `README.md`, `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`, `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`, `standards/VENUEDNA_CODEX_SCHEMA.md`, and `docs/data_contracts.md`. This continues, and must not re-litigate from scratch, the conflict already logged in `scripts/handoffs/reports/2026-08-12_library_engine_reconciliation_REPORT.md`, which found that the producer emits weather/wave metadata and a `live_probability_engine` block not present in the documented schema, additional trait-audit live-proxy/enrichment detail, and that `standards/03` shows a simpler, different round-artifact example than the detailed schema doc.

This handoff authorizes **investigation and reporting only**. It does not authorize resolving the authority conflict, editing any schema/doctrine file, or altering the producer.

## Pre-Execution Checks (required before any inspection)

1. Re-confirm `config/active_event.json` still reads `NO_ACTIVE_EVENT`. If it does not, stop and report the discrepancy — do not proceed.
2. Confirm the local worktree is synchronized with the remote commit referencing this handoff, per `SYSTEM_HANDOFF_SPEC.md`: run `git status`, `git log -1 --format=%H`, and confirm the local branch matches `origin/main` (`git fetch origin && git log origin/main -1 --format=%H`). If this handoff file is not present locally, or local/remote diverge, **stop** — do not create a substitute handoff or touch the worktree.
3. Confirm the working tree is clean (`git status --porcelain` empty) before starting. If it is not clean, stop and report what is dirty; do not stash, discard, or commit unrelated changes.

## Files to Inspect (exact paths — do not guess alternates)

- `engine/build_round_analysis.py` — the producer; ground truth for every field actually emitted (name, type, nesting, source computation).
- `library/engine/ROUND_ANALYSIS_SCHEMA.md` — current documented detailed interface.
- `README.md` — locate and quote its round-analysis references verbatim.
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` — canonical learning-loop doctrine; contains a simpler round-artifact example that must be compared, not assumed superseded.
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` — canonical artifact schema doctrine.
- `standards/VENUEDNA_CODEX_SCHEMA.md` — canonical typed code/artifact contract doctrine.
- `docs/data_contracts.md` — canonical producer-consumer boundary contract. Note: this file lives at `docs/data_contracts.md`, not at repo root; verify this path independently and flag if it has moved again.
- `AGENTS.md`, `CLAUDE.md`, `PERPLEXITY_OPERATING_PROTOCOL.md`, `SYSTEM_HANDOFF_SPEC.md` — doctrine/authority context only; read for hierarchy and handoff-sync rules, do not treat as schema sources.
- `scripts/handoffs/reports/2026-08-12_library_engine_reconciliation_REPORT.md` — prior finding; treat as existing evidence and build on it rather than re-deriving independently.

## Protected Files (no edits under any circumstance in this pass)

All files listed above, plus: all files under `engine/`, `library/`, `tests/`, `deploy/`, `data/` (including `data/venue_dna.db`, which is not the production master but is still protected here), `config/active_event.json`, any source manifest file, all `standards/*.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `PERPLEXITY_OPERATING_PROTOCOL.md`, `SYSTEM_HANDOFF_SPEC.md`, and any archived/historical artifact. The only file this handoff authorizes creating is the report named below.

## Required Investigation Steps

1. **Inventory the producer.** Walk `engine/build_round_analysis.py` and list every field it emits into the round-analysis artifact, including nested structures, with type and computed meaning. Pay specific attention to:
   - weather/wave metadata (e.g. `wave`, tee-time-wave classification, any weather-conditions fields)
   - the `live_probability_engine` block and every sub-field within it
   - `trait_audit` and any live-proxy/enrichment sub-fields beyond the base trait audit
   - all round-level and cumulative-learning structures (e.g. `round_sources`, `live_lean_notes`, `match_summary`, `model_performance`, `leaderboard_snapshot`, and any cumulative/rolling learning fields)
2. **Inventory the documentation.** For each of `ROUND_ANALYSIS_SCHEMA.md`, README's round-analysis section, `standards/03`, `standards/04`, `VENUEDNA_CODEX_SCHEMA.md`, and `docs/data_contracts.md`, list every round-analysis field each one documents or references.
3. **Diff and classify every discrepancy** into exactly one of:
   - Documented field absent from the producer (stale doc)
   - Producer-emitted field absent from all documentation (undocumented)
   - Type, meaning, or nesting mismatch between producer and a doc (name each doc)
   - Authority conflict — two or more doctrine/reference sources disagree with each other independent of the producer (e.g. standards/03's simpler example vs. the detailed schema doc)
4. **Verify every path reference** cited in README, standards, and `VENUEDNA_CODEX_SCHEMA.md` for the round-analysis schema and `data_contracts.md` actually resolves to the real current file path before this report recommends any move, rename, deprecation, or authority change. Do not assume any documented path is current; check it.
5. **Do not propose a resolution.** Present the reconciliation findings and exactly the following three labeled alternatives, with evidence-based pros/cons for each, plus one recommendation:
   - **A.** Retain `library/engine/ROUND_ANALYSIS_SCHEMA.md` as the detailed interface authority and update it to match the producer.
   - **B.** Migrate/reconcile the detailed schema into canonical `standards/` (specify which standard: 03 vs. 04 vs. a new file) so there is one authority tier.
   - **C.** A different minimal-safe model, only if the evidence in this repo specifically supports it (state the evidence).
6. **State confidence and evidence basis** for each finding — cite exact file paths and line-level or field-level evidence, not general impressions.

## Validation / Inspection Commands (read-only; run, do not remediate failures)

```
git status
git log -1 --format=%H
git fetch origin && git log origin/main -1 --format=%H
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
git diff --check
```

Record the output of each command in the report's "Validation Evidence" section. If any command fails or reveals divergence, log it — do not attempt to fix it.

## Stop Conditions

Stop and report without proceeding further if any of the following occurs:
- `config/active_event.json` is anything other than `NO_ACTIVE_EVENT`.
- The local worktree is not synchronized with the remote commit that introduced this handoff (per `SYSTEM_HANDOFF_SPEC.md`).
- The working tree is not clean at the start of the task.
- Resolving a discrepancy found during inventory would require altering a protected contract (any file in the Protected Files list) to complete the report — in that case, describe the blocked step and the exact contract at risk, and stop; do not edit around it.
- Venue intelligence or reconstruction inputs needed to interpret a field's meaning are missing — state what is missing rather than guessing.

## Required Final Report

- **Path (exact, only file this handoff authorizes creating):** `scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md`
- **Contents:** producer field inventory; documentation field inventory per source; full discrepancy table classified per the four categories above; path-verification results; the three labeled alternatives (A/B/C) with evidence and a recommendation; validation command outputs; explicit list of anything left unresolved or blocked, with the governing stop condition cited.

## Commit / Push Authorization

**None granted by this handoff.** Codex may create the single report file above in the local working tree only. Do not run `git add`, `git commit`, or `git push` for this task. Do not modify, move, rename, or delete any other file. A human (the repo owner) will review the report and issue a separate, explicit approval before any commit or push of the report — or of any follow-up remediation — occurs.
