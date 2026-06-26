# PGA VenueDNA Tier Engine — Space Setup Guide
Version 1 — June 2026
Purpose: Exact setup instructions for configuring the Perplexity Space so the unified PGA VenueDNA system runs with the correct files, authority order, and weekly update pattern.

## 1. Setup objective
This Space should function as the permanent operating home for the PGA VenueDNA Tier Engine.

Perplexity Spaces allow you to add custom instructions, upload local files, connect cloud-file repositories, and add links as sources, so the Space should be configured as a persistent knowledge hub rather than a one-off chat thread. [web:22][web:23][web:56]

The goal is to make the Space behave like a disciplined venue-intelligence engine with a stable memory layer made of canonical files and venue files, while weekly event files are refreshed as tournament context changes. [web:22][web:23]

## 2. Recommended setup pattern
Use this exact operating pattern:
- one Space
- one master instruction block
- a small permanent file library
- one venue file per locked course
- weekly event uploads for active tournaments only
- links added only for sources you expect to revisit repeatedly

This pattern aligns with how Spaces combine instructions, file context, and link sources in one project workspace. [web:22][web:23][web:25]

## 3. Space creation
When creating the Space:
- set the name to the final system name you want to keep
- use the description as an operator-facing label, not as behavior logic
- place all real system behavior inside the custom instructions field

Spaces apply custom instructions to threads started inside the Space, so the core operating logic must live in the Space instructions rather than in random first-thread setup text. [web:29][web:55][web:56]

## 4. What goes in custom instructions
Paste the contents of:
- `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md`

This should be the only full master instruction block in the Space. Do not duplicate the scoring spec, learning loop, or artifact schema inside the custom instructions field. Keep those as uploaded files so they remain separately maintainable. [web:22][web:23]

## 5. Permanent file library
Upload these files as the permanent backbone of the Space.

### 5.1 Required permanent engine files
Upload first, in this order:
1. `00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
2. `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md`
3. `02_PGA_VENUEDNA_SCORING_SPEC.md`
4. `03_PGA_VENUEDNA_LEARNING_LOOP.md`
5. `04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`

Reason: this creates a stable authority chain before you add venue files or weekly event data. [web:22][web:23]

### 5.2 Recommended permanent standards files
Add next as they are created:
- `05_PGA_VENUEDNA_SPACE_SETUP_GUIDE.md`
- `06_PGA_VENUEDNA_EVENT_WORKFLOW.md`
- `07_PGA_VENUEDNA_AUDIT_STANDARD.md`
- `08_PGA_VENUEDNA_SOURCE_HIERARCHY.md` if created
- `09_PGA_VENUEDNA_GLOSSARY.md` if created

### 5.3 Venue intelligence files
Add one locked file per venue, using a consistent naming convention such as:
- `COLONIAL_INTELLIGENCE_2026_v2.md`
- `ARONIMINK_INTELLIGENCE_2026_v1.md`
- `CRAIGRANCH_INTELLIGENCE_2026_v1.md`
- `HARBOURTOWN_INTELLIGENCE_2025_v1.md`
- `MUIRFIELD_INTELLIGENCE_2026_v1.md`

Only upload venue files that are either locked or clearly labeled provisional. Never keep multiple unlabeled competing venue versions in the Space at the same time.

## 6. Weekly event files
Each tournament week should have its own refreshed event file set.

### 6.1 Minimum weekly event uploads
Upload or refresh these files for the active event:
- `[year]_[event_slug]_field_input.csv`
- `[year]_[event_slug]_event_context.json`
- `[year]_[event_slug]_trait_form_matrix.csv` when available
- `[year]_[event_slug]_vts_full.csv` when scored output exists
- `[year]_[event_slug]_player_briefs.json` when briefs exist
- `[year]_[event_slug]_event_payload.json` when app payload exists

### 6.2 Optional weekly event files
Add when relevant:
- `[year]_[event_slug]_links.json`
- `[year]_[event_slug]_r1_diagnostic.json`
- `[year]_[event_slug]_live_snapshot_r1.csv`
- `[year]_[event_slug]_audit_log.md`
- `[year]_[event_slug]_audit_writeback.json`
- `[year]_[event_slug]_miss_ledger_rows.csv`

## 7. Upload order each week
For best reliability, load files in this order:
1. permanent engine files already in Space
2. active venue file
3. field input and event context files
4. scored output files
5. live update files
6. post-event audit files

This makes the active tournament context sit on top of a stable rules base instead of colliding with it. [web:22][web:23]

## 8. File hygiene rules
Use these rules strictly.

### 8.1 One source of truth per file type
- one master prompt file
- one scoring spec file
- one learning-loop file
- one artifact schema file
- one current venue file per active course
- one latest weekly file per event artifact type

### 8.2 Archive old versions outside the Space when possible
If older versions are useful for recordkeeping, store them externally rather than leaving too many superseded versions inside the Space. Too many overlapping versions increase context drift and retrieval ambiguity.

### 8.3 Replace, do not pile up
When you update the active week’s field input or scored output, replace the prior version or rename clearly with iteration labels such as:
- `initial`
- `weather_update`
- `r1_update`
- `final`
- `audit`

## 9. Naming rules
Use exact names that match the artifact schema.

Why this matters:
- the master prompt references canonical file names
- weekly workflows become much easier to repeat
- future event app builds can read standardized files directly

If a file needs a variant, add the iteration label before the extension.
Example:
- `2026_us_open_vts_full_initial.csv`
- `2026_us_open_vts_full_r1_update.csv`

## 10. Links to add to the Space
Use links only for recurring high-value sources, not every temporary article.

Recommended recurring links:
- official PGA Tour leaderboard or tournament page
- recurring weather source
- DataGolf event or main tools pages if useful in workflow
- DraftKings salary or contest source if used repeatedly
- any stable documentation source tied to your event app or deployment workflow

Spaces allow adding links alongside files, making them useful as persistent reference sources when they are stable and frequently reused. [web:22][web:55][web:56]

Do not clutter the Space with one-off news links that will be irrelevant next week.

## 11. Cloud connectors and repositories
Perplexity supports connected repositories such as Google Drive, OneDrive, SharePoint, Dropbox, Box, and local uploads within Spaces, so you can store archives externally while pulling current files into the Space as needed. [web:22]

Recommended use:
- keep long-term archives in your cloud folder structure
- keep only current canonical files and active event files inside the Space
- use connectors for retrieval, not as an excuse for sloppy naming

## 12. Thread discipline
Always start tournament work inside this Space, not in a general chat.

Spaces apply the custom instructions and attached file context only when the thread is created and run inside the Space environment. [web:55][web:56]

If a thread starts outside the Space, the engine behavior and file-awareness may not carry over reliably. [web:55]

## 13. Practical reliability rule
Because some users report that Spaces can inconsistently prioritize attached files in certain situations, begin major tournament threads with a short context-lock message naming the active event, venue, and active venue file. [web:53][web:58]

Use a starter line like:
- `Active event: 2026 U.S. Open`
- `Active venue file: OAKMONT_INTELLIGENCE_2026_v1.md`
- `Task: pre-tournament projection build`

This is not a replacement for the master prompt. It is a practical thread-level reinforcement step when stakes are high. [web:53][web:58]

## 14. Recommended Space description
The Space description is mainly for organization, not system behavior. One good format is:

`Permanent operating home for the PGA VenueDNA Tier Engine. Venue-specific PGA Tour scoring, event-week projections, live diagnostics, audit write-backs, and deployable event artifacts.`

The actual system logic should remain in the custom instructions and uploaded files, not the description field. [web:55][web:56]

## 15. Recommended external folder structure
Mirror the Space externally so archive management stays clean.

```text
PGA_VenueDNA/
  library/
    engine/
    venues/
    standards/
  events/
    2026_us_open/
      input/
      output/
      deploy/
      audit/
```

This makes it easy to upload current files into the Space and archive the rest outside it.

## 16. Setup checklist
Use this exact checklist.

### Initial Space setup
- Create the Space
- Add final Space name
- Add operator-facing description
- Paste `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md` into custom instructions
- Upload required permanent engine files
- Upload current locked venue intelligence files
- Add only recurring high-value links

### Tournament-week setup
- Confirm active event slug and file names
- Upload active event context and field input files
- Confirm active venue file exists and is clearly named
- Upload scored outputs as they are generated
- Upload live diagnostic files if running in-event analysis
- Upload audit outputs after completion

### Maintenance setup
- Remove or archive superseded event files
- Replace outdated venue files only when a new locked version exists
- Keep naming conventions consistent
- Keep one active truth source per artifact type

## 17. Best-practice operating rule
Treat the Space as the live command center, not as the long-term archive for every historical file ever created.

The Space should hold:
- the current engine brain
- the current venue library
- the current event context
- the current audit-ready outputs

The deeper archive should live in your connected storage or external folders. [web:22]

## 18. Deploy note
When event app files are generated, package them into a clean static folder. Netlify can deploy a static site either by connecting a repository or by manually drag-and-dropping the containing static folder, and static no-build deployments should leave build command blank when no build step exists. [web:31][web:39][web:41][web:34]

That makes the Space a strong control plane for generating the app files, while Netlify becomes the delivery layer for the event dashboard. [web:31][web:39]

## 19. Operating standard
For this Space, always prefer:
- one clear master prompt over multiple competing instruction blocks
- one source of truth per file type
- current event files over stale clutter
- stable recurring links over random article collections
- external archives over in-Space sprawl
- explicit active-event context at thread start when the work matters most

This file defines how to configure and maintain the Perplexity Space so the PGA VenueDNA Tier Engine operates cleanly and reliably.
