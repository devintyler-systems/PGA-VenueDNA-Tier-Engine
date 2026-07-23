# FUTURE_EVENT_HANDOFF

Version: 2026-07-18
Purpose: reusable Claude Code control file for all PGA VenueDNA event-app UX builds.

## Role

You are working on a PGA VenueDNA event deploy package.
Your job is to improve the event app UX without changing the canonical model logic, data contract, or venue-specific scoring truth.

## Read order before touching code

1. Active event folder for the current tournament
2. Active venue intelligence file for the course
3. Current event deploy files: `deploy/index.html`, `deploy/styles.css`, `deploy/app.js`, `deploy/data/*`
4. `C:\PGA_VenueDNA\standards\ux\claude-code\EVENT_DEPLOY_CHECKLIST.md`
5. The phase prompt being executed

If any of the above are missing, stop and state the exact blocker.

## Non-negotiables

- Do not recompute or reinterpret the core VenueDNA model in browser code.
- Treat event payloads, scored outputs, and player briefs as source of truth.
- Do not hand-write rankings in JS.
- Do not let UX layers overwrite official model output.
- Keep official model mode distinct from any user scenario mode.
- Keep derivative UI separate from core ranking logic.
- Preserve mobile usability.
- Keep the deploy package static-site friendly.
- Do not use `localStorage` or `sessionStorage`.

## Canonical working directory

For each event, work from:
`C:\PGA_VenueDNA\events\<event_slug>\deploy\`

Never treat one prior event folder as the template authority.
Shared standards live here:
`C:\PGA_VenueDNA\standards\ux\claude-code\`

## Execution sequence

For a standard UX upgrade cycle, run in this order unless the user says otherwise:

1. Prompt 01 — Phase 1 UI foundation
2. Prompt 02 — Contention chart + sparklines
3. Prompt 03 — Scenario builder
4. Prompt 04 — Live round layer
5. Prompt 05 — Ask the Model parser

Default rule:
- 01, 02, and 03 are core build prompts
- 04 and 05 are deferred until core UI is stable or explicitly requested

## Deliverable rules

- Modify only the active event deploy package unless asked to create a shared standard.
- Keep runtime files in the event deploy folder.
- Keep reusable process docs in `standards/ux/claude-code/`.
- If a new reusable rule emerges, propose updating the shared standards rather than burying it in one event.

## Output format after each prompt

Return:
1. what changed
2. files changed
3. any required data fields or blockers
4. next recommended prompt in the sequence

## Refusal conditions

Stop and explain instead of proceeding when:
- no active venue file is available
- event data files are missing
- the requested change would rewrite model logic in the browser
- the requested UI conflicts with canonical event artifacts
