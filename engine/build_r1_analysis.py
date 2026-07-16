"""
build_r1_analysis.py — Round 1 convenience entry-point for VenueDNA pipeline.

Delegates to build_round_analysis.py with --round 1 so callers only need:
    python engine/build_r1_analysis.py --event 2026_the_open_championship

Outputs (via build_round_analysis.py, schema v1.1):
    events/<slug>/output/<slug>_r1_analysis.json
    events/<slug>/deploy/data/r1_analysis.json
    events/<slug>/deploy/data/cumulative_learning.json

The delegated script enforces all v1.1 canonical keys:
    schema_version, round, event_slug, metadata, match_summary (total_r1),
    model_performance (r1-prefixed group stats), trait_audit, live_lean_notes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(
    description="VenueDNA R1 analysis builder (delegates to build_round_analysis.py)"
)
parser.add_argument(
    "--event", "--event_slug",
    dest="event",
    required=True,
    help="Event slug, e.g. 2026_the_open_championship",
)
parser.add_argument(
    "--check",
    action="store_true",
    help="Validate inputs only — no build (passed through to build_round_analysis.py)",
)
args = parser.parse_args()

cmd = [
    sys.executable,
    str(Path(__file__).resolve().parent / "build_round_analysis.py"),
    "--round", "1",
    "--event_slug", args.event,
]
if args.check:
    cmd.append("--check")

sys.exit(subprocess.call(cmd))
