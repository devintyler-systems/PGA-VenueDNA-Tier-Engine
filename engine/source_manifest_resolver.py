"""engine/source_manifest_resolver.py
Event-neutral resolver/validator for the ``source_manifest`` schema v1.0
contract (``standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`` §9, §9.4, §9.4A,
§9.5, §9.5A, §9.6).

Standalone by construction: this module never reads
``config/active_event.json`` and never imports or calls
``engine/enrich_cards.py``, ``engine/build_event_package.py``,
``engine/venuedna_scoring.py``, or ``engine/identity_resolver.py``. Every
input it needs -- a parsed manifest object and the caller's already-derived
event/venue slugs and event root -- is supplied explicitly by the caller.

It is read-only with respect to the manifest and repository: it may open a
declared physical source file to compute a SHA-256 digest or count data
rows for an already-declared, non-null integrity assertion, and it may
``resolve()`` a candidate path for containment checking, but it never
writes, creates, renames, or deletes any file, directory, event artifact,
deploy payload, cache, database row, manifest instance, or source input.

It performs no scoring, confidence collapsing, zero-fill, NeutralSkill or
VenueFit renormalization, penalty, gate, rank, tier, or probability
computation. It reports source availability and integrity only; a future,
separately authorized caller is responsible for feeding that report into
the scoring pipeline described in ``standards/02`` §7.5.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping, Optional, Sequence

# ── Schema constants (standards/04 §9.3, §9.5) ──────────────────────────────

SCHEMA_VERSION = "1.0"

REQUIRED_ROLES: tuple[str, ...] = (
    "field",
    "neutral_skill.sg_total.6m",
    "neutral_skill.sg_total.12m",
    "neutral_skill.sg_total.24m",
    "venue_fit.similar_sg.6m",
    "venue_fit.similar_sg.12m",
    "venue_fit.similar_sg.24m",
    "traits.approach.sg_per_shot.12m",
    "traits.approach.proximity.12m",
    "performance.sg_categories.season",
    "benchmark.decomposition",
    "venue_history",
    "recent_form.trending",
)

# §9.5A: exactly one required/missing_behavior combination per role, fixed.
ROLE_REQUIRED: Mapping[str, bool] = MappingProxyType({
    "field": True,
    "neutral_skill.sg_total.6m": True,
    "neutral_skill.sg_total.12m": True,
    "neutral_skill.sg_total.24m": True,
    "venue_fit.similar_sg.6m": True,
    "venue_fit.similar_sg.12m": True,
    "venue_fit.similar_sg.24m": True,
    "traits.approach.sg_per_shot.12m": False,
    "traits.approach.proximity.12m": False,
    "performance.sg_categories.season": False,
    "benchmark.decomposition": False,
    "venue_history": False,
    "recent_form.trending": False,
})

ROLE_MISSING_BEHAVIOR: Mapping[str, str] = MappingProxyType({
    "field": "block_release",
    "neutral_skill.sg_total.6m": "neutral_skill_horizon_incomplete",
    "neutral_skill.sg_total.12m": "neutral_skill_horizon_incomplete",
    "neutral_skill.sg_total.24m": "neutral_skill_horizon_incomplete",
    "venue_fit.similar_sg.6m": "venue_fit_horizon_incomplete",
    "venue_fit.similar_sg.12m": "venue_fit_horizon_incomplete",
    "venue_fit.similar_sg.24m": "venue_fit_horizon_incomplete",
    "traits.approach.sg_per_shot.12m": "widen_confidence",
    "traits.approach.proximity.12m": "widen_confidence",
    "performance.sg_categories.season": "widen_confidence",
    "benchmark.decomposition": "widen_confidence",
    "venue_history": "venue_history_missing",
    "recent_form.trending": "widen_confidence",
})

SIMILAR_SG_ROLES: tuple[str, ...] = (
    "venue_fit.similar_sg.6m", "venue_fit.similar_sg.12m", "venue_fit.similar_sg.24m",
)
SIMILAR_SG_HORIZON_MONTHS: Mapping[str, int] = MappingProxyType({
    "venue_fit.similar_sg.6m": 6,
    "venue_fit.similar_sg.12m": 12,
    "venue_fit.similar_sg.24m": 24,
})

# skip_layer/warn_only are reserved for a documented additional role beyond
# the thirteen; neither is permitted for any of the thirteen (§9.4).
ADDITIONAL_ONLY_MISSING_BEHAVIORS: tuple[str, ...] = ("skip_layer", "warn_only")
ALL_MISSING_BEHAVIORS: tuple[str, ...] = (
    "block_release",
    "neutral_skill_horizon_incomplete",
    "venue_fit_horizon_incomplete",
    "venue_history_missing",
    "widen_confidence",
    *ADDITIONAL_ONLY_MISSING_BEHAVIORS,
)

VALID_IDENTITY_KEYS: tuple[str, ...] = ("dg_id", "player_name", "dg_id+player_name")
VALID_ENCODINGS: tuple[str, ...] = ("utf-8", "utf-8-sig")

# ── Integrity reporting states (standards/04 §9.4A) ─────────────────────────

INTEGRITY_VERIFIED = "verified"
INTEGRITY_MISMATCH = "mismatch"
INTEGRITY_NOT_ASSERTED = "not_asserted"
INTEGRITY_UNABLE_TO_VALIDATE = "unable_to_validate"

# ── Finding severities ───────────────────────────────────────────────────────

SEVERITY_BLOCKER = "BLOCKER"
SEVERITY_WARNING = "WARNING"
_SEVERITY_ORDER: Mapping[str, int] = MappingProxyType({SEVERITY_BLOCKER: 0, SEVERITY_WARNING: 1})

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_ARCHIVED_SEGMENTS_CASEFOLDED = frozenset({"2026_finished_events", "finished_events"})

# Conservative, normalized (lowercased, non-alphanumeric-stripped) substring
# markers used to fail closed on an apparent credential/secret in metadata
# (§9.6 Rule 12). This is deliberately broad -- a false positive here only
# costs a manual review, never a silent secret leak.
_SECRET_KEY_MARKERS: tuple[str, ...] = (
    "apikey", "token", "secret", "password", "credential", "authkey",
)


def _normalize_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


# ── Public dataclasses ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class SourceManifestContext:
    """Caller-supplied, already-validated context. Never derived from
    ``config/active_event.json`` by this module -- obtaining these values
    (for example via ``engine/event_context.py``'s ``EventContext``) is the
    caller's responsibility in a future, separately authorized integration.
    """

    event_slug: str
    venue_slug: str
    event_root: Path
    repo_root: Path

    @property
    def input_root(self) -> Path:
        return self.event_root / "input"


@dataclass(frozen=True)
class Finding:
    """One structured resolver/validation finding."""

    severity: str
    code: str
    message: str
    role: Optional[str] = None


@dataclass(frozen=True)
class IntegrityOutcome:
    """One field's (``sha256`` or ``row_count``) validation outcome."""

    state: str  # verified | mismatch | not_asserted | unable_to_validate
    detail: Optional[str] = None


@dataclass(frozen=True)
class ResolvedSource:
    """One usable, declared source entry: path-safe and resolved to an
    existing regular file. Present in ``resolved_sources`` only when the
    declared ``path`` passed every §9.4/§9.6 path-safety check and the
    resolved target exists as a regular file -- integrity mismatches do not
    remove an entry from this mapping, since a mismatch is a finding about
    the file's content, not about whether the file was locatable.
    """

    role: str
    declared_path: str
    resolved_path: Path
    required: Optional[bool]
    missing_behavior: Optional[str]
    schema_id: Optional[str]
    identity_key: Optional[str]
    encoding: str
    sha256_outcome: IntegrityOutcome
    row_count_outcome: IntegrityOutcome
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class SourceManifestResolution:
    """Deterministic, complete resolver/validation result for one manifest."""

    schema_version: Optional[str]
    event_slug: Optional[str]
    venue_slug: Optional[str]
    resolved_sources: Mapping[str, ResolvedSource]
    findings: tuple[Finding, ...]

    @property
    def blockers(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == SEVERITY_BLOCKER)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == SEVERITY_WARNING)

    @property
    def is_release_blocked(self) -> bool:
        return len(self.blockers) > 0


# ── Finding helpers ──────────────────────────────────────────────────────────

def _finding(severity: str, code: str, message: str, role: Optional[str] = None) -> Finding:
    return Finding(severity=severity, code=code, message=message, role=role)


def _sorted_findings(findings: Sequence[Finding]) -> tuple[Finding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda f: (_SEVERITY_ORDER.get(f.severity, 2), f.code, f.role or "", f.message),
        )
    )


# ── Path safety (standards/04 §9.4 path rule, §9.6 Rule 3) ─────────────────
#
# This reimplements, scoped to one manifest's declared source-file paths,
# the same lexical-then-resolved containment approach
# engine/event_context.py already applies to its own manifest path fields:
# reject absolute/drive/backslash/traversal/archived-segment paths by string
# inspection first, then confirm the resolved target via resolve() +
# relative_to() (never a string prefix) so a symlink or junction escape is
# caught on the physical resolved path, not the declared text. It adds this
# schema's own requirements beyond EventContext: containment specifically
# under the event's own input root, and a regular-file check on the target.

def _validate_declared_path(
    declared: object, context: SourceManifestContext, role: str,
) -> tuple[Optional[Path], list[Finding]]:
    findings: list[Finding] = []

    if not isinstance(declared, str) or not declared.strip():
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_NOT_STRING",
            f"{role}: path must be a non-empty string; found {declared!r}", role,
        ))
        return None, findings

    if "\\" in declared:
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_BACKSLASH",
            f"{role}: path must not contain a backslash: {declared!r}", role,
        ))
        return None, findings

    if declared.startswith("/") or _DRIVE_RE.match(declared):
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_ABSOLUTE",
            f"{role}: path must be relative, not absolute or drive-rooted: {declared!r}", role,
        ))
        return None, findings

    pure = PurePosixPath(declared)

    if any(part == ".." for part in pure.parts):
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_TRAVERSAL",
            f"{role}: path must not contain '..' traversal: {declared!r}", role,
        ))
        return None, findings

    if any(part.casefold() in _ARCHIVED_SEGMENTS_CASEFOLDED for part in pure.parts):
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_ARCHIVED_SEGMENT_DECLARED",
            f"{role}: path declares an archived/finished-event segment: {declared!r}", role,
        ))
        return None, findings

    input_root_resolved = context.input_root.resolve()
    repo_root_resolved = context.repo_root.resolve()
    resolved = context.input_root.joinpath(*pure.parts).resolve()

    try:
        repo_relative = resolved.relative_to(repo_root_resolved)
    except ValueError:
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_REPOSITORY_ESCAPE",
            f"{role}: resolved path escapes the repository root: {declared!r}", role,
        ))
        return None, findings

    if any(part.casefold() in _ARCHIVED_SEGMENTS_CASEFOLDED for part in repo_relative.parts):
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_ARCHIVED_SEGMENT_RESOLVED",
            f"{role}: resolved path lands under an archived/finished-event location: {declared!r}", role,
        ))
        return None, findings

    try:
        resolved.relative_to(input_root_resolved)
    except ValueError:
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_INPUT_ROOT_ESCAPE",
            f"{role}: resolved path escapes the event's own input root: {declared!r}", role,
        ))
        return None, findings

    if resolved.exists() and not resolved.is_file():
        findings.append(_finding(
            SEVERITY_BLOCKER, "PATH_NOT_REGULAR_FILE",
            f"{role}: resolved target is not a regular file: {declared!r}", role,
        ))
        return None, findings

    return resolved, findings


# ── Integrity computation (standards/04 §9.4, §9.4A) ────────────────────────

def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_data_rows(path: Path, encoding: str) -> int:
    """Count physical data rows, header excluded. A blank line counts as a
    data row; a row malformed relative to the source's own schema is still
    counted -- this counts physical lines, never parses CSV structure, so
    it can never silently drop or estimate a row (standards/04 §9.4A).
    """
    text = path.read_text(encoding=encoding)
    lines = text.splitlines()
    if not lines:
        return 0
    return len(lines) - 1


def _validate_sha256(declared: object, resolved_path: Optional[Path]) -> IntegrityOutcome:
    if declared is None:
        return IntegrityOutcome(INTEGRITY_NOT_ASSERTED)
    if not isinstance(declared, str) or not _SHA256_RE.match(declared):
        return IntegrityOutcome(
            INTEGRITY_MISMATCH,
            detail=f"declared sha256 is not a lowercase 64-character hexadecimal digest: {declared!r}",
        )
    if resolved_path is None:
        return IntegrityOutcome(INTEGRITY_UNABLE_TO_VALIDATE, detail="source file could not be located")
    try:
        actual = _compute_sha256(resolved_path)
    except OSError as exc:
        return IntegrityOutcome(INTEGRITY_UNABLE_TO_VALIDATE, detail=f"source file could not be read: {exc}")
    if actual == declared:
        return IntegrityOutcome(INTEGRITY_VERIFIED)
    return IntegrityOutcome(INTEGRITY_MISMATCH, detail="computed sha256 does not match declared value")


def _validate_row_count(
    declared: object, resolved_path: Optional[Path], encoding: str,
) -> IntegrityOutcome:
    if declared is None:
        return IntegrityOutcome(INTEGRITY_NOT_ASSERTED)
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
        return IntegrityOutcome(
            INTEGRITY_MISMATCH,
            detail=f"declared row_count is not a non-negative integer: {declared!r}",
        )
    if resolved_path is None:
        return IntegrityOutcome(INTEGRITY_UNABLE_TO_VALIDATE, detail="source file could not be located")
    try:
        actual = _count_data_rows(resolved_path, encoding)
    except (OSError, UnicodeDecodeError) as exc:
        return IntegrityOutcome(
            INTEGRITY_UNABLE_TO_VALIDATE, detail=f"source file could not be read or decoded: {exc}",
        )
    if actual == declared:
        return IntegrityOutcome(INTEGRITY_VERIFIED)
    return IntegrityOutcome(
        INTEGRITY_MISMATCH,
        detail=f"computed row_count {actual} does not match declared value {declared}",
    )


# ── Secret/credential scan (standards/04 §9.6 Rule 12) ──────────────────────

def _scan_for_secrets(metadata: Mapping[str, object], role: str) -> list[Finding]:
    findings: list[Finding] = []

    def walk(obj: object) -> None:
        if isinstance(obj, Mapping):
            for key, value in obj.items():
                if any(marker in _normalize_key(key) for marker in _SECRET_KEY_MARKERS):
                    findings.append(_finding(
                        SEVERITY_BLOCKER, "CREDENTIAL_IN_METADATA",
                        f"{role}: metadata key {key!r} resembles a credential or secret", role,
                    ))
                walk(value)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)

    walk(metadata)
    return findings


# ── Per-entry validation ─────────────────────────────────────────────────────

def _validate_source_entry(
    entry: Mapping[str, object], role: str, context: SourceManifestContext,
) -> tuple[list[Finding], Optional[ResolvedSource]]:
    findings: list[Finding] = []

    required = entry.get("required")
    if not isinstance(required, bool):
        findings.append(_finding(
            SEVERITY_BLOCKER, "REQUIRED_NOT_BOOLEAN",
            f"{role}: required must be a boolean; found {required!r}", role,
        ))

    missing_behavior = entry.get("missing_behavior")
    if missing_behavior not in ALL_MISSING_BEHAVIORS:
        findings.append(_finding(
            SEVERITY_BLOCKER, "MISSING_BEHAVIOR_INVALID",
            f"{role}: missing_behavior {missing_behavior!r} is not a recognized value", role,
        ))
    elif role in ROLE_REQUIRED and missing_behavior in ADDITIONAL_ONLY_MISSING_BEHAVIORS:
        findings.append(_finding(
            SEVERITY_BLOCKER, "MISSING_BEHAVIOR_NOT_PERMITTED_FOR_ROLE",
            f"{role}: missing_behavior {missing_behavior!r} is reserved for an additional "
            f"role and is not permitted for one of the thirteen required roles", role,
        ))

    metadata = entry.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        findings.append(_finding(
            SEVERITY_BLOCKER, "METADATA_NOT_OBJECT",
            f"{role}: metadata must be an object; found {metadata!r}", role,
        ))
        metadata = {}
    metadata = metadata or {}
    findings.extend(_scan_for_secrets(metadata, role))

    identity_key = entry.get("identity_key")
    if identity_key is not None and identity_key not in VALID_IDENTITY_KEYS:
        findings.append(_finding(
            SEVERITY_BLOCKER, "IDENTITY_KEY_INVALID",
            f"{role}: identity_key {identity_key!r} is not one of {VALID_IDENTITY_KEYS}", role,
        ))

    encoding = entry.get("encoding", "utf-8")
    if encoding not in VALID_ENCODINGS:
        findings.append(_finding(
            SEVERITY_BLOCKER, "ENCODING_INVALID",
            f"{role}: encoding {encoding!r} is not one of {VALID_ENCODINGS}", role,
        ))
        encoding = "utf-8"

    declared_path = entry.get("path")
    resolved_path, path_findings = _validate_declared_path(declared_path, context, role)
    findings.extend(path_findings)

    # A safely-declared path whose target does not exist is a missing
    # source, not a path-safety defect -- the presence/missing_behavior
    # pass (in resolve_source_manifest) is the sole authority for that.
    if resolved_path is not None and not resolved_path.exists():
        resolved_path = None

    sha256_outcome = _validate_sha256(entry.get("sha256"), resolved_path)
    if sha256_outcome.state == INTEGRITY_MISMATCH:
        findings.append(_finding(
            SEVERITY_BLOCKER, "SHA256_MISMATCH",
            f"{role}: {sha256_outcome.detail}", role,
        ))
    elif sha256_outcome.state == INTEGRITY_UNABLE_TO_VALIDATE:
        findings.append(_finding(
            SEVERITY_BLOCKER, "SHA256_UNABLE_TO_VALIDATE",
            f"{role}: {sha256_outcome.detail}", role,
        ))

    row_count_outcome = _validate_row_count(entry.get("row_count"), resolved_path, encoding)
    if row_count_outcome.state == INTEGRITY_MISMATCH:
        findings.append(_finding(
            SEVERITY_BLOCKER, "ROW_COUNT_MISMATCH",
            f"{role}: {row_count_outcome.detail}", role,
        ))
    elif row_count_outcome.state == INTEGRITY_UNABLE_TO_VALIDATE:
        findings.append(_finding(
            SEVERITY_BLOCKER, "ROW_COUNT_UNABLE_TO_VALIDATE",
            f"{role}: {row_count_outcome.detail}", role,
        ))

    resolved_source: Optional[ResolvedSource] = None
    if resolved_path is not None and isinstance(declared_path, str):
        resolved_source = ResolvedSource(
            role=role,
            declared_path=declared_path,
            resolved_path=resolved_path,
            required=required if isinstance(required, bool) else None,
            missing_behavior=missing_behavior if missing_behavior in ALL_MISSING_BEHAVIORS else None,
            schema_id=entry.get("schema_id") if isinstance(entry.get("schema_id"), str) else None,
            identity_key=identity_key if identity_key in VALID_IDENTITY_KEYS else None,
            encoding=encoding,
            sha256_outcome=sha256_outcome,
            row_count_outcome=row_count_outcome,
            metadata=MappingProxyType(dict(metadata)),
        )

    return findings, resolved_source


# ── Cross-field rules (standards/04 §9.6) ───────────────────────────────────

def _validate_similar_course_provenance(
    entries_by_role: Mapping[str, Mapping[str, object]],
) -> list[Finding]:
    findings: list[Finding] = []
    provenance_by_role: dict[str, tuple[object, object, object]] = {}

    for role in SIMILAR_SG_ROLES:
        entry = entries_by_role.get(role)
        if entry is None:
            continue
        metadata = entry.get("metadata")
        if not isinstance(metadata, Mapping):
            findings.append(_finding(
                SEVERITY_BLOCKER, "SIMILAR_COURSE_METADATA_MISSING",
                f"{role}: metadata must declare similar_course_set_id, set_version, "
                f"set_provenance, and horizon_months", role,
            ))
            continue

        horizon_months = metadata.get("horizon_months")
        if horizon_months != SIMILAR_SG_HORIZON_MONTHS[role]:
            findings.append(_finding(
                SEVERITY_BLOCKER, "SIMILAR_COURSE_HORIZON_MONTHS_MISMATCH",
                f"{role}: horizon_months must equal {SIMILAR_SG_HORIZON_MONTHS[role]}; "
                f"found {horizon_months!r}", role,
            ))

        provenance_by_role[role] = (
            metadata.get("similar_course_set_id"),
            metadata.get("set_version"),
            metadata.get("set_provenance"),
        )

    if len(provenance_by_role) >= 2 and len(set(provenance_by_role.values())) > 1:
        for role in provenance_by_role:
            findings.append(_finding(
                SEVERITY_BLOCKER, "SIMILAR_COURSE_PROVENANCE_MISMATCH",
                f"{role}: similar_course_set_id/set_version/set_provenance must be "
                f"identical across all three similar-course horizons", role,
            ))

    return findings


def _validate_venue_history_metadata(
    entries_by_role: Mapping[str, Mapping[str, object]], context: SourceManifestContext,
) -> list[Finding]:
    entry = entries_by_role.get("venue_history")
    if entry is None:
        return []

    metadata = entry.get("metadata")
    if not isinstance(metadata, Mapping):
        return [_finding(
            SEVERITY_BLOCKER, "VENUE_HISTORY_METADATA_MISSING",
            "venue_history: metadata must declare a venue_slug sub-field", "venue_history",
        )]

    declared_venue_slug = metadata.get("venue_slug")
    if declared_venue_slug != context.venue_slug:
        return [_finding(
            SEVERITY_BLOCKER, "VENUE_HISTORY_VENUE_MISMATCH",
            f"venue_history: metadata venue_slug must equal {context.venue_slug!r}; "
            f"found {declared_venue_slug!r}", "venue_history",
        )]

    return []


# ── Top-level shape (standards/04 §9.3) ─────────────────────────────────────

def _validate_slug_field(value: object, field_name: str) -> list[Finding]:
    if not isinstance(value, str) or not _SLUG_RE.match(value):
        return [_finding(
            SEVERITY_BLOCKER, f"{field_name.upper()}_INVALID_FORMAT",
            f"{field_name} must be lowercase snake_case; found {value!r}",
        )]
    return []


# ── Public entry point ───────────────────────────────────────────────────────

def resolve_source_manifest(
    manifest: object, *, context: SourceManifestContext,
) -> SourceManifestResolution:
    """Resolve and validate one already-parsed ``source_manifest`` object
    against ``context``. Never reads ``config/active_event.json`` and never
    constructs a physical filename from ``event_slug``/``venue_slug`` --
    every ``path`` is read literally from the manifest (§9.6 Rule 1).
    """
    findings: list[Finding] = []

    if not isinstance(manifest, Mapping):
        findings.append(_finding(
            SEVERITY_BLOCKER, "MANIFEST_NOT_OBJECT",
            f"source_manifest must be a JSON object; found {type(manifest).__name__}",
        ))
        return SourceManifestResolution(
            schema_version=None, event_slug=None, venue_slug=None,
            resolved_sources=MappingProxyType({}), findings=_sorted_findings(findings),
        )

    schema_version = manifest.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        findings.append(_finding(
            SEVERITY_BLOCKER, "SCHEMA_VERSION_MISMATCH",
            f"schema_version must equal {SCHEMA_VERSION!r}; found {schema_version!r}",
        ))

    event_slug = manifest.get("event_slug")
    findings.extend(_validate_slug_field(event_slug, "event_slug"))
    if isinstance(event_slug, str) and _SLUG_RE.match(event_slug) and event_slug != context.event_slug:
        findings.append(_finding(
            SEVERITY_BLOCKER, "EVENT_SLUG_MISMATCH",
            f"event_slug must equal the active context's {context.event_slug!r}; found {event_slug!r}",
        ))

    venue_slug = manifest.get("venue_slug")
    findings.extend(_validate_slug_field(venue_slug, "venue_slug"))
    if isinstance(venue_slug, str) and _SLUG_RE.match(venue_slug) and venue_slug != context.venue_slug:
        findings.append(_finding(
            SEVERITY_BLOCKER, "VENUE_SLUG_MISMATCH",
            f"venue_slug must equal the active context's {context.venue_slug!r}; found {venue_slug!r}",
        ))

    sources = manifest.get("sources")
    if not isinstance(sources, list):
        findings.append(_finding(
            SEVERITY_BLOCKER, "SOURCES_NOT_LIST",
            f"sources must be an array; found {type(sources).__name__}",
        ))
        sources = []

    entries_by_role: dict[str, Mapping[str, object]] = {}
    resolved_by_role: dict[str, ResolvedSource] = {}

    for index, entry in enumerate(sources):
        if not isinstance(entry, Mapping):
            findings.append(_finding(
                SEVERITY_BLOCKER, "SOURCE_ENTRY_NOT_OBJECT",
                f"sources[{index}] must be an object; found {type(entry).__name__}",
            ))
            continue

        role = entry.get("role")
        if not isinstance(role, str) or not role:
            findings.append(_finding(
                SEVERITY_BLOCKER, "ROLE_NOT_STRING",
                f"sources[{index}]: role must be a non-empty string; found {role!r}",
            ))
            continue

        if role in entries_by_role:
            findings.append(_finding(
                SEVERITY_BLOCKER, "DUPLICATE_ROLE",
                f"role {role!r} is declared more than once in sources", role,
            ))
            continue

        entries_by_role[role] = entry
        entry_findings, resolved = _validate_source_entry(entry, role, context)
        findings.extend(entry_findings)
        if resolved is not None:
            resolved_by_role[role] = resolved

    # §9.5A: required/missing_behavior must match the fixed table exactly
    # for each of the thirteen roles; a missing required (block_release)
    # role blocks release, a missing optional/composite-deferred role only
    # warns, scoped to its own named outcome.
    for role in REQUIRED_ROLES:
        entry = entries_by_role.get(role)
        if entry is not None:
            declared_required = entry.get("required")
            declared_missing_behavior = entry.get("missing_behavior")
            if (
                declared_required != ROLE_REQUIRED[role]
                or declared_missing_behavior != ROLE_MISSING_BEHAVIOR[role]
            ):
                findings.append(_finding(
                    SEVERITY_BLOCKER, "ROLE_REQUIRED_MISSING_BEHAVIOR_MISMATCH",
                    f"{role}: required/missing_behavior must be "
                    f"{ROLE_REQUIRED[role]!r}/{ROLE_MISSING_BEHAVIOR[role]!r}; "
                    f"found {declared_required!r}/{declared_missing_behavior!r}", role,
                ))

        if role not in resolved_by_role:
            behavior = ROLE_MISSING_BEHAVIOR[role]
            if behavior == "block_release":
                findings.append(_finding(
                    SEVERITY_BLOCKER, "SOURCE_MISSING_BLOCK_RELEASE",
                    f"{role}: required source is missing or unresolved; release blocked", role,
                ))
            else:
                findings.append(_finding(
                    SEVERITY_WARNING, "SOURCE_MISSING",
                    f"{role}: source is missing or unresolved; outcome scoped to {behavior!r}", role,
                ))

    findings.extend(_validate_similar_course_provenance(entries_by_role))
    findings.extend(_validate_venue_history_metadata(entries_by_role, context))

    return SourceManifestResolution(
        schema_version=schema_version if isinstance(schema_version, str) else None,
        event_slug=event_slug if isinstance(event_slug, str) else None,
        venue_slug=venue_slug if isinstance(venue_slug, str) else None,
        resolved_sources=MappingProxyType(resolved_by_role),
        findings=_sorted_findings(findings),
    )
