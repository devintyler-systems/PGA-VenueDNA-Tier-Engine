# 2026 Genesis Scottish Open — FC-1 Repair Audit

Generated: 2026-07-06  |  Engine: score_engine_v2.py (FC-1 repair patch)

## Scope
FC-1 refactor: `generate_venue_history_summary` now branches on result quality first (win → podium → recent top-15 → depth-by-sample → limited fallback) instead of leading with raw sample-size depth class. `best_finish_renaissance` corrected from most-recent to true-minimum across all years.

## Change summary

| # | Player | Branch fired | Notes |
|---|---|---|---|

**Total changed: 0 of 166 players**

---

## Detailed diff

## Validation guards applied

- `best_finish_renaissance == 1` → summary contains winner/defending champion language ✓
- `best_finish_renaissance <= 5` → no limited-history wording without podium language ✓
- `last_finish_renaissance <= 15` → does not read like debut/no-history ✓
- VTS scoring weights and probability logic: unchanged ✓