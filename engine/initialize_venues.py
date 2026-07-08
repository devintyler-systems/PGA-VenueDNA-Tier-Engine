"""
Seed the course_profiles table in data/venuedna_master.db.

Run this once (or any time a profile changes) to establish or refresh
venue metadata. Uses INSERT OR REPLACE so reruns are safe.
"""

import sqlite3
import logging
from engine.datagolf_client import init_db

log = logging.getLogger(__name__)

# ── venue catalogue ───────────────────────────────────────────────────────────
#
# miss_penalty_index  1=forgiving → 5=brutal
# turf_firmness_tag   'firm' | 'soft'
# green_contour_rating 'severe' | 'flat'
# exposure_index      0.0 (sheltered) → 1.0 (fully exposed)

VENUES: list[dict] = [
    {
        "course_key":           "aronimink_gc",
        "course_name":          "Aronimink Golf Club",
        "location":             "Newtown Square, PA",
        "par":                  70,
        "yardage":              7394,
        "tour":                 "pga",
        # Tight tree corridors and angle-sensitive approach windows make
        # misses structural even though the raw hazard count is low.
        "miss_penalty_index":   3,
        "turf_firmness_tag":    "firm",
        # Penn A-1/A-4 bentgrass with elevated two-tier greens; no-soften policy.
        "green_contour_rating": "severe",
        # Inland suburban Philadelphia — tree canopy suppresses most wind.
        "exposure_index":       0.25,
        "notes":                "Donald Ross parkland; 2026 PGA Championship; hard par / easy bogey archetype",
    },
    {
        "course_key":           "shinnecock_hills_gc",
        "course_name":          "Shinnecock Hills Golf Club",
        "location":             "Southampton, NY",
        "par":                  70,
        "yardage":              7440,
        "tour":                 "pga",
        # Penal U.S. Open rough + firm/fast setup; no-soften-for-wind policy.
        "miss_penalty_index":   4,
        "turf_firmness_tag":    "firm",
        "green_contour_rating": "severe",
        # Fully exposed coastal links on Long Island's South Fork; wind is the
        # primary scoring lever and the dominant variance driver.
        "exposure_index":       0.90,
        "notes":                "Links-style; 2026 U.S. Open; high rough + wind = high variance; wide fairways (47.6 yds avg) offset some penalty",
    },
    {
        "course_key":           "tpc_river_highlands",
        "course_name":          "TPC River Highlands",
        "location":             "Cromwell, CT",
        "par":                  70,
        "yardage":              6844,
        "tour":                 "pga",
        # Miss penalty is almost entirely water-driven (holes 15-17);
        # raw fraction 0.0727 — the highest in the portfolio.
        "miss_penalty_index":   4,
        "turf_firmness_tag":    "soft",
        "green_contour_rating": "flat",
        # Inland Connecticut; the course's variance comes from water hazards
        # and putting pace, not wind.
        "exposure_index":       0.30,
        "notes":                "Short parkland birdie-fest; Travelers Championship (Signature, no-cut); water hazards 15-17 dominate risk profile",
    },
    {
        "course_key":           "tpc_deere_run",
        "course_name":          "TPC Deere Run",
        "location":             "Silvis, IL",
        "par":                  71,
        "yardage":              7327,
        "tour":                 "pga",
        # Low raw penalty fraction (0.026); soft/wet conditions in 2026
        # further reduced bomb-and-spray cost by 30-50 %.
        "miss_penalty_index":   2,
        "turf_firmness_tag":    "soft",
        "green_contour_rating": "flat",
        # Inland Illinois; tree-lined routing offers meaningful wind shelter.
        "exposure_index":       0.20,
        "notes":                "Parkland birdie-fest; John Deere Classic; approach under 150 yds is primary scoring zone; par-5 conversion critical",
    },
    {
        "course_key":           "renaissance_club",
        "course_name":          "The Renaissance Club",
        "location":             "North Berwick, East Lothian, Scotland",
        "par":                  71,
        "yardage":              7103,
        "tour":                 "pga",
        # Links rough is "penal, thick, variable"; penalty is positional
        # and recovery-difficulty-based rather than hazard-based.
        "miss_penalty_index":   3,
        "turf_firmness_tag":    "firm",
        # Fast links greens; pace and true roll vary significantly with wind.
        "green_contour_rating": "severe",
        # Coastal East Lothian; prevailing SW wind; one of the most exposed
        # venues in the portfolio.
        "exposure_index":       0.92,
        "notes":                "Scottish links; Genesis Scottish Open (DP World / PGA co-sanction); iron-first / 150-200 yd approach dominant; wind is primary variance driver",
    },
    {
        "course_key":           "harbour_town_golf_links",
        "course_name":          "Harbour Town Golf Links",
        "location":             "Hilton Head Island, SC",
        "par":                  71,
        "yardage":              7100,
        "tour":                 "pga",
        # Trees + water are real penalties; tiny TifEagle Bermuda targets
        # amplify approach misses; raw fraction 0.0328.
        "miss_penalty_index":   3,
        "turf_firmness_tag":    "firm",
        # Modest internal contour; difficulty comes from green size and
        # grain, not severe slopes.
        "green_contour_rating": "flat",
        # Mostly tree-sheltered interior; exposed closing stretch 16-18
        # along Calibogue Sound lifts exposure above true-inland baseline.
        "exposure_index":       0.50,
        "notes":                "Pete Dye second-shot course; RBC Heritage; 2024-25 Love GD restoration; Bermuda putting surface (grain-sensitive); tiny greens demand approach precision",
    },
    {
        "course_key":           "detroit_golf_club",
        "course_name":          "Detroit Golf Club",
        "location":             "Detroit, MI",
        "par":                  72,
        "yardage":              7345,
        "tour":                 "pga",
        # Classic Ross parkland; forgiving routing with moderate rough;
        # trees channel misses but recovery lies are generally clean.
        "miss_penalty_index":   2,
        "turf_firmness_tag":    "soft",
        # Donald Ross greens — undulating but not brutally tiered;
        # summer softness keeps them receptive.
        "green_contour_rating": "flat",
        # Inland Michigan, dense tree canopy; wind effect is minimal.
        "exposure_index":       0.15,
        "notes":                "Donald Ross parkland; Rocket Mortgage Classic; birdie-friendly; approach proximity and putting conversion separate the field",
    },
]


# ── schema migration ──────────────────────────────────────────────────────────

_NEW_COLUMNS = [
    ("miss_penalty_index",   "INTEGER"),
    ("turf_firmness_tag",    "TEXT"),
    ("green_contour_rating", "TEXT"),
    ("exposure_index",       "REAL"),
]


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """
    Add any missing columns to course_profiles without dropping existing data.
    SQLite does not support IF NOT EXISTS for ALTER TABLE, so we catch the
    OperationalError that fires when the column already exists.
    """
    for col_name, col_type in _NEW_COLUMNS:
        try:
            conn.execute(
                f"ALTER TABLE course_profiles ADD COLUMN {col_name} {col_type}"
            )
            conn.commit()
            log.info("Added column course_profiles.%s", col_name)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" in str(exc).lower():
                pass  # column already present — nothing to do
            else:
                raise


# ── seeder ────────────────────────────────────────────────────────────────────

def seed_venues(conn: sqlite3.Connection) -> None:
    _ensure_columns(conn)

    sql = """
        INSERT OR REPLACE INTO course_profiles (
            course_key,
            course_name,
            location,
            par,
            yardage,
            tour,
            miss_penalty_index,
            turf_firmness_tag,
            green_contour_rating,
            exposure_index,
            notes,
            updated_at
        ) VALUES (
            :course_key,
            :course_name,
            :location,
            :par,
            :yardage,
            :tour,
            :miss_penalty_index,
            :turf_firmness_tag,
            :green_contour_rating,
            :exposure_index,
            :notes,
            datetime('now')
        )
    """

    conn.executemany(sql, VENUES)
    conn.commit()
    log.info("Seeded %d course profiles.", len(VENUES))


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    conn = init_db()
    seed_venues(conn)

    rows = conn.execute(
        "SELECT course_key, miss_penalty_index, turf_firmness_tag, "
        "green_contour_rating, exposure_index FROM course_profiles ORDER BY course_key"
    ).fetchall()

    print(f"\n{'course_key':<30} {'mpi':>3}  {'firmness':<6}  {'contour':<7}  {'exp':>5}")
    print("-" * 62)
    for r in rows:
        print(
            f"{r['course_key']:<30} {r['miss_penalty_index']:>3}  "
            f"{r['turf_firmness_tag']:<6}  {r['green_contour_rating']:<7}  "
            f"{r['exposure_index']:>5.2f}"
        )

    conn.close()
