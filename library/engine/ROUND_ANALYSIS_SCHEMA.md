# Round Analysis Schema — VenueDNA Tier Engine
Schema version: 1.1 · Last updated: 2026-06-25

This document defines the canonical structure of `rN_analysis.json` files produced by
`build_round_analysis.py`. All round files (r1 through r4) use identical structure.

---

## Top-Level Structure

```json
{
  "schema_version":         "1.1",
  "generated_at":           "2026-06-25",
  "round":                  2,
  "event_slug":             "2026_travelers_championship",
  "metadata":               { ... },
  "round_sources":          [ ... ],
  "course_insights_loaded": true,
  "enrichment_summary":     { ... } | null,
  "live_lean_notes":        { ... },
  "match_summary":          { ... },
  "model_performance":      { ... },
  "sg_leader_averages":     { ... },
  "trait_audit":            { ... },
  "risers":                 [ ... ],
  "slippage":               [ ... ],
  "weekend_risers":         [ ... ],
  "slippage_risk":          [ ... ],
  "leaderboard_snapshot":   [ ... ],
  "dimension_leaders":      { ... },
  "course_stats":           [ ... ],
  "easiest_holes":          [ ... ],
  "hardest_holes":          [ ... ]
}
```

---

## Required vs Optional Fields

| Field | Required | Notes |
|---|---|---|
| `schema_version` | Yes | Always "1.1" |
| `generated_at` | Yes | ISO date string |
| `round` | Yes | Integer 1-4 |
| `event_slug` | Yes | Lowercase underscore slug |
| `metadata` | Yes | See below |
| `round_sources` | Yes | Array of file names used |
| `course_insights_loaded` | Yes | Boolean |
| `enrichment_summary` | No | Null if no course_insights CSV |
| `live_lean_notes` | Yes | See below |
| `match_summary` | Yes | See below |
| `model_performance` | Yes | See below |
| `sg_leader_averages` | Yes | Top10, Top18, full field SG avgs |
| `trait_audit` | Yes | One entry per trait |
| `risers` | Yes | Top 12 positive rank delta players |
| `slippage` | Yes | Top 10 negative rank delta players |
| `weekend_risers` | Yes | Course-fit-validated risers (may be empty array) |
| `slippage_risk` | Yes | Fragility-flagged players (may be empty array) |
| `leaderboard_snapshot` | Yes | All round players with SG breakdown |
| `dimension_leaders` | Yes | Top 5 per SG category |
| `course_stats` | Yes | Empty array if course_stats CSV not loaded |
| `easiest_holes` | Yes | Empty array if no course stats |
| `hardest_holes` | Yes | Empty array if no course stats |

---

## metadata

```json
"metadata": {
  "event_name":  "2026 Travelers Championship",
  "course_name": "TPC River Highlands",
  "par":         70,
  "round_label": "Round 2",
  "is_final":    false
}
```

`round_label` is "Round N" for rounds 1-3 and "Final Round" for round 4.
`is_final` controls leandown and Live Lean header text in the dashboard.

---

## match_summary

```json
"match_summary": {
  "matched":         68,
  "total_r1":        72,
  "unmatched":       ["Player Name"],
  "match_rate_pct":  94.4
}
```

Note: `total_r1` is a canonical field name inherited from the R1 schema. It represents
the total number of players in the round's leaderboard data regardless of round number.

---

## model_performance

```json
"model_performance": {
  "spearman_rho": 0.312,
  "groups": {
    "pt_top10":  { "n": 10, "avg_r1_pos": 14.2, "avg_r1_score": -4.1, "in_r1_top10": 4, "in_r1_top20": 7, "in_r1_top30": 8 },
    "pt_top20":  { ... },
    "tier1":     { ... },
    "tier2":     { ... },
    "tier1_2":   { ... },
    "all_field": { ... }
  }
}
```

Field names `avg_r1_pos`, `in_r1_top10`, etc. are canonical; they hold round N data
regardless of which round was built. Maintained for app.js backwards compatibility.

---

## trait_audit

One entry per trait key. Ten traits total.

```json
"trait_audit": {
  "app_wedge": {
    "venue_weight":    0.22,
    "top10_trait_avg": 74.3,
    "field_trait_avg": 66.1,
    "trait_delta":     8.2,
    "sg_proxy":        "sg_app",
    "sg_top10":        0.812,
    "sg_field":        0.043,
    "sg_delta":        0.769,
    "signal":          "validated",
    "sample_n_top10":  9,
    "sample_n_field":  61,
    "source_confidence": "proxy-confirmed",
    "enrichment":      { ... }
  }
}
```

### signal values

| Value | Meaning |
|---|---|
| `validated` | Trait delta >= 6 pts; top leaders were clearly stronger in this trait |
| `mixed` | Delta 2-6 pts; directional support but not decisive |
| `neutral` | Delta -3 to 2 pts; no clear signal |
| `weak` | Delta < -3 pts; leaders were actually weaker in this trait |
| `not_testable` | Insufficient data to compute delta |

### source_confidence values

| Value | Meaning |
|---|---|
| `direct` | Enrichment field is a 1:1 proxy for this trait (e.g., Scrambling% → ARG) |
| `proxy-confirmed` | SG dimension AND enrichment both support the signal |
| `weak-proxy` | Directional only — single proxy or limited enrichment |
| `not-testable` | Insufficient data to confirm or deny |

### trait_audit.enrichment

```json
"enrichment": {
  "available":         true,
  "source":            "round1_course_insights.csv (DataGolf proxy — not PGAT official SG)",
  "proxy_fields":      ["fairway_prox", "gir"],
  "primary_field":     "fairway_prox",
  "direction":         "lower_better",
  "top10_primary":     147.3,
  "field_primary":     168.2,
  "delta_primary":     20.9,
  "enrichment_signal": "confirmed",
  "upgraded_signal":   "validated",
  "enrichment_note":   "fairway_prox: top10=12.3in vs field=14.0in (closer by 1.7in)",
  "n_top10_ci":        9,
  "n_field_ci":        54
}
```

If enrichment is unavailable: `{ "available": false, "reason": "..." }`

#### enrichment_signal values

| Value | Meaning |
|---|---|
| `upgraded` | Strong enrichment signal that upgraded a weak/neutral/mixed trait to a higher level |
| `confirmed` | Enrichment corroborates the existing signal |
| `neutral` | Delta below significance threshold |
| `contradicted` | Enrichment data contradicts the SG-based signal |
| `not_available` | No enrichment CSV loaded |

---

## live_lean_notes

```json
"live_lean_notes": {
  "round":       1,
  "next_round":  2,
  "lean_up_traits": [
    { "trait": "app_wedge", "delta": 8.2, "confidence": "proxy-confirmed", "enr_signal": "confirmed" }
  ],
  "lean_down_traits": [
    { "trait": "ott_distance", "delta": -4.1 }
  ],
  "putt_caution": true,
  "putt_outliers": [
    { "player": "Ben Griffin", "sg_putt": 3.124, "sg_app": -0.211 }
  ],
  "watch_next_round": [
    {
      "player": "Ben Griffin",
      "pos_str": "T3",
      "score": -6,
      "sg_putt": 3.124,
      "sg_app": -0.211,
      "note": "putting-driven round (+3.12 putting vs -0.21 APP) — regression likely",
      "flag_type": "slippage"
    }
  ],
  "rho_note": "R1 rank correlation rho=0.312 — model-field separation expected to sharpen by R2."
}
```

`next_round` is null for the Final round (round 4). The dashboard uses this to
switch the Live Lean header from "ROUND N+1 LIVE LEAN" to "FINAL ROUND RECAP".

`flag_type` is `"slippage"` for regression candidates or `"sustainable"` for
approach-backed leaders not on the slippage list.

---

## Leaderboard record (in leaderboard_snapshot, weekend_risers, slippage_risk)

```json
{
  "r1_name":    "Scottie Scheffler",
  "norm_name":  "Scheffler, Scottie",
  "r1_pos":     1,
  "r1_pos_str": "1",
  "r1_score":   -8,
  "pt_rank":    1,
  "pt_tier":    1,
  "pt_vts":     91.4,
  "pt_flags":   "",
  "pt_driver":  "approach elite",
  "rank_delta": 0,
  "sg_ott":     0.412,
  "sg_app":     1.234,
  "sg_arg":     0.187,
  "sg_putt":    0.312,
  "sg_tot":     2.145
}
```

Note: `r1_name`, `r1_pos`, `r1_score` are canonical field names across all rounds (R1-R4).
The "r1" prefix is a naming convention, not a round indicator.

Weekend riser records additionally contain: `thesis_score` (int), `thesis_note` (string)
Slippage risk records additionally contain: `risk_flags` (array of strings)

---

## Cumulative Learning Schema (cumulative_learning.json)

```json
{
  "schema_version":   "1.0",
  "event_slug":       "2026_travelers_championship",
  "created_at":       "2026-06-25",
  "last_updated":     "2026-06-26",
  "rounds_completed": 2,
  "per_round": {
    "1": { "round": 1, "generated_at": "...", "spearman_rho": 0.312, "trait_signals": {...}, "model_hits": {...}, "risers": [...], "slippage": [...] },
    "2": { ... }
  },
  "cumulative_signals": {
    "app_wedge": {
      "rounds_observed":      [1, 2],
      "signal_history":       ["validated", "validated"],
      "confidence_history":   ["proxy-confirmed", "proxy-confirmed"],
      "delta_history":        [8.2, 7.1],
      "consensus":            "validated",
      "consensus_confidence": "proxy-confirmed"
    }
  }
}
```

`consensus` is the most recent round's signal. `consensus_confidence` is the most
recent round's source_confidence. As rounds accumulate, consistent signals across
multiple rounds increase confidence in the venue trait model.

---

## Trait Keys

| Key | Label | Venue Weight (Travelers) |
|---|---|---|
| `app_wedge` | APP: Wedge/100 | 22% |
| `app_100_150` | APP: 100-150 | 12% |
| `app_150_200` | APP: 150-200 | 6% |
| `ott_accuracy` | OTT: Accuracy | 14% |
| `ott_distance` | OTT: Distance | 5% |
| `putt_short_conv` | PUTT: Short Conv | 16% |
| `putt_lag` | PUTT: Lag | 10% |
| `arg_rough` | ARG: Rough | 7% |
| `arg_bunker` | ARG: Bunker | 5% |
| `par5_scoring` | Par 5 Scoring | 3% |

---

## Build Command Reference

```bash
# Round 1 (Travelers legacy)
python engine/build_r1_analysis.py

# Rounds 2-4
python engine/build_round_analysis.py --round 2
python engine/build_round_analysis.py --round 3
python engine/build_round_analysis.py --round 4   # Final

# Input directory convention for R2+
output/round{N}/round{N}_leaderboard.csv
output/round{N}/round{N}_player_strokes_gained.csv
output/round{N}/round{N}_course_stats.csv          (optional)
output/round{N}/round{N}_course_insights.csv       (optional)
```
