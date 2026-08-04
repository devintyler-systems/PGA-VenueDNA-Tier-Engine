"""Focused coverage for the deterministic schema-1.1 deploy-profile builder."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER = REPO_ROOT / "tools" / "build_deploy_profile.py"

sys.path.insert(0, str(REPO_ROOT / "tools"))

import build_deploy_profile as bdp  # noqa: E402
import validate_deploy_contract as vdc  # noqa: E402


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RepoFixture:
    """A minimal fake repository root for builder tests (temp dirs only)."""

    INDEX_HTML = '<link rel="stylesheet" href="styles.css"><script src="app.js"></script>'
    STYLES_CSS = "body { color: #111; }"
    STATIC_APP_JS = "async function load() {\n  return fetch('data/summary.json');\n}\n"
    DYNAMIC_APP_JS = (
        "async function loadRound(r) {\n"
        "  await fetch('data/summary.json');\n"
        "  return fetch(`data/r${r}_analysis.json`);\n"
        "}\n"
    )
    SUMMARY_JSON = '{"summary": true}'
    R1_JSON = '{"round": 1}'
    R1_CSV = "player_id,score\n1,70\n"

    def __init__(self, tmp_root: Path) -> None:
        self.repo = tmp_root
        self.deploy_root = tmp_root / "deploy"
        self.data_dir = self.deploy_root / "data"

    def write_static_tree(self, app_js: str | None = None) -> None:
        self.data_dir.mkdir(parents=True)
        (self.deploy_root / "index.html").write_bytes(self.INDEX_HTML.encode("utf-8"))
        (self.deploy_root / "styles.css").write_bytes(self.STYLES_CSS.encode("utf-8"))
        (self.deploy_root / "app.js").write_bytes(
            (app_js if app_js is not None else self.STATIC_APP_JS).encode("utf-8")
        )
        (self.data_dir / "summary.json").write_bytes(self.SUMMARY_JSON.encode("utf-8"))

    def output_path(self, name: str = "2026_example.json") -> Path:
        return self.repo / "config" / "deploy_contracts" / "archived" / name

    def archive_output_path(self) -> Path:
        return self.repo / "events" / "2026_Finished_Events" / "2026_example" / "sneaky.json"

    def build_kwargs(self, **overrides: object) -> dict:
        kwargs = dict(
            repo=self.repo,
            deploy_root_arg="deploy",
            output_arg=str(
                self.output_path().relative_to(self.repo).as_posix()
            ),
            event_slug="2026_example",
            board_mode="static_app",
            entry_html="index.html",
            scripts=["app.js"],
            stylesheets=["styles.css"],
            data_roots=["data"],
            dynamic_declarations_arg=None,
        )
        kwargs.update(overrides)
        return kwargs


def snapshot_tree(root: Path) -> dict[str, tuple[bytes, float]]:
    snapshot = {}

    for path in root.rglob("*"):
        if path.is_file():
            stat = path.stat()
            snapshot[str(path)] = (path.read_bytes(), stat.st_mtime_ns)

    return snapshot


class HelperLevelTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fixture = RepoFixture(Path(self._tmp.name))

    # 1. Static-app generation.
    def test_static_app_generation_succeeds(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(result.errors, [], result.errors)
        self.assertIsNotNone(result.profile)
        self.assertEqual(result.profile["board"]["mode"], "static_app")
        self.assertEqual(result.profile["schema_version"], "1.1")
        self.assertEqual(result.profile["profile_type"], "archived_deploy")

    # 2. Harness generation with alternate filenames.
    def test_harness_alternate_filenames_succeeds(self) -> None:
        deploy = self.fixture.deploy_root
        data_dir = deploy / "assets"
        data_dir.mkdir(parents=True)
        (deploy / "board.html").write_bytes(self.fixture.INDEX_HTML.encode("utf-8"))
        (deploy / "board.css").write_bytes(self.fixture.STYLES_CSS.encode("utf-8"))
        (deploy / "board.js").write_bytes(
            b"async function load() { return fetch('assets/summary.json'); }\n"
        )
        (data_dir / "summary.json").write_bytes(self.fixture.SUMMARY_JSON.encode("utf-8"))

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                board_mode="harness",
                entry_html="board.html",
                scripts=["board.js"],
                stylesheets=["board.css"],
                data_roots=["assets"],
            )
        )

        self.assertEqual(result.errors, [], result.errors)
        self.assertEqual(result.profile["board"]["mode"], "harness")
        self.assertEqual(result.profile["board"]["entry_html"], "board.html")

    # 3. Inline-styled generation without stylesheet.
    def test_inline_styled_without_stylesheet_succeeds(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(board_mode="inline_styled_app", stylesheets=[])
        )

        self.assertEqual(result.errors, [], result.errors)
        self.assertEqual(result.profile["board"]["stylesheets"], [])

    # 4. Unknown mode failure.
    def test_unknown_board_mode_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs(board_mode="bogus_mode"))

        self.assertIsNone(result.profile)
        self.assertTrue(any("Unsupported board mode" in e for e in result.errors))

    # 5. Missing entry failure.
    def test_missing_entry_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(entry_html="missing.html")
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("entry_html file missing" in e for e in result.errors))

    # 6. Missing script failure.
    def test_missing_script_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(scripts=["missing.js"])
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("scripts file missing" in e for e in result.errors))

    # 7. Missing required stylesheet failure.
    def test_missing_stylesheet_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(stylesheets=["missing.css"])
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("stylesheets file missing" in e for e in result.errors))

    # 8. Missing data root failure.
    def test_missing_data_root_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(data_roots=["missing_dir"])
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("data_roots directory missing" in e for e in result.errors))

    # 9. Output inside archive rejected.
    def test_output_inside_archive_rejected(self) -> None:
        self.fixture.write_static_tree()
        archive_out = self.fixture.archive_output_path()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                output_arg=archive_out.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("archive directory" in e for e in result.errors))

    # 10. Output inside deploy root rejected.
    def test_output_inside_deploy_root_rejected(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(output_arg="deploy/profile.json")
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("declared deploy root" in e for e in result.errors))

    # 11. Deploy root outside repository rejected.
    def test_deploy_root_outside_repository_rejected(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(deploy_root_arg="../outside_deploy")
        )

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("Deploy root must resolve inside the repository" in e for e in result.errors)
        )

    # 12. Output outside repository rejected.
    def test_output_outside_repository_rejected(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(output_arg="../outside_output.json")
        )

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("Output must resolve inside the repository" in e for e in result.errors)
        )

    # 13. Unsafe runtime path rejected.
    def test_unsafe_runtime_path_rejected(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(scripts=["../app.js"])
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("path is unsafe" in e for e in result.errors))

    # 14. Literal local JSON included and hashed.
    def test_literal_local_json_hashed(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(result.errors, [], result.errors)
        paths = {entry["path"] for entry in result.profile["integrity"]["files"]}
        self.assertIn("data/summary.json", paths)

        digest = next(
            e["sha256"] for e in result.profile["integrity"]["files"]
            if e["path"] == "data/summary.json"
        )
        self.assertEqual(digest, sha256_text(self.fixture.SUMMARY_JSON))

    # 15. Literal local CSV included and validated.
    def test_literal_local_csv_hashed(self) -> None:
        self.fixture.write_static_tree(
            app_js="async function load() { return fetch('data/scores.csv'); }\n"
        )
        (self.fixture.data_dir / "scores.csv").write_bytes(self.fixture.R1_CSV.encode("utf-8"))

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(result.errors, [], result.errors)
        paths = {entry["path"] for entry in result.profile["integrity"]["files"]}
        self.assertIn("data/scores.csv", paths)

    # 16. Invalid literal JSON fails.
    def test_invalid_literal_json_fails(self) -> None:
        self.fixture.write_static_tree()
        (self.fixture.data_dir / "summary.json").write_bytes(b"{not valid json")

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertIsNone(result.profile)
        self.assertTrue(any("Invalid literal fetch target" in e for e in result.errors))

    # 17. Headerless CSV fails.
    def test_headerless_csv_fails(self) -> None:
        self.fixture.write_static_tree(
            app_js="async function load() { return fetch('data/scores.csv'); }\n"
        )
        (self.fixture.data_dir / "scores.csv").write_bytes(b"")

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertIsNone(result.profile)
        self.assertTrue(any("Invalid literal fetch target" in e for e in result.errors))

    # 18. External URL not hashed.
    def test_external_url_not_hashed(self) -> None:
        self.fixture.write_static_tree(
            app_js=(
                "async function load() {\n"
                "  await fetch('https://example.com/data.json');\n"
                "  return fetch('data/summary.json');\n"
                "}\n"
            )
        )

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(result.errors, [], result.errors)
        paths = {entry["path"] for entry in result.profile["integrity"]["files"]}
        self.assertNotIn("https://example.com/data.json", paths)

    # 19. Dynamic expression without declarations fails.
    def test_dynamic_expression_without_declarations_fails(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(
            self.fixture.R1_JSON.encode("utf-8")
        )

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("Dynamic fetch expressions detected" in e for e in result.errors)
        )

    def _write_declarations(self, missing_required: bool = False, r3_present: bool = False) -> Path:
        decl_path = self.fixture.repo / "dynamic_declarations.json"
        targets = [
            {
                "path": "data/r1_analysis.json",
                "availability": "optional_pending" if missing_required else "required",
            },
            {"path": "data/r3_analysis.json", "availability": "optional_pending"},
        ]
        decl_path.write_bytes(
            json.dumps(
                {
                    "dynamic_fetches": [
                        {
                            "expression": "data/r${r}_analysis.json",
                            "pattern": "data/r{r}_analysis.json",
                            "targets": targets,
                        }
                    ]
                }
            ).encode("utf-8")
        )

        if r3_present:
            (self.fixture.data_dir / "r3_analysis.json").write_bytes(b"{}")

        return decl_path

    # 20. Dynamic declarations reconcile successfully.
    def test_dynamic_declarations_reconcile_successfully(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(
            self.fixture.R1_JSON.encode("utf-8")
        )
        decl_path = self._write_declarations()

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertEqual(result.errors, [], result.errors)
        self.assertEqual(len(result.profile["dynamic_fetches"]), 1)

    # 21. Missing required dynamic target fails.
    def test_missing_required_dynamic_target_fails(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        # r1_analysis.json intentionally NOT written on disk.
        decl_path = self._write_declarations()

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertIsNone(result.profile)
        self.assertTrue(any("Required dynamic target missing" in e for e in result.errors))

    # 22. Missing optional-pending target succeeds and is not hashed.
    def test_missing_optional_pending_target_succeeds_not_hashed(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(
            self.fixture.R1_JSON.encode("utf-8")
        )
        # r3_analysis.json (optional_pending) intentionally absent.
        decl_path = self._write_declarations()

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertEqual(result.errors, [], result.errors)
        paths = {entry["path"] for entry in result.profile["integrity"]["files"]}
        self.assertNotIn("data/r3_analysis.json", paths)

    # 23. Present optional-pending target is hashed.
    def test_present_optional_pending_target_hashed(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(
            self.fixture.R1_JSON.encode("utf-8")
        )
        decl_path = self._write_declarations(r3_present=True)

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertEqual(result.errors, [], result.errors)
        paths = {entry["path"] for entry in result.profile["integrity"]["files"]}
        self.assertIn("data/r3_analysis.json", paths)

    # 24. Dynamic target outside data roots fails.
    def test_dynamic_target_outside_data_roots_fails(self) -> None:
        self.fixture.write_static_tree(
            app_js=(
                "async function loadRound(r) {\n"
                "  await fetch('data/summary.json');\n"
                "  return fetch(`other/r${r}_analysis.json`);\n"
                "}\n"
            )
        )
        decl_path = self.fixture.repo / "dynamic_declarations.json"
        decl_path.write_bytes(
            json.dumps(
                {
                    "dynamic_fetches": [
                        {
                            "expression": "other/r${r}_analysis.json",
                            "pattern": "other/r{r}_analysis.json",
                            "targets": [
                                {"path": "other/r1_analysis.json", "availability": "required"}
                            ],
                        }
                    ]
                }
            ).encode("utf-8")
        )
        other_dir = self.fixture.deploy_root / "other"
        other_dir.mkdir()
        (other_dir / "r1_analysis.json").write_bytes(b"{}")

        result = bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("not contained under any declared data root" in e for e in result.errors)
        )

    # 25. Literal target outside data roots fails.
    def test_literal_target_outside_data_roots_fails(self) -> None:
        self.fixture.write_static_tree(
            app_js="async function load() { return fetch('other/summary.json'); }\n"
        )
        other_dir = self.fixture.deploy_root / "other"
        other_dir.mkdir()
        (other_dir / "summary.json").write_bytes(b"{}")

        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("not contained under any declared data root" in e for e in result.errors)
        )

    # 26. Empty data roots accepted for a board with no local targets.
    def test_empty_data_roots_accepted_when_no_local_targets(self) -> None:
        deploy = self.fixture.deploy_root
        deploy.mkdir(parents=True)
        (deploy / "index.html").write_bytes(self.fixture.INDEX_HTML.encode("utf-8"))
        (deploy / "styles.css").write_bytes(self.fixture.STYLES_CSS.encode("utf-8"))
        (deploy / "app.js").write_bytes(b"console.log('no fetches here');\n")

        result = bdp.build_profile(**self.fixture.build_kwargs(data_roots=[]))

        self.assertEqual(result.errors, [], result.errors)
        self.assertEqual(result.profile["board"]["data_roots"], [])

    # 27. Empty data roots rejected when local targets exist.
    def test_empty_data_roots_rejected_when_local_targets_exist(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs(data_roots=[]))

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("no --data-root was declared" in e for e in result.errors)
        )

    # 28. Duplicate path across runtime categories fails.
    def test_duplicate_path_across_categories_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(
            **self.fixture.build_kwargs(stylesheets=["app.js"])
        )

        self.assertIsNone(result.profile)
        self.assertTrue(
            any("Duplicate path across runtime categories" in e for e in result.errors)
        )

    # 29. Integrity ordering deterministic.
    def test_integrity_ordering_deterministic(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(result.errors, [], result.errors)
        paths = [entry["path"] for entry in result.profile["integrity"]["files"]]
        self.assertEqual(paths, sorted(paths, key=vdc.normalize_relative))

    # 30. Repeated generation produces byte-identical output.
    def test_repeated_generation_byte_identical(self) -> None:
        self.fixture.write_static_tree()
        first = bdp.build_profile(**self.fixture.build_kwargs())
        second = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(first.errors, [])
        self.assertEqual(second.errors, [])
        self.assertEqual(
            bdp.render_profile_json(first.profile), bdp.render_profile_json(second.profile)
        )

    # 31. Dry run prints but writes nothing.
    def test_dry_run_prints_but_writes_nothing(self) -> None:
        self.fixture.write_static_tree()
        output = self.fixture.output_path()

        proc = subprocess.run(
            [
                sys.executable, str(BUILDER),
                "--repo-root", str(self.fixture.repo),
                "--deploy-root", "deploy",
                "--output", "config/deploy_contracts/archived/2026_example.json",
                "--event-slug", "2026_example",
                "--board-mode", "static_app",
                "--entry-html", "index.html",
                "--script", "app.js",
                "--stylesheet", "styles.css",
                "--data-root", "data",
                "--dry-run",
            ],
            check=False, capture_output=True, text=True,
        )

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"schema_version": "1.1"', proc.stdout)
        self.assertFalse(output.exists())

    # 32. Dry run creates no output parent.
    def test_dry_run_creates_no_output_parent(self) -> None:
        self.fixture.write_static_tree()
        output = self.fixture.output_path()

        subprocess.run(
            [
                sys.executable, str(BUILDER),
                "--repo-root", str(self.fixture.repo),
                "--deploy-root", "deploy",
                "--output", "config/deploy_contracts/archived/2026_example.json",
                "--event-slug", "2026_example",
                "--board-mode", "static_app",
                "--entry-html", "index.html",
                "--script", "app.js",
                "--stylesheet", "styles.css",
                "--data-root", "data",
                "--dry-run",
            ],
            check=False, capture_output=True, text=True,
        )

        self.assertFalse(output.parent.exists())

    # 33. Check succeeds for identical profile.
    def test_check_succeeds_for_identical_profile(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        output.write_bytes(bdp.render_profile_json(result.profile))

        second = bdp.build_profile(**self.fixture.build_kwargs())
        self.assertEqual(
            output.read_bytes(), bdp.render_profile_json(second.profile)
        )

    # 34. Check fails for stale profile.
    def test_check_fails_for_stale_profile(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        output.write_bytes(bdp.render_profile_json(result.profile))

        (self.fixture.data_dir / "summary.json").write_bytes(b'{"summary": false}')
        stale_check = bdp.build_profile(**self.fixture.build_kwargs())

        self.assertEqual(stale_check.errors, [])
        self.assertNotEqual(
            output.read_bytes(), bdp.render_profile_json(stale_check.profile)
        )

    # 35. Check writes nothing.
    def test_check_writes_nothing(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        rendered = bdp.render_profile_json(result.profile)
        output.write_bytes(rendered)
        before = output.stat().st_mtime_ns

        proc = subprocess.run(
            [
                sys.executable, str(BUILDER),
                "--repo-root", str(self.fixture.repo),
                "--deploy-root", "deploy",
                "--output", "config/deploy_contracts/archived/2026_example.json",
                "--event-slug", "2026_example",
                "--board-mode", "static_app",
                "--entry-html", "index.html",
                "--script", "app.js",
                "--stylesheet", "styles.css",
                "--data-root", "data",
                "--check",
            ],
            check=False, capture_output=True, text=True,
        )

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(output.read_bytes(), rendered)
        self.assertEqual(output.stat().st_mtime_ns, before)

    # 36. Failed validation leaves no output.
    def test_failed_validation_leaves_no_output(self) -> None:
        self.fixture.write_static_tree()
        output = self.fixture.output_path()

        proc = subprocess.run(
            [
                sys.executable, str(BUILDER),
                "--repo-root", str(self.fixture.repo),
                "--deploy-root", "deploy",
                "--output", "config/deploy_contracts/archived/2026_example.json",
                "--event-slug", "2026_example",
                "--board-mode", "static_app",
                "--entry-html", "index.html",
                "--script", "missing.js",
                "--stylesheet", "styles.css",
                "--data-root", "data",
            ],
            check=False, capture_output=True, text=True,
        )

        self.assertEqual(proc.returncode, 1)
        self.assertFalse(output.exists())

    # 37. Existing output remains unchanged when regeneration fails.
    def test_existing_output_unchanged_when_regeneration_fails(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        rendered = bdp.render_profile_json(result.profile)
        output.write_bytes(rendered)

        broken = bdp.build_profile(**self.fixture.build_kwargs(scripts=["missing.js"]))

        self.assertIsNone(broken.profile)
        self.assertEqual(output.read_bytes(), rendered)

    # 38. Dynamic declarations input remains unchanged.
    def test_dynamic_declarations_input_unchanged(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS)
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(
            self.fixture.R1_JSON.encode("utf-8")
        )
        decl_path = self._write_declarations()
        before = decl_path.read_bytes()
        before_mtime = decl_path.stat().st_mtime_ns

        bdp.build_profile(
            **self.fixture.build_kwargs(
                dynamic_declarations_arg=decl_path.relative_to(self.fixture.repo).as_posix()
            )
        )

        self.assertEqual(decl_path.read_bytes(), before)
        self.assertEqual(decl_path.stat().st_mtime_ns, before_mtime)

    def test_dynamic_declaration_order_does_not_change_rendered_profile(self) -> None:
        self.fixture.write_static_tree(app_js=self.fixture.DYNAMIC_APP_JS + "\nfetch(url);")
        (self.fixture.data_dir / "r1_analysis.json").write_bytes(self.fixture.R1_JSON.encode("utf-8"))
        first = self._write_declarations()
        data = json.loads(first.read_text(encoding="utf-8"))
        data["dynamic_fetches"].append(
            {"expression": "url", "pattern": "data/r{r}_analysis.json", "targets": [
                {"availability": "optional_pending", "path": "data/r4_analysis.json"}
            ]}
        )
        first.write_text(json.dumps(data), encoding="utf-8")
        second = self.fixture.repo / "declarations_reordered.json"
        second.write_text(json.dumps({"dynamic_fetches": list(reversed(data["dynamic_fetches"]))}), encoding="utf-8")
        first_result = bdp.build_profile(**self.fixture.build_kwargs(dynamic_declarations_arg=first.relative_to(self.fixture.repo).as_posix()))
        second_result = bdp.build_profile(**self.fixture.build_kwargs(dynamic_declarations_arg=second.relative_to(self.fixture.repo).as_posix()))
        self.assertEqual(first_result.errors, [])
        self.assertEqual(second_result.errors, [])
        self.assertEqual(bdp.render_profile_json(first_result.profile), bdp.render_profile_json(second_result.profile))

    # 39. Deploy files remain byte- and mtime-identical.
    def test_deploy_files_unchanged(self) -> None:
        self.fixture.write_static_tree()
        before = snapshot_tree(self.fixture.deploy_root)

        bdp.build_profile(**self.fixture.build_kwargs())

        after = snapshot_tree(self.fixture.deploy_root)
        self.assertEqual(before, after)

    # 40. Generated output passes validate_deploy_profile().
    def test_generated_output_passes_validator(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        output.write_bytes(bdp.render_profile_json(result.profile))

        loaded = vdc.load_deploy_profile(output)
        errors, _warnings, _report = vdc.validate_deploy_profile(
            loaded, output, self.fixture.repo
        )
        self.assertEqual(errors, [])

    # Extra: normal-mode write produces a byte-identical file to render_profile_json.
    def test_normal_write_matches_rendered_bytes(self) -> None:
        self.fixture.write_static_tree()
        result = bdp.build_profile(**self.fixture.build_kwargs())
        output = self.fixture.output_path()
        output.parent.mkdir(parents=True)
        bdp.write_profile_atomic(output, bdp.render_profile_json(result.profile))

        self.assertEqual(output.read_bytes(), bdp.render_profile_json(result.profile))
        self.assertEqual(list(output.parent.glob("*.tmp")), [])


class CliLevelTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fixture = RepoFixture(Path(self._tmp.name))

    def _run(self, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, str(BUILDER),
                "--repo-root", str(self.fixture.repo),
                "--deploy-root", "deploy",
                "--output", "config/deploy_contracts/archived/2026_example.json",
                "--event-slug", "2026_example",
                "--board-mode", "static_app",
                "--entry-html", "index.html",
                "--script", "app.js",
                "--stylesheet", "styles.css",
                "--data-root", "data",
                *extra_args,
            ],
            check=False, capture_output=True, text=True,
        )

    def test_cli_normal_write_succeeds(self) -> None:
        self.fixture.write_static_tree()
        proc = self._run()

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        output = self.fixture.output_path()
        self.assertTrue(output.is_file())
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "1.1")

    def test_cli_dry_run_and_check_mutually_exclusive(self) -> None:
        self.fixture.write_static_tree()
        proc = self._run("--dry-run", "--check")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("mutually exclusive", proc.stdout)

    def test_cli_help(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(BUILDER), "--help"],
            check=False, capture_output=True, text=True,
        )

        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("--deploy-profile", proc.stdout)
        self.assertIn("--dry-run", proc.stdout)
        self.assertIn("--check", proc.stdout)


if __name__ == "__main__":
    unittest.main()
