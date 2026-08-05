#!/usr/bin/env python3
"""Statically validate the canonical VenueDNA scoring-doctrine contract.

The validator is intentionally read-only.  It parses Markdown, JSON, and
Python source text without importing or executing production scoring modules.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SCORING_SPEC = "standards/02_PGA_VENUEDNA_SCORING_SPEC.md"
LEARNING_LOOP = "standards/03_PGA_VENUEDNA_LEARNING_LOOP.md"
ARTIFACT_SCHEMA = "standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md"
COUNCIL_GOVERNANCE = "standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md"
DIAGNOSTIC_SOURCE = "engine/scoring_decomposition.py"
ACTIVE_EVENT = "config/active_event.json"

REQUIRED_FILES = (
    SCORING_SPEC,
    LEARNING_LOOP,
    ARTIFACT_SCHEMA,
    COUNCIL_GOVERNANCE,
    DIAGNOSTIC_SOURCE,
    ACTIVE_EVENT,
)

MARKER_NAME = "scoring-doctrine-v2"
MARKER_PATTERN = re.compile(
    r"<!--\s*scoring-doctrine-v2(?P<body>.*?)-->", re.DOTALL
)
MARKER_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

EXPECTED_MARKER = {
    "formula_id": "venuedna_dual_vector_decomposed",
    "formula_version": "2.0.0",
    "comparable_score_family": "dual_vector_sg_per_round_v2",
    "penalty_gate_set_id": "venuedna_v2_none",
    "canonical_core_inputs": "SG_Base_Comp,Delta_Fit_Comp,VenueHistoryDeltaRaw",
    "excluded_legacy_noncore_addends": (
        "trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20"
    ),
}
EXPECTED_MARKER_KEYS = tuple(EXPECTED_MARKER)
EXPECTED_CORE_INPUTS = tuple(EXPECTED_MARKER["canonical_core_inputs"].split(","))
EXPECTED_EXCLUDED_ADDENDS = tuple(
    EXPECTED_MARKER["excluded_legacy_noncore_addends"].split(",")
)
EXPECTED_DIVERGENCE_REASONS = (
    "FORMULA_IDENTITY_MISMATCH",
    "LEGACY_NONCORE_ADDITIVE_COMPONENTS",
    "CANONICAL_THREE_LAYER_DECOMPOSITION_NOT_EXPOSED",
    "HISTORICAL_3M_EVENT_SPECIFIC_IMPLEMENTATION",
    "FORMULA_V2_MIGRATION_PENDING",
    "PENALTY_GATE_SET_ID_MISMATCH",
)

NULL_EVENT_BINDINGS = (
    "event_slug",
    "event_name",
    "venue_slug",
    "venue_name",
    "event_root",
    "venue_profile",
    "event_context_file",
    "field_file",
    "weather_file",
    "tee_times_file",
    "pre_event_artifact",
    "live_round",
    "live_artifact",
    "deploy_root",
    "audit_root",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    rule_id: str
    file: str
    reason: str


@dataclass(frozen=True)
class ValidationReport:
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.severity == "error")


class ValidationConfigurationError(RuntimeError):
    """The validator could not safely inspect the requested repository."""


def _sorted_findings(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    return tuple(
        sorted(
            findings,
            key=lambda item: (item.severity, item.rule_id, item.file, item.reason),
        )
    )


def _finding(rule_id: str, file: str, reason: str, severity: str = "error") -> Finding:
    return Finding(severity=severity, rule_id=rule_id, file=file, reason=reason)


def _read_required(repo_root: Path, relative: str) -> str:
    path = repo_root / relative
    if not path.is_file():
        raise ValidationConfigurationError(f"Required doctrine source is missing: {relative}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationConfigurationError(f"Cannot read {relative}: {exc}") from exc


def _parse_marker_text(
    text: str, *, strict: bool
) -> tuple[dict[str, str], list[Finding]]:
    matches = list(MARKER_PATTERN.finditer(text))
    findings: list[Finding] = []
    metadata: dict[str, str] = {}

    if len(matches) != 1:
        findings.append(
            _finding(
                "MARKER_COUNT",
                SCORING_SPEC,
                f"Expected exactly one {MARKER_NAME} marker; found {len(matches)}.",
            )
        )
        return metadata, findings

    seen: set[str] = set()
    for line_number, raw_line in enumerate(matches[0].group("body").splitlines(), start=1):
        if not raw_line.strip():
            continue
        if raw_line != raw_line.strip() or raw_line.count("=") != 1:
            findings.append(
                _finding(
                    "MARKER_MALFORMED_ASSIGNMENT",
                    SCORING_SPEC,
                    f"Marker line {line_number} is not an exact key=value assignment: {raw_line!r}.",
                )
            )
            continue

        key, value = raw_line.split("=", 1)
        if not MARKER_KEY_PATTERN.fullmatch(key):
            findings.append(
                _finding(
                    "MARKER_MALFORMED_ASSIGNMENT",
                    SCORING_SPEC,
                    f"Marker line {line_number} has an invalid key: {key!r}.",
                )
            )
            continue

        if key in seen:
            findings.append(
                _finding(
                    "MARKER_DUPLICATE_KEY",
                    SCORING_SPEC,
                    f"Marker key is assigned more than once: {key}.",
                )
            )
            continue
        seen.add(key)
        metadata[key] = value

        if value == "":
            findings.append(
                _finding(
                    "MARKER_EMPTY_VALUE",
                    SCORING_SPEC,
                    f"Marker key has an empty value: {key}.",
                )
            )

        if key not in EXPECTED_MARKER:
            findings.append(
                _finding(
                    "MARKER_UNKNOWN_KEY",
                    SCORING_SPEC,
                    f"Unknown marker key: {key}.",
                    severity="error" if strict else "warning",
                )
            )

    missing = [key for key in EXPECTED_MARKER_KEYS if key not in metadata]
    if missing:
        findings.append(
            _finding(
                "MARKER_REQUIRED_KEYS",
                SCORING_SPEC,
                "Missing required marker keys: " + ", ".join(missing) + ".",
            )
        )

    value_rules = {
        "formula_id": "MARKER_FORMULA_ID",
        "formula_version": "MARKER_FORMULA_VERSION",
        "comparable_score_family": "MARKER_COMPARABLE_FAMILY",
        "penalty_gate_set_id": "MARKER_PENALTY_GATE_SET",
        "canonical_core_inputs": "MARKER_CORE_INPUTS",
        "excluded_legacy_noncore_addends": "MARKER_EXCLUDED_ADDENDS",
    }
    for key, expected in EXPECTED_MARKER.items():
        if key in metadata and metadata[key] != expected:
            findings.append(
                _finding(
                    value_rules[key],
                    SCORING_SPEC,
                    f"{key} must equal {expected!r}; found {metadata[key]!r}.",
                )
            )

    canonical = tuple(metadata.get("canonical_core_inputs", "").split(","))
    excluded = tuple(metadata.get("excluded_legacy_noncore_addends", "").split(","))
    overlap = sorted((set(canonical) - {""}) & (set(excluded) - {""}))
    if overlap:
        findings.append(
            _finding(
                "MARKER_COMPONENT_OVERLAP",
                SCORING_SPEC,
                "Canonical and excluded component sets overlap: " + ", ".join(overlap) + ".",
            )
        )

    return metadata, findings


def parse_doctrine_marker(path: Path) -> dict[str, str]:
    """Return the sole valid marker, raising ``ValueError`` for malformed input."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read doctrine marker source {path}: {exc}") from exc
    metadata, findings = _parse_marker_text(text, strict=False)
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise ValueError("; ".join(finding.reason for finding in errors))
    return metadata


def _literal_or_resolved(node: ast.AST, literals: dict[str, object]) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        if isinstance(node, ast.Name) and node.id in literals:
            return literals[node.id]
        raise ValueError("expression is not a static literal")


def extract_python_literals(path: Path) -> dict[str, object]:
    """Extract top-level literals and ``FORMULA`` descriptor keyword values.

    Source is parsed with :func:`ast.parse`; values are accepted only through
    :func:`ast.literal_eval` or a reference to an already extracted literal.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ValueError(f"Cannot statically parse {path}: {exc}") from exc

    literals: dict[str, object] = {}
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and value is not None:
            try:
                literals[target.id] = ast.literal_eval(value)
            except (ValueError, TypeError, SyntaxError):
                pass

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name) or node.targets[0].id != "FORMULA":
            continue
        if not isinstance(node.value, ast.Call):
            continue
        for keyword in node.value.keywords:
            if keyword.arg is None:
                continue
            try:
                literals[f"FORMULA.{keyword.arg}"] = _literal_or_resolved(
                    keyword.value, literals
                )
            except ValueError:
                continue
    return literals


def _expect_literal(
    findings: list[Finding],
    literals: dict[str, object],
    name: str,
    expected: object,
    rule_id: str,
) -> None:
    actual = literals.get(name, object())
    if actual != expected:
        rendered = "missing" if name not in literals else repr(actual)
        findings.append(
            _finding(
                rule_id,
                DIAGNOSTIC_SOURCE,
                f"{name} must equal {expected!r}; found {rendered}.",
            )
        )


def _validate_diagnostics(
    repo_root: Path, marker: dict[str, str]
) -> list[Finding]:
    try:
        literals = extract_python_literals(repo_root / DIAGNOSTIC_SOURCE)
    except ValueError as exc:
        raise ValidationConfigurationError(str(exc)) from exc

    findings: list[Finding] = []
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_FORMULA_ID",
        marker.get("formula_id"),
        "DIAGNOSTIC_FORMULA_ID",
    )
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_FORMULA_VERSION",
        marker.get("formula_version"),
        "DIAGNOSTIC_FORMULA_VERSION",
    )
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_PENALTY_GATE_SET_ID",
        marker.get("penalty_gate_set_id"),
        "DIAGNOSTIC_PENALTY_GATE_SET",
    )
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_ACTIVE_PENALTY_IDS",
        (),
        "DIAGNOSTIC_ACTIVE_PENALTIES",
    )
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_ACTIVE_GATE_IDS",
        (),
        "DIAGNOSTIC_ACTIVE_GATES",
    )
    _expect_literal(
        findings,
        literals,
        "HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID",
        "historical_3m_inline_gates",
        "DIAGNOSTIC_PRODUCTION_GATE_ID",
    )
    _expect_literal(
        findings,
        literals,
        "CANONICAL_V2_CORE_INPUTS",
        EXPECTED_CORE_INPUTS,
        "DIAGNOSTIC_CORE_INPUTS",
    )
    _expect_literal(
        findings,
        literals,
        "LEGACY_PRODUCTION_NONCORE_ADDENDS",
        EXPECTED_EXCLUDED_ADDENDS,
        "DIAGNOSTIC_EXCLUDED_ADDENDS",
    )
    _expect_literal(
        findings,
        literals,
        "PRODUCTION_DIVERGENCE_REASON_CODES",
        EXPECTED_DIVERGENCE_REASONS,
        "DIAGNOSTIC_DIVERGENCE_REASONS",
    )
    _expect_literal(
        findings,
        literals,
        "FORMULA.formula_identifier",
        "3m-enriched-v2.0",
        "DIAGNOSTIC_PRODUCTION_FORMULA_ID",
    )

    canonical_id = literals.get("CANONICAL_V2_FORMULA_ID")
    production_id = literals.get("FORMULA.formula_identifier")
    if production_id == canonical_id:
        findings.append(
            _finding(
                "DIAGNOSTIC_PRODUCTION_FORMULA_DIVERGENCE",
                DIAGNOSTIC_SOURCE,
                "Historical production formula identity must remain distinct from canonical v2 identity.",
            )
        )

    canonical_gate = literals.get("CANONICAL_V2_PENALTY_GATE_SET_ID")
    production_gate = literals.get("HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID")
    if production_gate == canonical_gate:
        findings.append(
            _finding(
                "DIAGNOSTIC_PRODUCTION_GATE_DIVERGENCE",
                DIAGNOSTIC_SOURCE,
                "Historical production gate configuration must remain distinct from venuedna_v2_none.",
            )
        )

    descriptor_pairs = (
        ("canonical_formula_id", "CANONICAL_V2_FORMULA_ID"),
        ("canonical_formula_version", "CANONICAL_V2_FORMULA_VERSION"),
        ("canonical_penalty_gate_set_id", "CANONICAL_V2_PENALTY_GATE_SET_ID"),
        ("canonical_active_penalty_ids", "CANONICAL_V2_ACTIVE_PENALTY_IDS"),
        ("canonical_active_gate_ids", "CANONICAL_V2_ACTIVE_GATE_IDS"),
        ("production_gate_configuration_id", "HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID"),
        ("canonical_core_inputs", "CANONICAL_V2_CORE_INPUTS"),
        ("legacy_production_noncore_addends", "LEGACY_PRODUCTION_NONCORE_ADDENDS"),
        ("production_divergence_reason_codes", "PRODUCTION_DIVERGENCE_REASON_CODES"),
    )
    mismatches = [
        field
        for field, constant in descriptor_pairs
        if literals.get(f"FORMULA.{field}", object()) != literals.get(constant, object())
    ]
    if mismatches:
        findings.append(
            _finding(
                "DIAGNOSTIC_DESCRIPTOR_MISMATCH",
                DIAGNOSTIC_SOURCE,
                "FORMULA descriptor fields do not match diagnostic constants: "
                + ", ".join(mismatches)
                + ".",
            )
        )
    return findings


def _normalize_prose(text: str) -> str:
    text = text.casefold().replace("`", "").replace("*", "")
    text = text.replace("–", "-").replace("—", "-")
    return " ".join(text.split())


def _extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^(?P<marks>#+)\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return ""
    level = len(match.group("marks"))
    following = re.compile(rf"^#{{1,{level}}}\s+", re.MULTILINE).search(text, match.end())
    end = following.start() if following else len(text)
    return text[match.start():end]


def _require_terms(
    findings: list[Finding],
    *,
    section: str,
    terms: Iterable[str],
    rule_id: str,
    file: str,
    reason: str,
) -> None:
    normalized = _normalize_prose(section)
    if not section or any(_normalize_prose(term) not in normalized for term in terms):
        findings.append(_finding(rule_id, file, reason))


def _validate_governance(texts: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    scoring = texts[SCORING_SPEC]
    missing = _extract_section(scoring, "7.5 Missing-data behavior")

    _require_terms(
        findings,
        section=missing,
        terms=("Missing values must not be represented as legitimate numeric zero.",),
        rule_id="GOV_MISSING_NOT_ZERO",
        file=SCORING_SPEC,
        reason="Section 7.5 must distinguish missing data from legitimate numeric zero.",
    )
    _require_terms(
        findings,
        section=missing,
        terms=(
            "With two valid NeutralSkill horizons",
            "renormalize within NeutralSkill",
            "with fewer than two, the player is UNSCORED",
        ),
        rule_id="GOV_NEUTRALSKILL_HORIZONS",
        file=SCORING_SPEC,
        reason="Section 7.5 must retain two-horizon renormalization and fewer-than-two UNSCORED behavior.",
    )
    _require_terms(
        findings,
        section=missing,
        terms=("A valid similar-course row with zero rounds is DEBUT",),
        rule_id="GOV_DEBUT_REQUIRES_VALID_ROW",
        file=SCORING_SPEC,
        reason="Section 7.5 must require a valid zero-round similar-course row for DEBUT.",
    )
    _require_terms(
        findings,
        section=missing,
        terms=("Missing raw venue-history data remains missing",),
        rule_id="GOV_VENUE_HISTORY_REMAINS_MISSING",
        file=SCORING_SPEC,
        reason="Section 7.5 must preserve missing raw venue-history data as missing.",
    )
    _require_terms(
        findings,
        section=missing,
        terms=(
            "VenueHistoryDeltaRaw = 0.0 is an explicit neutral contribution",
            "not conversion of raw-source missingness into observed zero data",
        ),
        rule_id="GOV_VENUE_HISTORY_NEUTRAL_ZERO",
        file=SCORING_SPEC,
        reason="Section 7.5 must define VenueHistoryDeltaRaw 0.0 as neutral doctrine, not zero filling.",
    )
    _require_terms(
        findings,
        section=missing,
        terms=("Missing mandatory gate evidence produces an UNKNOWN gate evaluation",),
        rule_id="GOV_GATE_EVIDENCE_UNKNOWN",
        file=SCORING_SPEC,
        reason="Section 7.5 must map missing mandatory gate evidence to UNKNOWN.",
    )

    artifact_inputs = _extract_section(
        texts[ARTIFACT_SCHEMA],
        "2C. pga_sg_query_allcourses_l{6,12,24}.csv and pga_sg_query_{slug}_similar_l{6,12,24}.csv",
    )
    _require_terms(
        findings,
        section=artifact_inputs,
        terms=(
            "Genuine numeric 0.0 in total_mean is valid observed data",
            "unavailable total_mean values remain missing",
            "not be silently converted to numeric zero",
        ),
        rule_id="GOV_ARTIFACT_MISSING_VALUES",
        file=ARTIFACT_SCHEMA,
        reason="Artifact input section 2C must preserve numeric-zero versus missing-value semantics.",
    )

    rocket_scoring = _extract_section(
        scoring, "17. ROCKET CLASSIC 2026 INACTIVE RESEARCH HYPOTHESES"
    )
    rocket_live = _extract_section(
        scoring, "18. INACTIVE ROCKET-DERIVED LIVE-BADGE HYPOTHESIS (ALPHA/BETA/GAMMA)"
    )
    rocket_learning = _extract_section(
        texts[LEARNING_LOOP], "10. ROCKET CLASSIC 2026 LEARNING ENTRY"
    )
    rocket_all = "\n".join((rocket_scoring, rocket_live, rocket_learning))

    _require_terms(
        findings,
        section=rocket_all,
        terms=(
            "Inactive provisional hypotheses based on one Rocket Classic event",
            "Provisional one-event evidence and guidance",
            "not a permanent global engine rule",
            "not formula-v2.0.0 scoring rules",
        ),
        rule_id="GOV_ROCKET_PROVISIONAL",
        file=SCORING_SPEC,
        reason="Rocket governance must remain provisional, one-event, inactive evidence.",
    )
    _require_terms(
        findings,
        section=rocket_scoring,
        terms=(
            "They do not alter PrePenaltyRaw, PostPenaltyRaw, PostGateRaw, confidence, tiers, probabilities, badges, or ranks",
            "they activate no penalty or gate",
            "do not override penalty_gate_set_id: venuedna_v2_none",
        ),
        rule_id="GOV_ROCKET_NO_ACTIVE_EFFECT",
        file=SCORING_SPEC,
        reason="Rocket hypotheses must have no score, tier, rank, probability, confidence, badge, penalty, or gate effect.",
    )
    _require_terms(
        findings,
        section=rocket_all,
        terms=("at least three relevant or sufficiently similar events by default",),
        rule_id="GOV_ROCKET_MULTI_EVENT_THRESHOLD",
        file=SCORING_SPEC,
        reason="Rocket activation must require at least three relevant or sufficiently similar events by default.",
    )
    _require_terms(
        findings,
        section=rocket_all,
        terms=("Model Council approval",),
        rule_id="GOV_ROCKET_COUNCIL_APPROVAL",
        file=SCORING_SPEC,
        reason="Rocket activation must retain Model Council approval.",
    )
    _require_terms(
        findings,
        section=rocket_all,
        terms=("explicit operator authorization",),
        rule_id="GOV_ROCKET_OPERATOR_AUTHORIZATION",
        file=SCORING_SPEC,
        reason="Rocket activation must retain explicit operator authorization.",
    )

    normalized_rocket = _normalize_prose(rocket_all)
    prohibited = (
        "Permanent scoring rules derived from Rocket Classic 2026",
        "Apply globally",
        "These rules are permanent until superseded",
    )
    present = [phrase for phrase in prohibited if _normalize_prose(phrase) in normalized_rocket]
    if present:
        findings.append(
            _finding(
                "GOV_ROCKET_LEGACY_PERMANENT_LANGUAGE",
                SCORING_SPEC,
                "Rocket sections contain prohibited permanent/global language: "
                + ", ".join(repr(phrase) for phrase in present)
                + ".",
            )
        )

    overview = _extract_section(scoring, "1. OVERVIEW")
    divergence = _extract_section(scoring, "7.7 Production implementation divergence")
    history = _extract_section(scoring, "7.8 Cross-event comparability and historical records")
    _require_terms(
        findings,
        section=overview,
        terms=(
            "authoritative canonical target doctrine",
            "does not authorize production implementation",
            "reusable-engine migration requires separate operator authorization",
            "migration task is explicitly scoped",
        ),
        rule_id="GOV_DOCTRINE_TARGET_ONLY",
        file=SCORING_SPEC,
        reason="The overview must approve v2 as target doctrine without authorizing production implementation.",
    )
    _require_terms(
        findings,
        section=divergence,
        terms=(
            "approved canonical target doctrine",
            "this specification does not authorize that migration",
            "separately authorized migration",
        ),
        rule_id="GOV_MIGRATION_SEPARATE_AUTHORIZATION",
        file=SCORING_SPEC,
        reason="Reusable-engine migration must remain separately scoped and operator-authorized.",
    )
    _require_terms(
        findings,
        section=divergence,
        terms=(
            "is a Wyndham initialization blocker",
            "No event, artifact, payload, database, deploy, or scoring migration is authorized",
        ),
        rule_id="GOV_WYNDHAM_BLOCK",
        file=SCORING_SPEC,
        reason="Wyndham initialization must remain blocked until a separately authorized migration is complete.",
    )
    _require_terms(
        findings,
        section=history + "\n" + divergence,
        terms=(
            "Archived 3M enriched and Open v3 artifacts remain valid historical event records",
            "No event, artifact, payload, database, deploy, or scoring migration is authorized",
        ),
        rule_id="GOV_HISTORICAL_ARTIFACT_IMMUTABILITY",
        file=SCORING_SPEC,
        reason="Historical 3M and Open records must remain historical and must not be rewritten as v2-conforming artifacts.",
    )

    council_schema = _extract_section(
        texts[COUNCIL_GOVERNANCE], "6. SCHEMA MODIFICATION AUTHORITY"
    )
    _require_terms(
        findings,
        section=council_schema,
        terms=(
            "3 events at similar venue types",
            "Council proposal",
            "No schema change may be applied based on a single event's results",
        ),
        rule_id="GOV_COUNCIL_MULTI_EVENT_AUTHORITY",
        file=COUNCIL_GOVERNANCE,
        reason="Council schema authority must retain multi-event evidence and reject single-event changes.",
    )
    return findings


def _validate_active_event(repo_root: Path, text: str) -> list[Finding]:
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationConfigurationError(f"Invalid JSON in {ACTIVE_EVENT}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValidationConfigurationError(f"{ACTIVE_EVENT} must contain a JSON object")

    findings: list[Finding] = []
    if manifest.get("status") != "NO_ACTIVE_EVENT":
        findings.append(
            _finding(
                "ACTIVE_EVENT_STATUS",
                ACTIVE_EVENT,
                f"status must equal 'NO_ACTIVE_EVENT'; found {manifest.get('status')!r}.",
            )
        )

    missing_bindings = [
        key for key in NULL_EVENT_BINDINGS
        if key not in manifest
    ]
    if missing_bindings:
        findings.append(
            _finding(
                "ACTIVE_EVENT_BINDINGS_REQUIRED",
                ACTIVE_EVENT,
                "NO_ACTIVE_EVENT requires every event and venue binding key: "
                + ", ".join(missing_bindings)
                + ".",
            )
        )

    non_null_bindings = [
        key for key in NULL_EVENT_BINDINGS
        if key in manifest and manifest[key] is not None
    ]
    if non_null_bindings:
        findings.append(
            _finding(
                "ACTIVE_EVENT_BINDINGS_NULL",
                ACTIVE_EVENT,
                "NO_ACTIVE_EVENT requires null event and venue bindings: "
                + ", ".join(non_null_bindings)
                + ".",
            )
        )

    notes = manifest.get("notes")
    if not isinstance(notes, str) or "do not create event-bound projections or live artifacts" not in notes.casefold():
        findings.append(
            _finding(
                "ACTIVE_EVENT_BUILD_NOT_AUTHORIZED",
                ACTIVE_EVENT,
                "NO_ACTIVE_EVENT notes must state that event-bound projection and live builds are not authorized.",
            )
        )

    wyndham = repo_root / "events" / "2026_wyndham_championship"
    if wyndham.exists():
        findings.append(
            _finding(
                "ACTIVE_EVENT_WYNDHAM_ABSENT",
                "events/2026_wyndham_championship",
                "Wyndham event directory must not exist during the doctrine-only phase.",
            )
        )
    return findings


def validate_repository(
    repo_root: Path,
    *,
    strict: bool = False,
) -> ValidationReport:
    """Validate a repository without importing production code or writing files."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValidationConfigurationError(f"Repository root does not exist: {root}")

    texts = {relative: _read_required(root, relative) for relative in REQUIRED_FILES}
    marker, findings = _parse_marker_text(texts[SCORING_SPEC], strict=strict)
    if marker:
        findings.extend(_validate_diagnostics(root, marker))
    findings.extend(_validate_governance(texts))
    findings.extend(_validate_active_event(root, texts[ACTIVE_EVENT]))
    return ValidationReport(findings=_sorted_findings(findings))


def _json_payload(report: ValidationReport, *, strict: bool) -> dict[str, Any]:
    return {
        "status": "fail" if report.errors else "pass",
        "strict": strict,
        "findings": [asdict(finding) for finding in report.findings],
    }


def _print_text(report: ValidationReport) -> None:
    for finding in report.findings:
        print(
            f"[{finding.severity}] {finding.rule_id} {finding.file}: {finding.reason}"
        )
    if report.errors:
        print(f"SCORING DOCTRINE FAILED ({len(report.errors)} errors)")
    elif report.findings:
        print(f"SCORING DOCTRINE PASSED ({len(report.findings)} warnings)")
    else:
        print("SCORING DOCTRINE PASSED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Default: parent directory of tools/.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat unknown marker keys as doctrine contract errors.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[1]
    )
    try:
        report = validate_repository(repo_root, strict=args.strict)
    except (ValidationConfigurationError, OSError, ValueError) as exc:
        if args.format == "json":
            print(json.dumps({"status": "error", "strict": args.strict, "error": str(exc)}, sort_keys=True))
        else:
            print(f"SCORING DOCTRINE VALIDATOR ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(_json_payload(report, strict=args.strict), indent=2, sort_keys=True))
    else:
        _print_text(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
