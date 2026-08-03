# PGA VenueDNA Tier Engine
project_handle: pga_venuedna

## Identity

PGA VenueDNA is a course-DNA prediction engine for PGA Tour tournaments.

Its core job is to produce venue-specific, audit-ready player projections. It scores players through separate NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, gates, and uncertainty layers. Core output is ranked player lists, five-tier projections, live round updates, and post-tournament audits.

Do not function as a generic golf assistant, consensus repeater, news summarizer, or generic betting model. Every material player conclusion must connect to a named structural venue mechanism.

## Instruction Precedence

Resolve instructions in this order:

1. Explicit task request
2. This `AGENTS.md`
3. Active event files and event-specific instructions
4. `SYSTEM_HANDOFF_SPEC.md`
5. Canonical standards in `standards/`
6. Repository implementation, tests, and deploy contracts
7. Historical artifacts and archived event files

`CLAUDE.md` governs Claude Code under the same doctrine as this file. If the two visibly diverge on anything beyond tool-specific mechanics (skill invocation, terminal syntax), treat it as a conflict and apply the rule below rather than picking one silently.

When two authorities conflict:

1. Stop.
2. Name the exact files or instructions in conflict.
3. State which authority governs.
4. Propose the smallest safe resolution.
5. Do not silently blend incompatible rules or write outside task scope.

## Stack

- Python for ingestion, scoring, live analysis, artifact generation, and validation
- HTML, JavaScript, and CSS for static event board deployments
- SQLite production database: `data/venuedna_master.db`
- SQLite raw API cache: `data/venue_dna.db`
- Data sources: DataGolf API, approved manual exports, venue profiles, weather inputs
- Deployment: static HTML/JS/CSS event boards served locally per event
- Repository: `devintyler83/PGA-VenueDNA-Tier-Engine`
- Local workspace: `C:\PGA_VenueDNA`

## System Contracts

- `SYSTEM_HANDOFF_SPEC.md` governs ownership, inter-agent handoffs, data-contract safety, live-event safety, and definition of done.
- `standards/VENUEDNA_CODEX_SCHEMA.md` governs code-generated JSON artifacts, SQLite records, Python interfaces, artifact validation, file naming, and write-back diffs.
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` governs core scoring logic.
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md` governs audit classification and learning write-backs.
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` governs permanent artifact structure, names, and packaging.
- `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md` governs Council triggers, objections, synthesis, escalation, and duplication control.
- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md` governs the durable system architecture.
- `config/active_event.json` is the machine-readable pointer to the current event state.

Do not create duplicate canonical copies of standards files in event folders, deploy folders, temporary folders, or tool-specific staging folders.

## UI/UX Design Skill

Repository skill:

- `.codex/skills/ui-ux-pro-max/SKILL.md`
- Codex: read `.codex/skills/ui-ux-pro-max/SKILL.md` directly when a material UI/UX task triggers this section; treat its workflow as a repository design standard.
- Claude Code: invoke the native `ui-ux-pro-max` skill via the Skill tool when a material UI/UX task triggers this section; it implements the same workflow. Do not read `.codex/skills/ui-ux-pro-max/SKILL.md` directly.

Use `ui-ux-pro-max` only for a material user-interface task:

- New static event board or dashboard
- Material redesign of an existing deploy surface
- New player drawer, table, card, filter, tab, chart, modal, or responsive layout
- UX or accessibility remediation
- Visual hierarchy, information-density, mobile, interaction, or dashboard readability problem


Do not invoke the skill for:

- Python scoring, data ingestion, SQLite, model logic, artifact generation, or audits
- Small copy edits
- One-line CSS fixes with no design-system consequence
- Non-visual deploy-data or payload changes

Before UI implementation:

1. Inspect the active event manifest and actual deploy surface.
2. Inspect `index.html`, `app.js`, `styles.css`, current payloads, and the fixture harness where present.
3. Run the skill's required `--design-system` search for a material new or redesigned UI.
4. Use a VenueDNA-specific query, not a generic dashboard query.
5. Persist the approved result only when it governs repeated pages or deploy surfaces.

Default design-system query:

```powershell
python .codex\skills\ui-ux-pro-max\scripts\search.py `
  "PGA Tour golf analytics dashboard data-dense executive dark mode venue intelligence" `
  --design-system --persist -p "PGA VenueDNA Tier Engine" -f markdown
```

For page-specific board work, use a page override:

```powershell
python .codex\skills\ui-ux-pro-max\scripts\search.py `
  "PGA Tour venue projection dashboard data-dense golf analytics" `
  --design-system --persist -p "PGA VenueDNA Tier Engine" `
  --page "event_board" -f markdown
```

Treat generated design-system files as supporting design guidance, not canonical scoring or data-contract authority.

VenueDNA UI rules:

- Preserve information density without visual clutter.
- Prioritize tier hierarchy, venue mechanism, confidence source, risk vector, live-state distinction, and player-comparison scanability.
- Preserve clear separation between Pre-Event Model and Live Update state.
- Use actual VenueDNA terms, score components, and payload fields. Do not invent generic dashboard metrics.
- Use SVG icons from one consistent icon system. Do not use emoji as UI icons.
- Preserve visible keyboard focus, readable contrast, responsive behavior, and `prefers-reduced-motion`.
- Do not use hover transforms that shift layout.
- Do not sacrifice data readability for decorative effects.
- Do not modify static-board payloads, fetch paths, or core model logic solely to satisfy a visual preference.

Before completing material UI work:

1. Validate all `app.js` fetch targets and payload contracts.
2. Test at 375px, 768px, 1024px, and 1440px widths.
3. Test the active theme or both themes when theme switching exists.
4. Confirm no horizontal mobile overflow, clipped modal content, or hidden fixed-header content.
5. Confirm no regression in Pre-Event versus Live state separation.
6. Run the fixture harness or browser validation.

## Actual Architecture

This is a pure pipeline plus static deploy system. It is not a Streamlit application.

1. Input: DataGolf CSVs, approved manual ingestion, venue profile, weather JSON, tee times, and round data enter `events/{event_slug}/input/`.
2. Engine: shared Python scripts in `engine/` calculate pre-event and live VenueDNA outputs.
3. Output: scored CSVs, JSON artifacts, trait matrices, diagnostics, and round artifacts write to `events/{event_slug}/output/`.
4. Deploy: static `app.js`, `index.html`, and `styles.css` consume approved files in `events/{event_slug}/deploy/data/`.
5. Audit: event accountability, Model Council review, diagnostics, and approved write-backs write to `events/{event_slug}/audit/`.
6. Archive: completed events move intact to `events/2026_Finished_Events/{event_slug}/`.

## Pipeline Roles

Keep these roles distinct.

### Pre-Event Projection Builder

Produces the canonical pre-event projection.

- Applies NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, gates, and confidence.
- Produces the complete five-tier ranking context.
- Is immutable once live tournament analysis starts.
- Does not use DFS pricing, betting markets, salary, ownership, or in-tournament results to alter core projection logic.

### Live Update Builder

Produces round-specific live analysis after Round 1 begins.

- Uses the canonical pre-event projection as a read-only spine.
- Joins live leaderboard, hole-level or SG diagnostics, remaining tee times, current conditions, and forecast context.
- Separates structural evidence from noise and variance.
- Creates a new round-specific artifact.
- Never overwrites a canonical pre-event artifact or prior-round live artifact.

### Deploy Builder

Transforms validated artifacts into static board payloads.

- Consumes approved output artifacts.
- Preserves the JSON and CSV contract required by `app.js`.
- Does not recalculate scoring logic.
- Does not rename or relocate deploy payloads without updating every affected fetch reference and validating the board.

## Key Files

### Shared Engine

- `engine/build_round_analysis.py` — main shared round and live scoring engine; event configs may be embedded
- `engine/traits_calculator.py` — venue trait calculations
- `engine/latent_model.py` — latent venue-fit model
- `engine/enrich_cards.py` — player-card enrichment
- `engine/dg_api_harvester.py` — DataGolf API ingestion and raw-cache writer
- `engine/datagolf_client.py` — canonical production database schema and DataGolf client behavior
- `engine/ingest_manual_exports.py` — approved manual-export ingestion
- `engine/initialize_venues.py` — course-profile seeding

### Canonical Data

- `data/venuedna_master.db` — tracked production master database
- `data/venue_dna.db` — untracked local DataGolf API cache
- `config/db_config.json` — harvester configuration, rate limits, DataGolf settings, sparse-column settings
- `config/active_event.json` — active-event pointer and event lifecycle state

### Standards

- `standards/00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
- `standards/03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `standards/05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
- `standards/VENUEDNA_CODEX_SCHEMA.md`

### Repository Governance

- `AGENTS.md` — Codex's repository-wide execution rules (this file)
- `CLAUDE.md` — Claude Code's repository-wide execution rules; same doctrine as this file
- `SYSTEM_HANDOFF_SPEC.md` — cross-agent ownership and handoff rules
- `tests/` — engine, payload, artifact, identity, and regression tests
- `tools/` — utility and preflight scripts
- `docs/` — planning documents, SOPs, data contracts, feature notes, and operating references

### Venue Library

- `library/venues/{venue_slug}/{venue_slug}_venue_profile.md`
- `library/venues/{venue_slug}/{venue_slug}_CH.csv`
- `library/venues/{venue_slug}/{venue_slug}_full_course_weather_data_{year}.json`
- `library/venues/{venue_slug}/{venue_slug}_weather.txt`

## Canonical Folder Structure

```text
events/{event_slug}/
  input/                 Raw venue/course CSVs, DataGolf pulls, weather JSON, tee times
  engine/                Event-specific engine forks when required; root engine is shared fallback
  output/                Scored CSVs, JSON payloads, trait matrices, diagnostics
    round1/              Round 1 live artifacts
    round2/              Round 2 live artifacts
    round3/              Round 3 live artifacts
    round4/              Round 4 live artifacts
    final_tournament/    Final event and post-tournament artifacts
  deploy/                Static board application
    data/                Protected JSON/CSV payloads consumed by app.js
  audit/                 Audit logs, Council reviews, diagnostics, write-back artifacts

events/2026_Finished_Events/{event_slug}/
  Same internal layout as an active event.
  Move an event here only after the tournament is complete.
  Before moving, inspect and update every hardcoded event path in scripts, tests, and CI workflows.

library/venues/{venue_slug}/
  {venue_slug}_venue_profile.md
  {venue_slug}_CH.csv
  {venue_slug}_full_course_weather_data_{year}.json
  {venue_slug}_weather.txt

data/raw/                 Incoming DataGolf pulls, unprocessed
data/processed/           Cleaned and normalized tournament/player data
data/venue/               Course characteristics and normalized venue features
library/engine/           Master prompts, rebuild guides, and durable engine references
library/templates/        Intake forms and repository templates
standards/                Canonical model doctrine and contracts
docs/                     Planning docs, specs, SOPs, data contracts, feature ideas
tests/                    Unit, integration, contract, and regression tests
tools/                    Utility, validation, and maintenance scripts
config/                   Machine-readable configuration and active-event state
```

## Source Priority

When repository context is available, inspect sources in this order:

1. `config/active_event.json`
2. Active event deploy files:
   - `events/{event_slug}/deploy/index.html`
   - `events/{event_slug}/deploy/app.js`
   - `events/{event_slug}/deploy/styles.css`
   - `events/{event_slug}/deploy/data/*`
3. Active event engine, output, and audit files:
   - `events/{event_slug}/engine/*`
   - `events/{event_slug}/output/*`
   - `events/{event_slug}/audit/*`
4. Shared engine:
   - `engine/build_round_analysis.py`
   - `engine/traits_calculator.py`
   - `engine/latent_model.py`
   - `engine/enrich_cards.py`
   - `engine/dg_api_harvester.py`
5. Canonical standards and venue library:
   - `standards/*`
   - `library/venues/{venue_slug}/*`
6. Database schema, migrations, and tests:
   - `data/venuedna_master.db`
   - `engine/datagolf_client.py`
   - `tests/*`
7. Archived events only when explicitly requested or needed for validated historical comparison.

Repository implementation governs current code behavior. Canonical standards govern model doctrine. Do not assume a historical artifact is current implementation truth.

## Naming Conventions

- Event files: `{year}_{event_slug}_{descriptor}.{ext}`
  - Correct: `2026_3m_open_vts_full.csv`
  - Incorrect: `3m_open_2026_vts_full.csv`
- Venue files: `{venue_slug}_{descriptor}.{ext}`
  - Correct: `tpc_twin_cities_venue_profile.md`
- Event folder slugs: lowercase snake_case
  - Correct: `2026_wyndham_championship`
- Venue folder slugs: lowercase snake_case
  - Correct: `sedgefield_country_club`
- Round folders: `round1/`, `round2/`, `round3/`, `round4/`, `final_tournament/`
- No spaces in filenames.
- Use underscores, not spaces or hyphens, unless an existing protected deploy contract requires otherwise.
- Deploy filenames must match `app.js` fetch calls exactly.
- JSON artifacts must comply with `standards/VENUEDNA_CODEX_SCHEMA.md` and `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`.

## Data Model

Core database tables include:

- `players` — canonical internal player records, player names, DataGolf IDs, and identity crosswalk
- `tournaments` — tournament, venue, year, and conditions metadata
- `strokes_gained` — player-level, tournament-level SG splits
- `venue_profiles` — normalized course-DNA features
- `venue_scores` — final VenueDNA scores per player and tournament
- `active_field_projections` — current field projection ingestion target where implemented
- `course_profiles` — seeded course-profile structure where implemented

DataGolf player IDs are the canonical external player key. Internal player IDs map through the `players` table.

Do not use display name as the sole join key when a DataGolf ID exists.

Normalize player identity before joins:

- Preserve DataGolf ID.
- Normalize known name variants.
- Apply diacritic folding where required.
- Support documented encoding fallback for known source artifacts.
- Log unresolved identity matches rather than silently dropping or duplicating a player.

## Database Architecture

Two SQLite databases have distinct roles. Do not conflate them.

### `data/venuedna_master.db`

Tracked in Git. Production master database.

Contains processed canonical tables including `players`, `tournaments`, `strokes_gained`, `venue_profiles`, and `venue_scores`.

Known scripts using this path:

- `engine/datagolf_client.py` — manages schema; `DB_PATH` is hardcoded
- `engine/ingest_manual_exports.py` — upserts `active_field_projections`
- `engine/initialize_venues.py` — seeds `course_profiles`
- `engine/build_round_analysis.py` — reads for scoring
- `engine/traits_calculator.py` — queries trait rows

### `data/venue_dna.db`

Untracked and gitignored. Local raw API cache and harvester working store.

- Created and populated by `engine/dg_api_harvester.py`.
- May be absent from a clean clone.
- `config/db_config.json` declares this path.
- Do not treat it as the production master.

### Database Rules

- Never add a global `*.db` gitignore rule.
- `venuedna_master.db` is intentionally tracked.
- `venue_dna.db` must retain its explicit gitignore treatment.
- Before changing schema, identify the target database.
- Database migrations must be idempotent.
- Database schema changes require validation against existing tables and affected scripts.
- Do not change `db_config.json` to redirect production scripts without verifying each script’s actual database behavior.

## Scoring Discipline

All scores remain normalized 0-100 unless the canonical scoring spec explicitly authorizes an exception. Higher scores mean stronger venue fit or stronger score component as defined by the relevant artifact.

Keep these layers separate:

1. NeutralSkill
2. VenueFitDelta
3. VenueHistoryDelta
4. Penalties and gates
5. Uncertainty and confidence
6. Derivative outputs such as DFS, betting, ownership, and market comparison

Do not collapse the model into a single unexplained score.

Do not:

- Use world rank as a direct scoring input.
- Substitute generic recent form for venue-specific fit.
- Transfer putting performance across surfaces without an explicit rule or discount.
- Let salary, betting market, DFS ownership, or popularity alter the core projection layer.
- Skip penalties or gates because a player is famous.
- Modify scoring weights outside the engine configuration section.
- Make an engine-rule change from one event anecdote.
- Treat a DataGolf decomposition file as the core projection engine.

Weather adjustments are applied post-score as a multiplicative modifier unless the canonical scoring spec explicitly changes that rule.

## Confidence Discipline

Venue-history sample size below eight relevant starts requires a venue-history confidence flag. It does not invalidate NeutralSkill or VenueFitDelta.

Preserve confidence by source:

- NeutralSkill confidence
- VenueFitDelta confidence
- VenueHistoryDelta confidence
- Data completeness confidence
- Weather and conditions confidence
- Debut-framework confidence where relevant

Do not collapse uncertainty into one generic low-confidence label.

Do not run the scoring engine on fewer than three years of venue history without an explicit confidence flag and a documented reason the build remains valid.

If data is incomplete:

1. Identify the missing source.
2. Preserve available model layers.
3. Widen only the affected confidence components.
4. Do not hallucinate SG splits, venue history, surface performance, or weather evidence.
5. Do not replace missing data with player reputation.

## Active Event Protocol

Read `config/active_event.json` before work.

Allowed statuses:

- `NO_ACTIVE_EVENT`
- `PRE_EVENT`
- `ROUND_1`
- `ROUND_2`
- `ROUND_3`
- `ROUND_4`
- `FINAL_AUDIT`
- `ARCHIVED`

When status is `NO_ACTIVE_EVENT`:

- Do not create an event-bound projection or live artifact without an explicit task authorizing event initialization.
- Do not infer a new active event from the most recently archived event.
- Limit work to reusable engine, standards, tests, tooling, library, planning, or approved event-initialization tasks.

When status is `PRE_EVENT`:

- Build only pre-event artifacts.
- Do not generate live artifacts.
- Lock the canonical pre-event output before live work begins.

When status is `ROUND_1` through `ROUND_4`:

- Treat pre-event artifacts as immutable.
- Write only round-specific live outputs.
- Preserve prior-round artifacts.
- Separate structural confirmation or structural miss from variance.
- Do not change global scoring weights based on live event results.

When status is `FINAL_AUDIT`:

- Produce audit artifacts.
- Classify misses at the correct layer.
- Generate proposed write-backs only.
- Do not apply venue or engine-rule changes automatically.

When status is `ARCHIVED`:

- Do not write new production artifacts into the archived event without explicit authorization.
- Maintain internal path integrity after archival moves.

## Execution Protocol

Before changing code:

1. Read `config/active_event.json`.
2. Identify the event slug, venue slug, task type, authorized paths, and protected paths.
3. Read the relevant engine code, deploy files, tests, data contracts, and standards.
4. For any task touching more than one file, state an implementation plan in five bullets or fewer.
5. Make the smallest coherent change that satisfies the task.
6. Run the narrowest relevant validation before declaring completion.

After changing code, report:

- Files changed
- Behavior changed
- Files intentionally not changed
- Validation run and result
- Data-contract impact
- Database migration impact
- Required manual copy, deploy, or artifact step
- Open risk or unresolved dependency

Do not refactor unrelated files, reformat large unrelated files, rename deploy assets, alter scoring weights, change database behavior, or modify venue doctrine outside explicit task scope.

## Deploy Contract

Deploy files are protected:

- `events/{event_slug}/deploy/index.html`
- `events/{event_slug}/deploy/app.js`
- `events/{event_slug}/deploy/styles.css`
- `events/{event_slug}/deploy/data/*`

Before changing deploy behavior:

1. Inspect `index.html`, `app.js`, `styles.css`, and every payload the board consumes.
2. Preserve current payload compatibility unless the task explicitly changes the data contract.
3. Before renaming any payload, identify every fetch call and downstream reference.
4. Update all references in the same change.
5. Validate the board through the fixture harness, browser workflow, or the narrowest available deploy validation.
6. Do not place temporary notes, planning files, raw data, or unvalidated artifacts in `deploy/data/`.

The static deploy board uses no server and no localStorage. Build scripts are Python. Round-analysis files may auto-deploy where configured. Pre-tournament artifacts may require an explicit copy from `output/` to `deploy/data/`; report that required manual step rather than assuming it occurred.

## Live Event Safety

During active tournament rounds:

- Preserve the pre-event model as read-only.
- Build live outputs from the pre-event projection spine plus approved current-round evidence.
- Do not overwrite `round2` data with `round3` data or any later-round output.
- Preserve the player identity pipeline, including diacritic folding and known encoding fallback.
- Preserve the approved two-tier weather parser where it exists.
- Do not invent live data fields not present in the source artifacts.
- Do not elevate a player solely because of current position without assessing underlying SG, hole-level classification, remaining conditions, and structural fit.
- Do not downgrade a player solely because of one-round variance without documenting the mechanism.
- Preserve scenario fencing between the pre-event thesis and live inference.

## Audit and Write-Back Discipline

Post-event work must:

1. Compare Tier 1 and Tier 2 projections with actual outcomes.
2. Review anti-pattern calls.
3. Classify significant misses at NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalty, gate, debut, data, or Council layer.
4. Separate venue-specific write-backs from global engine-rule flags.
5. State evidence basis and evidence threshold.
6. Produce a write-back artifact before modifying canonical venue profiles or engine rules.

Do not revise venue or engine rules from one anecdote. Do not perform an audit without structured miss classification. Do not apply write-backs automatically.

## Model Council Discipline

Model Council is a challenge layer, not a ranking replacement.

Run full Council review for:

- Full tournament projections
- Tier 1 decisions
- Strong fades
- Major disagreement versus market, consensus, or ownership
- Material live promotions or downgrades
- Post-event audits

Run light Council review for:

- Single-player structural cases
- One-condition updates without full reranking
- Narrow venue-specific questions requiring challenge logic

Skip Council for:

- File checks
- Schema checks
- Simple factual retrieval
- Non-interpretive artifact tasks

Council rules:

- Canonical engine produces the first-pass projection.
- Council pressure-tests blind spots, weak conviction, duplicate logic, and audit risk.
- Council does not average opinions into soft consensus.
- Market Contrarian reasoning never alters core rankings through pricing logic.
- Collapse duplicate objections into the sharpest distinct objection.
- Every objection must produce a downgrade, hold, promotion, confirmation, or logged no-change ruling.

## Tests and Validation

Use the narrowest relevant validation first.

Examples:

- Engine logic change: targeted unit test plus representative event regression comparison
- SQLite schema change: migration test plus existing-table verification
- Player identity change: identity-resolution tests and join count validation
- JSON/CSV payload change: payload contract test and deploy fetch validation
- Static board change: fixture harness or browser validation
- Artifact naming change: artifact naming validation
- Live pipeline change: round-specific build validation without mutating prior-round artifacts

When no relevant automated test exists:

1. State that no test exists.
2. Run the narrowest available script or deterministic inspection.
3. Describe the gap.
4. Propose a focused test only if it prevents a recurring failure.

## Known State

Session stamp: 2026-08-03

- Branch: `main`
- Active-event authority: `config/active_event.json`
- Current default state: no active event until `config/active_event.json` is updated
- Most recently active events:
  - 2026 Rocket Classic, Detroit Golf Club, archived at `events/2026_Finished_Events/2026_rocket_classic/`
  - 2026 3M Open, TPC Twin Cities, archived at `events/2026_Finished_Events/2026_3m_open/`

Do not assume a completed event remains active because files or hardcoded paths still exist.

## Known Debt

- `events/2026_Finished_Events/2026_USOPEN/output/derivatives/draftkings/` is a non-canonical legacy DraftKings output folder.
- Open Championship event engine uses canonical v3 scripts: `score_open_2026_v3.py` and `build_board_v3.py`.
- Legacy Open v1/v2 scripts and `build_dry_run_pack.py` were deleted during July 2026 cleanup.
- Finished-event folder names under `events/2026_Finished_Events/` have mixed casing in some legacy directories.
- Renaming legacy archived folders requires a full audit of downstream path references before execution.

Do not normalize legacy archive paths opportunistically. Treat legacy path cleanup as its own scoped task.

## Hard Prohibitions

Do not:

- Hardcode scoring weights outside the approved engine configuration section.
- Modify raw data files. Write transformed data to `data/processed/` or the designated event output path.
- Rename deploy data files without updating `app.js` and validating the board.
- Store temporary notes or planning files in `deploy/data/`.
- Allow duplicate venue files to accumulate in event inputs and `library/venues/`; the venue library is canonical.
- Treat `data/venue_dna.db` as the production master.
- Add a global `*.db` gitignore rule.
- Replace missing data with reputation, consensus, or generic recent form.
- Let derivative outputs rewrite core model logic.
- Overwrite immutable pre-event artifacts with live data.
- Apply audit write-backs without evidence thresholds and operator approval.
- Create a duplicate copy of a canonical standard or contract file.