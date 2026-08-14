# Pre-Event Operational Readiness Audit

**Date:** 2026-08-13
**Mode:** Event-neutral, read-only readiness audit
**Overall classification:** **BLOCKED**
**Confidence:** High. The current gates and code paths are directly evidenced; no future event-specific facts were inferred.

## 1. Executive readiness decision

**Fact.** Repository state is clean, synchronized on `main`, and the active-event manifest is `NO_ACTIVE_EVENT`. The generic no-active-event preflight is code-inspected read-only and passed.

**Fact.** The binding Weekly Event Setup Protocol requires updating `config/active_event.json` to `status: INITIALIZED` (`PERPLEXITY_OPERATING_PROTOCOL.md:44-88`). `AGENTS.md` permits only `NO_ACTIVE_EVENT`, `PRE_EVENT`, round states, `FINAL_AUDIT`, and `ARCHIVED` (`AGENTS.md:440-471`), while `tools/preflight_event.py` likewise rejects any status outside its enumerated set (`tools/preflight_event.py:20-35,90-125`). `INITIALIZED` is not accepted by either.

**Inference.** A later weekly setup cannot complete a safe manifest lifecycle transition as written: the protocol's required state is rejected by the repository's higher-precedence governance and preflight implementation.

**Recommendation.** Do not initialize an event. First obtain an explicit, committed governance resolution that selects a supported transition (or authorizes a coordinated protocol/tool/governance update). Under `AGENTS.md` precedence, the current permitted lifecycle governs until that resolution exists. Afterward, a separately authorized weekly setup must supply the operator inputs and capability admission detailed below.

## 2. Gate results

All mandatory audit gates ran before substantive inspection.

| Gate / command | Classification | Result |
| --- | --- | --- |
| `git status --short` | READY | Empty before report creation. |
| `git branch --show-current` | READY | `main`. |
| `git fetch origin` | READY | Completed; this is required synchronization activity and updates Git remote-tracking metadata only, not repository worktree content. |
| `git rev-parse HEAD` / `git rev-parse origin/main` | READY | Both returned `6a46dcfc65635706193b9d5fb0554f799d8903b1`. |
| `git status -sb` | READY | `## main...origin/main`. |
| `Get-Content config/active_event.json` | READY | `status: NO_ACTIVE_EVENT`; all event/venue/deploy bindings are null (`config/active_event.json:1-35`). |
| `python tools/preflight_event.py` | READY | Passed: `Status: NO_ACTIVE_EVENT`, `PREFLIGHT PASSED`. Static inspection confirms this script only reads manifest/filesystem state and prints findings (`tools/preflight_event.py:1-260`). |

## 3. Authority and current-state evidence map

| Authority / evidence | Classification | Finding |
| --- | --- | --- |
| Task, `AGENTS.md`, `CLAUDE.md`, `SYSTEM_HANDOFF_SPEC.md` | READY | Task scope plus repository governance control. `AGENTS.md` orders canonical standards above implementation and historical artifacts; `SYSTEM_HANDOFF_SPEC.md` requires a committed synchronized handoff and protected payload compatibility (`AGENTS.md:15-28`; `CLAUDE.md:15-31`; `SYSTEM_HANDOFF_SPEC.md:92-123`). |
| `PERPLEXITY_OPERATING_PROTOCOL.md` Weekly Event Setup | BLOCKED | It is the required setup workflow but specifies unsupported `INITIALIZED` state. This conflicts with higher-precedence `AGENTS.md` lifecycle rules and the preflight enumerated status set (`PERPLEXITY_OPERATING_PROTOCOL.md:44-88`; `AGENTS.md:440-471`; `tools/preflight_event.py:20-35`). |
| Canonical architecture and scoring doctrine | READY WITH OPERATOR INPUT | Inputs, output/deploy separation, dependency order, separated score layers, and missing-data treatment are defined; event-specific evidence is absent by design (`standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md:60-180`; `standards/02_PGA_VENUEDNA_SCORING_SPEC.md:1-100,200-270`). |
| Learning, artifact, and Council authority | NOT APPLICABLE WHILE NO_ACTIVE_EVENT | These controls govern live/final/audit and pre-event Council execution after an event is authorized (`standards/03_PGA_VENUEDNA_LEARNING_LOOP.md:1-155`; `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:262-421`; `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md:1-210`). |
| Current committed handoffs/reports | READY | The current binding audit handoff and the committed typed-artifact decision report exist. The latter preserves documentation-only typed posture, independent families, and no-adapter result (`scripts/handoffs/2026-08-13_pre_event_operational_readiness_audit.md`; `scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md`). |
| README and library schema | UNVERIFIED as operational authority | README describes legacy/historical workflows and points to library documentation; canonical standards and active manifest govern current readiness instead (`README.md:1-120,232-252`; `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:262-298`). |

## 4. Readiness matrix

| Area | Classification | Fact, inference, and required condition |
| --- | --- | --- |
| Branch, synchronization, clean worktree, active-event gates | READY | All gates in §2 passed. |
| Weekly Event Setup Protocol | BLOCKED | Its required `INITIALIZED` status is invalid under `AGENTS.md` and `tools/preflight_event.py`. **Required operator action:** explicitly reconcile the lifecycle authority in a committed follow-on governance task before any event initialization. |
| Exact operator authorization point | READY WITH OPERATOR INPUT | The protocol fires only after an operator supplies the next event and venue; Perplexity then owns committed setup artifacts and handoff publication (`PERPLEXITY_OPERATING_PROTOCOL.md:44-105`). **Required operator input:** event identity, venue identity, event window, and explicit authorization to create the folder/manifest and change active-event state, after the lifecycle conflict is resolved. |
| Event context and safe paths | READY WITH OPERATOR INPUT | `load_pre_event_context()` fails closed before event-bound I/O unless manifest schema, `PRE_EVENT` state, names/slugs, year, event root, profile, deploy, and audit paths are complete and safely contained (`engine/event_context.py:1-230`). **Required input:** all those event-specific bindings; none may be inferred from history. |
| Production capability admission | BLOCKED pending operator-selected pair | The production CLI requires explicit `PRODUCTION_SUPPORTED` capability admission before event input read, directory creation, or write; a registered venue alone is insufficient (`docs/data_contracts.md:387-407`; `engine/event_context.py:395-418`; `engine/enrich_cards.py:1233-1312`). **Required condition:** the operator-selected event/venue pair must already be production-admitted, or a separately authorized capability/venue-configuration task must complete first. This audit does not name or select a pair. |
| Venue intelligence | READY WITH OPERATOR INPUT | Weekly setup requires checking the selected venue’s durable intelligence for version, traits, mechanisms, anti-patterns, and debut framework; missing intelligence is a stop condition (`PERPLEXITY_OPERATING_PROTOCOL.md:52-58`). **Required input:** operator-selected venue and verified canonical library profile; no venue was inspected or inferred. |
| Field roster / identity anchor | READY WITH OPERATOR INPUT | `field` is the sole `block_release` source role and must resolve before identity or artifact writes (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:713-780`; `engine/source_manifest_resolver.py:25-85,614-760`). **Required input:** current field file with canonical DataGolf IDs where available. |
| Core SG and venue-fit sources | READY WITH OPERATOR INPUT | The manifest requires three neutral-skill and three similar-course horizons. Neutral skill may be composite-renormalized only under the scoring doctrine; incomplete venue fit is non-computable and never zero-filled (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:760-820`; `standards/02_PGA_VENUEDNA_SCORING_SPEC.md:20-100`). **Required input:** genuine, declared physical sources for the six roles and common similar-course provenance. |
| Venue history, traits, performance, benchmark, recent-form sources | READY WITH OPERATOR INPUT | These are scoped optional/missing-confidence sources, not substitutes for core scoring; venue history must match selected venue metadata (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:760-820`). **Required input:** actual sources or documented missingness; no reputation, generic form, or fabricated values. |
| Weather and tee times | READY WITH OPERATOR INPUT | Manifest has dedicated fields and preflight checks any declared source exists; scoring doctrine keeps weather post-score and confidence/source-specific (`config/active_event.json:10-14`; `tools/preflight_event.py:210-250`; `SYSTEM_HANDOFF_SPEC.md:113-123`). **Required input:** approved current weather and tee-time sources, their declared paths if used, and an explicit missing-data disposition. |
| Source-manifest binding and integrity | READY WITH OPERATOR INPUT | The resolver is event-neutral and read-only; it validates 13 logical roles, safe containment, identity metadata, and optional integrity assertions without constructing names or writing files (`engine/source_manifest_resolver.py:1-85,614-760`). The producer reads the manifest only after context/capability passes and blocks before identity/output/deploy creation on a defect (`engine/enrich_cards.py:1279-1312`). **Required input:** separately authorized real manifest at the selected event input root with valid source paths and metadata. |
| Identity and crosswalk | READY WITH OPERATOR INPUT | Resolver is I/O-free, ID-first, rejects ambiguous/unresolved/fuzzy-only joins as release-blocking, and emits deterministic diagnostics/provenance (`engine/identity_resolver.py:1-230,880-1035`; `tests/test_identity_resolver.py:780-880`). **Required input:** field roster IDs plus any approved in-memory crosswalk evidence; unresolved/ambiguous matches must be logged and block release rather than dropped or guessed. |
| Missing-data readiness | READY | Doctrine distinguishes missing rows, malformed values, and valid `DEBUT`; it preserves available layers and widens only affected confidence. `UNSCORED` is not numeric zero (`standards/02_PGA_VENUEDNA_SCORING_SPEC.md:55-100,200-250`; `AGENTS.md:420-438`). Event-specific completeness is NOT APPLICABLE until sources are authorized. |
| Pre-event scoring and Council | NOT APPLICABLE WHILE NO_ACTIVE_EVENT | A pre-event build needs an authorized `PRE_EVENT` context; the pre-tournament Council is required before canonical/deploy finalization and does not replace engine math (`engine/event_context.py:154-230`; `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md:1-110`). |
| Artifact, deploy, live, and audit guardrails | NOT APPLICABLE WHILE NO_ACTIVE_EVENT | Output/deploy separation, protected fetch contracts, immutable pre-event spine, round-specific live artifacts, final audit/write-back restrictions, and Council timing apply only after authorized lifecycle progression (`standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md:60-180`; `AGENTS.md:470-590`; `SYSTEM_HANDOFF_SPEC.md:113-176`). |
| Typed-artifact posture | READY | Typed artifacts remain documentation-only. `rN_analysis`, `final_analysis`, and `cumulative_learning` are independently versioned; the abstract envelope does not impose one wire shape; **NO ADAPTER CURRENTLY JUSTIFIED** (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:262-421`; `scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md`). |

## 5. Safe command inventory and excluded commands

### Demonstrably read-only for repository content

| Command or callable | Classification | Evidence / use |
| --- | --- | --- |
| `Get-Content`, `rg`, `git status`, `git branch --show-current`, `git rev-parse`, `git diff --check`, `git diff -- <path>` | READY | Read/inspection-only commands used by this audit. |
| `git fetch origin` | READY with metadata caveat | Mandatory gate; updates `.git` remote-tracking metadata but not the worktree or repository content. |
| `python tools/preflight_event.py` | READY | Inspected and run. It reads manifest/path state and prints findings; no write APIs are present (`tools/preflight_event.py:1-260`). |
| `engine.event_context.load_pre_event_context()` | READY when called only against an existing manifest | Reads manifest text and validates paths before event-bound I/O; creates nothing (`engine/event_context.py:1-230`). Not run because no `PRE_EVENT` context exists. |
| `engine.source_manifest_resolver.resolve_source_manifest()` | READY when given an already-existing parsed manifest and existing sources | Opens declared source files only for non-null integrity assertions; never creates, writes, renames, deletes, or scores (`engine/source_manifest_resolver.py:1-85`). Not run because no authorized real manifest exists. |
| `engine.identity_resolver` pure resolution/report functions | READY with in-memory inputs | No filesystem/database I/O (`engine/identity_resolver.py:1-18`). Not run because no authorized field/source rows exist. |
| `tools/validate_deploy_contract.py` | NOT APPLICABLE WHILE NO_ACTIVE_EVENT | Its validator documents itself as read-only (`tools/validate_deploy_contract.py:353-360`), but there is no authorized current deploy root to validate. |

### Excluded because they write, create state, download, or lack a no-write proof

- `engine/enrich_cards.py` / its CLI: excluded. It proceeds to source ingestion/scoring and output/deploy creation after gates; current tests prove output/deploy absence only for failures (`engine/enrich_cards.py:1279-1312`; `tests/test_enrich_cards.py:1784-1855`).
- `engine/build_round_analysis.py`, `engine/build_post_mortem.py`, `engine/build_event_package.py`, and all event builders: excluded; they write event/output/deploy/audit artifacts by role.
- `engine/verify_live_feed.py`: excluded; it creates generated inputs and backs up/restores cumulative artifacts (`engine/verify_live_feed.py:180-310`).
- Data ingestion/harvesting or download commands: excluded; they may create raw-cache/database/download state.
- Pytest suites: excluded for this audit. Their fixtures intentionally create temporary files, and source-manifest tests can create symlinks/junctions and include a protected-fixture exception (`tests/test_source_manifest_resolver.py:1-180`; `tests/test_event_context.py:1-330`). No test was run.

## 6. Future weekly event-setup checklist, authorization point, and stops

This is a control checklist, not authorization to act.

1. **Resolve the lifecycle conflict first — BLOCKED.** A committed decision must reconcile `PERPLEXITY_OPERATING_PROTOCOL.md` Step 5 with `AGENTS.md` and `tools/preflight_event.py`. Until then, do not create a folder, manifest, or active-event change.
2. **Obtain explicit operator authorization — READY WITH OPERATOR INPUT.** The operator must supply the event identity, venue identity, event window, and authority to initialize; Perplexity must publish the complete committed setup handoff before a builder acts (`PERPLEXITY_OPERATING_PROTOCOL.md:44-105`; `SYSTEM_HANDOFF_SPEC.md:92-110`).
3. **Verify admission and venue intelligence — READY WITH OPERATOR INPUT.** Confirm the selected pair is production-admitted and the selected canonical venue profile/intelligence is complete. Stop on unsupported capability or absent/incomplete venue intelligence (`docs/data_contracts.md:387-407`; `PERPLEXITY_OPERATING_PROTOCOL.md:52-58`).
4. **Create only under a new authorized setup task — NOT AUTHORIZED NOW.** The setup owner may then create the canonical event structure, source manifest, and active-event state according to the resolved lifecycle. This audit does not authorize any of those writes.
5. **Require real operator-provided inputs — READY WITH OPERATOR INPUT.** Provide current field roster, source exports for all 13 roles, venue-history evidence or declared absence, approved weather and tee-time evidence, source metadata/provenance, and any valid identity crosswalk evidence. Do not fabricate inputs or infer filenames from an event/venue name (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:617-820`; `standards/02_PGA_VENUEDNA_SCORING_SPEC.md:20-100`).
6. **Run only later approved validation — NOT APPLICABLE NOW.** After context is valid, use read-only preflight/source/identity/deploy checks. Stop before scoring if context, capability, field, path safety, manifest integrity, or identity release report blocks. Run the producer, Council, deploy, live, and audit paths only under their own later authorized lifecycle stage.

## 7. Risks, unknowns, and explicit non-actions

**Highest-risk unresolved item:** the `INITIALIZED` versus allowed-status conflict is a direct operational blocker. A superficially successful folder/manifest setup would still fail the current preflight and violate higher-precedence active-event governance.

Additional unknowns are intentionally unresolved: no operator-selected event/venue/window, no production-admission decision for a selected pair, no verified venue profile, no actual field/SG/weather/tee-time source, no real source manifest, no identity release report, no active deploy surface, and no Council/artifact validation. Their absence is expected under `NO_ACTIVE_EVENT`; none was inferred from archives.

**Explicit non-actions:** only this report was created. No event was initialized; no source manifest, projection, live/final artifact, audit, payload, deploy output, cache, backup, download, database, fixture, type, validator, adapter, migration, standards/code/test/tool/README/library/config/data change was made. `events/2026_wyndham_championship/` was not opened, modified, moved, regenerated, or used as current authority. No commit or push occurred.

## 8. Next authorization needed

Authorize a small governance-reconciliation task first: resolve the Weekly Event Setup Protocol's `INITIALIZED` requirement against the active-event statuses accepted by `AGENTS.md` and `tools/preflight_event.py`, including the precise valid transition and ownership. Only after that committed resolution should an operator authorize a separate event-specific setup handoff that names the event/venue/window, verifies production capability and venue intelligence, authorizes creation of event inputs/manifest/state, and lists exact read-only preflight and later build validations.
