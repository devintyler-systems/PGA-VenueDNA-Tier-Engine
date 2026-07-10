"""
VenueDNA — 2026 Genesis Scottish Open
build_round_analysis.py

Compiles live round CSVs + pre-tournament payload into r{N}_analysis.json (schema v1.1).
Produces: trait_audit.app_150_200 node + live_lean_notes with no null entries.

Usage:
    python engine/build_round_analysis.py --round 1 --event_slug 2026_genesis_scottish_open
"""

import argparse
import csv
import json
import os
import sqlite3
import unicodedata
import latent_model
import traits_calculator
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_PAYLOAD = ROOT / "deploy" / "data" / "event_payload.json"
DB_PATH = ROOT.parents[1] / "data" / "venuedna_master.db"


# ─────────────────────────────────────────────
# NAME NORMALISATION
# ─────────────────────────────────────────────

def _strip_accents(name: str) -> str:
    nfd = unicodedata.normalize("NFD", name)
    out = "".join(c for c in nfd if not unicodedata.combining(c))
    for k, v in {"Ø": "O", "ø": "O", "Æ": "AE", "æ": "AE",
                  "Å": "A", "å": "A", "Ö": "O", "ö": "O",
                  "Ü": "U", "ü": "U", "Ñ": "N", "ñ": "N", "ß": "SS"}.items():
        out = out.replace(k, v)
    return out.upper()


def _alpha_only(s: str) -> str:
    return "".join(c for c in s if c.isalpha() or c == " ").strip()


def normalize(s: str) -> str:
    return _alpha_only(_strip_accents(str(s)))


def key_first_last(full_name: str) -> str:
    """'Tom Kim' or 'Si Woo Kim' → 'KIM|TOM' / 'KIM|SI WOO'"""
    parts = normalize(full_name).split()
    if not parts:
        return "|"
    if len(parts) == 1:
        return f"{parts[0]}|"
    return f"{parts[-1]}|{' '.join(parts[:-1])}"


def key_last_first(raw: str) -> str:
    """'Kim, Tom' → 'KIM|TOM'"""
    if "," in raw:
        last, first = raw.split(",", 1)
        return f"{normalize(last.strip())}|{normalize(first.strip())}"
    return f"{normalize(raw)}|"


def key_payload(p: dict) -> str:
    return f"{normalize(p.get('last_name', ''))}|{normalize(p.get('first_name', ''))}"


def lkey_to_norm_name(lkey: str) -> str:
    """Convert pipe-delimited join key to strict lowercase snake_case norm_name.

    Spaces in both last and first parts become underscores so the output is
    always pure snake_case with no embedded whitespace:

      'HOJGAARD|RASMUS'    → 'hojgaard_rasmus'
      'KIM|SI WOO'         → 'kim_si_woo'
      'VAN ROOYEN|ERIK'    → 'van_rooyen_erik'
    """
    parts = lkey.split("|", 1)
    last  = parts[0].lower().replace(" ", "_")
    first = parts[1].lower().replace(" ", "_") if len(parts) > 1 and parts[1] else ""
    return f"{last}_{first}" if first else last


# ─────────────────────────────────────────────
# SAFE PARSERS
# ─────────────────────────────────────────────

def to_float(v, default: float = 0.0) -> float:
    try:
        s = str(v).strip()
        if s in ("", "null", "None", "N/A"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def to_int(v, default: int = 0) -> int:
    try:
        return int(str(v).strip().replace("+", ""))
    except (ValueError, TypeError):
        return default


def score_to_int(v) -> int:
    """'-5' → -5, 'E' → 0, '+3' → 3"""
    s = str(v).strip()
    if s in ("E", "EVEN", ""):
        return 0
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def pos_to_int(pos: str) -> int:
    try:
        return int(str(pos).replace("T", "").strip())
    except (ValueError, TypeError):
        return 999


# ─────────────────────────────────────────────
# DB CACHE + STATS HELPERS
# ─────────────────────────────────────────────

def load_db_brie_cache(event_slug_fragment: str) -> dict[str, float]:
    """Load brie_score from active_field_projections keyed by normalized last_first."""
    cache: dict[str, float] = {}
    if not DB_PATH.exists():
        return cache
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "SELECT player_name, brie_score FROM active_field_projections "
            "WHERE event_dir LIKE ?",
            (f"%{event_slug_fragment}%",),
        )
        for player_name, brie_score in cur.fetchall():
            if brie_score is not None:
                cache[key_last_first(player_name)] = float(brie_score)
        conn.close()
    except sqlite3.Error:
        pass
    return cache


def _spearman_rho(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    def _ranks(lst: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: lst[i])
        r = [0.0] * n
        for rank, idx in enumerate(order, 1):
            r[idx] = float(rank)
        return r
    rx, ry = _ranks(x), _ranks(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return round(1.0 - 6.0 * d2 / (n * (n * n - 1)), 4)


# ─────────────────────────────────────────────
# CUMULATIVE SG ACCUMULATION
# ─────────────────────────────────────────────

_SG_DIMS = ("sg_app", "sg_ott", "sg_arg", "sg_putt")


def accumulate_sg_by_round(round_num: int) -> dict[str, dict[str, float]]:
    """Sum per-player SG per dimension across rounds 1..round_num, keyed by lkey.

    Reads both player_strokes_gained.csv (SG column headers) and
    course_insights.csv (sg_* column headers) for each round and unions
    the player sets, so late entrants and partial-data rounds are included.
    """
    cumulative: dict[str, dict[str, float]] = {}
    for r in range(1, round_num + 1):
        r_dir   = ROOT / "output" / f"round{r}"
        sg_path = r_dir / f"round{r}_player_strokes_gained.csv"
        ci_path = r_dir / f"round{r}_course_insights.csv"
        sg_by_key: dict[str, dict] = {}
        ci_by_key: dict[str, dict] = {}
        if sg_path.exists():
            with open(sg_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    sg_by_key[key_first_last(row["Player"])] = row
        if ci_path.exists():
            with open(ci_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    ci_by_key[key_last_first(row["player_name"])] = row
        for lkey in set(sg_by_key) | set(ci_by_key):
            sg  = sg_by_key.get(lkey, {})
            ci  = ci_by_key.get(lkey, {})
            ent = cumulative.setdefault(lkey, {d: 0.0 for d in _SG_DIMS})
            ent["sg_app"]  += to_float(sg.get("sg-app to green") or ci.get("sg_app"))
            ent["sg_ott"]  += to_float(sg.get("sg-ott")          or ci.get("sg_ott"))
            ent["sg_arg"]  += to_float(ci.get("sg_arg"))
            ent["sg_putt"] += to_float(sg.get("sg-putting")      or ci.get("sg_putt"))
    return cumulative


# ─────────────────────────────────────────────
# CORE BUILD
# ─────────────────────────────────────────────

def build(round_num: int, event_slug: str, adj_weights: dict[str, float]) -> dict:
    round_key = f"round{round_num}"
    r_dir = ROOT / "output" / f"round{round_num}"

    # ── Pre-tournament payload ────────────────────────────────────
    with open(DEPLOY_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)

    pp_by_key = {key_payload(p): p for p in payload["players"]}

    # ── Live CSVs ─────────────────────────────────────────────────
    with open(r_dir / f"{round_key}_leaderboard.csv", encoding="utf-8") as f:
        lb_rows = list(csv.DictReader(f))

    with open(r_dir / f"{round_key}_player_strokes_gained.csv", encoding="utf-8") as f:
        sg_rows = list(csv.DictReader(f))
    sg_by_key = {key_first_last(r["Player"]): r for r in sg_rows}

    with open(r_dir / f"{round_key}_course_insights.csv", encoding="utf-8") as f:
        ci_rows = list(csv.DictReader(f))
    ci_by_key = {key_last_first(r["player_name"]): r for r in ci_rows}

    with open(r_dir / f"{round_key}_course_stats.csv", encoding="utf-8") as f:
        cs_rows = list(csv.DictReader(f))

    # ── Leaderboard ───────────────────────────────────────────────
    leaderboard = []
    for row in lb_rows:
        name = row["Player"]
        lkey = key_first_last(name)
        pp = pp_by_key.get(lkey, {})
        sg = sg_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        live_sg_ott = to_float(sg.get("sg-ott") or ci.get("sg_ott"))
        live_sg_app = to_float(sg.get("sg-app to green") or ci.get("sg_app"))
        live_sg_putt = to_float(sg.get("sg-putting") or ci.get("sg_putt"))
        live_sg_arg = to_float(ci.get("sg_arg"))
        live_sg_total = to_float(sg.get("sg-total") or ci.get("sg_total"))

        leaderboard.append({
            "position":            row["POS"],
            "player":              name,
            "player_key":          lkey,
            "score_r1":            score_to_int(row["R1"]),
            "strokes":             to_int(row.get("STROKES", "0")),
            "pre_tier":            int(pp["tier"]) if pp.get("tier") is not None else None,
            "pre_vts":             round(to_float(pp.get("vts_final")), 2) if pp else None,
            "scoring_band":        pp.get("scoring", {}).get("band") if pp else None,
            "pre_win_prob":        round(to_float(pp.get("win_prob")), 4) if pp else None,
            "pre_make_cut_prob":   round(to_float(pp.get("make_cut_prob")), 4) if pp else None,
            "live_sg_total":       round(live_sg_total, 3),
            "live_sg_ott":         round(live_sg_ott, 3),
            "live_sg_app":         round(live_sg_app, 3),
            "live_sg_putt":        round(live_sg_putt, 3),
            "live_sg_arg":         round(live_sg_arg, 3),
            "live_distance":       round(to_float(ci.get("distance")), 1),
            "live_accuracy":       round(to_float(ci.get("accuracy")), 4),
            "live_gir":            round(to_float(ci.get("gir")), 4),
        })

    # ── DB brie cache + field-mean imputation anchors ─────────────────────
    db_cache = load_db_brie_cache("GenesisScottishOpen")
    brie_vals = list(db_cache.values())
    active_field_mean_brie = sum(brie_vals) / len(brie_vals) if brie_vals else 0.0

    vts_vals = [to_float(p.get("vts_final")) for p in pp_by_key.values()
                if to_float(p.get("vts_final")) > 0.0]
    active_field_mean_vts = sum(vts_vals) / len(vts_vals) if vts_vals else 50.0

    # ── Snap entries — current-round data skeleton ────────────────────────────
    snap_entries = []
    for row in lb_rows:
        name = row["Player"]
        lkey = key_first_last(name)
        pp   = pp_by_key.get(lkey, {})
        sg   = sg_by_key.get(lkey, {})
        ci   = ci_by_key.get(lkey, {})

        # DB join: use brie_score as canonical pre-tournament BRIE baseline.
        # Late entries / missing players fall back to active field mean.
        db_brie  = db_cache.get(lkey)
        baseline = db_brie if db_brie is not None else active_field_mean_brie

        pt_vts_raw = to_float(pp.get("vts_final")) if pp else 0.0
        pt_vts_val = pt_vts_raw if pt_vts_raw > 0.0 else active_field_mean_vts

        snap_entries.append({
            "name":       name,
            "lkey":       lkey,
            "pos_str":    row["POS"],
            "score":      score_to_int(row["R1"]),
            "baseline":   baseline,
            "pt_vts":     round(pt_vts_val, 2),
            "pt_rank":    int(pp["rank"]) if pp.get("rank") is not None else None,
            "pt_tier":    int(pp["tier"]) if pp.get("tier") is not None else None,
            "in_payload": bool(pp),
            "sg_tot":     to_float(sg.get("sg-total") or ci.get("sg_total")),
            "pp": pp, "sg": sg, "ci": ci,
        })

    # ── Multi-dimension cumulative SG accumulation ────────────────────────────
    # Sum each SG dimension across rounds 1..round_num for every player.
    # Field averages anchor to the active leaderboard field only.
    cum_sg_all = accumulate_sg_by_round(round_num)
    cum_sg_per_player = [
        cum_sg_all.get(se["lkey"], {d: 0.0 for d in _SG_DIMS})
        for se in snap_entries
    ]
    field_avg_sg: dict[str, float] = {
        dim: (sum(c[dim] for c in cum_sg_per_player) / len(cum_sg_per_player)
              if cum_sg_per_player else 0.0)
        for dim in _SG_DIMS
    }

    # ── Dimension-specific V_p(t) modulation ─────────────────────────────────
    # V_p(t) = V_p_baseline + Σ_s (0.35 * round * w_s) * (cumulative_sg_proxy_{p,s} - field_avg_sg_proxy_s)
    modulated, z_scores, prob_dicts = latent_model.dimension_modulate(
        baselines    = [se["baseline"] for se in snap_entries],
        cum_sg       = cum_sg_per_player,
        field_avg_sg = field_avg_sg,
        adj_weights  = adj_weights,
        proxy_map    = traits_calculator.SG_PROXY_MAP,
        round_num    = round_num,
    )

    leaderboard_snapshot = []
    for i, se in enumerate(snap_entries):
        probs  = latent_model.enforce_monotonicity(prob_dicts[i])
        pp     = se["pp"]; sg = se["sg"]; ci = se["ci"]
        cum_sg = cum_sg_per_player[i]

        live_sg_app = to_float(sg.get("sg-app to green") or ci.get("sg_app"))

        # app_150_200_fw_sg: pre-tournament 150-200yd fairway SG projection from payload.
        # Debut / late-entry players missing from payload fall back to the round's sg_app.
        _fw_sg_raw = pp.get("app_150_200_value") if pp else None
        app_150_200_fw_sg = (
            round(to_float(_fw_sg_raw), 4) if _fw_sg_raw is not None
            else round(live_sg_app, 3)
        )

        # app_150_200_poor_shot_avoidance: rough-from-150+ SG proxy from payload.
        # Captures historical tendency to avoid rough in the 150-200yd approach zone.
        # Falls back to 0.0 when no historical baseline exists.
        _psa_raw = pp.get("rough_over150_value") if pp else None
        app_150_200_poor_shot_avoidance = (
            round(to_float(_psa_raw), 4) if _psa_raw is not None else 0.0
        )

        leaderboard_snapshot.append({
            "r1_pos":             pos_to_int(se["pos_str"]),
            "r1_pos_str":         se["pos_str"],
            "r1_name":            se["name"],
            "norm_name":          lkey_to_norm_name(se["lkey"]),
            "r1_score":           se["score"],
            "pt_rank":            se["pt_rank"],
            "pt_tier":            se["pt_tier"],
            "pt_vts":             se["pt_vts"],
            "brie_z_score":       round(float(z_scores[i]), 4),
            "v_p_t":              round(float(modulated[i]), 4),
            "cumulative_sg_app":  round(cum_sg["sg_app"],  3),
            "cumulative_sg_ott":  round(cum_sg["sg_ott"],  3),
            "cumulative_sg_arg":  round(cum_sg["sg_arg"],  3),
            "cumulative_sg_putt": round(cum_sg["sg_putt"], 3),
            "win_pct":      float(probs["win_pct"]),
            "top5_pct":     float(probs["top5_pct"]),
            "top10_pct":    float(probs["top10_pct"]),
            "top20_pct":    float(probs["top20_pct"]),
            "live_win_pct": round(float(probs["win_pct"]) / 100.0, 6),
            "sg_app":  round(live_sg_app, 3),
            "sg_putt": round(to_float(sg.get("sg-putting")      or ci.get("sg_putt")), 3),
            "sg_arg":  round(to_float(ci.get("sg_arg")),  3),
            "sg_ott":  round(to_float(sg.get("sg-ott")   or ci.get("sg_ott")),  3),
            "app_150_200_fw_sg":               app_150_200_fw_sg,
            "app_150_200_poor_shot_avoidance": app_150_200_poor_shot_avoidance,
        })

    # ── Model performance + metadata ──────────────────────────────────────
    ranked_pairs = [(se["pt_rank"], pos_to_int(se["pos_str"]))
                    for se in snap_entries if se["pt_rank"] is not None]
    spearman_rho = _spearman_rho(
        [p[0] for p in ranked_pairs], [p[1] for p in ranked_pairs]
    )

    tier_group_defs = [("tier_1", [1]), ("tier_2", [2]), ("tier_3", [3]), ("tier_4_5", [4, 5])]
    groups: dict = {}
    for gkey, tier_nums in tier_group_defs:
        members = [se for se in snap_entries if se["pt_tier"] in tier_nums]
        if members:
            positions = [pos_to_int(se["pos_str"]) for se in members]
            groups[gkey] = {
                "n":          len(members),
                "in_r1_top10": sum(1 for pos in positions if pos <= 10),
                "avg_r1_pos":  round(sum(positions) / len(positions), 1),
            }

    model_performance = {"spearman_rho": spearman_rho, "groups": groups}

    matched   = sum(1 for se in snap_entries if se["in_payload"])
    unmatched = [se["name"] for se in snap_entries if not se["in_payload"]]
    match_summary = {"matched": matched, "total_r1": len(lb_rows), "unmatched": unmatched}

    _build_ts = int(datetime.now().timestamp())
    metadata = {
        "round":             round_num,
        "round_label":       f"Round {round_num}",
        "course_name":       "The Renaissance Club",
        "par":               71,
        "is_final":          False,
        "cache_fingerprint": f"{_build_ts}_{round_num}",
    }

    # ── Course stats ──────────────────────────────────────────────
    holes = []
    for r in cs_rows:
        holes.append({
            "hole":      to_int(r["HOLE"]),
            "par":       to_int(r["PAR"]),
            "yards":     to_int(r["YARDS"]),
            "avg_score": round(to_float(r["AVG"]), 3),
            "vs_par":    round(to_float(r["+/-"]), 3),
            "eagles":    to_int(r.get("EAGLES", 0)),
            "birdies":   to_int(r.get("BIRDIES", 0)),
            "pars":      to_int(r.get("PARS", 0)),
            "bogeys":    to_int(r.get("BOGEYS", 0)),
            "dbl_plus":  to_int(r.get("DBL+", 0)),
        })

    hardest_holes = sorted(holes, key=lambda h: h["vs_par"], reverse=True)[:3]
    easiest_holes = sorted(holes, key=lambda h: h["vs_par"])[:3]
    field_vs_par_r1 = round(sum(h["vs_par"] for h in holes), 3)
    strokes_list = [to_int(r.get("STROKES", 0)) for r in lb_rows if r.get("STROKES")]
    field_avg_strokes = round(sum(strokes_list) / len(strokes_list), 2) if strokes_list else 70.0

    course_stats = {
        "holes": holes,
        "summary": {
            "field_vs_par_r1":   field_vs_par_r1,
            "field_avg_strokes": field_avg_strokes,
            "hardest_holes":     [{"hole": h["hole"], "vs_par": h["vs_par"]} for h in hardest_holes],
            "easiest_holes":     [{"hole": h["hole"], "vs_par": h["vs_par"]} for h in easiest_holes],
        },
    }

    # ── Trait Audit: app_150_200 ──────────────────────────────────
    # Compare pre-tournament 150-200 yd fairway approach value projection
    # against live R1 SG:APP as a proxy for zone confirmation.
    audit_rows = []
    for lb in lb_rows:
        name = lb["Player"]
        lkey = key_first_last(name)
        pp = pp_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        raw_pre = pp.get("app_150_200_value") if pp else None
        pre_val = to_float(raw_pre) if raw_pre is not None else 0.0
        has_pre_data = raw_pre is not None

        live_sg_app = to_float(ci.get("sg_app"))
        live_gir = to_float(ci.get("gir"))
        prox_raw = ci.get("prox_fw", "")
        live_prox_fw = to_float(prox_raw) if prox_raw not in ("", "null", "None") else 0.0

        delta = round(live_sg_app - pre_val, 3)

        if has_pre_data and pre_val > 1.5 and live_sg_app > 1.5:
            status = "CONFIRMING"
        elif has_pre_data and pre_val > 1.5 and live_sg_app <= 0.5:
            status = "DIVERGING"
        elif has_pre_data and pre_val <= 0.5 and live_sg_app > 1.5:
            status = "OUTPERFORMING"
        elif has_pre_data and pre_val <= -1.0 and live_sg_app <= 0.0:
            status = "AS_PROJECTED"
        else:
            status = "TRACKING"

        audit_rows.append({
            "player":              name,
            "position":            lb["POS"],
            "has_pre_data":        has_pre_data,
            "pre_app_150_200":     round(pre_val, 3),
            "live_sg_app":         round(live_sg_app, 3),
            "delta":               delta,
            "live_gir":            round(live_gir, 4),
            "live_prox_fw":        round(live_prox_fw, 2),
            "status":              status,
        })

    # Summary stats
    with_pre = [r for r in audit_rows if r["has_pre_data"]]
    avg_pre = round(sum(r["pre_app_150_200"] for r in with_pre) / len(with_pre), 3) if with_pre else 0.0
    avg_live = round(sum(r["live_sg_app"] for r in audit_rows) / len(audit_rows), 3) if audit_rows else 0.0
    status_counts = {}
    for r in audit_rows:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    top5_app = sorted(audit_rows, key=lambda r: r["live_sg_app"], reverse=True)[:5]
    bottom5_app = sorted(audit_rows, key=lambda r: r["live_sg_app"])[:5]

    # ── Canonical trait signal metrics (Schema v1.1) ──────────────────────
    import math as _math

    def _safe_bz(v: object) -> float | None:
        try:
            f = float(v)  # type: ignore[arg-type]
            return f if _math.isfinite(f) else None
        except (TypeError, ValueError):
            return None

    _all_bz   = [x for x in (_safe_bz(s["brie_z_score"]) for s in leaderboard_snapshot) if x is not None]
    _top10_bz = [x for x in (_safe_bz(s["brie_z_score"]) for s in leaderboard_snapshot
                              if s.get("r1_pos", 999) <= 10) if x is not None]

    field_trait_avg = round(sum(_all_bz)   / len(_all_bz),   4) if _all_bz   else 0.0
    top10_trait_avg = round(sum(_top10_bz) / len(_top10_bz), 4) if _top10_bz else 0.0
    trait_delta     = round(top10_trait_avg - field_trait_avg, 4)

    # Z-score proxy trait (brie_z_score is σ-normalised): use SD-scale thresholds.
    # Legacy percentage fields would use >= 6.0 / >= 2.0 / < -3.0 boundaries instead.
    if trait_delta >= 1.0:
        signal = "validated"
    elif trait_delta >= 0.40:
        signal = "mixed"
    elif trait_delta >= -0.40:
        signal = "neutral"
    else:
        signal = "weak"

    trait_audit = {
        "app_150_200": {
            "description": (
                "Pre-tournament 150-200 yd fairway approach projection (app_150_200_value) "
                "vs live R1 SG:APP. Positive delta = outperforming projection."
            ),
            "venue_weight":      0.06,
            "sg_proxy":          "sg_app",
            "top10_trait_avg":   top10_trait_avg,
            "field_trait_avg":   field_trait_avg,
            "trait_delta":       trait_delta,
            "signal":            signal,
            "source_confidence": "proxy-confirmed",
            "field_summary": {
                "total_players_audited":    len(audit_rows),
                "players_with_pre_data":    len(with_pre),
                "avg_pre_app_150_200":      avg_pre,
                "avg_live_sg_app_r1":       avg_live,
                "status_distribution":      status_counts,
            },
            "top5_live_sg_app":    [{"player": r["player"], "position": r["position"],
                                      "live_sg_app": r["live_sg_app"], "status": r["status"]}
                                     for r in top5_app],
            "bottom5_live_sg_app": [{"player": r["player"], "position": r["position"],
                                      "live_sg_app": r["live_sg_app"], "status": r["status"]}
                                     for r in bottom5_app],
            "confirming":    [r for r in audit_rows if r["status"] == "CONFIRMING"],
            "diverging":     [r for r in audit_rows if r["status"] == "DIVERGING"],
            "outperforming": [r for r in audit_rows if r["status"] == "OUTPERFORMING"],
            "all_players":   audit_rows,
        }
    }

    # ── Live Lean Notes ───────────────────────────────────────────
    # One note per leaderboard player — no null entries.
    _notes_list = []

    for lb in lb_rows:
        name = lb["Player"]
        lkey = key_first_last(name)
        pos = lb["POS"]
        pos_num = pos_to_int(pos)
        score_r1 = score_to_int(lb["R1"])
        pp = pp_by_key.get(lkey, {})
        sg = sg_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        tier = int(pp["tier"]) if pp.get("tier") is not None else 5
        vts = round(to_float(pp.get("vts_final")), 2) if pp else 0.0
        band = pp.get("scoring", {}).get("band", "Unranked") if pp else "Unranked"

        live_sg_total = to_float(sg.get("sg-total") or ci.get("sg_total"))
        live_sg_ott = to_float(sg.get("sg-ott") or ci.get("sg_ott"))
        live_sg_app = to_float(sg.get("sg-app to green") or ci.get("sg_app"))
        live_sg_putt = to_float(sg.get("sg-putting") or ci.get("sg_putt"))

        # Identify strongest live weapon
        sg_map = {"OTT": live_sg_ott, "APP": live_sg_app, "PUTT": live_sg_putt}
        best_cat, best_val = max(sg_map.items(), key=lambda x: x[1])

        if tier <= 2 and pos_num <= 10:
            note = (f"T{tier} conviction confirming — SG:{best_cat} leading at "
                    f"{best_val:+.2f}, vying for weekend contention ({band})")
        elif tier <= 2 and pos_num <= 25:
            note = (f"T{tier} pick tracking inside cut window — SG:TOTAL {live_sg_total:+.2f}, "
                    f"{band} band holds; R2 pivot opportunity")
        elif tier <= 2 and pos_num <= 60:
            note = (f"T{tier} high-conviction pick lagging — SG:APP {live_sg_app:+.2f} below "
                    f"projection, {band} band at risk; watch R2 approach metrics")
        elif tier <= 2:
            note = (f"T{tier} selection struggling below cut line — SG:TOTAL {live_sg_total:+.2f}; "
                    f"R2 recovery required; pre-tournament conviction under pressure")
        elif tier == 3 and pos_num <= 10:
            note = (f"T3 mid-field entry exceeding pre-tournament ceiling — "
                    f"SG:TOTAL {live_sg_total:+.2f} / SG:{best_cat} {best_val:+.2f} driving surprise placement")
        elif tier == 3 and pos_num <= 30:
            note = (f"T3 value pick activating within expected range — "
                    f"SG:TOTAL {live_sg_total:+.2f}, {band} band confirming")
        elif tier >= 4 and pos_num <= 15:
            note = (f"Low-tier entry outperforming projection — "
                    f"SG:{best_cat} {best_val:+.2f} leading a {score_r1:+d} R1; tier breakout watch")
        elif pos_num <= 50:
            note = (f"Mid-pack positioning within {band} band projection — "
                    f"SG:TOTAL {live_sg_total:+.2f} tracking; no major drift from baseline")
        elif pos_num <= 80:
            note = (f"Below-average R1 — SG:TOTAL {live_sg_total:+.2f}; "
                    f"cut survival conditional on R2 correction in SG:{best_cat}")
        else:
            note = (f"Struggling toward cut line — SG:TOTAL {live_sg_total:+.2f} ({score_r1:+d}); "
                    f"R2 must improve SG:APP ({live_sg_app:+.2f}) to survive")

        _notes_list.append({
            "player":        name,
            "position":      pos,
            "score_r1":      score_r1,
            "pre_tier":      tier,
            "pre_vts":       vts,
            "scoring_band":  band,
            "live_sg_total": round(live_sg_total, 3),
            "live_sg_ott":   round(live_sg_ott, 3),
            "live_sg_app":   round(live_sg_app, 3),
            "live_sg_putt":  round(live_sg_putt, 3),
            "note":          note,
        })

    # ── watch_next_round: latent-delta trajectory flags ──────────────────────
    # ΔV_p = V_p(t) − V_p_baseline.
    # 'slippage'   — Top 15 AND ΔV_p < −3.0: rank floated on un-modeled noise.
    # 'sustainable' — Top 15 AND ΔV_p ≥ +2.5: position is course-fit backed.
    watch_next_round = []
    for i, se in enumerate(snap_entries):
        pos_num = pos_to_int(se["pos_str"])
        if pos_num > 15:
            continue
        delta_vp = modulated[i] - se["baseline"]
        if delta_vp < -3.0:
            watch_next_round.append({
                "player":    se["name"],
                "position":  se["pos_str"],
                "delta_v_p": round(delta_vp, 4),
                "flag_type": "slippage",
            })
        elif delta_vp >= 2.5:
            watch_next_round.append({
                "player":    se["name"],
                "position":  se["pos_str"],
                "delta_v_p": round(delta_vp, 4),
                "flag_type": "sustainable",
            })

    live_lean_notes = {
        "notes":                 _notes_list,
        "watch_next_round":      watch_next_round,
        "wave_risk_annotation":  [],
        "wave_scoring_averages": {},
    }

    # ── Assemble output ───────────────────────────────────────────
    return {
        "schema_version":       "1.1",
        "event_slug":           event_slug,
        "round":                round_num,
        "generated_date":       date.today().isoformat(),
        "build_timestamp":      datetime.now().isoformat(timespec="seconds"),
        "field_size":           len(lb_rows),
        "population_anchor_size": len(db_cache),
        "active_field_size":    len(lb_rows),
        "metadata":             metadata,
        "model_performance":    model_performance,
        "match_summary":        match_summary,
        "leaderboard":          leaderboard,
        "leaderboard_snapshot": leaderboard_snapshot,
        "course_stats":         course_stats,
        "trait_audit":          trait_audit,
        "live_lean_notes":      live_lean_notes,
    }


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate(doc: dict) -> list[str]:
    errors = []

    if doc.get("schema_version") != "1.1":
        errors.append(f"schema_version mismatch: {doc.get('schema_version')!r}")

    app_node = doc.get("trait_audit", {}).get("app_150_200")
    if not app_node:
        errors.append("trait_audit.app_150_200 node missing or empty")
    else:
        if not app_node.get("all_players"):
            errors.append("trait_audit.app_150_200.all_players is empty")
        if not app_node.get("field_summary"):
            errors.append("trait_audit.app_150_200.field_summary missing")

    lean_container = doc.get("live_lean_notes", {})
    notes_list = lean_container.get("notes", []) if isinstance(lean_container, dict) else lean_container
    if not notes_list:
        errors.append("live_lean_notes.notes is empty")
    else:
        null_notes = [i for i, n in enumerate(notes_list) if n is None]
        if null_notes:
            errors.append(f"live_lean_notes.notes has null entries at indices: {null_notes}")
        blank_notes = [n.get("player", "?") for n in notes_list if n and not n.get("note")]
        if blank_notes:
            errors.append(f"live_lean_notes.notes entries missing note field: {blank_notes[:5]}")
    if "watch_next_round" not in lean_container:
        errors.append("live_lean_notes.watch_next_round key missing")

    return errors


# ─────────────────────────────────────────────
# ATOMIC TRANSACTION
# ─────────────────────────────────────────────

class CriticalTransactionFailure(Exception):
    pass


def build_cumulative(existing: dict, doc: dict, round_num: int) -> dict:
    """Merge this round's summary into the cumulative learning record."""
    app = doc["trait_audit"]["app_150_200"]["field_summary"]
    prior = [s for s in existing.get("round_summaries", []) if s.get("round") != round_num]
    prior.append({
        "round":               round_num,
        "generated_date":      doc["generated_date"],
        "field_size":          doc["field_size"],
        "avg_live_sg_app_r1":  app["avg_live_sg_app_r1"],
        "status_distribution": app["status_distribution"],
    })
    prior.sort(key=lambda s: s["round"])

    # ── per_round: object-keyed navigation index (string round → entry) ──────
    # Keyed by str(round_num) so JS can do per_round['1'], per_round['2'], etc.
    # Idempotent: assignment overwrites any existing key for this round cleanly.
    per_round: dict = {k: dict(v) for k, v in existing.get("per_round", {}).items()}
    per_round[str(round_num)] = {
        "round":               round_num,
        "generated_at":        doc["build_timestamp"],
        "generated_date":      doc["generated_date"],
        "field_size":          doc["field_size"],
        "spearman_rho":        doc["model_performance"]["spearman_rho"],
        "avg_live_sg_app_r1":  app["avg_live_sg_app_r1"],
        "status_distribution": app["status_distribution"],
    }

    # Merge trait signals from this round into the running cumulative_signals ledger.
    signals: dict = {k: dict(v) for k, v in existing.get("cumulative_signals", {}).items()}
    for trait_key, trait_data in doc.get("trait_audit", {}).items():
        if not isinstance(trait_data, dict):
            continue
        signal = trait_data.get("signal")
        if signal is None:
            continue
        prev = signals.get(trait_key, {})
        # Idempotent: strip any existing entry for this round so rebuilds
        # don't double-count, then append and re-sort by round number.
        prior_obs = [o for o in prev.get("rounds_observed", [])
                     if o.get("round") != round_num]
        prior_obs.append({"round": round_num, "signal": signal})
        prior_obs.sort(key=lambda o: o["round"])
        signals[trait_key] = {
            "consensus":       signal,
            "last_signal":     signal,
            "rounds_seen":     len(prior_obs),
            "rounds_observed": prior_obs,
        }

    return {
        "event_slug":         doc["event_slug"],
        "rounds_completed":   round_num,
        "cumulative_signals": signals,
        "round_summaries":    prior,
        "per_round":          per_round,
    }


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--event_slug", type=str, required=True)
    args = ap.parse_args()

    print(f"Building R{args.round} analysis for {args.event_slug} …")

    # ── Bayesian weight recalibration (reads prior cumulative_learning.json) ──
    adj_weights = traits_calculator.load_adjusted_weights(target_round=args.round)
    print(f"  weights          : {traits_calculator.describe_adjustment(adj_weights)}")

    try:
        doc = build(args.round, args.event_slug, adj_weights)
    except FileNotFoundError as exc:
        print(f"\n  No round data found for R{args.round}: {exc.filename}")
        print("  Bayesian prior recalibration module loaded and verified.")
        raise SystemExit(0)

    errors = validate(doc)
    if errors:
        print("\nVALIDATION FAILURES:")
        for e in errors:
            print(f"  ✗ {e}")
        raise SystemExit(1)

    # ── Paths ──────────────────────────────────────────────────────────────────
    round_dir   = ROOT / "output" / f"round{args.round}"
    final_round = round_dir / f"r{args.round}_analysis.json"
    final_cumul = ROOT / "output" / "cumulative_learning.json"
    tmp_round   = round_dir / f"r{args.round}_analysis.json.tmp"
    tmp_cumul   = ROOT / "output" / "cumulative_learning.json.tmp"

    # ── Load any existing cumulative record ────────────────────────────────────
    existing_cumul: dict = {}
    if final_cumul.exists():
        with open(final_cumul, encoding="utf-8") as f:
            existing_cumul = json.load(f)

    cumulative = build_cumulative(existing_cumul, doc, args.round)

    # ── Step 1 & 2: Write both payloads to staging files ──────────────────────
    tmp_round.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_cumul.write_text(json.dumps(cumulative, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Step 3: Atomic verification gate ──────────────────────────────────────
    try:
        staged_round = json.loads(tmp_round.read_text(encoding="utf-8"))
        staged_cumul = json.loads(tmp_cumul.read_text(encoding="utf-8"))
        if staged_cumul.get("rounds_completed") != args.round:
            raise CriticalTransactionFailure(
                f"rounds_completed desync: staged={staged_cumul.get('rounds_completed')!r}, "
                f"expected={args.round}"
            )
        if staged_round.get("round") != args.round:
            raise CriticalTransactionFailure(
                f"round field desync in r{args.round}_analysis.json.tmp: "
                f"got={staged_round.get('round')!r}"
            )
    except CriticalTransactionFailure:
        tmp_round.unlink(missing_ok=True)
        tmp_cumul.unlink(missing_ok=True)
        raise
    except (json.JSONDecodeError, OSError) as exc:
        tmp_round.unlink(missing_ok=True)
        tmp_cumul.unlink(missing_ok=True)
        raise CriticalTransactionFailure(f"Staging file parse failed: {exc}") from exc

    # ── Step 4: Atomic commit with rollback recovery ──────────────────────────
    # Snapshot the live cumulative file before touching it so a mid-chain crash
    # can restore the filesystem to a consistent pre-commit state.
    prod_cumulative_backup: str | None = (
        final_cumul.read_text(encoding="utf-8") if final_cumul.exists() else None
    )

    try:
        try:
            os.replace(tmp_round, final_round)
            os.replace(tmp_cumul, final_cumul)
        except OSError as exc:
            # Restore the cumulative file if it was left in a partial or missing state.
            if prod_cumulative_backup is not None and not final_cumul.exists():
                final_cumul.write_text(prod_cumulative_backup, encoding="utf-8")
            raise CriticalTransactionFailure(
                "Sequential commit desync intercepted; filesystem state rolled back."
            ) from exc
    finally:
        # Unconditional staging purge — fires on both success and failure paths.
        # Each unlink is individually guarded so a permission error on one file
        # cannot mask the primary CriticalTransactionFailure being propagated.
        for _tmp in (tmp_round, tmp_cumul):
            try:
                _tmp.unlink(missing_ok=True)
            except OSError:
                pass

    print(f"\nVALIDATION PASSED")
    print(f"  schema_version   : {doc['schema_version']}")
    print(f"  field_size       : {doc['field_size']}")
    print(f"  leaderboard      : {len(doc['leaderboard'])} entries")
    print(f"  live_lean_notes  : {len(doc['live_lean_notes'])} entries (0 nulls)")
    app = doc['trait_audit']['app_150_200']
    print(f"  app_150_200      : {app['field_summary']['total_players_audited']} audited, "
          f"{app['field_summary']['players_with_pre_data']} with pre-data")
    print(f"  status dist      : {app['field_summary']['status_distribution']}")
    print(f"  rounds_completed : {cumulative['rounds_completed']} (cumulative synced)")
    print(f"\n  [COMMITTED] {final_round.name}")
    print(f"  [COMMITTED] {final_cumul.name}")


if __name__ == "__main__":
    main()
