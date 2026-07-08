# 2026 U.S. Open — VenueDNA Dashboard
**Event:** 2026 U.S. Open | **Venue:** Shinnecock Hills GC | **Dates:** June 18-21, 2026

## Quick Start — No Server Needed
Open `2026_usopen_vts_dashboard.html` directly in Chrome, Firefox, or Safari.
All 156 player data is embedded in the JS file. No network requests required.

## Local Server (if downloads needed)
```bash
cd events/2026_USOPEN/deploy
python3 -m http.server 8000
# open http://localhost:8000/2026_usopen_vts_dashboard.html
```

## Dashboard Features
- Full 156-player sortable, filterable table
- Click any row or hero card to open the player detail drawer
- Drawer shows: VTS Decomposition bar, probability strip, trait profile, venue fit analysis, anti-pattern breakdown, conviction + failure condition
- Sidebar tier nav (T1-T5) filters the table instantly
- Search by player name, filter by Tour, anti-pattern status, gate status
- Download links to all JSON/CSV source files

## Source of Truth
All rankings, probabilities, VTS scores sourced directly from `2026_USOPEN_scored_field.csv`.
Narrative text generated from scoring model components — not hand-written.

## Output Files
```
output/
  2026_USOPEN_event_payload.json       Full event + player payload
  2026_USOPEN_player_briefs.json       T1/T2 briefs + all players
  2026_USOPEN_full_player_writeups.json All 156 players with full text
  2026_USOPEN_dashboard_data.csv       Flat CSV for analysis

deploy/
  2026_usopen_vts_dashboard.html       Dashboard (open this)
  2026_usopen_vts_dashboard.css        Styles
  2026_usopen_vts_dashboard.js         App + embedded data
  README_DEPLOY.md                     This file
```

## Weather Quick Reference
- R1 Thu: 20-27 mph / 35 gust | Rain + Gale — HARDEST DAY
- R2 Fri: 12-16 mph / 24 gust | Cloudy — Best scoring
- R3 Sat: 14-19 mph / 30 gust | Sunny — Punishing finish
- R4 Sun: 6-9 mph / 24 gust | Mostly Cloudy — Low scoring opportunity
