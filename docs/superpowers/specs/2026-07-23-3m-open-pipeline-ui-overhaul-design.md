# 3M Open Pipeline & UI Overhaul — Design Spec
**Date:** 2026-07-23  
**Event:** 2026 3M Open · TPC Twin Cities  
**Status:** Approved — implementing immediately (live event)

---

## Scope

Two-phase extension of the existing VenueDNA architecture. No architectural fragments.

- **Phase 1:** Expand `engine/enrich_cards.py` from 240 → ~600 lines (monolithic, Approach A)
- **Phase 2:** Five surgical injections into `deploy/app.js` + CSS additions + one HTML column

---

## Phase 1 — Data Pipeline (enrich_cards.py)

### Input files
All from `events/2026_3m_open/input/`:
| File | Purpose |
|---|---|
| `pga_field.csv` | Canonical field list (primary key) |
| `pga_sg_query_allcourses_l{6,12,24}.csv` | Base SG horizons |
| `pga_sg_query_3Mopen_similar_l{6,12,24}.csv` | Sim-course SG horizons |
| `app_skill_l12_sg.csv` | Approach SG by distance band |
| `app_skill_l12_prox.csv` | Proximity (ft) by distance band |
| `dg_performance_2026.csv` | putt_true, arg_true, app_true, ott_true |
| `dg_decomposition.csv` | driving_acc_adj, driving_dist_adj, std_dev |
| `tpc_twin_cities_CH.csv` | ch_adjustment, experience_adjustment |
| `pga_field_trending_table.csv` | true_sg_l20, l5_starts |
| `dg_course_table.csv`, `app_skill_l12_gh/great/bad.csv` | Loaded but supplementary |

### Name matching
1. Exact match after `normalize_name()` (lowercase, strip punctuation)
2. Fallback to `difflib.SequenceMatcher(None, a, b).ratio() > 0.85`
3. Short-name collision guard: exact pass resolves "Tom Kim" / "S.H. Kim" before fuzzy fires

### DEBUT treatment
- Players in field with no sim-course SG data → `data_depth = "DEBUT"`
- Impute missing stats to `0.0` raw (z-scores to field mean = 50)
- **Exception:** `trait_course_history` DEBUT haircut = `−0.25` (venue profile §12)

### 10 traits
| Trait key | Formula | Source |
|---|---|---|
| `trait_approach` | `0.10×sg_50_100 + 0.20×sg_100_150 + 0.40×sg_150_200 + 0.30×sg_200plus` | `app_skill_l12_sg` |
| `trait_long_iron` | `0.65×sg_150_200 + 0.35×z(prox_150_200)` | `app_skill_l12_sg` + `app_skill_l12_prox` |
| `trait_total_driving` | `ott_true` | `dg_performance_2026` |
| `trait_driving_accuracy` | `driving_acc_adj` | `dg_decomposition` |
| `trait_driving_distance` | `driving_dist_adj` | `dg_decomposition` |
| `trait_par5_scoring` | `0.55×ott_true + 0.45×app_true` | derived |
| `trait_putting` | `putt_true` | `dg_performance_2026` |
| `trait_course_history` | `ch_adjustment` (DEBUT: `−0.25`) | `tpc_twin_cities_CH` |
| `trait_closing_composure` | `1 / (std_dev + 0.1)` | `dg_decomposition` |
| `trait_recent_form` | `true_sg_l20` | `pga_field_trending_table` |

### Venue weight application
Combined latent = existing dual-vector `sg_sim_comp` PLUS:
```
+0.40 × trait_approach
+0.25 × trait_long_iron
+0.20 × trait_total_driving
+0.10 × trait_course_history
+0.05 × trait_recent_form
```

### Anti-pattern gates (multiplicative, applied before z-scale)
- **Inaccurate Bomber:** `driving_dist_adj > 0.15 AND driving_acc_adj < −0.05` → `×0.92`
- **Short-game Reliant:** `app_true < 0.20 AND (putt_true + arg_true) > 1.0` → `×0.90`

### Z-score + softmax (unchanged)
- Z-score: mean=50, std=15, clamp [0,100]
- Temperatures: Win=3.5, T5=5.0, T10=7.0, T20=10.0
- Monotonicity enforced: `cut > top20 > top10 > top5 > win`
- `make_cut_prob = min(98, max(20, top20 × 1.25 + 10))`

### Sparkline parsing
- Source: `l5_starts` column in `pga_field_trending_table.csv`
- Split by `_`, grab substring after final `-`, strip `T`
- Map `CUT/WD/DQ` → `80`; cast remainder to `int`
- Output: `l5_array: [int, ...]` (5 entries, or fewer if < 5 starts)

### Narrative thresholds
**strength_tags:**
- `trait_approach > 0.5` → `"Elite Iron Play (+X.X)"`
- `delta_fit > 0.15` → `"Strong Venue Fit (+X.X)"`
- `ott_true > 0.6` → `"Controlled Power"`
- `ch_adjustment > 0.04` → `"Proven Course Pedigree"`
- `true_sg_l20 > 1.5` → `"Red-Hot Form"`

**weakness_tags:**
- `trait_approach < 0.0` → `"Approach Deficit"`
- inaccurate-bomber gate triggered → `"Accuracy Risk"`
- `data_depth == DEBUT` → `"Venue Debut"`
- `trait_long_iron < 0.0` → `"Long-Iron Gap"`

**Fallback rule:** If both arrays empty → strength_tags = `["Field-Average Profile"]`, weakness_tags = `["No Clear Edge"]`.

### Ceiling/floor
- `vts_floor = max(0, vts_final − std_dev_scaled)` where `std_dev_scaled = std_dev × 5`
- `vts_ceil  = min(100, vts_final + std_dev_scaled)`
- Both included in payload per player

### Output schema (player record — key additions)
All existing fields preserved (`rank`, `player`, `tier`, `vts_final`, `neutralSkillIndex`, etc.).  
New fields: `win_prob`, `top_5_prob`, `top_10_prob`, `top_20_prob`, `make_cut_prob`, `miss_cut_prob` (snake_case aliases), `l5_array`, `strength_tags`, `weakness_tags`, `headline`, `win_case`, `std_dev`, `vts_floor`, `vts_ceil`, `trait_scores` (array of `{label, weight, score}`), `anti_pattern_flags`, `prepenalty_vts`.

### Output path
`events/2026_3m_open/deploy/data/2026_3m_open_event_payload.json`  
Also mirrored to `events/2026_3m_open/output/2026_3m_open_event_payload.json`

---

## Phase 2 — UI Integration (app.js + styles.css + HTML)

### Change 1 — Fetch URL (app.js line 133)
`board_export.json` → `2026_3m_open_event_payload.json`

### Change 2 — trait_scores fallback (app.js line 1161)
`br.trait_scores || []` → `br.trait_scores || p.trait_scores || []`

### Change 3 — Sparkline column (app.js lines 436–466 + HTML)
- `2026_3m_open_board.html`: add 11th `<th>Form</th>` (no sort)
- Row template: add `<td><canvas id="sp-${p.rank}" width="60" height="22"></canvas></td>`
- Post-render loop: paint sparklines after `tbody.innerHTML = ...`
- New `renderSparkline(canvas, arr)`: 5-point polyline, y = `2 + ((val-1)/79)×18`, green/red/neutral stroke by trend, red dot for val=80

### Change 4 — Modal: trait badges (app.js inside §2 ~line 1246)
Extend §2 with `p.strength_tags` / `p.weakness_tags` flex row.

### Change 5 — Modal: radial dials + ceiling/floor bar (app.js inside §1)
- 4 canvas dials injected after latent-row; painted via `requestAnimationFrame → drawProbDials()`
- CF bar injected after dials using `p.vts_floor`, `p.vts_ceil`, `p.vts_final`
- Arc clamped to `Math.min(val, maxPct)` to prevent overdraw
- Fill/left on CF bar clamped to `[0, 100]%`

### Change 6 — `buildWinCase` win_case fallback (app.js line 1052)
If `!hasAny` and `p.win_case` exists → return formatted scouting report block.

### CSS additions (styles.css)
`.badge-strength`, `.badge-weakness`, `.dial-row`, `.cf-bar-wrap`, `.cf-bar-lbl`, `.cf-bar-track`, `.cf-bar-fill`, `.cf-bar-pin`, `.cf-bar-ticks`

---

## Verification

```bash
python engine/enrich_cards.py
python -c "import json; d=json.load(open('events/2026_3m_open/deploy/data/2026_3m_open_event_payload.json')); print('Players:', len(d['players']))"
python -c "import json; d=json.load(open('events/2026_3m_open/deploy/data/2026_3m_open_event_payload.json')); assert all(p['top_10_prob'] >= p['top_5_prob'] for p in d['players']), 'Monotonicity fail'"
python -m http.server 8000 --directory events/2026_3m_open/deploy
```

**Required before manual Netlify deploy (added 2026-07-23):** the checks above validate the JSON payload only — they do not confirm anything actually renders. Run the Playwright rendering gate before deploying:

```
/verify-board 2026_3m_open
```

This was added after the Form-column sparkline shipped blank to production despite passing every check above — the payload was correct, the canvas paint call wasn't verified. `/verify-board` checks canvas pixel data, modal dials, badges, and the Analyst Mode toggle's actual view change, not just JSON shape. Do not deploy on a FAIL. A DATA ISSUE result (e.g. a late field addition with no trending-table row yet) is not a deploy blocker — log it, don't gate on it. Full gate definition: `docs/superpowers/specs/2026-07-23-playwright-verification-gate.md`.
