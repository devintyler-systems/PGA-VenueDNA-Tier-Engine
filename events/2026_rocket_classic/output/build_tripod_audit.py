"""
build_tripod_audit.py
Generates the read-only tripod audit companion for the 2026 Rocket Classic.
Reads: deploy/data/2026_rocket_classic_event_payload.json  (frozen, never written)
Writes: output/2026_rocket_classic_tripod_audit.json
Writes: deploy/data/2026_rocket_classic_tripod_audit.json  (UI copy)
"""
import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parent.parent.parent.parent
PAYLOAD_PATH  = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_event_payload.json"
OUTPUT_PATH   = REPO_ROOT / "events/2026_rocket_classic/output/2026_rocket_classic_tripod_audit.json"
DEPLOY_COPY   = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_tripod_audit.json"
EXPECTED_HASH = "16d9fc4ca96c34d21919382b6b0dd311a3690236c0eeb79a282e81f1726fdc53"

# Tripod trait labels in the payload trait_scores array
TRIPOD_LABELS = {
    "SG: Approach":  "sg_approach",
    "App 150-200":   "app_150_200",
    "Total Driving": "total_driving",
}
# Backing trait_availability keys for each tripod component
TRIPOD_AVAIL_MAP = {
    "sg_approach":   "trait_approach_raw",
    "app_150_200":   "trait_long_iron_raw",
    "total_driving": "ott_true",
}
TRIPOD_WEIGHTS = {"sg_approach": 0.40, "app_150_200": 0.25, "total_driving": 0.20}
WEIGHT_TOTAL   = 0.85
P60 = 60.0
P65 = 65.0


def sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_trait_score(trait_scores: list, label: str):
    for t in trait_scores:
        if t.get("label") == label:
            return t.get("score")
    return None


def component_usable(player: dict, avail_field: str) -> bool:
    """Returns True only if the component's usable_for_badges is True."""
    ta = player.get("trait_availability") or {}
    return bool(ta.get(avail_field, {}).get("usable_for_badges", False))


def all_components_eligible(player: dict) -> bool:
    """All three tripod backing fields must have usable_for_badges=True."""
    return all(component_usable(player, f) for f in TRIPOD_AVAIL_MAP.values())


def unavail_reason(player: dict) -> str:
    if player.get("data_depth") == "UNSCORED":
        return "player_unscored"
    ta = player.get("trait_availability") or {}
    blocked = []
    for comp_key, avail_field in TRIPOD_AVAIL_MAP.items():
        entry = ta.get(avail_field) or {}
        if not entry.get("usable_for_badges", False):
            avail = entry.get("availability", "UNKNOWN")
            blocked.append(f"{comp_key}:{avail}")
    return "component(s)_ineligible — " + ", ".join(blocked) if blocked else "unknown"


def percentile_rank(value: float, pool: list) -> float:
    below = sum(1 for v in pool if v < value)
    return round(below / len(pool) * 100, 1)


def p_threshold(pool: list, pct: float) -> float:
    s = sorted(pool)
    return s[int(pct / 100 * len(s))]


def build_interpretation(rec: dict) -> str:
    if rec["tripod_eligibility"] == "UNAVAILABLE":
        reason = rec.get("source_availability_reason", "")
        if "unscored" in reason:
            return "Player unscored — tripod audit unavailable."
        return ("Insufficient data — one or more tripod component traits are not eligible "
                "(zero-filled or unavailable).")
    qualified = rec["tripod_qualified"]
    supported = rec["tripod_supported"]
    count     = rec["qualified_trait_count"]
    failed    = rec["failed_all_tripod_traits"]
    if qualified:
        return "Tripod-qualified: all three Detroit core components at or above 60th percentile."
    if supported:
        return ("Tripod-supported: weighted profile above 65th percentile with "
                "two of three core components at 60th+ percentile.")
    if count == 2:
        return "Partial tripod — two of three core components at or above 60th percentile."
    if count == 1:
        return "Limited tripod profile — one of three core components at or above 60th percentile."
    if failed:
        return "No core component at 60th percentile in Detroit tripod."
    return "Tripod audit computed — see component percentiles."


def main():
    # Guard: verify frozen payload hash BEFORE reading
    actual = sha256(PAYLOAD_PATH)
    assert actual == EXPECTED_HASH, (
        f"Payload hash mismatch!\n  expected: {EXPECTED_HASH}\n  actual:   {actual}"
    )
    print(f"[hash-guard] Pre-read hash verified: {actual[:16]}...")

    with open(PAYLOAD_PATH) as f:
        payload = json.load(f)
    players = payload["players"]
    print(f"[load] {len(players)} players")

    # Classify
    unscored   = [p for p in players if p.get("data_depth") == "UNSCORED"]
    scored     = [p for p in players if p.get("data_depth") != "UNSCORED"]
    eligible   = [p for p in scored if all_components_eligible(p)]
    ineligible = [p for p in scored if not all_components_eligible(p)]

    print(f"[classify] unscored={len(unscored)}, eligible={len(eligible)}, "
          f"ineligible_scored={len(ineligible)}")
    assert len(unscored) + len(scored) == 147, "Total player count mismatch"
    assert len(eligible) + len(ineligible) == len(scored), "Scored classification mismatch"

    # Build score pools from eligible players only
    pools = {k: [] for k in TRIPOD_AVAIL_MAP}
    for p in eligible:
        ts = p.get("trait_scores", [])
        for label, key in TRIPOD_LABELS.items():
            v = get_trait_score(ts, label)
            assert v is not None, f"Eligible player {p['player_id']} missing trait score '{label}'"
            pools[key].append(v)

    pool_weighted = [
        (pools["sg_approach"][i] * 0.40
         + pools["app_150_200"][i]  * 0.25
         + pools["total_driving"][i] * 0.20) / WEIGHT_TOTAL
        for i in range(len(eligible))
    ]

    p60_sg  = p_threshold(pools["sg_approach"],  P60)
    p60_app = p_threshold(pools["app_150_200"],  P60)
    p60_drv = p_threshold(pools["total_driving"], P60)
    p65_wtd = p_threshold(pool_weighted,          P65)

    print(f"[thresholds] sg_approach p60={p60_sg:.1f}, app_150_200 p60={p60_app:.1f}, "
          f"total_driving p60={p60_drv:.1f}, weighted p65={p65_wtd:.1f}")

    # Build audit records — iterate over players in original payload order
    audit_records = []
    for p in players:
        pid = p["player_id"]
        base = {
            "player_id":             pid,
            "player_name":           p.get("player_name"),
            "rank":                  p.get("rank"),
            "tier":                  p.get("tier"),
            "vts_final":             p.get("vts_final"),
            "neutralSkillIndex":     p.get("neutralSkillIndex"),
            "deltaFit":              p.get("delta_fit"),
            "data_depth":            p.get("data_depth"),
            "current_engine_effect": "NONE",
            "proposed_v2_effect":    "NONE — NOT ACTIVE",
            "t2g_no_red_flag":       None,
            "t2g_source_note":       "arg_true_value_not_present_in_payload",
        }

        # ── UNSCORED ──────────────────────────────────────────────────────────
        if p.get("data_depth") == "UNSCORED":
            base.update({
                "tripod_eligibility":         "UNAVAILABLE",
                "tripod_qualified":           None,
                "tripod_supported":           None,
                "tripod_audit_status":        "INSUFFICIENT_DATA",
                "source_availability_reason": "player_unscored",
                "qualified_trait_count":      None,
                "failed_all_tripod_traits":   None,
                "weighted_tripod_score":      None,
                "weighted_tripod_percentile": None,
                "component_percentiles":      None,
                "recent_form_risk_flag":      None,
                "recent_form_risk_note":      "player_unscored",
                "audit_interpretation":       "Player unscored — tripod audit unavailable.",
            })
            audit_records.append(base)
            continue

        # ── Ineligible scored player ──────────────────────────────────────────
        if not all_components_eligible(p):
            reason = unavail_reason(p)
            base.update({
                "tripod_eligibility":         "UNAVAILABLE",
                "tripod_qualified":           None,
                "tripod_supported":           None,
                "tripod_audit_status":        "INSUFFICIENT_DATA",
                "source_availability_reason": reason,
                "qualified_trait_count":      None,
                "failed_all_tripod_traits":   None,
                "weighted_tripod_score":      None,
                "weighted_tripod_percentile": None,
                "component_percentiles":      None,
                "recent_form_risk_flag":      None,
                "recent_form_risk_note":      f"ineligible: {reason}",
                "audit_interpretation": (
                    "Insufficient data — one or more tripod component traits are not eligible "
                    "(zero-filled or unavailable)."
                ),
            })
            audit_records.append(base)
            continue

        # ── Eligible player ───────────────────────────────────────────────────
        ts      = p.get("trait_scores", [])
        sg_val  = get_trait_score(ts, "SG: Approach")
        app_val = get_trait_score(ts, "App 150-200")
        drv_val = get_trait_score(ts, "Total Driving")

        pct_sg  = percentile_rank(sg_val,  pools["sg_approach"])
        pct_app = percentile_rank(app_val, pools["app_150_200"])
        pct_drv = percentile_rank(drv_val, pools["total_driving"])

        wtd_score = (sg_val * 0.40 + app_val * 0.25 + drv_val * 0.20) / WEIGHT_TOTAL
        wtd_pct   = percentile_rank(wtd_score, pool_weighted)

        q_sg  = pct_sg  >= P60
        q_app = pct_app >= P60
        q_drv = pct_drv >= P60
        qual_count = int(q_sg) + int(q_app) + int(q_drv)

        tripod_qualified = all([q_sg, q_app, q_drv])
        tripod_supported = (wtd_pct >= P65) and (qual_count >= 2)

        # Recent form risk: only for tripod_qualified + measured true_sg_l20
        ta         = p.get("trait_availability") or {}
        l20_entry  = ta.get("true_sg_l20", {})
        l20_status = l20_entry.get("source_status", "")
        l20_ok     = l20_status not in ("", "MISSING", "MISSING_ZERO_FILLED")
        true_l20   = p.get("true_sg_l20")

        if not tripod_qualified:
            rf_flag = None
            rf_note = "not_tripod_qualified"
        elif not l20_ok or true_l20 is None:
            rf_flag = None
            rf_note = f"true_sg_l20_not_measured (status={l20_status!r})"
        else:
            rf_flag = (true_l20 < 0.0)
            rf_note = (f"L20 SG: {true_l20:+.2f} — "
                       f"{'form risk disclosed (audit only)' if rf_flag else 'no form risk'}")

        rec = dict(base)
        rec.update({
            "tripod_eligibility":         "ELIGIBLE",
            "tripod_qualified":           tripod_qualified,
            "tripod_supported":           tripod_supported,
            "qualified_trait_count":      qual_count,
            "failed_all_tripod_traits":   (qual_count == 0),
            "weighted_tripod_score":      round(wtd_score, 2),
            "weighted_tripod_percentile": round(wtd_pct, 1),
            "component_percentiles": {
                "sg_approach":   round(pct_sg,  1),
                "app_150_200":   round(pct_app, 1),
                "total_driving": round(pct_drv, 1),
            },
            "recent_form_risk_flag": rf_flag,
            "recent_form_risk_note": rf_note,
        })
        rec["audit_interpretation"] = build_interpretation(rec)
        audit_records.append(rec)

    # Sanity assertions before writing
    assert len(audit_records) == 147, f"Expected 147 records, got {len(audit_records)}"
    missing_pids = [r["player_id"] for r in audit_records if not r.get("player_id")]
    assert not missing_pids, f"Records with missing player_id: {missing_pids}"

    # Assemble artifact
    total_qualified   = sum(1 for r in audit_records if r.get("tripod_qualified") is True)
    total_supported   = sum(1 for r in audit_records if r.get("tripod_supported") is True)
    total_unavailable = sum(1 for r in audit_records if r.get("tripod_eligibility") == "UNAVAILABLE")

    artifact = {
        "metadata": {
            "artifact_type":          "READ_ONLY_AUDIT_COMPANION",
            "scoring_effect":         "NONE",
            "tier_effect":            "NONE",
            "probability_effect":     "NONE",
            "source_payload":         "2026_rocket_classic_event_payload.json",
            "source_payload_schema":  "rocket-classic-v1.2",
            "source_payload_hash":    EXPECTED_HASH,
            "join_key":               "player_id",
            "field_size_expected":    147,
            "frozen_output_preserved": True,
            "generated_at":           datetime.now(timezone.utc).isoformat(),
            "eligible_pool_size":     len(eligible),
            "tripod_qualified_count": total_qualified,
            "tripod_supported_count": total_supported,
            "unavailable_count":      total_unavailable,
            "v2_governance_status":   "NOT_ACTIVE",
            "v2_governance_note": (
                "PROPOSED_V2 rules have zero effect on current ranks, tiers, VTS, or probabilities."
            ),
        },
        "percentile_thresholds": {
            "eligible_pool_size":  len(eligible),
            "sg_approach_p60":     round(p60_sg,  2),
            "app_150_200_p60":     round(p60_app, 2),
            "total_driving_p60":   round(p60_drv, 2),
            "weighted_tripod_p65": round(p65_wtd, 2),
        },
        "players": audit_records,
    }

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"[write] {OUTPUT_PATH.name}")

    shutil.copy2(OUTPUT_PATH, DEPLOY_COPY)
    print(f"[copy]  {DEPLOY_COPY.name}")

    # Guard: verify frozen payload hash AFTER writing
    post_hash = sha256(PAYLOAD_PATH)
    assert post_hash == EXPECTED_HASH, (
        f"PAYLOAD HASH CHANGED after write!\n  expected: {EXPECTED_HASH}\n  actual:   {post_hash}"
    )
    print(f"[hash-guard] Post-write hash verified — payload untouched.")

    print(f"\n=== Build complete ===")
    print(f"  Total:       {len(audit_records)}")
    print(f"  Eligible:    {len(eligible)}")
    print(f"  Qualified:   {total_qualified}")
    print(f"  Supported:   {total_supported}")
    print(f"  Unavailable: {total_unavailable}")


if __name__ == "__main__":
    main()
