"""
Venue-fitness trait engine for PGA VenueDNA.

Computes four rolling metrics for a player against course-profile metadata:
  tvl_score  (12 months) — miss-tolerance ratio via SG:OTT across MPI buckets
  hew_score  ( 6 months) — exposure sensitivity via Ball Striking delta
  brie_score (24 months) — turf-firmness edge via SG:APP delta (firm vs soft)
  vfr_score  ( 6 months) — green-contour adaptability via SG:ARG delta

Lookback windows use hrl.round_date (ISO TEXT, YYYY-MM-DD) for exact date
boundaries.  Rows without a round_date are excluded from all trait calculations.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "venuedna_master.db"

MIN_ROUNDS = 10  # minimum qualifying rows required to emit a score


# ── public entry point ────────────────────────────────────────────────────────

def compute_player_traits(
    dg_id: str | int,
    reference_date: Optional[date | str] = None,
) -> dict:
    """Return the four venue-fitness scores for *dg_id* as of *reference_date*.

    Any trait that has fewer than MIN_ROUNDS qualifying rows in its window,
    or whose subgroup split is unsolvable (e.g. zero-denominator ratio),
    is returned as ``None``.
    """
    if reference_date is None:
        reference_date = date.today()
    elif isinstance(reference_date, str):
        reference_date = date.fromisoformat(reference_date)

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                hrl.round_date,
                hrl.sg_ott,
                hrl.sg_app,
                hrl.sg_arg,
                cp.miss_penalty_index,
                cp.exposure_index,
                cp.turf_firmness_tag,
                cp.green_contour_rating
            FROM historical_round_logs hrl
            JOIN course_profiles cp ON cp.course_name = hrl.course_name
            WHERE CAST(hrl.player_id AS TEXT) = ?
              AND hrl.round_date IS NOT NULL
            """,
            conn,
            params=(str(dg_id),),
        )

    def _window(months: int) -> pd.DataFrame:
        cutoff = (reference_date - timedelta(days=round(months * 30.44))).isoformat()
        return df[df["round_date"] >= cutoff].copy()

    w6  = _window(6)
    w12 = _window(12)
    w24 = _window(24)

    return {
        "dg_id":          dg_id,
        "reference_date": str(reference_date),
        "tvl_score":      _tvl(w12),
        "hew_score":      _hew(w6),
        "brie_score":     _brie(w24),
        "vfr_score":      _vfr(w6),
    }


# ── trait calculators ─────────────────────────────────────────────────────────

def _tvl(w: pd.DataFrame) -> Optional[float]:
    """avg SG:OTT (MPI ≤ 2) / avg SG:OTT (MPI ≥ 4)."""
    subset = w[["sg_ott", "miss_penalty_index"]].dropna()
    if len(subset) < MIN_ROUNDS:
        return None
    low  = subset.loc[subset["miss_penalty_index"] <= 2, "sg_ott"]
    high = subset.loc[subset["miss_penalty_index"] >= 4, "sg_ott"]
    if low.empty or high.empty or high.mean() == 0.0:
        return None
    return round(float(low.mean() / high.mean()), 4)


def _hew(w: pd.DataFrame) -> Optional[float]:
    """avg ball-striking (exposure < 0.4) − avg ball-striking (exposure ≥ 0.7)."""
    subset = w[["sg_ott", "sg_app", "exposure_index"]].dropna()
    if len(subset) < MIN_ROUNDS:
        return None
    bs       = subset["sg_ott"] + subset["sg_app"]
    low_exp  = bs[subset["exposure_index"] <  0.4]
    high_exp = bs[subset["exposure_index"] >= 0.7]
    if low_exp.empty or high_exp.empty:
        return None
    return round(float(low_exp.mean() - high_exp.mean()), 4)


def _brie(w: pd.DataFrame) -> Optional[float]:
    """avg SG:APP (firm) − avg SG:APP (soft)."""
    subset = w[["sg_app", "turf_firmness_tag"]].dropna()
    if len(subset) < MIN_ROUNDS:
        return None
    firm = subset.loc[subset["turf_firmness_tag"] == "firm", "sg_app"]
    soft = subset.loc[subset["turf_firmness_tag"] == "soft", "sg_app"]
    if firm.empty or soft.empty:
        return None
    return round(float(firm.mean() - soft.mean()), 4)


def _vfr(w: pd.DataFrame) -> Optional[float]:
    """avg SG:ARG (severe greens) − avg SG:ARG (flat greens)."""
    subset = w[["sg_arg", "green_contour_rating"]].dropna()
    if len(subset) < MIN_ROUNDS:
        return None
    severe = subset.loc[subset["green_contour_rating"] == "severe", "sg_arg"]
    flat   = subset.loc[subset["green_contour_rating"] == "flat",   "sg_arg"]
    if severe.empty or flat.empty:
        return None
    return round(float(severe.mean() - flat.mean()), 4)


# ── smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import logging
    import random

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    log = logging.getLogger(__name__)

    DUMMY_ID = "SMOKE_TEST_001"

    # Ensure schema exists (mirrors datagolf_client._create_tables)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS historical_round_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id       TEXT,
                player_name     TEXT,
                tour            TEXT,
                event_name      TEXT,
                course_name     TEXT,
                season          INTEGER,
                calendar_year   INTEGER,
                round           INTEGER,
                score           INTEGER,
                sg_putt         REAL,
                sg_arg          REAL,
                sg_app          REAL,
                sg_ott          REAL,
                sg_t2g          REAL,
                sg_total        REAL,
                driving_dist    REAL,
                driving_acc     REAL,
                round_date      TEXT,
                fetched_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(player_id, tour, event_name, season, round)
            );
            CREATE TABLE IF NOT EXISTS course_profiles (
                course_key           TEXT PRIMARY KEY,
                course_name          TEXT,
                location             TEXT,
                par                  INTEGER,
                yardage              INTEGER,
                tour                 TEXT,
                miss_penalty_index   INTEGER,
                turf_firmness_tag    TEXT,
                green_contour_rating TEXT,
                exposure_index       REAL,
                notes                TEXT,
                updated_at           TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migrate existing tables created before round_date was added
        try:
            conn.execute(
                "ALTER TABLE historical_round_logs ADD COLUMN round_date TEXT"
            )
            conn.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

        # Three synthetic courses covering all four trait splits
        conn.executemany(
            """
            INSERT OR IGNORE INTO course_profiles
                (course_key, course_name, miss_penalty_index,
                 turf_firmness_tag, green_contour_rating, exposure_index)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("smoke_low",  "Smoke Low Course",  1, "firm",   "severe", 0.15),
                ("smoke_high", "Smoke High Course", 5, "soft",   "flat",   0.80),
                ("smoke_mid",  "Smoke Mid Course",  3, "firm",   "flat",   0.55),
            ],
        )

        # 30 synthetic rounds across three date buckets so each lookback window
        # (6 / 12 / 24 months from 2026-07-08) contains ≥ MIN_ROUNDS qualifying rows.
        #   i  0-9  → 2024-08-15  (24-month window only)
        #   i 10-19 → 2025-08-15  (12-month + 24-month windows)
        #   i 20-29 → 2026-02-15  (all three windows)
        _DATES  = ["2024-08-15", "2025-08-15", "2026-02-15"]
        _YEARS  = [2024, 2025, 2026]
        rng     = random.Random(42)
        courses = ["Smoke Low Course", "Smoke High Course", "Smoke Mid Course"]
        rows    = []
        for i in range(30):
            bucket = 0 if i < 10 else (1 if i < 20 else 2)
            year   = _YEARS[bucket]
            rdate  = _DATES[bucket]
            rows.append((
                DUMMY_ID, "Smoke Test Player", "pga",
                f"Smoke-{year}-E{(i % 10) // 4}", courses[i % 3],
                year, year, (i % 4) + 1, 70,
                round(rng.uniform(-1.5, 1.5), 3),   # sg_putt
                round(rng.uniform(-1.5, 1.5), 3),   # sg_arg
                round(rng.uniform(-1.5, 1.5), 3),   # sg_app
                round(rng.uniform(-1.5, 1.5), 3),   # sg_ott
                round(rng.uniform(-1.5, 1.5), 3),   # sg_t2g
                round(rng.uniform(-3.0, 3.0), 3),   # sg_total
                275.0, 0.65, rdate,
            ))
        conn.executemany(
            """
            INSERT OR REPLACE INTO historical_round_logs
                (player_id, player_name, tour, event_name, course_name,
                 season, calendar_year, round, score,
                 sg_putt, sg_arg, sg_app, sg_ott, sg_t2g, sg_total,
                 driving_dist, driving_acc, round_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        log.info("Seeded %d synthetic rounds for %s", len(rows), DUMMY_ID)

    result = compute_player_traits(DUMMY_ID, reference_date="2026-07-08")
    print(json.dumps(result, indent=2))

    # Verify None handling: request with a player that has no data
    empty = compute_player_traits("NONEXISTENT_999", reference_date="2026-07-08")
    assert all(v is None for k, v in empty.items() if k not in ("dg_id", "reference_date")), \
        "Expected all traits None for unknown player"
    log.info("Edge-case assertion passed — unknown player returns all None.")

    # Clean up seed data
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM historical_round_logs WHERE player_id = ?", (DUMMY_ID,))
        conn.execute("DELETE FROM course_profiles WHERE course_key LIKE 'smoke_%'")
    log.info("Smoke-test seed data removed.")
