# TPC_RIVER_HIGHLANDS_INTELLIGENCE_2026_v1
Version 1.0 — June 2026
Status: Active venue intelligence file created from 2026 Travelers Championship event context, scored-field traces, and 4-round post-event audit.
Venue code: TPC_RIVER_HIGHLANDS
Course: TPC River Highlands, Cromwell CT
Event class reference: Travelers Championship (PGA Tour, no-cut, 72 players)

## 1. Venue role
This file is the locked venue intelligence profile for TPC River Highlands under the 2026 Travelers Championship evidence state.

Use for future Travelers Championship projections when the setup is structurally similar (par 70, ~7,100 yards, Bentgrass greens and fairways, bluegrass/fescue rough, June scheduling). If course yardage, layout, or surface characteristics change materially, create a new version rather than force this file onto a different configuration.

## 2. Structural venue summary
TPC River Highlands is a short par-70 birdie-fest where the winning margin is built through putting heat and approach precision at wedge distances, not driving length. The course consistently produces negative-to-par scoring (field average -0.76 strokes per round vs par) and rewards players who can convert the birdie opportunities created by two reachable par-5s and multiple short par-4 scoring holes.

The course rewarded:
- Short-range putting conversion under birdie pressure
- Wedge and short-iron approach precision (sub-150 yards)
- Par-5 scoring efficiency
- Approach accuracy from 100-150 yards
- Driving accuracy on Bentgrass fairways (water on late holes 15-17)

The course punished:
- Wild driving that finds water or deep rough in scoring stretches
- Poor wedge contact (missed greens from inside 150 yards)
- Inability to convert short birdie looks under birdie-fest pressure
- Approach-only profiles without corresponding putting heat

## 3. Setup lock — 2026 evidence state
### 3.1 Confirmed setup conditions
- par: `70`
- approximate_yardage: `7,100`
- scoring_class: `birdie_fest`
- birdie_fest_flag: `true`
- field_avg_per_round_vs_par: `-0.76`
- surface: `Bentgrass greens + Bentgrass fairways`
- rough: `Kentucky bluegrass / fescue`
- field_size: `72 players, no cut`
- tournament_format: `72-hole stroke play`
- putting_variance_class: `high`

### 3.2 Putting variance note
Putting is the highest-variance scoring category at this venue. Top finishes historically require ≥ +2.0 SG-PUTT per tournament. Predictability from pre-tournament 12-month putting traits is low — the category weight elevation reflects importance of the category, not reliability of the trait signal. Do not treat a high `putt_short_conv` trait score as a reliable predictor of hot-week putting at this venue.

## 4. Core trait model
### 4.1 Venue trait weights
Updated 2026-06-29 per 2026 Travelers Championship audit (see write-back WB-A1, WB-A2, WB-A4):

| Trait             | Weight | Direction note                                              |
|-------------------|--------|-------------------------------------------------------------|
| app_wedge         | 0.20   | Dominant at short par-70; fine-tuned down from 0.22        |
| ott_accuracy      | 0.14   | Bentgrass fairways + water at 15-17                        |
| putt_short_conv   | 0.19   | Birdie conversion at birdie-fest; elevated from 0.16       |
| app_100_150       | 0.12   | Iron play at key scoring distances                         |
| putt_lag          | 0.11   | Distance control on Bentgrass; elevated from 0.10          |
| arg_rough         | 0.07   | Scrambling from bluegrass/fescue                           |
| app_150_200       | 0.06   | Less critical at this yardage                              |
| arg_bunker        | 0.05   | Bunker play                                                |
| ott_distance      | 0.03   | Not a differentiator; top-10 drove shorter than field avg  |
| par5_scoring      | 0.03   | Two reachable par-5s create consistent separation          |

Weights sum to 1.00.

### 4.2 Trait notes
- `ott_distance` is intentionally low-weighted (0.03). 4-round audit showed top-10 drove 1.4 yards shorter than field average. Distance does not differentiate scorers here.
- `putt_short_conv` weight (0.19) reflects category importance, not trait predictability. The predictor is weak at this venue; hot-week putting is largely unforecastable from 12m history.
- `par5_scoring` at 0.03 is directionally correct but modestly under-weights the scoring opportunity. WB-A3 recommends increasing to 0.05 pending additional event confirmation.
- Approach combined (app_wedge + app_100_150 + app_150_200 = 0.38) remains the dominant trait cluster, consistent with audit finding that SG-APP was 33.9% of top-10 premium.

## 5. Anti-pattern set
### 5.1 Active anti-patterns
- `bomb_and_spray`
- `wedge_liability`
- `poor_birdie_conv`
- `rough_approach_liab`
- `approach_only_limitation` *(added 2026 audit, WB-A6)*

### 5.2 Anti-pattern meanings
- `bomb_and_spray`: Long-and-wild driving profile. Water at 15-17 and Bentgrass fairways make dispersion expensive in the scoring stretch.
- `wedge_liability`: Poor approach from inside 150 yards. At a venue where birdie looks are created by short approaches, missing greens from wedge distance is severely punishing.
- `poor_birdie_conv`: Weak short-range putting. Cannot cash the birdie looks generated in a birdie-fest field.
- `rough_approach_liab`: Poor approach from rough. Moderately penalizing; see gate rule WB-B2 before applying.
- `approach_only_limitation`: SG-APP elite but SG-PUTT below neutral. Pattern produces top-10 to top-15 ceilings, not podium outcomes. *(WB-A6)*

### 5.3 Approach-only limitation anti-pattern (WB-A6)
Trigger conditions:
- `SG-APP 12m > 0.70` AND `SG-PUTT 12m < 0.0`

Penalty applied:
- `win_probability × 0.85`
- `top3_probability × 0.90`
- Does NOT affect tier gate assignment

Evidence: 3-player pattern in 2026 event — Morikawa (3rd, SG-PUTT 15th), Cantlay (T14, PUTT 28th), Burns (T12, ARG 66th). Elite approach without putting heat yields top-10 to top-15, not podium. Confidence: medium-high. Validate at 2027 Travelers Championship.

## 6. Anti-pattern penalty magnitudes
### 6.1 Base penalty ranges
- `bomb_and_spray`: -1.5 to -4.0 SG
- `wedge_liability`: -2.0 to -5.0 SG
- `poor_birdie_conv`: -1.5 to -4.0 SG
- `rough_approach_liab`: -1.0 to -2.5 SG
- `approach_only_limitation`: probability modifiers only (see §5.3)

Anti-penalty cap: -9.0 SG total.

### 6.2 Wedge liability modifier (WB-B1, cross-venue)
**Rule:** If `wedge_liability` is active AND `max(ARG_Rough_score, ARG_Bunker_score) >= 70`, reduce the wedge_liability VTS penalty by 40% (multiply by 0.60).

**Rationale:** When a player can scramble effectively, the wedge_liability penalty overstates the scoring risk of missed greens. A strong scrambler who misses close compensates via recovery.

**Evidence:** Alex Fitzpatrick (wedge_liability fired → Tier 5 rank 57; actual SG-APP +5.518, T7). Justin Thomas (wedge_liability correctly identified approach issues, but SG-ARG +6.257 produced T14 from rank 49). Confidence: medium. Validate against 3 additional events before applying universally.

### 6.3 Rough approach liability gate (WB-B2, cross-venue)
**Rule:** `rough_approach_liab` flag only fires if `ARG_Rough_score < 55`. Suppress the flag if `ARG_Rough_score >= 55` (player can effectively scramble out of rough).

**Evidence:** Corey Conners (rough_approach_liab active → rank 51; actual SG-ARG +3.492, T7). MacIntyre (rough_approach_liab active → rank 43; actual SG-APP +3.598, T10). Both had ARG profiles above 55 threshold. Confidence: medium. Gate threshold of 55 is provisional; validate with 3+ events before finalizing.

## 7. Venue history treatment
### 7.1 General guidance
Venue history delta (VHD) is a meaningful layer at TPC River Highlands where course familiarity with the Bentgrass putting surface, specific hole routing, and par-5 strategy creates genuine repeat-performance advantages.

### 7.2 Recency decay rule (WB-A5)
**Rule:** Apply recency decay to course-history (CH) SG rounds older than 3 years. Rounds before the 3-year cutoff count at 60% weight in the VHD blend.

`rounds_before_3yr_cutoff: decay_factor = 0.60`

**Evidence:** Tommy Fleetwood (18 rounds, CH SG +1.76, model rank 2) finished T14. His 18-round history spans 5+ seasons; older rounds over-inflated expected approach performance. Viktor Hovland (19 rounds, CH SG +1.423, won) — history concentrated in active 2022-2025 window. Confidence: medium. Validate at 2027 Travelers Championship before promoting to standard rule.

### 7.3 Minimum rounds for VHD premium
- Rounds < 4: treat as debut-adjacent, minimal VHD contribution
- Rounds 4-8: moderate VHD contribution; weight proportionally
- Rounds ≥ 8: full VHD contribution, with recency decay applied per §7.2

## 8. Tier caps and eligibility logic
### 8.1 Tier 1 considerations
- Tier 1 requires clearly positive VenueFitDelta AND neutral or better putting profile
- `approach_only_limitation` flag active: cap win probability; do not block tier outright
- `bomb_and_spray` at full penalty: consider Tier 2 cap unless approach/putting compensates

### 8.2 Tier 2 blocks
Block Tier 2 when:
- `wedge_liability` at full penalty AND `ARG_Rough_score < 55`
- Multiple anti-patterns stacking beyond -6.0 SG combined

## 9. Debut framework
Apply engine default debut framework. No venue-specific debut modifiers validated from 2026 evidence alone.

Working posture:
- debut remains a real penalty at a putting-intensive birdie-fest
- comp-specialist relief is appropriate for players with strong course-adjacent profiles
- revisit after 2027 event

## 10. Probability / variance guidance
### 10.1 Venue variance class
`high` — particularly in the putting category. Week-to-week SG-PUTT variation is among the highest on tour at this venue type.

### 10.2 Probability handling
At this venue class:
- Widen the tail: late-field players with hot putting weeks can legitimately reach T5-T10
- Do not over-compress top-10 probabilities for strong approach players without putting flags
- Preserve winner normalization while acknowledging that single-week putting outliers can produce winners from outside the top-20 pre-tournament ranks

### 10.3 No-cut field note
72-player no-cut field. All players receive finish probabilities. Win exponent calibrated at 4.5 (vs standard 5.0) to reflect full-field survival over 4 rounds.

## 11. Confidence state
**Raise confidence:**
- Approach importance (APP_Wedge + APP_100_150 combined dominance confirmed all 4 rounds)
- Par-5 scoring as a scoring separator (4-round validated trait signal)
- OTT_Distance as a non-differentiator

**Hold confidence:**
- Putting category weight elevation (category importance confirmed; trait predictability unresolved)
- ARG compensating ability to suppress anti-patterns (2-3 player evidence, needs cross-event validation)

**Lower confidence locally:**
- `rough_approach_liab` gate threshold (55 is provisional)
- `wedge_liability` modifier magnitude (0.60 factor needs 3-event validation)

## 12. Comparison-year discipline
This file is anchored to 2026 TPC River Highlands evidence.

Do not assume prior Travelers Championship editions (pre-2023) are directly equivalent when:
- Course yardage changes materially
- Green surface (Bentgrass) or rough profile changes
- Scoring conditions diverge significantly from birdie-fest expectation

If future event context differs materially, create:
- `TPC_RIVER_HIGHLIGHTS_INTELLIGENCE_[YEAR]_v2.md`
or a setup-specific branch file.

## 13. Audit-linked write-back summary
This file implements the following locked takeaways from the 2026 Travelers Championship 4-round audit:

**Applied (WB-A1):** putt_short_conv weight 0.16 → 0.19; putt_lag weight 0.10 → 0.11. 4-round validated putting premium.
**Applied (WB-A2):** ott_distance weight 0.05 → 0.03. Consistent 4-round contradicted enrichment signal.
**Applied (WB-A4):** app_wedge weight 0.22 → 0.20. Rebalancing offset; approach combined weight remains dominant.
**Applied (WB-A5):** Recency decay rule for CH SG rounds > 3 years (60% weight). Validate 2027.
**Applied (WB-A6):** approach_only_limitation anti-pattern added. Probability modifier only.

**Pending external validation (WB-A3):** par5_scoring 0.03 → 0.05. Evidence is strong (4-round validated) but deferred until 2027 confirmation before applying as a permanent increase.
**Pending cross-venue validation (WB-B1):** wedge_liability modifier when ARG compensating strength ≥ 70. Validate at 3 additional events.
**Pending cross-venue validation (WB-B2):** rough_approach_liab gate threshold ARG_Rough < 55. Validate at 3 additional events.
