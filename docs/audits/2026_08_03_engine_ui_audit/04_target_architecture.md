# Target Architecture (Proposal Only)

1. **Strict deploy release contract and integrity validation:** declare board mode, the complete fetch target inventory, availability (`required` or `optional_pending`), parse checks, and hashes; never synchronize archives silently.
2. **ID-first identity resolver and provenance:** retain `dg_id`, reject ambiguous fallback joins, emit unresolved rows, and carry match/source provenance through every producer and consumer.
3. **Formal scoring-doctrine reconciliation and decomposition parity:** resolve the VTS conflict before declaring any event pathway canonical; establish golden-event parity for NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties/gates, confidence-by-source, and separately computed CeilingIndex. DG remains benchmark-only.
4. **Canonical pre-event output builder:** only after reconciliation, produce ID-first records, score decomposition, required/optional field designations, immutable pre-event hashes, and an event/venue configuration contract with declared traits, caps, gates, weather/wave assumptions, and provenance.
5. **Shared static-board platform:** one shell with a player-card component contract, filter registry, chart registry, and read-only live-layer adapter. It consumes pre-event payloads and overlays without browser-side core scoring.
6. **Probability calibration and broader CI quality gates:** artifact schema, identity-resolution, probability invariants/calibration, deploy manifest, accessibility, performance, and visual-regression validation at 375/768/1024/1440, as dependencies allow.

The deploy release contract is first in the implementation sequence: declared board mode, complete fetch target inventory, availability classification (`required` or `optional_pending`), parse checks, and hashes. A `required` file must exist, parse, and match its hash. An `optional_pending` target still declares every reachable path; it may be absent only when the board intentionally exposes a pending/unavailable state, and a present file must parse and hash-match. Strict validation reports absent optional targets separately and never infers that classification from absence.

For historical archives, use external profiles under `config/deploy_contracts/archived/`, one per inspected archive. Those profiles may reference and hash existing archived deploy files, but may not rewrite or synchronize them. Future producers emit the release manifest before archival; adding a file inside an archived event needs separate explicit operator authorization.

The Open entry inspected is an inline-styled HTML entry with external `app.js`, not an entirely single-file board. It exposes R1–R4 controls while the inspected archive contains only the generated round files documented by this audit. 3M requires both finite `ROUND_PAYLOADS` targets loaded via `fetch(url)` and the generic `data/r${r}_analysis.json` target to be declared.

Preserved invariants: immutable pre-event artifacts; live overlays only; derivative-market separation; VTS/ceiling distinction; and source-specific confidence.
