"""
VenueDNA 2026 U.S. Open — Brief + Risk Register Generator
Produces:
  2026_USOPEN_tier1_briefs.md
  2026_USOPEN_tier2_briefs.md
  2026_USOPEN_risk_register.csv
"""

import pandas as pd
import numpy as np

BASE    = r"C:\PGA_VenueDNA\events\2026_USOPEN"
IN_CSV  = f"{BASE}/2026_USOPEN_scored_field.csv"
OUT_T1  = f"{BASE}/2026_USOPEN_tier1_briefs.md"
OUT_T2  = f"{BASE}/2026_USOPEN_tier2_briefs.md"
OUT_REG = f"{BASE}/2026_USOPEN_risk_register.csv"

sf = pd.read_csv(IN_CSV)

def clean(val, fallback="none"):
    if pd.isna(val) or str(val).strip() in ("", "nan"):
        return fallback
    return str(val).strip()

def fmt_vts(v): return round(float(v), 1)
def fmt_win(v): return round(float(v) * 100, 1)
def fmt_sg(v):  return round(float(v), 2)
def fmt_idx(v): return round(float(v), 1)

def parse_secondary_driver(trait_label, primary):
    """Extract second driver from 'X + Y; weak Z' format."""
    try:
        drivers = trait_label.split(";")[0].split(" + ")
        for d in drivers:
            d = d.strip()
            if d != primary:
                return d
    except Exception:
        pass
    return None

def risk_classification(row):
    """
    Derive risk_type, risk_summary, impact, ceiling_note from trace fields.
    Returns dict.
    """
    ap    = clean(row["antipatternflags"])
    vfd   = float(row["venuefitdelta"])
    depth = clean(row["datadepthclass"])
    gate  = bool(row["recentformgateapplied"])
    prd   = clean(row["primary_trait_driver"])
    prisk = clean(row["primary_risk_trait"])
    debut = clean(row["debutclass"])
    fvn   = float(row["form_vs_neutralskill"]) if not pd.isna(row["form_vs_neutralskill"]) else 0.0
    ap_tot = float(row["antipatternpenaltytotal"])

    risk_types  = []
    summaries   = []
    impact      = "low"
    ceiling_note = ""

    # Anti-pattern driven structural risk
    if ap != "none":
        risk_types.append("structural")
        if "bomb_and_spray" in ap:
            summaries.append(f"Bomb-and-spray profile penalized hard in Shinnecock high-wind setup")
            impact = "high"
            ceiling_note = "Raw VTS ceiling capped by bomb-and-spray AP penalty; wind makes this worse"
        if "long_iron_liability" in ap:
            summaries.append(f"Long-iron liability dangerous on 200+ yd approach holes in sustained wind")
            impact = "high" if impact != "high" else "high"
        if "short_and_wild" in ap:
            summaries.append(f"Short-and-wild pattern structurally mismatched to long, exposed Shinnecock layout")
            impact = "high"
        if "weak_tight_runoff" in ap:
            summaries.append(f"Weak tight-runoff ARG amplifies damage on Shinnecock's run-off areas")
            impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))
        if "poor_lag_putting" in ap:
            summaries.append(f"Poor lag putting costly on large, undulating Shinnecock greens")

    # Venue fit direction risk
    if vfd < -5.0 and ap == "none":
        risk_types.append("structural")
        summaries.append(f"Strong neutral skill but negative venue fit delta ({vfd:+.1f} VTI); Shinnecock traits not primary strength")
        impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))
        ceiling_note = ceiling_note or "Venue mismatch limits ceiling relative to raw VTS"
    elif vfd < -3.0 and ap == "none":
        summaries.append(f"Slight Shinnecock fit drag (VFD {vfd:+.1f} VTI); neutral dominance carries score")

    # Form gate / variance risk
    if gate:
        risk_types.append("variance")
        summaries.append(f"Form gate applied: recent form materially trails 12m baseline")
        impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))
    elif abs(fvn) > 0.5:
        risk_types.append("variance")
        dir_str = "above" if fvn > 0 else "below"
        summaries.append(f"Form {dir_str} baseline ({fvn:+.2f} SG); trajectory watch pre-round")

    # Data depth / sample risk
    if depth in ("thin","medium"):
        risk_types.append("engine_sample")
        summaries.append(f"Only {depth} data sample; model confidence limited")
        impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))
        ceiling_note = ceiling_note or f"Thin sample: widen confidence interval on VTS estimate"

    # Debut risk
    if debut != "none":
        risk_types.append("engine_sample")
        summaries.append(f"Debut class {debut} at Shinnecock/comp level; venue exposure penalty baked in")
        impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))

    # Weather setup risk for players without wind tolerance
    if "WindTolerance" == prisk and not any(w in ap for w in ("bomb","short")):
        risk_types.append("weather_setup")
        summaries.append(f"Wind tolerance flagged as primary risk; highwind setup (Rds 1+3) most vulnerable")
        impact = max(impact, "medium", key=lambda x: ["low","medium","high"].index(x))

    # Default / clean profile
    if not summaries:
        risk_types.append("structural")
        summaries.append(f"Clean profile; primary structural risk is {prisk} gap vs field elite")
        impact = "low"

    # Ceiling note default
    if not ceiling_note:
        if impact == "low":
            ceiling_note = "VTS ceiling intact; no capping warranted"
        else:
            ceiling_note = f"Review ceiling if {prisk} continues as weak point under tournament pressure"

    risk_type_str = ";".join(sorted(set(risk_types))) if risk_types else "structural"
    summary_str   = "; ".join(summaries[:2])  # cap at 2 for column width
    return {
        "risk_type":               risk_type_str,
        "risk_summary":            summary_str,
        "impact_on_conviction":    impact,
        "ceiling_adjustment_note": ceiling_note,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1 BRIEFS
# ─────────────────────────────────────────────────────────────────────────────
t1 = sf[sf["tier"] == 1].sort_values("vtsfinal", ascending=False)

lines_t1 = [
    "# 2026 U.S. Open — Tier 1 Player Briefs",
    "",
    f"**Event:** 2026 U.S. Open | **Venue:** Shinnecock Hills GC | **Par:** 70 | **Yardage:** 7,440",
    f"**Weather class:** High Wind | **Tier 1 players:** {len(t1)}",
    "",
    "---",
    "",
]

for _, r in t1.iterrows():
    name       = clean(r["playername"])
    vts        = fmt_vts(r["vtsfinal"])
    win_pct    = fmt_win(r["winpct"])
    trait_lbl  = clean(r["trait_summary_label"], "—")
    ns_sg      = fmt_sg(r["neutralskillsg"])
    depth      = clean(r["datadepthclass"])
    conf       = clean(r["baselineconfidenceband"])
    vfd        = fmt_sg(r["venuefitdelta"])
    prd        = clean(r["primary_trait_driver"])
    prisk      = clean(r["primary_risk_trait"])
    fi         = fmt_idx(r["recentformindex"])
    fvn_sg     = fmt_sg(r["form_vs_neutralskill"]) if not pd.isna(r["form_vs_neutralskill"]) else 0.0
    gate_app   = bool(r["recentformgateapplied"])
    gate_rsn   = clean(r["recentformgate_reason"]) if gate_app else "none"
    debut_cls  = clean(r["debutclass"])
    ap_flags   = clean(r["antipatternflags"])
    health     = clean(r["healthgatestatus"])

    # secondary driver from trait label
    second_drv = parse_secondary_driver(trait_lbl, prd)
    support_str = f"with support from {second_drv}" if second_drv else "no secondary conflict"

    # venue fit direction narrative (-1.0 to +1.0 treated as venue-neutral)
    if vfd >= 1.5:
        venue_narrative = f"Shinnecock traits structurally confirm this player — {prd} and {second_drv or 'overall profile'} are a direct match."
    elif vfd >= -1.0:
        venue_narrative = f"Venue-neutral: strong neutral SG drives the tier position; Shinnecock fit delta ({vfd:+.1f} VTI) immaterial."
    elif vfd >= -3.5:
        venue_narrative = f"Slight Shinnecock venue drag (VFD {vfd:+.1f} VTI); overwhelming neutral SG depth absorbs the discount."
    else:
        venue_narrative = f"Meaningful negative venue fit delta ({vfd:+.1f} VTI); Tier 1 position sustained purely by elite neutral SG depth."

    # failure condition from primary risk and flags
    if ap_flags != "none":
        fail_str = f"Anti-pattern exposure ({ap_flags}) amplified by high-wind Rds 1+3; structural ceiling risk if conditions peak."
    elif prisk == "MajorGrind":
        fail_str = "Major-grind uncertainty in four-day attrition; if mental/execution wobble surfaces, tier fades mid-week."
    elif prisk == "APP_200+":
        fail_str = f"Long-iron approach liability under 25+ mph wind; score leaks on 200+ yd par-4 approaches in Rds 1+3."
    elif prisk == "APP_150-200":
        fail_str = f"Mid-iron precision gap under links wind; repeated approach misses in 150–200 yd range erodes scorecard."
    elif prisk == "APP_FlightCtrl":
        fail_str = "Flight control weakness exploited by variable Shinnecock wind directions; trajectory mismatches in Rds 1+3."
    elif prisk == "PUTT_LagCtrl":
        fail_str = "Poor lag putting on large Shinnecock greens generates consistent 3-putt exposure across all four rounds."
    else:
        fail_str = f"Primary failure vector is {prisk}; if that trait underperforms relative to model, tier slides toward Tier 2."

    lines_t1 += [
        f"### {name} — Tier 1 — VTS {vts}, Win {win_pct}%",
        "",
        f"- **Profile**: {trait_lbl}",
        f"- **Neutral skill**: {ns_sg} SG over last 12m ({depth} sample, {conf} confidence).",
        f"- **Shinnecock fit**: VenueFitDelta {vfd:+.1f} VTI; driven by {prd} {support_str}.",
        f"- **Form**: Recent form index {fi}; form vs baseline {fvn_sg:+.2f} SG; gate: {gate_rsn}.",
        f"- **Risks**: Debut class {debut_cls}, anti-patterns {ap_flags}, health {health}.",
        f"- **Conviction**: {venue_narrative}",
        f"- **Failure condition**: {fail_str}",
        "",
        "---",
        "",
    ]

with open(OUT_T1, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_t1))
print(f"Wrote Tier 1 briefs: {OUT_T1}  ({len(t1)} players)")


# ─────────────────────────────────────────────────────────────────────────────
# TIER 2 BRIEFS
# ─────────────────────────────────────────────────────────────────────────────
t2 = sf[sf["tier"] == 2].sort_values("vtsfinal", ascending=False)

lines_t2 = [
    "# 2026 U.S. Open — Tier 2 Player Briefs",
    "",
    f"**Event:** 2026 U.S. Open | **Venue:** Shinnecock Hills GC | **Par:** 70 | **Yardage:** 7,440",
    f"**Weather class:** High Wind | **Tier 2 players:** {len(t2)} | Path to win requires Tier-1 vulnerability + personal spike",
    "",
    "---",
    "",
]

for _, r in t2.iterrows():
    name      = clean(r["playername"])
    vts       = fmt_vts(r["vtsfinal"])
    win_pct   = fmt_win(r["winpct"])
    trait_lbl = clean(r["trait_summary_label"], "—")
    ns_sg     = fmt_sg(r["neutralskillsg"])
    depth     = clean(r["datadepthclass"])
    conf      = clean(r["baselineconfidenceband"])
    vfd       = fmt_sg(r["venuefitdelta"])
    prd       = clean(r["primary_trait_driver"])
    prisk     = clean(r["primary_risk_trait"])
    fi        = fmt_idx(r["recentformindex"])
    fvn_sg    = fmt_sg(r["form_vs_neutralskill"]) if not pd.isna(r["form_vs_neutralskill"]) else 0.0
    gate_app  = bool(r["recentformgateapplied"])
    gate_rsn  = clean(r["recentformgate_reason"]) if gate_app else "none"
    debut_cls = clean(r["debutclass"])
    ap_flags  = clean(r["antipatternflags"])
    health    = clean(r["healthgatestatus"])

    # missing piece from primary_risk_trait
    missing_map = {
        "APP_200+":       "long-iron precision under tournament wind",
        "APP_150-200":    "mid-iron execution in 150–200 yd wind window",
        "APP_FlightCtrl": "trajectory control in variable Shinnecock crosswinds",
        "PUTT_LagCtrl":   "lag-putting distance control on large greens",
        "MajorGrind":     "four-day major-pressure attrition",
        "ARG_TightRunoff":"tight-runoff scrambling around run-off zones",
        "ARG_Bunker":     "bunker play on Shinnecock's deep pot-style hazards",
        "WindTolerance":  "wind-tolerance in sustained 20+ mph setup",
        "OTT_Distance":   "distance gap vs Tier-1 field off the tee",
        "OTT_Accuracy":   "fairway-finding consistency in wind",
    }
    missing_piece = missing_map.get(prisk, prisk)

    # Path to win — tailored by primary driver + anti-patterns
    if vfd >= 5.0:
        path_str = (f"Above-average Shinnecock venue fit (VFD {vfd:+.1f} VTI) means any Tier-1 "
                    f"volatility week opens a real door; needs {prd} to fire at top-of-range and "
                    f"survive the {prisk} gap.")
    elif vfd >= 0:
        path_str = (f"Venue-neutral to slight positive; must spike {prd} to career-week level while "
                    f"mitigating {missing_piece} exposure — needs Tier-1 players to stumble in Rds 1+3 wind.")
    elif ap_flags != "none":
        path_str = (f"Anti-pattern flags ({ap_flags}) narrow the realistic ceiling; "
                    f"path to win requires atypically low wind Rds 1+3 and a top-decile {prd} spike "
                    f"to offset structural penalties.")
    else:
        path_str = (f"Neutral-to-negative venue fit (VFD {vfd:+.1f} VTI) means the route to beating Tier-1s "
                    f"is a hot form week in {prd} combined with Tier-1 field variance in Rds 1+3.")

    if gate_app:
        path_str += f" Form gate active — a form reversal in pre-event practice would be the first required trigger."

    # Failure condition
    if ap_flags != "none":
        fail_str = f"Anti-pattern penalties ({ap_flags}) are ceilings, not floors — if conditions peak (sustained 25+ mph), structural gaps widen further."
    elif prisk == "MajorGrind":
        fail_str = "If mental execution under Sunday major pressure fails, Tier-2 floor becomes Tier-3 result."
    elif prisk in ("APP_200+","APP_150-200"):
        fail_str = f"Round-3 Saturday wind (30+ mph gusts) is the specific vulnerability; long approach holes extract maximum damage."
    elif prisk == "PUTT_LagCtrl":
        fail_str = "Lag-putting breaks cause three-putt clusters that are unrecoverable on US Open scoring days."
    elif depth in ("thin","medium"):
        fail_str = f"Model confidence is {conf} ({depth} sample); surprise performance in either direction is elevated."
    else:
        fail_str = f"{missing_piece[0].upper() + missing_piece[1:]} gap surfaces under major pressure and Rds 1+3 wind — tier slips to Tier 3 if this trait bleeds."

    lines_t2 += [
        f"### {name} — Tier 2 — VTS {vts}, Win {win_pct}%",
        "",
        f"- **Profile**: {trait_lbl}",
        f"- **Neutral skill**: {ns_sg} SG over last 12m ({depth}, {conf} confidence).",
        f"- **Shinnecock fit**: VenueFitDelta {vfd:+.1f} VTI; strengths: {prd}; missing piece: {missing_piece}.",
        f"- **Form**: Recent form index {fi}; vs baseline {fvn_sg:+.2f} SG; gate: {gate_rsn}.",
        f"- **Risks**: Debut {debut_cls}, anti-patterns {ap_flags}, health {health}.",
        f"- **Path to win**: {path_str}",
        f"- **Failure condition**: {fail_str}",
        "",
        "---",
        "",
    ]

with open(OUT_T2, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_t2))
print(f"Wrote Tier 2 briefs: {OUT_T2}  ({len(t2)} players)")


# ─────────────────────────────────────────────────────────────────────────────
# RISK REGISTER — top 10 by vtsfinal (Tier 1 + top Tier 2)
# ─────────────────────────────────────────────────────────────────────────────
top10 = sf.nlargest(10, "vtsfinal").reset_index(drop=True)

reg_rows = []
for _, r in top10.iterrows():
    rc = risk_classification(r)
    reg_rows.append({
        "playername":              clean(r["playername"]),
        "tier":                    int(r["tier"]),
        "vtsfinal":                round(float(r["vtsfinal"]), 2),
        "winpct":                  round(float(r["winpct"]), 4),
        "primary_trait_driver":    clean(r["primary_trait_driver"]),
        "primary_risk_trait":      clean(r["primary_risk_trait"]),
        "antipatternflags":        clean(r["antipatternflags"]),
        "debutclass":              clean(r["debutclass"]),
        "recentformgateapplied":   bool(r["recentformgateapplied"]),
        "healthgatestatus":        clean(r["healthgatestatus"]),
        "risk_type":               rc["risk_type"],
        "risk_summary":            rc["risk_summary"],
        "impact_on_conviction":    rc["impact_on_conviction"],
        "ceiling_adjustment_note": rc["ceiling_adjustment_note"],
    })

reg_df = pd.DataFrame(reg_rows)
reg_df.to_csv(OUT_REG, index=False)
print(f"Wrote risk register: {OUT_REG}  ({len(reg_df)} rows)")
