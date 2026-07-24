---
description: Playwright pre-deploy verification gate for a VenueDNA event board (checks rendering, not just JSON)
argument-hint: <event-folder e.g. 2026_3m_open>
allowed-tools: Bash(python -m http.server:*), Bash(taskkill:*), Bash(Get-Process:*), mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_click, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_evaluate, mcp__playwright__browser_close
---

# VenueDNA Board Verification Gate — `$1`

Verify the **rendered** board for `events/$1/deploy/` before it gets manually deployed to Netlify. This catches rendering bugs a JSON-only check cannot — e.g. the blank `Form` sparkline column that shipped to production on 2026-07-23 despite a correct payload.

Do not skip steps. Do not report PASS on anything you didn't actually observe via a Playwright tool call.

## 0. Setup

1. Confirm `events/$1/deploy/` exists. If not, stop and report the path is wrong.
2. Find the primary board HTML file in that directory — it is the `.html` file that is NOT `index.html` (index.html is a redirect only, per repo convention). Do not assume a filename pattern; list the directory and pick it explicitly.
3. Start a local static server scoped to that folder on port 5500:
   ```powershell
   python -m http.server 5500 --directory events/$1/deploy
   ```
   Run this in the background — do not block on it.

## 1. Load and locate the table

1. Navigate Playwright to `http://localhost:5500/<board-file-found-in-step-0>`.
2. Take an accessibility snapshot (`browser_snapshot`) to get real element refs — do not guess selectors.
3. Confirm the leaderboard table is present and has rows (fail if 0 rows).

## 2. Sparkline / Form column check

1. Use `browser_evaluate` to run in-page JS that finds every `canvas` element inside the Form column and checks whether it has non-blank pixel data (e.g. `getImageData` sum > 0, or compare against a freshly-cleared canvas's data).
2. FAIL if any row's Form canvas is entirely blank/transparent while other columns for that same row have real data (i.e. it's not a legitimate DEBUT/no-data row — cross-check against the player's `data_depth` if visible in the row or modal).

## 3. Modal check (radial dials + ceiling/floor bar)

1. Pick one player row where `data_depth != DEBUT` (favor a top-10 ranked player — more likely to have full data).
2. Click that row via Playwright (use the snapshot ref, not a coordinate guess) to open the player modal.
3. Snapshot again inside the modal. Confirm: strength/weakness trait badge pills are present with actual text (not empty pills); the 4 probability dial canvases have non-blank pixel data (`browser_evaluate` again); the ceiling/floor bar's fill width is between 0–100% (not NaN, not 0-width unless genuinely at floor).

## 4. Interactive state check (Analyst Mode toggle)

1. From the snapshot, locate the control that switches the "Scenario"/"Analyst Mode" view (do not assume its id — find it by visible text or role).
2. Click it via Playwright.
3. Snapshot again and confirm the view actually changed (different content visible, not just a class toggle with no visible effect).
4. Click it again to confirm it toggles back cleanly.

## 5. Screenshot record

1. `browser_take_screenshot` of the default board view.
2. `browser_take_screenshot` of the opened modal from step 3.
3. Save both under `events/$1/deploy/_verify/` with a timestamp in the filename.

## 6. Report

Print a pass/fail table:

| Check | Result | Evidence |
|---|---|---|
| Table renders with rows | | |
| Form sparklines non-blank | | |
| Modal trait badges populated | | |
| Modal probability dials non-blank | | |
| Ceiling/floor bar valid range | | |
| Analyst Mode toggle changes view | | |
| Analyst Mode toggle reverts cleanly | | |

**If any row is FAIL: do not deploy.** State exactly what's broken and which file (`app.js` line/function if identifiable from the evaluate output, or the specific data field that's empty upstream).

## 7. Cleanup

Stop the local `python -m http.server` process on port 5500 before finishing. Close the Playwright browser session.
