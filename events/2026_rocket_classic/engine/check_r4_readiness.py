"""
check_r4_readiness.py — readiness gate for the R4 live-layer build.

Checks whether the four result files build_live_r4.py needs actually exist in
output/round4/ yet. Read-only: touches nothing, builds nothing. Run this before
starting any R4 build work; only proceed to copy build_live_r3.py -> build_live_r4.py
once this reports READY.

Exits 0 if ready, 1 if not.

Usage:
    python check_r4_readiness.py
"""

from __future__ import annotations

from pathlib import Path

EVENT_DIR = Path(__file__).resolve().parent.parent
ROUND4_DIR = EVENT_DIR / "output" / "round4"

REQUIRED_RESULT_FILES = [
    "round4_leaderboard.csv",
    "round4_player_strokes_gained.csv",
    "live_stats_r4_values.csv",
    "round4_course_stats.csv",
]

# Present since R3 built its lookahead section — not sufficient on their own.
KNOWN_LOOKAHEAD_FILES = [
    "detroit_golf_club_r4_weather_data_2026.json",
    "pga_field_r4_teetimes.csv",
]


def main() -> int:
    print("=== R4 Live-Layer Readiness Check ===\n")

    missing = []
    present = []
    for name in REQUIRED_RESULT_FILES:
        path = ROUND4_DIR / name
        if path.exists() and path.stat().st_size > 0:
            present.append(name)
            print(f"  OK:      {name} ({path.stat().st_size} bytes)")
        else:
            missing.append(name)
            print(f"  MISSING: {name}")

    print()
    for name in KNOWN_LOOKAHEAD_FILES:
        path = ROUND4_DIR / name
        status = "present (lookahead only, not a result file)" if path.exists() else "missing"
        print(f"  info:    {name} — {status}")

    print()
    if missing:
        print(f"NOT READY — {len(missing)}/{len(REQUIRED_RESULT_FILES)} result file(s) missing.")
        print("Do not start build_live_r4.py until all four result files above are OK.")
        return 1

    print("READY — all four R4 result files are present and non-empty.")
    print("Next: inspect each file's actual column layout/encoding before writing any")
    print("R4-specific parsing logic. Do not assume R3's shape carries forward.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
