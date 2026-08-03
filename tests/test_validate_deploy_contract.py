"""Focused CLI coverage for dynamic deploy payload manifests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "tools" / "validate_deploy_contract.py"


class DynamicPayloadManifestTests(unittest.TestCase):
    def make_deploy(
        self, root: Path, manifest: bool, missing_expected_file: bool = False
    ) -> Path:
        deploy = root / "deploy"
        data = deploy / "data"
        data.mkdir(parents=True)
        (deploy / "index.html").write_text(
            '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>',
            encoding="utf-8",
        )
        (deploy / "styles.css").write_text("body {}", encoding="utf-8")
        (deploy / "app.js").write_text(
            "async function load(round) { return fetch(`data/r${round}_analysis.json`); }",
            encoding="utf-8",
        )
        (data / "r1_analysis.json").write_text("{}", encoding="utf-8")

        if not missing_expected_file:
            (data / "r2_analysis.json").write_text("{}", encoding="utf-8")

        if manifest:
            (deploy / "payload_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "dynamic_fetches": [
                            {
                                "expression": "data/r${round}_analysis.json",
                                "pattern": "data/r{round}_analysis.json",
                                "expected_files": [
                                    "data/r1_analysis.json",
                                    "data/r2_analysis.json",
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

        return deploy

    def validate_strict(self, deploy: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--deploy-root", str(deploy), "--strict"],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_dynamic_fetch_without_manifest_fails_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.validate_strict(self.make_deploy(Path(directory), manifest=False))

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic target requires manual review", result.stdout)

    def test_declared_dynamic_fetch_with_all_files_passes_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.validate_strict(self.make_deploy(Path(directory), manifest=True))

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DEPLOY CONTRACT PASSED", result.stdout)

    def test_declared_dynamic_fetch_with_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.validate_strict(
                self.make_deploy(Path(directory), manifest=True, missing_expected_file=True)
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Declared dynamic payload missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
