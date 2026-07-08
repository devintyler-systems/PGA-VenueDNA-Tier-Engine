"""
Backfill historical_round_logs for the current weekly field.

Pulls 24 months of round-by-round SG history from DataGolf's
/historical-raw-data/rounds endpoint — one player × tour × year call
at a time — and upserts into data/venuedna_master.db.

Rate limiting is handled entirely by _get(); no manual sleeps needed.

Typical runtime: ~25 min for a 156-player field
  (156 players × 2 tours × 3 years × 1.5 s/call ≈ 1,404 s)
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta

from engine.datagolf_client import DB_PATH, _get, fetch_weekly_field, init_db

log = logging.getLogger(__name__)

LOOKBACK_MONTHS = 24
TOURS = ["pga", "euro"]  # euro needed for co-sanctioned events (e.g. Scottish Open)

# ── SQL ───────────────────────────────────────────────────────────────────────

_UPSERT_SQL = """
    INSERT OR REPLACE INTO historical_round_logs (
        player_id, player_name, tour, event_name, course_name,
        season, calendar_year, round, score,
        sg_putt, sg_arg, sg_app, sg_ott, sg_t2g, sg_total,
        driving_dist, driving_acc, round_date
    ) VALUES (
        :player_id, :player_name, :tour, :event_name, :course_name,
        :season, :calendar_year, :round, :score,
        :sg_putt, :sg_arg, :sg_app, :sg_ott, :sg_t2g, :sg_total,
        :driving_dist, :driving_acc, :round_date
    )
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _normalise_date_str(raw: str) -> str | None:
    """Return YYYY-MM-DD from any common date string, or None if unparseable."""
    s = str(raw).strip()
    # ISO YYYY-MM-DD (possibly with time suffix)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    # US formats: MM/DD/YYYY or MM-DD-YYYY; and YYYY/MM/DD
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_round_date(r: dict) -> str | None:
    """
    Extract an ISO round date from a DataGolf API record.

    Tries explicit round-level keys first, then derives the date from
    event_completed + round_num (round 4 = completion day, earlier rounds
    subtract one day per round back).  Returns None if no date can be found.
    """
    for key in ("round_date", "date", "event_date"):
        raw = r.get(key)
        if raw:
            return _normalise_date_str(raw)

    completed = r.get("event_completed")
    round_num  = r.get("round_num") or r.get("round") or r.get("round_number")
    if completed and round_num is not None:
        try:
            end = datetime.fromisoformat(str(completed).strip()[:10]).date()
            # Standard 4-round event: round 4 ends on event_completed
            return str(end - timedelta(days=4 - int(round_num)))
        except (ValueError, TypeError):
            pass

    return None


def _year_range(reference: date) -> list[int]:
    """Calendar years that together span LOOKBACK_MONTHS back from *reference*."""
    start = (reference - timedelta(days=round(LOOKBACK_MONTHS * 30.44))).year
    return list(range(start, reference.year + 1))


def _fetch_rounds(dg_id: str, tour: str, year: int) -> list[dict]:
    """
    One API call → flat list of round records for this player/tour/year.
    _get() sleeps RATE_LIMIT_SLEEP seconds after every call automatically.
    Returns [] on any network or HTTP error so the outer loop can continue.
    """
    try:
        raw = _get("historical-raw-data/rounds", {
            "tour": tour,
            "dg_id": dg_id,
            "year": year,
        })
    except Exception as exc:
        log.warning("API error  player=%s tour=%s year=%d — %s", dg_id, tour, year, exc)
        return []

    rows: list[dict] = raw if isinstance(raw, list) else raw.get("rounds", [])

    # If the endpoint ignores the dg_id param and returns the full event,
    # drop rows that belong to other players.  If rows have no dg_id key,
    # the API already filtered — keep everything.
    def _belongs(r: dict) -> bool:
        row_id = r.get("dg_id") or r.get("player_id")
        return row_id is None or str(row_id) == dg_id

    return [r for r in rows if _belongs(r)]


def _normalise(r: dict, player_id: str, tour: str) -> dict:
    """Map a DataGolf API record to the historical_round_logs column set."""
    return {
        "player_id":    player_id,
        "player_name":  r.get("player_name", ""),
        "tour":         r.get("tour", tour),
        "event_name":   r.get("event_name", ""),
        # DataGolf uses 'course' in some feeds, 'course_name' in others
        "course_name":  r.get("course") or r.get("course_name", ""),
        # 'season' = tour-season year; fall back to calendar_year if absent
        "season":       r.get("season") or r.get("calendar_year"),
        "calendar_year": r.get("calendar_year"),
        # round key varies across endpoint versions
        "round":        r.get("round_num") or r.get("round") or r.get("round_number"),
        "score":        r.get("score"),
        "sg_putt":      r.get("sg_putt"),
        "sg_arg":       r.get("sg_arg"),
        "sg_app":       r.get("sg_app"),
        "sg_ott":       r.get("sg_ott"),
        "sg_t2g":       r.get("sg_t2g"),
        "sg_total":     r.get("sg_total"),
        "driving_dist": r.get("driving_dist"),
        "driving_acc":  r.get("driving_acc"),
        "round_date":   _parse_round_date(r),
    }


def _upsert(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Batch-upsert *rows* and commit. Returns number of rows written."""
    if not rows:
        return 0
    conn.executemany(_UPSERT_SQL, rows)
    conn.commit()
    return len(rows)


# ── main entry point ──────────────────────────────────────────────────────────

def backfill(
    reference_date: date | None = None,
    tours: list[str] | None = None,
) -> None:
    """
    Fetch and store 24 months of SG history for every player in this week's field.

    Parameters
    ----------
    reference_date:
        Anchor for the lookback window. Defaults to today.
    tours:
        Tour codes to query. Defaults to TOURS (pga + euro).
    """
    if reference_date is None:
        reference_date = date.today()
    if tours is None:
        tours = TOURS

    years = _year_range(reference_date)
    calls_per_player = len(tours) * len(years)

    conn  = init_db()
    field = fetch_weekly_field(tour="pga")

    n = len(field)
    log.info(
        "Backfill start — %d players | tours=%s | years=%s | ~%d API calls total",
        n, tours, years, n * calls_per_player,
    )

    total_rows   = 0
    total_errors = 0

    for idx, player in enumerate(field, 1):
        dg_id = str(player.get("dg_id", "")).strip()
        name  = player.get("player_name", f"player_{dg_id}")

        if not dg_id:
            log.warning("[%d/%d] no dg_id for %s — skipped", idx, n, player)
            total_errors += 1
            continue

        player_rows: list[dict] = []
        for tour in tours:
            for year in years:
                raw = _fetch_rounds(dg_id, tour, year)
                player_rows.extend(_normalise(r, dg_id, tour) for r in raw)

        written = _upsert(conn, player_rows)
        log.info("[%d/%d]  %-30s  dg_id=%-8s  rows=%d", idx, n, name, dg_id, written)
        total_rows += written

    conn.close()
    log.info(
        "Backfill complete — %d rows written across %d players (%d skipped).",
        total_rows, n - total_errors, total_errors,
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    backfill()
