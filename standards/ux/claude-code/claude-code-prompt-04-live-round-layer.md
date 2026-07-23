# Claude Code Prompt 04 — Live round layer

You are adding a live operations layer to the PGA VenueDNA Open Championship app.

Goal: support round-by-round diagnostics without contaminating the canonical pre-tournament model.

## Scope
Implement:
1. leaderboard polling adapter
2. rank-delta display vs pre-tournament rank
3. promote / hold / downgrade diagnostic states
4. basic watchlist and toast alerts using in-memory state only

## Constraints
- No localStorage or sessionStorage
- Polling is fine; WebSockets are not required
- Pre-event rank must remain visible for auditability
- Live movement must be framed as diagnostic, not as a retroactive rewrite of the model

## Required behavior
- Fetch live leaderboard data on interval from a configurable adapter
- Match records safely to existing player identities
- Show movement from original model rank
- Expose watchlist stars in current session only
- Trigger toasts for major rank moves, new flags, cleared flags, and watched-player movement

## Output
Return:
1. implementation summary
2. files changed
3. adapter assumptions
4. unresolved risks around player matching or feed reliability
