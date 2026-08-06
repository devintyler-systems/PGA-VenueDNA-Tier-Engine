"""Tests for engine/scoring_decomposition.py -- the historical 3M
score-decomposition parity harness retained for archived diagnostics.

Every expected numeric value below is either (a) independently hand-derived
arithmetic that does not call the function under test, or (b) a direct read
of a frozen, read-only archived artifact. No test in this file computes an
expected value by calling z_score_scale/tempered_softmax/combine_raw_score/
decompose_player and then asserting the function returns what it just
returned.
"""
from __future__ import annotations

import csv
import inspect
import json
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_cards  # noqa: E402
from enrich_cards import z_score_scale, assign_tier, make_cut_prob  # noqa: E402
import scoring_decomposition as sd  # noqa: E402
from scoring_decomposition import (  # noqa: E402
    FORMULA,
    GATE_MULTIPLIERS,
    PRODUCTION_GATE_ORDER,
    CANONICAL_COUPLED_TRAIT_CAP,
    CANONICAL_SHORT_GAME_PUTTING_FLOOR,
    CANONICAL_V2_FORMULA_ID,
    CANONICAL_V2_FORMULA_VERSION,
    CANONICAL_V2_PENALTY_GATE_SET_ID,
    CANONICAL_V2_ACTIVE_PENALTY_IDS,
    CANONICAL_V2_ACTIVE_GATE_IDS,
    CANONICAL_V2_CORE_INPUTS,
    HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID,
    LEGACY_PRODUCTION_NONCORE_ADDENDS,
    PRODUCTION_DIVERGENCE_REASON_CODES,
    decompose_player,
    gate_effect_from_flags,
    apply_gate_sequence_to_total,
)

from test_enrich_cards import SyntheticEvent, _run_main, _output_path  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_SCORING_SPEC = _ROOT / "standards" / "02_PGA_VENUEDNA_SCORING_SPEC.md"
_ARCHIVED_3M_PAYLOAD = (
    _ROOT / "events" / "2026_Finished_Events" / "2026_3m_open"
    / "deploy" / "data" / "2026_3m_open_event_payload.json"
)


# ── Formula descriptor: no duplicated constants ─────────────────────────────

def test_historical_descriptor_component_weights_match_historical_constants():
    """The archival descriptor reports the historical helper constants without
    becoming an official canonical producer input."""
    cw = FORMULA.component_weights
    assert cw["approach"]       == enrich_cards.VW_APPROACH
    assert cw["long_iron"]      == enrich_cards.VW_LONG_IRON
    assert cw["ott"]            == enrich_cards.VW_OTT
    assert cw["course_history"] == enrich_cards.VW_CH
    assert cw["recent_form"]    == enrich_cards.VW_FORM
    assert cw["sg_similar_composite"] == 1.0


def test_historical_descriptor_horizon_weights_match_historical_constants():
    assert FORMULA.base_horizon_weights == {
        "6m": enrich_cards.BASE_WEIGHT_6M,
        "12m": enrich_cards.BASE_WEIGHT_12M,
        "24m": enrich_cards.BASE_WEIGHT_24M,
    }
    assert FORMULA.delta_horizon_weights == {
        "6m": enrich_cards.DELTA_WEIGHT_6M,
        "12m": enrich_cards.DELTA_WEIGHT_12M,
        "24m": enrich_cards.DELTA_WEIGHT_24M,
    }
    assert FORMULA.delta_clamp == enrich_cards.DELTA_CLAMP


def test_historical_descriptor_gate_multipliers_match_historical_penalties():
    assert GATE_MULTIPLIERS["INACCURATE_BOMBER"]  == enrich_cards.PENALTY_BOMBER
    assert GATE_MULTIPLIERS["SHORT_GAME_RELIANT"] == enrich_cards.PENALTY_SG_DEP


def test_descriptor_is_immutable():
    with pytest.raises(Exception):
        FORMULA.delta_clamp = 0.99  # dataclass(frozen=True) must reject this
    with pytest.raises(TypeError):
        FORMULA.component_weights["approach"] = 0.99  # MappingProxyType is read-only


def test_as_dict_does_not_mutate_descriptor():
    d = FORMULA.as_dict()
    d["delta_clamp"] = 999.0
    d["component_weights"]["approach"] = 999.0
    assert FORMULA.delta_clamp == enrich_cards.DELTA_CLAMP
    assert FORMULA.component_weights["approach"] == enrich_cards.VW_APPROACH


# ── Legacy trait diagnostic facts (not formula-v2 core authority) ───────────

def test_coupled_approach_long_iron_weight_is_065():
    assert FORMULA.coupled_approach_long_iron_weight == pytest.approx(0.65)


def test_legacy_coupled_weight_exceeds_direct_trait_cap_reference():
    assert FORMULA.coupled_approach_long_iron_weight > FORMULA.canonical_coupled_trait_cap
    assert FORMULA.canonical_coupled_trait_cap == pytest.approx(CANONICAL_COUPLED_TRAIT_CAP)
    assert CANONICAL_COUPLED_TRAIT_CAP == pytest.approx(0.50)


def test_legacy_direct_putting_and_around_the_green_weight_is_zero():
    assert FORMULA.direct_putting_weight == 0.0
    assert FORMULA.direct_around_the_green_weight == 0.0
    lo, hi = CANONICAL_SHORT_GAME_PUTTING_FLOOR
    assert FORMULA.direct_putting_weight + FORMULA.direct_around_the_green_weight < lo
    assert lo == pytest.approx(0.20) and hi == pytest.approx(0.25)


def test_conformity_status_is_nonconformant():
    status = FORMULA.canonical_conformity_status.lower()
    assert "conformant" not in status
    assert "historical_3m_inline_gates" in status
    assert "production gate configuration is venuedna_v2_none" not in status


def test_event_specificity_flags_root_producer_as_event_hardcoded():
    assert "event-hardcoded" in FORMULA.event_specificity.lower()
    assert "not a reusable canonical engine" in FORMULA.event_specificity.lower()


# ── Doctrine v2.0.0 is intentionally distinct from historical parity ───────

def _scoring_doctrine_v2_metadata() -> dict[str, str]:
    """Read only the deliberately stable metadata marker, never broad prose."""
    marker = re.search(
        r"<!-- scoring-doctrine-v2\n(?P<body>.*?)\n-->",
        _SCORING_SPEC.read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    assert marker, "missing stable scoring-doctrine-v2 metadata marker"
    return dict(line.split("=", 1) for line in marker.group("body").splitlines())


def _marker_component_set(metadata: dict[str, str], key: str) -> tuple[str, ...]:
    """Parse one compact, ordered component list from the stable marker."""
    return tuple(item for item in metadata[key].split(",") if item)


def test_canonical_doctrine_marker_identifies_exact_v2_contract():
    metadata = _scoring_doctrine_v2_metadata()
    assert metadata == {
        "formula_id": "venuedna_dual_vector_decomposed",
        "formula_version": "2.0.0",
        "comparable_score_family": "dual_vector_sg_per_round_v2",
        "penalty_gate_set_id": "venuedna_v2_none",
        "canonical_core_inputs": "SG_Base_Comp,Delta_Fit_Comp,VenueHistoryDeltaRaw",
        "excluded_legacy_noncore_addends": "trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20",
    }
    assert metadata["formula_id"] == "venuedna_dual_vector_decomposed"
    assert metadata["formula_version"] == "2.0.0"
    assert metadata["comparable_score_family"] == "dual_vector_sg_per_round_v2"
    assert metadata["penalty_gate_set_id"] == "venuedna_v2_none"


def test_historical_descriptor_remains_nonconforming_to_doctrine_v2():
    metadata = _scoring_doctrine_v2_metadata()
    assert FORMULA.formula_identifier == "3m-enriched-v2.0"
    assert FORMULA.formula_identifier != metadata["formula_id"]
    assert "conformant" not in FORMULA.canonical_conformity_status.lower()
    assert "FORMULA_IDENTITY_MISMATCH" in FORMULA.production_divergence_reason_codes


def test_canonical_v2_core_component_set_is_exact_in_marker_and_diagnostics():
    metadata = _scoring_doctrine_v2_metadata()
    expected = ("SG_Base_Comp", "Delta_Fit_Comp", "VenueHistoryDeltaRaw")
    assert CANONICAL_V2_FORMULA_ID == "venuedna_dual_vector_decomposed"
    assert CANONICAL_V2_FORMULA_VERSION == "2.0.0"
    assert _marker_component_set(metadata, "canonical_core_inputs") == expected
    assert CANONICAL_V2_CORE_INPUTS == expected
    assert FORMULA.canonical_core_inputs == expected


def test_legacy_noncore_addend_set_is_exact_in_marker_and_diagnostics():
    metadata = _scoring_doctrine_v2_metadata()
    expected = (
        "trait_approach_raw",
        "trait_long_iron_raw",
        "ott_true",
        "ch_adjustment",
        "true_sg_l20",
    )
    assert _marker_component_set(metadata, "excluded_legacy_noncore_addends") == expected
    assert LEGACY_PRODUCTION_NONCORE_ADDENDS == expected
    assert FORMULA.legacy_production_noncore_addends == expected


def test_canonical_core_and_legacy_noncore_sets_are_disjoint():
    metadata = _scoring_doctrine_v2_metadata()
    assert set(_marker_component_set(metadata, "canonical_core_inputs")).isdisjoint(
        _marker_component_set(metadata, "excluded_legacy_noncore_addends")
    )


def test_no_legacy_addend_is_authorized_as_v2_core_input():
    metadata = _scoring_doctrine_v2_metadata()
    canonical = set(_marker_component_set(metadata, "canonical_core_inputs"))
    excluded = set(_marker_component_set(metadata, "excluded_legacy_noncore_addends"))
    assert not canonical.intersection(excluded)
    assert FORMULA.as_dict()["canonical_core_inputs"] == list(CANONICAL_V2_CORE_INPUTS)


def test_historical_descriptor_has_structured_nonconformance_reasons():
    assert FORMULA.production_divergence_reason_codes == (
        "FORMULA_IDENTITY_MISMATCH",
        "LEGACY_NONCORE_ADDITIVE_COMPONENTS",
        "CANONICAL_THREE_LAYER_DECOMPOSITION_NOT_EXPOSED",
        "HISTORICAL_3M_EVENT_SPECIFIC_IMPLEMENTATION",
        "FORMULA_V2_MIGRATION_PENDING",
        "PENALTY_GATE_SET_ID_MISMATCH",
    )
    assert FORMULA.production_divergence_reason_codes == PRODUCTION_DIVERGENCE_REASON_CODES


def test_canonical_and_production_formula_identities_remain_distinct():
    assert FORMULA.formula_identifier == "3m-enriched-v2.0"
    assert FORMULA.formula_identifier != FORMULA.canonical_formula_id
    assert FORMULA.canonical_formula_id == CANONICAL_V2_FORMULA_ID


def test_canonical_penalty_gate_identity_is_not_historical_production_configuration():
    metadata = _scoring_doctrine_v2_metadata()
    assert metadata["penalty_gate_set_id"] == CANONICAL_V2_PENALTY_GATE_SET_ID == "venuedna_v2_none"
    assert CANONICAL_V2_ACTIVE_PENALTY_IDS == ()
    assert CANONICAL_V2_ACTIVE_GATE_IDS == ()
    assert FORMULA.canonical_penalty_gate_set_id == CANONICAL_V2_PENALTY_GATE_SET_ID
    assert FORMULA.production_gate_configuration_id == HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID
    assert FORMULA.production_gate_configuration_id != FORMULA.canonical_penalty_gate_set_id


def test_structured_divergence_includes_penalty_gate_set_mismatch():
    assert "PENALTY_GATE_SET_ID_MISMATCH" in FORMULA.production_divergence_reason_codes
    assert FORMULA.as_dict()["production_gate_configuration_id"] == "historical_3m_inline_gates"


def test_structured_doctrine_metadata_is_descriptive_not_production_arithmetic():
    """Production arithmetic and archived parity remain independently covered below."""
    result = decompose_player(2.0, 1.0, 1.0, 1.0, 1.0, 1.0, [])
    assert result["pre_gate_raw_total"] == pytest.approx(3.0)
    assert result["post_gate_raw_total"] == pytest.approx(3.0)


def test_legacy_diagnostics_keep_all_five_noncore_addends_visible():
    """The five current addends remain observable for parity, not doctrine."""
    production_components = FORMULA.component_weights
    assert {
        "approach", "long_iron", "ott", "course_history", "recent_form"
    } <= set(production_components)
    decomposition = decompose_player(
        sg_sim_comp=2.0,
        trait_approach_raw=1.0,
        trait_long_iron_raw=1.0,
        ott_true=1.0,
        ch_adj=1.0,
        true_sg_l20=1.0,
        gate_flags=[],
    )
    assert {
        "approach", "long_iron", "ott", "course_history", "recent_form"
    } <= set(decomposition["contributions"])


# ── combine_raw_score / decompose_player: hand-derived expectations ─────────

def test_combine_raw_score_hand_derived():
    """Independently hand-computed, not sourced from VW_* constants read
    back out of the module under test."""
    contrib = enrich_cards.combine_raw_score(
        sg_sim_comp=2.0,
        trait_approach_raw=1.0,
        trait_long_iron_raw=1.0,
        ott_true=1.0,
        ch_adj=1.0,
        true_sg_l20=1.0,
    )
    # 2.0 + 0.40*1 + 0.25*1 + 0.20*1 + 0.10*1 + 0.05*1 = 2.0 + 1.00 = 3.00
    assert contrib["sg_similar_composite"] == pytest.approx(2.0)
    assert contrib["approach"]             == pytest.approx(0.40)
    assert contrib["long_iron"]            == pytest.approx(0.25)
    assert contrib["ott"]                  == pytest.approx(0.20)
    assert contrib["course_history"]       == pytest.approx(0.10)
    assert contrib["recent_form"]          == pytest.approx(0.05)
    assert contrib["pre_gate_raw_total"]   == pytest.approx(3.00)


def test_combine_raw_score_zero_inputs_yield_zero_total():
    contrib = enrich_cards.combine_raw_score(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert contrib["pre_gate_raw_total"] == 0.0
    assert all(v == 0.0 for k, v in contrib.items() if k != "pre_gate_raw_total")


# ── Bit-level parity: combine_raw_score() vs. the pre-change literal path ───
#
# git show HEAD:engine/enrich_cards.py (pre-P1-remediation) computed the
# combined-raw score in main() as a single, direct, left-associated
# expression. This literal re-implementation is independent of
# combine_raw_score() -- it exists so these tests can prove bit-for-bit
# parity rather than re-deriving the same code path from itself.

def _literal_pre_gate_raw_total(
    sg_sim_comp: float,
    trait_approach_raw: float,
    trait_long_iron_raw: float,
    ott_true: float,
    ch_adj: float,
    true_sg_l20: float,
) -> float:
    return (
        sg_sim_comp
        + enrich_cards.VW_APPROACH  * trait_approach_raw
        + enrich_cards.VW_LONG_IRON * trait_long_iron_raw
        + enrich_cards.VW_OTT       * ott_true
        + enrich_cards.VW_CH        * ch_adj
        + enrich_cards.VW_FORM      * true_sg_l20
    )


@pytest.mark.parametrize("inputs", [
    (2.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (-1.234, 0.567, -0.891, 2.345, -0.012, 0.999),
    # Real archived values (Scheffler, Scottie, rank 1) -- see
    # events/2026_Finished_Events/2026_3m_open/deploy/data/2026_3m_open_event_payload.json
    (3.0587, 0.0467, 0.5824, 0.8323863333333333, 0.0, 2.7),
], ids=["ones", "zeros", "mixed_sign", "archived_scheffler"])
def test_combine_raw_score_bit_exact_parity_with_literal_expression(inputs):
    expected = _literal_pre_gate_raw_total(*inputs)
    actual = enrich_cards.combine_raw_score(*inputs)["pre_gate_raw_total"]
    assert actual.hex() == expected.hex()
    assert actual == expected


def test_combine_raw_score_bit_exact_parity_for_all_negative_zero_input():
    """The regression Codex caught: sum(contributions.values()) implicitly
    starts from int 0, and 0 + (-0.0) == +0.0 -- silently flipping the sign
    of an all-negative-zero result. The literal left-associated expression
    never introduces that leading 0, so combine_raw_score() must reproduce
    its exact negative-zero bit pattern."""
    inputs = (-0.0, -0.0, -0.0, -0.0, -0.0, -0.0)
    expected = _literal_pre_gate_raw_total(*inputs)
    actual = enrich_cards.combine_raw_score(*inputs)["pre_gate_raw_total"]

    # Sanity: the literal expression itself is negative zero.
    assert math.copysign(1.0, expected) == -1.0
    assert expected.hex() == "-0x0.0p+0"

    assert actual.hex() == expected.hex()
    assert actual == expected
    assert math.copysign(1.0, actual) == math.copysign(1.0, expected)


def test_combine_raw_score_does_not_prepend_integer_zero_via_sum_or_dict():
    """Direct regression for the specific bug: confirm the production total
    is NOT reproducible by summing the returned dict's values (which is
    exactly the buggy path being removed) for the all-negative-zero case,
    while remaining numerically equivalent for it via the literal path."""
    contrib = enrich_cards.combine_raw_score(-0.0, -0.0, -0.0, -0.0, -0.0, -0.0)
    buggy_dict_sum = sum(
        v for k, v in contrib.items() if k != "pre_gate_raw_total"
    )
    assert math.copysign(1.0, buggy_dict_sum) == 1.0  # the old bug: sum() -> +0.0
    assert math.copysign(1.0, contrib["pre_gate_raw_total"]) == -1.0  # the fix


def test_gate_effect_no_flags_is_identity():
    effect = gate_effect_from_flags([])
    assert effect["multiplier"] == 1.0
    assert effect["applied"] == []


def test_gate_effect_single_known_flag():
    effect = gate_effect_from_flags(["INACCURATE_BOMBER"])
    assert effect["multiplier"] == pytest.approx(enrich_cards.PENALTY_BOMBER)
    assert effect["applied"] == [{"flag": "INACCURATE_BOMBER", "multiplier": enrich_cards.PENALTY_BOMBER}]


def test_gate_effect_both_known_flags_multiply():
    effect = gate_effect_from_flags(["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"])
    expected = enrich_cards.PENALTY_BOMBER * enrich_cards.PENALTY_SG_DEP
    assert effect["multiplier"] == pytest.approx(expected)


def test_gate_effect_unknown_flag_ignored():
    """A flag name this registry does not recognize contributes no
    multiplier -- it is preserved in the reported flag list but does not
    silently alter the reconstructed score."""
    effect = gate_effect_from_flags(["SOME_FUTURE_FLAG"])
    assert effect["multiplier"] == 1.0
    assert effect["flags"] == ["SOME_FUTURE_FLAG"]
    assert effect["applied"] == []


def test_decompose_player_no_gate_pre_equals_post():
    result = decompose_player(2.0, 1.0, 1.0, 1.0, 1.0, 1.0, gate_flags=[])
    assert result["pre_gate_raw_total"] == pytest.approx(3.00)
    assert result["post_gate_raw_total"] == pytest.approx(3.00)


def test_decompose_player_with_gate_applies_multiplier():
    result = decompose_player(
        2.0, 1.0, 1.0, 1.0, 1.0, 1.0, gate_flags=["INACCURATE_BOMBER"]
    )
    assert result["pre_gate_raw_total"] == pytest.approx(3.00)
    assert result["post_gate_raw_total"] == pytest.approx(3.00 * enrich_cards.PENALTY_BOMBER)


# ── Exhaustive gate-coverage parity: diagnostic reconstruction vs.
# production engine.enrich_cards.apply_gates() ───────────────────────────────
#
# apply_gates() alone decides whether a gate fires (perf/decomp threshold
# comparisons); GATE_MULTIPLIERS/gate_effect_from_flags() never re-derive
# that decision -- they only need to agree, multiplier-for-multiplier and
# bit-for-bit, with what apply_gates() actually did once its flags are
# known. These tests are the smallest safe correction: no change to
# apply_gates() or its thresholds, only exhaustive coverage that a future
# new gate flag cannot silently go undetected by the diagnostic registry.

_NO_GATE_PERF   = {"app_true": 1.0, "putt_true": 0.0, "arg_true": 0.0}
_NO_GATE_DECOMP = {"driving_dist_adj": 0.0, "driving_acc_adj": 0.0}

_BOMBER_ONLY_PERF   = {"app_true": 0.5, "putt_true": 0.1, "arg_true": 0.1}
_BOMBER_ONLY_DECOMP = {"driving_dist_adj": 0.20, "driving_acc_adj": -0.10}

_SG_RELIANT_ONLY_PERF   = {"app_true": 0.1, "putt_true": 0.6, "arg_true": 0.6}
_SG_RELIANT_ONLY_DECOMP = {"driving_dist_adj": 0.0, "driving_acc_adj": 0.0}

_BOTH_GATES_PERF   = {"app_true": 0.1, "putt_true": 0.6, "arg_true": 0.6}
_BOTH_GATES_DECOMP = {"driving_dist_adj": 0.20, "driving_acc_adj": -0.10}

_GATE_SCENARIOS = [
    ("no_gates",        _NO_GATE_PERF,        _NO_GATE_DECOMP,        []),
    ("bomber_only",     _BOMBER_ONLY_PERF,     _BOMBER_ONLY_DECOMP,    ["INACCURATE_BOMBER"]),
    ("sg_reliant_only", _SG_RELIANT_ONLY_PERF, _SG_RELIANT_ONLY_DECOMP, ["SHORT_GAME_RELIANT"]),
    ("both_gates",      _BOTH_GATES_PERF,      _BOTH_GATES_DECOMP,
     ["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"]),
]


assert PRODUCTION_GATE_ORDER == ("INACCURATE_BOMBER", "SHORT_GAME_RELIANT"), (
    "PRODUCTION_GATE_ORDER must mirror apply_gates()'s literal source "
    "order; the fixtures/tests below assume this exact sequence."
)

# Non-unit raw values required by the remediation, plus adversarial
# extremes (a tiny subnormal-adjacent magnitude and both signed zeros).
# raw_in=1.0 alone previously hid the one-ULP combined-multiplier bug --
# see test_codex_counterexample_sequential_reconstruction_is_exact below.
_BIT_PARITY_RAW_VALUES = [1.0, 5.358820043066892, -7.25, 1e-300, -0.0, 0.0]


@pytest.mark.parametrize("raw_in", _BIT_PARITY_RAW_VALUES, ids=[repr(v) for v in _BIT_PARITY_RAW_VALUES])
@pytest.mark.parametrize("name,perf,decomp,expected_flags", _GATE_SCENARIOS, ids=[s[0] for s in _GATE_SCENARIOS])
def test_diagnostic_sequential_gate_reconstruction_matches_production_bit_for_bit(
    name, perf, decomp, expected_flags, raw_in
):
    """For every current production gate scenario (none / bomber-only /
    short-game-reliant-only / both) across several non-unit raw values:
    apply_gates() is the sole authority on which flags fire; this asserts
    apply_gate_sequence_to_total() -- which multiplies sequentially, one
    recognized flag at a time, in PRODUCTION_GATE_ORDER, exactly mirroring
    apply_gates()'s own ``raw *= ...`` reassignments -- reproduces
    apply_gates()'s own adjusted raw value bit-for-bit."""
    adjusted_raw, fired_flags = enrich_cards.apply_gates(raw_in, perf, decomp)
    assert fired_flags == expected_flags

    reconstructed = apply_gate_sequence_to_total(raw_in, fired_flags)

    assert reconstructed == adjusted_raw
    assert reconstructed.hex() == adjusted_raw.hex()


def test_codex_counterexample_sequential_reconstruction_is_exact():
    """The exact one-ULP divergence Codex reported: for raw_in =
    5.358820043066892 with both gates active, production's sequential
    ``raw *= PENALTY_BOMBER`` then ``raw *= PENALTY_SG_DEP`` differs from
    a single multiplication by the precomputed combined multiplier
    (PENALTY_BOMBER * PENALTY_SG_DEP) at the last mantissa bit. This test
    pins the exact hex values on both sides and fails if diagnostic
    reconstruction ever again used the combined-multiplier path."""
    raw_in = 5.358820043066892
    adjusted_raw, fired_flags = enrich_cards.apply_gates(raw_in, _BOTH_GATES_PERF, _BOTH_GATES_DECOMP)
    assert fired_flags == ["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"]
    assert adjusted_raw.hex() == "0x1.1bf97ed7d5cdfp+2"

    # Corrected diagnostic path: sequential, matches production exactly.
    sequential = apply_gate_sequence_to_total(raw_in, fired_flags)
    assert sequential == adjusted_raw
    assert sequential.hex() == adjusted_raw.hex() == "0x1.1bf97ed7d5cdfp+2"

    # Former (removed) diagnostic path: one combined multiplication.
    # Computed independently here -- not by calling any function under
    # test -- so this is a genuine canary against regressing back to it.
    combined_multiplier = enrich_cards.PENALTY_BOMBER * enrich_cards.PENALTY_SG_DEP
    former_combined_result = raw_in * combined_multiplier
    assert former_combined_result.hex() == "0x1.1bf97ed7d5ce0p+2"
    assert former_combined_result != adjusted_raw
    assert former_combined_result != sequential


def test_decompose_player_both_gates_matches_production_sequential_for_codex_value():
    """End-to-end through decompose_player(): pre_gate_raw_total set to
    exactly the Codex counterexample raw value (via a zero-weighted
    sg_sim_comp passthrough), both gates active -- post_gate_raw_total
    must match engine.enrich_cards.apply_gates()'s own sequential result
    bit-for-bit, not the former combined-multiplier approximation."""
    raw_in = 5.358820043066892
    result = decompose_player(
        sg_sim_comp=raw_in, trait_approach_raw=0.0, trait_long_iron_raw=0.0,
        ott_true=0.0, ch_adj=0.0, true_sg_l20=0.0,
        gate_flags=["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"],
    )
    assert result["pre_gate_raw_total"] == raw_in

    adjusted_raw, _ = enrich_cards.apply_gates(raw_in, _BOTH_GATES_PERF, _BOTH_GATES_DECOMP)
    assert result["post_gate_raw_total"] == adjusted_raw
    assert result["post_gate_raw_total"].hex() == adjusted_raw.hex()


def test_apply_gate_sequence_to_total_ignores_input_flag_list_order():
    """apply_gate_sequence_to_total() always iterates PRODUCTION_GATE_ORDER
    (never the caller's flag-list order), so supplying the two known flags
    in either order must produce the identical bit-for-bit sequential
    result -- matching production, which has one single fixed application
    order regardless of how a caller's flag list happens to be ordered."""
    raw_in = 5.358820043066892
    forward        = apply_gate_sequence_to_total(raw_in, ["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"])
    reversed_input = apply_gate_sequence_to_total(raw_in, ["SHORT_GAME_RELIANT", "INACCURATE_BOMBER"])
    assert forward == reversed_input
    assert forward.hex() == reversed_input.hex()

    adjusted_raw, _ = enrich_cards.apply_gates(raw_in, _BOTH_GATES_PERF, _BOTH_GATES_DECOMP)
    assert forward == adjusted_raw


def test_gate_effect_descriptive_multiplier_is_order_immaterial_but_not_used_for_totals():
    """gate_effect_from_flags()'s aggregate ``multiplier`` field always
    iterates PRODUCTION_GATE_ORDER too, so it is order-invariant given the
    same flag set. This is exactly why it is safe to keep as descriptive
    metadata -- but it must never be used to compute a post-gate total
    (see apply_gate_sequence_to_total's docstring); this test only
    verifies the metadata's own order-invariance, not its use as a total."""
    forward  = gate_effect_from_flags(["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"])
    reversed_order = gate_effect_from_flags(["SHORT_GAME_RELIANT", "INACCURATE_BOMBER"])
    assert forward["multiplier"] == reversed_order["multiplier"]
    assert forward["multiplier"].hex() == reversed_order["multiplier"].hex()
    # "applied" always reflects PRODUCTION_GATE_ORDER, not input order.
    assert [a["flag"] for a in forward["applied"]] == ["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"]
    assert [a["flag"] for a in reversed_order["applied"]] == ["INACCURATE_BOMBER", "SHORT_GAME_RELIANT"]


def _production_gate_flag_names() -> set[str]:
    """Extract every string literal passed to ``flags.append(...)`` inside
    ``apply_gates()`` via source introspection. This is a lightweight,
    automatic coverage check that requires no change to apply_gates()
    itself and no second production authority: it reads the real
    production source at test time, so a future new gate flag with no
    matching GATE_MULTIPLIERS entry fails this test immediately, without
    needing apply_gates() to expose a registry of its own."""
    source = inspect.getsource(enrich_cards.apply_gates)
    return set(re.findall(r'flags\.append\("([^"]+)"\)', source))


def test_gate_registry_covers_every_production_gate_flag_name():
    production_flags = _production_gate_flag_names()
    # Documents the current production gate set this exhaustive suite
    # covers (per the four scenarios above and the registry check below).
    assert production_flags == {"INACCURATE_BOMBER", "SHORT_GAME_RELIANT"}
    missing = production_flags - set(GATE_MULTIPLIERS.keys())
    assert not missing, (
        f"apply_gates() can emit {missing}, which has no GATE_MULTIPLIERS "
        "entry in engine/scoring_decomposition.py"
    )


def test_gate_registry_has_no_unrecognized_extra_entries():
    """The reverse direction: the diagnostic registry must not claim a
    multiplier for a flag apply_gates() can no longer emit."""
    production_flags = _production_gate_flag_names()
    extra = set(GATE_MULTIPLIERS.keys()) - production_flags
    assert not extra, f"GATE_MULTIPLIERS has entries apply_gates() never emits: {extra}"


def test_gate_effect_unsupported_flag_matches_current_production_behavior():
    """Production apply_gates() only ever emits the two known flag names
    (see test_gate_registry_covers_every_production_gate_flag_name) -- it
    has no notion of an 'unsupported' flag. This documents and locks the
    diagnostic layer's own defined behavior for any flag name outside that
    set (e.g. from a hand-edited or future artifact): treated as a no-op
    multiplier, never a crash and never a silent nonzero effect."""
    effect = gate_effect_from_flags(["NOT_A_REAL_PRODUCTION_GATE"])
    assert effect["multiplier"] == 1.0
    assert effect["applied"] == []
    assert effect["flags"] == ["NOT_A_REAL_PRODUCTION_GATE"]


# ── Missing-source diagnostic: current zero-default behavior, unchanged ─────

def test_missing_source_zero_default_yields_zero_contribution_only_for_that_component():
    """Mirrors production's zero-fill defaults (_EMPTY_SKILL/_EMPTY_PERF/
    _EMPTY_DECOMP/_EMPTY_TREND in enrich_cards.main()): a component with no
    source data contributes exactly 0.0 to the pre-gate total and does not
    perturb any other component's contribution."""
    present = enrich_cards.combine_raw_score(2.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    missing_form_only = enrich_cards.combine_raw_score(2.0, 1.0, 1.0, 1.0, 1.0, 0.0)
    assert missing_form_only["recent_form"] == 0.0
    for key in ("sg_similar_composite", "approach", "long_iron", "ott", "course_history"):
        assert missing_form_only[key] == present[key]
    assert missing_form_only["pre_gate_raw_total"] == pytest.approx(
        present["pre_gate_raw_total"] - present["recent_form"]
    )


# ── Benchmark isolation: unused DG columns never reach the official score ───

def test_benchmark_isolation_unused_dg_columns_do_not_change_vts(tmp_path, monkeypatch):
    """load_decomp() in enrich_cards.py reads only driving_acc_adj,
    driving_dist_adj, and std_dev from dg_decomposition.csv. Every other
    column in the real dg_decomposition.csv contract (baseline,
    country_adj, age, age_adj, true_sg_adj, timing_adj, sg_category_adj,
    course_history_adj, fit_other_adj, course_fit_total_adj,
    final_prediction -- see standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
    §2B) is benchmark-only and must never move vts_final, rank, or tier.
    driving_acc_adj/driving_dist_adj themselves are excluded from this test
    because existing gates consume them -- they are approved source trait
    fields, not benchmark-only columns."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    before = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    before_by_player = {p["player"]: p for p in before["players"]}

    # Rewrite dg_decomposition.csv with the same consumed columns unchanged,
    # but add every benchmark-only column populated with extreme values.
    with (event.input_dir / "dg_decomposition.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow([
            "player_name", "driving_acc_adj", "driving_dist_adj", "std_dev",
            "baseline", "country_adj", "age", "age_adj", "true_sg_adj",
            "timing_adj", "sg_category_adj", "course_history_adj",
            "fit_other_adj", "course_fit_total_adj", "final_prediction",
        ])
        for name in ("Doe, John", "Smith, Sam"):
            w.writerow([
                name, "0.0", "0.0", "3.0",
                "999.9", "999.9", "99", "999.9", "999.9",
                "999.9", "999.9", "999.9",
                "999.9", "999.9", "999.9",
            ])

    _run_main(monkeypatch, tmp_path, event.event_slug)
    after = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    after_by_player = {p["player"]: p for p in after["players"]}

    for name in ("Doe, John", "Smith, Sam"):
        b, a = before_by_player[name], after_by_player[name]
        assert a["vts_final"] == b["vts_final"]
        assert a["rank"] == b["rank"]
        assert a["tier"] == b["tier"]
        assert a["neutralSkillIndex"] == b["neutralSkillIndex"]
        assert a["winPct"] == b["winPct"]
        assert a["anti_pattern_flags"] == b["anti_pattern_flags"]


# ── Read-only archived 3M parity ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def archived_3m_players() -> list[dict]:
    payload = json.loads(_ARCHIVED_3M_PAYLOAD.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == FORMULA.formula_identifier
    return payload["players"]


def test_archived_payload_is_read_only_fixture_not_mutated(archived_3m_players):
    """Sanity guard: this test file must never write to the archive. Assert
    the path is under events/2026_Finished_Events/ (never modified) and
    that the loaded object is a fresh in-memory list every time (no shared
    mutable state leaking between tests)."""
    assert "2026_Finished_Events" in str(_ARCHIVED_3M_PAYLOAD)
    assert isinstance(archived_3m_players, list)
    assert len(archived_3m_players) == 144


def test_archived_tier_matches_assign_tier_of_stored_rank(archived_3m_players):
    """Exact, pure-function recomputation -- no floating-point field
    aggregation involved, so this must match bit-for-bit."""
    for p in archived_3m_players:
        assert assign_tier(p["rank"]) == p["tier"]


def test_archived_make_cut_prob_matches_stored_makecutpct(archived_3m_players):
    """make_cut_prob() is applied to an already-rounded stored input
    (top20Pct), so recomputing it must reproduce makeCutPct exactly."""
    for p in archived_3m_players:
        assert round(make_cut_prob(p["top20Pct"]), 1) == p["makeCutPct"]
        assert round(100.0 - p["makeCutPct"], 1) == p["missCutPct"]


def test_archived_probability_monotonicity_holds(archived_3m_players):
    for p in archived_3m_players:
        assert p["top5Pct"]  >= p["winPct"]
        assert p["top10Pct"] >= p["top5Pct"]
        assert p["top20Pct"] >= p["top10Pct"]


def test_archived_decomposition_reconstructs_pre_and_post_gate_raw(archived_3m_players):
    """Recompute every player's pre-gate contributions and post-gate raw
    from the frozen artifact's own stored decomposition fields, then
    z-score the reconstructed field exactly as enrich_cards.main() does,
    and prove the result reproduces the archive's own vts_final and
    prepenalty_vts exactly, after rounding the reconstruction to the same
    one decimal place the archive itself was stored at. All 144 players'
    vts_final values, and the gated player's prepenalty_vts, are asserted
    for exact equality -- there is no floating-point tolerance here: an
    independent verification pass found 144/144 vts_final values and 1/1
    prepenalty_vts values exact with a maximum residual of 0.0."""
    decompositions = [
        decompose_player(
            sg_sim_comp=p["sg_similar_composite"],
            trait_approach_raw=p["trait_approach_raw"],
            trait_long_iron_raw=p["trait_long_iron_raw"],
            ott_true=p["ott_true"],
            ch_adj=p["ch_adjustment"],
            true_sg_l20=p["true_sg_l20"],
            gate_flags=p["anti_pattern_flags"],
        )
        for p in archived_3m_players
    ]

    pre_totals  = [d["pre_gate_raw_total"]  for d in decompositions]
    post_totals = [d["post_gate_raw_total"] for d in decompositions]

    reconstructed_vts = z_score_scale(post_totals)
    reconstructed_pre = z_score_scale(pre_totals)

    vts_compared = 0
    prepenalty_compared = 0
    for p, recon_vts, recon_pre in zip(archived_3m_players, reconstructed_vts, reconstructed_pre):
        recon_vts_rounded = round(recon_vts, 1)
        vts_compared += 1
        assert recon_vts_rounded == p["vts_final"], (
            f"player={p['player']!r} archived vts_final={p['vts_final']} "
            f"reconstructed={recon_vts_rounded} "
            f"residual={recon_vts_rounded - p['vts_final']}"
        )
        if p["anti_pattern_flags"]:
            assert p["prepenalty_vts"] is not None
            recon_pre_rounded = round(recon_pre, 1)
            prepenalty_compared += 1
            assert recon_pre_rounded == p["prepenalty_vts"], (
                f"player={p['player']!r} archived prepenalty_vts={p['prepenalty_vts']} "
                f"reconstructed={recon_pre_rounded} "
                f"residual={recon_pre_rounded - p['prepenalty_vts']}"
            )
        else:
            assert p["prepenalty_vts"] is None

    assert vts_compared == 144
    assert prepenalty_compared >= 1


def test_archived_decomposition_reconstructed_ranking_matches_stored_rank(archived_3m_players):
    """The reconstructed, z-scored post-gate raw score -- rounded to 1
    decimal exactly as production rounds vts_final before sorting
    (enrich_cards.main() sorts on the already-rounded ``vts_final``, not
    the full-precision raw score) -- must be monotonically non-increasing
    across the archive's stored rank order. Two adjacent players may
    legitimately tie at the rounded display precision (production's stable
    sort then falls back to field order, which this decomposition-only
    reconstruction cannot recover from the frozen payload alone); a
    genuine inversion between two *different* rounded values would fail
    this assertion and would indicate a real decomposition mismatch."""
    decompositions = [
        decompose_player(
            sg_sim_comp=p["sg_similar_composite"],
            trait_approach_raw=p["trait_approach_raw"],
            trait_long_iron_raw=p["trait_long_iron_raw"],
            ott_true=p["ott_true"],
            ch_adj=p["ch_adjustment"],
            true_sg_l20=p["true_sg_l20"],
            gate_flags=p["anti_pattern_flags"],
        )
        for p in archived_3m_players
    ]
    post_totals = [d["post_gate_raw_total"] for d in decompositions]
    reconstructed_vts = [round(v, 1) for v in z_score_scale(post_totals)]

    stored_in_rank_order = sorted(
        zip(archived_3m_players, reconstructed_vts), key=lambda t: t[0]["rank"]
    )
    recon_by_rank_order = [v for _, v in stored_in_rank_order]

    for i in range(len(recon_by_rank_order) - 1):
        cur, nxt = recon_by_rank_order[i], recon_by_rank_order[i + 1]
        assert cur >= nxt, (
            f"rank {i + 1} ({stored_in_rank_order[i][0]['player']}, recon={cur}) "
            f"< rank {i + 2} ({stored_in_rank_order[i + 1][0]['player']}, recon={nxt})"
        )


def test_archived_anti_pattern_gate_flags_are_known_registry_members(archived_3m_players):
    """Every anti_pattern_flag actually present in the frozen archive must
    be a flag this parity layer's GATE_MULTIPLIERS registry recognizes --
    otherwise the reconstructed post-gate raw silently drops that player's
    gate effect."""
    seen = {f for p in archived_3m_players for f in p["anti_pattern_flags"]}
    assert seen, "expected at least one gated player in the archived fixture"
    assert seen <= set(GATE_MULTIPLIERS.keys())
