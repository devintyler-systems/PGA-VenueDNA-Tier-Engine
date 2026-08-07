"""tests/test_source_manifest_resolver.py
Synthetic-fixture test suite for engine/source_manifest_resolver.py.

The retrospective Wyndham fixture tests below are the sole exception to the
otherwise tmp_path-only rule. They read its explicitly authorized inputs and
assert no output or deploy artifact is created.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import source_manifest_resolver as smr  # noqa: E402
from venuedna_scoring import SimilarCourseRow, compute_player_projection  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
WYNDHAM_FIXTURE_ROOT = REPO_ROOT / "events" / "2026_wyndham_championship"
WYNDHAM_INPUT_ROOT = WYNDHAM_FIXTURE_ROOT / "input"


def _make_directory_link(link_path: Path, target: Path) -> None:
    """Create a directory symlink, falling back to an NTFS junction (via
    ``mklink /J``, which does not require elevated privilege) on Windows
    environments where symlink creation is denied. Skips the test entirely
    only if neither mechanism is available.
    """
    try:
        link_path.symlink_to(target, target_is_directory=True)
        return
    except OSError:
        pass
    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and link_path.exists():
            return
    pytest.skip("neither symlink nor junction creation is permitted in this environment")


# ── Fixture construction helpers ─────────────────────────────────────────────

FIELD_CSV = (
    'player_name,rounds_played,total_mean\n'
    '"Doe, John",10,0.512\n'
    '"Smith, Jane",12,0.301\n'
)

ROLE_FILENAMES: dict[str, str] = {
    "field": "field.csv",
    "neutral_skill.sg_total.6m": "ns_6m.csv",
    "neutral_skill.sg_total.12m": "ns_12m.csv",
    "neutral_skill.sg_total.24m": "ns_24m.csv",
    "venue_fit.similar_sg.6m": "vf_6m.csv",
    "venue_fit.similar_sg.12m": "vf_12m.csv",
    "venue_fit.similar_sg.24m": "vf_24m.csv",
    "traits.approach.sg_per_shot.12m": "app_sg.csv",
    "traits.approach.proximity.12m": "app_prox.csv",
    "performance.sg_categories.season": "perf.csv",
    "benchmark.decomposition": "decomp.csv",
    "venue_history": "venue_history.csv",
    "recent_form.trending": "trending.csv",
}


def build_context(tmp_path: Path, *, event_slug="2026_example_open", venue_slug="example_venue") -> smr.SourceManifestContext:
    repo_root = tmp_path / "repo"
    event_root = repo_root / "events" / event_slug
    input_dir = event_root / "input"
    input_dir.mkdir(parents=True)
    return smr.SourceManifestContext(
        event_slug=event_slug, venue_slug=venue_slug, event_root=event_root, repo_root=repo_root,
    )


def write_source_file(context: smr.SourceManifestContext, filename: str, content: str = FIELD_CSV) -> Path:
    path = context.input_root / filename
    path.write_text(content, encoding="utf-8")
    return path


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_count_of(content: str) -> int:
    lines = content.splitlines()
    return max(0, len(lines) - 1)


def _base_entry(context: smr.SourceManifestContext, role: str, *, content: str = FIELD_CSV, **overrides) -> dict:
    filename = ROLE_FILENAMES[role]
    path = write_source_file(context, filename, content)
    entry = {
        "role": role,
        "path": filename,
        "required": smr.ROLE_REQUIRED[role],
        "missing_behavior": smr.ROLE_MISSING_BEHAVIOR[role],
        "schema_id": f"venuedna.source.{role}.v1",
        "identity_key": "player_name",
        "encoding": "utf-8",
        "sha256": _sha256_of(path),
        "row_count": _row_count_of(content),
        "metadata": {},
    }
    if role in smr.SIMILAR_SG_ROLES:
        entry["metadata"] = {
            "similar_course_set_id": "example_venue_similar_v1",
            "set_version": 1,
            "set_provenance": "manual_datagolf_export_2026",
            "horizon_months": smr.SIMILAR_SG_HORIZON_MONTHS[role],
        }
    if role == "venue_history":
        entry["metadata"] = {"venue_slug": context.venue_slug}
    entry.update(overrides)
    return entry


def build_complete_manifest(context: smr.SourceManifestContext, *, overrides_by_role: dict | None = None) -> dict:
    overrides_by_role = overrides_by_role or {}
    sources = [
        _base_entry(context, role, **overrides_by_role.get(role, {}))
        for role in smr.REQUIRED_ROLES
    ]
    return {
        "schema_version": "1.0",
        "event_slug": context.event_slug,
        "venue_slug": context.venue_slug,
        "as_of": "2026-08-06T00:00:00Z",
        "sources": sources,
    }


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


# ── 1. Valid complete thirteen-role manifest ─────────────────────────────────

def test_valid_complete_manifest_resolves_all_thirteen_roles(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)

    before = snapshot(tmp_path)
    result = smr.resolve_source_manifest(manifest, context=context)
    after = snapshot(tmp_path)

    assert after == before, "resolver must not write any file"
    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert set(result.resolved_sources) == set(smr.REQUIRED_ROLES)
    for role in smr.REQUIRED_ROLES:
        resolved = result.resolved_sources[role]
        assert resolved.resolved_path.is_file()
        assert resolved.sha256_outcome.state == smr.INTEGRITY_VERIFIED
        assert resolved.row_count_outcome.state == smr.INTEGRITY_VERIFIED


# ── 2. Duplicate role ─────────────────────────────────────────────────────────

def test_duplicate_role_is_release_blocking(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["sources"].append(dict(manifest["sources"][0]))  # duplicate "field"

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "DUPLICATE_ROLE" for f in result.blockers)


# ── 3. Required-role omission ─────────────────────────────────────────────────

def test_required_role_omission_is_release_blocking(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["sources"] = [s for s in manifest["sources"] if s["role"] != "field"]

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(
        f.code == "SOURCE_MISSING_BLOCK_RELEASE" and f.role == "field" for f in result.blockers
    )
    assert "field" not in result.resolved_sources


# ── 4. Schema-version / event-slug / venue-slug mismatch ────────────────────

def test_schema_version_mismatch_is_release_blocking(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["schema_version"] = "2.0"

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "SCHEMA_VERSION_MISMATCH" for f in result.blockers)


def test_event_slug_mismatch_is_release_blocking(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["event_slug"] = "2026_a_different_open"

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "EVENT_SLUG_MISMATCH" for f in result.blockers)


def test_venue_slug_mismatch_is_release_blocking(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["venue_slug"] = "a_different_venue"

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "VENUE_SLUG_MISMATCH" for f in result.blockers)


# ── 5. Path-safety rejections ────────────────────────────────────────────────

@pytest.mark.parametrize("bad_path,expected_code", [
    ("/etc/passwd", "PATH_ABSOLUTE"),
    ("C:/inject.csv", "PATH_ABSOLUTE"),
    ("sub\\dir\\file.csv", "PATH_BACKSLASH"),
    ("../outside.csv", "PATH_TRAVERSAL"),
    ("2026_Finished_Events/leak.csv", "PATH_ARCHIVED_SEGMENT_DECLARED"),
])
def test_path_safety_lexical_rejections(tmp_path, bad_path, expected_code):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"path": bad_path}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == expected_code and f.role == "field" for f in result.blockers)
    assert "field" not in result.resolved_sources


def test_non_regular_file_target_rejected(tmp_path):
    context = build_context(tmp_path)
    directory_path = context.input_root / "a_directory.csv"
    directory_path.mkdir()
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"path": "a_directory.csv"}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "PATH_NOT_REGULAR_FILE" and f.role == "field" for f in result.blockers)


def test_symlink_escape_within_repo_but_outside_input_root_rejected(tmp_path):
    """A symlink target that stays inside repo_root but lands outside the
    event's own input root -- proves §9.6 Rule 3's added requirement beyond
    plain repository containment: the resolved target must stay inside
    EventContext.event_root / "input" specifically.
    """
    context = build_context(tmp_path)
    outside_input_root = context.repo_root / "outside_input_root"
    outside_input_root.mkdir()
    (outside_input_root / "leak.csv").write_text(FIELD_CSV, encoding="utf-8")

    junction_path = context.input_root / "linked_dir"
    _make_directory_link(junction_path, outside_input_root)

    manifest = build_complete_manifest(
        context, overrides_by_role={"field": {"path": "linked_dir/leak.csv"}},
    )
    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "PATH_INPUT_ROOT_ESCAPE" and f.role == "field" for f in result.blockers)


def test_symlink_escape_outside_repository_rejected(tmp_path):
    """A symlink target entirely outside repo_root -- proves containment is
    checked against the resolved physical path, not the declared text, and
    that a repo-level escape is caught even before the narrower input-root
    check.
    """
    context = build_context(tmp_path)
    outside_repo = tmp_path / "outside_repo"
    outside_repo.mkdir()
    (outside_repo / "leak.csv").write_text(FIELD_CSV, encoding="utf-8")

    junction_path = context.input_root / "linked_dir"
    _make_directory_link(junction_path, outside_repo)

    manifest = build_complete_manifest(
        context, overrides_by_role={"field": {"path": "linked_dir/leak.csv"}},
    )
    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "PATH_REPOSITORY_ESCAPE" and f.role == "field" for f in result.blockers)


# ── 6. Missing required vs. optional source scoping ─────────────────────────

def test_missing_required_source_blocks_release(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["sources"] = [s for s in manifest["sources"] if s["role"] != "field"]

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked


def test_missing_optional_source_is_scoped_warning_only(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    manifest["sources"] = [s for s in manifest["sources"] if s["role"] != "venue_history"]

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert any(
        f.severity == smr.SEVERITY_WARNING and f.code == "SOURCE_MISSING" and f.role == "venue_history"
        for f in result.warnings
    )
    assert "venue_history" not in result.resolved_sources


# ── 7. Similar-course provenance mismatch ────────────────────────────────────

def test_similar_course_provenance_mismatch_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(
        context,
        overrides_by_role={
            "venue_fit.similar_sg.12m": {
                "metadata": {
                    "similar_course_set_id": "different_set_id",
                    "set_version": 1,
                    "set_provenance": "manual_datagolf_export_2026",
                    "horizon_months": 12,
                },
            },
        },
    )

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "SIMILAR_COURSE_PROVENANCE_MISMATCH" for f in result.blockers)


# ── 8. Similar-course horizon_months mismatch ────────────────────────────────

def test_similar_course_horizon_months_mismatch_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(
        context,
        overrides_by_role={
            "venue_fit.similar_sg.6m": {
                "metadata": {
                    "similar_course_set_id": "example_venue_similar_v1",
                    "set_version": 1,
                    "set_provenance": "manual_datagolf_export_2026",
                    "horizon_months": 12,  # wrong -- role suffix is 6m
                },
            },
        },
    )

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(
        f.code == "SIMILAR_COURSE_HORIZON_MONTHS_MISMATCH" and f.role == "venue_fit.similar_sg.6m"
        for f in result.blockers
    )


# ── 9. Venue-history metadata venue mismatch ─────────────────────────────────

def test_venue_history_metadata_venue_mismatch_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(
        context,
        overrides_by_role={"venue_history": {"metadata": {"venue_slug": "wrong_venue"}}},
    )

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "VENUE_HISTORY_VENUE_MISMATCH" for f in result.blockers)


# ── 10. Secret/credential metadata ───────────────────────────────────────────

def test_secret_credential_metadata_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(
        context,
        overrides_by_role={"field": {"metadata": {"datagolf_api_key": "sk-super-secret-value"}}},
    )

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(f.code == "CREDENTIAL_IN_METADATA" and f.role == "field" for f in result.blockers)


# ── 11. sha256 integrity states ──────────────────────────────────────────────

def test_sha256_verified(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.resolved_sources["field"].sha256_outcome.state == smr.INTEGRITY_VERIFIED


def test_sha256_mismatch_blocks(tmp_path):
    context = build_context(tmp_path)
    wrong_hash = "0" * 64
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"sha256": wrong_hash}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert result.resolved_sources["field"].sha256_outcome.state == smr.INTEGRITY_MISMATCH
    assert any(f.code == "SHA256_MISMATCH" and f.role == "field" for f in result.blockers)


def test_sha256_null_is_not_asserted_and_never_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"sha256": None}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert result.resolved_sources["field"].sha256_outcome.state == smr.INTEGRITY_NOT_ASSERTED


def test_sha256_malformed_format_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(
        context, overrides_by_role={"field": {"sha256": "not-a-valid-digest"}},
    )

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert result.resolved_sources["field"].sha256_outcome.state == smr.INTEGRITY_MISMATCH
    assert any(f.code == "SHA256_MISMATCH" and f.role == "field" for f in result.blockers)


def test_sha256_unreadable_source_is_unable_to_validate(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    # Declare a sha256 for benchmark.decomposition but point it at a file
    # that does not exist -- an assertion about an unreachable file must be
    # unable_to_validate and release-blocking, independent of the role's
    # own (non-blocking) missing_behavior.
    for source in manifest["sources"]:
        if source["role"] == "benchmark.decomposition":
            source["path"] = "does_not_exist.csv"
            source["sha256"] = "a" * 64

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(
        f.code == "SHA256_UNABLE_TO_VALIDATE" and f.role == "benchmark.decomposition"
        for f in result.blockers
    )
    assert "benchmark.decomposition" not in result.resolved_sources


# ── 12. row_count integrity states ───────────────────────────────────────────

def test_row_count_verified(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_VERIFIED


def test_row_count_mismatch_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"row_count": 999}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_MISMATCH
    assert any(f.code == "ROW_COUNT_MISMATCH" and f.role == "field" for f in result.blockers)


def test_row_count_null_is_not_asserted_and_never_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"row_count": None}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_NOT_ASSERTED


def test_row_count_malformed_value_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"row_count": "two"}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_MISMATCH
    assert any(f.code == "ROW_COUNT_MISMATCH" and f.role == "field" for f in result.blockers)


def test_row_count_negative_value_blocks(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context, overrides_by_role={"field": {"row_count": -1}})

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_MISMATCH


def test_row_count_header_blank_and_malformed_row_treatment(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)

    content = (
        'player_name,rounds_played,total_mean\n'   # header -- excluded
        '"Doe, John",10,0.512\n'                    # data row 1
        '\n'                                        # blank line -- counted
        '"Malformed Row, Missing A Field"\n'         # malformed row -- counted
        '"Smith, Jane",12,0.301\n'                   # data row 2
    )
    declared_row_count = 4  # 5 physical lines minus the 1 header line
    field_path = context.input_root / ROLE_FILENAMES["field"]
    field_path.write_text(content, encoding="utf-8")
    declared_sha256 = hashlib.sha256(field_path.read_bytes()).hexdigest()

    for source in manifest["sources"]:
        if source["role"] == "field":
            source["row_count"] = declared_row_count
            source["sha256"] = declared_sha256

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert result.resolved_sources["field"].row_count_outcome.state == smr.INTEGRITY_VERIFIED
    assert result.resolved_sources["field"].sha256_outcome.state == smr.INTEGRITY_VERIFIED


def test_row_count_unreadable_source_is_unable_to_validate(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    for source in manifest["sources"]:
        if source["role"] == "benchmark.decomposition":
            source["path"] = "does_not_exist.csv"
            source["row_count"] = 3

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(
        f.code == "ROW_COUNT_UNABLE_TO_VALIDATE" and f.role == "benchmark.decomposition"
        for f in result.blockers
    )


def test_row_count_undecodable_source_is_unable_to_validate(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)
    bad_bytes_path = context.input_root / "decomp.csv"
    bad_bytes_path.write_bytes(b"player_name,rounds_played\n\xff\xfe\x00invalid-utf8\n")
    for source in manifest["sources"]:
        if source["role"] == "benchmark.decomposition":
            source["row_count"] = 1
            source["sha256"] = None
            source["encoding"] = "utf-8"

    result = smr.resolve_source_manifest(manifest, context=context)

    assert result.is_release_blocked
    assert any(
        f.code == "ROW_COUNT_UNABLE_TO_VALIDATE" and f.role == "benchmark.decomposition"
        for f in result.blockers
    )


# ── 13. Explicit legacy literal filename accepted ────────────────────────────

def test_explicit_legacy_literal_filename_accepted(tmp_path):
    context = build_context(tmp_path, event_slug="2026_example_open", venue_slug="example_venue")
    legacy_filename = "pga_sg_query_3Mopen_similar_l6.csv"
    manifest = build_complete_manifest(
        context, overrides_by_role={"venue_fit.similar_sg.6m": {"path": legacy_filename}},
    )
    # _base_entry wrote to the role's default filename; also write the
    # legacy-named physical file with matching integrity values.
    legacy_path = context.input_root / legacy_filename
    legacy_path.write_text(FIELD_CSV, encoding="utf-8")
    for source in manifest["sources"]:
        if source["role"] == "venue_fit.similar_sg.6m":
            source["sha256"] = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
            source["row_count"] = _row_count_of(FIELD_CSV)

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert result.resolved_sources["venue_fit.similar_sg.6m"].resolved_path == legacy_path


# ── 14. No inferred or implicit 3M-shaped fallback ───────────────────────────

def test_no_implicit_event_slug_shaped_fallback(tmp_path):
    context = build_context(tmp_path, event_slug="2026_example_open", venue_slug="example_venue")
    manifest = build_complete_manifest(context)

    # A file matching the historical naming *pattern* for this event exists
    # on disk, but no manifest entry declares it -- the resolver must never
    # discover or substitute it for a role whose declared path is wrong.
    pattern_shaped_path = context.input_root / "pga_sg_query_2026_example_open_similar_l6.csv"
    pattern_shaped_path.write_text(FIELD_CSV, encoding="utf-8")

    for source in manifest["sources"]:
        if source["role"] == "venue_fit.similar_sg.6m":
            source["path"] = "this_file_does_not_exist.csv"
            source["sha256"] = None
            source["row_count"] = None

    result = smr.resolve_source_manifest(manifest, context=context)

    assert "venue_fit.similar_sg.6m" not in result.resolved_sources
    assert any(
        f.role == "venue_fit.similar_sg.6m" and f.code == "SOURCE_MISSING"
        for f in result.warnings
    )


# ── 15. identity_key non-interference with identity_resolver.py ────────────

def test_module_does_not_import_forbidden_producer_modules():
    """AST-based, not substring-based: the module's own docstring names
    these modules by design (to document that it must not import them), so
    a plain substring search over the source text would false-positive on
    its own documentation. Only actual import statements are checked.
    """
    import ast

    module_path = Path(smr.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    forbidden = {"identity_resolver", "enrich_cards", "build_event_package", "venuedna_scoring", "event_context"}

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert not (imported & forbidden), f"forbidden import(s) found: {imported & forbidden}"


@pytest.mark.parametrize("identity_key", list(smr.VALID_IDENTITY_KEYS) + [None])
def test_identity_key_metadata_does_not_change_resolution_outcome(tmp_path, identity_key):
    context = build_context(tmp_path)
    overrides = {"field": {"identity_key": identity_key}}
    manifest = build_complete_manifest(context, overrides_by_role=overrides)

    result = smr.resolve_source_manifest(manifest, context=context)

    assert not result.is_release_blocked, [f.message for f in result.blockers]
    assert result.resolved_sources["field"].identity_key == identity_key
    # Every other role's resolution is identical regardless of this field.
    for role in smr.REQUIRED_ROLES:
        if role == "field":
            continue
        assert role in result.resolved_sources


def test_identity_resolver_precedence_is_unaffected_and_still_importable():
    """Proves engine/identity_resolver.py's own dg_id-first precedence still
    works exactly as before, without this module modifying that file or
    being invoked by it in any way.
    """
    sys.path.insert(0, str(_ENGINE_DIR))
    import identity_resolver  # noqa: E402  (imported here, not by the new module)

    field_rows = [
        {"player_name": "Doe, John", "dg_id": "1001"},
        {"player_name": "Smith, Jane", "dg_id": "1002"},
    ]
    field_index = identity_resolver.build_field_index(field_rows)
    assert field_index.is_valid

    source_rows = [
        {"player_name": "Doe, John", "dg_id": "1001"},
        {"player_name": "Smith, Jane", "dg_id": "1002"},
    ]
    result = identity_resolver.resolve_source_family(
        "example", field_index, source_rows, dg_id_field="dg_id",
    )
    methods = {m.field_dg_id: m.method for m in result.matches}
    assert methods == {"1001": identity_resolver.METHOD_EXACT_DG_ID, "1002": identity_resolver.METHOD_EXACT_DG_ID}


# ── 16. No repository writes outside tmp_path ────────────────────────────────

def test_resolver_makes_no_repository_writes_outside_tmp_path(tmp_path):
    context = build_context(tmp_path)
    manifest = build_complete_manifest(context)

    before = snapshot(tmp_path)
    result = smr.resolve_source_manifest(manifest, context=context)
    _ = result.is_release_blocked  # exercise the report without mutating anything
    after = snapshot(tmp_path)

    assert after == before
    assert not (context.event_root / "input" / "source_manifest.json").exists()
    assert not (context.event_root / "output").exists()
    assert not (context.event_root / "deploy").exists()


# ── 17. Authorized Wyndham retrospective-development fixture ────────────────

def _fixture_snapshot() -> dict[str, str]:
    return {
        path.relative_to(WYNDHAM_FIXTURE_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in WYNDHAM_FIXTURE_ROOT.rglob("*")
        if path.is_file()
    }


def _fixture_manifest() -> dict:
    return json.loads((WYNDHAM_INPUT_ROOT / "source_manifest.json").read_text(encoding="utf-8"))


def _fixture_source_path(manifest: dict, role: str) -> Path:
    entry = next(source for source in manifest["sources"] if source["role"] == role)
    return WYNDHAM_INPUT_ROOT / entry["path"]


def _fixture_player_row(manifest: dict, role: str, player_name: str) -> dict | None:
    with _fixture_source_path(manifest, role).open(newline="", encoding="utf-8") as handle:
        return next((row for row in csv.DictReader(handle) if row["player_name"] == player_name), None)


def test_wyndham_retrospective_fixture_resolves_all_integrity_asserted_roles_read_only():
    manifest = _fixture_manifest()
    context = smr.SourceManifestContext(
        event_slug="2026_wyndham_championship",
        venue_slug="sedgefield_country_club",
        event_root=WYNDHAM_FIXTURE_ROOT,
        repo_root=REPO_ROOT,
    )
    before = _fixture_snapshot()
    result = smr.resolve_source_manifest(manifest, context=context)
    after = _fixture_snapshot()

    assert after == before
    assert manifest["schema_version"] == "1.0"
    assert set(result.resolved_sources) == set(smr.REQUIRED_ROLES)
    assert not result.is_release_blocked, [finding.message for finding in result.blockers]
    for role, source in result.resolved_sources.items():
        assert source.resolved_path.is_relative_to(WYNDHAM_INPUT_ROOT), role
        assert source.sha256_outcome.state == smr.INTEGRITY_VERIFIED, role
        assert source.row_count_outcome.state == smr.INTEGRITY_VERIFIED, role

    similar_metadata = [
        next(source for source in manifest["sources"] if source["role"] == role)["metadata"]
        for role in smr.SIMILAR_SG_ROLES
    ]
    assert {metadata["similar_course_set_id"] for metadata in similar_metadata} == {
        "sedgefield_country_club_similarity_top21"
    }
    assert {metadata["set_version"] for metadata in similar_metadata} == {"1.0"}
    assert len({metadata["set_provenance"] for metadata in similar_metadata}) == 1
    assert [metadata["horizon_months"] for metadata in similar_metadata] == [6, 12, 24]
    venue_history = next(source for source in manifest["sources"] if source["role"] == "venue_history")
    assert venue_history["metadata"]["venue_slug"] == "sedgefield_country_club"


def test_wyndham_fixture_preserves_field_and_source_only_identity_coverage():
    manifest = _fixture_manifest()
    field_names = {
        row["player_name"]
        for row in csv.DictReader((WYNDHAM_INPUT_ROOT / "pga_field_teetimes.csv").open(encoding="utf-8"))
    }
    all_course_roles = (
        "neutral_skill.sg_total.6m", "neutral_skill.sg_total.12m", "neutral_skill.sg_total.24m",
    )
    similar_roles = (
        "venue_fit.similar_sg.6m", "venue_fit.similar_sg.12m", "venue_fit.similar_sg.24m",
    )

    assert "Skinns, David" in field_names
    assert all(_fixture_player_row(manifest, role, "Skinns, David") is not None for role in all_course_roles)
    assert all(_fixture_player_row(manifest, role, "Skinns, David") is None for role in similar_roles)

    assert "Moore, Taylor" in field_names
    assert all(_fixture_player_row(manifest, role, "Moore, Taylor") is None for role in all_course_roles)
    assert all(_fixture_player_row(manifest, role, "Moore, Taylor") is not None for role in similar_roles)

    assert "Berger, Daniel" not in field_names
    assert all(_fixture_player_row(manifest, role, "Berger, Daniel") is None for role in all_course_roles)
    assert all(_fixture_player_row(manifest, role, "Berger, Daniel") is not None for role in similar_roles)

    assert "Merritt, Troy" not in field_names
    assert any(_fixture_player_row(manifest, role, "Merritt, Troy") is not None for role in all_course_roles)


def test_wyndham_fixture_missing_source_statuses_are_unscored_in_memory_only():
    """Exercise the pure player-preparation function only: no rank, tier,
    probability, output, deploy payload, or artifact is generated or written.
    """
    manifest = _fixture_manifest()
    before = _fixture_snapshot()

    def player_inputs(player_name: str):
        neutral = {}
        similar = {}
        for horizon in ("6m", "12m", "24m"):
            all_row = _fixture_player_row(manifest, f"neutral_skill.sg_total.{horizon}", player_name)
            neutral[horizon] = float(all_row["total_mean"]) if all_row is not None else None
            similar_row = _fixture_player_row(manifest, f"venue_fit.similar_sg.{horizon}", player_name)
            similar[horizon] = (
                None if similar_row is None else SimilarCourseRow(
                    rounds_played=int(similar_row["rounds_played"]),
                    total_mean=float(similar_row["total_mean"]),
                )
            )
        return neutral, similar

    skinns = compute_player_projection(*player_inputs("Skinns, David"))
    moore = compute_player_projection(*player_inputs("Moore, Taylor"))
    after = _fixture_snapshot()

    assert after == before
    assert skinns.status == "UNSCORED"
    assert skinns.neutral_skill_raw is not None
    assert skinns.venue_fit_delta_raw is None
    assert skinns.pre_penalty_raw is None
    assert moore.status == "UNSCORED"
    assert moore.neutral_skill_raw is None
    assert moore.venue_fit_delta_raw is None
    assert moore.pre_penalty_raw is None
    assert not list((WYNDHAM_FIXTURE_ROOT / "output").iterdir())
    assert not list((WYNDHAM_FIXTURE_ROOT / "deploy" / "data").iterdir())
