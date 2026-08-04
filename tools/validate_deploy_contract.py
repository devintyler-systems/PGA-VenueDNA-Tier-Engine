#!/usr/bin/env python3
"""Validate static-board fetch targets and basic JSON/CSV payload integrity."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FETCH_CALL_PATTERN = r"""\b(?:fetch|d3\.(?:csv|json))\(\s*([^,\r\n)]*)"""
META_REFRESH_PATTERN = r"""<meta\s+http-equiv=[\"']refresh[\"']\s+content=[\"'][^\"']*url=([^\"']+)[\"']"""
DYNAMIC_PATTERN_PLACEHOLDER = re.compile(r"\\\{[^{}]+\\\}")
FETCH_PATTERNS = (
    r"""fetch\(\s*[`'"]([^`'"]+)[`'"]""",
    r"""d3\.csv\(\s*[`'"]([^`'"]+)[`'"]""",
    r"""d3\.json\(\s*[`'"]([^`'"]+)[`'"]""",
)

PROFILE_SCHEMA_VERSION = "1.1"
PROFILE_TYPE = "archived_deploy"
BOARD_MODES = {"static_app", "harness", "inline_styled_app"}
DYNAMIC_AVAILABILITY = {"required", "optional_pending"}
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DRIVE_PREFIX_PATTERN = re.compile(r"^[A-Za-z]:")


def repo_path(repo: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_fetch_targets(app_js: str) -> list[str]:
    targets: list[str] = []

    for pattern in FETCH_PATTERNS:
        for target in re.findall(pattern, app_js):
            if target not in targets:
                targets.append(target)

    return targets


def extract_nonliteral_fetch_targets(app_js: str) -> list[str]:
    """Return fetch expressions that cannot be resolved statically."""
    targets: list[str] = []

    for expression in re.findall(FETCH_CALL_PATTERN, app_js):
        target = expression.strip()

        if target.startswith(("'", '"', "`")):
            continue

        if target and target not in targets:
            targets.append(target)

    return targets


def local_target(target: str) -> str | None:
    clean_target = target.split("?", 1)[0].split("#", 1)[0]

    if clean_target.startswith(("http://", "https://", "//", "data:")):
        return None

    return clean_target


def resolve_target(deploy_root: Path, target: str) -> Path:
    if target.startswith("/"):
        return deploy_root / target.lstrip("/")

    return deploy_root / target


def is_deploy_relative_path(target: str) -> bool:
    path = Path(target)
    return (
        local_target(target) == target
        and not path.is_absolute()
        and not path.drive
        and ".." not in path.parts
    )


def validate_json(path: Path) -> str | None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return str(exc)

    return None


def validate_csv(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)

        if not header:
            return "CSV has no header row"

    except Exception as exc:
        return str(exc)

    return None


def validate_payload(path: Path) -> str | None:
    if path.suffix.lower() == ".json":
        return validate_json(path)

    if path.suffix.lower() == ".csv":
        return validate_csv(path)

    return None


def pattern_matches(pattern: str, value: str) -> bool:
    expression = DYNAMIC_PATTERN_PLACEHOLDER.sub("[^/]+", re.escape(pattern))
    return re.fullmatch(expression, value) is not None


def load_dynamic_payload_manifest(
    deploy_root: Path, manifest_arg: str | None, errors: list[str], warnings: list[str]
) -> dict[str, dict[str, Any]]:
    manifest_path = deploy_root / (manifest_arg or "payload_manifest.json")

    if not manifest_path.is_file():
        if manifest_arg:
            errors.append(f"Payload manifest does not exist: {manifest_path}")
        return {}

    try:
        manifest = load_manifest(manifest_path)
    except Exception as exc:
        errors.append(f"Invalid payload manifest {manifest_path}: {exc}")
        return {}

    if manifest.get("schema_version") != "1.0":
        errors.append(
            f"Payload manifest {manifest_path} requires schema_version '1.0'"
        )

    entries = manifest.get("dynamic_fetches")

    if not isinstance(entries, list):
        errors.append(f"Payload manifest {manifest_path} requires dynamic_fetches list")
        return {}

    declarations: dict[str, dict[str, Any]] = {}

    for index, entry in enumerate(entries):
        label = f"Payload manifest dynamic_fetches[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue

        expression = entry.get("expression")
        pattern = entry.get("pattern")
        expected_files = entry.get("expected_files")

        if not isinstance(expression, str) or not expression:
            errors.append(f"{label} requires non-empty expression")
            continue

        if expression in declarations:
            errors.append(f"{label} duplicates expression: {expression}")
            continue

        if not isinstance(pattern, str) or not pattern:
            errors.append(f"{label} requires non-empty pattern")
            continue

        if not isinstance(expected_files, list) or not expected_files:
            errors.append(f"{label} requires non-empty expected_files list")
            continue

        valid = True

        for expected_file in expected_files:
            if not isinstance(expected_file, str) or not expected_file:
                errors.append(f"{label} expected_files entries must be non-empty strings")
                valid = False
                continue

            if not is_deploy_relative_path(expected_file):
                errors.append(f"{label} expected file must be a local path: {expected_file}")
                valid = False
                continue

            if not pattern_matches(pattern, expected_file):
                errors.append(
                    f"{label} expected file does not match pattern: {expected_file}"
                )
                valid = False
                continue

            payload_path = resolve_target(deploy_root, expected_file)

            if not payload_path.is_file():
                errors.append(
                    f"Declared dynamic payload missing: {expected_file} -> {payload_path}"
                )
                valid = False
                continue

            validation_error = validate_payload(payload_path)

            if validation_error:
                errors.append(
                    f"Invalid declared dynamic payload: {payload_path} ({validation_error})"
                )
                valid = False

        if valid:
            declarations[expression] = entry

    if not declarations and not errors:
        warnings.append(f"Payload manifest {manifest_path} declares no dynamic fetches")

    return declarations


def is_safe_declared_path(value: Any) -> bool:
    """Validate a forward-slash, repo/deploy-root-relative path from a profile.

    Rejects empty values, backslashes, leading slashes, Windows drive
    prefixes, and any ``..`` segment. Callers still must resolve the
    candidate and verify containment against the intended base directory.
    """

    if not isinstance(value, str) or not value:
        return False

    if "\\" in value:
        return False

    if value.startswith("/"):
        return False

    if DRIVE_PREFIX_PATTERN.match(value):
        return False

    parts = value.split("/")

    if any(part in ("", "..") for part in parts):
        return False

    return True


def normalize_relative(value: str) -> str:
    parts = [part for part in value.split("/") if part not in ("", ".")]
    return "/".join(parts)


def resolve_safe_path(base: Path, value: Any) -> Path | None:
    """Resolve ``value`` against ``base`` iff it is safe and stays contained."""

    if not is_safe_declared_path(value):
        return None

    resolved_base = base.resolve()
    candidate = (resolved_base / value).resolve()

    try:
        candidate.relative_to(resolved_base)
    except ValueError:
        return None

    return candidate


def resolve_repo_relative_cli_path(repo: Path, value: str) -> Path | None:
    """Resolve a CLI-supplied path (OS-native syntax allowed) inside the repo."""

    if not value:
        return None

    candidate = Path(value)

    if not candidate.is_absolute():
        candidate = repo / candidate

    resolved_repo = repo.resolve()
    candidate = candidate.resolve()

    try:
        candidate.relative_to(resolved_repo)
    except ValueError:
        return None

    return candidate


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_deploy_profile(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_deploy_profile(
    profile: dict[str, Any], profile_path: Path, repo: Path
) -> tuple[list[str], list[str], list[str]]:
    """Validate a schema-1.1 external deploy profile.

    Returns ``(errors, warnings, report_lines)``. Read-only: never writes,
    hashes-in-place, or mutates deploy files.
    """

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(profile, dict):
        errors.append("Deploy profile must be a JSON object")
        return errors, warnings, [f"Profile path: {profile_path}"]

    for field in (
        "schema_version",
        "profile_type",
        "event_slug",
        "deploy_root",
        "board",
        "dynamic_fetches",
        "integrity",
    ):
        if field not in profile:
            errors.append(f"Deploy profile missing required field: {field}")

    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        errors.append(
            "Deploy profile schema_version must be "
            f"'{PROFILE_SCHEMA_VERSION}', got: {profile.get('schema_version')!r}"
        )

    if profile.get("profile_type") != PROFILE_TYPE:
        errors.append(
            f"Deploy profile profile_type must be '{PROFILE_TYPE}', "
            f"got: {profile.get('profile_type')!r}"
        )

    event_slug = profile.get("event_slug")

    if not isinstance(event_slug, str) or not event_slug:
        errors.append("Deploy profile event_slug must be a non-empty string")

    integrity = profile.get("integrity")

    if not isinstance(integrity, dict):
        errors.append("Deploy profile integrity must be an object")
        integrity = {}
    elif integrity.get("algorithm") != "sha256":
        errors.append(
            "Deploy profile integrity.algorithm must be 'sha256', "
            f"got: {integrity.get('algorithm')!r}"
        )

    deploy_root_value = profile.get("deploy_root")
    deploy_root: Path | None = None

    if not isinstance(deploy_root_value, str) or not deploy_root_value:
        errors.append("Deploy profile deploy_root must be a non-empty string")
    else:
        deploy_root = resolve_safe_path(repo, deploy_root_value)

        if deploy_root is None:
            errors.append(
                "Deploy profile deploy_root is unsafe or outside the "
                f"repository: {deploy_root_value}"
            )
        elif not deploy_root.is_dir():
            errors.append(f"Deploy profile deploy_root does not exist: {deploy_root}")
            deploy_root = None

    board = profile.get("board")

    if not isinstance(board, dict):
        errors.append("Deploy profile board must be an object")
        board = {}

    mode = board.get("mode")

    if mode not in BOARD_MODES:
        errors.append(f"Deploy profile board.mode is unsupported: {mode!r}")
        mode = None

    entry_html_value = board.get("entry_html")
    entry_path: Path | None = None

    if not isinstance(entry_html_value, str) or not entry_html_value:
        errors.append("Deploy profile board.entry_html must be a non-empty string")
        entry_html_value = None
    elif deploy_root is not None:
        entry_path = resolve_safe_path(deploy_root, entry_html_value)

        if entry_path is None:
            errors.append(f"Deploy profile board.entry_html path is unsafe: {entry_html_value}")
        elif not entry_path.is_file():
            errors.append(
                f"Deploy profile entry document missing: {entry_html_value} -> {entry_path}"
            )
            entry_path = None

    scripts_value = board.get("scripts")

    if not isinstance(scripts_value, list) or len(scripts_value) < 1:
        errors.append("Deploy profile board.scripts requires at least one entry")
        scripts_value = []

    stylesheets_value = board.get("stylesheets")

    if not isinstance(stylesheets_value, list):
        errors.append("Deploy profile board.stylesheets must be a list")
        stylesheets_value = []

    if mode in ("static_app", "harness") and len(stylesheets_value) < 1:
        errors.append(
            f"Deploy profile board.stylesheets requires at least one entry for mode {mode}"
        )

    data_roots_value = board.get("data_roots")

    if not isinstance(data_roots_value, list):
        errors.append("Deploy profile board.data_roots must be a list")
        data_roots_value = []

    def resolve_declared_list(
        values: list[Any], kind: str, require_file: bool
    ) -> list[tuple[str, Path]]:
        resolved: list[tuple[str, Path]] = []
        seen: set[str] = set()

        if deploy_root is None:
            return resolved

        for value in values:
            if not isinstance(value, str) or not value:
                errors.append(f"Deploy profile board.{kind} entries must be non-empty strings")
                continue

            norm = normalize_relative(value)

            if norm in seen:
                errors.append(f"Deploy profile board.{kind} duplicates path: {value}")
                continue

            candidate = resolve_safe_path(deploy_root, value)

            if candidate is None:
                errors.append(f"Deploy profile board.{kind} path is unsafe: {value}")
                continue

            seen.add(norm)

            exists = candidate.is_file() if require_file else candidate.is_dir()

            if not exists:
                label = "file" if require_file else "directory"
                errors.append(f"Deploy profile {kind} {label} missing: {value} -> {candidate}")
                continue

            resolved.append((value, candidate))

        return resolved

    resolved_scripts = resolve_declared_list(scripts_value, "scripts", require_file=True)
    resolved_stylesheets = resolve_declared_list(
        stylesheets_value, "stylesheets", require_file=True
    )
    resolved_data_roots = resolve_declared_list(
        data_roots_value, "data_roots", require_file=False
    )

    literal_local_targets: list[tuple[str, Path]] = []
    detected_dynamic_expressions: list[str] = []
    seen_literal: set[str] = set()

    for _, script_path in resolved_scripts:
        text = script_path.read_text(encoding="utf-8", errors="replace")
        fetch_targets = extract_fetch_targets(text)
        nonliteral_targets = extract_nonliteral_fetch_targets(text)

        for target in nonliteral_targets:
            if target not in detected_dynamic_expressions:
                detected_dynamic_expressions.append(target)

        for target in fetch_targets:
            if "${" in target or "{" in target:
                if target not in detected_dynamic_expressions:
                    detected_dynamic_expressions.append(target)
                continue

            local_value = local_target(target)

            if local_value is None:
                warnings.append(f"External target not checked: {target}")
                continue

            if local_value in seen_literal:
                continue

            seen_literal.add(local_value)

            if deploy_root is None:
                continue

            resolved = resolve_safe_path(deploy_root, local_value)

            if resolved is None:
                errors.append(f"Literal fetch target path is unsafe: {target}")
                continue

            if not resolved.is_file():
                errors.append(f"Literal fetch target missing: {target} -> {resolved}")
                continue

            validation_error = validate_payload(resolved)

            if validation_error:
                errors.append(f"Invalid literal fetch target: {resolved} ({validation_error})")

            literal_local_targets.append((local_value, resolved))

    dynamic_fetches_value = profile.get("dynamic_fetches")

    if not isinstance(dynamic_fetches_value, list):
        errors.append("Deploy profile dynamic_fetches must be a list")
        dynamic_fetches_value = []

    declared_expressions: set[str] = set()
    declared_target_paths: set[str] = set()
    dynamic_target_records: list[tuple[str, Path, str]] = []

    for index, entry in enumerate(dynamic_fetches_value):
        label = f"Deploy profile dynamic_fetches[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue

        expression = entry.get("expression")
        pattern = entry.get("pattern")
        targets = entry.get("targets")

        if not isinstance(expression, str) or not expression:
            errors.append(f"{label} requires non-empty expression")
            continue

        if expression in declared_expressions:
            errors.append(f"{label} duplicates expression: {expression}")
            continue

        declared_expressions.add(expression)

        if not isinstance(pattern, str) or not pattern:
            errors.append(f"{label} requires non-empty pattern")
            continue

        if not isinstance(targets, list) or len(targets) < 1:
            errors.append(f"{label} requires non-empty targets list")
            continue

        seen_target_paths: set[str] = set()

        for target_index, target in enumerate(targets):
            target_label = f"{label}.targets[{target_index}]"

            if not isinstance(target, dict):
                errors.append(f"{target_label} must be an object")
                continue

            target_path_value = target.get("path")
            availability = target.get("availability")

            if not isinstance(target_path_value, str) or not target_path_value:
                errors.append(f"{target_label} requires non-empty path")
                continue

            if availability not in DYNAMIC_AVAILABILITY:
                errors.append(f"{target_label} has unknown availability: {availability!r}")
                continue

            norm = normalize_relative(target_path_value)

            if norm in seen_target_paths:
                errors.append(f"{target_label} duplicates target path: {target_path_value}")
                continue

            if norm in declared_target_paths:
                errors.append(
                    f"{target_label} duplicates target path across dynamic declarations: "
                    f"{target_path_value}"
                )
                continue

            seen_target_paths.add(norm)
            declared_target_paths.add(norm)

            if not pattern_matches(pattern, target_path_value):
                errors.append(
                    f"{target_label} does not match pattern {pattern}: {target_path_value}"
                )
                continue

            if deploy_root is None:
                continue

            resolved_target = resolve_safe_path(deploy_root, target_path_value)

            if resolved_target is None:
                errors.append(f"{target_label} path is unsafe: {target_path_value}")
                continue

            dynamic_target_records.append((target_path_value, resolved_target, availability))

    for expression in detected_dynamic_expressions:
        if expression not in declared_expressions:
            errors.append(f"Undeclared dynamic expression detected in scripts: {expression}")

    for expression in declared_expressions:
        if expression not in detected_dynamic_expressions:
            errors.append(
                f"Declared dynamic expression not found in any declared script: {expression}"
            )

    required_targets_checked = 0
    optional_present = 0
    optional_absent = 0
    targets_needing_integrity: list[tuple[str, Path]] = []

    for path_value, resolved_target, availability in dynamic_target_records:
        exists = resolved_target.is_file()

        if availability == "required":
            required_targets_checked += 1

            if not exists:
                errors.append(f"Required dynamic target missing: {path_value} -> {resolved_target}")
                continue

            validation_error = validate_payload(resolved_target)

            if validation_error:
                errors.append(
                    f"Invalid required dynamic target: {resolved_target} ({validation_error})"
                )

            targets_needing_integrity.append((path_value, resolved_target))
        else:
            if not exists:
                optional_absent += 1
                continue

            optional_present += 1
            validation_error = validate_payload(resolved_target)

            if validation_error:
                errors.append(
                    f"Invalid optional-pending dynamic target: {resolved_target} "
                    f"({validation_error})"
                )

            targets_needing_integrity.append((path_value, resolved_target))

    integrity_files_value = integrity.get("files") if isinstance(integrity, dict) else None

    if not isinstance(integrity_files_value, list):
        errors.append("Deploy profile integrity.files must be a list")
        integrity_files_value = []

    integrity_map: dict[str, str] = {}
    integrity_paths: dict[str, Path] = {}
    seen_integrity_paths: set[str] = set()

    for index, entry in enumerate(integrity_files_value):
        label = f"Deploy profile integrity.files[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue

        path_value = entry.get("path")
        digest_value = entry.get("sha256")

        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{label} requires non-empty path")
            continue

        if not isinstance(digest_value, str) or not HEX64_PATTERN.match(digest_value):
            errors.append(
                f"{label} sha256 must be exactly 64 lowercase hexadecimal characters: {path_value}"
            )
            continue

        norm = normalize_relative(path_value)

        if norm in seen_integrity_paths:
            errors.append(f"{label} duplicates integrity path: {path_value}")
            continue

        seen_integrity_paths.add(norm)

        if deploy_root is None:
            continue

        resolved = resolve_safe_path(deploy_root, path_value)

        if resolved is None:
            errors.append(f"{label} path is unsafe: {path_value}")
            continue

        if not resolved.is_file():
            errors.append(f"Integrity target missing: {path_value} -> {resolved}")
            continue

        integrity_map[norm] = digest_value
        integrity_paths[norm] = resolved

    verified_integrity_paths: set[str] = set()

    for norm, digest in integrity_map.items():
        actual = compute_sha256(integrity_paths[norm])

        if actual != digest:
            errors.append(
                f"Hash mismatch for {norm}: expected {digest}, got {actual}"
            )
            continue

        verified_integrity_paths.add(norm)

    coverage_targets: list[tuple[str, Path]] = []

    if entry_html_value is not None and entry_path is not None:
        coverage_targets.append((entry_html_value, entry_path))

    coverage_targets.extend(resolved_scripts)
    coverage_targets.extend(resolved_stylesheets)
    coverage_targets.extend(literal_local_targets)
    coverage_targets.extend(targets_needing_integrity)

    hashes_verified = len(verified_integrity_paths)

    for value, path in coverage_targets:
        norm = normalize_relative(value)
        digest = integrity_map.get(norm)

        if digest is None:
            errors.append(f"Missing mandatory integrity coverage: {value}")
            continue


    report_lines = [
        f"Profile path: {profile_path}",
        f"Deploy root: {deploy_root if deploy_root is not None else deploy_root_value}",
        f"Board mode: {mode if mode is not None else board.get('mode')}",
        f"Entry document: {entry_html_value if entry_html_value is not None else 'MISSING'}",
        f"Scripts checked: {len(resolved_scripts)}",
        f"Stylesheets checked: {len(resolved_stylesheets)}",
        f"Data roots checked: {len(resolved_data_roots)}",
        f"Literal local targets checked: {len(literal_local_targets)}",
        f"Dynamic expressions checked: {len(declared_expressions)}",
        f"Required dynamic targets checked: {required_targets_checked}",
        f"Optional-pending targets present: {optional_present}",
        f"Optional-pending targets absent: {optional_absent}",
        f"Hashes verified: {hashes_verified}",
    ]

    return errors, warnings, report_lines


def run_profile_validation(deploy_profile_arg: str, repo: Path) -> int:
    profile_path = resolve_repo_relative_cli_path(repo, deploy_profile_arg)

    if profile_path is None:
        print("DEPLOY PROFILE FAILED")
        print(
            "- Deploy profile path must resolve inside the repository: "
            f"{deploy_profile_arg}"
        )
        return 1

    if not profile_path.is_file():
        print("DEPLOY PROFILE FAILED")
        print(f"- Deploy profile does not exist: {profile_path}")
        return 1

    try:
        profile_data = load_deploy_profile(profile_path)
    except Exception as exc:
        print("DEPLOY PROFILE FAILED")
        print(f"- Cannot read deploy profile {profile_path}: {exc}")
        return 1

    errors, warnings, report_lines = validate_deploy_profile(profile_data, profile_path, repo)

    for line in report_lines:
        print(line)

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("DEPLOY PROFILE FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DEPLOY PROFILE PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Default: parent directory of tools/",
    )
    parser.add_argument(
        "--event-slug",
        default=None,
        help="Optional expected active event slug",
    )
    parser.add_argument(
        "--deploy-root",
        default=None,
        help="Deploy root relative to repository. Overrides active manifest.",
    )
    parser.add_argument(
        "--deploy-profile",
        default=None,
        help=(
            "Path to an external schema-1.1 deploy profile. Mutually exclusive "
            "with --deploy-root and --payload-manifest."
        ),
    )
    parser.add_argument(
        "--app-js",
        default="app.js",
        help="Path to app.js relative to deploy root",
    )
    parser.add_argument(
        "--payload-manifest",
        default=None,
        help=(
            "Optional manifest path relative to deploy root. Defaults to "
            "payload_manifest.json when present."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on dynamic fetch targets requiring manual review",
    )
    args = parser.parse_args()

    repo = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[1]
    )

    if args.deploy_profile:
        if args.deploy_root:
            print("DEPLOY PROFILE FAILED")
            print("- --deploy-profile and --deploy-root are mutually exclusive")
            return 1

        if args.payload_manifest:
            print("DEPLOY PROFILE FAILED")
            print("- --deploy-profile and --payload-manifest are mutually exclusive")
            return 1

        return run_profile_validation(args.deploy_profile, repo)

    errors: list[str] = []
    warnings: list[str] = []

    if args.deploy_root:
        deploy_root = repo_path(repo, args.deploy_root)
    else:
        manifest_path = repo / "config" / "active_event.json"

        try:
            manifest = load_manifest(manifest_path)
        except Exception as exc:
            print("DEPLOY CONTRACT FAILED")
            print(f"- Cannot read {manifest_path}: {exc}")
            return 1

        if manifest.get("status") == "NO_ACTIVE_EVENT":
            print("DEPLOY CONTRACT FAILED")
            print(
                "- No active event. Use --deploy-root to validate "
                "an archived event or local fixture."
            )
            return 1

        if args.event_slug and manifest.get("event_slug") != args.event_slug:
            print("DEPLOY CONTRACT FAILED")
            print(
                f"- Active event is {manifest.get('event_slug')}, "
                f"not {args.event_slug}"
            )
            return 1

        deploy_root_value = manifest.get("deploy_root")

        if not deploy_root_value:
            print("DEPLOY CONTRACT FAILED")
            print("- Active manifest has no deploy_root")
            return 1

        deploy_root = repo_path(repo, deploy_root_value)

    app_js = deploy_root / args.app_js
    index_html = deploy_root / "index.html"
    styles_css = deploy_root / "styles.css"
    data_dir = deploy_root / "data"

    required_paths = (
        (app_js, "app.js"),
        (index_html, "index.html"),
        (styles_css, "styles.css"),
        (data_dir, "data directory"),
    )

    for path, label in required_paths:
        if not path.exists():
            errors.append(f"Missing deploy component [{label}]: {path}")

    if errors:
        print("DEPLOY CONTRACT FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    app_text = app_js.read_text(encoding="utf-8", errors="replace")
    fetch_targets = extract_fetch_targets(app_text)
    nonliteral_targets = extract_nonliteral_fetch_targets(app_text)
    dynamic_targets = list(nonliteral_targets)

    for target in fetch_targets:
        if ("${" in target or "{" in target) and target not in dynamic_targets:
            dynamic_targets.append(target)

    dynamic_declarations = load_dynamic_payload_manifest(
        deploy_root, args.payload_manifest, errors, warnings
    )

    if not fetch_targets:
        warnings.append(
            "No literal fetch(), d3.csv(), or d3.json() targets detected in app.js"
        )

    for target in dynamic_targets:
        if target in dynamic_declarations:
            continue

        message = f"Dynamic target requires manual review: {target}"

        if args.strict:
            errors.append(message)
        else:
            warnings.append(message)

    for target in fetch_targets:
        target_value = local_target(target)

        if target_value is None:
            warnings.append(f"External target not checked: {target}")
            continue

        if "${" in target_value or "{" in target_value:
            continue

        payload_path = resolve_target(deploy_root, target_value)

        if not payload_path.is_file():
            errors.append(
                f"Fetch target missing: {target} -> {payload_path}"
            )
            continue

        validation_error = validate_payload(payload_path)

        if validation_error:
            errors.append(f"Invalid payload: {payload_path} ({validation_error})")

    entry_html = index_html
    html_text = index_html.read_text(encoding="utf-8", errors="replace")
    meta_refresh = re.search(META_REFRESH_PATTERN, html_text, flags=re.IGNORECASE)

    if meta_refresh:
        refresh_target = local_target(meta_refresh.group(1).strip())

        if refresh_target is None:
            warnings.append(
                "index.html redirects externally; entry-document assets were not checked"
            )
        else:
            redirect_path = resolve_target(deploy_root, refresh_target)

            if redirect_path.is_file():
                entry_html = redirect_path
                html_text = entry_html.read_text(encoding="utf-8", errors="replace")
            else:
                errors.append(
                    "index.html meta-refresh target missing: "
                    f"{meta_refresh.group(1).strip()} -> {redirect_path}"
                )

    if "app.js" not in html_text:
        warnings.append(
            f"{entry_html.name} has no literal app.js reference. "
            "Verify module or bundled script loading."
        )

    if "styles.css" not in html_text:
        warnings.append(
            f"{entry_html.name} has no literal styles.css reference. "
            "Verify stylesheet loading."
        )

    print(f"Deploy root: {deploy_root}")
    print(f"Static targets checked: {len(fetch_targets)}")

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("DEPLOY CONTRACT FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DEPLOY CONTRACT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
