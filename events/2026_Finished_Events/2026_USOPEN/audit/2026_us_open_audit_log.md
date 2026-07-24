# 2026 U.S. Open — Post-Tournament Audit Log
Venue: Shinnecock Hills GC | Par 70 | 7,440 yds | Weather class: High Wind
Winner: Wyndham Clark, -4 (276) | Runner-up: Sam Burns, -3 | Cutline: +5 (145), 72 players made the cut
Audit completed by system | Source: 2026_USOPEN_scored_field.csv vs. official final results

## 1. Event context lock
- Conditions ran close to forecast in magnitude but not in sequencing: the model flagged Thursday (R1) as the toughest day (20–27mph sustained, 35mph gusts) and Saturday (R3) as second-toughest (30mph gusts). Actual scoring average was higher in R3 (73.62) than R1 (73.28) — the wind/setup combination played harder Saturday than Thursday, inverting the predicted severity order. R2 and R4 landed in the predicted-easier zone but R2 (72.25) scored tougher than its "best weekday scoring" label implied.
- USGA explicitly widened fairways (~2x 2004 width) and did not adjust hole locations or green speed for wind. This is a structural setup signal that bears directly on Finding 1 below and was present in the event context file but not visibly reflected in anti-pattern magnitude.
- Field-wide cut rate: 72/156 made the cut (46.2%), cutline +5.

## 2. Tier 1 / Tier 2 accountability review

| Tier | n | Avg VTS | Predicted Top10% (avg) | Actual Top10 rate | Predicted MakeCut% (avg) | Actual MakeCut rate |
|---|---|---|---|---|---|---|
| 1 | 8 | 86.7 | 70.3% | **12.5%** (1/8) | 85.9% | 87.5% |
| 2 | 32 | 72.0 | 46.3% | **0.0%** (0/32) | 78.8% | 50.0% |
| 3 | 41 | 58.9 | 22.5% | 17.1% | 55.3% | 56.1% |
| 4 | 37 | 42.7 | 6.7% | 5.4% | 18.2% | **43.2%** |
| 5 | 38 | 19.6 | 1.3% | 0.0% | 3.1% | **26.3%** |

**Tier 1 detail (sorted by VTS):**

| Player | VTS | Pred. Top10% | Finish | Result |
|---|---|---|---|---|
| Scheffler | 99.0 | 82.7% | T4 | Hit |
| Henley | 86.9 | 71.3% | T65 | **Severe miss** |
| Fitzpatrick, M. | 85.8 | 69.9% | 22 | Near miss |
| Fleetwood | 85.9 | 69.9% | T11 | Near hit |
| Young | 85.5 | 69.5% | T43 | Miss (anticipated — see §4) |
| Rahm | 87.0 | 71.5% | MC | **Severe miss** |
| Schauffele | 82.2 | 64.3% | T11 | Near hit |
| Aberg | 81.5 | 63.2% | T17 | Near miss |

Tier 1 win conversion: 0/8 (winner came from Tier 3). Tier 1 Top-10 hit rate of 12.5% against a model-implied ~70% average is the headline number, but the shape matters: three players (Fleetwood, Schauffele, Aberg) landed T11–T17 — close misses, not refutations. The damage is concentrated in two outright collapses (Rahm MC, Henley T65) plus one partially-anticipated miss (Young, see anti-pattern/risk review).

Tier 2 fared worse in relative terms: 0/32 Top-10, only 5/32 inside the actual Top-20, and a 50% cut-make rate against a predicted 78.8% average — the single largest probability-calibration gap in the field.

## 3. Anti-pattern review
Anti-pattern flags were directionally fine in the aggregate (field-wide Top-20 base rate 13.5%; flagged players landed at 12.6%, unflagged at 15.6% — a mild, correctly-signed fade). `short_and_wild` was a clean fade (0% Top-10, 0% Top-20, 82% missed cut on n=17).

The miss is concentrated, not diffuse: **the top three finishers all carried an anti-pattern flag**, and in two of three cases that flag is what knocked them out of Tier 1/2 into Tier 3.

| Finish | Player | Pre-penalty VTS | AP flag | AP penalty | Final VTS | Final Tier |
|---|---|---|---|---|---|---|
| 1st | Clark | 74.7 (Tier 2 range) | bomb_and_spray | −4.0 | 64.7 | 3 |
| 2nd | Burns | 78.2 (Tier 2 range) | bomb_and_spray; weak_tight_runoff | −6.1 | 59.9 | 3 |
| 3rd | Kim, T. | 65.7 (Tier 3 range either way) | poor_lag_putting | −1.3 | 61.8 | 3 |

Clark and Burns were both pre-penalty Tier 2 players that the `bomb_and_spray` / `weak_tight_runoff` penalty demoted a full tier — and both then won/finished runner-up. This is the single most evidence-dense finding in this audit: **the bomb_and_spray and weak_tight_runoff penalty magnitudes were too harsh for this specific setup.** The event context file explicitly recorded USGA's fairway-width doubling and a no-green-speed-adjustment philosophy — a structural signal that the driving-accuracy penalty this anti-pattern encodes should have been damped, independent of moisture/firmness. That signal was available pre-tournament and wasn't applied.

## 4. Risk register validation
Separate from tier placement, the named structural risks in the pre-tournament risk register were largely **correct in mechanism**, just under-weighted in score impact:

- `APP_200+` flagged for Scheffler, Rahm, Young. Rahm (MC) and Young (T43) both broke on this exact axis under wind. Scheffler's sheer baseline carried him through (T4).
- `MajorGrind` flagged for Henley, Schauffele, Aberg, Hovland, Cantlay. Henley (T65), Hovland (MC), and Cantlay (MC) broke on this exact axis; Schauffele (T11) and Aberg (T17) did not.

Net: 5 of the 7 most consequential Tier 1/2 misses had their failure mechanism named correctly in advance. The gap isn't risk identification — it's that named risks weren't converted into enough VTS discount or tier downgrade to move the published ranking.

## 5. Debut and form-gate review
- 23 debut players. A-class debuts (steepest penalty, −4.0) mostly missed the cut as expected; the exceptions (Tibbits T61, Fleming T56) finished well outside contention, consistent with the penalty. B-class debuts (Koivun, James, −1.75) both landed T23 — reasonable, no miscalibration evident. **Hold: debut framework performed as designed, no change warranted.**
- Recent-form hard gate fired on only 4 players this week (n too small for a reliable read either direction). **Hold, insufficient sample.**
- Health gate: no players flagged this week. No signal generated.

## 6. Probability / variance calibration review
Make-cut probability was the most miscalibrated output this week:
- Tier 4 (cut-line players): predicted 18.2% average make-cut, actual 43.2%.
- Tier 5 (fades): predicted 3.1% average make-cut, actual 26.3%.
- Tier 2: predicted 78.8% average make-cut, actual 50.0%.

This is a textbook signature of a high-variance week where the model's probability bands weren't widened enough even though the venue/week was correctly *labeled* "High Wind." The label was right; the band compression that should follow from it (scoring spec §8.2: "higher-variance venues compress win probabilities and reduce overconfidence in separation") was insufficiently applied to make-cut and Top-10 probabilities specifically.

## 7. Significant miss log
| Player | Projected | Actual | Magnitude | Primary category | Secondary category |
|---|---|---|---|---|---|
| Rahm, Jon | Tier 1, VTS 87.0, Top10% 71.5 | MC | Tier1→missed cut | Variance / noise | VenueFit miss (APP_200+ under wind) |
| Henley, Russell | Tier 1, VTS 86.9, Top10% 71.3 | T65 | Tier1→T65 | Variance / noise | Form scaling miss |
| Clark, Wyndham | Tier 3, VTS 64.7 | Win | 2-tier underrate | Anti-pattern miss | Weather/setup miss |
| Burns, Sam | Tier 3, VTS 59.9 | 2nd | 2-tier underrate | Anti-pattern miss | Weather/setup miss |
| Young, Cameron | Tier 1, VTS 85.5, Top10% 69.5 | T43 | Tier1→T43 | VenueFit miss (APP_200+) | — (anticipated in risk register) |
| Tier 2 field-wide | avg MakeCut% 78.8 | 50.0% actual | Calibration gap | Variance miss (probability) | — |

## 8. Audit verdict
Hold core trait weights (OTT_Distance/Accuracy and WindTolerance both correlated correctly with actual finish at venue-wide level, Spearman ρ ≈ −0.49). Adjust anti-pattern magnitude for this venue under wide-fairway/no-setup-softening conditions. Tighten the link between named risk-register mechanisms and VTS discount so a correctly-identified risk produces a correctly-sized tier move. Widen probability bands for high-wind-classified weeks, specifically make-cut and Top-10 outputs for Tier 2–5.
