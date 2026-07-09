# THERENAISSANCECLUB_INTELLIGENCE_2026_v2

## Overview
**Event:** 2026 Genesis Scottish Open
**Venue:** The Renaissance Club, North Berwick, East Lothian, Scotland
**Model Version:** VenueDNA v2
**Generated:** 2026-07-06

---

## 3.1 Venue Setup

| Attribute | Value |
|-----------|-------|
| Par | 71 |
| Yards | 7,103 |
| Type | Links |
| Location | East Lothian coastline, Scotland |
| Wind Exposure | HIGH — prevailing SW, gusts common |
| Firmness | Fast and firm in summer conditions |
| Rough Type | Scottish links rough — penal, thick, variable |
| Primary Scoring Zone | Approach 150-200yds (dominant par-4 approach distance) |
| Fairway Width | Moderate — accuracy premium without being hyper-narrow |
| Bunkers | Deep, pot-style links bunkers at strategic locations |
| Green Speed | Fast — medium Stimp in calm, variable in wind |
| Cut Rule | Top 65 and ties after 36 holes |
| Variance Class | HIGH |

### Setup Notes
The Renaissance Club plays as a classic East Lothian links. Wind direction heavily influences which holes play hardest. The course demands repeated approaches from 150-200yds — the dominant par-4 length — making SG:APP in this zone the primary separating factor. Short game (ARG) is critical because links rough produces unpredictable lies, demanding creativity around greens. Driving accuracy matters more than raw distance — wayward drives in rough at 150-200+ yards are punishing on scoring lines.

---

## 3.2 Trait-Weight Matrix

| Trait | Weight | Rationale |
|-------|--------|-----------|
| Approach 150-200yds (value) | 30% | Dominant scoring zone — most par-4s play this distance |
| SG:OTT (positional driving) | 20% | Accuracy matters more than distance on this layout |
| SG:APP (overall) | 15% | Approach baseline across all distances |
| SG:PUTT | 13% | Links greens reward good putting, but variance is high |
| SG:ARG (short game) | 10% | Links rough demands elite scrambling |
| Driving Accuracy (course-adj) | 12% | Staying in fairway critical for 150-200yd corridors |
| **Total** | **100%** | |

### Weight Rationale
The 30% weighting on APP 150-200yd reflects historical analysis: this is the range from which the majority of approach shots are played at Renaissance. Positional driving (OTT with accuracy component) receives 20% because wild driving in links rough compounds approach difficulty significantly. Traditional SG:PUTT receives moderate weighting (13%) because putting variance on links greens is inherently high — exceptional putters can win but so can average putters who hit greens.

---

## 3.3 Anti-Pattern Definitions

### AP-1: Weak Approach / No Positive History
- **Condition:** SG:APP < 0 AND no positive course history (ch_adjustment ≤ 0)
- **Penalty:** −0.40 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Player demonstrably struggles from fairway at key distances AND has no Renaissance track record to offset. Most dangerous structural mismatch for this venue.

### AP-2: Accuracy-Negative / Approach-Negative
- **Condition:** driving_accuracy_adj < 0 AND app_150_200_value ≤ 0
- **Penalty:** −0.30 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Both primary drivers of Renaissance performance are negative. No compensating mechanism.

### AP-3: Volatile Putter (FLAG ONLY — no venue_fit penalty)
- **Condition:** SG:PUTT > 1.5 (extreme putter in 12-month regressed data)
- **Penalty:** None to venue_fit (already regressed 40% toward mean in NeutralSkill)
- **Severity:** WATCH
- **Rationale:** Extreme putting regression reduces NeutralSkill contribution. Watch for putters who over-rely on hot putting — links greens revert to mean faster than inland courses.

### AP-4: Bomb-and-Spray Pattern
- **Condition:** SG:OTT in top 20% of field AND SG:APP < 0
- **Penalty:** −0.35 to venue_fit_raw
- **Severity:** HIGH
- **Rationale:** Long hitters who find rough regularly compound approach difficulty. Renaissance rough is penal enough that distance advantage is negated by the extra difficulty of approaches from rough at 150-200yds.

### AP-5: Renaissance Debut
- **Condition:** No course history entries in Renaissance Club CH database
- **Penalty:** −0.20 to venue_fit_raw
- **Severity:** MODERATE
- **Rationale:** Links courses have a learning curve, especially in variable weather. Historical analysis shows debut finishes skew worse than form-adjusted predictions.

### AP-6: Weak Short Game (ARG)
- **Condition:** SG:ARG < −0.5
- **Penalty:** −0.20 to venue_fit_raw
- **Severity:** MODERATE
- **Rationale:** Links rough demands strong short-game creativity. Weak ARG players bleed shots from around greens on tough lies.

### AP-7: Multi-Flag Anti-Pattern (aggregate)
- **Condition:** 2+ flags from AP-1 through AP-6
- **Severity:** CONFIRMED ANTI-PATTERN
- **Rationale:** Compound structural mismatch — multiple weak-link signals align with specific Renaissance demands.

---

## 3.4 Debut Framework

Players debuting at The Renaissance Club receive:
- **venue_fit penalty:** −0.20
- **venue_history_delta:** neutral (50.0) — no bonus or penalty from history
- **debut_flag:** True
- **badge:** "Debut Watch"

**Debut exceptions considered:** European Tour regulars who frequently compete at links venues may have transferable course-read advantage. However, in the absence of direct Renaissance data, the debut discount applies uniformly. Players with strong AP-150-200 form from comparable links (Carnoustie, Kingsbarns, Troon) may partially offset this in NeutralSkill.

---

## 3.5 Comp-Course List

| Course | Similarity Score | Key Shared Traits |
|--------|-----------------|-------------------|
| Carnoustie Golf Links | 0.85 | Long-iron demand, firm/fast, full wind exposure |
| Royal Troon | 0.80 | Accuracy premium, approach corridors, links rough |
| Kingsbarns Golf Links | 0.78 | Approach-from-rough premium, coastal links |
| Cabot Highlands / Castle Stuart | 0.70 | Elevated links feel, wind variable, modern layout |
| North Berwick (West Links) | 0.72 | Same coastline, similar weather, links DNA |
| Dunbar Golf Club | 0.65 | East Lothian links, less championship-caliber |
| St Andrews (Old) | 0.68 | Links DNA but different hole architecture |

**Comp-course use:** When a player lacks Renaissance history, strong performance at Carnoustie (0.85 match) provides the best proxy signal. European Tour links regulars performing well at Carnoustie or Troon have demonstrated the skill set that translates to Renaissance.

---

## 3.6 Variance Class

**Class: HIGH**

**Rationale:**
- Links setup subject to dramatic wind shifts between waves/days
- Historical: winning scores have ranged from -15 to -21 (wide scoring spread)
- Links rough introduces bounce/roll unpredictability — increases round-by-round variance
- Fast greens + wind = putts swing widely across groups
- Demonstrated in results: multiple T40+ starting seeds have won; elite players frequently fail to make cut

**Variance implications for model:**
- High variance increases dark-horse probability (Tier 3+ win_prob adjusted upward vs. inland equivalents)
- Top-5/Top-10 multipliers calibrated higher than average tour event (4.5× and 8.0× vs ~4× and 7×)
- Make-cut probability band is wider across skill tiers than low-variance events

---

## 3.7 Winner Trait Profile

Based on historical Renaissance Club winners and top-5 finishers (2021-2025):

| Trait | Required Level | Notes |
|-------|----------------|-------|
| SG:APP (week) | +0.5 to +2.0 | Non-negotiable — winner always gains on approach |
| APP 150-200yd (value) | +0.03 to +0.10 | Primary zone must be elite for the week |
| SG:OTT (week) | Neutral to +1.0 | Distance doesn't beat accuracy here |
| Driving Accuracy | Above field avg | Stay in fairways — rough compounds everything |
| SG:ARG | Neutral to +1.0 | Must scramble when Renaissance rough finds you |
| SG:PUTT (week) | Variable | Spike putter wins occasionally, consistent putter more reliable |

**Winner profile summary:**
The Renaissance Club champion is typically an iron-first player who keeps the ball in play off the tee, attacks with precision from 150-200yds, and has enough short-game skill to save pars when links conditions dictate difficult lies. High-variance bonus: genuine OTT outliers can win if their iron game keeps up. Putting-only wins (relying on hot putter without elite iron play) are rare and short-lived.

---

## Model Outputs Summary

| Category | Count |
|----------|-------|
| Field Size | 166 |
| Tier 1 | 3 |
| Tier 2 | 24 |
| Tier 3 | 77 |
| Tier 4 | 32 |
| Tier 5 | 30 |
| Anti-Pattern Players (2+ flags) | 8 |
| Renaissance Debuts | 39 |
| HOT form players | 17 |
| COLD/COOL form players | 50 |

---

*VenueDNA v2 — The Renaissance Club Intelligence File*
*Generated: 2026-07-06*
