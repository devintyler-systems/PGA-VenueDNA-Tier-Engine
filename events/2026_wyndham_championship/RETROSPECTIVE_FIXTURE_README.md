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

## Phase 6.5 Board-Shell Validation Certification

The fixture remains `RETROSPECTIVE_DEVELOPMENT_FIXTURE`, `NOT OFFICIAL`,
`NOT PRE_EVENT`, `NOT LIVE`, `NOT DEPLOYABLE`, `NOT PUBLISHED`. Sedgefield
Country Club remains `TEST_ONLY_SUPPORTED`. `config/active_event.json`
remained `NO_ACTIVE_EVENT` throughout this work.

**Phase 6.4 certified shell baseline** — commit
`feb2921265a562e0b8761bc43de857cc79f4808c` ("feat: add retrospective Wyndham
board-shell fixture (Phase 6.4)") built the retrospective static board shell
described above. Static-file inspection and fixture/doctrine validation
preceded rendered-browser validation.

**Phase 6.5 rendered validation** — actual rendered browser validation, not
static inspection alone, was performed at 375px, 768px, 1024px, and 1440px,
covering: horizontal-overflow absence; banner visibility and responsive
readability; table/control reachability, including intentional narrow-screen
internal table scrolling; keyboard-visible focus; `prefers-reduced-motion`
behavior; UNSCORED rendering, dedicated filtering, Tier 1–5 exclusion, and
last-place sorting; and dark/light color-scheme rendered contrast. The
initial rendered validation identified WCAG contrast defects in the fixture
warning banner and in the UNSCORED/mechanism-chip treatment. No source
changes were made in Phase 6.5 itself; remediation was deferred to a
separately authorized phase.

**Phase 6.5.1 remediation and independent review** — remediation was scoped
to `deploy/styles.css` only; `index.html`, `app.js`, deploy payloads, fixture
inputs, outputs, audit paths, scoring, identity, standards, databases, source
manifests, and active-event configuration were not touched. Re-validation
confirmed passing rendered contrast in both dark and light schemes for the
repaired banner, UNSCORED/mechanism-chip treatment, synthetic badge
treatment, and focus-visible indicators, alongside revalidated responsive,
keyboard, reduced-motion, and UNSCORED behavior. Targeted tests —
`python -m pytest tests/test_wyndham_retrospective_board_shell.py
tests/test_wyndham_retrospective_fixture_smoke.py
tests/test_retro_fixture_board_shell_doctrine.py -q` — result: `88 passed`.
Doctrine validation — `python tools/validate_scoring_doctrine.py --strict` —
result: `SCORING DOCTRINE PASSED (1 warnings)`, where the warning denotes the
recognized fenced retrospective fixture. Independent review by Gemini 3.1
Pro High returned `APPROVE FOR COMMIT`.

**Certified remediation commit** — commit
`b6e4aed6a6b512b3cf657dc020ef71cdfe20320c` ("fix: remediate retrospective
Wyndham shell contrast") touched exactly one file,
`events/2026_wyndham_championship/deploy/styles.css` (9 insertions, 3
deletions), and was pushed to `origin/main` only after independent approval.

**Carve-out clarification** — the pre-existing, untracked `design-system/`
guidance files were formally excluded from Phase 6.5 scope, remained
unchanged and uncommitted, and were not part of either the Phase 6.4 or
Phase 6.5.1 commit.

**Certification** — The retrospective Wyndham board-shell fixture's
responsive and accessibility baseline is certified for subsequent explicitly
authorized retrospective fixture development only. This certification does
not authorize projection generation, active-event activation, live analysis,
deployment, publication, or use as an official Wyndham board.
