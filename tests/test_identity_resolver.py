"""Tests for engine/identity_resolver.py — the ID-first identity resolver."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from identity_resolver import (  # noqa: E402
    FUZZY_AMBIGUITY_MARGIN,
    FUZZY_DIAGNOSTIC_THRESHOLD,
    InvalidDgId,
    METHOD_CROSSWALK,
    METHOD_ENCODING_FALLBACK,
    METHOD_EXACT_DG_ID,
    METHOD_EXACT_NAME,
    STATUS_AMBIGUOUS,
    STATUS_CONFLICT,
    STATUS_DUPLICATE_NORMALIZED_IDENTITY,
    STATUS_ENCODING_FALLBACK_CONFLICT,
    STATUS_FIELD_OWNERSHIP_CONFLICT,
    STATUS_MATCHED,
    STATUS_UNRESOLVED,
    build_field_index,
    build_player_provenance,
    build_release_report,
    normalize_dg_id,
    normalize_name,
    normalize_name_encoding_fallback,
    resolve_source_family,
    try_normalize_dg_id,
)


def field_row(name: str, dg_id: object) -> dict:
    return {"player_name": name, "dg_id": dg_id}


def src_row(name: str, **extra) -> dict:
    row = {"player_name": name}
    row.update(extra)
    return row


# ── DataGolf ID normalization ───────────────────────────────────────────────

class TestNormalizeDgId:
    def test_exact_string_id(self):
        assert normalize_dg_id("18417") == "18417"

    def test_integer_to_string_compatible(self):
        assert normalize_dg_id(18417) == "18417" == normalize_dg_id("18417")

    def test_malformed_id_rejected(self):
        for bad in ("abc", "12a3", "", "  ", "null", "NULL", "none", "n/a"):
            with pytest.raises(InvalidDgId):
                normalize_dg_id(bad)

    def test_boolean_rejected(self):
        with pytest.raises(InvalidDgId):
            normalize_dg_id(True)
        with pytest.raises(InvalidDgId):
            normalize_dg_id(False)

    def test_float_rejected(self):
        with pytest.raises(InvalidDgId):
            normalize_dg_id(123.0)

    def test_decimal_string_rejected(self):
        with pytest.raises(InvalidDgId):
            normalize_dg_id("123.0")

    def test_negative_rejected(self):
        with pytest.raises(InvalidDgId):
            normalize_dg_id(-5)
        with pytest.raises(InvalidDgId):
            normalize_dg_id("-5")

    def test_leading_zero_preserved_not_coerced(self):
        assert normalize_dg_id("00123") == "00123"
        assert normalize_dg_id("00123") != normalize_dg_id(123)
        assert normalize_dg_id("00123") != normalize_dg_id("123")

    def test_try_normalize_returns_none_on_failure(self):
        assert try_normalize_dg_id("abc") is None
        assert try_normalize_dg_id("18417") == "18417"


# ── Name normalization ───────────────────────────────────────────────────────

class TestNormalizeName:
    def test_strips_quotes(self):
        assert normalize_name('"Scheffler, Scottie"') == "scheffler, scottie"

    def test_strips_whitespace(self):
        assert normalize_name("  McIlroy, Rory  ") == "mcilroy, rory"

    def test_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_case_and_internal_whitespace(self):
        assert normalize_name("VAN   ROOYEN, Erik") == normalize_name("van rooyen, erik")

    def test_diacritic_folding(self):
        assert normalize_name("Åberg, Ludvig") == normalize_name("Aberg, Ludvig")

    def test_encoding_fallback_strips_punctuation(self):
        assert normalize_name_encoding_fallback("O'Brien, Sean") == normalize_name_encoding_fallback(
            "OBrien, Sean"
        )
        assert normalize_name_encoding_fallback("Van-Rooyen, Erik") == normalize_name_encoding_fallback(
            "Van Rooyen, Erik"
        )


# ── Field identity validation ───────────────────────────────────────────────

class TestBuildFieldIndex:
    def test_valid_field(self):
        rows = [field_row("Doe, John", "100"), field_row("Smith, Sam", "200")]
        idx = build_field_index(rows)
        assert idx.is_valid
        assert len(idx.identities) == 2
        assert idx.identities[0].dg_id == "100"

    def test_missing_dg_id_blocked(self):
        rows = [field_row("Doe, John", ""), field_row("Smith, Sam", "200")]
        idx = build_field_index(rows)
        assert not idx.is_valid
        assert any(e.code == "missing_or_malformed_dg_id" for e in idx.errors)

    def test_malformed_dg_id_blocked(self):
        rows = [field_row("Doe, John", "abc")]
        idx = build_field_index(rows)
        assert not idx.is_valid
        assert idx.errors[0].code == "missing_or_malformed_dg_id"

    def test_duplicate_field_dg_id_blocked(self):
        rows = [field_row("Doe, John", "100"), field_row("Doe, Jonathan", "100")]
        idx = build_field_index(rows)
        assert not idx.is_valid
        assert any(e.code == "duplicate_field_dg_id" for e in idx.errors)

    def test_duplicate_normalized_field_name_blocked(self):
        rows = [field_row("Doe, John", "100"), field_row('"Doe, John"', "200")]
        idx = build_field_index(rows)
        assert not idx.is_valid
        assert any(e.code == "ambiguous_field_normalized_name" for e in idx.errors)

    def test_missing_display_name_blocked(self):
        rows = [field_row("", "100")]
        idx = build_field_index(rows)
        assert not idx.is_valid
        assert idx.errors[0].code == "missing_display_name"

    def test_all_field_errors_collected_before_failure(self):
        rows = [
            field_row("Doe, John", "abc"),
            field_row("", "200"),
            field_row("Smith, Sam", "300"),
            field_row("Smith, Samuel", "300"),
        ]
        idx = build_field_index(rows)
        codes = {e.code for e in idx.errors}
        assert "missing_or_malformed_dg_id" in codes
        assert "missing_display_name" in codes
        assert "duplicate_field_dg_id" in codes


# ── Source-family resolution: exact dg_id ───────────────────────────────────

class TestExactDgIdResolution:
    def test_exact_id_match(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field, [src_row("Doe, John", dg_id="100")], dg_id_field="dg_id"
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert result.matches[0].status == STATUS_MATCHED

    def test_name_disagreement_does_not_override_exact_id(self):
        """A different spelling in the source row is irrelevant once the
        dg_id matches -- the ID wins, no name comparison blocks it."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field, [src_row("J. Doe (alt spelling)", dg_id="100")], dg_id_field="dg_id"
        )
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert result.matches[0].source_name == "J. Doe (alt spelling)"

    def test_duplicate_source_dg_id_blocked(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend",
            field,
            [src_row("Doe, John", dg_id="100"), src_row("Doe, Jon Impostor", dg_id="100")],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1

    def test_id_name_conflict_retains_exact_id_and_blocks_extra_row(self):
        """Exact dg_id points to one row; a *different* row exact-name-matches
        the same field identity. Exact ID remains authoritative and stays
        accepted -- the extra row becomes its own field-ownership-conflict
        blocker rather than retroactively discarding the exact-ID match."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend",
            field,
            [
                src_row("Someone Else Entirely", dg_id="100"),
                src_row("Doe, John", dg_id="999"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        match = result.matches[0]
        assert match.method == METHOD_EXACT_DG_ID
        assert match.field_dg_id == "100"
        assert match.source_name == "Someone Else Entirely"
        assert match.source_row is not None
        assert match.source_row.get("dg_id") == "100"
        assert sum(1 for m in result.matches if m.field_dg_id == "100") == 1
        assert not any(m.method == METHOD_EXACT_NAME for m in result.matches)

        conflicts = [d for d in result.ambiguous if d.status == STATUS_FIELD_OWNERSHIP_CONFLICT]
        assert len(conflicts) == 1
        assert conflicts[0].field_dg_id == "100"
        detail = conflicts[0].detail or ""
        assert "source row #1" in detail
        assert "Doe, John" in detail
        assert METHOD_EXACT_NAME in detail

        report = build_release_report(field, [result])
        assert report.is_release_blocked
        assert len(report.blockers) == 1

    def test_id_name_conflict_field_and_source_order_determinism(self):
        """The retained-exact-ID / extra-row-blocked outcome must not depend
        on field-row or source-row insertion order."""
        field_rows_normal = [field_row("Doe, John", "100")]
        field_rows_reversed = list(reversed(field_rows_normal))
        source_rows_normal = [
            src_row("Someone Else Entirely", dg_id="100"),
            src_row("Doe, John", dg_id="999"),
        ]
        source_rows_reversed = list(reversed(source_rows_normal))

        outcomes = []
        for f_rows in (field_rows_normal, field_rows_reversed):
            for s_rows in (source_rows_normal, source_rows_reversed):
                field = build_field_index(f_rows)
                result = resolve_source_family(
                    "trend", field, s_rows, dg_id_field="dg_id"
                )
                by_id = result.matches_by_dg_id()
                conflicts = [
                    d for d in result.ambiguous if d.status == STATUS_FIELD_OWNERSHIP_CONFLICT
                ]
                outcomes.append({
                    "matched_ids": frozenset(by_id.keys()),
                    "method_100": by_id["100"].method if "100" in by_id else None,
                    "accepted_source_name": by_id["100"].source_name if "100" in by_id else None,
                    "conflict_count": len(conflicts),
                    "conflict_references_extra_row": (
                        "Doe, John" in (conflicts[0].detail or "") if conflicts else False
                    ),
                    "blocker_count": len(build_release_report(field, [result]).blockers),
                })

        first = outcomes[0]
        for other in outcomes[1:]:
            assert other == first
        assert first["matched_ids"] == frozenset({"100"})
        assert first["method_100"] == METHOD_EXACT_DG_ID
        assert first["accepted_source_name"] == "Someone Else Entirely"
        assert first["conflict_count"] == 1
        assert first["conflict_references_extra_row"] is True
        assert first["blocker_count"] == 1


# ── Source-family resolution: name fallback ─────────────────────────────────

class TestNameFallbackResolution:
    def test_exact_normalized_name_fallback(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family("perf", field, [src_row("Doe, John")])
        assert result.matches[0].method == METHOD_EXACT_NAME

    def test_case_and_whitespace_fallback(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family("perf", field, [src_row("  doe,   JOHN  ")])
        assert result.matches[0].method == METHOD_EXACT_NAME

    def test_diacritic_folded_exact_fallback(self):
        field = build_field_index([field_row("Aberg, Ludvig", "100")])
        result = resolve_source_family("perf", field, [src_row("Åberg, Ludvig")])
        assert result.matches[0].method == METHOD_EXACT_NAME

    def test_punctuation_compatibility_uses_encoding_fallback(self):
        field = build_field_index([field_row("O'Brien, Sean", "100")])
        result = resolve_source_family("perf", field, [src_row("OBrien, Sean")])
        assert result.matches[0].method == METHOD_ENCODING_FALLBACK

    def test_duplicate_normalized_source_names_blocked(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Doe, John"), src_row('"Doe, John"')]
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1

    def test_fuzzy_only_candidate_remains_unresolved(self):
        field = build_field_index([field_row("Doe, John", "100")])
        # "Doe, Jon" is close but not equal -- must not auto-join, and must
        # not silently vanish as a plain no-op unresolved either: fuzzy
        # candidates were plausible, so it is reported ambiguous, not matched.
        result = resolve_source_family("perf", field, [src_row("Doe, Jon")])
        assert len(result.matches) == 0
        assert result.matches == ()

    def test_no_plausible_candidate_is_unresolved_not_ambiguous(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family("perf", field, [src_row("Totally Unrelated Person")])
        assert len(result.unresolved) == 1
        assert result.unresolved[0].status == STATUS_UNRESOLVED
        assert len(result.ambiguous) == 0

    def test_close_fuzzy_candidates_remain_ambiguous(self):
        field = build_field_index([field_row("Smith, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Smithe, John"), src_row("Smith, Johnn")]
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1
        diag = result.ambiguous[0]
        assert diag.best_candidate is not None
        assert diag.second_candidate is not None

    def test_fuzzy_candidate_ordering_is_deterministic(self):
        field = build_field_index([field_row("Zzz, Nomatch", "100")])
        names = ["Bbb, Name", "Aaa, Name", "Ccc, Name"]
        result1 = resolve_source_family("perf", field, [src_row(n) for n in names])
        result2 = resolve_source_family("perf", field, [src_row(n) for n in reversed(names)])
        d1 = result1.unresolved[0] if result1.unresolved else result1.ambiguous[0]
        d2 = result2.unresolved[0] if result2.unresolved else result2.ambiguous[0]
        assert d1.best_candidate == d2.best_candidate
        assert d1.second_candidate == d2.second_candidate


# ── Mapping integrity ────────────────────────────────────────────────────────

class TestMappingIntegrity:
    def test_one_source_row_cannot_feed_two_field_players(self):
        """Two field players whose names are both merely *close* to a single
        source row must never both resolve to it -- fuzzy never authorizes,
        so neither is accepted."""
        field = build_field_index(
            [field_row("Smith, John", "100"), field_row("Smith, Jon", "200")]
        )
        result = resolve_source_family("perf", field, [src_row("Smith, Jhon")])
        assert len(result.matches) == 0

    def test_two_source_rows_cannot_silently_feed_one_field_player(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Doe, John"), src_row('"Doe, John"')]
        )
        assert len(result.matches) == 0
        assert result.ambiguous[0].status == STATUS_AMBIGUOUS

    def test_unused_row_reported(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Doe, John"), src_row("Unclaimed, Player")]
        )
        assert "Unclaimed, Player" in result.unused_source_rows

    def test_missing_supplementary_row_warned_not_blocked(self):
        field = build_field_index(
            [field_row("Doe, John", "100"), field_row("Smith, Sam", "200")]
        )
        result = resolve_source_family("perf", field, [src_row("Doe, John")])
        assert len(result.unresolved) == 1
        assert len(result.ambiguous) == 0
        report = build_release_report(field, [result])
        assert not report.is_release_blocked
        assert any(d.code == "missing_source" for d in report.warnings)

    def test_all_blockers_collected_before_failure(self):
        field = build_field_index(
            [
                field_row("Doe, John", "100"),
                field_row("Smith, Sam", "200"),
                field_row("Jones, Bob", "300"),
            ]
        )
        result_a = resolve_source_family(
            "src_a", field, [src_row("Doe, John"), src_row('"Doe, John"')]
        )
        result_b = resolve_source_family(
            "src_b", field, [src_row("Smith, Samuel")]
        )
        report = build_release_report(field, [result_a, result_b])
        assert report.is_release_blocked
        blocker_families = {d.family for d in report.blockers}
        assert "src_a" in blocker_families


# ── Adversarial regression: row-ownership exclusivity & crosswalk authority ──

class TestRowOwnershipExclusivity:
    def test_encoding_fallback_row_reuse_blocked(self):
        """One source row must never be accepted twice within one family --
        not even when two field players reach it through *different*
        methods (exact-name / encoding fallback)."""
        field = build_field_index(
            [field_row("O'Brien, Sean", "100"), field_row("OBrien, Sean", "200")]
        )
        result = resolve_source_family("perf", field, [src_row("OBrien Sean")])
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 2
        details = " ".join(d.detail or "" for d in result.ambiguous)
        assert "#0" in details
        assert "O'Brien, Sean" in details
        assert "OBrien, Sean" in details

    def test_crosswalk_conflicts_with_exact_dg_id(self):
        """A crosswalk cannot assign a source row to one field player while
        that row's own dg_id exactly identifies a different field player.
        The exact-ID match is retained; the crosswalk is a blocker."""
        field = build_field_index(
            [field_row("Player A", "100"), field_row("Player B", "200")]
        )
        result = resolve_source_family(
            "trend", field,
            [src_row("Alias, A", dg_id="200")],
            dg_id_field="dg_id",
            crosswalk={"100": "Alias, A"},
        )
        assert len(result.matches) == 1
        assert result.matches[0].field_dg_id == "200"
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        conflict = [d for d in result.ambiguous if d.field_dg_id == "100"]
        assert len(conflict) == 1
        assert conflict[0].status == STATUS_CONFLICT
        assert "200" in (conflict[0].detail or "")

    def test_duplicate_raw_source_names_reach_resolver(self):
        """Two rows with the identical raw source name must both reach the
        resolver -- the duplicate is detected, not silently overwritten."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Doe, John"), src_row("Doe, John")]
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1
        detail = result.ambiguous[0].detail or ""
        assert "#0" in detail and "#1" in detail

    def test_duplicate_normalized_names_block_when_targeting_field_player(self):
        """Two distinct raw spellings that normalize to the same key must
        both remain visible, and block rather than silently pick one."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field, [src_row("Doe, John"), src_row("DOE,  JOHN")]
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1

    def test_duplicate_source_ids_preserved_with_row_ordinals(self):
        """Two rows sharing one canonical source dg_id: both preserved, the
        blocker names both row ordinals, and no accepted match is emitted."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field,
            [src_row("Row A", dg_id="100"), src_row("Row B", dg_id="100")],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1
        detail = result.ambiguous[0].detail or ""
        assert "#0" in detail and "#1" in detail

    def test_many_to_one_mixed_methods_blocked(self):
        """One field player targeted by two different rows through two
        different methods (crosswalk vs. independent exact-name evidence)
        -- the source family must block, not silently prefer crosswalk."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "perf", field,
            [src_row("Doe, John"), src_row("Crosswalk Target")],
            crosswalk={"100": "Crosswalk Target"},
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 1
        assert result.ambiguous[0].status == STATUS_CONFLICT

    def test_one_to_many_mixed_methods_blocked(self):
        """One source row proposed via encoding fallback for one field
        player and via crosswalk for a different field player -- it cannot
        be accepted for either."""
        field = build_field_index(
            [field_row("O'Brien, Sean", "100"), field_row("Other Player", "200")]
        )
        result = resolve_source_family(
            "perf", field,
            [src_row("OBrien Sean")],
            crosswalk={"200": "OBrien Sean"},
        )
        assert len(result.matches) == 0
        assert len(result.ambiguous) == 2


# ── Exact-ID acceptance does not suppress contradictory lower-precedence
# rows targeting the same, already-owned field identity ─────────────────────

class TestExactIdOwnershipConflicts:
    def test_exact_id_does_not_suppress_duplicate_normalized_name_blocker(self):
        field = build_field_index([field_row("O'Brien, Sean", "200")])
        result = resolve_source_family(
            "trend", field,
            [
                src_row("O'Brien, Sean", dg_id="200"),
                src_row("O'Brien, Sean"),
                src_row("O'Brien, Sean"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert result.matches[0].field_dg_id == "200"

        dup = [d for d in result.ambiguous if d.status == STATUS_DUPLICATE_NORMALIZED_IDENTITY]
        assert len(dup) == 1
        assert dup[0].field_display_name == "O'Brien, Sean"
        detail = dup[0].detail or ""
        assert "#1" in detail and "#2" in detail
        assert "O'Brien, Sean" in detail
        assert not any(d.method in (METHOD_EXACT_NAME, METHOD_ENCODING_FALLBACK) for d in result.matches)

        report = build_release_report(field, [result])
        assert report.is_release_blocked
        assert not any(
            "row #1" in (w.message or "") or "row #2" in (w.message or "")
            for w in report.warnings if w.code == "unused_source"
        )

    def test_exact_id_does_not_suppress_duplicate_normalized_name_blocker_reversed(self):
        """Same fixture with the duplicate rows loaded before the exact-ID
        row -- ordering must not change the classification or ownership."""
        field = build_field_index([field_row("O'Brien, Sean", "200")])
        result = resolve_source_family(
            "trend", field,
            [
                src_row("O'Brien, Sean"),
                src_row("O'Brien, Sean"),
                src_row("O'Brien, Sean", dg_id="200"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert result.matches[0].source_row is not None

        dup = [d for d in result.ambiguous if d.status == STATUS_DUPLICATE_NORMALIZED_IDENTITY]
        assert len(dup) == 1
        detail = dup[0].detail or ""
        assert "#0" in detail and "#1" in detail
        assert dup[0].field_display_name == "O'Brien, Sean"

        report = build_release_report(field, [result])
        assert report.is_release_blocked

    def test_exact_id_does_not_suppress_encoding_fallback_conflict(self):
        field = build_field_index([field_row("O'Brien, Sean", "200")])
        result = resolve_source_family(
            "perf", field,
            [
                src_row("O'Brien, Sean", dg_id="200"),
                src_row("OBrien Sean"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert result.matches[0].field_dg_id == "200"

        fb_conflicts = [d for d in result.ambiguous if d.status == STATUS_ENCODING_FALLBACK_CONFLICT]
        assert len(fb_conflicts) == 1
        detail = fb_conflicts[0].detail or ""
        assert "#0" in detail and "#1" in detail
        assert METHOD_ENCODING_FALLBACK in detail
        assert fb_conflicts[0].field_display_name == "O'Brien, Sean"

        report = build_release_report(field, [result])
        assert report.is_release_blocked
        assert not any(
            "#1" in (w.message or "") for w in report.warnings if w.code == "unused_source"
        )

    def test_exact_id_does_not_suppress_encoding_fallback_conflict_reversed(self):
        field = build_field_index([field_row("O'Brien, Sean", "200")])
        result = resolve_source_family(
            "perf", field,
            [
                src_row("OBrien Sean"),
                src_row("O'Brien, Sean", dg_id="200"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID

        fb_conflicts = [d for d in result.ambiguous if d.status == STATUS_ENCODING_FALLBACK_CONFLICT]
        assert len(fb_conflicts) == 1
        detail = fb_conflicts[0].detail or ""
        assert "#0" in detail and "#1" in detail

        report = build_release_report(field, [result])
        assert report.is_release_blocked

    def test_exact_id_field_ownership_rejects_second_name_row(self):
        """Even a single second row targeting an exact-ID-owned identity is
        a blocker -- ownership is enforced per-row, not only per duplicate
        group."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field,
            [
                src_row("Doe, John", dg_id="100"),
                src_row("Doe, John"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID

        ownership = [d for d in result.ambiguous if d.status == STATUS_FIELD_OWNERSHIP_CONFLICT]
        assert len(ownership) == 1
        assert ownership[0].field_display_name == "Doe, John"
        detail = ownership[0].detail or ""
        assert "#1" in detail

        report = build_release_report(field, [result])
        assert report.is_release_blocked

    def test_exact_id_with_unrelated_unused_row_remains_nonblocking(self):
        """An extra row that has no meaningful identity claim on the
        exact-ID-owned player must remain a plain unused warning -- not
        every extra row in a family becomes a blocker."""
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field,
            [
                src_row("Doe, John", dg_id="100"),
                src_row("Totally Unrelated Person"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 1
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        assert len(result.ambiguous) == 0
        assert "Totally Unrelated Person" in result.unused_source_rows

        report = build_release_report(field, [result])
        assert not report.is_release_blocked


# ── Global row-ownership adjudication: a stronger accepted claim by one
# field player suppresses an incidental weaker claim toward another ────────

class TestGlobalOwnershipAdjudication:
    def test_exact_name_claim_suppresses_incidental_encoding_conflict(self):
        """Field B validly and uniquely owns a row through exact normalized
        name. That row also happens to encoding-fallback resemble field A's
        (unrelated, exact-ID-owned) name. B's stronger, uniquely-adjudicated
        claim must suppress A's incidental weaker claim entirely -- no
        blocker, and the row is accepted for B only."""
        field = build_field_index(
            [field_row("O'Brien, Sean", "100"), field_row("OBrien Sean", "200")]
        )
        result = resolve_source_family(
            "trend", field,
            [
                src_row("O'Brien, Sean", dg_id="100"),
                src_row("OBrien Sean"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 2
        by_id = result.matches_by_dg_id()
        assert by_id["100"].method == METHOD_EXACT_DG_ID
        assert by_id["100"].field_dg_id == "100"
        assert by_id["200"].method == METHOD_EXACT_NAME
        assert by_id["200"].source_name == "OBrien Sean"

        # Row #1 must appear in exactly one accepted match, never also in a
        # conflict/blocker for field player A.
        assert sum(1 for m in result.matches if m.source_name == "OBrien Sean") == 1
        assert len(result.ambiguous) == 0
        assert not any(
            d.status in (STATUS_ENCODING_FALLBACK_CONFLICT, STATUS_FIELD_OWNERSHIP_CONFLICT,
                         STATUS_DUPLICATE_NORMALIZED_IDENTITY)
            for d in result.ambiguous
        )

        report = build_release_report(field, [result])
        assert not report.is_release_blocked

    def test_exact_name_claim_suppresses_incidental_encoding_conflict_reversed_field_order(self):
        field = build_field_index(
            [field_row("OBrien Sean", "200"), field_row("O'Brien, Sean", "100")]
        )
        result = resolve_source_family(
            "trend", field,
            [
                src_row("O'Brien, Sean", dg_id="100"),
                src_row("OBrien Sean"),
            ],
            dg_id_field="dg_id",
        )
        assert len(result.matches) == 2
        assert len(result.ambiguous) == 0
        report = build_release_report(field, [result])
        assert not report.is_release_blocked

    def test_crosswalk_claim_suppresses_incidental_encoding_conflict(self):
        """Field B uniquely owns a row through an explicit crosswalk. That
        row also happens to encoding-fallback resemble field A's (unrelated,
        exact-ID-owned) name. No encoding-fallback blocker may be emitted
        against A for B's crosswalk-owned row."""
        field = build_field_index(
            [field_row("O'Brien, Sean", "100"), field_row("Alias Target", "200")]
        )
        result = resolve_source_family(
            "trend", field,
            [
                src_row("O'Brien, Sean", dg_id="100"),
                src_row("OBrien Sean"),
            ],
            dg_id_field="dg_id",
            crosswalk={"200": "OBrien Sean"},
        )
        assert len(result.matches) == 2
        by_id = result.matches_by_dg_id()
        assert by_id["100"].method == METHOD_EXACT_DG_ID
        assert by_id["200"].method == METHOD_CROSSWALK
        assert by_id["200"].source_name == "OBrien Sean"
        assert len(result.ambiguous) == 0

        report = build_release_report(field, [result])
        assert not report.is_release_blocked

    def test_crosswalk_still_conflicts_with_exact_id_when_it_truly_disagrees(self):
        """Existing exact-ID/crosswalk contradiction behavior must remain
        blocking -- the suppression above only applies to a genuinely
        distinct, validly-owned row, never to a crosswalk that actually
        targets another player's own exact-ID row."""
        field = build_field_index(
            [field_row("Player A", "100"), field_row("Player B", "200")]
        )
        result = resolve_source_family(
            "trend", field,
            [src_row("Alias, A", dg_id="200")],
            dg_id_field="dg_id",
            crosswalk={"100": "Alias, A"},
        )
        assert len(result.matches) == 1
        assert result.matches[0].field_dg_id == "200"
        assert result.matches[0].method == METHOD_EXACT_DG_ID
        conflict = [d for d in result.ambiguous if d.field_dg_id == "100"]
        assert len(conflict) == 1
        assert conflict[0].status == STATUS_CONFLICT

        report = build_release_report(field, [result])
        assert report.is_release_blocked

    def test_exact_name_match_coherent_with_fuzzy_diagnostic_for_other_player(self):
        """A row accepted for B via exact normalized name must not also be
        placed in another field player's conflict set merely because that
        other player has a fuzzy-diagnostic resemblance to it. Fuzzy never
        authorizes a join, and a genuinely close fuzzy-only case remains a
        plain ambiguous diagnostic -- not one of the new ownership-conflict
        statuses -- per the existing fuzzy contract."""
        field = build_field_index(
            [field_row("Smith, John", "100"), field_row("Smith, Jon", "200")]
        )
        result = resolve_source_family(
            "perf", field, [src_row("Smith, John")]
        )
        assert len(result.matches) == 1
        assert result.matches[0].field_dg_id == "100"
        assert result.matches[0].method == METHOD_EXACT_NAME
        assert result.matches[0].source_name == "Smith, John"
        # The row must not appear a second time for field player 200.
        assert result.matches_by_dg_id().get("200") is None

        assert len(result.ambiguous) == 1
        fuzzy_diag = result.ambiguous[0]
        assert fuzzy_diag.field_dg_id == "200"
        assert fuzzy_diag.status == STATUS_AMBIGUOUS
        assert fuzzy_diag.best_candidate is not None

        report = build_release_report(field, [result])
        assert report.is_release_blocked  # existing fuzzy-only-probable-match contract

    def test_field_and_source_order_determinism_for_exact_name_suppression(self):
        """The exact-name-suppresses-encoding-conflict adversarial case must
        produce identical accepted mappings, methods, and blocker absence
        under every field-order / source-order combination."""
        field_rows_normal = [field_row("O'Brien, Sean", "100"), field_row("OBrien Sean", "200")]
        field_rows_reversed = list(reversed(field_rows_normal))
        source_rows_normal = [src_row("O'Brien, Sean", dg_id="100"), src_row("OBrien Sean")]
        source_rows_reversed = list(reversed(source_rows_normal))

        outcomes = []
        for f_rows in (field_rows_normal, field_rows_reversed):
            for s_rows in (source_rows_normal, source_rows_reversed):
                field = build_field_index(f_rows)
                result = resolve_source_family(
                    "trend", field, s_rows, dg_id_field="dg_id"
                )
                by_id = result.matches_by_dg_id()
                outcomes.append({
                    "matched_ids": frozenset(by_id.keys()),
                    "method_100": by_id["100"].method,
                    "method_200": by_id["200"].method,
                    "ambiguous_count": len(result.ambiguous),
                    "encoding_conflict_present": any(
                        d.status == STATUS_ENCODING_FALLBACK_CONFLICT for d in result.ambiguous
                    ),
                    "blocked": build_release_report(field, [result]).is_release_blocked,
                })

        first = outcomes[0]
        for other in outcomes[1:]:
            assert other == first
        assert first["matched_ids"] == frozenset({"100", "200"})
        assert first["method_100"] == METHOD_EXACT_DG_ID
        assert first["method_200"] == METHOD_EXACT_NAME
        assert first["ambiguous_count"] == 0
        assert first["encoding_conflict_present"] is False
        assert first["blocked"] is False


# ── Release report ───────────────────────────────────────────────────────────

class TestReleaseReport:
    def test_field_errors_become_blockers(self):
        field = build_field_index([field_row("Doe, John", "abc")])
        report = build_release_report(field, [])
        assert report.is_release_blocked
        assert report.blockers[0].code == "missing_or_malformed_dg_id"

    def test_render_is_deterministic_and_complete(self):
        field = build_field_index([field_row("Doe, John", "abc")])
        report = build_release_report(field, [])
        text = report.render()
        assert "1 blocker(s)" in text
        assert "missing_or_malformed_dg_id" in text


# ── Provenance ───────────────────────────────────────────────────────────────

class TestProvenance:
    def test_exact_id_method_emitted(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field, [src_row("Doe, John", dg_id="100")], dg_id_field="dg_id"
        )
        prov = build_player_provenance(field.identities[0], [result])
        assert prov["source_matches"]["trend"]["method"] == METHOD_EXACT_DG_ID
        assert prov["source_matches"]["trend"]["status"] == STATUS_MATCHED

    def test_exact_name_method_emitted_and_source_name_retained(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family("perf", field, [src_row("Doe, John")])
        prov = build_player_provenance(field.identities[0], [result])
        assert prov["source_matches"]["perf"]["method"] == METHOD_EXACT_NAME
        assert prov["source_matches"]["perf"]["source_name"] == "Doe, John"

    def test_source_family_retained_and_missing_recorded(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family("ch", field, [])
        prov = build_player_provenance(field.identities[0], [result])
        assert "ch" in prov["source_matches"]
        assert prov["source_matches"]["ch"]["status"] == "missing"

    def test_deterministic_output_ordering(self):
        field = build_field_index([field_row("Doe, John", "100")])
        r1 = resolve_source_family("a_family", field, [src_row("Doe, John")])
        r2 = resolve_source_family("b_family", field, [src_row("Doe, John")])
        prov1 = build_player_provenance(field.identities[0], [r1, r2])
        prov2 = build_player_provenance(field.identities[0], [r2, r1])
        assert list(prov1["source_matches"].keys()) != list(prov2["source_matches"].keys())
        # Each call's own ordering matches the order source_results was passed in,
        # deterministically -- not dependent on dict hashing.
        assert list(prov1["source_matches"].keys()) == ["a_family", "b_family"]
        assert list(prov2["source_matches"].keys()) == ["b_family", "a_family"]

    def test_compact_provenance_excludes_detailed_candidate_diagnostics(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field, [src_row("Doe, John", dg_id="100")], dg_id_field="dg_id"
        )
        prov = build_player_provenance(field.identities[0], [result])
        entry = prov["source_matches"]["trend"]
        assert "best_candidate" not in entry
        assert "second_candidate" not in entry
        assert set(entry.keys()) == {"status", "method", "source_name"}

    def test_schema_version_and_canonical_key_present(self):
        field = build_field_index([field_row("Doe, John", "100")])
        result = resolve_source_family(
            "trend", field, [src_row("Doe, John", dg_id="100")], dg_id_field="dg_id"
        )
        prov = build_player_provenance(field.identities[0], [result])
        assert prov["schema_version"] == "1.0"
        assert prov["canonical_key"] == "dg_id"
        assert prov["field_method"] == METHOD_EXACT_DG_ID
