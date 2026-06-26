# PGA VenueDNA Tier Engine — Scoring Specification
Version 1.1 — June 2026
Purpose: Canonical scoring core for the single Perplexity-native PGA VenueDNA system.

## 1. System role
The PGA VenueDNA Tier Engine is a venue-specific PGA Tour projection system. It does not produce generic golf commentary, rankings summaries, or narrative consensus takes. Its job is to estimate which players are most likely to perform best at a specific venue, why they fit, where they are vulnerable, and how confident the system should be in that conclusion.

The scoring system exists to survive post-tournament audit. Every score, tier, probability, and flag must be decomposable into named inputs that can be checked against outcomes.

## 2. Core scoring principle
Every player projection must be built from five distinct layers in order:
1. NeutralSkill
2. VenueFitDelta
3. VenueHistoryDelta
4. Penalties and gates
5. Probability and tier mapping

Do not collapse these into one blended intuition score before logging the component values. The audit depends on preserving attribution.

## 3. NeutralSkill
NeutralSkill is the player’s expected adjusted strokes-gained per round on a neutral PGA Tour course before venue-specific effects are applied.

NeutralSkill must be estimated from pre-tournament information only and should reflect the strongest transferable signal of player ability.

### 3.1 Inputs
- DataGolf true strokes gained and equivalent long-term adjusted SG measures
- Recency-weighted round history
- Number of rounds in sample
- Days since last competitive round
- Tour-quality context for low-data players
- Category-level SG persistence where available

### 3.2 Estimation rules
- Use recency weighting, but do not use pure short-term form as baseline skill.
- Regress small-sample players harder toward field average.
- Treat low-data rookies, returnees, and partial-schedule players as wider-uncertainty profiles.
- Do not let venue-specific data contaminate NeutralSkill.
- Do not use world ranking directly as a scoring input.

### 3.3 Category persistence rule
When category-level SG data is available, baseline skill estimation must recognize that categories persist differently:
- OTT is most stable and can positively inform future APP and overall ball-striking.
- APP is highly predictive and travels well venue to venue.
- ARG is moderately predictive.
- PUTT is least stable and must be regressed hardest toward mean.

Short-term performance driven mostly by putting should receive less carry-forward weight than the same short-term performance driven by OTT or APP.

### 3.4 NeutralSkill output
Store all of the following for every player:
- neutral_skill_sg
- neutral_skill_index
- data_depth_class
- baseline_confidence_band

`neutral_skill_index` is the field-relative normalized baseline score used downstream in VTS blending.

## 4. VenueFitDelta
VenueFitDelta is the course-specific performance adjustment relative to NeutralSkill. It answers one question: how much does this specific venue help or hurt this player versus a neutral course?

VenueFitDelta is derived from the active venue DNA file only. If the venue DNA file is not loaded or not locked, projection must stop until venue setup is complete.

### 4.1 Venue DNA requirements
Each venue file must define:
- surface type
- wind profile
- corridor tightness / driving penalty profile
- rough severity
- approach profile
- par-5 reachability and scoring pattern
- pressure-hole structure
- routing bias only when evidence exists
- structural comparability window
- excluded or partially comparable years
- trait-weight matrix summing to 100
- anti-pattern set
- anti-pattern magnitude modifier rules
- risk-stressor map when applicable
- debut-penalty framework
- comp-course list with similarity caps
- venue variance class

### 4.2 Trait weighting rules
VenueFitDelta must be built from weighted trait signals such as:
- SG:APP
- SG:OTT
- SG:PUTT on the specific surface
- SG:ARG
- SGT2G composite
- par-5 scoring
- pressure-hole scoring
- distance / accuracy profile when venue evidence supports it
- ball-flight fit when venue evidence supports it

Rules:
- Weights must sum to 100.
- Surface putting does not transfer cleanly across surfaces without explicit conversion or discount.
- Comp-course effects must be capped and named.
- If a trait’s venue relevance is weak or provisional, its confidence band must be recorded.
- If evidence is sparse, shrink the course-fit effect toward zero rather than forcing a strong conclusion.
- For extreme setups, the fit construction must distinguish generic SG:OTT from venue-specific driving demands such as corridor discipline, forced positional tee shots, or penalty-avoidance driving.

### 4.3 Fit construction
For each player:
- score the relevant traits against the venue weight matrix
- normalize to a field-relative venue fit score
- translate that to `venue_fit_delta`
- cap comp-course influence at the venue-file maximum
- store the reasoning trace

### 4.4 VenueFitDelta output
Store all of the following for every player:
- venue_fit_score
- venue_fit_delta
- venue_fit_confidence_band
- comp_course_adjustment
- comp_course_trace

## 5. VenueHistoryDelta
VenueHistoryDelta is the local-course adjustment on top of NeutralSkill and VenueFitDelta. It is not a substitute for either.

### 5.1 Usage thresholds
- 5 or more prior starts: venue history is active and can materially affect score.
- 3 to 4 prior starts: venue history is partial and must be blended conservatively.
- 1 to 2 prior starts: mention qualitatively only unless venue file defines a specific limited-sample rule.
- 0 starts: no venue history delta.

### 5.2 Construction rule
VenueHistoryDelta should compare a player’s historical SG at this venue to their NeutralSkill baseline rather than treating raw venue results as standalone evidence.

Good venue history must not be double-counted when it is already partly explained by obvious fit traits.

### 5.3 VenueHistoryDelta output
Store all of the following for every player:
- venue_history_rounds
- venue_history_sg
- venue_history_delta
- venue_history_confidence_band

## 6. Pre-penalty score
Before penalties and gates, every player receives a PrePenaltyVTS built from explicit blending of:
- neutral_skill_index
- venue_fit_delta
- venue_history_delta when active

### 6.1 Blending classes
Default structure:
- No or minimal venue history: baseline-led model
- Moderate venue history: blended model
- Deep venue history: balanced model with stronger local-course influence

Suggested default blending framework:
- 0 to 2 starts: NeutralSkill 60, VenueFitDelta 40
- 3 to 4 starts: NeutralSkill 50, VenueFitDelta 35, VenueHistoryDelta 15
- 5+ starts: NeutralSkill 40, VenueFitDelta 30, VenueHistoryDelta 30

These are defaults, not sacred constants. Venue files may override within bounded ranges, but every override must be documented and auditable.

### 6.2 Extreme-venue blend override
For venue files tagged as extreme, major-championship, or fit-dominant, tier eligibility may require a minimum VenueFitDelta threshold even when NeutralSkill is elite.

Rules:
- Tier 1 and Tier 2 eligibility may be blocked when VenueFitDelta falls below a venue-defined minimum threshold.
- This is a gating rule, not a hidden score nudge.
- The threshold and rationale must be stored in the venue file and visible in trace output.

### 6.3 Output
Store:
- pre_penalty_vts
- blend_class
- blend_weights_used
- tier_eligibility_gate_status

## 7. Penalties and gates
Apply modifiers only after PrePenaltyVTS is constructed.

### 7.1 Debut penalty
Debut penalty is venue-specific.

Required storage:
- debut_class
- debut_penalty_applied
- debut_reason

Rules:
- Do not reduce debut penalties just because the player is famous or highly ranked.
- Elite players without clean surface-specific evidence still carry an uncertainty penalty.
- Comp specialists can receive a reduced debut penalty only when the comp evidence is explicit and capped.
- Debut penalty changes require repeated evidence. One event does not override the standing framework.

### 7.2 Anti-pattern penalties
Anti-patterns are high-value fade logic. They must be:
- venue-specific
- historically evidenced
- named
- magnitude-defined
- setup-sensitive when appropriate
- weather-sensitive when appropriate

Required storage:
- anti_pattern_flags
- anti_pattern_penalty_total
- anti_pattern_trigger_trace
- anti_pattern_modifier_trace

Rules:
- Anti-patterns primarily suppress ceiling, not floor, unless venue file explicitly defines a floor-collapse condition.
- Soft-condition weeks can reduce certain anti-pattern penalties when the structural punishment is neutralized.
- Material setup changes can also reduce or reshape anti-pattern penalties even if the course remains difficult overall.
- Do not invent anti-patterns from one event or small noisy samples.
- Do not remove an anti-pattern because one elite player overcame it. First test whether setup conditions neutralized part of the penalty.

### 7.2.1 Anti-pattern magnitude modifier function
Anti-pattern magnitude is not always static.

When the venue file supplies setup modifiers, the applied anti-pattern penalty must be calculated as:

`applied_penalty = base_penalty × setup_modifier × weather_modifier × confidence_modifier`

Where applicable, setup modifiers may key off fields such as:
- fairway_width_class
- rough_severity_class
- green_speed_policy
- firmness_class
- rollout_class
- routing_bias_condition

Rules:
- Setup modifiers must be explicit, not intuitive.
- Setup modifiers may reduce or increase penalty magnitude within venue-defined bounds.
- Venue-specific modifier logic takes precedence over generic anti-pattern defaults.
- If multiple anti-patterns stack on the same player, log each component separately before summing.

Example venue rule:
- If `bomb_and_spray` is active and `fairway_width_class = wide` and `green_speed_policy = no_softening_for_wind`, reduce penalty magnitude by a bounded venue-defined percentage because the venue still punishes misses but offers more corridor tolerance than the historical baseline.

### 7.2.2 Anti-pattern tier caps
Venue files may define anti-pattern caps that limit maximum tier eligibility.

Rules:
- Some anti-patterns reduce ceiling only.
- Some anti-patterns may cap Tier 1 eligibility.
- Some anti-patterns may cap Tier 2 eligibility when paired with high-variance weather or severe setup.
- Tier caps must be explicit and logged, not hidden in narrative.

### 7.3 Recent form gates
Recent form affects confidence and finishing path, but must not overwrite venue logic blindly.

Cross-venue rules:
- quality multipliers apply before form weighting
- form window uses 35 / 25 / 10 / 10 / 10 / 10 weighting
- RF below 0 can trigger a hard penalty
- RF below a deeper threshold can force Tier 3 ceiling regardless of baseline skill

Required storage:
- form_score_adjusted
- recent_form_index
- recent_form_gate_applied

### 7.4 Health gate
Documented injury is a gate, not a soft narrative discount.

Rules:
- injured players cannot be treated as top-tier contention profiles until Round 1 clears without functional failure
- pre-tournament projection must show the gate explicitly
- live reactivation requires updated evidence

Required storage:
- health_flag
- health_gate_status
- health_gate_reason

### 7.5 Named risk-register linkage
The risk register is not commentary only. When a named structural risk is present and the week directly stresses that risk, the engine may apply a secondary quantitative adjustment after the base trait score is built.

Required storage:
- primary_risk_trait
- risk_stressor_active
- risk_secondary_discount_applied
- risk_discount_trace

Rules:
- The base trait model should identify the structural weakness first.
- The risk-register linkage exists to convert a correctly identified failure mechanism into enough score or probability movement to matter.
- Risk linkage may alter probability outputs, tier eligibility, or both.
- One-event evidence is sufficient for venue-specific note-taking, but cross-venue risk-linkage rules require repeated confirmation before becoming permanent engine constants.

### 7.5.1 Risk-stressor logic
Risk-stressor logic is triggered only when both of the following are true:
- a named primary risk trait is active for the player
- the event context or venue file indicates that the current week directly stresses that trait

Examples:
- `APP_200_plus` risk stressed by `weather_forecast_class = high_wind` and long-iron frequency above venue threshold
- `MajorGrind` risk stressed by `event_class = major` and `difficulty_class = high`
- `tight_runoff_scramble` risk stressed by firm short-grass runoff setup

### 7.5.2 Risk linkage actions
When stressor logic is active, the venue file or engine rule may authorize one or more of the following:
- direct VTS discount
- Tier 1 eligibility block
- Tier 2 eligibility block
- win_pct discount
- top10_pct discount
- make_cut_pct discount when the risk is floor-relevant

Probability discounts should be bounded and logged separately from anti-pattern penalties.

## 8. Variance layer
This engine must not operate as a pure point-estimate model.

### 8.1 Player variance
Each player should carry a volatility estimate derived from adjusted SG residual behavior, sample depth, and similar-player regression when data is sparse.

Store:
- player_variance_band
- volatility_index

### 8.2 Venue variance
Each venue file must include a venue variance class:
- low
- standard
- high

Rules:
- higher-variance venues compress win probabilities and reduce overconfidence in separation
- lower-variance venues justify stronger conviction in true structural fits
- variance class should influence probability mapping, anti-pattern magnitude, and portfolio diversification logic

Store:
- venue_variance_class
- variance_adjustment_trace

### 8.3 Probability compression by variance class
Variance compression must apply to more than win probability when the venue or weather class is extreme.

Rules:
- For `venue_variance_class = high` or `weather_forecast_class = high_wind`, compress player separation in `make_cut_pct`, `top10_pct`, and `top20_pct`, not just `win_pct`.
- Compression logic should reduce overconfidence in Tier 1 and Tier 2 while raising realistic survival odds for Tier 4 and Tier 5.
- Compression logic must be tier-aware or distribution-aware; it cannot simply subtract the same number from every player.
- If the week is labeled high-variance but tails still remain implausibly tight, the probability layer has failed even if rankings are directionally correct.

Store:
- probability_compression_class
- probability_compression_coefficients
- probability_compression_trace

## 9. Final VTS and tier mapping
After applying penalties, gates, and bounded variance adjustments, map to final VTS on a 0 to 100 scale.

Tier structure:
- Tier 1: 80+ — Course Architects
- Tier 2: 65–79 — Contention Windows
- Tier 3: 50–64 — Top-10 Range
- Tier 4: 35–49 — Cut-Line Players
- Tier 5: below 35 — Course Mismatches

Store:
- vts_final
- tier
- tier_reason

### 9.1 Tier eligibility precedence
Tier assignment must honor hard eligibility rules before final publication.

Precedence order:
1. Health gate
2. Venue-specific anti-pattern cap
3. VenueFit minimum threshold when defined
4. Debut cap when defined
5. Recent-form hard ceiling
6. Final VTS band

A player may have a Tier 1-caliber raw score and still publish as Tier 2 or Tier 3 if an eligibility gate is active.

## 10. Probability layer
Tier alone is not enough. Final output should include event-finish probabilities derived from score quality plus uncertainty.

Minimum outputs:
- win_pct
- top3_pct
- top5_pct
- top10_pct
- top20_pct
- make_cut_pct
- miss_cut_pct

Rules:
- do not derive these from tier only once the full model matures
- probability mapping should eventually consume NeutralSkill, VenueFitDelta, VenueHistoryDelta, variance, field strength, and named risk-linkage adjustments where triggered
- lineup optimization and betting derivatives are downstream consumers, not inputs to core projection
- the field-wide sum of win probabilities must remain normalized
- probability calibration must be audited separately from rank-order accuracy

## 11. Derivative layers are isolated
The following outputs may use model output, but they must never write back into the scoring core:
- DraftKings / fantasy lineup construction
- market edge tables
- ownership leverage logic
- contest-specific optimization
- betting card construction

These are derivative products. They do not influence core player projection weights, venue DNA, or audit conclusions.

## 12. Required player trace record
Every projected player row should eventually expose at least these fields:
- player_name
- neutral_skill_sg
- neutral_skill_index
- data_depth_class
- baseline_confidence_band
- venue_fit_score
- venue_fit_delta
- venue_fit_confidence_band
- comp_course_adjustment
- venue_history_rounds
- venue_history_sg
- venue_history_delta
- venue_history_confidence_band
- pre_penalty_vts
- blend_class
- blend_weights_used
- tier_eligibility_gate_status
- debut_class
- debut_penalty_applied
- anti_pattern_flags
- anti_pattern_penalty_total
- anti_pattern_modifier_trace
- primary_risk_trait
- risk_stressor_active
- risk_secondary_discount_applied
- form_score_adjusted
- recent_form_index
- recent_form_gate_applied
- health_flag
- health_gate_status
- player_variance_band
- volatility_index
- venue_variance_class
- probability_compression_class
- probability_compression_coefficients
- vts_final
- tier
- win_pct
- top5_pct
- top10_pct
- top20_pct
- make_cut_pct
- miss_cut_pct
- trace_notes

## 13. Failure conditions
The scoring output fails if any of the following are true:
- venue file is missing or unlocked
- VTS is produced without component separation
- surface-specific putting is transferred without rule or discount
- course history is used as standalone evidence instead of relative-to-baseline context
- form is flat-weighted
- anti-pattern penalties are unnamed or undocumented
- anti-pattern magnitude was clearly setup-conditional but no setup modifier was considered
- named primary risks are identified but cannot influence score or probability when directly stressed by conditions
- debut penalty is hand-waved away on reputation
- world rank is used directly as a projection variable
- derivative fantasy or betting logic modifies core projection
- output cannot be audited after results post

## 14. Audit linkage
Every significant miss must be attributable to one or more of these buckets:
- NeutralSkill miss
- VenueFit miss
- VenueHistory miss
- Debut penalty miss
- Anti-pattern miss
- Form scaling miss
- Health gate miss
- Variance miss
- Weather / setup miss
- Tier mapping miss

If a miss cannot be classified, the trace was not detailed enough.

## 15. Operating standard
The scoring engine must always prefer:
- explicit decomposition over blended intuition
- venue specificity over general reputation
- shrinkage over overfit certainty
- auditability over elegance
- learning loops over one-off takes

This file defines the canonical scoring logic for the single-system Perplexity Space implementation.
