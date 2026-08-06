"""Tests for engine/event_context.py -- manifest-driven event-context
loading and validation for the root pre-event producer.

Every test builds its own synthetic config/active_event.json and repo_root
under tmp_path. None touch the real config/active_event.json or any real
events/ or library/ directory.
"""
import json
import sys
from pathlib import Path, PurePosixPath

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from event_context import (  # noqa: E402
    EventContext,
    EventContextError,
    load_pre_event_context,
    require_supported_context,
    _resolve_within_repo,
    _archived_segment_present,
)


def _write_manifest(repo_root: Path, manifest: dict) -> Path:
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "active_event.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _valid_manifest(event_slug="wyndham_test_event", venue_slug="test_venue", **overrides):
    manifest = {
        "schema_version": "1.0",
        "status": "PRE_EVENT",
        "event_slug": event_slug,
        "event_name": "Test Event",
        "venue_slug": venue_slug,
        "venue_name": "Test Venue",
        "year": 2026,
        "event_root": f"events/{event_slug}",
        "venue_profile": f"library/venues/{venue_slug}/{venue_slug}_venue_profile.md",
        "deploy_root": f"events/{event_slug}/deploy",
        "audit_root": f"events/{event_slug}/audit",
    }
    manifest.update(overrides)
    return manifest


def test_valid_manifest_derives_context(tmp_path):
    manifest = _valid_manifest()
    manifest_path = _write_manifest(tmp_path, manifest)

    context = load_pre_event_context(manifest_path, repo_root=tmp_path)

    assert context.event_slug == "wyndham_test_event"
    assert context.event_name == "Test Event"
    assert context.venue_slug == "test_venue"
    assert context.venue_name == "Test Venue"
    assert context.year == 2026
    assert context.event_root == (tmp_path / "events" / "wyndham_test_event").resolve()
    assert context.deploy_root == (tmp_path / "events" / "wyndham_test_event" / "deploy").resolve()
    assert context.audit_root == (tmp_path / "events" / "wyndham_test_event" / "audit").resolve()
    assert context.venue_profile == (
        tmp_path / "library" / "venues" / "test_venue" / "test_venue_venue_profile.md"
    ).resolve()


def test_missing_manifest_file_fails_closed(tmp_path):
    with pytest.raises(EventContextError, match="not found"):
        load_pre_event_context(tmp_path / "config" / "active_event.json", repo_root=tmp_path)


def test_malformed_json_fails_closed(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "active_event.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(EventContextError, match="not valid JSON"):
        load_pre_event_context(config_dir / "active_event.json", repo_root=tmp_path)


def test_unsupported_schema_version_fails_closed(tmp_path):
    manifest = _valid_manifest(schema_version="2.0")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="schema_version"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_no_active_event_fails_before_field_checks(tmp_path):
    """NO_ACTIVE_EVENT must fail even when every other field is entirely
    absent -- the status check happens first, before any I/O-relevant
    field is inspected."""
    manifest_path = _write_manifest(
        tmp_path, {"schema_version": "1.0", "status": "NO_ACTIVE_EVENT"}
    )
    with pytest.raises(EventContextError, match="NO_ACTIVE_EVENT"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


@pytest.mark.parametrize("status", ["ROUND_1", "FINAL_AUDIT", "ARCHIVED", "BOGUS_STATUS", ""])
def test_non_pre_event_status_fails_closed(tmp_path, status):
    manifest = _valid_manifest(status=status)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="status"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


@pytest.mark.parametrize("missing_field", [
    "event_slug", "event_name", "venue_slug", "venue_name", "year",
    "event_root", "venue_profile", "deploy_root", "audit_root",
])
def test_missing_required_field_fails_closed(tmp_path, missing_field):
    manifest = _valid_manifest()
    manifest[missing_field] = None
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match=missing_field):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_absolute_event_root_rejected(tmp_path):
    manifest = _valid_manifest(event_root="/events/wyndham_test_event")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="absolute"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_windows_drive_absolute_event_root_rejected(tmp_path):
    manifest = _valid_manifest(event_root="C:/events/wyndham_test_event")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="absolute"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_traversal_in_event_root_rejected(tmp_path):
    manifest = _valid_manifest(event_root="events/../../outside_repo")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="traversal"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_archived_event_root_rejected(tmp_path):
    manifest = _valid_manifest(
        event_slug="2026_3m_open",
        event_root="events/2026_Finished_Events/2026_3m_open",
        deploy_root="events/2026_Finished_Events/2026_3m_open/deploy",
        audit_root="events/2026_Finished_Events/2026_3m_open/audit",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="archived|Finished_Events"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_finished_events_segment_rejected_even_with_matching_slug(tmp_path):
    """An event_root that embeds a Finished_Events segment must be rejected
    even before the events/{slug} equality check runs."""
    manifest = _valid_manifest(
        event_slug="2026_wyndham_championship",
        event_root="events/2026_Finished_Events/2026_wyndham_championship",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="archived|Finished_Events"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_event_root_slug_mismatch_rejected(tmp_path):
    manifest = _valid_manifest(event_slug="wyndham_test_event", event_root="events/some_other_event")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="event_root"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_deploy_root_mismatch_rejected(tmp_path):
    manifest = _valid_manifest(deploy_root="events/some_other_event/deploy")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="deploy_root"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_audit_root_mismatch_rejected(tmp_path):
    manifest = _valid_manifest(audit_root="events/some_other_event/audit")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="audit_root"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_venue_profile_slug_mismatch_rejected(tmp_path):
    manifest = _valid_manifest(
        venue_slug="test_venue",
        venue_profile="library/venues/some_other_venue/some_other_venue_venue_profile.md",
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="venue_profile"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_invalid_event_slug_format_rejected(tmp_path):
    manifest = _valid_manifest(event_slug="Not-A-Valid-Slug!", event_root="events/Not-A-Valid-Slug!")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="event_slug"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_backslash_path_rejected(tmp_path):
    manifest = _valid_manifest(event_root="events\\wyndham_test_event")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="forward-slash"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


# ── Manifest type validation (root type and field types) ───────────────────

@pytest.mark.parametrize("root_value", [
    ["array", "root"], "a plain string root", None, True, 42, 3.14,
], ids=["array", "string", "null", "boolean", "int", "float"])
def test_non_object_json_root_rejected(tmp_path, root_value):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "active_event.json").write_text(json.dumps(root_value), encoding="utf-8")
    with pytest.raises(EventContextError, match="JSON object"):
        load_pre_event_context(config_dir / "active_event.json", repo_root=tmp_path)


def test_boolean_year_rejected(tmp_path):
    manifest = _valid_manifest(year=True)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="year"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_string_year_rejected(tmp_path):
    manifest = _valid_manifest(year="2026")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="year"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_float_year_rejected(tmp_path):
    manifest = _valid_manifest(year=2026.0)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="year"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_non_string_event_name_rejected(tmp_path):
    manifest = _valid_manifest(event_name=12345)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="event_name"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_non_string_venue_name_rejected(tmp_path):
    manifest = _valid_manifest(venue_name=["not", "a", "string"])
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="venue_name"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


@pytest.mark.parametrize("field_name", ["event_root", "venue_profile", "deploy_root", "audit_root"])
def test_non_string_path_field_rejected(tmp_path, field_name):
    manifest = _valid_manifest(**{field_name: 12345})
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match=field_name):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_non_string_schema_version_rejected(tmp_path):
    manifest = _valid_manifest(schema_version=1.0)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="schema_version"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_non_string_status_rejected(tmp_path):
    manifest = _valid_manifest(status=123)
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="status"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


def test_malformed_json_still_rejected(tmp_path):
    """Regression guard: the new root-type check must not change how a
    non-JSON payload is reported."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "active_event.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(EventContextError, match="not valid JSON"):
        load_pre_event_context(config_dir / "active_event.json", repo_root=tmp_path)


def test_unsupported_schema_version_still_rejected(tmp_path):
    """Regression guard: schema_version type-checking must not weaken the
    existing unsupported-version rejection."""
    manifest = _valid_manifest(schema_version="9.9")
    manifest_path = _write_manifest(tmp_path, manifest)
    with pytest.raises(EventContextError, match="schema_version"):
        load_pre_event_context(manifest_path, repo_root=tmp_path)


# ── Resolved-target archive protection (Finding E) ──────────────────────────

def test_archived_segment_present_is_case_insensitive_and_segment_based():
    """Pure unit coverage of the segment-based, case-insensitive archived
    check -- proves it never does a raw substring match (an unrelated
    filename that merely contains the word is not rejected)."""
    assert _archived_segment_present(("events", "2026_Finished_Events", "2026_3m_open"))
    assert _archived_segment_present(("events", "2026_FINISHED_EVENTS", "2026_3m_open"))
    assert _archived_segment_present(("events", "finished_events", "x"))
    assert not _archived_segment_present(("events", "2026_3m_open"))
    assert not _archived_segment_present(("events", "not_2026_finished_events_at_all"))


def test_resolved_target_under_archived_segment_rejected_via_monkeypatched_resolution(
    tmp_path, monkeypatch
):
    """A declared path that looks safe (no archived segment in the declared
    string) but whose resolution -- for example via a symlink or a Windows
    junction -- lands under an archived/finished-event segment must still
    be rejected. This narrowly monkeypatches Path.resolve() so the
    regression is deterministic and does not depend on Windows
    developer-mode symlink privileges, per the pure resolved-path check
    exercised directly above."""
    real_resolve = Path.resolve
    repo_root = tmp_path
    aliased_path = repo_root / "events" / "looks_safe_alias"
    resolved_repo_root = real_resolve(repo_root)
    archived_target = resolved_repo_root / "events" / "2026_Finished_Events" / "2026_3m_open"

    def fake_resolve(self, *args, **kwargs):
        if self == aliased_path:
            return archived_target
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(EventContextError, match="resolves to.*archived|Finished_Events"):
        _resolve_within_repo(repo_root, PurePosixPath("events/looks_safe_alias"), "event_root")


def test_resolved_target_outside_repo_still_rejected_regardless_of_archive_check(
    tmp_path, monkeypatch
):
    """Regression guard: adding the post-resolution archived-segment check
    must not weaken the pre-existing repository-containment check."""
    real_resolve = Path.resolve
    repo_root = tmp_path
    aliased_path = repo_root / "events" / "looks_safe_alias"
    outside_target = real_resolve(tmp_path.parent) / "definitely_outside_the_repo"

    def fake_resolve(self, *args, **kwargs):
        if self == aliased_path:
            return outside_target
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(EventContextError, match="escapes the repository root"):
        _resolve_within_repo(repo_root, PurePosixPath("events/looks_safe_alias"), "event_root")


# ── Supported-context capability gate (Finding D) ───────────────────────────

def _make_context(**overrides) -> EventContext:
    fields = dict(
        event_slug="2026_3m_open", event_name="Some Event",
        venue_slug="tpc_twin_cities", venue_name="Some Venue",
        year=2026,
        event_root=Path("/repo/events/2026_3m_open"),
        venue_profile=Path("/repo/library/venues/tpc_twin_cities/tpc_twin_cities_venue_profile.md"),
        deploy_root=Path("/repo/events/2026_3m_open/deploy"),
        audit_root=Path("/repo/events/2026_3m_open/audit"),
    )
    fields.update(overrides)
    return EventContext(**fields)


def test_require_supported_context_accepts_exact_match():
    context = _make_context()
    require_supported_context(
        context, supported_event_slug="2026_3m_open", supported_venue_slug="tpc_twin_cities"
    )  # must not raise


def test_require_supported_context_rejects_wrong_event():
    context = _make_context(event_slug="2026_wyndham_championship")
    with pytest.raises(EventContextError, match="Unsupported event/venue"):
        require_supported_context(
            context, supported_event_slug="2026_3m_open", supported_venue_slug="tpc_twin_cities"
        )


def test_require_supported_context_rejects_wrong_venue():
    context = _make_context(venue_slug="sedgefield_country_club")
    with pytest.raises(EventContextError, match="Unsupported event/venue"):
        require_supported_context(
            context, supported_event_slug="2026_3m_open", supported_venue_slug="tpc_twin_cities"
        )


def test_require_supported_context_rejects_both_wrong():
    context = _make_context(
        event_slug="2026_wyndham_championship", venue_slug="sedgefield_country_club"
    )
    with pytest.raises(EventContextError, match="Unsupported event/venue"):
        require_supported_context(
            context, supported_event_slug="2026_3m_open", supported_venue_slug="tpc_twin_cities"
        )
