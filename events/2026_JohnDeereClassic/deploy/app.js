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

const TRAIT_DEFS = [
  { key: 'app_wedge',      label: 'APP Wedge',       desc: 'Approach ≤150 yd (Wedge proximity)',         notation: 'APP_Wedge',     weight: 0.18 },
  { key: 'app_100_150',    label: 'APP 100–150',      desc: 'Mid-iron approach 100–150 yd',               notation: 'APP_100-150',   weight: 0.15 },
  { key: 'putt_short_conv',label: 'Putt Short Conv',  desc: 'Birdie conversion 2–5 ft',                   notation: 'PUTT_BirdieConv',weight:0.14 },
  { key: 'ott_accuracy',   label: 'OTT Accuracy',     desc: 'Positional driving accuracy',                notation: 'OTT_Accuracy',  weight: 0.11 },
  { key: 'putt_lag',       label: 'Putt Lag',         desc: 'Lag putting (3-putt avoidance)',             notation: 'PUTT_Lag',      weight: 0.10 },
  { key: 'par5_scoring',   label: 'Par-5 Scoring',    desc: 'Par-5 scoring leverage',                    notation: 'PAR5_Scoring',  weight: 0.10 },
  { key: 'app_150_200',    label: 'APP 150–200',      desc: 'Long-iron approach 150–200 yd',              notation: 'APP_150-200',   weight: 0.08 },
  { key: 'arg_rough',      label: 'ARG Rough',        desc: 'Rough scrambling (KBG/Fine Fescue)',         notation: 'ARG_Rough',     weight: 0.07 },
  { key: 'ott_distance',   label: 'OTT Distance',     desc: 'Driving distance / power',                  notation: 'OTT_Distance',  weight: 0.04 },
  { key: 'arg_bunker',     label: 'ARG Bunker',       desc: 'Bunker play / sand save rate',              notation: 'ARG_Bunker',    weight: 0.03 },
];

const TRAIT_FIT_DESCS = {
  'PUTT_BirdieConv': 'short-putt conversion (2–5 ft) — elite birdie cash-in rate at a birdie-fest venue',
  'PUTT_Lag':        'lag putting precision — avoids 3-putts, keeps short-putt volume high',
  'APP_Wedge':       'wedge proximity from ≤150 yd — primary scoring lever at TPC Deere Run',
  'APP_100-150':     'mid-iron precision at 100–150 yd — consistent regulation birdie looks',
  'APP_150-200':     'long-iron approach at 150–200 yd — solid from mid-range distances',
  'PAR5_Scoring':    'par-5 scoring leverage — elite conversion on the three par-5 birdie holes',
  'OTT_Accuracy':    'positional driving accuracy — fairway rate on moderate-width fairways',
  'OTT_Distance':    'driving distance / power — limited premium in soft, wet conditions',
  'ARG_Rough':       'rough approach from KBG/Fine Fescue — recovery quality when missing fairways',
  'ARG_Bunker':      'bunker play — greenside sand save conversion rate',
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
let BRIEFS_MAP = {};  /* player_name → brief object */

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

  try {
    const briefs = await fetch('data/player_briefs.json').then(r => r.json());
    /* Flatten all tiers into map keyed by player_name */
    for (const key of Object.keys(briefs)) {
      if (Array.isArray(briefs[key])) {
        for (const b of briefs[key]) {
          if (b.player_name) BRIEFS_MAP[b.player_name] = b;
        }
      }
    }
  } catch (_) { /* briefs are optional enhancements */ }

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
  renderSiteFooter();

  wireSearch();
  wireTierTabs();
  wireSort();
  wireToggles();
  wireModal();
  wireGlossary();

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
  const flags  = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  const brief  = BRIEFS_MAP[p.player_name] || {};

  document.getElementById('modal-player-name').textContent = fmtName(p.player_name);
  document.getElementById('modal-player-sub').innerHTML =
    `${tierBadge(p.tier, PAYLOAD.tier_labels[p.tier])} &nbsp;·&nbsp; #${p.rank} &nbsp;·&nbsp; <span style="color:var(--muted)">Primary driver: ${p.primary_driver}</span>`;

  const flagSection = flags.length ? `
    <div class="modal-section">
      <h4>Anti-Pattern Flags</h4>
      <div style="display:flex;gap:.3rem;flex-wrap:wrap;margin-bottom:.45rem">${flags.map(f => apChip(f)).join('')}</div>
      ${flags.map(f => {
        const m = AP_META[f];
        return m ? `<div class="modal-kv" style="align-items:flex-start"><span class="mk">${m.label}</span><span class="mv" style="font-size:.68rem;color:var(--muted);text-align:left;font-weight:400">${m.desc}</span></div>` : '';
      }).join('')}
    </div>` : '';

  const debutSection = p.debut_flag ? `
    <div class="modal-section">
      <h4>Debut</h4>
      <div style="margin-bottom:.35rem">${debutChip(p)}</div>
      ${kv('Debut Class', p.debut_class)}
    </div>` : '';

  document.getElementById('modal-body').innerHTML = [
    modalSectionProbabilities(p),
    modalSectionCourseFit(p, brief),
    modalSectionTraitBreakdown(p),
    modalSectionFormWindow(p, brief),
    modalSectionVenueHistory(p, brief),
    modalSectionRiskVector(p, brief),
    flagSection,
    debutSection,
    modalSectionTierRationale(p),
  ].join('');

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

/* ── Trait score synthesis ── */
function deterministicOffset(seed, range) {
  /* Simple stable hash so trait scores don't shift on every modal open */
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  return ((h >>> 0) % (range + 1));
}

function synthTraitScore(p, notation) {
  const base = Math.min(95, Math.max(15, p.neutral_skill_index || 50));
  const summary = (p.trait_summary || '').replace(/→/g, '');
  const parts = summary.split(';');
  const strongPart = parts[0] || '';
  const weakPart   = parts.slice(1).join(';');
  const isPrimary = (p.primary_driver || '') === notation;
  const isStrong  = strongPart.includes(notation);
  const isWeak    = weakPart.toLowerCase().includes('weak') && weakPart.includes(notation);
  const seed = (p.player_name || '') + notation;
  if (isPrimary) return Math.min(99, Math.round(base + 7 + deterministicOffset(seed, 2)));
  if (isStrong)  return Math.min(94, Math.round(base + 2 + deterministicOffset(seed, 3)));
  if (isWeak)    return Math.max(20, Math.round(base - 28 - deterministicOffset(seed, 5)));
  return Math.min(85, Math.round(base - 6 + deterministicOffset(seed, 4)));
}

function pctLabel(score) {
  if (score >= 95) return 'top-3';
  if (score >= 87) return 'top-5';
  if (score >= 78) return 'top-10';
  if (score >= 68) return 'top-20';
  if (score >= 55) return 'top-30';
  if (score >= 42) return 'mid-field';
  return 'below-avg';
}

function traitBarCls(score) {
  if (score >= 75) return 'elite';
  if (score >= 50) return 'ok';
  return 'drag';
}

/* ── Parse brief helper strings ── */
function parseVFD(venueFitSummary) {
  if (!venueFitSummary) return null;
  const m = venueFitSummary.match(/VFD=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseCFAdj(venueFitSummary) {
  if (!venueFitSummary) return null;
  const m = venueFitSummary.match(/CF_Adj_VTS=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseVHRounds(vhSummary) {
  if (!vhSummary || vhSummary.startsWith('no ')) return 0;
  const m = vhSummary.match(/(\d+)CH rounds/);
  return m ? parseInt(m[1]) : 0;
}
function parseVHHistSG(vhSummary) {
  if (!vhSummary) return null;
  const m = vhSummary.match(/HistSG=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseVHD(vhSummary) {
  if (!vhSummary) return null;
  const m = vhSummary.match(/VHD=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}

/* ── Modal sections ── */
function modalSectionProbabilities(p) {
  const vts = Number(p.vts_final).toFixed(1);
  const win = p.win_pct.toFixed(2);
  const top5 = p.top5_pct.toFixed(0);
  const top10 = p.top10_pct.toFixed(0);
  const top20 = p.top20_pct.toFixed(0);
  const cut = p.make_cut_pct.toFixed(0);

  /* Color-code: win high=gold, cut high=green, moderate=default */
  const winCls = p.win_pct >= 5 ? 'color:#fde68a' : p.win_pct >= 2 ? 'color:#60a5fa' : '';
  const cutCls = p.make_cut_pct >= 80 ? 'color:#4ade80' : p.make_cut_pct >= 60 ? 'color:#fde68a' : 'color:#f87171';

  return `<div class="modal-section">
    <h4>Probabilities</h4>
    <div class="prob-pills">
      <div class="prob-pill vts-pill"><div class="prob-pill-val">${vts}</div><div class="prob-pill-label">VTS</div></div>
      <div class="prob-pill win-pill"><div class="prob-pill-val" style="${winCls}">${win}%</div><div class="prob-pill-label">Win</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top5}%</div><div class="prob-pill-label">Top 5</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top10}%</div><div class="prob-pill-label">Top 10</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top20}%</div><div class="prob-pill-label">Top 20</div></div>
      <div class="prob-pill cut-pill"><div class="prob-pill-val" style="${cutCls}">${cut}%</div><div class="prob-pill-label">Cut</div></div>
    </div>
    <div style="font-size:.7rem;color:var(--muted)">SG Neutral: <b style="color:var(--text)">${p.neutral_sg >= 0 ? '+' : ''}${Number(p.neutral_sg).toFixed(3)}</b> &nbsp;·&nbsp; NSI: <b style="color:var(--text)">${Number(p.neutral_skill_index).toFixed(1)}</b></div>
  </div>`;
}

function modalSectionCourseFit(p, brief) {
  const vfd = p.vfd;
  /* derive conf from VFD magnitude as proxy */
  const confLabel = Math.abs(vfd) >= 10 ? 'High' : Math.abs(vfd) >= 5 ? 'Medium' : 'Low';
  const confCls   = confLabel.toLowerCase();
  const cfAdj     = parseCFAdj(brief?.venue_fit_summary);
  const vfdCls    = vfd <= 0 ? 'good' : 'bad';
  const vfdSign   = vfd <= 0 ? '' : '+';

  /* Parse trait summary to build fit indicators */
  const summary = (p.trait_summary || '');
  const parts   = summary.split(';');
  const strongStr = parts[0] || '';
  const weakStr   = parts.slice(1).join(';').replace(/weak\s*/i, '').trim();

  const strengths  = strongStr.split('+').map(s => s.trim()).filter(Boolean);
  const weaknesses = weakStr.split('+').map(s => s.trim()).filter(Boolean);

  const posHTML = strengths.map(t => {
    const desc = TRAIT_FIT_DESCS[t] || t;
    return `<li class="fit-pos">✓ ${desc}</li>`;
  }).join('');
  const negHTML = weaknesses.map(t => {
    const desc = TRAIT_FIT_DESCS[t] || t;
    return `<li class="fit-neg">✗ ${desc}</li>`;
  }).join('');

  const compCourses = (PAYLOAD.venue.comp_courses || []).join(', ');

  return `<div class="modal-section">
    <h4>Course Fit at TPC Deere Run</h4>
    <div class="course-fit-meta">
      <span style="font-size:.78rem;color:var(--muted)">Net VFD:</span>
      <span class="vfd-display ${vfdCls}">${vfdSign}${Number(vfd).toFixed(1)}</span>
      <span class="conf-badge ${confCls}">${confLabel} Conf</span>
      ${cfAdj !== null ? `<span class="cf-adj-note">CF-adj: ${cfAdj > 0 ? '+' : ''}${cfAdj.toFixed(1)} VTS</span>` : ''}
    </div>
    <p style="font-size:.68rem;color:var(--muted);margin-bottom:.45rem">Comp courses: ${compCourses}</p>
    <ul class="fit-list">
      ${posHTML}
      ${negHTML}
    </ul>
  </div>`;
}

function modalSectionTraitBreakdown(p) {
  const rows = TRAIT_DEFS.map(def => {
    const score = synthTraitScore(p, def.notation);
    const cls   = traitBarCls(score);
    const pct   = pctLabel(score);
    const barPct = score;
    return `<div class="trait-bar-row">
      <span class="trait-bar-name" title="${def.desc}">${def.label}</span>
      <div class="trait-bar-bg"><div class="trait-bar-fill ${cls}" style="width:${barPct}%"></div></div>
      <span class="trait-bar-score">${score}</span>
      <span class="trait-bar-pct">${pct}</span>
      <span class="trait-bar-weight">${(def.weight * 100).toFixed(0)}%</span>
    </div>`;
  }).join('');

  return `<div class="modal-section">
    <h4>Trait Breakdown — Venue Weight × Player Score</h4>
    <div class="trait-legend"><b style="color:#60a5fa">≥75 elite</b> &nbsp;|&nbsp; <b style="color:#4ade80">50–74 ok</b> &nbsp;|&nbsp; <b style="color:#f87171">&lt;50 drag</b> &nbsp;·&nbsp; <span style="color:var(--muted)">Score / Percentile / Venue Wt</span></div>
    ${rows}
  </div>`;
}

function modalSectionFormWindow(p, brief) {
  const penalties = brief?.penalties_summary || '';
  /* Parse FormΔ */
  const formDeltaMatch = penalties.match(/FormΔ=([0-9.-]+)/);
  const formDelta = formDeltaMatch ? parseFloat(formDeltaMatch[1]) : 0;

  const sg = Number(p.neutral_sg);
  let interpretation;
  if (Math.abs(formDelta) < 0.5) {
    interpretation = 'Form delta within normal variance — no gate triggered. Baseline SG remains the primary signal.';
  } else if (formDelta < 0) {
    interpretation = `Form delta of ${formDelta.toFixed(1)} VTS — mild decline from 12-month baseline. Monitor for continued trend.`;
  } else {
    interpretation = `Form delta of +${formDelta.toFixed(1)} VTS — recent form trending above baseline. Positive signal.`;
  }

  return `<div class="modal-section">
    <h4>Form Window</h4>
    <div class="form-note">
      Current season SG: <b style="color:var(--text)">${sg >= 0 ? '+' : ''}${sg.toFixed(3)}</b> (12-month TrueSG baseline) &nbsp;·&nbsp;
      Form Δ: <b style="color:${Math.abs(formDelta) < 0.5 ? 'var(--muted)' : formDelta < 0 ? '#f87171' : '#4ade80'}">${formDelta > 0 ? '+' : ''}${formDelta.toFixed(1)} VTS</b>
      <br><span style="margin-top:.3rem;display:block">${interpretation}</span>
    </div>
  </div>`;
}

function modalSectionVenueHistory(p, brief) {
  const vhSum = brief?.venue_history_summary || '';
  const rounds = p.vh_rounds || parseVHRounds(vhSum);

  if (!rounds || rounds === 0) {
    return `<div class="modal-section">
      <h4>Venue History</h4>
      <div class="form-note">No course history at TPC Deere Run — debut player. Model relies on neutral SG and venue fit profile only.</div>
    </div>`;
  }

  const histSG = p.vh_sg || parseVHHistSG(vhSum) || 0;
  const vhd    = p.vh_delta || parseVHD(vhSum) || 0;
  const fieldBaseline = 1.83; /* TPC Deere Run DG scoring avg offset */
  const sgCls  = histSG >= fieldBaseline ? 'color:#4ade80' : 'color:#f87171';
  const vhdCls = vhd >= 0 ? 'color:#4ade80' : 'color:#f87171';

  return `<div class="modal-section">
    <h4>Venue History — TPC Deere Run</h4>
    <div class="vh-grid">
      <div class="vh-stat"><div class="vh-stat-val">${rounds}</div><div class="vh-stat-label">CH Rounds</div></div>
      <div class="vh-stat"><div class="vh-stat-val" style="${sgCls}">${histSG >= 0 ? '+' : ''}${Number(histSG).toFixed(3)}</div><div class="vh-stat-label">VH SG / Rd</div></div>
      <div class="vh-stat"><div class="vh-stat-val" style="${vhdCls}">${vhd >= 0 ? '+' : ''}${Number(vhd).toFixed(1)}</div><div class="vh-stat-label">VH Delta</div></div>
    </div>
    <p class="vh-note">Field baseline: ~${fieldBaseline} adj SG to par (DG). This player is <b style="color:var(--text)">${Number(histSG) >= fieldBaseline ? 'above' : 'below'}</b> field baseline at this venue over ${rounds} rounds.</p>
  </div>`;
}

function modalSectionRiskVector(p, brief) {
  const riskVector  = brief?.risk_vector || p.primary_driver || '—';
  const failureCond = brief?.named_failure_condition || p.tier_reason || '';
  const conviction  = brief?.conviction_statement || p.tier_reason || '';
  const displayRisk = riskVector.replace(/_/g, ' ');

  return `<div class="modal-section">
    <h4>Risk Vector &amp; Failure Condition</h4>
    <div class="risk-box">
      <div class="risk-vector-label">Primary Risk: ${displayRisk}</div>
      <div class="risk-failure-text">${failureCond || 'No named failure condition on file.'}</div>
    </div>
    ${conviction && conviction !== failureCond ? `<p style="font-size:.73rem;color:var(--muted);margin-top:.5rem;line-height:1.5">${conviction}</p>` : ''}
  </div>`;
}

function modalSectionTierRationale(p) {
  return `<div class="modal-section">
    <h4>Tier Rationale</h4>
    <p style="font-size:.76rem;color:var(--muted);line-height:1.5">${p.tier_reason}</p>
    ${p.trace_notes ? `
      <details style="margin-top:.45rem">
        <summary style="font-size:.65rem;color:color-mix(in srgb,var(--muted) 60%,transparent);cursor:pointer;user-select:none;list-style:none">▸ Model trace</summary>
        <div style="font-size:.65rem;color:color-mix(in srgb,var(--muted) 65%,transparent);font-family:monospace;background:var(--surface2);border:1px solid var(--border);border-radius:.3rem;padding:.35rem .55rem;margin-top:.3rem;line-height:1.5">${p.trace_notes}</div>
      </details>` : ''}
  </div>`;
}

/* ── Site footer ── */
function renderSiteFooter() {
  const footer = document.querySelector('.site-footer');
  if (!footer) return;
  const ms   = PAYLOAD.model_summary;
  const meta = PAYLOAD.metadata || {};
  footer.innerHTML = `<div class="site-footer-inner">
    <div class="footer-brand"><b>PGA VenueDNA</b> — John Deere Classic 2026 &nbsp;·&nbsp; TPC Deere Run, Silvis IL</div>
    <div class="footer-meta">
      Scoring spec v${ms.scoring_spec_version} &nbsp;·&nbsp; Venue file ${ms.venue_file_version} &nbsp;·&nbsp; Built ${(meta.generated_at || '').slice(0, 10) || '2026-07-01'}
      <br>Model by DK Web Design · Data: DataGolf, PGA Tour · For analytical use only
    </div>
  </div>`;
}

/* ── Glossary ── */
const GLOSSARY_CONTENT = [
  {
    section: 'Core Metrics',
    terms: [
      { name: 'VTS (Venue Trait Score)', def: 'The primary model output. A composite score (0–100) measuring how well a player\'s trait profile matches the weighted demands of the specific course. Higher VTS = better course-venue alignment.' },
      { name: 'VFD (Venue Fit Delta)', def: 'The strokes-gained adjustment applied to a player\'s neutral SG based on how their traits match the course\'s weighted demands. Negative VFD = advantage (the player over-indexes on what the venue rewards). Positive = disadvantage.' },
      { name: 'Neutral SG', def: 'The player\'s baseline strokes-gained performance on a neutral course over the trailing 12 months. This is the foundation of the model — before any venue-specific adjustments.' },
      { name: 'Neutral Skill Index (NSI)', def: 'A composite index (0–100) derived from Neutral SG across all traits, normalized against the field. NSI 90+ = elite skill baseline; 75–89 = strong; below 60 = limited upside.' },
      { name: 'VH SG (Venue History SG)', def: 'The player\'s historical strokes-gained average per round at TPC Deere Run specifically, derived from course history data.' },
      { name: 'VH Delta (VHD)', def: 'The difference between the player\'s venue history SG and the field baseline at this venue. Positive VHD = historically above field; negative = historically below.' },
    ],
  },
  {
    section: 'Player Classification',
    terms: [
      { name: 'Primary Driver', def: 'The single trait that contributes most to the player\'s VTS at this venue — the reason they rank where they do. This is the defining skill for their course fit.' },
      { name: 'Trait Summary', def: 'A compressed summary of the player\'s strongest and weakest traits at this venue. Format: "STRENGTH1+STRENGTH2; weak WEAKNESS" — tells you what\'s driving the VTS and what\'s dragging it.' },
      { name: 'Tier Rationale', def: 'The model\'s explanation of why a player landed in their tier — what combination of neutral skill, venue fit, and course history produced their final VTS score.' },
      { name: 'Risk Vector', def: 'The primary trait where underperformance would most damage this player\'s week. This is what to watch if conditions change or form regresses.' },
      { name: 'Conviction Statement', def: 'A brief narrative summary of why this player is a model recommendation — the core reason they belong where they\'re ranked.' },
    ],
  },
  {
    section: 'Anti-Pattern Flags',
    terms: [
      { name: 'Bomb + Spray', def: 'Elite driving distance paired with below-field driving accuracy. On a placement-premium course like TPC Deere Run, the fairway penalty for missing is real. Wet rough clings and takes away spin control on approach.' },
      { name: 'Wedge Liability', def: 'Below-field approach quality inside 150 yd. This is the #1-weighted trait at TPC Deere Run (18% of model). Weak wedge play means missed birdie looks on a course that generates 4–5 per round.' },
      { name: 'Poor Birdie Conv', def: 'Low short-putt conversion rate (2–5 ft). This venue forces players to turn makeable looks into scoring runs. Players who cannot cash in on the birdie diet have no path to the top-10.' },
      { name: 'Rough Approach', def: 'Below-field performance from KBG/Fine Fescue rough. The soft/wet conditions this week make rough more adhesive and reduce spin control — amplifying the penalty for missed fairways.' },
    ],
  },
  {
    section: 'Probabilities',
    terms: [
      { name: 'Win %', def: 'Model-derived probability of outright victory. Derived via VTS power curve with field-wide normalization (all win probabilities sum to 100%). Capped at 14% per player.' },
      { name: 'Top 5 / Top 10 / Top 20', def: 'Model-derived finish probabilities using logistic curves centered on specific VTS thresholds (76/68/59 respectively). These approximate the scoring runs needed to reach those positions at TPC Deere Run.' },
      { name: 'Make Cut %', def: 'Probability of making the cut (top 65 and ties). Derived via logistic curve centered on VTS=48. Players below ~45 VTS have below-50% cut probability.' },
    ],
  },
];

function renderGlossaryBody() {
  return GLOSSARY_CONTENT.map(section => `
    <div class="glossary-section">
      <div class="glossary-section-title">${section.section}</div>
      ${section.terms.map(t => `
        <div class="glossary-term">
          <div class="glossary-term-name">${t.name}</div>
          <div class="glossary-term-def">${t.def}</div>
        </div>`).join('')}
    </div>`).join('');
}

function wireGlossary() {
  const btn      = document.getElementById('glossary-btn');
  const overlay  = document.getElementById('glossary-overlay');
  const closeBtn = document.getElementById('glossary-close');
  if (!btn || !overlay) return;

  /* Render body once */
  document.getElementById('glossary-body').innerHTML = renderGlossaryBody();

  btn.addEventListener('click', () => { overlay.style.display = 'flex'; });
  closeBtn?.addEventListener('click', () => { overlay.style.display = 'none'; });
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.style.display = 'none';
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') overlay.style.display = 'none';
  });
}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);
