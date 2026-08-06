"""Tests for engine/venuedna_scoring.py -- the pure, I/O-free implementation
of canonical formula v2.0.0 (standards/02_PGA_VENUEDNA_SCORING_SPEC.md §7-§12).

This is a reusable scoring boundary, independent of any event, venue, or the
historical event-hardcoded 3M Open pathway (engine/enrich_cards.py). Every
expected numeric value below is independently hand-derived arithmetic that
does not call the function under test to produce its own expected value.
"""
from __future__ import annotations

import ast
import inspect
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import venuedna_scoring as vs  # noqa: E402


_ROOT = Path(__file__).resolve().parent.parent
_MODULE_PATH = _ROOT / "engine" / "venuedna_scoring.py"

LEGACY_NONCORE_ADDENDS = (
    "trait_approach_raw", "trait_long_iron_raw", "ott_true", "ch_adjustment", "true_sg_l20",
)


# ── 1. Exact formula metadata ───────────────────────────────────────────────

def test_formula_metadata_matches_canonical_doctrine():
    assert vs.FORMULA_ID == "venuedna_dual_vector_decomposed"
    assert vs.FORMULA_VERSION == "2.0.0"
    assert vs.COMPARABLE_SCORE_FAMILY == "dual_vector_sg_per_round_v2"
    assert vs.PENALTY_GATE_SET_ID == "venuedna_v2_none"
    assert vs.CORE_INPUTS == ("SG_Base_Comp", "Delta_Fit_Comp", "VenueHistoryDeltaRaw")
    assert vs.EXCLUDED_LEGACY_NONCORE_ADDENDS == LEGACY_NONCORE_ADDENDS


def test_formula_metadata_dict_reflects_same_constants():
    projection = vs.compute_player_projection(
        neutral_skill_horizons={"6m": 1.0, "12m": 1.0, "24m": 1.0},
        similar_course_rows={
            "6m": vs.SimilarCourseRow(20, 1.0),
            "12m": vs.SimilarCourseRow(20, 1.0),
            "24m": vs.SimilarCourseRow(20, 1.0),
        },
    )
    assert projection.formula_metadata["formula_id"] == vs.FORMULA_ID
    assert projection.formula_metadata["formula_version"] == vs.FORMULA_VERSION
    assert projection.formula_metadata["penalty_gate_set_id"] == vs.PENALTY_GATE_SET_ID
    assert projection.formula_metadata["core_inputs"] == vs.CORE_INPUTS


# ── 2. Exact three-layer core decomposition ─────────────────────────────────

def test_pre_penalty_raw_equals_sum_of_three_named_layers():
    projection = vs.compute_player_projection(
        neutral_skill_horizons={"6m": 2.0, "12m": 3.0, "24m": 1.0},
        similar_course_rows={
            "6m": vs.SimilarCourseRow(20, 2.5),
            "12m": vs.SimilarCourseRow(20, 3.5),
            "24m": vs.SimilarCourseRow(20, 1.5),
        },
    )
    expected_neutral_skill = 0.20 * 2.0 + 0.30 * 3.0 + 0.50 * 1.0
    expected_venue_fit = 0.50 * 0.5 + 0.30 * 0.5 + 0.20 * 0.5
    expected_venue_history = 0.0
    assert projection.neutral_skill_raw == pytest.approx(expected_neutral_skill)
    assert projection.venue_fit_delta_raw == pytest.approx(expected_venue_fit)
    assert projection.venue_history_delta_raw == expected_venue_history
    assert projection.pre_penalty_raw == pytest.approx(
        expected_neutral_skill + expected_venue_fit + expected_venue_history
    )


# ── 3. Legacy noncore addends cannot alter v2 output ────────────────────────

def test_compute_player_projection_signature_has_no_legacy_addend_parameters():
    params = set(inspect.signature(vs.compute_player_projection).parameters)
    for addend in LEGACY_NONCORE_ADDENDS:
        assert addend not in params


def test_compute_player_projection_rejects_legacy_addend_kwarg():
    with pytest.raises(TypeError):
        vs.compute_player_projection(
            neutral_skill_horizons={"6m": 1.0, "12m": 1.0, "24m": 1.0},
            similar_course_rows={
                "6m": vs.SimilarCourseRow(20, 1.0),
                "12m": vs.SimilarCourseRow(20, 1.0),
                "24m": vs.SimilarCourseRow(20, 1.0),
            },
            trait_approach_raw=0.9,  # type: ignore[call-arg]
        )


# ── 4. venuedna_v2_none applies no penalty or gate ──────────────────────────

def test_no_penalty_or_gate_applied_under_v2_none():
    projection = vs.compute_player_projection(
        neutral_skill_horizons={"6m": 5.0, "12m": 5.0, "24m": 5.0},
        similar_course_rows={
            "6m": vs.SimilarCourseRow(20, 5.0),
            "12m": vs.SimilarCourseRow(20, 5.0),
            "24m": vs.SimilarCourseRow(20, 5.0),
        },
    )
    assert projection.penalties_applied == ()
    assert projection.gates_applied == ()
    assert projection.post_penalty_raw == projection.pre_penalty_raw
    assert projection.post_gate_raw == projection.post_penalty_raw


# ── 5. Valid numeric zero is retained ───────────────────────────────────────

def test_neutral_skill_valid_zero_horizon_is_retained_not_missing():
    result = vs.compute_neutral_skill({"6m": 0.0, "12m": 1.0, "24m": 1.0})
    assert result.status == "SCORED"
    assert "6m" in result.valid_horizons
    assert result.value == pytest.approx(0.20 * 0.0 + 0.30 * 1.0 + 0.50 * 1.0)


def test_venue_history_zero_is_the_genuine_neutral_value_not_absence():
    result = vs.compute_venue_history(vs.VenueHistoryEvidence(relevant_starts=8))
    assert result.value == 0.0
    assert isinstance(result.value, float)


# ── 6. Missing values remain missing ────────────────────────────────────────

def test_neutral_skill_missing_horizon_excluded_from_valid_set():
    result = vs.compute_neutral_skill({"6m": None, "12m": 1.0, "24m": 1.0})
    assert "6m" not in result.valid_horizons
    assert len(result.valid_horizons) == 2


def test_neutral_skill_all_missing_yields_no_value():
    result = vs.compute_neutral_skill({"6m": None, "12m": None, "24m": None})
    assert result.value is None
    assert result.status == "UNSCORED"


# ── 7. Two-horizon NeutralSkill renormalization ─────────────────────────────

def test_neutral_skill_two_horizon_renormalization_hand_derived():
    # 12m and 24m valid; 6m missing. Weights 0.30 and 0.50 renormalize over 0.80.
    result = vs.compute_neutral_skill({"6m": None, "12m": 2.0, "24m": 4.0})
    expected = (0.30 * 2.0 + 0.50 * 4.0) / 0.80
    assert result.status == "SCORED"
    assert result.value == pytest.approx(expected)
    assert result.confidence == "THIN"


# ── 8. Fewer than two horizons produces UNSCORED ────────────────────────────

def test_neutral_skill_single_valid_horizon_is_unscored():
    result = vs.compute_neutral_skill({"6m": 1.0, "12m": None, "24m": None})
    assert result.status == "UNSCORED"
    assert result.value is None


def test_neutral_skill_zero_valid_horizons_is_unscored():
    result = vs.compute_neutral_skill({"6m": None, "12m": None, "24m": None})
    assert result.status == "UNSCORED"


def test_player_projection_is_unscored_when_neutral_skill_unscored():
    projection = vs.compute_player_projection(
        neutral_skill_horizons={"6m": 1.0, "12m": None, "24m": None},
        similar_course_rows={
            "6m": vs.SimilarCourseRow(20, 1.0),
            "12m": vs.SimilarCourseRow(20, 1.0),
            "24m": vs.SimilarCourseRow(20, 1.0),
        },
    )
    assert projection.status == "UNSCORED"
    assert projection.pre_penalty_raw is None
    assert projection.post_gate_raw is None


# ── 9. Valid zero-round similar row produces DEBUT ──────────────────────────

def test_venue_fit_zero_round_valid_row_is_debut():
    result = vs.compute_venue_fit(
        similar_course_rows={
            "6m": vs.SimilarCourseRow(0, 0.0),
            "12m": vs.SimilarCourseRow(0, 0.0),
            "24m": vs.SimilarCourseRow(0, 0.0),
        },
        base_horizons={"6m": 2.0, "12m": 2.0, "24m": 2.0},
    )
    assert result.data_depth == "DEBUT"
    assert result.value == 0.0
    assert result.confidence == "THIN"


def test_venue_fit_zero_round_row_debut_is_robust_to_nonsensical_total_mean():
    result = vs.compute_venue_fit(
        similar_course_rows={
            "6m": vs.SimilarCourseRow(0, 999.0),
            "12m": vs.SimilarCourseRow(0, -999.0),
            "24m": vs.SimilarCourseRow(0, 0.0),
        },
        base_horizons={"6m": 2.0, "12m": 2.0, "24m": 2.0},
    )
    assert result.data_depth == "DEBUT"
    assert result.value == 0.0


# ── 10. Missing similar row does not produce DEBUT ──────────────────────────

def test_venue_fit_entirely_missing_row_is_not_debut():
    result = vs.compute_venue_fit(
        similar_course_rows={"6m": None, "12m": None, "24m": None},
        base_horizons={"6m": 2.0, "12m": 2.0, "24m": 2.0},
    )
    assert result.data_depth == "MISSING"
    assert result.data_depth != "DEBUT"
    assert result.value is None


def test_venue_fit_partial_missing_horizons_is_not_renormalized():
    result = vs.compute_venue_fit(
        similar_course_rows={"6m": vs.SimilarCourseRow(20, 3.0), "12m": None, "24m": None},
        base_horizons={"6m": 2.0, "12m": 2.0, "24m": 2.0},
    )
    # Formula v2 authorizes partial-horizon renormalization only for
    # NeutralSkill. VenueFit keeps its fixed three-horizon vector intact.
    assert result.data_depth == "MISSING"
    assert result.value is None
    assert result.confidence == "THIN"


# ── 11. VenueHistoryDeltaRaw explicit neutral 0.0; raw-source confidence thin when missing ──

def test_venue_history_delta_raw_is_neutral_zero_and_thin_when_evidence_missing():
    result = vs.compute_venue_history(None)
    assert result.value == 0.0
    assert result.confidence == "THIN"


@pytest.mark.parametrize("relevant_starts", (0, 1, 7))
def test_venue_history_delta_raw_stays_zero_and_thin_below_threshold(relevant_starts):
    result = vs.compute_venue_history(vs.VenueHistoryEvidence(relevant_starts=relevant_starts))
    assert result.value == 0.0
    assert result.confidence == "THIN"


@pytest.mark.parametrize("relevant_starts", (8, 9))
def test_venue_history_threshold_is_confident_without_changing_neutral_raw(relevant_starts):
    result = vs.compute_venue_history(vs.VenueHistoryEvidence(relevant_starts=relevant_starts))
    assert result.value == 0.0
    assert result.confidence != "THIN"


# ── 12. Confidence components remain decomposed ─────────────────────────────

def test_confidence_by_source_independently_decomposed_not_collapsed():
    projection = vs.compute_player_projection(
        neutral_skill_horizons={"6m": 2.0, "12m": 2.0, "24m": 2.0},  # HIGH (3 valid)
        similar_course_rows={
            "6m": vs.SimilarCourseRow(20, 5.0),
            "12m": None,
            "24m": None,
        },  # THIN/MISSING (fixed VenueFit horizon doctrine)
        venue_history_evidence=None,  # THIN
    )
    conf = projection.confidence_by_source
    assert set(conf) == set(vs.CONFIDENCE_SOURCES)
    assert conf["neutral_skill"] == "HIGH"
    assert conf["venue_fit"] == "THIN"
    assert conf["venue_history"] == "THIN"
    # Independently decomposed: differing values prove no single collapsed label.
    assert len(set(conf.values())) > 1


# ── 13. Deterministic within-event z-score normalization ───────────────────

def test_z_score_scale_hand_derived_two_player_field():
    values = [1.0, 3.0]
    mu = 2.0
    var = ((1.0 - 2.0) ** 2 + (3.0 - 2.0) ** 2) / 2
    sd = math.sqrt(var)
    expected = [50.0 + 15.0 * (v - mu) / sd for v in values]
    result = vs.z_score_scale(values)
    assert result == pytest.approx(expected)


def test_z_score_scale_is_deterministic():
    values = [1.0, 3.0, 2.0, 7.5]
    assert vs.z_score_scale(values) == vs.z_score_scale(values)


def test_z_score_scale_clamped_to_0_100_and_empty_field():
    assert vs.z_score_scale([]) == []
    values = [0.0, 0.0, 0.0, 1000.0]
    result = vs.z_score_scale(values)
    assert all(0.0 <= v <= 100.0 for v in result)


# ── 14. Rank and tier ordering ───────────────────────────────────────────────

def test_rank_players_descending_by_post_gate_raw():
    ranks = vs.rank_players({"a": 10.0, "b": 30.0, "c": 20.0})
    assert ranks == {"b": 1, "c": 2, "a": 3}


def test_assign_tier_boundaries():
    assert vs.assign_tier(1) == "T1"
    assert vs.assign_tier(5) == "T1"
    assert vs.assign_tier(6) == "T2"
    assert vs.assign_tier(12) == "T2"
    assert vs.assign_tier(13) == "T3"
    assert vs.assign_tier(25) == "T3"
    assert vs.assign_tier(26) == "T4"
    assert vs.assign_tier(40) == "T4"
    assert vs.assign_tier(41) == "T5"


# ── 15. Probability field sums, monotonicity, and make-cut bounds ──────────

def test_probability_vectors_monotonic_and_bounded():
    scores = [10.0, 50.0, 30.0, 5.0, 90.0]
    results = vs.compute_probability_vectors(scores)
    for p in results:
        assert p["top5Pct"] >= p["winPct"]
        assert p["top10Pct"] >= p["top5Pct"]
        assert p["top20Pct"] >= p["top10Pct"]
        assert vs.MAKECUT_MIN <= p["makeCutPct"] <= vs.MAKECUT_MAX
        assert p["missCutPct"] == pytest.approx(100.0 - p["makeCutPct"])


def test_make_cut_prob_hand_derived_bounds():
    assert vs.make_cut_prob(0.0) == pytest.approx(20.0)
    assert vs.make_cut_prob(100.0) == 98.0  # clamped
    assert vs.make_cut_prob(50.0) == pytest.approx(min(98.0, 50.0 * 1.25 + 10.0))


def test_softmax_field_positions_sum_approximately():
    scores = [50.0, 48.0, 45.0, 40.0, 35.0, 30.0]
    win = vs.tempered_softmax(scores, vs.SOFTMAX_TEMPERATURES["win"], vs.SOFTMAX_POSITIONS["win"])
    total = sum(win)
    assert total == pytest.approx(100.0, rel=0.05)


# ── 16. DG benchmark isolation ──────────────────────────────────────────────

def test_no_function_accepts_a_dg_benchmark_parameter():
    for name, fn in inspect.getmembers(vs, inspect.isfunction):
        for param in inspect.signature(fn).parameters:
            assert not param.lower().startswith("dg_"), f"{name} accepts DG param {param}"
            assert "benchmark" not in param.lower(), f"{name} accepts benchmark param {param}"


# ── 17. No file, event, deploy, database, or archive I/O ───────────────────

def test_module_performs_no_io():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {"pathlib", "os", "sqlite3", "csv", "json", "sys", "shutil"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported & forbidden_modules == set()
    assert "open(" not in source


def _imported_module_names() -> set[str]:
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def test_module_has_no_dependency_on_enrich_cards():
    assert "enrich_cards" not in _imported_module_names()


def test_module_does_not_import_identity_resolver():
    assert "identity_resolver" not in _imported_module_names()


# ── 18. Historical formula remains separately identifiable ─────────────────

def test_formula_id_distinct_from_legacy_historical_implementation():
    import scoring_decomposition as sd  # noqa: E402  (legacy diagnostic parity layer)
    assert vs.FORMULA_ID != sd.FORMULA.formula_identifier
    assert vs.PENALTY_GATE_SET_ID != sd.HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID


# ── Structural: pure functions raise on nonsense, no hidden state ──────────

def test_compute_neutral_skill_is_a_pure_function_no_shared_state():
    horizons = {"6m": 1.0, "12m": 2.0, "24m": 3.0}
    first = vs.compute_neutral_skill(horizons)
    second = vs.compute_neutral_skill(horizons)
    assert first == second
