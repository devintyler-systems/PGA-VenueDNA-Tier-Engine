# Claude Code Prompt 01 — Phase 1 UI foundation

You are upgrading a static PGA VenueDNA event app for the 2026 Open Championship at Royal Birkdale.

Your mission: implement the highest-ROI Phase 1 UX upgrades without changing the canonical model logic.

## Non-negotiables

- Do not rewrite, reinterpret, or recompute the core VenueDNA scoring model in the browser.
- Treat source ranking files and payload files as the single source of truth.
- Preserve separation between NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, and derivative UX views.
- Do not use localStorage or sessionStorage.
- Keep the app deployable as a static site.
- Mobile usability is mandatory.

## Build scope

Implement these in this order:
1. Audit-flag tooltip system
2. Fuzzy search and structured filters
3. Responsive desktop/mobile board modes

## Required behavior

### Audit-flag tooltips
- Add hover and click tooltips to every flag badge
- Show flag code, rule label, penalty magnitude, and trigger trace if present
- Support tap interaction on mobile
- Severity tint must map to actual penalty magnitude

### Search and filters
- Add fuzzy name search
- Add structured filters for tier, flag, country, win probability band, make-cut band, debut status, and driver trait
- Support keyboard navigation and fast clear/reset
- Filtering must not alter canonical rank values

### Responsive views
- Desktop keeps a sortable table
- Mobile switches to stacked player cards
- Conditions bar becomes collapsible on small screens
- One shared render source so cards and table cannot diverge

## Technical preferences
- Plain JS is fine; lightweight libraries allowed if CDN-based
- Fuse.js allowed for search
- Keep CSS disciplined and mobile-first
- Build for a static deploy package

## Files to touch
- index.html
- styles.css
- app.js
- data payload files only if additive UI fields are required

## Output
Return:
1. a concise implementation summary
2. exact files changed
3. any new payload fields needed
4. follow-up TODOs for Phase 1 remainder
