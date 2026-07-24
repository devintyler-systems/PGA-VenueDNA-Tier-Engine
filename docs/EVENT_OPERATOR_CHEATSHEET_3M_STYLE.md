# EVENT_OPERATOR_CHEATSHEET_3M_STYLE

Keep this open while running a week. It assumes the 3M Open–style structure.

1. Context & paths
- Root: C\PGA_VenueDNA
- Active event: events/2026_3m_open/
- Venue intelligence: library/venues/tpc_twin_cities/

2. Authority order (never improvise around this)
- Engine math & naming: standards/02_PGA_VENUEDNA_SCORING_SPEC.md
- Learning loop & rounds: standards/03_PGA_VENUEDNA_LEARNING_LOOP.md
- Artifact/file contract: standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
- library/engine/* = reference-only design notes.

3. Required inputs before any build
- events/2026_3m_open/input/2026_3m_open_field_input.csv
- events/2026_3m_open/input/2026_3m_open_event_context.json
- events/2026_3m_open/input/tpc_twin_cities_venue_profile.md
- events/2026_3m_open/input/tpc_twin_cities_full_course_weather_data_2026.json
- SG & DG core: pga_field.csv, dg_performance_2026.csv, SG query CSVs (l6/l12/l24, similar/all), dg_course_table.csv, dg_decomposition.csv.

If any of these are missing or stale → stop.

4. Mandatory pre-tourney outputs in output/
- 2026_3m_open_vts_full.csv
- 2026_3m_open_event_payload.json
- 2026_3m_open_player_briefs.json
- 2026_3m_open_trait_form_matrix.csv
- 2026_3m_open_links.json

If any are missing → the build is not complete.

5. Deploy sanity
- events/2026_3m_open/deploy/ has index.html, app.js, styles.css, data/.
- Every file in deploy/data/ for this event starts with 2026_3m_open_.
- app.js fetch paths match those names; no bare paths like board_export.json or weather_forecast.json.

6. Engine edits rule
- Shared engine scripts live under engine/ at repo root.
- Event-specific overrides belong in events/2026_3m_open/engine/.
- Never silently change shared engine scripts just for one event week.

7. Round workflow (per N)
- Place roundN_leaderboard.csv and roundN_player_strokes_gained.csv in events/2026_3m_open/output/roundN/ (plus optional course_stats/insights).
- Run build_round_analysis.py --round N.
- Confirm output/2026_3m_open_rN_analysis.json and deploy/data/2026_3m_open_rN_analysis.json exist, plus updated deploy/data/2026_3m_open_cumulative_learning.json.

8. Dashboard check
- Serve events/2026_3m_open/deploy/ over HTTP.
- Tournament Learning tab shows LIVE badge for built rounds.
- Leaderboard snapshot, trait audit, and Live Lean notes populate.

9. Audit & derivatives
- Audit artifacts: events/2026_3m_open/audit/ (audit_log, council_review, writeback, miss_ledger rows).
- Derivatives (DFS, DK, sims): events/2026_3m_open/output/derivatives/.
- Derivatives never sit in deploy/data/ or alongside core ranking files.

10. R1 go / no-go
- All required inputs present.
- All mandatory outputs present.
- deploy/data/ normalized and wired.
- Authority understood: standards/ governs, library/engine/ informs.
- Event-specific engine changes, if any, live under events/2026_3m_open/engine/.

If any of these five are false → fix before you trust R1 output.
