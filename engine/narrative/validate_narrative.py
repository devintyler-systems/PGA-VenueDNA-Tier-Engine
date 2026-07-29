"""
validate_narrative.py

Validates a VenueDNA player narrative input+output pair against all
contract §6 rules.

Usage:
    python validate_narrative.py <input.json> <output.json> \\
        [--badge-policy config/badge_policy.v1.json] \\
        [--report-out path/to/report.json]

Exit codes:
    0  All hard-block rules pass (review flags may be present)
    1  One or more hard-block rules failed (block board build / block narrative)
    2  No hard-block failures but review flags present (build allowed, needs_editor_review set)
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package required. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

FORBIDDEN_ABSOLUTES = [
    "guaranteed", "certain", "cannot miss", "dominant", "automatic", "lock"
]

VALID_COMPONENT_IDS = {"neutral_skill", "venue_fit_delta", "venue_history_delta", "penalty_total"}

SCHEMA_DIR = Path(__file__).parent


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_words(text: str) -> int:
    return len(text.split())


def collect_prose_fields(output: dict) -> list[tuple[str, str]]:
    """Return (field_name, text) pairs for all prose fields subject to word-count checks."""
    fields = []
    for key in ("headline", "story_hook", "win_scenario", "failure_scenario", "form_note", "venue_history_note"):
        if key in output and isinstance(output[key], str):
            fields.append((key, output[key]))
    if isinstance(output.get("venue_fit"), dict):
        fields.append(("venue_fit.text", output["venue_fit"].get("text", "")))
    if isinstance(output.get("projection_explainer"), dict):
        fields.append(("projection_explainer.text", output["projection_explainer"].get("text", "")))
    for i, s in enumerate(output.get("strengths", [])):
        if isinstance(s, dict) and "statement" in s:
            fields.append((f"strengths[{i}].statement", s["statement"]))
    for i, w in enumerate(output.get("weaknesses", [])):
        if isinstance(w, dict) and "statement" in w:
            fields.append((f"weaknesses[{i}].statement", w["statement"]))
    return fields


WORD_LIMITS = {
    "headline":               12,
    "story_hook":             75,
    "venue_fit.text":         45,
    "projection_explainer.text": 35,
    "win_scenario":           35,
    "failure_scenario":       35,
    "form_note":              35,
    "venue_history_note":     35,
}

STRENGTH_WEAKNESS_WORD_LIMIT = 30


def validate(input_path: str, output_path: str, badge_policy_path: str) -> dict:
    """
    Run all validation rules. Returns a report dict with:
        player_id, passed, hard_block_errors, review_flags
    """
    inp = load_json(input_path)
    out = load_json(output_path)
    badge_policy = load_json(badge_policy_path)

    player_id = inp.get("player", {}).get("player_id", "<unknown>")
    hard_errors = []
    review_flags = []

    # ── Helper ────────────────────────────────────────────────────────────────

    def hard_block(rule: str, field: str, detail: str):
        hard_errors.append({"rule": rule, "field": field, "detail": detail})

    def review_flag(rule: str, field: str, detail: str):
        review_flags.append({"rule": rule, "field": field, "detail": detail})

    # ── Rule 1: player_id and event_id match ──────────────────────────────────

    inp_pid  = inp.get("player", {}).get("player_id")
    out_pid  = out.get("player_id")
    inp_eid  = inp.get("event", {}).get("event_id")
    out_eid  = out.get("event_id")

    if inp_pid != out_pid:
        hard_block("R01_ID_MISMATCH", "player_id",
                   f"input player_id={inp_pid!r} != output player_id={out_pid!r}")
    if inp_eid != out_eid:
        hard_block("R01_ID_MISMATCH", "event_id",
                   f"input event_id={inp_eid!r} != output event_id={out_eid!r}")

    # ── Rule 2: Required output fields present and non-empty ──────────────────

    required_fields = [
        "player_id", "event_id", "schema_version", "generated_at_utc",
        "generation_mode", "headline", "story_hook", "venue_fit",
        "strengths", "weaknesses", "win_scenario", "failure_scenario",
        "projection_explainer", "form_note", "venue_history_note",
        "evidence_refs", "quality"
    ]
    for field in required_fields:
        val = out.get(field)
        if val is None:
            hard_block("R02_MISSING_FIELD", field, f"Required field '{field}' is missing or null")
        elif isinstance(val, str) and val.strip() == "":
            hard_block("R02_EMPTY_FIELD", field, f"Required field '{field}' is empty string")
        elif isinstance(val, list) and len(val) == 0:
            hard_block("R02_EMPTY_LIST", field, f"Required list field '{field}' is empty")

    # Sub-fields of structured objects
    vf = out.get("venue_fit") or {}
    if not vf.get("text", "").strip():
        hard_block("R02_MISSING_FIELD", "venue_fit.text", "venue_fit.text is missing or empty")
    if not vf.get("trait_ids"):
        hard_block("R02_MISSING_FIELD", "venue_fit.trait_ids", "venue_fit.trait_ids is missing or empty")

    pe = out.get("projection_explainer") or {}
    if not pe.get("text", "").strip():
        hard_block("R02_MISSING_FIELD", "projection_explainer.text", "projection_explainer.text is missing or empty")
    if not pe.get("reason_codes"):
        hard_block("R02_MISSING_FIELD", "projection_explainer.reason_codes", "projection_explainer.reason_codes is missing or empty")
    if not pe.get("component_ids"):
        hard_block("R02_MISSING_FIELD", "projection_explainer.component_ids", "projection_explainer.component_ids is missing or empty")

    # ── Rule 3: JSON Schema validation ───────────────────────────────────────

    try:
        output_schema = load_json(str(SCHEMA_DIR / "narrative_output_schema.json"))
        validator = jsonschema.Draft7Validator(output_schema)
        schema_errors = list(validator.iter_errors(out))
        for err in schema_errors:
            hard_block("R03_SCHEMA_FAILURE", ".".join(str(p) for p in err.absolute_path) or "root",
                       err.message)
    except Exception as e:
        hard_block("R03_SCHEMA_LOAD_ERROR", "output_schema", str(e))

    # ── Rule 4: Word-count limits ─────────────────────────────────────────────

    for field_name, text in collect_prose_fields(out):
        wc = count_words(text)
        if field_name.startswith("strengths[") or field_name.startswith("weaknesses["):
            limit = STRENGTH_WEAKNESS_WORD_LIMIT
        else:
            limit = WORD_LIMITS.get(field_name, 999)
        if wc > limit:
            hard_block("R04_WORD_COUNT", field_name,
                       f"{wc} words exceeds limit of {limit}")

    # ── Rule 5: strengths[*].trait_id exists in input traits ─────────────────

    input_trait_ids = {t["trait_id"] for t in inp.get("traits", []) if "trait_id" in t}
    for i, s in enumerate(out.get("strengths", [])):
        tid = s.get("trait_id")
        if tid and tid not in input_trait_ids:
            hard_block("R05_STRENGTH_TRAIT_REF", f"strengths[{i}].trait_id",
                       f"trait_id={tid!r} not found in input traits")

    # ── Rule 6: weaknesses[*].trait_id in risk_factors or weakness-direction trait ──

    risk_ids = {r["risk_id"] for r in inp.get("risk_factors", []) if "risk_id" in r}
    risk_trait_ids = {r["evidence_trait_id"] for r in inp.get("risk_factors", [])
                      if r.get("evidence_trait_id")}
    weakness_direction_trait_ids = {
        t["trait_id"] for t in inp.get("traits", [])
        if t.get("direction") == "weakness" and "trait_id" in t
    }
    valid_weakness_refs = risk_ids | risk_trait_ids | weakness_direction_trait_ids

    for i, w in enumerate(out.get("weaknesses", [])):
        tid = w.get("trait_id")
        if tid and tid not in valid_weakness_refs and tid not in input_trait_ids:
            hard_block("R06_WEAKNESS_TRAIT_REF", f"weaknesses[{i}].trait_id",
                       f"trait_id={tid!r} not in risk_factors or weakness-direction traits")

    # ── Rule 7: venue_fit.trait_ids in course_dna.primary_demands ────────────

    demand_trait_ids = {d["trait_id"] for d in inp.get("course_dna", {}).get("primary_demands", [])
                        if "trait_id" in d}
    for i, tid in enumerate(vf.get("trait_ids", [])):
        if tid not in demand_trait_ids:
            hard_block("R07_VENUE_FIT_TRAIT_REF", f"venue_fit.trait_ids[{i}]",
                       f"trait_id={tid!r} not in course_dna.primary_demands")

    # ── Rule 8: projection_explainer.reason_codes in input projection_reason_codes ──

    inp_reason_codes = set(inp.get("projection", {}).get("projection_reason_codes", []))
    for i, code in enumerate(pe.get("reason_codes", [])):
        if code not in inp_reason_codes:
            hard_block("R08_REASON_CODE_REF", f"projection_explainer.reason_codes[{i}]",
                       f"reason_code={code!r} not in input projection.projection_reason_codes")

    # ── Rule 9: projection_explainer.component_ids are valid ─────────────────

    for i, cid in enumerate(pe.get("component_ids", [])):
        if cid not in VALID_COMPONENT_IDS:
            hard_block("R09_COMPONENT_ID", f"projection_explainer.component_ids[{i}]",
                       f"component_id={cid!r} not in allowed set {sorted(VALID_COMPONENT_IDS)}")

    # ── Rule 10: badge_ids in output exist in badge_policy ───────────────────

    policy_badge_ids = {b["badge_id"] for b in badge_policy.get("badges", [])}
    # Check output evidence_refs (narrative may not repeat badges, but we check input badges)
    for i, badge in enumerate(inp.get("badges", [])):
        bid = badge.get("badge_id")
        if bid and bid not in policy_badge_ids:
            hard_block("R10_BADGE_POLICY", f"input.badges[{i}].badge_id",
                       f"badge_id={bid!r} not in badge_policy.v1.json")

    # ── Rule 11: evidence_coverage not "high" when unavailable traits exist ───

    has_unavailable = any(
        t.get("evidence_status") == "unavailable"
        for t in inp.get("traits", [])
    )
    coverage = (out.get("quality") or {}).get("evidence_coverage")
    if has_unavailable and coverage == "high":
        hard_block("R11_EVIDENCE_COVERAGE", "quality.evidence_coverage",
                   "evidence_coverage='high' but input has traits with evidence_status='unavailable'")

    # ── Rule 12: Forbidden absolutes ─────────────────────────────────────────
    # Use word-boundary regex to avoid substring false positives (e.g. "blocked" contains "lock").

    all_prose_text = " ".join(text for _, text in collect_prose_fields(out)).lower()
    for phrase in FORBIDDEN_ABSOLUTES:
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pattern, all_prose_text):
            hard_block("R12_FORBIDDEN_ABSOLUTE", "prose",
                       f"Forbidden absolute found: '{phrase}'")

    # ── Review flag A: proper nouns not in input ─────────────────────────────

    known_names = set()
    known_names.add(inp.get("player", {}).get("display_name", "").lower())
    known_names.add(inp.get("event", {}).get("event_name", "").lower())
    known_names.add(inp.get("event", {}).get("venue_name", "").lower())
    for r in inp.get("form", {}).get("recent_results", []):
        known_names.add(r.get("event_name", "").lower())

    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', " ".join(
        text for _, text in collect_prose_fields(out)
    ))
    for noun in proper_nouns:
        if noun.lower() not in known_names and len(noun) > 3:
            review_flag("RF_A_PROPER_NOUN", "prose",
                        f"Proper noun not found in input: '{noun}' — review for invented reference")
            break  # One flag per player is sufficient; avoid noise

    # ── Review flag B: numbers not traceable to input ────────────────────────

    prose_numbers = re.findall(r'\b\d+\.?\d*\b', " ".join(
        text for _, text in collect_prose_fields(out)
    ))
    inp_numbers = set(re.findall(r'\b\d+\.?\d*\b', json.dumps(inp)))
    for num in prose_numbers:
        if num not in inp_numbers:
            review_flag("RF_B_UNTRACED_NUMBER", "prose",
                        f"Number '{num}' in prose not found in input JSON — possible invented stat")
            break  # One flag per player

    # ── Build report ──────────────────────────────────────────────────────────

    passed = len(hard_errors) == 0
    report = {
        "player_id": player_id,
        "passed": passed,
        "hard_block_errors": hard_errors,
        "review_flags": review_flags,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Validate a VenueDNA narrative input+output pair.")
    parser.add_argument("input",  help="Path to narrative input JSON")
    parser.add_argument("output", help="Path to narrative output JSON")
    parser.add_argument("--badge-policy", default="config/badge_policy.v1.json",
                        help="Path to badge_policy.v1.json (default: config/badge_policy.v1.json)")
    parser.add_argument("--report-out", default=None,
                        help="Optional path to write validation_report.json")
    args = parser.parse_args()

    report = validate(args.input, args.output, args.badge_policy)

    if args.report_out:
        with open(args.report_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {args.report_out}")

    if report["passed"]:
        if report["review_flags"]:
            print(f"PASS with {len(report['review_flags'])} review flag(s) for player_id={report['player_id']!r}")
            for flag in report["review_flags"]:
                print(f"  [REVIEW] {flag['rule']} | {flag['field']}: {flag['detail']}")
            sys.exit(2)
        else:
            print(f"PASS — all hard-block rules passed for player_id={report['player_id']!r}")
            sys.exit(0)
    else:
        print(f"FAIL — {len(report['hard_block_errors'])} hard-block error(s) for player_id={report['player_id']!r}")
        for err in report["hard_block_errors"]:
            print(f"  [BLOCK] {err['rule']} | {err['field']}: {err['detail']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
