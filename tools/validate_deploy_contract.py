#!/usr/bin/env python3
"""Validate static-board fetch targets and basic JSON/CSV payload integrity."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

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


def local_target(target: str) -> str | None:
    clean_target = target.split("?", 1)[0].split("#", 1)[0]

    if clean_target.startswith(("http://", "https://", "//", "data:")):
        return None

    return clean_target


def resolve_target(deploy_root: Path, target: str) -> Path:
    if target.startswith("/"):
        return deploy_root / target.lstrip("/")

    return deploy_root / target


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

    if not fetch_targets:
        warnings.append(
            "No literal fetch(), d3.csv(), or d3.json() targets detected in app.js"
        )

    for target in fetch_targets:
        target_value = local_target(target)

        if target_value is None:
            warnings.append(f"External target not checked: {target}")
            continue

        if "${" in target_value or "{" in target_value:
            message = f"Dynamic target requires manual review: {target}"

            if args.strict:
                errors.append(message)
            else:
                warnings.append(message)

            continue

        payload_path = resolve_target(deploy_root, target_value)

        if not payload_path.is_file():
            errors.append(
                f"Fetch target missing: {target} -> {payload_path}"
            )
            continue

        suffix = payload_path.suffix.lower()

        if suffix == ".json":
            validation_error = validate_json(payload_path)

            if validation_error:
                errors.append(
                    f"Invalid JSON payload: {payload_path} ({validation_error})"
                )

        elif suffix == ".csv":
            validation_error = validate_csv(payload_path)

            if validation_error:
                errors.append(
                    f"Invalid CSV payload: {payload_path} ({validation_error})"
                )

    html_text = index_html.read_text(encoding="utf-8", errors="replace")

    if "app.js" not in html_text:
        warnings.append(
            "index.html has no literal app.js reference. "
            "Verify module or bundled script loading."
        )

    if "styles.css" not in html_text:
        warnings.append(
            "index.html has no literal styles.css reference. "
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