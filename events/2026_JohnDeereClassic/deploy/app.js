/* PGA VenueDNA — John Deere Classic 2026 */

/* ── Anti-pattern metadata ── */
const AP_META = {
  bomb_and_spray: {
    cls: 'bomb', label: 'Bomb + Spray',
    desc: 'Elite distance with below-field driving accuracy — high tee-box variance at a placement-premium course. Fairway width is moderate; missing it here carries a real short-game penalty.',
    severity: '-1.0 to -2.5',
  },
  wedge_liability: {
    cls: 'wedge', label: 'Wedge Liability',
    desc: 'Below-field wedge proximity inside 150 yd — drag on the highest-weighted scoring trait at Deere Run. This venue bakes in a continual birdie diet; weak wedge play breaks the scoring run.',
    severity: '-2.0 to -5.0',
  },
  poor_birdie_conv: {
    cls: 'birdie', label: 'Poor Birdie Conv',
    desc: 'Low short-putt conversion limits birdie upside at a birdie-fest track. TPC Deere Run returns ~4–5 birdie looks per round; players who cannot convert have no path to contention.',
    severity: '-1.5 to -4.0',
  },
  rough_approach_liab: {
    cls: 'rough', label: 'Rough Approach',
    desc: 'Below-field approach quality from KBG/Fine Fescue rough — a risk multiplier when fairways are missed. Soft conditions amplify this because rough clings and controls spin poorly.',
    severity: '-1.0 to -2.5',
  },
};

/* ── Global state ── */
let PAYLOAD      = null;
let allPlayers   = [];
let searchQuery  = '';
let activeTier   = 'all';
let sortCol      = 'rank';
let sortDir      = 1;        // 1 = asc, -1 = desc
let filterFlagged = false;
let filterDebut  = false;

const DATA_PATH = 'data/event_payload.json';

/* ════════════════════════════════════════════
   BOOT
════════════════════════════════════════════ */
async function init() {
  try {
    PAYLOAD = await fetch(DATA_PATH).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
  } catch (e) {
    document.body.innerHTML =
      `<div style="padding:2rem;color:#fca5a5;font-family:monospace">
        Failed to load payload: ${e.message}<br>
        Expected: ${DATA_PATH}
      </div>`;
    return;
  }

  /* Build flat player list from tier objects (tiers are already rank-sorted) */
  allPlayers = [];
  for (let t = 1; t <= 5; t++) {
    for (const p of (PAYLOAD.tiers[`tier_${t}`] || [])) {
      p.flag_count = p.anti_pattern_flags
        ? p.anti_pattern_flags.split(';').filter(Boolean).length
        : 0;
      allPlayers.push(p);
    }
  }
  allPlayers.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999));

  renderHeader();
  renderInfoStrip();
  renderWinnerSection();
  renderTraitWeights();
  renderAPPanel();
  renderTierSections();
  renderAuditFooter();

  wireSearch();
  wireTierTabs();
  wireSort();
  wireToggles();
  wireModal();

  applyAndRender();
}

/* ════════════════════════════════════════════
   HELPERS
════════════════════════════════════════════ */
function fmtName(raw) {
  if (!raw) return '';
  const parts = raw.split(',').map(s => s.trim());
  return parts.length > 1 ? `${parts[1]} ${parts[0]}` : raw;
}

function kv(label, val) {
  const display = (val === null || val === undefined || val === '') ? '—' : val;
  return `<div class="kv"><span class="k">${label}</span><span class="v">${display}</span></div>`;
}

function apChip(flag) {
  const m = AP_META[flag];
  if (!m) return '';
  return `<span class="ap-chip ${m.cls}" title="${m.label}: ${m.desc.split('.')[0]}">${m.label}</span>`;
}

function debutChip(p) {
  if (!p.debut_flag) return '';
  const cls = (p.debut_class || '').toUpperCase() === 'A' ? 'debut-a' : 'debut-b';
  return `<span class="debut-chip ${cls}" title="Debut at TPC Deere Run — Class ${p.debut_class}">DEBUT-${p.debut_class || '?'}</span>`;
}

function tierBadge(tier, label) {
  return `<span class="tier-badge t${tier}">${label || `T${tier}`}</span>`;
}

function vfdDisplay(vfd) {
  if (vfd === null || vfd === undefined) return '<span style="color:var(--muted)">—</span>';
  const cls = vfd <= 0 ? 'vfd-neg' : 'vfd-pos';
  return `<span class="${cls}">${vfd > 0 ? '+' : ''}${Number(vfd).toFixed(1)}</span>`;
}

function sgDisplay(sg) {
  if (sg === null || sg === undefined) return '<span style="color:var(--muted)">—</span>';
  const col = sg >= 0 ? '#86efac' : '#fca5a5';
  return `<span style="color:${col}">${sg > 0 ? '+' : ''}${Number(sg).toFixed(2)}</span>`;
}

function vtsBar(vts, max = 90) {
  const pct = Math.min(100, Math.max(0, (vts / max) * 100));
  return `<div class="vts-bar-wrap">
    <span class="vts-num">${Number(vts).toFixed(1)}</span>
    <div class="vts-bar-bg"><div class="vts-bar-fill" style="width:${pct.toFixed(0)}%"></div></div>
  </div>`;
}

/* ════════════════════════════════════════════
   RENDER: HEADER
════════════════════════════════════════════ */
function renderHeader() {
  const ev  = PAYLOAD.event;
  const ms  = PAYLOAD.model_summary;
  const ven = PAYLOAD.venue;

  document.querySelector('.event-name').textContent = ev.name;

  document.querySelector('.header-meta').textContent =
    `${ev.venue} · ${ven.location} · ${ev.dates} · Par ${ev.par} · ${ev.yardage.toLocaleString()} yds · ${ev.field_size} players · ${ev.cut_rule.replace(/_/g,' ')}`;

  document.querySelector('.header-subtitle').textContent =
    'TPC Deere Run is a soft-wet birdie-fest where wedge control, short-putt conversion, and par-5 scoring drive separation.';

  const badges = document.querySelector('.badges');
  if (ev.field_locked) {
    badges.insertAdjacentHTML('beforeend', '<span class="badge badge-locked">FIELD LOCKED</span>');
  }
  if (!PAYLOAD.metadata?.tee_times_available) {
    badges.insertAdjacentHTML('beforeend', '<span class="badge badge-tbd">TEE TIMES TBD</span>');
  }
  if (ms.event_iteration) {
    badges.insertAdjacentHTML('beforeend', `<span class="badge badge-iter">iter: ${ms.event_iteration}</span>`);
  }
}

/* ════════════════════════════════════════════
   RENDER: INFO STRIP
════════════════════════════════════════════ */
function renderInfoStrip() {
  const v  = PAYLOAD.venue;
  const ws = PAYLOAD.weather_summary;
  const ms = PAYLOAD.model_summary;
  const td = ms.tier_distribution;
  const t1 = PAYLOAD.tiers.tier_1?.[0];

  /* Venue DNA */
  document.querySelector('.venue-dna-card').innerHTML = `
    <div class="info-card-title">Venue DNA — TPC Deere Run</div>
    <p class="venue-explainer">This is a conversion track, not a survival test. Reduced rollout and receptive greens lower the raw distance premium and push scoring toward short-iron precision plus birdie cash-in.</p>
    ${kv('Dominant Trait', v.dominant_trait)}
    ${kv('Dominant Weight', (v.dominant_trait_weight * 100).toFixed(0) + '% of VTS')}
    ${kv('Scoring Profile', v.scoring_profile)}
    ${kv('Variance Class', v.variance_class)}
    ${kv('Comp Courses', (v.comp_courses || []).join(' · '))}
    ${kv('Signature Stretch', v.signature_stretch)}
    ${kv('Scoring Avg (DG)', v.scoring_avg)}
    ${kv('Surface', (v.surface || '').split('(')[0].trim())}
  `;

  /* Weather */
  document.querySelector('.weather-card').innerHTML = `
    <div class="info-card-title">Weather Lock — ${(ws.forecast_class || '').replace(/_/g, '-')}</div>
    <div class="weather-chips">
      <span class="weather-chip chip-heat">🌡 ${ws.heat_alert}</span>
      <span class="weather-chip chip-storm">⛈ ${ws.primary_risk_window}</span>
      <span class="weather-chip chip-neutral">💨 ${ws.wind_profile}</span>
      <span class="weather-chip chip-good">✓ Best: ${ws.best_scoring_day}</span>
      <span class="weather-chip chip-storm">⚠ Delay: ${ws.delay_risk}</span>
    </div>
    ${kv('Course Effect', ws.course_effect)}
    <p class="weather-explainer">Extreme heat hits early, but the larger scoring effect is Friday–Saturday moisture, which should soften surfaces and increase receptivity before a cleaner Sunday finish.</p>
  `;

  /* Model snapshot */
  document.querySelector('.model-snapshot-card').innerHTML = `
    <div class="info-card-title">Model Snapshot</div>
    <div class="model-winner-name">${fmtName(ms.model_winner)}</div>
    <div class="model-winner-sub">Model Winner · VTS ${ms.model_winner_vts} · Tier 1 — ${PAYLOAD.tier_labels['1']}</div>
    ${t1 ? `
    <div class="stat-row">
      <div class="stat-pill"><span class="stat-val">${t1.win_pct.toFixed(2)}%</span><span class="stat-label">Win</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.top10_pct.toFixed(0)}%</span><span class="stat-label">Top 10</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.top20_pct.toFixed(0)}%</span><span class="stat-label">Top 20</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.make_cut_pct.toFixed(0)}%</span><span class="stat-label">Cut</span></div>
    </div>
    <div style="font-size:.66rem;color:var(--muted);margin-bottom:.5rem">${t1.trait_summary}</div>
    ` : ''}
    <div style="display:flex;gap:.38rem;flex-wrap:wrap">
      <span class="td-chip t1">T1 <b>${td['1']}</b></span>
      <span class="td-chip t2">T2 <b>${td['2']}</b></span>
      <span class="td-chip t3">T3 <b>${td['3']}</b></span>
      <span class="td-chip t4">T4 <b>${td['4']}</b></span>
      <span class="td-chip t5">T5 <b>${td['5']}</b></span>
    </div>
  `;
}

/* ════════════════════════════════════════════
   RENDER: WINNER SPOTLIGHT
════════════════════════════════════════════ */
function renderWinnerSection() {
  const winner = PAYLOAD.tiers.tier_1?.[0];
  const top3   = [
    PAYLOAD.tiers.tier_1?.[0],
    PAYLOAD.tiers.tier_2?.[0],
    PAYLOAD.tiers.tier_2?.[1],
  ].filter(Boolean);

  if (!winner) {
    document.querySelector('.winner-inner').innerHTML = '<p style="color:var(--muted)">No Tier 1 player found.</p>';
    return;
  }

  document.querySelector('.winner-inner').innerHTML = `
    <div class="section-title">Model Winner — Sole Tier 1 Course Architect</div>
    <div class="winner-card">
      <div>
        <div class="winner-badge">Tier 1 — ${PAYLOAD.tier_labels['1']}</div>
        <div class="winner-name">${fmtName(winner.player_name)}</div>
        <div class="winner-name-sub">#${winner.rank} overall · VTS ${winner.vts_final} · ${winner.primary_driver}</div>
        <div class="winner-stats">
          <div class="winner-stat"><div class="winner-stat-val">${winner.win_pct.toFixed(2)}%</div><div class="winner-stat-label">Win</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top5_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 5</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top10_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 10</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top20_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 20</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.make_cut_pct.toFixed(0)}%</div><div class="winner-stat-label">Cut</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.vts_final}</div><div class="winner-stat-label">VTS</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.neutral_sg >= 0 ? '+' : ''}${Number(winner.neutral_sg).toFixed(2)}</div><div class="winner-stat-label">SG Neutral</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${Number(winner.vfd).toFixed(1)}</div><div class="winner-stat-label">VFD</div></div>
        </div>
        <div class="winner-trace">${winner.trace_notes}</div>
      </div>
      <div class="winner-narrative">
        <h3>Birdie-Fit Analysis</h3>
        <p>${winner.tier_reason}</p>
        <p style="margin-top:.45rem">${winner.trait_summary}</p>
        ${winner.vh_rounds > 0 ? `<p style="margin-top:.4rem;font-size:.72rem">${winner.vh_rounds} course-history rounds · VH SG ${Number(winner.vh_sg).toFixed(3)}</p>` : ''}
        ${winner.anti_pattern_flags
          ? `<p style="margin-top:.4rem;color:#fca5a5;font-size:.7rem">⚠ ${winner.anti_pattern_flags.split(';').filter(Boolean).join(', ')}</p>`
          : '<p style="margin-top:.4rem;color:#86efac;font-size:.7rem">✓ No anti-pattern flags</p>'}
      </div>
    </div>

    <div class="top3-label">Top-3 Model Contenders</div>
    <div class="top3-grid">
      ${top3.map(p => miniCard(p)).join('')}
    </div>
  `;
}

function miniCard(p) {
  const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  return `
    <div class="mini-card t${p.tier}-card">
      <span class="mini-rank">#${p.rank}</span>
      <div class="mini-name">${fmtName(p.player_name)}</div>
      <div class="mini-driver">${p.primary_driver}</div>
      <div class="mini-stats">
        <span class="mini-stat"><b>${p.vts_final}</b> VTS</span>
        <span class="mini-stat"><b>${p.win_pct.toFixed(2)}%</b> Win</span>
        <span class="mini-stat"><b>${p.top10_pct.toFixed(0)}%</b> T10</span>
        <span class="mini-stat"><b>${p.make_cut_pct.toFixed(0)}%</b> Cut</span>
      </div>
      ${flags.length ? `<div class="mini-flags">${flags.map(f => apChip(f)).join('')}</div>` : ''}
      <div class="mini-tier-reason">${p.tier_reason}</div>
    </div>
  `;
}

/* ════════════════════════════════════════════
   RENDER: TRAIT WEIGHTS
════════════════════════════════════════════ */
function renderTraitWeights() {
  const twm = PAYLOAD.model_summary.trait_weight_matrix;

  const CLUSTER = new Set(['app_wedge','app_100_150','putt_short_conv','putt_lag','par5_scoring']);

  const rows = [
    { key: 'app_wedge',       label: 'APP Wedge',       w: twm.app_wedge },
    { key: 'app_100_150',     label: 'APP 100–150',      w: twm.app_100_150 },
    { key: 'putt_short_conv', label: 'Putt Short Conv',  w: twm.putt_short_conv },
    { key: 'ott_accuracy',    label: 'OTT Accuracy',     w: twm.ott_accuracy },
    { key: 'putt_lag',        label: 'Putt Lag',         w: twm.putt_lag },
    { key: 'par5_scoring',    label: 'Par-5 Scoring',    w: twm.par5_scoring },
    { key: 'app_150_200',     label: 'APP 150–200',      w: twm.app_150_200 },
    { key: 'arg_rough',       label: 'ARG Rough',        w: twm.arg_rough },
    { key: 'ott_distance',    label: 'OTT Distance',     w: twm.ott_distance },
    { key: 'arg_bunker',      label: 'ARG Bunker',       w: twm.arg_bunker },
  ].sort((a, b) => b.w - a.w);

  const maxW = Math.max(...rows.map(r => r.w));
  const clusterSum = [...CLUSTER].reduce((s, k) => s + (twm[k] || 0), 0);

  document.querySelector('.weights-panel').innerHTML = `
    <div class="weights-grid">
      ${rows.map(r => {
        const isCluster = CLUSTER.has(r.key);
        const barPct = ((r.w / maxW) * 100).toFixed(0);
        return `<div class="weight-row">
          <span class="weight-label${isCluster ? ' cluster' : ''}">${r.label}${isCluster ? ' ★' : ''}</span>
          <div class="weight-bar-bg">
            <div class="weight-bar-fill${isCluster ? ' cluster-bar' : ''}" style="width:${barPct}%"></div>
          </div>
          <span class="weight-pct">${(r.w * 100).toFixed(0)}%</span>
        </div>`;
      }).join('')}
    </div>
    <p class="weights-legend">
      ★ Decision cluster (APP Wedge + APP 100–150 + Putt Short Conv + Putt Lag + Par-5 Scoring) = <strong style="color:var(--accent)">${(clusterSum * 100).toFixed(0)}%</strong> of model weight.
      This cluster captures wedge pressure, birdie conversion, and par-5 leverage — the three axes that separate at Deere Run.
    </p>
  `;
}

/* ════════════════════════════════════════════
   RENDER: ANTI-PATTERN PANEL
════════════════════════════════════════════ */
function renderAPPanel() {
  const apFlags = PAYLOAD.flags?.anti_patterns || [];
  const apSeverity = PAYLOAD.model_summary.anti_patterns || {};

  /* Aggregate per-player totals */
  const penMap  = {};
  const flagMap = {};
  for (const entry of apFlags) {
    penMap[entry.player]  = (penMap[entry.player]  || 0) + entry.penalty_vts;
    flagMap[entry.player] = flagMap[entry.player] || new Set();
    flagMap[entry.player].add(entry.flag);
  }

  const sorted = Object.entries(penMap)
    .sort((a, b) => a[1] - b[1])   /* most negative first */
    .slice(0, 12);

  const t5Names = new Set((PAYLOAD.tiers.tier_5 || []).map(p => p.player_name));

  const apOrder = ['bomb_and_spray','wedge_liability','poor_birdie_conv','rough_approach_liab'];

  document.querySelector('.ap-panel').innerHTML = `
    <p class="ap-explainer">
      At Deere Run, weak wedge play and poor birdie conversion are more dangerous than raw inaccuracy because
      the venue rewards players who turn makeable looks into scoring runs. The par-71 layout generates 4–5 genuine
      birdie opportunities per round; players with anti-pattern exposure cannot build the sustained scoring runs
      that define leaderboard contention here.
    </p>

    <div class="ap-definitions">
      ${apOrder.map(key => {
        const m   = AP_META[key];
        const sev = apSeverity[key];
        if (!m) return '';
        return `
          <div class="ap-def-card">
            <div class="ap-def-name ap-${m.cls}">${m.label}</div>
            <div class="ap-def-severity">Severity band: ${sev ? `${sev[0]} to ${sev[1]} VTS pts` : '—'}</div>
            <div class="ap-def-desc">${m.desc}</div>
          </div>`;
      }).join('')}
    </div>

    <div class="ap-sub-title">Most Penalized — Active Anti-Pattern Flags</div>
    <div class="ap-pen-list">
      ${sorted.map(([name, total], i) => {
        const flags  = [...(flagMap[name] || [])];
        const isT5   = t5Names.has(name);
        return `
          <div class="ap-pen-row"${isT5 ? ' style="border-color:color-mix(in srgb,var(--t5) 35%,var(--border))"' : ''}>
            <span class="ap-pen-idx">${i + 1}.</span>
            <span class="ap-pen-name">${fmtName(name)}${isT5 ? ' ' + tierBadge(5) : ''}</span>
            <span class="ap-pen-total">${total.toFixed(1)}</span>
            <span class="ap-pen-flags">${flags.map(f => apChip(f)).join('')}</span>
          </div>`;
      }).join('')}
    </div>

    ${(PAYLOAD.tiers.tier_5 || []).length > 0 ? `
      <div class="ap-sub-title" style="margin-top:.9rem">High-Risk Mismatches — Tier 5 Course Mismatches</div>
      <div class="ap-pen-list">
        ${(PAYLOAD.tiers.tier_5 || []).map(p => {
          const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
          return `
            <div class="ap-pen-row" style="border-color:color-mix(in srgb,var(--t5) 25%,var(--border))">
              <span class="ap-pen-idx">#${p.rank}</span>
              <span class="ap-pen-name">${fmtName(p.player_name)}</span>
              <span class="ap-pen-total">VTS ${p.vts_final}</span>
              <span class="ap-pen-flags">${flags.map(f => apChip(f)).join('')}${debutChip(p)}</span>
            </div>`;
        }).join('')}
      </div>
    ` : ''}
  `;
}

/* ════════════════════════════════════════════
   RENDER: TIER ARCHITECTURE
════════════════════════════════════════════ */
function renderTierSections() {
  const tiers  = PAYLOAD.tiers;
  const labels = PAYLOAD.tier_labels;
  const dist   = PAYLOAD.model_summary.tier_distribution;

  /* Distribution chips */
  const distEl = document.querySelector('.tier-dist-row');
  if (distEl) {
    distEl.innerHTML = [1,2,3,4,5].map(t =>
      `<span class="td-chip t${t}">Tier ${t} · ${labels[t]} &nbsp;<b>${dist[t]}</b></span>`
    ).join('');
  }

  const tierDescs = {
    1: 'Elite fit + skill — primary win candidates',
    2: 'High contention probability, weekend scoring upside',
    3: 'Top-10 ceiling with variable floor',
    4: 'Cut-line range, limited upside',
    5: 'Course mismatches — significant scoring drag expected',
  };

  const container = document.querySelector('.tier-containers');
  container.innerHTML = [1,2,3,4,5].map(t => {
    const players = tiers[`tier_${t}`] || [];
    return `
      <details class="tier-details" ${t <= 2 ? 'open' : ''}>
        <summary>
          <span class="tier-arrow">▶</span>
          <span class="tier-summary-badge t${t}">Tier ${t}</span>
          <span class="tier-summary-label">${labels[t]}</span>
          <span class="tier-summary-count">${players.length} players</span>
          <span class="tier-summary-desc">${tierDescs[t]}</span>
        </summary>
        <div class="tier-cards-grid">
          ${players.map(p => playerCard(p)).join('')}
        </div>
      </details>`;
  }).join('');

  /* Wire card clicks → modal */
  document.querySelectorAll('.player-card').forEach(card => {
    card.addEventListener('click', e => {
      /* don't fire on the trace details toggle */
      if (e.target.closest('details.pc-trace')) return;
      const pname = card.dataset.player;
      const player = allPlayers.find(p => p.player_name === pname);
      if (player) openModal(player);
    });
  });
}

function playerCard(p) {
  const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  const chipsHTML = [
    ...flags.map(f => apChip(f)),
    debutChip(p),
  ].filter(Boolean).join('');

  return `
    <div class="player-card" data-player="${p.player_name}">
      <div class="pc-header">
        <span class="pc-rank">#${p.rank}</span>
        <span class="pc-name">${fmtName(p.player_name)}</span>
        <span class="pc-vts">${p.vts_final}</span>
      </div>
      <div class="pc-driver">${p.primary_driver}</div>
      <div class="pc-trait">${p.trait_summary}</div>
      <div class="pc-stats">
        <span class="pc-stat">Win <b>${p.win_pct.toFixed(2)}%</b></span>
        <span class="pc-stat">T10 <b>${p.top10_pct.toFixed(0)}%</b></span>
        <span class="pc-stat">Cut <b>${p.make_cut_pct.toFixed(0)}%</b></span>
        ${p.vh_rounds > 0 ? `<span class="pc-stat">CH <b>${p.vh_rounds}r</b></span>` : ''}
        <span class="pc-stat">SG <b>${p.neutral_sg >= 0 ? '+' : ''}${Number(p.neutral_sg).toFixed(2)}</b></span>
      </div>
      ${chipsHTML ? `<div class="pc-flags">${chipsHTML}</div>` : ''}
      <div class="pc-reason">${p.tier_reason}</div>
      ${p.trace_notes ? `
        <details class="pc-trace">
          <summary>▸ Trace notes</summary>
          <div class="trace-body">${p.trace_notes}</div>
        </details>` : ''}
    </div>`;
}

/* ════════════════════════════════════════════
   RENDER: AUDIT FOOTER
════════════════════════════════════════════ */
function renderAuditFooter() {
  const ms   = PAYLOAD.model_summary;
  const meta = PAYLOAD.metadata || {};
  const ev   = PAYLOAD.event;

  const winSum = allPlayers.reduce((s, p) => s + (p.win_pct || 0), 0);
  const winOk  = Math.abs(winSum - 100) < 0.5;

  const distOk = [1,2,3,4,5].every(t =>
    (PAYLOAD.tiers[`tier_${t}`] || []).length === (ms.tier_distribution[t] || 0)
  );

  document.querySelector('.audit-inner').innerHTML = `
    <span class="audit-item">Scoring spec: <b>v${ms.scoring_spec_version}</b></span>
    <span class="audit-item">Venue file: <b>${ms.venue_file_version}</b></span>
    <span class="audit-item">Iteration: <b>${ms.event_iteration}</b></span>
    <span class="audit-item">Field locked: <b>${ev.field_locked ? 'YES' : 'NO'}</b></span>
    <span class="audit-item">Win-pct sum: <b class="${winOk ? 'audit-ok' : 'audit-warn'}">${winSum.toFixed(2)}% ${winOk ? '✓' : '⚠'}</b></span>
    <span class="audit-item">Tier gate: <b class="${distOk ? 'audit-ok' : 'audit-warn'}">${distOk ? 'CLEAN ✓' : 'MISMATCH ⚠'}</b></span>
    <span class="audit-item">Engine: <b>${meta.engine_version || ms.scoring_spec_version}</b></span>
    <span class="audit-item">Built: <b>${(meta.generated_at || '').slice(0, 10)}</b></span>
    <span class="audit-item" style="margin-left:auto;font-size:.63rem;color:color-mix(in srgb,var(--muted) 50%,transparent)">PGA VenueDNA · John Deere Classic 2026</span>
  `;
}

/* ════════════════════════════════════════════
   TABLE LOGIC
════════════════════════════════════════════ */
function getFiltered() {
  let players = allPlayers;

  if (activeTier !== 'all') {
    players = players.filter(p => p.tier === +activeTier);
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    players = players.filter(p =>
      p.player_name.toLowerCase().includes(q) ||
      fmtName(p.player_name).toLowerCase().includes(q)
    );
  }

  if (filterFlagged) {
    players = players.filter(p => p.flag_count > 0);
  }

  if (filterDebut) {
    players = players.filter(p => p.debut_flag);
  }

  /* Sort */
  players = [...players].sort((a, b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (va === null || va === undefined) va = sortDir === 1 ? Infinity : -Infinity;
    if (vb === null || vb === undefined) vb = sortDir === 1 ? Infinity : -Infinity;
    if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
    return sortDir * (va < vb ? -1 : va > vb ? 1 : 0);
  });

  return players;
}

function applyAndRender() {
  const players   = getFiltered();
  const tbody     = document.getElementById('player-tbody');
  const emptyEl   = document.getElementById('empty-state');
  const resultBar = document.getElementById('table-result-bar');

  /* Update tier tab counts */
  const tierCounts = {};
  allPlayers.forEach(p => { tierCounts[p.tier] = (tierCounts[p.tier] || 0) + 1; });
  document.querySelectorAll('.tier-tab').forEach(tab => {
    const tc = tab.querySelector('.tc');
    if (!tc) return;
    const tier = tab.dataset.tier;
    tc.textContent = tier === 'all' ? allPlayers.length : (tierCounts[+tier] || 0);
  });

  if (players.length === 0) {
    tbody.innerHTML = '';
    emptyEl.style.display = 'block';
    resultBar.textContent = 'No players match current filters.';
    return;
  }

  emptyEl.style.display = 'none';
  resultBar.textContent = `${players.length} of ${allPlayers.length} players`;

  let rows    = '';
  let lastTier = null;

  for (const p of players) {
    /* Tier section divider when showing all */
    if (activeTier === 'all' && p.tier !== lastTier) {
      lastTier = p.tier;
      const lbl = PAYLOAD.tier_labels[p.tier];
      rows += `<tr class="tier-section-row">
        <td colspan="13">${tierBadge(p.tier)} ${lbl} · ${PAYLOAD.model_summary.tier_distribution[p.tier]} players</td>
      </tr>`;
    }

    const flags   = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
    const vhdDisp = p.vh_rounds > 0
      ? `${(p.vh_delta ?? 0).toFixed(1)} (${p.vh_rounds}r)`
      : '<span style="color:var(--muted)">—</span>';

    rows += `<tr data-player="${p.player_name}">
      <td class="rank-cell">${p.rank}</td>
      <td>
        <div class="pname">${fmtName(p.player_name)}</div>
        <div class="pdriver">${p.primary_driver}</div>
      </td>
      <td>${tierBadge(p.tier, `T${p.tier}`)}</td>
      <td class="vts-cell">${vtsBar(p.vts_final)}</td>
      <td class="prob-cell">${p.win_pct.toFixed(2)}%</td>
      <td class="prob-cell">${p.top10_pct.toFixed(0)}%</td>
      <td class="prob-cell">${p.make_cut_pct.toFixed(0)}%</td>
      <td>${sgDisplay(p.neutral_sg)}</td>
      <td>${vfdDisplay(p.vfd)}</td>
      <td style="font-size:.72rem;color:var(--muted)">${vhdDisp}</td>
      <td style="font-size:.68rem;color:var(--muted)">${p.primary_driver}</td>
      <td>${flags.map(f => apChip(f)).join('')}</td>
      <td>${debutChip(p)}</td>
    </tr>`;
  }

  tbody.innerHTML = rows;

  /* Row click → modal */
  tbody.querySelectorAll('tr[data-player]').forEach(row => {
    row.addEventListener('click', () => {
      const player = allPlayers.find(p => p.player_name === row.dataset.player);
      if (player) openModal(player);
    });
  });

  /* Sort indicators */
  document.querySelectorAll('.th-sort').forEach(th => {
    th.classList.remove('sorted');
    const ind = th.querySelector('.sort-ind');
    if (ind) ind.textContent = '↕';
  });
  const activeTh = document.querySelector(`.th-sort[data-col="${sortCol}"]`);
  if (activeTh) {
    activeTh.classList.add('sorted');
    const ind = activeTh.querySelector('.sort-ind');
    if (ind) ind.textContent = sortDir === 1 ? '↑' : '↓';
  }
}

/* ════════════════════════════════════════════
   MODAL
════════════════════════════════════════════ */
function openModal(p) {
  const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];

  document.getElementById('modal-player-name').textContent = fmtName(p.player_name);
  document.getElementById('modal-player-sub').innerHTML =
    `${tierBadge(p.tier, PAYLOAD.tier_labels[p.tier])} · #${p.rank} · ${p.primary_driver}`;

  document.getElementById('modal-body').innerHTML = `
    <div class="modal-section">
      <div class="modal-section-title">Probabilities</div>
      ${kv('VTS', p.vts_final)}
      ${kv('Win %', p.win_pct.toFixed(2) + '%')}
      ${kv('Top 5 %', p.top5_pct.toFixed(0) + '%')}
      ${kv('Top 10 %', p.top10_pct.toFixed(0) + '%')}
      ${kv('Top 20 %', p.top20_pct.toFixed(0) + '%')}
      ${kv('Make Cut %', p.make_cut_pct.toFixed(0) + '%')}
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Venue Fit</div>
      ${kv('Neutral SG', `${p.neutral_sg >= 0 ? '+' : ''}${Number(p.neutral_sg).toFixed(3)}`)}
      ${kv('Neutral Skill Index', Number(p.neutral_skill_index).toFixed(1))}
      ${kv('VFD (Venue Fit Delta)', `${p.vfd > 0 ? '+' : ''}${Number(p.vfd).toFixed(1)}`)}
      ${kv('Course Hist. Rounds', p.vh_rounds)}
      ${p.vh_rounds > 0 ? kv('VH SG', Number(p.vh_sg).toFixed(3)) + kv('VH Delta', Number(p.vh_delta).toFixed(1)) : ''}
      ${kv('Primary Driver', p.primary_driver)}
      ${kv('Trait Summary', p.trait_summary)}
    </div>
    ${flags.length ? `
      <div class="modal-section">
        <div class="modal-section-title">Anti-Pattern Flags</div>
        <div style="display:flex;gap:.28rem;flex-wrap:wrap;margin-bottom:.4rem">${flags.map(f => apChip(f)).join('')}</div>
        ${flags.map(f => {
          const m = AP_META[f];
          return m ? `<div class="modal-kv"><span class="mk">${m.label}</span><span class="mv" style="font-size:.68rem;color:var(--muted);text-align:left">${m.desc}</span></div>` : '';
        }).join('')}
      </div>` : ''}
    ${p.debut_flag ? `
      <div class="modal-section">
        <div class="modal-section-title">Debut</div>
        <div style="margin-bottom:.3rem">${debutChip(p)}</div>
        ${kv('Debut Class', p.debut_class)}
      </div>` : ''}
    <div class="modal-section">
      <div class="modal-section-title">Tier Rationale</div>
      <p style="font-size:.76rem;color:var(--muted);line-height:1.5">${p.tier_reason}</p>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Trace Notes</div>
      <div class="modal-trace">${p.trace_notes || '—'}</div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Tee Sheet</div>
      ${kv('R1 Tee Time', p.r1_tee_time || 'TBD')}
      ${kv('R1 Wave', p.r1_wave || 'TBD')}
    </div>
  `;

  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

function wireModal() {
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });
}

/* ════════════════════════════════════════════
   INTERACTION WIRING
════════════════════════════════════════════ */
function wireSearch() {
  const input    = document.getElementById('search-input');
  const clearBtn = document.getElementById('search-clear');

  input.addEventListener('input', () => {
    searchQuery = input.value.trim();
    clearBtn.style.display = searchQuery ? 'block' : 'none';
    applyAndRender();
  });
  clearBtn.addEventListener('click', () => {
    input.value  = '';
    searchQuery  = '';
    clearBtn.style.display = 'none';
    applyAndRender();
  });
}

function wireTierTabs() {
  document.querySelectorAll('.tier-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeTier = tab.dataset.tier;
      applyAndRender();
    });
  });
}

function wireSort() {
  const defaults = { rank: 1, tier: 1, vts_final: -1, win_pct: -1, top10_pct: -1, make_cut_pct: -1, neutral_sg: -1, flag_count: -1 };
  document.querySelectorAll('.th-sort').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (sortCol === col) {
        sortDir = -sortDir;
      } else {
        sortCol = col;
        sortDir = defaults[col] ?? -1;
      }
      applyAndRender();
    });
  });
}

function wireToggles() {
  const btnFlags = document.getElementById('btn-antipattern');
  const btnDebut = document.getElementById('btn-debut');
  const btnReset = document.getElementById('btn-reset');
  const btnEmptyReset = document.getElementById('empty-reset');

  btnFlags.addEventListener('click', () => {
    filterFlagged = !filterFlagged;
    btnFlags.classList.toggle('active', filterFlagged);
    applyAndRender();
  });

  btnDebut.addEventListener('click', () => {
    filterDebut = !filterDebut;
    btnDebut.classList.toggle('active', filterDebut);
    applyAndRender();
  });

  function doReset() {
    searchQuery   = '';
    activeTier    = 'all';
    sortCol       = 'rank';
    sortDir       = 1;
    filterFlagged = false;
    filterDebut   = false;
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.tier-tab[data-tier="all"]').classList.add('active');
    btnFlags.classList.remove('active');
    btnDebut.classList.remove('active');
    applyAndRender();
  }

  btnReset.addEventListener('click', doReset);
  if (btnEmptyReset) btnEmptyReset.addEventListener('click', doReset);
}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);
