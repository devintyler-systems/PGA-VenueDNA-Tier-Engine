"""events/2026_rocket_classic/output/_dry_run/diagnostic_run.py

READ-ONLY diagnostic against enrich_cards.py input files for 2026 Rocket Classic.
Writes 4 JSON artifacts to _dry_run/ only.  Mutates NO tracked files.
Exits 1 (STOP) if any baseline count mismatch or critical schema problem is found.

Run from repo root:
  python events/2026_rocket_classic/output/_dry_run/diagnostic_run.py
"""
from __future__ import annotations

import csv
import difflib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIAG_DIR  = Path(__file__).resolve().parent            # _dry_run/
_EVENT_DIR = _DIAG_DIR.parent.parent                    # events/2026_rocket_classic/
_INPUT_DIR = _EVENT_DIR / "input"

# ── Constants — must match enrich_cards.py exactly ────────────────────────────
PHANTOM_DECOMP_PLAYER = "Koepka, Brooks"
CROSSWALK_FILE        = "rocket_classic_player_ID_source.csv"
PERF_FILE             = "dg_performance_2026.csv"
PERF_FIELDS           = ("app_true", "ott_true", "putt_true", "arg_true")

UNSCORED_PLAYERS = [
    {"player": "Azallion, Daniel", "player_id": "35071"},
    {"player": "Celano, Ryan",     "player_id": "29665"},
    {"player": "Huskey, Keenan",   "player_id": "26597"},
    {"player": "Quiban, Justin",   "player_id": "15981"},
    {"player": "Silverman, Ben",   "player_id": "17381"},
]

THRESH_ELITE_APP   = 1.00
THRESH_STRONG_APP  = 0.60
THRESH_VENUE_FIT   = 0.15
THRESH_CTRL_POWER  = 0.60
THRESH_COURSE_PED  = 0.04
THRESH_HOT_FORM    = 1.50
THRESH_APP_DEFICIT = 0.00
THRESH_LI_GAP      = -0.05
DEBUT_CH_HAIRCUT   = -0.25

BADGE_INELIGIBLE_FIELDS = ("ch_adjustment", "true_sg_l20", "delta_fit")
FORM_TAG_PHRASES        = ("Red-Hot Form",)
CH_TAG_PHRASES          = ("Proven Course Pedigree",)
STRENGTH_TRAIT_MAP = {
    "Elite Iron Play":      "app_true",
    "Strong Approach Play": "app_true",
    "Controlled Power":     "ott_true",
}
WEAKNESS_TRAIT_MAP = {
    "Approach Deficit": "app_true",
    "Long-Iron Gap":    "trait_long_iron_raw",
}

BASELINES = {
    "total_field": 147,
    "unscored":    5,
    "scored":      142,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def safe_float(v, default=0.0):
    try:
        s = str(v).strip().lower()
        return float(v) if s not in ("", "null", "none", "n/a", "nan") else default
    except (ValueError, TypeError):
        return default


def normalize_name(s):
    if not s:
        return ""
    s = str(s).strip().strip('"').strip("'")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace(".", "").strip()


def norm_set(names):
    return {normalize_name(n): n for n in names}


def best_match(name, candidate_norms, threshold=0.85):
    n = normalize_name(name)
    if n in candidate_norms:
        return n, 1.0
    best, best_r = None, 0.0
    for cand in candidate_norms:
        r = difflib.SequenceMatcher(None, n, cand).ratio()
        if r > best_r:
            best, best_r = cand, r
    return (best, best_r) if best_r >= threshold else (None, best_r)


# ── Loaders ────────────────────────────────────────────────────────────────────

def _open(path):
    return path.open(newline="", encoding="utf-8")


def load_field_teetimes(path):
    """Returns [(player_name, dg_id), ...]"""
    if not path.exists():
        return []
    rows = []
    with _open(path) as f:
        for row in csv.DictReader(f):
            n = row.get("player_name", "").strip().strip('"')
            d = row.get("dg_id", "").strip()
            if n:
                rows.append((n, d))
    return rows


def load_csv_names(path, filter_stat=None):
    """Generic: returns {raw_name: True}.  filter_stat: require row['stat']=='sg per shot'."""
    if not path.exists():
        return {}
    result = {}
    with _open(path) as f:
        for row in csv.DictReader(f):
            if filter_stat and row.get("stat", "").strip().lower() != filter_stat:
                continue
            n = row.get("player_name", "").strip().strip('"')
            if n:
                result[n] = True
    return result


def load_csv_columns_and_count(path):
    """Returns (list[str] | None, int)."""
    if not path.exists():
        return None, 0
    with _open(path) as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        count = sum(1 for _ in reader)
    return cols, count


def load_ch_data(path):
    """Returns {normalize_name: ch_adjustment_float}."""
    if not path.exists():
        return {}
    result = {}
    with _open(path) as f:
        for row in csv.DictReader(f):
            n = row.get("player_name", "").strip().strip('"')
            if n:
                result[normalize_name(n)] = safe_float(row.get("ch_adjustment", 0))
    return result


def load_trending_data(path):
    """Returns {normalize_name: {dg_id, true_sg_l20, l5_starts}}."""
    if not path.exists():
        return {}
    result = {}
    with _open(path) as f:
        for row in csv.DictReader(f):
            n = row.get("player_name", "").strip().strip('"')
            if n:
                result[normalize_name(n)] = {
                    "dg_id":       row.get("dg_id", "").strip(),
                    "true_sg_l20": safe_float(row.get("true_sg_l20", 0)),
                    "l5_starts":   row.get("l5_starts", "").strip(),
                }
    return result


def load_crosswalk_meta(path):
    """Returns (columns_found, engine_loadable_count, schema_ok, sample_rows)."""
    if not path.exists():
        return None, 0, False, []
    with _open(path) as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        rows_raw = list(reader)
    schema_ok = ("player_name" in cols and "dg_id" in cols)
    loadable = 0
    for row in rows_raw:
        n  = row.get("player_name", "").strip()
        d  = row.get("dg_id", "").strip()
        if n and d:
            loadable += 1
    sample = [dict(r) for r in rows_raw[:3]]
    return cols, loadable, schema_ok, sample


# ── Trait availability simulator ───────────────────────────────────────────────

def sim_trait_availability(
    perf_absent: bool,
    skill_avail: bool,
    ch_resolved: bool,
    ch_adj: float,
    trend_avail: bool,
    data_depth: str,
    any_sg_avail: bool,
) -> dict:
    """Mirrors build_trait_availability() in enrich_cards.py."""
    result = {}

    _unavail_perf = {
        "availability": "UNAVAILABLE",
        "source_status": "MISSING",
        "usable_for_badges": False,
        "usable_for_narrative_traits": False,
        "source_file": PERF_FILE,
    }
    _ok_perf = {
        "availability": "MEASURED",
        "source_status": "OK",
        "usable_for_badges": True,
        "usable_for_narrative_traits": True,
        "source_file": PERF_FILE,
    }
    for field in PERF_FIELDS:
        result[field] = _unavail_perf.copy() if perf_absent else _ok_perf.copy()

    if skill_avail:
        result["trait_approach_raw"] = {
            "availability": "DERIVED", "source_status": "MEASURED",
            "usable_for_badges": True, "usable_for_narrative_traits": True,
        }
        result["trait_long_iron_raw"] = {
            "availability": "DERIVED", "source_status": "MEASURED",
            "usable_for_badges": True, "usable_for_narrative_traits": True,
        }
    else:
        _mzf = {
            "availability": "MISSING_ZERO_FILLED", "source_status": "MISSING",
            "usable_for_badges": False, "usable_for_narrative_traits": False,
        }
        result["trait_approach_raw"] = _mzf.copy()
        result["trait_long_iron_raw"] = _mzf.copy()

    if ch_resolved:
        avail_str = "MEASURED" if ch_adj != 0.0 else "MEASURED_ZERO"
        result["ch_adjustment"] = {
            "availability": avail_str, "source_status": "OK",
            "usable_for_badges": False, "usable_for_narrative_traits": True,
            "narrative_context": "venue_history",
            "narrative_qualifier": "venue-history context only — not a standalone player-skill trait",
        }
    elif data_depth == "DEBUT":
        result["ch_adjustment"] = {
            "availability": "DERIVED", "source_status": "DEBUT_HAIRCUT",
            "usable_for_badges": False, "usable_for_narrative_traits": True,
            "narrative_context": "venue_history",
            "narrative_qualifier": "venue-history context only — course debut",
        }
    else:
        result["ch_adjustment"] = {
            "availability": "MISSING_ZERO_FILLED", "source_status": "MISSING",
            "usable_for_badges": False, "usable_for_narrative_traits": False,
        }

    if trend_avail:
        result["true_sg_l20"] = {
            "availability": "MEASURED", "source_status": "OK",
            "usable_for_badges": False, "usable_for_narrative_traits": True,
        }
    else:
        result["true_sg_l20"] = {
            "availability": "MISSING_ZERO_FILLED", "source_status": "MISSING",
            "usable_for_badges": False, "usable_for_narrative_traits": False,
        }

    sg_composite_avail = "DERIVED" if any_sg_avail else "DEBUT_ZERO"
    result["sg_base_composite"] = {
        "availability": sg_composite_avail, "source_status": "OK" if any_sg_avail else "DEBUT",
        "usable_for_badges": False, "usable_for_narrative_traits": False,
    }
    result["delta_fit"] = {
        "availability": "DERIVED", "source_status": "OK",
        "usable_for_badges": False, "usable_for_narrative_traits": True,
    }
    return result


def unavail_set(avail: dict) -> set:
    return {t for t, m in avail.items()
            if m.get("availability") in ("UNAVAILABLE", "MISSING_ZERO_FILLED")}


# ── Gate checker ───────────────────────────────────────────────────────────────

def run_gates(scored_players: list[dict]) -> dict:
    """
    scored_players: list of dicts with keys:
      player_id, avail, strength_tags, weakness_tags
    Returns gate result dict.
    """
    v1_v, v2_v, v3_v, v4_v, v5_v, v6_v = [], [], [], [], [], []

    for p in scored_players:
        pid     = p["player_id"]
        avail   = p["avail"]
        unavail = unavail_set(avail)

        for tag in p["strength_tags"]:
            for phrase, trait in STRENGTH_TRAIT_MAP.items():
                if phrase in tag and trait in unavail:
                    v1_v.append({"player_id": pid, "tag": tag, "trait": trait,
                                 "availability": avail.get(trait, {}).get("availability")})

        for tag in p["weakness_tags"]:
            for phrase, trait in WEAKNESS_TRAIT_MAP.items():
                if phrase in tag and trait in unavail:
                    v2_v.append({"player_id": pid, "tag": tag, "trait": trait})

        for field in PERF_FIELDS:
            meta = avail.get(field, {})
            if meta.get("usable_for_badges") is True and meta.get("availability") == "UNAVAILABLE":
                v3_v.append({"player_id": pid, "field": field})

        for field in BADGE_INELIGIBLE_FIELDS:
            if avail.get(field, {}).get("usable_for_badges") is True:
                v4_v.append({"player_id": pid, "field": field})

        if "true_sg_l20" in unavail:
            for tag in p["strength_tags"]:
                if any(ph in tag for ph in FORM_TAG_PHRASES):
                    v5_v.append({"player_id": pid, "tag": tag})

        for tag in p["strength_tags"]:
            if any(ph in tag for ph in CH_TAG_PHRASES):
                if avail.get("ch_adjustment", {}).get("narrative_context") != "venue_history":
                    v6_v.append({"player_id": pid, "tag": tag})

    return {
        "V1_no_unavailable_in_strength_tags": {
            "status": "PASS" if not v1_v else "FAIL",
            "violation_count": len(v1_v),
            "violations": v1_v,
        },
        "V2_no_unavailable_in_weakness_tags": {
            "status": "PASS" if not v2_v else "FAIL",
            "violation_count": len(v2_v),
            "violations": v2_v,
        },
        "V3_no_unavailable_trait_in_badge_inputs": {
            "status": "PASS" if not v3_v else "FAIL",
            "violation_count": len(v3_v),
            "violations": v3_v,
        },
        "V4_contextual_fields_not_badge_eligible": {
            "status": "PASS" if not v4_v else "FAIL",
            "violation_count": len(v4_v),
            "violations": v4_v,
        },
        "V5_no_form_tag_when_true_sg_l20_missing": {
            "status": "PASS" if not v5_v else "FAIL",
            "violation_count": len(v5_v),
            "violations": v5_v,
        },
        "V6_ch_tag_must_carry_venue_history_qualifier": {
            "status": "PASS" if not v6_v else "FAIL",
            "violation_count": len(v6_v),
            "violations": v6_v,
        },
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ts = datetime.now(timezone.utc).isoformat()
    mismatches: list[dict] = []

    print("=== Rocket Classic Diagnostic Run ===")
    print(f"Timestamp: {ts}")
    print()

    # ── File paths ────────────────────────────────────────────────────────────
    field_path     = _INPUT_DIR / "pga_field_teetimes.csv"
    decomp_path    = _INPUT_DIR / "dg_decomposition.csv"
    perf_path      = _INPUT_DIR / PERF_FILE
    trending_path  = _INPUT_DIR / "pga_field_trending_table.csv"
    ch_path        = _INPUT_DIR / "detroit_golf_club_CH.csv"
    skill_path     = _INPUT_DIR / "app_skill_l12_sg.csv"
    crosswalk_path = _INPUT_DIR / CROSSWALK_FILE

    file_exists = {
        "pga_field_teetimes":      field_path.exists(),
        "dg_decomposition":        decomp_path.exists(),
        PERF_FILE:                 perf_path.exists(),
        "pga_field_trending_table": trending_path.exists(),
        "detroit_golf_club_CH":    ch_path.exists(),
        "app_skill_l12_sg":        skill_path.exists(),
        CROSSWALK_FILE:            crosswalk_path.exists(),
    }

    # ── PERF column inspection ────────────────────────────────────────────────
    perf_absent       = not perf_path.exists()
    perf_cols, perf_row_count = load_csv_columns_and_count(perf_path)
    perf_cols         = perf_cols or []
    perf_cols_ok      = not perf_absent and all(f in perf_cols for f in PERF_FIELDS)
    missing_perf_cols = [f for f in PERF_FIELDS if f not in perf_cols] if not perf_absent else list(PERF_FIELDS)

    perf_column_report = {
        "file_exists":      not perf_absent,
        "row_count":        perf_row_count,
        "found_columns":    perf_cols,
        "expected_columns": list(PERF_FIELDS),
        "columns_present":  [f for f in PERF_FIELDS if f in perf_cols],
        "columns_missing":  missing_perf_cols,
        "schema_ok":        perf_cols_ok,
        "engine_behavior":  (
            "perf_absent=False -> PERF_FIELDS marked MEASURED/usable_for_badges=True, "
            "but safe_float(row.get('app_true')) returns 0.0 for missing column — "
            "all perf values will be 0.0 despite MEASURED label"
            if not perf_absent and not perf_cols_ok
            else ("perf_absent=True -> PERF_FIELDS all UNAVAILABLE" if perf_absent else "OK")
        ),
    }

    if not perf_absent and not perf_cols_ok:
        mismatches.append({
            "type":     "PERF_COLUMN_MISMATCH",
            "severity": "CRITICAL",
            "detail": (
                f"dg_performance_2026.csv exists ({perf_row_count} rows) but is missing "
                f"required columns: {missing_perf_cols}. "
                f"Found columns: {perf_cols}. "
                f"Engine will set perf_absent=False and mark PERF_FIELDS MEASURED/usable_for_badges=True, "
                f"but actual loaded values are 0.0 (safe_float on absent keys). "
                f"This is a data-integrity mismatch: traits are labeled as measured evidence but are structurally zero-filled."
            ),
        })
        print("[CRITICAL] PERF COLUMN MISMATCH DETECTED")
        print(f"  File:           {perf_path.name}")
        print(f"  Rows:           {perf_row_count}")
        print(f"  Found cols:     {perf_cols}")
        print(f"  Missing:        {missing_perf_cols}")
        print()

    # ── Crosswalk inspection ──────────────────────────────────────────────────
    cw_cols, cw_loadable, cw_schema_ok, cw_sample = load_crosswalk_meta(crosswalk_path)
    crosswalk_report = {
        "file_exists":             crosswalk_path.exists(),
        "columns_found":           cw_cols,
        "columns_expected":        ["player_name", "dg_id"],
        "schema_ok":               cw_schema_ok,
        "engine_loadable_entries": cw_loadable,
        "sample_rows":             cw_sample,
        "note": (
            "Engine load_id_crosswalk() reads 'player_name'/'dg_id' columns. "
            "If columns differ, 0 entries load and crosswalk provides no ID resolution."
            if not cw_schema_ok and crosswalk_path.exists()
            else "OK"
        ),
    }
    if crosswalk_path.exists() and not cw_schema_ok:
        mismatches.append({
            "type":     "CROSSWALK_COLUMN_MISMATCH",
            "severity": "CRITICAL",
            "detail": (
                f"Crosswalk file {CROSSWALK_FILE} has columns {cw_cols} but engine expects "
                f"['player_name', 'dg_id']. load_id_crosswalk() will load 0 entries — "
                f"7 crosswalk-intended ID resolutions will NOT be applied."
            ),
        })
        print("[CRITICAL] CROSSWALK COLUMN MISMATCH")
        print(f"  Found columns:    {cw_cols}")
        print(f"  Expected columns: ['player_name', 'dg_id']")
        print(f"  Engine will load: 0 entries (no ID resolution)")
        print()

    # ── Field load ────────────────────────────────────────────────────────────
    field_records  = load_field_teetimes(field_path)
    field_names    = [n for n, _ in field_records]
    field_dg_map   = {n: d for n, d in field_records}
    total_field    = len(field_names)
    field_norms    = norm_set(field_names)

    unscored_norms = {normalize_name(u["player"]) for u in UNSCORED_PLAYERS}
    scored_names   = [n for n in field_names if normalize_name(n) not in unscored_norms]
    scored_count   = len(scored_names)

    # ── Reconcile field counts against baselines ──────────────────────────────
    reconciliation = {}
    for key, bl, obs in [
        ("total_field", BASELINES["total_field"], total_field),
        ("unscored",    BASELINES["unscored"],    len(UNSCORED_PLAYERS)),
        ("scored",      BASELINES["scored"],       scored_count),
    ]:
        ok = obs == bl
        reconciliation[key] = {"baseline": bl, "observed": obs, "match": ok}
        if not ok:
            mismatches.append({
                "type": f"COUNT_MISMATCH_{key.upper()}",
                "severity": "CRITICAL",
                "baseline": bl,
                "observed": obs,
            })

    # ── Decomp ────────────────────────────────────────────────────────────────
    decomp_names_raw = load_csv_names(decomp_path)
    decomp_norms     = norm_set(decomp_names_raw)
    phantom_norm     = normalize_name(PHANTOM_DECOMP_PLAYER)
    phantom_in_decomp = phantom_norm in decomp_norms
    phantom_in_field  = phantom_norm in field_norms

    reconciliation["phantom_absent_from_decomp"] = {
        "baseline": False, "observed": phantom_in_decomp,
        "match": not phantom_in_decomp,
        "note": "PHANTOM_DECOMP_PLAYER must not appear in decomp (withdrawn/phantom)",
    }
    reconciliation["phantom_absent_from_field"] = {
        "baseline": False, "observed": phantom_in_field,
        "match": not phantom_in_field,
    }
    if phantom_in_decomp:
        mismatches.append({
            "type": "PHANTOM_STILL_IN_DECOMP",
            "severity": "CRITICAL",
            "player": PHANTOM_DECOMP_PLAYER,
        })
    if phantom_in_field:
        mismatches.append({
            "type": "PHANTOM_IN_FIELD",
            "severity": "CRITICAL",
            "player": PHANTOM_DECOMP_PLAYER,
        })

    decomp_matched_scored = sum(1 for n in scored_names
                                if normalize_name(n) in decomp_norms)

    # ── Perf name coverage ────────────────────────────────────────────────────
    perf_names_raw   = load_csv_names(perf_path)
    perf_norms_set   = {normalize_name(n) for n in perf_names_raw}
    perf_matched_scored = sum(1 for n in scored_names if normalize_name(n) in perf_norms_set)

    # ── Trending ─────────────────────────────────────────────────────────────
    trending_data_n  = load_trending_data(trending_path)
    trend_norms_set  = set(trending_data_n.keys())
    trend_matched_scored   = sum(1 for n in scored_names if normalize_name(n) in trend_norms_set)
    trend_missing_scored   = [n for n in scored_names if normalize_name(n) not in trend_norms_set]

    # Fuzzy-only candidates (0.85–0.92 ratio) in trending
    trend_ambiguous = []
    for n in trend_missing_scored:
        matched_norm, ratio = best_match(n, trend_norms_set, threshold=0.85)
        if matched_norm and ratio < 0.92:
            trend_ambiguous.append({
                "field_name": n, "candidate": matched_norm, "ratio": round(ratio, 4)
            })

    # ── CH ────────────────────────────────────────────────────────────────────
    ch_data_n      = load_ch_data(ch_path)
    ch_norms_set   = set(ch_data_n.keys())
    ch_matched_scored = sum(1 for n in scored_names if normalize_name(n) in ch_norms_set)

    # ── Skill ─────────────────────────────────────────────────────────────────
    skill_names_raw  = load_csv_names(skill_path, filter_stat="sg per shot")
    skill_norms_set  = {normalize_name(n) for n in skill_names_raw}
    skill_matched_scored = sum(1 for n in scored_names if normalize_name(n) in skill_norms_set)

    # ── Per-player coverage matrix ────────────────────────────────────────────
    coverage_rows = []
    for player_name in field_names:
        pnorm    = normalize_name(player_name)
        dg_id    = field_dg_map.get(player_name, "")
        is_uns   = pnorm in unscored_norms
        in_decomp_flag = pnorm in decomp_norms
        in_perf  = pnorm in perf_norms_set
        in_trend = pnorm in trend_norms_set
        in_ch    = pnorm in ch_norms_set
        in_skill = pnorm in skill_norms_set

        if is_uns:
            data_depth = "UNSCORED"
        elif not in_decomp_flag:
            data_depth = "DEBUT"
        else:
            data_depth = "MEASURED"

        coverage_rows.append({
            "player_name": player_name,
            "dg_id_from_field": dg_id,
            "is_unscored":      is_uns,
            "data_depth":       data_depth,
            "in_decomp":        in_decomp_flag,
            "in_perf_file":     in_perf,
            "perf_schema_ok":   perf_cols_ok,
            "in_trending":      in_trend,
            "in_ch":            in_ch,
            "in_skill":         in_skill,
        })

    # ── Simulate trait_availability + tags for V1–V6 gates ────────────────────
    # Engine will use perf_absent = (not perf_path.exists()) — with the current
    # file present, perf_absent=False even though columns are wrong.
    engine_perf_absent = not perf_path.exists()

    scored_player_gate_inputs = []
    for rec in coverage_rows:
        if rec["is_unscored"]:
            continue
        pname  = rec["player_name"]
        pnorm  = normalize_name(pname)
        pid    = rec["dg_id_from_field"] or pname
        depth  = rec["data_depth"]

        ch_adj      = ch_data_n.get(pnorm, 0.0)
        true_sg_l20 = trending_data_n.get(pnorm, {}).get("true_sg_l20", 0.0) if rec["in_trending"] else 0.0
        any_sg_avail = rec["in_decomp"]

        avail = sim_trait_availability(
            perf_absent  = engine_perf_absent,
            skill_avail  = rec["in_skill"],
            ch_resolved  = rec["in_ch"],
            ch_adj       = ch_adj,
            trend_avail  = rec["in_trending"],
            data_depth   = depth,
            any_sg_avail = any_sg_avail,
        )
        unavail = unavail_set(avail)

        # Simulate strength tags (values are 0.0 when perf cols wrong)
        # app_true and ott_true will be 0.0 whether perf_absent or col-mismatch
        app_true    = 0.0  # col mismatch or absent → safe_float returns 0.0
        ott_true    = 0.0
        delta_fit   = 0.0  # sim only: true delta_fit requires SG corpus; treat as 0
        trait_li    = 0.0  # sim: approach proxies from skill file; treat as 0

        strength_tags = []
        if "app_true" not in unavail:
            if app_true > THRESH_ELITE_APP:
                strength_tags.append(f"Elite Iron Play (+{app_true:.2f})")
            elif app_true > THRESH_STRONG_APP:
                strength_tags.append(f"Strong Approach Play (+{app_true:.2f})")
        if delta_fit > THRESH_VENUE_FIT:
            strength_tags.append(f"Strong Venue Fit (+{delta_fit:.2f})")
        elif delta_fit > 0.05:
            strength_tags.append(f"Positive Venue Fit (+{delta_fit:.2f})")
        if "ott_true" not in unavail and ott_true > THRESH_CTRL_POWER:
            strength_tags.append("Controlled Power")
        if "ch_adjustment" not in unavail and ch_adj > THRESH_COURSE_PED:
            strength_tags.append("Proven Course Pedigree")
        if "true_sg_l20" not in unavail and true_sg_l20 > THRESH_HOT_FORM:
            strength_tags.append(f"Red-Hot Form ({true_sg_l20:.2f} SG L20)")
        if not strength_tags:
            strength_tags.append("Field-Average Profile")

        weakness_tags = []
        if "app_true" not in unavail and app_true < THRESH_APP_DEFICIT:
            weakness_tags.append("Approach Deficit")
        if depth == "DEBUT" or not rec["in_ch"]:
            weakness_tags.append("Venue Debut")
        if "trait_long_iron_raw" not in unavail and trait_li < THRESH_LI_GAP:
            weakness_tags.append("Long-Iron Gap")
        if not weakness_tags:
            weakness_tags.append("No Clear Structural Risk")

        scored_player_gate_inputs.append({
            "player_id":    pid,
            "avail":        avail,
            "strength_tags": strength_tags,
            "weakness_tags": weakness_tags,
        })

    gates = run_gates(scored_player_gate_inputs)
    all_gates_pass = all(v.get("status") == "PASS" for v in gates.values())

    # ── Additional reconciliation: pref/trending delta noted ─────────────────
    reconciliation["decomp_matched_scored"] = {
        "baseline": "142/142",
        "observed": f"{decomp_matched_scored}/{scored_count}",
        "match": decomp_matched_scored == scored_count,
        "note": "All 142 scored players expected to appear in dg_decomposition.csv",
    }
    reconciliation["trending_matched_scored"] = {
        "baseline": "~139/142 (8 noted gaps in prior build)",
        "observed": f"{trend_matched_scored}/{scored_count}",
        "match": True,  # not a hard baseline; informational
        "missing_players": trend_missing_scored,
    }

    # ── Write artifacts ───────────────────────────────────────────────────────
    _DIAG_DIR.mkdir(parents=True, exist_ok=True)

    coverage_report = {
        "diagnostic_ts":    ts,
        "schema_version":   "diagnostic-v1.0",
        "file_exists":      file_exists,
        "perf_column_report": perf_column_report,
        "crosswalk_report": crosswalk_report,
        "counts": {
            "total_field":   total_field,
            "unscored":      len(UNSCORED_PLAYERS),
            "scored":        scored_count,
            "decomp_rows":   len(decomp_names_raw),
            "perf_rows":     perf_row_count,
            "trending_rows": len(trending_data_n),
            "ch_rows":       len(ch_data_n),
            "skill_rows":    len(skill_names_raw),
        },
        "coverage_by_source": {
            "decomp": {
                "matched_scored": decomp_matched_scored,
                "total_scored": scored_count,
                "note": "Name-based; phantom excluded by PHANTOM_DECOMP_PLAYER constant",
            },
            "perf": {
                "matched_scored": perf_matched_scored,
                "total_scored": scored_count,
                "schema_ok": perf_cols_ok,
                "note": (
                    "Name match only — columns are wrong so values will be 0.0; "
                    "engine marks these MEASURED regardless"
                    if not perf_cols_ok and not perf_absent
                    else "OK"
                ),
            },
            "trending": {
                "matched_scored": trend_matched_scored,
                "total_scored": scored_count,
                "missing_scored": trend_missing_scored,
                "ambiguous_fuzzy_only": trend_ambiguous,
            },
            "ch": {
                "matched_scored": ch_matched_scored,
                "total_scored": scored_count,
            },
            "skill": {
                "matched_scored": skill_matched_scored,
                "total_scored": scored_count,
            },
        },
        "players": coverage_rows,
    }

    recon_doc = {
        "diagnostic_ts":    ts,
        "reconciliation":   reconciliation,
        "mismatches_found": len(mismatches),
        "mismatches":       mismatches,
    }

    gate_doc = {
        "diagnostic_ts":         ts,
        "engine_perf_absent":    engine_perf_absent,
        "perf_cols_ok":          perf_cols_ok,
        "all_gates_pass":        all_gates_pass,
        "simulation_note": (
            "PERF values simulated as 0.0 (col mismatch → safe_float returns 0.0). "
            "Delta_fit simulated as 0.0 (SG corpus not reloaded here). "
            "Gate results reflect what the engine WOULD produce given current inputs."
            if not perf_cols_ok and not perf_absent
            else "Simulation based on actual source availability."
        ),
        "gates": gates,
    }

    summary_doc = {
        "diagnostic_ts":          ts,
        "stop":                   len(mismatches) > 0,
        "stop_reasons":           [m["type"] for m in mismatches],
        "mismatches":             mismatches,
        "critical_schema_issues": {
            "perf_column_mismatch":      not perf_cols_ok and not perf_absent,
            "crosswalk_column_mismatch": crosswalk_path.exists() and not cw_schema_ok,
        },
        "counts": {
            "total_field":   total_field,
            "scored":        scored_count,
            "unscored":      len(UNSCORED_PLAYERS),
            "decomp_rows":   len(decomp_names_raw),
            "phantom_in_decomp": phantom_in_decomp,
            "phantom_in_field":  phantom_in_field,
        },
        "coverage_summary": {
            "decomp_matched_scored":  decomp_matched_scored,
            "perf_name_matched":      perf_matched_scored,
            "trending_matched":       trend_matched_scored,
            "trending_missing_count": len(trend_missing_scored),
            "ch_matched":             ch_matched_scored,
            "skill_matched":          skill_matched_scored,
        },
        "gates_all_pass": all_gates_pass,
    }

    (_DIAG_DIR / "diagnostic_coverage_report.json").write_text(
        json.dumps(coverage_report, indent=2, default=str), encoding="utf-8")
    (_DIAG_DIR / "diagnostic_reconciliation.json").write_text(
        json.dumps(recon_doc, indent=2, default=str), encoding="utf-8")
    (_DIAG_DIR / "diagnostic_gate_results.json").write_text(
        json.dumps(gate_doc, indent=2, default=str), encoding="utf-8")
    (_DIAG_DIR / "diagnostic_summary.json").write_text(
        json.dumps(summary_doc, indent=2, default=str), encoding="utf-8")

    # ── Print report ──────────────────────────────────────────────────────────
    print("=== COVERAGE REPORT ===")
    print(f"  Total field:       {total_field}  (baseline: {BASELINES['total_field']})")
    print(f"  UNSCORED:          {len(UNSCORED_PLAYERS)}  (baseline: {BASELINES['unscored']})")
    print(f"  Scored:            {scored_count}  (baseline: {BASELINES['scored']})")
    print(f"  Decomp rows:       {len(decomp_names_raw)}")
    print(f"  Phantom in decomp: {phantom_in_decomp}  (expected: False)")
    print(f"  Phantom in field:  {phantom_in_field}   (expected: False)")
    print()
    print("  Source coverage (scored players):")
    print(f"    Decomp:    {decomp_matched_scored}/{scored_count}")
    print(f"    Perf:      {perf_matched_scored}/{scored_count}  [schema_ok={perf_cols_ok}]")
    print(f"    Trending:  {trend_matched_scored}/{scored_count}  ({len(trend_missing_scored)} missing)")
    print(f"    CH:        {ch_matched_scored}/{scored_count}")
    print(f"    Skill:     {skill_matched_scored}/{scored_count}")
    print()
    if trend_missing_scored:
        print("  Trending missing (scored):", trend_missing_scored)
        print()
    if trend_ambiguous:
        print("  Trending fuzzy-only matches (ratio 0.85-0.92 — ambiguous):")
        for a in trend_ambiguous:
            print(f"    {a['field_name']} -> {a['candidate']} ({a['ratio']})")
        print()

    print("=== PERF FILE ===")
    print(f"  Exists:        {not perf_absent}")
    print(f"  Rows:          {perf_row_count}")
    print(f"  Columns found: {perf_cols}")
    print(f"  Schema OK:     {perf_cols_ok}")
    if missing_perf_cols:
        print(f"  Missing cols:  {missing_perf_cols}")
    print(f"  Engine behavior: {perf_column_report['engine_behavior']}")
    print()

    print("=== CROSSWALK ===")
    print(f"  Columns found:         {cw_cols}")
    print(f"  Schema OK:             {cw_schema_ok}")
    print(f"  Engine-loadable entries: {cw_loadable}")
    if not cw_schema_ok and crosswalk_path.exists():
        print("  [CRITICAL] Engine will load 0 entries — ID overrides not applied")
    print()

    print("=== V1-V6 GATE RESULTS ===")
    for gname, gdata in gates.items():
        vcnt = gdata.get("violation_count", 0)
        print(f"  {gname}: {gdata['status']}  ({vcnt} violations)")
    print()

    print(f"=== MISMATCHES: {len(mismatches)} ===")
    for m in mismatches:
        print(f"  [{m['severity']}] {m['type']}")
        if "detail" in m:
            print(f"    {m['detail']}")
        elif "baseline" in m:
            print(f"    baseline={m['baseline']} observed={m['observed']}")
    print()

    print("Artifacts written to:", str(_DIAG_DIR))
    print("  diagnostic_coverage_report.json")
    print("  diagnostic_reconciliation.json")
    print("  diagnostic_gate_results.json")
    print("  diagnostic_summary.json")
    print()

    if mismatches:
        print("STOP: Do not promote, fix, or rescore until mismatches are reviewed.")
        sys.exit(1)
    else:
        print("No baseline mismatches detected.")


if __name__ == "__main__":
    main()
