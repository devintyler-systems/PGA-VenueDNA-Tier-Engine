# Field-Completeness Check — Addendum to enrich_cards.py

**Status:** Proposed. Human approval required before merge — this touches `engine/enrich_cards.py`, which is gated per the Ralph Loop policy (`docs/RALPH-LOOP-POLICY.md`) and the Automation Backlog's Post-Event VenueDNA Learning Loop entry. Logging-only, no write-back, no scoring impact — but still engine-layer, so it goes through normal review, not an unattended loop.

## Why

`/verify-board 2026_3m_open` (2026-07-23 run) flagged 2 of 145 players with blank Form-column sparklines despite `data_depth != DEBUT`: **Lindheim, Nicholas** (dg_id `16713`) and **Campbell, Thomas** (dg_id `18359`). Root cause, confirmed against source CSVs:

- Both appear in `events/2026_3m_open/input/pga_field.csv` with `dg_rank: null, owgr_rank: null` — unranked, late-field additions (Monday qualifier / sponsor exemption profile).
- Neither appears in `events/2026_3m_open/input/pga_field_trending_table.csv` at all — zero rows, confirmed via direct grep, not a name-matching failure (`Campbell, Brian`, dg_id `18628`, is a different player already correctly excluded).

This is a **pull-order gap between two DataGolf source files** — `pga_field.csv` was pulled after these players locked into the field (it has their tee times); `pga_field_trending_table.csv` was pulled before. `enrich_cards.py` and `app.js` both behaved correctly given the data they received — this is upstream, not a logic bug.

It's silent today: a missing trending row just produces `l5_array: []`, rendered as a blank canvas indistinguishable from an intentional DEBUT blank without inspecting the payload directly. That cost real debugging time this week. It'll recur every week a Monday qualifier or last-minute alternate enters the field.

## What to add

One function in `engine/enrich_cards.py`, called once from `main()` right after `trending_data` is loaded (current line ~540, right after `trending_data  = load_trending(input_dir / "pga_field_trending_table.csv")`).

```python
def check_field_completeness(field_names: list[str], trending_data: dict, lookup: dict) -> list[str]:
    """Return canonical-field players (by pga_field.csv) with no row in
    pga_field_trending_table.csv, using the same exact+fuzzy resolve()
    logic the rest of the pipeline uses — not a raw name diff, so this
    doesn't false-flag players the fuzzy matcher would have caught anyway.
    """
    missing = []
    for name in field_names:
        if resolve(name, trending_data, lookup, threshold=0.85) is None:
            missing.append(name)
    return missing
```

Call site, immediately after the existing `trending_data` load line:

```python
    trending_data  = load_trending(input_dir  / "pga_field_trending_table.csv")

    _missing_trend = check_field_completeness(field_names, trending_data, build_lookup(trending_data))
    if _missing_trend:
        print(f"[enrich_cards] WARNING — {len(_missing_trend)} field player(s) missing from "
              f"pga_field_trending_table.csv (likely late field additions; Form/l5 data will "
              f"render blank, this is expected): {', '.join(_missing_trend)}", file=sys.stderr)
```

No new field in the output payload. No change to scoring, tiers, or probabilities. Purely a stderr warning at ingestion time — the same signal `/verify-board` surfaces after the fact, but available before you ever open a browser.

## Verification

```bash
python engine/enrich_cards.py
```

Expected: the existing output is unchanged (player count, all scores identical), plus one new stderr line naming Lindheim, Nicholas and Campbell, Thomas explicitly if this week's data hasn't changed. Confirm no other player names appear that weren't already known blanks.

## Explicit non-goals

- Does not attempt to backfill or impute `l5_array` for these players — no data exists to backfill from; that's a DataGolf coverage limitation, not something this pipeline can fix.
- Does not block the pipeline or change exit code — this is `main()` continuing normally, matching the "log it, don't gate on it" rule already stated in the Playwright verification-gate addendum.
- Does not touch `dg_api_harvester.py` or the DataGolf pull schedule itself. If this becomes a recurring multi-player problem, the real fix is re-pulling `pga_field_trending_table.csv` closer to tee times (a scheduling change, separate decision, separate approval).
