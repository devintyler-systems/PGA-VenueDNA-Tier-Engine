"""Tests for par5_predator badge qualification end-to-end."""
import importlib.util, copy
from pathlib import Path
import pytest

_ENGINE_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_Finished_Events" / "2026_rocket_classic" / "engine" / "enrich_cards.py"
)
_spec = importlib.util.spec_from_file_location("rocket_engine", _ENGINE_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

qualify_badges             = _mod.qualify_badges
compute_badge_percentiles  = _mod.compute_badge_percentiles
build_badge_inputs         = _mod.build_badge_inputs
load_badge_policy          = _mod.load_badge_policy
compute_par5_composite_scores = _mod.compute_par5_composite_scores
_PAR5_HOLE_MIN_2026        = _mod._PAR5_HOLE_MIN_2026

POLICY = load_badge_policy(
    Path(__file__).resolve().parent.parent / "config" / "badge_policy.v1.json"
)
assert any(b["badge_id"] == "par5_predator" for b in POLICY), "par5_predator missing from policy"


def _make_par5_composite(composite, coverage="FULL", holes=200, **kwargs):
    """Build a minimal par5_composite_data dict for build_badge_inputs."""
    return {
        "usable_for_badges": composite is not None,
        "coverage_status":   coverage,
        "composite":         composite,
        "component_availability": {
            "scoring_avg_2026":  "MEASURED",
            "birdie_pct_2026":   "MEASURED",
            "eagle_rate_2026":   "MEASURED" if coverage == "FULL" else "UNAVAILABLE",
            "scoring_avg_2025":  "MEASURED",
            "birdie_pct_2025":   "MEASURED",
            "eagle_rate_2025":   "MEASURED" if coverage == "FULL" else "UNAVAILABLE",
        },
        "holes_2026": holes,
        "scoring_avg_2026": 4.40,
        "birdie_pct_2026":  55.0,
        "eagle_rate_2026":  kwargs.get("eagle_rate_2026", 0.05),
        "scoring_avg_2025": kwargs.get("scoring_avg_2025", 4.45),
        "birdie_pct_2025":  kwargs.get("birdie_pct_2025", 53.0),
        "eagle_rate_2025":  kwargs.get("eagle_rate_2025", 0.04),
        "provenance":       "scoring_avg_2026=4.400; birdie_pct_2026=55.00%",
        "unavailable_reason": None,
    }


def _player_stub():
    """Minimal player dict for build_badge_inputs (par5 path only needs player_id)."""
    return {
        "player_name": "Test, Player",
        "player_id": "pid_test",
        "trait_availability": {},
        "_detroit_starts": 0,
        "_detroit_rounds": 0,
        "_ch_resolved": True,
    }


# ── Basic wiring ───────────────────────────────────────────────────────────────

def test_par5_predator_not_emitted_when_required_2026_input_missing():
    """usable_for_badges=False (missing required 2026 data) -> no badge."""
    par5_data = _make_par5_composite(None, coverage="UNAVAILABLE", holes=200)
    par5_data["usable_for_badges"] = False
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    assert not inputs["par5_scoring"]["usable_for_badges"]
    result = qualify_badges(inputs, POLICY, {})
    assert not any(b["badge_id"] == "par5_predator" for b in result)


def test_par5_predator_not_emitted_below_hole_gate():
    """If par5 composite computed but holes < minimum, badge is blocked upstream (usable=False)."""
    par5_data = _make_par5_composite(None, coverage="UNAVAILABLE", holes=100)
    par5_data["usable_for_badges"] = False
    par5_data["unavailable_reason"] = f"Insufficient 2026 par-5 holes: 100 < {_PAR5_HOLE_MIN_2026}"
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    assert not inputs["par5_scoring"]["usable_for_badges"]
    result = qualify_badges(inputs, POLICY, {})
    assert not any(b["badge_id"] == "par5_predator" for b in result)


def test_par5_predator_not_emitted_below_threshold():
    """Player with valid composite but below 89th percentile -> no badge."""
    par5_data = _make_par5_composite(0.5, coverage="FULL", holes=200)
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    # Manually assign a below-threshold percentile
    percentiles = {"par5_scoring": 50}
    result = qualify_badges(inputs, POLICY, percentiles)
    assert not any(b["badge_id"] == "par5_predator" for b in result)


def test_par5_predator_qualifies_at_or_above_89th_pct():
    """Player with valid composite at 89th+ percentile -> par5_predator emitted."""
    par5_data = _make_par5_composite(1.5, coverage="FULL", holes=220)
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    percentiles = {"par5_scoring": 89}
    result = qualify_badges(inputs, POLICY, percentiles)
    assert any(b["badge_id"] == "par5_predator" for b in result)


def test_par5_predator_qualification_reason_is_source_backed():
    """Emitted badge reason contains source filename and provenance."""
    par5_data = _make_par5_composite(1.5, coverage="FULL", holes=220)
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    percentiles = {"par5_scoring": 92}
    result = qualify_badges(inputs, POLICY, percentiles)
    badge = next(b for b in result if b["badge_id"] == "par5_predator")
    reason = badge["qualification_reason"]
    assert "par5_scoring_average.csv" in reason or "scoring_average" in reason
    assert "composite" in reason.lower() or "composite=" in reason


# ── Degraded coverage ──────────────────────────────────────────────────────────

def test_par5_predator_emitted_with_degraded_no_2026_eagle():
    """Missing 2026 eagle row -> DEGRADED_NO_2026_EAGLE -> still qualifiable if composite valid."""
    par5_data = _make_par5_composite(1.2, coverage="DEGRADED_NO_2026_EAGLE", holes=210)
    par5_data["eagle_rate_2026"] = None
    par5_data["component_availability"]["eagle_rate_2026"] = "UNAVAILABLE"
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    assert inputs["par5_scoring"]["usable_for_badges"]  # still eligible
    assert inputs["par5_scoring"]["availability"] == "DEGRADED_NO_2026_EAGLE"
    percentiles = {"par5_scoring": 91}
    result = qualify_badges(inputs, POLICY, percentiles)
    assert any(b["badge_id"] == "par5_predator" for b in result)


def test_par5_predator_not_blocked_by_missing_2025_eagle_alone():
    """Absence of 2025 eagle data alone is not a disqualifying state."""
    par5_data = _make_par5_composite(1.3, coverage="CURRENT_FULL_HISTORICAL_PARTIAL", holes=215)
    par5_data["eagle_rate_2025"] = None
    par5_data["component_availability"]["eagle_rate_2025"] = "UNAVAILABLE"
    par5_data["usable_for_badges"] = True  # still eligible — 2026 required data present
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    assert inputs["par5_scoring"]["usable_for_badges"]
    percentiles = {"par5_scoring": 90}
    result = qualify_badges(inputs, POLICY, percentiles)
    assert any(b["badge_id"] == "par5_predator" for b in result)


# ── Denominator quarantine ─────────────────────────────────────────────────────

def test_par5_predator_not_emitted_when_denominator_quarantined():
    """Required 2026 denominator failure -> usable=False -> no badge."""
    par5_data = _make_par5_composite(None, coverage="UNAVAILABLE", holes=200)
    par5_data["usable_for_badges"] = False
    par5_data["unavailable_reason"] = "Required 2026 denominator validation failed"
    inputs = build_badge_inputs(_player_stub(), None, None, par5_data)
    assert not inputs["par5_scoring"]["usable_for_badges"]
    result = qualify_badges(inputs, POLICY, {})
    assert not any(b["badge_id"] == "par5_predator" for b in result)


# ── compute_par5_composite_scores ──────────────────────────────────────────────

def _make_players_raw(n: int, base_id: str = "pid") -> list[dict]:
    return [{"player_id": f"{base_id}_{i}", "player_name": f"Player, {i}"} for i in range(n)]


def _make_par5_record(scoring_avg_2026, birdie_pct_2026, eagle_rate_2026=None,
                       holes_2026=200, **kwargs):
    """Build a minimal par5_records entry that passes all validation gates."""
    holes = holes_2026
    total_strokes = round(scoring_avg_2026 * holes)
    birdie_holes = holes
    birdies = round(birdie_pct_2026 / 100 * birdie_holes)
    eagles = None
    eagle_holes = None
    eagle_rate = None
    if eagle_rate_2026 is not None:
        eagle_holes = holes
        eagles = round(eagle_rate_2026 * eagle_holes)
        eagle_rate = eagle_rate_2026

    return {
        "scoring_avg_2026":     scoring_avg_2026,
        "total_strokes_2026":   total_strokes,
        "total_holes_2026":     holes,
        "birdie_pct_2026":      birdie_pct_2026,
        "birdies_2026":         birdies,
        "birdie_holes_2026":    birdie_holes,
        "eagle_rate_2026":      eagle_rate,
        "eagles_2026":          eagles,
        "eagle_holes_2026":     eagle_holes,
        "scoring_avg_2025":     kwargs.get("scoring_avg_2025"),
        "total_holes_2025":     kwargs.get("total_holes_2025"),
        "birdie_pct_2025":      kwargs.get("birdie_pct_2025"),
        "birdie_holes_2025":    kwargs.get("birdie_holes_2025"),
        "eagle_rate_2025":      kwargs.get("eagle_rate_2025"),
        "eagles_2025":          None,
        "eagle_holes_2025":     None,
        "has_eagle_2026":       eagle_rate_2026 is not None,
        "has_eagle_2025":       kwargs.get("eagle_rate_2025") is not None,
        "denom_ok_scoring_2026":  True,
        "denom_ok_birdie_2026":   True,
        "denom_cross_ok_2026":    True,
        "denom_cross_delta_2026": 0,
        "eagle_denom_ok_2026":    True if eagle_rate_2026 is not None else None,
        "source_name_normalized": "test player",
    }


def test_compute_par5_composite_best_scorer_gets_highest_composite():
    """Player with best (lowest) scoring avg and highest birdie% gets highest composite."""
    players = _make_players_raw(3)
    records = {
        "pid_0": _make_par5_record(4.30, 60.0, eagle_rate_2026=0.08, holes_2026=200),  # best
        "pid_1": _make_par5_record(4.50, 50.0, eagle_rate_2026=0.04, holes_2026=200),
        "pid_2": _make_par5_record(4.70, 40.0, eagle_rate_2026=0.02, holes_2026=200),  # worst
    }
    result = compute_par5_composite_scores(players, records)
    composites = {pid: v.get("composite") for pid, v in result.items() if v.get("composite") is not None}
    assert composites["pid_0"] > composites["pid_1"] > composites["pid_2"]


def test_compute_par5_composite_ineligible_below_hole_minimum():
    """Player with < 150 par-5 holes is UNAVAILABLE."""
    players = _make_players_raw(1)
    records = {"pid_0": _make_par5_record(4.40, 55.0, holes_2026=100)}
    result = compute_par5_composite_scores(players, records)
    assert not result["pid_0"]["usable_for_badges"]
    assert result["pid_0"]["coverage_status"] == "UNAVAILABLE"


def test_compute_par5_composite_degraded_no_2026_eagle():
    """Players without 2026 eagle data get DEGRADED_NO_2026_EAGLE coverage.
    Players with eagle data but missing 2025 data get CURRENT_FULL_HISTORICAL_PARTIAL (not FULL)."""
    players = _make_players_raw(3)
    records = {
        "pid_0": _make_par5_record(4.40, 55.0, eagle_rate_2026=None, holes_2026=200),  # no eagle -> DEGRADED_NO_2026_EAGLE
        "pid_1": _make_par5_record(4.45, 53.0, eagle_rate_2026=0.05, holes_2026=200),  # has eagle, no 2025 -> CURRENT_FULL_HISTORICAL_PARTIAL
        "pid_2": _make_par5_record(4.50, 51.0, eagle_rate_2026=0.08, holes_2026=200),  # has eagle, no 2025 -> CURRENT_FULL_HISTORICAL_PARTIAL
    }
    result = compute_par5_composite_scores(players, records)
    assert result["pid_0"]["coverage_status"] == "DEGRADED_NO_2026_EAGLE"
    assert result["pid_0"]["usable_for_badges"]   # still eligible despite no eagle
    # pid_1 has 2026 eagle but no 2025 data -> CURRENT_FULL_HISTORICAL_PARTIAL (not FULL, missing 2025 components)
    assert result["pid_1"]["coverage_status"] == "CURRENT_FULL_HISTORICAL_PARTIAL"
    assert result["pid_1"]["usable_for_badges"]


def test_compute_par5_composite_missing_2025_not_disqualifying():
    """Missing 2025 data does not block a player with valid 2026 required inputs."""
    players = _make_players_raw(2)
    records = {
        "pid_0": _make_par5_record(4.40, 55.0, eagle_rate_2026=0.05, holes_2026=200),  # no 2025
        "pid_1": _make_par5_record(4.45, 53.0, eagle_rate_2026=0.04, holes_2026=200,
                                    scoring_avg_2025=4.50, birdie_pct_2025=52.0),  # has 2025
    }
    result = compute_par5_composite_scores(players, records)
    assert result["pid_0"]["usable_for_badges"]
    assert result["pid_0"]["composite"] is not None
    assert result["pid_0"]["coverage_status"] == "CURRENT_FULL_HISTORICAL_PARTIAL"


# ── Existing badge regression ──────────────────────────────────────────────────

def test_existing_badges_unchanged_when_par5_added():
    """Adding par5_scoring to badge_inputs does not affect iron_surgeon, bomber, etc."""
    # Build a stub that qualifies for iron_surgeon (existing badge) but not par5
    _inputs_like = {
        "approach_play": {
            "value": 0.8, "usable_for_badges": True, "availability": "MEASURED",
            "source_file": "app_skill_l12_sg.csv", "source_column": "trait_approach_raw", "window": "12m"
        },
        "iron_play": {
            "value": 1.0, "usable_for_badges": True, "availability": "MEASURED",
            "source_file": "app_skill_l12_sg.csv + app_skill_l12_prox.csv", "source_column": "trait_long_iron_raw", "window": "12m"
        },
        "driving_distance": {"value": None, "usable_for_badges": False, "availability": "MISSING",
                              "source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "dist_mean", "window": "L24", "rounds": 0},
        "driving_accuracy": {"value": None, "usable_for_badges": False, "availability": "MISSING",
                              "source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "acc_mean", "window": "L24", "rounds": 0},
        "putting": {"value": None, "usable_for_badges": False, "availability": "MISSING",
                    "source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "putt_mean", "window": "L24", "rounds": 0},
        "recent_form": {"value": None, "usable_for_badges": False, "availability": "INSUFFICIENT_SAMPLE",
                        "source_file": "pga_sg_query_allcourses_l6.csv + l24.csv", "source_column": "total_mean delta (L6 − L24)", "window": "L6 vs L24",
                        "l6_total_mean": None, "l6_rounds": 0, "l24_total_mean": None, "l24_rounds": 0},
        "course_history": {"detroit_starts": 0, "rounds_played": 0, "usable_for_badges": True,
                           "availability": "MEASURED", "source_file": "detroit_golf_club_CH.csv",
                           "source_column": "2021-2025 annual columns (non-null = start)", "window": "2021-2025"},
        "par5_scoring": {"value": None, "usable_for_badges": False, "availability": "UNAVAILABLE",
                         "source_file": "...", "source_column": "...", "window": "...",
                         "holes_2026": None, "component_availability": {}, "provenance": "", "unavailable_reason": "no data"},
    }
    percentiles = {"approach_play": 95, "iron_play": 91}
    result = qualify_badges(_inputs_like, POLICY, percentiles)
    badge_ids = [b["badge_id"] for b in result]
    assert "iron_surgeon" in badge_ids
    assert "par5_predator" not in badge_ids
    assert "debut" in badge_ids  # debut because 0 detroit_starts
