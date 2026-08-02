# 2026 Rocket Classic — R4 Rollover Operator Note

Logged: 2026-08-01, ahead of the R4 rollover (R4 not yet played)

Before building `build_live_r4.py`, do the following — do not assume R3's shape carries
forward unchanged. Every round so far has broken at least one "just repoint the path"
assumption (R3 added a leaderboard column, changed CSV encoding, and changed the weather
source's prose format from R2).

1. **Inspect round4 source files fresh.** Check leaderboard/SG/live-stats/course-stats
   column layout and file encoding (UTF-8 vs cp1252) directly — don't assume they match R3.

2. **Leaderboard will likely gain another score column.** R2 had `TOTAL,R1,R2,STROKES`; R3
   added `R3` → `TOTAL,R1,R2,R3,STROKES`. R4's leaderboard will likely add `R4` the same
   way, including re-checking the amateur-marker-in-TOTAL-slot edge case against the new
   column count.

3. **Do not repoint the cut-line reference off `round2_leaderboard.csv` without confirming
   intent.** The cut line is fixed once R2 finishes and never moves — `build_live_r3.py`
   reads it from the frozen R2 leaderboard on purpose, not from R3's own totals (which
   would have drifted). R4 should read the same R2 reference, not `round3_leaderboard.csv`
   or `round4_leaderboard.csv`.

4. **R4 is the final round — there is no R5 to look ahead to.** Confirm before coding
   whether the R4 live artifact drops the lookahead `teetimes`/`weather` section entirely,
   or reframes it as final-results context. This is a structural decision, not a
   path-parameter — do not silently carry the R3→R4 lookahead pattern forward.

Reusable without re-verification: `engine/live_builder_common.py` (name normalization,
encoding fallback, weather-extraction tiers, numeric helpers) — proven stable across R2
and R3 already.
