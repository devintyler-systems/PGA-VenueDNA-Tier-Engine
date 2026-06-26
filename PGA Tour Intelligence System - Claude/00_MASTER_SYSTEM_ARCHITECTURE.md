# PGA Tour Intelligence System — Master Architecture Document
## Export Package for Platform Migration
### Built: June 2026 | Venue Library Version: 5 venues locked

---

## WHAT THIS SYSTEM IS

The **Venue Trait Scoring (VTS) System** is a structured, auditable PGA Tour prediction engine. It is NOT a general golf analytics tool. It is a venue-specific scoring machine that answers one question per tournament week:

> *Given what THIS specific course actually rewards and punishes — measured across 25 years of winner data — who in this field has the trait profile that wins here?*

Every output is designed to survive a post-tournament audit. That standard is the difference between this and every consensus model it competes against.

---

## SYSTEM ARCHITECTURE — TWO LAYERS

### LAYER 1: Venue Intelligence Library (Persistent)
- A growing database of locked course DNA profiles
- Each venue profile contains: structural properties, trait weight matrix, anti-pattern flags, debut penalty calibration, comp-course framework, scoring bands
- Grows more accurate with every tournament cycle via mandatory post-tournament audit write-back
- **Currently locked venues: Harbour Town, Aronimink, TPC Craig Ranch, Colonial CC (v2), Muirfield Village**

### LAYER 2: Weekly Projection Engine (Activated at Tournament Week)
- Scores the current field against the active venue DNA profile
- Produces five-tier field rankings, player briefs, anti-pattern fade flags, value identification, DraftKings lineup optimization
- Inputs: DataGolf CSVs (true SG, recent form, L5 event results, system rankings), DraftKings salary data, verified field list

---

## THE 10-STEP WORKFLOW (execute in order, never skip steps)

```
1.  VENUE DNA LOCK          — Course profile established/confirmed before any player scoring
2.  VTS SCORING ENGINE      — Python script scores full field (72–156 players) 
3.  TIER RANKINGS           — All players assigned Tier 1–5
4.  PLAYER BRIEFS           — Full brief for every T1/T2 player
5.  FINISH PROBABILITY      — Win/T10/T20/T30/MC bands per tier
6.  DARK HORSE / EDGE ID    — VTS vs. consensus rank gap table
7.  ODDS-VS-MODEL TABLE     — Strong Bet / Bet / Pass / Fade classification
8.  DK LINEUP OPTIMIZATION  — Brute-force combinatorial, $50K cap, 6-player
9.  R1 LIVE DIAGNOSTIC      — Real-time tier updates after Round 1 scores post
10. POST-TOURNAMENT AUDIT   — Mandatory hit/miss verdicts + library write-back
```

---

## VENUE TRAIT SCORE (VTS) — HOW IT WORKS

### Scoring Formula
```
VTS (0–100) = Σ (trait_score × venue_weight) + modifiers

Where modifiers include:
  - Debut penalty (negative, venue-calibrated)
  - Anti-pattern penalties (negative, named and documented)
  - Comp-course bonus/penalty (±3–4 pts max per comp)
  - Health gate flag (player not scored into contention until R1 clears)
  - Recent form hard gate adjustments
```

### Five Tiers
| Tier | VTS Range | Label | Interpretation |
|------|-----------|-------|----------------|
| 1 | 80+ | Course Architects | Structural winners. Bet-on profiles. |
| 2 | 65–79 | Contention Windows | Live for the weekend, capable of winning if variables align |
| 3 | 50–64 | Top-10 Range | Lack ≥1 critical venue trait to contend |
| 4 | 35–49 | Cut-Line Players | World-class players, mismatched trait profiles |
| 5 | <35 | Course Mismatches | Structurally disadvantaged |

---

## DATA SOURCES

### Primary: DataGolf (datagolf.com)
Pull these CSVs for every tournament week:
- **System Rankings** — global ranking + composite metrics
- **True SG (tSG)** — strokes gained vs. field, stabilized (≠ season averages)
- **Recent Form (RF)** — form index, quality-adjusted
- **L5 Event Results** — last 5 individual event SG splits (OTT, APP, ARG, T2G, PUTT)
- **Event SG Splits** — current tournament historical SG data at this specific venue

### Secondary: DraftKings
- Salary file for lineup optimization
- Implied odds (DK pricing as probability signal)
- Contest structures (tournaments vs. cash games drive lineup construction differently)

### Tertiary: Market Odds
- Outright win odds from FanDuel/DraftKings/BetMGM for edge table construction
- Convert American odds to implied probability for model vs. market comparison

---

## RESULT QUALITY MULTIPLIER (apply before ANY form weighting)

```
Full-field 72-hole PGA Tour event:    1.0x
DP World Tour (full-field):           0.9x
Co-sanctioned event:                  0.85x
LIV Golf (54-hole, shotgun):          0.6x
Developmental tour:                   0.5x
```
**This is non-negotiable. LIV wins are not PGA Tour wins. Apply multipliers or the form window is contaminated.**

---

## FORM WINDOW DECAY MODEL

```
Most recent event:      35% weight
Event minus 2:          25% weight
Event minus 3:          10% weight
Event minus 4:          10% weight
Event minus 5:          10% weight
Event minus 6:          10% weight
```
**For players with 5+ starts at the specific venue: career venue SG overrides the form window as primary variable.**

---

## CROSS-VENUE ENGINE RULES (locked, evidence-confirmed)

These are permanent system rules that apply at every venue. They were learned through post-tournament audits and are not venue-specific — they are engine-level.

### BET GATE — tSG + Recent Form
```
Rule: True SG > 1.5 AND Recent Form > 1.0 = BET classification
      regardless of whether event-specific SG splits are available
      
Missing splits = wider confidence band, NOT a lower tier
Evidence: Henley tSG 1.53, RF 1.55 classified WATCH → won Colonial 2026
```

### SINGLE-EVENT SG REGRESSION
```
Rule: When any event SG split exceeds a player's true SG by >0.5 in any category,
      apply 0.7x multiplier to that split before entering weight matrix
      
One elite event is a signal, not a guarantee
Evidence: Novak APP +0.99 vs tSG +0.81 → reverted R3/R4, T54 Colonial
```

### RECENT FORM HARD GATE
```
RF < 0.0:   mandatory −4 additional VTS for any Tier 2 pick
RF < −0.5:  automatic Tier 3 floor regardless of true SG

Negative form is a HARD GATE, not a soft flag
Evidence: Vilips RF −0.10 → CUT; Greyserman trending down → CUT
```

### WEATHER SCORING BAND
```
Rule: Apply soft/firm blend to 36-hole projected scoring ONLY
      Recalibrate at the cut using actual conditions before projecting R3/R4
      Do NOT blend soft weight across full tournament
      
Courses almost always firm by Sunday
Evidence: Colonial projected −15/−18, actual −12; soft blend held all 4 rounds = miss
```

### AP PENALTY CONDITION-SENSITIVITY
```
Rule: All anti-pattern penalties reduce ~30% on confirmed soft-condition weeks
      (multi-day rain, course saturated)
      
Bomb-and-spray: −7 firm/fast → −4/−5 soft
Soft ground neutralizes the structural punisher of the anti-pattern
Evidence: Smalley bomb-and-spray flagged −7, finished T3 Colonial on soft week
```

### ARG WEIGHT IMMOVABLE
```
Rule: SG:ARG weight does NOT decrease on soft-conditions weather adjustment
      
Courses always firm late; ARG separates in final rounds
Evidence: MacIntyre T42 — ARG −0.25 became separator when Colonial firmed R3/R4
```

### DEBUT PENALTY FLOOR
```
Rule: Elite players (world rank <30) with no surface-specific putting data for venue:
      debut penalty MINIMUM −9, not reducible on rank merit alone
      
The unknown IS the penalty
Evidence: Åberg debut reduced to −8 on rank 5 merit → bentgrass putting gap materialized, T17 Colonial
```

### R1 DIAGNOSTIC HOLD PROTOCOL
```
Rule: Do NOT downgrade a Tier 2 pick after ONE below-projection R1
      
Downgrade gate = 3+ strokes outside projected range AND miss is structural
(wrong fairways, wrong approach zones) — not statistical noise

Evidence: Cole −3 R1 → CONDITIONAL HOLD → shot 63 R3, 2nd in playoff Colonial
```

### VTS vs. WORLD RANK EDGE
```
Rule: When VTS tier materially exceeds consensus rank (>40-spot gap), the edge is real
      
Press it — world rank systematically undervalues course-fit players
Evidence: Cole world 117/VTS T2 → 2nd; Meissner world 108/VTS T2 → T3; Griffin VTS T2 → T3
```

### DOUBLE-DISCOUNT PROTOCOL
```
Rule: Anti-pattern flag + LIV discount firing simultaneously → hold MC classification
      Do not revise upward without explicit counter-evidence
      
Evidence: DeChambeau Aronimink — revised from MC to T11/20 after cross-validation
          Original MC call was correct. Double discount = MC more probable than base rates suggest
```

### ANTI-PATTERN CEILING RULE
```
Rule: Anti-patterns adjust ceiling, not floor
      No MC call for Tier 2 without floor-collapse justification
```

---

## PROMO CARD RULES

- Tier 1 MC cap: ≤10% (≤15% for players with confirmed bentgrass putting liability at major speed)
- Tier 2 MC cap: ≤25–30% unless injury/weather shock flagged
- Any "highest-edge contrarian" pick must log: model probability, crowd probability, implied edge
- Post-event audit classifies misses as: trait mis-weight / weather mis-weight / tier-mapping error / overconfidence / variance

---

## DK LINEUP CONSTRUCTION PRINCIPLES

- **Salary cap:** $50,000 exactly (6 players)
- **Scheffler insight:** At max salary (~$13,500), Scheffler is correctly priced by DK. Five Tier 1/2 course-fits at lower salaries often outcompete him on pts/$. Do not auto-insert max salary player.
- **Birdie machine profile confirmed** for low-scoring environments
- **DK floor rule (Craig Ranch-derived):** Exclude players with OTT SG below −0.20 at courses 7,200+ yards
- **Always brute-force the optimizer** — manual combination math fails at scale
- **Always verify salary cap arithmetic** before finalizing — cap overages have happened in session

---

## THE POST-TOURNAMENT AUDIT (what makes this compound over time)

Mandatory 10-section audit after every event:
1. Event identification + conditions
2. Accuracy metrics (Tier 1 → T10 rate, AP flag hit rate)
3. Tier 1/2 player review (every player, actual vs. projected)
4. Anti-pattern outcomes
5. Weight matrix adjustments
6. Model miss log (player + miss category + fix)
7. Debut penalty recalibration
8. Form window / result quality review
9. R1 diagnostic review
10. Library write-back (new course intelligence + highest-leverage change)

**The audit is the product. The projection is just the output.**

---

## PROHIBITED BEHAVIORS (failure modes to hard-code as guardrails)

1. Using world ranking as a projection input without converting to venue-relevant traits
2. Projecting favorably on general recent form without venue-specific filtering
3. Treating SG:Putting on Bermuda as predictive on Bentgrass (surface contamination)
4. Issuing a projection without a VTS score
5. Applying flat recency weight instead of decay model
6. Treating LIV results as PGA Tour-equivalent without multiplier
7. Holding a Tier 1 projection after R1 disqualifies it
8. Skipping the post-tournament audit
9. Using hedging language in any projection
10. Presenting consensus picks as validation for venue-derived projections

---

## HOW TO REBUILD ON PERPLEXITY / MULTI-MODEL PLATFORM

### System Prompt Architecture
The system needs a persistent system prompt that contains:
- Layer 1: Prime Directive (venue-specific only, audit-ready standard)
- Layer 2: Venue Library Protocol (DNA extraction, anti-patterns, debut penalty, result quality)
- Layer 3: Weekly Engine Protocol (VTS assignment, form window, AP penalties, health gate, tier output)
- Layer 4: R1 Diagnostic
- Layer 5: Output format standards
- Layer 6: Conviction standards
- Layer 7: Audit loop mandate
- Layer 8: Prohibited behaviors + five failure tests

### File Attachments to Load Every Session
Load these files at session start to hydrate the venue library:
- `Aronimink_Intelligence_System_Update.md`
- `Colonial_2026_Intelligence_Update.md`
- `Muirfield_Village_Intelligence_Update.md` (build after Memorial audit)
- `Harbour_Town_Intelligence_Update.md` (build when available)
- `TPC_Craig_Ranch_Intelligence_Update.md` (build when available)

### Model Routing Recommendation (for Perplexity multi-model)
| Task | Recommended Model |
|------|------------------|
| Venue DNA extraction from course history | Claude (context retention, structured reasoning) |
| DataGolf data parsing + VTS scoring math | GPT-4o or Gemini (strong at structured data) |
| Odds edge table + market comparison | Claude or GPT-4o |
| DK lineup brute-force optimization | GPT-4o with code execution |
| Post-tournament audit synthesis | Claude (document generation, calibration writing) |
| R1 live diagnostic | Any fast model with current leaderboard data + Sonar for live results |

### Session Handoff Protocol
Every session should end with a handoff file containing:
- Tournament name + date
- VTS scores for full field (or tier placements at minimum)
- Locked lineups
- Open build items
- Any mid-session calibration discoveries
- Next action

---

*Generated: June 2026*
*For platform migration to Perplexity multi-model environment*
