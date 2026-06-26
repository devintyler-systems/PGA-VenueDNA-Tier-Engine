# Perplexity Multi-Model Rebuild Guide
## PGA Tour Intelligence System — Platform Migration Notes
### June 2026

---

## THE CORE CHALLENGE ON PERPLEXITY

Perplexity does not have persistent memory or file storage between sessions the way this system relies on in Claude Projects. You need to build around three constraints:

1. **No native file persistence** — venue library files must be attached or pasted at session start
2. **Multi-model environment** — different models have different strengths; route tasks accordingly
3. **No project-level system prompt** — the system prompt must be injected into every new conversation

---

## SOLUTION: SESSION INITIALIZATION PROTOCOL

### Start Every VTS Session With This Sequence:

**Step 1 — Paste or attach the system prompt** (`01_SYSTEM_PROMPT_FULL.md`)
Set this as the system prompt or paste as first user message if system prompt isn't accessible.

**Step 2 — Load active venue file(s)**
Attach the relevant venue Intelligence Update file:
- Colonial: `Colonial_2026_Intelligence_Update.md`
- Aronimink: `Aronimink_Intelligence_System_Update.md`
- Craig Ranch: paste TPC Craig Ranch parameters from master doc
- Harbour Town / Muirfield: attach from session archive

**Step 3 — State the tournament context**
> "We are projecting [EVENT NAME] at [VENUE]. Confirm the venue DNA profile is loaded and provide the weight matrix you'll apply."

This forces the model to echo back the venue DNA before scoring begins — catches any context gaps immediately.

---

## MODEL ROUTING FOR PERPLEXITY

### Claude (Anthropic) — Primary for:
- Venue DNA profile extraction and write-back
- Player brief generation (T1/T2 full briefs)
- Post-tournament audit synthesis and calibration write-back
- Cross-venue rule application and edge cases
- Session handoff document generation
- Anti-pattern analysis with historical evidence chains

**Why:** Best at sustained reasoning across long structured documents, calibrated self-correction, and maintaining complex rule hierarchies without drift.

### GPT-4o — Primary for:
- DataGolf CSV parsing and structured data ingestion
- VTS math scoring (arithmetic verification)
- DK lineup combinatorial optimization (use code interpreter)
- Odds-to-implied-probability conversion tables
- Tier ranking output when speed matters

**Why:** Strongest at code execution and structured data operations. Code interpreter handles brute-force lineup math cleanly.

### Gemini Pro — Primary for:
- Large field batch scoring (long context, can hold 156-player field in one pass)
- Multi-document synthesis (load 3+ venue files simultaneously)
- Weather data + course condition context (strong at real-time synthesis)

**Why:** Largest effective context window; useful when you need full field + full venue profile + odds data simultaneously.

### Sonar (Perplexity native) — Primary for:
- Live R1 leaderboard pulls during tournaments
- Real-time weather updates
- Injury news verification
- DK salary file updates mid-week
- Odds line movement tracking

**Why:** Real-time web access is the core use case. Don't use for projection logic — use for live data only.

### Kimi — Secondary for:
- Long document processing when Gemini context is exceeded
- Parallel player batch scoring

### Nemotron — Reserve for:
- Speed tasks where quality doesn't need to be primary
- Quick odds conversion tables
- Simple data formatting

---

## WORKFLOW SPLIT BY TASK

```
TOURNAMENT WEEK WORKFLOW WITH MODEL ROUTING:

Monday–Tuesday (Build):
  ├── Gemini: Load venue DNA + full field → initial VTS scoring batch
  ├── GPT-4o: Validate math, run DK optimizer with code interpreter
  └── Claude: Generate T1/T2 player briefs, anti-pattern analysis, edge table

Wednesday (Finalize):
  ├── Sonar: Pull latest odds, injury news, weather
  ├── GPT-4o: Update DK salaries, rerun optimizer
  └── Claude: Final tier rankings, locked lineups, session handoff doc

Thursday R1 (Live):
  ├── Sonar: Real-time leaderboard after all groups complete
  └── Claude: R1 diagnostic — tier updates, downgrades, holds

Weekend:
  ├── Sonar: Live scores, position updates
  └── Claude: R2/R3/R4 position tracking vs. projections

Monday Post (Audit):
  └── Claude: Full post-tournament audit → venue library write-back
```

---

## VENUE LIBRARY FILE MANAGEMENT

### Where to Store Venue Files
Since Perplexity lacks project-level file storage, maintain the venue library in:

**Option A — Google Drive folder** (recommended)
- Create folder: `VTS_Venue_Library/`
- One .md file per venue
- Attach relevant file(s) at session start

**Option B — Local folder + paste**
- Keep venue files on desktop
- Copy-paste into session as system context

**Option C — NotionAI / Obsidian**
- If you use either, the venue library integrates cleanly as a knowledge base
- Reference directly from Perplexity if integration exists

### Naming Convention
```
[VENUE_CODE]_Intelligence_[YEAR]_v[N].md

Examples:
  COLONIAL_Intelligence_2026_v1.md
  ARONIMINK_Intelligence_2026_v1.md
  CRAIG_RANCH_Intelligence_2026_v1.md
  HARBOUR_TOWN_Intelligence_2025_v1.md
  MUIRFIELD_Intelligence_2026_v1.md
```

After each post-tournament audit, update the version number.

---

## CONTEXT INJECTION TEMPLATE

Paste this at the start of every new Perplexity session before any work begins:

```
SYSTEM: You are the PGA Tour Intelligence System (VTS Engine).

[PASTE FULL SYSTEM PROMPT FROM 01_SYSTEM_PROMPT_FULL.md]

ACTIVE VENUE LIBRARY LOADED:
[PASTE RELEVANT VENUE INTELLIGENCE FILE(S)]

CROSS-VENUE ENGINE RULES: [confirm loaded from system prompt above]

SESSION CONTEXT:
Tournament: [EVENT NAME]
Venue: [VENUE]
Week of: [DATE]
Field size: [N players]
Conditions forecast: [firm/soft/mixed]
Data files available: [list what DataGolf CSVs you have]

Confirm venue DNA profile is loaded. Echo back the trait weight matrix 
and anti-pattern list for [VENUE] before we begin scoring.
```

---

## WHAT TO DO ABOUT THE PYTHON SCORING ENGINE

The Python engine (`02_VTS_SCORING_ENGINE.py`) runs in two places:

**Option A — GPT-4o Code Interpreter (easiest)**
- Upload the .py file + your DataGolf CSVs to GPT-4o
- Prompt: "Run the score_field() function with these CSVs against this venue DNA profile. Return the sorted tier rankings."
- GPT-4o executes, returns results, you paste rankings back into Claude for brief generation

**Option B — Local Python environment**
- Run locally with your DataGolf CSVs
- Output the ranked CSV, paste into Claude for brief generation and analysis

**Option C — Replit / Google Colab**
- Upload the .py file to Replit or Colab
- Run with DataGolf CSV uploads directly
- Good for mid-week reruns after salary or odds updates

---

## THE AUDIT FORM

The post-tournament audit form (`post_tournament_audit_form.html`) works natively in any browser. After completing it:

1. Fill the form post-tournament
2. Click "Commit audit to venue library"
3. It generates a structured audit text block
4. Paste that block into Claude with the prompt: "Update the venue library profile with all changes below, confirm every weight adjustment applied, and flag any section requiring follow-up."
5. Claude returns an updated venue Intelligence .md file
6. Save it as the new version in your library folder

---

## KNOWN GAPS IN THE MULTI-MODEL REBUILD

These things work natively in Claude Projects that need workarounds on Perplexity:

| Feature | Claude Projects | Perplexity Workaround |
|---------|----------------|----------------------|
| Persistent venue library | Native (project files) | Attach files each session |
| Session memory | Native | Session handoff .md file |
| Audit form → auto write-back | sendPrompt() integration | Manual paste |
| Interactive tier rankings widget | HTML artifact rendered in chat | Build as standalone .html |
| Mid-session calibration writebacks | Auto-persisted | Manual save to library file |

---

## OPEN BUILD ITEMS (carry forward to new platform)

1. **R1 Live Diagnostic Framework for Memorial** — designed but not yet built as a structured protocol
2. **Harbour Town locked DNA file** — profile exists in session history, needs standalone .md write-back
3. **TPC Craig Ranch locked DNA file** — same status
4. **Muirfield Village post-Memorial audit** — complete before next event
5. **DK pts projection model** — currently using VTS × 2.5 as proxy; needs calibrated against historical DK scoring data

---

*Migration guide generated: June 2026*
*Target platform: Perplexity (Claude + Gemini + GPT-4o + Sonar + Kimi + Nemotron)*
