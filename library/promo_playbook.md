PGA Promo Card Playbook (Aronimink / Majors)

1\. Tier semantics → finish probabilities

Tier definitions must constrain MC odds:



Tier 1 (VTS ≥ 80): MC probability capped low (e.g., ≤ 10%), unless injury/weather shock is flagged.



Tier 2 (65–79): MC probability capped at moderate (e.g., ≤ 25–30%) in normal conditions.



Tier 3: Wide distribution; MC is live but not default.



Tier 4–5: MC is common and can be the mode.



Anti‑patterns and tour‑quality discounts:



Anti‑patterns (e.g., Blunt Power) and LIV/DP multipliers shrink ceiling and widen tails, but do not flip a Tier‑2 player into “MC favorite” without extreme supporting evidence.



Interpret: “more volatile, more likely to MC than a normal Tier 2, but still more likely to make the cut than not.”



When you pick “Misses Cut” for a Tier‑2+ player:



You must explicitly log:



Model MC probability (from finish‑distribution mapping).



Crowd MC probability.



Implied edge.



“Max contrarian” is not sufficient; base rates must still justify the pick.



2\. Course architecture for exotic props

Always anchor these props in actual hole design and course DNA, not generic major heuristics.



Final‑shot length:



Use finishing‑hole template:



Par and yardage (par‑4 vs par‑5 closer).



Typical approach distance (long‑iron vs wedge).



Green severity (tiers, runoffs, bunkers).



Hard par‑4 Ross finisher (like Aronimink 18):



Expect more 4–10 ft putts for par/birdie than tap‑ins.



Default lean: Over 3.5 ft, unless the closer is an easy par‑5 where wedges predominate.



Winning margin:



“Hard par, easy bogey” venues with few par‑5s and tough closers → compressed finishes:



Elevate “Exactly 1 shot” and “Playoff” relative to generic major averages.



Be suspicious of overweight consensus on “Exactly 2 shots” when your course model screams compression.



Cut line:



Use venue DNA + weather:



Firm/fast, long par‑70, thick rough → around E or +1.



Soft early week → −1 to −2 more plausible.



Don’t just import “typical PGA cut line”; tie it to Aronimink’s scoring expectations.



3\. Weather blending for winning score

Each venue must have:



A dry‑track band (design intent):



For Aronimink: −8 to −11 in firm, normal‑wind major setups.



A soft‑track band (weather‑eased):



For Aronimink: −12 to −15 baseline, with −16 to −19 live if it’s soft for multiple days.



A mechanical blend:



Define w\_soft from forecast (e.g., probability of meaningful rain early):



Example: w\_soft = 0.6, w\_firm = 0.4 when Thursday rain is \~50% and weekend looks good.



Model expected winning score as a mixture of dry/soft bands instead of ad‑hoc narrative.



When you pick a bin, state: “Venue band = X, weather band = Y, blend weight = Z → chosen bin.”



4\. Correlation and card coherence

Certain questions are structurally linked:



Nationality of winner ↔ Named winner.



Winning total ↔ Tie‑breaker final‑round score.



Winner ↔ Winner’s score ↔ Margin.



Rules:



For linked questions, treat them as a joint scenario, not independent darts:



If you pick Non‑USA in nationality, you should pick a non‑USA champion in winner.



If you pick winner at −14 total, final‑round score must be consistent with a plausible round‑by‑round path.



When you intentionally break coherence (to hedge):



Label it explicitly as “hedging correlation” and understand it increases the chance of losing multiple questions simultaneously if you’re wrong.



Tie‑breaker derivation:



Always derive tie‑breaker strokes from:



chosen winner,



chosen winning score bin,



expected Sunday scoring range (e.g., −1 to −3 for contenders).



Example: par‑70, winner −13, Sunday −3 → 67.



5\. Logging “edge” calls and audits

Any time you call something “highest‑edge pick” or make a strongly contrarian choice:



Log:



Model probability (from VTS → finish distribution mapping).



Crowd pick rate.



Implied edge (model – crowd).



After the event, classify misses:



Trait mis‑weight



Weather mis‑weight



Tier→finish mapping error



Overconfidence in contrarian angle



Pure variance



Use audits to adjust:



Shrink or expand anti‑pattern penalty sizes.



Re‑calibrate Tier→finish distributions (especially MC rates for Tier 1–2).



Update weather mixing weights for winning score bands.



6\. Summary “if/then” heuristics to internalize

If Tier 2 and no injury, then MC is never default; use 11–20 or 1–10 as base, MC only as a calculated tail.



If finishing hole is long par‑4 with tough green, then final shot is more likely >3.5 ft than <3.5 ft.



If venue = “hard par, few par‑5s, tough closer,” then 1‑shot win and playoffs are under‑picked relative to middle buckets.



If forecast materially softens first 1–2 rounds, then shift winning score band upward a few shots from DNA baseline.



If you pick Non‑USA in nationality, then do not pick a US winner unless you explicitly choose to accept correlation risk.

