# 3M Open Dual-Vector Pre-Tournament Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 3M Open pre-tournament pipeline: a new Python compute script (`engine/enrich_cards.py`) that reads 6 SG CSVs and writes `board_export.json`, plus surgical rewiring of `events/2026_3m_open/deploy/app.js` to consume dual-vector traits and a new board HTML (`3m_open_2026_board.html`) to replace the current redirect.

**Architecture:** Self-contained `enrich_cards.py` (no latent_model.py imports) reads All Courses + Similar Courses SG CSVs, runs sample-weighted Delta_Fit math with decoupled decay, Z-score scales, applies tempered softmax probability vectors, and writes the player payload. The deploy layer (`app.js` + board HTML) is purged of all Open Championship / Royal Birkdale scaffolding and wired to three new dual-vector traits.

**Tech Stack:** Python 3.10+ (stdlib only: csv, json, math, argparse, pathlib), pytest, vanilla JS (ES2020), HTML5 with embedded CSS.

## Global Constraints

- `enrich_cards.py` must import no project modules (no latent_model, no config.py)
- `argparse` lives **inside** `main()` only — keeps pure functions importable by tests
- All SG CSVs have columns `player_name`, `rounds_played`, `total_mean` (only these three consumed)
- Name normalization: strip surrounding `"` or `'`, then `.strip()` → `"Last, First"` format
- Delta_Fit clamped to `[-0.50, +0.50]`; Base weights `[6m:0.20, 12m:0.30, 24m:0.50]`; Delta weights `[6m:0.50, 12m:0.30, 24m:0.20]`
- Z-score: mean=50, std=15, clamp output to [0, 100]
- Tempered softmax temperatures: Win=3.5, Top5=5.0, Top10=7.0, Top20=10.0; cap each prob at 99.9
- Monotonicity: Top20 ≥ Top10 ≥ Top5 ≥ Win (clamp cascade upward from Win)
- `makeCutPct = min(98.0, max(20.0, top20Pct × 1.25 + 10.0))`
- `data_depth`: `"FULL"` if any sim horizon has rounds > 0; `"DEBUT"` if none
- All table/modal SG values formatted to 3 decimals with explicit sign (`sgSign()` already exists)
- `app.js` node syntax check must pass: `node --check events/2026_3m_open/deploy/app.js`
- Output JSON path: `events/2026_3m_open/deploy/data/board_export.json` (directory created by script)

---

### Task 1: `engine/enrich_cards.py` — Dual-Vector Compute Engine

**Files:**
- Create: `engine/enrich_cards.py`
- Create: `tests/test_enrich_cards.py`

**Interfaces:**
- Consumes: 6 CSV files at `events/2026_3m_open/input/` (columns: `player_name`, `rounds_played`, `total_mean`)
- Produces: `events/2026_3m_open/deploy/data/board_export.json` (schema detailed in Step 1)
- Exports (for tests): `normalize_name`, `load_sg`, `debut_row`, `compute_horizon`, `blend_composites`, `z_score_scale`, `tempered_softmax`, `enforce_monotonicity`, `assign_tier`, `make_cut_prob`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_enrich_cards.py`:

```python
"""Tests for engine/enrich_cards.py — pure-function coverage."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from enrich_cards import (
    normalize_name,
    load_sg,
    debut_row,
    compute_horizon,
    blend_composites,
    z_score_scale,
    tempered_softmax,
    enforce_monotonicity,
    assign_tier,
    make_cut_prob,
)


def test_normalize_name_strips_quotes():
    assert normalize_name('"Scheffler, Scottie"') == "Scheffler, Scottie"


def test_normalize_name_strips_whitespace():
    assert normalize_name("  McIlroy, Rory  ") == "McIlroy, Rory"


def test_normalize_name_empty():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_load_sg_reads_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        'player_name,rounds_played,total_mean\n"Scheffler, Scottie",20,2.5\n',
        encoding="utf-8",
    )
    result = load_sg(csv_file)
    assert result == {"Scheffler, Scottie": {"rounds": 20, "total_mean": 2.5}}


def test_load_sg_missing_file(tmp_path):
    result = load_sg(tmp_path / "nonexistent.csv")
    assert result == {}


def test_load_sg_skips_blank_names(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "player_name,rounds_played,total_mean\n,10,1.0\n", encoding="utf-8"
    )
    result = load_sg(csv_file)
    assert result == {}


def test_debut_row():
    assert debut_row() == {"rounds": 0, "total_mean": 0.0}


def test_compute_horizon_full_sample():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 20, "total_mean": 2.5}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(1.0)
    assert h["sg_sim_reg"] == pytest.approx(2.5)
    assert h["delta_fit"] == pytest.approx(0.5)


def test_compute_horizon_no_sim_rounds():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 0, "total_mean": 0.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(0.0)
    # W=0 → sg_sim_reg = base
    assert h["sg_sim_reg"] == pytest.approx(2.0)
    assert h["delta_fit"] == pytest.approx(0.0)


def test_compute_horizon_partial_sample():
    base = {"rounds": 20, "total_mean": 1.0}
    sim = {"rounds": 10, "total_mean": 3.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(0.5)
    assert h["sg_sim_reg"] == pytest.approx(0.5 * 3.0 + 0.5 * 1.0)  # 2.0
    assert h["delta_fit"] == pytest.approx(2.0 - 1.0)  # 1.0


def test_compute_horizon_caps_w_at_one():
    base = {"rounds": 20, "total_mean": 0.0}
    sim = {"rounds": 40, "total_mean": 1.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(1.0)


def test_blend_composites_weights():
    b6, b12, b24 = 1.0, 2.0, 3.0
    d6, d12, d24 = 0.1, 0.2, 0.3
    sg_base, delta = blend_composites(b6, b12, b24, d6, d12, d24)
    expected_base = 0.20 * 1.0 + 0.30 * 2.0 + 0.50 * 3.0
    expected_delta = 0.50 * 0.1 + 0.30 * 0.2 + 0.20 * 0.3
    assert sg_base == pytest.approx(expected_base)
    assert delta == pytest.approx(expected_delta)


def test_blend_composites_clamps_positive_delta():
    # Extreme positive delta → clamped to +0.50
    sg_base, delta = blend_composites(0, 0, 0, 1.0, 1.0, 1.0)
    assert delta == pytest.approx(0.50)


def test_blend_composites_clamps_negative_delta():
    # Extreme negative delta → clamped to -0.50
    sg_base, delta = blend_composites(0, 0, 0, -1.0, -1.0, -1.0)
    assert delta == pytest.approx(-0.50)


def test_z_score_scale_mean_and_spread():
    values = [0.0, 1.0, 2.0]
    scaled = z_score_scale(values)
    assert len(scaled) == 3
    # Middle value (mean of field) should be ~50
    assert scaled[1] == pytest.approx(50.0, abs=0.1)
    assert all(0.0 <= v <= 100.0 for v in scaled)


def test_z_score_scale_single_value():
    # Single value: sd=1.0 fallback → returns mean=50.0
    scaled = z_score_scale([5.0])
    assert scaled == [50.0]


def test_z_score_scale_preserves_order():
    values = [3.0, 1.0, 2.0]
    scaled = z_score_scale(values)
    assert scaled[0] > scaled[2] > scaled[1]


def test_z_score_scale_empty():
    assert z_score_scale([]) == []


def test_tempered_softmax_ordering():
    scores = [2.0, 1.0, 0.0]
    probs = tempered_softmax(scores, T=3.5, n_positions=1)
    assert len(probs) == 3
    assert probs[0] > probs[1] > probs[2]


def test_tempered_softmax_cap():
    # One dominant player should never exceed 99.9
    scores = [100.0, 0.0, 0.0]
    probs = tempered_softmax(scores, T=3.5, n_positions=1)
    assert all(p <= 99.9 for p in probs)


def test_tempered_softmax_no_negatives():
    scores = [-1.0, -2.0, -3.0]
    probs = tempered_softmax(scores, T=5.0, n_positions=5)
    assert all(p >= 0.0 for p in probs)


def test_enforce_monotonicity_clamps_cascade():
    p = {"winPct": 20.0, "top5Pct": 15.0, "top10Pct": 10.0, "top20Pct": 5.0}
    enforce_monotonicity(p)
    assert p["top5Pct"] >= p["winPct"]
    assert p["top10Pct"] >= p["top5Pct"]
    assert p["top20Pct"] >= p["top10Pct"]


def test_enforce_monotonicity_already_valid():
    p = {"winPct": 5.0, "top5Pct": 20.0, "top10Pct": 40.0, "top20Pct": 70.0}
    enforce_monotonicity(p)
    assert p == {"winPct": 5.0, "top5Pct": 20.0, "top10Pct": 40.0, "top20Pct": 70.0}


def test_assign_tier_boundaries():
    assert assign_tier(1) == "T1"
    assert assign_tier(5) == "T1"
    assert assign_tier(6) == "T2"
    assert assign_tier(12) == "T2"
    assert assign_tier(13) == "T3"
    assert assign_tier(25) == "T3"
    assert assign_tier(26) == "T4"
    assert assign_tier(40) == "T4"
    assert assign_tier(41) == "T5"
    assert assign_tier(200) == "T5"


def test_make_cut_prob_lower_clamp():
    assert make_cut_prob(0.0) == pytest.approx(20.0)


def test_make_cut_prob_upper_clamp():
    assert make_cut_prob(80.0) == pytest.approx(98.0)


def test_make_cut_prob_midrange():
    # 50 * 1.25 + 10 = 72.5
    assert make_cut_prob(50.0) == pytest.approx(72.5)
```

- [ ] **Step 2: Run tests to verify they all fail (import error)**

```
cd C:\PGA_VenueDNA
python -m pytest tests/test_enrich_cards.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'enrich_cards'`

- [ ] **Step 3: Implement `engine/enrich_cards.py`**

Create `engine/enrich_cards.py`:

```python
"""engine/enrich_cards.py — Pre-tournament dual-vector True SG enrichment."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

ALL_COURSES_FILES = {
    "6m":  "pga_sg_query.csv",
    "12m": "pga_sg_query (1).csv",
    "24m": "pga_sg_query (2).csv",
}
SIM_COURSES_FILES = {
    "6m":  "similar_courses_sg_6m.csv",
    "12m": "similar_courses_sg_12m.csv",
    "24m": "similar_courses_sg_24m.csv",
}
BASE_WEIGHTS  = {"6m": 0.20, "12m": 0.30, "24m": 0.50}
DELTA_WEIGHTS = {"6m": 0.50, "12m": 0.30, "24m": 0.20}
DELTA_CLAMP   = 0.50
TEMPS         = {"win": 3.5, "top5": 5.0, "top10": 7.0, "top20": 10.0}
N_POSITIONS   = {"win": 1, "top5": 5, "top10": 10, "top20": 20}
ZNORM_MEAN, ZNORM_STD = 50.0, 15.0


def normalize_name(s: str | None) -> str:
    return (s or "").strip().strip('"').strip("'").strip()


def load_sg(path: Path) -> dict:
    if not path.exists():
        return {}
    result = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = normalize_name(row.get("player_name", ""))
            rds  = int(float(row.get("rounds_played", 0) or 0))
            tot  = float(row.get("total_mean", 0) or 0)
            if name:
                result[name] = {"rounds": rds, "total_mean": tot}
    return result


def debut_row() -> dict:
    return {"rounds": 0, "total_mean": 0.0}


def compute_horizon(base: dict, sim: dict) -> dict:
    w = min(1.0, sim.get("rounds", 0) / 20.0)
    sg_sim_reg = (w * sim["total_mean"]) + ((1 - w) * base["total_mean"])
    return {"W": w, "sg_sim_reg": sg_sim_reg, "delta_fit": sg_sim_reg - base["total_mean"]}


def blend_composites(b6: float, b12: float, b24: float,
                     d6: float, d12: float, d24: float) -> tuple[float, float]:
    sg_base = 0.20 * b6 + 0.30 * b12 + 0.50 * b24
    delta   = 0.50 * d6 + 0.30 * d12 + 0.20 * d24
    delta   = max(-DELTA_CLAMP, min(DELTA_CLAMP, delta))
    return sg_base, delta


def z_score_scale(values: list[float], mean: float = ZNORM_MEAN,
                  std: float = ZNORM_STD) -> list[float]:
    if not values:
        return []
    mu  = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd  = math.sqrt(var) if var > 0 else 1.0
    return [max(0.0, min(100.0, mean + std * (v - mu) / sd)) for v in values]


def tempered_softmax(scores: list[float], T: float, n_positions: int) -> list[float]:
    max_s = max(scores)
    exps  = [math.exp((s - max_s) / T) for s in scores]
    total = sum(exps)
    return [min(99.9, (e / total) * n_positions * 100) for e in exps]


def enforce_monotonicity(p: dict) -> None:
    p["top5Pct"]  = max(p["top5Pct"],  p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])


def assign_tier(rank: int) -> str:
    if rank <= 5:  return "T1"
    if rank <= 12: return "T2"
    if rank <= 25: return "T3"
    if rank <= 40: return "T4"
    return "T5"


def make_cut_prob(top20: float) -> float:
    return min(98.0, max(20.0, top20 * 1.25 + 10.0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-vector True SG enrichment")
    parser.add_argument("--event", default="2026_3m_open")
    args = parser.parse_args()

    event_dir  = _ROOT / "events" / args.event
    input_dir  = event_dir / "input"
    deploy_dir = event_dir / "deploy" / "data"

    # Validate inputs
    missing = [f for f in list(ALL_COURSES_FILES.values()) + list(SIM_COURSES_FILES.values())
               if not (input_dir / f).exists()]
    if missing:
        print(f"[enrich_cards] ERROR — missing input files: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Load all 6 SG horizons
    all_sg = {h: load_sg(input_dir / f) for h, f in ALL_COURSES_FILES.items()}
    sim_sg = {h: load_sg(input_dir / f) for h, f in SIM_COURSES_FILES.items()}

    # Union of all player names
    all_names: set[str] = set()
    for d in list(all_sg.values()) + list(sim_sg.values()):
        all_names.update(d.keys())

    # Per-player composites
    players = []
    for name in sorted(all_names):
        h_data = {}
        for h in ("6m", "12m", "24m"):
            h_data[h] = compute_horizon(
                all_sg[h].get(name, debut_row()),
                sim_sg[h].get(name, debut_row()),
            )

        sg_base_comp, delta_fit_comp = blend_composites(
            all_sg["6m"].get(name,  debut_row())["total_mean"],
            all_sg["12m"].get(name, debut_row())["total_mean"],
            all_sg["24m"].get(name, debut_row())["total_mean"],
            h_data["6m"]["delta_fit"],
            h_data["12m"]["delta_fit"],
            h_data["24m"]["delta_fit"],
        )

        sg_sim_comp = sg_base_comp + delta_fit_comp

        any_sim = any(sim_sg[h].get(name, debut_row())["rounds"] > 0
                      for h in ("6m", "12m", "24m"))

        players.append({
            "player":              name,
            "sg_base_composite":   round(sg_base_comp,  4),
            "sg_similar_composite": round(sg_sim_comp,  4),
            "delta_fit":           round(delta_fit_comp, 4),
            "data_depth":          "FULL" if any_sim else "DEBUT",
            "_vts_raw":            sg_sim_comp,
            "_nsi_raw":            sg_base_comp,
        })

    # Z-score scaling
    vts_scaled = z_score_scale([p["_vts_raw"] for p in players])
    nsi_scaled = z_score_scale([p["_nsi_raw"] for p in players])

    # Probability vectors
    raw_scores = [p["_vts_raw"] for p in players]
    win_probs  = tempered_softmax(raw_scores, TEMPS["win"],   N_POSITIONS["win"])
    t5_probs   = tempered_softmax(raw_scores, TEMPS["top5"],  N_POSITIONS["top5"])
    t10_probs  = tempered_softmax(raw_scores, TEMPS["top10"], N_POSITIONS["top10"])
    t20_probs  = tempered_softmax(raw_scores, TEMPS["top20"], N_POSITIONS["top20"])

    # Assemble and enforce monotonicity
    for i, p in enumerate(players):
        p["vts_final"]         = round(vts_scaled[i], 1)
        p["neutralSkillIndex"] = round(nsi_scaled[i], 1)
        p["winPct"]   = round(win_probs[i],  1)
        p["top5Pct"]  = round(t5_probs[i],   1)
        p["top10Pct"] = round(t10_probs[i],  1)
        p["top20Pct"] = round(t20_probs[i],  1)
        enforce_monotonicity(p)
        p["makeCutPct"] = round(make_cut_prob(p["top20Pct"]), 1)
        p["missCutPct"] = round(100.0 - p["makeCutPct"], 1)
        del p["_vts_raw"], p["_nsi_raw"]

    # Sort by vts_final descending; assign rank + tier
    players.sort(key=lambda p: p["vts_final"], reverse=True)
    for i, p in enumerate(players, 1):
        p["rank"] = i
        p["tier"] = assign_tier(i)

    # Reorder fields to canonical schema
    ordered = [
        {
            "rank":                p["rank"],
            "player":              p["player"],
            "tier":                p["tier"],
            "vts_final":           p["vts_final"],
            "neutralSkillIndex":   p["neutralSkillIndex"],
            "sg_base_composite":   p["sg_base_composite"],
            "sg_similar_composite": p["sg_similar_composite"],
            "delta_fit":           p["delta_fit"],
            "data_depth":          p["data_depth"],
            "winPct":              p["winPct"],
            "top5Pct":             p["top5Pct"],
            "top10Pct":            p["top10Pct"],
            "top20Pct":            p["top20Pct"],
            "makeCutPct":          p["makeCutPct"],
            "missCutPct":          p["missCutPct"],
        }
        for p in players
    ]

    deploy_dir.mkdir(parents=True, exist_ok=True)
    out_path = deploy_dir / "board_export.json"
    out_path.write_text(
        json.dumps({
            "schemaVersion": "3m-dual-vector-v1.0",
            "generatedAt":   datetime.utcnow().isoformat() + "Z",
            "event":         "2026 3M Open",
            "venue":         "TPC Twin Cities",
            "players":       ordered,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"[enrich_cards] Written {len(ordered)} players → {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd C:\PGA_VenueDNA
python -m pytest tests/test_enrich_cards.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Smoke-run against real input (once similar-course CSVs are in place)**

```
cd C:\PGA_VenueDNA
python engine/enrich_cards.py --event 2026_3m_open
```

Expected output line: `[enrich_cards] Written N players → events/2026_3m_open/deploy/data/board_export.json`

Verify JSON structure:
```
python -c "import json; d=json.load(open('events/2026_3m_open/deploy/data/board_export.json')); print(d['schemaVersion']); print(len(d['players']), 'players'); print(d['players'][0])"
```

Expected: `3m-dual-vector-v1.0` on first line; valid player object on third.

- [ ] **Step 6: Commit**

```
git add engine/enrich_cards.py tests/test_enrich_cards.py events/2026_3m_open/deploy/data/board_export.json
git commit -m "feat: enrich_cards — dual-vector True SG pipeline for 2026 3M Open"
```

---

### Task 2: `events/2026_3m_open/deploy/app.js` — Purge Open Championship Scaffolding and Wire Dual-Vector Traits

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`

**Interfaces:**
- Consumes: `board_export.json` fields `sg_base_composite`, `sg_similar_composite`, `delta_fit`, `vts_final`, `neutralSkillIndex`
- Produces: Working leaderboard and modal with SG Base / SG Sim / Δ Fit instead of VFS / VHD / Penalties

**Changes in order from top to bottom of file:**

- [ ] **Step 1: Clean up state object — remove wave fields and waveByPlayer**

In `const S = { ... }`, replace:
```js
  weather:    { speed: 0, direction: 'N/A', wave_delta: 0.0, tide: 'N/A' },
  waveByPlayer: {},
```
With:
```js
  weather:    { speed: 0, direction: 'N/A' },
```

- [ ] **Step 2: Delete FM, RISK_KEYS, RISK_COLS, RULE_EXP (lines 29–68)**

Remove the entire block from `// ── Audit rule metadata` through the closing `};` of `RULE_EXP`. The deletion spans from:
```js
// ── Audit rule metadata ────────────────────────────────────────────────────────
const FM = {
```
through:
```js
  R9:'HOT/WARM form not validated by links evidence. Form credit discounted 40% of above-neutral contribution.',
};
```

After deletion the next line should be the blank line before `// ── Filter field definitions`.

- [ ] **Step 3: Rewrite FILTER_FIELDS — remove links columns, add dual-vector columns**

Replace the entire `const FILTER_FIELDS = [...]` block:

```js
// ── Filter field definitions ──────────────────────────────────────────────────
const FILTER_FIELDS = [
  { key:'pt_vts',          label:'VTS',            get:(p)      => p.vts_final },
  { key:'pt_nsi',          label:'NSI',            get:(p)      => p.neutralSkillIndex },
  { key:'pt_vfs',          label:'VFS',            get:(p)      => p.venueFitScore },
  { key:'pt_vhd',          label:'VHD',            get:(p)      => p.venueHistoryDelta },
  { key:'live_win',        label:'Win%',           get:(p)      => p.winPct },
  { key:'live_top10',      label:'Top 10%',        get:(p)      => p.top10Pct },
  { key:'live_cut',        label:'Cut%',           get:(p)      => p.makeCutPct },
  { key:'pt_tier',         label:'Tier #',         get:(p)      => parseInt((p.tier||'T5')[1]) },
  { key:'app_150_200',     label:'App 150–200',    get:(p,br)   => traitScore(br,'app_150_200') },
  { key:'ott_accuracy',    label:'OTT Accuracy',   get:(p,br)   => traitScore(br,'ott_accuracy') },
  { key:'ott_positional',  label:'OTT Positional', get:(p,br)   => traitScore(br,'ott_positional') },
  { key:'app_overall',     label:'App Overall',    get:(p,br)   => traitScore(br,'app_overall') },
  { key:'sg_putt',         label:'SG: Putting',    get:(p,br)   => traitScore(br,'sg_putt') },
  { key:'sg_arg',          label:'SG: ARG',        get:(p,br)   => traitScore(br,'sg_arg') },
];
```

With:

```js
// ── Filter field definitions ──────────────────────────────────────────────────
const FILTER_FIELDS = [
  { key:'pt_vts',        label:'VTS',      get:(p)    => p.vts_final },
  { key:'pt_nsi',        label:'NSI',      get:(p)    => p.neutralSkillIndex },
  { key:'pt_delta_fit',  label:'Δ Fit',    get:(p)    => p.delta_fit },
  { key:'pt_sg_base',    label:'SG Base',  get:(p)    => p.sg_base_composite },
  { key:'pt_sg_sim',     label:'SG Sim',   get:(p)    => p.sg_similar_composite },
  { key:'live_win',      label:'Win%',     get:(p)    => p.winPct },
  { key:'live_top10',    label:'Top 10%',  get:(p)    => p.top10Pct },
  { key:'live_cut',      label:'Cut%',     get:(p)    => p.makeCutPct },
  { key:'pt_tier',       label:'Tier #',   get:(p)    => parseInt((p.tier||'T5')[1]) },
  { key:'app_150_200',   label:'App 150–200', get:(p,br) => traitScore(br,'app_150_200') },
  { key:'sg_putt',       label:'SG: Putting', get:(p,br) => traitScore(br,'sg_putt') },
  { key:'sg_arg',        label:'SG: ARG',     get:(p,br) => traitScore(br,'sg_arg') },
];
```

- [ ] **Step 4: Rewrite QUICK_PRESETS — remove links presets, add dual-vector presets**

Replace:
```js
const QUICK_PRESETS = {
  'iron-elites':        [{ field:'app_150_200',  op:'>=', val:70 }],
  'long-iron-fits':     [{ field:'app_150_200',  op:'>=', val:60 }],
  'positional-drivers': [{ field:'ott_accuracy', op:'>=', val:65 }],
  'safe-cut-makers':    [{ field:'pt_vts',        op:'>=', val:65 }],
  'ceiling-plays':      [{ field:'live_win',      op:'>=', val:5.0 }],
};
```

With:
```js
const QUICK_PRESETS = {
  'venue-fits':      [{ field:'pt_delta_fit', op:'>=', val:0.080 }],
  'high-base':       [{ field:'pt_sg_base',  op:'>=', val:1.500 }],
  'long-iron-fits':  [{ field:'app_150_200', op:'>=', val:60 }],
  'safe-cut-makers': [{ field:'pt_vts',      op:'>=', val:65 }],
  'ceiling-plays':   [{ field:'live_win',    op:'>=', val:5.0 }],
};
```

- [ ] **Step 5: Remove birkdaleTag from altPlayers push in canonName()**

Replace:
```js
    S.altPlayers.push({
      player: nm, rank: '—', tier: 'T5',
      vts_final: 50.0,
      neutralSkillIndex: 50.0, nsi_final: 50.0,
      venueFitScore: 50.0,     vfs_final: 50.0,
      venueHistoryDelta: 0,    vhd: 0.0,
      penalties_total: 0,
      winPct: null, top5Pct: null, top10Pct: null,
      top20Pct: null, makeCutPct: null, missCutPct: null,
      win_prob: 0.001, top5_prob: 0.005, top10_prob: 0.010,
      top20_prob: 0.020, make_cut_prob: 0.500, miss_cut_prob: 0.500,
      birkdaleTag: 'RoyalBirkdaleDebut',
      band_name: 'Debut Profile',
```

With:
```js
    S.altPlayers.push({
      player: nm, rank: '—', tier: 'T5',
      vts_final: 50.0,
      neutralSkillIndex: 50.0, nsi_final: 50.0,
      sg_base_composite: 0.0, sg_similar_composite: 0.0, delta_fit: 0.0,
      winPct: null, top5Pct: null, top10Pct: null,
      top20Pct: null, makeCutPct: null, missCutPct: null,
      win_prob: 0.001, top5_prob: 0.005, top10_prob: 0.010,
      top20_prob: 0.020, make_cut_prob: 0.500, miss_cut_prob: 0.500,
      band_name: 'Debut Profile',
```

- [ ] **Step 6: Collapse buildFlags() to return empty array**

Replace:
```js
// ── Derive audit flags from board row ─────────────────────────────────────────
function buildFlags(p) {
  const f = [];
  if (p.R1_PuttRegression)       f.push('R1');
  if (p.R2_ZeroLinks)            f.push('R2');
  if (p.R3_OTTOnlyLinks)         f.push('R3');
  if (p.R4_BirkdaleDepthGate)    f.push('R4');
  if (p.R5_HistoryConflict)      f.push('R5');
  if (p.R6_PuttLedLinksTotal)    f.push('R6');
  if (p.R7_LinksAPPGate)         f.push('R7');
  if (p.R9_FormSpikeUnconfirmed) f.push('R9');
  return f;
}
```

With:
```js
// ── Derive audit flags from board row ─────────────────────────────────────────
function buildFlags(_p) { return []; }
```

- [ ] **Step 7: Simplify init() fetch — remove open_2026_board_export.json fallback**

Replace:
```js
      fetch('data/board_export.json')
        .then(r => r.ok ? r : fetch('data/open_2026_board_export.json'))
        .then(r => r.json()),
```

With:
```js
      fetch('data/board_export.json').then(r => r.json()),
```

- [ ] **Step 8: Simplify weather catch fallback — remove tide and wave_delta**

Replace:
```js
      .catch(() => ({ speed: 18, direction: 'WNW', wave_delta: 0.35, tide: 'Incoming / Damp' }))
```

With:
```js
      .catch(() => ({ speed: 0, direction: 'N/A' }))
```

- [ ] **Step 9: Remove renderRisk() call from renderAll()**

Replace:
```js
function renderAll() {
  renderSpotlight();
  renderTable();
  renderIntel();
  renderRisk();
}
```

With:
```js
function renderAll() {
  renderSpotlight();
  renderTable();
  renderIntel();
}
```

- [ ] **Step 10: Rewrite renderSpotlight() spotlight cards — remove birkdaleTag badges and replace bars**

In `renderSpotlight()`, replace the entire `return \`<div class="spotlight-card ${tc}" ...` template with the version below. Key changes: remove birkdaleTag badge, replace VFS/VHD/Pen bars with SG Sim/Δ Fit bars, replace `birkdale_history_note` with `venue_history_note`:

```js
  grid.innerHTML = t12.map(p => {
    const tc    = p.tier.toLowerCase();
    const nPct  = clamp(p.neutralSkillIndex, 0, 100);
    const sgSimPct = clamp((p.vts_final || 50), 0, 100);
    const dFit  = p.delta_fit || 0;
    const dPct  = clamp(Math.abs(dFit) * 100, 0, 50);
    const br    = S.briefsByName[normName(p.player)] || {};
    const badges = p.badges || br.badges || [];
    return `<div class="spotlight-card ${tc}" data-player="${esc(p.player)}">
      <div class="sc-top">
        <div class="sc-rank sans">${p.rank}</div>
        <div>
          <div class="sc-name">${p.player}</div>
          <span class="tier-badge sans">${p.tier}</span>
        </div>
        <div style="margin-left:auto;text-align:right">
          <div class="sc-vts sans">${f2(p.vts_final)}</div>
          <div class="sc-vts-lbl sans">VTS</div>
        </div>
      </div>
      <div class="sc-bars">
        ${bar('NSI',    nPct,   'bar-nsi',    f1(p.neutralSkillIndex))}
        ${bar('SG Sim', sgSimPct, 'bar-vfs',  sgSign(p.sg_similar_composite))}
        ${bar('Δ Fit',  dPct,   dFit >= 0 ? 'bar-vfs' : 'bar-pen', sgSign(dFit), dFit >= 0 ? 'var(--green-ok)' : 'var(--accent)')}
      </div>
      <div class="sc-stats">
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.winPct)}</div><div class="sc-stat-lbl sans">Win</div></div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.top10Pct)}</div><div class="sc-stat-lbl sans">Top 10</div></div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.makeCutPct)}</div><div class="sc-stat-lbl sans">Cut</div></div>
      </div>
      ${badges.length ? `<div class="sc-flags">${badges.map(b => `<span class="badge sans">${b}</span>`).join('')}</div>` : ''}
      <div class="sc-reason">${p.tierReason || ''}</div>
      ${(() => {
        const rows = [
          { lbl: 'Win Mechanism',       val: br.scoring_thesis },
          { lbl: 'Key Risk to Monitor', val: br.failure_condition || br.risk_vector },
          { lbl: 'Analyst Brief',       val: br.conviction_statement },
        ].filter(r => r.val);
        return rows.length
          ? `<div class="sc-analyst">${rows.map(r =>
              `<div class="sc-analyst-row">
                <div class="sc-analyst-lbl sans">${r.lbl}</div>
                <div class="sc-analyst-txt">${esc(r.val)}</div>
              </div>`).join('')}</div>`
          : '';
      })()}
    </div>`;
  }).join('');
```

- [ ] **Step 11: Rewrite renderTable() tbody row — replace VFS/VHD/Penalties columns**

Replace the full `tbody.innerHTML = sorted.map(p => { ... }).join('');` template. The key changes: remove `data-tag`, remove `data-vfs`, replace the VFS/VHD/Pen `<td>` cells with SG Base/SG Sim/Δ Fit, remove birkdaleTag badge:

```js
  tbody.innerHTML = sorted.map(p => {
    const tColor = { T1:'var(--t1-t)', T2:'var(--t2-t)', T3:'var(--t3-t)', T4:'var(--t4-t)', T5:'var(--t5-t)' }[p.tier];
    const tBg    = { T1:'var(--t1-bg)', T2:'var(--t2-bg)', T3:'var(--t3-bg)', T4:'var(--t4-bg)', T5:'var(--t5-bg)' }[p.tier];
    const flagStr = p._flags.join(',');
    return `<tr data-player="${esc(p.player)}" data-tier="${p.tier}" data-flags="${flagStr}" data-vts="${p.vts_final ?? ''}" data-nsi="${p.neutralSkillIndex ?? ''}" data-win="${p.winPct ?? ''}">
      <td class="left"><span class="rank-num sans" style="background:${tBg};color:${tColor}">${p.rank}</span></td>
      <td class="left"><div class="player-name-cell">${p.player}
        <small><span class="tier-badge sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor}">${p.tier}</span></small>
      </div></td>
      <td class="vts-cell sans">${f2(p.vts_final)}</td>
      <td class="sans">${f1(p.neutralSkillIndex)}</td>
      <td class="sans">${sgSign(p.sg_base_composite)}</td>
      <td class="sans">${sgSign(p.sg_similar_composite)}</td>
      <td class="sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</td>
      <td class="sans">${pct(p.winPct)}</td>
      <td class="sans">${pct(p.top10Pct)}</td>
      <td class="sans">${pct(p.makeCutPct)}</td>
    </tr>`;
  }).join('');
```

- [ ] **Step 12: Remove three legacy filter cases from applyVisibility()**

Replace:
```js
      switch (S.currentFilter) {
        case 'flagged':   if (!flags.length) show = false; break;
        case 'nopen':     if (flags.length)  show = false; break;
        case 't1t2':      if (tier !== 'T1' && tier !== 'T2') show = false; break;
        case 'history':   if (tag !== 'BirkdaleHistoryThin') show = false; break;
        case 'debut':     if (tag !== 'RoyalBirkdaleDebut')  show = false; break;
        case 'zerolinks': if (!flags.includes('R2'))          show = false; break;
      }
```

With:
```js
      switch (S.currentFilter) {
        case 'flagged': if (!flags.length) show = false; break;
        case 'nopen':   if (flags.length)  show = false; break;
        case 't1t2':    if (tier !== 'T1' && tier !== 'T2') show = false; break;
      }
```

Also remove the `const tag = tr.dataset.tag || '';` line two lines above the switch since `data-tag` no longer exists on rows.

- [ ] **Step 13: Update updateSortArrows() keyMap for new column order**

Replace:
```js
  const keyMap = ['rank','player','vts_final','neutralSkillIndex','venueFitScore','venueHistoryDelta','penalties_total','winPct','top10Pct','makeCutPct'];
```

With:
```js
  const keyMap = ['rank','player','vts_final','neutralSkillIndex','sg_base_composite','sg_similar_composite','delta_fit','winPct','top10Pct','makeCutPct'];
```

- [ ] **Step 14: Update updateBoardSub() venue name**

Replace:
```js
    ? `${total} players · Royal Birkdale VTS`
```

With:
```js
    ? `${total} players · TPC Twin Cities VTS`
```

- [ ] **Step 15: Delete renderRisk(), fmtRisk(), and toggleRisk() function bodies**

Delete the entire block from:
```js
// ── Risk register ──────────────────────────────────────────────────────────────
function renderRisk() {
```
through the closing `}` of `toggleRisk()`:
```js
function toggleRisk(hdr) {
  hdr.nextElementSibling.classList.toggle('open');
  hdr.querySelector('.risk-toggle').classList.toggle('open');
}
```

- [ ] **Step 16: Remove birkdale_history_note from buildWinCase() hasAny check and template**

Replace:
```js
  const hasAny = br.scoring_thesis || br.birkdale_history_note || br.failure_condition ||
                 br.risk_vector || br.conviction_statement || br.structural_note;
```

With:
```js
  const hasAny = br.scoring_thesis || br.failure_condition ||
                 br.risk_vector || br.conviction_statement || br.structural_note;
```

And remove the `birkdale_history_note` template line from the win case card:
```js
        ${br.birkdale_history_note ? `<div class="wc-q ${tc}c">Course Calibration</div><div class="wc-p">${br.birkdale_history_note}</div>` : ''}
```

- [ ] **Step 17: Clean up openModal() — remove riskData/riskDetails and wave variable block**

In `openModal()`, remove the `riskData` and `riskDetails` declarations:
```js
  const riskData = (S.analysis || {}).birkdale_risk_register || {};
  const riskDetails = flags.map(code => {
    const list  = riskData[RISK_KEYS[code]] || [];
    const entry = list.find(x => x.player === p.player);
    return entry ? { code, entry } : null;
  }).filter(Boolean);
```

And remove the entire wave variable block (everything from `const waveEntry` through `const windMitFill`):
```js
  const waveEntry    = S.waveByPlayer[normName(p.player)] || {};
  const _hasWaveData = !p._isAlt && (normName(p.player) in S.waveByPlayer);
  const playerWave   = _hasWaveData ? (waveEntry.wave || p.wave || null) : null;
  const waveDraw     = _hasWaveData ? (waveEntry.wave_draw || null) : 'Neutral';
  const wavePenalty  = _hasWaveData ? (waveEntry.wave_penalty ?? 0) : 0.0;
  const waveDelta    = S.weather.wave_delta || 0;
  const waveIsPen    = wavePenalty < 0;
  const waveLabel    = waveDraw === 'Neutral' || (!waveDraw && !playerWave)
    ? 'Neutral Draw — No Wind Penalty'
    : waveDraw
      ? (waveIsPen ? `${waveDraw} Draw — High Wind Exposure` : `${waveDraw} Draw — Favorable Window`)
      : (playerWave === 'early_late' ? 'AM Draw' : playerWave === 'late_early' ? 'PM Draw' : 'Neutral Draw — No Wind Penalty');
  const adjFloor     = fs != null && waveIsPen ? +(fs + wavePenalty).toFixed(1) : null;
  const windMitTrait = (br.trait_scores || []).find(t => /accuracy|ott/i.test(t.label || ''));
  const windMitScore = windMitTrait ? windMitTrait.score : (p.venueFitScore ?? 50);
  const windMitPct   = clamp(windMitScore, 0, 100);
  const windMitFill  = windMitScore >= 85 ? 'trait-fill-hi' : windMitScore >= 70 ? 'trait-fill-mid' : windMitScore >= 50 ? 'trait-fill-lo' : 'trait-fill-weak';
  const windMitColor = traitScoreColor(windMitScore) || 'color:#94a3b8';
```

Also remove the `nPct2`, `vPct2`, `vhPct2`, `pPct2` variable lines (used only for the old bars):
```js
  const nPct2  = clamp(p.neutralSkillIndex, 0, 100);
  const vPct2  = clamp(p.venueFitScore, 0, 100);
  const vhPct2 = clamp(Math.abs(p.venueHistoryDelta || 0) * 30, 0, 100);
  const pPct2  = clamp(Math.abs(p.penalties_total || 0) * 5, 0, 100);
```

And the `pens`, `activePens`, `zeroPens` variables (used only for old penalties section):
```js
  const pens = [
    {c:'R1',v:p.penaltyR1},{c:'R2',v:p.penaltyR2},{c:'R3',v:p.penaltyR3},
    {c:'R4',v:p.penaltyR4},{c:'R5',v:p.penaltyR5},{c:'R6',v:p.penaltyR6},
    {c:'R7',v:p.penaltyR7},{c:'R8',v:p.penaltyR8||0},{c:'R9',v:p.penaltyR9},
  ].filter(x => x.v !== undefined);
  const activePens = pens.filter(x => x.v && x.v !== 0);
  const zeroPens   = pens.filter(x => !x.v || x.v === 0);
```

- [ ] **Step 18: Simplify weather block in modal §1 — remove tide, wave, wind mitigation content**

The `${S.weather.speed > 0 ? \`...\` : ''}` block inside §1 currently shows wind speed, tide, wave draw, wave penalty bar, and adj floor. Replace with a simple wind-only display:

Replace:
```js
        ${S.weather.speed > 0 ? `<div style="margin-top:14px;padding:10px 14px;background:#0f172a;border:1px solid #1e293b;border-radius:8px">
          <div class="sans" style="font-size:10px;letter-spacing:.08em;color:#f59e0b;margin-bottom:8px">WEATHER &amp; WAVE PROFILE</div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-bottom:10px">
            <div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Wind: </span>
              <span class="sans" style="font-size:12px;color:#e2e8f0;font-weight:600">${S.weather.speed} kts ${S.weather.direction}</span>
            </div>
            <div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Tide: </span>
              <span class="sans" style="font-size:12px;color:#e2e8f0">${S.weather.tide}</span>
            </div>
            ${waveDraw ? `<div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Draw: </span>
              <span class="sans" style="font-size:12px;font-weight:700;color:${waveIsPen ? '#f59e0b' : '#3b82f6'}">${waveLabel}</span>
            </div>` : ''}
          </div>
          <div style="margin-bottom:8px">
            <div class="sans" style="font-size:10px;color:#64748b;letter-spacing:.06em;margin-bottom:4px">WIND IMPACT MITIGATION</div>
            <div class="trait-track"><div class="${windMitFill}" style="width:${windMitPct}%"></div></div>
            <div class="sans" style="font-size:11px;margin-top:3px;${windMitColor}">${f1(windMitScore)}</div>
          </div>
          ${waveIsPen ? `<div style="margin-top:8px;padding:8px 12px;background:#1c1400;border:1px solid #f59e0b;border-radius:6px;display:flex;align-items:center;gap:10px">
            <span class="sans" style="font-size:13px;font-weight:700;color:#f59e0b">${wavePenalty.toFixed(2)} Strokes</span>
            <span class="sans" style="font-size:11px;color:#94a3b8">Latent score adjusted for wind wave exposure</span>
          </div>` : ''}
          ${adjFloor != null ? `<div style="margin-top:6px">
            <span class="sans" style="font-size:11px;color:#94a3b8">Adj. Floor: </span>
            <span class="sans" style="font-size:12px;font-weight:600;color:#f59e0b">${adjFloor > 0 ? '+' : ''}${adjFloor}</span>
          </div>` : ''}
        </div>` : ''}
```

With:
```js
        ${S.weather.speed > 0 ? `<div style="margin-top:14px;padding:10px 14px;background:#0f172a;border:1px solid #1e293b;border-radius:8px">
          <div class="sans" style="font-size:10px;letter-spacing:.08em;color:#f59e0b;margin-bottom:8px">WIND CONDITIONS</div>
          <span class="sans" style="font-size:11px;color:#94a3b8">Wind: </span>
          <span class="sans" style="font-size:12px;color:#e2e8f0;font-weight:600">${S.weather.speed} kts ${S.weather.direction}</span>
        </div>` : ''}
```

- [ ] **Step 19: Remove vhn_rounds / "Birkdale Rds" from modal §9**

Remove only this line inside the `${ ... }` db-metrics-row block in §9:
```js
          ${br.vhn_rounds != null ? `<div class="db-metric"><div class="db-metric-key">Birkdale Rds</div><div class="db-metric-val">${br.vhn_rounds}</div></div>` : ''}
```

- [ ] **Step 20: Replace modal §10 System Footprint bars with dual-vector bars**

Replace the entire `<!-- §10 — SYSTEM FOOTPRINT: decomposition + penalties + venue evidence -->` section through the closing `</div>` of the last `modal-sec` in the template:

```js
      <!-- §10 — SYSTEM FOOTPRINT: dual-vector decomposition -->
      <div class="modal-sec">
        <div class="modal-sec-title sans">System Footprint — Score Decomposition</div>
        <div class="modal-layers">
          <div class="layer-row"><div class="layer-lbl sans">NSI</div><div class="layer-track"><div class="layer-fill" style="width:${clamp(p.neutralSkillIndex,0,100)}%;background:var(--navy)"></div></div><div class="layer-val sans" style="color:var(--navy)">${f1(p.neutralSkillIndex)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">SG Sim</div><div class="layer-track"><div class="layer-fill" style="width:${clamp(p.vts_final,0,100)}%;background:var(--green-ok)"></div></div><div class="layer-val sans" style="color:var(--green-ok)">${f1(p.vts_final)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">Δ Fit</div>${vhdDivergingBar(p.delta_fit)}<div class="layer-val sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</div></div>
        </div>
      </div>

      <div class="modal-sec">
        <div class="modal-sec-title sans">Similar Course Profile</div>
        <div class="modal-layers">
          <div class="layer-row"><div class="layer-lbl sans">SG Base</div><div style="flex:1;font-size:.78rem;color:var(--muted)">baseline skill anchor</div><div class="layer-val sans">${sgSign(p.sg_base_composite)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">SG Sim</div><div style="flex:1;font-size:.78rem;color:var(--muted)">similar-course ability</div><div class="layer-val sans">${sgSign(p.sg_similar_composite)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">Δ Fit</div><div style="flex:1;font-size:.78rem;color:var(--muted)">TPC Twin Cities uplift</div><div class="layer-val sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</div></div>
        </div>
        <div class="modal-note sans" style="margin-top:6px">data depth: <b>${p.data_depth || '—'}</b></div>
      </div>
```

This replaces the §10 footprint block + the old "Audit Penalties" block + the old "Links & Venue Evidence" block. Everything from `<!-- §10 ...` through the final `</div>` before `</div>` (closing `modal-body`) should become the two `<div class="modal-sec">` blocks above.

- [ ] **Step 21: Remove 'sec-risk' from PRE_SECTIONS**

Replace:
```js
const PRE_SECTIONS = ['sec-spotlight','sec-board','sec-intel','sec-risk','sec-method'];
```

With:
```js
const PRE_SECTIONS = ['sec-spotlight','sec-board','sec-intel','sec-method'];
```

- [ ] **Step 22: Syntax check**

```
node --check events/2026_3m_open/deploy/app.js
```

Expected: exits 0 with no output.

- [ ] **Step 23: Commit**

```
git add events/2026_3m_open/deploy/app.js
git commit -m "feat: 3M Open app.js — purge OC scaffolding, wire sg_base/sg_sim/delta_fit dual-vector traits"
```

---

### Task 3: Create `events/2026_3m_open/deploy/3m_open_2026_board.html` + update `index.html` redirect

**Files:**
- Create: `events/2026_3m_open/deploy/3m_open_2026_board.html`
- Modify: `events/2026_3m_open/deploy/index.html`

**Interfaces:**
- Consumes: `app.js` (relative, same directory), `data/board_export.json`
- Requires these DOM IDs and classes in HTML so `app.js` can wire events and render into them (complete list): `#board-tbody`, `.board-table`, `[id^="sa-"]` sort arrows, `#modal-overlay`, `#modal-content`, `#spotlight-grid`, `#spotlight-container`, `#spotlight-toggle`, `#tier-intel`, `#result-ct`, `#board-sub`, `#player-search`, `#sec-spotlight`, `#sec-board`, `#sec-intel`, `#sec-method`, `#sec-live`, `#sec-pm`, `#live-content`, `#live-pending`, `#glossary-modal-overlay`, `#glossary-modal-close`, `#adv-toggle`, `#adv-filter-panel`, `#rfb-add-rule`, `#clear-filters-btn`, `#scroll-top`, `.round-tab[data-round]`, `.chip[data-f]`, `.tier-tile[data-tier]`, `#wx-badge`, `#fb-wind-rating`

- [ ] **Step 1: Read the OC board HTML to use as CSS source**

```
Read: events/2026_the_open_championship/deploy/2026_the_open_championship_board.html
```

The `<style>` block (approx lines 11–560) is fully compatible with app.js class names. Copy it verbatim — all the CSS stays identical. Only HTML structure and text changes.

- [ ] **Step 2: Create `3m_open_2026_board.html`**

Copy the OC board HTML to `events/2026_3m_open/deploy/3m_open_2026_board.html`, then apply **every** change listed below. Make all changes to the copy in one pass.

**Change A — Title and header text:** Replace all occurrences of:
- `The Open Championship 2026` → `3M Open 2026`
- `Royal Birkdale` → `TPC Twin Cities`
- `VenueDNA — The Open Championship 2026` (page title) → `VenueDNA — 3M Open 2026`
- `Royal Birkdale VTS` → `TPC Twin Cities VTS`

**Change B — Table `<thead>` column headers:** Find the `<thead>` inside `.board-table`. Replace its content with:

```html
<thead>
<tr>
  <th onclick="doSort('rank')">Rank<span id="sa-rank" class="sort-arrow asc active"></span></th>
  <th onclick="doSort('player')">Player<span id="sa-player" class="sort-arrow idle"></span></th>
  <th onclick="doSort('vts_final')">VTS<span id="sa-vts_final" class="sort-arrow idle"></span></th>
  <th onclick="doSort('neutralSkillIndex')">NSI<span id="sa-neutralSkillIndex" class="sort-arrow idle"></span></th>
  <th onclick="doSort('sg_base_composite')">SG Base<span id="sa-sg_base_composite" class="sort-arrow idle"></span></th>
  <th onclick="doSort('sg_similar_composite')">SG Sim<span id="sa-sg_similar_composite" class="sort-arrow idle"></span></th>
  <th onclick="doSort('delta_fit')">Δ Fit<span id="sa-delta_fit" class="sort-arrow idle"></span></th>
  <th onclick="doSort('winPct')">Win%<span id="sa-winPct" class="sort-arrow idle"></span></th>
  <th onclick="doSort('top10Pct')">Top10%<span id="sa-top10Pct" class="sort-arrow idle"></span></th>
  <th onclick="doSort('makeCutPct')">Cut%<span id="sa-makeCutPct" class="sort-arrow idle"></span></th>
</tr>
</thead>
```

**Change C — Filter chip buttons:** In the controls bar, remove chips for `history`, `debut`, `zerolinks`. Keep only:
```html
<button class="ctrl-btn chip active" data-f="all" onclick="setChip('all')">All</button>
<button class="ctrl-btn chip" data-f="t1t2" onclick="setChip('t1t2')">T1+T2</button>
<button class="ctrl-btn chip" data-f="nopen" onclick="setChip('nopen')">Clean</button>
```

**Change D — Preset dropdown items:** Replace all `<button class="preset-item" ...>` buttons with:
```html
<button class="preset-item" data-preset="venue-fits">Venue Fits (Δ Fit ≥ +0.08)</button>
<button class="preset-item" data-preset="high-base">High Base (SG Base ≥ 1.50)</button>
<button class="preset-item" data-preset="long-iron-fits">Long Iron Fits</button>
<button class="preset-item" data-preset="safe-cut-makers">Safe Cut Makers</button>
<button class="preset-item" data-preset="ceiling-plays">Ceiling Plays</button>
```

**Change E — Remove `#sec-risk` section:** Delete the entire `<section id="sec-risk">` block (the risk register panel).

**Change F — Weather cards:** The weather section should show only a wind speed card. Remove any tide, wave, swell cards. Keep `#wx-badge` and `#fb-wind-rating` so `renderWeather()` can update them.

**Change G — Board subtitle initial text:** Find the element with `id="board-sub"` and set initial text to `Loading… · TPC Twin Cities VTS`.

**Change H — Glossary entries:** Update glossary term definitions:
- Replace VFS / VHD / Penalties entries with:
  - `SG Base` — Baseline skill across all courses (stability-weighted composite)
  - `SG Sim` — Similar-course strokes gained (sample-weighted regression)  
  - `Δ Fit` — Delta between SG Sim and SG Base; TPC Twin Cities venue fit signal

**Change I — `<script src="app.js">` tag:** Ensure it points to `app.js` (relative, no path prefix).

- [ ] **Step 3: Update `index.html` to redirect to new board**

Replace the entire content of `events/2026_3m_open/deploy/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url=3m_open_2026_board.html">
<title>VenueDNA — 3M Open 2026</title>
<style>
  body { margin: 0; background: #0f1419; color: #c9a84c; font-family: sans-serif;
         display: flex; align-items: center; justify-content: center; height: 100vh; }
  a { color: #c9a84c; }
</style>
</head>
<body>
  <p>Redirecting… <a href="3m_open_2026_board.html">click here if not redirected</a></p>
</body>
</html>
```

- [ ] **Step 4: Smoke-test in browser**

Start a local server and open `index.html`:
```
cd events/2026_3m_open/deploy
python -m http.server 8080
```

Open `http://localhost:8080` and verify:
1. Redirects to `3m_open_2026_board.html`
2. Board loads with 10 columns: Rank, Player, VTS, NSI, SG Base, SG Sim, Δ Fit, Win%, Top10%, Cut%
3. SG Base / SG Sim values show `+X.XXX` format (3 decimals with sign)
4. Δ Fit values are green for positive, red for negative
5. Clicking a player opens a modal with "Similar Course Profile" section showing SG Base / SG Sim / Δ Fit values
6. Filter chips work (All / T1+T2 / Clean)
7. Preset dropdown shows "Venue Fits" and "High Base" options

- [ ] **Step 5: Commit**

```
git add events/2026_3m_open/deploy/3m_open_2026_board.html events/2026_3m_open/deploy/index.html
git commit -m "feat: 3M Open board HTML — dual-vector table, updated modal, no OC scaffolding"
```

---

## Self-Review

**Spec coverage:**
- ✓ `enrich_cards.py` with all 8 pure functions + `main()` — Task 1
- ✓ Dual-vector math: per-horizon W/SG_Sim_Reg/Delta_Fit, decoupled decay weights, Delta clamp — Task 1 Step 3
- ✓ Z-score scale (mean=50, std=15, clamp [0,100]) — Task 1 Step 3
- ✓ Tempered softmax (4 temperatures) with monotonicity — Task 1 Step 3
- ✓ `board_export.json` schema (all 15 fields) — Task 1 Step 3
- ✓ `data_depth` FULL/DEBUT logic — Task 1 Step 3
- ✓ Exit 1 on missing CSV — Task 1 Step 3 main()
- ✓ FM/RISK_KEYS/RISK_COLS/RULE_EXP deleted — Task 2 Step 2
- ✓ FILTER_FIELDS updated (links removed, dual-vector added) — Task 2 Step 3
- ✓ QUICK_PRESETS updated (venue-fits, high-base) — Task 2 Step 4
- ✓ buildFlags() → `return [];` — Task 2 Step 6
- ✓ fetch fallback removed — Task 2 Step 7
- ✓ renderTable() columns updated — Task 2 Step 11
- ✓ applyVisibility() legacy cases removed — Task 2 Step 12
- ✓ updateSortArrows() keyMap updated — Task 2 Step 13
- ✓ "Royal Birkdale VTS" → "TPC Twin Cities VTS" — Task 2 Step 14
- ✓ renderRisk/fmtRisk/toggleRisk deleted — Task 2 Step 15
- ✓ Modal §10 footprint bars: NSI/SGSim/ΔFit — Task 2 Step 20
- ✓ "Similar Course Profile" section replaces "Links & Venue Evidence" — Task 2 Step 20
- ✓ PRE_SECTIONS minus sec-risk — Task 2 Step 21
- ✓ Board HTML with correct 10 columns + sort arrows — Task 3 Step 2
- ✓ index.html redirect updated — Task 3 Step 3

**Placeholder scan:** None found.

**Type consistency:**
- `sgSign(p.sg_base_composite)` — `sg_base_composite` defined in enrich_cards.py output schema ✓
- `sgSign(p.sg_similar_composite)` — `sg_similar_composite` defined ✓
- `sgSign(p.delta_fit)` — `delta_fit` defined ✓
- `p.vts_final` used in SG Sim bar — this IS the z-scored sg_similar_composite ✓
- `vhdDivergingBar(p.delta_fit)` — delta_fit is a raw float in [-0.5, +0.5]; diverging bar uses `val/5.0*50` scale which maps ±0.5 to ±5% fill — **note:** the diverging bar scale was designed for VHD (typically ±1 to ±5 range). For delta_fit (range ±0.50), the fill will be very small. Consider scaling: `val / 0.50 * 50` → maps ±0.50 to ±50% fill. Update `vhdDivergingBar(p.delta_fit)` call to use `p.delta_fit * 10` to get visual fill: `vhdDivergingBar((p.delta_fit || 0) * 10)` — this maps ±0.50 to ±5.0 which gives 50% fill at maximum delta.
- Sort arrow IDs: `sa-sg_base_composite`, `sa-sg_similar_composite`, `sa-delta_fit` must match keyMap entries exactly ✓

**Fix needed:** In Task 2 Step 20, the `vhdDivergingBar` call for delta_fit should use a scaled value for visual clarity:
```js
          <div class="layer-row"><div class="layer-lbl sans">Δ Fit</div>${vhdDivergingBar((p.delta_fit||0)*10)}<div class="layer-val sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</div></div>
```
(The `×10` scale maps ±0.50 SG/round to the same visual range as ±5.0 VHD, giving 50% fill at max delta.)
