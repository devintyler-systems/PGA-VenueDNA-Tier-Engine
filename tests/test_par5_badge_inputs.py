"""Tests for par-5 badge input loading and name resolution."""
import importlib.util, copy
from pathlib import Path
import pytest

_ENGINE_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_rocket_classic" / "engine" / "enrich_cards.py"
)
_spec = importlib.util.spec_from_file_location("rocket_engine", _ENGINE_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

build_par5_name_lookup = _mod.build_par5_name_lookup
normalize_name         = _mod.normalize_name


# ── Name lookup tests ──────────────────────────────────────────────────────────

def test_knapp_jake_resolves():
    """Payload 'Knapp, Jake' -> lookup key 'jake knapp' -> matches CSV 'Jake Knapp'."""
    players = [{"player_name": "Knapp, Jake", "player_id": "pid_knapp"}]
    lookup = build_par5_name_lookup(players)
    assert lookup.get(normalize_name("Jake Knapp")) == "pid_knapp"


def test_hojgaard_payload_name_resolves():
    """Payload 'Hojgaard, Nicolai' -> lookup key 'nicolai hojgaard' -> matches
    CSV 'Nicolai Hojgaard' (already diacritic-stripped in CSV data for this event).
    Note: normalize_name does NOT strip ø (LATIN SMALL LETTER O WITH STROKE) — it
    is a precomposed character, not a combining mark. The CSV data must already
    have diacritics stripped to match the payload."""
    players = [{"player_name": "Hojgaard, Nicolai", "player_id": "pid_nh"}]
    lookup = build_par5_name_lookup(players)
    # CSV already stored with diacritics stripped: "Nicolai Hojgaard"
    csv_normalized = normalize_name("Nicolai Hojgaard")
    assert csv_normalized == "nicolai hojgaard"
    assert lookup.get(csv_normalized) == "pid_nh"


def test_aberg_diacritic_stripping():
    """CSV 'Ludvig Åberg' normalizes to 'ludvig aberg'; payload 'Aberg, Ludvig' must match."""
    # Payload already has diacritic stripped (stored as "Aberg, Ludvig")
    players = [{"player_name": "Aberg, Ludvig", "player_id": "pid_la"}]
    lookup = build_par5_name_lookup(players)
    csv_normalized = normalize_name("Ludvig Åberg")
    assert csv_normalized == "ludvig aberg"
    assert lookup.get(csv_normalized) == "pid_la"


def test_koivun_does_not_resolve_suber():
    """'Koivun, Jackson' generates key 'jackson koivun'; CSV 'Jackson Suber' normalizes
    to 'jackson suber' — these are different strings, so no match."""
    players = [{"player_name": "Koivun, Jackson", "player_id": "pid_koivun"}]
    lookup = build_par5_name_lookup(players)
    suber_key = normalize_name("Jackson Suber")
    assert suber_key == "jackson suber"
    assert lookup.get(suber_key) is None   # UNMATCHED


def test_no_par5_source_row_matches_two_event_players():
    """If two event players somehow generate the same normalized first-last key,
    the lookup marks that key AMBIGUOUS (None), not matched to either."""
    # Construct two players with equivalent normalized first-last
    players = [
        {"player_name": "Smith, Jordan", "player_id": "pid_js1"},
        {"player_name": "Smith, Jordan", "player_id": "pid_js2"},  # duplicate
    ]
    lookup = build_par5_name_lookup(players)
    key = normalize_name("Jordan Smith")
    # Both players produce the same key -> AMBIGUOUS
    assert lookup.get(key) is None


def test_ambiguous_key_is_not_matched():
    """An AMBIGUOUS key (value=None) must not resolve to any player."""
    players = [
        {"player_name": "Doe, John", "player_id": "pid1"},
        {"player_name": "Doe, John", "player_id": "pid2"},
    ]
    lookup = build_par5_name_lookup(players)
    key = normalize_name("John Doe")
    resolved = lookup.get(key)
    assert resolved is None
