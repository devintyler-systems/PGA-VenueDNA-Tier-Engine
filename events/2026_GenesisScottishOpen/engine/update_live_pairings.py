"""
VenueDNA — Genesis Scottish Open 2026
update_live_pairings.py

Reads R1 tee-time pairings from input/r1_pairings.csv and writes the
tee_time field for each matched player into deploy/data/event_payload.json.

Expected CSV columns (case-insensitive, flexible):
  player_name  OR  last_name + first_name
  tee_time     — string, e.g. "07:35", "07:35 AM", "08:00 (Local)"

Run:
  python engine/update_live_pairings.py

After running, the frontend renderTierAlert() will detect any non-TBD
tee_time and flip the banner to "Round 1 Tee Times Live".
"""

import json, re
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
INPUT  = ROOT / "input"
OUTPUT = ROOT / "deploy" / "data"

PAIRINGS_CSV = INPUT / "r1_pairings.csv"
PAYLOAD_JSON = OUTPUT / "event_payload.json"

# ── name normalisation ────────────────────────────────────────────────────────
_STRIP = re.compile(r"[^a-z0-9 ]")

def norm(name: str) -> str:
    return _STRIP.sub("", name.lower().strip())

def name_key(raw: str) -> str:
    """'McIlroy, Rory' or 'Rory McIlroy' → canonical normalised string."""
    raw = raw.strip()
    if "," in raw:
        parts = raw.split(",", 1)
        return norm(parts[1]) + " " + norm(parts[0])
    return norm(raw)

# ── load pairings CSV ─────────────────────────────────────────────────────────
if not PAIRINGS_CSV.exists():
    raise FileNotFoundError(
        f"Pairings CSV not found: {PAIRINGS_CSV}\n"
        "Create input/r1_pairings.csv with columns: player_name, tee_time"
    )

import csv

pairings: dict[str, str] = {}
with open(PAIRINGS_CSV, newline="", encoding="utf-8-sig") as fh:
    reader = csv.DictReader(fh)
    cols = [c.strip().lower() for c in (reader.fieldnames or [])]
    reader.fieldnames = cols

    has_combined = "player_name" in cols
    has_split    = ("last_name" in cols) and ("first_name" in cols)
    if not (has_combined or has_split):
        raise ValueError("CSV must have 'player_name' OR 'last_name'+'first_name' columns")
    if "tee_time" not in cols:
        raise ValueError("CSV must have a 'tee_time' column")

    for row in reader:
        if has_combined:
            raw = row.get("player_name", "").strip()
        else:
            raw = f"{row.get('first_name','').strip()} {row.get('last_name','').strip()}"
        tee = row.get("tee_time", "").strip()
        if raw and tee:
            pairings[name_key(raw)] = tee

print(f"Loaded {len(pairings)} pairings from {PAIRINGS_CSV.name}")

# ── load existing payload ─────────────────────────────────────────────────────
with open(PAYLOAD_JSON, encoding="utf-8") as fh:
    payload = json.load(fh)

players = payload.get("players", [])

# ── match and update ──────────────────────────────────────────────────────────
matched = 0
unmatched = []

for p in players:
    last  = p.get("last_name",  "")
    first = p.get("first_name", "")
    full_key = name_key(f"{first} {last}")

    tee = pairings.get(full_key)
    if tee is None:
        # Try last-name-only fallback
        last_norm = norm(last)
        tee = next((v for k, v in pairings.items() if last_norm in k), None)

    if tee:
        p["tee_time"] = tee
        matched += 1
    else:
        p.setdefault("tee_time", "TBD")
        unmatched.append(f"{first} {last}")

# ── write back ────────────────────────────────────────────────────────────────
with open(PAYLOAD_JSON, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, ensure_ascii=False)

print(f"Updated event_payload.json — {matched}/{len(players)} players matched")
if unmatched:
    print(f"Unmatched ({len(unmatched)}): {', '.join(unmatched[:15])}"
          + (" …" if len(unmatched) > 15 else ""))
match_rate = matched / len(players) * 100 if players else 0
print(f"Match rate: {match_rate:.1f}%")
if match_rate < 85:
    print("WARNING: Match rate below 85% — check name formatting in r1_pairings.csv")
else:
    print("OK: Match rate >= 85%")
