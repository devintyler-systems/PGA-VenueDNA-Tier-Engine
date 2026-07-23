# Design: 3M Open Dual-Vector Pre-Tournament Pipeline

**Date:** 2026-07-22
**Event:** 2026 3M Open — TPC Twin Cities
**Approach:** B (self-contained, no latent_model.py imports)

---

## Target Files

| File | Status | Role |
|---|---|---|
| `engine/enrich_cards.py` | New | Python compute layer — reads SG CSVs, writes board_export.json |
| `events/2026_3m_open/deploy/data/board_export.json` | New (created by script) | Pre-tournament player payload |
| `events/2026_3m_open/deploy/app.js` | Modify | Purge Open Championship scaffolding, wire dual-vector traits |
| `events/2026_3m_open/deploy/index.html` | Modify | Grid column headers updated for SG Base / SG Sim / Δ Fit |

---

## Architecture

```
events/2026_3m_open/input/
  pga_sg_query.csv              ← All Courses 6m
  pga_sg_query (1).csv          ← All Courses 12m
  pga_sg_query (2).csv          ← All Courses 24m
  similar_courses_sg_6m.csv     ← Top 20 Similar Courses 6m
  similar_courses_sg_12m.csv    ← Top 20 Similar Courses 12m
  similar_courses_sg_24m.csv    ← Top 20 Similar Courses 24m
        │
        ▼
engine/enrich_cards.py  (--event 2026_3m_open)
        │
        ▼
events/2026_3m_open/deploy/data/board_export.json
        │
        ▼
events/2026_3m_open/deploy/app.js  (fetch at runtime)
```

`build_round_analysis.py` and `build_r1_analysis.py` are **not touched** — those
handle post-round passes once the tournament starts.

---

## Part 1: `engine/enrich_cards.py`

### CLI

```
python engine/enrich_cards.py --event 2026_3m_open
```

Default `--event` is `2026_3m_open`. Resolves all paths from `events/{event_slug}/`.

### Input Files

Column schema (same for all 6 CSVs): `player_name`, `rounds_played`, `total_mean`
(full DataGolf SG distribution export; only these three columns are consumed).

### Function Layout

All functions are module-level (no classes):

| Function | Purpose |
|---|---|
| `normalize_name(s)` | Strips quotes and whitespace; enforces `"Last, First"` |
| `load_sg(path)` | CSV → `dict[norm_name → {rounds: int, total_mean: float}]`. Missing file → empty dict. |
| `debut_row()` | Returns `{rounds: 0, total_mean: 0.0}` for join-miss players |
| `compute_horizon(base, sim)` | Per-horizon: W, SG_Sim_Reg, Delta_Fit |
| `blend_composites(h6, h12, h24)` | Applies decay weights → (SG_Base_Comp, Delta_Fit_Comp) |
| `z_score_scale(values, mean=50, std=15)` | List of floats → list of [0,100] floats |
| `tempered_softmax(scores, T)` | Field-level softmax with temperature → list of probabilities summing to 1.0 |
| `enforce_monotonicity(p)` | Mutates player dict: Top20 ≥ Top10 ≥ Top5 ≥ Win (in-place clamp cascade) |
| `assign_tier(rank)` | T1:1–5, T2:6–12, T3:13–25, T4:26–40, T5:41+ |
| `make_cut_prob(top20_pct)` | `min(98.0, max(20.0, top20_pct * 1.25 + 10.0))` |
| `main()` | Orchestrates: load → compute → scale → sort → write |

### Dual-Vector Math

**Step 1 — Per-horizon computation:**
```
W_h = min(1.0, N_rounds_h / 20.0)
SG_Sim_Reg_h = (W_h * SG_Sim_h) + ((1 - W_h) * SG_Base_h)
Delta_Fit_h  = SG_Sim_Reg_h - SG_Base_h
```

**Step 2 — Composites with decoupled decay:**
```
SG_Base_Comp    = (0.20 * SG_Base_6m) + (0.30 * SG_Base_12m) + (0.50 * SG_Base_24m)
Delta_Fit_Comp  = (0.50 * Delta_Fit_6m) + (0.30 * Delta_Fit_12m) + (0.20 * Delta_Fit_24m)
Delta_Fit_Comp  = clamp(Delta_Fit_Comp, -0.50, +0.50)
SG_Sim_Comp     = SG_Base_Comp + Delta_Fit_Comp
```

**Step 3 — Latent driver and scaling:**
```
VTS_Raw = SG_Base_Comp + Delta_Fit_Comp   (same as SG_Sim_Comp)

neutralSkillIndex = z_score_scale(all SG_Base_Comp values, mean=50, std=15)
vts_final         = z_score_scale(all VTS_Raw values, mean=50, std=15)
```

**Step 4 — Probability vectors (tempered softmax, field-level):**

| Output | Temperature |
|---|---|
| winPct | T = 3.5 |
| top5Pct | T = 5.0 |
| top10Pct | T = 7.0 |
| top20Pct | T = 10.0 |

For each temperature T, apply softmax over VTS_Raw scores across the full field:
```
raw_i   = exp(VTS_Raw_i / T)
share_i = raw_i / sum(raw_j)           # each player's share of 1.0
prob_i  = share_i * N_positions * 100  # expressed as %
prob_i  = min(prob_i, 99.9)            # hard cap
```
Where N_positions = 1 (Win), 5 (Top5), 10 (Top10), 20 (Top20).
This gives each player an independent percentage; the field sums to ~N_positions × 100%.

Monotonicity enforced in-place: `Top20 ≥ Top10 ≥ Top5 ≥ Win` by clamping up from Win.

**Step 5 — Derived fields:**
```
makeCutPct  = min(98.0, max(20.0, top20Pct * 1.25 + 10.0))
missCutPct  = 100.0 - makeCutPct
```

### Player Object Schema (board_export.json)

```json
{
  "rank": 1,
  "player": "Scottie Scheffler",
  "tier": "T1",
  "vts_final": 87.4,
  "neutralSkillIndex": 100.0,
  "sg_base_composite": 2.824,
  "sg_similar_composite": 2.910,
  "delta_fit": 0.086,
  "data_depth": "FULL",
  "winPct": 18.5,
  "top5Pct": 42.1,
  "top10Pct": 58.3,
  "top20Pct": 74.6,
  "makeCutPct": 92.0,
  "missCutPct": 8.0
}
```

`data_depth`: `"FULL"` when all 6 horizon CSVs had a match; `"DEBUT"` when no match
on any similar-course CSV (N_rounds = 0 across all horizons).

### Output

Creates `events/{event_slug}/deploy/data/` if absent, then writes `board_export.json`
with schema:
```json
{
  "schemaVersion": "3m-dual-vector-v1.0",
  "generatedAt": "<ISO timestamp>",
  "event": "2026 3M Open",
  "venue": "TPC Twin Cities",
  "players": [ ... ]
}
```

### Verification

```
python engine/enrich_cards.py --event 2026_3m_open
```

Script exits 0 on success and prints a summary line:
`[enrich_cards] Written N players → events/2026_3m_open/deploy/data/board_export.json`

Exits 1 with a descriptive message if any required input CSV is missing.

---

## Part 2: `deploy/app.js` Cleanup

### Complete Purge

| Symbol / Block | Action |
|---|---|
| `FM`, `RISK_KEYS`, `RISK_COLS`, `RULE_EXP` | Delete entire objects |
| `buildFlags()` | Replace body with `return [];` |
| `renderRisk()`, `fmtRisk()`, `toggleRisk()` | Delete |
| `S.waveByPlayer`, `S.weather.wave_delta`, `S.weather.tide` | Remove from state; `S.weather` → `{ speed: 0, direction: 'N/A' }` |
| All `birkdaleTag` references | Delete (spotlight badges, row `data-tag`, altPlayer scaffold) |
| Filter cases `'history'`, `'debut'`, `'zerolinks'` | Delete from `applyVisibility` switch |
| `birkdale_risk_register`, `birkdale_history_note`, `links_signal_note` | Delete all references |
| `"open_2026_board_export.json"` fetch fallback | Replace with `"board_export.json"` |
| `"Royal Birkdale VTS"` | → `"TPC Twin Cities VTS"` |
| Wave/tidal block in modal weather section | Remove (keep basic wind speed + direction only) |
| `br.vhn_rounds` / `"Birkdale Rds"` in §9 | Remove |

### Grid Column Changes

**Old:** Rank · Player · VTS · NSI · VFS · VHD · Penalties · Win% · Top10% · Cut% · Flags

**New:** Rank · Player · VTS · NSI · SG Base · SG Sim · Δ Fit · Win% · Top10% · Cut%

- `SG Base` → `p.sg_base_composite`, formatted `+2.824` (3 decimals, explicit sign)
- `SG Sim` → `p.sg_similar_composite`, formatted `+2.910`
- `Δ Fit` → `p.delta_fit`, formatted `+0.086`, colored green if ≥ 0, red if < 0

`updateSortArrows` key map updated to match new column order.

### Modal §10 — System Footprint Bars

Old: NSI bar / VFS bar / VHD diverging bar / Penalties bar

New:
- **NSI bar** → `p.neutralSkillIndex` (0–100 scale, navy)
- **SG Sim bar** → `p.vts_final` (0–100 scale; this IS the z-scored sg_similar_composite, green)
- **Δ Fit diverging bar** → centered at 0, fills right (green) for positive delta, left (red) for negative; label shows raw `+0.086`

### Modal — "Similar Course Profile" Section (replaces "Links & Venue Evidence")

```
┌─────────────────────────────────────────────┐
│  SIMILAR COURSE PROFILE                      │
│  SG Base    +2.824   baseline skill anchor   │
│  SG Sim     +2.910   similar-course ability  │
│  Δ Fit      +0.086   TPC Twin Cities uplift  │
└─────────────────────────────────────────────┘
```

Rendered as a three-row metric block. Δ Fit row colored green/red by sign.

### FILTER_FIELDS Updates

Remove: `ott_accuracy`, `ott_positional`, `app_overall` (links-weighted)

Add:
```js
{ key:'pt_delta_fit', label:'Δ Fit',    get:(p) => p.delta_fit },
{ key:'pt_sg_base',   label:'SG Base',  get:(p) => p.sg_base_composite },
{ key:'pt_sg_sim',    label:'SG Sim',   get:(p) => p.sg_similar_composite },
```

### QUICK_PRESETS Updates

Remove: `positional-drivers`, `iron-elites`

Add:
```js
'venue-fits': [{ field:'pt_delta_fit', op:'>=', val:0.080 }],
'high-base':  [{ field:'pt_sg_base',  op:'>=', val:1.500 }],
```

---

## Part 3: `deploy/index.html`

- Update `<th>` headers in `.board-table` to match new column order:
  Rank, Player, VTS, NSI, SG Base, SG Sim, Δ Fit, Win%, Top10%, Cut%
- Remove any `onclick` / chip references to `'history'`, `'debut'`, `'zerolinks'`
- Update page `<title>` and any header text from "The Open Championship" → "3M Open — TPC Twin Cities"
- Remove the `sec-risk` section anchor if it references the Birkdale risk register

---

## Verification Loop

```
python engine/enrich_cards.py --event 2026_3m_open
node --check events/2026_3m_open/deploy/app.js
```

Both must exit 0.
