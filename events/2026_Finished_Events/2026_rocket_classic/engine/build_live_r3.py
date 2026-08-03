"""
build_live_r3.py — Rocket Classic 2026 R3 live-diagnostic builder.

Merges post-R3 leaderboard, three-round SG, per-round live stats, course-through-3-rounds
stats, R4 tee times, R4 weather (narrative prose, format differs from R3's), and the
event-local player ID crosswalk into one auditable live-state artifact. This is a
diagnostic overlay only — it never writes to, reorders, or reinterprets the canonical
pre-tournament event payload. Pre-event rank/tier are read-only inputs here.

Does NOT touch 2026_rocket_classic_r2_live.json (either copy) — that is a frozen R2
evidence snapshot. This builder writes a sibling *_r3_live.json artifact only.

Usage:
    python build_live_r3.py
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from live_builder_common import (
    HOURLY_RE_NARRATIVE,
    HOURLY_RE_STRICT,
    extract_hourly,
    format_score,
    normalize_name,
    read_csv_raw,
    summarize_hourly,
    to_int,
    to_num,
)

# ── Paths ──────────────────────────────────────────────────────────────────────

EVENT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = EVENT_DIR / "output"
DEPLOY_DATA_DIR = EVENT_DIR / "deploy" / "data"

PATHS = {
    "live_r1": OUTPUT_DIR / "round1" / "live_stats_r1_values.csv",
    "live_r2": OUTPUT_DIR / "round2" / "live_stats_r2_values.csv",
    "live_r3": OUTPUT_DIR / "round3" / "live_stats_r3_values.csv",
    "sg": OUTPUT_DIR / "round3" / "round3_player_strokes_gained.csv",
    "leaderboard": OUTPUT_DIR / "round3" / "round3_leaderboard.csv",
    "course_stats": OUTPUT_DIR / "round3" / "round3_course_stats.csv",
    "teetimes": OUTPUT_DIR / "round4" / "pga_field_r4_teetimes.csv",
    "weather": OUTPUT_DIR / "round4" / "detroit_golf_club_r4_weather_data_2026.json",
    "payload": EVENT_DIR / "deploy" / "data" / "2026_rocket_classic_event_payload.json",
    "crosswalk": EVENT_DIR / "input" / "rocket_classic_player_ID_source.csv",
    # Cut line is fixed once R2 finishes and never moves — read it from the R2
    # leaderboard (read-only reference; never written to) rather than
    # recomputing from R3 totals, which would drift every round.
    "r2_leaderboard_cut_ref": OUTPUT_DIR / "round2" / "round2_leaderboard.csv",
}

# Sibling artifact — 2026_rocket_classic_r2_live.json is never written to by this script.
OUT_PATHS = [
    OUTPUT_DIR / "2026_rocket_classic_r3_live.json",
    DEPLOY_DATA_DIR / "2026_rocket_classic_r3_live.json",
]

SOURCE_FILE_NAMES = [p.name for p in PATHS.values()]

PRE_EVENT_TIER_WATCH = {"T1", "T2"}

match_issues: list[dict] = []


def log_issue(source_file: str, raw_name: str, normalized_key_attempt: str | None, reason: str) -> None:
    match_issues.append(
        {
            "source_file": source_file,
            "raw_name": raw_name,
            "normalized_key_attempt": normalized_key_attempt,
            "reason": reason,
        }
    )


# normalize_name, read_csv_raw, to_num, to_int, format_score now live in
# live_builder_common.py (shared with build_live_r2.py). See that module for
# the diacritic-fold and cp1252-fallback rationale.


# ── Player ID crosswalk (event-local authoritative source; used as a secondary
#    identity cross-check alongside the name-token key, never as the sole join) ──


def load_crosswalk() -> dict[str, str]:
    by_key: dict[str, str] = {}
    with PATHS["crosswalk"].open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_name = (row.get("player_name") or "").strip()
            dg_id = (row.get("dg_id") or "").strip()
            if not raw_name or not dg_id:
                continue
            key, _display, _amateur = normalize_name(raw_name)
            by_key[key] = dg_id
    return by_key


def load_r2_cut_line() -> float | None:
    """Cut line score, read from the frozen R2 leaderboard (RANK,PLAYER,TOTAL,R1,R2,STROKES)."""
    header, rows = read_csv_raw(PATHS["r2_leaderboard_cut_ref"])
    totals = []
    for row in rows:
        if len(row) < 3:
            continue
        rank_raw = row[0].strip()
        if normalize_status(rank_raw) != "cut_survivor":
            continue
        rest = row[2:]
        if rest and re.fullmatch(r"\(a+\)", rest[0].strip(), re.IGNORECASE):
            continue  # amateur marker in TOTAL slot — total unknown, skip for cut-line purposes
        total = to_num(rest[0]) if rest else None
        if total is not None:
            totals.append(total)
    return max(totals) if totals else None


# ── Leaderboard (authoritative join spine + cut status) ─────────────────────
#
# round3_leaderboard.csv adds an R3 column vs round2_leaderboard.csv's schema:
# RANK,PLAYER,TOTAL,R1,R2,R3,STROKES (was RANK,PLAYER,TOTAL,R1,R2,STROKES).
# STROKES (raw strokes total) is parsed but intentionally not carried into the
# output — same precedent as the R2 builder, which also dropped it.


def normalize_status(rank_raw: str) -> str:
    r = rank_raw.strip().upper()
    if r == "CUT":
        return "missed_cut"
    if r == "WD":
        return "withdrew"
    if re.fullmatch(r"T?\d+", r):
        return "cut_survivor"
    return "unknown"


def parse_lb_position(rank_raw: str) -> tuple[int | None, bool, str]:
    r = rank_raw.strip().upper()
    if r in ("CUT", "WD"):
        return None, False, r
    is_tied = r.startswith("T")
    digits = r[1:] if is_tied else r
    try:
        return int(digits), is_tied, rank_raw.strip()
    except ValueError:
        return None, False, rank_raw.strip()


def load_leaderboard() -> list[dict]:
    header, rows = read_csv_raw(PATHS["leaderboard"])
    entries = []
    for row in rows:
        if len(row) < 3:
            log_issue("round3_leaderboard.csv", ",".join(row), None, "row_too_short")
            continue

        rank_raw, player_raw = row[0], row[1]
        rest = row[2:]

        amateur = False
        if rest and re.fullmatch(r"\(a+\)", rest[0].strip(), re.IGNORECASE):
            # Known data glitch (same as R2): amateur marker occupies the TOTAL slot
            # instead of being appended to the player name, dropping TOTAL entirely
            # and shifting R1/R2/R3/STROKES down by one.
            amateur = True
            log_issue(
                "round3_leaderboard.csv",
                player_raw,
                None,
                "amateur_marker_in_total_slot_total_unknown",
            )
            rest = rest[1:]
            total_raw = None
            r1_raw, r2_raw, r3_raw = (rest + ["", "", ""])[:3]
        else:
            rest = (rest + ["", "", "", ""])[:4]
            total_raw, r1_raw, r2_raw, r3_raw = rest

        key, display, name_amateur = normalize_name(player_raw)
        if amateur or name_amateur:
            amateur = True
            if not display.endswith("(a)"):
                display = f"{display} (a)"

        status_raw = rank_raw.strip()
        status = normalize_status(status_raw)
        lb_pos_numeric, lb_is_tied, lb_pos_display = parse_lb_position(status_raw)

        entries.append(
            {
                "lb_pos_raw": status_raw,
                "lb_pos_display": lb_pos_display,
                "lb_pos_numeric": lb_pos_numeric,
                "lb_is_tied": lb_is_tied,
                "status_raw": status_raw,
                "status": status,
                "player_name": display,
                "player_key": key,
                "total": to_num(total_raw),
                "r1": to_int(r1_raw),
                "r2": to_int(r2_raw),
                "r3": to_int(r3_raw),
                "amateur": amateur,
            }
        )
    return entries


# ── Strokes-gained (three-round cumulative; positional — verified by column-sum
#    check: OTT + APP + ARG + PUTT == SG Total, e.g. Davis Riley:
#    1.293 + 3.385 + 0.382 + 6.671 = 11.731). Same column order as the R2 source:
#    0 RANK, 1 Player, 2 TOT, 3 OTT val, 4 OTT rank-str, 5 APP val, 6 APP rank-str,
#    7 ARG val, 8 ARG rank-str, 9 PUTT val, 10 PUTT rank-str, 11 SG Total, 12 SG Total rank-str


def load_sg() -> dict[str, dict]:
    header, rows = read_csv_raw(PATHS["sg"])
    by_key: dict[str, dict] = {}
    for row in rows:
        if len(row) < 3:
            continue
        player_raw = row[1]
        key, _display, _amateur = normalize_name(player_raw)

        if re.fullmatch(r"\(a+\)", row[2].strip(), re.IGNORECASE):
            log_issue("round3_player_strokes_gained.csv", player_raw, key, "amateur_row_sg_values_unreliable_nulled")
            by_key[key] = {"sg_ott": None, "sg_app": None, "sg_arg": None, "sg_putt": None, "sg_total": None}
            continue

        row = (row + [""] * 13)[:13]
        sg_ott = to_num(row[3])
        sg_app = to_num(row[5])
        sg_arg = to_num(row[7])
        sg_putt = to_num(row[9])
        sg_total = to_num(row[11])
        by_key[key] = {"sg_ott": sg_ott, "sg_app": sg_app, "sg_arg": sg_arg, "sg_putt": sg_putt, "sg_total": sg_total}
    return by_key


# ── Per-round live stats (supplementary detail: position/score/thru plus
#    accuracy/gir/scrambling/distance) ──


def load_live_stats(path: Path, source_name: str) -> dict[str, dict]:
    by_key: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_name = (row.get("player_name") or "").strip()
            if not raw_name:
                continue
            key, _display, _amateur = normalize_name(raw_name)
            by_key[key] = {
                "position": row.get("position"),
                "score": to_num(row.get("score")),
                "thru": row.get("thru"),
                "today": to_num(row.get("today") or row.get("today (r1)")),
                "sg_total": to_num(row.get("sg_total")),
                "accuracy": to_num(row.get("accuracy")),
                "gir": to_num(row.get("gir")),
                "scrambling": to_num(row.get("scrambling")),
                "distance": to_num(row.get("distance")),
            }
    return by_key


# ── R4 tee times (next-round lookahead; source columns are r4_* — kept as r4_*
#    in the output too, unlike the R2 builder's r3_teetime/r3_wave, so the field
#    names stay truthful about which round they describe) ─────────────────────


def load_teetimes() -> list[dict]:
    entries = []
    with PATHS["teetimes"].open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_name = (row.get("player_name") or "").strip()
            if not raw_name:
                continue
            key, display, _amateur = normalize_name(raw_name)

            def clean(v):
                v = (v or "").strip()
                return None if v.lower() == "null" or v == "" else v

            entries.append(
                {
                    "player_key": key,
                    "player_name": display,
                    "r4_teetime": clean(row.get("r4_teetime")),
                    "r4_wave": clean(row.get("r4_wave")),
                    "r4_starthole": clean(row.get("r4_starthole")),
                    "matched_leaderboard": False,  # filled in after leaderboard is loaded
                }
            )
    return entries


# ── Course-through-3-rounds ──────────────────────────────────────────────────


def load_course_observations() -> dict:
    header, rows = read_csv_raw(PATHS["course_stats"])
    holes = []
    for row in rows:
        row = [c.strip('"') for c in row]
        if len(row) < 11:
            continue
        holes.append(
            {
                "hole": to_int(row[0]),
                "par": to_int(row[1]),
                "yards": to_int(row[2]),
                "avg": to_num(row[3]),
                "field_rank": to_int(row[4]),
                "plus_minus": to_num(row[5]),
                "eagles": to_int(row[6]),
                "birdies": to_int(row[7]),
                "pars": to_int(row[8]),
                "bogeys": to_int(row[9]),
                "dbl_plus": to_int(row[10]),
            }
        )

    def top(seq, key, n=3, reverse=True):
        return sorted(seq, key=key, reverse=reverse)[:n]

    return {
        "holes": holes,
        "easiest_holes": [h["hole"] for h in top(holes, lambda h: h["plus_minus"] or 0, reverse=False)],
        "hardest_holes": [h["hole"] for h in top(holes, lambda h: h["plus_minus"] or 0, reverse=True)],
        "birdie_heavy": [h["hole"] for h in top(holes, lambda h: (h["birdies"] or 0) + (h["eagles"] or 0))],
        "danger_holes": [h["hole"] for h in top(holes, lambda h: (h["dbl_plus"] or 0) + (h["bogeys"] or 0))],
    }


# ── R4 weather ────────────────────────────────────────────────────────────────
#
# The R3 weather source (used by build_live_r2.py) was clean per-hour lines:
#   "6 AM: 74°F, 7% precip, wind 3 mph ESE"
# The R4 source is full narrative prose — each hourly line still opens the same
# way but is followed by descriptive clauses before wind, plus a lengthy prose
# discussion section afterward:
#   "7 AM: 69°F, steady rain, precip ~71%, ~0.03 in/hr, wind 8 mph NE, humidity ~92%.
#    Expect wet turf, soft greens, ..."
# Two extraction tiers are attempted in order; only if both fail below the 80%
# threshold do we drop to raw-text-only (no fabricated hourly labels).
# HOURLY_RE_STRICT/NARRATIVE, extract_hourly, and summarize_hourly live in
# live_builder_common.py (shared with build_live_r2.py, which only ever needs
# the strict tier since its source is clean).


def parse_weather() -> dict:
    raw_text = PATHS["weather"].read_text(encoding="utf-8")
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    candidate_lines = [ln for ln in lines if "°F" in ln]

    hourly_strict, rate_strict = extract_hourly(HOURLY_RE_STRICT, candidate_lines)
    if candidate_lines and rate_strict >= 0.8:
        return summarize_hourly(hourly_strict, raw_text, "parsed", "hourly_clean_v1")

    hourly_narrative, rate_narrative = extract_hourly(HOURLY_RE_NARRATIVE, candidate_lines)
    if candidate_lines and rate_narrative >= 0.8:
        return summarize_hourly(hourly_narrative, raw_text, "parsed_narrative", "narrative_v1")

    log_issue(
        "detroit_golf_club_r4_weather_data_2026.json",
        "(weather forecast text)",
        None,
        f"weather_parse_rate_below_threshold_strict={rate_strict:.2f}_narrative={rate_narrative:.2f}",
    )
    return {"parse_status": "fallback_raw", "parse_method": "unparsed", "raw_text": raw_text}


# ── Pre-event model payload (read-only reference) ───────────────────────────


def load_model_reference() -> dict[str, dict]:
    with PATHS["payload"].open(encoding="utf-8") as f:
        payload = json.load(f)
    by_key: dict[str, dict] = {}
    for p in payload.get("players", []):
        raw_name = p.get("player_name") or ""
        if not raw_name:
            continue
        key, _display, _amateur = normalize_name(raw_name)
        by_key[key] = {"pre_event_rank": p.get("rank"), "pre_event_tier": p.get("tier")}
    return by_key


# ── Diagnostic tags (computed once here — not re-derived in JS) ────────────


def assign_tags(entry: dict, sg: dict, model: dict) -> list[str]:
    tags = []
    status = entry["status"]
    lb_pos = entry["lb_pos_numeric"]
    pre_event_tier = model.get("pre_event_tier")

    ott, app, arg, putt, total = sg.get("sg_ott"), sg.get("sg_app"), sg.get("sg_arg"), sg.get("sg_putt"), sg.get("sg_total")

    if total is not None and ott is not None and app is not None:
        if total > 0 and (ott > 0.5 or app > 0.5):
            tags.append("structurally_live")

    if status == "cut_survivor" and None not in (ott, app, arg, putt):
        if (ott + app) < 0 and (arg + putt) > 1.5:
            tags.append("surviving_short_game")
        if (ott + app) < -1.0:
            tags.append("fragile_survivor")

    if pre_event_tier in PRE_EVENT_TIER_WATCH and lb_pos is not None and lb_pos <= 20 and total is not None and total > 0:
        tags.append("model_vindication")

    if pre_event_tier in PRE_EVENT_TIER_WATCH and (
        status in ("missed_cut", "withdrew") or (lb_pos is not None and lb_pos > 50)
    ):
        tags.append("model_miss_watch")

    return tags


def assign_bucket(entry: dict, tags: list[str], model: dict) -> str:
    pre_event_tier = model.get("pre_event_tier")
    lb_pos = entry["lb_pos_numeric"]

    is_downgrade = "model_miss_watch" in tags or "fragile_survivor" in tags
    is_promotion = (
        lb_pos is not None
        and lb_pos <= 30
        and (
            ("structurally_live" in tags and pre_event_tier not in PRE_EVENT_TIER_WATCH)
            or "model_vindication" in tags
        )
    )

    if is_downgrade:
        return "downgrade_watch"
    if is_promotion:
        return "promotion_watch"
    return "hold"


PROJECTION_NOTE = {
    "promotion_watch": "Outperforming pre-event tier through R3 — model vindication signal heading into R4.",
    "downgrade_watch": "Trailing pre-event expectation through R3 — watch for a R4 correction.",
    "hold": "Tracking in line with pre-event model expectation through R3.",
}


# ── Build ─────────────────────────────────────────────────────────────────────


def build() -> dict:
    leaderboard = load_leaderboard()
    sg_by_key = load_sg()
    live_r1 = load_live_stats(PATHS["live_r1"], "live_stats_r1_values.csv")
    live_r2 = load_live_stats(PATHS["live_r2"], "live_stats_r2_values.csv")
    live_r3 = load_live_stats(PATHS["live_r3"], "live_stats_r3_values.csv")
    teetimes = load_teetimes()
    course_observations = load_course_observations()
    weather = parse_weather()
    model_by_key = load_model_reference()
    crosswalk_by_key = load_crosswalk()

    lb_keys = {e["player_key"] for e in leaderboard}
    teetime_by_key = {}
    for t in teetimes:
        t["matched_leaderboard"] = t["player_key"] in lb_keys
        if not t["matched_leaderboard"]:
            log_issue("pga_field_r4_teetimes.csv", t["player_name"], t["player_key"], "no_leaderboard_match")
        teetime_by_key[t["player_key"]] = t

    for key in sg_by_key:
        if key not in lb_keys:
            log_issue("round3_player_strokes_gained.csv", key, key, "sg_row_not_in_leaderboard")
    for key in live_r1:
        if key not in lb_keys:
            log_issue("live_stats_r1_values.csv", key, key, "live_stats_row_not_in_leaderboard")
    for key in live_r2:
        if key not in lb_keys:
            log_issue("live_stats_r2_values.csv", key, key, "live_stats_row_not_in_leaderboard")
    for key in live_r3:
        if key not in lb_keys:
            log_issue("live_stats_r3_values.csv", key, key, "live_stats_row_not_in_leaderboard")
    for key in model_by_key:
        if key not in lb_keys:
            log_issue("2026_rocket_classic_event_payload.json", key, key, "model_player_not_in_leaderboard")

    cut_survivors = []
    mechanism_pool = []
    venue_mechanism_tags: dict[str, list[str]] = {}
    buckets = {"promotion_watch": [], "hold": [], "downgrade_watch": []}

    for entry in leaderboard:
        key = entry["player_key"]
        sg = sg_by_key.get(key, {})
        model = model_by_key.get(key, {})
        player_id = crosswalk_by_key.get(key)
        if key not in sg_by_key:
            log_issue("round3_player_strokes_gained.csv", entry["player_name"], key, "no_sg_match_for_leaderboard_player")
        if player_id is None:
            log_issue("rocket_classic_player_ID_source.csv", entry["player_name"], key, "no_crosswalk_id_match")

        tags = assign_tags(entry, sg, model)
        if tags:
            venue_mechanism_tags[key] = tags

        if entry["status"] != "cut_survivor":
            continue

        pre_event_rank = model.get("pre_event_rank")
        rank_delta = (
            (pre_event_rank - entry["lb_pos_numeric"])
            if (pre_event_rank is not None and entry["lb_pos_numeric"] is not None)
            else None
        )
        tt = teetime_by_key.get(key, {})
        bucket = assign_bucket(entry, tags, model)

        record = {
            "player_key": key,
            "player_id": player_id,
            "player_name": entry["player_name"],
            "lb_pos_display": entry["lb_pos_display"],
            "lb_pos_numeric": entry["lb_pos_numeric"],
            "total": entry["total"],
            "r1": entry["r1"],
            "r2": entry["r2"],
            "r3": entry["r3"],
            "pre_event_rank": pre_event_rank,
            "pre_event_tier": model.get("pre_event_tier"),
            "rank_delta": rank_delta,
            "sg_ott": sg.get("sg_ott"),
            "sg_app": sg.get("sg_app"),
            "sg_arg": sg.get("sg_arg"),
            "sg_putt": sg.get("sg_putt"),
            "sg_total": sg.get("sg_total"),
            "r1_detail": live_r1.get(key),
            "r2_detail": live_r2.get(key),
            "r3_detail": live_r3.get(key),
            "r4_teetime": tt.get("r4_teetime"),
            "r4_wave": tt.get("r4_wave"),
            "diagnostic_label": tags[0] if tags else "unclassified",
            "live_round_delta_tag": bucket,
            "r4_structural_projection_note": PROJECTION_NOTE[bucket],
        }
        cut_survivors.append(record)
        buckets[bucket].append(key)

        if sg.get("sg_total") is not None:
            mechanism_pool.append(record)

    def leaders(metric_key, n=10):
        pool = [r for r in mechanism_pool if r[metric_key] is not None]
        pool.sort(key=lambda r: r[metric_key], reverse=True)
        return [
            {"player_key": r["player_key"], "player_name": r["player_name"], "lb_pos_display": r["lb_pos_display"], "value": r[metric_key]}
            for r in pool[:n]
        ]

    mechanism_leaders = {
        "sg_total": leaders("sg_total"),
        "sg_ott": leaders("sg_ott"),
        "sg_app": leaders("sg_app"),
        "sg_arg": leaders("sg_arg"),
        "sg_putt": leaders("sg_putt"),
    }

    cut_line_score = load_r2_cut_line()

    return {
        "event": {"name": "Rocket Classic", "course": "Detroit Golf Club", "year": 2026},
        "live_state": {
            "through_round": 3,
            "live_round": "R3",
            "next_round": "R4",
            "live_label": "Live: R3 Update",
            "cut_line_score": cut_line_score,
            "cut_line_display": format_score(cut_line_score),
            "players_through": sum(1 for e in leaderboard if e["status"] == "cut_survivor"),
            "players_cut": sum(1 for e in leaderboard if e["status"] == "missed_cut"),
            "players_wd": sum(1 for e in leaderboard if e["status"] == "withdrew"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_iteration": "update_r3",
            "source_files": SOURCE_FILE_NAMES,
        },
        "leaderboard": leaderboard,
        "cut_survivors": cut_survivors,
        "mechanism_leaders": mechanism_leaders,
        "venue_mechanism_tags": venue_mechanism_tags,
        "diagnostic_buckets": buckets,
        "course_observations": course_observations,
        "round4_weather": weather,
        "teetimes": teetimes,
        "match_issues": match_issues,
    }


def main() -> None:
    result = build()
    for out_path in OUT_PATHS:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"wrote {out_path}")

    ls = result["live_state"]
    print(
        f"through_round={ls['through_round']} cut_line={ls['cut_line_display']} "
        f"players_through={ls['players_through']} cut={ls['players_cut']} wd={ls['players_wd']} "
        f"match_issues={len(result['match_issues'])}"
    )


if __name__ == "__main__":
    main()
