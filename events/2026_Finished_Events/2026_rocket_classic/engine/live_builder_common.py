"""
live_builder_common.py — shared parsing primitives for the Rocket Classic
live-diagnostic builders (build_live_r2.py, build_live_r3.py, and future
build_live_r{n}.py rounds).

Pure functions and constants only. No shared mutable state: each builder
keeps its own `match_issues` audit list and `log_issue()` — issues found by
one round's build must never leak into another round's artifact. Callers
that need to log a parsing shortfall (e.g. weather regex below threshold)
do so themselves using the return values from these helpers.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

# ── Name tokens ──────────────────────────────────────────────────────────────

AMATEUR_RE = re.compile(r"\(a+\)\s*$", re.IGNORECASE)
NAME_TOKEN_RE = re.compile(r"[A-Za-z]+")
SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}

# Some event-local sources spell certain names with native diacritics
# ("Højgaard", "Thorbjørn") while others use the ASCII transliteration
# ("Hojgaard", "Thorbjorn") for the same player. NAME_TOKEN_RE (`[A-Za-z]+`)
# silently drops non-ASCII letters instead of matching them, which fragments
# "højgaard" into "h" + "jgaard" instead of folding to "hojgaard" — breaking
# the cross-source join for any affected player. Fold diacritics to ASCII
# before tokenizing so the key is encoding/spelling-invariant. NFKD handles
# most accents (é→e, å→a) but ø/æ don't decompose that way, so they get an
# explicit map first.
_DIACRITIC_FOLD = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE"})


def fold_diacritics(s: str) -> str:
    s = s.translate(_DIACRITIC_FOLD)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def normalize_name(raw: str) -> tuple[str, str, bool]:
    """Return (player_key, display_name, amateur_flag) for a raw name string.

    Sources mix "Last, First" (event_payload, live_stats, teetimes) and
    "First Last" (leaderboard, SG csv) formats, and some surnames are
    multi-token ("Van Rooyen"). A strict first|last split breaks on those
    (order differs by source), so the key is built from the sorted set of
    cleaned, diacritic-folded name tokens instead — order-, format-, and
    encoding-invariant, still deterministic and auditable.
    """
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

    tokens = [t.lower() for t in NAME_TOKEN_RE.findall(fold_diacritics(raw))]
    tokens = [t for t in tokens if t not in SUFFIX_TOKENS]
    tokens.sort()
    key = "|".join(tokens)

    if amateur:
        display = f"{display} (a)"
    return key, display, amateur


# ── CSV loading ────────────────────────────────────────────────────────────


def read_csv_raw(path: Path, encodings: tuple[str, ...] = ("utf-8-sig", "cp1252")) -> tuple[list[str], list[list[str]]]:
    """Read a CSV with positional access, trying each encoding in order.

    Rocket Classic sources are mostly UTF-8, but some ship cp1252 (e.g. a
    leaderboard export containing "Højgaard"). Try UTF-8 first — the common
    case — and fall back rather than crashing or mangling non-ASCII names.
    """
    last_err: UnicodeDecodeError | None = None
    for enc in encodings:
        try:
            with path.open(encoding=enc, newline="") as f:
                rows = [r for r in csv.reader(f)]
            break
        except UnicodeDecodeError as e:
            last_err = e
    else:
        raise last_err  # all encodings failed

    if not rows:
        return [], []
    header = rows[0]
    data = [r for r in rows[1:] if any(cell.strip() for cell in r)]
    return header, data


# ── Numeric helpers ──────────────────────────────────────────────────────────


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


# ── Weather hourly-forecast extraction ───────────────────────────────────────
#
# Clean per-hour forecasts look like:
#   "6 AM: 74°F, 7% precip, wind 3 mph ESE"
# Narrative-prose forecasts (seen starting R4) keep the same opening but
# interleave descriptive clauses before wind:
#   "7 AM: 69°F, steady rain, precip ~71%, ~0.03 in/hr, wind 8 mph NE, ..."
# Try the strict regex first (clean sources); fall back to the looser
# narrative regex only if the strict one doesn't clear the match-rate bar.
# Callers own the threshold check and raw-text fallback/log_issue — these
# are just the extraction primitives.

HOURLY_RE_STRICT = re.compile(
    r"^(\d{1,2}\s(?:AM|PM)):\s(\d+)°F,\s(\d+)% precip,\swind\s(\d+)\smph\s([A-Z]+)$"
)
HOURLY_RE_NARRATIVE = re.compile(
    r"^(\d{1,2}\s(?:AM|PM)):\s(\d+)°F,.*?precip\s~?(\d+)%.*?wind\s(\d+)\smph\s([A-Z]+)"
)
TEE_WINDOW_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s?[AP]M)\s*(?:[–-]|and|to)\s*(\d{1,2}(?::\d{2})?\s?[AP]M)"
)


def hour_to_24(time_label: str) -> int:
    h, period = time_label.split(" ")
    h = int(h)
    if period == "AM":
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12


def extract_hourly(regex: re.Pattern, candidate_lines: list[str]) -> tuple[list[dict], float]:
    """Match `regex` against each candidate line; return (hourly_entries, match_rate)."""
    hourly = []
    for ln in candidate_lines:
        m = regex.match(ln)
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
    rate = (len(hourly) / len(candidate_lines)) if candidate_lines else 0.0
    return hourly, rate


def summarize_hourly(hourly: list[dict], raw_text: str, parse_status: str, parse_method: str) -> dict:
    """Build the structured weather summary dict from a successfully-extracted hourly list."""
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
    # group(0) — the whole match, verbatim as it appears in the source (exact
    # separator/spacing preserved) — not a reconstruction from sub-groups, so
    # a stricter or looser regex variant never changes the emitted string for
    # sources the narrower pattern already matched.
    tee_window_summary = tee_window_match.group(0) if tee_window_match else None

    return {
        "parse_status": parse_status,
        "parse_method": parse_method,
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
        "tee_time_window_summary": tee_window_summary,
    }
