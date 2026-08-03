"""Generate the final round payload for the 2026 3M Open board view.

Creates 2026_3m_open_final_payload.json by injecting tournament_complete
metadata into the pre-tournament event_payload. The board scores are based
on the final leaderboard — players are sorted by final position.

Usage: python events/2026_3m_open/engine/build_3m_final_payload.py
"""
import csv, json, re, unicodedata
from datetime import date
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent.parent.parent
EVENT  = BASE / 'events' / '2026_3m_open'
DEPLOY = EVENT / 'deploy' / 'data'
FINAL  = EVENT / 'output' / 'final_tournament'


def norm(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r'\s*\([^)]+\)', '', s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    if ',' in s:
        last, first = s.split(',', 1)
        s = f"{first.strip()} {last.strip()}"
    return ' '.join(s.lower().split())


def parse_pos(pos_str):
    p = str(pos_str or '').strip()
    if p in ('CUT', 'WD', 'DQ', '(a)', ''):
        return 9999
    try:
        return int(p.lstrip('T'))
    except ValueError:
        return 9999


# Load sources
with open(DEPLOY / '2026_3m_open_event_payload.json', encoding='utf-8') as f:
    payload = json.load(f)

lb_rows = []
with open(FINAL / 'final_leaderboard.csv', newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        lb_rows.append(row)

# Build final position lookup
lb_by_name = {}
for row in lb_rows:
    player = row.get('PLAYER', '')
    key = norm(player)
    lb_by_name[key] = {
        'final_pos': row.get('POS', ''),
        'final_pos_num': parse_pos(row.get('POS', '')),
        'total_score': row.get('TOTAL', ''),
        'cut_status': 'cut' if row.get('POS') in ('CUT', 'WD', 'DQ') else 'made',
    }

# Annotate each player with final position
players = payload.get('players', [])
for p in players:
    key = norm(p.get('player', ''))
    lb = lb_by_name.get(key, {})
    p['final_pos']      = lb.get('final_pos', '—')
    p['final_pos_num']  = lb.get('final_pos_num', 9999)
    p['final_score']    = lb.get('total_score', '—')
    p['cut_status']     = lb.get('cut_status', 'unknown')
    p['tournament_complete'] = True

# Inject tournament metadata
payload['tournament_complete'] = True
payload['is_final']            = True
payload['generated_at']        = date.today().isoformat()
payload['event_slug']          = '2026_3m_open'

out_path = DEPLOY / '2026_3m_open_final_payload.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, indent=2)

n_matched = sum(1 for p in players if p.get('final_pos') != '—')
print(f'[VenueDNA] Final payload written: {out_path}')
print(f'  Players: {len(players)} | matched to leaderboard: {n_matched}')
