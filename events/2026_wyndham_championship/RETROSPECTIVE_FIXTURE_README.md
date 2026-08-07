# 2026 Wyndham Championship Retrospective Fixture

## RETROSPECTIVE_DEVELOPMENT_FIXTURE

## NOT OFFICIAL

## NOT PRE_EVENT

## NOT LIVE

## NOT DEPLOYABLE

Wyndham began before this fixture was initialized. This event-local package is a
development fixture only; it is not an event lifecycle transition and it does
not establish an immutable official pre-event spine.

No output from this fixture may be represented as an official pre-event or live
Wyndham projection. No deploy artifact may be published, copied, or treated as
official. The `output/` and `deploy/data/` directories are intentionally empty
and must remain free of fixture artifacts in this phase.

This fixture validates only:

- source-manifest intake;
- source identity coverage;
- source-native `DEBUT` behavior;
- `UNSCORED` propagation; and
- future static-board behavior.

`config/active_event.json` remains `NO_ACTIVE_EVENT`. Any future official
Wyndham event work requires separate operator authorization and a lifecycle
decision. This fixture does not promote Sedgefield Country Club beyond
`TEST_ONLY_SUPPORTED`.

## Verified Phase 6.2 outcome

Running the unmodified canonical scoring path against this fixture's real
source data, strictly in-memory via a test-only producer seam, produces:

```text
143 SCORED
4 UNSCORED
```

The four UNSCORED players and their mechanisms:

- **David Skinns** — all three all-course NeutralSkill horizons present;
  all three similar-course VenueFit horizons absent.
- **Taylor Moore** — all three similar-course VenueFit horizons present;
  all three all-course NeutralSkill horizons absent.
- **William McGirt** — mixed VenueFit horizons: L6/L12 are source-native
  zero-observation `DEBUT` rows, L24 carries observed finite similar-course
  evidence. The fixed three-horizon VenueFit rule never renormalizes or
  partially blends across horizons, so this mixed state is non-computable.
- **C.T. Pan** — the same mixed L6/L12-`DEBUT`-plus-L24-observed VenueFit
  pattern as William McGirt, for the same non-computable reason.

No UNSCORED player receives an official rank, tier, score, or probability,
and none is included in normalization or probability pools. See
`docs/decisions/2026_08_06_wyndham_retrospective_fixture_authorization.md`
§"Phase 6.2 addendum" for the full record.

## Phase 6.3 board-shell allowance

`deploy/` may additionally contain up to three local, non-deployable
board-shell files as direct children: `index.html`, `app.js`, `styles.css`,
alongside the required empty `deploy/data/` directory. No other file or
subdirectory under `deploy/` is permitted. This allowance does not create a
board shell, does not authorize a deploy payload, official projection, live
artifact, or publication marker, and this fixture remains `NOT DEPLOYABLE`.
A future board shell must render each UNSCORED player above as a non-tier,
incomplete-evidence state. See
`docs/decisions/2026_08_06_wyndham_retrospective_fixture_authorization.md`
§"Phase 6.3 addendum" for the full record.
