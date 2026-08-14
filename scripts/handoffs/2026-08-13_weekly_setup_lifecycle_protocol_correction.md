# Weekly Event Setup Lifecycle Protocol Correction

**Date:** 2026-08-13
**Task type:** Narrow governance correction
**Required branch:** `main`
**Required active-event state:** `NO_ACTIVE_EVENT`

## Objective

Implement the committed lifecycle-state reconciliation decision:

```text
NO_ACTIVE_EVENT -> PRE_EVENT
```

The prior lifecycle decision established that `INITIALIZED` is an invalid current protocol instruction. This task authorizes a protocol-only correction; it does not authorize event initialization or any event-bound work.

## Authority

The governing decision is:

```text
scripts/handoffs/reports/2026-08-13_lifecycle_state_reconciliation_decision_REPORT.md
```

It determined:

- `AGENTS.md` and `CLAUDE.md` do not permit `INITIALIZED`.
- `tools/preflight_event.py` rejects `INITIALIZED`.
- `engine/event_context.py` accepts `PRE_EVENT` for pre-event work.
- The smallest safe correction is limited to `PERPLEXITY_OPERATING_PROTOCOL.md`.

## Mandatory gates

Run and report:

```powershell
git status --short
git branch --show-current
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status -sb
Get-Content config/active_event.json
```

Proceed only if:

- Branch is `main`.
- Worktree is clean before work begins.
- Local `HEAD` equals `origin/main`.
- Active-event status is `NO_ACTIVE_EVENT`.

If a gate fails, stop. Do not synchronize branches, clean unrelated files, alter lifecycle state, or perform event setup.

## Required inspection

Read:

- `AGENTS.md`
- `CLAUDE.md`
- `PERPLEXITY_OPERATING_PROTOCOL.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `tools/preflight_event.py`
- `engine/event_context.py`
- `scripts/handoffs/reports/2026-08-13_pre_event_operational_readiness_audit_REPORT.md`
- `scripts/handoffs/reports/2026-08-13_lifecycle_state_reconciliation_decision_REPORT.md`

## Sole authorized implementation file

```text
PERPLEXITY_OPERATING_PROTOCOL.md
```

Modify only Weekly Event Setup Step 5.

## Required protocol correction

Replace the instruction that persists:

```text
status: INITIALIZED
```

with the canonical supported transition:

```text
NO_ACTIVE_EVENT -> PRE_EVENT
```

The corrected Step 5 must state all of the following:

1. The active manifest may transition to `PRE_EVENT` only when the future event setup has been explicitly authorized.
2. The active manifest must be fully bound before the transition: event identity, venue identity, year, required event root/profile/context/source references, deploy root, audit root, and other required preflight/context bindings.
3. Required event structure must already exist and satisfy applicable path/profile validation before the state transition.
4. The correction does not itself authorize event selection, venue selection, folder creation, source-manifest creation, source acquisition, source ingestion, projection generation, artifact creation, deploy output, or a producer run.
5. A separate event-specific setup handoff and explicit operator authorization remain mandatory.
6. Do not introduce `INITIALIZED` as an alias, compatibility state, or temporary persisted manifest value.

## Explicitly protected files

Do not modify:

- `AGENTS.md`
- `CLAUDE.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/**`
- `tools/preflight_event.py`
- `engine/**`
- `standards/**`
- `tests/**`
- `docs/**`
- `README.md`
- `library/**`
- `deploy/**`
- Data, databases, manifests, artifacts, event files, or archives
- `events/2026_wyndham_championship/`

## Prohibitions

Do not:

- Initialize an event or update `config/active_event.json`.
- Select an event or venue.
- Create an event directory, source manifest, fixture, source file, or payload.
- Run an event-bound build, producer, deploy path, live path, audit path, download, or writing test.
- Create projections, live/final artifacts, audit outputs, deploy data, caches, backups, or database changes.
- Commit or push from Codex/Claude.

## Sole executor output

Create only this uncommitted report:

```text
scripts/handoffs/reports/2026-08-13_weekly_setup_lifecycle_protocol_correction_REPORT.md
```

The report must include:

1. Gate results.
2. Exact protocol text changed.
3. Confirmation that `INITIALIZED` is no longer instructed as a persisted manifest state.
4. Confirmation that the protocol directs `NO_ACTIVE_EVENT -> PRE_EVENT`.
5. Confirmation that complete bindings and separate event authorization remain explicit.
6. Exact changed-file list.
7. Confirmation that no protected file, event state, artifact, deploy output, commit, or push occurred.

## Completion validation

Run:

```powershell
git diff --check
git diff -- PERPLEXITY_OPERATING_PROTOCOL.md
git diff --name-only
git status --short
```

The permitted changed files are only:

```text
PERPLEXITY_OPERATING_PROTOCOL.md
scripts/handoffs/reports/2026-08-13_weekly_setup_lifecycle_protocol_correction_REPORT.md
```

Leave both changes uncommitted for Perplexity review.
