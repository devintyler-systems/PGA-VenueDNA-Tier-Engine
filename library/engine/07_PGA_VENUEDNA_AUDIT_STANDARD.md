# PGA VenueDNA Tier Engine — Audit Standard
Version 1.1 — June 2026
Purpose: Canonical post-event review template and miss-classification standard for the single Perplexity-native PGA VenueDNA system.

## 1. Audit role
The audit is mandatory after every modeled event.

Its purpose is not to defend the projection or rewrite history. Its purpose is to determine:
1. what the engine got right
2. what the engine got wrong
3. why each major miss happened
4. whether the miss belongs to venue intelligence, engine rules, weekly execution, or variance
5. what explicit write-back, if any, should occur

The audit is the compounding mechanism of the system. Without it, the model is only a one-week opinion generator.

## 2. Inputs required
A complete audit should use the following inputs whenever available:
- locked venue intelligence file used pre-event
- scoring spec version used pre-event
- learning-loop version used pre-event
- event workflow version used pre-event
- event context JSON
- field input CSV
- trait/form matrix CSV
- full scored field CSV
- Tier 1 and Tier 2 player briefs
- risk register
- Round 1 diagnostic files if generated
- official final leaderboard and cutline
- final SG splits or closest verified outcome proxy
- prior audit notes for the same venue, if any

If any required input is missing, state the gap before reaching conclusions.

## 3. Audit outputs
Every audit should produce:
- a human-readable audit log markdown file
- a structured audit write-back JSON
- miss-ledger rows for append to the global ledger
- a venue update decision: `update`, `hold`, or `insufficient_evidence`
- an engine-rule update decision: `promote`, `track`, `hold`, or `reject`

## 4. Event context lock
Before evaluating misses, restate the event context used by the model.

Minimum lock fields:
- event_name
- season_year
- venue_name
- venue_code
- venue_file_version
- event_class
- course_par
- course_yardage
- surface
- field_size
- cut_rule
- weather_forecast_class
- expected_scoring_band
- variance_expectation
- fairway_width_class
- rough_severity_class
- firmness_class
- green_speed_policy
- rollout_class
- long_iron_frequency_class
- difficulty_class
- notable setup notes realized during the event

Audit rule:
- if the realized setup materially differed from the pre-event setup lock, classify part of the miss as execution or setup-read error before changing venue intelligence.

## 5. Primary audit questions
Every audit must answer these in order:
1. Did the venue trait model identify the right winning profile?
2. Did Tier 1 and Tier 2 contain the real contenders often enough?
3. Did anti-patterns fire in the correct direction?
4. Were anti-pattern magnitudes sized correctly for the realized setup?
5. Did named risks identify the right failure mechanisms?
6. Did named risks translate into enough quantitative consequence?
7. Did the probability layer calibrate correctly by tier?
8. Did the live diagnostic, if used, react correctly?
9. What should be written back to venue intelligence?
10. What should be tracked as a possible cross-venue engine rule?

## 6. Accountability review
### 6.1 Tier review
Evaluate at minimum:
- Tier 1 Top-10 rate vs predicted Top-10 average
- Tier 1 win conversion
- Tier 2 Top-20 rate vs predicted Top-20 average
- Tier 2 cut-make rate vs predicted make-cut average
- Tier 3 overperformance rate
- Tier 4 and Tier 5 survival rate vs predicted make-cut average

Do not judge only by winner location. Tier shape matters more than winner hindsight.

### 6.2 Player-level accountability
At minimum, review all Tier 1 and Tier 2 players plus any player who:
- won or finished runner-up from Tier 3 to Tier 5
- missed the cut from Tier 1
- produced a severe probability miss
- triggered a major anti-pattern or risk-linked miss

For each key player, compare:
- projected tier
- pre-penalty VTS
- final VTS
- active penalties and gates
- projected probabilities
- actual finish outcome
- primary miss category
- secondary miss category if needed

## 7. Anti-pattern review
### 7.1 Directional review
Test whether each active anti-pattern remained directionally correct:
- flagged-player Top-10 rate
- flagged-player Top-20 rate
- flagged-player make-cut rate
- flagged vs unflagged comparison
- field-baseline comparison

A directionally correct anti-pattern can still have incorrect magnitude.

### 7.2 Magnitude review
For every anti-pattern that materially affected tier placement, check:
- base penalty used
- setup modifier used
- weather modifier used
- confidence modifier used
- total applied penalty
- whether the event context justified that modifier level

This is mandatory when either of the following happened:
- a flagged player won or contended from a demoted tier
- multiple top finishers shared the same anti-pattern flag

### 7.3 Setup-modifier audit
This is now a required section.

For each major anti-pattern, explicitly state:
- whether fairway width, rough severity, firmness, rollout, runoff behavior, or green-speed policy should have changed the magnitude
- whether the pre-event setup modifier was correct, too weak, too strong, or missing
- whether the miss belongs to the venue file or to weekly execution of the venue file

Do not collapse a setup-modifier miss into a generic anti-pattern failure if the underlying anti-pattern concept still held.

## 8. Named risk-linkage review
### 8.1 Mechanism review
For Tier 1 and Tier 2 misses, assess whether the named risk register correctly identified the failure mechanism.

Examples:
- `APP_200_plus`
- `MajorGrind`
- `tight_runoff_scramble`
- `wind_ballflight`

### 8.2 Conversion review
This is now a required section.

When a named risk was correct in mechanism, test whether it also produced enough quantitative consequence.

For each major case, record:
- primary_risk_trait
- whether risk_stressor_active was true
- whether a secondary discount was applied
- whether that discount moved tier placement, Top-10 probability, make-cut probability, or conviction level enough to matter

Possible verdicts:
- `correct_mechanism_correct_conversion`
- `correct_mechanism_underconverted`
- `incorrect_mechanism`
- `mechanism_correct_but_no_action_authorized`

Do not promote a cross-venue engine rule from one event alone unless evidence is unusually strong and explicitly justified.

## 9. Probability calibration review
### 9.1 Required by-tier review
Audit at minimum:
- Tier 1 predicted vs actual Top-10 rate
- Tier 2 predicted vs actual Top-20 rate
- Tier 2 predicted vs actual make-cut rate
- Tier 4 predicted vs actual make-cut rate
- Tier 5 predicted vs actual make-cut rate

### 9.2 Variance-compression review
This is now a required section for any event labeled:
- `high`
- `high_wind`
- `mixed_uncertain`

Evaluate whether:
- win probabilities were appropriately compressed
- Top-10 probabilities were appropriately compressed
- Top-20 probabilities were appropriately compressed
- make-cut probabilities were appropriately compressed
- lower-tier survival odds were unrealistically crushed
- upper-tier certainty was overstated

Possible verdicts:
- `compression_correct`
- `compression_too_weak`
- `compression_too_strong`
- `wrong_variance_class`

If the variance class was right but tails were still implausible, classify the miss as `compression_too_weak`, not `wrong_variance_class`.

## 10. Debut, form, and health review
### 10.1 Debut review
Check whether debut penalties:
- fired consistently
- over-penalized legitimate comp specialists
- under-penalized unproven players
- affected tier placement correctly

### 10.2 Form-gate review
Check whether recent-form hard gates:
- were triggered with enough sample
- correctly separated structural poor form from harmless noise
- overruled venue fit too aggressively or too weakly

### 10.3 Health-gate review
Check whether health information:
- was missing
- was correctly applied
- should have changed tier publication

## 11. Live diagnostic review
If a Round 1 diagnostic was produced, evaluate:
- whether holds were correct
- whether downgrades were justified by structural evidence rather than one-round noise
- whether upgrades were based on venue-fit confirmation rather than putting variance
- whether live setup conditions softened or amplified pre-modeled anti-patterns

Possible verdicts:
- `live_process_good`
- `overreacted_to_noise`
- `underreacted_to_structural_shift`
- `incomplete_live_inputs`

## 12. Miss classification standard
Every significant miss must map to one primary category and optional secondary category.

Primary categories:
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

Secondary categories may include:
- setup-modifier miss
- risk-linkage underconversion
- probability-compression miss
- missing-data confidence miss
- live-diagnostic miss

If a miss cannot be classified, the trace outputs were insufficient and the artifact layer needs improvement.

## 13. Write-back decision framework
### 13.1 Venue write-back
Use `update` only when the evidence supports a venue-specific change in one of the following:
- trait-weight importance
- anti-pattern set
- anti-pattern magnitude
- anti-pattern setup modifier
- debut sensitivity
- local weather/setup interaction
- venue variance class

Use `hold` when:
- the venue concept still looks right
- the miss appears driven by variance or one-off execution noise
- evidence is too entangled to isolate confidently

Use `insufficient_evidence` when:
- inputs are missing
- the event sample cannot support a stable inference

### 13.2 Engine-rule flags
Use these statuses for cross-venue candidates:
- `promote`
- `track`
- `hold`
- `reject`

Promotion requires repeated evidence unless the event produced an unusually clean mechanism with strong transfer logic.

## 14. Audit file contract
### 14.1 Audit log markdown must include
- event context summary
- Tier 1 and Tier 2 accountability review
- anti-pattern review
- setup-modifier review
- named risk-linkage review
- probability calibration review
- debut/form/health review
- live diagnostic review if used
- significant miss log
- venue write-back recommendations
- engine-rule flags
- final verdict

### 14.2 Audit write-back JSON should include
- event_context
- venue_changes
- engine_rule_flags
- miss_ledger_rows
- confidence_updates
- follow_up_actions
- setup_modifier_review
- risk_linkage_review
- probability_calibration_review

### 14.3 Miss-ledger rows should include at minimum
- event_id
- venue_code
- player_name
- projected_tier
- actual_finish_bucket
- primary_miss_category
- secondary_miss_category
- key_trigger
- corrective_action_candidate
- confidence_level

## 15. Failure conditions
The audit fails if:
- it evaluates only the winner and ignores tier shape
- it changes venue rules without separating variance from structure
- it treats setup-conditional misses as generic anti-pattern failures
- it notes named risks but never evaluates conversion into score/probability impact
- it ignores probability calibration by tier
- it revises engine rules from one anecdote without evidence threshold
- it produces narrative conclusions without explicit write-back decisions

## 16. Operating standard
The audit layer must always prefer:
- explicit miss classification over vague hindsight
- venue-specific write-backs over generic reactions
- repeated evidence over anecdotal editing
- traceable changes over aesthetic prose
- calibration over self-justification

This file defines the canonical audit standard for the PGA VenueDNA Tier Engine.
