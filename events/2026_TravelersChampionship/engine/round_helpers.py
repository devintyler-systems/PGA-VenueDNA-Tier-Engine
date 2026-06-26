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
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


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
    """Parse proximity string like '12\\'4"' into total inches."""
    s = str(s).strip()
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
        return float(str(s).rstrip("%"))
    except (TypeError, ValueError):
        return None
