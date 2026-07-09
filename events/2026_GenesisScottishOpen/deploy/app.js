/* PGA VenueDNA — 2026 Genesis Scottish Open — Interactive Dashboard */

/* ══════════════════════════════════════════════════════
   MODEL CONFIGURATION
══════════════════════════════════════════════════════ */
const VENUEDNA_CONFIG = {
  treatZeroAsMissing: true,
  allowImputedInFiltersDefault: false,
  confidencePenaltyMode: 'linear',
  confidencePenaltyStrength: 0.25,
  confidenceFloor: 0.75,
};

const DATA_DIR = 'data/';

/* ── Global state ── */
let allPlayers   = [];
let briefsById   = {};   // keyed by player_id
let briefsByNk   = {};   // keyed by makeNameKey result
let eventMeta    = {};

let searchQuery  = '';
let activeTier   = 'all';
let favOnly      = false;
let favorites    = new Set();
let comparePlayers = [];
let sortCol      = 'rank';
let sortDir      = 1;
let activeFilters = [];
let activePreset  = null;
let filterRuleCounter = 0;
let allowImputedInFilters = VENUEDNA_CONFIG.allowImputedInFiltersDefault;
let r1Data = null;
let r2Data = null;
let r3Data = null;
let r4Data = null;
let cumulativeData = null;
let unmatchedR4LastNames = new Set();
let unmatchedR4FullNames = [];
let showVfdCol = true;
let weatherData = null;
let fieldTraitPercentiles = {};
let activeBadgeFilter = null;

/* ── Trait definitions — weights must match event_payload.json trait_weight_matrix ── */
const TRAIT_DEFS = [
  { key: 'app_150_200',    label: 'APP 150-200 (Long Iron)',   weight: 0.30 },
  { key: 'ott_positional', label: 'OTT / Positional Drive',    weight: 0.20 },
  { key: 'app_overall',    label: 'APP Overall',               weight: 0.15 },
  { key: 'driving_accuracy', label: 'Driving Accuracy',        weight: 0.12 },
  { key: 'sg_putt',        label: 'Putting (Links-Regressed)', weight: 0.13 },
  { key: 'sg_arg',         label: 'Short Game/ARG',             weight: 0.10 },
];

const TRAIT_KEY_MAP = Object.fromEntries(TRAIT_DEFS.map(t => [t.key, t]));

/* Extra numeric columns available in filter panel (non-trait direct fields) */
const EXTRA_FILTER_DEFS = [
  { key: 'venue_fit_score', label: 'VFS — Venue Fit Score (0–100)' },
  { key: 'vts_final',       label: 'VTS — Final Score (0–100)' },
  { key: 'win_prob',        label: 'Win % (e.g. 5 = 5%)' },
  { key: 'top5_prob',       label: 'Top 5 % (e.g. 10 = 10%)' },
  { key: 'top10_prob',      label: 'Top 10 % (e.g. 25 = 25%)' },
  { key: 'top20_prob',      label: 'Top 20 % (e.g. 45 = 45%)' },
  { key: 'make_cut_prob',   label: 'Make Cut % (0–100)' },
  { key: 'tvl_score',  label: 'TVL — SG:OTT 12m (Off-Tee Consistency)' },
  { key: 'hew_score',  label: 'HEW — Ball Striking 6m (Tee-to-Green)' },
  { key: 'brie_score', label: 'BRIE — SG:APP 24m (Approach Precision)' },
  { key: 'vfr_score',  label: 'VFR — SG:ARG 6m (Around-Green)' },
];

/* ── Tier semantic labels ── */
const TIER_LABELS = {
  1: 'Structural Winner',
  2: 'Primary Contender',
  3: 'Dark Horse',
  4: 'Fragile Path',
  5: 'Fade / Cut Risk',
};

/* ── Badge schema: type (fit | ceiling | risk), color, tooltip ── */
const BADGE_SCHEMA = {
  /* Fit / style */
  'Defending Champ':  { type: 'fit',     color: '#c4a000', tooltip: 'Defending champion at The Renaissance Club — maximum venue calibration' },
  'Course Horse':     { type: 'fit',     color: '#16a34a', tooltip: 'Positive venue history + course-adj — proven scorer at The Renaissance Club' },
  'Iron Edge':        { type: 'fit',     color: '#0891b2', tooltip: 'Top-tier venue fit score (≥64) — approach profile optimally matched to Renaissance 150-200yd zone' },
  'Form Spike':       { type: 'fit',     color: '#16a34a', tooltip: 'Current scoring pace significantly above 12-month baseline (+1.0 SG) — momentum confirmed' },
  'Elite NSI':        { type: 'fit',     color: '#4f46e5', tooltip: 'World-class neutral skill index (≥85) — elite ball-striking profile translates to any surface' },
  /* Ceiling */
  'Dark Horse':       { type: 'ceiling', color: '#7c3aed', tooltip: 'Win probability ≥2% from Tier 3 — structural ceiling underpriced by market at this venue' },
  'Ceiling Play':     { type: 'ceiling', color: '#6d28d9', tooltip: 'Elevated win ceiling score — one elite-trait spike can produce a top-5 result from this tier' },
  'Live Longshot':    { type: 'ceiling', color: '#7c3aed', tooltip: 'Win probability >2% from Tier 3+ — market may be underpricing this player' },
  /* Risk */
  'Fragile Favorite': { type: 'risk',    color: '#dc2626', tooltip: 'Top-2-tier player with anti-pattern flags — structural blowup risk present' },
  'Anti-Pattern':     { type: 'risk',    color: '#dc2626', tooltip: '2+ recurring weak-link trait flags for this venue profile — pattern of failure here' },
  'Cut Sweat':        { type: 'risk',    color: '#d97706', tooltip: 'Make-cut probability below 60% — weekend status structurally uncertain' },
  'False Safety':     { type: 'risk',    color: '#a16003', tooltip: 'High cut rate but near-zero win ceiling — a positional trap for bettors' },
  'Debut Watch':      { type: 'risk',    color: '#d97706', tooltip: 'First start at The Renaissance Club — zero venue-specific calibration data' },
  'Volatile Putter':  { type: 'risk',    color: '#b45309', tooltip: 'High putting variance — links fescue greens can amplify or collapse this trait' },
  'Form Cold':        { type: 'risk',    color: '#dc2626', tooltip: 'Scoring pace below seasonal baseline — negative momentum entering event' },
};

/* Classify a badge label → schema entry (fallback to misc) */
function classifyBadge(label) {
  return BADGE_SCHEMA[label] || { type: 'misc', color: '#475569', tooltip: label };
}

/* Derive additional badges client-side from available merged player fields.
   Called after allPlayers is fully built. Mutates p.badges in place. */
function enhanceBadges(p) {
  const badgeSet = new Set(p.badges || []);

  /* Defending Champ supersedes Course Horse */
  if ((p.venue_history_summary || '').toLowerCase().includes('defending champion')) {
    badgeSet.delete('Course Horse');
    badgeSet.add('Defending Champ');
  }

  /* Iron Edge: top-tier VFS not already covered by a venue-history badge */
  if (+p.venue_fit_score >= 64 && !badgeSet.has('Course Horse') && !badgeSet.has('Defending Champ')) {
    badgeSet.add('Iron Edge');
  }

  /* Elite NSI: world-class neutral skill */
  if (+p.neutral_skill_index >= 85) {
    badgeSet.add('Elite NSI');
  }

  /* Form Cold: below-baseline form momentum */
  if (/Form (COOL|COLD)\b/.test(p.form_summary || '') && !badgeSet.has('Form Spike')) {
    badgeSet.add('Form Cold');
  }

  /* T3+ ceiling differentiation */
  if (p.tier >= 3) {
    if (+p.win_prob >= 2.0) {
      if (!badgeSet.has('Live Longshot')) badgeSet.add('Dark Horse');
      badgeSet.delete('Ceiling Play'); /* Live Longshot / Dark Horse supersedes — one ceiling badge only */
    } else if (+p.win_ceiling_score >= 75 && !badgeSet.has('Ceiling Play')) {
      badgeSet.add('Ceiling Play');
    }
  }

  p.badges = [...badgeSet];
}

/* Maps payload trait_weight_matrix keys → display labels (canonical source) */
const PAYLOAD_WEIGHT_LABELS = {
  'approach_150_200':  'APP 150-200 (Long Iron)',
  'sg_app_overall':    'APP Overall',
  'sg_ott_positional': 'OTT / Positional Drive',
  'driving_accuracy':  'Driving Accuracy',
  'sg_putt':           'Putting (Links-Regressed)',
  'sg_arg_short_game': 'Short Game/ARG',
};

/* ── Name-key helpers ── */
function makeNameKey(p) {
  if (p.last_name && p.first_name) return (p.last_name + ' ' + p.first_name).toUpperCase().trim();
  if (p.player_name) return p.player_name.toUpperCase().trim();
  return '';
}

function toNameKey(name) {
  // For player_id style: last_FIRST → keep as-is
  if (!name) return '';
  const parts = (name || '').split(', ');
  if (parts.length === 2) return `${parts[0].trim().toUpperCase()}_${parts[1].trim().toUpperCase()}`;
  return (name || '').trim().toUpperCase().replace(/\s+/g,'_');
}

/* ══════════════════════════════════════════════════════
   MISSING-TRAIT POLICY
══════════════════════════════════════════════════════ */
function isValidTraitScore(score) {
  if (score === null || score === undefined) return false;
  const n = +score;
  if (isNaN(n)) return false;
  if (VENUEDNA_CONFIG.treatZeroAsMissing && n === 0) return false;
  return true;
}

function getPlayerHistoricalBaseline(playerName, traitKey) {
  return null;
}

function computeConfidencePenalty(missingWeight) {
  if (VENUEDNA_CONFIG.confidencePenaltyMode === 'none' || missingWeight <= 0) return 0;
  const floor = VENUEDNA_CONFIG.confidenceFloor;
  let raw = 0;
  if (VENUEDNA_CONFIG.confidencePenaltyMode === 'linear') {
    raw = missingWeight * VENUEDNA_CONFIG.confidencePenaltyStrength;
  } else if (VENUEDNA_CONFIG.confidencePenaltyMode === 'stepped') {
    raw = missingWeight >= 0.20 ? 0.08 : missingWeight >= 0.10 ? 0.04 : 0.01;
  }
  return Math.min(raw, 1 - floor);
}

function runImputationPass(players) {
  const diag = {
    players_with_issues: [],
    field_averages: {},
    tier_averages: {},
    imputation_log: [],
    summary: null,
  };

  const fieldBucket = {};
  const tierBuckets = {};

  for (const p of players) {
    const tier = String(p.tier);
    if (!tierBuckets[tier]) tierBuckets[tier] = {};
    for (const t of (p.trait_scores || [])) {
      if (!fieldBucket[t.key])        fieldBucket[t.key] = [];
      if (!tierBuckets[tier][t.key])  tierBuckets[tier][t.key] = [];
      if (isValidTraitScore(t.score)) {
        fieldBucket[t.key].push(+t.score);
        tierBuckets[tier][t.key].push(+t.score);
      }
    }
  }

  const avg = arr => arr.length ? arr.reduce((a,b) => a+b, 0) / arr.length : null;

  const fieldAvg = {};
  for (const [key, arr] of Object.entries(fieldBucket)) {
    fieldAvg[key] = avg(arr);
    diag.field_averages[key] = fieldAvg[key] != null ? +fieldAvg[key].toFixed(1) : null;
  }

  const tierAvg = {};
  for (const [tier, traits] of Object.entries(tierBuckets)) {
    tierAvg[tier] = {};
    for (const [key, arr] of Object.entries(traits)) tierAvg[tier][key] = avg(arr);
  }
  diag.tier_averages = Object.fromEntries(
    Object.entries(tierAvg).map(([tier, traits]) => [
      `tier_${tier}`,
      Object.fromEntries(Object.entries(traits).map(([k,v]) => [k, v != null ? +v.toFixed(1) : null])),
    ])
  );

  for (const p of players) {
    p.imputed_traits = [];
    p.unknown_traits = [];
    p.missing_trait_weight = 0;
    const tier = String(p.tier);
    const pName = makeNameKey(p);

    for (const t of (p.trait_scores || [])) {
      if (!isValidTraitScore(t.score)) {
        t.original_score = t.score;
        t.imputed = true;

        const hb = getPlayerHistoricalBaseline(pName, t.key);
        const ta2 = tierAvg[tier]?.[t.key];
        const fa = fieldAvg[t.key];

        let imputedValue = null;
        let imputedFrom  = 'none';

        if (hb != null)       { imputedValue = hb; imputedFrom = 'player_historical'; }
        else if (ta2 != null) { imputedValue = ta2; imputedFrom = `tier_${tier}_avg`; }
        else if (fa != null)  { imputedValue = fa; imputedFrom = 'field_avg'; }

        t.score = imputedValue;
        t.imputed_from = imputedFrom;

        const entry = {
          key:           t.key,
          label:         t.label,
          weight:        t.weight,
          original:      t.original_score,
          imputed_value: imputedValue != null ? +imputedValue.toFixed(1) : null,
          from:          imputedFrom,
          resolved:      imputedValue != null,
        };

        if (imputedValue != null) p.imputed_traits.push(entry);
        else                      p.unknown_traits.push(entry);

        p.missing_trait_weight += (t.weight || 0);
        diag.players_with_issues.push({ player: pName, ...entry });
        diag.imputation_log.push({ player: pName, trait: t.key, from: imputedFrom });
      }
    }

    p.has_imputed = p.imputed_traits.length > 0;
    p.has_unknown = p.unknown_traits.length > 0;
    p.confidence_band =
      p.missing_trait_weight >= 0.20 ? 'low'    :
      p.missing_trait_weight >= 0.10 ? 'medium' :
      p.missing_trait_weight >  0    ? 'slight' : 'high';

    p.vts_raw = +p.vts_final;
    const penalty = computeConfidencePenalty(p.missing_trait_weight);
    p.vts_conf_adj = p.has_imputed || p.has_unknown
      ? +(p.vts_raw * (1 - penalty)).toFixed(2)
      : p.vts_raw;
    p.confidence_score = 1 - penalty;

    p.trait_map = {};
    for (const t of (p.trait_scores || [])) p.trait_map[t.key] = t;
  }

  const affected    = new Set(diag.players_with_issues.map(d => d.player));
  const withUnknown = new Set(diag.players_with_issues.filter(d => !d.resolved).map(d => d.player));
  const totalMissWt = [...affected].reduce((s, name) => {
    const p = players.find(x => makeNameKey(x) === name);
    return s + (p?.missing_trait_weight ?? 0);
  }, 0);

  diag.summary = {
    players_affected:          affected.size,
    players_with_unknown:      withUnknown.size,
    traits_imputed:            diag.players_with_issues.filter(d =>  d.resolved).length,
    traits_unknown:            diag.players_with_issues.filter(d => !d.resolved).length,
    avg_missing_trait_weight:  affected.size > 0 ? +(totalMissWt / affected.size).toFixed(3) : 0,
    affected_players:          [...affected],
    unknown_players:           [...withUnknown],
  };

  return diag;
}

function logDiagnostics(diag) {
  if (diag.summary.traits_imputed === 0) {
    console.info('[VenueDNA] Trait validation: all players fully observed. No imputation applied.');
    window.VenueDNA_Diagnostics = diag;
    return;
  }
  console.group('[VenueDNA] Missing-trait diagnostics');
  console.warn(
    `${diag.summary.traits_imputed} trait value(s) imputed across ` +
    `${diag.summary.players_affected} player(s): ${diag.summary.affected_players.join(', ')}`
  );
  console.groupCollapsed('Full imputation log');
  console.table(diag.players_with_issues);
  console.groupEnd();
  console.groupEnd();
  window.VenueDNA_Diagnostics = diag;
}

function renderDiagnosticsPanel(diag) {
  const el = document.getElementById('diag-panel-body');
  if (!el) return;

  const s = diag.summary;
  const allClear = s.traits_imputed === 0 && s.traits_unknown === 0;

  if (allClear) {
    el.innerHTML = `<p style="font-size:.78rem;color:var(--green)">✓ All player trait profiles fully observed. No imputation applied.</p>`;
    return;
  }

  const avgMissWtPct = +(s.avg_missing_trait_weight * 100).toFixed(1);
  const summaryHTML = `
    <div class="diag-counts">
      <span class="diag-count-pill">Players with imputed traits: <b>${s.players_affected - s.players_with_unknown}</b></span>
      <span class="diag-count-pill diag-count-warn">Players with unresolved unknown traits: <b>${s.players_with_unknown}</b></span>
      <span class="diag-count-pill">Traits successfully imputed: <b>${s.traits_imputed}</b></span>
      <span class="diag-count-pill diag-count-warn">Traits unresolved (unknown): <b>${s.traits_unknown}</b></span>
      <span class="diag-count-pill">Avg missing weight (affected): <b>${avgMissWtPct}%</b></span>
    </div>`;

  const byPlayer = {};
  for (const entry of diag.players_with_issues) {
    if (!byPlayer[entry.player]) byPlayer[entry.player] = [];
    byPlayer[entry.player].push(entry);
  }

  const rows = Object.entries(byPlayer).map(([name, traits]) => {
    const totalW   = traits.reduce((s, t) => s + (t.weight || 0), 0);
    const resolved = traits.filter(t =>  t.resolved);
    const unknown  = traits.filter(t => !t.resolved);
    const band     = totalW >= 0.20 ? 'low' : totalW >= 0.10 ? 'medium' : 'slight';
    const traitCells = traits.map(t => {
      const qual = t.resolved ? `~${t.imputed_value} via ${t.from}` : `? unknown`;
      const color = t.resolved ? 'var(--muted)' : '#f87171';
      return `<span style="font-size:.67rem;color:${color}">${t.key}: orig ${t.original ?? 'null'} → ${qual}</span>`;
    }).join('<br>');
    return `<tr>
      <td>${name}</td>
      <td><span class="diag-conf-badge diag-conf-${band}">${band}</span></td>
      <td style="font-size:.68rem">${(totalW*100).toFixed(0)}%</td>
      <td style="font-size:.68rem">${resolved.length} imputed · <span style="color:${unknown.length?'#f87171':'var(--muted)'}"> ${unknown.length} unknown</span></td>
      <td style="line-height:1.65">${traitCells}</td>
    </tr>`;
  }).join('');

  el.innerHTML = `
    ${summaryHTML}
    <div style="margin:.5rem 0;font-size:.73rem;color:#fcd34d">
      ⚠ VTS scores are pipeline-computed values. Imputation is a display-layer estimate only.
      <code style="font-size:.65rem;color:var(--muted);margin-left:.4rem">window.VenueDNA_Diagnostics</code> for full data.
    </div>
    <table class="diag-table">
      <thead><tr><th>Player</th><th>Conf</th><th>Missing Wt.</th><th>Counts</th><th>Trait detail</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderBadgeLegend(diag) {
  const el = document.getElementById('badge-legend');
  if (!el) return;
  if (diag.summary.traits_imputed === 0 && diag.summary.traits_unknown === 0) {
    el.style.display = 'none';
    return;
  }
  el.style.display = 'flex';
  el.innerHTML = `
    <span class="bl-label">Data quality:</span>
    <span class="bl-item"><span class="bl-dot bl-observed"></span>Observed</span>
    <span class="bl-item"><span class="badge-imputed badge-imputed-slight" style="position:static;font-size:.58rem">IMPUTED</span> ~estimated from tier/field avg</span>
    ${diag.summary.traits_unknown > 0
      ? `<span class="bl-item"><span class="badge-imputed badge-imputed-low" style="position:static;font-size:.58rem">UNKNOWN</span> no data available — excluded from filters</span>`
      : ''}`;
}

let DIAGNOSTICS = { summary: { traits_imputed: 0, players_affected: 0 } };

/* ── Anti-pattern metadata ── */
const AP_META = {
  bomb_and_spray:      { cls: 'bomb',   label: 'Bomb + Spray',            tip: 'Elite distance but below-field driving accuracy — high variance off tee at a placement-premium links.' },
  approach_liability:  { cls: 'wedge',  label: 'Approach Liability',       tip: 'Below-field approach proximity in the 150-200yd zone — drag on the course primary scoring trait.' },
  poor_links_putter:   { cls: 'birdie', label: 'Poor Links Putter',        tip: 'Below-field putting on links surfaces — limits birdie upside at Renaissance Club.' },
  debut_risk:          { cls: 'rough',  label: 'Debut Risk',               tip: 'First start at this venue — no course history adjustment.' },
  long_iron_weakness:  { cls: 'bomb',   label: 'Long-Iron Weakness',       tip: 'Below-field in 150-200yd approach zone — the highest-weighted trait here.' },
};

/* ── Filter preset definitions (Scottish Open) ── */
const FILTER_PRESETS = {
  'iron-elites':      [{ trait:'app_150_200',    op:'>=', value: 60 }],
  'long-iron-fits':   [{ trait:'app_150_200',    op:'>=', value: 55 }, { trait:'app_overall', op:'>=', value: 50 }],
  'positional-drivers':[{ trait:'driving_accuracy', op:'>=', value: 60 }],
  'course-horses':    [{ trait:'sg_putt',        op:'>=', value: 50 }],
  'ceiling-plays':    [{ trait:'sg_putt',        op:'>=', value: 40 }],
  'safe-cut-makers':  [{ trait:'app_150_200',    op:'>=', value: 45 }],
};

/* ── Preset view definitions ── */
const VIEW_PRESETS = {
  'top-equity':        { label: 'Top Win Equity',       sort: { col: 'win_pct', dir: -1 } },
  'iron-elites':       { label: 'Iron Elites',          sort: { col: 'vts_final', dir: -1 } },
  'long-iron-fits':    { label: 'Long-Iron Fits',       sort: { col: 'vts_final', dir: -1 } },
  'positional-drivers':{ label: 'Positional Drivers',   sort: { col: 'vts_final', dir: -1 } },
  'safe-cut-makers':   { label: 'Safe Cut Makers',      sort: { col: 'make_cut_prob', dir: -1 } },
  'longshot-dogs':     { label: 'Longshot Dogs',        tierFilter: '4', sort: { col: 'win_pct', dir: -1 } },
  'clean-flags':       { label: 'No Risk Flags',        noFlags: true, sort: { col: 'vts_final', dir: -1 } },
  'favorites':         { label: 'My Card',              favOnly: true },
};

/* ══════════════════════════════════════════════════════
   CSV PARSER
══════════════════════════════════════════════════════ */
function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''));
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g,''));
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] ?? ''; });
    return obj;
  });
}

/* ══════════════════════════════════════════════════════
   BOOTSTRAP
══════════════════════════════════════════════════════ */
async function init() {
  const [payload, briefs, vtsText] = await Promise.all([
    fetch(DATA_DIR + 'event_payload.json').then(r => r.json()),
    fetch(DATA_DIR + 'player_briefs.json').then(r => r.json()),
    fetch(DATA_DIR + 'vts_full.csv').then(r => r.text()),
  ]);

  /* Store event meta */
  eventMeta = payload;

  /* Parse vts_full.csv into a lookup by player_id */
  const vtsRows = parseCSV(vtsText);
  const vtsByPlayerId = {};
  for (const row of vtsRows) {
    if (row.player_id) vtsByPlayerId[row.player_id] = row;
  }

  /* Build briefs lookup by player_id and by name key */
  const briefsArr = Array.isArray(briefs) ? briefs : Object.values(briefs);
  for (const b of briefsArr) {
    if (b.player_id) briefsById[b.player_id] = b;
    const nk = makeNameKey(b);
    if (nk) briefsByNk[nk] = b;
  }

  /* Merge players from event_payload.players + vts_full.csv data */
  const payloadPlayers = payload.players || [];

  allPlayers = payloadPlayers.map(p => {
    const vts = vtsByPlayerId[p.player_id] || {};
    const brief = briefsById[p.player_id] || briefsByNk[makeNameKey(p)] || {};

    /* Display name: "LAST, FIRST" style for consistency with rest of app */
    const lastName  = (p.last_name || vts.last_name || '').trim();
    const firstName = (p.first_name || vts.first_name || '').trim();
    const player_name = lastName && firstName ? `${lastName}, ${firstName}` : (p.player_id || '');

    /* Numeric conversions from CSV (prefer CSV for probabilities as it has more decimal places) */
    const merged = {
      /* Identity */
      player_id:   p.player_id,
      player_name,
      last_name:   lastName,
      first_name:  firstName,

      /* Tier / rank */
      tier:        +(vts.tier || p.tier || 5),
      rank:        +(vts.rank || p.rank || 999),

      /* Scores */
      vts_final:          +(vts.vts_final || p.vts_final || 0),
      neutral_skill_index: +(vts.neutral_skill_index || p.neutral_skill_index || brief.neutral_skill_index || 0),
      venue_fit_score:     +(vts.venue_fit_score || p.venue_fit_score || 0),
      venue_history_normalized: +(vts.venue_history_normalized || p.venue_history_normalized || brief.venue_history_normalized || 0),
      form_score:          +(vts.form_score || p.form_score || brief.form_score || 0),
      penalties_applied:   +(vts.penalties_applied || 0),

      /* Probabilities */
      win_prob:      +(vts.win_prob || p.win_prob || 0),
      top5_prob:     +(vts.top5_prob || p.top5_prob || 0),
      top10_prob:    +(vts.top10_prob || p.top10_prob || 0),
      top20_prob:    +(vts.top20_prob || p.top20_prob || 0),
      make_cut_prob: +(vts.make_cut_prob || p.make_cut_prob || 0),
      miss_cut_prob: +(vts.miss_cut_prob || p.miss_cut_prob || 0),

      /* Alias for existing render functions */
      win_pct:    +(vts.win_prob || p.win_prob || 0),
      top5_pct:   +(vts.top5_prob || p.top5_prob || 0),
      top10_pct:  +(vts.top10_prob || p.top10_prob || 0),
      top20_pct:  +(vts.top20_prob || p.top20_prob || 0),

      /* Betting / conviction */
      best_betting_lane: vts.best_betting_lane || p.best_betting_lane || '',
      conviction_level:  vts.conviction_level  || p.conviction_level  || '',

      /* Anti-pattern flags — normalize from CSV "none" → '' */
      anti_pattern_flags: (() => {
        const f = vts.anti_pattern_flags || p.anti_pattern_flags || '';
        return (f === 'none' || f === 'None') ? '' : f;
      })(),

      /* Venue history rounds (from brief if available) */
      vh_rounds: p.starts_at_renaissance || brief.starts_at_renaissance || 0,

      /* VFD for display (venue_fit_score as a 0-100 percentile) */
      venue_fit_delta: +(vts.venue_fit_score || p.venue_fit_score || 0),

      /* Brief content */
      neutral_skill_summary:  p.neutral_skill_summary  || brief.neutral_skill_summary  || '',
      venue_fit_summary:      p.venue_fit_summary      || brief.venue_fit_summary      || '',
      venue_history_summary:  p.venue_history_summary  || brief.venue_history_summary  || '',
      form_summary:           p.form_summary           || brief.form_summary           || '',
      anti_pattern_summary:   p.anti_pattern_summary   || brief.anti_pattern_summary   || '',
      top_traits:    p.top_traits    || brief.top_traits    || [],
      drag_traits:   p.drag_traits   || brief.drag_traits   || [],
      risk_vector:   p.risk_vector   || brief.risk_vector   || '',
      failure_condition: p.failure_condition || brief.failure_condition || '',
      conviction_statement: p.conviction_statement || brief.conviction_statement || '',
      conviction_level:  p.conviction_level  || brief.conviction_level  || '',
      structural_edge:   p.structural_edge   || brief.structural_edge   || '',
      win_path:          p.win_path          || brief.win_path          || '',
      failure_mode:      p.failure_mode      || brief.failure_mode      || '',
      betting_use:       p.betting_use       || brief.betting_use       || '',
      market_misread:    p.market_misread    || brief.market_misread    || '',
      decomposition: p.decomposition || brief.decomposition || {},
      badges:        p.badges        || brief.badges        || [],
      brief_depth:   p.brief_depth   || brief.brief_depth   || '',

      /* Latent scores (continuous probability engine) */
      win_ceiling_score:  +(p.win_ceiling_score  || brief.win_ceiling_score  || 0),
      contention_score:   +(p.contention_score   || brief.contention_score   || 0),
      floor_score:        +(p.floor_score        || brief.floor_score        || 0),
      cut_survival_score: +(p.cut_survival_score || brief.cut_survival_score || 0),

      /* Extra fields */
      debut_flag:    p.debut_flag ?? brief.debut_flag ?? false,
      form_class:    p.form_class  || brief.form_class  || '',

      /* DB-sourced trait scores (from active_field_projections via engine) */
      tvl_score:   (p.tvl_score  != null) ? +p.tvl_score  : (brief.tvl_score  != null ? +brief.tvl_score  : null),
      hew_score:   (p.hew_score  != null) ? +p.hew_score  : (brief.hew_score  != null ? +brief.hew_score  : null),
      brie_score:  (p.brie_score != null) ? +p.brie_score : (brief.brie_score != null ? +brief.brie_score : null),
      vfr_score:   (p.vfr_score  != null) ? +p.vfr_score  : (brief.vfr_score  != null ? +brief.vfr_score  : null),

      /* Trait scores — built from TRAIT_DEFS + SG fields in payload */
      trait_scores: [],
    };

    /* Derive flag_count */
    merged.flag_count = merged.anti_pattern_flags
      ? merged.anti_pattern_flags.split(';').filter(f => f.trim() && f.trim() !== 'none').length
      : 0;

    /* Build trait_scores from available SG data (for imputation + filter panel).
       Use pickSg to distinguish null (no data) from 0.0 (exactly average) — the
       || 0 pattern would collapse both to zero and hide legitimate avg performers. */
    function pickSg(a, b) {
      if (a != null && !isNaN(+a)) return +a;
      if (b != null && !isNaN(+b)) return +b;
      return null;
    }
    const sgApp12m  = pickSg(p.sg_app_12m,  brief.sg_app_12m);
    const sgOtt12m  = pickSg(p.sg_ott_12m,  brief.sg_ott_12m);
    const sgPutt12m = pickSg(p.sg_putt_12m, brief.sg_putt_12m);
    const sgArg12m  = pickSg(p.sg_arg_12m,  brief.sg_arg_12m);

    /* Store raw SG values for field-relative percentile post-pass (computed after full field is built) */
    merged.sg_app_raw  = sgApp12m;
    merged.sg_ott_raw  = sgOtt12m;
    merged.sg_putt_raw = sgPutt12m;
    merged.sg_arg_raw  = sgArg12m;

    /* driving_accuracy_baseline is a %-point adj vs field avg (e.g. -3.3 = 3.3pp below avg).
       Map range -12..+12 to 0..100 so 0-adj players land at 50, not treated as zero/missing.
       Actual field range is -9.5% to +11.7% so bounds are never hit. */
    const driveAccRaw = (p.driving_accuracy_baseline != null) ? +p.driving_accuracy_baseline : null;
    const driveAccScore = (driveAccRaw !== null && !isNaN(driveAccRaw))
      ? Math.max(0, Math.min(100, ((driveAccRaw + 12) / 24) * 100))
      : null;

    /* app_150_200_value is strokes-gained-per-shot from fairway at 150-200yds relative to field avg.
       Store raw value here; percentile rank within the tournament field is computed in a post-pass
       after allPlayers is fully built, so the score reflects true field-relative ranking. */
    const app150Raw = (p.app_150_200_value != null) ? +p.app_150_200_value
                    : (brief.app_150_200_value != null ? +brief.app_150_200_value : null);
    merged.app_150_200_raw = (app150Raw !== null && !isNaN(app150Raw)) ? app150Raw : null;

    merged.trait_scores = [
      { key: 'app_150_200',    label: 'APP 150-200 (Long Iron)',   weight: 0.30, score: null }, // post-pass
      { key: 'ott_positional', label: 'OTT / Positional Drive',    weight: 0.20, score: null }, // post-pass
      { key: 'app_overall',    label: 'APP Overall',               weight: 0.15, score: null }, // post-pass
      { key: 'driving_accuracy', label: 'Driving Accuracy',        weight: 0.12, score: driveAccScore },
      { key: 'sg_putt',        label: 'Putting (Links-Regressed)', weight: 0.13, score: null }, // post-pass
      { key: 'sg_arg',         label: 'Short Game/ARG',             weight: 0.10, score: null }, // post-pass
    ];

    return merged;
  });

  allPlayers.sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));

  /* ── Field-relative percentile post-passes ──
     Each pass ranks players who have data against the full tournament field.
     Players with null raw values are excluded and keep score: null (shown as no-data).
     This ensures McIlroy SG-OTT 0.96 (rank 1) → 100, not 69 from a fixed ±2.5 range. */
  [
    ['app_150_200_raw', 'app_150_200'],
    ['sg_ott_raw',      'ott_positional'],
    ['sg_app_raw',      'app_overall'],
    ['sg_putt_raw',     'sg_putt'],
    ['sg_arg_raw',      'sg_arg'],
  ].forEach(([rawKey, traitKey]) => {
    const withData = allPlayers.filter(p => p[rawKey] != null);
    if (withData.length < 2) return;
    const sorted = [...withData].sort((a, b) => a[rawKey] - b[rawKey]);
    const n = sorted.length;
    sorted.forEach((p, i) => {
      const pct = (i / (n - 1)) * 100;
      const ts = p.trait_scores.find(t => t.key === traitKey);
      if (ts) ts.score = Math.round(pct * 10) / 10;
    });
  });

  /* ── Client-side badge enrichment (must run after allPlayers fully built) ── */
  allPlayers.forEach(p => enhanceBadges(p));

  /* ── Tier purity + betting lane corrections ──
     T3 players with no valid betting lane (Pass/No Edge) and WCS < 50 have no
     meaningful dark-horse upside — reclassify to T4 display tier.
     Lane thresholds:
       "Winner"  = genuine outright candidate: win% ≥3.0% (≈top 6 of 166-player field)
       "Top 5"   = strong contention profile: win% ≥1.8% (not ideal outright lane)
       "Top 10"  = solid T2 contender, thinner winning path (engine default kept)
     T1 note: engine sets all T1 no-flags win≥2.5% → "Winner"; all current T1
     players have win≥3.10% so they stay. Guard added for future proofing. */
  allPlayers.forEach(p => {
    /* T3 Pass/No Edge → T4 reclassification */
    if (p.tier === 3 && p.best_betting_lane === 'Pass / No Edge' && +p.win_ceiling_score < 50) {
      p.tier = 4;
      p.best_betting_lane = +p.make_cut_prob >= 35 ? 'Make Cut' : 'Miss Cut';
    }
    /* T1: correct any T1 player the engine mis-labeled if win < 3.0% */
    if (p.tier === 1) {
      if (+p.win_prob < 3.0) {
        p.best_betting_lane = +p.win_prob >= 1.8 ? 'Top 5' : 'Top 10';
      }
      /* win >= 3.0% stays "Winner" — engine already set it */
    }
    /* T2 no-flags: override engine's blanket "Top 10" with sharper lanes */
    if (p.tier === 2 && p.flag_count === 0) {
      if (+p.win_prob >= 3.0) {
        p.best_betting_lane = 'Winner';
      } else if (+p.win_prob >= 1.8) {
        p.best_betting_lane = 'Top 5';
      }
      /* win < 1.8%: keep engine's "Top 10" — no upgrade warranted */
    }
  });

  /* ── Missing-trait validation + imputation ── */
  DIAGNOSTICS = runImputationPass(allPlayers);
  logDiagnostics(DIAGNOSTICS);
  fieldTraitPercentiles = buildFieldTraitPercentiles(allPlayers);

  /* ── Weather forecast ── */
  try {
    const wxResp = await fetch(DATA_DIR + 'weather.json');
    weatherData = wxResp.ok ? await wxResp.json() : null;
  } catch(e) { weatherData = null; }

  /* ── Optional round analysis files ── */
  async function tryLoadRound(file, label) {
    try {
      const data = await fetch(DATA_DIR + file).then(r => {
        if (!r.ok) return null;
        return r.json();
      });
      if (data) console.info(`[VenueDNA] ${label} loaded`);
      return data;
    } catch (e) {
      console.warn(`[VenueDNA] ${label} not loaded (${e.message})`);
      return null;
    }
  }
  r1Data         = await tryLoadRound('r1_analysis.json',         'Round 1');
  r2Data         = await tryLoadRound('r2_analysis.json',         'Round 2');
  r3Data         = await tryLoadRound('r3_analysis.json',         'Round 3');
  r4Data         = await tryLoadRound('r4_analysis.json',         'Final');
  cumulativeData = await tryLoadRound('cumulative_learning.json', 'Cumulative learning');

  if (r4Data?.match_summary?.unmatched) {
    unmatchedR4FullNames = r4Data.match_summary.unmatched;
    r4Data.match_summary.unmatched.forEach(n => {
      unmatchedR4LastNames.add(normalizeLastName(n.trim().split(' ').pop()));
    });
  }

  renderHeader(payload);
  renderMetaBar(payload);
  renderInfoCards(payload);
  renderWeatherModule(weatherData);
  renderTierAlert();
  renderBriefs();
  renderFooter(payload);
  renderRoundInsights(payload);
  renderDiagnosticsPanel(DIAGNOSTICS);
  renderBadgeLegend(DIAGNOSTICS);
  wireDiagnosticsToggle();

  wireControls();
  wireModalClose();
  wireTierTabs();
  wireSortHeaders();
  wireCompare();
  wireFilterPanel();
  wirePresetDropdown();
  const glossaryBody = document.getElementById('glossary-modal-body');
  if (glossaryBody) glossaryBody.innerHTML = buildGlossaryHTML();
  wireGlossaryModal();

  applyAndRender();
}

/* ══════════════════════════════════════════════════════
   FIELD TRAIT PERCENTILES
══════════════════════════════════════════════════════ */
function buildFieldTraitPercentiles(players) {
  const buckets = {};
  for (const p of players) {
    for (const t of (p.trait_scores || [])) {
      if (t.score != null && !isNaN(+t.score)) {
        if (!buckets[t.key]) buckets[t.key] = [];
        buckets[t.key].push(+t.score);
      }
    }
  }
  const result = {};
  for (const [key, vals] of Object.entries(buckets)) {
    const sorted = [...vals].sort((a, b) => a - b);
    result[key] = {
      p40: sorted[Math.floor(sorted.length * 0.40)] ?? 40,
      p75: sorted[Math.floor(sorted.length * 0.75)] ?? 65,
    };
  }
  return result;
}

/* ══════════════════════════════════════════════════════
   WEATHER MODULE
══════════════════════════════════════════════════════ */
function renderWeatherModule(data) {
  const el = document.getElementById('weather-module');
  if (!el || !data) { if (el) el.style.display = 'none'; return; }

  const colorMap = { green: '#4ade80', amber: '#fcd34d', red: '#f87171' };

  const roundCards = (data.rounds || []).map(r => {
    const c = colorMap[r.color] || '#94a3b8';
    return `<div class="wx-round">
      <div class="wx-round-label" style="color:${c}">${r.tag}</div>
      <div class="wx-round-day">R${r.round} · ${r.date}</div>
      <div class="wx-round-stats">
        <span class="wx-stat">${r.high_c}°C</span>
        <span class="wx-stat">${r.wind_mph}mph ${r.wind_dir}</span>
        <span class="wx-stat">${r.rain_pct}% rain</span>
      </div>
      <div class="wx-round-note">${r.note}</div>
    </div>`;
  }).join('');

  const amplified = (data.traits_amplified || []).map(t => `<span class="wx-trait-chip">${t}</span>`).join('');

  el.innerHTML = `<div class="wx-module">
    <div class="wx-header">
      <span class="wx-title">🌬 Weather &amp; Conditions Forecast</span>
      <span class="wx-summary-tag">Projected score: <b>${data.winning_score_range}</b></span>
    </div>
    <div class="wx-rounds">${roundCards}</div>
    <div class="wx-bottom">
      <span class="wx-amplified-label">Traits amplified by forecast:</span>
      ${amplified}
    </div>
  </div>`;
}

/* ══════════════════════════════════════════════════════
   HEADER / META / INFO CARDS
══════════════════════════════════════════════════════ */
function renderHeader(payload) {
  const ev = payload.event;
  document.querySelector('.header h1').innerHTML = `<span>PGA VenueDNA</span> — 2026 Genesis Scottish Open`;
  document.querySelector('.header-meta').textContent =
    `${ev.venue} · ${ev.location} · ${ev.dates} · Par ${ev.par} · ${ev.yards} yds`;

  /* Remove no-cut banner — this event HAS a cut */
  const noCutEl = document.querySelector('.nocut-banner');
  if (noCutEl) noCutEl.style.display = 'none';

  const badges = document.querySelector('.badges');
  if (ev.field_locked) badges.insertAdjacentHTML('beforeend','<span class="badge-locked">FIELD LOCKED</span>');
  const currentRound = r4Data ? 'r4' : r3Data ? 'r3' : r2Data ? 'r2' : r1Data ? 'r1' : null;
  if (currentRound) badges.insertAdjacentHTML('beforeend',`<span class="badge-tbd">iter:${currentRound}</span>`);
}

function renderMetaBar(payload) {
  const ev = payload.event;
  document.querySelector('.meta-bar-inner').innerHTML = [
    `<span>Field: <b>${ev.field_size} players</b></span>`,
    `<span>Purse: <b>$${(ev.purse_usd/1e6).toFixed(0)}M</b></span>`,
    `<span>Tour: <b>${ev.tour}</b></span>`,
    `<span>Course type: <b>${ev.course_type}</b></span>`,
    `<span>Variance: <b>${ev.variance_class}</b></span>`,
    `<span>Cut rule: <b>${ev.cut_rule}</b></span>`,
    `<span>Anti-patterns: <b>${ev.anti_pattern_count}</b></span>`,
  ].join('');
}

function renderInfoCards(payload) {
  const ev = payload.event;
  const weights = ev.trait_weight_matrix || {};

  /* Derive primary trait dynamically from canonical payload weights */
  const sortedWeights = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  const [primaryKey, primaryVal] = sortedWeights[0] || ['approach_150_200', 0.30];
  const primaryLabel = PAYLOAD_WEIGHT_LABELS[primaryKey] || primaryKey.replace(/_/g, ' ');
  const primaryPct   = Math.round((primaryVal || 0) * 100);

  /* Winner profile */
  const winnerProfile = ev.winner_trait_profile || 'Strong approach from 150-200yds, positive driving accuracy, elite SG:APP.';

  /* Comp courses */
  const compCourses = (ev.comp_courses || []).map(c => c.name).join(', ');

  document.querySelector('.info-grid').innerHTML = `
    <div class="info-card">
      <h3>Venue</h3>
      ${kv('Location', ev.location)}
      ${kv('Par / Yardage', `${ev.par} / ${ev.yards} yds`)}
      ${kv('Course type', ev.course_type)}
      ${kv('Variance class', ev.variance_class)}
      ${kv('Primary scoring zone', ev.primary_scoring_zone)}
      ${kv('Cut rule', ev.cut_rule)}
      ${kv('Comp courses', compCourses)}
    </div>
    <div class="info-card">
      <h3>Trait Weights</h3>
      ${Object.entries(weights).map(([k,w])=>kv(
        PAYLOAD_WEIGHT_LABELS[k] || TRAIT_KEY_MAP[k.replace(/-/g,'_')]?.label || k.replace(/_/g,' '),
        `${Math.round(w*100)}%`
      )).join('')}
      <div class="kv" style="margin-top:.4rem;border-top:1px solid var(--border)">
        <span class="k" style="color:#38bdf8;font-size:.72rem">Primary trait</span>
        <span class="v" style="color:#38bdf8;font-size:.72rem">${primaryLabel}: ${primaryPct}%</span>
      </div>
    </div>
    <div class="info-card">
      <h3>Winner Profile</h3>
      ${kv('Debut players', ev.debut_count)}
      ${kv('Anti-pattern flags', ev.anti_pattern_count)}
      ${kv('Model version', ev.model_version)}
      ${kv('Generated', ev.generated_date)}
      <div style="margin-top:.5rem;font-size:.73rem;color:var(--muted);line-height:1.5">${winnerProfile}</div>
    </div>`;
}

function kv(k, v) {
  return `<div class="kv"><span class="k">${k}</span><span class="v">${v ?? '—'}</span></div>`;
}

function renderTierAlert() {
  const el = document.querySelector('.tee-alert');
  if (!el) return;
  if (r1Data || r2Data || r3Data || r4Data) { el.style.display = 'none'; return; }
  const counts = {};
  for (let t = 1; t <= 5; t++) {
    counts[t] = allPlayers.filter(p => +p.tier === t).length;
  }
  const total = allPlayers.length;
  el.textContent =
    `Tee times TBD — ${total} players scored. ` +
    `Distribution — T1:${counts[1]}  T2:${counts[2]}  T3:${counts[3]}  T4:${counts[4]}  T5:${counts[5]}`;
}

/* ══════════════════════════════════════════════════════
   UNIFIED FILTER + RENDER PIPELINE
══════════════════════════════════════════════════════ */
function applyAndRender() {
  let players = [...allPlayers];

  if (activeTier !== 'all') {
    players = players.filter(p => String(p.tier) === activeTier);
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    players = players.filter(p =>
      p.player_name.toLowerCase().includes(q) ||
      (p.first_name + ' ' + p.last_name).toLowerCase().includes(q)
    );
  }

  if (favOnly) {
    players = players.filter(p => favorites.has(p.player_name));
  }

  if (activePreset) {
    const vp = VIEW_PRESETS[activePreset];
    if (vp) {
      if (vp.favOnly) players = players.filter(p => favorites.has(p.player_name));
      if (vp.noFlags) players = players.filter(p => p.flag_count === 0);
      if (vp.tierFilter) players = players.filter(p => String(p.tier) === vp.tierFilter);
      if (vp.traitFilters) {
        vp.traitFilters.forEach(tf => { players = players.filter(p => traitFilterPass(p, tf)); });
      }
    }
  }

  activeFilters.forEach(f => {
    players = players.filter(p => traitFilterPassGlobal(p, f));
  });

  if (activeBadgeFilter) {
    players = players.filter(p => (p.badges || []).includes(activeBadgeFilter));
  }

  players = sortPlayers(players);

  renderTable(players);
  updateResultBar(players.length);
  updateActivePills();
  updateSortIndicators();
}

/* traitFilterPassGlobal — handles both trait_map (observed) and direct player fields */
function traitFilterPassGlobal(p, f) {
  /* Try trait_map first */
  if (p.trait_map && p.trait_map[f.trait]) {
    return traitFilterPass(p, f);
  }
  /* Fall through to direct fields for non-trait filters */
  const directMap = {
    'make_cut_prob':   p.make_cut_prob,
    'venue_history':   p.venue_history_normalized,
    'win_prob':        p.win_prob,
    'top5_prob':       p.top5_prob,
    'form_score':      p.form_score,
    'top10_prob':      p.top10_prob,
    'top20_prob':      p.top20_prob,
    'venue_fit_score': p.venue_fit_score,
    'vts_final':       +p.vts_final,
    'tvl_score':    p.tvl_score,
    'hew_score':    p.hew_score,
    'brie_score':   p.brie_score,
    'vfr_score':    p.vfr_score,
  };
  const score = directMap[f.trait];
  if (score == null) return false;
  const val = parseFloat(f.value);
  if (isNaN(val)) return true;
  if (f.op === '>=') return +score >= val;
  if (f.op === '<=') return +score <= val;
  if (f.op === '=')  return Math.round(+score) === Math.round(val);
  return true;
}

function getTraitQuality(p, traitKey) {
  const t = p.trait_map?.[traitKey];
  if (!t) return 'unknown';
  if (!t.imputed) return 'observed';
  return t.score !== null ? 'imputed' : 'unknown';
}

function traitFilterPass(p, f) {
  const quality = getTraitQuality(p, f.trait);
  if (quality === 'unknown') return false;
  if (quality === 'imputed' && !allowImputedInFilters) return false;
  const t = p.trait_map?.[f.trait];
  const score = t?.score != null ? +t.score : null;
  if (score === null) return false;
  const val = parseFloat(f.value);
  if (isNaN(val)) return true;
  if (f.op === '>=') return score >= val;
  if (f.op === '<=') return score <= val;
  if (f.op === '=')  return Math.round(score) === Math.round(val);
  return true;
}

function getTraitScore(p, traitKey) {
  const t = p.trait_map?.[traitKey];
  if (!t || t.score === null) return null;
  return +t.score;
}

function sortPlayers(players) {
  const col = sortCol;
  const dir = sortDir;
  return [...players].sort((a, b) => {
    let va, vb;
    if (col === 'player_name') {
      va = a.player_name || '';
      vb = b.player_name || '';
      return dir * va.localeCompare(vb);
    }
    if (col === 'flag_count') { va = a.flag_count || 0; vb = b.flag_count || 0; }
    else if (col === 'rank')      { va = a.rank ?? 999; vb = b.rank ?? 999; }
    else if (col === 'tier')      { va = a.tier ?? 9; vb = b.tier ?? 9; }
    else if (col === 'vts_final') {
      const useAdj = VENUEDNA_CONFIG.confidencePenaltyMode !== 'none';
      va = useAdj ? (a.vts_conf_adj ?? a.vts_raw ?? 0) : (+a.vts_final || 0);
      vb = useAdj ? (b.vts_conf_adj ?? b.vts_raw ?? 0) : (+b.vts_final || 0);
    }
    else if (col === 'venue_fit_score'){ va = +a.venue_fit_score || 0; vb = +b.venue_fit_score || 0; }
    else if (col === 'win_pct')      { va = +a.win_pct  || 0; vb = +b.win_pct  || 0; }
    else if (col === 'top5_pct')     { va = +a.top5_pct  || 0; vb = +b.top5_pct  || 0; }
    else if (col === 'top10_pct')    { va = +a.top10_pct || 0; vb = +b.top10_pct || 0; }
    else if (col === 'top20_pct')    { va = +a.top20_pct || 0; vb = +b.top20_pct || 0; }
    else if (col === 'make_cut_prob'){ va = +a.make_cut_prob || 0; vb = +b.make_cut_prob || 0; }
    else if (col === 'vh_rounds')    { va = +a.vh_rounds || 0; vb = +b.vh_rounds || 0; }
    else { va = a.rank ?? 999; vb = b.rank ?? 999; }
    return dir * (va - vb);
  });
}

/* ══════════════════════════════════════════════════════
   TABLE RENDER
══════════════════════════════════════════════════════ */
function renderTable(players) {
  const tbody = document.getElementById('player-tbody');
  const empty = document.getElementById('empty-state');
  tbody.innerHTML = '';

  if (players.length === 0) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  players.forEach(p => {
    const isFav = favorites.has(p.player_name);
    const inCompare = comparePlayers.some(c => c.player_name === p.player_name);
    const tr = document.createElement('tr');
    if (isFav) tr.classList.add('row-fav');
    if (inCompare) tr.classList.add('row-compare');
    tr.dataset.name = p.player_name;

    const dataBadge = playerDataBadgeHTML(p);

    /* Check for unmatched R4 */
    const _pLastName = normalizeLastName((p.last_name || p.player_name.split(',')[0]).trim());
    const unmatchedBadge = unmatchedR4LastNames.has(_pLastName)
      ? ' <span class="badge-unmatched" title="Player not found in R4 leaderboard data">UNMATCHED</span>'
      : '';

    /* Display name: "First Last" */
    const displayName = p.first_name && p.last_name
      ? `${p.first_name} ${p.last_name}`
      : p.player_name.split(', ').reverse().join(' ').trim();

    /* Cut probability cell */
    const cutCell = `<span style="color:${+p.make_cut_prob >= 70 ? '#4ade80' : +p.make_cut_prob >= 45 ? '#fcd34d' : '#f87171'};font-size:.8rem;font-weight:600">${fmtPct(p.make_cut_prob)}</span>`;

    /* Badges from player brief */
    const playerBadgesHTML = renderPlayerBadges(p.badges);

    tr.innerHTML = `
      <td class="rank-cell">${p.rank}</td>
      <td>
        <div class="player-name">${displayName} ${dataBadge}${unmatchedBadge}</div>
        <div class="player-driver">${p.best_betting_lane || ''} ${playerBadgesHTML}</div>
      </td>
      <td><span class="tier-badge t${p.tier} tier-badge-link" title="Click to filter Tier ${p.tier}">T${p.tier}</span></td>
      <td class="vts-cell">${vtsDisplayHTML(p)}</td>
      <td class="vts-label col-vfd" style="text-align:center">${vfdFitHTML(p)}</td>
      <td class="prob-cell">${fmtPct(p.win_pct)}</td>
      <td class="prob-cell">${fmtPct(p.top5_pct)}</td>
      <td class="prob-cell">${fmtPct(p.top10_pct)}</td>
      <td class="prob-cell">${fmtPct(p.top20_pct)}</td>
      <td>${cutCell}</td>
      <td>${apTagsHTML(p.anti_pattern_flags)}${confAdjFlagHTML(p)}</td>
      <td class="vts-label">${p.vh_rounds > 0 ? p.vh_rounds + ' rds' : p.debut_flag ? '<span style="color:#fcd34d;font-size:.72rem">Debut</span>' : '—'}</td>
      <td class="fav-cell">
        <button class="fav-btn${isFav ? ' on' : ''}" title="${isFav ? 'Remove favorite' : 'Add to favorites'}">★</button>
      </td>
      <td class="cmp-cell">
        <button class="cmp-btn${inCompare ? ' on' : ''}" title="${inCompare ? 'Remove from compare' : 'Add to compare'}">⊕</button>
      </td>`;

    tr.addEventListener('click', e => {
      if (e.target.classList.contains('fav-btn') || e.target.classList.contains('cmp-btn')) return;

      /* Tier badge click → jump to that tier filter */
      if (e.target.classList.contains('tier-badge-link')) {
        const t = String(p.tier);
        activeTier = t;
        document.querySelectorAll('.tier-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.tier === t));
        applyAndRender();
        return;
      }

      /* Player badge click → toggle badge filter */
      if (e.target.classList.contains('player-badge-link')) {
        const badge = e.target.dataset.badge;
        activeBadgeFilter = activeBadgeFilter === badge ? null : badge;
        applyAndRender();
        return;
      }

      const brief = briefsById[p.player_id] || briefsByNk[makeNameKey(p)];
      openModal(p, brief);
    });

    tr.querySelector('.fav-btn').addEventListener('click', e => {
      e.stopPropagation();
      toggleFavorite(p.player_name);
    });

    tr.querySelector('.cmp-btn').addEventListener('click', e => {
      e.stopPropagation();
      toggleCompare(p);
    });

    tbody.appendChild(tr);
  });

  /* R4 unmatched placeholder rows */
  if (r4Data && unmatchedR4FullNames.length) {
    const payloadLastNames = new Set(allPlayers.map(p => normalizeLastName((p.last_name || p.player_name.split(',')[0]).trim())));
    unmatchedR4FullNames.forEach(fullName => {
      const parts = fullName.trim().split(' ');
      const lastNorm = normalizeLastName(parts[parts.length - 1]);
      if (payloadLastNames.has(lastNorm)) return;
      const ph = document.createElement('tr');
      ph.className = 'row-placeholder';
      ph.innerHTML = `
        <td class="rank-cell" style="color:var(--muted)">—</td>
        <td>
          <div class="player-name">${fullName}
            <span class="badge-unmatched" title="Not in pre-tournament model">WD / ABSENT</span>
          </div>
          <div class="player-driver" style="color:var(--muted)">Not in pre-tournament model</div>
        </td>
        <td>—</td>
        <td class="vts-cell" style="color:var(--muted)">—</td>
        <td class="vts-label col-vfd" style="text-align:center;color:var(--muted)">—</td>
        <td class="prob-cell" style="color:var(--muted)">—</td>
        <td class="prob-cell" style="color:var(--muted)">—</td>
        <td class="prob-cell" style="color:var(--muted)">—</td>
        <td class="prob-cell" style="color:var(--muted)">—</td>
        <td style="color:var(--muted)">—</td>
        <td>—</td>
        <td class="vts-label" style="color:var(--muted)">—</td>
        <td class="fav-cell"></td>
        <td class="cmp-cell"></td>`;
      tbody.appendChild(ph);
    });
  }
}

/* Render player badges — table row: typed, truncation-safe, max 2 + "+N" overflow chip.
   Sorted: fit first, then ceiling, then risk. */
function renderPlayerBadges(badges) {
  if (!badges || badges.length === 0) return '';
  const TYPE_ORDER = { fit: 0, ceiling: 1, risk: 2, misc: 3 };
  const sorted = [...badges].sort((a, b) =>
    ((TYPE_ORDER[classifyBadge(a).type] ?? 9) - (TYPE_ORDER[classifyBadge(b).type] ?? 9))
  );
  const visible = sorted.slice(0, 2);
  const extra   = sorted.length - 2;
  const pills = visible.map(b => {
    const { color, tooltip } = classifyBadge(b);
    return `<span class="player-badge player-badge-link" data-badge="${b}" title="${tooltip} — click to filter" style="background:${color}22;border:1px solid ${color};color:${color}">${b}</span>`;
  }).join('');
  const morePill = extra > 0
    ? `<span class="badge-overflow-chip" title="${sorted.slice(2).join(', ')}">+${extra}</span>`
    : '';
  return pills + morePill;
}

function updateResultBar(count) {
  const bar = document.getElementById('table-result-bar');
  const total = allPlayers.length;
  const filtered = count < total;
  if (filtered || searchQuery || activeFilters.length || favOnly || activePreset) {
    bar.style.display = 'block';
    bar.textContent = `Showing ${count} of ${total} players`;
  } else {
    bar.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════════════
   CONTROLS WIRING
══════════════════════════════════════════════════════ */
function wireControls() {
  const input = document.getElementById('search-input');
  const clear = document.getElementById('search-clear');

  input.addEventListener('input', () => {
    searchQuery = input.value;
    clear.style.display = searchQuery ? 'block' : 'none';
    applyAndRender();
  });
  clear.addEventListener('click', () => {
    input.value = '';
    searchQuery = '';
    clear.style.display = 'none';
    input.focus();
    applyAndRender();
  });

  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== input && !isModalOpen()) {
      e.preventDefault();
      input.focus();
    }
  });

  document.getElementById('btn-favonly').addEventListener('click', () => {
    favOnly = !favOnly;
    document.getElementById('btn-favonly').classList.toggle('active', favOnly);
    applyAndRender();
  });

  document.getElementById('btn-reset').addEventListener('click', resetAll);
  document.getElementById('empty-reset').addEventListener('click', resetAll);
}

function wireTierTabs() {
  document.querySelectorAll('.tier-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      activeTier = tab.dataset.tier;
      document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      applyAndRender();
    });
  });
}

function wireSortHeaders() {
  document.querySelectorAll('.th-sort').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (sortCol === col) {
        sortDir = -sortDir;
      } else {
        sortCol = col;
        sortDir = (col === 'player_name' || col === 'tier' || col === 'rank') ? 1 : -1;
      }
      applyAndRender();
    });
  });
}

function updateSortIndicators() {
  document.querySelectorAll('.th-sort').forEach(th => {
    const col = th.dataset.col;
    th.classList.toggle('sorted', col === sortCol);
    const ind = th.querySelector('.sort-ind');
    if (ind) {
      if (col === sortCol) ind.textContent = sortDir === 1 ? '▲' : '▼';
      else ind.textContent = '';
    }
  });
}

/* ══════════════════════════════════════════════════════
   FAVORITES
══════════════════════════════════════════════════════ */
function toggleFavorite(name) {
  if (favorites.has(name)) favorites.delete(name);
  else favorites.add(name);
  updateFavCount();
  applyAndRender();
}

function updateFavCount() {
  document.getElementById('fav-count').textContent = favorites.size;
}

/* ══════════════════════════════════════════════════════
   COMPARE
══════════════════════════════════════════════════════ */
function wireCompare() {
  document.getElementById('btn-open-compare').addEventListener('click', openCompareModal);
  document.getElementById('btn-clear-compare').addEventListener('click', clearCompare);
  document.getElementById('compare-modal-close').addEventListener('click', () => {
    document.getElementById('compare-modal-overlay').style.display = 'none';
  });
  document.getElementById('compare-modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) e.currentTarget.style.display = 'none';
  });
}

function toggleCompare(p) {
  const idx = comparePlayers.findIndex(c => c.player_name === p.player_name);
  if (idx >= 0) {
    comparePlayers.splice(idx, 1);
  } else if (comparePlayers.length < 3) {
    comparePlayers.push(p);
  }
  updateCompareTray();
  const btn = document.getElementById('btn-compare');
  if (comparePlayers.length > 0) {
    btn.style.display = 'flex';
    document.getElementById('compare-num').textContent = comparePlayers.length;
  } else {
    btn.style.display = 'none';
  }
  applyAndRender();
}

function clearCompare() {
  comparePlayers = [];
  updateCompareTray();
  document.getElementById('btn-compare').style.display = 'none';
  applyAndRender();
}

function updateCompareTray() {
  const tray = document.getElementById('compare-tray');
  const playersEl = document.getElementById('compare-tray-players');
  if (comparePlayers.length === 0) {
    tray.style.display = 'none';
    return;
  }
  tray.style.display = 'block';
  const slotsLeft = 3 - comparePlayers.length;
  const slotHint = slotsLeft > 0
    ? `<span class="compare-slot-hint">+ ${slotsLeft} slot${slotsLeft > 1 ? 's' : ''} available</span>`
    : '';
  playersEl.innerHTML = comparePlayers.map(p =>
    `<div class="compare-chip">
       ${p.first_name || p.player_name.split(', ')[1] || p.player_name.split(',')[0]}
       <button class="compare-chip-remove" data-name="${p.player_name}" title="Remove">✕</button>
     </div>`
  ).join('') + slotHint;
  playersEl.querySelectorAll('.compare-chip-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.name;
      comparePlayers = comparePlayers.filter(c => c.player_name !== name);
      updateCompareTray();
      if (comparePlayers.length === 0) document.getElementById('btn-compare').style.display = 'none';
      else document.getElementById('compare-num').textContent = comparePlayers.length;
      applyAndRender();
    });
  });
}

function openCompareModal() {
  if (comparePlayers.length < 2) return;
  const overlay = document.getElementById('compare-modal-overlay');
  const body = document.getElementById('compare-modal-body');
  const n = comparePlayers.length;
  const colClass = n === 2 ? 'cols-2' : 'cols-3';

  const STAT_KEYS = [
    ['VTS',       p => (+p.vts_final).toFixed(1)],
    ['Win %',     p => fmtPct(p.win_pct)],
    ['Top 5 %',   p => fmtPct(p.top5_pct)],
    ['Top 10 %',  p => fmtPct(p.top10_pct)],
    ['Top 20 %',  p => fmtPct(p.top20_pct)],
    ['Make Cut',  p => fmtPct(p.make_cut_prob)],
    ['Miss Cut',  p => fmtPct(p.miss_cut_prob)],
    ['Tier',      p => `T${p.tier}`],
    ['CH Rds',    p => p.vh_rounds > 0 ? `${p.vh_rounds}` : (p.debut_flag ? 'Debut' : '—')],
    ['Flags',     p => p.flag_count > 0 ? apTagsHTML(p.anti_pattern_flags) : '—'],
    ['VFS',       p => (+p.venue_fit_score).toFixed(1)],
  ];

  const cols = comparePlayers.map(p => {
    const statRows = STAT_KEYS.map(([k, fn]) =>
      `<div class="compare-stat"><span class="cs-k">${k}</span><span class="cs-v">${fn(p)}</span></div>`
    ).join('');

    const traitRows = (p.trait_scores || []).filter(t => t.score != null).sort((a,b) => b.weight - a.weight).map(t => {
      const s = +t.score;
      const cmpPercs = fieldTraitPercentiles[t.key] || { p40: 40, p75: 65 };
      const cls = s >= cmpPercs.p75 ? 'bar-elite' : s >= cmpPercs.p40 ? 'bar-ok' : 'bar-weak';
      return `<div class="compare-trait-row">
        <span class="compare-trait-label">${t.label.split('(')[0].trim()}</span>
        <div class="compare-trait-bar-bg"><div class="compare-trait-bar-fill ${cls}" style="width:${Math.min(100,s)}%"></div></div>
        <span class="compare-trait-score" style="color:${s>=75?'#38bdf8':s>=50?'#4ade80':'#f87171'}">${s.toFixed(0)}</span>
      </div>`;
    }).join('');

    const displayName = p.first_name && p.last_name ? `${p.first_name} ${p.last_name}` : p.player_name;

    return `<div class="compare-col">
      <div class="compare-col-name">${displayName}</div>
      <div class="compare-col-sub">${tierBadgeHTML(p.tier)} &nbsp; VTS ${(+p.vts_final).toFixed(1)}</div>
      <h5>Output</h5>
      ${statRows}
      ${traitRows ? `<h5>Trait Profile</h5>${traitRows}` : ''}
      ${(p.structural_edge || p.conviction_statement) ? `<h5>${p.structural_edge ? 'Intelligence' : 'Conviction'}</h5><div style="font-size:.7rem;color:var(--muted);line-height:1.5">${p.structural_edge ? `<strong>Edge:</strong> ${p.structural_edge}` : p.conviction_statement}</div>` : ''}
    </div>`;
  }).join('');

  body.innerHTML = `<div class="compare-grid ${colClass}">${cols}</div>`;
  overlay.style.display = 'flex';
}

/* ══════════════════════════════════════════════════════
   FILTER PANEL
══════════════════════════════════════════════════════ */
function wireFilterPanel() {
  document.getElementById('btn-filter').addEventListener('click', () => {
    const panel = document.getElementById('filter-panel');
    const open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    document.getElementById('btn-filter').setAttribute('aria-expanded', String(!open));
    if (!open && document.getElementById('filter-rules').children.length === 0) {
      addFilterRule();
    }
  });
  document.getElementById('fp-close').addEventListener('click', () => {
    document.getElementById('filter-panel').style.display = 'none';
    document.getElementById('btn-filter').setAttribute('aria-expanded', 'false');
  });
  document.getElementById('fp-add-rule').addEventListener('click', addFilterRule);

  document.getElementById('fp-include-imputed').addEventListener('change', e => {
    allowImputedInFilters = e.target.checked;
    applyAndRender();
  });

  document.querySelectorAll('.fp-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const preset = chip.dataset.fpreset;
      const rules = FILTER_PRESETS[preset];
      if (!rules) return;
      activeFilters = rules.map(r => ({ ...r, id: ++filterRuleCounter }));
      syncFilterRulesUI();
      applyAndRender();
    });
  });
}

function addFilterRule(trait='app_150_200', op='>=', value=55) {
  const id = ++filterRuleCounter;
  activeFilters.push({ id, trait, op, value });
  syncFilterRulesUI();
  applyAndRender();
}

function syncFilterRulesUI() {
  const container = document.getElementById('filter-rules');
  container.innerHTML = '';
  const badge = document.getElementById('filter-badge');

  const imputedCb = document.getElementById('fp-include-imputed');
  if (imputedCb) imputedCb.checked = allowImputedInFilters;

  if (activeFilters.length === 0) {
    badge.style.display = 'none';
    return;
  }
  badge.style.display = 'inline-block';
  badge.textContent = activeFilters.length;

  activeFilters.forEach(f => {
    const row = document.createElement('div');
    row.className = 'filter-rule';
    row.dataset.id = f.id;

    const traitOpts = [
      ...TRAIT_DEFS.map(t =>
        `<option value="${t.key}" ${t.key === f.trait ? 'selected' : ''}>${t.label} (${Math.round(t.weight*100)}%)</option>`
      ),
      `<option disabled>─── Numeric columns ───</option>`,
      ...EXTRA_FILTER_DEFS.map(t =>
        `<option value="${t.key}" ${t.key === f.trait ? 'selected' : ''}>${t.label}</option>`
      ),
    ].join('');

    row.innerHTML = `
      <select class="fp-select fp-trait-sel">
        ${traitOpts}
      </select>
      <select class="fp-select fp-op-sel">
        <option value=">=" ${f.op === '>=' ? 'selected' : ''}>≥</option>
        <option value="<=" ${f.op === '<=' ? 'selected' : ''}>≤</option>
        <option value="="  ${f.op === '='  ? 'selected' : ''}>=</option>
      </select>
      <input type="number" class="fp-input fp-val" value="${f.value}" min="0" max="100" step="5" />
      <span style="font-size:.7rem;color:var(--muted)">(0–100)</span>
      <button class="fp-remove-rule" title="Remove rule">✕</button>`;

    row.querySelector('.fp-trait-sel').addEventListener('change', e => { f.trait = e.target.value; applyAndRender(); });
    row.querySelector('.fp-op-sel').addEventListener('change', e => { f.op = e.target.value; applyAndRender(); });
    row.querySelector('.fp-val').addEventListener('input', e => { f.value = parseFloat(e.target.value) || 0; applyAndRender(); });
    row.querySelector('.fp-remove-rule').addEventListener('click', () => {
      activeFilters = activeFilters.filter(x => x.id !== f.id);
      syncFilterRulesUI();
      applyAndRender();
    });

    container.appendChild(row);
  });
}

/* ══════════════════════════════════════════════════════
   ACTIVE PILLS
══════════════════════════════════════════════════════ */
function updateActivePills() {
  const el = document.getElementById('active-pills');
  const pills = [];

  if (activePreset) {
    const vp = VIEW_PRESETS[activePreset];
    pills.push(`<span class="filter-pill pill-preset">${vp?.label || activePreset}
      <button class="filter-pill-remove" data-action="clear-preset">✕</button></span>`);
  }

  if (favOnly) {
    pills.push(`<span class="filter-pill pill-favonly">★ Favorites only
      <button class="filter-pill-remove" data-action="clear-fav">✕</button></span>`);
  }

  if (activeTier !== 'all') {
    pills.push(`<span class="filter-pill pill-tier">Tier ${activeTier}
      <button class="filter-pill-remove" data-action="clear-tier">✕</button></span>`);
  }

  if (activeBadgeFilter) {
    pills.push(`<span class="filter-pill pill-badge">${activeBadgeFilter}
      <button class="filter-pill-remove" data-action="clear-badge">✕</button></span>`);
  }

  const allFilterDefs = [...TRAIT_DEFS, ...EXTRA_FILTER_DEFS];
  activeFilters.forEach(f => {
    const td = allFilterDefs.find(d => d.key === f.trait);
    const label = td ? td.label : f.trait;
    pills.push(`<span class="filter-pill">${label} ${f.op} ${f.value}
      <button class="filter-pill-remove" data-action="remove-filter" data-id="${f.id}">✕</button></span>`);
  });

  el.innerHTML = pills.join('');
  el.style.display = pills.length ? 'flex' : 'none';

  el.querySelectorAll('.filter-pill-remove').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const action = btn.dataset.action;
      if (action === 'clear-preset') { activePreset = null; syncPresetDropdownUI(); }
      else if (action === 'clear-fav') { favOnly = false; document.getElementById('btn-favonly').classList.remove('active'); }
      else if (action === 'clear-tier') { activeTier = 'all'; document.querySelectorAll('.tier-tab').forEach(t => { t.classList.toggle('active', t.dataset.tier === 'all'); }); }
      else if (action === 'clear-badge') { activeBadgeFilter = null; }
      else if (action === 'remove-filter') {
        const id = parseInt(btn.dataset.id);
        activeFilters = activeFilters.filter(f => f.id !== id);
        syncFilterRulesUI();
      }
      applyAndRender();
    });
  });
}

/* ══════════════════════════════════════════════════════
   PRESET VIEWS DROPDOWN
══════════════════════════════════════════════════════ */
function wirePresetDropdown() {
  const btn = document.getElementById('btn-presets');
  const dd  = document.getElementById('preset-dropdown');

  btn.addEventListener('click', e => {
    e.stopPropagation();
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
  });
  document.addEventListener('click', () => { dd.style.display = 'none'; });

  dd.querySelectorAll('.preset-item:not(#btn-toggle-vfd)').forEach(item => {
    item.addEventListener('click', e => {
      e.stopPropagation();
      const preset = item.dataset.preset;
      if (activePreset === preset) {
        activePreset = null;
      } else {
        activePreset = preset;
        const vp = VIEW_PRESETS[preset];
        if (vp?.sort) { sortCol = vp.sort.col; sortDir = vp.sort.dir; }
        if (vp?.favOnly) { favOnly = true; document.getElementById('btn-favonly').classList.add('active'); }
        if (vp?.tierFilter) {
          activeTier = vp.tierFilter;
          document.querySelectorAll('.tier-tab').forEach(t => t.classList.toggle('active', t.dataset.tier === vp.tierFilter));
        }
      }
      syncPresetDropdownUI();
      dd.style.display = 'none';
      applyAndRender();
    });
  });

  document.getElementById('btn-toggle-vfd')?.addEventListener('click', e => {
    e.stopPropagation();
    showVfdCol = !showVfdCol;
    syncVfdColumn();
    dd.style.display = 'none';
  });
}

function syncVfdColumn() {
  const table = document.getElementById('player-table');
  if (table) table.classList.toggle('hide-vfd', !showVfdCol);
  const btn = document.getElementById('btn-toggle-vfd');
  if (btn) btn.textContent = showVfdCol ? 'VFD Column ✓' : 'VFD Column ○';
}

function syncPresetDropdownUI() {
  document.querySelectorAll('.preset-item:not(#btn-toggle-vfd)').forEach(item => {
    item.classList.toggle('active', item.dataset.preset === activePreset);
  });
  document.getElementById('btn-presets').classList.toggle('active', !!activePreset);
}

/* ══════════════════════════════════════════════════════
   RESET ALL
══════════════════════════════════════════════════════ */
function resetAll() {
  searchQuery = '';
  activeTier  = 'all';
  favOnly     = false;
  activeFilters = [];
  activePreset  = null;
  activeBadgeFilter = null;
  sortCol = 'rank';
  sortDir = 1;
  allowImputedInFilters = VENUEDNA_CONFIG.allowImputedInFiltersDefault;

  document.getElementById('search-input').value = '';
  document.getElementById('search-clear').style.display = 'none';
  document.getElementById('btn-favonly').classList.remove('active');
  document.querySelectorAll('.tier-tab').forEach(t => t.classList.toggle('active', t.dataset.tier === 'all'));
  syncFilterRulesUI();
  syncPresetDropdownUI();
  applyAndRender();
}

/* ══════════════════════════════════════════════════════
   AP FLAG HELPERS
══════════════════════════════════════════════════════ */
function cleanConviction(raw) {
  if (!raw) return '';
  return raw;
}

function cleanDisplayKey(raw) {
  if (!raw) return '';
  const norm = raw.toLowerCase().replace(/-/g, '_');
  const tr = TRAIT_KEY_MAP[norm];
  if (tr) return tr.label;
  const ap = AP_META[norm];
  if (ap) return ap.label;
  return raw.replace(/_/g, ' ').replace(/-/g, ' ');
}

function cleanRawKeys(text) {
  if (!text) return '';
  return text.replace(/\b([A-Z]{2,3}_[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*)\b/g, match => {
    const def = TRAIT_KEY_MAP[match.toLowerCase().replace(/-/g, '_')];
    return def ? def.label : match;
  });
}

/* Replace raw model notation in engine-generated summary strings for display */
function cleanSummaryText(text) {
  if (!text) return '';
  return text
    .replace(/\bNeutralSkill\b/g, 'Neutral Skill')
    .replace(/\bVenueFit\b/g, 'Venue Fit')
    .replace(/\bVenueHistory\b/g, 'Course History')
    .replace(/\brenaissance-debut\b/gi, 'Renaissance Debut')
    .replace(/\bweak-ARG\b/gi, 'Weak Short Game')
    .replace(/\bweak-APP\/no-CH\b/gi, 'Weak Approach / No Course History')
    .replace(/\bacc-neg\/app-neg\b/gi, 'Negative Accuracy + Approach')
    .replace(/\bbomb-and-spray\b/gi, 'Bomb & Spray')
    .replace(/\|ANTI-PATTERN\b/g, '')
    .replace(/\bANTI-PATTERN\b/g, '')
    .replace(/\|/g, ', ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function apTagsHTML(flagStr) {
  if (!flagStr || !flagStr.trim() || flagStr === 'none') return '';
  return flagStr.split(';').map(f => {
    const key = f.trim().toLowerCase();
    const meta = AP_META[key];
    if (meta) {
      return `<span class="ap-tag ${meta.cls}" title="${meta.tip}">${meta.label}<span class="ap-tooltip">${meta.tip}</span></span>`;
    }
    if (!f.trim()) return '';
    return `<span class="ap-tag">${cleanDisplayKey(f.trim())}</span>`;
  }).join('');
}

function confAdjFlagHTML(p) {
  const raw = p.vts_raw ?? +p.vts_final;
  const adj = p.vts_conf_adj ?? raw;
  if (VENUEDNA_CONFIG.confidencePenaltyMode === 'none' || adj >= raw) return '';
  const trigger = p.has_unknown ? 'unknown trait' : 'imputed trait';
  return `<span class="ap-tag ap-tag-conf-adj" title="VTS adjusted from ${raw.toFixed(1)} → ${adj.toFixed(1)} (${trigger})">VTS adj</span>`;
}

/* ══════════════════════════════════════════════════════
   VTS BAR + TIER BADGE
══════════════════════════════════════════════════════ */
function vtsBarHTML(vts) {
  const pct = Math.min(100, Math.max(0, vts)).toFixed(0);
  return `<div class="vts-bar-wrap">
    <div class="vts-bar-bg"><div class="vts-bar-fill" style="width:${pct}%"></div></div>
    <span class="vts-num">${(+vts).toFixed(1)}</span>
  </div>`;
}

function tierBadgeHTML(tier) {
  const label = TIER_LABELS[tier] || '';
  return `<span class="tier-badge t${tier}" title="Tier ${tier}: ${label}">T${tier}</span>`;
}

function vfdFitHTML(p) {
  /* For Scottish Open, display venue_fit_score as a percentile (0-100) */
  const vfs = p.venue_fit_score;
  if (vfs == null || vfs === 0) return '<span class="prob-na">—</span>';
  const v = +vfs;
  let color = v >= 65 ? '#4ade80' : v >= 45 ? '#fcd34d' : '#f87171';
  const tip = 'Venue Fit Score (0-100 percentile): course-specific fit based on trait alignment with Renaissance Club requirements.';
  return `<span style="color:${color};font-size:.8rem;font-weight:600" title="${tip}">${v.toFixed(1)}</span>`;
}

function vtsDisplayHTML(p) {
  const raw = p.vts_raw ?? +p.vts_final;
  const adj = p.vts_conf_adj ?? raw;
  const hasAdj = VENUEDNA_CONFIG.confidencePenaltyMode !== 'none' && adj < raw;
  const rawPct  = Math.min(100, Math.max(0, raw)).toFixed(0);
  const dragPct = hasAdj ? Math.round((1 - adj / raw) * 100) : 0;

  return `<div class="vts-bar-wrap">
    <div class="vts-bar-bg"><div class="vts-bar-fill" style="width:${rawPct}%"></div></div>
    <div class="vts-nums">
      <span class="vts-num">${raw.toFixed(1)}</span>
      ${hasAdj ? `<span class="vts-adj-num" title="Conf-adjusted (${dragPct}% drag)">→ ${adj.toFixed(1)}</span>` : ''}
    </div>
  </div>`;
}

function playerDataBadgeHTML(p) {
  if (!p.has_imputed && !p.has_unknown) return '';
  const band = p.confidence_band;
  let label, cls;
  if (p.has_unknown) {
    label = 'UNKNOWN'; cls = 'badge-imputed badge-imputed-low';
  } else if (band === 'low') {
    label = 'LOW CONF'; cls = 'badge-imputed badge-imputed-low';
  } else if (band === 'medium') {
    label = 'IMPUTED'; cls = 'badge-imputed badge-imputed-medium';
  } else {
    label = 'IMPUTED'; cls = 'badge-imputed badge-imputed-slight';
  }
  const tooltip = [...(p.unknown_traits||[]).map(t => `✗ ${t.label}: no data`),
                   ...(p.imputed_traits||[]).map(t => `~ ${t.label}: ${t.imputed_value} (${t.from?.replace(/_/g,' ')})`)
                  ].join('\n');
  return `<span class="${cls}" title="${tooltip}">${label}</span>`;
}

/* ══════════════════════════════════════════════════════
   MODAL — player detail
══════════════════════════════════════════════════════ */
function openModal(p, brief) {
  const overlay = document.getElementById('modal-overlay');
  const displayName = p.first_name && p.last_name
    ? `${p.first_name} ${p.last_name}`
    : p.player_name.split(', ').reverse().join(' ').trim();

  document.getElementById('modal-player-name').textContent = displayName;
  document.getElementById('modal-player-sub').innerHTML =
    `${tierBadgeHTML(p.tier)} &nbsp; VTS ${(+p.vts_final).toFixed(1)} &nbsp;·&nbsp; ${p.best_betting_lane || 'Pre-Tournament'}`;

  const b = brief || {};
  const body = document.getElementById('modal-body');
  body.innerHTML = [
    sectionProbability(p),
    sectionPlayerBadges(p),
    sectionDarkHorseThesis(p),
    sectionBriefSummaries(p, b),
    sectionTraitBars(p.trait_scores),
    sectionTopDragTraits(p, b),
    sectionAntiPattern(p, b),
    sectionRiskFailure(p),
    sectionConviction(p, b),
    sectionDecomposition(p),
    sectionDbMetrics(p),
  ].join('');

  overlay.classList.add('open');
  body.querySelector('.audit-toggle')?.addEventListener('click', function() {
    const panel = body.querySelector('.audit-panel');
    const open  = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    this.textContent = open ? '▶ Score decomposition' : '▼ Score decomposition';
  });

  /* Modal badge click → close modal, activate badge filter */
  body.addEventListener('click', e => {
    if (e.target.classList.contains('player-badge-link')) {
      const badge = e.target.dataset.badge;
      if (badge) {
        activeBadgeFilter = activeBadgeFilter === badge ? null : badge;
        overlay.classList.remove('open');
        applyAndRender();
      }
    }
  });
}

function wireModalClose() {
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget || e.target.classList.contains('modal-close')) {
      document.getElementById('modal-overlay').classList.remove('open');
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.getElementById('modal-overlay').classList.remove('open');
      document.getElementById('compare-modal-overlay').style.display = 'none';
    }
  });
}

function isModalOpen() {
  return document.getElementById('modal-overlay').classList.contains('open') ||
    document.getElementById('compare-modal-overlay').style.display !== 'none';
}

/* ── Modal sections ── */
function sectionProbability(p) {
  const raw = p.vts_raw ?? +p.vts_final;

  /* Betting lane chip */
  const laneColors = {
    'Winner':  'background:#16a34a33;border-color:#16a34a;color:#86efac',
    'Top 5':   'background:#1d4ed833;border-color:#1d4ed8;color:#93c5fd',
    'Top 10':  'background:#7c3aed33;border-color:#7c3aed;color:#c4b5fd',
    'Top 20':  'background:#d9770633;border-color:#d97706;color:#fcd34d',
    'Make Cut':'background:#33415533;border-color:#475569;color:#94a3b8',
  };
  const lane = p.best_betting_lane || '';
  const laneStyle = laneColors[lane] || 'background:#33415533;border-color:#475569;color:#94a3b8';
  const laneChip = lane ? `<span style="${laneStyle};border:1px solid;border-radius:999px;padding:.2rem .8rem;font-size:.72rem;font-weight:700">${lane}</span>` : '';

  // Recalibrated thresholds: T1≈88%, T2≈69%, T3≈43% (logistic center=55, slope=12)
  const cutColor = +p.make_cut_prob >= 70 ? '#4ade80' : +p.make_cut_prob >= 45 ? '#fcd34d' : '#f87171';

  // Latent score pills — render if WCS is populated (now always true after merged-object fix)
  const hasLatent = +p.win_ceiling_score > 0;
  const latentRow = hasLatent ? `
    <div class="stat-row" style="margin-top:.4rem;opacity:.8">
      <span class="stat-pill" title="Win Ceiling Score — venue history wins + peak form"><span class="sk">WCS:</span> <span class="sv" style="color:#a78bfa">${(+p.win_ceiling_score).toFixed(1)}</span></span>
      <span class="stat-pill" title="Contention Score — approach fit + skill; drives T5/T10"><span class="sk">CS:</span> <span class="sv" style="color:#60a5fa">${(+p.contention_score).toFixed(1)}</span></span>
      <span class="stat-pill" title="Floor Score — balanced consistency; drives T10/T20"><span class="sk">FS:</span> <span class="sv" style="color:#34d399">${(+p.floor_score).toFixed(1)}</span></span>
      <span class="stat-pill" title="Cut Survival Score — NSI dominant; calibrated to top-65 cut rule"><span class="sk">CSS:</span> <span class="sv" style="color:${cutColor}">${(+p.cut_survival_score).toFixed(1)}</span></span>
    </div>` : '';

  const scoring = computeProjectedScoring(p);
  const scoringRow = `
    <div class="stat-row" style="margin-top:.4rem;opacity:.8">
      <span class="stat-pill" title="Expected 4-round score vs par — model median outcome. Lower = better in golf.">
        <span class="sk">Expected:</span> <span class="sv">${scoring.expected}</span>
      </span>
      <span class="stat-pill" title="Ceiling: best-case 4-round score — form spike + ideal conditions (5 shots better than expected)">
        <span class="sk">Ceiling:</span> <span class="sv" style="color:#4ade80">${scoring.ceiling}</span>
      </span>
      <span class="stat-pill" title="Floor: worst-case 4-round score — approach regression or adverse conditions (7 shots worse than expected)">
        <span class="sk">Floor:</span> <span class="sv" style="color:#f87171">${scoring.floor}</span>
      </span>
      <span class="stat-pill" title="Expected finish band based on probability distribution">
        <span class="sk">Band:</span> <span class="sv" style="color:#94a3b8">${scoring.band}</span>
      </span>
    </div>`;

  return `<div class="modal-section">
    <h4>Probability &amp; Output</h4>
    <div class="stat-row">
      <span class="stat-pill"><span class="sk">VTS:</span> <span class="sv" style="color:var(--accent)">${raw.toFixed(1)}</span></span>
      <span class="stat-pill"><span class="sk">Win:</span> <span class="sv">${fmtPct(p.win_pct)}</span></span>
      <span class="stat-pill"><span class="sk">Top 5:</span> <span class="sv">${fmtPct(p.top5_pct)}</span></span>
      <span class="stat-pill"><span class="sk">Top 10:</span> <span class="sv">${fmtPct(p.top10_pct)}</span></span>
      <span class="stat-pill"><span class="sk">Top 20:</span> <span class="sv">${fmtPct(p.top20_pct)}</span></span>
      <span class="stat-pill"><span class="sk">Make Cut:</span> <span class="sv" style="color:${cutColor}">${fmtPct(p.make_cut_prob)}</span></span>
      <span class="stat-pill"><span class="sk">Miss Cut:</span> <span class="sv" style="color:${cutColor === '#4ade80' ? '#f87171' : '#94a3b8'}">${fmtPct(p.miss_cut_prob)}</span></span>
    </div>
    ${latentRow}
    ${scoringRow}
    ${laneChip ? `<div style="margin-top:.5rem">${laneChip}</div>` : ''}
    <div style="margin-top:.75rem">${buildBettingStrip(p)}</div>
  </div>`;
}

function buildBettingStrip(p) {
  const wp  = +p.win_pct   || +p.win_prob   || 0;
  const t5  = +p.top5_pct  || +p.top5_prob  || 0;
  const t10 = +p.top10_pct || +p.top10_prob || 0;
  const t20 = +p.top20_pct || +p.top20_prob || 0;
  const mc  = +p.make_cut_prob || 0;
  const isc = +p.miss_cut_prob || 0;

  const lanes = [
    { label: 'Winner',   val: wp,  green: 4.0, amber: 2.5 },
    { label: 'Top 5',    val: t5,  green: 20,  amber: 12  },
    { label: 'Top 10',   val: t10, green: 35,  amber: 20  },
    { label: 'Top 20',   val: t20, green: 55,  amber: 35  },
    { label: 'Make Cut', val: mc,  green: 70,  amber: 45  },
    { label: 'Miss Cut', val: isc, green: 40,  amber: 25, invert: true },
  ];

  const cells = lanes.map(({ label, val, green, amber, invert }) => {
    let status, color;
    if (!invert) {
      status = val >= green ? 'STRONG' : val >= amber ? 'VIABLE' : 'THIN';
      color  = val >= green ? '#4ade80' : val >= amber ? '#fcd34d' : '#f87171';
    } else {
      status = val >= green ? 'DANGER' : val >= amber ? 'WATCH' : 'SAFE';
      color  = val >= green ? '#f87171' : val >= amber ? '#fcd34d' : '#4ade80';
    }
    return `<div class="bet-lane-cell">
      <div class="bet-lane-label">${label}</div>
      <div class="bet-lane-val" style="color:${color}">${val > 0 ? fmtPct(val) : '—'}</div>
      <div class="bet-lane-status" style="color:${color};font-size:.62rem">${status}</div>
    </div>`;
  }).join('');

  return `<div class="bet-strip">${cells}</div>`;
}

function sectionBriefSummaries(p, b) {
  const sections = [
    ['Neutral Skill', p.neutral_skill_summary || b.neutral_skill_summary],
    ['Venue Fit', p.venue_fit_summary || b.venue_fit_summary],
    ['Course History', p.venue_history_summary || b.venue_history_summary],
    ['Form', p.form_summary || b.form_summary],
  ].filter(([, text]) => text && text.trim());

  if (sections.length === 0) return '';
  return `<div class="modal-section">
    <h4>Player Analysis</h4>
    ${sections.map(([label, text]) =>
      `<div style="margin-bottom:.65rem">
        <div style="font-size:.72rem;font-weight:600;color:var(--accent);margin-bottom:.15rem;text-transform:uppercase;letter-spacing:.04em">${label}</div>
        <div style="font-size:.78rem;color:var(--muted);line-height:1.55">${cleanSummaryText(text)}</div>
      </div>`
    ).join('')}
  </div>`;
}

function sectionTraitBars(traits) {
  if (!traits || traits.length === 0) return '';
  const validTraits = traits.filter(t => t.score != null);
  if (validTraits.length === 0) return '';
  const sorted = [...validTraits].sort((a,b) => b.weight - a.weight);

  const bars = sorted.map(t => {
    const score   = t.score != null ? +t.score : null;
    const display = score != null ? score : 0;
    const pct     = Math.min(100, Math.max(0, display)).toFixed(0);
    const percs   = fieldTraitPercentiles[t.key] || { p40: 40, p75: 65 };
    const cls     = display >= percs.p75 ? 'bar-elite' : display >= percs.p40 ? 'bar-ok' : 'bar-weak';
    const imputedCls  = t.imputed ? ' bar-imputed' : '';
    const imputedTag  = t.imputed
      ? `<span class="trait-imputed-tag" title="Imputed from ${t.imputed_from?.replace('_',' ')}">~</span>`
      : '';
    const scoreDisplay = score != null ? display.toFixed(0) : '—';

    return `<div class="trait-row${t.imputed ? ' trait-row-imputed' : ''}">
      <div class="trait-name" title="${t.label}">${t.label}${imputedTag}</div>
      <div class="trait-bar-wrap">
        <div class="trait-bar-bg">
          <div class="trait-bar-fill ${cls}${imputedCls}" style="width:${pct}%"></div>
        </div>
        <span class="trait-score${t.imputed ? ' imputed-score' : ''}">${scoreDisplay}</span>
        <span class="trait-pct-rank">${t.imputed ? `~${t.imputed_from?.split('_').slice(0,2).join('-')}` : ''}</span>
      </div>
      <div class="trait-weight">${Math.round(t.weight*100)}%</div>
    </div>`;
  }).join('');

  return `<div class="modal-section">
    <h4>Trait Profile — Venue Weight × Player Score</h4>
    <div class="trait-legend">
      <span class="tl-item bar-elite-swatch"></span><span>Top 25% elite</span>
      <span class="tl-item bar-ok-swatch"></span><span>Mid-field ok</span>
      <span class="tl-item bar-weak-swatch"></span><span>Bottom 40% drag</span>
    </div>
    <div class="trait-bars">${bars}</div>
  </div>`;
}

function sectionTopDragTraits(p, b) {
  const tops  = p.top_traits  || b.top_traits  || [];
  const drags = p.drag_traits || b.drag_traits || [];
  if (tops.length === 0 && drags.length === 0) return '';
  const topHTML  = tops.filter(t => t && t !== 'No material drag traits').map(t => `<li class="fit-pos">✓ ${t}</li>`).join('');
  const dragHTML = drags.filter(t => t && t !== 'No material drag traits').map(t => `<li class="fit-drag">✗ ${t}</li>`).join('');
  return `<div class="modal-section">
    <h4>Trait Drivers</h4>
    <ul class="fit-list">
      ${topHTML || '<li class="fit-pos" style="opacity:.5">No positive separators identified</li>'}
      ${dragHTML}
    </ul>
  </div>`;
}

function sectionAntiPattern(p, b) {
  const summary = p.anti_pattern_summary || b.anti_pattern_summary || '';
  const flags   = p.anti_pattern_flags   || '';
  if (!summary && !flags) return '';
  return `<div class="modal-section">
    <h4>Anti-Pattern Analysis</h4>
    ${flags && flags !== 'none' ? `<div style="margin-bottom:.4rem">${apTagsHTML(flags)}</div>` : ''}
    ${summary ? `<p style="font-size:.78rem;color:var(--muted);line-height:1.55">${cleanSummaryText(summary)}</p>` : ''}
  </div>`;
}

function sectionRiskFailure(p) {
  const riskVec  = p.risk_vector        || '';
  const failure  = p.failure_condition  || '';
  if (!riskVec && !failure) return '';
  return `<div class="modal-section">
    <h4>Risk Vector &amp; Failure Condition</h4>
    ${riskVec ? `<div class="stat-row"><span class="stat-pill"><span class="sk">Risk:</span> <span class="sv">${riskVec}</span></span></div>` : ''}
    ${failure ? `<p class="risk-text" style="margin-top:.4rem">${cleanRawKeys(failure)}</p>` : ''}
  </div>`;
}

function sectionConviction(p, b) {
  const pp = (p && typeof p === 'object') ? p : {};
  const bb = (b && typeof b === 'object') ? b : {};
  const fallback = pp.conviction_statement || bb.conviction_statement || '';
  const hasNew = pp.structural_edge || pp.win_path || pp.failure_mode || pp.betting_use;
  if (hasNew) {
    const level = pp.conviction_level || '';
    const levelSlug = level.toLowerCase().replace(/[^a-z]/g, '-');
    const levelBadge = level
      ? ` &nbsp;<span class="conv-level conv-level-${levelSlug}">${level}</span>`
      : '';
    const rows = [
      ['Structural Edge', pp.structural_edge],
      ['Win Path',        pp.win_path],
      ['Failure Mode',    pp.failure_mode],
      ['Betting Use',     pp.betting_use],
      ['Market Misread',  pp.market_misread],
    ].filter(([, v]) => v)
     .map(([k, v]) => `<div class="conv-row"><span class="conv-key">${k}</span><span class="conv-body">${v}</span></div>`)
     .join('');
    return `<div class="modal-section"><h4>Intelligence${levelBadge}</h4><div class="conv-grid">${rows}</div></div>`;
  }
  if (!fallback) return '';
  return `<div class="modal-section"><h4>Conviction</h4><p>${fallback}</p></div>`;
}

function sectionDecomposition(p) {
  const d = p.decomposition || {};
  if (!d.trace_notes) return '';
  const rows = [
    ['NSI',                fmtNum(d.neutral_skill_index)],
    ['Venue Fit Score',    fmtNum(d.venue_fit_delta)],
    ['Venue History',      fmtNum(d.venue_history_delta)],
    ['Form Score',         fmtNum(d.form_score)],
    ['Penalties',          fmtNum(d.penalties || 0)],
    ['VTS Final',          fmtNum(p.vts_final)],
  ];
  const pills = rows.map(([k,v]) =>
    `<span class="stat-pill small"><span class="sk">${k}:</span> <span class="sv">${v}</span></span>`
  ).join('');
  return `<div class="modal-section audit-section">
    <button class="audit-toggle">▶ Score decomposition</button>
    <div class="audit-panel" style="display:none">
      <div class="stat-row">${pills}</div>
      ${d.trace_notes ? `<div class="trace-box">${d.trace_notes}</div>` : ''}
    </div>
  </div>`;
}

function sectionDbMetrics(p) {
  const metrics = [
    { key: 'tvl_score',  label: 'TVL (OTT 12m)',    tip: 'SG:OTT 12-month — off-tee consistency; drives fairway finding on tight links corridors' },
    { key: 'hew_score',  label: 'HEW (BallStr 6m)', tip: 'Ball Striking composite 6-month — tee-to-green quality indicator from DataGolf DB' },
    { key: 'brie_score', label: 'BRIE (APP 24m)',   tip: 'SG:APP 24-month — approach precision; primary Renaissance scoring driver from DB' },
    { key: 'vfr_score',  label: 'VFR (ARG 6m)',     tip: 'SG:ARG 6-month — around-green adaptability; links rough recovery from DB' },
  ];
  const hasAny = metrics.some(m => p[m.key] != null && !isNaN(p[m.key]));
  if (!hasAny) return '';
  const pills = metrics.map(({ key, label, tip }) => {
    const v = p[key];
    const fmt = (v != null && !isNaN(+v)) ? (+v >= 0 ? '+' : '') + (+v).toFixed(2) : '—';
    const color = (v != null && !isNaN(+v)) ? (+v >= 0.2 ? '#4ade80' : +v >= 0 ? '#fcd34d' : '#f87171') : '#94a3b8';
    return `<span class="stat-pill small" title="${tip}"><span class="sk">${label}:</span> <span class="sv" style="color:${color}">${fmt}</span></span>`;
  }).join('');
  return `<div class="modal-section">
    <h4>DB Metric Signals</h4>
    <div class="stat-row">${pills}</div>
  </div>`;
}

/* Modal badges — grouped by type (fit / ceiling / risk), all badges shown, clickable to filter */
function sectionPlayerBadges(p) {
  const badges = p.badges || [];
  if (badges.length === 0) return '';
  const TYPE_ORDER  = { fit: 0, ceiling: 1, risk: 2, misc: 3 };
  const GROUP_LABEL = { fit: 'Style / Fit', ceiling: 'Ceiling', risk: 'Risk', misc: 'Other' };
  const groups = {};
  badges.forEach(b => {
    const type = classifyBadge(b).type;
    (groups[type] = groups[type] || []).push(b);
  });
  const html = Object.keys(groups)
    .sort((a, b) => (TYPE_ORDER[a] ?? 9) - (TYPE_ORDER[b] ?? 9))
    .map(type => {
      const pills = groups[type].map(b => {
        const { color, tooltip } = classifyBadge(b);
        return `<span class="player-badge player-badge-link modal-badge" data-badge="${b}" title="${tooltip}" style="background:${color}22;border:1px solid ${color};color:${color}">${b}</span>`;
      }).join('');
      return `<div class="badge-group"><span class="badge-group-label">${GROUP_LABEL[type] || type}</span><div class="badge-group-pills">${pills}</div></div>`;
    }).join('');
  return `<div class="modal-section"><h4>Badges</h4><div class="badge-groups">${html}</div></div>`;
}

/* Dark Horse Thesis — Tier 3 only: answers the 4 structural questions for casual and sharp users */
function sectionDarkHorseThesis(p) {
  if (p.tier !== 3) return '';
  const nsi = +p.neutral_skill_index || 0;
  const vfs = +p.venue_fit_score || 0;
  const wcs = +p.win_ceiling_score || 0;

  /* Q1: Why can he win here */
  const q1 = (p.top_traits || [])[0]
    || `Venue fit score ${vfs.toFixed(1)}/100 — approach profile matches the Renaissance 150-200yd scoring zone`;

  /* Q2: Structural ceiling mechanism */
  let q2;
  if (wcs >= 78)      q2 = `Win Ceiling Score ${wcs.toFixed(1)} — elite ceiling; venue history or a form spike can produce a top-5 result from this field position`;
  else if (wcs >= 72) q2 = `Win Ceiling Score ${wcs.toFixed(1)} — elevated ceiling; one primary-trait fire above baseline is sufficient for contention`;
  else if (nsi >= 70) q2 = `Elite neutral skill (NSI ${nsi.toFixed(1)}) — world-class ball-striking creates ceiling on any course; venue history is the constraint, not skill`;
  else if (vfs >= 62) q2 = `Venue Fit Score ${vfs.toFixed(1)} — approach pattern structurally matched to Renaissance 150-200yd zone; fit can compensate for limited history sample`;
  else                q2 = `Win Ceiling Score ${wcs.toFixed(1)} — ceiling constrained; requires simultaneous multi-trait fire; high-variance outcome range`;

  /* Q3: What must spike */
  const drag = (p.drag_traits || [])[0];
  let q3;
  if (drag) {
    q3 = drag; /* Specific structural weakness is the most accurate answer */
  } else if (p.flag_count > 0) {
    q3 = `Anti-pattern flag(s) must not activate — ${p.anti_pattern_flags || 'course-specific structural weakness present'}`;
  } else if (/form (cool|cold)/i.test(p.form_summary || '')) {
    q3 = 'Form must recover to baseline — current below-average pace must mean-revert for ceiling to open';
  } else {
    q3 = 'Approach game from 150-200yds must hold above +0.3 SG for the week — this is the dominant scoring zone at Renaissance';
  }

  /* Q4: Why market may underrate */
  const vhText   = (p.venue_history_summary || '').toLowerCase();
  const isThin   = vhText.includes('thin') || /\b[12] start/.test(vhText) || vhText.includes('debut');
  const isCool   = /form (cool|cold)/i.test(p.form_summary || '');
  const hasLowNsi = nsi < 55;
  let q4;
  if (p.debut_flag || vhText.includes('debut')) {
    q4 = `Debut at The Renaissance Club — market has no venue history to anchor price; debut CSS penalty already applied in the model; structural fit profile is intact`;
  } else if (isThin) {
    q4 = `Thin venue sample creates market uncertainty; model already discounts through VHN score — if approach fit holds, the market gap widens`;
  } else if (isCool) {
    q4 = `Below-baseline recent form suppresses market price; structural profile unchanged — form regression is mean-reverting, not a structural deficit at links venues`;
  } else if (hasLowNsi) {
    q4 = `Below-median neutral skill (NSI ${nsi.toFixed(1)}) creates market skepticism; venue fit and course history create a compensating edge the raw-skill market doesn't price`;
  } else {
    q4 = `DP World Tour co-sanctioned field — market pricing often underweights DP Tour regulars with established Renaissance history vs. PGA Tour-only comparables`;
  }

  return `<div class="modal-section dh-thesis-section">
    <h4>Dark Horse Thesis</h4>
    <div class="dh-thesis-grid">
      <div class="dh-thesis-item"><div class="dh-thesis-q">Why can he win here?</div><div class="dh-thesis-a">${q1}</div></div>
      <div class="dh-thesis-item"><div class="dh-thesis-q">Structural ceiling mechanism</div><div class="dh-thesis-a">${q2}</div></div>
      <div class="dh-thesis-item"><div class="dh-thesis-q">What must spike?</div><div class="dh-thesis-a">${q3}</div></div>
      <div class="dh-thesis-item"><div class="dh-thesis-q">Why market may underrate</div><div class="dh-thesis-a">${q4}</div></div>
    </div>
  </div>`;
}

/* ══════════════════════════════════════════════════════
   BRIEF CARDS (T1 + T2)
══════════════════════════════════════════════════════ */
function renderBriefs() {
  const grid = document.querySelector('.brief-grid');
  const section = document.querySelector('.brief-section h2');
  if (section) section.textContent = 'Tier 1 & 2 Spotlight';

  const t1t2 = allPlayers.filter(p => p.tier <= 2).slice(0, 12);
  if (t1t2.length === 0) {
    grid.innerHTML = '<p style="color:var(--muted);font-size:.8rem">No Tier 1/2 players found.</p>';
    return;
  }

  grid.innerHTML = t1t2.map(p => {
    const tc = p.tier <= 2 ? `t${p.tier}-card` : '';
    const displayName = p.first_name && p.last_name
      ? `${p.first_name} ${p.last_name}`
      : p.player_name.split(', ').reverse().join(' ').trim();

    const topTraitsHTML = (p.top_traits || [])
      .filter(t => t && t !== 'No material drag traits')
      .slice(0, 3)
      .map(t => `<li class="fit-pos">${t}</li>`)
      .join('') || '<li class="fit-pos" style="opacity:.5">Profile loading...</li>';

    const cutColor = +p.make_cut_prob >= 75 ? '#4ade80' : +p.make_cut_prob >= 55 ? '#fcd34d' : '#f87171';

    const badgesHTML = renderPlayerBadges(p.badges);

    return `<div class="brief-card ${tc}" style="cursor:pointer" data-player-name="${p.player_name}">
      <div class="brief-name">${displayName} ${tierBadgeHTML(p.tier)} ${badgesHTML}</div>
      <div class="brief-stats">VTS ${(+p.vts_final).toFixed(1)} · Win ${fmtPct(p.win_pct)} · T5 ${fmtPct(p.top5_pct)} · T10 ${fmtPct(p.top10_pct)} · Cut <span style="color:${cutColor}">${fmtPct(p.make_cut_prob)}</span></div>
      <div class="brief-label">Key Strengths (Links/Renaissance Fit)</div>
      <ul class="fit-list fit-compact">${topTraitsHTML}</ul>
      <div class="brief-label">Course History</div>
      <div class="brief-val">${cleanSummaryText(p.venue_history_summary) || '—'}</div>
      <div class="brief-label">${p.structural_edge ? 'Structural Edge' : 'Conviction'}</div>
      <div class="brief-val">${p.structural_edge || p.conviction_statement || '—'}</div>
      ${(p.failure_mode || p.failure_condition) ? `<div class="brief-risk">${p.failure_mode ? cleanRawKeys(p.failure_mode.split('|')[0]?.trim()) : cleanRawKeys(p.failure_condition.split('|')[0]?.trim())}</div>` : ''}
    </div>`;
  }).join('');

  /* Wire click on brief cards → badge filter (if badge clicked) or modal */
  grid.addEventListener('click', e => {
    if (e.target.classList.contains('player-badge-link')) {
      const badge = e.target.dataset.badge;
      if (badge) {
        e.stopPropagation();
        activeBadgeFilter = activeBadgeFilter === badge ? null : badge;
        applyAndRender();
      }
      return;
    }
    const card = e.target.closest('.brief-card');
    if (card) {
      const name = card.dataset.playerName;
      const p = allPlayers.find(x => x.player_name === name);
      if (p) {
        const brief = briefsById[p.player_id] || briefsByNk[makeNameKey(p)];
        openModal(p, brief);
      }
    }
  });
}

/* ── Diagnostics toggle ── */
function wireDiagnosticsToggle() {
  document.getElementById('diag-toggle')?.addEventListener('click', () => {
    const panel = document.getElementById('diag-panel');
    if (!panel) return;
    const open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    document.getElementById('diag-toggle').textContent = open ? '▶ Diagnostics' : '▼ Diagnostics';
  });
}

/* ══════════════════════════════════════════════════════
   ROUND LEARNING PANEL
══════════════════════════════════════════════════════ */
function renderRoundInsights(payload) {
  const body = document.getElementById('ri-body');
  showRoundPanel('pre', body);

  const LIVE_BADGE    = ' <span class="rs-live">LIVE</span>';
  const PENDING_BADGE = ' <span class="rs-pending">—</span>';
  [['r1', r1Data, 'Round 1'], ['r2', r2Data, 'Round 2'], ['r3', r3Data, 'Round 3'], ['final', r4Data, 'Final']].forEach(([key, data, label]) => {
    const tab = document.querySelector(`.ri-tab[data-round="${key}"]`);
    if (!tab) return;
    tab.innerHTML = label + (data ? LIVE_BADGE : PENDING_BADGE);
  });

  document.querySelectorAll('.ri-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.ri-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      showRoundPanel(tab.dataset.round, body);
    });
  });
}

function showRoundPanel(round, body) {
  const roundMap = { r1: [r1Data, 1], r2: [r2Data, 2], r3: [r3Data, 3], final: [r4Data, 4] };
  if (roundMap[round]) {
    const [data, num] = roundMap[round];
    if (data) {
      try {
        renderRoundPanel(body, data, num);
      } catch (err) {
        console.error(`[VenueDNA] renderRoundPanel R${num} failed:`, err);
        body.innerHTML = `<div class="ri-card" style="color:#f87171;padding:1.5rem">
          <b>Round ${num} panel failed to render.</b><br>
          <span style="font-size:.75rem;color:var(--muted)">${err.message}</span>
        </div>`;
      }
      return;
    }
  }

  if (round === 'pre') {
    /* Pre-tournament panel: venue context */
    const ev = eventMeta.event || {};
    const weights = ev.trait_weight_matrix || {};
    const bars = Object.entries(weights).map(([k,w]) => {
      const pct = Math.round(w * 100);
      const def = TRAIT_KEY_MAP[k.replace(/-/g,'_')];
      const label = PAYLOAD_WEIGHT_LABELS[k] || (def ? def.label : k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()));
      return `<div class="ri-weight-bar">
        <span class="ri-weight-label">${label}</span>
        <div class="ri-weight-bar-bg"><div class="ri-weight-bar-fill" style="width:${pct*4}%"></div></div>
        <span class="ri-weight-pct">${pct}%</span>
      </div>`;
    }).join('');

    const topFits = allPlayers.filter(p => p.tier <= 2).slice(0,6);
    const topHTML = topFits.map(p => {
      const dName = p.first_name && p.last_name ? `${p.first_name} ${p.last_name}` : p.player_name;
      return `<div style="display:flex;justify-content:space-between;font-size:.75rem;padding:.2rem 0;border-bottom:1px solid var(--border)">
        <span>${dName} ${tierBadgeHTML(p.tier)}</span>
        <span style="color:var(--accent)">${fmtPct(p.win_pct)} win · Cut ${fmtPct(p.make_cut_prob)}</span>
      </div>`;
    }).join('');

    const compCourses = (ev.comp_courses || []).map(c =>
      `<div style="font-size:.73rem;padding:.15rem 0;border-bottom:1px solid var(--border)">
        <b>${c.name}</b> <span style="color:var(--muted);margin-left:.25rem">${c.similarity ? Math.round(c.similarity*100)+'% similarity' : ''} — ${c.note || ''}</span>
      </div>`
    ).join('');

    body.innerHTML = `
      <div class="ri-pre-grid">
        <div class="ri-card">
          <h4>Course Trait Weights — The Renaissance Club</h4>
          ${bars}
        </div>
        <div class="ri-card">
          <h4>Model Leaders</h4>
          ${topHTML}
        </div>
        <div class="ri-card">
          <h4>Comp Courses</h4>
          ${compCourses || '<p class="ri-placeholder">No comp courses listed.</p>'}
        </div>
        <div class="ri-card">
          <h4>Venue Context — Links DNA</h4>
          <div style="font-size:.75rem;color:var(--muted);line-height:1.65">
            <p>The Renaissance Club is a pure links test. Primary lever: approach from 150-200yds (30% weight). Wind exposure, firm/fast conditions, and unpredictable bounce elevate variance class to HIGH. Positional driving (20%) is rewarded over raw distance. Putting on links surfaces is regressed vs. parkland historical baselines.</p>
            <p style="margin-top:.5rem">Winner profile: consistent approach quality across 4 rounds, positive driving accuracy adjustment, reliable short game. Historical winners include Chris Gotterup (2025) — approach-dominant, stable off tee. Tournament variance is high — field spread wider than typical PGA events.</p>
            <p style="margin-top:.5rem">Cut rule: Top 65 and ties after 36 holes. Make-cut probability is a significant differentiator for volatile Tier 3/4 players.</p>
          </div>
        </div>
      </div>`;
  } else if (round === 'final') {
    body.innerHTML = `
      <div class="ri-cards">
        <div class="ri-card" style="grid-column:1/-1">
          <div style="text-align:center;padding:2rem 1rem">
            <div style="font-size:2rem;margin-bottom:.75rem">&#x1F3C1;</div>
            <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:.5rem">Final Round Data Not Yet Available</h3>
            <p style="color:var(--muted);font-size:.82rem">Round 4 data will populate here upon R4 build completion.</p>
          </div>
        </div>
      </div>`;
  } else {
    const roundLabels = { r1: 'Round 1', r2: 'Round 2', r3: 'Round 3' };
    const label = roundLabels[round] || round;
    body.innerHTML = `
      <div class="ri-cards">
        <div class="ri-card">
          <h4>Trait Winners <span class="ri-stub-badge">pending</span></h4>
          <p class="ri-placeholder">Which traits correlated with low scores in ${label}?</p>
        </div>
        <div class="ri-card">
          <h4>Model vs Realized <span class="ri-stub-badge">pending</span></h4>
          <p class="ri-placeholder">Compare predicted vs actual scoring contribution after ${label}.</p>
        </div>
        <div class="ri-card">
          <h4>Weekend Risers <span class="ri-stub-badge">pending</span></h4>
          <p class="ri-placeholder">Players outperforming VTS projection through ${label}.</p>
        </div>
        <div class="ri-card">
          <h4>Slippage Risk <span class="ri-stub-badge">pending</span></h4>
          <p class="ri-placeholder">Fragile stat profiles in the current top 20.</p>
        </div>
        <div class="ri-card">
          <h4>Favorites Tracker</h4>
          ${favorites.size > 0
            ? [...favorites].map(n => {
                const p = allPlayers.find(x => x.player_name === n);
                const dname = p && p.first_name ? `${p.first_name} ${p.last_name}` : n;
                return `<div style="font-size:.75rem;padding:.2rem 0;border-bottom:1px solid var(--border)">${dname} — <span style="color:var(--muted)">position TBD</span></div>`;
              }).join('')
            : '<p class="ri-placeholder">Star players in the field table to track them here.</p>'}
        </div>
      </div>`;
  }
}

/* Stub renderRoundPanel — populated when round analysis files are loaded */
function renderRoundPanel(body, rData, roundNum) {
  const d = rData;
  if (!d || !d.model_performance) {
    body.innerHTML = `<div class="ri-card" style="color:#f87171;padding:1.5rem">
      <b>Round ${roundNum} data is incomplete.</b><br>
      <span style="font-size:.75rem;color:var(--muted)">Missing model_performance block.</span>
    </div>`;
    return;
  }

  const mp = d.model_performance;
  const sgFmt   = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2);
  const scoreFmt = v => v == null ? '—' : v === 0 ? 'E' : (v > 0 ? '+' : '') + v.toFixed(0);
  const rho = mp.spearman_rho;
  const rhoColor = rho > 0.35 ? '#4ade80' : rho > 0.18 ? '#fcd34d' : '#f87171';

  const lbTop = (d.leaderboard_snapshot || []).slice(0, 15);
  const lbRows = lbTop.map(r => `<tr>
    <td>${r.r1_pos_str || r.r1_pos}</td>
    <td style="font-weight:600">${r.r1_name}</td>
    <td style="color:#4ade80">${scoreFmt(r.r1_score)}</td>
    <td style="color:var(--muted)">${r.pt_rank || '—'}</td>
    <td>${r.pt_tier ? `T${r.pt_tier}` : '—'}</td>
    <td>${r.pt_vts ? r.pt_vts.toFixed(1) : '—'}</td>
    <td style="color:${(r.sg_app||0)>1.0?'#4ade80':'var(--muted)'}">${sgFmt(r.sg_app)}</td>
    <td style="color:${(r.sg_putt||0)>2.0?'#fcd34d':'var(--muted)'}">${sgFmt(r.sg_putt)}</td>
    <td>${sgFmt(r.sg_arg)}</td>
    <td>${sgFmt(r.sg_ott)}</td>
  </tr>`).join('');

  const ms = d.match_summary || {};
  body.innerHTML = `
    <div class="ri-r1-layout">
      <div class="ri-r1-header">
        <span class="ri-r1-label">${d.metadata?.round_label || `Round ${roundNum}`}${d.metadata?.is_final ? ' — Final' : ' Complete'}</span>
        <span class="ri-r1-sub">${d.metadata?.course_name || 'The Renaissance Club'} · Par ${d.metadata?.par || 71}</span>
        <span class="ri-r1-meta">Built ${(d.build_timestamp || d.generated_at || '—').replace('T',' ')} · ${ms.matched ?? '?'}/${ms.total_r1 ?? '?'} matched</span>
      </div>
      <div class="ri-r1-grid">
        <div class="ri-card ri-card-wide">
          <h4>R${roundNum} Leaderboard Snapshot</h4>
          <div class="ri-lb-scroll">
            <table class="ri-lb-table">
              <thead><tr><th>Pos</th><th>Player</th><th>Score</th><th>PT Rank</th><th>Tier</th><th>VTS</th><th>SG:APP</th><th>SG:PUTT</th><th>SG:ARG</th><th>SG:OTT</th></tr></thead>
              <tbody>${lbRows}</tbody>
            </table>
          </div>
        </div>
        <div class="ri-card">
          <h4>Model Performance</h4>
          <div style="font-size:.78rem">
            <div style="padding:.25rem 0;border-bottom:1px solid var(--border)">
              <span style="color:var(--muted)">Spearman ρ:</span>
              <span style="color:${rhoColor};font-weight:700;margin-left:.4rem">${rho > 0 ? '+' : ''}${rho.toFixed(3)}</span>
            </div>
            ${Object.entries(mp.groups || {}).map(([k,g]) =>
              g ? `<div style="padding:.2rem 0;border-bottom:1px solid var(--border)">
                <span style="color:var(--muted);font-size:.72rem">${k.replace(/_/g,' ')}:</span>
                <span style="margin-left:.25rem">${g.in_r1_top10 ?? 0}/${g.n ?? 0} top10</span>
                <span style="color:var(--muted);font-size:.7rem;margin-left:.25rem">avg pos ${g.avg_r1_pos?.toFixed(0) ?? '—'}</span>
              </div>` : ''
            ).join('')}
          </div>
        </div>
      </div>
    </div>`;
}

/* ══════════════════════════════════════════════════════
   GLOSSARY MODAL
══════════════════════════════════════════════════════ */
function wireGlossaryModal() {
  const overlay = document.getElementById('glossary-modal-overlay');
  if (!overlay) return;

  document.getElementById('btn-glossary')?.addEventListener('click', () => {
    overlay.style.display = 'flex';
  });
  overlay.addEventListener('click', e => {
    if (e.target === e.currentTarget || e.target.classList.contains('modal-close')) {
      overlay.style.display = 'none';
    }
  });
}

function buildGlossaryHTML() {
  const section = (title, rows) => `
    <div class="gloss-section">
      <h4>${title}</h4>
      ${rows.map(([k, v]) => `<div class="gloss-row"><span class="gloss-key">${k}</span><span class="gloss-val">${v}</span></div>`).join('')}
    </div>`;

  return [
    section('Scores & Metrics', [
      ['VTS', 'Venue Tier Score (0–100) — composite ranking: NSI 40% + VFS 30% + VHN 15% + Form 15%.'],
      ['VFS', 'Venue Fit Score (0–100 percentile) — course-specific trait alignment at The Renaissance Club.'],
      ['NSI', 'Neutral Skill Index — baseline tour-wide skill, independent of venue or form.'],
      ['Win %', 'Model-estimated win probability for this event (all values shown to 1 decimal place).'],
      ['Top 5 %', 'Model-estimated probability of a Top 5 finish.'],
      ['Top 10 %', 'Model-estimated probability of a Top 10 finish.'],
      ['Top 20 %', 'Model-estimated probability of a Top 20 finish.'],
      ['Make Cut %', 'Probability of making the 36-hole cut (Top 65 + ties).'],
      ['CH Rds', 'Course history rounds — prior starts at The Renaissance Club. "Debut" = first start.'],
      ['Flags', 'Count of anti-pattern risk flags assigned to this player.'],
    ]),
    section('Projected Scoring (modal)', [
      ['Expected', '4-round projected score vs par — model median outcome. Lower score = better in golf.'],
      ['Ceiling', 'Best-case 4-round score: form spike + ideal conditions (~5 shots better than Expected).'],
      ['Floor', 'Worst-case 4-round score: approach regression or adverse conditions (~7 shots worse than Expected).'],
      ['Band', 'Likely finish zone based on probability distribution (Win contender / Top 5 / Top 10 / etc.).'],
    ]),
    section('Best Betting Lane', [
      ['Winner', 'Genuine outright candidate — win probability ≥3.0%. Top 5–6 players in a 166-player field.'],
      ['Top 5', 'Strong contention profile, win% 1.8–2.9% — best lane is a top-5 finish, not outright.'],
      ['Top 10', 'Solid contender with thinner winning path — T2 players with win% below 1.8%.'],
      ['Top 20', 'Viable mid-field play — T3 players with meaningful top-20 probability.'],
      ['Make Cut', 'Primary value is weekend status — cut probability is the key metric.'],
      ['Miss Cut', 'Model suggests cut is unlikely — fade or avoid.'],
      ['Pass / No Edge', 'No meaningful betting edge identified from this player\'s current profile.'],
    ]),
    section('Tiers', [
      ['T1', 'Elite course fits — highest VTS. Primary contender zone.'],
      ['T2', 'Strong fits — legitimate contention probability.'],
      ['T3', 'Moderate fits — value / mid-field plays.'],
      ['T4', 'Longshot territory — specific edge required to outperform.'],
      ['T5', 'Poor fits — significant course-profile mismatches.'],
    ]),
    section('Trait Abbreviations', [
      ['APP 150-200', 'Strokes gained on approach shots from 150–200 yards (primary scoring zone, 30%).'],
      ['OTT / Positional', 'Off-the-tee positional driving — accuracy-weighted distance (20%).'],
      ['APP Overall', 'Overall strokes gained: approach, full-field baseline (15%).'],
      ['DA', 'Driving Accuracy — % of fairways hit, expressed as adj. vs. field avg (12%).'],
      ['SG:PUTT', 'Strokes gained: putting, regressed for links surfaces (13%).'],
      ['SG:ARG', 'Strokes gained: around-the-green / short game (10%).'],
      ['TVL', 'SG:OTT (12-month) — off-tee consistency from DataGolf DB. Contributes to VFS: fairway finding on tight Renaissance corridors.'],
      ['HEW', 'Ball Striking composite (6-month) — OTT+APP combined from DataGolf DB. Measures tee-to-green quality entering the event.'],
      ['BRIE', 'SG:APP (24-month) — approach precision from DataGolf DB. Primary Renaissance scoring driver; correlates with 150-200yd zone performance.'],
      ['VFR', 'SG:ARG (6-month) — around-green adaptability from DataGolf DB. Links rough recovery and short-game resilience at Renaissance.'],
    ]),
    section('Tier Definitions', [
      ['T1 · Structural Winner', 'Full-profile match: elite NSI + strong venue fit + course history. Win probability ≥3%.'],
      ['T2 · Primary Contender', 'Strong two-of-three component match. Real contention ceiling. Top-10 most likely lane.'],
      ['T3 · Dark Horse', 'Structural ceiling exists but one component limits VTS. Win probability real but requires trait spike.'],
      ['T4 · Fragile Path', 'Thin venue history or form drag limits ceiling. Make-cut is not certain; approach must hold.'],
      ['T5 · Fade / Cut Risk', 'Profile mismatch or structural weakness. Miss-cut risk elevated. Fade or avoid in betting context.'],
    ]),
    section('Style / Fit Badges', [
      ['Defending Champ', 'Defending tournament champion — maximum venue calibration.'],
      ['Course Horse', 'Positive venue history + course-adjustment — proven scorer at The Renaissance Club.'],
      ['Iron Edge', 'Venue fit score ≥64 — approach profile optimally matched to Renaissance 150-200yd zone.'],
      ['Elite NSI', 'World-class neutral skill index (≥85) — elite ball-striking translates to any surface.'],
      ['Form Spike', 'Current scoring pace significantly above 12-month baseline — momentum confirmed.'],
    ]),
    section('Ceiling Badges', [
      ['Dark Horse', 'Win probability ≥2% from Tier 3 — structural ceiling underpriced by market.'],
      ['Ceiling Play', 'Elevated win ceiling score — one elite-trait spike can produce a top-5 result.'],
      ['Live Longshot', 'Win probability >2% from Tier 3+ — market may be underpricing this player.'],
    ]),
    section('Risk Badges', [
      ['Fragile Favorite', 'Top-2-tier player with anti-pattern flags — structural blowup risk present.'],
      ['Anti-Pattern', '2+ recurring weak-link trait flags for this venue profile.'],
      ['Cut Sweat', 'Make-cut probability below 60% — weekend status structurally uncertain.'],
      ['False Safety', 'High cut rate but near-zero win ceiling — positional trap for bettors.'],
      ['Debut Watch', 'First start at The Renaissance Club — zero venue-specific calibration.'],
      ['Volatile Putter', 'High putting variance — links fescue greens can amplify or collapse this trait.'],
      ['Form Cold', 'Scoring pace below seasonal baseline — negative momentum entering event.'],
    ]),
    section('Anti-Pattern Flags', [
      ['Bomb + Spray', 'Elite distance but below-field driving accuracy — punished at Renaissance Club placement holes.'],
      ['Approach Liability', 'Below-field in the 150–200yd zone — drag on primary scoring trait.'],
      ['Poor Links Putter', 'Below-field putting on links surfaces. Limits birdie upside.'],
      ['Long-Iron Weakness', 'Below-field in 150–200yd approach zone — highest-weighted trait.'],
      ['Debut Risk', 'No prior starts at this venue. No history adjustment applied.'],
    ]),
    section('Data Quality Badges', [
      ['OBSERVED', 'All trait scores from measured 12-month SG data.'],
      ['IMPUTED', 'One or more traits estimated from tier/field average. VTS shown as-is from pipeline.'],
      ['LOW CONF', 'Significant missing trait weight (≥20%). Confidence penalty applied.'],
      ['UNKNOWN', 'Trait data unavailable — no imputation possible. Excluded from filters.'],
      ['VTS adj', 'Confidence-adjusted display VTS shown alongside raw pipeline value.'],
    ]),
  ].join('');
}

/* ══════════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════════ */
function renderFooter(payload) {
  const ev = payload.event;
  document.querySelector('footer').innerHTML =
    `PGA VenueDNA · 2026 Genesis Scottish Open · The Renaissance Club · Model: ${ev.model_version || 'VenueDNA v2'} · Built ${new Date().toISOString().slice(0,10)}`;
}

/* ══════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════ */
function normalizeLastName(s) {
  return (s || '').toLowerCase()
    .replace(/[øØ]/g, 'o').replace(/[åÅ]/g, 'a').replace(/[æÆ]/g, 'ae')
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function fmtPct(v) {
  if (v == null || v === 'N/A' || v === 'not_applicable') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n.toFixed(1) + '%';
}

/* Derive projected 4-round scoring outputs from latent model scores.
   Par 71 × 4 rounds = 284 total. Calibrated to Renaissance Club scoring history.
   Golf convention: lower score = better performance.
     Ceiling = most-negative possible (best performance, deepest under par)
     Floor   = least-negative possible (worst likely performance, closest to par / over par) */
function computeProjectedScoring(p) {
  const wcs = +p.win_ceiling_score || 50;
  const mc  = +p.make_cut_prob || 50;
  const wp  = +p.win_prob || 0;
  const t5  = +p.top5_prob || 0;
  const t10 = +p.top10_prob || 0;
  const t20 = +p.top20_prob || 0;

  const expected_vs_par = Math.round(-22 + (100 - wcs) * 0.22);
  /* Ceiling = 5 more under par than expected (upside scenario) */
  const ceiling_vs_par  = expected_vs_par - 5;
  /* Floor   = 7 more over par than expected (downside scenario) */
  const floor_vs_par    = expected_vs_par + 7;
  const fmtVsPar = n => n === 0 ? 'E' : n > 0 ? `+${n}` : `${n}`;

  let band;
  if (wp >= 3.0) band = 'Win contender';
  else if (wp >= 1.8 || t5 >= 10.0) band = 'Top 5 contender';
  else if (t10 >= 15.0) band = 'Top 10 expected';
  else if (t20 >= 25.0) band = 'Top 20 likely';
  else if (mc >= 72.0) band = 'Solid cut maker';
  else if (mc >= 52.0) band = 'Make cut play';
  else band = 'Cut risk';

  return {
    expected: fmtVsPar(expected_vs_par),
    ceiling:  fmtVsPar(ceiling_vs_par),
    floor:    fmtVsPar(floor_vs_par),
    band,
  };
}

function fmtSigned(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toFixed(1);
}

function fmtNum(v) {
  const n = parseFloat(v);
  return isNaN(n) ? '—' : n.toFixed(2);
}

/* ── Run ── */
init().catch(err => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:2rem">
Board data failed to load. Serve this folder over HTTP, not file://.

Error: ${err.message}

Quick start:  npx serve .   or   python -m http.server 8080</pre>`;
});
