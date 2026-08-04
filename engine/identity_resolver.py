"""engine/identity_resolver.py
ID-first player identity resolver with match provenance for PGA VenueDNA.

Narrowly scoped to player identity matching: DataGolf ID normalization,
canonical name normalization, per-source-family resolution precedence,
fuzzy diagnostics (never authorizing a join), mapping-integrity detection,
and a deterministic release-blocking identity report.

This module does not contain scoring, venue, probability, file-output, or
event-specific logic. It performs no filesystem or database I/O.

Resolution precedence per source family:
  1. Exact canonical dg_id
  2. Optional explicit crosswalk supplied by the caller (in-memory only)
  3. Unique exact canonical normalized name
  4. Documented encoding/punctuation-normalized exact name
  5. Unresolved or ambiguous (fuzzy is diagnostic-only; never authorizes a join)
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field as dataclass_field
from typing import Mapping, Sequence

# ── Constants ────────────────────────────────────────────────────────────────

FUZZY_DIAGNOSTIC_THRESHOLD = 0.85
FUZZY_AMBIGUITY_MARGIN = 0.03

FIELD_METHOD_EXACT_DG_ID = "exact_dg_id"
METHOD_EXACT_DG_ID = "exact_dg_id"
METHOD_CROSSWALK = "crosswalk"
METHOD_EXACT_NAME = "exact_name"
METHOD_ENCODING_FALLBACK = "encoding_fallback"

STATUS_MATCHED = "matched"
STATUS_UNRESOLVED = "unresolved"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_CONFLICT = "conflict"
STATUS_MISSING = "missing"

# Field-ownership conflicts: a lower-precedence source row independently
# targets a field player already owned by an accepted exact-dg_id match.
# Exact-ID acceptance does not suppress these -- they remain release blockers.
STATUS_DUPLICATE_NORMALIZED_IDENTITY = "duplicate_normalized_source_identity"
STATUS_FIELD_OWNERSHIP_CONFLICT = "field_ownership_conflict"
STATUS_ENCODING_FALLBACK_CONFLICT = "encoding_fallback_conflict"

SEVERITY_BLOCKER = "BLOCKER"
SEVERITY_WARNING = "WARNING"

_NULL_SENTINELS = {"null", "none", "n/a", "na", "nan"}


# ── DataGolf ID normalization ──────────────────────────────────────────────

class InvalidDgId(ValueError):
    """Raised when a raw value cannot be safely normalized to a canonical dg_id."""


def normalize_dg_id(raw: object) -> str:
    """Normalize a raw DataGolf ID to its canonical decimal-string form.

    Accepts a non-negative ``int``, or a digit-only ``str`` after trimming
    whitespace. Rejects ``bool``, ``float``, decimal strings (``"123.0"``),
    empty strings, textual null sentinels, negative values, and any
    non-digit content. Leading zeros are preserved exactly -- ``"00123"``
    and ``"123"`` are distinct canonical values and must never silently
    collapse into each other.
    """
    if isinstance(raw, bool):
        raise InvalidDgId(f"dg_id must not be a boolean: {raw!r}")

    if isinstance(raw, int):
        if raw < 0:
            raise InvalidDgId(f"dg_id must not be negative: {raw!r}")
        return str(raw)

    if isinstance(raw, float):
        raise InvalidDgId(f"dg_id must not be a float: {raw!r}")

    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise InvalidDgId("dg_id must not be empty")
        if s.lower() in _NULL_SENTINELS:
            raise InvalidDgId(f"dg_id is a null sentinel: {raw!r}")
        if s.startswith("-"):
            raise InvalidDgId(f"dg_id must not be negative: {raw!r}")
        if not s.isdigit():
            raise InvalidDgId(f"dg_id must contain only digits: {raw!r}")
        return s

    raise InvalidDgId(f"dg_id has an unsupported type: {type(raw).__name__}")


def try_normalize_dg_id(raw: object) -> str | None:
    """Same as :func:`normalize_dg_id` but returns ``None`` instead of raising."""
    try:
        return normalize_dg_id(raw)
    except InvalidDgId:
        return None


# ── Name normalization ──────────────────────────────────────────────────────

def normalize_name(raw: str | None) -> str:
    """Canonical identity-matching name key.

    Trims surrounding whitespace and quote characters, applies NFD Unicode
    normalization with diacritic folding (strips combining marks), case-folds,
    removes periods (abbreviation compatibility), and collapses internal
    whitespace runs to single spaces. Does not guess or invert "Last, First"
    formatting -- callers needing "First Last" must convert explicitly
    before normalizing; this function only normalizes the string it is given.
    """
    if not raw:
        return ""
    s = str(raw).strip().strip('"').strip("'")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace(".", "")
    s = " ".join(s.split())
    return s


_WORD_SEPARATORS = re.compile(r"[-,]")
_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9 ]")


def normalize_name_encoding_fallback(raw: str | None) -> str:
    """A deeper, documented fallback tier beyond :func:`normalize_name`.

    Applies the same base normalization, then folds hyphens and commas to
    a single space (word separators) and strips every remaining
    non-alphanumeric character (apostrophes, periods) so that punctuation
    and compound-name formatting differences across vendor exports (e.g.
    "O'Brien" vs "OBrien", "Van-Rooyen" vs "Van Rooyen") can still resolve
    to the same key. This is a strictly wider key than :func:`normalize_name`
    and is only consulted when the primary exact key finds no candidate.
    """
    base = normalize_name(raw)
    base = _WORD_SEPARATORS.sub(" ", base)
    stripped = _NON_ALNUM_SPACE.sub("", base)
    return " ".join(stripped.split())


# ── Row-preserving source rows ──────────────────────────────────────────────

@dataclass(frozen=True)
class SourceRow:
    """One raw row from a supplementary source family, preserved intact.

    Loaders must construct one ``SourceRow`` per CSV data row -- including
    duplicates -- and must never collapse rows into a name-keyed dict before
    identity resolution runs. The resolver, not the loader, decides whether
    a duplicate raw name, duplicate normalized name, or duplicate dg_id is a
    release blocker.

    ``dg_id`` holds the *raw*, not-yet-normalized value from the source row
    (or ``None`` if this source family carries no id column); the resolver
    normalizes it internally. ``payload`` is the already-derived scoring
    value for this row (a dict of metric fields, or a bare scalar for
    single-value sources) -- preserved so that, after a row is accepted by
    the resolver, its value can be read back directly from the accepted
    match rather than through any name-keyed re-lookup that could silently
    resolve to a different, later-loaded duplicate.
    """

    source_name: str
    dg_id: str | None
    payload: object
    row_number: int


# ── Field identity ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FieldIdentity:
    """One canonical player from the field roster (e.g. pga_field.csv)."""

    display_name: str
    normalized_name: str
    dg_id: str
    row: Mapping[str, object]


@dataclass(frozen=True)
class FieldIdentityError:
    """A blocking defect discovered while building the canonical field index."""

    code: str
    message: str
    display_name: str | None = None
    dg_id: str | None = None


@dataclass(frozen=True)
class FieldIndex:
    """The validated canonical field roster, or the errors that block it."""

    identities: tuple[FieldIdentity, ...]
    errors: tuple[FieldIdentityError, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def by_dg_id(self) -> dict[str, FieldIdentity]:
        return {ident.dg_id: ident for ident in self.identities}

    def by_normalized_name(self) -> dict[str, list[FieldIdentity]]:
        grouped: dict[str, list[FieldIdentity]] = {}
        for ident in self.identities:
            grouped.setdefault(ident.normalized_name, []).append(ident)
        return grouped


def build_field_index(
    rows: Sequence[Mapping[str, object]],
    *,
    name_field: str = "player_name",
    dg_id_field: str = "dg_id",
) -> FieldIndex:
    """Build and validate the canonical field roster.

    Every accepted field player carries a display name, canonical
    normalized name, canonical dg_id, and the original source row. Rows
    with a missing or malformed dg_id, or an empty display name, are
    reported as errors rather than silently dropped or silently accepted.
    Duplicate dg_id and duplicate normalized-name groups are also reported
    as errors -- ``FieldIndex`` never silently overwrites one field player
    with another.
    """
    provisional: list[FieldIdentity] = []
    errors: list[FieldIdentityError] = []

    for row in rows:
        raw_name = row.get(name_field)
        display_name = str(raw_name).strip().strip('"') if raw_name is not None else ""
        raw_dg_id = row.get(dg_id_field)

        if not display_name:
            errors.append(
                FieldIdentityError(
                    code="missing_display_name",
                    message=f"Field row missing {name_field!r}",
                    dg_id=str(raw_dg_id) if raw_dg_id is not None else None,
                )
            )
            continue

        dg_id = try_normalize_dg_id(raw_dg_id)
        if dg_id is None:
            errors.append(
                FieldIdentityError(
                    code="missing_or_malformed_dg_id",
                    message=(
                        f"Field player {display_name!r} has a missing or "
                        f"malformed {dg_id_field}: {raw_dg_id!r}"
                    ),
                    display_name=display_name,
                )
            )
            continue

        provisional.append(
            FieldIdentity(
                display_name=display_name,
                normalized_name=normalize_name(display_name),
                dg_id=dg_id,
                row=row,
            )
        )

    # Duplicate dg_id groups.
    by_id: dict[str, list[FieldIdentity]] = {}
    for ident in provisional:
        by_id.setdefault(ident.dg_id, []).append(ident)
    for dg_id, group in by_id.items():
        if len(group) > 1:
            names = ", ".join(sorted(i.display_name for i in group))
            errors.append(
                FieldIdentityError(
                    code="duplicate_field_dg_id",
                    message=f"dg_id {dg_id!r} occurs {len(group)} times in the field: {names}",
                    dg_id=dg_id,
                )
            )

    # Duplicate normalized-name groups pointing at different dg_ids.
    by_name: dict[str, list[FieldIdentity]] = {}
    for ident in provisional:
        by_name.setdefault(ident.normalized_name, []).append(ident)
    for norm_name, group in by_name.items():
        distinct_ids = {i.dg_id for i in group}
        if len(distinct_ids) > 1:
            errors.append(
                FieldIdentityError(
                    code="ambiguous_field_normalized_name",
                    message=(
                        f"Normalized name {norm_name!r} refers to {len(distinct_ids)} "
                        f"distinct field players: "
                        + ", ".join(sorted(f"{i.display_name} ({i.dg_id})" for i in group))
                    ),
                    display_name=group[0].display_name,
                )
            )

    identities = tuple(provisional) if not errors else tuple()
    return FieldIndex(identities=identities, errors=tuple(errors))


# ── Fuzzy diagnostics (never authorizes a join) ─────────────────────────────

@dataclass(frozen=True)
class FuzzyCandidate:
    source_name: str
    score: float


def _rank_fuzzy_candidates(
    normalized_target: str, source_names: Sequence[str]
) -> tuple[FuzzyCandidate | None, FuzzyCandidate | None]:
    """Return (best, second_best) fuzzy candidates, deterministically ordered.

    Ties are broken by source name so ordering never depends on dict or
    file iteration order.
    """
    scored = [
        FuzzyCandidate(source_name=name, score=difflib.SequenceMatcher(
            None, normalized_target, normalize_name(name)
        ).ratio())
        for name in source_names
    ]
    scored.sort(key=lambda c: (-c.score, c.source_name))
    best = scored[0] if len(scored) >= 1 else None
    second = scored[1] if len(scored) >= 2 else None
    return best, second


# ── Source-family resolution ────────────────────────────────────────────────

@dataclass(frozen=True)
class MatchDiagnostic:
    """One field player's resolution outcome within one source family."""

    field_display_name: str
    field_dg_id: str
    status: str
    method: str | None = None
    source_name: str | None = None
    source_row: Mapping[str, object] | None = None
    best_candidate: FuzzyCandidate | None = None
    second_candidate: FuzzyCandidate | None = None
    detail: str | None = None


@dataclass(frozen=True)
class SourceFamilyResult:
    family: str
    matches: tuple[MatchDiagnostic, ...]
    unresolved: tuple[MatchDiagnostic, ...]
    ambiguous: tuple[MatchDiagnostic, ...]
    unused_source_rows: tuple[str, ...]

    def matches_by_dg_id(self) -> dict[str, MatchDiagnostic]:
        return {m.field_dg_id: m for m in self.matches}


@dataclass(frozen=True)
class _IndexedRow:
    """Internal bookkeeping row: stable ordinal + extracted identity fields."""

    ordinal: int
    source_name: str
    dg_id: str | None
    raw: Mapping[str, object]


def resolve_source_family(
    family: str,
    field_index: FieldIndex,
    source_rows: Sequence[Mapping[str, object]],
    *,
    name_field: str = "player_name",
    dg_id_field: str | None = None,
    crosswalk: Mapping[str, str] | None = None,
    fuzzy_threshold: float = FUZZY_DIAGNOSTIC_THRESHOLD,
    ambiguity_margin: float = FUZZY_AMBIGUITY_MARGIN,
) -> SourceFamilyResult:
    """Resolve every field player against one source family.

    ``field_index`` must already be valid (``field_index.is_valid``); callers
    are responsible for checking that before resolving any source family.

    Every raw source row is given a stable identity -- its ordinal position
    within ``source_rows`` -- and that identity, not its display name, is
    what mapping-integrity is enforced against. This makes duplicate-named
    rows individually distinguishable and guarantees, uniformly across every
    accepted method (``exact_dg_id``, ``crosswalk``, ``exact_normalized_name``,
    ``encoding_normalized_name``), that:

      * one source row is accepted for at most one field player, and
      * one field player is accepted from at most one source row per family.

    A valid unique exact-dg_id match is canonical and authoritative: once a
    row is claimed by exact ID, no lower-precedence method (crosswalk, exact
    name, or encoding fallback) may claim that same row for a different
    field player -- such a proposal is rejected as a blocking conflict
    without disturbing the original exact-ID match. Competing lower-precedence
    proposals for one row from different field players (mixed methods
    included) are never resolved by "first match wins" -- all such proposals
    are rejected as blockers.

    Exact-ID acceptance also does not suppress *other* rows that
    independently target the same, already-owned field identity. After
    every row's global ownership is known -- i.e. after Phases 1-3 have
    finished adjudicating every row's strongest valid claim -- every
    remaining row in the family is checked against each exact-ID-owned
    player's exact normalized name, encoding-normalized name, and
    crosswalk target. A row that has no other legitimate owner is never
    accepted and never reported as merely unused -- it is a
    field-ownership-conflict blocker, and the original exact-ID match is
    retained unchanged for diagnostic truth. This check runs strictly
    *after* global adjudication, not eagerly per-identity during Phase 1:
    a row already validly and uniquely owned by a different field player
    through an accepted claim (exact name, crosswalk, or its own exact ID)
    is never flagged as a conflict for a merely incidental, weaker
    encoding-fallback or name resemblance to another field player -- a
    stronger or equally-authoritative accepted claim always suppresses an
    incidental weaker one, so the same source row is never emitted as both
    an accepted match and a blocking conflict.
    """
    if not field_index.is_valid:
        raise ValueError("Cannot resolve a source family against an invalid field index")

    # ── Index every row by its stable ordinal; never collapse by name. ──────
    indexed_rows: list[_IndexedRow] = []
    for ordinal, row in enumerate(source_rows):
        raw_name = row.get(name_field)
        source_name = str(raw_name).strip().strip('"') if raw_name is not None else ""
        if not source_name:
            continue
        dg_id = try_normalize_dg_id(row.get(dg_id_field)) if dg_id_field else None
        indexed_rows.append(_IndexedRow(ordinal=ordinal, source_name=source_name, dg_id=dg_id, raw=row))

    all_source_names = [r.source_name for r in indexed_rows]

    by_id: dict[str, list[_IndexedRow]] = {}
    by_name: dict[str, list[_IndexedRow]] = {}
    by_fallback: dict[str, list[_IndexedRow]] = {}
    for r in indexed_rows:
        if r.dg_id is not None:
            by_id.setdefault(r.dg_id, []).append(r)
        by_name.setdefault(normalize_name(r.source_name), []).append(r)
        by_fallback.setdefault(normalize_name_encoding_fallback(r.source_name), []).append(r)

    field_by_dg_id = field_index.by_dg_id()

    matches: list[MatchDiagnostic] = []
    unresolved: list[MatchDiagnostic] = []
    ambiguous: list[MatchDiagnostic] = []
    already_decided: set[str] = set()
    id_owner_row: dict[int, str] = {}  # row ordinal -> owning field dg_id (exact-ID only)
    claimed_ordinals: set[int] = set()
    conflict_ordinals: set[int] = set()  # rejected field-ownership-conflict rows
    exact_matched: dict[str, _IndexedRow] = {}  # field dg_id -> its own exact-ID row

    def _dup_detail(label: str, rows: list[_IndexedRow]) -> str:
        parts = ", ".join(sorted(f"#{r.ordinal} {r.source_name!r}" for r in rows))
        return f"{family}: {label}: {parts}"

    # ── Phase 1: exact dg_id (authoritative; row-exclusive by construction). ──
    for ident in field_index.identities:
        if not dg_id_field:
            continue
        id_rows = by_id.get(ident.dg_id, [])
        if len(id_rows) > 1:
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_AMBIGUOUS,
                    detail=_dup_detail(
                        f"duplicate source dg_id {ident.dg_id!r} for {ident.display_name!r}", id_rows
                    ),
                )
            )
            already_decided.add(ident.dg_id)
            continue
        if len(id_rows) == 1:
            id_row = id_rows[0]
            # A different row also exact-name-matching this identity is not a
            # reason to discard the exact-ID acceptance -- exact ID remains
            # authoritative regardless of what a weaker-precedence row says.
            # That extra row is adjudicated in Phase 4, once every row's
            # global ownership is known, as a field-ownership-conflict
            # blocker attached to the extra row itself -- the exact-ID match
            # below is retained unchanged.
            id_owner_row[id_row.ordinal] = ident.dg_id
            claimed_ordinals.add(id_row.ordinal)
            matches.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_MATCHED,
                    method=METHOD_EXACT_DG_ID,
                    source_name=id_row.source_name,
                    source_row=id_row.raw,
                )
            )
            already_decided.add(ident.dg_id)
            exact_matched[ident.dg_id] = id_row

    # ── Phase 2: for identities without an exact-ID match, gather one
    # lower-precedence candidate row each (crosswalk > exact name > encoding
    # fallback), without yet committing it. ──
    pending: dict[int, list[tuple]] = {}  # row ordinal -> [(ident, method, row)]

    for ident in field_index.identities:
        if ident.dg_id in already_decided:
            continue

        candidate: tuple[str, _IndexedRow] | None = None
        crosswalk_entry_present = crosswalk is not None and ident.dg_id in crosswalk

        if crosswalk_entry_present:
            crosswalk_name = crosswalk.get(ident.dg_id)
            if not crosswalk_name or not str(crosswalk_name).strip():
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        detail=f"{family}: crosswalk target for {ident.display_name!r} is malformed or empty",
                    )
                )
                already_decided.add(ident.dg_id)
                continue
            cw_rows = by_name.get(normalize_name(crosswalk_name), [])
            if len(cw_rows) == 0:
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        detail=(
                            f"{family}: crosswalk target {crosswalk_name!r} for "
                            f"{ident.display_name!r} matches no source row"
                        ),
                    )
                )
                already_decided.add(ident.dg_id)
                continue
            if len(cw_rows) > 1:
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        detail=_dup_detail(
                            f"crosswalk target {crosswalk_name!r} ambiguous for {ident.display_name!r}",
                            cw_rows,
                        ),
                    )
                )
                already_decided.add(ident.dg_id)
                continue
            cw_row = cw_rows[0]
            # Many-to-one via mixed methods: crosswalk and independent exact-name
            # evidence disagree about which row this identity is.
            name_rows = by_name.get(ident.normalized_name, [])
            name_row = name_rows[0] if len(name_rows) == 1 else None
            if name_row is not None and name_row.ordinal != cw_row.ordinal:
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_CONFLICT,
                        detail=(
                            f"{family}: crosswalk match (#{cw_row.ordinal} {cw_row.source_name!r}) "
                            f"disagrees with exact name match (#{name_row.ordinal} "
                            f"{name_row.source_name!r}) for {ident.display_name!r}"
                        ),
                    )
                )
                already_decided.add(ident.dg_id)
                continue
            candidate = (METHOD_CROSSWALK, cw_row)
        else:
            name_rows = by_name.get(ident.normalized_name, [])
            if len(name_rows) > 1:
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        detail=_dup_detail(
                            f"normalized name {ident.normalized_name!r} matches "
                            f"{len(name_rows)} rows for {ident.display_name!r}",
                            name_rows,
                        ),
                    )
                )
                already_decided.add(ident.dg_id)
                continue
            if len(name_rows) == 1:
                candidate = (METHOD_EXACT_NAME, name_rows[0])
            else:
                fb_rows = by_fallback.get(normalize_name_encoding_fallback(ident.display_name), [])
                if len(fb_rows) > 1:
                    ambiguous.append(
                        MatchDiagnostic(
                            field_display_name=ident.display_name,
                            field_dg_id=ident.dg_id,
                            status=STATUS_AMBIGUOUS,
                            detail=_dup_detail(
                                f"encoding-fallback match ambiguous for {ident.display_name!r}", fb_rows
                            ),
                        )
                    )
                    already_decided.add(ident.dg_id)
                    continue
                if len(fb_rows) == 1:
                    candidate = (METHOD_ENCODING_FALLBACK, fb_rows[0])

        if candidate is None:
            best, second = _rank_fuzzy_candidates(ident.normalized_name, all_source_names)
            if best is not None and best.score >= fuzzy_threshold:
                if second is not None and (best.score - second.score) < ambiguity_margin:
                    detail = (
                        f"{family}: close competing fuzzy candidates for "
                        f"{ident.display_name!r} ({best.source_name!r}={best.score:.3f} vs "
                        f"{second.source_name!r}={second.score:.3f})"
                    )
                else:
                    detail = (
                        f"{family}: fuzzy-only probable match for {ident.display_name!r} "
                        f"({best.source_name!r}={best.score:.3f}) was not auto-joined"
                    )
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        best_candidate=best,
                        second_candidate=second,
                        detail=detail,
                    )
                )
            else:
                unresolved.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_UNRESOLVED,
                        best_candidate=best,
                        second_candidate=second,
                        detail=f"{family}: no plausible candidate for {ident.display_name!r}",
                    )
                )
            already_decided.add(ident.dg_id)
            continue

        method, row = candidate

        # ── ID authority: this row is already exact-ID-owned by someone else. ──
        if row.ordinal in id_owner_row:
            owner_dg_id = id_owner_row[row.ordinal]
            owner_ident = field_by_dg_id[owner_dg_id]
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_CONFLICT,
                    detail=(
                        f"{family}: {method} for {ident.display_name!r} targets source row "
                        f"#{row.ordinal} ({row.source_name!r}) whose own dg_id {row.dg_id!r} "
                        f"exactly identifies {owner_ident.display_name!r}; exact ID remains "
                        f"canonical for {owner_ident.display_name!r} and this {method} match "
                        f"is rejected"
                    ),
                )
            )
            already_decided.add(ident.dg_id)
            continue

        pending.setdefault(row.ordinal, []).append((ident, method, row))

    # ── Phase 3: adjudicate pending (non-ID) proposals -- one row, one player. ──
    for ordinal, proposals in pending.items():
        if len(proposals) == 1:
            ident, method, row = proposals[0]
            claimed_ordinals.add(row.ordinal)
            matches.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_MATCHED,
                    method=method,
                    source_name=row.source_name,
                    source_row=row.raw,
                )
            )
        else:
            row = proposals[0][2]
            names = ", ".join(
                sorted(f"{ident.display_name!r} via {method}" for ident, method, _ in proposals)
            )
            for ident, method, _ in proposals:
                ambiguous.append(
                    MatchDiagnostic(
                        field_display_name=ident.display_name,
                        field_dg_id=ident.dg_id,
                        status=STATUS_AMBIGUOUS,
                        detail=(
                            f"{family}: source row #{row.ordinal} ({row.source_name!r}) cannot "
                            f"be accepted for multiple field players: {names}"
                        ),
                    )
                )

    # ── Phase 4: field-ownership conflicts, adjudicated only after every
    # row's global ownership is known (Phases 1-3 complete). Exact-ID
    # acceptance does not suppress *other* rows that independently target
    # the same, already-owned field identity via exact normalized name,
    # encoding fallback, or crosswalk -- but a row already claimed by a
    # DIFFERENT field player through a valid, uniquely-adjudicated claim
    # (any accepted method) is never re-flagged as a conflict here: a
    # stronger or equally-authoritative accepted claim always suppresses
    # an incidental weaker claim from a different identity. Running this
    # scan before Phase 2/3 finish would flag rows that go on to be
    # legitimately owned by someone else -- this is exactly what must not
    # happen. ──
    for dg_id, id_row in exact_matched.items():
        ident = field_by_dg_id[dg_id]

        name_rows = by_name.get(ident.normalized_name, [])
        owned_ordinals = {id_row.ordinal}

        extra_name_rows = [
            r for r in name_rows
            if r.ordinal != id_row.ordinal and r.ordinal not in claimed_ordinals
        ]
        owned_ordinals.update(r.ordinal for r in extra_name_rows)

        fb_key = normalize_name_encoding_fallback(ident.display_name)
        extra_fb_rows = [
            r for r in by_fallback.get(fb_key, [])
            if r.ordinal not in owned_ordinals and r.ordinal not in claimed_ordinals
        ]
        owned_ordinals.update(r.ordinal for r in extra_fb_rows)

        extra_crosswalk_row: _IndexedRow | None = None
        if crosswalk is not None and dg_id in crosswalk:
            crosswalk_name = crosswalk.get(dg_id)
            if crosswalk_name and str(crosswalk_name).strip():
                for r in by_name.get(normalize_name(crosswalk_name), []):
                    if r.ordinal not in owned_ordinals and r.ordinal not in claimed_ordinals:
                        extra_crosswalk_row = r
                        owned_ordinals.add(r.ordinal)
                        break

        if len(extra_name_rows) >= 2:
            dup_parts = ", ".join(
                sorted(f"#{r.ordinal} {r.source_name!r}" for r in extra_name_rows)
            )
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_DUPLICATE_NORMALIZED_IDENTITY,
                    detail=(
                        f"{family}: exact-ID-owned field player {ident.display_name!r} "
                        f"(dg_id {ident.dg_id!r}, canonical row #{id_row.ordinal} "
                        f"{id_row.source_name!r}) is also independently targeted by "
                        f"{len(extra_name_rows)} duplicate normalized-name source rows: "
                        f"{dup_parts}"
                    ),
                )
            )
            conflict_ordinals.update(r.ordinal for r in extra_name_rows)
        elif len(extra_name_rows) == 1:
            r = extra_name_rows[0]
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_FIELD_OWNERSHIP_CONFLICT,
                    detail=(
                        f"{family}: exact-ID-owned field player {ident.display_name!r} "
                        f"(dg_id {ident.dg_id!r}, canonical row #{id_row.ordinal} "
                        f"{id_row.source_name!r}) is also independently targeted by "
                        f"source row #{r.ordinal} {r.source_name!r} via {METHOD_EXACT_NAME}"
                    ),
                )
            )
            conflict_ordinals.add(r.ordinal)

        for r in extra_fb_rows:
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_ENCODING_FALLBACK_CONFLICT,
                    detail=(
                        f"{family}: exact-ID-owned field player {ident.display_name!r} "
                        f"(dg_id {ident.dg_id!r}, canonical row #{id_row.ordinal} "
                        f"{id_row.source_name!r}) is also independently targeted by "
                        f"encoding-fallback source row #{r.ordinal} {r.source_name!r} "
                        f"via {METHOD_ENCODING_FALLBACK}"
                    ),
                )
            )
            conflict_ordinals.add(r.ordinal)

        if extra_crosswalk_row is not None:
            r = extra_crosswalk_row
            ambiguous.append(
                MatchDiagnostic(
                    field_display_name=ident.display_name,
                    field_dg_id=ident.dg_id,
                    status=STATUS_FIELD_OWNERSHIP_CONFLICT,
                    detail=(
                        f"{family}: exact-ID-owned field player {ident.display_name!r} "
                        f"(dg_id {ident.dg_id!r}, canonical row #{id_row.ordinal} "
                        f"{id_row.source_name!r}) is also independently targeted by "
                        f"crosswalk-mapped source row #{r.ordinal} {r.source_name!r} "
                        f"via {METHOD_CROSSWALK}"
                    ),
                )
            )
            conflict_ordinals.add(r.ordinal)

    unused = tuple(
        r.source_name for r in indexed_rows
        if r.ordinal not in claimed_ordinals and r.ordinal not in conflict_ordinals
    )

    return SourceFamilyResult(
        family=family,
        matches=tuple(matches),
        unresolved=tuple(unresolved),
        ambiguous=tuple(ambiguous),
        unused_source_rows=unused,
    )


# ── Release diagnostics ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReleaseDiagnostic:
    severity: str
    code: str
    message: str
    family: str | None = None
    field_display_name: str | None = None
    field_dg_id: str | None = None


@dataclass(frozen=True)
class IdentityReleaseReport:
    field_index: FieldIndex
    source_results: tuple[SourceFamilyResult, ...]
    diagnostics: tuple[ReleaseDiagnostic, ...]

    @property
    def blockers(self) -> tuple[ReleaseDiagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == SEVERITY_BLOCKER)

    @property
    def warnings(self) -> tuple[ReleaseDiagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == SEVERITY_WARNING)

    @property
    def is_release_blocked(self) -> bool:
        return len(self.blockers) > 0

    def render(self) -> str:
        """Deterministic, complete plain-text diagnostic summary."""
        lines: list[str] = []
        blockers = self.blockers
        warnings = self.warnings
        lines.append(
            f"Identity release report: {len(blockers)} blocker(s), {len(warnings)} warning(s)"
        )
        for d in blockers:
            lines.append(f"  BLOCKER [{d.code}] {d.family or '-'}: {d.message}")
        for d in warnings:
            lines.append(f"  WARNING [{d.code}] {d.family or '-'}: {d.message}")
        return "\n".join(lines)


def build_release_report(
    field_index: FieldIndex, source_results: Sequence[SourceFamilyResult]
) -> IdentityReleaseReport:
    """Aggregate field-index errors and every source family's diagnostics
    into one deterministic release report. Gathers everything before any
    caller decides whether to fail -- never stops at the first problem.
    """
    diagnostics: list[ReleaseDiagnostic] = []

    for err in field_index.errors:
        diagnostics.append(
            ReleaseDiagnostic(
                severity=SEVERITY_BLOCKER,
                code=err.code,
                message=err.message,
                field_display_name=err.display_name,
                field_dg_id=err.dg_id,
            )
        )

    for result in source_results:
        for diag in result.ambiguous:
            diagnostics.append(
                ReleaseDiagnostic(
                    severity=SEVERITY_BLOCKER,
                    code=f"identity_{diag.status}",
                    message=diag.detail or f"Ambiguous identity in {result.family}",
                    family=result.family,
                    field_display_name=diag.field_display_name,
                    field_dg_id=diag.field_dg_id,
                )
            )
        for diag in result.unresolved:
            diagnostics.append(
                ReleaseDiagnostic(
                    severity=SEVERITY_WARNING,
                    code="missing_source",
                    message=diag.detail or f"No {result.family} row for {diag.field_display_name!r}",
                    family=result.family,
                    field_display_name=diag.field_display_name,
                    field_dg_id=diag.field_dg_id,
                )
            )
        for diag in result.matches:
            if diag.method in (METHOD_EXACT_NAME, METHOD_ENCODING_FALLBACK):
                diagnostics.append(
                    ReleaseDiagnostic(
                        severity=SEVERITY_WARNING,
                        code=f"accepted_{diag.method}",
                        message=(
                            f"{result.family}: {diag.field_display_name!r} accepted via "
                            f"{diag.method} (source name {diag.source_name!r})"
                        ),
                        family=result.family,
                        field_display_name=diag.field_display_name,
                        field_dg_id=diag.field_dg_id,
                    )
                )
        for source_name in result.unused_source_rows:
            diagnostics.append(
                ReleaseDiagnostic(
                    severity=SEVERITY_WARNING,
                    code="unused_source",
                    message=f"{result.family}: source row {source_name!r} matched no field player",
                    family=result.family,
                )
            )

    return IdentityReleaseReport(
        field_index=field_index,
        source_results=tuple(source_results),
        diagnostics=tuple(diagnostics),
    )


# ── Compact player provenance ───────────────────────────────────────────────

PROVENANCE_SCHEMA_VERSION = "1.0"


def build_player_provenance(
    field_identity: FieldIdentity,
    source_results: Sequence[SourceFamilyResult],
) -> dict[str, object]:
    """Build the compact, additive ``identity_provenance`` object for one
    successfully-resolved player. Callers must only invoke this after
    confirming ``IdentityReleaseReport.is_release_blocked`` is ``False`` --
    this function assumes every family entry for this player is either a
    match or a warning-level miss, never a blocker-level ambiguity.
    """
    source_matches: dict[str, dict[str, object]] = {}
    for result in source_results:
        match = result.matches_by_dg_id().get(field_identity.dg_id)
        if match is not None:
            source_matches[result.family] = {
                "status": STATUS_MATCHED,
                "method": match.method,
                "source_name": match.source_name,
            }
        else:
            source_matches[result.family] = {"status": STATUS_MISSING}

    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "canonical_key": "dg_id",
        "field_source": "pga_field.csv",
        "field_method": FIELD_METHOD_EXACT_DG_ID,
        "source_matches": source_matches,
    }
