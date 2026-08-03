"""
Rocket Classic -- R4 Shrinkage-Mode Live Weighting (engine-only).

Produces a forward-looking probabilistic projection for Round 4 of the 2026 Rocket
Classic, BEFORE R4 is played. Blends each cut survivor's pre-event forecast
(vts_final, converted to SG/round units) with their live R1-R3 form (sg_total / 3)
using shrinkage-mode weighting:

    w_live = n / (n + 8)

n = rounds completed (3). K=8 is reused from this project's own "<8 rounds = low
confidence" convention -- not a new invented constant.

Shrinkage mode is the only mode implemented/official for R4 in this event. The
shared root engine's escalating-softmax pattern (engine/build_round_analysis.py,
gamma = 3.5 * ROUND) is an independent feature used by other events -- it has zero
references to "rocket_classic" and no round-numbered payload-rebuild files exist
for this event, confirming it has never run here. This script does not touch or
port it; escalating-mode diagnostic tags (promotion_watch/hold/downgrade_watch)
already produced by build_live_r3.py are carried through read-only for reference.

Read-only against:
  - output/2026_rocket_classic_r3_live.json       (cut_survivors: live SG/rounds)
  - output/2026_rocket_classic_event_payload.json (frozen pre-event vts_final)

Writes only:
  - output/round4/2026_rocket_classic_r4_shrinkage_projection.json
  - output/round4/2026_rocket_classic_r4_shrinkage_projection.csv (same data, flat
    one-row-per-cut-survivor form -- a live diagnostics artifact only; never used to
    write back into vts_full.csv or event_payload.json)

Does not modify event_payload.json, r3_live.json, canonical ranks/tiers, or any
deploy/ file. The CSV is derived from the same in-memory `build()` output as the
JSON -- fully reproducible from engine inputs, no separate computation path.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

EVENT_DIR = Path(__file__).resolve().parent.parent
R3_LIVE_PATH = EVENT_DIR / "output" / "2026_rocket_classic_r3_live.json"
PAYLOAD_PATH = EVENT_DIR / "output" / "2026_rocket_classic_event_payload.json"
OUT_PATH = EVENT_DIR / "output" / "round4" / "2026_rocket_classic_r4_shrinkage_projection.json"
OUT_CSV_PATH = EVENT_DIR / "output" / "round4" / "2026_rocket_classic_r4_shrinkage_projection.csv"

# CSV column order. The four names the requester explicitly specified are used
# verbatim (baseline_sg_per_round, live_sg_per_round_r1_r3, w_live,
# forecast_sg_per_round_r4); other columns carry the same values already present in
# the JSON output, renamed only where needed for flat-file clarity (e.g. splitting
# confidence_band into _low/_high since CSV cells can't hold a list).
CSV_COLUMNS = [
    "player_id",
    "player_name",
    "pre_event_rank",
    "pre_event_tier",
    "vts_final",
    "total_thru_r3",
    "baseline_sg_per_round",
    "live_sg_per_round_r1_r3",
    "w_live",
    "forecast_sg_per_round_r4",
    "projected_r4_score_to_par",
    "projected_final_total",
    "volatility_index",
    "confidence_band_low",
    "confidence_band_high",
    "win_pct",
    "top5_pct",
    "top10_pct",
    "top20_pct",
    "diagnostic_label",
    "live_round_delta_tag",
]

PAR = 70
N_ROUNDS = 3
SHRINKAGE_K = 8  # reused from this project's "<8 rounds = low confidence" convention
W_LIVE = N_ROUNDS / (N_ROUNDS + SHRINKAGE_K)

# Reused verbatim from engine/build_round_analysis.py (_LIVE_TEMPS, ~line 1813) for
# methodological consistency. NOTE: calibrated for the escalating-mode V_p(t) scale,
# not re-derived for shrinkage-mode inputs -- flagged in output as an assumption.
LIVE_TEMPS = {"win": 0.30, "top5": 0.55, "top10": 0.75, "top20": 1.10}


def softmax_t(values: list[float], temp: float) -> list[float]:
    """Max-subtraction stabilized softmax, reused verbatim from build_round_analysis.py."""
    scaled = [v / temp for v in values]
    max_s = max(scaled)
    exps = [math.exp(s - max_s) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build() -> dict:
    r3_live = load_json(R3_LIVE_PATH)
    payload = load_json(PAYLOAD_PATH)

    survivors = r3_live["cut_survivors"]
    payload_by_id = {p["player_id"]: p for p in payload["players"]}

    par_from_holes = sum(h["par"] for h in r3_live["course_observations"]["holes"])
    assert par_from_holes == PAR, f"Course par changed: holes sum to {par_from_holes}, expected {PAR}"

    # ---- Field-wide round variance (pooled, population variance, relative to each
    #      round's own field mean) ----
    round_scores: dict[int, list[float]] = {1: [], 2: [], 3: []}
    for p in survivors:
        for n in (1, 2, 3):
            v = p.get(f"r{n}")
            if v is not None:
                round_scores[n].append(v - PAR)
    round_means = {n: sum(vals) / len(vals) for n, vals in round_scores.items() if vals}

    deviations: list[float] = []
    for p in survivors:
        for n in (1, 2, 3):
            v = p.get(f"r{n}")
            if v is not None and n in round_means:
                deviations.append((v - PAR) - round_means[n])
    field_var = sum(d * d for d in deviations) / len(deviations) if deviations else 0.0

    # R4's own field mean isn't knowable before it's played; R3's field mean today
    # (freshest available round baseline) stands in for the expected R4 field scoring
    # level when converting a player's SG-relative forecast_R4 into an actual score.
    baseline_r4_field = round_means.get(3, 0.0)

    # ---- Per-player blend ----
    records: list[dict] = []
    proj_totals: list[float] = []
    match_issues: list[dict] = []

    for p in survivors:
        pid = p.get("player_id")
        pay = payload_by_id.get(pid)
        sg_total = p.get("sg_total")

        if pay is None or pay.get("vts_final") is None:
            match_issues.append({
                "player_key": p.get("player_key"),
                "player_name": p.get("player_name"),
                "player_id": pid,
                "reason": "no payload match or missing vts_final; excluded from projection",
            })
            continue
        if sg_total is None:
            match_issues.append({
                "player_key": p.get("player_key"),
                "player_name": p.get("player_name"),
                "player_id": pid,
                "reason": "missing sg_total in cut_survivors; excluded from projection",
            })
            continue

        vts_final = pay["vts_final"]
        baseline_forecast = (vts_final - 50.0) / 5.0
        live_signal = sg_total / N_ROUNDS
        forecast_r4 = (1 - W_LIVE) * baseline_forecast + W_LIVE * live_signal

        # forecast_R4 alone is a per-round quality estimate -- it says nothing about
        # who is already ahead after 3 rounds. Win/top-finish probability requires
        # projecting the FINAL total (current total + projected R4 score), not just
        # round-4 quality in isolation; otherwise a player far ahead on the
        # leaderboard with a merely average round-4 forecast would incorrectly show
        # a near-zero win probability. baseline_r4_field converts the SG-relative
        # forecast_R4 back into an actual score-to-par using R3's field mean as the
        # round baseline (R4's own field mean isn't knowable pre-round).
        total_thru_r3 = p.get("total")
        projected_r4_score_to_par = baseline_r4_field - forecast_r4
        projected_final_total = (
            total_thru_r3 + projected_r4_score_to_par if total_thru_r3 is not None else None
        )

        own_scores = [p.get(f"r{n}") for n in (1, 2, 3)]
        if all(v is not None for v in own_scores):
            own_devs = [v - PAR for v in own_scores]
            own_mean = sum(own_devs) / len(own_devs)
            ind_var = sum((d - own_mean) ** 2 for d in own_devs) / len(own_devs)
        else:
            ind_var = field_var  # fallback; shouldn't occur for confirmed cut survivors

        w_ind = N_ROUNDS / (N_ROUNDS + SHRINKAGE_K)  # same K, same n -> equals W_LIVE
        blended_var = w_ind * ind_var + (1 - w_ind) * field_var
        volatility_index = math.sqrt(max(0.0, blended_var))

        rec = {
            "player_id": pid,
            "player_key": p.get("player_key"),
            "player_name": p.get("player_name"),
            "pre_event_rank": p.get("pre_event_rank"),
            "pre_event_tier": p.get("pre_event_tier"),
            "vts_final": vts_final,
            "total_thru_r3": total_thru_r3,
            "baseline_forecast": round(baseline_forecast, 4),
            "live_signal": round(live_signal, 4),
            "w_live": round(W_LIVE, 4),
            "forecast_R4": round(forecast_r4, 4),
            "projected_r4_score_to_par": round(projected_r4_score_to_par, 4),
            "projected_final_total": round(projected_final_total, 4) if projected_final_total is not None else None,
            "volatility_index": round(volatility_index, 4),
            "confidence_band": (
                [round(projected_final_total - volatility_index, 4), round(projected_final_total + volatility_index, 4)]
                if projected_final_total is not None else None
            ),
            "diagnostic_label": p.get("diagnostic_label"),
            "live_round_delta_tag": p.get("live_round_delta_tag"),
            "trace": {
                "baseline_forecast": round(baseline_forecast, 4),
                "live_signal": round(live_signal, 4),
                "w_live": round(W_LIVE, 4),
                "forecast_R4": round(forecast_r4, 4),
                "total_thru_r3": total_thru_r3,
                "projected_final_total": round(projected_final_total, 4) if projected_final_total is not None else None,
            },
        }
        records.append(rec)
        # Lower projected_final_total is better (golf scoring); negate so that higher
        # z-score consistently means "more likely to win," matching this codebase's
        # existing softmax convention (build_round_analysis.py: higher V_p(t) = better).
        proj_totals.append(projected_final_total if projected_final_total is not None else 0.0)

    # ---- Probability compression (z-score + reused temperature softmax) ----
    mu = sum(proj_totals) / len(proj_totals) if proj_totals else 0.0
    variance = sum((t - mu) ** 2 for t in proj_totals) / len(proj_totals) if proj_totals else 1.0
    sigma = max(1e-9, math.sqrt(variance))
    zs = [-(t - mu) / sigma for t in proj_totals]

    win = softmax_t(zs, LIVE_TEMPS["win"])
    top5 = softmax_t(zs, LIVE_TEMPS["top5"])
    top10 = softmax_t(zs, LIVE_TEMPS["top10"])
    top20 = softmax_t(zs, LIVE_TEMPS["top20"])

    for i in range(len(records)):
        top5[i] = max(top5[i], win[i])
        top10[i] = max(top10[i], top5[i])
        top20[i] = max(top20[i], top10[i])

    for i, rec in enumerate(records):
        rec["win_pct"] = round(win[i] * 100, 2)
        rec["top5_pct"] = round(top5[i] * 100, 2)
        rec["top10_pct"] = round(top10[i] * 100, 2)
        rec["top20_pct"] = round(top20[i] * 100, 2)

    records.sort(key=lambda r: -r["win_pct"])

    return {
        "schema_version": "r4_shrinkage_projection_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PRE-R4 PROJECTION -- R4 NOT YET PLAYED. Forward-looking estimate only, not a result artifact.",
        "event": {"name": "Rocket Classic", "course": "Detroit Golf Club", "year": 2026, "par": PAR},
        "methodology": {
            "mode": "shrinkage",
            "w_live": round(W_LIVE, 4),
            "shrinkage_k": SHRINKAGE_K,
            "n_rounds": N_ROUNDS,
            "live_signal_field": "sg_total_live (cut_survivors.sg_total / 3)",
            "conversion": "1 stroke ~= 5 VTS points, anchored at VTS mean 50 (build_round_analysis.py vs_proj heuristic, ~line 1613)",
            "baseline_r4_field_score_to_par": round(baseline_r4_field, 4),
            "baseline_r4_field_source": "r3_field_mean_today (freshest available round baseline; R4's own field mean isn't knowable pre-round)",
            "projection_step": (
                "forecast_R4 (shrinkage-blended SG/round quality) is converted to "
                "projected_r4_score_to_par = baseline_r4_field - forecast_R4, then "
                "projected_final_total = total_thru_r3 + projected_r4_score_to_par. "
                "This step is necessary, not optional: forecast_R4 alone measures "
                "only next-round quality and ignores standing already earned over 3 "
                "rounds -- win/top-finish probability must be driven by projected "
                "FINAL total, or a player far ahead on the leaderboard with a merely "
                "average round-4 forecast would incorrectly show near-zero win odds."
            ),
            "compression": (
                "z-score projected_final_total across field (sign-flipped so lower "
                "total = higher z, since lower score is better in golf), temperature-"
                "scaled softmax reused verbatim from build_round_analysis.py "
                "_LIVE_TEMPS (~line 1813); each bucket independently normalized to "
                "~100% (not scaled by slot count) -- matches this codebase's "
                "existing live-probability convention"
            ),
            "compression_temps": LIVE_TEMPS,
            "escalating_mode_status": (
                "not implemented or used anywhere in Rocket Classic's own pipeline; "
                "the shared root engine's escalating-softmax pattern "
                "(gamma = 3.5 x ROUND) is an independent feature used by other "
                "events only and is untouched by this script"
            ),
        },
        "assumptions_and_caveats": [
            "R4 has not been played; this is a forward-looking probabilistic estimate, not a result.",
            "VenueHistoryDelta and a formal gates/penalties framework are not implemented for this event; baseline_forecast uses vts_final (neutralSkillIndex + delta_fit + whatever ad-hoc penalties were already baked in pre-event) only.",
            "All player volatility estimates use n=3 live rounds, shrunk toward field variance via this project's own <8-round low-confidence threshold (K=8).",
            "Softmax temperatures are reused verbatim from the escalating-mode pipeline for consistency; they were calibrated for that pipeline's V_p(t) scale, not re-derived for shrinkage-mode inputs.",
            "Each probability bucket (win/top5/top10/top20) is independently normalized to sum to ~100% across the field, then monotonicity-clamped -- this matches the existing codebase's own convention, not a per-slot (500%/1000%/2000%) scaling.",
            "win/top-finish probabilities are computed from projected_final_total (current total + projected R4 score), not from forecast_R4 alone -- forecast_R4 in isolation only measures round-4 quality and ignores standing already earned over 3 rounds.",
        ],
        "field_summary": {
            "n_players_projected": len(records),
            "n_match_issues": len(match_issues),
            "field_var": round(field_var, 4),
            "field_sd": round(math.sqrt(field_var), 4),
            "probability_sum_checks": {
                "win_pct_sum": round(sum(r["win_pct"] for r in records), 2),
                "top5_pct_sum": round(sum(r["top5_pct"] for r in records), 2),
                "top10_pct_sum": round(sum(r["top10_pct"] for r in records), 2),
                "top20_pct_sum": round(sum(r["top20_pct"] for r in records), 2),
            },
        },
        "match_issues": match_issues,
        "players": records,
    }


def write_csv(output: dict, path: Path) -> None:
    """Flat, one-row-per-cut-survivor mirror of the JSON `players` array.

    Diagnostic artifact only -- never a write-back source for vts_full.csv or
    event_payload.json. Derived from the same `build()` output as the JSON, so the
    two files cannot drift out of sync with each other.
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in output["players"]:
            band = r.get("confidence_band") or [None, None]
            writer.writerow({
                "player_id": r["player_id"],
                "player_name": r["player_name"],
                "pre_event_rank": r["pre_event_rank"],
                "pre_event_tier": r["pre_event_tier"],
                "vts_final": r["vts_final"],
                "total_thru_r3": r["total_thru_r3"],
                "baseline_sg_per_round": r["baseline_forecast"],
                "live_sg_per_round_r1_r3": r["live_signal"],
                "w_live": r["w_live"],
                "forecast_sg_per_round_r4": r["forecast_R4"],
                "projected_r4_score_to_par": r["projected_r4_score_to_par"],
                "projected_final_total": r["projected_final_total"],
                "volatility_index": r["volatility_index"],
                "confidence_band_low": band[0],
                "confidence_band_high": band[1],
                "win_pct": r["win_pct"],
                "top5_pct": r["top5_pct"],
                "top10_pct": r["top10_pct"],
                "top20_pct": r["top20_pct"],
                "diagnostic_label": r["diagnostic_label"],
                "live_round_delta_tag": r["live_round_delta_tag"],
            })


def main() -> None:
    output = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    write_csv(output, OUT_CSV_PATH)

    fs = output["field_summary"]
    print("=== Rocket Classic R4 Shrinkage Projection ===")
    print(f"w_live = {W_LIVE:.4f}  (n={N_ROUNDS}, K={SHRINKAGE_K})")
    print(f"field_var = {fs['field_var']}  field_sd = {fs['field_sd']}")
    print(f"players projected: {fs['n_players_projected']}  match_issues: {fs['n_match_issues']}")
    print(f"probability sums: {fs['probability_sum_checks']}")

    riley = next((r for r in output["players"] if r["player_name"] == "Davis Riley"), None)
    if riley:
        print("\n--- Spot-check: Davis Riley (tournament leader thru R3) ---")
        print(f"  pre_event_rank={riley['pre_event_rank']} tier={riley['pre_event_tier']} vts_final={riley['vts_final']}")
        print(f"  baseline_forecast={riley['baseline_forecast']}  live_signal={riley['live_signal']}")
        print(f"  forecast_R4={riley['forecast_R4']}  volatility_index={riley['volatility_index']}")
        print(f"  total_thru_r3={riley['total_thru_r3']}  projected_r4_score_to_par={riley['projected_r4_score_to_par']}")
        print(f"  projected_final_total={riley['projected_final_total']}  band={riley['confidence_band']}")
        print(f"  win_pct={riley['win_pct']}  top5_pct={riley['top5_pct']}  top10_pct={riley['top10_pct']}  top20_pct={riley['top20_pct']}")

    print("\n--- Top 5 by win_pct ---")
    for r in output["players"][:5]:
        print(f"  {r['win_pct']:5.2f}%  {r['player_name']:<24} total_thru_r3={r['total_thru_r3']:>5}  proj_final={r['projected_final_total']:>7}")

    print(f"\nWritten to: {OUT_PATH}")
    print(f"          and: {OUT_CSV_PATH}")


if __name__ == "__main__":
    main()
