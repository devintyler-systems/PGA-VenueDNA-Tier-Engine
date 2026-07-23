# Claude Code Prompt 02 — Contention chart + sparkline layer

You are working inside the PGA VenueDNA Open Championship event app.

Goal: add the two most valuable visual explanations without collapsing the model into a fuzzy composite.

## Scope

Implement:
1. Contention map
2. Player-card VTS sparkline history

## Rules
- Do not invent rankings from chart positions.
- The chart must read directly from the same player records used by the table/cards.
- Clicking a bubble must open the existing player modal/card detail.
- Sparkline history is explanatory only, not a model override.

## Contention map spec
- X axis = NeutralSkill index or NSI field
- Y axis = VenueFit score or VFS field
- Bubble size = win probability
- Color = tier
- Optional highlight toggles for flags and debut players
- Tooltip shows player, tier, win%, NSI, VFS, key risk

## Sparkline spec
- Add a compact 6–8 event sparkline to each player detail card
- Highlight current event point
- Tooltip on hover/tap shows event label and VTS value
- If history is missing, show a graceful no-history state

## Tech
- Prefer Chart.js or lightweight inline SVG
- Must remain mobile-safe
- Keep styling consistent with existing event app theme

## Output
Return:
1. implementation summary
2. files changed
3. assumptions made about data fields
4. any blockers caused by missing history fields
