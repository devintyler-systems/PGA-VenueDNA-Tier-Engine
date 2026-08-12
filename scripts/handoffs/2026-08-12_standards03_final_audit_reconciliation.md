# Codex Handoff: Reconcile Final-Audit and Write-Back Policy into `standards/03`

Date: 2026-08-12  
Author: Perplexity, under `PERPLEXITY_OPERATING_PROTOCOL.md`

## Objective

Perform a doctrine-only reconciliation that updates `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` with selectively adopted final-audit and write-back policy from the legacy reference documents listed below.

The goal is one canonical authority for both live learning and final audit/write-back discipline. Do not create a new numbered standard.

## Active Event and Repository State

- Active event: `NO_ACTIVE_EVENT` per `config/active_event.json`.
- Event-bound projections, live artifacts, deploy changes, and event initialization are out of scope.
- Local execution prerequisite: before work, verify the local checkout contains this handoff and is synchronized with the intended GitHub commit, per `SYSTEM_HANDOFF_SPEC.md`.

## Authority and Files to Inspect

Read these before editing:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `PERPLEXITY_OPERATING_PROTOCOL.md`
4. `SYSTEM_HANDOFF_SPEC.md`
5. `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` — target canonical standard
6. `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
7. `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
8. `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
9. `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
10. `library/engine/03_PGA_VENUEDNA_LEARNING_LOOP.md` — legacy reference evidence only
11. `library/engine/07_PGA_VENUEDNA_AUDIT_STANDARD.md` — legacy reference evidence only
12. `scripts/handoffs/reports/2026-08-12_library_engine_reconciliation_REPORT.md`
13. `docs/data_contracts.md`

## Authorized Files

- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `scripts/handoffs/reports/2026-08-12_standards03_final_audit_reconciliation_REPORT.md`

## Protected Files

Do not modify, rename, delete, or move:

- Any file in `library/engine/`, including legacy `03` and `07`
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `SYSTEM_HANDOFF_SPEC.md`, `PERPLEXITY_OPERATING_PROTOCOL.md`
- All Python, JavaScript, HTML, CSS, test, database, config, event, venue-library, deploy, and raw-data files

## Required Canonical Additions

Preserve the existing live-learning, round-artifact, and cumulative-learning rules in `standards/03`. Add a clearly labeled final-audit/write-back section that uses current VenueDNA v2 terminology and includes only reconciled policy for:

1. Tier 1 and Tier 2 accountability review against outcomes.
2. Structured material-miss classification at the correct layer: NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalty/gate, debut framework, data/completeness, conditions, variance, or Model Council.
3. Anti-pattern review, including direction, magnitude, and stated setup/conditions modifiers where evidence supports them.
4. Risk-mechanism and probability-calibration review, without inventing probabilities or using derivative-market outcomes as core-model evidence.
5. Explicit separation of venue-specific proposed write-backs from global engine-rule flags.
6. Evidence basis, evidence threshold, uncertainty, and a rule that one-event anecdotes do not change venue or engine doctrine.
7. Proposed-only write-backs requiring operator approval before canonical venue/profile or engine-rule changes.
8. Explicit decision statuses for each material finding: confirm, downgrade, promote, hold, proposed venue write-back, proposed engine-rule research, or logged no-change.
9. Council role at audit: challenge layer only; it may not replace canonical scoring, cure missing evidence, or convert consensus/market information into core-rank changes.

## Prohibitions

Do not:

- Change scoring formulas, weights, penalties, gates, tiers, probabilities, or current v2 component semantics.
- Reintroduce VTS score thresholds, fixed score bands, legacy venue dictionaries, market/odds/DFS/DraftKings logic, or automatic write-backs.
- Change source-manifest rules, identity rules, deploy JSON/CSV contracts, round-artifact schemas, current payload field names, code, tests, database behavior, or event state.
- Copy legacy terminology or stale artifact examples into canonical doctrine without reconciling it to current contracts.
- Create a new `standards/06` or `standards/07` file.
- Treat the legacy documents as co-equal canonical authority.

## Implementation Plan

Before editing, state a plan of no more than five bullets. Make the smallest coherent standards/03-only change that satisfies the required additions and does not duplicate or conflict with standards/02, 04, or 05.

## Validation

Run:

```powershell
python tools/validate_scoring_doctrine.py
python -m pytest tests/test_doctrine_contract.py -q
```

If either command is unavailable, fails for an environmental reason, or reveals a pre-existing failure, stop and report the exact blocker/failure. Do not weaken a test or validator to make this documentation update pass.

Also run:

```powershell
git diff --check
git diff -- standards/03_PGA_VENUEDNA_LEARNING_LOOP.md
```

## Expected Artifact and Commit Scope

1. Updated `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`.
2. Reconciliation report at `scripts/handoffs/reports/2026-08-12_standards03_final_audit_reconciliation_REPORT.md`, stating:
   - exact sections added/changed;
   - legacy policy selectively adopted;
   - legacy policy intentionally excluded and why;
   - validation commands and results;
   - confirmation that scoring, payload, identity, deploy, database, and event state did not change.

Commit only those two authorized files in one commit. Push is authorized only after both validations pass.

## Stop Conditions

Stop and report—do not commit—if:

- Required policy conflicts with standards/02, 04, 05, the code schema, or current active-event rules.
- The needed policy would require changes outside the authorized files.
- Validation fails for a non-environmental reason.
- The local checkout lacks this handoff or diverges from the intended remote state.

## Required Final Response

Return:

1. Files changed.
2. Canonical behavior/documentation changed.
3. Legacy content adopted and legacy content intentionally excluded.
4. Files intentionally not changed.
5. Validation results.
6. Data-contract, scoring, database, deploy, and event-state impact.
7. Commit SHA and push result.
8. Open risk or deferred follow-up.
