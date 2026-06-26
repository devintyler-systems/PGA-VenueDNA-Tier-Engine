"""
VenueDNA Build-Time Trait QA Module
Event: 2026 Travelers Championship @ TPC River Highlands

PURPOSE
-------
Validates trait score data in the generated event_payload.json before the deploy
package is used by analysts.  Catches the zero-as-sentinel problem (and other
data quality issues) at build time rather than silently propagating bad scores
into the UI.

ZERO-AS-SENTINEL RULE (critical)
---------------------------------
A trait score of exactly 0.0 is NEVER a valid PGA Tour percentile result.
The Tour's percentile distributions always yield at least a fractional value for
any measured golfer.  When a score of 0 appears in the pipeline output it means
the source data cell was empty / unmeasured and was silently filled by a default
(often a pandas fillna(0) in the upstream aggregation step).

Zero-sentinels must be classified as MISSING, not as "0th-percentile performance",
and must go through the imputation fallback chain before the UI receives them.
Treating them as real scores inflates confidence (the field avg of ~50 would now
compete against a false 0) and suppresses VTS for players like Sungjae Im who
had 3 high-weight zeros (combined 0.40 weight) in the initial build.

CLASSIFICATION TAXONOMY (8 categories)
----------------------------------------
  observed_valid        — numeric, in (0, 100], passes all checks
  invalid_zero_sentinel — exactly 0.0 (zero-as-sentinel rule violation)
  invalid_nan           — NaN, null, blank, or unparseable
  extreme_low_flag      — in (0, 2.0): valid non-zero but borderline; flagged for
                          human review; NOT auto-treated as missing
  imputed_from_historical — resolved via player historical baseline (stub in v1)
  imputed_from_tier     — resolved via same-tier cohort average
  imputed_from_field    — resolved via full-field average
  unresolved_unknown    — no valid imputation found; UI must display unknown badge

OUTPUTS
-------
  output/{SLUG}_qa_report.json    — full structured report (archive / CI use)
  output/{SLUG}_qa_records.csv    — per-(player × trait) row for spreadsheet audit
  deploy/data/qa_report.json      — UI-facing summary (consumed by app.js)

Run this script after the main pipeline completes and before any deployment step.
"""

import csv
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(r"C:\PGA_VenueDNA\events\2026_TravelersChampionship")
BASE_OUT = ROOT / "output"
BASE_DEP = ROOT / "deploy"
SLUG     = "2026_travelers_championship"

PAYLOAD_PATH = BASE_DEP / "data" / "event_payload.json"

# ── QA Configuration ──────────────────────────────────────────────────────────
# Warning thresholds — adjust to tighten or relax QA gates
QA_CONFIG = dict(
    # Fraction of players missing a trait before we warn for that trait
    per_trait_warning_threshold = 0.05,          # 5%
    # Flag if any single player's combined missing_trait_weight exceeds this
    player_missing_weight_warning = 0.20,        # 20%
    # Flag if tournament-wide weighted missingness rate exceeds this
    tournament_weighted_miss_warning = 0.03,     # 3% (weighted by venue importance)
    # Scores below this (but > 0) are flagged as "extreme low" for human review
    extreme_low_threshold = 2.0,
    # Minimum players per tier to compute a reliable tier average for imputation
    min_tier_size_for_imputation = 3,
)

# Venue trait weight matrix (must match VENUE_WEIGHTS in the main pipeline)
VENUE_WEIGHTS = dict(
    app_wedge       = 0.22,
    app_100_150     = 0.12,
    app_150_200     = 0.06,
    ott_accuracy    = 0.14,
    ott_distance    = 0.05,
    putt_short_conv = 0.16,
    putt_lag        = 0.10,
    arg_rough       = 0.07,
    arg_bunker      = 0.05,
    par5_scoring    = 0.03,
)
assert abs(sum(VENUE_WEIGHTS.values()) - 1.0) < 1e-6, "Venue weights must sum to 1.00"

ALL_TRAIT_KEYS = list(VENUE_WEIGHTS.keys())


# ── Score classification helpers ──────────────────────────────────────────────

def classify_raw_score(score) -> tuple[str, float | None]:
    """
    Returns (status, cleaned_value) for a raw trait score.

    cleaned_value is None for any invalid or sentinel category — the caller
    must resolve it via imputation before writing to the final record.
    """
    if score is None:
        return "invalid_nan", None
    try:
        v = float(score)
    except (ValueError, TypeError):
        return "invalid_nan", None
    if v != v:  # NaN check
        return "invalid_nan", None
    if v == 0.0:
        return "invalid_zero_sentinel", None
    if v < QA_CONFIG["extreme_low_threshold"]:
        return "extreme_low_flag", v   # valid but flagged; not auto-imputed
    if v > 100.0:
        return "invalid_nan", None     # out-of-range
    return "observed_valid", v


def get_player_historical_baseline(player_name: str, trait_key: str):
    """
    Stub — returns None, causing imputation to fall through to tier average.
    Future: load player_baselines.json keyed by player_name → trait_key → score.
    """
    return None


# ── Core QA pass ─────────────────────────────────────────────────────────────

def run_qa(payload: dict) -> dict:
    """
    Main QA function.  Accepts the parsed event_payload dict; returns a
    structured QA report dict ready for JSON serialisation.
    """
    players_flat = []
    for tier in [1, 2, 3, 4, 5]:
        for p in payload.get("tiers", {}).get(f"tier_{tier}", []):
            players_flat.append(p)

    total_players = len(players_flat)

    # ── Step 1: initial classification of every (player × trait) pair ─────────
    #
    # We build a staging list of records.  Each record holds:
    #   player_name, name_key (derived), tier, rank, trait_key,
    #   raw_source_value, cleaned_value, status, trait_weight

    records = []
    for p in players_flat:
        name = p.get("player_name", "Unknown")
        # Derive name_key the same way the pipeline does
        parts = str(name).strip().split(", ", 1)
        nk = f"{parts[0].strip().upper()}_{parts[1].strip().upper()}" if len(parts) == 2 else name.upper()

        trait_map_raw = {ts["key"]: ts for ts in p.get("trait_scores", [])}

        for tk in ALL_TRAIT_KEYS:
            ts = trait_map_raw.get(tk)
            raw_val = ts["score"] if ts else None
            status, cleaned = classify_raw_score(raw_val)
            records.append({
                "player_name": name,
                "name_key": nk,
                "tier": p.get("tier"),
                "rank": p.get("rank"),
                "trait_key": tk,
                "trait_weight": VENUE_WEIGHTS[tk],
                "raw_source_value": raw_val,
                "cleaned_value": cleaned,
                "status": status,
                "initial_status": status,   # preserved before imputation overwrites status
                "imputation_source": None,
                "imputed_value": None,
                "final_value": cleaned,   # updated after imputation
            })

    # ── Step 2: build tier averages and field average for imputation ───────────

    # Collect observed_valid and extreme_low scores (both are usable values)
    def _usable(r):
        return r["status"] in ("observed_valid", "extreme_low_flag")

    tier_avgs: dict[str, dict[str, float]] = {}
    for tier in [1, 2, 3, 4, 5]:
        for tk in ALL_TRAIT_KEYS:
            vals = [r["cleaned_value"] for r in records
                    if r["tier"] == tier and r["trait_key"] == tk and _usable(r)
                    and r["cleaned_value"] is not None]
            if len(vals) >= QA_CONFIG["min_tier_size_for_imputation"]:
                tier_avgs.setdefault(tier, {})[tk] = sum(vals) / len(vals)

    field_avgs: dict[str, float] = {}
    for tk in ALL_TRAIT_KEYS:
        vals = [r["cleaned_value"] for r in records
                if r["trait_key"] == tk and _usable(r)
                and r["cleaned_value"] is not None]
        if vals:
            field_avgs[tk] = sum(vals) / len(vals)

    # ── Step 3: imputation fallback for invalid / sentinel scores ─────────────

    needs_imputation_statuses = {"invalid_zero_sentinel", "invalid_nan"}

    for rec in records:
        if rec["status"] not in needs_imputation_statuses:
            rec["final_value"] = rec["cleaned_value"]
            continue

        tk = rec["trait_key"]
        pname = rec["player_name"]
        tier = rec["tier"]

        # Fallback 1: player historical baseline (stub)
        hist = get_player_historical_baseline(pname, tk)
        if hist is not None:
            rec["status"] = "imputed_from_historical"
            rec["imputation_source"] = "historical"
            rec["imputed_value"] = round(hist, 2)
            rec["final_value"] = rec["imputed_value"]
            continue

        # Fallback 2: tier cohort average
        tier_val = tier_avgs.get(tier, {}).get(tk)
        if tier_val is not None:
            rec["status"] = "imputed_from_tier"
            rec["imputation_source"] = f"tier_{tier}_avg"
            rec["imputed_value"] = round(tier_val, 2)
            rec["final_value"] = rec["imputed_value"]
            continue

        # Fallback 3: field average
        field_val = field_avgs.get(tk)
        if field_val is not None:
            rec["status"] = "imputed_from_field"
            rec["imputation_source"] = "field_avg"
            rec["imputed_value"] = round(field_val, 2)
            rec["final_value"] = rec["imputed_value"]
            continue

        # Unresolved
        rec["status"] = "unresolved_unknown"
        rec["imputation_source"] = None
        rec["imputed_value"] = None
        rec["final_value"] = None

    # ── Step 4: per-player summary (missing_trait_weight per player) ──────────

    player_summaries: dict[str, dict] = {}
    for rec in records:
        pname = rec["player_name"]
        if pname not in player_summaries:
            player_summaries[pname] = {
                "player_name": pname,
                "name_key": rec["name_key"],
                "tier": rec["tier"],
                "rank": rec["rank"],
                "issues": [],
                "missing_trait_weight": 0.0,
                "has_zero_sentinel": False,
                "has_nan": False,
                "has_unresolved": False,
                "imputed_traits": [],
                "unknown_traits": [],
                "extreme_low_traits": [],
            }
        ps = player_summaries[pname]
        s = rec["status"]
        w = rec["trait_weight"]

        init_s = rec["initial_status"]   # status before imputation overwrites it

        # Weight contribution: any trait that was originally invalid counts as missing
        if init_s in ("invalid_zero_sentinel", "invalid_nan"):
            ps["missing_trait_weight"] += w
            if init_s == "invalid_zero_sentinel":
                ps["has_zero_sentinel"] = True
                ps["issues"].append({"trait": rec["trait_key"], "status": init_s, "raw": rec["raw_source_value"]})
            else:
                ps["has_nan"] = True
                ps["issues"].append({"trait": rec["trait_key"], "status": init_s, "raw": rec["raw_source_value"]})

        if s in ("imputed_from_historical", "imputed_from_tier", "imputed_from_field"):
            ps["imputed_traits"].append({
                "trait": rec["trait_key"],
                "source": rec["imputation_source"],
                "imputed_value": rec["imputed_value"],
                "original_status": init_s,
            })

        if s == "unresolved_unknown":
            ps["has_unresolved"] = True
            ps["unknown_traits"].append(rec["trait_key"])
            ps["issues"].append({"trait": rec["trait_key"], "status": s, "raw": rec["raw_source_value"]})

        if s == "extreme_low_flag":
            ps["extreme_low_traits"].append({
                "trait": rec["trait_key"],
                "value": rec["cleaned_value"],
            })

    # Round missing_trait_weight
    for ps in player_summaries.values():
        ps["missing_trait_weight"] = round(ps["missing_trait_weight"], 4)

    # ── Step 5: tournament-level summary metrics ───────────────────────────────

    affected_players = [ps for ps in player_summaries.values()
                        if ps["has_zero_sentinel"] or ps["has_nan"] or ps["has_unresolved"]]

    # Use initial_status for counts of original data issues (pre-imputation)
    count_zero_sentinel = sum(1 for r in records if r["initial_status"] == "invalid_zero_sentinel")
    count_nan           = sum(1 for r in records if r["initial_status"] == "invalid_nan")
    # Post-imputation resolution counts
    count_imputed_hist  = sum(1 for r in records if r["status"] == "imputed_from_historical")
    count_imputed_tier  = sum(1 for r in records if r["status"] == "imputed_from_tier")
    count_imputed_field = sum(1 for r in records if r["status"] == "imputed_from_field")
    count_unknown       = sum(1 for r in records if r["status"] == "unresolved_unknown")
    count_extreme_low   = sum(1 for r in records if r["status"] == "extreme_low_flag")

    # Per-trait missing rate (zero-sentinel + nan + unresolved, before imputation)
    pre_impute_missing = {"invalid_zero_sentinel", "invalid_nan"}  # statuses that triggered imputation
    per_trait_missing_rate: dict[str, dict] = {}
    for tk in ALL_TRAIT_KEYS:
        trait_recs = [r for r in records if r["trait_key"] == tk]
        missing_n = sum(1 for r in trait_recs
                        if r["raw_source_value"] is None
                        or r["raw_source_value"] == 0.0
                        or (isinstance(r["raw_source_value"], float) and r["raw_source_value"] != r["raw_source_value"]))
        per_trait_missing_rate[tk] = {
            "missing_count": missing_n,
            "total": total_players,
            "missing_pct": round(missing_n / total_players * 100, 2) if total_players else 0,
            "venue_weight": VENUE_WEIGHTS[tk],
        }

    # Weighted missingness: sum over players of (missing_trait_weight) / total_players
    total_missing_wt = sum(ps["missing_trait_weight"] for ps in player_summaries.values())
    tournament_weighted_miss = round(total_missing_wt / total_players, 4) if total_players else 0

    # ── Step 6: warnings ──────────────────────────────────────────────────────

    warnings_list = []

    # Warning: any high-weight trait exceeds per-trait threshold
    top3_traits = sorted(VENUE_WEIGHTS.items(), key=lambda x: x[1], reverse=True)[:3]
    for tk, wt in top3_traits:
        miss_pct = per_trait_missing_rate[tk]["missing_pct"]
        if miss_pct > QA_CONFIG["per_trait_warning_threshold"] * 100:
            warnings_list.append({
                "level": "warning",
                "code": "HIGH_WEIGHT_TRAIT_MISSING",
                "message": (
                    f"Trait '{tk}' (venue weight {wt*100:.0f}%) has "
                    f"{miss_pct:.1f}% field missingness "
                    f"(threshold {QA_CONFIG['per_trait_warning_threshold']*100:.0f}%). "
                    f"Imputed values will affect ranking."
                ),
                "trait": tk,
                "missing_pct": miss_pct,
            })

    # Warning: any player exceeds missing_weight threshold
    heavy_miss_players = [
        ps for ps in player_summaries.values()
        if ps["missing_trait_weight"] >= QA_CONFIG["player_missing_weight_warning"]
    ]
    for ps in heavy_miss_players:
        warnings_list.append({
            "level": "warning",
            "code": "PLAYER_HIGH_MISSING_WEIGHT",
            "message": (
                f"{ps['player_name']} has {ps['missing_trait_weight']*100:.0f}% "
                f"combined missing trait weight — confidence penalty will apply."
            ),
            "player_name": ps["player_name"],
            "missing_trait_weight": ps["missing_trait_weight"],
        })

    # Warning: tournament-level weighted missingness
    if tournament_weighted_miss > QA_CONFIG["tournament_weighted_miss_warning"]:
        warnings_list.append({
            "level": "warning",
            "code": "TOURNAMENT_WEIGHTED_MISS_HIGH",
            "message": (
                f"Tournament weighted missingness rate is "
                f"{tournament_weighted_miss*100:.1f}% "
                f"(threshold {QA_CONFIG['tournament_weighted_miss_warning']*100:.0f}%). "
                f"Review data sourcing for affected traits."
            ),
            "weighted_miss_rate": tournament_weighted_miss,
        })

    # Info: extreme low flags (not auto-imputed, but noteworthy)
    extreme_players = [ps for ps in player_summaries.values() if ps["extreme_low_traits"]]
    for ps in extreme_players:
        for et in ps["extreme_low_traits"]:
            warnings_list.append({
                "level": "info",
                "code": "EXTREME_LOW_FLAG",
                "message": (
                    f"{ps['player_name']}: trait '{et['trait']}' = {et['value']:.2f} "
                    f"(< {QA_CONFIG['extreme_low_threshold']:.0f}) — "
                    f"valid non-zero but extreme floor; verify against source data."
                ),
                "player_name": ps["player_name"],
                "trait": et["trait"],
                "value": et["value"],
            })

    # Info: unresolved unknowns
    if count_unknown > 0:
        unknown_players = [ps for ps in player_summaries.values() if ps["has_unresolved"]]
        warnings_list.append({
            "level": "error",
            "code": "UNRESOLVED_UNKNOWN_TRAITS",
            "message": (
                f"{count_unknown} trait(s) across "
                f"{len(unknown_players)} player(s) could not be imputed. "
                f"UI will show UNKNOWN badge. Resolve source data gaps."
            ),
            "count": count_unknown,
            "affected_players": [ps["player_name"] for ps in unknown_players],
        })

    # ── Step 7: assemble report ───────────────────────────────────────────────

    tournament_summary = {
        "total_players": total_players,
        "players_with_any_issue": len(affected_players),
        "players_with_zero_sentinel": sum(1 for ps in player_summaries.values() if ps["has_zero_sentinel"]),
        "players_with_nan": sum(1 for ps in player_summaries.values() if ps["has_nan"]),
        "players_with_unresolved_unknown": sum(1 for ps in player_summaries.values() if ps["has_unresolved"]),
        "players_with_extreme_low": len(extreme_players),
        "traits_zero_sentinel_count": count_zero_sentinel,
        "traits_nan_count": count_nan,
        "traits_imputed_from_historical": count_imputed_hist,
        "traits_imputed_from_tier": count_imputed_tier,
        "traits_imputed_from_field": count_imputed_field,
        "traits_unresolved_unknown": count_unknown,
        "traits_extreme_low_flagged": count_extreme_low,
        "tournament_weighted_miss_rate": tournament_weighted_miss,
        "per_trait_missing_rate": per_trait_missing_rate,
        "tier_averages_used": {
            str(tier): {tk: round(v, 2) for tk, v in avgs.items()}
            for tier, avgs in tier_avgs.items()
        },
        "field_averages_used": {tk: round(v, 2) for tk, v in field_avgs.items()},
    }

    # Player records for UI — only include players with issues
    player_records_for_ui = []
    for ps in sorted(player_summaries.values(), key=lambda x: x["rank"] or 999):
        if ps["has_zero_sentinel"] or ps["has_nan"] or ps["has_unresolved"] or ps["extreme_low_traits"]:
            player_records_for_ui.append({
                "player_name": ps["player_name"],
                "name_key": ps["name_key"],
                "tier": ps["tier"],
                "rank": ps["rank"],
                "missing_trait_weight": ps["missing_trait_weight"],
                "has_zero_sentinel": ps["has_zero_sentinel"],
                "has_nan": ps["has_nan"],
                "has_unresolved": ps["has_unresolved"],
                "imputed_traits": ps["imputed_traits"],
                "unknown_traits": ps["unknown_traits"],
                "extreme_low_traits": ps["extreme_low_traits"],
                "issues": ps["issues"],
            })

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_slug": SLUG,
        "qa_config": QA_CONFIG,
        "zero_sentinel_rule": (
            "A trait score of exactly 0.0 is never a valid PGA Tour percentile result. "
            "Zero-sentinels indicate missing source data silently filled by a pipeline default "
            "(e.g. pandas fillna(0)). They must be imputed, not treated as 0th-percentile performance. "
            "See CLASSIFICATION TAXONOMY in this module's docstring for full policy."
        ),
        "tournament_summary": tournament_summary,
        "warnings": warnings_list,
        "player_records": player_records_for_ui,
    }

    return report, records


# ── Output helpers ────────────────────────────────────────────────────────────

def write_report_json(report: dict):
    """Write full report to output/ (archive) and deploy/data/ (UI)."""
    archive_path = BASE_OUT / f"{SLUG}_qa_report.json"
    ui_path      = BASE_DEP / "data" / "qa_report.json"

    for path in [archive_path, ui_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"  Wrote: {path}")


def write_records_csv(records: list[dict]):
    """Write per-(player × trait) detail rows to output/ for spreadsheet audit."""
    csv_path = BASE_OUT / f"{SLUG}_qa_records.csv"
    fieldnames = [
        "player_name", "name_key", "tier", "rank",
        "trait_key", "trait_weight",
        "raw_source_value", "cleaned_value", "initial_status", "status",
        "imputation_source", "imputed_value", "final_value",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k) for k in fieldnames})
    print(f"  Wrote: {csv_path}")


def print_summary(report: dict):
    """Print a human-readable QA summary to stdout."""
    ts = report["tournament_summary"]
    ws = report["warnings"]
    print()
    print("=" * 65)
    print("  VenueDNA QA Report — 2026 Travelers Championship")
    print("=" * 65)
    print(f"  Players:            {ts['total_players']}")
    print(f"  Players w/ issues:  {ts['players_with_any_issue']}")
    print(f"  Zero-sentinel:      {ts['traits_zero_sentinel_count']} traits across "
          f"{ts['players_with_zero_sentinel']} players")
    print(f"  NaN/null:           {ts['traits_nan_count']} traits")
    print(f"  Imputed (tier avg): {ts['traits_imputed_from_tier']}")
    print(f"  Imputed (field avg):{ts['traits_imputed_from_field']}")
    print(f"  Unresolved:         {ts['traits_unresolved_unknown']}")
    print(f"  Extreme low flags:  {ts['traits_extreme_low_flagged']}")
    print(f"  Wt'd miss rate:     {ts['tournament_weighted_miss_rate']*100:.2f}%")
    print()

    errors   = [w for w in ws if w["level"] == "error"]
    warnings_ = [w for w in ws if w["level"] == "warning"]
    infos    = [w for w in ws if w["level"] == "info"]

    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for w in errors:
            print(f"    [ERROR] {w['message']}")
        print()
    if warnings_:
        print(f"  WARNINGS ({len(warnings_)}):")
        for w in warnings_:
            print(f"    [WARN]  {w['message']}")
        print()
    if infos:
        print(f"  INFO ({len(infos)}):")
        for w in infos:
            print(f"    [INFO]  {w['message']}")
        print()

    print("  Per-trait missing rate (pre-imputation):")
    for tk, d in ts["per_trait_missing_rate"].items():
        bar = "#" * d["missing_count"]
        print(f"    {tk:<22} {d['missing_count']:>2}/{d['total']}  ({d['missing_pct']:>5.1f}%)  wt={d['venue_weight']:.2f}  {bar}")
    print()

    affected = report["player_records"]
    if affected:
        print(f"  Affected players ({len(affected)}):")
        for pr in affected:
            imputed = ", ".join(f"{t['trait']}->{t['source']}" for t in pr["imputed_traits"])
            unknown = ", ".join(pr["unknown_traits"])
            extreme = ", ".join(f"{t['trait']}={t['value']:.2f}" for t in pr.get("extreme_low_traits", []))
            parts = []
            if imputed:  parts.append(f"imputed: {imputed}")
            if unknown:  parts.append(f"UNKNOWN: {unknown}")
            if extreme:  parts.append(f"extreme_low: {extreme}")
            miss_pct = int(pr["missing_trait_weight"] * 100)
            detail = " | ".join(parts)
            print(f"    Rank {pr['rank']:>3}  {pr['player_name']:<25}  miss_wt={miss_pct}%  {detail}")
    print("=" * 65)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print(f"Loading payload: {PAYLOAD_PATH}")
    with open(PAYLOAD_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    print("Running QA validation pass…")
    report, records = run_qa(payload)

    print("Writing outputs…")
    write_report_json(report)
    write_records_csv(records)

    print_summary(report)

    n_errors   = sum(1 for w in report["warnings"] if w["level"] == "error")
    n_warnings = sum(1 for w in report["warnings"] if w["level"] == "warning")
    print(f"\nQA complete: {n_errors} error(s), {n_warnings} warning(s).")
    if n_errors > 0:
        print("  >> Fix errors before deploying the board. <<")
    elif n_warnings > 0:
        print("  >> Review warnings — imputed values will affect ranking display. <<")
    else:
        print("  >> All checks passed. <<")


if __name__ == "__main__":
    main()
