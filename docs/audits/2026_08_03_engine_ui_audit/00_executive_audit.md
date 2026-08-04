# VenueDNA Engine and Static-Board Audit

Date: 2026-08-03. Scope: shared engine, Open v3 archive engine, Rocket/3M/Open archived boards, contracts, validators, tests, and CI. `config/active_event.json` reports `NO_ACTIVE_EVENT`; no event artifact was created or changed.

## Executive conclusion

The repository has strong doctrine and useful local tests, but it is not release-safe as one platform. Three archived boards implement incompatible packaging and payload conventions, and strict deploy validation fails for every inspected archive. The root-level `enrich_cards.py` path is an event-hardcoded 3M Open enrichment pathway, not a reusable shared canonical engine; Open v3 is a separate event-specific scoring system that materially departs from doctrine.

## Top five blockers

1. **Blocker — no common strict deploy shape.** Rocket is a harness-only board with no `app.js` or `styles.css`, while the validator requires both (`tools/validate_deploy_contract.py`, strict Rocket result). Smallest resolution: make validator modes explicit (`static-app`, `single-file`, `harness`) with a declared contract; do not weaken strict validation.
2. **Blocker — undeclared dynamic payloads.** 3M `app.js:567,2162` has both a finite `ROUND_PAYLOADS` map loaded through `fetch(url)` and a generic `data/r${r}_analysis.json` fetch. Open `app.js:1153` has a generic dynamic round fetch, exposes R1–R4 controls, and the inspected archive contains only the generated round files documented in this audit. Neither archive contains a release manifest. Dynamic targets must be declared as `required` or `optional_pending`: required files must exist, parse, and hash-match; optional-pending targets must declare the complete reachable path set, may be absent only when the board intentionally exposes pending/unavailable state, and must parse/hash-match when present. Strict validation must report missing optional targets separately and must never infer optional status from absence.
3. **Critical — Open v3’s official VTS is not the canonical formula.** `score_open_2026_v3.py:470-475` uses `0.40*NSI + 0.30*VFS + 0.15*VHN + 0.15*form`; specification §7 says VTS raw is regressed similar-course SG and §8 z-score scaling. The Open system also feeds DataGolf CFA into VFS (`:408-416`). Doctrine in scoring spec §15 and architecture §1 makes DG benchmark-only. Smallest resolution: isolate Open v3 as a historical experimental pathway until it is reconciled through a formal doctrine/version change.
4. **Critical — identity fallback can silently authorize joins.** `engine/enrich_cards.py:272-293` uses name normalization and fuzzy `SequenceMatcher` at 0.85, returns only the best name, and has no ambiguity margin or unresolved-match log. It joins a `dg_id` only after name selection (`:729`). Smallest resolution: ID-first resolver with match provenance, ambiguity rejection, and unresolved output.
5. **High — missing-data handling changes scores silently.** Shared path supplies zero-valued skill/performance/trend defaults (`enrich_cards.py:677-680`) and excludes zeros from field statistics (`:362-368`). This can turn missing evidence into neutral skill and alter the comparison distribution. Smallest resolution: retain missingness per component; impute only documented field-neutral values and widen source confidence.

## Highest-leverage next task

Implement a **strict deploy release contract and integrity validation** first: a declared board mode, payload availability (`required` versus `optional_pending`), parse checks, and hashes. Preserve archives by placing historical profiles at `config/deploy_contracts/archived/`, one per inspected archive; profiles may reference and hash existing archive files but may not rewrite or synchronize them. Future event producers should emit a release manifest before archival, and adding a file inside an archived event requires separate explicit operator authorization.

The required implementation sequence is: (1) strict deploy release contract and integrity validation; (2) ID-first identity resolver and provenance; (3) formal scoring-doctrine reconciliation and decomposition parity; (4) canonical pre-event output builder; (5) shared static-board platform; and (6) probability calibration and broader CI quality gates as dependencies allow. Do not implement a canonical output builder before the VTS doctrine conflict is resolved.

See the companion documents for findings, architecture, and a scoped backlog.
