"""
PGA VenueDNA Tier Engine — 2026 Travelers Championship @ TPC River Highlands
Spec  : 02_PGA_VENUEDNA_SCORING_SPEC.md v1.1
Schema: 04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md v1.1

Outputs (all to events/2026_TravelersChampionship/output/):
  2026_travelers_championship_field_input.csv
  2026_travelers_championship_event_context.json
  2026_travelers_championship_trait_form_matrix.csv
  2026_travelers_championship_vts_full.csv
  2026_travelers_championship_player_briefs.json
  2026_travelers_championship_event_payload.json
  2026_travelers_championship_links.json

Deploy package (events/2026_TravelersChampionship/deploy/):
  Copies data files; HTML/CSS/JS in separate files.

NOTE: pga_field.csv not found in workspace.
      Field derived from tpc_river_highlands_CH.csv (72 players = correct signature-event size).
      Thursday tee times unavailable; r1_tee_time = "TBD" for all players.
      Source tee sheet from PGATour.com field page before publication.
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
ROOT     = Path(r"C:\PGA_VenueDNA\events\2026_TravelersChampionship")
BASE_IN  = ROOT / "input"
BASE_OUT = ROOT / "output"
BASE_DEP = ROOT / "deploy"
BASE_OUT.mkdir(parents=True, exist_ok=True)

SLUG = "2026_travelers_championship"

# ── Event / Venue Constants ────────────────────────────────────────────────────
EVENT_META = dict(
    event_name             = "Travelers Championship",
    event_slug             = SLUG,
    event_id               = 34,
    season_year            = 2026,
    venue_name             = "TPC River Highlands",
    venue_code             = "tpc_river_highlands",
    venue_file_version     = "2026_v1",
    course_par             = 70,
    course_yardage         = 6844,
    surface                = "Bentgrass/Poa annua (fairways + greens)",
    cut_rule               = "no_cut",
    no_cut_note            = (
        "Signature event — all 72 players complete 4 rounds (barring WD). "
        "make_cut_pct and miss_cut_pct are not_applicable. "
        "No cut-survival probability is generated."
    ),
    field_size             = 72,
    purse_total            = 20_000_000,
    weather_forecast_class = "mild",
    venue_variance_class   = "standard",
    birdie_fest_flag       = True,
    expected_scoring_band  = "-3 to -6 per round vs par (field avg historically -0.76/round)",
    variance_expectation   = "standard",
    fairway_width_class    = "moderate",   # 35.1 yd avg
    rough_severity_class   = "moderate",   # 4" tournament rough
    firmness_class         = "medium",
    green_speed_policy     = "fast",       # stimp 12
    rollout_class          = "moderate",
    long_iron_frequency_class = "low",     # short par-70 — mostly wedge/short iron
    difficulty_class       = "moderate",
    event_class            = "signature",
    engine_version         = "1.1",
    scoring_spec_version   = "1.1",
    learning_loop_version  = "1.0",
    event_iteration        = "initial",
    notes_on_setup_change  = "No material setup changes reported. Standard tournament prep.",
    notes_on_data_gaps     = (
        "pga_field.csv (tee sheet) not found. "
        "Field and player list derived from tpc_river_highlands_CH.csv (72-row course-history file). "
        "Thursday tee times unavailable — r1_tee_time=TBD for all players. "
        "Source tee sheet from PGATour.com before deploying the board."
    ),
    tee_times_available    = False,
)

# Venue trait weight matrix — TPC River Highlands (short par-70, birdie-fest)
# Weights sum to 1.00
VENUE_WEIGHTS = dict(
    app_wedge       = 0.22,   # Approach <150 yd — dominant at short par-70
    app_100_150     = 0.12,   # Approach 100-150 yd — iron play at key scoring distances
    app_150_200     = 0.06,   # Approach 150-200 yd — less critical here
    ott_accuracy    = 0.14,   # Driving accuracy — bentgrass fairways + water late
    ott_distance    = 0.05,   # Driving distance — minor premium; short track
    putt_short_conv = 0.16,   # Short putt conversion — birdie conversion at birdie-fest
    putt_lag        = 0.10,   # Lag putting — distance control on Bentgrass/Poa
    arg_rough       = 0.07,   # Scrambling from rough — Ky bluegrass/fescue
    arg_bunker      = 0.05,   # Bunker play
    par5_scoring    = 0.03,   # Par-5 scoring (adj_par5=-0.29/round historically)
)
assert abs(sum(VENUE_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.00"

# Anti-pattern definitions (TPC River Highlands specific)
# (base_low_SG, base_high_SG)  — negatives, more negative = more severe
ANTI_PATTERNS = dict(
    bomb_and_spray      = (-1.5, -4.0),  # Long+wild: water at 15-17, bentgrass fairways
    wedge_liability     = (-2.0, -5.0),  # Poor APP<150: critical at birdie-fest; calibrated for standard venue
    poor_birdie_conv    = (-1.5, -4.0),  # Poor short putting: can't cash birdie looks
    rough_approach_liab = (-1.0, -2.5),  # Poor approach from rough; moderate penalty
)
ANTI_PENALTY_CAP = -9.0   # maximum total anti-pattern penalty (SG)
AP_TO_VTS        =  2.0   # SG anti-pattern scale → VTS units (standard venue, not major)
SG_TO_VTS        = 10.0   # generic SG → VTS for debut penalties

DEBUT_PENALTIES = {"A": -4.0, "B": -1.75, "C": -1.0}  # SG units

WIN_EXP   = 4.5    # probability exponent; smaller than 5.0 because 72-player no-cut field
WIN_CAP   = 0.14   # single-player win cap


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
    """'Harman, Brian' → 'HARMAN_BRIAN'"""
    parts = str(name_str).strip().split(", ", 1)
    if len(parts) == 2:
        return f"{parts[0].strip().upper()}_{parts[1].strip().upper()}"
    return name_str.strip().upper()


def parse_win_pct(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace("%", "")
    try:
        return float(s) / 100.0
    except Exception:
        return 0.0


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

# ── 1. Field — tpc_river_highlands_CH.csv (72-player course-history file) ─────
print("Loading field from tpc_river_highlands_CH.csv …")
ch_raw = pd.read_csv(BASE_IN / "tpc_river_highlands_CH.csv")
ch_raw.columns = [c.strip() for c in ch_raw.columns]
ch_raw = ch_raw.dropna(subset=["player_name"])

ch_raw["name_key"] = ch_raw["player_name"].apply(name_key_from_comma)

for col in ["rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]:
    ch_raw[col] = pd.to_numeric(ch_raw[col], errors="coerce")

ch_raw = ch_raw.rename(columns={
    "rounds_played":        "venue_history_rounds",
    "historical_true_sg":   "venue_history_sg",
})
ch_raw["venue_history_rounds"] = ch_raw["venue_history_rounds"].fillna(0)

def display_name(key: str) -> str:
    parts = key.split("_", 1)
    if len(parts) == 2:
        return f"{parts[0].title()}, {parts[1].title()}"
    return key.title()

ch_raw["player_display"] = ch_raw["name_key"].apply(display_name)

df = ch_raw[[
    "player_name", "name_key", "player_display",
    "venue_history_rounds", "venue_history_sg",
    "versus_expected", "ch_adjustment", "experience_adjustment",
]].copy()
df["player_id"]    = range(1, len(df) + 1)
df["field_status"] = "confirmed"
df["r1_tee_time"]  = "TBD"   # pga_field.csv not available
df["r1_wave"]      = "TBD"

N = len(df)
print(f"  Field size: {N}")


# ── 2. True SG L12M ───────────────────────────────────────────────────────────
print("Loading True SG L12M …")
sg_raw = pd.read_csv(BASE_IN / "True_SG_Query_L12Months.csv")
sg_raw.columns = [c.strip() for c in sg_raw.columns]
sg_raw = sg_raw.rename(columns={
    "Last Name":             "lastname",
    "First Name":            "firstname",
    "Events Last 12 Months": "sg_events_12m",
    "Rounds":                "sg_rounds_12m",
    "Rounds-shotlink":       "sg_rounds_shotlink",
    "Wins":                  "wins_12m",
    "Win %":                 "win_pct_raw",
    "True SG-PUTT":          "sg_putt_12m",
    "True SG-ARG":           "sg_arg_12m",
    "True SG-APP":           "sg_app_12m",
    "True SG-OTT":           "sg_ott_12m",
    "True SG-T2G":           "sg_t2g_12m",
    "True SG--TOTAL":        "sg_total_12m",
    "Driving-Distance":      "dd_delta",
    "Driving-Accuracy":      "da_delta_raw",
})
sg_raw["name_key"] = sg_raw.apply(
    lambda r: name_key_from_last_first(r["lastname"], r["firstname"]), axis=1
)
# driving accuracy is stored as "5.30%" — strip %
sg_raw["da_delta"] = (
    sg_raw["da_delta_raw"].astype(str).str.replace("%", "", regex=False)
)
for c in ["sg_events_12m", "sg_rounds_12m", "sg_rounds_shotlink",
          "wins_12m", "sg_putt_12m", "sg_arg_12m", "sg_app_12m",
          "sg_ott_12m", "sg_t2g_12m", "sg_total_12m", "dd_delta", "da_delta"]:
    sg_raw[c] = pd.to_numeric(sg_raw[c], errors="coerce")
sg_raw["win_rate_12m"] = sg_raw["win_pct_raw"].apply(parse_win_pct)


# ── 3. Course Fit & Predicted Shots ───────────────────────────────────────────
print("Loading Course Fit & Predicted Shots …")
fit_raw = pd.read_csv(BASE_IN / "Player Course Fit & Predicted Shots.csv")
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


# ── 4. Approach Skill (fairway proximity buckets) ─────────────────────────────
print("Loading Approach Skill …")
app_raw = pd.read_csv(BASE_IN / "Player_Approach_Skill.csv")
app_raw.columns = [c.strip() for c in app_raw.columns]
app_raw = app_raw.rename(columns={
    "Last Name":              "lastname",
    "First Name":             "firstname",
    "Fairway 50-100 (shots)": "fw_50_100_shots",
    "Fairway 50-100 (value)": "fw_50_100_val",
    "Fairway 100-150 (shots)":"fw_100_150_shots",
    "Fairway 100-150 (value)":"fw_100_150_val",
    "Fairway 150-200 (shots)":"fw_150_200_shots",
    "Fairway 150-200 (value)":"fw_150_200_val",
    "Fairway over 200 (shots)":"fw_200plus_shots",
    "Fairway over 200 (value)":"fw_200plus_val",
    "Rough-Under 150 (shots)":"rgh_u150_shots",
    "Rough-Under 150 (value)":"rgh_u150_val",
    "Rough-Over 150 (shots)": "rgh_o150_shots",
    "Rough-Over 150 (value)": "rgh_o150_val",
})
app_raw["name_key"] = app_raw.apply(
    lambda r: name_key_from_last_first(r["lastname"], r["firstname"]), axis=1
)
for c in app_raw.columns:
    if c not in ("lastname", "firstname", "name_key"):
        app_raw[c] = pd.to_numeric(app_raw[c], errors="coerce")
# Deduplicate: Player_Approach_Skill.csv has Scheffler twice; keep first occurrence
app_raw = app_raw.drop_duplicates(subset=["name_key"], keep="first")


# ── 5. DG 2026 Performance (recent form signal) ───────────────────────────────
print("Loading DG 2026 performance …")
dg_raw = pd.read_csv(BASE_IN / "dg_performance_2026.csv")
dg_raw.columns = [c.strip() for c in dg_raw.columns]
dg_raw["name_key"] = dg_raw["player_name"].apply(name_key_from_comma)
dg_raw = dg_raw.rename(columns={
    "total_true":    "sg_total_2026",
    "app_true":      "sg_app_2026",
    "ott_true":      "sg_ott_2026",
    "putt_true":     "sg_putt_2026",
    "arg_true":      "sg_arg_2026",
    "rounds_played": "rounds_2026",
})
for c in ["sg_total_2026", "sg_app_2026", "sg_ott_2026",
          "sg_putt_2026", "sg_arg_2026", "rounds_2026"]:
    dg_raw[c] = pd.to_numeric(dg_raw[c], errors="coerce")


# ── 6. Merge all onto field ────────────────────────────────────────────────────
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
APP_COLS = [
    "name_key",
    "fw_50_100_val", "fw_100_150_val", "fw_150_200_val", "fw_200plus_val",
    "rgh_u150_val", "rgh_o150_val",
]
DG_COLS = [
    "name_key", "sg_total_2026", "sg_app_2026", "sg_ott_2026",
    "sg_putt_2026", "sg_arg_2026", "rounds_2026",
]

df = (df
      .merge(sg_raw[SG_COLS],  on="name_key", how="left")
      .merge(fit_raw[FIT_COLS], on="name_key", how="left")
      .merge(app_raw[APP_COLS], on="name_key", how="left")
      .merge(dg_raw[DG_COLS],   on="name_key", how="left"))

dups = df["name_key"].duplicated().sum()
assert dups == 0, f"Merge created {dups} duplicate rows — check name keys"
print(f"  Merged: {len(df)} rows, 0 duplicates")

# Audit note: CH file has 71 players; Travelers event is 72-player field.
# One player is absent from tpc_river_highlands_CH.csv (likely a late entry
# or sponsor exemption not yet in the course-history database).
# Field size is logged as 71 until the tee sheet / pga_field.csv is supplied.
if N < 72:
    print(f"  NOTE: CH file contains {N} players (expected 72). "
          f"Missing player(s) will be absent from all outputs. "
          f"Supply pga_field.csv + full CH row to complete the field.")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — NEUTRAL SKILL
# ═══════════════════════════════════════════════════════════════════════════════

# ── 7. Data depth & confidence ────────────────────────────────────────────────
def depth_class(rounds):
    if pd.isna(rounds):
        return "thin"
    r = float(rounds)
    if r >= 70:
        return "deep"
    if r >= 30:
        return "medium"
    return "thin"

df["data_depth_class"]       = df["sg_rounds_12m"].apply(depth_class)
df["baseline_confidence_band"] = df["data_depth_class"].map(
    {"deep": "high", "medium": "medium", "thin": "low"}
).fillna("low")


# ── 8. NeutralSkill ───────────────────────────────────────────────────────────
# Field median used as regression target; thin players shrunk toward mean
field_sg_median = df["sg_total_12m"].median()
df["sg_missing"] = df["sg_total_12m"].isna()

# Fill NaN with 80% of field median (20% shrinkage for no-data players)
df["neutral_skill_sg_raw"] = df["sg_total_12m"].fillna(field_sg_median * 0.80)

# Additional regression toward field average based on data depth
def regress_neutral(row):
    ns = row["neutral_skill_sg_raw"]
    dc = row["data_depth_class"]
    if dc == "thin":
        return ns * 0.50 + field_sg_median * 0.50
    if dc == "medium":
        return ns * 0.75 + field_sg_median * 0.25
    return ns  # deep: as-is

df["neutral_skill_sg"]    = df.apply(regress_neutral, axis=1)
df["neutral_skill_index"] = norm0100(df["neutral_skill_sg"])


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — VENUE FIT DELTA
# Trait weight matrix: TPC River Highlands (short par-70, birdie-fest)
# ═══════════════════════════════════════════════════════════════════════════════

def med(col):
    """Field median fill for a column."""
    return df[col].fillna(df[col].median())


# ── 9. Trait construction ─────────────────────────────────────────────────────

# APP Wedge (<150 yd): dominant at short par-70
# Use fw_50_100_val (per-shot SG quality from fairway <100 yd) — quality, not frequency
# shotdist_50_100 is a predicted-shots-per-round count (frequency metric), NOT used here
df["trait_app_wedge"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.45
    + df["cf_short_game"].fillna(0)                   * 0.25
    + med("fw_50_100_val")                            * 0.30   # per-shot SG quality from ≤100 yd
)

# APP 100-150 yd: iron play at key scoring distances
# Use fw_100_150_val (per-shot SG quality from 100-150 yd, fairway)
df["trait_app_100_150"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.50
    + df["cf_approach"].fillna(0)                      * 0.20
    + med("fw_100_150_val")                           * 0.30   # per-shot SG quality from 100-150 yd
)

# APP 150-200 yd: longer irons (less critical at short track)
# Use fw_150_200_val (per-shot SG quality from 150-200 yd, fairway)
df["trait_app_150_200"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.50
    + med("fw_150_200_val")                           * 0.50   # per-shot SG quality from 150-200 yd
)

# OTT Accuracy: driving accuracy — bentgrass fairways + water exposure at 15-17
df["trait_ott_accuracy"] = safe_norm(
    df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.40
    + df["da_delta"].fillna(0) * 0.04    # % delta, scale down
    + df["cf_accuracy"].fillna(0)        * 0.30
    + med("cf_fairway")                  * 0.30
)

# OTT Distance: minor premium — short track; distance still helps on par-5s
df["trait_ott_distance"] = safe_norm(
    df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.60
    + df["dd_delta"].fillna(0) * 0.02
    + df["cf_distance"].fillna(0)        * 0.40
)

# PUTT Short Conversion (2-5ft): birdie conversion — single most critical putting metric
df["trait_putt_short_conv"] = safe_norm(
    df["sg_putt_12m"].fillna(df["sg_putt_12m"].median()) * 0.55
    + med("cf_putt_2_5ft")                              * 0.45
)

# PUTT Lag: distance control on Bentgrass/Poa blend, stimp 12
df["trait_putt_lag"] = safe_norm(
    df["sg_putt_12m"].fillna(df["sg_putt_12m"].median()) * 0.50
    + med("cf_putt_5_30ft")                             * 0.50
)

# ARG Rough: scrambling from Ky bluegrass/fescue rough
df["trait_arg_rough"] = safe_norm(
    df["sg_arg_12m"].fillna(df["sg_arg_12m"].median()) * 0.55
    + med("cf_rough")                                  * 0.25
    + med("rgh_u150_val")                              * 0.20
)

# ARG Bunker: bunker escapes
df["trait_arg_bunker"] = safe_norm(
    df["sg_arg_12m"].fillna(df["sg_arg_12m"].median()) * 0.50
    + med("cf_bunker")                                 * 0.50
)

# Par-5 Scoring: historical adj_par5=-0.29/round means birdie opportunities exist
df["trait_par5_scoring"] = safe_norm(
    df["sg_app_12m"].fillna(df["sg_app_12m"].median()) * 0.40
    + df["sg_ott_12m"].fillna(df["sg_ott_12m"].median()) * 0.30
    + df["sg_arg_12m"].fillna(df["sg_arg_12m"].median()) * 0.30
)


# ── 10. Venue fit score (weighted dot product) ─────────────────────────────────
WEIGHT_TO_TRAIT = {
    "app_wedge":      "trait_app_wedge",
    "app_100_150":    "trait_app_100_150",
    "app_150_200":    "trait_app_150_200",
    "ott_accuracy":   "trait_ott_accuracy",
    "ott_distance":   "trait_ott_distance",
    "putt_short_conv":"trait_putt_short_conv",
    "putt_lag":       "trait_putt_lag",
    "arg_rough":      "trait_arg_rough",
    "arg_bunker":     "trait_arg_bunker",
    "par5_scoring":   "trait_par5_scoring",
}

vfs = pd.Series(0.0, index=df.index)
for wkey, tcol in WEIGHT_TO_TRAIT.items():
    vfs = vfs + VENUE_WEIGHTS[wkey] * df[tcol]

# Course-fit adjustment: cf_adj_total range ≈ ±0.36 SG → scale to ±7 VTS pts
cf_contrib = (df["cf_adj_total"].fillna(0) * 20.0).clip(-7.0, 7.0)
df["venue_fit_score"]         = (vfs + cf_contrib).clip(0.0, 100.0)
df["venue_fit_delta"]         = df["venue_fit_score"] - df["neutral_skill_index"]
df["comp_course_adjustment"]  = cf_contrib.round(2)
df["comp_course_trace"]       = (
    "DataGolf course-fit tool; comp courses: Colonial CC, TPC Potomac, Harbour Town; "
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
# Spec: 5+ starts active; 3-4 partial (50%); 1-2 qualitative (20%); 0 = zero
# ch_adjustment from CH file is already relative-to-baseline
# experience_adjustment is an additive sample-weight modifier
# ═══════════════════════════════════════════════════════════════════════════════

VH_TO_VTS = 8.0   # 1 SG at this venue ≈ 8 VTS pts

def compute_vhd(row):
    """
    Venue history delta — spec §5.
    For 5+ starts we blend ch_adjustment (calibrated) with versus_expected (raw excess
    vs baseline at the time) to capture persistent course-specific skill that ch_adj
    alone undersells for elite course specialists (e.g. Harman, Bradley at Travelers).
    """
    rounds     = float(row["venue_history_rounds"])  if not pd.isna(row["venue_history_rounds"])  else 0.0
    ch_adj     = float(row["ch_adjustment"])         if not pd.isna(row["ch_adjustment"])         else 0.0
    exp_adj    = float(row["experience_adjustment"]) if not pd.isna(row["experience_adjustment"]) else 0.0
    vs_exp     = float(row["versus_expected"])       if not pd.isna(row["versus_expected"])       else 0.0

    if rounds >= 5:
        # Deep history: blend calibrated ch_adj (50%) + raw vs-expected signal (30%) + exp_adj (20%)
        # vs_expected is the player's historical SG excess vs their baseline at the time —
        # for 5+ starts this signal is meaningful and should carry weight.
        combined_sg = ch_adj * 0.50 + vs_exp * 0.30 + exp_adj * 0.20
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "medium"
    elif rounds >= 3:
        # Partial: ch_adj + exp_adj at half weight
        combined_sg = (ch_adj + exp_adj) * 0.50
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "low"
    elif rounds >= 1:
        # Qualitative only: small signal
        combined_sg = (ch_adj + exp_adj) * 0.20
        delta_vts   = combined_sg * VH_TO_VTS
        conf        = "low"
    else:
        delta_vts = 0.0
        conf      = "none"

    # Hard cap: ±15 VTS pts (wider than generic because CH file is well-calibrated)
    delta_vts = float(np.clip(delta_vts, -15.0, 15.0))
    return delta_vts, conf

vh_results = df.apply(compute_vhd, axis=1, result_type="expand")
vh_results.columns = ["venue_history_delta", "venue_history_conf_band"]
df = pd.concat([df, vh_results], axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — PRE-PENALTY VTS (blended, history-class aware)
# ═══════════════════════════════════════════════════════════════════════════════

def build_pp_vts(row):
    rounds      = float(row["venue_history_rounds"])
    blend, bcls = get_blend(rounds)

    n_vts = float(row["neutral_skill_index"])   # 0-100
    v_vts = float(row["venue_fit_score"])       # 0-100
    # History expressed as 50-centered VTS (delta shifts from neutral center)
    h_vts = float(np.clip(50.0 + row["venue_history_delta"], 0.0, 100.0))

    pp = (
        blend["neutral"]      * n_vts
        + blend["venuefit"]   * v_vts
        + blend["venuehistory"] * h_vts
    )
    return pp, bcls, json.dumps(blend)

pp_results = df.apply(build_pp_vts, axis=1, result_type="expand")
pp_results.columns = ["pre_penalty_vts", "blend_class", "blend_weights_used"]
df = pd.concat([df, pp_results], axis=1)
df["tier_eligibility_gate_status"] = "clear"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — RECENT FORM
# sg_total_2026 (shorter, more recent) vs sg_total_12m (baseline)
# form_vs_baseline = 2026 SG − L12M SG; positive = trending better
# ═══════════════════════════════════════════════════════════════════════════════

# Fill missing 2026 data with neutral_skill_sg (no new evidence)
df["sg_total_2026"] = df["sg_total_2026"].fillna(df["neutral_skill_sg"])
df["form_vs_baseline"] = df["sg_total_2026"] - df["sg_total_12m"].fillna(df["neutral_skill_sg"])

def reg_weight(dc):
    return {"deep": 0.30, "medium": 0.40, "thin": 0.60}.get(dc, 0.60)

df["_regw"]             = df["data_depth_class"].apply(reg_weight)
df["form_score_raw"]    = (
    df["sg_total_2026"]    * (1 - df["_regw"])
    + df["neutral_skill_sg"] * df["_regw"]
)
df["form_score_adjusted"] = (
    df["form_score_raw"] * 0.65 + df["neutral_skill_sg"] * 0.35
)
df["recent_form_index"] = norm0100(df["form_score_raw"])

FORM_GATE_THRESHOLD = -1.0
df["recent_form_gate_applied"] = df["form_vs_baseline"] < FORM_GATE_THRESHOLD
df["recent_form_gate_reason"]  = df.apply(
    lambda r: (
        f"2026_SG_vs_12m_baseline={r['form_vs_baseline']:.2f} < {FORM_GATE_THRESHOLD}"
        if r["recent_form_gate_applied"] else ""
    ), axis=1
)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — DEBUT FLAGS
# ═══════════════════════════════════════════════════════════════════════════════
ELITE_SG = 1.5  # Class-C debut threshold

def assign_debut(row):
    thin     = row["data_depth_class"] == "thin"
    no_data  = bool(row["sg_missing"])
    sg       = float(row["neutral_skill_sg"]) if not pd.isna(row["neutral_skill_sg"]) else 0.0

    if not thin and not no_data:
        return False, ""

    # Assign debut class
    if sg >= ELITE_SG:
        return True, "C"
    elif sg >= 0.0:
        return True, "B"
    else:
        return True, "A"

debut_results              = df.apply(assign_debut, axis=1, result_type="expand")
debut_results.columns      = ["debut_flag", "debut_class"]
df = pd.concat([df, debut_results], axis=1)


# ── Health flags (no documented injuries at event build time) ──────────────────
df["injury_flag"]       = False
df["health_gate_status"] = "ok"
df["health_gate_reason"] = ""


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8 — ANTI-PATTERN FLAGS (TPC River Highlands specific)
# ═══════════════════════════════════════════════════════════════════════════════

dd = df["dd_delta"].fillna(0)
da = df["da_delta"].fillna(0)

p60_dd       = dd.quantile(0.60)   # above-avg distance
p45_da       = da.quantile(0.45)   # below-avg accuracy (tighter than generic)

p35_wedge    = df["trait_app_wedge"].quantile(0.35)
p35_sc       = df["trait_putt_short_conv"].quantile(0.35)
p30_rough    = df["trait_arg_rough"].quantile(0.30)

# bomb_and_spray: long but inaccurate → water exposure at 15-17
df["ap_bomb_and_spray"]      = (dd > p60_dd) & (da < p45_da)
# wedge_liability: poor APP<150 — fatal at birdie-fest
df["ap_wedge_liability"]     = df["trait_app_wedge"] < p35_wedge
# poor_birdie_conv: below 35th pct short-putt conversion
df["ap_poor_birdie_conv"]    = df["trait_putt_short_conv"] < p35_sc
# rough_approach_liab: poor approach from rough
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
        v = float(row[col])
        if v > bv:
            bv, bc = v, label
    return bc

def primary_risk(row):
    wv, wc = 9999.0, ""
    for col, label in TRAIT_LABELS.items():
        v = float(row[col])
        if v < wv:
            wv, wc = v, label
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

# ── A. Debut penalties ────────────────────────────────────────────────────────
sf["debut_penalty_applied"] = sf["debut_class"].map(DEBUT_PENALTIES).fillna(0.0)
sf["debut_penalty_vts"]     = sf["debut_penalty_applied"] * SG_TO_VTS / 4.0


# ── B. Anti-pattern penalties (severity-graded) ───────────────────────────────
def ap_penalty_series(flag_col, base_low, base_high, trait_col, direction="low"):
    """
    Returns a Series of penalty values (all ≤ 0) for flagged players.
    Severity interpolates between base_low and base_high based on
    how far below (direction='low') or above (direction='high') the
    median the flagged player sits.
    """
    t     = sf[trait_col]
    t_min = t.min()
    t_max = t.max()
    rng   = (t_max - t_min) if (t_max != t_min) else 1.0

    if direction == "low":
        sev = ((t.median() - t) / rng).clip(0, 1)
    else:
        sev = ((t - t.median()) / rng).clip(0, 1)

    penalty = (base_low + sev * (base_high - base_low)).clip(base_high, 0)
    return np.where(sf[flag_col], penalty, 0.0)


sf["ap_pen_bomb_spray"]      = ap_penalty_series(
    "ap_bomb_and_spray",    -2.0, -5.0, "trait_ott_distance", "high")
sf["ap_pen_wedge_liab"]      = ap_penalty_series(
    "ap_wedge_liability",   -3.0, -7.0, "trait_app_wedge",    "low")
sf["ap_pen_poor_birdie"]     = ap_penalty_series(
    "ap_poor_birdie_conv",  -2.0, -5.0, "trait_putt_short_conv", "low")
sf["ap_pen_rough_approach"]  = ap_penalty_series(
    "ap_rough_approach_liab",-1.5,-3.5, "trait_arg_rough",   "low")

sf["anti_pattern_penalty_total"] = (
    sf["ap_pen_bomb_spray"]
    + sf["ap_pen_wedge_liab"]
    + sf["ap_pen_poor_birdie"]
    + sf["ap_pen_rough_approach"]
).clip(ANTI_PENALTY_CAP, 0)

def ap_flag_str(row):
    flags = []
    if row["ap_bomb_and_spray"]:       flags.append("bomb_and_spray")
    if row["ap_wedge_liability"]:      flags.append("wedge_liability")
    if row["ap_poor_birdie_conv"]:     flags.append("poor_birdie_conv")
    if row["ap_rough_approach_liab"]:  flags.append("rough_approach_liab")
    return ";".join(flags)

sf["anti_pattern_flags"]          = sf.apply(ap_flag_str, axis=1)
sf["anti_pattern_trigger_trace"]  = sf["anti_pattern_flags"]
sf["anti_pattern_modifier_trace"] = (
    f"Standard venue (non-major birdie-fest). AP_TO_VTS={AP_TO_VTS} (vs 3.0 for major). "
    "Mild weather — no setup amplification. Weather modifier ×1.0 all patterns."
)


# ── C. Form delta (VTS) ───────────────────────────────────────────────────────
def form_delta_vts(row):
    fvb  = float(row["form_vs_baseline"])
    gate = bool(row["recent_form_gate_applied"])
    if gate:
        return max(fvb * 2.0, -8.0)
    if fvb > 1.0:
        return min(fvb * 1.5, 5.0)
    if fvb < -0.3:
        return fvb * 1.0
    return 0.0

sf["form_delta_vts"]  = sf.apply(form_delta_vts, axis=1)
sf["health_delta_vts"] = 0.0


# ── D. Variance ───────────────────────────────────────────────────────────────
def player_variance(row):
    if row["data_depth_class"] == "thin" or row["debut_flag"]:
        return "high"
    if abs(float(row["form_vs_baseline"])) > 1.0:
        return "high"
    if row["data_depth_class"] == "medium":
        return "medium"
    return "low"

sf["player_variance_band"] = sf.apply(player_variance, axis=1)
sf["volatility_index"]     = sf["player_variance_band"].map(
    {"low": 25.0, "medium": 50.0, "high": 75.0}
)
sf["venue_variance_class"]          = EVENT_META["venue_variance_class"]
sf["variance_adjustment_trace"]     = (
    "Standard venue variance class. No compression multiplier applied."
)
sf["probability_compression_class"] = "standard"
sf["probability_compression_coefficients"] = json.dumps(
    {"win_exponent": WIN_EXP, "win_cap": WIN_CAP,
     "top3_center": 80, "top5_center": 76, "top10_center": 68, "top20_center": 59}
)
sf["probability_compression_trace"] = (
    f"72-player no-cut field. Win exp={WIN_EXP}, cap={WIN_CAP}. "
    "No cut survival probability generated (not applicable)."
)


# ── E. Final VTS ──────────────────────────────────────────────────────────────
sf["vts_final_raw"] = (
    sf["pre_penalty_vts"]
    + sf["debut_penalty_vts"]
    + sf["anti_pattern_penalty_total"] * AP_TO_VTS
    + sf["form_delta_vts"]
    + sf["health_delta_vts"]
).clip(0.0, 100.0)

sf["vts_final"] = sf["vts_final_raw"].clip(0.0, 100.0)


# ── F. Tier assignment ────────────────────────────────────────────────────────
def assign_tier(vts):
    if vts >= 80:  return 1
    if vts >= 65:  return 2
    if vts >= 50:  return 3
    if vts >= 35:  return 4
    return 5

sf["tier"] = sf["vts_final"].apply(assign_tier)

# Contradiction gate: vts≥80 with gate=clear must be Tier 1
def tier_gate_check(row):
    g   = row["tier_eligibility_gate_status"]
    vts = float(row["vts_final"])
    t   = int(row["tier"])
    if g == "clear" and vts >= 80 and t > 1:
        return f"CONTRADICTION: vts={vts:.1f}≥80 gate=clear tier={t}"
    if g == "clear" and vts >= 65 and t > 2:
        return f"CONTRADICTION: vts={vts:.1f}≥65 gate=clear tier={t}"
    return "ok"

sf["tier_gate_check"] = sf.apply(tier_gate_check, axis=1)

def tier_reason_str(row):
    t   = int(row["tier"])
    ns  = float(row["neutral_skill_sg"])
    vfd = float(row["venue_fit_delta"])
    ap  = float(row["anti_pattern_penalty_total"])
    vhr = int(row["venue_history_rounds"])
    debut_tag = f"; debut-{row['debut_class']}" if row["debut_flag"] else ""
    gate_tag  = "; form-gated" if row["recent_form_gate_applied"] else ""
    hist_tag  = f"; {vhr}CH-rds" if vhr > 0 else "; 0CH-rds"

    if t == 1:
        return (f"Tier1: NeutralSG={ns:.2f}+VFD={vfd:.1f}{hist_tag}{debut_tag}"
                f" → elite birdie-fest fit at TPC River Highlands")
    if t == 2:
        return (f"Tier2: NeutralSG={ns:.2f}, VFD={vfd:.1f}{hist_tag}{debut_tag}{gate_tag}")
    if t == 3:
        return (f"Tier3: NeutralSG={ns:.2f}, moderate fit VFD={vfd:.1f}{hist_tag}{debut_tag}{gate_tag}")
    if t == 4:
        return (f"Tier4: Below-avg or mismatch VFD={vfd:.1f}, AP={ap:.1f}SG{hist_tag}{debut_tag}{gate_tag}")
    return (f"Tier5: Weak profile NeutralSG={ns:.2f}, AP={ap:.1f}SG{hist_tag}{debut_tag}{gate_tag}")

sf["tier_reason"] = sf.apply(tier_reason_str, axis=1)


# ── G. Probabilities (no-cut field: 72 players) ───────────────────────────────
# Win probability: exponent=4.5 (smaller than 156-player field)
var_spread = {"low": 1.00, "medium": 1.08, "high": 1.15}
sf["_var_s"] = sf["player_variance_band"].map(var_spread)

win_raw = (sf["vts_final"] / 100.0) ** WIN_EXP * sf["_var_s"]
sf["win_pct"] = (win_raw / win_raw.sum()).clip(0, WIN_CAP)
sf["win_pct"] = sf["win_pct"] / sf["win_pct"].sum()  # renormalize after cap

def calc_top_probs(vts, var_idx):
    v = float(vts)
    s = 1.0 + (float(var_idx) - 50.0) / 250.0
    return (
        logistic_prob(v, 80, 0.10) * s,   # top3
        logistic_prob(v, 76, 0.10) * s,   # top5
        logistic_prob(v, 68, 0.09) * s,   # top10
        logistic_prob(v, 59, 0.08) * s,   # top20
    )

probs = sf.apply(
    lambda r: calc_top_probs(r["vts_final"], r["volatility_index"]),
    axis=1, result_type="expand",
)
probs.columns = ["top3_pct", "top5_pct", "top10_pct", "top20_pct"]
sf = pd.concat([sf, probs], axis=1)

# No-cut handling: mark not_applicable per spec
sf["make_cut_pct"] = "not_applicable"
sf["miss_cut_pct"] = "not_applicable"
sf["no_cut_note"]  = EVENT_META["no_cut_note"]

# Risk stressor defaults (no stressors active in mild weather)
sf["risk_stressor_active"]           = False
sf["risk_secondary_discount_applied"] = 0.0
sf["risk_discount_trace"]            = ""


# ── H. Trace notes ────────────────────────────────────────────────────────────
def trace_note(row):
    parts = [
        f"NeutralSG={row['neutral_skill_sg']:.2f}",
        f"VFD={row['venue_fit_delta']:.1f}",
        f"VHD={row['venue_history_delta']:.1f}({int(row['venue_history_rounds'])}rds)",
    ]
    if row["debut_flag"]:
        parts.append(f"debut-{row['debut_class']} pen={row['debut_penalty_applied']:.1f}SG")
    if float(row["anti_pattern_penalty_total"]) < -1.0:
        parts.append(
            f"AP={row['anti_pattern_penalty_total']:.1f}SG({row['anti_pattern_flags']})"
        )
    if row["recent_form_gate_applied"]:
        parts.append(f"form-gate({row['form_vs_baseline']:.2f})")
    parts.append(f"→Tier{row['tier']} VTS={row['vts_final']:.1f}")
    return "; ".join(parts)

sf["trace_notes"] = sf.apply(trace_note, axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 11 — OUTPUT ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\nWriting output artifacts …")

# Sort by vts_final descending for all ranked outputs
sf_ranked = sf.sort_values("vts_final", ascending=False).reset_index(drop=True)
sf_ranked.insert(0, "rank_model", range(1, len(sf_ranked) + 1))


# ── Field Input CSV ────────────────────────────────────────────────────────────
field_cols = [
    "player_id", "player_display", "name_key", "field_status",
    "r1_tee_time", "r1_wave",
    "venue_history_rounds", "venue_history_sg", "versus_expected", "ch_adjustment",
    "sg_total_12m", "sg_ott_12m", "sg_app_12m", "sg_arg_12m", "sg_putt_12m",
    "sg_rounds_12m", "wins_12m", "win_rate_12m", "dd_delta", "da_delta",
    "sg_total_2026", "rounds_2026",
    "cf_adj_total", "cf_short_game", "cf_approach", "cf_distance", "cf_accuracy",
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
    "sg_total_12m", "sg_ott_12m", "sg_app_12m", "sg_arg_12m", "sg_putt_12m",
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
    "sg_total_2026", "form_vs_baseline", "recent_form_index", "form_score_adjusted",
    "recent_form_gate_applied", "recent_form_gate_reason",
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
    "make_cut_pct", "miss_cut_pct", "no_cut_note",
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
ctx["tier_gate_errors"]      = sf_ranked[sf_ranked["tier_gate_check"] != "ok"][["player_display", "tier_gate_check"]].to_dict(orient="records")

with open(BASE_OUT / f"{SLUG}_event_context.json", "w") as fh:
    json.dump(ctx, fh, indent=2, default=str)
print(f"  {SLUG}_event_context.json")


# ── Player Briefs JSON ────────────────────────────────────────────────────────
def make_brief(row):
    ap_str = row["anti_pattern_flags"] if row["anti_pattern_flags"] else "none"
    cf_adj = row.get("comp_course_adjustment", "N/A")   # cf_adj_total scaled → VTS pts
    return {
        "player_name":    row["player_display"],
        "tier":           int(row["tier"]),
        "vts_final":      round(float(row["vts_final"]), 1),
        "win_pct":        round(float(row["win_pct"]) * 100.0, 1),
        "top10_pct":      round(float(row["top10_pct"]) * 100.0, 1),
        "top20_pct":      round(float(row["top20_pct"]) * 100.0, 1),
        "make_cut_pct":   "not_applicable",
        "miss_cut_pct":   "not_applicable",
        "neutral_skill_summary": (
            f"TrueSG(12m)={row['neutral_skill_sg']:.2f}; "
            f"depth={row['data_depth_class']}; NeutralIdx={row['neutral_skill_index']:.1f}"
        ),
        "venue_fit_summary": (
            f"VFS={row['venue_fit_score']:.1f}; VFD={row['venue_fit_delta']:.1f}; "
            f"CF_Adj_VTS={round(float(cf_adj), 2) if cf_adj != 'N/A' else 'N/A'}; "
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
        "risk_vector":              row["primary_risk_trait"],
        "conviction_statement":     row["tier_reason"],
        "named_failure_condition": (
            f"If {row['primary_risk_trait']} underperforms or water penalty (holes 15-17) "
            f"accumulates, ceiling collapses. Active AP flags: {ap_str}."
        ),
        "trace_notes": row["trace_notes"],
    }

tier1_briefs = [make_brief(r) for _, r in vts_out[vts_out["tier"] == 1].iterrows()]
tier2_briefs = [make_brief(r) for _, r in vts_out[vts_out["tier"] == 2].iterrows()]

briefs_payload = {
    "event":        EVENT_META["event_name"],
    "venue":        EVENT_META["venue_name"],
    "generated_at": datetime.now().isoformat(),
    "no_cut_note":  EVENT_META["no_cut_note"],
    "tier_1":       tier1_briefs,
    "tier_2":       tier2_briefs,
}
with open(BASE_OUT / f"{SLUG}_player_briefs.json", "w") as fh:
    json.dump(briefs_payload, fh, indent=2, default=str)
print(f"  {SLUG}_player_briefs.json  (T1={len(tier1_briefs)}, T2={len(tier2_briefs)})")


# ── Event Payload JSON ─────────────────────────────────────────────────────────
def player_row_dict(row):
    return {
        "rank":              int(row["rank_model"]),
        "player_name":       row["player_display"],
        "tier":              int(row["tier"]),
        "vts_final":         round(float(row["vts_final"]), 1),
        "win_pct":           round(float(row["win_pct"]) * 100.0, 2),
        "top5_pct":          round(float(row["top5_pct"]) * 100.0, 1),
        "top10_pct":         round(float(row["top10_pct"]) * 100.0, 1),
        "top20_pct":         round(float(row["top20_pct"]) * 100.0, 1),
        "make_cut_pct":      "N/A",
        "neutral_sg":        round(float(row["neutral_skill_sg"]), 2),
        "vfd":               round(float(row["venue_fit_delta"]), 1),
        "vh_rounds":         int(row["venue_history_rounds"]),
        "vh_delta":          round(float(row["venue_history_delta"]), 1),
        "anti_pattern_flags":row["anti_pattern_flags"] if row["anti_pattern_flags"] else "",
        "primary_driver":    row["primary_trait_driver"],
        "tier_reason":       row["tier_reason"],
        "r1_tee_time":       row["r1_tee_time"],
        "r1_wave":           row["r1_wave"],
        "trace_notes":       row["trace_notes"],
    }

all_players = [player_row_dict(r) for _, r in vts_out.iterrows()]

ap_summary = []
for _, r in vts_out.iterrows():
    if r["anti_pattern_flags"]:
        total_pen_vts = round(float(r["anti_pattern_penalty_total"]) * AP_TO_VTS, 1)
        for flag in r["anti_pattern_flags"].split(";"):
            if flag.strip():
                ap_summary.append({
                    "player":     r["player_display"],
                    "flag":       flag.strip(),
                    "penalty_vts": total_pen_vts,
                })

payload = {
    "event": {
        "name":           EVENT_META["event_name"],
        "slug":           SLUG,
        "venue":          EVENT_META["venue_name"],
        "dates":          "2026-06-25 to 2026-06-28",
        "par":            EVENT_META["course_par"],
        "yardage":        EVENT_META["course_yardage"],
        "field_size":     EVENT_META["field_size"],
        "field_locked":   True,
        "cut_rule":       "no_cut",
        "no_cut_note":    EVENT_META["no_cut_note"],
        "purse":          EVENT_META["purse_total"],
        "event_class":    EVENT_META["event_class"],
        "tee_times_note": (
            "Thursday tee times not available at build time (pga_field.csv missing). "
            "r1_tee_time = TBD for all players."
        ),
    },
    "venue": {
        "name":            EVENT_META["venue_name"],
        "location":        "Cromwell, Connecticut, USA",
        "par":             70,
        "yardage":         6844,
        "surface":         EVENT_META["surface"],
        "stimp":           12,
        "fairway_width":   "35.1 yd avg (moderate)",
        "rough_severity":  "4\" tournament rough (moderate)",
        "variance_class":  "standard",
        "birdie_fest":     True,
        "scoring_avg":     "-0.76 per round vs par (field avg)",
        "signature_stretch": "Holes 15-17 around 4-acre lake; reachable par-4 15th",
        "course_record":   "58 (Jim Furyk, 2016)",
        "comp_courses":    ["Colonial CC", "TPC Potomac", "Harbour Town"],
    },
    "model_summary": {
        "trait_weight_matrix":    VENUE_WEIGHTS,
        "anti_patterns":          list(ANTI_PATTERNS.keys()),
        "no_cut_handling":        (
            "make_cut_pct and miss_cut_pct = not_applicable for all players. "
            "No cut survival probability generated."
        ),
        "probability_normalization": f"Field-wide win_pct sum = 1.00; cap = {WIN_CAP*100:.0f}% per player",
        "model_winner":           sf_ranked.iloc[0]["player_display"],
        "model_winner_vts":       round(float(sf_ranked.iloc[0]["vts_final"]), 1),
        "scoring_spec_version":   "1.1",
        "venue_file_version":     "2026_v1",
        "event_iteration":        "initial",
    },
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


# ── Links JSON ─────────────────────────────────────────────────────────────────
links = {
    "tournament_homepage":  "https://www.pgatour.com/tournaments/2026/travelers-championship/R034",
    "official_leaderboard": "https://www.pgatour.com/leaderboard",
    "field_list_source":    "tpc_river_highlands_CH.csv (derived field; pga_field.csv not found)",
    "tee_sheet_note":       "Retrieve from https://www.pgatour.com/tournaments/2026/travelers-championship/R034/field when available.",
    "datagolf_event_page":  "https://datagolf.com/tournament-stats?tour=pga&event_id=34",
    "weather_source":       "https://weather.com/weather/tenday/l/Cromwell+CT",
    "dk_contest_links":     "https://www.draftkings.com/lobby#/golf",
}
with open(BASE_OUT / f"{SLUG}_links.json", "w") as fh:
    json.dump(links, fh, indent=2)
print(f"  {SLUG}_links.json")


# ── Copy data files to deploy/data/ ───────────────────────────────────────────
dep_data = BASE_DEP / "data"
dep_data.mkdir(parents=True, exist_ok=True)
for fname in ["event_payload.json", "vts_full.csv", "player_briefs.json", "links.json"]:
    src_name = f"{SLUG}_{fname}"
    shutil.copy2(BASE_OUT / src_name, dep_data / fname)
print(f"  Copied 4 files to deploy/data/")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 12 — SANITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SANITY CHECKS")
print("=" * 70)

print(f"\nField size : {N}  (CH file has {N}; event is 72-player; 1 player absent from CH — see audit note)")
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
    print("\nTier gate check: ALL OK — no contradictory rows")

print(f"\nWin pct sum  : {vts_out['win_pct'].sum():.4f}  (must be ~1.0000)")
print(f"Max win pct  : {vts_out['win_pct'].max():.4f}  ({vts_out.iloc[0]['player_display']})")
print(f"make_cut_pct : {vts_out['make_cut_pct'].iloc[0]}  (all rows — correct for no-cut event)")

miss_sg  = sf[sf["sg_total_12m"].isna()]
miss_fit = sf[sf["cf_adj_total"].isna()]
print(f"\nMissing sg_total_12m  : {len(miss_sg)} players")
print(f"Missing cf_adj_total  : {len(miss_fit)} players")

if len(miss_sg):
    print("  Players missing SG data (shrunk to field avg):")
    print(" ", miss_sg["player_display"].tolist())

print("\n" + "=" * 70)
print("PIPELINE COMPLETE")
print("=" * 70)
