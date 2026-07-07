# PGA VenueDNA — 2026 Genesis Scottish Open
### Static HTML Board · Deploy Package · VenueDNA v2

---

## Event

**Event:** 2026 Genesis Scottish Open  
**Venue:** The Renaissance Club, North Berwick, East Lothian, Scotland  
**Dates:** July 10–13, 2026  
**Format:** 72-hole stroke play, cut after 36 holes  
**Defending Champion:** Chris Gotterup (2025, -15)  
**Model version:** VenueDNA v2  

---

## Contents

```
deploy/
├── index.html          main board shell
├── styles.css          dark-mode board styles
├── app.js              board logic (fetches data, renders table + modal + briefs)
├── data/
│   ├── event_payload.json    full event + field payload (primary data source)
│   ├── vts_full.csv          scored field (VTS, probabilities, tier, flags — all players)
│   ├── player_briefs.json    full narrative briefs (all 166 players, rich/medium/compact)
│   └── links.json            tournament/repo/deploy URLs
└── README.md           this file
```

---

## Quick Start (local preview)

The board uses `fetch()` and **must be served over HTTP** — opening `index.html` directly in a browser (`file://`) will produce a CORS error.

**Option A — Node.js**
```
npx serve .
# or:
npx http-server . -p 8080
```

**Option B — Python**
```
python -m http.server 8080
```

Then open `http://localhost:8080`.

---

## Netlify Deploy

1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag the entire `deploy/` folder onto the drop zone
3. Netlify assigns a URL instantly
4. Rename the site in **Site settings → Change site name**

No build step required. Fully static.

---

## Board Features

| Feature | Details |
|---------|---------|
| Tier tabs | Filter by All / T1 / T2 / T3 / T4 / T5 |
| Sortable table | Sort by rank, VTS, win%, top10%, cut%, tier, flags |
| VTS bar | Visual score bar proportional to 0–100 |
| Cut column | Shows make_cut_prob (this event HAS a cut) |
| AP flags | Anti-pattern flags visible on rows |
| Player modal | Click any row for full analysis: 9 sections including decomposition |
| T1/T2 brief cards | Narrative spotlight cards with conviction statements |
| Favorites | Star any player; compare up to 4 in side-by-side modal |
| Filter lab | Multi-rule trait filters with Scottish Open presets |
| Views | Quick presets: Iron Elites, Long-Iron Fits, Positional Drivers, Ceiling Plays |
| Responsive | Mobile-friendly collapsible controls |

---

## Model Summary

| Parameter | Value |
|-----------|-------|
| Model version | VenueDNA v2 |
| Field size | 166 players |
| Tier 1 | ≥80 VTS (5 players) |
| Tier 2 | 65–79 VTS (24 players) |
| Tier 3 | 50–64 VTS (69 players) |
| Tier 4 | 35–49 VTS (40 players) |
| Tier 5 | <35 VTS (28 players) |
| Variance class | HIGH (links course) |
| Primary trait | APP 150-200 Long Iron (0.28 weight) |
| Anti-pattern flags | 30 players flagged |
| Debut Watch | 39 players |

### Top 5 (Tier 1)
1. Wyndham Clark — VTS 92.0
2. Rory McIlroy — VTS 84.3
3. Scottie Scheffler — VTS 82.9
4. Matt Fitzpatrick — VTS 81.1
5. Tyrrell Hatton — VTS 81.1

---

## Venue Intelligence

**The Renaissance Club key traits:**
- SG:APP 150-200 (long-iron scoring): 28% weight
- SG:APP overall: 20% weight
- SG:T2G composite: 15% weight
- Driving accuracy / corridor discipline: 12% weight
- SG:PUTT (Renaissance surface, regressed): 10% weight
- SG:ARG / scrambling: 8% weight
- SG:OTT distance: 4% weight
- Par-3 performance: 3% weight

**Anti-pattern profiles:** Distance-without-accuracy (bomb & spray), negative-approach debuts on links, pure-putter upside from non-links surfaces, SG:ARG below -0.5.

---

## Regenerating

From `C:\PGA_VenueDNA\events\2026_GenesisScottishOpen\engine\`:

```
python score_engine_v2.py
```

Outputs all 8 event-pack files to `../output/`. Copy data files to `../deploy/data/` manually or via the copy commands in the build log.

---

## Reference App

Reference implementation (Travelers Championship):  
https://2026-travelerschampionship-venuedna.netlify.app/

GitHub repo:  
https://github.com/devintyler83/PGA-VenueDNA-Tier-Engine
