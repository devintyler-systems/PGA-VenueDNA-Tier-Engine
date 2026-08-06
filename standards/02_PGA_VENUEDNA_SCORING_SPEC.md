# 02 — PGA VenueDNA Scoring Specification

**Version:** 2.0-draft
**Status:** Canonical doctrine — implemented by the reusable root producer through `engine/venuedna_scoring.py`
**Formula:** `venuedna_dual_vector_decomposed` v2.0.0; historical 3M arithmetic remains diagnostic-only

<!-- scoring-doctrine-v2
formula_id=venuedna_dual_vector_decomposed
formula_version=2.0.0
comparable_score_family=dual_vector_sg_per_round_v2
penalty_gate_set_id=venuedna_v2_none
canonical_core_inputs=SG_Base_Comp,Delta_Fit_Comp,VenueHistoryDeltaRaw
excluded_legacy_noncore_addends=trait_approach_raw,trait_long_iron_raw,ott_true,ch_adjustment,true_sg_l20
-->

---

## 1. OVERVIEW

Formula v2.0.0 defines the canonical pre-penalty score from separately represented NeutralSkill, VenueFitDelta, and VenueHistoryDelta layers. It does not authorize a direct trait block. The reusable root producer derives official output from canonical `PostGateRaw`; archived historical 3M output remains a production-parity record only.

The dual-vector source layer computes per-horizon SG vectors by:
1. Computing per-horizon SG vectors from All Courses and Similar Courses CSVs
2. Applying sample-weight regression to suppress thin venue samples
3. Blending across three time horizons with decoupled decay weights
4. Z-score scaling to a fixed normal (mean=50, std=15, clamped [0,100])
5. Producing downstream field-normalized projections and probability vectors from the scored field's canonical `PostGateRaw`
6. Deriving Make Cut probability and enforcing monotonicity in the reusable root producer

This document is the authoritative canonical doctrine. The separately scoped, operator-authorized Phase 3 migration makes `engine/enrich_cards.py` the reusable root producer for v2.0.0 official scoring. It does not authorize event initialization, historical-artifact rewriting, deploy, database, or payload-contract migration.

---

## 2. INPUT FILES

Six CSV files are required. All use the same three-column schema:

```
player_name   — string; normalized to "Last, First" format; strip surrounding quotes and whitespace
rounds_played — integer; number of qualifying rounds in the horizon window
total_mean    — float; mean strokes gained per round across the horizon
```

Files (relative to `events/{slug}/input/`):
```
pga_sg_query_allcourses_l6.csv    — All Courses, last 6 months
pga_sg_query_allcourses_l12.csv   — All Courses, last 12 months
pga_sg_query_allcourses_l24.csv   — All Courses, last 24 months
pga_sg_query_{slug}_similar_l6.csv  — Similar Courses, last 6 months
pga_sg_query_{slug}_similar_l12.csv — Similar Courses, last 12 months
pga_sg_query_{slug}_similar_l24.csv — Similar Courses, last 24 months
```

Missing `total_mean` is missing data, not numeric `0.0`. Valid numeric zero remains a valid measurement.

### 2A. Source-manifest path binding (Phase 4.2 implementation)

The filenames listed above remain current, accurate documentation of what the historical, event-hardcoded 3M Open export shape looks like — they are legacy-producer/export documentation, not a naming convention any current or future event must follow. Following the narrow, event-neutral resolver/validator contract defined in `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §9 (schema `source_manifest` v1.0) and the approved resolver at `engine/source_manifest_resolver.py`, `engine/enrich_cards.py` now binds every physical source path — including these six SG-horizon files, the field roster, and every other one of the thirteen required logical source roles — through a validated `source_manifest.json` at the active event's own `input/` root, after `EventContext` validation and the existing capability gate succeed. Physical filenames remain arbitrary and are never inferred, constructed, or guessed from `event_slug` or `venue_slug`; the manifest's own declared `path` per role is the sole authority. This is a path-binding mechanism change only. It does not alter the formula, composite weights, §7.5 missing-data doctrine, tiers, probabilities, penalties, gates, benchmark isolation (§14), or any other scoring rule in this document, and it does not imply this producer is generalized to another venue — see `engine/event_context.py`'s `require_supported_context()` capability gate, which remains unchanged and still scopes this producer to `2026_3m_open` / `tpc_twin_cities` only.

---

## 3. NAME NORMALIZATION

```python
def normalize_name(s):
    return (s or "").strip().strip('"').strip("'").strip()
```

Canonical format: `"Last, First"` (DataGolf convention). All lookups use normalized names.

---

## 4. PLAYER UNIVERSE

The player universe is the union of names appearing in source files. A missing source row is not synthesized as `{rounds: 0, total_mean: 0.0}`. A valid similar-course row with `rounds_played: 0` is the distinct, legitimate `DEBUT` state.

---

## 5. PER-HORIZON COMPUTATION

For each time horizon h ∈ {6m, 12m, 24m}, when its required source is valid:

```
SG_Base_h   = total_mean from allcourses_lh CSV
N_Sim_h     = rounds_played from a valid similar_lh CSV row
SG_Sim_h    = total_mean from a valid similar_lh CSV row

Sample weight:
  W_h = min(1.0, N_Sim_h / 20.0)
  Interpretation: 0 for a valid DEBUT row with no similar-course rounds; 1.0 when ≥20 rounds

Regressed similar-course SG:
  SG_Sim_Reg_h = (W_h × SG_Sim_h) + ((1 - W_h) × SG_Base_h)
  Interpretation: Falls back to baseline for a valid DEBUT row or when N_Sim is thin

Delta Fit per horizon:
  Delta_Fit_h = SG_Sim_Reg_h - SG_Base_h
```

---

## 6. COMPOSITE BLENDING — DECOUPLED DECAY

Two composites are computed independently with different decay schedules:

**SG Base Composite (stability-heavy):**
```
SG_Base_Comp = 0.20 × SG_Base_6m + 0.30 × SG_Base_12m + 0.50 × SG_Base_24m
```
Rationale: Long-term skill is more predictive than short-term form on neutral baseline.

**Delta Fit Composite (recency-heavy):**
```
Delta_Fit_Raw = 0.50 × Delta_Fit_6m + 0.30 × Delta_Fit_12m + 0.20 × Delta_Fit_24m
Delta_Fit_Comp = clamp(Delta_Fit_Raw, -0.50, +0.50)
```
Rationale: Recent venue-type performance is a stronger signal than historical. The ±0.50 clamp prevents extreme thin-sample outliers from dominating.

When one NeutralSkill horizon is missing but two valid horizons remain, omit the missing horizon and renormalize the remaining NeutralSkill horizon weights. With fewer than two valid NeutralSkill horizons, the player is `UNSCORED`. Missing values are never represented as legitimate numeric zero.

**SG Similar Composite:**
```
SG_Sim_Comp = SG_Base_Comp + Delta_Fit_Comp
```

---

## 7. CANONICAL DECOMPOSED DUAL-VECTOR FORMULA

### 7.1 Formula metadata

```text
formula_id: venuedna_dual_vector_decomposed
formula_version: 2.0.0
comparable_score_family: dual_vector_sg_per_round_v2
penalty_gate_set_id: venuedna_v2_none
```

### 7.2 Canonical core formula

```text
NeutralSkillRaw = SG_Base_Comp
VenueFitDeltaRaw = Delta_Fit_Comp
VenueHistoryDeltaRaw = 0.0 until a separately approved bounded transform exists

PrePenaltyRaw =
    NeutralSkillRaw
  + VenueFitDeltaRaw
  + VenueHistoryDeltaRaw
```

`PrePenaltyRaw` is the canonical latent score before separately authorized penalties and gates. It is not exposed directly.

### 7.3 Penalty, gate, and normalization sequence

```text
PrePenaltyRaw =
    NeutralSkillRaw
  + VenueFitDeltaRaw
  + VenueHistoryDeltaRaw

PostPenaltyRaw =
    result after applying authorized explicit penalties to PrePenaltyRaw

PostGateRaw =
    result after applying authorized gates to PostPenaltyRaw

VenueDNA_final_projection =
    approved within-event normalization of PostGateRaw
```

Formula v2.0.0 currently declares `penalty_gate_set_id: venuedna_v2_none`; `PostPenaltyRaw` and `PostGateRaw` are therefore identity transformations. A future formula version may activate a penalty or gate set only after the applicable evidence threshold, Model Council approval, and separate operator authorization; it must then declare its versioned `penalty_gate_set_id` and penalty/gate application order. Penalties and gates do not alter the definitions of NeutralSkillRaw, VenueFitDeltaRaw, or VenueHistoryDeltaRaw. This doctrine does not assert that archived historical 3M artifacts implement this sequence.

### 7.4 Component authority

| Field or source | Formula v2.0.0 authority | Direct core addend? |
|---|---|---|
| `SG_Base_Comp` | NeutralSkillRaw | Yes |
| `Delta_Fit_Comp` | VenueFitDeltaRaw | Yes |
| Venue history | VenueHistoryDeltaRaw = `0.0` pending bounded transform approval | Yes, at `0.0` only |
| `trait_approach_raw` | Structural evidence | No |
| `trait_long_iron_raw` | Candidate future VenueFitDelta input | No |
| `ott_true` | Venue-specific penalty/gate input | No |
| `ch_adjustment` | Future VenueHistoryDelta input | No |
| `true_sg_l20` | NeutralSkill/confidence/narrative context | No |

The five named production addends are visible diagnostic evidence in the legacy producer, not authorized formula v2.0.0 core inputs.

### 7.5 Missing-data behavior

- Missing values must not be represented as legitimate numeric zero.
- With two valid NeutralSkill horizons, omit the missing horizon and renormalize within NeutralSkill; with fewer than two, the player is `UNSCORED`.
- A valid similar-course row with zero rounds is `DEBUT`, produces `VenueFitDeltaRaw = 0.0`, and has `THIN` venue-fit confidence.
- VenueFitDelta has a fixed three-horizon formula. Incomplete VenueFit evidence is non-computable and is not weight-renormalized.
- Missing raw venue-history data remains missing and produces `THIN` venue-history confidence; the canonical `VenueHistoryDeltaRaw = 0.0` is an explicit neutral contribution pending an approved bounded transform, not conversion of raw-source missingness into observed zero data.
- Venue-history confidence is `THIN` below eight relevant starts or when that structured evidence is absent; the neutral-zero contribution is not high-confidence evidence.
- Missing optional trait data does not redistribute weight into other layers.
- Missing mandatory gate evidence produces an `UNKNOWN` gate evaluation.

### 7.6 Confidence decomposition

Confidence is separately represented for `neutral_skill`, `venue_fit`, `venue_history`, `penalty_gate`, `data_completeness`, and `conditions`. Confidence is neither a generic collapsed label nor an unapproved raw-score addend.

### 7.7 Production implementation divergence

`engine/enrich_cards.py` is the canonical v2.0.0 reusable root producer. Its official raw score, normalization, rank, tier, and probability vectors derive from canonical `PostGateRaw`. Historical 3M formulas remain diagnostic-only in explicitly historical helpers and archived parity records; the five legacy noncore addends and historical 3M gates do not affect official output.

Wyndham initialization remains blocked. No event, artifact, payload, database, deploy, or Wyndham migration occurred in this Phase 3 work. Historical artifacts remain historical and are not relabeled as v2-conforming.

### 7.8 Cross-event comparability and historical records

`VenueDNA_final_projection` is field-normalized and directly comparable only within an event. The cross-event comparable family is `dual_vector_sg_per_round_v2`, not field-normalized VTS. Archived 3M enriched and Open v3 artifacts remain valid historical event records but are not cross-event VTS benchmarks.

### 7.9 Reusable root-producer implementation status (2026-08-04 addendum)

A pure, I/O-free implementation of formula v2.0.0 exists at `engine/venuedna_scoring.py`. It computes `NeutralSkillRaw`, `VenueFitDeltaRaw`, `VenueHistoryDeltaRaw`, the §7.5 missing-data and `UNSCORED`/`DEBUT` rules, the §7.6 decomposed confidence bands, and the §8-§11 normalization, probability, and tier math, independent of any event, venue, or the historical 3M pathway. It has no dependency on `engine/enrich_cards.py` or `engine/identity_resolver.py` and performs no file, event, deploy, or database I/O.

The producer calls this implementation for each resolved player. Official score, rank, tier, and probability vectors derive from its `PostGateRaw`; the producer emits the canonical decomposition, decomposed confidence, scoring status, `formula_id`, `formula_version`, `scoring_spec_version`, `comparable_score_family`, `penalty_gate_set_id`, `penalties_applied`, and `gates_applied`. Under `venuedna_v2_none`, the last two values are known empty arrays, not missing configuration. `UNSCORED` is a status: its official score, rank, tier, and probabilities are null and excluded from scored-field pools.

This is a producer implementation alignment to existing canonical contracts, not a new artifact-schema or data-contract version migration. Prospective root-producer payload semantics now carry canonical v2 metadata and decomposition; no previously generated or archived payload was rewritten. Future event output must carry this canonical v2 metadata and decomposition. No event, deploy, database, archived-artifact, active-event, canonical-schema-file, or Wyndham migration occurred; historical 3M helpers and records remain diagnostic or archival context only.

---

## 8. Z-SCORE SCALING

In a formula-v2.0.0-conforming producer, applied independently to `PostGateRaw` and `SG_Base_Comp` to produce the two display scores:

```
VenueDNA_final_projection = z_score_scale(all PostGateRaw values)
neutralSkillIndex = z_score_scale(all SG_Base_Comp values)
```

Z-score formula:
```python
def z_score_scale(values, mean=50.0, std=15.0):
    if not values: return []
    mu  = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    sd  = sqrt(var) if var > 0 else 1.0
    return [max(0.0, min(100.0, mean + std * (v - mu) / sd)) for v in values]
```

Output range: [0, 100], hard-clamped. Mean of the field maps to exactly 50.0.

`VenueDNA_final_projection` is field-normalized and directly comparable only within its event. A conforming UI may display it as VTS; it is the official ranking signal for `VenueDNA_rank` (descending sort). The cross-event comparable family is `dual_vector_sg_per_round_v2`, not this normalized display score.

---

## 9. PROBABILITY VECTORS — TEMPERED SOFTMAX

In a conforming producer, four independent probability vectors are computed over the full field using `PostGateRaw` scores:

| Output     | Temperature T | N_positions |
|------------|--------------|-------------|
| winPct     | 3.5          | 1           |
| top5Pct    | 5.0          | 5           |
| top10Pct   | 7.0          | 10          |
| top20Pct   | 10.0         | 20          |

Formula (applied per output):
```python
def tempered_softmax(scores, T, n_positions):
    max_s = max(scores)                              # numerical stability
    exps  = [exp((s - max_s) / T) for s in scores]
    total = sum(exps)
    return [min(99.9, (e / total) * n_positions * 100) for e in exps]
```

Each player receives an independent percentage. Field sum ≈ n_positions × 100%.
Hard cap: 99.9 per player per outcome.

Monotonicity is enforced after softmax:
```python
def enforce_monotonicity(p):
    p["top5Pct"]  = max(p["top5Pct"],  p["winPct"])
    p["top10Pct"] = max(p["top10Pct"], p["top5Pct"])
    p["top20Pct"] = max(p["top20Pct"], p["top10Pct"])
```

---

## 10. CUT PROBABILITY

```
makeCutPct = min(98.0, max(20.0, top20Pct × 1.25 + 10.0))
missCutPct = 100.0 - makeCutPct
```

---

## 11. TIER ASSIGNMENT

Based on `VenueDNA_rank` (ascending rank from vts_final sort):

```
T1: ranks 1–5
T2: ranks 6–12
T3: ranks 13–25
T4: ranks 26–40
T5: ranks 41+
```

---

## 12. DATA DEPTH FLAG

`DEBUT` is valid only when a similar-course source row exists and reports zero rounds. It produces `VenueFitDeltaRaw = 0.0` and `THIN` venue-fit confidence. A missing source row is missing data, not `DEBUT`, and may require `UNSCORED` status under §7.4. The legacy `data_depth` field is an implementation field and is not sufficient by itself to establish formula-v2.0.0 missing-data conformance.

---

## 13. BOARD EXPORT SCHEMA

The example below is the protected historical 3M export shape. It is not evidence that its archived producer conformed to formula v2.0.0. The root producer's prospective canonical-v2 field emission aligns implementation with the existing canonical contracts; it does not rewrite historical payloads or create an artifact-schema or data-contract version migration.

`deploy/data/board_export.json` envelope:
```json
{
  "schemaVersion": "3m-dual-vector-v1.0",
  "generatedAt":  "<ISO 8601 UTC timestamp>",
  "event":        "2026 3M Open",
  "venue":        "TPC Twin Cities",
  "players":      [ ... ]
}
```

Per-player object (canonical field order):
```json
{
  "rank":                 1,
  "player":               "Scheffler, Scottie",
  "tier":                 "T1",
  "vts_final":            87.4,
  "neutralSkillIndex":    85.1,
  "sg_base_composite":    2.824,
  "sg_similar_composite": 2.910,
  "delta_fit":            0.086,
  "data_depth":           "FULL",
  "winPct":               18.5,
  "top5Pct":              42.1,
  "top10Pct":             58.3,
  "top20Pct":             74.6,
  "makeCutPct":           92.0,
  "missCutPct":           8.0
}
```

All float fields: 1 decimal for vts_final/neutralSkillIndex/probabilities; 4 decimals for sg_* and delta_fit.

---

## 14. VENUEDNA vs. DG FIELD AUTHORITY

| VenueDNA Field                  | Drives          |
|---------------------------------|-----------------|
| vts_final / VenueDNA_final_projection | Official rank |
| VenueDNA_tier                   | Official tier   |
| VenueDNA_rank                   | Row ordering    |
| VenueDNA_neutral_skill          | NSI display     |
| delta_fit / VenueDNA_venue_fit_delta | Venue fit signal |

| DG Benchmark Field              | Role            |
|---------------------------------|-----------------|
| DG_finalprediction_benchmark    | Audit comparison |
| DG_baseline_benchmark           | Skill decomp    |
| DG_coursefittotaladj_benchmark  | Course fit audit |
| All other DG_* fields           | Read-only context |

DG fields must never be used to derive official ranks. If VenueDNA and DG disagree, VenueDNA wins. Disagreements should be logged in council findings.

---

## 15. VERIFICATION

For the reusable root producer, validate canonical-v2 behavior without creating an event artifact:

```
python -m pytest -q tests/test_enrich_cards.py
python -m pytest -q tests/test_venuedna_scoring.py
python tools/validate_scoring_doctrine.py --strict
```

The producer-level runtime tests must execute `engine/enrich_cards.py::main()` and prove canonical `PostGateRaw` feeds official score, rank, tier, and probability output. The static doctrine validator separately checks the approved structural dataflow and must not be treated as runtime proof. Historical diagnostics may be validated separately, but do not define official v2 output. Canonical output validation:
- Player count must match union of all 6 SG CSVs
- Rank 1 must have highest vts_final
- All top20Pct ≥ top10Pct ≥ top5Pct ≥ winPct
- All makeCutPct in [20.0, 98.0]
- All vts_final and neutralSkillIndex in [0.0, 100.0]

---

## 16. LIVE LAYER

Round-based diagnostics layered on top of the pre-tournament VTS board. The live layer is additive and read-only against §1–§15: it never recomputes or overwrites `vts_final`, `VenueDNA_rank`, or `VenueDNA_tier`. It produces overlay fields only, consumed by the live-round UX (see `standards/ux/claude-code/claude-code-prompt-04-live-round-layer.md`).

Live layer components:

- **Live SG splits** — per-round strokes-gained by category (Off-the-Tee, Approach, Around-the-Green, Putting), sourced from round scorecards.
- **Shrinkage projections** — forward-looking forecast blending pre-event `vts_final` with in-tournament live SG, using `w_live = n / (n + 8)` where `n` is completed rounds.
- **Structurally_live eligibility** — the `diagnostic_label: "structurally_live"` gate marking players whose shrinkage-projected finish keeps them within mathematical range of contention. This is an eligibility gate, not a conviction ranking (see §18).
- **Rocket-derived live-badge research** — the `CeilingIndex`, `LiveConvictionScore`, Alpha/Beta/Gamma, and `T2RiskTag` concepts in §17–§18 are inactive hypotheses. They are not current live outputs and do not alter formula-v2 scores, confidence, tiers, probabilities, badges, or ranks.

---

## 17. ROCKET CLASSIC 2026 INACTIVE RESEARCH HYPOTHESES

**Status:** Inactive provisional hypotheses based on one Rocket Classic event. They preserve historical observations and may inform future bounded research, but they are not formula-v2.0.0 scoring rules. They do not alter `PrePenaltyRaw`, `PostPenaltyRaw`, `PostGateRaw`, confidence, tiers, probabilities, badges, or ranks; they activate no penalty or gate and do not override `penalty_gate_set_id: venuedna_v2_none`. Any implementation requires at least three relevant or sufficiently similar events by default (unless a higher governing standard applies), Model Council approval, explicit operator authorization, and an activated future formula, penalty/gate-set, or trait-submodel version.

### 17.1 CeilingIndex

**Historical research inputs:**
- Recent tee-to-green form (last-12 / last-24 SG splits).
- Volatility (round-to-round spread, L5 arrays).
- Venue scoring fit (par-5 scoring, wedge/approach windows, penalty structure).

**Potential future research outputs:**
- A future approved model may evaluate a `CeilingIndex` (0–100).
- A future approved model may evaluate a distinct ceiling display value; no `vtsceil` field or score effect is active under formula v2.0.0.

**Inactive status:**
- No current producer is directed to compute `CeilingIndex`, emit `vtsceil`, or assign a score, tier, probability, confidence, rank, or badge effect from this hypothesis.
- A future separately authorized live or trait-submodel version may evaluate the relationship between this evidence and live diagnostics; formula v2.0.0 has no such effect.

### 17.2 Badge Governance

**Historical research categories:**

| Category          | Badges                              |
|--------------------|--------------------------------------|
| Validated Support   | Iron Surgeon, Detroit Veteran        |
| Neutral              | Putter                               |
| Probation             | Hot Streak, Par-5 Predator, Bomber  |

**Inactive status:**
- A future approved trait-submodel may evaluate whether these labels provide structural evidence. No badge may contribute to `VenueFitDelta`, `VenueHistoryDelta`, or any other formula-v2.0.0 layer.
- No label may drive a current tier, probability, confidence, rank, score, penalty, or gate effect.
- Historical hit/miss observations may be retained for future multi-event evaluation; they do not authorize badge promotion, demotion, or implementation.

### 17.3 Approach Deficit hypothesis

- A future approved model may evaluate whether simultaneous long-window (last-24) and short-window (last-12) SG:APP weakness is useful evidence for an `ApproachDeficit` hypothesis.
- A future model may compare that hypothesis with a watchlist-only treatment when the short window is neutral or positive.
- No `ApproachDeficit` penalty, reduced weight, watchlist effect, live confirmation effect, or gate is active under formula v2.0.0.

### 17.4 Trait Concentration Cap

- If a future separately authorized direct-trait submodel is activated, its normalized direct-trait weights and maximum marginal contribution must observe the **0.50** cap; raw source measurements are not capped.
- Approach plus long iron remains a tightly coupled research pair for any such future submodel.
- No direct trait block, putting/ARG floor, or direct putting/ARG allocation is active under formula version 2.0.0; the pure dual-vector formula validly has zero direct allocation.
- A future venue-specific direct-trait submodel requires a documented rationale, expected outcome shape, multi-event validation, Model Council approval, explicit operator authorization, and an activated version before implementation.

### 17.5 T2RiskTag hypothesis

**Potential future research trigger:**
- Player is Tier 2 by `VenueDNA_rank`.
- No individual trait score exceeds a high threshold (e.g., 70 on the 0–100 trait scale).
- Player carries multiple narrative/probation badges (Bomber, Hot Streak, Veteran, etc.) without a standout structural trait.

**Inactive status:**
- A future approved study may test whether the trigger pattern has confidence or live-diagnostic value.
- No `T2RiskTag` confidence, probability, score, tier, rank, badge, penalty, or gate effect is active under formula v2.0.0.

---

## 18. INACTIVE ROCKET-DERIVED LIVE-BADGE HYPOTHESIS (ALPHA/BETA/GAMMA)

### LiveConvictionScore

**Potential future research inputs:**
- A future approved ceiling diagnostic (formerly described as `vtsceil`, §17.1).
- Live SG (Tee-to-Green, Approach, Putting).
- Current score vs. projected winning total.
- Tee-time / weather.
- Volatility index.
- Potential future penalty/gate research evidence, including anti-pattern flags or `T2RiskTag`.

**Potential future research output:** `LiveConvictionScore` — 0–100 per player only in a separately authorized future version.

### Potential future badge thresholds

| Badge       | Definition                                                                                                   |
|-------------|-----------------------------------------------------------------------------------------------------------------|
| Alpha Live  | Highest `LiveConvictionScore` cluster among `structurally_live` players; typically the top 3–5 names with a real win path. |
| Beta Live   | Credible contenders with at least one constraint (draw, ceiling, or trait gap).                                |
| Gamma Live  | Remaining `structurally_live` players with a mathematical but weak practical win path.                        |

### Inactive status

- `structurally_live` remains an eligibility concept, but formula v2.0.0 does not activate `LiveConvictionScore` or Alpha/Beta/Gamma scoring.
- No current live badge, promotion, downgrade, or `T2RiskTag` restriction is authorized; none may rewrite or supplement pre-event score, confidence, tier, probability, rank, penalty, or gate behavior.
- These retained threshold descriptions are historical research material only and require the §17 status conditions before any future implementation.
