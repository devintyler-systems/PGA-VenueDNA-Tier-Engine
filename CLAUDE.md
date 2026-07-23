# PGA VenueDNA
project_handle: pga_venuedna

## Identity
A course-DNA prediction engine for PGA Tour tournaments. Scores players based on historical venue fit using strokes gained, course characteristics, and weather adjustments. Core output: ranked player lists per tournament with confidence-weighted scores.

## Stack
- Python (pipeline scripts), HTML/JS/CSS (deployed board app per event)
- Database: SQLite (`data/venuedna_master.db`)
- Data sources: DataGolf API, manual stat ingestion
- Deployment: static HTML/JS boards served locally per event

## Actual Architecture (not Streamlit — pure pipeline + static deploy)
1. **Input** — DataGolf CSVs + venue profile + weather JSON → `events/{slug}/input/`
2. **Engine** — Python pipeline scripts at `engine/` (shared root) compute VTS scores
3. **Output** — scored CSVs + JSON artifacts → `events/{slug}/output/`
4. **Deploy** — `app.js` + `index.html` + `styles.css` consume `deploy/data/` JSON/CSV → `events/{slug}/deploy/`

## Key Files
- `engine/build_round_analysis.py` — main shared scoring engine (84 KB); event configs embedded
- `engine/traits_calculator.py` — trait calculations
- `engine/latent_model.py` — latent model for venue fit
- `engine/enrich_cards.py` — player card enrichment
- `engine/dg_api_harvester.py` — DataGolf API ingestion
- `data/venuedna_master.db` — canonical SQLite DB (56 KB); `data/venue_dna.db` is zero-byte artifact
- `standards/` — scoring specs, architecture docs, audit SOPs
- `library/venues/` — per-venue profiles (each venue has its own subfolder)

## Canonical Folder Structure
```
events/{event_slug}/
  input/      — raw venue/course CSVs, DataGolf pulls, weather JSON
  engine/     — event-specific engine forks (optional; root engine is shared fallback)
  output/     — computed VTS CSVs, JSON payloads, trait matrices
    round{n}/ — per-round analysis artifacts
    final_tournament/ — post-tournament artifacts
  deploy/     — static board app (app.js, index.html, styles.css)
    data/     — CSVs/JSONs consumed by app.js
  audit/      — audit logs, council reviews, diagnostics

library/venues/{venue_slug}/
  {venue_slug}_venue_profile.md
  {venue_slug}_CH.csv
  {venue_slug}_full_course_weather_data_{year}.json
  {venue_slug}_weather.txt  (raw hourly source)

data/raw/       — incoming DataGolf API pulls, unprocessed
data/processed/ — cleaned, normalized tournament and player data
data/venue/     — course characteristic profiles (yardage, rough, green speed, layout tags)
ingestion/      — API call scripts, PDF parsers, manual stat loaders
library/engine/ — master system prompts, scoring specs, rebuild guides
library/templates/ — intake forms, CLAUDE.md template
standards/      — canonical architecture docs and scoring specs
docs/           — planning docs, specs, SOP references, feature ideas
tests/          — unit tests for engine components
tools/          — utility scripts (update_claude_md.py)
```

## Naming Conventions
- **Event files:** `{year}_{event_slug}_{descriptor}.{ext}` — year FIRST, then event slug
  - ✅ `2026_3m_open_vts_full.csv`
  - ❌ `3m_open_2026_vts_full.csv` (year not first)
- **Venue files:** `{venue_slug}_{descriptor}.{ext}`
  - ✅ `tpc_twin_cities_venue_profile.md`
- **Deploy data:** filenames must match exactly what `app.js` fetches (check before renaming)
- **No spaces** in any filename — use underscores
- **Lowercase** event slugs in folder names
- **Round folders:** `round1/` through `round4/`, `final_tournament/`

## Data Model (Key Tables)
- `players` — canonical player IDs, names, DataGolf IDs
- `tournaments` — course, year, conditions metadata
- `strokes_gained` — per-player, per-tournament SG splits
- `venue_profiles` — course DNA features (normalized 0-100)
- `venue_scores` — final VenueDNA scores per player per tournament

## Conventions
- All scores normalized 0-100; higher = better venue fit
- Scoring weights: no hardcoded values outside the engine's config section
- DataGolf player IDs are canonical; map to internal IDs in `players` table
- Weather adjustments applied post-score as a multiplicative modifier
- SG categories: Off-the-Tee, Approach, Around-the-Green, Putting
- Confidence band: sample size < 8 tournaments at venue → flag as low confidence
- Deploy data files are PROTECTED — never rename without updating app.js first

## Active Event
**2026 3M Open** | TPC Twin Cities | R1 starting 2026-07-23
- Event folder: `events/2026_3m_open/`
- Venue library: `library/venues/tpc_twin_cities/`
- Engine: shared root `engine/` (no event-local fork — root engine is the live copy)
- Weather source: NWS Twin Cities / TWC point forecast (Blaine MN, 45.17°N 93.24°W)
- Deploy: `events/2026_3m_open/deploy/` — live board with 4-round weather, VTS scores, Analyst Mode

## Current State
Session stamp: 2026-07-23 (post-cleanup)

- Branch: main
- Recent changes (latest first):
  - a6144ac | 2026-07-23 | fix(3m-open): board hierarchy + modal overflow
  - 6f1e6c7 | 2026-07-23 | fix(3m-open): move venue DNA to top + fix modal scroll truncation
  - ce3263d | 2026-07-23 | feat(3m-open): real 4-round weather forecast from NWS/TWC data
  - 278933c | 2026-07-23 | feat(3m-open): venue DNA panel + weather data from library files
  - 56306f7 | 2026-07-22 | fix: clear analyst-mode-row on Analyst Mode exit
- Next focus: [R1 live build — update with tee times / pairings / live SG when available]

## Known Issues / Debt
- `events/2026_3m_open/engine/` is empty — 3M Open runs against root engine (no protected per-event snapshot). Risk: root engine could be overwritten before post-mortem.
- `deploy/data/board_export.json` violates naming convention but CANNOT be renamed without updating app.js line 133.
- `deploy/3m_open_2026_board.html` + `index.html` are two entry points; `index.html` references `3m_open_2026_board.html` — rename requires updating both atomically.
- `deploy/data/3m_open_2026_overhaul_notes.txt` — temp note in live deploy/data/ folder; should be deleted.
- `data/venue_dna.db` — zero-byte file (artifact); `data/venuedna_master.db` is the real DB.
- `public/` folder — full mirror of Open Championship deploy (26 files, ~10 MB); purpose unclear (web server root?). Awaiting human decision on whether to keep/delete.
- Open Championship `engine/` — 3 versions of scoring script (score_open_2026.py, _v2, _v3) and 2 board builders (build_board_v2, build_board_v3). Canonical version unclear.
- `events/2026_USOPEN/DraftKings/` — non-canonical subfolder with DK outputs; needs to move to output/ or deploy/data/.
- `library/` root: `CJ_CUP_Byron_Nelson_Kickoff_Prompt.md` and `promo_playbook.md` are purpose-unclear artifacts.
- `engine/__pycache__/backfill_history.cpython-312.pyc` — orphaned bytecode; source `.py` deleted.

## Anti-Patterns to Avoid
- Do not hardcode weights anywhere — keep in engine's config section
- Do not modify raw/ data files; always write to processed/
- Do not run scoring engine on < 3 years of venue history without confidence flag
- Do not rename deploy/data/ files without updating app.js fetch calls first
- Do not store temp notes or planning files in deploy/data/ folders
- Do not let duplicate venue files accumulate in both input/ and library/venues/ — library/ is canonical
