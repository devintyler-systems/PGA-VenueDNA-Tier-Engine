# PGA VenueDNA Tier Engine

A repeatable tournament analysis system that builds pre-tournament player rankings (VTS) and post-round trait audit layers for PGA Tour events. The output is a static dashboard — no server required.

---

## Project Purpose

VenueDNA scores each player's fit for a specific PGA Tour venue using 10 weighted trait dimensions (approach wedge accuracy, putting conversion, scrambling, etc.). The engine:

1. Builds a pre-tournament field model from historical SG data and venue fit profiles
2. Exposes the model as an interactive static dashboard
3. After each round, ingests official round results and produces a trait audit layer (how well did the model's trait predictions hold up?)
4. Accumulates round-over-round signal data so the model's quality improves across the event week

---

## Folder Structure

```
C:\PGA_VenueDNA\
├── events/
│   └── 2026_TravelersChampionship/
│       ├── input/          Raw data sources (historical CSVs, DataGolf exports)
│       ├── output/         Pipeline outputs and canonical artifacts
│       │   └── round1/     Round-specific input CSVs (place here before each round build)
│       ├── engine/         Python build scripts
│       └── deploy/         Static app — serve this folder over HTTP
│           ├── index.html
│           ├── app.js
│           ├── styles.css
│           └── data/       JSON files loaded by app.js at runtime
├── events/2026_USOPEN/     Prior event (same structure)
├── library/
│   ├── engine/             Methodology documentation and schema specs
│   └── venues/             Venue intelligence notes
└── PGA Tour Intelligence System - Claude/  Legacy pre-VenueDNA reference files
```

### Source vs Output vs Deploy data

| Location | What it is |
|---|---|
| `input/` | Raw downloaded files — historical stats, course data, DataGolf exports |
| `output/` | Canonical pipeline artifacts — event payload, trait matrix, round analysis JSON |
| `deploy/data/` | Files served to the browser — copied from `output/` as part of deploy step |

The deploy folder is a self-contained static app. Copy or symlink `output/*.json` to `deploy/data/` after each build.

---

## Event Folder Organization

Each event has a consistent structure:

```
events/{YEAR}_{EventSlug}/
├── input/
│   ├── True_SG_Query_L12Months.csv         SG data from DataGolf / PGAT (last 12 months)
│   ├── {event}_course_table.csv            Venue hole-by-hole profile
│   ├── Player_Approach_Skill.csv           Approach skill breakdown
│   └── dg_performance_2026.csv             DataGolf current-season data
├── output/
│   ├── {slug}_event_payload.json           Full field model (primary source for dashboard)
│   ├── {slug}_trait_form_matrix.csv        Per-player trait percentile scores
│   ├── {slug}_player_briefs.json           Rich player narrative cards
│   ├── {slug}_qa_report.json               Trait imputation audit
│   ├── {slug}_vts_full.csv                 Full VTS scores (denormalized)
│   ├── {slug}_cumulative_learning.json     Round-over-round signal accumulation
│   ├── {slug}_r1_analysis.json             Round 1 trait audit
│   ├── {slug}_r2_analysis.json             Round 2 trait audit (after R2)
│   └── round1/                             Round 1 input CSVs (place here before R1 build)
│       ├── round1_leaderboard.csv
│       ├── round1_player_strokes_gained.csv
│       ├── round1_course_stats.csv
│       └── round1_course_insights.csv      (optional — DataGolf proxy enrichment)
├── engine/
│   ├── venuedna_pipeline_{slug}.py         Pre-tournament model builder (event-specific)
│   ├── build_r1_analysis.py                Round 1 builder (legacy, Travelers only)
│   ├── build_round_analysis.py             Generalized round builder (R1-R4)
│   ├── round_helpers.py                    Shared utility functions
│   ├── qa_trait_validation.py              QA and trait imputation validator
│   └── enrich_cards.py                     Player brief enrichment
└── deploy/
    ├── index.html
    ├── app.js
    ├── styles.css
    └── data/                               Served at runtime — mirror of output/ key files
        ├── event_payload.json
        ├── player_briefs.json
        ├── qa_report.json
        ├── vts_full.csv
        ├── r1_analysis.json
        ├── cumulative_learning.json
        └── links.json
```

---

## Tournament Learning

The **Tournament Learning** tab in the dashboard is powered by `rN_analysis.json` files:

- `r1_analysis.json` → Round 1 tab (LIVE badge appears automatically)
- `r2_analysis.json` → Round 2 tab
- `r3_analysis.json` → Round 3 tab
- `r4_analysis.json` → Final tab

Each file contains:
- **trait_audit** — did the pre-tournament model's trait predictions hold? (validated / mixed / neutral / weak)
- **source_confidence** — how reliable is the evidence? (direct / proxy-confirmed / weak-proxy / not-testable)
- **enrichment** — optional DataGolf proxy layer that can upgrade weak signals
- **live_lean_notes** — data-driven interpretation: which traits to lean on next round, who to watch
- **slippage_risk** — top-20 players with fragile stat profiles (putting spike, no approach backing)
- **weekend_risers** — players beating model rank with course-fit-backed stats

The dashboard app.js auto-detects which round files exist and shows LIVE badges on those tabs. Rounds without data show stub placeholder cards.

**cumulative_learning.json** accumulates signal history across rounds, tracking whether each trait's signal stays consistent from R1 → R2 → R3 → Final.

---

## How to Rebuild the JSON Files

### Serving the dashboard locally

```bash
cd events/2026_TravelersChampionship/deploy
python -m http.server 8080
# Open http://localhost:8080
```

The app **must** be served over HTTP, not opened as a file:// URL — browsers block fetch() from file:// origins.

### Pre-tournament build

Run once before the event starts. Requires input files in `input/`.

```bash
cd events/2026_TravelersChampionship/engine
python venuedna_pipeline_travelers2026.py   # builds event_payload, trait matrix, links
python qa_trait_validation.py              # validates trait imputation; produces qa_report.json
python enrich_cards.py                     # enriches player brief cards
```

Then copy outputs to deploy/data/:
```
copy output\2026_travelers_championship_event_payload.json    deploy\data\event_payload.json
copy output\2026_travelers_championship_player_briefs.json    deploy\data\player_briefs.json
copy output\2026_travelers_championship_qa_report.json        deploy\data\qa_report.json
copy output\2026_travelers_championship_vts_full.csv          deploy\data\vts_full.csv
```

### Round 1 analysis build (Travelers — legacy script)

The Travelers R1 reads from `output/round1 player & course stats/` (historical naming with spaces).

```bash
cd events/2026_TravelersChampionship/engine
python build_r1_analysis.py
# → output/2026_travelers_championship_r1_analysis.json
# → deploy/data/r1_analysis.json  (auto-written)
# → deploy/data/cumulative_learning.json  (created)
```

### Round 2 / Round 3 / Final build (generalized)

For all subsequent rounds, use `build_round_analysis.py`. Place downloaded round CSVs in `output/round{N}/` first.

**Required files in `output/round2/`:**
```
round2_leaderboard.csv
round2_player_strokes_gained.csv
```

**Optional files in `output/round2/`:**
```
round2_course_stats.csv
round2_course_insights.csv    (DataGolf proxy — upgrades weak trait signals)
```

```bash
cd events/2026_TravelersChampionship/engine
python build_round_analysis.py --round 2
python build_round_analysis.py --round 3
python build_round_analysis.py --round 4   # Final round
```

The script validates all required files before running, warns on missing optionals, and degrades gracefully (skips hole analysis or enrichment layer if files are absent).

Outputs auto-write to both `output/` and `deploy/data/`. No manual copy needed.

---

## Pre-Tournament Build — Required Input Files

| File | Source |
|---|---|
| `True_SG_Query_L12Months.csv` | DataGolf / PGAT export |
| `dg_performance_2026.csv` | DataGolf current season |
| `{event}_course_table.csv` | Venue profile CSV |
| `Player_Approach_Skill.csv` | DataGolf approach breakdown |
| Prior year results CSV | PGA Tour / DataGolf archive |

---

## Post-Round Build — Required Input Files (each round)

| File | Source | Required |
|---|---|---|
| `round{N}_leaderboard.csv` | PGA Tour scorecard export | Yes |
| `round{N}_player_strokes_gained.csv` | PGA Tour official SG stats | Yes |
| `round{N}_course_stats.csv` | PGA Tour hole-by-hole stats | Optional |
| `round{N}_course_insights.csv` | DataGolf round proxy stats | Optional |

**Leaderboard CSV columns:** `PLAYER`, `POS`, `TOTAL`, `Total Strokes`

**SG CSV columns:** `Player`, `SG-Off the Tee`, `SG-Approach to Green`, `SG- Around the Green`, `SG-Putting`, `SG-Total`

---

## What Is and Isn't Automated

| Step | Automated | Manual |
|---|---|---|
| Field scoring and VTS build | `venuedna_pipeline_*.py` | Requires placing input CSVs |
| QA validation | `qa_trait_validation.py` | — |
| Round analysis build | `build_round_analysis.py --round N` | Place round CSVs in `output/roundN/` first |
| Cumulative learning update | Automatic within round build | — |
| deploy/data refresh (round JSONs) | Auto-written by build script | — |
| deploy/data refresh (pre-tournament) | Manual copy after pipeline build | — |
| Dashboard update | Automatic on next page load | — |

---

## Adding a New Event

1. Create `events/{YEAR}_{EventSlug}/` with the standard subfolder structure
2. Copy and adapt the pipeline script, updating venue trait weights
3. Copy `build_round_analysis.py` and `round_helpers.py` into the new `engine/` directory
4. Update `EVENT_SLUG`, `COURSE_NAME`, `PAR`, `TRAIT_COLS`, `VENUE_WEIGHTS` at the top of both scripts
5. Copy the `deploy/` folder (HTML/CSS/JS) and update the venue context card in `app.js`

---

## Schema Reference

See `library/engine/ROUND_ANALYSIS_SCHEMA.md` for the complete field-by-field definition of the `rN_analysis.json` and `cumulative_learning.json` structures.

---

## Round Operator Runbook (R2 / R3 / Final)

Use this checklist each time new round files arrive. The workflow is identical for R2, R3, and Final (R4).

### Step 1 — Place files

Create the round folder and drop in the downloaded CSVs:

```
events/2026_TravelersChampionship/output/round2/
  round2_leaderboard.csv               ← required
  round2_player_strokes_gained.csv     ← required
  round2_course_stats.csv              ← optional (hole-by-hole stats)
  round2_course_insights.csv           ← optional (DataGolf proxy enrichment)
```

Rename files to match the exact naming convention above (`round{N}_*.csv`). The script will error fast if required files are missing.

**Leaderboard CSV must have columns:** `PLAYER`, `POS`, `TOTAL`, `Total Strokes`
**SG CSV must have columns:** `Player`, `SG-Off the Tee`, `SG-Approach to Green`, `SG- Around the Green`, `SG-Putting`, `SG-Total`

### Step 2 — Validate (dry run)

```bash
cd events/2026_TravelersChampionship/engine
python build_round_analysis.py --round 2 --check
```

Expected output if all files are ready:
```
=== CHECK MODE — Round 2 manifest ===
  [OK]  .../output/round2/round2_leaderboard.csv
  [OK]  .../output/round2/round2_player_strokes_gained.csv
  [OK]  .../output/2026_travelers_championship_trait_form_matrix.csv
  [OK]  .../deploy/data/event_payload.json
  [--]  .../output/round2/round2_course_stats.csv  (optional — skipped)
  [--]  .../output/round2/round2_course_insights.csv  (optional — skipped)

All required files present. Run without --check to build.
```

### Step 3 — Build

```bash
python build_round_analysis.py --round 2
```

**Signs the build succeeded:**
- `Matched N/N players to pre-tournament model` — match rate should be >85%; any `[unmatched]` lines list player names with their current positions
- `[warn] Duplicate leaderboard rows skipped` — if this appears, your leaderboard CSV has duplicate rows (harmless, deduped automatically)
- Trait audit prints 10 lines with signal values (`validated` / `mixed` / `neutral` / `weak` / `not_testable`)
- Final lines: `Wrote: ...deploy/data/r2_analysis.json` and `Wrote: ...deploy/data/cumulative_learning.json`

**Output files generated:**
```
output/2026_travelers_championship_r2_analysis.json   ← canonical archive
output/2026_travelers_championship_cumulative_learning.json
deploy/data/r2_analysis.json                          ← auto-deployed to dashboard
deploy/data/cumulative_learning.json                  ← updated
```

### Step 4 — Verify in dashboard

1. Reload `http://localhost:8080` (or restart `python -m http.server 8080` from `deploy/`)
2. Click **Tournament Learning** tab
3. Round 2 tab should show a green **LIVE** badge — click it
4. Check: leaderboard snapshot shows current standings, trait audit shows signal values, Live Lean section shows next-round guidance
5. Diagnostics panel (bottom of page) shows `build_timestamp` and source files used

### Repeat for R3 and Final

Same process — substitute `round3` or `round4` everywhere. Run `--round 4` for Final; the script auto-sets `is_final: true` and the app shows "FINAL ROUND RECAP" instead of next-round lean notes.

```bash
python build_round_analysis.py --round 3
python build_round_analysis.py --round 4   # Final
```
