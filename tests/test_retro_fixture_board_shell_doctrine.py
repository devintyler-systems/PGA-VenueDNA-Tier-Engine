"""tests/test_retro_fixture_board_shell_doctrine.py
Focused coverage for the Phase 6.3 fenced retrospective board-shell
allowance in tools/validate_scoring_doctrine.py.

Phase 6.3 permits exactly three local, non-deployable board-shell files
(index.html, app.js, styles.css) as direct children of
events/2026_wyndham_championship/deploy/, alongside the pre-existing
required empty deploy/data/ directory. It does not create, permit, or widen
any deploy payload, official artifact, live artifact, or publication marker.

Every test operates on a tmp_path-constructed synthetic repository copy. No
test writes an actual board-shell file into the committed
events/2026_wyndham_championship/ fixture, and no test touches
config/active_event.json outside its own tmp_path copy.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_scoring_doctrine.py"

_SPEC = importlib.util.spec_from_file_location("validate_scoring_doctrine", VALIDATOR_PATH)
assert _SPEC is not None and _SPEC.loader is not None
validator = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = validator
_SPEC.loader.exec_module(validator)


FIXTURE_FILES = (
    "standards/02_PGA_VENUEDNA_SCORING_SPEC.md",
    "standards/03_PGA_VENUEDNA_LEARNING_LOOP.md",
    "standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md",
    "standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md",
    "engine/scoring_decomposition.py",
    "engine/venuedna_scoring.py",
    "engine/enrich_cards.py",
    "config/active_event.json",
)

RETROSPECTIVE_MARKERS = (
    "RETROSPECTIVE_DEVELOPMENT_FIXTURE",
    "NOT OFFICIAL",
    "NOT PRE_EVENT",
    "NOT LIVE",
    "NOT DEPLOYABLE",
)

BOARD_SHELL_FILES = ("index.html", "app.js", "styles.css")

FENCED = "RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED"
ABSENT = "ACTIVE_EVENT_WYNDHAM_ABSENT"
DEPLOY_CONTENT = "RETROSPECTIVE_FIXTURE_DEPLOY_CONTENT"
NONEMPTY_DEPLOY_DATA = "RETROSPECTIVE_FIXTURE_NONEMPTY_DEPLOY_DATA"
NONEMPTY_OUTPUT = "RETROSPECTIVE_FIXTURE_NONEMPTY_OUTPUT"
NONEMPTY_AUDIT = "RETROSPECTIVE_FIXTURE_NONEMPTY_AUDIT"
BOARD_SHELL_NOT_A_FILE = "RETROSPECTIVE_FIXTURE_BOARD_SHELL_NOT_A_FILE"
ACTIVE_EVENT_STATUS = "RETROSPECTIVE_FIXTURE_ACTIVE_EVENT_STATUS"
README_MISSING = "RETROSPECTIVE_FIXTURE_README_MISSING"
MARKER_MISSING = "RETROSPECTIVE_FIXTURE_MARKER_MISSING"


@pytest.fixture
def doctrine_repo(tmp_path: Path) -> Path:
    for relative in FIXTURE_FILES:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def _rule_ids(repo: Path, *, strict: bool = False) -> set[str]:
    return {finding.rule_id for finding in validator.validate_repository(repo, strict=strict).findings}


def _errors(repo: Path, *, strict: bool = False) -> list:
    return [f for f in validator.validate_repository(repo, strict=strict).findings if f.severity == "error"]


def _write_wyndham_fixture(
    repo_root: Path,
    *,
    event_slug: str = "2026_wyndham_championship",
    include_readme: bool = True,
    markers: tuple[str, ...] = RETROSPECTIVE_MARKERS,
    output_files: tuple[str, ...] = (),
    audit_files: tuple[str, ...] = (),
    deploy_data_files: tuple[str, ...] = (),
    deploy_shell_files: tuple[str, ...] = (),
    deploy_extra_files: tuple[str, ...] = (),
    deploy_shell_as_directory: tuple[str, ...] = (),
) -> Path:
    """Construct a (by default fully compliant) synthetic Wyndham
    retrospective fixture under ``repo_root`` for doctrine-validator testing.
    """
    fixture_root = repo_root / "events" / event_slug
    (fixture_root / "input").mkdir(parents=True, exist_ok=True)
    (fixture_root / "output").mkdir(parents=True, exist_ok=True)
    (fixture_root / "audit").mkdir(parents=True, exist_ok=True)
    (fixture_root / "deploy" / "data").mkdir(parents=True, exist_ok=True)

    if include_readme:
        readme_text = "\n".join(f"## {marker}" for marker in markers) + "\n"
        (fixture_root / "RETROSPECTIVE_FIXTURE_README.md").write_text(readme_text, encoding="utf-8")

    (fixture_root / "input" / "source_manifest.json").write_text("{}", encoding="utf-8")

    for relative in output_files:
        path = fixture_root / "output" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for relative in audit_files:
        path = fixture_root / "audit" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for relative in deploy_data_files:
        path = fixture_root / "deploy" / "data" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for name in deploy_shell_files:
        (fixture_root / "deploy" / name).write_text("", encoding="utf-8")
    for name in deploy_extra_files:
        (fixture_root / "deploy" / name).write_text("", encoding="utf-8")
    for name in deploy_shell_as_directory:
        (fixture_root / "deploy" / name).mkdir(parents=True, exist_ok=True)

    return fixture_root


def _set_active_event_status(repo_root: Path, status: str) -> None:
    manifest_path = repo_root / "config" / "active_event.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = status
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


# ── 1. Fully fenced fixture with only empty deploy/data/ remains valid ──────

def test_fixture_with_only_empty_deploy_data_remains_valid(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo)
    ids = _rule_ids(doctrine_repo)
    assert FENCED in ids
    assert ABSENT not in ids
    assert _errors(doctrine_repo) == []


# ── 2. Fixture remains valid when all three allowed shell files exist ───────

def test_fixture_with_all_three_board_shell_files_remains_valid(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_shell_files=BOARD_SHELL_FILES)
    ids = _rule_ids(doctrine_repo)
    assert FENCED in ids
    assert ABSENT not in ids
    assert _errors(doctrine_repo) == []


@pytest.mark.parametrize("shell_file", BOARD_SHELL_FILES)
def test_fixture_with_single_board_shell_file_remains_valid(doctrine_repo: Path, shell_file: str) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_shell_files=(shell_file,))
    ids = _rule_ids(doctrine_repo)
    assert FENCED in ids
    assert ABSENT not in ids
    assert _errors(doctrine_repo) == []


def test_fixture_with_board_shell_files_stays_fenced_in_strict_mode(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_shell_files=BOARD_SHELL_FILES)
    ids = _rule_ids(doctrine_repo, strict=True)
    assert FENCED in ids
    assert ABSENT not in ids


# ── 3. Any file under deploy/data/ fails, even with the shell files present ──

def test_any_file_under_deploy_data_fails(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        deploy_data_files=("board_export.json",),
    )
    ids = _rule_ids(doctrine_repo)
    assert NONEMPTY_DEPLOY_DATA in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 4. Any file/subdirectory under output/ fails, even with shell files ─────

def test_any_file_under_output_fails(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        output_files=("scored_field.csv",),
    )
    ids = _rule_ids(doctrine_repo)
    assert NONEMPTY_OUTPUT in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 5. Any file/subdirectory under audit/ fails, even with shell files ──────

def test_any_file_under_audit_fails(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        audit_files=("audit_log.md",),
    )
    ids = _rule_ids(doctrine_repo)
    assert NONEMPTY_AUDIT in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 6. Any extra direct file under deploy/ fails ─────────────────────────────

@pytest.mark.parametrize(
    "extra_file",
    ("board_export.json", "player_briefs.json", "rankings.csv", "publish.marker", "README.md"),
)
def test_any_extra_direct_deploy_file_fails(doctrine_repo: Path, extra_file: str) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        deploy_extra_files=(extra_file,),
    )
    ids = _rule_ids(doctrine_repo)
    assert DEPLOY_CONTENT in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 7. Any extra deploy subdirectory fails ───────────────────────────────────

@pytest.mark.parametrize("extra_dir", ("assets", "images", "fonts", "vendor", "node_modules", "build"))
def test_any_extra_deploy_subdirectory_fails(doctrine_repo: Path, extra_dir: str) -> None:
    fixture_root = _write_wyndham_fixture(doctrine_repo, deploy_shell_files=BOARD_SHELL_FILES)
    (fixture_root / "deploy" / extra_dir).mkdir(parents=True)
    ids = _rule_ids(doctrine_repo)
    assert DEPLOY_CONTENT in ids
    assert ABSENT in ids
    assert FENCED not in ids


@pytest.mark.parametrize("shell_file", BOARD_SHELL_FILES)
def test_board_shell_entry_as_directory_fails(doctrine_repo: Path, shell_file: str) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_shell_as_directory=(shell_file,))
    ids = _rule_ids(doctrine_repo)
    assert BOARD_SHELL_NOT_A_FILE in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 8. The shell allowance never extends beyond the exact Wyndham fixture ───

def test_shell_allowance_does_not_extend_to_nonwyndham_event_root(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        event_slug="2026_other_event",
        deploy_shell_files=BOARD_SHELL_FILES,
    )
    ids = _rule_ids(doctrine_repo)
    assert FENCED not in ids
    assert ABSENT not in ids


# ── 9. Any non-NO_ACTIVE_EVENT state fails, even with shell files present ───

@pytest.mark.parametrize(
    "status", ("PRE_EVENT", "ROUND_1", "ROUND_2", "ROUND_3", "ROUND_4", "FINAL_AUDIT", "ARCHIVED")
)
def test_non_no_active_event_status_fails_with_shell_files_present(doctrine_repo: Path, status: str) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_shell_files=BOARD_SHELL_FILES)
    _set_active_event_status(doctrine_repo, status)
    ids = _rule_ids(doctrine_repo)
    assert ACTIVE_EVENT_STATUS in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 10. Missing README or any required fence marker fails, even with shell files ──

def test_missing_readme_fails_with_shell_files_present(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, include_readme=False, deploy_shell_files=BOARD_SHELL_FILES)
    ids = _rule_ids(doctrine_repo)
    assert README_MISSING in ids
    assert ABSENT in ids
    assert FENCED not in ids


@pytest.mark.parametrize("dropped_marker", RETROSPECTIVE_MARKERS)
def test_missing_any_required_marker_fails_with_shell_files_present(doctrine_repo: Path, dropped_marker: str) -> None:
    markers = tuple(marker for marker in RETROSPECTIVE_MARKERS if marker != dropped_marker)
    _write_wyndham_fixture(doctrine_repo, markers=markers, deploy_shell_files=BOARD_SHELL_FILES)
    ids = _rule_ids(doctrine_repo)
    assert MARKER_MISSING in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 11. The shell allowance never permits a deploy payload, official ────────
#         projection, live artifact, or publication marker.

@pytest.mark.parametrize(
    "marker_file",
    (
        "board_export.json",
        "event_payload.json",
        "player_briefs.json",
        "scored_field.csv",
        "rankings.json",
        "tiers.json",
        "probabilities.json",
        "live_round1.json",
        "OFFICIAL.marker",
        "PUBLISHED.marker",
    ),
)
def test_no_publication_or_official_artifact_marker_is_permitted_under_deploy(
    doctrine_repo: Path, marker_file: str
) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        deploy_extra_files=(marker_file,),
    )
    ids = _rule_ids(doctrine_repo)
    assert DEPLOY_CONTENT in ids
    assert ABSENT in ids
    assert FENCED not in ids


def test_no_publication_or_official_artifact_marker_is_permitted_under_deploy_data(
    doctrine_repo: Path,
) -> None:
    _write_wyndham_fixture(
        doctrine_repo,
        deploy_shell_files=BOARD_SHELL_FILES,
        deploy_data_files=("board_export.json",),
    )
    ids = _rule_ids(doctrine_repo)
    assert NONEMPTY_DEPLOY_DATA in ids
    assert ABSENT in ids
    assert FENCED not in ids


def test_shell_allowance_validation_performs_no_writes(doctrine_repo: Path) -> None:
    fixture_root = _write_wyndham_fixture(doctrine_repo, deploy_shell_files=BOARD_SHELL_FILES)
    before = {
        str(path.relative_to(fixture_root)): path.read_bytes()
        for path in fixture_root.rglob("*") if path.is_file()
    }
    validator.validate_repository(doctrine_repo)
    after = {
        str(path.relative_to(fixture_root)): path.read_bytes()
        for path in fixture_root.rglob("*") if path.is_file()
    }
    assert before == after
    assert not any((fixture_root / "output").iterdir())
    assert not any((fixture_root / "audit").iterdir())
    assert not any((fixture_root / "deploy" / "data").iterdir())
