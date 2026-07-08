import os
import pandas as pd

stats = pd.read_csv("stats.csv")
stats1 = pd.read_csv("stats (1).csv")
stats2 = pd.read_csv("stats (2).csv")
stats3 = pd.read_csv("stats (3).csv")
stats4 = pd.read_csv("stats (4).csv")
stats6 = pd.read_csv("stats (6).csv")
stats7 = pd.read_csv("stats (7).csv")
form = pd.read_csv("RBC Heritage 2026 Current Form.csv")

for df in [stats, stats1, stats2, stats3, stats4, stats6, stats7]:
    if "PLAYER" in df.columns:
        df.rename(columns={"PLAYER": "Player"}, inplace=True)

base = stats[["PLAYER_ID", "Player", "TOTAL ROUNDS"]].copy()
base.rename(columns={"PLAYER_ID": "player_id", "TOTAL ROUNDS": "total_rounds"}, inplace=True)

b1 = stats1[["Player", "# OF BIRDIES", "TOTAL ROUNDS"]].copy()
b1.rename(columns={"# OF BIRDIES": "birdies", "TOTAL ROUNDS": "birdie_rounds"}, inplace=True)
base = base.merge(b1, on="Player", how="left")

sg2 = stats2[["Player", "TOTAL SG:T2G", "MEASURED ROUNDS"]].copy()
sg2.rename(columns={"TOTAL SG:T2G": "tot_sg_t2g", "MEASURED ROUNDS": "measured_rounds"}, inplace=True)
base = base.merge(sg2, on="Player", how="left")

sg3 = stats3[["Player", "AVG"]].copy()
sg3.rename(columns={"AVG": "sg_ott"}, inplace=True)

sg4 = stats4[["Player", "AVG"]].copy()
sg4.rename(columns={"AVG": "sg_arg"}, inplace=True)

sg6 = stats6[["Player", "AVG"]].copy()
sg6.rename(columns={"AVG": "sg_app"}, inplace=True)

sg7 = stats7[["Player", "AVG"]].copy()
sg7.rename(columns={"AVG": "sg_putt_global"}, inplace=True)

for part in [sg3, sg4, sg6, sg7]:
    base = base.merge(part, on="Player", how="left")

base["birdies_per_round"] = base["birdies"] / base["birdie_rounds"]
base["sg_t2g"] = base["tot_sg_t2g"] / base["measured_rounds"]
base["sg_putt_bermuda_used"] = 0.75 * base["sg_putt_global"]

def finish_to_sg(finish):
    if pd.isna(finish):
        return None
    f = str(finish).strip().upper()
    if f in ["CUT", "WD", "DQ", ""]:
        return -0.60
    if f.startswith("T"):
        f = f[1:]
    try:
        pos = int(f)
    except:
        return None

    if pos == 1:
        return 2.40
    elif pos <= 3:
        return 2.10
    elif pos <= 5:
        return 1.80
    elif pos <= 10:
        return 1.50
    elif pos <= 20:
        return 1.10
    elif pos <= 30:
        return 0.60
    elif pos <= 40:
        return 0.25
    elif pos <= 60:
        return 0.00
    else:
        return -0.60

event_mult = {
    "Masters": 1.05,
    "Valero": 1.00,
    "Houston": 1.00,
    "Valspar": 1.00,
    "PLAYERS": 1.05
}

form_cols = ["Masters", "Valero", "Houston", "Valspar", "PLAYERS"]

form_rows = []
for _, row in form.iterrows():
    vals = []
    for ev in form_cols:
        sg = finish_to_sg(row[ev])
        if sg is not None:
            vals.append(sg * event_mult[ev])

    if len(vals) == 0:
        form_sg = None
    else:
        weights_template = [0.10, 0.10, 0.10, 0.25, 0.35]
        weights = weights_template[-len(vals):]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        form_sg = sum(w * v for w, v in zip(weights, vals))

    form_rows.append({"Player": row["Player"], "FormSG": form_sg})

form_df = pd.DataFrame(form_rows)
base = base.merge(form_df, on="Player", how="left")

valid_form = base["FormSG"].notna()
if valid_form.any():
    form_mean = base.loc[valid_form, "FormSG"].mean()
    form_sd = base.loc[valid_form, "FormSG"].std(ddof=0)
    if form_sd == 0:
        form_sd = 1.0
    base["FormScore"] = (50 + 15 * ((base["FormSG"] - form_mean) / form_sd)).clip(0, 100)
else:
    base["FormScore"] = 50.0

trait_inputs = [
    "sg_app",
    "sg_ott",
    "sg_putt_bermuda_used",
    "sg_arg",
    "birdies_per_round"
]

for col in trait_inputs:
    mean_val = base[col].mean()
    sd_val = base[col].std(ddof=0)
    if sd_val == 0:
        sd_val = 1.0
    base[f"TraitScore_{col}"] = (50 + 15 * ((base[col] - mean_val) / sd_val)).clip(0, 100)

base["TraitScore_APP"] = base["TraitScore_sg_app"]
base["TraitScore_OTT"] = base["TraitScore_sg_ott"]
base["TraitScore_Putt"] = base["TraitScore_sg_putt_bermuda_used"]
base["TraitScore_ARG"] = base["TraitScore_sg_arg"]
base["TraitScore_Par5"] = base["TraitScore_birdies_per_round"]
base["TraitScore_Pressure"] = base["TraitScore_birdies_per_round"]

base["VenueFit"] = (
    0.35 * base["TraitScore_APP"] +
    0.20 * base["TraitScore_OTT"] +
    0.18 * base["TraitScore_Putt"] +
    0.12 * base["TraitScore_ARG"] +
    0.10 * base["TraitScore_Par5"] +
    0.05 * base["TraitScore_Pressure"]
)

base["comp_adjustment_vts"] = 0.0
base["debut_flag"] = False
base["debut_penalty_vts"] = 0.0

out_cols = [
    "player_id",
    "Player",
    "total_rounds",
    "measured_rounds",
    "birdies",
    "birdie_rounds",
    "birdies_per_round",
    "sg_ott",
    "sg_app",
    "sg_arg",
    "sg_putt_global",
    "sg_putt_bermuda_used",
    "sg_t2g",
    "FormSG",
    "FormScore",
    "TraitScore_APP",
    "TraitScore_OTT",
    "TraitScore_Putt",
    "TraitScore_ARG",
    "TraitScore_Par5",
    "TraitScore_Pressure",
    "VenueFit",
    "comp_adjustment_vts",
    "debut_flag",
    "debut_penalty_vts"
]

output = base[out_cols]

os.makedirs("output", exist_ok=True)
output_path = os.path.join("output", "harbour_town_2026_trait_form_matrix.csv")
output.to_csv(output_path, index=False)

print("Wrote:", output_path)
print(output.head())