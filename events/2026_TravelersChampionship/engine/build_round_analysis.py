"""
build_round_analysis.py — Generalized Round Analysis Builder
2026 Travelers Championship · VenueDNA Tier Engine

Supports rounds 1-4 (use 4 for Final). Produces rN_analysis.json and updates
cumulative_learning.json after each round.

Usage (run from any directory):
    python engine/build_round_analysis.py --round 2
    python engine/build_round_analysis.py --round 3
    python engine/build_round_analysis.py --round 4

Round N input files (place in output/roundN/ before running):
    roundN_leaderboard.csv              [REQUIRED]
    roundN_player_strokes_gained.csv    [REQUIRED]
    roundN_course_stats.csv             [optional — hole analysis]
    roundN_course_insights.csv          [optional — DataGolf proxy enrichment]

Pre-tournament files (already present from pipeline build):
    output/{slug}_trait_form_matrix.csv [REQUIRED]
    deploy/data/event_payload.json      [REQUIRED]

Outputs:
    output/{slug}_rN_analysis.json
    deploy/data/rN_analysis.json
    output/{slug}_cumulative_learning.json  (created on R1, extended on R2+)
    deploy/data/cumulative_learning.json    (mirror)

Note: Round 1 can also be built with the dedicated build_r1_analysis.py, which
      reads from the legacy "round1 player & course stats" folder. This script
      normalizes all round folders to output/roundN/.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

# Import shared helpers (same directory as this script)
sys.path.insert(0, str(Path(__file__).parent))
from round_helpers import load_csv, csv_columns, ascii_fold, fl_to_lf, avg, parse_float, parse_prox, parse_pct, parse_pos

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="VenueDNA round analysis builder")
parser.add_argument("--round", type=int, required=True, choices=[1, 2, 3, 4],
                    help="Round number (1-4; use 4 for Final)")
parser.add_argument("--check", action="store_true",
                    help="Validate input files only — print manifest and exit without building")
args = parser.parse_args()

ROUND      = args.round
IS_FINAL   = ROUND == 4
CHECK_ONLY = args.check
TODAY      = date.today().isoformat()
BUILD_TS   = datetime.now().replace(microsecond=0).isoformat()

# ── Event config (edit for each new event) ───────────────────────────────────
ROOT        = Path(__file__).parent.parent
OUT         = ROOT / "output"
DEP         = ROOT / "deploy" / "data"
EVENT_SLUG  = "2026_travelers_championship"
EVENT_NAME  = "2026 Travelers Championship"
COURSE_NAME = "TPC River Highlands"
PAR         = 70

# ── Venue trait config ────────────────────────────────────────────────────────
TRAIT_COLS = {
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
}
VENUE_WEIGHTS = {
    "app_wedge": 0.22, "app_100_150": 0.12, "app_150_200": 0.06,
    "ott_accuracy": 0.14, "ott_distance": 0.05, "putt_short_conv": 0.16,
    "putt_lag": 0.10, "arg_rough": 0.07, "arg_bunker": 0.05, "par5_scoring": 0.03,
}
SG_PROXY = {
    "app_wedge": "sg_app", "app_100_150": "sg_app", "app_150_200": "sg_app",
    "ott_accuracy": "sg_ott", "ott_distance": "sg_ott",
    "putt_short_conv": "sg_putt", "putt_lag": "sg_putt",
    "arg_rough": "sg_arg", "arg_bunker": "sg_arg",
    "par5_scoring": "sg_app",
}

# ── Enrichment config ─────────────────────────────────────────────────────────
TRAIT_SIGNAL_THRESHOLDS = {"strong": 6, "lean": 2, "neutral": -3}
CI_TRAIT_MAP = {
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
}
CI_SIG = {"fairway_prox": 20, "rough_prox": 50,  "gir": 3.0, "d_accuracy": 3.0, "scrambling": 10.0, "d_distance": 3.0}
CI_STR = {"fairway_prox": 36, "rough_prox": 100, "gir": 5.0, "d_accuracy": 5.0, "scrambling": 15.0, "d_distance": 6.0}
DIRECT_ENRICHMENT = {
    "ott_accuracy": "d_accuracy",
    "arg_rough":    "scrambling",
    "arg_bunker":   "scrambling",
}
UPGRADE_MAP = {"weak": "neutral", "not_testable": "neutral", "neutral": "mixed", "mixed": "validated"}

# ── Path resolution ───────────────────────────────────────────────────────────
# Try clean convention first (output/roundN/), then legacy R1 folder with spaces
round_dir_candidates = [
    OUT / f"round{ROUND}",
    OUT / f"round{ROUND} player & course stats",
]
ROUND_DIR = next((d for d in round_dir_candidates if d.exists()), None)

if ROUND_DIR is None:
    print(f"ERROR: Round {ROUND} data directory not found.")
    print(f"  Searched:")
    for c in round_dir_candidates:
        print(f"    {c}")
    print(f"  Create output/round{ROUND}/ and place round{ROUND}_*.csv files inside.")
    raise SystemExit(1)

print(f"Round {ROUND} data dir: {ROUND_DIR}")

# ── File existence validation ─────────────────────────────────────────────────
LB_PATH  = ROUND_DIR / f"round{ROUND}_leaderboard.csv"
SG_PATH  = ROUND_DIR / f"round{ROUND}_player_strokes_gained.csv"
CS_PATH  = ROUND_DIR / f"round{ROUND}_course_stats.csv"
CI_PATH  = ROUND_DIR / f"round{ROUND}_course_insights.csv"
TFM_PATH = OUT / f"{EVENT_SLUG}_trait_form_matrix.csv"
PAY_PATH = DEP / "event_payload.json"

MISSING_REQUIRED = False
for path, label in [(LB_PATH, f"round{ROUND}_leaderboard.csv"),
                    (SG_PATH, f"round{ROUND}_player_strokes_gained.csv"),
                    (TFM_PATH, f"{EVENT_SLUG}_trait_form_matrix.csv"),
                    (PAY_PATH, "event_payload.json")]:
    if not path.exists():
        print(f"ERROR: Required file missing — {label}")
        print(f"  Expected: {path}")
        MISSING_REQUIRED = True
if MISSING_REQUIRED:
    raise SystemExit(1)

cs_loaded = CS_PATH.exists()
ci_loaded = CI_PATH.exists()
if not cs_loaded:
    print(f"[info] round{ROUND}_course_stats.csv not found — hole-by-hole analysis skipped")
if not ci_loaded:
    print(f"[info] round{ROUND}_course_insights.csv not found — enrichment layer skipped")

if CHECK_ONLY:
    print()
    print(f"=== CHECK MODE — {EVENT_NAME} Round {ROUND} ===")
    print(f"Event path  : {ROOT}")
    print(f"Round dir   : {ROUND_DIR}")
    print(f"Build time  : {BUILD_TS}")
    print()

    def _check_file(path, label, required, expected_cols=None):
        if not path.exists():
            tag = "MISS" if required else " -- "
            print(f"  [{tag}] {label}")
            return False
        try:
            rows = load_csv(path)
            cols = list(rows[0].keys()) if rows else []
            n    = len(rows)
        except Exception as e:
            print(f"  [ERR]  {label} — could not read: {e}")
            return False
        print(f"  [ OK]  {label}  ({n} rows)")
        if expected_cols:
            found   = set(cols)
            missing = [c for c in expected_cols if c not in found]
            if missing:
                print(f"         [WARN] Missing expected columns: {missing}")
                print(f"         Found: {cols}")
            else:
                print(f"         Columns OK: {[c for c in expected_cols if c in found]}")
        return True

    LB_COLS  = ["PLAYER", "POS", "TOTAL", "Total Strokes"]
    SG_COLS  = ["Player", "SG-Off the Tee", "SG-Approach to Green", "SG-Putting", "SG-Total"]
    ok = True
    ok &= _check_file(LB_PATH,  f"round{ROUND}_leaderboard.csv",              required=True,  expected_cols=LB_COLS)
    ok &= _check_file(SG_PATH,  f"round{ROUND}_player_strokes_gained.csv",    required=True,  expected_cols=SG_COLS)
    ok &= _check_file(TFM_PATH, f"{EVENT_SLUG}_trait_form_matrix.csv",        required=True)
    ok &= _check_file(PAY_PATH, "event_payload.json (deploy/data/)",           required=True)
    _check_file(CS_PATH,  f"round{ROUND}_course_stats.csv",                   required=False)
    _check_file(CI_PATH,  f"round{ROUND}_course_insights.csv",                required=False)

    # Check SG ARG column variant
    if SG_PATH.exists():
        sg_cols = set(csv_columns(SG_PATH))
        if "SG- Around the Green" in sg_cols:
            print(f"\n  [info] SG ARG column: 'SG- Around the Green' (space variant)")
        elif "SG-Around the Green" in sg_cols:
            print(f"\n  [info] SG ARG column: 'SG-Around the Green' (no space)")
        else:
            print(f"\n  [WARN] Neither 'SG- Around the Green' nor 'SG-Around the Green' found — ARG will be null")

    print()
    if ok:
        print("PASS — all required files present. Run without --check to build.")
        raise SystemExit(0)
    else:
        print("FAIL — fix missing/invalid files before building.")
        raise SystemExit(1)

# ── Load files ────────────────────────────────────────────────────────────────
lb      = load_csv(LB_PATH)
sg      = load_csv(SG_PATH)
tfm     = load_csv(TFM_PATH)
cs      = load_csv(CS_PATH) if cs_loaded else []
ci_rows = load_csv(CI_PATH) if ci_loaded else []

with open(PAY_PATH, encoding="utf-8") as f:
    payload = json.load(f)

print(f"Loaded: {len(lb)} leaderboard rows, {len(sg)} SG rows, {len(tfm)} trait matrix rows")
if ci_loaded:
    print(f"Loaded: {len(ci_rows)} course insights rows")

# ── Post-load column and count validation ─────────────────────────────────────
if sg:
    sg_col_set = set(sg[0].keys())
    # Normalize uppercase PLAYER → Player for downstream lookups
    if "Player" not in sg_col_set and "PLAYER" in sg_col_set:
        for row in sg:
            row["Player"] = row.pop("PLAYER")
        sg_col_set = set(sg[0].keys())
        print("[info] Normalized SG column: PLAYER -> Player")
    if "SG- Around the Green" in sg_col_set:
        SG_ARG_COL = "SG- Around the Green"
    elif "SG-Around the Green" in sg_col_set:
        SG_ARG_COL = "SG-Around the Green"
    else:
        SG_ARG_COL = None
        print(f"[warn] SG ARG column not found — neither spelling present; ARG values will be null")
    for req_col in ["Player", "SG-Off the Tee", "SG-Approach to Green", "SG-Putting", "SG-Total"]:
        if req_col not in sg_col_set:
            print(f"[warn] SG file missing expected column: '{req_col}'")
else:
    SG_ARG_COL = None
    print("[warn] SG file loaded 0 rows — SG data will be absent for all players")

lb_names = {ascii_fold(r.get("PLAYER", "").strip()) for r in lb if r.get("PLAYER")}
sg_names = {ascii_fold(r.get("Player", "").strip()) for r in sg if r.get("Player")}
lb_not_in_sg = lb_names - sg_names
if len(lb_not_in_sg) > 3:
    print(f"[warn] {len(lb_not_in_sg)} leaderboard players not in SG file: {sorted(lb_not_in_sg)[:10]}")

# ── Pre-tournament model lookup ───────────────────────────────────────────────
pretournament = {}
for tier in [1, 2, 3, 4, 5]:
    for p in payload["tiers"].get(f"tier_{tier}", []):
        pretournament[ascii_fold(p["player_name"]).lower()] = p

trait_by_nk = {}
for row in tfm:
    nk     = row.get("name_key", "")
    traits = {}
    for tk, col in TRAIT_COLS.items():
        try:
            v = float(row.get(col, 0))
            traits[tk] = round(v, 1) if v > 0 else None
        except (TypeError, ValueError):
            traits[tk] = None
    trait_by_nk[nk] = traits

name_to_nk = {}
for row in tfm:
    pname = ascii_fold(row["player_display"]).lower()
    name_to_nk[pname] = row["name_key"]

def lookup_traits(name_lf):
    nk = name_to_nk.get(ascii_fold(name_lf).lower())
    return trait_by_nk.get(nk) if nk else None

sg_by_folded = {}
for row in sg:
    sg_by_folded[ascii_fold(row["Player"].strip())] = row

# ── Course insights lookup (DataGolf proxy) ───────────────────────────────────
ci_by_norm = {}
if ci_loaded:
    for row in ci_rows:
        full = (row.get("First Name", "") + " " + row.get("Last Name", "")).strip()
        nk   = fl_to_lf(ascii_fold(full)).lower()
        ci_by_norm[nk] = {
            "d_distance":   parse_float(row.get("D. Distance")),
            "d_accuracy":   parse_pct(row.get("D. Accuracy")),
            "gir":          parse_pct(row.get("GIR")),
            "fairway_prox": parse_prox(row.get("Fairway Prox", "")),
            "rough_prox":   parse_prox(row.get("Rough Prox", "")),
            "scrambling":   parse_pct(row.get("Scrambling")),
            "great_shots":  parse_float(row.get("Great Shots")),
            "poor_shots":   parse_float(row.get("Poor Shots")),
        }

# ── Join leaderboard to pre-tournament model ──────────────────────────────────
# Note: field names (r1_name, r1_pos, r1_score) are canonical in the round schema
# regardless of round number — this maintains compatibility with app.js.
joined      = []
unmatched   = []
seen_folded = set()
duplicates  = []

for row in lb:
    if not any(row.values()):
        continue  # skip empty rows
    r_name  = row.get("PLAYER", "").strip()
    if not r_name:
        continue
    folded  = ascii_fold(r_name)
    if folded in seen_folded:
        duplicates.append(r_name)
        continue
    seen_folded.add(folded)
    norm    = fl_to_lf(folded)
    pt      = pretournament.get(norm.lower())
    sg_row  = sg_by_folded.get(folded)

    pos_str = row.get("POS", "")
    pos_num = parse_pos(pos_str)
    score   = parse_float(row.get("TOTAL")) or 0

    sg_arg_val = parse_float(sg_row.get(SG_ARG_COL)) if (sg_row and SG_ARG_COL) else None

    record = {
        "r1_name":    r_name,
        "norm_name":  norm,
        "r1_pos":     pos_num,
        "r1_pos_str": pos_str,
        "r1_score":   score,
        "r1_strokes": int(row["Total Strokes"]) if row.get("Total Strokes") else 0,
        "matched":    pt is not None,
        "pt_rank":    pt["rank"]               if pt else None,
        "pt_tier":    pt["tier"]               if pt else None,
        "pt_vts":     float(pt["vts_final"])   if pt else None,
        "pt_win_pct": float(pt["win_pct"])     if pt else None,
        "pt_top10":   float(pt["top10_pct"])   if pt else None,
        "pt_top20":   float(pt.get("top20_pct", 0)) if pt else None,
        "pt_flags":   (pt.get("anti_pattern_flags") or "") if pt else "",
        "pt_driver":  pt.get("primary_driver", "") if pt else "",
        "sg_ott":     parse_float(sg_row.get("SG-Off the Tee"))       if sg_row else None,
        "sg_app":     parse_float(sg_row.get("SG-Approach to Green")) if sg_row else None,
        "sg_arg":     sg_arg_val,
        "sg_putt":    parse_float(sg_row.get("SG-Putting"))           if sg_row else None,
        "sg_tot":     parse_float(sg_row.get("SG-Total"))             if sg_row else None,
        "traits":     lookup_traits(norm),
        "rank_delta": (pt["rank"] - pos_num) if pt else 0,
    }
    joined.append(record)
    if not pt:
        unmatched.append(r_name)

for r in joined:
    r["ci"] = ci_by_norm.get(r["norm_name"].lower())

if duplicates:
    print(f"[warn] Duplicate leaderboard rows skipped ({len(duplicates)}): {duplicates}")

matched = [r for r in joined if r["matched"]]
print(f"Matched {len(matched)}/{len(joined)} players to pre-tournament model")
if unmatched:
    unmatched_with_pos = [(r["r1_name"], r.get("r1_pos_str", "?")) for r in joined if not r["matched"]]
    for name, pos in unmatched_with_pos:
        print(f"  [unmatched] {name} (pos {pos})")

# ── Model performance ─────────────────────────────────────────────────────────
def group_stats(group):
    return {
        "n":            len(group),
        "avg_r1_pos":   avg([r["r1_pos"]   for r in group]),
        "avg_r1_score": avg([r["r1_score"] for r in group]),
        "in_r1_top10":  sum(1 for r in group if r["r1_pos"] <= 10),
        "in_r1_top20":  sum(1 for r in group if r["r1_pos"] <= 20),
        "in_r1_top30":  sum(1 for r in group if r["r1_pos"] <= 30),
    }

pt_top10 = [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 10]
pt_top20 = [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 20]
tier1    = [r for r in matched if r["pt_tier"] == 1]
tier2    = [r for r in matched if r["pt_tier"] == 2]
tier1_2  = [r for r in matched if r["pt_tier"] in (1, 2)]

model_perf = {
    "pt_top10":  group_stats(pt_top10),
    "pt_top20":  group_stats(pt_top20),
    "tier1":     group_stats(tier1),
    "tier2":     group_stats(tier2),
    "tier1_2":   group_stats(tier1_2),
    "all_field": group_stats(joined),
}

pairs = [(r["pt_rank"], r["r1_pos"]) for r in matched if r["pt_rank"]]
n  = len(pairs)
d2 = sum((a - b) ** 2 for a, b in pairs)
spearman_rho = round(1 - 6 * d2 / (n * (n ** 2 - 1)), 3) if n > 2 else 0.0

# ── Trait audit ───────────────────────────────────────────────────────────────
top10_group = [r for r in joined if r["r1_pos"] <= 10]
top18_group = [r for r in joined if r["r1_pos"] <= 18]

def sg_summary(group):
    return {
        "sg_ott":  avg([r["sg_ott"]  for r in group]),
        "sg_app":  avg([r["sg_app"]  for r in group]),
        "sg_arg":  avg([r["sg_arg"]  for r in group]),
        "sg_putt": avg([r["sg_putt"] for r in group]),
        "sg_tot":  avg([r["sg_tot"]  for r in group]),
    }

sg_leaders_top10 = sg_summary(top10_group)
sg_leaders_top18 = sg_summary(top18_group)

top10_with_traits = [r for r in top10_group if r["matched"] and r["traits"]]
all_with_traits   = [r for r in matched if r["traits"]]

trait_audit = {}
for tk in TRAIT_COLS:
    w    = VENUE_WEIGHTS[tk]
    t10v = [r["traits"][tk] for r in top10_with_traits if r["traits"] and r["traits"].get(tk) is not None]
    fv   = [r["traits"][tk] for r in all_with_traits   if r["traits"] and r["traits"].get(tk) is not None]
    t10a = avg(t10v)
    fa   = avg(fv)
    delta = round(t10a - fa, 1) if t10a is not None and fa is not None else None

    sg_key   = SG_PROXY.get(tk)
    sg_t10   = avg([r[sg_key] for r in top10_group if r.get(sg_key) is not None]) if sg_key else None
    sg_all   = avg([r[sg_key] for r in joined      if r.get(sg_key) is not None]) if sg_key else None
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

# ── Course insights enrichment ────────────────────────────────────────────────
top10_ci = [r for r in top10_group if r.get("ci")]
all_ci   = [r for r in joined      if r.get("ci")]

def ci_avg_field(field, group):
    vals = [r["ci"][field] for r in group if r.get("ci") and r["ci"].get(field) is not None]
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
    if delta >= CI_STR.get(field, 5.0) and base_sig in ("mixed", "neutral", "weak", "not_testable"):
        return "upgraded"
    return "confirmed"

def _make_ci_note(field, direction, t10v, fv, d):
    units = {"fairway_prox": "in", "rough_prox": "in", "gir": "%",
             "d_accuracy": "%", "scrambling": "%", "d_distance": "yds"}
    u = units.get(field, "")
    if t10v is None or fv is None:
        return f"{field}: n/a"
    if direction == "lower_better":
        return f"{field}: top10={round(t10v,1)}{u} vs field={round(fv,1)}{u} (closer by {round(d,1)}{u})"
    return f"{field}: top10={round(t10v,1)}{u} vs field={round(fv,1)}{u} ({'+' if d >= 0 else ''}{round(d,1)}{u})"

if ci_loaded:
    for tk, mapping in CI_TRAIT_MAP.items():
        primary   = mapping["primary"]
        direction = mapping["direction"]
        secondary = mapping["secondary"]

        if primary is None:
            trait_audit[tk]["enrichment"] = {"available": False, "reason": "no_direct_proxy"}
            continue

        t10_pri  = ci_avg_field(primary, top10_ci)
        f_pri    = ci_avg_field(primary, all_ci)
        delta_p  = enr_delta(primary, direction, t10_pri, f_pri)
        base_sig = trait_audit[tk]["signal"]
        e_sig    = enr_signal(primary, delta_p, base_sig)

        t10_sec  = ci_avg_field(secondary, top10_ci) if secondary else None
        f_sec    = ci_avg_field(secondary, all_ci)   if secondary else None
        sec_dir  = "lower_better" if secondary in ("fairway_prox", "rough_prox") else "higher_better"
        sec_d    = enr_delta(secondary, sec_dir, t10_sec, f_sec) if secondary else None

        notes = [_make_ci_note(primary, direction, t10_pri, f_pri, delta_p or 0)]
        if secondary and t10_sec is not None:
            notes.append(_make_ci_note(secondary, sec_dir, t10_sec, f_sec, sec_d or 0))

        upgraded_sig = UPGRADE_MAP.get(base_sig, base_sig) if e_sig == "upgraded" else base_sig

        trait_audit[tk]["enrichment"] = {
            "available":         True,
            "source":            f"round{ROUND}_course_insights.csv (DataGolf proxy — not PGAT official SG)",
            "proxy_fields":      [primary] + ([secondary] if secondary else []),
            "primary_field":     primary,
            "direction":         direction,
            "top10_primary":     t10_pri,
            "field_primary":     f_pri,
            "delta_primary":     delta_p,
            "top10_secondary":   t10_sec,
            "field_secondary":   f_sec,
            "delta_secondary":   sec_d,
            "enrichment_signal": e_sig,
            "upgraded_signal":   upgraded_sig,
            "enrichment_note":   " | ".join(notes),
            "n_top10_ci":        len(top10_ci),
            "n_field_ci":        len(all_ci),
        }
        if e_sig == "upgraded":
            trait_audit[tk]["signal"] = upgraded_sig
            trait_audit[tk]["signal_upgraded_by_enrichment"] = True

    ci_scramb_t10 = ci_avg_field("scrambling",   top10_ci)
    ci_scramb_all = ci_avg_field("scrambling",   all_ci)
    ci_acc_t10    = ci_avg_field("d_accuracy",   top10_ci)
    ci_acc_all    = ci_avg_field("d_accuracy",   all_ci)
    ci_fp_t10     = ci_avg_field("fairway_prox", top10_ci)
    ci_fp_all     = ci_avg_field("fairway_prox", all_ci)
    ci_dd_t10     = ci_avg_field("d_distance",   top10_ci)
    ci_dd_all     = ci_avg_field("d_distance",   all_ci)

    upgraded_traits  = [tk for tk in trait_audit if trait_audit[tk].get("signal_upgraded_by_enrichment")]
    confirmed_traits = [tk for tk in trait_audit
                        if trait_audit[tk].get("enrichment", {}).get("enrichment_signal") == "confirmed"]
    enrichment_summary = {
        "source":           f"round{ROUND}_course_insights.csv (DataGolf proxy — not PGAT official SG)",
        "player_match_n":   len(all_ci),
        "player_total":     len(joined),
        "traits_upgraded":  upgraded_traits,
        "traits_confirmed": confirmed_traits,
        "key_findings": [
            f"Scrambling: top10={round(ci_scramb_t10 or 0,1)}% vs field={round(ci_scramb_all or 0,1)}% ({round((ci_scramb_t10 or 0)-(ci_scramb_all or 0),1):+}pp) -> ARG enrichment",
            f"D.Accuracy: top10={round(ci_acc_t10 or 0,1)}% vs field={round(ci_acc_all or 0,1)}% ({round((ci_acc_t10 or 0)-(ci_acc_all or 0),1):+}pp) -> OTT_Acc enrichment",
            f"Fairway Prox: top10={round((ci_fp_t10 or 0)/12,1)}ft vs field={round((ci_fp_all or 0)/12,1)}ft -> APP_Wedge enrichment",
            f"D.Distance: top10={round(ci_dd_t10 or 0,1)}yds vs field={round(ci_dd_all or 0,1)}yds ({round((ci_dd_t10 or 0)-(ci_dd_all or 0),1):+}yds) -> OTT_Dist enrichment",
        ],
        "dg_note": "DataGolf SG correlated (~0.05-0.30 diff) but distinct from PGAT SG. Proxy layer only.",
    }
else:
    for tk in TRAIT_COLS:
        trait_audit[tk]["enrichment"] = {
            "available": False,
            "reason": f"round{ROUND}_course_insights.csv not present",
        }
    enrichment_summary = None

# ── Source confidence classification ──────────────────────────────────────────
def compute_source_confidence(tk, signal, enrichment):
    enr = enrichment if isinstance(enrichment, dict) else {}
    if not enr.get("available"):
        if signal == "validated":           return "proxy-confirmed"
        if signal in ("mixed", "neutral"):  return "weak-proxy"
        return "not-testable"
    e_sig = enr.get("enrichment_signal", "")
    pf    = enr.get("primary_field", "")
    if tk in DIRECT_ENRICHMENT and DIRECT_ENRICHMENT[tk] == pf and e_sig in ("confirmed", "upgraded"):
        return "direct"
    if signal == "validated" and e_sig in ("confirmed", "upgraded"):
        return "proxy-confirmed"
    if signal in ("mixed", "neutral") or e_sig == "neutral":
        return "weak-proxy"
    return "not-testable"

for tk in trait_audit:
    trait_audit[tk]["source_confidence"] = compute_source_confidence(
        tk, trait_audit[tk]["signal"], trait_audit[tk].get("enrichment")
    )

# ── Rank deltas: risers and slippage ─────────────────────────────────────────
by_delta = sorted([r for r in matched if r["pt_rank"]], key=lambda x: -x["rank_delta"])

def player_summary(r):
    return {
        "r1_name":    r["r1_name"],
        "norm_name":  r["norm_name"],
        "r1_pos":     r["r1_pos"],
        "r1_pos_str": r["r1_pos_str"],
        "r1_score":   r["r1_score"],
        "pt_rank":    r["pt_rank"],
        "pt_tier":    r["pt_tier"],
        "pt_vts":     r["pt_vts"],
        "pt_flags":   r["pt_flags"],
        "pt_driver":  r["pt_driver"],
        "rank_delta": r["rank_delta"],
        "sg_ott":     r["sg_ott"],
        "sg_app":     r["sg_app"],
        "sg_arg":     r["sg_arg"],
        "sg_putt":    r["sg_putt"],
        "sg_tot":     r["sg_tot"],
    }

risers = [player_summary(r) for r in by_delta[:12]]
slippage = [player_summary(r) for r in sorted(
    [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 35],
    key=lambda x: x["rank_delta"]
)[:10]]

def riser_thesis_score(r):
    score = 0
    if r["sg_app"]  and r["sg_app"]  > 0.5: score += 2
    if r["sg_arg"]  and r["sg_arg"]  > 0.3: score += 1
    if r["sg_putt"] and r["sg_putt"] > 0.3: score += 1
    return score

def _make_thesis_note(r):
    notes = []
    if r["sg_app"] and r["sg_app"] > 0.8:   notes.append(f"approach elite ({r['sg_app']:+.2f})")
    elif r["sg_app"] and r["sg_app"] > 0.4:  notes.append(f"approach solid ({r['sg_app']:+.2f})")
    if r["sg_arg"] and r["sg_arg"] > 0.5:    notes.append(f"scrambling strong ({r['sg_arg']:+.2f})")
    if r["sg_putt"] and r["sg_putt"] > 0.8:  notes.append(f"putting hot ({r['sg_putt']:+.2f})")
    if not notes:                             notes.append("score above expectation")
    if r.get("pt_driver"):                    notes.append(f"pre-event driver: {r['pt_driver']}")
    return " | ".join(notes)

weekend_risers = []
for r in by_delta[:20]:
    ts = riser_thesis_score(r)
    if ts >= 2 and r["r1_score"] <= -3:
        rec = player_summary(r)
        rec["thesis_score"] = ts
        rec["thesis_note"]  = _make_thesis_note(r)
        weekend_risers.append(rec)

slippage_risk = []
for r in matched:
    if r["r1_pos"] > 20:
        continue
    risks   = []
    sg_putt = r.get("sg_putt") or 0
    sg_app  = r.get("sg_app")  or 0
    pt_rank = r.get("pt_rank") or 99
    if sg_putt > 2.0 and sg_app < 0.3:
        risks.append(
            f"putting-driven round ({sg_putt:+.2f} putting vs {sg_app:+.2f} APP) — regression likely"
        )
    if pt_rank > 55 and r["r1_pos"] <= 12 and sg_app < 0.5:
        risks.append(f"no pre-tournament basis (model rank {pt_rank}), heat-check round")
    if risks:
        rec = player_summary(r)
        rec["risk_flags"] = risks
        slippage_risk.append(rec)

slippage_risk.sort(key=lambda x: x["r1_pos"])

# ── Live lean notes ───────────────────────────────────────────────────────────
slippage_names = {r["r1_name"] for r in slippage_risk}
sustainable_leaders = [
    r for r in joined
    if r["r1_pos"] <= 6
    and r["r1_name"] not in slippage_names
    and (r.get("sg_app") or 0) > 0.5
]

watch_next = [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str", ""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      " | ".join(r.get("risk_flags", [])),
        "flag_type": "slippage",
    }
    for r in slippage_risk[:5]
] + [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str", ""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      f"approach-backed leader (APP {(r.get('sg_app') or 0):+.2f}) — not flagged, sustainable position",
        "flag_type": "sustainable",
    }
    for r in sustainable_leaders[:2]
]

putt_outliers = sorted(
    [r for r in slippage_risk if (r.get("sg_putt") or 0) > 2.0],
    key=lambda x: -(x.get("sg_putt") or 0)
)

lean_up_traits = [
    {
        "trait":      tk,
        "delta":      trait_audit[tk].get("trait_delta"),
        "confidence": trait_audit[tk].get("source_confidence", "proxy-confirmed"),
        "enr_signal": (trait_audit[tk].get("enrichment") or {}).get("enrichment_signal"),
    }
    for tk in TRAIT_COLS if trait_audit[tk]["signal"] == "validated"
]
lean_down_traits = [
    {"trait": tk, "delta": trait_audit[tk].get("trait_delta")}
    for tk in TRAIT_COLS if trait_audit[tk]["signal"] in ("weak", "not_testable")
]

rho_note = (
    f"R{ROUND} rank correlation rho={spearman_rho} — tournament complete."
    if IS_FINAL
    else f"R{ROUND} rank correlation rho={spearman_rho} — model-field separation expected to sharpen by R{ROUND+1}."
)

live_lean_notes = {
    "round":            ROUND,
    "next_round":       ROUND + 1 if not IS_FINAL else None,
    "lean_up_traits":   lean_up_traits,
    "lean_down_traits": lean_down_traits,
    "putt_caution":     len(putt_outliers) > 0,
    "putt_outliers":    [
        {"player": r["r1_name"], "sg_putt": r.get("sg_putt"), "sg_app": r.get("sg_app")}
        for r in putt_outliers[:3]
    ],
    "watch_next_round": watch_next,
    "rho_note":         rho_note,
}

# ── Cumulative learning (create on R1, extend on R2+) ─────────────────────────
CUM_OUT = OUT / f"{EVENT_SLUG}_cumulative_learning.json"
CUM_DEP = DEP / "cumulative_learning.json"

this_round_entry = {
    "round":        ROUND,
    "generated_at": TODAY,
    "spearman_rho": spearman_rho,
    "trait_signals": {
        tk: {
            "signal":            v["signal"],
            "source_confidence": v.get("source_confidence", "not-testable"),
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
    "risers":   [r["r1_name"] for r in weekend_risers],
    "slippage": [r["r1_name"] for r in slippage_risk],
}

if CUM_OUT.exists():
    with open(CUM_OUT, encoding="utf-8") as f:
        cumulative_learning = json.load(f)
    print(f"Extending cumulative learning from R{cumulative_learning.get('rounds_completed', '?')}")
else:
    cumulative_learning = {
        "schema_version":    "1.0",
        "event_slug":        EVENT_SLUG,
        "created_at":        TODAY,
        "per_round":         {},
        "cumulative_signals": {
            tk: {
                "rounds_observed":      [],
                "signal_history":       [],
                "confidence_history":   [],
                "delta_history":        [],
                "consensus":            None,
                "consensus_confidence": None,
            }
            for tk in TRAIT_COLS
        },
    }

cumulative_learning["last_updated"]     = TODAY
cumulative_learning["updated_at"]       = BUILD_TS
cumulative_learning["rounds_completed"] = ROUND
cumulative_learning["per_round"][str(ROUND)] = this_round_entry

# Keep rounds_present as a sorted deduplicated list so callers know what's in the file
rounds_present = sorted(set(cumulative_learning.get("rounds_present", []) + [ROUND]))
cumulative_learning["rounds_present"] = rounds_present

for tk, v in trait_audit.items():
    cs_entry = cumulative_learning["cumulative_signals"].setdefault(tk, {
        "rounds_observed": [], "signal_history": [], "confidence_history": [],
        "delta_history": [], "consensus": None, "consensus_confidence": None,
    })
    observed = cs_entry.get("rounds_observed", [])
    if ROUND not in observed:
        cs_entry.setdefault("rounds_observed",    []).append(ROUND)
        cs_entry.setdefault("signal_history",     []).append(v["signal"])
        cs_entry.setdefault("confidence_history", []).append(v.get("source_confidence", "not-testable"))
        cs_entry.setdefault("delta_history",      []).append(v.get("trait_delta"))
    else:
        idx = observed.index(ROUND)
        cs_entry["signal_history"][idx]     = v["signal"]
        cs_entry["confidence_history"][idx] = v.get("source_confidence", "not-testable")
        cs_entry["delta_history"][idx]      = v.get("trait_delta")
    cs_entry["consensus"]            = cs_entry["signal_history"][-1]
    cs_entry["consensus_confidence"] = cs_entry["confidence_history"][-1]

# ── Course stats (hole-by-hole) ───────────────────────────────────────────────
holes_data = []
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

easiest = sorted(holes_data, key=lambda x: -x["birdies"])[:5]   if holes_data else []
hardest = sorted(holes_data, key=lambda x: -(x["bogeys"] + x["dbl"]))[:3] if holes_data else []

# ── Leaderboard snapshot ──────────────────────────────────────────────────────
leaderboard_snapshot = [
    {
        "r1_name":    r["r1_name"],
        "r1_pos":     r["r1_pos"],
        "r1_pos_str": r["r1_pos_str"],
        "r1_score":   r["r1_score"],
        "pt_rank":    r["pt_rank"],
        "pt_tier":    r["pt_tier"],
        "pt_vts":     r["pt_vts"],
        "sg_app":     r["sg_app"],
        "sg_putt":    r["sg_putt"],
        "sg_ott":     r["sg_ott"],
        "sg_arg":     r["sg_arg"],
        "sg_tot":     r["sg_tot"],
    }
    for r in joined
]

def _sg_full_field(key):
    vals = [p.get(key) for p in leaderboard_snapshot if p.get(key) is not None]
    if not vals:
        return None
    v = round(sum(vals) / len(vals), 3)
    return 0.0 if v == 0 else v  # normalize -0.0 → 0.0

sg_field_all = {k: _sg_full_field(k) for k in ("sg_ott", "sg_app", "sg_arg", "sg_putt", "sg_tot")}

sg_dimension_leaders = {
    "sg_app":  sorted([r for r in joined if r["sg_app"]  is not None], key=lambda x: -x["sg_app"])[:5],
    "sg_putt": sorted([r for r in joined if r["sg_putt"] is not None], key=lambda x: -x["sg_putt"])[:5],
    "sg_ott":  sorted([r for r in joined if r["sg_ott"]  is not None], key=lambda x: -x["sg_ott"])[:5],
    "sg_arg":  sorted([r for r in joined if r["sg_arg"]  is not None], key=lambda x: -x["sg_arg"])[:5],
}
dimension_leaders_clean = {
    dim: [
        {"r1_name": r["r1_name"], "r1_pos": r["r1_pos_str"], "value": r[dim], "r1_score": r["r1_score"]}
        for r in group
    ]
    for dim, group in sg_dimension_leaders.items()
}

# ── Assemble output ───────────────────────────────────────────────────────────
round_sources = [
    f"round{ROUND}_leaderboard.csv",
    f"round{ROUND}_player_strokes_gained.csv",
    f"{EVENT_SLUG}_trait_form_matrix.csv",
    "deploy/data/event_payload.json",
] + ([f"round{ROUND}_course_stats.csv"]     if cs_loaded else []) \
  + ([f"round{ROUND}_course_insights.csv"]  if ci_loaded else [])

output = {
    "schema_version":         "1.1",
    "generated_at":           TODAY,
    "build_timestamp":        BUILD_TS,
    "round":                  ROUND,
    "enrichment_used":        ci_loaded,
    "event_slug":             EVENT_SLUG,
    "metadata": {
        "event_name":   EVENT_NAME,
        "course_name":  COURSE_NAME,
        "par":          PAR,
        "round_label":  f"Round {ROUND}" if not IS_FINAL else "Final Round",
        "is_final":     IS_FINAL,
    },
    "round_sources":          round_sources,
    "course_insights_loaded": ci_loaded,
    "enrichment_summary":     enrichment_summary,
    "live_lean_notes":        live_lean_notes,
    "match_summary": {
        "matched":        len(matched),
        "total_r1":       len(joined),
        "unmatched":      unmatched,
        "match_rate_pct": round(len(matched) / len(joined) * 100, 1) if joined else 0,
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
    "leaderboard_snapshot": leaderboard_snapshot,
    "dimension_leaders":    dimension_leaders_clean,
    "course_stats":         holes_data,
    "easiest_holes":        easiest,
    "hardest_holes":        hardest,
}

# ── Write outputs ─────────────────────────────────────────────────────────────
out_path = OUT / f"{EVENT_SLUG}_r{ROUND}_analysis.json"
dep_path = DEP / f"r{ROUND}_analysis.json"

for path in [out_path, dep_path]:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote: {path}")

for path in [CUM_OUT, CUM_DEP]:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cumulative_learning, f, indent=2)
    print(f"Wrote: {path}")

# ── Final build summary ───────────────────────────────────────────────────────
round_label_final = "Final Round" if IS_FINAL else f"Round {ROUND}"
match_rate = round(len(matched) / len(joined) * 100, 1) if joined else 0
print()
print(f"{'='*60}")
print(f"  {EVENT_NAME} — {round_label_final} ANALYSIS COMPLETE")
print(f"  Built: {BUILD_TS}")
print(f"{'='*60}")
print(f"  Players matched : {len(matched)}/{len(joined)} ({match_rate}%)")
if unmatched:
    for r in joined:
        if not r["matched"]:
            print(f"    [unmatched] {r['r1_name']} (pos {r.get('r1_pos_str', '?')})")
if duplicates:
    print(f"  Duplicates skipped : {len(duplicates)} ({duplicates})")
print(f"  Spearman rho    : {spearman_rho}")
print(f"  PT Top10 -> top10: {model_perf['pt_top10']['in_r1_top10']}/10  "
      f"PT Top10 -> top20: {model_perf['pt_top10']['in_r1_top20']}/10")
print(f"  Enrichment      : {'ON (' + str(enrichment_summary['player_match_n']) + ' players)' if ci_loaded and enrichment_summary else 'OFF'}")
print()
print("  Trait audit:")
for tk, v in trait_audit.items():
    upg = " [UPGRADED]" if v.get("signal_upgraded_by_enrichment") else ""
    print(f"    {tk:<22} Δ={str(v['trait_delta']):>6}  sg_Δ={str(v['sg_delta']):>7}  → {v['signal']}{upg}")
print()
print(f"  Weekend risers  : {[r['r1_name'] for r in weekend_risers] or 'none'}")
print(f"  Slippage risk   : {[r['r1_name'] for r in slippage_risk] or 'none'}")
print()
print("  Files written:")
print(f"    output/{EVENT_SLUG}_r{ROUND}_analysis.json")
print(f"    deploy/data/r{ROUND}_analysis.json")
print(f"    deploy/data/cumulative_learning.json  (rounds present: {rounds_present})")
print()
print(f"  -> Reload dashboard. Round {ROUND} tab should show LIVE badge.")
print(f"{'='*60}")
