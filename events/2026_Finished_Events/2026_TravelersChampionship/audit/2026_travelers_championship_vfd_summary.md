# 2026 Travelers Championship — VenueFitDelta (VFD) Audit

**Generated:** 2026-06-29  
**Players joined:** 71 of 72  
**Unmatched leaderboard entries:** 1 (Keith Mitchell)  
**Venue:** TPC River Highlands  

---

## 1. VFD Defined

**VenueFitDelta (VFD)** = `venue_fit_score − neutral_skill_index` expressed in VTS points.  
A positive VFD means the engine assessed this player as *better-suited to TPC River Highlands* than their raw 12-month SG skill baseline alone would imply.  
A negative VFD means the venue profile discounted the player below their raw-skill expectation.

---

## 2. Correlation Analysis

### 2a. Spearman ρ — Component vs Final Finish Position

*(Lower finish position = better result. Negative ρ = component predicts better finish.)*

| Component | Spearman ρ (vs Final Pos) | Interpretation |
|---|---|---|
| VTS Final | -0.379 | Full model composite |
| NeutralSkill Index | -0.335 | Raw 12m SG only |
| NeutralSkill SG | -0.335 | Raw 12m SG (absolute) |
| VenueFitDelta | 0.090 | Venue-fit adjustment only |
| VenueHistoryDelta | -0.108 | Course-history adjustment only |

### 2b. Pearson r — Component vs Final Score to Par

*(More negative score = better. Positive r = component predicts better score.)*

| Component | Pearson r (vs Score to Par) | Interpretation |
|---|---|---|
| VTS Final | -0.347 | Full model composite |
| NeutralSkill Index | -0.337 | Raw 12m SG only |
| VenueFitDelta | 0.165 | Venue-fit adjustment only |
| VenueHistoryDelta | -0.104 | Course-history adjustment only |

---

## 3. Group Averages — VFD, NeutralSkill, VTS

| Group | N | Avg VFD | Median VFD | Avg NSI | Median NSI | Avg VTS | Median VTS |
|---|---|---|---|---|---|---|---|
| Top 5 | 6 | 4.94 | 6.67 | 64.41 | 55.43 | 60.05 | 56.12 |
| Top 10 | 11 | 6.35 | 8.51 | 57.18 | 55.56 | 52.58 | 52.08 |
| Top 20 | 21 | 5.60 | 3.35 | 55.79 | 55.31 | 50.95 | 49.92 |
| Full Field | 71 | 8.95 | 8.51 | 45.72 | 45.41 | 42.40 | 42.80 |

---

## 4. Full Player Table — Ranked by VFD (Descending)

| VFD Rank | Player | Pre-Model Rank | Tier | VFD | NSI | VHD | VTS | Final Pos | Final Score | AP Flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Snedeker, Brandt | 41 | 4 | 33.12 | 22.9 | 0.342 | 41.1 | T38 | -10.0 | — |
| 2 | Campbell, Brian | 71 | 5 | 30.77 | 0.0 | -0.053 | 0.0 | T47 | -8.0 | wedge_liability;rough_approach_liab |
| 3 | Berger, Daniel | 55 | 4 | 25.52 | 32.6 | -0.229 | 35.6 | T25 | -12.0 | poor_birdie_conv;rough_approach_liab |
| 4 | Hoge, Tom | 67 | 5 | 25.30 | 8.7 | -0.338 | 18.4 | T38 | -10.0 | poor_birdie_conv;rough_approach_liab |
| 5 | Glover, Lucas | 56 | 5 | 23.78 | 29.3 | -2.030 | 34.5 | T66 | 0.0 | poor_birdie_conv |
| 6 | Hubbard, Mark | 65 | 5 | 21.15 | 20.0 | 1.809 | 20.8 | 70 | 2.0 | wedge_liability;poor_birdie_conv;rough_approach_liab |
| 7 | Conners, Corey | 51 | 4 | 21.15 | 36.5 | 0.315 | 37.8 | T7 | -17.0 | poor_birdie_conv;rough_approach_liab |
| 8 | Rai, Aaron | 24 | 4 | 19.96 | 47.1 | 0.841 | 48.7 | T30 | -11.0 | poor_birdie_conv |
| 9 | Hisatsune, Ryo | 63 | 5 | 19.65 | 26.1 | 0.000 | 24.8 | T38 | -10.0 | poor_birdie_conv;rough_approach_liab |
| 10 | Straka, Sepp | 27 | 4 | 18.84 | 42.5 | -0.357 | 46.9 | 72 | 10.0 | rough_approach_liab |
| 11 | Vegas, Jhonattan | 70 | 5 | 18.42 | 13.3 | 0.146 | 11.5 | T51 | -7.0 | bomb_and_spray;wedge_liability;poor_birdie_conv;rough_approach_liab |
| 12 | Fitzpatrick, Alex | 57 | 5 | 16.54 | 34.3 | 0.000 | 34.4 | T7 | -17.0 | wedge_liability |
| 13 | Echavarria, Nico | 62 | 5 | 15.92 | 31.9 | -0.053 | 26.8 | T30 | -11.0 | wedge_liability;rough_approach_liab |
| 14 | Mccarthy, Denny | 29 | 4 | 15.71 | 36.2 | 0.976 | 45.4 | T14 | -14.0 | — |
| 15 | Woodland, Gary | 48 | 4 | 15.34 | 43.2 | 0.471 | 39.4 | 71 | 5.0 | bomb_and_spray;rough_approach_liab |
| 16 | James, Ben | 50 | 4 | 15.20 | 36.7 | -0.176 | 38.3 | T62 | -4.0 | poor_birdie_conv |
| 17 | Lowry, Shane | 17 | 3 | 14.92 | 50.0 | 0.084 | 50.7 | T22 | -13.0 | rough_approach_liab |
| 18 | Harman, Brian | 22 | 4 | 14.41 | 40.6 | 4.216 | 49.0 | T25 | -12.0 | — |
| 19 | Suber, Jackson | 69 | 5 | 14.14 | 23.2 | 0.000 | 13.2 | T30 | -11.0 | wedge_liability;poor_birdie_conv;rough_approach_liab |
| 20 | Hovland, Viktor | 8 | 3 | 13.91 | 55.6 | 0.134 | 58.1 | 1 | -21.0 | — |
| 21 | Kim, Michael | 32 | 4 | 13.08 | 36.5 | -0.071 | 44.4 | T30 | -11.0 | — |
| 22 | Morikawa, Collin | 14 | 3 | 12.95 | 55.3 | -2.788 | 52.1 | 3 | -20.0 | poor_birdie_conv |
| 23 | Taylor, Nick | 25 | 4 | 12.63 | 43.7 | -2.301 | 48.7 | T25 | -12.0 | — |
| 24 | Mccarty, Matt | 54 | 4 | 12.55 | 41.1 | 0.000 | 35.9 | T30 | -11.0 | wedge_liability;rough_approach_liab |
| 25 | Gerard, Ryan | 44 | 4 | 12.28 | 44.2 | -0.140 | 40.7 | T44 | -9.0 | poor_birdie_conv;rough_approach_liab |
| 26 | Henley, Russell | 3 | 2 | 12.23 | 68.4 | 1.406 | 66.9 | T12 | -15.0 | — |
| 27 | Novak, Andrew | 60 | 5 | 12.15 | 30.9 | 0.934 | 29.1 | T30 | -11.0 | wedge_liability;poor_birdie_conv |
| 28 | Noren, Alex | 9 | 3 | 11.91 | 54.1 | -0.040 | 57.7 | T55 | -6.0 | — |
| 29 | Poston, J.T. | 33 | 4 | 11.68 | 42.5 | -1.517 | 44.3 | 69 | 1.0 | rough_approach_liab |
| 30 | Bhatia, Akshay | 11 | 3 | 11.32 | 50.7 | 0.777 | 54.1 | T5 | -18.0 | — |
| 31 | Smalley, Alex | 37 | 4 | 11.29 | 39.4 | 1.509 | 42.7 | T47 | -8.0 | rough_approach_liab |
| 32 | Bridgeman, Jacob | 31 | 4 | 10.35 | 46.9 | -0.092 | 44.5 | T47 | -8.0 | wedge_liability |
| 33 | Cauley, Bud | 47 | 4 | 9.83 | 39.1 | -0.326 | 39.8 | T14 | -14.0 | poor_birdie_conv |
| 34 | Cole, Eric | 28 | 4 | 9.29 | 39.1 | 2.083 | 45.8 | T38 | -10.0 | — |
| 35 | Stevens, Sam | 58 | 5 | 8.61 | 35.7 | -1.860 | 30.4 | T62 | -4.0 | wedge_liability;poor_birdie_conv |
| 36 | Spaun, J.J. | 16 | 3 | 8.51 | 57.7 | -0.596 | 51.4 | T7 | -17.0 | poor_birdie_conv |
| 37 | Scott, Adam | 39 | 4 | 8.30 | 48.6 | 0.868 | 41.5 | 65 | -3.0 | bomb_and_spray;poor_birdie_conv |
| 38 | Kitayama, Kurt | 42 | 4 | 8.18 | 53.4 | 0.706 | 41.0 | T25 | -12.0 | bomb_and_spray;poor_birdie_conv;rough_approach_liab |
| 39 | Rose, Justin | 7 | 3 | 7.70 | 61.4 | -0.086 | 60.2 | T25 | -12.0 | — |
| 40 | Kim, Si Woo | 15 | 3 | 7.58 | 58.7 | -0.560 | 52.0 | T44 | -9.0 | poor_birdie_conv |
| 41 | Fowler, Rickie | 13 | 3 | 7.47 | 51.9 | -0.173 | 53.5 | T38 | -10.0 | — |
| 42 | Pendrith, Taylor | 64 | 5 | 6.47 | 34.5 | 1.632 | 24.0 | 61 | -5.0 | bomb_and_spray;wedge_liability;poor_birdie_conv |
| 43 | Meissner, Mac | 35 | 4 | 6.00 | 41.3 | 0.000 | 43.7 | T44 | -9.0 | — |
| 44 | Reitan, Kristoffer | 53 | 4 | 5.98 | 44.9 | 0.000 | 36.5 | T22 | -13.0 | wedge_liability;rough_approach_liab |
| 45 | Finau, Tony | 68 | 5 | 5.65 | 21.0 | -1.126 | 13.8 | T55 | -6.0 | bomb_and_spray;wedge_liability;poor_birdie_conv |
| 46 | Matsuyama, Hideki | 20 | 4 | 5.41 | 53.4 | 0.893 | 49.9 | T14 | -14.0 | poor_birdie_conv |
| 47 | Spieth, Jordan | 36 | 4 | 4.99 | 45.4 | -2.296 | 42.8 | T66 | 0.0 | bomb_and_spray |
| 48 | Im, Sungjae | 66 | 5 | 4.49 | 26.8 | -0.129 | 20.1 | T30 | -11.0 | wedge_liability;poor_birdie_conv |
| 49 | Hall, Harry | 30 | 4 | 4.49 | 49.5 | 2.044 | 44.9 | T51 | -7.0 | wedge_liability |
| 50 | Theegala, Sahith | 61 | 5 | 3.76 | 39.1 | 1.095 | 28.6 | T51 | -7.0 | bomb_and_spray;wedge_liability;poor_birdie_conv |
| 51 | English, Harris | 19 | 3 | 3.51 | 58.7 | 0.876 | 50.3 | T38 | -10.0 | wedge_liability |
| 52 | Fleetwood, Tommy | 2 | 2 | 3.35 | 73.9 | 1.014 | 67.6 | T14 | -14.0 | — |
| 53 | Fox, Ryan | 59 | 5 | 2.57 | 37.7 | -0.004 | 29.1 | T66 | 0.0 | bomb_and_spray;wedge_liability |
| 54 | Clark, Wyndham | 23 | 4 | 2.02 | 52.7 | 1.830 | 48.9 | T5 | -18.0 | bomb_and_spray |
| 55 | Cantlay, Patrick | 21 | 4 | 1.97 | 60.9 | 1.593 | 49.6 | T14 | -14.0 | bomb_and_spray;poor_birdie_conv |
| 56 | Bradley, Keegan | 38 | 4 | 1.58 | 48.1 | 1.466 | 42.6 | T14 | -14.0 | wedge_liability |
| 57 | Aberg, Ludvig | 6 | 3 | 1.32 | 67.9 | 0.046 | 62.9 | T55 | -6.0 | — |
| 58 | Burns, Sam | 18 | 3 | 1.10 | 62.1 | 0.750 | 50.3 | T12 | -15.0 | bomb_and_spray;rough_approach_liab |
| 59 | Knapp, Jake | 40 | 4 | 1.00 | 58.6 | -0.068 | 41.2 | T55 | -6.0 | bomb_and_spray;wedge_liability;rough_approach_liab |
| 60 | Hojgaard, Nicolai | 46 | 4 | 0.77 | 49.3 | 0.000 | 40.3 | T14 | -14.0 | bomb_and_spray;rough_approach_liab |
| 61 | Day, Jason | 52 | 4 | 0.19 | 44.0 | 1.256 | 37.5 | T55 | -6.0 | wedge_liability |
| 62 | Fitzpatrick, Matt | 4 | 2 | -0.39 | 72.2 | -0.854 | 65.2 | 4 | -19.0 | — |
| 63 | Griffin, Ben | 12 | 3 | -1.16 | 57.2 | -1.860 | 53.8 | T10 | -16.0 | — |
| 64 | Schauffele, Xander | 10 | 3 | -3.98 | 68.4 | 0.719 | 55.8 | T51 | -7.0 | bomb_and_spray |
| 65 | Thomas, Justin | 49 | 4 | -4.17 | 51.2 | 0.588 | 39.1 | T14 | -14.0 | bomb_and_spray;wedge_liability |
| 66 | Young, Cameron | 5 | 3 | -4.29 | 72.2 | 0.015 | 64.3 | T47 | -8.0 | — |
| 67 | Macintyre, Robert | 43 | 4 | -4.86 | 56.8 | 2.286 | 40.7 | T10 | -16.0 | bomb_and_spray;wedge_liability |
| 68 | Gotterup, Chris | 26 | 4 | -5.10 | 58.9 | 1.019 | 48.7 | T30 | -11.0 | bomb_and_spray |
| 69 | Mcnealy, Maverick | 34 | 4 | -5.49 | 59.7 | 0.379 | 43.8 | T55 | -6.0 | bomb_and_spray;wedge_liability |
| 70 | Lee, Min Woo | 45 | 4 | -5.57 | 49.5 | 0.454 | 40.4 | T62 | -4.0 | wedge_liability |
| 71 | Scheffler, Scottie | 1 | 1 | -10.15 | 100.0 | -0.008 | 82.0 | 2 | -21.0 | — |

---

## 5. VFD Validation / Miss / NeutralSkill Carry Analysis

### 5a. Best VFD Validations — Top-quintile VFD finishers inside Top 20

*(Top 14 by VFD = top quintile of 72-player field)*

| Player | VFD | VFD Rank | Pre-Model Rank | Final Pos | Score | Mechanism |
|---|---|---|---|---|---|---|
| Conners, Corey | 21.15 | 7 | 51 | T7 | -17.0 | APP_Wedge |
| Fitzpatrick, Alex | 16.54 | 12 | 57 | T7 | -17.0 | OTT_Accuracy |
| Mccarthy, Denny | 15.71 | 14 | 29 | T14 | -14.0 | PUTT_BirdieConv |

### 5b. VFD Misses — Top-quintile VFD, finished outside Top 30

| Player | VFD | VFD Rank | Pre-Model Rank | Final Pos | Score | AP Flags |
|---|---|---|---|---|---|---|
| Snedeker, Brandt | 33.12 | 1 | 41 | T38 | -10.0 | — |
| Hisatsune, Ryo | 19.65 | 9 | 63 | T38 | -10.0 | poor_birdie_conv;rough_approach_liab |
| Hoge, Tom | 25.30 | 4 | 67 | T38 | -10.0 | poor_birdie_conv;rough_approach_liab |
| Campbell, Brian | 30.77 | 2 | 71 | T47 | -8.0 | wedge_liability;rough_approach_liab |
| Vegas, Jhonattan | 18.42 | 11 | 70 | T51 | -7.0 | bomb_and_spray;wedge_liability;poor_birdie_conv;rough_approach_liab |
| Glover, Lucas | 23.78 | 5 | 56 | T66 | 0.0 | poor_birdie_conv |
| Hubbard, Mark | 21.15 | 6 | 65 | 70 | 2.0 | wedge_liability;poor_birdie_conv;rough_approach_liab |
| Straka, Sepp | 18.84 | 10 | 27 | 72 | 10.0 | rough_approach_liab |

### 5c. NeutralSkill Carry Jobs — Negative VFD, finished Top 20

*These players outperformed their venue-fit discount — raw skill carried them despite a venue mismatch.*

| Player | VFD | NSI | VHD | Pre-Model Rank | Final Pos | Score | AP Flags |
|---|---|---|---|---|---|---|---|
| Scheffler, Scottie | -10.15 | 100.0 | -0.008 | 1 | 2 | -21.0 | — |
| Fitzpatrick, Matt | -0.39 | 72.2 | -0.854 | 4 | 4 | -19.0 | — |
| Griffin, Ben | -1.16 | 57.2 | -1.860 | 12 | T10 | -16.0 | — |
| Macintyre, Robert | -4.86 | 56.8 | 2.286 | 43 | T10 | -16.0 | bomb_and_spray;wedge_liability |
| Thomas, Justin | -4.17 | 51.2 | 0.588 | 49 | T14 | -14.0 | bomb_and_spray;wedge_liability |

---

## 6. Spotlight Player Evaluations

### Scottie Scheffler

| Field | Value |
|-------|-------|
| Pre-tournament rank | 1 of 72 |
| Pre-tournament tier | Tier 1 |
| VTS Final | 81.95 |
| NeutralSkill Index | 100.0 (12m SG = 3.17) |
| Venue Fit Score | 89.85 |
| VenueFitDelta | **-10.15** |
| VenueHistoryDelta | -0.008 (22 rounds, CH SG 2.321) |
| Anti-Pattern Flags | — |
| AP Penalty Total | 0.00 |
| VFD Rank (of 72) | 71 |
| Final Finish | 2 (-21) |

### Viktor Hovland

| Field | Value |
|-------|-------|
| Pre-tournament rank | 8 of 72 |
| Pre-tournament tier | Tier 3 |
| VTS Final | 58.10 |
| NeutralSkill Index | 55.6 (12m SG = 1.33) |
| Venue Fit Score | 69.47 |
| VenueFitDelta | **13.91** |
| VenueHistoryDelta | 0.134 (19 rounds, CH SG 1.423) |
| Anti-Pattern Flags | — |
| AP Penalty Total | 0.00 |
| VFD Rank (of 72) | 20 |
| Final Finish | 1 (-21) |

### Collin Morikawa

| Field | Value |
|-------|-------|
| Pre-tournament rank | 14 of 72 |
| Pre-tournament tier | Tier 3 |
| VTS Final | 52.08 |
| NeutralSkill Index | 55.3 (12m SG = 1.32) |
| Venue Fit Score | 68.27 |
| VenueFitDelta | **12.95** |
| VenueHistoryDelta | -2.788 (16 rounds, CH SG 0.569) |
| Anti-Pattern Flags | poor_birdie_conv |
| AP Penalty Total | -2.35 |
| VFD Rank (of 72) | 22 |
| Final Finish | 3 (-20) |

### Scheffler vs Hovland — VFD Alignment Comparison

| Dimension | Scheffler | Hovland |
|-----------|-----------|---------|
| VFD | -10.15 | 13.91 |
| VFD Rank (of 72) | 71 | 20 |
| VenueHistoryDelta | -0.008 | 0.134 |
| Venue History Rounds | 22 | 19 |
| CH SG | 2.321 | 1.423 |
| NSI | 100.0 | 55.6 |
| NeutralSkill SG | 3.17 | 1.33 |
| VTS Final | 81.95 | 58.10 |
| Final Finish | 2 | 1 (PO win) |

---

## 7. Conclusions

### Did VenueFitDelta materially explain final standings?

The Spearman ρ for VFD vs final position was **0.090** (weak predictive power), compared to **-0.335** for NeutralSkill Index and **-0.379** for VTS Final (the full composite).  

VFD contributed *less* predictive signal than raw NeutralSkill alone in this event, meaning the **venue-fit adjustment layer added noise more than signal** relative to baseline SG. This is consistent with the audit finding that the strongest finishers were driven by event-week SG variance (especially putting) rather than pre-assigned venue-fit trait scores.

The full VTS composite outperformed both individual components in rank-ordering (ρ = -0.379), which validates the multi-component blending approach even if VFD alone was limited.

Group-level analysis: top-10 players averaged VFD = **6.35** vs full-field mean of **8.95** — a delta of **−2.60 VTS points**. This is a *counterintuitive negative result*: the top-10 finishers actually had **lower** average VFD than the rest of the field. High-VFD players were disproportionately represented in the VFD Misses bucket (Snedeker VFD rank 1 → T38; Campbell VFD rank 2 → T47; Glover VFD rank 5 → T66; Straka VFD rank 10 → 72nd). The inflated VFD values for these low-NSI players were not supported by sufficient baseline skill, confirming that VFD only adds value in combination with adequate NeutralSkill.

### Was Hovland's win more VFD-aligned than Scheffler's near-win?

**Yes** — Hovland carried a significantly higher VFD (+13.91, rank 20 of 72) than Scheffler (−10.15, rank 71 of 72). The venue-fit layer *positively identified* Hovland as a better fit for TPC River Highlands than his raw 12m SG would imply (NSI = 55.6 → venue boosted to 69.5). Scheffler, by contrast, received the deepest venue-fit discount in the entire field — the engine identified his approach trait mix as a weaker TPC River Highlands fit than his NSI (100.0) suggested.

**Scheffler's near-win was the single largest NeutralSkill carry job in the field**: NSI 100.0 overrode a VFD of −10.15 to produce a co-regulation-leader finish. His win probability was model-highest because NSI carries the most weight in the blend (40%), not because of venue fit.

**Hovland's win mechanism:** The VFD (+13.91) correctly placed him in the venue-aligned contender band. His win was then completed by VenueHistoryDelta (19 rounds, CH SG +1.423 = one of the deepest histories in the field) plus event-week OTT and putting variance that no pre-tournament model could have predicted. VFD identified the right player for the right venue; the specific win was partially variance on top of a correct structural call.

### Collin Morikawa — VFD verdict

Morikawa (VFD = 12.95, VFD Rank 22) finished 3rd from model rank 14. His VFD was positive, suggesting the model recognized his fit to this venue. His finish (3rd) validates his VFD assignment. The key driver of his finish was approach play (SG-APP +6.907, 2nd in field) which is the highest-weighted VTS trait — VFD correctly captures his approach strength at this venue but the model placed him only 14th overall due to AP flags (poor_birdie_conv).

### Should VFD be exposed on the main app table?

**Verdict: Yes — but require NSI context alongside it, and add a model-variance disclosure.**

VFD standalone ρ = +0.090 (wrong direction, essentially zero). This means VFD **alone is not a useful standalone predictor** and should never be displayed without its NSI counterpart. The dangerous pattern — high VFD, low NSI — produced the worst finishes in the field (Snedeker, Campbell, Glover, Straka). A user seeing only a large positive VFD for a low-NSI player would be misled.

**Where VFD does add value:** The three cleanest VFD validations (Conners T7, Alex Fitzpatrick T7, Morikawa 3rd) all paired moderate-to-strong NSI (36–55 NSI range) with a positive VFD signal. Hovland (NSI 55.6 + VFD +13.91 = 1st) is the prototype. VFD works when it amplifies a player with sufficient baseline skill, not when it inflates a low-skill player.

**Recommended app implementation:**
- Display VFD as a signed delta column (`+13.9`, `−10.2`), not as a raw score
- Color-code: green when both VFD > 0 AND NSI > 45; amber when VFD > 0 but NSI ≤ 45 (elevated venue fit, limited skill floor); grey/negative when VFD < 0 (raw-skill carry required)
- Tooltip: *'Venue Fit Delta — how much the course profile adjusts this player above or below their raw 12-month skill baseline. Best when paired with a strong NeutralSkill score.'*
- Do NOT expose VFD as a standalone ranking column. Always sort or filter on VTS, not VFD alone.

---

*End of VFD Audit — 2026 Travelers Championship*