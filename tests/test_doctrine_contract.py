"""Contract tests for the static scoring-doctrine validator.

All negative cases operate on temporary repository fixtures.  The production
engine is never imported or executed by this suite.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_scoring_doctrine.py"

SPEC = importlib.util.spec_from_file_location("validate_scoring_doctrine", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


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


@pytest.fixture
def doctrine_repo(tmp_path: Path) -> Path:
    for relative in FIXTURE_FILES:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def _path(repo: Path, relative: str) -> Path:
    return repo / Path(relative)


def _replace(repo: Path, relative: str, old: str, new: str) -> None:
    path = _path(repo, relative)
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture mutation target not found: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _replace_all(repo: Path, relative: str, old: str, new: str) -> None:
    path = _path(repo, relative)
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture mutation target not found: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _append_marker_line(repo: Path, line: str) -> None:
    _replace(
        repo,
        "standards/02_PGA_VENUEDNA_SCORING_SPEC.md",
        "excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20\n-->",
        "excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20\n"
        + line
        + "\n-->",
    )


def _findings(repo: Path, *, strict: bool = False):
    return validator.validate_repository(repo, strict=strict).findings


def _rule_ids(repo: Path, *, strict: bool = False) -> set[str]:
    return {finding.rule_id for finding in _findings(repo, strict=strict)}


def _errors(repo: Path, *, strict: bool = False):
    return [f for f in _findings(repo, strict=strict) if f.severity == "error"]


def _assert_alias_finding(repo: Path, rule_id: str, alias_name: str) -> None:
    finding = next(finding for finding in _findings(repo) if finding.rule_id == rule_id)
    assert "protected alias" in finding.reason
    assert alias_name in finding.reason


def test_current_repository_success() -> None:
    assert validator.validate_repository(ROOT).findings == ()
    assert validator.validate_repository(ROOT, strict=True).findings == ()


def test_public_parsers_read_marker_and_diagnostics_without_importing_engine() -> None:
    marker = validator.parse_doctrine_marker(
        ROOT / "standards" / "02_PGA_VENUEDNA_SCORING_SPEC.md"
    )
    literals = validator.extract_python_literals(
        ROOT / "engine" / "scoring_decomposition.py"
    )
    assert marker["formula_version"] == "2.0.0"
    assert literals["CANONICAL_V2_FORMULA_ID"] == marker["formula_id"]
    assert literals["FORMULA.formula_identifier"] == "3m-enriched-v2.0"


def test_missing_marker(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "standards/02_PGA_VENUEDNA_SCORING_SPEC.md")
    text = path.read_text(encoding="utf-8")
    start = text.index("<!-- scoring-doctrine-v2")
    end = text.index("-->", start) + 3
    path.write_text(text[:start] + text[end:], encoding="utf-8")
    assert "MARKER_COUNT" in _rule_ids(doctrine_repo)


def test_duplicate_marker(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "standards/02_PGA_VENUEDNA_SCORING_SPEC.md")
    text = path.read_text(encoding="utf-8")
    start = text.index("<!-- scoring-doctrine-v2")
    end = text.index("-->", start) + 3
    marker = text[start:end]
    path.write_text(text + "\n" + marker + "\n", encoding="utf-8")
    assert "MARKER_COUNT" in _rule_ids(doctrine_repo)


def test_missing_key(doctrine_repo: Path) -> None:
    _replace(doctrine_repo, FIXTURE_FILES[0], "formula_version=2.0.0\n", "")
    assert "MARKER_REQUIRED_KEYS" in _rule_ids(doctrine_repo)


def test_duplicate_key(doctrine_repo: Path) -> None:
    _append_marker_line(doctrine_repo, "formula_id=venuedna_dual_vector_decomposed")
    assert "MARKER_DUPLICATE_KEY" in _rule_ids(doctrine_repo)


def test_malformed_marker_line(doctrine_repo: Path) -> None:
    _append_marker_line(doctrine_repo, "this is not an assignment")
    assert "MARKER_MALFORMED_ASSIGNMENT" in _rule_ids(doctrine_repo)


def test_empty_value(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "comparable_score_family=dual_vector_sg_per_round_v2",
        "comparable_score_family=",
    )
    assert "MARKER_EMPTY_VALUE" in _rule_ids(doctrine_repo)


def test_unknown_key_warning(doctrine_repo: Path) -> None:
    _append_marker_line(doctrine_repo, "future_key=future_value")
    finding = next(f for f in _findings(doctrine_repo) if f.rule_id == "MARKER_UNKNOWN_KEY")
    assert finding.severity == "warning"


def test_unknown_key_strict_failure(doctrine_repo: Path) -> None:
    _append_marker_line(doctrine_repo, "future_key=future_value")
    finding = next(
        f for f in _findings(doctrine_repo, strict=True) if f.rule_id == "MARKER_UNKNOWN_KEY"
    )
    assert finding.severity == "error"


@pytest.mark.parametrize(
    ("old", "new", "rule_id"),
    (
        (
            "formula_id=venuedna_dual_vector_decomposed",
            "formula_id=wrong_formula",
            "MARKER_FORMULA_ID",
        ),
        ("formula_version=2.0.0", "formula_version=9.9.9", "MARKER_FORMULA_VERSION"),
        (
            "comparable_score_family=dual_vector_sg_per_round_v2",
            "comparable_score_family=wrong_family",
            "MARKER_COMPARABLE_FAMILY",
        ),
        (
            "penalty_gate_set_id=venuedna_v2_none",
            "penalty_gate_set_id=wrong_gate_set",
            "MARKER_PENALTY_GATE_SET",
        ),
        (
            "canonical_core_inputs=SG_Base_Comp,Delta_Fit_Comp,VenueHistoryDeltaRaw",
            "canonical_core_inputs=Delta_Fit_Comp,SG_Base_Comp,VenueHistoryDeltaRaw",
            "MARKER_CORE_INPUTS",
        ),
        (
            "excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20",
            "excluded_legacy_noncore_addends=true_sg_l20,ch_adjustment,ott_true,trait_long_iron_raw,trait_approach_raw",
            "MARKER_EXCLUDED_ADDENDS",
        ),
    ),
)
def test_wrong_marker_values(
    doctrine_repo: Path, old: str, new: str, rule_id: str
) -> None:
    _replace(doctrine_repo, FIXTURE_FILES[0], old, new)
    assert rule_id in _rule_ids(doctrine_repo)


def test_overlapping_sets(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20",
        "excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,SG_Base_Comp",
    )
    assert "MARKER_COMPONENT_OVERLAP" in _rule_ids(doctrine_repo)


def test_descriptor_mismatch(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/scoring_decomposition.py",
        "canonical_formula_id=CANONICAL_V2_FORMULA_ID,",
        'canonical_formula_id="descriptor_wrong",',
    )
    assert "DIAGNOSTIC_DESCRIPTOR_MISMATCH" in _rule_ids(doctrine_repo)


def test_production_identity_accidentally_equal_to_canonical(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/scoring_decomposition.py",
        'formula_identifier="3m-enriched-v2.0",',
        'formula_identifier="venuedna_dual_vector_decomposed",',
    )
    assert "DIAGNOSTIC_PRODUCTION_FORMULA_DIVERGENCE" in _rule_ids(doctrine_repo)


def test_production_gate_configuration_accidentally_equal_to_canonical(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/scoring_decomposition.py",
        'HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID = "historical_3m_inline_gates"',
        'HISTORICAL_PRODUCTION_GATE_CONFIGURATION_ID = "venuedna_v2_none"',
    )
    assert "DIAGNOSTIC_PRODUCTION_GATE_DIVERGENCE" in _rule_ids(doctrine_repo)


def test_missing_divergence_reason(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/scoring_decomposition.py",
        '    "FORMULA_V2_MIGRATION_PENDING",\n',
        "",
    )
    assert "DIAGNOSTIC_DIVERGENCE_REASONS" in _rule_ids(doctrine_repo)


def test_extra_divergence_reason(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/scoring_decomposition.py",
        '    "PENALTY_GATE_SET_ID_MISMATCH",\n)',
        '    "PENALTY_GATE_SET_ID_MISMATCH",\n    "EXTRA_REASON",\n)',
    )
    assert "DIAGNOSTIC_DIVERGENCE_REASONS" in _rule_ids(doctrine_repo)


def test_missing_data_zero_fill_regression(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "Missing values must not be represented as legitimate numeric zero.",
        "Missing values may be represented as legitimate numeric zero.",
    )
    assert "GOV_MISSING_NOT_ZERO" in _rule_ids(doctrine_repo)


def test_debut_regression(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "A valid similar-course row with zero rounds is `DEBUT`",
        "A missing similar-course row is `DEBUT`",
    )
    assert "GOV_DEBUT_REQUIRES_VALID_ROW" in _rule_ids(doctrine_repo)


def test_source_native_zero_observation_debut_regression(doctrine_repo: Path) -> None:
    spec = _path(doctrine_repo, FIXTURE_FILES[0]).read_text(encoding="utf-8")
    assert "it is a zero-observation DEBUT state, retains `total_mean: null`" in spec
    assert "is never converted to `0.0`" in spec


def test_venue_history_neutral_zero_regression(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "the canonical `VenueHistoryDeltaRaw = 0.0` is an explicit neutral contribution",
        "the canonical `VenueHistoryDeltaRaw = 0.0` fills missing raw history with zero",
    )
    assert "GOV_VENUE_HISTORY_NEUTRAL_ZERO" in _rule_ids(doctrine_repo)


@pytest.mark.parametrize(
    "legacy_phrase",
    (
        "Permanent scoring rules derived from Rocket Classic 2026",
        "Apply globally",
        "These rules are permanent until superseded",
    ),
)
def test_rocket_permanent_rule_regression(
    doctrine_repo: Path, legacy_phrase: str
) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "## 17. ROCKET CLASSIC 2026 INACTIVE RESEARCH HYPOTHESES",
        "## 17. ROCKET CLASSIC 2026 INACTIVE RESEARCH HYPOTHESES\n\n" + legacy_phrase,
    )
    assert "GOV_ROCKET_LEGACY_PERMANENT_LANGUAGE" in _rule_ids(doctrine_repo)


def test_rocket_active_effect_regression(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "They do not alter `PrePenaltyRaw`, `PostPenaltyRaw`, `PostGateRaw`, confidence, tiers, probabilities, badges, or ranks; they activate no penalty or gate",
        "They alter scores, tiers, confidence, badges, penalties, and gates",
    )
    assert "GOV_ROCKET_NO_ACTIVE_EFFECT" in _rule_ids(doctrine_repo)


def test_missing_multi_event_threshold(doctrine_repo: Path) -> None:
    _replace_all(
        doctrine_repo,
        FIXTURE_FILES[0],
        "at least three relevant or sufficiently similar events by default",
        "one event by default",
    )
    _replace_all(
        doctrine_repo,
        FIXTURE_FILES[1],
        "at least three relevant or sufficiently similar events by default",
        "one event by default",
    )
    assert "GOV_ROCKET_MULTI_EVENT_THRESHOLD" in _rule_ids(doctrine_repo)


def test_missing_council_approval(doctrine_repo: Path) -> None:
    _replace_all(doctrine_repo, FIXTURE_FILES[0], "Model Council approval", "informal review")
    _replace_all(doctrine_repo, FIXTURE_FILES[1], "Model Council approval", "informal review")
    assert "GOV_ROCKET_COUNCIL_APPROVAL" in _rule_ids(doctrine_repo)


def test_missing_operator_authorization(doctrine_repo: Path) -> None:
    _replace_all(
        doctrine_repo, FIXTURE_FILES[0], "explicit operator authorization", "implicit authorization"
    )
    _replace_all(
        doctrine_repo, FIXTURE_FILES[1], "explicit operator authorization", "implicit authorization"
    )
    assert "GOV_ROCKET_OPERATOR_AUTHORIZATION" in _rule_ids(doctrine_repo)


def test_canonical_producer_migration_status_regression(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "Historical 3M formulas remain diagnostic-only",
        "Historical 3M formulas remain official",
    )
    assert "GOV_PRODUCER_MIGRATION_STATUS" in _rule_ids(doctrine_repo)


def test_historical_rewrite_allowed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "Archived 3M enriched and Open v3 artifacts remain valid historical event records",
        "Archived 3M enriched and Open v3 artifacts may be rewritten as v2-conforming records",
    )
    assert "GOV_HISTORICAL_ARTIFACT_IMMUTABILITY" in _rule_ids(doctrine_repo)


def test_wyndham_block_removed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "Wyndham initialization remains blocked",
        "Wyndham initialization is allowed",
    )
    assert "GOV_WYNDHAM_BLOCK" in _rule_ids(doctrine_repo)


def test_invalid_active_event_bindings(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "config/active_event.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["event_slug"] = "2026_wyndham_championship"
    manifest["venue_slug"] = "sedgefield_country_club"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    ids = _rule_ids(doctrine_repo)
    assert "ACTIVE_EVENT_BINDINGS_NULL" in ids


def test_missing_active_event_binding_key_is_rejected(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "config/active_event.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.pop("event_slug")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert "ACTIVE_EVENT_BINDINGS_REQUIRED" in _rule_ids(doctrine_repo)


def test_wyndham_directory_is_rejected(doctrine_repo: Path) -> None:
    (doctrine_repo / "events" / "2026_wyndham_championship").mkdir(parents=True)
    assert "ACTIVE_EVENT_WYNDHAM_ABSENT" in _rule_ids(doctrine_repo)


def test_deterministic_finding_order(doctrine_repo: Path) -> None:
    _append_marker_line(doctrine_repo, "future_key=future_value")
    _replace(doctrine_repo, FIXTURE_FILES[0], "formula_version=2.0.0", "formula_version=9")
    first = _findings(doctrine_repo)
    second = _findings(doctrine_repo)
    keys = [(f.severity, f.rule_id, f.file, f.reason) for f in first]
    assert first == second
    assert keys == sorted(keys)


def test_valid_json_output() -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(env.get("TEMP", ".")) / "venuedna_doctrine_pycache")
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--format", "json", "--repo-root", str(ROOT)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["findings"] == []
    assert payload["status"] == "pass"


def test_no_production_module_imports() -> None:
    tree = ast.parse(VALIDATOR_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "engine.scoring_decomposition" not in imported
    assert "engine.enrich_cards" not in imported
    assert "scoring_decomposition" not in imported
    assert "enrich_cards" not in imported
    assert "engine.venuedna_scoring" not in imported
    assert "venuedna_scoring" not in imported


# ── Canonical v2 pure-implementation metadata drift (P3 migration) ─────────

def test_v2_implementation_formula_version_drift_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        'FORMULA_VERSION = "2.0.0"',
        'FORMULA_VERSION = "9.9.9"',
    )
    assert "V2IMPL_FORMULA_VERSION" in _rule_ids(doctrine_repo)


def test_v2_implementation_formula_id_drift_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        'FORMULA_ID = "venuedna_dual_vector_decomposed"',
        'FORMULA_ID = "some_other_formula"',
    )
    assert "V2IMPL_FORMULA_ID" in _rule_ids(doctrine_repo)


def test_v2_implementation_scoring_spec_version_drift_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        'SCORING_SPEC_VERSION = "2.0-draft"',
        'SCORING_SPEC_VERSION = "9.9-draft"',
    )
    assert "V2IMPL_SCORING_SPEC_VERSION" in _rule_ids(doctrine_repo)


def test_v2_implementation_legacy_addend_reentering_core_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        'CORE_INPUTS: tuple[str, ...] = ("SG_Base_Comp", "Delta_Fit_Comp", "VenueHistoryDeltaRaw")',
        'CORE_INPUTS: tuple[str, ...] = ("SG_Base_Comp", "Delta_Fit_Comp", "VenueHistoryDeltaRaw", "trait_approach_raw")',
    )
    assert "V2IMPL_COMPONENT_OVERLAP" in _rule_ids(doctrine_repo)


def test_v2_implementation_unapproved_active_gate_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        "ACTIVE_GATE_IDS: tuple[str, ...] = ()",
        'ACTIVE_GATE_IDS: tuple[str, ...] = ("SOME_NEW_GATE",)',
    )
    assert "V2IMPL_ACTIVE_GATES" in _rule_ids(doctrine_repo)


def test_v2_implementation_unapproved_active_penalty_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/venuedna_scoring.py",
        "ACTIVE_PENALTY_IDS: tuple[str, ...] = ()",
        'ACTIVE_PENALTY_IDS: tuple[str, ...] = ("SOME_NEW_PENALTY",)',
    )
    assert "V2IMPL_ACTIVE_PENALTIES" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_missing_canonical_scorer_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "projection = compute_player_projection(",
        "projection = legacy_projection(",
    )
    assert "V2PROD_CANONICAL_SCORER" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_unused_projection_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '"_post_gate_raw":       projection.post_gate_raw,',
        '"_post_gate_raw":       sg_sim_comp,',
    )
    assert "V2PROD_POST_GATE_LINEAGE" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_legacy_raw_pool_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'canonical_raw_scores = [record["post_gate_raw"] for record in scored_players]',
        'canonical_raw_scores = [record["_d_form"] for record in scored_players]',
    )
    assert "V2PROD_FINALIZER_RAW_POOL" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_legacy_normalization_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "normalized_scores = canonical_z_score_scale(canonical_raw_scores)",
        'normalized_scores = canonical_z_score_scale([record["_d_form"] for record in scored_players])',
    )
    assert "V2PROD_FINALIZER_NORMALIZATION" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_legacy_probability_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "probability_vectors = canonical_compute_probability_vectors(canonical_raw_scores)",
        'probability_vectors = canonical_compute_probability_vectors([record["_d_form"] for record in scored_players])',
    )
    assert "V2PROD_FINALIZER_PROBABILITIES" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_historical_probability_helper_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "probability_vectors = canonical_compute_probability_vectors(canonical_raw_scores)",
        "probability_vectors = tempered_softmax(canonical_raw_scores, 3.5, 1)",
    )
    ids = _rule_ids(doctrine_repo)
    assert "V2PROD_FINALIZER_PROBABILITIES" in ids
    assert "V2PROD_LEGACY_PROBABILITIES" in ids


def test_v2_producer_integration_official_score_redirect_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '"vts_final": canonical_vts,',
        '"vts_final": prepared["_d_form"],',
    )
    assert "V2PROD_FINALIZER_OFFICIAL_OUTPUT" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_rank_tier_redirect_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'key=lambda record: record["vts_final"],',
        'key=lambda record: record["_d_form"],',
    )
    assert "V2PROD_FINALIZER_SORT" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_later_official_score_overwrite_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'canonical_vts = round(normalized_scores[scored_index], 1)',
        'canonical_vts = round(normalized_scores[scored_index], 1)\n            canonical_vts = prepared["_d_form"]',
    )
    assert "V2PROD_FINALIZER_INTERMEDIATE_REBIND" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_arbitrary_alias_score_overwrite_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'canonical_vts = round(normalized_scores[scored_index], 1)',
        'canonical_vts = round(normalized_scores[scored_index], 1)\n'
        '            p["vts_final"] = canonical_vts\n'
        '            p["vts_final"] = p["_d_form"]',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_update_score_overwrite_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '                **probabilities,\n            }\n        else:',
        '                **probabilities,\n            }\n'
        '            record.update({"vts_final": prepared["_d_form"]})\n'
        '        else:',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_earlier_branch_score_writer_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'canonical_vts = round(normalized_scores[scored_index], 1)',
        'if prepared["player"] == "legacy":\n'
        '                canonical_vts = prepared["_d_form"]\n'
        '            else:\n'
        '                canonical_vts = round(normalized_scores[scored_index], 1)',
    )
    assert "V2PROD_FINALIZER_INTERMEDIATE_REBIND" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_later_probability_overwrite_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probabilities["winPct"] = 0.0',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_probability_mapping_rebind_to_zeroes_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probabilities = {\n'
        '                key: 0.0\n'
        '                for key in CANONICAL_PROBABILITY_FIELDS\n'
        '            }',
    )
    assert "V2PROD_PROBABILITY_REBIND" in _rule_ids(doctrine_repo)


def test_v2_finalizer_probability_mapping_rebind_from_legacy_data_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probabilities = {"winPct": prepared["_d_form"]}',
    )
    assert "V2PROD_PROBABILITY_REBIND" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_update_overwrites_each_probability_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probabilities.update({"winPct": 0.0, "top5Pct": 0.0, "top10Pct": 0.0, '
        '"top20Pct": 0.0, "makeCutPct": 0.0, "missCutPct": 0.0})',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_later_rank_overwrite_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'ordered_records = [reorder_record(record) for record in final_records]',
        'ordered_records = [reorder_record(record) for record in final_records]\n    final_records.append({})',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_later_tier_overwrite_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '{"rank": rank, **record, "tier": canonical_assign_tier(rank)}',
        '{"rank": rank, **record, "tier": "T5"}',
    )
    assert "V2PROD_FINALIZER_TIER" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_dynamic_update_is_fail_closed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        'engine/enrich_cards.py',
        'canonical_vts = round(normalized_scores[scored_index], 1)',
        'canonical_vts = round(normalized_scores[scored_index], 1)\n            record |= some_mapping',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_second_noncanonical_sort_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        reverse=True,\n    )\n    unscored_records',
        '        reverse=True,\n    )\n'
        '    ordered_scored_records.sort(key=lambda record: record["_d_form"], reverse=True)\n'
        '    unscored_records',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_ordered_record_mutation_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    return ordered_records",
        '    ordered_records[0]["vts_final"] = legacy_value\n    return ordered_records',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_dictionary_union_update_is_fail_closed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'canonical_vts = round(normalized_scores[scored_index], 1)',
        'canonical_vts = round(normalized_scores[scored_index], 1)\n            p |= some_mapping',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_probability_alias_mutation_is_fail_closed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probs["winPct"] = legacy_value',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_finalizer_ordered_alias_mutation_is_fail_closed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    return ordered_records",
        '    ordered[0]["vts_final"] = legacy_value\n    return ordered_records',
    )
    assert "V2PROD_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_main_mutates_finalizer_return_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "        live_r1_sg=live_r1_sg,\n    )\n\n    # ── Write outputs",
        '        live_r1_sg=live_r1_sg,\n    )\n'
        '    ordered_records[0]["vts_final"] = legacy_value\n\n'
        '    # ── Write outputs',
    )
    assert "V2PROD_MAIN_POST_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_main_rebinds_finalizer_return_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "        live_r1_sg=live_r1_sg,\n    )\n\n    # ── Write outputs",
        '        live_r1_sg=live_r1_sg,\n    )\n'
        '    ordered_records = other_records\n\n'
        '    # ── Write outputs',
    )
    assert "V2PROD_MAIN_POST_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_main_resorts_finalizer_return_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "        live_r1_sg=live_r1_sg,\n    )\n\n    # ── Write outputs",
        '        live_r1_sg=live_r1_sg,\n    )\n'
        '    ordered_records.sort(key=lambda record: record["_d_form"], reverse=True)\n\n'
        '    # ── Write outputs',
    )
    assert "V2PROD_MAIN_POST_FINALIZER_MUTATION" in _rule_ids(doctrine_repo)


def test_v2_main_payload_players_replacement_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload["players"] = players_raw\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_PAYLOAD_PLAYERS_REPLACED" in _rule_ids(doctrine_repo)


def test_v2_main_payload_players_update_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload.update({"players": players_raw})\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_PAYLOAD_PLAYERS_REPLACED" in _rule_ids(doctrine_repo)


def test_v2_main_payload_players_union_update_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload |= {"players": players_raw}\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_PAYLOAD_PLAYERS_REPLACED" in _rule_ids(doctrine_repo)


def test_v2_main_payload_rebind_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload = other_payload\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_PAYLOAD_REBIND" in _rule_ids(doctrine_repo)


def test_v2_main_noncanonical_payload_serialization_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'json_str = json.dumps(payload, indent=2)',
        'json_str = json.dumps(other_payload, indent=2)',
    )
    assert "V2PROD_MAIN_SERIALIZATION_HANDOFF" in _rule_ids(doctrine_repo)


def test_v2_finalizer_unknown_ordered_records_mutator_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    return ordered_records",
        "    ordered_records.scramble()\n    return ordered_records",
    )
    assert "V2PROD_UNKNOWN_MUTATOR" in _rule_ids(doctrine_repo)


def test_v2_finalizer_unknown_probability_mutator_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        'for key, value in probability_vectors[scored_index].items()\n            }',
        'for key, value in probability_vectors[scored_index].items()\n            }\n'
        '            probabilities.scramble()',
    )
    assert "V2PROD_UNKNOWN_MUTATOR" in _rule_ids(doctrine_repo)


def test_v2_main_unknown_payload_mutator_is_rejected(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload.scramble()\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_UNKNOWN_MUTATOR" in _rule_ids(doctrine_repo)


def test_v2_main_unknown_payload_player_collection_mutator_is_rejected(
    doctrine_repo: Path,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        '        "players":       ordered_records,\n    }\n    json_str = json.dumps(payload, indent=2)',
        '        "players":       ordered_records,\n    }\n'
        '    payload["players"].scramble()\n'
        '    json_str = json.dumps(payload, indent=2)',
    )
    assert "V2PROD_UNKNOWN_MUTATOR" in _rule_ids(doctrine_repo)


@pytest.mark.parametrize(
    ("snippet", "rule_id", "alias_name"),
    (
        ("    ordered_alias = ordered_records\n    ordered_alias.clear()", "V2PROD_PROTECTED_ALIAS_MUTATION", "ordered_alias"),
        ("    alias_1 = ordered_records\n    alias_2 = alias_1\n    alias_2.reverse()", "V2PROD_PROTECTED_ALIAS_MUTATION", "alias_2"),
        ("    ordered_alias = ordered_records\n    ordered_alias.scramble()", "V2PROD_PROTECTED_ALIAS_MUTATION", "ordered_alias"),
        ("    ordered_alias = ordered_records\n    ordered_alias = []", "V2PROD_PROTECTED_ALIAS_REBIND", "ordered_alias"),
    ),
    ids=("clear", "chain_reverse", "unknown_method", "rebind"),
)
def test_v2_protected_ordered_records_aliases_are_rejected(
    doctrine_repo: Path, snippet: str, rule_id: str, alias_name: str,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    return ordered_records",
        snippet + "\n    return ordered_records",
    )
    _assert_alias_finding(doctrine_repo, rule_id, alias_name)


@pytest.mark.parametrize(
    ("snippet", "rule_id", "alias_name"),
    (
        ("    payload_alias = payload\n    payload_alias.update({\"players\": players_raw})", "V2PROD_PROTECTED_ALIAS_MUTATION", "payload_alias"),
        ("    payload_alias = payload\n    payload_alias[\"players\"] = players_raw", "V2PROD_PROTECTED_ALIAS_MUTATION", "payload_alias"),
        ("    payload_alias = payload\n    payload_alias |= {\"players\": players_raw}", "V2PROD_PROTECTED_ALIAS_MUTATION", "payload_alias"),
        ("    payload_alias = payload\n    payload_alias.clear()", "V2PROD_PROTECTED_ALIAS_MUTATION", "payload_alias"),
        ("    payload_alias = payload\n    payload_alias.scramble()", "V2PROD_PROTECTED_ALIAS_MUTATION", "payload_alias"),
        ("    payload_alias = payload\n    payload_alias = other_payload", "V2PROD_PROTECTED_ALIAS_REBIND", "payload_alias"),
    ),
    ids=("update", "subscript", "union", "clear", "unknown_method", "rebind"),
)
def test_v2_protected_payload_aliases_are_rejected(
    doctrine_repo: Path, snippet: str, rule_id: str, alias_name: str,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    json_str = json.dumps(payload, indent=2)",
        snippet + "\n    json_str = json.dumps(payload, indent=2)",
    )
    _assert_alias_finding(doctrine_repo, rule_id, alias_name)


@pytest.mark.parametrize(
    ("snippet", "rule_id", "alias_name"),
    (
        ("    players_alias = payload[\"players\"]\n    players_alias.clear()", "V2PROD_PROTECTED_ALIAS_MUTATION", "players_alias"),
        ("    players_alias = payload[\"players\"]\n    players_alias.append(noncanonical_record)", "V2PROD_PROTECTED_ALIAS_MUTATION", "players_alias"),
        ("    players_alias_1 = payload[\"players\"]\n    players_alias_2 = players_alias_1\n    players_alias_2.reverse()", "V2PROD_PROTECTED_ALIAS_MUTATION", "players_alias_2"),
        ("    players_alias = payload[\"players\"]\n    players_alias.scramble()", "V2PROD_PROTECTED_ALIAS_MUTATION", "players_alias"),
        ("    players_alias = payload[\"players\"]\n    players_alias = players_raw", "V2PROD_PROTECTED_ALIAS_REBIND", "players_alias"),
    ),
    ids=("clear", "append", "chain_reverse", "unknown_method", "rebind"),
)
def test_v2_protected_payload_players_aliases_are_rejected(
    doctrine_repo: Path, snippet: str, rule_id: str, alias_name: str,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    json_str = json.dumps(payload, indent=2)",
        snippet + "\n    json_str = json.dumps(payload, indent=2)",
    )
    _assert_alias_finding(doctrine_repo, rule_id, alias_name)


@pytest.mark.parametrize(
    "snippet",
    (
        '            probability_alias = probabilities\n            probability_alias["winPct"] = 0.0',
        '            probability_alias = probabilities\n            probability_alias.update({"winPct": 0.0})',
        '            probability_alias_1 = probabilities\n            probability_alias_2 = probability_alias_1\n            probability_alias_2.clear()',
    ),
    ids=("subscript", "update", "chain_clear"),
)
def test_v2_protected_probability_aliases_are_rejected(
    doctrine_repo: Path, snippet: str,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "            record = {",
        snippet + "\n            record = {",
    )
    _assert_alias_finding(doctrine_repo, "V2PROD_PROTECTED_ALIAS_MUTATION", "probability_alias")


def test_v2_read_only_protected_alias_is_allowed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    json_str = json.dumps(payload, indent=2)",
        "    payload_alias = payload\n    json_str = json.dumps(payload, indent=2)",
    )
    assert not _errors(doctrine_repo)


@pytest.mark.parametrize(
    ("snippet", "rule_id", "alias_name"),
    (
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias.clear()',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias_1 = payload\n'
            '    payload_alias_2 = payload_alias_1\n'
            '    players_alias = payload_alias_2["players"]\n'
            '    players_alias.clear()',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias_1 = payload_alias["players"]\n'
            '    players_alias_2 = players_alias_1\n'
            '    players_alias_2.reverse()',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias_2",
        ),
        (
            '    payload_alias_1 = payload\n'
            '    payload_alias_2 = payload_alias_1\n'
            '    players_alias_1 = payload_alias_2["players"]\n'
            '    players_alias_2 = players_alias_1\n'
            '    players_alias_2.clear()',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias_2",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias[0] = noncanonical_record',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias.append(noncanonical_record)',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias += [noncanonical_record]',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias.scramble()',
            "V2PROD_PROTECTED_ALIAS_MUTATION",
            "players_alias",
        ),
        (
            '    payload_alias = payload\n'
            '    players_alias = payload_alias["players"]\n'
            '    players_alias = players_raw',
            "V2PROD_PROTECTED_ALIAS_REBIND",
            "players_alias",
        ),
    ),
    ids=(
        "direct_clear",
        "payload_chain_clear",
        "player_chain_reverse",
        "combined_chain_clear",
        "subscript_replace",
        "append",
        "augmented_assignment",
        "unknown_method",
        "rebind",
    ),
)
def test_v2_derived_payload_player_aliases_are_rejected(
    doctrine_repo: Path, snippet: str, rule_id: str, alias_name: str,
) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    json_str = json.dumps(payload, indent=2)",
        snippet + "\n    json_str = json.dumps(payload, indent=2)",
    )
    _assert_alias_finding(doctrine_repo, rule_id, alias_name)


def test_v2_read_only_derived_payload_player_alias_is_allowed(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        "engine/enrich_cards.py",
        "    json_str = json.dumps(payload, indent=2)",
        '    payload_alias = payload\n'
        '    players_alias = payload_alias["players"]\n'
        "    count = len(players_alias)\n"
        "    json_str = json.dumps(payload, indent=2)",
    )
    assert not _errors(doctrine_repo)


def test_v2_finalizer_and_main_handoff_are_approved(doctrine_repo: Path) -> None:
    assert not _errors(doctrine_repo)


def test_v2_producer_integration_precanonical_none_default_is_allowed(doctrine_repo: Path) -> None:
    assert not _errors(doctrine_repo)


def test_v2_producer_integration_unscored_null_defaults_are_allowed(doctrine_repo: Path) -> None:
    assert not _errors(doctrine_repo)


def test_v2_producer_integration_legacy_raw_call_is_rejected(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "engine/enrich_cards.py")
    text = path.read_text(encoding="utf-8")
    marker = "    # ── Canonical finalization boundary"
    assert marker in text
    path.write_text(
        text.replace(marker, "    combine_raw_score(1, 1, 1, 1, 1, 1)\n" + marker, 1),
        encoding="utf-8",
    )
    assert "V2PROD_MAIN_SCORING_AUTHORITY" in _rule_ids(doctrine_repo)


def test_v2_producer_integration_legacy_gate_call_is_rejected(doctrine_repo: Path) -> None:
    path = _path(doctrine_repo, "engine/enrich_cards.py")
    text = path.read_text(encoding="utf-8")
    marker = "    # ── Canonical finalization boundary"
    path.write_text(
        text.replace(marker, "    apply_gates(1, {}, {})\n" + marker, 1),
        encoding="utf-8",
    )
    assert "V2PROD_MAIN_SCORING_AUTHORITY" in _rule_ids(doctrine_repo)


def test_no_repository_writes(doctrine_repo: Path) -> None:
    before = {
        p.relative_to(doctrine_repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in doctrine_repo.rglob("*")
        if p.is_file()
    }
    validator.validate_repository(doctrine_repo, strict=True)
    after = {
        p.relative_to(doctrine_repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in doctrine_repo.rglob("*")
        if p.is_file()
    }
    assert after == before


def test_execution_failure_uses_exit_code_two(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(tmp_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2


def test_contract_failure_uses_exit_code_one(doctrine_repo: Path) -> None:
    _replace(
        doctrine_repo,
        FIXTURE_FILES[0],
        "formula_version=2.0.0",
        "formula_version=9.9.9",
    )
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(doctrine_repo)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "SCORING DOCTRINE FAILED" in completed.stdout
    assert "MARKER_FORMULA_VERSION" in completed.stdout
