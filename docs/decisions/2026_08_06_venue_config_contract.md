# Venue Configuration Contract (Phase 4.3) — 2026-08-06

## Decision

VenueDNA defines a `VenueConfig` schema at `engine/venue_config.py`: a per-venue record of trait weights, anti-pattern thresholds, debut-framework parameters, a variance classification, and narrative thresholds. `engine/enrich_cards.py`'s diagnostic/narrative pathway (historical five-addend trait display, `INACCURATE_BOMBER`/`SHORT_GAME_RELIANT` anti-pattern flags, and strength/weakness-tag and win-case narrative thresholds) is now driven by a resolved `VenueConfig` rather than hardcoded TPC Twin Cities module constants. Two venues are registered: `tpc_twin_cities` (`status: ACTIVE`, values unchanged from the pre-Phase-4.3 hardcoded constants) and `sedgefield_country_club` (`status: RECONSTRUCTED`, provisional, doctrine-derived).

This is a venue-configuration and venue-library phase only. No canonical scoring formula, artifact schema, database, deploy, or active-event change is authorized or implemented by this decision. `engine/venuedna_scoring.py`'s `NeutralSkillRaw`/`VenueFitDeltaRaw`/`VenueHistoryDeltaRaw`/`PostGateRaw` formula (standards/02 §7.2-7.4) is untouched and has no dependency on this module.

## Context

Prior to this phase, `engine/enrich_cards.py` hardcoded TPC Twin Cities' trait weights (`VW_APPROACH` etc.), anti-pattern thresholds (`BOMB_DIST_THRESH` etc.), a debut haircut (`DEBUT_CH_HAIRCUT`), and narrative thresholds (`THRESH_ELITE_APP` etc.) as bare module constants, consumed directly by `historical_gate_diagnostics()`, `apply_gates()`, `combine_raw_score()`, `build_strength_tags()`, `build_weakness_tags()`, `build_win_case()`, and `finalize_canonical_official_records()`'s `trait_scores` construction. `engine/event_context.py`'s `require_supported_context()` capability gate already restricts this producer's live pipeline to one event/venue (`2026_3m_open` / `tpc_twin_cities`); this phase does not relax that gate.

Wyndham Championship initialization requires a venue profile for its host course, Sedgefield Country Club. Authoring that profile surfaced the need for a machine-readable configuration layer distinct from the producer's own code, so a second venue's trait/threshold/narrative behavior can be staged, validated, and reviewed before any future, separately authorized capability-gate activation.

The active-event manifest is `NO_ACTIVE_EVENT`; no event, venue, deploy, or data artifact is in scope for this phase. Wyndham (`events/2026_wyndham_championship/`) is not initialized.

## Authorities reviewed

- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `engine/enrich_cards.py`
- `engine/event_context.py`
- `engine/venuedna_scoring.py`
- `engine/scoring_decomposition.py`
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `library/venues/tpc_twin_cities/`
- `library/venues/detroit_golf_club/detroit_golf_club_intelligence_2026_v1.json`
- `tests/test_enrich_cards.py`, `tests/test_scoring_decomposition.py`, `tests/test_doctrine_contract.py`

## Schema

`engine/venue_config.py` defines:

- `TraitWeights` — `approach`, `long_iron`, `ott`, `ch`, `form`. Each in `[0.0, 1.0]`; sum within `[0.5, 1.01]` (a full or partial-tripod subset of the five historical diagnostic addends).
- `AntiPatternThresholds` — `bomb_dist_thresh`, `bomb_acc_thresh`, `sg_app_thresh`, `sg_sum_thresh` (per-shot/per-round stroke units, within `[-3.0, 3.0]`); `penalty_bomber`, `penalty_sg_dep` (multiplicative penalties within `(0.5, 1.0]`).
- `DebutFramework` — `ch_haircut` (non-positive, within `[-1.0, 0.0]`); `widen_confidence` (bool). Declared for schema completeness; not currently consumed by any score (VenueHistoryDeltaRaw remains 0.0 per standards/02 §7.2/§7.4).
- `variance_class` — one of `LOW`, `MEDIUM`, `MEDIUM_HIGH`, `HIGH`. Informational/reserved: no current code branches on it.
- `NarrativeThresholds` — `elite_app`, `strong_app`, `venue_fit`, `ctrl_power`, `course_ped`, `hot_form`, `app_deficit`, `li_gap`; `elite_app` must exceed `strong_app`.
- `VenueConfig` — combines the above plus `venue_slug`, `venue_name`, and `status` (`ACTIVE` | `RECONSTRUCTED`, diagnostic metadata only).

`load_venue_config(venue_slug)` looks up a small in-module registry (`TPC_TWIN_CITIES`, `SEDGEFIELD_COUNTRY_CLUB`) and raises `VenueConfigError` for any unregistered slug.

## Relationship to the venue profile and the capability gate

A `VenueConfig` and a venue profile (`library/venues/{slug}/{slug}_venue_profile.md`) are two representations of the same doctrine: the profile is the narrative, human-authored mechanism document; the config is its machine-readable trait/threshold projection, hand-derived from the profile in this phase (no automated profile-to-config parser exists or is authorized here).

Registering a `VenueConfig` does **not** make a venue runnable. `engine/event_context.py`'s `require_supported_context()` remains the sole, independent authority on which event/venue combination this producer executes for. `sedgefield_country_club` has a valid, loadable `VenueConfig` and a venue profile, but `SUPPORTED_VENUE_SLUG` in `engine/enrich_cards.py` still names only `tpc_twin_cities` — Sedgefield cannot drive a live producer run until a future, separately authorized phase changes that gate.

## Producer integration

`engine/enrich_cards.py`'s former bare module constants (`VW_APPROACH`, `BOMB_DIST_THRESH`, `DEBUT_CH_HAIRCUT`, `THRESH_ELITE_APP`, etc.) are now derived from `TPC_TWIN_CITIES` (`VW_APPROACH = TPC_TWIN_CITIES.trait_weights.approach`, and so on) rather than being independent literals — their values are numerically unchanged. They remain module-level constants under their historical names because `engine/scoring_decomposition.py` imports them directly by name; this preserves that parity/reporting layer's single-source-of-truth contract without any change to it.

`historical_gate_diagnostics()`, `apply_gates()`, `combine_raw_score()`, `build_strength_tags()`, `build_weakness_tags()`, `build_win_case()`, and `finalize_canonical_official_records()` each gained an additional, optional, trailing `venue_config: VenueConfig = TPC_TWIN_CITIES` parameter. Every existing call site in the test suite that does not pass this parameter is therefore unaffected — verified by running `tests/test_enrich_cards.py` and `tests/test_scoring_decomposition.py` unmodified (all passing).

`main()` resolves `venue_config = load_venue_config(context.venue_slug)` immediately after `require_supported_context()` succeeds, and threads it through the per-player `historical_gate_diagnostics()` call and into `finalize_canonical_official_records()`. Because `require_supported_context()` restricts every CLI-invoked production run to `venue_slug == "tpc_twin_cities"` (a registered venue), this resolves to `TPC_TWIN_CITIES` in production today, proving the wiring works without changing output. `main()`'s internal test-injection seam (the `_context` keyword-only parameter — see its docstring) intentionally bypasses `require_supported_context()` and, in the existing test suite, injects an arbitrary placeholder `venue_slug` (`"synthetic_test_venue"`) unrelated to any registered `VenueConfig`; `main()` falls back to `TPC_TWIN_CITIES` when `load_venue_config()` raises `VenueConfigError`, exactly matching what every caller already used before this phase. This fallback affects no production behavior — the capability gate, not this fallback, is what decides which venue may reach a live run.

This does not change `vts_final`, `neutralSkillIndex`, `rank`, `tier`, `winPct`/`top5Pct`/`top10Pct`/`top20Pct`/`makeCutPct`/`missCutPct`, `penalties_applied`, or `gates_applied` — those derive exclusively from `engine.venuedna_scoring.compute_player_projection().post_gate_raw`, which this phase does not touch. `venue_config` affects only the diagnostic `trait_scores[].weight` display values, the diagnostic `anti_pattern_flags`/`gate_flags`, and the narrative `strength_tags`/`weakness_tags`/`headline`/`win_case`/`scouting_report` fields.

## Sedgefield Country Club venue intelligence

`library/venues/sedgefield_country_club/sedgefield_country_club_venue_profile.md` is authored as `RECONSTRUCTED_V1` — a doctrine-derived, provisional profile based on Sedgefield's well-established public course record (Donald Ross design, small contoured greens, generous fairways, shorter yardage than TPC Twin Cities), following the same "reconstructed, documentation-only, not yet activated" framing already established by `library/venues/detroit_golf_club/detroit_golf_club_intelligence_2026_v1.json`'s dominant-tripod hypothesis. It is not backed by a per-player DataGolf course-history export or any structured VenueDNA evidence source for this venue.

`sedgefield_country_club_CH.csv` contains only the canonical header row (`player_name,rounds_played,historical_true_sg,versus_expected,ch_adjustment,experience_adjustment`) and zero data rows. CLAUDE.md prohibits replacing missing data with reputation, consensus, or fabricated venue history; no approved DataGolf course-history export exists for Sedgefield/Wyndham in this repository, so no per-player row was invented. Weather files (`_full_course_weather_data_2026.json`, `_weather.txt`) were not created for the same reason — the task listed them as optional, and fabricating forecast or historical weather data would violate the same prohibition.

## Known limitation — anti-pattern semantic mismatch at Sedgefield

The venue profile's §11 explicitly flags that TPC Twin Cities' `SHORT_GAME_RELIANT` anti-pattern (a downgrade, because receptive bentgrass greens compress putting's edge) may not transfer to Sedgefield, where small, quick Ross greens plausibly make strong putting/short-game touch a *positive* fit signal instead. `engine/enrich_cards.py`'s gate logic in this phase recognizes only the two historical flag names with the same trigger direction for every venue; `SEDGEFIELD_COUNTRY_CLUB`'s anti-pattern thresholds widen the bar for flagging `SHORT_GAME_RELIANT` (reduced conviction) but do not invert or replace its definition. Resolving this properly — a green-complex-aware anti-pattern taxonomy — is out of scope for this phase and is not activated (the capability gate blocks Sedgefield from any live run regardless).

## Rules adopted

1. A `VenueConfig` is validated at construction (range/type checks on every field); an invalid config raises `VenueConfigError` rather than silently clamping or defaulting.
2. `load_venue_config()` fails closed for any unregistered `venue_slug`.
3. Registering a `VenueConfig` does not admit a venue through `require_supported_context()`; the two mechanisms are independent, and only the capability gate decides producer eligibility.
4. `engine/venue_config.py` has no dependency on and no effect on `engine/venuedna_scoring.py`'s canonical formula, `standards/02`'s missing-data doctrine, or `standards/04`/`standards/VENUEDNA_CODEX_SCHEMA.md`'s artifact schemas.
5. TPC Twin Cities' `VenueConfig` values are numerically identical to the pre-Phase-4.3 hardcoded constants; this is verified by both the unmodified pre-existing test suite and new cross-checking assertions in `tests/test_venue_config.py` and `tests/test_enrich_cards.py`.
6. Sedgefield's `VenueConfig` and venue profile are explicitly marked provisional/reconstructed and must be validated against real Wyndham Championship course-history data before being treated as high-confidence doctrine or before any future capability-gate activation.
7. No fabricated per-player venue-history or weather data was introduced for Sedgefield.

## Not authorized by this decision

- Any change to `config/active_event.json` (remains `NO_ACTIVE_EVENT`).
- Wyndham Championship initialization or any `events/2026_wyndham_championship/` artifact.
- Any change to `engine/venuedna_scoring.py`, `standards/02`, `standards/04`, or `standards/VENUEDNA_CODEX_SCHEMA.md`.
- Relaxing `require_supported_context()` to admit Sedgefield or any venue other than `tpc_twin_cities`.
- Activating `VenueHistoryDeltaRaw` from `debut_framework.ch_haircut` or any other new transform.
- Any deploy, database, or UI change.
