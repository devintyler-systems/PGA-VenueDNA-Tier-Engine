"""3M Open 2026 Post-Mortem compiler.

Adapted from engine/build_post_mortem.py to match 3M Open source data format:
  - final_leaderboard.csv   (POS, PLAYER, TOTAL, RD1-RD4, STROKES)
  - final_player_strokes_gained.csv  (Player, SG-OTT/APP/ARG/PUTT/Total)
  - 2026_3m_open_board_export.json   (pre-tournament model)
  - deploy/data/r1_analysis.json     (wave data)
  - round3/round3_player_strokes_gained.csv  (cumulative R1-R3 SG for SRVI)

Usage: python events/2026_3m_open/engine/build_3m_post_mortem.py
"""
import csv, json, math, re, unicodedata
from datetime import date
from pathlib import Path

BASE      = Path(__file__).resolve().parent.parent.parent.parent
EVENT     = BASE / 'events' / '2026_3m_open'
FINAL_DIR = EVENT / 'output' / 'final_tournament'
DEPLOY    = EVENT / 'deploy' / 'data'
R3_DIR    = EVENT / 'output' / 'round3'

PAR           = 71
SLUG          = '2026_3m_open'
SRVI_THRESH   = 6.0


# ── Name normalisation ─────────────────────────────────────────────────────────

def norm(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r'\s*\([^)]+\)', '', s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    if ',' in s:
        last, first = s.split(',', 1)
        s = f"{first.strip()} {last.strip()}"
    return ' '.join(s.lower().split())


def safe_float(row, col):
    try:
        v = (row or {}).get(col, '') or ''
        return float(v) if str(v).lower() not in ('null', '', 'nan', '-', '—') else None
    except (ValueError, TypeError):
        return None


def parse_pos(pos_str: str):
    p = str(pos_str or '').strip()
    if p in ('CUT', 'WD', 'DQ', '(a)', ''):
        return None
    try:
        return int(p.lstrip('T'))
    except ValueError:
        return None


def pearson_corr(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num  = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denom = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / denom if denom > 0 else 0.0


def spearman_rho(xs, ys):
    indexed_x = sorted(enumerate(xs), key=lambda t: t[1])
    rx = [0] * len(xs)
    for rank, (idx, _) in enumerate(indexed_x, 1):
        rx[idx] = rank
    indexed_y = sorted(enumerate(ys), key=lambda t: t[1])
    ry = [0] * len(ys)
    for rank, (idx, _) in enumerate(indexed_y, 1):
        ry[idx] = rank
    return pearson_corr(rx, ry)


def classify_trait(rho: float) -> str:
    if rho <= -0.30:
        return 'validated'
    if rho <= -0.10:
        return 'mixed'
    if rho <= 0.10:
        return 'neutral'
    return 'weak'


# ── Load sources ───────────────────────────────────────────────────────────────

def load_csv(path):
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(path, newline='', encoding=enc) as f:
                rows = list(csv.DictReader(f))
            if rows:
                return rows
        except Exception:
            continue
    return []


print('[VenueDNA] Building 3M Open post-mortem...')

lb_rows  = load_csv(FINAL_DIR / 'final_leaderboard.csv')
sg_rows  = load_csv(FINAL_DIR / 'final_player_strokes_gained.csv')
r3_sg    = load_csv(R3_DIR    / 'round3_player_strokes_gained.csv')

with open(DEPLOY / '2026_3m_open_board_export.json', encoding='utf-8') as f:
    board_data = json.load(f)['players']

r1_data = {}
r1_path = DEPLOY / 'r1_analysis.json'
if r1_path.exists():
    with open(r1_path, encoding='utf-8') as f:
        r1_data = json.load(f)

print(f'  Leaderboard: {len(lb_rows)} rows')
print(f'  Final SG:    {len(sg_rows)} rows')
print(f'  R3 SG:       {len(r3_sg)} rows')
print(f'  Board:       {len(board_data)} players')

# ── Build lookup dicts ─────────────────────────────────────────────────────────

lb_by_name   = {norm(r.get('PLAYER', r.get('player', ''))): r for r in lb_rows if r.get('PLAYER') or r.get('player')}
sg_by_name   = {norm(r.get('Player', '')): r for r in sg_rows if r.get('Player')}
r3sg_by_name = {norm(r.get('Player', '')): r for r in r3_sg   if r.get('Player')}

wave_by_name = {}
for snap in r1_data.get('leaderboard_snapshot', []):
    key = norm(snap.get('r1_name', ''))
    if key:
        wave_by_name[key] = {'wave': snap.get('wave'), 'wave_penalty': snap.get('wave_penalty', 0)}

# ── Player comparison table ───────────────────────────────────────────────────

player_comparison = []

for p in board_data:
    raw_name = p.get('player', '')
    key = norm(raw_name)
    lb  = lb_by_name.get(key)
    if not lb:
        continue

    pos_str    = lb.get('POS', '')
    final_pos  = parse_pos(pos_str)
    cut_status = 'cut' if pos_str in ('CUT', 'WD', 'DQ') else 'made'
    pt_rank    = p.get('rank')

    sg = sg_by_name.get(key) or {}
    # Parse SG columns
    sg_ott  = safe_float(sg, 'SG-Off the Tee')
    sg_app  = safe_float(sg, 'SG-Approach to Green')
    sg_arg  = safe_float(sg, 'SG-Around the Green') or safe_float(sg, 'SG- Around the Green')
    sg_putt = safe_float(sg, 'SG-Putting')
    sg_tot  = safe_float(sg, 'SG Total') or safe_float(sg, 'SG-Total')

    prediction_delta = (pt_rank - final_pos) if (pt_rank and final_pos) else None

    # Canonical display name: convert "Last, First" → "First Last"
    if ',' in raw_name:
        last, first = raw_name.split(',', 1)
        display_name = f"{first.strip()} {last.strip()}"
    else:
        display_name = raw_name

    player_comparison.append({
        'player_name':       display_name,
        'player_id':         p.get('player_id'),
        'pt_rank':           pt_rank,
        'pt_tier':           p.get('tier'),
        'pt_vts':            p.get('vts_final'),
        'final_pos':         pos_str,
        'final_pos_numeric': final_pos,
        'total_sg':          sg_tot,
        'sg_app':            sg_app,
        'sg_putt':           sg_putt,
        'sg_ott':            sg_ott,
        'sg_arg':            sg_arg,
        'prediction_delta':  prediction_delta,
        'cut_status':        cut_status,
    })

player_comparison.sort(key=lambda r: (
    0 if r['cut_status'] == 'made' else 1,
    r['final_pos_numeric'] if r['final_pos_numeric'] is not None else 9999,
))
print(f'  Player comparison: {len(player_comparison)} rows')

# ── Spearman ρ: pt_rank vs final position ────────────────────────────────────

pairs_pos = [(r['pt_rank'], r['final_pos_numeric'])
             for r in player_comparison
             if r['cut_status'] == 'made' and r['pt_rank'] and r['final_pos_numeric']]
rho_pos = spearman_rho([p[0] for p in pairs_pos], [p[1] for p in pairs_pos]) if pairs_pos else 0.0

pairs_sg  = [(r['pt_rank'], r['total_sg'])
             for r in player_comparison
             if r['cut_status'] == 'made' and r['pt_rank'] and r['total_sg'] is not None]
rho_sg = spearman_rho([p[0] for p in pairs_sg], [-p[1] for p in pairs_sg]) if pairs_sg else 0.0

print(f'  Spearman rho (rank vs pos): {rho_pos:.3f}')
print(f'  Spearman rho (rank vs SG):  {rho_sg:.3f}')

# ── Tier hit rates ─────────────────────────────────────────────────────────────

tier_hit_rates = {}
for tier in ('T1', 'T2', 'T3', 'T4', 'T5'):
    tp = [r for r in player_comparison if r['pt_tier'] == tier]
    n  = len(tp)
    if n == 0:
        continue
    n10  = sum(1 for r in tp if r['final_pos_numeric'] and r['final_pos_numeric'] <= 10)
    n20  = sum(1 for r in tp if r['final_pos_numeric'] and r['final_pos_numeric'] <= 20)
    ncut = sum(1 for r in tp if r['cut_status'] == 'made')
    tier_hit_rates[tier] = {
        'player_count': n, 'top10_count': n10, 'top20_count': n20, 'cut_count': ncut,
        'top10_pct': round(n10 / n, 3), 'top20_pct': round(n20 / n, 3), 'cut_pct': round(ncut / n, 3),
    }

# ── Trait audit (Spearman ρ using final SG data) ──────────────────────────────

TRAIT_DEFS = [
    ('app_overall',  'Approach Play',       'SG-Approach to Green'),
    ('putting',      'Putting',             'SG-Putting'),
    ('arg_overall',  'Around the Green',    'SG-Around the Green'),
    ('ott_total',    'Off the Tee SG',      'SG-Off the Tee'),
    ('t2g',          'Tee to Green',        'SG Total'),
]

made_cut = [r for r in player_comparison if r['cut_status'] == 'made']

trait_audit = []
for trait_key, label, sg_col in TRAIT_DEFS:
    pairs = []
    for r in made_cut:
        key  = norm(r['player_name'])
        sg_r = sg_by_name.get(key, {})
        v    = safe_float(sg_r, sg_col)
        if v is not None and r['final_pos_numeric']:
            pairs.append((r['final_pos_numeric'], v))
    if len(pairs) < 5:
        trait_audit.append({'trait': trait_key, 'label': label, 'status': 'neutral', 'spearman_rho': None})
        continue
    rho_t = spearman_rho([p[0] for p in pairs], [p[1] for p in pairs])
    trait_audit.append({'trait': trait_key, 'label': label, 'status': classify_trait(rho_t), 'spearman_rho': round(rho_t, 3)})

# ── SRVI: per-round score vs par (proxy for single-round SG spike) ───────────
# Uses RD1-RD4 columns from final_leaderboard.csv as par-relative proxy.
# SRVI_THRESH of 6.0 SG ≈ shooting 65 or better (71-65=6).

srvi_spikes = []
for lb in lb_rows:
    pos_str = lb.get('POS', '')
    final_pos = parse_pos(pos_str)
    if final_pos is None:
        continue
    player_name = lb.get('PLAYER', '')
    if ',' in player_name:
        last, first = player_name.split(',', 1)
        player_name = f"{first.strip()} {last.strip()}"
    for rnd_num, col in ((1, 'RD1'), (2, 'RD2'), (3, 'RD3'), (4, 'RD4')):
        score = safe_float(lb, col)
        if score is None:
            continue
        sg_proxy = PAR - score
        if sg_proxy >= SRVI_THRESH:
            is_winner = pos_str == '1'
            srvi_spikes.append({
                'player':    player_name,
                'round':     rnd_num,
                'sg':        round(sg_proxy, 2),
                'final_pos': pos_str,
                'winner':    is_winner,
                'badge':     'Volatility Spike Winner' if is_winner else None,
            })

srvi_spikes.sort(key=lambda s: (-s['sg'], s['round']))

# ── Wave draw impact ──────────────────────────────────────────────────────────

favored_wave = r1_data.get('metadata', {}).get('favored_wave', 'early_late')
wave_pairs   = []
for r in player_comparison:
    key = norm(r['player_name'])
    wv  = wave_by_name.get(key, {})
    lb  = lb_by_name.get(key)
    if not lb or parse_pos(lb.get('POS', 'CUT')) is None:
        continue
    sg  = r.get('total_sg')
    if sg is None:
        continue
    wave_flag = 0 if wv.get('wave') == favored_wave else 1
    wave_pairs.append((wave_flag, sg))

wave_corr = None
if len(wave_pairs) >= 5:
    wave_corr = round(pearson_corr([p[0] for p in wave_pairs], [p[1] for p in wave_pairs]), 3)

# ── Summary stats ──────────────────────────────────────────────────────────────

winner_row  = next((r for r in player_comparison if r['final_pos_numeric'] == 1), None)
n_made_cut  = sum(1 for r in player_comparison if r['cut_status'] == 'made')

output = {
    'schema_version':     '1.1',
    'generated_at':       date.today().isoformat(),
    'event_slug':         SLUG,
    'tournament_complete': True,
    'spearman_rho':       round(rho_pos, 3),
    'spearman_rho_vs_sg': round(rho_sg,  3),
    'tier_hit_rates':     tier_hit_rates,
    'trait_audit':        trait_audit,
    'single_round_volatility': {
        'threshold': SRVI_THRESH,
        'note':      'Spike threshold = par-relative proxy (par-score >= 6.0). Not per-round SG.',
        'spikes':    srvi_spikes,
    },
    'wave_penalty_correlation': {
        'correlation':  wave_corr,
        'favored_wave': favored_wave or None,
        'note': (
            f"Pearson correlation: disadvantaged wave (1) vs. total SG "
            f"over {len(wave_pairs)} matched players."
        ),
    },
    'player_comparison': player_comparison,
    'summary_stats': {
        'field_size':     len(lb_rows),
        'made_cut':       n_made_cut,
        'winner':         winner_row['player_name'] if winner_row else None,
        'winner_pt_rank': winner_row['pt_rank']     if winner_row else None,
    },
}

out_path = DEPLOY / 'post_mortem_analysis.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print(f'[VenueDNA] Post-mortem written: {out_path}')
print(f'  rho (rank vs pos): {rho_pos:.3f}')
print(f'  rho (rank vs SG):  {rho_sg:.3f}')
print(f'  Tier hit rates:    {list(tier_hit_rates.keys())}')
print(f'  SRVI spikes:       {len(srvi_spikes)}')
print(f'  Player rows:       {len(player_comparison)}')
print(f'  {n_made_cut}/{len(lb_rows)} made cut')
