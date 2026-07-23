# PGA VenueDNA
project_handle: pga_venuedna

## Identity
A course-DNA prediction engine for PGA Tour tournaments. Scores players based on historical venue fit using strokes gained, course characteristics, and weather adjustments. Core output: ranked player lists per tournament with confidence-weighted scores.

## Stack
- Python, Streamlit, Pandas, SQLAlchemy
- Database: SQLite (local dev), Postgres (prod-ready)
- Data sources: DataGolf API, manual stat ingestion
- Deployment: local Streamlit server

## Key Files
- `app.py` — Main Streamlit UI, tournament selector, player rankings view
- `scoring_engine.py` — Core VenueDNA algorithm; strokes gained weighting, course fit logic
- `config.py` — All scoring weights and tunable parameters (nothing hardcoded in engine)
- `data/raw/` — Incoming DataGolf API pulls, unprocessed
- `data/processed/` — Cleaned, normalized tournament and player data
- `data/venue/` — Course characteristic profiles (yardage, rough, green speed, layout tags)
- `db/schema.sql` — SQLite schema; reference before adding tables
- `ingestion/` — API call scripts, PDF parsers, manual stat loaders

## Data Model (Key Tables)
- `players` — canonical player IDs, names, DataGolf IDs
- `tournaments` — course, year, conditions metadata
- `strokes_gained` — per-player, per-tournament SG splits
- `venue_profiles` — course DNA features (normalized 0-100)
- `venue_scores` — final VenueDNA scores per player per tournament

## Conventions
- All scores normalized 0-100; higher = better venue fit
- Scoring weights live in `config.py` only — never hardcode in engine
- DataGolf player IDs are canonical; map to internal IDs in `players` table
- Weather adjustments applied post-score as a multiplicative modifier
- SG categories: Off-the-Tee, Approach, Around-the-Green, Putting
- Confidence band: sample size < 8 tournaments at venue → flag as low confidence

## Current State / Active Work
Session stamp: 2026-07-18 00:17

- Branch: main
- Recent changes (latest first):
  - 79bd241 | 2026-07-17 | System — architecture blueprint: UI/UX structural spec + schema v1.1 trait keys
  - 1338a5d | 2026-07-17 | Open 2026 — R2 integrity pass: CUT clamp, weather metadata, firm/fast lean_up guarantee, narrative dedup guard
  - 7cc4a99 | 2026-07-17 | Open 2026 — R2 live build: firm/fast SG overrides, spin penalty, glossaryModalOpen rename, applyLeaderboardFilters extraction
  - 1ff1ea1 | 2026-07-17 | Open 2026 — premium UI port: forecast deck, rule-builder filters, glossary modal, cum-learning grid
  - 6aba75c | 2026-07-16 | Open 2026 — R2 build: CUT guard, cumulative fallback, trait-row history format
- Next focus: [fill this in before you start the session]

## Known Issues / Debt
[Track open bugs, edge cases, or pending refactors here]

## Anti-Patterns to Avoid
- Do not hardcode weights anywhere except config.py
- Do not modify raw/ data files; always write to processed/
- Do not run scoring engine on < 3 years of venue history without confidence flag