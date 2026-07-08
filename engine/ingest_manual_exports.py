"""
Ingest manual DataGolf CSV exports into active_field_projections.

Workflow:
  1. Load the three True SG CSV files from an event's input/ directory
  2. Compute the four venue-fitness trait scores via calculate_traits
  3. Fetch the live weekly field from the DataGolf API to obtain dg_id per player
  4. Join traits to the live field on a normalised name key
  5. Upsert the matched rows into active_field_projections in venuedna_master.db

Name matching: the CSV uses "Last, First" format; the DataGolf field API returns
"First Last".  Both are normalised to a stripped, lowercase, whitespace-free key
(e.g. "mcilroy_rory").  Compound surnames like "Van Rooyen" will appear in the
unmatched log when the API returns them in "First Last" order.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

import pandas as pd

from engine.calculate_traits import compute_traits, load_trait_inputs
from engine.datagolf_client import DB_PATH, fetch_weekly_field, init_db

log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parent.parent
EVENT_DIR = ROOT / "events" / "2026_GenesisScottishOpen" / "input"

# ── schema ────────────────────────────────────────────────────────────────────

_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS active_field_projections (
        dg_id        TEXT PRIMARY KEY,
        player_name  TEXT NOT NULL,
        tvl_score    REAL,
        hew_score    REAL,
        brie_score   REAL,
        vfr_score    REAL,
        event_dir    TEXT,
        ingested_at  TEXT DEFAULT (datetime('now'))
    );
"""

_UPSERT = """
    INSERT OR REPLACE INTO active_field_projections
        (dg_id, player_name, tvl_score, hew_score, brie_score, vfr_score, event_dir)
    VALUES
        (:dg_id, :player_name, :tvl_score, :hew_score, :brie_score, :vfr_score, :event_dir)
"""


# ── name normalisation ────────────────────────────────────────────────────────

def _name_key(s: str) -> str:
    """
    Produce a lowercase, whitespace-free join key from either name format.

      "Last, First"  →  "last_first"
      "First Last"   →  "last_first"  (rsplit on final space)

    Non-ASCII and punctuation are stripped so accented letters don't block matches.
    """
    s = s.strip()
    if ", " in s:
        last, first = s.split(", ", 1)
    else:
        tokens = s.rsplit(None, 1)
        first, last = (tokens[0], tokens[1]) if len(tokens) == 2 else ("", s)
    raw = f"{last.strip()}_{first.strip()}".lower()
    raw = re.sub(r"\s+", "", raw)          # collapse internal spaces
    raw = re.sub(r"[^a-z0-9_]", "", raw)  # drop accents / punctuation
    return raw


# ── main ──────────────────────────────────────────────────────────────────────

def ingest(
    event_input_dir: Path | str | None = None,
    tour: str = "pga",
) -> None:
    """
    Compute traits from CSV exports and cache matched field players to DB.

    Parameters
    ----------
    event_input_dir:
        Directory containing dg_true_sg_6m/12m/24m.csv.
        Defaults to the 2026 Genesis Scottish Open input folder.
    tour:
        Tour code passed to fetch_weekly_field().  Defaults to "pga".
    """
    if event_input_dir is None:
        event_input_dir = EVENT_DIR
    event_input_dir = Path(event_input_dir)

    # ── 1. trait scores from CSV ──────────────────────────────────────────────
    log.info("Loading trait inputs from %s", event_input_dir)
    df_raw    = load_trait_inputs(event_input_dir)
    df_traits = compute_traits(df_raw)          # indexed by "Last, First" player_name
    log.info("Traits computed for %d players from CSV exports", len(df_traits))

    # ── 2. live field → dg_id lookup ─────────────────────────────────────────
    log.info("Fetching live %s field from DataGolf API...", tour.upper())
    field_raw = fetch_weekly_field(tour=tour)

    field_df = pd.DataFrame(field_raw)[["player_name", "dg_id"]]
    field_df["_key"] = field_df["player_name"].apply(_name_key)
    field_df = field_df.drop_duplicates("_key").set_index("_key")
    log.info("API returned %d players in the live field", len(field_df))

    # ── 3. join on normalised name key ────────────────────────────────────────
    trait_keys = df_traits.index.map(_name_key)
    df_traits  = df_traits.copy()
    df_traits.index = trait_keys

    merged = field_df.join(df_traits, how="inner")

    unmatched = field_df.index.difference(df_traits.index).tolist()
    if unmatched:
        log.warning(
            "%d field players had no CSV trait match (compound surnames or "
            "spelling differences): %s",
            len(unmatched),
            [field_df.loc[k, "player_name"] for k in unmatched[:10]],
        )

    log.info("Matched %d / %d field players to trait scores", len(merged), len(field_df))

    # ── 4. upsert into DB ────────────────────────────────────────────────────
    conn = init_db()
    conn.execute(_CREATE_TABLE)
    conn.commit()

    records = []
    for _, row in merged.iterrows():
        records.append({
            "dg_id":      str(row["dg_id"]),
            "player_name": row["player_name"],
            "tvl_score":  None if pd.isna(row["tvl_score"])  else round(float(row["tvl_score"]),  4),
            "hew_score":  None if pd.isna(row["hew_score"])  else round(float(row["hew_score"]),  4),
            "brie_score": None if pd.isna(row["brie_score"]) else round(float(row["brie_score"]), 4),
            "vfr_score":  None if pd.isna(row["vfr_score"])  else round(float(row["vfr_score"]),  4),
            "event_dir":  str(event_input_dir),
        })

    conn.executemany(_UPSERT, records)
    conn.commit()
    conn.close()

    # ── 5. success report ─────────────────────────────────────────────────────
    fully_scored = sum(
        1 for r in records
        if all(r[k] is not None for k in ("tvl_score", "hew_score", "brie_score", "vfr_score"))
    )

    print(
        f"\n  Ingest complete — {len(records)} tournament field players matched "
        f"and cached to active_field_projections "
        f"({fully_scored} with all four trait scores computed)."
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(
        description="Ingest DataGolf True SG CSV exports into active_field_projections."
    )
    parser.add_argument(
        "--input-dir", "-i",
        default=None,
        help="Path to event input/ directory containing the three dg_true_sg_*.csv files. "
             "Defaults to events/2026_GenesisScottishOpen/input/",
    )
    parser.add_argument(
        "--tour", "-t",
        default="pga",
        help="Tour code for fetch_weekly_field() (default: pga)",
    )
    args = parser.parse_args()

    ingest(
        event_input_dir=args.input_dir,
        tour=args.tour,
    )
