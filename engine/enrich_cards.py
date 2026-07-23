"""engine/enrich_cards.py — Pre-tournament dual-vector True SG enrichment."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

ALL_COURSES_FILES = {
    "6m":  "pga_sg_query_allcourses_l6.csv",
    "12m": "pga_sg_query_allcourses_l12.csv",
    "24m": "pga_sg_query_allcourses_l24.csv",
}
SIM_COURSES_FILES = {
    "6m":  "pga_sg_query_3Mopen_similar_l6.csv",
    "12m": "pga_sg_query_3Mopen_similar_l12.csv",
    "24m": "pga_sg_query_3Mopen_similar_l24.csv",
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
    def _safe_float(v: str) -> float:
        try:
            return float(v) if v and v.lower() not in ("null", "none", "") else 0.0
        except (ValueError, TypeError):
            return 0.0

    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = normalize_name(row.get("player_name", ""))
            rds  = int(_safe_float(row.get("rounds_played", "0")))
            tot  = _safe_float(row.get("total_mean", "0"))
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

    # Validate all 6 input CSVs exist
    missing = [f for f in list(ALL_COURSES_FILES.values()) + list(SIM_COURSES_FILES.values())
               if not (input_dir / f).exists()]
    if missing:
        print(f"[enrich_cards] ERROR — missing input files: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Load all 6 SG horizons
    all_sg = {h: load_sg(input_dir / f) for h, f in ALL_COURSES_FILES.items()}
    sim_sg = {h: load_sg(input_dir / f) for h, f in SIM_COURSES_FILES.items()}

    # Union of all player names across all 6 files
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
            "player":               name,
            "sg_base_composite":    round(sg_base_comp,   4),
            "sg_similar_composite": round(sg_sim_comp,    4),
            "delta_fit":            round(delta_fit_comp, 4),
            "data_depth":           "FULL" if any_sim else "DEBUT",
            "_vts_raw":             sg_sim_comp,
            "_nsi_raw":             sg_base_comp,
        })

    # Z-score scaling
    vts_scaled = z_score_scale([p["_vts_raw"] for p in players])
    nsi_scaled = z_score_scale([p["_nsi_raw"] for p in players])

    # Probability vectors (tempered softmax)
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
            "rank":                 p["rank"],
            "player":               p["player"],
            "tier":                 p["tier"],
            "vts_final":            p["vts_final"],
            "neutralSkillIndex":    p["neutralSkillIndex"],
            "sg_base_composite":    p["sg_base_composite"],
            "sg_similar_composite": p["sg_similar_composite"],
            "delta_fit":            p["delta_fit"],
            "data_depth":           p["data_depth"],
            "winPct":               p["winPct"],
            "top5Pct":              p["top5Pct"],
            "top10Pct":             p["top10Pct"],
            "top20Pct":             p["top20Pct"],
            "makeCutPct":           p["makeCutPct"],
            "missCutPct":           p["missCutPct"],
        }
        for p in players
    ]

    deploy_dir.mkdir(parents=True, exist_ok=True)
    out_path = deploy_dir / "board_export.json"
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": "3m-dual-vector-v1.0",
                "generatedAt":   datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "event":         "2026 3M Open",
                "venue":         "TPC Twin Cities",
                "players":       ordered,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[enrich_cards] Written {len(ordered)} players -> {out_path}")


if __name__ == "__main__":
    main()
