"""tests/test_wyndham_retrospective_board_shell.py
Static-file inspection coverage for the Phase 6.4 fenced Wyndham
retrospective board shell.

RETROSPECTIVE DEVELOPMENT FIXTURE — NOT OFFICIAL — NOT PRE_EVENT — NOT LIVE
— NOT DEPLOYABLE.

This suite performs deterministic, read-only static inspection of the three
committed board-shell files. It does not launch a browser, does not create
any deploy/data, output, or audit artifact, and does not modify
config/active_event.json. No test writes into the fixture; every assertion
reads the already-authored shell files under
events/2026_wyndham_championship/deploy/.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "events" / "2026_wyndham_championship"
DEPLOY_ROOT = FIXTURE_ROOT / "deploy"

INDEX_HTML = DEPLOY_ROOT / "index.html"
APP_JS = DEPLOY_ROOT / "app.js"
STYLES_CSS = DEPLOY_ROOT / "styles.css"

VALIDATOR_PATH = ROOT / "tools" / "validate_scoring_doctrine.py"
_SPEC = importlib.util.spec_from_file_location("validate_scoring_doctrine", VALIDATOR_PATH)
assert _SPEC is not None and _SPEC.loader is not None
validator = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = validator
_SPEC.loader.exec_module(validator)

RETROSPECTIVE_MARKERS = (
    "RETROSPECTIVE DEVELOPMENT FIXTURE",
    "NOT OFFICIAL",
    "NOT PRE-EVENT",
    "NOT LIVE",
    "NOT DEPLOYABLE",
)

# The four real player identities behind the verified Phase 6.2 UNSCORED
# outcome must never appear in synthetic UI fixture data.
PROHIBITED_REAL_PLAYER_NAMES = (
    "David Skinns",
    "Taylor Moore",
    "William McGirt",
    "C.T. Pan",
    "Daniel Berger",
    "Troy Merritt",
)

REQUIRED_UNSCORED_MECHANISM_TEXT = (
    "Missing required VenueFit evidence",
    "Missing required NeutralSkill evidence",
    "Mixed VenueFit horizons",
)


# ── 1. Exactly the three approved shell files exist, nothing else ──────────

def test_exactly_three_shell_files_present_as_direct_children() -> None:
    assert INDEX_HTML.is_file()
    assert APP_JS.is_file()
    assert STYLES_CSS.is_file()

    direct_children = {p.name for p in DEPLOY_ROOT.iterdir()}
    assert direct_children == {"index.html", "app.js", "styles.css", "data"}


def test_deploy_data_directory_remains_recursively_empty() -> None:
    data_dir = DEPLOY_ROOT / "data"
    assert data_dir.is_dir()
    assert list(data_dir.rglob("*")) == []


def test_no_output_or_audit_artifact_exists() -> None:
    assert list((FIXTURE_ROOT / "output").rglob("*")) == []
    assert list((FIXTURE_ROOT / "audit").rglob("*")) == []


def test_no_disallowed_deploy_subdirectory_or_asset_class() -> None:
    disallowed_names = {"assets", "images", "fonts", "vendor", "node_modules", "build", "dist"}
    direct_children = {p.name for p in DEPLOY_ROOT.iterdir()}
    assert direct_children.isdisjoint(disallowed_names)


# ── 2. Doctrine validator accepts the real committed shell files ───────────

def test_doctrine_validator_accepts_real_fixture_with_shell_files(tmp_path: Path) -> None:
    result = validator.validate_repository(ROOT, strict=True)
    ids = {finding.rule_id for finding in result.findings}
    assert "RETROSPECTIVE_WYNDHAM_FIXTURE_FENCED" in ids
    assert "ACTIVE_EVENT_WYNDHAM_ABSENT" not in ids
    errors = [f for f in result.findings if f.severity == "error"]
    assert errors == []


# ── 3. index.html carries the required retrospective fence text ───────────

def test_index_html_contains_all_required_fence_markers() -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")
    for marker in RETROSPECTIVE_MARKERS:
        assert marker in text, f"missing required fence marker: {marker!r}"


def test_index_html_declares_venue_context_and_non_official_subtitle() -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")
    assert "2026 Wyndham Championship" in text
    assert "Sedgefield Country Club" in text
    assert "no official scoring payload loaded" in text


def test_index_html_references_only_the_local_shell_assets() -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")
    assert 'href="styles.css"' in text
    assert 'src="app.js"' in text
    # No external stylesheet, font, or script host of any kind.
    assert "http://" not in text
    assert "https://" not in text


# ── 4. app.js contains no network, storage, or external-endpoint calls ─────

def test_app_js_contains_no_fetch_call() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "fetch(" not in text


def test_app_js_contains_no_local_storage_usage() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "localStorage" not in text
    assert "sessionStorage" not in text


def test_app_js_contains_no_external_http_endpoint_or_query_string_read() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "http://" not in text
    assert "https://" not in text
    assert "XMLHttpRequest" not in text
    assert "location.search" not in text
    assert "URLSearchParams" not in text


# ── 5. app.js uses a synthetic in-memory data declaration only ─────────────

def test_app_js_declares_synthetic_in_memory_fixture_array() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert re.search(r"\bFIXTURE_PLAYERS\s*=\s*\[", text), "expected an in-memory FIXTURE_PLAYERS array literal"
    assert "synthetic" in text.lower()


def test_app_js_fixture_names_are_generic_not_real_players() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    for real_name in PROHIBITED_REAL_PLAYER_NAMES:
        assert real_name not in text, f"real player identity leaked into fixture data: {real_name!r}"


# ── 6. UNSCORED UI state is present and never assigns a tier/score/rank ────

def test_app_js_declares_four_unscored_fixture_records_with_required_mechanisms() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    unscored_blocks = re.findall(r'status:\s*"unscored"', text)
    assert len(unscored_blocks) == 4

    for mechanism_text in REQUIRED_UNSCORED_MECHANISM_TEXT:
        assert mechanism_text in text


def test_unscored_fixture_records_carry_no_rank_tier_or_score_fields() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    # Extract each fixture object literal and check the unscored ones never
    # declare rank/tier/score/win/top5/top10/top20 numeric fields.
    objects = re.findall(r"\{[^{}]*status:\s*\"unscored\"[^{}]*\}", text, flags=re.DOTALL)
    assert len(objects) == 4
    for obj in objects:
        for forbidden_field in ("rank:", "tier:", "score:", "win:", "top5:", "top10:", "top20:"):
            assert forbidden_field not in obj, (
                f"UNSCORED fixture record must not declare {forbidden_field!r}: {obj}"
            )


def test_unscored_rows_render_em_dash_placeholders_and_named_status() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "UNSCORED — incomplete required evidence" in text or (
        "UNSCORED" in text and "incomplete required evidence" in text
    )
    # The unscored row-rendering branch must emit "—" placeholders rather
    # than a numeric zero or a fabricated rank/tier.
    unscored_branch_match = re.search(
        r'if \(player\.status === "unscored"\) \{(.*?)\n  \}', text, flags=re.DOTALL
    )
    assert unscored_branch_match is not None
    unscored_branch = unscored_branch_match.group(1)
    assert unscored_branch.count("—") >= 6
    assert re.search(r'data-col="tier">T\d', unscored_branch) is None
    assert re.search(r'data-col="score">\d', unscored_branch) is None
    assert re.search(r'data-col="rank">\d', unscored_branch) is None


def test_tier_filter_logic_excludes_unscored_records() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    # The T1-T5 tier branch of filterPlayers must require status === "scored".
    filter_fn_match = re.search(r"function filterPlayers\(.*?\n  \}", text, flags=re.DOTALL)
    assert filter_fn_match is not None
    filter_fn = filter_fn_match.group(0)
    assert 'p.status === "scored" && p.tier === filterValue' in filter_fn


def test_sort_logic_always_places_unscored_records_last() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    sort_fn_match = re.search(r"function sortPlayers\(.*?\n  \}", text, flags=re.DOTALL)
    assert sort_fn_match is not None
    sort_fn = sort_fn_match.group(0)
    assert "scored.concat(unscored)" in sort_fn


# ── 7. styles.css must not introduce any external network dependency ───────

def test_styles_css_has_no_external_url_reference() -> None:
    text = STYLES_CSS.read_text(encoding="utf-8")
    assert "http://" not in text
    assert "https://" not in text
    assert "@import" not in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
