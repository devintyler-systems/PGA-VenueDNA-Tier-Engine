"""tests/test_wyndham_retrospective_fixture_smoke.py
Phase 6.2 — Test-Only Producer Smoke Test and UNSCORED Propagation
Validation.

Runs the reusable root producer's canonical scoring path
(``engine/enrich_cards.py::main()``) against the committed, fenced Wyndham
retrospective development fixture at ``events/2026_wyndham_championship/``,
entirely in-memory, via the internal ``_capture_only`` test-injection seam
(Phase 6.2; see the seam's docstring in ``engine/enrich_cards.py::main()``).

This is a strictly test-only producer-path validation. It is not
authorization for an official Wyndham projection, live artifact, board
export, or deploy payload -- see ``events/2026_wyndham_championship/
RETROSPECTIVE_FIXTURE_README.md`` and ``docs/decisions/
2026_08_06_wyndham_retrospective_fixture_authorization.md``.

Every test in this file:
  * reads the real, committed fixture input files (read-only);
  * never monkeypatches ``engine.enrich_cards._ROOT`` -- the producer's own
    repo root is used, so the source manifest's containment checks resolve
    against the real repository exactly as they would in production;
  * injects an in-memory ``EventContext`` directly (never via
    ``config/active_event.json``, a CLI flag, or an environment variable);
  * calls ``main(_context=..., _capture_only=True)`` so no output, deploy,
    or audit artifact is ever created;
  * asserts the fixture's ``output/``, ``audit/``, ``deploy/``, and
    ``deploy/data/`` directories are empty both before and after the run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

import enrich_cards  # noqa: E402
from event_context import EventContext  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
EVENT_SLUG = "2026_wyndham_championship"
VENUE_SLUG = "sedgefield_country_club"
FIXTURE_ROOT = REPO_ROOT / "events" / EVENT_SLUG

FENCE_DIRS = ("output", "audit", "deploy", "deploy/data")

# Phase 6.3 authorized exactly these three local, non-deployable board-shell
# files as direct children of deploy/ (tools/validate_scoring_doctrine.py;
# RETROSPECTIVE_FIXTURE_README.md "Phase 6.3 board-shell allowance"). They
# are excluded from the ``deploy`` fence-emptiness check below only --
# ``deploy/data`` and every other fence directory remain fully empty with no
# allowance.
BOARD_SHELL_ALLOWED_FILES = frozenset({"index.html", "app.js", "styles.css"})


def _fixture_context() -> EventContext:
    """The real, committed fixture directory as the producer's event_root --
    never a tmp_path copy. ``venue_profile``/``deploy_root``/``audit_root``
    are not read anywhere in main()'s body (grep-verified); they are set to
    their doctrinally-expected paths purely for EventContext shape
    completeness, not because main() opens them.
    """
    return EventContext(
        event_slug=EVENT_SLUG,
        event_name="Wyndham Championship",
        venue_slug=VENUE_SLUG,
        venue_name="Sedgefield Country Club",
        year=2026,
        event_root=FIXTURE_ROOT,
        venue_profile=(
            REPO_ROOT / "library" / "venues" / VENUE_SLUG / f"{VENUE_SLUG}_venue_profile.md"
        ),
        deploy_root=FIXTURE_ROOT / "deploy",
        audit_root=FIXTURE_ROOT / "audit",
    )


def _fence_inventory() -> dict[str, list[str]]:
    """Recursive inventory of every fenced directory's file contents,
    relative paths only, deterministically sorted. The Phase 6.3-authorized
    board-shell files are excluded from the ``deploy`` entry only; every
    other fence directory, including ``deploy/data``, is reported in full
    with no allowance."""
    inventory: dict[str, list[str]] = {}
    for rel in FENCE_DIRS:
        target = FIXTURE_ROOT / rel
        if not target.exists():
            inventory[rel] = []
            continue
        files = sorted(
            str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()
        )
        if rel == "deploy":
            files = [f for f in files if f not in BOARD_SHELL_ALLOWED_FILES]
        inventory[rel] = files
    return inventory


def _repo_relative_files_under_event_root() -> set[str]:
    return {
        str(p.relative_to(FIXTURE_ROOT)) for p in FIXTURE_ROOT.rglob("*") if p.is_file()
    }


@pytest.fixture(scope="module")
def smoke_result():
    """Runs the producer exactly once via the `_capture_only` seam and
    shares the in-memory result across every assertion test below -- the
    fixture directory itself is asserted empty before AND after this single
    invocation, and every other test in this module only re-reads the
    already-captured in-memory ``records`` list, never re-running main()."""
    before_fence = _fence_inventory()
    before_files = _repo_relative_files_under_event_root()
    assert all(files == [] for files in before_fence.values()), (
        f"Fixture fence directories must start empty: {before_fence}"
    )

    context = _fixture_context()
    records = enrich_cards.main(_context=context, _capture_only=True)

    after_fence = _fence_inventory()
    after_files = _repo_relative_files_under_event_root()

    return {
        "records": records,
        "before_fence": before_fence,
        "after_fence": after_fence,
        "before_files": before_files,
        "after_files": after_files,
    }


def _by_name(records: list[dict], name: str) -> dict:
    matches = [r for r in records if r["player"] == name]
    assert len(matches) == 1, f"expected exactly one record for {name!r}, found {len(matches)}"
    return matches[0]


# ── 1. No-side-effect proof ──────────────────────────────────────────────────

def test_no_new_files_under_event_root(smoke_result):
    """Zero new files anywhere under events/2026_wyndham_championship/ --
    not just the fenced directories -- as a result of the smoke run."""
    assert smoke_result["after_files"] == smoke_result["before_files"]


def test_fence_directories_remain_empty_before_and_after(smoke_result):
    for rel in FENCE_DIRS:
        assert smoke_result["before_fence"][rel] == [], rel
        assert smoke_result["after_fence"][rel] == [], rel


def test_no_official_artifact_files_exist(smoke_result):
    """No board export, player brief, event payload, scored CSV, or any
    other official artifact exists anywhere under the fixture root."""
    forbidden_suffixes = (
        "_event_payload.json", "_player_briefs.json", "_vts_full.csv",
        "_trait_form_matrix.csv", "_links.json", "board_export.json",
    )
    for rel_path in smoke_result["after_files"]:
        assert not rel_path.endswith(forbidden_suffixes), rel_path


# ── 2. Field and source counts ───────────────────────────────────────────────

def test_field_source_contains_147_players():
    import csv
    with (FIXTURE_ROOT / "input" / "pga_field_teetimes.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 147


UNSCORED_SOURCE_ABSENT = ("Skinns, David", "Moore, Taylor")
UNSCORED_MIXED_HORIZON = ("McGirt, William", "Pan, C.T.")
ALL_UNSCORED_NAMES = frozenset(UNSCORED_SOURCE_ABSENT) | frozenset(UNSCORED_MIXED_HORIZON)
SCORED_COUNT = 143
UNSCORED_COUNT = 4


def test_exactly_143_scored_and_4_unscored(smoke_result):
    """Verified against the real, committed fixture through the protected
    canonical scoring engine (engine/venuedna_scoring.py). Two UNSCORED
    players are source-absent (Skinns, Moore); two more -- McGirt and Pan --
    are UNSCORED for a distinct, doctrine-consistent reason: a mixed
    VenueFit horizon state (see test_mcgirt_and_pan_mixed_horizon_venue_fit_
    is_non_computable below). Neither pair is a fabricated or narrowed
    expectation -- both are the actual computed result of running the
    unmodified producer against the unmodified fixture."""
    records = smoke_result["records"]
    assert len(records) == 147

    scored = [r for r in records if r["scoring_status"] == "SCORED"]
    unscored = [r for r in records if r["scoring_status"] == "UNSCORED"]

    assert len(scored) == SCORED_COUNT
    assert len(unscored) == UNSCORED_COUNT
    assert {r["player"] for r in unscored} == ALL_UNSCORED_NAMES


def test_official_scored_field_pools_contain_only_143(smoke_result):
    records = smoke_result["records"]
    ranked = [r for r in records if r["rank"] is not None]
    tiered = [r for r in records if r["tier"] is not None]
    vts_scored = [r for r in records if r["vts_final"] is not None]

    assert len(ranked) == SCORED_COUNT
    assert len(tiered) == SCORED_COUNT
    assert len(vts_scored) == SCORED_COUNT
    assert {r["scoring_status"] for r in ranked} == {"SCORED"}
    assert {r["scoring_status"] for r in tiered} == {"SCORED"}

    ranks = sorted(r["rank"] for r in ranked)
    assert ranks == list(range(1, SCORED_COUNT + 1))


# ── 3. David Skinns ───────────────────────────────────────────────────────────

def test_skinns_dg_id_and_field_presence(smoke_result):
    skinns = _by_name(smoke_result["records"], "Skinns, David")
    assert skinns["dg_id"] == "10873"


def test_skinns_retained_unscored_with_null_officials(smoke_result):
    skinns = _by_name(smoke_result["records"], "Skinns, David")

    assert skinns["scoring_status"] == "UNSCORED"
    assert skinns["rank"] is None
    assert skinns["tier"] is None
    assert skinns["vts_final"] is None
    assert skinns["neutralSkillIndex"] is None
    assert skinns["prepenalty_vts"] is None
    for field in ("winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct"):
        assert skinns[field] is None, field


def test_skinns_has_all_neutral_skill_horizons_but_no_venue_fit(smoke_result):
    """Skinns has all three NeutralSkill/all-course horizons (his
    neutral_skill_raw is computable) but is absent from all three required
    similar-course VenueFit horizons (venue_fit_delta_raw non-computable)."""
    skinns = _by_name(smoke_result["records"], "Skinns, David")

    assert skinns["neutral_skill_raw"] is not None
    assert skinns["venue_fit_delta_raw"] is None
    assert skinns["data_depth"] == "MISSING"
    assert skinns["pre_penalty_raw"] is None
    assert skinns["post_gate_raw"] is None


def test_skinns_not_silently_assigned_debut(smoke_result):
    """A missing similar-course source row is incomplete VenueFit evidence,
    never the DEBUT state -- DEBUT requires a *present* zero-round row.
    ``course_debut`` is an internal preparation field stripped from the
    final payload (see _OUTPUT_PRIVATE_FIELDS in engine/enrich_cards.py);
    the public, emitted signal for this is ``data_depth``."""
    skinns = _by_name(smoke_result["records"], "Skinns, David")
    assert skinns["data_depth"] != "DEBUT"
    assert skinns["data_depth"] == "MISSING"


# ── 4. Taylor Moore ───────────────────────────────────────────────────────────

def test_moore_retained_unscored_with_null_officials(smoke_result):
    moore = _by_name(smoke_result["records"], "Moore, Taylor")

    assert moore["scoring_status"] == "UNSCORED"
    assert moore["rank"] is None
    assert moore["tier"] is None
    assert moore["vts_final"] is None
    assert moore["neutralSkillIndex"] is None
    assert moore["prepenalty_vts"] is None
    for field in ("winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct"):
        assert moore[field] is None, field


def test_moore_has_no_neutral_skill_horizons(smoke_result):
    """Moore is absent from all three required all-course NeutralSkill
    horizons -- fewer than two valid horizons means NeutralSkillRaw itself
    is non-computable (UNSCORED at the NeutralSkill composite layer), even
    though he carries all three similar-course VenueFit horizons."""
    moore = _by_name(smoke_result["records"], "Moore, Taylor")

    assert moore["neutral_skill_raw"] is None
    assert moore["pre_penalty_raw"] is None
    assert moore["post_gate_raw"] is None


# ── 4b. McGirt and Pan -- mixed-horizon VenueFit UNSCORED ───────────────────
#
# Distinct from Skinns (source-absent from all three similar-course
# horizons) and Moore (source-absent from all three all-course horizons):
# McGirt and Pan are each PRESENT in all three venue_fit.similar_sg.*
# horizons, but their evidence is internally inconsistent --
#   * L6 and L12: a present row with rounds_played=0 and the documented
#     source-native null total_mean sentinel -- individually a valid
#     zero-observation DEBUT row.
#   * L24: a present row with real, non-zero rounds_played and a finite
#     total_mean -- real observed data, not DEBUT.
# standards/02 SS7.5 / engine/venuedna_scoring.py::compute_venue_fit() (a
# protected file, unmodified here) requires VenueFit's fixed three-horizon
# formula to be either uniformly DEBUT across all three horizons or fully
# computable (finite) across all three -- never renormalized, never a
# partial blend. This specific mixed state satisfies neither path, so it is
# genuinely non-computable, not a bug in the smoke-test seam.

def test_mcgirt_and_pan_present_in_all_similar_course_horizons(smoke_result):
    """McGirt and Pan are not missing source rows -- confirms their
    UNSCORED status is not the same source-absent mechanism as Skinns."""
    import csv

    similar_files = {
        h: FIXTURE_ROOT / "input" / f"pga_sg_query_sedgefield_country_club_similar_l{h}.csv"
        for h in ("6", "12", "24")
    }
    for name in UNSCORED_MIXED_HORIZON:
        for path in similar_files.values():
            with path.open(encoding="utf-8") as f:
                rows = [r for r in csv.DictReader(f) if r["player_name"] == name]
            assert len(rows) == 1, (name, path.name)


def test_mcgirt_and_pan_mixed_horizon_venue_fit_is_non_computable(smoke_result):
    for name in UNSCORED_MIXED_HORIZON:
        record = _by_name(smoke_result["records"], name)
        assert record["scoring_status"] == "UNSCORED"
        assert record["data_depth"] == "MISSING"
        assert record["data_depth"] != "DEBUT"
        assert record["venue_fit_delta_raw"] is None
        assert record["pre_penalty_raw"] is None
        assert record["post_gate_raw"] is None
        # No horizon renormalization: VenueFit is not computed as if only
        # the finite (24m) horizon existed -- the whole component is null.


def test_mcgirt_and_pan_null_official_score_rank_tier_probabilities(smoke_result):
    for name in UNSCORED_MIXED_HORIZON:
        record = _by_name(smoke_result["records"], name)
        assert record["rank"] is None
        assert record["tier"] is None
        assert record["vts_final"] is None
        assert record["neutralSkillIndex"] is None
        for field in ("winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct"):
            assert record[field] is None, (name, field)


# ── 5. Daniel Berger and Troy Merritt excluded from field-based results ─────

def test_berger_and_merritt_absent_from_official_records(smoke_result):
    names = {r["player"] for r in smoke_result["records"]}
    assert "Berger, Daniel" not in names
    assert "Merritt, Troy" not in names


def test_berger_and_merritt_source_only_rows_produce_no_official_record():
    """Both have source-only rows (Berger in all three similar-course
    horizons; Merritt in all three all-course horizons) but neither is in
    the field file -- their rows must never generate an official record,
    rank, tier, score, or probability. Field-index membership, not source
    presence, is what admits a player into official results."""
    import csv

    with (FIXTURE_ROOT / "input" / "pga_field_teetimes.csv").open(encoding="utf-8") as f:
        field_names = {row["player_name"] for row in csv.DictReader(f)}
    assert "Berger, Daniel" not in field_names
    assert "Merritt, Troy" not in field_names

    with (FIXTURE_ROOT / "input" / "pga_sg_query_sedgefield_country_club_similar_l6.csv").open(
        encoding="utf-8"
    ) as f:
        assert any(row["player_name"] == "Berger, Daniel" for row in csv.DictReader(f))

    with (FIXTURE_ROOT / "input" / "pga_sg_query_allcourses_l6.csv").open(encoding="utf-8") as f:
        assert any(row["player_name"] == "Merritt, Troy" for row in csv.DictReader(f))


# ── 6. Canonical scored records ──────────────────────────────────────────────

def test_scored_records_carry_unchanged_formula_v2_metadata(smoke_result):
    scored = [r for r in smoke_result["records"] if r["scoring_status"] == "SCORED"]
    assert scored, "no scored players to check"
    for record in scored:
        assert record["formula_id"] == "venuedna_dual_vector_decomposed"
        assert record["formula_version"] == "2.0.0"
        assert record["comparable_score_family"] == "dual_vector_sg_per_round_v2"
        assert record["penalty_gate_set_id"] == "venuedna_v2_none"
        assert record["penalties_applied"] == []
        assert record["gates_applied"] == []


def test_scored_records_have_populated_officials_within_canonical_range(smoke_result):
    scored = [r for r in smoke_result["records"] if r["scoring_status"] == "SCORED"]
    for record in scored:
        assert 0.0 <= record["vts_final"] <= 100.0
        assert 0.0 <= record["neutralSkillIndex"] <= 100.0
        assert record["tier"] in ("T1", "T2", "T3", "T4", "T5")
        assert record["top20Pct"] >= record["top10Pct"] >= record["top5Pct"] >= record["winPct"]
        assert 20.0 <= record["makeCutPct"] <= 98.0


def test_unscored_players_excluded_from_normalization_and_probabilities(smoke_result):
    """UNSCORED players never participate in field-normalized z-scoring or
    the tempered-softmax probability vectors -- their vts_final/probability
    fields are null, not a computed value derived alongside the scored
    field (already covered by the null-officials tests above); this test
    additionally confirms no UNSCORED player receives a Tier 1-5 label."""
    unscored = [r for r in smoke_result["records"] if r["scoring_status"] == "UNSCORED"]
    assert len(unscored) == UNSCORED_COUNT
    for record in unscored:
        assert record["tier"] is None
        assert record["rank"] is None
        assert record["vts_final"] is None
        assert record["winPct"] is None
        assert record["top5Pct"] is None
        assert record["top10Pct"] is None
        assert record["top20Pct"] is None
