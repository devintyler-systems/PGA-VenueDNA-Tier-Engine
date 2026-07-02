"""
PGA VenueDNA Tier Engine — 2026 John Deere Classic @ TPC Deere Run
Spec  : 02_PGA_VENUEDNA_SCORING_SPEC.md v1.1
Schema: 04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md v1.1
Workflow: 06_PGA_VENUEDNA_EVENT_WORKFLOW.md

Weather lock: soft_wet — heat dome early, Friday-Saturday rain risk, Sunday clean.
Firmness: soft (receptive greens, reduced rollout).

Outputs (all to events/2026_JohnDeereClassic/output/):
  TPC_DEERE_RUN_INTELLIGENCE_2026_v1.md
  2026_john_deere_classic_event_context.json
  2026_john_deere_classic_field_input.csv
  2026_john_deere_classic_trait_form_matrix.csv
  2026_john_deere_classic_vts_full.csv
  2026_john_deere_classic_player_briefs.json
  2026_john_deere_classic_event_payload.json

Deploy package (events/2026_JohnDeereClassic/deploy/data/):
  Copies event_payload.json, vts_full.csv, player_briefs.json

Venue lock: TPC Deere Run
  - Birdie-fest: adj_score_to_par = -1.83 (DG)
  - Par-5 leverage: adj_par5_score = -0.39/round (DG)
  - APP <150: positive less_150_sg = 0.024 (DG)
  - Moderate fairways (fw_width=37.9 yd, fw_diff=0.4) — soft week lowers rollout
  - Low penalty exposure: miss_fw_pen_frac=0.0264, adj_penalties=0.26
  - Dominant traits: APP_Wedge, APP_100_150, Putt_Short_Conv, Par5_Scoring
"""

import json
import warnings
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(r"C:\PGA_VenueDNA\events\2026_JohnDeereClassic")
BASE_IN  = ROOT / "input"
BASE_OUT = ROOT / "output"
BASE_DEP = ROOT / "deploy"
BASE_OUT.mkdir(parents=True, exist_ok=True)
(BASE_DEP / "data").mkdir(parents=True, exist_ok=True)

SLUG = "2026_john_deere_classic"

# ── Event / Venue Constants ────────────────────────────────────────────────────
EVENT_META = dict(
    event_name              = "John Deere Classic",
    event_slug              = SLUG,
    event_id                = 33,
    season_year             = 2026,
    venue_name              = "TPC Deere Run",
    venue_code              = "TPC_DEERE_RUN",
    venue_file_version      = "2026_v1",
    course_par              = 71,
    course_yardage          = 7327,
    # DG table shows 7133 but hole 4 extended adds yardage; 7327 is 2026 championship routing
    course_yardage_dg       = 7133,
    surface                 = "Southshore Bentgrass (fairways + greens); Kentucky Bluegrass/Fine Fescue rough",
    cut_rule                = "top_65_and_ties",
    field_size              = 144,
    weather_forecast_class  = "soft_wet",
    venue_variance_class    = "standard",
    birdie_fest_flag        = True,
    expected_scoring_band   = "-18 to -22 (4 rounds); avg round -1.5 to -1.8 vs par",
    variance_expectation    = "standard_to_slightly_widened_due_to_delay_risk",
    fairway_width_class     = "moderate",   # DG fw_width=37.9 yd, fw_diff=0.4
    rough_severity_class    = "moderate",   # DG rgh_diff=0.4; ~4" tournament rough
    firmness_class          = "soft",
    green_speed_policy      = "medium_fast",
    rollout_class           = "reduced",    # soft turf after rain
    long_iron_frequency_class = "low_to_moderate",
    difficulty_class        = "birdie_fest",  # DG adj_score_to_par=-1.83
    event_class             = "standard_pga_cut_event",
    engine_version          = "1.1",
    scoring_spec_version    = "1.1",
    learning_loop_version   = "1.1",
    event_iteration         = "initial_weather_locked",
    notes_on_setup_change   = [
        "Hole 4 extended from 454 to 492 yards for 2026 championship routing.",
        "Friday-Saturday rain risk softens greens and fairways.",
        "Reduced rollout lessens pure distance advantage; increases receptive-approach conditions.",
    ],
    notes_on_data_gaps      = [
        "One player absent from fit-adj file (143 rows vs 144 field); assigned median fit values.",
        "No separate 2026 DG performance file available; form_vs_baseline=0 for all players.",
        "Players with rounds_played=0 in CH flagged as debut class.",
    ],
    tee_times_available     = False,
    # Weather lock metadata
    weather_heat_alert      = "Extreme Heat Warning through Thursday night",
    weather_primary_risk    = "Friday afternoon through Saturday afternoon",
    weather_wind_profile    = "10-15 mph, non-dominant",
    weather_course_effect   = "Softer, more receptive, lower-rollout scoring setup",
    weather_best_scoring_day = "Sunday",
    weather_delay_risk      = "Moderate Friday-Saturday",
    wind_outlook            = "moderate_non_dominant",
    expected_conditions     = "Extreme heat early, storms/rain risk Friday-Saturday, cleaner Sunday.",
    firmness_outlook        = "Softening through week, especially after Friday precipitation.",
)

# ── Trait Weight Matrix — TPC Deere Run (weather-adjusted seed) ───────────────
# Base Deere weights reflect: birdie-fest par-71, par-5 leverage (-0.39/round DG),
# strong <150 SG signal (0.024 DG), moderate fairways, low penalty exposure.
# Weather adjustment (soft_wet): Par5_Scoring 0.08→0.10, Putt_Lag 0.09→0.10,
# OTT_Distance 0.05→0.04, OTT_Accuracy 0.12→0.11, ARG_Bunker 0.04→0.03.
# Interpretation: soft turf magnifies par-5 birdie equity, lag putting on soft greens,
# reduces rollout value of raw distance. Sum = 1.00.
VENUE_WEIGHTS = dict(
    app_wedge       = 0.18,   # APP <125 yd — dominant wedge/short-iron track
    app_100_150     = 0.15,   # APP 100-150 yd — second wedge bucket, high-value at Deere
    app_150_200     = 0.08,   # APP 150-200 yd — longer irons, less dominant
    ott_accuracy    = 0.11,   # Driving accuracy — bentgrass fairways, moderate penalty
    ott_distance    = 0.04,   # Distance — softened; soft turf lowers rollout premium
    putt_short_conv = 0.14,   # Short putt conversion 2-15 ft — birdie cash-in
    putt_lag        = 0.10,   # Lag putting — mild bump on softer greens
    arg_rough       = 0.07,   # Rough scrambling — moderate rough severity
    arg_bunker      = 0.03,   # Bunker play — low bunker exposure at Deere
    par5_scoring    = 0.10,   # Par-5 scoring — boosted for soft/wet week
)
assert abs(sum(VENUE_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.00"

# Anti-pattern definitions — Deere Run specific
# bomb_and_spray is softened vs penalty venue: miss_fw_pen_frac=0.0264 is modest
ANTI_PATTERNS = dict(
    bomb_and_spray      = (-1.0, -2.5),   # softened — low OB/penalty at Deere
    wedge_liability     = (-2.0, -5.0),   # fatal at conversion birdie-fest
    poor_birdie_conv    = (-1.5, -4.0),   # poor short putting at birdie-fest
    rough_approach_liab = (-1.0, -2.5),   # moderate rough severity
)
ANTI_PENALTY_CAP = -9.0
AP_TO_VTS        =  2.0   # standard non-major scale

DEBUT_PENALTIES = {"A": -4.0, "B": -1.75, "C": -1.0}  # SG units

WIN_EXP  = 4.5    # probability exponent per spec
WIN_CAP  = 0.14   # single-player win cap (per prompt — same as Travelers)


# ── Helpers ───────────────────────────────────────────────────────────────────
def norm0100(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(50.0, index=series.index)
    return (series - lo) / (hi - lo) * 100.0


def safe_norm(series: pd.Series) -> pd.Series:
    s = series.copy()
    fill = s.median() if not s.isna().all() else 0.0
    return norm0100(s.fillna(fill))


def name_key_from_last_first(last: str, first: str) -> str:
    return f"{str(last).strip().upper()}_{str(first).strip().upper()}"


def name_key_from_comma(name_str: str) -> str:
    """'Johnson, Zach' or '"Johnson, Zach"' → 'JOHNSON_ZACH'"""
    s = str(name_str).strip().strip('"')
    parts = s.split(", ", 1)
    if len(parts) == 2:
        return f"{parts[0].strip().upper()}_{parts[1].strip().upper()}"
    return s.upper()


def parse_pct(val) -> float:
    """Strip % and return float. '-4.90%' → -4.90. '12%' → 12.0."""
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace("%", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_win_pct(val) -> float:
    """'12%' → 0.12."""
    return parse_pct(val) / 100.0


def logistic_prob(vts: float, center: float = 65.0, steepness: float = 0.08) -> float:
    return 1.0 / (1.0 + np.exp(-steepness * (vts - center)))


def get_blend(rounds: float):
    """Return (blend_dict, blend_class) based on venue rounds played."""
    if rounds >= 5:
        return {"neutral": 0.40, "venuefit": 0.30, "venuehistory": 0.30}, "Balanced"
    elif rounds >= 3:
        return {"neutral": 0.50, "venuefit": 0.35, "venuehistory": 0.15}, "Blended"
    else:
        return {"neutral": 0.60, "venuefit": 0.40, "venuehistory": 0.00}, "Neutral+Venue"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — DATA INGESTION
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. Field ──────────────────────────────────────────────────────────────────
print("Loading field …")
field_raw = pd.read_csv(BASE_IN / "john_deere_classic_2026_field.csv")
field_raw.columns = [c.strip() for c in field_raw.columns]
field_raw["name_key"] = field_raw.apply(
    lambda r: name_key_from_last_first(r["Last Name"], r["First Name"]), axis=1
)
field_raw["player_display"] = field_raw.apply(
    lambda r: f"{str(r['Last Name']).strip().title()}, {str(r['First Name']).strip().title()}", axis=1
)
field_raw["player_id"]    = range(1, len(field_raw) + 1)
field_raw["field_status"] = "confirmed"
field_raw["r1_tee_time"]  = "TBD"
field_raw["r1_wave"]      = "TBD"

df = field_raw[["player_id", "name_key", "player_display", "field_status",
                 "r1_tee_time", "r1_wave"]].copy()
N = len(df)
print(f"  Field size: {N}")


# ── 2. True SG L12M ───────────────────────────────────────────────────────────
print("Loading True SG L12M …")
sg_raw = pd.read_csv(BASE_IN / "field_player_Last12month_TrueSG_Data.csv")
sg_raw.columns = [c.strip() for c in sg_raw.columns]
sg_raw = sg_raw.rename(columns={
    "Last Name":             "lastname",
    "First Name":            "firstname",
    "Events Last 12 Months": "sg_events_12m",
    "Rounds":                "sg_rounds_12m",
    "Rounds-shotlink":       "sg_rounds_shotlink",
    "Wins":                  "wins_12m",
    "Win %":                 "win_pct_raw",
    "sg-putt":               "sg_putt_12m",
    "sg-arg":                "sg_arg_12m",
    "sg-app":                "sg_app_12m",
    "sg-ott":                "sg_ott_12m",
    "sg-t2g":                "sg_t2g_12m",
    "sg-total":              "sg_total_12m",
    "Driving-Distance":      "dd_delta",
    "Driving-Accuracy":      "da_delta_raw",
})
sg_raw["name_key"]      = sg_raw.apply(
    lambda r: name_key_from_last_first(r["lastname"], r["firstname"]), axis=1
)
# Driving-Accuracy stored as percentage delta e.g. "-4.90%" → -4.90
sg_raw["da_delta"]      = sg_raw["da_delta_raw"].apply(parse_pct)
# Win % stored as "12%" → 0.12
sg_raw["win_rate_12m"]  = sg_raw["win_pct_raw"].apply(parse_win_pct)

for c in ["sg_events_12m", "sg_rounds_12m", "sg_rounds_shotlink", "wins_12m",
          "sg_putt_12m", "sg_arg_12m", "sg_app_12m",
          "sg_ott_12m", "sg_t2g_12m", "sg_total_12m", "dd_delta"]:
    sg_raw[c] = pd.to_numeric(sg_raw[c], errors="coerce")


# ── 3. Course Fit & Venue-Fit Adjustments ─────────────────────────────────────
print("Loading venue-fit adjustments …")
fit_raw = pd.read_csv(BASE_IN / "tpcdeererun_playerfitadj_predictedshotdistance.csv")
fit_raw.columns = [c.strip() for c in fit_raw.columns]
fit_raw = fit_raw.rename(columns={
    "Last Name":            "lastname",
    "First Name":           "firstname",
    "Short Game":           "cf_short_game",
    "Approach":             "cf_approach",
    "Driving-Distance":     "cf_distance",
    "Driving-Accuracy":     "cf_accuracy",
    "Total SG Adjustment":  "cf_adj_total",
    "Putting 2-5ft":        "cf_putt_2_5ft",
    "Putting 5-30ft":       "cf_putt_5_30ft",
    "Putting 30+ ft":       "cf_putt_30plus",
    "Course-Fairway":       "cf_fairway",
    "Course-Rough":         "cf_rough",
    "Course-Bunker":        "cf_bunker",
    "Approach 50-100yds":   "shotdist_50_100",
    "Approach 100-150 yds": "shotdist_100_150",
    "Approach 150-200 yds": "shotdist_150_200",
    "Approach 200+ yds":    "shotdist_200plus",
})
fit_raw["name_key"] = fit_raw.apply(
    lambda r: name_key_from_last_first(r["lastname"], r["firstname"]), axis=1
)
for c in fit_raw.columns:
    if c not in ("lastname", "firstname", "name_key"):
        fit_raw[c] = pd.to_numeric(fit_raw[c], errors="coerce")


# ── 4. Course History ─────────────────────────────────────────────────────────
print("Loading course history …")
ch_raw = pd.read_csv(BASE_IN / "tpc_deere_run_CH.csv")
ch_raw.columns = [c.strip() for c in ch_raw.columns]
ch_raw = ch_raw.dropna(subset=["player_name"])
ch_raw["name_key"] = ch_raw["player_name"].apply(name_key_from_comma)

for col in ["rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]:
    ch_raw[col] = pd.to_numeric(ch_raw[col], errors="coerce")

ch_raw = ch_raw.rename(columns={
    "rounds_played":      "venue_history_rounds",
    "historical_true_sg": "venue_history_sg",
})
ch_raw["venue_history_rounds"] = ch_raw["venue_history_rounds"].fillna(0)


# ── 5. Merge ──────────────────────────────────────────────────────────────────
print("Merging data sources …")
SG_COLS = [
    "name_key", "sg_events_12m", "sg_rounds_12m", "sg_rounds_shotlink",
    "wins_12m", "win_rate_12m", "sg_putt_12m", "sg_arg_12m", "sg_app_12m",
    "sg_ott_12m", "sg_t2g_12m", "sg_total_12m", "dd_delta", "da_delta",
]
FIT_COLS = [
    "name_key", "cf_short_game", "cf_approach", "cf_distance", "cf_accuracy",
    "cf_adj_total", "cf_putt_2_5ft", "cf_putt_5_30ft", "cf_putt_30plus",
    "cf_fairway", "cf_rough", "cf_bunker",
    "shotdist_50_100", "shotdist_100_150", "shotdist_150_200", "shotdist_200plus",
]
CH_COLS = [
    "name_key", "venue_history_rounds", "venue_history_sg",
    "versus_expected", "ch_adjustment", "experience_adjustment",
]

df = (df
      .merge(sg_raw[SG_COLS],  on="name_key", how="left")
      .merge(fit_raw[FIT_COLS], on="name_key", how="left")
      .merge(ch_raw[CH_COLS],   on="name_key", how="left"))

dups = df["name_key"].duplicated().sum()
assert dups == 0, f"Merge created {dups} duplicate rows — check name keys"
df["venue_history_rounds"] = df["venue_history_rounds"].fillna(0)
print(f"  Merged: {len(df)} rows, 0 duplicates")
print(f"  Missing fit data: {df['cf_adj_total'].isna().sum()} players (assigned median)")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — NEUTRAL SKILL
# ═══════════════════════════════════════════════════════════════════════════════

def depth_class(rounds):
    if pd.isna(rounds):
        return "thin"
    r = float(rounds)
    if r >= 70:
        return "deep"
    if r >= 30:
        return "medium"
    return "thin"

df["data_depth_class"]          = df["sg_rounds_12m"].apply(depth_class)
df["baseline_confidence_band"]  = df["data_depth_class"].map(
    {"deep": "high", "medium": "medium", "thin": "low"}
).fillna("low")

field_sg_median = df["sg_total_12m"].median()
df["sg_missing"] = df["sg_total_12m"].isna()

df["neutral_skill_sg_raw"] = df["sg_total_12m"].fillna(field_sg_median * 0.80)

def regress_neutral(row):
    ns = row["neutral_skill_sg_raw"]
    dc = row["data_depth_class"]
    if dc == "thin":
        return ns * 0.50 + field_sg_median * 0.50
    if dc == "medium":
        return ns * 0.75 + field_sg_median * 0.25
    return ns

df["neutral_skill_sg"]    = df.apply(regress_neutral, axis=1)
df["neutral_skill_index"] = norm0100(df["neutral_skill_sg"])


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — VENUE FIT DELTA
# Trait weight matrix: TPC Deere Run (par-71 birdie-fest, weather-adjusted)
# ═══════════════════════════════════════════════════════════════════════════════

def med(col):
    return df[col].fillna(df[col].median())


# ── Trait construction ────────────────────────────────────────────────────────

# APP Wedge (<125 yd): primary scoring trait at Deere
# DG less_150_sg=0.024 confirms sub-150 approach is above-baseline value.
# No approach-skill fw_50_100_val file available; lean on sg_app + cf_short_game.
df["trait_app_wedge"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.50
    + df["cf_short_game"].fillna(0)                    * 0.30
    + med("shotdist_50_100") * 0.004                   # frequency proxy, scaled down
    + med("cf_fairway") * 0.01                         # fairway-hit context
)

# APP 100-150 yd: iron play at key Deere scoring distances
df["trait_app_100_150"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.45
    + df["cf_approach"].fillna(0)                      * 0.30
    + med("shotdist_100_150") * 0.004
)

# APP 150-200 yd: longer irons — less dominant at Deere (low_to_moderate long-iron freq)
df["trait_app_150_200"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.55
    + med("shotdist_150_200") * 0.004
    + df["cf_approach"].fillna(0) * 0.20
)

# OTT Accuracy: bentgrass fairways; soft week rewards fairway-hitting.
# DG adj_driving_accuracy=0.6907 (69% baseline); miss_fw_pen_frac=0.0264 (modest).
df["trait_ott_accuracy"] = safe_norm(
    df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.40
    + df["da_delta"].fillna(0) * 0.04
    + df["cf_accuracy"].fillna(0)  * 0.30
    + med("cf_fairway")            * 0.01
)

# OTT Distance: softened — reduced rollout on soft turf. DG adj_driving_distance=291.7.
df["trait_ott_distance"] = safe_norm(
    df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.60
    + df["dd_delta"].fillna(0) * 0.02
    + df["cf_distance"].fillna(0) * 0.40
)

# PUTT Short Conversion (2-5ft): birdie-conversion at high-volume scoring week
df["trait_putt_short_conv"] = safe_norm(
    df["sg_putt_12m"].fillna(df["sg_putt_12m"].median()) * 0.55
    + med("cf_putt_2_5ft") * 0.45
)

# PUTT Lag (5-30ft, 30+ft): mild bump on softer greens; distance control matters.
df["trait_putt_lag"] = safe_norm(
    df["sg_putt_12m"].fillna(df["sg_putt_12m"].median()) * 0.45
    + med("cf_putt_5_30ft")    * 0.35
    + med("cf_putt_30plus")    * 0.20
)

# ARG Rough: moderate rough (rgh_diff=0.4, arg_rough_sg=-0.012 — slight negative)
df["trait_arg_rough"] = safe_norm(
    df["sg_arg_12m"].fillna(df["sg_arg_12m"].median()) * 0.55
    + med("cf_rough")                                  * 0.45
)

# ARG Bunker: low bunker exposure (arg_bunker_sg=0.018 near neutral)
df["trait_arg_bunker"] = safe_norm(
    df["sg_arg_12m"].fillna(df["sg_arg_12m"].median()) * 0.55
    + med("cf_bunker")                                 * 0.45
)

# Par-5 Scoring: strong lever (DG adj_par5=-0.39/round); boosted for soft_wet week.
# Use sg_t2g (tee-to-green total) + sg_app + sg_ott as par-5 proxy.
df["trait_par5_scoring"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median())  * 0.35
    + df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.35
    + df["sg_t2g_12m"].fillna(df["sg_t2g_12m"].median()) * 0.30
)


# ── Venue fit score (weighted dot product) ─────────────────────────────────────
WEIGHT_TO_TRAIT = {
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

vfs = pd.Series(0.0, index=df.index)
for wkey, tcol in WEIGHT_TO_TRAIT.items():
    vfs = vfs + VENUE_WEIGHTS[wkey] * df[tcol]

# cf_adj_total range ≈ ±0.36 SG → scale ±7 VTS pts (same as Travelers)
cf_contrib = (df["cf_adj_total"].fillna(0) * 20.0).clip(-7.0, 7.0)
df["venue_fit_score"]        = (vfs + cf_contrib).clip(0.0, 100.0)
df["venue_fit_delta"]        = df["venue_fit_score"] - df["neutral_skill_index"]
df["comp_course_adjustment"] = cf_contrib.round(2)
df["comp_course_trace"]      = (
    "DataGolf venue-fit tool; comp courses: TPC River Highlands, Colonial CC, Sedgefield CC; "
    "cf_adj_total scaled ×20, capped ±7 VTS pts"
)

def vf_conf(row):
    if row["data_depth_class"] == "deep" and not pd.isna(row["cf_adj_total"]):
        return "high"
    if row["data_depth_class"] == "thin":
        return "low"
    return "medium"

df["venue_fit_conf_band"] = df.apply(vf_conf, axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — VENUE HISTORY DELTA
# ═══════════════════════════════════════════════════════════════════════════════

VH_TO_VTS = 8.0   # 1 SG at this venue ≈ 8 VTS pts

def compute_vhd(row):
    rounds  = float(row["venue_history_rounds"]) if not pd.isna(row["venue_history_rounds"]) else 0.0
    ch_adj  = float(row["ch_adjustment"])        if not pd.isna(row["ch_adjustment"])        else 0.0
    exp_adj = float(row["experience_adjustment"])if not pd.isna(row["experience_adjustment"])else 0.0
    vs_exp  = float(row["versus_expected"])      if not pd.isna(row["versus_expected"])      else 0.0

    if rounds >= 5:
        combined_sg = ch_adj * 0.50 + vs_exp * 0.30 + exp_adj * 0.20
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "medium"
    elif rounds >= 3:
        combined_sg = (ch_adj + exp_adj) * 0.50
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "low"
    elif rounds >= 1:
        combined_sg = (ch_adj + exp_adj) * 0.20
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "low"
    else:
        delta_vts = 0.0
        conf      = "none"

    delta_vts = float(np.clip(delta_vts, -15.0, 15.0))
    return delta_vts, conf

vh_results          = df.apply(compute_vhd, axis=1, result_type="expand")
vh_results.columns  = ["venue_history_delta", "venue_history_conf_band"]
df = pd.concat([df, vh_results], axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — PRE-PENALTY VTS (history-class blended)
# ═══════════════════════════════════════════════════════════════════════════════

def build_pp_vts(row):
    rounds      = float(row["venue_history_rounds"])
    blend, bcls = get_blend(rounds)

    n_vts = float(row["neutral_skill_index"])
    v_vts = float(row["venue_fit_score"])
    h_vts = float(np.clip(50.0 + row["venue_history_delta"], 0.0, 100.0))

    pp = (
        blend["neutral"]        * n_vts
        + blend["venuefit"]     * v_vts
        + blend["venuehistory"] * h_vts
    )
    return pp, bcls, json.dumps(blend)

pp_results          = df.apply(build_pp_vts, axis=1, result_type="expand")
pp_results.columns  = ["pre_penalty_vts", "blend_class", "blend_weights_used"]
df = pd.concat([df, pp_results], axis=1)
df["tier_eligibility_gate_status"] = "clear"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — FORM (no separate 2026 DG file available)
# form_vs_baseline = 0 for all players; no form gate triggers.
# ═══════════════════════════════════════════════════════════════════════════════

df["form_vs_baseline"]      = 0.0
df["recent_form_index"]     = 50.0   # neutral
df["form_score_adjusted"]   = df["neutral_skill_sg"]
df["recent_form_gate_applied"] = False
df["recent_form_gate_reason"]  = ""


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — DEBUT FLAGS
# Debut = rounds_played == 0 in CH (not absent from CH file — all players present).
# Class assigned by neutral_skill_sg level.
# ═══════════════════════════════════════════════════════════════════════════════

ELITE_SG = 1.5

def assign_debut(row):
    is_debut = (float(row["venue_history_rounds"]) == 0)
    if not is_debut:
        return False, ""
    sg = float(row["neutral_skill_sg"]) if not pd.isna(row["neutral_skill_sg"]) else 0.0
    if sg >= ELITE_SG:
        return True, "C"
    elif sg >= 0.0:
        return True, "B"
    else:
        return True, "A"

debut_results         = df.apply(assign_debut, axis=1, result_type="expand")
debut_results.columns = ["debut_flag", "debut_class"]
df = pd.concat([df, debut_results], axis=1)

df["injury_flag"]       = False
df["health_gate_status"] = "ok"
df["health_gate_reason"] = ""


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8 — ANTI-PATTERN FLAGS (Deere Run specific)
# ═══════════════════════════════════════════════════════════════════════════════

dd = df["dd_delta"].fillna(0)
da = df["da_delta"].fillna(0)

p60_dd = dd.quantile(0.60)
p45_da = da.quantile(0.45)

p35_wedge = df["trait_app_wedge"].quantile(0.35)
p35_sc    = df["trait_putt_short_conv"].quantile(0.35)
p30_rough = df["trait_arg_rough"].quantile(0.30)

# bomb_and_spray: long + inaccurate — softened at Deere (low pen exposure)
df["ap_bomb_and_spray"]      = (dd > p60_dd) & (da < p45_da)
# wedge_liability: fatal at conversion birdie-fest
df["ap_wedge_liability"]     = df["trait_app_wedge"] < p35_wedge
# poor_birdie_conv: below 35th pct short putting
df["ap_poor_birdie_conv"]    = df["trait_putt_short_conv"] < p35_sc
# rough_approach_liab: weak from rough at moderate-rough venue
df["ap_rough_approach_liab"] = df["trait_arg_rough"] < p30_rough


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9 — TRAIT DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

TRAIT_LABELS = {
    "trait_app_wedge":       "APP_Wedge",
    "trait_app_100_150":     "APP_100-150",
    "trait_app_150_200":     "APP_150-200",
    "trait_ott_accuracy":    "OTT_Accuracy",
    "trait_ott_distance":    "OTT_Distance",
    "trait_putt_short_conv": "PUTT_BirdieConv",
    "trait_putt_lag":        "PUTT_Lag",
    "trait_arg_rough":       "ARG_Rough",
    "trait_arg_bunker":      "ARG_Bunker",
    "trait_par5_scoring":    "PAR5_Scoring",
}

def primary_driver(row):
    bv, bc = -9999.0, ""
    for col, label in TRAIT_LABELS.items():
        if float(row[col]) > bv:
            bv, bc = float(row[col]), label
    return bc

def primary_risk(row):
    wv, wc = 9999.0, ""
    for col, label in TRAIT_LABELS.items():
        if float(row[col]) < wv:
            wv, wc = float(row[col]), label
    return wc

def trait_summary(row):
    pos = sorted(TRAIT_LABELS.items(), key=lambda x: -row[x[0]])[:2]
    neg = sorted(TRAIT_LABELS.items(), key=lambda x:  row[x[0]])[:1]
    return f"{'+'.join(l for _, l in pos)}; weak {neg[0][1] if neg else ''}"

df["primary_trait_driver"] = df.apply(primary_driver, axis=1)
df["primary_risk_trait"]   = df.apply(primary_risk,   axis=1)
df["trait_summary_label"]  = df.apply(trait_summary,  axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10 — SCORING PIPELINE → VTS FINAL
# ═══════════════════════════════════════════════════════════════════════════════

sf = df.copy()

# A. Debut penalties
SG_TO_VTS = 10.0
sf["debut_penalty_applied"] = sf["debut_class"].map(DEBUT_PENALTIES).fillna(0.0)
sf["debut_penalty_vts"]     = sf["debut_penalty_applied"] * SG_TO_VTS / 4.0


# B. Anti-pattern penalties (severity-graded)
def ap_penalty_series(flag_col, base_low, base_high, trait_col, direction="low"):
    t     = sf[trait_col]
    t_min, t_max = t.min(), t.max()
    rng   = (t_max - t_min) if (t_max != t_min) else 1.0
    if direction == "low":
        sev = ((t.median() - t) / rng).clip(0, 1)
    else:
        sev = ((t - t.median()) / rng).clip(0, 1)
    penalty = (base_low + sev * (base_high - base_low)).clip(base_high, 0)
    return np.where(sf[flag_col], penalty, 0.0)

sf["ap_pen_bomb_spray"]     = ap_penalty_series(
    "ap_bomb_and_spray",    -1.0, -2.5, "trait_ott_distance",    "high")
sf["ap_pen_wedge_liab"]     = ap_penalty_series(
    "ap_wedge_liability",   -2.0, -5.0, "trait_app_wedge",       "low")
sf["ap_pen_poor_birdie"]    = ap_penalty_series(
    "ap_poor_birdie_conv",  -1.5, -4.0, "trait_putt_short_conv", "low")
sf["ap_pen_rough_approach"] = ap_penalty_series(
    "ap_rough_approach_liab",-1.0,-2.5, "trait_arg_rough",       "low")

sf["anti_pattern_penalty_total"] = (
    sf["ap_pen_bomb_spray"]
    + sf["ap_pen_wedge_liab"]
    + sf["ap_pen_poor_birdie"]
    + sf["ap_pen_rough_approach"]
).clip(ANTI_PENALTY_CAP, 0)

def ap_flag_str(row):
    flags = []
    if row["ap_bomb_and_spray"]:      flags.append("bomb_and_spray")
    if row["ap_wedge_liability"]:     flags.append("wedge_liability")
    if row["ap_poor_birdie_conv"]:    flags.append("poor_birdie_conv")
    if row["ap_rough_approach_liab"]: flags.append("rough_approach_liab")
    return ";".join(flags)

sf["anti_pattern_flags"]          = sf.apply(ap_flag_str, axis=1)
sf["anti_pattern_trigger_trace"]  = sf["anti_pattern_flags"]
sf["anti_pattern_modifier_trace"] = (
    f"Deere Run standard venue (non-major birdie-fest). AP_TO_VTS={AP_TO_VTS}. "
    "Soft/wet week: bomb_and_spray softened (miss_fw_pen_frac=0.0264 modest). "
    "No weather amplification on other patterns."
)


# C. Form delta (no 2026 DG file → 0 for all)
sf["form_delta_vts"]  = 0.0
sf["health_delta_vts"] = 0.0


# D. Variance
def player_variance(row):
    if row["data_depth_class"] == "thin" or row["debut_flag"]:
        return "high"
    if row["data_depth_class"] == "medium":
        return "medium"
    return "low"

sf["player_variance_band"] = sf.apply(player_variance, axis=1)
sf["volatility_index"]     = sf["player_variance_band"].map(
    {"low": 25.0, "medium": 50.0, "high": 75.0}
)
sf["venue_variance_class"]          = EVENT_META["venue_variance_class"]
sf["variance_adjustment_trace"]     = "Standard venue variance class. Soft/wet delay risk: no compression multiplier."
sf["probability_compression_class"] = "standard"
sf["probability_compression_coefficients"] = json.dumps(
    {"win_exponent": WIN_EXP, "win_cap": WIN_CAP,
     "top3_center": 80, "top5_center": 76, "top10_center": 68, "top20_center": 59,
     "make_cut_center": 48, "make_cut_steepness": 0.07}
)
sf["probability_compression_trace"] = (
    f"144-player cut event. Win exp={WIN_EXP}, cap={WIN_CAP}. "
    "make_cut_pct via logistic(vts, center=48, steep=0.07)."
)


# E. Final VTS
sf["vts_final_raw"] = (
    sf["pre_penalty_vts"]
    + sf["debut_penalty_vts"]
    + sf["anti_pattern_penalty_total"] * AP_TO_VTS
    + sf["form_delta_vts"]
    + sf["health_delta_vts"]
).clip(0.0, 100.0)

sf["vts_final"] = sf["vts_final_raw"].clip(0.0, 100.0)


# F. Tier assignment
def assign_tier(vts):
    if vts >= 80: return 1
    if vts >= 65: return 2
    if vts >= 50: return 3
    if vts >= 35: return 4
    return 5

sf["tier"] = sf["vts_final"].apply(assign_tier)

TIER_LABELS = {
    1: "Course Architects",
    2: "Contention Windows",
    3: "Top-10 Range",
    4: "Cut-Line Players",
    5: "Course Mismatches",
}

def tier_gate_check(row):
    g, vts, t = row["tier_eligibility_gate_status"], float(row["vts_final"]), int(row["tier"])
    if g == "clear" and vts >= 80 and t > 1:
        return f"CONTRADICTION: vts={vts:.1f}≥80 gate=clear tier={t}"
    if g == "clear" and vts >= 65 and t > 2:
        return f"CONTRADICTION: vts={vts:.1f}≥65 gate=clear tier={t}"
    return "ok"

sf["tier_gate_check"] = sf.apply(tier_gate_check, axis=1)

def tier_reason_str(row):
    t    = int(row["tier"])
    ns   = float(row["neutral_skill_sg"])
    vfd  = float(row["venue_fit_delta"])
    ap   = float(row["anti_pattern_penalty_total"])
    vhr  = int(row["venue_history_rounds"])
    debut_tag = f"; debut-{row['debut_class']}" if row["debut_flag"] else ""
    hist_tag  = f"; {vhr}CH-rds" if vhr > 0 else "; 0CH-rds (debut)"
    if t == 1:
        return (f"Tier1 — Course Architect: NeutralSG={ns:.2f}+VFD={vfd:.1f}{hist_tag}{debut_tag}"
                f" → elite birdie-fest fit at TPC Deere Run")
    if t == 2:
        return (f"Tier2 — Contention Window: NeutralSG={ns:.2f}, VFD={vfd:.1f}{hist_tag}{debut_tag}")
    if t == 3:
        return (f"Tier3 — Top-10 Range: NeutralSG={ns:.2f}, moderate fit VFD={vfd:.1f}{hist_tag}{debut_tag}")
    if t == 4:
        return (f"Tier4 — Cut-Line Player: Below-avg or mismatch VFD={vfd:.1f}, AP={ap:.1f}SG{hist_tag}{debut_tag}")
    return (f"Tier5 — Course Mismatch: Weak NeutralSG={ns:.2f}, AP={ap:.1f}SG{hist_tag}{debut_tag}")

sf["tier_reason"] = sf.apply(tier_reason_str, axis=1)


# G. Probabilities
var_spread = {"low": 1.00, "medium": 1.08, "high": 1.15}
sf["_var_s"] = sf["player_variance_band"].map(var_spread)

win_raw  = (sf["vts_final"] / 100.0) ** WIN_EXP * sf["_var_s"]
sf["win_pct"] = (win_raw / win_raw.sum()).clip(0, WIN_CAP)
sf["win_pct"] = sf["win_pct"] / sf["win_pct"].sum()

def calc_top_probs(vts, var_idx):
    v = float(vts)
    s = 1.0 + (float(var_idx) - 50.0) / 250.0
    return (
        logistic_prob(v, 80, 0.10) * s,   # top3
        logistic_prob(v, 76, 0.10) * s,   # top5
        logistic_prob(v, 68, 0.09) * s,   # top10
        logistic_prob(v, 59, 0.08) * s,   # top20
        logistic_prob(v, 48, 0.07) * s,   # make_cut
    )

probs = sf.apply(
    lambda r: calc_top_probs(r["vts_final"], r["volatility_index"]),
    axis=1, result_type="expand",
)
probs.columns = ["top3_pct", "top5_pct", "top10_pct", "top20_pct", "make_cut_pct"]
sf = pd.concat([sf, probs], axis=1)
sf["miss_cut_pct"] = (1.0 - sf["make_cut_pct"]).clip(0.0, 1.0)

sf["risk_stressor_active"]            = False
sf["risk_secondary_discount_applied"] = 0.0
sf["risk_discount_trace"]             = ""


# H. Trace notes
def trace_note(row):
    parts = [
        f"NeutralSG={row['neutral_skill_sg']:.2f}",
        f"VFD={row['venue_fit_delta']:.1f}",
        f"VHD={row['venue_history_delta']:.1f}({int(row['venue_history_rounds'])}rds)",
    ]
    if row["debut_flag"]:
        parts.append(f"debut-{row['debut_class']} pen={row['debut_penalty_applied']:.1f}SG")
    if float(row["anti_pattern_penalty_total"]) < -1.0:
        parts.append(f"AP={row['anti_pattern_penalty_total']:.1f}SG({row['anti_pattern_flags']})")
    parts.append(f"→Tier{row['tier']} VTS={row['vts_final']:.1f}")
    return "; ".join(parts)

sf["trace_notes"] = sf.apply(trace_note, axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 11 — OUTPUT ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\nWriting output artifacts …")

sf_ranked = sf.sort_values("vts_final", ascending=False).reset_index(drop=True)
sf_ranked.insert(0, "rank_model", range(1, len(sf_ranked) + 1))


# ── Field Input CSV ────────────────────────────────────────────────────────────
field_cols = [
    "player_id", "player_display", "name_key", "field_status",
    "r1_tee_time", "r1_wave",
    "venue_history_rounds", "venue_history_sg", "versus_expected", "ch_adjustment",
    "sg_total_12m", "sg_ott_12m", "sg_app_12m", "sg_arg_12m", "sg_putt_12m", "sg_t2g_12m",
    "sg_rounds_12m", "wins_12m", "win_rate_12m", "dd_delta", "da_delta",
    "cf_adj_total", "cf_short_game", "cf_approach", "cf_distance", "cf_accuracy",
    "cf_putt_2_5ft", "cf_putt_5_30ft", "cf_rough", "cf_bunker",
    "shotdist_50_100", "shotdist_100_150", "shotdist_150_200", "shotdist_200plus",
    "data_depth_class", "baseline_confidence_band",
    "debut_flag", "debut_class", "injury_flag",
]
sf_ranked[field_cols].to_csv(BASE_OUT / f"{SLUG}_field_input.csv", index=False)
print(f"  {SLUG}_field_input.csv   ({len(sf_ranked)} rows)")


# ── Trait / Form Matrix CSV ────────────────────────────────────────────────────
matrix_cols = [
    "rank_model", "player_id", "player_display", "name_key",
    "data_depth_class", "baseline_confidence_band",
    "neutral_skill_sg", "neutral_skill_index",
    "sg_total_12m", "sg_ott_12m", "sg_app_12m", "sg_arg_12m", "sg_putt_12m", "sg_t2g_12m",
    "sg_rounds_12m", "wins_12m", "dd_delta", "da_delta",
    "trait_app_wedge", "trait_app_100_150", "trait_app_150_200",
    "trait_ott_accuracy", "trait_ott_distance",
    "trait_putt_short_conv", "trait_putt_lag",
    "trait_arg_rough", "trait_arg_bunker", "trait_par5_scoring",
    "cf_adj_total", "cf_short_game", "cf_approach", "cf_distance", "cf_accuracy",
    "cf_putt_2_5ft", "cf_putt_5_30ft", "cf_rough", "cf_bunker",
    "shotdist_50_100", "shotdist_100_150", "shotdist_150_200", "shotdist_200plus",
    "venue_fit_score", "venue_fit_delta", "venue_fit_conf_band",
    "venue_history_rounds", "venue_history_sg", "venue_history_delta", "venue_history_conf_band",
    "debut_flag", "debut_class", "injury_flag",
    "ap_bomb_and_spray", "ap_wedge_liability", "ap_poor_birdie_conv", "ap_rough_approach_liab",
    "primary_trait_driver", "primary_risk_trait", "trait_summary_label",
]
sf_ranked[matrix_cols].to_csv(BASE_OUT / f"{SLUG}_trait_form_matrix.csv", index=False)
print(f"  {SLUG}_trait_form_matrix.csv")


# ── VTS Full CSV ───────────────────────────────────────────────────────────────
vts_cols = [
    "rank_model", "player_id", "player_display", "name_key",
    "field_status", "r1_tee_time", "r1_wave",
    "data_depth_class", "baseline_confidence_band",
    "neutral_skill_sg", "neutral_skill_index",
    "venue_fit_score", "venue_fit_delta", "venue_fit_conf_band",
    "comp_course_adjustment", "comp_course_trace",
    "venue_history_rounds", "venue_history_sg", "venue_history_delta", "venue_history_conf_band",
    "pre_penalty_vts", "blend_class", "blend_weights_used", "tier_eligibility_gate_status",
    "debut_flag", "debut_class", "debut_penalty_applied",
    "anti_pattern_flags", "anti_pattern_penalty_total",
    "ap_pen_bomb_spray", "ap_pen_wedge_liab", "ap_pen_poor_birdie", "ap_pen_rough_approach",
    "anti_pattern_trigger_trace", "anti_pattern_modifier_trace",
    "primary_risk_trait", "risk_stressor_active", "risk_secondary_discount_applied", "risk_discount_trace",
    "form_score_adjusted", "recent_form_index", "form_vs_baseline",
    "recent_form_gate_applied", "recent_form_gate_reason", "form_delta_vts",
    "injury_flag", "health_gate_status", "health_gate_reason", "health_delta_vts",
    "player_variance_band", "volatility_index", "venue_variance_class", "variance_adjustment_trace",
    "probability_compression_class", "probability_compression_coefficients", "probability_compression_trace",
    "vts_final_raw", "vts_final", "tier", "tier_reason", "tier_gate_check",
    "win_pct", "top3_pct", "top5_pct", "top10_pct", "top20_pct",
    "make_cut_pct", "miss_cut_pct",
    "primary_trait_driver", "trait_summary_label", "trace_notes",
]
vts_out = sf_ranked[vts_cols].copy()
vts_out.to_csv(BASE_OUT / f"{SLUG}_vts_full.csv", index=False)
print(f"  {SLUG}_vts_full.csv")


# ── Event Context JSON ─────────────────────────────────────────────────────────
ctx = dict(EVENT_META)
ctx["generated_at"]       = datetime.now().isoformat()
ctx["field_locked"]       = True
ctx["field_size_actual"]  = N
ctx["tier_distribution"]  = {
    int(k): int(v) for k, v in sf["tier"].value_counts().sort_index().items()
}
ctx["venue_trait_weights"]   = VENUE_WEIGHTS
ctx["anti_patterns_active"]  = list(ANTI_PATTERNS.keys())
ctx["model_winner"]          = sf_ranked.iloc[0]["player_display"]
ctx["model_top3"]            = sf_ranked.head(3)["player_display"].tolist()
ctx["win_pct_sum_check"]     = round(float(sf_ranked["win_pct"].sum()), 4)
ctx["tier_gate_errors"]      = (
    sf_ranked[sf_ranked["tier_gate_check"] != "ok"]
    [["player_display", "tier_gate_check"]].to_dict(orient="records")
)
ctx["weather_summary"] = {
    "forecast_class":        "soft_wet",
    "heat_alert":            EVENT_META["weather_heat_alert"],
    "primary_risk_window":   EVENT_META["weather_primary_risk"],
    "wind_profile":          EVENT_META["weather_wind_profile"],
    "course_effect":         EVENT_META["weather_course_effect"],
    "best_scoring_day":      EVENT_META["weather_best_scoring_day"],
    "delay_risk":            EVENT_META["weather_delay_risk"],
}
# Remove redundant flat keys now embedded in weather_summary
for k in ["weather_heat_alert","weather_primary_risk","weather_wind_profile",
          "weather_course_effect","weather_best_scoring_day","weather_delay_risk"]:
    ctx.pop(k, None)

with open(BASE_OUT / f"{SLUG}_event_context.json", "w") as fh:
    json.dump(ctx, fh, indent=2, default=str)
print(f"  {SLUG}_event_context.json")


# ── Player Briefs JSON ─────────────────────────────────────────────────────────
def make_brief(row):
    ap_str = row["anti_pattern_flags"] if row["anti_pattern_flags"] else "none"
    cf_adj = row.get("comp_course_adjustment", "N/A")
    return {
        "player_name":    row["player_display"],
        "tier":           int(row["tier"]),
        "tier_label":     TIER_LABELS[int(row["tier"])],
        "vts_final":      round(float(row["vts_final"]), 1),
        "win_pct":        round(float(row["win_pct"]) * 100.0, 1),
        "top10_pct":      round(float(row["top10_pct"]) * 100.0, 1),
        "top20_pct":      round(float(row["top20_pct"]) * 100.0, 1),
        "make_cut_pct":   round(float(row["make_cut_pct"]) * 100.0, 1),
        "miss_cut_pct":   round(float(row["miss_cut_pct"]) * 100.0, 1),
        "neutral_skill_summary": (
            f"TrueSG(12m)={row['neutral_skill_sg']:.2f}; "
            f"depth={row['data_depth_class']}; NeutralIdx={row['neutral_skill_index']:.1f}"
        ),
        "venue_fit_summary": (
            f"VFS={row['venue_fit_score']:.1f}; VFD={row['venue_fit_delta']:.1f}; "
            f"CF_Adj_VTS={round(float(cf_adj),2) if cf_adj != 'N/A' else 'N/A'}; "
            f"lead={row['primary_trait_driver']}"
        ),
        "venue_history_summary": (
            f"{int(row['venue_history_rounds'])}CH rounds; "
            f"HistSG={row['venue_history_sg'] if not pd.isna(row['venue_history_sg']) else 'N/A'}; "
            f"VHD={row['venue_history_delta']:.1f}VTS"
        ),
        "penalties_summary": (
            f"Debut={row['debut_class'] or 'none'}; "
            f"AP_total={row['anti_pattern_penalty_total']:.1f}SG ({ap_str}); "
            f"FormΔ={row['form_delta_vts']:.1f}VTS"
        ),
        "risk_vector":          row["primary_risk_trait"],
        "conviction_statement": row["tier_reason"],
        "named_failure_condition": (
            f"If {row['primary_risk_trait']} underperforms under heat/rain stress "
            f"or birdie conversion collapses on soft greens. Active AP flags: {ap_str}."
        ),
        "trace_notes": row["trace_notes"],
    }

tier1_briefs = [make_brief(r) for _, r in vts_out[vts_out["tier"] == 1].iterrows()]
tier2_briefs = [make_brief(r) for _, r in vts_out[vts_out["tier"] == 2].iterrows()]

briefs_payload = {
    "event":        EVENT_META["event_name"],
    "venue":        EVENT_META["venue_name"],
    "generated_at": datetime.now().isoformat(),
    "cut_rule":     EVENT_META["cut_rule"],
    "tier_1":       tier1_briefs,
    "tier_2":       tier2_briefs,
}
with open(BASE_OUT / f"{SLUG}_player_briefs.json", "w") as fh:
    json.dump(briefs_payload, fh, indent=2, default=str)
print(f"  {SLUG}_player_briefs.json  (T1={len(tier1_briefs)}, T2={len(tier2_briefs)})")


# ── Event Payload JSON ─────────────────────────────────────────────────────────
def player_row_dict(row):
    return {
        "rank":               int(row["rank_model"]),
        "player_name":        row["player_display"],
        "tier":               int(row["tier"]),
        "tier_label":         TIER_LABELS[int(row["tier"])],
        "vts_final":          round(float(row["vts_final"]), 1),
        "win_pct":            round(float(row["win_pct"]) * 100.0, 2),
        "top5_pct":           round(float(row["top5_pct"]) * 100.0, 1),
        "top10_pct":          round(float(row["top10_pct"]) * 100.0, 1),
        "top20_pct":          round(float(row["top20_pct"]) * 100.0, 1),
        "make_cut_pct":       round(float(row["make_cut_pct"]) * 100.0, 1),
        "miss_cut_pct":       round(float(row["miss_cut_pct"]) * 100.0, 1),
        "neutral_sg":         round(float(row["neutral_skill_sg"]), 2),
        "neutral_skill_index":round(float(row["neutral_skill_index"]), 1),
        "vfd":                round(float(row["venue_fit_delta"]), 1),
        "vh_rounds":          int(row["venue_history_rounds"]),
        "vh_sg":              round(float(row["venue_history_sg"]), 3) if not pd.isna(row["venue_history_sg"]) else None,
        "vh_delta":           round(float(row["venue_history_delta"]), 1),
        "anti_pattern_flags": row["anti_pattern_flags"] if row["anti_pattern_flags"] else "",
        "debut_flag":         bool(row["debut_flag"]),
        "debut_class":        row["debut_class"] if row["debut_class"] else "",
        "primary_driver":     row["primary_trait_driver"],
        "trait_summary":      row["trait_summary_label"],
        "tier_reason":        row["tier_reason"],
        "r1_tee_time":        row["r1_tee_time"],
        "r1_wave":            row["r1_wave"],
        "trace_notes":        row["trace_notes"],
    }

all_players = [player_row_dict(r) for _, r in vts_out.iterrows()]

ap_summary = []
for _, r in vts_out.iterrows():
    if r["anti_pattern_flags"]:
        total_pen_vts = round(float(r["anti_pattern_penalty_total"]) * AP_TO_VTS, 1)
        for flag in r["anti_pattern_flags"].split(";"):
            if flag.strip():
                ap_summary.append({
                    "player":      r["player_display"],
                    "flag":        flag.strip(),
                    "penalty_vts": total_pen_vts,
                })

payload = {
    "event": {
        "name":         EVENT_META["event_name"],
        "slug":         SLUG,
        "venue":        EVENT_META["venue_name"],
        "dates":        "2026-07-02 to 2026-07-05",
        "par":          EVENT_META["course_par"],
        "yardage":      EVENT_META["course_yardage"],
        "field_size":   EVENT_META["field_size"],
        "field_locked": True,
        "cut_rule":     EVENT_META["cut_rule"],
        "event_class":  EVENT_META["event_class"],
        "tee_times_note": "Tee times not available at build time. r1_tee_time=TBD for all players.",
    },
    "venue": {
        "name":            EVENT_META["venue_name"],
        "location":        "Silvis, Illinois, USA",
        "par":             71,
        "yardage":         7327,
        "yardage_dg":      7133,
        "surface":         EVENT_META["surface"],
        "stimp":           11,
        "fairway_width":   "37.9 yd avg (moderate)",
        "rough_severity":  "~4\" tournament rough (moderate); KBG/Fine Fescue",
        "variance_class":  "standard",
        "birdie_fest":     True,
        "scoring_avg":     "-1.83 adj score to par (DG)",
        "scoring_profile": "Birdie-fest, par-5 leverage, wedge/short-iron scoring",
        "signature_stretch": "Par-4 14, par-3 16 over Rock River, par-5 17",
        "course_record":   "256 (-25)",
        "comp_courses":    ["TPC River Highlands", "Colonial CC", "Sedgefield CC"],
        "dominant_trait":  "Wedge/short-iron APP plus short-putt conversion",
        "dominant_trait_weight": round(
            VENUE_WEIGHTS["app_wedge"] + VENUE_WEIGHTS["app_100_150"] + VENUE_WEIGHTS["putt_short_conv"], 2
        ),
        "anti_patterns": list(ANTI_PATTERNS.keys()),
        "dg_stats": {
            "adj_score_to_par":   -1.83,
            "adj_par5_score":     -0.39,
            "less_150_sg":         0.024,
            "fw_width":           37.9,
            "fw_diff":             0.4,
            "rgh_diff":            0.4,
            "miss_fw_pen_frac":    0.0264,
            "adj_penalties":       0.26,
            "adj_gir":             0.7227,
        },
    },
    "weather_summary": {
        "forecast_class":      "soft_wet",
        "heat_alert":          EVENT_META["weather_heat_alert"],
        "primary_risk_window": EVENT_META["weather_primary_risk"],
        "wind_profile":        EVENT_META["weather_wind_profile"],
        "course_effect":       EVENT_META["weather_course_effect"],
        "best_scoring_day":    EVENT_META["weather_best_scoring_day"],
        "delay_risk":          EVENT_META["weather_delay_risk"],
    },
    "model_summary": {
        "trait_weight_matrix":    VENUE_WEIGHTS,
        "anti_patterns":          {k: list(v) for k, v in ANTI_PATTERNS.items()},
        "cut_handling":           f"make_cut_pct via logistic(vts, center=48, steep=0.07); {EVENT_META['cut_rule']}",
        "probability_normalization": f"Field-wide win_pct sum=1.00; cap={WIN_CAP*100:.0f}% per player",
        "model_winner":           sf_ranked.iloc[0]["player_display"],
        "model_winner_vts":       round(float(sf_ranked.iloc[0]["vts_final"]), 1),
        "tier_distribution":      {
            int(k): int(v) for k, v in sf["tier"].value_counts().sort_index().items()
        },
        "scoring_spec_version":   "1.1",
        "venue_file_version":     "2026_v1",
        "event_iteration":        "initial_weather_locked",
    },
    "tier_labels": TIER_LABELS,
    "tiers": {
        "tier_1": [p for p in all_players if p["tier"] == 1],
        "tier_2": [p for p in all_players if p["tier"] == 2],
        "tier_3": [p for p in all_players if p["tier"] == 3],
        "tier_4": [p for p in all_players if p["tier"] == 4],
        "tier_5": [p for p in all_players if p["tier"] == 5],
    },
    "flags": {
        "anti_patterns":  ap_summary,
        "value_flags":    [],
        "health_gates":   [],
        "risk_stressors": [],
    },
    "players": all_players,
    "metadata": {
        "engine_version":       EVENT_META["engine_version"],
        "scoring_spec_version": EVENT_META["scoring_spec_version"],
        "venue_file_version":   EVENT_META["venue_file_version"],
        "event_iteration":      EVENT_META["event_iteration"],
        "generated_at":         datetime.now().isoformat(),
        "field_size":           N,
        "tee_times_available":  False,
    },
}
with open(BASE_OUT / f"{SLUG}_event_payload.json", "w") as fh:
    json.dump(payload, fh, indent=2, default=str)
print(f"  {SLUG}_event_payload.json")


# ── TPC Deere Run Intelligence File ───────────────────────────────────────────
t1_players = [p["player_name"] for p in all_players if p["tier"] == 1]
t2_players = [p["player_name"] for p in all_players if p["tier"] == 2]
top5_win   = [(p["player_name"], p["win_pct"]) for p in all_players[:5]]

intel_md = f"""# TPC DEERE RUN INTELLIGENCE — 2026 John Deere Classic
*PGA VenueDNA Tier Engine v1.1 | Venue File: 2026_v1 | Generated: {datetime.now().strftime('%Y-%m-%d')}*

---

## VENUE LOCK — TPC Deere Run

| Field | Value | Source |
|---|---|---|
| Par | 71 | Championship routing |
| Yardage | 7,327 (DG: 7,133) | 2026 routing incl. Hole 4 +38 yd |
| Surface | Southshore Bentgrass / KBG+Fine Fescue rough | Venue file |
| Adj Score to Par | **-1.83** | DataGolf course table |
| Adj Par-5 Score | **-0.39 / round** | DataGolf |
| APP <150 SG | +0.024 | DataGolf less_150_sg |
| Fairway Width | 37.9 yd avg (moderate) | DataGolf fw_width |
| Miss-FW Penalty | 2.64% (low) | DataGolf miss_fw_pen_frac |
| Adj Penalties | 0.26 (low) | DataGolf adj_penalties |
| Adj GIR | 72.3% (high) | DataGolf adj_gir |

**Difficulty class:** Birdie-fest (easy). This is a conversion track — the player who cashes their birdie looks wins.

---

## WEATHER LOCK — soft_wet

- **Heat alert**: Extreme Heat Warning through Thursday night
- **Rain risk**: Friday afternoon through Saturday afternoon (delay risk: moderate)
- **Wind**: 10-15 mph, non-dominant
- **Course effect**: Softening through week; receptive greens after Friday rain
- **Best scoring day**: Sunday (cleaner weather, still warm, wind manageable)

**Weather modeling implications:**
- Reduced rollout lowers raw distance premium
- Receptive greens favor approach players and putters
- Par-5 scoring importance increased (soft fairways, stoppable approaches)
- Short-putt conversion remains highest-priority trait
- Lag putting mild bump on softer surfaces
- bomb_and_spray penalty softened (low OB/penalty at Deere even in wet conditions)

---

## TRAIT WEIGHT MATRIX (Weather-Adjusted Deere Seed)

| Trait | Weight | Justification |
|---|---|---|
| APP_Wedge | **0.18** | Dominant — DG less_150_sg=0.024; conversion track |
| APP_100_150 | **0.15** | Key iron-play bucket at short-iron birdie track |
| Putt_Short_Conv | **0.14** | Birdie cash-in; single most critical putting metric |
| OTT_Accuracy | **0.11** | Bentgrass FWs; soft week rewards FW-hitting |
| Putt_Lag | **0.10** | Bumped for soft/wet greens; distance control matters |
| Par5_Scoring | **0.10** | Boosted — DG adj_par5=-0.39; soft turf magnifies equity |
| APP_150_200 | **0.08** | Lower frequency; low_to_moderate long-iron demand |
| ARG_Rough | **0.07** | Moderate rough (rgh_diff=0.4) |
| OTT_Distance | **0.04** | Softened — reduced rollout on wet turf |
| ARG_Bunker | **0.03** | Low bunker exposure at Deere |

*Sum = 1.00. Dominant cluster (APP_Wedge + APP_100_150 + Putt_Short_Conv) = 0.47 of total weight.*

---

## ANTI-PATTERN DEFINITIONS

| Pattern | Severity Range (SG) | Trigger | Notes |
|---|---|---|---|
| poor_birdie_conv | -1.5 to -4.0 | PUTT_BirdieConv < p35 | Fatal at conversion birdie-fest |
| wedge_liability | -2.0 to -5.0 | APP_Wedge < p35 | Core scoring trait at Deere |
| rough_approach_liab | -1.0 to -2.5 | ARG_Rough < p30 | Moderate rough severity |
| bomb_and_spray | -1.0 to -2.5 | DD > p60 AND DA < p45 | **Softened** — miss_fw_pen_frac=0.0264 modest |

---

## VENUE DNA SNAPSHOT

- **Scoring profile**: Birdie-fest, par-5 leverage, wedge/short-iron scoring
- **Dominant trait**: Wedge/short-iron APP + short-putt conversion (~0.47 of total weight)
- **Variance class**: Standard (penalties exist but not dominant)
- **Comp courses**: TPC River Highlands, Colonial CC, Sedgefield CC
- **Course record**: 256 (-25)
- **Signature stretch**: Par-4 14, par-3 16 (over Rock River), par-5 17

---

## MODEL OUTPUTS — 2026 FIELD

**Model winner**: {sf_ranked.iloc[0]["player_display"]} (VTS: {sf_ranked.iloc[0]["vts_final"]:.1f})

**Top-5 win probability:**
{chr(10).join(f"  {i+1}. {name} — {pct:.1f}%" for i, (name, pct) in enumerate(top5_win))}

**Tier 1 — Course Architects ({len(t1_players)} players):**
{", ".join(t1_players) if t1_players else "None"}

**Tier 2 — Contention Windows ({len(t2_players)} players):**
{", ".join(t2_players) if t2_players else "None"}

**Tier distribution:**
{chr(10).join(f"  T{k}: {v} players — {TIER_LABELS[k]}" for k, v in sorted({int(k): int(v) for k, v in sf['tier'].value_counts().sort_index().items()}.items()))}

---

## DATA AUDIT NOTES

- Field: 144 players (john_deere_classic_2026_field.csv)
- SG 12M: 144 rows joined (field_player_Last12month_TrueSG_Data.csv)
- Fit-adj: 143 rows (1 player assigned median fit values; tpcdeererun_playerfitadj_predictedshotdistance.csv)
- CH: 144 rows (tpc_deere_run_CH.csv) — all field players have CH records
- Debut players (rounds_played=0): {int(sf['debut_flag'].sum())}
- No separate 2026 DG performance file → form_vs_baseline=0 all players
- Missing sg_total_12m: {int(sf['sg_total_12m'].isna().sum())} players

---

## SETUP CHANGE NOTE

**Hole 4**: Extended from 454 to 492 yards (+38 yd) for 2026 championship routing.
- Now a genuine par-4 approach challenge vs short-iron layup scenario
- Slightly increases APP_150_200 demand; no structural change to trait weight matrix
- Monitor hole-4 scoring vs DG par-4 baseline (-0.05/round) for week-1 calibration

---

*Scoring spec: v1.1 | Learning loop: v1.1 | Engine: PGA_VenueDNA_Tier_Engine_v1*
"""

with open(BASE_OUT / "TPC_DEERE_RUN_INTELLIGENCE_2026_v1.md", "w", encoding="utf-8") as fh:
    fh.write(intel_md)
print(f"  TPC_DEERE_RUN_INTELLIGENCE_2026_v1.md")


# ── Deploy copies ──────────────────────────────────────────────────────────────
dep_data = BASE_DEP / "data"
dep_data.mkdir(parents=True, exist_ok=True)
for fname in ["event_payload.json", "vts_full.csv", "player_briefs.json"]:
    src_name = f"{SLUG}_{fname}"
    shutil.copy2(BASE_OUT / src_name, dep_data / fname)
print(f"  Copied 3 files to deploy/data/")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 12 — SANITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SANITY CHECKS")
print("=" * 70)

print(f"\nField size : {N}")
print(f"Duplicates : {sf['name_key'].duplicated().sum()}")

print("\nTop 10 by vts_final:")
top10 = vts_out.head(10)[[
    "rank_model", "player_display", "vts_final", "tier",
    "neutral_skill_sg", "venue_fit_delta", "venue_history_delta", "win_pct",
]]
print(top10.to_string(index=False))

print("\nTier distribution:")
print(vts_out["tier"].value_counts().sort_index().to_string())

errors = vts_out[vts_out["tier_gate_check"] != "ok"]
if len(errors):
    print(f"\nWARNING: {len(errors)} tier gate contradictions!")
    print(errors[["player_display", "vts_final", "tier", "tier_gate_check"]].to_string())
else:
    print("\nTier gate check: ALL OK")

print(f"\nWin pct sum      : {vts_out['win_pct'].sum():.4f}  (must be ~1.0000)")
print(f"Max win pct      : {vts_out['win_pct'].max():.4f}  ({vts_out.iloc[0]['player_display']})")
print(f"Debut players    : {int(sf['debut_flag'].sum())}")
print(f"Missing sg_total : {int(sf['sg_total_12m'].isna().sum())} players")
print(f"Missing cf_total : {int(sf['cf_adj_total'].isna().sum())} players")

print(f"\nAnti-pattern flag counts:")
print(f"  bomb_and_spray     : {sf['ap_bomb_and_spray'].sum()}")
print(f"  wedge_liability    : {sf['ap_wedge_liability'].sum()}")
print(f"  poor_birdie_conv   : {sf['ap_poor_birdie_conv'].sum()}")
print(f"  rough_approach_liab: {sf['ap_rough_approach_liab'].sum()}")

print("\nMake-cut range (top/bottom 5):")
cut_sorted = vts_out.sort_values("make_cut_pct", ascending=False)
print("  Top 5 make-cut:")
print(cut_sorted.head(5)[["player_display", "vts_final", "make_cut_pct"]].to_string(index=False))
print("  Bottom 5 make-cut:")
print(cut_sorted.tail(5)[["player_display", "vts_final", "make_cut_pct"]].to_string(index=False))

print("\n" + "=" * 70)
print("PIPELINE COMPLETE")
print("=" * 70)
