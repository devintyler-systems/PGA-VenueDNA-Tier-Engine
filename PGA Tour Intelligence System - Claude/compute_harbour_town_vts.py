import os
import pandas as pd
import numpy as np

# 1) Load the trait+form matrix
matrix_path = "output/harbour_town_2026_trait_form_matrix.csv"
df = pd.read_csv(matrix_path)

# 2) Sample-size blending to get VTS_prePenalties

def compute_blend_weights(measured_rounds):
    if pd.isna(measured_rounds):
        return 0.55, 0.45, "lt20_missing"
    if measured_rounds >= 40:
        return 0.70, 0.30, "ge40"
    if 20 <= measured_rounds <= 39:
        return 0.60, 0.40, "20to39"
    return 0.55, 0.45, "lt20"

vts_pre = []
blend_rows = []

for _, row in df.iterrows():
    venue = row["VenueFit"]
    form_score = row["FormScore"]
    mr = row["measured_rounds"]
    w_v, w_f, bin_label = compute_blend_weights(mr)

    # base blended value
    vts0 = w_v * venue + w_f * form_score

    # clamp for <20 measured rounds: FormScore can move at most ±12 from VenueFit
    if bin_label.startswith("lt20"):
        max_delta = 12.0
        vts_low  = venue - max_delta
        vts_high = venue + max_delta
        vts_clamped = min(max(vts0, vts_low), vts_high)
    else:
        vts_clamped = vts0

    vts_pre.append(vts_clamped)
    blend_rows.append({
        "w_venue": w_v,
        "w_form": w_f,
        "sample_bin": bin_label
    })

df["VTS_prePenalties"] = vts_pre
blend_df = pd.DataFrame(blend_rows)
df = pd.concat([df, blend_df], axis=1)

# 3) Anti-pattern thresholds (field-based)

# SG:OTT quartile threshold
ott_valid = df["sg_ott"].notna()
ott_q75 = df.loc[ott_valid, "sg_ott"].quantile(0.75) if ott_valid.any() else 0.0

# Birdies median
bird_valid = df["birdies_per_round"].notna()
bird_med = df.loc[bird_valid, "birdies_per_round"].median() if bird_valid.any() else 0.0

# 4) Anti-pattern detection AP1–AP4

df["AP1"] = False
df["AP2"] = False
df["AP3"] = False
df["AP4"] = False
df["AP1_penalty"] = 0.0
df["AP2_penalty"] = 0.0
df["AP3_penalty"] = 0.0
df["AP4_penalty"] = 0.0

for idx, row in df.iterrows():
    sg_ott = row["sg_ott"]
    sg_arg = row["sg_arg"]
    sg_putt = row["sg_putt_global"]
    sg_t2g = row["sg_t2g"]
    bpr = row["birdies_per_round"]

    # AP1: Bomb-spray
    if (pd.notna(sg_ott) and pd.notna(sg_arg) and pd.notna(sg_putt)
        and sg_ott >= ott_q75 and sg_arg < 0 and sg_putt < 0):
        df.at[idx, "AP1"] = True
        df.at[idx, "AP1_penalty"] = -8.0

    # AP2: Bermuda drag
    if (pd.notna(sg_putt) and pd.notna(sg_t2g)
        and sg_putt <= -0.25 and -0.10 <= sg_t2g <= 0.10):
        df.at[idx, "AP2"] = True
        df.at[idx, "AP2_penalty"] = -6.0

    # AP3: Wedge gap
    if (pd.notna(row["sg_app"]) and pd.notna(bpr) and pd.notna(sg_arg)
        and row["sg_app"] > 0 and bpr < bird_med and sg_arg < 0):
        df.at[idx, "AP3"] = True
        df.at[idx, "AP3_penalty"] = -4.0

    # AP4: High-variance OTT at tight courses
    if (pd.notna(sg_ott) and pd.notna(sg_t2g) and pd.notna(sg_arg)
        and sg_ott >= 0.3 and sg_t2g < 0 and sg_arg < 0):
        df.at[idx, "AP4"] = True
        df.at[idx, "AP4_penalty"] = -5.0

# Total AP penalty
df["anti_pattern_penalties_vts_total"] = (
    df["AP1_penalty"] + df["AP2_penalty"] + df["AP3_penalty"] + df["AP4_penalty"]
)

# 5) Debut penalties

# Here we don't have actual Harbour Town history yet, so treat everyone as non-debut by default.
# Once you have a debut list, set df.loc[mask, "debut_flag"] = True accordingly.

# Apply specified debut penalties
def compute_debut_penalty(is_debut, comp_rounds_ge8=False):
    if not is_debut:
        return 0.0
    return -6.0 if comp_rounds_ge8 else -11.0

# Placeholder: no one is debut until you set it.
df["debut_penalty_vts"] = df["debut_penalty_vts"]  # keep 0.0 for now

# 6) Comp-course adjustment (already 0, ensure cap ±6)
df["comp_adjustment_vts"] = df["comp_adjustment_vts"].clip(-6.0, 6.0)

# 7) Final VTS

df["base_vts"] = df["VTS_prePenalties"] + df["comp_adjustment_vts"]
df["vts_after_debut"] = df["base_vts"] + df["debut_penalty_vts"]
df["final_vts"] = df["vts_after_debut"] + df["anti_pattern_penalties_vts_total"]

# Clip to [0, 100]
df["final_vts"] = df["final_vts"].clip(0, 100)

# 8) Tiering

def assign_tier(vts):
    if vts >= 80:
        return "T1"
    if 65 <= vts <= 79:
        return "T2"
    if 50 <= vts <= 64:
        return "T3"
    if 35 <= vts <= 49:
        return "T4"
    return "T5"

df["tier"] = df["final_vts"].apply(assign_tier)

# 9) Save full VTS output

out_cols = [
    "player_id", "Player",
    "final_vts", "tier",
    "VenueFit", "FormScore",
    "w_venue", "w_form", "sample_bin",
    "comp_adjustment_vts",
    "debut_flag", "debut_penalty_vts",
    "AP1", "AP2", "AP3", "AP4",
    "AP1_penalty", "AP2_penalty", "AP3_penalty", "AP4_penalty",
    "anti_pattern_penalties_vts_total"
]

os.makedirs("output", exist_ok=True)
vts_path = os.path.join("output", "harbour_town_2026_vts_full.csv")
df[out_cols].to_csv(vts_path, index=False)
print("Wrote:", vts_path)