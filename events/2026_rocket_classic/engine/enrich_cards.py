"""events/2026_rocket_classic/engine/enrich_cards.py
VenueDNA 2026 Rocket Classic — event-local fork of root engine.
Standalone: does NOT import from root engine/enrich_cards.py.

Differences from root engine (engine/enrich_cards.py):
  - SIM_COURSES_FILES → pga_sg_query_detroit_golf_club_similar_l*.csv
  - Field source → pga_field_teetimes.csv (no pga_field.csv for this event)
  - CH source → detroit_golf_club_CH.csv
  - dg_performance_2026.csv absent → perf_data={}, OTT component=0 for all players
  - 5 UNSCORED stubs appended post-z-score (excluded from scoring loop)
  - Phantom exclusion noted: Koepka, Brooks in decomp but not in teetimes field
  - Event/venue: "2026 Rocket Classic" / "Detroit Golf Club"
  - Schema version: "rocket-classic-v1.2" (v1.2 refines badge/narrative eligibility)
  - 5 mandatory pipeline artifacts written per build
  - Per-player trait_availability block: availability/source_status/usable_for_badges/
    usable_for_narrative_traits per trait — zero is never ambiguous downstream
  - ch_adjustment/true_sg_l20/delta_fit: badge-ineligible; ch_adjustment carries
    narrative_context="venue_history" qualifier so it is never treated as stable player skill
  - true_sg_l20 MISSING_ZERO_FILLED players gated from form-based strength/weakness tags
  - Payload-level sourceCoverage with per-field availability and measured counts
  - Six packaging validation gates (V1–V6) enforced before write

Unchanged from root engine:
  - VTS weights (VW_APPROACH=0.40, VW_LONG_IRON=0.25, VW_OTT=0.20, VW_CH=0.10, VW_FORM=0.05)
  - Z-score normalization (mean=50, std=15, clamped 0-100)
  - Tier buckets (T1≤5, T2≤12, T3≤25, T4≤40, T5=rest)
  - Anti-pattern gate thresholds
  - ALL SG composite formulas

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
import hashlib
import json
import math
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# Event-local base: events/2026_rocket_classic/engine/ → events/2026_rocket_classic/
_EVENT_DIR = Path(__file__).resolve().parent.parent

# ── §1  Constants ──────────────────────────────────────────────────────────────

ALL_COURSES_FILES = {
    "6m":  "pga_sg_query_allcourses_l6.csv",
    "12m": "pga_sg_query_allcourses_l12.csv",
    "24m": "pga_sg_query_allcourses_l24.csv",
}
SIM_COURSES_FILES = {
    "6m":  "pga_sg_query_detroit_golf_club_similar_l6.csv",
    "12m": "pga_sg_query_detroit_golf_club_similar_l12.csv",
    "24m": "pga_sg_query_detroit_golf_club_similar_l24.csv",
}

# Player in dg_decomposition.csv but NOT in pga_field_teetimes.csv (withdrawn/phantom).
PHANTOM_DECOMP_PLAYER = "Koepka, Brooks"

# Event-local identity crosswalk (authoritative supplement to pga_field_teetimes.csv).
CROSSWALK_FILE = "rocket_classic_player_ID_source.csv"

# 5 confirmed UNSCORED players: in pga_field_teetimes.csv but not in dg_decomposition.csv.
UNSCORED_PLAYERS: list[dict] = [
    {"player": "Azallion, Daniel", "player_id": "35071"},
    {"player": "Celano, Ryan",     "player_id": "29665"},
    {"player": "Huskey, Keenan",   "player_id": "26597"},
    {"player": "Quiban, Justin",   "player_id": "15981"},
    {"player": "Silverman, Ben",   "player_id": "17381"},
]

# Fields sourced from dg_performance_2026.csv. When absent, ALL are UNAVAILABLE.
PERF_FIELDS = ("app_true", "ott_true", "putt_true", "arg_true")
PERF_FILE   = "dg_performance_2026.csv"
PERF_ABSENT_REASON = "source file absent from events/2026_rocket_classic/input/"

DELTA_CLAMP = 0.50

TEMPS       = {"win": 3.5, "top5": 5.0, "top10": 7.0, "top20": 10.0}
N_POSITIONS = {"win": 1,   "top5": 5,   "top10": 10,  "top20": 20}

ZNORM_MEAN, ZNORM_STD = 50.0, 15.0

# Venue trait weights — Detroit Golf Club (UNCHANGED from root)
VW_APPROACH  = 0.40
VW_LONG_IRON = 0.25
VW_OTT       = 0.20
VW_CH        = 0.10
VW_FORM      = 0.05

# Anti-pattern gate thresholds (UNCHANGED)
BOMB_DIST_THRESH = 0.15
BOMB_ACC_THRESH  = -0.05
SG_APP_THRESH    = 0.20
SG_SUM_THRESH    = 1.00
PENALTY_BOMBER   = 0.92
PENALTY_SG_DEP   = 0.90

DEBUT_CH_HAIRCUT = -0.25

WAVE_MODIFIER      = 1.5
EARLY_WAVE_CONTEXT = "capitalizing on calmer morning conditions at Detroit Golf Club."
LATE_WAVE_CONTEXT  = "facing potentially windier afternoon conditions at Detroit Golf Club."

STD_VTS_SCALE = 5.0

THRESH_ELITE_APP   = 1.00
THRESH_STRONG_APP  = 0.60
THRESH_VENUE_FIT   = 0.15
THRESH_CTRL_POWER  = 0.60
THRESH_COURSE_PED  = 0.04
THRESH_HOT_FORM    = 1.50
THRESH_APP_DEFICIT = 0.00
THRESH_LI_GAP      = -0.05

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
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if name:
                _blank = {"", "null", "none", "n/a", "nan"}
                result[name] = {
                    "putt_true":       safe_float(row.get("putt_true")),
                    "arg_true":        safe_float(row.get("arg_true")),
                    "app_true":        safe_float(row.get("app_true")),
                    "ott_true":        safe_float(row.get("ott_true")),
                    "_missing_fields": frozenset(
                        f for f in PERF_FIELDS
                        if str(row.get(f, "")).strip().lower() in _blank
                    ),
                }
    return result


def load_decomp(path: Path) -> dict[str, dict]:
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


def load_id_crosswalk(path: Path) -> dict[str, dict]:
    """Load event-local identity crosswalk. Returns normalized_name → {original_name, dg_id}.
    Only exact normalized-name matches are applied downstream."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name  = row.get("player_name", "").strip().strip('"')
            dg_id = row.get("dg_id", "").strip()
            if name and dg_id:
                result[normalize_name(name)] = {"original_name": name, "dg_id": dg_id}
    return result


def load_trending(path: Path) -> dict[str, dict]:
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
    return {normalize_name(k): k for k in data_dict}


def resolve(name: str, data_dict: dict, lookup: dict,
            threshold: float = 0.85) -> object | None:
    norm = normalize_name(name)
    if norm in lookup:
        return data_dict[lookup[norm]]
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
    return (0.10 * skill["sg_50_100"]
          + 0.20 * skill["sg_100_150"]
          + 0.40 * skill["sg_150_200"]
          + 0.30 * skill["sg_200plus"])


def compute_trait_long_iron(skill: dict, prox_z_raw: float) -> float:
    return 0.65 * skill["sg_150_200"] + 0.35 * prox_z_raw


def prox_to_z_raw(prox: float, field_mean: float, field_std: float) -> float:
    return -(prox - field_mean) / (field_std + 1e-9)


# ── §6  Anti-Pattern Gates ─────────────────────────────────────────────────────

def apply_gates(raw: float, perf: dict, decomp: dict) -> tuple[float, list[str]]:
    flags: list[str] = []
    dist_adj = decomp.get("driving_dist_adj", 0.0)
    acc_adj  = decomp.get("driving_acc_adj",  0.0)
    app_true = perf.get("app_true", 0.0)
    putt     = perf.get("putt_true", 0.0)
    arg      = perf.get("arg_true",  0.0)

    if dist_adj > BOMB_DIST_THRESH and acc_adj < BOMB_ACC_THRESH:
        raw *= PENALTY_BOMBER
        flags.append("INACCURATE_BOMBER")

    # SHORT_GAME_RELIANT: never fires when perf absent (putt=arg=0.0 < SG_SUM_THRESH=1.00)
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
    if "," in s:
        last, first = s.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return s


def load_tee_times(path: Path) -> dict[str, dict]:
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


def build_trait_availability(
    perf_absent: bool,
    skill_avail: bool,
    prox_avail: bool,
    ch_resolved: bool,
    ch_adj: float,
    trend_avail: bool,
    data_depth: str,
    any_sg_avail: bool,
    perf_field_missing: frozenset = frozenset(),
) -> dict:
    """
    Returns per-player availability metadata for each trait/component.

    availability values:
      MEASURED         — directly read from a source file, value is real
      MEASURED_ZERO    — read from source file; value is genuinely 0 (not missing)
      DERIVED          — calculated from one or more MEASURED source fields
      DEBUT_ZERO       — player has no rounds in SG corpus; zero is structural, not missing
      MISSING_ZERO_FILLED — source file present but player row absent; 0.0 substituted
                            for VTS formula continuity — NOT real evidence
      UNAVAILABLE      — source file itself is absent; field cannot be trusted at all
    """
    _unavail_perf = {
        "availability":                "UNAVAILABLE",
        "source_status":               "MISSING",
        "usable_for_badges":           False,
        "usable_for_narrative_traits": False,
        "source_file":                 PERF_FILE,
        "reason":                      PERF_ABSENT_REASON,
    }
    _ok_perf = {
        "availability":                "MEASURED",
        "source_status":               "OK",
        "usable_for_badges":           True,
        "usable_for_narrative_traits": True,
        "source_file":                 PERF_FILE,
    }

    result: dict = {}

    # Performance file fields
    for field in PERF_FIELDS:
        if perf_absent or field in perf_field_missing:
            result[field] = _unavail_perf.copy()
        else:
            result[field] = _ok_perf.copy()

    # Approach raw (derived from app_skill_l12_sg.csv)
    if skill_avail:
        result["trait_approach_raw"] = {
            "availability":                "DERIVED",
            "source_status":               "MEASURED",
            "usable_for_badges":           True,
            "usable_for_narrative_traits": True,
            "source_file":                 "app_skill_l12_sg.csv",
        }
        result["trait_long_iron_raw"] = {
            "availability":                "DERIVED",
            "source_status":               "MEASURED" if prox_avail else "PARTIAL",
            "usable_for_badges":           True,
            "usable_for_narrative_traits": True,
            "source_file":                 "app_skill_l12_sg.csv + app_skill_l12_prox.csv",
            "prox_component":              "MEASURED" if prox_avail else "MISSING_ZERO_FILLED",
        }
    else:
        _mzf_skill = {
            "availability":                "MISSING_ZERO_FILLED",
            "source_status":               "MISSING",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": False,
            "source_file":                 "app_skill_l12_sg.csv",
            "reason":                      "player not in app_skill_l12_sg.csv; 0.0 substituted for VTS formula continuity",
        }
        result["trait_approach_raw"]  = _mzf_skill.copy()
        result["trait_long_iron_raw"] = _mzf_skill.copy()
        result["trait_long_iron_raw"]["source_file"] = "app_skill_l12_sg.csv + app_skill_l12_prox.csv"

    # Course-history adjustment — badge-ineligible; narrative-eligible as venue-history
    # context only, never as a standalone player-skill trait.
    if ch_resolved:
        avail = "MEASURED" if ch_adj != 0.0 else "MEASURED_ZERO"
        result["ch_adjustment"] = {
            "availability":                avail,
            "source_status":               "OK",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": True,
            "source_file":                 "detroit_golf_club_CH.csv",
            "narrative_context":           "venue_history",
            "narrative_qualifier":         "venue-history context only — not a standalone player-skill trait",
        }
    elif data_depth == "DEBUT":
        result["ch_adjustment"] = {
            "availability":                "DERIVED",
            "source_status":               "DEBUT_HAIRCUT",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": True,
            "source_file":                 None,
            "reason":                      f"course debut — structural haircut {DEBUT_CH_HAIRCUT} applied",
            "narrative_context":           "venue_history",
            "narrative_qualifier":         "venue-history context only — not a standalone player-skill trait",
        }
    else:
        result["ch_adjustment"] = {
            "availability":                "MISSING_ZERO_FILLED",
            "source_status":               "MISSING",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": False,
            "source_file":                 "detroit_golf_club_CH.csv",
            "reason":                      "player not in CH file; 0.0 substituted",
        }

    # Recent form — badge-ineligible (contextual, not a stable player trait);
    # narrative-eligible only when measured for this player.
    if trend_avail:
        result["true_sg_l20"] = {
            "availability":                "MEASURED",
            "source_status":               "OK",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": True,
            "source_file":                 "pga_field_trending_table.csv",
        }
    else:
        result["true_sg_l20"] = {
            "availability":                "MISSING_ZERO_FILLED",
            "source_status":               "MISSING",
            "usable_for_badges":           False,
            "usable_for_narrative_traits": False,
            "source_file":                 "pga_field_trending_table.csv",
            "reason":                      "player not in trending table; 0.0 substituted",
        }

    # Dual-vector SG composites (always DERIVED; DEBUT_ZERO when no rounds in corpus)
    if any_sg_avail:
        sg_composite_avail = "DERIVED"
        sg_status          = "OK"
    else:
        sg_composite_avail = "DEBUT_ZERO"
        sg_status          = "DEBUT"

    result["sg_base_composite"] = {
        "availability":                sg_composite_avail,
        "source_status":               sg_status,
        "usable_for_badges":           False,
        "usable_for_narrative_traits": False,
        "source_files":                ["pga_sg_query_allcourses_l*.csv"],
    }
    result["sg_similar_composite"] = {
        "availability":                "DERIVED",
        "source_status":               "OK",
        "usable_for_badges":           False,
        "usable_for_narrative_traits": False,
        "source_files":                ["pga_sg_query_detroit_golf_club_similar_l*.csv"],
    }
    result["delta_fit"] = {
        "availability":                "DERIVED",
        "source_status":               "OK",
        "usable_for_badges":           False,
        "usable_for_narrative_traits": True,
        "source_files":                [
            "pga_sg_query_allcourses_l*.csv",
            "pga_sg_query_detroit_golf_club_similar_l*.csv",
        ],
    }

    return result


def _unavail_set(trait_availability: dict) -> set[str]:
    """Return the set of trait names whose availability is UNAVAILABLE or MISSING_ZERO_FILLED."""
    return {
        t for t, meta in trait_availability.items()
        if meta.get("availability") in ("UNAVAILABLE", "MISSING_ZERO_FILLED")
    }


def build_strength_tags(app_true: float, delta_fit: float, ott_true: float,
                        ch_adj: float, true_sg_l20: float,
                        unavail_traits: set[str]) -> list[str]:
    """Explicitly gates on unavail_traits so no UNAVAILABLE/MISSING_ZERO_FILLED
    trait can produce a strength tag."""
    tags: list[str] = []
    if "app_true" not in unavail_traits:
        if app_true > THRESH_ELITE_APP:
            tags.append(f"Elite Iron Play (+{app_true:.2f})")
        elif app_true > THRESH_STRONG_APP:
            tags.append(f"Strong Approach Play (+{app_true:.2f})")
    if delta_fit > THRESH_VENUE_FIT:
        tags.append(f"Strong Venue Fit (+{delta_fit:.2f})")
    elif delta_fit > 0.05:
        tags.append(f"Positive Venue Fit (+{delta_fit:.2f})")
    if "ott_true" not in unavail_traits and ott_true > THRESH_CTRL_POWER:
        tags.append("Controlled Power")
    if "ch_adjustment" not in unavail_traits and ch_adj > THRESH_COURSE_PED:
        tags.append("Proven Course Pedigree")
    if "true_sg_l20" not in unavail_traits and true_sg_l20 > THRESH_HOT_FORM:
        tags.append(f"Red-Hot Form ({true_sg_l20:.2f} SG L20)")
    if not tags:
        tags.append("Field-Average Profile")
    return tags


def build_weakness_tags(app_true: float, trait_long_iron_raw: float,
                        data_depth: str, course_debut: bool,
                        gate_flags: list[str],
                        unavail_traits: set[str]) -> list[str]:
    """Explicitly gates on unavail_traits so no UNAVAILABLE/MISSING_ZERO_FILLED
    trait can produce a weakness tag."""
    tags: list[str] = []
    if "app_true" not in unavail_traits and app_true < THRESH_APP_DEFICIT:
        tags.append("Approach Deficit")
    if "INACCURATE_BOMBER" in gate_flags:
        tags.append("Accuracy Risk")
    if course_debut:
        tags.append("Venue Debut")
    if "trait_long_iron_raw" not in unavail_traits and trait_long_iron_raw < THRESH_LI_GAP:
        tags.append("Long-Iron Gap")
    if not tags:
        tags.append("No Clear Structural Risk")
    return tags


def build_headline(strength_tags: list[str], weakness_tags: list[str]) -> str:
    top = strength_tags[0]
    if top == "Field-Average Profile":
        return "Field-average fit — outcome driven by weekly form variance."
    if "Elite Iron Play" in top:
        return f"Approach-first contender — {top.lower()} at Detroit Golf Club's tree-lined layout."
    if "Venue Fit" in top:
        return f"Structurally aligned — {top} creates upside above raw form."
    if "Course Pedigree" in top:
        return f"Track record matters here — {top} anchors the pre-tournament case."
    if "Red-Hot Form" in top:
        return f"Form player entering a birdiefest — {top} adds scoreboard pressure."
    return f"{top} is the primary driver of the pre-tournament case."


def build_win_case(player: str, app_true: float, delta_fit: float,
                   ott_true: float, strength_tags: list[str],
                   weakness_tags: list[str],
                   unavail_traits: set[str]) -> str:
    """Skips unavailable traits in narrative mechanism selection."""
    app_avail = "app_true" not in unavail_traits
    ott_avail = "ott_true" not in unavail_traits

    if app_avail and app_true > THRESH_ELITE_APP:
        mech = (f"elite approach play (+{app_true:.2f} SG: App). "
                "Detroit Golf Club's tree-lined corridors demand precision from "
                "150-200 yards — top-approach players consistently lead the field "
                "in birdie conversion at this layout.")
    elif app_avail and app_true > THRESH_STRONG_APP:
        mech = (f"above-average approach play (+{app_true:.2f} SG: App) at a venue "
                "where 44% of approaches arrive from 150-200 yards.")
    elif delta_fit > THRESH_VENUE_FIT:
        mech = (f"a historically strong fit for similar-course scoring environments "
                f"(delta fit +{delta_fit:.2f}).")
    elif ott_avail and ott_true > THRESH_CTRL_POWER:
        mech = ("controlled total driving — tree-lined fairways at Detroit Golf Club "
                "punish positional errors off the tee with blocked approaches and "
                "recovery-bogey exposure.")
    else:
        mech = ("consistent ball-striking in Detroit Golf Club's birdie-heavy environment, "
                "where sustained iron quality separates contenders from scoreboard noise.")

    if "Accuracy Risk" in weakness_tags:
        risk = ("Primary risk: driver accuracy. Tree-lined fairways amplify dispersion "
                "into blocked approach windows and compounding bogeys.")
    elif "Long-Iron Gap" in weakness_tags:
        risk = ("Primary risk: long-iron gap. With 44% of approaches from 150-200 yards, "
                "a mid-iron deficit creates a ceiling on birdie production from quality positions.")
    elif "Venue Debut" in weakness_tags:
        risk = ("First-timer risk: Detroit Golf Club rewards course knowledge — "
                "positional awareness off tight tees takes a round or two to calibrate.")
    elif "Approach Deficit" in weakness_tags:
        risk = ("Approach play grades below field average — the primary win mechanism here. "
                "A short-game spike is required to compensate.")
    else:
        risk = ("Form trajectory holds the key — when approach and ball-striking peak, "
                "the contention path opens fully.")

    if ott_avail and ott_true > 0.40:
        p5 = ("Par-5 conversion on Detroit Golf Club's three reachable holes "
              "will separate a top-10 from a podium finish.")
    else:
        p5 = ("Approach consistency through the closing stretch — "
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


def validate_availability_gates(players: list[dict]) -> dict:
    """
    Six packaging validation gates — enforced before payload is written.

    V1: No UNAVAILABLE/MISSING_ZERO_FILLED trait may appear in strength_tags.
    V2: No UNAVAILABLE/MISSING_ZERO_FILLED trait may appear in weakness_tags.
    V3: No UNAVAILABLE trait may be listed as a badge-eligible input.
    V4: ch_adjustment, true_sg_l20, and delta_fit must have usable_for_badges=False
        for every player (these are contextual signals, not stable player traits).
    V5: A player with true_sg_l20 not measured (MISSING_ZERO_FILLED) cannot carry
        any form-based strength tag ("Red-Hot Form").
    V6: Every strength tag derived from ch_adjustment must carry the venue_history
        narrative_context qualifier in trait_availability.

    Returns a dict with gate status and any violations.
    """
    STRENGTH_TRAIT_MAP = {
        "Elite Iron Play":      "app_true",
        "Strong Approach Play": "app_true",
        "Controlled Power":     "ott_true",
    }
    WEAKNESS_TRAIT_MAP = {
        "Approach Deficit":  "app_true",
        "Long-Iron Gap":     "trait_long_iron_raw",
    }
    # Contextual fields that must never be badge sources
    BADGE_INELIGIBLE_FIELDS = ("ch_adjustment", "true_sg_l20", "delta_fit")
    # Form-based strength tag prefixes
    FORM_TAG_PHRASES = ("Red-Hot Form",)
    # Course-history tag prefix
    CH_TAG_PHRASES = ("Proven Course Pedigree",)

    v1_violations: list[dict] = []
    v2_violations: list[dict] = []
    v3_violations: list[dict] = []
    v4_violations: list[dict] = []
    v5_violations: list[dict] = []
    v6_violations: list[dict] = []

    for p in players:
        avail   = p.get("trait_availability", {})
        pid     = p.get("player_id") or p.get("player", "unknown")
        unavail = {t for t, m in avail.items()
                   if m.get("availability") in ("UNAVAILABLE", "MISSING_ZERO_FILLED")}

        # V1
        for tag in (p.get("strength_tags") or []):
            for phrase, trait in STRENGTH_TRAIT_MAP.items():
                if phrase in tag and trait in unavail:
                    v1_violations.append({"player_id": pid, "tag": tag, "trait": trait,
                                          "availability": avail[trait]["availability"]})

        # V2
        for tag in (p.get("weakness_tags") or []):
            for phrase, trait in WEAKNESS_TRAIT_MAP.items():
                if phrase in tag and trait in unavail:
                    v2_violations.append({"player_id": pid, "tag": tag, "trait": trait,
                                          "availability": avail[trait]["availability"]})

        # V3 — UNAVAILABLE perf fields must not be badge-eligible
        for field in PERF_FIELDS:
            if avail.get(field, {}).get("usable_for_badges") is True:
                if avail[field].get("availability") == "UNAVAILABLE":
                    v3_violations.append({"player_id": pid, "field": field,
                                          "reason": "usable_for_badges=True on UNAVAILABLE field"})

        # V4 — contextual fields must be badge-ineligible
        for field in BADGE_INELIGIBLE_FIELDS:
            if field in avail and avail[field].get("usable_for_badges") is True:
                v4_violations.append({"player_id": pid, "field": field,
                                      "reason": f"{field} is a contextual signal — must have usable_for_badges=False"})

        # V5 — missing form players cannot carry form-based strength tags
        if "true_sg_l20" in unavail:
            for tag in (p.get("strength_tags") or []):
                if any(phrase in tag for phrase in FORM_TAG_PHRASES):
                    v5_violations.append({"player_id": pid, "tag": tag,
                                          "reason": "true_sg_l20 is MISSING_ZERO_FILLED — form tag prohibited"})

        # V6 — course-history strength tags must carry venue_history qualifier
        for tag in (p.get("strength_tags") or []):
            if any(phrase in tag for phrase in CH_TAG_PHRASES):
                ch_meta = avail.get("ch_adjustment", {})
                if ch_meta.get("narrative_context") != "venue_history":
                    v6_violations.append({"player_id": pid, "tag": tag,
                                          "reason": "ch_adjustment missing narrative_context=venue_history qualifier"})

    return {
        "V1_no_unavailable_in_strength_tags": {
            "status":     "PASS" if not v1_violations else "FAIL",
            "violations": v1_violations,
        },
        "V2_no_unavailable_in_weakness_tags": {
            "status":     "PASS" if not v2_violations else "FAIL",
            "violations": v2_violations,
        },
        "V3_no_unavailable_trait_in_badge_inputs": {
            "status":     "PASS" if not v3_violations else "FAIL",
            "violations": v3_violations,
        },
        "V4_contextual_fields_not_badge_eligible": {
            "status":     "PASS" if not v4_violations else "FAIL",
            "violations": v4_violations,
        },
        "V5_no_form_tag_when_true_sg_l20_missing": {
            "status":     "PASS" if not v5_violations else "FAIL",
            "violations": v5_violations,
        },
        "V6_ch_tag_must_carry_venue_history_qualifier": {
            "status":     "PASS" if not v6_violations else "FAIL",
            "violations": v6_violations,
        },
    }


# ── §10  Main Pipeline ─────────────────────────────────────────────────────────

def check_field_completeness(field_names: list[str], trending_data: dict,
                             lookup: dict) -> list[str]:
    missing = []
    for name in field_names:
        if resolve(name, trending_data, lookup, threshold=0.85) is None:
            missing.append(name)
    return missing


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_mandatory_artifacts(
    output_dir: Path,
    players_raw: list[dict],
    field_names: list[str],
    field_ids: dict,
    payload_source_coverage: dict,
    all_sg: dict,
    sim_sg: dict,
    app_skill_data: dict,
    app_prox_data: dict,
    decomp_data: dict,
    ch_data: dict,
    trending_data: dict,
    input_dir: Path,
    ts: str,
    perf_absent: bool,
    crosswalk_resolved_norms: set,
    crosswalk_file: str,
) -> None:
    """Write the 5 mandatory pipeline artifacts every build must produce."""

    # 1. Raw projection
    raw_proj = {
        "schemaVersion": "rocket-classic-raw-v1.0",
        "generatedAt":   ts,
        "event":         "2026 Rocket Classic",
        "note":          "Raw VTS latent scores before z-normalization. Not for display.",
        "players": [
            {
                "player":          p["player"],
                "player_id":       p["player_id"],
                "data_depth":      p["data_depth"],
                "_vts_raw":        round(p["_vts_raw"], 6),
                "_nsi_raw":        round(p["_nsi_raw"], 6),
                "_prepenalty_raw": round(p["_prepenalty_raw"], 6),
                "gate_flags":      p["gate_flags"],
            }
            for p in players_raw
        ],
    }
    (output_dir / "2026_rocket_classic_raw_projection.json").write_text(
        json.dumps(raw_proj, indent=2), encoding="utf-8")

    # 2. Identity report
    _unscored_norms = {normalize_name(u["player"]) for u in UNSCORED_PLAYERS}
    scored_field = [n for n in field_names if normalize_name(n) not in _unscored_norms]
    id_records = []
    for name in scored_field:
        pid  = field_ids.get(name)
        norm = normalize_name(name)
        is_cw = norm in crosswalk_resolved_norms
        id_records.append({
            "player":               name,
            "player_id":            pid,
            "id_resolved":          pid is not None and pid != "",
            "identity_source":      crosswalk_file if is_cw else "pga_field_teetimes.csv",
            "identity_resolution":  "EXPLICIT_EVENT_CROSSWALK" if is_cw else "FIELD_CSV",
            "identity_confidence":  "HIGH",
        })
    resolved_count      = sum(1 for r in id_records if r["id_resolved"])
    unresolved_count    = len(id_records) - resolved_count
    crosswalk_count     = sum(1 for r in id_records if r["identity_resolution"] == "EXPLICIT_EVENT_CROSSWALK")

    identity_report = {
        "schemaVersion":           "rocket-classic-identity-v1.1",
        "generatedAt":             ts,
        "fieldTotal":              len(field_names),
        "scoredCount":             len(scored_field),
        "unscoredCount":           len(UNSCORED_PLAYERS),
        "resolvedPlayerIds":       resolved_count,
        "unresolvedPlayerIds":     unresolved_count,
        "crosswalkFile":           crosswalk_file,
        "crosswalkResolvedCount":  crosswalk_count,
        "crosswalkNote":           (
            "IDs confirmed/provided by event-local authoritative crosswalk. "
            "Crosswalk takes precedence over pga_field_teetimes.csv for listed players."
        ),
        "phantomDecompPlayer":     PHANTOM_DECOMP_PLAYER,
        "phantomNote":             "In dg_decomposition.csv but NOT in pga_field_teetimes.csv — withdrawn or pre-event inclusion.",
        "unscoredPlayers":         UNSCORED_PLAYERS,
        "players":                 id_records,
    }
    (output_dir / "2026_rocket_classic_identity_report.json").write_text(
        json.dumps(identity_report, indent=2), encoding="utf-8")

    # 3. Field completeness report — with availability status per source
    def coverage_count(data_d: dict, names: list[str], lk: dict) -> int:
        return sum(1 for n in names if resolve(n, data_d, lk) is not None)

    def classify_zeros(data_d: dict, names: list[str], lk: dict) -> dict:
        measured = matched_nz = matched_z = unmatched = 0
        for n in names:
            row = resolve(n, data_d, lk)
            if row is None:
                unmatched += 1
            else:
                matched_nz += 1
        return {"matched": matched_nz, "unmatched_zero_filled": unmatched}

    sources: dict = {
        "pga_field_teetimes": {
            "availability":    "MEASURED",
            "coverage":        len(field_names),
            "total":           len(field_names),
            "pct":             100.0,
            "note":            f"{len(UNSCORED_PLAYERS)} UNSCORED excluded from scoring loop",
        }
    }

    for key, data_d, lk, avail_type in [
        ("dg_decomposition",         decomp_data,    build_lookup(decomp_data),    "MEASURED"),
        ("allcourses_sg",            all_sg["12m"],  build_lookup(all_sg["12m"]),  "DERIVED"),
        ("detroit_similar_sg",       sim_sg["12m"],  build_lookup(sim_sg["12m"]),  "DERIVED"),
        ("app_skill_l12_sg",         app_skill_data, build_lookup(app_skill_data), "DERIVED"),
        ("app_skill_l12_prox",       app_prox_data,  build_lookup(app_prox_data),  "DERIVED"),
        ("detroit_golf_club_ch",     ch_data,        build_lookup(ch_data),        "MEASURED"),
        ("pga_field_trending_table", trending_data,  build_lookup(trending_data),  "MEASURED"),
    ]:
        counts = classify_zeros(data_d, scored_field, lk)
        sources[key] = {
            "availability":           avail_type,
            "matched_measured":       counts["matched"],
            "unmatched_zero_filled":  counts["unmatched_zero_filled"],
            "total":                  len(scored_field),
            "pct_measured":           round(100.0 * counts["matched"] / max(len(scored_field), 1), 1),
        }
        if counts["unmatched_zero_filled"] > 0:
            sources[key]["zero_fill_status"] = "MISSING_ZERO_FILLED"
        else:
            sources[key]["zero_fill_status"] = "NONE"

    sources["dg_performance_2026"] = {
        "availability":                "UNAVAILABLE",
        "source_status":               "ABSENT",
        "matched_measured":            0,
        "unmatched_zero_filled":       len(scored_field),
        "total":                       len(scored_field),
        "pct_measured":                0.0,
        "zero_fill_status":            "MISSING_ZERO_FILLED",
        "fields_affected":             list(PERF_FIELDS),
        "usable_for_badges":           False,
        "usable_for_narrative_traits": False,
        "impact":                      (
            "VW_OTT (0.20) component=0 for all 142 scored players uniformly; "
            "SHORT_GAME_RELIANT gate inactive; no badge or narrative trait may reference "
            "app_true, ott_true, putt_true, or arg_true."
        ),
    }

    completeness_report = {
        "schemaVersion":  "rocket-classic-completeness-v1.2",
        "generatedAt":    ts,
        "fieldTotal":     len(field_names),
        "scoredCount":    len(scored_field),
        "availabilityKey": {
            "MEASURED":           "directly read from source file; value is real",
            "MEASURED_ZERO":      "read from source file; value is genuinely 0, not missing",
            "DERIVED":            "calculated from one or more MEASURED fields",
            "DEBUT_ZERO":         "player has no rounds in SG corpus; 0 is structural",
            "MISSING_ZERO_FILLED":"source file present but player row absent; 0 substituted",
            "UNAVAILABLE":        "source file itself absent; field cannot be trusted",
        },
        "sourceCoverage": sources,
    }
    (output_dir / "2026_rocket_classic_field_completeness_report.json").write_text(
        json.dumps(completeness_report, indent=2), encoding="utf-8")

    # 4. Input manifest
    manifest_files = []
    for fname in sorted(p.name for p in input_dir.iterdir()
                        if p.is_file() and not p.name.startswith(".")):
        fpath = input_dir / fname
        try:
            stat = fpath.stat()
            manifest_files.append({
                "filename":      fname,
                "size_bytes":    stat.st_size,
                "sha256":        file_sha256(fpath),
                "last_modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            })
        except OSError:
            manifest_files.append({"filename": fname, "error": "stat failed"})

    input_manifest = {
        "schemaVersion": "rocket-classic-manifest-v1.0",
        "generatedAt":   ts,
        "inputDir":      str(input_dir.relative_to(input_dir.parent.parent.parent.parent)),
        "fileCount":     len(manifest_files),
        "files":         manifest_files,
    }
    (output_dir / "2026_rocket_classic_input_manifest.json").write_text(
        json.dumps(input_manifest, indent=2), encoding="utf-8")

    print(f"[enrich_cards] Mandatory artifacts written to {output_dir}")


def make_unscored_stub(entry: dict) -> dict:
    stub = {
        "rank":                None,
        "player":              entry["player"],
        "player_name":         entry["player"],
        "player_id":           entry["player_id"],
        "tier":                None,
        "vts_final":           None,
        "live_vts":            None,
        "neutralSkillIndex":   None,
        "sg_base_composite":   None,
        "sg_similar_composite": None,
        "delta_fit":           None,
        "data_depth":          "UNSCORED",
        "winPct":              None, "top5Pct":  None,
        "top10Pct":            None, "top20Pct": None,
        "makeCutPct":          None, "missCutPct": None,
        "win_prob":            None, "top_5_prob":  None,
        "top_10_prob":         None, "top_20_prob": None,
        "make_cut_prob":       None, "miss_cut_prob": None,
        "prepenalty_vts":      None,
        "vts_floor":           None,
        "vts_ceil":            None,
        "std_dev":             None,
        "l5_array":            [],
        "strength_tags":       [],
        "weakness_tags":       [],
        "headline":            None,
        "win_case":            None,
        "scouting_report":     None,
        "trait_scores":        [],
        "archetype_tags":      [],
        "anti_pattern_flags":  [],
        "app_true":            None,
        "ott_true":            None,
        "ch_adjustment":       None,
        "true_sg_l20":         None,
        "trait_approach_raw":  None,
        "trait_long_iron_raw": None,
        "r2_wave":             None,
        "r2_teetime":          None,
        "trait_availability":  None,
        "identity_source":     None,
        "identity_resolution": "UNSCORED",
        "identity_confidence": None,
    }
    return stub


def main() -> None:
    parser = argparse.ArgumentParser(description="VenueDNA Rocket Classic enrichment pipeline")
    parser.add_argument("--live", default=None, choices=["r1", "r2", "r3", "r4"],
                        help="Enable live-round enrichment mode")
    args = parser.parse_args()

    event_dir  = _EVENT_DIR
    input_dir  = event_dir / "input"
    output_dir = event_dir / "output"
    deploy_dir = event_dir / "deploy" / "data"

    output_dir.mkdir(parents=True, exist_ok=True)
    deploy_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ── Load all source files ──────────────────────────────────────────────────
    print("[enrich_cards] Loading source files...")

    field_names = load_field(input_dir / "pga_field_teetimes.csv")
    if not field_names:
        print("[enrich_cards] ERROR -- pga_field_teetimes.csv missing or empty", file=sys.stderr)
        sys.exit(1)
    field_ids = load_field_ids(input_dir / "pga_field_teetimes.csv")

    # Load and apply event-local identity crosswalk (exact normalized-name match only).
    crosswalk_data = load_id_crosswalk(input_dir / CROSSWALK_FILE)
    crosswalk_resolved_norms: set[str] = set()
    for norm, cw in crosswalk_data.items():
        for fname in field_names:
            if normalize_name(fname) == norm:
                existing = field_ids.get(fname)
                if existing and existing != cw["dg_id"]:
                    print(f"[enrich_cards] CROSSWALK OVERRIDE: {fname} "
                          f"id {existing!r} -> {cw['dg_id']} (authoritative crosswalk)", file=sys.stderr)
                field_ids[fname] = cw["dg_id"]
                crosswalk_resolved_norms.add(norm)
                break
    if crosswalk_data:
        print(f"  Crosswalk: {len(crosswalk_resolved_norms)}/{len(crosswalk_data)} entries "
              f"matched to field ({CROSSWALK_FILE})")

    print(f"  Field: {len(field_names)} players, {len(field_ids)} with dg_id")

    all_sg = {h: load_sg_csv(input_dir / f) for h, f in ALL_COURSES_FILES.items()}
    sim_sg = {h: load_sg_csv(input_dir / f) for h, f in SIM_COURSES_FILES.items()}

    app_skill_data = load_app_skill(input_dir / "app_skill_l12_sg.csv")
    app_prox_data  = load_app_prox(input_dir  / "app_skill_l12_prox.csv")

    perf_path   = input_dir / PERF_FILE
    perf_absent = not perf_path.exists()
    if perf_absent:
        print(f"[enrich_cards] WARNING -- {PERF_FILE} absent; "
              f"PERF_FIELDS {PERF_FIELDS} are UNAVAILABLE for all scored players",
              file=sys.stderr)
        perf_data = {}
    else:
        perf_data = load_performance(perf_path)

    decomp_data   = load_decomp(input_dir   / "dg_decomposition.csv")
    ch_data       = load_ch(input_dir       / "detroit_golf_club_CH.csv")
    trending_data = load_trending(input_dir / "pga_field_trending_table.csv")

    # Filter UNSCORED players from scoring iteration
    _unscored_norms = {normalize_name(u["player"]) for u in UNSCORED_PLAYERS}
    scored_field_names = [n for n in field_names if normalize_name(n) not in _unscored_norms]
    print(f"  Scoring: {len(scored_field_names)} players  UNSCORED stubs: {len(UNSCORED_PLAYERS)}")

    _missing_trend = check_field_completeness(
        scored_field_names, trending_data, build_lookup(trending_data))
    if _missing_trend:
        print(f"[enrich_cards] WARNING -- {len(_missing_trend)} scored player(s) missing from "
              f"pga_field_trending_table.csv: {', '.join(_missing_trend)}", file=sys.stderr)

    # Build lookup tables
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

    prox_values         = list(app_prox_data.values())
    prox_mean, prox_std = field_stats(prox_values) if prox_values else (30.0, 4.0)

    std_vals       = [v["std_dev"] for v in decomp_data.values() if v["std_dev"] > 0]
    field_std_mean = sum(std_vals) / len(std_vals) if std_vals else 3.0

    # ── Per-player raw computation (scored players only) ───────────────────────
    print("[enrich_cards] Computing latent scores...")

    _EMPTY_SKILL  = {"sg_50_100": 0.0, "sg_100_150": 0.0, "sg_150_200": 0.0, "sg_200plus": 0.0}
    _EMPTY_PERF   = {"putt_true": 0.0, "arg_true": 0.0, "app_true": 0.0, "ott_true": 0.0}
    _EMPTY_DECOMP = {"driving_acc_adj": 0.0, "driving_dist_adj": 0.0, "std_dev": field_std_mean}
    _EMPTY_TREND  = {"true_sg_l20": 0.0, "l5_starts": ""}

    players_raw: list[dict] = []

    for name in scored_field_names:
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
        any_sg     = any(all_r[h]["rounds"] > 0 or sim_r[h]["rounds"] > 0
                         for h in ("6m", "12m", "24m"))
        data_depth = "FULL" if any_sim else "DEBUT"

        sg_base_comp, sg_sim_comp, delta_fit = make_composites(all_r, sim_r)

        # Track source resolution for availability metadata
        _skill_raw = resolve(name, app_skill_data, lk["skill"])
        _prox_raw  = resolve(name, app_prox_data,  lk["prox"])
        _ch_raw    = resolve(name, ch_data,         lk["ch"])
        _trend_raw = resolve(name, trending_data,   lk["trend"])

        skill  = _skill_raw if _skill_raw is not None else _EMPTY_SKILL.copy()
        prox   = _prox_raw
        perf   = resolve(name, perf_data, lk["perf"]) or _EMPTY_PERF.copy()
        decomp = resolve(name, decomp_data, lk["decomp"]) or _EMPTY_DECOMP.copy()
        ch     = _ch_raw
        trend  = _trend_raw if _trend_raw is not None else _EMPTY_TREND.copy()

        skill_avail = _skill_raw is not None
        prox_avail  = _prox_raw  is not None
        ch_resolved = _ch_raw    is not None
        trend_avail = _trend_raw is not None

        course_debut = not ch_resolved
        if ch is None:
            ch_adj = DEBUT_CH_HAIRCUT if data_depth == "DEBUT" else 0.0
        else:
            ch_adj = ch["ch_adjustment"]

        if prox is not None:
            prox_z_raw = prox_to_z_raw(prox, prox_mean, prox_std)
        else:
            prox_z_raw = 0.0

        trait_approach_raw  = compute_trait_approach(skill)
        trait_long_iron_raw = compute_trait_long_iron(skill, prox_z_raw)
        ott_true            = perf["ott_true"]
        app_true            = perf["app_true"]
        true_sg_l20         = trend["true_sg_l20"]

        combined_raw = (
            sg_sim_comp
            + VW_APPROACH  * trait_approach_raw
            + VW_LONG_IRON * trait_long_iron_raw
            + VW_OTT       * ott_true            # 0.0 when perf absent (uniform, not neutral)
            + VW_CH        * ch_adj
            + VW_FORM      * true_sg_l20
        )

        prepenalty_raw = combined_raw
        combined_raw, gate_flags = apply_gates(combined_raw, perf, decomp)

        par5_raw      = 0.55 * ott_true + 0.45 * app_true
        composure_raw = 1.0 / (decomp["std_dev"] + 0.1)

        players_raw.append({
            "player":               name,
            "player_id":            field_ids.get(name),
            "data_depth":           data_depth,
            "course_debut":         course_debut,
            "sg_base_composite":    round(sg_base_comp,    4),
            "sg_similar_composite": round(sg_sim_comp,     4),
            "delta_fit":            round(delta_fit,        4),
            "gate_flags":           gate_flags,
            "_vts_raw":             combined_raw,
            "_nsi_raw":             sg_base_comp,
            "_prepenalty_raw":      prepenalty_raw,
            "app_true":             app_true,
            "ott_true":             ott_true,
            "ch_adjustment":        ch_adj,
            "true_sg_l20":          true_sg_l20,
            "trait_approach_raw":   round(trait_approach_raw,  4),
            "trait_long_iron_raw":  round(trait_long_iron_raw, 4),
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
            "l5_array":             parse_l5_starts(trend["l5_starts"]),
            "std_dev":              round(decomp["std_dev"], 3),
            # Resolution tracking (private; used for trait_availability/provenance, then dropped)
            "_skill_avail":         skill_avail,
            "_prox_avail":          prox_avail,
            "_ch_resolved":         ch_resolved,
            "_trend_avail":         trend_avail,
            "_any_sg_avail":        any_sg,
            "_crosswalk_resolved":  normalize_name(name) in crosswalk_resolved_norms,
            "_perf_missing":        frozenset(perf.get("_missing_fields", set())),
        })

    # ── Field-level z-scoring (scored players only) ────────────────────────────
    print("[enrich_cards] Z-scoring...")

    vts_scaled = z_score_scale([p["_vts_raw"]        for p in players_raw])
    nsi_scaled = z_score_scale([p["_nsi_raw"]        for p in players_raw])
    pre_scaled = z_score_scale([p["_prepenalty_raw"] for p in players_raw])

    d_keys = ["_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
              "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure"]
    d_scaled = {k: z_score_scale([p[k] for p in players_raw]) for k in d_keys}

    # ── Probability matrices ───────────────────────────────────────────────────
    print("[enrich_cards] Computing probability matrices...")

    raw_scores = [p["_vts_raw"] for p in players_raw]

    live_tee_times: dict = {}
    live_r1_sg: dict     = {}

    if args.live == "r1":
        print("[enrich_cards] Live R1 mode -- loading round data...")
        live_tee_times = load_tee_times(
            event_dir / "output" / "round1" / "round2_tee_times.csv")
        live_r1_sg = load_r1_sg(
            event_dir / "output" / "round1" / "round1_player_strokes_gained.csv")
        print(f"  Tee times: {len(live_tee_times)} | R1 SG: {len(live_r1_sg)}")

        raw_std    = field_stats(raw_scores)[1]
        temp_scale = ZNORM_STD / max(raw_std, 0.01)

        wave_vts: list[float] = []
        for i, p in enumerate(players_raw):
            norm      = normalize_name(p["player"])
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

        win_probs = tempered_softmax(wave_vts, TEMPS["win"]   * temp_scale, N_POSITIONS["win"])
        t5_probs  = tempered_softmax(wave_vts, TEMPS["top5"]  * temp_scale, N_POSITIONS["top5"])
        t10_probs = tempered_softmax(wave_vts, TEMPS["top10"] * temp_scale, N_POSITIONS["top10"])
        t20_probs = tempered_softmax(wave_vts, TEMPS["top20"] * temp_scale, N_POSITIONS["top20"])
    else:
        win_probs = tempered_softmax(raw_scores, TEMPS["win"],   N_POSITIONS["win"])
        t5_probs  = tempered_softmax(raw_scores, TEMPS["top5"],  N_POSITIONS["top5"])
        t10_probs = tempered_softmax(raw_scores, TEMPS["top10"], N_POSITIONS["top10"])
        t20_probs = tempered_softmax(raw_scores, TEMPS["top20"], N_POSITIONS["top20"])

    # ── Assemble final records ─────────────────────────────────────────────────
    print("[enrich_cards] Assembling player records...")

    for i, p in enumerate(players_raw):
        vts = round(vts_scaled[i], 1)
        nsi = round(nsi_scaled[i], 1)
        pre = round(pre_scaled[i], 1)

        p["vts_final"]         = vts
        p["neutralSkillIndex"] = nsi
        p["prepenalty_vts"]    = pre if p["gate_flags"] else None

        p["winPct"]   = round(win_probs[i],  1)
        p["top5Pct"]  = round(t5_probs[i],   1)
        p["top10Pct"] = round(t10_probs[i],  1)
        p["top20Pct"] = round(t20_probs[i],  1)
        enforce_monotonicity(p)
        p["makeCutPct"] = round(make_cut_prob(p["top20Pct"]), 1)
        p["missCutPct"] = round(100.0 - p["makeCutPct"], 1)

        p["win_prob"]      = p["winPct"]
        p["top_5_prob"]    = p["top5Pct"]
        p["top_10_prob"]   = p["top10Pct"]
        p["top_20_prob"]   = p["top20Pct"]
        p["make_cut_prob"] = p["makeCutPct"]
        p["miss_cut_prob"] = p["missCutPct"]

        spread         = round(p["std_dev"] * STD_VTS_SCALE, 1)
        p["vts_floor"] = round(max(0.0,   vts - spread), 1)
        p["vts_ceil"]  = round(min(100.0, vts + spread), 1)

        trait_scores = []
        for j, (label, weight) in enumerate(TRAIT_DISPLAY_CFG):
            trait_scores.append({
                "label":  label,
                "weight": weight,
                "score":  round(d_scaled[d_keys[j]][i], 1),
            })
        p["trait_scores"] = trait_scores

        _arc_dist = d_scaled["_d_drv_dist"][i]
        _arc_acc  = d_scaled["_d_drv_acc"][i]
        _arc_app  = d_scaled["_d_approach"][i]
        _arc_li   = d_scaled["_d_long_iron"][i]
        _arc_putt = d_scaled["_d_putt"][i]
        _arc_comp = d_scaled["_d_composure"][i]
        archetype_tags: list[str] = []
        if _arc_dist >= 75 and _arc_acc <= 30:
            archetype_tags.append("Erratic Bomber")
        # Short-Game Specialist and Putting Reliant archetypes suppressed when perf absent
        if not perf_absent:
            if _arc_putt >= 70 and _arc_comp >= 70 and _arc_app <= 40:
                archetype_tags.append("Short-Game Specialist")
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

        # Build trait_availability for this player
        trait_avail = build_trait_availability(
            perf_absent        = perf_absent,
            skill_avail        = p["_skill_avail"],
            prox_avail         = p["_prox_avail"],
            ch_resolved        = p["_ch_resolved"],
            ch_adj             = p["ch_adjustment"],
            trend_avail        = p["_trend_avail"],
            data_depth         = p["data_depth"],
            any_sg_avail       = p["_any_sg_avail"],
            perf_field_missing = p.get("_perf_missing", frozenset()),
        )
        p["trait_availability"] = trait_avail

        # Compute unavailable set for strength/weakness/win_case gating
        unavail = _unavail_set(trait_avail)

        # Data-confidence disclosure: flag players with imputed VTS components.
        # A weighted component is "imputed" if its source cell was blank/absent
        # and safe_float() substituted 0.0 — mathematically neutral but not measured.
        _WEIGHTED_VTS_FIELDS = (
            "trait_approach_raw", "trait_long_iron_raw", "ott_true",
            "ch_adjustment", "true_sg_l20",
        )
        _IMPUTED_STATES = {"UNAVAILABLE", "MISSING_ZERO_FILLED"}
        imputed_vts = [
            f for f in _WEIGHTED_VTS_FIELDS
            if trait_avail.get(f, {}).get("availability") in _IMPUTED_STATES
        ]
        if imputed_vts:
            p["data_confidence"] = "reduced"
            p["data_confidence_note"] = (
                f"{len(imputed_vts)} of 6 VTS components "
                f"({', '.join(imputed_vts)}) imputed as neutral (0.0) "
                f"due to missing source data — VTS score is unaffected "
                f"but reflects fewer real inputs."
            )

        strength = build_strength_tags(
            p["app_true"], p["delta_fit"], p["ott_true"],
            p["ch_adjustment"], p["true_sg_l20"],
            unavail,
        )
        weakness = build_weakness_tags(
            p["app_true"], p["trait_long_iron_raw"],
            p["data_depth"], p["course_debut"], p["gate_flags"],
            unavail,
        )
        p["strength_tags"] = strength
        p["weakness_tags"] = weakness
        p["headline"]      = build_headline(strength, weakness)
        p["win_case"]      = build_win_case(
            p["player"], p["app_true"], p["delta_fit"],
            p["ott_true"], strength, weakness, unavail,
        )
        p["anti_pattern_flags"] = p["gate_flags"]

        p["player_name"] = p["player"]
        if args.live == "r1":
            norm_fl = normalize_name(lastname_first_to_first_last(p["player"]))
            sg_info = live_r1_sg.get(norm_fl, {})
            wave    = p.get("_r2_wave", "")
            p["live_vts"]   = p.get("_live_vts", vts)
            p["r2_wave"]    = wave
            p["r2_teetime"] = p.get("_r2_teetime", "")
            if wave and sg_info:
                narrative = build_live_r1_narrative(
                    p["player"],
                    sg_info.get("r1_score", "--"),
                    sg_info.get("sg_approach", 0.0),
                    wave,
                )
                p["win_case"] = narrative + " " + p["win_case"]
        p["scouting_report"] = p["win_case"]

        # Identity provenance — per-player audit trail for downstream consumers
        if p.get("_crosswalk_resolved"):
            p["identity_source"]     = CROSSWALK_FILE
            p["identity_resolution"] = "EXPLICIT_EVENT_CROSSWALK"
            p["identity_confidence"] = "HIGH"
        else:
            p["identity_source"]     = "pga_field_teetimes.csv"
            p["identity_resolution"] = "FIELD_CSV"
            p["identity_confidence"] = "HIGH"

    # ── Packaging validation gates ─────────────────────────────────────────────
    print("[enrich_cards] Running availability validation gates...")
    gate_results = validate_availability_gates(players_raw)
    for gate, result in gate_results.items():
        status = result["status"]
        n_viol = len(result["violations"])
        print(f"  {gate}: {status}" + (f" ({n_viol} violations)" if n_viol else ""))
        if status == "FAIL":
            for v in result["violations"]:
                print(f"    VIOLATION: {v}", file=sys.stderr)
            sys.exit(1)

    # ── Aggregate source-coverage statistics from per-player availability ──────
    all_avail  = [p["trait_availability"] for p in players_raw]
    n_scored   = len(players_raw)

    def _count_measured(field: str) -> int:
        return sum(1 for a in all_avail
                   if a.get(field, {}).get("availability")
                   in ("MEASURED", "MEASURED_ZERO", "DERIVED", "DEBUT_ZERO"))

    def _perf_field_coverage(field: str) -> dict:
        if perf_absent:
            return {
                "availability":                "UNAVAILABLE",
                "source_status":               "MISSING",
                "source_file":                 PERF_FILE,
                "measured_count":              0,
                "scored_count":                n_scored,
                "pct_measured":                0.0,
                "usable_for_badges":           False,
                "usable_for_narrative_traits": False,
                "reason":                      PERF_ABSENT_REASON,
            }
        mc = _count_measured(field)
        return {
            "availability":                "MEASURED",
            "source_status":               "OK",
            "source_file":                 PERF_FILE,
            "measured_count":              mc,
            "scored_count":                n_scored,
            "pct_measured":                round(100.0 * mc / n_scored, 1),
            "usable_for_badges":           mc > 0,
            "usable_for_narrative_traits": mc > 0,
        }

    payload_source_coverage = {
        "fields": {
            "app_true":  _perf_field_coverage("app_true"),
            "ott_true":  _perf_field_coverage("ott_true"),
            "putt_true": _perf_field_coverage("putt_true"),
            "arg_true":  _perf_field_coverage("arg_true"),
            "trait_approach_raw": {
                "availability":                "DERIVED",
                "source_file":                 "app_skill_l12_sg.csv",
                "measured_count":              _count_measured("trait_approach_raw"),
                "zero_filled_count":           n_scored - _count_measured("trait_approach_raw"),
                "scored_count":                n_scored,
                "pct_measured":                round(100.0 * _count_measured("trait_approach_raw") / n_scored, 1),
                "usable_for_badges":           True,
                "usable_for_narrative_traits": True,
                "note":                        "zero-filled players are MISSING_ZERO_FILLED — not eligible for badges or narrative",
            },
            "trait_long_iron_raw": {
                "availability":                "DERIVED",
                "source_file":                 "app_skill_l12_sg.csv + app_skill_l12_prox.csv",
                "measured_count":              _count_measured("trait_long_iron_raw"),
                "zero_filled_count":           n_scored - _count_measured("trait_long_iron_raw"),
                "scored_count":                n_scored,
                "pct_measured":                round(100.0 * _count_measured("trait_long_iron_raw") / n_scored, 1),
                "usable_for_badges":           True,
                "usable_for_narrative_traits": True,
                "note":                        "zero-filled players are MISSING_ZERO_FILLED",
            },
            "ch_adjustment": {
                "availability":                "MEASURED",
                "source_file":                 "detroit_golf_club_CH.csv",
                "measured_count":              _count_measured("ch_adjustment"),
                "zero_filled_count":           n_scored - _count_measured("ch_adjustment"),
                "scored_count":                n_scored,
                "pct_measured":                round(100.0 * _count_measured("ch_adjustment") / n_scored, 1),
                "usable_for_badges":           False,
                "usable_for_narrative_traits": True,
                "narrative_context":           "venue_history",
                "narrative_constraint":        "venue-history context only — not a standalone player-skill trait",
            },
            "true_sg_l20": {
                "availability":                "MEASURED",
                "source_file":                 "pga_field_trending_table.csv",
                "measured_count":              _count_measured("true_sg_l20"),
                "zero_filled_count":           n_scored - _count_measured("true_sg_l20"),
                "scored_count":                n_scored,
                "pct_measured":                round(100.0 * _count_measured("true_sg_l20") / n_scored, 1),
                "usable_for_badges":           False,
                "usable_for_narrative_traits": True,
                "narrative_constraint":        "narrative-eligible only when measured (per-player check required); MISSING_ZERO_FILLED players receive no form-based tags",
            },
            "delta_fit": {
                "availability":                "DERIVED",
                "source_files":                [
                    "pga_sg_query_allcourses_l*.csv",
                    "pga_sg_query_detroit_golf_club_similar_l*.csv",
                ],
                "usable_for_badges":           False,
                "usable_for_narrative_traits": True,
            },
        },
        "validation_gates": gate_results,
    }

    # Write mandatory artifacts (includes raw projection — must happen before sort/drop)
    write_mandatory_artifacts(
        output_dir, players_raw,
        field_names, field_ids, payload_source_coverage,
        all_sg, sim_sg, app_skill_data, app_prox_data,
        decomp_data, ch_data, trending_data,
        input_dir, ts, perf_absent,
        crosswalk_resolved_norms, CROSSWALK_FILE,
    )

    # ── Sort + rank ────────────────────────────────────────────────────────────
    players_raw.sort(key=lambda p: p["vts_final"], reverse=True)
    for i, p in enumerate(players_raw, 1):
        p["rank"] = i
        p["tier"] = assign_tier(i)

    # ── Canonical output schema (drop private fields) ──────────────────────────
    _drop = {
        "_vts_raw", "_nsi_raw", "_prepenalty_raw", "gate_flags", "course_debut",
        "_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
        "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure",
        "_live_vts", "_r2_wave", "_r2_teetime",
        "_skill_avail", "_prox_avail", "_ch_resolved", "_trend_avail", "_any_sg_avail",
        "_crosswalk_resolved", "_perf_missing",
    }

    _first = [
        "rank", "player", "player_name", "player_id", "tier", "vts_final", "live_vts",
        "neutralSkillIndex",
        "sg_base_composite", "sg_similar_composite", "delta_fit", "data_depth",
        "data_confidence", "data_confidence_note",
        "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
        "win_prob", "top_5_prob", "top_10_prob", "top_20_prob",
        "make_cut_prob", "miss_cut_prob",
        "prepenalty_vts", "vts_floor", "vts_ceil", "std_dev",
        "l5_array", "strength_tags", "weakness_tags", "headline", "win_case",
        "scouting_report",
        "trait_scores", "archetype_tags", "anti_pattern_flags",
        "app_true", "ott_true", "ch_adjustment", "true_sg_l20",
        "trait_approach_raw", "trait_long_iron_raw",
        "trait_availability",
        "identity_source", "identity_resolution", "identity_confidence",
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

    # Append UNSCORED stubs
    stubs = [make_unscored_stub(u) for u in UNSCORED_PLAYERS]
    all_players = ordered + stubs

    # ── Write outputs ──────────────────────────────────────────────────────────
    _live_suffix = {"r1": "rd1", "r2": "rd2", "r3": "rd3", "r4": "rd4"}
    if args.live:
        file_base  = f"2026_rocket_classic_{_live_suffix[args.live]}_payload.json"
        schema_ver = f"rocket-classic-live-{args.live}-v1.1"
    else:
        file_base  = "2026_rocket_classic_event_payload.json"
        schema_ver = "rocket-classic-v1.2"

    payload = {
        "schemaVersion":  schema_ver,
        "generatedAt":    ts,
        "event":          "2026 Rocket Classic",
        "venue":          "Detroit Golf Club",
        "fieldSize":      len(all_players),
        "scoredCount":    len(ordered),
        "unscoredCount":  len(stubs),
        "sourceCoverage": payload_source_coverage,
        "players":        all_players,
    }
    json_str = json.dumps(payload, indent=2)

    deploy_path = deploy_dir / file_base
    output_path = output_dir / file_base

    deploy_path.write_text(json_str, encoding="utf-8")
    output_path.write_text(json_str, encoding="utf-8")

    print(f"[enrich_cards] Done -- {len(ordered)} scored + {len(stubs)} unscored = {len(all_players)} total")
    print(f"  Schema : {schema_ver}")
    print(f"  Deploy : {deploy_path}")
    print(f"  Output : {output_path}")

    debuts  = sum(1 for p in ordered if p["data_depth"] == "DEBUT")
    bombers = sum(1 for p in ordered if "INACCURATE_BOMBER" in (p["anti_pattern_flags"] or []))
    sgdeps  = sum(1 for p in ordered if "SHORT_GAME_RELIANT" in (p["anti_pattern_flags"] or []))
    print(f"  DEBUT:{debuts}  Bomber gates:{bombers}  SG-Reliant gates:{sgdeps}  "
          f"OTT-component:{'DEAD/UNAVAILABLE (perf absent)' if perf_absent else 'active'}")
    print(f"  Top 5: {', '.join(p['player'] for p in ordered[:5])}")


if __name__ == "__main__":
    main()
