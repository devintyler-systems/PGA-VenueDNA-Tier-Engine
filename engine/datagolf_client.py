"""
DataGolf API client for PGA VenueDNA.

Manages a local SQLite database (data/venuedna_master.db) and provides
rate-limited access to the DataGolf feeds API.
"""

import os
import time
import sqlite3
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── config ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "venuedna_master.db"
ENV_PATH = ROOT / ".env"

DG_BASE_URL = "https://feeds.datagolf.com"
RATE_LIMIT_SLEEP = 1.5  # seconds between requests (≤ 45 req/min)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

load_dotenv(ENV_PATH)
API_KEY = os.getenv("DATAGOLF_API_KEY")
if not API_KEY:
    raise EnvironmentError(f"DATAGOLF_API_KEY not found in {ENV_PATH}")


# ── database ──────────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """Open (or create) the master database and ensure both tables exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    log.info("DB ready: %s", DB_PATH)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
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
            miss_penalty_index   INTEGER CHECK(miss_penalty_index BETWEEN 1 AND 5),
            turf_firmness_tag    TEXT CHECK(turf_firmness_tag IN ('firm', 'soft')),
            green_contour_rating TEXT CHECK(green_contour_rating IN ('severe', 'flat')),
            exposure_index       REAL CHECK(exposure_index BETWEEN 0.0 AND 1.0),
            notes                TEXT,
            updated_at           TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    # Migrate existing databases that predate the round_date column.
    try:
        conn.execute(
            "ALTER TABLE historical_round_logs ADD COLUMN round_date TEXT"
        )
        conn.commit()
        log.info("Migrated historical_round_logs: added round_date column.")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _get(endpoint: str, params: dict | None = None) -> dict | list:
    """
    Rate-limited GET against the DataGolf feeds API.
    Sleeps RATE_LIMIT_SLEEP seconds after every call regardless of success,
    so callers never need to manage pacing themselves.
    """
    url = f"{DG_BASE_URL}/{endpoint.lstrip('/')}"
    payload = {"key": API_KEY, "file_format": "json", **(params or {})}

    try:
        resp = requests.get(url, params=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as exc:
        log.error("HTTP %s from %s: %s", exc.response.status_code, url, exc.response.text)
        raise
    except requests.exceptions.RequestException as exc:
        log.error("Request failed for %s: %s", url, exc)
        raise
    finally:
        time.sleep(RATE_LIMIT_SLEEP)


# ── public API ────────────────────────────────────────────────────────────────

def fetch_weekly_field(tour: str = "pga") -> list[dict]:
    """
    Pull the current week's player list from the /field-updates endpoint.

    Returns a list of player dicts as delivered by DataGolf. Each dict
    typically contains player_name, dg_id, country, am, and ownership odds.
    """
    log.info("Fetching weekly field for tour=%s", tour)
    data = _get("field-updates", {"tour": tour})

    # DataGolf wraps the field under a 'field' key
    field = data.get("field", data) if isinstance(data, dict) else data
    log.info("Received %d players in field", len(field))
    return field


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = init_db()

    players = fetch_weekly_field(tour="pga")
    for p in players[:5]:
        print(p)

    conn.close()
