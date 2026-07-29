"""
validate_badge_emission.py
Release gate: verifies badge emission integrity in the Rocket Classic event artifact.
Exits 0 on full pass, 1 on any failure.
Run: python events/2026_rocket_classic/output/validate_badge_emission.py
"""
import json, sys
from collections import Counter
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent.parent.parent.parent
PAYLOAD_PATH = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_event_payload.json"
POLICY_PATH  = REPO_ROOT / "config/badge_policy.v1.json"


def validate_payload(payload: dict, policy_badges: list[dict]) -> list[str]:
    errors: list[str] = []

    # G5: policy badge_id uniqueness
    policy_ids = [b["badge_id"] for b in policy_badges]
    for bid, cnt in Counter(policy_ids).items():
        if cnt > 1:
            errors.append(f"[G5] Duplicate badge_id in policy: '{bid}' appears {cnt} times")
    valid_ids = set(policy_ids)

    players = payload.get("players", [])
    scored  = [p for p in players if p.get("data_depth") != "UNSCORED"]

    for p in scored:
        pid = p.get("player_id", "?")
        if "badges" not in p:
            errors.append(f"[G2] Player {pid}: 'badges' field missing")
            continue
        if not isinstance(p["badges"], list):
            errors.append(f"[G2] Player {pid}: 'badges' is not a list (got {type(p['badges']).__name__})")
            continue
        for entry in p["badges"]:
            if not isinstance(entry, dict):
                errors.append(f"[G2] Player {pid}: badge entry is not a dict: {entry!r}")
                continue
            bid    = entry.get("badge_id", "")
            reason = entry.get("qualification_reason", None)
            if not bid:
                errors.append(f"[G2] Player {pid}: badge entry missing badge_id")
            elif bid not in valid_ids:
                errors.append(f"[G3] Player {pid}: unknown badge_id '{bid}' not in policy")
            if reason is None or not str(reason).strip():
                errors.append(f"[G4] Player {pid}: badge '{bid}' has empty/missing qualification_reason")

    if scored:
        total = sum(len(p["badges"]) for p in scored if isinstance(p.get("badges"), list))
        if total == 0:
            errors.append(
                f"[G1] {len(scored)} scored player(s) but zero total badges emitted — "
                "badge qualification is required before release"
            )

    return errors


def main() -> None:
    print("=== Badge Emission Release Gate ===\n")

    for label, path in [("Payload", PAYLOAD_PATH), ("Policy", POLICY_PATH)]:
        if not path.exists():
            print(f"FAIL [G6]: {label} not found: {path}")
            sys.exit(1)

    try:
        payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL [G6]: Cannot parse payload: {e}"); sys.exit(1)

    try:
        policy_badges = json.loads(POLICY_PATH.read_text(encoding="utf-8")).get("badges", [])
    except Exception as e:
        print(f"FAIL [G6]: Cannot parse policy: {e}"); sys.exit(1)

    errors = validate_payload(payload, policy_badges)

    if errors:
        print(f"FAILED ({len(errors)} error(s)):\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    scored = [p for p in payload.get("players", []) if p.get("data_depth") != "UNSCORED"]
    total  = sum(len(p.get("badges", [])) for p in scored)
    print(f"PASSED — {total} badge(s) emitted across {len(scored)} scored players")
    sys.exit(0)


if __name__ == "__main__":
    main()
