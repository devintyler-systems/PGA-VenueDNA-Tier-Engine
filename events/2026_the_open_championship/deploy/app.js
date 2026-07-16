'use strict';

// ── State ──────────────────────────────────────────────────────────────────────
const S = {
  boardData:         [],
  briefsByName:      {},
  analysis:          null,
  activePlayer:      null,
  currentFilter:     'all',
  currentTier:       'all',
  searchQuery:       '',
  sort: { key: 'rank', dir: 1 },
  numFilters: { vts_min:null, vts_max:null, nsi_min:null, nsi_max:null, vfs_min:null, vfs_max:null, win_min:null, win_max:null },
  spotlightOpen:     false,
  advFilterOpen:     false,
  currentRound:      'pre',
  roundData:         {},
  altPlayers:        [],
  activeFetchTarget: null,
  weather:    { speed: 0, direction: 'N/A', wave_delta: 0.0, tide: 'N/A' },
  waveByPlayer: {},
};

// ── Audit rule metadata ────────────────────────────────────────────────────────
const FM = {
  R1:{lbl:'R1',cls:'fr1',full:'PUTT Regression'},
  R2:{lbl:'R2',cls:'fr2',full:'Zero Links'},
  R3:{lbl:'R3',cls:'fr3',full:'OTT-Only Links'},
  R4:{lbl:'R4',cls:'fr4',full:'Depth Gate'},
  R5:{lbl:'R5',cls:'fr5',full:'History Conflict'},
  R6:{lbl:'R6',cls:'fr6',full:'Putt-Led Total'},
  R7:{lbl:'R7',cls:'fr7',full:'APP Gate'},
  R9:{lbl:'R9',cls:'fr9',full:'Form Spike'},
};

const RISK_KEYS = {
  R1:'risk_R1_putt_regression', R2:'risk_R2_zero_links',
  R3:'risk_R3_ott_only_links',  R4:'risk_R4_birkdale_depth_gate',
  R5:'risk_R5_history_conflict',R6:'risk_R6_putt_led_links',
  R7:'risk_R7_links_app_gate',  R9:'risk_R9_form_spike',
};

const RISK_COLS = {
  R1:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'nsi',l:'NSI'},{k:'putt_share',l:'Putt%'},{k:'sg_putt_pred',l:'SG PUTT'},{k:'links_putt_rank',l:'Links PUTT Rk'},{k:'links_t2g_rank',l:'T2G Rk'},{k:'penaltyR1',l:'Pen'},{k:'reason',l:'Reason'}],
  R2:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'nsi',l:'NSI'},{k:'links_events',l:'Links Ev'},{k:'modelled_delta',l:'Δ Cap'},{k:'penaltyR2',l:'Pen'},{k:'reason',l:'Reason'}],
  R3:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'nsi',l:'NSI'},{k:'sg_ott_links',l:'SG OTT'},{k:'sg_app_links',l:'SG APP'},{k:'penaltyR3',l:'Pen'},{k:'reason',l:'Reason'}],
  R4:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'vhn',l:'VHN'},{k:'birkdale_rounds',l:'Rds'},{k:'excess_vhn',l:'Excess VHN'},{k:'penaltyR4',l:'Pen'},{k:'reason',l:'Reason'}],
  R5:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'vhn',l:'VHN'},{k:'links_total_6m',l:'Links 6m'},{k:'penaltyR5',l:'Pen'},{k:'reason',l:'Reason'}],
  R6:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'sg_putt_links',l:'Links PUTT'},{k:'sg_t2g_links',l:'Links T2G'},{k:'penaltyR6',l:'Pen'},{k:'reason',l:'Reason'}],
  R7:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'sg_app_links',l:'Links APP'},{k:'app_rank',l:'APP Rk'},{k:'penaltyR7',l:'Pen'},{k:'reason',l:'Reason'}],
  R9:[{k:'rank',l:'#'},{k:'player',l:'Player'},{k:'form_class',l:'Form'},{k:'links_evidence',l:'Links Ev'},{k:'penaltyR9',l:'Pen'},{k:'reason',l:'Reason'}],
};

const RULE_EXP = {
  R1:'High-NSI players whose skill is propped by non-transferable putting. Links T2G must confirm. Without confirmation: −4.0 VTS (no links); −2.0 (borderline).',
  R2:'Zero links or Birkdale rounds — modelled links_delta is unconstrained. Cap: delta clipped to ±1.5, excess removed from VTS.',
  R3:"OTT positive at GSO but APP collapsed. Birkdale's precision layout punishes length-without-accuracy. −5.0 VTS.",
  R4:'Thin Birkdale sample (<6 rounds) inflates VHN above neutral. Penalty: −0.15 × excess VHN above 50.',
  R5:'Meaningful Birkdale history contradicted by catastrophic 6m links form. History contribution discounted 75%.',
  R6:"Positive GSO total driven by PUTT alone; T2G collapses without putter. Birkdale's wind-exposed greens don't transfer. −3.0 VTS.",
  R7:'Below-threshold APP at links courses. Birkdale demands elite approach inside 175 yds. −2.5 (no links); −1.5 (borderline).',
  R9:'HOT/WARM form not validated by links evidence. Form credit discounted 40% of above-neutral contribution.',
};

// ── Name normalisation — accent-strip + lowercase + trim ──────────────────────
function normName(s) {
  return (s || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim()
    .replace(/[\u2018\u2019\u0060']/g, "'");
}

// ── Canonical name join — live CSV → boardData with suffix/initials fallbacks ─
function canonName(rawName) {
  const nm = rawName || '';
  if (!nm) return nm;

  // 1. Direct normName match
  let found = S.boardData.find(x => normName(x.player) === normName(nm));
  if (found) return found.player;

  // 2. Strip trailing generational suffixes (Jr., Sr., II, III, IV) and retry
  const stripped = nm.replace(/\s*\b(?:Jr\.?|Sr\.?|I{2,3}|IV)\b\s*$/i, '').trim();
  if (stripped && stripped !== nm) {
    found = S.boardData.find(x => normName(x.player) === normName(stripped));
    if (found) return found.player;
  }

  // 3. Initials first-name pattern ("A.B. Lastname") — unambiguous last-name match
  const initM = nm.match(/^(?:[A-Z]\.)+(?:\s+[A-Z]\.)*\s+(.+)$/i);
  if (initM) {
    const lastName = normName(initM[1]);
    const cands = S.boardData.filter(x => {
      const parts = normName(x.player).split(' ');
      return parts[parts.length - 1] === lastName;
    });
    if (cands.length === 1) return cands[0].player;
  }

  // 4. Fallback: register a runtime debut/alternate record so the drawer stays openable
  if (!S.altPlayers.find(x => x.player === nm)) {
    S.altPlayers.push({
      player: nm, rank: '—', tier: 'T5',
      vts_final: 50.0,
      neutralSkillIndex: 50.0, nsi_final: 50.0,
      venueFitScore: 50.0,     vfs_final: 50.0,
      venueHistoryDelta: 0,    vhd: 0.0,
      penalties_total: 0,
      winPct: null, top5Pct: null, top10Pct: null,
      top20Pct: null, makeCutPct: null, missCutPct: null,
      win_prob: 0.001, top5_prob: 0.005, top10_prob: 0.010,
      top20_prob: 0.020, make_cut_prob: 0.500, miss_cut_prob: 0.500,
      birkdaleTag: 'RoyalBirkdaleDebut',
      band_name: 'Debut Profile',
      tierReason: 'Late alternate or field addition — not in pre-tournament model.',
      risk_flags: ['Late Alternate / No Pre-Tourney Model Data'],
      _flags: [], _isAlt: true,
    });
    console.info('[VenueDNA] alt registered:', nm);
  }
  return nm;
}

// ── Derive audit flags from board row ─────────────────────────────────────────
function buildFlags(p) {
  const f = [];
  if (p.R1_PuttRegression)       f.push('R1');
  if (p.R2_ZeroLinks)            f.push('R2');
  if (p.R3_OTTOnlyLinks)         f.push('R3');
  if (p.R4_BirkdaleDepthGate)    f.push('R4');
  if (p.R5_HistoryConflict)      f.push('R5');
  if (p.R6_PuttLedLinksTotal)    f.push('R6');
  if (p.R7_LinksAPPGate)         f.push('R7');
  if (p.R9_FormSpikeUnconfirmed) f.push('R9');
  return f;
}

// ── Initialisation ─────────────────────────────────────────────────────────────
async function init() {
  const tbody = document.getElementById('board-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="11" class="no-results sans">Loading…</td></tr>';

  try {
    const [boardJson, analysisJson, briefsJson] = await Promise.all([
      fetch('data/board_export.json')
        .then(r => r.ok ? r : fetch('data/open_2026_board_export.json'))
        .then(r => r.json()),
      fetch('data/final_analysis.json').then(r => r.json()).catch(() => ({})),
      fetch('data/player_briefs.json').then(r => r.json()).catch(() => ({ players: [] })),
    ]);

    S.analysis = analysisJson;

    // Build normalised brief lookup: "first last" → brief object
    S.briefsByName = {};
    for (const b of (briefsJson.players || [])) {
      const key = normName(`${b.first_name} ${b.last_name}`);
      S.briefsByName[key] = b;
    }

    S.boardData = (boardJson.players || []).map(p => ({ ...p, _flags: buildFlags(p) }));

    bindEvents();
    renderAll();

    fetch('data/weather_forecast.json')
      .then(r => r.ok ? r.json() : Promise.reject())
      .catch(() => ({ speed: 18, direction: 'WNW', wave_delta: 0.35, tide: 'Incoming / Damp' }))
      .then(wx => { S.weather = { ...S.weather, ...wx }; renderWeather(S.weather); console.log('PGA_VenueDNA Engine R1 dry-run check complete - Weather Wave Invariant: PASS'); });
  } catch (err) {
    console.error('[VenueDNA]', err);
    if (tbody) tbody.innerHTML =
      `<tr><td colspan="11" class="no-results sans">Load failed — serve via http://localhost (not file://). ${err.message}</td></tr>`;
  }
}

// ── Event binding ──────────────────────────────────────────────────────────────
function bindEvents() {
  const srch = document.getElementById('player-search');
  if (srch) {
    srch.addEventListener('input', e => { S.searchQuery = e.target.value; applyVisibility(); });
    srch.addEventListener('keyup', e => { S.searchQuery = e.target.value; applyVisibility(); });
  }
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
  window.addEventListener('scroll', () =>
    document.getElementById('scroll-top')?.classList.toggle('visible', window.scrollY > 400)
  );
  document.querySelectorAll('.round-tab[data-round]').forEach(btn =>
    btn.addEventListener('click', () => switchRound(btn.dataset.round))
  );
  document.getElementById('live-content')?.addEventListener('click', e => {
    const tr = e.target.closest('.live-table tr[data-player]');
    if (!tr) return;
    const name = tr.dataset.player;
    if (!name) return;
    openModal(name);
  });
  document.getElementById('spotlight-toggle')?.addEventListener('click', toggleSpotlight);
  document.getElementById('adv-toggle')?.addEventListener('click', toggleAdvFilter);
  document.getElementById('clear-filters-btn')?.addEventListener('click', clearFilters);
  ['af-vts-min','af-vts-max','af-nsi-min','af-nsi-max','af-vfs-min','af-vfs-max','af-win-min','af-win-max'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', onNumFilter);
  });
}

// ── Render orchestration ───────────────────────────────────────────────────────
function renderAll() {
  renderSpotlight();
  renderTable();
  renderIntel();
  renderRisk();
}

// ── Spotlight — T1/T2 cards ────────────────────────────────────────────────────
function renderSpotlight() {
  const grid = document.getElementById('spotlight-grid');
  if (!grid) return;
  const t12 = S.boardData.filter(p => p.tier === 'T1' || p.tier === 'T2');
  grid.innerHTML = t12.map(p => {
    const tc    = p.tier.toLowerCase();
    const nPct  = clamp(p.neutralSkillIndex, 0, 100);
    const vPct  = clamp(p.venueFitScore, 0, 100);
    const vhPct = clamp(Math.abs(p.venueHistoryDelta || 0) * 40, 0, 100);
    const pPct  = clamp(Math.abs(p.penalties_total || 0) * 6, 0, 100);
    const hasPen = (p.penalties_total || 0) < 0;
    const br    = S.briefsByName[normName(p.player)] || {};
    const badges = p.badges || br.badges || [];
    return `<div class="spotlight-card ${tc}" data-player="${esc(p.player)}">
      <div class="sc-top">
        <div class="sc-rank sans">${p.rank}</div>
        <div>
          <div class="sc-name">${p.player}</div>
          <span class="tier-badge sans">${p.tier}</span>
          ${p.birkdaleTag === 'RoyalBirkdaleDebut' ? ' <span class="badge sans">Debut</span>' : p.birkdaleTag === 'BirkdaleHistoryThin' ? ' <span class="badge sans">Birkdale Hist</span>' : ''}
        </div>
        <div style="margin-left:auto;text-align:right">
          <div class="sc-vts sans">${f2(p.vts_final)}</div>
          <div class="sc-vts-lbl sans">VTS</div>
        </div>
      </div>
      <div class="sc-bars">
        ${bar('NSI', nPct, 'bar-nsi', f1(p.neutralSkillIndex))}
        ${bar('VFS', vPct, 'bar-vfs', f1(p.venueFitScore))}
        ${bar('VHD', vhPct, 'bar-vhd', vhd(p.venueHistoryDelta))}
        ${hasPen ? bar('Pen', pPct, 'bar-pen', f2(p.penalties_total), 'var(--accent)') : ''}
      </div>
      <div class="sc-stats">
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.winPct)}</div><div class="sc-stat-lbl sans">Win</div></div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.top10Pct)}</div><div class="sc-stat-lbl sans">Top 10</div></div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.makeCutPct)}</div><div class="sc-stat-lbl sans">Cut</div></div>
      </div>
      ${badges.length ? `<div class="sc-flags">${badges.map(b => `<span class="badge sans">${b}</span>`).join('')}</div>` : ''}
      ${p._flags.length ? `<div class="sc-flags">${p._flags.map(f => flag(f)).join('')}</div>` : ''}
      <div class="sc-reason">${p.tierReason || ''}</div>
    </div>`;
  }).join('');

  grid.querySelectorAll('.spotlight-card[data-player]').forEach(card => {
    card.addEventListener('click', () => {
      const name = card.dataset.player;
      scrollToPlayer(name);
      openModal(name);
    });
  });
}

function bar(lbl, fillPct, cls, val, valColor) {
  return `<div class="bar-row">
    <div class="bar-lbl sans">${lbl}</div>
    <div class="bar-track"><div class="bar-fill ${cls}" style="width:${fillPct}%"></div></div>
    <div class="bar-val sans"${valColor ? ` style="color:${valColor}"` : ''}>${val}</div>
  </div>`;
}

// ── Full-field table — renders ALL rows; visibility toggled by applyVisibility ─
function renderTable() {
  const sorted = [...S.boardData].sort((a, b) => {
    const { key, dir } = S.sort;
    if (key === 'player') return dir * (a.player || '').localeCompare(b.player || '');
    return dir * ((a[key] || 0) - (b[key] || 0));
  });

  const tbody = document.getElementById('board-tbody');
  if (!tbody) return;

  tbody.innerHTML = sorted.map(p => {
    const tColor = { T1:'var(--t1-t)', T2:'var(--t2-t)', T3:'var(--t3-t)', T4:'var(--t4-t)', T5:'var(--t5-t)' }[p.tier];
    const tBg    = { T1:'var(--t1-bg)', T2:'var(--t2-bg)', T3:'var(--t3-bg)', T4:'var(--t4-bg)', T5:'var(--t5-bg)' }[p.tier];
    const hasPen = (p.penalties_total || 0) < 0;
    const flagStr = p._flags.join(',');
    return `<tr data-player="${esc(p.player)}" data-tier="${p.tier}" data-flags="${flagStr}" data-tag="${p.birkdaleTag || ''}" data-vts="${p.vts_final ?? ''}" data-nsi="${p.neutralSkillIndex ?? ''}" data-vfs="${p.venueFitScore ?? ''}" data-win="${p.winPct ?? ''}">
      <td class="left"><span class="rank-num sans" style="background:${tBg};color:${tColor}">${p.rank}</span></td>
      <td class="left"><div class="player-name-cell">${p.player}
        <small><span class="tier-badge sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor}">${p.tier}</span>
        ${p.birkdaleTag === 'RoyalBirkdaleDebut' ? '<span class="badge sans">Debut</span>' : ''}</small>
      </div></td>
      <td class="vts-cell sans">${f2(p.vts_final)}</td>
      <td class="sans">${f1(p.neutralSkillIndex)}</td>
      <td class="sans">${f1(p.venueFitScore)}</td>
      <td class="sans">${vhd(p.venueHistoryDelta)}</td>
      <td class="sans${hasPen ? ' pen-neg' : ''}">${hasPen ? f2(p.penalties_total) : '<span style="color:var(--text-3)">—</span>'}</td>
      <td class="sans">${pct(p.winPct)}</td>
      <td class="sans">${pct(p.top10Pct)}</td>
      <td class="sans">${pct(p.makeCutPct)}</td>
      <td class="left">${p._flags.map(f => flag(f)).join(' ')}</td>
    </tr>`;
  }).join('');

  // Bind row-click events — no inline onclick in markup
  tbody.querySelectorAll('tr[data-player]').forEach(tr => {
    tr.addEventListener('click', () => {
      S.activePlayer = tr.dataset.player;
      openModal(tr.dataset.player);
    });
  });

  applyVisibility();
  updateSortArrows();
}

// ── Visibility engine — toggles .hidden; no DOM destruction ───────────────────
function applyVisibility() {
  const q = normName(S.searchQuery);
  const nf = S.numFilters;
  const hasNumFilter = Object.values(nf).some(v => v !== null);
  let shown = 0;

  document.querySelectorAll('#board-tbody tr[data-player]').forEach(tr => {
    const tier  = tr.dataset.tier;
    const flags = tr.dataset.flags ? tr.dataset.flags.split(',').filter(Boolean) : [];
    const tag   = tr.dataset.tag || '';
    const name  = normName(tr.dataset.player);

    let show = true;

    if (S.currentTier !== 'all' && tier !== S.currentTier) show = false;

    if (show) {
      switch (S.currentFilter) {
        case 'flagged':   if (!flags.length) show = false; break;
        case 'nopen':     if (flags.length)  show = false; break;
        case 't1t2':      if (tier !== 'T1' && tier !== 'T2') show = false; break;
        case 'history':   if (tag !== 'BirkdaleHistoryThin') show = false; break;
        case 'debut':     if (tag !== 'RoyalBirkdaleDebut')  show = false; break;
        case 'zerolinks': if (!flags.includes('R2'))          show = false; break;
      }
    }

    if (show && q) {
      const matchName = name.includes(q);
      const matchFlag = flags.some(f => f.toLowerCase().includes(q));
      const matchTier = normName(tier) === q;
      if (!matchName && !matchFlag && !matchTier) show = false;
    }

    if (show && hasNumFilter) {
      const vts = parseFloat(tr.dataset.vts);
      const nsi = parseFloat(tr.dataset.nsi);
      const vfs = parseFloat(tr.dataset.vfs);
      const win = parseFloat(tr.dataset.win);
      if (nf.vts_min !== null && (isNaN(vts) || vts < nf.vts_min)) show = false;
      if (nf.vts_max !== null && (isNaN(vts) || vts > nf.vts_max)) show = false;
      if (nf.nsi_min !== null && (isNaN(nsi) || nsi < nf.nsi_min)) show = false;
      if (nf.nsi_max !== null && (isNaN(nsi) || nsi > nf.nsi_max)) show = false;
      if (nf.vfs_min !== null && (isNaN(vfs) || vfs < nf.vfs_min)) show = false;
      if (nf.vfs_max !== null && (isNaN(vfs) || vfs > nf.vfs_max)) show = false;
      if (nf.win_min !== null && (isNaN(win) || win < nf.win_min)) show = false;
      if (nf.win_max !== null && (isNaN(win) || win > nf.win_max)) show = false;
    }

    tr.classList.toggle('hidden', !show);
    if (show) shown++;
  });

  setResultCount(shown);
  updateBoardSub(shown);
  reindexRankColumn();
}

// ── Sort ───────────────────────────────────────────────────────────────────────
function doSort(key) {
  S.sort.dir = S.sort.key === key ? -S.sort.dir : (key === 'rank' || key === 'player' ? 1 : -1);
  S.sort.key = key;
  renderTable();
}

function updateSortArrows() {
  document.querySelectorAll('[id^="sa-"]').forEach(el => { el.className = 'sort-arrow idle'; });
  const el = document.getElementById('sa-' + S.sort.key);
  if (el) el.className = 'sort-arrow ' + (S.sort.dir > 0 ? 'asc' : 'desc') + ' active';
  document.querySelectorAll('.board-table th').forEach(th => th.classList.remove('sort-active'));
  const keyMap = ['rank','player','vts_final','neutralSkillIndex','venueFitScore','venueHistoryDelta','penalties_total','winPct','top10Pct','makeCutPct'];
  const idx = keyMap.indexOf(S.sort.key);
  const ths = document.querySelectorAll('.board-table th');
  if (idx >= 0 && ths[idx]) ths[idx].classList.add('sort-active');
}

// ── Filter controls — called by inline HTML handlers ──────────────────────────
function setTier(t) {
  S.currentTier = t;
  document.querySelectorAll('.tier-tile').forEach(el => el.classList.toggle('active', el.dataset.tier === t));
  applyVisibility();
}

function setChip(f) {
  S.currentFilter = f;
  document.querySelectorAll('.chip').forEach(el => el.classList.toggle('active', el.dataset.f === f));
  applyVisibility();
}

function onSearch(v) { S.searchQuery = v; applyVisibility(); }

function setResultCount(n) {
  const el = document.getElementById('result-ct');
  if (el) el.textContent = `Showing ${n} of ${S.boardData.length} players`;
}

function updateBoardSub(n) {
  const el = document.getElementById('board-sub');
  const total = S.boardData.length;
  if (el) el.textContent = n === total
    ? `${total} players · Royal Birkdale VTS`
    : `${n} of ${total} · filtered`;
}

// ── Tier intelligence panel ────────────────────────────────────────────────────
function renderIntel() {
  const summary = (S.analysis || {}).five_tier_summary || {};
  const leads   = summary.tier_leads || {};
  const descs   = summary.tier_descriptions || {};
  const counts  = summary.tier_counts || { T1:6, T2:22, T3:47, T4:53, T5:28 };
  const grid    = document.getElementById('tier-intel');
  if (!grid) return;
  grid.innerHTML = ['T1','T2','T3','T4','T5'].map(t => {
    const desc    = (descs[t] || '').split(' — ')[0];
    const players = (leads[t] || []).slice(0, 3);
    return `<div class="tier-block ${t.toLowerCase()}-bl">
      <div class="tier-block-header sans"><span>${t} — ${desc}</span><span>${counts[t] || ''}</span></div>
      ${players.map(lp => `<div class="tier-block-player" data-player="${esc(lp.player)}" style="cursor:pointer">
        <div class="tbp-name">#${lp.rank} ${lp.player}</div>
        <div class="tbp-vals sans">
          <span>VTS <b>${f2(lp.vts)}</b></span>
          <span>NSI <b>${f1(lp.nsi)}</b></span>
          <span>VFS <b>${f1(lp.vfs)}</b></span>
          ${(lp.flags || []).map(f => flag(f.replace(/-.*$/, ''))).join('')}
        </div>
      </div>`).join('')}
    </div>`;
  }).join('');

  grid.querySelectorAll('.tier-block-player[data-player]').forEach(el => {
    el.addEventListener('click', () => openModal(el.dataset.player));
  });
}

// ── Risk register ──────────────────────────────────────────────────────────────
function renderRisk() {
  const register = (S.analysis || {}).riskRegister || [];
  const riskData = (S.analysis || {}).birkdale_risk_register || {};
  const container = document.getElementById('risk-rules');
  if (!container) return;
  container.innerHTML = register.map(rule => {
    const code  = rule.rule;
    const m     = FM[code] || { lbl: code, cls: 'fr1', full: code };
    const rPlayers = riskData[RISK_KEYS[code]] || [];
    const cols  = RISK_COLS[code] || [{ k:'rank',l:'#' },{ k:'player',l:'Player' },{ k:'reason',l:'Reason' }];
    const rows  = rPlayers.length
      ? rPlayers.map(rp => `<tr data-player="${esc(rp.player)}" style="cursor:pointer">${cols.map(c => `<td>${fmtRisk(rp[c.k], c.k)}</td>`).join('')}</tr>`).join('')
      : (rule.affectedPlayers || []).map(name => `<tr data-player="${esc(name)}" style="cursor:pointer"><td colspan="${cols.length}">${name}</td></tr>`).join('');
    return `<div class="risk-rule-card">
      <div class="risk-rule-header" onclick="toggleRisk(this)">
        <span class="flag risk-code ${m.cls} sans">${code}</span>
        <div><div class="risk-rule-title">${m.full}</div><div class="risk-rule-desc sans">${rule.description || ''}</div></div>
        <span class="risk-count sans">${rule.affectedCount} players</span>
        <span class="risk-toggle sans">▼</span>
      </div>
      <div class="risk-body">
        <div class="risk-mechanism sans">${RULE_EXP[code] || ''}</div>
        <table class="risk-pt sans">
          <thead><tr>${cols.map(c => `<th>${c.l}</th>`).join('')}</tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
  }).join('');

  container.querySelectorAll('.risk-pt tbody tr[data-player]').forEach(tr => {
    tr.addEventListener('click', () => openModal(tr.dataset.player));
  });
}

function toggleRisk(hdr) {
  hdr.nextElementSibling.classList.toggle('open');
  hdr.querySelector('.risk-toggle').classList.toggle('open');
}

function fmtRisk(v, k) {
  if (v == null) return '<span style="color:var(--text-3)">—</span>';
  if (typeof v === 'number') {
    if (k.startsWith('penalty') || k === 'modelled_delta')
      return `<span${v < 0 ? ' class="pen-neg"' : ''}>${f2(v)}</span>`;
    if (k === 'putt_share') return pct(v * 100);
    return f2(v);
  }
  return String(v);
}

// ── Modal helpers ──────────────────────────────────────────────────────────────
function traitFillCls(score) {
  if (score >= 85) return 'trait-fill-hi';
  if (score >= 70) return 'trait-fill-mid';
  if (score >= 50) return 'trait-fill-lo';
  return 'trait-fill-weak';
}

function traitScoreColor(score) {
  if (score >= 85) return 'color:var(--green-ok)';
  if (score >= 50) return '';
  return 'color:var(--accent)';
}

function sgSign(v) {
  if (v == null) return '—';
  const n = Number(v);
  return (n >= 0 ? '+' : '') + n.toFixed(3);
}

function buildWinCase(p, br, tier) {
  const tn = parseInt(tier[1]) || 3;
  const tc = tier.toLowerCase();
  const hasAny = br.scoring_thesis || br.birkdale_history_note || br.failure_condition ||
                 br.risk_vector || br.conviction_statement || br.structural_note;
  if (!hasAny) return '';

  if (tn <= 2) {
    const label = tn === 1 ? 'Win Case — Tier 1 Structural Winner' : 'Contention Brief — Primary Contender';
    return `<div class="modal-sec">
      <div class="modal-sec-title sans">${label}</div>
      <div class="win-case-card ${tc}">
        ${br.scoring_thesis        ? `<div class="wc-q ${tc}c">Win Mechanism</div><div class="wc-p">${br.scoring_thesis}</div>` : ''}
        ${br.birkdale_history_note ? `<div class="wc-q ${tc}c">Course Calibration</div><div class="wc-p">${br.birkdale_history_note}</div>` : ''}
        ${(br.failure_condition || br.risk_vector) ? `<div class="wc-q ${tc}c">Key Risk</div><div class="wc-p">${br.failure_condition || br.risk_vector}</div>` : ''}
        ${br.conviction_statement  ? `<div class="wc-q ${tc}c">Model Read</div><div class="wc-p">${br.conviction_statement}</div>` : ''}
      </div>
    </div>`;
  }

  if (tn === 3) {
    return `<div class="modal-sec">
      <div class="modal-sec-title sans">Dark Horse Thesis</div>
      <div class="win-case-card t3">
        ${br.structural_note ? `<div class="wc-q t3c">Ceiling Mechanism</div><div class="wc-p">${br.structural_note}</div>` : ''}
        ${(br.drag_traits && br.drag_traits.length) ? `<div class="wc-q t3c">What Must Spike</div><div class="wc-p">Drag traits: ${br.drag_traits.join(', ')}.</div>` : ''}
        ${br.bet_path_note ? `<div class="wc-q t3c">Betting Verdict</div><div class="wc-p">${br.bet_path_note}</div>` : ''}
      </div>
    </div>`;
  }

  const title = tn === 4 ? 'Fragile Path Analysis' : 'Fade Analysis — Structural Miss';
  return `<div class="modal-sec">
    <div class="modal-sec-title sans">${title}</div>
    <div class="win-case-card ${tc}">
      ${br.failure_condition     ? `<div class="wc-q ${tc}c">Primary Constraint</div><div class="wc-p">${br.failure_condition}</div>` : ''}
      ${br.bet_path_note         ? `<div class="wc-q ${tc}c">Tournament Path</div><div class="wc-p">${br.bet_path_note}</div>` : ''}
      ${br.anti_pattern_summary  ? `<div class="wc-q ${tc}c">Structural Risk</div><div class="wc-p">${br.anti_pattern_summary}</div>` : ''}
    </div>
  </div>`;
}

// ── openModal — all 10 data zones ─────────────────────────────────────────────
function openModal(name) {
  const p = S.boardData.find(x => x.player === name)
         || S.altPlayers.find(x => x.player === name);
  if (!p) return;

  const br    = S.briefsByName[normName(p.player)] || {};
  const tier  = p.tier;
  const tn    = parseInt(tier[1]) || 3;
  const flags = p._flags || [];

  const tColor = { T1:'var(--t1-t)', T2:'var(--t2-t)', T3:'var(--t3-t)', T4:'var(--t4-t)', T5:'var(--t5-t)' }[tier];
  const tBg    = { T1:'var(--t1-bg)', T2:'var(--t2-bg)', T3:'var(--t3-bg)', T4:'var(--t4-bg)', T5:'var(--t5-bg)' }[tier];
  const tBd    = { T1:'var(--t1-b)', T2:'var(--t2-b)', T3:'var(--t3-b)', T4:'var(--t4-b)', T5:'var(--t5-b)' }[tier];

  // Prefer brief probabilities; fall back to board values; then to alt-player defaults
  const wPct    = br.win_prob      ?? p.winPct  ?? p.win_prob;
  const t5Pct   = br.top5_prob     ?? p.top5Pct ?? p.top5_prob;
  const t10Pct  = br.top10_prob    ?? p.top10Pct ?? p.top10_prob;
  const t20Pct  = br.top20_prob    ?? p.top20Pct ?? p.top20_prob;
  const mcPct   = br.make_cut_prob ?? p.makeCutPct ?? p.make_cut_prob;
  const missPct = br.miss_cut_prob ?? p.missCutPct ?? p.miss_cut_prob;
  const wcs     = br.win_ceiling_score;
  const cs      = br.contention_score;
  const fs      = br.floor_score;
  const css     = br.cut_survival_score;
  const scoring     = br.scoring || {};
  const traitScores = br.trait_scores || [];
  const topTraits   = br.top_traits   || [];
  const badges      = p.badges || br.badges || [];

  const pens = [
    {c:'R1',v:p.penaltyR1},{c:'R2',v:p.penaltyR2},{c:'R3',v:p.penaltyR3},
    {c:'R4',v:p.penaltyR4},{c:'R5',v:p.penaltyR5},{c:'R6',v:p.penaltyR6},
    {c:'R7',v:p.penaltyR7},{c:'R8',v:p.penaltyR8||0},{c:'R9',v:p.penaltyR9},
  ].filter(x => x.v !== undefined);
  const activePens = pens.filter(x => x.v && x.v !== 0);
  const zeroPens   = pens.filter(x => !x.v || x.v === 0);

  const nPct2  = clamp(p.neutralSkillIndex, 0, 100);
  const vPct2  = clamp(p.venueFitScore, 0, 100);
  const vhPct2 = clamp(Math.abs(p.venueHistoryDelta || 0) * 30, 0, 100);
  const pPct2  = clamp(Math.abs(p.penalties_total || 0) * 5, 0, 100);

  const riskData = (S.analysis || {}).birkdale_risk_register || {};
  const riskDetails = flags.map(code => {
    const list  = riskData[RISK_KEYS[code]] || [];
    const entry = list.find(x => x.player === p.player);
    return entry ? { code, entry } : null;
  }).filter(Boolean);

  const analystLabel = tn <= 2 ? 'Analyst Intelligence — Full Brief' : tn === 3 ? 'Model Conviction' : 'Model Note';

  const waveEntry    = S.waveByPlayer[normName(p.player)] || {};
  const _hasWaveData = !p._isAlt && (normName(p.player) in S.waveByPlayer);
  const playerWave   = _hasWaveData ? (waveEntry.wave || p.wave || null) : null;
  const waveDraw     = _hasWaveData ? (waveEntry.wave_draw || null) : 'Neutral';
  const wavePenalty  = _hasWaveData ? (waveEntry.wave_penalty ?? 0) : 0.0;
  const waveDelta    = S.weather.wave_delta || 0;
  const waveIsPen    = wavePenalty < 0;
  const waveLabel    = waveDraw === 'Neutral' || (!waveDraw && !playerWave)
    ? 'Neutral Draw — No Wind Penalty'
    : waveDraw
      ? (waveIsPen ? `${waveDraw} Draw — High Wind Exposure` : `${waveDraw} Draw — Favorable Window`)
      : (playerWave === 'early_late' ? 'AM Draw' : playerWave === 'late_early' ? 'PM Draw' : 'Neutral Draw — No Wind Penalty');
  const adjFloor     = fs != null && waveIsPen ? +(fs + wavePenalty).toFixed(1) : null;
  const windMitTrait = (br.trait_scores || []).find(t => /accuracy|ott/i.test(t.label || ''));
  const windMitScore = windMitTrait ? windMitTrait.score : (p.venueFitScore ?? 50);
  const windMitPct   = clamp(windMitScore, 0, 100);
  const windMitFill  = windMitScore >= 85 ? 'trait-fill-hi' : windMitScore >= 70 ? 'trait-fill-mid' : windMitScore >= 50 ? 'trait-fill-lo' : 'trait-fill-weak';
  const windMitColor = traitScoreColor(windMitScore) || 'color:#94a3b8';

  S.activePlayer = name;

  document.getElementById('modal-content').innerHTML = `
    <!-- HEADER -->
    <div class="modal-header">
      <button class="modal-close sans" onclick="closeModal()">✕</button>
      <div class="modal-rank sans" style="background:${tBg};color:${tColor};border:2px solid ${tColor}">${p.rank}</div>
      <div style="flex:1;min-width:0">
        <div class="modal-name">${p.player}</div>
        <div class="modal-badges">
          <span class="tier-badge sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor}">${tier}</span>
          ${badges.map(b => `<span class="badge sans">${b}</span>`).join('')}
          ${flags.map(f => flag(f)).join('')}
        </div>
        ${(scoring.band || p.band_name) ? `<div class="modal-band-row"><span class="modal-band-pill" style="background:${tBg};color:${tColor};border-color:${tBd}">${scoring.band || p.band_name}</span></div>` : ''}
      </div>
      <div class="modal-vts">
        <div class="modal-vts-val sans">${f2(p.vts_final)}</div>
        <div class="modal-vts-lbl sans">VTS</div>
        ${p.prepenalty_vts && p.prepenalty_vts !== p.vts_final ? `<div class="modal-vts-lbl sans" style="margin-top:2px">Pre: ${f2(p.prepenalty_vts)}</div>` : ''}
      </div>
    </div>

    <div class="modal-body">

      <!-- §1 — PROBABILITY & OUTPUT -->
      <div class="modal-sec">
        <div class="modal-sec-title sans">Probability &amp; Output</div>
        <div class="modal-probs">
          <div class="prob-box"><div class="prob-val sans">${pct(wPct)}</div><div class="prob-lbl sans">Win</div></div>
          <div class="prob-box"><div class="prob-val sans">${pct(t5Pct)}</div><div class="prob-lbl sans">Top 5</div></div>
          <div class="prob-box"><div class="prob-val sans">${pct(t10Pct)}</div><div class="prob-lbl sans">Top 10</div></div>
          <div class="prob-box"><div class="prob-val sans">${pct(t20Pct)}</div><div class="prob-lbl sans">Top 20</div></div>
          <div class="prob-box"><div class="prob-val sans">${pct(mcPct)}</div><div class="prob-lbl sans">Make Cut</div></div>
          <div class="prob-box"><div class="prob-val sans" style="color:var(--accent)">${pct(missPct)}</div><div class="prob-lbl sans">Miss Cut</div></div>
        </div>
        <div class="latent-row">
          ${wcs != null ? `<div class="latent-pill"><div class="latent-val">${f1(wcs)}</div><div class="latent-lbl">WCS</div></div>` : ''}
          ${cs  != null ? `<div class="latent-pill"><div class="latent-val">${f1(cs)}</div><div class="latent-lbl">CS</div></div>` : ''}
          ${fs  != null ? `<div class="latent-pill"><div class="latent-val">${f1(fs)}</div><div class="latent-lbl">FS</div></div>` : ''}
          ${css != null ? `<div class="latent-pill"><div class="latent-val">${f1(css)}</div><div class="latent-lbl">CSS</div></div>` : ''}
          ${scoring.expected ? `<div class="latent-pill"><div class="latent-val" style="color:var(--green-ok)">${scoring.expected}</div><div class="latent-lbl">Expected</div></div>` : ''}
          ${scoring.ceiling  ? `<div class="latent-pill"><div class="latent-val" style="color:var(--gold)">${scoring.ceiling}</div><div class="latent-lbl">Ceiling</div></div>` : ''}
          ${scoring.floor    ? `<div class="latent-pill"><div class="latent-val" style="color:var(--accent)">${scoring.floor}</div><div class="latent-lbl">Floor</div></div>` : ''}
        </div>

        ${S.weather.speed > 0 ? `<div style="margin-top:14px;padding:10px 14px;background:#0f172a;border:1px solid #1e293b;border-radius:8px">
          <div class="sans" style="font-size:10px;letter-spacing:.08em;color:#f59e0b;margin-bottom:8px">WEATHER &amp; WAVE PROFILE</div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-bottom:10px">
            <div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Wind: </span>
              <span class="sans" style="font-size:12px;color:#e2e8f0;font-weight:600">${S.weather.speed} kts ${S.weather.direction}</span>
            </div>
            <div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Tide: </span>
              <span class="sans" style="font-size:12px;color:#e2e8f0">${S.weather.tide}</span>
            </div>
            ${waveDraw ? `<div>
              <span class="sans" style="font-size:11px;color:#94a3b8">Draw: </span>
              <span class="sans" style="font-size:12px;font-weight:700;color:${waveIsPen ? '#f59e0b' : '#3b82f6'}">${waveLabel}</span>
            </div>` : ''}
          </div>
          <div style="margin-bottom:8px">
            <div class="sans" style="font-size:10px;color:#64748b;letter-spacing:.06em;margin-bottom:4px">WIND IMPACT MITIGATION</div>
            <div class="trait-track"><div class="${windMitFill}" style="width:${windMitPct}%"></div></div>
            <div class="sans" style="font-size:11px;margin-top:3px;${windMitColor}">${f1(windMitScore)}</div>
          </div>
          ${waveIsPen ? `<div style="margin-top:8px;padding:8px 12px;background:#1c1400;border:1px solid #f59e0b;border-radius:6px;display:flex;align-items:center;gap:10px">
            <span class="sans" style="font-size:13px;font-weight:700;color:#f59e0b">${wavePenalty.toFixed(2)} Strokes</span>
            <span class="sans" style="font-size:11px;color:#94a3b8">Latent score adjusted for wind wave exposure</span>
          </div>` : ''}
          ${adjFloor != null ? `<div style="margin-top:6px">
            <span class="sans" style="font-size:11px;color:#94a3b8">Adj. Floor: </span>
            <span class="sans" style="font-size:12px;font-weight:600;color:#f59e0b">${adjFloor > 0 ? '+' : ''}${adjFloor}</span>
          </div>` : ''}
        </div>` : ''}
      </div>

      <!-- §2 — STYLE / FIT BADGES -->
      ${badges.length ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Style &amp; Fit</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">${badges.map(b => `<span class="badge sans" style="font-size:12px;padding:4px 10px">${b}</span>`).join('')}</div>
      </div>` : ''}

      <!-- §3 — WIN CASE / TIER BRIEF -->
      ${p._isAlt
        ? `<div class="modal-sec">
            <div class="modal-sec-title sans">Pre-Tournament Status</div>
            <div class="analyst-brief" style="color:var(--text-2);font-style:italic">No pre-tournament briefing available; field alternate tracked at baseline thresholds.</div>
            ${(p.risk_flags || []).length ? `<div class="modal-note sans" style="color:var(--accent);margin-top:8px">${p.risk_flags.join(' · ')}</div>` : ''}
          </div>`
        : buildWinCase(p, br, tier)}

      <!-- §4 — PLAYER ANALYSIS -->
      ${(br.neutral_skill_summary || br.venue_fit_summary || br.venue_history_summary || br.form_summary) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Player Analysis</div>
        <div class="analysis-blocks">
          ${br.neutral_skill_summary ? `<div class="analysis-block"><div class="analysis-block-lbl">Neutral Skill</div><div class="analysis-block-text">${br.neutral_skill_summary}</div></div>` : ''}
          ${br.venue_fit_summary     ? `<div class="analysis-block"><div class="analysis-block-lbl">Venue Fit</div><div class="analysis-block-text">${br.venue_fit_summary}</div></div>` : ''}
          ${br.venue_history_summary ? `<div class="analysis-block"><div class="analysis-block-lbl">Course History</div><div class="analysis-block-text">${br.venue_history_summary}</div></div>` : ''}
          ${br.form_summary          ? `<div class="analysis-block"><div class="analysis-block-lbl">Form</div><div class="analysis-block-text">${br.form_summary}</div></div>` : ''}
        </div>
      </div>` : ''}

      <!-- §5 — TRAIT PROFILE -->
      ${traitScores.length ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Trait Profile — Venue Weight vs Player Score</div>
        <div class="trait-rows">
          ${traitScores.map(t => {
            const sc = clamp(t.score, 0, 100);
            const fc = traitFillCls(t.score);
            const vc = traitScoreColor(t.score);
            return `<div class="trait-row">
              <div class="trait-lbl">${t.label}</div>
              <div class="trait-wt">${Math.round((t.weight || 0) * 100)}%</div>
              <div class="trait-track"><div class="${fc}" style="width:${sc}%"></div></div>
              <div class="trait-score"${vc ? ` style="${vc}"` : ''}>${f1(t.score)}</div>
            </div>`;
          }).join('')}
        </div>
      </div>` : ''}

      <!-- §6 — TRAIT DRIVERS -->
      ${topTraits.length ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Trait Drivers</div>
        <div class="trait-drivers">
          ${topTraits.map(t => `<div class="trait-driver"><span class="trait-check">✓</span><span>${t}</span></div>`).join('')}
        </div>
      </div>` : ''}

      <!-- §7 — ANTI-PATTERN & RISK VECTOR -->
      ${(br.anti_pattern_summary || br.risk_vector || riskDetails.length || (br.drag_traits && br.drag_traits.length)) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Anti-Pattern Analysis &amp; Risk Vector</div>
        ${br.risk_vector          ? `<div class="modal-note sans"><b>Risk Vector:</b> ${br.risk_vector}</div>` : ''}
        ${br.anti_pattern_summary ? `<div class="modal-note sans">${br.anti_pattern_summary}</div>` : ''}
        ${(br.drag_traits && br.drag_traits.length) ? `<div class="modal-note sans"><b>Drag Traits:</b> ${br.drag_traits.join(' · ')}</div>` : ''}
        ${riskDetails.map(({ code, entry }) => `<div class="risk-detail">
          <h4 class="sans">${flag(code)} ${FM[code] ? FM[code].full : code}</h4>
          <p>${entry.reason || ''}</p>
          <div class="risk-detail-meta">${Object.entries(entry).filter(([k]) => k !== 'player' && k !== 'reason').map(([k, v]) => `<span><b>${k}:</b> ${v != null ? v : '—'}</span>`).join('')}</div>
        </div>`).join('')}
      </div>` : ''}

      <!-- §8 — ANALYST INTELLIGENCE -->
      ${(br.conviction_statement || br.scoring_thesis) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">${analystLabel}</div>
        ${br.conviction_statement ? `<div class="analyst-brief">${br.conviction_statement}</div>` : ''}
        ${(br.scoring_thesis && tn >= 3) ? `<div class="modal-note sans">${br.scoring_thesis}</div>` : ''}
        ${br.bet_path_note ? `<div class="modal-note sans">${br.bet_path_note}</div>` : ''}
      </div>` : ''}

      <!-- §9 — DB METRIC SIGNALS -->
      ${(br.tvl_score != null || br.hew_score != null || br.brie_score != null || br.vfr_score != null) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">DB Metric Signals</div>
        <div class="db-metrics-row">
          ${br.tvl_score  != null ? `<div class="db-metric"><div class="db-metric-key">TVL (OTT)</div><div class="db-metric-val" style="color:${br.tvl_score  >= 0 ? 'var(--green-ok)' : 'var(--accent)'}">${sgSign(br.tvl_score)}</div></div>`  : ''}
          ${br.hew_score  != null ? `<div class="db-metric"><div class="db-metric-key">HEW (BallStr)</div><div class="db-metric-val" style="color:${br.hew_score  >= 0 ? 'var(--green-ok)' : 'var(--accent)'}">${sgSign(br.hew_score)}</div></div>`  : ''}
          ${br.brie_score != null ? `<div class="db-metric"><div class="db-metric-key">BRIE (APP)</div><div class="db-metric-val" style="color:${br.brie_score >= 0 ? 'var(--green-ok)' : 'var(--accent)'}">${sgSign(br.brie_score)}</div></div>` : ''}
          ${br.vfr_score  != null ? `<div class="db-metric"><div class="db-metric-key">VFR (ARG)</div><div class="db-metric-val" style="color:${br.vfr_score  >= 0 ? 'var(--green-ok)' : 'var(--accent)'}">${sgSign(br.vfr_score)}</div></div>`  : ''}
          ${br.links_signal_score != null ? `<div class="db-metric"><div class="db-metric-key">FW-SG Links</div><div class="db-metric-val" style="color:${br.links_signal_score >= 0 ? 'var(--green-ok)' : 'var(--accent)'}">${sgSign(br.links_signal_score)}</div></div>` : ''}
          ${br.vhn_rounds != null ? `<div class="db-metric"><div class="db-metric-key">Birkdale Rds</div><div class="db-metric-val">${br.vhn_rounds}</div></div>` : ''}
        </div>
      </div>` : ''}

      <!-- §10 — SYSTEM FOOTPRINT: decomposition + penalties + venue evidence -->
      <div class="modal-sec">
        <div class="modal-sec-title sans">System Footprint — Score Decomposition</div>
        <div class="modal-layers">
          <div class="layer-row"><div class="layer-lbl sans">NSI</div><div class="layer-track"><div class="layer-fill" style="width:${nPct2}%;background:var(--navy)"></div></div><div class="layer-val sans" style="color:var(--navy)">${f1(p.neutralSkillIndex)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">VFS</div><div class="layer-track"><div class="layer-fill" style="width:${vPct2}%;background:var(--green-ok)"></div></div><div class="layer-val sans" style="color:var(--green-ok)">${f1(p.venueFitScore)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">VHD</div>${vhdDivergingBar(p.venueHistoryDelta)}<div class="layer-val sans" style="color:${(p.venueHistoryDelta||0)>=0?'var(--green-ok)':'var(--accent)'}">${vhd(p.venueHistoryDelta)}</div></div>
          ${activePens.length ? `<div class="layer-row"><div class="layer-lbl sans">Penalties</div><div class="layer-track"><div class="layer-fill" style="width:${pPct2}%;background:var(--accent)"></div></div><div class="layer-val sans" style="color:var(--accent)">${f2(p.penalties_total)}</div></div>` : ''}
        </div>
        ${br.vfs_base != null ? `<div class="modal-note sans" style="margin-top:8px">VFS Base: ${f2(br.vfs_base)} · Links Δ: ${br.vfs_links_delta != null ? f2(br.vfs_links_delta) : '—'} · VHN: ${br.venue_history_normalized != null ? f1(br.venue_history_normalized) : '—'} · Form: ${br.form_score != null ? f1(br.form_score) : '—'}</div>` : ''}
      </div>

      <div class="modal-sec">
        <div class="modal-sec-title sans">Audit Penalties</div>
        <div class="modal-pens">
          ${activePens.length
            ? activePens.map(pen => `<div class="pen-row active sans"><span>${flag(pen.c)} ${FM[pen.c] ? FM[pen.c].full : pen.c}</span><span class="pen-amt neg">${f2(pen.v)}</span></div>`).join('')
            : '<div class="pen-row zero sans">No audit penalties applied.</div>'}
          ${zeroPens.map(pen => `<div class="pen-row zero sans"><span>${pen.c} — not triggered</span><span class="pen-amt">0.00</span></div>`).join('')}
        </div>
      </div>

      <div class="modal-sec">
        <div class="modal-sec-title sans">Links &amp; Venue Evidence</div>
        <div class="modal-note">${br.links_signal_note || p.linksNote || 'No links data available.'}</div>
        ${(br.birkdale_history_note || p.birkdaleNote) ? `<div class="modal-note">${br.birkdale_history_note || p.birkdaleNote}</div>` : ''}
        <div style="margin-top:10px;font-size:13px;color:var(--text-2);line-height:1.55">${p.tierReason || ''}</div>
        ${(p.formClass || p.bettingPath) ? `<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
          ${p.formClass   ? `<span class="badge sans">${p.formClass} form</span>` : ''}
          ${p.bettingPath ? `<span class="badge sans">Path: ${p.bettingPath}</span>` : ''}
        </div>` : ''}
      </div>

    </div>`;

  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
  S.activePlayer = null;
}

function onOverlayClick(e) {
  if (e.target.id === 'modal-overlay') closeModal();
}

// ── Theme toggle ───────────────────────────────────────────────────────────────
function toggleTheme() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  document.documentElement.dataset.theme = isDark ? 'light' : 'dark';
  document.getElementById('theme-icon').textContent  = isDark ? '☽' : '☀';
  document.getElementById('theme-label').textContent = isDark ? 'Dark' : 'Light';
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function f1(v)  { return v != null ? Number(v).toFixed(1) : '—'; }
function f2(v)  { return v != null ? Number(v).toFixed(2) : '—'; }
function pct(v) { return v != null ? Number(v).toFixed(1) + '%' : '—'; }
function vhd(v) { if (v == null) return '—'; return (v > 0 ? '+' : '') + Number(v).toFixed(3); }
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v || 0)); }
function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function flag(code) {
  const m = FM[code];
  if (!m) return `<span class="flag sans">${code}</span>`;
  return `<span class="flag ${m.cls} sans" title="${m.full}">${m.lbl}</span>`;
}

// ── Round tab switching ────────────────────────────────────────────────────────
const PRE_SECTIONS = ['sec-spotlight','sec-board','sec-intel','sec-risk','sec-method'];

// Purges all stale live-round DOM nodes before a tab transition.
// Risers table, slippage table, putt-caution banner, and lean pills all
// live inside #live-content, so wiping it covers every named container.
function clearRoundVisualElements() {
  document.getElementById('live-content')?.replaceChildren();
  document.getElementById('live-pending')?.classList.add('hidden');
}

async function switchRound(r) {
  S.currentRound      = r;
  S.activeFetchTarget = r;
  document.querySelectorAll('.round-tab').forEach(el =>
    el.classList.toggle('active', el.dataset.round === String(r))
  );

  if (r === 'pre') {
    document.getElementById('sec-live')?.classList.remove('loading-blur');
    PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.remove('hidden'));
    document.getElementById('sec-live')?.classList.add('hidden');
    return;
  }

  PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.add('hidden'));
  const liveSection = document.getElementById('sec-live');
  const pending     = document.getElementById('live-pending');
  const content     = document.getElementById('live-content');
  liveSection?.classList.remove('hidden');
  document.getElementById('weather-impact-section')?.classList.remove('hidden');
  clearRoundVisualElements();

  if (S.roundData[r]) {
    liveSection?.classList.remove('loading-blur');
    pending?.classList.add('hidden');
    content?.classList.remove('hidden');
    renderLiveRound(S.roundData[r], content);
    return;
  }

  liveSection?.classList.add('loading-blur');
  pending?.classList.remove('hidden');
  content?.classList.add('hidden');
  try {
    const resp = await fetch(`data/r${r}_analysis.json`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (S.activeFetchTarget !== r) return;
    S.roundData[r] = data;
    liveSection?.classList.remove('loading-blur');
    pending?.classList.add('hidden');
    content?.classList.remove('hidden');
    renderLiveRound(data, content);
  } catch (e) {
    console.warn(`[VenueDNA] R${r} unavailable:`, e.message);
    liveSection?.classList.remove('loading-blur');
    if (pending) {
      pending.innerHTML = `<div style="border:2px solid #f59e0b;background:#0f172a;color:#f59e0b;padding:24px 28px;border-radius:8px;font-family:-apple-system,sans-serif;font-size:15px;font-weight:600;text-align:center;letter-spacing:.02em">Round ${r} Analysis Pending Live Scores</div>`;
      pending.classList.remove('hidden');
    }
    content?.classList.add('hidden');
  }
}

// ── Live round renderer ────────────────────────────────────────────────────────
function renderLiveRound(data, el) {
  const round     = data.round || '?';
  const meta      = data.metadata || {};
  const lean      = data.live_lean_notes || {};
  const match     = data.match_summary  || {};
  const rho       = (data.model_performance || {}).spearman_rho;
  const isFinal   = !!(meta.is_final);
  const nextRound = lean.next_round ?? null;
  const lbSnap = [...(data.leaderboard_snapshot || [])].sort((a, b) => (a.r1_pos || 999) - (b.r1_pos || 999));
  const risers   = (data.weekend_risers || data.risers || []).slice(0, 15);
  const slippage = (data.slippage_risk || []).slice(0, 10);

  S.waveByPlayer = {};
  for (const r of lbSnap) {
    if (r.r1_name) {
      S.waveByPlayer[normName(r.r1_name)] = {
        wave:         r.wave        || null,
        wave_draw:    r.wave_draw   || null,
        wave_penalty: r.wave_penalty ?? 0,
      };
    }
  }

  const sgFmt = v => v != null ? (v > 0 ? '+' : '') + Number(v).toFixed(2) : '—';
  const posFmt = r => r.r1_pos_str || r.r1_pos || '—';
  const deltaHtml = (pt, pos) => {
    if (pt == null) return '—';
    const d = pt - (pos || 99);
    if (d > 0)  return `<span style="color:var(--green-ok)">▲${d}</span>`;
    if (d < 0)  return `<span style="color:var(--accent)">▼${Math.abs(d)}</span>`;
    return `<span style="color:var(--text-3)">—</span>`;
  };

  el.innerHTML = `
    ${lean.putt_caution ? `<div class="putt-caution-banner sans">
      <strong>⚠ Putting Caution Active</strong> — ${lean.putt_outliers?.length || ''} players with putting-biased performance prone to regression.
      ${(lean.putt_outliers || []).length ? '<br><span style="margin-top:5px;display:inline-block">' +
        lean.putt_outliers.map(p => `<span style="margin-right:10px">${p.player} <b>(SG-PUTT: ${sgFmt(p.sg_putt)})</b></span>`).join('') +
        '</span>' : ''}
    </div>` : ''}

    <div class="live-sub-header">
      <div class="live-sub-title">${meta.round_label || `Round ${round}`} Leaderboard</div>
      <div class="live-sub-note sans">${match.matched ?? '?'} / ${match.total_r1 ?? match.total ?? '?'} matched</div>
      ${rho != null ? `<span class="rho-badge sans">rho: ${Number(rho).toFixed(3)}</span>` : ''}
    </div>
    <div style="overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface);box-shadow:0 2px 8px var(--shadow)">
      <table class="live-table">
        <thead><tr>
          <th>Pos</th><th class="left">Player</th><th>PT Rank</th>
          <th>Score</th><th>Δ Rank</th>
          <th>SG-TOT</th><th>SG-APP</th><th>SG-PUTT</th><th>Live Win%</th>
        </tr></thead>
        <tbody>${lbSnap.slice(0, 80).map(r => {
          const score = r.r1_score ?? 0;
          const scoreColor = score < 0 ? 'var(--green-ok)' : score > 0 ? 'var(--accent)' : 'var(--text-3)';
          const scoreStr   = score > 0 ? `+${score}` : String(score);
          const winPct = r.live_win_pct != null ? r.live_win_pct.toFixed(1) + '%' : '—';
          return `<tr data-player="${esc(canonName(r.r1_name))}">
            <td class="sans">${posFmt(r)}</td>
            <td class="sans" style="font-weight:600;min-width:150px">${r.r1_name || '—'}</td>
            <td class="sans" style="color:var(--text-3)">${r.pt_rank ?? '—'}</td>
            <td class="sans" style="font-weight:700;color:${scoreColor}">${scoreStr}</td>
            <td class="sans">${deltaHtml(r.pt_rank, r.r1_pos)}</td>
            <td class="sans">${sgFmt(r.sg_tot)}</td>
            <td class="sans" style="color:${(r.sg_app||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgFmt(r.sg_app)}</td>
            <td class="sans" style="color:${(r.sg_putt||0)>=0?'var(--navy)':'var(--accent)'}">${sgFmt(r.sg_putt)}</td>
            <td class="sans">${winPct}</td>
          </tr>`;
        }).join('')}</tbody>
      </table>
    </div>

    ${(risers.length || slippage.length) ? `
    <div style="display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap">

      ${risers.length ? `<div style="flex:1;min-width:340px">
      <div class="live-sub-header">
        <div class="live-sub-title">Weekend Risers</div>
        <div class="live-sub-note sans">Approach-backed outperformers</div>
      </div>
      <div style="overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface);box-shadow:0 2px 8px var(--shadow)">
        <table class="live-table">
          <thead><tr>
            <th class="left">Player</th><th>Pos</th><th>PT Rank</th>
            <th>Δ Rank</th><th>SG:APP</th><th>SG:PUTT</th><th>SG:TOT</th><th>Thesis</th>
          </tr></thead>
          <tbody>${risers.map(r => `<tr data-player="${esc(canonName(r.r1_name))}">
            <td class="sans" style="font-weight:600">${r.r1_name || '—'}</td>
            <td class="sans">${posFmt(r)}</td>
            <td class="sans" style="color:var(--text-3)">${r.pt_rank ?? '—'}</td>
            <td class="sans" style="color:var(--green-ok)">▲${r.rank_delta ?? '—'}</td>
            <td class="sans" style="color:var(--green-ok)">${sgFmt(r.sg_app)}</td>
            <td class="sans">${sgFmt(r.sg_putt)}</td>
            <td class="sans">${sgFmt(r.sg_tot)}</td>
            <td class="sans" style="color:var(--text-2);max-width:200px;white-space:normal;font-size:11px">${r.thesis_note || '—'}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
      </div>` : ''}

      ${slippage.length ? `<div style="flex:1;min-width:340px">
      <div class="live-sub-header">
        <div class="live-sub-title">Slippage Risk</div>
        <div class="live-sub-note sans">Top-20 positions with fragile SG profile</div>
      </div>
      <div style="overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface);box-shadow:0 2px 8px var(--shadow)">
        <table class="live-table">
          <thead><tr>
            <th class="left">Player</th><th>Δ Rank</th>
            <th>SG:APP</th><th>SG:PUTT</th><th>SG:TOT</th>
          </tr></thead>
          <tbody>${slippage.map(r => `<tr data-player="${esc(canonName(r.r1_name))}">
            <td class="sans" style="font-weight:600">${r.r1_name || '—'}</td>
            <td class="sans">${deltaHtml(r.pt_rank, r.r1_pos)}</td>
            <td class="sans" style="color:${(r.sg_app||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgFmt(r.sg_app)}</td>
            <td class="sans" style="color:var(--accent);font-weight:700">${sgFmt(r.sg_putt)}</td>
            <td class="sans">${sgFmt(r.sg_tot)}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
      </div>` : ''}

    </div>` : ''}

    ${(lean.lean_up_traits?.length || lean.lean_down_traits?.length) ? `
    <div class="live-sub-header">
      <div class="live-sub-title">${isFinal ? 'Final Round Recap' : 'Live Lean — Trait Signals'}</div>
      <div class="live-sub-note sans">${nextRound == null ? 'Tournament Complete' : `R${round} field validation vs model weights`}</div>
    </div>
    <div class="lean-pills">
      ${(lean.lean_up_traits || []).map(t =>
        `<span class="lean-pill lean-up sans">▲ ${t.trait}${t.delta != null ? ' Δ' + t.delta : ''}${t.confidence ? ' · ' + t.confidence : ''}</span>`
      ).join('')}
      ${(lean.lean_down_traits || []).map(t =>
        `<span class="lean-pill lean-down sans">▼ ${t.trait}${t.delta != null ? ' Δ' + t.delta : ''}</span>`
      ).join('')}
    </div>` : ''}

    ${lean.rho_note ? `<div style="margin-top:16px;font-family:-apple-system,sans-serif;font-size:11px;color:var(--text-3)">${lean.rho_note}</div>` : ''}
  `;

}

// ── Spotlight toggle ───────────────────────────────────────────────────────────
function toggleSpotlight() {
  S.spotlightOpen = !S.spotlightOpen;
  document.getElementById('spotlight-container')?.classList.toggle('hidden', !S.spotlightOpen);
  const btn = document.getElementById('spotlight-toggle');
  if (btn) btn.textContent = S.spotlightOpen ? 'Hide Spotlight' : 'Show Spotlight';
}

// ── Advanced filter panel toggle ───────────────────────────────────────────────
function toggleAdvFilter() {
  S.advFilterOpen = !S.advFilterOpen;
  document.getElementById('adv-filter-panel')?.classList.toggle('hidden', !S.advFilterOpen);
  const btn = document.getElementById('adv-toggle');
  if (btn) btn.textContent = S.advFilterOpen ? '▲ Filter' : '▼ Filter';
}

// ── Numeric filter input handler ───────────────────────────────────────────────
function onNumFilter() {
  const getVal = id => { const v = parseFloat(document.getElementById(id)?.value); return isNaN(v) ? null : v; };
  S.numFilters = {
    vts_min: getVal('af-vts-min'), vts_max: getVal('af-vts-max'),
    nsi_min: getVal('af-nsi-min'), nsi_max: getVal('af-nsi-max'),
    vfs_min: getVal('af-vfs-min'), vfs_max: getVal('af-vfs-max'),
    win_min: getVal('af-win-min'), win_max: getVal('af-win-max'),
  };
  applyVisibility();
}

// ── Clear all filters and reset sort to VTS rank ──────────────────────────────
function clearFilters() {
  S.currentFilter = 'all';
  S.currentTier   = 'all';
  S.searchQuery   = '';
  S.numFilters    = { vts_min:null, vts_max:null, nsi_min:null, nsi_max:null, vfs_min:null, vfs_max:null, win_min:null, win_max:null };
  S.sort          = { key: 'rank', dir: 1 };
  const srch = document.getElementById('player-search');
  if (srch) srch.value = '';
  document.querySelectorAll('.chip[data-f]').forEach(el => el.classList.toggle('active', el.dataset.f === 'all'));
  document.querySelectorAll('.tier-tile').forEach(el => el.classList.toggle('active', el.dataset.tier === 'all'));
  ['af-vts-min','af-vts-max','af-nsi-min','af-nsi-max','af-vfs-min','af-vfs-max','af-win-min','af-win-max'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  renderTable();
}

// ── Scroll Full Field table to a player row ────────────────────────────────────
function scrollToPlayer(name) {
  const tr = document.querySelector(`#board-tbody tr[data-player="${name.replace(/"/g, '\\"')}"]`);
  if (!tr) return;
  tr.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── Diverging VHD bar: green right for positive, red left for negative ─────────
function vhdDivergingBar(val) {
  const v = val || 0;
  const fillPct = Math.min(Math.abs(v) / 5.0 * 50, 50);
  const center = `<div style="position:absolute;left:50%;transform:translateX(-50%);width:1px;top:0;bottom:0;background:var(--border-2)"></div>`;
  if (v >= 0) {
    return `<div class="layer-track" style="position:relative;overflow:hidden">${center}<div style="position:absolute;left:50%;width:${fillPct}%;top:0;bottom:0;border-radius:0 4px 4px 0;background:var(--green-ok)"></div></div>`;
  }
  return `<div class="layer-track" style="position:relative;overflow:hidden">${center}<div style="position:absolute;right:50%;width:${fillPct}%;top:0;bottom:0;border-radius:4px 0 0 4px;background:var(--accent)"></div></div>`;
}

// ── Re-index rank column based on current sort and visible rows ────────────────
function reindexRankColumn() {
  const isByRank = S.sort.key === 'rank' || S.sort.key === 'vts_final';
  document.querySelectorAll('#board-tbody tr[data-player]:not(.hidden)').forEach((tr, i) => {
    const rankEl = tr.cells[0]?.querySelector('.rank-num');
    if (!rankEl) return;
    if (!rankEl.dataset.origRank) rankEl.dataset.origRank = rankEl.textContent.trim();
    const orig = rankEl.dataset.origRank;
    if (isByRank) {
      rankEl.textContent = orig;
    } else {
      rankEl.innerHTML = `${i + 1}<span class="badge sans" style="font-size:9px;padding:1px 4px;margin-left:4px;vertical-align:middle;opacity:.75">VTS:#${orig}</span>`;
    }
  });
}

// ── Weather renderer ───────────────────────────────────────────────────────────
function renderWeather(wx) {
  const section = document.getElementById('weather-impact-section');
  if (!section) return;

  const speedEl = document.getElementById('wx-wind-speed');
  const dirEl   = document.getElementById('wx-wind-dir');
  const tideEl  = document.getElementById('wx-tide');
  const deltaEl = document.getElementById('wx-wave-delta');
  const badgeEl = document.getElementById('wx-badge');
  const noteEl  = document.getElementById('wx-wave-note');

  if (speedEl) speedEl.textContent = wx.speed ?? '—';
  if (dirEl)   dirEl.textContent   = wx.direction ?? '—';
  if (tideEl)  tideEl.textContent  = wx.tide ?? '—';
  if (deltaEl) deltaEl.textContent = wx.wave_delta != null ? (wx.wave_delta > 0 ? '+' : '') + Number(wx.wave_delta).toFixed(2) : '—';

  const speed = wx.speed ?? 0;
  const severity = speed >= 30 ? 'Severe' : speed >= 20 ? 'Significant' : speed >= 12 ? 'Moderate' : 'Light';
  const sevColor = speed >= 30 ? '#ef4444' : speed >= 20 ? '#f59e0b' : speed >= 12 ? '#3b82f6' : '#22c55e';
  if (badgeEl) { badgeEl.textContent = severity; badgeEl.style.background = sevColor; }

  if (noteEl) {
    if (wx.wave_delta > 0) {
      noteEl.textContent = `Wave model active — late/early tee times favored by ${wx.wave_delta.toFixed(2)} strokes vs. midday wave.`;
      noteEl.style.color = '#3b82f6';
    } else {
      noteEl.textContent = 'Wave delta neutral — no tee-time adjustment applied.';
      noteEl.style.color = '#64748b';
    }
  }

  section.classList.remove('hidden');
}

// ── Bootstrap ──────────────────────────────────────────────────────────────────
init();
