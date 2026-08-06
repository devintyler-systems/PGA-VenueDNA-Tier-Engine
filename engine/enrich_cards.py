"""engine/enrich_cards.py
VenueDNA pre-event dual-vector + venue-trait enrichment pipeline. Normal
command-line execution takes no arguments and always runs against the
manifest-bound active event (config/active_event.json); an internal,
argparse-invisible keyword-only seam on main() exists solely for isolated
test injection and can never be reached from the command line.

Sections
  §1  Imports & constants
  §2  CSV loaders
  §3  Identity resolution (delegates to engine/identity_resolver.py)
  §4  Dual-vector SG composites
  §5  Venue trait calculations
  §6  Anti-pattern gates
  §7  Math utilities
  §8  Sparkline parser
  §9  Narrative engine
  §10 Main pipeline
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity_resolver import (  # noqa: E402
    FieldIndex,
    SourceFamilyResult,
    SourceRow,
    build_field_index,
    build_player_provenance,
    build_release_report,
)
from identity_resolver import normalize_name as _canonical_normalize_name  # noqa: E402
from event_context import (  # noqa: E402
    EventContext,
    EventContextError,
    load_pre_event_context,
    require_supported_context,
)
from venuedna_scoring import (  # noqa: E402
    FORMULA_METADATA as CANONICAL_FORMULA_METADATA,
    assign_tier as canonical_assign_tier,
    compute_player_projection,
    compute_probability_vectors as canonical_compute_probability_vectors,
    z_score_scale as canonical_z_score_scale,
)

# ── §1  Constants ──────────────────────────────────────────────────────────────

# Temporary capability gate (see require_supported_context() call in main()):
# SIM_COURSES_FILES below and the tpc_twin_cities_CH.csv loader, plus the
# narrative copy in build_headline()/build_win_case(), remain hardcoded to
# this one event/venue pending a separately authorized venue-generalization
# migration. Do not run this producer's remaining logic for another event or
# venue by editing these two constants alone.
SUPPORTED_EVENT_SLUG = "2026_3m_open"
SUPPORTED_VENUE_SLUG = "tpc_twin_cities"

ALL_COURSES_FILES = {
    "6m":  "pga_sg_query_allcourses_l6.csv",
    "12m": "pga_sg_query_allcourses_l12.csv",
    "24m": "pga_sg_query_allcourses_l24.csv",
}
SIM_COURSES_FILES = {
    "6m":  "pga_sg_query_3Mopen_similar_l6.csv",
    "12m": "pga_sg_query_3Mopen_similar_l12.csv",
    "24m": "pga_sg_query_3Mopen_similar_l24.csv",
}

DELTA_CLAMP = 0.50

# Composite blending weights (scoring spec §6) — named so the parity/
# decomposition layer (engine/scoring_decomposition.py) can import them
# instead of redeclaring the same numbers.
BASE_WEIGHT_6M,  BASE_WEIGHT_12M,  BASE_WEIGHT_24M  = 0.20, 0.30, 0.50
DELTA_WEIGHT_6M, DELTA_WEIGHT_12M, DELTA_WEIGHT_24M = 0.50, 0.30, 0.20

TEMPS       = {"win": 3.5, "top5": 5.0, "top10": 7.0, "top20": 10.0}
N_POSITIONS = {"win": 1,   "top5": 5,   "top10": 10,  "top20": 20}

ZNORM_MEAN, ZNORM_STD = 50.0, 15.0

# Venue trait weights (TPC Twin Cities venue profile §6)
VW_APPROACH  = 0.40
VW_LONG_IRON = 0.25
VW_OTT       = 0.20
VW_CH        = 0.10
VW_FORM      = 0.05

# Anti-pattern gate thresholds
BOMB_DIST_THRESH = 0.15     # driving_dist_adj above
BOMB_ACC_THRESH  = -0.05    # driving_acc_adj below
SG_APP_THRESH    = 0.20     # app_true below = weak approach
SG_SUM_THRESH    = 1.00     # putt_true + arg_true above = short-game reliant
PENALTY_BOMBER   = 0.92
PENALTY_SG_DEP   = 0.90

# Debut course-history haircut (venue profile §12)
DEBUT_CH_HAIRCUT = -0.25

# Live-round wave modifier (±VTS points on 0-100 scale)
WAVE_MODIFIER      = 1.5
EARLY_WAVE_CONTEXT = "capitalizing on favorable 7-9 mph morning winds."
LATE_WAVE_CONTEXT  = "facing tougher 11-14 mph afternoon winds."

# std_dev → VTS floor/ceil: 1 stroke ≈ 5 VTS points
STD_VTS_SCALE = 5.0

# Narrative thresholds (all per-round stroke units)
THRESH_ELITE_APP   = 1.00
THRESH_STRONG_APP  = 0.60
THRESH_VENUE_FIT   = 0.15   # delta_fit
THRESH_CTRL_POWER  = 0.60   # ott_true
THRESH_COURSE_PED  = 0.04   # ch_adjustment
THRESH_HOT_FORM    = 1.50   # true_sg_l20
THRESH_APP_DEFICIT = 0.00
THRESH_LI_GAP      = -0.05  # trait_long_iron_raw

# Display trait config — (label, venue_weight) in order matching d_keys
TRAIT_DISPLAY_CFG = [
    ("SG: Approach",     VW_APPROACH),
    ("App 150-200",      VW_LONG_IRON),
    ("Total Driving",    VW_OTT),
    ("Course History",   VW_CH),
    ("Recent Form",      VW_FORM),
    ("Par 5 Scoring",    0.00),
    ("Driving Accuracy", 0.00),
    ("Driving Distance", 0.00),
    ("SG: Putting",      0.00),
    ("Closing Holes",    0.00),
]

# ── §2  CSV Loaders ────────────────────────────────────────────────────────────

def safe_float(v: object, default: float = 0.0) -> float:
    try:
        s = str(v).strip().lower()
        return float(v) if s not in ("", "null", "none", "n/a", "nan") else default
    except (ValueError, TypeError):
        return default


def optional_float(v: object) -> float | None:
    """Parse a finite numeric source value without turning absence into zero."""
    try:
        s = str(v).strip().lower()
        value = float(v) if s not in ("", "null", "none", "n/a", "nan") else None
        return value if value is not None and math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def optional_rounds(v: object) -> int | None:
    """Parse a non-negative integral round count while preserving missingness."""
    value = optional_float(v)
    if value is None or value < 0 or not value.is_integer():
        return None
    return int(value)


def normalize_name(s: str | None) -> str:
    """Compatibility wrapper — delegates to the canonical identity resolver.

    Retained because non-identity logic in this file (live-round tee-time
    and R1 SG joins) and existing tests import ``normalize_name`` directly
    from this module. All identity-resolution behavior itself lives in
    ``engine/identity_resolver.py``.
    """
    return _canonical_normalize_name(s)


def load_field_rows(path: Path) -> list[dict]:
    """Raw ordered rows from pga_field.csv, for canonical field-index
    construction. Unlike the pre-resolver loaders, this preserves every
    column rather than projecting down to name/id only."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_sg_csv(path: Path) -> list[SourceRow]:
    """Row-preserving loader for one SG-query horizon file.

    Duplicate rows (same or colliding raw/normalized names) are preserved
    intact -- the identity resolver, not this loader, decides whether a
    duplicate is a release blocker. ``payload`` is ``{rounds, total_mean}``.
    """
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "rounds":     optional_rounds(row.get("rounds_played")),
                    "total_mean": optional_float(row.get("total_mean")),
                },
                row_number=i,
            ))
    return rows


def load_app_skill(path: Path) -> list[SourceRow]:
    """Row-preserving loader for sg-per-shot rows.

    ``payload`` is ``{sg_50_100, sg_100_150, sg_150_200, sg_200plus}``.
    """
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            if row.get("stat", "").strip().lower() != "sg per shot":
                continue
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "sg_50_100":  safe_float(row.get("50_100_fw_value")),
                    "sg_100_150": safe_float(row.get("100_150_fw_value")),
                    "sg_150_200": safe_float(row.get("150_200_fw_value")),
                    "sg_200plus": safe_float(row.get("over_200_fw_value")),
                },
                row_number=i,
            ))
    return rows


def load_app_prox(path: Path) -> list[SourceRow]:
    """Row-preserving loader for proximity rows. ``payload`` is a bare
    float (prox_150_200_ft); lower = closer = better."""
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            if row.get("stat", "").strip().lower() != "proximity (ft)":
                continue
            name = row.get("player_name", "").strip().strip('"')
            raw  = row.get("150_200_fw_value", "")
            if name and str(raw).strip().lower() not in ("", "null", "none"):
                rows.append(SourceRow(
                    source_name=name, dg_id=None, payload=safe_float(raw), row_number=i,
                ))
    return rows


def load_performance(path: Path) -> list[SourceRow]:
    """Row-preserving loader. ``payload`` is
    ``{putt_true, arg_true, app_true, ott_true}``."""
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "putt_true": safe_float(row.get("putt_true")),
                    "arg_true":  safe_float(row.get("arg_true")),
                    "app_true":  safe_float(row.get("app_true")),
                    "ott_true":  safe_float(row.get("ott_true")),
                },
                row_number=i,
            ))
    return rows


def load_decomp(path: Path) -> list[SourceRow]:
    """Row-preserving loader. ``payload`` is
    ``{driving_acc_adj, driving_dist_adj, std_dev}``."""
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "driving_acc_adj":  safe_float(row.get("driving_acc_adj")),
                    "driving_dist_adj": safe_float(row.get("driving_dist_adj")),
                    "std_dev":          safe_float(row.get("std_dev"), default=3.0),
                },
                row_number=i,
            ))
    return rows


def load_ch(path: Path) -> list[SourceRow]:
    """Row-preserving loader. ``payload`` is
    ``{ch_adjustment, experience_adj}``."""
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "ch_adjustment":  safe_float(row.get("ch_adjustment")),
                    "experience_adj": safe_float(row.get("experience_adjustment")),
                },
                row_number=i,
            ))
    return rows


def load_trending(path: Path) -> list[SourceRow]:
    """Row-preserving loader. ``payload`` is ``{true_sg_l20, l5_starts}``.

    ``dg_id`` (raw, not-yet-normalized) is captured on the ``SourceRow``
    itself when present -- pga_field_trending_table.csv is one of only two
    source families that carries it. It is not otherwise consumed by scoring.
    """
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            rows.append(SourceRow(
                source_name=name,
                dg_id=row.get("dg_id", "").strip() or None,
                payload={
                    "true_sg_l20": safe_float(row.get("true_sg_l20")),
                    "l5_starts":   row.get("l5_starts", "").strip(),
                },
                row_number=i,
            ))
    return rows


# ── §3  Identity Resolution ────────────────────────────────────────────────────
#
# All ID-first / name-fallback / fuzzy-diagnostic / mapping-integrity logic
# lives in engine/identity_resolver.py. This section only adapts this file's
# row-preserving `list[SourceRow]` loader shape into the resolver's row-
# sequence input, and reads results back out directly from the accepted
# match's own row -- never through a name-keyed re-lookup that could
# silently resolve to a different, later-loaded duplicate. It contains no
# matching logic of its own.

def _rows_for_resolution(source_rows: list[SourceRow]) -> list[dict]:
    """Adapt a ``list[SourceRow]`` into rows for ``resolve_source_family()``,
    carrying the original ``SourceRow`` through under ``_source_row`` so the
    accepted match's payload can be read back without any dict lookup keyed
    by (possibly duplicated) display name.
    """
    return [
        {"player_name": r.source_name, "dg_id": r.dg_id, "_source_row": r}
        for r in source_rows
    ]


def resolve_all_source_families(
    field_index: FieldIndex,
    *,
    all_sg: dict, sim_sg: dict,
    app_skill_data: list[SourceRow], app_prox_data: list[SourceRow],
    perf_data: list[SourceRow], decomp_data: list[SourceRow],
    ch_data: list[SourceRow], trending_data: list[SourceRow],
) -> dict[str, SourceFamilyResult]:
    """Resolve every supplementary source family against the canonical field
    index. Returns {family_name: SourceFamilyResult}, in a fixed, documented
    order (dict insertion order == iteration order == provenance order)."""
    from identity_resolver import resolve_source_family

    results: dict[str, SourceFamilyResult] = {}
    for horizon, rows in all_sg.items():
        results[f"all_{horizon}"] = resolve_source_family(
            f"all_{horizon}", field_index, _rows_for_resolution(rows)
        )
    for horizon, rows in sim_sg.items():
        results[f"sim_{horizon}"] = resolve_source_family(
            f"sim_{horizon}", field_index, _rows_for_resolution(rows)
        )
    results["skill"] = resolve_source_family(
        "skill", field_index, _rows_for_resolution(app_skill_data)
    )
    results["prox"] = resolve_source_family(
        "prox", field_index, _rows_for_resolution(app_prox_data)
    )
    results["perf"] = resolve_source_family(
        "perf", field_index, _rows_for_resolution(perf_data)
    )
    results["decomp"] = resolve_source_family(
        "decomp", field_index, _rows_for_resolution(decomp_data)
    )
    results["ch"] = resolve_source_family(
        "ch", field_index, _rows_for_resolution(ch_data)
    )
    results["trend"] = resolve_source_family(
        "trend", field_index, _rows_for_resolution(trending_data),
        dg_id_field="dg_id",
    )
    return results


def _matched_value(result: SourceFamilyResult, dg_id: str) -> object | None:
    """Return the accepted match's own preserved payload, read directly off
    the resolver's ``source_row`` -- never a name-keyed re-lookup."""
    match = result.matches_by_dg_id().get(dg_id)
    if match is None or match.source_row is None:
        return None
    source_row = match.source_row.get("_source_row")
    return source_row.payload if source_row is not None else None


# ── §4  Dual-Vector SG Composites ─────────────────────────────────────────────

def debut_row() -> dict:
    return {"rounds": 0, "total_mean": 0.0}


def compute_horizon(base: dict, sim: dict) -> dict:
    w = min(1.0, sim.get("rounds", 0) / 20.0)
    sg_sim_reg = w * sim["total_mean"] + (1 - w) * base["total_mean"]
    return {"delta_fit": sg_sim_reg - base["total_mean"]}


def adapt_to_v2_neutral_skill_horizons(all_resolved_raw: dict) -> dict:
    """Adapt resolved all-course rows to canonical NeutralSkill inputs.

    Takes per-horizon rows exactly as returned by ``_matched_value()`` --
    each either a row dict with ``total_mean``, or ``None`` when that source
    family has no row for this player -- and adapts them into
    ``compute_neutral_skill()``'s input shape, preserving the missing-vs-
    present distinction through the official producer path.
    """
    return {h: (row["total_mean"] if row is not None else None) for h, row in all_resolved_raw.items()}


def adapt_to_v2_similar_course_rows(sim_resolved_raw: dict) -> dict:
    """Adapt resolved similar-course rows to canonical VenueFit inputs.

    Takes per-horizon rows exactly as returned by ``_matched_value()`` and
    adapts them into ``compute_venue_fit()``'s input shape: a present row
    becomes a ``SimilarCourseRow`` (rounds 0 is a valid DEBUT row), a
    missing row stays ``None``.  Blank and malformed source cells remain
    ``None`` inside a present row for the canonical scorer to evaluate.
    """
    from venuedna_scoring import SimilarCourseRow

    return {
        h: (SimilarCourseRow(row["rounds"], row["total_mean"]) if row is not None else None)
        for h, row in sim_resolved_raw.items()
    }


def make_composites(all_resolved: dict, sim_resolved: dict) -> tuple[float, float, float]:
    """Return (sg_base_comp, sg_sim_comp, delta_fit_comp) from resolved horizon dicts."""
    sg_base = (BASE_WEIGHT_6M  * all_resolved["6m"]["total_mean"]
             + BASE_WEIGHT_12M * all_resolved["12m"]["total_mean"]
             + BASE_WEIGHT_24M * all_resolved["24m"]["total_mean"])
    delta = (DELTA_WEIGHT_6M  * compute_horizon(all_resolved["6m"],  sim_resolved["6m"])["delta_fit"]
           + DELTA_WEIGHT_12M * compute_horizon(all_resolved["12m"], sim_resolved["12m"])["delta_fit"]
           + DELTA_WEIGHT_24M * compute_horizon(all_resolved["24m"], sim_resolved["24m"])["delta_fit"])
    delta = max(-DELTA_CLAMP, min(DELTA_CLAMP, delta))
    return sg_base, sg_base + delta, delta


def historical_gate_diagnostics(perf: dict, decomp: dict) -> list[str]:
    """Expose historical 3M anti-pattern labels for narrative diagnostics only.

    This intentionally does not call ``apply_gates`` and never changes a
    canonical score, rank, tier, or probability.
    """
    flags: list[str] = []
    if decomp.get("driving_dist_adj", 0.0) > BOMB_DIST_THRESH and decomp.get("driving_acc_adj", 0.0) < BOMB_ACC_THRESH:
        flags.append("INACCURATE_BOMBER")
    if perf.get("app_true", 0.0) < SG_APP_THRESH and (perf.get("putt_true", 0.0) + perf.get("arg_true", 0.0)) > SG_SUM_THRESH:
        flags.append("SHORT_GAME_RELIANT")
    return flags


# ── §5  Venue Trait Calculations ───────────────────────────────────────────────

def compute_trait_approach(skill: dict) -> float:
    """Distance-weighted fw SG per shot (per-shot units, ~[-0.1, 0.1])."""
    return (0.10 * skill["sg_50_100"]
          + 0.20 * skill["sg_100_150"]
          + 0.40 * skill["sg_150_200"]
          + 0.30 * skill["sg_200plus"])


def compute_trait_long_iron(skill: dict, prox_z_raw: float) -> float:
    """0.65 × sg_150_200 + 0.35 × z-raw(−prox). prox_z_raw already inverted."""
    return 0.65 * skill["sg_150_200"] + 0.35 * prox_z_raw


def prox_to_z_raw(prox: float, field_mean: float, field_std: float) -> float:
    """Lower proximity (ft) = better. Negate so higher return = better player."""
    return -(prox - field_mean) / (field_std + 1e-9)


def combine_raw_score(
    sg_sim_comp: float,
    trait_approach_raw: float,
    trait_long_iron_raw: float,
    ott_true: float,
    ch_adj: float,
    true_sg_l20: float,
) -> dict:
    """Decomposition of the pre-gate combined-raw VTS input.

    ``pre_gate_raw_total`` is calculated through the same direct,
    left-associated ``a + b + c + d + e + f`` expression -- same operand
    order, same grouping, same numeric literals -- as the addends
    previously inlined in ``main()``. It is calculated directly from the
    six terms below, never through the returned dict, ``sum()``, a loop,
    or any other reduction over a (re)ordered collection: those paths
    insert an implicit leading ``0 + …`` that silently normalizes an
    all-``-0.0`` input's signed-zero result to ``+0.0``, which the literal
    expression does not do. The per-component values are exposed in the
    returned dict for diagnostics/reporting only; that dict does not
    itself compute or alter the production total. Consumed directly by
    ``main()`` and by the read-only parity layer in
    ``engine/scoring_decomposition.py``; contains no I/O.
    """
    approach_term       = VW_APPROACH  * trait_approach_raw
    long_iron_term      = VW_LONG_IRON * trait_long_iron_raw
    ott_term            = VW_OTT       * ott_true
    course_history_term = VW_CH        * ch_adj
    recent_form_term    = VW_FORM      * true_sg_l20

    pre_gate_raw_total = (
        sg_sim_comp
        + approach_term
        + long_iron_term
        + ott_term
        + course_history_term
        + recent_form_term
    )

    return {
        "sg_similar_composite": sg_sim_comp,
        "approach":             approach_term,
        "long_iron":            long_iron_term,
        "ott":                  ott_term,
        "course_history":       course_history_term,
        "recent_form":          recent_form_term,
        "pre_gate_raw_total":   pre_gate_raw_total,
    }


# ── §6  Anti-Pattern Gates ─────────────────────────────────────────────────────

def apply_gates(raw: float, perf: dict, decomp: dict) -> tuple[float, list[str]]:
    """Multiplicative penalties before z-score. Returns (adjusted_raw, flags)."""
    flags: list[str] = []
    dist_adj = decomp.get("driving_dist_adj", 0.0)
    acc_adj  = decomp.get("driving_acc_adj",  0.0)
    app_true = perf.get("app_true", 0.0)
    putt     = perf.get("putt_true", 0.0)
    arg      = perf.get("arg_true",  0.0)

    if dist_adj > BOMB_DIST_THRESH and acc_adj < BOMB_ACC_THRESH:
        raw *= PENALTY_BOMBER
        flags.append("INACCURATE_BOMBER")

    if app_true < SG_APP_THRESH and (putt + arg) > SG_SUM_THRESH:
        raw *= PENALTY_SG_DEP
        flags.append("SHORT_GAME_RELIANT")

    return raw, flags


# ── §7  Math Utilities ─────────────────────────────────────────────────────────

def field_stats(values: list[float]) -> tuple[float, float]:
    valid = [v for v in values if v != 0.0]
    if not valid:
        return 0.0, 1.0
    mu  = sum(valid) / len(valid)
    var = sum((v - mu) ** 2 for v in valid) / len(valid)
    return mu, math.sqrt(var) if var > 0 else 1.0


def z_score_scale(values: list[float]) -> list[float]:
    mu, sd = field_stats(values)
    return [max(0.0, min(100.0, ZNORM_MEAN + ZNORM_STD * (v - mu) / sd))
            for v in values]


def tempered_softmax(scores: list[float], T: float, n_pos: int) -> list[float]:
    max_s = max(scores)
    exps  = [math.exp((s - max_s) / T) for s in scores]
    total = sum(exps)
    return [min(99.9, (e / total) * n_pos * 100) for e in exps]


def enforce_monotonicity(p: dict) -> None:
    p["top5Pct"]  = max(p["top5Pct"],  p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])


def assign_tier(rank: int) -> str:
    if rank <= 5:   return "T1"
    if rank <= 12:  return "T2"
    if rank <= 25:  return "T3"
    if rank <= 40:  return "T4"
    return "T5"


def make_cut_prob(top20: float) -> float:
    return min(98.0, max(20.0, top20 * 1.25 + 10.0))


# ── §8  Sparkline Parser ───────────────────────────────────────────────────────

def parse_l5_starts(raw: str) -> list[int]:
    """'tour-event-POS_...' → numeric array. CUT/WD/DQ/MDF/DNS → 80."""
    if not raw or not raw.strip():
        return []
    result: list[int] = []
    for entry in raw.strip().split("_"):
        parts   = entry.strip().split("-")
        pos_str = parts[-1].strip().upper()
        if pos_str in ("CUT", "WD", "DQ", "W/D", "MDF", "DNS"):
            result.append(80)
        else:
            pos_str = pos_str.lstrip("T")
            try:
                result.append(int(pos_str))
            except ValueError:
                result.append(80)
    return result


# ── §9  Narrative Engine ───────────────────────────────────────────────────────

def lastname_first_to_first_last(s: str) -> str:
    """'Doe, John' → 'John Doe' for name-matching compatibility."""
    if "," in s:
        last, first = s.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return s


def load_tee_times(path: Path) -> dict[str, dict]:
    """{norm_name: {r2_wave, r2_teetime}} from round2_tee_times.csv.
    CSV names are 'Last, First' matching pga_field.csv — normalized as-is."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("player_name", "").strip().strip('"').strip("'")
            if not raw:
                continue
            norm  = normalize_name(raw)
            wave  = row.get("r2_wave", "").strip().lower()
            ttime = row.get("r2_teetime", "").strip()
            if norm:
                result[norm] = {"r2_wave": wave, "r2_teetime": ttime}
    return result


def load_r1_sg(path: Path) -> dict[str, dict]:
    """{norm_name: {r1_score, sg_total, sg_approach}} from round1 SG file.
    Amateur rows (TOT == '(a)') carry an extra column that shifts SG fields right by 1."""
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("Player", "").strip().strip('"')
            if not name:
                continue
            is_amateur = row.get("TOT", "").strip() == "(a)"
            if is_amateur:
                r1_score    = row.get("SG-Off The Tee", "").strip()
                sg_approach = row.get("SG-Approach to Green (Rank)", "").strip()
                sg_total    = row.get("SG Total (Rank)", "").strip()
            else:
                r1_score    = row.get("R1", "").strip()
                sg_approach = row.get("SG-Approach to Green", "").strip()
                sg_total    = row.get("SG Total", "").strip()
            if not r1_score or r1_score == "-":
                continue
            result[normalize_name(name)] = {
                "r1_score":    r1_score,
                "sg_total":    safe_float(sg_total),
                "sg_approach": safe_float(sg_approach),
            }
    return result

def build_strength_tags(app_true: float, delta_fit: float, ott_true: float,
                        ch_adj: float, true_sg_l20: float) -> list[str]:
    tags: list[str] = []
    if app_true > THRESH_ELITE_APP:
        tags.append(f"Elite Iron Play (+{app_true:.2f})")
    elif app_true > THRESH_STRONG_APP:
        tags.append(f"Strong Approach Play (+{app_true:.2f})")
    if delta_fit > THRESH_VENUE_FIT:
        tags.append(f"Strong Venue Fit (+{delta_fit:.2f})")
    elif delta_fit > 0.05:
        tags.append(f"Positive Venue Fit (+{delta_fit:.2f})")
    if ott_true > THRESH_CTRL_POWER:
        tags.append("Controlled Power")
    if ch_adj > THRESH_COURSE_PED:
        tags.append("Proven Course Pedigree")
    if true_sg_l20 > THRESH_HOT_FORM:
        tags.append(f"Red-Hot Form ({true_sg_l20:.2f} SG L20)")
    if not tags:
        tags.append("Field-Average Profile")
    return tags


def build_weakness_tags(app_true: float, trait_long_iron_raw: float,
                        data_depth: str, course_debut: bool,
                        gate_flags: list[str]) -> list[str]:
    tags: list[str] = []
    if app_true < THRESH_APP_DEFICIT:
        tags.append("Approach Deficit")
    if "INACCURATE_BOMBER" in gate_flags:
        tags.append("Accuracy Risk")
    if course_debut:
        tags.append("Venue Debut")
    if trait_long_iron_raw < THRESH_LI_GAP:
        tags.append("Long-Iron Gap")
    if not tags:
        tags.append("No Clear Structural Risk")
    return tags


def build_headline(strength_tags: list[str], weakness_tags: list[str]) -> str:
    top = strength_tags[0]
    if top == "Field-Average Profile":
        return "Field-average fit — outcome driven by weekly form variance."
    if "Elite Iron Play" in top:
        return f"Approach-first contender — {top.lower()} at TPC's longer-skewed layout."
    if "Venue Fit" in top:
        return f"Structurally aligned — {top} creates upside above raw form."
    if "Course Pedigree" in top:
        return f"Track record matters here — {top} anchors the pre-tournament case."
    if "Red-Hot Form" in top:
        return f"Form player entering a birdiefest — {top} adds scoreboard pressure."
    return f"{top} is the primary driver of the pre-tournament case."


def build_win_case(player: str, app_true: float, delta_fit: float,
                   ott_true: float, strength_tags: list[str],
                   weakness_tags: list[str]) -> str:
    # Primary mechanism
    if app_true > THRESH_ELITE_APP:
        mech = (f"elite approach play (+{app_true:.2f} SG: App). "
                "TPC Twin Cities has crowned 6 of 7 winners since 2019 who ranked "
                "top-10 in approach for the week.")
    elif app_true > THRESH_STRONG_APP:
        mech = (f"above-average approach play (+{app_true:.2f} SG: App) at a venue "
                "where 46% of approaches arrive from 175+ yards.")
    elif delta_fit > THRESH_VENUE_FIT:
        mech = (f"a historically strong fit for similar-course scoring environments "
                f"(delta fit +{delta_fit:.2f}).")
    elif ott_true > THRESH_CTRL_POWER:
        mech = ("controlled total driving — water threatens 9 of 14 driving holes "
                "and the combination of distance with directional control is the structural edge.")
    else:
        mech = ("consistent ball-striking in TPC Twin Cities' birdiefest environment, "
                "where sustained iron quality separates contenders from scoreboard noise.")

    # Primary risk
    if "Accuracy Risk" in weakness_tags:
        risk = ("Primary risk: driver accuracy. Water on 9 driving holes amplifies "
                "dispersion into compounding mistakes.")
    elif "Long-Iron Gap" in weakness_tags:
        risk = ("Primary risk: long-iron gap. With 46% of approaches from 175+ yards, "
                "a 150-200 deficit creates a ceiling on birdie production from quality positions.")
    elif "Venue Debut" in weakness_tags:
        risk = ("First-timer risk: the closing stretch (H16-H17-H18) introduces "
                "decision-quality pressure without prior calibration under tournament conditions.")
    elif "Approach Deficit" in weakness_tags:
        risk = ("Approach play grades below field average — the primary win mechanism here. "
                "A short-game spike is required to compensate.")
    else:
        risk = ("Form trajectory holds the key — when approach and ball-striking peak, "
                "the contention path opens fully.")

    # Par-5 close
    if ott_true > 0.40:
        p5 = ("Par-5 conversion on H6, H12, and H18 (all 593-596 yards) "
              "will separate a top-10 from a podium finish.")
    else:
        p5 = ("Precision through the closing stretch (H16-H17-H18) — "
              "not just birdie volume — determines where this week lands.")

    return f"{player} wins through {mech} {risk} {p5}"


def build_live_r1_narrative(player: str, r1_score: str, sg_approach: float,
                            r2_wave: str) -> str:
    wave_ctx = EARLY_WAVE_CONTEXT if r2_wave == "early" else LATE_WAVE_CONTEXT
    sg_fmt = f"+{sg_approach:.3f}" if sg_approach >= 0 else f"{sg_approach:.3f}"
    return (
        f"[LIVE R1 UPDATE]: {player} shot {r1_score} in Round 1, gaining "
        f"{sg_fmt} strokes on Approach. They draw the {r2_wave} wave for "
        f"Round 2, {wave_ctx}"
    )


CANONICAL_PROBABILITY_FIELDS = (
    "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
)
_OUTPUT_PRIVATE_FIELDS = {
    "_post_gate_raw", "_nsi_raw", "gate_flags", "course_debut",
    "_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
    "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure",
}
_OUTPUT_FIRST_FIELDS = [
    "rank", "player", "player_name", "player_id", "dg_id", "tier",
    "vts_final", "live_vts",
    "neutralSkillIndex",
    "sg_base_composite", "sg_similar_composite", "delta_fit", "data_depth",
    "formula_id", "formula_version", "scoring_spec_version", "comparable_score_family", "penalty_gate_set_id",
    "penalties_applied", "gates_applied",
    "scoring_status", "confidence_by_source",
    "neutral_skill_raw", "venue_fit_delta_raw", "venue_history_delta_raw",
    "pre_penalty_raw", "post_penalty_raw", "post_gate_raw",
    "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
    "win_prob", "top_5_prob", "top_10_prob", "top_20_prob",
    "make_cut_prob", "miss_cut_prob",
    "prepenalty_vts", "vts_floor", "vts_ceil", "std_dev",
    "l5_array", "strength_tags", "weakness_tags", "headline", "win_case",
    "scouting_report",
    "trait_scores", "archetype_tags", "anti_pattern_flags",
    "app_true", "ott_true", "ch_adjustment", "true_sg_l20",
    "trait_approach_raw", "trait_long_iron_raw",
    "r2_wave", "r2_teetime",
    "identity_provenance",
]


def finalize_canonical_official_records(
    prepared_records: list[dict],
    *,
    live_mode: str | None,
    live_tee_times: dict[str, dict],
    live_r1_sg: dict[str, dict],
) -> list[dict]:
    """Pure canonical finalization boundary for prepared player records.

    The caller supplies already-resolved player evidence and display-only
    trait scores.  This helper owns every official score, probability, rank,
    tier, and final-record decision; it neither reads external state nor
    mutates the caller-owned prepared records.
    """
    scored_players = [record for record in prepared_records if record["post_gate_raw"] is not None]
    canonical_raw_scores = [record["post_gate_raw"] for record in scored_players]
    normalized_scores = canonical_z_score_scale(canonical_raw_scores)
    neutral_skill_scores = canonical_z_score_scale([record["_nsi_raw"] for record in scored_players])
    prepenalty_scores = canonical_z_score_scale([record["pre_penalty_raw"] for record in scored_players])
    probability_vectors = canonical_compute_probability_vectors(canonical_raw_scores)
    scored_index_by_dg_id = {record["dg_id"]: index for index, record in enumerate(scored_players)}
    display_keys = [
        "_d_approach", "_d_long_iron", "_d_ott", "_d_ch", "_d_form",
        "_d_par5", "_d_drv_acc", "_d_drv_dist", "_d_putt", "_d_composure",
    ]
    display_scores = {
        key: z_score_scale([record[key] for record in prepared_records])
        for key in display_keys
    }

    pre_rank_records: list[dict] = []
    for raw_index, prepared in enumerate(prepared_records):
        scored_index = scored_index_by_dg_id.get(prepared["dg_id"])
        if scored_index is not None:
            canonical_vts = round(normalized_scores[scored_index], 1)
            probabilities = {
                key: round(value, 1)
                for key, value in probability_vectors[scored_index].items()
            }
            record = {
                **prepared,
                "vts_final": canonical_vts,
                "neutralSkillIndex": round(neutral_skill_scores[scored_index], 1),
                "prepenalty_vts": round(prepenalty_scores[scored_index], 1),
                **probabilities,
            }
        else:
            record = {
                **prepared,
                "vts_final": None,
                "neutralSkillIndex": None,
                "prepenalty_vts": None,
                **{key: None for key in CANONICAL_PROBABILITY_FIELDS},
            }

        record["win_prob"] = record["winPct"]
        record["top_5_prob"] = record["top5Pct"]
        record["top_10_prob"] = record["top10Pct"]
        record["top_20_prob"] = record["top20Pct"]
        record["make_cut_prob"] = record["makeCutPct"]
        record["miss_cut_prob"] = record["missCutPct"]

        spread = round(record["std_dev"] * STD_VTS_SCALE, 1)
        record["vts_floor"] = (
            round(max(0.0, record["vts_final"] - spread), 1)
            if record["vts_final"] is not None else None
        )
        record["vts_ceil"] = (
            round(min(100.0, record["vts_final"] + spread), 1)
            if record["vts_final"] is not None else None
        )
        record["trait_scores"] = [
            {
                "label": label,
                "weight": weight,
                "score": round(display_scores[display_keys[index]][raw_index], 1),
            }
            for index, (label, weight) in enumerate(TRAIT_DISPLAY_CFG)
        ]

        arc_dist = display_scores["_d_drv_dist"][raw_index]
        arc_acc = display_scores["_d_drv_acc"][raw_index]
        arc_app = display_scores["_d_approach"][raw_index]
        arc_long_iron = display_scores["_d_long_iron"][raw_index]
        arc_putt = display_scores["_d_putt"][raw_index]
        arc_composure = display_scores["_d_composure"][raw_index]
        archetype_tags: list[str] = []
        if arc_dist >= 75 and arc_acc <= 30:
            archetype_tags.append("Erratic Bomber")
        if arc_putt >= 70 and arc_composure >= 70 and arc_app <= 40:
            archetype_tags.append("Short-Game Specialist")
        putt_value = record.get("_d_putt") or 0.0
        positive_sg = sum(value for value in [
            record.get("app_true", 0.0), record.get("ott_true", 0.0),
            putt_value, record.get("ch_adjustment", 0.0),
        ] if value and value > 0)
        if positive_sg > 0 and putt_value > 0 and putt_value >= 0.6 * positive_sg:
            archetype_tags.append("Putting Reliant")
        if arc_long_iron <= 30:
            archetype_tags.append("Weak Long-Iron")
        record["archetype_tags"] = archetype_tags

        strength = build_strength_tags(
            record["app_true"], record["delta_fit"] or 0.0, record["ott_true"],
            record["ch_adjustment"], record["true_sg_l20"]
        )
        weakness = build_weakness_tags(
            record["app_true"], record["trait_long_iron_raw"],
            record["data_depth"], record["course_debut"], record["gate_flags"]
        )
        record["strength_tags"] = strength
        record["weakness_tags"] = weakness
        record["headline"] = build_headline(strength, weakness)
        record["win_case"] = build_win_case(
            record["player"], record["app_true"], record["delta_fit"] or 0.0,
            record["ott_true"], strength, weakness
        )
        record["anti_pattern_flags"] = record["gate_flags"]
        record["player_name"] = record["player"]

        if live_mode == "r1":
            wave_info = live_tee_times.get(normalize_name(record["player"]), {})
            wave = wave_info.get("r2_wave", "")
            live_base = normalized_scores[scored_index] if scored_index is not None else 50.0
            if wave == "early":
                live_value = min(100.0, max(0.0, live_base + WAVE_MODIFIER))
            elif wave == "late":
                live_value = min(100.0, max(0.0, live_base - WAVE_MODIFIER))
            else:
                live_value = live_base
            record["live_vts"] = round(live_value, 1)
            record["r2_wave"] = wave
            record["r2_teetime"] = wave_info.get("r2_teetime", "")
            sg_info = live_r1_sg.get(normalize_name(lastname_first_to_first_last(record["player"])), {})
            if wave and sg_info:
                narrative = build_live_r1_narrative(
                    record["player"],
                    sg_info.get("r1_score", "—"),
                    sg_info.get("sg_approach", 0.0),
                    wave,
                )
                record["win_case"] = narrative + " " + record["win_case"]
        record["scouting_report"] = record["win_case"]
        pre_rank_records.append(record)

    ordered_scored_records = sorted(
        (record for record in pre_rank_records if record["post_gate_raw"] is not None),
        key=lambda record: record["vts_final"],
        reverse=True,
    )
    unscored_records = [
        record for record in pre_rank_records if record["post_gate_raw"] is None
    ]
    final_records = [
        {"rank": rank, **record, "tier": canonical_assign_tier(rank)}
        for rank, record in enumerate(ordered_scored_records, 1)
    ] + [
        {"rank": None, **record, "tier": None}
        for record in unscored_records
    ]

    def reorder_record(record: dict) -> dict:
        source = dict(record)
        source["identity_provenance"] = source.pop("_identity_provenance")
        output: dict = {}
        for key in _OUTPUT_FIRST_FIELDS:
            if key in source:
                output[key] = source[key]
        for key, value in source.items():
            if key not in output and key not in _OUTPUT_PRIVATE_FIELDS:
                output[key] = value
        return output

    ordered_records = [reorder_record(record) for record in final_records]
    return ordered_records


# ── §10  Main Pipeline ─────────────────────────────────────────────────────────

def main(*, _context: EventContext | None = None, _live_mode: str | None = None) -> None:
    """Production entry point.

    Normal command-line execution (``python engine/enrich_cards.py``) takes
    no arguments. Any argument -- including a former ``--event`` or
    ``--live`` -- is unrecognized and causes argparse's own error handling
    to print usage and exit nonzero before any event-bound path is
    constructed. ``config/active_event.json`` is the sole source of event
    context for normal execution; there is no CLI flag, environment
    variable, or fallback that selects an event without it.

    ``_context``/``_live_mode`` are keyword-only and never populated by
    argparse -- they exist solely so isolated tests can inject an explicit,
    already-validated ``EventContext`` (and, where legitimate, an explicit
    live-round mode) without writing a real manifest file or going through
    the command line. No command-line invocation can set either parameter.
    """
    if _context is not None:
        context = _context
        live_mode = _live_mode
    else:
        parser = argparse.ArgumentParser(description="VenueDNA enrichment pipeline")
        parser.parse_args()  # no flags are defined -- any argument exits nonzero here

        try:
            context = load_pre_event_context(
                _ROOT / "config" / "active_event.json", repo_root=_ROOT,
            )
            require_supported_context(
                context,
                supported_event_slug=SUPPORTED_EVENT_SLUG,
                supported_venue_slug=SUPPORTED_VENUE_SLUG,
            )
        except EventContextError as exc:
            print(f"[enrich_cards] ERROR — {exc}", file=sys.stderr)
            sys.exit(1)
        live_mode = None

    event_slug = context.event_slug
    event_name = context.event_name
    venue_name = context.venue_name
    event_dir  = context.event_root

    input_dir  = event_dir / "input"
    output_dir = event_dir / "output"
    deploy_dir = event_dir / "deploy" / "data"

    # ── Load all source files ──────────────────────────────────────────────────
    print("[enrich_cards] Loading source files…")

    field_rows = load_field_rows(input_dir / "pga_field.csv")
    if not field_rows:
        print("[enrich_cards] ERROR — pga_field.csv missing or empty", file=sys.stderr)
        sys.exit(1)

    all_sg = {h: load_sg_csv(input_dir / f) for h, f in ALL_COURSES_FILES.items()}
    sim_sg = {h: load_sg_csv(input_dir / f) for h, f in SIM_COURSES_FILES.items()}

    app_skill_data = load_app_skill(input_dir / "app_skill_l12_sg.csv")
    app_prox_data  = load_app_prox(input_dir  / "app_skill_l12_prox.csv")
    perf_data      = load_performance(input_dir / "dg_performance_2026.csv")
    decomp_data    = load_decomp(input_dir    / "dg_decomposition.csv")
    ch_data        = load_ch(input_dir        / "tpc_twin_cities_CH.csv")
    trending_data  = load_trending(input_dir  / "pga_field_trending_table.csv")

    # ── Identity resolution (ID-first; fuzzy is diagnostic-only) ────────────────
    print("[enrich_cards] Resolving player identity…")

    field_index = build_field_index(field_rows, name_field="player_name", dg_id_field="dg_id")
    source_results = (
        resolve_all_source_families(
            field_index,
            all_sg=all_sg, sim_sg=sim_sg,
            app_skill_data=app_skill_data, app_prox_data=app_prox_data,
            perf_data=perf_data, decomp_data=decomp_data,
            ch_data=ch_data, trending_data=trending_data,
        )
        if field_index.is_valid else {}
    )
    release_report = build_release_report(field_index, list(source_results.values()))

    print(f"  Field: {len(field_index.identities)} players, "
          f"{len(field_index.identities)} with dg_id")

    if release_report.is_release_blocked:
        print("[enrich_cards] IDENTITY RELEASE BLOCKED", file=sys.stderr)
        print(release_report.render(), file=sys.stderr)
        sys.exit(1)

    for w in release_report.warnings:
        print(f"[enrich_cards] WARNING [{w.code}] {w.family or '-'}: {w.message}", file=sys.stderr)

    # ── Per-player raw computation ─────────────────────────────────────────────
    print("[enrich_cards] Computing latent scores…")

    _EMPTY_SKILL  = {"sg_50_100": 0.0, "sg_100_150": 0.0, "sg_150_200": 0.0, "sg_200plus": 0.0}
    _EMPTY_PERF   = {"putt_true": 0.0, "arg_true": 0.0, "app_true": 0.0, "ott_true": 0.0}
    _EMPTY_DECOMP = {"driving_acc_adj": 0.0, "driving_dist_adj": 0.0}
    _EMPTY_TREND  = {"true_sg_l20": 0.0, "l5_starts": ""}

    # Field-level std_dev fallback
    std_vals       = [r.payload["std_dev"] for r in decomp_data if r.payload["std_dev"] > 0]
    field_std_mean = sum(std_vals) / len(std_vals) if std_vals else 3.0
    _EMPTY_DECOMP["std_dev"] = field_std_mean

    # Field-level proximity stats for prox→z-raw conversion
    prox_values          = [r.payload for r in app_prox_data]
    prox_mean, prox_std  = field_stats(prox_values) if prox_values else (30.0, 4.0)

    players_raw: list[dict] = []

    for ident in field_index.identities:
        name = ident.display_name

        # Canonical v2 inputs retain absent rows and invalid source cells as
        # missing.  Do not route these through the historical debut fallback.
        all_raw = {h: _matched_value(source_results[f"all_{h}"], ident.dg_id) for h in all_sg}
        sim_raw = {h: _matched_value(source_results[f"sim_{h}"], ident.dg_id) for h in sim_sg}
        projection = compute_player_projection(
            adapt_to_v2_neutral_skill_horizons(all_raw),
            adapt_to_v2_similar_course_rows(sim_raw),
            venue_history_evidence=None,
        )
        sg_base_comp = projection.neutral_skill_raw
        delta_fit = projection.venue_fit_delta_raw
        sg_sim_comp = (
            sg_base_comp + delta_fit
            if sg_base_comp is not None and delta_fit is not None
            else None
        )
        data_depth = projection.data_depth

        # Supplementary data
        skill  = _matched_value(source_results["skill"],  ident.dg_id) or _EMPTY_SKILL.copy()
        prox   = _matched_value(source_results["prox"],   ident.dg_id)
        perf   = _matched_value(source_results["perf"],   ident.dg_id) or _EMPTY_PERF.copy()
        decomp = _matched_value(source_results["decomp"], ident.dg_id) or _EMPTY_DECOMP.copy()
        ch     = _matched_value(source_results["ch"],     ident.dg_id)
        trend  = _matched_value(source_results["trend"],  ident.dg_id) or _EMPTY_TREND.copy()

        course_debut = data_depth == "DEBUT"
        ch_adj = ch["ch_adjustment"] if ch is not None else 0.0

        # Proximity z-raw (inverted: lower prox in feet → higher score)
        if prox is not None:
            prox_z_raw = prox_to_z_raw(prox, prox_mean, prox_std)
        else:
            prox_z_raw = 0.0   # imputed to field mean → z-raw = 0

        # Trait raw values
        trait_approach_raw  = compute_trait_approach(skill)
        trait_long_iron_raw = compute_trait_long_iron(skill, prox_z_raw)
        ott_true             = perf["ott_true"]
        app_true             = perf["app_true"]
        true_sg_l20           = trend["true_sg_l20"]

        # Historical 3M anti-pattern labels remain diagnostic only.  Canonical
        # v2 declares an identity penalty/gate set and derives all official
        # score outputs below from projection.post_gate_raw.
        gate_flags = historical_gate_diagnostics(perf, decomp)

        # Raw values for display trait z-scoring (after full field collected)
        par5_raw      = 0.55 * ott_true + 0.45 * app_true
        composure_raw = 1.0 / (decomp["std_dev"] + 0.1)

        players_raw.append({
            # Identity
            "player":               name,
            "player_id":            ident.dg_id,  # deprecated compatibility alias of dg_id
            "dg_id":                ident.dg_id,
            "_identity_provenance": build_player_provenance(ident, list(source_results.values())),
            "data_depth":           data_depth,
            "course_debut":         course_debut,
            # Dual-vector SG
            "sg_base_composite":    round(sg_base_comp, 4) if sg_base_comp is not None else None,
            "sg_similar_composite": round(sg_sim_comp, 4) if sg_sim_comp is not None else None,
            "delta_fit":            round(delta_fit, 4) if delta_fit is not None else None,
            # Historical diagnostic gate state (not canonical score input)
            "gate_flags":           gate_flags,
            # Canonical decomposition and latent score (field-normalized after loop)
            "formula_id":           projection.formula_metadata["formula_id"],
            "formula_version":      projection.formula_metadata["formula_version"],
            "scoring_spec_version": projection.formula_metadata["scoring_spec_version"],
            "comparable_score_family": projection.formula_metadata["comparable_score_family"],
            "penalty_gate_set_id":  projection.formula_metadata["penalty_gate_set_id"],
            "penalties_applied":    list(projection.penalties_applied),
            "gates_applied":        list(projection.gates_applied),
            "scoring_status":       projection.status,
            "confidence_by_source": dict(projection.confidence_by_source),
            "neutral_skill_raw":    projection.neutral_skill_raw,
            "venue_fit_delta_raw":  projection.venue_fit_delta_raw,
            "venue_history_delta_raw": projection.venue_history_delta_raw,
            "pre_penalty_raw":      projection.pre_penalty_raw,
            "post_penalty_raw":     projection.post_penalty_raw,
            "post_gate_raw":        projection.post_gate_raw,
            "_post_gate_raw":       projection.post_gate_raw,
            "_nsi_raw":             sg_base_comp,
            # Narrative inputs
            "app_true":             app_true,
            "ott_true":             ott_true,
            "ch_adjustment":        ch_adj,
            "true_sg_l20":          true_sg_l20,
            "trait_approach_raw":   round(trait_approach_raw,  4),
            "trait_long_iron_raw":  round(trait_long_iron_raw, 4),
            # Display-trait raws (private; z-scored after loop)
            "_d_approach":          app_true,
            "_d_long_iron":         trait_long_iron_raw,
            "_d_ott":               ott_true,
            "_d_ch":                ch_adj,
            "_d_form":              true_sg_l20,
            "_d_par5":              par5_raw,
            "_d_drv_acc":           decomp["driving_acc_adj"],
            "_d_drv_dist":          decomp["driving_dist_adj"],
            "_d_putt":              perf["putt_true"],
            "_d_composure":         composure_raw,
            # Finalized fields
            "l5_array":             parse_l5_starts(trend["l5_starts"]),
            "std_dev":              round(decomp["std_dev"], 3),
        })

    # ── Canonical finalization boundary ───────────────────────────────────────
    print("[enrich_cards] Finalizing canonical records…")

    # ── Live inputs (the pure finalization boundary receives prepared data) ────
    live_tee_times: dict = {}
    live_r1_sg: dict     = {}

    if live_mode == "r1":
        print("[enrich_cards] Live R1 mode — loading round data…")
        live_tee_times = load_tee_times(
            event_dir / "output" / "round1" / "round2_tee_times.csv")
        live_r1_sg = load_r1_sg(
            event_dir / "output" / "round1" / "round1_player_strokes_gained.csv")
        print(f"  Tee times: {len(live_tee_times)} | R1 SG: {len(live_r1_sg)}")

    ordered_records = finalize_canonical_official_records(
        players_raw,
        live_mode=live_mode,
        live_tee_times=live_tee_times,
        live_r1_sg=live_r1_sg,
    )

    # ── Write outputs (only after identity validation succeeded above) ─────────
    _live_suffix = {"r1": "rd1", "r2": "rd2", "r3": "rd3", "r4": "rd4"}
    file_base = (f"{event_slug}_{_live_suffix[live_mode]}_payload.json"
                 if live_mode else f"{event_slug}_event_payload.json")
    schema_ver = f"3m-live-{live_mode}-v1.0" if live_mode else "3m-enriched-v2.0"

    payload = {
        "schemaVersion": schema_ver,
        "formulaMetadata": {
            key: CANONICAL_FORMULA_METADATA[key]
            for key in (
                "formula_id", "formula_version", "scoring_spec_version",
                "comparable_score_family", "penalty_gate_set_id",
            )
        },
        "generatedAt":   datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event":         event_name,
        "venue":         venue_name,
        "fieldSize":     len(ordered_records),
        "players":       ordered_records,
    }
    json_str = json.dumps(payload, indent=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    deploy_dir.mkdir(parents=True, exist_ok=True)

    deploy_path = deploy_dir / file_base
    output_path = output_dir / file_base

    deploy_path.write_text(json_str, encoding="utf-8")
    output_path.write_text(json_str, encoding="utf-8")

    print(f"[enrich_cards] Done — {len(ordered_records)} players written")
    print(f"  Deploy : {deploy_path}")
    print(f"  Output : {output_path}")

    debuts  = sum(1 for p in ordered_records if p["data_depth"] == "DEBUT")
    bombers = sum(1 for p in ordered_records if "INACCURATE_BOMBER" in (p["anti_pattern_flags"] or []))
    sgdeps  = sum(1 for p in ordered_records if "SHORT_GAME_RELIANT" in (p["anti_pattern_flags"] or []))
    print(f"  DEBUT:{debuts}  Bomber gates:{bombers}  SG-Reliant gates:{sgdeps}")
    print(f"  Top 5: {', '.join(p['player'] for p in ordered_records[:5])}")


if __name__ == "__main__":
    main()
