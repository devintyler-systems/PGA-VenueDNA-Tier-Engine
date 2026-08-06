"""engine/event_context.py
Manifest-driven event-context loading and validation for the root pre-event
producer (engine/enrich_cards.py).

Fail-closed: every function here is pure with respect to program state (the
only I/O is reading the manifest JSON text) and raises ``EventContextError``
before any event-bound path is ever used for a read or write. Nothing here
creates a directory, writes a file, or touches ``events/``, ``library/``, or
``deploy/`` content.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REQUIRED_MANIFEST_FIELDS = (
    "status",
    "event_slug",
    "event_name",
    "venue_slug",
    "venue_name",
    "year",
    "event_root",
    "venue_profile",
    "deploy_root",
    "audit_root",
)

SUPPORTED_SCHEMA_VERSION = "1.0"
NO_ACTIVE_EVENT_STATUS = "NO_ACTIVE_EVENT"
PRE_EVENT_STATUS = "PRE_EVENT"

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_ARCHIVED_SEGMENTS_CASEFOLDED = frozenset({"2026_finished_events", "finished_events"})


class EventContextError(ValueError):
    """Raised when the active-event manifest cannot support a safe production build."""


@dataclass(frozen=True)
class EventContext:
    event_slug: str
    event_name: str
    venue_slug: str
    venue_name: str
    year: int
    event_root: Path
    venue_profile: Path
    deploy_root: Path
    audit_root: Path


def load_manifest(manifest_path: Path) -> dict:
    """Read and parse the active-event manifest. Raises ``EventContextError``
    on a missing file or invalid JSON -- never a bare exception."""
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise EventContextError(
            f"Active-event manifest not found: {manifest_path}"
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EventContextError(
            f"Active-event manifest is not valid JSON: {manifest_path} ({exc})"
        ) from exc


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventContextError(
            f"{field_name} must be a non-empty string, got {value!r}"
        )
    return value


def _require_int_year(value: object, field_name: str = "year") -> int:
    # bool is a subclass of int in Python -- must be excluded explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventContextError(
            f"{field_name} must be an integer, not {type(value).__name__}: {value!r}"
        )
    return value


def _validate_slug(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _SLUG_RE.match(value):
        raise EventContextError(
            f"{field_name} must be lowercase snake_case: {value!r}"
        )
    return value


def _validate_repo_relative_path(raw_value: object, field_name: str) -> PurePosixPath:
    """Validate ``raw_value`` is a safe, repository-relative, forward-slash
    path. Rejects absolute paths, drive prefixes, backslashes, and '..'
    traversal by string inspection alone -- no filesystem access."""
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise EventContextError(f"{field_name} must be a non-empty string")
    if "\\" in raw_value:
        raise EventContextError(
            f"{field_name} must use forward-slash repository-relative paths: {raw_value!r}"
        )
    if raw_value.startswith("/") or _DRIVE_RE.match(raw_value):
        raise EventContextError(
            f"{field_name} must be repository-relative, not absolute: {raw_value!r}"
        )
    pure = PurePosixPath(raw_value)
    if any(part == ".." for part in pure.parts):
        raise EventContextError(
            f"{field_name} must not contain '..' traversal: {raw_value!r}"
        )
    return pure


def _archived_segment_present(parts: tuple[str, ...]) -> bool:
    """Segment-based, case-insensitive archived/finished-event detection.
    Never a substring match -- an unrelated filename that merely contains
    one of these words as part of a longer segment name is not rejected."""
    return any(part.casefold() in _ARCHIVED_SEGMENTS_CASEFOLDED for part in parts)


def _reject_archived_segment(parts: tuple[str, ...], field_name: str, *, stage: str) -> None:
    if _archived_segment_present(parts):
        raise EventContextError(
            f"{field_name} {stage} an archived/finished-event location: {'/'.join(parts)!r}"
        )


def _resolve_within_repo(repo_root: Path, pure: PurePosixPath, field_name: str) -> Path:
    """Join ``pure`` onto ``repo_root``, confirm the resolved target stays
    inside the repository via resolve()+relative_to() (not string prefixes,
    so a symlink escape is also caught), and reject the *resolved*
    repository-relative path if it lands under an archived/finished-event
    segment -- even when the originally-declared path did not textually
    mention one (for example via a symlink or filesystem junction)."""
    resolved = repo_root.joinpath(*pure.parts).resolve()
    repo_resolved = repo_root.resolve()
    try:
        resolved_relative = resolved.relative_to(repo_resolved)
    except ValueError as exc:
        raise EventContextError(
            f"{field_name} escapes the repository root: {'/'.join(pure.parts)!r}"
        ) from exc
    _reject_archived_segment(resolved_relative.parts, field_name, stage="resolves to")
    return resolved


def load_pre_event_context(manifest_path: Path, *, repo_root: Path) -> EventContext:
    """Load, validate, and return the active PRE_EVENT context.

    Raises ``EventContextError`` -- before any event-bound path is used for
    I/O -- when the manifest is missing, malformed, does not decode to a
    JSON object, declares an unsupported schema version, is NO_ACTIVE_EVENT,
    is any status other than PRE_EVENT, is missing a required field, has a
    wrongly-typed field, or declares an unsafe or internally inconsistent
    path (before or after filesystem resolution).
    """
    manifest = load_manifest(manifest_path)

    if not isinstance(manifest, dict):
        raise EventContextError(
            f"Active-event manifest must decode to a JSON object, got "
            f"{type(manifest).__name__}: {manifest_path}"
        )

    schema_version = manifest.get("schema_version")
    _require_non_empty_string(schema_version, "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise EventContextError(
            f"Unsupported active-event manifest schema_version: {schema_version!r} "
            f"(expected {SUPPORTED_SCHEMA_VERSION!r})"
        )

    status = manifest.get("status")
    _require_non_empty_string(status, "status")
    if status == NO_ACTIVE_EVENT_STATUS:
        raise EventContextError(
            "No active event: config/active_event.json status is NO_ACTIVE_EVENT. "
            "Update the manifest to PRE_EVENT with full event/venue bindings "
            "before running the pre-event producer."
        )
    if status != PRE_EVENT_STATUS:
        raise EventContextError(
            f"Unsupported active-event status for the pre-event producer: {status!r} "
            f"(expected {PRE_EVENT_STATUS!r})"
        )

    missing = [key for key in REQUIRED_MANIFEST_FIELDS if not manifest.get(key)]
    if missing:
        raise EventContextError(
            f"Active-event manifest missing required field(s): {', '.join(missing)}"
        )

    event_name = _require_non_empty_string(manifest["event_name"], "event_name")
    venue_name = _require_non_empty_string(manifest["venue_name"], "venue_name")
    year = _require_int_year(manifest["year"])

    event_slug = _validate_slug(manifest["event_slug"], "event_slug")
    venue_slug = _validate_slug(manifest["venue_slug"], "venue_slug")

    field_values = {
        "event_root": manifest["event_root"],
        "venue_profile": manifest["venue_profile"],
        "deploy_root": manifest["deploy_root"],
        "audit_root": manifest["audit_root"],
    }
    pure_paths: dict[str, PurePosixPath] = {}
    for field_name, raw_value in field_values.items():
        pure = _validate_repo_relative_path(raw_value, field_name)
        _reject_archived_segment(pure.parts, field_name, stage="declares")
        pure_paths[field_name] = pure

    event_root = _resolve_within_repo(repo_root, pure_paths["event_root"], "event_root")
    venue_profile = _resolve_within_repo(repo_root, pure_paths["venue_profile"], "venue_profile")
    deploy_root = _resolve_within_repo(repo_root, pure_paths["deploy_root"], "deploy_root")
    audit_root = _resolve_within_repo(repo_root, pure_paths["audit_root"], "audit_root")

    expected_event_root = (repo_root / "events" / event_slug).resolve()
    if event_root != expected_event_root:
        raise EventContextError(
            f"event_root {field_values['event_root']!r} must equal events/{event_slug}"
        )

    expected_deploy_root = (expected_event_root / "deploy").resolve()
    if deploy_root != expected_deploy_root:
        raise EventContextError(
            f"deploy_root {field_values['deploy_root']!r} must equal events/{event_slug}/deploy"
        )

    expected_audit_root = (expected_event_root / "audit").resolve()
    if audit_root != expected_audit_root:
        raise EventContextError(
            f"audit_root {field_values['audit_root']!r} must equal events/{event_slug}/audit"
        )

    expected_venue_profile = (
        repo_root / "library" / "venues" / venue_slug / f"{venue_slug}_venue_profile.md"
    ).resolve()
    if venue_profile != expected_venue_profile:
        raise EventContextError(
            f"venue_profile {field_values['venue_profile']!r} must equal "
            f"library/venues/{venue_slug}/{venue_slug}_venue_profile.md"
        )

    return EventContext(
        event_slug=event_slug,
        event_name=event_name,
        venue_slug=venue_slug,
        venue_name=venue_name,
        year=year,
        event_root=event_root,
        venue_profile=venue_profile,
        deploy_root=deploy_root,
        audit_root=audit_root,
    )


def require_supported_context(
    context: EventContext, *, supported_event_slug: str, supported_venue_slug: str
) -> None:
    """Fail-closed capability gate for a producer whose remaining input
    files and narrative logic are still hardcoded to one specific event and
    venue. Call this after ``load_pre_event_context`` succeeds and before
    any event-bound input read, directory creation, or write.

    This gate does not initialize an event, does not touch the manifest,
    does not weaken any canonical path check, and does not claim the
    producer is venue-generic -- it only prevents the producer's remaining
    venue-specific behavior from silently running under a mismatched event
    or venue label.
    """
    if context.event_slug != supported_event_slug or context.venue_slug != supported_venue_slug:
        raise EventContextError(
            "Unsupported event/venue context for this producer: "
            f"got event_slug={context.event_slug!r}, venue_slug={context.venue_slug!r}; "
            f"this producer's remaining input files and narrative logic are still "
            f"hardcoded to event_slug={supported_event_slug!r}, "
            f"venue_slug={supported_venue_slug!r}. Venue generalization requires a "
            f"separately authorized migration before this producer can run for "
            f"another event or venue."
        )
