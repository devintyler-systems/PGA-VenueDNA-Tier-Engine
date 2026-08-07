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
V2_IMPLEMENTATION = "engine/venuedna_scoring.py"
PRODUCER_IMPLEMENTATION = "engine/enrich_cards.py"
ACTIVE_EVENT = "config/active_event.json"

REQUIRED_FILES = (
    SCORING_SPEC,
    LEARNING_LOOP,
    ARTIFACT_SCHEMA,
    COUNCIL_GOVERNANCE,
    DIAGNOSTIC_SOURCE,
    V2_IMPLEMENTATION,
    ACTIVE_EVENT,
)

MARKER_NAME = "scoring-doctrine-v2"
MARKER_PATTERN = re.compile(
    r"<!--\s*scoring-doctrine-v2(?P<body>.*?)-->", re.DOTALL
)
MARKER_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SCORING_SPEC_VERSION_PATTERN = re.compile(
    r"^\*\*Version:\*\*\s*(?P<version>\S+)\s*$", re.MULTILINE
)

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

# Phase 6.1: the sole authorized Wyndham retrospective-development fixture.
# This is a hardcoded exact-path exception, not a generic fixture-mode
# bypass -- see docs/decisions/2026_08_06_wyndham_retrospective_fixture_authorization.md.
RETROSPECTIVE_FIXTURE_EVENT_ROOT = "events/2026_wyndham_championship"
RETROSPECTIVE_FIXTURE_README = "RETROSPECTIVE_FIXTURE_README.md"
RETROSPECTIVE_FIXTURE_MARKERS = (
    "RETROSPECTIVE_DEVELOPMENT_FIXTURE",
    "NOT OFFICIAL",
    "NOT PRE_EVENT",
    "NOT LIVE",
    "NOT DEPLOYABLE",
)
RETROSPECTIVE_FIXTURE_APPROVED_ENTRIES = frozenset(
    {RETROSPECTIVE_FIXTURE_README, "input", "output", "audit", "deploy"}
)
RETROSPECTIVE_FIXTURE_SUCCESS_RULE = "RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED"

# Phase 6.3: the exact fenced retrospective board-shell allowance. Only these
# three local, non-deployable board-shell assets may exist as direct children
# of deploy/ alongside the required empty data/ directory. This does not
# authorize a deploy payload, official artifact, or any other file or
# subdirectory -- see
# docs/decisions/2026_08_06_wyndham_retrospective_fixture_authorization.md.
RETROSPECTIVE_FIXTURE_BOARD_SHELL_FILES = frozenset(
    {"index.html", "app.js", "styles.css"}
)
RETROSPECTIVE_FIXTURE_APPROVED_DEPLOY_ENTRIES = (
    RETROSPECTIVE_FIXTURE_BOARD_SHELL_FILES | frozenset({"data"})
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


def _scoring_spec_version(text: str) -> str:
    """Return the single version declared by the canonical scoring spec."""
    matches = SCORING_SPEC_VERSION_PATTERN.findall(text)
    if len(matches) != 1:
        raise ValidationConfigurationError(
            f"Expected exactly one scoring-spec Version declaration in {SCORING_SPEC}; "
            f"found {len(matches)}."
        )
    return matches[0]


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
    file: str = DIAGNOSTIC_SOURCE,
) -> None:
    actual = literals.get(name, object())
    if actual != expected:
        rendered = "missing" if name not in literals else repr(actual)
        findings.append(
            _finding(
                rule_id,
                file,
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


def _validate_v2_implementation(
    repo_root: Path, marker: dict[str, str], scoring_spec_version: str
) -> list[Finding]:
    """Statically validate engine/venuedna_scoring.py -- the pure canonical
    v2.0.0 reference implementation -- against the same doctrine marker
    that governs the historical-parity diagnostic layer. Never imports the
    module; reads only its top-level literal assignments via AST.
    """
    try:
        literals = extract_python_literals(repo_root / V2_IMPLEMENTATION)
    except ValueError as exc:
        raise ValidationConfigurationError(str(exc)) from exc

    findings: list[Finding] = []
    _expect_literal(
        findings, literals, "FORMULA_ID", marker.get("formula_id"),
        "V2IMPL_FORMULA_ID", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "FORMULA_VERSION", marker.get("formula_version"),
        "V2IMPL_FORMULA_VERSION", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "COMPARABLE_SCORE_FAMILY", marker.get("comparable_score_family"),
        "V2IMPL_COMPARABLE_FAMILY", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "PENALTY_GATE_SET_ID", marker.get("penalty_gate_set_id"),
        "V2IMPL_PENALTY_GATE_SET", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "SCORING_SPEC_VERSION", scoring_spec_version,
        "V2IMPL_SCORING_SPEC_VERSION", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "CORE_INPUTS", EXPECTED_CORE_INPUTS,
        "V2IMPL_CORE_INPUTS", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "EXCLUDED_LEGACY_NONCORE_ADDENDS", EXPECTED_EXCLUDED_ADDENDS,
        "V2IMPL_EXCLUDED_ADDENDS", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "ACTIVE_PENALTY_IDS", (),
        "V2IMPL_ACTIVE_PENALTIES", file=V2_IMPLEMENTATION,
    )
    _expect_literal(
        findings, literals, "ACTIVE_GATE_IDS", (),
        "V2IMPL_ACTIVE_GATES", file=V2_IMPLEMENTATION,
    )

    core = tuple(literals.get("CORE_INPUTS", ()))
    excluded = tuple(literals.get("EXCLUDED_LEGACY_NONCORE_ADDENDS", ()))
    overlap = sorted(set(core) & set(excluded))
    if overlap:
        findings.append(
            _finding(
                "V2IMPL_COMPONENT_OVERLAP",
                V2_IMPLEMENTATION,
                "Canonical core inputs and excluded legacy addends overlap: "
                + ", ".join(overlap)
                + ".",
            )
        )

    return findings


def _producer_main_ast(path: Path) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Parse and locate the root producer entry point without importing it."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ValueError(f"Cannot statically parse {path}: {exc}") from exc
    main_node = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"),
        None,
    )
    if main_node is None:
        raise ValueError(f"Cannot find main() in {path}")
    return main_node


def _producer_module_ast(path: Path) -> ast.Module:
    """Parse the producer module once for finite helper and main boundaries."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ValueError(f"Cannot statically parse {path}: {exc}") from exc


def _named_top_level_function(
    module: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        ),
        None,
    )


def _main_called_names(main_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return call names in ``main`` without importing production code."""
    calls: set[str] = set()
    for node in ast.walk(main_node):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    return calls


def _subscript_key(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Subscript):
        return None
    slice_node = node.slice
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value
    return None


def _is_name(node: ast.AST, expected: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected


def _contains_name(node: ast.AST, expected: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == expected for child in ast.walk(node))


def _has_name_assignment(main_node: ast.AST, name: str, predicate) -> bool:
    for node in ast.walk(main_node):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if any(_is_name(target, name) for target in targets) and predicate(node.value):
            return True
    return False


def _is_post_gate_projection_entry(node: ast.AST) -> bool:
    if not isinstance(node, ast.Dict):
        return False
    captured: set[str] = set()
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and key.value in {"post_gate_raw", "_post_gate_raw"}:
            if (
                isinstance(value, ast.Attribute)
                and _is_name(value.value, "projection")
                and value.attr == "post_gate_raw"
            ):
                captured.add(key.value)
    return captured == {"post_gate_raw", "_post_gate_raw"}


def _is_scored_player_pool(node: ast.AST) -> bool:
    if not isinstance(node, ast.ListComp) or len(node.generators) != 1:
        return False
    generator = node.generators[0]
    if not (_is_name(node.elt, "p") and _is_name(generator.target, "p") and _is_name(generator.iter, "players_raw")):
        return False
    if len(generator.ifs) != 1:
        return False
    condition = generator.ifs[0]
    return (
        isinstance(condition, ast.Compare)
        and len(condition.ops) == 1
        and isinstance(condition.ops[0], ast.IsNot)
        and len(condition.comparators) == 1
        and isinstance(condition.comparators[0], ast.Constant)
        and condition.comparators[0].value is None
        and isinstance(condition.left, ast.Subscript)
        and _is_name(condition.left.value, "p")
        and _subscript_key(condition.left) == "_post_gate_raw"
    )


def _is_canonical_raw_pool(node: ast.AST) -> bool:
    if not isinstance(node, ast.ListComp) or len(node.generators) != 1:
        return False
    generator = node.generators[0]
    return (
        isinstance(node.elt, ast.Subscript)
        and _is_name(node.elt.value, "p")
        and _subscript_key(node.elt) == "_post_gate_raw"
        and _is_name(generator.target, "p")
        and _is_name(generator.iter, "scored_players")
        and not generator.ifs
    )


def _is_named_call(node: ast.AST, function_name: str, argument_name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_name(node.func, function_name)
        and len(node.args) >= 1
        and _is_name(node.args[0], argument_name)
    )


def _has_subscript_assignment(main_node: ast.AST, key: str, predicate) -> bool:
    for node in ast.walk(main_node):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Subscript) and _subscript_key(target) == key and predicate(node.value):
                return True
    return False


OFFICIAL_PROBABILITY_FIELDS = (
    "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct", "missCutPct",
)
OFFICIAL_OUTPUT_FIELDS = ("vts_final", *OFFICIAL_PROBABILITY_FIELDS, "rank", "tier")


@dataclass(frozen=True)
class _ProducerWrite:
    """One statically observable write to an official player-record field."""

    field: str
    node: ast.AST
    value: ast.AST | None
    form: str

    @property
    def source_order(self) -> tuple[int, int]:
        return (getattr(self.node, "lineno", -1), getattr(self.node, "col_offset", -1))


def _main_ast_nodes(main_node: ast.AST) -> Iterable[ast.AST]:
    """Yield main-body nodes in source order without descending into helpers."""
    def visit(node: ast.AST) -> Iterable[ast.AST]:
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            yield from visit(child)

    yield from visit(main_node)


def _parent_map(main_node: ast.AST) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for parent in _main_ast_nodes(main_node):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    return parents


def _is_scored_index_test(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.IsNot)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value is None
        and _is_name(node.left, "scored_index")
    )


def _is_in_scored_branch(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    child = node
    while parent := parents.get(id(child)):
        if isinstance(parent, ast.If) and _is_scored_index_test(parent.test):
            return any(item is child for item in parent.body)
        child = parent
    return False


def _is_in_unscored_branch(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    child = node
    while parent := parents.get(id(child)):
        if isinstance(parent, ast.If) and _is_scored_index_test(parent.test):
            return any(item is child for item in parent.orelse)
        if (
            isinstance(parent, ast.For)
            and _is_name(parent.target, "p")
            and _is_name(parent.iter, "unscored_players")
        ):
            return True
        child = parent
    return False


def _is_probability_loop(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    child = node
    while parent := parents.get(id(child)):
        if not isinstance(parent, ast.For):
            child = parent
            continue
        target = parent.target
        is_key_value_target = (
            isinstance(target, ast.Tuple)
            and len(target.elts) == 2
            and _is_name(target.elts[0], "key")
            and _is_name(target.elts[1], "value")
        )
        is_probs_items = (
            isinstance(parent.iter, ast.Call)
            and isinstance(parent.iter.func, ast.Attribute)
            and _is_name(parent.iter.func.value, "probs")
            and parent.iter.func.attr == "items"
        )
        if is_key_value_target and is_probs_items:
            return True
        child = parent
    return False


def _is_scored_rank_loop(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    child = node
    while parent := parents.get(id(child)):
        if isinstance(parent, ast.For):
            target = parent.target
            is_i_p_target = (
                isinstance(target, ast.Tuple)
                and len(target.elts) == 2
                and _is_name(target.elts[0], "i")
                and _is_name(target.elts[1], "p")
            )
            is_scored_enumerate = (
                isinstance(parent.iter, ast.Call)
                and _is_name(parent.iter.func, "enumerate")
                and len(parent.iter.args) == 2
                and _is_name(parent.iter.args[0], "scored_players")
                and isinstance(parent.iter.args[1], ast.Constant)
                and parent.iter.args[1].value == 1
            )
            if is_i_p_target and is_scored_enumerate:
                return True
        child = parent
    return False


def _unscored_probability_default_fields(
    node: ast.AST,
    parents: dict[int, ast.AST],
) -> tuple[str, ...]:
    """Return the literal probability keys in the approved unscored-null loop."""
    if not _is_in_unscored_branch(node, parents):
        return ()
    child = node
    while parent := parents.get(id(child)):
        if isinstance(parent, ast.For) and _is_name(parent.target, "key") and isinstance(parent.iter, ast.Tuple):
            fields = tuple(
                element.value
                for element in parent.iter.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
            if fields == OFFICIAL_PROBABILITY_FIELDS:
                return fields
        child = parent
    return ()


def _p_subscript_field(target: ast.AST) -> str | None:
    if not isinstance(target, ast.Subscript) or not _is_name(target.value, "p"):
        return None
    return _subscript_key(target)


def _is_none(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _is_round_of_name(value: ast.AST | None, name: str) -> bool:
    return (
        isinstance(value, ast.Call)
        and _is_name(value.func, "round")
        and bool(value.args)
        and _is_name(value.args[0], name)
    )


def _is_canonical_vts_binding(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_name(node.func, "round")
        and bool(node.args)
        and isinstance(node.args[0], ast.Subscript)
        and _is_name(node.args[0].value, "vts_scaled")
        and _is_name(node.args[0].slice, "scored_index")
    )


def _is_canonical_probs_binding(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and _is_name(node.value, "canonical_probabilities")
        and _is_name(node.slice, "scored_index")
    )


def _has_scored_name_assignment(
    main_node: ast.AST,
    parents: dict[int, ast.AST],
    name: str,
    predicate,
) -> bool:
    for node in _main_ast_nodes(main_node):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if _is_in_scored_branch(node, parents) and any(_is_name(target, name) for target in targets):
            if predicate(node.value):
                return True
    return False


def _append_dynamic_writes(writes: list[_ProducerWrite], node: ast.AST, form: str) -> None:
    writes.extend(_ProducerWrite(field, node, None, form) for field in OFFICIAL_OUTPUT_FIELDS)


def _collect_official_writes(main_node: ast.AST) -> list[_ProducerWrite]:
    """Collect only the concrete record-mutation patterns this producer permits."""
    writes: list[_ProducerWrite] = []
    parents = _parent_map(main_node)
    for node in _main_ast_nodes(main_node):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            value = node.value if not isinstance(node, ast.AugAssign) else None
            for target in targets:
                field = _p_subscript_field(target)
                if field in OFFICIAL_OUTPUT_FIELDS:
                    writes.append(_ProducerWrite(field, node, value, "subscript"))
                elif (
                    isinstance(target, ast.Subscript)
                    and _is_name(target.value, "p")
                    and _subscript_key(target) is None
                ):
                    if _is_probability_loop(node, parents):
                        writes.extend(
                            _ProducerWrite(field, node, value, "probability_loop")
                            for field in OFFICIAL_PROBABILITY_FIELDS
                        )
                    elif fields := _unscored_probability_default_fields(node, parents):
                        writes.extend(
                            _ProducerWrite(field, node, value, "probability_default_loop")
                            for field in fields
                        )
                    else:
                        _append_dynamic_writes(writes, node, "dynamic_subscript")
            continue
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not _is_name(node.func.value, "p"):
            continue
        if node.func.attr == "__setitem__":
            if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                if node.args[0].value in OFFICIAL_OUTPUT_FIELDS:
                    writes.append(_ProducerWrite(node.args[0].value, node, node.args[1], "setitem"))
            else:
                _append_dynamic_writes(writes, node, "dynamic_setitem")
        elif node.func.attr == "update":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Dict) and not node.keywords:
                for key, value in zip(node.args[0].keys, node.args[0].values):
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        if key.value in OFFICIAL_OUTPUT_FIELDS:
                            writes.append(_ProducerWrite(key.value, node, value, "update"))
                    else:
                        _append_dynamic_writes(writes, node, "dynamic_update")
            elif not node.args and all(keyword.arg is not None for keyword in node.keywords):
                for keyword in node.keywords:
                    if keyword.arg in OFFICIAL_OUTPUT_FIELDS:
                        writes.append(_ProducerWrite(keyword.arg, node, keyword.value, "update"))
            else:
                _append_dynamic_writes(writes, node, "dynamic_update")
    return sorted(writes, key=lambda write: write.source_order)


def _canonical_sort_lineno(main_node: ast.AST) -> int | None:
    for node in _main_ast_nodes(main_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not (_is_name(node.func.value, "scored_players") and node.func.attr == "sort"):
            continue
        key = next((keyword.value for keyword in node.keywords if keyword.arg == "key"), None)
        reverse = next((keyword.value for keyword in node.keywords if keyword.arg == "reverse"), None)
        if (
            isinstance(key, ast.Lambda)
            and isinstance(key.body, ast.Subscript)
            and _is_name(key.body.value, "p")
            and _subscript_key(key.body) == "vts_final"
            and isinstance(reverse, ast.Constant)
            and reverse.value is True
        ):
            return node.lineno
    return None


def _ordered_records_lineno(main_node: ast.AST) -> int | None:
    for node in _main_ast_nodes(main_node):
        if not isinstance(node, ast.Assign) or not any(_is_name(target, "ordered") for target in node.targets):
            continue
        if isinstance(node.value, ast.ListComp) and _is_name(node.value.generators[0].iter, "players_raw"):
            return node.lineno
    return None


def _writer_rule_id(field: str, suffix: str) -> str:
    if field == "vts_final":
        boundary = "OFFICIAL_SCORE"
    elif field in OFFICIAL_PROBABILITY_FIELDS:
        boundary = "PROBABILITY"
    else:
        boundary = field.upper()
    return f"V2PROD_{boundary}_{suffix}"


def _validate_terminal_official_writers(main_node: ast.AST) -> list[Finding]:
    """Prove the narrow approved writer pattern remains exclusive and terminal."""
    parents = _parent_map(main_node)
    writes = _collect_official_writes(main_node)
    sort_lineno = _canonical_sort_lineno(main_node)
    ordered_lineno = _ordered_records_lineno(main_node)
    findings: list[Finding] = []

    if sort_lineno is None:
        findings.append(_finding(
            "V2PROD_RANK_TIER_DATAFLOW", PRODUCER_IMPLEMENTATION,
            "rank and tier must sort canonical vts_final before canonical assignment.",
        ))
    if ordered_lineno is None:
        findings.append(_finding(
            "V2PROD_OUTPUT_SERIALIZATION", PRODUCER_IMPLEMENTATION,
            "official records must be assembled from players_raw before JSON serialization.",
        ))

    for field in OFFICIAL_OUTPUT_FIELDS:
        field_writes = [write for write in writes if write.field == field]
        canonical: list[_ProducerWrite] = []
        classified: list[tuple[_ProducerWrite, str]] = []
        for write in field_writes:
            is_canonical = (
                write.form in {"subscript", "probability_loop"}
                and (
                    (field == "vts_final" and _is_name(write.value, "vts") and _is_in_scored_branch(write.node, parents))
                    or (
                        field in OFFICIAL_PROBABILITY_FIELDS
                        and _is_round_of_name(write.value, "value")
                        and _is_probability_loop(write.node, parents)
                        and _is_in_scored_branch(write.node, parents)
                    )
                    or (field == "rank" and _is_name(write.value, "i") and _is_scored_rank_loop(write.node, parents))
                    or (
                        field == "tier"
                        and isinstance(write.value, ast.Call)
                        and _is_name(write.value.func, "canonical_assign_tier")
                        and bool(write.value.args)
                        and _is_name(write.value.args[0], "i")
                        and _is_scored_rank_loop(write.node, parents)
                    )
                )
            )
            if is_canonical:
                canonical.append(write)
                classified.append((write, "canonical"))
                continue
            if write.form.startswith("dynamic"):
                classified.append((write, "ambiguous"))
                continue
            if _is_none(write.value) and _is_in_unscored_branch(write.node, parents):
                classified.append((write, "unscored_default"))
                continue
            classified.append((write, "candidate_default" if _is_none(write.value) else "competing"))

        canonical_orders = {write.source_order for write in canonical}
        for index, (write, category) in enumerate(classified):
            if category != "candidate_default":
                continue
            later_canonical = any(order > write.source_order for order in canonical_orders)
            classified[index] = (write, "initial_default" if later_canonical else "competing")

        for write, category in classified:
            if category == "ambiguous":
                findings.append(_finding(
                    "V2PROD_AMBIGUOUS_OUTPUT_UPDATE", PRODUCER_IMPLEMENTATION,
                    f"{field} may be overwritten by an unprovable dynamic player-record mutation at line {write.source_order[0]}.",
                ))
            elif category == "competing":
                findings.append(_finding(
                    _writer_rule_id(field, "COMPETING_WRITER"), PRODUCER_IMPLEMENTATION,
                    f"{field} has an unauthorized competing writer at line {write.source_order[0]}.",
                ))

        if len(canonical) != 1:
            findings.append(_finding(
                _writer_rule_id(field, "NOT_TERMINAL"), PRODUCER_IMPLEMENTATION,
                f"{field} requires exactly one approved canonical final writer; found {len(canonical)}.",
            ))
            continue

        writer = canonical[0]
        invalid_order = (
            ordered_lineno is None
            or writer.source_order[0] >= ordered_lineno
            or (field == "vts_final" and (sort_lineno is None or writer.source_order[0] >= sort_lineno))
            or (field in {"rank", "tier"} and (sort_lineno is None or writer.source_order[0] <= sort_lineno))
        )
        if invalid_order:
            findings.append(_finding(
                _writer_rule_id(field, "NOT_TERMINAL"), PRODUCER_IMPLEMENTATION,
                f"{field} canonical writer must be terminal in its approved phase before record serialization.",
            ))
    return findings


CANONICAL_FINALIZER = "finalize_canonical_official_records"
TRACKED_FINALIZER_NAMES = (
    "scored_players",
    "canonical_raw_scores",
    "normalized_scores",
    "probability_vectors",
    "canonical_vts",
    "probabilities",
    "pre_rank_records",
    "ordered_scored_records",
    "final_records",
    "ordered_records",
)
OFFICIAL_OUTPUT_FIELDS = (
    "vts_final", "winPct", "top5Pct", "top10Pct", "top20Pct", "makeCutPct",
    "missCutPct", "rank", "tier",
)
_MUTATING_METHODS = {
    "update", "sort", "reverse", "append", "extend", "insert", "clear", "pop",
    "__setitem__",
}
_FINALIZER_PROTECTED_OBJECTS = frozenset((*TRACKED_FINALIZER_NAMES, "record"))
_FINALIZER_ALLOWED_METHODS = frozenset({
    ("scored_index_by_dg_id", "get"),
    ("probability_vectors", "items"),
    ("record", "get"),
    ("pre_rank_records", "append"),
})


def _function_nodes(function: ast.AST) -> Iterable[ast.AST]:
    """Traverse one function boundary without following nested helper bodies."""
    def visit(node: ast.AST) -> Iterable[ast.AST]:
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            yield from visit(child)

    yield from visit(function)


def _name_assignments(function: ast.AST, name: str) -> list[ast.AST]:
    assignments: list[ast.AST] = []
    for node in _function_nodes(function):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            if any(_is_name(target, name) for target in targets):
                assignments.append(node)
        elif isinstance(node, ast.AugAssign) and _is_name(node.target, name):
            assignments.append(node)
    return assignments


def _subscript_root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Subscript):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _receiver_root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return _subscript_root_name(node)


def _protected_alias_source(
    value: ast.AST,
    aliases: dict[str, str],
    protected_roots: dict[str, str],
    *,
    allow_payload_players: bool,
) -> str | None:
    """Recognize only the finite direct alias forms approved by this contract."""
    if isinstance(value, ast.Name):
        return aliases.get(value.id) or protected_roots.get(value.id)
    if (
        allow_payload_players
        and isinstance(value, ast.Subscript)
        and isinstance(value.value, ast.Name)
        and _subscript_key(value) == "players"
    ):
        base_root = aliases.get(value.value.id) or protected_roots.get(value.value.id)
        if base_root == "payload":
            return 'payload["players"]'
    return None


def _protected_alias_findings(
    function: ast.AST,
    *,
    protected_roots: dict[str, str],
    function_name: str,
    allow_payload_players: bool = False,
) -> list[Finding]:
    """Fail closed on direct local aliases of protected mutable objects.

    This is deliberately limited to simple name assignments and the one
    approved payload-player subscript.  It neither follows calls nor infers
    aliases through arbitrary expressions, containers, or attributes.
    """
    aliases: dict[str, str] = {}
    findings: list[Finding] = []
    ordered_nodes = sorted(_function_nodes(function), key=lambda node: (getattr(node, "lineno", -1), getattr(node, "col_offset", -1)))

    for node in ordered_nodes:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        alias_name = targets[0].id
        source_root = _protected_alias_source(
            node.value, aliases, protected_roots,
            allow_payload_players=allow_payload_players,
        )
        if alias_name in aliases:
            findings.append(_finding(
                "V2PROD_PROTECTED_ALIAS_REBIND", PRODUCER_IMPLEMENTATION,
                f"{function_name} must not rebind protected alias {alias_name} for {aliases[alias_name]}.",
            ))
            continue
        if source_root is not None and alias_name not in protected_roots:
            aliases[alias_name] = source_root

    for node in ordered_nodes:
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id in aliases:
            findings.append(_finding(
                "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                f"{function_name} must not mutate protected alias {node.target.id} for {aliases[node.target.id]} through augmented assignment.",
            ))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            for target in targets:
                if isinstance(target, ast.Subscript) and (root := _subscript_root_name(target)) in aliases:
                    findings.append(_finding(
                        "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                        f"{function_name} must not mutate protected alias {root} for {aliases[root]} through subscript assignment.",
                    ))
                elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in aliases:
                    alias_name = target.value.id
                    findings.append(_finding(
                        "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                        f"{function_name} must not mutate protected alias {alias_name} for {aliases[alias_name]} through attribute assignment.",
                    ))
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript) and (root := _subscript_root_name(target)) in aliases:
                    findings.append(_finding(
                        "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                        f"{function_name} must not delete through protected alias {root} for {aliases[root]}.",
                    ))
                elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in aliases:
                    alias_name = target.value.id
                    findings.append(_finding(
                        "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                        f"{function_name} must not delete through protected alias {alias_name} for {aliases[alias_name]}.",
                    ))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            alias_name = _receiver_root_name(node.func.value)
            if alias_name in aliases:
                findings.append(_finding(
                    "V2PROD_PROTECTED_ALIAS_MUTATION", PRODUCER_IMPLEMENTATION,
                    f"{function_name} must not call {node.func.attr}() through protected alias {alias_name} for {aliases[alias_name]}.",
                ))
    return findings


def _dict_value(node: ast.AST, key_name: str) -> ast.AST | None:
    if not isinstance(node, ast.Dict):
        return None
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and key.value == key_name:
            return value
    return None


def _has_assignment(function: ast.AST, name: str, predicate) -> bool:
    return any(
        predicate(node.value)
        for node in _name_assignments(function, name)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    )


def _is_finalizer_scored_pool(value: ast.AST) -> bool:
    if not isinstance(value, ast.ListComp) or len(value.generators) != 1:
        return False
    generator = value.generators[0]
    if not (_is_name(value.elt, "record") and _is_name(generator.target, "record") and _is_name(generator.iter, "prepared_records")):
        return False
    if len(generator.ifs) != 1 or not isinstance(generator.ifs[0], ast.Compare):
        return False
    condition = generator.ifs[0]
    return (
        isinstance(condition.left, ast.Subscript)
        and _is_name(condition.left.value, "record")
        and _subscript_key(condition.left) == "post_gate_raw"
        and len(condition.ops) == 1
        and isinstance(condition.ops[0], ast.IsNot)
        and len(condition.comparators) == 1
        and isinstance(condition.comparators[0], ast.Constant)
        and condition.comparators[0].value is None
    )


def _is_finalizer_raw_pool(value: ast.AST) -> bool:
    if not isinstance(value, ast.ListComp) or len(value.generators) != 1:
        return False
    generator = value.generators[0]
    return (
        isinstance(value.elt, ast.Subscript)
        and _is_name(value.elt.value, "record")
        and _subscript_key(value.elt) == "post_gate_raw"
        and _is_name(generator.target, "record")
        and _is_name(generator.iter, "scored_players")
        and not generator.ifs
    )


def _is_canonical_vts(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Call)
        and _is_name(value.func, "round")
        and bool(value.args)
        and isinstance(value.args[0], ast.Subscript)
        and _is_name(value.args[0].value, "normalized_scores")
        and _is_name(value.args[0].slice, "scored_index")
    )


def _is_probability_projection(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.DictComp)
        and isinstance(value.value, ast.Call)
        and _is_name(value.value.func, "round")
        and bool(value.value.args)
        and _is_name(value.value.args[0], "value")
        and len(value.generators) == 1
        and isinstance(value.generators[0].iter, ast.Call)
        and isinstance(value.generators[0].iter.func, ast.Attribute)
        and value.generators[0].iter.func.attr == "items"
        and isinstance(value.generators[0].iter.func.value, ast.Subscript)
        and _is_name(value.generators[0].iter.func.value.value, "probability_vectors")
        and _is_name(value.generators[0].iter.func.value.slice, "scored_index")
    )


def _has_canonical_score_and_probability_record(function: ast.AST) -> bool:
    for node in _function_nodes(function):
        if not isinstance(node, ast.Dict):
            continue
        if not _is_name(_dict_value(node, "vts_final"), "canonical_vts"):
            continue
        if any(key is None and _is_name(value, "probabilities") for key, value in zip(node.keys, node.values)):
            return True
    return False


def _is_finalizer_sort(value: ast.AST) -> bool:
    if not (isinstance(value, ast.Call) and _is_name(value.func, "sorted") and value.args):
        return False
    key = next((keyword.value for keyword in value.keywords if keyword.arg == "key"), None)
    reverse = next((keyword.value for keyword in value.keywords if keyword.arg == "reverse"), None)
    return (
        isinstance(key, ast.Lambda)
        and isinstance(key.body, ast.Subscript)
        and _is_name(key.body.value, "record")
        and _subscript_key(key.body) == "vts_final"
        and isinstance(reverse, ast.Constant)
        and reverse.value is True
    )


def _has_canonical_rank_and_tier(function: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Dict)
        and _is_name(_dict_value(node, "rank"), "rank")
        and isinstance(_dict_value(node, "tier"), ast.Call)
        and _is_name(_dict_value(node, "tier").func, "canonical_assign_tier")
        for node in _function_nodes(function)
    )


def _finalizer_mutation_rule(function: ast.AST) -> str | None:
    """Return the narrow failure class for an unapproved finalizer mutation."""
    for node in _function_nodes(function):
        if isinstance(node, ast.AugAssign):
            return "V2PROD_FINALIZER_MUTATION"
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.target if isinstance(node, ast.AnnAssign) else node.targets[0], ast.Subscript):
            target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0]
            root = _subscript_root_name(target)
            key = _subscript_key(target)
            # The finalizer must assemble official fields once in its approved
            # dictionary expression.  A subscript write to any protected key is
            # therefore a competing writer regardless of the local alias used.
            if key in OFFICIAL_OUTPUT_FIELDS:
                return "V2PROD_FINALIZER_MUTATION"
            if root in {
                "probabilities", "probs", "probability_vectors", "final_records",
                "ordered_records", "ordered", "records",
            }:
                return "V2PROD_FINALIZER_MUTATION"
            if root == "record" and key in OFFICIAL_OUTPUT_FIELDS:
                return "V2PROD_FINALIZER_MUTATION"
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        root = _receiver_root_name(node.func.value)
        if (root, node.func.attr) in _FINALIZER_ALLOWED_METHODS:
            continue
        if _is_name(node.func.value, "archetype_tags") and node.func.attr == "append":
            continue
        if node.func.attr in _MUTATING_METHODS:
            return "V2PROD_FINALIZER_MUTATION"
        if root in _FINALIZER_PROTECTED_OBJECTS:
            return "V2PROD_UNKNOWN_MUTATOR"
    return None


def _validate_finalizer(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_protected_alias_findings(
        function,
        protected_roots={name: name for name in _FINALIZER_PROTECTED_OBJECTS},
        function_name=CANONICAL_FINALIZER,
    ))
    for name in TRACKED_FINALIZER_NAMES:
        assignments = _name_assignments(function, name)
        if len(assignments) != 1 or any(isinstance(node, ast.AugAssign) for node in assignments):
            findings.append(_finding(
                "V2PROD_PROBABILITY_REBIND" if name == "probabilities" else "V2PROD_FINALIZER_INTERMEDIATE_REBIND",
                PRODUCER_IMPLEMENTATION,
                f"{CANONICAL_FINALIZER} must assign canonical probabilities exactly once without rebinding."
                if name == "probabilities"
                else f"{CANONICAL_FINALIZER} must assign tracked {name} exactly once without augmented assignment.",
            ))

    required_assignments = (
        ("scored_players", _is_finalizer_scored_pool, "V2PROD_FINALIZER_SCORED_POOL"),
        ("canonical_raw_scores", _is_finalizer_raw_pool, "V2PROD_FINALIZER_RAW_POOL"),
        ("normalized_scores", lambda value: _is_named_call(value, "canonical_z_score_scale", "canonical_raw_scores"), "V2PROD_FINALIZER_NORMALIZATION"),
        ("probability_vectors", lambda value: _is_named_call(value, "canonical_compute_probability_vectors", "canonical_raw_scores"), "V2PROD_FINALIZER_PROBABILITIES"),
        ("canonical_vts", _is_canonical_vts, "V2PROD_FINALIZER_OFFICIAL_SCORE"),
        ("probabilities", _is_probability_projection, "V2PROD_FINALIZER_OFFICIAL_PROBABILITIES"),
    )
    for name, predicate, rule_id in required_assignments:
        if not _has_assignment(function, name, predicate):
            findings.append(_finding(
                rule_id, PRODUCER_IMPLEMENTATION,
                f"{CANONICAL_FINALIZER} must preserve the approved canonical {name} assignment.",
            ))
    if not _has_canonical_score_and_probability_record(function):
        findings.append(_finding(
            "V2PROD_FINALIZER_OFFICIAL_OUTPUT", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must assemble official score and probabilities from canonical_vts and probabilities.",
        ))

    calls = _main_called_names(function)
    prohibited = {
        "combine_raw_score": "V2PROD_LEGACY_RAW_SCORE",
        "apply_gates": "V2PROD_LEGACY_GATES",
        "tempered_softmax": "V2PROD_LEGACY_PROBABILITIES",
    }
    for call, rule_id in prohibited.items():
        if call in calls:
            findings.append(_finding(
                rule_id, PRODUCER_IMPLEMENTATION,
                f"{CANONICAL_FINALIZER} must not invoke historical {call}.",
            ))
    if "canonical_assign_tier" not in calls:
        findings.append(_finding(
            "V2PROD_FINALIZER_TIER", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must assign tier through canonical_assign_tier.",
        ))
    if not _has_assignment(function, "ordered_scored_records", _is_finalizer_sort):
        findings.append(_finding(
            "V2PROD_FINALIZER_SORT", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must construct canonical score ordering with sorted().",
        ))
    if not _has_assignment(function, "final_records", lambda value: isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)):
        findings.append(_finding(
            "V2PROD_FINALIZER_RANK", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must assemble ranked and unscored final records together.",
        ))
    elif not _has_canonical_rank_and_tier(function):
        findings.append(_finding(
            "V2PROD_FINALIZER_TIER", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must derive tier from canonical rank during final assembly.",
        ))
    if not any(isinstance(node, ast.Return) and _is_name(node.value, "ordered_records") for node in _function_nodes(function)):
        findings.append(_finding(
            "V2PROD_FINALIZER_RETURN", PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} must return ordered_records directly.",
        ))
    mutation_rule = _finalizer_mutation_rule(function)
    if mutation_rule:
        findings.append(_finding(
            mutation_rule, PRODUCER_IMPLEMENTATION,
            f"{CANONICAL_FINALIZER} contains an unknown protected-object method call."
            if mutation_rule == "V2PROD_UNKNOWN_MUTATOR"
            else f"{CANONICAL_FINALIZER} contains an unapproved mutable finalization operation.",
        ))
    return findings


def _validate_main_handoff(main_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_protected_alias_findings(
        main_node,
        protected_roots={"ordered_records": "ordered_records", "payload": "payload"},
        function_name="main()",
        allow_payload_players=True,
    ))
    finalizer_calls = [
        node for node in _function_nodes(main_node)
        if isinstance(node, ast.Call) and _is_name(node.func, CANONICAL_FINALIZER)
    ]
    if len(finalizer_calls) != 1:
        findings.append(_finding(
            "V2PROD_MAIN_FINALIZER_CALL", PRODUCER_IMPLEMENTATION,
            f"main() must call {CANONICAL_FINALIZER} exactly once.",
        ))
        return findings
    finalizer_call = finalizer_calls[0]
    handoff_assignment = next(
        (
            node for node in _function_nodes(main_node)
            if isinstance(node, ast.Assign)
            and any(_is_name(target, "ordered_records") for target in node.targets)
            and node.value is finalizer_call
        ),
        None,
    )
    if handoff_assignment is None:
        findings.append(_finding(
            "V2PROD_MAIN_FINALIZER_HANDOFF", PRODUCER_IMPLEMENTATION,
            "main() must bind the sole finalizer return to ordered_records.",
        ))
        return findings
    handoff_line = handoff_assignment.lineno
    for node in _function_nodes(main_node):
        if getattr(node, "lineno", -1) <= handoff_line:
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            if any(_is_name(target, "ordered_records") or _subscript_root_name(target) == "ordered_records" for target in targets):
                findings.append(_finding(
                    "V2PROD_MAIN_POST_FINALIZER_MUTATION", PRODUCER_IMPLEMENTATION,
                    "main() must not rebind or mutate ordered_records after finalization.",
                ))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if _is_name(node.func.value, "ordered_records") and node.func.attr in _MUTATING_METHODS:
                findings.append(_finding(
                    "V2PROD_MAIN_POST_FINALIZER_MUTATION", PRODUCER_IMPLEMENTATION,
                    "main() must not transform ordered_records after finalization.",
                ))
            elif _is_name(node.func.value, "ordered_records"):
                findings.append(_finding(
                    "V2PROD_UNKNOWN_MUTATOR", PRODUCER_IMPLEMENTATION,
                    "main() must not call an unapproved method on ordered_records after finalization.",
                ))
    official_writes = [
        node for node in _function_nodes(main_node)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        and any(
            isinstance(target, ast.Subscript) and _subscript_key(target) in OFFICIAL_OUTPUT_FIELDS
            for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        )
    ]
    if official_writes:
        findings.append(_finding(
            "V2PROD_MAIN_OFFICIAL_WRITE", PRODUCER_IMPLEMENTATION,
            "main() must contain no direct official score, probability, rank, or tier writes.",
        ))
    prohibited = {
        "canonical_z_score_scale", "z_score_scale", "canonical_compute_probability_vectors",
        "canonical_assign_tier", "combine_raw_score", "apply_gates", "tempered_softmax",
    }
    if _main_called_names(main_node) & prohibited:
        findings.append(_finding(
            "V2PROD_MAIN_SCORING_AUTHORITY", PRODUCER_IMPLEMENTATION,
            "main() must not retain canonical or legacy finalization authority.",
        ))
    payload_assignments = [
        node for node in _function_nodes(main_node)
        if isinstance(node, ast.Assign) and any(_is_name(target, "payload") for target in node.targets)
    ]
    canonical_payload_assignments = [
        node for node in payload_assignments
        if (
            isinstance(node, ast.Assign)
            and any(_is_name(target, "payload") for target in node.targets)
            and _dict_value(node.value, "players") is not None
            and _is_name(_dict_value(node.value, "players"), "ordered_records")
        )
    ]
    payload_handoff = len(canonical_payload_assignments) == 1
    json_assignments = _name_assignments(main_node, "json_str")
    json_handoff = len(json_assignments) == 1 and isinstance(json_assignments[0], (ast.Assign, ast.AnnAssign)) and (
        isinstance(json_assignments[0].value, ast.Call)
        and isinstance(json_assignments[0].value.func, ast.Attribute)
        and _is_name(json_assignments[0].value.func.value, "json")
        and json_assignments[0].value.func.attr == "dumps"
        and bool(json_assignments[0].value.args)
        and _is_name(json_assignments[0].value.args[0], "payload")
    )
    if not payload_handoff or not json_handoff:
        findings.append(_finding(
            "V2PROD_MAIN_SERIALIZATION_HANDOFF", PRODUCER_IMPLEMENTATION,
            "main() must pass ordered_records directly into the approved JSON payload serialization.",
        ))
        return findings

    payload_assignment = canonical_payload_assignments[0]
    json_assignment = json_assignments[0]
    if payload_assignment.lineno >= json_assignment.lineno:
        findings.append(_finding(
            "V2PROD_PAYLOAD_SERIALIZATION_ORDER", PRODUCER_IMPLEMENTATION,
            "main() must construct the canonical payload before serializing it.",
        ))
        return findings

    for node in _function_nodes(main_node):
        if getattr(node, "lineno", -1) <= payload_assignment.lineno:
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            for target in targets:
                if _is_name(target, "payload"):
                    if isinstance(node, ast.AugAssign) and isinstance(node.value, ast.Dict) and _dict_value(node.value, "players") is not None:
                        rule_id = "V2PROD_PAYLOAD_PLAYERS_REPLACED"
                        reason = "main() must not replace payload players after canonical payload construction."
                    else:
                        rule_id = "V2PROD_PAYLOAD_REBIND"
                        reason = "main() must not rebind payload after canonical payload construction."
                    findings.append(_finding(rule_id, PRODUCER_IMPLEMENTATION, reason))
                elif _subscript_root_name(target) == "payload":
                    findings.append(_finding(
                        "V2PROD_PAYLOAD_PLAYERS_REPLACED", PRODUCER_IMPLEMENTATION,
                        "main() must not mutate payload or its protected players collection after canonical construction.",
                    ))
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if _receiver_root_name(node.func.value) != "payload":
            continue
        if (
            node.func.attr == "update"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Dict)
            and _dict_value(node.args[0], "players") is not None
        ):
            findings.append(_finding(
                "V2PROD_PAYLOAD_PLAYERS_REPLACED", PRODUCER_IMPLEMENTATION,
                "main() must not replace payload players after canonical payload construction.",
            ))
        else:
            findings.append(_finding(
                "V2PROD_UNKNOWN_MUTATOR", PRODUCER_IMPLEMENTATION,
                "main() must not call an unapproved method on payload after canonical construction.",
            ))
    return findings


def _validate_v2_producer_integration(repo_root: Path) -> list[Finding]:
    """Validate finite canonical-finalizer and main-handoff boundaries only."""
    try:
        module = _producer_module_ast(repo_root / PRODUCER_IMPLEMENTATION)
    except ValueError as exc:
        raise ValidationConfigurationError(str(exc)) from exc
    main_node = _named_top_level_function(module, "main")
    finalizer = _named_top_level_function(module, CANONICAL_FINALIZER)
    if main_node is None or finalizer is None:
        return [_finding(
            "V2PROD_FINALIZER_MISSING", PRODUCER_IMPLEMENTATION,
            f"Producer must define main() and {CANONICAL_FINALIZER}().",
        )]
    findings = _validate_finalizer(finalizer)
    findings.extend(_validate_main_handoff(main_node))
    if "compute_player_projection" not in _main_called_names(main_node):
        findings.append(_finding(
            "V2PROD_CANONICAL_SCORER", PRODUCER_IMPLEMENTATION,
            "main() must prepare records through compute_player_projection().",
        ))
    projection_assignment = _has_name_assignment(
        main_node,
        "projection",
        lambda value: isinstance(value, ast.Call) and _is_name(value.func, "compute_player_projection"),
    )
    post_gate_lineage = any(_is_post_gate_projection_entry(node) for node in _function_nodes(main_node))
    if not projection_assignment or not post_gate_lineage:
        findings.append(_finding(
            "V2PROD_POST_GATE_LINEAGE", PRODUCER_IMPLEMENTATION,
            "main() must preserve compute_player_projection().post_gate_raw in prepared records.",
        ))
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
            "authoritative canonical doctrine",
            "reusable root producer",
            "PostGateRaw",
        ),
        rule_id="GOV_CANONICAL_PRODUCER_MIGRATION",
        file=SCORING_SPEC,
        reason="The overview must identify canonical v2 as the reusable root-producer doctrine.",
    )
    _require_terms(
        findings,
        section=divergence,
        terms=(
            "canonical v2.0.0 reusable root producer",
            "Historical 3M formulas remain diagnostic-only",
            "No event, artifact, payload, database, deploy",
        ),
        rule_id="GOV_PRODUCER_MIGRATION_STATUS",
        file=SCORING_SPEC,
        reason="Production-divergence text must accurately state canonical producer migration and historical isolation.",
    )
    _require_terms(
        findings,
        section=divergence,
        terms=(
            "Wyndham initialization remains blocked",
            "No event, artifact, payload, database, deploy",
        ),
        rule_id="GOV_WYNDHAM_BLOCK",
        file=SCORING_SPEC,
        reason="Wyndham initialization must remain blocked despite reusable root-producer migration.",
    )
    _require_terms(
        findings,
        section=history + "\n" + divergence,
        terms=(
            "Archived 3M enriched and Open v3 artifacts remain valid historical event records",
            "No event, artifact, payload, database, deploy",
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


def _validate_wyndham_retrospective_fixture(
    fixture_root: Path, manifest: dict[str, Any]
) -> list[Finding]:
    """Report every deviation from the sole authorized Wyndham
    retrospective-development fixture.

    This check applies only to the exact, hardcoded fixture root the caller
    passes in. It never widens into a generic "fixture mode" bypass: any
    deviation is returned to the caller, which keeps its blanket
    ACTIVE_EVENT_WYNDHAM_ABSENT rule in force.
    """
    findings: list[Finding] = []

    if manifest.get("status") != "NO_ACTIVE_EVENT":
        findings.append(
            _finding(
                "RETROSPECTIVE_FIXTURE_ACTIVE_EVENT_STATUS",
                RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                "The retrospective fixture exception requires config/active_event.json "
                "status to remain 'NO_ACTIVE_EVENT'.",
            )
        )

    readme_path = fixture_root / RETROSPECTIVE_FIXTURE_README
    if not readme_path.is_file():
        findings.append(
            _finding(
                "RETROSPECTIVE_FIXTURE_README_MISSING",
                RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                f"Retrospective fixture requires {RETROSPECTIVE_FIXTURE_README}.",
            )
        )
    else:
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            readme_text = ""
            findings.append(
                _finding(
                    "RETROSPECTIVE_FIXTURE_README_UNREADABLE",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    f"Cannot read {RETROSPECTIVE_FIXTURE_README}: {exc}",
                )
            )
        missing_markers = [
            marker for marker in RETROSPECTIVE_FIXTURE_MARKERS if marker not in readme_text
        ]
        if missing_markers:
            findings.append(
                _finding(
                    "RETROSPECTIVE_FIXTURE_MARKER_MISSING",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    "Retrospective fixture README is missing required fence markers: "
                    + ", ".join(missing_markers)
                    + ".",
                )
            )

    top_level = {entry.name for entry in fixture_root.iterdir()} if fixture_root.is_dir() else set()
    unapproved = sorted(top_level - RETROSPECTIVE_FIXTURE_APPROVED_ENTRIES)
    if unapproved:
        findings.append(
            _finding(
                "RETROSPECTIVE_FIXTURE_UNAPPROVED_CONTENT",
                RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                "Retrospective fixture contains unapproved top-level paths: "
                + ", ".join(unapproved)
                + ".",
            )
        )

    for name in ("output", "audit"):
        directory = fixture_root / name
        if directory.is_dir() and any(directory.rglob("*")):
            findings.append(
                _finding(
                    f"RETROSPECTIVE_FIXTURE_NONEMPTY_{name.upper()}",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    f"Retrospective fixture {name}/ must remain empty; no output, "
                    "deploy, or live artifact may exist in this phase.",
                )
            )

    deploy_dir = fixture_root / "deploy"
    if deploy_dir.is_dir():
        deploy_entries = list(deploy_dir.iterdir())
        unapproved_deploy = sorted(
            entry.name for entry in deploy_entries
            if entry.name not in RETROSPECTIVE_FIXTURE_APPROVED_DEPLOY_ENTRIES
        )
        if unapproved_deploy:
            findings.append(
                _finding(
                    "RETROSPECTIVE_FIXTURE_DEPLOY_CONTENT",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    "Retrospective fixture deploy/ must contain only the local "
                    "board-shell files (index.html, app.js, styles.css) and an "
                    "empty data/ directory: " + ", ".join(unapproved_deploy) + ".",
                )
            )
        misplaced_shell = sorted(
            entry.name for entry in deploy_entries
            if entry.name in RETROSPECTIVE_FIXTURE_BOARD_SHELL_FILES and not entry.is_file()
        )
        if misplaced_shell:
            findings.append(
                _finding(
                    "RETROSPECTIVE_FIXTURE_BOARD_SHELL_NOT_A_FILE",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    "Retrospective fixture board-shell entries must be plain files, "
                    "not directories: " + ", ".join(misplaced_shell) + ".",
                )
            )
        deploy_data_dir = deploy_dir / "data"
        if deploy_data_dir.is_dir() and any(deploy_data_dir.rglob("*")):
            findings.append(
                _finding(
                    "RETROSPECTIVE_FIXTURE_NONEMPTY_DEPLOY_DATA",
                    RETROSPECTIVE_FIXTURE_EVENT_ROOT,
                    "Retrospective fixture deploy/data/ must remain empty; no deploy "
                    "payload may exist in this phase.",
                )
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
        fixture_findings = _validate_wyndham_retrospective_fixture(wyndham, manifest)
        if fixture_findings:
            findings.extend(fixture_findings)
            findings.append(
                _finding(
                    "ACTIVE_EVENT_WYNDHAM_ABSENT",
                    "events/2026_wyndham_championship",
                    "Wyndham event directory must not exist during the doctrine-only phase.",
                )
            )
        else:
            findings.append(
                _finding(
                    RETROSPECTIVE_FIXTURE_SUCCESS_RULE,
                    "events/2026_wyndham_championship",
                    "Wyndham event directory recognized as the sole authorized "
                    "retrospective-development fixture: NO_ACTIVE_EVENT is preserved, "
                    "all required fence markers are present, and no output, deploy, "
                    "or live artifact exists under the fixture root.",
                    severity="info",
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
        scoring_spec_version = _scoring_spec_version(texts[SCORING_SPEC])
        findings.extend(_validate_diagnostics(root, marker))
        findings.extend(_validate_v2_implementation(root, marker, scoring_spec_version))
        findings.extend(_validate_v2_producer_integration(root))
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
