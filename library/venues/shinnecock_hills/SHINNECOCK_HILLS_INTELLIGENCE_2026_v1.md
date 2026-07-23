# SHINNECOCK_HILLS_INTELLIGENCE_2026_v1
Version 1.0 — June 2026
Status: Active venue intelligence file created from 2026 U.S. Open event context, scored-field traces, and post-event audit.
Venue code: SHINNECOCK_HILLS
Course: Shinnecock Hills Golf Club
Event class reference: U.S. Open

## 1. Venue role
This file is the locked venue intelligence profile for Shinnecock Hills under the 2026 U.S. Open setup evidence currently available in the Space.

This file should be used for future Shinnecock-based projections only when the announced setup is structurally similar. If fairway width, rough profile, firmness, or green-speed policy changes materially, create a new version rather than force this file onto a different setup.

## 2. Structural venue summary
Shinnecock Hills is a major-championship, wind-exposed, high-penalty venue where the winning profile is still driven primarily by disciplined long-game control, but the 2026 setup showed that corridor width can materially change how harshly wild power should be punished.

The course rewarded:
- OTT distance plus playable accuracy
- wind-tolerant ball flight
- long-iron and 200+ yard approach resilience
- scrambling from demanding recovery positions
- emotional and tactical durability over four hard rounds

The course punished:
- short-and-wild driving
- poor long-iron control under wind
- weak recovery profiles from tight or exposed areas
- players who relied on clean rhythm without major-pressure resilience

## 3. Setup lock — 2026 evidence state
### 3.1 Confirmed setup conditions
- weather class: `high_wind`
- weather sequencing note: forecast magnitude broadly correct, round-order severity partially wrong
- fairway width class: `wide_relative_us_open_historical`
- rough severity class: `high`
- firmness class: `firm`
- green speed policy: `no_softening_for_wind`
- runoff challenge: `meaningful`
- event difficulty class: `high`
- venue variance class: `high`

### 3.2 Interpretation
The course still played like a U.S. Open and still demanded elite driving control, but the widened fairways created more tolerance for aggressive drivers than a historically narrow Shinnecock baseline would imply.

That means the anti-pattern concept `bomb_and_spray` remains valid here, but its default penalty magnitude was too harsh for the 2026 configuration.

## 4. Core trait model
### 4.1 Primary traits
Use the following structural trait priorities for Shinnecock-like setups:

- OTT_Distance_Accuracy composite: 26
- APP_175_200_plus / long-iron resilience: 22
- WindTolerance / trajectory control: 18
- SG_ARG / exposed recovery skill: 12
- MajorGrind / four-round difficulty resilience: 10
- SG_APP overall baseline quality: 7
- Pressure-hole performance: 3
- Surface putting transfer: 2

Weights sum to 100.

### 4.2 Trait notes
- `OTT_Distance_Accuracy composite` is preferred to raw SG:OTT because the venue is not simply a power test; it is a playable-power test under exposure.
- `APP_175_200_plus` should be treated as a core scoring lever whenever forecast and setup indicate repeated long-iron stress.
- `WindTolerance` remains a confidence-raised trait at this venue after the 2026 audit.
- `Surface putting` remains a low-weight finisher, not a driver.

## 5. Anti-pattern set
### 5.1 Active anti-patterns
- `short_and_wild`
- `bomb_and_spray`
- `weak_tight_runoff`
- `poor_lag_putting`
- `APP_200_plus_fragility`
- `major_grind_fragility`

### 5.2 Anti-pattern meanings
- `short_and_wild`: insufficient distance plus poor corridor control; structural fade.
- `bomb_and_spray`: elite or above-average distance paired with miss dispersion that usually becomes expensive in U.S. Open conditions.
- `weak_tight_runoff`: recovery profile that underperforms when misses feed into shaved or exposed collection areas.
- `poor_lag_putting`: vulnerable on long, fast, contour-heavy greens where defensive two-putting matters.
- `APP_200_plus_fragility`: long-iron exposure likely to punish the player under wind.
- `major_grind_fragility`: four-round difficulty resilience concern, especially when par is an asset.

## 6. Anti-pattern penalty magnitudes
### 6.1 Base penalty ranges
Use these as venue defaults before setup modifiers:

- `short_and_wild`: -3.5 to -5.0 VTS
- `bomb_and_spray`: -3.5 to -4.5 VTS
- `weak_tight_runoff`: -1.5 to -2.5 VTS
- `poor_lag_putting`: -0.75 to -1.5 VTS
- `APP_200_plus_fragility`: typically trait-driven first; direct anti-pattern overlay only when venue file chooses to stack a bounded extra penalty
- `major_grind_fragility`: generally use risk-linkage and tier-cap logic before large direct VTS penalties

### 6.2 2026 setup modifier rule
For `bomb_and_spray` under the 2026 Shinnecock evidence state:

Apply:
`applied_bomb_and_spray = base_penalty × 0.60 to 0.70`

Trigger conditions:
- fairway_width_class = `wide_relative_us_open_historical`
- green_speed_policy = `no_softening_for_wind`
- rough_severity_class remains `high`

Interpretation:
- the venue still punishes wild misses
- the setup still rewards disciplined driving
- but materially wider corridors partially offset the usual punishment severity for power-dispersion players

### 6.3 weak_tight_runoff rule
Hold `weak_tight_runoff` at the existing base range for now.

Reason:
- 2026 evidence is not clean enough to isolate this penalty from the co-occurring `bomb_and_spray` miss on Sam Burns
- revisit only when it fires without that co-occurrence in a comparable setup

### 6.4 short_and_wild rule
Do not soften `short_and_wild` off the 2026 event.

Reason:
- the 2026 audit showed it faded cleanly and does not share the same corridor-benefit profile as `bomb_and_spray`

## 7. Tier caps and eligibility logic
### 7.1 Tier 1 blocks
Block Tier 1 when any of the following are true:
- `short_and_wild` active
- `APP_200_plus_fragility` active at severe level and weather class = `high_wind`
- `major_grind_fragility` active at severe level and event_class = major and difficulty_class = high
- health gate active

### 7.2 Tier 2 blocks
Block Tier 2 when:
- `short_and_wild` is active at severe level
- debut penalty class is top-tier restrictive
- multiple anti-patterns stack and push the player below the venue fit minimum

### 7.3 Venue fit minimums
For this venue class:
- Tier 1 requires clearly positive VenueFitDelta
- Tier 2 requires at least neutral-to-positive VenueFitDelta unless overridden by exceptional venue history and no active severe gates

This venue should not publish “best player in the field” into Tier 1 when the fit is only neutral and the risk layer is stressed.

## 8. Named risk-stressor map
### 8.1 APP_200_plus
Stress this risk when:
- weather_forecast_class = `high_wind`
- long_iron_frequency_class = `high`

Allowed actions:
- Tier 1 block when severe
- top10_pct discount
- win_pct discount
- optional bounded VTS haircut if not already fully expressed in trait scoring

### 8.2 MajorGrind
Stress this risk when:
- event_class = `major`
- difficulty_class = `high`
- winning score expectation is near par or worse

Allowed actions:
- Tier 1 block when severe
- top10_pct discount
- top20_pct discount only when the player also carries volatility or recovery weakness

### 8.3 weak_tight_runoff / exposed recovery
Stress this risk when:
- firmness_class = `firm`
- runoff challenge = `meaningful`
- misses are expected to gather into shaved or exposed areas

Allowed actions:
- top10_pct discount
- bounded VTS discount
- pair naturally with SG_ARG weakness

## 9. Debut framework
Hold debut framework unchanged from engine default until Shinnecock-specific evidence proves otherwise.

Working posture:
- debut remains a real penalty here
- comp specialists can receive only bounded relief
- one-event rookie survival is not enough to soften the venue rule

## 10. Venue history treatment
Use venue history only as a relative-to-baseline adjustment.

Guidance:
- meaningful Shinnecock history can help when a player repeatedly outperforms baseline on this exact style of test
- shallow history should stay conservative
- do not let old U.S. Open finish positions override present long-game fit

## 11. Probability / variance guidance
### 11.1 Venue variance class
Set venue variance class to `high` for the 2026 evidence state.

### 11.2 Probability handling
At this venue class:
- compress separation in make-cut and top-10 bands, not only win probability
- avoid extreme confidence in Tier 2 make-cut rates
- allow more survival probability in Tier 4 and Tier 5 than a standard event model would
- preserve winner normalization while widening plausible contention tails

### 11.3 Forecast sequencing guidance
Round-by-round weather severity ordering should be treated as a soft guide, not a hard ranking input, until more events confirm forecast-day sequencing reliability.

## 12. Confidence state
Raise confidence:
- WindTolerance
- OTT_Distance_Accuracy composite

Hold confidence:
- MajorGrind as a concept, but not yet as a stronger weight
- weak_tight_runoff magnitude

Lower confidence only locally:
- `bomb_and_spray` magnitude at Shinnecock under wide-fairway/no-softening setup conditions

Do not lower confidence in the anti-pattern concept globally.

## 13. Comparison-year discipline
This venue file is anchored to the 2026 setup evidence presently stored in the Space.

Do not assume historical Shinnecock U.S. Open versions are directly equivalent when:
- fairway width is materially different
- wind-response setup policy is different
- firmness or runoff behavior is materially different

If future event context differs materially, create:
- `SHINNECOCK_HILLS_INTELLIGENCE_[YEAR]_v2.md`
or a setup-specific branch file.

## 14. Audit-linked write-back summary
This file implements the following locked takeaways from the 2026 U.S. Open audit:
- keep core trait model intact
- retain `short_and_wild` as a valid hard fade
- reduce `bomb_and_spray` magnitude for the 2026 widened-fairway / no-softening setup
- hold `weak_tight_runoff` pending cleaner evidence
- formalize APP_200_plus and MajorGrind as stress-linked risk rules here
- treat Shinnecock 2026 as a high-variance probability-compression venue

## 15. Next audit checkpoint
Re-test these specific Shinnecock rules when one of the following occurs:
- Shinnecock hosts again with a similar setup
- another major presents widened corridors plus no-softening wind policy
- another high-wind major validates or disconfirms the APP_200_plus and MajorGrind stress-link logic

Until then, this file is the active intelligence baseline for Shinnecock Hills in the current Space.
