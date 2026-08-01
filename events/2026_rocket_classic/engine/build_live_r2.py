"""
build_live_r2.py — Rocket Classic 2026 R2 live-diagnostic builder.

Merges post-R2 leaderboard, two-round SG, per-round live stats, course-through-2-rounds
stats, R3 tee times, and R3 weather (prose, not real JSON) into one auditable live-state
artifact. This is a diagnostic overlay only — it never writes to, reorders, or reinterprets
the canonical pre-tournament event payload. Pre-event rank/tier are read-only inputs here.

Usage:
    python build_live_r2.py
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

EVENT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = EVENT_DIR / "output"
DEPLOY_DATA_DIR = EVENT_DIR / "deploy" / "data"

PATHS = {
    "live_r1": OUTPUT_DIR / "round1" / "live_stats_r1_values.csv",
    "live_r2": OUTPUT_DIR / "round2" / "live_stats_r2_values.csv",
    "sg": OUTPUT_DIR / "round2" / "round1_round2_player_strokes_gained.csv",
    "leaderboard": OUTPUT_DIR / "round2" / "round2_leaderboard.csv",
    "course_stats": OUTPUT_DIR / "round2" / "round2_course_stats.csv",
    "teetimes": OUTPUT_DIR / "round3" / "pga_field_r3_teetimes.csv",
    "weather": OUTPUT_DIR / "round3" / "detroit_golf_club_r3_weather_data_2026.json",
    "payload": EVENT_DIR / "deploy" / "data" / "2026_rocket_classic_event_payload.json",
}

OUT_PATHS = [
    OUTPUT_DIR / "2026_rocket_classic_r2_live.json",
    DEPLOY_DATA_DIR / "2026_rocket_classic_r2_live.json",
]

SOURCE_FILE_NAMES = [p.name for p in PATHS.values()]

MODEL_TIER_WATCH = {"T1", "T2"}
AMATEUR_RE = re.compile(r"\(a+\)\s*$", re.IGNORECASE)
NAME_TOKEN_RE = re.compile(r"[A-Za-z]+")
SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}

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


# ── Name normalization ───────────────────────────────────────────────────────
#
# Sources mix "Last, First" (event_payload, live_stats, teetimes) and "First Last"
# (leaderboard, SG csv) formats, and some surnames are multi-token ("Van Rooyen",
# "van Rooyen"). A strict first|last split breaks on those (order differs by source),
# so the key is built from the sorted set of cleaned name tokens instead — order- and
# format-invariant, still deterministic and auditable.


def normalize_name(raw: str) -> tuple[str, str, bool]:
    """Return (player_key, display_name, amateur_flag) for a raw name string."""
    raw = (raw or "").strip()
    amateur = False
    m = AMATEUR_RE.search(raw)
    if m:
        amateur = True
        raw = raw[: m.start()].strip().rstrip(",").strip()

    if "," in raw:
        last_part, _, first_part = raw.partition(",")
        display = f"{first_part.strip()} {last_part.strip()}".strip()
    else:
        display = raw

    tokens = [t.lower() for t in NAME_TOKEN_RE.findall(raw)]
    tokens = [t for t in tokens if t not in SUFFIX_TOKENS]
    tokens.sort()
    key = "|".join(tokens)

    if amateur:
        display = f"{display} (a)"
    return key, display, amateur


# ── CSV loading (positional access — some source headers are unreliable) ───────


def read_csv_raw(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader]
    if not rows:
        return [], []
    header = rows[0]
    data = [r for r in rows[1:] if any(cell.strip() for cell in r)]
    return header, data


def to_num(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip()
    if raw in ("", "-", "null", "None"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def to_int(raw: str | None) -> int | None:
    val = to_num(raw)
    return int(val) if val is not None else None


def format_score(score: float | None) -> str:
    if score is None:
        return "-"
    score = int(score)
    if score == 0:
        return "E"
    return f"+{score}" if score > 0 else str(score)


# ── Leaderboard (authoritative join spine + cut status) ─────────────────────


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
            log_issue("round2_leaderboard.csv", ",".join(row), None, "row_too_short")
            continue

        rank_raw, player_raw = row[0], row[1]
        rest = row[2:]

        amateur = False
        if rest and re.fullmatch(r"\(a+\)", rest[0].strip(), re.IGNORECASE):
            # Known data glitch: amateur marker occupies the TOTAL slot instead of
            # being appended to the player name, dropping TOTAL entirely.
            amateur = True
            log_issue(
                "round2_leaderboard.csv",
                player_raw,
                None,
                "amateur_marker_in_total_slot_total_unknown",
            )
            rest = rest[1:]
            total_raw = None
            r1_raw, r2_raw = (rest + ["", ""])[:2]
        else:
            rest = (rest + ["", "", ""])[:3]
            total_raw, r1_raw, r2_raw = rest

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
                "amateur": amateur,
            }
        )
    return entries


# ── Strokes-gained (two-round cumulative; positional — header labels are
#    off-by-one for the SG-Off-the-Tee column in this source file) ─────────
#
# Verified by column-sum check: OTT + APP + ARG + PUTT == SG Total for clean rows
# (e.g. Cameron Young: 2.52 + 3.593 + 1.044 + 1.232 = 8.389). Column order:
# 0 RANK, 1 Player, 2 TOTAL, 3 OTT val, 4 OTT rank-str, 5 APP val, 6 APP rank-str,
# 7 ARG val, 8 ARG rank-str, 9 PUTT val, 10 PUTT rank-str, 11 SG Total, 12 SG Total rank-str


def load_sg() -> dict[str, dict]:
    header, rows = read_csv_raw(PATHS["sg"])
    by_key: dict[str, dict] = {}
    for row in rows:
        if len(row) < 3:
            continue
        player_raw = row[1]
        key, _display, _amateur = normalize_name(player_raw)

        if re.fullmatch(r"\(a+\)", row[2].strip(), re.IGNORECASE):
            log_issue("round1_round2_player_strokes_gained.csv", player_raw, key, "amateur_row_sg_values_unreliable_nulled")
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


# ── Per-round live stats (supplementary detail: accuracy/gir/scrambling/distance) ──


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
                "today": to_num(row.get("today") or row.get("today (r1)")),
                "sg_total": to_num(row.get("sg_total")),
                "accuracy": to_num(row.get("accuracy")),
                "gir": to_num(row.get("gir")),
                "scrambling": to_num(row.get("scrambling")),
                "distance": to_num(row.get("distance")),
            }
    return by_key


# ── R3 tee times ─────────────────────────────────────────────────────────────


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
                    "r3_teetime": clean(row.get("r3_teetime")),
                    "r3_wave": clean(row.get("r3_wave")),
                    "r3_starthole": clean(row.get("r3_starthole")),
                    "matched_leaderboard": False,  # filled in after leaderboard is loaded
                }
            )
    return entries


# ── Course-through-2-rounds ──────────────────────────────────────────────────


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


# ── R3 weather (prose text with a regular per-hour pattern, not real JSON) ──

HOURLY_RE = re.compile(
    r"^(\d{1,2}\s(?:AM|PM)):\s(\d+)°F,\s(\d+)% precip,\swind\s(\d+)\smph\s([A-Z]+)$"
)
TEE_WINDOW_RE = re.compile(r"(\d{1,2}:\d{2}\s?[AP]M\s?[–-]\s?\d{1,2}:\d{2}\s?[AP]M)")


def hour_to_24(time_label: str) -> int:
    h, period = time_label.split(" ")
    h = int(h)
    if period == "AM":
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12


def parse_weather() -> dict:
    raw_text = PATHS["weather"].read_text(encoding="utf-8")
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    candidate_lines = [ln for ln in lines if "°F" in ln]
    hourly = []
    for ln in candidate_lines:
        m = HOURLY_RE.match(ln)
        if not m:
            continue
        time_label, temp, precip, wind, wind_dir = m.groups()
        hourly.append(
            {
                "time_label": time_label,
                "hour_24": hour_to_24(time_label),
                "temp_f": int(temp),
                "precip_pct": int(precip),
                "wind_mph": int(wind),
                "wind_dir": wind_dir,
            }
        )

    parse_rate = (len(hourly) / len(candidate_lines)) if candidate_lines else 0.0

    if not candidate_lines or parse_rate < 0.8:
        log_issue(
            "detroit_golf_club_r3_weather_data_2026.json",
            "(weather forecast text)",
            None,
            f"weather_parse_rate_below_threshold_{parse_rate:.2f}",
        )
        return {"parse_status": "fallback_raw", "raw_text": raw_text}

    temps = [h["temp_f"] for h in hourly]
    winds = [h["wind_mph"] for h in hourly]
    precips = [h["precip_pct"] for h in hourly]

    dir_counts: dict[str, int] = {}
    for h in hourly:
        dir_counts[h["wind_dir"]] = dir_counts.get(h["wind_dir"], 0) + 1
    max_count = max(dir_counts.values())
    dominant_wind_dirs = sorted([d for d, c in dir_counts.items() if c == max_count])

    def window_summary(entries):
        if not entries:
            return None
        t = [e["temp_f"] for e in entries]
        w = [e["wind_mph"] for e in entries]
        p = [e["precip_pct"] for e in entries]
        return f"{min(t)}–{max(t)}°F, wind {min(w)}–{max(w)} mph, precip {min(p)}–{max(p)}%"

    early = [h for h in hourly if 6 <= h["hour_24"] <= 10]
    late = [h for h in hourly if 11 <= h["hour_24"] <= 17]

    max_precip = max(precips)
    risk_label = "low" if max_precip < 20 else ("moderate" if max_precip < 40 else "high")

    tee_window_match = TEE_WINDOW_RE.search(raw_text)

    return {
        "parse_status": "parsed",
        "raw_text": raw_text,
        "hourly": hourly,
        "temp_range_f": [min(temps), max(temps)],
        "wind_range_mph": [min(winds), max(winds)],
        "precip_range_pct": [min(precips), max(precips)],
        "max_precip_pct": max_precip,
        "dominant_wind_dirs": dominant_wind_dirs,
        "risk_label": risk_label,
        "early_window_summary": window_summary(early),
        "late_window_summary": window_summary(late),
        "tee_time_window_summary": tee_window_match.group(1) if tee_window_match else None,
    }


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
        by_key[key] = {"model_rank": p.get("rank"), "model_tier": p.get("tier")}
    return by_key


# ── Diagnostic tags (computed once here — not re-derived in JS) ────────────


def assign_tags(entry: dict, sg: dict, model: dict) -> list[str]:
    tags = []
    status = entry["status"]
    lb_pos = entry["lb_pos_numeric"]
    model_tier = model.get("model_tier")

    ott, app, arg, putt, total = sg.get("sg_ott"), sg.get("sg_app"), sg.get("sg_arg"), sg.get("sg_putt"), sg.get("sg_total")

    if total is not None and ott is not None and app is not None:
        if total > 0 and (ott > 0.5 or app > 0.5):
            tags.append("structurally_live")

    if status == "cut_survivor" and None not in (ott, app, arg, putt):
        if (ott + app) < 0 and (arg + putt) > 1.5:
            tags.append("surviving_short_game")
        if (ott + app) < -1.0:
            tags.append("fragile_survivor")

    if model_tier in MODEL_TIER_WATCH and lb_pos is not None and lb_pos <= 20 and total is not None and total > 0:
        tags.append("model_vindication")

    if model_tier in MODEL_TIER_WATCH and (
        status in ("missed_cut", "withdrew") or (lb_pos is not None and lb_pos > 50)
    ):
        tags.append("model_miss_watch")

    return tags


def assign_bucket(entry: dict, tags: list[str], model: dict) -> str | None:
    if entry["status"] != "cut_survivor":
        return None
    model_tier = model.get("model_tier")
    lb_pos = entry["lb_pos_numeric"]

    is_downgrade = "model_miss_watch" in tags or "fragile_survivor" in tags
    is_promotion = (
        lb_pos is not None
        and lb_pos <= 30
        and (
            ("structurally_live" in tags and model_tier not in MODEL_TIER_WATCH)
            or "model_vindication" in tags
        )
    )

    if is_downgrade:
        return "downgrade_watch"
    if is_promotion:
        return "promotion_watch"
    return "hold"


# ── Build ─────────────────────────────────────────────────────────────────────


def build() -> dict:
    leaderboard = load_leaderboard()
    sg_by_key = load_sg()
    live_r1 = load_live_stats(PATHS["live_r1"], "live_stats_r1_values.csv")
    live_r2 = load_live_stats(PATHS["live_r2"], "live_stats_r2_values.csv")
    teetimes = load_teetimes()
    course_observations = load_course_observations()
    weather = parse_weather()
    model_by_key = load_model_reference()

    lb_keys = {e["player_key"] for e in leaderboard}
    teetime_by_key = {}
    for t in teetimes:
        t["matched_leaderboard"] = t["player_key"] in lb_keys
        if not t["matched_leaderboard"]:
            log_issue("pga_field_r3_teetimes.csv", t["player_name"], t["player_key"], "no_leaderboard_match")
        teetime_by_key[t["player_key"]] = t

    for key in sg_by_key:
        if key not in lb_keys:
            log_issue("round1_round2_player_strokes_gained.csv", key, key, "sg_row_not_in_leaderboard")
    for key in live_r1:
        if key not in lb_keys:
            log_issue("live_stats_r1_values.csv", key, key, "live_stats_row_not_in_leaderboard")
    for key in live_r2:
        if key not in lb_keys:
            log_issue("live_stats_r2_values.csv", key, key, "live_stats_row_not_in_leaderboard")
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
        if key not in sg_by_key:
            log_issue("round1_round2_player_strokes_gained.csv", entry["player_name"], key, "no_sg_match_for_leaderboard_player")

        tags = assign_tags(entry, sg, model)
        if tags:
            venue_mechanism_tags[key] = tags

        if entry["status"] != "cut_survivor":
            continue

        model_rank = model.get("model_rank")
        rank_delta = (model_rank - entry["lb_pos_numeric"]) if (model_rank is not None and entry["lb_pos_numeric"] is not None) else None
        tt = teetime_by_key.get(key, {})

        record = {
            "player_key": key,
            "player_name": entry["player_name"],
            "lb_pos_display": entry["lb_pos_display"],
            "lb_pos_numeric": entry["lb_pos_numeric"],
            "total": entry["total"],
            "r1": entry["r1"],
            "r2": entry["r2"],
            "model_rank": model_rank,
            "model_tier": model.get("model_tier"),
            "rank_delta": rank_delta,
            "sg_ott": sg.get("sg_ott"),
            "sg_app": sg.get("sg_app"),
            "sg_arg": sg.get("sg_arg"),
            "sg_putt": sg.get("sg_putt"),
            "sg_total": sg.get("sg_total"),
            "r1_detail": live_r1.get(key),
            "r2_detail": live_r2.get(key),
            "r3_teetime": tt.get("r3_teetime"),
            "r3_wave": tt.get("r3_wave"),
            "diagnostic_label": tags[0] if tags else "unclassified",
        }
        cut_survivors.append(record)

        bucket = assign_bucket(entry, tags, model)
        if bucket:
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

    survivor_totals = [e["total"] for e in leaderboard if e["status"] == "cut_survivor" and e["total"] is not None]
    cut_line_score = max(survivor_totals) if survivor_totals else None

    return {
        "event": {"name": "Rocket Classic", "course": "Detroit Golf Club", "year": 2026},
        "live_state": {
            "through_round": 2,
            "cut_line_score": cut_line_score,
            "cut_line_display": format_score(cut_line_score),
            "players_through": sum(1 for e in leaderboard if e["status"] == "cut_survivor"),
            "players_cut": sum(1 for e in leaderboard if e["status"] == "missed_cut"),
            "players_wd": sum(1 for e in leaderboard if e["status"] == "withdrew"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_iteration": "update_r2",
            "source_files": SOURCE_FILE_NAMES,
        },
        "leaderboard": leaderboard,
        "cut_survivors": cut_survivors,
        "mechanism_leaders": mechanism_leaders,
        "venue_mechanism_tags": venue_mechanism_tags,
        "diagnostic_buckets": buckets,
        "course_observations": course_observations,
        "round3_weather": weather,
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
