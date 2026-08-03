#!/usr/bin/env python3
"""Validate static-board fetch targets and basic JSON/CSV payload integrity."""

from __future__ import annotations

import argparse
import csv
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
