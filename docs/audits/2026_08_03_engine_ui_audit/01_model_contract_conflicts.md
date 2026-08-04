# Model and Contract Conflicts

## Implemented scoring pathways

| Path | Implemented VTS formula | Assessment |
|---|---|---|
| Root-level, event-hardcoded 3M Open enrichment pathway: `engine/enrich_cards.py` | `zscore(sg_sim_comp + 0.40*approach + 0.25*long_iron + 0.20*OTT + 0.10*course_history + 0.05*form)`, with multiplicative gates applied afterward and field z-score scaling following (`:288-293`, `:705-728`, `:788-800`) | Its root location does not make its event-specific constants and filenames canonical across events. The additional trait/history/form addends also mean its VTS is not scoring-spec §7’s `SG_Sim_Comp` alone. |
| Open v3 | `.40*NSI + .30*VFS + .15*VHN + .15*form` (`score_open_2026_v3.py:470-475`) | Independent, event-hard-coded formulation; conflicts with canonical VTS definition. |
| Live `build_round_analysis.py` | preserves pre-event VTS and makes z-score/softmax live overlays (`:1761-1862`) | Intended additive overlay; inspect producer-path parity before relying on it cross-event. |

## Findings

| Severity | Evidence / current behavior | Governing rule | Impact | Smallest safe resolution | Required test |
|---|---|---|---|---|---|
| Critical | Open v3 VTS formula above replaces canonical raw-similar-SG formula. | Scoring spec §7–§8. | Official rank meaning differs by event. | Mark Open v3 historical/experimental; create a separately approved canonical adapter. | Golden-event rank/decomposition parity. |
| Critical | Open VFS adds `dg_cfa*1.5` (`score_open_2026_v3.py:408-416`). | Scoring spec §15; architecture §1: DG benchmark only. | Derivative/DG influence can change official ranking. | Remove only through approved scoring-doctrine task; meanwhile disclose noncanonical path. | Assert DG perturbation does not alter canonical ranks. |
| High | The root-level, event-hardcoded 3M pathway weights are `0.40/0.25/0.20/0.10/0.05` (`enrich_cards.py:705-728`); the tightly coupled approach-plus-long-iron pair totals 0.65. | Scoring spec §17 has a hard maximum of 0.50 for a coupled trait pair absent an explicit documented venue override. No qualifying override was established by this audit. | Confirmed doctrine conflict; trait concentration can overstate one structural signal. | Formally reconcile doctrine/configuration and add a correlation report; no weight change is authorized by this documentation task. | Coupled-weight cap and correlation test. |
| High | The root-level, event-hardcoded 3M pathway has no putting or ARG addend; they are display traits and gate input only (`:677-728`, `:881-897`). | Spec §17 minimum short-game+putting 0.20–0.25 in birdie-race contexts. | May violate venue-specific minimum where applicable. | Encode venue-context rule and report required/actual share. | Contextual weight-floor test. |
| High | The root-level, event-hardcoded 3M pathway similarity regression is `min(1, rounds/20)` and horizon decays `.20/.30/.50` base, `.50/.30/.20` delta (`:299-316`). | Spec §5–§6. | This portion aligns, but has no explicit time-decay metadata in payload. | Emit component and horizon provenance. | Hand-calculated composite fixture. |
| Medium | Open uses links windows `.35/.35/.20/.10` and a four-event confidence table (`score_open_2026_v3.py:123-204`), not the canonical three-horizon model. | Scoring spec §5–§6. | Cross-event comparisons cannot be treated as identical. | Version the model pathway and block mixed-event leaderboard comparison. | Schema discriminator test. |
| Medium | Venue history: shared course-history adjustment has debut haircut; Open shrinks 1/2 events (`score_open_2026_v3.py:230-265`). | Spec and CodeX schema require thin-confidence explanation. | Inconsistent sample gates. | Centralize sample-depth policy without altering scores first. | 0/1/2/8-start boundary tests. |
| Medium | Anti-patterns shared: inaccurate bomber/short-game reliance gates (`enrich_cards.py:339-359`); Open has its own flags. | Spec §17 and Council rules. | No cross-event semantics. | Canonical flag registry with event extension namespace. | Registry/schema contract test. |
| Medium | Ceiling fields diverge: shared emits `vts_ceil`; doctrine calls `CeilingIndex` and `vtsceil`; Open emits `win_ceiling_score`. | Scoring spec §17.1. | Board users cannot compare ceiling semantics. | Define one explicit ceiling sidecar contract; retain aliases only during migration. | Ceiling semantic/0–100 test. |
| High | Missing data is zero-filled (`enrich_cards.py:677-680`) and all zeros excluded from normalization (`:362-368`). | Data contracts §missing-numeric policy; scoring confidence doctrine. | Biases scores and hides missingness. | Component availability flags + confidence decomposition. | Missingness does not alter unrelated-field distribution. |

## Required/optional field-boundary ambiguity

Required artifact fields follow the artifact schema and use `"unknown"` where that schema prescribes it. Optional JSON scalar fields use `null` under the general data contract. A versioned schema must designate each field as required or optional, and existing consumers must migrate together. Do not silently coerce field types.

`standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md:283-293` requires required unknowns as string `"unknown"`; `docs/data_contracts.md:306-324` requires unavailable optional scalars as `null` and no text sentinels in numeric fields. The artifact schema governs artifact doctrine (per AGENTS precedence), so its current rule governs where it applies. Repository payloads use numbers, missing strings, and absent fields. Smallest safe resolution: designate required-versus-optional fields in one versioned JSON schema and migrate consumers together; do not silently coerce.
