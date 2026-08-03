# Claude Code Prompt 04 — Live round layer

You are adding a live operations layer to the PGA VenueDNA Open Championship app.

Goal: support round-by-round diagnostics without contaminating the canonical pre-tournament model.

## Scope
Implement:
1. leaderboard polling adapter
2. rank-delta display vs pre-tournament rank
3. promote / hold / downgrade diagnostic states
4. basic watchlist and toast alerts using in-memory state only
5. Alpha/Beta/Gamma live badge grouping per `02_PGA_VENUEDNA_SCORING_SPEC.md` §16–§18

## Constraints
- No localStorage or sessionStorage
- Polling is fine; WebSockets are not required
- Pre-event rank must remain visible for auditability
- Live movement must be framed as diagnostic, not as a retroactive rewrite of the model
- Do not recompute VenueDNA scores, `LiveConvictionScore`, or `CeilingIndex` in browser code — the UI only reads and groups fields that the engine/build layer already computed and wrote into the event payload / live-round artifact. If a required field is missing from the payload, surface that as a data gap, not a UI-side calculation.

## Required behavior
- Fetch live leaderboard data on interval from a configurable adapter
- Match records safely to existing player identities
- Show movement from original model rank
- Read `LiveConvictionScore`, `CeilingIndex` (and `vtsceil`), and `structurally_live` (`diagnostic_label`) directly from the event payload / live-round artifact for each player
- Group `structurally_live` players into Alpha / Beta / Gamma live badges using the scoring-spec thresholds (§18): Alpha = top `LiveConvictionScore` cluster (typically 3–5 names with a real win path), Beta = credible contenders with a named constraint, Gamma = remaining structurally-live players with a weak practical win path
- Render the Promotion Watch / diagnostic buckets as badge-grouped, `LiveConvictionScore`-ranked lists (Alpha, then Beta, then Gamma) — never as a single flat "Structurally Live" tag applied to dozens of names
- Every promotion/downgrade between badge tiers displayed in the UI must show the mechanism string the engine attached (e.g., "Alpha → Beta: tee-time downgrade + SG:APP drop"), not a bare rank-delta number
- Expose watchlist stars in current session only
- Trigger toasts for major rank moves, new flags, cleared flags, watched-player movement, and Alpha/Beta/Gamma badge changes
- If a scenario/what-if view exists, visually fence it (distinct container, border, or panel) and label it clearly as non-official — it must never be styled or positioned so it could be mistaken for the official live board

## Non-negotiables
- Live layer is diagnostic only. `structurally_live` is eligibility, not a conviction ranking — the badge tier is the label users see.
- Official ranks, tiers, and VTS come from the core pre-tournament artifacts (`vts_final`, `VenueDNA_rank`, `VenueDNA_tier`) and are never overwritten by live-layer or scenario-mode output.
- Scenario/what-if mode, if present, is kept visually and structurally distinct from official mode at all times.

## Output
Return:
1. implementation summary
2. files changed
3. adapter assumptions
4. which payload/artifact fields were confirmed present (`LiveConvictionScore`, `CeilingIndex`, `vtsceil`, `structurally_live`) vs. missing and needing an upstream builder change
5. unresolved risks around player matching or feed reliability
