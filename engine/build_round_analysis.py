"""
VenueDNA Generic Round Analysis Builder — engine/build_round_analysis.py
Schema version 1.1

Accepts an --event_slug argument and resolves all paths, trait configs, and
venue weights dynamically. Replaces event-specific copies with a single
authoritative module.

Usage:
    python engine/build_round_analysis.py --event_slug 2026_genesis_scottish_open --round 1
    python engine/build_round_analysis.py --event_slug 2026_genesis_scottish_open --round 2
    python engine/build_round_analysis.py --event_slug 2026_genesis_scottish_open --final
    python engine/build_round_analysis.py --event_slug 2026_genesis_scottish_open --round 1 --check

Round N input files (place in event output/roundN/ before running):
    roundN_leaderboard.csv              [REQUIRED]
    roundN_player_strokes_gained.csv    [REQUIRED]
    roundN_course_stats.csv             [optional]
    roundN_course_insights.csv          [optional]

Pre-tournament files (already present from pipeline build):
    deploy/data/event_payload.json      [REQUIRED]
    output/{slug}_trait_form_matrix.csv [REQUIRED]

Outputs:
    output/{slug}_rN_analysis.json
    deploy/data/rN_analysis.json
    output/{slug}_cumulative_learning.json
    deploy/data/cumulative_learning.json

New in schema 1.1:
    - trait_audit.app_150_200.brie_z  sub-driver breakdown (BRIE-Z metrics)
    - live_lean_notes.wave_risk_annotation  (players in disadvantaged wave split)
    - live_lean_notes.wave_scoring_averages  (avg score per wave)
    - Unique-narrative enforcement for per-player thesis notes
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="VenueDNA generic round analysis builder")
parser.add_argument("--event_slug", "--event", dest="event_slug", required=True, help="e.g. 2026_genesis_scottish_open")
grp = parser.add_mutually_exclusive_group(required=True)
grp.add_argument("--round", type=int, choices=[1, 2, 3, 4])
grp.add_argument("--final", action="store_true")
parser.add_argument("--check", action="store_true", help="Validate inputs only — no build")
parser.add_argument("--test-dry-run", dest="test_dry_run", action="store_true",
                    help="Inject mock CSV data and validate full pipeline — no live data required")
args = parser.parse_args()

DRY_RUN     = args.test_dry_run
EVENT_SLUG  = args.event_slug
FINAL_BUILD = args.final
ROUND       = 4 if FINAL_BUILD else args.round
IS_FINAL    = FINAL_BUILD or (ROUND == 4)
CHECK_ONLY  = args.check
TODAY       = date.today().isoformat()
BUILD_TS    = datetime.now().replace(microsecond=0).isoformat()

# ── Event configs ─────────────────────────────────────────────────────────────

_EVENT_CONFIGS: dict[str, dict] = {
    "2026_genesis_scottish_open": {
        "event_name":   "2026 Genesis Scottish Open",
        "course_name":  "The Renaissance Club",
        "par":          71,
        "event_dir_glob": "events/*GenesisScottish*",
        "course_key":   "renaissance_club",
        "favored_wave": "late_early",
        "trait_cols": {
            "app_150_200":     "trait_app_150_200",
            "ott_positional":  "trait_ott_positional",
            "app_overall":     "trait_app_overall",
            "driving_accuracy":"trait_driving_accuracy",
            "sg_putt":         "trait_sg_putt",
            "sg_arg":          "trait_sg_arg",
        },
        "venue_weights": {
            "app_150_200":      0.30,
            "ott_positional":   0.20,
            "app_overall":      0.15,
            "driving_accuracy": 0.12,
            "sg_putt":          0.13,
            "sg_arg":           0.10,
        },
        "sg_proxy": {
            "app_150_200":      "sg_app",
            "ott_positional":   "sg_ott",
            "app_overall":      "sg_app",
            "driving_accuracy": "sg_ott",
            "sg_putt":          "sg_putt",
            "sg_arg":           "sg_arg",
        },
        "ci_trait_map": {
            "app_150_200":      {"primary": "gir",         "direction": "higher_better", "secondary": "fairway_prox"},
            "ott_positional":   {"primary": "d_accuracy",  "direction": "higher_better", "secondary": None},
            "app_overall":      {"primary": "fairway_prox","direction": "lower_better",  "secondary": "gir"},
            "driving_accuracy": {"primary": "d_accuracy",  "direction": "higher_better", "secondary": None},
            "sg_putt":          {"primary": None,           "direction": None,            "secondary": None},
            "sg_arg":           {"primary": "scrambling",  "direction": "higher_better", "secondary": "rough_prox"},
        },
    },
    "2026_travelers_championship": {
        "event_name":   "2026 Travelers Championship",
        "course_name":  "TPC River Highlands",
        "par":          70,
        "event_dir_glob": "events/*Travelers*",
        "course_key":   "tpc_river_highlights",
        "favored_wave": "early_late",
        "trait_cols": {
            "app_wedge":       "trait_app_wedge",
            "app_100_150":     "trait_app_100_150",
            "app_150_200":     "trait_app_150_200",
            "ott_accuracy":    "trait_ott_accuracy",
            "ott_distance":    "trait_ott_distance",
            "putt_short_conv": "trait_putt_short_conv",
            "putt_lag":        "trait_putt_lag",
            "arg_rough":       "trait_arg_rough",
            "arg_bunker":      "trait_arg_bunker",
            "par5_scoring":    "trait_par5_scoring",
        },
        "venue_weights": {
            "app_wedge": 0.22, "app_100_150": 0.12, "app_150_200": 0.06,
            "ott_accuracy": 0.14, "ott_distance": 0.05, "putt_short_conv": 0.16,
            "putt_lag": 0.10, "arg_rough": 0.07, "arg_bunker": 0.05, "par5_scoring": 0.03,
        },
        "sg_proxy": {
            "app_wedge": "sg_app", "app_100_150": "sg_app", "app_150_200": "sg_app",
            "ott_accuracy": "sg_ott", "ott_distance": "sg_ott",
            "putt_short_conv": "sg_putt", "putt_lag": "sg_putt",
            "arg_rough": "sg_arg", "arg_bunker": "sg_arg", "par5_scoring": "sg_app",
        },
        "ci_trait_map": {
            "app_wedge":       {"primary": "fairway_prox",  "direction": "lower_better",  "secondary": "gir"},
            "app_100_150":     {"primary": "fairway_prox",  "direction": "lower_better",  "secondary": "gir"},
            "app_150_200":     {"primary": "gir",           "direction": "higher_better", "secondary": "fairway_prox"},
            "ott_accuracy":    {"primary": "d_accuracy",    "direction": "higher_better", "secondary": None},
            "ott_distance":    {"primary": "d_distance",    "direction": "higher_better", "secondary": None},
            "putt_short_conv": {"primary": None,            "direction": None,            "secondary": None},
            "putt_lag":        {"primary": None,            "direction": None,            "secondary": None},
            "arg_rough":       {"primary": "scrambling",    "direction": "higher_better", "secondary": "rough_prox"},
            "arg_bunker":      {"primary": "scrambling",    "direction": "higher_better", "secondary": None},
            "par5_scoring":    {"primary": "gir",           "direction": "higher_better", "secondary": "d_distance"},
        },
    },
    # ── 2026 The Open Championship — Royal Birkdale ───────────────────────────
    # Weights derived from links-optimized GSO baseline with Birkdale adjustments:
    #   ott_accuracy  +4% (vs GSO driving_accuracy 0.12): gorse/rough demands peak
    #   ott_positional −2% (vs GSO 0.20): positional play yields to accuracy priority
    #   app_overall  −2% (vs GSO 0.15): absorbs net balance shift
    "2026_the_open_championship": {
        "event_name":   "2026 The Open Championship",
        "course_name":  "Royal Birkdale",
        "par":          70,
        "event_dir_glob": "events/*the_open*",
        "event_root":   "C:/PGA_VenueDNA/events/2026_the_open_championship",
        "course_key":   "royal_birkdale",
        "favored_wave": "late_early",
        "trait_cols": {
            "app_150_200":   "trait_app_150_200",
            "ott_accuracy":  "trait_driving_accuracy",
            "ott_positional":"trait_ott_positional",
            "app_overall":   "trait_app_overall",
            "sg_putt":       "trait_sg_putt",
            "sg_arg":        "trait_sg_arg",
        },
        "venue_weights": {
            "app_150_200":   0.30,
            "ott_accuracy":  0.16,
            "ott_positional":0.18,
            "app_overall":   0.13,
            "sg_putt":       0.13,
            "sg_arg":        0.10,
        },
        "sg_proxy": {
            "app_150_200":   "sg_app",
            "ott_accuracy":  "sg_ott",
            "ott_positional":"sg_ott",
            "app_overall":   "sg_app",
            "sg_putt":       "sg_putt",
            "sg_arg":        "sg_arg",
        },
        "ci_trait_map": {
            "app_150_200":   {"primary": "gir",        "direction": "higher_better", "secondary": "fairway_prox"},
            "ott_accuracy":  {"primary": "d_accuracy", "direction": "higher_better", "secondary": None},
            "ott_positional":{"primary": "d_accuracy", "direction": "higher_better", "secondary": None},
            "app_overall":   {"primary": "fairway_prox","direction": "lower_better", "secondary": "gir"},
            "sg_putt":       {"primary": None,         "direction": None,            "secondary": None},
            "sg_arg":        {"primary": "scrambling", "direction": "higher_better", "secondary": "rough_prox"},
        },
        # Weekend firm/fast override: 0.08 VTS haircut for high-apex/high-spin profiles
        # Active from R2 — dry conditions confirmed through opening 36 holes.
        # Targets R3-flagged (OTT-Only Links) players whose trajectory volatility is
        # stressed by the sustained NW wind on fast Birkdale surfaces.
        "weekend_high_spin_penalty": {
            "active_from_round": 2,
            "penalty_vts":       0.08,
            "flag":              "high_apex_high_spin",
            "players": [
                "Scottie Scheffler", "Jon Rahm", "Rory McIlroy", "Kurt Kitayama",
                "Ryan Gerard", "Kristoffer Reitan", "Alex Smalley", "Tyrrell Hatton",
                "Angel Ayora", "Justin Thomas", "Sepp Straka", "Daniel Hillier",
                "Pierceson Coody", "Sam Stevens", "Rasmus Neergaard-Petersen",
                "Rasmus Hojgaard", "Hennie Du Plessis", "Marco Penge", "Max Greyserman",
                "Haotong Li", "Casey Jarvis", "Jesper Svensson", "Andy Sullivan",
            ],
        },
    },
}

cfg = _EVENT_CONFIGS.get(EVENT_SLUG)
if cfg is None:
    print(f"ERROR: Unknown event_slug '{EVENT_SLUG}'.")
    print(f"  Known slugs: {sorted(_EVENT_CONFIGS.keys())}")
    raise SystemExit(1)

EVENT_NAME  = cfg["event_name"]
COURSE_NAME = cfg["course_name"]
PAR         = cfg["par"]
TRAIT_COLS  = cfg["trait_cols"]
VENUE_WEIGHTS = cfg["venue_weights"]
SG_PROXY    = cfg["sg_proxy"]
CI_TRAIT_MAP = cfg["ci_trait_map"]
COURSE_KEY  = cfg.get("course_key", "")
FAVORED_WAVE = cfg.get("favored_wave", "late_early")

_CANONICAL_TRAITS = [
    "app_wedge", "app_100_150", "app_150_200", "ott_accuracy", "ott_distance",
    "putt_short_conv", "putt_lag", "arg_rough", "arg_bunker", "par5_scoring",
]

# Locate event directory
event_glob = cfg.get("event_dir_glob", f"events/*{EVENT_SLUG}*")
_event_candidates = sorted(_ROOT.glob(event_glob))
if not _event_candidates:
    print(f"ERROR: Cannot find event directory for '{EVENT_SLUG}'. Searched: {_ROOT / event_glob}")
    raise SystemExit(1)
EVENT_DIR  = _event_candidates[0]
_root_cfg  = cfg.get("event_root")
EVENT_ROOT = Path(_root_cfg) if _root_cfg else EVENT_DIR
OUT        = EVENT_DIR / "output"
DEP        = EVENT_DIR / "deploy" / "data"
INPUT_DIR  = EVENT_ROOT / "output" / f"round{ROUND}"
OUTPUT_DIR = EVENT_ROOT / "deploy" / "data"

# ── Enrichment thresholds (conservative universal defaults) ───────────────────
TRAIT_SIGNAL_THRESHOLDS = {"strong": 6, "lean": 2, "neutral": -3}
CI_SIG = {"fairway_prox": 20, "rough_prox": 50, "gir": 3.0, "d_accuracy": 3.0,
           "scrambling": 10.0, "d_distance": 3.0}
CI_STR = {"fairway_prox": 36, "rough_prox": 100, "gir": 5.0, "d_accuracy": 5.0,
           "scrambling": 15.0, "d_distance": 6.0}
DIRECT_ENRICHMENT = {"ott_accuracy": "d_accuracy", "arg_rough": "scrambling",
                     "arg_bunker": "scrambling", "ott_positional": "d_accuracy"}
UPGRADE_MAP = {"weak": "neutral", "not_testable": "neutral",
               "neutral": "mixed",  "mixed": "validated"}

# ── Path resolution ───────────────────────────────────────────────────────────
if FINAL_BUILD:
    for candidate in [OUT / "final_tournament", OUT / "round4 player & course stats"]:
        if candidate.exists():
            ROUND_DIR = candidate
            break
    else:
        print("ERROR: Final tournament data directory not found.")
        raise SystemExit(1)
    LB_PATH = ROUND_DIR / "final_leaderboard.csv"
    SG_PATH = ROUND_DIR / "final_tournament_player_strokes_gained.csv"
    CS_PATH = ROUND_DIR / "final_tournament_course_stats.csv"
    CI_PATH = ROUND_DIR / "final_tournament_course_insights.csv"
else:
    for candidate in [OUT / f"round{ROUND}", OUT / f"round{ROUND} player & course stats"]:
        if candidate.exists():
            ROUND_DIR = candidate
            break
    else:
        if DRY_RUN:
            ROUND_DIR = INPUT_DIR
        else:
            print(f"ERROR: Round {ROUND} data directory not found.")
            print(f"  Create {OUT / f'round{ROUND}'} and place round{ROUND}_*.csv files inside.")
            raise SystemExit(1)
    LB_PATH = ROUND_DIR / f"round{ROUND}_leaderboard.csv"
    SG_PATH = ROUND_DIR / f"round{ROUND}_player_strokes_gained.csv"
    CS_PATH = ROUND_DIR / f"round{ROUND}_course_stats.csv"
    CI_PATH = ROUND_DIR / f"round{ROUND}_course_insights.csv"

TFM_PATH = OUT / f"{EVENT_SLUG}_trait_form_matrix.csv"
PAY_PATH = DEP / "event_payload.json"
PAIRINGS  = EVENT_DIR / "input" / "r1_pairings.csv"

# ── Helper functions ──────────────────────────────────────────────────────────

def load_csv(p: Path) -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, newline="", encoding=enc) as f:
                rows = list(csv.DictReader(f))
            if rows:
                return rows
        except (UnicodeDecodeError, Exception):
            continue
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def csv_columns(p: Path) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, newline="", encoding=enc) as f:
                return next(csv.reader(f), [])
        except Exception:
            continue
    return []


def ascii_fold(s: str) -> str:
    folded = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return folded.replace('.', '')


_COMBINING_RE = re.compile("[\u0300-\u036f]")

def norm_name(s: str) -> str:
    """Mirror JS normName: NFD decompose, strip U+0300-U+036F combining marks, lowercase, trim."""
    stripped   = _COMBINING_RE.sub("", unicodedata.normalize("NFD", str(s)))
    no_periods = stripped.replace(".", "")
    return re.sub("[‘’`’]", "'", no_periods).lower().strip()


_SUFFIX_RE = re.compile(r'\b(jr\.?|sr\.?|ii|iii|iv)\s*$', re.IGNORECASE)

def _deep_norm(s: str) -> str:
    """Robust lookup key: norm_name + collapse commas + strip trailing name suffixes.
    Handles ‘Last, First’ board-export format and Jr./Sr. designations."""
    n = norm_name(s).replace(',', ' ')
    n = _SUFFIX_RE.sub('', n).strip()
    return re.sub(r'\s+', ' ', n)


def fl_to_lf(name: str) -> str:
    parts = name.strip().split()
    return parts[-1] + ", " + " ".join(parts[:-1]) if len(parts) >= 2 else name


def avg(lst: list) -> float | None:
    vals = [x for x in lst if x is not None]
    return round(mean(vals), 3) if vals else None


def parse_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_prox(s: Any) -> int | None:
    s = (str(s).strip()
         .replace("'", "'").replace("‘", "'")
         .replace("”", '"').replace("“", '"'))
    m = re.match(r"(\d+)'\s*(\d+)\"", s)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m2 = re.match(r"(\d+)'", s)
    return int(m2.group(1)) * 12 if m2 else None


def parse_pct(s: Any) -> float | None:
    try:
        return float(str(s).rstrip("%").strip())
    except (TypeError, ValueError):
        return None


def parse_pos(pos_str: str) -> int:
    s = str(pos_str).strip().lstrip("T")
    return int(s) if s.isdigit() else 72


def classify_wave(tee_time_str: str, am_cutoff: int = 12) -> str:
    if not tee_time_str:
        return "unknown"
    raw = str(tee_time_str).strip().upper()
    if raw in ("TBD", "N/A", ""):
        return "unknown"
    is_pm = "PM" in raw
    is_am = "AM" in raw
    cleaned = raw.replace("AM", "").replace("PM", "").strip()
    parts = cleaned.replace(":", " ").split()
    try:
        hour = int(parts[0])
    except (IndexError, ValueError):
        return "unknown"
    if is_pm and hour != 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0
    return "early_late" if hour < am_cutoff else "late_early"


# ── Dry-run mock environment ──────────────────────────────────────────────────
_DRY_RUN_CREATED: list[Path] = []
if DRY_RUN:
    print(f"[dry-run] Injecting mock environment — {EVENT_NAME} Round {ROUND}")
    ROUND_DIR.mkdir(parents=True, exist_ok=True)

    _MOCK_PLAYERS = [
        ("Rory McIlroy",       "1",   "-7"), ("Jon Rahm",           "2",   "-6"),
        ("Scottie Scheffler",  "T3",  "-5"), ("Viktor Hovland",     "T3",  "-5"),
        ("Collin Morikawa",    "5",   "-4"), ("Tommy Fleetwood",    "6",   "-3"),
        ("Tyrrell Hatton",     "T7",  "-3"), ("Shane Lowry",        "T7",  "-3"),
        ("Matt Fitzpatrick",   "T9",  "-2"), ("Justin Thomas",      "T9",  "-2"),
        ("Xander Schauffele",  "T11", "-1"), ("Patrick Cantlay",    "T11", "-1"),
        ("Max Homa",           "T11", "-1"), ("Robert MacIntyre",   "T14", "E"),
        ("Adam Scott",         "T14", "E"),  ("Francesco Molinari", "T16", "+1"),
        ("Cameron Smith",      "T16", "+1"), ("Jordan Spieth",      "T16", "+1"),
        ("Jason Day",          "T19", "+2"), ("Hideki Matsuyama",   "T19", "+2"),
        ("Brian Harman",       "T21", "+3"), ("Luke Donald",        "T21", "+3"),
        ("Alex Noren",         "T23", "+4"), ("Thorbjorn Olesen",   "T23", "+4"),
        ("Louis Debut",        "25",  "+5"),
    ]

    if not LB_PATH.exists():
        with open(LB_PATH, "w", newline="", encoding="utf-8") as _f:
            _cw = csv.writer(_f)
            _cw.writerow(["PLAYER", "POS", "TOTAL"])
            _cw.writerows(_MOCK_PLAYERS)
        _DRY_RUN_CREATED.append(LB_PATH)
        print(f"[dry-run] Wrote {LB_PATH.name} ({len(_MOCK_PLAYERS)} players)")

    if not SG_PATH.exists():
        with open(SG_PATH, "w", newline="", encoding="utf-8") as _f:
            _cw = csv.writer(_f)
            _cw.writerow(["Player", "SG-Off the Tee", "SG-Approach to Green",
                          "SG- Around the Green", "SG-Putting", "SG-Total"])
            for _i, _mp in enumerate(_MOCK_PLAYERS):
                _cw.writerow([
                    _mp[0],
                    round(0.80 - _i * 0.060, 2), round(1.20 - _i * 0.090, 2),
                    round(0.30 - _i * 0.030, 2), round(0.50 - _i * 0.040, 2),
                    round(2.80 - _i * 0.220, 2),
                ])
        _DRY_RUN_CREATED.append(SG_PATH)
        print(f"[dry-run] Wrote {SG_PATH.name}")

    if not PAIRINGS.exists():
        PAIRINGS.parent.mkdir(parents=True, exist_ok=True)
        with open(PAIRINGS, "w", newline="", encoding="utf-8") as _f:
            _cw = csv.writer(_f)
            _cw.writerow(["player_name", "wave"])
            for _i, _mp in enumerate(_MOCK_PLAYERS):
                _cw.writerow([_mp[0], "early_late" if _i % 2 == 0 else "late_early"])
        _DRY_RUN_CREATED.append(PAIRINGS)
        print(f"[dry-run] Wrote r1_pairings.csv (AM/PM alternating across {len(_MOCK_PLAYERS)} players)")

    if not PAY_PATH.exists():
        _mock_tiers: dict = {f"tier_{_t}": [] for _t in range(1, 6)}
        for _i, _mp in enumerate(_MOCK_PLAYERS[:-1]):
            _lf = fl_to_lf(ascii_fold(_mp[0]))
            _mock_tiers[f"tier_{min(5, _i // 5 + 1)}"].append({
                "player_name": _lf, "rank": _i + 1, "tier": _i // 5 + 1,
                "vts_final":   round(80.0 - _i * 2.5, 1),
                "win_pct":     round(max(0.1, 15.0 - _i * 0.6), 2),
                "top10_pct":   round(max(1.0, 45.0 - _i * 1.5), 1),
                "top20_pct":   round(max(5.0, 65.0 - _i * 1.0), 1),
                "primary_driver": "app_150_200",
            })
        PAY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PAY_PATH, "w", encoding="utf-8") as _pf:
            json.dump({"tiers": _mock_tiers, "players": []}, _pf, indent=2)
        _DRY_RUN_CREATED.append(PAY_PATH)
        print(f"[dry-run] Wrote event_payload.json (24 modelled + 1 debut alt)")

    if not TFM_PATH.exists():
        _trait_headers = ["name_key", "player_display"] + list(TRAIT_COLS.values())
        TFM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TFM_PATH, "w", newline="", encoding="utf-8") as _f:
            _cw = csv.writer(_f)
            _cw.writerow(_trait_headers)
            for _i, _mp in enumerate(_MOCK_PLAYERS[:-1]):
                _lf = fl_to_lf(ascii_fold(_mp[0]))
                _nk = _lf.lower()
                _scores = [round(max(20.0, 80.0 - _i * 2.0 + _j * 3.0), 1)
                           for _j in range(len(TRAIT_COLS))]
                _cw.writerow([_nk, _lf] + _scores)
        _DRY_RUN_CREATED.append(TFM_PATH)
        print(f"[dry-run] Wrote trait form matrix ({len(_MOCK_PLAYERS) - 1} player rows)")

# ── File validation ───────────────────────────────────────────────────────────
MISSING_REQUIRED = False
for path, label in [
    (LB_PATH,  f"round{ROUND}_leaderboard.csv"),
    (SG_PATH,  f"round{ROUND}_player_strokes_gained.csv"),
    (TFM_PATH, f"{EVENT_SLUG}_trait_form_matrix.csv"),
    (PAY_PATH, "event_payload.json"),
]:
    if not path.exists():
        print(f"ERROR: Required file missing — {label}")
        print(f"  Expected: {path}")
        MISSING_REQUIRED = True

if MISSING_REQUIRED:
    raise SystemExit(1)

cs_loaded = CS_PATH.exists()
ci_loaded = CI_PATH.exists()
if not cs_loaded:
    print(f"[info] round{ROUND}_course_stats.csv not found — hole analysis skipped")
if not ci_loaded:
    print(f"[info] round{ROUND}_course_insights.csv not found — enrichment skipped")

if CHECK_ONLY:
    print(f"\n=== CHECK MODE — {EVENT_NAME} Round {ROUND} ===")
    print(f"Event dir : {EVENT_DIR}")
    print(f"Round dir : {ROUND_DIR}")
    print(f"Build ts  : {BUILD_TS}")

    def _check_file(p, label, required):
        if not p.exists():
            print(f"  [{'MISS' if required else ' -- '}] {label}")
            return False
        rows = load_csv(p)
        print(f"  [ OK]  {label}  ({len(rows)} rows)")
        return True

    _check_file(LB_PATH,  f"round{ROUND}_leaderboard.csv",           True)
    _check_file(SG_PATH,  f"round{ROUND}_player_strokes_gained.csv", True)
    _check_file(TFM_PATH, f"{EVENT_SLUG}_trait_form_matrix.csv",     True)
    _check_file(PAY_PATH, "event_payload.json",                       True)
    _check_file(CS_PATH,  f"round{ROUND}_course_stats.csv",          False)
    _check_file(CI_PATH,  f"round{ROUND}_course_insights.csv",       False)
    print("\nPASS — all required files present." if not MISSING_REQUIRED else "\nFAIL — fix issues above.")
    raise SystemExit(0)

# ── Load files ────────────────────────────────────────────────────────────────
lb      = load_csv(LB_PATH)
sg      = load_csv(SG_PATH)
tfm     = load_csv(TFM_PATH)
cs      = load_csv(CS_PATH) if cs_loaded else []
ci_rows = load_csv(CI_PATH) if ci_loaded else []
with open(PAY_PATH, encoding="utf-8") as f:
    payload = json.load(f)

# Board-export rank override — post-audit VTS ranks supersede event_payload ranks
_board_rank: dict[str, int] = {}
for _be_name in ("board_export.json", f"{EVENT_SLUG}_board_export.json",
                 "open_2026_board_export.json"):
    _be_path = DEP / _be_name
    if _be_path.exists():
        try:
            with open(_be_path, encoding="utf-8") as _bef:
                _be_doc = json.load(_bef)
            for _bep in _be_doc.get("players", []):
                _bek  = ascii_fold(_bep.get("player", "")).lower()
                _bek2 = _deep_norm(_bep.get("player", ""))
                if isinstance(_bep.get("rank"), int):
                    if _bek:
                        _board_rank[_bek] = _bep["rank"]
                    if _bek2 and _bek2 != _bek:
                        _board_rank[_bek2] = _bep["rank"]
            if _board_rank:
                print(f"[info] Board rank override loaded: {len(_board_rank)} players from {_be_name}")
                break
        except Exception as _bee:
            print(f"[warn] Board export rank load failed ({_be_name}): {_bee}")

# ── Leaderboard header normalisation — handles lowercase, "Player Name", etc. ─
if lb:
    _lb_col = set(lb[0].keys())
    _LB_PLAYER = ("PLAYER", "Player", "player", "Player Name", "player_name", "NAME", "Name")
    _lbc = next((a for a in _LB_PLAYER if a in _lb_col), None)
    if _lbc and _lbc != "PLAYER":
        for r in lb:
            r["PLAYER"] = r.pop(_lbc, "")
        _lb_col = set(lb[0].keys())
    _LB_POS = ("POS", "Pos", "pos", "POSITION", "Position", "position")
    _lbp = next((a for a in _LB_POS if a in _lb_col), None)
    if _lbp and _lbp != "POS":
        for r in lb:
            r["POS"] = r.pop(_lbp, "")
        _lb_col = set(lb[0].keys())
    _LB_SCORE = ("TOTAL", "Total", "total", "SCORE", "Score", "score", f"R{ROUND}", f"r{ROUND}")
    _lbs = next((a for a in _LB_SCORE if a in _lb_col), None)
    if _lbs and _lbs not in ("TOTAL",):
        for r in lb:
            r["TOTAL"] = r.pop(_lbs, "")

# ── Weather forecast — wind/wave latent penalty matrix ────────────────────────
_WEATHER_PATH = DEP / "weather_forecast.json"
_WX = {"speed": 0, "direction": "N/A", "wave_delta": 0.0, "tide": "N/A",
       "disadvantaged_wave": "Neutral", "favored_wave": "Neutral"}
try:
    # Guard 1 — file existence
    if not _WEATHER_PATH.exists():
        raise FileNotFoundError("weather_forecast.json not found — safe defaults applied")
    # Guard 2 — file read and JSON parse
    try:
        with open(_WEATHER_PATH, encoding="utf-8") as _wf:
            _wx_raw = json.load(_wf)
    except (json.JSONDecodeError, OSError, ValueError) as _parse_err:
        raise ValueError(f"weather_forecast.json unreadable: {_parse_err}") from _parse_err
    # Guard 3 — key extraction with type coercion and empty-payload check
    if not isinstance(_wx_raw, dict) or not _wx_raw:
        raise ValueError("weather_forecast.json payload is empty or not a JSON object")
    _WX["speed"]              = float(_wx_raw.get("speed") or 0)
    _WX["direction"]          = str(_wx_raw.get("direction") or "N/A")
    _WX["wave_delta"]         = float(_wx_raw.get("wave_delta") or 0.0)
    _WX["tide"]               = str(_wx_raw.get("tide") or "N/A")
    _disadv                   = _wx_raw.get("disadvantaged_wave")
    _WX["disadvantaged_wave"] = str(_disadv) if _disadv else "Neutral"
except Exception as _wxe:
    print(f"[warn] Weather loading failed: {_wxe} — safe defaults applied (speed=0, wave_delta=0.0, wave=Neutral)")
    _WX["speed"]              = 0
    _WX["wave_delta"]         = 0.0
    _WX["disadvantaged_wave"] = "Neutral"
    _WX["favored_wave"]       = "Neutral"

WX_SPEED       = _WX["speed"]
WX_DELTA       = _WX["wave_delta"]
_opp_wave      = "early_late" if FAVORED_WAVE == "late_early" else "late_early"
WX_DISADV_WAVE = _WX["disadvantaged_wave"] or (_opp_wave if WX_SPEED > 15 else None)
WIND_SEVERITY  = min(1.0, WX_SPEED / 20.0) if WX_SPEED > 15 else 0.0
WAVE_PENALTY   = round(WX_DELTA * WIND_SEVERITY, 4)
print(f"Weather: {WX_SPEED:.1f} kts | wave_delta={WX_DELTA} | disadv_wave={WX_DISADV_WAVE or 'none'} | latent_penalty={WAVE_PENALTY}")
if DRY_RUN:
    WX_SPEED       = 22.0
    WX_DELTA       = 0.45
    WX_DISADV_WAVE = "late_early"
    WIND_SEVERITY  = min(1.0, WX_SPEED / 20.0)
    WAVE_PENALTY   = round(WX_DELTA * WIND_SEVERITY, 4)
    print(f"[dry-run] Weather overridden: {WX_SPEED} kts | wave_delta={WX_DELTA} | disadv_wave={WX_DISADV_WAVE} (PM) | penalty={WAVE_PENALTY}")

print(f"Loaded: {len(lb)} leaderboard / {len(sg)} SG / {len(tfm)} trait rows")

# Normalise SG columns
SG_ARG_COL = None
if sg:
    sg_col_set = set(sg[0].keys())
    if FINAL_BUILD and "SG-OTT" in sg_col_set:
        sg = [
            {"Player": f"{r.get('First Name','')} {r.get('Last Name','')}".strip(),
             "SG-Off the Tee": r.get("SG-OTT"), "SG-Approach to Green": r.get("SG-APP"),
             "SG- Around the Green": r.get("SG-ARG"), "SG-Putting": r.get("SG-Putt"),
             "SG-Total": r.get("SG-Total")}
            for r in sg
        ]
        sg_col_set = set(sg[0].keys())
    if "Player" not in sg_col_set and "PLAYER" in sg_col_set:
        for r in sg:
            r["Player"] = r.pop("PLAYER")
        sg_col_set = set(sg[0].keys())
    # Normalize lowercase DK/DataGolf export format
    if "sg-total" in sg_col_set:
        _LC_MAP = {
            "sg-ott":          "SG-Off the Tee",
            "sg-app to green": "SG-Approach to Green",
            "sg-around green": "SG- Around the Green",
            "sg-putting":      "SG-Putting",
            "sg-total":        "SG-Total",
        }
        for r in sg:
            for src, dst in _LC_MAP.items():
                if src in r:
                    r[dst] = r.pop(src)
        sg_col_set = set(sg[0].keys())
    # Colon-separated format: SG:OTT / SG:APP / SG:ARG / SG:PUTT (R&A / DP World Tour)
    _COLON_MAP = {
        "SG:OTT":  "SG-Off the Tee",      "sg:ott":   "SG-Off the Tee",
        "SG:APP":  "SG-Approach to Green", "sg:app":   "SG-Approach to Green",
        "SG:ARG":  "SG- Around the Green", "sg:arg":   "SG- Around the Green",
        "SG:PUTT": "SG-Putting",           "sg:putt":  "SG-Putting",
        "SG:Total":"SG-Total",             "sg:total": "SG-Total",
    }
    if any(k in sg_col_set for k in _COLON_MAP):
        for r in sg:
            for src, dst in list(_COLON_MAP.items()):
                if src in r:
                    r[dst] = r.pop(src)
        sg_col_set = set(sg[0].keys())
    # Long-form column names (Strokes Gained Approach, Strokes Gained Off the Tee, etc.)
    _LONG_MAP = {
        "Strokes Gained Off the Tee":       "SG-Off the Tee",
        "Strokes Gained Approach":          "SG-Approach to Green",
        "Strokes Gained Approach to Green": "SG-Approach to Green",
        "Strokes Gained Around the Green":  "SG- Around the Green",
        "Strokes Gained Putting":           "SG-Putting",
        "Strokes Gained Total":             "SG-Total",
    }
    if any(k in sg_col_set for k in _LONG_MAP):
        for r in sg:
            for src, dst in list(_LONG_MAP.items()):
                if src in r:
                    r[dst] = r.pop(src)
        sg_col_set = set(sg[0].keys())
    # SG player name column aliases ("Player Name", "player", "Name")
    if "Player" not in sg_col_set:
        _SG_NAME = ("PLAYER", "player", "Player Name", "player_name", "Name", "name")
        _sgn = next((a for a in _SG_NAME if a in sg_col_set), None)
        if _sgn:
            for r in sg:
                r["Player"] = r.pop(_sgn)
            sg_col_set = set(sg[0].keys())
    SG_ARG_COL = (
        "SG- Around the Green" if "SG- Around the Green" in sg_col_set
        else "SG-Around the Green" if "SG-Around the Green" in sg_col_set
        else None
    )

# ── Pre-tournament model lookup ───────────────────────────────────────────────
pretournament: dict[str, dict] = {}
for tier in range(1, 6):
    for p in payload.get("tiers", {}).get(f"tier_{tier}", []):
        pretournament[ascii_fold(p.get("player_name", "")).lower()] = p
# Also handle flat players array
for p in payload.get("players", []):
    last, first = p.get("last_name",""), p.get("first_name","")
    pname = f"{last} {first}".strip() or p.get("player_name","")
    pretournament[ascii_fold(pname).lower()] = p
    # Also key "Last, First" to match fl_to_lf(leaderboard_name) lookups
    if last and first:
        pretournament[ascii_fold(f"{last}, {first}").lower()] = p

# Trait form matrix
trait_by_nk: dict[str, dict] = {}
name_to_nk:  dict[str, str]  = {}
for row in tfm:
    nk = row.get("name_key", "")
    traits = {}
    for tk, col in TRAIT_COLS.items():
        try:
            v = float(row.get(col, 0))
            traits[tk] = round(v, 1) if v > 0 else None
        except (TypeError, ValueError):
            traits[tk] = None
    trait_by_nk[nk] = traits
    if "player_display" in row:
        name_to_nk[ascii_fold(row["player_display"]).lower()] = nk

def lookup_traits(name_lf: str) -> dict | None:
    nk = name_to_nk.get(ascii_fold(name_lf).lower())
    return trait_by_nk.get(nk) if nk else None

sg_by_folded = {ascii_fold(r["Player"].strip()): r for r in sg if r.get("Player")}

# Course insights
ci_by_norm: dict[str, dict] = {}
if ci_loaded:
    for row in ci_rows:
        full = (row.get("First Name","") + " " + row.get("Last Name","")).strip()
        nk   = fl_to_lf(ascii_fold(full)).lower()
        ci_by_norm[nk] = {
            "d_distance":   parse_float(row.get("D. Distance")),
            "d_accuracy":   parse_pct(row.get("D. Accuracy")),
            "gir":          parse_pct(row.get("GIR")),
            "fairway_prox": parse_prox(row.get("Fairway Prox","")),
            "rough_prox":   parse_prox(row.get("Rough Prox","")),
            "scrambling":   parse_pct(row.get("Scrambling")),
        }

# ── Wave assignments from pairings ────────────────────────────────────────────
wave_assign: dict[str, str] = {}
if PAIRINGS.exists():
    for row in load_csv(PAIRINGS):
        pname = (row.get("player_name") or
                 f"{row.get('last_name','')}, {row.get('first_name','')}".strip(", "))
        if not pname:
            continue
        wave = str(row.get("wave","")).strip().lower()
        if wave not in ("late_early","early_late"):
            wave = classify_wave(str(row.get("tee_time","")))
        wave_assign[ascii_fold(pname).strip().lower()] = wave

# ── Join leaderboard to model ─────────────────────────────────────────────────
joined: list[dict] = []
unmatched: list[str] = []
seen: set[str] = set()
duplicates: list[str] = []
_field_n = len(lb)

for row in lb:
    if not any(row.values()):
        continue
    r_name = (row.get("PLAYER") or row.get("Player") or "").strip()
    if not r_name:
        continue
    folded = ascii_fold(r_name)
    if folded in seen:
        duplicates.append(r_name)
        continue
    seen.add(folded)
    norm      = fl_to_lf(folded)
    record_nm = fl_to_lf(norm_name(r_name))
    pt        = pretournament.get(norm.lower())
    sg_row  = sg_by_folded.get(folded)

    pos_str = row.get("POS","")
    pos_num = parse_pos(pos_str)
    score   = parse_float(row.get("TOTAL") or row.get(f"R{ROUND}") or row.get("SCORE")) or 0

    sg_arg_val = parse_float(sg_row.get(SG_ARG_COL)) if (sg_row and SG_ARG_COL) else None

    wave_key  = folded.lower()
    wave_alt  = fl_to_lf(folded).lower()
    wave_val  = wave_assign.get(wave_key) or wave_assign.get(wave_alt) or "unknown"

    record = {
        "r1_name":    r_name,
        "norm_name":  record_nm,
        "r1_pos":     pos_num,
        "r1_pos_str": pos_str,
        "r1_score":   score,
        "wave":       wave_val,
        "matched":    pt is not None,
        "pt_rank":    (_board_rank.get(folded.lower()) or _board_rank.get(_deep_norm(r_name)) or pt["rank"]) if pt else None,
        "pt_tier":    pt["tier"]              if pt else None,
        "pt_vts":     parse_float(pt.get("vts_final")) if pt else None,
        "pt_win_pct": parse_float(pt.get("win_pct") or pt.get("win_prob")) if pt else None,
        "pt_top10":   parse_float(pt.get("top10_pct") or pt.get("top10_prob")) if pt else None,
        "pt_top20":   parse_float(pt.get("top20_pct") or pt.get("top20_prob")) if pt else None,
        "pt_flags":   (pt.get("anti_pattern_flags") or "") if pt else "",
        "pt_driver":  pt.get("primary_driver","") if pt else "",
        "sg_ott":  parse_float(sg_row.get("SG-Off the Tee"))       if sg_row else None,
        "sg_app":  parse_float(sg_row.get("SG-Approach to Green")) if sg_row else None,
        "sg_arg":  sg_arg_val,
        "sg_putt": parse_float(sg_row.get("SG-Putting"))           if sg_row else None,
        "sg_tot":  parse_float(sg_row.get("SG-Total"))             if sg_row else None,
        "traits":     lookup_traits(norm),
        "rank_delta": ((_board_rank.get(folded.lower()) or _board_rank.get(_deep_norm(r_name)) or pt["rank"]) - pos_num) if pt else 0,
    }
    record["ci"] = ci_by_norm.get(record["norm_name"].lower())
    joined.append(record)
    if not pt:
        print(f"[warn] Alternate detected during join: {r_name}")
        record["pt_rank"]   = _field_n + 1
        record["pt_tier"]   = 5
        record["pt_vts"]    = 50.0
        record["pt_flags"]  = "DEBUT, ALT"
        record["pt_driver"] = "alternate entry"
        record["pt_vhd"]    = 0.0
        unmatched.append(r_name)

matched = [r for r in joined if r["matched"]]
print(f"Matched {len(matched)}/{len(joined)} players | unmatched: {len(unmatched)}")

# ── Wave risk analysis ─────────────────────────────────────────────────────────
wave_scores: dict[str, list[float]] = {"early_late": [], "late_early": []}
for r in joined:
    w = r.get("wave","")
    if w in wave_scores:
        wave_scores[w].append(r["r1_score"])

wave_avgs: dict[str, float | None] = {
    w: (round(sum(s)/len(s), 3) if s else None)
    for w, s in wave_scores.items()
}

wave_risk_annotation: list[dict] = []
el_avg = wave_avgs.get("early_late")
le_avg = wave_avgs.get("late_early")
if el_avg is not None and le_avg is not None and abs(el_avg - le_avg) > 0.25:
    disadvantaged = "early_late" if el_avg > le_avg else "late_early"
    favoured      = "late_early" if disadvantaged == "early_late" else "early_late"
    diff          = round(abs(el_avg - le_avg), 3)
    desc_dis = "AM Thu/PM Fri" if disadvantaged == "early_late" else "PM Thu/AM Fri"
    for r in joined:
        if r.get("wave") == disadvantaged:
            wave_risk_annotation.append({
                "player":           r["r1_name"],
                "norm_name":        r.get("norm_name",""),
                "pt_rank":          r.get("pt_rank"),
                "r1_pos":           r.get("r1_pos"),
                "wave":             disadvantaged,
                "scoring_avg_diff": diff,
                "note": (
                    f"Disadvantaged wave ({disadvantaged}: {desc_dis}) — "
                    f"field scoring avg {diff:.2f} SG behind {favoured} group through R{ROUND}"
                ),
            })
    wave_risk_annotation.sort(key=lambda x: (x.get("pt_rank") or 999, x.get("r1_pos") or 999))
    print(f"Wave risk: {len(wave_risk_annotation)} players flagged "
          f"(disadvantaged={disadvantaged}, diff={diff:.3f})")

# ── Model performance ─────────────────────────────────────────────────────────
def group_stats(grp: list[dict]) -> dict:
    return {
        "n":           len(grp),
        "avg_r1_pos":  avg([r["r1_pos"]   for r in grp]),
        "avg_r1_score":avg([r["r1_score"] for r in grp]),
        "in_r1_top10": sum(1 for r in grp if r["r1_pos"] <= 10),
        "in_r1_top20": sum(1 for r in grp if r["r1_pos"] <= 20),
    }

model_perf = {
    "pt_top10":  group_stats([r for r in matched if r.get("pt_rank") and r["pt_rank"] <= 10]),
    "pt_top20":  group_stats([r for r in matched if r.get("pt_rank") and r["pt_rank"] <= 20]),
    "tier1":     group_stats([r for r in matched if r.get("pt_tier") == 1]),
    "tier2":     group_stats([r for r in matched if r.get("pt_tier") == 2]),
    "tier1_2":   group_stats([r for r in matched if r.get("pt_tier") in (1, 2)]),
    "all_field": group_stats(joined),
}

pairs = [(r["pt_rank"], r["r1_pos"]) for r in matched if r.get("pt_rank")]
n  = len(pairs)
d2 = sum((a - b)**2 for a, b in pairs)
spearman_rho = round(1 - 6 * d2 / (n * (n**2 - 1)), 3) if n >= 10 else 0.0
if math.isnan(spearman_rho) or math.isinf(spearman_rho):
    spearman_rho = 0.000

# ── Trait audit ───────────────────────────────────────────────────────────────
top10_group = [r for r in joined if r["r1_pos"] <= 10]
all_with_traits = [r for r in matched if r.get("traits")]
top10_with_traits = [r for r in top10_group if r.get("matched") and r.get("traits")]

def sg_summary(grp: list[dict]) -> dict:
    return {k: avg([r[k] for r in grp]) for k in ("sg_ott","sg_app","sg_arg","sg_putt","sg_tot")}

sg_leaders_top10 = sg_summary(top10_group)
sg_leaders_top18 = sg_summary([r for r in joined if r["r1_pos"] <= 18])

trait_audit: dict[str, dict] = {}
for tk in TRAIT_COLS:
    w    = VENUE_WEIGHTS[tk]
    t10v = [r["traits"][tk] for r in top10_with_traits if r["traits"].get(tk) is not None]
    fv   = [r["traits"][tk] for r in all_with_traits   if r["traits"].get(tk) is not None]
    t10a = avg(t10v)
    fa   = avg(fv)
    delta = round(t10a - fa, 1) if t10a is not None and fa is not None else None

    sg_key  = SG_PROXY.get(tk)
    sg_t10  = avg([r[sg_key] for r in top10_group if r.get(sg_key) is not None]) if sg_key else None
    sg_all  = avg([r[sg_key] for r in joined      if r.get(sg_key) is not None]) if sg_key else None
    sg_delta = round(sg_t10 - sg_all, 3) if sg_t10 is not None and sg_all is not None else None

    if delta is None and sg_delta is None:
        signal = "not_testable"
    else:
        d = delta if delta is not None else 0
        if   d >= TRAIT_SIGNAL_THRESHOLDS["strong"]:  signal = "validated"
        elif d >= TRAIT_SIGNAL_THRESHOLDS["lean"]:    signal = "mixed"
        elif d >= TRAIT_SIGNAL_THRESHOLDS["neutral"]: signal = "neutral"
        else:                                          signal = "weak"

    trait_audit[tk] = {
        "venue_weight":    w,
        "top10_trait_avg": t10a,
        "field_trait_avg": fa,
        "trait_delta":     delta,
        "sg_proxy":        sg_key,
        "sg_top10":        sg_t10,
        "sg_field":        0.0 if sg_all == 0 else sg_all,
        "sg_delta":        sg_delta,
        "signal":          signal,
        "sample_n_top10":  len(t10v),
        "sample_n_field":  len(fv),
    }

# ── BRIE-Z sub-driver augmentation for app_150_200 (schema v1.1) ─────────────
def _brie_z_augment() -> dict:
    try:
        cfg_p = _ROOT / "config" / "db_config.json"
        if cfg_p.exists():
            with open(cfg_p) as fh:
                db_path = _ROOT / json.load(fh)["db_path"]
        else:
            db_path = _ROOT / "data" / "venuedna_master.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        bz_rows = conn.execute(
            "SELECT brie_z_score, wave_bonus "
            "FROM active_field_projections WHERE brie_z_score IS NOT NULL"
        ).fetchall()
        bz_vals = [float(r["brie_z_score"]) for r in bz_rows]
        wb_vals = [float(r["wave_bonus"] or 0) for r in bz_rows]

        g_rows = conn.execute(
            "SELECT app_150_200_fw_sg, app_150_200_poor_shot_avoidance "
            "FROM local_player_granular_traits "
            "WHERE app_150_200_fw_sg IS NOT NULL"
        ).fetchall()
        fw_vals  = [float(r["app_150_200_fw_sg"]) for r in g_rows]
        psa_vals = [float(r["app_150_200_poor_shot_avoidance"]) for r in g_rows
                    if r["app_150_200_poor_shot_avoidance"] is not None]

        # Course rough penalty
        c_row = conn.execute(
            "SELECT difficulty_app_rough_vs_fw FROM course_profiles WHERE course_key = ?",
            (COURSE_KEY,),
        ).fetchone()
        penalty = float(c_row[0]) if (c_row and c_row[0] is not None) else 0.0
        conn.close()

        return {
            "schema_version":       "1.1",
            "available":            len(bz_vals) > 0,
            "n_players":            len(bz_vals),
            "field_avg_brie_z":     avg(bz_vals),
            "field_avg_fw_sg":      avg(fw_vals),
            "field_avg_psa":        avg(psa_vals),
            "course_rough_penalty": penalty,
            "wave_bonus_applied_n": sum(1 for v in wb_vals if v > 0),
            "note": (
                "BRIE-Z = 0.6×fw_sg + 0.4×psa − course_rough_penalty. "
                "Wave bonus (+0.15) applied before Z-scoring."
            ),
        }
    except Exception as exc:
        return {"available": False, "schema_version": "1.1", "error": str(exc)}

if "app_150_200" in trait_audit:
    trait_audit["app_150_200"]["brie_z"] = _brie_z_augment()

# ── Course insights enrichment ────────────────────────────────────────────────
top10_ci = [r for r in top10_group if r.get("ci")]
all_ci   = [r for r in joined      if r.get("ci")]

def ci_avg_field(field, grp):
    vals = [r["ci"][field] for r in grp if r.get("ci") and r["ci"].get(field) is not None]
    return avg(vals)

def enr_delta(field, direction, t10v, fv):
    if t10v is None or fv is None:
        return None
    return round(fv - t10v, 2) if direction == "lower_better" else round(t10v - fv, 2)

def enr_signal(field, delta, base_sig):
    if delta is None:
        return "not_available"
    if delta < 0:
        return "contradicted"
    if delta < CI_SIG.get(field, 3.0):
        return "neutral"
    if delta >= CI_STR.get(field, 5.0) and base_sig in ("mixed","neutral","weak","not_testable"):
        return "upgraded"
    return "confirmed"

if ci_loaded:
    for tk, mapping in CI_TRAIT_MAP.items():
        primary   = mapping["primary"]
        direction = mapping["direction"]
        secondary = mapping["secondary"]
        if primary is None:
            trait_audit[tk]["enrichment"] = {"available": False, "reason": "no_direct_proxy"}
            continue
        t10_pri = ci_avg_field(primary, top10_ci)
        f_pri   = ci_avg_field(primary, all_ci)
        delta_p = enr_delta(primary, direction, t10_pri, f_pri)
        base_sig = trait_audit[tk]["signal"]
        e_sig    = enr_signal(primary, delta_p, base_sig)
        sec_dir  = "lower_better" if secondary in ("fairway_prox","rough_prox") else "higher_better"
        t10_sec  = ci_avg_field(secondary, top10_ci) if secondary else None
        f_sec    = ci_avg_field(secondary, all_ci)   if secondary else None
        sec_d    = enr_delta(secondary, sec_dir, t10_sec, f_sec) if secondary else None
        upg_sig  = UPGRADE_MAP.get(base_sig, base_sig) if e_sig == "upgraded" else base_sig
        trait_audit[tk]["enrichment"] = {
            "available":          True,
            "source":             f"round{ROUND}_course_insights.csv",
            "primary_field":      primary,
            "direction":          direction,
            "top10_primary":      t10_pri,
            "field_primary":      f_pri,
            "delta_primary":      delta_p,
            "top10_secondary":    t10_sec,
            "field_secondary":    f_sec,
            "delta_secondary":    sec_d,
            "enrichment_signal":  e_sig,
            "upgraded_signal":    upg_sig,
        }
        if e_sig == "upgraded":
            trait_audit[tk]["signal"] = upg_sig
            trait_audit[tk]["signal_upgraded_by_enrichment"] = True
else:
    for tk in TRAIT_COLS:
        trait_audit[tk]["enrichment"] = {
            "available": False,
            "reason": f"round{ROUND}_course_insights.csv not present",
        }

def compute_source_confidence(tk, signal, enrichment):
    enr = enrichment if isinstance(enrichment, dict) else {}
    if not enr.get("available"):
        if signal == "validated":          return "proxy-confirmed"
        if signal in ("mixed","neutral"):  return "weak-proxy"
        return "not-testable"
    e_sig = enr.get("enrichment_signal","")
    pf    = enr.get("primary_field","")
    if tk in DIRECT_ENRICHMENT and DIRECT_ENRICHMENT[tk] == pf and e_sig in ("confirmed","upgraded"):
        return "direct"
    if signal == "validated" and e_sig in ("confirmed","upgraded"):
        return "proxy-confirmed"
    if signal in ("mixed","neutral") or e_sig == "neutral":
        return "weak-proxy"
    return "not-testable"

for tk in trait_audit:
    trait_audit[tk]["source_confidence"] = compute_source_confidence(
        tk, trait_audit[tk]["signal"], trait_audit[tk].get("enrichment")
    )

# ── Canonical 10-trait enforcement (Schema v1.1) ──────────────────────────────
# Evict legacy / non-canonical keys that predate schema v1.1
for _nck in [tk for tk in list(trait_audit.keys()) if tk not in _CANONICAL_TRAITS]:
    del trait_audit[_nck]
# Pad any canonical traits absent from the event config with zeroed placeholders
for _ct in _CANONICAL_TRAITS:
    if _ct not in trait_audit:
        trait_audit[_ct] = {
            "venue_weight":    0.00,
            "top10_trait_avg": None,
            "field_trait_avg": None,
            "trait_delta":     None,
            "sg_proxy":        None,
            "sg_top10":        None,
            "sg_field":        None,
            "sg_delta":        None,
            "signal":          "not_testable",
            "sample_n_top10":  0,
            "sample_n_field":  0,
            "source_confidence": "not-testable",
            "enrichment": {"available": False, "reason": "trait_not_in_event_config"},
        }

# ── Rank deltas ───────────────────────────────────────────────────────────────
by_delta = sorted([r for r in matched if r.get("pt_rank")], key=lambda x: -x["rank_delta"])

def player_summary(r: dict) -> dict:
    return {
        k: r[k] for k in (
            "r1_name","norm_name","r1_pos","r1_pos_str","r1_score",
            "pt_rank","pt_tier","pt_vts","pt_flags","pt_driver",
            "rank_delta","sg_ott","sg_app","sg_arg","sg_putt","sg_tot","wave",
        ) if k in r
    }

# ── Slippage risk ─────────────────────────────────────────────────────────────
_ELIM_PFX = ("CUT", "MC", "WD", "DQ", "MDF")
slippage_risk: list[dict] = []
for r in matched:
    if r["r1_pos"] > 20:
        continue
    if str(r.get("r1_pos_str", "")).upper().strip().startswith(_ELIM_PFX):
        continue
    risks = []
    sg_putt = r.get("sg_putt") or 0
    sg_app  = r.get("sg_app")  or 0
    pt_rank = r.get("pt_rank") or 99
    if sg_putt > 2.0 and sg_app < 0.3:
        risks.append(f"putting-driven ({sg_putt:+.2f} putt vs {sg_app:+.2f} APP) — regression likely")
    if pt_rank > 55 and r["r1_pos"] <= 12 and sg_app < 0.5:
        risks.append(f"no pre-tournament basis (model rank {pt_rank}), heat-check round")
    if risks:
        rec = player_summary(r)
        rec["risk_flags"] = risks
        slippage_risk.append(rec)
slippage_risk.sort(key=lambda x: x.get("r1_pos", 99))

# ── Risers ────────────────────────────────────────────────────────────────────
def riser_thesis_score(r: dict) -> int:
    score = 0
    if r.get("sg_app")  and r["sg_app"]  > 0.5: score += 2
    if r.get("sg_arg")  and r["sg_arg"]  > 0.3: score += 1
    if r.get("sg_putt") and r["sg_putt"] > 0.3: score += 1
    return score

# Extract high-spin player set early so _make_thesis_note can reference it
_spin_early_cfg  = cfg.get("weekend_high_spin_penalty", {})
_SPIN_ROUND_GATE = (
    _spin_early_cfg.get("active_from_round", 99)
    if isinstance(_spin_early_cfg, dict) else 99
)
_SPIN_PLAYERS_EARLY: set[str] = (
    {ascii_fold(p).lower() for p in (_spin_early_cfg.get("players") or [])}
    if isinstance(_spin_early_cfg, dict) else set()
)

_seen_notes: set[str] = set()

def _make_thesis_note(r: dict) -> str:
    name_key   = ascii_fold(r.get("r1_name", "")).lower()
    is_hi_spin = (ROUND >= _SPIN_ROUND_GATE) and (name_key in _SPIN_PLAYERS_EARLY)

    sg_app  = r.get("sg_app")  or 0.0
    sg_arg  = r.get("sg_arg")  or 0.0
    sg_putt = r.get("sg_putt") or 0.0
    sg_ott  = r.get("sg_ott")  or 0.0
    pt_vts  = r.get("pt_vts")  or 0.0
    score   = r.get("r1_score", 0)

    notes = []

    # app_150_200 — primary Birkdale separation trait (SG-APP proxy)
    if sg_app >= 0.8:
        notes.append(f"app_150_200 elite (SG-APP {sg_app:+.2f})")
    elif sg_app >= 0.4:
        notes.append(f"app_150_200 positive (SG-APP {sg_app:+.2f})")
    elif sg_app < -0.3:
        notes.append(f"app_150_200 below field (SG-APP {sg_app:+.2f})")

    # ott_accuracy — positional driving signal
    if sg_ott >= 0.5:
        notes.append(f"ott_accuracy supported (SG-OTT {sg_ott:+.2f})")
    elif sg_ott < -0.4:
        notes.append(f"ott_accuracy stressed (SG-OTT {sg_ott:+.2f})")

    # pt_vts — pre-event fit anchor; always included to guarantee note uniqueness
    notes.append(f"pt_vts={pt_vts:.2f}")

    # ARG scrambling
    if sg_arg >= 0.5:
        notes.append(f"scrambling positive ({sg_arg:+.2f} ARG)")
    elif sg_arg < -0.4:
        notes.append(f"scrambling stressed ({sg_arg:+.2f} ARG)")

    # Putting
    if sg_putt >= 0.8:
        notes.append(f"putting hot ({sg_putt:+.2f} PUTT)")
    elif sg_putt < -0.8:
        notes.append(f"putting suppressed ({sg_putt:+.2f} PUTT)")

    # Pre-event driver
    if r.get("pt_driver"):
        notes.append(f"pre-event driver: {r['pt_driver']}")

    # Score context if narrative is thin
    if len(notes) < 2:
        notes.append(f"R{ROUND} score {score:+d}")

    # High-spin trajectory risk — injected after substantive content
    if is_hi_spin:
        notes.append(
            "TRAJECTORY RISK: NNW 18kts steady baseline — unstable landing windows and "
            f"descent variability under firm/fast Birkdale stress (R{ROUND})"
        )

    base = " | ".join(notes)
    if base in _seen_notes:
        raise SystemExit(
            f"FATAL: Duplicate player brief detected for '{r.get('r1_name', '')}'. "
            f"Narrative engine must produce unique analysis per player. "
            f"Text: \"{base[:120]}...\""
        )
    _seen_notes.add(base)
    return base

weekend_risers: list[dict] = []
for r in by_delta[:20]:
    if str(r.get("r1_pos_str", "")).upper().strip().startswith(("CUT", "MC", "WD", "DQ", "MDF")):
        continue
    ts = riser_thesis_score(r)
    if ts >= 2 and r.get("r1_score", 0) <= -3:
        rec = player_summary(r)
        rec["thesis_score"] = ts
        rec["thesis_note"]  = _make_thesis_note(r)
        weekend_risers.append(rec)

risers   = [player_summary(r) for r in by_delta[:12]]
slippage = [player_summary(r) for r in sorted(
    [r for r in matched if r.get("pt_rank") and r["pt_rank"] <= 35],
    key=lambda x: x["rank_delta"]
)[:10]]

# ── Live lean notes ───────────────────────────────────────────────────────────
slippage_names = {r["r1_name"] for r in slippage_risk}
sustainable_leaders = [
    r for r in joined
    if r["r1_pos"] <= 6
    and r["r1_name"] not in slippage_names
    and (r.get("sg_app") or 0) > 0.5
    and not str(r.get("r1_pos_str", "")).upper().strip().startswith(_ELIM_PFX)
]

watch_next: list[dict] = [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str",""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      " | ".join(r.get("risk_flags",[])),
        "flag_type": "slippage",
    }
    for r in slippage_risk[:5]
] + [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str",""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      f"approach-backed leader (APP {(r.get('sg_app') or 0):+.2f}) — sustainable position",
        "flag_type": "sustainable",
    }
    for r in sustainable_leaders[:2]
]

putt_outliers = sorted(
    [r for r in slippage_risk if (r.get("sg_putt") or 0) > 2.0],
    key=lambda x: -(x.get("sg_putt") or 0)
)

# Firm/fast override — three traits guaranteed in lean_up matching active multipliers.
# These appear regardless of whether the data audit flags them as "validated" because
# the SG CSV multipliers (OTT x1.10, APP x1.15, ARG x1.10) are baked in at data prep.
_FF_LEAN: list[dict] = []
if WX_SPEED > 0:
    _wx_kts = int(WX_SPEED)
    _FF_LEAN = [
        {"trait": "app_150_200", "delta": None, "confidence": "firm-fast-override",
         "multiplier": "APP x1.15",
         "enr_signal": f"175-225yd separation elevated; NNW {_wx_kts}kts active"},
        {"trait": "app_200+",    "delta": None, "confidence": "firm-fast-override",
         "multiplier": "APP x1.15",
         "enr_signal": "long-iron into exposed greens — primary weekend stress vector"},
        {"trait": "ott_accuracy","delta": None, "confidence": "firm-fast-override",
         "multiplier": "OTT x1.10",
         "enr_signal": f"positional driving premium — firm/fast Birkdale corridors ({_WX.get('tide','N/A')})"},
    ]
_ff_lean_keys = {e["trait"] for e in _FF_LEAN}

lean_up = _FF_LEAN + [
    {"trait": tk, "delta": trait_audit[tk].get("trait_delta"),
     "confidence": trait_audit[tk].get("source_confidence", "proxy-confirmed"),
     "enr_signal": (trait_audit[tk].get("enrichment") or {}).get("enrichment_signal")}
    for tk in TRAIT_COLS
    if tk in trait_audit and trait_audit[tk]["signal"] == "validated"
    and tk not in _ff_lean_keys
]
lean_down = [{"trait": tk, "delta": trait_audit[tk].get("trait_delta")}
             for tk in TRAIT_COLS
             if tk in trait_audit and trait_audit[tk]["signal"] in ("weak", "not_testable")]

rho_note = (
    f"R{ROUND} rho={spearman_rho} — tournament complete." if IS_FINAL
    else f"R{ROUND} rho={spearman_rho} — separation expected to sharpen by R{ROUND+1}."
)

live_lean_notes: dict = {
    "round":                  ROUND,
    "next_round":             ROUND + 1 if not IS_FINAL else None,
    "lean_up_traits":         lean_up,
    "lean_down_traits":       lean_down,
    "putt_caution":           len(putt_outliers) > 0,
    "putt_outliers":          [
        {"player": r["r1_name"], "sg_putt": r.get("sg_putt"), "sg_app": r.get("sg_app")}
        for r in putt_outliers[:3]
    ],
    "watch_next_round":       watch_next,
    "wave_risk_annotation":   wave_risk_annotation,
    "wave_scoring_averages":  wave_avgs,
    "rho_note":               rho_note,
}

# ── Cumulative learning ───────────────────────────────────────────────────────
CUM_OUT = OUT / f"{EVENT_SLUG}_cumulative_learning.json"
CUM_DEP = OUTPUT_DIR / "cumulative_learning.json"

this_round_entry = {
    "round":        ROUND,
    "generated_at": TODAY,
    "spearman_rho": spearman_rho,
    "trait_signals": {
        tk: {
            "signal":            v["signal"],
            "source_confidence": v.get("source_confidence","not-testable"),
            "trait_delta":       v.get("trait_delta"),
            "sg_delta":          v.get("sg_delta"),
            "enrichment_signal": (v.get("enrichment") or {}).get("enrichment_signal"),
        }
        for tk, v in trait_audit.items()
    },
    "model_hits": {
        "pt_top10_in_top10": model_perf["pt_top10"]["in_r1_top10"],
        "pt_top10_in_top20": model_perf["pt_top10"]["in_r1_top20"],
        "tier1_2_in_top20":  model_perf["tier1_2"]["in_r1_top20"],
    },
    "risers":           [r["r1_name"] for r in weekend_risers],
    "slippage":         [r["r1_name"] for r in slippage_risk],
    "wave_annotation_n": len(wave_risk_annotation),
}

if CUM_OUT.exists():
    with open(CUM_OUT, encoding="utf-8") as f:
        cumulative_learning = json.load(f)
elif CUM_DEP.exists():
    with open(CUM_DEP, encoding="utf-8") as f:
        cumulative_learning = json.load(f)
    print(f"[info] Cumulative state loaded from deploy fallback: {CUM_DEP}")
else:
    cumulative_learning = {
        "schema_version":    "1.0",
        "event_slug":        EVENT_SLUG,
        "created_at":        TODAY,
        "per_round":         {},
        "cumulative_signals": {
            tk: {
                "rounds_observed":    [],
                "signal_history":     [],
                "confidence_history": [],
                "delta_history":      [],
                "consensus":          None,
                "consensus_confidence": None,
            }
            for tk in _CANONICAL_TRAITS
        },
    }

cumulative_learning["last_updated"]     = TODAY
cumulative_learning["updated_at"]       = BUILD_TS
cumulative_learning["rounds_completed"] = ROUND
cumulative_learning["is_final"]         = IS_FINAL
cumulative_learning["per_round"][str(ROUND)] = this_round_entry

rounds_present = sorted(set(cumulative_learning.get("rounds_present",[]) + [ROUND]))
cumulative_learning["rounds_present"] = rounds_present

for tk, v in trait_audit.items():
    cs_entry = cumulative_learning["cumulative_signals"].setdefault(tk, {
        "rounds_observed":[], "signal_history":[], "confidence_history":[],
        "delta_history":[], "consensus":None, "consensus_confidence":None,
    })
    observed = cs_entry.get("rounds_observed",[])
    if ROUND not in observed:
        cs_entry.setdefault("rounds_observed",    []).append(ROUND)
        cs_entry.setdefault("signal_history",     []).append(v["signal"])
        cs_entry.setdefault("confidence_history", []).append(v.get("source_confidence","not-testable"))
        cs_entry.setdefault("delta_history",      []).append(v.get("trait_delta"))
    else:
        idx = observed.index(ROUND)
        cs_entry["signal_history"][idx]     = v["signal"]
        cs_entry["confidence_history"][idx] = v.get("source_confidence","not-testable")
        cs_entry["delta_history"][idx]      = v.get("trait_delta")
    cs_entry["consensus"]            = cs_entry["signal_history"][-1]
    cs_entry["consensus_confidence"] = cs_entry["confidence_history"][-1]

# ── Leaderboard snapshot ──────────────────────────────────────────────────────
lb_snapshot = [
    {k: r[k] for k in ("r1_name","r1_pos","r1_pos_str","r1_score","pt_rank",
                         "pt_tier","pt_vts","sg_app","sg_putt","sg_ott","sg_arg","sg_tot","wave","rank_delta")
     if k in r}
    for r in joined
]

def _sg_field(key):
    vals = [p.get(key) for p in lb_snapshot if p.get(key) is not None]
    if not vals: return None
    v = round(sum(vals)/len(vals), 3)
    return 0.0 if v == 0 else v

sg_field_all = {k: _sg_field(k) for k in ("sg_ott","sg_app","sg_arg","sg_putt","sg_tot")}

sg_dimension_leaders = {
    dim: [
        {"r1_name": r["r1_name"], "r1_pos": r.get("r1_pos_str"), "value": r[dim], "r1_score": r["r1_score"]}
        for r in sorted([x for x in joined if x.get(dim) is not None], key=lambda x: -x[dim])[:5]
    ]
    for dim in ("sg_app","sg_putt","sg_ott","sg_arg")
}

# ── Historical cumulative SG aggregation (rounds 2-4) ────────────────────────
def _load_hist_sg_tot(rnd: int) -> dict[str, float]:
    for cand in [OUT / f"round{rnd}", OUT / f"round{rnd} player & course stats"]:
        if cand.exists():
            p = cand / f"round{rnd}_player_strokes_gained.csv"
            if p.exists():
                result: dict[str, float] = {}
                for row in load_csv(p):
                    name = (row.get("Player") or row.get("PLAYER", "")).strip()
                    if not name:
                        continue
                    lf = fl_to_lf(ascii_fold(name)).lower()
                    v = parse_float(row.get("SG-Total") or row.get("sg-total"))
                    if v is not None:
                        result[lf] = v
                return result
    return {}

# pop_registry : full Round 1 population — stable denominator, never shrinks
# cumulative_sg_by_norm : active players only — used in V_p(t) and softmax
cumulative_sg_by_norm: dict[str, float] = {}
pop_registry:          dict[str, float] = {}

if ROUND == 1:
    for _r in joined:
        _nk = _r["norm_name"].lower()
        _v  = _r.get("sg_tot") or 0.0
        cumulative_sg_by_norm[_nk] = _v
        pop_registry[_nk]          = _v
else:
    # _hist_totals[0] = R1 SG map — serves double duty as population anchor
    _hist_totals = [_load_hist_sg_tot(r) for r in range(1, ROUND)]
    _r1_sg_map   = _hist_totals[0] if _hist_totals else {}
    _pop_keys    = set(_r1_sg_map.keys())
    _active_nks  = {_r["norm_name"].lower() for _r in joined}

    # Active players: sum all prior rounds + current round
    for _r in joined:
        _nk = _r["norm_name"].lower()
        cumulative_sg_by_norm[_nk] = (_r.get("sg_tot") or 0.0) + sum(
            h.get(_nk, 0.0) for h in _hist_totals
        )

    # Full population: active entries + frozen cut/WD/DQ vectors
    for _nk in _pop_keys:
        if _nk in _active_nks:
            pop_registry[_nk] = cumulative_sg_by_norm[_nk]
        else:
            # Eliminated: freeze at terminal sum from all completed prior rounds
            pop_registry[_nk] = sum(h.get(_nk, 0.0) for h in _hist_totals)

# ── Live in-round probability modulation ─────────────────────────────────────
_vts_vals = [r["pt_vts"] for r in joined if r.get("pt_vts") is not None]
field_vts_mean = sum(_vts_vals) / len(_vts_vals) if _vts_vals else 50.0

# Baseline anchored to full R1 population — not just surviving active field
_pop_vals = list(pop_registry.values())
_field_avg_cum_sg = sum(_pop_vals) / len(_pop_vals) if _pop_vals else 0.0

_gamma = 0.35 * ROUND

# ── Weekend high-spin penalty (firm/fast Birkdale override) ───────────────────
_spin_cfg    = cfg.get("weekend_high_spin_penalty", {})
_spin_active = (
    isinstance(_spin_cfg, dict)
    and ROUND >= _spin_cfg.get("active_from_round", 99)
    and _spin_cfg.get("penalty_vts", 0) > 0
)
_spin_pen_vts     = _spin_cfg.get("penalty_vts", 0.0) if _spin_active else 0.0
_spin_pen_players = (
    {ascii_fold(p).lower() for p in (_spin_cfg.get("players") or [])}
    if _spin_active else set()
)
if _spin_active:
    print(f"Weekend spin penalty: -{_spin_pen_vts:.2f} VTS applied to "
          f"{len(_spin_pen_players)} high-apex/high-spin players (R{ROUND})")

_ordered_nks = [r["norm_name"].lower() for r in joined]
_vpt = [
    (r["pt_vts"] if r.get("pt_vts") is not None else field_vts_mean)
    - (_spin_pen_vts if ascii_fold(r["r1_name"]).lower() in _spin_pen_players else 0.0)
    + _gamma * (cumulative_sg_by_norm.get(r["norm_name"].lower(), 0.0) - _field_avg_cum_sg)
    for r in joined
]

# ── Wind/wave latent penalty: depress V_p(t) for disadvantaged draw ───────────
# Latent_adj = Latent_raw − (wave_delta × WindSeverityFactor)
# WindSeverityFactor = min(1.0, speed_kts / 20.0)  — only active when speed > 15 kts
_wave_penalty_amounts: list[float] = [0.0] * len(joined)
if WAVE_PENALTY > 0 and WX_DISADV_WAVE:
    _penalized_n = 0
    for _i, _r in enumerate(joined):
        if _r.get("wave") == WX_DISADV_WAVE:
            _vpt[_i] -= WAVE_PENALTY
            _vpt[_i] = max(0.1, _vpt[_i])
            _wave_penalty_amounts[_i] = -WAVE_PENALTY
            _penalized_n += 1
    print(f"Wave penalty applied: {_penalized_n} players in '{WX_DISADV_WAVE}' draw penalized -{WAVE_PENALTY} latent pts")

_mu           = sum(_vpt) / len(_vpt) if _vpt else 0.0
field_std_dev = (sum((v - _mu) ** 2 for v in _vpt) / len(_vpt)) ** 0.5 if _vpt else 1.0
_sigma        = max(1e-9, field_std_dev)
_zs           = [(v - _mu) / _sigma for v in _vpt]

_LIVE_TEMPS = {"win": 0.30, "top5": 0.55, "top10": 0.75, "top20": 1.10}

def _softmax_t(z_arr: list[float], temp: float) -> list[float]:
    scaled = [z / temp for z in z_arr]
    max_s  = max(scaled)
    exps   = [math.exp(s - max_s) for s in scaled]
    total  = sum(exps)
    return [e / total for e in exps]

if not _zs:
    raise SystemExit("ERROR: No field data — leaderboard join produced zero players.")

# ── CUT/WD/DQ hard-clamp ─────────────────────────────────────────────────────
# Eliminated players are zeroed before softmax so remaining probability sums
# to exactly 100% over the active weekend field only.
_ELIM_PREFIXES = ("CUT", "MC", "WD", "DQ", "MDF")
_active_mask   = [
    not str(r.get("r1_pos_str", "")).upper().strip().startswith(_ELIM_PREFIXES)
    for r in joined
]
_active_zs = [_zs[i] for i, ok in enumerate(_active_mask) if ok]
_n_elim    = _active_mask.count(False)
if _n_elim:
    print(f"CUT/WD/DQ clamp: {_n_elim} eliminated players zeroed; softmax over {len(_active_zs)} active players")

if not _active_zs:
    raise SystemExit("ERROR: No active players remaining after CUT/WD/DQ elimination.")

_wa   = _softmax_t(_active_zs, _LIVE_TEMPS["win"])
_t5a  = _softmax_t(_active_zs, _LIVE_TEMPS["top5"])
_t10a = _softmax_t(_active_zs, _LIVE_TEMPS["top10"])
_t20a = _softmax_t(_active_zs, _LIVE_TEMPS["top20"])

# Map active results back to full-field index; eliminated entries receive 0.0
_win, _top5, _top10, _top20 = [], [], [], []
_ai = 0
for _ok in _active_mask:
    if _ok:
        _win.append(_wa[_ai]);   _top5.append(_t5a[_ai])
        _top10.append(_t10a[_ai]); _top20.append(_t20a[_ai])
        _ai += 1
    else:
        _win.append(0.0); _top5.append(0.0); _top10.append(0.0); _top20.append(0.0)

for _i in range(len(_ordered_nks)):
    _top5[_i]  = max(_top5[_i],  _win[_i])
    _top10[_i] = max(_top10[_i], _top5[_i])
    _top20[_i] = max(_top20[_i], _top10[_i])

live_probs_by_norm: dict[str, dict] = {
    _ordered_nks[i]: {
        "win_pct":           round(_win[i]   * 100, 2),
        "top5_pct":          round(_top5[i]  * 100, 2),
        "top10_pct":         round(_top10[i] * 100, 2),
        "top20_pct":         round(_top20[i] * 100, 2),
        "v_p_t":             round(_vpt[i], 4),
        "cumulative_sg_tot": round(cumulative_sg_by_norm.get(_ordered_nks[i], 0.0), 4),
    }
    for i in range(len(_ordered_nks))
}

for _i, rec in enumerate(lb_snapshot):
    _nk = joined[_i]["norm_name"].lower()
    _lp = live_probs_by_norm.get(_nk, {})
    rec["live_win_pct"]      = _lp.get("win_pct")
    rec["live_top5_pct"]     = _lp.get("top5_pct")
    rec["live_top10_pct"]    = _lp.get("top10_pct")
    rec["live_top20_pct"]    = _lp.get("top20_pct")
    rec["v_p_t"]             = _lp.get("v_p_t")
    rec["cumulative_sg_tot"] = _lp.get("cumulative_sg_tot")
    _pw = joined[_i].get("wave", "unknown")
    rec["wave_draw"]    = "AM" if _pw == "early_late" else "PM" if _pw == "late_early" else "Neutral"
    _raw_pen = round(_wave_penalty_amounts[_i], 4) if _i < len(_wave_penalty_amounts) else 0.0
    rec["wave_penalty"] = 0.00 if rec["wave_draw"] == "Neutral" else _raw_pen

holes_data: list[dict] = []
if cs_loaded:
    for row in cs:
        try:
            holes_data.append({
                "hole":       int(row["Hole"]),
                "par":        int(row["Par"]),
                "yards":      int(row["Yards"]),
                "avg":        parse_float(row["Avg"]),
                "rank":       int(row["Rank"]),
                "plus_minus": parse_float(row["Plus - Minus"]),
                "birdies":    int(row["Birdies"]),
                "pars":       int(row["Pars"]),
                "bogeys":     int(row["Bogeys"]),
                "dbl":        int(row["DBL+"]),
            })
        except (ValueError, KeyError) as e:
            print(f"[warn] Skipping course stats row: {e}")

easiest = sorted(holes_data, key=lambda x: -x["birdies"])[:5]    if holes_data else []
hardest = sorted(holes_data, key=lambda x: -(x["bogeys"]+x["dbl"]))[:3] if holes_data else []

# ── Build enrichment summary ──────────────────────────────────────────────────
if ci_loaded and all_ci:
    upgraded_traits  = [tk for tk in trait_audit if trait_audit[tk].get("signal_upgraded_by_enrichment")]
    confirmed_traits = [tk for tk in trait_audit
                        if (trait_audit[tk].get("enrichment") or {}).get("enrichment_signal") == "confirmed"]
    enrichment_summary = {
        "source":           f"round{ROUND}_course_insights.csv",
        "player_match_n":   len(all_ci),
        "player_total":     len(joined),
        "traits_upgraded":  upgraded_traits,
        "traits_confirmed": confirmed_traits,
    }
else:
    enrichment_summary = None

# ── Assemble output ───────────────────────────────────────────────────────────
round_label = "Final Tournament" if FINAL_BUILD else ("Final Round" if IS_FINAL else f"Round {ROUND}")
if FINAL_BUILD:
    round_sources = ["final_leaderboard.csv","final_tournament_player_strokes_gained.csv",
                     f"{EVENT_SLUG}_trait_form_matrix.csv","deploy/data/event_payload.json"]
else:
    round_sources = [f"round{ROUND}_leaderboard.csv", f"round{ROUND}_player_strokes_gained.csv",
                     f"{EVENT_SLUG}_trait_form_matrix.csv", "deploy/data/event_payload.json"]
if cs_loaded: round_sources.append(f"round{ROUND}_course_stats.csv")
if ci_loaded: round_sources.append(f"round{ROUND}_course_insights.csv")

output = {
    "schema_version":         "1.1",
    "generated_at":           TODAY,
    "build_timestamp":        BUILD_TS,
    "round":                  ROUND,
    "event_slug":             EVENT_SLUG,
    "enrichment_used":        ci_loaded,
    "metadata": {
        "event_name":         EVENT_NAME,
        "course_name":        COURSE_NAME,
        "par":                PAR,
        "round_label":        round_label,
        "is_final":           IS_FINAL,
        "is_full_tournament": FINAL_BUILD,
        "favored_wave":       FAVORED_WAVE,
        "wx_speed_kts":       WX_SPEED,
        "wx_direction":       _WX.get("direction", "N/A"),
        "wx_wave_delta":      WX_DELTA,
        "wx_tide":            _WX.get("tide", "N/A"),
    },
    "round_sources":          round_sources,
    "course_insights_loaded": ci_loaded,
    "enrichment_summary":     enrichment_summary,
    "live_lean_notes":        live_lean_notes,
    "match_summary": {
        "matched":        len(matched),
        "total_r1":       len(joined),
        "unmatched":      unmatched,
        "match_rate_pct": round(len(matched)/len(joined)*100, 1) if joined else 0,
    },
    "model_performance": {
        "spearman_rho": spearman_rho,
        "groups":       model_perf,
    },
    "sg_leader_averages": {
        "top10":      sg_leaders_top10,
        "top18":      sg_leaders_top18,
        "full_field": sg_field_all,
    },
    "trait_audit":          trait_audit,
    "risers":               risers,
    "slippage":             slippage,
    "weekend_risers":       weekend_risers,
    "slippage_risk":        slippage_risk,
    "leaderboard_snapshot": lb_snapshot,
    "dimension_leaders":    sg_dimension_leaders,
    "live_probability_engine": {
        "round":                  ROUND,
        "gamma":                  _gamma,
        "field_vts_mean":         round(field_vts_mean, 4),
        "field_avg_cum_sg":       round(_field_avg_cum_sg, 4),
        "temperatures":           _LIVE_TEMPS,
        "prior_rounds_used":      list(range(1, ROUND)),
        "population_anchor_size": len(pop_registry),
        "active_field_size":      len(cumulative_sg_by_norm),
        "eliminated_frozen_count": len(pop_registry) - len(cumulative_sg_by_norm),
        "wave_penalty_params": {
            "wx_speed_kts":       WX_SPEED,
            "wx_delta_strokes":   WX_DELTA,
            "disadvantaged_wave": WX_DISADV_WAVE,
            "wind_severity":      WIND_SEVERITY,
            "latent_penalty":     WAVE_PENALTY,
            "players_penalized":  sum(1 for v in _wave_penalty_amounts if v < 0),
        },
    },
    "course_stats":         holes_data,
    "easiest_holes":        easiest,
    "hardest_holes":        hardest,
}

# ── Write ─────────────────────────────────────────────────────────────────────
if FINAL_BUILD:
    out_path = OUT / f"{EVENT_SLUG}_final_analysis.json"
    dep_path = DEP / "final_analysis.json"
else:
    out_path = OUT / f"{EVENT_SLUG}_r{ROUND}_analysis.json"
    dep_path = DEP / f"r{ROUND}_analysis.json"

import os as _os
if not _os.path.exists("C:/PGA_VenueDNA/architecture_blueprint.md"):
    print("[warn] System architecture blueprint missing.")

for path in [out_path, dep_path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote: {path}")

for path in [CUM_OUT, CUM_DEP]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cumulative_learning, f, indent=2)
    print(f"Wrote: {path}")

# ── Dry-run validation and cleanup ────────────────────────────────────────────
if DRY_RUN:
    _val_errors: list[str] = []

    try:
        with open(dep_path, encoding="utf-8") as _vf:
            _vdata = json.load(_vf)
        if _vdata.get("schema_version") != "1.1":
            _val_errors.append(f"{dep_path.name}: schema_version != '1.1'")
        _snap = _vdata.get("leaderboard_snapshot", [])
        if _snap:
            for _key in ("wave_draw", "wave_penalty"):
                if _key not in _snap[0]:
                    _val_errors.append(f"{dep_path.name}: missing snake_case key '{_key}'")
        if "total_r1" not in (_vdata.get("match_summary") or {}):
            _val_errors.append(f"{dep_path.name}: missing match_summary.total_r1")
        for _row in _snap[:10]:
            _w   = _row.get("live_win_pct")  or 0
            _t5  = _row.get("live_top5_pct") or 0
            _t10 = _row.get("live_top10_pct") or 0
            _t20 = _row.get("live_top20_pct") or 0
            if not (_t5 >= _w and _t10 >= _t5 and _t20 >= _t10):
                _val_errors.append(
                    f"Probability monotonicity violated — {_row.get('r1_name','?')}: "
                    f"win={_w} t5={_t5} t10={_t10} t20={_t20}"
                )
                break
    except Exception as _ve:
        _val_errors.append(f"Read error {dep_path.name}: {_ve}")

    try:
        with open(CUM_DEP, encoding="utf-8") as _vf:
            _cldata = json.load(_vf)
        if _cldata.get("schema_version") != "1.0":
            _val_errors.append("cumulative_learning.json: schema_version != '1.0'")
    except Exception as _ve:
        _val_errors.append(f"Read error cumulative_learning.json: {_ve}")

    if _val_errors:
        print("\n[dry-run] VALIDATION FAILED:")
        for _err in _val_errors:
            print(f"  FAIL: {_err}")
        raise SystemExit(1)

    print("\n[dry-run] VALIDATION PASSED - schema v1.1 | snake_case keys | probability monotonicity OK")
    _dep_dir = DEP.resolve()
    _cleanup_paths = [
        p for p in (list(_DRY_RUN_CREATED) + [out_path, CUM_OUT])
        if not Path(p).resolve().is_relative_to(_dep_dir)
    ]
    for _cp in _cleanup_paths:
        try:
            Path(_cp).unlink(missing_ok=True)
        except Exception:
            pass
    for _d in [ROUND_DIR, PAIRINGS.parent]:
        try:
            _d.rmdir()
        except Exception:
            pass
    print(f"[dry-run] Cleaned {len(_cleanup_paths)} test artifacts. Engine validated for R1 live ingestion.")
    raise SystemExit(0)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 62)
print(f"  {EVENT_NAME} — {round_label} ANALYSIS COMPLETE")
print(f"  Built: {BUILD_TS}")
print("=" * 62)
print(f"  Players matched  : {len(matched)}/{len(joined)} ({output['match_summary']['match_rate_pct']}%)")
print(f"  Spearman rho     : {spearman_rho}")
print(f"  Wave flagged     : {len(wave_risk_annotation)} players  |  avgs: {wave_avgs}")
print(f"  Enrichment       : {'ON (' + str(enrichment_summary['player_match_n']) + ' players)' if ci_loaded and enrichment_summary else 'OFF'}")
print()
print("  Trait audit (signal / source_confidence):")
for tk, v in trait_audit.items():
    upg = " [UPGRADED]" if v.get("signal_upgraded_by_enrichment") else ""
    bz  = " [BRIE-Z]" if v.get("brie_z",{}).get("available") else ""
    print(f"    {tk:<22} delta={str(v['trait_delta']):>6}  "
          f"sg_d={str(v['sg_delta']):>7}  => {v['signal']}{upg}{bz}")
print()
print(f"  Weekend risers   : {[r['r1_name'] for r in weekend_risers] or 'none'}")
print(f"  Slippage risk    : {[r['r1_name'] for r in slippage_risk] or 'none'}")
print()
out_stem = "final_analysis" if FINAL_BUILD else f"r{ROUND}_analysis"
print(f"  Files written:")
print(f"    output/{EVENT_SLUG}_{out_stem}.json")
print(f"    deploy/data/{out_stem}.json")
print(f"    deploy/data/cumulative_learning.json  (rounds: {rounds_present}, is_final={IS_FINAL})")
