"""engine/venue_config.py
Venue-specific configuration layer for the pre-event enrichment producer
(engine/enrich_cards.py) — Phase 4.3.

Defines a single ``VenueConfig`` schema (trait weights, anti-pattern
thresholds, debut framework, variance class, narrative thresholds) so the
per-venue diagnostic/narrative behavior in engine/enrich_cards.py is driven
by declared configuration instead of hardcoded TPC Twin Cities module
constants. Every value below is a static Python literal, validated at
import time. Pure, I/O-free, no dependency on and no effect on
engine/venuedna_scoring.py's canonical NeutralSkillRaw / VenueFitDeltaRaw /
VenueHistoryDeltaRaw / PostGateRaw formula (standards/02
§7.2-7.4) — this module governs only the historical/diagnostic five-addend
trait display, the historical INACCURATE_BOMBER / SHORT_GAME_RELIANT
anti-pattern flags, and the narrative strength/weakness-tag thresholds
engine/enrich_cards.py already computes as display and diagnostic output.

Registering a venue here does not make it runnable: engine/enrich_cards.py's
``require_supported_context()`` capability gate (engine/event_context.py)
independently and exclusively decides which event/venue combination this
producer will actually execute for. A venue may have a validated
``VenueConfig`` here while remaining unreachable through that gate.
"""
from __future__ import annotations

from dataclasses import dataclass

VARIANCE_CLASSES = ("LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH")
STATUS_VALUES = ("ACTIVE", "RECONSTRUCTED")


class VenueConfigError(ValueError):
    """Raised when a VenueConfig fails schema validation, or when
    ``load_venue_config()`` is asked for an unregistered venue_slug."""


@dataclass(frozen=True)
class TraitWeights:
    """Combine-weight for each of the five historical diagnostic trait
    addends engine/enrich_cards.py's ``combine_raw_score()`` /
    ``TRAIT_DISPLAY_CFG`` report. Diagnostic/display weighting only — never
    the canonical NeutralSkill/VenueFitDelta/VenueHistoryDelta formula in
    engine/venuedna_scoring.py, and never a formula-v2.0.0 core addend
    (standards/02 §7.4)."""

    approach: float
    long_iron: float
    ott: float
    ch: float
    form: float

    def validate(self, venue_slug: str) -> None:
        fields = (
            ("approach", self.approach), ("long_iron", self.long_iron),
            ("ott", self.ott), ("ch", self.ch), ("form", self.form),
        )
        for name, value in fields:
            _require_numeric(value, f"{venue_slug}: trait_weights.{name}")
            if not (0.0 <= value <= 1.0):
                raise VenueConfigError(
                    f"{venue_slug}: trait_weights.{name} must be within [0.0, 1.0], got {value!r}"
                )
        total = self.approach + self.long_iron + self.ott + self.ch + self.form
        if not (0.5 <= total <= 1.01):
            raise VenueConfigError(
                f"{venue_slug}: trait_weights must sum within [0.5, 1.01] (a full or "
                f"partial-tripod subset of the five diagnostic addends); got {total!r}"
            )


@dataclass(frozen=True)
class AntiPatternThresholds:
    """Historical/diagnostic anti-pattern gate thresholds consumed by
    engine/enrich_cards.py's ``historical_gate_diagnostics()`` /
    ``apply_gates()`` to produce ``anti_pattern_flags`` and the
    INACCURATE_BOMBER / SHORT_GAME_RELIANT diagnostic penalty multipliers.
    Never a canonical formula-v2.0.0 penalty or gate — ``penalty_gate_set_id``
    remains ``venuedna_v2_none`` regardless of this module."""

    bomb_dist_thresh: float
    bomb_acc_thresh: float
    sg_app_thresh: float
    sg_sum_thresh: float
    penalty_bomber: float
    penalty_sg_dep: float

    def validate(self, venue_slug: str) -> None:
        thresholds = (
            ("bomb_dist_thresh", self.bomb_dist_thresh),
            ("bomb_acc_thresh", self.bomb_acc_thresh),
            ("sg_app_thresh", self.sg_app_thresh),
            ("sg_sum_thresh", self.sg_sum_thresh),
        )
        for name, value in thresholds:
            _require_numeric(value, f"{venue_slug}: anti_pattern_thresholds.{name}")
            if not (-3.0 <= value <= 3.0):
                raise VenueConfigError(
                    f"{venue_slug}: anti_pattern_thresholds.{name} must be within "
                    f"[-3.0, 3.0] per-shot/per-round stroke units, got {value!r}"
                )
        penalties = (
            ("penalty_bomber", self.penalty_bomber),
            ("penalty_sg_dep", self.penalty_sg_dep),
        )
        for name, value in penalties:
            _require_numeric(value, f"{venue_slug}: anti_pattern_thresholds.{name}")
            if not (0.5 < value <= 1.0):
                raise VenueConfigError(
                    f"{venue_slug}: anti_pattern_thresholds.{name} must be a "
                    f"multiplicative penalty within (0.5, 1.0], got {value!r}"
                )


@dataclass(frozen=True)
class DebutFramework:
    """Course-debut confidence treatment (venue profile doctrine §12).

    ``ch_haircut`` is declared here for schema completeness and possible
    future VenueHistoryDelta activation. engine/enrich_cards.py does not
    currently apply it to any score: VenueHistoryDeltaRaw remains 0.0 per
    standards/02 §7.2/§7.4 pending a separately approved bounded transform
    (see docs/decisions/2026_08_06_venue_config_contract.md)."""

    ch_haircut: float
    widen_confidence: bool = True

    def validate(self, venue_slug: str) -> None:
        _require_numeric(self.ch_haircut, f"{venue_slug}: debut_framework.ch_haircut")
        if not (-1.0 <= self.ch_haircut <= 0.0):
            raise VenueConfigError(
                f"{venue_slug}: debut_framework.ch_haircut must be a non-positive "
                f"haircut within [-1.0, 0.0], got {self.ch_haircut!r}"
            )
        if not isinstance(self.widen_confidence, bool):
            raise VenueConfigError(
                f"{venue_slug}: debut_framework.widen_confidence must be a bool, "
                f"got {self.widen_confidence!r}"
            )


@dataclass(frozen=True)
class NarrativeThresholds:
    """Thresholds consumed only by engine/enrich_cards.py's narrative layer
    (``build_strength_tags`` / ``build_weakness_tags`` / ``build_win_case``)
    to select strength/weakness tags and win-case mechanism text. Narrative
    display only — never a canonical score, tier, rank, or probability
    input."""

    elite_app: float
    strong_app: float
    venue_fit: float
    ctrl_power: float
    course_ped: float
    hot_form: float
    app_deficit: float
    li_gap: float

    def validate(self, venue_slug: str) -> None:
        fields = (
            ("elite_app", self.elite_app), ("strong_app", self.strong_app),
            ("venue_fit", self.venue_fit), ("ctrl_power", self.ctrl_power),
            ("course_ped", self.course_ped), ("hot_form", self.hot_form),
            ("app_deficit", self.app_deficit), ("li_gap", self.li_gap),
        )
        for name, value in fields:
            _require_numeric(value, f"{venue_slug}: narrative_thresholds.{name}")
        if not (self.elite_app > self.strong_app):
            raise VenueConfigError(
                f"{venue_slug}: narrative_thresholds.elite_app must exceed "
                f"strong_app ({self.elite_app!r} <= {self.strong_app!r})"
            )


@dataclass(frozen=True)
class VenueConfig:
    """Complete per-venue configuration record. ``status`` is diagnostic
    metadata only (never read by scoring logic): ``ACTIVE`` marks a config
    whose values match an already-validated, currently-running producer
    configuration; ``RECONSTRUCTED`` marks a doctrine-derived, provisional
    configuration staged ahead of the venue's own capability-gate
    activation and historical validation (mirrors
    library/venues/detroit_golf_club's RECONSTRUCTED_V1 precedent)."""

    venue_slug: str
    venue_name: str
    trait_weights: TraitWeights
    anti_pattern_thresholds: AntiPatternThresholds
    debut_framework: DebutFramework
    variance_class: str
    narrative_thresholds: NarrativeThresholds
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        if not isinstance(self.venue_slug, str) or not self.venue_slug:
            raise VenueConfigError("venue_slug must be a non-empty string")
        if not isinstance(self.venue_name, str) or not self.venue_name:
            raise VenueConfigError(f"{self.venue_slug}: venue_name must be a non-empty string")
        if self.variance_class not in VARIANCE_CLASSES:
            raise VenueConfigError(
                f"{self.venue_slug}: variance_class must be one of {VARIANCE_CLASSES}, "
                f"got {self.variance_class!r}"
            )
        if self.status not in STATUS_VALUES:
            raise VenueConfigError(
                f"{self.venue_slug}: status must be one of {STATUS_VALUES}, got {self.status!r}"
            )
        self.trait_weights.validate(self.venue_slug)
        self.anti_pattern_thresholds.validate(self.venue_slug)
        self.debut_framework.validate(self.venue_slug)
        self.narrative_thresholds.validate(self.venue_slug)


def _require_numeric(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VenueConfigError(f"{label} must be numeric, got {value!r}")


# ── Canonical venue registry ────────────────────────────────────────────────

TPC_TWIN_CITIES = VenueConfig(
    venue_slug="tpc_twin_cities",
    venue_name="TPC Twin Cities",
    # Values unchanged from the pre-Phase-4.3 hardcoded constants previously
    # inlined directly in engine/enrich_cards.py (venue profile §6, §11, §12).
    trait_weights=TraitWeights(approach=0.40, long_iron=0.25, ott=0.20, ch=0.10, form=0.05),
    anti_pattern_thresholds=AntiPatternThresholds(
        bomb_dist_thresh=0.15, bomb_acc_thresh=-0.05,
        sg_app_thresh=0.20, sg_sum_thresh=1.00,
        penalty_bomber=0.92, penalty_sg_dep=0.90,
    ),
    debut_framework=DebutFramework(ch_haircut=-0.25, widen_confidence=True),
    variance_class="MEDIUM_HIGH",
    narrative_thresholds=NarrativeThresholds(
        elite_app=1.00, strong_app=0.60, venue_fit=0.15, ctrl_power=0.60,
        course_ped=0.04, hot_form=1.50, app_deficit=0.00, li_gap=-0.05,
    ),
    status="ACTIVE",
)

# RECONSTRUCTED_V1 — doctrine-derived from Sedgefield Country Club's public
# course record (Donald Ross design, small contoured greens, generous
# fairways, shorter approach distribution than TPC Twin Cities) per
# library/venues/sedgefield_country_club/sedgefield_country_club_venue_profile.md.
# Not historically validated against per-player Wyndham Championship results
# -- no approved DataGolf course-history export exists for this venue yet
# (see that profile's §19 Source Note and docs/decisions/
# 2026_08_06_venue_config_contract.md). Structurally valid and loadable, but
# engine/event_context.py's require_supported_context() capability gate does
# not admit this venue_slug, so it cannot drive a live producer run in this
# phase.
SEDGEFIELD_COUNTRY_CLUB = VenueConfig(
    venue_slug="sedgefield_country_club",
    venue_name="Sedgefield Country Club",
    trait_weights=TraitWeights(approach=0.42, long_iron=0.18, ott=0.20, ch=0.12, form=0.08),
    anti_pattern_thresholds=AntiPatternThresholds(
        bomb_dist_thresh=0.12, bomb_acc_thresh=-0.03,
        sg_app_thresh=0.10, sg_sum_thresh=1.30,
        penalty_bomber=0.93, penalty_sg_dep=0.95,
    ),
    debut_framework=DebutFramework(ch_haircut=-0.20, widen_confidence=True),
    variance_class="MEDIUM_HIGH",
    narrative_thresholds=NarrativeThresholds(
        elite_app=1.00, strong_app=0.55, venue_fit=0.15, ctrl_power=0.45,
        course_ped=0.05, hot_form=1.40, app_deficit=0.00, li_gap=-0.08,
    ),
    status="RECONSTRUCTED",
)

_REGISTRY: dict[str, VenueConfig] = {
    TPC_TWIN_CITIES.venue_slug: TPC_TWIN_CITIES,
    SEDGEFIELD_COUNTRY_CLUB.venue_slug: SEDGEFIELD_COUNTRY_CLUB,
}


def load_venue_config(venue_slug: str) -> VenueConfig:
    """Look up a validated ``VenueConfig`` by ``venue_slug``.

    Raises ``VenueConfigError`` for any venue_slug not in the registry --
    fail-closed, rather than silently returning a default configuration.
    This registry membership check is independent of, and narrower than,
    engine/event_context.py's require_supported_context() capability gate:
    a venue can be registered here (loadable, structurally valid) without
    that gate admitting it into a live producer run.
    """
    config = _REGISTRY.get(venue_slug)
    if config is None:
        raise VenueConfigError(
            f"No VenueConfig registered for venue_slug={venue_slug!r}. "
            f"Known venues: {sorted(_REGISTRY)}."
        )
    return config
