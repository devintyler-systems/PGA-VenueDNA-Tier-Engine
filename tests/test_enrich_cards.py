"""Tests for engine/enrich_cards.py — pure-function coverage."""
import csv
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

import enrich_cards
from enrich_cards import (
    normalize_name,
    load_sg_csv,
    debut_row,
    compute_horizon,
    make_composites,
    z_score_scale,
    tempered_softmax,
    enforce_monotonicity,
    assign_tier,
    make_cut_prob,
)
from identity_resolver import SourceRow
from identity_resolver import normalize_name as _canonical_normalize_name


def test_normalize_name_strips_quotes():
    assert normalize_name('"Scheffler, Scottie"') == "scheffler, scottie"


def test_normalize_name_strips_whitespace():
    assert normalize_name("  McIlroy, Rory  ") == "mcilroy, rory"


def test_normalize_name_empty():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_load_sg_csv_reads_csv(tmp_path):
    """load_sg_csv is row-preserving -- it returns a list[SourceRow], one
    entry per CSV data row, not a name-keyed dict (Correction 3)."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        'player_name,rounds_played,total_mean\n"Scheffler, Scottie",20,2.5\n',
        encoding="utf-8",
    )
    result = load_sg_csv(csv_file)
    assert len(result) == 1
    assert result[0].source_name == "Scheffler, Scottie"
    assert result[0].dg_id is None
    assert result[0].payload == {"rounds": 20, "total_mean": 2.5}
    assert result[0].row_number == 1


def test_load_sg_csv_missing_file(tmp_path):
    result = load_sg_csv(tmp_path / "nonexistent.csv")
    assert result == []


def test_load_sg_csv_skips_blank_names(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "player_name,rounds_played,total_mean\n,10,1.0\n", encoding="utf-8"
    )
    result = load_sg_csv(csv_file)
    assert result == []


def test_load_sg_csv_preserves_duplicate_rows(tmp_path):
    """Two rows sharing the same raw name must both reach the caller intact
    -- the loader must never collapse duplicates before identity resolution
    (Correction 3 / Finding C)."""
    csv_file = tmp_path / "test.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["player_name", "rounds_played", "total_mean"])
        w.writerow(["Doe, John", "20", "2.5"])
        w.writerow(["Doe, John", "15", "1.0"])
    result = load_sg_csv(csv_file)
    assert len(result) == 2
    assert [r.source_name for r in result] == ["Doe, John", "Doe, John"]
    assert [r.payload["total_mean"] for r in result] == [2.5, 1.0]
    assert [r.row_number for r in result] == [1, 2]


def test_debut_row():
    assert debut_row() == {"rounds": 0, "total_mean": 0.0}


def test_compute_horizon_full_sample():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 20, "total_mean": 2.5}
    h = compute_horizon(base, sim)
    assert h["delta_fit"] == pytest.approx(0.5)


def test_compute_horizon_no_sim_rounds():
    base = {"rounds": 20, "total_mean": 2.0}
    sim = {"rounds": 0, "total_mean": 0.0}
    h = compute_horizon(base, sim)
    # W=0 → sg_sim_reg = base → delta_fit = 0
    assert h["delta_fit"] == pytest.approx(0.0)


def test_compute_horizon_partial_sample():
    base = {"rounds": 20, "total_mean": 1.0}
    sim = {"rounds": 10, "total_mean": 3.0}
    h = compute_horizon(base, sim)
    # W=0.5 → sg_sim_reg = 0.5*3 + 0.5*1 = 2.0 → delta_fit = 1.0
    assert h["delta_fit"] == pytest.approx(1.0)


def test_compute_horizon_caps_w_at_one():
    base = {"rounds": 20, "total_mean": 0.0}
    sim = {"rounds": 40, "total_mean": 1.0}
    h = compute_horizon(base, sim)
    # W capped at 1 → delta_fit = 1.0 - 0.0
    assert h["delta_fit"] == pytest.approx(1.0)


def _make_horizons(b6, b12, b24, d6, d12, d24):
    """Build all_resolved / sim_resolved dicts for make_composites tests.
    With sim rounds=20 W=1, so delta_fit == sim.total_mean - base.total_mean."""
    all_r = {
        "6m":  {"rounds": 20, "total_mean": b6},
        "12m": {"rounds": 20, "total_mean": b12},
        "24m": {"rounds": 20, "total_mean": b24},
    }
    sim_r = {
        "6m":  {"rounds": 20, "total_mean": b6 + d6},
        "12m": {"rounds": 20, "total_mean": b12 + d12},
        "24m": {"rounds": 20, "total_mean": b24 + d24},
    }
    return all_r, sim_r


def test_make_composites_weights():
    all_r, sim_r = _make_horizons(1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
    sg_base, _, delta = make_composites(all_r, sim_r)
    expected_base = 0.20 * 1.0 + 0.30 * 2.0 + 0.50 * 3.0
    expected_delta = 0.50 * 0.1 + 0.30 * 0.2 + 0.20 * 0.3
    assert sg_base == pytest.approx(expected_base)
    assert delta == pytest.approx(expected_delta)


def test_make_composites_clamps_positive_delta():
    all_r, sim_r = _make_horizons(0, 0, 0, 5.0, 5.0, 5.0)
    _, _, delta = make_composites(all_r, sim_r)
    assert delta == pytest.approx(0.50)


def test_make_composites_clamps_negative_delta():
    all_r, sim_r = _make_horizons(0, 0, 0, -5.0, -5.0, -5.0)
    _, _, delta = make_composites(all_r, sim_r)
    assert delta == pytest.approx(-0.50)


def test_z_score_scale_mean_and_spread():
    # field_stats excludes 0.0 as sentinel; use non-zero values so mean = middle
    values = [1.0, 2.0, 3.0]
    scaled = z_score_scale(values)
    assert len(scaled) == 3
    # Middle value (mean of field) should be exactly 50
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
    probs = tempered_softmax(scores, T=3.5, n_pos=1)
    assert len(probs) == 3
    assert probs[0] > probs[1] > probs[2]


def test_tempered_softmax_cap():
    # One dominant player should never exceed 99.9
    scores = [100.0, 0.0, 0.0]
    probs = tempered_softmax(scores, T=3.5, n_pos=1)
    assert all(p <= 99.9 for p in probs)


def test_tempered_softmax_no_negatives():
    scores = [-1.0, -2.0, -3.0]
    probs = tempered_softmax(scores, T=5.0, n_pos=5)
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


# ── Identity integration (synthetic temporary events only) ─────────────────

class SyntheticEvent:
    """Builds a minimal, valid synthetic event input/ tree under tmp_path.
    Never touches events/2026_Finished_Events/ or any archived directory."""

    SIX_SOURCE_FILES = [
        "pga_sg_query_allcourses_l6.csv", "pga_sg_query_allcourses_l12.csv",
        "pga_sg_query_allcourses_l24.csv", "pga_sg_query_3Mopen_similar_l6.csv",
        "pga_sg_query_3Mopen_similar_l12.csv", "pga_sg_query_3Mopen_similar_l24.csv",
    ]

    def __init__(self, tmp_path: Path, event_slug: str = "synthetic_event") -> None:
        self.root = tmp_path
        self.event_slug = event_slug
        self.input_dir = tmp_path / "events" / event_slug / "input"
        self.input_dir.mkdir(parents=True)

    def _write(self, name: str, header: list[str], rows: list[list[str]]) -> None:
        with (self.input_dir / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    def write_all(self, field_rows: list[tuple[str, str]]) -> None:
        """field_rows: list of (player_name, dg_id) tuples."""
        self._write("pga_field.csv", ["player_name", "dg_id"], [list(r) for r in field_rows])
        names = [r[0] for r in field_rows]
        for fname in self.SIX_SOURCE_FILES:
            self._write(
                fname, ["player_name", "rounds_played", "total_mean"],
                [[n, "10", "1.0"] for n in names],
            )
        self._write(
            "app_skill_l12_sg.csv",
            ["stat", "player_name", "50_100_fw_value", "100_150_fw_value",
             "150_200_fw_value", "over_200_fw_value"],
            [["SG Per Shot", n, "0.1", "0.1", "0.1", "0.1"] for n in names],
        )
        self._write(
            "app_skill_l12_prox.csv", ["stat", "player_name", "150_200_fw_value"],
            [["Proximity (ft)", n, "28"] for n in names],
        )
        self._write(
            "dg_performance_2026.csv",
            ["player_name", "putt_true", "arg_true", "app_true", "ott_true"],
            [[n, "0.1", "0.1", "0.3", "0.2"] for n in names],
        )
        self._write(
            "dg_decomposition.csv",
            ["player_name", "driving_acc_adj", "driving_dist_adj", "std_dev"],
            [[n, "0.0", "0.0", "3.0"] for n in names],
        )
        self._write(
            "tpc_twin_cities_CH.csv",
            ["player_name", "ch_adjustment", "experience_adjustment"],
            [[n, "0.05", "0.0"] for n in names],
        )
        self._write(
            "pga_field_trending_table.csv",
            ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
            [[n, dg_id, "0.2", ""] for n, dg_id in field_rows],
        )


def _run_main(monkeypatch, tmp_path, event_slug, argv_extra=None):
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    argv = ["enrich_cards.py", "--event", event_slug] + (argv_extra or [])
    monkeypatch.setattr(sys, "argv", argv)
    enrich_cards.main()


def _output_path(tmp_path, event_slug):
    return (
        tmp_path / "events" / event_slug / "output" / "2026_3m_open_event_payload.json"
    )


def _deploy_path(tmp_path, event_slug):
    return (
        tmp_path / "events" / event_slug / "deploy" / "data"
        / "2026_3m_open_event_payload.json"
    )


def test_normalize_name_delegates_to_identity_resolver():
    for raw in ('"Scheffler, Scottie"', "  Åberg, Ludvig  ", "", None, "O'Brien, Sean"):
        assert normalize_name(raw) == _canonical_normalize_name(raw)


def test_output_contains_dg_id_and_unchanged_player_id(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)

    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    for p in payload["players"]:
        assert "dg_id" in p
        assert "player_id" in p
        assert p["player_id"] == p["dg_id"]


def test_accepted_source_matches_include_provenance(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)

    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    p = payload["players"][0]
    prov = p["identity_provenance"]
    assert prov["schema_version"] == "1.0"
    assert prov["canonical_key"] == "dg_id"
    trend_entry = prov["source_matches"]["trend"]
    assert trend_entry["status"] == "matched"
    assert trend_entry["method"] == "exact_dg_id"
    all_6m_entry = prov["source_matches"]["all_6m"]
    assert all_6m_entry["method"] == "exact_name"


def test_fuzzy_probable_match_blocks_rather_than_silently_contributing_data(
    tmp_path, monkeypatch, capsys
):
    """A source row close enough to look like a probable misspelling
    (fuzzy score above the diagnostic threshold) must never be silently
    auto-joined -- under the new resolver it blocks the entire release
    rather than quietly feeding that row's numbers into the player record,
    which is a strictly stronger guarantee than defaulting to zero."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100")])
    # Near-miss spelling only -- fuzzy score is high but not an exact match.
    event._write(
        "dg_performance_2026.csv",
        ["player_name", "putt_true", "arg_true", "app_true", "ott_true"],
        [["Doe, Jon", "9.9", "9.9", "9.9", "9.9"]],
    )
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    assert not _output_path(tmp_path, event.event_slug).exists()
    captured = capsys.readouterr()
    assert "perf" in captured.err
    assert "Doe, Jon" in captured.err


def test_no_plausible_candidate_falls_back_to_defaults_and_proceeds(tmp_path, monkeypatch):
    """A source row with no plausible relationship to a field player's name
    is a genuine data-completeness gap, not an identity failure -- it must
    not block release, and the player must receive the same empty defaults
    as before, never another player's or an unrelated row's data."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100")])
    event._write(
        "dg_performance_2026.csv",
        ["player_name", "putt_true", "arg_true", "app_true", "ott_true"],
        [["Totally Unrelated Person", "9.9", "9.9", "9.9", "9.9"]],
    )
    _run_main(monkeypatch, tmp_path, event.event_slug)

    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    p = payload["players"][0]
    assert p["app_true"] == 0.0
    assert p["ott_true"] == 0.0
    assert p["identity_provenance"]["source_matches"]["perf"]["status"] == "missing"


def test_identity_blocker_produces_nonzero_exit(tmp_path, monkeypatch, capsys):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Doe, Johnny", "100")])  # duplicate dg_id
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "IDENTITY RELEASE BLOCKED" in captured.err


def test_no_partial_output_created_on_blocker(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Doe, Johnny", "100")])
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()


def test_preexisting_output_byte_and_mtime_unchanged_on_blocker(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)

    out_path = _output_path(tmp_path, event.event_slug)
    before_bytes = out_path.read_bytes()
    before_mtime = out_path.stat().st_mtime_ns

    # Corrupt the field to introduce a blocker, then re-run.
    event._write(
        "pga_field.csv", ["player_name", "dg_id"],
        [["Doe, John", "100"], ["Doe, Johnny", "100"]],
    )
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert out_path.read_bytes() == before_bytes
    assert out_path.stat().st_mtime_ns == before_mtime


def test_valid_exact_mappings_preserve_expected_scoring_values(tmp_path, monkeypatch):
    """With unchanged, unambiguous identity mappings, VTS/tier/score fields
    match a direct hand-computation using the same pure functions -- the
    resolver must not perturb scoring for correctly-identified players."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)

    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    players = {p["player"]: p for p in payload["players"]}

    # Both players have identical source rows (same trait values), so a
    # correctly-unperturbed pipeline must produce identical vts_final,
    # identical tier eligibility ordering only broken by dg_id/name --
    # i.e. deterministic, not incidentally different.
    assert players["Doe, John"]["vts_final"] == players["Smith, Sam"]["vts_final"]
    assert players["Doe, John"]["tier"] in ("T1", "T2")
    assert players["Doe, John"]["sg_base_composite"] == pytest.approx(1.0)


def test_golden_score_parity_for_unchanged_identity_mappings(tmp_path, monkeypatch):
    """Full production pipeline, synthetic fixture, unambiguous identity
    mappings (one exact-dg_id match per player via pga_field_trending_table,
    one exact-name fallback match per player for every other source).
    Expected values are explicit, independently hand-derived constants --
    NOT computed by calling z_score_scale/tempered_softmax/make_composites
    (the functions under test) -- verifying the resolver refactor does not
    perturb scoring for correctly-identified players (Correction 4)."""
    import math

    event = SyntheticEvent(tmp_path, event_slug="golden_fixture")
    event.input_dir.mkdir(parents=True, exist_ok=True)
    ev = event

    ev._write("pga_field.csv", ["player_name", "dg_id"],
              [["Doe, John", "100"], ["Smith, Sam", "200"]])
    for fname in ["pga_sg_query_allcourses_l6.csv", "pga_sg_query_allcourses_l12.csv",
                  "pga_sg_query_allcourses_l24.csv"]:
        ev._write(fname, ["player_name", "rounds_played", "total_mean"],
                  [["Doe, John", "20", "1.0"], ["Smith, Sam", "20", "3.0"]])
    for fname in ["pga_sg_query_3Mopen_similar_l6.csv", "pga_sg_query_3Mopen_similar_l12.csv",
                  "pga_sg_query_3Mopen_similar_l24.csv"]:
        ev._write(fname, ["player_name", "rounds_played", "total_mean"],
                  [["Doe, John", "20", "1.2"], ["Smith, Sam", "20", "3.0"]])
    ev._write("app_skill_l12_sg.csv",
              ["stat", "player_name", "50_100_fw_value", "100_150_fw_value",
               "150_200_fw_value", "over_200_fw_value"],
              [["SG Per Shot", "Doe, John", "0", "0", "0", "0"],
               ["SG Per Shot", "Smith, Sam", "0", "0", "0", "0"]])
    ev._write("app_skill_l12_prox.csv", ["stat", "player_name", "150_200_fw_value"],
              [["Proximity (ft)", "Doe, John", "30"], ["Proximity (ft)", "Smith, Sam", "30"]])
    ev._write("dg_performance_2026.csv",
              ["player_name", "putt_true", "arg_true", "app_true", "ott_true"],
              [["Doe, John", "0", "0", "0", "0"], ["Smith, Sam", "0", "0", "0", "0"]])
    # Doe: driving_dist_adj > 0.15 and driving_acc_adj < -0.05 -> INACCURATE_BOMBER gate.
    ev._write("dg_decomposition.csv",
              ["player_name", "driving_acc_adj", "driving_dist_adj", "std_dev"],
              [["Doe, John", "-0.10", "0.20", "3.0"], ["Smith, Sam", "0.0", "0.0", "3.0"]])
    ev._write("tpc_twin_cities_CH.csv", ["player_name", "ch_adjustment", "experience_adjustment"],
              [["Doe, John", "0.0", "0.0"], ["Smith, Sam", "0.0", "0.0"]])
    # Only trending carries dg_id -- exercises the exact_dg_id method; every
    # other family above exercises exact_name fallback for a name-only source.
    ev._write("pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
              [["Doe, John", "100", "0.0", ""], ["Smith, Sam", "200", "0.0", ""]])

    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    players = {p["player"]: p for p in payload["players"]}
    doe, smith = players["Doe, John"], players["Smith, Sam"]

    # ── Identity ──
    assert doe["dg_id"] == doe["player_id"] == "100"
    assert smith["dg_id"] == smith["player_id"] == "200"
    assert doe["identity_provenance"]["source_matches"]["trend"] == {
        "status": "matched", "method": "exact_dg_id", "source_name": "Doe, John",
    }
    assert doe["identity_provenance"]["source_matches"]["all_6m"] == {
        "status": "matched", "method": "exact_name", "source_name": "Doe, John",
    }
    assert smith["identity_provenance"]["source_matches"]["trend"]["method"] == "exact_dg_id"

    # ── Dual-vector SG composites (hand-derived from the fixture's own
    # weights: sg_base = 0.20*6m + 0.30*12m + 0.50*24m; delta_fit is the
    # weighted sim-vs-all regression) ──
    assert doe["sg_base_composite"] == pytest.approx(1.0)
    assert doe["sg_similar_composite"] == pytest.approx(1.2)
    assert doe["delta_fit"] == pytest.approx(0.2)
    assert smith["sg_base_composite"] == pytest.approx(3.0)
    assert smith["sg_similar_composite"] == pytest.approx(3.0)
    assert smith["delta_fit"] == pytest.approx(0.0)

    # ── Gate / no-gate distinction ──
    assert doe["anti_pattern_flags"] == ["INACCURATE_BOMBER"]
    assert smith["anti_pattern_flags"] == []

    # ── Z-scored fields: with exactly two nonzero raw values, the z-score
    # formula (50 + 15*(v-mu)/sd) always resolves to exactly (35.0, 65.0)
    # regardless of the raw magnitudes, since mu is their midpoint and sd
    # equals half their spread -- independently verifiable arithmetic, not
    # a call into z_score_scale(). neutralSkillIndex uses pre-gate,
    # pre-delta sg_base_composite (1.0 vs 3.0); vts_final uses the
    # post-gate combined raw (1.2*0.92=1.104 vs 3.0); prepenalty_vts uses
    # the pre-gate combined raw (1.2 vs 3.0) and is only populated when a
    # gate fired.
    assert doe["neutralSkillIndex"] == pytest.approx(35.0)
    assert smith["neutralSkillIndex"] == pytest.approx(65.0)
    assert doe["vts_final"] == pytest.approx(35.0)
    assert smith["vts_final"] == pytest.approx(65.0)
    assert doe["prepenalty_vts"] == pytest.approx(35.0)
    assert smith["prepenalty_vts"] is None

    # ── Probability + ranking: win uses tempered_softmax(T=3.5, n_pos=1) on
    # the post-gate raw scores [1.104, 3.0] -- recomputed here via bare
    # math.exp, not by calling tempered_softmax(). top5/10/20 use n_pos
    # large relative to a 2-player field, so both hit the 99.9 cap.
    raw_scores = [1.2 * 0.92, 3.0]
    max_s = max(raw_scores)
    exps = [math.exp((s - max_s) / 3.5) for s in raw_scores]
    total = sum(exps)
    expected_win = [round(min(99.9, (e / total) * 1 * 100), 1) for e in exps]
    assert doe["winPct"] == pytest.approx(expected_win[0])
    assert smith["winPct"] == pytest.approx(expected_win[1])
    for p in (doe, smith):
        assert p["top5Pct"] == pytest.approx(99.9)
        assert p["top10Pct"] == pytest.approx(99.9)
        assert p["top20Pct"] == pytest.approx(99.9)

    # ── Deterministic ranking + tier ──
    assert smith["rank"] == 1
    assert doe["rank"] == 2
    assert doe["tier"] == "T1"
    assert smith["tier"] == "T1"


def test_duplicate_raw_source_rows_in_csv_produce_nonzero_exit(tmp_path, monkeypatch, capsys):
    """Production loader path (not the pure resolver): two rows sharing one
    field player's raw source name in a supplementary CSV must block."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    with event.input_dir.joinpath("dg_performance_2026.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["player_name", "putt_true", "arg_true", "app_true", "ott_true"])
        w.writerow(["Doe, John", "0.1", "0.1", "0.1", "0.1"])
        w.writerow(["Doe, John", "9.9", "9.9", "9.9", "9.9"])
        w.writerow(["Smith, Sam", "0.1", "0.1", "0.1", "0.1"])

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "perf" in captured.err
    assert "#" in captured.err  # row-ordinal context present
    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()


def test_duplicate_source_ids_in_csv_produce_nonzero_exit(tmp_path, monkeypatch, capsys):
    """Two rows in pga_field_trending_table.csv sharing one canonical
    source dg_id must block, with row-ordinal context in the diagnostic."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    event._write(
        "pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
        [
            ["Doe, John", "100", "0.2", ""],
            ["Doe, John Impostor", "100", "9.9", ""],
            ["Smith, Sam", "200", "0.2", ""],
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "trend" in captured.err
    assert "#" in captured.err
    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()


def test_no_dirs_created_on_duplicate_row_blocker(tmp_path, monkeypatch):
    """Neither output/ nor deploy/data/ is created at all (not merely the
    payload file) when a duplicate-row identity blocker fires on a fresh
    event with no prior output."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    event._write(
        "pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
        [
            ["Doe, John", "100", "0.2", ""],
            ["Doe, John Impostor", "100", "9.9", ""],
            ["Smith, Sam", "200", "0.2", ""],
        ],
    )
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, event.event_slug)

    output_dir = tmp_path / "events" / event.event_slug / "output"
    deploy_dir = tmp_path / "events" / event.event_slug / "deploy"
    assert not output_dir.exists()
    assert not deploy_dir.exists()


def test_no_ambiguous_duplicate_data_reaches_scoring(tmp_path, monkeypatch):
    """A duplicate-row collision affecting only two of three field players
    still blocks the entire release -- the third, unambiguous player's data
    must not reach scoring/output either, since output is all-or-nothing."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200"), ("Jones, Bob", "300")])
    with event.input_dir.joinpath("dg_performance_2026.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["player_name", "putt_true", "arg_true", "app_true", "ott_true"])
        w.writerow(["Doe, John", "0.1", "0.1", "0.1", "0.1"])
        w.writerow(["Doe, John", "9.9", "9.9", "9.9", "9.9"])
        w.writerow(["Smith, Sam", "0.1", "0.1", "0.1", "0.1"])
        w.writerow(["Jones, Bob", "0.1", "0.1", "0.1", "0.1"])

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()


def test_output_ordering_remains_deterministic(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200"), ("Jones, Bob", "300")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    first = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))

    event2 = SyntheticEvent(tmp_path, event_slug="synthetic_event_2")
    event2.write_all([("Doe, John", "100"), ("Smith, Sam", "200"), ("Jones, Bob", "300")])
    _run_main(monkeypatch, tmp_path, event2.event_slug)
    second = json.loads(_output_path(tmp_path, event2.event_slug).read_text(encoding="utf-8"))

    first_order = [p["player"] for p in first["players"]]
    second_order = [p["player"] for p in second["players"]]
    assert first_order == second_order


# ── Field-ownership conflict after exact-ID acceptance (production CLI) ─────

def test_field_ownership_conflict_produces_nonzero_exit_with_no_new_dirs(
    tmp_path, monkeypatch, capsys
):
    """A second trending-table row with no dg_id but the same name as an
    already exact-ID-matched field player must block release -- it is not
    merely an unused row -- and no output/ or deploy/ directory is created
    on this fresh event with no prior output."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    event._write(
        "pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
        [
            ["Doe, John", "100", "0.2", ""],
            ["Doe, John", "", "9.9", ""],
            ["Smith, Sam", "200", "0.2", ""],
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert exc_info.value.code != 0

    captured = capsys.readouterr()
    assert "trend" in captured.err
    assert "Doe, John" in captured.err
    assert "exact-ID-owned" in captured.err or "dg_id" in captured.err

    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()
    output_dir = tmp_path / "events" / event.event_slug / "output"
    deploy_dir = tmp_path / "events" / event.event_slug / "deploy"
    assert not output_dir.exists()
    assert not deploy_dir.exists()


def test_field_ownership_conflict_preserves_existing_output_bytes_and_mtime(
    tmp_path, monkeypatch
):
    """Once a valid payload exists on disk, a subsequent build that trips a
    field-ownership conflict (second trending row targeting an exact-ID-
    owned player) must not touch the existing output file at all."""
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)

    out_path = _output_path(tmp_path, event.event_slug)
    deploy_path = _deploy_path(tmp_path, event.event_slug)
    before_out_bytes = out_path.read_bytes()
    before_out_mtime = out_path.stat().st_mtime_ns
    before_deploy_bytes = deploy_path.read_bytes()
    before_deploy_mtime = deploy_path.stat().st_mtime_ns

    event._write(
        "pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
        [
            ["Doe, John", "100", "0.2", ""],
            ["Doe, John", "", "9.9", ""],
            ["Smith, Sam", "200", "0.2", ""],
        ],
    )

    with pytest.raises(SystemExit):
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert out_path.read_bytes() == before_out_bytes
    assert out_path.stat().st_mtime_ns == before_out_mtime
    assert deploy_path.read_bytes() == before_deploy_bytes
    assert deploy_path.stat().st_mtime_ns == before_deploy_mtime
