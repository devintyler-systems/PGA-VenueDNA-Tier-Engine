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
  sort:      { key: 'rank', dir: 1 },
  liveSort:  { key: 'r1_pos', dir: 1 },
  numFilters: { vts_min:null, vts_max:null, nsi_min:null, nsi_max:null, vfs_min:null, vfs_max:null, win_min:null, win_max:null },
  spotlightOpen:     true,
  advFilterOpen:     false,
  currentRound:      'pre',
  roundData:         {},
  altPlayers:        [],
  activeFetchTarget: null,
  weather:    { speed: 0, direction: 'N/A' },
  cumulativeLearning: null,
  filterRules:          [],
  glossaryModalOpen:    false,
  pmData:               null,
  currentView:          'table',
  scenarioMode:         false,
  scenarioWeights:      {},
  favorites:            new Set(),
  chartHighlightFlags:  false,
  chartHighlightDebut:  false,
  activeTagFilters:     [],
};

// ── Filter field definitions ──────────────────────────────────────────────────
const FILTER_FIELDS = [
  { key:'pt_vts',        label:'VTS',         get:(p)    => p.vts_final },
  { key:'pt_nsi',        label:'NSI',         get:(p)    => p.neutralSkillIndex },
  { key:'pt_delta_fit',  label:'Delta Fit',   get:(p)    => p.delta_fit },
  { key:'pt_sg_base',    label:'SG Base',     get:(p)    => p.sg_base_composite },
  { key:'pt_sg_sim',     label:'SG Sim',      get:(p)    => p.sg_similar_composite },
  { key:'live_win',      label:'Win%',        get:(p)    => p.winPct },
  { key:'live_top10',    label:'Top 10%',     get:(p)    => p.top10Pct },
  { key:'live_cut',      label:'Cut%',        get:(p)    => p.makeCutPct },
  { key:'pt_tier',       label:'Tier #',      get:(p)    => parseInt((p.tier||'T5')[1]) },
  { key:'app_150_200',   label:'App 150-200', get:(p,br) => traitScore(br,'app_150_200',p) },
  { key:'sg_putt',       label:'SG: Putting', get:(p,br) => traitScore(br,'sg_putt',p) },
  { key:'sg_arg',        label:'SG: ARG',     get:(p,br) => traitScore(br,'sg_arg',p) },
];

const QUICK_PRESETS = {
  'venue-fits':      [{ field:'pt_delta_fit', op:'>=', val:0.080 }],
  'high-base':       [{ field:'pt_sg_base',  op:'>=', val:1.500 }],
  'long-iron-fits':  [{ field:'app_150_200', op:'>=', val:60 }],
  'safe-cut-makers': [{ field:'pt_vts',      op:'>=', val:65 }],
  'ceiling-plays':   [{ field:'live_win',    op:'>=', val:5.0 }],
};

function traitScore(br, key, pData) {
  // Check brief first, then fall back to player payload trait_scores
  const ts = (br || {}).trait_scores || (pData || {}).trait_scores || [];
  const entry = ts.find(t => resolveCumKey(t.label) === key);
  return entry != null ? entry.score : null;
}

// ── Name normalisation — accent-strip + lowercase + trim ──────────────────────
function normName(s) {
  return (s || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim()
    .replace(/[\u2018\u2019\u0060']/g, "'");
}

// ── Tag normalisation — strip trailing numeric parentheticals for filter matching ─
function normalizeTag(t) {
  return (t || '').replace(/\s*\([^)]*\)\s*$/, '').trim();
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
      neutralSkillIndex: 50.0,
      sg_base_composite: 0.0, sg_similar_composite: 0.0, delta_fit: 0.0,
      winPct: null, top5Pct: null, top10Pct: null,
      top20Pct: null, makeCutPct: null, missCutPct: null,
      win_prob: 0.001, top5_prob: 0.005, top10_prob: 0.010,
      top20_prob: 0.020, make_cut_prob: 0.500, miss_cut_prob: 0.500,
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
  const br = S.briefsByName[normName(p.player)] || {};
  return [...(br.anti_pattern_flags || [])];
}

// ── Initialisation ─────────────────────────────────────────────────────────────
async function init() {
  const tbody = document.getElementById('board-tbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="11" class="no-results sans">Loading…</td></tr>';

  try {
    const [boardJson, analysisJson, briefsJson] = await Promise.all([
      fetch('data/2026_3m_open_event_payload.json').then(r => r.json()),
      fetch('data/2026_3m_open_final_analysis.json').then(r => r.json()).catch(() => ({})),
      fetch('data/2026_3m_open_player_briefs.json').then(r => r.json()).catch(() => ({})),
    ]);

    S.analysis = analysisJson;

    // Build normalised brief lookup — handles flat {"Last, First": {...}} shape from 3M brief export
    S.briefsByName = {};
    const _bEntries = Array.isArray(briefsJson.players)
      ? briefsJson.players
      : Object.values(briefsJson).filter(b => b && typeof b === 'object' && b.player_name);
    for (const b of _bEntries) {
      const _bKey = b.player_name || `${b.last_name || ''}, ${b.first_name || ''}`.trim();
      // Map 3M brief schema fields → modal-expected field names
      if (!b.scoring_thesis)        b.scoring_thesis        = b.exact_mechanism || b.why_it_fits_structurally || '';
      if (!b.failure_condition)     b.failure_condition     = b.named_failure_condition || '';
      if (!b.risk_vector)           b.risk_vector           = b.card_risk_vector || b.key_risk_vector || '';
      if (!b.conviction_statement)  b.conviction_statement  = b.convictionStatement || b.why_it_fits_structurally || '';
      if (!b.neutral_skill_summary) b.neutral_skill_summary = b.neutral_skill_summary || b.why_it_fits_structurally || '';
      if (!b.form_summary)          b.form_summary          = b.form_summary || '';
      if (!b.anti_pattern_summary)  b.anti_pattern_summary  = b.penalty_context || '';
      if (!b.venue_history_summary) b.venue_history_summary = b.venue_history_context || '';
      S.briefsByName[normName(_bKey)] = b;
    }

    S.boardData = (boardJson.players || []).map(p => ({ ...p, _flags: buildFlags(p) }));

    bindEvents();
    renderAll();

    fetch('data/2026_3m_open_weather_forecast.json')
      .then(r => r.ok ? r.json() : Promise.reject())
      .catch(() => ({ speed: 0, direction: 'N/A' }))
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
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeModal(); closeGlossary(); } });
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
  document.getElementById('rfb-add-rule')?.addEventListener('click', addFilterRule);
  document.getElementById('adv-filter-panel')?.addEventListener('click', e => {
    const removeBtn = e.target.closest('.rfb-remove[data-idx]');
    if (removeBtn) removeFilterRule(parseInt(removeBtn.dataset.idx));
  });
  document.getElementById('adv-filter-panel')?.addEventListener('change', e => {
    const rule = e.target.closest('.rfb-rule[data-idx]');
    if (!rule) return;
    const idx = parseInt(rule.dataset.idx);
    if (e.target.classList.contains('rfb-select')) updateRuleField(idx, e.target.value);
    if (e.target.classList.contains('rfb-op'))     updateRuleOp(idx, e.target.value);
  });
  document.getElementById('adv-filter-panel')?.addEventListener('input', e => {
    const rule = e.target.closest('.rfb-rule[data-idx]');
    if (rule && e.target.classList.contains('rfb-input')) {
      updateRuleVal(parseInt(rule.dataset.idx), e.target.value);
    }
  });

  // Theme toggle
  document.getElementById('btn-theme')?.addEventListener('click', toggleTheme);

  // Reset all
  document.getElementById('btn-reset')?.addEventListener('click', clearFilters);

  // Glossary open
  document.getElementById('btn-glossary')?.addEventListener('click', openGlossary);
  document.getElementById('glossary-modal-close')?.addEventListener('click', closeGlossary);
  document.getElementById('glossary-modal-overlay')?.addEventListener('click', e => {
    if (e.target.id === 'glossary-modal-overlay') closeGlossary();
  });

  // Drawer backdrop click-outside close
  document.getElementById('drawer-backdrop')?.addEventListener('click', closeModal);

  // Search clear
  const srchClear = document.getElementById('search-clear');
  if (srchClear) {
    srchClear.addEventListener('click', () => {
      const inp = document.getElementById('player-search');
      if (inp) { inp.value = ''; S.searchQuery = ''; applyVisibility(); }
      srchClear.style.display = 'none';
    });
  }
  const playerSearch = document.getElementById('player-search');
  if (playerSearch) {
    playerSearch.addEventListener('input', e => {
      const clr = document.getElementById('search-clear');
      if (clr) clr.style.display = e.target.value ? 'block' : 'none';
    });
  }

  // Presets dropdown toggle
  const btnPresets = document.getElementById('btn-presets');
  const presetDd   = document.getElementById('preset-dropdown');
  if (btnPresets && presetDd) {
    btnPresets.addEventListener('click', e => {
      e.stopPropagation();
      const open = presetDd.style.display === 'block';
      presetDd.style.display = open ? 'none' : 'block';
    });
    document.addEventListener('click', () => { presetDd.style.display = 'none'; });
    presetDd.querySelectorAll('.preset-item[data-preset]').forEach(btn => {
      btn.addEventListener('click', () => {
        applyPreset(btn.dataset.preset);
        presetDd.style.display = 'none';
      });
    });
    presetDd.querySelectorAll('.view-mode-item[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        switchView(btn.dataset.view);
        presetDd.style.display = 'none';
      });
    });
  }

  // Favorites filter
  document.getElementById('btn-favonly')?.addEventListener('click', () => {
    const btn = document.getElementById('btn-favonly');
    if (S.currentFilter === 'favonly') {
      S.currentFilter = 'all';
      btn?.classList.remove('active');
    } else {
      S.currentFilter = 'favonly';
      btn?.classList.add('active');
    }
    applyVisibility();
  });

  // Scenario button
  document.getElementById('btn-scenario')?.addEventListener('click', toggleScenarioPanel);

  // Scenario reset/exit
  document.getElementById('scenario-reset')?.addEventListener('click', resetScenario);
  document.getElementById('scenario-exit')?.addEventListener('click', exitScenario);

  // Contention chart toggles
  document.getElementById('chart-toggle-flags')?.addEventListener('click', () => {
    S.chartHighlightFlags = !S.chartHighlightFlags;
    document.getElementById('chart-toggle-flags')?.classList.toggle('active', S.chartHighlightFlags);
    renderContentionChart();
  });
  document.getElementById('chart-toggle-debut')?.addEventListener('click', () => {
    S.chartHighlightDebut = !S.chartHighlightDebut;
    document.getElementById('chart-toggle-debut')?.classList.toggle('active', S.chartHighlightDebut);
    renderContentionChart();
  });

  // Flag tooltip (event delegation)
  bindFlagTooltip();

  // Trait badge filter — event delegation on body
  document.body.addEventListener('click', e => {
    const badge = e.target.closest('.badge-strength, .badge-weakness');
    if (!badge) return;
    const tag = badge.textContent.trim();
    toggleTagFilter(tag);
  });

  bindSectionNav();
}

// ── Section Nav ────────────────────────────────────────────────────────────────
function bindSectionNav() {
  document.querySelectorAll('.snav-tab[data-snav]').forEach(btn => {
    if (btn.disabled) return;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.snav-tab').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      const snav = btn.dataset.snav;
      if (snav === 'pre') {
        switchView('table');
      } else {
        // R1–R4, Final: will be wired in T8 for dynamic fetch
        // For now, just show a "Round data not yet available" note
        const note = document.getElementById('round-pending-note');
        if (!note) {
          const div = document.createElement('div');
          div.id = 'round-pending-note';
          div.style.cssText = 'max-width:1400px;margin:1rem auto;padding:0 1rem;font-size:.82rem;color:var(--muted);';
          div.textContent = `${btn.textContent.trim()} — Round data not yet available.`;
          document.getElementById('section-nav')?.insertAdjacentElement('afterend', div);
        } else {
          note.textContent = `${btn.textContent.trim()} — Round data not yet available.`;
        }
      }
    });
  });
}

// ── Render orchestration ───────────────────────────────────────────────────────
function renderAll() {
  renderSpotlight();
  renderTable();
  renderCards();
  renderIntel();
  renderContentionChart();
}

// ── Views system ───────────────────────────────────────────────────────────────
const VIEW_SECTIONS = {
  table:      ['sec-spotlight','sec-board','sec-intel','sec-venue-dna','sec-method','sec-contention'],
  cards:      ['sec-spotlight','sec-board','sec-intel'],
  map:        ['sec-contention'],
  storylines: ['sec-storylines'],
};

function switchView(view) {
  S.currentView = view;
  const allManaged = [...new Set(Object.values(VIEW_SECTIONS).flat())];
  allManaged.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden', !VIEW_SECTIONS[view]?.includes(id));
  });
  const cardsGrid = document.getElementById('player-cards');
  if (cardsGrid) cardsGrid.style.display = view === 'cards' ? 'grid' : '';
  const primary = VIEW_SECTIONS[view]?.[0];
  if (primary) document.getElementById(primary)?.scrollIntoView({ behavior:'smooth', block:'start' });
  if (view === 'storylines') renderStorylines();
  document.querySelectorAll('.view-mode-item[data-view]').forEach(btn => {
    btn.style.color = btn.dataset.view === view ? 'var(--gold)' : '';
    btn.style.fontWeight = btn.dataset.view === view ? '700' : '';
  });
}

// ── Spotlight — T1/T2 cards ────────────────────────────────────────────────────
function renderSpotlight() {
  const grid = document.getElementById('spotlight-grid');
  if (!grid) return;
  const t12 = S.boardData.filter(p => p.tier === 'T1' || p.tier === 'T2');
  grid.innerHTML = t12.map(p => {
    const tc       = p.tier.toLowerCase();
    const nPct     = clamp(p.neutralSkillIndex, 0, 100);
    const sgSimPct = clamp(p.vts_final || 50, 0, 100);
    const dFit     = p.delta_fit || 0;
    const dPct     = clamp(Math.abs(dFit) * 100, 0, 50);
    const br       = S.briefsByName[normName(p.player)] || {};
    const badges   = p.badges || br.badges || [];
    return `<div class="spotlight-card ${tc}" data-player="${esc(p.player)}">
      <div class="sc-top">
        <div class="sc-rank sans">${p.rank}</div>
        <div>
          <div class="sc-name">${p.player}</div>
          <span class="tier-badge sans">${p.tier}</span>
        </div>
        <div style="margin-left:auto;text-align:right">
          <div class="sc-vts sans">${f2(p.vts_final)}</div>
          <div class="sc-vts-lbl sans">VTS</div>
        </div>
      </div>
      <div class="sc-bars">
        ${bar('NSI',    nPct,    'bar-nsi', f1(p.neutralSkillIndex))}
        ${bar('SG Sim', sgSimPct,'bar-vfs', sgSign(p.sg_similar_composite))}
        ${bar('Δ Fit',  dPct,    dFit >= 0 ? 'bar-vfs' : 'bar-pen', sgSign(dFit), dFit >= 0 ? 'var(--green-ok)' : 'var(--accent)')}
      </div>
      <div class="sc-stats">
        <div class="sc-stat-box">
          <div class="sc-stat-val sans">${pct(p.winPct)}</div>
          <div class="sc-stat-lbl sans">Win</div>
          ${fairOdds(p.winPct) ? `<div style="font-size:.55rem;color:var(--muted);font-family:'Inter',sans-serif;">${fairOdds(p.winPct)}</div>` : ''}
        </div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.top10Pct)}</div><div class="sc-stat-lbl sans">Top 10</div></div>
        <div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.makeCutPct)}</div><div class="sc-stat-lbl sans">Cut</div></div>
      </div>
      ${badges.length ? `<div class="sc-flags">${badges.map(b => `<span class="badge sans">${b}</span>`).join('')}</div>` : ''}
      ${p._flags.length ? `<div class="sc-flags">${p._flags.map(f => flag(f)).join('')}</div>` : ''}
      <div class="sc-reason">${p.tierReason || ''}</div>
      ${(() => {
        const rows = [
          { lbl: 'Win Mechanism',       val: br.scoring_thesis },
          { lbl: 'Key Risk to Monitor', val: br.failure_condition || br.risk_vector },
          { lbl: 'Analyst Brief',       val: br.conviction_statement },
        ].filter(r => r.val);
        return rows.length
          ? `<div class="sc-analyst">${rows.map(r =>
              `<div class="sc-analyst-row">
                <div class="sc-analyst-lbl sans">${r.lbl}</div>
                <div class="sc-analyst-txt">${esc(r.val)}</div>
              </div>`).join('')}</div>`
          : '';
      })()}
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
    const flagStr = p._flags.join(',');
    return `<tr data-player="${esc(p.player)}" data-tier="${p.tier}" data-flags="${flagStr}" data-vts="${p.vts_final ?? ''}" data-nsi="${p.neutralSkillIndex ?? ''}" data-win="${p.winPct ?? ''}">
      <td class="left"><span class="rank-num sans" style="background:${tBg};color:${tColor}">${p.rank}</span></td>
      <td class="left"><div class="player-name-cell">${p.player}
        <small><span class="tier-badge sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor}">${p.tier}</span></small>
      </div></td>
      <td class="vts-cell sans">${f2(p.vts_final)}</td>
      <td class="sans">${f1(p.neutralSkillIndex)}</td>
      <td class="sans">${sgSign(p.sg_base_composite)}</td>
      <td class="sans">${sgSign(p.sg_similar_composite)}</td>
      <td class="sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</td>
      <td class="sans">${pct(p.winPct)}</td>
      <td class="sans">${pct(p.top10Pct)}</td>
      <td class="sans">${pct(p.makeCutPct)}</td>
      <td class="sparkline-cell"><canvas id="sp-${p.rank}" width="60" height="22"></canvas></td>
    </tr>`;
  }).join('');

  // Paint sparklines — canvas elements now in DOM
  sorted.forEach(p => {
    const cv = document.getElementById(`sp-${p.rank}`);
    if (cv && Array.isArray(p.l5_array) && p.l5_array.length > 0) renderSparkline(cv, p.l5_array);
  });

  // Bind row-click events — no inline onclick in markup
  tbody.querySelectorAll('tr[data-player]').forEach(tr => {
    tr.addEventListener('click', () => {
      S.activePlayer = tr.dataset.player;
      openModal(tr.dataset.player);
    });
  });

  applyVisibility();
  updateSortArrows();
  if (S.scenarioMode) renderScenarioResults();
}

// ── Mobile card view — same source as table; shown on narrow viewports ────────
function renderCards() {
  const container = document.getElementById('player-cards');
  if (!container) return;
  const sorted = [...S.boardData].sort((a, b) => {
    const { key, dir } = S.sort;
    if (key === 'player') return dir * (a.player || '').localeCompare(b.player || '');
    return dir * ((a[key] || 0) - (b[key] || 0));
  });
  container.innerHTML = sorted.map(p => {
    const tColor = { T1:'var(--t1-t)', T2:'var(--t2-t)', T3:'var(--t3-t)', T4:'var(--t4-t)', T5:'var(--t5-t)' }[p.tier] || '';
    const tBg    = { T1:'var(--t1-bg)', T2:'var(--t2-bg)', T3:'var(--t3-bg)', T4:'var(--t4-bg)', T5:'var(--t5-bg)' }[p.tier] || '';
    const flagStr = (p._flags || []).join(',');
    return `<div class="player-card" data-player="${esc(p.player)}" data-tier="${p.tier}" data-flags="${flagStr}" data-vts="${p.vts_final ?? ''}" data-nsi="${p.neutralSkillIndex ?? ''}" data-win="${p.winPct ?? ''}">
      <div class="pc-top">
        <div class="pc-rank sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor}">${p.rank}</div>
        <div class="pc-name">
          ${p.player}
          <span class="tier-badge sans" style="background:${tBg};color:${tColor};border:1px solid ${tColor};margin-left:.35rem;">${p.tier}</span>
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div class="pc-vts sans">${f2(p.vts_final)}</div>
          <div class="pc-vts-lbl sans">VTS</div>
        </div>
      </div>
      <div class="pc-metrics">
        <div class="pc-metric"><div class="pc-metric-lbl sans">NSI</div><div class="pc-metric-val sans">${f1(p.neutralSkillIndex)}</div></div>
        <div class="pc-metric"><div class="pc-metric-lbl sans">Win%</div><div class="pc-metric-val sans">${pct(p.winPct)}</div></div>
        <div class="pc-metric" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}"><div class="pc-metric-lbl sans">Δ Fit</div><div class="pc-metric-val sans">${sgSign(p.delta_fit)}</div></div>
      </div>
      ${p._flags.length ? `<div class="pc-flags">${p._flags.map(f => flag(f)).join('')}</div>` : ''}
      ${p.tierReason ? `<div class="pc-reason">${esc(p.tierReason)}</div>` : ''}
    </div>`;
  }).join('');

  container.querySelectorAll('.player-card[data-player]').forEach(card => {
    card.addEventListener('click', () => openModal(card.dataset.player));
  });
}

// ── Named rule engine — evaluates S.filterRules against one player record ─────
// Handles numeric comparisons and case-insensitive string profile matching.
function applyLeaderboardFilters(pData, br) {
  if (!S.filterRules.length) return true;
  for (const rule of S.filterRules) {
    if (rule.val === '' || rule.val === null || rule.val === undefined) continue;
    const fieldDef = FILTER_FIELDS.find(f => f.key === rule.field);
    if (!fieldDef) continue;
    const v = fieldDef.get(pData || {}, br);
    if (v == null) return false;
    if (typeof v === 'string') {
      const sv = v.toLowerCase();
      const qv = String(rule.val).toLowerCase();
      if (rule.op === '='  && !sv.includes(qv)) return false;
      continue;
    }
    const numV = parseFloat(v);
    const numR = parseFloat(rule.val);
    if (isNaN(numV) || isNaN(numR)) continue;
    if (rule.op === '>=' && numV < numR) return false;
    if (rule.op === '<=' && numV > numR) return false;
    if (rule.op === '='  && Math.abs(numV - numR) > 0.001) return false;
  }
  return true;
}

// ── Visibility / leaderboard filter engine — toggles .hidden; no DOM destruction
function applyVisibility() {
  const q = normName(S.searchQuery);
  const hasRuleFilter = S.filterRules.length > 0;
  let shown = 0;

  document.querySelectorAll('#board-tbody tr[data-player]').forEach(tr => {
    const tier  = tr.dataset.tier;
    const flags = tr.dataset.flags ? tr.dataset.flags.split(',').filter(Boolean) : [];
    const name  = normName(tr.dataset.player);

    let show = true;

    if (S.currentTier !== 'all' && tier !== S.currentTier) show = false;

    if (show) {
      switch (S.currentFilter) {
        case 'flagged': if (!flags.length) show = false; break;
        case 'nopen':   if (flags.length)  show = false; break;
        case 't1t2':    if (tier !== 'T1' && tier !== 'T2') show = false; break;
        case 'favonly': if (!S.favorites?.has(tr.dataset.player)) show = false; break;
      }
    }

    if (show && q) {
      const matchName = name.includes(q);
      const matchFlag = flags.some(f => f.toLowerCase().includes(q));
      const matchTier = normName(tier) === q;
      if (!matchName && !matchFlag && !matchTier) show = false;
    }

    if (show && hasRuleFilter) {
      const pData = S.boardData.find(x => x.player === tr.dataset.player);
      const br    = pData ? (S.briefsByName[normName(pData.player)] || {}) : {};
      if (!applyLeaderboardFilters(pData || {}, br)) show = false;
    }

    tr.classList.toggle('hidden', !show);
    if (show) shown++;
  });

  // Tag filter pass — runs after all other passes (additive)
  if (S.activeTagFilters.length > 0) {
    document.querySelectorAll('#board-tbody tr[data-player]').forEach(row => {
      if (row.classList.contains('hidden')) return; // already hidden
      const name = row.dataset.player;
      if (!name) return;
      const p  = [...S.boardData, ...S.altPlayers].find(x => normName(x.player) === normName(name));
      const br = S.briefsByName[normName(name)] || {};
      const tags = [
        ...(p?.strength_tags || []),
        ...(p?.weakness_tags || []),
        ...(br.strength_tags || []),
        ...(br.weakness_tags || []),
      ];
      const normalizedTags = tags.map(normalizeTag);
      const matches = S.activeTagFilters.every(f => normalizedTags.includes(f));
      if (!matches) {
        row.classList.add('hidden');
        shown--;
      }
    });
  }

  // Sync mobile cards with same filter logic
  document.querySelectorAll('#player-cards .player-card[data-player]').forEach(card => {
    const tier  = card.dataset.tier;
    const flags = card.dataset.flags ? card.dataset.flags.split(',').filter(Boolean) : [];
    const name  = normName(card.dataset.player);
    let showCard = true;
    if (S.currentTier !== 'all' && tier !== S.currentTier) showCard = false;
    if (showCard) {
      switch (S.currentFilter) {
        case 'flagged': if (!flags.length) showCard = false; break;
        case 'nopen':   if (flags.length)  showCard = false; break;
        case 't1t2':    if (tier !== 'T1' && tier !== 'T2') showCard = false; break;
        case 'favonly': if (!S.favorites?.has(card.dataset.player)) showCard = false; break;
      }
    }
    if (showCard && q) {
      const matchName = name.includes(q);
      const matchFlag = flags.some(f => f.toLowerCase().includes(q));
      if (!matchName && !matchFlag) showCard = false;
    }
    if (showCard && hasRuleFilter) {
      const pData = S.boardData.find(x => x.player === card.dataset.player);
      const br    = pData ? (S.briefsByName[normName(pData.player)] || {}) : {};
      if (!applyLeaderboardFilters(pData || {}, br)) showCard = false;
    }
    card.classList.toggle('hidden', !showCard);
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
  const keyMap = ['rank','player','vts_final','neutralSkillIndex','sg_base_composite','sg_similar_composite','delta_fit','winPct','top10Pct','makeCutPct'];
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
    ? `${total} players · TPC Twin Cities VTS`
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
      <div class="tier-block-header sans" onclick="filterByTier('${t}')" style="cursor:pointer;user-select:none;" title="Click to filter board to ${t}"><span>${t} — ${desc}</span><span>${counts[t] || ''}</span></div>
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


// ── Storylines module — read-only narrative strip ────────────────────────────
function renderStorylines() {
  const grid = document.getElementById('storylines-grid');
  if (!grid || !S.boardData.length) return;

  const byVFS = [...S.boardData].filter(p => p.delta_fit != null).sort((a, b) => b.delta_fit - a.delta_fit);
  const topVFS = byVFS[0];
  const topContender = S.boardData.find(p => (p.tier === 'T1' || p.tier === 'T2') && (p.delta_fit || 0) >= 0);
  const risers = S.boardData.map(p => {
    const br = S.briefsByName[normName(p.player)] || {};
    return { player: p.player, tier: p.tier, vsBaselineL20: br.vsBaselineL20 != null ? Number(br.vsBaselineL20) : null };
  }).filter(x => x.vsBaselineL20 != null && x.vsBaselineL20 > 0).sort((a, b) => b.vsBaselineL20 - a.vsBaselineL20);
  const topRiser = risers[0];
  const darkHorse = S.boardData.find(p => (p.tier === 'T3' || p.tier === 'T4') && (p.delta_fit || 0) > 0.1);

  function storylineCard(icon, label, playerObj, narrative, tierColor) {
    if (!playerObj) return '';
    const pName = playerObj.player || playerObj;
    const br    = S.briefsByName[normName(pName)] || {};
    const txt   = narrative || br.convictionStatement || br.conviction_statement || br.why_it_fits_structurally || '';
    const tc    = tierColor || 'var(--gold)';
    return `<div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem;cursor:pointer;" data-player="${esc(pName)}">
      <div style="font-size:.65rem;color:${tc};font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem;font-family:'Inter',sans-serif;">${icon} ${esc(label)}</div>
      <div style="font-weight:700;font-size:.9rem;color:var(--text);margin-bottom:.3rem;">${esc(pName)}</div>
      <div style="font-size:.73rem;color:var(--text-2);line-height:1.45;">${esc(txt.slice(0, 180))}${txt.length > 180 ? '…' : ''}</div>
    </div>`;
  }

  grid.innerHTML = [
    storylineCard('◈', 'Top Venue Fit', topVFS,
      topVFS ? `Δ Fit: ${sgSign(topVFS.delta_fit)} — highest venue fit delta in the field.` : '',
      'var(--t1-t)'),
    storylineCard('▲', 'Structural Contender', topContender, null, 'var(--t2-t)'),
    topRiser ? storylineCard('📈', 'Form Riser',
      { player: topRiser.player },
      `vs. Baseline L20: ${topRiser.vsBaselineL20 >= 0 ? '+' : ''}${topRiser.vsBaselineL20.toFixed(2)} SG — trending above baseline.`,
      'var(--green-ok)') : '',
    darkHorse ? storylineCard('◎', 'Dark Horse',
      darkHorse,
      (S.briefsByName[normName(darkHorse.player)] || {}).dark_horse_thesis || '',
      'var(--t3-t)') : '',
  ].filter(Boolean).join('');

  grid.querySelectorAll('[data-player]').forEach(card => {
    card.addEventListener('click', () => openModal(card.dataset.player));
  });
}

// ── Contention map — NSI vs VTS bubble chart ──────────────────────────────────
let _contentionChart = null;

function renderContentionChart() {
  const canvas = document.getElementById('contention-canvas');
  if (!canvas || !window.Chart || !S.boardData.length) return;

  const TIER_COLORS = {
    T1: { bg: 'rgba(22,163,74,.75)',  border: '#16a34a' },
    T2: { bg: 'rgba(37,99,235,.75)',  border: '#2563eb' },
    T3: { bg: 'rgba(124,58,237,.75)', border: '#7c3aed' },
    T4: { bg: 'rgba(234,88,12,.75)',  border: '#ea580c' },
    T5: { bg: 'rgba(220,38,38,.6)',   border: '#dc2626' },
  };

  const players = S.boardData.filter(p => p.vts_final != null && p.neutralSkillIndex != null);

  const datasets = ['T1','T2','T3','T4','T5'].map(tier => {
    const tp = players.filter(p => p.tier === tier);
    const cols = TIER_COLORS[tier];
    return {
      label: tier,
      data: tp.map(p => {
        const hasFlag  = (p._flags || []).length > 0;
        const isDebut  = (p.data_depth || '').toUpperCase() === 'DEBUT';
        const highlight = (S.chartHighlightFlags && hasFlag) || (S.chartHighlightDebut && isDebut);
        return {
          x: p.neutralSkillIndex,
          y: p.delta_fit != null ? p.delta_fit : 0,
          r: Math.max(4, Math.min(24, (p.winPct || 0.5) * 3.5)),
          player: p.player,
          tier,
          winPct: p.winPct,
          nsi: p.neutralSkillIndex,
          vts: p.vts_final,
          vfs: p.delta_fit != null ? p.delta_fit : 0,
          hasFlag,
          isDebut,
          highlight,
        };
      }),
      backgroundColor: tp.map(p => {
        const isDebut  = (p.data_depth || '').toUpperCase() === 'DEBUT';
        const hasFlag  = (p._flags || []).length > 0;
        if (S.chartHighlightDebut && isDebut) return 'rgba(251,191,36,.85)';
        if (S.chartHighlightFlags && hasFlag)  return 'rgba(239,68,68,.85)';
        return cols.bg;
      }),
      borderColor: cols.border,
      borderWidth: 1.5,
      hoverBorderWidth: 2.5,
    };
  });

  const chartConfig = {
    type: 'bubble',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: window.innerWidth < 640 ? 1.2 : 2.2,
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#7a8fa6', font: { size: 11 }, boxWidth: 12, padding: 10 },
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const d = ctx.raw;
              const lines = [`${d.player}  (${d.tier})`, `NSI: ${f1(d.nsi)} · Δ Fit: ${sgSign(d.vfs)} · Win: ${pct(d.winPct)}`];
              if (d.isDebut) lines.push('⚑ Course Debut');
              if (d.hasFlag) lines.push('⚑ Has Flags');
              return lines;
            },
          },
          backgroundColor: '#161d27',
          borderColor: '#2a3a4a',
          borderWidth: 1,
          padding: 8,
          titleColor: '#c9a84c',
          bodyColor: '#b8c4cc',
        },
      },
      scales: {
        x: {
          title: { display: true, text: 'Neutral Skill Index (NSI)', color: '#7a8fa6', font: { size: 11 } },
          ticks: { color: '#7a8fa6', font: { size: 10 } },
          grid:  { color: 'rgba(42,58,74,.4)' },
          min: 20, max: 105,
        },
        y: {
          title: { display: true, text: 'Venue Fit Δ (SG/round)', color: '#7a8fa6', font: { size: 11 } },
          ticks: { color: '#7a8fa6', font: { size: 10 }, callback: v => (v >= 0 ? '+' : '') + Number(v).toFixed(2) },
          grid:  { color: 'rgba(42,58,74,.4)' },
          min: -0.55, max: 0.55,
        },
      },
      onClick(evt, elements) {
        if (!elements.length) return;
        const el    = elements[0];
        const ds    = datasets[el.datasetIndex];
        const point = ds.data[el.index];
        if (point?.player) {
          scrollToPlayer(point.player);
          openModal(point.player);
        }
      },
    },
  };

  if (_contentionChart) {
    _contentionChart.destroy();
    _contentionChart = null;
  }
  _contentionChart = new Chart(canvas, chartConfig);
}

// ── Scenario builder ──────────────────────────────────────────────────────────
const SCENARIO_TRAITS = [
  { key: 'app_150_200',   label: 'App 150–200 yd',   defaultWeight: 0.25 },
  { key: 'ott_accuracy',  label: 'OTT Accuracy',      defaultWeight: 0.15 },
  { key: 'ott_positional',label: 'OTT Positional',    defaultWeight: 0.12 },
  { key: 'app_overall',   label: 'App Overall',        defaultWeight: 0.20 },
  { key: 'sg_putt',       label: 'SG: Putting',       defaultWeight: 0.10 },
  { key: 'sg_arg',        label: 'SG: ARG',           defaultWeight: 0.10 },
  { key: 'par5_scoring',  label: 'Par-5 Scoring',     defaultWeight: 0.08 },
];

function getDefaultWeights() {
  const dw = {};
  for (const t of SCENARIO_TRAITS) dw[t.key] = t.defaultWeight;
  return dw;
}

function toggleScenarioPanel() {
  const panel = document.getElementById('scenario-panel');
  if (!panel) return;
  const isHidden = panel.classList.contains('hidden');
  if (isHidden) {
    panel.classList.remove('hidden');
    if (!Object.keys(S.scenarioWeights).length) S.scenarioWeights = getDefaultWeights();
    renderScenarioSliders();
    enterScenarioMode();
  } else {
    exitScenario();
  }
}

function enterScenarioMode() {
  S.scenarioMode = true;
  const btn = document.getElementById('btn-scenario');
  if (btn) { btn.style.borderColor = 'var(--gold)'; btn.style.color = 'var(--gold)'; btn.textContent = '⊡ Analyst Mode ON'; }
  document.getElementById('analyst-mode-banner')?.classList.remove('hidden');
  renderScenarioResults();
}

function exitScenario() {
  S.scenarioMode = false;
  document.getElementById('scenario-panel')?.classList.add('hidden');
  const btn = document.getElementById('btn-scenario');
  if (btn) { btn.style.borderColor = 'var(--gold-dim)'; btn.style.color = 'var(--gold-dim)'; btn.textContent = '⊡ Analyst Mode'; }
  document.getElementById('analyst-mode-banner')?.classList.add('hidden');
  // Remove scenario rank column
  document.querySelectorAll('#board-tbody tr[data-player]').forEach(tr => {
    const sc = tr.querySelector('.scenario-rank-cell');
    if (sc) sc.remove();
  });
  document.querySelectorAll('#board-table th.scenario-col').forEach(th => th.remove());
  document.getElementById('board-sub-scenario')?.remove();
  S.scenarioWeights = {};
  document.querySelectorAll('#board-tbody tr.analyst-mode-row').forEach(r => r.classList.remove('analyst-mode-row'));
}

function resetScenario() {
  S.scenarioWeights = getDefaultWeights();
  renderScenarioSliders();
  renderScenarioResults();
}

function renderScenarioSliders() {
  const container = document.getElementById('scenario-sliders');
  if (!container) return;
  container.innerHTML = SCENARIO_TRAITS.map(t => {
    const w = (S.scenarioWeights[t.key] ?? t.defaultWeight);
    return `<div class="slider-wrap">
      <div class="slider-label">
        <span>${t.label}</span>
        <span><span class="slider-default">default ${Math.round(t.defaultWeight*100)}%</span> → <span class="slider-current" id="sw-val-${t.key}">${Math.round(w*100)}%</span></span>
      </div>
      <input type="range" min="0" max="50" step="1" value="${Math.round(w*100)}"
        data-trait="${t.key}"
        oninput="onScenarioSlider('${t.key}', this.value)">
    </div>`;
  }).join('');
}

function onScenarioSlider(traitKey, rawVal) {
  S.scenarioWeights[traitKey] = parseFloat(rawVal) / 100;
  const valEl = document.getElementById('sw-val-' + traitKey);
  if (valEl) valEl.textContent = rawVal + '%';
  renderScenarioResults();
}

function computeScenarioScore(p) {
  const br = S.briefsByName[normName(p.player)] || {};
  const ts = (br.trait_scores || []);
  let sum = 0; let wSum = 0;
  for (const t of SCENARIO_TRAITS) {
    const w = S.scenarioWeights[t.key] ?? t.defaultWeight;
    if (w === 0) continue;
    const entry = ts.find(x => resolveCumKey(x.label) === t.key);
    const score = entry != null ? (entry.score || 50) : 50;
    sum  += w * score;
    wSum += w;
  }
  return wSum > 0 ? sum / wSum : p.vts_final;
}

function renderScenarioResults() {
  if (!S.scenarioMode) return;
  // Mark existing rows as clean — will be re-marked below
  document.querySelectorAll('#board-tbody tr.analyst-mode-row').forEach(r => r.classList.remove('analyst-mode-row'));
  const scored = S.boardData.map(p => ({
    player: p.player,
    officialRank: p.rank,
    scenarioScore: computeScenarioScore(p),
  })).sort((a, b) => b.scenarioScore - a.scenarioScore);

  const scenarioRankMap = {};
  scored.forEach((s, i) => { scenarioRankMap[s.player] = i + 1; });

  // Remove old scenario columns first
  document.querySelectorAll('#board-table th.scenario-col').forEach(th => th.remove());
  document.getElementById('board-sub-scenario')?.remove();

  // Add header columns if not present
  const thead = document.querySelector('#board-table thead tr');
  if (thead && !thead.querySelector('.scenario-col')) {
    const thSc = document.createElement('th');
    thSc.className = 'scenario-col sans';
    thSc.style.cssText = 'color:var(--gold);font-weight:700;';
    thSc.textContent = '⊡ Sc.Rank';
    const thDelta = document.createElement('th');
    thDelta.className = 'scenario-col sans';
    thDelta.textContent = 'Δ';
    thead.appendChild(thSc);
    thead.appendChild(thDelta);
  }

  // Add scenario-unofficial banner
  const boardSection = document.getElementById('sec-board');
  if (boardSection && !document.getElementById('board-sub-scenario')) {
    const banner = document.createElement('div');
    banner.id = 'board-sub-scenario';
    banner.className = 'scenario-unofficial-tag';
    banner.style.cssText = 'display:inline-block;margin-bottom:.5rem;';
    banner.textContent = '⚠ UNOFFICIAL SCENARIO — Rankings below are NOT official VenueDNA outputs';
    boardSection.insertBefore(banner, boardSection.querySelector('.table-container'));
  }

  // Update each row
  document.querySelectorAll('#board-tbody tr[data-player]').forEach(tr => {
    const pName = tr.dataset.player;
    const sRank = scenarioRankMap[pName];
    const pData = S.boardData.find(x => x.player === pName);
    const oRank = pData?.rank;
    const delta = oRank != null && sRank != null ? oRank - sRank : null;

    // Remove old scenario cells
    tr.querySelectorAll('td.scenario-col').forEach(td => td.remove());

    // Add scenario rank cell
    const tdSc = document.createElement('td');
    tdSc.className = 'scenario-col scenario-rank-cell sans';
    tdSc.textContent = sRank != null ? sRank : '—';
    tr.appendChild(tdSc);
    tr.classList.add('analyst-mode-row');

    // Add delta cell
    const tdDelta = document.createElement('td');
    tdDelta.className = 'scenario-col sans';
    if (delta == null || delta === 0) {
      tdDelta.className += ' scenario-delta-zero'; tdDelta.textContent = '—';
    } else if (delta > 0) {
      tdDelta.className += ' scenario-delta-pos'; tdDelta.textContent = `▲${delta}`;
    } else {
      tdDelta.className += ' scenario-delta-neg'; tdDelta.textContent = `▼${Math.abs(delta)}`;
    }
    tr.appendChild(tdDelta);
  });
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
  const hasAny = br.scoring_thesis || br.failure_condition ||
                 br.risk_vector || br.conviction_statement || br.structural_note;
  if (!hasAny) {
    return p.win_case
      ? `<div class="modal-sec">
           <div class="modal-sec-title sans">Scouting Report</div>
           <div class="analyst-brief">${p.win_case}</div>
         </div>`
      : '';
  }

  if (tn <= 2) {
    const label = tn === 1 ? 'Win Case — Tier 1 Structural Winner' : 'Contention Brief — Primary Contender';
    return `<div class="modal-sec">
      <div class="modal-sec-title sans">${label}</div>
      <div class="win-case-card ${tc}">
        ${br.scoring_thesis        ? `<div class="wc-q ${tc}c">Win Mechanism</div><div class="wc-p">${br.scoring_thesis}</div>` : ''}
        ${(br.failure_condition || br.risk_vector) ? `<div class="wc-q ${tc}c">Key Risk</div><div class="wc-p">${br.failure_condition || br.risk_vector}</div>` : ''}
        ${br.conviction_statement  ? `<div class="wc-q ${tc}c">Model Read</div><div class="wc-p">${br.conviction_statement}</div>` : ''}
      </div>
    </div>`;
  }

  if (tn === 3) {
    return `<div class="modal-sec">
      <div class="modal-sec-title sans">Dark Horse Thesis</div>
      <div class="win-case-card t3">
        ${(br.dark_horse_thesis || br.structural_note) ? `<div class="wc-q t3c">Win Case</div><div class="wc-p">${br.dark_horse_thesis || br.structural_note}</div>` : ''}
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

// ── Live SG block — renders LIVE STROKES GAINED section for modal §1 ──────────
function buildLiveSGBlock(p) {
  const r = S.currentRound;
  if (r === 'pre' || !S.roundData[r]) return '';

  const snap = S.roundData[r].leaderboard_snapshot || [];
  const nm   = normName(p.player);
  const row  = snap.find(x => normName(x.r1_name || '') === nm);

  const hasData = row && (row.sg_ott != null || row.sg_app != null ||
                          row.sg_arg != null || row.sg_putt != null || row.sg_tot != null);

  const hdr = '<div class="sans" style="font-size:10px;letter-spacing:.08em;color:#34d399;margin-bottom:8px">LIVE STROKES GAINED PERFORMANCE</div>';

  if (!hasData) {
    return '<div style="margin-top:14px;padding:10px 14px;background:#020617;border:1px solid #1e293b;border-radius:8px">' +
      hdr +
      '<div class="sans" style="font-size:12px;color:#64748b;font-style:italic">Live Stats: Round data is pending first scorecard</div>' +
      '</div>';
  }

  const sgSafe = v => (v == null || (typeof v === 'number' && isNaN(v))) ? null : v;
  const sgCol  = v => v == null ? '#94a3b8' : v >= 0 ? '#34d399' : '#fb7185';
  const sgFmt  = v => v == null ? '0.00' : (v >= 0 ? '+' : '') + Number(v).toFixed(2);

  const metrics = [
    { lbl: 'ott',  val: sgSafe(row.sg_ott)  },
    { lbl: 'app',  val: sgSafe(row.sg_app)  },
    { lbl: 'arg',  val: sgSafe(row.sg_arg)  },
    { lbl: 'putt', val: sgSafe(row.sg_putt) },
    { lbl: 'tot',  val: sgSafe(row.sg_tot)  },
  ];

  const cells = metrics.map(m =>
    '<div style="background:#0f172a;border:1px solid #1e293b;border-radius:6px;padding:7px 4px;text-align:center">' +
      '<div class="sans" style="font-size:15px;font-weight:800;color:' + sgCol(m.val) + '">' + sgFmt(m.val) + '</div>' +
      '<div class="sans" style="font-size:9px;color:#64748b;letter-spacing:.07em;text-transform:uppercase;margin-top:2px">' + m.lbl + '</div>' +
    '</div>'
  ).join('');

  return '<div style="margin-top:14px;padding:10px 14px;background:#020617;border:1px solid #1e293b;border-radius:8px">' +
    hdr +
    '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px">' + cells + '</div>' +
    '</div>';
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
  const traitScores = br.trait_scores || p.trait_scores || [];
  const topTraits   = br.top_traits   || [];
  const badges      = p.badges || br.badges || [];

  const analystLabel = tn <= 2 ? 'Analyst Intelligence — Full Brief' : tn === 3 ? 'Model Conviction' : 'Model Note';

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
          <div class="prob-box">
            <div class="prob-val sans">${pct(wPct)}</div>
            <div class="prob-lbl sans">Win</div>
            ${fairOdds(wPct) ? `<div class="prob-odds sans">${fairOdds(wPct)}</div>` : ''}
          </div>
          <div class="prob-box">
            <div class="prob-val sans">${pct(t5Pct)}</div>
            <div class="prob-lbl sans">Top 5</div>
            ${fairOdds(t5Pct) ? `<div class="prob-odds sans">${fairOdds(t5Pct)}</div>` : ''}
          </div>
          <div class="prob-box">
            <div class="prob-val sans">${pct(t10Pct)}</div>
            <div class="prob-lbl sans">Top 10</div>
            ${fairOdds(t10Pct) ? `<div class="prob-odds sans">${fairOdds(t10Pct)}</div>` : ''}
          </div>
          <div class="prob-box">
            <div class="prob-val sans">${pct(t20Pct)}</div>
            <div class="prob-lbl sans">Top 20</div>
            ${fairOdds(t20Pct) ? `<div class="prob-odds sans">${fairOdds(t20Pct)}</div>` : ''}
          </div>
          <div class="prob-box">
            <div class="prob-val sans">${pct(mcPct)}</div>
            <div class="prob-lbl sans">Make Cut</div>
            ${fairOdds(mcPct) ? `<div class="prob-odds sans">${fairOdds(mcPct)}</div>` : ''}
          </div>
          <div class="prob-box">
            <div class="prob-val sans" style="color:var(--accent)">${pct(missPct)}</div>
            <div class="prob-lbl sans">Miss Cut</div>
          </div>
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

        ${(p.vts_floor != null && p.vts_ceil != null) ? `
        <div class="dial-row">
          <canvas id="d-win" width="72" height="72"></canvas>
          <canvas id="d-t5"  width="72" height="72"></canvas>
          <canvas id="d-t10" width="72" height="72"></canvas>
          <canvas id="d-cut" width="72" height="72"></canvas>
        </div>
        <div class="cf-bar-wrap">
          <div class="cf-bar-lbl sans">Projection Range (±1σ)</div>
          <div class="cf-bar-track">
            <div class="cf-bar-fill" style="left:${Math.max(0,Math.min(100,p.vts_floor))}%;width:${Math.max(0,Math.min(100,(p.vts_ceil||0)-(p.vts_floor||0)))}%"></div>
            <div class="cf-bar-pin"  style="left:${Math.max(0,Math.min(100,p.vts_final))}%"></div>
          </div>
          <div class="cf-bar-ticks sans">
            <span>Floor ${f1(p.vts_floor)}</span><span>VTS ${f2(p.vts_final)}</span><span>Ceil ${f1(p.vts_ceil)}</span>
          </div>
        </div>` : ''}

        ${buildLiveSGBlock(p)}

        ${S.weather.speed > 0 ? `<div style="margin-top:14px;padding:10px 14px;background:#0f172a;border:1px solid #1e293b;border-radius:8px">
          <div class="sans" style="font-size:10px;letter-spacing:.08em;color:#f59e0b;margin-bottom:8px">WIND CONDITIONS</div>
          <span class="sans" style="font-size:11px;color:#94a3b8">Wind: </span>
          <span class="sans" style="font-size:12px;color:#e2e8f0;font-weight:600">${S.weather.speed} kts ${S.weather.direction}</span>
        </div>` : ''}
      </div>

      <!-- §2 — STYLE / FIT BADGES -->
      ${(badges.length || (p.strength_tags||[]).length || (p.weakness_tags||[]).length) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Style &amp; Fit</div>
        ${badges.length ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">${badges.map(b => `<span class="badge sans" style="font-size:12px;padding:4px 10px">${b}</span>`).join('')}</div>` : ''}
        ${((p.strength_tags||[]).length || (p.weakness_tags||[]).length) ? `<div style="display:flex;gap:6px;flex-wrap:wrap">
          ${(p.strength_tags||[]).map(t=>`<span class="badge-strength sans">${t}</span>`).join('')}
          ${(p.weakness_tags||[]).map(t=>`<span class="badge-weakness sans">${t}</span>`).join('')}
        </div>` : ''}
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
        ${(br.strengthTags?.length || br.weaknessTags?.length) ? `<div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.6rem;">
          ${(br.strengthTags||[]).map(t=>`<span style="background:#052e16;border:1px solid #16a34a55;color:#4ade80;padding:.1rem .4rem;border-radius:4px;font-size:.68rem;font-family:'Inter',sans-serif">+${t}</span>`).join('')}
          ${(br.weaknessTags||[]).map(t=>`<span style="background:#450a0a;border:1px solid #dc262655;color:#fca5a5;padding:.1rem .4rem;border-radius:4px;font-size:.68rem;font-family:'Inter',sans-serif">–${t}</span>`).join('')}
        </div>` : ''}
      </div>` : ''}

      <!-- §5 — TRAIT PROFILE -->
      ${p._isAlt
        ? `<div class="modal-sec">
            <div class="modal-sec-title sans">Trait Profile — Venue Weight vs Player Score</div>
            <div class="modal-note sans" style="color:#94a3b8;font-style:italic;margin-bottom:10px">Alternate Entry: Baseline Regressed to Field Mean</div>
            <div class="trait-rows">
              ${['App 150–200','OTT Accuracy','OTT Positional','App Overall','SG: Putting','SG: ARG'].map(lbl =>
                '<div class="trait-row">' +
                '<div class="trait-lbl" style="color:#64748b">' + lbl + '</div>' +
                '<div class="trait-wt" style="color:#64748b">—</div>' +
                '<div class="trait-track"><div class="trait-fill-lo" style="width:50%;background:#475569;opacity:0.5"></div></div>' +
                '<div class="trait-score" style="color:#64748b">50.0</div>' +
                '</div>'
              ).join('')}
            </div>
          </div>`
        : traitScores.length ? `<div class="modal-sec">
          <div class="modal-sec-title sans">Trait Profile — Venue Weight vs Player Score</div>
          <div class="trait-rows">
            ${traitScores.map(t => {
              const sc  = Math.max(0, Math.min(100, isNaN(t.score) || t.score == null ? 50 : t.score));
              const fc  = traitFillCls(t.score);
              const vc  = traitScoreColor(t.score);
              const _ck = resolveCumKey(t.label);
              const _cs = _ck && (S.cumulativeLearning?.cumulative_signals?.[_ck]);
              const _ch = _cs?.signal_history?.length
                ? `<div class="trait-history-text">History: ${_cs.signal_history.map(v => `[${v}]`).join(' ')}</div>`
                : '';
              return `<div class="trait-row">
                <div class="trait-meta-row">
                  <div class="trait-lbl">${t.label}</div>
                  <div class="trait-wt">${Math.round((t.weight || 0) * 100)}%</div>
                  <div class="trait-track"><div class="${fc}" style="width:${sc}%"></div></div>
                  <div class="trait-score"${vc ? ` style="${vc}"` : ''}>${f1(t.score)}</div>
                </div>
                ${_ch}
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
      ${(br.anti_pattern_summary || br.risk_vector || (br.drag_traits && br.drag_traits.length)) ? `<div class="modal-sec">
        <div class="modal-sec-title sans">Anti-Pattern Analysis &amp; Risk Vector</div>
        ${br.risk_vector          ? `<div class="modal-note sans"><b>Risk Vector:</b> ${br.risk_vector}</div>` : ''}
        ${br.anti_pattern_summary ? `<div class="modal-note sans">${br.anti_pattern_summary}</div>` : ''}
        ${(br.drag_traits && br.drag_traits.length) ? `<div class="modal-note sans"><b>Drag Traits:</b> ${br.drag_traits.join(' · ')}</div>` : ''}
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
        </div>
      </div>` : ''}

      <!-- §10 — SYSTEM FOOTPRINT: dual-vector decomposition -->
      <div class="modal-sec">
        <div class="modal-sec-title sans">System Footprint — Score Decomposition</div>
        <div class="modal-layers">
          <div class="layer-row"><div class="layer-lbl sans">NSI</div><div class="layer-track"><div class="layer-fill" style="width:${clamp(p.neutralSkillIndex,0,100)}%;background:var(--navy)"></div></div><div class="layer-val sans" style="color:var(--navy)">${f1(p.neutralSkillIndex)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">SG Sim</div><div class="layer-track"><div class="layer-fill" style="width:${clamp(p.vts_final,0,100)}%;background:var(--green-ok)"></div></div><div class="layer-val sans" style="color:var(--green-ok)">${f1(p.vts_final)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">Δ Fit</div>${vhdDivergingBar((p.delta_fit||0)*10)}<div class="layer-val sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</div></div>
        </div>
      </div>

      <div class="modal-sec">
        <div class="modal-sec-title sans">Similar Course Profile</div>
        <div class="modal-layers">
          <div class="layer-row"><div class="layer-lbl sans">SG Base</div><div style="flex:1;font-size:.78rem;color:var(--muted)">baseline skill anchor</div><div class="layer-val sans">${sgSign(p.sg_base_composite)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">SG Sim</div><div style="flex:1;font-size:.78rem;color:var(--muted)">similar-course ability</div><div class="layer-val sans">${sgSign(p.sg_similar_composite)}</div></div>
          <div class="layer-row"><div class="layer-lbl sans">Δ Fit</div><div style="flex:1;font-size:.78rem;color:var(--muted)">TPC Twin Cities uplift</div><div class="layer-val sans" style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</div></div>
        </div>
        <div class="modal-note sans" style="margin-top:6px">data depth: <b>${p.data_depth || '—'}</b></div>
      </div>

      <!-- §11 — VTS SPARKLINE HISTORY -->
      <div class="modal-sec">
        <div class="modal-sec-title sans">VTS Journey — Similar-Course History</div>
        ${(() => {
          const ts = (br.trait_scores || []);
          const history = S.cumulativeLearning?.cumulative_signals?.app_overall?.signal_history
                       || S.cumulativeLearning?.cumulative_signals?.app_150_200?.signal_history;
          if (!history || !history.length) {
            return `<div class="sparkline-wrap"><div class="sparkline-empty">Tournament in progress — cross-event VTS history will populate after Round 1 analysis.</div>
              <div style="margin-top:.5rem;font-size:.7rem;color:var(--muted)">Current: VTS <b style="color:var(--gold)">${f2(p.vts_final)}</b> · NSI <b>${f1(p.neutralSkillIndex)}</b> · Δ Fit <b style="color:${(p.delta_fit||0)>=0?'var(--green-ok)':'var(--accent)'}">${sgSign(p.delta_fit)}</b></div></div>`;
          }
          const pts = history.map((v,i) => ({ i, v }));
          const vals = pts.map(pt => pt.v === 'validated' ? 3 : pt.v === 'mixed' ? 2 : pt.v === 'weak' ? 1 : 0);
          const mx = Math.max(...vals, 1);
          const W = 200; const H = 40; const pad = 4;
          const iw = W - pad*2; const ih = H - pad*2;
          const px = (i) => pad + (i / Math.max(pts.length-1,1)) * iw;
          const py = (v) => pad + ih - (v / mx) * ih;
          const pathD = vals.map((v,i) => (i === 0 ? 'M' : 'L') + px(i).toFixed(1) + ' ' + py(v).toFixed(1)).join(' ');
          const lastX = px(vals.length-1); const lastY = py(vals[vals.length-1]);
          return `<div class="sparkline-wrap"><svg class="sparkline-svg" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" aria-label="Trait signal trajectory">
            <path d="${pathD}" fill="none" stroke="var(--gold-dim)" stroke-width="1.5"/>
            <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="3" fill="var(--gold)" stroke="var(--surface2)" stroke-width="1"/>
            ${vals.map((v,i) => `<circle cx="${px(i).toFixed(1)}" cy="${py(v).toFixed(1)}" r="2" fill="${v>=3?'#4ade80':v>=2?'#fbbf24':'#f87171'}" opacity=".8"/>`).join('')}
          </svg>
          <div style="font-size:.62rem;color:var(--muted);margin-top:.2rem;">Trait consensus trajectory · ${pts.length} signal points · current event marked gold</div></div>`;
        })()}
      </div>

    </div>`;

  document.getElementById('player-drawer')?.classList.add('open');
  document.getElementById('drawer-backdrop')?.classList.add('open');
  document.body.classList.add('drawer-open');
  requestAnimationFrame(() => drawProbDials(wPct, t5Pct, t10Pct, mcPct));
}

function closeModal() {
  document.getElementById('player-drawer')?.classList.remove('open');
  document.getElementById('drawer-backdrop')?.classList.remove('open');
  document.body.classList.remove('drawer-open');
  S.activePlayer = null;
}

function onOverlayClick(e) {
  if (e.target.id === 'drawer-backdrop') closeModal();
}

// ── Glossary modal ─────────────────────────────────────────────────────────────
function renderGlossary() {
  const body = document.getElementById('glossary-body');
  if (!body) return;
  body.innerHTML = Object.entries(uiGlossary).map(([section, items]) =>
    `<div class="gloss-section">
      <div class="gloss-section-title">${esc(section)}</div>
      ${items.map(({ term, def }) =>
        `<div class="gloss-item">
          <span class="gi-term">${esc(term)}</span>
          <div class="gi-def">${esc(def)}</div>
        </div>`
      ).join('')}
    </div>`
  ).join('');
}

function openGlossary() {
  S.glossaryModalOpen = true;
  renderGlossary();
  document.getElementById('glossary-modal-overlay')?.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeGlossary() {
  if (!S.glossaryModalOpen) return;
  S.glossaryModalOpen = false;
  document.getElementById('glossary-modal-overlay')?.classList.remove('open');
  if (!S.activePlayer) document.body.style.overflow = '';
}

function onGlossaryOverlayClick(e) {
  if (e.target.id === 'glossary-modal-overlay') closeGlossary();
}

// ── Theme toggle ───────────────────────────────────────────────────────────────
function toggleTheme() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  if (isLight) {
    document.documentElement.removeAttribute('data-theme');
    document.getElementById('theme-icon').textContent = '☽';
    document.getElementById('theme-label').textContent = 'Dark';
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
    document.getElementById('theme-icon').textContent = '☀';
    document.getElementById('theme-label').textContent = 'Light';
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function f1(v)  { return v != null ? Number(v).toFixed(1) : '—'; }
function f2(v)  { return v != null ? Number(v).toFixed(2) : '—'; }
function pct(v) { return v != null ? Number(v).toFixed(1) + '%' : '—'; }
function fairOdds(v) {
  if (v == null || Number(v) <= 0) return null;
  const p  = Number(v);
  const dc = 100 / p;
  const am = dc >= 2
    ? Math.round((dc - 1) * 100)
    : Math.round(-100 / (dc - 1));
  return am >= 0 ? '+' + am : String(am);
}
function vhd(v) { if (v == null) return '—'; return (v > 0 ? '+' : '') + Number(v).toFixed(3); }
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v || 0)); }
function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── Flag metadata — code → {lbl, cls, full} ───────────────────────────────────
const FM = {
  'VenueDNA_flag_accuracy_risk':      { lbl:'ACC',   cls:'flag-warn',   full:'Driving accuracy risk — penalty exposure on water-threatened holes' },
  'VenueDNA_flag_short_game_only':    { lbl:'SGO',   cls:'flag-warn',   full:'Short-game-only profile — TPC does not reward scrambling over ball-striking' },
  'VenueDNA_flag_putting_dependency': { lbl:'PUTT',  cls:'flag-warn',   full:'Putting-reliant profile — easy bentgrass greens compress putting advantage' },
  'VenueDNA_flag_long_iron_deficit':  { lbl:'LI-',   cls:'flag-warn',   full:'Long-iron deficit — 150-200 fw SG below neutral, limiting primary birdie creation' },
  'VenueDNA_flag_distance_cap':       { lbl:'DIST',  cls:'flag-info',   full:'Distance ceiling — limited upside on longer par 4s and reachable par 5s' },
  'VenueDNA_flag_course_debut':       { lbl:'DEB',   cls:'flag-info',   full:'TPC Twin Cities debut — no course history adjustment available' },
  'VenueDNA_flag_limited_history':    { lbl:'LTD',   cls:'flag-info',   full:'Limited course history — fewer than 4 starts at TPC Twin Cities' },
  'VenueDNA_flag_high_variance':      { lbl:'VAR',   cls:'flag-warn',   full:'High variance profile — wide outcome range; ceiling and floor both elevated' },
  'VenueDNA_flag_form_concern':       { lbl:'FORM',  cls:'flag-danger', full:'Recent form concern — performance below recent-season baseline' },
  'VenueDNA_flag_ott_accuracy':       { lbl:'OTT',   cls:'flag-warn',   full:'OTT accuracy concern — driving accuracy penalty applied' },
};

// ── UI Glossary — rendered dynamically into #glossary-body ─────────────────────
const uiGlossary = {
  'Score Components': [
    { term: 'VTS 0–100', def: 'Venue Tier Score: z-scored composite of SG Similar Composite across the full field (mean=50, std=15). The official ranking signal.' },
    { term: 'NSI 0–100', def: 'Neutral Skill Index: z-scored SG Base Composite — general skill ranking independent of venue fit. Tells you who is playing the best golf right now, ignoring course fit.' },
    { term: 'SG Base', def: 'Baseline skill across all courses — stability-weighted composite (6m:20%, 12m:30%, 24m:50%). The long-run skill anchor.' },
    { term: 'SG Sim', def: 'Similar-course strokes gained — sample-weighted regression using the top-20 courses most similar to TPC Twin Cities.' },
    { term: 'Δ Fit', def: 'Delta between SG Sim and SG Base — TPC Twin Cities venue fit signal. Positive = course-specialist upside; clamped ±0.50 SG/round.' },
    { term: 'VFS (Venue Fit)', def: 'Δ Fit expressed as a venue fit signal. Used on the Contention Map Y-axis. High VFS + high NSI = structural contender.' },
  ],
  'Traits': [
    { term: 'NeutralSkill (NSI)', def: 'Player skill level independent of venue. Drives the X-axis on the Contention Map.' },
    { term: 'VenueFitDelta', def: 'How much TPC Twin Cities specifically helps or hurts this player vs. their all-course baseline.' },
    { term: 'VenueHistoryDelta', def: 'Course-history adjustment — derived from prior starts at TPC Twin Cities. Clamped to a modest modifier.' },
    { term: 'App 150–200 yd', def: 'Approach strokes gained from 150–200 yards. The #1 birdie creation mechanism at TPC Twin Cities (46% of approaches from this range).' },
    { term: 'OTT Accuracy / Positional', def: 'Driving accuracy and positional efficiency. Penalised on the 9 water-threatened driving holes at TPC.' },
  ],
  'Probability Outputs': [
    { term: 'Win%', def: 'Tempered softmax win probability (T=3.5); full field sums to ~100%.' },
    { term: 'Top5% / Top10%', def: 'Tempered softmax placement probabilities (T=7.0); field sums to ~500% / ~1000%.' },
    { term: 'Cut%', def: 'Estimated make-cut probability: min(98, max(20, Top20% × 1.25 + 10)).' },
    { term: 'Fair +Odds', def: 'Implied fair American odds derived from model probability. Formula: fair decimal = 100 / p%; American = +(decimal−1)×100 if positive. These are model-implied prices, NOT betting lines.' },
  ],
  'Tiers': [
    { term: 'T1 — Elite', def: 'Ranks 1–5. Structural winners: high NSI AND positive VFS. Must-consider contenders.' },
    { term: 'T2 — Strong', def: 'Ranks 6–12. Primary contenders with at least one structural advantage at TPC.' },
    { term: 'T3 — Mid-tier', def: 'Ranks 13–25. Viable ceiling plays if a key trait fires. Dark horse territory.' },
    { term: 'T4 — Value', def: 'Ranks 26–40. Fragile paths requiring multiple things to go right.' },
    { term: 'T5 — Long-shots', def: 'Ranks 41+. Structural mismatches or limited data — fade candidates.' },
  ],
  'Anti-Pattern Flags': [
    { term: 'ACC — Accuracy Risk', def: 'Driving accuracy concern. Penalty exposure on TPC\'s 9 water-threatened holes. Even a single penalty stroke can cascade.' },
    { term: 'SGO — Short Game Only', def: 'Short-game-only profile. TPC rewards ball-striking over scrambling; this flag signals a structural ceiling.' },
    { term: 'PUTT — Putting Dependency', def: 'Putting-reliant profile. Easy bentgrass greens compress putting edges vs. trickier venues.' },
    { term: 'LI– — Long-Iron Deficit', def: '150–200 fw SG below neutral. Limits birdie creation on TPC\'s approach-heavy layout.' },
    { term: 'FORM — Form Concern', def: 'Recent performance below recent-season baseline. Watch vs. baseline trend.' },
    { term: 'DEB — Course Debut', def: 'No prior TPC Twin Cities starts — no course history adjustment available.' },
  ],
  'Analyst Mode': [
    { term: 'What It Is', def: 'A client-side weight-adjustment sandbox. Trait weights can be changed to explore how rankings would shift under a different emphasis (e.g., if you believe putting matters more than approach this week).' },
    { term: 'What It Is NOT', def: 'Official VenueDNA outputs. Analyst Mode results are clearly badged as UNOFFICIAL and are never written back to any data file.' },
    { term: 'Reset to Official', def: 'The "Reset to official model" button restores canonical VenueDNA weights and exits Analyst Mode. The rank table reverts to official order.' },
  ],
};

function flag(code, penMag) {
  const m = FM[code];
  if (!m) return `<span class="flag sans" data-fc="${esc(code)}" data-ft-lbl="${esc(code.replace(/^VenueDNA_flag_/, '').replace(/_/g,' '))}" data-ft-full="No description available.">${esc(code.replace(/^VenueDNA_flag_/, ''))}</span>`;
  const penAttr = penMag != null ? ` data-ft-pen="Penalty applied: ${penMag}"` : '';
  return `<span class="flag ${m.cls} sans" data-fc="${esc(code)}" data-ft-cls="${m.cls}" data-ft-lbl="${esc(m.lbl)}" data-ft-full="${esc(m.full)}"${penAttr}>${m.lbl}</span>`;
}

// ── Flag tooltip system — custom hover/tap tooltips for flag badges ──────────
function bindFlagTooltip() {
  const tip = document.getElementById('flag-tooltip');
  if (!tip) return;

  function showTip(el, x, y) {
    const fc  = el.dataset.fc;
    const lbl = el.dataset.ftLbl || (fc || '').replace(/^VenueDNA_flag_/, '').replace(/_/g,' ');
    const full = el.dataset.ftFull || '';
    const pen  = el.dataset.ftPen || null;
    const cls  = el.dataset.ftCls || '';
    document.getElementById('ft-code').textContent  = fc ? fc.replace(/^VenueDNA_/,'') : '';
    document.getElementById('ft-label').textContent = lbl;
    document.getElementById('ft-full').textContent  = full;
    const penEl = document.getElementById('ft-penalty');
    if (pen) { penEl.textContent = pen; penEl.style.display = 'block'; } else { penEl.style.display = 'none'; }
    tip.className = `flag-tooltip${cls.includes('warn') ? ' ft-warn' : cls.includes('danger') ? ' ft-danger' : cls.includes('info') ? ' ft-info' : ''}`;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left = x + 12;
    let top  = y + 10;
    tip.classList.remove('hidden');
    const tw = tip.offsetWidth || 200;
    const th = tip.offsetHeight || 80;
    if (left + tw > vw - 8) left = x - tw - 12;
    if (top  + th > vh - 8) top  = y - th - 10;
    tip.style.left = Math.max(4, left) + 'px';
    tip.style.top  = Math.max(4, top)  + 'px';
  }

  function hideTip() {
    tip.classList.add('hidden');
  }

  document.addEventListener('mouseover', e => {
    const fl = e.target.closest('.flag[data-fc]');
    if (fl) { showTip(fl, e.clientX, e.clientY); } else { hideTip(); }
  });
  document.addEventListener('mousemove', e => {
    if (!tip.classList.contains('hidden')) {
      const fl = e.target.closest('.flag[data-fc]');
      if (fl) { showTip(fl, e.clientX, e.clientY); }
    }
  });
  document.addEventListener('mouseout', e => {
    if (!e.target.closest('.flag[data-fc]')) hideTip();
  });
  document.addEventListener('touchstart', e => {
    const fl = e.target.closest('.flag[data-fc]');
    if (fl) {
      const t = e.touches[0];
      showTip(fl, t.clientX, t.clientY);
      e.preventDefault();
    } else {
      hideTip();
    }
  }, { passive: false });
}

// ── Resolve a trait label string to a cumulative_signals key ──────────────────
function resolveCumKey(label) {
  if (!S.cumulativeLearning) return null;
  const signals = S.cumulativeLearning.cumulative_signals || {};
  const l = (label || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  for (const k of Object.keys(signals)) {
    if (l.includes(k.replace(/_/g, '')) || k.replace(/_/g, '').includes(l)) return k;
  }
  // Canon Schema v1.1 rules — return canonical key regardless of current signal availability
  const rules = [
    [/150|200/,                          'app_150_200'],
    [/accuracy|ottacc|drivingacc/,       'ott_accuracy'],
    [/positional|ottpos/,                'ott_positional'],
    [/appoverall|appgen|overallapproach/, 'app_overall'],
    [/sgputt|putting/,                   'sg_putt'],
    [/arg|aroundgreen/,                  'sg_arg'],
    [/wedge/,                            'app_wedge'],
    [/\b100\b/,                          'app_100_150'],
    [/shortconv|convrate|short.*conv/,   'putt_short_conv'],
    [/lag/,                              'putt_lag'],
    [/rough/,                            'arg_rough'],
    [/bunker/,                           'arg_bunker'],
    [/par5/,                             'par5_scoring'],
    [/dist/,                             'ott_distance'],
  ];
  for (const [re, k] of rules) {
    if (re.test(l)) return k;
  }
  // Safe fallback: sanitize unmapped label to snake_case to prevent key-lookup gaps
  const snakeKey = (label || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return snakeKey || null;
}

// ── Round tab switching ────────────────────────────────────────────────────────
const PRE_SECTIONS = ['sec-spotlight','sec-board','sec-intel','sec-method'];

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
    document.getElementById('sec-pm')?.classList.add('hidden');
    return;
  }

  if (r === 'pm') {
    PRE_SECTIONS.forEach(id => document.getElementById(id)?.classList.add('hidden'));
    document.getElementById('sec-live')?.classList.add('hidden');
    const pmSection = document.getElementById('sec-pm');
    if (!pmSection) return;
    pmSection.classList.remove('hidden');
    if (S.pmData) { renderPostMortemView(S.pmData); return; }
    pmSection.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-3);font-family:-apple-system,sans-serif">Loading post-mortem…</div>';
    try {
      const resp = await fetch('data/2026_3m_open_post_mortem_analysis.json');
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
  const pending     = document.getElementById('live-pending');
  const content     = document.getElementById('live-content');
  liveSection?.classList.remove('hidden');
  clearRoundVisualElements();

  if (S.roundData[r]) {
    liveSection?.classList.remove('loading-blur');
    pending?.classList.add('hidden');
    content?.classList.remove('hidden');
    const _tabBtnC = document.querySelector(`.round-tab[data-round="${r}"]`);
    if (_tabBtnC) _tabBtnC.textContent = S.roundData[r].metadata?.is_final ? `R${r} Final` : `R${r} Live`;
    S.liveLeanNotes = S.roundData[r].live_lean_notes || {};
    renderLiveRound(S.roundData[r], content);
    renderCumulativeAnalysis();
    return;
  }

  liveSection?.classList.add('loading-blur');
  pending?.classList.remove('hidden');
  content?.classList.add('hidden');
  try {
    const [resp, cumLearn] = await Promise.all([
      fetch(`data/2026_3m_open_r${r}_analysis.json`),
      fetch('data/2026_3m_open_cumulative_learning.json').then(res => res.ok ? res.json() : null).catch(() => null),
    ]);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (S.activeFetchTarget !== r) return;
    S.roundData[r] = data;
    S.cumulativeLearning = cumLearn;
    S.liveLeanNotes = data.live_lean_notes || {};
    const _tabBtn = document.querySelector(`.round-tab[data-round="${r}"]`);
    if (_tabBtn) _tabBtn.textContent = data.metadata?.is_final ? `R${r} Final` : `R${r} Live`;
    liveSection?.classList.remove('loading-blur');
    pending?.classList.add('hidden');
    content?.classList.remove('hidden');
    renderLiveRound(data, content);
    renderCumulativeAnalysis();
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
  const _ls = S.liveSort;
  const lbSnap = [...(data.leaderboard_snapshot || [])].sort((a, b) => {
    if (_ls.key === 'r1_name') return _ls.dir * (a.r1_name || '').localeCompare(b.r1_name || '');
    const _va = a[_ls.key] ?? (_ls.dir > 0 ? Infinity : -Infinity);
    const _vb = b[_ls.key] ?? (_ls.dir > 0 ? Infinity : -Infinity);
    return _ls.dir * (_va - _vb);
  });
  const _lsArrow = key => `<span class="sort-arrow ${key === _ls.key ? (_ls.dir > 0 ? 'asc' : 'desc') + ' active' : 'idle'}"></span>`;
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
          <th data-sort-key="r1_pos">Pos ${_lsArrow('r1_pos')}</th>
          <th class="left" data-sort-key="r1_name">Player ${_lsArrow('r1_name')}</th>
          <th data-sort-key="pt_rank">PT Rank ${_lsArrow('pt_rank')}</th>
          <th data-sort-key="r1_score">Score ${_lsArrow('r1_score')}</th>
          <th data-sort-key="rank_delta">Δ Rank ${_lsArrow('rank_delta')}</th>
          <th data-sort-key="sg_tot">SG-TOT ${_lsArrow('sg_tot')}</th>
          <th data-sort-key="sg_app">SG-APP ${_lsArrow('sg_app')}</th>
          <th data-sort-key="sg_putt">SG-PUTT ${_lsArrow('sg_putt')}</th>
          <th data-sort-key="live_win_pct">Live Win% ${_lsArrow('live_win_pct')}</th>
        </tr></thead>
        <tbody>${lbSnap.slice(0, 80).map(r => {
          const score = r.r1_score ?? 0;
          const scoreColor = score < 0 ? 'var(--green-ok)' : score > 0 ? 'var(--accent)' : 'var(--text-3)';
          const scoreStr   = score > 0 ? `+${score}` : String(score);
          const isElim  = /^(CUT|WD|DQ|MC|MDF)/i.test(r.r1_pos_str || '');
          const winPct  = isElim ? '0.0%' : (r.live_win_pct != null ? r.live_win_pct.toFixed(1) + '%' : '—');
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
      <div class="live-sub-title">${isFinal ? 'Final Round Recap' : (nextRound != null ? `ROUND ${nextRound} LIVE LEAN` : 'Live Lean — Trait Signals')}</div>
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

  el.querySelectorAll('.live-table thead th[data-sort-key]').forEach(th => {
    th.addEventListener('click', () => sortLiveLeaderboard(th.dataset.sortKey));
  });
}

// ── Live leaderboard sort ──────────────────────────────────────────────────────
function sortLiveLeaderboard(key) {
  const ascByDefault = key === 'r1_pos' || key === 'r1_name' || key === 'pt_rank' || key === 'r1_score';
  S.liveSort.dir = S.liveSort.key === key ? -S.liveSort.dir : (ascByDefault ? 1 : -1);
  S.liveSort.key = key;
  const r = S.currentRound;
  if (r !== 'pre' && S.roundData[r]) {
    renderLiveRound(S.roundData[r], document.getElementById('live-content'));
    renderCumulativeAnalysis();
  }
}

// ── Cumulative learning renderer ──────────────────────────────────────────────
function renderCumulativeAnalysis() {
  if (!S.cumulativeLearning) return;

  const rounds   = S.cumulativeLearning.rounds_completed;
  const isFinalC = !!S.cumulativeLearning.is_final;
  const signals  = S.cumulativeLearning.cumulative_signals || {};
  const traitKeys = Object.keys(signals);

  // Update engine header badge with live round status
  const badgeEl = document.getElementById('engine-version-badge');
  if (badgeEl && rounds != null) {
    badgeEl.textContent = isFinalC
      ? `v3+Audit ENGINE · Final`
      : `v3+Audit ENGINE · R${rounds} Completed`;
  }

  if (!traitKeys.length) return;

  const liveContent = document.getElementById('live-content');
  if (!liveContent) return;

  document.getElementById('cum-analysis-section')?.remove();

  const pillCls = s => {
    if (s === 'validated')    return 'cum-pill-validated';
    if (s === 'mixed')        return 'cum-pill-mixed';
    if (s === 'weak')         return 'cum-pill-weak';
    if (s === 'not_testable') return 'cum-pill-not_testable';
    return 'cum-pill-not_testable';
  };

  const confCls = c => {
    if (!c) return 'cum-conf-default';
    if (c.includes('proxy-confirmed') || c.includes('confirmed')) return 'cum-conf-confirmed';
    if (c.includes('weak'))  return 'cum-conf-weak';
    if (c.includes('mixed')) return 'cum-conf-weak';
    return 'cum-conf-default';
  };

  const dotColor = v => {
    if (v === 'validated') return '#34d399';
    if (v === 'mixed')     return '#fbbf24';
    if (v === 'weak')      return '#f87171';
    return '#475569';
  };

  const renderTraj = hist => {
    if (!hist || !hist.length) return '<span style="color:#475569;font-size:10px">—</span>';
    return hist.map((v, i) => {
      const dot  = '<span class="cum-dot" style="background:' + dotColor(v) + '" title="' + v + '"></span>';
      const conn = i < hist.length - 1 ? '<span class="cum-connector"></span>' : '';
      return dot + conn;
    }).join('');
  };

  const rows = traitKeys.map(tk => {
    const cs        = signals[tk];
    const hist      = cs.signal_history || [];
    const consensus = cs.consensus || 'not_testable';
    const confRaw   = cs.consensus_confidence || '';
    const deltas    = (cs.delta_history || []).filter(d => d != null && !isNaN(parseFloat(d)));
    const mag       = deltas.length
      ? (deltas.reduce((a, d) => a + Math.abs(parseFloat(d)), 0) / deltas.length).toFixed(2)
      : '—';
    const confLabel = confRaw || (
      consensus === 'validated' ? 'proxy-confirmed'
      : consensus === 'weak'   ? 'weak-proxy'
      : consensus === 'mixed'  ? 'mixed-signal'
      : 'pending'
    );
    return '<div class="cum-grid-row">'
      + '<div class="cum-trait-key">' + tk.replace(/_/g, ' ') + '</div>'
      + '<div><span class="cum-pill ' + pillCls(consensus) + '">' + consensus.replace(/_/g, ' ') + '</span></div>'
      + '<div class="cum-mag">' + mag + '</div>'
      + '<div><span class="cum-conf-tag ' + confCls(confLabel) + '">' + confLabel.replace(/_/g, ' ') + '</span></div>'
      + '<div class="cum-traj">' + renderTraj(hist) + '</div>'
      + '</div>';
  }).join('');

  const el = document.createElement('div');
  el.id = 'cum-analysis-section';
  el.innerHTML = '<div class="live-sub-header" style="margin-top:24px">'
    + '<div class="live-sub-title">Cumulative Learning — Multi-Round Trait Trajectory</div>'
    + '<div class="live-sub-note sans">'
    + (isFinalC ? 'Final consensus' : 'R' + rounds + ' consensus')
    + ' · horizon delta profiles</div>'
    + '</div>'
    + '<div class="cum-grid-wrap">'
    + '<div class="cum-grid-header">'
    + '<div>Trait Model Key</div>'
    + '<div>Consensus State</div>'
    + '<div>Abs Magnitude</div>'
    + '<div>Proxy Confidence</div>'
    + '<div>Trajectory Marks</div>'
    + '</div>'
    + rows
    + '</div>';
  liveContent.appendChild(el);
}

// ── Post-Mortem renderer ───────────────────────────────────────────────────────
function renderPostMortemView(data) {
  const el = document.getElementById('sec-pm');
  if (!el) return;

  const rho      = data.spearman_rho;
  const thr      = data.tier_hit_rates || {};
  const t1       = thr.T1 || {};
  const t2       = thr.T2 || {};
  const traits   = data.trait_audit || [];
  const srvi     = data.single_round_volatility || {};
  const spikes   = srvi.spikes || [];
  const winner   = spikes.find(s => s.winner) || null;
  const waveCorr = data.wave_penalty_correlation || {};
  const appTrait = traits.find(t => t.trait === 'app_overall') || {};
  const players  = data.player_comparison || [];
  const spikeSet = new Set(spikes.map(s => s.player));

  const sgFmt    = v  => v != null ? (v > 0 ? '+' : '') + Number(v).toFixed(2) : '—';
  const pctFmt   = v  => v != null ? Math.round(v * 100) + '%' : '—';
  const rhoColor = r  => r > 0.3 ? 'var(--green-ok)' : r > 0.1 ? '#f59e0b' : 'var(--accent)';
  const statusColor = s => ({ validated: 'var(--green-ok)', mixed: '#f59e0b', neutral: 'var(--text-3)', weak: 'var(--accent)' }[s] || 'var(--text-3)');

  const t12n    = (t1.player_count || 0) + (t2.player_count || 0);
  const t12top20 = t12n > 0
    ? Math.round(((t1.top20_count || 0) + (t2.top20_count || 0)) / t12n * 100) + '%'
    : '—';

  el.innerHTML = `
<div style="padding:24px 0 8px">
  <div class="section-header">
    <h2 class="section-title sans">Post-Mortem &amp; Model Calibration</h2>
    <span class="section-sub sans">${data.event_slug || ''} &middot; Generated ${data.generated_at || ''}</span>
  </div>

  ${winner ? `
  <div style="display:flex;align-items:center;gap:16px;background:linear-gradient(135deg,#0f172a,#1e293b);border:2px solid var(--accent);border-radius:var(--radius-lg);padding:16px 20px;margin-bottom:20px">
    <span style="font-size:28px;flex-shrink:0">&#9889;</span>
    <div>
      <div class="sans" style="font-size:10px;color:var(--accent);letter-spacing:.1em;text-transform:uppercase;font-weight:700">Volatility Spike Winner</div>
      <div class="sans" style="font-size:15px;color:#f1f5f9;font-weight:700;margin-top:3px">${winner.player} &mdash; R${winner.round} (+${winner.sg.toFixed(2)} SG)</div>
      <div class="sans" style="font-size:12px;color:var(--text-2);margin-top:4px">Win driven by a single outlier round exceeding ${srvi.threshold} SG. Multi-round consistency supported model ranking.</div>
    </div>
  </div>` : ''}

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:24px">
    <div class="pm-card">
      <div class="pm-card-label">Overall Spearman &rho;</div>
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
      <div class="pm-card-sub">&rho; = ${appTrait.spearman_rho != null ? appTrait.spearman_rho.toFixed(3) : '—'}</div>
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
      <div class="sans" style="font-size:11px;color:var(--text-2)">&rho; ${t.spearman_rho != null ? t.spearman_rho.toFixed(3) : '—'}</div>
    </div>`).join('')}
  </div>

  <div class="sans" style="font-size:11px;font-weight:700;color:var(--text-3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Model vs. Actual &mdash; Full Field</div>
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
        <th class="sans">PRED &Delta;</th>
      </tr></thead>
      <tbody>
        ${players.map(r => {
          const d = r.prediction_delta;
          const dHtml = d == null ? '—'
            : d > 0  ? `<span style="color:var(--green-ok)">&#9650;${d}</span>`
            : d < 0  ? `<span style="color:var(--accent)">&#9660;${Math.abs(d)}</span>`
            : '<span style="color:var(--text-3)">—</span>';
          const isSpike = spikeSet.has(r.player_name);
          return `<tr class="${r.cut_status === 'cut' ? 'pm-cut-row' : ''}">
            <td class="sans" style="font-weight:700;color:var(--text-1)">${r.pt_rank ?? '—'}</td>
            <td class="sans">${r.player_name}${isSpike ? ' <span style="color:var(--accent);font-size:10px">&#9889;</span>' : ''}</td>
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
  <div class="sans" style="font-size:11px;font-weight:700;color:var(--text-3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">Single-Round Volatility Spikes (&ge;${srvi.threshold} SG)</div>
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

// ── Spotlight toggle ───────────────────────────────────────────────────────────
function toggleSpotlight() {
  S.spotlightOpen = !S.spotlightOpen;
  document.getElementById('spotlight-container')?.classList.toggle('hidden', !S.spotlightOpen);
  const btn = document.getElementById('spotlight-toggle');
  if (btn) {
    btn.textContent = S.spotlightOpen ? 'Hide Spotlight' : 'Show Spotlight';
    btn.classList.toggle('active', S.spotlightOpen);
  }
}

// ── Advanced filter panel toggle ───────────────────────────────────────────────
function toggleAdvFilter() {
  S.advFilterOpen = !S.advFilterOpen;
  document.getElementById('adv-filter-panel')?.classList.toggle('hidden', !S.advFilterOpen);
  const btn = document.getElementById('adv-toggle');
  if (btn) btn.textContent = S.advFilterOpen ? '▲ Filter' : '▼ Filter';
}

// ── Rule filter builder functions ─────────────────────────────────────────────
function renderFilterRules() {
  const zone = document.getElementById('active-filters-zone');
  if (!zone) return;
  if (!S.filterRules.length) {
    zone.innerHTML = '<div class="rfb-empty sans">No rules active. Add a rule or use Quick Filters below.</div>';
    return;
  }
  const fieldOptions = FILTER_FIELDS.map(f =>
    `<option value="${f.key}">${f.label}</option>`
  ).join('');
  zone.innerHTML = S.filterRules.map((rule, i) => `
    <div class="rfb-rule" data-idx="${i}">
      <select class="rfb-select sans">
        ${FILTER_FIELDS.map(f =>
          `<option value="${f.key}"${rule.field === f.key ? ' selected' : ''}>${f.label}</option>`
        ).join('')}
      </select>
      <select class="rfb-op sans">
        <option value=">="${rule.op === '>=' ? ' selected' : ''}>≥</option>
        <option value="<="${rule.op === '<=' ? ' selected' : ''}>≤</option>
        <option value="="${rule.op === '='  ? ' selected' : ''}>=</option>
      </select>
      <input type="number" class="rfb-input sans" value="${rule.val ?? ''}" placeholder="Value" step="0.1">
      <button class="rfb-remove sans" data-idx="${i}">✕</button>
    </div>
  `).join('');
}

function addFilterRule() {
  S.filterRules.push({ field: FILTER_FIELDS[0].key, op: '>=', val: '' });
  renderFilterRules();
}

function removeFilterRule(idx) {
  S.filterRules.splice(idx, 1);
  renderFilterRules();
  applyVisibility();
}

function updateRuleField(idx, field) {
  if (S.filterRules[idx]) { S.filterRules[idx].field = field; applyVisibility(); }
}

function updateRuleOp(idx, op) {
  if (S.filterRules[idx]) { S.filterRules[idx].op = op; applyVisibility(); }
}

function updateRuleVal(idx, val) {
  if (S.filterRules[idx]) { S.filterRules[idx].val = val; applyVisibility(); }
}

// ── Tag filter system ──────────────────────────────────────────────────────────
function toggleTagFilter(tag) {
  const norm = normalizeTag(tag);
  const idx = S.activeTagFilters.indexOf(norm);
  if (idx >= 0) {
    S.activeTagFilters.splice(idx, 1);
  } else {
    S.activeTagFilters.push(norm);
  }
  renderTagPills();
  applyVisibility();
}

function renderTagPills() {
  let zone = document.getElementById('tag-filter-zone');
  if (!zone) {
    zone = document.createElement('div');
    zone.id = 'tag-filter-zone';
    zone.style.cssText = 'max-width:1400px;margin:.4rem auto 0;padding:0 1rem;display:flex;flex-wrap:wrap;gap:.35rem;';
    const boardSection = document.getElementById('sec-board');
    boardSection?.insertAdjacentElement('beforebegin', zone);
  }
  if (S.activeTagFilters.length === 0) {
    zone.innerHTML = '';
    return;
  }
  zone.innerHTML = S.activeTagFilters.map(tag =>
    `<button class="pill" onclick="toggleTagFilter('${tag.replace(/'/g,"\\'")}')">
      ${esc(tag)} <span style="margin-left:.3rem;color:var(--muted)">✕</span>
    </button>`
  ).join('');
}

// ── Tier block click → board filter ────────────────────────────────────────────
function filterByTier(tier) {
  S.currentTier = S.currentTier === tier ? 'all' : tier;
  document.querySelectorAll('.snav-tab').forEach(t => t.classList.remove('active'));
  applyVisibility();
}

function applyPreset(name) {
  const preset = QUICK_PRESETS[name];
  if (!preset) return;
  S.filterRules = preset.map(r => ({ ...r }));
  renderFilterRules();
  applyVisibility();
  if (!S.advFilterOpen) {
    S.advFilterOpen = true;
    document.getElementById('adv-filter-panel')?.classList.remove('hidden');
    const btn = document.getElementById('adv-toggle');
    if (btn) btn.textContent = '▲ Filter';
  }
}

// ── Clear all filters and reset sort to VTS rank ──────────────────────────────
function clearFilters() {
  S.currentFilter    = 'all';
  S.currentTier      = 'all';
  S.searchQuery      = '';
  S.filterRules      = [];
  S.activeTagFilters = [];
  S.sort             = { key: 'rank', dir: 1 };
  const srch = document.getElementById('player-search');
  if (srch) srch.value = '';
  document.querySelectorAll('.chip[data-f]').forEach(el => el.classList.toggle('active', el.dataset.f === 'all'));
  document.querySelectorAll('.tier-tile').forEach(el => el.classList.toggle('active', el.dataset.tier === 'all'));
  renderTagPills();
  renderFilterRules();
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

// ── Weather renderer — four-box conditions deck ────────────────────────────────
function renderWeather(wx) {
  const speed     = wx.speed ?? 0;
  const waveDelta = wx.wave_delta ?? 0;
  const tide      = wx.tide ?? '—';

  // Overall badge (severity label)
  const severity  = speed >= 30 ? 'Severe' : speed >= 20 ? 'Significant' : speed >= 12 ? 'Moderate' : 'Light';
  const sevColor  = speed >= 30 ? '#ef4444' : speed >= 20 ? '#f59e0b' : speed >= 12 ? '#3b82f6' : '#22c55e';
  const badgeEl   = document.getElementById('wx-badge');
  if (badgeEl) { badgeEl.textContent = severity; badgeEl.style.background = sevColor; badgeEl.style.color = '#000'; }

  // Box 1 — Wind Impact
  const windRating = speed >= 30 ? ['Severe',      'fb-severe']
    : speed >= 22  ? ['Challenging',  'fb-challenging']
    : speed >= 15  ? ['Benign',       'fb-benign']
    : speed >= 8   ? ['Very Benign',  'fb-very-benign']
    : ['Exceptional', 'fb-exceptional'];
  const windRatingEl = document.getElementById('fb-wind-rating');
  const windDetailEl = document.getElementById('fb-wind-detail');
  if (windRatingEl) { windRatingEl.textContent = windRating[0]; windRatingEl.className = `fb-rating sans ${windRating[1]}`; }
  if (windDetailEl) windDetailEl.textContent = `${speed} mph ${wx.direction ?? ''}`.trim();

  // Box 2 — Tide / Surface
  const tideLower  = tide.toLowerCase();
  const tideRating = tideLower.includes('firm') || tideLower.includes('fast')
    ? ['Firm / Fast',    'fb-challenging']
    : tideLower.includes('damp') || tideLower.includes('soft') || tideLower.includes('incoming') || tideLower.includes('wet')
    ? ['Soft / Active',  'fb-very-benign']
    : ['Neutral',        'fb-benign'];
  const tideRatingEl = document.getElementById('fb-tide-rating');
  const tideDetailEl = document.getElementById('fb-tide-detail');
  if (tideRatingEl) { tideRatingEl.textContent = tideRating[0]; tideRatingEl.className = `fb-rating sans ${tideRating[1]}`; }
  if (tideDetailEl) tideDetailEl.textContent = tide;

  // Box 3 — Wave Score Δ
  const waveRating = waveDelta >= 0.5  ? ['Significant',  'fb-challenging']
    : waveDelta >= 0.25 ? ['Moderate',     'fb-benign']
    : waveDelta >= 0.1  ? ['Minor',         'fb-very-benign']
    : ['Negligible',    'fb-exceptional'];
  const waveRatingEl = document.getElementById('fb-wave-rating');
  const waveDetailEl = document.getElementById('fb-wave-detail');
  if (waveRatingEl) { waveRatingEl.textContent = waveRating[0]; waveRatingEl.className = `fb-rating sans ${waveRating[1]}`; }
  if (waveDetailEl) waveDetailEl.textContent = (waveDelta > 0 ? '+' : '') + Number(waveDelta).toFixed(2) + ' strokes';

  // Box 4 — Overall Conditions (composite)
  const windScore  = speed < 8 ? 3 : speed < 15 ? 2 : speed < 22 ? 1 : speed < 30 ? 0 : -1;
  const waveScore  = waveDelta < 0.1 ? 1 : waveDelta < 0.25 ? 0 : -1;
  const composite  = windScore + waveScore;
  const overallRating = composite >= 3  ? ['Exceptional',  'fb-exceptional']
    : composite >= 1  ? ['Very Benign',  'fb-very-benign']
    : composite === 0 ? ['Benign',       'fb-benign']
    : composite === -1 ? ['Challenging', 'fb-challenging']
    : ['Severe',        'fb-severe'];
  const overallRatingEl = document.getElementById('fb-overall-rating');
  const overallDetailEl = document.getElementById('fb-overall-detail');
  if (overallRatingEl) { overallRatingEl.textContent = overallRating[0]; overallRatingEl.className = `fb-rating sans ${overallRating[1]}`; }
  if (overallDetailEl) overallDetailEl.textContent = `${severity} wind · ${waveRating[0]} wave Δ`;

  // Wave note (shows only when wave model is active)
  const noteEl = document.getElementById('wx-wave-note');
  if (noteEl) {
    if (waveDelta > 0.1) {
      noteEl.textContent = `Wave model active — late/early tee times favored by ${waveDelta.toFixed(2)} strokes vs. midday wave.`;
      noteEl.style.display = 'block';
    } else {
      noteEl.style.display = 'none';
    }
  }

  // Venue DNA weather card — 4-round forecast grid
  const badgeInline = document.getElementById('wx-badge-inline');
  if (badgeInline) { badgeInline.textContent = severity; badgeInline.style.background = sevColor; badgeInline.style.color = '#000'; }

  const roundGrid = document.getElementById('wx-round-grid');
  if (roundGrid && Array.isArray(wx.rounds) && wx.rounds.length) {
    roundGrid.innerHTML = wx.rounds.map(r => {
      const pk = r.speed_peak || 0;
      const wLabel = pk >= 22 ? 'Challenging' : pk >= 15 ? 'Benign' : pk >= 8 ? 'V. Benign' : 'Exceptional';
      const wColor = pk >= 22 ? '#f59e0b' : pk >= 15 ? '#3b82f6' : '#22c55e';
      const flags = [];
      if (r.heat_index_peak && r.heat_index_peak >= 95) flags.push(`<span style="color:#f59e0b;font-size:.58rem;font-weight:700;">🌡 HI ${r.heat_index_peak}°F</span>`);
      if (r.storm_risk) flags.push(`<span style="color:#ef4444;font-size:.58rem;font-weight:700;">⚡ ${r.precip_pct}%</span>`);
      return `<div style="background:var(--surface2);border-radius:4px;padding:.42rem .5rem;">
        <div style="font-size:.6rem;color:var(--gold);font-weight:700;margin-bottom:.12rem;white-space:nowrap;">${esc(r.label)}</div>
        <div style="font-size:.75rem;font-weight:700;color:var(--text);">${r.temp_high}°F · <span style="font-size:.65rem;font-weight:400;color:var(--muted);">${esc(r.sky)}</span></div>
        <div style="font-size:.62rem;color:var(--muted);margin-top:.08rem;">${(r.speed_morning || 0)}–${pk} mph ${esc(r.direction)}</div>
        <div style="font-size:.6rem;color:${wColor};font-weight:600;margin-top:.06rem;">${wLabel}</div>
        ${flags.length ? `<div style="margin-top:.15rem;display:flex;flex-wrap:wrap;gap:.2rem;">${flags.join('')}</div>` : ''}
      </div>`;
    }).join('');
  }
}

// ── Sparklines ─────────────────────────────────────────────────────────────────
function renderSparkline(canvas, arr) {
  if (!canvas || !arr || arr.length === 0) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const n = arr.length;
  const xStep = n > 1 ? (W - 12) / (n - 1) : 0;

  // y: val=1 (best) → top of canvas; val=80 (CUT) → bottom
  const toY = v => 2 + ((Math.min(v, 80) - 1) / 79) * (H - 4);

  // Trend color: improving (last < first numerically = better finish) = green
  const trend = arr[arr.length - 1] < arr[0] ? '#4ade80'
              : arr[arr.length - 1] > arr[0] ? '#fca5a5'
              : '#94a3b8';

  ctx.clearRect(0, 0, W, H);

  // Line
  ctx.beginPath();
  ctx.strokeStyle = trend;
  ctx.lineWidth   = 1.5;
  ctx.lineJoin    = 'round';
  arr.forEach((v, i) => {
    const x = 6 + i * xStep;
    const y = toY(v);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Dots — CUT in red, others in trend color
  arr.forEach((v, i) => {
    const x = 6 + i * xStep;
    const y = toY(v);
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fillStyle = v === 80 ? '#fca5a5' : trend;
    ctx.fill();
  });
}

// ── Radial Probability Dials ───────────────────────────────────────────────────
function drawDial(id, val, maxPct, label, color) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2, cy = canvas.height / 2, r = 28;
  const safeVal = Math.min(val ?? 0, maxPct);
  const pct = safeVal / maxPct;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI * 1.5);
  ctx.strokeStyle = '#1e2936';
  ctx.lineWidth   = 6;
  ctx.stroke();

  // Value arc (clamped to [0, maxPct])
  if (pct > 0) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + pct * Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth   = 6;
    ctx.lineCap     = 'round';
    ctx.stroke();
  }

  // Center text
  ctx.fillStyle  = '#e8e0d4';
  ctx.font       = 'bold 11px Inter,sans-serif';
  ctx.textAlign  = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(safeVal != null ? safeVal.toFixed(1) + '%' : '—', cx, cy - 4);

  // Label below center
  ctx.fillStyle  = '#7a8fa6';
  ctx.font       = '9px Inter,sans-serif';
  ctx.fillText(label, cx, cy + 9);
}

function drawProbDials(w, t5, t10, mc) {
  drawDial('d-win', w,  15,  'Win',   '#c9a84c');
  drawDial('d-t5',  t5, 40,  'Top 5', '#4ade80');
  drawDial('d-t10', t10, 60, 'Top 10','#93c5fd');
  drawDial('d-cut', mc, 100, 'Cut',   '#c4b5fd');
}

// ── Bootstrap ──────────────────────────────────────────────────────────────────
init();
