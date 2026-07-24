"""
join_r1_scores.py — one-off data join, NOT a model-logic change.

Adds real, already-official Round 1 scoring fields (position, score, thru,
total-to-par) from the raw leaderboard CSV onto the existing live-round
payload, and computes a simple vts_delta (live_vts - vts_final) so the
frontend can flag players outperforming/underperforming their pre-tournament
projection. No trait weights, venue weights, or model coefficients are
touched or invented — this is pure data plumbing.

Usage:
    python scripts/join_r1_scores.py --event 2026_3m_open --round 1
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


_MANUAL_FOLD = {"ø": "o", "Ø": "O", "đ": "d", "Đ": "D", "ł": "l", "Ł": "L"}


def norm(name: str) -> str:
    for src, dst in _MANUAL_FOLD.items():
        name = name.replace(src, dst)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"[.\-']", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name


def to_first_last(payload_name: str) -> str:
    """'Scheffler, Scottie' -> 'Scottie Scheffler'"""
    if "," in payload_name:
        last, first = payload_name.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return payload_name.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", required=True)
    ap.add_argument("--round", type=int, default=1)
    args = ap.parse_args()

    event_dir = ROOT / "events" / args.event
    lb_path = event_dir / "output" / f"round{args.round}" / f"round{args.round}_leaderboard.csv"
    payload_path = event_dir / "deploy" / "data" / f"{args.event}_rd{args.round}_payload.json"

    if not lb_path.exists():
        raise SystemExit(f"ERROR: missing {lb_path}")
    if not payload_path.exists():
        raise SystemExit(f"ERROR: missing {payload_path}")

    lookup: dict[str, dict] = {}
    with open(lb_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[norm(row["PLAYER"])] = {
                "r1_position": row["POS"],
                "r1_to_par": row["TOTAL"],
                "r1_thru": row["THRU"],
                "r1_score": int(row["R1"]) if row["R1"].strip().isdigit() else None,
            }

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    matched, unmatched = 0, []
    for p in payload["players"]:
        key = norm(to_first_last(p["player"]))
        rec = lookup.get(key)
        if rec:
            p.update(rec)
            matched += 1
            live_vts = p.get("live_vts")
            vts_final = p.get("vts_final")
            if isinstance(live_vts, (int, float)) and isinstance(vts_final, (int, float)):
                p["vts_delta"] = round(live_vts - vts_final, 2)
                if p["vts_delta"] >= 3:
                    p["form_signal"] = "outperforming"
                elif p["vts_delta"] <= -3:
                    p["form_signal"] = "underperforming"
                else:
                    p["form_signal"] = "in_line"
        else:
            unmatched.append(p["player"])
            p["r1_position"] = None
            p["r1_to_par"] = None
            p["r1_thru"] = None
            p["r1_score"] = None

    payload["r1_scores_joined_at"] = json.dumps(None)  # placeholder, replaced below
    from datetime import datetime, timezone
    payload["r1_scores_joined_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Matched {matched}/{len(payload['players'])} players.")
    if unmatched:
        print("UNMATCHED (needs manual name-map check):")
        for n in unmatched:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
