# 2026 Rocket Classic — R4 Live Layer: Blocked Pending Results

Logged: 2026-08-01

## Status

R4 live-layer work (`build_live_r4.py`, a new R4 JSON schema, and any
`fixture_harness.*` changes) is **blocked**. `output/round4/` currently contains only
lookahead/context files, not result data:

- `detroit_golf_club_r4_weather_data_2026.json` (forecast)
- `pga_field_r4_teetimes.csv` (tee times)

None of the following exist yet, anywhere in the event tree:

- `round4_leaderboard.csv`
- `round4_player_strokes_gained.csv`
- `live_stats_r4_values.csv`
- `round4_course_stats.csv`

`output/final_tournament/` is also empty.

## What must land before work resumes

All four result files above. Once they exist in `output/round4/`, the next step is the
previously drafted prompt: inspect the new files fresh (column layout, encoding,
amateur-marker/CUT edge cases — don't assume R3's shape), then copy
`build_live_r3.py` → `build_live_r4.py`, wire it to `engine/live_builder_common.py`,
keep the cut-line reference on `round2_leaderboard.csv` unless told otherwise, and
decide — before writing code — whether the artifact drops lookahead teetimes/weather
or reframes as final-results context, since R4 is the last round.

## No code changed in this check

This is a status note only. No builder, schema, or frontend files were touched.
