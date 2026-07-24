# 3M Open 2026 — UX Blueprint Overhaul v2
**Session base commit:** 9009e2d
**Date:** 2026-07-23
**Branch:** main
**Deploy target:** events/2026_3m_open/deploy/ (app.js, 2026_3m_open_board.html, styles.css)

## Global Constraints
- Never rename deploy/data/ JSON files without updating all fetch() calls in app.js
- All scores stay normalized 0-100; do NOT change payload schema
- State object `S` in app.js is the single source of truth — all filter/view changes go through S
- CSS variables must remain in both :root (dark) and [data-theme="light"] blocks
- Do NOT break existing functionality: search, favorites, preset filters, glossary, contention chart toggles, scenario sliders

## Task Order
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

## Task 1: Right-side slide-out player drawer
**Fix #4 & #11 from spec**

Replace `.modal-overlay` + `.modal` center-screen pattern with a fixed right-side drawer:

```css
.player-drawer {
  position: fixed;
  top: 0; right: -100%;
  width: min(480px, 100vw);
  height: 100vh;
  overflow-y: auto;
  z-index: 9999;
  background: var(--surface);
  border-left: 1px solid var(--border);
  box-shadow: -4px 0 32px rgba(0,0,0,.6);
  transition: right 0.3s ease;
}
.player-drawer.open { right: 0; }
.drawer-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.6);
  z-index: 9998;
  display: none;
}
.drawer-backdrop.open { display: block; }
body.drawer-open { overflow: hidden; }
```

- Update `openModal(name)` → animate `.player-drawer` to `right:0`, add `.open` class, set `body.drawer-open`
- Update `closeModal()` → remove `.open`, wait 300ms, reset body scroll
- Close on: Escape, backdrop click, close button
- Drawer content (header + scrollable body) stays identical to current modal content
- The old `.modal-overlay` and `.modal` CSS classes can remain for the glossary modal (which is still a center modal)

## Task 2: Layout spacing fixes
**Fix #2 & #3 from spec**

1. **What Wins Here grid** — already uses `display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr))` but cards don't stretch to equal height. Add `align-items: stretch` and ensure inner flex columns use `flex:1` to fill.

2. **Spotlight section** — `.spotlight-container` grid is fine; `.spotlight-card` content needs `display:flex; flex-direction:column;` so the tier reason text at the bottom is pushed down consistently. Add `flex:1` to `.sc-reason`.

3. **Weather panel cards** — same stretch treatment so 4 data points fill the card evenly.

## Task 3: Theme toggle fix
**Fix #1 from spec**

Current state: `toggleTheme()` in app.js sets `data-theme` on `document.body`. The CSS selector is `[data-theme="light"]` — check if this is on `<html>` or `<body>`. Audit and fix:

- `styles.css`: `[data-theme="light"]` block must exist with ALL variable overrides
- `2026_3m_open_board.html` inline `<style>`: same
- `toggleTheme()` in app.js: explicitly target `document.documentElement` (the `<html>` element) to set `document.documentElement.setAttribute('data-theme', 'light')` / `removeAttribute`
- The icon should toggle ☀ ↔ ☽ and the label should toggle Light ↔ Dark

## Task 4: Fixed top navigation bar
**Fix #9 & #10 from spec**

Add a fixed navigation bar between the header and the controls-sticky bar:

```html
<nav class="section-nav" id="section-nav">
  <div class="section-nav-inner">
    <button class="snav-tab active" data-snav="pre">Pre-Tournament</button>
    <button class="snav-tab" data-snav="r1">Rd 1</button>
    <button class="snav-tab" data-snav="r2">Rd 2</button>
    <button class="snav-tab" data-snav="r3">Rd 3</button>
    <button class="snav-tab" data-snav="final">Final</button>
    <button class="snav-tab snav-placeholder" data-snav="tee-times" disabled>Tee-Times ◌</button>
  </div>
</nav>
```

CSS:
```css
.section-nav {
  position: sticky; top: 0; z-index: 60;
  background: var(--surface2);
  border-bottom: 1px solid var(--border);
  padding: 0 1rem;
}
.section-nav-inner { max-width:1400px; margin:0 auto; display:flex; gap:0; overflow-x:auto; }
.snav-tab { padding:.55rem .9rem; font-size:.78rem; color:var(--muted); border-bottom:2px solid transparent; white-space:nowrap; transition:color .15s,border-color .15s; }
.snav-tab:hover { color:var(--text-1); }
.snav-tab.active { color:var(--gold); border-bottom-color:var(--gold); }
.snav-placeholder { opacity:.4; cursor:default; }
```

Wire `data-snav` → `switchRound()` equivalent. "Pre-Tournament" tab shows the pre-tournament view. R1–Final tabs are wired to Task 8's dynamic load.

## Task 5: Global activeFilters state + badge/tier filtering
**Fix #5 & #8 from spec**

1. Add `activeTagFilters: []` to state `S`

2. In `renderTable()` / `applyVisibility()`: add a filter pass that checks — for each player row — if ANY of their `strength_tags` or `weakness_tags` (from payload) includes ALL active tag filters. If `activeTagFilters.length > 0`, hide players that don't match.

3. In `buildTableRow()` and the modal's badge section: add `onclick` to each `.badge-strength` and `.badge-weakness` element:
   ```js
   onclick="toggleTagFilter('Elite Iron Play')"
   ```

4. `toggleTagFilter(tag)`:
   - If tag in S.activeTagFilters → remove it
   - Else → push it
   - Update active-pills bar with pill for each active tag (gold pill, click to remove)
   - Call `applyVisibility()`

5. Tier Intelligence blocks: each tier block header gets `onclick="filterByTier('T1')"` → sets `S.currentTier` and calls `applyVisibility()`. Already partially wired in existing `currentTier` state, but Tier Intel blocks are not clickable yet.

## Task 6: Analyst Mode UI repositioning
**Fix #6 from spec**

Current: Analyst Mode button is in the controls bar; the `#scenario-panel` is rendered in the middle of the page (between Contention chart and Tier Intel).

New layout:
- Move `#scenario-panel` (the slider sandbox) to be immediately above `#sec-contention`
- Add a sticky sub-header when Analyst Mode is active, positioned below `#section-nav` (from T4), with the `⊡ Analyst Mode` label + Reset + Exit buttons
- The `#analyst-mode-banner` (existing) stays as is (sticky below controls)

## Task 7: Contention Map dot visual hierarchy
**Fix #7 from spec**

In `renderContentionChart()` (Chart.js scatter):
- Base layer: all non-highlighted, non-debut players → `backgroundColor: 'rgba(75,85,99,0.6)'`, `borderColor: 'rgba(75,85,99,0.3)'`
- If `S.chartHighlightFlags`: flagged players → `backgroundColor: 'rgba(251,191,36,1.0)'`, `borderColor: '#fbbf24'`, `borderWidth: 2`
- If `S.chartHighlightDebut`: debut players → `backgroundColor: 'rgba(56,189,248,0.9)'`, `borderColor: '#38bdf8'`
- Render highlighted players in a separate dataset (Chart.js renders datasets in order, so last = on top)
- Split the single dataset into: `[baseDataset, debutDataset, highlightDataset]` — always render highlight last

## Task 8: Round tab dynamic payload fetch
Wire the section-nav tabs (from T4) to dynamically load round payloads:

Round URL mapping:
```js
const ROUND_PAYLOADS = {
  pre:   'data/2026_3m_open_event_payload.json',
  r1:    'data/2026_3m_open_rd1_payload.json',
  r2:    'data/2026_3m_open_rd2_payload.json',
  r3:    'data/2026_3m_open_rd3_payload.json',
  final: 'data/2026_3m_open_final_payload.json',
};
```

`switchRound(round)`:
1. Update active tab UI
2. Set `S.currentRound = round`
3. Show loading blur on board
4. `fetch(ROUND_PAYLOADS[round])` — on 404 → show "Round data not yet available" banner, restore pre-tournament data
5. On success → update `S.boardData`, call `renderAll()`
6. No hard page reload
