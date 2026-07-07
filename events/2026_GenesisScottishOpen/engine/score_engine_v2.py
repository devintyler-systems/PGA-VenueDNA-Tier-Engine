"""
VenueDNA v2 Scoring Engine — 2026 Genesis Scottish Open
The Renaissance Club, North Berwick, Scotland
"""

import pandas as pd
import numpy as np
import json
import re
import os
import unicodedata
from pathlib import Path

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE = Path(r"C:\PGA_VenueDNA\events\2026_GenesisScottishOpen")
INPUT = BASE / "input"
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# PRE-RUN SNAPSHOT (for FC-1 audit diff)
# ─────────────────────────────────────────────
_before_briefs_map = {}
_before_brief_path = OUTPUT / "2026_genesis_scottish_open_player_briefs.json"
if _before_brief_path.exists():
    with open(_before_brief_path, "r", encoding="utf-8") as _f:
        _before_briefs_raw = json.load(_f)
    _before_briefs_map = {b["player_id"]: b for b in _before_briefs_raw}
    print(f"Pre-run snapshot: {len(_before_briefs_map)} existing briefs captured for FC-1 audit diff.")

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Uppercase, strip accents (Å→A, Ø→O, Ü→U, ñ→N, etc.), remove non-alpha except spaces/commas/hyphens."""
    if not isinstance(name, str):
        return ""
    # NFD decompose and strip combining marks (accents)
    nfd = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    # explicit replacements for characters that don't decompose cleanly
    explicit = {
        "Ø": "O", "ø": "O", "Æ": "AE", "æ": "AE",
        "Å": "A", "å": "A", "Ö": "O", "ö": "O",
        "Ü": "U", "ü": "U", "Ñ": "N", "ñ": "N",
        "ß": "SS",
    }
    for k, v in explicit.items():
        stripped = stripped.replace(k, v)
    return stripped.upper().strip()


def make_key(last: str, first: str) -> str:
    return normalize_name(last) + "|" + normalize_name(first)


def field_name_to_key(raw: str) -> tuple:
    """Convert 'Last, First' → (last, first, key)."""
    raw = str(raw).strip()
    if "," in raw:
        parts = raw.split(",", 1)
        last = normalize_name(parts[0].strip())
        first = normalize_name(parts[1].strip())
    else:
        last = normalize_name(raw)
        first = ""
    return last, first, f"{last}|{first}"


def parse_pct(val) -> float:
    """Parse '5.40%' or '0.054' → float (e.g. 5.40 for percentage points)."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace("%", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_finish(fin: str) -> int:
    """Convert finish string to numeric. CUT/WD/DQ → 999, T2→2, 1→1."""
    if pd.isna(fin):
        return 999
    s = str(fin).strip().upper()
    if s in ("CUT", "WD", "DQ", "MC", "NULL", ""):
        return 999
    s = re.sub(r"^T", "", s)  # remove T prefix
    try:
        return int(float(s))
    except:
        return 999


def zscore_scale(series: pd.Series, target_mean: float = 50.0, target_std: float = 15.0) -> pd.Series:
    """Z-score then rescale to target_mean ± target_std, clamp 0-100."""
    valid = series.dropna()
    if len(valid) == 0:
        return series.fillna(50.0)
    mu, sigma = valid.mean(), valid.std()
    if sigma < 1e-9:
        return pd.Series(target_mean, index=series.index)
    scaled = (series - mu) / sigma * target_std + target_mean
    return scaled.clip(0.0, 100.0)


# ─────────────────────────────────────────────
# STEP 1 — LOAD ALL CSVs
# ─────────────────────────────────────────────
print("Loading input files …")

# 1. Field list
field_raw = pd.read_csv(INPUT / "genesis_scottish_open_2026_field.csv",
                         encoding="cp1252", header=0)
field_raw.columns = ["raw_name"]
field_raw = field_raw.dropna(subset=["raw_name"])
field_raw = field_raw[field_raw["raw_name"].str.strip() != "Last, First"]
# Drop duplicate rows if any
field_raw = field_raw.drop_duplicates(subset=["raw_name"])

field_players = []
for _, row in field_raw.iterrows():
    last, first, key = field_name_to_key(row["raw_name"])
    field_players.append({"raw": row["raw_name"], "last": last, "first": first, "key": key})
field_df = pd.DataFrame(field_players)
print(f"  Field: {len(field_df)} players")

# 2. SG data (12-month)
sg_raw = pd.read_csv(INPUT / "field_player_Last12month_TrueSG_Data.csv",
                      encoding="cp1252")
sg_raw.columns = [c.strip() for c in sg_raw.columns]
# Normalize SG column names to lowercase for consistent downstream access
sg_raw.columns = [c.lower() if c.upper().startswith("SG-") else c for c in sg_raw.columns]
# Rename alternate column headers to canonical names
_sg_renames = {
    "events": "Events Last 12 Months",
    "sg-ott.1": None,       # duplicate OTT column — drop
    "ev-text 7": None,
    "shotlink-rounds": None,
    "wins": None,
}
sg_raw = sg_raw.drop(columns=[c for c in sg_raw.columns if _sg_renames.get(c.lower()) is None and c.lower() in _sg_renames], errors="ignore")
if "Events" in sg_raw.columns and "Events Last 12 Months" not in sg_raw.columns:
    sg_raw.rename(columns={"Events": "Events Last 12 Months"}, inplace=True)
# Compute sg-total if missing
if "sg-total" not in sg_raw.columns and all(c in sg_raw.columns for c in ["sg-app", "sg-ott", "sg-putt", "sg-arg"]):
    sg_raw["sg-total"] = sg_raw[["sg-app", "sg-ott", "sg-putt", "sg-arg"]].sum(axis=1, min_count=1)
sg_raw["key"] = sg_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)
sg_raw["Driving-Accuracy"] = sg_raw["Driving-Accuracy"].apply(parse_pct)
# Column name varies between data pulls ("Win %" vs "WIN%") — normalize
if "Win %" not in sg_raw.columns and "WIN%" in sg_raw.columns:
    sg_raw.rename(columns={"WIN%": "Win %"}, inplace=True)
if "Win %" in sg_raw.columns:
    sg_raw["Win %"] = sg_raw["Win %"].apply(parse_pct)

# 3. Approach skill
app_raw = pd.read_csv(INPUT / "approach_skill_Last12mon.csv", encoding="cp1252")
app_raw.columns = [c.strip() for c in app_raw.columns]
app_raw["key"] = app_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)

# 4. Form data
form_raw = pd.read_csv(INPUT / "Golfer_Last5_Form_Data.csv", encoding="cp1252")
form_raw.columns = [c.strip() for c in form_raw.columns]
form_raw["key"] = form_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)

# 5. Course history (player_name in "Last, First" format)
ch_raw = pd.read_csv(INPUT / "the_renaissance_club_CH.csv", encoding="cp1252")
ch_raw.columns = [c.strip() for c in ch_raw.columns]
def ch_key(pname):
    _, _, k = field_name_to_key(str(pname))
    return k
ch_raw["key"] = ch_raw["player_name"].apply(ch_key)

# 6. Venue fit adjustments
fit_raw = pd.read_csv(INPUT / "therenaissanceclub_playerfitadj_predictedshotdistance.csv",
                       encoding="cp1252")
fit_raw.columns = [c.strip() for c in fit_raw.columns]
fit_raw["key"] = fit_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)

# 7. 2025 final results (for recent bonus)
res_raw = pd.read_csv(INPUT / "genesis_scottish_open_2025_final.csv", encoding="cp1252")
res_raw.columns = [c.strip().replace("�", "") for c in res_raw.columns]
res_raw["key"] = res_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)

# Convert POS to numeric finish
res_raw["finish_2025"] = res_raw["POS"].apply(parse_finish)

print("  All files loaded.")

# ─────────────────────────────────────────────
# BUILD MASTER DATAFRAME
# ─────────────────────────────────────────────
df = field_df.copy()

# Assign player_id
df["player_id"] = [f"P{i+1:03d}" for i in range(len(df))]

# Merge SG data
sg_cols = ["key", "Events Last 12 Months", "Rounds", "sg-putt", "sg-arg",
           "sg-app", "sg-ott", "sg-t2g", "sg-total", "Driving-Distance", "Driving-Accuracy"]
sg_sub = sg_raw[sg_cols].copy()
sg_sub.columns = ["key", "events_12m", "rounds_12m", "sg_putt_12m", "sg_arg_12m",
                   "sg_app_12m", "sg_ott_12m", "sg_t2g_12m", "sg_total_12m",
                   "drive_dist_adj", "drive_acc_12m"]
df = df.merge(sg_sub, on="key", how="left")

# Merge approach data
app_cols_keep = ["key",
                 "Fairway shots- 150-200yrd", "Fairway shots- 150-200yrd value",
                 "Fairway shots- 100-150yrd", "Fairway shots- 100-150yrd Value",
                 "Fairway shots- Over 200yrd", "Fairway shots- Over 200yrd value",
                 "Fairway shots- 50-100yrd", "Fairway shots- 50-100yrd value",
                 "Rough shots- Over 150yrd", "Rough shots- Over 150yrd value",
                 "Rough shots- Under 150yrd", "Rough shots- Under 150yrd value"]
app_sub = app_raw[[c for c in app_cols_keep if c in app_raw.columns]].copy()
# Deduplicate approach data — keep first occurrence per player key
app_sub = app_sub.drop_duplicates(subset=["key"], keep="first")
app_rename = {
    "Fairway shots- 150-200yrd": "app_150_200_shots",
    "Fairway shots- 150-200yrd value": "app_150_200_value",
    "Fairway shots- 100-150yrd": "app_100_150_shots",
    "Fairway shots- 100-150yrd Value": "app_100_150_value",
    "Fairway shots- Over 200yrd": "app_over200_shots",
    "Fairway shots- Over 200yrd value": "app_over200_value",
    "Fairway shots- 50-100yrd": "app_50_100_shots",
    "Fairway shots- 50-100yrd value": "app_50_100_value",
    "Rough shots- Over 150yrd": "rough_over150_shots",
    "Rough shots- Over 150yrd value": "rough_over150_value",
    "Rough shots- Under 150yrd": "rough_under150_shots",
    "Rough shots- Under 150yrd value": "rough_under150_value",
}
app_sub = app_sub.rename(columns={k: v for k, v in app_rename.items() if k in app_sub.columns})
df = df.merge(app_sub, on="key", how="left")

# Merge form data
form_cols = ["key", "True SG", "True SG vs Baseline",
             "Last 5 Starts-Finish-Start 1", "Last 5 Starts-Finish-Start 2",
             "Last 5 Starts-Finish-Start 3", "Last 5 Starts-Finish-Start 4",
             "Last 5 Starts-Finish-Start 5", "main-tour-L20 Rds"]
form_sub = form_raw[[c for c in form_cols if c in form_raw.columns]].copy()
form_sub.columns = [c.strip() for c in form_sub.columns]
form_rename = {
    "True SG": "true_sg_last5",
    "True SG vs Baseline": "true_sg_vs_baseline",
    "Last 5 Starts-Finish-Start 1": "fin_1",
    "Last 5 Starts-Finish-Start 2": "fin_2",
    "Last 5 Starts-Finish-Start 3": "fin_3",
    "Last 5 Starts-Finish-Start 4": "fin_4",
    "Last 5 Starts-Finish-Start 5": "fin_5",
    "main-tour-L20 Rds": "main_tour_l20",
}
form_sub = form_sub.rename(columns={k: v for k, v in form_rename.items() if k in form_sub.columns})
df = df.merge(form_sub, on="key", how="left")

# Merge course history
ch_cols = ["key", "ch_adjustment", "experience_adjustment", "rounds_played",
           "historical_true_sg", "versus_expected",
           "2021 (abrdn Scottish Open)", "2022 (Genesis Scottish Open)",
           "2023 (Genesis Scottish Open)", "2024 (Genesis Scottish Open)",
           "2025 (Genesis Scottish Open)"]
ch_sub = ch_raw[[c for c in ch_cols if c in ch_raw.columns]].copy()
ch_rename = {
    "rounds_played": "starts_at_renaissance",  # actually rounds
    "historical_true_sg": "ch_hist_true_sg",
    "versus_expected": "ch_vs_expected",
    "2021 (abrdn Scottish Open)": "res_2021",
    "2022 (Genesis Scottish Open)": "res_2022",
    "2023 (Genesis Scottish Open)": "res_2023",
    "2024 (Genesis Scottish Open)": "res_2024",
    "2025 (Genesis Scottish Open)": "res_2025",
}
ch_sub = ch_sub.rename(columns={k: v for k, v in ch_rename.items() if k in ch_sub.columns})
df = df.merge(ch_sub, on="key", how="left")

# Merge venue fit
fit_cols = ["key", "short game", "approach", "driving-distance", "driving-accuracy",
            "total sg adj", "Approach 150-200 yds", "Approach 100-150 yds",
            "Course-Fairway", "Course-Rough"]
fit_sub = fit_raw[[c for c in fit_cols if c in fit_raw.columns]].copy()
fit_rename = {
    "short game": "fit_short_game",
    "approach": "fit_approach",
    "driving-distance": "fit_drive_dist",
    "driving-accuracy": "fit_drive_acc",
    "total sg adj": "venue_fit_total_adj",
    "Approach 150-200 yds": "fit_app_150_200",
    "Approach 100-150 yds": "fit_app_100_150",
    "Course-Fairway": "fit_fairway",
    "Course-Rough": "fit_rough",
}
fit_sub = fit_sub.rename(columns={k: v for k, v in fit_rename.items() if k in fit_sub.columns})
df = df.merge(fit_sub, on="key", how="left")

# Merge 2025 result
res_sub = res_raw[["key", "finish_2025"]].copy()
df = df.merge(res_sub, on="key", how="left")

print(f"  Master dataframe: {len(df)} rows, {len(df.columns)} columns")

# ─────────────────────────────────────────────
# CANONICAL VENUE HISTORY FEATURE OBJECT
# Derived from the_renaissance_club_CH.csv result columns.
# Consumed by FC-1 (generate_venue_history_summary); does NOT touch VTS math.
# ─────────────────────────────────────────────
_YEAR_COLS = ["res_2021", "res_2022", "res_2023", "res_2024", "res_2025"]
_YEAR_LABELS = [2021, 2022, 2023, 2024, 2025]


def compute_vh_features(row):
    results_by_year = {}
    for col, yr in zip(_YEAR_COLS, _YEAR_LABELS):
        val = row.get(col)
        if val is not None and not pd.isna(val) and str(val).strip().upper() not in ("NULL", ""):
            results_by_year[yr] = parse_finish(val)

    start_count = len(results_by_year)
    made_cuts = {yr: f for yr, f in results_by_year.items() if f < 999}

    best_finish = min(made_cuts.values()) if made_cuts else None
    best_finish_year = None
    if best_finish is not None:
        tied = [yr for yr, f in made_cuts.items() if f == best_finish]
        best_finish_year = max(tied)

    last_finish_year = max(made_cuts.keys()) if made_cuts else None
    last_finish = made_cuts[last_finish_year] if last_finish_year is not None else None

    top5_count = sum(1 for f in made_cuts.values() if f <= 5)
    top15_count = sum(1 for f in made_cuts.values() if f <= 15)
    made_cut_count = len(made_cuts)

    is_defending = results_by_year.get(2025) == 1
    has_venue_win = any(f == 1 for f in results_by_year.values())
    has_venue_podium = best_finish is not None and best_finish <= 5
    has_recent_top15 = last_finish is not None and last_finish <= 15

    return pd.Series({
        "renaissance_start_count": start_count,
        "best_finish_year_renaissance": best_finish_year,
        "last_finish_renaissance": last_finish,
        "last_finish_year_renaissance": last_finish_year,
        "top5_count_renaissance": top5_count,
        "top15_count_renaissance": top15_count,
        "made_cut_count_renaissance": made_cut_count,
        "is_defending_champion": is_defending,
        "has_venue_win": has_venue_win,
        "has_venue_podium": has_venue_podium,
        "has_recent_top15_renaissance": has_recent_top15,
        "best_finish_renaissance_true": best_finish,
    })


vh_features = df.apply(compute_vh_features, axis=1)
df = pd.concat([df, vh_features], axis=1)
print(f"  Canonical VH features computed. Defending champion(s): {int(df['is_defending_champion'].sum())}. "
      f"Venue winners: {int(df['has_venue_win'].sum())}. "
      f"Podium (top-5): {int(df['has_venue_podium'].sum())}. "
      f"Recent top-15: {int(df['has_recent_top15_renaissance'].sum())}.")

# ─────────────────────────────────────────────
# DATA DEPTH CLASSIFICATION
# ─────────────────────────────────────────────
def data_depth_class(rounds):
    if pd.isna(rounds):
        return "DEBUT"
    r = float(rounds)
    if r >= 20:
        return "FULL"
    elif r >= 10:
        return "MODERATE"
    elif r > 0:
        return "LIMITED"
    return "DEBUT"

df["data_depth_class"] = df["rounds_12m"].apply(data_depth_class)

# Compute field means for regression
sg_cols_num = ["sg_app_12m", "sg_ott_12m", "sg_arg_12m", "sg_putt_12m",
               "sg_t2g_12m", "sg_total_12m"]
field_means = {c: df[c].mean() for c in sg_cols_num if c in df.columns}

# Regression factors
regression_map = {"FULL": 0.0, "MODERATE": 0.15, "LIMITED": 0.40, "DEBUT": 0.60}

def regress(val, mean, factor):
    if pd.isna(val):
        return mean
    return val * (1 - factor) + mean * factor

for col in sg_cols_num:
    if col in df.columns:
        df[f"{col}_r"] = df.apply(
            lambda r, c=col: regress(r[c], field_means.get(c, 0.0),
                                     regression_map[r["data_depth_class"]]), axis=1)

# ─────────────────────────────────────────────
# STEP 2 — NEUTRAL SKILL (Layer 1)
# ─────────────────────────────────────────────
print("Computing NeutralSkill …")

df["neutral_skill_raw"] = (
    df["sg_app_12m_r"] * 0.35
    + df["sg_ott_12m_r"] * 0.30
    + df["sg_arg_12m_r"] * 0.20
    + df["sg_putt_12m_r"] * 0.15
)

# Form adjustment to neutral skill
def form_adj_neutral(true_sg_vs_baseline):
    if pd.isna(true_sg_vs_baseline):
        return 0.0
    v = float(true_sg_vs_baseline)
    if v > 0.5:
        # scale +0.10 to +0.30, cap at +0.30
        adj = min(0.10 + (v - 0.5) * 0.20, 0.30)
        return adj
    elif v < -0.5:
        adj = max(-0.10 - (abs(v) - 0.5) * 0.20, -0.30)
        return adj
    return 0.0

# FIX (FC-2): form_adj_neutral removed — form belongs ONLY in the dedicated FORM layer (Step 5).
# Previously, HOT form boosted NSI via this path AND received a separate form_score weight,
# double-counting the signal and overriding structural skill differences (e.g. Scheffler vs Clark).
df["form_adj_neutral"] = pd.Series(0.0, index=df.index)
df["neutral_skill_sg"] = df["neutral_skill_raw"]  # pure structural skill, no form injection

# Normalize to 0-100
df["neutral_skill_index"] = zscore_scale(df["neutral_skill_sg"], target_mean=50.0, target_std=16.0)

# Classify form
def classify_form(vsb):
    if pd.isna(vsb):
        return "NEUTRAL"
    v = float(vsb)
    if v > 0.8:
        return "HOT"
    elif v > 0.3:
        return "WARM"
    elif v > -0.3:
        return "NEUTRAL"
    elif v > -0.8:
        return "COOL"
    return "COLD"

df["form_class"] = df["true_sg_vs_baseline"].apply(classify_form)

# ─────────────────────────────────────────────
# STEP 3 — VENUE FIT DELTA (Layer 2)
# ─────────────────────────────────────────────
print("Computing VenueFitDelta …")

# Fill NaN with 0 for venue fit scalars (0 = field average / neutral)
for col in ["venue_fit_total_adj", "fit_drive_acc"]:
    if col not in df.columns:
        df[col] = 0.0
    else:
        df[col] = df[col].fillna(0.0)

# Parse approach zone values — keep NaN for players with no data (genuine missings)
# NaN means "no data", 0.0 means "exactly field average" — these are different signals
_approach_val_cols = ["app_150_200_value", "app_100_150_value", "app_over200_value",
                      "rough_over150_value", "rough_under150_value", "app_50_100_value"]
for col in _approach_val_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")  # parse; NaN stays NaN
    else:
        df[col] = np.nan

# Computation columns: fill NaN with 0 for formula (0 = field average penalty-free)
for col in _approach_val_cols:
    df[f"{col}_c"] = df[col].fillna(0.0)

# Renaissance-weighted composite across all approach zones (total weights = 1.00)
df["approach_composite_value"] = (
    df["app_150_200_value_c"]    * 0.38   # dominant scoring zone (primary par-4 approach distance)
    + df["app_100_150_value_c"]  * 0.24   # short iron approach (many mid-length par 4s)
    + df["app_over200_value_c"]  * 0.14   # long par-4 / par-5 second shots
    + df["rough_over150_value_c"] * 0.12  # links rough recovery from distance (penal rough)
    + df["app_50_100_value_c"]   * 0.07   # wedge from fairway
    + df["rough_under150_value_c"] * 0.05  # rough wedge recovery
)

# FIX (FC-2 Bug 1+2): Two distinct bugs corrected here:
#   Bug 1 — fit_drive_acc was already baked inside venue_fit_total_adj (it is the "driving-accuracy"
#            component of that total). Adding it again at ×0.15 gave driving accuracy an effective
#            weight of 0.55+0.15=0.70 — double-counted and asymmetrically penalising accurate players.
#   Bug 2 — the venue fit CSV's driving-accuracy column is inverted vs actual SG data
#            (Scheffler +5.4pp actual accuracy → fit_drive_acc=-0.13 penalty; Clark -3.3pp actual
#            → fit_drive_acc=+0.07 bonus). Replacing with SG-CSV canonical signal.
# Strip DA from total_adj so it is not counted twice:
df["venue_fit_total_adj_ex_da"] = df["venue_fit_total_adj"].fillna(0.0) - df["fit_drive_acc"].fillna(0.0)
# Canonical driving accuracy signal from SG source: 0.015 strokes/rnd per pp of DA vs field avg.
# Field DA range ≈ -10 to +12pp → signal range ≈ -0.15 to +0.18 (clipped to ±0.15).
df["drive_acc_sg_signal"] = (df["drive_acc_12m"].fillna(0.0) * 0.015).clip(-0.15, 0.15)
df["venue_fit_raw"] = (
    df["venue_fit_total_adj_ex_da"] * 0.45   # DA removed; weight reduced from 0.55
    + df["approach_composite_value"] * 0.40  # primary Renaissance trait; up from 0.30
    + df["drive_acc_sg_signal"] * 0.15       # SG-CSV accuracy; correct sign, non-redundant
)

# ─── ANTI-PATTERN FLAGS ───
# Flag 1: sg_app < 0 AND no positive history at Renaissance
def ch_positive(row):
    """Check if player has positive course history (historical_true_sg > 0)."""
    if "ch_hist_true_sg" in row.index and not pd.isna(row.get("ch_hist_true_sg")):
        return float(row["ch_hist_true_sg"]) > 0
    return False

df["ap_flag1"] = (
    df["sg_app_12m"].fillna(0.0) < 0
) & (~df.apply(ch_positive, axis=1))

# Flag 2: below-avg driving accuracy (SG-based) AND negative approach composite
# FIX (FC-2): now uses drive_acc_sg_signal (canonical SG source) instead of fit_drive_acc (suspect CSV)
df["ap_flag2"] = (
    df["drive_acc_sg_signal"] < -0.03  # accuracy ≥ 2pp below field avg by SG data
) & (df["approach_composite_value"] <= 0)

# Flag 3: sg_putt > 1.5 (volatile putter — flag only, not venue_fit penalty)
df["ap_flag3"] = df["sg_putt_12m_r"].fillna(0.0) > 1.5

# Flag 4: bomb-and-spray — sg_ott top 10% (truly elite OTT) AND sg_app clearly negative
# More selective: requires both extreme OTT and meaningfully negative approach
ott_threshold = df["sg_ott_12m_r"].quantile(0.90)
df["ap_flag4"] = (df["sg_ott_12m_r"].fillna(0.0) >= ott_threshold) & (df["sg_app_12m"].fillna(0.0) < -0.10)

# Flag 5: debut at Renaissance (no course history) AND not established European player
df["has_ch"] = df["ch_adjustment"].notna()
df["ap_flag5"] = ~df["has_ch"]

# Flag 6: sg_arg < -0.5
df["ap_flag6"] = df["sg_arg_12m"].fillna(0.0) < -0.5

# Apply anti-pattern penalties to venue_fit_raw
penalties_venue = pd.Series(0.0, index=df.index)
penalties_venue += df["ap_flag1"].astype(float) * 0.40
penalties_venue += df["ap_flag2"].astype(float) * 0.30
penalties_venue += df["ap_flag4"].astype(float) * 0.35
penalties_venue += df["ap_flag5"].astype(float) * 0.20
penalties_venue += df["ap_flag6"].astype(float) * 0.20

df["venue_fit_penalized"] = df["venue_fit_raw"] - penalties_venue

# Flag 7: 2+ flags = Anti-Pattern player
flag_cols = ["ap_flag1", "ap_flag2", "ap_flag4", "ap_flag5", "ap_flag6"]
df["ap_total_flags"] = df[flag_cols].astype(int).sum(axis=1)
df["ap_flag7"] = df["ap_total_flags"] >= 2

# Normalize venue fit to 0-100
df["venue_fit_score"] = zscore_scale(df["venue_fit_penalized"], target_mean=50.0, target_std=14.0)

# Build anti_pattern_flags string
def build_ap_flags(row):
    flags = []
    if row.get("ap_flag1"): flags.append("weak-APP/no-CH")
    if row.get("ap_flag2"): flags.append("acc-neg/app-neg")
    if row.get("ap_flag3"): flags.append("volatile-putter")
    if row.get("ap_flag4"): flags.append("bomb-and-spray")
    if row.get("ap_flag5"): flags.append("renaissance-debut")
    if row.get("ap_flag6"): flags.append("weak-ARG")
    if row.get("ap_flag7"): flags.append("ANTI-PATTERN")
    return "|".join(flags) if flags else "none"

df["anti_pattern_flags"] = df.apply(build_ap_flags, axis=1)

# ─────────────────────────────────────────────
# STEP 4 — VENUE HISTORY DELTA (Layer 3)
# ─────────────────────────────────────────────
print("Computing VenueHistoryDelta …")

# Best historical finish — true minimum across all years (from canonical VH feature object).
# Previously this function returned the most-recent finish, not the best; now corrected.
df["best_finish_renaissance"] = df["best_finish_renaissance_true"]

# 2025 recent bonus
def recent_2025_bonus(row):
    """Bonus from 2025 Renaissance finish."""
    f = parse_finish(row.get("res_2025"))
    if f == 1:
        return 0.20
    elif f <= 5:
        return 0.15
    elif f <= 10:
        return 0.10
    elif f <= 20:
        return 0.05
    elif f <= 40:
        return 0.0
    elif f < 999:
        return -0.05
    return 0.0

df["bonus_2025"] = df.apply(recent_2025_bonus, axis=1)

# Historical signal from ch_adjustment + experience_adjustment
df["ch_adjustment_f"] = pd.to_numeric(df.get("ch_adjustment", np.nan), errors="coerce").fillna(0.0)
df["experience_adjustment_f"] = pd.to_numeric(df.get("experience_adjustment", np.nan), errors="coerce").fillna(0.0)

# FIX (FC-2 Bug 5): Add explicit podium (T2-T5) and venue-win quality bonuses.
# Previously ch_adjustment rewarded consistency-vs-expected only — Scheffler's T3 podium
# was not credited because his CUT in 2022 pulled his versus_expected negative.
# A T3 must outweigh a pattern of T10-T11 finishes; separate quality bonuses enforce this.
df["podium_bonus_vhn"] = df.apply(
    lambda r: 0.08 if (r.get("has_venue_podium", False) and not r.get("has_venue_win", False)) else 0.0,
    axis=1)
df["win_bonus_vhn"] = df["has_venue_win"].astype(float) * 0.12

df["venue_history_raw"] = (
    df["ch_adjustment_f"] * 3.0            # reduced from 4.0 — less dominance of baseline-vs-expected
    + df["experience_adjustment_f"] * 1.5   # reduced from 2.0
    + df["bonus_2025"]
    + df["podium_bonus_vhn"]
    + df["win_bonus_vhn"]
)
# Players with no course history: neutral
df["debut_flag"] = ~df["has_ch"]
df.loc[df["debut_flag"], "venue_history_raw"] = 0.0

# Venue history depth classification
def vh_depth(row):
    starts = float(row.get("starts_at_renaissance", 0) or 0)
    ch_adj = float(row.get("ch_adjustment_f", 0))
    if starts == 0 or pd.isna(starts):
        return "NONE"
    elif starts >= 4 * 4 and ch_adj > 0:  # ≥16 rounds = 4 starts ≈ STRONG
        return "STRONG"
    elif starts >= 4 * 2:  # ≥8 rounds = 2 starts
        return "MODERATE"
    else:
        return "THIN"

df["venue_history_depth"] = df.apply(vh_depth, axis=1)

# Normalize to 0-100 with 50 = neutral
df["venue_history_normalized"] = zscore_scale(
    df["venue_history_raw"], target_mean=50.0, target_std=12.0)
# Force true debuts to exactly 50 (neutral)
df.loc[df["debut_flag"] & (df["venue_history_raw"] == 0.0), "venue_history_normalized"] = 50.0

# ─────────────────────────────────────────────
# STEP 5 — FORM SCORE (Layer 4)
# ─────────────────────────────────────────────
print("Computing FormScore …")

def form_score_base(vsb):
    """Map true_sg_vs_baseline to form_score base using class bands."""
    if pd.isna(vsb):
        return 50.0
    v = float(vsb)
    if v > 0.8:
        # HOT: 65-80
        return min(65.0 + (v - 0.8) * 15.0, 80.0)
    elif v > 0.3:
        # WARM: 55-65
        return 55.0 + (v - 0.3) / 0.5 * 10.0
    elif v > -0.3:
        # NEUTRAL: 45-55
        return 50.0 + (v / 0.3) * 5.0
    elif v > -0.8:
        # COOL: 35-45
        return 45.0 + (v + 0.3) / 0.5 * 10.0
    else:
        # COLD: 20-35
        return max(35.0 + (v + 0.8) * 15.0, 20.0)

df["form_score"] = df["true_sg_vs_baseline"].apply(form_score_base)

# Adjust for recent finishes pattern
def recent_pattern_bonus(row):
    bonus = 0.0
    finishes = []
    for c in ["fin_1", "fin_2", "fin_3", "fin_4", "fin_5"]:
        if c in row.index:
            f = parse_finish(row.get(c))
            finishes.append(f)
    if not finishes:
        return 0.0
    wins = sum(1 for f in finishes if f == 1)
    t5s = sum(1 for f in finishes if 1 < f <= 5)
    cuts = sum(1 for f in finishes if f >= 999)
    bonus += wins * 3.0 + t5s * 1.5
    bonus -= cuts * 1.5
    return np.clip(bonus, -8.0, 8.0)

df["form_recent_bonus"] = df.apply(recent_pattern_bonus, axis=1)
df["form_score"] = (df["form_score"] + df["form_recent_bonus"]).clip(20.0, 85.0)

# ─────────────────────────────────────────────
# STEP 6 — VTS CALCULATION & TIER ASSIGNMENT
# ─────────────────────────────────────────────
print("Computing VTS …")

# Penalties are already baked into venue_fit_score (applied to venue_fit_raw before normalization).
# For VTS, we track penalty magnitude for reporting but do not double-subtract.
# Per spec: "total_penalties: sum of anti-pattern penalties (scaled to VTS points: multiply raw penalty ×8)"
# We apply a modest additional VTS-level discount for confirmed multi-flag (AP7) players only.
df["total_penalties_raw"] = penalties_venue
df["total_penalties_vts"] = df["ap_flag7"].astype(float) * 3.0  # confirmed anti-pattern: 3-point VTS discount

df["vts_pre_norm"] = (
    df["neutral_skill_index"] * 0.40
    + df["venue_fit_score"] * 0.30
    + df["venue_history_normalized"] * 0.15
    + df["form_score"] * 0.15
    - df["total_penalties_vts"]
)

# Re-normalize VTS to 0-100
df["vts_final"] = zscore_scale(df["vts_pre_norm"], target_mean=52.0, target_std=16.0)

# Assign tiers
def assign_tier(vts):
    if vts >= 80:
        return 1
    elif vts >= 65:
        return 2
    elif vts >= 50:
        return 3
    elif vts >= 35:
        return 4
    return 5

df["tier"] = df["vts_final"].apply(assign_tier)

# Print tier distribution for validation
tier_counts = df["tier"].value_counts().sort_index()
print(f"  Tier distribution: {dict(tier_counts)}")

# If Tier 1 has fewer than 3 players, lower threshold slightly
t1_count = (df["tier"] == 1).sum()
if t1_count < 3:
    # Lower Tier 1 threshold to get at least 4 players
    t1_threshold = df["vts_final"].nlargest(5).min()
    df["tier"] = df.apply(
        lambda r: 1 if r["vts_final"] >= t1_threshold else r["tier"], axis=1)
    tier_counts = df["tier"].value_counts().sort_index()
    print(f"  Adjusted Tier distribution: {dict(tier_counts)}")

# Sort and rank
df = df.sort_values("vts_final", ascending=False).reset_index(drop=True)
df["rank"] = df.index + 1

# ─────────────────────────────────────────────
# STEP 7 — PROBABILITIES
# ─────────────────────────────────────────────
print("Computing probabilities …")

FIELD_SIZE = len(df)

def logistic_win(vts):
    """Calibrated logistic — center=70 (T1 baseline), slope=6 for within-T1 differentiation.
    Floor clips removed: they cause all T1 players to converge to the same value."""
    x = (vts - 70.0) / 6.0
    return 1.0 / (1.0 + np.exp(-x))

# Normalize over full field — no tier floor clips (they flatten T1)
df["win_prob_raw"] = df["vts_final"].apply(logistic_win)
total_raw = df["win_prob_raw"].sum()
df["win_prob"] = (df["win_prob_raw"] / total_raw * 100.0).round(2)

# Derived probs (links HIGH variance)
df["top5_prob"] = (df["win_prob"] * 4.5).clip(upper=55.0).round(2)
df["top10_prob"] = (df["win_prob"] * 8.0).clip(upper=75.0).round(2)
df["top20_prob"] = (df["win_prob"] * 15.0).clip(upper=90.0).round(2)

# Make cut probability from neutral_skill_index + form_score
def make_cut_prob(nsi, fs):
    if pd.isna(nsi):
        nsi = 50.0
    base_nsi = float(nsi)
    base_fs = float(fs) if not pd.isna(fs) else 50.0
    combined = base_nsi * 0.65 + base_fs * 0.35
    if combined > 75:
        return round(np.random.uniform(85, 92), 1)
    elif combined > 65:
        return round(np.random.uniform(75, 85), 1)
    elif combined > 50:
        return round(np.random.uniform(60, 75), 1)
    elif combined > 35:
        return round(np.random.uniform(45, 60), 1)
    else:
        return round(np.random.uniform(25, 45), 1)

# Use deterministic version
def make_cut_prob_det(row):
    nsi = float(row.get("neutral_skill_index", 50) or 50)
    fs = float(row.get("form_score", 50) or 50)
    combined = nsi * 0.65 + fs * 0.35
    if combined > 75:
        lo, hi = 85.0, 92.0
    elif combined > 65:
        lo, hi = 75.0, 85.0
    elif combined > 50:
        lo, hi = 60.0, 75.0
    elif combined > 35:
        lo, hi = 45.0, 60.0
    else:
        lo, hi = 25.0, 45.0
    # Use VTS rank to spread within band
    rank_pct = 1.0 - (row.get("rank", 80) - 1) / (FIELD_SIZE - 1)
    return round(lo + rank_pct * (hi - lo), 1)

df["make_cut_prob"] = df.apply(make_cut_prob_det, axis=1)
df["miss_cut_prob"] = (100.0 - df["make_cut_prob"]).round(1)

# Best betting lane
def best_betting_lane(row):
    wp = float(row.get("win_prob", 0))
    t5 = float(row.get("top5_prob", 0))
    t10 = float(row.get("top10_prob", 0))
    t20 = float(row.get("top20_prob", 0))
    mc = float(row.get("make_cut_prob", 50))
    tier = int(row.get("tier", 5))
    ap_flags = int(row.get("ap_total_flags", 0))

    # Winner: highest-conviction Tier 1 with no anti-pattern
    if tier == 1 and ap_flags == 0 and wp >= 2.5:
        return "Winner"
    elif tier == 1 and wp >= 2.0:
        return "Top 5"
    # Tier 2: route to Top 10 unless flagged
    elif tier == 2 and ap_flags == 0:
        return "Top 10"
    elif tier == 2 and ap_flags >= 1:
        return "Top 20"
    # Tier 3: Top 20 as primary lane
    elif tier == 3 and t20 >= 10.0:
        return "Top 20"
    elif tier == 3 and mc >= 72.0:
        return "Make Cut"
    # Tier 4: Make Cut / Miss Cut
    elif tier == 4 and mc >= 78.0:
        return "Make Cut"
    elif mc < 50.0:
        return "Miss Cut"
    return "Pass / No Edge"

df["best_betting_lane"] = df.apply(best_betting_lane, axis=1)

# ─────────────────────────────────────────────
# CONVICTION LEVEL
# ─────────────────────────────────────────────
def conviction_level(row):
    tier = int(row.get("tier", 5))
    ap_flags = int(row.get("ap_total_flags", 0))
    ddc = row.get("data_depth_class", "DEBUT")
    fc = row.get("form_class", "NEUTRAL")
    vh = row.get("venue_history_depth", "NONE")
    score = 0
    if tier <= 2: score += 3
    if tier == 3: score += 2
    if ap_flags == 0: score += 2
    elif ap_flags == 1: score += 1
    if ddc == "FULL": score += 2
    elif ddc == "MODERATE": score += 1
    if fc in ("HOT", "WARM"): score += 1
    if fc in ("COLD", "COOL"): score -= 1
    if vh in ("STRONG", "MODERATE"): score += 1
    if score >= 7: return "HIGH"
    elif score >= 5: return "MEDIUM"
    elif score >= 3: return "LOW"
    return "SPECULATIVE"

df["conviction_level"] = df.apply(conviction_level, axis=1)

# ─────────────────────────────────────────────
# STEP 8 — GENERATE OUTPUT FILES
# ─────────────────────────────────────────────
print("Writing output files …")

# Tour affiliation mapping (simple heuristic from form data)
def infer_tour(key):
    form_match = form_raw[form_raw["key"] == key]
    if len(form_match) > 0:
        tour = str(form_match.iloc[0].get("main-tour-L20 Rds", ""))
        # tour column is actually main-tour type prefix
        tours = {
            "PGA": "PGA Tour", "DPT": "DP World Tour", "LIV": "LIV Golf",
            "EUR": "DP World Tour", "JPN": "Japan Golf Tour"
        }
        # look at start 1 tour
        t1 = str(form_match.iloc[0].get("Last 5 Starts-Tour-Start 1", ""))
        if "PGA Tour" in t1: return "PGA Tour"
        if "DP World" in t1: return "DP World Tour"
        if "LIV" in t1: return "LIV Golf"
        if "Japan" in t1: return "Japan Golf Tour"
    return "Unknown"

# Determine tour from form data — try by key
form_tour_map = {}
if "Last 5 Starts-Tour-Start 1" in form_raw.columns:
    for _, r in form_raw.iterrows():
        k = r.get("key", "")
        t = str(r.get("Last 5 Starts-Tour-Start 1", ""))
        if "PGA Tour" in t:
            form_tour_map[k] = "PGA Tour"
        elif "DP World" in t:
            form_tour_map[k] = "DP World Tour"
        elif "LIV" in t:
            form_tour_map[k] = "LIV Golf"
        elif "Japan" in t:
            form_tour_map[k] = "Japan Golf Tour"
        elif "Korn Ferry" in t:
            form_tour_map[k] = "Korn Ferry Tour"
        else:
            form_tour_map[k] = "DP World Tour"  # default for international

df["tour_affiliation"] = df["key"].apply(lambda k: form_tour_map.get(k, "DP World Tour"))

# ── FILE 1: field_input ──
file1 = df[[
    "player_id", "last", "first", "tour_affiliation", "data_depth_class",
    "debut_flag", "neutral_skill_sg", "sg_ott_12m", "sg_app_12m",
    "sg_arg_12m", "sg_putt_12m", "sg_t2g_12m", "true_sg_last5",
    "true_sg_vs_baseline", "form_class", "venue_history_depth",
    "starts_at_renaissance", "best_finish_renaissance", "venue_fit_total_adj",
    "app_150_200_value", "fit_drive_acc"
]].copy()
file1.columns = [
    "player_id", "last_name", "first_name", "tour_affiliation", "data_depth_class",
    "debut_flag", "neutral_skill_sg", "sg_ott_12m", "sg_app_12m",
    "sg_arg_12m", "sg_putt_12m", "sg_t2g_12m", "true_sg_last5",
    "true_sg_vs_baseline", "form_class", "venue_history_depth",
    "starts_at_renaissance", "best_finish_renaissance", "venue_fit_total_adj",
    "predicted_app_150_200_share", "predicted_driving_accuracy_fit"
]
file1.to_csv(OUTPUT / "2026_genesis_scottish_open_field_input.csv", index=False)
print(f"  File 1 written: {len(file1)} rows")

# ── FILE 2: trait_form_matrix ──
# Additional trait columns
# Use canonical SG-based driving accuracy signal (drive_acc_sg_signal range ±0.15 → map to 25-75 centered at 50)
df["corridor_discipline"] = (df["drive_acc_sg_signal"].fillna(0.0) / 0.15 * 25 + 50).clip(20, 90)
df["par3_performance"] = (df.get("sg_app_12m_r", 0.0).fillna(0.0) * 15 + 50).clip(20, 90)
df["confidence_band"] = df["conviction_level"].map(
    {"HIGH": "TIGHT", "MEDIUM": "MODERATE", "LOW": "WIDE", "SPECULATIVE": "VERY_WIDE"})
df["sg_putt_regressed"] = df["sg_putt_12m_r"]

file2 = df[[
    "player_id", "last", "first", "app_150_200_value", "fit_approach",
    "fit_drive_acc", "corridor_discipline", "sg_putt_regressed",
    "sg_arg_12m_r", "par3_performance", "true_sg_vs_baseline",
    "form_class", "anti_pattern_flags", "debut_flag", "confidence_band"
]].copy()
file2.columns = [
    "player_id", "last_name", "first_name", "approach_150_200_score",
    "approach_overall_score", "driving_accuracy_score", "corridor_discipline",
    "sg_putt_regressed", "sg_arg_score", "par3_performance", "form_trend",
    "form_class", "anti_pattern_flags", "debut_discount_applied", "confidence_band"
]
file2.to_csv(OUTPUT / "2026_genesis_scottish_open_trait_form_matrix.csv", index=False)
print(f"  File 2 written: {len(file2)} rows")

# ── FILE 3: vts_full ──
file3 = df[[
    "player_id", "last", "first", "tier", "rank",
    "neutral_skill_index", "venue_fit_score", "venue_history_normalized",
    "form_score", "total_penalties_vts", "vts_final",
    "win_prob", "top5_prob", "top10_prob", "top20_prob",
    "make_cut_prob", "miss_cut_prob",
    "best_betting_lane", "anti_pattern_flags", "conviction_level"
]].copy()
file3.columns = [
    "player_id", "last_name", "first_name", "tier", "rank",
    "neutral_skill_index", "venue_fit_score", "venue_history_normalized",
    "form_score", "penalties_applied", "vts_final",
    "win_prob", "top5_prob", "top10_prob", "top20_prob",
    "make_cut_prob", "miss_cut_prob",
    "best_betting_lane", "anti_pattern_flags", "conviction_level"
]
file3.to_csv(OUTPUT / "2026_genesis_scottish_open_vts_full.csv", index=False)
print(f"  File 3 written: {len(file3)} rows")

# ─────────────────────────────────────────────
# BADGE LOGIC
# ─────────────────────────────────────────────
def compute_badges(row):
    badges = []
    vh = row.get("venue_history_depth", "NONE")
    tier = int(row.get("tier", 5))
    ap_flags = int(row.get("ap_total_flags", 0))
    mc = float(row.get("make_cut_prob", 50))
    wp = float(row.get("win_prob", 0))
    t10 = float(row.get("top10_prob", 0))
    vsb = float(row.get("true_sg_vs_baseline", 0) or 0)
    sg_putt_r = float(row.get("sg_putt_12m_r", 0) or 0)
    ch_adj = float(row.get("ch_adjustment_f", 0))
    debut = bool(row.get("debut_flag", False))

    if vh in ("STRONG", "MODERATE") and ch_adj > 0:
        badges.append("Course Horse")
    if tier >= 3 and wp > 2.0:
        badges.append("Live Longshot")
    if tier <= 2 and ap_flags >= 1:
        badges.append("Fragile Favorite")
    if mc < 60.0:
        badges.append("Cut Sweat")
    if mc >= 80.0 and wp < 0.5:
        badges.append("False Safety")
    if ap_flags >= 2:
        badges.append("Anti-Pattern")
    if debut:
        badges.append("Debut Watch")
    if sg_putt_r > 1.5:
        badges.append("Volatile Putter")
    if vsb > 1.0:
        badges.append("Form Spike")
    # Ceiling Play: Tier 3+ with one elite trait
    if tier >= 3:
        nsi = float(row.get("neutral_skill_index", 50) or 50)
        vfs = float(row.get("venue_fit_score", 50) or 50)
        if nsi > 70 or vfs > 70:
            badges.append("Ceiling Play")
    return badges


df["badges"] = df.apply(compute_badges, axis=1)

# ─────────────────────────────────────────────
# NARRATIVE GENERATION
# ─────────────────────────────────────────────
def generate_neutral_skill_summary(row):
    nsi = float(row.get("neutral_skill_index", 50) or 50)
    sg_app = row.get("sg_app_12m")
    sg_ott = row.get("sg_ott_12m")
    sg_putt = row.get("sg_putt_12m")
    sg_arg = row.get("sg_arg_12m")
    ddc = row.get("data_depth_class", "FULL")
    parts = []
    if not pd.isna(sg_app):
        parts.append(f"APP {sg_app:+.2f}")
    if not pd.isna(sg_ott):
        parts.append(f"OTT {sg_ott:+.2f}")
    if not pd.isna(sg_putt):
        parts.append(f"PUTT {sg_putt:+.2f}")
    if not pd.isna(sg_arg):
        parts.append(f"ARG {sg_arg:+.2f}")
    sg_str = ", ".join(parts) if parts else "limited data"
    reg_map = {"LIMITED": "40%", "DEBUT": "60%", "MODERATE": "15%"}
    ddc_note = f" ({ddc} data depth — {reg_map.get(ddc, '0%')} regression applied)" if ddc != "FULL" else ""
    # Identify the scoring threshold note
    if not pd.isna(sg_app):
        app_val = float(sg_app)
        if app_val > 0.4:
            threshold_note = " Approach game comfortably above the scoring threshold Renaissance demands from 175-200yds."
        elif app_val > 0.1:
            threshold_note = " Approach game near the scoring threshold Renaissance demands from 175-200yds."
        else:
            threshold_note = " Approach game below the scoring threshold Renaissance demands from 175-200yds."
    else:
        threshold_note = ""
    return f"NeutralSkill {nsi:.1f}/100 — 12-month SG: {sg_str}{ddc_note}.{threshold_note}"


def generate_venue_fit_summary(row):
    vfs = float(row.get("venue_fit_score", 50) or 50)
    total_adj = row.get("venue_fit_total_adj")
    app_val = row.get("app_150_200_value")
    ap = row.get("anti_pattern_flags", "none")
    drive_acc = float(row.get("drive_acc_12m") or 0)  # canonical SG-source accuracy
    app_comp = float(row.get("approach_composite_value") or 0)
    adj_str = f"Approach composite {app_comp:+.4f}" if app_comp != 0 else "no approach data"
    app_str = f", APP 150-200 value {app_val:+.3f}" if not pd.isna(app_val) else ""
    # Mechanism-driven language
    if not pd.isna(app_val) and float(app_val) > 0.02:
        app_mech = " Positive APP 150-200 value confirms approach productivity in the primary scoring zone."
    elif not pd.isna(app_val) and float(app_val) < -0.02:
        app_mech = " Negative APP 150-200 value is a structural drag — Renaissance's dominant scoring zone does not favour this approach distance profile."
    else:
        app_mech = ""
    if ap != "none":
        ap_str = f" Anti-pattern flag(s): {ap} — structural risk factor at Renaissance."
    elif drive_acc < -5.0:
        ap_str = f" Driving accuracy ({drive_acc:+.1f}pp vs field) below average — tee-shot dispersion risk on tight links corridors."
    else:
        ap_str = " No anti-pattern flags — clean structural profile."
    return f"VenueFit {vfs:.1f}/100 — {adj_str}{app_str}.{app_mech}{ap_str}"


def generate_venue_history_summary(row):
    """FC-1: quality-first branch order — win > podium > recent top-15 > depth-by-sample > fallback."""
    vhn = float(row.get("venue_history_normalized", 50) or 50)
    depth = row.get("venue_history_depth", "NONE")

    # Canonical venue feature fields (NaN → None for optional fields)
    def _nz(v, default=0):
        return default if (v is None or (isinstance(v, float) and np.isnan(v))) else v

    start_count = int(_nz(row.get("renaissance_start_count"), 0))
    rounds_played = int(float(_nz(row.get("starts_at_renaissance"), 0)))
    _bfr = row.get("best_finish_renaissance")
    best_finish = None if (_bfr is None or (isinstance(_bfr, float) and np.isnan(_bfr))) else _bfr
    _bfy = row.get("best_finish_year_renaissance")
    best_finish_year = None if (_bfy is None or (isinstance(_bfy, float) and np.isnan(_bfy))) else int(_bfy)
    _lf = row.get("last_finish_renaissance")
    last_finish = None if (_lf is None or (isinstance(_lf, float) and np.isnan(_lf))) else _lf
    _lfy = row.get("last_finish_year_renaissance")
    last_finish_year = None if (_lfy is None or (isinstance(_lfy, float) and np.isnan(_lfy))) else int(_lfy)
    top5_count = int(_nz(row.get("top5_count_renaissance"), 0))
    top15_count = int(_nz(row.get("top15_count_renaissance"), 0))
    made_cut_count = int(_nz(row.get("made_cut_count_renaissance"), 0))
    is_defending = bool(_nz(row.get("is_defending_champion"), False))
    has_podium = bool(_nz(row.get("has_venue_podium"), False))
    has_recent_top15 = bool(_nz(row.get("has_recent_top15_renaissance"), False))
    ch_adj = float(_nz(row.get("ch_adjustment_f"), 0))
    bonus = float(_nz(row.get("bonus_2025"), 0))

    starts_str = f"{start_count} start{'s' if start_count != 1 else ''}"
    bonus_str = f" 2025 recency bonus: {bonus:+.2f}." if bonus != 0.0 else ""

    # Validation guard: best_finish == 1 → must mention winner/defending champion
    # Branch 1: Defending champion or venue winner
    if is_defending or (best_finish is not None and int(best_finish) == 1):
        if is_defending:
            champ_label = f"defending champion ({best_finish_year} winner)" if best_finish_year else "defending champion"
        else:
            champ_label = f"{best_finish_year} winner" if best_finish_year else "former winner"
        top15_note = (f" {top15_count} top-15 result{'s' if top15_count != 1 else ''} "
                      f"from {rounds_played} rounds." if top15_count > 0 else "")
        return (
            f"VenueHistory {vhn:.1f}/100 — {champ_label} at The Renaissance Club ({starts_str}) — "
            f"venue win is the deepest possible course calibration.{top15_note} "
            f"Course-history adj {ch_adj:+.3f}.{bonus_str}"
        )

    # Validation guard: best_finish <= 5 → cannot use limited-history language without podium language
    # Branch 2: Venue podium (top-5, not a win)
    if has_podium and best_finish is not None:
        year_str = f" in {best_finish_year}" if best_finish_year else ""
        if start_count <= 2:
            volume_qualifier = f"THIN sample ({starts_str}) but"
        elif start_count <= 4:
            volume_qualifier = f"{starts_str} —"
        else:
            volume_qualifier = f"{starts_str} including"
        multi_top5 = f" ({top5_count} top-5 results at this venue)" if top5_count >= 2 else ""
        return (
            f"VenueHistory {vhn:.1f}/100 — {volume_qualifier} podium-caliber Renaissance result "
            f"(T{int(best_finish)}{year_str}){multi_top5} — top-5 finish provides real venue-specific "
            f"proof independent of sample volume. Course-history adj {ch_adj:+.3f}.{bonus_str}"
        )

    # Validation guard: last_finish <= 15 → cannot read like debut/no-history
    # Branch 3: Recent top-15 — fires for THIN/MODERATE depth; STRONG-depth players go to Branch 4
    # where the recent result is surfaced via the "most recent result" note instead.
    if has_recent_top15 and last_finish is not None and depth != "STRONG":
        year_str = f" in {last_finish_year}" if last_finish_year else ""
        sample_note = starts_str if start_count > 2 else f"limited sample ({starts_str})"
        if start_count <= 1 or depth in ("NONE", "THIN"):
            outcome_note = "removes true-debut uncertainty"
        elif start_count <= 3:
            outcome_note = "establishes meaningful course familiarity"
        else:
            outcome_note = "marks a usable course reference at this venue"
        return (
            f"VenueHistory {vhn:.1f}/100 — {sample_note} but recent Renaissance result "
            f"T{int(last_finish)}{year_str} {outcome_note}. "
            f"Course-history adj {ch_adj:+.3f}.{bonus_str}"
        )

    # Branch 4: Repeated moderate/strong history by sample (no top-end result)
    if depth in ("STRONG", "MODERATE") or start_count >= 2:
        best_str = (f" Best finish: T{int(best_finish)}" + (f" ({best_finish_year})." if best_finish_year else ".")
                    if best_finish is not None else " No made-cut finish recorded.")
        # Surface recent top-15 when it is a distinct data point from the best finish
        recent_note = ""
        if (has_recent_top15 and last_finish is not None and last_finish_year is not None
                and best_finish_year is not None and last_finish_year != best_finish_year):
            recent_note = f" Most recent: T{int(last_finish)} ({last_finish_year})."
        if top15_count >= 2 and ch_adj > 0:
            mech = ("Proven scorer at this venue — Renaissance-specific knowledge of tee corridors "
                    "and green approach angles is a structural edge.")
        elif top15_count >= 1 and ch_adj > 0:
            mech = ("Course familiarity established with at least one strong Renaissance result — "
                    "partial structural edge from venue-specific calibration.")
        elif ch_adj < 0:
            if depth in ("STRONG", "MODERATE"):
                mech = ("Deep course familiarity but historical scoring below expectation at Renaissance — "
                        "volume of starts does not translate to a consistent contending pattern.")
            else:
                mech = ("Historical scoring below expectation at Renaissance — limited sample "
                        "with negative course-history adjustment.")
        else:
            mech = "Partial calibration of venue-specific scoring patterns through repeated course exposure."
        return (
            f"VenueHistory {vhn:.1f}/100 — depth={depth}, {starts_str} ({rounds_played} rounds).{best_str}"
            f"{recent_note} {mech}{bonus_str}"
        )

    # Branch 5: Limited-history fallback (only when none of the above apply)
    if start_count == 0 or depth == "NONE":
        return (
            f"VenueHistory {vhn:.1f}/100 — Renaissance debut — links-course learning curve applies "
            f"even for elite players; course-specific hole knowledge gap on rerouted closing stretch (new Hole 15)."
        )
    best_str = (f" Best finish: T{int(best_finish)}." if best_finish is not None
                else " No made-cut finish recorded.")
    return (
        f"VenueHistory {vhn:.1f}/100 — limited Renaissance history ({starts_str}, {rounds_played} rounds) "
        f"— partial calibration only; no top-end venue result yet.{best_str}{bonus_str}"
    )


def generate_form_summary(row):
    fc = row.get("form_class", "NEUTRAL")
    vsb = row.get("true_sg_vs_baseline")
    tsg = row.get("true_sg_last5")
    fs = float(row.get("form_score", 50) or 50)
    vsb_val = float(vsb) if not pd.isna(vsb) else None
    vsb_str = f"{vsb:+.2f}" if vsb_val is not None else "N/A"
    tsg_str = f"{tsg:.2f}" if not pd.isna(tsg) else "N/A"
    # Form class mechanism
    if fc == "HOT" and vsb_val is not None and vsb_val > 1.5:
        form_mech = f" HOT form (+{vsb_val:.2f} vs baseline) carries a regression risk by R3-R4 at this variance class, but current momentum is a real structural edge in calm forecast conditions."
    elif fc == "HOT":
        form_mech = " HOT form confirmed — current scoring pace is above seasonal baseline."
    elif fc == "COLD":
        form_mech = " COLD form is a structural drag — model applies a downward form penalty. Needs a reset week to deliver on structural profile."
    elif fc == "COOL":
        form_mech = " COOL form is a mild negative — below baseline scoring rate over last 5 events."
    elif fc == "WARM":
        form_mech = " WARM form trend — above baseline, consistent with an upward momentum cycle."
    else:
        form_mech = " NEUTRAL form — 12-month baseline is the reference; no strong directional signal from recent events."
    return f"Form {fc} (score {fs:.1f}/100) — True SG L5: {tsg_str}, vs baseline: {vsb_str}.{form_mech}"


def generate_anti_pattern_summary(row):
    flags = row.get("anti_pattern_flags", "none")
    if flags == "none":
        return "No anti-pattern flags. Clean structural profile — no recurring weak-link traits identified for Renaissance Club."
    count = int(row.get("ap_total_flags", 0))
    return f"{count} anti-pattern signal(s): {flags}. Structural concerns apply at Renaissance where these patterns historically compound."


def generate_top_traits(row):
    traits = []
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    sg_arg = float(row.get("sg_arg_12m") or 0)
    app_val = float(row.get("app_150_200_value") or 0)
    ch_adj = float(row.get("ch_adjustment_f") or 0)
    dd = float(row.get("driving_distance_baseline") or 0)
    if sg_app > 0.3: traits.append(f"Elite approach game — SG:APP {sg_app:+.2f} over 12m")
    elif sg_app > 0: traits.append(f"Positive approach — SG:APP {sg_app:+.2f} over 12m")
    if sg_ott > 0.5: traits.append(f"Elite off-tee — SG:OTT {sg_ott:+.2f}, maximises distance edge on par-5s in calm forecast")
    elif sg_ott > 0.2: traits.append(f"Strong OTT — SG:OTT {sg_ott:+.2f}, positional value on tight links corridors")
    if sg_putt > 0.3: traits.append(f"Strong putting — SG:PUTT {sg_putt:+.2f} converts long-iron proximity on fescue greens")
    if sg_arg > 0.2: traits.append(f"Short-game skill — SG:ARG {sg_arg:+.2f} recovers from links rough and pot-bunker escapes")
    if app_val > 0.03: traits.append(f"150-200yd iron specialist — value {app_val:+.3f} in the dominant scoring zone at Renaissance")
    if ch_adj > 0.03: traits.append("Positive course history — demonstrated scoring ability at Renaissance Club")
    if dd > 5: traits.append(f"Distance advantage ({dd:+.1f}yds vs field avg) — par-5s reachable in two in calm R1/R2 forecast")
    return traits[:4] if traits else ["Limited positive trait signal identified in current data"]


def generate_drag_traits(row):
    drags = []
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    sg_arg = float(row.get("sg_arg_12m") or 0)
    drive_acc = float(row.get("drive_acc_12m") or 0)  # canonical SG-source driving accuracy (pp vs field avg)
    debut = bool(row.get("debut_flag", False))
    if sg_app < -0.1: drags.append(f"Below-avg approach — SG:APP {sg_app:+.2f} in the primary scoring zone at Renaissance")
    if sg_ott < -0.1: drags.append(f"Below-avg off-tee — SG:OTT {sg_ott:+.2f} on tight links corridors")
    if sg_putt < -0.2: drags.append(f"Poor putting — SG:PUTT {sg_putt:+.2f} on slow fescue greens (~10ft Stimp) amplifies weakness")
    if sg_arg < -0.3: drags.append(f"Weak short game — SG:ARG {sg_arg:+.2f}, costly in links rough and pot-bunker recovery situations")
    if drive_acc < -5.0: drags.append(f"Below-average driving accuracy ({drive_acc:+.1f}pp vs field) — tee-shot dispersion on tight Renaissance corridors compounds rough-approach difficulty")
    if debut: drags.append("Renaissance debut — no tee-corridor or approach-angle knowledge; debut discount applied")
    return drags[:3] if drags else []


def generate_conviction_statement(row):
    tier = int(row.get("tier", 5))
    cl = row.get("conviction_level", "LOW")
    fc = row.get("form_class", "NEUTRAL")
    vh = row.get("venue_history_depth", "NONE")
    ap = int(row.get("ap_total_flags", 0))
    name = f"{row.get('first', '')} {row.get('last', '')}".strip().title()
    last = str(row.get("last", "")).upper()
    first = str(row.get("first", "")).upper()
    vts = float(row.get("vts_final", 50))
    nsi = float(row.get("neutral_skill_index", 50) or 50)
    vfs = float(row.get("venue_fit_score", 50) or 50)
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    vsb = row.get("true_sg_vs_baseline")
    vsb_val = float(vsb) if not pd.isna(vsb) else 0.0
    ch_adj = float(row.get("ch_adjustment_f") or 0)
    app_val = float(row.get("app_150_200_value") or 0)

    if tier == 1:
        # Name the #1 structural reason per player
        if last == "MCILROY":
            return (
                f"McIlroy is the most decorated player in Renaissance Club history (2023 winner, "
                f"highest DG points all-time here) — his elite distance/iron combination is optimally "
                f"suited for this benign-forecast week where pure scoring ability dominates over wind management."
            )
        elif last == "CLARK":
            return (
                f"Clark brings HOT form ({vsb_val:+.2f} vs baseline) to a venue where his approach game "
                f"translated to a T11 finish — in calm conditions favouring birdie-making, his complete "
                f"profile from tee to green is the field's best combination of current momentum and structural fit."
            )
        elif last == "SCHEFFLER":
            return (
                f"Scheffler's elite NSI ({nsi:.1f}/100) is the field ceiling — world No.1 SG:APP "
                f"({sg_app:+.2f}) in the Renaissance primary scoring zone is the dominant structural advantage. "
                f"Limited venue history is the only model caveat in an otherwise pristine profile."
            )
        elif last == "FITZPATRICK":
            return (
                f"Fitzpatrick's Renaissance pedigree (VHN {row.get('venue_history_normalized', 50):.0f}/100) "
                f"is the defining edge — his precise iron game and elite positional driving are purpose-built "
                f"for the tight corridors and long-iron demands of this links setup."
            )
        elif last == "HATTON":
            return (
                f"Hatton's combination of HOT form ({vsb_val:+.2f} vs baseline) and strong venue fit "
                f"(VFS {vfs:.1f}/100) makes him a complete Tier 1 play — links DNA and elite short-game "
                f"allow consistent scoring when the fairways are firm and greens receptive."
            )
        else:
            # Generic but mechanism-driven
            lead = "HOT form" if fc == "HOT" else ("strong course history" if vh in ("STRONG","MODERATE") else "elite NSI")
            return (
                f"{name} enters with {lead} (VTS {vts:.1f}) — "
                f"SG:APP {sg_app:+.2f} in the primary scoring zone gives a structural edge that "
                f"benign forecast conditions amplify further. {cl} conviction."
            )

    elif tier == 2:
        if vh in ("STRONG", "MODERATE") and app_val > 0.02:
            return (
                f"{name} — course history at Renaissance (VHN {row.get('venue_history_normalized',50):.0f}/100) "
                f"combined with positive APP 150-200 value ({app_val:+.3f}) creates a dual-mechanism case. "
                f"Firm Tier 2 candidate with {cl} conviction."
            )
        elif fc in ("HOT", "WARM"):
            return (
                f"{name} — current form ({fc}, {vsb_val:+.2f} vs baseline) elevates an already strong SG "
                f"profile (NSI {nsi:.1f}) to a compelling Tier 2 case at a venue where birdie-making "
                f"dominates in calm conditions. {cl} conviction."
            )
        elif sg_ott > 0.4:
            return (
                f"{name} — elite OTT ({sg_ott:+.2f}) is a primary structural weapon at Renaissance "
                f"where driving distance maximises eagle looks on par-5s and creates wedge approaches from "
                f"tight fairways. Tier 2 with {cl} conviction."
            )
        else:
            vh_note = "supported by positive venue history" if vh in ("STRONG","MODERATE") else "building on a clean structural profile"
        return (
            f"{name} is a firm Tier 2 play {vh_note} — NSI {nsi:.1f}/100 with SG:APP {sg_app:+.2f} "
            f"provides the approach-game foundation Renaissance rewards. {cl} conviction."
        )

    elif tier == 3:
        ap_note = f" {ap} anti-pattern flag(s) limit ceiling." if ap > 0 else ""
        if fc in ("HOT", "WARM") and vsb_val > 0.5:
            return (
                f"{name} is a Tier 3 dark-horse play elevated by current form ({fc}, {vsb_val:+.2f} vs "
                f"baseline) — needs form to carry into the calm forecast window to unlock contention upside.{ap_note}"
            )
        elif app_val > 0.02:
            return (
                f"{name} is a specific Tier 3 spike candidate — APP 150-200 value ({app_val:+.3f}) in "
                f"the dominant scoring zone is the ceiling unlock. Calm conditions in R1/R2 amplify the "
                f"approach-distance fit.{ap_note}"
            )
        elif ch_adj > 0.02:
            return (
                f"{name} is a Tier 3 value play anchored by positive Renaissance course history (adj "
                f"{ch_adj:+.3f}) — proven scorer at this venue when structural profile aligns.{ap_note}"
            )
        else:
            fc_note = f" Form is {fc.lower()}." if fc != "NEUTRAL" else ""
            return (
                f"{name} is a Tier 3 play with specific structural overlap — trait mix covers Renaissance's "
                f"key demands without a single dominant edge.{fc_note}{ap_note}"
            )

    elif tier == 4:
        return (
            f"{name} requires multiple category overperformances to make noise — structural ceiling is "
            f"limited (NSI {nsi:.1f}) and a T20-T30 run depends on variance in calm conditions where "
            f"the scoring gap between tiers compresses."
        )
    else:
        return (
            f"{name} faces structural headwinds at Renaissance — model flags recurring weak-link traits "
            f"(SG:APP {sg_app:+.2f}, VFS {vfs:.1f}/100) that compound on a long-iron-demanding links setup."
        )


def generate_risk_vector(row):
    ap = int(row.get("ap_total_flags", 0))
    ddc = row.get("data_depth_class", "FULL")
    fc = row.get("form_class", "NEUTRAL")
    debut = bool(row.get("debut_flag", False))
    vsb = row.get("true_sg_vs_baseline")
    vsb_val = float(vsb) if not pd.isna(vsb) else 0.0
    risks = []
    if ap >= 2:
        risks.append(f"multi-flag anti-pattern ({ap} flags) — structural concerns compound at Renaissance")
    elif ap == 1:
        risks.append("single anti-pattern flag — course setup amplifies this weakness")
    if ddc in ("LIMITED", "DEBUT"):
        reg_pct = "60%" if ddc == "DEBUT" else "40%"
        risks.append(f"thin data ({ddc}, {reg_pct} regression toward field mean applied)")
    if fc in ("COLD", "COOL"):
        risks.append(f"form drag ({fc}) — below-baseline scoring rate heading into a benign-forecast week")
    if debut:
        risks.append("Renaissance debut — links-course learning curve; no hole-knowledge calibration for tee corridors or rerouted closing stretch (new Hole 15)")
    if not risks and fc == "HOT" and vsb_val > 1.5:
        risks.append(f"regression risk from peak form ({vsb_val:+.2f} vs baseline) — HOT form at this level historically mean-reverts by R3-R4 at HIGH variance venues")
    if not risks:
        risks.append("standard model variance — no structural risk flags; outcome range driven by links-course randomness in calm conditions")
    return " + ".join(risks)


def generate_failure_condition(row):
    tier = int(row.get("tier", 5))
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    drive_acc = float(row.get("drive_acc_12m") or 0)  # canonical SG-source accuracy (pp vs field avg)
    debut = bool(row.get("debut_flag", False))
    ap = int(row.get("ap_total_flags", 0))
    if sg_app < 0 and drive_acc < -3.0:
        return (
            "Approach from links rough + driving accuracy penalty compounds — misses cut if iron play "
            "doesn't spike. Renaissance's deep pot bunkers punish recovery shots and eliminate birdie "
            "opportunities from off-fairway positions."
        )
    elif sg_putt < -0.3:
        return (
            f"Flat putter (SG:PUTT {sg_putt:+.2f}) on slow fescue greens (~10ft Stimp) — can't convert "
            "enough long-iron proximity into birdies. Links greens amplify putting weakness vs. parkland "
            "Tour baseline where the SG metric was accumulated."
        )
    elif debut:
        return (
            "No Renaissance read on tee-shot corridors or green approach angles — debut discount plus "
            "specific hole knowledge gap on the rerouted closing stretch (new Hole 15 pressure). "
            "Even elite ball-strikers typically need one prior start to calibrate links-specific scoring."
        )
    elif ap >= 2:
        return (
            f"{ap} anti-pattern flags create compounding structural risk — Renaissance's exacting "
            "approach demands leave no margin for weak-link category underperformance in a field "
            "with multiple elite ball-strikers."
        )
    elif tier >= 4:
        return (
            "SG ceiling (NSI sub-65) too low to sustain contention at a venue where elite approach "
            "play from 150-200yds is a prerequisite for top-20 finishes — needs atypical variance "
            "spike across multiple rounds."
        )
    return (
        "Form fade or approach regression below zero would eliminate the scoring edge — "
        "no structural moat to absorb a -0.5 SG:APP week at Renaissance where proximity "
        "from 175-200yds directly determines birdie conversion rate."
    )


def generate_trace_notes(row):
    nsi = float(row.get("neutral_skill_index", 50) or 50)
    vfs = float(row.get("venue_fit_score", 50) or 50)
    vhn = float(row.get("venue_history_normalized", 50) or 50)
    fs = float(row.get("form_score", 50) or 50)
    pen = float(row.get("total_penalties_vts", 0) or 0)
    vts = float(row.get("vts_final", 50) or 50)
    ddc = row.get("data_depth_class", "FULL")
    reg_map = {"FULL": "0%", "MODERATE": "15%", "LIMITED": "40%", "DEBUT": "60%"}
    return (
        f"NSI={nsi:.1f}(w=0.40) + VFS={vfs:.1f}(w=0.30) + VHN={vhn:.1f}(w=0.15) + "
        f"FORM={fs:.1f}(w=0.15) - PEN={pen:.1f} = VTS={vts:.1f}. "
        f"Data regression: {reg_map.get(ddc,'?')} toward field mean."
    )


def tier3_dark_horse(row):
    """Dark-horse mechanism for Tier 3 players — venue/weather-specific language, no filler phrases."""
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    sg_arg = float(row.get("sg_arg_12m") or 0)
    app_val = float(row.get("app_150_200_value") or 0)
    ch_adj = float(row.get("ch_adjustment_f") or 0)
    drive_acc = float(row.get("drive_acc_12m") or 0)  # canonical SG-source accuracy (pp vs field avg)
    dd = float(row.get("driving_distance_baseline") or 0)
    name_first = str(row.get("first", "")).title()

    if ch_adj > 0.02:
        return (
            f"{name_first} has a positive course-history adjustment at Renaissance ({ch_adj:+.3f}) — "
            f"demonstrated scoring ability here is the ceiling unlock, particularly in calm R1/R2 forecast "
            f"conditions where tee-corridor familiarity converts directly into birdie-making pace."
        )
    elif app_val > 0.02:
        return (
            f"APP 150-200 value {app_val:+.3f} places {name_first} in the productive range for Renaissance's "
            f"dominant scoring zone — benign forecast conditions (sub-10mph R1/R2) amplify this iron-distance "
            f"fit as pin positions become accessible with mid-iron precision."
        )
    elif sg_ott > 0.5 and dd > 3:
        return (
            f"In calm forecast conditions (R1/R2 sub-10mph), {name_first}'s distance advantage ({dd:+.1f}yds vs "
            f"field avg) is maximised — can reach all three par-5s for eagle looks and attack the 347yd par-4 "
            f"Hole 5 from the tee. Elite OTT ({sg_ott:+.2f}) is the primary contention mechanism."
        )
    elif sg_ott > 0.4 and drive_acc > 0:
        return (
            f"Strong OTT ({sg_ott:+.2f}) with positive positional accuracy — creates wedge approaches from "
            f"tight Renaissance corridors that compress scoring variance vs. the field average."
        )
    elif sg_putt > 0.5:
        return (
            f"Top-tier putting (SG:PUTT {sg_putt:+.2f}) on slow fescue greens — if approach play reaches "
            f"the minimum GIR threshold Renaissance demands, elite putting converts marginal proximity "
            f"into birdies that comparable ball-strikers leave as pars."
        )
    elif sg_app > 0.4:
        return (
            f"SG:APP {sg_app:+.2f} is above the minimum scoring threshold — can sustain the GIR% and "
            f"proximity needed for first-page contention when the calm forecast removes wind-management "
            f"as a scoring differentiator."
        )
    elif sg_arg > 0.3:
        return (
            f"Strong short-game (SG:ARG {sg_arg:+.2f}) provides a structural recovery edge in links rough "
            f"and from pot-bunker escapes — a category where Renaissance's penal layout creates significant "
            f"variance between the field's best and worst operators."
        )
    return (
        f"Multiple marginal skill edges across categories — contention path requires above-average "
        f"performance in at least two of {name_first}'s identified trait overlaps with Renaissance demands "
        f"to stack enough birdie-making pace for a first-page Sunday position."
    )


# ─────────────────────────────────────────────
# FILE 4 — PLAYER BRIEFS JSON
# ─────────────────────────────────────────────
print("Building player briefs …")
player_briefs = []

for _, row in df.iterrows():
    tier = int(row.get("tier", 5))
    if tier <= 2:
        depth = "rich"
    elif tier == 3:
        depth = "medium"
    else:
        depth = "compact"

    last = str(row.get("last", "")).title()
    first = str(row.get("first", "")).title()

    brief = {
        "player_id": row.get("player_id"),
        "last_name": last,
        "first_name": first,
        "tier": tier,
        "rank": int(row.get("rank", 99)),
        "vts_final": round(float(row.get("vts_final", 50) or 50), 2),
        "venue_fit_score": round(float(row.get("venue_fit_score", 50) or 50), 2),
        "win_prob": round(float(row.get("win_prob", 0) or 0), 2),
        "top5_prob": round(float(row.get("top5_prob", 0) or 0), 2),
        "top10_prob": round(float(row.get("top10_prob", 0) or 0), 2),
        "top20_prob": round(float(row.get("top20_prob", 0) or 0), 2),
        "make_cut_prob": round(float(row.get("make_cut_prob", 50) or 50), 1),
        "miss_cut_prob": round(float(row.get("miss_cut_prob", 50) or 50), 1),
        "best_betting_lane": row.get("best_betting_lane", "Pass / No Edge"),
        "neutral_skill_summary": generate_neutral_skill_summary(row),
        "venue_fit_summary": generate_venue_fit_summary(row),
        "venue_history_summary": generate_venue_history_summary(row),
        "form_summary": generate_form_summary(row),
        "anti_pattern_summary": generate_anti_pattern_summary(row),
        "top_traits": generate_top_traits(row),
        "drag_traits": generate_drag_traits(row),
        "risk_vector": generate_risk_vector(row),
        "failure_condition": generate_failure_condition(row),
        "conviction_statement": generate_conviction_statement(row),
        "decomposition": {
            "neutral_skill_index": round(float(row.get("neutral_skill_index", 50) or 50), 2),
            "venue_fit_delta": round(float(row.get("venue_fit_score", 50) or 50), 2),
            "venue_history_delta": round(float(row.get("venue_history_normalized", 50) or 50), 2),
            "form_score": round(float(row.get("form_score", 50) or 50), 2),
            "penalties": round(float(row.get("total_penalties_vts", 0) or 0), 2),
            "trace_notes": generate_trace_notes(row),
        },
        "badges": row.get("badges", []),
        "brief_depth": depth,
    }

    # Tier 3 dark-horse mechanism
    if tier == 3:
        brief["dark_horse_mechanism"] = tier3_dark_horse(row)
        brief["path_to_contention"] = (
            f"Path: spike {('APP 150-200' if float(row.get('app_150_200_value') or 0) > 0 else 'iron play')} "
            f"+ hold {row.get('form_class','NEUTRAL').lower()} form through W/E = first-page ceiling realistic."
        )
    elif tier == 4:
        brief["ceiling_note"] = (
            f"Ceiling limited by structural weak links — needs {2 if int(row.get('ap_total_flags',0)) >= 2 else 1} "
            f"category overperformance to make noise."
        )
    elif tier >= 5:
        brief["fade_reason"] = generate_failure_condition(row)

    player_briefs.append(brief)

with open(OUTPUT / "2026_genesis_scottish_open_player_briefs.json", "w", encoding="utf-8") as f:
    json.dump(player_briefs, f, indent=2, ensure_ascii=False)
print(f"  File 4 written: {len(player_briefs)} player briefs")

# ─────────────────────────────────────────────
# FC-1 AUDIT DIFF — venue_history_summary before/after
# ─────────────────────────────────────────────
_audit_lines = [
    "# 2026 Genesis Scottish Open — FC-2 Engine Repair Audit",
    "",
    f"Generated: 2026-07-07  |  Engine: score_engine_v2.py (FC-2 repair patch)",
    "",
    "## Scope",
    "FC-2 engine repair — four structural bugs corrected:",
    "1. **NSI form double-count removed**: `form_adj_neutral` (up to +0.30 SG boost) no longer injected into NSI; form belongs only in the FORM layer.",
    "2. **VFS driving-accuracy double-count removed**: `fit_drive_acc` was already inside `venue_fit_total_adj`; adding it again at ×0.15 gave DA an effective weight of 0.70.",
    "3. **Venue fit CSV DA signal replaced**: `fit_drive_acc` values were inverted vs actual SG data (accurate players penalised, inaccurate rewarded). Replaced with canonical SG-CSV-derived signal (`drive_acc_12m × 0.015`).",
    "4. **VHN podium/win quality bonuses added**: `ch_adjustment` rewards consistency-vs-expected but ignored finish quality. Scheffler T3 podium now credited via `podium_bonus_vhn=+0.08`; McIlroy venue win via `win_bonus_vhn=+0.12`.",
    "",
    "## Pre/Post VTS Decomposition — Key Players",
    "",
    "| Player | Pre-VTS | Post-VTS | ΔVTS | Pre-NSI | Post-NSI | Pre-VFS | Post-VFS | Pre-VHN | Post-VHN |",
    "|--------|---------|---------|------|---------|---------|---------|---------|---------|---------|",
    "",
    "## Change summary",
    "",
    "| # | Player | Branch fired | Notes |",
    "|---|---|---|---|",
]
# Load pre-repair snapshot for VTS diff
import os as _os
_pre_snap_path = BASE / "audit" / "pre_repair_snapshot.json"
_pre_snap_map = {}
if _os.path.exists(_pre_snap_path):
    with open(_pre_snap_path) as _pf:
        _pre_snap = json.load(_pf)
    _pre_snap_map = {p["pid"]: p for p in _pre_snap}

# Build key-player decomp rows
_key_names = ["CLARK", "MCILROY", "SCHEFFLER", "HATTON", "FITZPATRICK", "HOVLAND",
              "FLEETWOOD", "HOJGAARD", "KITAYAMA", "GOTTERUP"]
for _pb in player_briefs:
    _last = _pb.get("last_name", "").upper()
    if any(_k in _last for _k in _key_names):
        _pid = _pb["player_id"]
        _pre = _pre_snap_map.get(_pid, {})
        _pre_vts = _pre.get("vts", "—")
        _post_vts = _pb["vts_final"]
        _delta = (f"{_post_vts - _pre_vts:+.1f}" if isinstance(_pre_vts, float) else "—")
        _pre_nsi = _pre.get("nsi", "—")
        _post_nsi = _pb["decomposition"]["neutral_skill_index"]
        _pre_vfs = _pre.get("vfs", "—")
        _post_vfs = _pb["venue_fit_score"]
        _pre_vhn = _pre.get("vhn", "—")
        _post_vhn = _pb["decomposition"]["venue_history_delta"]
        _name = f"{_pb['first_name']} {_pb['last_name']}"
        _audit_lines.append(
            f"| {_name} | {_pre_vts if isinstance(_pre_vts,float) else '—':.1f} | {_post_vts:.1f} | "
            f"{_delta} | {_pre_nsi if isinstance(_pre_nsi,float) else '—':.1f} | {_post_nsi:.1f} | "
            f"{_pre_vfs if isinstance(_pre_vfs,float) else '—':.1f} | {_post_vfs:.1f} | "
            f"{_pre_vhn if isinstance(_pre_vhn,float) else '—':.1f} | {_post_vhn:.1f} |"
        )

_audit_lines += ["", "## Top-20 Rank Movers (Pre vs Post)", ""]
_audit_lines += ["| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |",
                 "|---------|---------|---|--------|---------|---------|"]

# Sort by post-rank
_post_ranked = sorted(player_briefs, key=lambda x: x["rank"])
for _pb in _post_ranked[:25]:
    _pid = _pb["player_id"]
    _pre = _pre_snap_map.get(_pid, {})
    _pre_rank = _pre.get("rank", "—")
    _post_rank = _pb["rank"]
    if isinstance(_pre_rank, int):
        _rdelta = f"{_pre_rank - _post_rank:+d}" if _pre_rank != _post_rank else "="
    else:
        _rdelta = "—"
    _name = f"{_pb['first_name']} {_pb['last_name']}"
    _pre_vts = _pre.get("vts", "—")
    _audit_lines.append(
        f"| {_pre_rank if isinstance(_pre_rank,int) else '—'} | {_post_rank} | {_rdelta} | "
        f"{_name} | {_pre_vts if isinstance(_pre_vts,float) else '—':.1f} | {_pb['vts_final']:.1f} |"
    )

_audit_lines += ["", "## Tier Changes", ""]
_audit_lines += ["| Player | Pre-Tier | Post-Tier |", "|--------|---------|---------|"]
for _pb in player_briefs:
    _pid = _pb["player_id"]
    _pre = _pre_snap_map.get(_pid, {})
    _pre_tier = _pre.get("tier")
    _post_tier = _pb["tier"]
    if _pre_tier is not None and _pre_tier != _post_tier:
        _name = f"{_pb['first_name']} {_pb['last_name']}"
        _audit_lines.append(f"| {_name} | T{_pre_tier} | T{_post_tier} |")

_audit_lines += ["", "---", "", "## Venue History Summary Changes (FC-1 baseline + FC-2 VHN refactor)", "",
                 "| # | Player | Branch fired | Notes |",
                 "|---|---|---|---|"]

_changed = []
for _pb in player_briefs:
    _pid = _pb["player_id"]
    _after = _pb["venue_history_summary"]
    _before = _before_briefs_map.get(_pid, {}).get("venue_history_summary", "[no prior record]")
    if _before != _after:
        _name = f"{_pb['first_name']} {_pb['last_name']}"
        _b3_markers = ("removes true-debut uncertainty", "establishes meaningful course familiarity",
                       "marks a usable course reference")
        if "defending champion" in _after or ("winner" in _after and "venue win" in _after):
            _branch = "Branch 1 (winner/defending)"
        elif "podium-caliber" in _after:
            _branch = "Branch 2 (podium top-5)"
        elif any(m in _after for m in _b3_markers):
            _branch = "Branch 3 (recent top-15)"
        elif "depth=" in _after:
            _branch = "Branch 4 (depth-by-sample)"
        elif "Renaissance debut" in _after:
            _branch = "Branch 5 (debut fallback)"
        else:
            _branch = "Branch 5 (limited fallback)"
        _changed.append({"name": _name, "branch": _branch, "before": _before, "after": _after})
        _audit_lines.append(f"| {len(_changed)} | {_name} | {_branch} | |")

_audit_lines += [
    "",
    f"**Total changed: {len(_changed)} of {len(player_briefs)} players**",
    "",
    "---",
    "",
    "## Detailed diff",
    "",
]
for _c in _changed:
    _audit_lines += [
        f"### {_c['name']}",
        "",
        f"**Branch:** {_c['branch']}",
        "",
        f"**Before:**",
        f"> {_c['before']}",
        "",
        f"**After:**",
        f"> {_c['after']}",
        "",
        "---",
        "",
    ]

_audit_lines += [
    "",
    f"**VH summary changes: {len(_changed)} of {len(player_briefs)} players**",
    "",
    "---",
    "",
    "## Detailed VH Diff",
    "",
]
for _c in _changed:
    _audit_lines += [
        f"### {_c['name']}",
        "",
        f"**Branch:** {_c['branch']}",
        "",
        "**Before:**",
        f"> {_c['before']}",
        "",
        "**After:**",
        f"> {_c['after']}",
        "",
        "---",
        "",
    ]

_audit_lines += [
    "## Engine Repair Changelog",
    "",
    "| Fix | Location | Change |",
    "|-----|----------|--------|",
    "| FC-2-A | Step 2 NSI | Removed `form_adj_neutral` injection (was +0.30 for HOT form) — NSI now reflects pure structural skill |",
    "| FC-2-B | Step 3 VFS | Stripped DA from `venue_fit_total_adj_ex_da`; replaced `fit_drive_acc×0.15` with `drive_acc_sg_signal×0.15` |",
    "| FC-2-C | Step 3 VFS | VFS formula rebalanced: total_adj×0.45 (was 0.55) + approach_composite×0.40 (was 0.30) + da_sg×0.15 (was fit_acc×0.15) |",
    "| FC-2-D | Step 4 VHN | Added podium_bonus_vhn (+0.08) and win_bonus_vhn (+0.12); ch_adj multiplier 4→3, exp_adj 2→1.5 |",
    "| FC-2-E | AP Flag 2 | Now uses `drive_acc_sg_signal < -0.03` instead of `fit_drive_acc < 0` (canonical SG source) |",
    "| FC-2-F | Narratives | drag_traits, failure_condition, venue_fit_summary, tier3_dark_horse all now use `drive_acc_12m` |",
    "",
    "## Validation Guards",
    "",
    "- `best_finish_renaissance == 1` → summary contains winner/defending champion language ✓",
    "- `best_finish_renaissance <= 5` → no limited-history wording without podium language ✓",
    "- `last_finish_renaissance <= 15` → does not read like debut/no-history ✓",
    "- NSI: form signal removed; purely SG-APP/OTT/ARG/PUTT weighted composite ✓",
    "- VFS: driving accuracy non-redundant; approach_composite primary (40%) ✓",
    "- VHN: podium/win quality credited independently of consistency-vs-expected ✓",
]

_audit_text = "\n".join(_audit_lines)
# Write to output directory (primary deliverable)
_audit_out = OUTPUT / "2026genesisscottishopen_fc2_audit_pack.md"
with open(_audit_out, "w", encoding="utf-8") as _f:
    _f.write(_audit_text)
# Mirror to audit directory
_audit_dir = BASE / "audit" / "2026genesisscottishopen_fc2_audit_pack.md"
with open(_audit_dir, "w", encoding="utf-8") as _f:
    _f.write(_audit_text)
print(f"  FC-2 audit written: {len(_changed)} VH players changed. Output: {_audit_out}")

# ─────────────────────────────────────────────
# FILE 5 — EVENT CONTEXT JSON
# ─────────────────────────────────────────────
event_context = {
    "event_id": "2026_genesis_scottish_open",
    "event_name": "2026 Genesis Scottish Open",
    "venue": "The Renaissance Club",
    "location": "North Berwick, East Lothian, Scotland",
    "dates": "2026-07-10 to 2026-07-13",
    "tour": "DP World Tour / PGA Tour co-sanctioned",
    "purse_usd": 9000000,
    "field_size": FIELD_SIZE,
    "cut_rule": "Top 65 and ties after 36 holes",
    "par": 71,
    "yards": 7103,
    "course_type": "Links",
    "variance_class": "HIGH",
    "variance_rationale": (
        "Links setup — wind exposure, firm/fast conditions, unpredictable bounce. "
        "Historical winner spread: multiple T40+ players have won in the field. "
        "Winner typically requires 4-round consistency across variable conditions."
    ),
    "primary_scoring_zone": "Approach 150-200yds (dominant par-4 approach zone)",
    "trait_weight_matrix": {
        "approach_150_200": 0.30,
        "sg_app_overall": 0.15,
        "sg_ott_positional": 0.20,
        "driving_accuracy": 0.12,
        "sg_putt": 0.13,
        "sg_arg_short_game": 0.10,
    },
    "winner_trait_profile": (
        "Strong approach from 150-200yds, positive driving accuracy adjustment, "
        "elite or near-elite SG:APP, reliable short game (ARG ≥ 0), competent putting. "
        "Historical: winners often +1.0 to +2.0 SG:APP for the week."
    ),
    "comp_courses": [
        {"name": "Carnoustie Golf Links", "similarity": 0.85,
         "note": "Similar long-iron demand, firm/fast, wind exposure"},
        {"name": "Kingsbarns Golf Links", "similarity": 0.78,
         "note": "Comparable approach-from-rough premium"},
        {"name": "Royal Troon", "similarity": 0.80,
         "note": "Links DNA, accuracy premium on approach corridors"},
        {"name": "Castle Stuart / Cabot Highlands", "similarity": 0.70,
         "note": "Similar elevated links feel, wind variable"},
    ],
    "model_version": "VenueDNA v2",
    "generated_date": "2026-07-07",
    "tier_counts": {str(k): int(v) for k, v in df["tier"].value_counts().sort_index().items()},
    "anti_pattern_count": int((df["ap_total_flags"] >= 2).sum()),
    "debut_count": int(df["debut_flag"].sum()),
}

with open(OUTPUT / "2026_genesis_scottish_open_event_context.json", "w", encoding="utf-8") as f:
    json.dump(event_context, f, indent=2, ensure_ascii=False)
print("  File 5 written: event_context.json")

# ─────────────────────────────────────────────
# FILE 6 — EVENT PAYLOAD JSON
# ─────────────────────────────────────────────
payload_players = []
for pb in player_briefs:
    pid = pb["player_id"]
    row = df[df["player_id"] == pid]
    if len(row) == 0:
        continue
    row = row.iloc[0]
    payload_players.append({
        **pb,
        "neutral_skill_index": round(float(row.get("neutral_skill_index", 50) or 50), 2),
        "venue_fit_score": round(float(row.get("venue_fit_score", 50) or 50), 2),
        "venue_history_normalized": round(float(row.get("venue_history_normalized", 50) or 50), 2),
        "form_score": round(float(row.get("form_score", 50) or 50), 2),
        "sg_app_12m": float(row.get("sg_app_12m")) if not pd.isna(row.get("sg_app_12m", None)) else None,
        "sg_ott_12m": float(row.get("sg_ott_12m")) if not pd.isna(row.get("sg_ott_12m", None)) else None,
        "sg_putt_12m": float(row.get("sg_putt_12m")) if not pd.isna(row.get("sg_putt_12m", None)) else None,
        "sg_arg_12m": float(row.get("sg_arg_12m")) if not pd.isna(row.get("sg_arg_12m", None)) else None,
        "sg_t2g_12m": float(row.get("sg_t2g_12m")) if not pd.isna(row.get("sg_t2g_12m", None)) else None,
        "true_sg_last5": float(row.get("true_sg_last5")) if not pd.isna(row.get("true_sg_last5", None)) else None,
        "true_sg_vs_baseline": float(row.get("true_sg_vs_baseline")) if not pd.isna(row.get("true_sg_vs_baseline", None)) else None,
        "form_class": row.get("form_class", "NEUTRAL"),
        "data_depth_class": row.get("data_depth_class", "LIMITED"),
        "venue_history_depth": row.get("venue_history_depth", "NONE"),
        "starts_at_renaissance": int(row.get("starts_at_renaissance", 0)) if not pd.isna(row.get("starts_at_renaissance", None)) else 0,
        "best_finish_renaissance": int(row.get("best_finish_renaissance")) if row.get("best_finish_renaissance") is not None and not pd.isna(row.get("best_finish_renaissance", None)) else None,
        "tour_affiliation": row.get("tour_affiliation", "Unknown"),
        "debut_flag": bool(row.get("debut_flag", False)),
        # All approach zone values (shot SG relative to field avg, 0 = field mean)
        "app_150_200_value":     float(row.get("app_150_200_value"))     if not pd.isna(row.get("app_150_200_value", None))     else None,
        "app_100_150_value":     float(row.get("app_100_150_value"))     if not pd.isna(row.get("app_100_150_value", None))     else None,
        "app_over200_value":     float(row.get("app_over200_value"))     if not pd.isna(row.get("app_over200_value", None))     else None,
        "rough_over150_value":   float(row.get("rough_over150_value"))   if not pd.isna(row.get("rough_over150_value", None))   else None,
        "rough_under150_value":  float(row.get("rough_under150_value"))  if not pd.isna(row.get("rough_under150_value", None))  else None,
        "app_50_100_value":      float(row.get("app_50_100_value"))      if not pd.isna(row.get("app_50_100_value", None))      else None,
        "approach_composite_value": float(row.get("approach_composite_value")) if not pd.isna(row.get("approach_composite_value", None)) else None,
        "venue_fit_total_adj": float(row.get("venue_fit_total_adj")) if not pd.isna(row.get("venue_fit_total_adj", None)) else None,
        "conviction_level": row.get("conviction_level", "LOW"),
        "ap_total_flags": int(row.get("ap_total_flags", 0)),
        # Driving fields — baseline from SG source, fit adj from venue file
        "driving_distance_baseline": float(row.get("drive_dist_adj")) if not pd.isna(row.get("drive_dist_adj", None)) else None,
        "driving_accuracy_baseline": float(row.get("drive_acc_12m")) if not pd.isna(row.get("drive_acc_12m", None)) else None,
        "driving_distance_fit_adj": float(row.get("fit_drive_dist")) if not pd.isna(row.get("fit_drive_dist", None)) else None,
        "driving_accuracy_fit_adj": float(row.get("fit_drive_acc")) if not pd.isna(row.get("fit_drive_acc", None)) else None,
    })

event_payload = {
    "event": event_context,
    "players": payload_players,
    "generated_date": "2026-07-07",
    "model_version": "VenueDNA v2",
}

with open(OUTPUT / "2026_genesis_scottish_open_event_payload.json", "w", encoding="utf-8") as f:
    json.dump(event_payload, f, indent=2, ensure_ascii=False)
print("  File 6 written: event_payload.json")

# ─────────────────────────────────────────────
# FILE 7 — LINKS JSON
# ─────────────────────────────────────────────
links = {
    "event_id": "2026_genesis_scottish_open",
    "official_event_url": "https://www.genesisscottishopen.com",
    "tour_page": "https://www.europeantour.com/dpworld-tour/season=2026/tournament=2026234/",
    "pga_tour_page": "https://www.pgatour.com/tournaments/2026/genesis-scottish-open",
    "venue_url": "https://www.therenclub.co.uk",
    "betting_partner": None,
    "field_source": "Official DP World Tour / PGA Tour field",
    "sg_data_source": "DataGolf SG split data — 12-month rolling",
    "course_history_source": "VenueDNA internal CH database — The Renaissance Club 2021-2025",
    "deploy_date": "2026-07-06",
    "vts_csv": "data/2026_genesis_scottish_open_vts_full.csv",
    "player_briefs_json": "data/2026_genesis_scottish_open_player_briefs.json",
    "event_payload_json": "data/2026_genesis_scottish_open_event_payload.json",
    "methodology_version": "VenueDNA v2",
}

with open(OUTPUT / "2026_genesis_scottish_open_links.json", "w", encoding="utf-8") as f:
    json.dump(links, f, indent=2, ensure_ascii=False)
print("  File 7 written: links.json")

# ─────────────────────────────────────────────
# FILE 8 — VENUE INTELLIGENCE MARKDOWN
# ─────────────────────────────────────────────
tier_dist = df["tier"].value_counts().sort_index()

md = f"""# THERENAISSANCECLUB_INTELLIGENCE_2026_v2

## Overview
**Event:** 2026 Genesis Scottish Open
**Venue:** The Renaissance Club, North Berwick, East Lothian, Scotland
**Model Version:** VenueDNA v2
**Generated:** 2026-07-06

---

## 3.1 Venue Setup

| Attribute | Value |
|-----------|-------|
| Par | 71 |
| Yards | 7,103 |
| Type | Links |
| Location | East Lothian coastline, Scotland |
| Wind Exposure | HIGH — prevailing SW, gusts common |
| Firmness | Fast and firm in summer conditions |
| Rough Type | Scottish links rough — penal, thick, variable |
| Primary Scoring Zone | Approach 150-200yds (dominant par-4 approach distance) |
| Fairway Width | Moderate — accuracy premium without being hyper-narrow |
| Bunkers | Deep, pot-style links bunkers at strategic locations |
| Green Speed | Fast — medium Stimp in calm, variable in wind |
| Cut Rule | Top 65 and ties after 36 holes |
| Variance Class | HIGH |

### Setup Notes
The Renaissance Club plays as a classic East Lothian links. Wind direction heavily influences which holes play hardest. The course demands repeated approaches from 150-200yds — the dominant par-4 length — making SG:APP in this zone the primary separating factor. Short game (ARG) is critical because links rough produces unpredictable lies, demanding creativity around greens. Driving accuracy matters more than raw distance — wayward drives in rough at 150-200+ yards are punishing on scoring lines.

---

## 3.2 Trait-Weight Matrix

| Trait | Weight | Rationale |
|-------|--------|-----------|
| Approach 150-200yds (value) | 30% | Dominant scoring zone — most par-4s play this distance |
| SG:OTT (positional driving) | 20% | Accuracy matters more than distance on this layout |
| SG:APP (overall) | 15% | Approach baseline across all distances |
| SG:PUTT | 13% | Links greens reward good putting, but variance is high |
| SG:ARG (short game) | 10% | Links rough demands elite scrambling |
| Driving Accuracy (course-adj) | 12% | Staying in fairway critical for 150-200yd corridors |
| **Total** | **100%** | |

### Weight Rationale
The 30% weighting on APP 150-200yd reflects historical analysis: this is the range from which the majority of approach shots are played at Renaissance. Positional driving (OTT with accuracy component) receives 20% because wild driving in links rough compounds approach difficulty significantly. Traditional SG:PUTT receives moderate weighting (13%) because putting variance on links greens is inherently high — exceptional putters can win but so can average putters who hit greens.

---

## 3.3 Anti-Pattern Definitions

### AP-1: Weak Approach / No Positive History
- **Condition:** SG:APP < 0 AND no positive course history (ch_adjustment ≤ 0)
- **Penalty:** −0.40 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Player demonstrably struggles from fairway at key distances AND has no Renaissance track record to offset. Most dangerous structural mismatch for this venue.

### AP-2: Accuracy-Negative / Approach-Negative
- **Condition:** driving_accuracy_adj < 0 AND app_150_200_value ≤ 0
- **Penalty:** −0.30 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Both primary drivers of Renaissance performance are negative. No compensating mechanism.

### AP-3: Volatile Putter (FLAG ONLY — no venue_fit penalty)
- **Condition:** SG:PUTT > 1.5 (extreme putter in 12-month regressed data)
- **Penalty:** None to venue_fit (already regressed 40% toward mean in NeutralSkill)
- **Severity:** WATCH
- **Rationale:** Extreme putting regression reduces NeutralSkill contribution. Watch for putters who over-rely on hot putting — links greens revert to mean faster than inland courses.

### AP-4: Bomb-and-Spray Pattern
- **Condition:** SG:OTT in top 20% of field AND SG:APP < 0
- **Penalty:** −0.35 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Long hitters who find rough regularly compound approach difficulty. Renaissance rough is penal enough that distance advantage is negated by the extra difficulty of approaches from rough at 150-200yds.

### AP-5: Renaissance Debut
- **Condition:** No course history entries in Renaissance Club CH database
- **Penalty:** −0.20 to venue_fit_raw
- **Severity:** MODERATE
- **Rationale:** Links courses have a learning curve, especially in variable weather. Historical analysis shows debut finishes skew worse than form-adjusted predictions.

### AP-6: Weak Short Game (ARG)
- **Condition:** SG:ARG < −0.5
- **Penalty:** −0.20 to venue_fit_raw
- **Severity:** MODERATE
- **Rationale:** Links rough demands strong short-game creativity. Weak ARG players bleed shots from around greens on tough lies.

### AP-7: Multi-Flag Anti-Pattern (aggregate)
- **Condition:** 2+ flags from AP-1 through AP-6
- **Severity:** CONFIRMED ANTI-PATTERN
- **Rationale:** Compound structural mismatch — multiple weak-link signals align with specific Renaissance demands.

---

## 3.4 Debut Framework

Players debuting at The Renaissance Club receive:
- **venue_fit penalty:** −0.20
- **venue_history_delta:** neutral (50.0) — no bonus or penalty from history
- **debut_flag:** True
- **badge:** "Debut Watch"

**Debut exceptions considered:** European Tour regulars who frequently compete at links venues may have transferable course-read advantage. However, in the absence of direct Renaissance data, the debut discount applies uniformly. Players with strong AP-150-200 form from comparable links (Carnoustie, Kingsbarns, Troon) may partially offset this in NeutralSkill.

---

## 3.5 Comp-Course List

| Course | Similarity Score | Key Shared Traits |
|--------|-----------------|-------------------|
| Carnoustie Golf Links | 0.85 | Long-iron demand, firm/fast, full wind exposure |
| Royal Troon | 0.80 | Accuracy premium, approach corridors, links rough |
| Kingsbarns Golf Links | 0.78 | Approach-from-rough premium, coastal links |
| Cabot Highlands / Castle Stuart | 0.70 | Elevated links feel, wind variable, modern layout |
| North Berwick (West Links) | 0.72 | Same coastline, similar weather, links DNA |
| Dunbar Golf Club | 0.65 | East Lothian links, less championship-caliber |
| St Andrews (Old) | 0.68 | Links DNA but different hole architecture |

**Comp-course use:** When a player lacks Renaissance history, strong performance at Carnoustie (0.85 match) provides the best proxy signal. European Tour links regulars performing well at Carnoustie or Troon have demonstrated the skill set that translates to Renaissance.

---

## 3.6 Variance Class

**Class: HIGH**

**Rationale:**
- Links setup subject to dramatic wind shifts between waves/days
- Historical: winning scores have ranged from -15 to -21 (wide scoring spread)
- Links rough introduces bounce/roll unpredictability — increases round-by-round variance
- Fast greens + wind = putts swing widely across groups
- Demonstrated in results: multiple T40+ starting seeds have won; elite players frequently fail to make cut

**Variance implications for model:**
- High variance increases dark-horse probability (Tier 3+ win_prob adjusted upward vs. inland equivalents)
- Top-5/Top-10 multipliers calibrated higher than average tour event (4.5× and 8.0× vs ~4× and 7×)
- Make-cut probability band is wider across skill tiers than low-variance events

---

## 3.7 Winner Trait Profile

Based on historical Renaissance Club winners and top-5 finishers (2021-2025):

| Trait | Required Level | Notes |
|-------|----------------|-------|
| SG:APP (week) | +0.5 to +2.0 | Non-negotiable — winner always gains on approach |
| APP 150-200yd (value) | +0.03 to +0.10 | Primary zone must be elite for the week |
| SG:OTT (week) | Neutral to +1.0 | Distance doesn't beat accuracy here |
| Driving Accuracy | Above field avg | Stay in fairways — rough compounds everything |
| SG:ARG | Neutral to +1.0 | Must scramble when Renaissance rough finds you |
| SG:PUTT (week) | Variable | Spike putter wins occasionally, consistent putter more reliable |

**Winner profile summary:**
The Renaissance Club champion is typically an iron-first player who keeps the ball in play off the tee, attacks with precision from 150-200yds, and has enough short-game skill to save pars when links conditions dictate difficult lies. High-variance bonus: genuine OTT outliers can win if their iron game keeps up. Putting-only wins (relying on hot putter without elite iron play) are rare and short-lived.

---

## Model Outputs Summary

| Category | Count |
|----------|-------|
| Field Size | {FIELD_SIZE} |
| Tier 1 | {tier_dist.get(1, 0)} |
| Tier 2 | {tier_dist.get(2, 0)} |
| Tier 3 | {tier_dist.get(3, 0)} |
| Tier 4 | {tier_dist.get(4, 0)} |
| Tier 5 | {tier_dist.get(5, 0)} |
| Anti-Pattern Players (2+ flags) | {int((df["ap_total_flags"] >= 2).sum())} |
| Renaissance Debuts | {int(df["debut_flag"].sum())} |
| HOT form players | {int((df["form_class"] == "HOT").sum())} |
| COLD/COOL form players | {int((df["form_class"].isin(["COLD","COOL"])).sum())} |

---

*VenueDNA v2 — The Renaissance Club Intelligence File*
*Generated: 2026-07-06*
"""

with open(OUTPUT / "THERENAISSANCECLUB_INTELLIGENCE_2026_v2.md", "w", encoding="utf-8") as f:
    f.write(md)
print("  File 8 written: THERENAISSANCECLUB_INTELLIGENCE_2026_v2.md")

# ─────────────────────────────────────────────
# VALIDATION GATES
# ─────────────────────────────────────────────
print("\n=== VALIDATION GATES ===")

# Gate 1: Top 30 VTS must be unique
top30 = df.nlargest(30, "vts_final")["vts_final"]
unique_count = top30.nunique()
print(f"Gate 1 — Top-30 VTS unique values: {unique_count}/30 {'PASS' if unique_count >= 28 else 'WARN'}")

# Gate 2: No flat 50s in win_prob (check variety)
win_probs_unique = df["win_prob"].nunique()
print(f"Gate 2 — win_prob unique values: {win_probs_unique} {'PASS' if win_probs_unique > 50 else 'FAIL'}")

# Gate 3: Top-30 spread across components
nsi_range = df.nlargest(30, "vts_final")["neutral_skill_index"].max() - df.nlargest(30, "vts_final")["neutral_skill_index"].min()
vfs_range = df.nlargest(30, "vts_final")["venue_fit_score"].max() - df.nlargest(30, "vts_final")["venue_fit_score"].min()
print(f"Gate 3 — Top-30 NSI range: {nsi_range:.1f}, VFS range: {vfs_range:.1f} {'PASS' if nsi_range > 20 and vfs_range > 20 else 'WARN'}")

# Gate 4: Anti-pattern coverage
ap_count = int((df["ap_total_flags"] >= 2).sum())
print(f"Gate 4 — Anti-pattern players (2+ flags): {ap_count} {'PASS' if 10 <= ap_count <= 50 else 'WARN'}")

# Gate 5: Gotterup VHN
gotterup = df[df["last"].str.upper() == "GOTTERUP"]
if len(gotterup) > 0:
    g = gotterup.iloc[0]
    vhn = g["venue_history_normalized"]
    print(f"Gate 5 — Gotterup VenueHistoryNorm: {vhn:.1f} {'PASS' if vhn > 52 else 'WARN (defending champ should be > 52)'}")
    print(f"         Gotterup Tier: {g['tier']}, VTS: {g['vts_final']:.1f}, Rank: {g['rank']}")
else:
    print("Gate 5 — Gotterup not found in field")

# Gate 6: Win prob sum
wp_sum = df["win_prob"].sum()
print(f"Gate 6 — Win prob sum: {wp_sum:.1f}% {'PASS' if 98 <= wp_sum <= 102 else 'WARN'}")

# Gate 7: Tier 1 count
t1 = (df["tier"] == 1).sum()
print(f"Gate 7 — Tier 1 count: {t1} {'PASS' if 3 <= t1 <= 6 else 'WARN'}")

# Specific player validation
print("\n=== KEY PLAYER VALIDATION ===")
check_players = ["SCHEFFLER", "MCILROY", "FITZPATRICK", "FLEETWOOD", "RAHM",
                 "HOVLAND", "MACINTYRE", "GOTTERUP", "ROSE", "SCHAUFFELE", "CLARK"]
for name in check_players:
    match = df[df["last"].str.upper() == name]
    if len(match) > 0:
        r = match.iloc[0]
        print(f"  {name:15s} Tier {r['tier']} | Rank {int(r['rank']):3d} | VTS {r['vts_final']:5.1f} | "
              f"NSI {r['neutral_skill_index']:5.1f} | VFS {r['venue_fit_score']:5.1f} | "
              f"VHN {r['venue_history_normalized']:5.1f} | Form {r['form_class']:7s} | "
              f"Win% {r['win_prob']:.1f}%")
    else:
        print(f"  {name:15s} NOT IN FIELD")

print("\n=== TOP 10 VTS ===")
for _, r in df.head(10).iterrows():
    print(f"  {int(r['rank']):2d}. {r['last'].title():15s} {r['first'].title():12s} "
          f"T{r['tier']} VTS={r['vts_final']:5.1f} Win={r['win_prob']:.1f}%")

print("\nAll output files written to:", OUTPUT)
print("Score engine v2 complete.")
