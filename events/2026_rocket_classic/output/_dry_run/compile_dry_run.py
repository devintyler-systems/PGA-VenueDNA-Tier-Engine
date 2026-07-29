"""
events/2026_rocket_classic/output/_dry_run/compile_dry_run.py

Dry-run narrative-input compilation against the Rocket Classic v1.2 event payload.

Purpose: prove that the narrative contract consumes only evidence that is
allowed by trait_availability and sourceCoverage.

Hard rules enforced:
  - No API / model calls
  - No narrative generation or modification of any tracked file
  - Zero values are valid evidence only when availability == MEASURED_ZERO
  - PERF_FIELDS (app_true, ott_true, putt_true, arg_true) are HARD_EXCLUDED
  - ch_adjustment enters only as venue_history context
  - true_sg_l20 enters only when availability == MEASURED
  - MISSING_ZERO_FILLED approach/long-iron never enters trait input or badge evaluation
  - No badge derives from true_sg_l20, ch_adjustment, or delta_fit
"""

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parents[4]
PAYLOAD_PATH = REPO_ROOT / "events/2026_rocket_classic/output/2026_rocket_classic_event_payload.json"
OUTPUT_DIR   = Path(__file__).resolve().parent

# ── Contract constants ─────────────────────────────────────────────────────────

# Fields from dg_performance_2026.csv — HARD_EXCLUDED regardless of any value
HARD_EXCLUDED: set[str] = {"app_true", "ott_true", "putt_true", "arg_true"}

# Fields that are badge-ineligible by v1.2 contract
BADGE_INELIGIBLE: set[str] = {
    "ch_adjustment", "true_sg_l20", "delta_fit",
    "sg_base_composite", "sg_similar_composite",
} | HARD_EXCLUDED

# Availability values that represent real evidence for narrative purposes
VALID_NARRATIVE_AVAIL: set[str] = {"MEASURED", "MEASURED_ZERO", "DERIVED", "DEBUT_ZERO"}

# Availability values that mean the value is zero-filled noise, not evidence
INVALID_AVAIL: set[str] = {"UNAVAILABLE", "MISSING_ZERO_FILLED"}


# ── Per-player compiler ────────────────────────────────────────────────────────

def compile_player(player: dict) -> dict:
    pid        = player.get("player_id")
    pname      = player.get("player") or player.get("player_name", "unknown")
    depth      = player.get("data_depth", "UNKNOWN")
    avail_map  = player.get("trait_availability")

    # ── UNSCORED: no scoring data, no narrative possible ─────────────────────
    if depth == "UNSCORED":
        return {
            "player_id":           pid,
            "player_name":         pname,
            "data_depth":          depth,
            "eligibility":         "UNAVAILABLE",
            "rejection_reason":    "UNSCORED — absent from dg_decomposition.csv; excluded from scoring loop",
            "narrative_permitted": False,
            "badge_eligible":      False,
            "approved_inputs":     [],
            "excluded_fields":     [],
            "badge_traits_considered": [],
            "evidence_flags":      ["UNSCORED"],
            "reason_codes":        ["UNSCORED_NO_DECOMP_DATA"],
        }

    if avail_map is None:
        return {
            "player_id":           pid,
            "player_name":         pname,
            "data_depth":          depth,
            "eligibility":         "UNAVAILABLE",
            "rejection_reason":    "trait_availability is null — cannot compile inputs",
            "narrative_permitted": False,
            "badge_eligible":      False,
            "approved_inputs":     [],
            "excluded_fields":     [],
            "badge_traits_considered": [],
            "evidence_flags":      ["NULL_AVAILABILITY"],
            "reason_codes":        ["NULL_TRAIT_AVAILABILITY"],
        }

    approved_inputs: list[dict]  = []
    excluded_fields: list[dict]  = []
    badge_considered: list[dict] = []
    evidence_flags: list[str]    = []
    reason_codes: list[str]      = []

    for trait, meta in avail_map.items():
        avail_val       = meta.get("availability", "UNKNOWN")
        usable_narr     = meta.get("usable_for_narrative_traits", False)
        usable_badge    = meta.get("usable_for_badges", False)
        narr_context    = meta.get("narrative_context")
        narr_qualifier  = meta.get("narrative_qualifier")
        excl_reason_raw = meta.get("reason", "")

        # ── HARD_EXCLUDED: perf fields never enter, regardless of value ───────
        if trait in HARD_EXCLUDED:
            excluded_fields.append({
                "field":        trait,
                "availability": avail_val,
                "rule":         "HARD_EXCLUDED",
                "reason":       "PERF_FILE_ABSENT — dg_performance_2026.csv not present; "
                                "value is 0.0 zero-fill, not real evidence",
            })
            continue

        # ── Badge evaluation tracking ─────────────────────────────────────────
        if trait in BADGE_INELIGIBLE:
            badge_considered.append({
                "trait":        trait,
                "availability": avail_val,
                "verdict":      "EXCLUDED",
                "reason":       "badge-ineligible by v1.2 contract",
            })
        elif not usable_badge:
            badge_considered.append({
                "trait":        trait,
                "availability": avail_val,
                "verdict":      "EXCLUDED",
                "reason":       f"usable_for_badges=False ({avail_val})",
            })
        else:
            badge_considered.append({
                "trait":        trait,
                "availability": avail_val,
                "value":        player.get(trait),
                "verdict":      "ELIGIBLE",
                "reason":       "usable_for_badges=True and not in BADGE_INELIGIBLE set",
            })

        # ── Narrative input gating ────────────────────────────────────────────
        if not usable_narr:
            if avail_val in INVALID_AVAIL:
                excluded_fields.append({
                    "field":        trait,
                    "availability": avail_val,
                    "rule":         "INVALID_AVAILABILITY",
                    "reason":       excl_reason_raw or f"{avail_val} — value is not real evidence",
                })
            else:
                excluded_fields.append({
                    "field":        trait,
                    "availability": avail_val,
                    "rule":         "CONTRACT_INELIGIBLE",
                    "reason":       "usable_for_narrative_traits=False — structural/scoring-only field",
                })
            continue

        # ── ch_adjustment: narrative-eligible only as venue-history context ───
        if trait == "ch_adjustment":
            if narr_context != "venue_history":
                excluded_fields.append({
                    "field":        trait,
                    "availability": avail_val,
                    "rule":         "MISSING_VENUE_HISTORY_QUALIFIER",
                    "reason":       "ch_adjustment must carry narrative_context=venue_history",
                })
                continue
            approved_inputs.append({
                "field":              trait,
                "availability":       avail_val,
                "value":              player.get(trait),
                "narrative_context":  narr_context,
                "narrative_qualifier": narr_qualifier,
                "label":              "Venue-history context only — not a standalone player-skill trait",
            })
            continue

        # ── true_sg_l20: narrative-eligible only when MEASURED ────────────────
        if trait == "true_sg_l20":
            if avail_val != "MEASURED":
                excluded_fields.append({
                    "field":        trait,
                    "availability": avail_val,
                    "rule":         "FORM_NOT_MEASURED",
                    "reason":       "true_sg_l20 enters narrative only when availability==MEASURED; "
                                    f"this player has {avail_val}",
                })
                continue
            approved_inputs.append({
                "field":        trait,
                "availability": avail_val,
                "value":        player.get(trait),
                "label":        "Recent form (L20 strokes gained)",
            })
            continue

        # ── All other narrative-eligible traits ───────────────────────────────
        if avail_val in INVALID_AVAIL:
            excluded_fields.append({
                "field":        trait,
                "availability": avail_val,
                "rule":         "INVALID_AVAILABILITY",
                "reason":       excl_reason_raw or f"{avail_val} — zero-fill, not real evidence",
            })
        else:
            approved_inputs.append({
                "field":        trait,
                "availability": avail_val,
                "value":        player.get(trait),
            })

    # ── Evidence flags ─────────────────────────────────────────────────────────
    is_debut        = depth == "DEBUT"
    approach_avail  = avail_map.get("trait_approach_raw", {}).get("availability", "UNKNOWN")
    long_iron_avail = avail_map.get("trait_long_iron_raw", {}).get("availability", "UNKNOWN")
    form_avail      = avail_map.get("true_sg_l20", {}).get("availability", "UNKNOWN")
    perf_avail      = avail_map.get("app_true", {}).get("availability", "UNKNOWN")

    missing_approach  = approach_avail  in INVALID_AVAIL
    missing_long_iron = long_iron_avail in INVALID_AVAIL
    missing_form      = form_avail      in INVALID_AVAIL
    perf_absent       = perf_avail == "UNAVAILABLE"

    if is_debut:
        evidence_flags.append("DEBUT")
        reason_codes.append("DEBUT_PLAYER_NO_SIM_COURSE_HISTORY")
    if missing_form:
        evidence_flags.append("MISSING_FORM")
        reason_codes.append("TRUE_SG_L20_NOT_MEASURED")
    if missing_approach:
        evidence_flags.append("MISSING_APPROACH_TRAIT")
        reason_codes.append("TRAIT_APPROACH_RAW_MISSING_ZERO_FILLED")
    if missing_long_iron:
        evidence_flags.append("MISSING_LONG_IRON_TRAIT")
        reason_codes.append("TRAIT_LONG_IRON_RAW_MISSING_ZERO_FILLED")
    if perf_absent:
        evidence_flags.append("PERF_FILE_ABSENT")
        reason_codes.append("APP_OTT_PUTT_ARG_UNAVAILABLE_ALL_SCORED_PLAYERS")

    # ── Eligibility decision ───────────────────────────────────────────────────
    # At minimum a scored player always has delta_fit + ch_adjustment as approved inputs.
    # UNAVAILABLE: zero approved inputs (impossible in v1.2 for scored players, but guarded).
    narr_input_count = len(approved_inputs)

    if narr_input_count == 0:
        eligibility = "UNAVAILABLE"
    elif missing_approach and missing_long_iron and missing_form:
        eligibility = "LIMITED_EVIDENCE"   # still has delta_fit + ch_adjustment
    elif is_debut or missing_form or missing_approach or missing_long_iron:
        eligibility = "LIMITED_EVIDENCE"
    else:
        # All 142 scored players carry PERF_FILE_ABSENT — none are fully evidence-complete
        eligibility = "ELIGIBLE_WITH_LIMITATIONS"

    narrative_permitted = eligibility in ("ELIGIBLE_WITH_LIMITATIONS", "LIMITED_EVIDENCE")
    badge_eligible_flag = any(
        b["verdict"] == "ELIGIBLE" for b in badge_considered
    )

    return {
        "player_id":               pid,
        "player_name":             pname,
        "data_depth":              depth,
        "eligibility":             eligibility,
        "narrative_permitted":     narrative_permitted,
        "badge_eligible":          badge_eligible_flag,
        "approved_input_count":    narr_input_count,
        "approved_inputs":         approved_inputs,
        "excluded_field_count":    len(excluded_fields),
        "excluded_fields":         excluded_fields,
        "badge_traits_considered": badge_considered,
        "evidence_flags":          evidence_flags,
        "reason_codes":            reason_codes,
    }


# ── Assertions ─────────────────────────────────────────────────────────────────

def run_assertions(records: list[dict], payload: dict) -> dict:
    players_raw = payload["players"]
    scored      = [p for p in players_raw if p.get("data_depth") != "UNSCORED" and p.get("trait_availability") is not None]
    unscored    = [p for p in players_raw if p.get("data_depth") == "UNSCORED"]

    results: dict[str, dict] = {}

    # A1: 5 UNSCORED stubs create no narrative request
    unscored_records = [r for r in records if r["data_depth"] == "UNSCORED"]
    unscored_narr_ok = all(not r["narrative_permitted"] for r in unscored_records)
    results["A1_unscored_stubs_no_narrative"] = {
        "status":   "PASS" if len(unscored_records) == 5 and unscored_narr_ok else "FAIL",
        "detail":   f"{len(unscored_records)} UNSCORED records; "
                    f"narrative_permitted=True in {sum(1 for r in unscored_records if r['narrative_permitted'])} of them",
    }

    # A2: All 142 scored players retain canonical player IDs
    null_ids = [p for p in scored if not p.get("player_id")]
    results["A2_scored_players_have_canonical_ids"] = {
        "status": "PASS" if len(null_ids) == 0 else "FAIL",
        "detail": f"{len(scored)} scored players; {len(null_ids)} with null player_id",
    }

    # A3: app_true/ott_true/putt_true/arg_true never enter approved inputs
    perf_in_inputs = []
    for r in records:
        for inp in r.get("approved_inputs", []):
            if inp["field"] in HARD_EXCLUDED:
                perf_in_inputs.append({"player": r["player_name"], "field": inp["field"]})
    results["A3_perf_fields_never_in_narrative_inputs"] = {
        "status": "PASS" if not perf_in_inputs else "FAIL",
        "detail": f"{len(perf_in_inputs)} violations" if perf_in_inputs else "0 violations",
    }

    # A4: ch_adjustment labeled only as venue-history context when present in inputs
    ch_unlabeled = []
    for r in records:
        for inp in r.get("approved_inputs", []):
            if inp["field"] == "ch_adjustment" and inp.get("narrative_context") != "venue_history":
                ch_unlabeled.append(r["player_name"])
    results["A4_ch_adjustment_only_as_venue_history"] = {
        "status": "PASS" if not ch_unlabeled else "FAIL",
        "detail": f"{len(ch_unlabeled)} unlabeled violations" if ch_unlabeled else "All ch_adjustment inputs carry venue_history context",
    }

    # A5: true_sg_l20 enters only for MEASURED players
    form_violations = []
    for r in records:
        for inp in r.get("approved_inputs", []):
            if inp["field"] == "true_sg_l20" and inp.get("availability") != "MEASURED":
                form_violations.append({"player": r["player_name"], "availability": inp["availability"]})
    results["A5_true_sg_l20_only_when_measured"] = {
        "status": "PASS" if not form_violations else "FAIL",
        "detail": f"{len(form_violations)} violations" if form_violations else "0 violations",
    }

    # A6: MISSING_ZERO_FILLED approach/long-iron never in approved inputs
    mzf_in_inputs = []
    for r in records:
        for inp in r.get("approved_inputs", []):
            if inp["field"] in ("trait_approach_raw", "trait_long_iron_raw") \
               and inp.get("availability") == "MISSING_ZERO_FILLED":
                mzf_in_inputs.append({"player": r["player_name"], "field": inp["field"]})
    results["A6_missing_zero_filled_approach_not_in_inputs"] = {
        "status": "PASS" if not mzf_in_inputs else "FAIL",
        "detail": f"{len(mzf_in_inputs)} violations" if mzf_in_inputs else "0 violations",
    }

    # A7: No badge derived from true_sg_l20, ch_adjustment, or delta_fit
    badge_violations = []
    for r in records:
        for bt in r.get("badge_traits_considered", []):
            if bt["trait"] in ("true_sg_l20", "ch_adjustment", "delta_fit") \
               and bt["verdict"] == "ELIGIBLE":
                badge_violations.append({"player": r["player_name"], "trait": bt["trait"]})
    results["A7_no_badge_from_contextual_fields"] = {
        "status": "PASS" if not badge_violations else "FAIL",
        "detail": f"{len(badge_violations)} violations" if badge_violations else "0 violations",
    }

    # A8: Every narrative candidate has an evidence/data-depth flag
    no_flag = [r for r in records
               if r["narrative_permitted"] and not r.get("evidence_flags")]
    results["A8_every_narrative_candidate_has_evidence_flag"] = {
        "status": "PASS" if not no_flag else "FAIL",
        "detail": f"{len(no_flag)} candidates missing evidence flags" if no_flag else "0 violations",
    }

    # A9: PERF_FILE_ABSENT flag present for all 142 scored players
    perf_flag_missing = [
        r for r in records
        if r["data_depth"] not in ("UNSCORED",)
        and r.get("player_id") is not None
        and "PERF_FILE_ABSENT" not in r.get("evidence_flags", [])
    ]
    results["A9_perf_absent_flag_all_scored"] = {
        "status": "PASS" if not perf_flag_missing else "FAIL",
        "detail": f"{len(perf_flag_missing)} scored players missing PERF_FILE_ABSENT flag"
                  if perf_flag_missing else f"All {len(scored)} scored players carry PERF_FILE_ABSENT flag",
    }

    return results


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not PAYLOAD_PATH.exists():
        print(f"ERROR: payload not found at {PAYLOAD_PATH}", file=sys.stderr)
        sys.exit(1)

    with PAYLOAD_PATH.open(encoding="utf-8") as f:
        payload = json.load(f)

    players  = payload["players"]
    ts       = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    print(f"[dry_run] Loaded payload: {len(players)} field records  "
          f"(schema: {payload.get('schemaVersion')})")

    # Compile all players
    records = [compile_player(p) for p in players]

    # ── Eligibility distribution ───────────────────────────────────────────────
    from collections import Counter
    eligibility_dist = Counter(r["eligibility"] for r in records)
    reason_dist      = Counter()
    for r in records:
        for rc in r.get("reason_codes", []):
            reason_dist[rc] += 1

    print(f"[dry_run] Eligibility distribution:")
    for k, v in sorted(eligibility_dist.items()):
        print(f"  {k}: {v}")

    # ── Run assertions ─────────────────────────────────────────────────────────
    print("[dry_run] Running assertions...")
    assertion_results = run_assertions(records, payload)
    all_pass = all(v["status"] == "PASS" for v in assertion_results.values())
    for gate, res in assertion_results.items():
        mark = "PASS" if res["status"] == "PASS" else "FAIL"
        print(f"  {gate}: {mark}  — {res['detail']}")

    if not all_pass:
        print("[dry_run] ASSERTION FAILURES DETECTED", file=sys.stderr)

    # ── Write full records ─────────────────────────────────────────────────────
    full_report = {
        "dry_run_schema":       "narrative-dry-run-v1.0",
        "generatedAt":          ts,
        "payloadSchema":        payload.get("schemaVersion"),
        "payloadPath":          str(PAYLOAD_PATH.relative_to(REPO_ROOT)),
        "totalRecords":         len(records),
        "eligibilityBreakdown": dict(eligibility_dist),
        "reasonCodeBreakdown":  dict(reason_dist),
        "assertionResults":     assertion_results,
        "allAssertionsPass":    all_pass,
        "records":              records,
    }
    records_path = OUTPUT_DIR / "narrative_dry_run_records.json"
    records_path.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    print(f"[dry_run] Records written: {records_path.relative_to(REPO_ROOT)}")

    # ── Write summary (no per-player details) ─────────────────────────────────
    summary = {
        "dry_run_schema":       "narrative-dry-run-summary-v1.0",
        "generatedAt":          ts,
        "payloadSchema":        payload.get("schemaVersion"),
        "totalRecords":         len(records),
        "eligibilityBreakdown": dict(eligibility_dist),
        "reasonCodeBreakdown":  dict(reason_dist),
        "assertionResults":     assertion_results,
        "allAssertionsPass":    all_pass,
        "narrativePermitted":   sum(1 for r in records if r["narrative_permitted"]),
        "narrativeRejected":    sum(1 for r in records if not r["narrative_permitted"]),
        "badgeEligible":        sum(1 for r in records if r["badge_eligible"]),
    }
    summary_path = OUTPUT_DIR / "narrative_dry_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[dry_run] Summary written: {summary_path.relative_to(REPO_ROOT)}")

    print(f"[dry_run] Complete — all_assertions_pass={all_pass}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
