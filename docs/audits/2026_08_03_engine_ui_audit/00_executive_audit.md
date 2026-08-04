# VenueDNA Engine and Static-Board Audit

Date: 2026-08-03. Scope: shared engine, Open v3 archive engine, Rocket/3M/Open archived boards, contracts, validators, tests, and CI. `config/active_event.json` reports `NO_ACTIVE_EVENT`; no event artifact was created or changed.

## Executive conclusion

The repository has strong doctrine and useful local tests, but it is not release-safe as one platform. Three archived boards implement incompatible packaging and payload conventions, and strict deploy validation fails for every inspected archive. The shared `enrich_cards.py` path is closest to the scoring specification; Open v3 is an event-specific independent scoring system that materially departs from it.

## Top five blockers

1. **Blocker — no common strict deploy shape.** Rocket is a harness-only board with no `app.js` or `styles.css`, while the validator requires both (`tools/validate_deploy_contract.py`, strict Rocket result). Smallest resolution: make validator modes explicit (`static-app`, `single-file`, `harness`) with a declared contract; do not weaken strict validation.
2. **Blocker — undeclared dynamic payloads.** 3M `app.js:567,2162` and Open `app.js:1153` use dynamic paths; neither archive contains the optional manifest. Strict validation fails. Open has only `r1_analysis.json` and `r2_analysis.json` despite a general `r{r}` fetch. Smallest resolution: event producer emits `payload_manifest.json` enumerating only generated rounds, then strict validation is required before release.
3. **Critical — Open v3’s official VTS is not the canonical formula.** `score_open_2026_v3.py:470-475` uses `0.40*NSI + 0.30*VFS + 0.15*VHN + 0.15*form`; specification §7 says VTS raw is regressed similar-course SG and §8 z-score scaling. The Open system also feeds DataGolf CFA into VFS (`:408-416`). Doctrine in scoring spec §15 and architecture §1 makes DG benchmark-only. Smallest resolution: isolate Open v3 as a historical experimental pathway until it is reconciled through a formal doctrine/version change.
4. **Critical — identity fallback can silently authorize joins.** `engine/enrich_cards.py:272-293` uses name normalization and fuzzy `SequenceMatcher` at 0.85, returns only the best name, and has no ambiguity margin or unresolved-match log. It joins a `dg_id` only after name selection (`:729`). Smallest resolution: ID-first resolver with match provenance, ambiguity rejection, and unresolved output.
5. **High — missing-data handling changes scores silently.** Shared path supplies zero-valued skill/performance/trend defaults (`enrich_cards.py:677-680`) and excludes zeros from field statistics (`:362-368`). This can turn missing evidence into neutral skill and alter the comparison distribution. Smallest resolution: retain missingness per component; impute only documented field-neutral values and widen source confidence.

## Highest-leverage next task

Implement a versioned **canonical pre-event output builder plus deploy manifest/hash step**. It should make one ID-first player record, one scoring decomposition, one schema version, one manifest of all board payloads, and a strict contract test. This unlocks probability calibration, shared-board work, and reliable audits without changing scoring doctrine in the first increment.

See the companion documents for findings, architecture, and a scoped backlog.
