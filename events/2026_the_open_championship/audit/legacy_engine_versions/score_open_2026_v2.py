"""
VenueDNA 2026 — The Open Championship
Scoring Engine v2 — Canonical GSO schema (0-100 VTS)
Weights: NSI 40% | VFS 30% | VHN 15% | Form 15%
"""

import csv, json, math, re, unicodedata, pathlib
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE  = pathlib.Path(__file__).parent.parent
INP   = BASE / "input"
OUT   = BASE / "output"
DEPLOY = BASE / "deploy" / "data"
OUT.mkdir(exist_ok=True)
DEPLOY.mkdir(parents=True, exist_ok=True)

EVENT_SLUG = "2026_the_open_championship"
NOW        = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Name normalisation ─────────────────────────────────────────────────────────
def nkey(name):
    """Canonical key: 'Last, First' or 'First Last' → lowercase_underscore."""
    if not name:
        return ""
    s = unicodedata.normalize("NFD", name.strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for src, dst in [("Ø","O"),("ø","o"),("Æ","AE"),("æ","ae"),("Å","A"),("å","a"),
                     ("ß","ss"),("ñ","n"),("Ñ","N"),("ü","u"),("Ü","U")]:
        s = s.replace(src, dst)
    s = s.lower().strip()
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?(?=[\s,]|$)", "", s)
    if "," in s:
        parts = s.split(",", 1)
        last, first = parts[0].strip(), parts[1].strip()
    else:
        tokens = s.split()
        last  = tokens[-1] if tokens else ""
        first = " ".join(tokens[:-1])
    key = f"{last}_{first}".replace("-","").replace(" ","_")
    return re.sub(r"[^a-z0-9_]", "", key)

def display_name(name):
    """'Last, First' → 'First Last'."""
    if "," in name:
        parts = name.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name.strip()

# ── CSV loaders ───────────────────────────────────────────────────────────────
def load_csv(path, key_fn=None):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if key_fn:
        return {key_fn(r): r for r in rows if r}
    return rows

def safe_f(val, default=None):
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return default

# ── Load all input files ──────────────────────────────────────────────────────
print("Loading input files…")

tee_rows   = load_csv(INP / "the_open_championship_player_field_R1_R2_teetimes.csv")
FIELD_KEYS = {nkey(r["player_name"]): r for r in tee_rows}
FIELD_NAMES = {nkey(r["player_name"]): display_name(r["player_name"]) for r in tee_rows}

sg12       = load_csv(INP / "pga_sg_query_l12.csv",    key_fn=lambda r: nkey(r["player_name"]))
sg24       = load_csv(INP / "pga_sg_query_l24.csv",    key_fn=lambda r: nkey(r["player_name"]))
sg6        = load_csv(INP / "pga_sg_query_6.csv",      key_fn=lambda r: nkey(r["player_name"]))
dgperf     = load_csv(INP / "dg_performance_2026.csv", key_fn=lambda r: nkey(r["player_name"]))
dgskill    = load_csv(INP / "dg_skill_ratings.csv",    key_fn=lambda r: nkey(r["player_name"]))
dgdecomp   = load_csv(INP / "dg_decomposition.csv",    key_fn=lambda r: nkey(r["player_name"]))
trending   = load_csv(INP / "pga_field_trending_table.csv", key_fn=lambda r: nkey(r["player_name"]))
ch_raw     = load_csv(INP / "royal_birkdale_gc_CH.csv", key_fn=lambda r: nkey(r["player_name"]))

# CFA file uses Last Name / First Name columns
cfa_rows = load_csv(INP / "the_open_championship_coursefitadjustments.csv")
cfa = {}
for r in cfa_rows:
    if r.get("Last Name"):
        k = nkey(r["Last Name"] + ", " + r.get("First Name",""))
        cfa[k] = r

# APP skill files – SG per shot by distance bucket
app_sg_rows = load_csv(INP / "app_skill_l12_sg.csv")
app_sg = {}
for r in app_sg_rows:
    k = nkey(r["player_name"])
    app_sg[k] = r   # overwrite; only one row per player (l12_months)

app_prox_rows = load_csv(INP / "app_skill_l12_prox.csv")
app_prox = {}
for r in app_prox_rows:
    k = nkey(r["player_name"])
    app_prox[k] = r

# Venue / weather config
with open(INP / "venue_birkdale_2026.json", encoding="utf-8") as f:
    VENUE = json.load(f)

with open(INP / "birkdale_full_course_weather_data_2026.json", encoding="utf-8") as f:
    WEATHER = json.load(f)

# Past winners
past_w_rows = load_csv(INP / "the_open_championship_past_winners_courses.csv")

print(f"  Field: {len(FIELD_KEYS)} players")
print(f"  L12 SG: {len(sg12)} | DG skill: {len(dgskill)} | CH: {len(ch_raw)} | CFA: {len(cfa)}")

# ── Trait weights (GSO-compatible, Open-tuned) ────────────────────────────────
TRAIT_DEFS = [
    {"key": "app_150_200",      "label": "APP 150-200 (Long Iron)", "weight": 0.30},
    {"key": "ott_positional",   "label": "OTT / Positional Drive",  "weight": 0.20},
    {"key": "app_overall",      "label": "APP Overall",              "weight": 0.15},
    {"key": "driving_accuracy", "label": "Driving Accuracy",         "weight": 0.12},
    {"key": "sg_putt",          "label": "Putting (Links-Regressed)","weight": 0.13},
    {"key": "sg_arg",           "label": "Short Game/ARG",           "weight": 0.10},
]
TRAIT_WEIGHT = {t["key"]: t["weight"] for t in TRAIT_DEFS}

# ── Collect raw trait values for all field players ────────────────────────────
print("Collecting raw trait values…")

raw = {}   # nkey → {trait_key: float}

for k in FIELD_KEYS:
    raw[k] = {}

    # SG L12 data
    s12 = sg12.get(k, {})
    raw[k]["sg_putt"]   = safe_f(s12.get("putt_mean"))
    raw[k]["sg_arg"]    = safe_f(s12.get("arg_mean"))
    raw[k]["app_overall"] = safe_f(s12.get("app_mean"))
    raw[k]["ott_l12"]   = safe_f(s12.get("ott_mean"))
    raw[k]["t2g_l12"]   = safe_f(s12.get("t2g_mean"))
    raw[k]["total_l12"] = safe_f(s12.get("total_mean"))
    raw[k]["acc_l12"]   = safe_f(s12.get("acc_mean"))
    raw[k]["dist_l12"]  = safe_f(s12.get("dist_mean"))
    raw[k]["events_l12"]= safe_f(s12.get("events_played"), 0)

    # DG performance 2026 (fallback for SG)
    dp = dgperf.get(k, {})
    raw[k]["app_true"]  = safe_f(dp.get("app_true"))
    raw[k]["ott_true"]  = safe_f(dp.get("ott_true"))
    raw[k]["arg_true"]  = safe_f(dp.get("arg_true"))
    raw[k]["putt_true"] = safe_f(dp.get("putt_true"))
    raw[k]["total_true"]= safe_f(dp.get("total_true"))

    # DG skill predictions
    dk = dgskill.get(k, {})
    raw[k]["sg_app_pred"]  = safe_f(dk.get("sg_app_pred"))
    raw[k]["sg_ott_pred"]  = safe_f(dk.get("sg_ott_pred"))
    raw[k]["sg_arg_pred"]  = safe_f(dk.get("sg_arg_pred"))
    raw[k]["sg_putt_pred"] = safe_f(dk.get("sg_putt_pred"))
    raw[k]["sg_total_pred"]= safe_f(dk.get("sg_total_pred"))
    raw[k]["acc_pred"]     = safe_f(dk.get("accuracy_pred"))
    raw[k]["dist_pred"]    = safe_f(dk.get("distance_pred"))

    # DG decomposition
    dd = dgdecomp.get(k, {})
    raw[k]["dg_final"]     = safe_f(dd.get("final_prediction"))
    raw[k]["dg_cfa"]       = safe_f(dd.get("course_fit_total_adj"), 0)
    raw[k]["dg_dist_adj"]  = safe_f(dd.get("driving_dist_adj"), 0)
    raw[k]["dg_acc_adj"]   = safe_f(dd.get("driving_acc_adj"), 0)

    # APP skill 150-200 FW zone
    asg = app_sg.get(k, {})
    raw[k]["app_150_200_raw"] = safe_f(asg.get("150_200_fw_value"))
    raw[k]["app_100_150_raw"] = safe_f(asg.get("100_150_fw_value"))
    raw[k]["app_over200_raw"] = safe_f(asg.get("over_200_fw_value"))
    raw[k]["rough_150_raw"]   = safe_f(asg.get("over_150_rgh_value"))

    # Form / trending
    tr = trending.get(k, {})
    raw[k]["true_sg_l20"]    = safe_f(tr.get("true_sg_l20"))
    raw[k]["vs_baseline_l20"]= safe_f(tr.get("vs_baseline_l20"))

    # Short-term SG (6-event)
    s6 = sg6.get(k, {})
    raw[k]["total_l6"]  = safe_f(s6.get("total_mean"))
    raw[k]["app_l6"]    = safe_f(s6.get("app_mean"))

    # Course history
    ch = ch_raw.get(k, {})
    raw[k]["ch_rounds"]  = safe_f(ch.get("rounds_played"), 0)
    raw[k]["ch_vs_exp"]  = safe_f(ch.get("versus_expected"), 0)
    raw[k]["ch_adj"]     = safe_f(ch.get("ch_adjustment"), 0)
    raw[k]["exp_adj"]    = safe_f(ch.get("experience_adjustment"), 0)
    raw[k]["ch_true_sg"] = safe_f(ch.get("historical_true_sg"))
    raw[k]["ch_2008"]    = ch.get("2008 (The Open Championship)", "")
    raw[k]["ch_2017"]    = ch.get("2017 (The Open Championship)", "")

    # CFA skill adjustments
    cf = cfa.get(k, {})
    raw[k]["cfa_sg_adj"]  = safe_f(cf.get("Total SG Adjustment"), 0)
    raw[k]["cfa_app_adj"] = safe_f(cf.get("APPROACH"), 0)
    raw[k]["cfa_sg_adj2"] = safe_f(cf.get("SHORT GAME"), 0)

    # OTT positional composite: accuracy-weighted OTT
    ott_v = raw[k]["ott_l12"] or raw[k]["sg_ott_pred"] or 0
    acc_v = raw[k]["acc_l12"] or raw[k]["acc_pred"] or 0
    # OTT positional = blend OTT SG (0.65) + accuracy normalization (0.35)
    # Accuracy at Birkdale: mean around 0.55 (55%); higher = better
    # Normalize acc relative to field: 0.65 = average → 0; each 0.05 ≈ 0.1 SG equiv
    acc_offset = (acc_v - 0.58) * 2.0   # field average acc ≈ 0.58
    raw[k]["ott_positional_raw"] = 0.65 * ott_v + 0.35 * acc_offset

# ── Compute NSI (Neutral Skill Index 0–100) ───────────────────────────────────
print("Computing NSI…")

def best_total_sg(k):
    r = raw[k]
    # Prefer L12 total; fallback to DG perf true; fallback to DG pred
    v = r.get("total_l12")
    if v is None:
        v = r.get("total_true")
    if v is None:
        v = r.get("sg_total_pred")
    return v

total_sg_vals = {k: best_total_sg(k) for k in FIELD_KEYS}
valid_vals = sorted([v for v in total_sg_vals.values() if v is not None])
N = len(valid_vals)

def percentile_0_100(val, sorted_vals):
    """Field-relative percentile, 0 = worst, 100 = best."""
    if val is None:
        return 50.0
    n = len(sorted_vals)
    rank = sum(1 for v in sorted_vals if v < val)
    return round(rank / max(n - 1, 1) * 100, 2)

nsi_raw = {k: percentile_0_100(total_sg_vals[k], valid_vals) for k in FIELD_KEYS}

# ── Compute per-trait field percentiles ───────────────────────────────────────
print("Computing trait percentiles…")

def field_pctile(trait_key, raw_key):
    """Return {nkey: 0-100 score} for a given raw field."""
    vals = {k: raw[k].get(raw_key) for k in FIELD_KEYS}
    valid_sorted = sorted([v for v in vals.values() if v is not None])
    return {k: percentile_0_100(vals[k], valid_sorted) for k in FIELD_KEYS}

# Each trait → field-percentile score
p_app150   = field_pctile("app_150_200",    "app_150_200_raw")
p_ott_pos  = field_pctile("ott_positional", "ott_positional_raw")
p_app_ovr  = field_pctile("app_overall",    "app_overall")
p_drv_acc  = field_pctile("driving_accuracy","acc_l12")
p_putt     = field_pctile("sg_putt",        "sg_putt")
p_arg      = field_pctile("sg_arg",         "sg_arg")

def trait_score(k):
    # Apply links-regressed putting dampening (×0.85 for links courses)
    putt_adj = round(p_putt[k] * 0.85 + 50 * 0.15, 2)   # pull toward 50
    return {
        "app_150_200":      p_app150[k],
        "ott_positional":   p_ott_pos[k],
        "app_overall":      p_app_ovr[k],
        "driving_accuracy": p_drv_acc[k],
        "sg_putt":          putt_adj,
        "sg_arg":           p_arg[k],
    }

# ── Compute VFS (Venue Fit Score 0–100) ───────────────────────────────────────
print("Computing VFS…")

def compute_vfs(k):
    ts = trait_score(k)
    weighted = sum(TRAIT_WEIGHT[tk] * ts[tk] for tk in TRAIT_WEIGHT)
    # Apply DG course fit adjustment (cfa_sg_adj) as a small modifier ±5 pts
    cfa_boost = (raw[k].get("cfa_sg_adj") or 0) * 5.0
    # Apply decomp course fit adj as a smaller modifier ±3 pts
    dg_boost  = (raw[k].get("dg_cfa") or 0) * 1.5
    vfs = max(0.0, min(100.0, weighted + cfa_boost + dg_boost))
    return round(vfs, 2)

vfs_vals = {k: compute_vfs(k) for k in FIELD_KEYS}

# ── Compute VHN (Venue History Normalized 0–100) ──────────────────────────────
print("Computing VHN…")

def compute_vhn(k):
    r = raw[k]
    rounds = int(r.get("ch_rounds") or 0)
    ch_adj = r.get("ch_adj") or 0
    exp_adj= r.get("exp_adj") or 0
    vs_exp = r.get("ch_vs_exp") or 0

    if rounds == 0:
        # No Birkdale history: neutral baseline, small Open-history boost from CFA
        cfa_adj = r.get("cfa_sg_adj") or 0
        open_boost = min(abs(cfa_adj) * 2.0, 5.0) * (1 if cfa_adj >= 0 else -1)
        return round(max(10.0, min(90.0, 50.0 + open_boost)), 2)

    # Has Birkdale history: scale from vs_expected and rounds
    # rounds=4 → moderate weight, rounds=8 → full weight
    rounds_wt = min(rounds / 8.0, 1.0)
    # vs_expected in ±3 range; scale to ±30 VHN points
    history_delta = vs_exp * 10.0 * rounds_wt
    # ch_adj/exp_adj are small refinements ±0.05; scale × 50
    fine_adj = (ch_adj + exp_adj) * 50.0
    vhn = 50.0 + history_delta + fine_adj
    return round(max(5.0, min(95.0, vhn)), 2)

vhn_vals = {k: compute_vhn(k) for k in FIELD_KEYS}

# ── Compute Form (0–100) ──────────────────────────────────────────────────────
print("Computing Form…")

def compute_form(k):
    r = raw[k]
    vs_bl = r.get("vs_baseline_l20")
    total6 = r.get("total_l6")
    total12= r.get("total_l12")

    if vs_bl is not None:
        # vs_baseline ≈ 0 is neutral; ±1.5 is typical range
        form_score = 50.0 + vs_bl * 12.0
    elif total6 is not None and total12 is not None:
        form_score = 50.0 + (total6 - total12) * 15.0
    else:
        form_score = 50.0

    return round(max(10.0, min(92.0, form_score)), 2)

def form_class(score):
    if score >= 68: return "HOT"
    if score >= 58: return "WARM"
    if score >= 42: return "NEUTRAL"
    if score >= 32: return "COOL"
    return "COLD"

form_vals = {k: compute_form(k) for k in FIELD_KEYS}

# ── Compute VTS Final ──────────────────────────────────────────────────────────
print("Computing VTS Final…")

W_NSI, W_VFS, W_VHN, W_FORM = 0.40, 0.30, 0.15, 0.15

def compute_vts(k):
    nsi  = nsi_raw[k]
    vfs  = vfs_vals[k]
    vhn  = vhn_vals[k]
    form = form_vals[k]
    return round(W_NSI*nsi + W_VFS*vfs + W_VHN*vhn + W_FORM*form, 2)

vts_vals = {k: compute_vts(k) for k in FIELD_KEYS}

# ── Assign Tiers ───────────────────────────────────────────────────────────────
all_vts = sorted(vts_vals.values())
N_field = len(all_vts)

def assign_tier(vts):
    if vts >= 78.0:  return 1
    if vts >= 63.5:  return 2
    if vts >= 48.0:  return 3
    if vts >= 33.0:  return 4
    return 5

TIER_LABELS = {
    1: "Structural Winner",
    2: "Primary Contender",
    3: "Dark Horse",
    4: "Fragile Path",
    5: "Fade / Cut Risk",
}

# ── Probabilities (softmax) ───────────────────────────────────────────────────
print("Computing probabilities…")

VTS_LIST = list(vts_vals.values())

def softmax_prob(vts, T, total_pct):
    """Normalised softmax probability."""
    exp_v = math.exp(vts / T)
    exp_sum = sum(math.exp(v / T) for v in VTS_LIST)
    return round(exp_v / exp_sum * total_pct, 2)

def logistic(vts, mid=53.0, steep=0.10):
    """Logistic make-cut probability."""
    return round(100.0 / (1 + math.exp(-steep * (vts - mid))), 1)

def win_ceiling(vts, vfs, nsi):
    """Composite ceiling metric 0–100."""
    return round(min(100, (vts * 0.5 + vfs * 0.3 + nsi * 0.2)), 2)

def contention_score(vts, vfs):
    return round(min(100, vts * 0.6 + vfs * 0.4), 2)

def floor_score(vts, form):
    return round(min(100, vts * 0.7 + form * 0.3), 2)

probs = {}
for k in FIELD_KEYS:
    vts = vts_vals[k]
    probs[k] = {
        "win":    softmax_prob(vts, 14.0, 100.0),
        "top5":   softmax_prob(vts, 17.5, 500.0),
        "top10":  softmax_prob(vts, 21.0, 1000.0),
        "top20":  softmax_prob(vts, 27.0, 2000.0),
        "cut":    logistic(vts),
    }
    probs[k]["miss_cut"] = round(100.0 - probs[k]["cut"], 1)

# ── Best betting lane ──────────────────────────────────────────────────────────
def best_lane(p):
    if p["win"] >= 4.0:        return "Winner"
    if p["win"] >= 2.0:        return "Top 5"
    if p["top10"] >= 15.0:     return "Top 10"
    if p["top20"] >= 30.0:     return "Top 20"
    if p["cut"] >= 72.0:       return "Make Cut"
    if p["cut"] < 45.0:        return "Miss Cut"
    return "Pass"

# ── Anti-pattern detection ────────────────────────────────────────────────────
print("Computing anti-patterns…")

AP_META = {
    "bomb_and_spray":      {"label": "Bomb + Spray",            "cls": "bomb"},
    "approach_liability":  {"label": "Approach Liability",       "cls": "wedge"},
    "long_iron_weakness":  {"label": "Long-Iron Weakness",       "cls": "bomb"},
    "poor_links_putter":   {"label": "Poor Links Putter",        "cls": "birdie"},
    "debut_risk":          {"label": "Debut Risk",               "cls": "rough"},
    "weak_arg_links":      {"label": "Weak ARG / Links Rough",   "cls": "rough"},
}

def detect_anti_patterns(k):
    r = raw[k]
    ts = trait_score(k)
    flags = []

    ott_v   = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    acc_v   = r.get("acc_l12") or r.get("acc_pred") or 0
    app_v   = r.get("app_overall") or r.get("sg_app_pred") or 0
    putt_v  = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    arg_v   = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    a150_v  = r.get("app_150_200_raw")

    # Bomb + Spray: above-average OTT but poor accuracy at Birkdale
    if ott_v > 0.4 and acc_v < -0.10:
        flags.append("bomb_and_spray")

    # Approach Liability: below-field approach game in primary zone
    if app_v < 0.0 or (a150_v is not None and a150_v < -0.02):
        flags.append("approach_liability")

    # Long-Iron Weakness: below 35th percentile in 150-200 zone
    if ts["app_150_200"] < 35.0:
        flags.append("long_iron_weakness")

    # Poor Links Putter: below-average putting (links-regressed amplifies)
    if putt_v < -0.12:
        flags.append("poor_links_putter")

    # Weak ARG: below-average short game in links context
    if arg_v < -0.08:
        flags.append("weak_arg_links")

    # Debut Risk: zero Birkdale rounds AND no CFA adjustment
    ch_rds = int(r.get("ch_rounds") or 0)
    cfa_adj = abs(r.get("cfa_sg_adj") or 0)
    if ch_rds == 0 and cfa_adj < 0.01:
        flags.append("debut_risk")

    return flags

ap_flags = {k: detect_anti_patterns(k) for k in FIELD_KEYS}

# ── Badges ────────────────────────────────────────────────────────────────────
def compute_badges(k, tier, p, nsi, vfs):
    r = raw[k]
    flags = ap_flags[k]
    badges = []

    # Course Horse: positive Birkdale history
    ch_rds = int(r.get("ch_rounds") or 0)
    ch_adj = r.get("ch_adj") or 0
    if ch_rds >= 4 and ch_adj > 0.005:
        badges.append("Course Horse")

    # Iron Edge: elite VFS and not already Course Horse
    if vfs >= 64.0 and "Course Horse" not in badges:
        badges.append("Iron Edge")

    # Elite NSI
    if nsi >= 85.0:
        badges.append("Elite NSI")

    # Form Spike
    vs_bl = r.get("vs_baseline_l20") or 0
    fc = form_class(form_vals[k])
    if vs_bl >= 0.9:
        badges.append("Form Spike")
    elif fc in ("COOL", "COLD"):
        badges.append("Form Cold")

    # Debut Watch: first Open / first Birkdale
    if ch_rds == 0:
        badges.append("Debut Watch")

    # Cut Sweat
    if p["cut"] < 60.0:
        badges.append("Cut Sweat")

    # Anti-Pattern
    if len(flags) >= 2:
        badges.append("Anti-Pattern")

    # Fragile Favorite: T1/T2 with flags
    if tier <= 2 and len(flags) >= 1:
        badges.append("Fragile Favorite")
        if "Anti-Pattern" in badges:
            badges.remove("Anti-Pattern")   # Fragile Favorite supersedes

    # Tier 3+ ceiling
    if tier >= 3:
        if p["win"] >= 2.0 and "Live Longshot" not in badges:
            badges.append("Dark Horse")
        elif (win_ceiling(vts_vals[k], vfs, nsi) >= 75 and
              "Dark Horse" not in badges):
            badges.append("Ceiling Play")

    # Volatile Putter: top-15% putt variance (high std_dev relative to field)
    s12d = sg12.get(k, {})
    putt_std = safe_f(s12d.get("putt_std_dev"), 0)
    if putt_std > 2.0:   # >p85 of field L12 putt_std_dev distribution
        badges.append("Volatile Putter")

    return list(dict.fromkeys(badges))   # dedup preserve order

# ── Scoring band (for player modal) ──────────────────────────────────────────
BAND_DEFS = [
    (85, "Elite Contention Vector: Approach Driven", "#c9a84c"),
    (72, "Strong Contender: Long-Iron Profile",       "#22c55e"),
    (58, "Dark Horse: Ceiling Achievable",            "#60a5fa"),
    (44, "Fragile Path: Anti-Pattern Exposure",       "#fb923c"),
    (0,  "Fade / Cut Risk: Structural Disadvantage",  "#f87171"),
]

def scoring_band(vts):
    for thr, label, color in BAND_DEFS:
        if vts >= thr:
            return label, color
    return BAND_DEFS[-1][1], BAND_DEFS[-1][2]

def projected_scores(vts, nsi, form):
    """Projected R4 relative-to-par score (integer)."""
    # Par 70; expected winning score -8; field average ~+5 to par
    baseline_vs_par = 5  # average bogey count for mid-field players
    sg_contribution = (vts - 50) / 100 * 15   # elite players ≈ -10 below par
    expected = round(baseline_vs_par - sg_contribution)
    ceiling  = round(expected - 3 - (vts - 50) / 30)
    floor_v  = round(expected + 4 + (50 - form) / 25)
    def fmt(n):
        return (f"+{n}" if n > 0 else str(n))
    return fmt(expected), fmt(ceiling), fmt(floor_v)

# ── Conviction / narrative generation ────────────────────────────────────────
LINK_COUNTRIES = {"SCO","ENG","IRL","NIR","WAL","AUS","NZL","RSA","SWE","DEN","NOR","FIN"}

def pick_country(k):
    tr = tee_rows
    tt = FIELD_KEYS.get(k, {})
    # Try to get from teetimes (no country there, use empty)
    # DG skill ratings don't have country either
    # We'll derive from name patterns as best effort
    return ""

def conviction_statement(k, tier, nsi, vfs, fc):
    r = raw[k]
    app_v = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    arg_v = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    a150  = r.get("app_150_200_raw")
    name  = FIELD_NAMES.get(k, k)

    parts = []
    if app_v >= 0.8:
        parts.append(f"elite approach (SG:APP +{app_v:.2f}) directly matches Birkdale's 175–225yd demand")
    elif app_v >= 0.4:
        parts.append(f"strong approach game (SG:APP +{app_v:.2f}) in the primary scoring zone")
    elif app_v >= 0.05:
        parts.append(f"competent approach play (SG:APP +{app_v:.2f}) suits Birkdale's mid-iron corridors")
    elif app_v >= -0.15:
        parts.append(f"near-average approach (SG:APP {app_v:+.2f}) — below the required threshold for Birkdale's primary zone")
    else:
        parts.append(f"below-average approach (SG:APP {app_v:.2f}) creates significant exposure in Birkdale's primary scoring zone")

    ch_rds = int(r.get("ch_rounds") or 0)
    if ch_rds >= 8:
        parts.append(f"deep Birkdale pedigree ({ch_rds} rounds, {r.get('ch_2008','')} 2008 / {r.get('ch_2017','')} 2017)")
    elif ch_rds >= 4:
        parts.append(f"proven Birkdale performer ({ch_rds} rounds)")

    if fc == "HOT":
        parts.append("arriving in career-best form")
    elif fc == "COLD":
        parts.append("carrying significant form risk into the championship")

    return "; ".join(parts) + "."

def failure_condition(k):
    flags = ap_flags[k]
    r = raw[k]
    parts = []
    if "bomb_and_spray" in flags:
        parts.append("Birkdale's 22-yard corridors and gorse OB punish wayward driving severely")
    if "approach_liability" in flags or "long_iron_weakness" in flags:
        parts.append("below-field performance in the 150-200yd zone — the decisive scoring range")
    if "poor_links_putter" in flags:
        parts.append("links-surface putting volatility on medium-pace fescue greens")
    if "debut_risk" in flags:
        parts.append("no Birkdale or Open reference data — environmental calibration fully unknown")
    if "weak_arg_links" in flags:
        parts.append("below-field ARG skill in links rough and revetted bunkers")
    if not parts:
        ch_rds = int(r.get("ch_rounds") or 0)
        if ch_rds == 0:
            parts.append("standard high-variance Open Championship environment; debut uncertainty")
        else:
            parts.append("standard Open Championship variance; wind and firm conditions can neutralize any profile")
    return ". ".join(parts) + "."

def risk_vector(k, tier):
    flags = ap_flags[k]
    r = raw[k]
    vects = []
    if "bomb_and_spray" in flags:
        vects.append("accuracy risk off tee")
    if "approach_liability" in flags:
        vects.append("approach liability in primary scoring zone")
    if "debut_risk" in flags:
        vects.append("full links debut uncertainty")
    if "poor_links_putter" in flags:
        vects.append("putting volatility on links fescue")
    if tier >= 4:
        vects.append("below-field structural skill profile")
    return "; ".join(vects) if vects else "standard major championship variance"

# ── SG summaries ─────────────────────────────────────────────────────────────
def nsi_summary(k, nsi):
    r = raw[k]
    brie = r.get("app_overall") or r.get("sg_app_pred") or 0
    tvl  = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    putt = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    vfr  = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    return (f"NeutralSkill {nsi:.1f}/100 — DB Metrics: BRIE (APP) {brie:+.2f}, "
            f"TVL (OTT) {tvl:+.2f}, PUTT {putt:+.2f}, VFR (ARG) {vfr:+.2f}. "
            f"Approach game {'above' if brie>0 else 'below'} the scoring threshold Birkdale demands from 175-200yds.")

def vfs_summary(k, vfs, ts):
    r = raw[k]
    a150 = r.get("app_150_200_raw")
    flags = ap_flags[k]
    ap_str = "; ".join(AP_META[f]["label"] for f in flags[:2]) if flags else "No anti-pattern flags — clean structural profile"
    a150_str = f"APP 150-200 value {a150:+.3f}" if a150 is not None else "APP 150-200 data unavailable"
    return (f"VenueFit {vfs:.1f}/100 — {a150_str}. "
            f"{'Positive' if (a150 or 0)>0 else 'Negative'} APP 150-200 value "
            f"{'confirms' if (a150 or 0)>0 else 'exposes'} approach productivity in the primary scoring zone. "
            f"{ap_str}.")

def vhn_summary(k, vhn):
    r = raw[k]
    ch_rds = int(r.get("ch_rounds") or 0)
    ch_adj = r.get("ch_adj") or 0
    vs_exp = r.get("ch_vs_exp") or 0
    if ch_rds == 0:
        return f"VenueHistory {vhn:.1f}/100 — No Birkdale starts — open-environment debut. No course-specific calibration."
    yrs = []
    if r.get("ch_2008"): yrs.append(f"{r['ch_2008']} 2008")
    if r.get("ch_2017"): yrs.append(f"{r['ch_2017']} 2017")
    hist = " / ".join(yrs) if yrs else f"{ch_rds} rounds"
    return (f"VenueHistory {vhn:.1f}/100 — {ch_rds} Birkdale starts ({hist}). "
            f"True SG vs expected: {vs_exp:+.3f}. Course-history adj {ch_adj:+.3f}.")

def form_summary(k, form, fc):
    r = raw[k]
    vs_bl = r.get("vs_baseline_l20") or 0
    total_l20 = r.get("true_sg_l20") or 0
    return (f"Form {fc} (score {form:.1f}/100) — True SG L20: {total_l20:.2f}, "
            f"vs baseline: {vs_bl:+.2f}. "
            f"{'Positive momentum entering championship.' if fc in ('HOT','WARM') else 'Below seasonal baseline — negative momentum.' if fc == 'COLD' else '12-month baseline is the reference; no strong directional signal.'}")

def ap_summary(k):
    flags = ap_flags[k]
    if not flags:
        return "No anti-pattern flags. Clean structural profile — no recurring weak-link traits identified for Royal Birkdale."
    descs = {
        "bomb_and_spray":     "Bomb + Spray — accuracy penalised in 22-yard Birkdale corridors; gorse OB real scoring event",
        "approach_liability": "Approach Liability — below-field in the primary 150-200yd scoring zone",
        "long_iron_weakness": "Long-Iron Weakness — exposure in the dominant par-4 approach range at Birkdale",
        "poor_links_putter":  "Poor Links Putter — below-field on fescue; links surfaces amplify weak putting",
        "debut_risk":         "Debut Risk — no Birkdale or Open data; full environmental uncertainty",
        "weak_arg_links":     "Weak ARG/Links Rough — revetted bunkers and steep run-offs create up-and-down challenge",
    }
    parts = [descs.get(f, f) for f in flags]
    return "Anti-pattern flags: " + "; ".join(parts) + "."

def bet_path(p, tier, lane):
    paths = {
        "Winner": "Elite approach separates on par 4s 3, 6, 8, 16; positional tee play keeps card clean; contends R3–R4.",
        "Top 5":  "Strong NeutralSkill and venue fit create top-5 ceiling; most realistic path is top-10 via consistent ball-striking.",
        "Top 10": "Reliable contender profile with top-10 as the ceiling; unlikely to win but can post a high finish.",
        "Top 20": "Structural mid-tier player — make cut easily, final 20 realistic, win very thin.",
        "Make Cut": "Cut survival likely; weekend upside limited by structural weaknesses.",
        "Miss Cut": "Structural anti-patterns and cut probability below 50%; fading this player at Birkdale.",
        "Pass":   "Mixed profile — insufficient edge to recommend a bet. Monitor conditions and market.",
    }
    return paths.get(lane, paths["Pass"])

# ── Build player objects ──────────────────────────────────────────────────────
def _top_trait_bullets(k, app_v, ott_v, arg_v, putt_v, ts):
    r = raw[k]
    bullets = []
    if app_v >= 0.5:
        bullets.append(f"Elite approach — BRIE (APP) {app_v:+.2f} in Birkdale's 175–200yd zone")
    elif app_v >= 0.2:
        bullets.append(f"Strong approach — BRIE (APP) {app_v:+.2f} above field average")
    if ott_v >= 0.5:
        bullets.append(f"Elite off-tee — TVL (OTT) {ott_v:+.2f}, positional accuracy suits narrow Birkdale corridors")
    elif ts["driving_accuracy"] >= 65:
        bullets.append(f"Accurate driver — low miss-rate in Birkdale's punishing gorse corridors")
    if putt_v >= 0.3:
        bullets.append(f"Strong putting — SG:PUTT {putt_v:+.2f}, converts approach proximity on firm fescue greens")
    if arg_v >= 0.2:
        bullets.append(f"Short-game skill — VFR (ARG) {arg_v:+.2f}, escapes Birkdale's revetted bunkers")
    ch_rds = int(r.get("ch_rounds") or 0)
    if ch_rds >= 4:
        bullets.append(f"Proven Birkdale performer — {ch_rds} rounds of course-specific data")
    if not bullets:
        bullets.append("Workmanlike profile — no dominant trait edge at Royal Birkdale")
    return bullets[:4]


def _best_finish(r):
    f17 = r.get("ch_2017", "")
    f08 = r.get("ch_2008", "")
    best = None
    for f in [f17, f08]:
        if not f or f == "MC" or f == "WD":
            continue
        try:
            pos = int(f.replace("T","").strip())
            if best is None or pos < best:
                best = pos
        except Exception:
            pass
    return best


print("Building player objects…")

players_sorted = sorted(FIELD_KEYS.keys(), key=lambda k: -vts_vals[k])
all_players = []
rank = 1

for k in players_sorted:
    r = raw[k]
    tee = FIELD_KEYS[k]
    nsi  = nsi_raw[k]
    vfs  = vfs_vals[k]
    vhn  = vhn_vals[k]
    form = form_vals[k]
    vts  = vts_vals[k]
    tier = assign_tier(vts)
    p    = probs[k]
    fc   = form_class(form)
    ts   = trait_score(k)
    lane = best_lane(p)
    badges = compute_badges(k, tier, p, nsi, vfs)
    flags  = ap_flags[k]
    wc  = win_ceiling(vts, vfs, nsi)
    cs  = contention_score(vts, vfs)
    fs  = floor_score(vts, form)
    cls = round(logistic(vts, mid=48.0, steep=0.12), 2)
    band_label, band_color = scoring_band(vts)
    exp_sc, ceil_sc, floor_sc = projected_scores(vts, nsi, form)

    # SG values
    app_v  = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v  = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    arg_v  = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    putt_v = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    t2g_v  = r.get("t2g_l12") or round((app_v + ott_v), 3)

    name = FIELD_NAMES[k]
    parts = name.split(" ", 1)
    first_nm = parts[0] if len(parts) > 0 else ""
    last_nm  = parts[1] if len(parts) > 1 else ""

    pid = f"P{rank:03d}"

    trait_scores_list = []
    for td in TRAIT_DEFS:
        tk = td["key"]
        score_v = ts[tk]
        trait_scores_list.append({
            "key":    tk,
            "label":  td["label"],
            "weight": td["weight"],
            "score":  score_v,
            "imputed": score_v == 50.0,
        })

    ch_rds = int(r.get("ch_rounds") or 0)
    debut  = (ch_rds == 0 and abs(r.get("cfa_sg_adj") or 0) < 0.01)

    obj = {
        "player_id":            pid,
        "last_name":            last_nm,
        "first_name":           first_nm,
        "tier":                 tier,
        "rank":                 rank,
        "vts_final":            vts,
        "venue_fit_score":      vfs,
        "win_prob":             p["win"],
        "top5_prob":            p["top5"],
        "top10_prob":           p["top10"],
        "top20_prob":           p["top20"],
        "make_cut_prob":        p["cut"],
        "miss_cut_prob":        p["miss_cut"],
        "win_ceiling_score":    wc,
        "contention_score":     cs,
        "floor_score":          fs,
        "cut_survival_score":   cls,
        "best_betting_lane":    lane,
        "neutral_skill_summary":nsi_summary(k, nsi),
        "venue_fit_summary":    vfs_summary(k, vfs, ts),
        "venue_history_summary":vhn_summary(k, vhn),
        "form_summary":         form_summary(k, form, fc),
        "anti_pattern_summary": ap_summary(k),
        "drag_traits":          [AP_META[f]["label"] for f in flags],
        "risk_vector":          risk_vector(k, tier),
        "failure_condition":    failure_condition(k),
        "conviction_statement": conviction_statement(k, tier, nsi, vfs, fc),
        "decomposition": {
            "neutral_skill_index":  nsi,
            "venue_fit_delta":      vfs,
            "venue_history_delta":  vhn,
            "form_score":           form,
            "penalties":            0.0,
            "trace_notes": (f"NSI={nsi:.1f}(w=0.40) + VFS={vfs:.1f}(w=0.30) + "
                            f"VHN={vhn:.1f}(w=0.15) + FORM={form:.1f}(w=0.15) = VTS={vts:.1f}."),
        },
        "badges":               badges,
        "brief_depth":          "rich" if nsi > 60 else "standard",
        "top_traits":           _top_trait_bullets(k, app_v, ott_v, arg_v, putt_v, ts),
        "scoring": {
            "band":       band_label,
            "band_color": band_color,
            "expected":   exp_sc,
            "ceiling":    ceil_sc,
            "floor":      floor_sc,
        },
        "neutral_skill_index":      nsi,
        "venue_history_normalized": vhn,
        "form_score":               form,
        "sg_app_12m":               round(app_v, 3),
        "sg_ott_12m":               round(ott_v, 3),
        "sg_putt_12m":              round(putt_v, 3),
        "sg_arg_12m":               round(arg_v, 3),
        "sg_t2g_12m":               round(t2g_v, 3),
        "true_sg_last5":            round(r.get("true_sg_l20") or 0, 2),
        "true_sg_vs_baseline":      round(r.get("vs_baseline_l20") or 0, 2),
        "form_class":               fc,
        "data_depth_class":         "FULL" if ch_rds > 0 else "DEBUT",
        "venue_history_depth":      ("RICH" if ch_rds >= 8 else "MODERATE" if ch_rds >= 4 else "LIGHT" if ch_rds > 0 else "NONE"),
        "starts_at_birkdale":       ch_rds,
        "renaissance_start_count":  ch_rds,
        "best_finish_birkdale":     _best_finish(r),
        "tour_affiliation":         "DP World Tour / PGA Tour",
        "debut_flag":               debut,
        "app_150_200_value":        round(r.get("app_150_200_raw") or 0, 4),
        "app_100_150_value":        round(r.get("app_100_150_raw") or 0, 4),
        "app_over200_value":        round(r.get("app_over200_raw") or 0, 4),
        "rough_over150_value":      round(r.get("rough_150_raw") or 0, 4),
        "rough_under150_value":     0.0,
        "app_50_100_value":         0.0,
        "approach_composite_value": round(r.get("app_150_200_raw") or 0, 4),
        "venue_fit_total_adj":      round((r.get("cfa_sg_adj") or 0) + (r.get("dg_cfa") or 0), 3),
        "conviction_level":         ("HIGH" if tier <= 1 else "MEDIUM" if tier <= 2 else "STANDARD"),
        "ap_total_flags":           len(flags),
        "anti_pattern_flags":       "; ".join(AP_META[f]["label"] for f in flags) if flags else "none",
        "driving_distance_baseline":round(r.get("dist_l12") or 0, 1),
        "driving_accuracy_baseline":round(r.get("acc_l12") or r.get("acc_pred") or 0, 3),
        "driving_distance_fit_adj": round(r.get("dg_dist_adj") or 0, 3),
        "driving_accuracy_fit_adj": round(r.get("dg_acc_adj") or 0, 3),
        "dg_id":                    str(tee.get("dg_id", "")),
        "owgr_rank":                safe_f(tee.get("owgr_rank"), 999),
        "tvl_score":                round(ott_v, 3),
        "hew_score":                round(t2g_v, 3),
        "brie_score":               round(app_v, 3),
        "vfr_score":                round(arg_v, 3),
        "vhn_score":                round(r.get("ch_vs_exp") or 0, 3),
        "vhn_rounds":               ch_rds,
        "tee_time":                 tee.get("r1_teetime", "TBD"),
        "r1_teetime":               tee.get("r1_teetime", "TBD"),
        "r1_wave":                  tee.get("r1_wave", ""),
        "r1_starthole":             tee.get("r1_starthole", "1"),
        "r2_teetime":               tee.get("r2_teetime", "TBD"),
        "r2_wave":                  tee.get("r2_wave", ""),
        "r2_starthole":             tee.get("r2_starthole", "1"),
        "trait_scores":             trait_scores_list,
        # Alias columns for JS compatibility
        "win_pct":                  p["win"],
        "top5_pct":                 p["top5"],
        "top10_pct":                p["top10"],
        "top20_pct":                p["top20"],
    }
    all_players.append(obj)
    rank += 1



# ── Tier summary ──────────────────────────────────────────────────────────────
tier_counts = {}
for p in all_players:
    t = p["tier"]
    tier_counts[t] = tier_counts.get(t, 0) + 1

print("\nTIER DISTRIBUTION:")
for t in sorted(tier_counts):
    players_in_tier = [p for p in all_players if p["tier"] == t]
    avg_vts = sum(p["vts_final"] for p in players_in_tier) / len(players_in_tier)
    avg_win = sum(p["win_prob"] for p in players_in_tier) / len(players_in_tier)
    print(f"  T{t}: {tier_counts[t]:3d} players | avg VTS {avg_vts:.1f} | avg Win% {avg_win:.2f}")

print(f"\nWin% sum: {sum(p['win_prob'] for p in all_players):.1f}%")

# ── Value / Model Over / Under ────────────────────────────────────────────────
# Model Over: high VTS but low OWGR rank (market undervalues)
model_over = []
model_under = []
struct_fades = []

for p in all_players:
    owgr = p["owgr_rank"] or 999
    tier = p["tier"]
    vts  = p["vts_final"]
    win  = p["win_prob"]
    flags_count = p["ap_total_flags"]

    # Model Over: good VTS but market rank (owgr) is outside top 30
    if tier <= 2 and owgr > 40 and vts >= 65:
        model_over.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"OWGR #{int(owgr)} — model ranks T{tier} (VTS {vts:.1f}); structural approach fit suggests market undervaluation.",
        })

    # Model Under (true structural fades): T4/T5 OR T2-T3 with multiple flags
    if tier >= 4 and win < 0.5:
        struct_fades.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"T{tier} — structural skill gap at Royal Birkdale; {flags_count} anti-pattern flags.",
        })
    elif tier in (2, 3) and flags_count >= 2 and vts < 58:
        model_under.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"T{tier} with {flags_count} anti-pattern flags; VTS {vts:.1f} overstates market narrative; structural fade.",
        })

# ── Event context JSON ────────────────────────────────────────────────────────
event_ctx = {
    "event_id":            EVENT_SLUG,
    "event_name":          "2026 The Open Championship",
    "venue":               "Royal Birkdale Golf Club",
    "location":            "Southport, Merseyside, England",
    "dates":               "2026-07-17 to 2026-07-20",
    "tour":                "The Open Championship (R&A)",
    "field_size":          len(all_players),
    "cut_rule":            "Top 70 and ties after 36 holes",
    "par":                 VENUE["par"],
    "yards":               VENUE["yardage"],
    "course_type":         "Links",
    "variance_class":      "HIGH",
    "variance_rationale":  "Irish Sea wind exposure, firm/fast links conditions, revetted bunkers, par-70 layout concentrates scoring decisions.",
    "primary_scoring_zone":"Approach 150-200yds (dominant par-4 approach zone at 175–225yds)",
    "trait_weight_matrix": {
        "approach_150_200":  0.30,
        "sg_app_overall":    0.15,
        "sg_ott_positional": 0.20,
        "driving_accuracy":  0.12,
        "sg_putt":           0.13,
        "sg_arg_short_game": 0.10,
    },
    "model_version":       "VenueDNA v2",
    "generated_date":      "2026-07-15",
    "tier_counts":         {str(k): v for k, v in tier_counts.items()},
    "anti_pattern_count":  sum(1 for p in all_players if p["ap_total_flags"] >= 1),
    "debut_count":         sum(1 for p in all_players if p["debut_flag"]),
    "similar_courses":     list(VENUE.get("similar_course_mapping", {}).items()),
    "expected_winning_score": VENUE["scoring_par_baseline"]["expected_winning_score_relative_to_par"],
    "wind_forecast":       "10-25mph W/NW/SW Irish Sea; gusts possible 30-35mph on holes 4, 6, 12, 13, 15, 18",
}

# ── Event payload JSON ────────────────────────────────────────────────────────
payload = {
    "event":          "2026 The Open Championship",
    "players":        all_players,
    "generated_date": "2026-07-15",
    "model_version":  "VenueDNA v2",
}

# ── Weather JSON (deploy/data) ────────────────────────────────────────────────
wind = WEATHER.get("wind_profile", {})
weather_deploy = {
    "event_id": EVENT_SLUG,
    "source": "Irish Met Office / UK Met Office, Southport, updated July 15 2026",
    "tournament_summary": (
        f"Expected {wind.get('expected_speed_mph',{}).get('min',10)}–"
        f"{wind.get('expected_speed_mph',{}).get('max',25)}mph W/NW Irish Sea winds. "
        "Links-specialist profile rewarded. Winning score expected -8 ± 3. "
        "Firm/fast forecast amplifies approach precision and ARG skill."
    ),
    "winning_score_range": "-5 to -13",
    "traits_amplified": ["Approach precision 150-200yds", "Positional driving accuracy",
                         "ARG / revetted bunker skill", "Wind management", "Trajectory control"],
    "rounds": [
        {"round": 1, "date": "Thu Jul 17", "wind_mph": "12-18", "wind_dir": "W/NW",
         "tag": "Firm/Breezy", "color": "#f59e0b", "note": "Opening conditions. Positional driving critical."},
        {"round": 2, "date": "Fri Jul 18", "wind_mph": "15-22", "wind_dir": "NW/SW",
         "tag": "Challenging", "color": "#dc2626", "note": "Wind increases. 150-200yd approaches decisive."},
        {"round": 3, "date": "Sat Jul 19", "wind_mph": "10-18", "wind_dir": "W",
         "tag": "Moving Day", "color": "#22c55e", "note": "Scoring window. Ball-strikers separate."},
        {"round": 4, "date": "Sun Jul 20", "wind_mph": "14-20", "wind_dir": "W/NW",
         "tag": "Championship Sunday", "color": "#c9a84c", "note": "Pressure links golf. Course management wins."},
    ],
}

# ── VTS Full CSV ──────────────────────────────────────────────────────────────
vts_rows = []
for p in all_players:
    vts_rows.append({
        "rank":           p["rank"],
        "player_name":    p["first_name"] + " " + p["last_name"],
        "tier":           p["tier"],
        "vts_final":      p["vts_final"],
        "nsi":            p["neutral_skill_index"],
        "vfs":            p["venue_fit_score"],
        "vhn":            p["venue_history_normalized"],
        "form":           p["form_score"],
        "win_prob":       p["win_prob"],
        "top5_prob":      p["top5_prob"],
        "top10_prob":     p["top10_prob"],
        "top20_prob":     p["top20_prob"],
        "make_cut_prob":  p["make_cut_prob"],
        "sg_app_12m":     p["sg_app_12m"],
        "sg_ott_12m":     p["sg_ott_12m"],
        "sg_arg_12m":     p["sg_arg_12m"],
        "sg_putt_12m":    p["sg_putt_12m"],
        "brie_score":     p["brie_score"],
        "tvl_score":      p["tvl_score"],
        "vfr_score":      p["vfr_score"],
        "hew_score":      p["hew_score"],
        "app_150_200":    p["app_150_200_value"],
        "ch_rounds":      p["vhn_rounds"],
        "ch_vs_exp":      p["vhn_score"],
        "ap_flags":       p["ap_total_flags"],
        "form_class":     p["form_class"],
        "badges":         "; ".join(p["badges"]),
        "best_bet":       p["best_betting_lane"],
    })

# ── QA Report ────────────────────────────────────────────────────────────────
qa_report = {
    "event_id": EVENT_SLUG,
    "generated_at": NOW,
    "field_size": len(all_players),
    "trait_coverage": {},
    "imputed_players": [],
    "debut_players": [],
    "summary": {},
}

for td in TRAIT_DEFS:
    tk = td["key"]
    covered = sum(1 for p in all_players
                  if any(t["key"] == tk and not t["imputed"] for t in p["trait_scores"]))
    qa_report["trait_coverage"][tk] = {
        "covered": covered,
        "imputed": len(all_players) - covered,
        "coverage_pct": round(covered / len(all_players) * 100, 1),
    }

qa_report["debut_players"] = [
    p["first_name"] + " " + p["last_name"]
    for p in all_players if p["debut_flag"]
]
qa_report["summary"] = {
    "total_players":      len(all_players),
    "debut_count":        len(qa_report["debut_players"]),
    "anti_pattern_count": sum(1 for p in all_players if p["ap_total_flags"] >= 1),
    "tier_distribution":  {str(k): v for k, v in tier_counts.items()},
    "win_pct_sum":        round(sum(p["win_prob"] for p in all_players), 1),
    "avg_vts":            round(sum(p["vts_final"] for p in all_players) / len(all_players), 2),
    "model_version":      "VenueDNA v2",
}

# ── Final analysis JSON (audit structure) ────────────────────────────────────
final_analysis = {
    "schema_version":  "2.0-pretournament",
    "generated_at":    "2026-07-15",
    "build_timestamp": NOW,
    "round":           0,
    "event_slug":      EVENT_SLUG,
    "enrichment_used": True,
    "metadata": {
        "event_name":        "2026 The Open Championship",
        "course_name":       "Royal Birkdale Golf Club",
        "par":               VENUE["par"],
        "total_par":         VENUE["par"] * 4,
        "round_label":       "Pre-Tournament",
        "is_final":          False,
        "is_full_tournament":False,
        "field_size_finished": len(all_players),
        "winner":            None,
    },
    "venue_summary": {
        "par":              VENUE["par"],
        "yardage":          VENUE["yardage"],
        "expected_winning_score": VENUE["scoring_par_baseline"]["expected_winning_score_relative_to_par"],
        "sigma":            VENUE["scoring_par_baseline"]["sigma_winning_score"],
        "primary_separator":"SG:APP 175–225yd mid-iron",
        "secondary_separator":"SG:ARG revetted bunkers",
        "putting_role":     "Dampened — lag avoidance over spike putting on firm fescue",
        "wind_role":        "Critical — 10-25mph W/NW/SW Irish Sea; H4, H6, H12, H13, H15, H18 spike difficulty",
        "upgrade_traits":   VENUE["player_trait_overrides"]["upgrade_traits"],
        "downgrade_traits": VENUE["player_trait_overrides"]["downgrade_traits"],
        "anti_patterns":    [g["threshold"] if isinstance(g, dict) else str(g)
                             for g in VENUE.get("penalties_and_gates", {}).get("hard_gates", [])],
        "similar_courses":  list(VENUE.get("similar_course_mapping", {}).items()),
    },
    "tier_lists": {
        f"tier{t}": [
            {
                "playerName": p["first_name"] + " " + p["last_name"],
                "tier":       f"T{t}",
                "vtsFinal":   p["vts_final"],
                "nsi":        p["neutral_skill_index"],
                "vfs":        p["venue_fit_score"],
                "vhn":        p["venue_history_normalized"],
                "form":       p["form_score"],
                "winPct":     p["win_prob"],
                "top10Pct":   p["top10_prob"],
                "makeCutPct": p["make_cut_prob"],
                "badges":     p["badges"],
                "bettingPath":p["best_betting_lane"],
                "thesis":     p["conviction_statement"],
            }
            for p in all_players if p["tier"] == t
        ]
        for t in range(1, 6)
    },
    "value_section": {
        "modelOver":      model_over[:6],
        "modelUnder":     model_under[:6],
        "structuralFades":struct_fades[:8],
        "disclaimer":     ("VenueDNA is an analytical pre-tournament baseline. "
                           "Probabilities are model-derived from skill and venue data. "
                           "Not financial betting advice. Conditions and late withdrawals can shift all projections."),
    },
    "anti_pattern_flags": {
        "hardGatePlayers": [
            {"playerName": p["first_name"] + " " + p["last_name"],
             "flags": ap_flags[nkey(p["first_name"] + " " + p["last_name"])],
             "tier": p["tier"]}
            for p in all_players
            if "bomb_and_spray" in ap_flags.get(nkey(p["first_name"] + " " + p["last_name"]), []) or
               "approach_liability" in ap_flags.get(nkey(p["first_name"] + " " + p["last_name"]), [])
        ][:10],
        "softGatePlayers": [
            {"playerName": p["first_name"] + " " + p["last_name"],
             "flags": ap_flags[nkey(p["first_name"] + " " + p["last_name"])],
             "tier": p["tier"]}
            for p in all_players
            if "debut_risk" in ap_flags.get(nkey(p["first_name"] + " " + p["last_name"]), [])
        ][:10],
        "antiPatternNarratives": {
            "bomb_and_spray":     {"description": "Elite distance but below-field driving accuracy — Birkdale's 22-yard corridors and OB gorse are fatal for wide drivers."},
            "approach_liability": {"description": "Below-field approach in 150-200yd zone — the decisive scoring range at Birkdale par 4s."},
            "long_iron_weakness": {"description": "Below 35th percentile in 150-200yd FW — highest-weighted trait at Royal Birkdale."},
            "poor_links_putter":  {"description": "Below-field putting on links fescue — medium-pace greens amplify variance; 3-putt avoidance critical."},
            "debut_risk":         {"description": "No Birkdale or Open history — wind-reading, shot trajectory, and course management unproven at links level."},
            "weak_arg_links":     {"description": "Below-field ARG in links context — revetted pot bunkers require specialized up-and-down technique."},
        },
    },
    "allPlayers": all_players,
    "weather":    weather_deploy,
    "event_context": event_ctx,
    "qa_summary": qa_report["summary"],
}

# ── Write outputs ─────────────────────────────────────────────────────────────
print("\nWriting outputs…")

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  {path.name}: {path.stat().st_size/1024:.0f} KB")

def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name}: {path.stat().st_size/1024:.0f} KB")

# Output dir
write_json(OUT  / f"{EVENT_SLUG}_eventpayload.json",   payload)
write_json(OUT  / f"{EVENT_SLUG}_playerbriefs.json",   {"players": all_players})
write_json(OUT  / f"{EVENT_SLUG}_final_analysis.json", final_analysis)
write_json(OUT  / f"{EVENT_SLUG}_qareport.json",        qa_report)
write_csv (OUT  / f"{EVENT_SLUG}_vtsfull.csv",          vts_rows)

# Deploy dir (copies for board)
write_json(DEPLOY / "event_payload.json",   payload)
write_json(DEPLOY / "player_briefs.json",   {"players": all_players})
write_json(DEPLOY / "final_analysis.json",  final_analysis)
write_json(DEPLOY / "weather.json",         weather_deploy)
write_json(DEPLOY / "event_context.json",   event_ctx)
write_csv (DEPLOY / "vts_full.csv",         vts_rows)

# ── Top-line summary ──────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TOP-LINE SPOT CHECK")
print("="*70)
spotlight = ["Scottie Scheffler","Rory McIlroy","Matt Fitzpatrick","Tommy Fleetwood",
             "Jon Rahm","Si Woo Kim","Robert MacIntyre","Ludvig Aberg","Viktor Hovland",
             "Shane Lowry","Sepp Straka"]
for p in all_players:
    pn = p["first_name"] + " " + p["last_name"]
    if pn in spotlight:
        ch = p["vhn_rounds"]
        mech = p["conviction_statement"][:70]
        print(f"\n{pn}")
        print(f"  T{p['tier']} | VTS={p['vts_final']} | NSI={p['neutral_skill_index']} | VFS={p['venue_fit_score']} | VHN={p['venue_history_normalized']} | Form={p['form_score']}")
        print(f"  Win={p['win_prob']}% | Top10={p['top10_prob']}% | Cut={p['make_cut_prob']}%")
        print(f"  Birkdale: {ch} rds | Flags: {p['ap_total_flags']} | Badges: {p['badges']}")
        print(f"  Mechanism: {mech}…")

print("\nDone.")
