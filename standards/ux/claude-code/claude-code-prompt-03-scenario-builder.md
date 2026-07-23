# Claude Code Prompt 03 — Scenario builder with model lock

You are extending the PGA VenueDNA event app with a user-controlled scenario builder.

Goal: let users test trait-weight what-ifs without confusing those results with the official VenueDNA model.

## Critical guardrail
The official model and the user scenario mode must be visually and functionally separated at all times.

## Scope
- Add a scenario panel with trait-weight sliders
- Add `Official Model` and `Scenario Mode` states
- Add reset-to-default button
- Re-rank only the client-side scenario view
- Never overwrite source payload data

## Requirements
- Display default weight and user-adjusted weight side by side
- Persistently label scenario results as unofficial
- Lock penalty rules by default; do not expose all engine internals as sliders
- Show delta vs official rank for each player in scenario mode
- Allow one-click exit back to official model

## UX rules
- The official model is default on load
- Scenario mode should feel exploratory, not authoritative
- If key fields for a player are missing, surface uncertainty instead of forcing rank movement

## Output
Return:
1. implementation summary
2. files changed
3. data assumptions
4. safeguards added to prevent confusion with official output
