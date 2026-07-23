> **AUTHORITY: Reference only**
> **Canonical counterpart:** `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
> **Keep reason:** Contains the three-artifact-class architecture, deploy package layout rules, and Space-era versioning metadata not covered by the standards CSV column contracts.
---

# PGA VenueDNA Tier Engine — Artifact Schema
Version 1.1 — June 2026
Purpose: Canonical output, file, and deploy contract for the single Perplexity-native PGA VenueDNA system.

## 1. System role
The artifact layer converts model logic into usable operating outputs.

This layer exists so the engine can do four things reliably:
1. produce weekly event packs
2. populate Space files with stable knowledge assets
3. generate structured outputs for in-chat analysis and audit
4. feed a deployable static event app or dashboard

The artifact contract is part of the engine design. If outputs are inconsistent, the system is not operational.

## 2. Artifact classes
The system uses three artifact classes:
- persistent library artifacts
- weekly event artifacts
- deploy artifacts

### 2.1 Persistent library artifacts
These live in Space files and change only when venue knowledge or engine rules change.

Examples:
- master architecture
- master Space prompt
- scoring specification
- learning-loop specification
- venue intelligence files
- audit standard
- workflow guide
- artifact schema

### 2.2 Weekly event artifacts
These are generated or refreshed per tournament.

Examples:
- field input files
- player trait matrix
- scored field output
- player brief package
- event app data bundle
- Round 1 live update pack
- final audit package

### 2.3 Deploy artifacts
These are the files needed to render a usable event dashboard or static site.

Examples:
- HTML shell
- CSS
- JS
- JSON payloads
- CSV downloads
- image assets
- notes / README for manual deploy

## 3. Folder standard
Use this structure for generated outputs.

```text
PGA_VenueDNA/
  library/
    engine/
    venues/
    standards/
  events/
    [YEAR]_[EVENT_SLUG]/
      input/
      output/
      deploy/
      audit/
```

Within Perplexity Space, persistent files should mirror the `library/` structure conceptually even if stored flat.

## 4. Naming convention
Use lowercase or uppercase consistently within a class. Event deliverables should use event-specific slugs.

Recommended convention:
- library files: `NN_PGA_VENUEDNA_[NAME].md`
- venue files: `[VENUECODE]_INTELLIGENCE_[YEAR]_vN.md`
- event files: `[year]_[event_slug]_[artifact_name].[ext]`

Examples:
- `2026_us_open_field_input.csv`
- `2026_us_open_vts_full.csv`
- `2026_us_open_player_briefs.json`
- `2026_us_open_event_payload.json`
- `2026_us_open_audit_log.md`

## 5. Persistent Space file set
These are the core files that should ultimately live in the Space as stable knowledge assets.

### 5.1 Engine files
- `00_PGA_VENUEDNA_MASTER_ARCHITECTURE.md`
- `01_PGA_VENUEDNA_MASTER_SPACE_PROMPT.md`
- `02_PGA_VENUEDNA_SCORING_SPEC.md`
- `03_PGA_VENUEDNA_LEARNING_LOOP.md`
- `04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md`
- `05_PGA_VENUEDNA_SPACE_SETUP_GUIDE.md`
- `06_PGA_VENUEDNA_EVENT_WORKFLOW.md`
- `07_PGA_VENUEDNA_AUDIT_STANDARD.md`

### 5.2 Venue files
One venue intelligence file per locked course.

### 5.3 Optional helper files
- glossary of trait terms
- source hierarchy file
- DataGolf field-ingestion checklist
- deploy README

## 6. Weekly event pack
Every tournament should resolve to one standard event pack.

Minimum event pack contents:
- field input file
- event context JSON
- player trait/form matrix
- full scored output
- player briefs package
- event payload JSON
- event links file
- live update file if R1+ exists
- post-event audit package

## 7. Input artifacts
These are the files the engine expects from the user or from preprocessing.

### 7.1 Field input CSV
File name:
- `[year]_[event_slug]_field_input.csv`

Purpose:
- master player-level modeling input for the week

Minimum columns:
- player_name
- player_id if available
- country
- field_status
- is_debut
- debut_class_prelim
- career_venue_starts
- career_venue_rounds
- career_venue_sg
- neutral_skill_sg_source
- true_sg_total
- true_sg_ott
- true_sg_app
- true_sg_arg
- true_sg_putt
- recent_form_index
- form_score_adjusted
- sg_ott_recent
- sg_app_recent
- sg_arg_recent
- sg_putt_recent
- sg_putt_surface
- par5_scoring
- pressure_hole_scoring if available
- comp_course_signal
- injury_flag
- dk_salary if applicable
- notes

### 7.2 Event context JSON
File name:
- `[year]_[event_slug]_event_context.json`

Purpose:
- venue and setup context for the week

Minimum keys:
- event_name
- event_slug
- season_year
- venue_name
- venue_code
- venue_file_version
- course_par
- course_yardage
- surface
- cut_rule
- field_size
- weather_forecast_class
- expected_scoring_band
- variance_expectation
- notes_on_setup_change
- notes_on_data_gaps
- fairway_width_class
- rough_severity_class
- firmness_class
- green_speed_policy
- rollout_class
- long_iron_frequency_class
- difficulty_class
- event_class
- generated_at
- engine_version
- scoring_spec_version
- learning_loop_version
- event_iteration

Notes:
- `expected_conditions`, `firmness_outlook`, and `wind_outlook` may still be included as descriptive helper keys, but the setup-class fields above are the canonical inputs for anti-pattern magnitude and risk-stressor logic.
- If a field is unknown, store `unknown` rather than omitting the key.

## 8. Core output artifacts
These are the engine’s mandatory outputs for a full event build.

### 8.1 Trait/form matrix CSV
File name:
- `[year]_[event_slug]_trait_form_matrix.csv`

Purpose:
- debugging and analysis table showing raw and adjusted traits before final scoring

Minimum columns:
- player_name
- neutral_skill_sg
- neutral_skill_index
- data_depth_class
- baseline_confidence_band
- true_sg_total
- true_sg_ott
- true_sg_app
- true_sg_arg
- true_sg_putt
- sg_putt_surface
- recent_form_index
- form_score_adjusted
- comp_course_adjustment_prelim
- venue_history_rounds
- venue_history_sg
- named_risk_tags
- likely_anti_pattern_flags
- missing_data_notes

### 8.2 Full scored field CSV
File name:
- `[year]_[event_slug]_vts_full.csv`

Purpose:
- canonical player ranking output for the event

Minimum columns:
- rank_model
- player_name
- neutral_skill_sg
- neutral_skill_index
- data_depth_class
- baseline_confidence_band
- venue_fit_score
- venue_fit_delta
- venue_fit_confidence_band
- comp_course_adjustment
- venue_history_rounds
- venue_history_sg
- venue_history_delta
- venue_history_confidence_band
- pre_penalty_vts
- blend_class
- blend_weights_used
- tier_eligibility_gate_status
- debut_class
- debut_penalty_applied
- anti_pattern_flags
- anti_pattern_penalty_total
- anti_pattern_trigger_trace
- anti_pattern_modifier_trace
- primary_risk_trait
- risk_stressor_active
- risk_secondary_discount_applied
- risk_discount_trace
- form_score_adjusted
- recent_form_index
- recent_form_gate_applied
- health_flag
- health_gate_status
- health_gate_reason
- player_variance_band
- volatility_index
- venue_variance_class
- variance_adjustment_trace
- probability_compression_class
- probability_compression_coefficients
- probability_compression_trace
- vts_final
- tier
- tier_reason
- win_pct
- top3_pct
- top5_pct
- top10_pct
- top20_pct
- make_cut_pct
- miss_cut_pct
- trace_notes

This is the single source of truth for rankings, tiers, gates, and probability outputs.

### 8.3 Player briefs JSON
File name:
- `[year]_[event_slug]_player_briefs.json`

Purpose:
- structured data for Tier 1 and Tier 2 player cards, chat summaries, and event app rendering

Top-level structure:
```json
{
  "event": {},
  "generated_at": "",
  "tier_1": [],
  "tier_2": []
}
```

Each player object should include:
- player_name
- tier
- vts_final
- win_pct
- top10_pct
- make_cut_pct
- neutral_skill_summary
- venue_fit_summary
- venue_history_summary
- penalties_summary
- risk_vector
- conviction_statement
- named_failure_condition
- trace_notes

### 8.4 Event payload JSON
File name:
- `[year]_[event_slug]_event_payload.json`

Purpose:
- primary front-end data object for a static event app

Recommended top-level structure:
```json
{
  "event": {},
  "venue": {},
  "model_summary": {},
  "tiers": {
    "tier_1": [],
    "tier_2": [],
    "tier_3": [],
    "tier_4": [],
    "tier_5": []
  },
  "flags": {
    "anti_patterns": [],
    "value_flags": [],
    "health_gates": [],
    "risk_stressors": []
  },
  "players": [],
  "metadata": {}
}
```

Required objects:
- event summary
- venue summary
- trait weight matrix summary
- model winner card
- five tier collections
- anti-pattern flags
- value flags
- scoring-band notes
- setup-conditional notes
- metadata for file version, venue file version, generated time

Recommended metadata keys:
- engine_version
- scoring_spec_version
- learning_loop_version
- venue_file_version
- event_iteration
- probability_compression_class

### 8.5 Event links JSON
File name:
- `[year]_[event_slug]_links.json`

Purpose:
- stable URL map for event app, research workflow, and manual review

Include:
- tournament homepage
- official leaderboard
- DataGolf event page if used
- field list source
- weather source
- DK contest links if applicable
- notes links

## 9. Live update artifacts
These activate only when live diagnostics are run.

### 9.1 Round 1 diagnostic JSON
File name:
- `[year]_[event_slug]_r1_diagnostic.json`

Purpose:
- structured update for post-R1 re-tiering

Include:
- scoring_conditions_summary
- promotions
- downgrades
- holds
- failed_trait_explanations
- updated_probabilities_for_promoted_and_downgraded_players
- structural_miss_vs_variance_noise_tags
- live_setup_change_notes

### 9.2 Live leaderboard snapshot CSV
File name:
- `[year]_[event_slug]_live_snapshot_r1.csv`

Purpose:
- freeze-frame evidence record for live decisions

## 10. Audit artifacts
These close the loop after the event.

### 10.1 Event audit log markdown
File name:
- `[year]_[event_slug]_audit_log.md`

Purpose:
- human-readable audit narrative and verdict

### 10.2 Audit write-back JSON
File name:
- `[year]_[event_slug]_audit_writeback.json`

Purpose:
- structured venue and engine changes ready for manual or assisted file update

Suggested keys:
- event_context
- venue_changes
- engine_rule_flags
- miss_ledger_rows
- confidence_updates
- follow_up_actions

Recommended additional keys:
- setup_modifier_review
- risk_linkage_review
- probability_calibration_review

### 10.3 Miss ledger CSV append block
File name:
- `[year]_[event_slug]_miss_ledger_rows.csv`

Purpose:
- append-ready rows for the global miss ledger

## 11. Deploy package
The deploy package is what powers a Netlify-ready static event app.

### 11.1 Deploy folder structure
```text
[year]_[event_slug]_deploy/
  index.html
  styles.css
  app.js
  data/
    event_payload.json
    vts_full.csv
    player_briefs.json
    links.json
  assets/
    logo.svg
    optional_images/
  README.md
```

### 11.2 Deploy rules
- `index.html` is the app shell
- `app.js` reads the JSON and CSV payloads
- `styles.css` controls display only; model logic stays in source data generation, not browser logic
- all event-specific content should be data-driven from `/data`
- the deploy package should work as a static site without a build command

### 11.3 README contents
The deploy README should tell the user:
- whether the package is drag-and-drop ready for Netlify
- whether it can be used as a repo root or subdirectory deploy
- which files to update for a new event
- which files are generated and should not be hand-edited

## 12. Space file vs weekly upload split
Perplexity Spaces support custom instructions, file uploads, connected repositories, and links within a Space, which makes them suitable for storing stable engine files and recurring venue intelligence while weekly data can be added as event-specific files.

### Keep permanently in Space files
- master prompt
- architecture and standards docs
- scoring spec
- learning-loop spec
- artifact schema
- setup guide
- locked venue files
- audit standard
- global miss ledger if size permits

### Upload or refresh weekly
- field input CSV
- event context JSON
- trait/form matrix
- vts full output
- player briefs JSON
- event payload JSON
- R1 diagnostic files
- audit write-back files

## 13. Chat output contract
When the system answers in chat for a tournament build, it should be able to reference and synthesize these artifacts into five standard output blocks:
- venue trait summary
- full tier rankings
- Tier 1 and 2 player briefs
- anti-pattern and value flag section
- probability and risk section

The files are the canonical storage layer. The chat response is the readable layer.

## 14. Data integrity rules
Artifact generation fails if:
- file names do not follow event naming conventions
- event context omits setup-class fields needed by the active venue file
- VTS output omits component fields required by the scoring spec
- tier eligibility or risk-linkage actions are applied but not logged in artifact fields
- probabilities are emitted without model metadata or compression metadata
- deploy files contain hand-written rankings that diverge from source data files
- derivative fantasy outputs are mixed into core ranking files
- audit files overwrite pre-event source outputs instead of versioning them

## 15. Versioning rules
Each event artifact set should include metadata for:
- generated_at timestamp
- venue_file_version
- engine_version
- scoring_spec_version
- learning_loop_version
- event_iteration label such as `initial`, `update_r1`, `final`, `audit`

This prevents confusion between early-week, post-weather, and live-updated builds.

## 16. Operating standard
The artifact layer must always prefer:
- standard schema over improvisation
- generated data over manual restatement
- static deploy simplicity over fragile tooling
- readable outputs plus auditable source files
- permanent Space knowledge separated from weekly event payloads

This file defines the canonical file, output, and deploy contract for the single-system Perplexity PGA VenueDNA engine.
