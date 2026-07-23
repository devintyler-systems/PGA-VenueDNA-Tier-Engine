"""Tests for engine/enrich_cards.py — pure-function coverage."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from enrich_cards import (
    normalize_name,
    load_sg,
    debut_row,
    compute_horizon,
    blend_composites,
    z_score_scale,
    tempered_softmax,
    enforce_monotonicity,
    assign_tier,
    make_cut_prob,
)


def test_normalize_name_strips_quotes():
    assert normalize_name('"Scheffler, Scottie"') == "Scheffler, Scottie"


def test_normalize_name_strips_whitespace():
    assert normalize_name("  McIlroy, Rory  ") == "McIlroy, Rory"


def test_normalize_name_empty():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_load_sg_reads_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        'player_name,rounds_played,total_mean\n"Scheffler, Scottie",20,2.5\n',
        encoding="utf-8",
    )
    result = load_sg(csv_file)
    assert result == {"Scheffler, Scottie": {"rounds": 20, "total_mean": 2.5}}


def test_load_sg_missing_file(tmp_path):
    result = load_sg(tmp_path / "nonexistent.csv")
    assert result == {}


def test_load_sg_skips_blank_names(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "player_name,rounds_played,total_mean\n,10,1.0\n", encoding="utf-8"
    )
    result = load_sg(csv_file)
    assert result == {}


def test_debut_row():
    assert debut_row() == {"rounds": 0, "total_mean": 0.0}


def test_compute_horizon_full_sample():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 20, "total_mean": 2.5}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(1.0)
    assert h["sg_sim_reg"] == pytest.approx(2.5)
    assert h["delta_fit"] == pytest.approx(0.5)


def test_compute_horizon_no_sim_rounds():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 0, "total_mean": 0.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(0.0)
    # W=0 → sg_sim_reg = base
    assert h["sg_sim_reg"] == pytest.approx(2.0)
    assert h["delta_fit"] == pytest.approx(0.0)


def test_compute_horizon_partial_sample():
    base = {"rounds": 20, "total_mean": 1.0}
    sim = {"rounds": 10, "total_mean": 3.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(0.5)
    assert h["sg_sim_reg"] == pytest.approx(0.5 * 3.0 + 0.5 * 1.0)  # 2.0
    assert h["delta_fit"] == pytest.approx(2.0 - 1.0)  # 1.0


def test_compute_horizon_caps_w_at_one():
    base = {"rounds": 20, "total_mean": 0.0}
    sim = {"rounds": 40, "total_mean": 1.0}
    h = compute_horizon(base, sim)
    assert h["W"] == pytest.approx(1.0)


def test_blend_composites_weights():
    b6, b12, b24 = 1.0, 2.0, 3.0
    d6, d12, d24 = 0.1, 0.2, 0.3
    sg_base, delta = blend_composites(b6, b12, b24, d6, d12, d24)
    expected_base = 0.20 * 1.0 + 0.30 * 2.0 + 0.50 * 3.0
    expected_delta = 0.50 * 0.1 + 0.30 * 0.2 + 0.20 * 0.3
    assert sg_base == pytest.approx(expected_base)
    assert delta == pytest.approx(expected_delta)


def test_blend_composites_clamps_positive_delta():
    # Extreme positive delta → clamped to +0.50
    sg_base, delta = blend_composites(0, 0, 0, 1.0, 1.0, 1.0)
    assert delta == pytest.approx(0.50)


def test_blend_composites_clamps_negative_delta():
    # Extreme negative delta → clamped to -0.50
    sg_base, delta = blend_composites(0, 0, 0, -1.0, -1.0, -1.0)
    assert delta == pytest.approx(-0.50)


def test_z_score_scale_mean_and_spread():
    values = [0.0, 1.0, 2.0]
    scaled = z_score_scale(values)
    assert len(scaled) == 3
    # Middle value (mean of field) should be ~50
    assert scaled[1] == pytest.approx(50.0, abs=0.1)
    assert all(0.0 <= v <= 100.0 for v in scaled)


def test_z_score_scale_single_value():
    # Single value: sd=1.0 fallback → returns mean=50.0
    scaled = z_score_scale([5.0])
    assert scaled == [50.0]


def test_z_score_scale_preserves_order():
    values = [3.0, 1.0, 2.0]
    scaled = z_score_scale(values)
    assert scaled[0] > scaled[2] > scaled[1]


def test_z_score_scale_empty():
    assert z_score_scale([]) == []


def test_tempered_softmax_ordering():
    scores = [2.0, 1.0, 0.0]
    probs = tempered_softmax(scores, T=3.5, n_positions=1)
    assert len(probs) == 3
    assert probs[0] > probs[1] > probs[2]


def test_tempered_softmax_cap():
    # One dominant player should never exceed 99.9
    scores = [100.0, 0.0, 0.0]
    probs = tempered_softmax(scores, T=3.5, n_positions=1)
    assert all(p <= 99.9 for p in probs)


def test_tempered_softmax_no_negatives():
    scores = [-1.0, -2.0, -3.0]
    probs = tempered_softmax(scores, T=5.0, n_positions=5)
    assert all(p >= 0.0 for p in probs)


def test_enforce_monotonicity_clamps_cascade():
    p = {"winPct": 20.0, "top5Pct": 15.0, "top10Pct": 10.0, "top20Pct": 5.0}
    enforce_monotonicity(p)
    assert p["top5Pct"] >= p["winPct"]
    assert p["top10Pct"] >= p["top5Pct"]
    assert p["top20Pct"] >= p["top10Pct"]


def test_enforce_monotonicity_already_valid():
    p = {"winPct": 5.0, "top5Pct": 20.0, "top10Pct": 40.0, "top20Pct": 70.0}
    enforce_monotonicity(p)
    assert p == {"winPct": 5.0, "top5Pct": 20.0, "top10Pct": 40.0, "top20Pct": 70.0}


def test_assign_tier_boundaries():
    assert assign_tier(1) == "T1"
    assert assign_tier(5) == "T1"
    assert assign_tier(6) == "T2"
    assert assign_tier(12) == "T2"
    assert assign_tier(13) == "T3"
    assert assign_tier(25) == "T3"
    assert assign_tier(26) == "T4"
    assert assign_tier(40) == "T4"
    assert assign_tier(41) == "T5"
    assert assign_tier(200) == "T5"


def test_make_cut_prob_lower_clamp():
    assert make_cut_prob(0.0) == pytest.approx(20.0)


def test_make_cut_prob_upper_clamp():
    assert make_cut_prob(80.0) == pytest.approx(98.0)


def test_make_cut_prob_midrange():
    # 50 * 1.25 + 10 = 72.5
    assert make_cut_prob(50.0) == pytest.approx(72.5)
