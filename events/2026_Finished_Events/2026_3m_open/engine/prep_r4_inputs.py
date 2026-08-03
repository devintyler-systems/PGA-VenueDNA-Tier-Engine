"""Prepare Round 4 input files for the 2026 3M Open.

Copies final tournament source files to the round4/ folder with the naming
convention expected by engine/build_round_analysis.py --round 4.

Usage: python events/2026_3m_open/engine/prep_r4_inputs.py
"""
import shutil
from pathlib import Path

BASE  = Path(__file__).resolve().parent.parent.parent.parent  # C:\PGA_VenueDNA
EVENT = BASE / 'events' / '2026_3m_open'
FINAL = EVENT / 'output' / 'final_tournament'
R4    = EVENT / 'output' / 'round4'

R4.mkdir(parents=True, exist_ok=True)

copies = [
    (FINAL / 'final_leaderboard.csv',            R4 / 'round4_leaderboard.csv'),
    (FINAL / 'final_player_strokes_gained.csv',  R4 / 'round4_player_strokes_gained.csv'),
]

for src, dst in copies:
    if not src.exists():
        print(f'[ERROR] Source not found: {src}')
        raise SystemExit(1)
    shutil.copy2(src, dst)
    print(f'  {src.name} -> {dst}')

print('[VenueDNA] Round 4 input files staged.')
