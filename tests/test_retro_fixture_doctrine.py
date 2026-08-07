"""tests/test_retro_fixture_doctrine.py
Focused coverage for the Phase 6.1 Wyndham retrospective-fixture doctrine
carve-out in tools/validate_scoring_doctrine.py.

Every test operates on a tmp_path-constructed repository copy. No test
touches the real events/2026_wyndham_championship/ fixture or
config/active_event.json.
"""
from __future__ import annotations

import hashlib
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

FENCED = "RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED"
ABSENT = "ACTIVE_EVENT_WYNDHAM_ABSENT"


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
    deploy_root_files: tuple[str, ...] = (),
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
    for relative in deploy_root_files:
        path = fixture_root / "deploy" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html></html>", encoding="utf-8")

    return fixture_root


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _set_active_event_status(repo_root: Path, status: str) -> None:
    manifest_path = repo_root / "config" / "active_event.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = status
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


# ── 1. The exact authorized fixture passes only while every criterion holds ──

def test_compliant_fixture_is_fenced_with_no_errors(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo)
    ids = _rule_ids(doctrine_repo)
    assert FENCED in ids
    assert ABSENT not in ids
    assert _errors(doctrine_repo) == []


def test_compliant_fixture_stays_fenced_in_strict_mode(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo)
    ids = _rule_ids(doctrine_repo, strict=True)
    assert FENCED in ids
    assert ABSENT not in ids


# ── 2. Missing README fails closed ───────────────────────────────────────────

def test_missing_readme_fails_closed(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, include_readme=False)
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_README_MISSING" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 3. Missing any required marker fails closed ──────────────────────────────

@pytest.mark.parametrize("dropped_marker", RETROSPECTIVE_MARKERS)
def test_missing_any_required_marker_fails_closed(doctrine_repo: Path, dropped_marker: str) -> None:
    markers = tuple(marker for marker in RETROSPECTIVE_MARKERS if marker != dropped_marker)
    _write_wyndham_fixture(doctrine_repo, markers=markers)
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_MARKER_MISSING" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 4. Non-empty output/ fails closed ────────────────────────────────────────

def test_nonempty_output_fails_closed(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, output_files=("scored_field.csv",))
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_NONEMPTY_OUTPUT" in ids
    assert ABSENT in ids
    assert FENCED not in ids


def test_nonempty_audit_fails_closed(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, audit_files=("audit_log.md",))
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_NONEMPTY_AUDIT" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 5. Any deploy/data/* payload fails closed ────────────────────────────────

def test_deploy_data_payload_fails_closed(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_data_files=("players.json",))
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_NONEMPTY_DEPLOY_DATA" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 6. Any official board artifact fails closed ──────────────────────────────

def test_official_board_artifact_fails_closed(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, deploy_root_files=("index.html",))
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_DEPLOY_CONTENT" in ids
    assert ABSENT in ids
    assert FENCED not in ids


def test_unapproved_event_root_content_fails_closed(doctrine_repo: Path) -> None:
    fixture_root = _write_wyndham_fixture(doctrine_repo)
    (fixture_root / "round1").mkdir()
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_UNAPPROVED_CONTENT" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 7. A non-Wyndham event root cannot use the exception ─────────────────────

def test_nonwyndham_event_root_cannot_use_exception(doctrine_repo: Path) -> None:
    _write_wyndham_fixture(doctrine_repo, event_slug="2026_other_event")
    ids = _rule_ids(doctrine_repo)
    assert FENCED not in ids
    assert ABSENT not in ids


# ── 8. Any non-NO_ACTIVE_EVENT manifest status fails closed ─────────────────

@pytest.mark.parametrize("status", ("PRE_EVENT", "ROUND_1", "ROUND_2", "ROUND_3", "ROUND_4", "FINAL_AUDIT", "ARCHIVED"))
def test_non_no_active_event_status_fails_closed(doctrine_repo: Path, status: str) -> None:
    _write_wyndham_fixture(doctrine_repo)
    _set_active_event_status(doctrine_repo, status)
    ids = _rule_ids(doctrine_repo)
    assert "RETROSPECTIVE_FIXTURE_ACTIVE_EVENT_STATUS" in ids
    assert ABSENT in ids
    assert FENCED not in ids


# ── 9. The normal ACTIVE_EVENT_WYNDHAM_ABSENT block remains in force ────────

def test_ordinary_wyndham_initialization_without_fixture_markers_still_blocked(doctrine_repo: Path) -> None:
    (doctrine_repo / "events" / "2026_wyndham_championship").mkdir(parents=True)
    ids = _rule_ids(doctrine_repo)
    assert ABSENT in ids
    assert FENCED not in ids


# ── 10. The fixture exception does not permit source scoring/build execution ─

def test_compliant_fixture_validation_performs_no_writes_or_scoring(doctrine_repo: Path) -> None:
    fixture_root = _write_wyndham_fixture(doctrine_repo)
    before = _snapshot(fixture_root)
    validator.validate_repository(doctrine_repo)
    after = _snapshot(fixture_root)

    assert before == after
    assert not any((fixture_root / "output").iterdir())
    assert not any((fixture_root / "audit").iterdir())
    assert not any((fixture_root / "deploy" / "data").iterdir())
