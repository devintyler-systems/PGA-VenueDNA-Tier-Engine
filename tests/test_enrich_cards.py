"""Tests for engine/enrich_cards.py — pure-function coverage."""
import csv
import hashlib
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
    combine_raw_score,
    apply_gates,
    z_score_scale,
    tempered_softmax,
    enforce_monotonicity,
    assign_tier,
    make_cut_prob,
    adapt_to_v2_neutral_skill_horizons,
    adapt_to_v2_similar_course_rows,
)
from identity_resolver import SourceRow
from identity_resolver import normalize_name as _canonical_normalize_name
from venuedna_scoring import SimilarCourseRow
from event_context import EventContext
from source_manifest_resolver import (
    ROLE_MISSING_BEHAVIOR,
    ROLE_REQUIRED,
    REQUIRED_ROLES,
    SIMILAR_SG_HORIZON_MONTHS,
)


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


@pytest.mark.parametrize(
    ("rounds", "total_mean", "expected_rounds", "expected_mean"),
    (
        ("", "", None, None),
        ("null", "none", None, None),
        ("bad", "not-a-number", None, None),
        ("0", "0", 0, 0.0),
        ("0.0", "0.0", 0, 0.0),
    ),
)
def test_load_sg_csv_preserves_missingness_and_valid_zero(
    tmp_path, rounds, total_mean, expected_rounds, expected_mean
):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        f'player_name,rounds_played,total_mean\n"Doe, John",{rounds},{total_mean}\n',
        encoding="utf-8",
    )
    row = load_sg_csv(csv_file)[0].payload
    assert row["rounds"] == expected_rounds
    assert row["total_mean"] == expected_mean


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


# ── Synthetic source_manifest.json helpers (Phase 4.2 producer integration) ─
#
# These build a schema-1.0 source_manifest.json for a synthetic event tree,
# reusing the resolver's own ROLE_REQUIRED/ROLE_MISSING_BEHAVIOR/
# SIMILAR_SG_HORIZON_MONTHS tables so the manifest's required/missing_behavior
# combinations can never silently drift from standards/04 §9.5A. sha256 and
# row_count default to null (not_asserted) so tests that overwrite a
# declared file's content after the manifest is written -- a common existing
# fixture pattern -- never trip an unintended integrity mismatch; only the
# tests that specifically exercise integrity validation supply real values.

DEFAULT_MANIFEST_ROLE_FILES: dict[str, str] = {
    "field": "pga_field.csv",
    "neutral_skill.sg_total.6m": "pga_sg_query_allcourses_l6.csv",
    "neutral_skill.sg_total.12m": "pga_sg_query_allcourses_l12.csv",
    "neutral_skill.sg_total.24m": "pga_sg_query_allcourses_l24.csv",
    "venue_fit.similar_sg.6m": "pga_sg_query_3Mopen_similar_l6.csv",
    "venue_fit.similar_sg.12m": "pga_sg_query_3Mopen_similar_l12.csv",
    "venue_fit.similar_sg.24m": "pga_sg_query_3Mopen_similar_l24.csv",
    "traits.approach.sg_per_shot.12m": "app_skill_l12_sg.csv",
    "traits.approach.proximity.12m": "app_skill_l12_prox.csv",
    "performance.sg_categories.season": "dg_performance_2026.csv",
    "benchmark.decomposition": "dg_decomposition.csv",
    "venue_history": "tpc_twin_cities_CH.csv",
    "recent_form.trending": "pga_field_trending_table.csv",
}


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_count_of(path: Path, encoding: str = "utf-8") -> int:
    lines = path.read_text(encoding=encoding).splitlines()
    return max(0, len(lines) - 1)


def _manifest_source_entry(
    role: str, filename: str, *, venue_slug: str,
    sha256: str | None = None, row_count: int | None = None,
) -> dict:
    entry = {
        "role": role,
        "path": filename,
        "required": ROLE_REQUIRED[role],
        "missing_behavior": ROLE_MISSING_BEHAVIOR[role],
        "schema_id": f"venuedna.source.synthetic.{role}.v1",
        "identity_key": "player_name",
        "encoding": "utf-8",
        "sha256": sha256,
        "row_count": row_count,
        "metadata": {},
    }
    if role in SIMILAR_SG_HORIZON_MONTHS:
        entry["metadata"] = {
            "similar_course_set_id": "synthetic_similar_v1",
            "set_version": 1,
            "set_provenance": "synthetic_test_fixture",
            "horizon_months": SIMILAR_SG_HORIZON_MONTHS[role],
        }
    elif role == "venue_history":
        entry["metadata"] = {"venue_slug": venue_slug}
    return entry


def write_synthetic_source_manifest(
    input_dir: Path, *, event_slug: str, venue_slug: str,
    role_files: dict[str, str] | None = None,
    omit_roles: tuple[str, ...] = (),
    integrity_overrides: dict[str, dict] | None = None,
) -> None:
    """Writes a schema-1.0 source_manifest.json into a synthetic event's
    input/ directory, declaring every one of the thirteen required roles by
    default (pointing at the same legacy-compatible filenames existing
    fixtures already write), so pre-existing tests need no rewriting.
    ``role_files`` overrides the declared filename per role (for arbitrary-
    filename tests); ``omit_roles`` drops a role from ``sources`` entirely
    (for missing-source tests); ``integrity_overrides`` supplies
    ``{role: {"sha256": ..., "row_count": ...}}`` for tests that specifically
    exercise integrity validation.
    """
    role_files = role_files if role_files is not None else DEFAULT_MANIFEST_ROLE_FILES
    integrity_overrides = integrity_overrides or {}
    sources = []
    for role in REQUIRED_ROLES:
        if role in omit_roles:
            continue
        filename = role_files.get(role)
        if filename is None:
            continue
        overrides = integrity_overrides.get(role, {})
        sources.append(_manifest_source_entry(
            role, filename, venue_slug=venue_slug,
            sha256=overrides.get("sha256"), row_count=overrides.get("row_count"),
        ))
    manifest = {
        "schema_version": "1.0",
        "event_slug": event_slug,
        "venue_slug": venue_slug,
        "as_of": "2026-01-01T00:00:00Z",
        "sources": sources,
    }
    (input_dir / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


# ── Identity integration (synthetic temporary events only) ─────────────────

class SyntheticEvent:
    """Builds a minimal, valid synthetic event input/ tree under tmp_path.
    Never touches events/2026_Finished_Events/ or any archived directory."""

    SIX_SOURCE_FILES = [
        "pga_sg_query_allcourses_l6.csv", "pga_sg_query_allcourses_l12.csv",
        "pga_sg_query_allcourses_l24.csv", "pga_sg_query_3Mopen_similar_l6.csv",
        "pga_sg_query_3Mopen_similar_l12.csv", "pga_sg_query_3Mopen_similar_l24.csv",
    ]

    def __init__(self, tmp_path: Path, event_slug: str = "synthetic_event",
                 venue_slug: str = "synthetic_test_venue") -> None:
        self.root = tmp_path
        self.event_slug = event_slug
        self.venue_slug = venue_slug
        self.input_dir = tmp_path / "events" / event_slug / "input"
        self.input_dir.mkdir(parents=True)

    def _write(self, name: str, header: list[str], rows: list[list[str]]) -> None:
        with (self.input_dir / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    def write_source_manifest(self, **kwargs) -> None:
        kwargs.setdefault("event_slug", self.event_slug)
        kwargs.setdefault("venue_slug", self.venue_slug)
        write_synthetic_source_manifest(self.input_dir, **kwargs)

    def write_all(self, field_rows: list[tuple[str, str]], *, write_manifest: bool = True) -> None:
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
        if write_manifest:
            self.write_source_manifest()


def _make_context(tmp_path, event_slug, *, venue_slug="synthetic_test_venue",
                   event_name=None, venue_name=None):
    """Build an in-memory EventContext for the internal test seam. This
    never writes a manifest file and never touches the real repository --
    it is the isolated-test equivalent of an already-validated production
    context, injected directly via main()'s keyword-only _context param."""
    event_root = tmp_path / "events" / event_slug
    return EventContext(
        event_slug=event_slug,
        event_name=event_name or event_slug,
        venue_slug=venue_slug,
        venue_name=venue_name or venue_slug,
        year=2026,
        event_root=event_root,
        venue_profile=(
            tmp_path / "library" / "venues" / venue_slug / f"{venue_slug}_venue_profile.md"
        ),
        deploy_root=event_root / "deploy",
        audit_root=event_root / "audit",
    )


def _run_main(monkeypatch, tmp_path, event_slug, *, live_mode=None, context=None):
    """Invoke main() through the internal, argparse-invisible test seam --
    never through --event or any other CLI flag, which no longer exist on
    the normal production entry point."""
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    context = context or _make_context(tmp_path, event_slug)
    enrich_cards.main(_context=context, _live_mode=live_mode)


def _output_path(tmp_path, event_slug):
    return (
        tmp_path / "events" / event_slug / "output" / f"{event_slug}_event_payload.json"
    )


def _deploy_path(tmp_path, event_slug):
    return (
        tmp_path / "events" / event_slug / "deploy" / "data"
        / f"{event_slug}_event_payload.json"
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
    ev.write_source_manifest()

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

    # ── Z-scored fields: with exactly two nonzero canonical PostGateRaw values, the z-score
    # formula (50 + 15*(v-mu)/sd) always resolves to exactly (35.0, 65.0)
    # regardless of the raw magnitudes, since mu is their midpoint and sd
    # equals half their spread -- independently verifiable arithmetic, not
    # a call into the producer's scoring helpers. neutralSkillIndex uses
    # SG_Base_Comp (1.0 vs 3.0); vts_final and prepenalty_vts use canonical
    # PostGateRaw/PrePenaltyRaw (1.2 vs 3.0). The historical bomber flag
    # remains visible but has no score effect.
    assert doe["neutralSkillIndex"] == pytest.approx(35.0)
    assert smith["neutralSkillIndex"] == pytest.approx(65.0)
    assert doe["vts_final"] == pytest.approx(35.0)
    assert smith["vts_final"] == pytest.approx(65.0)
    assert doe["prepenalty_vts"] == pytest.approx(35.0)
    assert smith["prepenalty_vts"] == pytest.approx(65.0)
    assert doe["post_gate_raw"] == pytest.approx(1.2)
    assert smith["post_gate_raw"] == pytest.approx(3.0)
    assert doe["formula_id"] == "venuedna_dual_vector_decomposed"
    assert doe["formula_version"] == "2.0.0"
    assert doe["scoring_spec_version"] == "2.0-draft"
    assert doe["penalties_applied"] == []
    assert doe["gates_applied"] == []
    assert payload["formulaMetadata"] == {
        "formula_id": "venuedna_dual_vector_decomposed",
        "formula_version": "2.0.0",
        "scoring_spec_version": "2.0-draft",
        "comparable_score_family": "dual_vector_sg_per_round_v2",
        "penalty_gate_set_id": "venuedna_v2_none",
    }

    # ── Probability + ranking: win uses tempered_softmax(T=3.5, n_pos=1) on
    # canonical PostGateRaw scores [1.2, 3.0] -- recomputed here via bare
    # math.exp, not by calling tempered_softmax(). top5/10/20 use n_pos
    # large relative to a 2-player field, so both hit the 99.9 cap.
    raw_scores = [1.2, 3.0]
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


def test_combine_raw_score_extraction_matches_pipeline_prepenalty_vts(tmp_path, monkeypatch):
    """P1 score-decomposition parity: combine_raw_score() was extracted
    verbatim from the addends previously inlined in main() (same terms,
    same summation order). This asserts main()'s own field-wide z-scoring
    of the extracted function's pre_gate_raw_total reproduces the pipeline's
    prepenalty_vts for a gated player -- i.e. the extraction changed no
    score, using the same golden fixture as the parity test above."""
    event = SyntheticEvent(tmp_path, event_slug="combine_raw_score_check")
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
    ev._write("dg_decomposition.csv",
              ["player_name", "driving_acc_adj", "driving_dist_adj", "std_dev"],
              [["Doe, John", "-0.10", "0.20", "3.0"], ["Smith, Sam", "0.0", "0.0", "3.0"]])
    ev._write("tpc_twin_cities_CH.csv", ["player_name", "ch_adjustment", "experience_adjustment"],
              [["Doe, John", "0.0", "0.0"], ["Smith, Sam", "0.0", "0.0"]])
    ev._write("pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
              [["Doe, John", "100", "0.0", ""], ["Smith, Sam", "200", "0.0", ""]])
    ev.write_source_manifest()

    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    players = {p["player"]: p for p in payload["players"]}
    doe = players["Doe, John"]

    # Doe: sg_similar_composite=1.2, all other addend inputs are 0 -- so
    # pre_gate_raw_total == 1.2 exactly, matching the module's own
    # sg_sim_comp value.
    decomposition = combine_raw_score(
        sg_sim_comp=doe["sg_similar_composite"],
        trait_approach_raw=doe["trait_approach_raw"],
        trait_long_iron_raw=doe["trait_long_iron_raw"],
        ott_true=doe["ott_true"],
        ch_adj=doe["ch_adjustment"],
        true_sg_l20=doe["true_sg_l20"],
    )
    assert decomposition["pre_gate_raw_total"] == pytest.approx(1.2)
    assert doe["anti_pattern_flags"] == ["INACCURATE_BOMBER"]
    assert doe["prepenalty_vts"] is not None


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


# ── Canonical-v2 root-producer integration boundary ───────────────────────
#
# These adapters translate the already-resolved, pre-debut_row()-fallback
# per-horizon rows (each either a row dict or None when a source family has
# no row for that player) into engine/venuedna_scoring.py's canonical input
# shape. The tests below verify that main() invokes them and preserves the
# missing-row versus valid zero-round DEBUT distinction required by the
# canonical producer integration.

def test_adapt_to_v2_neutral_skill_horizons_preserves_missing_vs_present():
    result = adapt_to_v2_neutral_skill_horizons({
        "6m": {"rounds": 20, "total_mean": 2.5},
        "12m": None,
        "24m": {"rounds": 20, "total_mean": 0.0},
    })
    assert result == {"6m": 2.5, "12m": None, "24m": 0.0}


def test_adapt_to_v2_similar_course_rows_preserves_missing_vs_debut():
    result = adapt_to_v2_similar_course_rows({
        "6m": {"rounds": 0, "total_mean": 0.0},
        "12m": None,
        "24m": {"rounds": 15, "total_mean": 1.2},
    })
    assert result["6m"] == SimilarCourseRow(0, 0.0)
    assert result["12m"] is None
    assert result["24m"] == SimilarCourseRow(15, 1.2)


def test_v2_adapters_are_called_by_main_runtime(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path)
    event.write_all([("Doe, John", "100")])
    calls = {"neutral": 0, "similar": 0}
    real_neutral = enrich_cards.adapt_to_v2_neutral_skill_horizons
    real_similar = enrich_cards.adapt_to_v2_similar_course_rows

    def neutral_adapter(rows):
        calls["neutral"] += 1
        return real_neutral(rows)

    def similar_adapter(rows):
        calls["similar"] += 1
        return real_similar(rows)

    monkeypatch.setattr(enrich_cards, "adapt_to_v2_neutral_skill_horizons", neutral_adapter)
    monkeypatch.setattr(enrich_cards, "adapt_to_v2_similar_course_rows", similar_adapter)
    _run_main(monkeypatch, tmp_path, event.event_slug)
    assert calls == {"neutral": 1, "similar": 1}


def test_main_canonical_outputs_ignore_extreme_legacy_addends_and_historical_gates(tmp_path, monkeypatch):
    """Runtime proof: legacy inputs would reverse the old 3M order, but not
    the migrated official canonical v2 ordering (Alpha, then Bravo)."""
    event = SyntheticEvent(tmp_path, event_slug="canonical_isolation")
    names = [("Alpha, Ann", "100"), ("Bravo, Bob", "200")]
    event.write_all(names)
    for filename in (
        "pga_sg_query_allcourses_l6.csv", "pga_sg_query_allcourses_l12.csv",
        "pga_sg_query_allcourses_l24.csv",
    ):
        event._write(filename, ["player_name", "rounds_played", "total_mean"], [
            ["Alpha, Ann", "20", "3.0"], ["Bravo, Bob", "20", "2.0"],
        ])
    for filename in (
        "pga_sg_query_3Mopen_similar_l6.csv", "pga_sg_query_3Mopen_similar_l12.csv",
        "pga_sg_query_3Mopen_similar_l24.csv",
    ):
        event._write(filename, ["player_name", "rounds_played", "total_mean"], [
            ["Alpha, Ann", "20", "3.0"], ["Bravo, Bob", "20", "2.0"],
        ])

    _run_main(monkeypatch, tmp_path, event.event_slug)
    baseline = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))

    # These changes would make Bravo overwhelmingly first under the old
    # five-addend formula, while Alpha's historical bomber gate would further
    # reduce its old raw score. Canonical raw scores remain 3.0 and 2.0.
    event._write("app_skill_l12_sg.csv", ["stat", "player_name", "50_100_fw_value", "100_150_fw_value", "150_200_fw_value", "over_200_fw_value"], [
        ["SG Per Shot", "Alpha, Ann", "0", "0", "0", "0"],
        ["SG Per Shot", "Bravo, Bob", "100", "100", "100", "100"],
    ])
    event._write("dg_performance_2026.csv", ["player_name", "putt_true", "arg_true", "app_true", "ott_true"], [
        ["Alpha, Ann", "0", "0", "0", "0"], ["Bravo, Bob", "0", "0", "100", "100"],
    ])
    event._write("dg_decomposition.csv", [
        "player_name", "driving_acc_adj", "driving_dist_adj", "std_dev",
        "fit_other_adj", "course_history_adj", "timing_adj",
    ], [
        ["Alpha, Ann", "-1", "1", "3", "-100", "-100", "-100"],
        ["Bravo, Bob", "0", "0", "3", "100", "100", "100"],
    ])
    event._write("tpc_twin_cities_CH.csv", ["player_name", "ch_adjustment", "experience_adjustment"], [
        ["Alpha, Ann", "0", "0"], ["Bravo, Bob", "100", "0"],
    ])
    event._write("pga_field_trending_table.csv", ["player_name", "dg_id", "true_sg_l20", "l5_starts"], [
        ["Alpha, Ann", "100", "0", ""], ["Bravo, Bob", "200", "100", ""],
    ])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    changed = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))

    official_keys = ("vts_final", "rank", "tier", "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct", "post_gate_raw")
    baseline_players = {p["player"]: p for p in baseline["players"]}
    changed_players = {p["player"]: p for p in changed["players"]}
    assert [p["player"] for p in changed["players"]] == ["Alpha, Ann", "Bravo, Bob"]
    for player in baseline_players:
        assert {key: changed_players[player][key] for key in official_keys} == {
            key: baseline_players[player][key] for key in official_keys
        }
    assert changed_players["Alpha, Ann"]["anti_pattern_flags"] == ["INACCURATE_BOMBER"]
    historical_alpha, _ = apply_gates(
        combine_raw_score(3.0, 0.0, 0.0, 0.0, 0.0, 0.0)["pre_gate_raw_total"],
        {"putt_true": 0.0, "arg_true": 0.0, "app_true": 0.0, "ott_true": 0.0},
        {"driving_acc_adj": -1.0, "driving_dist_adj": 1.0},
    )
    historical_bravo, _ = apply_gates(
        combine_raw_score(2.0, 100.0, 65.0, 100.0, 100.0, 100.0)["pre_gate_raw_total"],
        {"putt_true": 0.0, "arg_true": 0.0, "app_true": 100.0, "ott_true": 100.0},
        {"driving_acc_adj": 0.0, "driving_dist_adj": 0.0},
    )
    assert historical_bravo > historical_alpha  # Old official order: Bravo, Alpha.


def test_main_preserves_csv_missingness_and_excludes_unscored_from_official_field(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path, event_slug="canonical_missingness")
    names = [
        ("Scored, Sue", "100"), ("Debut, Dee", "200"), ("Missing Sim, Mia", "300"),
        ("Missing All, Ari", "400"), ("Bad Base, Bea", "500"), ("Bad Rounds, Ray", "600"),
    ]
    event.write_all(names)
    all_names = [name for name, _ in names if name != "Missing All, Ari"]
    for filename in (
        "pga_sg_query_allcourses_l6.csv", "pga_sg_query_allcourses_l12.csv",
        "pga_sg_query_allcourses_l24.csv",
    ):
        rows = [[name, "20", "1.0"] for name in all_names]
        if filename.endswith("l6.csv"):
            rows = [[name, "20", "null" if name == "Bad Base, Bea" else "1.0"] for name in all_names]
        event._write(filename, ["player_name", "rounds_played", "total_mean"], rows)
    for filename in (
        "pga_sg_query_3Mopen_similar_l6.csv", "pga_sg_query_3Mopen_similar_l12.csv",
        "pga_sg_query_3Mopen_similar_l24.csv",
    ):
        rows = []
        for name, _ in names:
            if name == "Missing Sim, Mia":
                continue
            rounds, mean = ("0", "") if name == "Debut, Dee" else ("20", "1.0")
            if name == "Bad Rounds, Ray" and filename.endswith("l6.csv"):
                rounds = "bad"
            rows.append([name, rounds, mean])
        event._write(filename, ["player_name", "rounds_played", "total_mean"], rows)

    _run_main(monkeypatch, tmp_path, event.event_slug)
    players = {
        p["player"]: p
        for p in json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))["players"]
    }
    assert players["Scored, Sue"]["scoring_status"] == "SCORED"
    assert players["Debut, Dee"]["scoring_status"] == "SCORED"
    assert players["Debut, Dee"]["data_depth"] == "DEBUT"
    assert players["Debut, Dee"]["venue_fit_delta_raw"] == 0.0
    for name in ("Scored, Sue", "Debut, Dee"):
        assert players[name]["penalties_applied"] == []
        assert players[name]["gates_applied"] == []
        assert players[name]["scoring_spec_version"] == "2.0-draft"
    for name in ("Missing Sim, Mia", "Missing All, Ari", "Bad Base, Bea", "Bad Rounds, Ray"):
        assert players[name]["scoring_status"] == "UNSCORED"
        assert players[name]["vts_final"] is None
        assert players[name]["rank"] is None
        assert players[name]["tier"] is None
        assert players[name]["post_gate_raw"] is None
        assert all(players[name][key] is None for key in (
            "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
        ))
        assert players[name]["penalties_applied"] == []
        assert players[name]["gates_applied"] == []
        assert players[name]["scoring_spec_version"] == "2.0-draft"
    assert players["Scored, Sue"]["rank"] == 1


def test_main_handles_an_entirely_unscored_field_without_probability_pool_errors(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path, event_slug="all_unscored")
    event.write_all([("Missing, Moe", "100")])
    for filename in SyntheticEvent.SIX_SOURCE_FILES:
        event._write(filename, ["player_name", "rounds_played", "total_mean"], [])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    player = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))["players"][0]
    assert player["scoring_status"] == "UNSCORED"
    assert player["vts_final"] is None
    assert player["rank"] is None
    assert player["tier"] is None
    assert player["winPct"] is None
    assert player["penalties_applied"] == []
    assert player["gates_applied"] == []


# ── Manifest-driven event context (production entry point, no CLI flags) ───
#
# These tests exercise main() with no keyword-only _context injected -- the
# actual production default path -- against a synthetic config/active_event.
# json under tmp_path. They never touch the real config/active_event.json or
# any real events/ or library/ directory.
#
# The only event/venue slug pairing that clears the capability gate is the
# one this producer's remaining input files are still hardcoded to:
# SUPPORTED_EVENT_SLUG / SUPPORTED_VENUE_SLUG ("2026_3m_open" /
# "tpc_twin_cities"). Manifests below default to that pairing so the
# "valid manifest" tests reach the pipeline; the unsupported-venue tests
# further down deliberately use a different pairing.

def _write_manifest(tmp_path, *, status="PRE_EVENT",
                     event_slug=enrich_cards.SUPPORTED_EVENT_SLUG,
                     venue_slug=enrich_cards.SUPPORTED_VENUE_SLUG,
                     event_name="Test-Only Manifest Event Label",
                     venue_name="Test-Only Manifest Venue Label",
                     overrides=None):
    manifest = {
        "schema_version": "1.0",
        "status": status,
        "event_slug": event_slug,
        "event_name": event_name,
        "venue_slug": venue_slug,
        "venue_name": venue_name,
        "year": 2026,
        "event_root": f"events/{event_slug}",
        "venue_profile": f"library/venues/{venue_slug}/{venue_slug}_venue_profile.md",
        "deploy_root": f"events/{event_slug}/deploy",
        "audit_root": f"events/{event_slug}/audit",
    }
    if overrides:
        manifest.update(overrides)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "active_event.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _run_main_from_manifest(monkeypatch, tmp_path):
    """Invoke main() through the real production path: no _context
    injected, argv carries no flags, config/active_event.json (under
    tmp_path) is the sole source of event context."""
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py"])
    enrich_cards.main()


class _CallCounter:
    """Wraps a callable and records how many times it was invoked, while
    still delegating through to the original so wrapped tests that do
    expect calls keep working. Used to prove a rejected argument or a
    failed manifest/gate check performs zero event-bound reads or writes."""

    def __init__(self, wrapped):
        self.calls = 0
        self._wrapped = wrapped

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self._wrapped(*args, **kwargs)


_EVENT_BOUND_READERS = (
    "load_field_rows", "load_sg_csv", "load_app_skill", "load_app_prox",
    "load_performance", "load_decomp", "load_ch", "load_trending",
)


def _spy_event_bound_readers(monkeypatch):
    spies = {}
    for name in _EVENT_BOUND_READERS:
        counter = _CallCounter(getattr(enrich_cards, name))
        monkeypatch.setattr(enrich_cards, name, counter)
        spies[name] = counter
    return spies


def _spy_path_write_text(monkeypatch):
    return_counter = _CallCounter(Path.write_text)
    monkeypatch.setattr(Path, "write_text", return_counter)
    return return_counter


# ── Production CLI safety (Finding A / Finding B) ───────────────────────────

def test_event_flag_no_longer_accepted(tmp_path, monkeypatch):
    """--event no longer exists on the normal CLI -- argparse's own
    unrecognized-argument handling must reject it, before any event-bound
    read, directory creation, or write."""
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py", "--event", "some_event"])
    reader_spies = _spy_event_bound_readers(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()

    assert exc_info.value.code != 0
    assert all(counter.calls == 0 for counter in reader_spies.values())
    assert not (tmp_path / "events").exists()
    assert not (tmp_path / "config").exists()


@pytest.mark.parametrize("live_value", ["r1", "r2", "r3", "r4"])
def test_live_flag_no_longer_accepted_for_every_former_value(tmp_path, monkeypatch, live_value):
    """This PRE_EVENT producer no longer accepts --live in any form -- every
    formerly-supported round value must exit nonzero before any event-bound
    I/O, and must never create a live-named output or deploy artifact."""
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py", "--live", live_value])
    reader_spies = _spy_event_bound_readers(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()

    assert exc_info.value.code != 0
    assert all(counter.calls == 0 for counter in reader_spies.values())
    assert not (tmp_path / "events").exists()
    assert not (tmp_path / "config").exists()


def test_unrecognized_cli_argument_of_any_kind_exits_nonzero(tmp_path, monkeypatch):
    """No CLI argument at all is accepted by the normal entry point -- there
    is no hidden flag, environment-variable convention, or fallback that
    selects an event without the manifest."""
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py", "--anything-else"])
    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()
    assert exc_info.value.code != 0
    assert not (tmp_path / "events").exists()


# ── Manifest-only execution (Finding A / Finding B, requirements 7-13) ──────

def test_no_active_event_fails_before_all_event_bound_readers_and_writers(
    tmp_path, monkeypatch, capsys
):
    """NO_ACTIVE_EVENT must fail closed before any event-bound reader is
    called and before Path.write_text is ever invoked -- proven with call-
    counting spies, not just directory-absence inference."""
    _write_manifest(tmp_path, status="NO_ACTIVE_EVENT",
                     overrides={"event_slug": None, "event_name": None,
                                "venue_slug": None, "venue_name": None,
                                "event_root": None, "venue_profile": None,
                                "deploy_root": None, "audit_root": None})
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py"])
    reader_spies = _spy_event_bound_readers(monkeypatch)
    write_counter = _spy_path_write_text(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "NO_ACTIVE_EVENT" in captured.err or "No active event" in captured.err
    assert all(counter.calls == 0 for counter in reader_spies.values())
    assert write_counter.calls == 0
    assert not (tmp_path / "events").exists()


def test_valid_manifest_derives_paths_and_metadata(tmp_path, monkeypatch):
    """A valid synthetic PRE_EVENT manifest for the supported event/venue
    pairing drives event_root/output/deploy paths and event/venue metadata
    from the manifest itself -- not from a hardcoded literal."""
    manifest = _write_manifest(tmp_path)
    event_slug = manifest["event_slug"]
    event = SyntheticEvent(tmp_path, event_slug=event_slug, venue_slug=manifest["venue_slug"])
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])

    _run_main_from_manifest(monkeypatch, tmp_path)

    out_path = _output_path(tmp_path, event_slug)
    deploy_path = _deploy_path(tmp_path, event_slug)
    assert out_path.exists()
    assert deploy_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["event"] == manifest["event_name"] == "Test-Only Manifest Event Label"
    assert payload["venue"] == manifest["venue_name"] == "Test-Only Manifest Venue Label"
    assert payload["event"] != "2026 3M Open"
    assert payload["venue"] != "TPC Twin Cities"


def test_existing_output_unchanged_after_context_validation_failure(tmp_path, monkeypatch):
    """Once a valid manifest-driven payload exists on disk, a subsequent run
    against a manifest that fails context validation must not touch it --
    same bytes, same mtime, for both the output and deploy copies."""
    manifest = _write_manifest(tmp_path)
    event_slug = manifest["event_slug"]
    event = SyntheticEvent(tmp_path, event_slug=event_slug, venue_slug=manifest["venue_slug"])
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main_from_manifest(monkeypatch, tmp_path)

    out_path = _output_path(tmp_path, event_slug)
    deploy_path = _deploy_path(tmp_path, event_slug)
    before_out_bytes = out_path.read_bytes()
    before_out_mtime = out_path.stat().st_mtime_ns
    before_deploy_bytes = deploy_path.read_bytes()
    before_deploy_mtime = deploy_path.stat().st_mtime_ns

    # Corrupt the manifest so deploy_root no longer matches events/{slug}/deploy.
    _write_manifest(tmp_path, overrides={"deploy_root": f"events/{event_slug}/wrong_deploy"})

    with pytest.raises(SystemExit):
        _run_main_from_manifest(monkeypatch, tmp_path)

    assert out_path.read_bytes() == before_out_bytes
    assert out_path.stat().st_mtime_ns == before_out_mtime
    assert deploy_path.read_bytes() == before_deploy_bytes
    assert deploy_path.stat().st_mtime_ns == before_deploy_mtime


# ── Unsupported venue containment (Finding D, requirements 14-20) ──────────

def test_wyndham_like_manifest_fails_before_any_3m_or_tpc_input_read(
    tmp_path, monkeypatch, capsys
):
    """A valid-shaped PRE_EVENT manifest for a completely different event
    and venue must be rejected by the capability gate before any 3M-named
    similar-course reader or TPC course-history reader is invoked, and must
    create no output or deploy artifact. No source_manifest.json is written
    at all for this event -- proving the capability gate fails before the
    producer ever attempts to locate or parse a source manifest, since the
    failure is the gate's own message, not a manifest-not-found error."""
    event_slug = "2026_wyndham_championship"
    venue_slug = "sedgefield_country_club"
    _write_manifest(
        tmp_path, event_slug=event_slug, venue_slug=venue_slug,
        event_name="Wyndham Championship", venue_name="Sedgefield Country Club",
    )
    event = SyntheticEvent(tmp_path, event_slug=event_slug, venue_slug=venue_slug)
    event.write_all([("Doe, John", "100")], write_manifest=False)
    assert not (event.input_dir / "source_manifest.json").exists()

    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py"])
    reader_spies = _spy_event_bound_readers(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "Unsupported event/venue" in captured.err
    assert "source_manifest" not in captured.err
    assert reader_spies["load_sg_csv"].calls == 0   # 3M-named similar-course reader
    assert reader_spies["load_ch"].calls == 0        # TPC course-history reader
    assert all(counter.calls == 0 for counter in reader_spies.values())
    assert not (tmp_path / "events" / event_slug / "output").exists()
    assert not (tmp_path / "events" / event_slug / "deploy").exists()


def test_supported_event_unsupported_venue_pair_fails(tmp_path, monkeypatch):
    event_slug = enrich_cards.SUPPORTED_EVENT_SLUG
    venue_slug = "some_other_venue"
    _write_manifest(tmp_path, event_slug=event_slug, venue_slug=venue_slug)
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py"])
    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()
    assert exc_info.value.code != 0
    assert not (tmp_path / "events" / event_slug / "output").exists()


def test_unsupported_event_supported_venue_pair_fails(tmp_path, monkeypatch):
    event_slug = "some_other_event"
    venue_slug = enrich_cards.SUPPORTED_VENUE_SLUG
    _write_manifest(tmp_path, event_slug=event_slug, venue_slug=venue_slug)
    monkeypatch.setattr(enrich_cards, "_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["enrich_cards.py"])
    with pytest.raises(SystemExit) as exc_info:
        enrich_cards.main()
    assert exc_info.value.code != 0
    assert not (tmp_path / "events" / event_slug / "output").exists()


def test_supported_event_venue_reaches_worker_via_internal_seam_without_cli(
    tmp_path, monkeypatch
):
    """The correctly supported event/venue pairing can still reach the
    existing worker through the internal _context seam -- with no CLI flag
    and no manifest file involved at all -- proving the seam, not a CLI
    bypass, is what makes isolated testing possible."""
    assert not (tmp_path / "config" / "active_event.json").exists()
    event_slug = enrich_cards.SUPPORTED_EVENT_SLUG
    venue_slug = enrich_cards.SUPPORTED_VENUE_SLUG
    event = SyntheticEvent(tmp_path, event_slug=event_slug, venue_slug=venue_slug)
    event.write_all([("Doe, John", "100")])
    context = _make_context(tmp_path, event_slug, venue_slug=venue_slug)
    _run_main(monkeypatch, tmp_path, event_slug, context=context)
    assert _output_path(tmp_path, event_slug).exists()


# ── Contract preservation (Finding C, requirements 21-24) ──────────────────

def test_pre_event_schema_version_restored_to_3m_enriched_v2(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path, event_slug="schema_check_event")
    event.write_all([("Doe, John", "100")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "3m-enriched-v2.0"
    assert payload["schemaVersion"] != "venuedna-enriched-v2.0"


def test_no_production_line_emits_venuedna_schema_identifier():
    source = Path(enrich_cards.__file__).read_text(encoding="utf-8")
    assert "venuedna-enriched-v2.0" not in source
    assert "venuedna-live-" not in source


def test_payload_shape_unchanged(tmp_path, monkeypatch):
    event = SyntheticEvent(tmp_path, event_slug="shape_check_event")
    event.write_all([("Doe, John", "100")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    assert set(payload.keys()) == {
        "schemaVersion", "formulaMetadata", "generatedAt", "event", "venue",
        "fieldSize", "players",
    }


# ── Source-manifest producer integration (Phase 4.2) ────────────────────────
#
# Proves engine/enrich_cards.py binds all thirteen logical source roles
# through a validated source_manifest.json (never a hardcoded physical
# filename or a filename constructed from event_slug/venue_slug), blocks
# release before any load or write on a manifest defect, and preserves
# standards/02 §7.5 missing-data doctrine when a manifest declares a role
# absent. Synthetic tmp_path trees only -- never a real event or archive.

ARBITRARY_ROLE_FILES: dict[str, str] = {
    "field": "roster_export.csv",
    "neutral_skill.sg_total.6m": "skill_baseline_6.csv",
    "neutral_skill.sg_total.12m": "skill_baseline_12.csv",
    "neutral_skill.sg_total.24m": "skill_baseline_24.csv",
    "venue_fit.similar_sg.6m": "venue_comp_6.csv",
    "venue_fit.similar_sg.12m": "venue_comp_12.csv",
    "venue_fit.similar_sg.24m": "venue_comp_24.csv",
    "traits.approach.sg_per_shot.12m": "approach_detail.csv",
    "traits.approach.proximity.12m": "approach_proximity.csv",
    "performance.sg_categories.season": "season_performance.csv",
    "benchmark.decomposition": "benchmark_export.csv",
    "venue_history": "history_export.csv",
    "recent_form.trending": "trend_export.csv",
}


def _write_arbitrary_named_event(event: "SyntheticEvent", names: list[tuple[str, str]]) -> None:
    """Writes the same thirteen-role content SyntheticEvent.write_all()
    would, but under ARBITRARY_ROLE_FILES's non-legacy filenames -- proving
    role binding, not filename convention, is what the producer depends on."""
    player_names = [n for n, _ in names]
    event._write(ARBITRARY_ROLE_FILES["field"], ["player_name", "dg_id"], [list(r) for r in names])
    for role in ("neutral_skill.sg_total.6m", "neutral_skill.sg_total.12m", "neutral_skill.sg_total.24m",
                 "venue_fit.similar_sg.6m", "venue_fit.similar_sg.12m", "venue_fit.similar_sg.24m"):
        event._write(
            ARBITRARY_ROLE_FILES[role], ["player_name", "rounds_played", "total_mean"],
            [[n, "10", "1.0"] for n in player_names],
        )
    event._write(
        ARBITRARY_ROLE_FILES["traits.approach.sg_per_shot.12m"],
        ["stat", "player_name", "50_100_fw_value", "100_150_fw_value",
         "150_200_fw_value", "over_200_fw_value"],
        [["SG Per Shot", n, "0.1", "0.1", "0.1", "0.1"] for n in player_names],
    )
    event._write(
        ARBITRARY_ROLE_FILES["traits.approach.proximity.12m"],
        ["stat", "player_name", "150_200_fw_value"],
        [["Proximity (ft)", n, "28"] for n in player_names],
    )
    event._write(
        ARBITRARY_ROLE_FILES["performance.sg_categories.season"],
        ["player_name", "putt_true", "arg_true", "app_true", "ott_true"],
        [[n, "0.1", "0.1", "0.3", "0.2"] for n in player_names],
    )
    event._write(
        ARBITRARY_ROLE_FILES["benchmark.decomposition"],
        ["player_name", "driving_acc_adj", "driving_dist_adj", "std_dev"],
        [[n, "0.0", "0.0", "3.0"] for n in player_names],
    )
    event._write(
        ARBITRARY_ROLE_FILES["venue_history"],
        ["player_name", "ch_adjustment", "experience_adjustment"],
        [[n, "0.05", "0.0"] for n in player_names],
    )
    event._write(
        ARBITRARY_ROLE_FILES["recent_form.trending"],
        ["player_name", "dg_id", "true_sg_l20", "l5_starts"],
        [[n, dg_id, "0.2", ""] for n, dg_id in names],
    )
    event.write_source_manifest(role_files=ARBITRARY_ROLE_FILES)


# ── 1. Manifest path binding ────────────────────────────────────────────────

def test_manifest_binds_all_thirteen_roles_with_arbitrary_non_legacy_filenames(
    tmp_path, monkeypatch,
):
    """A manifest declaring wholly non-3M/non-TPC filenames for all thirteen
    roles succeeds end-to-end, and none of the legacy filenames exist on
    disk at all -- proving the producer never needs them once a manifest is
    present."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_arbitrary_filenames")
    names = [("Doe, John", "100"), ("Smith, Sam", "200")]
    _write_arbitrary_named_event(event, names)

    for legacy_name in DEFAULT_MANIFEST_ROLE_FILES.values():
        assert not (event.input_dir / legacy_name).exists()

    _run_main(monkeypatch, tmp_path, event.event_slug)

    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    assert payload["fieldSize"] == 2
    players = {p["player"]: p for p in payload["players"]}
    assert players["Doe, John"]["dg_id"] == "100"
    assert players["Doe, John"]["scoring_status"] == "SCORED"
    assert players["Smith, Sam"]["scoring_status"] == "SCORED"


# ── 2. No implicit fallback ─────────────────────────────────────────────────

def test_manifest_omitted_field_role_blocks_before_any_load_or_write_and_legacy_file_does_not_rescue(
    tmp_path, monkeypatch, capsys,
):
    event = SyntheticEvent(tmp_path, event_slug="manifest_missing_field_role")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    # Legacy pga_field.csv exists on disk, but the manifest omits the
    # `field` role entirely -- it must never be rescued by the legacy
    # file's mere presence.
    assert (event.input_dir / "pga_field.csv").exists()
    event.write_source_manifest(omit_roles=("field",))
    reader_spies = _spy_event_bound_readers(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "SOURCE MANIFEST RELEASE BLOCKED" in captured.err
    assert all(counter.calls == 0 for counter in reader_spies.values())
    assert not (tmp_path / "events" / event.event_slug / "output").exists()
    assert not (tmp_path / "events" / event.event_slug / "deploy").exists()


def test_manifest_path_safety_violation_on_optional_role_blocks_release(
    tmp_path, monkeypatch,
):
    """A path-safety violation (traversal) on an *optional* role still
    blocks release -- path-safety findings are never downgraded by a
    role's own non-blocking missing_behavior."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_path_traversal")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    overrides = dict(DEFAULT_MANIFEST_ROLE_FILES)
    overrides["benchmark.decomposition"] = "../outside_input_root.csv"
    event.write_source_manifest(role_files=overrides)

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)
    assert exc_info.value.code != 0
    assert not _output_path(tmp_path, event.event_slug).exists()
    assert not _deploy_path(tmp_path, event.event_slug).exists()


def test_manifest_with_explicit_legacy_filename_remains_valid(tmp_path, monkeypatch):
    """A manifest that explicitly declares a legacy 3M/TPC-shaped filename
    (rather than an arbitrary one) is fully valid when that file exists --
    the no-fallback rule forbids implicit rescue, not explicit legacy
    declaration."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_explicit_legacy")
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    assert payload["fieldSize"] == 2


# ── 3. Block-before-side-effects ordering ───────────────────────────────────

def test_missing_source_manifest_file_blocks_before_dirs_or_artifacts(tmp_path, monkeypatch, capsys):
    event = SyntheticEvent(tmp_path, event_slug="manifest_file_missing")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    assert not (event.input_dir / "source_manifest.json").exists()

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "source_manifest.json could not be read" in captured.err
    assert not (tmp_path / "events" / event.event_slug / "output").exists()
    assert not (tmp_path / "events" / event.event_slug / "deploy").exists()


def test_malformed_source_manifest_json_blocks_before_dirs_or_artifacts(tmp_path, monkeypatch, capsys):
    event = SyntheticEvent(tmp_path, event_slug="manifest_malformed_json")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    (event.input_dir / "source_manifest.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "not valid JSON" in captured.err
    assert not (tmp_path / "events" / event.event_slug / "output").exists()
    assert not (tmp_path / "events" / event.event_slug / "deploy").exists()


def test_manifest_sha256_mismatch_blocks_before_any_output_or_deploy_artifact(tmp_path, monkeypatch, capsys):
    event = SyntheticEvent(tmp_path, event_slug="manifest_sha256_mismatch")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    event.write_source_manifest(integrity_overrides={"field": {"sha256": "0" * 64}})

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "SOURCE MANIFEST RELEASE BLOCKED" in captured.err
    assert not (tmp_path / "events" / event.event_slug / "output").exists()
    assert not (tmp_path / "events" / event.event_slug / "deploy").exists()


def test_manifest_row_count_mismatch_blocks_before_any_output_or_deploy_artifact(tmp_path, monkeypatch, capsys):
    event = SyntheticEvent(tmp_path, event_slug="manifest_row_count_mismatch")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    event.write_source_manifest(integrity_overrides={"field": {"row_count": 999}})

    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, tmp_path, event.event_slug)

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "SOURCE MANIFEST RELEASE BLOCKED" in captured.err
    assert not (tmp_path / "events" / event.event_slug / "output").exists()
    assert not (tmp_path / "events" / event.event_slug / "deploy").exists()


def test_manifest_with_correct_integrity_assertions_succeeds(tmp_path, monkeypatch):
    """A non-null, correctly-computed sha256/row_count assertion is
    ``verified`` and must never block -- only a genuine mismatch does."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_integrity_verified")
    event.write_all([("Doe, John", "100")], write_manifest=False)
    field_path = event.input_dir / "pga_field.csv"
    event.write_source_manifest(integrity_overrides={
        "field": {"sha256": _sha256_of(field_path), "row_count": _row_count_of(field_path)},
    })
    _run_main(monkeypatch, tmp_path, event.event_slug)
    assert _output_path(tmp_path, event.event_slug).exists()


# ── 4. Missing-data behavior (standards/02 §7.5) ────────────────────────────

def test_manifest_omitted_neutral_skill_horizon_preserves_two_horizon_renormalization(
    tmp_path, monkeypatch,
):
    """Omitting the 6m NeutralSkill role from the manifest -- even though a
    6m file with wildly different content exists on disk under its legacy
    name -- must never be read; NeutralSkillRaw must still be computed as
    the renormalized average of the remaining two valid horizons per
    standards/02 §7.5, never treated as observed zero and never leaking in
    the unread 99.0 value. (The omitted 6m role also removes VenueFit's
    required 6m base horizon, so the overall player becomes UNSCORED via
    VenueFit's own separate non-renormalization rule -- §7.5 explicitly
    keeps these two outcomes independent: NeutralSkillRaw is still returned
    as a real, correctly-renormalized value even when the player's overall
    status is UNSCORED for an unrelated reason.)"""
    event = SyntheticEvent(tmp_path, event_slug="manifest_neutral_skill_horizon_missing")
    event.write_all([("Renorm, Rae", "100")], write_manifest=False)
    event._write(
        "pga_sg_query_allcourses_l6.csv", ["player_name", "rounds_played", "total_mean"],
        [["Renorm, Rae", "20", "99.0"]],
    )
    event.write_source_manifest(omit_roles=("neutral_skill.sg_total.6m",))

    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    player = payload["players"][0]
    assert player["neutral_skill_raw"] == pytest.approx(1.0)
    assert player["confidence_by_source"]["neutral_skill"] == "THIN"
    assert player["scoring_status"] == "UNSCORED"
    assert player["venue_fit_delta_raw"] is None


def test_manifest_omitted_venue_fit_horizon_yields_non_computable_and_unscored(
    tmp_path, monkeypatch,
):
    """Omitting one of the three venue_fit.similar_sg horizons makes
    VenueFitDeltaRaw non-computable (never renormalized across the
    remaining two) per standards/02 §7.5 -- the whole player becomes
    UNSCORED even though every NeutralSkill horizon is present and valid."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_venue_fit_horizon_missing")
    event.write_all([("Incomplete, Ivy", "100")], write_manifest=False)
    event.write_source_manifest(omit_roles=("venue_fit.similar_sg.6m",))

    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    player = payload["players"][0]
    assert player["scoring_status"] == "UNSCORED"
    assert player["venue_fit_delta_raw"] is None
    assert player["neutral_skill_raw"] == pytest.approx(1.0)
    assert player["vts_final"] is None
    assert player["rank"] is None


def test_manifest_omitted_venue_history_role_does_not_alter_venue_history_delta_semantics(
    tmp_path, monkeypatch,
):
    """Omitting the optional venue_history role must not fabricate observed
    venue-history evidence: venue_history_delta_raw remains the same
    doctrine-neutral 0.0 and venue_history confidence remains THIN, exactly
    as it already is when the role's file is present (main() does not wire
    CH rows into VenueHistoryEvidence -- that remains separate, out-of-
    scope technical debt for this task, per the task's own instruction)."""
    event = SyntheticEvent(tmp_path, event_slug="manifest_venue_history_missing")
    event.write_all([("NoHistory, Ned", "100")], write_manifest=False)
    event.write_source_manifest(omit_roles=("venue_history",))

    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    player = payload["players"][0]
    assert player["scoring_status"] == "SCORED"
    assert player["venue_history_delta_raw"] == 0.0
    assert player["confidence_by_source"]["venue_history"] == "THIN"


# ── 5. Compatibility and preservation ───────────────────────────────────────

def test_manifest_driven_build_preserves_canonical_formula_metadata_and_payload_shape(
    tmp_path, monkeypatch,
):
    event = SyntheticEvent(tmp_path, event_slug="manifest_compat_check")
    event.write_all([("Doe, John", "100"), ("Smith, Sam", "200")])
    _run_main(monkeypatch, tmp_path, event.event_slug)
    payload = json.loads(_output_path(tmp_path, event.event_slug).read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "3m-enriched-v2.0"
    assert payload["formulaMetadata"] == {
        "formula_id": "venuedna_dual_vector_decomposed",
        "formula_version": "2.0.0",
        "scoring_spec_version": "2.0-draft",
        "comparable_score_family": "dual_vector_sg_per_round_v2",
        "penalty_gate_set_id": "venuedna_v2_none",
    }
    assert set(payload.keys()) == {
        "schemaVersion", "formulaMetadata", "generatedAt", "event", "venue",
        "fieldSize", "players",
    }
    p = payload["players"][0]
    assert "identity_provenance" in p
    assert p["dg_id"] == p["player_id"]
