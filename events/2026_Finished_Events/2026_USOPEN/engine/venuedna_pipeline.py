"""
PGA VenueDNA Tier Engine – 2026 U.S. Open @ Shinnecock Hills GC
Produces:
  2026_USOPEN_trait_form_matrix.csv
  2026_USOPEN_scored_field.csv
"""

import re, json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
BASE = r"C:\PGA_VenueDNA\events\2026_USOPEN"
FIELD_CSV   = f"{BASE}/2026_USOPEN_field_input.csv"
SG_CSV      = f"{BASE}/2026_USOPEN_Last12Mon_TrueSG.csv"
FORM_CSV    = f"{BASE}/2026_USOPEN_RecentForm.csv"
EXCEL_PATH  = f"{BASE}/CourseFitAdjustment+PredictedShotDist_USOPEN_2026.xlsx"
OUT_MATRIX  = f"{BASE}/2026_USOPEN_trait_form_matrix.csv"
OUT_SCORED  = f"{BASE}/2026_USOPEN_scored_field.csv"

# ── event / venue constants (hardcoded per spec) ──────────────────────────────
EVENT_META = dict(
    eventname="2026 U.S. Open",
    venue="Shinnecock Hills Golf Club",
    venuecode="shinnecock_hills_gc",
    venuefileversion="2026_v1",
    weatherforecastclass="highwind",
    venuevarianceclass="high",
    par=70,
    yardage=7440,
    cutrule="low 60 and ties",
)

VENUE_WEIGHTS = dict(
    ott_distance=0.18,
    ott_accuracy=0.12,
    app_150_200=0.10,
    app_200_plus=0.15,
    app_short=0.05,
    app_flight_control=0.05,
    arg_tight_runoff=0.12,
    arg_bunker=0.08,
    putt_distance_control=0.10,
    putt_short_conversion=0.05,
    wind_tolerance=0.10,
    major_grind=0.05,
)

# anti-pattern definitions: (base_low, base_high, highwind_scaler)
ANTI_PATTERNS = dict(
    bomb_and_spray      = (-3.0, -6.0, 1.2),
    short_and_wild      = (-2.0, -5.0, 1.0),
    long_iron_liability = (-3.0, -7.0, 1.2),
    weak_tight_runoff   = (-2.0, -5.0, 1.0),
    poor_lag_putting    = (-1.0, -3.0, 1.1),
)

HIGHWIND = EVENT_META["weatherforecastclass"] == "highwind"
ANTI_PENALTY_CAP = -9.0   # max total anti-pattern penalty per player

BLEND = dict(neutral=0.65, venuefit=0.35, venuehistory=0.0)

DEBUT_PENALTIES = dict(A=-4.0, B=-1.75, C=-1.0)

# ── helpers ───────────────────────────────────────────────────────────────────

def norm0100(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(50.0, index=series.index)
    return (series - lo) / (hi - lo) * 100.0


def clean_name_key(last: str, first: str) -> str:
    return f"{str(last).strip().upper()}_{str(first).strip().upper()}"


def parse_win_pct(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace("%", "")
    try:
        return float(s) / 100.0
    except Exception:
        return 0.0


# ── 1. LOAD FIELD ─────────────────────────────────────────────────────────────
print("Loading field...")
field_raw = pd.read_csv(FIELD_CSV)
field_raw.columns = [c.strip() for c in field_raw.columns]
field_raw = field_raw.rename(columns={
    "First Name": "firstname",
    "Last Name":  "lastname",
    "World Rank": "worldrank",
})
field_raw["playername"] = field_raw["lastname"].str.upper().str.strip() + ", " + field_raw["firstname"].str.upper().str.strip()
field_raw["name_key"] = field_raw.apply(lambda r: clean_name_key(r["lastname"], r["firstname"]), axis=1)
field_raw["worldrank"] = pd.to_numeric(field_raw["worldrank"], errors="coerce")
field_raw["playerid"] = range(1, len(field_raw) + 1)

N = len(field_raw)
print(f"  Field size: {N}")

# ── 2. LOAD LAST-12M TRUE SG ──────────────────────────────────────────────────
print("Loading True SG...")
sg_raw = pd.read_csv(SG_CSV)
sg_raw.columns = [c.strip() for c in sg_raw.columns]
# columns: Last Name, First Name, Events, Rounds, Wins, WIN%, SG-PUTT, SG-ARG, SG-APP, SG-OTT (dup), SG-OTT, SG-TOTAL, Driving-Distance, Driving-Accuracy
# rename carefully – there are two SG-OTT columns; keep first as duplicate/ignore, second as primary
sg_raw = sg_raw.rename(columns={
    "Last Name":          "lastname",
    "First Name":         "firstname",
    "Events":             "truesg_sample_events",
    "Rounds":             "truesg_sample_rounds",
    "Wins":               "wins_12m",
    "WIN%":               "win_pct_raw",
    "SG-PUTT":            "truesg_putt_12m",
    "SG-ARG":             "truesg_arg_12m",
    "SG-APP":             "truesg_app_12m",
    "SG-OTT":             "truesg_ott_delta",   # first column (SG-OTT delta-like)
    "SG-OTT.1":           "truesg_ott_12m",     # second column (main OTT SG)
    "SG-TOTAL":           "truesg_total_12m",
    "Driving-Distance":   "driving_distance_delta",
    "Driving-Accuracy":   "driving_accuracy_delta",
})

sg_raw["lastname"]  = sg_raw["lastname"].str.strip().str.upper()
sg_raw["firstname"] = sg_raw["firstname"].str.strip().str.upper()
sg_raw["name_key"]  = sg_raw["lastname"] + "_" + sg_raw["firstname"]

# driving_accuracy_delta is stored as "4.60%" — strip the % before numeric coerce
sg_raw["driving_accuracy_delta"] = (
    sg_raw["driving_accuracy_delta"].astype(str).str.replace("%","", regex=False)
)

# numeric coerce
for c in ["truesg_putt_12m","truesg_arg_12m","truesg_app_12m","truesg_ott_12m",
          "truesg_total_12m","truesg_sample_events","truesg_sample_rounds",
          "wins_12m","driving_distance_delta","driving_accuracy_delta"]:
    sg_raw[c] = pd.to_numeric(sg_raw[c], errors="coerce")

sg_raw["win_rate_12m"] = sg_raw["win_pct_raw"].apply(parse_win_pct)
sg_raw["truesg_sample_rounds"] = sg_raw["truesg_sample_rounds"].fillna(0)

# ── 3. LOAD RECENT FORM ───────────────────────────────────────────────────────
print("Loading Recent Form...")
form_raw = pd.read_csv(FORM_CSV, usecols=["Last Name","First Name","main-tour",
                                           "Last 20 Rds True-SG","Last 20 VERSUS BASELINE"])
form_raw.columns = ["lastname","firstname","main_tour","last20rds_sg","last20_vs_baseline"]
form_raw["lastname"]  = form_raw["lastname"].str.strip().str.upper()
form_raw["firstname"] = form_raw["firstname"].str.strip().str.upper()
form_raw["name_key"]  = form_raw["lastname"] + "_" + form_raw["firstname"]
form_raw["last20rds_sg"]      = pd.to_numeric(form_raw["last20rds_sg"],      errors="coerce")
form_raw["last20_vs_baseline"] = pd.to_numeric(form_raw["last20_vs_baseline"], errors="coerce")

# ── 4. LOAD EXCEL (course fit + shot dist) ────────────────────────────────────
print("Loading Course Fit Excel...")
xl = pd.read_excel(EXCEL_PATH)
xl.columns = [c.strip() for c in xl.columns]
xl = xl.rename(columns={
    "Last Name":            "lastname",
    "First Name":           "firstname",
    "SG-Short Game":        "cf_sg_short_game",
    "SG-Approach":          "cf_sg_approach",
    "SG-Distance":          "cf_sg_distance",
    "SG-Accuracy":          "cf_sg_accuracy",
    "SG-Total SG Adj":      "coursefit_adj_total",
    "Putting 2-5ft":        "cf_putt_2_5ft",
    "Putting 5-30ft":       "cf_putt_5_30ft",
    "Putting 30+ ft":       "cf_putt_30plus",
    "Course-Fairway":       "cf_course_fairway",
    "Course-Rough":         "cf_course_rough",
    "Course-Bunker":        "cf_course_bunker",
    "Approach 50-100yds":   "shotdist_approach_100_150",   # mapped to closest bucket
    "Approach 100-150 yds": "shotdist_approach_150_175",
    "Approach 150-200 yds": "shotdist_approach_175_200",
    "Approach 200+ yds":    "shotdist_approach_200_225",
})
xl["lastname"]  = xl["lastname"].str.strip().str.upper()
xl["firstname"] = xl["firstname"].str.strip().str.upper()
xl["name_key"]  = xl["lastname"] + "_" + xl["firstname"]

for c in xl.columns:
    if c not in ("lastname","firstname","name_key"):
        xl[c] = pd.to_numeric(xl[c], errors="coerce")

# ── 5. MERGE ALL ONTO FIELD ───────────────────────────────────────────────────
print("Merging inputs...")
df = field_raw.copy()

df = df.merge(sg_raw.drop(columns=["lastname","firstname"]),   on="name_key", how="left")
df = df.merge(form_raw.drop(columns=["lastname","firstname"]), on="name_key", how="left")
df = df.merge(xl.drop(columns=["lastname","firstname"]),       on="name_key", how="left")

# ── 6. DATA DEPTH / BASELINE CONFIDENCE ──────────────────────────────────────
def depth_class(rounds):
    if pd.isna(rounds):
        return "thin"
    r = float(rounds)
    if r >= 70:  return "deep"
    if r >= 30:  return "medium"
    return "thin"

def confidence_band(dc):
    return {"deep":"high","medium":"medium","thin":"low"}.get(dc, "low")

df["datadepthclass"]        = df["truesg_sample_rounds"].apply(depth_class)
df["baselineconfidenceband"] = df["datadepthclass"].apply(confidence_band)

# ── 7. NEUTRAL SKILL ──────────────────────────────────────────────────────────
# neutralskillsg = smooth truesg_total_12m; fill missing with median of thin group
median_sg = df["truesg_total_12m"].median()
df["neutralskillsg"] = df["truesg_total_12m"].fillna(median_sg)
# for thin/no data flag with penalty
df["_sg_missing"] = df["truesg_total_12m"].isna()

df["neutralskillindex"] = norm0100(df["neutralskillsg"])

# ── 8. VENUE FIT TRAITS (0–100) ───────────────────────────────────────────────
#
# We build trait scores from the available data columns:
#   OTT:   truesg_ott_12m (distance proxy via driving_distance_delta, accuracy via driving_accuracy_delta)
#   APP:   truesg_app_12m, cf_sg_approach, shotdist columns
#   ARG:   truesg_arg_12m, cf_sg_short_game, cf_course_bunker
#   PUTT:  truesg_putt_12m, cf_putt columns
#   WIND:  composite of OTT + APP + accuracy
#   MAJOR: win_rate_12m + neutralskillsg proxy

def safe_norm(series):
    s = series.copy().fillna(series.median() if not series.isna().all() else 0)
    return norm0100(s)

# OTT sub-traits
# Distance: SG-OTT + driving distance delta (positive = longer than avg)
ott_dist_raw = df["truesg_ott_12m"].fillna(0) + df["driving_distance_delta"].fillna(0) * 0.02
# Accuracy: invert; negative driving_accuracy_delta = less accurate; positive = more
ott_acc_raw  = df["truesg_ott_12m"].fillna(0) + df["driving_accuracy_delta"].fillna(0) * 0.03

df["trait_ott_distance"] = safe_norm(ott_dist_raw)
df["trait_ott_accuracy"] = safe_norm(ott_acc_raw)
df["trait_ott_total"]    = safe_norm(df["truesg_ott_12m"].fillna(0))

# APP sub-traits
# APP 150-200: base sg_app + course_fit approach 150-175 column (higher = better)
app_150_200_raw = df["truesg_app_12m"].fillna(0) * 0.6 + df["shotdist_approach_150_175"].fillna(df["shotdist_approach_150_175"].median()) * 0.4
app_200_raw     = df["truesg_app_12m"].fillna(0) * 0.4 + df["shotdist_approach_200_225"].fillna(df["shotdist_approach_200_225"].median()) * 0.6
app_short_raw   = df["truesg_app_12m"].fillna(0) * 0.5 + df["shotdist_approach_100_150"].fillna(df["shotdist_approach_100_150"].median()) * 0.5
# flight control = accuracy * app combination (negative driving_acc = poor flight)
app_flight_raw  = df["truesg_app_12m"].fillna(0) + df["driving_accuracy_delta"].fillna(0) * 0.02

df["trait_app_150_200"]      = safe_norm(app_150_200_raw)
df["trait_app_200_plus"]     = safe_norm(app_200_raw)
df["trait_app_short"]        = safe_norm(app_short_raw)
df["trait_app_flight_control"]= safe_norm(app_flight_raw)
df["trait_app_total"]        = safe_norm(df["truesg_app_12m"].fillna(0))

# ARG sub-traits
# tight runoff: sg_arg + cf_course_rough (rough scrambling)
arg_tight_raw  = df["truesg_arg_12m"].fillna(0) * 0.6 + df["cf_course_rough"].fillna(df["cf_course_rough"].median()) * 0.4
# bunker: sg_arg + cf_course_bunker
arg_bunker_raw = df["truesg_arg_12m"].fillna(0) * 0.5 + df["cf_course_bunker"].fillna(df["cf_course_bunker"].median()) * 0.5

df["trait_arg_tight_runoff"] = safe_norm(arg_tight_raw)
df["trait_arg_bunker"]       = safe_norm(arg_bunker_raw)
df["trait_arg_total"]        = safe_norm(df["truesg_arg_12m"].fillna(0))

# PUTT sub-traits
# distance control: putt + cf_putt_5_30ft (lag range)
putt_dc_raw  = df["truesg_putt_12m"].fillna(0) * 0.5 + df["cf_putt_5_30ft"].fillna(df["cf_putt_5_30ft"].median()) * 0.5
# short conversion: putt + cf_putt_2_5ft
putt_sc_raw  = df["truesg_putt_12m"].fillna(0) * 0.5 + df["cf_putt_2_5ft"].fillna(df["cf_putt_2_5ft"].median()) * 0.5

df["trait_putt_distance_control"]  = safe_norm(putt_dc_raw)
df["trait_putt_short_conversion"]  = safe_norm(putt_sc_raw)
df["trait_putt_total"]             = safe_norm(df["truesg_putt_12m"].fillna(0))

# Wind tolerance: high OTT distance + high APP 200+ + decent accuracy (not bomb-and-spray)
wind_raw = (
    df["truesg_ott_12m"].fillna(0) * 0.35 +
    df["truesg_app_12m"].fillna(0) * 0.35 +
    df["driving_accuracy_delta"].fillna(0) * 0.02 +
    df["cf_sg_distance"].fillna(0) * 0.30
)
df["trait_wind_tolerance"] = safe_norm(wind_raw)

# Major grind: win_rate + neutral skill baseline
major_raw = df["win_rate_12m"].fillna(0) * 40.0 + df["neutralskillsg"].fillna(0) * 0.5
df["trait_major_grind"] = safe_norm(major_raw)

# ── 9. VENUE FIT SCORE (dot-product of trait weights) ─────────────────────────
#
# Map each weight key to the trait column it references
WEIGHT_TO_TRAIT = {
    "ott_distance":       "trait_ott_distance",
    "ott_accuracy":       "trait_ott_accuracy",
    "app_150_200":        "trait_app_150_200",
    "app_200_plus":       "trait_app_200_plus",
    "app_short":          "trait_app_short",
    "app_flight_control": "trait_app_flight_control",
    "arg_tight_runoff":   "trait_arg_tight_runoff",
    "arg_bunker":         "trait_arg_bunker",
    "putt_distance_control": "trait_putt_distance_control",
    "putt_short_conversion": "trait_putt_short_conversion",
    "wind_tolerance":     "trait_wind_tolerance",
    "major_grind":        "trait_major_grind",
}

vfs = pd.Series(0.0, index=df.index)
for wkey, tcol in WEIGHT_TO_TRAIT.items():
    vfs = vfs + VENUE_WEIGHTS[wkey] * df[tcol]

# course-fit adjustment: bounded ±8 points on 0-100 scale → clamp to ±6
cf_contribution = df["coursefit_adj_total"].fillna(0) * 15.0
cf_contribution = cf_contribution.clip(-6, 6)
df["venuefitscore"] = (vfs + cf_contribution).clip(0, 100)

# venuefitdelta = venuefitscore – neutralskillindex (both 0-100)
df["venuefitdelta"] = df["venuefitscore"] - df["neutralskillindex"]

def venuefit_confidence(row):
    if row["datadepthclass"] == "deep" and not pd.isna(row["coursefit_adj_total"]):
        return "high"
    if row["datadepthclass"] == "thin":
        return "low"
    return "medium"

df["venuefitconfidenceband"] = df.apply(venuefit_confidence, axis=1)

# ── 10. COURSE FIT SUB-COMPONENTS (optional output columns) ──────────────────
df["coursefit_adj_ott"]  = df["cf_sg_distance"] + df["cf_sg_accuracy"]
df["coursefit_adj_app"]  = df["cf_sg_approach"]
df["coursefit_adj_arg"]  = df["cf_sg_short_game"]
df["coursefit_adj_putt"] = df["cf_putt_5_30ft"] * 0.05  # scale to SG-like

# shot dist columns (rename to spec names for output)
df["shotdist_approach_225_plus"] = df["shotdist_approach_200_225"]  # best proxy available
df["shotdist_par3_175_200"]      = df["shotdist_approach_175_200"]
df["shotdist_par3_200_plus"]     = df["shotdist_approach_200_225"]

# ── 11. VENUE HISTORY (Shinnecock – placeholders) ─────────────────────────────
# No historical SG data available; set to zero / low confidence
df["venue_history_rounds"]     = 0
df["venue_history_sg_total"]   = 0.0
df["venue_history_sg_ott"]     = 0.0
df["venue_history_sg_app"]     = 0.0
df["venue_history_sg_arg"]     = 0.0
df["venue_history_sg_putt"]    = 0.0
df["venuehistorydelta"]        = 0.0
df["venuehistoryconfidenceband"] = "low"

# ── 12. RECENT FORM ───────────────────────────────────────────────────────────
# formscore_raw: quality-weighted by tour tier + decay (last20rds_sg base)
TOUR_QUALITY = {
    "PGA Tour": 1.0, "Major": 1.0, "LIV Golf": 0.90, "DP World Tour": 0.85,
    "Korn Ferry Tour": 0.75, "Amateur": 0.60,
}
df["last20rds_sg"]      = df["last20rds_sg"].fillna(df["neutralskillsg"])
df["last20_vs_baseline"] = df["last20_vs_baseline"].fillna(0.0)

# formscore_raw = last20rds_sg smoothed toward neutralskillsg
# regression weight: deep→0.3, medium→0.4, thin→0.6 (more reversion for thin)
def regression_weight(dc):
    return {"deep":0.30, "medium":0.40, "thin":0.60}.get(dc, 0.60)

df["_regw"] = df["datadepthclass"].apply(regression_weight)
df["formscore_raw"] = df["last20rds_sg"] * (1 - df["_regw"]) + df["neutralskillsg"] * df["_regw"]

df["recentformindex"]    = norm0100(df["formscore_raw"])
df["form_vs_neutralskill"] = df["last20_vs_baseline"].fillna(0.0)

# formscore_adjusted: regress further toward neutralskill
df["formscore_adjusted"] = df["formscore_raw"] * 0.65 + df["neutralskillsg"] * 0.35

# form gate: apply when form_vs_neutralskill < -1.0
FORM_GATE_THRESHOLD = -1.0
df["recentformgateapplied"] = df["form_vs_neutralskill"] < FORM_GATE_THRESHOLD
df["recentformgate_reason"] = df.apply(
    lambda r: f"Last20 vs baseline = {r['form_vs_neutralskill']:.2f} SG (threshold {FORM_GATE_THRESHOLD})"
              if r["recentformgateapplied"] else "",
    axis=1
)

# ── 13. DEBUT FLAGS ───────────────────────────────────────────────────────────
# Simple heuristic: if sample rounds < 30 or main_tour is Amateur → debut considered
# Class A: no main-tour data + thin; Class B: some comp data; Class C: elite by neutralskillsg
ELITE_THRESHOLD = 1.5  # SG threshold for Class C

def assign_debut(row):
    thin = row["datadepthclass"] == "thin"
    is_amateur = str(row.get("main_tour","")).strip() == "Amateur"
    sg = float(row["neutralskillsg"]) if not pd.isna(row["neutralskillsg"]) else 0.0

    if not thin and not is_amateur:
        return False, ""
    if is_amateur or (thin and sg < 0.2):
        if sg >= ELITE_THRESHOLD:
            return True, "C"
        elif sg >= 0.0:
            return True, "B"
        else:
            return True, "A"
    if thin:
        return True, "B"
    return False, ""

debut_results = df.apply(lambda r: assign_debut(r), axis=1)
df["debutflag"]  = debut_results.apply(lambda x: x[0])
df["debutclass"] = debut_results.apply(lambda x: x[1])

# ── 14. HEALTH FLAGS ─────────────────────────────────────────────────────────
df["injuryflag"]       = False
df["healthgatestatus"] = "ok"
df["healthgatereason"] = ""

# ── 15. ANTI-PATTERN FLAGS ───────────────────────────────────────────────────
#
# bomb_and_spray:       high OTT distance but poor accuracy
# short_and_wild:       below-avg OTT distance + poor accuracy
# long_iron_liability:  poor APP 200+ (below 35th pct) with avg+ distance
# weak_tight_runoff:    poor ARG tight runoff (below 30th pct)
# poor_lag_putting:     poor putt distance control (below 30th pct)

# Anti-patterns use raw driving stats (distance/accuracy) for the OTT-based patterns.
# This avoids SG-OTT conflation — SG-OTT blends distance and accuracy into one number,
# so we need the raw split to detect bomb-and-spray (long but wild) vs short-and-wild.
dd  = df["driving_distance_delta"].fillna(0)   # positive = longer than avg
da  = df["driving_accuracy_delta"].fillna(0)   # positive = more accurate than avg
ott = df["truesg_ott_12m"].fillna(0)

p60_dd  = dd.quantile(0.60)    # above-avg distance
p40_da  = da.quantile(0.40)    # below-avg accuracy (40th pct = poor accuracy)
p40_dd  = dd.quantile(0.40)    # below-avg distance

p35_app200  = df["trait_app_200_plus"].quantile(0.35)
p30_arg_tr  = df["trait_arg_tight_runoff"].quantile(0.30)
p30_putt_dc = df["trait_putt_distance_control"].quantile(0.30)

# bomb_and_spray: notably long (top 40% in raw distance) but below-avg accuracy
df["antipattern_bomb_and_spray_flag"]      = (dd > p60_dd) & (da < p40_da)
# short_and_wild: below-avg distance AND below-avg accuracy
df["antipattern_short_and_wild_flag"]      = (dd < p40_dd) & (da < p40_da)
# long_iron_liability: below 35th pct in APP_200+ trait (poor long irons into greens)
df["antipattern_long_iron_liability_flag"] = (df["trait_app_200_plus"] < p35_app200)
# weak_tight_runoff: poor ARG (links-style scrambling) below 30th pct
df["antipattern_weak_tight_runoff_flag"]   = (df["trait_arg_tight_runoff"] < p30_arg_tr)
# poor_lag_putting: poor lag putting (distance control) below 30th pct
df["antipattern_poor_lag_putting_flag"]    = (df["trait_putt_distance_control"] < p30_putt_dc)

# ── 16. DIAGNOSTICS ──────────────────────────────────────────────────────────
TRAIT_LABELS = {
    "trait_ott_distance":       "OTT_Distance",
    "trait_ott_accuracy":       "OTT_Accuracy",
    "trait_app_200_plus":       "APP_200+",
    "trait_app_150_200":        "APP_150-200",
    "trait_app_flight_control": "APP_FlightCtrl",
    "trait_arg_tight_runoff":   "ARG_TightRunoff",
    "trait_arg_bunker":         "ARG_Bunker",
    "trait_putt_distance_control": "PUTT_LagCtrl",
    "trait_wind_tolerance":     "WindTolerance",
    "trait_major_grind":        "MajorGrind",
}

def primary_driver(row):
    best_col, best_val = None, -9999
    for col, label in TRAIT_LABELS.items():
        v = float(row[col])
        if v > best_val:
            best_val, best_col = v, col
    return TRAIT_LABELS.get(best_col, "")

def primary_risk(row):
    worst_col, worst_val = None, 9999
    for col, label in TRAIT_LABELS.items():
        v = float(row[col])
        if v < worst_val:
            worst_val, worst_col = v, col
    return TRAIT_LABELS.get(worst_col, "")

def trait_summary(row):
    pos = sorted(TRAIT_LABELS.items(), key=lambda x: -row[x[0]])[:2]
    neg = sorted(TRAIT_LABELS.items(), key=lambda x: row[x[0]])[:1]
    pos_str = " + ".join(l for _, l in pos)
    neg_str = neg[0][1] if neg else ""
    return f"{pos_str}; weak {neg_str}"

df["primary_trait_driver"] = df.apply(primary_driver, axis=1)
df["primary_risk_trait"]   = df.apply(primary_risk,   axis=1)
df["trait_summary_label"]  = df.apply(trait_summary,  axis=1)

# ── 17. ASSEMBLE MATRIX ───────────────────────────────────────────────────────
print("Assembling trait_form_matrix...")

MATRIX_COLS = [
    "playerid","firstname","lastname","playername","worldrank","main_tour",
    "datadepthclass","baselineconfidenceband",
    # NeutralSkill
    "truesg_total_12m","truesg_ott_12m","truesg_app_12m","truesg_arg_12m","truesg_putt_12m",
    "truesg_sample_events","truesg_sample_rounds","wins_12m","win_rate_12m",
    "driving_distance_delta","driving_accuracy_delta",
    "neutralskillsg","neutralskillindex",
    # VenueFit traits
    "trait_ott_distance","trait_ott_accuracy","trait_ott_total",
    "trait_app_total","trait_app_150_200","trait_app_200_plus","trait_app_short","trait_app_flight_control",
    "trait_arg_total","trait_arg_tight_runoff","trait_arg_bunker",
    "trait_putt_total","trait_putt_distance_control","trait_putt_short_conversion",
    "trait_wind_tolerance","trait_major_grind",
    # Course fit
    "coursefit_adj_total","coursefit_adj_ott","coursefit_adj_app","coursefit_adj_arg","coursefit_adj_putt",
    "shotdist_approach_100_150","shotdist_approach_150_175","shotdist_approach_175_200",
    "shotdist_approach_200_225","shotdist_approach_225_plus",
    "shotdist_par3_175_200","shotdist_par3_200_plus",
    # VenueFit summary
    "venuefitscore","venuefitdelta","venuefitconfidenceband",
    # Venue history
    "venue_history_rounds","venue_history_sg_total","venue_history_sg_ott",
    "venue_history_sg_app","venue_history_sg_arg","venue_history_sg_putt",
    "venuehistorydelta","venuehistoryconfidenceband",
    # Recent form
    "last20rds_sg","last20_vs_baseline","formscore_raw","recentformindex",
    "form_vs_neutralskill","formscore_adjusted","recentformgateapplied","recentformgate_reason",
    # Debut / health / anti-pattern
    "debutflag","debutclass","injuryflag","healthgatestatus","healthgatereason",
    "antipattern_bomb_and_spray_flag","antipattern_short_and_wild_flag",
    "antipattern_long_iron_liability_flag","antipattern_weak_tight_runoff_flag",
    "antipattern_poor_lag_putting_flag",
    # Diagnostics
    "primary_trait_driver","primary_risk_trait","trait_summary_label",
]

matrix = df[MATRIX_COLS].copy()
matrix.to_csv(OUT_MATRIX, index=False)
print(f"  Wrote {OUT_MATRIX}  ({len(matrix)} rows)")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 – SCORING PIPELINE → scored_field.csv
# ═══════════════════════════════════════════════════════════════════════════════
print("\nRunning scoring pipeline...")

sf = df.copy()

# ── A. PRE-PENALTY VTS (blend) ────────────────────────────────────────────────
# convert everything to a common VTS scale (0-100)
neutral_vts = sf["neutralskillindex"]          # already 0-100
venue_vts   = sf["venuefitscore"]              # already 0-100
history_vts = pd.Series(50.0, index=sf.index) # no history → neutral

sf["prepenaltyvts"] = (
    BLEND["neutral"]      * neutral_vts +
    BLEND["venuefit"]     * venue_vts   +
    BLEND["venuehistory"] * history_vts
)

sf["blendclass"]      = "Neutral+Venue"
sf["blendweightsused"] = json.dumps(BLEND)

# ── B. DEBUT PENALTIES ────────────────────────────────────────────────────────
sf["debutpenaltyapplied"] = sf["debutclass"].map(DEBUT_PENALTIES).fillna(0.0)
# convert SG-unit debut penalty to VTS scale (SG ≈ 1.0 ~ 15 VTS units)
SG_TO_VTS = 10.0
sf["debutpenaltyapplied_vts"] = sf["debutpenaltyapplied"] * SG_TO_VTS / 4.0

# ── C. ANTI-PATTERN PENALTIES ─────────────────────────────────────────────────
# Severity scale: how far below the percentile threshold determines penalty depth
# Use trait z-score within field to interpolate between base_low and base_high

def ap_penalty(flag_col, base_low, base_high, hw_scaler, trait_col, direction="low"):
    """
    direction='low'  → flag means trait is too low (poor bunker, poor arg)
    direction='high' → flag means trait is too high relative to accuracy (bomb-spray)
    Returns a series of penalties (negative numbers, 0 if not flagged).
    """
    # severity 0-1: 0 = just barely flagged, 1 = worst in field
    t = sf[trait_col]
    t_min, t_max = t.min(), t.max()
    rng = (t_max - t_min) if t_max != t_min else 1.0

    if direction == "low":
        # lower value = more severe
        sev = ((t.median() - t) / rng).clip(0, 1)
    else:
        # higher distance value = more severe for bomb-spray
        sev = ((t - t.median()) / rng).clip(0, 1)

    # interpolate penalty
    penalty = base_low + sev * (base_high - base_low)  # base_high is more negative
    if HIGHWIND:
        penalty = penalty * hw_scaler
    penalty = penalty.clip(base_high * hw_scaler if HIGHWIND else base_high, 0)  # cap at spec range
    return np.where(sf[flag_col], penalty, 0.0)

sf["antipattern_penalty_bomb_and_spray"]      = ap_penalty("antipattern_bomb_and_spray_flag",      -3.0, -6.0, 1.2, "trait_ott_distance", "high")
sf["antipattern_penalty_short_and_wild"]       = ap_penalty("antipattern_short_and_wild_flag",       -2.0, -5.0, 1.0, "trait_ott_accuracy", "low")
sf["antipattern_penalty_long_iron_liability"]  = ap_penalty("antipattern_long_iron_liability_flag",  -3.0, -7.0, 1.2, "trait_app_200_plus", "low")
sf["antipattern_penalty_weak_tight_runoff"]    = ap_penalty("antipattern_weak_tight_runoff_flag",    -2.0, -5.0, 1.0, "trait_arg_tight_runoff", "low")
sf["antipattern_penalty_poor_lag_putting"]     = ap_penalty("antipattern_poor_lag_putting_flag",     -1.0, -3.0, 1.1, "trait_putt_distance_control", "low")

sf["antipatternpenaltytotal"] = (
    sf["antipattern_penalty_bomb_and_spray"] +
    sf["antipattern_penalty_short_and_wild"] +
    sf["antipattern_penalty_long_iron_liability"] +
    sf["antipattern_penalty_weak_tight_runoff"] +
    sf["antipattern_penalty_poor_lag_putting"]
).clip(ANTI_PENALTY_CAP, 0)

# build semicolon-separated flag string
def ap_flags(row):
    flags = []
    if row["antipattern_bomb_and_spray_flag"]:      flags.append("bomb_and_spray")
    if row["antipattern_short_and_wild_flag"]:       flags.append("short_and_wild")
    if row["antipattern_long_iron_liability_flag"]:  flags.append("long_iron_liability")
    if row["antipattern_weak_tight_runoff_flag"]:    flags.append("weak_tight_runoff")
    if row["antipattern_poor_lag_putting_flag"]:     flags.append("poor_lag_putting")
    return ";".join(flags)

sf["antipatternflags"] = sf.apply(ap_flags, axis=1).fillna("")

# ── D. FORM & HEALTH DELTA (VTS) ─────────────────────────────────────────────
# form delta: form gate → cap ceiling, else mild boost/penalty
def form_delta_vts(row):
    fvn = row["form_vs_neutralskill"]
    gate = row["recentformgateapplied"]
    if gate:
        return max(fvn * 2.0, -8.0)   # gate: amplify the gap, cap at -8
    if fvn > 1.0:
        return min(fvn * 1.5, 5.0)    # hot form boost, capped
    if fvn < -0.3:
        return fvn * 1.0              # modest drag
    return 0.0

sf["form_delta_vts"]  = sf.apply(form_delta_vts, axis=1)
sf["health_delta_vts"] = 0.0  # no health issues flagged

# ── E. VARIANCE ───────────────────────────────────────────────────────────────
def player_variance(row):
    if row["datadepthclass"] == "thin" or row["debutflag"]:
        return "high"
    if abs(row["form_vs_neutralskill"]) > 1.0:
        return "high"
    if row["datadepthclass"] == "medium":
        return "medium"
    return "low"

sf["playervarianceband"] = sf.apply(player_variance, axis=1)

variance_idx = {"low":25.0, "medium":50.0, "high":75.0}
sf["volatilityindex"]   = sf["playervarianceband"].map(variance_idx)
sf["venuevarianceclass"] = EVENT_META["venuevarianceclass"]

# ── F. FINAL VTS ──────────────────────────────────────────────────────────────
# anti-pattern penalties are on SG scale; convert to VTS-scale adjustment
# SG anti-pattern total (~-1 to -9 SG range) → on VTS 0-100: scale by ~3
AP_TO_VTS = 3.0

sf["vtsfinal_raw"] = (
    sf["prepenaltyvts"]
    + sf["debutpenaltyapplied_vts"]
    + sf["antipatternpenaltytotal"] * AP_TO_VTS
    + sf["form_delta_vts"]
    + sf["health_delta_vts"]
).clip(0, 100)

sf["vtsfinal"] = sf["vtsfinal_raw"].clip(0, 100)

# ── G. TIERS ─────────────────────────────────────────────────────────────────
def assign_tier(vts):
    if vts >= 80: return 1
    if vts >= 65: return 2
    if vts >= 50: return 3
    if vts >= 35: return 4
    return 5

sf["tier"] = sf["vtsfinal"].apply(assign_tier)

def tier_reason(row):
    t = row["tier"]
    ns = row["neutralskillsg"]
    vfd = row["venuefitdelta"]
    ap = row["antipatternpenaltytotal"]
    debut = f"; debut-{row['debutclass']}" if row["debutflag"] else ""
    gate = "; form-gated" if row["recentformgateapplied"] else ""

    if t == 1:
        return f"Elite NeutralSG={ns:.2f} + positive VenueFitDelta={vfd:.1f}{debut}"
    elif t == 2:
        return f"Strong NeutralSG={ns:.2f}, solid Shinnecock fit VFD={vfd:.1f}{debut}{gate}"
    elif t == 3:
        return f"Mid-tier NeutralSG={ns:.2f}, moderate fit VFD={vfd:.1f}{debut}{gate}"
    elif t == 4:
        return f"Below-avg skill or venue mismatch VFD={vfd:.1f}, AP={ap:.1f}{debut}{gate}"
    else:
        return f"Weak profile NeutralSG={ns:.2f}, AP={ap:.1f}, VFD={vfd:.1f}{debut}{gate}"

sf["tierreason"] = sf.apply(tier_reason, axis=1)

# tier gate (form or health gated the tier upward)
def tier_gate(row):
    if row["recentformgateapplied"] and row["tier"] > 2:
        return True, "Form gate applied: recent perf materially below baseline"
    return False, ""

tg = sf.apply(tier_gate, axis=1)
sf["tier_gate_flag"]   = tg.apply(lambda x: x[0])
sf["tier_gate_reason"] = tg.apply(lambda x: x[1])

# ── H. PROBABILITIES ─────────────────────────────────────────────────────────
# Base probability curve from vtsfinal, with Shinnecock high-variance compression
# Win%: compress heavily; top player ~8-10%
# Cut%: Tier 1/2 ≥ 80%, Tier 4/5 lower

def logistic_prob(vts, center=65.0, steepness=0.08):
    return 1.0 / (1.0 + np.exp(-steepness * (vts - center)))

# Raw win weight (un-normalized)
variance_spread = {"low":1.0, "medium":1.10, "high":1.20}
sf["_var_s"] = sf["playervarianceband"].map(variance_spread)

# Exponent = 5 gives realistic separation: top ~7-10%, long tail low
# Higher variance slightly boosts long-shot upside (wider spread, not better EV)
win_raw = (sf["vtsfinal"] / 100.0) ** 5.0 * sf["_var_s"]
win_sum = win_raw.sum()
sf["winpct"] = win_raw / win_sum

# Cap at 0.12 (Shinnecock compression: no single player dominates US Open)
# then renormalize so sum = 1.0
sf["winpct"] = sf["winpct"].clip(0, 0.12)
sf["winpct"] = sf["winpct"] / sf["winpct"].sum()

# Top finish probabilities (cumulative from vtsfinal)
def calc_finish_probs(vts, var_band):
    v = float(vts)
    # variance mod: high-variance players have slightly wider top-finish range
    s = 1.0 + (float(var_band) - 50) / 250.0
    top3   = logistic_prob(v, 82, 0.11) * s
    top5   = logistic_prob(v, 78, 0.10) * s
    top10  = logistic_prob(v, 72, 0.09) * s
    top20  = logistic_prob(v, 63, 0.08) * s
    # makecut logistic: center=55, steepness=0.12 → Tier1 ~86%, Tier5 ~2% before scaling
    makecut_raw = logistic_prob(v, 55, 0.12) * min(s, 1.05)
    return top3, top5, top10, top20, makecut_raw

probs = sf.apply(
    lambda r: calc_finish_probs(r["vtsfinal"], r["volatilityindex"]),
    axis=1, result_type="expand"
)
probs.columns = ["top3pct","top5pct","top10pct","top20pct","makecut_raw"]

sf = pd.concat([sf, probs], axis=1)

# Scale makecut so field average ≈ 40% (~60 out of 156 make cut, consistent with spec)
field_avg_mc = sf["makecut_raw"].mean()
sf["makecutpct"] = (sf["makecut_raw"] * (0.40 / field_avg_mc)).clip(0.02, 0.97)
sf["misscutpct"] = 1.0 - sf["makecutpct"]

# ── I. TRACE NOTES ────────────────────────────────────────────────────────────
def trace_note(row):
    parts = [
        f"NeutralSG={row['neutralskillsg']:.2f}",
        f"VFD={row['venuefitdelta']:.1f}",
    ]
    if row["debutflag"]:
        parts.append(f"debut-{row['debutclass']} pen={row['debutpenaltyapplied']:.1f}SG")
    if row["antipatternpenaltytotal"] < -1.0:
        parts.append(f"AP={row['antipatternpenaltytotal']:.1f}VTS ({row['antipatternflags']})")
    if row["recentformgateapplied"]:
        parts.append(f"form-gate({row['form_vs_neutralskill']:.2f})")
    parts.append(f"->Tier{row['tier']} vtsfinal={row['vtsfinal']:.1f}")
    return "; ".join(parts)

sf["tracenotes"] = sf.apply(trace_note, axis=1)

# ── J. ASSEMBLE SCORED FIELD ──────────────────────────────────────────────────
print("Assembling scored_field...")

SCORED_COLS = [
    # identity
    "playerid","playername","firstname","lastname","worldrank","main_tour",
    "datadepthclass","baselineconfidenceband",
    # core skill
    "neutralskillsg","neutralskillindex",
    "venuefitscore","venuefitdelta","venuefitconfidenceband",
    "venue_history_rounds","venue_history_sg_total","venuehistorydelta","venuehistoryconfidenceband",
    # blend
    "prepenaltyvts","blendclass","blendweightsused",
    # debut
    "debutflag","debutclass","debutpenaltyapplied",
    # anti-patterns
    "antipatternflags","antipatternpenaltytotal",
    "antipattern_penalty_bomb_and_spray","antipattern_penalty_short_and_wild",
    "antipattern_penalty_long_iron_liability","antipattern_penalty_weak_tight_runoff",
    "antipattern_penalty_poor_lag_putting",
    # form & health
    "formscore_adjusted","recentformindex","form_vs_neutralskill",
    "recentformgateapplied","recentformgate_reason","form_delta_vts",
    "injuryflag","healthgatestatus","healthgatereason","health_delta_vts",
    # variance
    "playervarianceband","volatilityindex","venuevarianceclass",
    # final vts & tiers
    "vtsfinal_raw","vtsfinal","tier","tierreason","tier_gate_flag","tier_gate_reason",
    # probabilities
    "winpct","top3pct","top5pct","top10pct","top20pct","makecutpct","misscutpct",
    # diagnostics
    "primary_trait_driver","primary_risk_trait","trait_summary_label","tracenotes",
]

scored = sf[SCORED_COLS].copy()
scored.to_csv(OUT_SCORED, index=False)
print(f"  Wrote {OUT_SCORED}  ({len(scored)} rows)")

# ── K. SANITY CHECKS ─────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SANITY CHECKS")
print("="*70)

print("\nTOP 10 by vtsfinal:")
top10 = scored.nlargest(10, "vtsfinal")[["playername","vtsfinal","tier","neutralskillsg","venuefitdelta"]]
print(top10.to_string(index=False))

print("\nTier distribution:")
print(scored["tier"].value_counts().sort_index().to_string())

print(f"\nSum of winpct: {scored['winpct'].sum():.4f}")
print(f"Max winpct:    {scored['winpct'].max():.4f}  ({scored.loc[scored['winpct'].idxmax(),'playername']})")

print(f"\nMakecut stats - mean: {scored['makecutpct'].mean():.3f}, "
      f"Tier1 avg: {scored[scored['tier']==1]['makecutpct'].mean():.3f}, "
      f"Tier5 avg: {scored[scored['tier']==5]['makecutpct'].mean():.3f}")

missing_key = sf[sf["truesg_total_12m"].isna() | sf["last20rds_sg"].isna() | sf["coursefit_adj_total"].isna()]
print(f"\nRows with missing key inputs (for audit): {len(missing_key)}")
if len(missing_key):
    print(missing_key[["playername","truesg_total_12m","last20rds_sg","coursefit_adj_total"]].to_string(index=False))

print("\n" + "="*70)
print("DONE")
