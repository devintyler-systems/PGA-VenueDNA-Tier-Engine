#!/usr/bin/env python3
"""Validate active-event configuration and required inputs before a VenueDNA build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_MANIFEST_KEYS = (
    "schema_version",
    "status",
    "year",
    "event_slug",
    "event_name",
    "venue_slug",
    "venue_name",
    "event_root",
    "venue_profile",
    "deploy_root",
    "audit_root",
)

EVENT_BOUND_STATUSES = {
    "PRE_EVENT",
    "ROUND_1",
    "ROUND_2",
    "ROUND_3",
    "ROUND_4",
    "FINAL_AUDIT",
    "ARCHIVED",
}

VALID_STATUSES = {"NO_ACTIVE_EVENT", *EVENT_BOUND_STATUSES}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def as_repo_path(repo: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else repo / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Default: parent directory of tools/",
    )
    parser.add_argument(
        "--manifest",
        default="config/active_event.json",
        help="Manifest path relative to repository root",
    )
    parser.add_argument(
        "--phase",
        choices=("pre_event", "live", "audit"),
        default=None,
        help="Optional phase-specific validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing declared optional inputs as failures",
    )
    args = parser.parse_args()

    repo = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[1]
    )
    manifest_path = as_repo_path(repo, args.manifest)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        print("PREFLIGHT FAILED")
        print(f"- {exc}")
        return 1

    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            errors.append(f"Manifest missing required key: {key}")

    status = manifest.get("status")

    if status not in VALID_STATUSES:
        errors.append(
            f"Invalid status: {status!r}. "
            f"Allowed: {', '.join(sorted(VALID_STATUSES))}"
        )

    if status == "NO_ACTIVE_EVENT":
        if args.phase:
            errors.append(
                f"Cannot run {args.phase} validation while status is NO_ACTIVE_EVENT"
            )

        active_bindings = [
            key
            for key in ("event_slug", "event_root", "venue_profile")
            if manifest.get(key)
        ]

        if active_bindings:
            errors.append(
                "NO_ACTIVE_EVENT must not contain active bindings: "
                + ", ".join(active_bindings)
            )

    elif status in EVENT_BOUND_STATUSES:
        required_active_values = (
            "event_slug",
            "event_name",
            "venue_slug",
            "venue_name",
            "event_root",
            "venue_profile",
            "deploy_root",
            "audit_root",
        )

        for key in required_active_values:
            if not manifest.get(key):
                errors.append(f"{status} requires non-null field: {key}")

        event_slug = manifest.get("event_slug")
        venue_slug = manifest.get("venue_slug")
        event_root = manifest.get("event_root")
        deploy_root = manifest.get("deploy_root")

        expected_event_root = f"events/{event_slug}"
        if event_root and Path(event_root).as_posix().rstrip("/") != expected_event_root:
            errors.append(
                f"event_root must equal {expected_event_root}, got {event_root}"
            )

        expected_profile = (
            f"library/venues/{venue_slug}/{venue_slug}_venue_profile.md"
        )
        venue_profile = manifest.get("venue_profile")

        if venue_profile and Path(venue_profile).as_posix() != expected_profile:
            warnings.append(
                "venue_profile differs from standard convention: "
                f"expected {expected_profile}, got {venue_profile}"
            )

        required_directories = {
            "event_root": event_root,
            "input": f"{event_root}/input" if event_root else None,
            "output": f"{event_root}/output" if event_root else None,
            "deploy_root": deploy_root,
            "deploy_data": f"{deploy_root}/data" if deploy_root else None,
            "audit_root": manifest.get("audit_root"),
        }

        for label, value in required_directories.items():
            path = as_repo_path(repo, value)
            if not path or not path.is_dir():
                errors.append(f"Missing required directory [{label}]: {value}")

        profile_path = as_repo_path(repo, venue_profile)
        if not profile_path or not profile_path.is_file():
            errors.append(f"Missing canonical venue profile: {venue_profile}")

        if args.phase == "pre_event" and status != "PRE_EVENT":
            errors.append(
                f"--phase pre_event requires PRE_EVENT status, got {status}"
            )

        if args.phase == "live" and status not in {
            "ROUND_1",
            "ROUND_2",
            "ROUND_3",
            "ROUND_4",
        }:
            errors.append(
                f"--phase live requires ROUND_1 through ROUND_4 status, got {status}"
            )

        if args.phase == "audit" and status != "FINAL_AUDIT":
            errors.append(
                f"--phase audit requires FINAL_AUDIT status, got {status}"
            )

        if status in {
            "ROUND_1",
            "ROUND_2",
            "ROUND_3",
            "ROUND_4",
            "FINAL_AUDIT",
        }:
            pre_event_artifact = manifest.get("pre_event_artifact")

            if not pre_event_artifact:
                errors.append(
                    f"{status} requires a non-null pre_event_artifact"
                )
            else:
                pre_event_path = as_repo_path(repo, pre_event_artifact)
                if not pre_event_path or not pre_event_path.is_file():
                    errors.append(
                        "Missing immutable pre-event artifact: "
                        f"{pre_event_artifact}"
                    )

        if status in {"ROUND_1", "ROUND_2", "ROUND_3", "ROUND_4"}:
            expected_round = int(status[-1])
            live_round = manifest.get("live_round")

            if live_round != expected_round:
                errors.append(
                    f"{status} requires live_round={expected_round}, got {live_round!r}"
                )

        declared_sources = (
            "event_context_file",
            "field_file",
            "weather_file",
            "tee_times_file",
        )

        for key in declared_sources:
            value = manifest.get(key)

            if not value:
                continue

            source_path = as_repo_path(repo, value)

            if not source_path or not source_path.is_file():
                message = f"Declared source file does not exist [{key}]: {value}"

                if args.strict:
                    errors.append(message)
                else:
                    warnings.append(message)

    print(f"Repository: {repo}")
    print(f"Manifest: {manifest_path}")
    print(f"Status: {status}")

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("PREFLIGHT FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PREFLIGHT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())