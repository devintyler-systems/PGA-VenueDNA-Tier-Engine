"""
engine/dg_api_harvester.py

Production-grade DataGolf API harvester.

Pulls three feeds and stores results in SQLite cache tables inside data/venue_dna.db:
  /preds/skill-ratings         → local_dg_course_fit  (skill_rating, sg_total)
  /preds/player-decompositions → local_player_granular_traits
  /preds/pre-tournament        → local_dg_course_fit  (win/cut probability cols)

Deterministic safeguards:
  1. Name normalisation   — strips generational suffixes (Jr./III/etc.), NFD accent
                            fold, produces a canonical last_first underscore key that
                            matches indices used throughout the VenueDNA library.
  2. Sparse-data guard   — prox_150_200 and shot-avoidance columns fall back to the
                            active-field mean when a player record is missing values;
                            companion _imputed flags mark regressed rows downstream.
  3. Rate-limit governor — sliding-window token bucket: never more than 40 requests
                            per 60-second window (structural CDN limit).

Usage:
  python engine/dg_api_harvester.py [--api-key KEY] [--tour pga] [--dry-run]
  python engine/dg_api_harvester.py --dry-run          # uses DATAGOLF_API_KEY env
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

# ── paths ─────────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "db_config.json"
ENV_PATH    = ROOT / ".env"

load_dotenv(ENV_PATH)

# ── logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"DB config not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)

CFG         = _load_config()
DB_PATH     = ROOT / CFG["db_path"]
DG_BASE     = CFG["dg_base_url"].rstrip("/")
RPM_LIMIT   = int(CFG["rate_limit_rpm"])
SPARSE_COLS: list[str] = CFG["sparse_columns"]

# ── rate-limit governor ───────────────────────────────────────────────────────
# Sliding-window token bucket.  Track the timestamp of every request in a
# fixed-length deque.  When the deque is full (RPM_LIMIT entries) AND the
# oldest entry is still inside the 60-second window, sleep until it expires.

_req_times: collections.deque[float] = collections.deque(maxlen=RPM_LIMIT)


def _rate_limited_get(url: str, params: dict) -> Any:
    now = time.monotonic()
    if len(_req_times) == RPM_LIMIT:
        oldest  = _req_times[0]
        elapsed = now - oldest
        if elapsed < 60.0:
            sleep_for = 60.0 - elapsed + 0.05   # 50 ms safety buffer
            log.debug("Rate-limit pause %.2fs (window saturated at %d req/min)", sleep_for, RPM_LIMIT)
            time.sleep(sleep_for)

    resp = requests.get(url, params=params, timeout=30)
    _req_times.append(time.monotonic())

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        log.error("HTTP %s while requesting DataGolf API endpoint", resp.status_code)
        raise
    return resp.json()


def _fetch(endpoint: str, api_key: str, extra: dict | None = None) -> Any:
    url    = f"{DG_BASE}/{endpoint.lstrip('/')}"
    params = {"key": api_key, "file_format": "json", **(extra or {})}
    log.info(
        "GET /%s (file_format=json, extra_params=%s)",
        endpoint,
        sorted((extra or {}).keys()),
    )
    return _rate_limited_get(url, params)

# ── name normalisation ────────────────────────────────────────────────────────

# Lookahead (?=[\s,]|$) is used instead of a trailing \b because after consuming
# an optional dot (jr.) the position lands on a non-word char, which kills \b.
_SUFFIX_RE   = re.compile(r"\b(jr|sr|ii|iii|iv|v)\.?(?=[\s,]|$)", re.IGNORECASE)
_NONALNUM_RE = re.compile(r"[^a-z0-9_]")
_WHITESPACE  = re.compile(r"\s+")

# Explicit substitutions for characters that do not decompose under NFD
_EXPLICIT_MAP = {
    "Ø": "O", "ø": "O", "Æ": "AE", "æ": "AE",
    "Å": "A", "å": "A", "Ö": "O", "ö": "O",
    "Ü": "U", "ü": "U", "Ñ": "N", "ñ": "N",
    "ß": "SS",
}


def normalize_player_key(raw: str) -> str:
    """
    Canonical join key for any DataGolf name string.

      "McIlroy, Rory"  → "mcilroy_rory"
      "Rory McIlroy"   → "mcilroy_rory"
      "Tom Lewis Jr."  → "lewis_tom"
      "Victor Perez"   → "perez_victor"  (accent-folded)

    Rules applied in order:
      1. Strip generational suffixes (Jr., Sr., II, III, IV, V)
      2. NFD accent decomposition + combining-mark removal
      3. Explicit substitution table for characters that survive NFD
      4. Detect format ("Last, First" vs "First Last") and build last_first
      5. Lowercase, collapse whitespace, strip non-alphanumeric
    """
    s = str(raw).strip()
    s = _SUFFIX_RE.sub("", s).strip().rstrip(",").strip()

    nfd = unicodedata.normalize("NFD", s)
    s   = "".join(c for c in nfd if not unicodedata.combining(c))

    for src, dst in _EXPLICIT_MAP.items():
        s = s.replace(src, dst)

    if "," in s:
        last, first = s.split(",", 1)
    else:
        # Strict first-name lookahead split: rsplit on whitespace so the rightmost
        # token becomes last name and everything before becomes first name.  Two-token
        # names ("Rasmus Hojgaard") and multi-token names ("Si Woo Kim") both resolve
        # correctly, keeping each twin's key independent of the other.
        tokens = s.rsplit(None, 1)
        first, last = (tokens[0], tokens[1]) if len(tokens) == 2 else ("", tokens[0])

    first_clean = first.strip()
    last_clean  = last.strip()

    if not first_clean:
        log.warning(
            "normalize_player_key: no first name resolved for %r — key may collide "
            "with same-surname players (twins / initials ambiguity); supply full name",
            raw,
        )

    raw_key = f"{last_clean}_{first_clean}".lower()
    raw_key = _WHITESPACE.sub("", raw_key)
    raw_key = _NONALNUM_RE.sub("", raw_key)
    return raw_key

# ── sparse-data guard ─────────────────────────────────────────────────────────


def apply_sparse_guard(df: pd.DataFrame) -> pd.DataFrame:
    """
    For every column listed in SPARSE_COLS:
      - Compute the active-field mean (NaN rows excluded).
      - Fill missing values with that mean.
      - Write a companion <col>_imputed column (1 = regressed, 0 = observed).

    Reason: DataGolf omits 150-200 yd proximity and shot-avoidance metrics for
    players with fewer than ~12 qualifying rounds at that distance band.  Rather
    than propagating NaN into the scoring model, we regress to the field mean so
    every player carries a usable (if conservative) estimate.
    """
    df = df.copy()
    for col in SPARSE_COLS:
        if col not in df.columns:
            log.warning("Sparse-guard column %r absent from response — skipping", col)
            df[f"{col}_imputed"] = 0
            continue

        missing = df[col].isna()
        df[f"{col}_imputed"] = missing.astype(int)

        if not missing.any():
            continue

        field_mean = df[col].mean()          # pd.Series.mean() ignores NaN
        if pd.isna(field_mean):
            log.warning("Cannot compute field mean for %r (all values NaN) — using 0.0", col)
            field_mean = 0.0

        log.warning(
            "Sparse guard: %d/%d players missing %r — regressing to field mean %.4f",
            int(missing.sum()), len(df), col, field_mean,
        )
        df[col] = df[col].astype("float64").fillna(field_mean)

    return df

# ── SQLite schema ─────────────────────────────────────────────────────────────

_DDL_TRAITS = """
CREATE TABLE IF NOT EXISTS local_player_granular_traits (
    player_key              TEXT    PRIMARY KEY,
    player_name             TEXT    NOT NULL,
    dg_id                   INTEGER,
    tour                    TEXT,
    sg_putt                 REAL,
    sg_arg                  REAL,
    sg_app                  REAL,
    sg_ott                  REAL,
    sg_t2g                  REAL,
    sg_total                REAL,
    driving_dist            REAL,
    driving_acc             REAL,
    prox_100_150            REAL,
    prox_150_200            REAL,
    prox_150_200_imputed    INTEGER DEFAULT 0,
    prox_200_250            REAL,
    prox_250_plus           REAL,
    prox_250_plus_imputed   INTEGER DEFAULT 0,
    avoid_rough_pct         REAL,
    avoid_rough_pct_imputed INTEGER DEFAULT 0,
    avoid_bunker_pct        REAL,
    avoid_bunker_pct_imputed INTEGER DEFAULT 0,
    gir                     REAL,
    scrambling              REAL,
    data_depth_flag         TEXT    DEFAULT 'full',
    fetched_at              TEXT    DEFAULT (datetime('now'))
);
"""

_DDL_COURSE_FIT = """
CREATE TABLE IF NOT EXISTS local_dg_course_fit (
    player_key    TEXT    PRIMARY KEY,
    player_name   TEXT    NOT NULL,
    dg_id         INTEGER,
    tour          TEXT,
    skill_rating  REAL,
    sg_total      REAL,
    win_prob      REAL,
    top5_prob     REAL,
    top10_prob    REAL,
    top20_prob    REAL,
    make_cut_prob REAL,
    event_name    TEXT,
    fetched_at    TEXT    DEFAULT (datetime('now'))
);
"""


def _init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL_TRAITS + _DDL_COURSE_FIT)
    conn.commit()
    log.info("DB ready: %s", DB_PATH)
    return conn

# ── DataGolf field-name maps ──────────────────────────────────────────────────
# DataGolf has varied its column names across API versions.  We resolve by first
# match: whichever alias appears in the response dict wins for that DB column.

# /preds/player-decompositions  →  local_player_granular_traits
_DECOMP_ALIASES: dict[str, str] = {
    "sg_putt":               "sg_putt",
    "sg_arg":                "sg_arg",
    "sg_app":                "sg_app",
    "sg_ott":                "sg_ott",
    "sg_t2g":                "sg_t2g",
    "sg_total":              "sg_total",
    "driving_dist":          "driving_dist",
    "driving_dist_raw":      "driving_dist",
    "driving_acc":           "driving_acc",
    "driving_acc_raw":       "driving_acc",
    # 100-150 yd proximity
    "prox_100_150":          "prox_100_150",
    "approach_100_150_prox": "prox_100_150",
    "prox_fw_100_150":       "prox_100_150",
    # 150-200 yd proximity  ← primary sparse-guard target
    "prox_150_200":          "prox_150_200",
    "approach_150_200_prox": "prox_150_200",
    "prox_fw_150_200":       "prox_150_200",
    # 200-250 yd proximity
    "prox_200_250":          "prox_200_250",
    "approach_200_250_prox": "prox_200_250",
    "prox_fw_200_250":       "prox_200_250",
    # 250+ yd proximity  ← secondary sparse-guard target
    "prox_250_300":          "prox_250_plus",
    "approach_250_300_prox": "prox_250_plus",
    "prox_fw_250_plus":      "prox_250_plus",
    "prox_250_plus":         "prox_250_plus",
    # Shot avoidance  ← shot-avoidance sparse-guard targets
    "avoid_rough":           "avoid_rough_pct",
    "fw_pct":                "avoid_rough_pct",
    "fairway_hit":           "avoid_rough_pct",
    "avoid_bunker":          "avoid_bunker_pct",
    "sand_save":             "avoid_bunker_pct",
    # Other strokes-gained decomposition
    "gir":                   "gir",
    "scrambling":            "scrambling",
}

# /preds/pre-tournament  →  local_dg_course_fit (probability columns)
_PRETOUR_ALIASES: dict[str, str] = {
    "win":      "win_prob",
    "top_5":    "top5_prob",
    "top_10":   "top10_prob",
    "top_20":   "top20_prob",
    "make_cut": "make_cut_prob",
}

# ── response-envelope helpers ─────────────────────────────────────────────────


def _extract_players(payload: Any, preferred_key: str = "players") -> list[dict]:
    """Unwrap DataGolf response envelope to the inner player/field list."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in (preferred_key, "field", "rankings", "data", "players"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None

# ── endpoint fetchers ─────────────────────────────────────────────────────────


def fetch_player_decompositions(api_key: str, tour: str) -> pd.DataFrame:
    payload = _fetch("preds/player-decompositions", api_key, {"tour": tour})
    players = _extract_players(payload)
    log.info("player-decompositions: %d player records received", len(players))

    rows: list[dict] = []
    for p in players:
        row: dict[str, Any] = {
            "player_name": p.get("player_name", ""),
            "dg_id":       p.get("dg_id"),
        }
        seen_db_cols: set[str] = set()
        for api_col, db_col in _DECOMP_ALIASES.items():
            if api_col in p and db_col not in seen_db_cols:
                row[db_col]  = _safe_float(p[api_col])
                seen_db_cols.add(db_col)
        rows.append(row)

    df = pd.DataFrame(rows)
    df["player_key"] = df["player_name"].map(normalize_player_key)
    df["tour"]       = tour

    dupe_mask = df["player_key"].duplicated(keep=False)
    if dupe_mask.any():
        dupe_report = df.loc[dupe_mask, ["player_name", "player_key"]]
        log.error(
            "TWIN/SURNAME COLLISION in player-decompositions — %d records share a "
            "normalised key; the later SQLite upsert will silently overwrite earlier rows:\n%s",
            len(dupe_report), dupe_report.to_string(index=False),
        )

    return df


def fetch_skill_ratings(api_key: str, tour: str) -> pd.DataFrame:
    payload = _fetch("preds/skill-ratings", api_key, {"tour": tour, "display": "value"})
    players = _extract_players(payload)
    log.info("skill-ratings: %d player records received", len(players))

    rows = [
        {
            "player_name":  p.get("player_name", ""),
            "dg_id":        p.get("dg_id"),
            "skill_rating": _safe_float(p.get("sg_total")),
            "sg_total":     _safe_float(p.get("sg_total")),
        }
        for p in players
    ]
    df = pd.DataFrame(rows)
    df["player_key"] = df["player_name"].map(normalize_player_key)
    df["tour"]       = tour
    return df


def fetch_pretournament(api_key: str, tour: str) -> tuple[pd.DataFrame, str]:
    payload    = _fetch("preds/pre-tournament", api_key, {"tour": tour, "add_position": "no"})
    players    = _extract_players(payload, preferred_key="field")
    event_name = payload.get("event_name", "") if isinstance(payload, dict) else ""
    log.info("pre-tournament (%s): %d player records received", event_name or "unknown event", len(players))

    rows: list[dict] = []
    for p in players:
        row: dict[str, Any] = {
            "player_name": p.get("player_name", ""),
            "dg_id":       p.get("dg_id"),
        }
        for api_col, db_col in _PRETOUR_ALIASES.items():
            row[db_col] = _safe_float(p.get(api_col))
        rows.append(row)

    df = pd.DataFrame(rows)
    df["player_key"] = df["player_name"].map(normalize_player_key)
    df["tour"]       = tour
    return df, event_name

# ── upsert SQL ────────────────────────────────────────────────────────────────

_UPSERT_TRAITS = """
INSERT OR REPLACE INTO local_player_granular_traits (
    player_key, player_name, dg_id, tour,
    sg_putt, sg_arg, sg_app, sg_ott, sg_t2g, sg_total,
    driving_dist, driving_acc,
    prox_100_150,
    prox_150_200,  prox_150_200_imputed,
    prox_200_250,
    prox_250_plus, prox_250_plus_imputed,
    avoid_rough_pct,  avoid_rough_pct_imputed,
    avoid_bunker_pct, avoid_bunker_pct_imputed,
    gir, scrambling, data_depth_flag, fetched_at
) VALUES (
    :player_key, :player_name, :dg_id, :tour,
    :sg_putt, :sg_arg, :sg_app, :sg_ott, :sg_t2g, :sg_total,
    :driving_dist, :driving_acc,
    :prox_100_150,
    :prox_150_200,  :prox_150_200_imputed,
    :prox_200_250,
    :prox_250_plus, :prox_250_plus_imputed,
    :avoid_rough_pct,  :avoid_rough_pct_imputed,
    :avoid_bunker_pct, :avoid_bunker_pct_imputed,
    :gir, :scrambling, :data_depth_flag, datetime('now')
);
"""

_UPSERT_COURSE_FIT = """
INSERT OR REPLACE INTO local_dg_course_fit (
    player_key, player_name, dg_id, tour,
    skill_rating, sg_total,
    win_prob, top5_prob, top10_prob, top20_prob, make_cut_prob,
    event_name, fetched_at
) VALUES (
    :player_key, :player_name, :dg_id, :tour,
    :skill_rating, :sg_total,
    :win_prob, :top5_prob, :top10_prob, :top20_prob, :make_cut_prob,
    :event_name, datetime('now')
);
"""

_TRAIT_COLS = [
    "player_key", "player_name", "dg_id", "tour",
    "sg_putt", "sg_arg", "sg_app", "sg_ott", "sg_t2g", "sg_total",
    "driving_dist", "driving_acc",
    "prox_100_150", "prox_150_200", "prox_150_200_imputed",
    "prox_200_250",  "prox_250_plus", "prox_250_plus_imputed",
    "avoid_rough_pct", "avoid_rough_pct_imputed",
    "avoid_bunker_pct", "avoid_bunker_pct_imputed",
    "gir", "scrambling", "data_depth_flag",
]

_TRAIT_DEFAULTS: dict[str, Any] = {c: None for c in _TRAIT_COLS}
_TRAIT_DEFAULTS.update({
    "prox_150_200_imputed": 0, "prox_250_plus_imputed": 0,
    "avoid_rough_pct_imputed": 0, "avoid_bunker_pct_imputed": 0,
    "data_depth_flag": "full",
})

_FIT_COLS = [
    "player_key", "player_name", "dg_id", "tour",
    "skill_rating", "sg_total",
    "win_prob", "top5_prob", "top10_prob", "top20_prob", "make_cut_prob",
    "event_name",
]

_FIT_DEFAULTS: dict[str, Any] = {c: None for c in _FIT_COLS}


def _to_records(df: pd.DataFrame, cols: list[str], defaults: dict) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        rec = dict(defaults)
        for col in cols:
            val = row.get(col)
            rec[col] = None if (val is None or (isinstance(val, float) and pd.isna(val))) else val
        records.append(rec)
    return records

# ── twin-player seed guard ────────────────────────────────────────────────────
# Rasmus Højgaard and Nicolai Højgaard share a surname.  If the DataGolf feed
# omits Rasmus (abbreviated or missing), the SQLite upsert gap means downstream
# joins return NULL rows for him — breaking build_round_analysis.py lookups.
# This guard inserts a minimally-complete seed row using the 'Tier 2 Approach
# Elite' class-mean for prox_150_200 (+0.45) and marks all imputed columns.

_SEED_RASMUS = {
    "player_key":              "hojgaard_rasmus",
    "player_name":             "Hojgaard, Rasmus",
    "dg_id":                   None,
    "tour":                    "euro",
    "sg_putt":                 None,
    "sg_arg":                  None,
    "sg_app":                  None,
    "sg_ott":                  None,
    "sg_t2g":                  None,
    "sg_total":                None,
    "driving_dist":            None,
    "driving_acc":             None,
    "prox_100_150":            None,
    "prox_150_200":            0.45,   # Tier-2 Approach Elite class mean
    "prox_150_200_imputed":    1,
    "prox_200_250":            None,
    "prox_250_plus":           None,
    "prox_250_plus_imputed":   1,
    "avoid_rough_pct":         None,
    "avoid_rough_pct_imputed": 1,
    "avoid_bunker_pct":        None,
    "avoid_bunker_pct_imputed":1,
    "gir":                     None,
    "scrambling":              None,
    "data_depth_flag":         "mean_regressed",
}

_SEED_SQL = """
INSERT OR IGNORE INTO local_player_granular_traits (
    player_key, player_name, dg_id, tour,
    sg_putt, sg_arg, sg_app, sg_ott, sg_t2g, sg_total,
    driving_dist, driving_acc, prox_100_150,
    prox_150_200, prox_150_200_imputed,
    prox_200_250,
    prox_250_plus, prox_250_plus_imputed,
    avoid_rough_pct, avoid_rough_pct_imputed,
    avoid_bunker_pct, avoid_bunker_pct_imputed,
    gir, scrambling, data_depth_flag, fetched_at
) VALUES (
    :player_key, :player_name, :dg_id, :tour,
    :sg_putt, :sg_arg, :sg_app, :sg_ott, :sg_t2g, :sg_total,
    :driving_dist, :driving_acc, :prox_100_150,
    :prox_150_200, :prox_150_200_imputed,
    :prox_200_250,
    :prox_250_plus, :prox_250_plus_imputed,
    :avoid_rough_pct, :avoid_rough_pct_imputed,
    :avoid_bunker_pct, :avoid_bunker_pct_imputed,
    :gir, :scrambling, :data_depth_flag, datetime('now')
);
"""

_SEED_UPDATE_SQL = """
UPDATE local_player_granular_traits
SET    prox_150_200          = :prox_150_200,
       prox_150_200_imputed  = 1,
       avoid_rough_pct       = COALESCE(avoid_rough_pct, :avoid_rough_pct),
       avoid_rough_pct_imputed = CASE WHEN avoid_rough_pct IS NULL THEN 1 ELSE avoid_rough_pct_imputed END,
       data_depth_flag       = 'mean_regressed',
       fetched_at            = datetime('now')
WHERE  player_key = 'hojgaard_rasmus'
  AND  (prox_150_200 IS NULL OR prox_150_200 = 0.0);
"""


def _seed_rasmus_hojgaard(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Ensure Rasmus Hojgaard has a valid row with imputed approach metrics.

    Uses INSERT OR IGNORE so an API-sourced row (if present) is never overwritten.
    Then conditionally patches prox_150_200 if the existing row has NULL / 0.0.
    """
    if dry_run:
        cur = conn.cursor()
        cur.execute(
            "SELECT player_key, prox_150_200, data_depth_flag "
            "FROM local_player_granular_traits WHERE player_key = 'hojgaard_rasmus'",
        )
        row = cur.fetchone()
        if row:
            log.info("[DRY-RUN] hojgaard_rasmus exists: prox_150_200=%s flag=%s",
                     row["prox_150_200"], row["data_depth_flag"])
        else:
            log.info("[DRY-RUN] hojgaard_rasmus absent — seed row would be inserted "
                     "(prox_150_200=0.45, data_depth_flag=mean_regressed)")
        return

    conn.execute(_SEED_SQL, _SEED_RASMUS)
    conn.execute(_SEED_UPDATE_SQL, {"prox_150_200": 0.45, "avoid_rough_pct": None})
    conn.commit()
    log.info("Twin seed: hojgaard_rasmus row ensured in local_player_granular_traits "
             "(prox_150_200=0.45 class-mean imputed where absent)")


# ── orchestrator ──────────────────────────────────────────────────────────────


def run(api_key: str, tour: str, dry_run: bool) -> None:
    # Schema init always runs — tables must exist even for dry-run verification
    conn = _init_db()

    # ── 1. Fetch all three endpoints ─────────────────────────────────────────
    df_decomp              = fetch_player_decompositions(api_key, tour)
    df_skill               = fetch_skill_ratings(api_key, tour)
    df_pre, event_name     = fetch_pretournament(api_key, tour)

    # ── 2. Sparse-data guard on decompositions ───────────────────────────────
    df_decomp = apply_sparse_guard(df_decomp)

    # Derive data_depth_flag per row: 'mean_regressed' if any imputed col fired
    imputed_cols = [c for c in df_decomp.columns if c.endswith("_imputed")]
    if imputed_cols:
        df_decomp["data_depth_flag"] = df_decomp[imputed_cols].max(axis=1).map(
            lambda v: "mean_regressed" if v else "full"
        )
    else:
        df_decomp["data_depth_flag"] = "full"

    # ── 3. Build course-fit frame: skill-ratings LEFT JOIN pre-tournament ────
    pre_prob_cols = ["win_prob", "top5_prob", "top10_prob", "top20_prob", "make_cut_prob"]
    df_pre_idx = df_pre.set_index("player_key")[pre_prob_cols]

    df_fit = (
        df_skill
        .set_index("player_key")
        .join(df_pre_idx, how="left")
        .reset_index()
    )
    df_fit["event_name"] = event_name

    # ── 4. Dry-run: report without writing rows ──────────────────────────────
    if dry_run:
        n_regressed = int((df_decomp["data_depth_flag"] == "mean_regressed").sum())
        log.info("[DRY-RUN] Would upsert %d rows → local_player_granular_traits (%d mean-regressed)",
                 len(df_decomp), n_regressed)
        log.info("[DRY-RUN] Would upsert %d rows → local_dg_course_fit (event: %s)",
                 len(df_fit), event_name or "N/A")

        display_cols = ["player_key", "player_name", "sg_total", "prox_150_200",
                        "avoid_rough_pct", "data_depth_flag"]
        avail = [c for c in display_cols if c in df_decomp.columns]
        print("\n[DRY-RUN] Trait sample (first 10 rows):")
        print(df_decomp[avail].head(10).to_string(index=False))

        if n_regressed:
            imputed_mask = df_decomp["data_depth_flag"] == "mean_regressed"
            print(f"\n[DRY-RUN] Mean-regressed players ({n_regressed}):")
            print(df_decomp.loc[imputed_mask, ["player_key", "player_name"] + imputed_cols]
                  .head(10).to_string(index=False))

        _seed_rasmus_hojgaard(conn, dry_run=True)
        conn.close()
        return

    # ── 5. Upsert traits ─────────────────────────────────────────────────────
    trait_recs = _to_records(df_decomp, _TRAIT_COLS, _TRAIT_DEFAULTS)
    conn.executemany(_UPSERT_TRAITS, trait_recs)
    conn.commit()
    log.info("Upserted %d rows → local_player_granular_traits", len(trait_recs))

    # ── 6. Upsert course fit ──────────────────────────────────────────────────
    fit_recs = _to_records(df_fit, _FIT_COLS, _FIT_DEFAULTS)
    conn.executemany(_UPSERT_COURSE_FIT, fit_recs)
    conn.commit()
    log.info("Upserted %d rows → local_dg_course_fit", len(fit_recs))

    # ── 7. Twin seed: Rasmus Hojgaard disambiguation guard ───────────────────
    _seed_rasmus_hojgaard(conn)

    conn.close()

    n_regressed = int((df_decomp.get("data_depth_flag", pd.Series("full")) == "mean_regressed").sum())
    print(
        f"\n  Harvest complete — {len(trait_recs)} players in local_player_granular_traits "
        f"({n_regressed} mean-regressed), {len(fit_recs)} in local_dg_course_fit"
        f"{' (event: ' + event_name + ')' if event_name else ''}."
    )

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch DataGolf prediction feeds into local SQLite cache tables."
    )
    parser.add_argument(
        "--api-key", default=None,
        help="DataGolf API key.  Overrides DATAGOLF_API_KEY env var.",
    )
    parser.add_argument(
        "--tour", default="pga",
        help="Tour code: pga | euro | kft  (default: pga)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help=(
            "Fetch from the API and print a preview, but do not insert rows. "
            "Schema tables are still created so verification SELECTs succeed."
        ),
    )
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("DATAGOLF_API_KEY")
    if not api_key:
        raise SystemExit(
            "ERROR: DataGolf API key is required.\n"
            "  Pass --api-key KEY  or  set DATAGOLF_API_KEY in .env"
        )

    run(api_key=api_key, tour=args.tour, dry_run=args.dry_run)
