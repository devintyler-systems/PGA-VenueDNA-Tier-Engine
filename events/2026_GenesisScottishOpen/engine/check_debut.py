import json
with open('deploy/data/event_payload.json', encoding='utf-8') as f:
    data = json.load(f)
players = data['players']

print("=== Win Case fields — T1/T2 players ===")
print(f"{'Name':15s}  {'tier':4s}  {'start_count':11s}  {'rounds':6s}  {'bf':4s}  {'debut':5s}  expected_q2")
for p in players:
    tier = int(p.get('tier', 5) or 5)
    if tier > 2:
        continue
    rsc   = p.get('renaissance_start_count', 'MISSING')
    rounds= p.get('starts_at_renaissance', 0)
    bf    = p.get('best_finish_renaissance')
    deb   = p.get('debut_flag', False)
    name  = p.get('last_name', '?')
    # Simulate sectionWinCase Q2 logic
    starts = int(rsc) if isinstance(rsc, int) else 0
    if bf == 1:
        q2 = f"winner ({starts} starts)"
    elif bf and bf <= 5:
        q2 = f"Top-{bf} finish ({starts} starts)"
    elif starts >= 10:
        q2 = f"{starts} starts — deep familiarity"
    elif starts >= 4:
        q2 = f"{starts} starts — partial"
    elif starts >= 1:
        q2 = f"{starts} start(s) — limited"
    else:
        q2 = "DEBUT"
    print(f"{name:15s}  T{tier:1d}    {str(rsc):11s}  {rounds:6d}  {str(bf):4s}  {str(deb):5s}  {q2}")

print()
print("=== renaissance_start_count distribution ===")
from collections import Counter
dist = Counter(p.get('renaissance_start_count', 'MISSING') for p in players)
for k, v in sorted(dist.items()):
    print(f"  {k}: {v} players")
