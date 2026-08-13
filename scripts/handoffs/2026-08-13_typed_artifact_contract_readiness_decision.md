# Typed Artifact Contract Readiness and Scope Decision

**Date:** 2026-08-13  
**Task class:** Read-only governance, readiness, and scope decision  
**Executor:** Codex or Claude Code, read-only reviewer  
**Repository:** `devintyler-systems/PGA-VenueDNA-Tier-Engine`  
**Required branch:** `main`  
**Required local repository:** `C:\PGA_VenueDNA`  
**Active event required state:** `NO_ACTIVE_EVENT`

## 1. Objective

Produce a decision package on the readiness and minimum future scope for typed artifact contracts. This is a **read-only scope-decision task**, not a type-design or implementation task.

The sole executor output is:

```text
scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md
```

The report must decide, from governing doctrine and current compatibility evidence, whether the correct next state is:

1. documentation-only;
2. runtime validation-only; or
3. shared producer/consumer contracts.

It must not create types, schemas, validators, adapters, migrations, producer changes, consumer changes, or deployment artifacts.

## 2. Governing context

The committed governance result in `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §3F controls this review:

- `rN_analysis`, `final_analysis`, and `cumulative_learning` are independently versioned families.
- The abstract Live Artifact envelope does not require a shared producer wire format.
- **NO ADAPTER CURRENTLY JUSTIFIED** remains binding.
- Current producer output, `README.md`, and `library/engine/ROUND_ANALYSIS_SCHEMA.md` remain compatibility evidence only; they are not authorized targets for transition.

Follow authority in this order:

1. Explicit current task.
2. `AGENTS.md`.
3. Active event files and instructions.
4. `SYSTEM_HANDOFF_SPEC.md`.
5. Canonical standards in `standards/`.
6. Repository code, tests, and deploy contracts.
7. Historical artifacts and archived events.

If authority conflicts, stop. Name the conflict, cite paths and exact competing rules, identify the governing authority, and recommend the smallest safe resolution. Do not resolve the conflict by changing files.

## 3. Mandatory gates

Run these gates before substantive inspection. Include commands and concise results in the report.

```powershell
git status --short
git branch --show-current
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status -sb
git log -1 --oneline HEAD
git log -1 --oneline origin/main
Get-Content config/active_event.json
```

Proceed only if all of the following are true:

- `config/active_event.json` has `status: NO_ACTIVE_EVENT`.
- Local branch is `main`.
- `git status --short` is empty before report creation.
- Local `HEAD` equals `origin/main` after `git fetch origin`.
- No uncommitted, untracked, or unrelated local changes exist.

If a gate fails, stop substantive work. The report may document the failure only; do not fix synchronization, clean the worktree, initialize an event, or alter state.

## 4. Required inspection

Inspect these governing and compatibility sources before deciding scope:

- `AGENTS.md`
- `CLAUDE.md`
- `PERPLEXITY_OPERATING_PROTOCOL.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`, with direct attention to §3F
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `README.md`
- `library/engine/ROUND_ANALYSIS_SCHEMA.md`
- `engine/build_round_analysis.py`
- Relevant **non-archived** tests, validators, shims, templates, producers, consumers, and artifact references
- Committed reconciliation, discovery, and detailed artifact-interface decision reports relevant to the three live-analysis families

Use read-only discovery first. Suitable commands include:

```powershell
git ls-files
git log --oneline --all -- scripts/handoffs scripts/handoffs/reports standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
git grep -n -I -e "rN_analysis" -e "final_analysis" -e "cumulative_learning" -e "schema_version" -e "adapter" -- ':!events/2026_wyndham_championship/**'
```

Inspect only what is needed to establish current contracts, consumers, compatibility boundaries, and test/validation ownership. Do not treat an archived board as current authority.

## 5. Questions the report must answer

### 5.1 Contract posture

Choose one and explain why it is the minimum safe next state:

- **Documentation-only:** canonical policy and compatibility evidence are sufficient; no runtime contract is presently justified.
- **Runtime validation-only:** one or more independently owned runtime validators are justified without a shared producer/consumer contract.
- **Shared producer/consumer contracts:** a common typed contract is necessary and justified across actual producer and consumer boundaries.

State the evidence, authority hierarchy, practical benefit, compatibility risk, and reason the two rejected choices are not presently warranted.

### 5.2 Minimum future family scope

If a future typed step is justified, state the smallest safe family scope. Address separately:

- `rN_analysis`
- `final_analysis`
- `cumulative_learning`

Do not assume these families require the same type, release cadence, ownership model, wire format, or validation system. Identify whether a first step should cover zero, one, or multiple families and why.

### 5.3 Type representation and field semantics

Recommend only a future direction, not a concrete implementation. The report must decide:

- Candidate type representation appropriate to the repository and governance constraints.
- Enum handling, including open versus closed sets and unknown values.
- Difference between nullable, absent, and empty-array fields.
- Legacy members: preserve, deprecate, reject, or translate only under a separately authorized future change.
- Compatibility expectations for current producer output and current README/library documentation.

### 5.4 Family-specific boundaries

State a recommended future representation and ownership boundary for:

- The final-artifact discriminator for `final_analysis`.
- `cumulative_learning` state, update, and upgrade representation.
- Versioning and upgrade behavior for each independently versioned family.

The report must preserve the doctrine that an abstract Live Artifact envelope does not itself require a shared producer wire format.

### 5.5 Validation ownership and test strategy

Recommend where future validation would conceptually belong and who owns it, while preserving producer/consumer boundaries. Identify a future test strategy covering:

- Canonical fixtures.
- Positive and negative validation cases.
- Enum, nullable, absent, and empty-array cases.
- Legacy compatibility cases.
- Producer/consumer boundary tests only if shared contracts become justified.
- Family-version compatibility and upgrade behavior.

Do not run any test that writes fixtures, caches, generated files, deploy payloads, databases, or event artifacts. A test may be considered only after establishing it is read-only; otherwise exclude it and document why.

## 6. Report requirements

Create exactly one Markdown report at:

```text
scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md
```

Use this structure:

1. **Executive decision** — one selected posture, confidence, and immediate recommendation.
2. **Gate results** — active-event, branch, worktree, and local/remote synchronization evidence.
3. **Authority and evidence map** — governing authority, compatibility evidence, ambiguity, and explicitly non-authoritative archival evidence.
4. **Current-state findings** — actual producer/consumer, schema, validation, test, and versioning facts with exact paths.
5. **Scope decision** — minimum family scope and why broader scope is not justified.
6. **Semantic decisions** — type representation direction; enum; nullable; absent; empty array; legacy members; final discriminator; cumulative state/update/upgrade; validation ownership.
7. **Future-only test strategy** — proposed fixtures and tests, with no implementation.
8. **Risks and stop conditions** — unresolved evidence, authority conflicts, and conditions that require a new authorization.
9. **Explicit non-actions** — list every protected area left unchanged.
10. **Next authorization needed** — precise bounded task that would be needed before implementation, if any.

Every material finding must cite exact repository paths. Clearly label fact, inference, and recommendation. Do not substitute reputation, historical practice, or archived artifacts for governing authority.

## 7. Protected files and boundaries

### Sole authorized executor write

```text
scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md
```

### Read-only evidence

All files listed in Section 4, relevant non-archived contract surfaces, and committed governance reports are read-only evidence.

### Explicitly protected: no modification

- `standards/**`
- All Python, JavaScript, CSS, HTML, typed-contract, validation, producer, consumer, shim, template, test, migration, and adapter files
- `README.md`
- `library/**`
- `deploy/**` and `deploy/data/**`
- `config/**`, including `config/active_event.json`
- All event state, manifests, projection/live artifacts, databases, and raw data
- Any archived board or archived event

### Absolute preservation rule

`events/2026_wyndham_championship/` is absolutely preserved. Do not modify, move, regenerate, migrate, delete, or use it as current authority. Do not create new artifacts beneath it or derive a current event state from it.

## 8. Explicitly unauthorized actions

The following are out of scope and forbidden:

- Typed code, type definitions, runtime validators, schemas, shared contracts, or contract packages.
- Standards edits, including §3F or any canonical artifact policy.
- Producer, consumer, adapter, shim, template, migration, or compatibility implementation.
- README or library-schema transition.
- Deploy change, generated deploy payload, static-board change, or data rebuild.
- Event initialization, event-state modification, projections, live analysis, audit artifacts, or archive work.
- Alteration of `events/2026_wyndham_championship/`.
- Any commit or push by Codex or Claude.

**NO ADAPTER CURRENTLY JUSTIFIED** remains binding. Do not propose an adapter as an implementation next step without a separately authorized review that establishes the changed evidence and governing approval.

## 9. Stop conditions

Stop analysis and report the block rather than resolving it if:

- `config/active_event.json` is not `NO_ACTIVE_EVENT`.
- The local branch is not `main`, the worktree is not clean, or local `HEAD` differs from `origin/main`.
- A required governing source or committed decision report is missing, unreadable, or conflicts materially with another higher-authority source.
- Answering a decision question would require writing any protected file or using archived evidence as present authority.
- The review cannot distinguish documentation-only, runtime validation-only, and shared-contract choices using path-specific evidence.
- A conclusion depends on a producer change, adapter, migration, README/library transition, deploy change, test mutation, or event action.

Do not remedy a stop condition. Document it in the authorized report and await a new task.

## 10. Validation and completion

Before handing back the report:

1. Confirm the report is the only executor-created file.
2. Confirm no protected file changed.
3. Confirm no event, deploy, standards, code, README/library, type, validator, adapter, migration, or archive change occurred.
4. Re-run:

```powershell
git status --short
git diff --check
git diff -- scripts/handoffs/reports/2026-08-13_typed_artifact_contract_readiness_decision_REPORT.md
```

5. Report exact changed-file status and commands run.

## 11. Commit and push boundary

Codex/Claude must **not commit or push**. The executor’s sole permitted output is the uncommitted report path named in Section 6.

Perplexity retains responsibility for any later review, creation of a follow-on handoff, and any commit/push decision. A future commit of the report, if desired, requires explicit operator authorization after review.

## 12. Required final response

Return a concise completion note containing:

- Gate outcome.
- Report path.
- Chosen posture: documentation-only, runtime validation-only, or shared producer/consumer contracts.
- Minimum future family scope.
- The highest-risk unresolved question or conflict, if any.
- Confirmation that no implementation, protected-file modification, commit, or push occurred.
