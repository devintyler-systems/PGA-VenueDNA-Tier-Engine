# Playwright MCP Verification Gate — Addendum to 3M Open UX Overhaul

**Status:** Proposed addendum. Does not modify [`2026-07-23-3m-open-ux-overhaul.md`](../plans/2026-07-23-3m-open-ux-overhaul.md) or its design spec — adds a verification step after their existing tasks complete.

## Why

The UX overhaul plan's own Verification section runs `python engine/enrich_cards.py` and a `node -e` field-count check — both confirm the **JSON payload** is correct. Neither confirms the **rendered board** is correct. That gap is exactly how the live board shipped with a blank `Form` column, blank `Flags`, and `Pen` showing `—` for every row on the previous (Open Championship) deploy — defects invisible to a JSON-only check, visible in two seconds to anyone looking at the page.

As of 2026-07-23, commit `9009e2d` landed Phase 1 & 2 (sparkline canvases, radial probability dials, ceiling/floor bar, trait badges) — but the live board at `2026-3m-open.netlify.app` still shows the **old** blank `Form` column, because there is no CI/CD: no `netlify.toml`, no GitHub Actions workflow in this repo. Deploy is a manual step. Nothing currently catches a rendering bug between `git push` and that manual deploy.

## What this adds

A Playwright MCP–driven check, run from Claude Code, after the plan's existing Verification section and before the manual Netlify deploy:

1. Serve `events/2026_3m_open/deploy/` locally (`npx serve` or equivalent) or open the file directly via `file://`.
2. Playwright MCP navigates to `3m_open_2026_board.html`.
3. Wait for `tbody` to populate, then assert:
   - Every `<canvas id="sp-*">` (Form column sparklines) has non-empty rendered pixel data — not just present in the DOM.
   - No table cell in `Form`, `strengthTags`/`weaknessTags` badge rows renders empty/`—` for rows where the underlying payload has real data.
4. Open the player modal for at least one player with `data_depth != DEBUT` and assert the 4 radial probability dials and the ceiling/floor bar render (canvas non-empty).
5. Click the Analyst Mode toggle (renamed from Scenario per this plan) and assert the view actually switches state — this is interactive, not just static render, so it needs Playwright's click+assert loop, not a screenshot alone.
6. Capture a screenshot of both the default board view and the modal for visual record — attach to the commit/PR description.

If any assertion fails, do not deploy — fix and re-run. This is a gate, not a report.

## Install (one-time, project-scoped so it's checked into git)

```powershell
cd C:\PGA_VenueDNA
claude mcp add --scope project playwright -- npx -y @playwright/mcp@latest
npx playwright install chromium
```

`--scope project` writes to `.mcp.json` at the repo root — commit it so the gate is available in every future session without reinstalling. If Windows throws a connection error on the bare `npx` form, use the `cmd /c` wrapper instead:

```powershell
claude mcp add --scope project playwright -- cmd /c npx -y @playwright/mcp@latest
```

Verify inside a Claude Code session: `/mcp` should list `playwright` as connected with ~20+ tools (`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_take_screenshot`, etc.).

## Where this lives going forward

Add this same 6-step gate to every future per-event UX change, not just this one — it's the missing step in the `events/<event>/deploy/` pattern generally, not a 3M-Open-specific fix.
