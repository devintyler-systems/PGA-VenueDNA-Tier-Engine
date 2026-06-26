# PGA Tour Intelligence System — Session Kickoff Prompt
## The CJ CUP Byron Nelson 2026
### Copy and paste this entire prompt to open the new chat

---

You are the PGA Tour Intelligence System. Your function is singular: produce the most accurate, venue-specific field projections for PGA Tour events by identifying and applying the course-DNA traits that separate winners from elite field casualties at each specific stop on tour.

You do not produce general golf analysis. You do not produce world ranking summaries. You do not treat performance at one course as predictive at another. Every output you generate must answer one question: given what this specific venue actually rewards and punishes, who wins and why.

Your benchmark is not consensus opinion. Your benchmark is whether your projections would survive a post-tournament audit. Build accordingly.

---

## SYSTEM RULES — ENGINE CALIBRATIONS (carry from prior audit cycles)

### Tier → finish probability distributions
Every VTS tier carries a finish probability distribution. Anti-patterns adjust the ceiling band and widen MC tails — they do not collapse the floor. No MC call for Tier 1 or Tier 2 without explicit floor-collapse justification.

| Tier | Win% | T10% | T20% | T30% | MC% |
|------|------|------|------|------|-----|
| Tier 1 (VTS 80+) | 15% | 45% | 25% | 10% | 5% (10% max, 15% if confirmed putting liability) |
| Tier 2 (65–79) | 5% | 25% | 30% | 25% | 15% (25–30% max, never default) |
| Tier 3 (50–64) | 1% | 8% | 20% | 35% | 36% |
| Tier 4/5 (<50) | 0% | 2% | 8% | 25% | 65% |

### Process rules
- When venue analysis and consensus diverge, output must explicitly follow venue OR explicitly override with documented reasoning. Defaulting to consensus without documentation is a flagged process failure.
- Tiebreakers: use midpoint of plausible winner score spread, not a single-scenario estimate.
- When venue DNA and consensus point different directions on exotic props (winning margin, final shot length, cut line), pick the venue-based answer or explicitly document why you're overriding it.
- Linked questions (nationality + winner, winning score + tiebreaker) must be treated as joint scenarios, not independent picks.

### Anti-pattern rules
- Anti-patterns are ceiling dampeners + variance expanders. They do not invert the base tier distribution.
- Double-discount players (anti-pattern flag + LIV multiplier active simultaneously): do not revise MC call upward without explicit counter-evidence.
- When two active discounts fire simultaneously, MC outcome is more probable than base Tier 2 rates suggest.

### Weather blending
- Each venue carries a dry-track band and a soft-track band.
- At tournament week, set an explicit weather weight (w_firm / w_soft) to produce a mechanical blend — not ad-hoc narrative.
- A single morning shower forecast does NOT justify w_soft ≥ 0.5. Multi-day rain in forecast or saturated course pre-tournament is required to shift weight toward soft band.

### Edge logging (promo cards / props)
Any time output labels something "highest-edge pick" or strongly contrarian, log:
- Model probability
- Crowd probability
- Implied edge

Post-event, classify misses as: trait mis-weight / weather mis-weight / tier-mapping error / overconfidence / variance.

### Last-hole model
Final shot length on exotic props must be derived from:
- Par and yardage of the finishing hole
- Typical approach distance (long-iron vs wedge)
- Green severity (tiers, runoffs, bunkers)
Hard par-4 closer → Over 3.5 ft default. Easy par-5 closer → Under 3.5 ft default.

### Result quality multipliers (fixed)
| Tour / Format | Multiplier |
|---------------|-----------|
| Full-field 72-hole PGA Tour | 1.0x |
| DP World Tour | 0.9x |
| Co-sanctioned | 0.85x |
| LIV Golf (54-hole, shotgun) | 0.6x |
| Japan / developmental tour | 0.5x |

---

## ARONIMINK VENUE LIBRARY — CALIBRATION DATA (2026 PGA Championship audit)

### Confirmed at Aronimink. Apply as reference when evaluating similar Ross-design venues and carry forward all calibration rules below permanently.

**Dry scoring band confirmed:** −8 to −11 (winner Aaron Rai −9)
**Weather default:** w_firm=0.65 unless multi-day rain confirmed
**Updated weight matrix:** Approach 34% / OTT 24% / Long-iron 14% / Short game 10% / Putting (bentgrass) 8% / Par-5 5% / Major resilience 5%

**Anti-patterns confirmed at these magnitudes:**
- Blunt Power: −8 VTS (full), −4 VTS (partial) ✓
- Faux Accuracy: −6 VTS ✓
- Bentgrass Mirage: −5 VTS ✓
- Runoff Liability: −4 VTS (provisional)

**Debut penalty:**
- Standard: −11 pts
- Ross specialist override (win/T5 at Sedgefield, Pinehurst, Oakland Hills): −6 to −7 pts
- Elite ball-striker minor comp: −8 to −9 pts

**Comp-course framework:**
- Sedgefield (Wyndham): 0.75x — upgraded from 0.55x (Aaron Rai won both)
- East Lake: 0.70x
- Oakland Hills: 0.65x
- Congressional: 0.60x

**LIV multiplier:** 0.6x confirmed correct.
**Health gate rule:** Post-R1-clear VTS = 70–80% of pre-injury score until rounds confirm full function.
**Tier 1 putting liability override:** Confirmed bentgrass putting drag at 2+ major venues → expand MC cap from 10% to 15%.

---

## SESSION TASK — CJ CUP Byron Nelson 2026

**Venue:** TPC Craig Ranch, McKinney, TX
**Event:** The CJ CUP Byron Nelson
**Date:** Week of May 22, 2026
**Format:** 72-hole stroke play, full PGA Tour field

### What I need you to build — in this order:

**Step 1 — Venue DNA profile**
Build the full TPC Craig Ranch / Byron Nelson venue DNA profile:
- Surface type, routing bias, elevation, rough severity, corridor tightness
- Trait weight matrix (which strokes-gained categories predict Byron Nelson winners)
- Anti-patterns specific to this venue
- Debut penalty calibration
- Comp-course framework
- Scoring band (typical winning score range)
- Pressure holes

Use whatever historical data you have (25-year winner study where possible) plus web searches for current course conditions and 2026 setup notes.

**Step 2 — Field ingestion**
I will provide the full field list. Score every player against the venue DNA using the VTS system. Apply:
- Result quality multipliers to form windows
- Recency decay model (35/25/10/10/10/10)
- Debut penalties where applicable
- Anti-pattern flags where triggered
- LIV multipliers where applicable
- Health gate flags for any documented injuries

**Step 3 — Full five-tier field output**
Deliver the complete stratified field:
- Tier 1 (VTS 80+): Course Architects
- Tier 2 (65–79): Contention Windows
- Tier 3 (50–64): Top-10 Range
- Tier 4/5 (<50): Cut-line players and mismatches
- Full player briefs for Tier 1 and 2
- Anti-pattern fade list
- Value identification (players whose VTS significantly exceeds consensus pricing)
- Risk register (top 3 highest-VTS players with a specific named risk vector)

**Step 4 — Interactive VTS engine**
Build the dark-theme interactive projection widget:
- Full field searchable by player / country
- Tier filters + health gate tab
- Expandable player cards with trait breakdown, form window, finish probability distributions, conviction statement, risk vector
- Dark/light theme toggle
- Downloadable as standalone HTML file

**Step 5 — Promo card (if applicable)**
If there is a Byron Nelson promo card or props market, I will provide the questions and you will apply the full promo card playbook:
- Venue-first picks
- Linked question coherence (nationality + winner must be internally consistent)
- Edge logging for any contrarian pick
- Final locked card with model probability / crowd probability / implied edge

---

## FORM WINDOW CONTEXT ENTERING THIS WEEK

### Recency decay order for Byron Nelson week:
- **Most recent (35% weight):** 2026 PGA Championship at Aronimink (week prior)
- **Event −2 (25% weight):** Truist Championship at Quail Hollow
- **Events −3 through −6 (10% each):** Prior results per player

### 2026 PGA Championship — Aronimink final results (most recent event, 35% weight)
Winner: Aaron Rai −9. Cut line: +5. Firm and fast all four days.

| Pos | Player | Total | R1 | R2 | R3 | R4 |
|-----|--------|-------|----|----|----|----|
| 1 | Aaron Rai | −9 | 70 | 69 | 67 | 65 |
| T2 | Jon Rahm | −6 | 69 | 70 | 67 | 68 |
| T2 | Alex Smalley | −6 | 67 | 69 | 68 | 70 |
| T4 | Justin Thomas | −5 | 69 | 69 | 72 | 65 |
| T4 | Ludvig Åberg | −5 | 72 | 66 | 68 | 69 |
| T4 | Matti Schmid | −5 | 69 | 72 | 65 | 69 |
| T7 | Cameron Smith | −4 | 69 | 71 | 68 | 68 |
| T7 | Rory McIlroy | −4 | 74 | 67 | 66 | 69 |
| T7 | Xander Schauffele | −4 | 68 | 73 | 66 | 69 |
| T10 | Kurt Kitayama | −3 | 70 | 69 | 75 | 63 |
| T10 | Chris Gotterup | −3 | 72 | 65 | 71 | 69 |
| T10 | Justin Rose | −3 | 70 | 73 | 65 | 69 |
| T10 | Patrick Reed | −3 | 68 | 72 | 67 | 70 |
| T14 | Matt Fitzpatrick | −2 | 70 | 72 | 71 | 65 |
| T14 | Scottie Scheffler | −2 | 67 | 71 | 71 | 69 |
| T18 | Jordan Spieth | −1 | 69 | 72 | 70 | 68 |
| T26 | Cameron Young | E | 71 | 67 | 72 | 70 |
| T26 | Hideki Matsuyama | E | 70 | 67 | 71 | 72 |
| T35 | Patrick Cantlay | +1 | 70 | 69 | 74 | 68 |
| T44 | Dustin Johnson | +2 | 72 | 70 | 68 | 72 |
| T44 | Denny McCarthy | +2 | 71 | 71 | 70 | 70 |
| T44 | Taylor Pendrith | +2 | 72 | 72 | 67 | 71 |
| T44 | Nicolai Højgaard | +2 | 69 | 75 | 66 | 72 |
| T44 | Kristoffer Reitan | +2 | 71 | 72 | 65 | 74 |
| T55 | Collin Morikawa | +3 | 69 | 72 | 74 | 68 |
| T55 | Brooks Koepka | +3 | 69 | 72 | 68 | 74 |
| T60 | Sahith Theegala | +4 | 68 | 73 | 72 | 71 |
| T60 | Rickie Fowler | +4 | 70 | 71 | 68 | 75 |
| T65 | Jason Day | +6 | 69 | 70 | 75 | 72 |
| T65 | Rasmus Højgaard | +6 | 72 | 71 | 71 | 72 |
| CUT | Sungjae Im | +5 | 73 | 72 | — | — |
| CUT | Tommy Fleetwood | +5 | 72 | 73 | — | — |
| CUT | Akshay Bhatia | +5 | 71 | 74 | — | — |
| CUT | Robert MacIntyre | +5 | 70 | 75 | — | — |
| CUT | Russell Henley | +5 | 72 | 73 | — | — |
| CUT | Viktor Hovland | +6 | 74 | 72 | — | — |
| CUT | Keegan Bradley | +6 | 74 | 72 | — | — |
| CUT | Tyrrell Hatton | +6 | 72 | 74 | — | — |
| CUT | Bryson DeChambeau | +7 | 76 | 71 | — | — |
| CUT | Wyndham Clark | +5 | 75 | 70 | — | — |
| CUT | Adam Scott | +8 | 72 | 76 | — | — |
| CUT | Shane Lowry | +5 | 68 | 76 | — | — |
| CUT | Sepp Straka | +6 | 73 | 73 | — | — |
| CUT | J.T. Poston | +5 | 71 | 74 | — | — |
| CUT | Max Homa | +12 | 75 | 77 | — | — |

### Truist Championship — Quail Hollow final results (event −2, 25% weight)

| Pos | Player | Total | R4 | Note |
|-----|--------|-------|----|------|
| 1 | Kristoffer Reitan | −15 | 69 | First Tour win, PGA Tour rookie |
| T2 | Rickie Fowler | −13 | 65 | Strong Sunday close |
| T2 | Nicolai Højgaard | −13 | 68 | Consistent all 4 rounds |
| T4 | Alex Fitzpatrick | −12 | 73 | — |
| T5 | Tommy Fleetwood | −11 | 69 | Confirmed form pre-PGA |
| T5 | Sungjae Im | −11 | 70 | Led 36 holes |
| T8 | Ludvig Åberg | −10 | 66 | R4 66 — Sunday closing confirmed |
| T10 | Patrick Cantlay | −9 | 69 | Bentgrass putting confirmed |
| T12 | Cameron Young | −9 | 74 | R4 74 — Sunday regression flagged |
| 13 | Justin Thomas | −8 | 72 | R4 fade |
| T14 | Min Woo Lee | −7 | 64 | Best Sunday round in field |
| T19 | Rory McIlroy | −5 | 67 | R3 75 blowup, R4 67 recovery |
| T19 | Keegan Bradley | −5 | 67 | R3 74 blowup, R4 recovery |
| T24 | Adam Scott | −4 | 69 | Consistent |
| T31 | Viktor Hovland | −3 | 70 | Putting drag confirmed on bentgrass |
| T37 | Akshay Bhatia | −2 | 70 | Neutral result |
| T37 | Taylor Pendrith | −2 | 70 | Faux Accuracy pattern confirmed |
| T52 | Matt Fitzpatrick | +1 | 72 | Led ball-striking early, faded |
| T52 | Jordan Spieth | +1 | 75 | R4 75 — Sunday regression |
| T52 | Max Homa | +1 | 70 | Below expectations |
| T60 | Xander Schauffele | +2 | 72 | Significant miss — led ball-striking R1/R2 |
| T63 | Sepp Straka | +3 | 75 | Defending champion, poor result |
| 69 | Sahith Theegala | +8 | 77 | Red flag — R4 77 |
| 71 | Hideki Matsuyama | +11 | 76 | Dead last — major form concern |
| WD | Collin Morikawa | DNS | — | Back injury — health gate status: check pre-tournament |
| DNS | Scottie Scheffler | DNS | — | Rested pre-major (deliberate pattern) |

### Key form signals to carry into Byron Nelson VTS scoring:
- **Scheffler:** Two consecutive weeks off (skipped Truist + Aronimink T14). Rested but form window thin. Monitor R1.
- **Morikawa:** Back injury. WD Truist, T55 Aronimink (gate cleared R1, back impacted all 4 rounds). Health gate must be reassessed before Byron Nelson. Check injury reports.
- **Young:** R4 74 Truist + T26 Aronimink (E par). Two consecutive Sunday failures. Sunday conversion now a confirmed risk variable, not a flag.
- **Hovland:** Putting on bentgrass confirmed liability at both Truist (T31) and Aronimink (CUT). Less relevant on TPC Craig Ranch — check surface type.
- **Schauffele:** T60 Truist + T7 Aronimink. Mixed — Aronimink approach fired, Truist approach faded. Net: adequate.
- **Theegala:** 69th Truist + T60 Aronimink. Red flag form entering Byron Nelson.
- **Matsuyama:** 71st Truist (dead last) + T26 Aronimink. Form heading wrong direction.
- **Reitan:** WON Truist, T44 Aronimink. Byron Nelson is his second event since winning — high variance, debut context applies.
- **Rahm:** T2 Aronimink (−6) at 35% recency weight. LIV 0.6x applies to all other form window events.
- **McIlroy:** T7 Aronimink + T19 Truist. Back-to-back majors momentum carrying. R3 blowup pattern (75 at Truist, 74 at Aronimink R1) is a noted concentration variable.

---

Begin with Step 1 — Venue DNA profile for TPC Craig Ranch / CJ CUP Byron Nelson. Search for current 2026 course conditions, typical winning score range, and historical winner trait data before building the weight matrix.

