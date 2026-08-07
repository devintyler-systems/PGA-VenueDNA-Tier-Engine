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

## Phase 6.2 addendum — verified UNSCORED outcome

Phase 6.2 executed the unmodified canonical scoring path against this
fixture's real source data, strictly in-memory via a test-only producer
seam, and confirmed the verified fully-sourced final-field outcome:

```text
143 SCORED
4 UNSCORED
```

The four UNSCORED players fall into two distinct, doctrine-consistent
mechanisms — neither is a data-quality defect in the fixture:

- **David Skinns** — present in the field and has all three all-course
  NeutralSkill horizons, but is absent from all three similar-course
  VenueFit horizons.
- **Taylor Moore** — present in the field and has all three similar-course
  VenueFit horizons, but is absent from all three all-course NeutralSkill
  horizons.
- **William McGirt** — present in the similar-course rows, but the three
  required VenueFit horizons are mixed: L6 and L12 are source-native
  zero-observation `DEBUT` rows, while L24 carries observed finite
  similar-course evidence. The fixed three-horizon VenueFit rule
  (`standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §7.5) never renormalizes and
  never partially blends across horizons, so this mixed state is
  non-computable.
- **C.T. Pan** — the same mixed L6/L12-`DEBUT`-plus-L24-observed VenueFit
  pattern as William McGirt, for the same non-computable reason.

No UNSCORED player receives an official rank, tier, score, or probability.
No UNSCORED player is included in normalization or probability pools. This
addendum documents a verified fixture outcome only; it does not authorize
an official projection or a deploy payload, and it does not change
`engine/venuedna_scoring.py` or any canonical standard.

## Phase 6.3 addendum — fenced board-shell allowance

Phase 6.3 permits exactly one additional, local, non-deployable asset class
under this fixture: a retrospective board shell at
`events/2026_wyndham_championship/deploy/`. The doctrine validator now
recognizes `index.html`, `app.js`, and `styles.css` as approved direct
children of `deploy/`, alongside the pre-existing required empty `data/`
directory. No other direct child or subdirectory of `deploy/` is permitted,
`deploy/data/` must remain recursively empty, and this allowance is scoped
to the exact hardcoded Wyndham fixture path — it does not extend to any
other event root. See `docs/data_contracts.md` §"Retrospective Fixture
Doctrine-Validation Carve-Out (Phase 6.1)" for the updated rule set.

This addendum does not create a board shell. It does not authorize a deploy
payload, official projection, live artifact, or publication marker. The
fixture remains `NOT DEPLOYABLE` regardless of the board-shell allowance. A
future board shell, once created under a separate authorization, must
render the four UNSCORED players documented above as a non-tier,
incomplete-evidence state rather than omitting them or assigning them a
fabricated tier.
