"""engine/enrich_cards.py
VenueDNA 3M Open 2026 — monolithic dual-vector + venue-trait enrichment pipeline.

Sections
  §1  Imports & constants
  §2  CSV loaders
  §3  Name matching
  §4  Dual-vector SG composites
  §5  Venue trait calculations
  §6  Anti-pattern gates
  §7  Math utilities
  §8  Sparkline parser
  §9  Narrative engine
  §10 Main pipeline
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# ── §1  Constants ──────────────────────────────────────────────────────────────

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

DELTA_CLAMP = 0.50

TEMPS       = {"win": 3.5, "top5": 5.0, "top10": 7.0, "top20": 10.0}
N_POSITIONS = {"win": 1,   "top5": 5,   "top10": 10,  "top20": 20}

ZNORM_MEAN, ZNORM_STD = 50.0, 15.0

# Venue trait weights (TPC Twin Cities venue profile §6)
VW_APPROACH  = 0.40
VW_LONG_IRON = 0.25
VW_OTT       = 0.20
VW_CH        = 0.10
VW_FORM      = 0.05

# Anti-pattern gate thresholds
BOMB_DIST_THRESH = 0.15     # driving_dist_adj above
BOMB_ACC_THRESH  = -0.05    # driving_acc_adj below
SG_APP_THRESH    = 0.20     # app_true below = weak approach
SG_SUM_THRESH    = 1.00     # putt_true + arg_true above = short-game reliant
PENALTY_BOMBER   = 0.92
PENALTY_SG_DEP   = 0.90

# Debut course-history haircut (venue profile §12)
DEBUT_CH_HAIRCUT = -0.25

# Live-round wave modifier (±VTS points on 0-100 scale)
WAVE_MODIFIER      = 1.5
EARLY_WAVE_CONTEXT = "capitalizing on favorable 7-9 mph morning winds."
LATE_WAVE_CONTEXT  = "facing tougher 11-14 mph afternoon winds."

# std_dev → VTS floor/ceil: 1 stroke ≈ 5 VTS points
STD_VTS_SCALE = 5.0

# Narrative thresholds (all per-round stroke units)
THRESH_ELITE_APP   = 1.00
THRESH_STRONG_APP  = 0.60
THRESH_VENUE_FIT   = 0.15   # delta_fit
THRESH_CTRL_POWER  = 0.60   # ott_true
THRESH_COURSE_PED  = 0.04   # ch_adjustment
THRESH_HOT_FORM    = 1.50   # true_sg_l20
THRESH_APP_DEFICIT = 0.00
THRESH_LI_GAP      = -0.05  # trait_long_iron_raw

# Display trait config — (label, venue_weight) in order matching d_keys
TRAIT_DISPLAY_CFG = [
    ("SG: Approach",     VW_APPROACH),
    ("App 150-200",      VW_LONG_IRON),
    ("Total Driving",    VW_OTT),
    ("Course History",   VW_CH),
    ("Recent Form",      VW_FORM),
    ("Par 5 Scoring",    0.00),
    ("Driving Accuracy", 0.00),
    ("Driving Distance", 0.00),
    ("SG: Putting",      0.00),
    ("Closing Holes",    0.00),
]

# ── §2  CSV Loaders ────────────────────────────────────────────────────────────

def safe_float(v: object, default: float = 0.0) -> float:
    try:
        s = str(v).strip().lower()
        return float(v) if s not in ("", "null", "none", "n/a", "nan") else default
    except (ValueError, TypeError):
        return default


def normalize_name(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip().strip('"').strip("'")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace(".", "").strip()


def load_field(path: Path) -> list[str]:
    """Ordered canonical player names from pga_field.csv."""
    if not path.exists():
        return []
    names = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = row.get("player_name", "").strip().strip('"')
            if n:
                names.append(n)
    return names


def load_field_ids(path: Path) -> dict[str, str]:
    """Returns {player_name: dg_id} from pga_field.csv. Names are 'Last, First' format."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = row.get("player_name", "").strip().strip('"')
            fid = row.get("dg_id", "").strip()
            if n and fid and fid.lower() != "null":
                result[n] = fid
    return result


def load_sg_csv(path: Path) -> dict[str, dict]:
    """{name: {rounds, total_mean}}"""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "rounds":     int(safe_float(row.get("rounds_played", 0))),
                    "total_mean": safe_float(row.get("total_mean", 0)),
                }
    return result


def load_app_skill(path: Path) -> dict[str, dict]:
    """{name: {sg_50_100, sg_100_150, sg_150_200, sg_200plus}} from sg-per-shot rows."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("stat", "").strip().lower() != "sg per shot":
                continue
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "sg_50_100":  safe_float(row.get("50_100_fw_value")),
                    "sg_100_150": safe_float(row.get("100_150_fw_value")),
                    "sg_150_200": safe_float(row.get("150_200_fw_value")),
                    "sg_200plus": safe_float(row.get("over_200_fw_value")),
                }
    return result


def load_app_prox(path: Path) -> dict[str, float]:
    """{name: prox_150_200_ft}  lower = closer = better."""
    result: dict[str, float] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("stat", "").strip().lower() != "proximity (ft)":
                continue
            name = row.get("player_name", "").strip().strip('"')
            raw  = row.get("150_200_fw_value", "")
            if name and str(raw).strip().lower() not in ("", "null", "none"):
                result[name] = safe_float(raw)
    return result


def load_performance(path: Path) -> dict[str, dict]:
    """{name: {putt_true, arg_true, app_true, ott_true}}"""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "putt_true": safe_float(row.get("putt_true")),
                    "arg_true":  safe_float(row.get("arg_true")),
                    "app_true":  safe_float(row.get("app_true")),
                    "ott_true":  safe_float(row.get("ott_true")),
                }
    return result


def load_decomp(path: Path) -> dict[str, dict]:
    """{name: {driving_acc_adj, driving_dist_adj, std_dev}}"""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "driving_acc_adj":  safe_float(row.get("driving_acc_adj")),
                    "driving_dist_adj": safe_float(row.get("driving_dist_adj")),
                    "std_dev":          safe_float(row.get("std_dev"), default=3.0),
                }
    return result


def load_ch(path: Path) -> dict[str, dict]:
    """{name: {ch_adjustment, experience_adj}}"""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "ch_adjustment":  safe_float(row.get("ch_adjustment")),
                    "experience_adj": safe_float(row.get("experience_adjustment")),
                }
    return result


def load_trending(path: Path) -> dict[str, dict]:
    """{name: {true_sg_l20, l5_starts}}"""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                result[name] = {
                    "true_sg_l20": safe_float(row.get("true_sg_l20")),
                    "l5_starts":   row.get("l5_starts", "").strip(),
                }
    return result


# ── §3  Name Matching ──────────────────────────────────────────────────────────

def build_lookup(data_dict: dict) -> dict[str, str]:
    """Return {norm_name: original_name} for fast exact-match lookup."""
    return {normalize_name(k): k for k in data_dict}


def resolve(name: str, data_dict: dict, lookup: dict,
            threshold: float = 0.85) -> object | None:
    """Left-join: exact match first, then difflib fuzzy at threshold."""
    norm = normalize_name(name)

    # Exact
    if norm in lookup:
        return data_dict[lookup[norm]]

    # Fuzzy — short Korean/hyphenated names survive because exact pass fires first
    best_r, best_orig = 0.0, None
    for norm_key, orig_key in lookup.items():
        r = difflib.SequenceMatcher(None, norm, norm_key).ratio()
        if r > best_r:
            best_r, best_orig = r, orig_key
    if best_r >= threshold and best_orig is not None:
        return data_dict[best_orig]

    return None


# ── §4  Dual-Vector SG Composites ─────────────────────────────────────────────

def debut_row() -> dict:
    return {"rounds": 0, "total_mean": 0.0}


def compute_horizon(base: dict, sim: dict) -> dict:
    w = min(1.0, sim.get("rounds", 0) / 20.0)
    sg_sim_reg = w * sim["total_mean"] + (1 - w) * base["total_mean"]
    return {"delta_fit": sg_sim_reg - base["total_mean"]}


def make_composites(all_resolved: dict, sim_resolved: dict) -> tuple[float, float, float]:
    """Return (sg_base_comp, sg_sim_comp, delta_fit_comp) from resolved horizon dicts."""
    sg_base = (0.20 * all_resolved["6m"]["total_mean"]
             + 0.30 * all_resolved["12m"]["total_mean"]
             + 0.50 * all_resolved["24m"]["total_mean"])
    delta = (0.50 * compute_horizon(all_resolved["6m"],  sim_resolved["6m"])["delta_fit"]
           + 0.30 * compute_horizon(all_resolved["12m"], sim_resolved["12m"])["delta_fit"]
           + 0.20 * compute_horizon(all_resolved["24m"], sim_resolved["24m"])["delta_fit"])
    delta = max(-DELTA_CLAMP, min(DELTA_CLAMP, delta))
    return sg_base, sg_base + delta, delta


# ── §5  Venue Trait Calculations ───────────────────────────────────────────────

def compute_trait_approach(skill: dict) -> float:
    """Distance-weighted fw SG per shot (per-shot units, ~[-0.1, 0.1])."""
    return (0.10 * skill["sg_50_100"]
          + 0.20 * skill["sg_100_150"]
          + 0.40 * skill["sg_150_200"]
          + 0.30 * skill["sg_200plus"])


def compute_trait_long_iron(skill: dict, prox_z_raw: float) -> float:
    """0.65 × sg_150_200 + 0.35 × z-raw(−prox). prox_z_raw already inverted."""
    return 0.65 * skill["sg_150_200"] + 0.35 * prox_z_raw


def prox_to_z_raw(prox: float, field_mean: float, field_std: float) -> float:
    """Lower proximity (ft) = better. Negate so higher return = better player."""
    return -(prox - field_mean) / (field_std + 1e-9)


# ── §6  Anti-Pattern Gates ─────────────────────────────────────────────────────

def apply_gates(raw: float, perf: dict, decomp: dict) -> tuple[float, list[str]]:
    """Multiplicative penalties before z-score. Returns (adjusted_raw, flags)."""
    flags: list[str] = []
    dist_adj = decomp.get("driving_dist_adj", 0.0)
    acc_adj  = decomp.get("driving_acc_adj",  0.0)
    app_true = perf.get("app_true", 0.0)
    putt     = perf.get("putt_true", 0.0)
    arg      = perf.get("arg_true",  0.0)

    if dist_adj > BOMB_DIST_THRESH and acc_adj < BOMB_ACC_THRESH:
        raw *= PENALTY_BOMBER
        flags.append("INACCURATE_BOMBER")

    if app_true < SG_APP_THRESH and (putt + arg) > SG_SUM_THRESH:
        raw *= PENALTY_SG_DEP
        flags.append("SHORT_GAME_RELIANT")

    return raw, flags


# ── §7  Math Utilities ─────────────────────────────────────────────────────────

def field_stats(values: list[float]) -> tuple[float, float]:
    valid = [v for v in values if v != 0.0]
    if not valid:
        return 0.0, 1.0
    mu  = sum(valid) / len(valid)
    var = sum((v - mu) ** 2 for v in valid) / len(valid)
    return mu, math.sqrt(var) if var > 0 else 1.0


def z_score_scale(values: list[float]) -> list[float]:
    mu, sd = field_stats(values)
    return [max(0.0, min(100.0, ZNORM_MEAN + ZNORM_STD * (v - mu) / sd))
            for v in values]


def tempered_softmax(scores: list[float], T: float, n_pos: int) -> list[float]:
    max_s = max(scores)
    exps  = [math.exp((s - max_s) / T) for s in scores]
    total = sum(exps)
    return [min(99.9, (e / total) * n_pos * 100) for e in exps]


def enforce_monotonicity(p: dict) -> None:
    p["top5Pct"]  = max(p["top5Pct"],  p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])


def assign_tier(rank: int) -> str:
    if rank <= 5:   return "T1"
    if rank <= 12:  return "T2"
    if rank <= 25:  return "T3"
    if rank <= 40:  return "T4"
    return "T5"


def make_cut_prob(top20: float) -> float:
    return min(98.0, max(20.0, top20 * 1.25 + 10.0))


# ── §8  Sparkline Parser ───────────────────────────────────────────────────────

def parse_l5_starts(raw: str) -> list[int]:
    """'tour-event-POS_...' → numeric array. CUT/WD/DQ/MDF/DNS → 80."""
    if not raw or not raw.strip():
        return []
    result: list[int] = []
    for entry in raw.strip().split("_"):
        parts   = entry.strip().split("-")
        pos_str = parts[-1].strip().upper()
        if pos_str in ("CUT", "WD", "DQ", "W/D", "MDF", "DNS"):
            result.append(80)
        else:
            pos_str = pos_str.lstrip("T")
            try:
                result.append(int(pos_str))
            except ValueError:
                result.append(80)
    return result


# ── §9  Narrative Engine ───────────────────────────────────────────────────────

def lastname_first_to_first_last(s: str) -> str:
    """'Doe, John' → 'John Doe' for name-matching compatibility."""
    if "," in s:
        last, first = s.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return s


def load_tee_times(path: Path) -> dict[str, dict]:
    """{norm_name: {r2_wave, r2_teetime}} from round2_tee_times.csv.
    CSV names are 'Last, First' matching pga_field.csv — normalized as-is."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("player_name", "").strip().strip('"').strip("'")
            if not raw:
                continue
            norm  = normalize_name(raw)
            wave  = row.get("r2_wave", "").strip().lower()
            ttime = row.get("r2_teetime", "").strip()
            if norm:
                result[norm] = {"r2_wave": wave, "r2_teetime": ttime}
    return result


def load_r1_sg(path: Path) -> dict[str, dict]:
    """{norm_name: {r1_score, sg_total, sg_approach}} from round1 SG file.
    Amateur rows (TOT == '(a)') carry an extra column that shifts SG fields right by 1."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("Player", "").strip().strip('"')
            if not name:
                continue
            is_amateur = row.get("TOT", "").strip() == "(a)"
            if is_amateur:
                r1_score    = row.get("SG-Off The Tee", "").strip()
                sg_approach = row.get("SG-Approach to Green (Rank)", "").strip()
                sg_total    = row.get("SG Total (Rank)", "").strip()
            else:
                r1_score    = row.get("R1", "").strip()
                sg_approach = row.get("SG-Approach to Green", "").strip()
                sg_total    = row.get("SG Total", "").strip()
            if not r1_score or r1_score == "-":
                continue
            result[normalize_name(name)] = {
                "r1_score":    r1_score,
                "sg_total":    safe_float(sg_total),
                "sg_approach": safe_float(sg_approach),
            }
    return result

def build_strength_tags(app_true: float, delta_fit: float, ott_true: float,
                        ch_adj: float, true_sg_l20: float) -> list[str]:
    tags: list[str] = []
    if app_true > THRESH_ELITE_APP:
        tags.append(f"Elite Iron Play (+{app_true:.2f})")
    elif app_true > THRESH_STRONG_APP:
        tags.append(f"Strong Approach Play (+{app_true:.2f})")
    if delta_fit > THRESH_VENUE_FIT:
        tags.append(f"Strong Venue Fit (+{delta_fit:.2f})")
    elif delta_fit > 0.05:
        tags.append(f"Positive Venue Fit (+{delta_fit:.2f})")
    if ott_true > THRESH_CTRL_POWER:
        tags.append("Controlled Power")
    if ch_adj > THRESH_COURSE_PED:
        tags.append("Proven Course Pedigree")
    if true_sg_l20 > THRESH_HOT_FORM:
        tags.append(f"Red-Hot Form ({true_sg_l20:.2f} SG L20)")
    if not tags:
        tags.append("Field-Average Profile")
    return tags


def build_weakness_tags(app_true: float, trait_long_iron_raw: float,
                        data_depth: str, course_debut: bool,
                        gate_flags: list[str]) -> list[str]:
    tags: list[str] = []
    if app_true < THRESH_APP_DEFICIT:
        tags.append("Approach Deficit")
    if "INACCURATE_BOMBER" in gate_flags:
        tags.append("Accuracy Risk")
    if course_debut:
        tags.append("Venue Debut")
    if trait_long_iron_raw < THRESH_LI_GAP:
        tags.append("Long-Iron Gap")
    if not tags:
        tags.append("No Clear Structural Risk")
    return tags


def build_headline(strength_tags: list[str], weakness_tags: list[str]) -> str:
    top = strength_tags[0]
    if top == "Field-Average Profile":
        return "Field-average fit — outcome driven by weekly form variance."
    if "Elite Iron Play" in top:
        return f"Approach-first contender — {top.lower()} at TPC's longer-skewed layout."
    if "Venue Fit" in top:
        return f"Structurally aligned — {top} creates upside above raw form."
    if "Course Pedigree" in top:
        return f"Track record matters here — {top} anchors the pre-tournament case."
    if "Red-Hot Form" in top:
        return f"Form player entering a birdiefest — {top} adds scoreboard pressure."
    return f"{top} is the primary driver of the pre-tournament case."


def build_win_case(player: str, app_true: float, delta_fit: float,
                   ott_true: float, strength_tags: list[str],
                   weakness_tags: list[str]) -> str:
    # Primary mechanism
    if app_true > THRESH_ELITE_APP:
        mech = (f"elite approach play (+{app_true:.2f} SG: App). "
                "TPC Twin Cities has crowned 6 of 7 winners since 2019 who ranked "
                "top-10 in approach for the week.")
    elif app_true > THRESH_STRONG_APP:
        mech = (f"above-average approach play (+{app_true:.2f} SG: App) at a venue "
                "where 46% of approaches arrive from 175+ yards.")
    elif delta_fit > THRESH_VENUE_FIT:
        mech = (f"a historically strong fit for similar-course scoring environments "
                f"(delta fit +{delta_fit:.2f}).")
    elif ott_true > THRESH_CTRL_POWER:
        mech = ("controlled total driving — water threatens 9 of 14 driving holes "
                "and the combination of distance with directional control is the structural edge.")
    else:
        mech = ("consistent ball-striking in TPC Twin Cities' birdiefest environment, "
                "where sustained iron quality separates contenders from scoreboard noise.")

    # Primary risk
    if "Accuracy Risk" in weakness_tags:
        risk = ("Primary risk: driver accuracy. Water on 9 driving holes amplifies "
                "dispersion into compounding mistakes.")
    elif "Long-Iron Gap" in weakness_tags:
        risk = ("Primary risk: long-iron gap. With 46% of approaches from 175+ yards, "
                "a 150-200 deficit creates a ceiling on birdie production from quality positions.")
    elif "Venue Debut" in weakness_tags:
        risk = ("First-timer risk: the closing stretch (H16-H17-H18) introduces "
                "decision-quality pressure without prior calibration under tournament conditions.")
    elif "Approach Deficit" in weakness_tags:
        risk = ("Approach play grades below field average — the primary win mechanism here. "
                "A short-game spike is required to compensate.")
    else:
        risk = ("Form trajectory holds the key — when approach and ball-striking peak, "
                "the contention path opens fully.")

    # Par-5 close
    if ott_true > 0.40:
        p5 = ("Par-5 conversion on H6, H12, and H18 (all 593-596 yards) "
              "will separate a top-10 from a podium finish.")
    else:
        p5 = ("Precision through the closing stretch (H16-H17-H18) — "
              "not just birdie volume — determines where this week lands.")

    return f"{player} wins through {mech} {risk} {p5}"


def build_live_r1_narrative(player: str, r1_score: str, sg_approach: float,
                            r2_wave: str) -> str:
    wave_ctx = EARLY_WAVE_CONTEXT if r2_wave == "early" else LATE_WAVE_CONTEXT
    sg_fmt = f"+{sg_approach:.3f}" if sg_approach >= 0 else f"{sg_approach:.3f}"
    return (
        f"[LIVE R1 UPDATE]: {player} shot {r1_score} in Round 1, gaining "
        f"{sg_fmt} strokes on Approach. They draw the {r2_wave} wave for "
        f"Round 2, {wave_ctx}"
    )


# ── §10  Main Pipeline ─────────────────────────────────────────────────────────

def check_field_completeness(field_names: list[str], trending_data: dict, lookup: dict) -> list[str]:
    """Return canonical-field players (by pga_field.csv) with no row in
    pga_field_trending_table.csv, using the same exact+fuzzy resolve()
    logic the rest of the pipeline uses — not a raw name diff, so this
    doesn't false-flag players the fuzzy matcher would have caught anyway.
    """
    missing = []
    for name in field_names:
        if resolve(name, trending_data, lookup, threshold=0.85) is None:
            missing.append(name)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="VenueDNA enrichment pipeline")
    parser.add_argument("--event", default="2026_3m_open")
    parser.add_argument("--live", default=None, choices=["r1", "r2", "r3", "r4"],
                        help="Enable live-round enrichment mode")
    args = parser.parse_args()

    event_dir  = _ROOT / "events" / args.event
    input_dir  = event_dir / "input"
    output_dir = event_dir / "output"
    deploy_dir = event_dir / "deploy" / "data"

    output_dir.mkdir(parents=True, exist_ok=True)
    deploy_dir.mkdir(parents=True, exist_ok=True)

    # ── Load all source files ──────────────────────────────────────────────────
    print("[enrich_cards] Loading source files…")

    field_names = load_field(input_dir / "pga_field.csv")
    if not field_names:
        print("[enrich_cards] ERROR — pga_field.csv missing or empty", file=sys.stderr)
        sys.exit(1)
    field_ids = load_field_ids(input_dir / "pga_field.csv")
    print(f"  Field: {len(field_names)} players, {len(field_ids)} with dg_id")

    all_sg = {h: load_sg_csv(input_dir / f) for h, f in ALL_COURSES_FILES.items()}
    sim_sg = {h: load_sg_csv(input_dir / f) for h, f in SIM_COURSES_FILES.items()}

    app_skill_data = load_app_skill(input_dir / "app_skill_l12_sg.csv")
    app_prox_data  = load_app_prox(input_dir  / "app_skill_l12_prox.csv")
    perf_data      = load_performance(input_dir / "dg_performance_2026.csv")
    decomp_data    = load_decomp(input_dir    / "dg_decomposition.csv")
    ch_data        = load_ch(input_dir        / "tpc_twin_cities_CH.csv")
    trending_data  = load_trending(input_dir  / "pga_field_trending_table.csv")

    _missing_trend = check_field_completeness(field_names, trending_data, build_lookup(trending_data))
    if _missing_trend:
        print(f"[enrich_cards] WARNING — {len(_missing_trend)} field player(s) missing from "
              f"pga_field_trending_table.csv (likely late field additions; Form/l5 data will "
              f"render blank, this is expected): {', '.join(_missing_trend)}", file=sys.stderr)

    # Build name-lookup tables once (exact pass; fuzzy fires per-player only on misses)
    lk = {
        "all_6m":  build_lookup(all_sg["6m"]),
        "all_12m": build_lookup(all_sg["12m"]),
        "all_24m": build_lookup(all_sg["24m"]),
        "sim_6m":  build_lookup(sim_sg["6m"]),
        "sim_12m": build_lookup(sim_sg["12m"]),
        "sim_24m": build_lookup(sim_sg["24m"]),
        "skill":   build_lookup(app_skill_data),
        "prox":    build_lookup(app_prox_data),
        "perf":    build_lookup(perf_data),
        "decomp":  build_lookup(decomp_data),
        "ch":      build_lookup(ch_data),
        "trend":   build_lookup(trending_data),
    }

    # Field-level proximity stats for prox→z-raw conversion
    prox_values          = list(app_prox_data.values())
    prox_mean, prox_std  = field_stats(prox_values) if prox_values else (30.0, 4.0)

    # Field-level std_dev fallback
    std_vals         = [v["std_dev"] for v in decomp_data.values() if v["std_dev"] > 0]
    field_std_mean   = sum(std_vals) / len(std_vals) if std_vals else 3.0

    # ── Per-player raw computation ─────────────────────────────────────────────
    print("[enrich_cards] Computing latent scores…")

    _EMPTY_SKILL  = {"sg_50_100": 0.0, "sg_100_150": 0.0, "sg_150_200": 0.0, "sg_200plus": 0.0}
    _EMPTY_PERF   = {"putt_true": 0.0, "arg_true": 0.0, "app_true": 0.0, "ott_true": 0.0}
    _EMPTY_DECOMP = {"driving_acc_adj": 0.0, "driving_dist_adj": 0.0, "std_dev": field_std_mean}
    _EMPTY_TREND  = {"true_sg_l20": 0.0, "l5_starts": ""}

    players_raw: list[dict] = []

    for name in field_names:
        # Dual-vector SG composites
        all_r = {
            "6m":  resolve(name, all_sg["6m"],  lk["all_6m"])  or debut_row(),
            "12m": resolve(name, all_sg["12m"], lk["all_12m"]) or debut_row(),
            "24m": resolve(name, all_sg["24m"], lk["all_24m"]) or debut_row(),
        }
        sim_r = {
            "6m":  resolve(name, sim_sg["6m"],  lk["sim_6m"])  or debut_row(),
            "12m": resolve(name, sim_sg["12m"], lk["sim_12m"]) or debut_row(),
            "24m": resolve(name, sim_sg["24m"], lk["sim_24m"]) or debut_row(),
        }

        any_sim    = any(sim_r[h]["rounds"] > 0 for h in ("6m", "12m", "24m"))
        data_depth = "FULL" if any_sim else "DEBUT"

        sg_base_comp, sg_sim_comp, delta_fit = make_composites(all_r, sim_r)

        # Supplementary data
        skill  = resolve(name, app_skill_data, lk["skill"])  or _EMPTY_SKILL.copy()
        prox   = resolve(name, app_prox_data,  lk["prox"])
        perf   = resolve(name, perf_data,      lk["perf"])   or _EMPTY_PERF.copy()
        decomp = resolve(name, decomp_data,    lk["decomp"]) or _EMPTY_DECOMP.copy()
        ch     = resolve(name, ch_data,        lk["ch"])
        trend  = resolve(name, trending_data,  lk["trend"])  or _EMPTY_TREND.copy()

        course_debut = (ch is None)
        if ch is None:
            # DEBUT haircut on course history; non-debuts with no CH data get neutral
            ch_adj = DEBUT_CH_HAIRCUT if data_depth == "DEBUT" else 0.0
        else:
            ch_adj = ch["ch_adjustment"]

        # Proximity z-raw (inverted: lower prox in feet → higher score)
        if prox is not None:
            prox_z_raw = prox_to_z_raw(prox, prox_mean, prox_std)
        else:
            prox_z_raw = 0.0   # imputed to field mean → z-raw = 0

        # Trait raw values
        trait_approach_raw  = compute_trait_approach(skill)
        trait_long_iron_raw = compute_trait_long_iron(skill, prox_z_raw)
        ott_true            = perf["ott_true"]
        app_true            = perf["app_true"]
        true_sg_l20         = trend["true_sg_l20"]

        # Combined latent (addends in SG-compatible units; z-scored after full field)
        combined_raw = (
            sg_sim_comp
            + VW_APPROACH  * trait_approach_raw
            + VW_LONG_IRON * trait_long_iron_raw
            + VW_OTT       * ott_true
            + VW_CH        * ch_adj
            + VW_FORM      * true_sg_l20
        )

        prepenalty_raw = combined_raw
        combined_raw, gate_flags = apply_gates(combined_raw, perf, decomp)

        # Raw values for display trait z-scoring (after full field collected)
        par5_raw      = 0.55 * ott_true + 0.45 * app_true
        composure_raw = 1.0 / (decomp["std_dev"] + 0.1)

        players_raw.append({
            # Identity
            "player":               name,
            "player_id":            field_ids.get(name),  # dg_id — immutable numeric join key
            "data_depth":           data_depth,
            "course_debut":         course_debut,
            # Dual-vector SG
            "sg_base_composite":    round(sg_base_comp,    4),
            "sg_similar_composite": round(sg_sim_comp,     4),
            "delta_fit":            round(delta_fit,        4),
            # Gate state
            "gate_flags":           gate_flags,
            # Latent scores (private; z-scored after loop)
            "_vts_raw":             combined_raw,
            "_nsi_raw":             sg_base_comp,
            "_prepenalty_raw":      prepenalty_raw,
            # Narrative inputs
            "app_true":             app_true,
            "ott_true":             ott_true,
            "ch_adjustment":        ch_adj,
            "true_sg_l20":          true_sg_l20,
            "trait_approach_raw":   round(trait_approach_raw,  4),
            "trait_long_iron_raw":  round(trait_long_iron_raw, 4),
            # Display-trait raws (private; z-scored after loop)
            "_d_approach":          app_true,
            "_d_long_iron":         trait_long_iron_raw,
            "_d_ott":               ott_true,
            "_d_ch":                ch_adj,
            "_d_form":              true_sg_l20,
            "_d_par5":              par5_raw,
            "_d_drv_acc":           decomp["driving_acc_adj"],
            "_d_drv_dist":          decomp["driving_dist_adj"],
            "_d_putt":              perf["putt_true"],
            "_d_composure":         composure_raw,
            # Finalized fields
            "l5_array":             parse_l5_starts(trend["l5_starts"]),
            "std_dev":              round(decomp["std_dev"], 3),
        })

    # ── Field-level z-scoring ─────────────────────────────────────────────────
    print("[enrich_cards] Z-scoring…")

    vts_scaled = z_score_scale([p["_vts_raw"]        for p in players_raw])
    nsi_scaled = z_score_scale([p["_nsi_raw"]        for p in players_raw])
    pre_scaled = z_score_scale([p["_prepenalty_raw"] for p in players_raw])

    d_keys = ["_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
              "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure"]
    d_scaled = {k: z_score_scale([p[k] for p in players_raw]) for k in d_keys}

    # ── Probability matrices ───────────────────────────────────────────────────
    print("[enrich_cards] Computing probability matrices…")

    raw_scores = [p["_vts_raw"] for p in players_raw]

    # ── Live round enrichment ─────────────────────────────────────────────────
    live_tee_times: dict = {}
    live_r1_sg: dict     = {}

    if args.live == "r1":
        print("[enrich_cards] Live R1 mode — loading round data…")
        live_tee_times = load_tee_times(
            event_dir / "output" / "round1" / "round2_tee_times.csv")
        live_r1_sg = load_r1_sg(
            event_dir / "output" / "round1" / "round1_player_strokes_gained.csv")
        print(f"  Tee times: {len(live_tee_times)} | R1 SG: {len(live_r1_sg)}")

        # Softmax on wave-adjusted VTS (0-100); scale temps proportionally so
        # the distribution width matches what raw-score temps produce.
        raw_std    = field_stats(raw_scores)[1]
        temp_scale = ZNORM_STD / max(raw_std, 0.01)

        wave_vts: list[float] = []
        for i, p in enumerate(players_raw):
            norm = normalize_name(p["player"])
            wave_info = live_tee_times.get(norm, {})
            wave      = wave_info.get("r2_wave", "")
            base      = vts_scaled[i]
            if wave == "early":
                adjusted = min(100.0, max(0.0, base + WAVE_MODIFIER))
            elif wave == "late":
                adjusted = min(100.0, max(0.0, base - WAVE_MODIFIER))
            else:
                adjusted = base
            wave_vts.append(adjusted)
            p["_live_vts"]   = round(adjusted, 1)
            p["_r2_wave"]    = wave
            p["_r2_teetime"] = wave_info.get("r2_teetime", "")

        win_probs  = tempered_softmax(wave_vts, TEMPS["win"]   * temp_scale, N_POSITIONS["win"])
        t5_probs   = tempered_softmax(wave_vts, TEMPS["top5"]  * temp_scale, N_POSITIONS["top5"])
        t10_probs  = tempered_softmax(wave_vts, TEMPS["top10"] * temp_scale, N_POSITIONS["top10"])
        t20_probs  = tempered_softmax(wave_vts, TEMPS["top20"] * temp_scale, N_POSITIONS["top20"])
    else:
        win_probs  = tempered_softmax(raw_scores, TEMPS["win"],   N_POSITIONS["win"])
        t5_probs   = tempered_softmax(raw_scores, TEMPS["top5"],  N_POSITIONS["top5"])
        t10_probs  = tempered_softmax(raw_scores, TEMPS["top10"], N_POSITIONS["top10"])
        t20_probs  = tempered_softmax(raw_scores, TEMPS["top20"], N_POSITIONS["top20"])

    # ── Assemble final records ─────────────────────────────────────────────────
    print("[enrich_cards] Assembling player records…")

    for i, p in enumerate(players_raw):
        vts = round(vts_scaled[i], 1)
        nsi = round(nsi_scaled[i], 1)
        pre = round(pre_scaled[i], 1)

        p["vts_final"]         = vts
        p["neutralSkillIndex"] = nsi
        p["prepenalty_vts"]    = pre if p["gate_flags"] else None

        # Probabilities — camelCase for app.js compat
        p["winPct"]   = round(win_probs[i],  1)
        p["top5Pct"]  = round(t5_probs[i],   1)
        p["top10Pct"] = round(t10_probs[i],  1)
        p["top20Pct"] = round(t20_probs[i],  1)
        enforce_monotonicity(p)
        p["makeCutPct"] = round(make_cut_prob(p["top20Pct"]), 1)
        p["missCutPct"] = round(100.0 - p["makeCutPct"], 1)

        # Snake-case aliases for verification scripts
        p["win_prob"]      = p["winPct"]
        p["top_5_prob"]    = p["top5Pct"]
        p["top_10_prob"]   = p["top10Pct"]
        p["top_20_prob"]   = p["top20Pct"]
        p["make_cut_prob"] = p["makeCutPct"]
        p["miss_cut_prob"] = p["missCutPct"]

        # VTS floor/ceiling: ±(std_dev × scale), clamped
        spread        = round(p["std_dev"] * STD_VTS_SCALE, 1)
        p["vts_floor"] = round(max(0.0,   vts - spread), 1)
        p["vts_ceil"]  = round(min(100.0, vts + spread), 1)

        # Display trait scores
        trait_scores = []
        for j, (label, weight) in enumerate(TRAIT_DISPLAY_CFG):
            trait_scores.append({
                "label":  label,
                "weight": weight,
                "score":  round(d_scaled[d_keys[j]][i], 1),
            })
        p["trait_scores"] = trait_scores

        # Archetype tag classification using z-scored trait percentiles
        _arc_dist = d_scaled["_d_drv_dist"][i]
        _arc_acc  = d_scaled["_d_drv_acc"][i]
        _arc_app  = d_scaled["_d_approach"][i]
        _arc_li   = d_scaled["_d_long_iron"][i]
        _arc_putt = d_scaled["_d_putt"][i]
        _arc_comp = d_scaled["_d_composure"][i]   # closing-holes / scrambling proxy for ARG
        archetype_tags: list[str] = []
        if _arc_dist >= 75 and _arc_acc <= 30:
            archetype_tags.append("Erratic Bomber")
        if _arc_putt >= 70 and _arc_comp >= 70 and _arc_app <= 40:
            archetype_tags.append("Short-Game Specialist")
        # Putting Reliant: raw sg_putt ≥ 60% of player's total positive SG
        _putt_v = p.get("_d_putt") or 0.0
        _pos_sg = sum(v for v in [
            p.get("app_true", 0.0), p.get("ott_true", 0.0),
            _putt_v, p.get("ch_adjustment", 0.0),
        ] if v and v > 0)
        if _pos_sg > 0 and _putt_v > 0 and _putt_v >= 0.6 * _pos_sg:
            archetype_tags.append("Putting Reliant")
        if _arc_li <= 30:
            archetype_tags.append("Weak Long-Iron")
        p["archetype_tags"] = archetype_tags

        # Narratives
        strength = build_strength_tags(
            p["app_true"], p["delta_fit"], p["ott_true"],
            p["ch_adjustment"], p["true_sg_l20"]
        )
        weakness = build_weakness_tags(
            p["app_true"], p["trait_long_iron_raw"],
            p["data_depth"], p["course_debut"], p["gate_flags"]
        )
        p["strength_tags"] = strength
        p["weakness_tags"] = weakness
        p["headline"]      = build_headline(strength, weakness)
        p["win_case"]      = build_win_case(
            p["player"], p["app_true"], p["delta_fit"],
            p["ott_true"], strength, weakness
        )
        p["anti_pattern_flags"] = p["gate_flags"]

        # Live fields + narrative injection
        p["player_name"] = p["player"]
        if args.live == "r1":
            # r1_sg keys are "First Last" (from SG CSV); field names are "Last, First"
            norm_fl = normalize_name(lastname_first_to_first_last(p["player"]))
            sg_info = live_r1_sg.get(norm_fl, {})
            wave    = p.get("_r2_wave", "")
            p["live_vts"]   = p.get("_live_vts", vts)
            p["r2_wave"]    = wave
            p["r2_teetime"] = p.get("_r2_teetime", "")
            if wave and sg_info:
                narrative = build_live_r1_narrative(
                    p["player"],
                    sg_info.get("r1_score", "—"),
                    sg_info.get("sg_approach", 0.0),
                    wave,
                )
                p["win_case"] = narrative + " " + p["win_case"]
        p["scouting_report"] = p["win_case"]

    # ── Sort + rank ────────────────────────────────────────────────────────────
    players_raw.sort(key=lambda p: p["vts_final"], reverse=True)
    for i, p in enumerate(players_raw, 1):
        p["rank"] = i
        p["tier"] = assign_tier(i)

    # ── Canonical output schema (drop private fields) ──────────────────────────
    _drop = {"_vts_raw", "_nsi_raw", "_prepenalty_raw", "gate_flags", "course_debut",
             "_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
             "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure",
             "_live_vts", "_r2_wave", "_r2_teetime"}

    _first = [
        "rank", "player", "player_name", "player_id", "tier", "vts_final", "live_vts",
        "neutralSkillIndex",
        "sg_base_composite", "sg_similar_composite", "delta_fit", "data_depth",
        "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
        "win_prob", "top_5_prob", "top_10_prob", "top_20_prob",
        "make_cut_prob", "miss_cut_prob",
        "prepenalty_vts", "vts_floor", "vts_ceil", "std_dev",
        "l5_array", "strength_tags", "weakness_tags", "headline", "win_case",
        "scouting_report",
        "trait_scores", "archetype_tags", "anti_pattern_flags",
        "app_true", "ott_true", "ch_adjustment", "true_sg_l20",
        "trait_approach_raw", "trait_long_iron_raw",
        "r2_wave", "r2_teetime",
    ]

    def reorder(p: dict) -> dict:
        out: dict = {}
        for k in _first:
            if k in p:
                out[k] = p[k]
        for k, v in p.items():
            if k not in out and k not in _drop:
                out[k] = v
        return out

    ordered = [reorder(p) for p in players_raw]

    # ── Write outputs ──────────────────────────────────────────────────────────
    _live_suffix = {"r1": "rd1", "r2": "rd2", "r3": "rd3", "r4": "rd4"}
    file_base = (f"2026_3m_open_{_live_suffix[args.live]}_payload.json"
                 if args.live else "2026_3m_open_event_payload.json")
    schema_ver = f"3m-live-{args.live}-v1.0" if args.live else "3m-enriched-v2.0"

    payload = {
        "schemaVersion": schema_ver,
        "generatedAt":   datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event":         "2026 3M Open",
        "venue":         "TPC Twin Cities",
        "fieldSize":     len(ordered),
        "players":       ordered,
    }
    json_str = json.dumps(payload, indent=2)

    deploy_path = deploy_dir / file_base
    output_path = output_dir / file_base

    deploy_path.write_text(json_str, encoding="utf-8")
    output_path.write_text(json_str, encoding="utf-8")

    print(f"[enrich_cards] Done — {len(ordered)} players written")
    print(f"  Deploy : {deploy_path}")
    print(f"  Output : {output_path}")

    debuts  = sum(1 for p in ordered if p["data_depth"] == "DEBUT")
    bombers = sum(1 for p in ordered if "INACCURATE_BOMBER" in (p["anti_pattern_flags"] or []))
    sgdeps  = sum(1 for p in ordered if "SHORT_GAME_RELIANT" in (p["anti_pattern_flags"] or []))
    print(f"  DEBUT:{debuts}  Bomber gates:{bombers}  SG-Reliant gates:{sgdeps}")
    print(f"  Top 5: {', '.join(p['player'] for p in ordered[:5])}")


if __name__ == "__main__":
    main()
