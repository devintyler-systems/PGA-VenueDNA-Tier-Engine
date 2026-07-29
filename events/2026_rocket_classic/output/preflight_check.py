"""
preflight_check.py
Preflight validation — runs BEFORE the audit companion is generated.
Verifies frozen payload integrity and source prerequisites.
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
VENUE_INTEL    = REPO_ROOT / "library/venues/detroit_golf_club/detroit_golf_club_intelligence_2026_v1.json"
EXPECTED_HASH  = "f132e9616fe70ab679bd68e8fb2c98e41c237f22b4db4b63b8df7db5ae051c57"

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

print("=== Rocket Classic Preflight Check ===\n")

# V0: Frozen payload hashes
print("V0: Frozen payload hash integrity")
for path in [PAYLOAD_DEPLOY, PAYLOAD_OUTPUT]:
    with open(path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    if h == EXPECTED_HASH:
        ok(f"{path.name} hash matches")
    else:
        fail(f"{path.name} hash CHANGED: {h}")

# Load payload
with open(PAYLOAD_DEPLOY) as f:
    payload = json.load(f)

# V1: Schema version
print("\nV1: Schema version")
sv = payload.get("schemaVersion", "")
if sv == "rocket-classic-v1.4":
    ok(f"schemaVersion: {sv}")
else:
    fail(f"schemaVersion wrong: {sv!r}")

# V2: Player count
print("\nV2: Player count")
players = payload.get("players", [])
if len(players) == 147:
    ok("147 player records")
else:
    fail(f"Expected 147 players, got {len(players)}")

# V3: All player_ids present
print("\nV3: player_id presence")
missing_pid = [i for i, p in enumerate(players) if not p.get("player_id")]
if not missing_pid:
    ok("All records have player_id")
else:
    fail(f"Missing player_id at indices: {missing_pid}")

# V4: Unique player_ids
print("\nV4: Unique player_ids")
pid_counts = Counter(p.get("player_id") for p in players)
dupes = {k: v for k, v in pid_counts.items() if v > 1}
if not dupes:
    ok("All player_ids unique")
else:
    fail(f"Duplicate player_ids: {dupes}")

# V5: UNSCORED count and null vts_final
print("\nV5: UNSCORED player count")
unscored = [p for p in players if p.get("data_depth") == "UNSCORED"]
if len(unscored) == 5:
    ok("5 UNSCORED players")
else:
    fail(f"Expected 5 UNSCORED, got {len(unscored)}")
for p in unscored:
    if p.get("vts_final") is not None:
        fail(f"UNSCORED {p['player_id']} has non-null vts_final: {p.get('vts_final')}")
ok("All UNSCORED players have null vts_final")

# V6: Zero-filled / ineligible scored players
print("\nV6: Zero-filled player source availability")
zero_filled = [
    p for p in players
    if p.get("data_depth") != "UNSCORED"
    and not (p.get("trait_availability") or {}).get("trait_approach_raw", {}).get("usable_for_badges", True)
]
if len(zero_filled) == 5:
    ok("5 zero-filled / reduced-confidence players")
else:
    fail(f"Expected 5 zero-filled players, got {len(zero_filled)}")

# V7: Per-component blocking on zero-filled players
print("\nV7: Per-component blocking of zero-filled players")
for p in zero_filled:
    ta = p.get("trait_availability") or {}
    for field in ("trait_approach_raw", "trait_long_iron_raw"):
        entry = ta.get(field, {})
        if entry.get("usable_for_badges", True):
            fail(f"{p['player_id']} ({p.get('player_name')}): {field} unexpectedly usable_for_badges=True")
ok("All zero-filled players blocked for approach_raw and long_iron_raw")

# Eligible count by per-component usable_for_badges gate
eligible = [
    p for p in players
    if p.get("data_depth") != "UNSCORED"
    and all(
        (p.get("trait_availability") or {}).get(f, {}).get("usable_for_badges", False)
        for f in TRIPOD_AVAIL_MAP.values()
    )
]
if len(eligible) == 137:
    ok("137 players fully tripod-eligible (all 3 components usable_for_badges=True)")
else:
    fail(f"Expected 137 tripod-eligible, got {len(eligible)}")

# V8: Venue intelligence
print("\nV8: Venue intelligence artifact")
if VENUE_INTEL.exists():
    with open(VENUE_INTEL) as f:
        vi = json.load(f)
    if vi.get("dominant_tripod_governance", {}).get("status") == "NOT_ACTIVE":
        ok("V2 governance is NOT_ACTIVE")
    else:
        fail(f"V2 governance status wrong: {vi.get('dominant_tripod_governance', {}).get('status')!r}")
    if vi.get("dominant_tripod", {}).get("scoring_impact") == "NONE":
        ok("V1 scoring_impact is NONE")
    else:
        fail("V1 scoring_impact not NONE")
else:
    fail(f"Venue intelligence file not found: {VENUE_INTEL}")

# Summary
print(f"\n{'='*48}")
if failures:
    print(f"PREFLIGHT: FAILED ({len(failures)} failure(s))")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"PREFLIGHT: PASSED — all prerequisites verified.")
    print(f"  Eligible pool: {len(eligible)} players")
    print(f"  Unscored:      {len(unscored)} players")
    print(f"  Zero-filled:   {len(zero_filled)} players")
    sys.exit(0)
