"""engine/venuedna_scoring.py
Pure, I/O-free implementation of the canonical VenueDNA dual-vector
decomposed scoring formula (standards/02_PGA_VENUEDNA_SCORING_SPEC.md
§7-§12).

formula_id: venuedna_dual_vector_decomposed
formula_version: 2.0.0
comparable_score_family: dual_vector_sg_per_round_v2
penalty_gate_set_id: venuedna_v2_none

This module performs no file, network, database, or event-path I/O. It has
no dependency on engine/enrich_cards.py or engine/identity_resolver.py, no
DataGolf benchmark input, and no venue- or event-specific data. It is the
reusable canonical scoring boundary for a root-producer migration.

The historical, event-hardcoded 3M Open pathway in engine/enrich_cards.py
(formula_identifier "3m-enriched-v2.0", gate configuration
"historical_3m_inline_gates") remains a separately identified historical
implementation. This module does not read, call, or alter it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional

# ── Canonical formula identity (doctrine-locked) ────────────────────────────
FORMULA_ID = "venuedna_dual_vector_decomposed"
FORMULA_VERSION = "2.0.0"
SCORING_SPEC_VERSION = "2.0-draft"
COMPARABLE_SCORE_FAMILY = "dual_vector_sg_per_round_v2"
PENALTY_GATE_SET_ID = "venuedna_v2_none"

# The exact, and only, three named layers summed into PrePenaltyRaw.
CORE_INPUTS: tuple[str, ...] = ("SG_Base_Comp", "Delta_Fit_Comp", "VenueHistoryDeltaRaw")

# Historical engine/enrich_cards.py addends. Never accepted as parameters by
# this module -- see the doctrine validator's V2IMPL_COMPONENT_OVERLAP check.
EXCLUDED_LEGACY_NONCORE_ADDENDS: tuple[str, ...] = (
    "trait_approach_raw", "trait_long_iron_raw", "ott_true", "ch_adjustment", "true_sg_l20",
)

# penalty_gate_set_id venuedna_v2_none: no penalty or gate is active.
ACTIVE_PENALTY_IDS: tuple[str, ...] = ()
ACTIVE_GATE_IDS: tuple[str, ...] = ()

FORMULA_METADATA: Mapping[str, object] = MappingProxyType({
    "formula_id": FORMULA_ID,
    "formula_version": FORMULA_VERSION,
    "scoring_spec_version": SCORING_SPEC_VERSION,
    "comparable_score_family": COMPARABLE_SCORE_FAMILY,
    "penalty_gate_set_id": PENALTY_GATE_SET_ID,
    "core_inputs": CORE_INPUTS,
    "excluded_legacy_noncore_addends": EXCLUDED_LEGACY_NONCORE_ADDENDS,
})

# ── Composite blending weights (standards/02 §6) ────────────────────────────
BASE_WEIGHT_6M, BASE_WEIGHT_12M, BASE_WEIGHT_24M = 0.20, 0.30, 0.50
DELTA_WEIGHT_6M, DELTA_WEIGHT_12M, DELTA_WEIGHT_24M = 0.50, 0.30, 0.20
DELTA_CLAMP = 0.50
HORIZONS: tuple[str, ...] = ("6m", "12m", "24m")

_BASE_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {"6m": BASE_WEIGHT_6M, "12m": BASE_WEIGHT_12M, "24m": BASE_WEIGHT_24M}
)
_DELTA_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {"6m": DELTA_WEIGHT_6M, "12m": DELTA_WEIGHT_12M, "24m": DELTA_WEIGHT_24M}
)

# ── Z-score normalization (standards/02 §8) ─────────────────────────────────
ZNORM_MEAN, ZNORM_STD = 50.0, 15.0

# ── Tempered softmax (standards/02 §9) ──────────────────────────────────────
SOFTMAX_TEMPERATURES: Mapping[str, float] = MappingProxyType(
    {"win": 3.5, "top5": 5.0, "top10": 7.0, "top20": 10.0}
)
SOFTMAX_POSITIONS: Mapping[str, int] = MappingProxyType(
    {"win": 1, "top5": 5, "top10": 10, "top20": 20}
)
SOFTMAX_CAP = 99.9

# ── Cut probability (standards/02 §10) ──────────────────────────────────────
MAKECUT_MIN, MAKECUT_MAX = 20.0, 98.0
MAKECUT_TOP20_MULT, MAKECUT_OFFSET = 1.25, 10.0

# ── Tier assignment (standards/02 §11) ──────────────────────────────────────
TIER_BOUNDARIES: tuple[tuple[int, str], ...] = ((5, "T1"), (12, "T2"), (25, "T3"), (40, "T4"))
TIER_DEFAULT = "T5"

CONFIDENCE_SOURCES: tuple[str, ...] = (
    "neutral_skill", "venue_fit", "venue_history", "penalty_gate",
    "data_completeness", "conditions",
)


@dataclass(frozen=True)
class SimilarCourseRow:
    """A valid, present similar-course source row for one horizon.
    ``rounds_played == 0`` is the legitimate DEBUT state, not missing data.
    A horizon with no row at all is represented by ``None``, never by this
    type with a fabricated zero.
    """

    rounds_played: Optional[int]
    total_mean: Optional[float]


@dataclass(frozen=True)
class NeutralSkillResult:
    value: Optional[float]
    status: str  # "SCORED" | "UNSCORED"
    valid_horizons: tuple[str, ...]
    confidence: str  # "HIGH" | "THIN"


@dataclass(frozen=True)
class VenueFitResult:
    value: Optional[float]
    data_depth: str  # "FULL" | "DEBUT" | "MISSING"
    confidence: str  # "HIGH" | "THIN"
    computable_horizons: tuple[str, ...]


@dataclass(frozen=True)
class VenueHistoryResult:
    value: float
    confidence: str  # "HIGH" | "THIN"


@dataclass(frozen=True)
class VenueHistoryEvidence:
    """Observed venue-history sample metadata, kept separate from raw score."""

    relevant_starts: Optional[int]


@dataclass(frozen=True)
class PlayerProjection:
    neutral_skill_raw: Optional[float]
    venue_fit_delta_raw: Optional[float]
    venue_history_delta_raw: float
    penalties_applied: tuple[str, ...]
    gates_applied: tuple[str, ...]
    pre_penalty_raw: Optional[float]
    post_penalty_raw: Optional[float]
    post_gate_raw: Optional[float]
    confidence_by_source: Mapping[str, str]
    status: str  # "SCORED" | "UNSCORED"
    data_depth: str
    formula_metadata: Mapping[str, object]


def compute_neutral_skill(horizons: Mapping[str, Optional[float]]) -> NeutralSkillResult:
    """NeutralSkillRaw = SG_Base_Comp. Missing horizons are omitted and the
    remaining horizon weights renormalize; fewer than two valid horizons
    yields UNSCORED. A present ``0.0`` is a valid measurement, never treated
    as missing.
    """
    valid = tuple(h for h in HORIZONS if horizons.get(h) is not None)
    if len(valid) < 2:
        return NeutralSkillResult(value=None, status="UNSCORED", valid_horizons=valid, confidence="THIN")

    weight_sum = sum(_BASE_WEIGHTS[h] for h in valid)
    value = sum(_BASE_WEIGHTS[h] * horizons[h] for h in valid) / weight_sum
    confidence = "HIGH" if len(valid) == 3 else "THIN"
    return NeutralSkillResult(value=value, status="SCORED", valid_horizons=valid, confidence=confidence)


def compute_venue_fit(
    similar_course_rows: Mapping[str, Optional[SimilarCourseRow]],
    base_horizons: Mapping[str, Optional[float]],
) -> VenueFitResult:
    """VenueFitDeltaRaw = Delta_Fit_Comp.

    Formula v2 has a fixed three-horizon VenueFit vector.  Unlike
    NeutralSkill, doctrine does *not* authorize renormalizing the delta
    weights when a horizon is incomplete: every horizon therefore has to be
    present and valid before this component is computable.  A present row
    reporting zero rounds is a valid DEBUT observation; its total mean is
    intentionally irrelevant because the regression weight is zero.
    """
    rows = tuple(similar_course_rows.get(h) for h in HORIZONS)
    bases = tuple(base_horizons.get(h) for h in HORIZONS)
    all_zero_rounds = all(row is not None and row.rounds_played == 0 for row in rows)

    if all_zero_rounds and all(base is not None for base in bases):
        return VenueFitResult(
            value=0.0,
            data_depth="DEBUT",
            confidence="THIN",
            computable_horizons=HORIZONS,
        )

    computable = tuple(
        h for h in HORIZONS
        if (
            similar_course_rows.get(h) is not None
            and similar_course_rows[h].rounds_played is not None
            and similar_course_rows[h].rounds_played >= 0
            and similar_course_rows[h].total_mean is not None
            and base_horizons.get(h) is not None
        )
    )
    if computable != HORIZONS:
        return VenueFitResult(
            value=None,
            data_depth="MISSING",
            confidence="THIN",
            computable_horizons=computable,
        )

    raw_sum = 0.0
    for h in HORIZONS:
        row = similar_course_rows[h]
        base = base_horizons[h]
        assert row is not None and row.rounds_played is not None and row.total_mean is not None
        assert base is not None
        w = min(1.0, row.rounds_played / 20.0)
        sg_sim_reg = w * row.total_mean + (1 - w) * base
        raw_sum += _DELTA_WEIGHTS[h] * (sg_sim_reg - base)
    value = max(-DELTA_CLAMP, min(DELTA_CLAMP, raw_sum))
    return VenueFitResult(value=value, data_depth="FULL", confidence="HIGH", computable_horizons=HORIZONS)


def compute_venue_history(evidence: Optional[VenueHistoryEvidence]) -> VenueHistoryResult:
    """VenueHistoryDeltaRaw is always the explicit canonical neutral ``0.0``
    under formula v2.0.0 (penalty_gate_set_id venuedna_v2_none; no bounded
    transform is approved). This is not zero-filling missing raw-source
    data -- it is the doctrine-declared neutral contribution. Raw-source
    relevant-start count affects only venue_history confidence, never the
    value.  The governing threshold is eight relevant starts; a mere boolean
    "evidence exists" cannot establish that threshold.
    """
    relevant_starts = evidence.relevant_starts if evidence is not None else None
    confidence = "HIGH" if isinstance(relevant_starts, int) and relevant_starts >= 8 else "THIN"
    return VenueHistoryResult(value=0.0, confidence=confidence)


def _data_completeness_confidence(
    neutral_skill: NeutralSkillResult, venue_fit: VenueFitResult, venue_history: VenueHistoryResult
) -> str:
    if "THIN" in (neutral_skill.confidence, venue_fit.confidence, venue_history.confidence):
        return "THIN"
    return "HIGH"


def compute_player_projection(
    neutral_skill_horizons: Mapping[str, Optional[float]],
    similar_course_rows: Mapping[str, Optional[SimilarCourseRow]],
    *,
    venue_history_evidence: Optional[VenueHistoryEvidence] = None,
    conditions_confidence: str = "HIGH",
) -> PlayerProjection:
    """Full canonical per-player decomposition. No parameter accepts any of
    the five legacy noncore addends or a DataGolf benchmark field -- they
    cannot be threaded into this formula's output.
    """
    neutral_skill = compute_neutral_skill(neutral_skill_horizons)
    venue_fit = compute_venue_fit(similar_course_rows, neutral_skill_horizons)
    venue_history = compute_venue_history(venue_history_evidence)

    if neutral_skill.status == "UNSCORED" or venue_fit.value is None:
        pre_penalty = post_penalty = post_gate = None
        status = "UNSCORED"
    else:
        pre_penalty = neutral_skill.value + venue_fit.value + venue_history.value
        post_penalty = pre_penalty  # venuedna_v2_none: identity transformation
        post_gate = post_penalty  # venuedna_v2_none: identity transformation
        status = "SCORED"

    confidence_by_source: Mapping[str, str] = MappingProxyType({
        "neutral_skill": neutral_skill.confidence,
        "venue_fit": venue_fit.confidence,
        "venue_history": venue_history.confidence,
        "penalty_gate": "HIGH",  # venuedna_v2_none: no active penalty or gate requires evidence
        "data_completeness": _data_completeness_confidence(neutral_skill, venue_fit, venue_history),
        "conditions": conditions_confidence,
    })

    return PlayerProjection(
        neutral_skill_raw=neutral_skill.value,
        venue_fit_delta_raw=venue_fit.value,
        venue_history_delta_raw=venue_history.value,
        penalties_applied=ACTIVE_PENALTY_IDS,
        gates_applied=ACTIVE_GATE_IDS,
        pre_penalty_raw=pre_penalty,
        post_penalty_raw=post_penalty,
        post_gate_raw=post_gate,
        confidence_by_source=confidence_by_source,
        status=status,
        data_depth=venue_fit.data_depth,
        formula_metadata=FORMULA_METADATA,
    )


# ── Field-level normalization (standards/02 §8) ─────────────────────────────

def z_score_scale(values: list[float]) -> list[float]:
    if not values:
        return []
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd = math.sqrt(var) if var > 0 else 1.0
    return [max(0.0, min(100.0, ZNORM_MEAN + ZNORM_STD * (v - mu) / sd)) for v in values]


# ── Probability vectors (standards/02 §9-§10) ───────────────────────────────

def tempered_softmax(scores: list[float], temperature: float, n_positions: int) -> list[float]:
    max_s = max(scores)
    exps = [math.exp((s - max_s) / temperature) for s in scores]
    total = sum(exps)
    return [min(SOFTMAX_CAP, (e / total) * n_positions * 100) for e in exps]


def enforce_monotonicity(p: dict) -> None:
    p["top5Pct"] = max(p["top5Pct"], p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])


def make_cut_prob(top20: float) -> float:
    return min(MAKECUT_MAX, max(MAKECUT_MIN, top20 * MAKECUT_TOP20_MULT + MAKECUT_OFFSET))


def compute_probability_vectors(post_gate_raw_values: list[float]) -> list[dict]:
    if not post_gate_raw_values:
        return []
    vectors = {
        outcome: tempered_softmax(
            post_gate_raw_values, SOFTMAX_TEMPERATURES[outcome], SOFTMAX_POSITIONS[outcome]
        )
        for outcome in ("win", "top5", "top10", "top20")
    }
    results: list[dict] = []
    for i in range(len(post_gate_raw_values)):
        p = {
            "winPct": vectors["win"][i],
            "top5Pct": vectors["top5"][i],
            "top10Pct": vectors["top10"][i],
            "top20Pct": vectors["top20"][i],
        }
        enforce_monotonicity(p)
        p["makeCutPct"] = make_cut_prob(p["top20Pct"])
        p["missCutPct"] = 100.0 - p["makeCutPct"]
        results.append(p)
    return results


# ── Rank and tier (standards/02 §11) ────────────────────────────────────────

def rank_players(post_gate_raw_values: Mapping[str, float]) -> dict[str, int]:
    """Descending sort by ``post_gate_raw_values``; rank 1 is the highest."""
    ordered = sorted(post_gate_raw_values.items(), key=lambda kv: kv[1], reverse=True)
    return {key: i + 1 for i, (key, _) in enumerate(ordered)}


def assign_tier(rank: int) -> str:
    for boundary, tier in TIER_BOUNDARIES:
        if rank <= boundary:
            return tier
    return TIER_DEFAULT
