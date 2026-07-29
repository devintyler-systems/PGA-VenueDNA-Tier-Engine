# /verify-narrative-harness

Playwright verification gate for the Rocket Classic **fixture harness only**.
Scoped exclusively to `events/2026_rocket_classic/deploy/fixture_harness.html`.

This command is a development gate, not a production deployment gate.
It verifies fixture drawer behavior, evidence states, responsive layout, and
filter-state persistence. It does NOT verify the full Rocket Classic board —
that gate will be `/verify-board` once the real scoring artifact is wired.

Do not skip steps. Do not report PASS on anything you didn't actually observe
via a Playwright tool call.

---

## Setup

Start a local server at the repo root (port 5500) before running:

```
http://localhost:5500/events/2026_rocket_classic/deploy/fixture_harness.html
```

---

## Check 8 — Drawer opens; board remains visible

**Goal:** Clicking a fixture row opens the drawer without hiding the roster table.

1. Navigate to `http://localhost:5500/events/2026_rocket_classic/deploy/fixture_harness.html`
2. Wait for the page to load and fixture rows to render (wait for `#roster-tbody tr` to exist)
3. Take a screenshot — confirm 3 roster rows are visible
4. Click the first roster row (`#roster-tbody tr:first-child`)
5. Wait for `#player-drawer.open` to appear in the DOM
6. Evaluate: `document.getElementById('roster-panel') !== null` → must be `true`
7. Evaluate: `getComputedStyle(document.getElementById('roster-panel')).display` → must NOT be `'none'`
8. Evaluate: `parseFloat(getComputedStyle(document.getElementById('roster-panel')).opacity) > 0` → must be `true`
9. Take a screenshot confirming drawer is open alongside the visible roster

**PASS criteria:** Drawer has class `open`, roster panel is in DOM, display ≠ 'none', opacity > 0.

---

## Check 9 — Elite evidence state (full narrative renders, no warning labels)

**Goal:** fixture_elite_001 shows full narrative with no "Limited evidence" label and no "Narrative unavailable" text.

1. If drawer is open, close it (press Escape or click backdrop)
2. Find the row with `data-player-id="fixture_elite_001"` and click it
3. Wait for `#drawer-inner` to update
4. Evaluate: `document.querySelector('#drawer-inner .evidence-banner')` → must be `null` (no banner)
5. Evaluate: `document.querySelector('#drawer-inner .narrative-unavailable')` → must be `null`
6. Evaluate: `document.querySelector('#drawer-inner .drawer-headline')?.textContent?.trim()` → must be non-empty string
7. Evaluate: `document.querySelector('#drawer-inner .drawer-prose')?.textContent?.trim()` → must be non-empty string
8. Take a screenshot of the open drawer

**PASS criteria:** No evidence banner, no unavailable message, headline and story_hook prose both render.

---

## Check 10 — Volatile evidence state ("Limited evidence" label visible)

**Goal:** fixture_volatile_001 shows "Limited evidence" banner and at least one weakness card.

1. Close the current drawer
2. Find the row with `data-player-id="fixture_volatile_001"` and click it
3. Wait for `#drawer-inner` to update
4. Evaluate: `document.querySelector('#drawer-inner .evidence-banner')` → must NOT be `null`
5. Evaluate: `document.querySelector('#drawer-inner .evidence-banner')?.textContent` → must contain "Limited evidence"
6. Evaluate: `document.querySelectorAll('#drawer-inner .weakness-card').length` → must be ≥ 1
7. Take a screenshot

**PASS criteria:** `.evidence-banner` present, text contains "Limited evidence", at least one weakness card rendered.

---

## Check 11 — Thin evidence state ("Limited evidence" OR "Narrative unavailable" renders correctly)

**Goal:** fixture_thin_001 shows either the limited-evidence label (if validation passed) or the structural-failure state (if validation_errors is non-empty). Prose fields must NOT render if validation_errors is non-empty.

1. Close the current drawer
2. Find the row with `data-player-id="fixture_thin_001"` and click it
3. Wait for `#drawer-inner` to update
4. Evaluate:
   ```js
   const banner = document.querySelector('#drawer-inner .evidence-banner');
   const unavailable = document.querySelector('#drawer-inner .narrative-unavailable');
   banner !== null || unavailable !== null
   ```
   → must be `true`
5. If `.narrative-unavailable` is present:
   - Evaluate: `document.querySelector('#drawer-inner .drawer-headline')?.textContent?.trim() || ''` → must be `''` (prose suppressed)
   - Evaluate: `.narrative-unavailable strong` text must contain "structural validation failed"
6. If only `.evidence-banner` is present (validation passed, thin evidence):
   - Evaluate: `.evidence-banner` text contains "Limited evidence" or "low confidence"
7. Take a screenshot

**PASS criteria:** Either the evidence-banner or the narrative-unavailable block is present. If unavailable block: no prose fields render. If evidence-banner: "Limited evidence" wording appears.

---

## Check 12 — Filter state persists across drawer player switches

**Goal:** `activeFilters` state is not reset when the drawer switches between players.

1. Ensure all drawers are closed
2. Click a badge filter checkbox (any checkbox in `#badge-filter-list`)
3. Evaluate: `window.__harness.getActiveFilters().badges.length > 0` → must be `true`
4. Note the current `activeFilters.badges` array value
5. Click the `fixture_elite_001` row to open drawer
6. Evaluate: `window.__harness.getActiveFilters().badges` → must equal the same value as step 4
7. Click the `fixture_volatile_001` row (switches player without closing drawer)
8. Evaluate: `window.__harness.getActiveFilters().badges` → must still equal the value from step 4
9. Evaluate: `window.__harness.getOpenPlayerId()` → must be `'fixture_volatile_001'`

**PASS criteria:** `activeFilters.badges` unchanged after opening and switching drawer players.

---

## Check 13 — Desktop layout (≥1280px): permanent three-zone

**Goal:** At 1400×900, filter zone, roster, and drawer are simultaneously visible with no overlap. Drawer is alongside the roster (not a sheet).

1. Resize browser to 1400×900
2. Open drawer for any fixture player
3. Take a screenshot
4. Evaluate:
   ```js
   const sidebar = document.getElementById('filter-sidebar');
   const roster  = document.getElementById('roster-panel');
   const drawer  = document.getElementById('player-drawer');
   const sRect = sidebar.getBoundingClientRect();
   const rRect = roster.getBoundingClientRect();
   const dRect = drawer.getBoundingClientRect();
   // All three must be visible (width > 0, height > 0)
   sRect.width > 0 && rRect.width > 0 && dRect.width > 0
   ```
   → must be `true`
5. Evaluate: `getComputedStyle(document.getElementById('player-drawer')).position` → must NOT be `'fixed'` (it's in flow, not a sheet)
6. Evaluate: no overlap — `dRect.left >= rRect.right - 1` (drawer starts at or after roster ends)

**PASS criteria:** All three zones have width > 0, drawer is not position:fixed, drawer left edge ≥ roster right edge.

---

## Check 14 — Narrow layout (<900px): drawer as bottom sheet; roster independently scrollable

**Goal:** At 375×812, drawer renders as a fixed bottom sheet. Roster table is independently scrollable beneath it.

1. Resize browser to 375×812
2. Click any fixture row to open the drawer
3. Wait for `#player-drawer.open`
4. Take a screenshot
5. Evaluate:
   ```js
   const drawer = document.getElementById('player-drawer');
   const s = getComputedStyle(drawer);
   s.position === 'fixed' && s.bottom === '0px'
   ```
   → must be `true`
6. Evaluate: `document.getElementById('player-drawer').getBoundingClientRect().width` → must equal `window.innerWidth` (or close to it, within 2px)
7. Evaluate:
   ```js
   const roster = document.getElementById('roster-panel');
   getComputedStyle(roster).overflowY
   ```
   → must be `'auto'` or `'scroll'` (independently scrollable)
8. Take a screenshot confirming bottom-sheet presentation

**PASS criteria:** Drawer is `position:fixed`, `bottom:0`, full viewport width. Roster overflow-y is auto or scroll.

---

## Reporting

After all 7 checks (8–14):

- **ALL PASS:** Report the harness as verified. Phase 5 (narrative builder) and full-board planning may proceed.
- **ANY FAIL:** Report which check failed, what was observed vs. expected, and do not proceed to Phase 5.

Take and save screenshots to `events/2026_rocket_classic/deploy/_verify/` with timestamps.
