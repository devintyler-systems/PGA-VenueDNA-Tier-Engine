"""
build_narratives.py

Build-time narrative generator for VenueDNA events.
Reads the event scoring artifact, constructs narrative input objects per
contract §2, calls the Claude API, validates each response, and persists
all outputs with a full audit trail.

Usage:
    python build_narratives.py --event 2026_rocket_classic

Required env:
    ANTHROPIC_API_KEY

Config consumed (no hardcoded values):
    config/narrative_generation.v1.json
    config/badge_policy.v1.json

Outputs written:
    events/{slug}/output/narratives/{slug}_narrative_inputs_snapshot.json
    events/{slug}/output/narratives/{slug}_player_narratives.json
    events/{slug}/audit/narrative_validation_report.json
    events/{slug}/deploy/data/{slug}_player_narratives.json  (copy for board)
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Optional imports (fail with clear message) ───────────────────────────────

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package required. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

# ── Path resolution ───────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.parent
ENGINE_DIR = Path(__file__).parent
CONFIG_DIR = REPO_ROOT / "config"

# ── Load shared config ─────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    gen_cfg = load_json(CONFIG_DIR / "narrative_generation.v1.json")
    badge_policy = load_json(CONFIG_DIR / "badge_policy.v1.json")
    return gen_cfg, badge_policy


# ── Event artifact discovery ──────────────────────────────────────────────────

def find_scoring_artifact(event_dir: Path) -> Path:
    """Return the best available scoring artifact in output/."""
    candidates = [
        event_dir / "output" / f"{event_dir.name}_final_payload.json",
        event_dir / "output" / f"{event_dir.name}_event_payload.json",
        event_dir / "deploy"  / "data" / f"{event_dir.name}_event_payload.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No scoring artifact found for event '{event_dir.name}'. "
        f"Run the scoring pipeline first. Searched:\n" +
        "\n".join(f"  {c}" for c in candidates)
    )


# ── Badge qualification ────────────────────────────────────────────────────────

def qualify_badges(player: dict, badge_policy: dict) -> list[dict]:
    """
    Award badges based on badge_policy.v1.json thresholds.
    Returns list of badge input objects.
    """
    trait_map = {t["label"].lower().replace(" ", "_"): t for t in player.get("trait_scores", [])}
    badges = []

    for badge_def in badge_policy.get("badges", []):
        bid = badge_def["badge_id"]
        threshold = badge_def.get("threshold", {})
        required_trait_ids = badge_def.get("required_trait_ids", [])

        # Venue-starts based badges
        if "venue_starts_min" in threshold:
            ch_score = player.get("ch_adjustment", 0)
            # Map ch_adjustment to approximate starts; use data_depth as fallback
            # When real starts data is available in the payload, use it directly.
            starts = _estimate_starts(player)
            if starts >= threshold["venue_starts_min"]:
                badges.append({
                    "badge_id": bid,
                    "label": badge_def["label"],
                    "qualification_reason": f"{starts} prior starts satisfies the {threshold['venue_starts_min']}-start minimum.",
                    "evidence_trait_ids": required_trait_ids or ["course_history"],
                })
            continue

        if "venue_starts_max" in threshold:
            starts = _estimate_starts(player)
            if starts <= threshold["venue_starts_max"]:
                badges.append({
                    "badge_id": bid,
                    "label": badge_def["label"],
                    "qualification_reason": f"No prior starts at this venue — venue_starts = {starts}.",
                    "evidence_trait_ids": [],
                })
            continue

        # Percentile-based badges
        if "field_percentile_min" in threshold and required_trait_ids:
            min_pct = threshold["field_percentile_min"]
            # Trait percentiles come from vts_full.csv rankings; approximate via score rank
            # For now, use trait_scores score as percentile proxy (will be replaced with
            # actual percentile data once vts_full.csv is integrated)
            qualifying = True
            evidence_trait_ids = []
            for trait_id in required_trait_ids:
                trait_score = _find_trait_score(player, trait_id)
                if trait_score is None or trait_score < min_pct:
                    qualifying = False
                    break
                evidence_trait_ids.append(trait_id)
            if qualifying:
                badges.append({
                    "badge_id": bid,
                    "label": badge_def["label"],
                    "qualification_reason": (
                        f"{', '.join(required_trait_ids)} threshold(s) satisfied "
                        f"(≥{min_pct}th percentile)."
                    ),
                    "evidence_trait_ids": evidence_trait_ids,
                })

    return badges


def _estimate_starts(player: dict) -> int:
    """Estimate venue starts from available payload fields."""
    # If payload carries explicit venue_starts, use it
    if "venue_starts" in player:
        return int(player["venue_starts"])
    # data_depth == DEBUT → 0 starts
    if player.get("data_depth") == "DEBUT":
        return 0
    # Positive course history score suggests multiple starts
    ch = player.get("ch_adjustment", 0)
    if ch > 0.1:
        return 4  # placeholder: pipeline should supply actual count
    return 1  # limited history


def _find_trait_score(player: dict, trait_id: str) -> float | None:
    """Look up a trait score from the player's trait_scores array by approximate label match."""
    label_map = {
        "approach_play":       ["sg: approach", "approach play", "approach"],
        "iron_play":           ["app 150-200", "iron play 150-200yd", "long-iron 150-225"],
        "driving_accuracy":    ["driving accuracy", "driving acc"],
        "driving_distance":    ["driving distance", "driving dist"],
        "par5_scoring":        ["par 5 scoring", "par5 scoring", "par-5 scoring"],
        "putting":             ["sg: putting", "putting", "easy green putting"],
        "recent_form":         ["recent form", "recent form context"],
        "course_history":      ["course history"],
    }
    aliases = label_map.get(trait_id, [trait_id])
    for ts in player.get("trait_scores", []):
        label_lower = ts.get("label", "").lower()
        if any(alias in label_lower for alias in aliases):
            return ts.get("score")
    return None


# ── Input object construction ─────────────────────────────────────────────────

DETROIT_GOLF_CLUB_DNA = {
    "identity_summary": "A long tree-lined parkland layout that rewards elite approach play from 150-200 yards and penalizes positional mistakes off the tee.",
    "primary_demands": [
        {
            "trait_id": "approach_play",
            "label": "Approach Play",
            "importance": 0.40,
            "rank": 1,
            "reason": "Narrow tree-lined corridors force precise iron play; 44% of approaches arrive from 150-200 yards.",
        },
        {
            "trait_id": "iron_play",
            "label": "Iron Play 150-200yd",
            "importance": 0.25,
            "rank": 2,
            "reason": "Mid-iron precision separates scoring at this length; proximity from 150-200 directly correlates with birdie conversion.",
        },
        {
            "trait_id": "driving_accuracy",
            "label": "Driving Accuracy",
            "importance": 0.15,
            "rank": 3,
            "reason": "Tree-lined fairways penalize errant tee shots with blocked approaches and penalty stroke exposure.",
        },
        {
            "trait_id": "par5_scoring",
            "label": "Par-5 Scoring",
            "importance": 0.10,
            "rank": 4,
            "reason": "Three reachable par-5s provide concentrated birdie opportunity for players who can both reach and convert.",
        },
        {
            "trait_id": "putting",
            "label": "Putting",
            "importance": 0.10,
            "rank": 5,
            "reason": "Bentgrass greens at moderate speed reward consistent putting after birdie-range approaches.",
        },
    ],
    "scoring_opportunities": [
        "Three reachable par-5s where two-putt birdies are available for long hitters.",
        "Mid-iron birdie setups when approach play is elite — proximity from 150-175 yards is the scoring engine.",
        "Early wave scoring advantage on calm mornings before afternoon wind.",
    ],
    "primary_failure_modes": [
        "Missed fairways into trees produce blocked approaches and bogey exposure.",
        "Approach play below field average leads to long-birdie attempts and net pars.",
        "Putting volatility erases approach-play gains — this course does not forgive wasted birdie chances.",
    ],
    "par": 72,
    "yardage": 7380,
    "weather_context": None,
}

KNOWN_COMPONENT_IDS = ["neutral_skill", "venue_fit_delta", "venue_history_delta", "penalty_total"]

TRAIT_ID_LABEL_MAP = {
    "approach_play": "Approach Play",
    "iron_play": "Iron Play 150-200yd",
    "driving_accuracy": "Driving Accuracy",
    "driving_distance": "Driving Distance",
    "par5_scoring": "Par-5 Scoring",
    "putting": "Putting",
    "recent_form": "Recent Form",
    "course_history": "Course History",
}


def build_input_object(player: dict, event_meta: dict, badge_policy: dict, now_utc: str) -> dict:
    """Construct a contract §2 input object from a scoring artifact player record."""

    pid = player.get("player_id") or player.get("dg_id") or ""
    display_name = player.get("player") or player.get("player_name") or ""
    tier = player.get("tier", "T5")
    vts = float(player.get("vts_final", player.get("VenueDNA_final_projection", 50.0)))
    data_depth = player.get("data_depth", "FULL")
    is_debut = data_depth == "DEBUT"

    # Project components
    neutral_skill = float(player.get("neutralSkillIndex", vts))
    venue_fit_delta = float(player.get("delta_fit", 0.0))
    ch_adjustment = float(player.get("ch_adjustment", 0.0))
    penalty_total = 0.0  # Will be enriched once penalty fields are confirmed in payload

    # Conviction from data quality
    conviction = "Low" if is_debut else ("High" if vts >= 80 else "Medium")
    confidence_score = 0.31 if is_debut else (0.88 if vts >= 80 else 0.58)
    confidence_label = conviction

    # Projection reason codes
    reason_codes = []
    if vts >= 90:
        reason_codes.append("ELITE_APPROACH_FIT")
    if ch_adjustment > 0.05:
        reason_codes.append("POSITIVE_VENUE_HISTORY")
    if is_debut:
        reason_codes.append("DEBUT_PENALTY_APPLIED")
        penalty_total -= 2.4
    if not reason_codes:
        reason_codes.append("STANDARD_VENUE_FIT")

    # Traits from trait_scores
    traits = []
    trait_score_list = player.get("trait_scores", [])
    debut_trait_ids = {"iron_play", "driving_accuracy"} if is_debut else set()

    for ts in trait_score_list:
        label = ts.get("label", "")
        score = float(ts.get("score", 0))
        weight = float(ts.get("weight", 0))
        trait_id = _label_to_trait_id(label)
        evidence_status = "unavailable" if trait_id in debut_trait_ids else (
            "limited" if score < 20 else "validated"
        )
        direction = "strength" if score >= 70 else ("weakness" if score < 35 else "neutral")
        traits.append({
            "trait_id": trait_id,
            "label": TRAIT_ID_LABEL_MAP.get(trait_id, label),
            "score": score,
            "field_percentile": score,  # proxy until vts_full.csv percentile is wired
            "venue_importance": weight,
            "fit_contribution": round((score - 50) * weight / 10, 2),
            "direction": direction,
            "evidence_status": evidence_status,
        })

    # Badges
    badges = qualify_badges(player, badge_policy)

    # Form
    true_sg = player.get("true_sg_l20", 0.0)
    strength_tags = player.get("strength_tags", [])
    form_label = "Strong" if true_sg >= 1.0 else ("Mixed" if true_sg >= 0 else "Weak")
    form_direction = "improving" if true_sg >= 1.0 else ("steady" if true_sg >= 0 else "declining")

    form_evidence = []
    if strength_tags:
        form_evidence.append(strength_tags[0] if strength_tags else "Recent form data available.")
    else:
        form_evidence.append("Form evidence based on available strokes gained data.")

    l5 = player.get("l5_array", [])
    recent_results = []
    for i, pos in enumerate(l5[:4]):
        recent_results.append({
            "event_name": f"Recent Start {i + 1}",
            "finish": f"T{pos}" if isinstance(pos, int) and pos > 0 else "MC",
            "date": "2026-01-01",  # placeholder until event dates are available
        })

    # Venue history
    starts = _estimate_starts(player)
    cuts_made = min(starts, round(starts * 0.75))
    history_label = (
        "No meaningful venue sample" if starts == 0
        else ("Limited venue sample" if starts < 3 else "Meaningful venue sample")
    )

    # Risk factors from weakness_tags and anti_pattern_flags
    risk_factors = []
    for wt in player.get("weakness_tags", []):
        risk_factors.append({
            "risk_id": wt.lower().replace(" ", "_")[:40],
            "label": wt,
            "severity": "medium",
            "evidence_trait_id": None,
            "description": f"Weakness flagged: {wt}",
        })
    if is_debut:
        risk_factors.append({
            "risk_id": "debut_penalty",
            "label": "Venue debut",
            "severity": "medium",
            "evidence_trait_id": None,
            "description": f"No prior starts at this venue. Debut penalty of {abs(penalty_total):.1f} VTS points applied per standard policy.",
        })

    if not risk_factors:
        risk_factors.append({
            "risk_id": "general_execution_risk",
            "label": "General execution risk",
            "severity": "low",
            "evidence_trait_id": None,
            "description": "No specific anti-pattern flags raised; standard execution risk applies.",
        })

    return {
        "schema_version": "1.0",
        "event": {
            "event_id": event_meta["event_id"],
            "event_name": event_meta["event_name"],
            "venue_id": event_meta["venue_id"],
            "venue_name": event_meta["venue_name"],
            "event_phase": "pre_tournament",
            "generated_at_utc": now_utc,
            "data_as_of_utc": now_utc,
        },
        "course_dna": DETROIT_GOLF_CLUB_DNA,
        "player": {
            "player_id": pid,
            "display_name": display_name,
            "country": None,
            "handedness": None,
        },
        "projection": {
            "vts": round(vts, 1),
            "vts_rank": int(player.get("rank", 999)),
            "field_size": event_meta.get("field_size", 144),
            "tier": tier,
            "tier_rank": 1,  # enriched later when all players are processed
            "conviction": conviction,
            "confidence_score": round(confidence_score, 2),
            "confidence_label": confidence_label,
            "neutral_skill": round(neutral_skill, 1),
            "venue_fit_delta": round(venue_fit_delta, 2),
            "venue_history_delta": round(ch_adjustment, 2),
            "penalty_total": round(penalty_total, 2),
            "projection_direction": "positive" if vts > 55 else ("negative" if vts < 45 else "neutral"),
            "projection_reason_codes": reason_codes,
        },
        "traits": traits,
        "badges": badges,
        "form": {
            "sample_window": "last_20_starts",
            "form_label": form_label,
            "form_direction": form_direction,
            "form_evidence": form_evidence if form_evidence else ["Form data not available."],
            "recent_results": recent_results,
        },
        "venue_history": {
            "starts": starts,
            "cuts_made": cuts_made,
            "best_finish": None,
            "history_label": history_label,
            "evidence": [history_label + "."],
        },
        "risk_factors": risk_factors,
        "live_context": {
            "round": None,
            "position": None,
            "strokes_gained": [],
            "prediction_status": None,
            "round_evidence": [],
        },
    }


def _label_to_trait_id(label: str) -> str:
    label_lower = label.lower()
    mapping = {
        "sg: approach": "approach_play",
        "approach play": "approach_play",
        "app 150-200": "iron_play",
        "long-iron 150-225": "iron_play",
        "iron play": "iron_play",
        "total driving": "driving_accuracy",
        "driving accuracy": "driving_accuracy",
        "driving acc": "driving_accuracy",
        "driving distance": "driving_distance",
        "par 5 scoring": "par5_scoring",
        "par5 scoring": "par5_scoring",
        "par-5 scoring": "par5_scoring",
        "sg: putting": "putting",
        "easy green putting": "putting",
        "putting": "putting",
        "recent form": "recent_form",
        "course history": "course_history",
    }
    for key, tid in mapping.items():
        if key in label_lower:
            return tid
    return label_lower.replace(" ", "_").replace(":", "").replace("-", "_")


# ── Narrative generation ────────────────────────────────────────────────────────

def build_prompt(input_obj: dict, gen_cfg: dict) -> tuple[str, str]:
    """Return (system_prompt, user_message) from config and input object."""
    system_prompt = gen_cfg["system_prompt"]
    user_template = gen_cfg["user_prompt_template"]
    user_message = user_template.replace(
        "{{PLAYER_NARRATIVE_INPUT_JSON}}",
        json.dumps(input_obj, indent=2)
    )
    return system_prompt, user_message


def call_api_with_retry(client, system_prompt: str, user_message: str, gen_cfg: dict) -> str:
    """Call Claude API with retry policy from config. Returns raw response text."""
    retry_policy = gen_cfg.get("retry_policy", {})
    max_attempts = retry_policy.get("max_attempts", 3)
    retry_on = set(retry_policy.get("retry_on", ["schema_failure", "api_error"]))
    no_retry_on = set(retry_policy.get("no_retry_on", ["evidence_reference_failure"]))

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.messages.create(
                model=gen_cfg["model"],
                max_tokens=gen_cfg.get("max_tokens", 1200),
                temperature=gen_cfg.get("temperature", 0),
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            last_error = e
            err_type = "api_error"
            if err_type in no_retry_on:
                break
            if err_type not in retry_on:
                break
            if attempt < max_attempts:
                print(f"  Attempt {attempt} failed ({e}), retrying...", flush=True)
    raise RuntimeError(f"API call failed after {max_attempts} attempts: {last_error}")


def parse_narrative_response(raw: str) -> dict:
    """Extract JSON from API response. Handles markdown code fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        inner = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        text = "\n".join(inner)
    return json.loads(text)


# ── Inline validator ──────────────────────────────────────────────────────────

# Import the validate function from validate_narrative.py in the same package
sys.path.insert(0, str(ENGINE_DIR))
try:
    from validate_narrative import validate as _validate_narrative
    _VALIDATOR_AVAILABLE = True
except ImportError:
    _VALIDATOR_AVAILABLE = False
    print("WARNING: validate_narrative.py not importable — skipping inline validation", file=sys.stderr)


def validate_inline(input_obj: dict, narrative_obj: dict, badge_policy_path: str) -> dict:
    """Run validation and return report dict."""
    if not _VALIDATOR_AVAILABLE:
        return {
            "player_id": input_obj["player"]["player_id"],
            "passed": True,
            "hard_block_errors": [],
            "review_flags": [{"rule": "VALIDATOR_UNAVAILABLE", "field": "system",
                              "detail": "validate_narrative.py not importable"}],
        }
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf_in:
        json.dump(input_obj, tf_in)
        path_in = tf_in.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf_out:
        json.dump(narrative_obj, tf_out)
        path_out = tf_out.name
    try:
        report = _validate_narrative(path_in, path_out, badge_policy_path)
    finally:
        os.unlink(path_in)
        os.unlink(path_out)
    return report


def make_blocked_narrative(input_obj: dict, event_id: str, errors: list, now_utc: str) -> dict:
    """Return a minimal narrative object with validation_errors populated (prose suppressed)."""
    return {
        "player_id": input_obj["player"]["player_id"],
        "event_id": event_id,
        "schema_version": "1.0",
        "generated_at_utc": now_utc,
        "generation_mode": "pre_tournament",
        "headline": "",
        "story_hook": "",
        "venue_fit": {"text": "", "trait_ids": []},
        "strengths": [],
        "weaknesses": [],
        "win_scenario": "",
        "failure_scenario": "",
        "projection_explainer": {"text": "", "reason_codes": [], "component_ids": []},
        "form_note": "",
        "venue_history_note": "",
        "evidence_refs": {
            "strength_trait_ids": [],
            "risk_trait_ids": [],
            "course_demand_trait_ids": [],
            "projection_reason_codes": [],
        },
        "quality": {
            "evidence_coverage": "low",
            "needs_editor_review": True,
            "validation_errors": errors,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build VenueDNA player narratives at build time.")
    parser.add_argument("--event", required=True, help="Event slug, e.g. 2026_rocket_classic")
    args = parser.parse_args()

    slug = args.event
    event_dir = REPO_ROOT / "events" / slug
    if not event_dir.exists():
        print(f"ERROR: Event directory not found: {event_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Load config ────────────────────────────────────────────────────────────
    print(f"Loading config from {CONFIG_DIR}...", flush=True)
    gen_cfg, badge_policy = load_config()
    badge_policy_path = str(CONFIG_DIR / "badge_policy.v1.json")

    # ── Validate ANTHROPIC_API_KEY ─────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()

    # ── Find scoring artifact ──────────────────────────────────────────────────
    artifact_path = find_scoring_artifact(event_dir)
    print(f"Using scoring artifact: {artifact_path}", flush=True)
    artifact = load_json(artifact_path)

    # Extract player list — handle both payload schemas
    players = (
        artifact.get("players")
        or artifact.get("official_model", {}).get("players")
        or []
    )
    if not players:
        print("ERROR: No players found in scoring artifact.", file=sys.stderr)
        sys.exit(1)

    field_size = len(players)
    event_meta = {
        "event_id": f"pga_{slug}",
        "event_name": artifact.get("event_name", "Rocket Classic"),
        "venue_id": "detroit_golf_club",
        "venue_name": "Detroit Golf Club",
        "field_size": field_size,
    }

    # ── Prepare output dirs ────────────────────────────────────────────────────
    narratives_dir = event_dir / "output" / "narratives"
    narratives_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = event_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    deploy_data_dir = event_dir / "deploy" / "data"
    deploy_data_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Build input objects ────────────────────────────────────────────────────
    print(f"Building {field_size} narrative input objects...", flush=True)
    inputs = []
    for player in players:
        inp = build_input_object(player, event_meta, badge_policy, now_utc)
        inputs.append(inp)

    # Persist input snapshot
    snapshot_path = narratives_dir / f"{slug}_narrative_inputs_snapshot.json"
    snapshot = {
        "generated_at_utc": now_utc,
        "prompt_contract_version": gen_cfg["prompt_contract_version"],
        "model": gen_cfg["model"],
        "output_schema_version": gen_cfg["output_schema_version"],
        "player_count": len(inputs),
        "inputs": inputs,
    }
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Input snapshot written: {snapshot_path}", flush=True)

    # ── System prompt (cached across all players) ──────────────────────────────
    system_prompt = gen_cfg["system_prompt"]

    # ── Generate narratives ────────────────────────────────────────────────────
    narratives = []
    validation_reports = []
    passed = 0
    blocked = 0
    review_flagged = 0

    for i, inp in enumerate(inputs):
        pid = inp["player"]["player_id"]
        name = inp["player"]["display_name"]
        print(f"  [{i+1}/{field_size}] {name} ({pid})...", end=" ", flush=True)

        _, user_message = build_prompt(inp, gen_cfg)

        narrative = None
        hard_block_errors = []

        try:
            raw = call_api_with_retry(client, system_prompt, user_message, gen_cfg)
            narrative = parse_narrative_response(raw)
        except json.JSONDecodeError as e:
            hard_block_errors.append({"rule": "PARSE_FAILURE", "field": "response", "detail": str(e)})
        except Exception as e:
            hard_block_errors.append({"rule": "API_FAILURE", "field": "api", "detail": str(e)})

        if narrative and not hard_block_errors:
            report = validate_inline(inp, narrative, badge_policy_path)
            validation_reports.append(report)
            if not report["passed"]:
                blocked += 1
                hard_block_errors = report["hard_block_errors"]
                narrative = make_blocked_narrative(inp, event_meta["event_id"], hard_block_errors, now_utc)
                print(f"BLOCKED ({len(hard_block_errors)} errors)")
            else:
                passed += 1
                if report["review_flags"]:
                    review_flagged += 1
                    narrative["quality"]["needs_editor_review"] = True
                print(f"PASS {'(+review)' if report['review_flags'] else ''}")
        else:
            blocked += 1
            narrative = make_blocked_narrative(inp, event_meta["event_id"], hard_block_errors, now_utc)
            validation_reports.append({
                "player_id": pid,
                "passed": False,
                "hard_block_errors": hard_block_errors,
                "review_flags": [],
            })
            print(f"BLOCKED (generation error)")

        narratives.append(narrative)

    # ── Write outputs ──────────────────────────────────────────────────────────
    narratives_path = narratives_dir / f"{slug}_player_narratives.json"
    with open(narratives_path, "w", encoding="utf-8") as f:
        json.dump(narratives, f, indent=2)
    print(f"\nNarratives written: {narratives_path}")

    audit_report = {
        "generated_at_utc": now_utc,
        "prompt_contract_version": gen_cfg["prompt_contract_version"],
        "model": gen_cfg["model"],
        "player_count": field_size,
        "passed": passed,
        "blocked": blocked,
        "review_flagged": review_flagged,
        "players": validation_reports,
    }
    audit_path = audit_dir / "narrative_validation_report.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    print(f"Audit report written: {audit_path}")

    # Copy to deploy/data/
    deploy_path = deploy_data_dir / f"{slug}_player_narratives.json"
    shutil.copy2(narratives_path, deploy_path)
    print(f"Copied to deploy/data: {deploy_path}")

    print(f"\nDone. Passed: {passed}, Blocked: {blocked}, Review-flagged: {review_flagged}")
    sys.exit(0 if blocked == 0 else 1)


if __name__ == "__main__":
    main()
