# EVENT_DEPLOY_CHECKLIST

Version: 2026-07-18
Purpose: preflight and execution checklist for any PGA VenueDNA event app build in Claude Code.

## Preflight

Before making any code change, confirm all of the following:

### Event context lock
- Event slug is known
- Active event folder exists
- Active venue intelligence file is identified
- Current task is clear: build, refine, live update, or audit support

### Deploy structure lock
Inside `C:\PGA_VenueDNA\events\<event_slug>\deploy\` confirm:
- `index.html`
- `styles.css`
- `app.js`
- `data\`
- `assets\`
- `README.md` preferred

### Data lock
Inside `deploy/data/` confirm the event has, at minimum:
- event payload JSON
- full scored field CSV
- player briefs JSON
- links JSON

Recommended canonical names follow the event slug pattern:
- `<event_slug>eventpayload.json`
- `<event_slug>vtsfull.csv`
- `<event_slug>playerbriefs.json`
- `<event_slug>links.json`

### Guardrail lock
Confirm these rules before coding:
- model logic stays upstream from front-end
- official ranks come from source artifacts only
- no local persistence APIs
- mobile support required
- scenario mode, if built, must be visually fenced from official mode
- live features cannot erase pre-event thesis visibility

## Prompt order

### Default build order
1. `claude-code-prompt-01-phase1-ui-foundation.md`
2. `claude-code-prompt-02-contention-chart-sparklines.md`
3. `claude-code-prompt-03-scenario-builder.md`

### Deferred until requested or stable
4. `claude-code-prompt-04-live-round-layer.md`
5. `claude-code-prompt-05-ask-the-model-parser.md`

## Validation after each prompt

### After Prompt 01
- Flag tooltips work on desktop and mobile
- Search works across player fields
- Filters do not mutate rankings
- Desktop table and mobile cards match same source data

### After Prompt 02
- Bubble chart reads from canonical player records
- Clicking chart points opens correct player detail
- Sparkline shows history if available, graceful empty state if not

### After Prompt 03
- Official mode is default on load
- Scenario mode is persistently labeled unofficial
- Reset returns exact default weights
- Scenario results never overwrite source files

### After Prompt 04
- Polling adapter is configurable
- Rank delta shows movement vs original model rank
- Watchlist uses in-memory state only
- Live layer is diagnostic, not a retroactive model rewrite

### After Prompt 05
- Query parser maps to known local fields only
- Unknown query fragments fail gracefully
- Returned results are filtered structured outputs, not hallucinated prose

## Escalate instead of coding when

- active venue file is missing
- event payload is incomplete
- player identity matching is unsafe
- requested feature requires changing scoring rules rather than UX
- chart or scenario view would obscure official rankings

## Completion standard

A prompt is not complete unless all are true:
- build runs from the event deploy folder
- canonical data remains source of truth
- event-specific work stays in the event folder
- reusable process improvements are identified for promotion to shared standards
- output includes changed files, blockers, and next prompt recommendation
