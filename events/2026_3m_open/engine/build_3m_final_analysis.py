"""Generate final_analysis.json for the 2026 3M Open.

Produces the S.analysis artifact fetched on init (used for five_tier_summary
in the tier intelligence panel and completion metadata).

Usage: python events/2026_3m_open/engine/build_3m_final_analysis.py
"""
import json
from datetime import date
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent.parent.parent
EVENT  = BASE / 'events' / '2026_3m_open'
DEPLOY = EVENT / 'deploy' / 'data'

with open(DEPLOY / '2026_3m_open_board_export.json', encoding='utf-8') as f:
    board = json.load(f)

players = board.get('players', [])

# Group by tier
tier_map: dict[str, list] = {'T1': [], 'T2': [], 'T3': [], 'T4': [], 'T5': []}
for p in players:
    t = p.get('tier', 'T5')
    if t in tier_map:
        tier_map[t].append(p)

tier_descriptions = {
    'T1': 'Elite DNA — perfect venue match',
    'T2': 'High confidence — strong trait overlap',
    'T3': 'Moderate fit — multiple trait alignment',
    'T4': 'Fringe — partial fit or form-dependent',
    'T5': 'Mismatch or low data depth',
}

tier_leads = {}
for tier, group in tier_map.items():
    top3 = sorted(group, key=lambda p: p.get('rank', 999))[:3]
    # Convert "Last, First" → "First Last" for display
    leads = []
    for p in top3:
        raw = p.get('player', '')
        if ',' in raw:
            last, first = raw.split(',', 1)
            display = f"{first.strip()} {last.strip()}"
        else:
            display = raw
        leads.append({
            'rank':  p.get('rank'),
            'player': display,
            'vts':   p.get('vts_final'),
            'nsi':   p.get('neutralSkillIndex'),
            'vfs':   round((p.get('vts_final', 50) - 50) / 5, 1),
            'flags': [],
        })
    tier_leads[tier] = leads

tier_counts = {t: len(v) for t, v in tier_map.items()}

output = {
    'schema_version':      '1.1',
    'generated_at':        date.today().isoformat(),
    'event_slug':          '2026_3m_open',
    'tournament_complete': True,
    'is_final':            True,
    'five_tier_summary': {
        'tier_leads':        tier_leads,
        'tier_descriptions': tier_descriptions,
        'tier_counts':       tier_counts,
    },
}

out_path = DEPLOY / 'final_analysis.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print(f'[VenueDNA] final_analysis.json written: {out_path}')
for tier, cnt in tier_counts.items():
    leads_names = [p['player'] for p in tier_leads[tier]]
    print(f'  {tier}: {cnt} players, leads={leads_names}')
