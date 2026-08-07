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
    require_production_capability,
)
from venuedna_scoring import (  # noqa: E402
    FORMULA_METADATA as CANONICAL_FORMULA_METADATA,
    TOTAL_MEAN_FINITE,
    TOTAL_MEAN_INVALID,
    TOTAL_MEAN_SOURCE_NULL,
    assign_tier as canonical_assign_tier,
    compute_player_projection,
    compute_probability_vectors as canonical_compute_probability_vectors,
    z_score_scale as canonical_z_score_scale,
)
from source_manifest_resolver import (  # noqa: E402
    SourceManifestContext,
    SourceManifestResolution,
    resolve_source_manifest,
)
from venue_config import (  # noqa: E402
    VenueConfig,
    VenueConfigError,
    TPC_TWIN_CITIES,
    load_venue_config,
)

# ── §1  Constants ──────────────────────────────────────────────────────────────

# Documentation/back-compat constants only (Phase 4.4): the actual production
# admission gate is engine/event_context.py's capability policy, called below
# as require_production_capability(context). These two values describe --
# but no longer themselves drive -- that policy's sole PRODUCTION_SUPPORTED
# entry; the narrative copy in build_headline()/build_win_case() and the
# venue trait weights below remain hardcoded to this one event/venue pending
# a separately authorized venue-generalization migration. Do not run this
# producer's remaining logic for another event or venue by editing these
# two constants alone -- that would not change the capability policy table.
SUPPORTED_EVENT_SLUG = "2026_3m_open"
SUPPORTED_VENUE_SLUG = "tpc_twin_cities"

# Historical/illustrative reference only (standards/04 §9.5's illustrative
# 2026_3m_open mapping table). Since the source-manifest migration below,
# main() binds every physical source path through resolve_source_manifest()
# and never reads these dicts for production path construction -- they are
# retained only as a documentation cross-reference for engine/
# scoring_decomposition.py's own historical-pathway commentary.
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

# Venue trait weights, anti-pattern thresholds, and the debut haircut below
# are sourced from engine/venue_config.py's TPC_TWIN_CITIES VenueConfig
# (Phase 4.3) rather than being independent literals -- their values are
# unchanged from the pre-Phase-4.3 hardcoded TPC Twin Cities constants (see
# docs/decisions/2026_08_06_venue_config_contract.md). They remain
# module-level constants under their historical names because
# engine/scoring_decomposition.py imports them directly by name: this
# remains the single source of truth for both this diagnostic/narrative
# pathway and that read-only parity/reporting layer. main() additionally
# resolves a VenueConfig explicitly at runtime (see below) and threads it
# through the functions that consume these values, so these module-level
# constants now describe TPC Twin Cities' default behavior specifically,
# not a venue-generic default.
VW_APPROACH  = TPC_TWIN_CITIES.trait_weights.approach
VW_LONG_IRON = TPC_TWIN_CITIES.trait_weights.long_iron
VW_OTT       = TPC_TWIN_CITIES.trait_weights.ott
VW_CH        = TPC_TWIN_CITIES.trait_weights.ch
VW_FORM      = TPC_TWIN_CITIES.trait_weights.form

# Anti-pattern gate thresholds
BOMB_DIST_THRESH = TPC_TWIN_CITIES.anti_pattern_thresholds.bomb_dist_thresh  # driving_dist_adj above
BOMB_ACC_THRESH  = TPC_TWIN_CITIES.anti_pattern_thresholds.bomb_acc_thresh   # driving_acc_adj below
SG_APP_THRESH    = TPC_TWIN_CITIES.anti_pattern_thresholds.sg_app_thresh     # app_true below = weak approach
SG_SUM_THRESH    = TPC_TWIN_CITIES.anti_pattern_thresholds.sg_sum_thresh     # putt_true + arg_true above = short-game reliant
PENALTY_BOMBER   = TPC_TWIN_CITIES.anti_pattern_thresholds.penalty_bomber
PENALTY_SG_DEP   = TPC_TWIN_CITIES.anti_pattern_thresholds.penalty_sg_dep

# Debut course-history haircut (venue profile §12)
DEBUT_CH_HAIRCUT = TPC_TWIN_CITIES.debut_framework.ch_haircut

# Live-round wave modifier (±VTS points on 0-100 scale)
WAVE_MODIFIER      = 1.5
EARLY_WAVE_CONTEXT = "capitalizing on favorable 7-9 mph morning winds."
LATE_WAVE_CONTEXT  = "facing tougher 11-14 mph afternoon winds."

# std_dev → VTS floor/ceil: 1 stroke ≈ 5 VTS points
STD_VTS_SCALE = 5.0

# Narrative thresholds (all per-round stroke units) -- sourced from
# TPC_TWIN_CITIES.narrative_thresholds; see the block comment above VW_APPROACH.
THRESH_ELITE_APP   = TPC_TWIN_CITIES.narrative_thresholds.elite_app
THRESH_STRONG_APP  = TPC_TWIN_CITIES.narrative_thresholds.strong_app
THRESH_VENUE_FIT   = TPC_TWIN_CITIES.narrative_thresholds.venue_fit    # delta_fit
THRESH_CTRL_POWER  = TPC_TWIN_CITIES.narrative_thresholds.ctrl_power   # ott_true
THRESH_COURSE_PED  = TPC_TWIN_CITIES.narrative_thresholds.course_ped   # ch_adjustment
THRESH_HOT_FORM    = TPC_TWIN_CITIES.narrative_thresholds.hot_form     # true_sg_l20
THRESH_APP_DEFICIT = TPC_TWIN_CITIES.narrative_thresholds.app_deficit
THRESH_LI_GAP      = TPC_TWIN_CITIES.narrative_thresholds.li_gap       # trait_long_iron_raw


def _build_trait_display_cfg(venue_config: VenueConfig) -> list[tuple[str, float]]:
    """(label, venue_weight) pairs in order matching d_keys, for one
    VenueConfig's trait_weights. The five weighted rows mirror
    combine_raw_score()'s five diagnostic addends; the remaining rows are
    display-only (weight 0.00) in every venue, matching current behavior."""
    w = venue_config.trait_weights
    return [
        ("SG: Approach",     w.approach),
        ("App 150-200",      w.long_iron),
        ("Total Driving",    w.ott),
        ("Course History",   w.ch),
        ("Recent Form",      w.form),
        ("Par 5 Scoring",    0.00),
        ("Driving Accuracy", 0.00),
        ("Driving Distance", 0.00),
        ("SG: Putting",      0.00),
        ("Closing Holes",    0.00),
    ]


# Display trait config — (label, venue_weight) in order matching d_keys
TRAIT_DISPLAY_CFG = _build_trait_display_cfg(TPC_TWIN_CITIES)

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


_SOURCE_NULL_TOTAL_MEAN_TOKENS = frozenset(("", "null", "none", "n/a", "nan"))


def parse_total_mean(v: object) -> tuple[float | None, str]:
    """Preserve a source-native null separately from malformed mean input.

    The accepted null tokens are exactly the existing normalized missing-value
    conventions. The caller keeps the raw null as ``None`` and passes its
    state to the canonical VenueFit scorer; no source value is zero-filled.
    """
    token = str(v).strip().lower()
    if token in _SOURCE_NULL_TOTAL_MEAN_TOKENS:
        return None, TOTAL_MEAN_SOURCE_NULL
    try:
        value = float(v)
    except (ValueError, TypeError):
        return None, TOTAL_MEAN_INVALID
    if not math.isfinite(value):
        return None, TOTAL_MEAN_INVALID
    return value, TOTAL_MEAN_FINITE


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
    duplicate is a release blocker. ``payload`` preserves ``rounds``, raw
    nullable ``total_mean``, and the mean's parse state.
    """
    rows: list[SourceRow] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            total_mean, total_mean_state = parse_total_mean(row.get("total_mean"))
            rows.append(SourceRow(
                source_name=name,
                dg_id=None,
                payload={
                    "rounds":     optional_rounds(row.get("rounds_played")),
                    "total_mean": total_mean,
                    "total_mean_state": total_mean_state,
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
    becomes a ``SimilarCourseRow`` (rounds 0 is a valid DEBUT row only with
    a finite mean or a documented source-native null sentinel), a missing
    row stays ``None``. Raw nullness and malformed-cell state remain distinct
    for the canonical scorer to evaluate.
    """
    from venuedna_scoring import SimilarCourseRow

    return {
        h: (
            SimilarCourseRow(
                row["rounds"], row["total_mean"],
                row.get("total_mean_state", TOTAL_MEAN_FINITE),
            )
            if row is not None else None
        )
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


def historical_gate_diagnostics(
    perf: dict, decomp: dict, venue_config: VenueConfig = TPC_TWIN_CITIES,
) -> list[str]:
    """Expose historical anti-pattern labels for narrative diagnostics only.

    This intentionally does not call ``apply_gates`` and never changes a
    canonical score, rank, tier, or probability. Thresholds come from
    ``venue_config.anti_pattern_thresholds`` (default: TPC Twin Cities,
    preserving prior behavior for unchanged call sites).
    """
    t = venue_config.anti_pattern_thresholds
    flags: list[str] = []
    if decomp.get("driving_dist_adj", 0.0) > t.bomb_dist_thresh and decomp.get("driving_acc_adj", 0.0) < t.bomb_acc_thresh:
        flags.append("INACCURATE_BOMBER")
    if perf.get("app_true", 0.0) < t.sg_app_thresh and (perf.get("putt_true", 0.0) + perf.get("arg_true", 0.0)) > t.sg_sum_thresh:
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
    venue_config: VenueConfig = TPC_TWIN_CITIES,
) -> dict:
    """Decomposition of the pre-gate combined-raw VTS input.

    ``pre_gate_raw_total`` is calculated through the same direct,
    left-associated ``a + b + c + d + e + f`` expression -- same operand
    order, same grouping -- as the addends previously inlined in
    ``main()``. It is calculated directly from the six terms below, never
    through the returned dict, ``sum()``, a loop, or any other reduction
    over a (re)ordered collection: those paths insert an implicit leading
    ``0 + …`` that silently normalizes an all-``-0.0`` input's signed-zero
    result to ``+0.0``, which the literal expression does not do. The
    per-component values are exposed in the returned dict for
    diagnostics/reporting only; that dict does not itself compute or alter
    the production total. Trait weights come from ``venue_config.trait_weights``
    (default: TPC Twin Cities, preserving prior behavior -- including the
    same numeric literals -- for unchanged call sites). Consumed by the
    read-only parity layer in ``engine/scoring_decomposition.py`` and by
    tests; never called by ``main()`` or ``finalize_canonical_official_records()``,
    which derive official output only from
    ``engine.venuedna_scoring.compute_player_projection()``. Contains no I/O.
    """
    w = venue_config.trait_weights
    approach_term       = w.approach  * trait_approach_raw
    long_iron_term      = w.long_iron * trait_long_iron_raw
    ott_term            = w.ott       * ott_true
    course_history_term = w.ch        * ch_adj
    recent_form_term    = w.form      * true_sg_l20

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

def apply_gates(
    raw: float, perf: dict, decomp: dict, venue_config: VenueConfig = TPC_TWIN_CITIES,
) -> tuple[float, list[str]]:
    """Multiplicative penalties before z-score. Returns (adjusted_raw, flags).

    Thresholds and penalty multipliers come from
    ``venue_config.anti_pattern_thresholds`` (default: TPC Twin Cities,
    preserving prior behavior for unchanged call sites).
    """
    t = venue_config.anti_pattern_thresholds
    flags: list[str] = []
    dist_adj = decomp.get("driving_dist_adj", 0.0)
    acc_adj  = decomp.get("driving_acc_adj",  0.0)
    app_true = perf.get("app_true", 0.0)
    putt     = perf.get("putt_true", 0.0)
    arg      = perf.get("arg_true",  0.0)

    if dist_adj > t.bomb_dist_thresh and acc_adj < t.bomb_acc_thresh:
        raw *= t.penalty_bomber
        flags.append("INACCURATE_BOMBER")

    if app_true < t.sg_app_thresh and (putt + arg) > t.sg_sum_thresh:
        raw *= t.penalty_sg_dep
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
                        ch_adj: float, true_sg_l20: float,
                        venue_config: VenueConfig = TPC_TWIN_CITIES) -> list[str]:
    n = venue_config.narrative_thresholds
    tags: list[str] = []
    if app_true > n.elite_app:
        tags.append(f"Elite Iron Play (+{app_true:.2f})")
    elif app_true > n.strong_app:
        tags.append(f"Strong Approach Play (+{app_true:.2f})")
    if delta_fit > n.venue_fit:
        tags.append(f"Strong Venue Fit (+{delta_fit:.2f})")
    elif delta_fit > 0.05:
        tags.append(f"Positive Venue Fit (+{delta_fit:.2f})")
    if ott_true > n.ctrl_power:
        tags.append("Controlled Power")
    if ch_adj > n.course_ped:
        tags.append("Proven Course Pedigree")
    if true_sg_l20 > n.hot_form:
        tags.append(f"Red-Hot Form ({true_sg_l20:.2f} SG L20)")
    if not tags:
        tags.append("Field-Average Profile")
    return tags


def build_weakness_tags(app_true: float, trait_long_iron_raw: float,
                        data_depth: str, course_debut: bool,
                        gate_flags: list[str],
                        venue_config: VenueConfig = TPC_TWIN_CITIES) -> list[str]:
    n = venue_config.narrative_thresholds
    tags: list[str] = []
    if app_true < n.app_deficit:
        tags.append("Approach Deficit")
    if "INACCURATE_BOMBER" in gate_flags:
        tags.append("Accuracy Risk")
    if course_debut:
        tags.append("Venue Debut")
    if trait_long_iron_raw < n.li_gap:
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
                   weakness_tags: list[str],
                   venue_config: VenueConfig = TPC_TWIN_CITIES) -> str:
    # Narrative copy below remains TPC Twin Cities-specific prose: the
    # capability gate (engine/event_context.py require_supported_context())
    # only ever runs this producer for tpc_twin_cities in this phase, so
    # generalizing the mechanism/risk/par-5 sentence templates to other
    # venues is out of scope here (see docs/decisions/
    # 2026_08_06_venue_config_contract.md). Only the numeric mechanism
    # thresholds are venue_config-driven, matching the task's "narrative
    # thresholds" scope.
    n = venue_config.narrative_thresholds
    # Primary mechanism
    if app_true > n.elite_app:
        mech = (f"elite approach play (+{app_true:.2f} SG: App). "
                "TPC Twin Cities has crowned 6 of 7 winners since 2019 who ranked "
                "top-10 in approach for the week.")
    elif app_true > n.strong_app:
        mech = (f"above-average approach play (+{app_true:.2f} SG: App) at a venue "
                "where 46% of approaches arrive from 175+ yards.")
    elif delta_fit > n.venue_fit:
        mech = (f"a historically strong fit for similar-course scoring environments "
                f"(delta fit +{delta_fit:.2f}).")
    elif ott_true > n.ctrl_power:
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
    venue_config: VenueConfig = TPC_TWIN_CITIES,
) -> list[dict]:
    """Pure canonical finalization boundary for prepared player records.

    The caller supplies already-resolved player evidence and display-only
    trait scores.  This helper owns every official score, probability, rank,
    tier, and final-record decision; it neither reads external state nor
    mutates the caller-owned prepared records. ``venue_config`` drives only
    the display trait_scores weights and the narrative strength/weakness
    tags and win_case thresholds below (default: TPC Twin Cities, preserving
    prior behavior for unchanged callers) -- it has no effect on
    vts_final/rank/tier/probabilities, which derive solely from
    ``compute_player_projection().post_gate_raw`` upstream in main().
    """
    trait_display_cfg = _build_trait_display_cfg(venue_config)
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
            for index, (label, weight) in enumerate(trait_display_cfg)
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
            record["ch_adjustment"], record["true_sg_l20"], venue_config
        )
        weakness = build_weakness_tags(
            record["app_true"], record["trait_long_iron_raw"],
            record["data_depth"], record["course_debut"], record["gate_flags"],
            venue_config
        )
        record["strength_tags"] = strength
        record["weakness_tags"] = weakness
        record["headline"] = build_headline(strength, weakness)
        record["win_case"] = build_win_case(
            record["player"], record["app_true"], record["delta_fit"] or 0.0,
            record["ott_true"], strength, weakness, venue_config
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

def _resolved_source_path(
    resolution: SourceManifestResolution, input_root: Path, role: str,
) -> Path:
    """Physical path for one logical source role, per the validated
    source_manifest.json resolution -- never a hardcoded legacy filename and
    never constructed from event_slug or venue_slug. When the manifest
    declares no usable source for ``role`` (an optional role's absence is
    already reported as a resolver finding, not necessarily a release
    blocker), this returns a guaranteed-nonexistent placeholder path under
    the event's own input root so the existing loader's own
    ``path.exists()`` check reports the source as missing -- exactly as it
    already does for a literal missing file -- never a fallback to a real
    hardcoded filename.
    """
    resolved = resolution.resolved_sources.get(role)
    if resolved is not None:
        return resolved.resolved_path
    return input_root / f".unresolved_source_manifest_role__{role.replace('.', '_')}"


def main(
    *,
    _context: EventContext | None = None,
    _live_mode: str | None = None,
    _capture_only: bool = False,
) -> list[dict] | None:
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

    ``_capture_only`` is keyword-only, like ``_context``/``_live_mode``, and
    is honored only together with an injected ``_context`` -- passing
    ``_capture_only=True`` without ``_context`` raises ``ValueError`` before
    any event-bound path is touched, so it can never become a generic
    dry-run bypass reachable from the production CLI branch below (argparse
    defines no flag for it, and the CLI branch never sets it). When honored,
    ``main()`` runs the full canonical pipeline -- source-manifest
    resolution, identity resolution, per-player scoring, and finalization --
    exactly as the production path does, then returns the in-memory
    ``ordered_records`` list immediately after finalization instead of
    creating ``output``/``deploy`` directories or writing any payload file.
    """
    if _capture_only and _context is None:
        raise ValueError(
            "_capture_only is honored only together with an injected _context "
            "(the internal test-injection path); it is never valid on the "
            "production CLI path."
        )
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
            require_production_capability(context)
        except EventContextError as exc:
            print(f"[enrich_cards] ERROR — {exc}", file=sys.stderr)
            sys.exit(1)
        live_mode = None

    # ── Venue configuration resolution (Phase 4.3; policy-independence note
    # added Phase 4.4) ────────────────────────────────────────────────────
    #
    # require_production_capability() above -- engine/event_context.py's
    # capability policy -- is the sole authority on which event/venue
    # combination this producer may run for in production; every CLI-invoked
    # run reaches this point only after resolving PRODUCTION_SUPPORTED for
    # (context.event_slug, context.venue_slug), which today matches exactly
    # one pair: event_slug=SUPPORTED_EVENT_SLUG, venue_slug=SUPPORTED_VENUE_SLUG
    # ("tpc_twin_cities"), a registered VenueConfig. The internal
    # test-injection seam (the `_context` branch above) intentionally
    # bypasses that gate and may inject an arbitrary placeholder venue_slug
    # unrelated to any registered VenueConfig (see tests/test_enrich_cards.py's
    # SyntheticEvent/_make_context default of "synthetic_test_venue"), so an
    # unregistered venue_slug here falls back to TPC_TWIN_CITIES -- the same
    # constants every caller (including that test seam) already used before
    # this venue-config layer existed. This fallback affects only the
    # diagnostic/narrative trait_scores, anti_pattern_flags, and
    # strength/weakness-tag values written to a test-seam-produced payload
    # under tmp_path; it can never grant CAPABILITY_PRODUCTION_SUPPORTED --
    # resolve_capability()/require_production_capability() run only in the
    # non-`_context` CLI branch above, are computed independently of this
    # fallback, and are never consulted or re-run down here. A registered
    # venue whose (event_slug, venue_slug) pair is not itself
    # PRODUCTION_SUPPORTED (Sedgefield Country Club today) resolves its own
    # real VenueConfig here -- load_venue_config("sedgefield_country_club")
    # succeeds and returns SEDGEFIELD_COUNTRY_CLUB directly, never hitting
    # this except branch -- so this fallback can never substitute TPC's
    # configuration for a different, validly-registered venue's own values
    # (tests/test_enrich_cards.py proves this end to end).
    try:
        venue_config = load_venue_config(context.venue_slug)
    except VenueConfigError:
        venue_config = TPC_TWIN_CITIES

    # ── Source-manifest resolution (standards/04 §9) ────────────────────────
    #
    # Applies to both the production CLI path and the internal test-
    # injection seam above, since both set `context` before reaching here.
    # After EventContext validation and the capability gate succeed, a
    # validated source_manifest.json at the event's own input root is the
    # sole, authoritative physical-path lookup mechanism for every one of
    # the thirteen logical source roles -- no config pointer, no CLI flag,
    # no fallback location, and no hardcoded-filename rescue. A missing
    # manifest, unreadable manifest, invalid JSON, non-object JSON root, or
    # any resolver blocker fails release before any source file is opened,
    # before identity resolution, before scoring, and before output/deploy
    # directory creation or any write.
    manifest_path = context.event_root / "input" / "source_manifest.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[enrich_cards] ERROR — source_manifest.json could not be read "
              f"at {manifest_path}: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        manifest_obj = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        print(f"[enrich_cards] ERROR — source_manifest.json is not valid JSON "
              f"at {manifest_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    manifest_context = SourceManifestContext(
        event_slug=context.event_slug,
        venue_slug=context.venue_slug,
        event_root=context.event_root,
        repo_root=_ROOT,
    )
    manifest_resolution = resolve_source_manifest(manifest_obj, context=manifest_context)
    if manifest_resolution.is_release_blocked:
        print("[enrich_cards] SOURCE MANIFEST RELEASE BLOCKED", file=sys.stderr)
        for finding in manifest_resolution.blockers:
            print(f"[enrich_cards] BLOCKER [{finding.code}] {finding.role or '-'}: "
                  f"{finding.message}", file=sys.stderr)
        sys.exit(1)
    for finding in manifest_resolution.warnings:
        print(f"[enrich_cards] WARNING [{finding.code}] {finding.role or '-'}: "
              f"{finding.message}", file=sys.stderr)

    event_slug = context.event_slug
    event_name = context.event_name
    venue_name = context.venue_name
    event_dir  = context.event_root

    input_dir  = event_dir / "input"
    output_dir = event_dir / "output"
    deploy_dir = event_dir / "deploy" / "data"

    # ── Load all source files ──────────────────────────────────────────────────
    print("[enrich_cards] Loading source files…")

    field_rows = load_field_rows(_resolved_source_path(manifest_resolution, input_dir, "field"))
    if not field_rows:
        print("[enrich_cards] ERROR — field roster is empty or unresolved", file=sys.stderr)
        sys.exit(1)

    all_sg = {
        h: load_sg_csv(_resolved_source_path(manifest_resolution, input_dir, f"neutral_skill.sg_total.{h}"))
        for h in ("6m", "12m", "24m")
    }
    sim_sg = {
        h: load_sg_csv(_resolved_source_path(manifest_resolution, input_dir, f"venue_fit.similar_sg.{h}"))
        for h in ("6m", "12m", "24m")
    }

    app_skill_data = load_app_skill(_resolved_source_path(
        manifest_resolution, input_dir, "traits.approach.sg_per_shot.12m"))
    app_prox_data  = load_app_prox(_resolved_source_path(
        manifest_resolution, input_dir, "traits.approach.proximity.12m"))
    perf_data      = load_performance(_resolved_source_path(
        manifest_resolution, input_dir, "performance.sg_categories.season"))
    decomp_data    = load_decomp(_resolved_source_path(
        manifest_resolution, input_dir, "benchmark.decomposition"))
    ch_data        = load_ch(_resolved_source_path(
        manifest_resolution, input_dir, "venue_history"))
    trending_data  = load_trending(_resolved_source_path(
        manifest_resolution, input_dir, "recent_form.trending"))

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
        gate_flags = historical_gate_diagnostics(perf, decomp, venue_config)

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
        venue_config=venue_config,
        live_r1_sg=live_r1_sg,
    )

    # ── Write outputs (only after identity validation succeeded above) ─────────
    if _capture_only:
        return ordered_records

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
