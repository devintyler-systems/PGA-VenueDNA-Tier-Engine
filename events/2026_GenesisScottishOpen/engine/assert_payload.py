"""
VenueDNA — GSO 2026
assert_payload.py

Runs assertion checks on deploy/data/event_payload.json:
  A1 — every player has a tee_time field
  A2 — no player with vts_final >= 70.0 has 'Solid cut maker' in scoring.band
  A3 — no stale SG:APP/SG:OTT/SG:ARG/'over 12m' labels in top_traits/drag_traits
  A4 — every player has scoring.band set
"""

import json, sys
from pathlib import Path
from collections import Counter

ROOT    = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "deploy" / "data" / "event_payload.json"

with open(PAYLOAD, encoding="utf-8") as f:
    data = json.load(f)

players = data.get("players", [])
print(f"Players loaded: {len(players)}\n")

errors = []

# A1: every player has tee_time field
missing_tee = [p.get("last_name", "?") for p in players if "tee_time" not in p]
if missing_tee:
    errors.append(f"FAIL A1 — missing tee_time ({len(missing_tee)}): {missing_tee}")
else:
    print(f"PASS A1 — All {len(players)} players have tee_time field")

# A2: no VTS>=70 player has 'Solid cut maker' band
violations = []
for p in players:
    vts  = float(p.get("vts_final", 0) or 0)
    band = p.get("scoring", {}).get("band", "")
    if vts >= 70.0 and "Solid cut maker" in band:
        violations.append(f"  {p.get('last_name','?')} VTS={vts:.1f}  band={band!r}")

if violations:
    errors.append(f"FAIL A2 — Solid cut maker tier-override violations ({len(violations)}):")
    errors.extend(violations)
else:
    n70 = sum(1 for p in players if float(p.get("vts_final", 0) or 0) >= 70.0)
    print(f"PASS A2 — No VTS>=70 player (n={n70}) has 'Solid cut maker' band")

# A3: no stale labels in top_traits / drag_traits
STALE = ["SG:APP", "SG:OTT", "SG:ARG", "over 12m", "SG:PUTT over", "12-month SG:"]
stale_hits = []
for p in players:
    for field in ("top_traits", "drag_traits"):
        for val in p.get(field, []):
            for pat in STALE:
                if pat in str(val):
                    stale_hits.append(f"  {p.get('last_name','?')} [{field}]: {val!r}")
                    break

if stale_hits:
    errors.append(f"FAIL A3 — Stale labels in trait strings ({len(stale_hits)} hits):")
    errors.extend(stale_hits[:10])
    if len(stale_hits) > 10:
        errors.append(f"  ... and {len(stale_hits)-10} more")
else:
    print("PASS A3 — No stale SG:APP/OTT/ARG or 'over 12m' in top/drag_traits")

# A4: every player has scoring.band
missing_band = [p.get("last_name", "?") for p in players if not p.get("scoring", {}).get("band")]
if missing_band:
    errors.append(f"FAIL A4 — missing scoring.band ({len(missing_band)}): {missing_band[:10]}")
else:
    print(f"PASS A4 — All {len(players)} players have scoring.band")

# Band distribution
print("\nBand distribution:")
bands = Counter(p.get("scoring", {}).get("band", "MISSING") for p in players)
for band, cnt in sorted(bands.items(), key=lambda x: -x[1]):
    print(f"  {cnt:3d}  {band}")

# Sample top-tier narrative labels
print("\nSample top_traits (first 3 T1/T2 players):")
shown = 0
for p in players:
    tier = int(p.get("pt_tier", p.get("tier", 5)) or 5)
    if tier <= 2 and shown < 3:
        print(f"  {p.get('last_name','?')} T{tier}: {p.get('top_traits', [])}")
        shown += 1

print()
if errors:
    print("=== ASSERTION FAILURES ===")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("=== ALL ASSERTIONS PASSED ===")
