# EVENT_DEPLOY_CHECKLIST_3M_STYLE

Version: 2026-07-23
Purpose: Standardized event setup and deploy checklist using the cleaned 2026 3M Open as the reference model.

## 1. Event Setup — Before Any Build

### 1.1 Context lock
- Event slug: `3m_open`
- Event folder: `events/2026_3m_open/`
- Venue: TPC Twin Cities (active venue intelligence in `library/venues/tpc_twin_cities/`)
- Current task: pre-tournament build, live round update, or post-event audit — state it explicitly.

### 1.2 Folder structure lock
Confirm the canonical event structure exists:

```text
events/2026_3m_open/
  input/
  output/
    round1/
    round2/
    round3/
    round4/
  engine/
  deploy/
    data/
  audit/
```

If any subfolder is missing, create it before placing files.

### 1.3 Input completeness lock
Inside `events/2026_3m_open/input/` confirm:
- `2026_3m_open_field_input.csv` — player-level modeling input (matches field schema in standards scoring spec).
- `2026_3m_open_event_context.json` — venue/setup context (matches context schema in artifact schema).
- `tpc_twin_cities_venue_profile.md` — venue profile notes (course traits, hole characteristics).
- `tpc_twin_cities_full_course_weather_data_2026.json` — weather forecast and historical pattern.

Also confirm core SG and DataGolf inputs are present:
- `pga_field.csv`
- `dg_performance_2026.csv`
- SG query CSVs (`*_l6.csv`, `*_l12.csv`, `*_l24.csv` for similar/all courses).
- `dg_course_table.csv`
- `dg_decomposition.csv`

If any required input is missing or stale, **stop** and resolve before running the pipeline.

## 2. Pre-Tournament Build — 3M Pattern

### 2.1 Engine authority lock
- Active scoring rules: `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`.
- Active learning-loop rules: `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`.
- Active artifact schema: `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`.
- `library/engine/` docs are reference-only; do not change engine behavior based on those without updating `standards/`.

### 2.2 Engine scripts
For the 3M Open, the event uses shared root engine scripts:
- `engine/traits_calculator.py`
- `engine/latent_model.py`
- `engine/build_round_analysis.py`

If you need event-specific overrides (e.g., R1 weight changes), **snapshot** the root engine scripts into `events/2026_3m_open/engine/` and work there. Do not mutate shared engine scripts without a standards update.

### 2.3 Build outputs expected in `output/`
After a successful pre-tournament build, expect at least:
- `2026_3m_open_vts_full.csv` — canonical ranked field.
- `2026_3m_open_event_payload.json` — primary app payload.
- `2026_3m_open_player_briefs.json` — player card content.
- `2026_3m_open_trait_form_matrix.csv` — trait/form diagnostics.
- `2026_3m_open_links.json` — external URLs.

If any of these are missing, treat the build as incomplete.

## 3. Deploy — 3M Reference State

### 3.1 Deploy shell
Inside `events/2026_3m_open/deploy/` confirm:
- `index.html`
- `app.js`
- `styles.css`
- `data/`
- optional `2026_3m_open_README.md`.

The app must run from this folder over HTTP (e.g., `python -m http.server 8080` from `deploy/`).

### 3.2 Deploy data files
Inside `deploy/data/` for 3M Open, the cleaned reference set is:
- `2026_3m_open_vts_full.csv`
- `2026_3m_open_event_payload.json`
- `2026_3m_open_player_briefs.json`
- `2026_3m_open_links.json`
- `2026_3m_open_trait_form_matrix.csv`
- `2026_3m_open_board_export.json`
- `2026_3m_open_weather_forecast.json`
- `2026_3m_open_final_analysis.json` (if present)
- `2026_3m_open_post_mortem_analysis.json` (if present)

Rule: **no bare names** — all deploy data files for the active event must start with `2026_3m_open_`.

### 3.3 app.js fetch paths
In `deploy/app.js`, confirm:
- All fetch URLs point to `data/2026_3m_open_*.json` or `data/2026_3m_open_*.csv`.
- Round analysis, cumulative learning, and post-mortem files use the `2026_3m_open_r{N}_analysis.json` and `2026_3m_open_cumulative_learning.json` patterns.
- No fetch paths reference legacy names like `board_export.json`, `weather_forecast.json`, or `final_analysis.json` without the event prefix.

If any bare paths remain, fix the filenames and references together before deployment.

## 4. Live Round Workflow — Minimal 3M Checklist

### 4.1 Round input placement
For each round `N`:
- Place `round{N}_leaderboard.csv` and `round{N}_player_strokes_gained.csv` into `events/2026_3m_open/output/round{N}/`.
- Optionally place `round{N}_course_stats.csv` and `round{N}_course_insights.csv` in the same folder.

### 4.2 Round build
From the engine folder:
- Run `build_round_analysis.py --round N` using the shared engine or event-local copy.
- Confirm it writes both `output/2026_3m_open_r{N}_analysis.json` and `deploy/data/2026_3m_open_r{N}_analysis.json`.
- Confirm `deploy/data/2026_3m_open_cumulative_learning.json` updates.

### 4.3 Dashboard verification
After each round build:
- Serve `deploy/` locally.
- Check the Tournament Learning tab shows a LIVE badge for the new round.
- Confirm leaderboard snapshot, trait audit, and live-lean notes populate correctly.

## 5. Audit & Derivatives — Guardrails

### 5.1 Audit artifacts
Post-event, ensure audit files live in `events/2026_3m_open/audit/`:
- `2026_3m_open_audit_log.md`
- `2026_3m_open_council_review.md`
- optional `2026_3m_open_audit_writeback.json` and `2026_3m_open_miss_ledger_rows.csv`.

Do not overwrite pre-event outputs in `output/` with audit adjustments; treat them as separate artifacts.

### 5.2 Derivative outputs
Any DraftKings, betting, or simulation files should live under an explicit derivatives path, for example:
- `events/2026_3m_open/output/derivatives/`.

Rule: derivative outputs never sit alongside core ranking artifacts or deploy data files.

## 6. Quick R1 Readiness Checklist (3M Pattern)

Before R1:
1. Confirm `input/` contains field input, event context, venue profile, and weather JSON for 3M.
2. Confirm `output/` contains vts_full, event_payload, player_briefs, trait_form_matrix, and links for `2026_3m_open`.
3. Confirm `deploy/data/` contains the 9+ `2026_3m_open_*` files and that app.js fetch paths match them.
4. Confirm standards docs are the authority for scoring, learning-loop, and artifacts; library/engine docs are reference-only.
5. Confirm any event-specific engine modifications were made in `events/2026_3m_open/engine/`, not in the shared root engine.

If all five are true, the event is structurally R1-ready.
