# Wyndham Retrospective Fixture Authorization — 2026-08-06

## Authorized scope

The operator authorized a governed, event-local development fixture for the
2026 Wyndham Championship at Sedgefield Country Club. The authorization is
limited to source-manifest intake and validation under
`events/2026_wyndham_championship/`.

## Mandatory fence

```text
RETROSPECTIVE_DEVELOPMENT_FIXTURE
NOT OFFICIAL
NOT PRE_EVENT
NOT LIVE
NOT DEPLOYABLE
```

The fixture began after the tournament had already started. It does not create
an official pre-event spine, alter `config/active_event.json`, change the
active-event lifecycle, or admit Wyndham/Sedgefield to production capability.

## Permitted evidence and validation

The fixture may contain the thirteen operator-approved candidate inputs and an
integrity-asserted `input/source_manifest.json`. It validates source contracts,
identity coverage, source-native missingness, and in-memory `UNSCORED`
preparation behavior only. The similar-course input roles are bound to the
operator-supplied Sedgefield top-21 comparison-course set recorded in
`docs/decisions/2026_08_06_sedgefield_similar_course_set_v1.md`.

## Exclusions

This authorization does not permit an official score, rank, tier, probability,
player brief, pre-event artifact, live artifact, board export, deploy payload,
board publication, venue promotion, API access, database write, commit, or
push. It also does not authorize modification of the external candidate files.

Any official Wyndham work requires a separate operator authorization and
lifecycle decision.

## Phase 6.1 addendum — doctrine-validator carve-out

The pre-existing `ACTIVE_EVENT_WYNDHAM_ABSENT` doctrine rule in
`tools/validate_scoring_doctrine.py` blocked on the mere existence of
`events/2026_wyndham_championship/`, with no way to distinguish this
authorized fixture from unauthorized initialization. Phase 6.1 adds a
hardcoded, exact-path exception that recognizes only this fixture when every
fence criterion in the mandatory fence above still holds (README present
with all five markers, `config/active_event.json` still `NO_ACTIVE_EVENT`,
event root limited to the approved development-fixture paths, and
`output/`, `audit/`, and `deploy/data/` empty). Any deviation — including a
renamed or relocated fixture, or a different event root attempting the same
exception — falls back to the original blanket block. See
`docs/data_contracts.md` §"Retrospective Fixture Doctrine-Validation
Carve-Out (Phase 6.1)" for the full rule set.
