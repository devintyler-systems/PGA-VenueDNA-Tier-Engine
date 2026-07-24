"""
apply_audit_corrections.py
Open Championship 2026 – Royal Birkdale
Applies 9 audit-correction rules to vts_full.csv, recomputes VTS for the
full 156-player field, and emits final_analysis.json (schema 3.1-pretournament).
"""

import csv
import json
import math
import os
import re

# ── paths ──────────────────────────────────────────────────────────────────
BASE     = r"C:\PGA_VenueDNA\events\2026_the_open_championship"
VTS_CSV  = os.path.join(BASE, "deploy", "data", "vts_full.csv")
SKL_CSV  = os.path.join(BASE, "input", "dg_skill_ratings.csv")
LK6_CSV  = os.path.join(BASE, "input", "dg_true_sg_links_courses", "dg_true_sg_links_6m.csv")
BK_CSV   = os.path.join(BASE, "input", "dg_true_sg_links_courses", "dg_true_sg_royal_birkdale_alltime.csv")
OUT_JSON = os.path.join(BASE, "deploy", "data", "final_analysis.json")

# ── weights ────────────────────────────────────────────────────────────────
W_NSI, W_VFS, W_VHN, W_FORM = 0.40, 0.30, 0.15, 0.15

# probability temperatures
TEMP_WIN   = 14.0
TEMP_TOP3  = 11.0
TEMP_TOP5  = 10.5
TEMP_TOP10 = 9.5
TEMP_TOP20 = 8.5
CUT_MID, CUT_SCALE = 48.0, 12.0


# ── helpers ────────────────────────────────────────────────────────────────
def flt(v, default=None):
    if v is None or str(v).strip() in ("", "null", "None", "nan"):
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def intt(v, default=None):
    f = flt(v)
    if f is None:
        return default
    return int(round(f))


def nkey(name: str) -> str:
    """Normalise 'First Last' or 'Last, First' (with optional quotes) → key."""
    name = name.strip().strip('"').strip("'")
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        name = parts[1] + " " + parts[0]
    name = re.sub(r"[^a-z0-9 ]", "", name.lower())
    return "_".join(name.split())


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_lookup(rows, key_col):
    out = {}
    for r in rows:
        k = nkey(r[key_col])
        out[k] = r
    return out


def assign_tier(vts):
    if vts >= 78.0: return "T1"
    if vts >= 63.5: return "T2"
    if vts >= 48.0: return "T3"
    if vts >= 33.0: return "T4"
    return "T5"


# ── probability computation ────────────────────────────────────────────────
def compute_probs(players_vts):
    """
    players_vts: list of (key, vts) in any order.
    Returns dict key → {win, top3, top5, top10, top20, make_cut, miss_cut}.
    """
    keys = [k for k, _ in players_vts]
    vals = [v for _, v in players_vts]

    def softmax_pct(T):
        raw = [math.exp(v / T) for v in vals]
        total = sum(raw)
        return [round(100.0 * r / total, 2) for r in raw]

    w   = softmax_pct(TEMP_WIN)
    t3  = softmax_pct(TEMP_TOP3)
    t5  = softmax_pct(TEMP_TOP5)
    t10 = softmax_pct(TEMP_TOP10)
    t20 = softmax_pct(TEMP_TOP20)

    result = {}
    for i, k in enumerate(keys):
        mcp = round(100.0 / (1.0 + math.exp(-(vals[i] - CUT_MID) / CUT_SCALE)), 1)
        result[k] = {
            "win":      w[i],
            "top3":     t3[i],
            "top5":     t5[i],
            "top10":    t10[i],
            "top20":    t20[i],
            "make_cut": mcp,
            "miss_cut": round(100.0 - mcp, 1),
        }
    return result


# ── audit penalty rules ────────────────────────────────────────────────────
RISK_DESC = {
    "R1": "PUTT regression — high-NSI player whose neutral skill is propped by non-transferable putting; links T2G weak",
    "R2": "Zero links evidence cap — no links or Birkdale rounds; modelled links_delta capped to ±1.5",
    "R3": "OTT-only links signal — OTT positive at GSO but APP collapsed; Birkdale's precision layout punishes this split",
    "R4": "Birkdale depth gate — thin Birkdale sample (<6 rounds) inflating VHN above neutral",
    "R5": "History vs current-form conflict — meaningful Birkdale history contradicted by catastrophic 6m links form",
    "R6": "Putting-led links total — positive GSO total driven by PUTT alone; T2G rank collapses without putter",
    "R7": "Links APP gate — below-threshold APP at links courses; Birkdale demands elite approach play inside 175 yds",
    "R8": "GSO 1.25x multiplier — already baked into base VTS by v3 engine; no additional adjustment applied",
    "R9": "Form spike unconfirmed — HOT/WARM form class not validated by links-course evidence",
}


def apply_penalties(row, skills, lk, bk):
    """
    Compute all 9 audit correction deltas.
    Returns dict: r1..r9 (floats), total (float, floor −15), flags (list[str]).
    """
    P = {f"r{i}": 0.0 for i in range(1, 10)}
    flags = []

    # pull base values
    cur_nsi     = flt(row.get("nsi"),       0.0)
    cur_vhn     = flt(row.get("vhn"),       50.0)
    cur_form    = flt(row.get("form"),       50.0)
    cur_rank    = intt(row.get("rank"),      999)
    cur_links_d = flt(row.get("vfs_links_d"), 0.0)
    form_cls    = row.get("form_class", "").strip().upper()

    # skills
    sg_putt_pred  = flt(skills.get("sg_putt_pred"))  if skills else None
    sg_total_pred = flt(skills.get("sg_total_pred")) if skills else None
    sg_app_pred   = flt(skills.get("sg_app_pred"))   if skills else None
    putt_share = 0.0
    if sg_putt_pred is not None and sg_total_pred and sg_total_pred > 0:
        putt_share = sg_putt_pred / sg_total_pred

    # links 6m
    if lk:
        l6_events     = intt(lk.get("events_played"), 0)
        l6_total      = flt(lk.get("total_mean"))
        l6_ott        = flt(lk.get("ott_mean"))
        l6_app        = flt(lk.get("app_mean"))
        db_total_rank = intt(lk.get("total_rank"))
        db_t2g_rank   = intt(lk.get("t2g_rank"))
        db_app_rank   = intt(lk.get("app_rank"))
        db_putt_rank  = intt(lk.get("putt_rank"))
    else:
        l6_events = 0
        l6_total = l6_ott = l6_app = None
        db_total_rank = db_t2g_rank = db_app_rank = db_putt_rank = None

    # birkdale
    if bk:
        bk_rounds = intt(bk.get("rounds_played"), 0)
        bk_total  = flt(bk.get("total_mean"))
    else:
        bk_rounds = 0
        bk_total  = None
    bk_events = intt(bk.get("events_played"), 0) if bk else 0

    # ── R1: PUTT regression ───────────────────────────────────────────────
    # Fires when high-NSI player's neutral skill is putt-dominated (>35%)
    # and links evidence does NOT confirm T2G competitiveness.
    if cur_nsi > 75 and putt_share > 0.35:
        if l6_events == 0:
            P["r1"] = -4.0
            flags.append("R1:PuttReg-NoLinks")
        elif db_t2g_rank is not None and db_t2g_rank > 30:
            P["r1"] = -4.0
            flags.append("R1:PuttReg-T2GWeak")
        elif db_putt_rank is not None and db_putt_rank > 25:
            P["r1"] = -2.0
            flags.append("R1:PuttReg-PuttUnconfirmed")
        # else: putt_rank ≤25 AND t2g_rank ≤30 → confirmed, no penalty

    # ── R2: Zero links evidence cap ───────────────────────────────────────
    # No links events AND no Birkdale history → any positive links_delta
    # beyond ±1.5 VFS is modelled fiction; claw back the excess.
    if l6_events == 0 and bk_events == 0:
        excess = max(0.0, cur_links_d - 1.5)
        P["r2"] = -round(excess * W_VFS, 3)
        if P["r2"] < 0:
            flags.append(f"R2:ZeroLinks-cap(links_d={cur_links_d:.2f})")

    # ── R3: OTT-only links penalty ────────────────────────────────────────
    # Positive links OTT signal but APP negative or rank >55 → Birkdale's
    # precision layout will expose this split; non-competitive without APP.
    if l6_events >= 1 and l6_ott is not None and l6_ott > 0:
        app_weak = (l6_app is None) or (l6_app < 0) or (db_app_rank is not None and db_app_rank > 55)
        if app_weak:
            P["r3"] = -5.0
            flags.append("R3:OTT-OnlyLinks")

    # ── R4: Birkdale depth gate ────────────────────────────────────────────
    # <6 rounds at Birkdale with a positive SG record → VHN overstates
    # confidence; cap the VHN lift above the 1-event neutral ceiling.
    if 0 < bk_rounds < 6 and bk_total is not None and bk_total > 0:
        if cur_vhn > 56.67:
            P["r4"] = -round(0.15 * (cur_vhn - 56.67), 3)
            flags.append(f"R4:DepthGate-vhn{cur_vhn:.1f}")

    # ── R5: History vs current-form conflict ──────────────────────────────
    # Solid Birkdale record (≥6 rounds) contradicted by catastrophic
    # 6m links total (rank >60) AND T2G collapse (rank >65) → 75% discount
    # to the VHN-above-neutral contribution.
    if (bk_rounds >= 6 and bk_total is not None and bk_total > 0
            and cur_vhn > 50):
        if (db_total_rank is not None and db_total_rank > 60
                and db_t2g_rank is not None and db_t2g_rank > 65):
            P["r5"] = -round(0.15 * 0.75 * (cur_vhn - 50.0), 3)
            flags.append(f"R5:HistVsForm-vhn{cur_vhn:.1f}")

    # ── R6: Putting-led links total ────────────────────────────────────────
    # Strong links PUTT rank (≤25) driving a positive links total, but T2G
    # rank is weak (>55) → links total is hollow; subtract ball-striking premium.
    if (l6_events >= 1
            and db_putt_rank is not None and db_putt_rank <= 25
            and db_t2g_rank  is not None and db_t2g_rank  > 55):
        P["r6"] = -3.0
        flags.append("R6:PuttLedLinks")

    # ── R7: Links APP gate (top-40 scrutiny) ──────────────────────────────
    # For players currently inside rank 40, sub-threshold APP at links
    # courses (rank >40 in DB) combined with mediocre DG APP pred (<0.60)
    # signals structural inability to score at Birkdale's demanding layout.
    if cur_rank <= 40:
        if (l6_events >= 1
                and db_app_rank is not None and db_app_rank > 40
                and sg_app_pred is not None and sg_app_pred < 0.60):
            P["r7"] = -2.5
            flags.append("R7:LinksAPP-Gate")
        elif (l6_events == 0
                and sg_app_pred is not None and sg_app_pred < 0.45):
            P["r7"] = -1.5
            flags.append("R7:LinksAPP-NoLinks")

    # ── R8: GSO 1.25x multiplier ──────────────────────────────────────────
    # Already baked into base VTS by score_open_2026_v3.py.
    # No additional adjustment; tracked for audit transparency only.
    P["r8"] = 0.0

    # ── R9: Form spike gate ────────────────────────────────────────────────
    # HOT/WARM form class for players outside top-25 not validated by
    # links-course performance → partial discount to the form contribution
    # above neutral.
    if form_cls in ("HOT", "WARM") and cur_rank > 25:
        no_links_confirm = (l6_events == 0 or
                            (db_total_rank is not None and db_total_rank > 50))
        if no_links_confirm:
            delta = W_FORM * 0.40 * max(0.0, cur_form - 50.0)
            P["r9"] = -round(delta, 3)
            if P["r9"] < 0:
                flags.append("R9:FormSpike-Unconfirmed")

    # ── aggregate (hard floor −15 to prevent stack overflow) ──────────────
    total = max(-15.0, sum(P[f"r{i}"] for i in range(1, 10)))
    P["total"] = round(total, 3)
    P["flags"] = flags
    return P


# ── narrative generators ────────────────────────────────────────────────────
def gen_badges(row, lk, bk):
    badges = []
    nsi      = flt(row.get("nsi"), 0.0)
    vfs      = flt(row.get("vfs"), 0.0)
    form_cls = row.get("form_class", "").strip().upper()
    bk_rds   = intt(bk.get("rounds_played"), 0) if bk else 0
    l6_ev    = intt(lk.get("events_played"), 0) if lk else 0

    if nsi >= 95:  badges.append("Elite NSI")
    elif nsi >= 85: badges.append("High NSI")

    if vfs >= 80:   badges.append("Iron Edge")
    elif vfs >= 70: badges.append("Links Ready")

    if bk_rds == 0:    badges.append("Debut Watch")
    elif bk_rds >= 8:  badges.append("Birkdale Vet")
    elif bk_rds >= 4:  badges.append("Birkdale Exp")

    if form_cls == "HOT":  badges.append("In Form")
    elif form_cls == "COLD": badges.append("Cold Spell")

    if l6_ev == 0: badges.append("No Links 6m")

    return badges[:5]


def gen_tier_reason(pen, tier, row, lk, bk):
    pt     = pen["total"]
    nsi    = flt(row.get("nsi"), 0.0)
    vfs    = flt(row.get("vfs"), 0.0)
    bk_rds = intt(bk.get("rounds_played"), 0) if bk else 0
    parts  = []

    if tier == "T1":   parts.append("elite combined skill and venue fit")
    elif tier == "T2": parts.append("credible links fit and strong neutral skill")
    elif tier == "T3": parts.append("mid-field projection with partial Birkdale alignment")
    else:              parts.append("below-threshold fit for Birkdale's demands")

    if pt <= -8:   parts.append(f"heavy audit correction ({pt:+.1f} VTS)")
    elif pt <= -4: parts.append(f"moderate audit adjustment ({pt:+.1f} VTS)")
    elif pt < 0:   parts.append(f"minor audit adjustment ({pt:+.1f} VTS)")

    if bk_rds >= 8: parts.append("meaningful Birkdale history")
    elif bk_rds == 0: parts.append("Royal Birkdale debut")

    if nsi >= 90: parts.append("elite neutral skill")

    return "; ".join(parts[:3])


def gen_thesis(name, vts_new, pen, row, skills, lk, bk):
    tier     = assign_tier(vts_new)
    pt       = pen["total"]
    l6_ev    = intt(lk.get("events_played"), 0) if lk else 0
    bk_rds   = intt(bk.get("rounds_played"), 0) if bk else 0
    sg_app   = flt(skills.get("sg_app_pred")) if skills else None
    sg_ott   = flt(skills.get("sg_ott_pred")) if skills else None
    l6_tot   = flt(lk.get("total_mean")) if lk else None
    l6_t_rk  = intt(lk.get("total_rank")) if lk else None

    sentences = []

    # lead
    if tier == "T1":
        sentences.append(f"{name} rates Tier 1 — elite skill profile aligns with Birkdale's ball-striking demands.")
    elif tier == "T2":
        sentences.append(f"{name} rates Tier 2 — legitimate top-10 threat with credible links fit.")
    elif tier == "T3":
        sentences.append(f"{name} rates Tier 3 — mid-field projection; needs ideal scoring conditions.")
    else:
        sentences.append(f"{name} rates Tier {tier[1]} — structural mismatches limit realistic contention.")

    # audit correction note
    if pt <= -5:
        sentences.append(f"Audit penalties ({pt:+.1f} VTS) reflect structural issues at links courses.")
    elif pt < -2:
        sentences.append(f"Audit corrections ({pt:+.1f} VTS) temper the initial model score.")

    # links evidence
    if l6_ev == 0:
        sentences.append("No links evidence in last 6 months — confidence limited to modelled skill.")
    elif l6_tot is not None:
        if l6_tot >= 2.0:
            sentences.append(f"GSO links form ({l6_tot:+.2f} SG/rd, rank {l6_t_rk}) is a compelling Birkdale signal.")
        elif l6_tot >= 0.5:
            sentences.append(f"GSO links form ({l6_tot:+.2f} SG/rd) provides modest confirmation.")
        elif l6_tot < -0.5:
            sentences.append(f"Negative GSO links form ({l6_tot:+.2f} SG/rd, rank {l6_t_rk}) is a structural red flag.")

    # Birkdale history
    if bk_rds >= 8:
        bk_tot = flt(bk.get("total_mean")) if bk else None
        if bk_tot and bk_tot > 1.0:
            sentences.append(f"Meaningful Birkdale history ({bk_rds}rds, {bk_tot:+.2f}/rd) adds venue credibility.")

    # APP/OTT profile
    if sg_app is not None and sg_ott is not None and sg_app > 0.5 and sg_ott > 0.3:
        sentences.append("APP+OTT profile suits Birkdale's precision layout.")

    return " ".join(sentences[:3])


def gen_links_note(lk):
    if not lk or intt(lk.get("events_played"), 0) == 0:
        return "No links course data in last 6 months."
    ev    = intt(lk.get("events_played"), 0)
    rds   = intt(lk.get("rounds_played"), 0)
    tot   = flt(lk.get("total_mean"))
    t_rk  = intt(lk.get("total_rank"))
    t2g   = flt(lk.get("t2g_mean"))
    app   = flt(lk.get("app_mean"))
    ott   = flt(lk.get("ott_mean"))
    putt  = flt(lk.get("putt_mean"))
    parts = [f"Links 6m ({ev}ev/{rds}rd): total {tot:+.2f}/rd (rank {t_rk})"]
    if t2g  is not None: parts.append(f"T2G {t2g:+.2f}")
    if app  is not None: parts.append(f"APP {app:+.2f}")
    if ott  is not None: parts.append(f"OTT {ott:+.2f}")
    if putt is not None: parts.append(f"PUTT {putt:+.2f}")
    return ", ".join(parts)


def gen_birkdale_note(bk):
    if not bk or intt(bk.get("rounds_played"), 0) == 0:
        return "Royal Birkdale debut — no prior SG data at this venue."
    ev    = intt(bk.get("events_played"), 0)
    rds   = intt(bk.get("rounds_played"), 0)
    tot   = flt(bk.get("total_mean"))
    t_rk  = intt(bk.get("total_rank"))
    t_str = f"{tot:+.3f}/rd (rank {t_rk})" if tot is not None else "n/a"
    return f"Birkdale all-time ({ev}ev/{rds}rds): total {t_str}."


# ── main ───────────────────────────────────────────────────────────────────
def main():
    print("Loading CSVs…")
    base_rows = load_csv(VTS_CSV)
    skl_lkp   = build_lookup(load_csv(SKL_CSV),  "player_name")
    lk6_lkp   = build_lookup(load_csv(LK6_CSV),  "player_name")
    bk_lkp    = build_lookup(load_csv(BK_CSV),   "player_name")

    print(f"  vts_full: {len(base_rows)} players")
    print(f"  skills:   {len(skl_lkp)} entries")
    print(f"  links6m:  {len(lk6_lkp)} entries")
    print(f"  birkdale: {len(bk_lkp)} entries")

    # ── pass 1: apply corrections ─────────────────────────────────────────
    corrected = []
    for row in base_rows:
        k       = nkey(row["player_name"])
        skills  = skl_lkp.get(k)
        lk      = lk6_lkp.get(k)
        bk      = bk_lkp.get(k)

        cur_vts = flt(row.get("vts_final"), 0.0)
        pen     = apply_penalties(row, skills, lk, bk)

        pre_penalty_vts = cur_vts            # v3 engine already has GSO 1.25x
        vts_new         = round(max(10.0, pre_penalty_vts + pen["total"]), 2)

        corrected.append({
            "_key":    k,
            "_name":   row["player_name"],
            "_pre":    round(pre_penalty_vts, 2),
            "_pen":    pen,
            "_vts":    vts_new,
            "_tier":   assign_tier(vts_new),
            "_row":    row,
            "_skills": skills,
            "_lk":     lk,
            "_bk":     bk,
        })

    # ── pass 2: re-rank and compute softmax probs ─────────────────────────
    corrected.sort(key=lambda x: x["_vts"], reverse=True)
    probs = compute_probs([(p["_key"], p["_vts"]) for p in corrected])

    # ── pass 3: build JSON output ─────────────────────────────────────────
    tier_lists = {"T1": [], "T2": [], "T3": [], "T4": [], "T5": []}

    for rank_idx, p in enumerate(corrected, 1):
        k       = p["_key"]
        row     = p["_row"]
        skills  = p["_skills"]
        lk      = p["_lk"]
        bk      = p["_bk"]
        pen     = p["_pen"]
        vts_new = p["_vts"]
        tier    = p["_tier"]
        name    = p["_name"]
        pr      = probs[k]

        # venue history delta: VHN contribution above/below neutral (0.15 weight)
        vhn_raw        = flt(row.get("vhn"), 50.0)
        venue_hist_d   = round((vhn_raw - 50.0) * W_VHN, 3)

        entry = {
            "rank":            rank_idx,
            "playerName":      name,
            "tier":            tier,
            "vtsFinal":        vts_new,
            "prePenaltyVts":   p["_pre"],
            "penaltiesTotal":  pen["total"],
            "penaltyR1":       pen["r1"],
            "penaltyR2":       pen["r2"],
            "penaltyR3":       pen["r3"],
            "penaltyR4":       pen["r4"],
            "penaltyR5":       pen["r5"],
            "penaltyR6":       pen["r6"],
            "penaltyR7":       pen["r7"],
            "penaltyR8":       pen["r8"],
            "penaltyR9":       pen["r9"],
            "neutralSkillIndex":  round(flt(row.get("nsi"),      0.0), 2),
            "venueFitScore":      round(flt(row.get("vfs"),      0.0), 2),
            "vfsBase":            round(flt(row.get("vfs_base"), 0.0), 2),
            "vfsLinksDelta":      round(flt(row.get("vfs_links_d"), 0.0), 2),
            "vhn":                round(vhn_raw, 2),
            "venueHistoryDelta":  venue_hist_d,
            "form":               round(flt(row.get("form"), 50.0), 2),
            "birkdaleTag":        row.get("birkdale_tag", "").strip(),
            "formClass":          row.get("form_class", "").strip(),
            "riskFlags":          pen["flags"],
            "tierReason":         gen_tier_reason(pen, tier, row, lk, bk),
            "winPct":             pr["win"],
            "top3Pct":            pr["top3"],
            "top5Pct":            pr["top5"],
            "top10Pct":           pr["top10"],
            "top20Pct":           pr["top20"],
            "makeCutPct":         pr["make_cut"],
            "missCutPct":         pr["miss_cut"],
            "badges":             gen_badges(row, lk, bk),
            "bettingPath":        row.get("best_bet", "").strip(),
            "thesis":             gen_thesis(name, vts_new, pen, row, skills, lk, bk),
            "linksNote":          gen_links_note(lk),
            "birkdaleNote":       gen_birkdale_note(bk),
        }
        tier_lists[tier].append(entry)

    # ── field summary ─────────────────────────────────────────────────────
    field_summary = {
        "totalPlayers": len(corrected),
        "tierCounts":   {t: len(tier_lists[t]) for t in ("T1","T2","T3","T4","T5")},
        "thresholds":   {"T1": 78.0, "T2": 63.5, "T3": 48.0, "T4": 33.0},
        "auditRules": {
            "R1": "PUTT regression (−4.0 or −2.0 VTS)",
            "R2": "Zero links cap on modelled links_delta (−W_VFS × excess)",
            "R3": "OTT-only links signal (−5.0 VTS)",
            "R4": "Birkdale depth gate <6 rounds (−0.15×excess_vhn)",
            "R5": "History vs current-form conflict 75% discount (−0.15×0.75×(vhn−50))",
            "R6": "Putting-led links total (−3.0 VTS)",
            "R7": "Links APP gate top-40 (−2.5 or −1.5 VTS)",
            "R8": "GSO 1.25x multiplier (0.0 — already in base)",
            "R9": "Form spike gate unconfirmed (−W_FORM×0.40×(form−50))",
        },
    }

    # ── risk register ─────────────────────────────────────────────────────
    all_entries = [e for t in tier_lists.values() for e in t]
    risk_register = []
    for rnum in range(1, 10):
        prefix  = f"R{rnum}:"
        hit_players = [e["playerName"] for e in all_entries
                       if any(f.startswith(prefix) for f in e["riskFlags"])]
        if hit_players:
            risk_register.append({
                "rule":            f"R{rnum}",
                "description":     RISK_DESC[f"R{rnum}"],
                "affectedCount":   len(hit_players),
                "affectedPlayers": hit_players,
            })

    # ── assemble output ────────────────────────────────────────────────────
    output = {
        "schemaVersion": "3.1-pretournament",
        "event":         "2026 The Open Championship",
        "venue":         "Royal Birkdale, Southport, England",
        "par":           70,
        "generatedAt":   "2026-07-15",
        "engine":        "VenueDNA Tier Engine v3 + Audit Corrections (9 rules)",
        "fieldSummary":  field_summary,
        "riskRegister":  risk_register,
        "tierLists":     tier_lists,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ── console report ────────────────────────────────────────────────────
    print(f"\nWritten: {OUT_JSON}")
    counts = field_summary["tierCounts"]
    print(f"Field: {field_summary['totalPlayers']} players  "
          f"T1:{counts['T1']}  T2:{counts['T2']}  T3:{counts['T3']}  "
          f"T4:{counts['T4']}  T5:{counts['T5']}")

    print("\n-- TOP 35 after audit corrections --")
    header = f"{'Rk':>3}  {'Player':<24} {'Tier':>4}  {'VTSf':>6}  {'Pre':>6}  {'Pen':>6}  Flags"
    print(header)
    print("-" * 90)
    for e in all_entries[:35]:
        flags_str = "|".join(e["riskFlags"]) if e["riskFlags"] else "—"
        print(f"{e['rank']:>3}. {e['playerName']:<24} {e['tier']:>4}  "
              f"{e['vtsFinal']:>6.2f}  {e['prePenaltyVts']:>6.2f}  "
              f"{e['penaltiesTotal']:>+6.1f}  {flags_str}")

    print("\n-- Tier 1 probabilities --")
    for e in tier_lists["T1"]:
        print(f"  {e['rank']:>3}. {e['playerName']:<24}  "
              f"win={e['winPct']:.2f}%  top5={e['top5Pct']:.1f}%  "
              f"top10={e['top10Pct']:.1f}%  cut={e['makeCutPct']:.0f}%")

    print("\n-- Risk register --")
    for r in risk_register:
        players_str = ", ".join(r["affectedPlayers"][:8])
        suffix = f"…+{len(r['affectedPlayers'])-8}" if len(r["affectedPlayers"]) > 8 else ""
        print(f"  {r['rule']} ({r['affectedCount']} players): {players_str}{suffix}")

    return output


if __name__ == "__main__":
    main()
