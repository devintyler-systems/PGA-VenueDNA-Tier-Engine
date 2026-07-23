#!/usr/bin/env python3
"""Post-mortem compiler for PGA VenueDNA.
Usage: python engine/build_post_mortem.py --event 2026_the_open_championship
"""

import argparse
import csv
import json
import math
import re
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def normalize_name(name: str) -> str:
    """'Last, First' or 'First Last' → 'first last' for dict keying."""
    name = name.strip()
    name = re.sub(r'\s*\([^)]+\)', '', name)
    if ',' in name:
        last, first = name.split(',', 1)
        name = f"{first.strip()} {last.strip()}"
    return ' '.join(name.lower().split())


def parse_position(pos_str: str):
    """'T4' → 4, '1' → 1, 'CUT'/'WD'/'DQ' → None."""
    if not pos_str or pos_str in ('CUT', 'WD', 'DQ', ''):
        return None
    try:
        return int(str(pos_str).lstrip('T').strip())
    except ValueError:
        return None


def pearson_corr(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denom = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    return num / denom if denom > 0 else 0.0


def rank_vector(values):
    """Values → 1-based rank list (1 = smallest value)."""
    indexed = sorted(enumerate(values), key=lambda t: t[1])
    ranks = [0] * len(values)
    for rank, (idx, _) in enumerate(indexed, start=1):
        ranks[idx] = rank
    return ranks


def spearman_rho(xs, ys):
    return pearson_corr(rank_vector(xs), rank_vector(ys))


def classify_trait(rho: float) -> str:
    """Spearman ρ between final position and trait value.
    Negative ρ = good finishers have high trait value = model signal validated."""
    if rho <= -0.30:
        return 'validated'
    if rho <= -0.10:
        return 'mixed'
    if rho <= 0.10:
        return 'neutral'
    return 'weak'


def safe_float(row, col):
    try:
        v = (row or {}).get(col, '') or ''
        return float(v) if str(v).lower() not in ('null', '', 'nan') else None
    except (ValueError, TypeError):
        return None


TRAITS = [
    ('app_overall',   'Approach Play',       'sg_app'),
    ('putting',       'Putting',             'sg_putt'),
    ('arg_overall',   'Around the Green',    'sg_arg'),
    ('ott_total',     'Off the Tee SG',      'sg_ott'),
    ('ott_accuracy',  'OTT Accuracy',        'accuracy'),
    ('ott_distance',  'OTT Distance',        'distance'),
    ('t2g',           'Tee to Green',        'sg_t2g'),
    ('ball_striking', 'Ball Striking',       'sg_bs'),
    ('scrambling',    'Scrambling',          'scrambling'),
    ('gir',           'Greens in Reg',       'gir'),
]

SRVI_THRESHOLD = 6.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', required=True)
    args = parser.parse_args()
    slug = args.event

    event_dir  = BASE_DIR / 'events' / slug
    final_dir  = event_dir / 'output' / 'final_tournament'
    deploy_dir = event_dir / 'deploy' / 'data'

    # ── Load inputs ──────────────────────────────────────────────────────────────
    with open(final_dir / 'final_leaderboard.csv', newline='', encoding='utf-8') as f:
        lb_rows = list(csv.DictReader(f))
    with open(final_dir / 'final_tournament_course_insights.csv', newline='', encoding='utf-8') as f:
        ci_rows = list(csv.DictReader(f))
    with open(deploy_dir / 'board_export.json', encoding='utf-8') as f:
        board_data = json.load(f)['players']

    r1_data = {}
    r1_path = deploy_dir / 'r1_analysis.json'
    if r1_path.exists():
        with open(r1_path, encoding='utf-8') as f:
            r1_data = json.load(f)

    # ── Build lookup dicts ───────────────────────────────────────────────────────
    lb_by_name    = {normalize_name(r['player_name']): r for r in lb_rows}
    ci_by_name    = {normalize_name(r['player_name']): r for r in ci_rows}
    wave_by_name  = {}
    for snap in r1_data.get('leaderboard_snapshot', []):
        key = normalize_name(snap.get('r1_name', ''))
        if key:
            wave_by_name[key] = {
                'wave':         snap.get('wave'),
                'wave_penalty': snap.get('wave_penalty', 0),
            }

    # ── Player comparison table ───────────────────────────────────────────────────
    player_comparison = []
    for p in board_data:
        key = normalize_name(p['player'])
        lb  = lb_by_name.get(key)
        ci  = ci_by_name.get(key)
        if not lb:
            continue
        pos_str    = lb.get('pos', '')
        final_pos  = parse_position(pos_str)
        cut_status = 'cut' if pos_str in ('CUT', 'WD', 'DQ') else 'made'
        pt_rank    = p.get('rank')
        prediction_delta = (pt_rank - final_pos) if (pt_rank and final_pos) else None
        player_comparison.append({
            'player_name':       lb['player_name'],
            'pt_rank':           pt_rank,
            'pt_tier':           p.get('tier'),
            'pt_vts':            p.get('vts_final'),
            'final_pos':         pos_str,
            'final_pos_numeric': final_pos,
            'total_sg':          safe_float(lb, 'total_sg'),
            'sg_app':            safe_float(ci, 'sg_app'),
            'sg_putt':           safe_float(ci, 'sg_putt'),
            'sg_ott':            safe_float(ci, 'sg_ott'),
            'sg_arg':            safe_float(ci, 'sg_arg'),
            'prediction_delta':  prediction_delta,
            'cut_status':        cut_status,
        })

    player_comparison.sort(key=lambda r: (
        0 if r['cut_status'] == 'made' else 1,
        r['final_pos_numeric'] if r['final_pos_numeric'] is not None else 9999,
    ))

    # ── Spearman ρ: pt_rank vs final position (made-cut only) ────────────────────
    pairs_pos = [
        (r['pt_rank'], r['final_pos_numeric'])
        for r in player_comparison
        if r['cut_status'] == 'made' and r['pt_rank'] and r['final_pos_numeric']
    ]
    rho_pos = spearman_rho([p[0] for p in pairs_pos], [p[1] for p in pairs_pos])

    # ── Spearman ρ: pt_rank vs total_sg (negate sg — lower rank = higher sg = validated) ──
    pairs_sg = [
        (r['pt_rank'], r['total_sg'])
        for r in player_comparison
        if r['cut_status'] == 'made' and r['pt_rank'] and r['total_sg'] is not None
    ]
    rho_sg = spearman_rho([p[0] for p in pairs_sg], [-p[1] for p in pairs_sg])

    # ── Tier hit rates ────────────────────────────────────────────────────────────
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
            'player_count': n,
            'top10_count':  n10,
            'top20_count':  n20,
            'cut_count':    ncut,
            'top10_pct':    round(n10  / n, 3),
            'top20_pct':    round(n20  / n, 3),
            'cut_pct':      round(ncut / n, 3),
        }

    # ── Trait audit (Spearman ρ between final position and each SG signal) ───────
    finishers = []
    for row in ci_rows:
        key     = normalize_name(row['player_name'])
        pos_str = lb_by_name.get(key, {}).get('pos', 'CUT')
        pos_num = parse_position(pos_str)
        if pos_num is not None:
            finishers.append({'pos': pos_num, 'ci': row})

    trait_audit = []
    for trait_key, label, ci_col in TRAITS:
        pairs = []
        for f in finishers:
            v = safe_float(f['ci'], ci_col)
            if v is not None:
                pairs.append((f['pos'], v))
        if len(pairs) < 5:
            trait_audit.append({'trait': trait_key, 'label': label, 'status': 'neutral', 'spearman_rho': None})
            continue
        rho_t = spearman_rho([p[0] for p in pairs], [p[1] for p in pairs])
        trait_audit.append({
            'trait':        trait_key,
            'label':        label,
            'status':       classify_trait(rho_t),
            'spearman_rho': round(rho_t, 3),
        })

    # ── Single-Round Volatility Index ─────────────────────────────────────────────
    srvi_spikes = []
    for row in lb_rows:
        if parse_position(row.get('pos', 'CUT')) is None:
            continue
        for rnd in (1, 2, 3, 4):
            v = safe_float(row, f'r{rnd}_sg')
            if v is not None and v > SRVI_THRESHOLD:
                is_winner = row['pos'] == '1'
                srvi_spikes.append({
                    'player':    row['player_name'],
                    'round':     rnd,
                    'sg':        round(v, 2),
                    'final_pos': row['pos'],
                    'winner':    is_winner,
                    'badge':     'Volatility Spike Winner' if is_winner else None,
                })
    srvi_spikes.sort(key=lambda s: -s['sg'])

    # ── Wave draw impact ──────────────────────────────────────────────────────────
    favored_wave = r1_data.get('metadata', {}).get('favored_wave', '')
    wave_pairs   = []
    for key, wv in wave_by_name.items():
        lb = lb_by_name.get(key)
        if not lb or parse_position(lb.get('pos', 'CUT')) is None:
            continue
        v = safe_float(lb, 'total_sg')
        if v is None:
            continue
        wave_flag = 0 if wv.get('wave') == favored_wave else 1
        wave_pairs.append((wave_flag, v))

    wave_corr = None
    if len(wave_pairs) >= 5:
        wave_corr = round(
            pearson_corr([p[0] for p in wave_pairs], [p[1] for p in wave_pairs]), 3
        )

    # ── Summary stats ─────────────────────────────────────────────────────────────
    winner_row = next((r for r in player_comparison if r['final_pos_numeric'] == 1), None)
    n_made_cut = sum(1 for r in player_comparison if r['cut_status'] == 'made')

    output = {
        'schema_version':     '1.1',
        'generated_at':       date.today().isoformat(),
        'event_slug':         slug,
        'spearman_rho':       round(rho_pos, 3),
        'spearman_rho_vs_sg': round(rho_sg, 3),
        'tier_hit_rates':     tier_hit_rates,
        'trait_audit':        trait_audit,
        'single_round_volatility': {
            'threshold': SRVI_THRESHOLD,
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

    out_path = deploy_dir / 'post_mortem_analysis.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f'[VenueDNA] Post-mortem written: {out_path}')
    print(f'  rho (rank vs pos): {rho_pos:.3f}')
    print(f'  rho (rank vs sg):  {rho_sg:.3f}')
    print(f'  SRVI spikes: {len(srvi_spikes)}')
    print(f'  {n_made_cut}/{len(lb_rows)} made cut')


if __name__ == '__main__':
    main()
