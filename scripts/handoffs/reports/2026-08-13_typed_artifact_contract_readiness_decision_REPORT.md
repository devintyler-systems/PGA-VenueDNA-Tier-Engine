# Typed Artifact Contract Readiness and Scope Decision

**Date:** 2026-08-13
**Mode:** Read-only governance and scope decision
**Decision confidence:** High for the present posture; medium for any future implementation sequencing because there is no active non-archived deploy consumer.

## 1. Executive decision

**Recommendation — documentation-only.** The minimum safe immediate posture is to retain the now-complete canonical policy and compatibility baseline without creating a typed contract, standalone runtime validator, adapter, migration, or producer/consumer change.

**Fact.** `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §3F already assigns the three detailed families independent version lines, their detailed member treatment, compatibility policy, final discriminator, and cumulative state behavior (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:262-421`). `standards/03` defers detailed field/type/nesting/missing-value decisions to that authority (`standards/03_PGA_VENUEDNA_LEARNING_LOOP.md:111-137`), and `docs/data_contracts.md` declares the Live Artifact envelope abstract rather than a common emitted wire shape (`docs/data_contracts.md:485-508`).

**Inference.** A documentation-only posture is sufficient now because policy has been settled while a verified non-archived, deployed consumer boundary has not: the active manifest has no event or deploy root, and the only non-archived UI reader found is a reusable template, not an active board (`config/active_event.json:2-20`; `library/ui_templates/template_app.js:1890-2188`).

**Recommendation.** Make no typed-family implementation now. Preserve `engine/build_round_analysis.py`, README, and library schema as compatibility evidence only. Reconsider a bounded, family-local implementation only after a separately authorized task names a current producer/consumer boundary, frozen samples, and validation owner.

### Rejected postures

| Rejected posture | Why it is not warranted now |
| --- | --- |
| Runtime validation-only | **Fact:** the producer already has narrow build-time checks for versions and selected invariants, while `engine/verify_live_feed.py` drives a producer and writes/backups event paths (`engine/build_round_analysis.py:2032-2108`; `engine/verify_live_feed.py:180-310`). **Inference:** a new independent validator would need the same field semantics, version dispatch, fixtures, and owner decisions as a typed family but lacks an identified current runtime boundary. It would add a second, unauthorised compatibility authority rather than reduce a demonstrated production risk. |
| Shared producer/consumer contracts | **Fact:** §3F says the three families are independent, the envelope does not require one producer shape, and no adapter is justified (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:300-302,404-421`). The only current non-archived UI reader is a template that reads detailed fields directly (`library/ui_templates/template_app.js:1890-2188`); there is no active event board (`config/active_event.json:4-17`). **Inference:** there is no verified shared wire boundary to own. A shared contract would prematurely couple independently versioned families and implicitly introduce the envelope mapping that doctrine rejects. |

## 2. Gate results

All mandatory gates passed before substantive inspection.

| Command | Concise result |
| --- | --- |
| `git status --short` | Empty before report creation. |
| `git branch --show-current` | `main`. |
| `git fetch origin` | Completed successfully. |
| `git rev-parse HEAD` | `cdd4b2383e97375c5ab3dd537ec96dc7d8ab4326`. |
| `git rev-parse origin/main` | `cdd4b2383e97375c5ab3dd537ec96dc7d8ab4326` — equal to local HEAD. |
| `git status -sb` | `## main...origin/main`. |
| `git log -1 --oneline HEAD` | `cdd4b23 docs: add typed artifact contract readiness decision handoff`. |
| `git log -1 --oneline origin/main` | Same commit and subject. |
| `Get-Content config/active_event.json` | `status` is `NO_ACTIVE_EVENT`; event/deploy pointers are null. |

## 3. Authority and evidence map

| Classification | Evidence and effect |
| --- | --- |
| **Governing fact** | `AGENTS.md` and `CLAUDE.md` place explicit task scope first, then repository governance, `SYSTEM_HANDOFF_SPEC.md`, canonical standards, code/tests/deploy contracts, and historical artifacts (`AGENTS.md:15-28`; `CLAUDE.md:15-31`). `SYSTEM_HANDOFF_SPEC.md` requires a committed synchronized handoff and preserves JSON consumed by `app.js` as a protected contract (`SYSTEM_HANDOFF_SPEC.md:92-110,113-123`). |
| **Governing fact** | `standards/04` §3F owns detailed fields, types, nesting, requiredness, source-contingent behavior, versions, compatibility/deprecation/translation, producer obligations, and consumer-validation requirements; §3F expressly creates no typed definition, adapter, migration, producer change, or README/library transition (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:280-298,404-421`). |
| **Governing fact** | `standards/03` owns learning cadence, interpretation, audit and write-back behavior rather than a competing detailed payload (`standards/03_PGA_VENUEDNA_LEARNING_LOOP.md:111-137`). `docs/data_contracts.md` owns the abstract envelope and general JSON/migration rules (`docs/data_contracts.md:485-508,788-803,856-900`). |
| **Compatibility fact** | The current producer emits round/final `schema_version: "1.1"`, a separate cumulative state at `"1.0"`, and writes them to output and deploy paths (`engine/build_round_analysis.py:1516-1596,1936-2027`). README points to the library schema as complete, but §3F demotes both to compatibility evidence pending a versioned migration (`README.md:232-252`; `library/engine/ROUND_ANALYSIS_SCHEMA.md:1-300`; `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:272-278,404-413`). |
| **Non-authoritative evidence** | Prior discovery, reconciliation, envelope, and detailed-interface reports record the prior conflict, its resolution, the family boundary, and absence of a verified non-archived envelope consumer (`scripts/handoffs/reports/2026-08-12_round_analysis_schema_sync_REPORT.md:8-14`; `scripts/handoffs/reports/2026-08-12_live_artifact_envelope_abstract_contract_REPORT.md:8-56`; `scripts/handoffs/reports/2026-08-12_round_cumulative_schema_strategy_discovery_REPORT.md:7-13,71-111`; `scripts/handoffs/reports/2026-08-12_detailed_artifact_interface_decision_REPORT.md:1-157`). They support, but do not supersede, current §3F. Archived boards were not used as present authority. |

**Conflict finding — no current governing conflict.** Earlier reconciliation reported conflicting detailed examples; current `standards/03` and `docs/data_contracts.md` now explicitly defer to §3F. The remaining gap is evidence, not an authority conflict: no active non-archived deployed consumer establishes a shared runtime boundary.

## 4. Current-state findings

### Producer, consumers, and validation

1. **Fact — producer shape.** `engine/build_round_analysis.py` constructs one current round/final payload with required metadata, detailed maps/arrays, and `metadata.is_full_tournament`; final mode changes output location and terminal metadata, not the shared construction (`engine/build_round_analysis.py:1936-2021`). It persists cumulative state by output-first, deploy-fallback, then fresh initialization; repeated rounds replace the existing history index rather than append it (`engine/build_round_analysis.py:1516-1596`).
2. **Fact — current narrow checks are not a typed-contract system.** The producer dry-run reopens just-written files and checks two fixed schema versions, selected names, and probability monotonicity (`engine/build_round_analysis.py:2032-2108`). `engine/verify_live_feed.py` validates a fixed R1 scenario but writes generated inputs and restores backups, so it is not read-only test evidence to run in this review (`engine/verify_live_feed.py:180-310`).
3. **Fact — consumers are path/detail specific.** `engine/build_post_mortem.py` only consumes `leaderboard_snapshot[].r1_name`, `.wave`, and `.wave_penalty` when R1 analysis exists (`engine/build_post_mortem.py:113-132`). The reusable template directly reads round metadata, lean notes, match summary, model performance, snapshot records, and cumulative state/history (`library/ui_templates/template_app.js:1890-2188`). Neither establishes a generic Live Artifact envelope boundary.
4. **Fact — deploy profile validation is only fetch/integrity validation.** The deploy-profile tests build temporary deploy trees, and `tools/validate_deploy_contract.py` validates declared dynamic payload existence/parseability rather than rN/final/cumulative field semantics (`tests/test_deploy_profile_validation.py:1-110`; `tools/validate_deploy_contract.py:128-220`; `library/templates/deploy_payload_manifest.json:1-14`). It must not be recast as an artifact-family validator without authorization.
5. **Inference.** There is no evidence for a common producer/consumer contract package. Current sources support preservation tests around separate detailed artifacts and path references, not a shared emitted envelope.

### Family baseline

| Family | Current compatibility fact | Governing boundary | Immediate scope decision |
| --- | --- | --- |
| `rN_analysis` | Producer emits `"1.1"` and R1–R4 paths; R1–R4 use a common construction (`engine/build_round_analysis.py:1936-2021`). | One independently versioned round family; R1–R4 share a line unless a true interface difference requires a split (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:300,324-353`). | No new typed or validation implementation. |
| `final_analysis` | Producer uses the same base payload but final output path, `round: 4`, `metadata.is_full_tournament: true`, and `round_label: "Final Tournament"` (`engine/build_round_analysis.py:1931-2021`). | Independent terminal family, not an R4 alias; future terminal-only members and future parity remain unresolved (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:301,355-374`). | No new typed or validation implementation. |
| `cumulative_learning` | Separate persistent `"1.0"` document; it is read/updated/written as state (`engine/build_round_analysis.py:1516-1596,2024-2027`). | Independent state family with initialization, read precedence, update, reprocessing, terminal, and upgrade requirements (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:302,376-401`). | No new typed or validation implementation. |

## 5. Scope decision

**Recommendation — minimum immediate typed-family scope: zero families.** No event is active, no current deployed non-archived consumer exists, and no producer/documentation transition is authorized. Documentation-only preserves the current compatibility baseline without using it as a transition target.

**Future-only sequencing direction, not implementation authorization:** if an actual current consumer need later exists, evaluate one independently owned family at a time. Start with `rN_analysis` only if the named need is a direct round consumer; do not pull `final_analysis` or `cumulative_learning` into that work merely because the producer currently shares code. Add final only after final-versus-R4 parity and terminal summaries are explicitly settled. Add cumulative only through a state-aware scope that includes upgrade behavior. This follows §3F family separation and avoids a shared producer wire format (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:300-302,355-401`).

## 6. Semantic decisions — future direction only

These are documentation-level directions for a later, separately authorized scope; they create no schema, type, validator, adapter, or migration.

| Topic | Future-only recommendation | Basis |
| --- | --- | --- |
| Type representation | Use separate, producer-owned Python structural representations/validators for each approved family, with an externally documented JSON contract only where §3F requires it. Do not create a common cross-family package or make the abstract envelope an emitted base type. | Python producer and existing Codex schema are the relevant implementation lane (`engine/build_round_analysis.py`; `standards/VENUEDNA_CODEX_SCHEMA.md:1-240`); §3F forbids assuming a common wire shape (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:262-298,404-421`). |
| Enum handling, including unknowns | Classify each enum in an authorized family scope. Treat only values explicitly closed by canonical policy as closed. For any not-yet-closed or source/legacy value, preserve an unknown string as unknown with a diagnostic/warning; do not coerce it to a known value or silently reject/rewrite producer output. Future consumer presentation may choose a safe fallback only without changing the artifact value. | §3F leaves exact scalar domains unresolved in places and preserves legacy/source-contingent values (`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:321-353`); general rules prohibit changing a field type or reusing meaning (`docs/data_contracts.md:788-803`). |
| Nullable, absent, and empty arrays | Preserve the exact §3F tri-state policy: unavailable optional scalar is `null`; no-result collection is `[]`; unavailable tagged object is its `{ "available": false, ... }` form; a member is absent only where §3F expressly permits it. Tests must distinguish all four forms. | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:311-322,336-353`; `docs/data_contracts.md:788-803`. |
| Legacy members and boundaries | Preserve current legacy compatibility names and semantics unchanged until an approved versioned deprecation window with replacement mapping and selected non-archived consumer validation. This includes `total_r1`, R1-prefixed model/leaderboard terms, and final/R4 labels. No translation now. | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:340-348,365-374,394-403`. |
| `final_analysis` discriminator | The future terminal representation must retain `round == 4`, `metadata.is_final == true`, and use `metadata.is_full_tournament == true` as the required discriminator; `r4_analysis` remains false. Do not infer final family only from filename or `is_final`, because R4 also uses that flag. Keep terminal-only members unresolved pending explicit authority. | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:355-374`; `engine/build_round_analysis.py:1931-2021`. |
| Cumulative state, update, and upgrade | Treat it as persistent state, not a round payload collection: preserve initialization members, output-first/deploy-fallback read precedence, sorted unique round history, in-place reprocessed-round replacement, terminal persistence, and history-aware upgrade. Any future upgrade must dispatch on source version, be idempotent, preserve or deterministically reconstruct history, validate before persistence, and never silently reinterpret state. | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:376-403`; `engine/build_round_analysis.py:1516-1596`. |
| Validation ownership | Producer owns family-local structural validation and version dispatch; each actual consumer owns its own narrow assumption validation. Deploy-profile tooling owns paths, existence, parsing, and integrity only. No central/shared validator or envelope adapter is justified. | `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:404-421`; `docs/data_contracts.md:536-547,856-900`; `tools/validate_deploy_contract.py:128-220`. |

## 7. Future-only test strategy

Do not implement or run this plan under the present authorization.

1. **Fixtures.** Add version-pinned, event-neutral canonical JSON fixtures only in a future approved test scope. Do not derive current authority from archived boards or `events/2026_wyndham_championship/`. Freeze a representative baseline for each selected family from an authorized producer run or specially approved synthetic fixture.
2. **Positive cases.** For `rN_analysis`, cover every required object/array, source-contingent `null`, absent-only members, tagged unavailable enrichment, legacy member preservation, and all R1–R4 cases. For final, cover its discriminator and R4 non-final-family comparison. For cumulative, cover fresh initialization, output/deploy fallback, partial history, reprocessed round replacement, final state, and every supported source-version upgrade.
3. **Negative cases.** Reject/diagnose wrong version dispatch, required-member/type/nesting changes, illegal absent-vs-null-vs-empty substitutions, closed-enum violations once canonically defined, invalid final discriminator, cumulative duplicate/unsorted history, non-idempotent upgrade, and loss of historic records.
4. **Compatibility cases.** Preserve current legacy names and currently supported compatibility fields through selected producer and actual named-consumer tests. Treat unknown open enum values as retained/directed diagnostics rather than conversion. Add producer/consumer boundary tests only if a separately authorized shared contract is later justified.
5. **Ownership tests.** Keep deploy tests limited to fetch/path/parse/integrity unless their scope is separately expanded; the existing temporary-tree deploy tests prove that separation (`tests/test_deploy_profile_validation.py:1-110`; `tests/test_build_deploy_profile.py:280-430`).

## 8. Risks and stop conditions

**Highest-risk unresolved question:** there is no active non-archived deployed consumer to establish which detailed fields must be validated as runtime commitments; concurrently, §3F leaves future final-only members and final/R4 shape parity unresolved (`config/active_event.json:4-17`; `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:355-374`). This is an evidence gap, not a governing conflict.

Stop and obtain a new authorization if any proposed next step would:

- create types, schemas, validators, adapters, fixtures, migrations, or shared contracts;
- select final-only members or change final/R4 parity;
- reinterpret current versions, enum/null/absent/empty semantics, or cumulative state behavior;
- name an active board, change deploy fetches, or rely on archived/Wyndham artifacts as current authority; or
- require testing that creates event files, deploy payloads, caches, generated artifacts, or databases.

## 9. Explicit non-actions

Only this report was created. No changes were made to `standards/**`, `engine/**`, `tests/**`, `tools/**`, `README.md`, `library/**`, `deploy/**`, `config/**`, data, databases, event files, deploy payloads, or archived content. `events/2026_wyndham_championship/` was not opened, modified, moved, regenerated, or used as current authority. No implementation, event initialization, test run, commit, or push occurred.

## 10. Next authorization needed

Before any implementation, authorize a new bounded task that names **one** family, the current non-archived producer and actual consumer(s), frozen canonical fixture source, exact version/enum/member policy to enforce, validation owner, positive/negative compatibility matrix, and whether final/R4 or cumulative state behavior is in scope. The task must explicitly retain the §3F family boundary and state that no adapter is in scope unless new verified consumer evidence and a versioned mapping are separately approved.
