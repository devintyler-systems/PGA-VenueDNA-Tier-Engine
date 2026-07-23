# 00 — PGA VenueDNA Master Architecture

**Version:** 1.1
**Status:** Canonical
**Scope:** Full platform — all events, all engines, all deploy artifacts

---

## 1. SYSTEM IDENTITY

VenueDNA is a deterministic course-fit ranking engine for PGA Tour events. It produces official player rankings and tier projections driven exclusively by VenueDNA scoring logic. DataGolf (DG) prediction fields are ingested as benchmark context and audit decomposition only — they do not determine official ranks, tiers, or projections at any stage.

---

## 2. AUTHORITY CHAIN

```
VenueDNA_* fields  →  OFFICIAL  (ranks, tiers, projections, trait scores, flags)
DG_*      fields   →  BENCHMARK (decomposition audit, comparison only)
```

Hard rules:
- `VenueDNA_rank` is the only field that controls row ordering on official boards.
- `VenueDNA_tier` is the only field that controls tier assignment.
- `VenueDNA_final_projection` is the only field that controls official board projection.
- DG benchmark fields must never be used to sort, filter, or assign rank in official mode.
- Browser/deploy code must never recalculate official ranks from DG fields.
- Scenario mode is the only context where non-official orderings are permitted, and scenario mode must be visually distinct from official mode with one-click recovery to official ordering.

---

## 3. DATA PIPELINE LAYERS

```
Layer 0 — Ingestion
  events/{event_slug}/input/
    pga_field.csv               ← tee times, wave, start hole, dg_id
    dg_decomposition.csv        ← DG benchmark decomposition
    datagolf.csv                ← DG prediction summary
    dg_course_table.csv         ← DG course history table
    dg_performance_2026.csv     ← in-season DG performance
    pga_field_trending_table.csv← trending/momentum signals
    app_skill_l12_sg.csv        ← approach skill SG
    app_skill_l12_gh.csv        ← approach GIR
    app_skill_l12_bad.csv       ← approach bad shot rate
    app_skill_l12_great.csv     ← approach great shot rate
    app_skill_l12_prox.csv      ← approach proximity
    pga_sg_query_allcourses_l{6,12,24}.csv    ← baseline SG horizons
    pga_sg_query_{slug}_similar_l{6,12,24}.csv ← similar-course SG horizons

Layer 1 — Latent Scoring (Python engine)
  engine/enrich_cards.py        ← dual-vector True SG compute; writes board_export.json
  (future: engine/latent_model.py for extended trait scoring)

Layer 2 — Canonical Output (generated artifacts)
  events/{event_slug}/output/
    {slug}_trait_form_matrix.csv   ← per-player trait scores + DG benchmark columns
    {slug}_vts_full.csv            ← full VTS ranking with tee times
    {slug}_player_briefs.json      ← narrative briefs per player
    {slug}_event_payload.json      ← master event context + council findings
    {slug}_links.json              ← external link registry

Layer 3 — Event Deployment (static UX)
  events/{event_slug}/deploy/
    data/board_export.json         ← primary runtime payload (copied from output)
    data/{slug}_event_payload.json ← event context payload
    data/{slug}_vts_full.csv       ← VTS full ranking
    data/{slug}_player_briefs.json ← player brief narratives
    data/{slug}_links.json         ← link registry
    app.js                         ← UI logic (reads from data/ only, no rank recalc)
    *.html                         ← static board shell
    styles.css
    assets/

Layer 4 — Round Analysis (post-round)
  engine/build_round_analysis.py  ← R1-R4 live scoring + trait validation
  events/{event_slug}/output/
    {slug}_r{N}_analysis.json      ← per-round board + Spearman rho
    {slug}_cumulative_learning.json← cross-round learning accumulation
    {slug}_council_findings.json   ← model council post-event synthesis
    {slug}_final_analysis.json     ← final tournament post-mortem
```

---

## 4. DUAL-VECTOR TRUE SG TOPOLOGY

The canonical scoring method decouples venue-specific signal from general skill baseline using two independent SG vectors per player:

```
Vector A — SG Base (Neutral Skill)
  Source: pga_sg_query_allcourses_l{6,12,24}.csv
  Represents: General player skill across all competitive rounds
  Decay: stability-heavy [6m:0.20, 12m:0.30, 24m:0.50]

Vector B — SG Similar (Venue Fit)
  Source: pga_sg_query_{slug}_similar_l{6,12,24}.csv
  Represents: Player performance at courses structurally similar to the target venue
  Sample-weight regression: W = min(1.0, N_rounds / 20.0)
  Decay: recency-heavy [6m:0.50, 12m:0.30, 24m:0.20]

Delta Fit = SG_Sim_Regressed - SG_Base
  Interpretation: Positive = course-type specialist upside; Negative = course-type headwind
  Clamp: [-0.50, +0.50] SG/round
```

The full math is in `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`.

---

## 5. PATH DISCIPLINE

```
standards/          ← shared governance, schema, scoring specs (never event-specific)
library/venues/     ← permanent venue intelligence (persists across years)
events/{slug}/
  input/            ← raw ingested CSVs (never modified by engine)
  output/           ← canonical generated artifacts (engine writes here)
  deploy/           ← static UX package (reads from deploy/data/ only)
  deploy/data/      ← copies of output/ files for UX consumption
  audit/            ← diagnostic and review placeholders
engine/             ← Python compute scripts (enrich_cards.py, build_round_analysis.py)
tests/              ← pytest test suite covering engine pure functions
docs/               ← plans, specs, design decisions (not runtime)
```

No engine output goes directly to `deploy/` root. All deploy data must flow through `deploy/data/`.

---

## 6. CANONICAL FILENAMES

Event slug format: `YYYY_{event_name_snake_case}` (e.g., `2026_3m_open`)

Output files use slug as prefix:
```
{slug}_trait_form_matrix.csv
{slug}_vts_full.csv
{slug}_player_briefs.json
{slug}_event_payload.json
{slug}_links.json
{slug}_r{N}_analysis.json
{slug}_cumulative_learning.json
{slug}_council_findings.json
{slug}_final_analysis.json
```

Deploy runtime payload:
```
deploy/data/board_export.json   ← primary UI data file (dual-vector schema)
```

---

## 7. SCHEMA VERSION

Current canonical schema: **1.1**

Schema 1.1 introduces:
- Dual-vector VTS (`sg_base_composite`, `sg_similar_composite`, `delta_fit`)
- `data_depth` field (`FULL` / `DEBUT`)
- Decoupled decay weights for Base vs. Delta Fit
- Tempered softmax probability vectors replacing flat percentage tables

Schema version is written into every generated artifact as `schemaVersion` or `schema_version`.

---

## 8. DEPENDENCY ORDER

Before any event build begins:
1. All 5 standards files must exist in `standards/`
2. Venue library files must exist in `library/venues/{venue_slug}/`
3. All required input CSVs must exist in `events/{slug}/input/`
4. Output directory must exist at `events/{slug}/output/`

If any standard is missing, stop and report the exact path before generating downstream artifacts.
