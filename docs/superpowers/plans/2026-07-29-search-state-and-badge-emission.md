# Search State + Badge Emission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace DOM-hiding search with canonical state-driven filtering (Obj A) and implement the full badge qualification and emission pipeline from engine to artifact to UI (Obj B–D), covering 7 of 8 policy badges from confirmed source data.

**Architecture:** A new `build_badge_inputs()` function in `enrich_cards.py` assembles a normalized per-player badge-input record (with provenance) from confirmed raw source columns. `qualify_badges()` consumes this record against `badge_policy.v1.json`. Emitted `badges[]` flows through the JSON artifact. A standalone release gate validator runs post-build. Search state joins `S.activeFilters` in the harness state machine; badge filters are enabled when the artifact contains emitted badges.

**Tech Stack:** Python 3.x + pytest (engine + validator tests); vanilla JS (harness, no new framework); `config/badge_policy.v1.json` as single source of truth for badge definitions.

## Global Constraints

- Do NOT modify scoring logic, tiers, VTS, NeutralSkill, VenueFitDelta, VenueHistoryDelta, or penalty calculations.
- Do NOT use `dg_decomposition.csv` contribution fields (`driving_dist_adj`, `driving_acc_adj`) as badge inputs — use raw normalized metrics from `pga_sg_query_allcourses_l24.csv` only.
- Do NOT infer badges client-side — browser renders artifact-emitted data only.
- Do NOT hard-code player names, badge IDs, or qualification results.
- Do NOT add `row.style.display`, CSS hiding, or a second visibility source of truth for search.
- Do NOT add new SaaS or runtime dependency for the release gate.
- `config/badge_policy.v1.json` is the only badge definition source; no badge constants elsewhere.
- Unknown `badge_id` values must count as validation errors and block release.
- Minimal, localized patches — no refactors of unrelated code.
- Every emitted badge must include `qualification_reason` naming the source file, column/window, and observed metric value.
- Commit after every task that produces an independently testable deliverable.

## Source File Reconnaissance (confirmed before coding)

### `dg_performance_2026.csv` — exact columns
```
player_name, events_played, wins, x_wins, x_wins_majors, rounds_played, shotlink_played,
putt_true, arg_true, app_true, ott_true, t2g_true, total_true
```
These are ShotLink **long-run true-skill composites** — not rolling-window form indicators.
`total_true` is cumulative ShotLink SG, NOT a current-form measure.
→ **`hot_streak` DOES NOT use this file as primary.** Use L6−L24 delta fallback.

### `pga_sg_query_allcourses_l24.csv` — key badge-relevant columns
```
player_name, rounds_played, dist_mean, dist_rank, acc_mean, acc_rank,
putt_mean, putt_rank, total_mean, total_rank, app_mean, app_rank, ...
```
- `dist_mean` → `bomber` badge source
- `acc_mean` → `precision_driver` badge source
- `putt_mean` → `putter` badge source
- `total_mean` → L24 baseline for `hot_streak` delta

### `pga_sg_query_allcourses_l6.csv` — same schema as l24
- `total_mean` → L6 recent window for `hot_streak` delta
- `rounds_played` → minimum-round gate for `hot_streak`

### `detroit_golf_club_CH.csv` — exact columns
```
player_name,
2021 (Rocket Mortgage Classic), 2022 (Rocket Mortgage Classic),
2023 (Rocket Mortgage Classic), 2024 (Rocket Mortgage Classic),
2025 (Rocket Classic),
rounds_played, historical_true_sg, versus_expected, ch_adjustment, experience_adjustment
```
- Annual columns hold result values (CUT, WD, T12, numeric, null) — non-null = start occurred
- `detroit_starts` = count of non-null values across the 5 annual columns
- `rounds_played` = included in qualification_reason for detroit_veteran

## Corrected Badge Availability Matrix

| Badge | Status | Source File | Source Column(s) |
|-------|--------|-------------|------------------|
| `iron_surgeon` | ✅ Implementable | `app_skill_l12_sg.csv + prox.csv` | `trait_approach_raw`, `trait_long_iron_raw` |
| `debut` | ✅ Implementable | `detroit_golf_club_CH.csv` | 5 annual columns (null = no start) |
| `detroit_veteran` | ✅ Implementable | `detroit_golf_club_CH.csv` | 5 annual columns (count non-null ≥ 3) |
| `bomber` | ✅ Implementable | `pga_sg_query_allcourses_l24.csv` | `dist_mean` (NOT `driving_dist_adj`) |
| `precision_driver` | ✅ Implementable | `pga_sg_query_allcourses_l24.csv` | `acc_mean` (NOT `driving_acc_adj`) |
| `putter` | ✅ Implementable | `pga_sg_query_allcourses_l24.csv` | `putt_mean` |
| `hot_streak` | ✅ Implementable | `l6.csv + l24.csv` | `total_mean` delta (L6 − L24), min-round gated |
| `par5_predator` | ⛔ BLOCKED | — | No par-5 source column in any supplied file |

## Normalized Badge-Input Schema (per player, built before qualification)

Each entry has provenance so `qualify_badges()` can construct accurate `qualification_reason` strings and the validator can detect missing/malformed inputs.

```python
# Per-player badge input record (built by build_badge_inputs())
badge_inputs = {
    "approach_play": {
        "source_file":   "app_skill_l12_sg.csv",
        "source_column": "trait_approach_raw",
        "window":        "12m",
        "value":         float,          # raw SG value; None if unavailable
        "availability":  str,            # "DERIVED" | "MISSING_ZERO_FILLED"
        "usable_for_badges": bool,       # from trait_availability
    },
    "iron_play": {
        "source_file":   "app_skill_l12_sg.csv + app_skill_l12_prox.csv",
        "source_column": "trait_long_iron_raw",
        "window":        "12m",
        "value":         float,
        "availability":  str,
        "usable_for_badges": bool,
    },
    "driving_distance": {
        "source_file":   "pga_sg_query_allcourses_l24.csv",
        "source_column": "dist_mean",
        "window":        "L24",
        "value":         float,          # yards above/below field avg; None if not in file
        "rounds":        int,
        "availability":  str,            # "MEASURED" | "MISSING"
        "usable_for_badges": bool,
    },
    "driving_accuracy": {
        "source_file":   "pga_sg_query_allcourses_l24.csv",
        "source_column": "acc_mean",
        "window":        "L24",
        "value":         float,
        "rounds":        int,
        "availability":  str,
        "usable_for_badges": bool,
    },
    "putting": {
        "source_file":   "pga_sg_query_allcourses_l24.csv",
        "source_column": "putt_mean",
        "window":        "L24",
        "value":         float,
        "rounds":        int,
        "availability":  str,
        "usable_for_badges": bool,
    },
    "recent_form": {
        "source_file":   "pga_sg_query_allcourses_l6.csv + l24.csv",
        "source_column": "total_mean (L6 − L24 delta)",
        "window":        "L6 vs L24",
        "value":         float,          # delta; None if sample gate fails
        "l6_total_mean": float,
        "l6_rounds":     int,
        "l24_total_mean": float,
        "l24_rounds":    int,
        "availability":  str,            # "MEASURED" | "INSUFFICIENT_SAMPLE"
        "usable_for_badges": bool,
        # minimum gates: l6_rounds >= 8 AND l24_rounds >= 16
    },
    "course_history": {
        "source_file":   "detroit_golf_club_CH.csv",
        "source_column": "2021-2025 annual columns (non-null = start)",
        "window":        "2021-2025",
        "detroit_starts": int,           # count of non-null annual values
        "rounds_played":  int,           # from rounds_played column
        "availability":  str,            # "MEASURED" | "MISSING"
        "usable_for_badges": bool,
    },
}
```

## Pipeline Path (confirmed)

```
events/2026_rocket_classic/input/*.csv
→ events/2026_rocket_classic/engine/enrich_cards.py  §10 main()
    [existing] per-player loop → players_raw populated
    [existing] assembly loop → trait_availability built, strength/weakness tags
    [NEW INSERT POINT A]:  build_badge_inputs() per player
    [NEW INSERT POINT B]:  compute_badge_percentiles() field-wide
    [NEW INSERT POINT C]:  qualify_badges() per player → p["badges"]
    sort + rank
    reorder() — add "badges" to _first
    [schema version bump: rocket-classic-v1.3]
→ deploy/data/2026_rocket_classic_event_payload.json
→ deploy/fixture_harness.js
    [EDIT D]: S.activeFilters.query + filteredFixtures() + renderRoster() drawer guard
    [EDIT E]: playerToFixture() p.badges with validation
    [EDIT F]: renderBadgeFilters() presence-detect + checkboxes
    [EDIT G]: filteredFixtures() badge filter
```

---

## Task A — Normalized Source Ingestion + Badge Qualification in Engine

**Files:**
- Modify: `events/2026_rocket_classic/engine/enrich_cards.py`
- Create: `tests/test_badge_qualification.py`

**Interfaces produced (consumed by Task B):**
- `load_badge_policy(path: Path) -> list[dict]` — reads `config/badge_policy.v1.json["badges"]`
- `load_sg_l24(path: Path) -> dict[str, dict]` — loads `pga_sg_query_allcourses_l24.csv`; returns `{player_name: {dist_mean, acc_mean, putt_mean, total_mean, rounds_played}}`
- `load_sg_l6(path: Path) -> dict[str, dict]` — same schema, from `l6.csv`; returns `{total_mean, rounds_played}`
- `build_badge_inputs(p: dict, sg_l24_row: dict | None, sg_l6_row: dict | None) -> dict` — constructs normalized badge-input record per player; reads `trait_availability` from `p`; minimum round gates: `l6_rounds >= 8 AND l24_rounds >= 16`
- `compute_badge_percentiles(players_raw: list[dict]) -> list[dict[str, float]]` — field percentile per badge-eligible trait (among players where `usable_for_badges=True`); returns list indexed by player position
- `qualify_badges(badge_inputs: dict, badge_policy_badges: list[dict], player_percentiles: dict[str, float]) -> list[dict]` — returns `[{badge_id, qualification_reason}, ...]`; reasons must name source file, column/window, and observed value

**Interfaces consumed from existing code:**
- `players_raw[i]` — has keys `trait_availability`, `trait_approach_raw`, `trait_long_iron_raw`, `course_debut`, `player`, `player_id`
- `trait_availability[key]["usable_for_badges"]` — boolean eligibility per trait field
- `resolve(name, data, lookup)` — existing fuzzy-name resolver; use for all source lookups

### Implementation Steps

- [ ] **Step A1: Add `load_badge_policy()` to §2 (after `load_id_crosswalk`)**

```python
def load_badge_policy(policy_path: Path) -> list[dict]:
    """Load badge definitions from badge_policy.v1.json. Returns [] if file missing."""
    if not policy_path.exists():
        print(f"[enrich_cards] WARNING -- badge_policy not found: {policy_path}", file=sys.stderr)
        return []
    with policy_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("badges", [])
```

- [ ] **Step A2: Add `load_sg_l24()` and `load_sg_l6()` loaders to §2**

Both use the same schema; only the source file differs:
```python
def _load_sg_window(path: Path) -> dict[str, dict]:
    """
    Load a pga_sg_query_allcourses_l*.csv into {player_name: metric_dict}.
    Badge-relevant columns: dist_mean, acc_mean, putt_mean, total_mean, rounds_played.
    """
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            result[name] = {
                "dist_mean":    safe_float(row.get("dist_mean"), default=None),
                "acc_mean":     safe_float(row.get("acc_mean"), default=None),
                "putt_mean":    safe_float(row.get("putt_mean"), default=None),
                "total_mean":   safe_float(row.get("total_mean"), default=None),
                "rounds_played": int(safe_float(row.get("rounds_played"), default=0)),
            }
    return result

def load_sg_l24(path: Path) -> dict[str, dict]:
    return _load_sg_window(path)

def load_sg_l6(path: Path) -> dict[str, dict]:
    return _load_sg_window(path)
```

Note: `safe_float` must accept `default=None` — confirm the existing implementation supports this, or add an overload.

- [ ] **Step A3: Update `load_ch()` to also return `detroit_starts` from the 5 annual columns**

Replace the existing `load_ch()`:
```python
_CH_ANNUAL_COLS = [
    "2021 (Rocket Mortgage Classic)",
    "2022 (Rocket Mortgage Classic)",
    "2023 (Rocket Mortgage Classic)",
    "2024 (Rocket Mortgage Classic)",
    "2025 (Rocket Classic)",
]

def load_ch(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not path.exists():
        return result
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("player_name", "").strip().strip('"')
            if not name:
                continue
            detroit_starts = sum(
                1 for col in _CH_ANNUAL_COLS
                if str(row.get(col, "")).strip().lower() not in ("", "null", "none")
            )
            result[name] = {
                "ch_adjustment":  safe_float(row.get("ch_adjustment")),
                "experience_adj": safe_float(row.get("experience_adjustment")),
                "detroit_starts": detroit_starts,
                "rounds_played":  int(safe_float(row.get("rounds_played"), default=0)),
            }
    return result
```

- [ ] **Step A4: Add `_BADGE_AVAIL_MAP` constant after §1 constants**

```python
# Maps badge_policy.v1.json trait_id → trait_availability key.
# Determines which trait_availability key gates badge eligibility for percentile badges.
# trait_ids not listed here are handled by a separate non-percentile path in qualify_badges().
_BADGE_TRAIT_AVAIL_MAP: dict[str, str] = {
    "approach_play":    "trait_approach_raw",
    "iron_play":        "trait_long_iron_raw",
    # driving_distance, driving_accuracy, putting, recent_form: sourced from l24/l6 CSV;
    # eligibility determined by presence in those files (usable_for_badges in badge_input record).
}

# Minimum round gates for hot_streak: player must have sufficient sample in both windows.
BADGE_HOT_STREAK_L6_MIN_ROUNDS  = 8
BADGE_HOT_STREAK_L24_MIN_ROUNDS = 16
```

- [ ] **Step A5: Add `build_badge_inputs()` to §9 (before qualification functions)**

```python
def build_badge_inputs(
    p: dict,
    sg_l24_row: dict | None,
    sg_l6_row:  dict | None,
) -> dict:
    """
    Assemble normalized badge-input record for one player.
    Reads trait_availability from p["trait_availability"].
    All non-None values include source provenance for qualification_reason construction.
    """
    avail = p.get("trait_availability", {})

    def _ta_entry(avail_key: str, source_file: str, source_col: str, window: str) -> dict:
        ta = avail.get(avail_key, {})
        return {
            "source_file":      source_file,
            "source_column":    source_col,
            "window":           window,
            "value":            p.get(avail_key.replace("_raw", "_raw"), None),
            "availability":     ta.get("availability", "MISSING"),
            "usable_for_badges": ta.get("usable_for_badges", False),
        }

    # approach_play / iron_play from existing trait_availability
    approach = _ta_entry(
        "trait_approach_raw", "app_skill_l12_sg.csv", "trait_approach_raw", "12m"
    )
    approach["value"] = p.get("trait_approach_raw")

    iron = _ta_entry(
        "trait_long_iron_raw", "app_skill_l12_sg.csv + app_skill_l12_prox.csv",
        "trait_long_iron_raw", "12m"
    )
    iron["value"] = p.get("trait_long_iron_raw")

    # driving_distance / accuracy / putting / total from l24 CSV (not from decomp)
    def _l24_entry(col: str, source_col_name: str) -> dict:
        val   = sg_l24_row.get(col) if sg_l24_row else None
        rnds  = sg_l24_row.get("rounds_played", 0) if sg_l24_row else 0
        avail_status = "MEASURED" if (sg_l24_row is not None and val is not None) else "MISSING"
        return {
            "source_file":       "pga_sg_query_allcourses_l24.csv",
            "source_column":     source_col_name,
            "window":            "L24",
            "value":             val,
            "rounds":            rnds,
            "availability":      avail_status,
            "usable_for_badges": avail_status == "MEASURED",
        }

    # recent_form: L6 total_mean − L24 total_mean, gated on minimum rounds
    l6_tm   = sg_l6_row.get("total_mean")   if sg_l6_row  else None
    l6_rnd  = sg_l6_row.get("rounds_played", 0) if sg_l6_row else 0
    l24_tm  = sg_l24_row.get("total_mean")  if sg_l24_row else None
    l24_rnd = sg_l24_row.get("rounds_played", 0) if sg_l24_row else 0
    form_gate_ok = (
        l6_tm is not None and l24_tm is not None
        and l6_rnd  >= BADGE_HOT_STREAK_L6_MIN_ROUNDS
        and l24_rnd >= BADGE_HOT_STREAK_L24_MIN_ROUNDS
    )
    recent_form_entry = {
        "source_file":    "pga_sg_query_allcourses_l6.csv + l24.csv",
        "source_column":  "total_mean delta (L6 − L24)",
        "window":         "L6 vs L24",
        "value":          round(l6_tm - l24_tm, 4) if form_gate_ok else None,
        "l6_total_mean":  l6_tm,
        "l6_rounds":      l6_rnd,
        "l24_total_mean": l24_tm,
        "l24_rounds":     l24_rnd,
        "availability":   "MEASURED" if form_gate_ok else "INSUFFICIENT_SAMPLE",
        "usable_for_badges": form_gate_ok,
    }

    # course_history: detroit_starts from CH file
    ch_from_p = avail.get("ch_adjustment", {})
    detroit_starts = p.get("_detroit_starts", 0)   # set from ch_data in main loop
    ch_rounds      = p.get("_detroit_rounds", 0)
    ch_avail = "MEASURED" if detroit_starts > 0 or p.get("_ch_resolved", False) else "MISSING"
    # course_debut players also get a course_history entry with detroit_starts=0
    if not p.get("_ch_resolved", False):
        detroit_starts = 0
        ch_rounds      = 0
        ch_avail       = "MEASURED"    # debut is a confirmed data state, not missing

    ch_entry = {
        "source_file":    "detroit_golf_club_CH.csv",
        "source_column":  "2021-2025 annual columns (non-null = start)",
        "window":         "2021-2025",
        "detroit_starts": detroit_starts,
        "rounds_played":  ch_rounds,
        "availability":   ch_avail,
        "usable_for_badges": True,     # count-based; always evaluable
    }

    return {
        "approach_play":    approach,
        "iron_play":        iron,
        "driving_distance": _l24_entry("dist_mean",  "dist_mean"),
        "driving_accuracy": _l24_entry("acc_mean",   "acc_mean"),
        "putting":          _l24_entry("putt_mean",  "putt_mean"),
        "recent_form":      recent_form_entry,
        "course_history":   ch_entry,
    }
```

- [ ] **Step A6: Add `compute_badge_percentiles()` to §9**

```python
def compute_badge_percentiles(
    players_raw: list[dict],
    badge_inputs_list: list[dict],
) -> list[dict]:
    """
    Compute field percentile (0–100) per badge-eligible trait per player.
    Percentile is within the pool of players whose badge_input entry has usable_for_badges=True.
    Returns list indexed by player position; each entry is {trait_id: percentile}.
    """
    n      = len(players_raw)
    result: list[dict] = [{} for _ in range(n)]

    # All percentile-based badge trait_ids
    PERCENTILE_TRAITS = [
        "approach_play", "iron_play",
        "driving_distance", "driving_accuracy",
        "putting", "recent_form",
    ]

    for trait_id in PERCENTILE_TRAITS:
        eligible = [
            (i, badge_inputs_list[i][trait_id]["value"])
            for i in range(n)
            if badge_inputs_list[i].get(trait_id, {}).get("usable_for_badges", False)
            and badge_inputs_list[i][trait_id].get("value") is not None
        ]
        if not eligible:
            continue
        eligible.sort(key=lambda x: x[1], reverse=True)
        ne = len(eligible)
        for rank_0, (idx, _) in enumerate(eligible):
            pct = round(100.0 * (ne - 1 - rank_0) / ne) if ne > 1 else 50
            result[idx][trait_id] = pct

    return result
```

- [ ] **Step A7: Add `qualify_badges()` to §9**

```python
def qualify_badges(
    badge_inputs: dict,
    badge_policy_badges: list[dict],
    player_percentiles: dict[str, float],
) -> list[dict]:
    """
    Qualify a player against all badge definitions.
    badge_inputs: output of build_badge_inputs() for this player
    badge_policy_badges: the "badges" list from badge_policy.v1.json
    player_percentiles: {trait_id: field_percentile_0_100} for this player
    Returns [{badge_id, qualification_reason}, ...].
    """
    earned: list[dict] = []
    earned_ids: set[str] = set()

    for badge in sorted(badge_policy_badges, key=lambda b: b.get("display_order", 99)):
        bid             = badge["badge_id"]
        threshold       = badge.get("threshold", {})
        required_traits = badge.get("required_trait_ids", [])
        exclusions      = badge.get("exclusions", [])

        if any(ex in earned_ids for ex in exclusions):
            continue

        # ── Percentile-threshold badges ───────────────────────────────────
        if "field_percentile_min" in threshold:
            min_pct     = threshold["field_percentile_min"]
            eligible    = True
            reason_parts: list[str] = []

            for tid in required_traits:
                entry = badge_inputs.get(tid, {})
                if not entry.get("usable_for_badges", False):
                    eligible = False
                    break
                pct = player_percentiles.get(tid)
                if pct is None or pct < min_pct:
                    eligible = False
                    break
                val  = entry.get("value")
                win  = entry.get("window", "")
                src  = entry.get("source_column", tid)
                reason_parts.append(
                    f"{tid}: {val:+.3f} ({src}, {win}, {pct:.0f}th-pct)"
                    if isinstance(val, float) else
                    f"{tid}: {pct:.0f}th-pct ({src}, {win})"
                )

            if not eligible:
                continue

            # par5_predator guard — no valid source; must never emit
            if bid == "par5_predator":
                continue

            src_files = ", ".join(
                dict.fromkeys(badge_inputs[tid]["source_file"] for tid in required_traits if tid in badge_inputs)
            )
            reason = (f"Top-quintile {'; '.join(reason_parts)} "
                      f"(field threshold: {min_pct}th, source: {src_files})")
            earned.append({"badge_id": bid, "qualification_reason": reason})
            earned_ids.add(bid)

        # ── venue_starts_max: 0 → debut ───────────────────────────────────
        elif "venue_starts_max" in threshold and threshold["venue_starts_max"] == 0:
            ch = badge_inputs.get("course_history", {})
            if ch.get("usable_for_badges") and ch.get("detroit_starts", -1) == 0:
                earned.append({
                    "badge_id": bid,
                    "qualification_reason": (
                        "No prior Rocket Classic starts at Detroit Golf Club. "
                        f"(source: {ch['source_file']})"
                    ),
                })
                earned_ids.add(bid)

        # ── venue_starts_min: 3 → detroit_veteran ─────────────────────────
        elif "venue_starts_min" in threshold:
            min_starts = threshold["venue_starts_min"]
            ch = badge_inputs.get("course_history", {})
            starts  = ch.get("detroit_starts", 0)
            rounds  = ch.get("rounds_played", 0)
            if ch.get("usable_for_badges") and starts >= min_starts:
                earned.append({
                    "badge_id": bid,
                    "qualification_reason": (
                        f"{starts} prior Rocket Classic start(s) at Detroit Golf Club "
                        f"({rounds} rounds played). "
                        f"(source: {ch['source_file']})"
                    ),
                })
                earned_ids.add(bid)

    return earned
```

- [ ] **Step A8: Wire all new functions into `main()`**

**A8a** — Load badge policy and new source files at top of `main()` (after directory setup):
```python
_repo_root = _EVENT_DIR.parent.parent
badge_policy_badges = load_badge_policy(_repo_root / "config" / "badge_policy.v1.json")
print(f"  Badge policy: {len(badge_policy_badges)} badge definition(s) loaded")

sg_l24_data = load_sg_l24(input_dir / ALL_COURSES_FILES["24m"])
sg_l6_data  = load_sg_l6 (input_dir / ALL_COURSES_FILES["6m"])
lk_l24      = build_lookup(sg_l24_data)
lk_l6       = build_lookup(sg_l6_data)
```

**A8b** — In per-player raw loop, after `_ch_raw = resolve(...)`, store detroit_starts and rounds on the row dict:
```python
_ch_starts = _ch_raw.get("detroit_starts", 0) if _ch_raw else 0
_ch_rounds = _ch_raw.get("rounds_played",  0) if _ch_raw else 0
```
And in `players_raw.append({...})`:
```python
"_ch_resolved":    _ch_raw is not None,
"_detroit_starts": _ch_starts,
"_detroit_rounds": _ch_rounds,
```

**A8c** — After the "Assemble final records" loop, insert badge qualification pass:
```python
# ── Badge inputs + qualification ──────────────────────────────────────────
print("[enrich_cards] Building badge inputs and qualifying badges...")
badge_inputs_list: list[dict] = []
for p in players_raw:
    sg_l24_row = resolve(p["player"], sg_l24_data, lk_l24)
    sg_l6_row  = resolve(p["player"], sg_l6_data,  lk_l6)
    badge_inputs_list.append(build_badge_inputs(p, sg_l24_row, sg_l6_row))

badge_percentiles = compute_badge_percentiles(players_raw, badge_inputs_list)
for i, p in enumerate(players_raw):
    p["badges"] = qualify_badges(badge_inputs_list[i], badge_policy_badges, badge_percentiles[i])

total_badges = sum(len(p["badges"]) for p in players_raw)
print(f"  Badges emitted: {total_badges} across {len(players_raw)} scored players")
```

**A8d** — Add `"badges"` to `_first` list (after `"anti_pattern_flags"`):
```python
"trait_scores", "archetype_tags", "anti_pattern_flags", "badges",
```

**A8e** — Bump schema version:
```python
schema_ver = "rocket-classic-v1.3"  # v1.3: per-player badges[] field added
```

**A8f** — Add new private fields to `_drop`:
```python
"_ch_resolved", "_detroit_starts", "_detroit_rounds",
```

- [ ] **Step A9: Write unit tests** — Create `tests/test_badge_qualification.py`:

```python
"""Unit tests for badge qualification in the Rocket Classic event-local engine."""
import importlib.util
from pathlib import Path
import pytest

_ENGINE_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_rocket_classic" / "engine" / "enrich_cards.py"
)
_spec = importlib.util.spec_from_file_location("rocket_engine", _ENGINE_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

qualify_badges            = _mod.qualify_badges
compute_badge_percentiles = _mod.compute_badge_percentiles
build_badge_inputs        = _mod.build_badge_inputs
load_badge_policy         = _mod.load_badge_policy
_BADGE_TRAIT_AVAIL_MAP    = _mod._BADGE_TRAIT_AVAIL_MAP

_POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "badge_policy.v1.json"
BADGE_HOT_STREAK_L6_MIN_ROUNDS  = _mod.BADGE_HOT_STREAK_L6_MIN_ROUNDS
BADGE_HOT_STREAK_L24_MIN_ROUNDS = _mod.BADGE_HOT_STREAK_L24_MIN_ROUNDS


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_policy():
    return load_badge_policy(_POLICY_PATH)


def _inputs_stub(**overrides):
    """Minimal badge_inputs dict — all traits ineligible by default."""
    base = {
        "approach_play":    {"source_file": "f", "source_column": "c", "window": "w", "value": 0.5, "availability": "DERIVED",  "usable_for_badges": False},
        "iron_play":        {"source_file": "f", "source_column": "c", "window": "w", "value": 0.5, "availability": "DERIVED",  "usable_for_badges": False},
        "driving_distance": {"source_file": "f", "source_column": "dist_mean", "window": "L24", "value": 10.0, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "driving_accuracy": {"source_file": "f", "source_column": "acc_mean",  "window": "L24", "value": 0.05, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "putting":          {"source_file": "f", "source_column": "putt_mean", "window": "L24", "value": 0.40, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "recent_form":      {"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": 0.30, "l6_total_mean": 1.5, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "course_history":   {"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True},
    }
    for k, v in overrides.items():
        if k in base and isinstance(v, dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


# ── load_badge_policy ─────────────────────────────────────────────────────────

def test_load_badge_policy_returns_list():
    badges = _load_policy()
    assert isinstance(badges, list) and len(badges) == 8


def test_load_badge_policy_missing_file(tmp_path):
    assert load_badge_policy(tmp_path / "nonexistent.json") == []


# ── debut badge ───────────────────────────────────────────────────────────────

def test_debut_qualifies_when_zero_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert any(b["badge_id"] == "debut" for b in result)


def test_debut_not_emitted_when_one_start():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 1, "rounds_played": 4, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert not any(b["badge_id"] == "debut" for b in result)


# ── detroit_veteran badge ─────────────────────────────────────────────────────

def test_detroit_veteran_qualifies_at_three_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 3, "rounds_played": 12, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    ids = [b["badge_id"] for b in result]
    assert "detroit_veteran" in ids
    assert "debut" not in ids


def test_detroit_veteran_not_emitted_at_two_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 2, "rounds_played": 8, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert not any(b["badge_id"] == "detroit_veteran" for b in result)


# ── detroit_starts derivation from non-null annual cols ──────────────────────

def test_detroit_starts_counts_cut_as_start():
    """CUT is a valid start — it must be counted, not skipped."""
    from events.rockets_test_helper import detroit_starts_from_row  # use load_ch logic directly
    # We test by calling load_ch on a tmp CSV
    import csv, tempfile
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [
        {"player_name": "Test, Player",
         "2021 (Rocket Mortgage Classic)": "CUT",
         "2022 (Rocket Mortgage Classic)": "T9",
         "2023 (Rocket Mortgage Classic)": "null",
         "2024 (Rocket Mortgage Classic)": "",
         "2025 (Rocket Classic)": "T41",
         "rounds_played": "8",
         "historical_true_sg": "0.5",
         "versus_expected": "0.3",
         "ch_adjustment": "0.02",
         "experience_adjustment": "0.05"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        import pathlib
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Test, Player"]["detroit_starts"] == 3   # CUT + T9 + T41 = 3; null + "" = 0


def test_detroit_starts_counts_wd_as_start():
    import csv, tempfile, pathlib
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [{"player_name": "Test, WD",
             "2021 (Rocket Mortgage Classic)": "WD",
             "2022 (Rocket Mortgage Classic)": "",
             "2023 (Rocket Mortgage Classic)": "",
             "2024 (Rocket Mortgage Classic)": "",
             "2025 (Rocket Classic)": "",
             "rounds_played": "2",
             "historical_true_sg": "0.0",
             "versus_expected": "0.0",
             "ch_adjustment": "0.0",
             "experience_adjustment": "0.05"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Test, WD"]["detroit_starts"] == 1


def test_debut_has_zero_detroit_starts():
    import csv, tempfile, pathlib
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [{"player_name": "Debut, Player",
             "2021 (Rocket Mortgage Classic)": "",
             "2022 (Rocket Mortgage Classic)": "null",
             "2023 (Rocket Mortgage Classic)": "null",
             "2024 (Rocket Mortgage Classic)": "",
             "2025 (Rocket Classic)": "",
             "rounds_played": "0",
             "historical_true_sg": "0.0",
             "versus_expected": "0.0",
             "ch_adjustment": "0.0",
             "experience_adjustment": "0.0"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Debut, Player"]["detroit_starts"] == 0


# ── iron_surgeon badge ────────────────────────────────────────────────────────

def test_iron_surgeon_qualifies_at_80th_percentile():
    badges = _load_policy()
    inp = _inputs_stub(
        approach_play={"source_file": "f", "source_column": "trait_approach_raw", "window": "12m", "value": 1.2, "availability": "DERIVED", "usable_for_badges": True},
        iron_play=    {"source_file": "f", "source_column": "trait_long_iron_raw", "window": "12m", "value": 0.8, "availability": "DERIVED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"approach_play": 85, "iron_play": 82})
    assert any(b["badge_id"] == "iron_surgeon" for b in result)


def test_iron_surgeon_not_emitted_when_approach_ineligible():
    badges = _load_policy()
    inp = _inputs_stub(
        approach_play={"source_file": "f", "source_column": "c", "window": "w", "value": 1.2, "availability": "MISSING_ZERO_FILLED", "usable_for_badges": False},
        iron_play=    {"source_file": "f", "source_column": "c", "window": "w", "value": 0.8, "availability": "DERIVED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"approach_play": 90, "iron_play": 90})
    assert not any(b["badge_id"] == "iron_surgeon" for b in result)


# ── bomber badge ──────────────────────────────────────────────────────────────

def test_bomber_uses_dist_mean_not_decomp():
    """bomber must use dist_mean from l24.csv; driving_dist_adj is never a badge input."""
    badges = _load_policy()
    inp = _inputs_stub(
        driving_distance={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "dist_mean", "window": "L24", "value": 15.0, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"driving_distance": 90})
    b_ids = [b["badge_id"] for b in result]
    assert "bomber" in b_ids
    bomber = next(b for b in result if b["badge_id"] == "bomber")
    assert "dist_mean" in bomber["qualification_reason"]
    assert "l24" in bomber["qualification_reason"].lower() or "L24" in bomber["qualification_reason"]


def test_bomber_not_emitted_when_ineligible():
    badges = _load_policy()
    inp = _inputs_stub()  # driving_distance usable_for_badges=False by default
    result = qualify_badges(inp, badges, {"driving_distance": 90})
    assert not any(b["badge_id"] == "bomber" for b in result)


# ── precision_driver badge ────────────────────────────────────────────────────

def test_precision_driver_uses_acc_mean_not_decomp():
    badges = _load_policy()
    inp = _inputs_stub(
        driving_accuracy={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "acc_mean", "window": "L24", "value": 0.12, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"driving_accuracy": 85})
    assert any(b["badge_id"] == "precision_driver" for b in result)
    pd_badge = next(b for b in result if b["badge_id"] == "precision_driver")
    assert "acc_mean" in pd_badge["qualification_reason"]


# ── putter badge ──────────────────────────────────────────────────────────────

def test_putter_uses_putt_mean():
    badges = _load_policy()
    inp = _inputs_stub(
        putting={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "putt_mean", "window": "L24", "value": 0.55, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"putting": 88})
    assert any(b["badge_id"] == "putter" for b in result)
    putter_b = next(b for b in result if b["badge_id"] == "putter")
    assert "putt_mean" in putter_b["qualification_reason"]


# ── hot_streak badge ──────────────────────────────────────────────────────────

def test_hot_streak_qualifies_with_sufficient_sample():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": 0.80, "l6_total_mean": 2.0, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"recent_form": 85})
    assert any(b["badge_id"] == "hot_streak" for b in result)


def test_hot_streak_rejected_insufficient_l6_rounds():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": None, "l6_total_mean": 2.0, "l6_rounds": 4, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "INSUFFICIENT_SAMPLE", "usable_for_badges": False},
    )
    result = qualify_badges(inp, badges, {"recent_form": 90})
    assert not any(b["badge_id"] == "hot_streak" for b in result)


def test_hot_streak_rejected_insufficient_l24_rounds():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": None, "l6_total_mean": 2.0, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 8, "availability": "INSUFFICIENT_SAMPLE", "usable_for_badges": False},
    )
    result = qualify_badges(inp, badges, {"recent_form": 90})
    assert not any(b["badge_id"] == "hot_streak" for b in result)


# ── par5_predator never emits ─────────────────────────────────────────────────

def test_par5_predator_never_emitted():
    badges = _load_policy()
    # Even with a high percentile, par5_predator must never emit — no source column
    inp = _inputs_stub()
    result = qualify_badges(inp, badges, {"par5_scoring": 95})
    assert not any(b["badge_id"] == "par5_predator" for b in result)


# ── qualification_reason must be source-backed ────────────────────────────────

def test_all_emitted_badges_have_source_backed_reasons():
    badges = _load_policy()
    inp = _inputs_stub(
        course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {})
    for b in result:
        assert len(b["qualification_reason"]) > 10, f"badge {b['badge_id']} has thin reason"
        assert "source" in b["qualification_reason"].lower() or any(
            kw in b["qualification_reason"] for kw in ["detroit", "Detroit", ".csv", "L24", "L6", "12m"]
        ), f"badge {b['badge_id']} reason lacks source provenance"


# ── compute_badge_percentiles ─────────────────────────────────────────────────

def test_top_player_gets_highest_percentile():
    players = [
        {"trait_approach_raw": 2.0, "trait_long_iron_raw": 2.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": True},
                                "trait_long_iron_raw": {"usable_for_badges": True}}},
        {"trait_approach_raw": 1.0, "trait_long_iron_raw": 1.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": True},
                                "trait_long_iron_raw": {"usable_for_badges": True}}},
        {"trait_approach_raw": 0.0, "trait_long_iron_raw": 0.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": False},
                                "trait_long_iron_raw": {"usable_for_badges": False}}},
    ]
    badge_inputs = [
        {"approach_play": {"value": 2.0, "usable_for_badges": True}, "iron_play": {"value": 2.0, "usable_for_badges": True},
         "driving_distance": {"value": None, "usable_for_badges": False}, "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False}, "recent_form": {"value": None, "usable_for_badges": False}},
        {"approach_play": {"value": 1.0, "usable_for_badges": True}, "iron_play": {"value": 1.0, "usable_for_badges": True},
         "driving_distance": {"value": None, "usable_for_badges": False}, "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False}, "recent_form": {"value": None, "usable_for_badges": False}},
        {"approach_play": {"value": 0.0, "usable_for_badges": False}, "iron_play": {"value": 0.0, "usable_for_badges": False},
         "driving_distance": {"value": None, "usable_for_badges": False}, "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False}, "recent_form": {"value": None, "usable_for_badges": False}},
    ]
    result = compute_badge_percentiles(players, badge_inputs)
    assert result[0].get("approach_play", 0) >= result[1].get("approach_play", 0)
    assert "approach_play" not in result[2]
```

- [ ] **Step A10: Run tests — all must pass**

```bash
pytest tests/test_badge_qualification.py -v
```

Expected: all tests pass with the new functions implemented.

- [ ] **Step A11: Run the pipeline**

```bash
python events/2026_rocket_classic/engine/enrich_cards.py
```

Verify: output payload has `badges[]` on scored players; `total_badges > 0`.

- [ ] **Step A12: Commit**

```bash
git add events/2026_rocket_classic/engine/enrich_cards.py tests/test_badge_qualification.py
git commit -m "feat(rocket-2026): full badge emission pipeline — 7 badges, normalized inputs, provenance"
```

---

## Task B — Release Gate Validator + Tests

**Files:**
- Create: `events/2026_rocket_classic/output/validate_badge_emission.py`
- Create: `tests/test_validate_badge_emission.py`
- Modify: `events/2026_rocket_classic/output/preflight_check.py` (update hash + schema version)

**Interfaces:**
- Consumes: rebuilt payload at `deploy/data/2026_rocket_classic_event_payload.json`
- Produces: `validate_payload(payload, policy_badges) -> list[str]` (errors); `main()` exits 0/1

### Implementation Steps

- [ ] **Step B1: Write failing tests — Create `tests/test_validate_badge_emission.py`**

```python
"""Tests for the badge emission release gate validator."""
import importlib.util, json
from pathlib import Path
import pytest

_VAL_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_rocket_classic" / "output" / "validate_badge_emission.py"
)
_spec = importlib.util.spec_from_file_location("badge_validator", _VAL_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
validate_payload = _mod.validate_payload

_POLICY = [
    {"badge_id": "debut",       "label": "Debut",       "display_order": 8,
     "required_trait_ids": [], "threshold": {"venue_starts_max": 0}, "exclusions": []},
    {"badge_id": "iron_surgeon","label": "Iron Surgeon","display_order": 1,
     "required_trait_ids": ["approach_play","iron_play"],
     "threshold": {"field_percentile_min": 80}, "exclusions": []},
]

def _player(pid="1", depth="FULL", badges=None):
    return {"player_id": pid, "data_depth": depth,
            "badges": badges if badges is not None else [
                {"badge_id": "debut", "qualification_reason": "No prior starts. (source: detroit_golf_club_CH.csv)"}
            ]}

def _payload(players=None):
    return {"players": players or [_player()]}

# Gate 1
def test_g1_zero_badges_across_scored_players_fails():
    errors = validate_payload(_payload([_player(badges=[])]), _POLICY)
    assert any("[G1]" in e for e in errors)

def test_g1_does_not_fire_for_unscored_only():
    errors = validate_payload(_payload([_player(depth="UNSCORED", badges=[])]), _POLICY)
    assert not any("[G1]" in e for e in errors)

def test_g1_passes_when_some_badge_present():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G1]" in e for e in errors)

# Gate 2
def test_g2_missing_badges_field_fails():
    p = {"player_id": "1", "data_depth": "FULL"}
    errors = validate_payload(_payload([p]), _POLICY)
    assert any("[G2]" in e for e in errors)

def test_g2_badges_not_list_fails():
    errors = validate_payload(_payload([_player(badges="debut")]), _POLICY)
    assert any("[G2]" in e for e in errors)

def test_g2_malformed_entry_no_reason_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"debut"}])]), _POLICY)
    assert any("[G4]" in e for e in errors)   # missing reason = G4

# Gate 3
def test_g3_unknown_badge_id_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"invented","qualification_reason":"x"}])]), _POLICY)
    assert any("[G3]" in e for e in errors)

def test_g3_known_badge_id_passes():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G3]" in e for e in errors)

# Gate 4
def test_g4_empty_reason_fails():
    errors = validate_payload(_payload([_player(badges=[{"badge_id":"debut","qualification_reason":""}])]), _POLICY)
    assert any("[G4]" in e for e in errors)

# Gate 5
def test_g5_duplicate_policy_id_fails():
    dup = _POLICY + [_POLICY[0]]
    errors = validate_payload(_payload([_player()]), dup)
    assert any("[G5]" in e for e in errors)

def test_g5_unique_policy_passes():
    errors = validate_payload(_payload([_player()]), _POLICY)
    assert not any("[G5]" in e for e in errors)
```

- [ ] **Step B2: Implement the validator — Create `events/2026_rocket_classic/output/validate_badge_emission.py`**

```python
"""
validate_badge_emission.py
Release gate: verifies badge emission integrity in the Rocket Classic event artifact.
Exits 0 on full pass, 1 on any failure.
Run: python events/2026_rocket_classic/output/validate_badge_emission.py
"""
import json, sys
from collections import Counter
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent.parent.parent.parent
PAYLOAD_PATH = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_event_payload.json"
POLICY_PATH  = REPO_ROOT / "config/badge_policy.v1.json"


def validate_payload(payload: dict, policy_badges: list[dict]) -> list[str]:
    errors: list[str] = []

    # G5: policy badge_id uniqueness
    policy_ids = [b["badge_id"] for b in policy_badges]
    for bid, cnt in Counter(policy_ids).items():
        if cnt > 1:
            errors.append(f"[G5] Duplicate badge_id in policy: '{bid}' appears {cnt} times")
    valid_ids = set(policy_ids)

    players = payload.get("players", [])
    scored  = [p for p in players if p.get("data_depth") != "UNSCORED"]

    for p in scored:
        pid = p.get("player_id", "?")
        if "badges" not in p:
            errors.append(f"[G2] Player {pid}: 'badges' field missing")
            continue
        if not isinstance(p["badges"], list):
            errors.append(f"[G2] Player {pid}: 'badges' is not a list (got {type(p['badges']).__name__})")
            continue
        for entry in p["badges"]:
            if not isinstance(entry, dict):
                errors.append(f"[G2] Player {pid}: badge entry is not a dict: {entry!r}")
                continue
            bid    = entry.get("badge_id", "")
            reason = entry.get("qualification_reason", None)
            if not bid:
                errors.append(f"[G2] Player {pid}: badge entry missing badge_id")
            elif bid not in valid_ids:
                errors.append(f"[G3] Player {pid}: unknown badge_id '{bid}' not in policy")
            if reason is None or not str(reason).strip():
                errors.append(f"[G4] Player {pid}: badge '{bid}' has empty/missing qualification_reason")

    if scored:
        total = sum(len(p["badges"]) for p in scored if isinstance(p.get("badges"), list))
        if total == 0:
            errors.append(
                f"[G1] {len(scored)} scored player(s) but zero total badges emitted — "
                "badge qualification is required before release"
            )

    return errors


def main() -> None:
    print("=== Badge Emission Release Gate ===\n")

    for label, path in [("Payload", PAYLOAD_PATH), ("Policy", POLICY_PATH)]:
        if not path.exists():
            print(f"FAIL [G6]: {label} not found: {path}")
            sys.exit(1)

    try:
        payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL [G6]: Cannot parse payload: {e}"); sys.exit(1)

    try:
        policy_badges = json.loads(POLICY_PATH.read_text(encoding="utf-8")).get("badges", [])
    except Exception as e:
        print(f"FAIL [G6]: Cannot parse policy: {e}"); sys.exit(1)

    errors = validate_payload(payload, policy_badges)

    if errors:
        print(f"FAILED ({len(errors)} error(s)):\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    scored = [p for p in payload.get("players", []) if p.get("data_depth") != "UNSCORED"]
    total  = sum(len(p.get("badges", [])) for p in scored)
    print(f"PASSED — {total} badge(s) emitted across {len(scored)} scored players")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step B3: Run tests — all must pass**

```bash
pytest tests/test_validate_badge_emission.py -v
```

- [ ] **Step B4: Run the gate against the rebuilt artifact**

```bash
python events/2026_rocket_classic/output/validate_badge_emission.py
```

Expected: PASSED.

- [ ] **Step B5: Update preflight_check.py** — compute new hash, update `EXPECTED_HASH` and schema version check:

```python
# Compute new hash:
python -c "
import hashlib, pathlib
h = hashlib.sha256(pathlib.Path('events/2026_rocket_classic/deploy/data/2026_rocket_classic_event_payload.json').read_bytes()).hexdigest()
print(h)
"
# Then update preflight_check.py line 17: EXPECTED_HASH = "<new_hash>"
# And update line 53: if sv == "rocket-classic-v1.3":
```

- [ ] **Step B6: Run preflight**

```bash
python events/2026_rocket_classic/output/preflight_check.py
```

Expected: PREFLIGHT: PASSED.

- [ ] **Step B7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step B8: Commit**

```bash
git add events/2026_rocket_classic/output/validate_badge_emission.py \
        tests/test_validate_badge_emission.py \
        events/2026_rocket_classic/output/preflight_check.py
git commit -m "feat(rocket-2026): badge release gate, tests, preflight update"
```

---

## Task C — Harness State/Search/UI Consumption

**Files:**
- Modify: `events/2026_rocket_classic/deploy/fixture_harness.js`
- Modify: `events/2026_rocket_classic/deploy/fixture_harness.css`

**Interfaces consumed:**
- `p.badges` from rebuilt event_payload — `[{badge_id, qualification_reason}]`
- `S.badgePolicy` — loaded from `config/badge_policy.v1.json`
- `S.activeFilters` — add `query: ""`

### Implementation Steps

- [ ] **Step C1: Add `query: ""` to `S.activeFilters`** (around line 18)

```js
activeFilters: { tier: "All", badges: [], traitRanges: {}, query: "" },
```

- [ ] **Step C2: Add name query filter to `filteredFixtures()`** (before `return true`)

```js
if (S.activeFilters.query) {
  const name = (inp.player.display_name || "").toLowerCase();
  if (!name.includes(S.activeFilters.query)) return false;
}
```

- [ ] **Step C3: Enable badge filter in `filteredFixtures()`** — replace skipped comment

```js
if (S.activeFilters.badges.length > 0) {
  const playerBadgeIds = (inp.badges || []).map((b) => b.badge_id);
  if (!S.activeFilters.badges.some((bid) => playerBadgeIds.includes(bid))) return false;
}
```

- [ ] **Step C4: Replace DOM-hiding search handler in `bindGlobalEvents()`**

```js
// Remove:
//   document.querySelectorAll(".roster-row").forEach(row => { row.style.display = ...; });
// Replace with:
const searchInput = document.getElementById("player-search");
if (searchInput) {
  searchInput.addEventListener("input", () => {
    S.activeFilters.query = searchInput.value.trim().toLowerCase();
    renderRoster();
  });
}
```

- [ ] **Step C5: Add drawer close guard in `renderRoster()`** (after `const visible = filteredFixtures()`, before `tbody.innerHTML`)

```js
if (S.openPlayerId) {
  if (!visible.some((f) => f.input.player.player_id === S.openPlayerId)) {
    closeDrawer();
  }
}
```

- [ ] **Step C6: Clear query in `resetFilters()`**

```js
S.activeFilters.query = "";
const searchEl = document.getElementById("player-search");
if (searchEl) searchEl.value = "";
```

Also uncheck badge filter checkboxes:
```js
document.querySelectorAll(".badge-filter-checkbox").forEach((cb) => { cb.checked = false; });
```

- [ ] **Step C7: Add `validateEmittedBadges()` helper before `playerToFixture()`**

```js
// Browser renders artifact-emitted data only — no client-side badge inference.
function validateEmittedBadges(rawBadges, badgePolicy) {
  if (!Array.isArray(rawBadges)) return [];
  const known = new Set((badgePolicy?.badges || []).map((b) => b.badge_id));
  return rawBadges.filter((b) => {
    if (!b || typeof b.badge_id !== "string") return false;
    if (!known.has(b.badge_id)) {
      console.error(`Badge validation error: unknown badge_id '${b.badge_id}' — omitting`);
      return false;
    }
    return true;
  });
}
```

- [ ] **Step C8: Update `playerToFixture()` — consume `p.badges`** (replace `badges: []` line)

```js
badges: validateEmittedBadges(p.badges || [], S.badgePolicy),
```

- [ ] **Step C9: Update `renderBadgeFilters()` — detect badge presence**

```js
function renderBadgeFilters() {
  const presentIds = new Set();
  S.fixtures.forEach((f) => { (f.input.badges || []).forEach((b) => presentIds.add(b.badge_id)); });

  const DISABLED_HTML = `...`; // unchanged disabled HTML block

  if (presentIds.size === 0) {
    ["badge-filter-list","badge-filter-list-popover","badge-filter-list-overlay"].forEach((id) => {
      const el = document.getElementById(id); if (el) el.innerHTML = DISABLED_HTML;
    });
    return;
  }

  const badgeDefs = (S.badgePolicy?.badges || []).filter((b) => presentIds.has(b.badge_id));
  const checkboxHtml = badgeDefs.map((def) => `
    <label class="badge-filter-item">
      <input type="checkbox" class="badge-filter-checkbox" data-badge-id="${esc(def.badge_id)}" />
      <span class="badge-filter-label">${esc(def.icon || "")} ${esc(def.label)}</span>
    </label>
  `).join("");

  ["badge-filter-list","badge-filter-list-popover","badge-filter-list-overlay"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = checkboxHtml;
    el.querySelectorAll(".badge-filter-checkbox").forEach((cb) => {
      cb.addEventListener("change", () => {
        S.activeFilters.badges = [...document.querySelectorAll(".badge-filter-checkbox:checked")]
          .map((c) => c.dataset.badgeId);
        renderRoster();
      });
    });
  });
}
```

- [ ] **Step C10: Add badge filter CSS to `fixture_harness.css`**

```css
/* ── Badge filter checkboxes ─────────────────────────────────────────────── */
.badge-filter-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--color-text-muted);
  cursor: pointer; padding: 3px 0;
}
.badge-filter-item:hover { color: var(--color-text); }
.badge-filter-checkbox {
  accent-color: var(--color-accent); width: 13px; height: 13px; cursor: pointer;
}
```

- [ ] **Step C11: Manual verification via local server**

- Search "scheff" → only Scheffler
- Clear → full roster restored
- Tier T1 + search "m" → only T1 players whose name contains m
- Check Iron Surgeon → only players with that badge
- Open Scheffler's drawer → type "z" in search (no T1 players with z) → drawer closes
- Reset Filters → all clear, full roster, drawer closed

- [ ] **Step C12: Commit**

```bash
git add events/2026_rocket_classic/deploy/fixture_harness.js events/2026_rocket_classic/deploy/fixture_harness.css
git commit -m "feat(rocket-2026): state-driven search, badge filters enabled, emitted badge consumption"
```

---

## Remaining Concrete Blocker

| Badge | Concrete Missing Input |
|-------|----------------------|
| `par5_predator` | No par-5 SG or par-5 scoring column exists in any supplied source file. Cannot emit without a `pga_field_par5_scoring.csv` or equivalent. |
