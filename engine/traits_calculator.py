"""
VenueDNA Traits Calculator v2 — engine/traits_calculator.py

Extends the base trait pipeline to compute the BRIE-Z sub-driver,
apply course difficulty re-anchoring, and inject wave draw scalars.

Reads:
  - input/approach_skill_Last12mon.csv  (app_150_200_fw_sg)
  - local_player_granular_traits        (avoid_rough_pct → poor_shot_avoidance)
  - course_profiles                     (difficulty_app_rough_vs_fw)
  - input/r1_pairings.csv               (wave designation — optional)

Writes to active_field_projections:
  - brie_z_score   REAL   (Z-scored BRIE-Z composite, 0-100 scale)
  - wave_bonus     REAL   (0.0 | 0.15 SG bonus for favored-wave players)

Writes to local_player_granular_traits:
  - app_150_200_fw_sg              REAL
  - app_150_200_poor_shot_avoidance REAL

Usage:
    python engine/traits_calculator.py --event_slug 2026_genesis_scottish_open
    python engine/traits_calculator.py --event_slug 2026_genesis_scottish_open --dry-run
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.latent_model import compute_brie_z, inject_wave_scalar, zscore_normalize

# ── Event slug → config ────────────────────────────────────────────────────────

_EVENT_CONFIGS: dict[str, dict] = {
    "2026_genesis_scottish_open": {
        "event_dir_glob": "events/*GenesisScottish*",
        "course_key":     "renaissance_club",
        "favored_wave":   "late_early",
    },
    "2026_travelers_championship": {
        "event_dir_glob": "events/*Travelers*",
        "course_key":     "tpc_river_highlights",
        "favored_wave":   "early_late",
    },
    "2026_usopen": {
        "event_dir_glob": "events/*USOPEN*",
        "course_key":     "shinnecock_hills_gc",
        "favored_wave":   "late_early",
    },
    "2026_john_deere_classic": {
        "event_dir_glob": "events/*JohnDeere*",
        "course_key":     "tpc_deere_run",
        "favored_wave":   "late_early",
    },
}


def _resolve_event_dir(slug: str) -> Path:
    cfg = _EVENT_CONFIGS.get(slug, {})
    pattern = cfg.get("event_dir_glob", f"events/*{slug}*")
    candidates = sorted(_ROOT.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"Cannot locate event directory for '{slug}'. "
            f"Searched: {_ROOT / pattern}"
        )
    return candidates[0]


# ── DB ─────────────────────────────────────────────────────────────────────────

def _open_db() -> sqlite3.Connection:
    cfg_path = _ROOT / "config" / "db_config.json"
    if cfg_path.exists():
        with open(cfg_path) as fh:
            cfg = json.load(fh)
        db_path = _ROOT / cfg["db_path"]
    else:
        db_path = _ROOT / "data" / "venuedna_master.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Add BRIE-Z output columns to existing tables (idempotent via try/except)."""
    migrations = [
        ("active_field_projections",       "brie_z_score",                   "REAL"),
        ("active_field_projections",       "wave_bonus",                     "REAL DEFAULT 0.0"),
        ("local_player_granular_traits",   "app_150_200_fw_sg",              "REAL"),
        ("local_player_granular_traits",   "app_150_200_poor_shot_avoidance", "REAL"),
        ("course_profiles",                "difficulty_app_rough_vs_fw",     "REAL DEFAULT 0.0"),
        ("course_profiles",                "difficulty_ott_rough_vs_fw",     "REAL DEFAULT 0.0"),
        ("course_profiles",                "difficulty_putt_fescue",         "REAL DEFAULT 0.0"),
    ]
    for table, col, col_type in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            conn.commit()
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise


# ── Name normalisation (matches score_engine_v2 key format) ──────────────────

def _norm_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    nfd = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in nfd if not unicodedata.combining(c))
    for src, dst in {"Ø":"O","ø":"O","Æ":"AE","æ":"AE","Å":"A","å":"A",
                     "Ö":"O","ö":"O","Ü":"U","ü":"U","Ñ":"N","ñ":"N","ß":"SS"}.items():
        stripped = stripped.replace(src, dst)
    return stripped.upper().strip()


def _make_key(last: str, first: str) -> str:
    return _norm_name(last) + "|" + _norm_name(first)


def _name_to_key(raw: str) -> str:
    raw = str(raw).strip()
    if "," in raw:
        parts = raw.split(",", 1)
        return _make_key(parts[0].strip(), parts[1].strip())
    return _make_key(raw, "")


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run(event_slug: str, dry_run: bool = False, verbose: bool = True) -> pd.DataFrame:
    """
    Compute BRIE-Z scores and wave bonuses for all players in the event.

    Returns a summary DataFrame with one row per player.
    """
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    cfg          = _EVENT_CONFIGS.get(event_slug, {})
    course_key   = cfg.get("course_key", "renaissance_club")
    favored_wave = cfg.get("favored_wave", "late_early")

    event_dir  = _resolve_event_dir(event_slug)
    input_dir  = event_dir / "input"
    pairings   = input_dir / "r1_pairings.csv"

    log(f"[traits_calculator] event: {event_slug}")
    log(f"  dir          : {event_dir}")
    log(f"  course_key   : {course_key}")
    log(f"  favored_wave : {favored_wave}")
    log(f"  pairings     : {'found' if pairings.exists() else 'missing — wave_bonus = 0.0'}")

    conn = _open_db()
    _ensure_schema(conn)

    # ── 1. Approach skill CSV → app_150_200_fw_sg ─────────────────────────────
    app_csv = input_dir / "approach_skill_Last12mon.csv"
    fw_sg_map: dict[str, float] = {}
    if app_csv.exists():
        try:
            app_raw = pd.read_csv(app_csv, encoding="cp1252")
            app_raw.columns = [c.strip() for c in app_raw.columns]
            val_col = "Fairway shots- 150-200yrd value"
            for _, row in app_raw.iterrows():
                key = _make_key(str(row.get("Last Name", "")), str(row.get("First Name", "")))
                if val_col in app_raw.columns:
                    try:
                        fw_sg_map[key] = float(row[val_col])
                    except (ValueError, TypeError):
                        pass
            log(f"  approach CSV : {len(fw_sg_map)} fw_sg values")
        except Exception as exc:
            log(f"  [warn] approach CSV read failed: {exc}")
    else:
        log(f"  [warn] approach_skill_Last12mon.csv not found — fw_sg = 0.0 for all")

    # ── 2. local_player_granular_traits → avoid_rough_pct ────────────────────
    try:
        traits_rows = conn.execute(
            "SELECT player_key, player_name, avoid_rough_pct "
            "FROM local_player_granular_traits"
        ).fetchall()
    except sqlite3.OperationalError:
        traits_rows = []
        log("  [warn] local_player_granular_traits not found — psa = 0.0 for all")

    avoid_map: dict[str, float] = {}
    for r in traits_rows:
        key = _name_to_key(str(r["player_name"]))
        if r["avoid_rough_pct"] is not None:
            avoid_map[key] = float(r["avoid_rough_pct"])

    # Centre avoid_rough_pct at field mean so it becomes a signed SG-comparable metric
    field_mean_avoid = sum(avoid_map.values()) / len(avoid_map) if avoid_map else 0.0
    psa_map = {k: v - field_mean_avoid for k, v in avoid_map.items()}
    log(f"  granular traits: {len(avoid_map)} avoid_rough_pct values "
        f"(field mean {field_mean_avoid:.4f})")

    # ── 3. Course difficulty from course_profiles ─────────────────────────────
    course_rough_penalty = 0.0
    try:
        row = conn.execute(
            "SELECT difficulty_app_rough_vs_fw FROM course_profiles WHERE course_key = ?",
            (course_key,),
        ).fetchone()
        if row and row[0] is not None:
            course_rough_penalty = float(row[0])
    except sqlite3.OperationalError:
        pass
    log(f"  course rough penalty: {course_rough_penalty:.4f}")

    # ── 4. Field player list from active_field_projections ────────────────────
    try:
        proj_rows = conn.execute(
            "SELECT dg_id, player_name FROM active_field_projections"
        ).fetchall()
    except sqlite3.OperationalError:
        proj_rows = []
        log("  [warn] active_field_projections not found — returning empty frame")

    log(f"  active field  : {len(proj_rows)} players")

    # ── 5. Compute BRIE-Z per player ─────────────────────────────────────────
    records = []
    for r in proj_rows:
        pname = str(r["player_name"])
        key   = _name_to_key(pname)

        fw_sg = fw_sg_map.get(key, 0.0)
        psa   = psa_map.get(key, 0.0)
        bz    = compute_brie_z(fw_sg, psa, course_rough_penalty)

        records.append({
            "key":                  key,
            "player_name":          pname,
            "dg_id":                r["dg_id"],
            "brie_z_fw_sg":         fw_sg,
            "brie_z_psa":           psa,
            "course_rough_penalty": course_rough_penalty,
            "brie_z_raw":           bz,
        })

    df = pd.DataFrame(records)
    if df.empty:
        log("  [warn] No players to process.")
        conn.close()
        return df

    # ── 6. Wave scalar injection ──────────────────────────────────────────────
    df = inject_wave_scalar(
        df,
        pairings_path=pairings if pairings.exists() else None,
        favored_wave=favored_wave,
        bonus=0.15,
        name_col="key",
    )
    favored_n = (df["wave_bonus"] > 0).sum()
    log(f"  wave scalar   : {favored_n} players in favored '{favored_wave}' draw (+0.15)")

    # ── 7. Z-score BRIE-Z (wave bonus included before normalisation) ──────────
    df["brie_z_score"] = zscore_normalize(
        df["brie_z_raw"] + df["wave_bonus"],
        target_mean=50.0,
        target_std=15.0,
    )

    # ── 8. DB writes ──────────────────────────────────────────────────────────
    if not dry_run:
        written = 0
        for _, row in df.iterrows():
            conn.execute(
                """
                UPDATE active_field_projections
                SET brie_z_score = ?, wave_bonus = ?
                WHERE player_name = ?
                """,
                (
                    round(float(row["brie_z_score"]), 4),
                    round(float(row["wave_bonus"]), 4),
                    row["player_name"],
                ),
            )
            conn.execute(
                """
                UPDATE local_player_granular_traits
                SET app_150_200_fw_sg              = ?,
                    app_150_200_poor_shot_avoidance = ?
                WHERE player_name = ?
                """,
                (
                    round(float(row["brie_z_fw_sg"]), 6),
                    round(float(row["brie_z_psa"]),   6),
                    row["player_name"],
                ),
            )
            written += 1
        conn.commit()
        log(f"  DB writes     : {written} players updated")
    else:
        log("  [dry-run] DB writes skipped")

    conn.close()

    summary_cols = [
        "player_name", "brie_z_fw_sg", "brie_z_psa", "course_rough_penalty",
        "brie_z_raw", "wave_bonus", "brie_z_score", "wave_designation",
    ]
    return df[[c for c in summary_cols if c in df.columns]]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VenueDNA BRIE-Z + Wave Scalar Pipeline"
    )
    parser.add_argument(
        "--event_slug", required=True,
        metavar="SLUG",
        help="Event identifier, e.g. 2026_genesis_scottish_open",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute scores but skip DB writes",
    )
    args = parser.parse_args()

    result = run(args.event_slug, dry_run=args.dry_run, verbose=True)

    if result.empty:
        print("\nNo players processed.")
        sys.exit(1)

    print(f"\n{'Player':<35} {'FW-SG':>7} {'PSA':>7} {'Penalty':>8} "
          f"{'Raw':>8} {'WaveB':>6} {'Score':>7} {'Wave':<12}")
    print("-" * 96)
    for _, r in result.head(25).iterrows():
        print(
            f"{str(r.get('player_name','?')):<35} "
            f"{float(r.get('brie_z_fw_sg', 0)):>7.4f} "
            f"{float(r.get('brie_z_psa', 0)):>7.4f} "
            f"{float(r.get('course_rough_penalty', 0)):>8.4f} "
            f"{float(r.get('brie_z_raw', 0)):>8.4f} "
            f"{float(r.get('wave_bonus', 0)):>6.2f} "
            f"{float(r.get('brie_z_score', 50)):>7.1f} "
            f"{str(r.get('wave_designation', 'unknown')):<12}"
        )
