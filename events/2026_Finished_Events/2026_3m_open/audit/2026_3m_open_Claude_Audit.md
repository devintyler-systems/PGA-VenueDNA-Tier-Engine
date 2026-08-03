Council finding zero — before anything else: your own audit contradicts itself. Section 3 declares the Rd1/Rd2 player-card join broken (Scheffler showing T5/Debut/50.0/0.0%), then the closing addendum says Scheffler, a mid-pack player, and Sargent all showed differentiated real values, "may have been fixed since... worth a targeted re-check." That's not a footnote — that's the difference between "ship a join-key fix" and "ship nothing, it's already resolved." Don't let Claude Code build a fix for a bug that might not exist anymore. First instruction in the master prompt has to be: reproduce on Rd1 and Rd2 and Rd3 contexts, screenshot/log the actual payload response, confirm before touching code.

Root cause — these are not seven bugs, they're one gap. I pulled your Travelers Championship codebase for comparison (it's sitting in this project's knowledge). Travelers has: a shared name_key normalizer (ascii_fold + fl_to_lf) with an explicit matched flag on every join, a QA validation pass (qa_trait_validation.py) that gates deploy on missing-rate thresholds, an imputation fallback chain that labels every substituted value (imputed_from: player_historical/tier_avg/field_avg), and enrich_cards.py generating genuinely distinct Win Mechanism / Key Risk / Skill Read fields per player off structured trait deltas — not one template string.

3M Open doesn't have that rigor showing up in its output. The templated briefs, the silent fallback-to-"Alternate Entry" instead of an error state, the 404 leak, the hardcoded "R1 Live" label — all of it is what happens when a build skips the join-validation and enrichment layer Travelers already proved out. This isn't "invent a fix." It's "port what's already working and gate the pipeline so this can't ship broken again." That reframes the whole priority list.

P0 — trust-breaking, fix before any event goes live again

Join failure (if confirmed on retest): enforce the same name_key-indexed join across every round context, not just Pre-Tournament. Add the matched: bool flag to the round-context payload; if matched=false, render a visible error state, never the "Late Alternate" template. That template should only ever be reachable for players flagged as verified alternates in event_context — a hard guard, not a silent default.
Templated briefs: port enrich_cards.py's structured-field approach. Add a build-time QA gate: fail the build if any two players' key_risk string match exactly. That's a one-line duplicate check that would have caught this before deploy instead of after.
404 leak: trivial — route through the same EmptyState pattern already correctly used on R3/R4 ("Analysis Pending Live Scores"). No architecture question here, just an unhandled branch.
"R1 Live" label: your own schema already carries is_final: false/true on the round payload (I can see it in the Travelers r3_analysis.json). The front end just isn't reading it for tab labels. Bind the label to that flag — don't invent a new one.

P1 — wiring gaps, not bugs

Tee-Times tab: not a mystery. Your USOPEN field_input.csv already carries First Name / Last Name / Rd1 Tee Time / World Rank — the ingestion shape exists in this system today. 3M's empty tab means that source was never connected for this event, not that the feature needs to be built from scratch.
VTS Journey flat-line chart: side with suppression over blending. The audit's "blend in tour-wide similar-course data" suggestion would contaminate venue-specific history with generic tour data — that's the same class of violation as your no-cross-surface-putting-transfer rule. You already have venuehistoryconfidenceband in the schema for exactly this case — when history rounds ≤2, render a plain "No comparable venue history" badge using that existing field. Don't touch the charting library for this.

P2 — architecture hygiene (do once, benefits every future event)

Extract the name_key/ascii_fold/fl_to_lf join logic — I found it copy-pasted near-identically across build_r1_analysis.py and build_round_analysis.py. One shared module, imported everywhere. Duplicated join logic is exactly how the 3M gap happened in the first place.
Make qa_trait_validation.py-style pre-deploy validation mandatory for every event, not opt-in.
Confirm the single-file HTML + embedded JSON <script type="application/json"> deploy pattern is what 3M Open actually shipped — if it's still three separate files, that's your recurring Netlify path-resolution failure mode showing up again.

P3 — strategic additions, ranked

Event-context-modulated anti-pattern/trait magnitude. The audit's "heat fade risk" idea is the same fix your US Open Learning Loop audit already flagged as unresolved — bomb-and-spray penalized Clark and Burns a full tier when widened fairways should have softened it. Both are "penalty magnitude needs to scale by live event-context signal, not apply as a fixed discount." This is the highest-value item on the list because it closes a gap you already know is costing you tier accuracy — not a UI nice-to-have.
Storyline momentum tag (Riser/Faller/Steady/Bailout) — cheap, derived entirely from Δ Rank you already compute. Ship it.
Structured JSON-schema brief generation — same fix as P0's template problem, just formalized as the standing generation method going forward.
Per-player form-vs-forecast running correlation — real value, but behind P0–P2.
Clickable Tier Intelligence bars → filter table — minor UX, low cost, low priority.
Push back on two audit suggestions: SQLite/DuckDB for the learning ledger is premature — flat CSV/JSON is fine until you're querying across 15+ events; revisit then, not now. Swapping to Plotly/Observable Plot doesn't fix the sparse-data problem, it just redecorates it — skip.