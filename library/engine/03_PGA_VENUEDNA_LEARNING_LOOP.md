> **AUTHORITY: Reference only**
> **Canonical counterpart:** `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
> **Keep reason:** Contains the 16-section audit methodology, global miss ledger schema, and write-back split rules that predate and extend the standards round-cadence spec.
---

# PGA VenueDNA Tier Engine — Learning Loop Specification
Version 1.1 — June 2026
Purpose: Canonical learning, audit, and write-back logic for the single Perplexity-native PGA VenueDNA system.

## 1. System role
The learning loop is the compounding engine of the PGA VenueDNA Tier Engine. The weekly projection is the output. The audit is the product.

This system does not improve by storing prior takes. It improves by converting tournament outcomes into calibrated changes at the correct layer:
- venue layer
- engine layer
- player uncertainty layer
- probability layer

Every completed event must generate a structured audit and at least one explicit learning decision, even if the decision is to hold all current weights and rules.

## 2. Learning hierarchy
The system learns at four levels:
1. Event audit level
2. Venue file level
3. Cross-venue engine-rule level
4. Probability / variance calibration level

Do not patch a venue rule when the miss is clearly engine-wide. Do not rewrite an engine rule when the miss is isolated to one venue setup.

## 3. Mandatory audit trigger
An audit is mandatory after every completed tournament for which the system published projections.

Minimum trigger set:
- pre-tournament projections were produced
- a Round 1 live diagnostic was produced
- or a derivative output was published from model rankings

If the engine made a call, the engine owes a verdict.

## 4. Audit package inputs
Every post-event audit must consume:
- final leaderboard and player finishing positions
- cutline and scoring distribution
- weather / firmness / setup observations by round
- actual SG category leaders and top-finisher profiles where available
- the final pre-tournament player trace table
- all Round 1 and live updates made during the event
- anti-pattern flags issued
- debut penalties applied
- lineup / betting derivatives only for downstream review, never for core score calibration

## 5. Audit sequence
The audit must run in this order.

### Step 1 — Event context lock
Record:
- tournament
- venue
- date
- field strength notes
- weather summary by round
- setup summary
- winning score
- cutline
- venue variance conditions relative to expectation

This prevents false learning from setup changes that were not part of the original venue baseline.

### Step 2 — Projection accountability
For every Tier 1 and Tier 2 player, log:
- pre-tournament VTS
- tier
- key component scores
- final finishing position
- made / missed cut
- whether the player beat, met, or missed projection

Core accountability metrics:
- Tier 1 Top-10 rate
- Tier 1 win conversion rate
- Tier 2 Top-20 rate
- anti-pattern fade outside-Top-20 rate
- debut-penalty hit rate
- make-cut calibration by tier
- top-10 calibration by tier

### Step 3 — Significant miss log
Every player who materially outperformed or underperformed projection must enter the miss log.

Default miss threshold:
- 20+ finishing places from projected expectation band
- or 2+ tier difference versus outcome
- or any high-conviction anti-pattern / Tier 1 miss

Each miss must be assigned one primary category and optional secondary category.

Primary miss categories:
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
- Live diagnostic miss
- Data quality miss

If no category fits cleanly, the trace quality failed.

### Step 4 — Trait weight review
Review whether the venue trait matrix actually separated high finishers from the field.

For each weighted trait:
- compare projected importance to actual top-finisher profile
- record whether the trait was confirmed, neutral, or disconfirmed
- record strength of evidence

Adjustment rules:
- one noisy event is not enough for a major weight rewrite unless setup was extreme and clearly exposed a missing trait
- repeated confirmation strengthens confidence band before it increases weight
- repeated disconfirmation reduces either weight magnitude or confidence level
- underweighted traits can be promoted only with explicit evidence

### Step 5 — Anti-pattern review
For every anti-pattern flag:
- log player result
- log whether the anti-pattern held structurally, partially, or failed
- log whether weather or setup neutralized the structural penalty
- log whether penalty size was too soft, correct, or too harsh

Do not delete an anti-pattern because one elite player overcame it without explanation. Investigate whether the course played outside expected punishment conditions.

### Step 5A — Setup modifier review
When setup-conditional anti-pattern logic exists or should have existed, the audit must explicitly review:
- whether fairway width, rough, firmness, or green-speed policy changed the true punishment profile
- whether the anti-pattern concept was right but the magnitude was wrong
- whether the miss belongs in venue file setup modifiers rather than in the engine core

This step exists to prevent false anti-pattern deletions when the real issue was conditional sizing.

### Step 6 — Debut review
For all debut players:
- compare projected adjustment to actual result band
- review whether debut class was too steep, too soft, or correctly sized
- separate general debut success from comp-specialist success and elite-no-surface-data cases

Do not revise the venue debut penalty from one outlier alone. Revise only when the class error repeats or multiple debut players clear the same bar.

### Step 7 — Variance review
Review both player and venue variance behavior.

Questions:
- did high-volatility players realize wider-than-expected outcome spread?
- did the venue play as a high-variance or low-variance week relative to its stored class?
- did probabilities appear too concentrated or too flat?
- were make-cut and top-10 bands miscalibrated by tier even if win probability sum was normalized correctly?

If many players with similar VTS produced widely divergent finishes under expected conditions, check venue variance calibration before changing trait weights.

### Step 8 — Round 1 diagnostic review
If live updates were produced, audit them.

For every R1 downgrade, hold, or promotion:
- log original decision
- actual later result
- whether the trigger logic was correct
- whether the model overreacted or underreacted

This protects the engine from learning the wrong lesson from one live overcorrection.

### Step 9 — Risk-register conversion review
If named structural risks were issued pre-tournament, audit whether they had enough quantitative consequence.

Review:
- whether the named risk mechanism actually materialized
- whether it was already sufficiently expressed in trait scoring
- whether a direct risk-to-score or risk-to-probability linkage was missing
- whether the fix belongs at venue level or cross-venue engine-rule level

This step separates “good note, weak score impact” from true false positives.

### Step 10 — Write-back decision layer
Every audit must end with explicit write-back decisions at the correct layer.

Allowed write-back targets:
- venue trait weights
- venue confidence bands
- anti-pattern penalty ranges
- anti-pattern setup modifiers
- debut class / exact venue penalty
- comp-course similarity caps
- routing-bias confidence
- surface-conversion rules
- venue variance class
- cross-venue engine rules
- probability mapping rules

Every write-back must include:
- field changed
- old value
- new value
- evidence
- confidence of change
- next audit checkpoint

## 6. Venue file write-back rules
A venue file should be updated when the evidence is specific to that venue’s structure, repeatable setup, or recurring trait interaction.

Examples:
- APP weight too low at Colonial in repeated firm setups
- a pressure-hole trait matters more than originally priced at Muirfield
- debut penalty at Harbour Town is consistently too soft
- a comp course is repeatedly over-translating to Aronimink
- an anti-pattern penalty should be damped when fairway width materially expands at a specific US Open venue

Venue file updates must not be used to patch an engine-wide weakness like over-trusting short-term putting spikes.

## 7. Engine-rule write-back rules
A cross-venue engine rule should be updated only when the same miss pattern appears across multiple venues or multiple event types.

Examples of engine-rule candidates:
- single-event SG regression threshold
- RF hard-gate threshold
- debut penalty floor logic
- variance compression rule
- comp-course cap discipline
- putting regression treatment
- live-update downgrade threshold
- risk-register-to-probability linkage

Engine-rule updates require:
- at least two supporting event cases, preferably more
- explicit statement that the miss is not venue-local
- rollback condition if later evidence disconfirms the change

## 8. Global miss ledger
The system must maintain a cross-event miss ledger.

Each row should include:
- event_id
- venue
- player
- projection_tier
- actual_finish_band
- primary_miss_category
- secondary_miss_category
- miss_direction
- miss_magnitude
- structural_or_noise
- proposed_fix_layer
- action_taken
- follow_up_status

Purpose:
- detect repeated failure patterns
- prevent venue-by-venue patch drift
- identify where the engine is overconfident
- surface rule candidates for promotion to engine-level logic

## 9. Confidence management
The system should not only learn weights. It should learn confidence.

Three confidence objects must be updated over time:
- venue trait confidence
- anti-pattern confidence
- probability calibration confidence

If a trait remains plausible but inconsistent, lower its confidence before forcing a binary keep/remove decision.

## 10. Learning thresholds
Use bounded change rules.

Default thresholds:
- minor weight adjustment: 1 to 3 points
- moderate adjustment: 4 to 6 points
- major adjustment: 7+ points only with strong repeated evidence
- anti-pattern penalty resize: 1 to 2 VTS points unless extreme repeated miss exists
- debut penalty resize: 1 point unless class failure is obvious

The goal is stable compounding, not dramatic weekly oscillation.

## 11. No-overfit protections
The learning loop fails if it overreacts to noise.

Protections:
- one-event weather distortions do not rewrite core venue DNA without structural support
- one star player overcoming a bad fit does not erase the anti-pattern
- putting-heavy outlier wins do not automatically justify raising PUTT weight
- unusual cutline behavior does not redefine venue variance alone
- derivative betting or DFS results never override core audit evidence
- one-event debut success does not trigger framework softening unless the class failure is broad and repeated

When uncertain, reduce confidence or note provisional status instead of forcing a hard rewrite.

## 12. Probability calibration review
Projection quality is not just rank ordering. Probability calibration must be reviewed separately.

Review:
- were win probabilities too concentrated?
- were Tier 1 make-cut probabilities too optimistic?
- were Tier 2 make-cut and top-10 probabilities too optimistic?
- were Tier 4 and Tier 5 make-cut probabilities too pessimistic?
- were longshot top-10 outcomes underrepresented?
- did high-variance venues flatten outcomes more than the model expected?
- at birdie-fest venues (high birdie conversion rate, scoring profile easy-to-standard, `venue_variance_class = standard`), were Tier 3 top-10 probability bands set too low? Birdie-fests compress the NeutralSkill advantage gap; Tier 3 players require higher top-10 probability floors at these venues than at tight or penal tracks. Flag for review when 4+ Tier 3 players finish in the top 10 at a birdie-fest venue.

Where possible, probability review should compare predicted bands to realized frequencies over multiple events, not one event alone.

## 13. Learning output objects
Every audit should generate four outputs.

### A. Event audit log
Human-readable verdict of what happened and why.

### B. Venue write-back block
Paste-ready structured changes for the active venue file.

### C. Global miss ledger rows
Structured rows appended to the master miss ledger.

### D. Engine review flags
A short list of possible engine-wide rule issues requiring future confirmation.

## 14. Required audit record fields
Every final audit record should store at minimum:
- event_id
- venue_id
- event_conditions_summary
- winning_score
- cutline
- top_finish_profile_summary
- tier1_top10_rate
- tier1_win_rate
- tier2_top20_rate
- anti_pattern_hit_rate
- debut_penalty_review
- key_miss_cases
- weight_changes
- anti_pattern_changes
- variance_changes
- engine_rule_flags
- venue_write_back_status
- audit_completed_by_system

## 15. Failure conditions
The learning loop fails if:
- no audit is run after projections were published
- the audit is narrative only with no structured change log
- significant misses are not categorized
- venue changes are made without evidence
- engine rules are changed from one anecdote
- betting or fantasy outcomes influence core calibration
- confidence is not updated when evidence is mixed
- no write-back or hold decision is recorded

## 16. Operating standard
The learning loop must always prefer:
- compounding over reaction
- evidence over memory
- classification over vague hindsight
- bounded updates over weekly thrash
- engine integrity over preserving prior takes

This file defines how the single-system Perplexity PGA VenueDNA engine learns from tournament outcomes and improves over time.
