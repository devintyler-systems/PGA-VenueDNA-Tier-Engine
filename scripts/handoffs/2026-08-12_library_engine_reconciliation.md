# Codex Handoff: Reconcile library/engine/ Legacy Docs vs standards/ Canonical Files
Date: 2026-08-12
Author: Perplexity (per PERPLEXITY_OPERATING_PROTOCOL.md)

## Objective
Reconcile library/engine/ legacy numbered docs against standards/ canonical docs; identify duplicates, superseded drafts, and any content standards/ is missing. Read-only report, no file changes, deletions, or merges authorized in this task.

## Active Event
NO_ACTIVE_EVENT (per config/active_event.json, confirmed 2026-08-12). No event-bound work is in scope.

## Files to Inspect (library/engine/)
- 00_MASTER_SYSTEM_ARCHITECTURE.md vs standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md
- 01_PGA_VENUEDNA_MASTER_SPACE_PROMPT_v1.1.md and 01_SYSTEM_PROMPT_FULL.md (no standards/01 exists - confirm intentional gap)
- 02_PGA_VENUEDNA_SCORING_SPEC_historical.md + 02_VTS_SCORING_ENGINE.py vs standards/02_PGA_VENUEDNA_SCORING_SPEC.md
- 03_PGA_VENUEDNA_LEARNING_LOOP.md + 03_PERPLEXITY_REBUILD_GUIDE.md vs standards/03_PGA_VENUEDNA_LEARNING_LOOP.md
- 04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md + 04_QUICK_REFERENCE_CARD.md vs standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
- 05_PGA_VENUEDNA_SPACE_SETUP_GUIDE.md vs standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md (different topics - confirm not miscategorized)
- 06_PGA_VENUEDNA_EVENT_WORKFLOW.md vs SYSTEM_HANDOFF_SPEC.md and README.md runbook content
- 07_PGA_VENUEDNA_AUDIT_STANDARD.md vs standards/03_PGA_VENUEDNA_LEARNING_LOOP.md (audit classification doctrine)
- PGA_VENUEDNA_SYNC_CHECK_2026-06-24.md (dated point-in-time note - assess for archival)
- ROUND_ANALYSIS_SCHEMA.md (README.md references this directly as current - confirm still accurate, not a duplicate)

## Authorized Files
None. This is a read-only task; no writes to any existing file are authorized.

## Protected Files
All files in standards/, library/engine/, README.md, AGENTS.md, CLAUDE.md, SYSTEM_HANDOFF_SPEC.md — do not modify, rename, or delete any file.

## Expected Artifact
A single markdown report at `scripts/handoffs/reports/2026-08-12_library_engine_reconciliation_REPORT.md` containing, per file pair:
1. Whether the library/engine/ version is superseded, duplicate, additive/unique, or miscategorized.
2. Specific content differences worth preserving if superseded.
3. A proposed disposition (archive, promote content into standards/, deprecate with pointer, or keep as-is) — proposals only, no action taken.

## Allowed Impact
None on scoring, payload, identity, deploy, database, or event state. This is a documentation audit only.

## Validation Commands
None required (no code changes). Confirm the report file is committed and readable.

## Stop Conditions
Stop and report if any library/engine/ file appears to be actively referenced by production code (grep the repo for filename references) — flag rather than assume it is safe to deprecate.

## Required Final Report
- List of files reviewed.
- Disposition proposed per file.
- Any files still referenced by app.js / engine scripts / README.md that block deprecation.
- Open questions for operator decision.

## Commit/Push Authorization
This handoff file only, committed by Perplexity. The REPORT.md this task produces should be committed by Codex per standard workflow; no other repo changes are authorized.
