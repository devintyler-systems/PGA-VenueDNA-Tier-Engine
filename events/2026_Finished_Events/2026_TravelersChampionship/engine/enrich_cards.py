"""
PGA VenueDNA — Travelers 2026 Card Enrichment
Reads source CSVs, rebuilds trait scores, generates rich narrative briefs,
injects trait_scores into event_payload.json, rewrites player_briefs.json.

No new scoring logic. Trait math is identical to venuedna_pipeline_travelers2026.py.
This script only adds narrative text and display-ready derived fields.
"""

import json, warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT    = Path(r"C:\PGA_VenueDNA\events\2026_TravelersChampionship")
IN      = ROOT / "input"
DEP     = ROOT / "deploy" / "data"

# ── Venue weight matrix (identical to pipeline) ──────────────────────────────
VENUE_WEIGHTS = dict(
    app_wedge       = 0.22,
    app_100_150     = 0.12,
    app_150_200     = 0.06,
    ott_accuracy    = 0.14,
    ott_distance    = 0.05,
    putt_short_conv = 0.16,
    putt_lag        = 0.10,
    arg_rough       = 0.07,
    arg_bunker      = 0.05,
    par5_scoring    = 0.03,
)

TRAIT_LABELS = {
    "app_wedge":       "Wedge/Short-Iron (APP <150 yd)",
    "app_100_150":     "Mid-Iron (APP 100–150 yd)",
    "app_150_200":     "Long-Iron (APP 150–200 yd)",
    "ott_accuracy":    "Positional Driving (OTT Accuracy)",
    "ott_distance":    "Driving Distance (OTT Power)",
    "putt_short_conv": "Birdie Conversion (2–5 ft)",
    "putt_lag":        "Lag Putting (Bentgrass pace control)",
    "arg_rough":       "Rough Scrambling (ARG)",
    "arg_bunker":      "Bunker Play (ARG)",
    "par5_scoring":    "Par-5 Scoring",
}

# ── Helpers (identical to pipeline) ──────────────────────────────────────────
def norm0100(s):
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(50.0, index=s.index)
    return (s - lo) / (hi - lo) * 100.0

def safe_norm(s):
    sc = s.copy()
    fill = sc.median() if not sc.isna().all() else 0.0
    return norm0100(sc.fillna(fill))

def nk_last_first(last, first):
    return f"{str(last).strip().upper()}_{str(first).strip().upper()}"

def nk_comma(name_str):
    parts = str(name_str).strip().split(", ", 1)
    return f"{parts[0].strip().upper()}_{parts[1].strip().upper()}" if len(parts) == 2 else str(name_str).strip().upper()

def parse_pct(v):
    s = str(v).strip().replace("%","")
    try: return float(s) / 100.0
    except: return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Load source data (identical column renames as pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
print("Loading source CSVs …")

ch = pd.read_csv(IN / "tpc_river_highlands_CH.csv")
ch.columns = [c.strip() for c in ch.columns]
ch["name_key"] = ch["player_name"].apply(nk_comma)
for c in ["rounds_played","historical_true_sg","versus_expected","ch_adjustment","experience_adjustment"]:
    ch[c] = pd.to_numeric(ch[c], errors="coerce")
ch = ch.rename(columns={"rounds_played":"vh_rounds","historical_true_sg":"vh_sg"})
ch["vh_rounds"] = ch["vh_rounds"].fillna(0)

sg = pd.read_csv(IN / "True_SG_Query_L12Months.csv")
sg.columns = [c.strip() for c in sg.columns]
sg = sg.rename(columns={
    "Last Name":"lastname","First Name":"firstname",
    "Events Last 12 Months":"sg_events_12m","Rounds":"sg_rounds_12m",
    "Wins":"wins_12m","Win %":"win_pct_raw",
    "True SG-PUTT":"sg_putt_12m","True SG-ARG":"sg_arg_12m","True SG-APP":"sg_app_12m",
    "True SG-OTT":"sg_ott_12m","True SG-T2G":"sg_t2g_12m","True SG--TOTAL":"sg_total_12m",
    "Driving-Distance":"dd_delta","Driving-Accuracy":"da_delta_raw",
})
sg["name_key"] = sg.apply(lambda r: nk_last_first(r["lastname"], r["firstname"]), axis=1)
sg["da_delta"] = sg["da_delta_raw"].astype(str).str.replace("%","",regex=False)
for c in ["sg_events_12m","sg_rounds_12m","wins_12m","sg_putt_12m","sg_arg_12m",
          "sg_app_12m","sg_ott_12m","sg_t2g_12m","sg_total_12m","dd_delta","da_delta"]:
    sg[c] = pd.to_numeric(sg[c], errors="coerce")
sg["win_rate_12m"] = sg["win_pct_raw"].apply(parse_pct)

fit = pd.read_csv(IN / "Player Course Fit & Predicted Shots.csv")
fit.columns = [c.strip() for c in fit.columns]
fit = fit.rename(columns={
    "Last Name":"lastname","First Name":"firstname",
    "Short Game":"cf_short_game","Approach":"cf_approach",
    "Driving-Distance":"cf_distance","Driving-Accuracy":"cf_accuracy",
    "Total SG Adjustment":"cf_adj_total",
    "Putting 2-5ft":"cf_putt_2_5ft","Putting 5-30ft":"cf_putt_5_30ft","Putting 30+ ft":"cf_putt_30plus",
    "Course-Fairway":"cf_fairway","Course-Rough":"cf_rough","Course-Bunker":"cf_bunker",
    "Approach 50-100yds":"shotdist_50_100","Approach 100-150 yds":"shotdist_100_150",
    "Approach 150-200 yds":"shotdist_150_200","Approach 200+ yds":"shotdist_200plus",
})
fit["name_key"] = fit.apply(lambda r: nk_last_first(r["lastname"], r["firstname"]), axis=1)
for c in fit.columns:
    if c not in ("lastname","firstname","name_key"):
        fit[c] = pd.to_numeric(fit[c], errors="coerce")

app = pd.read_csv(IN / "Player_Approach_Skill.csv")
app.columns = [c.strip() for c in app.columns]
app = app.rename(columns={
    "Last Name":"lastname","First Name":"firstname",
    "Fairway 50-100 (shots)":"fw_50_100_shots","Fairway 50-100 (value)":"fw_50_100_val",
    "Fairway 100-150 (shots)":"fw_100_150_shots","Fairway 100-150 (value)":"fw_100_150_val",
    "Fairway 150-200 (shots)":"fw_150_200_shots","Fairway 150-200 (value)":"fw_150_200_val",
    "Fairway over 200 (shots)":"fw_200plus_shots","Fairway over 200 (value)":"fw_200plus_val",
    "Rough-Under 150 (shots)":"rgh_u150_shots","Rough-Under 150 (value)":"rgh_u150_val",
    "Rough-Over 150 (shots)":"rgh_o150_shots","Rough-Over 150 (value)":"rgh_o150_val",
})
app["name_key"] = app.apply(lambda r: nk_last_first(r["lastname"], r["firstname"]), axis=1)
for c in app.columns:
    if c not in ("lastname","firstname","name_key"):
        app[c] = pd.to_numeric(app[c], errors="coerce")
app = app.drop_duplicates(subset=["name_key"], keep="first")

dg = pd.read_csv(IN / "dg_performance_2026.csv")
dg.columns = [c.strip() for c in dg.columns]
dg["name_key"] = dg["player_name"].apply(nk_comma)
dg = dg.rename(columns={
    "total_true":"sg_total_2026","app_true":"sg_app_2026",
    "ott_true":"sg_ott_2026","putt_true":"sg_putt_2026",
    "arg_true":"sg_arg_2026","rounds_played":"rounds_2026",
})
for c in ["sg_total_2026","sg_app_2026","sg_ott_2026","sg_putt_2026","sg_arg_2026","rounds_2026"]:
    dg[c] = pd.to_numeric(dg[c], errors="coerce")


# ── Merge ─────────────────────────────────────────────────────────────────────
df = (ch[["name_key","player_name","vh_rounds","vh_sg","versus_expected","ch_adjustment","experience_adjustment"]]
      .merge(sg[["name_key","sg_rounds_12m","sg_putt_12m","sg_arg_12m","sg_app_12m",
                  "sg_ott_12m","sg_total_12m","dd_delta","da_delta","wins_12m","win_rate_12m"]], on="name_key", how="left")
      .merge(fit[["name_key","cf_short_game","cf_approach","cf_distance","cf_accuracy",
                   "cf_adj_total","cf_putt_2_5ft","cf_putt_5_30ft","cf_putt_30plus",
                   "cf_fairway","cf_rough","cf_bunker"]], on="name_key", how="left")
      .merge(app[["name_key","fw_50_100_val","fw_100_150_val","fw_150_200_val",
                   "rgh_u150_val","rgh_o150_val"]], on="name_key", how="left")
      .merge(dg[["name_key","sg_total_2026","sg_app_2026","sg_ott_2026",
                  "sg_putt_2026","sg_arg_2026","rounds_2026"]], on="name_key", how="left"))
df = df.drop_duplicates(subset=["name_key"], keep="first").reset_index(drop=True)
print(f"  Merged: {len(df)} players")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Rebuild traits (identical math as pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
def med(col): return df[col].fillna(df[col].median())

df["trait_app_wedge"]       = safe_norm(df["sg_app_12m"].fillna(df["sg_app_12m"].median())*0.45 + df["cf_short_game"].fillna(0)*0.25 + med("fw_50_100_val")*0.30)
df["trait_app_100_150"]     = safe_norm(df["sg_app_12m"].fillna(df["sg_app_12m"].median())*0.50 + df["cf_approach"].fillna(0)*0.20 + med("fw_100_150_val")*0.30)
df["trait_app_150_200"]     = safe_norm(df["sg_app_12m"].fillna(df["sg_app_12m"].median())*0.50 + med("fw_150_200_val")*0.50)
df["trait_ott_accuracy"]    = safe_norm(df["sg_ott_12m"].fillna(df["sg_ott_12m"].median())*0.40 + df["da_delta"].fillna(0)*0.04 + df["cf_accuracy"].fillna(0)*0.30 + med("cf_fairway")*0.30)
df["trait_ott_distance"]    = safe_norm(df["sg_ott_12m"].fillna(df["sg_ott_12m"].median())*0.60 + df["dd_delta"].fillna(0)*0.02 + df["cf_distance"].fillna(0)*0.40)
df["trait_putt_short_conv"] = safe_norm(df["sg_putt_12m"].fillna(df["sg_putt_12m"].median())*0.55 + med("cf_putt_2_5ft")*0.45)
df["trait_putt_lag"]        = safe_norm(df["sg_putt_12m"].fillna(df["sg_putt_12m"].median())*0.50 + med("cf_putt_5_30ft")*0.50)
df["trait_arg_rough"]       = safe_norm(df["sg_arg_12m"].fillna(df["sg_arg_12m"].median())*0.55 + med("cf_rough")*0.25 + med("rgh_u150_val")*0.20)
df["trait_arg_bunker"]      = safe_norm(df["sg_arg_12m"].fillna(df["sg_arg_12m"].median())*0.50 + med("cf_bunker")*0.50)
df["trait_par5_scoring"]    = safe_norm(df["sg_app_12m"].fillna(df["sg_app_12m"].median())*0.40 + df["sg_ott_12m"].fillna(df["sg_ott_12m"].median())*0.30 + df["sg_arg_12m"].fillna(df["sg_arg_12m"].median())*0.30)

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

# Form signal
field_sg_med = df["sg_total_12m"].median()
df["sg_total_2026"]     = df["sg_total_2026"].fillna(df["sg_total_12m"].fillna(field_sg_med))
df["form_vs_baseline"]  = df["sg_total_2026"] - df["sg_total_12m"].fillna(field_sg_med)

print("  Traits rebuilt OK")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Load current model outputs
# ═══════════════════════════════════════════════════════════════════════════════
vts = pd.read_csv(DEP / "vts_full.csv")
vts.columns = [c.strip() for c in vts.columns]
# Key columns needed: name_key, vts_final, tier, rank_model, win_pct, top5_pct,
#   top10_pct, top20_pct, anti_pattern_flags, venue_fit_delta, venue_fit_conf_band,
#   venue_history_delta, comp_course_adjustment, primary_risk_trait, trace_notes

with open(DEP / "event_payload.json") as f:
    payload = json.load(f)

# Flatten payload tiers
all_payload_players = []
for t in range(1, 6):
    for p in payload["tiers"].get(f"tier_{t}", []):
        all_payload_players.append(p)
payload_by_nk = {}
for p in all_payload_players:
    # Reconstruct name_key from player_name "Last, First"
    nk = nk_comma(p["player_name"])
    payload_by_nk[nk] = p

vts_by_nk = {}
for _, row in vts.iterrows():
    vts_by_nk[str(row.get("name_key",""))] = row.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Narrative generation helpers
# ═══════════════════════════════════════════════════════════════════════════════

def tier_label(score: float) -> str:
    if score >= 80: return "elite"
    if score >= 65: return "strong"
    if score >= 50: return "mid"
    if score >= 35: return "below-mid"
    return "weak"

def pct_rank(score: float) -> str:
    if score >= 90: return "top-5"
    if score >= 80: return "top-10"
    if score >= 65: return "top-25"
    if score >= 50: return "mid-field"
    if score >= 35: return "bottom-25"
    return "bottom-10"

# Venue-specific positive driver explanations (no generic language)
POS_DRIVERS = {
    "app_wedge":       "wedge-proximity dominance from ≤150 yd — primary scoring lever at short par-70 birdie-fest",
    "app_100_150":     "mid-iron precision at 100–150 yd scoring zone — consistent regulation birdie looks",
    "app_150_200":     "longer-iron approach accuracy sustains scoring distance without course-length premium",
    "ott_accuracy":    "positional driving on Bentgrass fairways; avoids penalty exposure at water-lined holes 15–17",
    "ott_distance":    "driving power reaches par-5 landing zones and opens wedge angles on shorter par-4s",
    "putt_short_conv": "birdie-conversion efficiency at 2–5 ft on Bentgrass/Poa — turns created looks into strokes gained",
    "putt_lag":        "Bentgrass pace control limits three-putt leaks; maintains scoring tempo in birdie-fest field",
    "arg_rough":       "rough-scrambling from 4\" Bluegrass/fescue is above field baseline; holds scoring momentum after misses",
    "arg_bunker":      "bunker recovery efficiency reduces bogey exposure on penalty-hole setups",
    "par5_scoring":    "par-5 birdie rate (adj −0.29/round historically) adds bonus strokes to floor",
}

# Venue-specific drag trait explanations
DRAG_TRAITS = {
    "app_wedge":       "wedge liability at <150 yd; critical deficiency in birdie-fest where approach quality determines scoring floor",
    "app_100_150":     "sub-field mid-iron precision; loses regulation birdie probability at primary approach zone",
    "app_150_200":     "longer-iron inconsistency; less critical at this yardage but adds bogey variance on non-wedge holes",
    "ott_accuracy":    "spray pattern elevates water risk at holes 15–17; forced position play compresses scoring ceiling",
    "ott_distance":    "shorter off-tee reduces approach angles on par-4s but is a minor drag at this sub-6,850-yd track",
    "putt_short_conv": "short-putt conversion below field rate; cannot cash the 8–10 birdie looks generated per round",
    "putt_lag":        "lag-distance exposure on stimp-12 Bentgrass/Poa; three-putt risk accumulates over 72 holes",
    "arg_rough":       "rough-approach liability from moderate 4\" fescue; scrambling margin thinner than field average",
    "arg_bunker":      "bunker escapes below field average; adds bogey strokes on an otherwise scoring-friendly layout",
    "par5_scoring":    "below-average par-5 scoring rate; leaves bonus strokes on the table at a historically low scoring venue",
}

AP_EXPLANATIONS = {
    "bomb_and_spray":      "BOMB+SPRAY: driving length provides no course-specific premium at 6,844 yds; spray pattern creates water-penalty exposure at closing holes 15–17 and bentgrass rough penalties",
    "wedge_liability":     "WEDGE LIABILITY: APP profile <150 yd is below field median; loses equity every hole where the birdie-fest field is converting wedge looks",
    "poor_birdie_conv":    "POOR BIRDIE CONV: short-putt efficiency is below field rate; cannot convert the birdie looks generated in a scoring-rich environment",
    "rough_approach_liab": "ROUGH APPROACH LIAB: approach from moderate 4\" Bluegrass/fescue rough is below field baseline; bogey-penalty accumulation risk over 72 holes",
}

def form_narrative(row) -> str:
    fvb = float(row["form_vs_baseline"]) if not pd.isna(row.get("form_vs_baseline")) else 0.0
    sg_12m = float(row["sg_total_12m"]) if not pd.isna(row.get("sg_total_12m")) else 0.0
    sg_2026 = float(row["sg_total_2026"]) if not pd.isna(row.get("sg_total_2026")) else 0.0
    rounds_2026 = row.get("rounds_2026", None)
    rd_str = f" ({int(rounds_2026)} 2026 events)" if pd.notna(rounds_2026) and rounds_2026 > 0 else ""

    if fvb > 0.30:
        return (f"2026 SG_Total={sg_2026:.2f}{rd_str} vs 12m baseline {sg_12m:.2f} — "
                f"elevated +{fvb:.2f}; approach+putting sharpness above recent baseline")
    elif fvb > 0.08:
        return (f"2026 SG_Total={sg_2026:.2f}{rd_str} vs 12m baseline {sg_12m:.2f} — "
                f"slight upward trend (+{fvb:.2f}); no form gate triggered")
    elif fvb < -0.50:
        return (f"2026 SG_Total={sg_2026:.2f}{rd_str} vs 12m baseline {sg_12m:.2f} — "
                f"form decline {fvb:.2f}; form gate applied; base skill moderates downside")
    elif fvb < -0.15:
        return (f"2026 SG_Total={sg_2026:.2f}{rd_str} vs 12m baseline {sg_12m:.2f} — "
                f"mild decline {fvb:.2f}; within expected variance, no gate triggered")
    else:
        return (f"2026 SG_Total={sg_2026:.2f}{rd_str} vs 12m baseline {sg_12m:.2f} — "
                f"flat form ({fvb:+.2f}); stable baseline used for scoring")

def vh_narrative(row) -> str:
    rounds  = float(row["vh_rounds"]) if not pd.isna(row.get("vh_rounds")) else 0.0
    vh_sg   = float(row["vh_sg"])     if not pd.isna(row.get("vh_sg"))     else 0.0
    vs_exp  = float(row["versus_expected"]) if not pd.isna(row.get("versus_expected")) else 0.0
    ch_adj  = float(row["ch_adjustment"])   if not pd.isna(row.get("ch_adjustment"))   else 0.0

    if rounds == 0:
        return "No recorded starts at TPC River Highlands; venue history delta = 0. Model relies on neutral-skill + venue-fit layers only."
    elif rounds <= 2:
        return (f"{int(rounds)} start(s) at TPC River Highlands — too sparse for statistical weight. "
                f"HistSG={vh_sg:.3f}/rd; qualitative signal only (20% weight). "
                f"ch_adj={ch_adj:+.3f}, vs_expected={vs_exp:+.3f}.")
    elif rounds <= 4:
        return (f"{int(rounds)} starts at TPC River Highlands (partial history, 50% weight). "
                f"HistSG={vh_sg:.3f}/rd; ch_adj={ch_adj:+.3f}, vs_expected={vs_exp:+.3f}. "
                f"Directional signal, not statistically stable.")
    else:
        sign = "above" if vs_exp > 0 else "below"
        return (f"{int(rounds)} starts at TPC River Highlands (full 5+ weight). "
                f"HistSG={vh_sg:.3f}/rd; {sign} contemporary-field baseline by {abs(vs_exp):.3f} SG. "
                f"ch_adj={ch_adj:+.3f} (calibrated); blend: 50% ch_adj + 30% vs_expected + 20% exp_adj.")

def conviction_statement(row, vts_row, traits_ranked) -> str:
    tier  = int(vts_row.get("tier", 3))
    vts   = float(vts_row.get("vts_final", 50.0))
    vfd   = float(vts_row.get("venue_fit_delta", 0.0))
    rounds = float(row["vh_rounds"])
    ap    = str(vts_row.get("anti_pattern_flags", ""))
    top_trait = traits_ranked[0]["key"] if traits_ranked else ""

    fit_dir = "positive venue-fit delta" if vfd > 0 else "modest venue-fit drag"
    hist_str = f"{int(rounds)}-round course history active" if rounds >= 5 else "limited course history; fit-dominant model"
    ap_clean = ap.strip() if ap and ap.lower() not in ("","nan","none") else ""
    ap_str   = f"; penalized for {ap_clean}" if ap_clean else ""

    return (f"Tier {tier} (VTS {vts:.1f}): {fit_dir} ({vfd:+.1f}) against neutral baseline; "
            f"lead trait {top_trait.replace('_',' ').upper()} at TPC River Highlands weighted 22% in fit model; "
            f"{hist_str}{ap_str}.")

def risk_failure_condition(row, vts_row, drag_traits) -> tuple:
    """Returns (risk_vector, named_failure_condition)"""
    pri_risk  = str(vts_row.get("primary_risk_trait", "ARG_Bunker")).strip()
    ap        = str(vts_row.get("anti_pattern_flags", "")).strip()
    vh_rounds = float(row["vh_rounds"])
    vfd       = float(vts_row.get("venue_fit_delta", 0.0))
    drag_name = drag_traits[0]["key"] if drag_traits else "ott_accuracy"

    risk_map = {
        "ARG_Bunker":      "bunker recovery (lowest weighted-contribution trait in kit)",
        "PUTT_Lag":        "Bentgrass lag-putting pace control (stimp 12, Poa annua mixed greens)",
        "OTT_Distance":    "positional control (distance advantage removed at sub-6,850-yd layout)",
        "OTT_Accuracy":    "driving spray into bentgrass fairways and water exposure at holes 15–17",
        "APP_Wedge":       "wedge proximity consistency from inside 100 yd",
        "APP_100-150":     "mid-iron precision at primary scoring yardage",
        "PUTT_BirdieConv": "short-putt conversion (2–5 ft Bentgrass birdie window)",
        "ARG_Rough":       "rough scrambling from 4\" Bluegrass/fescue",
    }
    risk_str = risk_map.get(pri_risk, f"weakness in {pri_risk.lower()} profile")

    # Build named failure condition
    parts = []
    if ap:
        for a in ap.split(","):
            ak = a.strip()
            if ak in AP_EXPLANATIONS:
                parts.append(AP_EXPLANATIONS[ak])
    if vfd < -5:
        parts.append(f"venue-fit drag ({vfd:+.1f}) against neutral baseline; fit mismatch grows if short-iron game declines mid-tournament")
    if vh_rounds >= 5 and float(row.get("versus_expected", 0) or 0) < -0.1:
        parts.append(f"negative vs-expected history ({row.get('versus_expected',0):+.3f}) signals pattern of under-performing field baseline at this venue")
    parts.append(f"primary structural risk is {risk_str}; if this signal deteriorates across 72 holes, scoring floor compresses")
    if vfd > 3 and vh_rounds < 3:
        parts.append("high venue-fit score is projection-based with limited course-history corroboration; confidence band is medium")

    failure = " | ".join(parts) if parts else f"Primary downside: {risk_str}."
    return pri_risk, failure


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Build per-player card data
# ═══════════════════════════════════════════════════════════════════════════════
print("Building player cards …")

BRIEF_TIERS = {1: "rich", 2: "rich", 3: "medium", 4: "compact", 5: "compact"}
TOP25_NAMES = None  # Will be determined by rank

# Load rank from vts_full
vts_rank = {}
for _, r in vts.iterrows():
    vts_rank[str(r.get("name_key",""))] = int(r.get("rank_model", 99))

enriched_players = []

for _, row in df.iterrows():
    nk = row["name_key"]
    vts_row  = vts_by_nk.get(nk, {})
    pay_row  = payload_by_nk.get(nk, {})

    rank = vts_rank.get(nk, 99)
    tier = int(vts_row.get("tier", 5)) if vts_row else 5
    brief_depth = "rich" if rank <= 25 else BRIEF_TIERS.get(tier, "compact")

    # --- Build trait_scores list ---
    trait_scores = []
    for wkey, tcol in TRAIT_COLS.items():
        score = float(row[tcol]) if tcol in df.columns and not pd.isna(row[tcol]) else 50.0
        trait_scores.append({
            "key":        wkey,
            "label":      TRAIT_LABELS[wkey],
            "weight":     VENUE_WEIGHTS[wkey],
            "score":      round(score, 1),
            "tier_label": tier_label(score),
            "pct_rank":   pct_rank(score),
        })

    # Sort by weighted contribution (weight × score) descending
    trait_scores.sort(key=lambda t: t["weight"] * t["score"], reverse=True)

    # Top 3 positive, bottom 2 drag (by score)
    scores_by_score = sorted(trait_scores, key=lambda t: t["score"], reverse=True)
    top_pos  = [t for t in scores_by_score[:4] if t["score"] >= 50][:3]
    bot_drag = [t for t in scores_by_score if t["score"] < 50][:2]

    # --- Course fit explanation ---
    vfd = float(vts_row.get("venue_fit_delta", 0.0)) if vts_row else 0.0
    vf_conf = str(vts_row.get("venue_fit_conf_band", "medium"))
    comp_adj = float(vts_row.get("comp_course_adjustment", 0.0)) if vts_row else 0.0

    pos_lines = [POS_DRIVERS[t["key"]] for t in top_pos]
    drag_lines = [DRAG_TRAITS[t["key"]] for t in bot_drag]
    comp_note = (
        f"Comp-course contribution: {comp_adj:+.1f} VTS (Colonial CC, TPC Potomac, Harbour Town fit)"
        if abs(comp_adj) > 0.5
        else "Comp-course contribution minimal (<0.5 VTS); primary signal from trait model"
    )

    course_fit_explanation = {
        "positive_drivers": pos_lines if pos_lines else ["Neutral fit; no dominant positive trait above field average"],
        "drag_traits":      drag_lines if drag_lines else ["No significant drag traits identified below field median"],
        "net_vfd":          round(vfd, 2),
        "confidence_band":  vf_conf,
        "comp_course_note": comp_note,
    }

    # --- Narrative blocks ---
    ap_raw   = vts_row.get("anti_pattern_flags", "") if vts_row else ""
    ap_flags = "" if (str(ap_raw).lower() in ("","nan","none","0")) else str(ap_raw).strip()
    pri_risk, named_failure = risk_failure_condition(row, vts_row if vts_row else {}, bot_drag)

    if brief_depth in ("rich", "medium"):
        form_win  = form_narrative(row)
        vh_story  = vh_narrative(row)
        conv_stmt = conviction_statement(row, vts_row if vts_row else {}, trait_scores)
        pen_parts = []
        if ap_flags and ap_flags.strip():
            for a in ap_flags.split(","):
                ak = a.strip()
                if ak: pen_parts.append(AP_EXPLANATIONS.get(ak, ak))
        pen_summary = " | ".join(pen_parts) if pen_parts else "No anti-pattern flags. No debut penalty. No form gate."
    else:
        # Compact
        form_win  = f"Form: SG_Total(12m)={row.get('sg_total_12m',0.0):.2f}" if not pd.isna(row.get("sg_total_12m")) else "Form: n/a"
        vh_rds    = int(float(row["vh_rounds"])) if not pd.isna(row.get("vh_rounds")) else 0
        vh_story  = f"{vh_rds} starts at TPC River Highlands" if vh_rds > 0 else "No TPC River Highlands history"
        conv_stmt = str(vts_row.get("tier_reason","")) if vts_row else ""
        pen_parts = []
        if ap_flags and ap_flags.strip():
            for a in ap_flags.split(","):
                ak = a.strip()
                if ak: pen_parts.append(ak.replace("_"," ").upper())
        pen_summary = "AP: " + ", ".join(pen_parts) if pen_parts else "No AP flags."

    # NeutralSkill summary
    ns_idx = float(vts_row.get("neutral_skill_index", 50.0)) if vts_row else 50.0
    sg12   = float(row.get("sg_total_12m", 0.0)) if not pd.isna(row.get("sg_total_12m")) else 0.0
    depth  = str(vts_row.get("data_depth_class","medium")) if vts_row else "medium"
    ns_summary = f"TrueSG(12m)={sg12:.2f}; depth={depth}; NeutralIdx={ns_idx:.1f}"

    # VenueFit summary
    vfs_score = float(vts_row.get("venue_fit_score", 50.0)) if vts_row else 50.0
    lead_trait = trait_scores[0]["key"].replace("_"," ").upper() if trait_scores else "—"
    vf_summary = (f"VFS={vfs_score:.1f}; VFD={vfd:+.1f}; CompAdj={comp_adj:+.1f}; lead={lead_trait}; "
                  f"conf={vf_conf}")

    card = {
        "player_name":   pay_row.get("player_name", row["player_name"]),
        "name_key":      nk,
        "rank":          rank,
        "tier":          tier,
        "brief_depth":   brief_depth,
        "vts_final":     float(vts_row.get("vts_final", 50.0)) if vts_row else 50.0,
        "win_pct":       float(pay_row.get("win_pct", 0.0)) if pay_row else 0.0,
        "top5_pct":      float(pay_row.get("top5_pct", 0.0)) if pay_row else 0.0,
        "top10_pct":     float(pay_row.get("top10_pct", 0.0)) if pay_row else 0.0,
        "top20_pct":     float(pay_row.get("top20_pct", 0.0)) if pay_row else 0.0,
        "make_cut_pct":  "not_applicable",
        "miss_cut_pct":  "not_applicable",
        "anti_pattern_flags": ap_flags,
        "trait_scores":       trait_scores,
        "course_fit_explanation": course_fit_explanation,
        "neutral_skill_summary":  ns_summary,
        "venue_fit_summary":      vf_summary,
        "venue_history_summary":  vh_story,
        "form_window":            form_win,
        "penalties_summary":      pen_summary,
        "risk_vector":            pri_risk,
        "conviction_statement":   conv_stmt,
        "named_failure_condition":named_failure,
        "trace_notes":  str(vts_row.get("trace_notes","")) if vts_row else "",
    }
    enriched_players.append(card)

# Sort by rank
enriched_players.sort(key=lambda p: p["rank"])
print(f"  Built {len(enriched_players)} player cards")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Write enriched player_briefs.json
# ═══════════════════════════════════════════════════════════════════════════════
from collections import defaultdict
by_tier = defaultdict(list)
for p in enriched_players:
    by_tier[p["tier"]].append(p)

briefs_out = {
    "event":         "Travelers Championship",
    "venue":         "TPC River Highlands",
    "generated_at":  datetime.now().isoformat(),
    "no_cut_note":   payload["event"]["no_cut_note"],
    "schema_version":"1.1",
    "brief_tiers":   {"1":"rich","2":"rich","3":"medium (rank<=25 rich)","4":"compact","5":"compact"},
    "tier_1":  by_tier[1],
    "tier_2":  by_tier[2],
    "tier_3":  by_tier[3],
    "tier_4":  by_tier[4],
    "tier_5":  by_tier[5],
}

with open(DEP / "player_briefs.json", "w") as f:
    json.dump(briefs_out, f, indent=2)
print(f"  Wrote player_briefs.json ({sum(len(v) for v in by_tier.values())} players)")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — Inject trait_scores + course_fit_explanation into event_payload.json
# ═══════════════════════════════════════════════════════════════════════════════
card_by_nk = {c["name_key"]: c for c in enriched_players}

for tier_key in ("tier_1","tier_2","tier_3","tier_4","tier_5"):
    for p in payload["tiers"].get(tier_key, []):
        nk = nk_comma(p["player_name"])
        card = card_by_nk.get(nk)
        if not card:
            continue
        p["trait_scores"]             = card["trait_scores"]
        p["course_fit_explanation"]   = card["course_fit_explanation"]
        p["form_window"]              = card["form_window"]
        p["venue_history_narrative"]  = card["venue_history_summary"]
        p["conviction_statement"]     = card["conviction_statement"]
        p["named_failure_condition"]  = card["named_failure_condition"]
        p["brief_depth"]              = card["brief_depth"]

with open(DEP / "event_payload.json", "w") as f:
    json.dump(payload, f, indent=2)
print("  Updated event_payload.json with trait_scores + course-fit data")
print("\nEnrichment complete.")
