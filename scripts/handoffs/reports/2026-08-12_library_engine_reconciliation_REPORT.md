# Library/Engine Reconciliation Report

**Date:** 2026-08-12  
**Scope:** read-only reconciliation of `library/engine/` documentation against the current canonical standards and operational documentation.  
**Active event:** `NO_ACTIVE_EVENT` (verified from `config/active_event.json`).

## Executive finding

`standards/` is the governing doctrine for architecture, scoring, artifact contracts, learning, and Council governance. Most numbered `library/engine/` files preserve the June 2026 VTS/Perplexity operating model and must not be used as runtime authority. They remain useful historical and operational context, with two material exceptions:

- The detailed audit and write-back method in legacy `03` and `07` is more complete than the current runtime-focused `standards/03` learning-loop schema. That policy should be promoted selectively in a separately authorized doctrine change.
- `ROUND_ANALYSIS_SCHEMA.md` is linked directly from `README.md` and describes fields emitted by `engine/build_round_analysis.py`; it cannot be deprecated. It is only partially current and needs a separately scoped schema synchronization.

No legacy document is directly referenced by current shared engine or deploy code by filename. Historical event files and templates contain historical textual references, which are not current production imports.

## Pair-by-pair disposition

### `00_MASTER_SYSTEM_ARCHITECTURE.md` vs `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`

**Classification:** Superseded.

The library document is a June migration-era VTS architecture: fixed score-band tiers, mutable venue-weight dictionaries, current-market and DraftKings workflow, and permanent cross-venue rules. The canonical architecture instead establishes the official VenueDNA-versus-DG authority chain, a static deploy pipeline, dual-vector input topology, and current artifact paths.

**Preserve:** the clear persistent-library versus weekly-engine separation, audit-first operating philosophy, and result-quality provenance as historical design rationale.

**Proposed disposition:** Archive/deprecate with a pointer to canonical `standards/00` and `standards/02`. Do not promote fixed VTS thresholds, DFS/market steps, or named June rules into the standards; formula v2.0.0 has no active penalty/gate set.

### `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT_v1.1.md`

**Classification:** Additive/unique, but non-canonical control-plane material.

There is intentionally no `standards/01`: the standards sequence reserves canonical system doctrine for 00 and 02–05, while this file is a Perplexity Space prompt. It retains useful evidence, missing-data, artifact, and drift checks, but its authority hierarchy conflicts with the repository hierarchy in `AGENTS.md` and names legacy `07` as audit authority.

**Preserve:** its compact failure tests, evidence-standard language, and explicit instruction not to let derivative products alter core ranking.

**Proposed disposition:** Keep only as a clearly labeled legacy Perplexity adapter, with a deprecation pointer to `AGENTS.md`, `SYSTEM_HANDOFF_SPEC.md`, and standards 00/02–05. Do not create a canonical `standards/01` unless an operator authorizes a platform-neutral control-prompt standard.

### `01_SYSTEM_PROMPT_FULL.md`

**Classification:** Superseded duplicate.

It duplicates the earlier VTS operating model and embeds stale venue-library status, model routing, fixed VTS tiers, market/DK workflow, and automatic venue write-back language. It conflicts with the current immutable pre-event, Council, and operator-approval rules.

**Preserve:** no unique executable doctrine; its venue-specificity and auditability checks are already represented more safely in the v1.1 Space prompt and current governance.

**Proposed disposition:** Archive with a pointer to the v1.1 prompt and canonical standards. It should not be loaded beside the newer prompt.

### `02_PGA_VENUEDNA_SCORING_SPEC_historical.md` vs `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`

**Classification:** Superseded historical doctrine.

The legacy specification has a richer prospective decomposition—NeutralSkill, VenueFit, VenueHistory, penalties, gates, variance, and risk linkage—but assigns operational score effects that formula v2.0.0 does not authorize. Canonical v2 uses `SG_Base_Comp + Delta_Fit_Comp + 0.0 VenueHistoryDeltaRaw`; penalties and gates are identity transforms under `venuedna_v2_none`, and tiers are rank bands rather than score thresholds.

**Preserve:** the layer separation, confidence-by-source requirement, setup-sensitive anti-pattern analysis, and bounded/no-overfit write-back concepts. They are candidates for future approved penalty/gate research, not current scoring inputs.

**Proposed disposition:** Archive/deprecate with a pointer to canonical `standards/02`; preserve selected policy in a future evidence-backed proposal rather than merging formula text.

### `02_VTS_SCORING_ENGINE.py` vs `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`

**Classification:** Superseded legacy executable.

The script hard-codes a template venue dictionary, score-threshold tiers, flat tier probabilities, active form/debut/anti-pattern gates, a DraftKings optimizer, and a market edge table. It has no current shared-engine reference and does not implement source-manifest binding, canonical identity handling, dual-vector v2 scoring, or the protected output contract.

**Preserve:** it is a useful historical prototype showing former score traces and derivative isolation intent; no code should be promoted directly.

**Proposed disposition:** Deprecate/archive with a pointer to `engine/venuedna_scoring.py` and `engine/enrich_cards.py`. Do not execute it for an event.

### `03_PGA_VENUEDNA_LEARNING_LOOP.md` vs `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`

**Classification:** Superseded for runtime schema; additive for final-audit method.

The canonical document governs deployed round cadence, correlation, trait validation, round/cumulative JSON, and Council evidence. The legacy document adds a full post-event accountability sequence: significant-miss taxonomy, setup-modifier and risk-conversion review, global miss ledger, bounded update thresholds, and explicit venue-versus-engine write-back split.

**Preserve:** sections 5–15 of the legacy document, after reconciling terminology with v2 scores and the current artifact schema. This is the strongest material gap found.

**Proposed disposition:** In a separately authorized doctrine task, promote an audit/write-back section into canonical `standards/03` (or an explicitly authorized new canonical audit standard). Until then retain as reference-only; do not treat it as equal authority.

### `03_PERPLEXITY_REBUILD_GUIDE.md`

**Classification:** Additive historical migration note; miscategorized by number.

It is not a learning-loop specification. It documents June Perplexity limitations, then-current model routing, external storage options, manual audit workflow, and a legacy VTS execution script. Those platform claims and model recommendations are stale and are not repository doctrine.

**Preserve:** platform-migration history only.

**Proposed disposition:** Archive under migration/history documentation or deprecate with a pointer; do not retain it in the numbered learning-loop namespace.

### `04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` vs `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`

**Classification:** Superseded contract with additive packaging guidance.

Canonical `standards/04` specifies current input/output/deploy contracts, unknown-value policy, mismatch reporting, venue-intelligence artifacts, and the source-manifest contract. The legacy document instead defines Space-era artifact classes, older field names, stale deploy names, and broader audit package guidance.

**Preserve:** the three artifact-class explanation, static-deploy rule that browser code does not calculate model logic, version/iteration provenance, and structured final-audit write-back/miss-ledger concepts—after contract review.

**Proposed disposition:** Deprecate with a pointer to canonical `standards/04`; selectively promote only missing packaging or audit-artifact requirements in a versioned contract change. Do not merge old CSV/JSON shapes or filename examples.

### `04_QUICK_REFERENCE_CARD.md`

**Classification:** Superseded duplicate summary.

It condenses the legacy VTS score bands, gates, Weather/DK rules, locked June venue list, and betting language. Those facts conflict with or exceed active canonical v2 scoring authority.

**Preserve:** none as policy; it may have historical training/reference value.

**Proposed disposition:** Archive/deprecate. If a current quick reference is desired, generate it solely from current standards and active-event protocol in a separate task.

### `05_PGA_VENUEDNA_SPACE_SETUP_GUIDE.md` vs `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`

**Classification:** Different topic; not a duplicate and not a misfiled Council document.

The library file describes Perplexity Space setup, uploads, links, connectors, and Netlify deployment. Canonical `standards/05` governs Model Council membership, triggers, objection handling, and limits. Neither replaces the other.

**Preserve:** the one-source-of-truth and active-context hygiene principles.

**Proposed disposition:** Keep only as historical platform setup guidance or move/deprecate with a pointer; it requires a current platform verification before operational use. Do not merge it into Council governance.

### `06_PGA_VENUEDNA_EVENT_WORKFLOW.md` vs `SYSTEM_HANDOFF_SPEC.md` and `README.md`

**Classification:** Additive workflow narrative, but superseded for execution authority.

The document provides a useful Monday-to-post-event sequence and setup-condition checklist. `SYSTEM_HANDOFF_SPEC.md` instead governs task handoffs and change ownership, while `README.md` contains the current but legacy-event-specific technical runbook. The library workflow includes old VTS, odds, and DK behavior, and says to revise venue files directly after an audit—contrary to current operator-approval discipline.

**Preserve:** venue/context lock, missing-data disclosure, pre-score sanity checks, live structural-versus-noise assessment, and audit completeness checklist.

**Proposed disposition:** Do not use as an authoritative runbook. In a separate task, extract a platform-neutral operator runbook into `docs/`, reconciled against `AGENTS.md`, active-event lifecycle, and current command paths. Until then deprecate with pointers to `SYSTEM_HANDOFF_SPEC.md`, `README.md`, and standards.

### `07_PGA_VENUEDNA_AUDIT_STANDARD.md` vs `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`

**Classification:** Additive/unique final-audit doctrine; its former canonical claim is superseded.

This is the most complete human audit template: it requires tier-shape review, anti-pattern direction/magnitude and setup modifiers, risk-mechanism conversion, probability compression, live review, miss taxonomy, and explicit venue/engine outcomes. Canonical `standards/03` currently centers deployed round artifacts and schema updates, so it does not fully replace this material.

**Preserve:** sections 4–14, particularly the audit question ordering and write-back decision statuses, after updating field names and approval language.

**Proposed disposition:** Promote the reconciled policy into canonical `standards/03` or an authorized audit standard, then retain this legacy copy only as a deprecated pointer. No automatic write-back behavior should be adopted.

### `PGA_VENUEDNA_SYNC_CHECK_2026-06-24.md`

**Classification:** Dated point-in-time note.

It accurately records the June relationship among the then-current 01/02/03/04/06/07 files and recommends a prompt patch that was subsequently represented by the v1.1 prompt. It is not evidence of current alignment.

**Preserve:** provenance of the June reconciliation decision.

**Proposed disposition:** Archive as a dated historical audit note; do not use to establish current doctrine.

### `ROUND_ANALYSIS_SCHEMA.md`

**Classification:** Current referenced operational schema; partially stale, not a duplicate.

`README.md` explicitly names this file as the complete field-by-field definition. Its core structure matches `engine/build_round_analysis.py` (`round_sources`, `live_lean_notes`, `match_summary`, `model_performance`, `trait_audit`, and `leaderboard_snapshot`). The producer now also emits fields not documented here, including weather/wave metadata and `live_probability_engine`; its trait audit has additional live-proxy/enrichment detail. Canonical `standards/03` presents a different, simpler round-artifact example, so the two specifications need an explicit authority/reconciliation decision.

**Preserve:** all of it as the current README-linked interface reference until replaced by a synchronized contract.

**Proposed disposition:** Keep as-is. Open a dedicated schema-sync task to reconcile `ROUND_ANALYSIS_SCHEMA.md`, `engine/build_round_analysis.py`, `README.md`, and `standards/03`; do not deprecate or move it first.

## Reference and deprecation blockers

- **Direct current reference:** `README.md:252` links `library/engine/ROUND_ANALYSIS_SCHEMA.md`. This blocks its deprecation.
- **Current producer alignment:** `engine/build_round_analysis.py` emits the round-analysis structures documented by that file, with newer fields that the document does not yet enumerate. This blocks treating the file as historical.
- **No direct current shared-engine or deploy-code imports:** filename-reference search found no current `engine/` or deploy `app.js` dependency on the other listed legacy files.
- **Historical references remain:** archived John Deere/Travelers materials and legacy templates mention older numbered docs. They are archival/template references, not evidence that a listed document governs current production behavior.

## Open operator decisions

1. Should the detailed final-audit/write-back policy from legacy `03` and `07` be promoted into `standards/03`, or should an explicit new canonical audit standard be created?
2. Should legacy Perplexity Space/migration documents remain in `library/engine/` as history, or move to a clearly historical documentation location?
3. Should a current operator runbook replace the mixed legacy `README.md`/`06` workflow guidance?
4. Which artifact contract governs detailed round-analysis JSON: should `ROUND_ANALYSIS_SCHEMA.md` be synchronized into `standards/03`, or should `standards/03` explicitly defer to it?

## Task impact

This report makes no scoring, payload, identity, deploy, database, event-state, or canonical-document changes. All dispositions are proposals only.
