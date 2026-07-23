# Deploy README

This folder is the static deploy package for a single PGA VenueDNA event app. The artifact schema defines the deploy package as the event-specific static site layer containing `index.html`, `styles.css`, `app.js`, `data/`, `assets/`, and a README that explains which files are generated and which should not be hand-edited.[cite:21]

## Purpose

Use this folder to render the current event board from canonical event artifacts, not to store shared engine standards or permanent venue/system rules.[cite:21][cite:22] Event-specific app behavior should stay downstream from the active event files and active venue file, because the compact instructions require current event artifacts and venue intelligence to govern projection outputs.[cite:22]

## Folder contract

Expected structure:

```text
deploy/
  index.html
  styles.css
  app.js
  data/
    <event_slug>eventpayload.json
    <event_slug>vtsfull.csv
    <event_slug>playerbriefs.json
    <event_slug>links.json
  assets/
  README.md
```

This mirrors the deploy package contract in the artifact schema, which treats the front end as a static shell driven by data files rather than embedded model logic.[cite:21]

## What belongs here

- Runtime app files: `index.html`, `styles.css`, `app.js`.[cite:21]
- Event-local data files for the current tournament in `data/`.[cite:21]
- Event-local presentation assets in `assets/`.[cite:21]
- This README for handoff and operating rules.[cite:21]

## What does not belong here

Do **not** store reusable Claude process docs, engine specs, venue intelligence, or scoring standards inside this folder long-term, because those are persistent shared artifacts, not weekly deploy files.[cite:21] Shared UX control files should live in `C:\PGA_VenueDNA\standards\ux\claude-code\` so future events can use the same process without inheriting one prior event folder as the template authority.[cite:21][cite:22]

## Canonical data sources

The front end should read from canonical event artifacts in `data/`, especially the full scored field CSV and event payload JSON, because the schema identifies those as the source of truth for ranks, tiers, gates, probabilities, and event app rendering.[cite:21] Do not hardcode rankings, tiers, or player summaries in JavaScript when the same fields already exist in the generated data files.[cite:21]

Recommended event-local filenames:

- `<event_slug>eventpayload.json`.[cite:21]
- `<event_slug>vtsfull.csv`.[cite:21]
- `<event_slug>playerbriefs.json`.[cite:21]
- `<event_slug>links.json`.[cite:21]

## Shared standards location

Before changing this deploy package in Claude Code, read the shared control files here:

```text
C:\PGA_VenueDNA\standards\ux\claude-code\FUTURE_EVENT_HANDOFF.md
C:\PGA_VenueDNA\standards\ux\claude-code\EVENT_DEPLOY_CHECKLIST.md
```

Those shared files define the reusable UX build process for future events, while this folder remains event-local.[cite:22]

## Claude Code run order

Default prompt sequence:

1. `claude-code-prompt-01-phase1-ui-foundation.md`
2. `claude-code-prompt-02-contention-chart-sparklines.md`
3. `claude-code-prompt-03-scenario-builder.md`
4. `claude-code-prompt-04-live-round-layer.md` when live support is needed
5. `claude-code-prompt-05-ask-the-model-parser.md` when parser support is needed

This order matches the controlled UX rollout created for the Open build and keeps higher-risk live features behind the core UI foundation work.[cite:22]

## Edit rules

- `index.html`, `styles.css`, and `app.js` may be edited for UX work.[cite:21]
- Files inside `data/` are generated artifacts and should not be hand-edited unless the task is a deliberate data repair or regeneration step.[cite:21]
- Shared process files in `standards/ux/claude-code/` should be updated only when improving the reusable workflow for all events.[cite:21][cite:22]

## Guardrails

- Do not move core scoring logic into browser code.[cite:21][cite:22]
- Do not let scenario mode overwrite official model output.[cite:22]
- Do not use DFS, odds, or popularity to alter canonical core ranks in the app layer.[cite:22]
- Do not use `localStorage` or `sessionStorage` in the Space-style static deploy workflow; prefer in-memory state for watchlist or alert behavior.[cite:22]
- Keep mobile usability mandatory for every event build.[cite:22]

## New event process

For a future event:

1. Create a new event folder under `C:\PGA_VenueDNA\events\<event_slug>\`.[cite:21]
2. Place event-specific runtime files in that event’s `deploy/` folder.[cite:21]
3. Load the active venue file and current event data files before any UX work begins.[cite:22]
4. Run Claude Code from the event’s `deploy/` root, but always point it first to the shared standards folder.[cite:22]

## Quick start

Example launch flow:

```text
Working directory:
C:\PGA_VenueDNA\events\<event_slug>\deploy\

First read:
C:\PGA_VenueDNA\standards\ux\claude-code\FUTURE_EVENT_HANDOFF.md
C:\PGA_VenueDNA\standards\ux\claude-code\EVENT_DEPLOY_CHECKLIST.md

Then:
- inspect deploy/index.html
- inspect deploy/styles.css
- inspect deploy/app.js
- inspect deploy/data/*
- inspect the active venue intelligence file
- execute Prompt 01
```

This keeps the build portable across tournaments while preserving the event-specific and venue-specific authority order required by the VenueDNA system.[cite:22]
