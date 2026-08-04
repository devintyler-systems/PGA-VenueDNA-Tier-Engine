#!/usr/bin/env python3
"""Deterministically build a schema-1.1 external deploy profile.

Reads an existing static-board deploy tree, discovers literal and dynamic
fetch targets in its declared scripts, computes SHA-256 integrity coverage,
and writes a ``config/deploy_contracts/archived/*.json`` profile that
already passes :func:`validate_deploy_contract.validate_deploy_profile`.

Read-only against the deploy root: this tool never writes, hashes-in-place,
or mutates any file under ``--deploy-root``.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_deploy_contract as vdc  # noqa: E402

ARCHIVE_ROOT_RELATIVE = ("events", "2026_Finished_Events")


@dataclass
class BuildResult:
    profile: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    deploy_root: Path | None = None
    output_path: Path | None = None


def _resolve_declared_entries(
    deploy_root: Path,
    values: list[str],
    kind: str,
    require_file: bool,
    errors: list[str],
) -> list[tuple[str, Path]]:
    resolved: list[tuple[str, Path]] = []

    for value in values:
        if not vdc.is_safe_declared_path(value):
            errors.append(f"Deploy profile board.{kind} path is unsafe: {value}")
            continue

        candidate = vdc.resolve_safe_path(deploy_root, value)

        if candidate is None:
            errors.append(f"Deploy profile board.{kind} path is unsafe: {value}")
            continue

        exists = candidate.is_file() if require_file else candidate.is_dir()

        if not exists:
            label = "file" if require_file else "directory"
            errors.append(f"Deploy profile {kind} {label} missing: {value} -> {candidate}")
            continue

        resolved.append((value, candidate))

    return resolved


def _check_output_safety(
    repo: Path, output_path: Path, deploy_root: Path, errors: list[str]
) -> None:
    archive_root = repo.joinpath(*ARCHIVE_ROOT_RELATIVE).resolve()

    try:
        output_path.relative_to(archive_root)
        errors.append(
            f"Output must not be inside the archive directory {archive_root}: {output_path}"
        )
        return
    except ValueError:
        pass

    try:
        output_path.relative_to(deploy_root)
        errors.append(
            f"Output must not be inside the declared deploy root {deploy_root}: {output_path}"
        )
    except ValueError:
        pass


def _load_dynamic_declarations(
    repo: Path, dynamic_declarations_arg: str, errors: list[str]
) -> list[Any]:
    decl_path = vdc.resolve_repo_relative_cli_path(repo, dynamic_declarations_arg)

    if decl_path is None:
        errors.append(
            "Dynamic declarations path must resolve inside the repository: "
            f"{dynamic_declarations_arg}"
        )
        return []

    if not decl_path.is_file():
        errors.append(f"Dynamic declarations file does not exist: {decl_path}")
        return []

    try:
        decl_data = json.loads(decl_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Cannot read dynamic declarations file {decl_path}: {exc}")
        return []

    raw = decl_data.get("dynamic_fetches") if isinstance(decl_data, dict) else None

    if not isinstance(raw, list):
        errors.append(
            f"Dynamic declarations file requires a dynamic_fetches list: {decl_path}"
        )
        return []

    return copy.deepcopy(raw)


def _canonical_dynamic_fetches(entries: list[Any]) -> list[Any]:
    """Return a deterministic copy without inferring or changing availability."""
    canonical: list[Any] = []

    for entry in entries:
        if not isinstance(entry, dict):
            canonical.append(entry)
            continue

        copied = copy.deepcopy(entry)
        targets = copied.get("targets")
        if isinstance(targets, list):
            copied["targets"] = sorted(
                targets,
                key=lambda target: (
                    vdc.normalize_relative(target.get("path", ""))
                    if isinstance(target, dict) else "",
                    target.get("availability", "") if isinstance(target, dict) else "",
                ),
            )
        canonical.append(copied)

    return sorted(
        canonical,
        key=lambda entry: (
            entry.get("expression", "") if isinstance(entry, dict) else "",
            entry.get("pattern", "") if isinstance(entry, dict) else "",
        ),
    )


def build_profile(
    *,
    repo: Path,
    deploy_root_arg: str,
    output_arg: str,
    event_slug: str,
    board_mode: str,
    entry_html: str,
    scripts: list[str],
    stylesheets: list[str],
    data_roots: list[str],
    dynamic_declarations_arg: str | None,
) -> BuildResult:
    errors: list[str] = []
    warnings: list[str] = []

    repo_resolved = repo.resolve()

    deploy_root = vdc.resolve_repo_relative_cli_path(repo_resolved, deploy_root_arg)

    if deploy_root is None:
        errors.append(
            f"Deploy root must resolve inside the repository: {deploy_root_arg}"
        )
    elif not deploy_root.is_dir():
        errors.append(f"Deploy root does not exist: {deploy_root}")
        deploy_root = None

    output_path = vdc.resolve_repo_relative_cli_path(repo_resolved, output_arg)

    if output_path is None:
        errors.append(f"Output must resolve inside the repository: {output_arg}")
    elif deploy_root is not None:
        _check_output_safety(repo_resolved, output_path, deploy_root, errors)

    if not event_slug:
        errors.append("event_slug must be a non-empty string")

    if board_mode not in vdc.BOARD_MODES:
        errors.append(f"Unsupported board mode: {board_mode!r}")

    if deploy_root is None:
        return BuildResult(
            profile=None, errors=errors, warnings=warnings, deploy_root=None,
            output_path=output_path,
        )

    entry_resolved = _resolve_declared_entries(
        deploy_root, [entry_html] if entry_html else [], "entry_html", True, errors
    )
    resolved_scripts = _resolve_declared_entries(
        deploy_root, scripts, "scripts", True, errors
    )
    resolved_stylesheets = _resolve_declared_entries(
        deploy_root, stylesheets, "stylesheets", True, errors
    )
    _resolve_declared_entries(deploy_root, data_roots, "data_roots", False, errors)

    literal_present_targets: list[tuple[str, Path]] = []
    seen_literal: set[str] = set()
    detected_dynamic_expressions: list[str] = []

    for _, script_path in resolved_scripts:
        text = script_path.read_text(encoding="utf-8", errors="replace")
        literal_targets, dynamic_expressions = vdc.scan_script_fetch_targets(text)

        for expression in dynamic_expressions:
            if expression not in detected_dynamic_expressions:
                detected_dynamic_expressions.append(expression)

        for target in literal_targets:
            local_value = vdc.local_target(target)

            if local_value is None:
                continue

            if local_value in seen_literal:
                continue

            seen_literal.add(local_value)

            resolved = vdc.resolve_safe_path(deploy_root, local_value)

            if resolved is None:
                errors.append(f"Literal fetch target path is unsafe: {target}")
                continue

            if not resolved.is_file():
                errors.append(f"Literal fetch target missing: {target} -> {resolved}")
                continue

            validation_error = vdc.validate_payload(resolved)

            if validation_error:
                errors.append(
                    f"Invalid literal fetch target: {resolved} ({validation_error})"
                )
                continue

            literal_present_targets.append((local_value, resolved))

    if detected_dynamic_expressions and not dynamic_declarations_arg:
        errors.append(
            "Dynamic fetch expressions detected but --dynamic-declarations was not "
            "supplied: " + ", ".join(detected_dynamic_expressions)
        )

    dynamic_fetches_value: list[Any] = []

    if dynamic_declarations_arg:
        dynamic_fetches_value = _load_dynamic_declarations(
            repo_resolved, dynamic_declarations_arg, errors
        )
        dynamic_fetches_value = _canonical_dynamic_fetches(dynamic_fetches_value)

    dynamic_target_paths: list[str] = []
    dynamic_present_targets: list[tuple[str, Path]] = []

    for entry in dynamic_fetches_value:
        if not isinstance(entry, dict):
            continue

        targets = entry.get("targets")

        if not isinstance(targets, list):
            continue

        for target in targets:
            if not isinstance(target, dict):
                continue

            path_value = target.get("path")

            if not isinstance(path_value, str) or not path_value:
                continue

            dynamic_target_paths.append(path_value)

            resolved = vdc.resolve_safe_path(deploy_root, path_value)

            if resolved is None:
                continue

            if resolved.is_file():
                dynamic_present_targets.append((path_value, resolved))

    local_targets_needing_root = [value for value, _ in literal_present_targets]
    local_targets_needing_root.extend(dynamic_target_paths)

    if local_targets_needing_root:
        if not data_roots:
            errors.append(
                "Local literal or dynamic targets exist but no --data-root was declared"
            )
        else:
            normalized_roots = [vdc.normalize_relative(root) for root in data_roots]

            for path_value in local_targets_needing_root:
                norm_path = vdc.normalize_relative(path_value)
                contained = any(
                    norm_path == root or norm_path.startswith(root + "/")
                    for root in normalized_roots
                )

                if not contained:
                    errors.append(
                        "Target is not contained under any declared data root: "
                        f"{path_value}"
                    )

    integrity_categories: dict[str, str] = {}
    integrity_entries: list[tuple[str, Path]] = []

    def add_integrity(value: str, path: Path, category: str) -> None:
        norm = vdc.normalize_relative(value)

        if norm in integrity_categories:
            errors.append(
                f"Duplicate path across runtime categories: {value} "
                f"(already declared as {integrity_categories[norm]})"
            )
            return

        integrity_categories[norm] = category
        integrity_entries.append((value, path))

    for value, path in entry_resolved:
        add_integrity(value, path, "entry_html")

    for value, path in resolved_scripts:
        add_integrity(value, path, "script")

    for value, path in resolved_stylesheets:
        add_integrity(value, path, "stylesheet")

    for value, path in literal_present_targets:
        add_integrity(value, path, "literal_fetch_target")

    for value, path in dynamic_present_targets:
        add_integrity(value, path, "dynamic_target")

    if errors:
        return BuildResult(
            profile=None, errors=errors, warnings=warnings, deploy_root=deploy_root,
            output_path=output_path,
        )

    integrity_files = sorted(
        (
            {"path": value, "sha256": vdc.compute_sha256(path)}
            for value, path in integrity_entries
        ),
        key=lambda entry: vdc.normalize_relative(entry["path"]),
    )

    board = {
        "mode": board_mode,
        "entry_html": entry_html,
        "scripts": sorted(scripts, key=vdc.normalize_relative),
        "stylesheets": sorted(stylesheets, key=vdc.normalize_relative),
        "data_roots": sorted(data_roots, key=vdc.normalize_relative),
    }

    profile = {
        "schema_version": vdc.PROFILE_SCHEMA_VERSION,
        "profile_type": vdc.PROFILE_TYPE,
        "event_slug": event_slug,
        "deploy_root": deploy_root.relative_to(repo_resolved).as_posix(),
        "board": board,
        "dynamic_fetches": dynamic_fetches_value,
        "integrity": {"algorithm": "sha256", "files": integrity_files},
    }

    report_path = output_path if output_path is not None else Path(output_arg)
    validator_errors, validator_warnings, _ = vdc.validate_deploy_profile(
        profile, report_path, repo_resolved
    )
    warnings.extend(validator_warnings)

    if validator_errors:
        return BuildResult(
            profile=None, errors=validator_errors, warnings=warnings,
            deploy_root=deploy_root, output_path=output_path,
        )

    return BuildResult(
        profile=profile, errors=[], warnings=warnings, deploy_root=deploy_root,
        output_path=output_path,
    )


def render_profile_json(profile: dict[str, Any]) -> bytes:
    text = json.dumps(profile, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    return text.encode("utf-8")


def write_profile_atomic(output_path: Path, rendered: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(
        dir=str(output_path.parent), prefix=output_path.name + ".", suffix=".tmp"
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(rendered)

        os.replace(tmp_name, str(output_path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Default: parent directory of tools/",
    )
    parser.add_argument("--deploy-root", required=True, help="Deploy root relative to repository")
    parser.add_argument(
        "--output", required=True, help="Profile output path relative to repository"
    )
    parser.add_argument("--event-slug", required=True, help="Archived event slug")
    parser.add_argument(
        "--board-mode", required=True, choices=sorted(vdc.BOARD_MODES), help="Board mode"
    )
    parser.add_argument(
        "--entry-html", required=True, help="Entry document, deploy-root-relative"
    )
    parser.add_argument(
        "--script", action="append", default=[], help="Script, deploy-root-relative (repeatable)"
    )
    parser.add_argument(
        "--stylesheet",
        action="append",
        default=[],
        help="Stylesheet, deploy-root-relative (repeatable)",
    )
    parser.add_argument(
        "--data-root",
        action="append",
        default=[],
        help="Data root directory, deploy-root-relative (repeatable)",
    )
    parser.add_argument(
        "--dynamic-declarations",
        default=None,
        help="Path to a dynamic_fetches declarations JSON file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the profile without writing it",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the existing output profile matches a fresh build without writing",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.dry_run and args.check:
        print("BUILD FAILED")
        print("- --dry-run and --check are mutually exclusive")
        return 1

    repo = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[1]
    )

    result = build_profile(
        repo=repo,
        deploy_root_arg=args.deploy_root,
        output_arg=args.output,
        event_slug=args.event_slug,
        board_mode=args.board_mode,
        entry_html=args.entry_html,
        scripts=args.script,
        stylesheets=args.stylesheet,
        data_roots=args.data_root,
        dynamic_declarations_arg=args.dynamic_declarations,
    )

    if result.warnings:
        print("WARNINGS:")
        for warning in result.warnings:
            print(f"- {warning}")

    if result.errors:
        print("BUILD FAILED")
        for error in result.errors:
            print(f"- {error}")
        return 1

    assert result.profile is not None
    assert result.output_path is not None

    rendered = render_profile_json(result.profile)

    if args.dry_run:
        print(rendered.decode("utf-8"), end="")
        print("BUILD OK (dry run)")
        return 0

    if args.check:
        if not result.output_path.is_file():
            print("BUILD CHECK FAILED")
            print(f"- Output profile does not exist: {result.output_path}")
            return 1

        existing = result.output_path.read_bytes()

        if existing == rendered:
            print(f"Deploy profile is up to date: {result.output_path}")
            return 0

        print("BUILD CHECK FAILED")
        print(f"- Deploy profile is stale and needs regeneration: {result.output_path}")
        return 1

    result.output_path.parent.mkdir(parents=True, exist_ok=True)
    write_profile_atomic(result.output_path, rendered)
    print(f"Deploy profile written: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
