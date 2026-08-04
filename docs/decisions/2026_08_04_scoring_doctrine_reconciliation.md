# Scoring Doctrine Reconciliation — 2026-08-04

## Decision

VenueDNA adopts the decomposed dual-vector formula family below as the canonical target doctrine. This is a doctrine decision only: it does not authorize production implementation or a reusable-engine migration, and it does not change production arithmetic in this task. A later migration requires separate operator authorization after this doctrine package is committed and a migration task is explicitly scoped.

## Context

The root `engine/enrich_cards.py` producer is an event-hardcoded 3M implementation whose raw score combines `SG_Sim_Comp` with five additional weighted addends. The score-decomposition audit established exact parity for that historical behavior and identified it as nonconforming to the intended decomposed doctrine. The active-event manifest is `NO_ACTIVE_EVENT`; no event, deploy, archive, or data artifact is in scope.

## Authorities reviewed

- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `docs/audits/2026_08_03_engine_ui_audit/07_score_decomposition_parity.md`
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `engine/scoring_decomposition.py`
- `engine/enrich_cards.py`
- `tests/test_scoring_decomposition.py`

## Exact formula

```text
NeutralSkillRaw = SG_Base_Comp
VenueFitDeltaRaw = Delta_Fit_Comp
VenueHistoryDeltaRaw = 0.0 until a separately approved bounded transform exists

PrePenaltyRaw =
    NeutralSkillRaw
  + VenueFitDeltaRaw
  + VenueHistoryDeltaRaw
```

## Score-layer sequence

```text
PrePenaltyRaw =
    NeutralSkillRaw
  + VenueFitDeltaRaw
  + VenueHistoryDeltaRaw

PostPenaltyRaw = result after applying authorized explicit penalties to PrePenaltyRaw
PostGateRaw = result after applying authorized gates to PostPenaltyRaw
VenueDNA_final_projection = approved within-event normalization of PostGateRaw
```

Formula v2.0.0 currently declares `penalty_gate_set_id: venuedna_v2_none`; its post-penalty and post-gate layers are identity transformations. This is the canonical identity penalty/gate set, not the historical production configuration. A future formula version may activate a set only after the applicable evidence threshold, Model Council approval, and separate operator authorization; it must declare its versioned identifier and penalty/gate order. These layers do not redefine NeutralSkillRaw, VenueFitDeltaRaw, or assert current 3M production conformance.

## Formula/version metadata

```text
formula_id: venuedna_dual_vector_decomposed
formula_version: 2.0.0
comparable_score_family: dual_vector_sg_per_round_v2
penalty_gate_set_id: venuedna_v2_none
```

## Component authority

| Current production field | Formula v2.0.0 authority | Treatment in v2.0.0 |
|---|---|---|
| `SG_Base_Comp` | NeutralSkillRaw | Authorized core input |
| `Delta_Fit_Comp` | VenueFitDeltaRaw | Authorized core input |
| Venue history | VenueHistoryDeltaRaw | `0.0` until an approved bounded transform exists |
| `trait_approach_raw` | Structural evidence | Not a direct core addend |
| `trait_long_iron_raw` | Candidate future VenueFitDelta input | Not a direct core addend |
| `ott_true` | Venue-specific penalty/gate input | Not a direct core addend |
| `ch_adjustment` | Future VenueHistoryDelta input | Not a direct core addend |
| `true_sg_l20` | NeutralSkill/confidence/narrative context | Not a direct core addend |

## Production divergence

`engine/enrich_cards.py` remains a historical divergent 3M-specific implementation. Its current inline gate behavior is separate historical behavior, not `venuedna_v2_none`. Its current arithmetic, scores, ranks, tiers, probabilities, gates, artifacts, deploy behavior, and historical records are unchanged by this decision. Formula v2.0.0 is the canonical target doctrine for a possible later reusable-engine migration; this decision does not authorize that migration.

Diagnostic metadata now records, without changing arithmetic, the canonical v2 core-input set, the five legacy noncore addends, and structured production-divergence reason codes. The current producer has a different formula identity, adds the five legacy components, does not expose the canonical three-layer formula, is 3M-specific, and has not migrated to v2.0.0.

The hardcoded 3M behavior is:

```text
not a doctrine blocker
a Wyndham initialization blocker
an implementation blocker after doctrine approval
```

## Trait concentration rules

- Apply the `0.50` cap to normalized direct-trait-submodel weights and maximum marginal contribution to the final latent score, never to raw source measurements.
- Approach plus long iron is a tightly coupled pair.
- A direct trait block is not active in formula version `2.0.0`.
- The birdie-race putting plus ARG floor applies only when a direct trait-weight submodel is active.
- Zero direct putting/ARG allocation is valid under the pure dual-vector formula.

## Missing-source behavior

- Genuine numeric zero is valid observed data; `null`, `none`, empty, absent, unparseable, or unavailable source values remain missing and are not silently converted to observed numeric zero.
- With two valid NeutralSkill horizons, omit the missing horizon and renormalize within NeutralSkill.
- With fewer than two valid NeutralSkill horizons, the player is `UNSCORED`.
- A valid similar-course row with zero rounds is the legitimate `DEBUT` state: `VenueFitDeltaRaw = 0.0` with `THIN` confidence.
- Missing raw venue-history data remains missing with `THIN` venue-history confidence; the canonical neutral `VenueHistoryDeltaRaw = 0.0` is not raw-source zero filling and is not an automatic negative score.
- Missing optional trait data does not redistribute weight into other layers.
- Missing mandatory gate evidence yields an `UNKNOWN` gate evaluation.

## Confidence decomposition

Confidence remains separately represented for `neutral_skill`, `venue_fit`, `venue_history`, `penalty_gate`, `data_completeness`, and `conditions`. It is not collapsed into a generic confidence value and is not an unauthorized raw-score addend.

## Cross-event comparability

`VenueDNA_final_projection` remains field-normalized and is directly comparable only within an event. Its cross-event comparable score family is `dual_vector_sg_per_round_v2`, not field-normalized VTS.

## Historical handling

Archived 3M enriched and Open v3 artifacts remain valid historical event records. They are not cross-event VTS benchmarks and must not be rewritten to imply formula v2.0.0 conformance.

## Rocket-derived evidence

Rocket Classic one-event observations are inactive provisional hypotheses only. They may support venue-specific hypotheses, audit flags, or bounded research, but cannot create permanent global scoring, schema, gate, or doctrine rules; they do not override formula v2.0.0. No direct trait, penalty, gate, badge, `CeilingIndex`, `ApproachDeficit`, or `T2RiskTag` score effect is active under v2.0.0. A global change requires the applicable multi-event threshold (at least three relevant or sufficiently similar events by default unless a higher governing standard applies), Model Council approval, explicit operator authorization, and an activated future formula, penalty/gate-set, or trait-submodel version.

## Wyndham prerequisites

Do not initialize Wyndham from the hardcoded 3M producer. Wyndham initialization remains blocked. Only a separately authorized migration task may implement formula v2.0.0 in a reusable root producer; it must preserve the declared missing-data and confidence behavior and validate score, rank, tier, probability, gate, artifact, deploy, and event-state effects before any event initialization.

## Deferred issues

1. Implement a bounded VenueHistoryDelta transform with separate approval and evidence threshold.
2. Define and validate any direct trait-weight submodel, including its normalized cap and birdie-race putting/ARG floor.
3. Migrate the root producer from its 3M-specific arithmetic to formula v2.0.0.
4. Add approved confidence metadata to payloads and artifacts without conflating it with raw score.
5. Establish cross-event validation on the comparable SG-per-round family rather than field-normalized VTS.

## Council findings

The five unresolved audit findings remain recorded as distinct implementation and validation work: formula reconciliation, coupled-trait concentration, putting/ARG treatment, reusable-engine migration, and source-confidence representation. This decision resolves their doctrine direction only; it does not authorize arithmetic, artifact, payload, deploy, archive, or event changes.

## Approval status

Formula v2.0.0 is approved as canonical target doctrine only. No event, artifact, payload, database, deploy, scoring, or reusable-engine migration is authorized by this package. Operator approval for a separately scoped subsequent engine migration is **pending**.
