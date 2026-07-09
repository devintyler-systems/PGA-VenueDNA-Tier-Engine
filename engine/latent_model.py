"""
VenueDNA Latent Variable Model — engine/latent_model.py

Core math layer for BRIE-Z sub-driver computation, course difficulty
re-anchoring, wave draw scalar injection, Z-score normalization, and
post-softmax monotonicity validation.

Run as CLI:
    python engine/latent_model.py --verify-monotonicity
    python engine/latent_model.py --verify-monotonicity --event_slug 2026_genesis_scottish_open
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ── Exception ──────────────────────────────────────────────────────────────────

class ValuationAnomalyException(Exception):
    """
    Raised when any player's probability vector violates:
      P(Make Cut) >= P(Top 20) >= P(Top 10) >= P(Top 5) >= P(Win)
    """


# ── BRIE-Z sub-driver ─────────────────────────────────────────────────────────

BRIE_Z_BETA_1: float = 0.6   # fairway 150-200 SG weight
BRIE_Z_BETA_2: float = 0.4   # poor-shot avoidance weight


def compute_brie_z(
    app_150_200_fw_sg: float,
    app_150_200_poor_shot_avoidance: float,
    course_rough_penalty: float = 0.0,
) -> float:
    """
    BRIE-Z sub-driver for the 150-200yd approach zone.

    Replaces the generic 24-month aggregate BRIE with a spatially resolved
    metric: fairway precision at the dominant Renaissance scoring corridor,
    weighted with miss-avoidance and adjusted for links fescue rough penalty.

    Args:
        app_150_200_fw_sg: SG per shot from 150-200yd fairway lies.
            Sourced from 'Fairway shots- 150-200yrd value' in approach_skill CSV.
        app_150_200_poor_shot_avoidance: Centered avoidance rate (avoid_rough_pct
            minus field mean). Positive = better than field average at missing rough.
        course_rough_penalty: difficulty_app_rough_vs_fw from course_profiles.
            Penalises players whose baseline was built in forgiving environments
            relative to thick fescue links rough. Default 0.0 (no adjustment).

    Returns:
        Scalar BRIE-Z score. Higher is better. Units are SG-per-shot equivalent.
    """
    raw = (
        BRIE_Z_BETA_1 * float(app_150_200_fw_sg)
        + BRIE_Z_BETA_2 * float(app_150_200_poor_shot_avoidance)
    )
    return round(raw - float(course_rough_penalty), 6)


# ── Course difficulty matrix ───────────────────────────────────────────────────

def apply_course_difficulty_matrix(
    df: pd.DataFrame,
    course_key: str,
    conn: sqlite3.Connection,
    baseline_col: str = "brie_z_raw",
) -> pd.DataFrame:
    """
    Subtract the course-specific difficulty penalty from player baseline inputs.

    Reads `difficulty_app_rough_vs_fw` from course_profiles and applies it to
    `baseline_col`. Returns a copy with `{baseline_col}_adjusted` added, plus
    `_course_difficulty_applied` (the penalty value used).

    If the course_key is not found or the column is NULL, the DataFrame is
    returned with a 0.0 adjustment (no-op).
    """
    df = df.copy()
    row = conn.execute(
        "SELECT difficulty_app_rough_vs_fw FROM course_profiles WHERE course_key = ?",
        (course_key,),
    ).fetchone()

    penalty = 0.0
    if row and row[0] is not None:
        penalty = float(row[0])

    if baseline_col in df.columns:
        df[f"{baseline_col}_adjusted"] = df[baseline_col] - penalty
    else:
        df[f"{baseline_col}_adjusted"] = -penalty

    df["_course_difficulty_applied"] = penalty
    return df


# ── Wave draw scalar ──────────────────────────────────────────────────────────

_VALID_WAVE_DESIGNATIONS = frozenset({"late_early", "early_late"})


def classify_wave_from_time(tee_time_str: str, am_cutoff_hour: int = 12) -> str:
    """
    Infer wave designation from a tee-time string.

    Times before am_cutoff_hour:00 local → 'early_late'
    (plays AM Thursday, PM Friday — historically calmer on wind-swing days).

    Times at or after am_cutoff_hour:00 → 'late_early'
    (plays PM Thursday, AM Friday).

    Accepts formats: '07:30', '7:30 AM', '14:05', '2:05 PM', '07:30:00'.
    Returns 'unknown' if the string cannot be parsed or is TBD.
    """
    if not tee_time_str:
        return "unknown"
    raw = str(tee_time_str).strip().upper()
    if raw in ("TBD", "N/A", ""):
        return "unknown"

    is_pm = "PM" in raw
    is_am = "AM" in raw
    cleaned = raw.replace("AM", "").replace("PM", "").strip()
    parts = cleaned.replace(":", " ").split()
    try:
        hour = int(parts[0])
    except (IndexError, ValueError):
        return "unknown"

    if is_pm and hour != 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0

    return "early_late" if hour < am_cutoff_hour else "late_early"


def inject_wave_scalar(
    df: pd.DataFrame,
    pairings_path: Path | str | None,
    favored_wave: str = "late_early",
    bonus: float = 0.15,
    name_col: str = "key",
) -> pd.DataFrame:
    """
    Inject a wave draw bonus into the player DataFrame.

    Reads `r1_pairings.csv` to determine each player's wave designation. Players
    in the favored wave receive `bonus` in a new `wave_bonus` column; all others
    receive 0.0.

    Wave designation is read from an explicit 'wave' column if present; otherwise
    inferred from 'tee_time' using classify_wave_from_time().

    If pairings_path is None, missing, or the file is empty, wave_bonus is clamped
    to 0.0 for all players (pre-draw state — no signal injected).

    Args:
        df: Player DataFrame. Must contain `name_col` for matching.
        pairings_path: Path to r1_pairings.csv.
        favored_wave: Which wave gets the bonus ('late_early' or 'early_late').
                      Defaults to 'late_early'. Validated against known designations;
                      falls back to 'late_early' if unrecognised.
        bonus: SG bonus for favored-wave players (default +0.15).
        name_col: Column in df used as join key (expected: normalized player key).

    Returns:
        Copy of df with 'wave_bonus' (float) and 'wave_designation' (str) added.
    """
    df = df.copy()
    df["wave_bonus"] = 0.0
    df["wave_designation"] = "unknown"

    if favored_wave not in _VALID_WAVE_DESIGNATIONS:
        favored_wave = "late_early"

    if pairings_path is None:
        return df

    path = Path(pairings_path)
    if not path.exists():
        return df

    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return df

    if not rows:
        return df

    wave_map: dict[str, tuple[str, float]] = {}
    for row in rows:
        name_raw = (
            row.get("player_name")
            or f"{row.get('last_name', '')}, {row.get('first_name', '')}".strip(", ")
        )
        if not name_raw:
            continue

        wave_col = str(row.get("wave", "")).strip().lower()
        if wave_col in _VALID_WAVE_DESIGNATIONS:
            designation = wave_col
        else:
            designation = classify_wave_from_time(str(row.get("tee_time", "")))

        player_key = _norm_key(name_raw)
        wave_map[player_key] = (designation, bonus if designation == favored_wave else 0.0)

    for idx, row_df in df.iterrows():
        pkey = str(row_df.get(name_col, ""))
        if pkey in wave_map:
            designation, b = wave_map[pkey]
            df.at[idx, "wave_designation"] = designation
            df.at[idx, "wave_bonus"] = b

    return df


def _norm_key(name: str) -> str:
    """Minimal name normalisation for wave-map lookup. Mirrors dg_api_harvester."""
    _SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\.?(?=[\s,]|$)", re.IGNORECASE)
    s = str(name).strip()
    s = _SUFFIX_RE.sub("", s).strip().rstrip(",").strip()
    nfd = unicodedata.normalize("NFD", s)
    s = "".join(c for c in nfd if not unicodedata.combining(c))
    explicit = {"Ø":"O","ø":"O","Æ":"AE","æ":"AE","Å":"A","å":"A",
                "Ö":"O","ö":"O","Ü":"U","ü":"U","Ñ":"N","ñ":"N","ß":"SS"}
    for src, dst in explicit.items():
        s = s.replace(src, dst)
    if "," in s:
        last, first = s.split(",", 1)
    else:
        tokens = s.rsplit(None, 1)
        first, last = (tokens[0], tokens[1]) if len(tokens) == 2 else ("", tokens[0])
    raw = f"{last.strip()}_{first.strip()}".lower()
    raw = re.sub(r"\s+", "", raw)
    raw = re.sub(r"[^a-z0-9_]", "", raw)
    return raw


# ── Z-score normalization ─────────────────────────────────────────────────────

def zscore_normalize(
    series: pd.Series,
    target_mean: float = 50.0,
    target_std: float = 15.0,
) -> pd.Series:
    """
    Z-score then rescale to [target_mean ± target_std], clamped 0-100.
    NaN values fill to target_mean after scaling.
    """
    valid = series.dropna()
    if len(valid) == 0:
        return series.fillna(target_mean)
    mu, sigma = valid.mean(), valid.std()
    if sigma < 1e-9:
        return pd.Series(target_mean, index=series.index)
    scaled = (series - mu) / sigma * target_std + target_mean
    return scaled.clip(0.0, 100.0).fillna(target_mean)


# ── Monotonicity validation ───────────────────────────────────────────────────

_PROB_CHAIN = [
    # (primary_key, alias_key, label)
    ("make_cut_prob", "make_cut_prob", "make_cut"),
    ("top20_prob",    "top20_pct",     "top20"),
    ("top10_prob",    "top10_pct",     "top10"),
    ("top5_prob",     "top5_pct",      "top5"),
    ("win_prob",      "win_pct",       "win"),
]

_CHAIN_TRANSITIONS = [
    ("make_cut", "top20"),
    ("top20",    "top10"),
    ("top10",    "top5"),
    ("top5",     "win"),
]


def _resolve_prob(player: dict, primary: str, alias: str) -> float | None:
    v = player.get(primary)
    if v is None:
        v = player.get(alias)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def verify_monotonicity(players: list[dict]) -> None:
    """
    Assert P(Make Cut) >= P(Top 20) >= P(Top 10) >= P(Top 5) >= P(Win)
    for every player in the list.

    Args:
        players: Player dicts from event_payload.json. Accepts both canonical
                 field names (win_prob, top5_prob, ...) and alias names
                 (win_pct, top5_pct, ...) used in some payload layouts.

    Raises:
        ValuationAnomalyException: Lists every violation with player name,
            which transition failed, and the magnitude of the inversion.
    """
    violations: list[str] = []

    for p in players:
        name = (
            f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            or p.get("player_name", "unknown")
        )
        pid = p.get("player_id", "?")

        probs: dict[str, float | None] = {}
        for primary, alias, label in _PROB_CHAIN:
            probs[label] = _resolve_prob(p, primary, alias)

        for higher_label, lower_label in _CHAIN_TRANSITIONS:
            hi = probs[higher_label]
            lo = probs[lower_label]
            if hi is None or lo is None:
                continue
            if lo > hi + 1e-9:
                violations.append(
                    f"{name} (id={pid}): "
                    f"P({lower_label})={lo:.4f} > P({higher_label})={hi:.4f}  "
                    f"[delta={lo - hi:.4f}]"
                )

    if violations:
        raise ValuationAnomalyException(
            f"Monotonicity violated for {len(violations)} player(s):\n"
            + "\n".join(f"  • {v}" for v in violations)
        )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _find_payload(event_slug: str | None) -> Path:
    root = Path(__file__).resolve().parent.parent
    if event_slug:
        # Try both slug-exact and partial-glob matches
        slug_norm = event_slug.replace("_", "*")
        for pattern in (
            f"events/*{event_slug}*/deploy/data/event_payload.json",
            f"events/*{slug_norm}*/deploy/data/event_payload.json",
        ):
            candidates = sorted(root.glob(pattern))
            if candidates:
                return candidates[0]
    # Default: most recently modified
    all_payloads = sorted(
        root.glob("events/*/deploy/data/event_payload.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if all_payloads:
        return all_payloads[0]
    raise FileNotFoundError("No event_payload.json found under events/*/deploy/data/")


def _extract_players(payload: dict) -> list[dict]:
    if isinstance(payload.get("players"), list):
        return payload["players"]
    if isinstance(payload.get("tiers"), dict):
        out: list[dict] = []
        for tier_list in payload["tiers"].values():
            if isinstance(tier_list, list):
                out.extend(tier_list)
        return out
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VenueDNA Latent Model CLI")
    parser.add_argument(
        "--verify-monotonicity",
        action="store_true",
        help="Verify P(Cut) >= P(T20) >= P(T10) >= P(T5) >= P(Win) for all players",
    )
    parser.add_argument(
        "--event_slug",
        default=None,
        metavar="SLUG",
        help="Event slug (e.g. 2026_genesis_scottish_open). Defaults to most recent payload.",
    )
    args = parser.parse_args()

    if not args.verify_monotonicity:
        parser.print_help()
        sys.exit(0)

    payload_path = _find_payload(args.event_slug)
    print(f"Payload : {payload_path}")
    with open(payload_path, encoding="utf-8") as fh:
        payload = json.load(fh)

    players = _extract_players(payload)
    if not players:
        print("ERROR: No players found in payload.")
        sys.exit(1)

    print(f"Players : {len(players)}")
    print("Checking monotonicity …")

    try:
        verify_monotonicity(players)
        print(f"PASS — constraint holds for all {len(players)} players.")
        sys.exit(0)
    except ValuationAnomalyException as exc:
        print(f"FAIL\n{exc}")
        sys.exit(2)
