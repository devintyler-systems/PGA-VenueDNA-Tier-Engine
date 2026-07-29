"""Tests for the badge emission release gate validator."""
import importlib.util, json
from pathlib import Path
import pytest

_VAL_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_rocket_classic" / "output" / "validate_badge_emission.py"
)
_spec = importlib.util.spec_from_file_location("badge_validator", _VAL_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
validate_payload = _mod.validate_payload

_POLICY = [
    {"badge_id": "debut",       "label": "Debut",       "display_order": 8,
     "required_trait_ids": [], "threshold": {"venue_starts_max": 0}, "exclusions": []},
    {"badge_id": "iron_surgeon","label": "Iron Surgeon","display_order": 1,
     "required_trait_ids": ["approach_play","iron_play"],
     "threshold": {"field_percentile_min": 80}, "exclusions": []},
]

def _player(pid="1", depth="FULL", badges=None):
    return {"player_id": pid, "data_depth": depth,
            "badges": badges if badges is not None else [
                {"badge_id": "debut", "qualification_reason": "No prior starts. (source: detroit_golf_club_CH.csv)"}
            ]}

def _payload(players=None):
    return {"players": players or [_player()]}


# Gate 1 — zero badges across all scored players
def test_g1_zero_badges_across_scored_players_fails():
    errors = validate_payload(_payload([_player(badges=[])]), _POLICY)
    assert any("[G1]" in e for e in errors)

def test_g1_does_not_fire_for_unscored_only():
    errors = validate_payload(_payload([_player(depth="UNSCORED", badges=[])]), _POLICY)
    assert not any("[G1]" in e for e in errors)

def test_g1_passes_when_some_badge_present():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G1]" in e for e in errors)


# Gate 2 — badges field structure
def test_g2_missing_badges_field_fails():
    p = {"player_id": "1", "data_depth": "FULL"}
    errors = validate_payload(_payload([p]), _POLICY)
    assert any("[G2]" in e for e in errors)

def test_g2_badges_not_list_fails():
    errors = validate_payload(_payload([_player(badges="debut")]), _POLICY)
    assert any("[G2]" in e for e in errors)


# Gate 3 — unknown badge_id
def test_g3_unknown_badge_id_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"invented","qualification_reason":"x"}])]), _POLICY)
    assert any("[G3]" in e for e in errors)

def test_g3_known_badge_id_passes():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G3]" in e for e in errors)


# Gate 4 — empty qualification_reason
def test_g4_empty_reason_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"debut","qualification_reason":""}])]), _POLICY)
    assert any("[G4]" in e for e in errors)

def test_g4_missing_reason_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"debut"}])]), _POLICY)
    assert any("[G4]" in e for e in errors)


# Gate 5 — duplicate policy badge_ids
def test_g5_duplicate_policy_id_fails():
    dup = _POLICY + [_POLICY[0]]
    errors = validate_payload(_payload([_player()]), dup)
    assert any("[G5]" in e for e in errors)

def test_g5_unique_policy_passes():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G5]" in e for e in errors)


# UNSCORED players are excluded from all per-player gates
def test_unscored_player_excluded_from_per_player_gates():
    p = {"player_id": "2", "data_depth": "UNSCORED"}  # no badges field at all
    errors = validate_payload(_payload([_player(), p]), _POLICY)
    # G2 must NOT fire for the UNSCORED player
    assert not any("player_id=2" in e and "[G2]" in e for e in errors)
