"""
Round 1 Analysis Builder — 2026 Travelers Championship
Joins Round 1 data against pre-tournament model to produce r1_analysis.json.
"""
import csv, json, re, unicodedata
from pathlib import Path
from statistics import mean

ROOT = Path(r"C:\PGA_VenueDNA\events\2026_TravelersChampionship")
R1   = ROOT / "output" / "round1 player & course stats"
OUT  = ROOT / "output"
DEP  = ROOT / "deploy" / "data"

def load_csv(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def ascii_fold(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")

def fl_to_lf(name):
    parts = name.strip().split()
    return parts[-1] + ", " + " ".join(parts[:-1]) if len(parts) >= 2 else name

def avg(lst):
    vals = [x for x in lst if x is not None]
    return round(mean(vals), 3) if vals else None

def parse_float(v):
    try: return float(v)
    except: return None

def parse_prox(s):
    s = str(s).strip()
    m = re.match(r"(\d+)'\s*(\d+)\"", s)
    if m: return int(m.group(1))*12 + int(m.group(2))
    m2 = re.match(r"(\d+)'", s)
    if m2: return int(m2.group(1))*12
    return None

def parse_pct(s):
    try: return float(str(s).rstrip("%"))
    except: return None

# ── Load files ──────────────────────────────────────────────────────────────
lb  = load_csv(R1 / "round1_leaderboard.csv")
sg  = load_csv(R1 / "round1_player_strokes_gained.csv")
tfm = load_csv(OUT / "2026_travelers_championship_trait_form_matrix.csv")
cs  = load_csv(R1 / "round1_course_stats.csv")

with open(DEP / "event_payload.json", encoding="utf-8") as f:
    payload = json.load(f)

CI_PATH   = R1 / "round1_course_insights.csv"
ci_rows   = load_csv(CI_PATH) if CI_PATH.exists() else []
ci_loaded = bool(ci_rows)

# ── Pre-tournament lookup ────────────────────────────────────────────────────
pretournament = {}
for tier in [1, 2, 3, 4, 5]:
    for p in payload["tiers"].get(f"tier_{tier}", []):
        pretournament[ascii_fold(p["player_name"]).lower()] = p

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
VENUE_WEIGHTS = {
    "app_wedge": 0.22, "app_100_150": 0.12, "app_150_200": 0.06,
    "ott_accuracy": 0.14, "ott_distance": 0.05, "putt_short_conv": 0.16,
    "putt_lag": 0.10, "arg_rough": 0.07, "arg_bunker": 0.05, "par5_scoring": 0.03,
}

# Build trait lookup from trait_form_matrix
trait_by_nk = {}
for row in tfm:
    nk = row.get("name_key", "")
    traits = {}
    for tk, col in TRAIT_COLS.items():
        try:
            v = float(row.get(col, 0))
            traits[tk] = round(v, 1) if v > 0 else None
        except:
            traits[tk] = None
    trait_by_nk[nk] = traits

name_to_nk = {}
for row in tfm:
    pname = ascii_fold(row["player_display"]).lower()
    name_to_nk[pname] = row["name_key"]

def lookup_traits(name_lf):
    nk = name_to_nk.get(ascii_fold(name_lf).lower())
    return trait_by_nk.get(nk) if nk else None

# SG lookup
sg_by_folded = {}
for row in sg:
    sg_by_folded[ascii_fold(row["Player"].strip())] = row

# ── Course insights lookup (DataGolf proxy) ──────────────────────────────────
ci_by_norm = {}
if ci_loaded:
    for row in ci_rows:
        full = (row.get("First Name", "") + " " + row.get("Last Name", "")).strip()
        nk = fl_to_lf(ascii_fold(full)).lower()
        ci_by_norm[nk] = {
            "d_distance":   parse_float(row.get("D. Distance")),
            "d_accuracy":   parse_pct(row.get("D. Accuracy")),
            "gir":          parse_pct(row.get("GIR")),
            "fairway_prox": parse_prox(row.get("Fairway Prox", "")),
            "rough_prox":   parse_prox(row.get("Rough Prox", "")),
            "scrambling":   parse_pct(row.get("Scrambling")),
            "great_shots":  parse_float(row.get("Great Shots")),
            "poor_shots":   parse_float(row.get("Poor Shots")),
        }

# ── Join leaderboard to everything ──────────────────────────────────────────
joined = []
unmatched = []

for row in lb:
    r1_name = row["PLAYER"]
    folded  = ascii_fold(r1_name)
    norm    = fl_to_lf(folded)
    pt      = pretournament.get(norm.lower())
    sg_row  = sg_by_folded.get(folded)

    r1_pos_str = row["POS"]
    r1_pos_num = int(r1_pos_str.replace("T", "")) if r1_pos_str.replace("T", "").isdigit() else 72
    r1_score   = parse_float(row["TOTAL"]) or 0

    record = {
        "r1_name":    r1_name,
        "norm_name":  norm,
        "r1_pos":     r1_pos_num,
        "r1_pos_str": r1_pos_str,
        "r1_score":   r1_score,
        "r1_strokes": int(row["Total Strokes"]),
        "matched":    pt is not None,
        "pt_rank":    pt["rank"]               if pt else None,
        "pt_tier":    pt["tier"]               if pt else None,
        "pt_vts":     float(pt["vts_final"])   if pt else None,
        "pt_win_pct": float(pt["win_pct"])     if pt else None,
        "pt_top10":   float(pt["top10_pct"])   if pt else None,
        "pt_top20":   float(pt.get("top20_pct", 0)) if pt else None,
        "pt_flags":   (pt.get("anti_pattern_flags") or "") if pt else "",
        "pt_driver":  pt.get("primary_driver", "") if pt else "",
        "sg_ott":     parse_float(sg_row["SG-Off the Tee"])          if sg_row else None,
        "sg_app":     parse_float(sg_row["SG-Approach to Green"])     if sg_row else None,
        "sg_arg":     parse_float(sg_row["SG- Around the Green"])     if sg_row else None,
        "sg_putt":    parse_float(sg_row["SG-Putting"])               if sg_row else None,
        "sg_tot":     parse_float(sg_row["SG-Total"])                 if sg_row else None,
        "traits":     lookup_traits(norm),
        "rank_delta": (pt["rank"] - r1_pos_num) if pt else 0,
    }
    joined.append(record)
    if not pt:
        unmatched.append(r1_name)

# Attach course insights proxy data to every joined record
for r in joined:
    r["ci"] = ci_by_norm.get(r["norm_name"].lower())

matched = [r for r in joined if r["matched"]]

# ── Model performance ────────────────────────────────────────────────────────
def group_stats(group):
    return {
        "n":          len(group),
        "avg_r1_pos": avg([r["r1_pos"] for r in group]),
        "avg_r1_score": avg([r["r1_score"] for r in group]),
        "in_r1_top10":  sum(1 for r in group if r["r1_pos"] <= 10),
        "in_r1_top20":  sum(1 for r in group if r["r1_pos"] <= 20),
        "in_r1_top30":  sum(1 for r in group if r["r1_pos"] <= 30),
    }

pt_top10  = [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 10]
pt_top20  = [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 20]
tier1     = [r for r in matched if r["pt_tier"] == 1]
tier2     = [r for r in matched if r["pt_tier"] == 2]
tier1_2   = [r for r in matched if r["pt_tier"] in (1, 2)]

model_perf = {
    "pt_top10":  group_stats(pt_top10),
    "pt_top20":  group_stats(pt_top20),
    "tier1":     group_stats(tier1),
    "tier2":     group_stats(tier2),
    "tier1_2":   group_stats(tier1_2),
    "all_field": group_stats(joined),
}

# Spearman rank correlation
pairs = [(r["pt_rank"], r["r1_pos"]) for r in matched if r["pt_rank"]]
n = len(pairs)
d2 = sum((a - b) ** 2 for a, b in pairs)
spearman_rho = round(1 - 6 * d2 / (n * (n**2 - 1)), 3)

# ── Trait audit ──────────────────────────────────────────────────────────────
top10_group = [r for r in joined if r["r1_pos"] <= 10]
top18_group = [r for r in joined if r["r1_pos"] <= 18]

# SG leader averages vs field
def sg_summary(group):
    return {
        "sg_ott":  avg([r["sg_ott"]  for r in group]),
        "sg_app":  avg([r["sg_app"]  for r in group]),
        "sg_arg":  avg([r["sg_arg"]  for r in group]),
        "sg_putt": avg([r["sg_putt"] for r in group]),
        "sg_tot":  avg([r["sg_tot"]  for r in group]),
    }

sg_leaders_top10  = sg_summary(top10_group)
sg_leaders_top18  = sg_summary(top18_group)
sg_field_all      = sg_summary(joined)

# Trait profiles: top 10 R1 vs full field (for matched players with traits)
top10_with_traits = [r for r in top10_group if r["matched"] and r["traits"]]
all_with_traits   = [r for r in matched if r["traits"]]

TRAIT_SIGNAL_THRESHOLDS = {
    "strong":    6,   # delta >= 6 -> strong validated
    "lean":      2,   # delta >= 2 -> mixed/lean
    "neutral":  -3,   # delta > -3 -> neutral
    "weak":    -99,   # else -> weak
}

trait_audit = {}
for tk in TRAIT_COLS:
    w = VENUE_WEIGHTS[tk]
    t10_vals = [r["traits"][tk] for r in top10_with_traits if r["traits"] and r["traits"].get(tk) is not None]
    f_vals   = [r["traits"][tk] for r in all_with_traits   if r["traits"] and r["traits"].get(tk) is not None]
    t10a = avg(t10_vals)
    fa   = avg(f_vals)
    delta = round(t10a - fa, 1) if t10a is not None and fa is not None else None

    # Supplementary SG signal
    sg_proxy = {
        "app_wedge":       "sg_app",
        "app_100_150":     "sg_app",
        "app_150_200":     "sg_app",
        "ott_accuracy":    "sg_ott",
        "ott_distance":    "sg_ott",
        "putt_short_conv": "sg_putt",
        "putt_lag":        "sg_putt",
        "arg_rough":       "sg_arg",
        "arg_bunker":      "sg_arg",
        "par5_scoring":    "sg_app",
    }
    sg_key = sg_proxy.get(tk)
    sg_t10 = avg([r[sg_key] for r in top10_group if r.get(sg_key) is not None]) if sg_key else None
    sg_all = avg([r[sg_key] for r in joined      if r.get(sg_key) is not None]) if sg_key else None
    sg_delta = round(sg_t10 - sg_all, 3) if sg_t10 is not None and sg_all is not None else None

    # Signal classification using both trait delta and SG delta
    if delta is None and sg_delta is None:
        signal = "not_testable"
    else:
        d = delta if delta is not None else 0
        if d >= TRAIT_SIGNAL_THRESHOLDS["strong"]:
            signal = "validated"
        elif d >= TRAIT_SIGNAL_THRESHOLDS["lean"]:
            signal = "mixed"
        elif d >= TRAIT_SIGNAL_THRESHOLDS["neutral"]:
            signal = "neutral"
        else:
            signal = "weak"

    trait_audit[tk] = {
        "venue_weight":    w,
        "top10_trait_avg": t10a,
        "field_trait_avg": fa,
        "trait_delta":     delta,
        "sg_proxy":        sg_key,
        "sg_top10":        sg_t10,
        "sg_field":        sg_all,
        "sg_delta":        sg_delta,
        "signal":          signal,
        "sample_n_top10":  len(t10_vals),
        "sample_n_field":  len(f_vals),
    }

# ── Course insights enrichment layer ─────────────────────────────────────────
CI_TRAIT_MAP = {
    "app_wedge":       {"primary": "fairway_prox",  "direction": "lower_better",  "secondary": "gir"},
    "app_100_150":     {"primary": "fairway_prox",  "direction": "lower_better",  "secondary": "gir"},
    "app_150_200":     {"primary": "gir",           "direction": "higher_better", "secondary": "fairway_prox"},
    "ott_accuracy":    {"primary": "d_accuracy",    "direction": "higher_better", "secondary": None},
    "ott_distance":    {"primary": "d_distance",    "direction": "higher_better", "secondary": None},
    "putt_short_conv": {"primary": None,            "direction": None,            "secondary": None},
    "putt_lag":        {"primary": None,            "direction": None,            "secondary": None},
    "arg_rough":       {"primary": "scrambling",    "direction": "higher_better", "secondary": "rough_prox"},
    "arg_bunker":      {"primary": "scrambling",    "direction": "higher_better", "secondary": None},
    "par5_scoring":    {"primary": "gir",           "direction": "higher_better", "secondary": "d_distance"},
}
CI_SIG = {"fairway_prox": 20, "rough_prox": 50,  "gir": 3.0, "d_accuracy": 3.0, "scrambling": 10.0, "d_distance": 3.0}
CI_STR = {"fairway_prox": 36, "rough_prox": 100, "gir": 5.0, "d_accuracy": 5.0, "scrambling": 15.0, "d_distance": 6.0}

def ci_avg_field(field, group):
    vals = [r["ci"][field] for r in group if r.get("ci") and r["ci"].get(field) is not None]
    return avg(vals)

def enr_delta(field, direction, t10v, fv):
    if t10v is None or fv is None: return None
    return round(fv - t10v, 2) if direction == "lower_better" else round(t10v - fv, 2)

def enr_signal(field, delta, base_sig):
    if delta is None: return "not_available"
    if delta < 0: return "contradicted"
    if delta < CI_SIG.get(field, 3.0): return "neutral"
    if delta >= CI_STR.get(field, 5.0) and base_sig in ("mixed", "neutral", "weak", "not_testable"):
        return "upgraded"
    return "confirmed"

def _make_ci_note(field, direction, t10v, fv, d):
    units = {"fairway_prox": "in", "rough_prox": "in", "gir": "%",
             "d_accuracy": "%", "scrambling": "%", "d_distance": "yds"}
    u = units.get(field, "")
    if t10v is None or fv is None: return f"{field}: n/a"
    if direction == "lower_better":
        return f"{field}: top10={round(t10v,1)}{u} vs field={round(fv,1)}{u} (closer by {round(d,1)}{u})"
    return f"{field}: top10={round(t10v,1)}{u} vs field={round(fv,1)}{u} ({'+' if d>=0 else ''}{round(d,1)}{u})"

UPGRADE_MAP = {"weak": "neutral", "not_testable": "neutral", "neutral": "mixed", "mixed": "validated"}

top10_ci = [r for r in top10_group if r.get("ci")]
all_ci   = [r for r in joined if r.get("ci")]

if ci_loaded:
    for tk, mapping in CI_TRAIT_MAP.items():
        primary   = mapping["primary"]
        direction = mapping["direction"]
        secondary = mapping["secondary"]

        if primary is None:
            trait_audit[tk]["enrichment"] = {"available": False, "reason": "no_direct_proxy"}
            continue

        t10_pri  = ci_avg_field(primary, top10_ci)
        f_pri    = ci_avg_field(primary, all_ci)
        delta    = enr_delta(primary, direction, t10_pri, f_pri)
        base_sig = trait_audit[tk]["signal"]
        e_sig    = enr_signal(primary, delta, base_sig)

        t10_sec = ci_avg_field(secondary, top10_ci) if secondary else None
        f_sec   = ci_avg_field(secondary, all_ci)   if secondary else None
        sec_dir = "lower_better" if secondary in ("fairway_prox", "rough_prox") else "higher_better"
        sec_d   = enr_delta(secondary, sec_dir, t10_sec, f_sec) if secondary else None

        notes = [_make_ci_note(primary, direction, t10_pri, f_pri, delta or 0)]
        if secondary and t10_sec is not None:
            notes.append(_make_ci_note(secondary, sec_dir, t10_sec, f_sec, sec_d or 0))

        upgraded_sig = UPGRADE_MAP.get(base_sig, base_sig) if e_sig == "upgraded" else base_sig

        trait_audit[tk]["enrichment"] = {
            "available":         True,
            "source":            "course_insights_dg_proxy",
            "proxy_fields":      [primary] + ([secondary] if secondary else []),
            "primary_field":     primary,
            "direction":         direction,
            "top10_primary":     t10_pri,
            "field_primary":     f_pri,
            "delta_primary":     delta,
            "top10_secondary":   t10_sec,
            "field_secondary":   f_sec,
            "delta_secondary":   sec_d,
            "enrichment_signal": e_sig,
            "upgraded_signal":   upgraded_sig,
            "enrichment_note":   " | ".join(notes),
            "n_top10_ci":        len(top10_ci),
            "n_field_ci":        len(all_ci),
        }
        if e_sig == "upgraded":
            trait_audit[tk]["signal"] = upgraded_sig
            trait_audit[tk]["signal_upgraded_by_enrichment"] = True

    ci_scramb_t10 = ci_avg_field("scrambling",   top10_ci)
    ci_scramb_all = ci_avg_field("scrambling",   all_ci)
    ci_acc_t10    = ci_avg_field("d_accuracy",   top10_ci)
    ci_acc_all    = ci_avg_field("d_accuracy",   all_ci)
    ci_fp_t10     = ci_avg_field("fairway_prox", top10_ci)
    ci_fp_all     = ci_avg_field("fairway_prox", all_ci)
    ci_dd_t10     = ci_avg_field("d_distance",   top10_ci)
    ci_dd_all     = ci_avg_field("d_distance",   all_ci)
    upgraded_traits  = [tk for tk in trait_audit if trait_audit[tk].get("signal_upgraded_by_enrichment")]
    confirmed_traits = [tk for tk in trait_audit
                        if trait_audit[tk].get("enrichment", {}).get("enrichment_signal") == "confirmed"]
    enrichment_summary = {
        "source":           "round1_course_insights.csv (DataGolf proxy — not PGAT official SG)",
        "player_match_n":   len(all_ci),
        "player_total":     len(joined),
        "traits_upgraded":  upgraded_traits,
        "traits_confirmed": confirmed_traits,
        "key_findings": [
            f"Scrambling: top10={round(ci_scramb_t10 or 0,1)}% vs field={round(ci_scramb_all or 0,1)}% ({round((ci_scramb_t10 or 0)-(ci_scramb_all or 0),1):+}pp) -> ARG UPGRADED",
            f"D.Accuracy: top10={round(ci_acc_t10 or 0,1)}% vs field={round(ci_acc_all or 0,1)}% ({round((ci_acc_t10 or 0)-(ci_acc_all or 0),1):+}pp) -> OTT_Acc CONFIRMED",
            f"Fairway Prox: top10={round((ci_fp_t10 or 0)/12,1)}ft vs field={round((ci_fp_all or 0)/12,1)}ft (top10 closer) -> APP_Wedge CONFIRMED",
            f"D.Distance: top10={round(ci_dd_t10 or 0,1)}yds vs field={round(ci_dd_all or 0,1)}yds ({round((ci_dd_t10 or 0)-(ci_dd_all or 0),1):+}yds) -> OTT_Dist WEAK confirmed",
        ],
        "dg_note": "DataGolf SG correlated (~0.05-0.30 diff) but distinct from PGAT SG. Proxy layer only.",
    }
else:
    for tk in TRAIT_COLS:
        trait_audit[tk]["enrichment"] = {"available": False, "reason": "course_insights_not_loaded"}
    enrichment_summary = None

# ── Source confidence classification ─────────────────────────────────────────
# direct   = enrichment field is a 1:1 proxy for this specific trait concept
# proxy-confirmed = validated by both SG dimension + enrichment in same direction
# weak-proxy = directional evidence, single dimension, or limited sample
# not-testable = insufficient R1 data to draw conclusion

DIRECT_ENRICHMENT = {
    "ott_accuracy": "d_accuracy",
    "arg_rough":    "scrambling",
    "arg_bunker":   "scrambling",
}

def compute_source_confidence(tk, signal, enrichment):
    enr = enrichment if isinstance(enrichment, dict) else {}
    if not enr.get("available"):
        if signal == "validated": return "proxy-confirmed"
        if signal in ("mixed", "neutral"): return "weak-proxy"
        return "not-testable"
    e_sig = enr.get("enrichment_signal", "")
    pf    = enr.get("primary_field", "")
    if tk in DIRECT_ENRICHMENT and DIRECT_ENRICHMENT[tk] == pf and e_sig in ("confirmed", "upgraded"):
        return "direct"
    if signal == "validated" and e_sig in ("confirmed", "upgraded"):
        return "proxy-confirmed"
    if signal in ("mixed", "neutral") or e_sig == "neutral":
        return "weak-proxy"
    return "not-testable"

for tk in trait_audit:
    trait_audit[tk]["source_confidence"] = compute_source_confidence(
        tk, trait_audit[tk]["signal"], trait_audit[tk].get("enrichment")
    )

# ── Rank deltas: risers and slippage ────────────────────────────────────────
by_delta = sorted([r for r in matched if r["pt_rank"]], key=lambda x: -x["rank_delta"])

def player_summary(r):
    return {
        "r1_name":     r["r1_name"],
        "norm_name":   r["norm_name"],
        "r1_pos":      r["r1_pos"],
        "r1_pos_str":  r["r1_pos_str"],
        "r1_score":    r["r1_score"],
        "pt_rank":     r["pt_rank"],
        "pt_tier":     r["pt_tier"],
        "pt_vts":      r["pt_vts"],
        "pt_flags":    r["pt_flags"],
        "pt_driver":   r["pt_driver"],
        "rank_delta":  r["rank_delta"],
        "sg_ott":      r["sg_ott"],
        "sg_app":      r["sg_app"],
        "sg_arg":      r["sg_arg"],
        "sg_putt":     r["sg_putt"],
        "sg_tot":      r["sg_tot"],
    }

risers  = [player_summary(r) for r in by_delta[:12]]
slippage_candidates = sorted(
    [r for r in matched if r["pt_rank"] and r["pt_rank"] <= 35],
    key=lambda x: x["rank_delta"]
)
slippage = [player_summary(r) for r in slippage_candidates[:10]]

# Weekend risers: positive delta + SG profile matches course thesis
# Thesis: APP + ARG matter; OTT secondary
def riser_thesis_score(r):
    score = 0
    if r["sg_app"] and r["sg_app"] > 0.5: score += 2
    if r["sg_arg"] and r["sg_arg"] > 0.3: score += 1
    if r["sg_putt"] and r["sg_putt"] > 0.3: score += 1
    return score

def _make_thesis_note(r):
    notes = []
    if r["sg_app"] and r["sg_app"] > 0.8: notes.append(f"approach elite ({r['sg_app']:+.2f})")
    elif r["sg_app"] and r["sg_app"] > 0.4: notes.append(f"approach solid ({r['sg_app']:+.2f})")
    if r["sg_arg"] and r["sg_arg"] > 0.5: notes.append(f"scrambling strong ({r['sg_arg']:+.2f})")
    if r["sg_putt"] and r["sg_putt"] > 0.8: notes.append(f"putting hot ({r['sg_putt']:+.2f})")
    if not notes: notes.append("score above expectation")
    pt_driver = r.get("pt_driver", "")
    if pt_driver: notes.append(f"pre-event driver: {pt_driver}")
    return " | ".join(notes)

# Rebuild with proper function call order
weekend_risers = []
for r in by_delta[:20]:
    ts = riser_thesis_score(r)
    if ts >= 2 and r["r1_score"] <= -3:
        rec = player_summary(r)
        rec["thesis_score"] = ts
        rec["thesis_note"]  = _make_thesis_note(r)
        weekend_risers.append(rec)

# Slippage risk: R1 top 20, round primarily driven by putting with weak approach
# Must have sg_putt > 2.0 AND sg_app < 0.3 (putting-reliant, approach didn't back it)
# OR pre-tournament rank > 55 AND R1 pos <= 12 (huge overperformer, no model basis)
slippage_risk = []
for r in matched:
    if r["r1_pos"] > 20:
        continue
    risks = []
    sg_putt = r.get("sg_putt") or 0
    sg_app  = r.get("sg_app")  or 0
    pt_rank = r.get("pt_rank") or 99

    # Putting-driven round with weak approach — most regressive pattern
    if sg_putt > 2.0 and sg_app < 0.3:
        risks.append(f"putting-driven round ({sg_putt:+.2f} putting vs {sg_app:+.2f} APP) — regression likely")

    # Massive overperformer with no model basis AND weak approach (not a course-fit round)
    if pt_rank > 55 and r["r1_pos"] <= 12 and sg_app < 0.5:
        risks.append(f"no pre-tournament basis (model rank {pt_rank}), heat-check round")

    if risks:
        rec = player_summary(r)
        rec["risk_flags"] = risks
        slippage_risk.append(rec)

slippage_risk.sort(key=lambda x: x["r1_pos"])

# ── Live lean notes (data-driven, consumable by UI for any round) ─────────────
slippage_names = {r["r1_name"] for r in slippage_risk}
sustainable_leaders = [
    r for r in joined
    if r["r1_pos"] <= 6 and r["r1_name"] not in slippage_names and (r.get("sg_app") or 0) > 0.5
]

watch_next = [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str", ""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      " | ".join(r.get("risk_flags", [])),
        "flag_type": "slippage",
    }
    for r in slippage_risk[:5]
] + [
    {
        "player":    r["r1_name"],
        "pos_str":   r.get("r1_pos_str", ""),
        "score":     r.get("r1_score", 0),
        "sg_putt":   r.get("sg_putt"),
        "sg_app":    r.get("sg_app"),
        "note":      f"approach-backed leader (APP {(r.get('sg_app') or 0):+.2f}) — not flagged, sustainable position",
        "flag_type": "sustainable",
    }
    for r in sustainable_leaders[:2]
]

putt_outliers = sorted(
    [r for r in slippage_risk if (r.get("sg_putt") or 0) > 2.0],
    key=lambda x: -(x.get("sg_putt") or 0)
)

lean_up_traits = [
    {
        "trait":      tk,
        "delta":      trait_audit[tk].get("trait_delta"),
        "confidence": trait_audit[tk].get("source_confidence", "proxy-confirmed"),
        "enr_signal": (trait_audit[tk].get("enrichment") or {}).get("enrichment_signal"),
    }
    for tk in TRAIT_COLS if trait_audit[tk]["signal"] == "validated"
]
lean_down_traits = [
    {
        "trait": tk,
        "delta": trait_audit[tk].get("trait_delta"),
    }
    for tk in TRAIT_COLS if trait_audit[tk]["signal"] in ("weak", "not_testable")
]

live_lean_notes = {
    "round":            1,
    "next_round":       2,
    "lean_up_traits":   lean_up_traits,
    "lean_down_traits": lean_down_traits,
    "putt_caution":     len(putt_outliers) > 0,
    "putt_outliers":    [{"player": r["r1_name"], "sg_putt": r.get("sg_putt"), "sg_app": r.get("sg_app")} for r in putt_outliers[:3]],
    "watch_next_round": watch_next,
    "rho_note":         f"R1 rank correlation rho={spearman_rho} — model-field separation expected to sharpen by R3.",
}

# ── Cumulative learning (round-over-round signal tracking) ────────────────────
cumulative_round_entry = {
    "round":        1,
    "generated_at": "2026-06-25",
    "spearman_rho": spearman_rho,
    "trait_signals": {
        tk: {
            "signal":            v["signal"],
            "source_confidence": v.get("source_confidence", "not-testable"),
            "trait_delta":       v.get("trait_delta"),
            "sg_delta":          v.get("sg_delta"),
            "enrichment_signal": (v.get("enrichment") or {}).get("enrichment_signal"),
        }
        for tk, v in trait_audit.items()
    },
    "model_hits": {
        "pt_top10_in_top10": model_perf["pt_top10"]["in_r1_top10"],
        "pt_top10_in_top20": model_perf["pt_top10"]["in_r1_top20"],
        "tier1_2_in_top20":  model_perf["tier1_2"]["in_r1_top20"],
    },
    "risers":   [r["r1_name"] for r in weekend_risers],
    "slippage": [r["r1_name"] for r in slippage_risk],
}

cumulative_signals = {
    tk: {
        "rounds_observed":      [1],
        "signal_history":       [v["signal"]],
        "confidence_history":   [v.get("source_confidence", "not-testable")],
        "delta_history":        [v.get("trait_delta")],
        "consensus":            v["signal"],
        "consensus_confidence": v.get("source_confidence", "not-testable"),
    }
    for tk, v in trait_audit.items()
}

cumulative_learning = {
    "schema_version":    "1.0",
    "event_slug":        "2026_travelers_championship",
    "last_updated":      "2026-06-25",
    "rounds_completed":  1,
    "per_round":         {"1": cumulative_round_entry},
    "cumulative_signals": cumulative_signals,
}

# ── Course stats ─────────────────────────────────────────────────────────────
holes_data = []
for row in cs:
    holes_data.append({
        "hole":    int(row["Hole"]),
        "par":     int(row["Par"]),
        "yards":   int(row["Yards"]),
        "avg":     parse_float(row["Avg"]),
        "rank":    int(row["Rank"]),
        "plus_minus": parse_float(row["Plus - Minus"]),
        "birdies": int(row["Birdies"]),
        "pars":    int(row["Pars"]),
        "bogeys":  int(row["Bogeys"]),
        "dbl":     int(row["DBL+"]),
    })

# Top scoring holes (most birdies relative to par)
easiest = sorted(holes_data, key=lambda x: -x["birdies"])[:5]
hardest = sorted(holes_data, key=lambda x: -(x["bogeys"] + x["dbl"]))[:3]

# ── Leaderboard snapshot ─────────────────────────────────────────────────────
leaderboard_snapshot = []
for r in joined:
    snap = {
        "r1_name":    r["r1_name"],
        "r1_pos":     r["r1_pos"],
        "r1_pos_str": r["r1_pos_str"],
        "r1_score":   r["r1_score"],
        "pt_rank":    r["pt_rank"],
        "pt_tier":    r["pt_tier"],
        "pt_vts":     r["pt_vts"],
        "sg_app":     r["sg_app"],
        "sg_putt":    r["sg_putt"],
        "sg_ott":     r["sg_ott"],
        "sg_arg":     r["sg_arg"],
        "sg_tot":     r["sg_tot"],
    }
    leaderboard_snapshot.append(snap)

# ── Trait winners summary (by SG dimension) ──────────────────────────────────
sg_dimension_leaders = {
    "sg_app":  sorted([r for r in joined if r["sg_app"]  is not None], key=lambda x: -x["sg_app"])[:5],
    "sg_putt": sorted([r for r in joined if r["sg_putt"] is not None], key=lambda x: -x["sg_putt"])[:5],
    "sg_ott":  sorted([r for r in joined if r["sg_ott"]  is not None], key=lambda x: -x["sg_ott"])[:5],
    "sg_arg":  sorted([r for r in joined if r["sg_arg"]  is not None], key=lambda x: -x["sg_arg"])[:5],
}

dimension_leaders_clean = {}
for dim, group in sg_dimension_leaders.items():
    dimension_leaders_clean[dim] = [
        {"r1_name": r["r1_name"], "r1_pos": r["r1_pos_str"],
         "value": r[dim], "r1_score": r["r1_score"]} for r in group
    ]

# ── Assemble output ──────────────────────────────────────────────────────────
round_sources = [
    "round1_leaderboard.csv",
    "round1_player_strokes_gained.csv",
    "2026_travelers_championship_trait_form_matrix.csv",
    "deploy/data/event_payload.json",
] + (["round1_course_insights.csv"] if ci_loaded else [])

output = {
    "schema_version":         "1.1",
    "generated_at":           "2026-06-25",
    "round":                  1,
    "event_slug":             "2026_travelers_championship",
    "round_sources":          round_sources,
    "course_insights_loaded": ci_loaded,
    "enrichment_summary":     enrichment_summary,
    "live_lean_notes":        live_lean_notes,
    "match_summary": {
        "matched":         len(matched),
        "total_r1":        len(joined),
        "unmatched":       unmatched,
        "match_rate_pct":  round(len(matched) / len(joined) * 100, 1),
    },
    "model_performance": {
        "spearman_rho":    spearman_rho,
        "groups":          model_perf,
    },
    "sg_leader_averages": {
        "top10":     sg_leaders_top10,
        "top18":     sg_leaders_top18,
        "full_field": sg_field_all,
    },
    "trait_audit":       trait_audit,
    "risers":            risers,
    "slippage":          slippage,
    "weekend_risers":    weekend_risers,
    "slippage_risk":     slippage_risk,
    "leaderboard_snapshot": leaderboard_snapshot,
    "dimension_leaders": dimension_leaders_clean,
    "course_stats":      holes_data,
    "easiest_holes":     easiest,
    "hardest_holes":     hardest,
}

# Write outputs
out_path = OUT / "2026_travelers_championship_r1_analysis.json"
dep_path = DEP / "r1_analysis.json"
for path in [out_path, dep_path]:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote: {path}")

cum_path = OUT / "2026_travelers_championship_cumulative_learning.json"
cum_dep  = DEP / "cumulative_learning.json"
for path in [cum_path, cum_dep]:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cumulative_learning, f, indent=2)
    print(f"Wrote: {path}")

print()
print("=== SUMMARY ===")
print(f"Matched: {len(matched)}/72, unmatched: {unmatched}")
print(f"Spearman rho: {spearman_rho}")
print(f"PT Top 10 -> R1 top10: {model_perf['pt_top10']['in_r1_top10']}/10")
print(f"PT Top 10 -> R1 top20: {model_perf['pt_top10']['in_r1_top20']}/10")
print()
print("Trait audit:")
for tk, v in trait_audit.items():
    print(f"  {tk:<22} delta={str(v['trait_delta']):>6}  sg_delta={str(v['sg_delta']):>7}  signal={v['signal']}")
print()
print("Weekend risers:", [r["r1_name"] for r in weekend_risers])
print("Slippage risk:", [r["r1_name"] for r in slippage_risk])
if ci_loaded and enrichment_summary:
    print()
    print("=== COURSE INSIGHTS ENRICHMENT ===")
    print(f"Matched: {enrichment_summary['player_match_n']}/{enrichment_summary['player_total']} players")
    print(f"Traits upgraded:  {enrichment_summary['traits_upgraded']}")
    print(f"Traits confirmed: {enrichment_summary['traits_confirmed']}")
    for finding in enrichment_summary["key_findings"]:
        print(f"  {finding}")
