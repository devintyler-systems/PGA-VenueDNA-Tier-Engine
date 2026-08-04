# Probability and Validation Audit

## Archived probability evidence

| Board | Formula / parameters | Monotonicity and field sums | Recommendation |
|---|---|---|---|
| Rocket | Shared `tempered_softmax`, T win/top5/top10/top20=`3.5/5/7/10`, multiplied by positions; make-cut=`clip(1.25*top20+10,20,98)` (`enrich_cards.py:45-46,376-400`). | Payload: 147 players; displayed sums 100.1/500.1/1000.5/2000.2 due rounding. | Keep only as experimental; rank-one make-cut was 32.2%, a sanity concern. |
| 3M | Same shared formula. | 144 players; 99.9/499.5/999.9/1999.8; monotonicity is enforced in code. Rank one: win 1.9%, cut 35.0%. | Experimental; do not use for a confidence/betting claim. |
| Open | independent softmax T=`14/17.5/21/27`, position totals 100/500/1000/2000; logistic cut midpoint 53, slope .10 (`score_open_2026_v3.py:496-524`). | 156 players; 99.99/500.01/1000.01/2000.00; sampled payload had no monotonic violations. Rank one: 3.69% win, 95.4% cut. | Experimental; label separately from shared pathway. |

The sums are expected position-event totals, not probabilities summing to 100 for top-N markets. Temperatures are hand-set. No inspected producer or payload supplied calibration date, holdout set, Brier/log-loss, reliability curve, intercept/slope, or uncertainty intervals. Boards expose probabilities in sorting, filters, narratives, and betting-lane language (Open `app.js:70-115`, `score_open_2026_v3.py:527-537`); they should not be presented as calibrated forecasts.

## Required walk-forward calibration framework

1. Freeze each event’s pre-event payload and source hash before results.
2. Split strictly by event chronology; train parameters on prior events only, never rows from the held-out event.
3. Score win/top5/top10/top20/make-cut with Brier score and log loss; retain field-size-normalized expected-count error.
4. Produce reliability diagrams, calibration intercept/slope, and bootstrap confidence intervals by market and by venue class.
5. Compare canonical model, event extension, and no-fit baseline; record model/schema version and field size.
6. Promote a probability label from experimental only after documented out-of-sample criteria approved by Council governance.

## Validation gaps

`engine/latent_model.py` has a monotonicity verifier, but its default payload finder searches only `events/*/`, not archived `events/2026_Finished_Events/*/` (`latent_model.py:_find_payload`). Tests pass, but no cross-event probability-calibration or archived-payload monotonicity test was found. Add a deterministic archive-fixture validator before changing probability math.
