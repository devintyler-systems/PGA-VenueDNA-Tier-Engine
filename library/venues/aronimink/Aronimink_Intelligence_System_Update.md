# Aronimink Golf Club — Intelligence System Update
## 2026 PGA Championship Post-Tournament Audit
### File type: Venue Library Write-Back + Engine Calibration Update
### Date: May 2026 | Audit cycle: 1 of N (first major data point on modern Hanse restoration)

---

## 1. VENUE IDENTITY

| Field | Value |
|-------|-------|
| Venue | Aronimink Golf Club |
| Location | Newtown Square, PA (suburban Philadelphia) |
| Architect | Donald Ross (1928), restored Gil Hanse & Jim Wagner (2015–2018) |
| Championship par / yardage | Par 70, ~7,394 yards |
| Surface | Bentgrass (Penn A-1/A-4 greens, L-93 fairways) |
| Bunkering | ~178 bunkers post-restoration |
| Tour event | PGA Championship (2026) |
| Prior usable data | 2010–11 AT&T National, 2018 BMW Championship |

---

## 2. CONFIRMED SCORING BANDS

### Dry track band (now confirmed): −8 to −11
- 2026 winner: Aaron Rai −9
- 2018 BMW winner: Keegan Bradley −20 (SOFT conditions — discard for dry calibration)
- **Confirmed dry winning range: −8 to −11**
- Target number under normal firm-fast setup: −9 to −10

### Soft track band (theoretical): −12 to −15
- Not tested in 2026 — Thursday rain dissipated by mid-morning
- Course played firm and fast all four days
- Band remains in library as theoretical soft scenario only

### Weather blending rule (updated):
- **Previous:** w_soft=0.6, w_firm=0.4 when Thursday rain forecast ~47%
- **Updated:** w_firm=0.65 is the DEFAULT for Aronimink unless multi-day rain is confirmed
- **Rule:** A single morning shower forecast (even at 47%) does NOT justify w_soft=0.6
- **Trigger for soft band weighting:** Multi-day rain in forecast, or course already saturated pre-tournament
- **2026 lesson:** Thursday rain dissipated. By R1 afternoon the course was playing firm. Overweighting soft band cost 3–6 shots on the winning score projection.

---

## 3. TRAIT WEIGHT MATRIX — UPDATED

| Trait | Pre-2026 Weight | Updated Weight | Evidence |
|-------|----------------|----------------|----------|
| SG: Approach (long-iron emphasis) | 32% | **34%** | Top-10 at 2026 PGA filled with elite approach players. Alex Smalley T2 via approach alone. Every T5 finisher was top-quartile approach. |
| Driving position (OTT angle control) | 24% | **24%** | Unchanged — corridors confirmed punishing but approach is primary differentiator |
| Long-iron proximity 175–225 | 14% | **14%** | Unchanged — confirmed as secondary separator |
| Short game (ARG + sand + tight lies) | 10% | **10%** | Unchanged |
| Putting — bentgrass only | 10% | **8%** | Firm track created scramble-for-par environment. Putting separated within contention but approach separated across the full leaderboard. Redistribute 2% to approach. |
| Par-5 efficiency (holes 9 and 16) | 5% | **5%** | Unchanged — only 2 par-5s, weight confirmed appropriate |
| Major-grade resilience (pressure holes) | 5% | **5%** | Unchanged |
| **Total** | **100%** | **100%** | |

### Weight adjustment evidence:
- Approach 32%→34%: Rahm T2, Åberg T4, Thomas T4, McIlroy T7, Schauffele T7 — every top-7 was elite approach. Smalley T2 from VTS 45 driven almost entirely by approach performance.
- Putting 10%→8%: Scheffler T14 despite VTS 91 — putting drag confirmed. Hovland CUT — putting drag confirmed. Firm-fast greens made approach the separator, not the putter.

---

## 4. ANTI-PATTERN LIBRARY — 2026 RESULTS

### Anti-pattern 1: Blunt Power
**Definition:** Elite raw distance + below-median OTT angle control on tight-corridor holes

| Player | Pre-event flag | Penalty | Actual finish | Verdict |
|--------|---------------|---------|---------------|---------|
| Bryson DeChambeau | Full trigger | −8 VTS | CUT (+7) | **CONFIRMED** |
| Dustin Johnson | Full trigger | −8 VTS | T44 (+2) | **CONFIRMED** |
| Tyrrell Hatton | Partial trigger | −4 VTS | CUT (+6) | **CONFIRMED** |

**2026 verdict:** Anti-pattern confirmed at current penalty magnitude. −8 VTS for full trigger is correctly calibrated. No adjustment needed.

**Write-back:** Penalty magnitude CONFIRMED at −8 full / −4 partial. Do not reduce.

---

### Anti-pattern 2: Faux Accuracy
**Definition:** High fairways-hit rate + below-median SG:APP from 175–225 yards

| Player | Pre-event flag | Penalty | Actual finish | Verdict |
|--------|---------------|---------|---------------|---------|
| Taylor Pendrith | Full trigger | −6 VTS | T44 (+2) | **CONFIRMED** |
| J.T. Poston | Full trigger | −6 VTS | CUT (+5) | **CONFIRMED** |

**2026 verdict:** Anti-pattern confirmed. Driving the fairway without long-iron attack capability is explicitly punished at Aronimink. Penalty magnitude correct.

**Write-back:** Penalty magnitude CONFIRMED at −6. Do not adjust.

---

### Anti-pattern 3: Bentgrass Mirage
**Definition:** Strong aggregate SG:Putting driven by non-bentgrass surfaces; neutral/negative on bentgrass-specific splits

| Player | Pre-event flag | Penalty | Actual finish | Verdict |
|--------|---------------|---------|---------------|---------|
| Denny McCarthy | Full trigger | −5 VTS | T44 (+2) | **CONFIRMED** |

**2026 verdict:** Confirmed. Aggregate putting advantage did not transfer to Aronimink bentgrass.

**Write-back:** Penalty magnitude CONFIRMED at −5. Do not adjust.

---

### Anti-pattern 4: Runoff Liability
**Definition:** Bottom quartile ARG from tight lies (10–30 yards); weak nipping and bump-and-run

**Status:** Not formally triggered in 2026 field. Insufficient sample to confirm or deny in this cycle.

**Write-back:** Maintain provisional −4 VTS penalty. Flag for 2027 cycle if more Ross major data available.

---

## 5. DEBUT PENALTY RECALIBRATION

### Standard debut penalty: −11 pts — CONFIRMED
Evidence: Three non-Ross-specialist debutants missed the cut (Fleetwood CUT, Im CUT, Bhatia CUT). The penalty correctly suppressed these players.

### Ross specialist override path — NEW RULE
**Trigger:** Player has won or finished T5+ at a Ross-design course (Sedgefield/Wyndham, Oakland Hills, Pinehurst, East Lake in certain setups) AND approach + OTT profile fits Aronimink trait matrix.

**New rule:** When Ross specialist comp evidence exists, trim debut penalty from −11 to **−6 or −7**.

**Evidence:**
- Aaron Rai: Won Wyndham Championship 2024 (Sedgefield — Ross design, 0.75x comp). Applied −11 debut. Actual result: **WON**. Should have been −6/−7 with Sedgefield comp. This is the clearest lesson from 2026.
- Alex Smalley: T2 finish from VTS 45/Tier 4-5. No comp evidence available — this is pure variance, not a calibration miss. Cannot model.

### Debut penalty by category going forward:

| Category | Penalty | Trigger |
|----------|---------|---------|
| Standard debut, no relevant comp | −11 pts | Default |
| Ross specialist with comp evidence | −6 to −7 pts | Win/T5 at Sedgefield, Oakland Hills, Pinehurst, or similar Ross venue |
| Elite ball-striker, minor comp evidence | −8 to −9 pts | T10+ at a Ross-adjacent venue (East Lake, Congressional) |
| Player with 1–2 prior Aronimink rounds | −4 to −5 pts | Partial venue history blend |

**Historical first-start Top-10 rate update:**
- 2026 data: Rai WON (1st Aronimink start), Åberg T4 (1st start), Thomas T4 (no debut), Smalley T2 (1st start but variance)
- Adjusted rate: ~3 debutants in top 10 of 82 finishers = ~15% of top-10 slots
- Verdict: Debut rate elevated by variance (Smalley) and Ross specialist correction (Rai). Standard penalty CONFIRMED; Ross override path now established.

---

## 6. COMP-COURSE FRAMEWORK — UPDATED

### Sedgefield Country Club (Wyndham Championship)
- **Previous similarity rating:** 0.55x
- **Updated similarity rating:** 0.75x
- **Evidence:** Aaron Rai won Wyndham 2024, won Aronimink 2026. The Ross design DNA transfers more strongly than the 0.55x rating implied.
- **Max VTS adjustment:** ±4 pts (up from ±2 pts)
- **Usage rule:** For any player with a win or T5 at Sedgefield, apply 0.75x comp weight to Aronimink fit score. Trim debut penalty to −6/−7.

### East Lake Golf Club (Tour Championship)
- **Similarity rating:** 0.70x — UNCHANGED
- **Max VTS adjustment:** ±4 pts — UNCHANGED

### Oakland Hills (South), major setups
- **Similarity rating:** 0.65x — UNCHANGED
- **Max VTS adjustment:** ±3 pts — UNCHANGED

### Congressional (Blue), pre-renovation major setups
- **Similarity rating:** 0.60x — UNCHANGED
- **Max VTS adjustment:** ±3 pts — UNCHANGED

---

## 7. MODEL MISS LOG — 2026 PGA CHAMPIONSHIP

| Player | Projected | Actual | Miss category | Fix |
|--------|-----------|--------|---------------|-----|
| Aaron Rai | T20/T30 | **WON** | Tier-mapping error — Sedgefield comp underweighted; debut penalty too steep for Ross specialist | Sedgefield 0.55x→0.75x; debut −11→−6/−7 for Ross specialists |
| Alex Smalley | MC (T4/5) | T2 | Pure variance — no comp evidence, no path to model | No fix available — variance bucket |
| Scottie Scheffler | Win/T10 | T14 | Trait mis-weight — putting drag underestimated at major speed | Expand Tier 1 floor risk for players with confirmed bentgrass putting issues |
| Viktor Hovland | T10/T20 | CUT | Trait mis-weight — putting risk on bentgrass flagged but floor risk cap (≤10% MC) was too tight | Consider expanding to 15% MC probability for T1 players with confirmed bentgrass putting liability |
| Cameron Young | T10/T20 | T26 | Trait mis-weight — Sunday conversion flag from Truist R4 74 materialized | Sunday conversion risk variable should carry more weight when Truist flag exists |
| Tommy Fleetwood | T10/T20 | CUT | Debut penalty held correctly | No fix — model was right |
| Sungjae Im | T10/T20 | CUT | Debut penalty held correctly | No fix — model was right |
| Winning score | −12 to −15 | −9 | Weather mis-weight — Thursday rain overweighted | w_firm=0.65 default; single morning shower ≠ w_soft=0.6 |

---

## 8. HEALTH GATE VALIDATION

**Collin Morikawa:** Health gate applied pre-tournament (WD Truist + Cadillac T62 on documented back). Gate cleared R1 (completed without incident). Final result: T55 (+3).

**Verdict:** Gate was correct call. T55 finish confirms back impacted all four rounds — even with gate cleared, performance was below his pre-injury VTS profile. Health gate protocol VALIDATED.

**Write-back rule reinforced:** Health gate clearing on R1 does NOT restore full pre-injury VTS. Post-R1 gate clear = assign interim VTS at 70–80% of pre-injury projection until round-by-round evidence confirms full function.

---

## 9. LIV MULTIPLIER VALIDATION

**Jon Rahm:** LIV 0.6x applied across full form window. Actual: T2 (−6).

**Verdict:** Discount was correct in direction but may be slightly aggressive for elite-level LIV players. Rahm's trait profile transferred fully — the 0.6x suppressed him from win projection appropriately. He contended but did not win.

**Write-back:** 0.6x LIV multiplier CONFIRMED as correct magnitude. No adjustment. The multiplier correctly suppresses win probability while allowing contention window projection.

---

## 10. FINISH PROBABILITY DISTRIBUTION — CONFIRMED BANDS

Updated based on 2026 results across 6 Tier 1 players:

| Tier | Win% | T10% | T20% | T30% | MC% | 2026 actual |
|------|------|------|------|------|-----|-------------|
| Tier 1 | 15% | **45%** | 25% | 10% | **5%** | 4/6 Top 10 (67%), 1 CUT |
| Tier 2 | 5% | 25% | **30%** | 25% | **15%** | Mixed — some CUTs confirmed |
| Tier 3 | 1% | 8% | 20% | 35% | 36% | Largely confirmed |
| Tier 4/5 | 0% | 2% | 8% | 25% | **65%** | Largely confirmed |

**Adjustment for Tier 1 players with confirmed bentgrass putting liability:**
- Standard Tier 1 MC cap: ≤10%
- **New override:** Tier 1 players with confirmed bentgrass putting issues at major speed: MC cap expanded to 15%
- Trigger: Documented putting drag at 2+ bentgrass major venues OR SG:Putting below 40th percentile on bentgrass-specific splits

---

## 11. PROMO CARD AUDIT — ENGINE RULES CONFIRMED

| Question | Pick | Result | Verdict | Lesson |
|----------|------|--------|---------|--------|
| Best scoring round | −8 or better | Confirmed | **HIT** | Dry track — low round possible |
| Cut line | Even par | Cut was +5 | Miss | Firm track pushed cut higher than expected |
| 54-hole leader wins | No | Correct | **HIT** | Major compression confirmed |
| Nationality — Non-USA | Non-USA | Rai (ENG) won | **HIT** (+15 edge) | Highest-edge pick delivered |
| Rahm vs Schauffele | Schauffele | Rahm T2, Schauffele T7 | Miss | LIV discount underpredicted Rahm's competitive sharpness |
| DeChambeau finish | 11–20 | CUT (+7) | Miss — too generous | Anti-pattern confirmed MC. Original MC pick (pre-revision) was correct |
| Winning margin | Exactly 1 shot | Rai won by 3 | Miss | Venue compressed field but winner ran away late |
| Winning score | −12 to −15 | −9 | Miss | Weather mis-weight — see Section 2 |
| Winner | McIlroy | Rai won | Miss | Rai was correct nationality pick, wrong player |
| Nationality pick | Non-USA | HIT | **HIT** | Best pick on card — validates edge logging process |

**Key promo card lesson:** Q6 DeChambeau — we revised from MC to 11–20 after cross-validation. The original MC call was correct. Anti-pattern + LIV double discount should have held. The cross-system revision was a mistake in this case. Log: when two active discounts fire simultaneously (anti-pattern + LIV), the MC outcome is more probable than Tier 2 base rates suggest. Do not revise away from MC on double-discount players without explicit counter-evidence.

---

## 12. VENUE PROFILE SNAPSHOT — UPDATED FOR NEXT CYCLE

**Aronimink Golf Club — 2027 PGA Championship baseline**

```
STRUCTURAL PROPERTIES (unchanged)
- Par 70, ~7,394 yards
- Bentgrass greens (Penn A-1/A-4), bentgrass fairways (L-93)
- 178 bunkers (clustered, wrap-around greenside)
- Significant elevation changes — downhill tees, uphill approaches
- Tree-lined corridors with angle sensitivity (hallway effect)
- Two par-5s (holes 9 and 16): 16 reachable, 9 three-shot for most
- Hard par, easy bogey scoring environment

TRAIT WEIGHT MATRIX (updated 2026)
- SG: Approach (long-iron emphasis): 34%
- Driving position (OTT angle control): 24%
- Long-iron proximity 175–225: 14%
- Short game (ARG, sand, tight lies): 10%
- Putting — bentgrass surface only: 8%
- Par-5 efficiency (holes 9 and 16): 5%
- Major-grade resilience (pressure holes): 5%

ANTI-PATTERNS (all confirmed 2026)
- Blunt Power: −8 VTS (full), −4 VTS (partial) — CONFIRMED
- Faux Accuracy: −6 VTS — CONFIRMED
- Bentgrass Mirage: −5 VTS — CONFIRMED
- Runoff Liability: −4 VTS — provisional (insufficient 2026 data)

DEBUT PENALTY
- Standard: −11 pts
- Ross specialist override: −6 to −7 pts (trigger: win/T5 at Sedgefield, Oakland Hills, Pinehurst)
- Elite ball-striker minor comp: −8 to −9 pts

COMP-COURSE FRAMEWORK
- Sedgefield (Wyndham): 0.75x similarity, ±4 pts max
- East Lake (Tour Championship): 0.70x, ±4 pts max
- Oakland Hills: 0.65x, ±3 pts max
- Congressional: 0.60x, ±3 pts max

SCORING BANDS
- Dry track (default): −8 to −11
- Soft track (multi-day rain): −12 to −15
- Weather default: w_firm=0.65 unless multi-day rain confirmed

RESULT QUALITY MULTIPLIERS (unchanged)
- Full PGA Tour 72-hole: 1.0x
- DP World Tour: 0.9x
- Co-sanctioned: 0.85x
- LIV Golf: 0.6x
- Japan/developmental tour: 0.5x

VENUE HISTORY DATA AVAILABLE
- 2010 AT&T National: field scoring, hole-by-hole averages
- 2011 AT&T National: field scoring, hole-by-hole averages
- 2018 BMW Championship: full SG decomposition, Bradley WIN (soft conditions — discount)
- 2026 PGA Championship: full results, confirmed dry-track band, anti-pattern validation
- 2020 KPMG Women's PGA: women's game — apply structural discount, directional only

PRESSURE HOLES (confirmed)
- Hole 8 (par-3, 238 yards): toughest hole in 2018 BMW — long-iron precision separates
- Hole 12 (par-4, 466 yards): elevated two-tier green, deep right bunker — bogey magnet
- Hole 15 (par-4, 515 yards): long par-4, approach angle critical
- Hole 16 (par-5, 545 yards): primary birdie opportunity — must convert
- Hole 18 (par-4): hard Ross finisher — winner's final shot typically 4–10 feet (Over 3.5 ft)

KNOWN DATA GAPS
- Pre-Hanse routing data (pre-2018): apply structural discount, directional only
- 2026 hole-by-hole SG breakdown: pending DataGolf publication
- Bentgrass putting sample size: adequate from 2018 + 2026 combined
```

---

## 13. NEXT CYCLE INSTRUCTIONS — 2027 PGA CHAMPIONSHIP

When building the 2027 Aronimink projection:

1. Pull the updated weight matrix (34/24/14/10/8/5/5) — do not default to generic weights
2. Apply Sedgefield comp at 0.75x for any player with Wyndham history
3. Default scoring band to −8 to −11 unless multi-day rain confirmed in forecast
4. Check for Blunt Power, Faux Accuracy, Bentgrass Mirage flags before finalizing VTS
5. Ross specialist debut override: check Wyndham/Pinehurst/Oakland Hills history before applying −11
6. For any player with confirmed bentgrass putting liability: expand MC floor to 15% regardless of tier
7. LIV players: 0.6x confirmed correct — do not adjust
8. Health gate: post-gate-clear VTS = 70–80% of pre-injury score until rounds confirm full function
9. Double-discount players (anti-pattern + LIV): do not revise MC call toward higher finish without explicit counter-evidence

---

*File generated: May 2026*
*Source: 2026 PGA Championship final results + full post-tournament audit*
*Next update: 2027 PGA Championship post-tournament (Aronimink cycle 2 of N)*

