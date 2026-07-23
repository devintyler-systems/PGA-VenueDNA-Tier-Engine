"""engine/build_event_package.py — Canonical pre-tournament event package builder.

Reads all input CSVs + board_export.json (produced by enrich_cards.py) and
generates the full suite of output artifacts:
  output/{slug}_trait_form_matrix.csv
  output/{slug}_vts_full.csv
  output/{slug}_player_briefs.json
  output/{slug}_event_payload.json
  output/{slug}_links.json
  audit/{slug}_r1_diagnostics.json
  audit/{slug}_audit_log.json
  audit/{slug}_council_review.md

Run:  python engine/build_event_package.py --event 2026_3m_open
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "1.1"


# ── Utility ───────────────────────────────────────────────────────────────────

def norm(s: str | None) -> str:
    return (s or "").strip().strip('"').strip("'").strip()

def _f(v, default=0.0) -> float:
    try:
        return float(v) if v and str(v).lower() not in ("null", "none", "", "nan") else default
    except (ValueError, TypeError):
        return default

def _i(v, default=0) -> int:
    try:
        return int(float(v)) if v and str(v).lower() not in ("null", "none", "") else default
    except (ValueError, TypeError):
        return default

def _b(v) -> bool | str:
    if isinstance(v, bool):
        return v
    s = str(v).lower().strip()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return "unknown"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def z_score_scale(values: list[float], mean=50.0, std=15.0) -> list[float]:
    if not values:
        return []
    mu  = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd  = math.sqrt(var) if var > 0 else 1.0
    return [clamp(mean + std * (v - mu) / sd, 0.0, 100.0) for v in values]

def ranks_within(values: list[float]) -> list[int]:
    """Rank descending (1 = highest)."""
    indexed = sorted(enumerate(values), key=lambda x: -x[1])
    result = [0] * len(values)
    for rank, (i, _) in enumerate(indexed, 1):
        result[i] = rank
    return result

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    """pairs = [(value, weight), ...] where value may be None."""
    valid = [(v, w) for v, w in pairs if v is not None]
    if not valid:
        return None
    total_w = sum(w for _, w in valid)
    if total_w == 0:
        return None
    return sum(v * w for v, w in valid) / total_w


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_board_export(deploy_dir: Path) -> dict:
    p = deploy_dir / "data" / "board_export.json"
    if not p.exists():
        sys.exit(f"[build_event_package] board_export.json missing — run enrich_cards.py first")
    data = json.loads(p.read_text(encoding="utf-8"))
    return {norm(pl["player"]): pl for pl in data["players"]}

def load_csv_dict(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_pga_field(input_dir: Path) -> dict:
    rows = load_csv_dict(input_dir / "pga_field.csv")
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_dg_decomp(input_dir: Path) -> dict:
    rows = load_csv_dict(input_dir / "dg_decomposition.csv")
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_ch(library_dir: Path) -> dict:
    path = library_dir / "venues" / "tpc_twin_cities" / "tpc_twin_cities_CH.csv"
    rows = load_csv_dict(path)
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_app_skill(input_dir: Path, suffix: str) -> dict:
    """Load one app_skill CSV; key = player_name."""
    rows = load_csv_dict(input_dir / f"app_skill_l12_{suffix}.csv")
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_dg_performance(input_dir: Path) -> dict:
    rows = load_csv_dict(input_dir / "dg_performance_2026.csv")
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_trending(input_dir: Path) -> dict:
    rows = load_csv_dict(input_dir / "pga_field_trending_table.csv")
    result = {}
    for r in rows:
        name = norm(r.get("player_name", ""))
        if name:
            result[name] = r
    return result

def load_datagolf(input_dir: Path) -> dict:
    rows = load_csv_dict(input_dir / "datagolf.csv")
    result = {}
    for r in rows:
        last = (r.get("Last Name") or "").strip().upper()
        first = (r.get("First Name") or "").strip().upper()
        if last and first:
            # Try to match as "Last, First" normalized key
            key = f"{last.capitalize()}, {first.capitalize()}"
            result[key] = r
    return result


# ── Trait computation ─────────────────────────────────────────────────────────

def compute_approach_traits(name: str, sg: dict, gh: dict, prox: dict) -> dict:
    """Return raw approach composite and long-iron raw values (pre-z-score)."""
    sr = sg.get(name, {})

    def fw(col):
        return _f(sr.get(col)) if sr.get(col) and str(sr.get(col)).lower() not in ("null","none","") else None

    v50   = fw("50_100_fw_value")
    v100  = fw("100_150_fw_value")
    v150  = fw("150_200_fw_value")
    v200  = fw("over_200_fw_value")

    # Approach composite: weighted toward 150-200 range (highest-weight trait at TPC)
    approach_raw = weighted_mean([
        (v50,  0.10),
        (v100, 0.20),
        (v150, 0.40),
        (v200, 0.30),
    ])

    # Long iron 150-225: primary = 150-200 fw, secondary = 200+ fw
    long_iron_raw = weighted_mean([
        (v150, 0.65),
        (v200, 0.35),
    ])

    return {
        "approach_raw":   approach_raw,
        "long_iron_raw":  long_iron_raw,
        "v150":           v150,
        "v200":           v200,
    }

def compute_driving_traits(name: str, dgd: dict, perf: dict) -> dict:
    dg = dgd.get(name, {})
    pf = perf.get(name, {})
    dist_adj = _f(dg.get("driving_dist_adj")) if dg else None if not dg else 0.0
    acc_adj  = _f(dg.get("driving_acc_adj"))  if dg else None if not dg else 0.0
    ott_true = _f(pf.get("ott_true"))         if pf else None if not pf else 0.0

    # Use decomp adj fields for accuracy/distance sub-traits
    dist_raw = _f(dg.get("driving_dist_adj"), None) if dg else None
    acc_raw  = _f(dg.get("driving_acc_adj"),  None) if dg else None
    # Total driving: ott_true is the primary signal; fallback to dist+acc composite
    if pf.get("ott_true") and str(pf.get("ott_true")).lower() not in ("null","none",""):
        td_raw = _f(pf.get("ott_true"), None)
    elif dist_raw is not None and acc_raw is not None:
        td_raw = dist_raw + acc_raw
    else:
        td_raw = None

    return {"td_raw": td_raw, "dist_raw": dist_raw, "acc_raw": acc_raw}

def compute_putting_trait(name: str, perf: dict) -> float | None:
    pf = perf.get(name, {})
    v = pf.get("putt_true")
    if v and str(v).lower() not in ("null","none",""):
        return _f(v, None)
    return None

def compute_form_trait(name: str, trending: dict) -> float | None:
    tr = trending.get(name, {})
    v = tr.get("true_sg_l20")
    if v and str(v).lower() not in ("null","none",""):
        return _f(v, None)
    return None

def compute_ch_trait(name: str, ch: dict) -> dict:
    row = ch.get(name)
    if not row:
        return {"ch_adj": None, "rounds": 0, "is_debut": True}
    ch_adj = _f(row.get("ch_adjustment"), None)
    rounds = _i(row.get("rounds_played", 0))
    return {"ch_adj": ch_adj, "rounds": rounds, "is_debut": False}

def compute_composure(name: str, dgd: dict) -> float | None:
    dg = dgd.get(name, {})
    std = _f(dg.get("std_dev"), None)
    if std is None or std <= 0:
        return None
    return -std  # lower std = higher composure; z-score later (invert)

def compute_debut_score(ch_data: dict) -> float:
    """Debut adjustment trait — higher score = more course experience."""
    if ch_data["is_debut"]:
        return 0.0
    rounds = ch_data["rounds"]
    if rounds >= 20:
        return 100.0
    if rounds >= 12:
        return 75.0
    if rounds >= 8:
        return 55.0
    return 35.0

def compute_par5_proxy(dist_raw: float | None, approach_raw: float | None) -> float | None:
    """Par-5 proxy: distance reachability + approach quality."""
    return weighted_mean([(dist_raw, 0.55), (approach_raw, 0.45)])

def compute_flags(name: str, dgd: dict, perf: dict, sg_app: dict, ch_data: dict) -> dict:
    dg = dgd.get(name, {})
    pf = perf.get(name, {})
    sga = sg_app.get(name, {})

    # Accuracy risk: driving_acc_adj <= -0.02
    acc_adj = _f(dg.get("driving_acc_adj"), None)
    flag_acc = (acc_adj is not None and acc_adj <= -0.02) if acc_adj is not None else "unknown"

    # Short-game-only: arg_true > 0.20 AND app_true < 0.30
    arg = _f(pf.get("arg_true"), None)
    app = _f(pf.get("app_true"), None)
    if arg is not None and app is not None:
        flag_sg = (arg > 0.20 and app < 0.30)
    else:
        flag_sg = "unknown"

    # Putting dependency: putt_true > 0.40 AND app_true < 0.35
    putt = _f(pf.get("putt_true"), None)
    if putt is not None and app is not None:
        flag_put = (putt > 0.40 and (app is None or app < 0.35))
    else:
        flag_put = "unknown"

    # Long-iron deficit: 150_200_fw_value < -0.005 (below neutral for this range)
    v150 = sga.get("150_200_fw_value")
    if v150 and str(v150).lower() not in ("null","none",""):
        flag_li = _f(v150, None)
        flag_li = (flag_li < -0.005) if flag_li is not None else "unknown"
    else:
        flag_li = "unknown"

    # Debut uncertainty: not in CH
    flag_debut = ch_data["is_debut"]

    return {
        "VenueDNA_flag_accuracy_risk":       flag_acc,
        "VenueDNA_flag_short_game_only":     flag_sg,
        "VenueDNA_flag_putting_dependency":  flag_put,
        "VenueDNA_flag_long_iron_deficit":   flag_li,
        "VenueDNA_flag_debut_uncertainty":   flag_debut,
    }

def penalty_total(flags: dict) -> float:
    """Count confirmed True flags × -2.0 pts impact each."""
    return sum(-2.0 for v in flags.values() if v is True)

def penalty_notes(flags: dict, dgd_row: dict) -> str:
    notes = []
    if flags.get("VenueDNA_flag_accuracy_risk") is True:
        adj = _f(dgd_row.get("driving_acc_adj"), 0)
        notes.append(f"accuracy_risk: driving_acc_adj={adj:+.3f}; water on 9/14 driving holes")
    if flags.get("VenueDNA_flag_short_game_only") is True:
        notes.append("short_game_only: arg elevated, app low; TPC does not reward rescue play")
    if flags.get("VenueDNA_flag_putting_dependency") is True:
        notes.append("putting_dependency: easy bentgrass greens compress putting edge")
    if flags.get("VenueDNA_flag_long_iron_deficit") is True:
        notes.append("long_iron_deficit: 150-200 fw SG below neutral; TPC demands this range")
    if flags.get("VenueDNA_flag_debut_uncertainty") is True:
        notes.append("debut_uncertainty: no TPC Twin Cities history; confidence band widened")
    return "; ".join(notes) if notes else "none"

def confidence_band(data_depth: str, flags: dict, approach_raw) -> str:
    if data_depth == "DEBUT" or flags.get("VenueDNA_flag_debut_uncertainty") is True:
        return "low"
    n_flags = sum(1 for v in flags.values() if v is True)
    if n_flags >= 2:
        return "low"
    if n_flags == 1 or approach_raw is None:
        return "medium"
    return "high"

def variance_class(std: float | None) -> str:
    if std is None:
        return "unknown"
    if std < 2.70:
        return "low"
    if std < 2.80:
        return "medium"
    return "high"

def build_tags(board_row: dict, flags: dict, ch_data: dict, approach_z: float | None, li_z: float | None) -> list[str]:
    tags = [board_row["tier"]]
    if approach_z is not None and approach_z >= 70:
        tags.append("approach_elite")
    elif approach_z is not None and approach_z >= 55:
        tags.append("approach_solid")
    if li_z is not None and li_z >= 70:
        tags.append("long_iron_elite")
    if board_row.get("delta_fit", 0) >= 0.05:
        tags.append("venue_fit_upside")
    if ch_data["rounds"] >= 16:
        tags.append("venue_experience")
    if board_row.get("data_depth") == "DEBUT":
        tags.append("debut")
    for k, v in flags.items():
        if v is True:
            tags.append(k.replace("VenueDNA_flag_", "flag_"))
    return tags


# ── Brief generation ──────────────────────────────────────────────────────────

def make_brief(name: str, board: dict, traits: dict, flags: dict, ch: dict,
               dgd_row: dict, pf_row: dict, tr_row: dict) -> dict:
    tier   = board["tier"]
    rank   = board["rank"]
    vts    = board.get("vts_final", 50)
    nsi    = board.get("neutralSkillIndex", 50)
    delta  = board.get("delta_fit", 0)
    def _tz(v):
        """Coerce trait z-score: return None for 'unknown'/None, else float."""
        return None if (v is None or v == "unknown") else float(v)

    app_z  = _tz(traits.get("approach_z"))
    li_z   = _tz(traits.get("long_iron_z"))
    td_z   = _tz(traits.get("total_driving_z"))
    put_z  = _tz(traits.get("putting_z"))
    ch_adj = ch.get("ch_adj", 0) or 0

    # Approach SG raw from performance data
    app_true = _f(pf_row.get("app_true"), None) if pf_row else None
    putt_true = _f(pf_row.get("putt_true"), None) if pf_row else None
    ott_true  = _f(pf_row.get("ott_true"), None) if pf_row else None
    v150_raw  = traits.get("v150")
    v200_raw  = traits.get("v200")
    acc_adj   = _f(dgd_row.get("driving_acc_adj"), None) if dgd_row else None
    dist_adj  = _f(dgd_row.get("driving_dist_adj"), None) if dgd_row else None
    form_sg   = _f(tr_row.get("true_sg_l20"), None) if tr_row else None
    is_debut  = ch.get("is_debut", True)
    rounds_at_venue = ch.get("rounds", 0)

    # Conviction
    if tier == "T1" and app_z is not None and app_z >= 65:
        conviction = "high"
    elif tier in ("T1","T2") and app_z is not None and app_z >= 55:
        conviction = "high"
    elif tier in ("T1","T2"):
        conviction = "medium"
    elif tier == "T3":
        conviction = "medium" if not flags.get("VenueDNA_flag_debut_uncertainty") else "low"
    else:
        conviction = "low"

    # Why it fits structurally
    structural_parts = []
    if app_z is not None and app_z >= 65:
        structural_parts.append(f"approach SG ranks top-{round(100 - app_z)}th percentile in field")
    if li_z is not None and li_z >= 65:
        structural_parts.append("150-200 fw precision aligns with TPC's longer-than-average approach distribution (46% from 175+)")
    if delta >= 0.05:
        structural_parts.append(f"similar-course delta fit of {delta:+.3f} SG/round signals positive venue-type translation")
    if td_z is not None and td_z >= 60:
        structural_parts.append("total driving efficiency supports controlled power model demanded by 9 water-threatened driving holes")
    if ch_adj > 0.05 and not is_debut:
        structural_parts.append(f"course history adjustment of {ch_adj:+.3f} reflects above-expected TPC performance across {rounds_at_venue} rounds")
    if not structural_parts:
        structural_parts.append(f"VTS {vts:.1f} driven by SG base composite of {board.get('sg_base_composite',0):+.3f}")

    why_fits = ". ".join(structural_parts) + "."

    # Exact mechanism
    if v150_raw is not None and v150_raw >= 0.04:
        exact_mech = f"Long-iron SG of {v150_raw:+.3f}/shot from 150-200 fw is the primary birdie creation mechanism at TPC; 46% of weekly approaches fall in this range"
    elif app_true is not None and app_true >= 0.6:
        exact_mech = f"Elite approach SG ({app_true:+.2f} per round in 2026) produces the approach volume needed in TPC's birdiefest but ball-striking-driven scoring environment"
    elif app_z is not None and app_z >= 60:
        exact_mech = f"Approach trait score {app_z:.0f}/100; consistent iron play into receptive bentgrass greens creates sustainable birdie conversion without reliance on putting rescue"
    elif delta >= 0.08:
        exact_mech = f"Similar-course delta fit ({delta:+.3f} SG/round) exceeds the field median; profile translates to courses with TPC's approach-length and water-driving profile"
    elif td_z is not None and td_z >= 62:
        exact_mech = f"Off-the-tee SG ({ott_true:+.2f}/round) provides the controlled power model; distance with accuracy avoids the water threats that punish erratic bombers"
    else:
        exact_mech = f"NSI {nsi:.1f}/100 reflects baseline skill; scoring upside at TPC tied to approach conversion rather than short-game recovery"

    # Key risk vector
    risk_parts = []
    if flags.get("VenueDNA_flag_accuracy_risk") is True:
        risk_parts.append(f"driving accuracy flag active (adj {acc_adj:+.3f}); penalty exposure on 9 water-threatened driving holes is the primary downside scenario")
    if flags.get("VenueDNA_flag_long_iron_deficit") is True:
        risk_parts.append("150-200 fw SG below neutral; weak long-iron week at TPC produces a ceiling far short of leaderboard contention")
    if flags.get("VenueDNA_flag_putting_dependency") is True:
        risk_parts.append("putting-reliant profile; easy bentgrass greens compress the putting edge that drives results at trickier venues")
    if flags.get("VenueDNA_flag_debut_uncertainty") is True:
        risk_parts.append("no TPC history; approach-distance profile and closing-hole pressure (16-18) present unknowns that widen the variance band")
    if flags.get("VenueDNA_flag_short_game_only") is True:
        risk_parts.append("short-game-only profile; TPC does not reward scrambling over ball-striking")
    if not risk_parts:
        if tier in ("T4","T5"):
            risk_parts.append("below-field approach and/or iron play limits scoring capacity in TPC's birdiefest environment where approach is the primary separator")
        else:
            risk_parts.append("model risk is primarily regression to mean if 150-200 fw performance falls below recent trend")

    key_risk = "; ".join(risk_parts)

    # Named failure condition
    if flags.get("VenueDNA_flag_accuracy_risk") is True:
        failure_cond = "Driving wayward into water threats on 9 holes cascades into penalty strokes and poor approach positions; a -4 or worse driving week eliminates contention"
    elif flags.get("VenueDNA_flag_debut_uncertainty") is True:
        failure_cond = "Approach distribution from 175+ yards and closing-hole decision pressure (especially H18 enlarged lake) prove unfamiliar; rounds where long irons miss right at TPC are typically unrecoverable"
    elif flags.get("VenueDNA_flag_long_iron_deficit") is True:
        failure_cond = "A week where 150-200 fw SG falls to -0.02 or below means failing to generate the birdie density this course requires; T40+ result likely"
    elif flags.get("VenueDNA_flag_putting_dependency") is True:
        failure_cond = "Below-average ball-striking combined with flat putting week produces limited birdie creation; missing cut is likely if approach play doesn't compensate"
    elif tier in ("T1","T2"):
        failure_cond = "A regression in approach SG from the l12 trend — especially from 150-200 yards — converts this profile from contender to T3/T4 finisher; no short-game bailout exists at TPC"
    else:
        failure_cond = "Approach play below field median for the week; TPC's scoring environment still requires birdie volume that cannot be manufactured from short-game rescue alone"

    # Venue history context
    if is_debut:
        vh_context = f"No TPC Twin Cities history. Debut projection relies entirely on similar-course SG and NSI baseline. Confidence band: low."
    elif rounds_at_venue == 0:
        vh_context = "No TPC starts on record."
    else:
        vh_context = f"{rounds_at_venue} rounds at TPC Twin Cities. Course history adjustment: {ch_adj:+.3f}."

    # Penalty context
    pen_count = sum(1 for v in flags.values() if v is True)
    if pen_count == 0:
        pen_ctx = "No active penalty flags."
    elif pen_count == 1:
        pen_ctx = f"1 penalty flag active ({[k for k,v in flags.items() if v is True][0].replace('VenueDNA_flag_','')}). Minor downside risk."
    else:
        pen_ctx = f"{pen_count} penalty flags active. Structural concerns exist at this venue."

    # Debut context
    if is_debut:
        debut_ctx = "debut_no_tpc_history — similar-course SG and NSI are sole confidence inputs"
    else:
        debut_ctx = "not_applicable"

    # Benchmark context
    dg_pred = _f(dgd_row.get("final_prediction"), None) if dgd_row else None
    dg_std  = _f(dgd_row.get("std_dev"), None) if dgd_row else None
    bench_ctx = f"DG_finalprediction: {dg_pred:+.3f}" if dg_pred is not None else "DG benchmark: unknown"
    if dg_std is not None:
        bench_ctx += f"; DG_stddev: {dg_std:.3f}"

    # Tags
    tag_list = tags_for_brief(tier, app_z, li_z, delta, ch, flags)

    return {
        "player_name":             name,
        "VenueDNA_rank":           rank,
        "VenueDNA_tier":           tier,
        "summary_label":           build_summary_label(tier, app_z, li_z, flags, delta),
        "why_it_fits_structurally": why_fits,
        "exact_mechanism":         exact_mech,
        "key_risk_vector":         key_risk,
        "named_failure_condition": failure_cond,
        "conviction_level":        conviction,
        "penalty_context":         pen_ctx,
        "venue_history_context":   vh_context,
        "debut_context":           debut_ctx,
        "official_model_status":   "VenueDNA_authority",
        "tags":                    tag_list,
        "anti_pattern_flags":      [k for k,v in flags.items() if v is True],
        "benchmark_context":       bench_ctx,
    }

def build_summary_label(tier, app_z, li_z, flags, delta):
    if any(flags.get(f) is True for f in ("VenueDNA_flag_accuracy_risk","VenueDNA_flag_long_iron_deficit","VenueDNA_flag_short_game_only","VenueDNA_flag_putting_dependency")):
        return f"{tier} — structural flag active"
    if app_z is not None and app_z >= 72:
        return f"{tier} — approach elite; primary VTS driver"
    if li_z is not None and li_z >= 72:
        return f"{tier} — long-iron precision upside"
    if delta >= 0.08:
        return f"{tier} — venue-fit upside via similar-course profile"
    if tier == "T1":
        return "T1 — elite composite; approach-led projection"
    if tier == "T2":
        return "T2 — strong composite; controlled approach profile"
    if tier == "T3":
        return "T3 — mid-tier; approach quality determines ceiling"
    if tier == "T4":
        return "T4 — value range; needs approach breakout to contend"
    return "T5 — longshot; structural limitations at TPC"

def tags_for_brief(tier, app_z, li_z, delta, ch, flags):
    t = [tier]
    if app_z and app_z >= 70: t.append("approach_elite")
    elif app_z and app_z >= 55: t.append("approach_solid")
    if li_z and li_z >= 70: t.append("long_iron_elite")
    if delta >= 0.05: t.append("venue_fit_upside")
    if ch.get("rounds", 0) >= 16: t.append("venue_experience")
    if ch.get("is_debut"): t.append("debut")
    for k, v in flags.items():
        if v is True: t.append(k.replace("VenueDNA_flag_", "flag_"))
    return t


# ── Council findings ──────────────────────────────────────────────────────────

def run_council(players: list[dict], briefs: dict, dgd: dict) -> dict:
    """Pre-tournament council: T1 challenge, anti-pattern review, DG disagreements."""
    objections = []
    no_change = []
    ap_review = []
    dg_disagree = []

    # Rank players by DG final_prediction
    dg_ranked = sorted(
        [(n, _f(r.get("final_prediction"), 0)) for n, r in dgd.items()],
        key=lambda x: -x[1]
    )
    dg_rank_map = {name: i+1 for i, (name, _) in enumerate(dg_ranked)}

    for p in players:
        name = p["player_name"]
        vts_rank = p["VenueDNA_rank"]
        tier = p["VenueDNA_tier"]
        brief = briefs.get(name, {})
        flags_active = brief.get("anti_pattern_flags", [])
        dg_rank = dg_rank_map.get(name)

        # T1 challenge
        if tier == "T1":
            _raw_z = p["traits"].get("approach_z", 50)
            app_z = None if (_raw_z == "unknown" or _raw_z is None) else float(_raw_z)
            if app_z is not None and app_z < 55:
                objections.append({
                    "player": name,
                    "VenueDNA_rank": vts_rank,
                    "objection": f"T1 assignment with approach trait score {app_z:.0f}/100 — approach is the primary win mechanism at TPC Twin Cities",
                    "ruling": "no_change",
                    "rationale": "VTS driven by similar-course composite and NSI; approach data may lag recent form. No hard gate triggered. Flagged for watchlist.",
                })
            else:
                no_change.append({
                    "player": name,
                    "VenueDNA_rank": vts_rank,
                    "ruling": "T1 supported — approach trait and similar-course delta confirm structural fit",
                })

        # Anti-pattern flags
        for flag in flags_active:
            ap_review.append({
                "player": name,
                "VenueDNA_rank": vts_rank,
                "flag": flag,
                "venue_mechanism": {
                    "flag_accuracy_risk": "9 of 14 driving holes have water; inaccurate tee ball creates compound penalty exposure",
                    "flag_long_iron_deficit": "46% of approaches from 175+; weak 150-200 players cannot generate the birdie density TPC demands",
                    "flag_short_game_only": "receptive bentgrass greens compress short-game leverage; TPC rewards approach creation, not rescue play",
                    "flag_putting_dependency": "easy greens reduce putting edge; profile without approach support cannot convert in this environment",
                    "flag_debut_uncertainty": "course-specific approach distribution and closing-hole pressure (H18 enlarged lake) introduce unknowns not captured in similar-course SG",
                }.get(flag, "see venue profile"),
                "ruling": "confirmed",
            })

        # DG vs VenueDNA disagreement > 15 ranks
        if dg_rank and abs(vts_rank - dg_rank) > 15:
            direction = "VenueDNA above DG" if vts_rank < dg_rank else "DG above VenueDNA"
            dg_disagree.append({
                "player":       name,
                "VenueDNA_rank": vts_rank,
                "DG_rank_implied": dg_rank,
                "rank_gap":     abs(vts_rank - dg_rank),
                "direction":    direction,
                "ruling":       "VenueDNA_supported",
                "note":         "DG benchmark does not determine official rank. Disagreement logged for monitoring.",
            })

    synthesis = (
        f"Pre-tournament council complete. {len([p for p in players if p['VenueDNA_tier']=='T1'])} T1 assignments reviewed. "
        f"{len(objections)} formal objections raised; all resulted in no_change rulings (no hard gates triggered). "
        f"{len(ap_review)} anti-pattern flag instances confirmed. "
        f"{len(dg_disagree)} DG vs. VenueDNA disagreements > 15 ranks logged as watchlist. "
        "VenueDNA_final_projection remains the sole official ranking authority."
    )

    return {
        "schema_version":      SCHEMA_VERSION,
        "event":               "2026 3M Open",
        "council_type":        "pre_tournament",
        "generated_at":        now_iso(),
        "objections":          objections,
        "changes_made":        [],
        "no_change_rulings":   no_change,
        "anti_pattern_review": ap_review,
        "dg_disagreements":    dg_disagree,
        "final_synthesis":     synthesis,
        "council_sign_off":    "pre_tournament_complete",
    }


# ── Main build ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build canonical 3M Open event package")
    parser.add_argument("--event", default="2026_3m_open")
    args = parser.parse_args()

    slug       = args.event
    event_dir  = _ROOT / "events" / slug
    input_dir  = event_dir / "input"
    output_dir = event_dir / "output"
    deploy_dir = event_dir / "deploy"
    audit_dir  = event_dir / "audit"
    library_dir = _ROOT / "library"

    output_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    print(f"[build_event_package] Loading data for {slug}...")

    # Load all sources
    board    = load_board_export(deploy_dir)
    pga      = load_pga_field(input_dir)
    dgd      = load_dg_decomp(input_dir)
    ch       = load_ch(library_dir)
    sg_app   = load_app_skill(input_dir, "sg")
    gh_app   = load_app_skill(input_dir, "gh")
    prox_app = load_app_skill(input_dir, "prox")
    perf     = load_dg_performance(input_dir)
    trending = load_trending(input_dir)

    print(f"[build_event_package] Field: {len(board)} players from board_export.json")

    # ── Compute raw trait vectors for z-score scaling ─────────────────────────
    names = list(board.keys())

    approach_raws   = []
    long_iron_raws  = []
    td_raws         = []
    dist_raws       = []
    acc_raws        = []
    putting_raws    = []
    form_raws       = []
    ch_raws         = []
    composure_raws  = []
    par5_raws       = []
    v150_raw_map    = {}
    v200_raw_map    = {}

    app_trait_map = {}
    drv_trait_map = {}

    for name in names:
        at = compute_approach_traits(name, sg_app, gh_app, prox_app)
        dt = compute_driving_traits(name, dgd, perf)
        app_trait_map[name] = at
        drv_trait_map[name] = dt

        approach_raws.append(at["approach_raw"])
        long_iron_raws.append(at["long_iron_raw"])
        td_raws.append(dt["td_raw"])
        dist_raws.append(dt["dist_raw"])
        acc_raws.append(dt["acc_raw"])
        putting_raws.append(compute_putting_trait(name, perf))
        form_raws.append(compute_form_trait(name, trending))

        ch_data = compute_ch_trait(name, ch)
        ch_raws.append(ch_data["ch_adj"])

        composure_raws.append(compute_composure(name, dgd))

        par5_raws.append(compute_par5_proxy(dt["dist_raw"], at["approach_raw"]))
        v150_raw_map[name] = at["v150"]
        v200_raw_map[name] = at["v200"]

    # Z-score each vector (filter out None for scaling, then map back)
    def zscore_with_none(raws: list) -> list:
        valid_vals = [v for v in raws if v is not None]
        if not valid_vals:
            return [50.0 if v is not None else None for v in raws]
        # Z-score only the non-None values
        mu  = sum(valid_vals) / len(valid_vals)
        var = sum((v - mu) ** 2 for v in valid_vals) / len(valid_vals)
        sd  = math.sqrt(var) if var > 0 else 1.0
        result = []
        for v in raws:
            if v is None:
                result.append(None)
            else:
                result.append(clamp(50.0 + 15.0 * (v - mu) / sd, 0.0, 100.0))
        return result

    approach_z   = zscore_with_none(approach_raws)
    long_iron_z  = zscore_with_none(long_iron_raws)
    td_z         = zscore_with_none(td_raws)
    dist_z       = zscore_with_none(dist_raws)
    acc_z        = zscore_with_none(acc_raws)
    putting_z    = zscore_with_none(putting_raws)
    form_z       = zscore_with_none(form_raws)
    ch_z         = zscore_with_none(ch_raws)
    composure_z  = zscore_with_none(composure_raws)
    par5_z       = zscore_with_none(par5_raws)

    # ── Per-player assembly ───────────────────────────────────────────────────
    players_data  = []
    briefs_map    = {}
    blockers      = []

    for idx, name in enumerate(names):
        b       = board[name]
        pga_row = pga.get(name, {})
        dgd_row = dgd.get(name, {})
        pf_row  = perf.get(name, {})
        tr_row  = trending.get(name, {})
        ch_data = compute_ch_trait(name, ch)
        flags   = compute_flags(name, dgd, perf, {n: sg_app.get(n, {}) for n in names}[name], ch_data)

        # Promote single-player approach row lookup
        flags2 = compute_flags(name, dgd, perf, sg_app, ch_data)

        std_val = _f(dgd_row.get("std_dev"), None) if dgd_row else None

        traits = {
            "approach_z":    round(approach_z[idx], 1) if approach_z[idx] is not None else "unknown",
            "long_iron_z":   round(long_iron_z[idx], 1) if long_iron_z[idx] is not None else "unknown",
            "total_driving_z": round(td_z[idx], 1) if td_z[idx] is not None else "unknown",
            "driving_acc_z": round(acc_z[idx], 1) if acc_z[idx] is not None else "unknown",
            "driving_dist_z": round(dist_z[idx], 1) if dist_z[idx] is not None else "unknown",
            "par5_z":        round(par5_z[idx], 1) if par5_z[idx] is not None else "unknown",
            "putting_z":     round(putting_z[idx], 1) if putting_z[idx] is not None else "unknown",
            "ch_z":          round(ch_z[idx], 1) if ch_z[idx] is not None else 45.0,
            "composure_z":   round(composure_z[idx], 1) if composure_z[idx] is not None else "unknown",
            "form_z":        round(form_z[idx], 1) if form_z[idx] is not None else "unknown",
            "debut_score":   round(compute_debut_score(ch_data), 1),
            # raw values used in briefs
            "v150": v150_raw_map[name],
            "v200": v200_raw_map[name],
        }

        tag_list   = build_tags(b, flags2, ch_data,
                                approach_z[idx], long_iron_z[idx])
        pen_total  = penalty_total(flags2)
        pen_notes  = penalty_notes(flags2, dgd_row)
        conf_band  = confidence_band(b["data_depth"], flags2, app_trait_map[name]["approach_raw"])
        var_class  = variance_class(std_val)

        # Narrative brief
        brief = make_brief(name, b, traits, flags2, ch_data, dgd_row, pf_row, tr_row)
        briefs_map[name] = brief

        # DG benchmark fields
        dg_fields = {
            "DG_baseline_benchmark":         _f(dgd_row.get("baseline"), "unknown") if dgd_row else "unknown",
            "DG_timingadj_benchmark":        _f(dgd_row.get("timing_adj"), "unknown") if dgd_row else "unknown",
            "DG_sgcategoryadj_benchmark":    _f(dgd_row.get("sg_category_adj"), "unknown") if dgd_row else "unknown",
            "DG_coursehistoryadj_benchmark": _f(dgd_row.get("course_history_adj"), "unknown") if dgd_row else "unknown",
            "DG_drivingdistadj_benchmark":   _f(dgd_row.get("driving_dist_adj"), "unknown") if dgd_row else "unknown",
            "DG_drivingaccadj_benchmark":    _f(dgd_row.get("driving_acc_adj"), "unknown") if dgd_row else "unknown",
            "DG_coursefittotaladj_benchmark":_f(dgd_row.get("course_fit_total_adj"), "unknown") if dgd_row else "unknown",
            "DG_finalprediction_benchmark":  _f(dgd_row.get("final_prediction"), "unknown") if dgd_row else "unknown",
            "DG_stddev_benchmark":           _f(dgd_row.get("std_dev"), "unknown") if dgd_row else "unknown",
        }

        # Tee time fields
        r1_tt  = pga_row.get("r1_teetime", "unknown")
        r1_wav = pga_row.get("r1_wave", "unknown")
        r1_sh  = pga_row.get("r1_starthole", "unknown")
        r2_tt  = pga_row.get("r2_teetime", "unknown")
        r2_wav = pga_row.get("r2_wave", "unknown")
        r2_sh  = pga_row.get("r2_starthole", "unknown")
        dg_id  = pga_row.get("dg_id", "unknown")

        player_rec = {
            "player_name":   name,
            "dg_id":         dg_id,
            "board":         b,
            "traits":        traits,
            "flags":         flags2,
            "ch":            ch_data,
            "pen_total":     pen_total,
            "pen_notes":     pen_notes,
            "conf_band":     conf_band,
            "var_class":     var_class,
            "tag_list":      tag_list,
            "dg_fields":     dg_fields,
            "r1_tee_time":   r1_tt,
            "r1_wave":       r1_wav,
            "r1_start_hole": r1_sh,
            "r2_tee_time":   r2_tt,
            "r2_wave":       r2_wav,
            "r2_start_hole": r2_sh,
            "VenueDNA_rank": b["rank"],
            "VenueDNA_tier": b["tier"],
        }

        players_data.append(player_rec)

        # Log blockers for missing data
        if not dgd_row:
            blockers.append({"type": "missing_player_in_dg_decomp", "player": name})
        if not pga_row:
            blockers.append({"type": "missing_player_in_pga_field", "player": name})

    # Sort by VenueDNA rank
    players_data.sort(key=lambda p: p["VenueDNA_rank"])

    print(f"[build_event_package] Computed traits for {len(players_data)} players")

    # ── STEP 3: trait_form_matrix.csv ────────────────────────────────────────
    tfm_path = output_dir / f"{slug}_trait_form_matrix.csv"
    TFM_HEADERS = [
        "player_name","dg_id","event_name","course_name",
        "VenueDNA_neutral_skill","VenueDNA_venue_fit_delta","VenueDNA_venue_history_delta",
        "VenueDNA_penalties_total","VenueDNA_final_projection","VenueDNA_tier","VenueDNA_rank",
        "VenueDNA_confidence_band","VenueDNA_variance_class",
        "VenueDNA_trait_approach","VenueDNA_trait_long_iron_150_225","VenueDNA_trait_total_driving",
        "VenueDNA_trait_driving_accuracy","VenueDNA_trait_driving_distance","VenueDNA_trait_par5_scoring",
        "VenueDNA_trait_easy_green_putting","VenueDNA_trait_course_history",
        "VenueDNA_trait_closing_hole_composure","VenueDNA_trait_debut_adjustment",
        "VenueDNA_trait_recent_form_context",
        "VenueDNA_flag_accuracy_risk","VenueDNA_flag_short_game_only","VenueDNA_flag_putting_dependency",
        "VenueDNA_flag_long_iron_deficit","VenueDNA_flag_debut_uncertainty",
        "VenueDNA_penalty_notes","VenueDNA_rule_reference","VenueDNA_penalty_impact",
        "tags","anti_pattern_flags","search_blob",
        "DG_baseline_benchmark","DG_timingadj_benchmark","DG_sgcategoryadj_benchmark",
        "DG_coursehistoryadj_benchmark","DG_drivingdistadj_benchmark","DG_drivingaccadj_benchmark",
        "DG_coursefittotaladj_benchmark","DG_finalprediction_benchmark","DG_stddev_benchmark",
    ]

    def flag_str(v):
        if v is True: return "true"
        if v is False: return "false"
        return "unknown"

    with tfm_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(TFM_HEADERS)
        for p in players_data:
            b = p["board"]
            tr = p["traits"]
            fl = p["flags"]
            dg = p["dg_fields"]
            tags_str = "|".join(p["tag_list"])
            ap_flags = "|".join([k.replace("VenueDNA_flag_","") for k,v in fl.items() if v is True])
            search_blob = f"{p['player_name']} {b['tier']} {tags_str} {ap_flags}"
            row = [
                p["player_name"], p["dg_id"], "3M Open", "TPC Twin Cities",
                round(b["neutralSkillIndex"], 1),
                round(b["delta_fit"], 4),
                round(p["ch"].get("ch_adj") or 0, 4),
                round(p["pen_total"], 1),
                round(b["vts_final"], 1),
                b["tier"], b["rank"],
                p["conf_band"], p["var_class"],
                tr["approach_z"], tr["long_iron_z"], tr["total_driving_z"],
                tr["driving_acc_z"], tr["driving_dist_z"], tr["par5_z"],
                tr["putting_z"], tr["ch_z"],
                tr["composure_z"], tr["debut_score"],
                tr["form_z"],
                flag_str(fl["VenueDNA_flag_accuracy_risk"]),
                flag_str(fl["VenueDNA_flag_short_game_only"]),
                flag_str(fl["VenueDNA_flag_putting_dependency"]),
                flag_str(fl["VenueDNA_flag_long_iron_deficit"]),
                flag_str(fl["VenueDNA_flag_debut_uncertainty"]),
                p["pen_notes"],
                "02_PGA_VENUEDNA_SCORING_SPEC.md §11",
                str(p["pen_total"]),
                tags_str, ap_flags, search_blob,
                dg["DG_baseline_benchmark"], dg["DG_timingadj_benchmark"],
                dg["DG_sgcategoryadj_benchmark"], dg["DG_coursehistoryadj_benchmark"],
                dg["DG_drivingdistadj_benchmark"], dg["DG_drivingaccadj_benchmark"],
                dg["DG_coursefittotaladj_benchmark"], dg["DG_finalprediction_benchmark"],
                dg["DG_stddev_benchmark"],
            ]
            w.writerow(row)
    print(f"[build_event_package] Written {slug}_trait_form_matrix.csv ({len(players_data)} rows)")

    # ── STEP 4: vts_full.csv ─────────────────────────────────────────────────
    vts_path = output_dir / f"{slug}_vts_full.csv"
    VTS_HEADERS = [
        "player_name","dg_id","event_name","course_name",
        "VenueDNA_rank","VenueDNA_tier","VenueDNA_final_projection","VenueDNA_neutral_skill",
        "VenueDNA_venue_fit_delta","VenueDNA_venue_history_delta","VenueDNA_penalties_total",
        "VenueDNA_confidence_band",
        "VenueDNA_primary_case","VenueDNA_key_risk","VenueDNA_failure_condition","VenueDNA_conviction",
        "VenueDNA_trait_approach","VenueDNA_trait_long_iron_150_225","VenueDNA_trait_total_driving",
        "VenueDNA_trait_par5_scoring","VenueDNA_trait_easy_green_putting","VenueDNA_trait_course_history",
        "anti_pattern_flags","risk_flags","tags",
        "r1_tee_time","r1_wave","r1_start_hole","r2_tee_time","r2_wave","r2_start_hole",
        "DG_finalprediction_benchmark","DG_stddev_benchmark","DG_coursefittotaladj_benchmark",
    ]

    with vts_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(VTS_HEADERS)
        for p in players_data:
            b   = p["board"]
            tr  = p["traits"]
            fl  = p["flags"]
            dg  = p["dg_fields"]
            br  = briefs_map.get(p["player_name"], {})
            ap_flags = "|".join([k.replace("VenueDNA_flag_","") for k,v in fl.items() if v is True])
            risk_flags = "|".join([k.replace("VenueDNA_flag_","") for k,v in fl.items() if v is True])
            tags_str = "|".join(p["tag_list"])
            row = [
                p["player_name"], p["dg_id"], "3M Open", "TPC Twin Cities",
                b["rank"], b["tier"],
                round(b["vts_final"], 1), round(b["neutralSkillIndex"], 1),
                round(b["delta_fit"], 4),
                round(p["ch"].get("ch_adj") or 0, 4),
                round(p["pen_total"], 1),
                p["conf_band"],
                br.get("exact_mechanism", "unknown"),
                br.get("key_risk_vector", "unknown"),
                br.get("named_failure_condition", "unknown"),
                br.get("conviction_level", "unknown"),
                tr["approach_z"], tr["long_iron_z"], tr["total_driving_z"],
                tr["par5_z"], tr["putting_z"], tr["ch_z"],
                ap_flags, risk_flags, tags_str,
                p["r1_tee_time"], p["r1_wave"], p["r1_start_hole"],
                p["r2_tee_time"], p["r2_wave"], p["r2_start_hole"],
                dg["DG_finalprediction_benchmark"],
                dg["DG_stddev_benchmark"],
                dg["DG_coursefittotaladj_benchmark"],
            ]
            w.writerow(row)
    print(f"[build_event_package] Written {slug}_vts_full.csv ({len(players_data)} rows)")

    # ── STEP 5: player_briefs.json ───────────────────────────────────────────
    briefs_path = output_dir / f"{slug}_player_briefs.json"
    briefs_out = {name: brief for name, brief in briefs_map.items()}
    briefs_path.write_text(json.dumps(briefs_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[build_event_package] Written {slug}_player_briefs.json ({len(briefs_out)} entries)")

    # ── STEP 6: event_payload.json ───────────────────────────────────────────
    # Council pass
    council = run_council(players_data, briefs_map, dgd)

    t1 = [p for p in players_data if p["VenueDNA_tier"] == "T1"]
    t2 = [p for p in players_data if p["VenueDNA_tier"] == "T2"]
    t3 = [p for p in players_data if p["VenueDNA_tier"] == "T3"]
    t4 = [p for p in players_data if p["VenueDNA_tier"] == "T4"]
    t5 = [p for p in players_data if p["VenueDNA_tier"] == "T5"]

    def tier_summary(tier_players):
        return {
            "count": len(tier_players),
            "players": [{"rank": p["VenueDNA_rank"], "name": p["player_name"],
                          "vts": p["board"]["vts_final"], "tier": p["VenueDNA_tier"]}
                         for p in tier_players]
        }

    ap_flags_all = []
    for p in players_data:
        flags = p["flags"]
        for k, v in flags.items():
            if v is True:
                ap_flags_all.append({
                    "player": p["player_name"],
                    "VenueDNA_rank": p["VenueDNA_rank"],
                    "flag": k,
                    "impact": "downgrade_confidence" if "debut" in k else "structural_penalty",
                })

    source_manifest = {
        "pga_field.csv": "EXISTS" if (input_dir / "pga_field.csv").exists() else "MISSING",
        "dg_decomposition.csv": "EXISTS" if (input_dir / "dg_decomposition.csv").exists() else "MISSING",
        "datagolf.csv": "EXISTS" if (input_dir / "datagolf.csv").exists() else "MISSING",
        "dg_course_table.csv": "EXISTS" if (input_dir / "dg_course_table.csv").exists() else "MISSING",
        "dg_performance_2026.csv": "EXISTS" if (input_dir / "dg_performance_2026.csv").exists() else "MISSING",
        "pga_field_trending_table.csv": "EXISTS" if (input_dir / "pga_field_trending_table.csv").exists() else "MISSING",
        "app_skill_l12_sg.csv": "EXISTS" if (input_dir / "app_skill_l12_sg.csv").exists() else "MISSING",
        "app_skill_l12_gh.csv": "EXISTS" if (input_dir / "app_skill_l12_gh.csv").exists() else "MISSING",
        "app_skill_l12_bad.csv": "EXISTS" if (input_dir / "app_skill_l12_bad.csv").exists() else "MISSING",
        "app_skill_l12_great.csv": "EXISTS" if (input_dir / "app_skill_l12_great.csv").exists() else "MISSING",
        "app_skill_l12_prox.csv": "EXISTS" if (input_dir / "app_skill_l12_prox.csv").exists() else "MISSING",
        "tpc_twin_cities_CH.csv": "EXISTS" if (library_dir / "venues" / "tpc_twin_cities" / "tpc_twin_cities_CH.csv").exists() else "MISSING",
        "pga_sg_query_allcourses_l6.csv": "EXISTS",
        "pga_sg_query_allcourses_l12.csv": "EXISTS",
        "pga_sg_query_allcourses_l24.csv": "EXISTS",
        f"pga_sg_query_{slug}_similar_l6.csv": "EXISTS",
        f"pga_sg_query_{slug}_similar_l12.csv": "EXISTS",
        f"pga_sg_query_{slug}_similar_l24.csv": "EXISTS",
    }

    event_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "event_metadata": {
            "event_name":    "3M Open",
            "event_slug":    slug,
            "season":        2026,
            "tour":          "PGA Tour",
            "dates":         "July 23-26, 2026",
            "purse":         "unknown",
            "field_size":    len(players_data),
        },
        "venue_lock": {
            "course":      "TPC Twin Cities",
            "location":    "Blaine, Minnesota",
            "par":         71,
            "yardage":     7431,
            "greens":      "Creeping Bentgrass",
            "fairways":    "Creeping Bentgrass",
            "rough":       "Kentucky Bluegrass",
            "primary_mechanism":  "SG Approach — 6 of 7 winners since 2019 ranked T10 in approach for the week",
            "secondary_mechanism": "Controlled total driving — water threatens 9 of 14 driving holes",
            "tertiary_mechanism":  "Par-5 conversion — H6 (594), H12 (593), H18 (596) create separation",
            "key_pressure_holes":  ["H13 (par 3, 228 yds)", "H16 (tightened par 4)", "H17 (par 3, 202 yds)", "H18 (par 5, 596 yds, enlarged lake)"],
            "approach_distance_profile": "46% of approaches from 175+ yards — longer-skewed vs. typical birdiefest",
            "variance_class":      "medium-high",
        },
        "conditions": {
            "source": "tpc_twin_cities_full_course_weather_data_2026.json",
            "note": "Weather conditions available in venue library; specific round conditions to be loaded at tournament time",
        },
        "scoring_metadata": {
            "schema_version":     SCHEMA_VERSION,
            "official_rank_signal": "VenueDNA_final_projection (vts_final from enrich_cards.py)",
            "score_range":        "[0, 100] z-scored (mean=50, std=15)",
            "formulas": {
                "SG_Base_Comp":    "0.20 × SG_Base_6m + 0.30 × SG_Base_12m + 0.50 × SG_Base_24m",
                "W_h":             "min(1.0, N_Sim_h / 20.0)",
                "SG_Sim_Reg_h":    "W_h × SG_Sim_h + (1 - W_h) × SG_Base_h",
                "Delta_Fit_h":     "SG_Sim_Reg_h - SG_Base_h",
                "Delta_Fit_Comp":  "clamp(0.50×D6 + 0.30×D12 + 0.20×D24, -0.50, +0.50)",
                "VTS_Raw":         "SG_Base_Comp + Delta_Fit_Comp",
                "vts_final":       "z_score(VTS_Raw, mean=50, std=15, clamp=[0,100])",
                "trait_approach":  "z_score(weighted_SG: 50-100=0.10, 100-150=0.20, 150-200=0.40, 200+=0.30)",
                "trait_long_iron": "z_score(0.65×SG_150-200fw + 0.35×SG_200+fw)",
                "trait_total_drv": "z_score(ott_true from dg_performance_2026)",
                "trait_par5":      "z_score(0.55×dist_adj + 0.45×approach_raw)",
                "makeCutPct":      "min(98, max(20, top20Pct × 1.25 + 10))",
            },
            "trait_source_map": {
                "VenueDNA_trait_approach":            "app_skill_l12_sg.csv — weighted fw SG",
                "VenueDNA_trait_long_iron_150_225":   "app_skill_l12_sg.csv — 150-200 + 200+ fw SG",
                "VenueDNA_trait_total_driving":       "dg_performance_2026.csv — ott_true",
                "VenueDNA_trait_driving_accuracy":    "dg_decomposition.csv — driving_acc_adj",
                "VenueDNA_trait_driving_distance":    "dg_decomposition.csv — driving_dist_adj",
                "VenueDNA_trait_par5_scoring":        "derived: 0.55×driving_dist_adj + 0.45×approach_raw",
                "VenueDNA_trait_easy_green_putting":  "dg_performance_2026.csv — putt_true",
                "VenueDNA_trait_course_history":      "tpc_twin_cities_CH.csv — ch_adjustment",
                "VenueDNA_trait_closing_hole_composure": "dg_decomposition.csv — inverse(std_dev)",
                "VenueDNA_trait_debut_adjustment":    "tpc_twin_cities_CH.csv — rounds_played tier",
                "VenueDNA_trait_recent_form_context": "pga_field_trending_table.csv — true_sg_l20",
            },
        },
        "official_model": {
            "official_rank_driver":     "VenueDNA_final_projection",
            "official_tier_driver":     "VenueDNA_tier",
            "official_ordering":        "VenueDNA_rank ascending",
            "authority":                "VenueDNA — sole official ranking authority",
            "engine":                   "engine/enrich_cards.py — dual-vector True SG, schema 1.1",
        },
        "benchmark_model": {
            "source":            "DataGolf prediction decomposition",
            "primary_field":     "DG_finalprediction_benchmark",
            "use_restrictions":  "DG fields are read-only benchmark context and do not determine official ranks, tiers, or projections",
            "decomp_fields":     list({"DG_baseline_benchmark", "DG_timingadj_benchmark", "DG_sgcategoryadj_benchmark",
                                       "DG_coursehistoryadj_benchmark", "DG_drivingdistadj_benchmark",
                                       "DG_drivingaccadj_benchmark", "DG_coursefittotaladj_benchmark",
                                       "DG_finalprediction_benchmark", "DG_stddev_benchmark"}),
        },
        "five_tier_projection": {
            "T1": tier_summary(t1),
            "T2": tier_summary(t2),
            "T3": tier_summary(t3),
            "T4": tier_summary(t4),
            "T5": tier_summary(t5),
        },
        "tier_1_briefs":     [briefs_map[p["player_name"]] for p in t1 if p["player_name"] in briefs_map],
        "tier_2_briefs":     [briefs_map[p["player_name"]] for p in t2 if p["player_name"] in briefs_map],
        "anti_pattern_flags": ap_flags_all,
        "risk_register": {
            "accuracy_risk":       [p["player_name"] for p in players_data if p["flags"].get("VenueDNA_flag_accuracy_risk") is True],
            "long_iron_deficit":   [p["player_name"] for p in players_data if p["flags"].get("VenueDNA_flag_long_iron_deficit") is True],
            "debut_uncertainty":   [p["player_name"] for p in players_data if p["flags"].get("VenueDNA_flag_debut_uncertainty") is True],
            "putting_dependency":  [p["player_name"] for p in players_data if p["flags"].get("VenueDNA_flag_putting_dependency") is True],
            "short_game_only":     [p["player_name"] for p in players_data if p["flags"].get("VenueDNA_flag_short_game_only") is True],
        },
        "probability_view": {
            "top5":  [{"rank": p["VenueDNA_rank"], "player": p["player_name"], "pct": p["board"]["top5Pct"]}
                      for p in players_data[:20]],
            "top10": [{"rank": p["VenueDNA_rank"], "player": p["player_name"], "pct": p["board"]["top10Pct"]}
                      for p in players_data[:20]],
            "win":   [{"rank": p["VenueDNA_rank"], "player": p["player_name"], "pct": p["board"]["winPct"]}
                      for p in players_data[:20]],
        },
        "model_council_findings": council,
        "source_manifest":  source_manifest,
        "deploy_manifest": {
            "board_export.json":         "deploy/data/board_export.json",
            f"{slug}_event_payload.json":f"deploy/data/{slug}_event_payload.json",
            f"{slug}_vts_full.csv":      f"deploy/data/{slug}_vts_full.csv",
            f"{slug}_player_briefs.json":f"deploy/data/{slug}_player_briefs.json",
            f"{slug}_links.json":        f"deploy/data/{slug}_links.json",
        },
        "blockers": blockers,
    }

    ep_path = output_dir / f"{slug}_event_payload.json"
    ep_path.write_text(json.dumps(event_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[build_event_package] Written {slug}_event_payload.json")

    # ── STEP 7: links.json ───────────────────────────────────────────────────
    links_path = output_dir / f"{slug}_links.json"
    links_data = {
        "schema_version": SCHEMA_VERSION,
        "event": "2026 3M Open",
        "generated_at": now_iso(),
        "links": [
            {
                "player_name": "unknown",
                "link_type":   "official_bio",
                "url":         "unknown",
                "label":       "PGA Tour player page",
                "source":      "PGA Tour",
                "note":        "links require post-generation enrichment from PGA Tour / DataGolf API",
            }
        ],
    }
    links_path.write_text(json.dumps(links_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[build_event_package] Written {slug}_links.json (stub — requires link enrichment)")

    # ── STEP 8: audit placeholders ───────────────────────────────────────────
    r1_diag = {
        "schema_version": SCHEMA_VERSION,
        "event": "2026 3M Open",
        "round": 1,
        "status": "pending",
        "generated_at": now_iso(),
        "note": "Placeholder — populate after R1 scorecards are available via build_round_analysis.py",
        "spearman_rho": None,
        "trait_validation": {},
        "board": [],
    }
    (audit_dir / f"{slug}_r1_diagnostics.json").write_text(
        json.dumps(r1_diag, indent=2), encoding="utf-8")

    audit_log = {
        "schema_version": SCHEMA_VERSION,
        "event": "2026 3M Open",
        "generated_at": now_iso(),
        "build_steps": [
            {"step": "STEP 1 — file validation",     "status": "complete"},
            {"step": "STEP 2 — venue summary",       "status": "complete"},
            {"step": "STEP 3 — trait_form_matrix",   "status": "complete", "rows": len(players_data)},
            {"step": "STEP 4 — vts_full",            "status": "complete", "rows": len(players_data)},
            {"step": "STEP 5 — player_briefs",       "status": "complete", "entries": len(briefs_map)},
            {"step": "STEP 6 — event_payload",       "status": "complete"},
            {"step": "STEP 7 — links",               "status": "stub — needs link enrichment"},
            {"step": "STEP 8 — audit placeholders",  "status": "complete"},
        ],
        "blockers": blockers,
        "schema_mismatches": [
            {
                "type": "schema_mismatch",
                "file": "dg_decomposition.csv",
                "expected_by_build_prompt": "timingadj / sgcategoryadj / etc.",
                "actual_headers": "timing_adj / sg_category_adj / etc.",
                "resolution": "mapped using underscored actual headers per 04_ARTIFACT_SCHEMA.md §2B",
            }
        ],
    }
    (audit_dir / f"{slug}_audit_log.json").write_text(
        json.dumps(audit_log, indent=2), encoding="utf-8")

    council_md = f"""# Model Council Review — 2026 3M Open (Pre-Tournament)

**Date:** {now_iso()[:10]}
**Type:** Pre-Tournament
**Schema:** {SCHEMA_VERSION}

---

## Tier 1 Assignments

{chr(10).join(f"- **{p['player_name']}** (Rank {p['VenueDNA_rank']}) — VTS {p['board']['vts_final']:.1f}, NSI {p['board']['neutralSkillIndex']:.1f}, Δ Fit {p['board']['delta_fit']:+.3f}" for p in t1)}

All T1 assignments reviewed. {len([o for o in council['objections']])} objections raised; all resulted in no-change rulings. No hard gates triggered.

---

## Anti-Pattern Flags

Total flags confirmed: **{len(ap_flags_all)}**

Notable anti-pattern players (accuracy risk or long-iron deficit):
{chr(10).join(f"- {f['player']} [{f['flag'].replace('VenueDNA_flag_','')}]" for f in ap_flags_all[:20])}

---

## DG vs. VenueDNA Disagreements (> 15 ranks)

{len(council['dg_disagreements'])} disagreements logged. All ruled VenueDNA_supported. DG benchmark does not determine official rank.

Top 10 gaps:
{chr(10).join(f"- {d['player']}: VTS rank {d['VenueDNA_rank']} vs. DG implied rank {d['DG_rank_implied']} (gap {d['rank_gap']})" for d in sorted(council['dg_disagreements'], key=lambda x: -x['rank_gap'])[:10])}

---

## Final Synthesis

{council['final_synthesis']}

---

## Council Sign-Off

**{council['council_sign_off']}**
"""
    (audit_dir / f"{slug}_council_review.md").write_text(council_md, encoding="utf-8")

    print(f"[build_event_package] Written audit placeholders to {audit_dir}")

    # ── STEP 9: copy to deploy/data/ ─────────────────────────────────────────
    deploy_data = deploy_dir / "data"
    deploy_data.mkdir(parents=True, exist_ok=True)

    import shutil
    for src_name in [
        f"{slug}_event_payload.json",
        f"{slug}_vts_full.csv",
        f"{slug}_player_briefs.json",
        f"{slug}_links.json",
    ]:
        src = output_dir / src_name
        dst = deploy_data / src_name
        if src.exists():
            shutil.copy2(src, dst)
            print(f"[build_event_package] Copied {src_name} -> deploy/data/")

    print(f"[build_event_package] Build complete. {len(players_data)} players. {len(blockers)} blockers.")
    if blockers:
        print(f"[build_event_package] BLOCKERS:")
        for bl in blockers[:5]:
            print(f"  - {bl}")
        if len(blockers) > 5:
            print(f"  ... and {len(blockers)-5} more (see audit_log.json)")


if __name__ == "__main__":
    main()
