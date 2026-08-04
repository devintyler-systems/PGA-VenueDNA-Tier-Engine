"""engine/scoring_decomposition.py
Read-only, I/O-free score-decomposition parity layer for the root-level,
event-hardcoded 3M Open enrichment pathway (engine/enrich_cards.py).

Purpose (P1 score-decomposition parity phase): expose exactly what the
current implementation computes -- component weights, coupled-pair totals,
gate multipliers, and per-player raw-score contributions -- as data, without
changing any score, rank, tier, probability, gate, or identity behavior.

This module imports every numeric constant it reports from
engine/enrich_cards.py. It never redefines a weight, threshold, or clamp
value of its own -- there is exactly one source of truth for both
production scoring and this parity/reporting layer. It performs no
filesystem, network, or database I/O.

Canonical doctrine values (standards/02_PGA_VENUEDNA_SCORING_SPEC.md §17.4)
are recorded here only as comparison references for reporting; they do not
alter engine/enrich_cards.py behavior and are not enforced by this module.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich_cards import (  # noqa: E402
    BASE_WEIGHT_6M, BASE_WEIGHT_12M, BASE_WEIGHT_24M,
    DELTA_WEIGHT_6M, DELTA_WEIGHT_12M, DELTA_WEIGHT_24M,
    DELTA_CLAMP,
    VW_APPROACH, VW_LONG_IRON, VW_OTT, VW_CH, VW_FORM,
    PENALTY_BOMBER, PENALTY_SG_DEP,
    combine_raw_score,
)

# ── Canonical doctrine reference values (reporting only; not enforced) ────────
# standards/02_PGA_VENUEDNA_SCORING_SPEC.md §17.4
CANONICAL_COUPLED_TRAIT_CAP = 0.50
CANONICAL_SHORT_GAME_PUTTING_FLOOR = (0.20, 0.25)

# Formula-v2 doctrine markers. These immutable values are diagnostic metadata
# only: they identify the canonical doctrine against which the current 3M
# production pathway is audited; they do not participate in any arithmetic.
CANONICAL_V2_FORMULA_ID = "venuedna_dual_vector_decomposed"
CANONICAL_V2_FORMULA_VERSION = "2.0.0"
CANONICAL_V2_PENALTY_GATE_SET_ID = "venuedna_v2_none"
CANONICAL_V2_ACTIVE_PENALTY_IDS: tuple[str, ...] = ()
CANONICAL_V2_ACTIVE_GATE_IDS: tuple[str, ...] = ()
HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID = "historical_3m_inline_gates"
CANONICAL_V2_CORE_INPUTS: tuple[str, ...] = (
    "SG_Base_Comp",
    "Delta_Fit_Comp",
    "VenueHistoryDeltaRaw",
)
LEGACY_PRODUCTION_NONCORE_ADDENDS: tuple[str, ...] = (
    "trait_approach_raw",
    "trait_long_iron_raw",
    "ott_true",
    "ch_adjustment",
    "true_sg_l20",
)
PRODUCTION_DIVERGENCE_REASON_CODES: tuple[str, ...] = (
    "FORMULA_IDENTITY_MISMATCH",
    "LEGACY_NONCORE_ADDITIVE_COMPONENTS",
    "CANONICAL_THREE_LAYER_DECOMPOSITION_NOT_EXPOSED",
    "HISTORICAL_3M_EVENT_SPECIFIC_IMPLEMENTATION",
    "FORMULA_V2_MIGRATION_PENDING",
    "PENALTY_GATE_SET_ID_MISMATCH",
)

# ── Gate multiplier registry ────────────────────────────────────────────────
# Mirrors engine/enrich_cards.py apply_gates()'s flag -> multiplier mapping.
# The *decision* to fire a gate (threshold comparisons against perf/decomp
# inputs) lives only in apply_gates(); this registry only records which
# multiplier an already-fired flag name corresponds to, so a post-gate raw
# score can be reconstructed from a frozen artifact's stored
# ``anti_pattern_flags`` list without re-deriving the trigger condition.
GATE_MULTIPLIERS: Mapping[str, float] = MappingProxyType({
    "INACCURATE_BOMBER":  PENALTY_BOMBER,
    "SHORT_GAME_RELIANT": PENALTY_SG_DEP,
})

# Canonical production gate-*application* order -- the exact literal
# sequence of `raw *= ...` statements inside engine.enrich_cards.
# apply_gates() (INACCURATE_BOMBER's `raw *= PENALTY_BOMBER` is evaluated
# first, then SHORT_GAME_RELIANT's `raw *= PENALTY_SG_DEP`). This is taken
# directly from apply_gates()'s source order, not derived from
# alphabetical sorting, dict/set iteration, or the order flags happen to
# appear in a caller-supplied list. Only recognized flags actually present
# in a given flag list are applied, always in this fixed sequence.
PRODUCTION_GATE_ORDER: tuple[str, ...] = ("INACCURATE_BOMBER", "SHORT_GAME_RELIANT")


@dataclass(frozen=True)
class ScoringFormulaDescriptor:
    """Immutable snapshot of what engine/enrich_cards.py currently computes."""

    implementation_path: str
    formula_identifier: str
    event_specificity: str
    component_weights: Mapping[str, float]
    coupled_approach_long_iron_weight: float
    canonical_coupled_trait_cap: float
    direct_putting_weight: float
    direct_around_the_green_weight: float
    canonical_short_game_putting_floor: tuple[float, float]
    base_horizon_weights: Mapping[str, float]
    delta_horizon_weights: Mapping[str, float]
    delta_clamp: float
    gate_multipliers: Mapping[str, float]
    source_default_behavior: str
    source_confidence_availability: str
    dg_benchmark_dependency: str
    canonical_conformity_status: str
    canonical_formula_id: str
    canonical_formula_version: str
    canonical_penalty_gate_set_id: str
    canonical_active_penalty_ids: tuple[str, ...]
    canonical_active_gate_ids: tuple[str, ...]
    production_gate_configuration_id: str
    canonical_core_inputs: tuple[str, ...]
    legacy_production_noncore_addends: tuple[str, ...]
    production_divergence_reason_codes: tuple[str, ...]

    def as_dict(self) -> dict:
        """Plain-dict snapshot for reporting; does not mutate this descriptor."""
        return {
            "implementation_path": self.implementation_path,
            "formula_identifier": self.formula_identifier,
            "event_specificity": self.event_specificity,
            "component_weights": dict(self.component_weights),
            "coupled_approach_long_iron_weight": self.coupled_approach_long_iron_weight,
            "canonical_coupled_trait_cap": self.canonical_coupled_trait_cap,
            "direct_putting_weight": self.direct_putting_weight,
            "direct_around_the_green_weight": self.direct_around_the_green_weight,
            "canonical_short_game_putting_floor": list(self.canonical_short_game_putting_floor),
            "base_horizon_weights": dict(self.base_horizon_weights),
            "delta_horizon_weights": dict(self.delta_horizon_weights),
            "delta_clamp": self.delta_clamp,
            "gate_multipliers": dict(self.gate_multipliers),
            "source_default_behavior": self.source_default_behavior,
            "source_confidence_availability": self.source_confidence_availability,
            "dg_benchmark_dependency": self.dg_benchmark_dependency,
            "canonical_conformity_status": self.canonical_conformity_status,
            "canonical_formula_id": self.canonical_formula_id,
            "canonical_formula_version": self.canonical_formula_version,
            "canonical_penalty_gate_set_id": self.canonical_penalty_gate_set_id,
            "canonical_active_penalty_ids": list(self.canonical_active_penalty_ids),
            "canonical_active_gate_ids": list(self.canonical_active_gate_ids),
            "production_gate_configuration_id": self.production_gate_configuration_id,
            "canonical_core_inputs": list(self.canonical_core_inputs),
            "legacy_production_noncore_addends": list(self.legacy_production_noncore_addends),
            "production_divergence_reason_codes": list(self.production_divergence_reason_codes),
        }


FORMULA = ScoringFormulaDescriptor(
    implementation_path="engine/enrich_cards.py",
    # Matches the produced payload's schemaVersion for a pre-event/non-live
    # build. Live-round builds instead emit "3m-live-{round}-v1.0"; the
    # underlying combined-raw formula in combine_raw_score() is identical
    # in both modes -- only downstream wave-adjustment/softmax temperature
    # scaling differs for live builds (see enrich_cards.main(), args.live).
    formula_identifier="3m-enriched-v2.0",
    event_specificity=(
        "Event-hardcoded 2026 3M Open enrichment pathway (SIM_COURSES_FILES, "
        "tpc_twin_cities_CH.csv, TRAIT_DISPLAY_CFG). Its root-level file "
        "location does not make its constants canonical across events; it is "
        "not a reusable canonical engine."
    ),
    component_weights=MappingProxyType({
        "sg_similar_composite": 1.0,
        "approach":             VW_APPROACH,
        "long_iron":            VW_LONG_IRON,
        "ott":                  VW_OTT,
        "course_history":       VW_CH,
        "recent_form":          VW_FORM,
    }),
    coupled_approach_long_iron_weight=VW_APPROACH + VW_LONG_IRON,
    canonical_coupled_trait_cap=CANONICAL_COUPLED_TRAIT_CAP,
    direct_putting_weight=0.0,
    direct_around_the_green_weight=0.0,
    canonical_short_game_putting_floor=CANONICAL_SHORT_GAME_PUTTING_FLOOR,
    base_horizon_weights=MappingProxyType({
        "6m": BASE_WEIGHT_6M, "12m": BASE_WEIGHT_12M, "24m": BASE_WEIGHT_24M,
    }),
    delta_horizon_weights=MappingProxyType({
        "6m": DELTA_WEIGHT_6M, "12m": DELTA_WEIGHT_12M, "24m": DELTA_WEIGHT_24M,
    }),
    delta_clamp=DELTA_CLAMP,
    gate_multipliers=GATE_MULTIPLIERS,
    source_default_behavior=(
        "Missing supplementary source rows receive zero-valued defaults "
        "(_EMPTY_SKILL, _EMPTY_PERF, _EMPTY_DECOMP, _EMPTY_TREND in "
        "enrich_cards.main()). Missing course-history data defaults to the "
        "DEBUT haircut (-0.25) for DEBUT players, or 0.0 for non-debut "
        "players with no CH row. Missing proximity data is imputed to the "
        "field mean (prox_z_raw = 0.0)."
    ),
    source_confidence_availability=(
        "Not implemented. No per-component (NeutralSkill / VenueFitDelta / "
        "VenueHistoryDelta / data-completeness / weather) confidence field is "
        "computed or emitted by this producer. The only dispersion signals "
        "in the payload are the aggregate std_dev, vts_floor, and vts_ceil "
        "fields."
    ),
    dg_benchmark_dependency=(
        "None emitted. load_decomp() reads only driving_acc_adj, "
        "driving_dist_adj, and std_dev from dg_decomposition.csv, used "
        "solely as internal gate/composure inputs -- never exposed as "
        "DG_*_benchmark output fields. Every other dg_decomposition.csv "
        "column (baseline, country_adj, age, age_adj, true_sg_adj, "
        "timing_adj, sg_category_adj, course_history_adj, fit_other_adj, "
        "course_fit_total_adj, final_prediction) is read from the CSV by "
        "csv.DictReader but never consumed by any loader. Unlike Open v3 "
        "(score_open_2026_v3.py compute_vfs_v3(), which adds "
        "dg_cfa*1.5 into VFS), this pathway does not blend any DataGolf "
        "field into vts_final."
    ),
    canonical_conformity_status=(
        "DIVERGENT from standards/02_PGA_VENUEDNA_SCORING_SPEC.md: "
        "production formula identity is 3m-enriched-v2.0 rather than "
        "venuedna_dual_vector_decomposed v2.0.0; it uses historical_3m_inline_gates "
        "rather than canonical venuedna_v2_none; it adds five legacy "
        "noncore components to its raw total, does not expose the canonical "
        "NeutralSkill/VenueFitDelta/VenueHistoryDelta decomposition as its "
        "production formula, is a historical 3M-specific implementation, "
        "and has not migrated to formula v2.0.0."
    ),
    canonical_formula_id=CANONICAL_V2_FORMULA_ID,
    canonical_formula_version=CANONICAL_V2_FORMULA_VERSION,
    canonical_penalty_gate_set_id=CANONICAL_V2_PENALTY_GATE_SET_ID,
    canonical_active_penalty_ids=CANONICAL_V2_ACTIVE_PENALTY_IDS,
    canonical_active_gate_ids=CANONICAL_V2_ACTIVE_GATE_IDS,
    production_gate_configuration_id=HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID,
    canonical_core_inputs=CANONICAL_V2_CORE_INPUTS,
    legacy_production_noncore_addends=LEGACY_PRODUCTION_NONCORE_ADDENDS,
    production_divergence_reason_codes=PRODUCTION_DIVERGENCE_REASON_CODES,
)


def gate_effect_from_flags(flags: list[str] | None) -> dict:
    """Diagnostic gate-effect summary for an already-determined flag list.

    Does not decide whether a gate fires -- that decision is made only by
    engine.enrich_cards.apply_gates() against perf/decomp thresholds. Given
    a flag list (e.g. a frozen artifact's stored ``anti_pattern_flags``),
    reports which recognized flags apply, in production's fixed
    application order (``PRODUCTION_GATE_ORDER``), and each one's
    individual multiplier.

    The returned ``multiplier`` field is a *descriptive aggregate* only --
    the product of every recognized flag's multiplier -- exposed for
    reporting/inspection. It must NEVER be used to calculate a post-gate
    raw total: IEEE-754 float multiplication is not associative, so
    ``pre_total * (m1 * m2)`` can differ from ``(pre_total * m1) * m2`` by
    one ULP. Production applies gates sequentially
    (``engine.enrich_cards.apply_gates()``: ``raw *= PENALTY_BOMBER`` then
    ``raw *= PENALTY_SG_DEP``, each reassigning ``raw`` in place), so any
    diagnostic post-gate total is calculated the same sequential way by
    ``apply_gate_sequence_to_total()`` below, never from this aggregate.
    """
    flags = list(flags or [])
    flag_set = set(flags)
    applied: list[dict] = []
    multiplier = 1.0
    for gate_name in PRODUCTION_GATE_ORDER:
        if gate_name in flag_set:
            m = GATE_MULTIPLIERS[gate_name]
            multiplier *= m
            applied.append({"flag": gate_name, "multiplier": m})
    return {"flags": flags, "applied": applied, "multiplier": multiplier}


def apply_gate_sequence_to_total(pre_total: float, flags: list[str] | None) -> float:
    """Reconstruct a post-gate raw total by applying each recognized flag's
    multiplier to ``pre_total`` one at a time, in
    ``engine.enrich_cards.apply_gates()``'s exact production order and
    exact sequential-reassignment arithmetic (``raw *= PENALTY_BOMBER``
    then ``raw *= PENALTY_SG_DEP``) -- never a single multiplication by a
    precomputed combined multiplier, which can diverge from production by
    one ULP for the combined-gate case. This is the only function that
    should be used to reconstruct a diagnostic post-gate raw total;
    ``gate_effect_from_flags()``'s aggregate ``multiplier`` field is
    descriptive metadata only, not a calculation input.
    """
    flag_set = set(flags or [])
    total = pre_total
    for gate_name in PRODUCTION_GATE_ORDER:
        if gate_name in flag_set:
            total = total * GATE_MULTIPLIERS[gate_name]
    return total


def decompose_player(
    sg_sim_comp: float,
    trait_approach_raw: float,
    trait_long_iron_raw: float,
    ott_true: float,
    ch_adj: float,
    true_sg_l20: float,
    gate_flags: list[str] | None = None,
) -> dict:
    """Full per-player decomposition: pre-gate contributions, pre-gate raw
    total, gate effect, and post-gate raw total.

    Delegates all arithmetic to engine.enrich_cards.combine_raw_score() and
    this module's PRODUCTION_GATE_ORDER/GATE_MULTIPLIERS -- introduces no
    formula of its own, and performs no I/O. ``post_gate_raw_total`` is
    calculated by ``apply_gate_sequence_to_total()`` (sequential, matching
    production bit-for-bit), never by multiplying ``pre_gate_raw_total`` by
    ``gate_effect()``'s descriptive aggregate multiplier.
    """
    pre = combine_raw_score(
        sg_sim_comp, trait_approach_raw, trait_long_iron_raw,
        ott_true, ch_adj, true_sg_l20,
    )
    pre_total = pre["pre_gate_raw_total"]
    contributions = {k: v for k, v in pre.items() if k != "pre_gate_raw_total"}
    gate = gate_effect_from_flags(gate_flags)
    post_total = apply_gate_sequence_to_total(pre_total, gate_flags)
    return {
        "contributions":       contributions,
        "pre_gate_raw_total":  pre_total,
        "gate_effect":         gate,
        "post_gate_raw_total": post_total,
    }
