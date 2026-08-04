"""Focused coverage for the schema-1.1 external deploy-profile validator."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "tools" / "validate_deploy_contract.py"

sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_deploy_contract as vdc  # noqa: E402


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DeployProfileFixture:
    """Builds a minimal, valid static_app deploy tree + schema-1.1 profile."""

    INDEX_HTML = '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>'
    STYLES_CSS = "body { color: #111; }"
    APP_JS = (
        "async function loadRound(r) {\n"
        "  await fetch('data/summary.json');\n"
        "  return fetch(`data/r${r}_analysis.json`);\n"
        "}\n"
    )
    R1_JSON = '{"round": 1}'
    SUMMARY_JSON = '{"summary": true}'

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.deploy_root = repo_root / "deploy"
        self.data_dir = self.deploy_root / "data"

    def build(self) -> dict:
        self.data_dir.mkdir(parents=True)
        (self.deploy_root / "index.html").write_bytes(self.INDEX_HTML.encode("utf-8"))
        (self.deploy_root / "styles.css").write_bytes(self.STYLES_CSS.encode("utf-8"))
        (self.deploy_root / "app.js").write_bytes(self.APP_JS.encode("utf-8"))
        (self.data_dir / "r1_analysis.json").write_bytes(self.R1_JSON.encode("utf-8"))
        (self.data_dir / "summary.json").write_bytes(self.SUMMARY_JSON.encode("utf-8"))

        integrity_files = [
            {"path": "index.html", "sha256": sha256_text(self.INDEX_HTML)},
            {"path": "app.js", "sha256": sha256_text(self.APP_JS)},
            {"path": "styles.css", "sha256": sha256_text(self.STYLES_CSS)},
            {"path": "data/summary.json", "sha256": sha256_text(self.SUMMARY_JSON)},
            {"path": "data/r1_analysis.json", "sha256": sha256_text(self.R1_JSON)},
        ]

        return {
            "schema_version": "1.1",
            "profile_type": "archived_deploy",
            "event_slug": "2026_example",
            "deploy_root": "deploy",
            "board": {
                "mode": "static_app",
                "entry_html": "index.html",
                "scripts": ["app.js"],
                "stylesheets": ["styles.css"],
                "data_roots": ["data"],
            },
            "dynamic_fetches": [
                {
                    "expression": "data/r${r}_analysis.json",
                    "pattern": "data/r{r}_analysis.json",
                    "targets": [
                        {"path": "data/r1_analysis.json", "availability": "required"},
                        {"path": "data/r3_analysis.json", "availability": "optional_pending"},
                    ],
                }
            ],
            "integrity": {"algorithm": "sha256", "files": integrity_files},
        }


class HelperLevelTests(unittest.TestCase):
    def _run(self, profile: dict, repo_root: Path):
        profile_path = repo_root / "profile.json"
        return vdc.validate_deploy_profile(profile, profile_path, repo_root)

    # 1. Valid static-app profile.
    def test_valid_static_app_profile_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            errors, warnings, report = self._run(profile, repo_root)

        self.assertEqual(errors, [])
        self.assertIn("Board mode: static_app", report)
        self.assertIn("Required dynamic targets checked: 1", report)
        self.assertIn("Optional-pending targets present: 0", report)
        self.assertIn("Optional-pending targets absent: 1", report)
        self.assertIn("Hashes verified: 5", report)

    # 2. Valid harness profile with alternate asset names.
    def test_valid_harness_profile_with_alternate_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            deploy = repo_root / "deploy"
            data = deploy / "data"
            data.mkdir(parents=True)
            entry_html = '<script src="bundle.js"></script><link rel="stylesheet" href="theme.css">'
            bundle_js = "fetch('data/points.json');"
            theme_css = "body{}"
            points_json = "{}"
            (deploy / "board.htm").write_text(entry_html, encoding="utf-8")
            (deploy / "bundle.js").write_text(bundle_js, encoding="utf-8")
            (deploy / "theme.css").write_text(theme_css, encoding="utf-8")
            (data / "points.json").write_text(points_json, encoding="utf-8")

            profile = {
                "schema_version": "1.1",
                "profile_type": "archived_deploy",
                "event_slug": "2026_example",
                "deploy_root": "deploy",
                "board": {
                    "mode": "harness",
                    "entry_html": "board.htm",
                    "scripts": ["bundle.js"],
                    "stylesheets": ["theme.css"],
                    "data_roots": ["data"],
                },
                "dynamic_fetches": [],
                "integrity": {
                    "algorithm": "sha256",
                    "files": [
                        {"path": "board.htm", "sha256": sha256_text(entry_html)},
                        {"path": "bundle.js", "sha256": sha256_text(bundle_js)},
                        {"path": "theme.css", "sha256": sha256_text(theme_css)},
                        {"path": "data/points.json", "sha256": sha256_text(points_json)},
                    ],
                },
            }
            errors, warnings, report = self._run(profile, repo_root)

        self.assertEqual(errors, [])
        self.assertIn("Board mode: harness", report)

    # 3. Valid inline-styled profile with no stylesheet.
    def test_valid_inline_styled_profile_without_stylesheet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            deploy = repo_root / "deploy"
            data = deploy / "data"
            data.mkdir(parents=True)
            entry_html = "<style>body{}</style><script src=\"app.js\"></script>"
            app_js = "fetch('data/points.json');"
            points_json = "{}"
            (deploy / "index.html").write_text(entry_html, encoding="utf-8")
            (deploy / "app.js").write_text(app_js, encoding="utf-8")
            (data / "points.json").write_text(points_json, encoding="utf-8")

            profile = {
                "schema_version": "1.1",
                "profile_type": "archived_deploy",
                "event_slug": "2026_example",
                "deploy_root": "deploy",
                "board": {
                    "mode": "inline_styled_app",
                    "entry_html": "index.html",
                    "scripts": ["app.js"],
                    "stylesheets": [],
                    "data_roots": ["data"],
                },
                "dynamic_fetches": [],
                "integrity": {
                    "algorithm": "sha256",
                    "files": [
                        {"path": "index.html", "sha256": sha256_text(entry_html)},
                        {"path": "app.js", "sha256": sha256_text(app_js)},
                        {"path": "data/points.json", "sha256": sha256_text(points_json)},
                    ],
                },
            }
            errors, warnings, report = self._run(profile, repo_root)

        self.assertEqual(errors, [])
        self.assertIn("Stylesheets checked: 0", report)

    # 4. Unknown mode.
    def test_unknown_mode_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["board"]["mode"] = "custom_mode"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("board.mode is unsupported" in error for error in errors))

    # 5. Missing entry.
    def test_missing_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            (repo_root / "deploy" / "index.html").unlink()
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("entry document missing" in error for error in errors))

    # 6. Missing script.
    def test_missing_script_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            (repo_root / "deploy" / "app.js").unlink()
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("scripts file missing" in error for error in errors))

    # 7. Missing required stylesheet.
    def test_missing_required_stylesheet_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            (repo_root / "deploy" / "styles.css").unlink()
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("stylesheets file missing" in error for error in errors))

    # 8. Missing data root.
    def test_missing_data_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["board"]["data_roots"] = ["nonexistent"]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("data_roots directory missing" in error for error in errors))

    # 9. Unsafe deploy root.
    def test_unsafe_deploy_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["deploy_root"] = "../outside"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("deploy_root is unsafe" in error for error in errors))

    def test_deploy_root_outside_repo_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["deploy_root"] = "C:/deploy"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("deploy_root is unsafe" in error for error in errors))

    # 10. Unsafe runtime paths.
    def test_unsafe_runtime_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["board"]["scripts"] = ["../outside.js"]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("scripts path is unsafe" in error for error in errors))

    def test_unsafe_runtime_path_absolute_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["board"]["scripts"] = ["/app.js"]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("scripts path is unsafe" in error for error in errors))

    # 11. Correct hash.
    def test_correct_hash_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            errors, _, report = self._run(profile, repo_root)

        self.assertEqual(errors, [])
        self.assertIn("Hashes verified: 5", report)

    # 12. Hash mismatch.
    def test_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["files"][0]["sha256"] = "0" * 64
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("Hash mismatch" in error for error in errors))

    # 13. Invalid digest.
    def test_invalid_digest_format_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["files"][0]["sha256"] = "ABCDEF"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("64 lowercase hexadecimal" in error for error in errors))

    # 14. Duplicate integrity path.
    def test_duplicate_integrity_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["files"].append(dict(profile["integrity"]["files"][0]))
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("duplicates integrity path" in error for error in errors))

    # 15. Missing mandatory integrity coverage.
    def test_missing_integrity_coverage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["files"] = [
                entry
                for entry in profile["integrity"]["files"]
                if entry["path"] != "styles.css"
            ]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(
            any("Missing mandatory integrity coverage: styles.css" in error for error in errors)
        )

    # 16. Literal local fetch coverage.
    def test_literal_local_fetch_missing_coverage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["files"] = [
                entry
                for entry in profile["integrity"]["files"]
                if entry["path"] != "data/summary.json"
            ]
            errors, _, report = self._run(profile, repo_root)

        self.assertIn("Literal local targets checked: 1", report)
        self.assertTrue(
            any(
                "Missing mandatory integrity coverage: data/summary.json" in error
                for error in errors
            )
        )

    # 17. Missing required dynamic target.
    def test_missing_required_dynamic_target_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            (repo_root / "deploy" / "data" / "r1_analysis.json").unlink()
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("Required dynamic target missing" in error for error in errors))

    # 18. Missing optional-pending target passes and is reported.
    def test_missing_optional_pending_target_passes_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            errors, _, report = self._run(profile, repo_root)

        self.assertEqual(errors, [])
        self.assertIn("Optional-pending targets absent: 1", report)
        self.assertIn("Optional-pending targets present: 0", report)

    # 19. Invalid present optional target.
    def test_invalid_present_optional_target_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            bad_json = "{not valid json"
            (repo_root / "deploy" / "data" / "r3_analysis.json").write_text(
                bad_json, encoding="utf-8"
            )
            profile["integrity"]["files"].append(
                {"path": "data/r3_analysis.json", "sha256": sha256_text(bad_json)}
            )
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(
            any("Invalid optional-pending dynamic target" in error for error in errors)
        )

    # 20. Present optional hash mismatch.
    def test_present_optional_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            good_json = "{}"
            (repo_root / "deploy" / "data" / "r3_analysis.json").write_text(
                good_json, encoding="utf-8"
            )
            profile["integrity"]["files"].append(
                {"path": "data/r3_analysis.json", "sha256": "1" * 64}
            )
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("Hash mismatch for data/r3_analysis.json" in error for error in errors))

    # 21. Unknown availability.
    def test_unknown_availability_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"][0]["targets"][0]["availability"] = "sometimes"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("unknown availability" in error for error in errors))

    # 22. Duplicate expression.
    def test_duplicate_expression_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"].append(copy.deepcopy(profile["dynamic_fetches"][0]))
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("duplicates expression" in error for error in errors))

    # 23. Duplicate target path.
    def test_duplicate_target_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"][0]["targets"].append(
                {"path": "data/r1_analysis.json", "availability": "optional_pending"}
            )
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("duplicates target path" in error for error in errors))

    def test_duplicate_target_path_across_declarations_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"].append(
                {
                    "expression": "url",
                    "pattern": "data/r{r}_analysis.json",
                    "targets": [
                        {"path": "data/r1_analysis.json", "availability": "required"}
                    ],
                }
            )
            (repo_root / "deploy" / "app.js").write_text(
                DeployProfileFixture.APP_JS + "\nfetch(url);", encoding="utf-8"
            )
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("across dynamic declarations" in error for error in errors))

    def test_extra_integrity_entry_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            (repo_root / "deploy" / "extra.txt").write_text("extra", encoding="utf-8")
            profile["integrity"]["files"].append(
                {"path": "extra.txt", "sha256": "0" * 64}
            )
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("Hash mismatch for extra.txt" in error for error in errors))

    # 24. Pattern mismatch.
    def test_pattern_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"][0]["targets"][0]["path"] = "data/other_file.json"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("does not match pattern" in error for error in errors))

    # 25. Undeclared detected expression.
    def test_undeclared_detected_expression_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"] = []
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(
            any("Undeclared dynamic expression detected in scripts" in error for error in errors)
        )

    # 26. Declared expression absent from scripts.
    def test_declared_expression_absent_from_scripts_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["dynamic_fetches"][0]["expression"] = "data/never_used_${x}.json"
            profile["dynamic_fetches"][0]["pattern"] = "data/never_used_{x}.json"
            profile["dynamic_fetches"][0]["targets"] = [
                {"path": "data/never_used_1.json", "availability": "optional_pending"}
            ]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(
            any(
                "Declared dynamic expression not found in any declared script" in error
                for error in errors
            )
        )
        self.assertTrue(
            any("Undeclared dynamic expression detected in scripts" in error for error in errors)
        )

    # Additional field/schema coverage.
    def test_wrong_schema_version_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["schema_version"] = "1.0"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("schema_version must be" in error for error in errors))

    def test_wrong_profile_type_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["profile_type"] = "live_deploy"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("profile_type must be" in error for error in errors))

    def test_wrong_integrity_algorithm_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile["integrity"]["algorithm"] = "md5"
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("integrity.algorithm must be" in error for error in errors))

    def test_missing_top_level_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            del profile["event_slug"]
            errors, _, _ = self._run(profile, repo_root)

        self.assertTrue(any("missing required field: event_slug" in error for error in errors))

    # 30. Validation does not rewrite files.
    def test_validation_does_not_rewrite_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()

            deploy = repo_root / "deploy"
            before = {
                path: path.read_bytes()
                for path in deploy.rglob("*")
                if path.is_file()
            }
            before_mtimes = {path: path.stat().st_mtime_ns for path in before}

            self._run(profile, repo_root)

            after = {path: path.read_bytes() for path in deploy.rglob("*") if path.is_file()}
            after_mtimes = {path: path.stat().st_mtime_ns for path in after}

        self.assertEqual(before, after)
        self.assertEqual(before_mtimes, after_mtimes)


class CliLevelTests(unittest.TestCase):
    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_valid_profile_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile_path = repo_root / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run_cli(
                [
                    "--repo-root",
                    str(repo_root),
                    "--deploy-profile",
                    "profile.json",
                ]
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DEPLOY PROFILE PASSED", result.stdout)

    # 27. CLI argument conflicts.
    def test_cli_deploy_profile_and_deploy_root_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile_path = repo_root / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run_cli(
                [
                    "--repo-root",
                    str(repo_root),
                    "--deploy-profile",
                    "profile.json",
                    "--deploy-root",
                    "deploy",
                ]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("mutually exclusive", result.stdout)

    def test_cli_deploy_profile_and_payload_manifest_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            profile = DeployProfileFixture(repo_root).build()
            profile_path = repo_root / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = self._run_cli(
                [
                    "--repo-root",
                    str(repo_root),
                    "--deploy-profile",
                    "profile.json",
                    "--payload-manifest",
                    "payload_manifest.json",
                ]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("mutually exclusive", result.stdout)

    def test_cli_profile_path_outside_repo_fails(self) -> None:
        with tempfile.TemporaryDirectory() as outer_directory:
            outer = Path(outer_directory)
            repo_root = outer / "repo"
            repo_root.mkdir()
            outside_profile = outer / "outside_profile.json"
            outside_profile.write_text("{}", encoding="utf-8")

            result = self._run_cli(
                [
                    "--repo-root",
                    str(repo_root),
                    "--deploy-profile",
                    "../outside_profile.json",
                ]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("must resolve inside the repository", result.stdout)

    # 28. Legacy deploy-root behavior.
    def test_legacy_deploy_root_behavior_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            deploy = repo_root / "deploy"
            data = deploy / "data"
            data.mkdir(parents=True)
            (deploy / "index.html").write_text(
                '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>',
                encoding="utf-8",
            )
            (deploy / "styles.css").write_text("body {}", encoding="utf-8")
            (deploy / "app.js").write_text(
                "fetch('data/summary.json');", encoding="utf-8"
            )
            (data / "summary.json").write_text("{}", encoding="utf-8")

            result = self._run_cli(["--deploy-root", str(deploy)])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DEPLOY CONTRACT PASSED", result.stdout)

    # 29. Legacy schema-1.0 manifest behavior.
    def test_legacy_schema_1_0_manifest_behavior_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            deploy = repo_root / "deploy"
            data = deploy / "data"
            data.mkdir(parents=True)
            (deploy / "index.html").write_text(
                '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>',
                encoding="utf-8",
            )
            (deploy / "styles.css").write_text("body {}", encoding="utf-8")
            (deploy / "app.js").write_text(
                "fetch(`data/r${r}_analysis.json`);", encoding="utf-8"
            )
            (data / "r1_analysis.json").write_text("{}", encoding="utf-8")

            (deploy / "payload_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "dynamic_fetches": [
                            {
                                "expression": "data/r${r}_analysis.json",
                                "pattern": "data/r{r}_analysis.json",
                                "expected_files": ["data/r1_analysis.json"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run_cli(["--deploy-root", str(deploy), "--strict"])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DEPLOY CONTRACT PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
