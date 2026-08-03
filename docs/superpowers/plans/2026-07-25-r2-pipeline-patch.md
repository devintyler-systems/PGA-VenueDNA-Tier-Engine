# Plan: VenueDNA R2 Pipeline Patch — 2026-07-25

## Context
3M Open R2 is complete. The board app.js fetches `data/2026_3m_open_r{N}_analysis.json` but
the pipeline (`build_round_analysis.py`) outputs `r{N}_analysis.json` (no slug prefix). The
3M Open event config is also missing from `_EVENT_CONFIGS`, and a R3 Heat Stress Penalty
needs to be added for afternoon tee-times.

Key facts:
- PAR: 71, TPC Twin Cities
- R3 heat warning: 96°F+ heat index by 12:35 PM CDT → -0.05 SG penalty for tee times ≥ 11:30 AM
- TFM CSV uses `player_name` not `name_key`/`player_display` (must fix lookup)
- round3_tee_times.json (7.2KB) already in deploy/data; r3_teetime column in CSV
- Weights from player_briefs: app_overall=0.40, app_150_200=0.25, ott_accuracy=0.10,
  ott_positional=0.10, sg_putt=0.05, par5_scoring=0.05, recent_form=0.05

## Global Constraints
- DO NOT rename files in deploy/data that app.js fetches (check before renaming)
- Weights must not be hardcoded outside engine config section
- All changes on main branch (no worktree needed for this event-specific work)
- Python script must remain executable: `python engine/build_round_analysis.py --event_slug 2026_3m_open --round 2`

## Tasks

### Task 1 — Fix app.js fetch URLs (deploy/app.js)
The 3M Open app.js uses slug-prefixed filenames for round analysis files, but the pipeline
outputs without slug. Fix by removing the `2026_3m_open_` prefix from these specific fetches:
- Line ~2022: `data/2026_3m_open_r${r}_analysis.json` → `data/r${r}_analysis.json`
- Line ~2023: `data/2026_3m_open_cumulative_learning.json` → `data/cumulative_learning.json`
- Line ~427: `data/2026_3m_open_post_mortem_analysis.json` → `data/post_mortem_analysis.json`
- Line ~154: `data/2026_3m_open_final_analysis.json` → `data/final_analysis.json`

Note: The event_payload, player_briefs, and weather_forecast fetches are correctly
slug-prefixed and those files exist — DO NOT change those.

### Task 2 — Add 3M Open config + R3 heat penalty + TFM lookup fix (engine/build_round_analysis.py)

#### 2a. Add 3M Open entry to _EVENT_CONFIGS (before line 227 `}` that closes the dict)
```python
    "2026_3m_open": {
        "event_name":   "2026 3M Open",
        "course_name":  "TPC Twin Cities",
        "par":          71,
        "event_dir_glob": "events/*3m_open*",
        "course_key":   "tpc_twin_cities",
        "favored_wave": "early_late",
        "trait_cols": {
            "app_150_200":     "VenueDNA_trait_long_iron_150_225",
            "ott_accuracy":    "VenueDNA_trait_driving_accuracy",
            "ott_positional":  "VenueDNA_trait_total_driving",
            "app_overall":     "VenueDNA_trait_approach",
            "sg_putt":         "VenueDNA_trait_easy_green_putting",
            "par5_scoring":    "VenueDNA_trait_par5_scoring",
            "recent_form":     "VenueDNA_trait_recent_form_context",
        },
        "venue_weights": {
            "app_150_200": 0.25, "ott_accuracy": 0.10, "ott_positional": 0.10,
            "app_overall": 0.40, "sg_putt": 0.05, "par5_scoring": 0.05, "recent_form": 0.05,
        },
        "sg_proxy": {
            "app_150_200": "sg_app", "ott_accuracy": "sg_ott", "ott_positional": "sg_ott",
            "app_overall": "sg_app", "sg_putt": "sg_putt",
            "par5_scoring": "sg_app", "recent_form": "sg_tot",
        },
        "ci_trait_map": {
            "app_150_200":   {"primary": "gir",          "direction": "higher_better", "secondary": "fairway_prox"},
            "ott_accuracy":  {"primary": "d_accuracy",   "direction": "higher_better", "secondary": None},
            "ott_positional":{"primary": "d_accuracy",   "direction": "higher_better", "secondary": "d_distance"},
            "app_overall":   {"primary": "fairway_prox", "direction": "lower_better",  "secondary": "gir"},
            "sg_putt":       {"primary": None,           "direction": None,            "secondary": None},
            "par5_scoring":  {"primary": "gir",          "direction": "higher_better", "secondary": "d_distance"},
            "recent_form":   {"primary": None,           "direction": None,            "secondary": None},
        },
    },
```

#### 2b. Fix TFM name lookup (around line 744-754)
Current code uses `name_key` and `player_display` columns. The 3M Open TFM uses `player_name`.
Add fallbacks:
```python
# Before: nk = row.get("name_key", "")
nk = row.get("name_key") or row.get("player_name", "")
# ...
# Before: if "player_display" in row: name_to_nk[...] = nk
display = row.get("player_display") or row.get("player_name") or nk
if display:
    name_to_nk[ascii_fold(display).lower()] = nk
```

#### 2c. Add R3 Heat Stress Penalty (in leaderboard snapshot section, around line 1452)
When ROUND == 2, load round3_tee_times to flag players with afternoon tee times.
Add a helper to parse tee times to minutes-from-midnight.
Add `heat_stress_penalty` and `heat_index_peak` fields to each leaderboard snapshot record.

Pipeline for the penalty:
1. Load `events/{event_slug}/output/round2/round3_tee_times.csv` (already generated by data ingestion)
   - If CSV not found, try `deploy/data/round3_tee_times.json`
2. Build dict: normalized_player_name → r3_teetime string
3. For each `_rec` in `lb_snapshot`:
   - Look up player's r3_teetime
   - Parse time (format: "H:MM AM/PM") to total minutes
   - If minutes >= 690 (11:30 AM): `_rec["heat_stress_penalty"] = -0.05; _rec["heat_index_peak"] = 96`
   - Else: `_rec["heat_stress_penalty"] = 0.0`
4. Only apply when `ROUND == 2` (projecting R3)

### Task 3 — Run pipeline and verify
Execute: `python engine/build_round_analysis.py --event_slug 2026_3m_open --round 2`
Verify output files exist:
- `events/2026_3m_open/output/2026_3m_open_r2_analysis.json`
- `events/2026_3m_open/deploy/data/r2_analysis.json`
Check assertions from prompt:
- `vs_proj` is not hardcoded (it's calculated)
- DNS players have 0.0% win probability
- heat_stress_penalty present for afternoon tee times
