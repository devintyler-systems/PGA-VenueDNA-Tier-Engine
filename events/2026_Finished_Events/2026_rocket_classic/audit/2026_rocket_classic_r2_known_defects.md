# 2026 Rocket Classic — Known Defect in Frozen R2 Live Snapshot

Logged: 2026-08-01

## Summary

The frozen R2 live-diagnostic snapshot (`output/2026_rocket_classic_r2_live.json` and
`deploy/data/2026_rocket_classic_r2_live.json`, committed in `e543bf4`) contains a
name-normalization defect inherited by `build_live_r2.py`'s original `normalize_name()`.

`round2_leaderboard.csv` spells three players' names with native diacritics, while every
other R2 source (SG csv, live-stats csv, event payload, teetimes) spells the same players
with the ASCII transliteration. The tokenizer regex (`[A-Za-z]+`) silently drops non-ASCII
letters instead of folding them, so "Højgaard" fragments into tokens `h` + `jgaard` instead
of `hojgaard` — producing a join key that matches nothing else in the artifact.

## Affected players

- Rasmus Højgaard
- Nicolai Højgaard
- Thorbjørn Olesen

## Consequence in the frozen artifact

In `cut_survivors`, these three players are present but keyed under fragmented,
malformed `player_key` values (`h|jgaard|rasmus`, `h|jgaard|nicolai`, `olesen|rn|thorbj`)
instead of the canonical `hojgaard|rasmus` / `hojgaard|nicolai` / `olesen|thorbjorn`. Because
nothing else in the artifact matches those malformed keys:

- `model_rank` / `model_tier` are `null` for all three (pre-event model cross-reference lost)
- `r1_detail` / `r2_detail` are `null` for all three (per-round live-stat detail lost)
- SG values (`sg_ott`/`sg_app`/`sg_arg`/`sg_putt`/`sg_total`) are present and correct, because
  the SG source file happens to use the same diacritic spelling as the leaderboard, so that
  one join still succeeds — only the *cross-source* joins (model payload, live-stats) fail
- Diagnostic bucket assignment for these three was still computed correctly (it only depends
  on SG values and leaderboard position, not on the model cross-reference), so
  `diagnostic_buckets` counts in the frozen snapshot are unaffected

## Disposition

The frozen R2 artifact (both copies) is preserved **unchanged**, on purpose, for audit
integrity — it reflects exactly what the live board showed at the time. It is not being
regenerated or patched.

The underlying parsing defect is fixed forward: diacritic folding (NFKD + explicit ø/æ
map) before name-tokenization now lives in `engine/live_builder_common.py`, shared by
`build_live_r2.py` (import-wired, but never re-run against the frozen output — see below)
and `build_live_r3.py` (built with the fix from the start). The R3 live snapshot does not
carry this defect: all three players resolve to correct, unified keys with populated
`pre_event_rank`/`pre_event_tier` and per-round detail.

`build_live_r2.py` was refactored on 2026-08-01 to import the fixed `normalize_name` /
`read_csv_raw` / weather-extraction primitives from `live_builder_common.py` instead of
maintaining its own duplicate, unfixed copies — this was verified safe via an in-process
diff of `build()`'s return value against the frozen file (never touching `OUT_PATHS`).
That diff confirms: if `build_live_r2.py` were ever re-run today, its output would *no
longer match* the frozen snapshot for these three players (the defect would be fixed) —
which is precisely why the frozen file is not being regenerated. The script's source now
carries the fix; the artifact intentionally does not.
