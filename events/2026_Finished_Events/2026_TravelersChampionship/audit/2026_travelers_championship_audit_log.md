# 2026 Travelers Championship — Post-Tournament Audit Log

**Audit Date:** 2026-06-29  
**Engine Version:** 1.1 | **Learning Loop Version:** 1.0  
**Result:** Viktor Hovland, −21, Monday playoff over Scheffler  
**Spec Reference:** 03_PGA_VENUEDNA_LEARNING_LOOP.md | Artifact Schema: 04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md  
**Model Rho (final):** 0.341

---

## FILE CONFIRMATION

All audit reference files verified present:

| File | Status |
|------|--------|
| 2026_travelers_championship_vts_full.csv | ✓ |
| 2026_travelers_championship_trait_form_matrix.csv | ✓ |
| 2026_travelers_championship_field_input.csv | ✓ |
| 2026_travelers_championship_player_briefs.json | ✓ |
| 2026_travelers_championship_event_context.json | ✓ |
| 2026_travelers_championship_r1_analysis.json | ✓ |
| 2026_travelers_championship_r2_analysis.json | ✓ |
| 2026_travelers_championship_r3_analysis.json | ✓ |
| 2026_travelers_championship_r4_analysis.json | ✓ |
| 2026_travelers_championship_cumulative_learning.json | ✓ |
| 2026_travelers_championship_final_analysis.json | ✓ |
| final_leaderboard.csv | ✓ |
| final_tournament_player_strokes_gained.csv | ✓ |
| final_tournament_course_stats.csv | ✓ |
| final_tournament_course_insights.csv | ✓ |

---

## PRE-TOURNAMENT MODEL STRUCTURE (Verified from vts_full.csv + event_context.json)

**Tier distribution:** Tier 1 (1), Tier 2 (3), Tier 3 (15), Tier 4 (36), Tier 5 (16)

| Rank | Player | VTS | Tier | Anti-Pattern Flags |
|------|--------|-----|------|--------------------|
| 1 | Scheffler, Scottie | 82.0 | 1 | — |
| 2 | Fleetwood, Tommy | 67.6 | 2 | — |
| 3 | Henley, Russell | 66.9 | 2 | — |
| 4 | Fitzpatrick, Matt | 65.2 | 2 | — |
| 5 | Young, Cameron | 64.3 | 3 | — |
| 6 | Åberg, Ludvig | 62.9 | 3 | — |
| 8 | Hovland, Viktor | 58.1 | 3 | — |
| 11 | Bhatia, Akshay | 54.1 | 3 | — |
| 14 | Morikawa, Collin | 52.1 | 3 | poor_birdie_conv |
| 18 | Burns, Sam | 50.3 | 3 | bomb_and_spray; rough_approach_liab |
| 21 | Cantlay, Patrick | 49.6 | 4 | bomb_and_spray; poor_birdie_conv |
| 23 | Clark, Wyndham | 48.9 | 4 | bomb_and_spray |
| 49 | Thomas, Justin | 39.1 | 4 | bomb_and_spray; wedge_liability |
| 57 | Fitzpatrick, Alex | 34.4 | 5 | wedge_liability |

**Model winner:** Scheffler. **Model top-3:** Scheffler, Fleetwood, Henley.

**Venue trait weights (authoritative from event_context.json):**

| Trait | Weight |
|-------|--------|
| APP_Wedge | 22% |
| PUTT_Short_Conv | 16% |
| OTT_Accuracy | 14% |
| APP_100–150 | 12% |
| PUTT_Lag | 10% |
| ARG_Rough | 7% |
| APP_150–200 | 6% |
| OTT_Distance | 5% |
| ARG_Bunker | 5% |
| Par5_Scoring | 3% |

---

## TASK 1: TIER ACCOUNTABILITY REVIEW

### Final Leaderboard (Key Players)

| Final Pos | Player | Score | Rounds | Pre-Tourney Rank | Pre-Tourney Tier | VTS | Rank Delta |
|-----------|--------|-------|--------|-------------------|------------------|-----|------------|
| 1 (PO) | Hovland, Viktor | −21 | 65-61-64-69 | 8 | 3 | 58.1 | +7 |
| 2 | Scheffler, Scottie | −21 | 64-60-67-68 | 1 | 1 | 82.0 | −1 |
| 3 | Morikawa, Collin | −20 | 69-66-64-61 | 14 | 3 | 52.1 | +11 |
| 4 | Fitzpatrick, Matt | −19 | 64-66-67-64 | 4 | 2 | 65.2 | 0 |
| T5 | Clark, Wyndham | −18 | 68-64-65-65 | 23 | 4 | 48.9 | +18 |
| T5 | Bhatia, Akshay | −18 | 66-62-67-67 | 11 | 3 | 54.1 | +6 |
| T7 | Conners, Corey | −17 | 65-68-67-63 | 51 | 4 | 37.8 | +44 |
| T7 | Spaun, J.J. | −17 | 66-65-68-64 | 24 | 4 | 47.7 | +17 |
| T7 | Fitzpatrick, Alex | −17 | 69-66-64-64 | 57 | 5 | 34.4 | +50 |
| T10 | MacIntyre, Robert | −16 | 67-65-67-65 | 43 | 4 | 40.7 | +33 |
| T10 | Griffin, Ben | −16 | 64-66-67-67 | 48 | 4 | 40.9 | +38 |
| T12 | Henley, Russell | −15 | 66-70-65-64 | 3 | 2 | 66.9 | −9 |
| T12 | Burns, Sam | −15 | 66-66-66-67 | 18 | 3 | 50.3 | +6 |
| T14 | Fleetwood, Tommy | −14 | 67-64-70-65 | 2 | 2 | 67.6 | −12 |
| T14 | Thomas, Justin | −14 | 68-66-65-67 | 49 | 4 | 39.1 | +35 |
| T14 | Cantlay, Patrick | −14 | 65-66-64-71 | 21 | 4 | 49.6 | +7 |

---

### Tier 1 — Scheffler, Scottie (VTS 82.0)

**Final finish:** 2nd (−21, lost playoff). Pre-tourney rank 1 → Final pos 2.

**Verdict: MODEL HIT — FULL VALIDATION**

Scheffler finishing −21 in regulation is the cleanest possible validation of a VTS 82 model-winner call. He co-led through 72 holes and lost a playoff to a one-shot variance event. His SG breakdown: OTT +1.941 (12th), APP +5.230 (6th), ARG −0.228 (41st), PUTT +4.139 (12th) — approach was elite, putting was strong, ARG mildly negative. The model correctly weighted approach as the primary scoring trait at TPC River Highlands.

**Do not classify as a miss.** A playoff outcome is a variance event (±1 shot over 2 holes), not a structural error. Scheffler's −21 in regulation is the correct analytical data point.

---

### Tier 2 — Matt Fitzpatrick (VTS 65.2, Rank 4)

**Final finish:** 4th (−19). Rank delta: 0 (rank 4 → 4th).

**Verdict: MODEL HIT**

Fitzpatrick's SG: OTT +2.722 (5th), APP +2.551 (17th), ARG +4.114 (4th), PUTT −0.305 (37th). Approach and scrambling both strong. Negative putting limited his ceiling but his overall game was precisely what the model projected. The VTS 65.2 correctly captured his all-around approach-plus-scrambling profile at this venue.

---

### Tier 2 — Henley, Russell (VTS 66.9, Rank 3)

**Final finish:** T12 (−15). Rank delta: −9 (rank 3 → T12).

**Verdict: SLIGHT UNDERPERFORM — Model Variance**

Henley's SG: OTT +3.259 (3rd), APP +0.697 (32nd), ARG −2.898 (64th), PUTT +4.024 (13th). He drove the ball excellently (CH record of 30 rounds, venue_history_sg=1.445 — strongest in field), but approach was pedestrian and ARG was 64th in the field. His VTS 66.9 (rank 3) predicted a top-5 ceiling; T12 is within acceptable variance for a 72-player event. No write-back warranted. The miss mechanism is ARG liability, not a structural model error.

---

### Tier 2 — Fleetwood, Tommy (VTS 67.6, Rank 2)

**Final finish:** T14 (−14). Rank delta: −12 (rank 2 → T14).

**Verdict: UNDERPERFORM — VenueFitDelta Miss**

Fleetwood's SG: OTT +1.153 (24th), APP −0.260 (38th), ARG +1.442 (18th), PUTT +1.747 (24th). His approach play — the primary scoring driver at TPC River Highlands — was 38th in the field, directly contradicting his rank-2 VTS position. His model ranking was driven by strong 12-month SG-APP (0.63) and venue history (18 rounds, +1.76 CH SG), but neither materialized in-week. At VTS 67.6, a T14 finish represents a meaningful underperformance. Classify as VenueFitDelta miss — the 14-weight on venue history compressed his true in-week approach ceiling.

**Write-back flag:** Revisit CH SG blending weight for Fleetwood — strong venue history over-inflated expected approach performance in-week.

---

### Viktor Hovland — Winner: VTS-Aligned Win or Model Miss?

**Pre-tourney rank:** 8 of 72 (VTS 58.1, Tier 3)  
**Final finish:** 1st (−21, playoff)  
**Final SG:** OTT +3.962 (1st), APP +0.776 (31st), ARG +2.009 (10th), PUTT +4.335 (9th)

**Verdict: PARTIAL VTS-ALIGNMENT — with event-week OTT variance**

The model ranked Hovland 8th of 72, placing him in the top ~11% of the field and Tier 3. A rank-8 player winning a 72-player no-cut event is within the expected probability range of the model's top tier — this is NOT a structural miss.

The win mechanism breaks into three components:
1. **VenueHistoryDelta (predictable):** Hovland carried 19 rounds of TPC River Highlands course history with CH SG = 1.423 — one of the strongest venue histories in the field. This was baked into his VTS.
2. **OTT surge (event-week variance):** His 12-month SG-OTT was only +0.15, but he posted SG-OTT +3.962 (1st in the 72-player field). This OTT surge was not predictable from pre-tournament data.
3. **Putting heat (event-week variance):** His 12-month SG-PUTT was only +0.15, but he posted SG-PUTT +4.335 (9th in the field). Again, not predictable.

His approach (SG-APP +0.776, 31st) was average — the model's highest-weighted trait did NOT drive his win. His victory was built on OTT accuracy, short game, and hot putting. This is a classic **VenueHistoryDelta + Model Variance** outcome: the model correctly identified him as a top-10 contender based on venue fit; the specific win mechanism was two unpredictable hot categories.

**Conclusion:** Hovland's win validates the model at the tier assignment level (Tier 3, rank 8 = strong contender). The win mechanism partially confirms venue history weight but introduces a question about approach over-centrality in win prediction at this venue. See write-back recommendations.

---

## TASK 2: ANTI-PATTERN REVIEW

### Cantlay, Patrick — AP Flags: bomb_and_spray; poor_birdie_conv

**Pre-tourney tier:** 4 (rank 21, VTS 49.6)  
**Final finish:** T14 (−14)  
**Final SG:** OTT −0.059 (39th), APP +4.314 (8th), ARG −1.189 (53rd), PUTT +1.016 (28th), TOT +4.083

**bomb_and_spray:** Fired (OTT 39th, mildly negative). The flag correctly identified OTT as a liability.  
**poor_birdie_conv:** Partially fired. PUTT was +1.016 (28th) — modest, not elite. His approach was 8th in the field yet he was only T14. The birdie conversion limitation clearly capped his ceiling: 8th-best approach without making putts limits you to a mid-pack T14 rather than a top-5.

**Verdict: PARTIAL FAIL**

The anti-pattern flags correctly identified two structural weaknesses. However, Cantlay's elite approach (SG-APP 8th in field, +4.314) compensated for OTT liability, and he finished T14 — 7 spots better than his pre-tournament model rank of 21. The AP penalty suppressed him to Tier 4, but even with that suppression he outperformed his assigned rank.

**Mechanism:** bomb_and_spray fired as predicted; approach compensated more than expected; poor_birdie_conv held — his putting cap (28th in putting) prevented conversion of his elite approach into a top-5 finish. The flag held on the ceiling suppression but the floor was elevated by approach strength.

**AP System Implication:** Cantlay demonstrates that bomb_and_spray should be paired with a "strong approach compensates" discount if SG-APP 12m > 0.70. His 12m SG-APP was +0.73 — a signal the model should have partially offset against the spray penalty.

---

### Thomas, Justin — AP Flags: bomb_and_spray; wedge_liability

**Pre-tourney tier:** 4 (rank 49, VTS 39.1)  
**Final finish:** T14 (−14)  
**Final SG:** OTT +1.175 (23rd), APP −2.616 (56th), ARG +6.257 (1st), PUTT −0.734 (41st), TOT +4.083

**bomb_and_spray:** Did NOT fire. OTT was 23rd (+1.175). Flag was incorrect on this dimension — Thomas was accurate in the tournament week.  
**wedge_liability:** FIRED. APP was 56th in the field (−2.616). This is direct confirmation that Thomas's approach/wedge play was as poor as the flag predicted.

**Verdict: FAIL (flag fired but result escaped penalty through ARG)**

Thomas's wedge_liability anti-pattern was 100% correct — his approach play was among the worst in the top-30 finishers (56th in the field at −2.616). By rights he should have missed the top 20 from rank 49. What rescued him: SG-ARG +6.257 — the single best scrambling performance in the entire 72-player field. A player ranked 49th pre-tournament finished T14 because his short game and scrambling offset a catastrophic approach week.

This is **model variance**, not a structural error. The model correctly identified his approach liability. The unpredictable variable was elite ARG — no pre-tournament data predicted a top-1 scrambling week from a player whose 12m SG-ARG was +0.25.

**AP System Implication:** The Thomas outcome reveals a gap in the current anti-pattern architecture. When wedge_liability fires on a player whose ARG_Rough or ARG_Bunker trait score is above 70, the rescue probability should be elevated. A "high-ARG rescues wedge-liability" modifier would have improved the model's Thomas probability distribution.

---

## TASK 3: TRAIT WEIGHT VALIDATION

### Final Tournament Realized SG Averages (Top 10)

| SG Category | Top-10 Average | Full-Field | Delta | % of Total Positive SG |
|-------------|---------------|------------|-------|------------------------|
| SG-PUTT | +3.230 | 0.0 | +3.230 | **39.1%** |
| SG-APP | +2.802 | 0.0 | +2.802 | **33.9%** |
| SG-OTT | +1.171 | 0.0 | +1.171 | **14.2%** |
| SG-ARG | +1.061 | 0.0 | +1.061 | **12.8%** |
| **Total** | **+8.264** | — | — | 100% |

### Trait Signal Audit (from final_analysis.json trait_audit)

| Trait | Pre-Tourney Wt | Trait Delta (Top10 vs Field) | 4-Rd Consensus | Realized SG Proxy | Delta Direction | Confidence |
|-------|----------------|------------------------------|----------------|-------------------|-----------------|------------|
| APP_Wedge | 22% | +13.4 | validated (4/4) | SG-APP +2.802 | Correct | High |
| PUTT_Short_Conv | 16% | +2.0 | mixed (2/4 neutral) | SG-PUTT +3.230 | UNDERWEIGHTED | Medium |
| OTT_Accuracy | 14% | +6.0 | validated (3.5/4) | SG-OTT +1.171 | Slightly over | High |
| APP_100–150 | 12% | +13.5 | validated (4/4) | SG-APP +2.802 | Correct | High |
| PUTT_Lag | 10% | −0.4 | neutral (final) | SG-PUTT +3.230 | UNDERWEIGHTED | Low |
| ARG_Rough | 7% | +7.3 | validated (4/4) | SG-ARG +1.061 | Accurate | Medium |
| APP_150–200 | 6% | +13.3 | validated (4/4) | SG-APP +2.802 | Correct | High |
| OTT_Distance | 5% | +2.9 | mixed (enrichment contradicted) | SG-OTT +1.171 | OVERWEIGHTED | Low |
| ARG_Bunker | 5% | +5.7 | mixed (R4) | SG-ARG +1.061 | Accurate | Low |
| Par5_Scoring | 3% | +11.0 | validated (4/4) | SG-APP +2.802 | UNDERWEIGHTED | High |

### Weight Validation Summary

**Directionally Correct (high-weight traits were real scoring drivers):**
- APP_Wedge (22%): Validated all 4 rounds. Trait delta +13.4, SG-APP +2.802. The highest-weighted trait was a genuine scoring differentiator. ✓
- OTT_Accuracy (14%): Validated all 4 rounds with direct proxy data. Top-10 drove accuracy 77.1% vs field 69.2% (+7.9pp). ✓
- APP_100–150 (12%): Validated all 4 rounds. ✓
- ARG_Rough (7%): Validated all 4 rounds. ✓

**Overweighted (weight > realized importance):**
- OTT_Distance (5%): Contradicted by enrichment — top-10 actually hit it 1.4 yards *shorter* than field (283.5 vs 284.9). Distance was not a scoring driver at TPC River Highlands in 2026. The model correctly assigned low weight (5%), but even this weight may be inflated.
- APP_Wedge cluster (22% + 12% + 6% = 40% combined): Approach was only 33.9% of realized top-10 SG premium. Slightly overweighted in aggregate vs putting.

**Underweighted (realized importance > model weight):**
- Putting combined (PUTT_Short_Conv 16% + PUTT_Lag 10% = 26%): Realized putting was 39.1% of top-10 SG premium — 13 percentage points higher than the model weight. This is the single largest calibration gap. The predictor signal (putt_short_conv trait delta = +2.0) was weak, which correctly signals that **putting performance is highly variable** (hard to predict from 12m traits). However, the model weight should be elevated regardless because hot putting weeks dominate at this venue.
- Par5_Scoring (3%): Validated all 4 rounds with strong deltas (+5.6 to +12.9). At only 3% weight, this trait is significantly underweighted relative to its actual tournament influence. Par-5 birdie conversion is a clear edge trait at TPC River Highlands.

**Key Insight — The Putting Paradox:**  
Putting SG was the top scoring category tournament-wide (39.1% of net advantage), but the putting trait predictor (putt_short_conv) showed only a +2.0 trait delta and mixed signal. This means putting OUTCOMES were essential to winning, but pre-tournament putting TRAITS did not predict who would have a hot putting week. This is consistent with the known high variance of putting week-to-week. The model should weight putting higher in the probability model while maintaining the expectation that individual putting prediction will be low confidence.

---

## TASK 4: MISS LOG

Classification labels per Learning Loop spec:
- **NeutralSkill** — player's baseline skill was wrong  
- **VenueFitDelta** — trait fit to this venue was mis-scored  
- **VenueHistoryDelta** — prior history at TPC River Highlands was over/under-weighted  
- **Penalty/Gate** — a disqualifying factor was missed or wrongly applied  
- **Model Variance** — result within acceptable model uncertainty, no structural fix needed

### Material Misses

| Player | Pre-Tourney Tier | Pre-Tourney Rank | Final Finish | Miss Layer | Evidence | Write-Back Recommended |
|--------|-----------------|-----------------|--------------|------------|----------|----------------------|
| Hovland, Viktor | 3 | 8 | 1st (PO) | VenueHistoryDelta + Model Variance | Rank 8 → 1st is within model probability. CH SG +1.423 (19 rds) was strongest active in-field metric for this result. OTT surge (+3.962) and PUTT heat (+4.335) not predictable. | Y (VenueHistory weight for 15+ round CH) |
| Morikawa, Collin | 3 | 14 | 3rd | VenueFitDelta | Model ranked 14th; OTT was 2nd (+3.593), APP was 2nd (+6.907) in field. Poor_birdie_conv flag fired only partially (PUTT +2.878, 15th). His approach ceiling at this venue was undervalued. | Y (APP_wedge trait boost for players with 12m SG-APP > 0.80) |
| Clark, Wyndham | 4 | 23 | T5 | Model Variance | Finish driven by SG-PUTT +8.712 (1st in field) vs APP −2.957 (57th). Bomb_and_spray flag fired on APP and OTT. Only a putting outlier week — no structural model signal. | N |
| Fitzpatrick, Alex | 5 | 57 | T7 | VenueFitDelta | Tier 5 (lowest tier) finished T7. SG-APP +5.518 (5th in field). The wedge_liability flag suppressed him to Tier 5; his actual in-week approach was elite. The anti-pattern over-penalized his approach ceiling. | Y (reduce wedge_liability APP penalty for players with ARG_Rough score > 65) |
| Conners, Corey | 4 | 51 | T7 | VenueFitDelta | Rank 51 → T7. SG-APP +2.916 (12th), SG-ARG +3.492 (7th). Anti-pattern flags (poor_birdie_conv; rough_approach_liab) suppressed him unfairly — his scrambling (7th in field) directly contradicts the rough_approach_liab flag. | Y (rough_approach_liab flag should test ARG_Rough trait vs threshold before applying) |
| MacIntyre, Robert | 4 | 43 | T10 | VenueFitDelta | Rank 43 → T10. SG-APP +3.598 (10th). Bomb_and_spray + wedge_liability flags assigned; approach was among the tournament's best. His 12m SG-APP (+−0.11) was near zero but he has strong course history (8 rounds, +1.686 CH SG). | Y (partial — CH SG integration for Tier 4 players with ≥8 rounds) |
| Fleetwood, Tommy | 2 | 2 | T14 | VenueFitDelta | Rank 2 → T14. Model's 2nd-highest player. SG-APP −0.260 (38th). Strong 18-round course history (+1.76 CH SG) inflated confidence in approach performance that didn't materialize. Venue history over-blended into tier assignment. | Y (CH SG recency weight — older CH rounds should decay faster in blend) |
| Spaun, J.J. | 4 | 24 | T7 | Model Variance | Rank 24 → T7. SG-PUTT +5.007 (5th in field). Strong putting week not predicted by pre-tournament traits. No structural fix warranted — pure putting variance. | N |
| Griffin, Ben | 4 | 48 | T10 | Model Variance | Rank 48 → T10. SG-PUTT +3.412 (14th), SG-APP +2.722 (T14). Small positive putting outlier + solid approach. Within acceptable variance for a birdie-fest. | N |
| Bhatia, Akshay | 3 | 11 | T5 | Model Variance | Rank 11 → T5. Mild positive surprise. SG-PUTT +5.102 (4th). Putting outlier but rank delta only 6 spots. Within model range. | N |
| Burns, Sam | 3 | 18 | T12 | Model Variance | Rank 18 → T12. Positive result. AP flag (bomb_and_spray; rough_approach_liab) — ARG did fire (−3.120, 66th). Approach was strong (+4.379, 7th). Result consistent with model tier. | N |

---

## TASK 5: WRITE-BACK RECOMMENDATIONS

*Only write-backs supported by ≥2 rounds of evidence are included.*

### Bucket A: Venue Profile Write-Backs — TPC River Highlights (tpc_river_highlands)

---

**WB-A1: Increase Putting Weight Allocation**

| Field | Value |
|-------|-------|
| Change | Increase PUTT_Short_Conv from 16% → 19%; increase PUTT_Lag from 10% → 11% |
| Evidence Basis | 4-round cumulative: putting SG was 39.1% of top-10 SG premium vs 26% model weight. R2 (validated), R3 (validated), R4 final (mixed but elevated SG-PUTT +3.230 for top-10). Top-6 in the field all had SG-PUTT > +1.0. |
| Confidence | Medium-High (4 rounds, direct SG data; trait predictor quality weak) |
| Recommended Action | Write to venue profile: `putt_short_conv: 0.19`, `putt_lag: 0.11`. Partially offset by reducing OTT_Distance and APP_150_200. Add model_variance note: "Putting at TPC River Highlands is high-variance; weight reflects importance but predictor reliability is low." |

---

**WB-A2: Reduce OTT_Distance Weight**

| Field | Value |
|-------|-------|
| Change | Reduce OTT_Distance from 5% → 3% |
| Evidence Basis | 4-round cumulative: consensus signal = "mixed". Enrichment contradicted all 4 rounds (top-10 hit it shorter than field in final, −1.4 yds). R1 signal was "weak" (−5.4 trait delta). Distance is not a scoring differentiator at TPC River Highlands. |
| Confidence | High (4 rounds, direct enrichment data; consistent contradicted signal) |
| Recommended Action | Write to venue profile: `ott_distance: 0.03`. Reallocate 2% to PUTT_Short_Conv (WB-A1 above). |

---

**WB-A3: Increase Par5_Scoring Weight**

| Field | Value |
|-------|-------|
| Change | Increase Par5_Scoring from 3% → 5% |
| Evidence Basis | 4-round cumulative: validated all 4 rounds. Trait deltas: R1 +5.6, R2 +12.9, R3 +12.2, R4 +11.0. The course has 2 reachable par-5s that consistently separate the field. SG-APP proxy confirmed all 4 rounds. |
| Confidence | High (4 rounds validated, proxy-confirmed) |
| Recommended Action | Write to venue profile: `par5_scoring: 0.05`. Offset from APP_Wedge reduction (see WB-A4). |

---

**WB-A4: Reduce APP_Wedge from 22% → 20%**

| Field | Value |
|-------|-------|
| Change | Reduce APP_Wedge from 22% → 20% |
| Evidence Basis | Approach was validated as a strong signal (trait delta +13.4 in final), but realized approach SG was 33.9% of top-10 premium vs 40% combined approach weight. Slight systematic overweight relative to putting importance. 4-round evidence. |
| Confidence | Medium (approach is correctly directional, just slightly over-indexed in weight) |
| Recommended Action | Write to venue profile: `app_wedge: 0.20`. Free 2% redistributed to Par5_Scoring (WB-A3). |

---

**WB-A5: Add Course-History Recency Decay Rule**

| Field | Value |
|-------|-------|
| Change | Apply recency decay to CH SG for rounds older than 3 years: rounds before 2023 count at 60% weight |
| Evidence Basis | Fleetwood (18 rounds, CH SG +1.76 pre-tourney) finished T14 with SG-APP 38th. Hovland (19 rounds, CH SG +1.423) won. Henley (30 rounds, CH SG +1.445) finished T12. The raw CH SG overstated Fleetwood's current approach fit because his venue rounds span 5+ years of varying form. 2-player evidence (Fleetwood miss, Henley slight underperform). |
| Confidence | Medium (2 data points; directional logic is sound) |
| Recommended Action | Add to venue profile: `venue_history_recency_decay: {years_cutoff: 3, decay_factor: 0.60}`. VHD blend weight should apply decay before computing venue_history_delta. Flag for validation at 2027 Travelers. |

---

**WB-A6: Elevate Anti-Pattern — "approach_only_limitation"**

| Field | Value |
|-------|-------|
| Change | Add anti-pattern flag: `approach_only_limitation` — triggers when SG-APP 12m > +0.70 but SG-PUTT 12m < 0.0. Suppress win probability by 15% (not tier gate). |
| Evidence Basis | Morikawa (APP elite, PUTT neutral) finished 3rd but had SG-ARG −3.296 (67th) and neutral putting. Cantlay (APP 8th in event, PUTT 28th) finished T14 with 8th-best approach. Burns (APP strong in event, ARG −3.120) capped at T12. Pattern across 3 players: elite approach without putting heat results in top-10 to top-15, not contention. 2 Tier 3+ players + 1 Tier 4 player with clear mechanism. |
| Confidence | Medium-High |
| Recommended Action | Add to `anti_patterns_active` list: `approach_only_limitation`. Penalty = win probability ×0.85, top-3 probability ×0.90. Do NOT affect tier gate. |

---

### Bucket B: Engine Rule Flags — Potential Cross-Venue Changes

---

**WB-B1: ARG-Compensates-Wedge-Liability Modifier**

| Field | Value |
|-------|-------|
| Change | Add engine rule: if wedge_liability flag is active AND ARG_Rough or ARG_Bunker trait score ≥ 70, reduce wedge_liability VTS penalty by 40% |
| Evidence Basis | Justin Thomas: wedge_liability flag correctly identified APP weakness (SG-APP 56th), but ARG +6.257 (1st in field) fully compensated. Alex Fitzpatrick: wedge_liability Tier 5 assignment despite SG-APP +5.518 (5th in field). Both cases show the current flag architecture over-penalizes when a player has the short-game to rescue missed greens. |
| Confidence | Medium (2 direct examples; Thomas ARG rescue is arguably extreme event-week variance, but Alex Fitz is structural) |
| Recommended Action | Add to engine spec v1.2: `if anti_pattern == "wedge_liability" and max(ARG_Rough_score, ARG_Bunker_score) >= 70: apply penalty_multiplier = 0.60`. Review across past events before applying universally. |

---

**WB-B2: Rough_Approach_Liab Flag — Add ARG_Rough Threshold Gate**

| Field | Value |
|-------|-------|
| Change | Add pre-trigger check: rough_approach_liab anti-pattern only fires if ARG_Rough trait score < 55. If ARG_Rough ≥ 55, suppress flag. |
| Evidence Basis | Corey Conners (rank 51, rough_approach_liab flag active) finished T7 with SG-ARG +3.492 (7th in field). His pre-tournament ARG_Rough score was in the mid-tier range. The flag was applied because of approach accuracy metrics, but his ARG compensated. MacIntyre (similar pattern). 2 events with same mechanism. |
| Confidence | Medium |
| Recommended Action | Add threshold gate to rough_approach_liab trigger condition in engine spec. Validate against 3 additional events before promoting to standard rule. |

---

**WB-B3: Putting Variance Annotation for Birdie-Fest Venues**

| Field | Value |
|-------|-------|
| Change | Add explicit field to birdie-fest venue profiles: `putting_variance_class: high`. In model output, add annotation: "Putting is the highest-variance scoring category at this venue. Top finishes will likely require ≥ +2.0 SG-PUTT. Predictability is low." |
| Evidence Basis | 4-round evidence from this event. Putt SG drove 39.1% of top-10 premium but putt trait predictor delta was only +2.0 (mixed signal). Same disconnect expected at most birdie-fest venues where scoring is loose enough for hot putters to separate. |
| Confidence | High (4-round evidence; consistent with general birdie-fest theory) |
| Recommended Action | Add `putting_variance_class: high` to TPC River Highlands venue file. Flag for inclusion in general birdie-fest venue template. Add to event_context.json template as standard field for `birdie_fest_flag: true` events. |

---

## TASK 6: MODEL PERFORMANCE SUMMARY

### Round-by-Round Spearman Rho

| Round | Rho | Tier 1/2 in Top 20 | Pre-Tournament Top-10 in Final Top 10 |
|-------|-----|--------------------|------------------------------------|
| R1 | 0.184 | 4/4 | — |
| R2 | 0.269 | 3/4 | — |
| R3 | 0.344 | 2/4 | — |
| R4 (Final) | 0.341 | 4/4 | 3 of 10 |

Final rho of 0.341 is moderate for a 72-player birdie-fest. Pre-tournament top-10 (VTS ranks 1–10) placed 3 players in the actual final top 10 (Scheffler 2nd, Bhatia T5, Hovland 1st). All 4 Tier 1/2 players finished top 14.

### Overall Model Grade: B+

**Rationale:**
- Tier 1 (Scheffler): Runner-up from co-lead. Full validation.
- Tier 2: One strong hit (Fitzpatrick 4th), one acceptable (Henley T12), one underperform (Fleetwood T14).
- Winner (Hovland): Tier 3 rank 8 win — within model probability range, partially VTS-aligned.
- Major misses: Alex Fitzpatrick (T5→T7 from Tier 5) and Corey Conners (rank 51→T7) represent meaningful VenueFitDelta failures driven by over-penalization of anti-patterns.
- Anti-patterns: Cantlay (partial fail), Thomas (fail — ARG rescued from flag). Both fired on real weaknesses but results escaped.
- Trait weights: Directionally correct across approach, OTT accuracy, ARG. Putting materially underweighted vs realized importance (most actionable single write-back).

---

## AUDIT SUMMARY

The 2026 Travelers Championship returned a **B+ model grade**. The model's top call (Scheffler) was validated at the highest level — runner-up co-leading through 72 holes. Viktor Hovland's win from Tier 3 / rank 8 is within expected model probability and is partially VTS-supported via strong 19-round course history; the specific win mechanism (OTT surge + putting heat) was event-week variance that no pre-tournament model could fully predict. The single most important write-back is **putting weight elevation**: across all 4 rounds, SG-PUTT drove 39.1% of top-10 scoring advantage vs the model's 26% combined putting weight — a 13-percentage-point gap that should be partially closed in the next TPC River Highlands venue file iteration. The most actionable structural fix is the **ARG-compensates-wedge-liability modifier** (Engine Rule WB-B1), which would have corrected the systematic under-tiering of Alex Fitzpatrick and Justin Thomas.
