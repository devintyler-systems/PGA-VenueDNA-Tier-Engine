I clicked through the full VenueDNA 3M Open board — Pre-Tournament, Rd 1, Rd 2, Rd 3, Final, Post-Mortem, and Tee-Times tabs, Table/Card/Contention Map/Storylines views, Analyst Mode weight sandbox, Advanced Filters, Spotlight, Glossary, and individual player cards across tiers (T1 through T5). Here's the honest state of the app and what I'd prioritize.

What's actually working well
Rd 1/Rd 2 leaderboards are live, correctly sorted, and the Spearman rho badge is genuinely useful (0.229→0.380 shown live).

The Contention Map (NSI vs Venue Fit Δ scatter) is a strong, differentiated visualization — keep investing here.

The Glossary is clear and well-written; this is rare in fantasy/analytics tools and is a real asset.

Analyst Mode's Sc.Rank/Δ columns are populated correctly now, confirming that fix held.

Filter trait dropdown and "+Add filter rule" work with a full trait list.

Tier Intelligence breakdown (T1–T5 counts) is a nice compact summary.

Confirmed bugs / weak spots to fix
1. Player Brief "Key Risk" text is boilerplate copy-pasted across almost the entire field. I pulled the Spotlight panel text directly: 11 of 12 "Top Contenders" have the exact identical sentence — "A regression in approach SG from the l12 trend — especially from 150-200 yards — converts this profile from contender to T3/T4 finisher; no short-game bailout exists at TPC". Only Maverick McNealy has unique language. This is your "Weak Spotlight & Player Cards" complaint confirmed at the data layer, not just a UI illusion — the brief-generation logic is falling back to a single template for nearly everyone instead of pulling player-specific inputs.

2. Player card "Win Mechanism / Key Risk / Model Read / Neutral Skill" blocks reuse the same paragraph 3-4 times within a single card. On Scheffler's card, the "Model Read," "Neutral Skill," and part of "Analyst Intelligence — Full Brief" are all the same approach-SG sentence repeated verbatim. This isn't just boring, it signals the brief generator has one narrative slot being fanned out into multiple UI locations rather than genuinely distinct content blocks (mechanism vs. risk vs. skill assessment should be structurally different).

3. Trait Profile Confirmed and this is worse than I described. Clicking Scheffler's name in the Round 1 Leaderboard (bottom table) opens a player card that's completely mismatched:

Header shows "Scottie Scheffler" tagged T5, "Debut Profile," VTS 50.00 — he's actually T1, VTS 100.00 on Pre-Tournament.

Win probability shows 0.0% / 0.0% / 0.0% across the board with absurd placeholder odds like "+9999900" and "+999900" — clearly a null-fallback the front-end is defaulting to rather than fetching his real projections.

"Pre-Tournament Status" box says "No pre-tournament briefing available; field alternate tracked at baseline thresholds" and flags "Late Alternate / No Pre-Tourney Model Data" in red — this is the "field alternate" fallback template, being served to the actual betting favorite/leader.

Every single Trait Profile row is pegged to 50.0 with a "—" delta and the italic label "Alternate Entry: Baseline Regressed to Field Mean" confirming this is a generic placeholder record, not player-specific data.

Yet oddly, "Player Analysis / Neutral Skill" text below still shows his real pre-tournament brief language (approach SG top-24th percentile, etc.) — so the brief text and the trait/probability data are coming from two different, disconnected data sources, and the trait/probability layer is failing its lookup while the narrative layer is succeeding.

Root cause (my assessment)
This is a player_id join failure specific to the round-context modal, not a rendering/CSS issue. On Pre-Tournament, the modal correctly resolves Scheffler's player_id to his real VTS record. On Rd 1/Rd 2, the modal is very likely trying to join the live-round payload record to his pre-tournament trait/probability record by a different key or index than the one used on the Pre-Tournament tab — and when that join fails, instead of erroring, it silently falls back to a generic "unmatched/alternate field player" template (hence "Debut Profile," "Late Alternate," 50.0 defaults, and 0.0% odds). The fact that the brief/narrative text still displays correctly suggests the brief lookup and the trait/probability lookup are two separate code paths, and only the trait/probability path is broken in round-context.

This is very likely happening for a large share (possibly all) of players clicked from the Rd 1/Rd 2 leaderboard tables, not just Scheffler — worth a full sweep, but given it reproduced immediately and consistently on the literal Round 1 leader, I'd treat this as near-universal, not intermittent.

Also confirmed: your "R1 Live" labeling bug
The sub-tab still reads "R1 Live" and "R2 Live" even though both rounds are complete and Rd 3 is the active state — confirmed exactly as you described. This is a hardcoded label that isn't tied to round-completion state; it should flip to "R1 Final" / "R2 Final" once that round's data is locked (likely once R3/R4 data exists or a cut/final flag is set upstream).

Priority fix recommendation
Highest priority: Fix the player card data-join in Rd 1/Rd 2/Rd 3/Rd 4 contexts so it pulls the same player_id-indexed trait/probability record used on Pre-Tournament, merged with that round's live deltas — instead of falling to the alternate/debut fallback template. This is a correctness bug affecting the single most-viewed feature (clicking any player during a live round).

Add a guard so the "Alternate Entry / Debut Profile / No Pre-Tourney Model Data" fallback template can only render for players who are actually verified late alternates (a real subset of the field), not as a silent catch-all for failed joins. Right now this fallback is masking the bug rather than surfacing it — it should log/flag a visible error state instead of impersonating a legitimate rare-case template.

Tie the "R1 Live"/"R2 Live" tab labels to a round-completion flag so they read "Final" once scores are locked, consistent with how Rd 3/Rd 4 correctly read "Pending Live Scores."

This needs to be retested across a wider sample (a handful of T1–T5 players clicked directly from the Rd1/Rd2/Rd3 leaderboard tables) to confirm scope before your dev applies a fix — but based on reproducing it instantly on the actual R1 leader, I'd treat this as a systemic join bug, not a one-off.

4. "VTS Journey — Similar-Course History" chart is a flat, near-identical gold line for every player, with only "2 signal points." This is confirmed — it's not a rich sparkline, it's a near-static rendering because most players have "No TPC starts on record" (course history is genuinely thin for a NEW-ish PGA stop). The chart isn't broken code, it's an honest reflection of sparse data, but presenting it as a full "Journey" is misleading. Either suppress the chart when data depth is 2 points, replace with a plain badge, or blend in tour-wide similar-course data to give it real shape.

5. "Final" tab leaks a raw HTTP 404 error to the user: "Round data not yet available (data/2026_3m_open_final_payload.json — HTTP 404)". This is a real bug, not a design choice — it should be caught and replaced with the same clean "pending" messaging used on Post-Mortem and R3/R4 ("Round 3 Analysis Pending Live Scores").

6. Tee-Times tab is completely empty of content — no wave groupings, no start times, nothing beyond the tab label rendering the same Field Explorer/Storylines/Contention Map stack underneath it. It was "un-grayed" per your changelog, but functionally there's no tee time data wired in at all.

7. Rd 3 / Rd 4 correctly show "Analysis Pending Live Scores" — consistent with your note that these haven't been built yet. No surprises there, but worth flagging that this placeholder pattern should also be what Final/Tee-Times use instead of the 404 leak or blank tab.

New feature ideas / architecture recommendations
Player Briefs — make them individual and alive:

Move brief generation off single-template narrative slotting. Feed the LLM/script a structured stat delta per player (SG trend by category, course-fit deltas, recent finishes, weather-adjusted projections) and force distinct prompts per section (Win Mechanism ≠ Key Risk ≠ Skill Read) so it can't just repeat one sentence three times.

Build a daily brief refresh: after each round, regenerate a short "what happened + what it means going forward" blurb per player using that day's actual SG/score deltas vs. their pre-tournament VTS baseline. This is very achievable with your existing per-round SG data — you already compute vs_proj and Δ Rank, you just need a templated narrative layer that consumes those deltas ("Kohles' +8.07 SG:APP day shattered his T4 tier profile — this isn't variance, it's a genuine ball-striking spike").

Add a lightweight "storyline momentum" tag that updates each round: Riser / Faller / Steady / Bailout — computed directly from Δ Rank you already display.

Weather/conditions/form integration:

You already show wind and heat data per round, but nothing in the trait model appears to react to it live. Build a "conditions-adjusted" overlay: e.g., on the 94°F/33% storm-risk R3/R4 days, surface a "heat fade risk" trait modifier for players with poor heat-tolerance history, and visually flag it on the leaderboard (small icon), not buried in a static "What Wins Here" card.

Track "form vs forecast" — plot each player's live SG performance against their pre-tournament VTS score as the tournament progresses, and calculate a running correlation (you're already doing this at the field level with Spearman rho — extend it to a per-player accuracy score, e.g., "Overperforming model by +2.3 SG/rd").

Model accountability / learning loop (your "tracking traits/weights" ask):

Build a persistent per-event ledger: pre-tournament trait weights → actual round-by-round Spearman rho → post-event calibration delta. You already compute rho per round; store it in a small JSON/CSV time series across events so you can trend "is App 150-200yd weighting improving predictive power event over event?" This is the actual "post mortem" infrastructure — right now Post-Mortem is just a placeholder waiting for final data, but it should ideally show the trait-weight accuracy audit trail, not just final standings.

Consider a simple backtesting harness in Python: for each completed event, re-run the VTS model with varying weight configs against actual results and log which weight combos would have maximized rho. Over several events this becomes a legitimate weight-tuning system rather than a fixed 0.25/0.20/0.15... split.

UX / layout:

The "Tier Intelligence" bars (T1-T5 counts) are underutilized — clicking a tier should filter the Field Explorer table, not just display a count.

Player card sections are dense with repeated text blocks; consolidate "Neutral Skill / Model Read / Full Brief" into a single well-structured module with 3 distinct short takes rather than 3 near-duplicate paragraphs — this alone would make cards feel dramatically less "templated."

The 404 leak and empty Tee-Times tab both suggest you need a shared "EmptyState" component across all tabs so every not-yet-available section renders the same clean, on-brand placeholder instead of ad hoc states.

Tooling suggestions:

For richer/faster brief generation with less duplication risk, consider structured-output prompting (JSON schema enforcing distinct fields per section) rather than free-text generation reused across UI slots — this directly fixes the duplicate-paragraph issue.

For the trait-weight backtesting ledger, a simple SQLite or DuckDB file checked into your repo (rather than flat JSON) would make season-long cross-event trend queries much easier as your event count grows.

Consider Plotly or Observable Plot instead of your current charting for the VTS Journey and Contention Map — both handle sparse-data states (like the 2-point course history problem) more gracefully with built-in "insufficient data" handling.

Overall: the pipeline/backend fixes in your changelog appear to have landed correctly (rankings, SG dedup, player ID matching, R1/R2 leaderboard mechanics all checked out live). The remaining gap is squarely in the narrative/content generation layer — briefs are structurally sound but content-duplicated — and in unbuilt surface area (Tee-Times, R3/R4, Final/Post-Mortem) that's honestly placeholder-flagged rather than broken, except for the one real bug (404 leak on Final tab).

"3. Trait Profile is NOT stuck at grey/50 as originally reported — that part appears fixed. I checked Scheffler (T1), a mid-pack player, and Sargent (T5, bottom of field) — all three show real, differentiated numeric values (e.g., Sargent's App 150–200yd = 1.1, Par-5 Scoring = 13.8; Scheffler's = 72.1 and 43.8 respectively). This may have been fixed since the user's note, or the issue is intermittent/tab-specific — worth a targeted re-check on Rd 2/3/4 specifically since I only spot-checked Rd 1."