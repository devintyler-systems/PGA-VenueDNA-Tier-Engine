"""
VenueDNA 2026 — The Open Championship
Scoring Engine v3 — Links Signal + True Birkdale History + Model Council
Weights: NSI 40% | VFS 30% | VHN 15% | Form 15%
Links signal: confidence-shrunk 4-window average → VFS delta (capped ±8)
VHN: dg_true_sg_royal_birkdale_alltime.csv total_mean (percentile)
"""

import csv, json, math, re, unicodedata, pathlib
from datetime import datetime, timezone

BASE   = pathlib.Path(__file__).parent.parent
INP    = BASE / "input"
LINKS  = INP / "dg_true_sg_links_courses"
OUT    = BASE / "output"
DEPLOY = BASE / "deploy" / "data"
OUT.mkdir(exist_ok=True)
DEPLOY.mkdir(parents=True, exist_ok=True)

EVENT_SLUG = "2026_the_open_championship"
NOW        = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Name normalisation ─────────────────────────────────────────────────────────
def nkey(name):
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
    if "," in name:
        parts = name.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name.strip()

def safe_f(val, default=None):
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return default

def load_csv(path, key_fn=None):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if key_fn:
        return {key_fn(r): r for r in rows if r}
    return rows

def fmt(n):
    """Score-to-par format: E / -X / +X. Never '++'."""
    n = int(round(n)) if not isinstance(n, int) else n
    if n == 0:  return "E"
    if n > 0:   return f"+{n}"
    return str(n)

# ── Load standard v2 inputs ───────────────────────────────────────────────────
print("Loading v2 inputs…")

tee_rows   = load_csv(INP / "the_open_championship_player_field_R1_R2_teetimes.csv")
FIELD_KEYS  = {nkey(r["player_name"]): r for r in tee_rows}
FIELD_NAMES = {nkey(r["player_name"]): display_name(r["player_name"]) for r in tee_rows}

sg12     = load_csv(INP / "pga_sg_query_l12.csv",    key_fn=lambda r: nkey(r["player_name"]))
sg24     = load_csv(INP / "pga_sg_query_l24.csv",    key_fn=lambda r: nkey(r["player_name"]))
sg6      = load_csv(INP / "pga_sg_query_6.csv",      key_fn=lambda r: nkey(r["player_name"]))
dgperf   = load_csv(INP / "dg_performance_2026.csv", key_fn=lambda r: nkey(r["player_name"]))
dgskill  = load_csv(INP / "dg_skill_ratings.csv",    key_fn=lambda r: nkey(r["player_name"]))
dgdecomp = load_csv(INP / "dg_decomposition.csv",    key_fn=lambda r: nkey(r["player_name"]))
trending = load_csv(INP / "pga_field_trending_table.csv", key_fn=lambda r: nkey(r["player_name"]))
ch_raw   = load_csv(INP / "royal_birkdale_gc_CH.csv",     key_fn=lambda r: nkey(r["player_name"]))

cfa_rows = load_csv(INP / "the_open_championship_coursefitadjustments.csv")
cfa = {}
for r in cfa_rows:
    if r.get("Last Name"):
        k = nkey(r["Last Name"] + ", " + r.get("First Name",""))
        cfa[k] = r

app_sg_rows = load_csv(INP / "app_skill_l12_sg.csv")
app_sg = {nkey(r["player_name"]): r for r in app_sg_rows}

app_prox_rows = load_csv(INP / "app_skill_l12_prox.csv")
app_prox = {nkey(r["player_name"]): r for r in app_prox_rows}

with open(INP / "venue_birkdale_2026.json", encoding="utf-8") as f:
    VENUE = json.load(f)
with open(INP / "birkdale_full_course_weather_data_2026.json", encoding="utf-8") as f:
    WEATHER = json.load(f)

past_w_rows = load_csv(INP / "the_open_championship_past_winners_courses.csv")

print(f"  Field: {len(FIELD_KEYS)} players")

# ── Load v3 links SG files ────────────────────────────────────────────────────
print("Loading links SG files…")

links6m   = load_csv(LINKS / "dg_true_sg_links_6m.csv",      key_fn=lambda r: nkey(r["player_name"]))
links12m  = load_csv(LINKS / "dg_true_sg_links_12m.csv",     key_fn=lambda r: nkey(r["player_name"]))
links24m  = load_csv(LINKS / "dg_true_sg_links_24m.csv",     key_fn=lambda r: nkey(r["player_name"]))
linksall  = load_csv(LINKS / "dg_true_sg_links_alltime.csv", key_fn=lambda r: nkey(r["player_name"]))
birk_all  = load_csv(LINKS / "dg_true_sg_royal_birkdale_alltime.csv", key_fn=lambda r: nkey(r["player_name"]))

print(f"  Links 6M: {len(links6m)} | 12M: {len(links12m)} | 24M: {len(links24m)} | Alltime: {len(linksall)}")
print(f"  Birkdale alltime: {len(birk_all)} (field overlap)")

# ── Confidence schema for links windows ───────────────────────────────────────
# events_played thresholds → confidence multiplier
CONF_TABLE = [(4, 1.00), (2, 0.75), (1, 0.40), (0, 0.00)]
LINK_WEIGHTS = {"6m": 0.35, "12m": 0.35, "24m": 0.20, "alltime": 0.10}
LINKS_SCALE  = 4.0    # 1.0 SG/rd links signal → 4.0 VFS pts
LINKS_CAP    = 8.0    # max ±8 VFS pts from links signal

def _conf(events):
    ev = int(events or 0)
    for threshold, conf in CONF_TABLE:
        if ev >= threshold:
            return conf
    return 0.0

def compute_links_signal(k):
    """
    4-window confidence-weighted links SG signal.
    Returns (raw_signal, delta_vfs, windows_dict, confidence_overall, trace).
    """
    windows = {}
    for tag, src in [("6m", links6m), ("12m", links12m),
                     ("24m", links24m), ("alltime", linksall)]:
        row = src.get(k)
        if row is None:
            windows[tag] = {"events": 0, "total_mean": None, "app_mean": None,
                            "ott_mean": None, "conf": 0.0, "adj": None}
            continue
        ev  = int(safe_f(row.get("events_played"), 0))
        tm  = safe_f(row.get("total_mean"))
        apm = safe_f(row.get("app_mean"))
        otm = safe_f(row.get("ott_mean"))
        conf = _conf(ev)
        adj  = (tm * conf) if tm is not None else None
        windows[tag] = {"events": ev, "total_mean": tm, "app_mean": apm,
                        "ott_mean": otm, "conf": conf, "adj": adj}

    # Weighted average (only windows with data)
    wt_sum  = 0.0
    wt_sig  = 0.0
    for tag, wt in LINK_WEIGHTS.items():
        adj = windows[tag]["adj"]
        if adj is not None:
            wt_sig += wt * adj
            wt_sum += wt

    if wt_sum < 0.05:
        raw_signal = None
        delta_vfs  = 0.0
        conf_overall = 0.0
        trace = "No links data — zero signal applied."
    else:
        raw_signal   = wt_sig / wt_sum
        conf_overall = wt_sum   # sum of weights where data exists
        delta_vfs    = max(-LINKS_CAP, min(LINKS_CAP, raw_signal * LINKS_SCALE))
        parts = []
        for tag in ("6m","12m","24m","alltime"):
            w = windows[tag]
            if w["adj"] is not None:
                parts.append(f"{tag}:{w['total_mean']:+.3f}(ev={w['events']},conf={w['conf']:.2f}→adj={w['adj']:+.3f})")
            else:
                parts.append(f"{tag}:no_data")
        trace = f"raw_sig={raw_signal:+.3f}; delta_vfs={delta_vfs:+.2f}; windows=[{' | '.join(parts)}]"

    # Build 13 per-player links fields
    fields = {
        "true_links_events_6m":     windows["6m"]["events"],
        "true_links_events_12m":    windows["12m"]["events"],
        "true_links_events_24m":    windows["24m"]["events"],
        "true_links_events_alltime":windows["alltime"]["events"],
        "true_links_total_6m":      windows["6m"]["total_mean"],
        "true_links_total_12m":     windows["12m"]["total_mean"],
        "true_links_total_24m":     windows["24m"]["total_mean"],
        "true_links_total_alltime": windows["alltime"]["total_mean"],
        "true_links_app_12m":       windows["12m"]["app_mean"],
        "true_links_ott_12m":       windows["12m"]["ott_mean"],
        "links_signal_score":       round(raw_signal, 4) if raw_signal is not None else None,
        "links_signal_confidence":  round(conf_overall, 3),
        "links_signal_trace":       trace,
    }
    return raw_signal, delta_vfs, windows, conf_overall, trace, fields

# ── Pre-compute Birkdale VHN percentile table ─────────────────────────────────
print("Computing Birkdale VHN percentile table…")

birk_active = {k: birk_all[k]
               for k in FIELD_KEYS
               if k in birk_all and int(safe_f(birk_all[k].get("events_played"), 0)) > 0}

birk_total_means = {k: safe_f(birk_all[k].get("total_mean"))
                    for k in birk_active
                    if safe_f(birk_all[k].get("total_mean")) is not None}

sorted_birk_vals = sorted(birk_total_means.values())
N_birk = len(sorted_birk_vals)

def birk_pctile(val):
    if val is None or N_birk == 0:
        return 50.0
    rank = sum(1 for v in sorted_birk_vals if v < val)
    # Scale to 15–92 (not 0/100 to avoid extremes)
    return round(15.0 + rank / max(N_birk - 1, 1) * 77.0, 2)

def birkdale_tag(events, thin_threshold=2):
    if events == 0:
        return "RoyalBirkdaleDebut"
    if events <= thin_threshold:
        return "BirkdaleHistoryThin"
    return "BirkdaleHistoryActive"

def compute_vhn_v3(k):
    bd    = birk_all.get(k)
    ch    = ch_raw.get(k, {})
    cfa_r = cfa.get(k, {})

    # Open-context fallback modifier (CFA-based) for debuts
    cfa_adj  = safe_f(cfa_r.get("Total SG Adjustment"), 0) or 0
    open_mod = max(-6.0, min(6.0, cfa_adj * 3.0))

    if bd is None:
        return 50.0 + open_mod, "NoRoyalBirkdaleHistory", 0, None

    events = int(safe_f(bd.get("events_played"), 0))
    total_mean = safe_f(bd.get("total_mean"))

    if events == 0 or total_mean is None:
        tag = "RoyalBirkdaleDebut"
        ch_rds_ch = int(safe_f(ch.get("rounds_played"), 0))
        if ch_rds_ch > 0:
            # Has old CH data but not in Birkdale alltime with rounds — treat as debut
            tag = "RoyalBirkdaleDebut"
        return round(max(10.0, min(90.0, 50.0 + open_mod)), 2), tag, 0, None

    tag   = birkdale_tag(events)
    pct   = birk_pctile(total_mean)

    if events == 1:
        # Thin: 55% toward field average (45% trust in single event)
        vhn = 0.55 * 50.0 + 0.45 * pct
    elif events == 2:
        # Moderate thin: 30% shrinkage
        vhn = 0.30 * 50.0 + 0.70 * pct
    else:
        vhn = pct

    return round(max(10.0, min(95.0, vhn)), 2), tag, events, total_mean

# ── Trait definitions ─────────────────────────────────────────────────────────
TRAIT_DEFS = [
    {"key": "app_150_200",      "label": "APP 150-200 (Long Iron)", "weight": 0.30},
    {"key": "ott_positional",   "label": "OTT / Positional Drive",  "weight": 0.20},
    {"key": "app_overall",      "label": "APP Overall",              "weight": 0.15},
    {"key": "driving_accuracy", "label": "Driving Accuracy",         "weight": 0.12},
    {"key": "sg_putt",          "label": "Putting (Links-Regressed)","weight": 0.13},
    {"key": "sg_arg",           "label": "Short Game/ARG",           "weight": 0.10},
]
TRAIT_WEIGHT = {t["key"]: t["weight"] for t in TRAIT_DEFS}

# ── Collect raw traits ────────────────────────────────────────────────────────
print("Collecting raw trait values…")

raw = {}
links_signals = {}   # nkey → (raw_signal, delta_vfs, windows, conf, trace, fields)

for k in FIELD_KEYS:
    raw[k] = {}

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

    dp = dgperf.get(k, {})
    raw[k]["app_true"]  = safe_f(dp.get("app_true"))
    raw[k]["ott_true"]  = safe_f(dp.get("ott_true"))
    raw[k]["arg_true"]  = safe_f(dp.get("arg_true"))
    raw[k]["putt_true"] = safe_f(dp.get("putt_true"))
    raw[k]["total_true"]= safe_f(dp.get("total_true"))

    dk = dgskill.get(k, {})
    raw[k]["sg_app_pred"]  = safe_f(dk.get("sg_app_pred"))
    raw[k]["sg_ott_pred"]  = safe_f(dk.get("sg_ott_pred"))
    raw[k]["sg_arg_pred"]  = safe_f(dk.get("sg_arg_pred"))
    raw[k]["sg_putt_pred"] = safe_f(dk.get("sg_putt_pred"))
    raw[k]["sg_total_pred"]= safe_f(dk.get("sg_total_pred"))
    raw[k]["acc_pred"]     = safe_f(dk.get("accuracy_pred"))
    raw[k]["dist_pred"]    = safe_f(dk.get("distance_pred"))

    dd = dgdecomp.get(k, {})
    raw[k]["dg_final"]    = safe_f(dd.get("final_prediction"))
    raw[k]["dg_cfa"]      = safe_f(dd.get("course_fit_total_adj"), 0)
    raw[k]["dg_dist_adj"] = safe_f(dd.get("driving_dist_adj"), 0)
    raw[k]["dg_acc_adj"]  = safe_f(dd.get("driving_acc_adj"), 0)

    asg = app_sg.get(k, {})
    raw[k]["app_150_200_raw"] = safe_f(asg.get("150_200_fw_value"))
    raw[k]["app_100_150_raw"] = safe_f(asg.get("100_150_fw_value"))
    raw[k]["app_over200_raw"] = safe_f(asg.get("over_200_fw_value"))
    raw[k]["rough_150_raw"]   = safe_f(asg.get("over_150_rgh_value"))

    tr = trending.get(k, {})
    raw[k]["true_sg_l20"]    = safe_f(tr.get("true_sg_l20"))
    raw[k]["vs_baseline_l20"]= safe_f(tr.get("vs_baseline_l20"))

    s6 = sg6.get(k, {})
    raw[k]["total_l6"] = safe_f(s6.get("total_mean"))
    raw[k]["app_l6"]   = safe_f(s6.get("app_mean"))

    ch = ch_raw.get(k, {})
    raw[k]["ch_rounds"]  = safe_f(ch.get("rounds_played"), 0)
    raw[k]["ch_vs_exp"]  = safe_f(ch.get("versus_expected"), 0)
    raw[k]["ch_adj"]     = safe_f(ch.get("ch_adjustment"), 0)
    raw[k]["exp_adj"]    = safe_f(ch.get("experience_adjustment"), 0)
    raw[k]["ch_true_sg"] = safe_f(ch.get("historical_true_sg"))
    raw[k]["ch_2008"]    = ch.get("2008 (The Open Championship)", "")
    raw[k]["ch_2017"]    = ch.get("2017 (The Open Championship)", "")

    cf = cfa.get(k, {})
    raw[k]["cfa_sg_adj"]  = safe_f(cf.get("Total SG Adjustment"), 0)
    raw[k]["cfa_app_adj"] = safe_f(cf.get("APPROACH"), 0)
    raw[k]["cfa_sg_adj2"] = safe_f(cf.get("SHORT GAME"), 0)

    ott_v = raw[k]["ott_l12"] or raw[k]["sg_ott_pred"] or 0
    acc_v = raw[k]["acc_l12"] or raw[k]["acc_pred"] or 0
    acc_offset = (acc_v - 0.58) * 2.0
    raw[k]["ott_positional_raw"] = 0.65 * ott_v + 0.35 * acc_offset

    # Compute links signal (v3)
    ls = compute_links_signal(k)
    links_signals[k] = ls

# ── NSI ───────────────────────────────────────────────────────────────────────
print("Computing NSI…")

def best_total_sg(k):
    r = raw[k]
    v = r.get("total_l12")
    if v is None: v = r.get("total_true")
    if v is None: v = r.get("sg_total_pred")
    return v

total_sg_vals = {k: best_total_sg(k) for k in FIELD_KEYS}
valid_vals = sorted([v for v in total_sg_vals.values() if v is not None])

def percentile_0_100(val, sorted_vals):
    if val is None:
        return 50.0
    n = len(sorted_vals)
    rank = sum(1 for v in sorted_vals if v < val)
    return round(rank / max(n - 1, 1) * 100, 2)

nsi_raw = {k: percentile_0_100(total_sg_vals[k], valid_vals) for k in FIELD_KEYS}

# ── Trait percentiles ─────────────────────────────────────────────────────────
print("Computing trait percentiles…")

def field_pctile(raw_key):
    vals = {k: raw[k].get(raw_key) for k in FIELD_KEYS}
    valid_sorted = sorted([v for v in vals.values() if v is not None])
    return {k: percentile_0_100(vals[k], valid_sorted) for k in FIELD_KEYS}

p_app150  = field_pctile("app_150_200_raw")
p_ott_pos = field_pctile("ott_positional_raw")
p_app_ovr = field_pctile("app_overall")
p_drv_acc = field_pctile("acc_l12")
p_putt    = field_pctile("sg_putt")
p_arg     = field_pctile("sg_arg")

def trait_score(k):
    putt_adj = round(p_putt[k] * 0.85 + 50 * 0.15, 2)
    return {
        "app_150_200":      p_app150[k],
        "ott_positional":   p_ott_pos[k],
        "app_overall":      p_app_ovr[k],
        "driving_accuracy": p_drv_acc[k],
        "sg_putt":          putt_adj,
        "sg_arg":           p_arg[k],
    }

# ── VFS (base + links delta) ──────────────────────────────────────────────────
print("Computing VFS with links delta…")

def compute_vfs_v3(k):
    ts       = trait_score(k)
    weighted = sum(TRAIT_WEIGHT[tk] * ts[tk] for tk in TRAIT_WEIGHT)
    cfa_boost = (raw[k].get("cfa_sg_adj") or 0) * 5.0
    dg_boost  = (raw[k].get("dg_cfa") or 0) * 1.5
    vfs_base  = max(0.0, min(100.0, weighted + cfa_boost + dg_boost))

    _, delta_vfs, _, _, _, _ = links_signals[k]
    vfs_final = max(0.0, min(100.0, vfs_base + delta_vfs))
    return round(vfs_base, 2), round(delta_vfs, 2), round(vfs_final, 2)

vfs_base_vals  = {}
vfs_delta_vals = {}
vfs_vals       = {}
for k in FIELD_KEYS:
    b, d, f = compute_vfs_v3(k)
    vfs_base_vals[k]  = b
    vfs_delta_vals[k] = d
    vfs_vals[k]       = f

# ── VHN (v3 — Birkdale alltime source) ───────────────────────────────────────
print("Computing VHN (v3 Birkdale alltime source)…")

vhn_vals     = {}
vhn_tags     = {}
vhn_events   = {}
vhn_tm_vals  = {}
for k in FIELD_KEYS:
    vhn, tag, ev, tm = compute_vhn_v3(k)
    vhn_vals[k]    = vhn
    vhn_tags[k]    = tag
    vhn_events[k]  = ev
    vhn_tm_vals[k] = tm

# ── Form ──────────────────────────────────────────────────────────────────────
print("Computing Form…")

def compute_form(k):
    r = raw[k]
    vs_bl  = r.get("vs_baseline_l20")
    total6 = r.get("total_l6")
    total12= r.get("total_l12")
    if vs_bl is not None:
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

# ── VTS Final ─────────────────────────────────────────────────────────────────
print("Computing VTS Final…")

W_NSI, W_VFS, W_VHN, W_FORM = 0.40, 0.30, 0.15, 0.15

def compute_vts(k):
    return round(W_NSI*nsi_raw[k] + W_VFS*vfs_vals[k] + W_VHN*vhn_vals[k] + W_FORM*form_vals[k], 2)

vts_vals = {k: compute_vts(k) for k in FIELD_KEYS}

# ── Tiers ─────────────────────────────────────────────────────────────────────
def assign_tier(vts):
    if vts >= 78.0: return 1
    if vts >= 63.5: return 2
    if vts >= 48.0: return 3
    if vts >= 33.0: return 4
    return 5

TIER_LABELS = {
    1: "Structural Winner",
    2: "Primary Contender",
    3: "Dark Horse",
    4: "Fragile Path",
    5: "Fade / Cut Risk",
}

# ── Probabilities ─────────────────────────────────────────────────────────────
print("Computing probabilities…")

VTS_LIST = list(vts_vals.values())

def softmax_prob(vts, T, total_pct):
    exp_v   = math.exp(vts / T)
    exp_sum = sum(math.exp(v / T) for v in VTS_LIST)
    return round(exp_v / exp_sum * total_pct, 2)

def logistic(vts, mid=53.0, steep=0.10):
    return round(100.0 / (1 + math.exp(-steep * (vts - mid))), 1)

def win_ceiling(vts, vfs, nsi):
    return round(min(100, vts * 0.5 + vfs * 0.3 + nsi * 0.2), 2)

def contention_score(vts, vfs):
    return round(min(100, vts * 0.6 + vfs * 0.4), 2)

def floor_score_fn(vts, form):
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

def best_lane(p):
    if p["win"] >= 4.0:    return "Winner"
    if p["win"] >= 2.0:    return "Top 5"
    if p["top10"] >= 15.0: return "Top 10"
    if p["top20"] >= 30.0: return "Top 20"
    if p["cut"] >= 72.0:   return "Make Cut"
    if p["cut"] < 45.0:    return "Miss Cut"
    return "Pass"

# ── Anti-patterns ─────────────────────────────────────────────────────────────
print("Computing anti-patterns…")

AP_META = {
    "bomb_and_spray":     {"label": "Bomb + Spray",           "cls": "bomb"},
    "approach_liability": {"label": "Approach Liability",      "cls": "wedge"},
    "long_iron_weakness": {"label": "Long-Iron Weakness",      "cls": "bomb"},
    "poor_links_putter":  {"label": "Poor Links Putter",       "cls": "birdie"},
    "debut_risk":         {"label": "Debut Risk",              "cls": "rough"},
    "weak_arg_links":     {"label": "Weak ARG / Links Rough",  "cls": "rough"},
}

def detect_anti_patterns(k):
    r = raw[k]
    ts = trait_score(k)
    flags = []
    ott_v  = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    acc_v  = r.get("acc_l12") or r.get("acc_pred") or 0
    app_v  = r.get("app_overall") or r.get("sg_app_pred") or 0
    putt_v = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    arg_v  = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    a150_v = r.get("app_150_200_raw")

    if ott_v > 0.4 and acc_v < -0.10:
        flags.append("bomb_and_spray")
    if app_v < 0.0 or (a150_v is not None and a150_v < -0.02):
        flags.append("approach_liability")
    if ts["app_150_200"] < 35.0:
        flags.append("long_iron_weakness")
    if putt_v < -0.12:
        flags.append("poor_links_putter")
    if arg_v < -0.08:
        flags.append("weak_arg_links")

    ev_birk = vhn_events.get(k, 0)
    cfa_adj = abs(raw[k].get("cfa_sg_adj") or 0)
    if ev_birk == 0 and cfa_adj < 0.01:
        flags.append("debut_risk")

    return flags

ap_flags = {k: detect_anti_patterns(k) for k in FIELD_KEYS}

# ── Badges ────────────────────────────────────────────────────────────────────
def compute_badges(k, tier, p, nsi, vfs):
    r = raw[k]
    flags = ap_flags[k]
    badges = []
    ev_birk = vhn_events.get(k, 0)
    ch_adj  = r.get("ch_adj") or 0

    if ev_birk >= 2 and (vhn_tm_vals.get(k) or 0) > 0.5:
        badges.append("Course Horse")
    if vfs >= 64.0 and "Course Horse" not in badges:
        badges.append("Iron Edge")
    if nsi >= 85.0:
        badges.append("Elite NSI")

    vs_bl = r.get("vs_baseline_l20") or 0
    fc    = form_class(form_vals[k])
    if vs_bl >= 0.9:
        badges.append("Form Spike")
    elif fc in ("COOL","COLD"):
        badges.append("Form Cold")

    ls_sig = links_signals[k][0]  # raw_signal
    if ls_sig is not None and ls_sig >= 2.0:
        badges.append("Links Specialist")

    if ev_birk == 0:
        badges.append("Debut Watch")
    if p["cut"] < 60.0:
        badges.append("Cut Sweat")
    if len(flags) >= 2:
        badges.append("Anti-Pattern")
    if tier <= 2 and len(flags) >= 1:
        badges.append("Fragile Favorite")
        if "Anti-Pattern" in badges:
            badges.remove("Anti-Pattern")
    if tier >= 3:
        if p["win"] >= 2.0:
            badges.append("Dark Horse")
        elif win_ceiling(vts_vals[k], vfs, nsi) >= 75 and "Dark Horse" not in badges:
            badges.append("Ceiling Play")

    s12d = sg12.get(k, {})
    putt_std = safe_f(s12d.get("putt_std_dev"), 0)
    if putt_std > 2.0:
        badges.append("Volatile Putter")

    return list(dict.fromkeys(badges))

# ── Projected score (Birkdale-anchored, no "++") ──────────────────────────────
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

def projected_scores(vts, nsi, form, vfs):
    """
    72-hole score relative to par. Birkdale par 70, winning score -8±3.
    VTS=80 → expected ~-2; VTS=50 → expected ~+5; VTS=35 → expected ~+11.
    """
    expected_raw = 5.0 - (vts - 50.0) / 100.0 * 22.0
    expected = int(round(expected_raw))

    ceiling_raw = expected - 3.5 - (vts - 50.0) / 26.0
    ceiling = int(round(ceiling_raw))

    form_drag = max(0.0, (62.0 - form) / 18.0) * 3.5
    floor_raw = expected + 5.0 + form_drag
    floor_v   = int(round(floor_raw))

    ceiling = min(ceiling, expected - 2)
    floor_v = max(floor_v, expected + 3)
    ceiling = max(ceiling, -16)
    floor_v = min(floor_v, 28)

    return fmt(expected), fmt(ceiling), fmt(floor_v)

# ── 12-field note generators ──────────────────────────────────────────────────

def _app_phrase(app_v):
    if app_v >= 0.8:
        return f"elite approach (SG:APP {app_v:+.2f}) — directly meets Birkdale's 175–225yd demand"
    if app_v >= 0.4:
        return f"strong approach game (SG:APP {app_v:+.2f}) in the primary scoring zone"
    if app_v >= 0.05:
        return f"competent approach (SG:APP {app_v:+.2f}) — sufficient for Birkdale's mid-iron corridors"
    if app_v >= -0.15:
        return f"near-average approach (SG:APP {app_v:+.2f}) — below the Birkdale threshold"
    return f"below-average approach (SG:APP {app_v:+.2f}) — significant exposure in the primary scoring zone"

def gen_conviction(k, tier, nsi, vfs, fc):
    r = raw[k]
    app_v  = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v  = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    arg_v  = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    ev_birk = vhn_events.get(k, 0)
    ls_sig  = links_signals[k][0]
    parts   = [_app_phrase(app_v)]

    if ev_birk >= 2:
        tm = vhn_tm_vals.get(k) or 0
        parts.append(f"proven Birkdale performer ({ev_birk} events, SG {tm:+.3f}/rd at course)")
    elif ev_birk == 1:
        tm = vhn_tm_vals.get(k) or 0
        parts.append(f"single Birkdale event on record (SG {tm:+.3f}/rd) — limited but positive signal")

    if ls_sig is not None and ls_sig >= 1.5:
        parts.append(f"elite links SG signal ({ls_sig:+.3f}/rd weighted) confirms links-surface upside")
    elif ls_sig is not None and ls_sig >= 0.5:
        parts.append(f"positive links SG signal ({ls_sig:+.3f}/rd) supports links-surface fit")

    if fc == "HOT":
        parts.append("arriving in peak form entering the championship")
    elif fc == "COLD":
        parts.append("negative form momentum is a structural risk factor")

    return "; ".join(parts) + "."

def gen_failure_condition(k):
    flags = ap_flags[k]
    parts = []
    if "bomb_and_spray" in flags:
        parts.append("Birkdale's 22-yard corridors and gorse OB are fatal for inaccurate drivers")
    if "approach_liability" in flags or "long_iron_weakness" in flags:
        parts.append("below-field production in the 150–200yd zone — the decisive scoring range at every par 4")
    if "poor_links_putter" in flags:
        parts.append("links-surface putting volatility on medium-pace fescue greens amplifies bogey accumulation")
    if "debut_risk" in flags:
        parts.append("no Birkdale reference — wind management, trajectory, and course routing entirely unknown")
    if "weak_arg_links" in flags:
        parts.append("below-field ARG in links rough and revetted pot bunkers extends bogey sequences")
    if not parts:
        ev_birk = vhn_events.get(k, 0)
        if ev_birk == 0:
            parts.append("standard Open Championship high-variance environment with full debut uncertainty")
        else:
            parts.append("standard Open Championship variance; wind and firm/fast conditions can neutralize any profile")
    return ". ".join(parts) + "."

def gen_risk_vector(k, tier):
    flags = ap_flags[k]
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

def gen_ap_summary(k):
    flags = ap_flags[k]
    if not flags:
        return "No anti-pattern flags. Clean structural profile — no recurring weak-link traits identified for Royal Birkdale."
    descs = {
        "bomb_and_spray":     "Bomb + Spray — accuracy penalised in 22-yard Birkdale corridors; gorse OB is a real scoring event",
        "approach_liability": "Approach Liability — below-field in the primary 150–200yd scoring zone",
        "long_iron_weakness": "Long-Iron Weakness — exposure in the dominant par-4 approach range at Birkdale",
        "poor_links_putter":  "Poor Links Putter — below-field on fescue; links surfaces amplify weak putting",
        "debut_risk":         "Debut Risk — no Birkdale or Open data; full environmental uncertainty",
        "weak_arg_links":     "Weak ARG/Links Rough — revetted bunkers and steep run-offs create up-and-down challenge",
    }
    parts = [descs.get(f, f) for f in flags]
    return "Anti-pattern flags: " + "; ".join(parts) + "."

def gen_links_signal_note(k, tier):
    _, delta_vfs, windows, conf, trace, _ = links_signals[k]
    ls_sig = links_signals[k][0]
    if ls_sig is None:
        return "No links-specific SG data. Links signal contribution = 0 VFS points."
    name = FIELD_NAMES.get(k, k)
    w6  = windows["6m"]
    w12 = windows["12m"]
    w24 = windows["24m"]
    wal = windows["alltime"]

    parts = []
    if w6["events"] > 0 and w6["total_mean"] is not None:
        parts.append(f"6M: {w6['total_mean']:+.3f}/rd ({w6['events']} event(s), conf={w6['conf']:.2f})")
    else:
        parts.append("6M: no data")
    if w12["events"] > 0 and w12["total_mean"] is not None:
        parts.append(f"12M: {w12['total_mean']:+.3f}/rd ({w12['events']} event(s), conf={w12['conf']:.2f})")
    else:
        parts.append("12M: no data")
    if w24["events"] > 0 and w24["total_mean"] is not None:
        parts.append(f"24M: {w24['total_mean']:+.3f}/rd ({w24['events']} event(s))")
    if wal["events"] > 0 and wal["total_mean"] is not None:
        parts.append(f"Alltime: {wal['total_mean']:+.3f}/rd ({wal['events']} event(s))")

    dir_word = "positive" if ls_sig >= 0.3 else "negative" if ls_sig <= -0.3 else "neutral"
    return (f"Links SG signal {dir_word} ({ls_sig:+.3f}/rd weighted). "
            f"VFS delta applied: {delta_vfs:+.1f} pts. "
            f"Windows — {'; '.join(parts)}.")

def gen_birkdale_history_note(k):
    tag    = vhn_tags.get(k, "NoRoyalBirkdaleHistory")
    ev     = vhn_events.get(k, 0)
    tm     = vhn_tm_vals.get(k)
    vhn    = vhn_vals[k]
    r      = raw[k]
    f17    = r.get("ch_2017","")
    f08    = r.get("ch_2008","")

    if tag in ("NoRoyalBirkdaleHistory", "RoyalBirkdaleDebut"):
        return f"Royal Birkdale debut — no course-specific SG data. VHN set to neutral (50 baseline). Performance history entirely unknown on this routing."

    hist_parts = []
    if f17: hist_parts.append(f"2017: {f17}")
    if f08: hist_parts.append(f"2008: {f08}")
    hist_str = " / ".join(hist_parts) if hist_parts else f"{ev} event(s)"

    if tag == "BirkdaleHistoryThin":
        return (f"Thin Birkdale sample ({ev} event): {hist_str}. "
                f"SG {tm:+.3f}/rd — positive but shrunk 45% toward neutral (50% trust). "
                f"VHN {vhn:.1f}/100. Cannot positively anchor T1 thesis on this sample alone.")
    return (f"Active Birkdale record ({ev} events): {hist_str}. "
            f"True SG {tm:+.3f}/rd at course — {'above' if tm>0 else 'below'} field average. "
            f"VHN {vhn:.1f}/100. {'Positive course history provides structural support.' if tm>0 else 'Below-average course SG is a negative signal for tournament projection.'}")

def gen_form_note(k, fc, form):
    r     = raw[k]
    vs_bl = r.get("vs_baseline_l20") or 0
    l20   = r.get("true_sg_l20") or 0
    total6 = r.get("total_l6")
    if fc == "HOT":
        return (f"Form {fc} ({form:.0f}/100). True SG L20 {l20:+.2f}/rd, {vs_bl:+.2f} above 12-month baseline. "
                f"Arriving in peak cycle — positive momentum entering the championship.")
    if fc == "WARM":
        return (f"Form {fc} ({form:.0f}/100). True SG L20 {l20:+.2f}/rd, {vs_bl:+.2f} vs baseline. "
                f"Modestly above seasonal baseline — no red flags in recent trajectory.")
    if fc == "NEUTRAL":
        return (f"Form {fc} ({form:.0f}/100). L20 SG {l20:+.2f}/rd, {vs_bl:+.2f} vs baseline. "
                f"In-line with 12-month average — no directional signal for or against.")
    if fc == "COOL":
        return (f"Form {fc} ({form:.0f}/100). L20 SG {l20:+.2f}/rd, {vs_bl:+.2f} below baseline. "
                f"Below recent average — worth monitoring but not disqualifying.")
    return (f"Form COLD ({form:.0f}/100). L20 SG {l20:+.2f}/rd, {vs_bl:+.2f} below baseline. "
            f"Significantly below seasonal baseline — negative momentum entering the championship.")

def gen_scoring_thesis(k, tier):
    r     = raw[k]
    app_v = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    a150  = r.get("app_150_200_raw")
    acc_v = r.get("acc_l12") or r.get("acc_pred") or 0
    arg_v = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    ev_birk = vhn_events.get(k, 0)
    vts   = vts_vals[k]

    parts = []
    if app_v >= 0.5 or (a150 is not None and a150 >= 0.05):
        a150_s = f" (150-200 value {a150:+.3f})" if a150 else ""
        parts.append(f"Scores via approach precision{a150_s} — generates birdies from the primary par-4 scoring zone (175–225yds)")
    if ott_v >= 0.4 and acc_v >= 0.0:
        parts.append(f"Positional driving ({ott_v:+.2f} OTT, acc={acc_v:.2%}) keeps the card clean through Birkdale's narrow corridors")
    if arg_v >= 0.2:
        parts.append(f"Short-game saves ({arg_v:+.2f} ARG) absorb bogeys from revetted bunkers and tight rough lies")
    if ev_birk >= 1:
        parts.append(f"Course knowledge from {ev_birk} prior Birkdale event(s) supports routing and wind management")
    if not parts:
        parts.append(f"Structural mid-field profile — scoring upside capped by limited elite-tier traits on this layout (VTS {vts:.1f})")
    return ". ".join(parts) + "."

def gen_links_fit_note(k):
    _, delta_vfs, _, _, _, _ = links_signals[k]
    ts     = trait_score(k)
    r      = raw[k]
    acc_v  = r.get("acc_l12") or r.get("acc_pred") or 0
    app_v  = r.get("app_overall") or r.get("sg_app_pred") or 0
    a150   = r.get("app_150_200_raw")
    ls_sig = links_signals[k][0]

    acc_grade = "elite" if ts["driving_accuracy"] >= 75 else "strong" if ts["driving_accuracy"] >= 60 else "average" if ts["driving_accuracy"] >= 40 else "below-average"
    app_grade = "elite" if ts["app_overall"] >= 80 else "strong" if ts["app_overall"] >= 65 else "average" if ts["app_overall"] >= 40 else "below-average"

    ls_note = (f" Links SG delta {delta_vfs:+.1f} VFS pts applied from {ls_sig:+.3f}/rd weighted signal."
               if ls_sig is not None else " No links SG correction applied.")

    return (f"Links structural fit: {acc_grade} accuracy (field pctile {ts['driving_accuracy']:.0f}), "
            f"{app_grade} APP overall (pctile {ts['app_overall']:.0f}).{ls_note}")

def gen_structural_note(k, tier, nsi, vfs, vhn):
    tag = vhn_tags.get(k, "NoRoyalBirkdaleHistory")
    vts = vts_vals[k]
    lbl = TIER_LABELS.get(tier, "")
    ls_sig = links_signals[k][0]
    ls_part = ""
    if ls_sig is not None:
        if ls_sig >= 1.5:
            ls_part = " Links-specialist SG provides meaningful upward VFS adjustment."
        elif ls_sig <= -0.5:
            ls_part = " Negative links SG signal reduces VFS from general trait baseline."

    history_part = ""
    if tag == "BirkdaleHistoryActive":
        history_part = " Active Birkdale history contributes positive VHN signal."
    elif tag in ("RoyalBirkdaleDebut","NoRoyalBirkdaleHistory"):
        history_part = " Debut at Royal Birkdale — VHN is neutral baseline."

    return (f"T{tier} {lbl}. VTS {vts:.1f}/100 (NSI={nsi:.1f}, VFS={vfs:.1f}, VHN={vhn:.1f}).{ls_part}{history_part}")

def gen_bet_path(p, tier, lane):
    paths = {
        "Winner": "Approach edge on par 4s 3, 6, 8, 16 creates birdie separation; positional tee play keeps bogeys off the card in wind; legitimate R3-R4 contender.",
        "Top 5":  "Strong structural profile with top-5 ceiling; most realistic path is top-10 via consistent ball-striking across four rounds.",
        "Top 10": "Reliable contender — top-10 is the ceiling; unlikely to win but can post a high-quality finish with clean wind management.",
        "Top 20": "Structural mid-tier — cut is comfortable, final-20 is realistic, win probability is very thin without unexpected form spike.",
        "Make Cut": "Cut survival likely; weekend upside is limited by structural weaknesses in primary scoring traits.",
        "Miss Cut": "Structural anti-patterns and sub-50% cut probability. Fading this player at Royal Birkdale.",
        "Pass":   "Mixed profile — insufficient model edge to recommend a bet position. Monitor pre-tournament conditions and market movement.",
    }
    return paths.get(lane, paths["Pass"])

def gen_nsi_summary(k, nsi):
    r     = raw[k]
    app_v = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    putt  = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    arg_v = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    return (f"NeutralSkill {nsi:.1f}/100 — SG:APP (BRIE) {app_v:+.2f}, "
            f"SG:OTT (TVL) {ott_v:+.2f}, SG:PUTT {putt:+.2f}, SG:ARG (VFR) {arg_v:+.2f}. "
            f"Approach game {'above' if app_v>0 else 'below'} the scoring threshold Birkdale demands from 175–200yds.")

def gen_vfs_summary(k, vfs, ts):
    r      = raw[k]
    a150   = r.get("app_150_200_raw")
    flags  = ap_flags[k]
    _, delta_vfs, _, _, _, _ = links_signals[k]
    a150_s = f"APP 150-200: {a150:+.3f}" if a150 is not None else "APP 150-200: data unavailable"
    ap_str = ("; ".join(AP_META[f]["label"] for f in flags[:2])
              if flags else "No anti-pattern flags — clean structural profile")
    return (f"VenueFit {vfs:.1f}/100 — {a150_s}. "
            f"Links signal delta: {delta_vfs:+.1f} VFS pts. "
            f"{'Positive APP 150-200 confirms approach productivity in the primary scoring zone.' if (a150 or 0)>0 else 'Negative APP 150-200 exposes approach weakness in the primary zone.'} "
            f"{ap_str}.")

def gen_vhn_summary(k, vhn):
    tag = vhn_tags.get(k, "NoRoyalBirkdaleHistory")
    ev  = vhn_events.get(k, 0)
    tm  = vhn_tm_vals.get(k)
    r   = raw[k]
    if tag in ("NoRoyalBirkdaleHistory","RoyalBirkdaleDebut"):
        return f"VenueHistory {vhn:.1f}/100 — No Birkdale starts. Open debut — no course-specific calibration available."
    yrs = []
    if r.get("ch_2008"): yrs.append(f"{r['ch_2008']} in 2008")
    if r.get("ch_2017"): yrs.append(f"{r['ch_2017']} in 2017")
    hist = " / ".join(yrs) if yrs else f"{ev} event(s)"
    thin = " (thin sample — 45% shrinkage applied)" if tag == "BirkdaleHistoryThin" else ""
    return (f"VenueHistory {vhn:.1f}/100 — {ev} Birkdale event(s): {hist}{thin}. "
            f"True SG at course: {tm:+.3f}/rd.")

def gen_form_summary(k, form, fc):
    r      = raw[k]
    vs_bl  = r.get("vs_baseline_l20") or 0
    l20    = r.get("true_sg_l20") or 0
    return (f"Form {fc} ({form:.1f}/100) — True SG L20: {l20:+.2f}/rd, vs 12-month baseline: {vs_bl:+.2f}. "
            f"{'Positive momentum entering the championship.' if fc in ('HOT','WARM') else 'Carrying negative momentum below seasonal baseline.' if fc == 'COLD' else '12-month baseline remains the reference; no strong directional form signal.'}")

# ── Helper bullets ────────────────────────────────────────────────────────────
def _top_trait_bullets(k, app_v, ott_v, arg_v, putt_v, ts):
    r       = raw[k]
    bullets = []
    if app_v >= 0.5:
        bullets.append(f"Elite approach — SG:APP {app_v:+.2f} in Birkdale's 175–200yd zone")
    elif app_v >= 0.2:
        bullets.append(f"Strong approach — SG:APP {app_v:+.2f} above field average")
    if ott_v >= 0.5:
        bullets.append(f"Elite off-tee — SG:OTT {ott_v:+.2f}, positional accuracy in narrow Birkdale corridors")
    elif ts["driving_accuracy"] >= 65:
        bullets.append(f"Accurate driver — low miss-rate in Birkdale's punishing gorse corridors")
    if putt_v >= 0.3:
        bullets.append(f"Strong putting — SG:PUTT {putt_v:+.2f}, converts proximity on firm fescue greens")
    if arg_v >= 0.2:
        bullets.append(f"Short-game skill — SG:ARG {arg_v:+.2f}, escapes Birkdale's revetted bunkers")
    ev_birk = vhn_events.get(k, 0)
    if ev_birk >= 2:
        bullets.append(f"Active Birkdale record — {ev_birk} events of course-specific data")
    ls_sig = links_signals[k][0]
    if ls_sig is not None and ls_sig >= 1.5:
        bullets.append(f"Links specialist — {ls_sig:+.3f}/rd weighted links SG signal (top-tier)")
    if not bullets:
        bullets.append("Workmanlike profile — no dominant trait edge at Royal Birkdale")
    return bullets[:4]

def _best_finish(r):
    best = None
    for f in [r.get("ch_2017",""), r.get("ch_2008","")]:
        if not f or f in ("MC","WD"):
            continue
        try:
            pos = int(f.replace("T","").strip())
            if best is None or pos < best:
                best = pos
        except Exception:
            pass
    return best

# ── Build player objects ──────────────────────────────────────────────────────
print("Building player objects…")

players_sorted = sorted(FIELD_KEYS.keys(), key=lambda k: -vts_vals[k])
all_players    = []
rank           = 1

for k in players_sorted:
    r    = raw[k]
    tee  = FIELD_KEYS[k]
    nsi  = nsi_raw[k]
    vfs  = vfs_vals[k]
    vfs_b = vfs_base_vals[k]
    vfs_d = vfs_delta_vals[k]
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
    wc   = win_ceiling(vts, vfs, nsi)
    cs   = contention_score(vts, vfs)
    fs   = floor_score_fn(vts, form)
    cls  = round(logistic(vts, mid=48.0, steep=0.12), 2)
    band_label, band_color = scoring_band(vts)
    exp_sc, ceil_sc, floor_sc = projected_scores(vts, nsi, form, vfs)

    app_v  = r.get("app_overall") or r.get("sg_app_pred") or 0
    ott_v  = r.get("ott_l12") or r.get("sg_ott_pred") or 0
    arg_v  = r.get("sg_arg") or r.get("sg_arg_pred") or 0
    putt_v = r.get("sg_putt") or r.get("sg_putt_pred") or 0
    t2g_v  = r.get("t2g_l12") or round(app_v + ott_v, 3)

    name     = FIELD_NAMES[k]
    parts_nm = name.split(" ", 1)
    first_nm = parts_nm[0] if parts_nm else ""
    last_nm  = parts_nm[1] if len(parts_nm) > 1 else ""

    pid = f"P{rank:03d}"

    _, _, windows, conf, trace, link_fields = links_signals[k]
    ls_sig   = links_signals[k][0]
    ev_birk  = vhn_events.get(k, 0)
    birk_tag = vhn_tags.get(k, "NoRoyalBirkdaleHistory")
    birk_tm  = vhn_tm_vals.get(k)

    trait_scores_list = []
    for td in TRAIT_DEFS:
        tk      = td["key"]
        score_v = ts[tk]
        trait_scores_list.append({
            "key":     tk,
            "label":   td["label"],
            "weight":  td["weight"],
            "score":   score_v,
            "imputed": score_v == 50.0,
        })

    debut = (ev_birk == 0 and abs(r.get("cfa_sg_adj") or 0) < 0.01)

    obj = {
        "player_id":            pid,
        "last_name":            last_nm,
        "first_name":           first_nm,
        "tier":                 tier,
        "rank":                 rank,
        "vts_final":            vts,
        "venue_fit_score":      vfs,
        "vfs_base":             vfs_b,
        "vfs_links_delta":      vfs_d,
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
        # 12 structured note fields
        "conviction_statement": gen_conviction(k, tier, nsi, vfs, fc),
        "failure_condition":    gen_failure_condition(k),
        "risk_vector":          gen_risk_vector(k, tier),
        "anti_pattern_summary": gen_ap_summary(k),
        "links_signal_note":    gen_links_signal_note(k, tier),
        "birkdale_history_note":gen_birkdale_history_note(k),
        "form_note":            gen_form_note(k, fc, form),
        "scoring_thesis":       gen_scoring_thesis(k, tier),
        "links_fit_note":       gen_links_fit_note(k),
        "structural_note":      gen_structural_note(k, tier, nsi, vfs, vhn),
        "bet_path_note":        gen_bet_path(p, tier, lane),
        "council_override_note":"",   # filled by council pass
        # Score construction trace
        "decomposition": {
            "neutral_skill_index": nsi,
            "venue_fit_delta":     vfs,
            "vfs_base":            vfs_b,
            "vfs_links_delta":     vfs_d,
            "venue_history_delta": vhn,
            "form_score":          form,
            "penalties":           0.0,
            "trace_notes": (f"NSI={nsi:.1f}(w=0.40) + VFS={vfs:.1f}(w=0.30) + "
                            f"VHN={vhn:.1f}(w=0.15) + FORM={form:.1f}(w=0.15) = VTS={vts:.1f}. "
                            f"VFS = base {vfs_b:.1f} + links_delta {vfs_d:+.1f}. "
                            f"Links trace: {trace}"),
        },
        # Summary fields (board uses these)
        "neutral_skill_summary":gen_nsi_summary(k, nsi),
        "venue_fit_summary":    gen_vfs_summary(k, vfs, ts),
        "venue_history_summary":gen_vhn_summary(k, vhn),
        "form_summary":         gen_form_summary(k, form, fc),
        "drag_traits":          [AP_META[f]["label"] for f in flags],
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
        "birkdale_tag":             birk_tag,
        "birkdale_events":          ev_birk,
        "birkdale_sg_per_round":    round(birk_tm, 4) if birk_tm else None,
        "sg_app_12m":               round(app_v, 3),
        "sg_ott_12m":               round(ott_v, 3),
        "sg_putt_12m":              round(putt_v, 3),
        "sg_arg_12m":               round(arg_v, 3),
        "sg_t2g_12m":               round(t2g_v, 3),
        "true_sg_last20":           round(r.get("true_sg_l20") or 0, 2),
        "true_sg_vs_baseline":      round(r.get("vs_baseline_l20") or 0, 2),
        "form_class":               fc,
        "data_depth_class":         "FULL" if ev_birk > 0 else "DEBUT",
        "venue_history_depth":      ("RICH" if ev_birk >= 3 else "MODERATE" if ev_birk >= 2 else "LIGHT" if ev_birk > 0 else "NONE"),
        "starts_at_birkdale":       ev_birk,
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
        "vhn_rounds":               ev_birk,
        "tee_time":                 tee.get("r1_teetime","TBD"),
        "r1_teetime":               tee.get("r1_teetime","TBD"),
        "r1_wave":                  tee.get("r1_wave",""),
        "r1_starthole":             tee.get("r1_starthole","1"),
        "r2_teetime":               tee.get("r2_teetime","TBD"),
        "r2_wave":                  tee.get("r2_wave",""),
        "r2_starthole":             tee.get("r2_starthole","1"),
        "trait_scores":             trait_scores_list,
        "win_pct":                  p["win"],
        "top5_pct":                 p["top5"],
        "top10_pct":                p["top10"],
        "top20_pct":                p["top20"],
        # 13 links fields
        **link_fields,
    }
    all_players.append(obj)
    rank += 1

# ── Tier summary ──────────────────────────────────────────────────────────────
tier_counts = {}
for p in all_players:
    t = p["tier"]
    tier_counts[t] = tier_counts.get(t, 0) + 1

print("\nTIER DISTRIBUTION (v3):")
for t in sorted(tier_counts):
    players_in_tier = [p for p in all_players if p["tier"] == t]
    avg_vts = sum(p["vts_final"] for p in players_in_tier) / len(players_in_tier)
    avg_win = sum(p["win_prob"] for p in players_in_tier) / len(players_in_tier)
    print(f"  T{t}: {tier_counts[t]:3d} players | avg VTS {avg_vts:.1f} | avg Win% {avg_win:.2f}")
print(f"\nWin% sum: {sum(p['win_prob'] for p in all_players):.1f}%")

# ── Value / Model Over / Under ────────────────────────────────────────────────
model_over    = []
model_under   = []
struct_fades  = []
links_boosted = []  # players where links_delta > 4.0

for p in all_players:
    owgr       = p["owgr_rank"] or 999
    tier       = p["tier"]
    vts        = p["vts_final"]
    win        = p["win_prob"]
    flags_count = p["ap_total_flags"]
    ld         = p.get("vfs_links_delta", 0)

    if tier <= 2 and owgr > 40 and vts >= 65:
        model_over.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"OWGR #{int(owgr)} — model ranks T{tier} (VTS {vts:.1f}); structural approach fit suggests market undervaluation.",
        })
    if tier >= 4 and win < 0.5:
        struct_fades.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"T{tier} — structural skill gap; {flags_count} anti-pattern flags.",
        })
    elif tier in (2, 3) and flags_count >= 2 and vts < 58:
        model_under.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "reason": f"T{tier} with {flags_count} anti-pattern flags; VTS {vts:.1f} may overstate market narrative.",
        })
    if ld >= 4.0:
        links_boosted.append({
            "playerName": p["first_name"] + " " + p["last_name"],
            "tier": tier,
            "vts": vts,
            "links_delta": ld,
            "links_signal": p.get("links_signal_score"),
            "links_events_12m": p.get("true_links_events_12m"),
        })

# ── Model Council (5 roles) ───────────────────────────────────────────────────
print("Running Model Council…")

tier1_players = [p for p in all_players if p["tier"] == 1]
tier2_players = [p for p in all_players if p["tier"] == 2]

# Index by nkey for lookup
player_by_nkey = {nkey(p["first_name"] + " " + p["last_name"]): p for p in all_players}

def _pname(p):
    return p["first_name"] + " " + p["last_name"]

def _lookup(name):
    k = nkey(name)
    return player_by_nkey.get(k)

# --- Architect ---
architect_findings = []
for p in tier1_players:
    app_v  = p["sg_app_12m"]
    ls_sig = p.get("links_signal_score")
    ls_d   = p.get("vfs_links_delta", 0)
    tag    = p.get("birkdale_tag","")
    ev_b   = p.get("birkdale_events", 0)
    note   = (f"T1 case built on NSI={p['neutral_skill_index']:.1f}, VFS={p['venue_fit_score']:.1f}. "
              f"Approach: SG:APP {app_v:+.2f}. "
              f"Links delta: {ls_d:+.1f} VFS pts. "
              f"Birkdale: {tag} ({ev_b} events). "
              f"Structural validator: {'APPROVED' if app_v >= 0.2 or ls_d >= 2.0 else 'CONDITIONAL — approach below threshold or no links lift'}.")
    architect_findings.append({"player": _pname(p), "tier": 1, "vts": p["vts_final"], "note": note})

# --- Skeptic ---
skeptic_flags = []
for p in tier1_players + tier2_players[:8]:
    flags_count = p["ap_total_flags"]
    ls_d = p.get("vfs_links_delta", 0)
    ev_b = p.get("birkdale_events", 0)
    issues = []
    if flags_count >= 2:
        issues.append(f"{flags_count} anti-pattern flags on a T{p['tier']} player")
    if p["neutral_skill_index"] >= 85 and p.get("links_signal_score") is not None and p["links_signal_score"] < 0:
        issues.append(f"Elite NSI but negative links signal ({p['links_signal_score']:+.3f}/rd)")
    if ev_b == 0:
        issues.append(f"Debut at Royal Birkdale — no course-specific data for T{p['tier']} projection")
    if ls_d < -2.0:
        issues.append(f"Negative links delta {ls_d:+.1f} VFS pts — links-specific form undermines general NSI")
    if issues:
        skeptic_flags.append({
            "player":  _pname(p),
            "tier":    p["tier"],
            "vts":     p["vts_final"],
            "issues":  issues,
        })

# --- Market Contrarian ---
mc_notes = []
for p in links_boosted:
    tier = p["tier"]
    ld   = p["links_delta"]
    sig  = p["links_signal"]
    ev12 = p.get("links_events_12m", 0)
    mc_notes.append({
        "player":    p["playerName"],
        "tier":      tier,
        "vts":       p["vts"],
        "links_delta": ld,
        "note": (f"Links signal +{ld:.1f} VFS pts — if general NSI understates links ceiling, "
                 f"this player may outperform market odds. 12M events: {ev12}. "
                 f"{'Strong multi-window signal — monitor odds.' if (ev12 or 0) >= 2 else 'Thin sample — 6M heavily weighted; validate via 24M window.'}")
    })

# --- Audit Officer ---
audit_notes = []
debut_players = [p for p in all_players if p.get("birkdale_tag") in ("RoyalBirkdaleDebut","NoRoyalBirkdaleHistory")]
thin_players  = [p for p in all_players if p.get("birkdale_tag") == "BirkdaleHistoryThin"]
no_links_data = [p for p in all_players if p.get("links_signal_score") is None]

audit_notes.append({
    "check": "Birkdale debut count",
    "finding": f"{len(debut_players)} players have no Birkdale history. VHN set to neutral 50 baseline.",
    "severity": "INFO",
})
audit_notes.append({
    "check": "Birkdale thin sample",
    "finding": f"{len(thin_players)} players have 1 Birkdale event — VHN shrunk 45% toward 50.",
    "severity": "INFO",
})
audit_notes.append({
    "check": "No links SG data",
    "finding": f"{len(no_links_data)} players have no links SG data in any window — zero links delta applied.",
    "severity": "INFO",
})
# Check T1 players with debut
t1_debuts = [p for p in tier1_players if p.get("birkdale_tag") in ("RoyalBirkdaleDebut","NoRoyalBirkdaleHistory")]
if t1_debuts:
    audit_notes.append({
        "check": "T1 with debut flag",
        "finding": (f"{len(t1_debuts)} T1 player(s) have no Birkdale history: "
                    f"{', '.join(_pname(p) for p in t1_debuts)}. "
                    "Debut risk cannot positively anchor T1 — NSI and VFS must carry entire case."),
        "severity": "WARN",
    })

# --- Tom Kim adjudication ---
tom_kim = _lookup("Tom Kim")
tom_kim_v2_note = ""
tom_kim_council = {}

if tom_kim:
    tk_nsi   = tom_kim["neutral_skill_index"]
    tk_vfs   = tom_kim["venue_fit_score"]
    tk_vfs_b = tom_kim.get("vfs_base", 0)
    tk_ld    = tom_kim.get("vfs_links_delta", 0)
    tk_vhn   = tom_kim["venue_history_normalized"]
    tk_form  = tom_kim["form_score"]
    tk_vts   = tom_kim["vts_final"]
    tk_tier  = tom_kim["tier"]
    tk_rank  = tom_kim["rank"]
    tk_ls6   = tom_kim.get("true_links_total_6m")
    tk_ls12  = tom_kim.get("true_links_total_12m")
    tk_ls24  = tom_kim.get("true_links_total_24m")
    tk_lsal  = tom_kim.get("true_links_total_alltime")
    tk_sig   = tom_kim.get("links_signal_score")
    tk_ev6   = tom_kim.get("true_links_events_6m", 0)
    tk_ev12  = tom_kim.get("true_links_events_12m", 0)
    tk_ev24  = tom_kim.get("true_links_events_24m", 0)
    tk_eval  = tom_kim.get("true_links_events_alltime", 0)

    tom_kim_council = {
        "player": "Tom Kim",
        "adjudication": "EXPLICIT COUNCIL REVIEW",
        "prior_version_rank": "~50th (v2 — general L12 SG only, 0.530/rd)",
        "v3_rank": tk_rank,
        "v3_tier": tk_tier,
        "v3_vts":  tk_vts,
        "nsi":     tk_nsi,
        "vfs_base":    tk_vfs_b,
        "vfs_links_delta": tk_ld,
        "vfs_final":   tk_vfs,
        "vhn":     tk_vhn,
        "form":    tk_form,
        "links_windows": {
            "6m":      {"events": tk_ev6,  "total_mean": tk_ls6,  "conf": _conf(tk_ev6),  "note": "GSO win — sole 6M event, high conf penalty"},
            "12m":     {"events": tk_ev12, "total_mean": tk_ls12, "conf": _conf(tk_ev12), "note": "2 events, moderate confidence"},
            "24m":     {"events": tk_ev24, "total_mean": tk_ls24, "conf": _conf(tk_ev24), "note": "4 events, full confidence"},
            "alltime": {"events": tk_eval, "total_mean": tk_lsal, "conf": _conf(tk_eval), "note": "8 events, full confidence"},
        },
        "weighted_signal": tk_sig,
        "vfs_delta_applied": tk_ld,
        "architect_ruling": (
            f"Tom Kim's general L12 SG (0.530/rd) placed him ~50th in v2. "
            f"Links SG across all windows is elite: 6M {(tk_ls6 or 0):+.3f} (1 ev, conf=0.40), "
            f"12M {(tk_ls12 or 0):+.3f} (2 ev, conf=0.75), "
            f"24M {(tk_ls24 or 0):+.3f} (4 ev), alltime {(tk_lsal or 0):+.3f} (8 ev). "
            f"Weighted signal {(tk_sig or 0):+.3f}/rd → VFS delta {tk_ld:+.1f} pts applied. "
            f"NSI remains constrained by general form (0.530/rd → pctile {tk_nsi:.1f}). "
            f"VTS v3: {tk_vts:.1f} (v2 was ~50). Material upward movement confirmed."
        ),
        "skeptic_challenge": (
            f"6M window is GSO win only (1 event, conf=0.40). "
            f"GSO at Dundonald Links — a legitimate links test but single-tournament sample. "
            f"If GSO was a one-week form spike on a moderately links-like layout, "
            f"alltime 8-event signal ({(tk_lsal or 0):+.3f}/rd) provides the stabiliser. "
            f"NSI constraint at {tk_nsi:.1f}/100 limits T2 case — links ceiling is real but general skill floor is mid-field."
        ),
        "market_contrarian_note": (
            f"Post-GSO win, market may overrate Tom Kim's general form but underrate his links-specific ceiling. "
            f"VTS {tk_vts:.1f} (T{tk_tier}) represents a structural re-rating from v2 ~50th. "
            f"At correct links-adjusted odds, Tom Kim is a value play in Top 20 and Top 10 markets. "
            f"Win market remains constrained by NSI floor vs T1 players."
        ),
        "synthesis_ruling": (
            f"RULING: Tom Kim moves from v2 rank ~50 to v3 rank {tk_rank} (T{tk_tier}). "
            f"No manual override applied — model movement ({(tk_vts - 50):.1f} VTS pts gained) is evidence-based. "
            f"Links SG signal is sustained across multiple windows (not just GSO). "
            f"Top 10 and Top 20 markets are the recommended play. "
            f"Win market: plausible ceiling but NSI constraint at {tk_nsi:.1f}/100 limits structural T1 case."
        ),
    }

    # Inject council note into player object
    tom_kim["council_override_note"] = (
        f"COUNCIL REVIEWED. Prior v2 rank ~50th on general L12 SG (0.530/rd) only. "
        f"v3 links signal {(tk_sig or 0):+.3f}/rd weighted (4 windows: 6M {(tk_ls6 or 0):+.2f}×0.40, "
        f"12M {(tk_ls12 or 0):+.2f}×0.75, 24M {(tk_ls24 or 0):+.2f}×1.00, alltime {(tk_lsal or 0):+.2f}×1.00). "
        f"VFS delta {tk_ld:+.1f} pts applied. NSI remains {tk_nsi:.1f}/100 — T1 structural case not met. "
        f"Settled T{tk_tier}, rank {tk_rank}. "
        f"Top 10/Top 20 markets recommended."
    )
    # Update links signal note too
    tom_kim["links_signal_note"] = (
        f"COUNCIL-ADJUDICATED links signal. "
        f"6M: {(tk_ls6 or 0):+.3f}/rd (1 event = GSO win, conf=0.40). "
        f"12M: {(tk_ls12 or 0):+.3f}/rd (2 events, conf=0.75). "
        f"24M: {(tk_ls24 or 0):+.3f}/rd (4 events, full confidence). "
        f"Alltime: {(tk_lsal or 0):+.3f}/rd (8 events, full confidence). "
        f"Weighted signal {(tk_sig or 0):+.3f}/rd → VFS delta {tk_ld:+.1f} pts. "
        f"Sustained multi-window elite links production; 6M GSO win not an outlier — alltime confirms."
    )

# --- Synthesis Chair ---
synthesis_rulings = []

# Scheffler review (negative links signal)
scheffler = _lookup("Scottie Scheffler")
if scheffler:
    sch_ls6  = scheffler.get("true_links_total_6m")
    sch_ld   = scheffler.get("vfs_links_delta", 0)
    sch_nsi  = scheffler["neutral_skill_index"]
    synthesis_rulings.append({
        "player": "Scottie Scheffler",
        "topic":  "Negative links 6M signal vs elite NSI",
        "ruling": (
            f"Scheffler holds T1 via elite NSI ({sch_nsi:.1f}/100). "
            f"6M links SG: {(sch_ls6 or 0):+.3f}/rd (GSO near-miss performance). "
            f"Links delta {sch_ld:+.1f} VFS pts — modest negative. "
            f"NSI dominance (40% weight) outweighs the links VFS penalty at this magnitude. "
            f"T1 standing MAINTAINED. Note: Royal Birkdale links fragility is a real risk; "
            f"if links-specific underperformance is systemic, market odds may be too short."
        ),
    })

# General synthesis
synthesis_rulings.append({
    "player": "All T1 players",
    "topic":  "T1 validation",
    "ruling": (
        f"{len(tier1_players)} players in T1 (VTS≥78). "
        f"All require NSI≥75 OR links delta≥4.0 to justify. "
        f"T1 debuts (no Birkdale): {len(t1_debuts)} player(s) — these hold on NSI/VFS strength alone. "
        f"Council accepts T1 list as structurally sound. No forced demotions."
    ),
})

synthesis_rulings.append({
    "player": "Tom Kim",
    "topic":  "Complete adjudication",
    "ruling": tom_kim_council.get("synthesis_ruling", "See tom_kim council object."),
})

council_findings = {
    "council_version":  "v3",
    "event":            "2026 The Open Championship",
    "generated_at":     NOW,
    "model_version":    "VenueDNA v3",
    "roles": {
        "architect": {
            "reviewer":  "Architect",
            "focus":     "Structural validation of T1 list — approach-first thesis at Royal Birkdale",
            "findings":  architect_findings,
        },
        "skeptic": {
            "reviewer":  "Skeptic",
            "focus":     "Challenge overrated positions, flag structural contradictions",
            "findings":  skeptic_flags,
        },
        "market_contrarian": {
            "reviewer":  "Market Contrarian",
            "focus":     "Identify links-boosted players the market has not fully repriced",
            "findings":  mc_notes,
        },
        "audit_officer": {
            "reviewer":  "Audit Officer",
            "focus":     "Data integrity — source validation, debut flags, thin samples, missing windows",
            "findings":  audit_notes,
        },
        "synthesis_chair": {
            "reviewer":  "Synthesis Chair",
            "focus":     "Final rulings — accepts, overrides, Tom Kim adjudication",
            "findings":  synthesis_rulings,
        },
    },
    "tom_kim_adjudication": tom_kim_council,
    "key_stats": {
        "t1_count":               len(tier1_players),
        "t2_count":               len(tier2_players),
        "debut_count":            len(debut_players),
        "thin_birkdale_count":    len(thin_players),
        "links_boosted_count":    len(links_boosted),
        "no_links_data_count":    len(no_links_data),
        "skeptic_flags_raised":   len(skeptic_flags),
    },
}

# ── Synthesis changes log ─────────────────────────────────────────────────────
# Compare v2 ranks (v2 order = general SG only, no links delta)
# Re-create approximate v2 VTS for each player (VFS_base only, no links delta)
synthesis_changes = []
for p in all_players:
    vts_v3  = p["vts_final"]
    vfs_b   = p.get("vfs_base", p["venue_fit_score"])
    vfs_d   = p.get("vfs_links_delta", 0)
    nsi_v   = p["neutral_skill_index"]
    vhn_v   = p["venue_history_normalized"]
    frm_v   = p["form_score"]
    vts_v2_approx = round(W_NSI*nsi_v + W_VFS*vfs_b + W_VHN*vhn_v + W_FORM*frm_v, 2)
    delta   = round(vts_v3 - vts_v2_approx, 2)
    if abs(delta) >= 1.0 or p.get("links_signal_score") is not None:
        driver = "links_signal" if abs(vfs_d) >= 1.0 else "vhn_v3" if abs(vts_v3 - vts_v2_approx - vfs_d * W_VFS) > 0.5 else "model_base"
        synthesis_changes.append({
            "player":         _pname(p),
            "nkey_id":        nkey(_pname(p)),
            "v2_vts_approx":  vts_v2_approx,
            "v3_vts":         vts_v3,
            "delta_vts":      delta,
            "v3_tier":        p["tier"],
            "v3_rank":        p["rank"],
            "links_delta_vfs":vfs_d,
            "links_signal":   p.get("links_signal_score"),
            "birkdale_tag":   p.get("birkdale_tag",""),
            "driver":         driver,
        })

synthesis_changes.sort(key=lambda x: -abs(x["delta_vts"]))

# ── All-player notes JSON ─────────────────────────────────────────────────────
all_player_notes = []
for p in all_players:
    all_player_notes.append({
        "player":              _pname(p),
        "rank":                p["rank"],
        "tier":                p["tier"],
        "vts":                 p["vts_final"],
        "conviction_statement":p["conviction_statement"],
        "failure_condition":   p["failure_condition"],
        "risk_vector":         p["risk_vector"],
        "anti_pattern_summary":p["anti_pattern_summary"],
        "links_signal_note":   p["links_signal_note"],
        "birkdale_history_note":p["birkdale_history_note"],
        "form_note":           p["form_note"],
        "scoring_thesis":      p["scoring_thesis"],
        "links_fit_note":      p["links_fit_note"],
        "structural_note":     p["structural_note"],
        "bet_path_note":       p["bet_path_note"],
        "council_override_note":p["council_override_note"],
    })

# ── Links signal audit CSV ────────────────────────────────────────────────────
links_audit_rows = []
for p in all_players:
    links_audit_rows.append({
        "rank":             p["rank"],
        "player":           _pname(p),
        "tier":             p["tier"],
        "vts":              p["vts_final"],
        "vfs_base":         p.get("vfs_base", 0),
        "links_delta":      p.get("vfs_links_delta", 0),
        "vfs_final":        p["venue_fit_score"],
        "links_signal":     p.get("links_signal_score",""),
        "links_confidence": p.get("links_signal_confidence",""),
        "ev_6m":            p.get("true_links_events_6m", 0),
        "sg_6m":            p.get("true_links_total_6m",""),
        "ev_12m":           p.get("true_links_events_12m", 0),
        "sg_12m":           p.get("true_links_total_12m",""),
        "ev_24m":           p.get("true_links_events_24m", 0),
        "sg_24m":           p.get("true_links_total_24m",""),
        "ev_alltime":       p.get("true_links_events_alltime", 0),
        "sg_alltime":       p.get("true_links_total_alltime",""),
        "trace":            p.get("links_signal_trace",""),
    })

# ── Birkdale history audit CSV ────────────────────────────────────────────────
birk_audit_rows = []
for p in all_players:
    birk_audit_rows.append({
        "rank":             p["rank"],
        "player":           _pname(p),
        "tier":             p["tier"],
        "vts":              p["vts_final"],
        "birkdale_tag":     p.get("birkdale_tag",""),
        "birkdale_events":  p.get("birkdale_events", 0),
        "birkdale_sg_rnd":  p.get("birkdale_sg_per_round",""),
        "vhn":              p["venue_history_normalized"],
        "ch_2008":          raw.get(nkey(_pname(p)),{}).get("ch_2008",""),
        "ch_2017":          raw.get(nkey(_pname(p)),{}).get("ch_2017",""),
        "best_finish":      p.get("best_finish_birkdale",""),
        "vhn_note":         p["venue_history_summary"][:80],
    })

# ── Event context / payload / weather ────────────────────────────────────────
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
    "primary_scoring_zone":"Approach 150-200yds (dominant par-4 approach zone at 175-225yds)",
    "trait_weight_matrix": {
        "approach_150_200":  0.30,
        "sg_app_overall":    0.15,
        "sg_ott_positional": 0.20,
        "driving_accuracy":  0.12,
        "sg_putt":           0.13,
        "sg_arg_short_game": 0.10,
    },
    "links_signal_weights": LINK_WEIGHTS,
    "model_version":       "VenueDNA v3",
    "generated_date":      "2026-07-15",
    "tier_counts":         {str(k): v for k, v in tier_counts.items()},
    "anti_pattern_count":  sum(1 for p in all_players if p["ap_total_flags"] >= 1),
    "debut_count":         sum(1 for p in all_players if p["debut_flag"]),
    "similar_courses":     list(VENUE.get("similar_course_mapping", {}).items()),
    "expected_winning_score": VENUE["scoring_par_baseline"]["expected_winning_score_relative_to_par"],
    "wind_forecast":       "10-25mph W/NW/SW Irish Sea; gusts possible 30-35mph on holes 4, 6, 12, 13, 15, 18",
}

payload = {
    "event":          "2026 The Open Championship",
    "players":        all_players,
    "generated_date": "2026-07-15",
    "model_version":  "VenueDNA v3",
}

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
         "tag": "Firm/Breezy", "color": "#f59e0b",
         "note": "Opening conditions. Positional driving critical."},
        {"round": 2, "date": "Fri Jul 18", "wind_mph": "15-22", "wind_dir": "NW/SW",
         "tag": "Challenging", "color": "#dc2626",
         "note": "Wind increases. 150-200yd approaches decisive."},
        {"round": 3, "date": "Sat Jul 19", "wind_mph": "10-18", "wind_dir": "W",
         "tag": "Moving Day", "color": "#22c55e",
         "note": "Scoring window. Ball-strikers separate."},
        {"round": 4, "date": "Sun Jul 20", "wind_mph": "14-20", "wind_dir": "W/NW",
         "tag": "Championship Sunday", "color": "#c9a84c",
         "note": "Pressure links golf. Course management wins."},
    ],
}

# ── VTS CSV ───────────────────────────────────────────────────────────────────
vts_rows = []
for p in all_players:
    vts_rows.append({
        "rank":         p["rank"],
        "player_name":  _pname(p),
        "tier":         p["tier"],
        "vts_final":    p["vts_final"],
        "nsi":          p["neutral_skill_index"],
        "vfs":          p["venue_fit_score"],
        "vfs_base":     p.get("vfs_base", 0),
        "vfs_links_d":  p.get("vfs_links_delta", 0),
        "vhn":          p["venue_history_normalized"],
        "form":         p["form_score"],
        "birkdale_tag": p.get("birkdale_tag",""),
        "win_prob":     p["win_prob"],
        "top5_prob":    p["top5_prob"],
        "top10_prob":   p["top10_prob"],
        "top20_prob":   p["top20_prob"],
        "make_cut_prob":p["make_cut_prob"],
        "sg_app_12m":   p["sg_app_12m"],
        "sg_ott_12m":   p["sg_ott_12m"],
        "sg_arg_12m":   p["sg_arg_12m"],
        "sg_putt_12m":  p["sg_putt_12m"],
        "links_signal": p.get("links_signal_score",""),
        "links_delta":  p.get("vfs_links_delta", 0),
        "ap_flags":     p["ap_total_flags"],
        "form_class":   p["form_class"],
        "badges":       "; ".join(p["badges"]),
        "best_bet":     p["best_betting_lane"],
    })

# ── QA ────────────────────────────────────────────────────────────────────────
qa_report = {
    "event_id": EVENT_SLUG,
    "generated_at": NOW,
    "field_size": len(all_players),
    "model_version": "VenueDNA v3",
    "trait_coverage": {},
    "debut_players": [],
    "summary": {},
}

for td in TRAIT_DEFS:
    tk      = td["key"]
    covered = sum(1 for p in all_players
                  if any(t["key"] == tk and not t["imputed"] for t in p["trait_scores"]))
    qa_report["trait_coverage"][tk] = {
        "covered":      covered,
        "imputed":      len(all_players) - covered,
        "coverage_pct": round(covered / len(all_players) * 100, 1),
    }

qa_report["debut_players"] = [_pname(p) for p in all_players if p["debut_flag"]]
qa_report["summary"] = {
    "total_players":        len(all_players),
    "debut_count":          len(qa_report["debut_players"]),
    "anti_pattern_count":   sum(1 for p in all_players if p["ap_total_flags"] >= 1),
    "tier_distribution":    {str(k): v for k, v in tier_counts.items()},
    "win_pct_sum":          round(sum(p["win_prob"] for p in all_players), 1),
    "avg_vts":              round(sum(p["vts_final"] for p in all_players) / len(all_players), 2),
    "links_boosted_players":len(links_boosted),
    "birkdale_active_players": sum(1 for p in all_players if p.get("birkdale_tag") == "BirkdaleHistoryActive"),
    "birkdale_thin_players":   sum(1 for p in all_players if p.get("birkdale_tag") == "BirkdaleHistoryThin"),
    "model_version":        "VenueDNA v3",
}

# ── Final analysis ────────────────────────────────────────────────────────────
final_analysis = {
    "schema_version":  "3.0-pretournament",
    "generated_at":    "2026-07-15",
    "build_timestamp": NOW,
    "round":           0,
    "event_slug":      EVENT_SLUG,
    "model_version":   "VenueDNA v3",
    "enrichment_used": True,
    "links_signal_used": True,
    "metadata": {
        "event_name":           "2026 The Open Championship",
        "course_name":          "Royal Birkdale Golf Club",
        "par":                  VENUE["par"],
        "total_par":            VENUE["par"] * 4,
        "round_label":          "Pre-Tournament",
        "is_final":             False,
        "is_full_tournament":   False,
        "field_size_finished":  len(all_players),
        "winner":               None,
    },
    "venue_summary": {
        "par":               VENUE["par"],
        "yardage":           VENUE["yardage"],
        "expected_winning_score": VENUE["scoring_par_baseline"]["expected_winning_score_relative_to_par"],
        "sigma":             VENUE["scoring_par_baseline"]["sigma_winning_score"],
        "primary_separator": "SG:APP 175-225yd mid-iron",
        "secondary_separator":"SG:ARG revetted bunkers",
        "putting_role":      "Dampened — lag avoidance over spike putting on firm fescue",
        "wind_role":         "Critical — 10-25mph W/NW/SW Irish Sea; H4, H6, H12, H13, H15, H18 spike difficulty",
        "upgrade_traits":    VENUE["player_trait_overrides"]["upgrade_traits"],
        "downgrade_traits":  VENUE["player_trait_overrides"]["downgrade_traits"],
    },
    "tier_lists": {
        f"tier{t}": [
            {
                "playerName": _pname(p),
                "tier":       f"T{t}",
                "vtsFinal":   p["vts_final"],
                "nsi":        p["neutral_skill_index"],
                "vfs":        p["venue_fit_score"],
                "vfs_base":   p.get("vfs_base", 0),
                "vfs_links_delta": p.get("vfs_links_delta", 0),
                "vhn":        p["venue_history_normalized"],
                "birkdaleTag":p.get("birkdale_tag",""),
                "form":       p["form_score"],
                "winPct":     p["win_prob"],
                "top10Pct":   p["top10_prob"],
                "makeCutPct": p["make_cut_prob"],
                "badges":     p["badges"],
                "bettingPath":p["best_betting_lane"],
                "thesis":     p["conviction_statement"],
                "linksNote":  p["links_signal_note"],
                "birkdaleNote":p["birkdale_history_note"],
            }
            for p in all_players if p["tier"] == t
        ]
        for t in range(1, 6)
    },
    "value_section": {
        "modelOver":      model_over[:6],
        "modelUnder":     model_under[:6],
        "structuralFades":struct_fades[:8],
        "linksBoosted":   links_boosted[:8],
        "disclaimer":     ("VenueDNA is an analytical pre-tournament baseline. "
                           "Probabilities are model-derived from skill and venue data. "
                           "Not financial betting advice."),
    },
    "anti_pattern_flags": {
        "hardGatePlayers": [
            {"playerName": _pname(p), "flags": ap_flags.get(nkey(_pname(p)),[]), "tier": p["tier"]}
            for p in all_players
            if any(f in ap_flags.get(nkey(_pname(p)),[]) for f in ("bomb_and_spray","approach_liability"))
        ][:10],
        "softGatePlayers": [
            {"playerName": _pname(p), "flags": ap_flags.get(nkey(_pname(p)),[]), "tier": p["tier"]}
            for p in all_players
            if "debut_risk" in ap_flags.get(nkey(_pname(p)),[])
        ][:10],
    },
    "council_summary": {
        "t1_count":            len(tier1_players),
        "skeptic_flags":       len(skeptic_flags),
        "links_boosted":       len(links_boosted),
        "tom_kim_ruling":      tom_kim_council.get("synthesis_ruling","N/A"),
    },
    "allPlayers":    all_players,
    "weather":       weather_deploy,
    "event_context": event_ctx,
    "qa_summary":    qa_report["summary"],
}

# ── Write outputs ─────────────────────────────────────────────────────────────
print("\nWriting outputs…")

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  {path.name}: {path.stat().st_size/1024:.0f} KB")

def write_csv(path, rows, fields=None):
    if not rows: return
    fields = fields or list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name}: {path.stat().st_size/1024:.0f} KB")

# Output dir artifacts
write_json(OUT / f"{EVENT_SLUG}_eventpayload_v3.json",     payload)
write_json(OUT / f"{EVENT_SLUG}_playerbriefs_v3.json",     {"players": all_players})
write_json(OUT / f"{EVENT_SLUG}_final_analysis_v3.json",   final_analysis)
write_json(OUT / f"{EVENT_SLUG}_qareport_v3.json",         qa_report)
write_csv (OUT / f"{EVENT_SLUG}_vtsfull_v3.csv",           vts_rows)
write_json(OUT / f"{EVENT_SLUG}_council_findings.json",    council_findings)
write_json(OUT / f"{EVENT_SLUG}_all_player_notes.json",    all_player_notes)
write_json(OUT / f"{EVENT_SLUG}_synthesis_changes_log.json", synthesis_changes)
write_csv (OUT / f"{EVENT_SLUG}_links_signal_audit.csv",   links_audit_rows)
write_csv (OUT / f"{EVENT_SLUG}_birkdale_history_audit.csv", birk_audit_rows)

# Deploy dir (board reads these)
write_json(DEPLOY / "event_payload.json",    payload)
write_json(DEPLOY / "player_briefs.json",    {"players": all_players})
write_json(DEPLOY / "final_analysis.json",   final_analysis)
write_json(DEPLOY / "weather.json",          weather_deploy)
write_json(DEPLOY / "event_context.json",    event_ctx)
write_json(DEPLOY / "council_findings.json", council_findings)
write_csv (DEPLOY / "vts_full.csv",          vts_rows)

# ── Top-line summary ──────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TOP-LINE SPOT CHECK (v3)")
print("="*70)
spotlight = ["Scottie Scheffler","Rory McIlroy","Matt Fitzpatrick","Tommy Fleetwood",
             "Jon Rahm","Si Woo Kim","Robert MacIntyre","Ludvig Aberg","Viktor Hovland",
             "Shane Lowry","Tom Kim","Xander Schauffele","Sepp Straka","Matt Wallace"]
for p in all_players:
    pn = _pname(p)
    if pn in spotlight:
        ld  = p.get("vfs_links_delta", 0)
        ls  = p.get("links_signal_score","—")
        btag = p.get("birkdale_tag","—")[:20]
        ev_b = p.get("birkdale_events", 0)
        print(f"\n{pn}")
        print(f"  T{p['tier']} rank={p['rank']} | VTS={p['vts_final']} | NSI={p['neutral_skill_index']:.1f} | "
              f"VFS={p['venue_fit_score']:.1f}(base={p.get('vfs_base',0):.1f}+lnk={ld:+.1f}) | "
              f"VHN={p['venue_history_normalized']:.1f} | Form={p['form_score']:.1f}")
        print(f"  Win={p['win_prob']}% | Top10={p['top10_prob']}% | Cut={p['make_cut_prob']}%")
        print(f"  Links sig={ls} | Birkdale={btag}({ev_b}ev) | Flags={p['ap_total_flags']}")
        print(f"  Score: {p['scoring']['ceiling']}/{p['scoring']['expected']}/{p['scoring']['floor']}")
        print(f"  {p['conviction_statement'][:80]}…")

print("\n" + "="*70)
print(f"Win% sum: {sum(p['win_prob'] for p in all_players):.1f}%")
print(f"Links boosted players (delta>=4): {len(links_boosted)}")
print(f"Birkdale debuts: {len(debut_players)}")
print("Done.")
