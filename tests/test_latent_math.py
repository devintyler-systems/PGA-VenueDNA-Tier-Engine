"""
tests/test_latent_math.py — Deterministic unit tests for VenueDNA latent math.

Run: pytest tests/test_latent_math.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.latent_model import (
    BRIE_Z_BETA_1,
    BRIE_Z_BETA_2,
    ValuationAnomalyException,
    classify_wave_from_time,
    compute_brie_z,
    inject_wave_scalar,
    verify_monotonicity,
    zscore_normalize,
)


# ── BRIE-Z formula ────────────────────────────────────────────────────────────

class TestBrieZFormula:
    def test_exact_coefficient_weights(self):
        """0.6 × fw_sg + 0.4 × psa — exact linear combination."""
        fw, psa = 0.10, 0.05
        expected = BRIE_Z_BETA_1 * fw + BRIE_Z_BETA_2 * psa
        assert abs(compute_brie_z(fw, psa) - expected) < 1e-9

    def test_course_penalty_subtracted(self):
        """Rough penalty lowers BRIE-Z by exactly the penalty value."""
        base      = compute_brie_z(0.05, 0.02, 0.0)
        penalised = compute_brie_z(0.05, 0.02, 0.03)
        assert penalised < base
        assert abs(base - penalised - 0.03) < 1e-9

    def test_zero_inputs_zero_output(self):
        assert compute_brie_z(0.0, 0.0, 0.0) == 0.0

    def test_negative_fw_sg_reduces_score(self):
        assert compute_brie_z(-0.05, 0.0) < compute_brie_z(0.05, 0.0)

    def test_beta_weights_sum_to_unity(self):
        """Ensures no hidden scaling bias in the formula weights."""
        assert abs(BRIE_Z_BETA_1 + BRIE_Z_BETA_2 - 1.0) < 1e-9

    def test_higher_psa_improves_score(self):
        low  = compute_brie_z(0.0, -0.05)
        high = compute_brie_z(0.0,  0.05)
        assert high > low

    def test_large_penalty_can_invert_sign(self):
        """A very stiff course penalty should drive BRIE-Z negative."""
        assert compute_brie_z(0.05, 0.05, course_rough_penalty=1.0) < 0.0


# ── Wave time classification ───────────────────────────────────────────────────

class TestClassifyWaveFromTime:
    def test_morning_strings_are_early_late(self):
        assert classify_wave_from_time("07:30")    == "early_late"
        assert classify_wave_from_time("8:00 AM")  == "early_late"
        assert classify_wave_from_time("11:59")    == "early_late"
        assert classify_wave_from_time("09:00:00") == "early_late"

    def test_noon_and_afternoon_are_late_early(self):
        assert classify_wave_from_time("12:00")    == "late_early"
        assert classify_wave_from_time("13:30")    == "late_early"
        assert classify_wave_from_time("2:05 PM")  == "late_early"
        assert classify_wave_from_time("14:00")    == "late_early"

    def test_tbd_returns_unknown(self):
        assert classify_wave_from_time("TBD")  == "unknown"
        assert classify_wave_from_time("")     == "unknown"
        assert classify_wave_from_time("N/A")  == "unknown"

    def test_twelve_pm_noon_is_late_early(self):
        assert classify_wave_from_time("12:00 PM") == "late_early"

    def test_midnight_twelve_am_is_early_late(self):
        assert classify_wave_from_time("12:00 AM") == "early_late"


# ── Wave scalar injection ─────────────────────────────────────────────────────

class TestInjectWaveScalar:
    def _base_df(self, keys: list[str]) -> pd.DataFrame:
        return pd.DataFrame([{"key": k} for k in keys])

    def test_none_path_clamps_all_to_zero(self):
        df = self._base_df(["scheffler_scottie", "mcilroy_rory"])
        result = inject_wave_scalar(df, pairings_path=None)
        assert (result["wave_bonus"] == 0.0).all()

    def test_missing_file_clamps_all_to_zero(self, tmp_path):
        df = self._base_df(["scheffler_scottie"])
        result = inject_wave_scalar(df, pairings_path=tmp_path / "nope.csv")
        assert (result["wave_bonus"] == 0.0).all()

    def test_empty_file_clamps_all_to_zero(self, tmp_path):
        p = tmp_path / "r1_pairings.csv"
        p.write_text("player_name,tee_time\n")
        df = self._base_df(["scheffler_scottie"])
        result = inject_wave_scalar(df, pairings_path=p)
        assert (result["wave_bonus"] == 0.0).all()

    def test_explicit_wave_column_respected(self, tmp_path):
        p = tmp_path / "r1_pairings.csv"
        p.write_text(
            "player_name,tee_time,wave\n"
            "McIlroy, Rory,07:30,early_late\n"
            "Scheffler, Scottie,13:00,late_early\n"
        )
        df = self._base_df(["mcilroy_rory", "scheffler_scottie"])
        result = inject_wave_scalar(
            df, pairings_path=p, favored_wave="late_early", bonus=0.15
        )
        scheffler = result[result["key"] == "scheffler_scottie"].iloc[0]
        mcilroy   = result[result["key"] == "mcilroy_rory"].iloc[0]
        assert scheffler["wave_bonus"] == 0.15
        assert mcilroy["wave_bonus"]   == 0.0

    def test_unfavoured_wave_gets_zero(self, tmp_path):
        p = tmp_path / "r1_pairings.csv"
        p.write_text(
            "player_name,wave\n"
            "Scheffler, Scottie,early_late\n"
        )
        df = self._base_df(["scheffler_scottie"])
        result = inject_wave_scalar(
            df, pairings_path=p, favored_wave="late_early", bonus=0.15
        )
        assert result.iloc[0]["wave_bonus"] == 0.0

    def test_invalid_favored_wave_defaults_to_late_early(self, tmp_path):
        p = tmp_path / "r1_pairings.csv"
        p.write_text(
            "player_name,wave\n"
            "Scheffler, Scottie,late_early\n"
        )
        df = self._base_df(["scheffler_scottie"])
        # "unknown_wave" is not a valid designation — should silently default
        result = inject_wave_scalar(
            df, pairings_path=p, favored_wave="unknown_wave", bonus=0.15
        )
        # After default fallback to late_early, Scheffler (late_early) gets bonus
        assert result.iloc[0]["wave_bonus"] == 0.15

    def test_wave_designation_column_populated(self, tmp_path):
        p = tmp_path / "r1_pairings.csv"
        p.write_text(
            "player_name,wave\n"
            "McIlroy, Rory,early_late\n"
        )
        df = self._base_df(["mcilroy_rory"])
        result = inject_wave_scalar(df, pairings_path=p)
        assert result.iloc[0]["wave_designation"] == "early_late"


# ── Monotonicity validation ───────────────────────────────────────────────────

class TestVerifyMonotonicity:
    def _player(
        self,
        make_cut: float,
        top20: float,
        top10: float,
        top5: float,
        win: float,
        pid: str = "P001",
    ) -> dict:
        return {
            "player_id":   pid,
            "first_name":  "Test",
            "last_name":   "Player",
            "make_cut_prob": make_cut,
            "top20_prob":  top20,
            "top10_prob":  top10,
            "top5_prob":   top5,
            "win_prob":    win,
        }

    def test_clean_ordering_passes(self):
        verify_monotonicity([self._player(80.0, 45.0, 25.0, 12.0, 4.0)])

    def test_equal_adjacent_values_pass(self):
        """Equal values at a transition are valid (>= not strict >)."""
        verify_monotonicity([self._player(50.0, 30.0, 30.0, 10.0, 5.0)])

    def test_win_gt_top5_raises(self):
        with pytest.raises(ValuationAnomalyException) as exc_info:
            verify_monotonicity([self._player(80.0, 45.0, 25.0, 5.0, 8.0)])
        assert "win" in str(exc_info.value).lower()

    def test_top5_gt_top10_raises(self):
        with pytest.raises(ValuationAnomalyException):
            verify_monotonicity([self._player(80.0, 45.0, 20.0, 30.0, 4.0)])

    def test_top10_gt_top20_raises(self):
        with pytest.raises(ValuationAnomalyException):
            verify_monotonicity([self._player(80.0, 20.0, 40.0, 10.0, 3.0)])

    def test_top20_gt_make_cut_raises(self):
        with pytest.raises(ValuationAnomalyException):
            verify_monotonicity([self._player(30.0, 45.0, 25.0, 12.0, 4.0)])

    def test_single_violator_in_large_field_fires(self):
        players = [
            self._player(80.0, 45.0, 25.0, 12.0, 4.0, "P001"),   # valid
            self._player(80.0, 45.0, 25.0,  5.0, 8.0, "P002"),   # win > top5
            self._player(75.0, 40.0, 20.0, 10.0, 3.0, "P003"),   # valid
        ]
        with pytest.raises(ValuationAnomalyException) as exc_info:
            verify_monotonicity(players)
        assert "P002" in str(exc_info.value)

    def test_none_probs_skipped_gracefully(self):
        players = [{
            "player_id": "P001", "first_name": "T", "last_name": "P",
            "make_cut_prob": None, "top20_prob": None,
            "top10_prob": None, "top5_prob": None, "win_prob": None,
        }]
        verify_monotonicity(players)  # must not raise

    def test_alias_fields_accepted(self):
        """Payload using win_pct / top5_pct / top10_pct alias names is validated."""
        players = [{
            "player_id": "P001", "first_name": "T", "last_name": "P",
            "make_cut_prob": 80.0,
            "top20_pct":    45.0,
            "top10_pct":    25.0,
            "top5_pct":     12.0,
            "win_pct":       4.0,
        }]
        verify_monotonicity(players)

    def test_alias_violation_detected(self):
        """Violations via alias field names are caught too."""
        players = [{
            "player_id": "P001", "first_name": "T", "last_name": "P",
            "make_cut_prob": 80.0,
            "top20_pct":    45.0,
            "top10_pct":    25.0,
            "top5_pct":      3.0,
            "win_pct":       6.0,   # win > top5 — violation
        }]
        with pytest.raises(ValuationAnomalyException):
            verify_monotonicity(players)

    def test_empty_list_passes(self):
        verify_monotonicity([])


# ── Z-score normalisation ─────────────────────────────────────────────────────

class TestZscoreNormalize:
    def test_output_clamped_0_to_100(self):
        s = pd.Series([0.0, 0.05, 0.1, -0.05, -0.1])
        result = zscore_normalize(s)
        assert (result >= 0.0).all() and (result <= 100.0).all()

    def test_mean_near_target(self):
        s = pd.Series(range(100), dtype=float)
        result = zscore_normalize(s, target_mean=50.0, target_std=15.0)
        assert abs(result.mean() - 50.0) < 2.0

    def test_empty_series_returns_empty(self):
        s = pd.Series([], dtype=float)
        result = zscore_normalize(s, target_mean=50.0)
        assert len(result) == 0

    def test_constant_series_returns_target_mean(self):
        s = pd.Series([0.05] * 10)
        result = zscore_normalize(s, target_mean=50.0)
        assert (result == 50.0).all()

    def test_nan_fills_to_target_mean(self):
        s = pd.Series([1.0, 2.0, float("nan"), 3.0])
        result = zscore_normalize(s, target_mean=50.0)
        assert not result.isna().any()
