# Claude Code Master Cleanup Prompt

Use this from the root of `C:\PGA_VenueDNA`.

```text
You are operating inside the PGA VenueDNA Tier Engine project.

Root path: C:\PGA_VenueDNA
GitHub: https://github.com/devintyler83/PGA-VenueDNA-Tier-Engine
Active event: 2026 3M Open
Active event folder: C:\PGA_VenueDNA\events\2026_3m_open

TASK: Full project cleanup, reorganization, canonical renaming, and 3M Open build audit.

Complete ALL phases in order. Do not skip phases. Do not move on until each phase is verified.

PHASE 1 — MAP THE FULL PROJECT
Walk the complete directory tree at C:\PGA_VenueDNA. List every file and folder with its current path and file size. Flag any file that:
- Has a non-canonical name
- Is in the wrong folder
- Appears to be a duplicate
- Has no obvious home in the canonical structure

Output a full file inventory table before making any changes.

PHASE 2 — CANONICAL FOLDER STRUCTURE
Enforce this exact structure. Create any missing folders. Do not delete folders that have files until files are relocated.

C:\PGA_VenueDNA\
├── standards\
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

PHASE 3 — CANONICAL FILE NAMING
Apply these naming rules. Rename any file that does not conform. Log every rename.

Engine/standards files:
  00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md
  01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md
  02_PGA_VENUEDNA_SCORING_SPEC.md
  03_PGA_VENUEDNA_LEARNING_LOOP.md
  04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md
  05_PGA_VENUEDNA_MODEL_COUNCIL_GOVERNANCE.md
  06_PGA_VENUEDNA_EVENT_WORKFLOW.md
  07_PGA_VENUEDNA_AUDIT_STANDARD.md

Venue files (library/venues/):
  {VENUECODE}_INTELLIGENCE_{YEAR}_v{N}.md
  Example: TPC_TWIN_CITIES_INTELLIGENCE_2026_v1.md

Event input files (events/YYYY_slug/input/):
  {year}{eventslug}_field_input.csv
  {year}{eventslug}_event_context.json
  {year}{eventslug}_venue_profile.md
  {year}{eventslug}_weather.md
  Raw source files can keep source cues but should be prefixed cleanly, such as dg_, sg_, or pga_.

Event output files (events/YYYY_slug/output/):
  {year}{eventslug}_traitform_matrix.csv
  {year}{eventslug}_vts_full.csv
  {year}{eventslug}_player_briefs.json
  {year}{eventslug}_event_payload.json
  {year}{eventslug}_links.json

Round files (events/YYYY_slug/output/roundN/):
  round{N}_leaderboard.csv
  round{N}_player_strokes_gained.csv
  round{N}_course_stats.csv
  round{N}_course_insights.csv

Audit files (events/YYYY_slug/audit/):
  {year}{eventslug}_audit_log.md
  {year}{eventslug}_audit_writeback.json
  {year}{eventslug}_miss_ledger_rows.csv

Deploy files (events/YYYY_slug/deploy/data/):
  event_payload.json
  player_briefs.json
  vts_full.csv
  links.json
  qa_report.json

PHASE 4 — 3M OPEN BUILD AUDIT
Audit `C:\PGA_VenueDNA\events\2026_3m_open`.

Required input files:
  [ ] 20263mopen_field_input.csv
  [ ] 20263mopen_event_context.json
  [ ] 20263mopen_venue_profile.md
  [ ] 20263mopen_weather.md

Required output files:
  [ ] 20263mopen_vts_full.csv
  [ ] 20263mopen_player_briefs.json
  [ ] 20263mopen_event_payload.json
  [ ] 20263mopen_traitform_matrix.csv
  [ ] 20263mopen_links.json

Pipeline scripts:
  [ ] engine/venuedna_pipeline_3mopen_2026.py or clean equivalent
  [ ] engine/build_round_analysis.py
  [ ] engine/round_helpers.py
  [ ] engine/qa_trait_validation.py

Deploy shell:
  [ ] deploy/index.html
  [ ] deploy/app.js
  [ ] deploy/styles.css
  [ ] deploy/data/event_payload.json

For each required file, mark PRESENT, MISSING, or MISPLACED.
For each missing file, state what it should contain and whether it blocks the build.

PHASE 5 — ORPHAN AND MISPLACED FILE RESOLUTION
For every flagged file:
1. Propose canonical home
2. Propose canonical name
3. Show before/after path
4. Move it after destination exists

Do not delete suspected duplicates without confirmation.

PHASE 6 — CLAUDE.md VERIFICATION AND UPDATE
Verify that CLAUDE.md includes:
- Correct folder structure
- Canonical naming rules
- Active event = 2026 3M Open
- Event folder path
- Active venue file target
- New event week setup checklist

Update if needed and show diff.

PHASE 7 — FINAL VERIFICATION REPORT
Return:
1. Files renamed
2. Files moved
3. Folders created
4. 3M Open completeness table
5. Unresolved human-decision items
6. Immediate next recommended action

CONSTRAINTS:
- Do not modify .json or .csv contents during cleanup.
- Do not change Python logic during cleanup.
- Do not delete files unless zero-byte or confirmed duplicate.
- Prior-event files must live in their own event folder, not root or 3M Open.
- Treat venue profile and weather as required inputs.
- If ambiguity exists, stop and ask.
```
