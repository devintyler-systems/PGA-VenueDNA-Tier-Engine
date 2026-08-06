# Source Manifest Contract (Phase 4.1) — 2026-08-05

## Decision

VenueDNA defines `source_manifest` schema version 1.0: a canonical contract mapping event-neutral logical source roles to physical event input files. This is a contract-only phase. No parser, resolver, producer change, event package, venue profile, deploy change, or scoring change is authorized or implemented by this decision. The canonical schema is recorded in `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §9; the interface-boundary summary is recorded in `docs/data_contracts.md` under "Source Manifest Contract."

## Context

`engine/enrich_cards.py` reads every event input file by a hardcoded physical filename (`ALL_COURSES_FILES`, `SIM_COURSES_FILES` containing `3Mopen`-named literals, `tpc_twin_cities_CH.csv`). A prior remediation phase added `engine/event_context.py` and a fail-closed `require_supported_context()` capability gate so this producer cannot silently run its remaining event/venue-specific input reads and narrative logic under a mismatched event or venue label (for example a Wyndham Championship manifest). That gate is containment, not generalization — it does not make the producer able to run for another event.

The next step toward genuine venue generalization is separating *what the pipeline needs* (a fixed set of logical source roles: neutral skill horizons, similar-course venue-fit horizons, approach traits, performance, benchmark decomposition, venue history, recent form) from *what one event's export happens to be named*. This decision defines that mapping's contract shape only, so a future, separately authorized phase can implement a parser/resolver against a stable target instead of inventing the shape ad hoc under implementation pressure.

The active-event manifest is `NO_ACTIVE_EVENT`; no event, venue, deploy, or data artifact is in scope for this phase.

## Authorities reviewed

- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `engine/enrich_cards.py`
- `engine/event_context.py`
- `engine/identity_resolver.py`
- `tools/preflight_event.py`
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`
- `docs/data_contracts.md`
- `events/2026_Finished_Events/2026_3m_open/input/`
- `library/venues/tpc_twin_cities/`

## Required logical roles (thirteen)

```text
field
neutral_skill.sg_total.6m
neutral_skill.sg_total.12m
neutral_skill.sg_total.24m
venue_fit.similar_sg.6m
venue_fit.similar_sg.12m
venue_fit.similar_sg.24m
traits.approach.sg_per_shot.12m
traits.approach.proximity.12m
performance.sg_categories.season
benchmark.decomposition
venue_history
recent_form.trending
```

These thirteen roles were checked against the current archived `2026_3m_open` input directory and found sufficient to describe every file `engine/enrich_cards.py` actually reads today (`pga_field.csv`, the three `pga_sg_query_allcourses_l*.csv`, the three `pga_sg_query_3Mopen_similar_l*.csv`, `app_skill_l12_sg.csv`, `app_skill_l12_prox.csv`, `dg_performance_2026.csv`, `dg_decomposition.csv`, `tpc_twin_cities_CH.csv`, `pga_field_trending_table.csv`) — no fourteenth role was needed and none was invented.

## Top-level and per-source schema

See `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §9 for the full, canonical field-by-field definition:

- Top level: `schema_version`, `event_slug`, `venue_slug`, `as_of`, `sources`.
- Each source entry: `role`, `path`, `required`, `missing_behavior`, `schema_id`, `identity_key`, `encoding`, `sha256`, `row_count`, `metadata`.

## Rules adopted (fifteen)

1. Physical filenames are arbitrary and never inferred from event names.
2. Paths are relative to the active event input directory.
3. Absolute, traversal, archived, and repository-escape paths are invalid.
4. Manifest `event_slug` and `venue_slug` must match `EventContext`.
5. Logical roles are unique.
6. All three similar-course horizons must use the same `similar_course_set_id`, `set_version`, and `set_provenance`.
7. Venue-history metadata must match the active `venue_slug`.
8. Required missing sources block before identity resolution or artifact writes.
9. Optional missing sources affect only their declared layer or confidence.
10. Missing data is not numeric zero.
11. `dg_id` remains the preferred identity key; names remain fallback only.
12. API credentials or secret DataGolf keys may not appear.
13. Existing archived 3M physical files remain immutable.
14. Backward compatibility uses explicit manifest entries for legacy filenames; no implicit 3M fallback is authorized.
15. This contract does not change the current producer payload shape, `schemaVersion`, deploy filenames, formula metadata, ranks, tiers, probabilities, penalties, gates, or scoring.

## Naming conflicts identified (not resolved here)

Two pre-existing, unrelated uses of the term "source_manifest" already exist in this repository:

1. `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §3D lists a `"source_manifest": {}` key inside the aspirational `{slug}_event_payload.json` output shape — an output-side summary object, not this input-side, role-keyed schema.
2. `engine/build_event_package.py` builds an in-memory `source_manifest` dict that is only a per-filename `"EXISTS"`/`"MISSING"` presence map with no role, identity, encoding, or provenance metadata.

Neither is this schema. Reconciling the name collision — whether by renaming one, deprecating one, or declaring them formally distinct and cross-referenced — is an open decision deferred to a future phase. It does not block adopting this contract, because neither pre-existing use is implemented against a live producer path today (the `{slug}_event_payload.json` shape in §3D is itself aspirational and does not match `engine/enrich_cards.py`'s actual current payload; `build_event_package.py` is a separate, non-`enrich_cards.py` script).

## Explicitly deferred (not decided here)

- Whether a future `config/active_event.json` gains an additive optional pointer field (for example `source_manifest_file`, following the existing precedent of `event_context_file`, `field_file`, `weather_file`, `tee_times_file` already present as optional manifest fields) is not decided by this phase. Any such addition is a separate, explicitly authorized manifest-schema decision.
- Whether or how an actual `source_manifest.json` is ever authored for the archived `2026_3m_open` event, for Wyndham, or for any other event is not decided here.
- Parser, resolver, and `engine/enrich_cards.py` integration are separate, future, explicitly authorized phases.

## Production divergence

None. `engine/enrich_cards.py` is unchanged by this decision. Its hardcoded `ALL_COURSES_FILES`, `SIM_COURSES_FILES`, and `tpc_twin_cities_CH.csv` reads, its `SUPPORTED_EVENT_SLUG`/`SUPPORTED_VENUE_SLUG` capability gate, its payload shape, and its `schemaVersion` values remain exactly as committed at `7b621dcd4f0afff1423448331e338b10fdc9547c`.

## Amendment — 2026-08-06 (Phase 4.1 documentation corrections)

Six adjudicated corrections were applied to the canonical schema (`standards/04` §9) and its interface summary (`docs/data_contracts.md`). This amendment records what changed and why; it does not reopen or reverse the original decision above. Still contract-only — no parser, resolver, producer, event, or artifact change is authorized by this amendment.

1. **Input-root containment (Rule 3).** The resolved `path` must now be a regular file inside `EventContext.event_root / "input"` specifically, not merely "inside the repository." Symlink/junction escapes are explicitly rejected on the resolved physical path. This extends the existing `engine/event_context.py` safety approach with source-file containment; it does not describe a separate path-safety system, and no resolver exists to enforce it yet.
2. **Similar-course provenance (Rule 6).** Each `venue_fit.similar_sg.{6,12,24}m` entry must now declare its own `horizon_months` (integer `6`/`12`/`24` matching the role suffix) in addition to the shared `similar_course_set_id`/`set_version`/`set_provenance`. Rule 7's "or an unambiguous equivalent" wording for `venue_history` metadata is removed; a `venue_slug` sub-field equal to the top-level `venue_slug` is now the sole, deterministic requirement.
3. **Deterministic role-specific missing behavior.** A new §9.5A in `standards/04` fixes exactly one `required`/`missing_behavior` combination per logical role, replacing the prior open per-event choice. `field` alone blocks release. The six NeutralSkill/VenueFit horizon roles carry new documentation-only labels (`neutral_skill_horizon_incomplete`, `venue_fit_horizon_incomplete`) that delegate outcome entirely to `standards/02` §7.5's two-of-three renormalization / `UNSCORED` / non-computable-VenueFit rules — they do not block release on a single missing horizon and do not add scoring logic. `venue_history` gets its own `venue_history_missing` label, scoped to venue-history confidence only, distinguishing missing raw evidence from the separate neutral `VenueHistoryDeltaRaw = 0.0` model contribution already governed by §7.5. The four remaining optional roles keep `widen_confidence`, each scoped to its own named context outcome only. `skip_layer`/`warn_only` are no longer permitted for any of the thirteen roles.
4. **Integrity assertions.** `sha256` and `row_count` field definitions now state precise future-validator semantics: `null` means not supplied and is never a validated success; a supplied value requires an exact byte-for-byte (`sha256`) or header-excluded-row-count (`row_count`) match, and any mismatch is a validation failure. No validator is implemented by this amendment.
5. **`build_event_package.py` terminology.** The naming note in `standards/04` §9 and the naming caution in `docs/data_contracts.md` now state that `build_event_package.py`'s `source_manifest` is not merely an in-memory dict — it is written verbatim into that producer's own `{slug}_event_payload.json` output under the `source_manifest` key (the same key `standards/04` §3D names). This is a wording correction only; the naming-collision reconciliation itself remains deferred, as originally decided above.
6. **Legacy filename documentation.** `standards/04` §9's introductory paragraph now explicitly cross-references `standards/02` §2 as remaining accurate, current documentation of what `engine/enrich_cards.py` reads today, and states plainly that nothing in this contract implies any current producer reads `source_manifest.json`.

No change in this amendment touches `engine/enrich_cards.py`, `engine/event_context.py`, `engine/build_event_package.py`, `engine/identity_resolver.py`, any scoring file, any event, any payload, or any database. The thirteen logical roles, the archived `2026_3m_open` illustrative table, and DataGolf-ID-first identity precedence are unchanged.

## Amendment 2 — 2026-08-06 (integrity-assertion validation-state clarification)

This amendment further clarifies point 4 of Amendment 1 above (Integrity assertions). It does not reopen or reverse any prior decision. Still contract-only — no parser, resolver, producer, event, or artifact change is authorized by this amendment.

**Previous ambiguity.** Amendment 1's `sha256`/`row_count` definitions established that a supplied value requires an exact match and that a mismatch "is a validation failure, not a warning," but did not state explicitly that a mismatch is release-blocking, did not define how a validator reports its outcome, did not address an unreadable or unhashable source file, and did not state whether `row_count` treats blank or malformed rows as counted data rows. The validator's read-only obligation (never patching a stale value) was stated only for `sha256`, not `row_count`.

**Clarification adopted.** `standards/04` §9.4 now states explicitly that a non-null `sha256` or `row_count` is a declared integrity assertion requiring an exact, independently-computed match; that any mismatch is a release-blocking validation failure; and that a `null` value means the assertion was not supplied — neither a pass nor a failure. A new §9.4A defines four validation-reporting states (`verified`, `mismatch`, `not_asserted`, `unable_to_validate`); states that an unreadable or unhashable source file is always `unable_to_validate` and release-blocking regardless of whether either field was supplied; and states that a validator is read-only with respect to both fields — it must never write, normalize, replace, infer, or backfill either value. `row_count`'s definition now states that a blank line counts as a data row and that `row_count` asserts row cardinality (every physical data row present), not row-shape validity, so a malformed row is still counted, never dropped or estimated. `docs/data_contracts.md` rule 16 is updated to summarize this and defer full semantics to `standards/04` §9.4/§9.4A.

**No production behavior changed.** No parser, resolver, validator, `source_manifest.json` instance, event, payload, deploy artifact, or scoring behavior is created, implemented, or altered by this amendment. `engine/enrich_cards.py` and every other producer remain exactly as before this amendment.
