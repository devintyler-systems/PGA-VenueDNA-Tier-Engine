# Open Championship 2026 Post-Mortem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile a 4-round post-mortem JSON payload and render a "Post-Mortem & Model Calibration" view in the existing 2026 Open Championship dashboard.

**Architecture:** New Python script (`engine/build_post_mortem.py`) ingests the final CSV data, joins it to pre-tournament board data, and writes `post_mortem_analysis.json` to the deploy/data directory. The existing `app.js` gains a `renderPostMortemView()` function and a new `'pm'` branch in `switchRound()`. The HTML gains one tab button and one section div.

**Tech Stack:** Python 3 (stdlib only — no scipy), Vanilla JS ES6, HTML/CSS matching existing patterns in `open_2026_venuedna.html` and `styles.css`.

## Global Constraints

- No external Python dependencies — use stdlib only (csv, json, math, re, pathlib, argparse)
- All paths are relative to repo root `C:/PGA_VenueDNA/`
- Player names in board_export use "First Last"; CSVs use "Last, First" — normalization required on all joins
- CUT/WD players must not distort Spearman rho calculation (exclude from correlation pairs, include in tier cut-rate denominators)
- CSS class `.tier-badge.t1/.t2/.t3/.t4/.t5` already exists in `deploy/styles.css` — use it; do not re-define
- Reuse `.live-table` CSS class for the comparison table; do not duplicate table styles
- Do not add `sec-pm` to `PRE_SECTIONS` constant — it is managed independently in `switchRound()`
- Output file must satisfy: `pm.spearman_rho` and `pm.tier_hit_rates` are truthy (verification gate)

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `engine/build_post_mortem.py` | CLI compiler: joins CSV + JSON → writes post_mortem_analysis.json |
| Modify | `events/2026_the_open_championship/deploy/open_2026_venuedna.html` | Add `<button data-round="pm">` tab + `<section id="sec-pm">` div |
| Modify | `events/2026_the_open_championship/deploy/app.js` | `switchRound()` 'pm' branch + `renderPostMortemView()` function |

---

## Task 1: Python Post-Mortem Compiler

**Files:**
- Create: `engine/build_post_mortem.py`

**Interfaces:**
- Consumes: `events/{slug}/output/final_tournament/final_leaderboard.csv`, `events/{slug}/output/final_tournament/final_tournament_course_insights.csv`, `events/{slug}/deploy/data/board_export.json`, `events/{slug}/deploy/data/r1_analysis.json`
- Produces: `events/{slug}/deploy/data/post_mortem_analysis.json` with shape:
  ```
  {
    schema_version, generated_at, event_slug,
    spearman_rho: float,          // pt_rank vs final position (made-cut only)
    spearman_rho_vs_sg: float,    // pt_rank vs total_sg (made-cut only)
    tier_hit_rates: { T1: { player_count, top10_count, top20_count, cut_count, top10_pct, top20_pct, cut_pct }, T2: … },
    trait_audit: [{ trait, label, status, spearman_rho }],
    single_round_volatility: { threshold: 6.0, spikes: [{ player, round, sg, final_pos, winner, badge }] },
    wave_penalty_correlation: { correlation, favored_wave, note },
    player_comparison: [{ player_name, pt_rank, pt_tier, pt_vts, final_pos, final_pos_numeric, total_sg, sg_app, sg_putt, sg_ott, sg_arg, prediction_delta, cut_status }],
    summary_stats: { field_size, made_cut, winner, winner_pt_rank }
  }
  ```

- [ ] **Step 1: Write the script**

```python
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
        return float(v) if v.lower() not in ('null', '', 'nan') else None
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
    board_by_name = {normalize_name(p['player']): p    for p in board_data}
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
            'player_name':      lb['player_name'],
            'pt_rank':          pt_rank,
            'pt_tier':          p.get('tier'),
            'pt_vts':           p.get('vts_final'),
            'final_pos':        pos_str,
            'final_pos_numeric': final_pos,
            'total_sg':         safe_float(lb, 'total_sg'),
            'sg_app':           safe_float(ci, 'sg_app'),
            'sg_putt':          safe_float(ci, 'sg_putt'),
            'sg_ott':           safe_float(ci, 'sg_ott'),
            'sg_arg':           safe_float(ci, 'sg_arg'),
            'prediction_delta': prediction_delta,
            'cut_status':       cut_status,
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

    # ── Spearman ρ: pt_rank vs total_sg (negate sg so higher rank = more negative = validated) ──
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

    # ── Trait audit ───────────────────────────────────────────────────────────────
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

    # ── Wave penalty correlation ──────────────────────────────────────────────────
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
        wave_corr = round(pearson_corr([p[0] for p in wave_pairs], [p[1] for p in wave_pairs]), 3)

    # ── Summary stats ─────────────────────────────────────────────────────────────
    winner_row = next((r for r in player_comparison if r['final_pos_numeric'] == 1), None)
    n_made_cut = sum(1 for r in player_comparison if r['cut_status'] == 'made')

    output = {
        'schema_version': '1.1',
        'generated_at':   date.today().isoformat(),
        'event_slug':     slug,
        'spearman_rho':   round(rho_pos, 3),
        'spearman_rho_vs_sg': round(rho_sg, 3),
        'tier_hit_rates': tier_hit_rates,
        'trait_audit':    trait_audit,
        'single_round_volatility': {
            'threshold': SRVI_THRESHOLD,
            'spikes':    srvi_spikes,
        },
        'wave_penalty_correlation': {
            'correlation':  wave_corr,
            'favored_wave': favored_wave or None,
            'note': f"Pearson correlation: disadvantaged wave (1) vs. total SG over {len(wave_pairs)} matched players.",
        },
        'player_comparison': player_comparison,
        'summary_stats': {
            'field_size':     len(lb_rows),
            'made_cut':       n_made_cut,
            'winner':         winner_row['player_name'] if winner_row else None,
            'winner_pt_rank': winner_row['pt_rank'] if winner_row else None,
        },
    }

    out_path = deploy_dir / 'post_mortem_analysis.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f'[VenueDNA] Post-mortem written → {out_path}')
    print(f'  ρ (rank vs pos): {rho_pos:.3f}')
    print(f'  ρ (rank vs sg):  {rho_sg:.3f}')
    print(f'  SRVI spikes: {len(srvi_spikes)}')
    print(f'  {n_made_cut}/{len(lb_rows)} made cut')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the script**

```
python C:/PGA_VenueDNA/engine/build_post_mortem.py --event 2026_the_open_championship
```

Expected output (approximate):
```
[VenueDNA] Post-mortem written → …/deploy/data/post_mortem_analysis.json
  ρ (rank vs pos): 0.xxx
  ρ (rank vs sg):  0.xxx
  SRVI spikes: N
  78/157 made cut
```

- [ ] **Step 3: Verify JSON schema**

```
node -e "const pm = require('./events/2026_the_open_championship/deploy/data/post_mortem_analysis.json'); if (!pm.spearman_rho || !pm.tier_hit_rates) throw new Error('Post-mortem schema failure'); console.log('Post-mortem compilation successfully verified.');"
```

Expected: `Post-mortem compilation successfully verified.`

- [ ] **Step 4: Commit**

```bash
git add engine/build_post_mortem.py events/2026_the_open_championship/deploy/data/post_mortem_analysis.json
git commit -m "feat: post-mortem compiler — Spearman rho, tier hit rates, trait audit, SRVI"
```

---

## Task 2: HTML — Tab Button + Section Container

**Files:**
- Modify: `events/2026_the_open_championship/deploy/open_2026_venuedna.html` at lines 561 and 636

**Interfaces:**
- Consumes: nothing new
- Produces: `data-round="pm"` button (picked up by existing `bindEvents()` listener at app.js:224), `id="sec-pm"` div (hidden by default, shown by `switchRound('pm')`)

- [ ] **Step 1: Add the Post-Mortem tab button**

In `open_2026_venuedna.html` line 561, after the R4 Final button:

Old:
```html
      <button class="round-tab sans" data-round="4">R4 Final</button>
    </div>
```

New:
```html
      <button class="round-tab sans" data-round="4">R4 Final</button>
      <button class="round-tab sans" data-round="pm">Post-Mortem</button>
    </div>
```

- [ ] **Step 2: Add the sec-pm section div**

In `open_2026_venuedna.html` after line 636 (after closing `</section>` of sec-live):

Old:
```html
  </section>

  <section class="section" id="sec-spotlight">
```

New:
```html
  </section>

  <section class="section hidden" id="sec-pm"></section>

  <section class="section" id="sec-spotlight">
```

- [ ] **Step 3: Add PM card CSS to the inline `<style>` tag**

Find the `</style>` closing tag in the HTML head (it appears after line 136) and insert before it:

Old:
```css
.t5 .tier-badge{background:var(--t5-bg);color:var(--t5-t);border:1px solid var(--t5-b)}
```

New:
```css
.t5 .tier-badge{background:var(--t5-bg);color:var(--t5-t);border:1px solid var(--t5-b)}
.pm-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:14px 18px}
.pm-card-label{font-family:-apple-system,sans-serif;font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.pm-card-value{font-family:-apple-system,sans-serif;font-size:26px;font-weight:700;margin:4px 0 2px;line-height:1}
.pm-card-sub{font-family:-apple-system,sans-serif;font-size:11px;color:var(--text-2)}
.pm-cut-row td{opacity:.45}
```

- [ ] **Step 4: Verify HTML syntax**

```
node --check "C:/PGA_VenueDNA/events/2026_the_open_championship/deploy/open_2026_venuedna.html" 2>&1 || echo "(HTML is not JS — this is expected; check visually instead)"
```

Open in browser and confirm: 6 tabs appear in the ribbon (Pre-Tourney, R1 Live, R2 Live, R3 Live, R4 Final, Post-Mortem).

- [ ] **Step 5: Commit**

```bash
git add events/2026_the_open_championship/deploy/open_2026_venuedna.html
git commit -m "feat: add Post-Mortem tab button and sec-pm container"
```

---

## Task 3: app.js — switchRound 'pm' Branch + renderPostMortemView

**Files:**
- Modify: `events/2026_the_open_championship/deploy/app.js`
  - Line 14 — add `pmData: null` to state object S
  - Lines 1100–1104 — extend `switchRound()` 'pre' case to also hide sec-pm
  - Lines 1106–1156 — add 'pm' branch before the live-round fetch block
  - After function `renderCumulativeAnalysis()` (line ~1432) — add `renderPostMortemView(data)`

**Interfaces:**
- Consumes: `S.pmData` (cached post_mortem_analysis.json), `data/post_mortem_analysis.json` fetch
- Produces: Renders into `#sec-pm`; reuses `.live-table`, `.tier-badge.t1…t5`, `.pm-card*` CSS classes

- [ ] **Step 1: Add pmData to S state**

In `app.js` line 24, after `filterRules: [],`:

Old:
```javascript
  filterRules:          [],
  glossaryModalOpen:    false,
};
```

New:
```javascript
  filterRules:          [],
  glossaryModalOpen:    false,
  pmData:               null,
};
```

- [ ] **Step 2: Extend 'pre' case in switchRound to hide sec-pm**

In `app.js` lines 1100–1104:

Old:
```javascript
  if (r === 'pre') {
    document.getElementById('sec-live')?.classList.remove('loading-blur');
    PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.remove('hidden'));
    document.getElementById('sec-live')?.classList.add('hidden');
    return;
  }
```

New:
```javascript
  if (r === 'pre') {
    document.getElementById('sec-live')?.classList.remove('loading-blur');
    PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.remove('hidden'));
    document.getElementById('sec-live')?.classList.add('hidden');
    document.getElementById('sec-pm')?.classList.add('hidden');
    return;
  }
```

- [ ] **Step 3: Add 'pm' branch and hide sec-pm in live-round path**

In `app.js` after the 'pre' guard (line 1105), add the 'pm' branch and also hide sec-pm for r1–r4:

Old:
```javascript
  PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.add('hidden'));
  const liveSection = document.getElementById('sec-live');
```

New:
```javascript
  if (r === 'pm') {
    PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.add('hidden'));
    document.getElementById('sec-live')?.classList.add('hidden');
    const pmSection = document.getElementById('sec-pm');
    if (!pmSection) return;
    pmSection.classList.remove('hidden');
    if (S.pmData) { renderPostMortemView(S.pmData); return; }
    pmSection.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-3);font-family:-apple-system,sans-serif">Loading post-mortem…</div>';
    try {
      const resp = await fetch('data/post_mortem_analysis.json');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      S.pmData = await resp.json();
      renderPostMortemView(S.pmData);
    } catch (e) {
      pmSection.innerHTML = '<div style="text-align:center;padding:48px;color:var(--accent);font-family:-apple-system,sans-serif">Post-Mortem data not yet available.</div>';
    }
    return;
  }

  PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.add('hidden'));
  document.getElementById('sec-pm')?.classList.add('hidden');
  const liveSection = document.getElementById('sec-live');
```

- [ ] **Step 4: Add renderPostMortemView function**

Append after the closing `}` of `renderCumulativeAnalysis()` (around line 1432). Add the full function:

```javascript
// ── Post-Mortem renderer ───────────────────────────────────────────────────────
function renderPostMortemView(data) {
  const el = document.getElementById('sec-pm');
  if (!el) return;

  const rho       = data.spearman_rho;
  const thr       = data.tier_hit_rates || {};
  const t1        = thr.T1 || {};
  const t2        = thr.T2 || {};
  const traits    = data.trait_audit || [];
  const srvi      = data.single_round_volatility || {};
  const spikes    = srvi.spikes || [];
  const winner    = spikes.find(s => s.winner) || null;
  const waveCorr  = data.wave_penalty_correlation || {};
  const appTrait  = traits.find(t => t.trait === 'app_overall') || {};
  const players   = data.player_comparison || [];
  const spikeSet  = new Set(spikes.map(s => s.player));

  const sgFmt = v  => v != null ? (v > 0 ? '+' : '') + Number(v).toFixed(2) : '—';
  const pctFmt = v => v != null ? Math.round(v * 100) + '%' : '—';
  const rhoColor = r => r > 0.3 ? 'var(--green-ok)' : r > 0.1 ? '#f59e0b' : 'var(--accent)';
  const statusColor = s => ({ validated: 'var(--green-ok)', mixed: '#f59e0b', neutral: 'var(--text-3)', weak: 'var(--accent)' }[s] || 'var(--text-3)');

  const t12top20 = (t1.player_count || 0) + (t2.player_count || 0) > 0
    ? Math.round(((t1.top20_count || 0) + (t2.top20_count || 0)) / ((t1.player_count || 0) + (t2.player_count || 0)) * 100) + '%'
    : '—';

  el.innerHTML = `
<div style="padding:24px 0 8px">
  <div class="section-header">
    <h2 class="section-title sans">Post-Mortem &amp; Model Calibration</h2>
    <span class="section-sub sans">${data.event_slug || ''} · Generated ${data.generated_at || ''}</span>
  </div>

  ${winner ? `
  <div style="display:flex;align-items:center;gap:16px;background:linear-gradient(135deg,#0f172a,#1e293b);border:2px solid var(--accent);border-radius:var(--radius-lg);padding:16px 20px;margin-bottom:20px">
    <span style="font-size:28px;flex-shrink:0">⚡</span>
    <div>
      <div class="sans" style="font-size:10px;color:var(--accent);letter-spacing:.1em;text-transform:uppercase;font-weight:700">Volatility Spike Winner</div>
      <div class="sans" style="font-size:15px;color:#f1f5f9;font-weight:700;margin-top:3px">${winner.player} — R${winner.round} (+${winner.sg.toFixed(2)} SG)</div>
      <div class="sans" style="font-size:12px;color:var(--text-2);margin-top:4px">Win driven by a single outlier round exceeding ${srvi.threshold} SG. Multi-round consistency supported model ranking.</div>
    </div>
  </div>` : ''}

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:24px">
    <div class="pm-card">
      <div class="pm-card-label">Overall Spearman ρ</div>
      <div class="pm-card-value" style="color:${rho != null ? rhoColor(Math.abs(rho)) : 'var(--text-2)'}">${rho != null ? rho.toFixed(3) : '—'}</div>
      <div class="pm-card-sub">rank vs. final position</div>
    </div>
    <div class="pm-card">
      <div class="pm-card-label">T1/T2 Top-20 Hit Rate</div>
      <div class="pm-card-value" style="color:var(--green-ok)">${t12top20}</div>
      <div class="pm-card-sub">T1: ${pctFmt(t1.top20_pct)} &middot; T2: ${pctFmt(t2.top20_pct)}</div>
    </div>
    <div class="pm-card">
      <div class="pm-card-label">Approach Signal</div>
      <div class="pm-card-value" style="color:${statusColor(appTrait.status)};font-size:18px">${(appTrait.status || '—').toUpperCase()}</div>
      <div class="pm-card-sub">ρ = ${appTrait.spearman_rho != null ? appTrait.spearman_rho.toFixed(3) : '—'}</div>
    </div>
    <div class="pm-card">
      <div class="pm-card-label">Wave Penalty Corr</div>
      <div class="pm-card-value" style="color:${Math.abs(waveCorr.correlation ?? 0) > 0.1 ? '#f59e0b' : 'var(--text-3)'};font-size:22px">${waveCorr.correlation != null ? waveCorr.correlation.toFixed(3) : '—'}</div>
      <div class="pm-card-sub">${waveCorr.favored_wave ? 'favored: ' + waveCorr.favored_wave : '—'}</div>
    </div>
  </div>

  <div class="sans" style="font-size:11px;font-weight:700;color:var(--text-3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Trait Audit Validation</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:24px">
    ${traits.map(t => `
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px 12px">
      <div class="sans" style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.06em">${t.label}</div>
      <div class="sans" style="font-size:12px;font-weight:700;color:${statusColor(t.status)};margin-top:4px">${(t.status || '').toUpperCase()}</div>
      <div class="sans" style="font-size:11px;color:var(--text-2)">ρ ${t.spearman_rho != null ? t.spearman_rho.toFixed(3) : '—'}</div>
    </div>`).join('')}
  </div>

  <div class="sans" style="font-size:11px;font-weight:700;color:var(--text-3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Model vs. Actual — Full Field</div>
  <div style="overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface);box-shadow:0 2px 8px var(--shadow);margin-bottom:24px">
    <table class="live-table">
      <thead><tr>
        <th class="sans">PT RANK</th>
        <th class="sans">Player</th>
        <th class="sans">TIER</th>
        <th class="sans">FINAL POS</th>
        <th class="sans">TOTAL SG</th>
        <th class="sans">SG:APP</th>
        <th class="sans">SG:PUTT</th>
        <th class="sans">PRED Δ</th>
      </tr></thead>
      <tbody>
        ${players.map(r => {
          const d = r.prediction_delta;
          const dHtml = d == null ? '—'
            : d > 0  ? `<span style="color:var(--green-ok)">▲${d}</span>`
            : d < 0  ? `<span style="color:var(--accent)">▼${Math.abs(d)}</span>`
            : '<span style="color:var(--text-3)">—</span>';
          const isSpike = spikeSet.has(r.player_name);
          return `<tr class="${r.cut_status === 'cut' ? 'pm-cut-row' : ''}">
            <td class="sans" style="font-weight:700;color:var(--text-1)">${r.pt_rank ?? '—'}</td>
            <td class="sans">${r.player_name}${isSpike ? ' <span style="color:var(--accent);font-size:10px">⚡</span>' : ''}</td>
            <td class="sans"><span class="tier-badge ${(r.pt_tier || '').toLowerCase()}">${r.pt_tier ?? '—'}</span></td>
            <td class="sans" style="font-weight:700">${r.final_pos || 'CUT'}</td>
            <td class="sans">${sgFmt(r.total_sg)}</td>
            <td class="sans">${sgFmt(r.sg_app)}</td>
            <td class="sans">${sgFmt(r.sg_putt)}</td>
            <td class="sans">${dHtml}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  </div>

  ${spikes.length > 0 ? `
  <div class="sans" style="font-size:11px;font-weight:700;color:var(--text-3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Single-Round Volatility Spikes (≥${srvi.threshold} SG)</div>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:24px">
    ${spikes.map(s => `
    <div style="background:var(--surface);border:1px solid ${s.winner ? 'var(--accent)' : 'var(--border)'};border-radius:var(--radius);padding:10px 14px;min-width:180px">
      <div class="sans" style="font-size:13px;font-weight:700;color:var(--text-1)">${s.player}</div>
      <div class="sans" style="font-size:11px;color:var(--text-2);margin-top:2px">R${s.round} &middot; +${s.sg.toFixed(2)} SG &middot; Finished ${s.final_pos}</div>
      ${s.badge ? `<div class="sans" style="font-size:10px;color:var(--accent);margin-top:4px;text-transform:uppercase;letter-spacing:.05em;font-weight:700">${s.badge}</div>` : ''}
    </div>`).join('')}
  </div>` : ''}
</div>`;
}
```

- [ ] **Step 5: Verify JavaScript syntax**

```
node --check C:/PGA_VenueDNA/events/2026_the_open_championship/deploy/app.js
```

Expected: no output (syntax OK).

- [ ] **Step 6: Run verification loop**

```
python C:/PGA_VenueDNA/engine/build_post_mortem.py --event 2026_the_open_championship
node --check C:/PGA_VenueDNA/events/2026_the_open_championship/deploy/app.js
node -e "const pm = require('./events/2026_the_open_championship/deploy/data/post_mortem_analysis.json'); if (!pm.spearman_rho || !pm.tier_hit_rates) throw new Error('Post-mortem schema failure'); console.log('Post-mortem compilation successfully verified.');"
```

All three must pass without errors.

- [ ] **Step 7: Commit**

```bash
git add events/2026_the_open_championship/deploy/app.js
git commit -m "feat: renderPostMortemView — summary cards, trait audit grid, model vs actual table, SRVI badges"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `build_post_mortem.py` ingests final_leaderboard.csv + final_tournament_course_insights.csv
- [x] Spearman ρ between pt_rank and final total_sg / pos — both computed
- [x] Tier 1 and Tier 2 hit rates (Top 10%, Top 20%, Cut %) — `tier_hit_rates` object
- [x] Trait Audit for 10 schema traits → classified as validated/mixed/neutral/weak
- [x] SRVI: identifies single-round outlier rounds > 6.0 SG (Ryan Fox R3 = 8.26)
- [x] Output to `deploy/data/post_mortem_analysis.json` conforming to Schema v1.1
- [x] HTML: "Post-Mortem" button tab in the round selector header ribbon
- [x] JS: `renderPostMortemView(data)` with summary card grid (ρ, T1/T2 top-20, approach signal, wave corr)
- [x] JS: "Model vs. Actual" table with PT RANK, FINAL POS, TOTAL SG, SG:APP, SG:PUTT, PRED Δ
- [x] Ryan Fox SRVI badge: "Volatility Spike Winner" in summary card and ⚡ in table row
- [x] CUT players: excluded from Spearman pairs, included in tier cut-rate denominators, rendered with `.pm-cut-row` (opacity 0.45)
- [x] Name normalization: `normalize_name()` handles "Last, First" ↔ "First Last" and strips suffixes

**Placeholder scan:** None — all steps contain complete code.

**Type consistency:**
- `S.pmData` set in switchRound 'pm' branch, read in `renderPostMortemView(S.pmData)` — consistent
- `spearman_rho` field name used in both Python output and JS verification gate — consistent
- `.tier-badge.t1/.t2` matches styles.css line 45-46 — consistent
- `.pm-card`, `.pm-card-label`, `.pm-card-value`, `.pm-card-sub`, `.pm-cut-row` defined in HTML `<style>`, used in `renderPostMortemView()` — consistent
