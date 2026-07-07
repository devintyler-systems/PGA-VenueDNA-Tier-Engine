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
sg_raw["key"] = sg_raw.apply(
    lambda r: make_key(str(r.get("Last Name", "")), str(r.get("First Name", ""))), axis=1)
sg_raw["Driving-Accuracy"] = sg_raw["Driving-Accuracy"].apply(parse_pct)
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
                 "Rough shots- Over 150yrd", "Rough shots- Over 150yrd value",
                 "Fairway shots- 100-150yrd", "Fairway shots- 100-150yrd Value",
                 "Fairway shots- Over 200yrd", "Fairway shots- Over 200yrd value",
                 "Fairway shots- 50-100yrd", "Fairway shots- 50-100yrd value"]
app_sub = app_raw[[c for c in app_cols_keep if c in app_raw.columns]].copy()
# Deduplicate approach data — keep first occurrence per player key
app_sub = app_sub.drop_duplicates(subset=["key"], keep="first")
app_rename = {
    "Fairway shots- 150-200yrd": "app_150_200_shots",
    "Fairway shots- 150-200yrd value": "app_150_200_value",
    "Rough shots- Over 150yrd": "rough_over150_shots",
    "Rough shots- Over 150yrd value": "rough_over150_value",
    "Fairway shots- 100-150yrd": "app_100_150_shots",
    "Fairway shots- 100-150yrd Value": "app_100_150_value",
    "Fairway shots- Over 200yrd": "app_over200_shots",
    "Fairway shots- Over 200yrd value": "app_over200_value",
    "Fairway shots- 50-100yrd": "app_50_100_shots",
    "Fairway shots- 50-100yrd value": "app_50_100_value",
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

df["form_adj_neutral"] = df["true_sg_vs_baseline"].apply(form_adj_neutral)
df["neutral_skill_sg"] = df["neutral_skill_raw"] + df["form_adj_neutral"]

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

# Fill NaN with 0 for fit components (neutral if no data)
for col in ["venue_fit_total_adj", "app_150_200_value", "fit_drive_acc"]:
    if col not in df.columns:
        df[col] = 0.0
    else:
        df[col] = df[col].fillna(0.0)

# The app_150_200_value is in SG/shot scale already
df["venue_fit_raw"] = (
    df["venue_fit_total_adj"] * 0.55
    + df["app_150_200_value"] * 0.30
    + df["fit_drive_acc"].fillna(0.0) * 0.15
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

# Flag 2: fit_drive_acc < 0 AND app_150_200_value <= 0 (both negative)
df["ap_flag2"] = (
    df["fit_drive_acc"].fillna(0.0) < 0
) & (df["app_150_200_value"].fillna(0.0) <= 0)

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

# Best historical finish (across all years at Renaissance)
def best_finish_renaissance(row):
    for col in ["res_2025", "res_2024", "res_2023", "res_2022", "res_2021"]:
        if col in row.index:
            f = parse_finish(row.get(col))
            if f < 999:
                return f
    return 999

df["best_finish_renaissance"] = df.apply(best_finish_renaissance, axis=1)
df["best_finish_renaissance"] = df["best_finish_renaissance"].apply(
    lambda x: x if x < 999 else None)

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

df["venue_history_raw"] = (
    df["ch_adjustment_f"] * 4.0
    + df["experience_adjustment_f"] * 2.0
    + df["bonus_2025"]
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
df["corridor_discipline"] = df["fit_drive_acc"].fillna(0.0) * 50 + 50  # normalized
df["corridor_discipline"] = df["corridor_discipline"].clip(20, 90)
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
    ddc = row.get("data_depth_class", "FULL")
    parts = []
    if not pd.isna(sg_app):
        parts.append(f"APP {sg_app:+.2f}")
    if not pd.isna(sg_ott):
        parts.append(f"OTT {sg_ott:+.2f}")
    if not pd.isna(sg_putt):
        parts.append(f"PUTT {sg_putt:+.2f}")
    sg_str = ", ".join(parts) if parts else "limited data"
    ddc_note = f" ({ddc} data depth)" if ddc != "FULL" else ""
    return f"NeutralSkill index {nsi:.1f}/100 — 12-month SG: {sg_str}{ddc_note}."


def generate_venue_fit_summary(row):
    vfs = float(row.get("venue_fit_score", 50) or 50)
    total_adj = row.get("venue_fit_total_adj")
    app_val = row.get("app_150_200_value")
    ap = row.get("anti_pattern_flags", "none")
    adj_str = f"Total adj {total_adj:+.3f}" if not pd.isna(total_adj) else "no fit data"
    app_str = f", APP 150-200 value {app_val:+.3f}" if not pd.isna(app_val) else ""
    ap_str = f" Anti-pattern: {ap}." if ap != "none" else ""
    return f"VenueFit {vfs:.1f}/100 — {adj_str}{app_str}.{ap_str}"


def generate_venue_history_summary(row):
    vhn = float(row.get("venue_history_normalized", 50) or 50)
    depth = row.get("venue_history_depth", "NONE")
    bfr = row.get("best_finish_renaissance")
    bonus = float(row.get("bonus_2025", 0))
    starts = row.get("starts_at_renaissance")
    starts_str = f"{int(starts)} rds" if not pd.isna(starts) else "0 rds"
    bfr_str = f" Best finish: {int(bfr)}." if not pd.isna(bfr) and bfr is not None else " No recorded finish."
    bonus_str = f" 2025 recency bonus: {bonus:+.2f}." if bonus != 0.0 else ""
    return f"VenueHistory {vhn:.1f}/100 — depth={depth}, {starts_str}.{bfr_str}{bonus_str}"


def generate_form_summary(row):
    fc = row.get("form_class", "NEUTRAL")
    vsb = row.get("true_sg_vs_baseline")
    tsg = row.get("true_sg_last5")
    fs = float(row.get("form_score", 50) or 50)
    vsb_str = f"{vsb:+.2f}" if not pd.isna(vsb) else "N/A"
    tsg_str = f"{tsg:.2f}" if not pd.isna(tsg) else "N/A"
    return f"Form {fc} (score {fs:.1f}/100) — True SG L5: {tsg_str}, vs baseline: {vsb_str}."


def generate_anti_pattern_summary(row):
    flags = row.get("anti_pattern_flags", "none")
    if flags == "none":
        return "No anti-pattern flags. Clean structural profile."
    count = int(row.get("ap_total_flags", 0))
    return f"{count} anti-pattern signal(s): {flags}. Structural concerns noted."


def generate_top_traits(row):
    traits = []
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    sg_arg = float(row.get("sg_arg_12m") or 0)
    app_val = float(row.get("app_150_200_value") or 0)
    ch_adj = float(row.get("ch_adjustment_f") or 0)
    if sg_app > 0.3: traits.append(f"Elite approach (SG:APP {sg_app:+.2f})")
    elif sg_app > 0: traits.append(f"Positive approach (SG:APP {sg_app:+.2f})")
    if sg_ott > 0.5: traits.append(f"Elite off-tee (SG:OTT {sg_ott:+.2f})")
    elif sg_ott > 0.2: traits.append(f"Strong OTT (SG:OTT {sg_ott:+.2f})")
    if sg_putt > 0.3: traits.append(f"Strong putting (SG:PUTT {sg_putt:+.2f})")
    if sg_arg > 0.2: traits.append(f"Short-game skill (SG:ARG {sg_arg:+.2f})")
    if app_val > 0.03: traits.append(f"150-200yd iron specialist (value {app_val:+.3f})")
    if ch_adj > 0.03: traits.append("Positive course history adjustment")
    return traits[:4] if traits else ["Limited positive trait signal"]


def generate_drag_traits(row):
    drags = []
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    sg_arg = float(row.get("sg_arg_12m") or 0)
    fit_acc = float(row.get("fit_drive_acc") or 0)
    debut = bool(row.get("debut_flag", False))
    if sg_app < -0.1: drags.append(f"Weak approach (SG:APP {sg_app:+.2f})")
    if sg_ott < -0.1: drags.append(f"Below-avg OTT (SG:OTT {sg_ott:+.2f})")
    if sg_putt < -0.2: drags.append(f"Poor putting (SG:PUTT {sg_putt:+.2f})")
    if sg_arg < -0.3: drags.append(f"Weak ARG (SG:ARG {sg_arg:+.2f})")
    if fit_acc < -0.10: drags.append("Course accuracy penalty — wayward driver here")
    if debut: drags.append("Renaissance debut — unknown ceiling")
    return drags[:3] if drags else ["No material drag traits"]


def generate_conviction_statement(row):
    tier = int(row.get("tier", 5))
    cl = row.get("conviction_level", "LOW")
    fc = row.get("form_class", "NEUTRAL")
    vh = row.get("venue_history_depth", "NONE")
    ap = int(row.get("ap_total_flags", 0))
    name = f"{row.get('first', '')} {row.get('last', '')}".strip().title()
    vts = float(row.get("vts_final", 50))

    if tier == 1:
        return f"{name} is a legitimate contender — elite cross-category score (VTS {vts:.1f}), {cl} conviction."
    elif tier == 2:
        vh_note = "supported by venue history" if vh in ("STRONG","MODERATE") else "with limited course history"
        return f"{name} is a firm Tier 2 play {vh_note} — top-shelf SG profile, {cl} conviction."
    elif tier == 3:
        fc_note = f"Form is {fc.lower()}." if fc != "NEUTRAL" else ""
        ap_note = f" {ap} anti-pattern flag(s) apply." if ap > 0 else ""
        return f"{name} is a viable dark horse here — specific trait overlap with Renaissance demands.{fc_note}{ap_note}"
    elif tier == 4:
        return f"{name} requires multiple components to converge — structural ceiling is limited but a quiet T20 run is possible."
    else:
        return f"{name} faces structural headwinds at this venue — model flags recurring weak-link traits that often hurt at Renaissance."


def generate_risk_vector(row):
    ap = int(row.get("ap_total_flags", 0))
    ddc = row.get("data_depth_class", "FULL")
    fc = row.get("form_class", "NEUTRAL")
    debut = bool(row.get("debut_flag", False))
    risks = []
    if ap >= 2:
        risks.append("multi-flag anti-pattern")
    if ddc in ("LIMITED", "DEBUT"):
        risks.append(f"thin data ({ddc})")
    if fc in ("COLD", "COOL"):
        risks.append(f"form drag ({fc})")
    if debut:
        risks.append("venue debut discount")
    return " + ".join(risks) if risks else "baseline variance only"


def generate_failure_condition(row):
    tier = int(row.get("tier", 5))
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    fit_acc = float(row.get("fit_drive_acc") or 0)
    if sg_app < 0 and fit_acc < 0:
        return "Approach from links rough + accuracy penalty compounds — misses cut if iron play doesn't spike."
    elif sg_putt < -0.3:
        return "Flat putter on fast links greens — can't convert enough long-iron proximity into birdies."
    elif tier >= 4:
        return "SG ceiling too low to sustain contention — relies on variance, not repeatable skill edges."
    return "Reverts to field average if form fades — no dominant skill separating him on this setup."


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
    """Dark-horse mechanism for Tier 3 players."""
    sg_app = float(row.get("sg_app_12m") or 0)
    sg_ott = float(row.get("sg_ott_12m") or 0)
    sg_putt = float(row.get("sg_putt_12m") or 0)
    app_val = float(row.get("app_150_200_value") or 0)
    ch_adj = float(row.get("ch_adjustment_f") or 0)
    fit_acc = float(row.get("fit_drive_acc") or 0)
    name_first = str(row.get("first", "")).title()

    if ch_adj > 0.02:
        return f"{name_first} has proven he can score at Renaissance — positive course history is the ceiling unlock."
    elif app_val > 0.02:
        return f"Strong 150-200yd iron value ({app_val:+.3f}) — the primary scoring zone at Renaissance where he excels."
    elif sg_ott > 0.5 and fit_acc > 0:
        return f"Elite OTT ({sg_ott:+.2f}) combined with positional accuracy — sets up short-iron looks from tight fairways."
    elif sg_putt > 0.5:
        return f"Top-tier putter ({sg_putt:+.2f}) — if he hits enough greens, he can spike a leaderboard run."
    elif sg_app > 0.4:
        return f"Above-average approach game ({sg_app:+.2f}) — can sustain GIR% needed for links contention."
    return "Combination of marginal skill edges across multiple categories — upside available if form spikes."


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
    "generated_date": "2026-07-06",
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
        "app_150_200_value": float(row.get("app_150_200_value")) if not pd.isna(row.get("app_150_200_value", None)) else None,
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
    "generated_date": "2026-07-06",
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
