# PGA VenueDNA Tier Engine — Weekly Event Workflow
Version 1.1 — June 2026

Purpose: This file is the concrete week-of-event operating runbook for the PGA VenueDNA Space. It converts the system architecture, scoring engine, and audit loop into one repeatable Monday-through-post-event workflow.

Use this file whenever a new tournament week begins.

## 1. Operating rule

Run the event in this order. Do not skip steps. Do not reorder steps unless a file or data dependency forces a pause.

1. Venue lock
2. Event context build
3. Field ingestion
4. Trait and form matrix build
5. Full-field scoring
6. Tier review and player brief generation
7. Market / DFS derivative layer
8. Round 1 live diagnostic
9. Post-tournament audit
10. Venue-library write-back and archive

This file governs weekly operations. The master architecture file governs system design. The scoring engine file governs score construction. The full system prompt governs output behavior and failure tests.

## 2. Monday — Venue lock

### 2.1 Confirm event scope
Before any scoring begins, confirm:

- event name
- venue name
- course routing
- par
- yardage
- green surface
- cut rule
- expected weather pattern
- whether the venue already has a locked intelligence file

If any of these are unclear, resolve them first. Do not score a field against an uncertain venue profile.

### 2.2 Load the active venue intelligence
If a venue file already exists, load it and verify that it still matches the current tournament setup.

Confirm that the active venue profile includes:

- structural description
- trait weight matrix
- anti-pattern list
- anti-pattern magnitude modifier rules
- debut penalty framework
- comp-course framework
- scoring band expectations
- variance notes
- any known weather sensitivity adjustments
- any risk-stressor map already established

If the venue setup materially changed from the stored version, create a revised venue version before field scoring.

### 2.3 Venue lock output
At the end of venue lock, the system must be able to state:

- what this course rewards
- what this course punishes
- what traits carry the heaviest weight
- which anti-patterns are active
- what type of player is structurally miscast here

Do not proceed until that statement is stable.

## 3. Monday–Tuesday — Event context build

Create an event context file for the week.

### 3.1 Required event context fields
The event context should include:

- event_name
- event_slug
- season_year
- venue_name
- venue_code
- venue_file_version
- par
- yardage
- surface
- cut_rule
- weather_forecast_class
- expected_scoring_band
- field_size
- notes_on_setup_change
- notes_on_data_gaps

### 3.2 Expanded setup fields
For venues where setup materially changes scoring, add explicit fields for:

- fairway_width_class
- rough_severity_class
- firmness_class
- green_speed_policy
- rollout_class
- long_iron_frequency_class
- difficulty_class
- event_class

These fields exist so anti-pattern magnitude and risk-stressor logic can be applied explicitly rather than narratively.

### 3.3 Weather classification
Classify weather into an actionable modeling label, not a vague description.

Use labels such as:

- firm_fast
- neutral
- soft_wet
- high_wind
- mixed_uncertain

If the week projects as soft/wet, note whether anti-pattern penalties should be reduced and whether scoring band expectations need to widen.

### 3.4 Setup-conditional pre-check
Before field scoring, explicitly test whether setup notes change the size of any active anti-pattern.

Examples:
- materially wider fairways may soften `bomb_and_spray`
- firmer short-grass runoffs may increase `tight_runoff_scramble`
- no setup softening under wind may sustain long-iron / trajectory pressure even if fairways widen

If setup changes matter and no modifier rule exists, flag it before scoring. Do not bury the issue in post-event hindsight.

## 4. Tuesday — Field ingestion

### 4.1 Raw inputs required
Before scoring, gather the weekly field input set.

Minimum required sources:

- verified field list
- true SG file
- recent form file
- last-events SG split file
- venue history data where available
- odds data if market layer will be produced
- DraftKings salary file if DFS output will be produced

### 4.2 Minimum player fields
Each player row should contain, where available:

- player_name
- player_id
- world_rank
- true_sg
- true_sg_ott
- true_sg_app
- true_sg_arg
- true_sg_putt
- recent_form_index
- last_event_sg_splits
- venue_starts
- venue_rounds
- career_venue_sg
- debut_flag
- debut_class
- injury_flag
- comp_course_signal
- dk_salary
- outright_odds

If a field is missing, document it. Do not silently fabricate substitutions.

### 4.3 Missing-data behavior
If data is incomplete:

- identify exactly what is missing
- continue only if venue-fit scoring is still supportable
- widen confidence where appropriate
- do not hallucinate venue history or surface-specific putting evidence
- do not replace unavailable evidence with vague reputation language

## 5. Tuesday — Trait and form matrix build

### 5.1 Normalize to model inputs
Transform the raw player inputs into the fields required by the scoring engine.

This includes:

- normalized trait scores
- adjusted recent-form score
- result-quality-multiplied form inputs
- comp-course adjustments
- venue-history override eligibility
- debut penalty class
- injury / availability gate flags
- named structural risk tags where applicable

### 5.2 Apply form processing rules
Use the engine’s standing rules:
- apply result quality multiplier before form weighting
- apply recency decay across the defined form window
- use career venue SG as primary form variable when the player meets the venue-history threshold
- apply recent-form hard gates where required

### 5.3 Risk pre-tagging
Before full-field scoring, create or refresh named risk tags for plausible top-end players.

Examples:
- `APP_200_plus`
- `MajorGrind`
- `tight_runoff_scramble`
- `wind_ballflight`

Risk tags should identify failure mechanisms, not generic worry.

### 5.4 Trait/form matrix output
Before full-field scoring, produce a trait/form matrix that makes it obvious:

- why each player is rating well or poorly
- what primary trait drives the score
- which penalties are likely to apply
- where named risk tags are active
- where missing-data confidence discounts will matter

This matrix is the first diagnostic checkpoint of the week.

## 6. Tuesday–Wednesday — Full-field scoring

### 6.1 Run the VTS scoring engine
Score the field against the locked venue profile.

For each player, the system must compute:

- raw trait contribution total
- debut penalty if applicable
- anti-pattern penalties if triggered
- anti-pattern setup modifiers if triggered
- comp-course adjustment if applicable
- recent-form hard-gate effect if applicable
- risk-stressor linkage adjustment if applicable
- final VTS
- tier assignment
- finish probability band

### 6.2 Tier assignment standard
Use the standing five-tier structure:

- Tier 1: Course Architects
- Tier 2: Contention Windows
- Tier 3: Top-10 Range
- Tier 4: Cut-Line Players
- Tier 5: Course Mismatches

Do not publish partial tier outputs. Every scored event gets a full five-tier field ranking.

### 6.3 Immediate sanity checks
Before player briefs are written, verify:

- the venue’s core traits are actually influencing the top of the board
- obvious anti-pattern players are not floating unrealistically high without explanation
- debut penalties are firing consistently
- soft-condition weeks are not over-penalizing bomb-and-spray or similar anti-patterns if the venue file says those should be softened
- setup-conditional anti-patterns are applying the correct modifier when fairway width, runoff severity, or green-speed policy changed
- named risk tags that are directly stressed by event context create visible score or probability consequences
- negative-form hard gates are visibly reflected in the output

If these checks fail, stop and debug before moving on.

### 6.4 High-variance probability check
If `venue_variance_class = high` or `weather_forecast_class = high_wind`, confirm before publish that:

- make-cut probabilities are not unrealistically concentrated in Tier 1 and Tier 2
- Tier 4 and Tier 5 survival odds are not being crushed to implausible lows
- top-10 bands have been compressed along with win probabilities

Do not leave high-variance calibration to the audit if miscalibration is already visible pre-publish.

## 7. Wednesday — Tier review and player briefs

### 7.1 Tier review
Read the scored field top-down and verify that the ranking “sounds like the course,” not just “sounds like the world ranking.”

Specifically confirm:

- Tier 1 players have structural fit, not just fame
- Tier 2 players have real contention paths
- Tier 3 players are missing a specific element
- Tier 4 and Tier 5 players are there for venue reasons, not generic pessimism
- no player survived into Tier 1 only because NeutralSkill overwhelmed a clearly active fit or risk gate

### 7.2 Generate Tier 1 and Tier 2 briefs
Every Tier 1 and Tier 2 player gets a structured brief containing:

- VTS score
- primary trait drivers
- venue history note
- recent form note
- anti-pattern or debut risk note
- conviction statement
- named failure condition

Do not use generic player blurbs. Each brief must explain why this venue changes the player’s chances.

### 7.3 Risk register
Create a short risk register for the highest-rated players.

For the top 3 to 5 VTS players, identify:

- the most likely reason the projection could fail
- whether the risk is structural, variance-based, weather-based, or health-based
- whether the risk changes conviction or only ceiling
- whether the event context actively stresses that risk this week

## 8. Wednesday — Market / DFS derivative layer

This layer is optional. It only activates if odds or DFS files are present.

### 8.1 Odds edge table
If outright or placement odds are available:

- convert odds to implied probability
- compare to model probability
- classify as Strong Bet / Bet / Pass / Fade
- log where model edge materially exceeds consensus

Do not let market prices rewrite the venue score. The market layer is derivative, not upstream.

### 8.2 DFS build
If DraftKings salary data is available:

- run the lineup optimizer
- obey salary cap
- obey venue-specific floor rules
- avoid auto-locking a max-salary player without lineup-composition evidence
- confirm all salary math before finalizing

If the venue file includes a long-course OTT minimum or similar floor rule, enforce it.

## 9. Thursday — Round 1 live diagnostic

### 9.1 Trigger
This protocol activates after all Round 1 groups finish.

Do not run it mid-wave unless explicitly needed for live monitoring.

### 9.2 Inputs
Use:

- Round 1 leaderboard position
- Round 1 SG splits if available
- hole / scoring context if available
- actual weather and course condition notes
- pre-tournament tier and VTS placement

### 9.3 Diagnostic logic
For each Tier 1 and Tier 2 player:

- compare Round 1 result to projected scoring band
- identify whether the miss was structural or statistical
- downgrade only when the miss is both large enough and structurally revealing
- hold when the bad round is variance noise rather than a venue-fit contradiction
- re-check whether the live setup appears to be softening or amplifying a pre-modeled anti-pattern
- re-check whether the named risk tag is materializing in the exact way anticipated

Outside players can be promoted only if the Round 1 profile maps to the venue’s true demands.

Do not reward random hot putting alone as proof of course fit.

### 9.4 Round 1 output
Produce:

- holds
- upgrades
- downgrades
- players out of contention
- players newly in contention
- one-sentence reason for every movement

## 10. Friday–Sunday — Tournament monitoring

Use the Space during the weekend for controlled diagnostics, not panic rewrites.

Focus on:

- whether the venue is playing as expected
- whether the winning profile matches the locked trait assumptions
- whether weather or setup created a structural shift
- whether anti-pattern players are surviving for explainable reasons
- whether round-by-round forecast severity is tracking actual scoring severity

Do not rewrite the venue file during the tournament. Save structural learning for the audit.

## 11. Monday after event — Post-tournament audit

### 11.1 Audit principle
The audit is mandatory. The audit is the compounding mechanism. The weekly projection is only the temporary output.

### 11.2 Required audit questions
Review:

- Tier 1 Top-10 hit rate
- Tier 2 contention accuracy
- anti-pattern fade accuracy
- debut penalty calibration
- recent-form hard gate performance
- venue-history override performance
- weather-adjustment correctness
- Round 1 diagnostic correctness
- most significant over-performers
- most significant under-performers
- whether named risk mechanisms were correct but under-converted into score impact
- whether high-variance probability bands were too compressed or too wide by tier

### 11.3 Miss classification
Every major miss should be tagged into one or more categories:

- trait mis-weight
- anti-pattern magnitude error
- debut penalty error
- weather misread
- venue-history misuse
- form-window error
- injury / health information gap
- variance / noise
- tier-mapping error
- overconfidence error

### 11.4 Audit write-back
At the end of the audit, write down exactly what changes:

- trait weights to revise
- anti-pattern penalties to revise
- anti-pattern setup modifiers to revise
- debut penalty rules to revise
- scoring-band assumptions to revise
- weather-sensitivity logic to revise
- risk-register-to-score linkage candidates to track
- open questions that still need another cycle of evidence

Do not leave the audit as narrative only. It must create explicit write-backs.

## 12. Venue library update

After the audit, update the venue file if evidence justifies it.

### 12.1 Update threshold
Write back only what is evidence-supported.

Do not change weights because the winner was famous or because one unexpected player spiked with a putter for four days.

Change the venue intelligence only when the event revealed:

- persistent trait importance
- incorrect anti-pattern magnitude
- incorrect anti-pattern setup modifier
- incorrect debut sensitivity
- structural weather interaction
- repeated blind spot versus player archetype

### 12.2 Versioning
If the venue file changes materially:

- increment the version
- note what changed
- note why it changed
- note what evidence triggered the revision

## 13. Weekly archive and handoff

At the end of each tournament cycle, preserve a compact handoff record containing:

- event and venue
- file versions used
- final tier board
- best edges identified
- main misses
- audit changes
- next action item

This handoff is what keeps the engine coherent across weeks.

## 14. Non-negotiable failure rules

A weekly run is incomplete if any of the following are missing:

- no locked venue profile before scoring
- no full-field five-tier ranking
- no Tier 1 / Tier 2 briefs
- no Round 1 diagnostic when the event was actively monitored
- no post-tournament audit
- no venue write-back decision
- no documentation of missing data or confidence limitations
- no setup-conditional anti-pattern check when setup notes materially changed the course

## 15. End-state definition

A tournament week is considered complete only when all of the following are true:

- the venue was locked before scoring
- the field was scored against the correct venue profile
- derivative outputs were built only after core scoring
- Round 1 diagnostic was handled if applicable
- post-event audit was completed
- venue intelligence was either updated or explicitly confirmed unchanged
- a handoff record exists for future reference

That is the complete operating loop for the PGA VenueDNA Space implementation.
