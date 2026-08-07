"""Tests for engine/venue_config.py -- the venue-configuration schema and
registry introduced in Phase 4.3.

These tests validate config load and basic invariants only. They do not
exercise engine/enrich_cards.py's live producer pipeline (see
tests/test_enrich_cards.py for that) and make no assertion about
engine/venuedna_scoring.py's canonical formula, which this module has no
effect on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from venue_config import (  # noqa: E402
    AntiPatternThresholds,
    DebutFramework,
    NarrativeThresholds,
    SEDGEFIELD_COUNTRY_CLUB,
    TPC_TWIN_CITIES,
    TraitWeights,
    VARIANCE_CLASSES,
    VenueConfig,
    VenueConfigError,
    load_venue_config,
)


# ── Registry lookups ─────────────────────────────────────────────────────

def test_load_venue_config_tpc_twin_cities():
    config = load_venue_config("tpc_twin_cities")
    assert config is TPC_TWIN_CITIES
    assert config.venue_slug == "tpc_twin_cities"
    assert config.status == "ACTIVE"


def test_load_venue_config_sedgefield():
    config = load_venue_config("sedgefield_country_club")
    assert config is SEDGEFIELD_COUNTRY_CLUB
    assert config.venue_slug == "sedgefield_country_club"
    assert config.status == "RECONSTRUCTED"


def test_load_venue_config_unknown_venue_raises():
    with pytest.raises(VenueConfigError):
        load_venue_config("2026_wyndham_championship")


def test_load_venue_config_unknown_venue_error_lists_known_venues():
    with pytest.raises(VenueConfigError) as exc_info:
        load_venue_config("not_a_real_venue")
    message = str(exc_info.value)
    assert "sedgefield_country_club" in message
    assert "tpc_twin_cities" in message


# ── TPC Twin Cities values match the pre-Phase-4.3 hardcoded constants ────

def test_tpc_trait_weights_match_enrich_cards_constants():
    import enrich_cards

    w = TPC_TWIN_CITIES.trait_weights
    assert w.approach == enrich_cards.VW_APPROACH == pytest.approx(0.40)
    assert w.long_iron == enrich_cards.VW_LONG_IRON == pytest.approx(0.25)
    assert w.ott == enrich_cards.VW_OTT == pytest.approx(0.20)
    assert w.ch == enrich_cards.VW_CH == pytest.approx(0.10)
    assert w.form == enrich_cards.VW_FORM == pytest.approx(0.05)


def test_tpc_anti_pattern_thresholds_match_enrich_cards_constants():
    import enrich_cards

    t = TPC_TWIN_CITIES.anti_pattern_thresholds
    assert t.bomb_dist_thresh == enrich_cards.BOMB_DIST_THRESH
    assert t.bomb_acc_thresh == enrich_cards.BOMB_ACC_THRESH
    assert t.sg_app_thresh == enrich_cards.SG_APP_THRESH
    assert t.sg_sum_thresh == enrich_cards.SG_SUM_THRESH
    assert t.penalty_bomber == enrich_cards.PENALTY_BOMBER
    assert t.penalty_sg_dep == enrich_cards.PENALTY_SG_DEP


def test_tpc_debut_haircut_matches_enrich_cards_constant():
    import enrich_cards

    assert TPC_TWIN_CITIES.debut_framework.ch_haircut == enrich_cards.DEBUT_CH_HAIRCUT


def test_tpc_narrative_thresholds_match_enrich_cards_constants():
    import enrich_cards

    n = TPC_TWIN_CITIES.narrative_thresholds
    assert n.elite_app == enrich_cards.THRESH_ELITE_APP
    assert n.strong_app == enrich_cards.THRESH_STRONG_APP
    assert n.venue_fit == enrich_cards.THRESH_VENUE_FIT
    assert n.ctrl_power == enrich_cards.THRESH_CTRL_POWER
    assert n.course_ped == enrich_cards.THRESH_COURSE_PED
    assert n.hot_form == enrich_cards.THRESH_HOT_FORM
    assert n.app_deficit == enrich_cards.THRESH_APP_DEFICIT
    assert n.li_gap == enrich_cards.THRESH_LI_GAP


# ── Sedgefield is structurally valid but distinct from TPC ────────────────

def test_sedgefield_is_structurally_valid_venue_config():
    assert isinstance(SEDGEFIELD_COUNTRY_CLUB, VenueConfig)
    assert SEDGEFIELD_COUNTRY_CLUB.variance_class in VARIANCE_CLASSES


def test_sedgefield_trait_weights_differ_from_tpc():
    assert SEDGEFIELD_COUNTRY_CLUB.trait_weights != TPC_TWIN_CITIES.trait_weights


def test_sedgefield_not_reachable_through_capability_gate():
    """Sedgefield has a valid VenueConfig but is not yet admitted by
    engine/event_context.py's require_supported_context() capability
    gate -- registering a VenueConfig does not, by itself, make a venue
    runnable."""
    import enrich_cards

    assert enrich_cards.SUPPORTED_VENUE_SLUG != "sedgefield_country_club"


# ── Schema validation ──────────────────────────────────────────────────────

def _valid_trait_weights(**overrides):
    defaults = dict(approach=0.40, long_iron=0.25, ott=0.20, ch=0.10, form=0.05)
    defaults.update(overrides)
    return TraitWeights(**defaults)


def _valid_anti_pattern_thresholds(**overrides):
    defaults = dict(
        bomb_dist_thresh=0.15, bomb_acc_thresh=-0.05,
        sg_app_thresh=0.20, sg_sum_thresh=1.00,
        penalty_bomber=0.92, penalty_sg_dep=0.90,
    )
    defaults.update(overrides)
    return AntiPatternThresholds(**defaults)


def _valid_narrative_thresholds(**overrides):
    defaults = dict(
        elite_app=1.00, strong_app=0.60, venue_fit=0.15, ctrl_power=0.60,
        course_ped=0.04, hot_form=1.50, app_deficit=0.00, li_gap=-0.05,
    )
    defaults.update(overrides)
    return NarrativeThresholds(**defaults)


def _valid_venue_config(**overrides):
    defaults = dict(
        venue_slug="test_venue",
        venue_name="Test Venue",
        trait_weights=_valid_trait_weights(),
        anti_pattern_thresholds=_valid_anti_pattern_thresholds(),
        debut_framework=DebutFramework(ch_haircut=-0.20),
        variance_class="MEDIUM",
        narrative_thresholds=_valid_narrative_thresholds(),
    )
    defaults.update(overrides)
    return VenueConfig(**defaults)


def test_valid_venue_config_constructs_without_error():
    config = _valid_venue_config()
    assert config.venue_slug == "test_venue"
    assert config.status == "ACTIVE"


def test_trait_weight_out_of_range_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(trait_weights=_valid_trait_weights(approach=1.5))


def test_trait_weight_negative_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(trait_weights=_valid_trait_weights(approach=-0.1))


def test_trait_weight_sum_too_low_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(trait_weights=_valid_trait_weights(
            approach=0.05, long_iron=0.05, ott=0.05, ch=0.05, form=0.05,
        ))


def test_trait_weight_non_numeric_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(trait_weights=_valid_trait_weights(approach="0.4"))


def test_trait_weight_bool_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(trait_weights=_valid_trait_weights(approach=True))


def test_penalty_multiplier_out_of_range_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(
            anti_pattern_thresholds=_valid_anti_pattern_thresholds(penalty_bomber=1.5)
        )


def test_penalty_multiplier_too_low_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(
            anti_pattern_thresholds=_valid_anti_pattern_thresholds(penalty_bomber=0.1)
        )


def test_debut_haircut_positive_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(debut_framework=DebutFramework(ch_haircut=0.1))


def test_debut_haircut_out_of_range_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(debut_framework=DebutFramework(ch_haircut=-2.0))


def test_narrative_elite_app_must_exceed_strong_app():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(narrative_thresholds=_valid_narrative_thresholds(
            elite_app=0.5, strong_app=0.6,
        ))


def test_invalid_variance_class_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(variance_class="EXTREME")


def test_invalid_status_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(status="DRAFT")


def test_empty_venue_slug_rejected():
    with pytest.raises(VenueConfigError):
        _valid_venue_config(venue_slug="")


def test_venue_config_is_frozen():
    config = _valid_venue_config()
    with pytest.raises(Exception):
        config.venue_slug = "other_venue"
