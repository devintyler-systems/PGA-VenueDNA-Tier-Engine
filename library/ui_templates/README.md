# VenueDNA Canonical UI Templates

Extracted from the 3M Open 2026 board (commit f428e22) after the full UX Blueprint Overhaul.

## Files

| File | Description |
|------|-------------|
| `template_board.html` | Main SPA HTML — title, header, section structure, modal/drawer markup |
| `template_app.js` | Full state machine — filtering, views, round loading, chart, analyst mode |
| `template_styles.css` | Theme-aware CSS design system (dark/light, all component classes) |

## Placeholders (replace when cloning for a new event)

| Placeholder | Replace with |
|-------------|-------------|
| `EVENT_NAME_PLACEHOLDER` | e.g. `Genesis Scottish Open 2027` |
| `VENUE_NAME_PLACEHOLDER` | e.g. `The Renaissance Club` |
| `COURSE_META_PLACEHOLDER` | e.g. `Par 70 · 7,034 yds · July 10–13, 2027 · North Berwick` |
| `FETCH_URL_PLACEHOLDER` | e.g. `2027_genesis_scottish_open_event_payload.json` |
| `EVENT_SLUG_PLACEHOLDER` | e.g. `2027_genesis_scottish_open` (prefix for all round/analysis payloads) |

## Cloning for a New Event

```bash
cp -r library/ui_templates/ events/{event_slug}/deploy/
cd events/{event_slug}/deploy/
# Rename files
mv template_board.html {year}_{event_slug}_board.html
mv template_app.js app.js
mv template_styles.css styles.css
# Run find/replace on all 5 placeholders
```

## What's Included in This Template

- Right-side slide-out player drawer (not center modal)
- Dark/light theme toggle (targets `document.documentElement`)
- Section nav bar: Pre-Tournament / Rd 1–4 / Final / Tee-Times
- Dynamic round payload fetch (graceful 404 fallback)
- Badge/tier filtering with tag normalization
- Active filter pills with dismiss buttons
- Analyst Mode weight sandbox with live slider reactivity
- Contention Map: 3-dataset dot hierarchy (base / debut / highlight)
- Spotlight cards with flex layout
- Venue DNA grid with equal-height card stretch
- Pre-tournament data snapshot/restore on round switch
