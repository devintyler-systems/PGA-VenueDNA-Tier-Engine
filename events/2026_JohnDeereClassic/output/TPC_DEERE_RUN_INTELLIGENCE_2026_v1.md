# TPC DEERE RUN INTELLIGENCE — 2026 John Deere Classic
*PGA VenueDNA Tier Engine v1.1 | Venue File: 2026_v1 | Generated: 2026-07-02*

---

## VENUE LOCK — TPC Deere Run

| Field | Value | Source |
|---|---|---|
| Par | 71 | Championship routing |
| Yardage | 7,327 (DG: 7,133) | 2026 routing incl. Hole 4 +38 yd |
| Surface | Southshore Bentgrass / KBG+Fine Fescue rough | Venue file |
| Adj Score to Par | **-1.83** | DataGolf course table |
| Adj Par-5 Score | **-0.39 / round** | DataGolf |
| APP <150 SG | +0.024 | DataGolf less_150_sg |
| Fairway Width | 37.9 yd avg (moderate) | DataGolf fw_width |
| Miss-FW Penalty | 2.64% (low) | DataGolf miss_fw_pen_frac |
| Adj Penalties | 0.26 (low) | DataGolf adj_penalties |
| Adj GIR | 72.3% (high) | DataGolf adj_gir |

**Difficulty class:** Birdie-fest (easy). This is a conversion track — the player who cashes their birdie looks wins.

---

## WEATHER LOCK — soft_wet

- **Heat alert**: Extreme Heat Warning through Thursday night
- **Rain risk**: Friday afternoon through Saturday afternoon (delay risk: moderate)
- **Wind**: 10-15 mph, non-dominant
- **Course effect**: Softening through week; receptive greens after Friday rain
- **Best scoring day**: Sunday (cleaner weather, still warm, wind manageable)

**Weather modeling implications:**
- Reduced rollout lowers raw distance premium
- Receptive greens favor approach players and putters
- Par-5 scoring importance increased (soft fairways, stoppable approaches)
- Short-putt conversion remains highest-priority trait
- Lag putting mild bump on softer surfaces
- bomb_and_spray penalty softened (low OB/penalty at Deere even in wet conditions)

---

## TRAIT WEIGHT MATRIX (Weather-Adjusted Deere Seed)

| Trait | Weight | Justification |
|---|---|---|
| APP_Wedge | **0.18** | Dominant — DG less_150_sg=0.024; conversion track |
| APP_100_150 | **0.15** | Key iron-play bucket at short-iron birdie track |
| Putt_Short_Conv | **0.14** | Birdie cash-in; single most critical putting metric |
| OTT_Accuracy | **0.11** | Bentgrass FWs; soft week rewards FW-hitting |
| Putt_Lag | **0.10** | Bumped for soft/wet greens; distance control matters |
| Par5_Scoring | **0.10** | Boosted — DG adj_par5=-0.39; soft turf magnifies equity |
| APP_150_200 | **0.08** | Lower frequency; low_to_moderate long-iron demand |
| ARG_Rough | **0.07** | Moderate rough (rgh_diff=0.4) |
| OTT_Distance | **0.04** | Softened — reduced rollout on wet turf |
| ARG_Bunker | **0.03** | Low bunker exposure at Deere |

*Sum = 1.00. Dominant cluster (APP_Wedge + APP_100_150 + Putt_Short_Conv) = 0.47 of total weight.*

---

## ANTI-PATTERN DEFINITIONS

| Pattern | Severity Range (SG) | Trigger | Notes |
|---|---|---|---|
| poor_birdie_conv | -1.5 to -4.0 | PUTT_BirdieConv < p35 | Fatal at conversion birdie-fest |
| wedge_liability | -2.0 to -5.0 | APP_Wedge < p35 | Core scoring trait at Deere |
| rough_approach_liab | -1.0 to -2.5 | ARG_Rough < p30 | Moderate rough severity |
| bomb_and_spray | -1.0 to -2.5 | DD > p60 AND DA < p45 | **Softened** — miss_fw_pen_frac=0.0264 modest |

---

## VENUE DNA SNAPSHOT

- **Scoring profile**: Birdie-fest, par-5 leverage, wedge/short-iron scoring
- **Dominant trait**: Wedge/short-iron APP + short-putt conversion (~0.47 of total weight)
- **Variance class**: Standard (penalties exist but not dominant)
- **Comp courses**: TPC River Highlands, Colonial CC, Sedgefield CC
- **Course record**: 256 (-25)
- **Signature stretch**: Par-4 14, par-3 16 (over Rock River), par-5 17

---

## MODEL OUTPUTS — 2026 FIELD

**Model winner**: Koivun, Jackson (VTS: 85.1)

**Top-5 win probability:**
  1. Koivun, Jackson — 3.1%
  2. Griffin, Ben — 2.3%
  3. Wallace, Matt — 2.2%
  4. Kim, Tom — 2.1%
  5. Fowler, Rickie — 1.8%

**Tier 1 — Course Architects (2 players):**
Koivun, Jackson, Griffin, Ben

**Tier 2 — Contention Windows (40 players):**
Wallace, Matt, Kim, Tom, Fowler, Rickie, Gotterup, Chris, Bridgeman, Jacob, Bradley, Keegan, Bauchou, Zach, Cole, Eric, Bezuidenhout, Christiaan, Fisk, Steven, Suber, Jackson, Thorbjornsen, Michael, Poston, J.T., Kim, Michael, Mccarthy, Denny, Meissner, Mac, Homa, Max, Yellamaraju, Sudarshan, Finau, Tony, Spieth, Jordan, Greyserman, Max, Pendrith, Taylor, Brennan, Michael, Mitchell, Keith, Putnam, Andrew, Peterson, Paul, Eckroat, Austin, Ghim, Doug, Thompson, Davis, Mouw, William, Novak, Andrew, Olesen, Thorbjorn, Li, Haotong, Grillo, Emiliano, Kanaya, Takumi, Kuchar, Matt, Lipsky, David, Potgieter, Aldrich, Dumont De Chassart, Adrien, Johnson, Zach

**Tier distribution:**
  T1: 2 players — Course Architects
  T2: 40 players — Contention Windows
  T3: 67 players — Top-10 Range
  T4: 29 players — Cut-Line Players
  T5: 6 players — Course Mismatches

---

## DATA AUDIT NOTES

- Field: 144 players (john_deere_classic_2026_field.csv)
- SG 12M: 144 rows joined (field_player_Last12month_TrueSG_Data.csv)
- Fit-adj: 143 rows (1 player assigned median fit values; tpcdeererun_playerfitadj_predictedshotdistance.csv)
- CH: 144 rows (tpc_deere_run_CH.csv) — all field players have CH records
- Debut players (rounds_played=0): 24
- No separate 2026 DG performance file → form_vs_baseline=0 all players
- Missing sg_total_12m: 1 players

---

## SETUP CHANGE NOTE

**Hole 4**: Extended from 454 to 492 yards (+38 yd) for 2026 championship routing.
- Now a genuine par-4 approach challenge vs short-iron layup scenario
- Slightly increases APP_150_200 demand; no structural change to trait weight matrix
- Monitor hole-4 scoring vs DG par-4 baseline (-0.05/round) for week-1 calibration

---

*Scoring spec: v1.1 | Learning loop: v1.1 | Engine: PGA_VenueDNA_Tier_Engine_v1*

---

## POST-EVENT WRITE-BACK BLOCK — 2026 JDC Final Audit
*Appended: 2026-07-05 | Source: 2026_JDC_audit_postmortem.md | Confidence: HIGH*

### Venue DNA — Confirmed

**Birdie-fest conversion venue: CONFIRMED.**
Tournament scoring (-20 winner, -2 cut) validates the pre-tournament difficulty class. Par 5 holes (2, 10, 17) and short par-4 hole 14 were the primary birdie sources. Putting was the single strongest SG differentiator among top finishers (Hodges 1st: +8.93, Meissner 2nd: +8.41, Gotterup 5th: +5.40). Core DNA traits confirmed: APP_Wedge, Putt_Short_Conv, Par5_Scoring. No trait weight changes warranted from this event alone.

### Anti-Pattern Status

**bomb_and_spray — CONCEPT VALID. SIZING NOW SETUP-CONDITIONAL.**

| Player | Penalty Applied | Actual Finish | OTT SG | Conditions | Verdict |
|--------|----------------|---------------|--------|------------|---------|
| Gotterup | -2.67 SG | 1st (WON) | +5.41 (1st) | Soft/wet | OVER-PENALIZED |
| Meissner | -1.10 SG | T6 | +0.29 (38th) | Soft/wet | OVER-PENALIZED |
| Spieth | -1.24 SG | T58 | -0.95 (56th) | Soft/wet | CORRECT (direction validated) |

Write-back applied: on soft/wet Deere weeks — weekly FW% > 65%, rough_moisture_class = wet, or adj_penalties < 0.20 — reduce bomb_and_spray base penalty by **30–50%**. The concept is correct under standard dry conditions. Soft rough at Deere's already-low miss_fw_pen_frac (0.0264) materially neutralizes the structural punishment.

**rough_approach_liab — CONCEPT VALID. SIZING NOW SETUP-CONDITIONAL.**

| Player | Penalty Applied | Actual Finish | ARG/App SG | Conditions | Verdict |
|--------|----------------|---------------|------------|------------|---------|
| Suber | -1.11 SG | T6 | App +3.73 (16th) | Soft/wet | OVER-PENALIZED |
| Brennan | -1.39 SG | T33 | App +4.44 (13th) | Soft/wet | OVER-PENALIZED |
| Poston | -1.18 SG | T51 | App -2.11 (69th) | Soft/wet | CORRECT |
| Yellamaraju | -1.11 SG | CUT | N/A (cut) | Soft/wet | CORRECT (direction) |

Write-back applied: on soft/wet Deere weeks (same conditions class as bomb_and_spray modifier), reduce rough_approach_liab base penalty by **20–40%**. Low rough severity in wet conditions reduces the structural approach-from-rough demand.

### VHD Gate — Applied

VHD directional accuracy at ≥6 rounds in this event: 5/5 (100%). VHD with <6 rounds (Koivun, 4 rounds, VHD +0.024) produced the only Tier 1 failure (CUT). Write-back applied to scoring spec: VHD rounds < 6 caps contribution at ±1.0 VTS points and cannot support Tier 1. VHD rounds < 8 AND VHD ≤ +1.0 blocks Tier 1 by default.

### Tier 3 Probability Review — Monitoring Flag

5 of 11 top-10 finishers were Tier 3 players. VTS compressed Tier 3 ceiling too aggressively at this birdie-fest profile. No hard rule change applied — flagged for probability calibration review across 2+ birdie-fest events. At next Deere Run event, apply an explicit Tier 3 top-10 probability floor uplift if venue scoring profile is again classified birdie-fest.

### Venue File Status: 2026 Final

| Component | Status |
|-----------|--------|
| DNA traits | CONFIRMED — no weight changes |
| bomb_and_spray anti-pattern | VALID — soft-week modifier added |
| rough_approach_liab anti-pattern | VALID — soft-week modifier added |
| VHD gate | NEW RULE applied to scoring spec |
| Tier 3 probability floor | MONITORING — not yet adjusted |
| Comp courses | HOLD — needs 2+ events to recalibrate VFD at birdie-fest venues |
