# Lifecycle-State Reconciliation Decision

**Date:** 2026-08-13
**Mode:** Event-neutral, read-only governance decision
**Decision:** **1. Protocol-only correction**
**Confidence:** High

## 1. Executive decision and confidence

**Fact.** The current repository permits `NO_ACTIVE_EVENT`, `PRE_EVENT`, `ROUND_1` through `ROUND_4`, `FINAL_AUDIT`, and `ARCHIVED`; it does not permit `INITIALIZED` (`AGENTS.md:438-483`). The same status set is enforced by preflight (`tools/preflight_event.py:25-35, 100-126`), and the pre-event producer accepts only `PRE_EVENT` (`engine/event_context.py:159-197`).

**Fact.** The Weekly Event Setup Protocol instead directs the setup owner to set `status: INITIALIZED` (`PERPLEXITY_OPERATING_PROTOCOL.md:44-81`).

**Decision / recommendation.** Select **Protocol-only correction**. The minimum safe future change is a separately authorized, non-code edit to `PERPLEXITY_OPERATING_PROTOCOL.md` Step 5: replace the required `INITIALIZED` state with `PRE_EVENT` and state that the transition requires the complete active-event bindings and existing event structure required by preflight/context validation. Do not add `INITIALIZED` to governance, preflight, or the engine.

**Inference.** `INITIALIZED` is an **invalid current protocol instruction**, not a valid state, superseded alias, or merely undocumented transition. It conflicts with the higher-precedence local governance that controls this executor, and with two independent fail-closed enforcement surfaces.

The valid future transition is:

```text
NO_ACTIVE_EVENT  ->  PRE_EVENT
```

This decision does not authorize that transition for any specific event.

## 2. Gate results

All mandatory gates passed before this report was created.

| Command | Result |
| --- | --- |
| `git status --short` | Empty worktree. |
| `git branch --show-current` | `main`. |
| `git fetch origin` | Completed successfully. |
| `git rev-parse HEAD` | `485909d7a55f92cd2f55711824ea351aa22da2a9`. |
| `git rev-parse origin/main` | `485909d7a55f92cd2f55711824ea351aa22da2a9`. |
| `git status -sb` | `## main...origin/main`. |
| `Get-Content config/active_event.json` | `status: NO_ACTIVE_EVENT`; event/venue and deploy bindings are null (`config/active_event.json:1-19, 32-34`). |

**Fact.** The binding handoff required a clean, synchronized `main` and `NO_ACTIVE_EVENT` before proceeding (`scripts/handoffs/2026-08-13_lifecycle_state_reconciliation_decision.md:18-32`). All conditions held.

## 3. Authority hierarchy and exact conflict map

### Governing order

**Fact.** The controlling task directs a read-only governance decision and permits exactly one report write (`scripts/handoffs/2026-08-13_lifecycle_state_reconciliation_decision.md:3-14, 34-65`). Under it, `AGENTS.md` orders authority as task, `AGENTS.md`, active-event instructions, `SYSTEM_HANDOFF_SPEC.md`, canonical standards, implementation/tests/deploy contracts, then historical artifacts (`AGENTS.md:12-25`). It also requires stopping, naming the conflict, identifying the governing authority, and proposing the smallest safe resolution (`AGENTS.md:45-51`).

**Fact.** `CLAUDE.md` independently states the same order for its lane and directs explicit conflict handling (`CLAUDE.md:12-34`). `SYSTEM_HANDOFF_SPEC.md` requires both planning lanes to follow the repository authority hierarchy and active-event lifecycle, and confines the Perplexity protocol to Perplexity's direct artifact/commit behavior (`SYSTEM_HANDOFF_SPEC.md:20-29`). It also requires a committed, synchronized handoff before local execution (`SYSTEM_HANDOFF_SPEC.md:76-98`).

### Exact conflict map

| Authority / enforcement surface | Exact rule | Effect |
| --- | --- | --- |
| `PERPLEXITY_OPERATING_PROTOCOL.md:48-51, 79-81` | With `NO_ACTIVE_EVENT`, proceed with setup; then set `config/active_event.json` to `status: INITIALIZED`. | Introduces a required transient state. |
| `AGENTS.md:442-463` | Enumerates allowed statuses, omits `INITIALIZED`, and defines `NO_ACTIVE_EVENT` and `PRE_EVENT` behavior. | Governing lifecycle has no `INITIALIZED` transition. |
| `CLAUDE.md:424-445` | Mirrors the allowed-state list and pre-event behavior. | Corroborates the same governance doctrine. |
| `tools/preflight_event.py:25-35, 100-140` | `VALID_STATUSES` omits `INITIALIZED`; event-bound states require complete non-null bindings and directories/profile checks. | Rejects `INITIALIZED`; accepts a fully bound `PRE_EVENT`. |
| `engine/event_context.py:159-197` | The pre-event context rejects `NO_ACTIVE_EVENT` and every state other than `PRE_EVENT` before event-bound I/O. | A pre-event producer cannot consume `INITIALIZED`. |

**Inference.** The conflict is one-way: the protocol's state token is the sole divergent instruction. No evidence supports changing the already-aligned governance, preflight, or producer behavior to preserve that token.

## 4. Lifecycle-state findings

**Fact.** `NO_ACTIVE_EVENT` is the present, intentionally unbound state; its manifest notes prohibit event-bound projection or live artifacts until an update (`config/active_event.json:3-18, 34`). Repository governance allows only reusable work or an explicitly authorized initialization task while in this state (`AGENTS.md:453-457`).

**Fact.** `PRE_EVENT` is the first state that authorizes pre-event artifacts while prohibiting live artifacts (`AGENTS.md:459-463`). Preflight applies its complete event-binding checks to it and requires it for `--phase pre_event` (`tools/preflight_event.py:126-184`). The engine's `load_pre_event_context()` requires it before event-bound I/O (`engine/event_context.py:159-197`).

**Fact.** The canonical architecture separates event input, output, deploy, and audit; output becomes deploy data through the protected deployment path (`standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md:32-69, 114-127`). The artifact schema's event-neutral source-manifest integration also performs context and capability checks before source reads, output/deploy-directory creation, or writes (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:617-637, 775-789`). Neither establishes an `INITIALIZED` lifecycle state.

**Recommendation.** A future authorized event setup should make one transition from the fully null `NO_ACTIVE_EVENT` manifest to a fully bound `PRE_EVENT` manifest only after its authorized setup work is ready to satisfy the existing required fields and directory/profile validation. It must not insert an `INITIALIZED` manifest state.

## 5. Selected resolution and rejected alternatives

### Selected: 1. Protocol-only correction

**Why this is the smallest safe scope.** The protocol is the only divergent authority. A narrow Step 5 correction restores consistency with the higher-precedence lifecycle and existing enforcement without changing an accepted manifest schema, code, test, deploy path, scoring layer, or artifact interface.

### Rejected alternatives

1. **Governance-only correction — rejected.** Adding `INITIALIZED` to `AGENTS.md`/`CLAUDE.md` would lower the established `PRE_EVENT` entry condition and still leave preflight and `EventContext` rejecting it. It would require broader code and test changes without evidence of a needed state semantic.
2. **Preflight-only correction — rejected.** Accepting `INITIALIZED` in preflight alone would create disagreement with governing lifecycle and the producer's strict `PRE_EVENT` requirement; it would not make a build viable.
3. **Coordinated protocol/governance/preflight alignment — rejected.** Alignment already exists across governance, preflight, and engine. Coordinated edits would be unnecessary scope expansion and heighten regression risk.
4. **Hold pending missing authority or evidence — rejected.** The binding handoff, active manifest, governance, preflight, and engine provide sufficient direct evidence.

## 6. Risk and backward-compatibility analysis

| Area | Fact / inference | Compatibility effect |
| --- | --- | --- |
| Active manifest | `NO_ACTIVE_EVENT` is valid only when active bindings are absent; event-bound preflight states require complete bindings (`tools/preflight_event.py:108-140`). | Protocol correction preserves the current manifest schema and avoids a new persisted enum value. |
| Event context / producer | Pre-event context accepts only `PRE_EVENT` and fails before event-bound I/O otherwise (`engine/event_context.py:159-197`). | No engine change or migration; future setups can use the supported entry state. |
| Artifacts and scoring | Pre-event and live boundaries remain immutable/separate (`AGENTS.md:459-483`; `SYSTEM_HANDOFF_SPEC.md:113-124`). | No scoring, artifact, database, or write-back behavior changes. |
| Deploy | Output/deploy separation and protected payload paths remain unchanged (`standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md:63-69, 114-127`; `docs/data_contracts.md:519-547`). | No board, fetch target, payload, or deploy migration. |
| Historical records | Canonical authority places historical artifacts below present implementation, and the task prohibits using archive material as current authority (`AGENTS.md:12-25`; `scripts/handoffs/2026-08-13_lifecycle_state_reconciliation_decision.md:43-44`). | No historical manifest or archive is changed or reinterpreted. |

**Highest-risk unresolved issue.** A future setup owner could follow the uncorrected protocol literally, create files/commits around `INITIALIZED`, and then be blocked by preflight and the producer. The correction must be committed before any event-specific setup is authorized.

## 7. Future-only validation and test strategy

**Ownership.** The future protocol-only documentation edit belongs to the Perplexity planning/commit lane described by `AGENTS.md:23-25` and `SYSTEM_HANDOFF_SPEC.md:20-29`; an operator must separately authorize it. No Codex implementation change is authorized by this report.

**Validation after that authorization, not performed here:**

1. Review the committed protocol diff to confirm Step 5 names exactly `PRE_EVENT`, never `INITIALIZED`, and keeps the full-binding precondition explicit.
2. Confirm no change to `AGENTS.md`, `CLAUDE.md`, `tools/preflight_event.py`, `engine/event_context.py`, standards, tests, configuration, deploy, artifacts, or data.
3. On the then-current neutral manifest, run the read-only generic preflight; it should continue to recognize `NO_ACTIVE_EVENT`. Do not fabricate a manifest or fixture to test the transition.
4. Only in a later, separately authorized event-setup task, validate the real fully bound manifest with `python tools/preflight_event.py --phase pre_event --strict` before any producer run, as the data-contract validation surface requires (`docs/data_contracts.md:872-900`).
5. No test edit is justified for this protocol-only correction. If any future implementation proposes changing the accepted enum or context semantics, that implementation must first add targeted status-enumeration and fail-closed regression coverage, then run the narrowest affected test suite. That is outside the corrective scope selected here.

## 8. Explicit non-actions

**Fact.** This executor created only this report. It did not modify governance, protocol, standards, configuration, code, tools, tests, docs, README, library, deploy files, event files, artifacts, data, or databases.

No event was initialized; no event/venue was selected; no source manifest or data was acquired; no projection, live/final/audit artifact, or deploy output was created. No archived board or `events/2026_wyndham_championship/` was inspected, used as current authority, or changed. No commit, push, stage, pull/merge/rebase branch synchronization, cleanup, or lifecycle-state update occurred; the required `git fetch origin` updated remote-tracking metadata only.

## 9. Exact next authorization required

**Required separate authorization:**

> Authorize Perplexity to make and commit one protocol-only governance correction in `PERPLEXITY_OPERATING_PROTOCOL.md`: change Weekly Event Setup Step 5 from `status: INITIALIZED` to `status: PRE_EVENT`, explicitly requiring complete active-event bindings and existing preflight-required structure at that transition. Do not modify `AGENTS.md`, `CLAUDE.md`, `SYSTEM_HANDOFF_SPEC.md`, standards, configuration, preflight, engine, tests, docs, deploy files, artifacts, data, databases, or events.

After that committed correction, a different explicit operator authorization and event-specific handoff are required before selecting an event/venue, creating any folder or source manifest, changing `config/active_event.json`, or running event-bound validation/build work.
