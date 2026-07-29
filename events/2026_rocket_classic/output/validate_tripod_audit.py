"""
validate_tripod_audit.py
Audit mode validation — runs AFTER build_tripod_audit.py generates the sidecar.
Verifies 147 records, joins, qualification logic, and zero-impact guarantees.
Exits 0 on full pass, 1 on any failure.
"""
import json
import hashlib
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT      = Path(__file__).resolve().parent.parent.parent.parent
PAYLOAD_DEPLOY = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_event_payload.json"
PAYLOAD_OUTPUT = REPO_ROOT / "events/2026_rocket_classic/output/2026_rocket_classic_event_payload.json"
AUDIT_PATH     = REPO_ROOT / "events/2026_rocket_classic/output/2026_rocket_classic_tripod_audit.json"
EXPECTED_HASH  = "16d9fc4ca96c34d21919382b6b0dd311a3690236c0eeb79a282e81f1726fdc53"

TRIPOD_AVAIL_MAP = {
    "sg_approach":   "trait_approach_raw",
    "app_150_200":   "trait_long_iron_raw",
    "total_driving": "ott_true",
}

failures = []

def fail(msg):
    failures.append(msg)
    print(f"  FAIL: {msg}")

def ok(msg):
    print(f"  OK:   {msg}")

print("=== Rocket Classic Tripod Audit Validation ===\n")

# V0: Frozen payload hashes (post-build re-check)
print("V0: Frozen payload hash re-check (post-build)")
for path in [PAYLOAD_DEPLOY, PAYLOAD_OUTPUT]:
    with open(path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    if h == EXPECTED_HASH:
        ok(f"{path.name} hash still matches")
    else:
        fail(f"PAYLOAD TAMPERED: {path.name} hash = {h}")

# Load payload
with open(PAYLOAD_DEPLOY) as f:
    payload = json.load(f)
payload_players = {p["player_id"]: p for p in payload["players"]}

# Audit file must exist
if not AUDIT_PATH.exists():
    fail("Audit companion file does not exist — run build_tripod_audit.py first")
    print(f"\n{'='*48}")
    print(f"RESULT: FAILED ({len(failures)} failure(s))")
    sys.exit(1)

with open(AUDIT_PATH) as f:
    audit = json.load(f)
audit_players = audit.get("players", [])

# V1: Header metadata
print("\nV1: Audit header metadata")
header = audit.get("metadata", {})
required_fields = [
    "artifact_type", "scoring_effect", "tier_effect", "probability_effect",
    "source_payload", "source_payload_schema", "join_key",
    "field_size_expected", "frozen_output_preserved",
]
for field in required_fields:
    if field in header:
        ok(f"header.{field} present")
    else:
        fail(f"header.{field} MISSING")
if header.get("artifact_type") == "READ_ONLY_AUDIT_COMPANION":
    ok("artifact_type correct")
else:
    fail(f"artifact_type wrong: {header.get('artifact_type')!r}")
if header.get("scoring_effect") == "NONE":
    ok("scoring_effect is NONE")
else:
    fail(f"scoring_effect wrong: {header.get('scoring_effect')!r}")
if header.get("frozen_output_preserved") is True:
    ok("frozen_output_preserved is True")
else:
    fail(f"frozen_output_preserved wrong: {header.get('frozen_output_preserved')!r}")
if header.get("v2_governance_status") == "NOT_ACTIVE":
    ok("v2_governance_status is NOT_ACTIVE")
else:
    fail(f"v2_governance_status wrong: {header.get('v2_governance_status')!r}")

# V2: Player count
print("\nV2: Audit record count")
if len(audit_players) == 147:
    ok("147 audit records")
else:
    fail(f"Expected 147 audit records, got {len(audit_players)}")

# V3: Every record has player_id
print("\nV3: player_id presence")
missing_pid = [i for i, p in enumerate(audit_players) if not p.get("player_id")]
if not missing_pid:
    ok("All audit records have player_id")
else:
    fail(f"Records missing player_id at indices: {missing_pid}")

# V4: Audit player_ids match payload exactly
print("\nV4: player_id cross-reference")
audit_pids = [p["player_id"] for p in audit_players]
pid_counts = Counter(audit_pids)
dupes = {k: v for k, v in pid_counts.items() if v > 1}
if not dupes:
    ok("All audit player_ids are unique")
else:
    fail(f"Duplicate player_ids: {dupes}")

missing_from_payload = [pid for pid in audit_pids if pid not in payload_players]
if not missing_from_payload:
    ok("All audit player_ids exist in frozen payload")
else:
    fail(f"{len(missing_from_payload)} audit player_ids not in payload: {missing_from_payload[:5]}")

missing_from_audit = [pid for pid in payload_players if pid not in pid_counts]
if not missing_from_audit:
    ok("All 147 payload player_ids present in audit")
else:
    fail(f"{len(missing_from_audit)} payload player_ids absent from audit: {missing_from_audit[:5]}")

# V5: Eligible player component completeness
print("\nV5: Component percentile completeness for eligible players")
bad_eligible = []
for p in audit_players:
    if p.get("tripod_eligibility") == "ELIGIBLE":
        cp = p.get("component_percentiles") or {}
        if set(cp.keys()) != {"sg_approach", "app_150_200", "total_driving"}:
            bad_eligible.append(f"{p['player_id']}: got {set(cp.keys())}")
if not bad_eligible:
    ok("All ELIGIBLE players have exactly 3 component_percentiles")
else:
    fail(f"Wrong component_percentiles keys: {bad_eligible[:3]}")

# V6: Per-component eligibility gate — no non-eligible component can qualify
print("\nV6: Per-component eligibility gate")
v6_violations = []
for p in audit_players:
    payload_p = payload_players.get(p["player_id"], {})
    ta = payload_p.get("trait_availability") or {}
    for comp_key, avail_field in TRIPOD_AVAIL_MAP.items():
        entry = ta.get(avail_field) or {}
        usable = entry.get("usable_for_badges", False)
        if not usable:
            if p.get("tripod_qualified") is True:
                v6_violations.append(f"{p['player_id']}: {avail_field} not usable but tripod_qualified=True")
            if p.get("tripod_supported") is True:
                v6_violations.append(f"{p['player_id']}: {avail_field} not usable but tripod_supported=True")
            if p.get("tripod_eligibility") != "UNAVAILABLE":
                v6_violations.append(f"{p['player_id']}: {avail_field} not usable but tripod_eligibility={p.get('tripod_eligibility')!r}")
if not v6_violations:
    ok("No player with ineligible component marked qualified/supported/ELIGIBLE")
else:
    for v in v6_violations[:5]:
        fail(v)

# V7: UNSCORED players have null qualification
print("\nV7: UNSCORED player handling")
v7_issues = []
for p in audit_players:
    payload_p = payload_players.get(p["player_id"], {})
    if payload_p.get("data_depth") == "UNSCORED":
        if p.get("tripod_qualified") is not None:
            v7_issues.append(f"UNSCORED {p['player_id']} has non-null tripod_qualified")
        if p.get("tripod_supported") is not None:
            v7_issues.append(f"UNSCORED {p['player_id']} has non-null tripod_supported")
        if p.get("tripod_eligibility") != "UNAVAILABLE":
            v7_issues.append(f"UNSCORED {p['player_id']} has eligibility: {p.get('tripod_eligibility')!r}")
if not v7_issues:
    ok("All UNSCORED players have UNAVAILABLE eligibility and null qualification")
else:
    for v in v7_issues:
        fail(v)

# V8: UNAVAILABLE count
print("\nV8: UNAVAILABLE count")
unavailable = [p for p in audit_players if p.get("tripod_eligibility") == "UNAVAILABLE"]
if len(unavailable) == 10:
    ok("10 UNAVAILABLE (5 unscored + 5 zero-filled)")
else:
    fail(f"Expected 10 UNAVAILABLE, got {len(unavailable)}")

# V9: T2G gate is null for all players
print("\nV9: T2G gate is null for all players")
t2g_non_null = [p for p in audit_players
                if p.get("t2g_no_red_flag") is True or p.get("t2g_no_red_flag") is False]
if not t2g_non_null:
    ok("t2g_no_red_flag is null for all 147 players")
else:
    fail(f"{len(t2g_non_null)} players have non-null t2g_no_red_flag (arg_true not in payload)")

# V10: Zero-impact fields on every record
print("\nV10: Zero-impact fields")
bad_effect = []
for p in audit_players:
    if p.get("current_engine_effect") != "NONE":
        bad_effect.append(f"{p['player_id']}: current_engine_effect={p.get('current_engine_effect')!r}")
    if p.get("proposed_v2_effect") != "NONE — NOT ACTIVE":
        bad_effect.append(f"{p['player_id']}: proposed_v2_effect={p.get('proposed_v2_effect')!r}")
if not bad_effect:
    ok("All records have correct zero-impact fields")
else:
    fail(f"Wrong effect fields on {len(bad_effect)//2} player(s): {bad_effect[:4]}")

# V11: Eligible count
print("\nV11: Eligible count")
eligible = [p for p in audit_players if p.get("tripod_eligibility") == "ELIGIBLE"]
if len(eligible) == 137:
    ok("137 ELIGIBLE players")
else:
    fail(f"Expected 137 ELIGIBLE, got {len(eligible)}")

# V12: Qualified players have non-null component percentiles
print("\nV12: Qualified players have complete component data")
for p in audit_players:
    if p.get("tripod_qualified") is True:
        cp = p.get("component_percentiles") or {}
        if not all(cp.get(k) is not None for k in ("sg_approach", "app_150_200", "total_driving")):
            fail(f"{p['player_id']} tripod_qualified but missing component percentile(s): {cp}")
ok("All tripod_qualified players have complete component percentiles")

# Summary
total_qualified = sum(1 for p in audit_players if p.get("tripod_qualified") is True)
total_supported = sum(1 for p in audit_players if p.get("tripod_supported") is True)

print(f"\n{'='*48}")
print(f"Total field records:  {len(audit_players)}")
print(f"Eligible:             {len(eligible)}")
print(f"Tripod-qualified:     {total_qualified}")
print(f"Tripod-supported:     {total_supported}")
print(f"Unavailable:          {len(unavailable)}")

if failures:
    print(f"\nRESULT: FAILED ({len(failures)} failure(s))")
    for f_ in failures:
        print(f"  - {f_}")
    sys.exit(1)
else:
    print(f"\nRESULT: PASSED — all 12 audit gates")
    sys.exit(0)
