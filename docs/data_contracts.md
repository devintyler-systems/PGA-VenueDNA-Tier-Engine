# PGA VenueDNA Data Contracts
# Version 1.0
# Canonical interface contract for engine, artifacts, static board, audit, and database workflows

## Purpose

This document defines the data boundaries inside PGA VenueDNA.

It protects the projection engine from deploy-layer drift, protects static boards from payload breaks, preserves player identity across DataGolf and local sources, and keeps pre-event, live, and audit workflows separately auditable.

This file governs interface shape. It does not redefine scoring math. Use `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` for model logic, `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` for artifact packaging, and `standards/VENUEDNA_CODEX_SCHEMA.md` for typed code contracts.

## Authority

Resolve contract conflicts in this order:

1. Explicit approved task that declares a deliberate contract migration
2. `AGENTS.md`
3. `SYSTEM_HANDOFF_SPEC.md`
4. `standards/VENUEDNA_CODEX_SCHEMA.md`
5. `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
6. This file
7. Current `app.js` fetch calls and parser behavior
8. Historical event artifacts

A historical payload is not canonical merely because an older board consumed it.

## Contract Boundaries

| Producer | Consumer | Contract | Rule |
|---|---|---|---|
| DataGolf API or manual source | Ingestion scripts | Raw source data | Preserve source files; never edit raw data in place |
| Ingestion scripts | SQLite and processed datasets | Normalized player, field, tournament, SG, and conditions records | DataGolf ID is canonical player identity |
| Venue library | Pre-event engine | Venue profile and supporting venue files | `library/venues/` is canonical |
| Pre-event engine | Event output | Immutable pre-event projection artifact | Lock before Round 1 |
| Live engine | `output/roundN/` | Round-specific live artifact | Never overwrite pre-event or earlier-round output |
| Output or deploy builder | `deploy/data/` | Static-board JSON and CSV payloads | Must match `app.js` fetch contract |
| Static board | Browser | `index.html`, `app.js`, `styles.css`, payloads | Board does not calculate core scores |
| Audit workflow | `audit/` and write-back log | Audit and proposed model changes | Write-backs require approval |

## Player Identity

### Canonical Keys

- `dg_id` is the canonical external player key.
- `player_id` is the canonical internal player key.
- `player_name` is display data and a fallback join field only.
- `event_slug` and `venue_slug` use lowercase snake_case.
- `year` is a four-digit integer.

### Identity Rules

1. Join by DataGolf ID whenever both sources contain it.
2. Use the `players` crosswalk before falling back to player name.
3. Normalize display names only as a fallback: whitespace trim, case normalization, diacritic folding, and documented encoding fallback.
4. Log unresolved and ambiguous matches.
5. Never silently duplicate a player because source spellings differ.
6. Never discard a source row because a display-name join fails.

## Event State

`config/active_event.json` is the only machine-readable pointer to the current event.

Valid statuses:

- `NO_ACTIVE_EVENT`
- `PRE_EVENT`
- `ROUND_1`
- `ROUND_2`
- `ROUND_3`
- `ROUND_4`
- `FINAL_AUDIT`
- `ARCHIVED`

When status is `NO_ACTIVE_EVENT`, event builders must not generate event-bound pre-event or live artifacts.

When status is `PRE_EVENT`, builders may create pre-event projections but not live outputs.

When status is `ROUND_1` through `ROUND_4`, the pre-event artifact is immutable and every new live result must write to its own round-specific path.

When status is `FINAL_AUDIT`, builders may create audits and write-back proposals but may not automatically change canonical rules.

## Event Paths

```text
events/{event_slug}/
  input/
  engine/
  output/
    round1/
    round2/
    round3/
    round4/
    final_tournament/
  deploy/
    data/
  audit/
```

For an active event, the manifest must point to:

- `event_root`
- canonical venue profile
- deploy root
- audit root
- pre-event artifact once live work begins
- current live round and live artifact when applicable

## Venue Contract

Canonical venue intelligence lives at:

```text
library/venues/{venue_slug}/
```

Required venue profile:

```text
library/venues/{venue_slug}/{venue_slug}_venue_profile.md
```

Potential supporting venue files:

```text
{venue_slug}_CH.csv
{venue_slug}_full_course_weather_data_{year}.json
{venue_slug}_weather.txt
```

Event-local venue copies may exist for reproducibility. They do not supersede the venue library unless an approved event-specific override names the conflict and expiry.

## Core Projection Contract

The core projection is decomposed. Do not treat one composite display score as the only source of truth.

Required components:

- `neutral_skill_score`
- `venue_fit_delta`
- `venue_history_delta`
- `penalties_applied`
- `gates_applied`
- `composite_score`
- `confidence_band`
- `structural_justification`

### Required Player Projection Shape

```json
{
  "player_id": "string",
  "player_name": "string",
  "tier": 1,
  "neutral_skill_score": 0.0,
  "venue_fit_delta": 0.0,
  "venue_history_delta": 0.0,
  "penalties_applied": [],
  "gates_applied": [],
  "composite_score": 0.0,
  "confidence_band": "HIGH",
  "structural_justification": "Named venue mechanism",
  "debut_flag": false,
  "debut_framework_applied": null
}
```

### Projection Rules

- Scores remain normalized 0-100 unless a canonical scoring rule explicitly authorizes another scale.
- Tier 1 requires a non-empty structural mechanism.
- `THIN` confidence requires a named missing or weak evidence source.
- Penalties and gates remain visible outside the composite.
- DFS salary, betting price, market rank, and ownership are derivative inputs. They cannot change core projection ranks.

## Pre-Event Artifact

A pre-event projection is immutable when tournament live analysis begins.

It must preserve:

- Full five-tier context
- Player-level component decomposition
- Confidence source
- Anti-pattern flags
- Risk register
- Relevant source and version metadata
- Model Council findings when triggered

Do not overwrite it to create a live update.

## Live Artifact

A live artifact is a new round-specific output joined to the immutable pre-event projection spine.

### Required Live Metadata

```json
{
  "event_slug": "string",
  "round": 2,
  "generated_at": "ISO8601",
  "pre_event_artifact": "relative/path/to/pre_event_artifact.json",
  "authoritative_spine": "relative/path/to/leaderboard_or_round_spine.csv",
  "player_updates": [],
  "conditions_context": {},
  "scenario_fencing": {},
  "diagnostics": {}
}
```

### Live Rules

- `round` must match the output folder and `active_event.json`.
- Live output may add diagnostics and live interpretation but may not rewrite pre-event score components.
- Promotions and downgrades must identify structural evidence, conditions evidence, or variance.
- Preserve pre-event thesis separately from live inference.
- Round 3 output cannot overwrite Round 2 output.
- Missing SG, weather, or tee-time data widens confidence. It does not justify invented evidence.

## Static Deploy Contract

```text
events/{event_slug}/deploy/
  index.html
  app.js
  styles.css
  data/
```

### Protected Deploy Files

- `index.html`
- `app.js`
- `styles.css`
- Every JSON and CSV file under `deploy/data/`

### Fetch Rules

`app.js` is the executable source of truth for the payload paths consumed by the board.

Before changing a deploy payload:

1. Inspect every literal `fetch()`, `d3.csv()`, and `d3.json()` call.
2. Verify every target exists under the event deploy root.
3. Verify JSON parses and CSV has a header.
4. Update all fetch references in the same change if a filename moves or changes.
5. Validate the fixture harness or browser board.
6. Do not place raw data, temporary exports, notes, or planning documents in `deploy/data/`.

### Dynamic Payload Manifest (Legacy, Schema 1.0)

Boards may use dynamic local fetches only when their deploy root contains an optional
`payload_manifest.json`. Its presence is additive: boards without one retain normal
dynamic-target warnings and fail strict validation.

The manifest declares the exact runtime expression, a generic local-file pattern, and
the complete expected local files. Every expected file must exist and pass the normal
JSON or CSV validation before strict validation accepts the dynamic expression.

```json
{
  "schema_version": "1.0",
  "dynamic_fetches": [
    {
      "expression": "data/r${round}_analysis.json",
      "pattern": "data/r{round}_analysis.json",
      "expected_files": [
        "data/r1_analysis.json",
        "data/r2_analysis.json",
        "data/r3_analysis.json",
        "data/r4_analysis.json"
      ]
    }
  ]
}
```

`expression` must exactly match the dynamic first argument found in `app.js`.
`pattern` uses named placeholders such as `{round}`; it is not an executable path
template. `expected_files` is the authoritative enumeration and must use local,
deploy-root-relative paths that match the pattern. Do not use this manifest to
authorize external URLs or undeclared runtime paths.

Validate a dynamic board with:

```powershell
python tools/validate_deploy_contract.py --deploy-root events/{event_slug}/deploy --strict
```

Use `--payload-manifest path/to/manifest.json` only when the event intentionally
stores the manifest outside the default deploy-root location.

This schema-1.0 manifest and the `--deploy-root`/`--payload-manifest` CLI flow remain
fully supported. It is a legacy compatibility path, retained alongside schema 1.1
below, not superseded by it.

### External Deploy Profile v1.1

**Purpose.** A schema-1.0 payload manifest lives inside a live event's own deploy
root and is meant for a board that is still being produced. Once an event is
archived, its deploy files become read-only history: nothing should write into
`events/2026_Finished_Events/{event_slug}/`, including a manifest. Schema 1.1
introduces an `archived_deploy` profile that lives entirely outside the archive and
only references and hashes existing archive files. It never rewrites or
synchronizes them.

**`profile_type: "archived_deploy"`.** The profile is a standalone JSON document
identified by `schema_version: "1.1"` and `profile_type: "archived_deploy"`. It
declares the board's asset inventory, dynamic fetch expressions, and a complete
SHA-256 integrity manifest for everything the board can load.

**External historical profile location.**

```text
config/deploy_contracts/archived/
```

One profile per inspected archive, named for the archived event slug (for example
`config/deploy_contracts/archived/2026_example.json`).

**Board modes.** `board.mode` is one of:

- `static_app` — external `app.js` and `styles.css`; requires at least one script and
  one stylesheet.
- `harness` — a fixture-harness board with the same asset-count rules as
  `static_app`; filenames may differ from the `index.html`/`app.js`/`styles.css`
  convention.
- `inline_styled_app` — an entry document with inline styling; requires at least one
  script but `board.stylesheets` may be empty.

Every declared `entry_html`, `scripts`, `stylesheets`, and `data_roots` entry must
exist under `deploy_root` before the profile is generated or accepted.

**Required versus optional-pending targets.** Every dynamic fetch target declares an
`availability` of `required` or `optional_pending`. A `required` target must exist,
parse, and hash-match. An `optional_pending` target may be absent — that is reported
separately and never inferred from absence — but a present optional-pending target
must still parse and hash-match.

**SHA-256 integrity rules.** `integrity.algorithm` is `"sha256"`. `integrity.files`
covers, at minimum: the entry document, every script, every stylesheet, every
present local literal fetch target, every present required dynamic target, and every
present optional-pending dynamic target. Digests are raw-byte SHA-256, lowercase hex,
64 characters. Validation never writes a hash back into any file.

**Path safety.** `deploy_root` and every runtime path declared inside the profile
(`board.entry_html`, `board.scripts`, `board.stylesheets`, `board.data_roots`,
dynamic target paths, `integrity.files[].path`) is a forward-slash path relative to
its base directory. Absolute paths, drive prefixes, UNC paths, backslashes, and any
`..` segment are rejected. Containment is checked with `Path.resolve()` plus
`relative_to()`, not string prefixes, so a symlink escape is also rejected.

**Full example profile.**

```json
{
  "schema_version": "1.1",
  "profile_type": "archived_deploy",
  "event_slug": "2026_example",
  "deploy_root": "events/2026_Finished_Events/2026_example/deploy",
  "board": {
    "mode": "static_app",
    "entry_html": "index.html",
    "scripts": ["app.js"],
    "stylesheets": ["styles.css"],
    "data_roots": ["data"]
  },
  "dynamic_fetches": [
    {
      "expression": "data/r${r}_analysis.json",
      "pattern": "data/r{r}_analysis.json",
      "targets": [
        {"path": "data/r1_analysis.json", "availability": "required"},
        {"path": "data/r4_analysis.json", "availability": "optional_pending"}
      ]
    }
  ],
  "integrity": {
    "algorithm": "sha256",
    "files": [
      {"path": "app.js", "sha256": "…64 lowercase hex characters…"},
      {"path": "data/r1_analysis.json", "sha256": "…64 lowercase hex characters…"},
      {"path": "index.html", "sha256": "…64 lowercase hex characters…"},
      {"path": "styles.css", "sha256": "…64 lowercase hex characters…"}
    ]
  }
}
```

**Validator command.**

```powershell
python tools/validate_deploy_contract.py --deploy-profile config/deploy_contracts/archived/2026_example.json
```

`--deploy-profile` is mutually exclusive with `--deploy-root` and `--payload-manifest`.

**Builder command.** `tools/build_deploy_profile.py` is a deterministic,
standard-library-only generator. It reads an existing deploy tree, discovers literal
and dynamic fetch targets in the declared scripts, computes integrity hashes, and
writes a profile that already passes `validate_deploy_profile()`. It never writes
into `deploy_root`.

```powershell
python tools\build_deploy_profile.py `
  --deploy-root events/2026_Finished_Events/2026_example/deploy `
  --output config/deploy_contracts/archived/2026_example.json `
  --event-slug 2026_example `
  --board-mode static_app `
  --entry-html index.html `
  --script app.js `
  --stylesheet styles.css `
  --data-root data `
  --dynamic-declarations path\to\dynamic_declarations.json
```

A dynamic-fetch expression detected in a declared script always requires an explicit
`--dynamic-declarations` file; the builder never guesses `required` versus
`optional_pending` status.

`data_roots` generation rule (stricter than the structural validator): empty
`data_roots` is permitted only when the board consumes no local payloads. Every local
literal or dynamic target must be contained beneath a declared data root. The builder
enforces this before it will generate a profile; the structural validator itself does
not require a minimum `data_roots` count, only that every declared root exists.

**Dry-run command.** Builds and validates the profile in memory and prints the exact
JSON that would be written; writes no file and creates no output directory.

```powershell
python tools\build_deploy_profile.py --deploy-root ... --output ... --event-slug ... `
  --board-mode static_app --entry-html index.html --script app.js --stylesheet styles.css `
  --data-root data --dry-run
```

**Check command.** Regenerates the expected profile in memory and compares it
byte-for-byte against the existing output file; writes nothing; exits nonzero when
the file is stale or missing.

```powershell
python tools\build_deploy_profile.py --deploy-root ... --output ... --event-slug ... `
  --board-mode static_app --entry-html index.html --script app.js --stylesheet styles.css `
  --data-root data --check
```

**Historical archive immutability.** A profile under
`config/deploy_contracts/archived/` may reference and hash files that already exist
inside `events/2026_Finished_Events/{event_slug}/deploy/`. Neither the builder nor the
validator ever writes into an archived event directory. Adding a file inside an
archived event requires separate explicit operator authorization outside this
tooling.

**Future profiles should be generated before archival.** A live event's deploy
builder should emit its schema-1.1 profile as part of the release, before the event
moves to `events/2026_Finished_Events/`, so the archive already carries its own
integrity manifest.

**Builder and validator never synchronize or rewrite archive contents.** Both tools
are read-only against `deploy_root`. If a hash mismatch or missing file is found, the
fix is to correct the producer that created the archive, not to have the builder or
validator patch the archive in place.

**Legacy schema-1.0 manifests remain supported**, unchanged, alongside schema 1.1.

### Board Rules

- Static-board code displays approved artifacts.
- Static-board code does not recalculate NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, or gates.
- A payload migration requires coordinated producer, consumer, test, and documentation changes.
- Do not change a payload filename merely for cosmetic consistency.

## CSV Rules

- UTF-8 is required; UTF-8 with BOM is accepted for spreadsheet compatibility.
- A header row is mandatory.
- Do not include an unnamed index column.
- Engine-generated headers use snake_case.
- Preserve `player_id` or `dg_id` when available.
- Missing numeric values are blank or documented null-equivalents. Do not place text sentinels inside numeric fields.

### Minimum Ranking Export

```csv
player_id,player_name,tier,neutral_skill_score,venue_fit_delta,venue_history_delta,composite_score,confidence_band
```

Additional fields are allowed. Do not remove, rename, or retype this core set without a contract migration.

## JSON Rules

- JSON is UTF-8.
- Durable artifacts include `schema_version`.
- Durable artifacts include event and generation metadata.
- Use snake_case keys.
- Use `null` for unavailable optional scalar values.
- Use `[]` for empty collections.
- Do not change a field type in place.
- Do not reuse a field name for a different meaning.

### Versioning

Increment schema version when a field is removed, renamed, retyped, or materially changes semantic meaning.

Additive optional fields may retain the same major version when backward compatible.

## SQLite Rules

### Database Roles

- `data/venuedna_master.db`: tracked processed production master.
- `data/venue_dna.db`: untracked DataGolf raw cache and harvester working store.

### Requirements

- Database migrations are idempotent.
- Every schema task names its target database.
- Validate impacted tables and scripts after migration.
- Never add global `*.db` gitignore behavior.
- Preserve DataGolf ID identity mapping in `players`.
- Do not treat raw cache data as production model truth.

## Audit and Write-Back Contract

An audit must preserve:

- Event context
- Original projection reference
- Tier 1 and Tier 2 accountability
- Anti-pattern review
- Significant miss log
- Miss layer and root cause
- Proposed write-back recommendations
- Engine-rule flags

### Miss Layers

Use one or more:

- `NEUTRAL_SKILL`
- `VENUE_FIT`
- `VENUE_HISTORY`
- `PENALTY`
- `GATE`
- `DEBUT`
- `DATA`
- `COUNCIL`
- `CONDITIONS`

### Write-Back Rules

- Write-backs are proposed diffs, not automatic changes.
- Every proposed venue change names a target file and target section.
- Every proposed global rule change becomes an engine-rule flag.
- Every proposal states evidence basis and evidence threshold.
- One event is not sufficient justification for permanent rule changes without threshold evidence.

## Contract Migration Protocol

A migration is required when a producer or consumer changes payload shape, file location, field name, field type, field meaning, or identifier behavior.

Every migration includes:

1. Scope statement
2. Version or compatibility decision
3. Producer change
4. Consumer change
5. Test change
6. Existing artifact rebuild or compatibility plan
7. Rollback plan for active deploy behavior

Do not combine a contract migration with unrelated cleanup or refactoring.

## Required Validation

Run the narrowest applicable command:

```powershell
python tools/preflight_event.py --phase pre_event
python tools/preflight_event.py --phase live
python tools/preflight_event.py --phase audit
python tools/validate_deploy_contract.py
```

For a release candidate or production board handoff:

```powershell
python tools/preflight_event.py --phase pre_event --strict
python tools/validate_deploy_contract.py --strict
```

The scripts catch structural contract failures. They do not replace browser validation, scoring regression tests, or Model Council review.

## Failure Behavior

When a contract check fails:

1. Stop the affected build or deploy action.
2. Name the missing file, invalid path, broken payload, or incompatible field.
3. Preserve approved existing artifacts.
4. Correct the producer or consumer at the correct layer.
5. Rerun targeted validation.
6. Do not bypass a failure by copying files into arbitrary paths or weakening the contract.
