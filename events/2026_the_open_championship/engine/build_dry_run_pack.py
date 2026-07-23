"""Normalize the Open v3 scorer output into the repository artifact contract.

This is intentionally a packaging layer: it never recalculates rankings.
"""
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
OUT = BASE / "output"
DEPLOY = BASE / "deploy"
DATA = DEPLOY / "data"
SLUG = "2026_the_open_championship"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f)

def dump(path, value):
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)

payload_raw = load("event_payload.json")
context = load("event_context.json")
players = payload_raw["players"]

tiers = {f"tier_{n}": [p for p in players if p["tier"] == n] for n in range(1, 6)}
event_payload = {
    "event": {"name": context["event_name"], "event_id": context["event_id"], "dates": context.get("dates")},
    "venue": {"name": context["venue"], "par": context["par"], "yards": context["yards"], "course_type": context["course_type"]},
    "model_summary": {"model_version": context["model_version"], "field_size": len(players), "tier_counts": context["tier_counts"]},
    "trait_weight_matrix": context["trait_weight_matrix"],
    "tiers": tiers,
    "flags": {"anti_patterns": [p["first_name"] + " " + p["last_name"] for p in players if p.get("ap_total_flags", 0)], "value_flags": [], "health_gates": [], "risk_stressors": []},
    "players": players,
    "metadata": {"engine_version": context["model_version"], "event_iteration": "dry_run", "generated_at": NOW,
                 "source_scorer": "score_open_2026_v3.py", "schema_note": "Normalized packaging; rankings are unchanged."},
}
briefs = {
    "event": event_payload["event"],
    "generated_at": NOW,
    # The runtime uses this full-field lookup for its player modal. The tier
    # subsets remain for clients that only render pre-tournament briefs.
    "players": players,
    "tier_1": tiers["tier_1"],
    "tier_2": tiers["tier_2"],
}
links = {
    "event_id": SLUG,
    "generated_at": NOW,
    "availability": "not supplied by active event inputs",
    "tournament_homepage": None,
    "official_leaderboard": None,
    "datagolf_event_page": None,
    "field_list_source": "input/the_open_championship_player_field_R1_R2_teetimes.csv",
    "weather_source": "input/birkdale_full_course_weather_data_2026.json",
    "notes": "Null URLs are deliberate: no canonical URLs were present in the active event inputs.",
}

dump(OUT / f"{SLUG}_event_context.json", context)
dump(OUT / f"{SLUG}_event_payload.json", event_payload)
dump(OUT / f"{SLUG}_player_briefs.json", briefs)
dump(OUT / f"{SLUG}_links.json", links)

# Adapter for the existing interactive board. This is packaging only: every
# score, rank, tier, probability, and aggregate penalty is copied verbatim
# from the normalized scorer payload. Rule-level penalty splits were not
# emitted by the v3 source, so they are deliberately represented as zero /
# false instead of being reconstructed or inferred.
def board_row(p):
    d = p["decomposition"]
    return {
        "rank": p["rank"],
        "player": f"{p['first_name']} {p['last_name']}",
        "tier": f"T{p['tier']}",
        "vts_final": p["vts_final"],
        "prepenalty_vts": p["vts_final"] - d.get("penalties", 0),
        "penalties_total": d.get("penalties", 0),
        "penaltyR1": 0, "penaltyR2": 0, "penaltyR3": 0,
        "penaltyR4": 0, "penaltyR5": 0, "penaltyR6": 0,
        "penaltyR7": 0, "penaltyR8": 0, "penaltyR9": 0,
        "neutralSkillIndex": d["neutral_skill_index"],
        "venueFitScore": p["venue_fit_score"],
        "venueFitDelta": d["venue_fit_delta"],
        "venueHistoryDelta": d["venue_history_delta"],
        "winPct": p["win_pct"],
        "top3Pct": None,
        "top5Pct": p["top5_pct"],
        "top10Pct": p["top10_pct"],
        "top20Pct": p["top20_pct"],
        "makeCutPct": p["make_cut_prob"],
        "missCutPct": p["miss_cut_prob"],
        "R1_PuttRegression": False, "R2_ZeroLinks": False,
        "R3_OTTOnlyLinks": False, "R4_BirkdaleDepthGate": False,
        "R5_HistoryConflict": False, "R6_PuttLedLinksTotal": False,
        "R7_LinksAPPGate": False, "R9_FormSpikeUnconfirmed": False,
        "tierReason": p.get("conviction_statement", ""),
        "formClass": p.get("form_class", ""),
        "birkdaleTag": p.get("birkdale_tag", ""),
        "badges": p.get("badges", []),
        "bettingPath": p.get("best_betting_lane", ""),
        "thesis": p.get("scoring_thesis", ""),
        "linksNote": p.get("links_signal_note", ""),
        "birkdaleNote": p.get("birkdale_history_note", ""),
        "rawRiskFlags": [],
    }

board_export = {
    "schemaVersion": "3.2-normalized-board-adapter",
    "generatedAt": NOW,
    "event": context["event_name"],
    "venue": context["venue"],
    "players": [board_row(p) for p in players],
    "metadata": {
        "source_scorer": "score_open_2026_v3.py",
        "rule_level_penalty_trace": "not_available_in_v3_source",
        "rankings_recalculated": False,
    },
}
dump(OUT / f"{SLUG}_board_export.json", board_export)

trait_fields = ["player_name", "neutral_skill_sg", "neutral_skill_index", "data_depth_class", "baseline_confidence_band", "true_sg_total", "true_sg_ott", "true_sg_app", "true_sg_arg", "true_sg_putt", "sg_putt_surface", "recent_form_index", "form_score_adjusted", "comp_course_adjustment_prelim", "venue_history_rounds", "venue_history_sg", "named_risk_tags", "likely_anti_pattern_flags", "missing_data_notes"]
with (OUT / f"{SLUG}_trait_form_matrix.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=trait_fields); w.writeheader()
    for p in players:
        w.writerow({"player_name": f"{p['first_name']} {p['last_name']}", "neutral_skill_sg": p.get("true_sg_vs_baseline"), "neutral_skill_index": p["neutral_skill_index"], "data_depth_class": p.get("data_depth_class"), "baseline_confidence_band": "not_available_in_v3_source", "true_sg_total": p.get("true_sg_last20"), "true_sg_ott": p.get("sg_ott_12m"), "true_sg_app": p.get("sg_app_12m"), "true_sg_arg": p.get("sg_arg_12m"), "true_sg_putt": p.get("sg_putt_12m"), "sg_putt_surface": "not_available_in_v3_source", "recent_form_index": p.get("form_score"), "form_score_adjusted": p.get("form_score"), "comp_course_adjustment_prelim": "not_available_in_v3_source", "venue_history_rounds": p.get("vhn_rounds"), "venue_history_sg": p.get("birkdale_sg_per_round"), "named_risk_tags": "; ".join(p.get("risk_vector", [])) if isinstance(p.get("risk_vector"), list) else p.get("risk_vector"), "likely_anti_pattern_flags": p.get("anti_pattern_summary"), "missing_data_notes": "Fields marked not_available_in_v3_source are packaging gaps, not imputed values."})

vts_fields = ["rank_model", "player_name", "neutral_skill_sg", "neutral_skill_index", "data_depth_class", "baseline_confidence_band", "venue_fit_score", "venue_fit_delta", "venue_fit_confidence_band", "comp_course_adjustment", "venue_history_rounds", "venue_history_sg", "venue_history_delta", "venue_history_confidence_band", "pre_penalty_vts", "blend_class", "blend_weights_used", "tier_eligibility_gate_status", "debut_class", "debut_penalty_applied", "anti_pattern_flags", "anti_pattern_penalty_total", "anti_pattern_trigger_trace", "anti_pattern_modifier_trace", "primary_risk_trait", "risk_stressor_active", "risk_secondary_discount_applied", "risk_discount_trace", "form_score_adjusted", "recent_form_index", "recent_form_gate_applied", "health_flag", "health_gate_status", "health_gate_reason", "player_variance_band", "volatility_index", "venue_variance_class", "variance_adjustment_trace", "probability_compression_class", "probability_compression_coefficients", "probability_compression_trace", "vts_final", "tier", "tier_reason", "win_pct", "top3_pct", "top5_pct", "top10_pct", "top20_pct", "make_cut_pct", "miss_cut_pct", "trace_notes"]
with (OUT / f"{SLUG}_vts_full.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=vts_fields); w.writeheader()
    for p in players:
        d = p["decomposition"]
        w.writerow({"rank_model": p["rank"], "player_name": f"{p['first_name']} {p['last_name']}", "neutral_skill_sg": p.get("true_sg_vs_baseline"), "neutral_skill_index": d["neutral_skill_index"], "data_depth_class": p.get("data_depth_class"), "baseline_confidence_band": "not_available_in_v3_source", "venue_fit_score": p["venue_fit_score"], "venue_fit_delta": d["venue_fit_delta"], "venue_fit_confidence_band": p.get("links_signal_confidence"), "comp_course_adjustment": "not_available_in_v3_source", "venue_history_rounds": p.get("vhn_rounds"), "venue_history_sg": p.get("birkdale_sg_per_round"), "venue_history_delta": d["venue_history_delta"], "venue_history_confidence_band": p.get("venue_history_depth"), "pre_penalty_vts": p["vts_final"], "blend_class": "v3_fixed_40_30_15_15", "blend_weights_used": "NSI=0.40;VFS=0.30;VHN=0.15;FORM=0.15", "tier_eligibility_gate_status": "not_available_in_v3_source", "debut_class": p.get("birkdale_tag"), "debut_penalty_applied": 0, "anti_pattern_flags": p.get("anti_pattern_summary"), "anti_pattern_penalty_total": d["penalties"], "anti_pattern_trigger_trace": "not_available_in_v3_source", "anti_pattern_modifier_trace": "not_available_in_v3_source", "primary_risk_trait": p.get("risk_vector"), "risk_stressor_active": "not_available_in_v3_source", "risk_secondary_discount_applied": "not_available_in_v3_source", "risk_discount_trace": "not_available_in_v3_source", "form_score_adjusted": d["form_score"], "recent_form_index": d["form_score"], "recent_form_gate_applied": "not_available_in_v3_source", "health_flag": "not_available_in_v3_source", "health_gate_status": "not_available_in_v3_source", "health_gate_reason": "not_available_in_v3_source", "player_variance_band": "not_available_in_v3_source", "volatility_index": "not_available_in_v3_source", "venue_variance_class": context.get("variance_class"), "variance_adjustment_trace": "not_available_in_v3_source", "probability_compression_class": "not_available_in_v3_source", "probability_compression_coefficients": "not_available_in_v3_source", "probability_compression_trace": "not_available_in_v3_source", "vts_final": p["vts_final"], "tier": p["tier"], "tier_reason": p.get("conviction_statement"), "win_pct": p["win_pct"], "top3_pct": "not_available_in_v3_source", "top5_pct": p["top5_pct"], "top10_pct": p["top10_pct"], "top20_pct": p["top20_pct"], "make_cut_pct": p["make_cut_prob"], "miss_cut_pct": p["miss_cut_prob"], "trace_notes": d["trace_notes"]})

# Deploy files: canonical names plus explicit legacy aliases requested for review.
for source, target in [(OUT / f"{SLUG}_event_payload.json", DATA / "event_payload.json"), (OUT / f"{SLUG}_player_briefs.json", DATA / "player_briefs.json"), (OUT / f"{SLUG}_vts_full.csv", DATA / "vts_full.csv"), (OUT / f"{SLUG}_links.json", DATA / "links.json"), (OUT / f"{SLUG}_board_export.json", DATA / "board_export.json")]:
    shutil.copyfile(source, target)
shutil.copyfile(DATA / "event_payload.json", DATA / "eventpayload.json")
shutil.copyfile(DATA / "vts_full.csv", DATA / "vtsfull.csv")
shutil.copyfile(DATA / "player_briefs.json", DATA / "playerbriefs.json")
shutil.copyfile(DATA / "board_export.json", DATA / "open_2026_board_export.json")
print(f"normalized {len(players)} players at {NOW}")
