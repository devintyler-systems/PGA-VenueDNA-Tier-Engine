"""
round_helpers.py — Shared utility functions for VenueDNA round analysis scripts.

Usage:
    from round_helpers import load_csv, ascii_fold, fl_to_lf, avg, parse_float, parse_prox, parse_pct
"""
import csv
import re
import unicodedata
from pathlib import Path
from statistics import mean


def load_csv(p: Path) -> list:
    """Load a CSV with automatic encoding detection (utf-8-sig → utf-8 → latin-1)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, newline="", encoding=enc) as f:
                rows = list(csv.DictReader(f))
            if rows:
                return rows
        except (UnicodeDecodeError, Exception):
            continue
    # Last-resort: replace undecodable bytes rather than crashing
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def csv_columns(p: Path) -> list:
    """Return header column names from a CSV without loading all rows."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, newline="", encoding=enc) as f:
                reader = csv.reader(f)
                return next(reader, [])
        except (UnicodeDecodeError, Exception):
            continue
    return []


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")


def fl_to_lf(name: str) -> str:
    """'First Last' → 'Last, First'. Used for name-key normalization."""
    parts = name.strip().split()
    return parts[-1] + ", " + " ".join(parts[:-1]) if len(parts) >= 2 else name


def avg(lst: list):
    vals = [x for x in lst if x is not None]
    return round(mean(vals), 3) if vals else None


def parse_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_prox(s) -> int | None:
    """Parse proximity string like '12\\'4"' into total inches.
    Handles both straight and curly quote variants."""
    # Normalize curly/smart quotes to straight equivalents
    s = (str(s).strip()
         .replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"'))
    m = re.match(r"(\d+)'\s*(\d+)\"", s)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m2 = re.match(r"(\d+)'", s)
    if m2:
        return int(m2.group(1)) * 12
    return None


def parse_pct(s) -> float | None:
    """Parse '72.4%' → 72.4."""
    try:
        return float(str(s).rstrip("%").strip())
    except (TypeError, ValueError):
        return None


def parse_pos(pos_str: str) -> int:
    """Parse leaderboard position string to int.
    Handles: '1', 'T12', 'T1' → integer; WD/CUT/DQ/MDF/'--'/other → 72 (bottom sentinel)."""
    s = str(pos_str).strip().lstrip("T")
    return int(s) if s.isdigit() else 72
