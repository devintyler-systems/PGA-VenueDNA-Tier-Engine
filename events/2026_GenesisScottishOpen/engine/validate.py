import json, os
from collections import Counter

out = r'C:\PGA_VenueDNA\events\2026_GenesisScottishOpen\output'
with open(os.path.join(out, '2026_genesis_scottish_open_player_briefs.json')) as f:
    briefs = json.load(f)

check = ['Clark', 'Mcilroy', 'Scheffler', 'Fitzpatrick', 'Gotterup', 'Macintyre', 'Hovland', 'Schauffele', 'Fleetwood', 'Rahm']
for name in check:
    matches = [b for b in briefs if b['last_name'].lower() == name.lower()]
    if matches:
        b = matches[0]
        print(f"{b['first_name']:12s} {b['last_name']:15s} T{b['tier']} Rank {b['rank']:3d} VTS={b['vts_final']:5.1f} Win={b['win_prob']:4.1f}% T10={b['top10_prob']:4.1f}% MC={b['make_cut_prob']:4.1f}% Lane={b['best_betting_lane']}")
    else:
        print(f'NOT FOUND: {name}')

print()
tiers = Counter(b['tier'] for b in briefs)
print('Tier distribution:', dict(sorted(tiers.items())))
print()

ap_count = sum(1 for b in briefs if 'Anti-Pattern' in b.get('badges', []))
debut_count = sum(1 for b in briefs if 'Debut Watch' in b.get('badges', []))
ch_count = sum(1 for b in briefs if 'Course Horse' in b.get('badges', []))
print(f'Anti-Pattern badge: {ap_count}')
print(f'Debut Watch badge: {debut_count}')
print(f'Course Horse badge: {ch_count}')
print()

# Check decomposition for Clark
clark = [b for b in briefs if b['last_name'].lower() == 'clark'][0]
print('Clark decomposition:')
for k, v in clark['decomposition'].items():
    print(f'  {k}: {v}')
print()
print('Clark conviction statement:', clark['conviction_statement'])
print()
print('Clark top traits:', clark['top_traits'])
print('Clark drag traits:', clark['drag_traits'])
print('Clark risk vector:', clark['risk_vector'])
print()

# Check event payload structure
with open(os.path.join(out, '2026_genesis_scottish_open_event_payload.json')) as f2:
    payload = json.load(f2)
print('Payload keys:', list(payload.keys()))
print('Payload players count:', len(payload['players']))
print('Event name:', payload['event']['event_name'])
print('Venue:', payload['event']['venue'])
print('Field size:', payload['event']['field_size'])
print('Tier counts:', payload['event']['tier_counts'])
print()

# Sample Tier 3 dark horse entry
t3 = [b for b in briefs if b['tier'] == 3]
print(f'Tier 3 sample ({len(t3)} players):')
for b in t3[:3]:
    print(f"  {b['first_name']} {b['last_name']}: {b.get('dark_horse_mechanism', 'N/A')}")
