# Capability Policy + Two-Venue Regression Harness (Phase 4.4) — 2026-08-06

## Decision

VenueDNA replaces the single-pair capability gate concept in `engine/event_context.py` with an explicit, three-state capability policy: `PRODUCTION_SUPPORTED`, `TEST_ONLY_SUPPORTED`, `UNSUPPORTED`. Two explicit `(event_slug, venue_slug)` pairs are registered: `(2026_3m_open, tpc_twin_cities)` as `PRODUCTION_SUPPORTED`, and `(2026_wyndham_championship, sedgefield_country_club)` as `TEST_ONLY_SUPPORTED`. `engine/enrich_cards.py`'s `main()` now calls `require_production_capability()` on its real, non-test-seam production/CLI path, replacing its prior `require_supported_context(context, supported_event_slug=SUPPORTED_EVENT_SLUG, supported_venue_slug=SUPPORTED_VENUE_SLUG)` call site. A two-venue regression harness (`tests/test_event_context.py`, `tests/test_enrich_cards.py`) proves TPC production parity, Sedgefield test-only admission, and fail-closed behavior for every other pair — without creating any real event, writing any real artifact, or authorizing Sedgefield/Wyndham for production.

This is an engine/test phase only. No canonical scoring formula, artifact schema, database, deploy, or active-event change is authorized or implemented by this decision. `config/active_event.json` remains `NO_ACTIVE_EVENT`, unchanged.

## Context

Phase 4.3 (`docs/decisions/2026_08_06_venue_config_contract.md`) registered a second venue's `VenueConfig` (`sedgefield_country_club`) while leaving `engine/event_context.py`'s `require_supported_context()` capability gate as a single hardcoded pair (`SUPPORTED_EVENT_SLUG`/`SUPPORTED_VENUE_SLUG` in `engine/enrich_cards.py`, both still `"2026_3m_open"`/`"tpc_twin_cities"`). That gate had exactly two outcomes: the one supported pair, or rejection — with no way to distinguish "this pair is deliberately staged for deterministic testing" from "this pair is simply unknown." This phase adds that middle state so a second venue can be regression-tested end-to-end (proving its own `VenueConfig` actually drives the pipeline, proving it cannot reach the CLI, proving no side effects occur) without any of that testing implying — or silently drifting toward — production readiness.

## Authorities reviewed

- `AGENTS.md`, `CLAUDE.md`, `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `engine/event_context.py`, `engine/venue_config.py`, `engine/enrich_cards.py`, `engine/source_manifest_resolver.py` (inspected, not modified)
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`, `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`, `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`, `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`, `docs/decisions/2026_08_05_source_manifest_contract.md`, `docs/decisions/2026_08_06_venue_config_contract.md`
- `tests/test_event_context.py`, `tests/test_enrich_cards.py`, `tests/test_venue_config.py`
- `library/venues/tpc_twin_cities/`, `library/venues/sedgefield_country_club/`

No conflict was found between this task and any of the above; no standards file required modification.

## Capability policy design

`engine/event_context.py` adds, alongside the pre-existing `require_supported_context()` (retained, unmodified, still independently tested — no longer this producer's call site):

- `CapabilityPolicyEntry(event_slug, venue_slug, status)` — one explicit pair record.
- `_CAPABILITY_POLICY` — a two-entry tuple. Not a wildcard rule: an unlisted pair, including a listed venue paired with the wrong event or a listed event paired with the wrong venue, is not looked up at all.
- `CapabilityDecision(status, event_slug, venue_slug, reason)` — the testable return value of a lookup.
- `resolve_capability(event_slug, venue_slug) -> CapabilityDecision` — pure; matches the pair against `_CAPABILITY_POLICY`, then confirms the named venue has a valid, registered `engine/venue_config.VenueConfig` via `load_venue_config()`. Both conditions must hold: a matching policy entry is not by itself sufficient (a venue's `VenueConfig` must actually exist and be valid), and a registered `VenueConfig` is not by itself sufficient (the pair must have an explicit policy entry). Any failure resolves `UNSUPPORTED` with a stated reason — never a partial match, never an inferred default.
- `require_production_capability(context: EventContext) -> CapabilityDecision` — raises `EventContextError` unless `resolve_capability()` returns `PRODUCTION_SUPPORTED`. This is the function `engine/enrich_cards.py main()`'s real CLI path calls, immediately after `load_pre_event_context()` succeeds and strictly before any event-bound input read, directory creation, or write — the same placement `require_supported_context()` occupied before this phase.

`engine/venue_config.py` is unchanged: Sedgefield's `VenueConfig` was already registered and structurally valid in Phase 4.3; this phase only changes how the *capability* question is answered, not the venue-configuration schema itself.

## Why Sedgefield is not production-supported

No approved Wyndham Championship event inputs or `source_manifest.json` exist; `sedgefield_country_club_CH.csv` is header-only (no per-player venue-history evidence); the `SHORT_GAME_RELIANT` anti-pattern's semantic mismatch at Sedgefield (documented in the Phase 4.3 decision) is unresolved. None of this changed in this phase. `TEST_ONLY_SUPPORTED` exists precisely so this staged, provisional configuration can be exercised deterministically — proving the plumbing works — without that exercise being mistaken for, or silently escalating into, a production-readiness claim.

## Preserving real CLI production behavior

`engine/enrich_cards.py main()`'s two entry paths are unchanged in shape:

- **Real CLI path** (no `_context`): `argparse.ArgumentParser().parse_args()` still accepts zero arguments; `config/active_event.json` is still the sole event-context source; `require_production_capability(context)` replaces the prior `require_supported_context(...)` call at the identical point in the control flow. A `TEST_ONLY_SUPPORTED` or `UNSUPPORTED` pair raises `EventContextError` here exactly as an unsupported pair always has — before the source-manifest is read, before any directory is created, before any write.
- **Internal test-injection seam** (`_context`/`_live_mode`, keyword-only, not argparse-visible): unchanged. This seam intentionally bypasses `require_production_capability()` — it always has, since Phase 4.2 introduced it — so isolated tests can inject an already-constructed `EventContext` without a real manifest file. This phase adds no new CLI flag, environment variable, or argparse surface; the test-only pathway remains reachable only through this pre-existing, already-documented internal parameter.

**Phase 4.3 fallback disposition.** `main()`'s `except VenueConfigError: venue_config = TPC_TWIN_CITIES` fallback (triggered only when `_context` injects a venue_slug absent from `engine/venue_config.py`'s registry, e.g. the placeholder `"synthetic_test_venue"` most of `tests/test_enrich_cards.py` already uses) is **retained, not replaced** — narrowly proven, not modified, to satisfy this phase's own requirement. It governs only which `VenueConfig` supplies *diagnostic/narrative* values (`trait_scores` weights, anti-pattern thresholds, strength/weakness-tag text) for a test-seam-produced payload under `tmp_path`; `resolve_capability()`/`require_production_capability()` run only in the real-CLI branch, are computed independently of this fallback, and are never consulted or re-invoked here. `test_placeholder_synthetic_venue_pair_never_resolves_production_supported` (`tests/test_enrich_cards.py`) proves the placeholder pair this fallback most commonly serves is `UNSUPPORTED` regardless of the fallback's behavior. A venue that *is* validly registered but not production-supported (Sedgefield) never reaches this fallback at all — `load_venue_config("sedgefield_country_club")` succeeds directly — which `test_sedgefield_test_only_context_drives_sedgefield_trait_weights_not_tpc` proves end-to-end by asserting the produced payload's approach-trait weight matches `SEDGEFIELD_COUNTRY_CLUB`, not `TPC_TWIN_CITIES`.

## Two-venue regression proof

All in `tests/test_event_context.py` and `tests/test_enrich_cards.py`; none create a real event, write into `events/`, or modify `config/active_event.json`.

- **TPC production parity:** `test_resolve_capability_tpc_is_production_supported`, `test_require_production_capability_accepts_tpc_context` (pure-function level); `test_cli_production_path_admits_tpc_capability_supported_pair` (full CLI-path run, via monkeypatched `_ROOT` + synthetic `config/active_event.json` under `tmp_path` — never the real repository manifest). The full pre-existing suite (identity resolution, golden-score parity, canonical-v2 isolation, etc.) is unmodified and passes unchanged, proving zero output-shape or scoring drift.
- **Sedgefield config-selection:** `test_sedgefield_test_only_context_drives_sedgefield_trait_weights_not_tpc` runs the full pipeline through the internal `_context` seam only, and asserts the payload's trait weights match Sedgefield's own `VenueConfig`, not TPC's.
- **No-side-effect evidence:** `test_sedgefield_test_only_context_without_sources_creates_no_artifacts` (test-seam Sedgefield context, no source files → `SystemExit`, no `output/`/`deploy/` created) and `test_cli_production_path_rejects_sedgefield_test_only_pair` (real CLI path, real Sedgefield source files present on disk, still rejected before any read — proving rejection happens at the capability gate, not merely because sources happen to be absent).
- **Fail-closed evidence:** `test_resolve_capability_unknown_pair_is_unsupported`, `test_resolve_capability_known_event_wrong_venue_is_unsupported`, `test_resolve_capability_known_venue_wrong_event_is_unsupported`, `test_resolve_capability_registered_pair_with_missing_venue_config_fails_closed`, `test_require_production_capability_rejects_sedgefield_test_only_context`, `test_require_production_capability_rejects_unsupported_context`, `test_cli_production_path_rejects_unknown_pair`.

## Explicitly not authorized by this decision

- Any change to `config/active_event.json` (remains `NO_ACTIVE_EVENT`).
- Wyndham Championship initialization or any `events/2026_wyndham_championship/` artifact — the `2026_wyndham_championship` string used as a capability-policy lookup key is not an event-initialization action.
- Any change to `engine/venuedna_scoring.py`, `engine/scoring_decomposition.py`, `engine/identity_resolver.py`, `engine/source_manifest_resolver.py`, `engine/build_event_package.py`, `standards/02`, `standards/04`, or `standards/VENUEDNA_CODEX_SCHEMA.md`.
- Making Sedgefield/Wyndham `PRODUCTION_SUPPORTED`.
- Any change to TPC Twin Cities' scoring output or its existing production admission.
- Any deploy, database, or UI change.
- Authoring a real `source_manifest.json`, acquiring DataGolf API access, or fabricating Sedgefield venue-history/weather evidence.

## Promotion criteria — the immediate gating dependency

Before any future phase may propose moving `(2026_wyndham_championship, sedgefield_country_club)` from `TEST_ONLY_SUPPORTED` to `PRODUCTION_SUPPORTED`, the single, immediate, currently-missing dependency is: an approved, real Wyndham Championship source dataset (at minimum a populated `sedgefield_country_club_CH.csv` course-history export and a real `source_manifest.json` under an initialized `events/2026_wyndham_championship/input/`), obtained and reviewed through the normal event-initialization and Model Council process — not fabricated, not inferred from doctrine alone. This decision does not further scope that future phase.
