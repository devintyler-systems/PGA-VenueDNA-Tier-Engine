# Target Architecture (Proposal Only)

1. **Shared scoring kernel:** pure versioned functions for NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties/gates, confidence-by-source, and separately computed CeilingIndex. Event configuration supplies traits, gates, and approved overrides; DG remains benchmark-only.
2. **Event/venue configuration contract:** schema-versioned JSON with declared trait weights, correlated-trait cap, short-game/putting floor, sample gates, weather/wave assumptions, and producer provenance.
3. **Canonical output builder:** ID-first player records, source availability, score decomposition, explicit `null`/`unknown` policy, and an immutable pre-event hash.
4. **Deploy copy / integrity step:** copy only declared payloads from output, create a hash manifest plus dynamic-fetch manifest, validate fetches and hashes, never synchronize silently.
5. **Shared static-board app:** one shell, feature flags, a filter registry, chart registry, and a player-card component contract. It consumes pre-event read-only payloads plus a read-only round adapter; it never recalculates core scores.
6. **Quality suite:** artifact-schema, identity-resolution, probability invariants/calibration, deploy manifest, accessibility, performance, and visual-regression tests at 375/768/1024/1440.

Preserved invariants: immutable pre-event artifacts; live overlays only; derivative-market separation; VTS/ceiling distinction; and source-specific confidence.
