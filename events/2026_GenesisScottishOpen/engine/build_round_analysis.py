"""
VenueDNA — 2026 Genesis Scottish Open
build_round_analysis.py

Compiles live round CSVs + pre-tournament payload into r{N}_analysis.json (schema v1.1).
Produces: trait_audit.app_150_200 node + live_lean_notes with no null entries.

Usage:
    python engine/build_round_analysis.py --round 1 --event_slug 2026_genesis_scottish_open
"""

import argparse
import csv
import json
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_PAYLOAD = ROOT / "deploy" / "data" / "event_payload.json"


# ─────────────────────────────────────────────
# NAME NORMALISATION
# ─────────────────────────────────────────────

def _strip_accents(name: str) -> str:
    nfd = unicodedata.normalize("NFD", name)
    out = "".join(c for c in nfd if not unicodedata.combining(c))
    for k, v in {"Ø": "O", "ø": "O", "Æ": "AE", "æ": "AE",
                  "Å": "A", "å": "A", "Ö": "O", "ö": "O",
                  "Ü": "U", "ü": "U", "Ñ": "N", "ñ": "N", "ß": "SS"}.items():
        out = out.replace(k, v)
    return out.upper()


def _alpha_only(s: str) -> str:
    return "".join(c for c in s if c.isalpha() or c == " ").strip()


def normalize(s: str) -> str:
    return _alpha_only(_strip_accents(str(s)))


def key_first_last(full_name: str) -> str:
    """'Tom Kim' or 'Si Woo Kim' → 'KIM|TOM' / 'KIM|SI WOO'"""
    parts = normalize(full_name).split()
    if not parts:
        return "|"
    if len(parts) == 1:
        return f"{parts[0]}|"
    return f"{parts[-1]}|{' '.join(parts[:-1])}"


def key_last_first(raw: str) -> str:
    """'Kim, Tom' → 'KIM|TOM'"""
    if "," in raw:
        last, first = raw.split(",", 1)
        return f"{normalize(last.strip())}|{normalize(first.strip())}"
    return f"{normalize(raw)}|"


def key_payload(p: dict) -> str:
    return f"{normalize(p.get('last_name', ''))}|{normalize(p.get('first_name', ''))}"


# ─────────────────────────────────────────────
# SAFE PARSERS
# ─────────────────────────────────────────────

def to_float(v, default: float = 0.0) -> float:
    try:
        s = str(v).strip()
        if s in ("", "null", "None", "N/A"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def to_int(v, default: int = 0) -> int:
    try:
        return int(str(v).strip().replace("+", ""))
    except (ValueError, TypeError):
        return default


def score_to_int(v) -> int:
    """'-5' → -5, 'E' → 0, '+3' → 3"""
    s = str(v).strip()
    if s in ("E", "EVEN", ""):
        return 0
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def pos_to_int(pos: str) -> int:
    try:
        return int(str(pos).replace("T", "").strip())
    except (ValueError, TypeError):
        return 999


# ─────────────────────────────────────────────
# CORE BUILD
# ─────────────────────────────────────────────

def build(round_num: int, event_slug: str) -> dict:
    round_key = f"round{round_num}"
    r_dir = ROOT / "output" / f"round{round_num}"

    # ── Pre-tournament payload ────────────────────────────────────
    with open(DEPLOY_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)

    pp_by_key = {key_payload(p): p for p in payload["players"]}

    # ── Live CSVs ─────────────────────────────────────────────────
    with open(r_dir / f"{round_key}_leaderboard.csv", encoding="utf-8") as f:
        lb_rows = list(csv.DictReader(f))

    with open(r_dir / f"{round_key}_player_strokes_gained.csv", encoding="utf-8") as f:
        sg_rows = list(csv.DictReader(f))
    sg_by_key = {key_first_last(r["Player"]): r for r in sg_rows}

    with open(r_dir / f"{round_key}_course_insights.csv", encoding="utf-8") as f:
        ci_rows = list(csv.DictReader(f))
    ci_by_key = {key_last_first(r["player_name"]): r for r in ci_rows}

    with open(r_dir / f"{round_key}_course_stats.csv", encoding="utf-8") as f:
        cs_rows = list(csv.DictReader(f))

    # ── Leaderboard ───────────────────────────────────────────────
    leaderboard = []
    for row in lb_rows:
        name = row["Player"]
        lkey = key_first_last(name)
        pp = pp_by_key.get(lkey, {})
        sg = sg_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        live_sg_ott = to_float(sg.get("sg-ott") or ci.get("sg_ott"))
        live_sg_app = to_float(sg.get("sg-app to green") or ci.get("sg_app"))
        live_sg_putt = to_float(sg.get("sg-putting") or ci.get("sg_putt"))
        live_sg_arg = to_float(ci.get("sg_arg"))
        live_sg_total = to_float(sg.get("sg-total") or ci.get("sg_total"))

        leaderboard.append({
            "position":            row["POS"],
            "player":              name,
            "player_key":          lkey,
            "score_r1":            score_to_int(row["R1"]),
            "strokes":             to_int(row.get("STROKES", "0")),
            "pre_tier":            int(pp["tier"]) if pp.get("tier") is not None else None,
            "pre_vts":             round(to_float(pp.get("vts_final")), 2) if pp else None,
            "scoring_band":        pp.get("scoring", {}).get("band") if pp else None,
            "pre_win_prob":        round(to_float(pp.get("win_prob")), 4) if pp else None,
            "pre_make_cut_prob":   round(to_float(pp.get("make_cut_prob")), 4) if pp else None,
            "live_sg_total":       round(live_sg_total, 3),
            "live_sg_ott":         round(live_sg_ott, 3),
            "live_sg_app":         round(live_sg_app, 3),
            "live_sg_putt":        round(live_sg_putt, 3),
            "live_sg_arg":         round(live_sg_arg, 3),
            "live_distance":       round(to_float(ci.get("distance")), 1),
            "live_accuracy":       round(to_float(ci.get("accuracy")), 4),
            "live_gir":            round(to_float(ci.get("gir")), 4),
        })

    # ── Course stats ──────────────────────────────────────────────
    holes = []
    for r in cs_rows:
        holes.append({
            "hole":      to_int(r["HOLE"]),
            "par":       to_int(r["PAR"]),
            "yards":     to_int(r["YARDS"]),
            "avg_score": round(to_float(r["AVG"]), 3),
            "vs_par":    round(to_float(r["+/-"]), 3),
            "eagles":    to_int(r.get("EAGLES", 0)),
            "birdies":   to_int(r.get("BIRDIES", 0)),
            "pars":      to_int(r.get("PARS", 0)),
            "bogeys":    to_int(r.get("BOGEYS", 0)),
            "dbl_plus":  to_int(r.get("DBL+", 0)),
        })

    hardest_holes = sorted(holes, key=lambda h: h["vs_par"], reverse=True)[:3]
    easiest_holes = sorted(holes, key=lambda h: h["vs_par"])[:3]
    field_vs_par_r1 = round(sum(h["vs_par"] for h in holes), 3)
    strokes_list = [to_int(r.get("STROKES", 0)) for r in lb_rows if r.get("STROKES")]
    field_avg_strokes = round(sum(strokes_list) / len(strokes_list), 2) if strokes_list else 70.0

    course_stats = {
        "holes": holes,
        "summary": {
            "field_vs_par_r1":   field_vs_par_r1,
            "field_avg_strokes": field_avg_strokes,
            "hardest_holes":     [{"hole": h["hole"], "vs_par": h["vs_par"]} for h in hardest_holes],
            "easiest_holes":     [{"hole": h["hole"], "vs_par": h["vs_par"]} for h in easiest_holes],
        },
    }

    # ── Trait Audit: app_150_200 ──────────────────────────────────
    # Compare pre-tournament 150-200 yd fairway approach value projection
    # against live R1 SG:APP as a proxy for zone confirmation.
    audit_rows = []
    for lb in lb_rows:
        name = lb["Player"]
        lkey = key_first_last(name)
        pp = pp_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        raw_pre = pp.get("app_150_200_value") if pp else None
        pre_val = to_float(raw_pre) if raw_pre is not None else 0.0
        has_pre_data = raw_pre is not None

        live_sg_app = to_float(ci.get("sg_app"))
        live_gir = to_float(ci.get("gir"))
        prox_raw = ci.get("prox_fw", "")
        live_prox_fw = to_float(prox_raw) if prox_raw not in ("", "null", "None") else 0.0

        delta = round(live_sg_app - pre_val, 3)

        if has_pre_data and pre_val > 1.5 and live_sg_app > 1.5:
            status = "CONFIRMING"
        elif has_pre_data and pre_val > 1.5 and live_sg_app <= 0.5:
            status = "DIVERGING"
        elif has_pre_data and pre_val <= 0.5 and live_sg_app > 1.5:
            status = "OUTPERFORMING"
        elif has_pre_data and pre_val <= -1.0 and live_sg_app <= 0.0:
            status = "AS_PROJECTED"
        else:
            status = "TRACKING"

        audit_rows.append({
            "player":              name,
            "position":            lb["POS"],
            "has_pre_data":        has_pre_data,
            "pre_app_150_200":     round(pre_val, 3),
            "live_sg_app":         round(live_sg_app, 3),
            "delta":               delta,
            "live_gir":            round(live_gir, 4),
            "live_prox_fw":        round(live_prox_fw, 2),
            "status":              status,
        })

    # Summary stats
    with_pre = [r for r in audit_rows if r["has_pre_data"]]
    avg_pre = round(sum(r["pre_app_150_200"] for r in with_pre) / len(with_pre), 3) if with_pre else 0.0
    avg_live = round(sum(r["live_sg_app"] for r in audit_rows) / len(audit_rows), 3) if audit_rows else 0.0
    status_counts = {}
    for r in audit_rows:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    top5_app = sorted(audit_rows, key=lambda r: r["live_sg_app"], reverse=True)[:5]
    bottom5_app = sorted(audit_rows, key=lambda r: r["live_sg_app"])[:5]

    trait_audit = {
        "app_150_200": {
            "description": (
                "Pre-tournament 150-200 yd fairway approach projection (app_150_200_value) "
                "vs live R1 SG:APP. Positive delta = outperforming projection."
            ),
            "field_summary": {
                "total_players_audited":    len(audit_rows),
                "players_with_pre_data":    len(with_pre),
                "avg_pre_app_150_200":      avg_pre,
                "avg_live_sg_app_r1":       avg_live,
                "status_distribution":      status_counts,
            },
            "top5_live_sg_app":    [{"player": r["player"], "position": r["position"],
                                      "live_sg_app": r["live_sg_app"], "status": r["status"]}
                                     for r in top5_app],
            "bottom5_live_sg_app": [{"player": r["player"], "position": r["position"],
                                      "live_sg_app": r["live_sg_app"], "status": r["status"]}
                                     for r in bottom5_app],
            "confirming":    [r for r in audit_rows if r["status"] == "CONFIRMING"],
            "diverging":     [r for r in audit_rows if r["status"] == "DIVERGING"],
            "outperforming": [r for r in audit_rows if r["status"] == "OUTPERFORMING"],
            "all_players":   audit_rows,
        }
    }

    # ── Live Lean Notes ───────────────────────────────────────────
    # One note per leaderboard player — no null entries.
    live_lean_notes = []

    for lb in lb_rows:
        name = lb["Player"]
        lkey = key_first_last(name)
        pos = lb["POS"]
        pos_num = pos_to_int(pos)
        score_r1 = score_to_int(lb["R1"])
        pp = pp_by_key.get(lkey, {})
        sg = sg_by_key.get(lkey, {})
        ci = ci_by_key.get(lkey, {})

        tier = int(pp["tier"]) if pp.get("tier") is not None else 5
        vts = round(to_float(pp.get("vts_final")), 2) if pp else 0.0
        band = pp.get("scoring", {}).get("band", "Unranked") if pp else "Unranked"

        live_sg_total = to_float(sg.get("sg-total") or ci.get("sg_total"))
        live_sg_ott = to_float(sg.get("sg-ott") or ci.get("sg_ott"))
        live_sg_app = to_float(sg.get("sg-app to green") or ci.get("sg_app"))
        live_sg_putt = to_float(sg.get("sg-putting") or ci.get("sg_putt"))

        # Identify strongest live weapon
        sg_map = {"OTT": live_sg_ott, "APP": live_sg_app, "PUTT": live_sg_putt}
        best_cat, best_val = max(sg_map.items(), key=lambda x: x[1])

        if tier <= 2 and pos_num <= 10:
            note = (f"T{tier} conviction confirming — SG:{best_cat} leading at "
                    f"{best_val:+.2f}, vying for weekend contention ({band})")
        elif tier <= 2 and pos_num <= 25:
            note = (f"T{tier} pick tracking inside cut window — SG:TOTAL {live_sg_total:+.2f}, "
                    f"{band} band holds; R2 pivot opportunity")
        elif tier <= 2 and pos_num <= 60:
            note = (f"T{tier} high-conviction pick lagging — SG:APP {live_sg_app:+.2f} below "
                    f"projection, {band} band at risk; watch R2 approach metrics")
        elif tier <= 2:
            note = (f"T{tier} selection struggling below cut line — SG:TOTAL {live_sg_total:+.2f}; "
                    f"R2 recovery required; pre-tournament conviction under pressure")
        elif tier == 3 and pos_num <= 10:
            note = (f"T3 mid-field entry exceeding pre-tournament ceiling — "
                    f"SG:TOTAL {live_sg_total:+.2f} / SG:{best_cat} {best_val:+.2f} driving surprise placement")
        elif tier == 3 and pos_num <= 30:
            note = (f"T3 value pick activating within expected range — "
                    f"SG:TOTAL {live_sg_total:+.2f}, {band} band confirming")
        elif tier >= 4 and pos_num <= 15:
            note = (f"Low-tier entry outperforming projection — "
                    f"SG:{best_cat} {best_val:+.2f} leading a {score_r1:+d} R1; tier breakout watch")
        elif pos_num <= 50:
            note = (f"Mid-pack positioning within {band} band projection — "
                    f"SG:TOTAL {live_sg_total:+.2f} tracking; no major drift from baseline")
        elif pos_num <= 80:
            note = (f"Below-average R1 — SG:TOTAL {live_sg_total:+.2f}; "
                    f"cut survival conditional on R2 correction in SG:{best_cat}")
        else:
            note = (f"Struggling toward cut line — SG:TOTAL {live_sg_total:+.2f} ({score_r1:+d}); "
                    f"R2 must improve SG:APP ({live_sg_app:+.2f}) to survive")

        live_lean_notes.append({
            "player":        name,
            "position":      pos,
            "score_r1":      score_r1,
            "pre_tier":      tier,
            "pre_vts":       vts,
            "scoring_band":  band,
            "live_sg_total": round(live_sg_total, 3),
            "live_sg_ott":   round(live_sg_ott, 3),
            "live_sg_app":   round(live_sg_app, 3),
            "live_sg_putt":  round(live_sg_putt, 3),
            "note":          note,
        })

    # ── Assemble output ───────────────────────────────────────────
    return {
        "schema_version": "1.1",
        "event_slug":     event_slug,
        "round":          round_num,
        "generated_date": date.today().isoformat(),
        "field_size":     len(lb_rows),
        "leaderboard":    leaderboard,
        "course_stats":   course_stats,
        "trait_audit":    trait_audit,
        "live_lean_notes": live_lean_notes,
    }


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate(doc: dict) -> list[str]:
    errors = []

    if doc.get("schema_version") != "1.1":
        errors.append(f"schema_version mismatch: {doc.get('schema_version')!r}")

    app_node = doc.get("trait_audit", {}).get("app_150_200")
    if not app_node:
        errors.append("trait_audit.app_150_200 node missing or empty")
    else:
        if not app_node.get("all_players"):
            errors.append("trait_audit.app_150_200.all_players is empty")
        if not app_node.get("field_summary"):
            errors.append("trait_audit.app_150_200.field_summary missing")

    notes = doc.get("live_lean_notes", [])
    if not notes:
        errors.append("live_lean_notes is empty")
    else:
        null_notes = [i for i, n in enumerate(notes) if n is None]
        if null_notes:
            errors.append(f"live_lean_notes has null entries at indices: {null_notes}")
        blank_notes = [n.get("player", "?") for n in notes if n and not n.get("note")]
        if blank_notes:
            errors.append(f"live_lean_notes entries missing note field: {blank_notes[:5]}")

    return errors


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--event_slug", type=str, required=True)
    args = ap.parse_args()

    print(f"Building R{args.round} analysis for {args.event_slug} …")

    doc = build(args.round, args.event_slug)

    out_path = ROOT / "output" / f"round{args.round}" / f"r{args.round}_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    print(f"Written: {out_path}")

    errors = validate(doc)
    if errors:
        print("\nVALIDATION FAILURES:")
        for e in errors:
            print(f"  ✗ {e}")
        raise SystemExit(1)

    print(f"\nVALIDATION PASSED")
    print(f"  schema_version : {doc['schema_version']}")
    print(f"  field_size     : {doc['field_size']}")
    print(f"  leaderboard    : {len(doc['leaderboard'])} entries")
    print(f"  live_lean_notes: {len(doc['live_lean_notes'])} entries (0 nulls)")
    app = doc['trait_audit']['app_150_200']
    print(f"  app_150_200    : {app['field_summary']['total_players_audited']} audited, "
          f"{app['field_summary']['players_with_pre_data']} with pre-data")
    print(f"  status dist    : {app['field_summary']['status_distribution']}")


if __name__ == "__main__":
    main()
