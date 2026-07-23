# 3M Open Deploy README

This folder is the active deploy package for the 2026 3M Open event app. It should contain only the event-local static app shell and the event-local data files that drive the board, because the artifact schema treats deploy files as weekly event artifacts rather than permanent shared standards.[cite:21]

## Read this first

Before making any edits in this folder, Claude Code should read the shared control files located at:

```text
C:\PGA_VenueDNA\standards\ux\claude-code\FUTURE_EVENT_HANDOFF.md
C:\PGA_VenueDNA\standards\ux\claude-code\EVENT_DEPLOY_CHECKLIST.md
C:\PGA_VenueDNA\standards\ux\claude-code\DEPLOY_README_TEMPLATE.md
```

Those files define the reusable process for all events, while this folder only defines the active 3M Open deploy package.[cite:21][cite:22]

## Working directory

Claude Code should work from this directory:

```text
C:\PGA_VenueDNA\events\2026_3m_open\deploy\
```

The active event files and the active venue intelligence file must control the build order and decisions for this event, because current event artifacts and the current venue file sit at the top of the operating authority order.[cite:22]

## Expected files here

This deploy folder should contain:

```text
deploy/
  README.md
  index.html
  styles.css
  app.js
  data/
  assets/
```

The artifact schema expects the deploy package to be a static event app with runtime files, JSON/CSV payloads, image assets, and a README for manual deploy guidance.[cite:21]

## Canonical data expectation

The front end should render from event-local generated artifacts in `data/`, especially the event payload JSON, full scored field CSV, player briefs JSON, and links JSON, because those are the canonical source artifacts for ranking, tiers, cards, and app rendering.[cite:21] Do not hardcode rankings or player narratives in browser code when they already exist in the source files.[cite:21]

Recommended filenames:

- `2026_3m_openeventpayload.json`
- `2026_3m_openvtsfull.csv`
- `2026_3m_openplayerbriefs.json`
- `2026_3m_openlinks.json`

These names should stay consistent with the event slug naming discipline required by the artifact schema.[cite:21]

## Edit rules

- `index.html`, `styles.css`, and `app.js` may be edited for UX implementation.[cite:21]
- Files inside `data/` are generated artifacts and should not be hand-edited unless the task is explicit data repair or regeneration.[cite:21]
- Shared standards must not be moved into this event folder, because reusable process files belong in the shared standards layer, not the weekly event package.[cite:21][cite:22]

## Prompt order

Default Claude Code run order for this event:

1. `claude-code-prompt-01-phase1-ui-foundation.md`
2. `claude-code-prompt-02-contention-chart-sparklines.md`
3. `claude-code-prompt-03-scenario-builder.md`
4. `claude-code-prompt-04-live-round-layer.md` only when live support is needed
5. `claude-code-prompt-05-ask-the-model-parser.md` only when parser support is needed

This preserves the intended rollout from core UI to higher-risk live and parser layers.[cite:22]

## Guardrails

- Do not move model logic into the front end.[cite:21][cite:22]
- Do not let scenario mode overwrite official model mode.[cite:22]
- Do not let derivative layers alter canonical core rankings.[cite:22]
- Do not use local persistence APIs for watchlist or alerts in this workflow.[cite:22]
- Keep the mobile experience usable, because the deploy package is meant to function as a live static event app.[cite:21]

## Launch instruction

Use this standard start instruction in Claude Code:

```text
Read:
1. C:\PGA_VenueDNA\standards\ux\claude-code\FUTURE_EVENT_HANDOFF.md
2. C:\PGA_VenueDNA\standards\ux\claude-code\EVENT_DEPLOY_CHECKLIST.md
3. C:\PGA_VenueDNA\standards\ux\claude-code\DEPLOY_README_TEMPLATE.md
4. The active event files in C:\PGA_VenueDNA\events\2026_3m_open\deploy\
5. The active venue intelligence file for the 3M Open

Then execute Prompt 01.
```

This keeps the build repeatable across events while preserving event-local and venue-local authority.[cite:22]
