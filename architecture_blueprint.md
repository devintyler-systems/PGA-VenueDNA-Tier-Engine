# VenueDNA UI/UX Architecture Blueprint

**Source of truth** for structural layout conventions established across the 2026 Genesis Scottish Open and 2026 The Open Championship. All future event generation routines must conform to this specification.

---

## Section 1 — Top-Level Forecast Deck Grid Hierarchy

Container: `#forecast-deck`

- Renders as a horizontal 4-box grid.
- Each box maps to a named weather/condition severity class:

| CSS Class | Severity Label |
|---|---|
| `fb-exceptional` | Exceptional (best-case scoring conditions) |
| `fb-very-benign` | Very Benign |
| `fb-benign` | Benign |
| `fb-challenging` | Challenging |
| `fb-severe` | Severe (worst-case conditions) |

- Exactly **4 boxes** are rendered at a time. The active condition class is applied to the relevant box; inactive boxes render in muted state.
- Box content: condition label, wind speed band, precipitation probability, temperature range, and a one-line scoring impact note.
- The deck is read-only (display only); no interactive controls live inside `#forecast-deck`.

---

## Section 2 — Summary Card Layouts

Three equal-width (`1/3` grid) cards render immediately below the forecast deck.

### 2a — VENUE Card
- Displays: course name, par, yardage, surface type, primary grass, course designer, and year opened.
- Sub-row: current course setup notes (pin positions, rough height, green speed estimate).

### 2b — TRAIT WEIGHTS Card
- Renders the 10 canonical trait metrics and their assigned percentage weights for the event.
- Weights must sum to exactly **100%**.
- Canonical trait order (display) — Schema v1.1 keys:
  1. `app_wedge`
  2. `app_100_150`
  3. `app_150_200`
  4. `ott_accuracy`
  5. `ott_distance`
  6. `putt_short_conv`
  7. `putt_lag`
  8. `arg_rough`
  9. `arg_bunker`
  10. `par5_scoring`
- Each row: trait label (human-readable), weight percentage, optional directional arrow if weight deviates >2 pp from tour-average baseline.

### 2c — WINNER PROFILE Card
- Synthesized narrative block (2–4 sentences) describing the archetypal winning player type for this venue.
- Followed by 3–5 bullet traits labeled **Key Differentiators**.
- Source: `event_payload.json → winner_profile`.

---

## Section 3 — Interactive Filter Query Builder

Container: `#active-filters-zone`

### Rule Binding
- Supports sequential multi-rule bindings (AND logic).
- Each rule: `[trait metric] [operator] [threshold value]`
- Operators: `>=`, `<=`, `=`
- Trait metric dropdown pulls from the same 10-trait canonical list defined in Section 2b.
- Threshold value accepts any numeric input (decimals permitted).
- Rules stack visually as removable chips; up to **10 simultaneous rules** supported.

### Quick Filter Macros (Preset Chips)
Exactly 5 preset macro chips must be present:

| Chip Label | Rule Logic |
|---|---|
| **Ball-Strikers** | `ott_accuracy >= 0.6` AND `ott_positional >= 0.6` |
| **Wedge Artists** | `arg_scrambling >= 0.65` AND `app_150_200 >= 0.6` |
| **Putter-Reliant** | `putt_overall >= 0.7` |
| **Course Horses** | `course_history >= 0.7` |
| **Hot Form** | `mental_form >= 0.65` |

- Clicking a macro chip appends its rules to the active filter stack (does not replace existing rules).
- A **Clear All** control resets the filter stack to empty.

### Filter Output
- The player board below `#active-filters-zone` re-renders in real time to show only players passing all active rules.
- Match count badge updates dynamically: `N players match`.

---

## Section 4 — Tab Navigation & Glossary Modal

### Horizontal Tab Bar
Five tabs, rendered as a single horizontal button group:

| Tab Label | Data Source |
|---|---|
| Pre-Tournament | `event_payload.json` |
| R1 | `r1_analysis.json` |
| R2 | `r2_analysis.json` |
| R3 | `r3_analysis.json` |
| R4 / Final | `r4_analysis.json` or `final_analysis.json` |

- Tabs for rounds not yet played are visually disabled (greyed, non-clickable).
- Active tab persists in `localStorage` key `venuedna_active_tab`.

### Glossary Modal (`#glossary-modal-overlay`)
- Triggered by a **Glossary** button in the header or sidebar.
- Overlay covers the full viewport; clicking outside the modal panel closes it.
- State variable: `glossaryModalOpen` (boolean, default `false`).
- Panel interior renders a **three-column grid**:

| Column | Content |
|---|---|
| Column 1 | Strokes Gained metric definitions (SG:OTT, SG:APP, SG:ARG, SG:PUTT, SG:T2G, SG:Total) |
| Column 2 | VenueDNA trait metric definitions (all 10 canonical traits) |
| Column 3 | Score / odds / probability term definitions (Live Win %, Top-5/10/20 %, Rho, etc.) |

- Each entry: **term** (bold) + one-sentence plain-English definition.
- Modal has no sub-navigation or nested tabs.

---

## Section 5 — Cumulative Learning Grid Structure

Container: `#cumulative-learning-grid`

Renders as a **5-column grid**, one row per trait metric (10 rows total).

| Column | Field | Notes |
|---|---|---|
| 1 | **Trait Model Key** | Machine-readable trait slug (e.g. `ott_accuracy`) |
| 2 | **Consensus Pill** | Color-coded badge: `bullish` (green) / `neutral` (grey) / `bearish` (red) |
| 3 | **Abs Magnitude** | Absolute value of cumulative signal delta; formatted to 2 decimal places |
| 4 | **Proxy Confidence** | `high` / `medium` / `low` label derived from source_confidence across rounds |
| 5 | **Trajectory Marks** | Per-round delta sparkline or arrow sequence (e.g. `↑ ↑ → ↓`) |

### Data Source
- Populated from `cumulative_learning.json → traits[]`.
- Schema version: `1.0`.
- Grid header row is sticky on scroll.
- Rows with `abs_magnitude = 0` and `consensus = neutral` render at reduced opacity (0.5).

---

## Compiler Validation Hook

`engine/build_round_analysis.py` checks for the presence of this file immediately prior to output serialization:

```python
import os as _os
if not _os.path.exists("C:/PGA_VenueDNA/architecture_blueprint.md"):
    print("[warn] System architecture blueprint missing.")
```

This is a **non-breaking warning gate** — the build continues regardless. Its presence in the pipeline ensures that blueprint drift is surfaced during live event builds.

---

*Last codified: 2026-07-17 | Events: 2026 Genesis Scottish Open, 2026 The Open Championship*
