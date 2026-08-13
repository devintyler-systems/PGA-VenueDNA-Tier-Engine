# Standards/04 Detailed Artifact Interface Implementation Handoff

## Scope
Event-neutral; `config/active_event.json` must remain `NO_ACTIVE_EVENT`. Implement only the approved detailed artifact-interface doctrine in `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`, using the committed decision report `scripts/handoffs/reports/2026-08-12_detailed_artifact_interface_decision_REPORT.md` as the decision baseline.

Before work: fetch, switch `main`, pull `--ff-only`, require clean status, `HEAD = origin/main`, and verify this handoff exists locally. Stop on any failed gate or authority conflict.

## Authorized file
Only `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` may be modified.

## Required implementation
Add a canonical detailed section that:
- defines independent detailed families for `rN_analysis`, `final_analysis`, and stateful `cumulative_learning` beneath the abstract Live Artifact interface;
- records required, optional-stable, source-contingent null/empty/absent, legacy-compatibility, and unresolved-member treatment from the decision matrices;
- establishes R1-R4 shared version-line policy and split condition;
- establishes final-analysis terminal-family treatment, current discriminator, and unresolved R4 parity boundary;
- establishes cumulative initialization, output-first/deploy-fallback read precedence, update/reprocessed-round behavior, terminal semantics, and versioned upgrade prerequisites;
- establishes independent compatibility/deprecation/translation rules without selecting new schema numbers;
- assigns detailed fields, types, nesting, missing behavior, compatibility, producer obligations, and consumer-validation rules to standards/04.

## Protected
Do not modify standards/03, data contracts, CODEX schema, README, library, engine, tests, deploy, config, events, databases, or existing handoffs/reports. Do not open or modify the Wyndham fixture. Do not create typed schemas, producer changes, adapters, migrations, README/library transitions, or deploy changes. Preserve `NO ADAPTER CURRENTLY JUSTIFIED`.

## Validation
Run `python tools/validate_scoring_doctrine.py`, `python -m pytest tests/test_doctrine_contract.py -q`, `git diff --check`, and show final `git status --short` plus `git diff --name-only`. Stop if output names/payload facts conflict with the decision report; report the conflict without remediation.

## Commit boundary
Executor may not commit, push, branch, or alter Git configuration. Return files changed, exact doctrine changes, validations, protected files unchanged, data-contract/migration/deploy impact, risks, and follow-on requirements.