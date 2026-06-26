# PGA VenueDNA — Travelers Championship 2026
### Static HTML Board · Deploy Package

---

## Contents

```
deploy/
├── index.html          main board shell
├── styles.css          dark-mode board styles
├── app.js              board logic (fetches data, renders table + modal + briefs)
├── data/
│   ├── event_payload.json    tier data + probabilities (primary data source)
│   ├── vts_full.csv          full 71-column model trace (all players)
│   ├── player_briefs.json    T1/T2 narrative briefs
│   └── links.json            tournament/DG/weather URLs
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

Then open `http://localhost:8080` (or the port shown).

---

## Netlify Drag-and-Drop Deploy

1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag the entire `deploy/` folder onto the drop zone
3. Netlify assigns a URL instantly (e.g. `magical-name-123.netlify.app`)
4. Rename the site in **Site settings → Change site name** if desired

No build step, no config file needed. The site is fully static.

---

## Board Features

| Feature | Details |
|---------|---------|
| Tier tabs | Filter table by All / T1 / T2 / T3 / T4 / T5 |
| VTS bar | Visual bar proportional to score out of 100 |
| AP flags | Color-coded tags: BOMB · WEDGE- · BIRDIE- · ROUGH- |
| Player modal | Click any row for full model trace + probability breakdown |
| T1/T2 briefs | Narrative cards below the table |
| No-cut annotation | Cut column shows "N/A" throughout (signature event) |
| Responsive | Horizontal scroll on mobile via `.table-wrap` |

---

## Model Summary

| Parameter | Value |
|-----------|-------|
| Spec version | 1.1 |
| Field size | 72 players (no cut) |
| Tier bands | T1≥80 · T2 65–79 · T3 50–64 · T4 35–49 · T5<35 |
| AP_TO_VTS | 2.0 (standard venue) |
| WIN_EXP | 4.5 (72-player no-cut) |
| WIN_CAP | 14% |
| Dominant trait | APP_Wedge (0.22 weight) |
| Birdie-fest | Yes — field avg −0.76/round vs par |

### Tier Distribution (initial build)
- T1: 1 · T2: 3 · T3: 15 · T4: 36 · T5: 16

---

## Data Status & Audit Notes

**Field source:** `tpc_river_highlands_CH.csv` (71 players).
`pga_field.csv` was not present at build time — field derived from course-history file.
One player may be missing from the CH file (72-player event). Supply `pga_field.csv`
and re-run `engine/venuedna_pipeline_travelers2026.py` to complete the field.

**Tee times:** All `r1_tee_time = TBD`. Retrieve from the PGA TOUR field page when
Thursday groupings are released (typically Tuesday of tournament week).

**make_cut_pct / miss_cut_pct:** `not_applicable` for all players.
This is a no-cut signature event. The board displays "N/A" in the cut column.

**Anti-pattern calibration:** `AP_TO_VTS=2.0` (standard birdie-fest venue).
Major-championship scale is 3.0; this event does not warrant that severity.

**Tier gate contradiction check:** All 71 rows passed `tier_gate_check = ok`.
No VTS≥80+gate=clear rows assigned to Tier 2 or lower.

**Audit flags (pre-publication review recommended):**
- Brian Harman — VTS 49.0, Tier 4, no AP flags. Five consecutive top-10s here historically.
  One point below Tier 3 boundary; consider narrative note in pre-pub brief.
- Keegan Bradley — `wedge_liability` AP flag active (sg_app=0.15 last 12m), but 2 wins
  at this venue. AP flag is mechanically correct; counter-narrative belongs in brief.

---

## Regenerating the Pack

From `C:\PGA_VenueDNA\events\2026_TravelersChampionship\engine\`:

```
python venuedna_pipeline_travelers2026.py
```

Outputs all 7 event-pack files to `../output/` and copies data files to `../deploy/data/`.
The pipeline reads from `../input/` — update source CSVs before re-running.
