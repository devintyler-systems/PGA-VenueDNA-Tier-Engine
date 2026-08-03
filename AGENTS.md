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
- `data/venuedna_master.db` — canonical SQLite DB (56 KB); tracked. See Database Architecture section.
- `data/venue_dna.db` — harvester raw-cache DB; gitignored. Written by `dg_api_harvester.py`.
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

events/2026_Finished_Events/{event_slug}/  — archive location for completed tournaments.
  Same internal layout as an active event (input/engine/output/deploy/audit unchanged).
  Move an event here once its tournament is finished; when you do, check for and
  update any hardcoded `events/{slug}` path assumptions in that event's scripts,
  its tests, and any CI workflow that targets its `deploy/` folder.

library/venues/{venue_slug}/
  {venue_slug}_venue_profile.md
  {venue_slug}_CH.csv
  {venue_slug}_full_course_weather_data_{year}.json
  {venue_slug}_weather.txt  (raw hourly source)

data/raw/       — incoming DataGolf API pulls, unprocessed
data/processed/ — cleaned, normalized tournament and player data
data/venue/     — course characteristic profiles (yardage, rough, green speed, layout tags)
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

## Database Architecture

Two SQLite databases with distinct roles — do not conflate them.

### `data/venuedna_master.db` (tracked in git — 56 KB)
Processed production master. Holds canonical `players`, `tournaments`, `strokes_gained`, `venue_profiles`, and `venue_scores` tables.
Scripts that use it — all hardcode this path, ignoring `db_config.json`'s `db_path` field:
- `engine/datagolf_client.py` — manages schema; `DB_PATH` hardcoded
- `engine/ingest_manual_exports.py` — upserts into `active_field_projections`
- `engine/initialize_venues.py` — seeds `course_profiles`
- `engine/build_round_analysis.py` — reads for scoring (reads `db_config.json` for other settings only)
- `engine/traits_calculator.py` — queries trait rows (reads `db_config.json` for other settings only)

### `data/venue_dna.db` (untracked — gitignored)
Local raw API-cache and harvester working store. Created and populated on first run by `engine/dg_api_harvester.py`. Absent from a clean clone.
`config/db_config.json` declares `"db_path": "data/venue_dna.db"`. Only `dg_api_harvester.py` obeys that field. All other scripts that load `db_config.json` do so for `rate_limit_rpm`, `dg_base_url`, and `sparse_columns` only.

**Rule:** Never add a global `*.db` gitignore rule. `venuedna_master.db` is intentionally tracked; `venue_dna.db` has its own explicit gitignore entry.

## Conventions
- All scores normalized 0-100; higher = better venue fit
- Scoring weights: no hardcoded values outside the engine's config section
- DataGolf player IDs are canonical; map to internal IDs in `players` table
- Weather adjustments applied post-score as a multiplicative modifier
- SG categories: Off-the-Tee, Approach, Around-the-Green, Putting
- Confidence band: sample size < 8 tournaments at venue → flag as low confidence
- Deploy data files are PROTECTED — never rename without updating app.js first

## Active Event
No event is currently active. The two most recently active events have both been archived:
- **2026 Rocket Classic** — Detroit Golf Club — `events/2026_Finished_Events/2026_rocket_classic/`
- **2026 3M Open** — TPC Twin Cities — `events/2026_Finished_Events/2026_3m_open/`

When a new event kicks off, create it at `events/{event_slug}/` (flat, not under `2026_Finished_Events/`) and update this section. Move it to `2026_Finished_Events/` once its tournament finishes (see Canonical Folder Structure).

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
- `events/2026_Finished_Events/2026_USOPEN/output/derivatives/draftkings/` — non-canonical subfolder with DK outputs; doesn't follow canonical output/ structure.
- Open Championship `engine/` — canonical v3 scripts (`score_open_2026_v3.py`, `build_board_v3.py`) are active. Legacy v1/v2 versions and `build_dry_run_pack.py` were deleted in July 2026 cleanup.
- Finished event folder names under `events/2026_Finished_Events/` use mixed case (e.g., `2026_GenesisScottishOpen`) instead of canonical lowercase snake_case. Deferred: renaming requires auditing all downstream path references.

## Anti-Patterns to Avoid
- Do not hardcode weights anywhere — keep in engine's config section
- Do not modify raw/ data files; always write to processed/
- Do not run scoring engine on < 3 years of venue history without confidence flag
- Do not rename deploy/data/ files without updating app.js fetch calls first
- Do not store temp notes or planning files in deploy/data/ folders
- Do not let duplicate venue files accumulate in both input/ and library/venues/ — library/ is canonical
