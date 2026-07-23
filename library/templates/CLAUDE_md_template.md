# CLAUDE.md

## Project
PGA VenueDNA Tier Engine

Root path: `C:\PGA_VenueDNA`
GitHub repo: [PGA-VenueDNA-Tier-Engine](https://github.com/devintyler83/PGA-VenueDNA-Tier-Engine)

This repository exists to produce venue-specific PGA Tour projections that are traceable, auditable, and deployable. Core outputs must preserve separation between NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties/gates, and derivative layers.[file:23][file:22]

## Active event
- Event: **2026 3M Open**
- Event slug: `3mopen`
- Event folder: `C:\PGA_VenueDNA\events\2026_3m_open`
- Venue: **TPC Twin Cities**
- Required active venue file target: `library\venues\TPC_TWIN_CITIES_INTELLIGENCE_2026_v1.md`

If the active venue intelligence file is missing, stop projection work and resolve that gap before running modeling or event-output generation.[file:23]

## Canonical folder structure

```text
C:\PGA_VenueDNA\
├── standards\
│   ├── 00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md
│   ├── 01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md
│   ├── 02_PGA_VENUEDNA_SCORING_SPEC.md
│   ├── 03_PGA_VENUEDNA_LEARNING_LOOP.md
│   ├── 04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
│   ├── 05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md
│   ├── 06_PGA_VENUEDNA_EVENT_WORKFLOW.md
│   └── 07_PGA_VENUEDNA_AUDIT_STANDARD.md
├── library\
│   ├── engine\
│   └── venues\
├── events\
│   └── YYYY_event_slug\
│       ├── input\
│       ├── output\
│       │   ├── round1\
│       │   ├── round2\
│       │   ├── round3\
│       │   └── round4\
│       ├── engine\
│       ├── deploy\
│       │   ├── data\
│       │   ├── index.html
│       │   ├── app.js
│       │   └── styles.css
│       └── audit\
├── data\
├── config\
├── tools\
├── tests\
├── docs\
├── public\
├── CLAUDE.md
└── README.md
```

This structure keeps persistent standards separate from reusable engine files, venue intelligence, weekly event packs, deploy assets, and post-event audit artifacts.[cite:21][file:22][file:25]

## Naming rules

### Standards files
Use these exact names:
- `00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md`
- `02_PGA_VENUEDNA_SCORING_SPEC.md`
- `03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md`
- `06_PGA_VENUEDNA_EVENT_WORKFLOW.md`
- `07_PGA_VENUEDNA_AUDIT_STANDARD.md`

### Venue intelligence files
Pattern:
- `{VENUECODE}_INTELLIGENCE_{YEAR}_v{N}.md`

Example:
- `TPC_TWIN_CITIES_INTELLIGENCE_2026_v1.md`

One venue intelligence file should exist per locked course in `library\venues\`.[file:22]

### Event input files
Place in `events\YYYY_event_slug\input\`.

Canonical names:
- `{year}{eventslug}_field_input.csv`
- `{year}{eventslug}_event_context.json`
- `{year}{eventslug}_venue_profile.md`
- `{year}{eventslug}_weather.md`

Raw source files may retain source cues, but should be prefixed cleanly, for example:
- `dg_performance_2026.csv`
- `sg_query_allcourses_l12.csv`
- `pga_field.csv`

### Event output files
Place in `events\YYYY_event_slug\output\`.

Canonical names:
- `{year}{eventslug}_traitform_matrix.csv`
- `{year}{eventslug}_vts_full.csv`
- `{year}{eventslug}_player_briefs.json`
- `{year}{eventslug}_event_payload.json`
- `{year}{eventslug}_links.json`

These are mandatory source-of-truth artifacts for the event pack and deploy chain.[file:22]

### Round files
Place in `events\YYYY_event_slug\output\roundN\`.

Canonical names:
- `round{N}_leaderboard.csv`
- `round{N}_player_strokes_gained.csv`
- `round{N}_course_stats.csv`
- `round{N}_course_insights.csv`

### Audit files
Place in `events\YYYY_event_slug\audit\`.

Canonical names:
- `{year}{eventslug}_audit_log.md`
- `{year}{eventslug}_audit_writeback.json`
- `{year}{eventslug}_miss_ledger_rows.csv`

### Deploy data files
Place in `events\YYYY_event_slug\deploy\data\`.

Canonical names:
- `event_payload.json`
- `player_briefs.json`
- `vts_full.csv`
- `links.json`
- `qa_report.json`

The deploy package should remain a static-site-friendly shell with source data files separated from browser presentation files.[file:22][file:18]

## Operating rules for Claude Code
- Work from the repository root unless an event-specific task explicitly requires the event folder.
- Do not delete files unless they are confirmed duplicates or zero-byte placeholders.
- Prefer move/rename over recreate.
- Log every rename, move, and folder creation.
- Do not alter ranking logic or scoring formulas during a file cleanup task.
- Do not change CSV or JSON content during organizational cleanup unless explicitly asked.
- Keep prior events in their own event folders; do not let historical event files live in root or current-event paths.
- Treat venue profile and weather as required event inputs, not optional notes.
- Before a full projection build, confirm active event files, active venue file, and event context are present.[file:23][file:22]

## 3M Open required file check
The active 3M Open folder should contain or resolve to these files:

### Input
- `20263mopen_field_input.csv`
- `20263mopen_event_context.json`
- `20263mopen_venue_profile.md`
- `20263mopen_weather.md`

### Output
- `20263mopen_traitform_matrix.csv`
- `20263mopen_vts_full.csv`
- `20263mopen_player_briefs.json`
- `20263mopen_event_payload.json`
- `20263mopen_links.json`

### Engine
- `venuedna_pipeline_3mopen_2026.py` or equivalent cleanly named event pipeline
- `build_round_analysis.py`
- `round_helpers.py`
- `qa_trait_validation.py`

### Deploy
- `deploy\index.html`
- `deploy\app.js`
- `deploy\styles.css`
- `deploy\data\event_payload.json`

If any required input is missing or misplaced, stop and report the gap before calling the build complete.

## New event week setup checklist

When starting a new event week, do this in order:

1. Create `events\YYYY_event_slug\` with subfolders: `input`, `output`, `output\round1`, `output\round2`, `output\round3`, `output\round4`, `engine`, `deploy`, `deploy\data`, `audit`.
2. Copy or link the current deploy shell into the new event's `deploy\` folder.
3. Create or place the active venue intelligence file in `library\venues\` using the canonical venue naming pattern.[file:22]
4. Place required event inputs into `input\`:
   - `{year}{eventslug}_field_input.csv`
   - `{year}{eventslug}_event_context.json`
   - `{year}{eventslug}_venue_profile.md`
   - `{year}{eventslug}_weather.md`
5. Copy the reusable engine helpers needed for the event into `events\YYYY_event_slug\engine\` only if the workflow still uses event-local scripts; otherwise point to `library\engine\` as the single source of truth.
6. Verify all output target filenames before running any build so generated artifacts match the schema on first write.[file:22]
7. Confirm `CLAUDE.md` active-event section is updated to the new week.
8. Run a preflight file audit: required present, missing, misplaced, duplicate, stale prior-event contamination.
9. Only after the file audit passes, run the pre-tournament pipeline.
10. Copy canonical outputs into `deploy\data\` using deploy names, not event-prefixed names.
11. After Round 1 or later, place round files into the correct `output\roundN\` folder and keep names exact.
12. After event completion, write audit artifacts into `audit\` and do not overwrite pre-event outputs.[file:22][file:25]

## Cleanup task template for Claude Code
When asked to clean the repo, follow this sequence:
1. Inventory all files.
2. Flag non-canonical names and misplaced files.
3. Create missing folders.
4. Rename and move files with a logged before/after path.
5. Check active event completeness.
6. Update `CLAUDE.md` if structure or active event changed.
7. Produce a final report with unresolved decisions clearly separated.

## Master cleanup prompt for Claude Code

```text
You are operating inside the PGA VenueDNA Tier Engine project.

Root path: C:\PGA_VenueDNA
GitHub: https://github.com/devintyler83/PGA-VenueDNA-Tier-Engine
Active event: 2026 3M Open
Active event folder: C:\PGA_VenueDNA\events\2026_3m_open

TASK: Full project cleanup, canonical reorganization, naming normalization, and active-event completeness audit.

PHASE 1 — Inventory
- Walk the full directory tree.
- Output every file and folder path.
- Flag duplicates, misplaced files, stale prior-event files in the wrong path, and ambiguous names.

PHASE 2 — Enforce folder structure
- Ensure the canonical repo structure in this CLAUDE.md exists.
- Create missing folders.
- Do not delete folders with unresolved files.

PHASE 3 — Enforce naming
- Rename standards, venue, event input, output, round, audit, and deploy files to match the naming rules in this CLAUDE.md.
- Log every rename.

PHASE 4 — Active-event audit
- Audit C:\PGA_VenueDNA\events\2026_3m_open for required inputs, outputs, engine files, deploy files, venue profile, and weather.
- Mark each required file PRESENT, MISSING, or MISPLACED.
- State what each missing file is supposed to contain and whether it blocks a clean pre-tournament build.

PHASE 5 — Resolve misplaced files
- Move files to their canonical folders.
- Show before/after path for each move.
- Do not delete suspected duplicates without confirmation.

PHASE 6 — Update CLAUDE.md
- Verify active event, active venue file, folder structure, naming rules, and event-week checklist are accurate.
- Update if needed and show the diff.

PHASE 7 — Final report
Return a structured report with:
1. Files renamed
2. Files moved
3. Folders created
4. 3M Open completeness table
5. Unresolved items needing human decision
6. Immediate next action

Constraints:
- Do not change model logic.
- Do not rewrite CSV or JSON contents during cleanup.
- Do not delete files unless zero-byte or confirmed duplicate.
- Treat venue profile and weather as required active-event inputs.
- If ambiguity exists, stop and ask before acting.
```

## Notes
The repo currently contains top-level directories including `config`, `data`, `docs`, `engine`, `events`, `library`, `public`, `standards`, `tests`, and `tools`, which should remain the backbone of the project organization unless intentionally superseded by a newer canonical structure.[cite:21]
