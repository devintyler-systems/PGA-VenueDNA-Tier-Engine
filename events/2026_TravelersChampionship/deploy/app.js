/* PGA VenueDNA — Travelers Championship 2026 — Interactive Dashboard */

/* ══════════════════════════════════════════════════════
   MODEL CONFIGURATION
   Edit these values to tune data-quality and scoring behavior.
   All runtime behavior reads from this object — no magic numbers elsewhere.
══════════════════════════════════════════════════════ */
const VENUEDNA_CONFIG = {
  /* ── Data quality ── */
  treatZeroAsMissing: true,
  // Scores are percentile-based (0–100). Exactly 0 is not a valid PGA Tour
  // result; it signals a missing-data sentinel. Set false only if a trait
  // genuinely allows a true-zero observed score.

  /* ── Filter behavior ── */
  allowImputedInFiltersDefault: false,
  // false (default): players with imputed or unknown trait data are EXCLUDED
  //   from threshold filters (>=, <=, =). The user can override per-session
  //   via the "Include imputed" toggle in the filter panel.
  // true: imputed scores participate in filters as if observed.
  // Players with UNKNOWN traits (imputation failed) are always excluded
  //   regardless of this setting.

  /* ── Confidence-adjusted VTS ── */
  confidencePenaltyMode: 'linear',
  // 'none'    — show raw VTS only; no adjustment applied.
  // 'linear'  — penalty = missing_trait_weight × confidencePenaltyStrength
  // 'stepped' — fixed penalty steps: slight→1%, medium→4%, low→8%

  confidencePenaltyStrength: 0.25,
  // Used in 'linear' mode. Controls how strongly missing weight suppresses the
  // display score. 0.25 is intentionally moderate:
  //   OTT_Accuracy missing (14%) → penalty 0.035 → VTS ×0.965
  //   APP_Wedge missing  (22%) → penalty 0.055 → VTS ×0.945
  //   Two traits missing (36%) → penalty 0.090 → VTS ×0.910
  // Increase toward 0.5 for more aggressive suppression.

  confidenceFloor: 0.75,
  // Minimum multiplier regardless of how much data is missing.
  // Prevents runaway suppression when many traits are imputed.
  // At 0.75, a VTS of 80 can drop no lower than 60 from imputation alone.
};

const DATA_DIR = 'data/';

/* ── Global state ── */
let allPlayers   = [];
let briefsByNk   = {};
let eventMeta    = {};

let searchQuery  = '';
let activeTier   = 'all';
let favOnly      = false;
let favorites    = new Set();
let comparePlayers = [];       // array of player objects, max 4
let sortCol      = 'rank';
let sortDir      = 1;          // 1=asc, -1=desc
let activeFilters = [];        // [{id, trait, op, value}]
let activePreset  = null;
let filterRuleCounter = 0;
let allowImputedInFilters = VENUEDNA_CONFIG.allowImputedInFiltersDefault;
let r1Data = null;         // populated from r1_analysis.json when available
let r2Data = null;         // populated from r2_analysis.json when available
let r3Data = null;         // populated from r3_analysis.json when available
let r4Data = null;         // populated from r4_analysis.json when available (Final)
let cumulativeData = null; // populated from cumulative_learning.json when available

/* ── Trait definitions (for filter panel + compare) ── */
const TRAIT_DEFS = [
  { key: 'app_wedge',      label: 'APP Wedge',        weight: 0.22 },
  { key: 'app_100_150',    label: 'APP 100-150',       weight: 0.12 },
  { key: 'app_150_200',    label: 'APP 150-200',       weight: 0.06 },
  { key: 'ott_accuracy',   label: 'OTT Accuracy',      weight: 0.14 },
  { key: 'ott_distance',   label: 'OTT Distance',      weight: 0.05 },
  { key: 'putt_short_conv',label: 'Putt Short Conv',   weight: 0.16 },
  { key: 'putt_lag',       label: 'Putt Lag',          weight: 0.10 },
  { key: 'arg_rough',      label: 'ARG Rough',         weight: 0.07 },
  { key: 'arg_bunker',     label: 'ARG Bunker',        weight: 0.05 },
  { key: 'par5_scoring',   label: 'Par-5 Scoring',     weight: 0.03 },
];

const TRAIT_KEY_MAP = Object.fromEntries(TRAIT_DEFS.map(t => [t.key, t]));

/* ══════════════════════════════════════════════════════
   MISSING-TRAIT POLICY
   Scores are percentile-style 0–100. Exactly 0 is not a
   valid PGA Tour result in any trait — it signals missing
   data stored as a sentinel, not true bottom-of-field.
══════════════════════════════════════════════════════ */

/* True if a score is real observed data — not null/NaN/sentinel-zero */
function isValidTraitScore(score) {
  if (score === null || score === undefined) return false;
  const n = +score;
  if (isNaN(n)) return false;
  if (VENUEDNA_CONFIG.treatZeroAsMissing && n === 0) return false;
  return true;
}

/*
 * getPlayerHistoricalBaseline — hook for future player-specific baseline data.
 * Return a number (0–100) to use as the first-priority imputation source,
 * or null to fall through to tier average.
 *
 * To activate: load a player_baselines.json keyed by player_name → trait_key → score
 * and look it up here. The hook sits ahead of tier average in the fallback chain.
 */
function getPlayerHistoricalBaseline(playerName, traitKey) {  // eslint-disable-line no-unused-vars
  // Future: return playerBaselines[playerName]?.[traitKey] ?? null;
  return null;
}

/*
 * computeConfidencePenalty — translate missing_trait_weight into a VTS drag fraction.
 * Returns a value in [0, 1-confidenceFloor]. The caller multiplies VTS by (1 - penalty).
 */
function computeConfidencePenalty(missingWeight) {
  if (VENUEDNA_CONFIG.confidencePenaltyMode === 'none' || missingWeight <= 0) return 0;
  const floor = VENUEDNA_CONFIG.confidenceFloor;
  let raw = 0;
  if (VENUEDNA_CONFIG.confidencePenaltyMode === 'linear') {
    raw = missingWeight * VENUEDNA_CONFIG.confidencePenaltyStrength;
  } else if (VENUEDNA_CONFIG.confidencePenaltyMode === 'stepped') {
    raw = missingWeight >= 0.20 ? 0.08
        : missingWeight >= 0.10 ? 0.04
        : 0.01;
  }
  return Math.min(raw, 1 - floor);
}

/*
 * runImputationPass — mutates each player in-place with:
 *
 *   .imputed_traits[]    successfully filled: {key, label, weight, original, imputed_value, from}
 *   .unknown_traits[]    unresolved (no fallback available): same shape, imputed_value=null
 *   .missing_trait_weight  sum of weights for ALL non-observed traits (imputed + unknown)
 *   .confidence_score    (1 − penalty) where penalty = computeConfidencePenalty(missing_weight)
 *   .confidence_band     'high' | 'slight' | 'medium' | 'low'
 *   .has_imputed         true when any trait was filled by imputation
 *   .has_unknown         true when any trait could not be filled at all
 *   .vts_raw             original pipeline vts_final (preserved, never mutated)
 *   .vts_conf_adj        vts_raw × (1 − penalty); equals vts_raw when no imputation
 *
 * Fallback order per missing trait:
 *   1. Player historical baseline  (getPlayerHistoricalBaseline — currently a stub)
 *   2. Tier / cohort average       (same tier, valid observed scores only)
 *   3. Full-field average          (all players, valid observed scores only)
 *   4. null → unknown              (no data available; trait is excluded from scoring)
 *
 * Does NOT modify vts_final. vts_conf_adj is a display-layer advisory.
 */
function runImputationPass(players) {
  const diag = {
    players_with_issues: [],
    field_averages: {},
    tier_averages: {},
    imputation_log: [],
    summary: null,
  };

  /* ── Step 1: collect valid observed scores ── */
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

  /* ── Step 2: compute averages (observed only) ── */
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

  /* ── Step 3: impute or flag missing traits per player ── */
  for (const p of players) {
    p.imputed_traits = [];
    p.unknown_traits = [];
    p.missing_trait_weight = 0;
    const tier = String(p.tier);

    for (const t of (p.trait_scores || [])) {
      if (!isValidTraitScore(t.score)) {
        t.original_score = t.score;
        t.imputed = true;

        /* Fallback chain: historical → tier avg → field avg → null */
        const hb = getPlayerHistoricalBaseline(p.player_name, t.key);
        const ta = tierAvg[tier]?.[t.key];
        const fa = fieldAvg[t.key];

        let imputedValue = null;
        let imputedFrom  = 'none';

        if (hb != null)      { imputedValue = hb; imputedFrom = 'player_historical'; }
        else if (ta != null) { imputedValue = ta; imputedFrom = `tier_${tier}_avg`; }
        else if (fa != null) { imputedValue = fa; imputedFrom = 'field_avg'; }

        t.score = imputedValue;   // null when no fallback — trait is unknown
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
        diag.players_with_issues.push({ player: p.player_name, ...entry });
        diag.imputation_log.push({ player: p.player_name, trait: t.key, from: imputedFrom });
      }
    }

    /* Confidence band */
    p.has_imputed = p.imputed_traits.length > 0;
    p.has_unknown = p.unknown_traits.length > 0;
    p.confidence_band =
      p.missing_trait_weight >= 0.20 ? 'low'    :
      p.missing_trait_weight >= 0.10 ? 'medium' :
      p.missing_trait_weight >  0    ? 'slight' : 'high';

    /* Confidence-adjusted VTS (display-layer advisory; vts_final is never mutated) */
    p.vts_raw = +p.vts_final;
    const penalty = computeConfidencePenalty(p.missing_trait_weight);
    p.vts_conf_adj = p.has_imputed || p.has_unknown
      ? +(p.vts_raw * (1 - penalty)).toFixed(2)
      : p.vts_raw;
    p.confidence_score = 1 - penalty;

    /* Rebuild trait_map with imputed/null scores so downstream lookups are consistent */
    p.trait_map = {};
    for (const t of (p.trait_scores || [])) p.trait_map[t.key] = t;
  }

  /* ── Diagnostics summary ── */
  const affected      = new Set(diag.players_with_issues.map(d => d.player));
  const withUnknown   = new Set(diag.players_with_issues.filter(d => !d.resolved).map(d => d.player));
  const totalMissWt   = [...affected].reduce((s, name) => {
    const p = players.find(x => x.player_name === name);
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

/* Emit diagnostics to console + expose on window for dev access */
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

  console.groupCollapsed('Field averages used for imputation fallback');
  console.table(Object.entries(diag.field_averages).map(([trait, val]) => ({ trait, field_avg: val })));
  console.groupEnd();

  console.groupCollapsed('Full imputation log');
  console.table(diag.players_with_issues);
  console.groupEnd();

  console.groupEnd();

  /* Attach to window so power users can inspect in devtools */
  window.VenueDNA_Diagnostics = diag;
}

/* Render the diagnostics summary panel in the UI */
function renderDiagnosticsPanel(diag) {
  const el = document.getElementById('diag-panel-body');
  if (!el) return;

  const s = diag.summary;
  const allClear = s.traits_imputed === 0 && s.traits_unknown === 0;

  if (allClear) {
    el.innerHTML = `<p style="font-size:.78rem;color:var(--green)">✓ All player trait profiles fully observed. No imputation applied.</p>`;
    return;
  }

  /* Summary counts strip */
  const avgMissWtPct = +(s.avg_missing_trait_weight * 100).toFixed(1);
  const summaryHTML = `
    <div class="diag-counts">
      <span class="diag-count-pill">Players with imputed traits: <b>${s.players_affected - s.players_with_unknown}</b></span>
      <span class="diag-count-pill diag-count-warn">Players with unresolved unknown traits: <b>${s.players_with_unknown}</b></span>
      <span class="diag-count-pill">Traits successfully imputed: <b>${s.traits_imputed}</b></span>
      <span class="diag-count-pill diag-count-warn">Traits unresolved (unknown): <b>${s.traits_unknown}</b></span>
      <span class="diag-count-pill">Avg missing weight (affected): <b>${avgMissWtPct}%</b></span>
    </div>`;

  /* Per-player detail table */
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
      <td>${name.split(',').reverse().join(' ').trim()}</td>
      <td><span class="diag-conf-badge diag-conf-${band}">${band}</span></td>
      <td style="font-size:.68rem">${(totalW*100).toFixed(0)}%</td>
      <td style="font-size:.68rem">${resolved.length} imputed · <span style="color:${unknown.length?'#f87171':'var(--muted)'}"> ${unknown.length} unknown</span></td>
      <td style="line-height:1.65">${traitCells}</td>
    </tr>`;
  }).join('');

  /* Upstream QA section (shown if qa_report.json was loaded) */
  let upstreamQAHTML = '';
  const qa = diag.upstreamQA;
  if (qa) {
    const qts = qa.tournament_summary;
    const warnings = (qa.warnings || []).filter(w => w.level === 'warning' || w.level === 'error');
    const infoItems = (qa.warnings || []).filter(w => w.level === 'info');
    const warnPills = warnings.map(w =>
      `<div class="diag-qa-warn diag-qa-${w.level}">[${w.level.toUpperCase()}] ${w.message}</div>`
    ).join('');
    const infoPills = infoItems.map(w =>
      `<div class="diag-qa-warn diag-qa-info">[INFO] ${w.message}</div>`
    ).join('');
    upstreamQAHTML = `
      <div class="diag-qa-section">
        <div class="diag-qa-header">Build-time QA Report
          <span class="diag-qa-ts">generated ${qa.generated_at?.slice(0,19).replace('T',' ')} UTC</span>
        </div>
        <div class="diag-counts" style="margin-bottom:.35rem">
          <span class="diag-count-pill">Zero-sentinels: <b>${qts.traits_zero_sentinel_count}</b></span>
          <span class="diag-count-pill">Imputed (tier): <b>${qts.traits_imputed_from_tier}</b></span>
          <span class="diag-count-pill">Imputed (field): <b>${qts.traits_imputed_from_field}</b></span>
          <span class="diag-count-pill ${qts.traits_unresolved_unknown > 0 ? 'diag-count-warn' : ''}">Unresolved: <b>${qts.traits_unresolved_unknown}</b></span>
          <span class="diag-count-pill">Extreme-low flags: <b>${qts.traits_extreme_low_flagged}</b></span>
          <span class="diag-count-pill">Wtd miss rate: <b>${(qts.tournament_weighted_miss_rate * 100).toFixed(2)}%</b></span>
        </div>
        ${warnPills}${infoPills}
      </div>`;
  }

  el.innerHTML = `
    ${upstreamQAHTML}
    ${summaryHTML}
    <div style="margin:.5rem 0;font-size:.73rem;color:#fcd34d">
      ⚠ VTS scores are pipeline-computed values. Imputation is a display-layer estimate only.
      Unknown traits are excluded from threshold filters regardless of settings.
      <code style="font-size:.65rem;color:var(--muted);margin-left:.4rem">window.VenueDNA_Diagnostics</code> for full data.
    </div>
    <table class="diag-table">
      <thead><tr><th>Player</th><th>Conf</th><th>Missing Wt.</th><th>Counts</th><th>Trait detail</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

/*
 * renderBadgeLegend — small always-visible strip explaining badge meanings.
 * Only rendered when the field contains at least one player with non-observed data.
 */
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
      : ''}
    <span class="bl-item"><span class="badge-imputed badge-imputed-low" style="position:static;font-size:.58rem">LOW CONF</span> ≥20% trait weight unobserved</span>
    ${VENUEDNA_CONFIG.confidencePenaltyMode !== 'none'
      ? `<span class="bl-item" style="color:var(--muted)">VTS → adj: confidence-adjusted display score (raw preserved)</span>`
      : ''}`;
}

/* Global diagnostics store (populated in init) */
let DIAGNOSTICS = { summary: { traits_imputed: 0, players_affected: 0 } };

/* ── Anti-pattern metadata (tooltip text) ── */
const AP_META = {
  bomb_and_spray:      { cls: 'bomb',   label: 'Bomb + Spray',            tip: 'Elite distance but below-field driving accuracy — high variance off tee at a placement-premium course.' },
  wedge_liability:     { cls: 'wedge',  label: 'Wedge Liability',          tip: 'Below-field wedge proximity inside 150 yd — drag on the course\'s highest-weighted scoring trait.' },
  poor_birdie_conv:    { cls: 'birdie', label: 'Poor Birdie Conv',         tip: 'Low conversion inside 5 ft — limits birdie upside at a birdie-fest track.' },
  rough_approach_liab: { cls: 'rough',  label: 'Rough Approach Liability', tip: 'Below-field approach quality from rough — risk multiplier at TPC River Highlands if fairways are missed.' },
};

/* ── Filter preset definitions ── */
const FILTER_PRESETS = {
  'wedge-spec':    [{ trait:'app_wedge',       op:'>=', value: 75 }],
  'birdie-conv':   [{ trait:'putt_short_conv', op:'>=', value: 75 }],
  'accurate':      [{ trait:'ott_accuracy',    op:'>=', value: 75 }],
  'around-green':  [{ trait:'arg_rough',       op:'>=', value: 70 }, { trait:'arg_bunker', op:'>=', value: 70 }],
  'betting-card':  [{ trait:'app_wedge',       op:'>=', value: 70 }, { trait:'putt_short_conv', op:'>=', value: 70 }],
};

/* ── Preset view definitions (view-button dropdown) ── */
const VIEW_PRESETS = {
  'top-equity':       { label: 'Top Win Equity',       sort: { col: 'win_pct', dir: -1 } },
  'wedge-fits':       { label: 'Best Wedge Fits',      traitFilters: [{ trait:'app_wedge', op:'>=', value:70 }], sort: { col: 'app_wedge_score', dir: -1 } },
  'birdie-makers':    { label: 'Best Birdie Makers',   traitFilters: [{ trait:'putt_short_conv', op:'>=', value:70 }], sort: { col: 'putt_short_conv_score', dir: -1 } },
  'accurate-drivers': { label: 'Accurate Drivers',     traitFilters: [{ trait:'ott_accuracy', op:'>=', value:70 }], sort: { col: 'ott_accuracy_score', dir: -1 } },
  'safe-floor':       { label: 'Safest Floor',         sort: { col: 'top20_pct', dir: -1 } },
  'longshot-dogs':    { label: 'Longshot Dogs',        tierFilter: '4', sort: { col: 'win_pct', dir: -1 } },
  'clean-flags':      { label: 'No Risk Flags',        noFlags: true, sort: { col: 'vts_final', dir: -1 } },
  'favorites':        { label: 'My Card',              favOnly: true },
};

/* ══════════════════════════════════════════════════════
   BOOTSTRAP
══════════════════════════════════════════════════════ */
async function init() {
  const [payload, briefs] = await Promise.all([
    fetch(DATA_DIR + 'event_payload.json').then(r => r.json()),
    fetch(DATA_DIR + 'player_briefs.json').then(r => r.json()),
  ]);
  eventMeta = payload;

  for (const tier of [1,2,3,4,5]) {
    for (const p of (briefs[`tier_${tier}`] || [])) {
      if (p.name_key) briefsByNk[p.name_key] = p;
    }
  }

  allPlayers = [];
  for (const tier of [1,2,3,4,5]) {
    for (const p of (payload.tiers[`tier_${tier}`] || [])) {
      /* Derive flag_count before imputation pass */
      p.flag_count = p.anti_pattern_flags
        ? p.anti_pattern_flags.split(';').filter(f => f.trim()).length
        : 0;
      allPlayers.push(p);
    }
  }
  allPlayers.sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));

  /* ── Missing-trait validation + imputation ── */
  DIAGNOSTICS = runImputationPass(allPlayers);
  logDiagnostics(DIAGNOSTICS);

  /* ── Upstream QA report (optional — generated by qa_trait_validation.py) ── */
  try {
    const qaReport = await fetch(DATA_DIR + 'qa_report.json').then(r => r.json());
    DIAGNOSTICS.upstreamQA = qaReport;
    console.info('[VenueDNA] Upstream QA report loaded:', qaReport.tournament_summary);
  } catch (_) {
    /* qa_report.json not present — client-side diagnostics only */
  }

  /* ── Round analysis files (all optional — generated by build_round_analysis.py) ── */
  async function tryLoadRound(file, label) {
    try {
      const data = await fetch(DATA_DIR + file).then(r => {
        if (!r.ok) return null;
        return r.json();
      });
      if (data) console.info(`[VenueDNA] ${label} loaded: ${data.match_summary?.matched}/${data.match_summary?.total_r1} matched, built ${data.build_timestamp || data.generated_at}`);
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
  /* trait_map is built inside runImputationPass after imputation */

  renderHeader(payload);
  renderMetaBar(payload);
  renderInfoCards(payload);
  renderNoCutBanner(payload);
  renderTierAlert(payload.tiers);
  renderBriefs(briefs);
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

  applyAndRender();
}

/* ══════════════════════════════════════════════════════
   HEADER / META / INFO CARDS (unchanged logic)
══════════════════════════════════════════════════════ */
function renderHeader(payload) {
  const ev = payload.event, ms = payload.model_summary;
  document.querySelector('.header h1').innerHTML = `<span>PGA VenueDNA</span> — ${ev.name}`;
  document.querySelector('.header-meta').textContent =
    `${ev.venue} · ${payload.venue?.location || 'Cromwell, CT'} · ${ev.dates} · Par ${ev.par} · ${ev.yardage} yds`;
  const badges = document.querySelector('.badges');
  if (ev.field_locked) badges.insertAdjacentHTML('beforeend','<span class="badge-locked">FIELD LOCKED</span>');
  if (ev.cut_rule === 'no_cut') badges.insertAdjacentHTML('beforeend','<span class="badge-nocut">NO CUT</span>');
  const hasRoundData = r1Data || r2Data || r3Data || r4Data;
  if (!hasRoundData && ev.tee_times_note?.includes('TBD')) badges.insertAdjacentHTML('beforeend','<span class="badge-tbd">TEE TIMES TBD</span>');
  const rounds = cumulativeData?.rounds_present;
  const currentRound = rounds?.length
    ? `r${Math.max(...rounds)}`
    : (r4Data ? 'r4' : r3Data ? 'r3' : r2Data ? 'r2' : r1Data ? 'r1' : null);
  const iterLabel = currentRound || ms.event_iteration;
  if (iterLabel) badges.insertAdjacentHTML('beforeend',`<span class="badge-tbd">iter:${iterLabel}</span>`);
}

function renderMetaBar(payload) {
  const ev = payload.event, ms = payload.model_summary;
  document.querySelector('.meta-bar-inner').innerHTML = [
    `<span>Field: <b>${ev.field_size} players</b></span>`,
    `<span>Purse: <b>$${(ev.purse/1e6).toFixed(0)}M</b></span>`,
    `<span>Class: <b>${ev.event_class}</b></span>`,
    `<span>Spec: <b>v${ms.scoring_spec_version}</b></span>`,
    `<span>Venue file: <b>${ms.venue_file_version}</b></span>`,
    `<span>Model leader: <b>${ms.model_winner} (VTS ${ms.model_winner_vts})</b></span>`,
  ].join('');
}

function renderInfoCards(payload) {
  const v = payload.venue, ms = payload.model_summary;
  document.querySelector('.info-grid').innerHTML = `
    <div class="info-card">
      <h3>Venue</h3>
      ${kv('Location', v.location)}${kv('Par / Yardage', `${v.par} / ${v.yardage} yds`)}
      ${kv('Surface', v.surface)}${kv('Stimp', v.stimp)}
      ${kv('Fairway width', v.fairway_width)}${kv('Rough', v.rough_severity)}
      ${kv('Scoring avg', v.scoring_avg)}${kv('Signature stretch', v.signature_stretch)}
      ${kv('Course record', v.course_record)}
    </div>
    <div class="info-card">
      <h3>Trait Weights</h3>
      ${Object.entries(ms.trait_weight_matrix).map(([k,w])=>kv(TRAIT_KEY_MAP[k]?.label || k.replace(/_/g,' '), `${Math.round(w*100)}%`)).join('')}
    </div>
    <div class="info-card">
      <h3>Model Config</h3>
      ${ms.anti_patterns.map(ap=>kv(AP_META[ap]?.label || ap.replace(/_/g,' '),'active')).join('')}
      ${kv('Cut rule', payload.event.cut_rule)}
      ${kv('Win cap', '14%')}${kv('Win normalization','field sum = 1.00')}
      ${kv('Comp courses', v.comp_courses?.join(', '))}
    </div>`;
}

function kv(k, v) {
  return `<div class="kv"><span class="k">${k}</span><span class="v">${v ?? '—'}</span></div>`;
}

function renderNoCutBanner(payload) {
  const ev = payload.event;
  if (ev.cut_rule !== 'no_cut') return;
  document.querySelector('.nocut-banner').innerHTML =
    `<span class="icon">✕</span><span>${ev.no_cut_note}</span>`;
}

function renderTierAlert(tiers) {
  const el = document.querySelector('.tee-alert');
  if (r1Data || r2Data || r3Data || r4Data) { el.style.display = 'none'; return; }
  const counts = {};
  for (let t = 1; t <= 5; t++) counts[t] = (tiers[`tier_${t}`] || []).length;
  const total = Object.values(counts).reduce((a,b) => a+b, 0);
  el.textContent =
    `Tee times TBD for all ${total} players (pga_field.csv not available at build time). ` +
    `Distribution — T1:${counts[1]}  T2:${counts[2]}  T3:${counts[3]}  T4:${counts[4]}  T5:${counts[5]}`;
}

/* ══════════════════════════════════════════════════════
   UNIFIED FILTER + RENDER PIPELINE
══════════════════════════════════════════════════════ */
function applyAndRender() {
  let players = [...allPlayers];

  /* 1. Tier filter */
  if (activeTier !== 'all') {
    players = players.filter(p => String(p.tier) === activeTier);
  }

  /* 2. Search */
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    players = players.filter(p => p.player_name.toLowerCase().includes(q));
  }

  /* 3. Favorites-only */
  if (favOnly) {
    players = players.filter(p => favorites.has(p.player_name));
  }

  /* 4. Preset view filters */
  if (activePreset) {
    const vp = VIEW_PRESETS[activePreset];
    if (vp) {
      if (vp.favOnly) players = players.filter(p => favorites.has(p.player_name));
      if (vp.noFlags) players = players.filter(p => p.flag_count === 0);
      if (vp.tierFilter) players = players.filter(p => String(p.tier) === vp.tierFilter);
      if (vp.traitFilters) {
        vp.traitFilters.forEach(tf => {
          players = players.filter(p => traitFilterPass(p, tf));
        });
      }
    }
  }

  /* 5. Manual trait filters */
  activeFilters.forEach(f => {
    players = players.filter(p => traitFilterPass(p, f));
  });

  /* 6. Sort */
  players = sortPlayers(players);

  renderTable(players);
  updateResultBar(players.length);
  updateActivePills();
  updateSortIndicators();
}

/*
 * getTraitQuality — returns the data-quality classification for a specific trait.
 *   'observed' — raw pipeline data, fully trusted
 *   'imputed'  — filled from tier or field average; estimate only
 *   'unknown'  — no data at all; imputation failed (no valid cohort exists)
 */
function getTraitQuality(p, traitKey) {
  const t = p.trait_map?.[traitKey];
  if (!t) return 'unknown';
  if (!t.imputed) return 'observed';
  return t.score !== null ? 'imputed' : 'unknown';
}

/*
 * traitFilterPass — evaluates one filter rule against one player.
 *
 * Exclusion policy:
 *   unknown  → always excluded (no meaningful data to compare against a threshold)
 *   imputed  → excluded by default; pass only when user has enabled allowImputedInFilters
 *   observed → evaluated normally
 *
 * This ensures that threshold filters like "APP_Wedge >= 75" only surface players
 * with genuinely observed evidence for that claim.
 */
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
  /* top-N is resolved via sort; always pass here */
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
      /* When conf adjustment is active, sort by adj score so displayed order matches displayed value */
      const useAdj = VENUEDNA_CONFIG.confidencePenaltyMode !== 'none';
      va = useAdj ? (a.vts_conf_adj ?? a.vts_raw ?? 0) : (+a.vts_final || 0);
      vb = useAdj ? (b.vts_conf_adj ?? b.vts_raw ?? 0) : (+b.vts_final || 0);
    }
    else if (col === 'win_pct')   { va = +a.win_pct || 0; vb = +b.win_pct || 0; }
    else if (col === 'top10_pct') { va = +a.top10_pct || 0; vb = +b.top10_pct || 0; }
    else if (col === 'top20_pct') { va = +a.top20_pct || 0; vb = +b.top20_pct || 0; }
    else if (col === 'vh_rounds') { va = +a.vh_rounds || 0; vb = +b.vh_rounds || 0; }
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
    const nk = toNameKey(p.player_name);
    const isFav = favorites.has(p.player_name);
    const inCompare = comparePlayers.some(c => c.player_name === p.player_name);
    const tr = document.createElement('tr');
    if (isFav) tr.classList.add('row-fav');
    if (inCompare) tr.classList.add('row-compare');
    tr.dataset.name = p.player_name;

    const dataBadge = playerDataBadgeHTML(p);
    tr.innerHTML = `
      <td class="rank-cell">${p.rank}</td>
      <td>
        <div class="player-name">${p.player_name} ${dataBadge}</div>
        <div class="player-driver">${TRAIT_KEY_MAP[p.primary_driver?.toLowerCase().replace(/-/g,'_')]?.label || p.primary_driver || ''}</div>
      </td>
      <td>${tierBadgeHTML(p.tier)}</td>
      <td class="vts-cell">${vtsDisplayHTML(p)}</td>
      <td class="prob-cell">${fmtPct(p.win_pct)}</td>
      <td class="prob-cell">${fmtPct(p.top10_pct)}</td>
      <td class="prob-cell">${fmtPct(p.top20_pct)}</td>
      <td><span class="prob-na">N/A</span></td>
      <td>${apTagsHTML(p.anti_pattern_flags)}</td>
      <td class="vts-label">${p.vh_rounds ?? 0} rds</td>
      <td class="fav-cell">
        <button class="fav-btn${isFav ? ' on' : ''}" title="${isFav ? 'Remove favorite' : 'Add to favorites'}">★</button>
      </td>
      <td class="cmp-cell">
        <button class="cmp-btn${inCompare ? ' on' : ''}" title="${inCompare ? 'Remove from compare' : 'Add to compare'}">⊕</button>
      </td>`;

    /* Row click → modal (not from fav/cmp buttons) */
    tr.addEventListener('click', e => {
      if (e.target.classList.contains('fav-btn') || e.target.classList.contains('cmp-btn')) return;
      openModal(p, briefsByNk[nk]);
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
  /* Search */
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

  /* Keyboard shortcut: / focuses search */
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== input && !isModalOpen()) {
      e.preventDefault();
      input.focus();
    }
  });

  /* Favorites only toggle */
  document.getElementById('btn-favonly').addEventListener('click', () => {
    favOnly = !favOnly;
    document.getElementById('btn-favonly').classList.toggle('active', favOnly);
    applyAndRender();
  });

  /* Reset all */
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
        /* Default direction: numeric cols desc, name asc */
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
  } else if (comparePlayers.length < 4) {
    comparePlayers.push(p);
  }
  updateCompareTray();
  /* Update btn-compare in controls bar */
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
  playersEl.innerHTML = comparePlayers.map(p =>
    `<div class="compare-chip">
       ${p.player_name.split(',')[0]}
       <button class="compare-chip-remove" data-name="${p.player_name}" title="Remove">✕</button>
     </div>`
  ).join('');
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
  const colClass = n === 2 ? 'cols-2' : n === 3 ? 'cols-3' : 'cols-4';

  const adjActive = VENUEDNA_CONFIG.confidencePenaltyMode !== 'none';
  const STAT_KEYS = [
    ['VTS (raw)',    p => (p.vts_raw ?? +p.vts_final).toFixed(1)],
    adjActive
      ? ['VTS (adj)', p => {
          const adj = p.vts_conf_adj ?? p.vts_raw ?? +p.vts_final;
          const raw = p.vts_raw ?? +p.vts_final;
          return adj < raw
            ? `<span style="color:#fcd34d">${adj.toFixed(1)}</span>`
            : `<span style="color:var(--muted)">${adj.toFixed(1)} —</span>`;
        }]
      : null,
    ['Win %',        p => fmtPct(p.win_pct)],
    ['Top 10 %',     p => fmtPct(p.top10_pct)],
    ['Top 20 %',     p => fmtPct(p.top20_pct)],
    ['Tier',         p => `T${p.tier}`],
    ['CH Rds',       p => `${p.vh_rounds ?? 0}`],
    ['Flags',        p => p.flag_count > 0 ? apTagsHTML(p.anti_pattern_flags) : '—'],
    ['Conf band',    p => p.confidence_band !== 'high'
      ? `<span style="color:${p.confidence_band==='low'?'#f87171':p.confidence_band==='medium'?'#fcd34d':'#94a3b8'}">${p.confidence_band}</span>`
      : '<span style="color:#86efac">high</span>'],
    ['Missing wt',   p => p.missing_trait_weight > 0 ? `${Math.round(p.missing_trait_weight*100)}%` : '—'],
  ].filter(Boolean);

  const cols = comparePlayers.map(p => {
    const brief = briefsByNk[toNameKey(p.player_name)] || {};
    const traits = p.trait_scores || brief.trait_scores || [];
    const sorted = [...traits].sort((a,b) => b.weight - a.weight);

    const statRows = STAT_KEYS.map(([k, fn]) =>
      `<div class="compare-stat"><span class="cs-k">${k}</span><span class="cs-v">${fn(p)}</span></div>`
    ).join('');

    const traitRows = sorted.map(t => {
      const quality = getTraitQuality(p, t.key);
      const s = t.score != null ? +t.score : null;
      const display = s ?? 0;
      const cls = display >= 75 ? 'bar-elite' : display >= 50 ? 'bar-ok' : 'bar-weak';
      const imputedStyle = quality !== 'observed' ? 'opacity:.6;' : '';
      const label = quality === 'unknown' ? '—' : display.toFixed(0);
      const qualMark = quality === 'imputed' ? '~' : quality === 'unknown' ? '?' : '';
      return `<div class="compare-trait-row">
        <span class="compare-trait-label" title="${t.label}${quality !== 'observed' ? ` [${quality}]` : ''}">${qualMark}${t.label.split('(')[0].trim()}</span>
        <div class="compare-trait-bar-bg" style="${imputedStyle}"><div class="compare-trait-bar-fill ${cls}" style="width:${Math.min(100,display)}%"></div></div>
        <span class="compare-trait-score" style="color:${display>=75?'#38bdf8':display>=50?'#4ade80':'#f87171'};${imputedStyle}">${label}</span>
      </div>`;
    }).join('');

    const fitPos = (p.course_fit_explanation?.positive_drivers || brief.course_fit_explanation?.positive_drivers || []).slice(0,2);
    const conviction = p.conviction_statement || brief.conviction_statement || '—';

    const vtsRaw  = (p.vts_raw ?? +p.vts_final).toFixed(1);
    const vtsAdj  = p.vts_conf_adj != null && p.vts_conf_adj < (p.vts_raw ?? +p.vts_final)
      ? ` <span style="color:#fcd34d;font-size:.72rem">→ ${p.vts_conf_adj.toFixed(1)} adj</span>` : '';
    const confLabel = p.confidence_band !== 'high'
      ? ` ${playerDataBadgeHTML(p)}` : '';
    return `<div class="compare-col">
      <div class="compare-col-name">${p.player_name.split(',').reverse().join(' ').trim()}</div>
      <div class="compare-col-sub">${tierBadgeHTML(p.tier)} &nbsp; VTS ${vtsRaw}${vtsAdj}${confLabel}</div>
      <h5>Output</h5>
      ${statRows}
      <h5>Trait Profile</h5>
      ${traitRows}
      ${fitPos.length ? `<h5>Fit Drivers</h5>${fitPos.map(d=>`<div style="font-size:.7rem;color:#86efac;margin-bottom:.15rem">✓ ${d}</div>`).join('')}` : ''}
      ${conviction !== '—' ? `<h5>Conviction</h5><div style="font-size:.7rem;color:var(--muted);line-height:1.5">${conviction}</div>` : ''}
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

  /* "Include imputed/unknown" toggle */
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

function addFilterRule(trait='app_wedge', op='>=', value=70) {
  const id = ++filterRuleCounter;
  activeFilters.push({ id, trait, op, value });
  syncFilterRulesUI();
  applyAndRender();
}

function syncFilterRulesUI() {
  const container = document.getElementById('filter-rules');
  container.innerHTML = '';
  const badge = document.getElementById('filter-badge');

  /* Keep the "include imputed" checkbox in sync with current state */
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

    const traitOpts = TRAIT_DEFS.map(t =>
      `<option value="${t.key}" ${t.key === f.trait ? 'selected' : ''}>${t.label} (${Math.round(t.weight*100)}%)</option>`
    ).join('');

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

    row.querySelector('.fp-trait-sel').addEventListener('change', e => {
      f.trait = e.target.value;
      applyAndRender();
    });
    row.querySelector('.fp-op-sel').addEventListener('change', e => {
      f.op = e.target.value;
      applyAndRender();
    });
    row.querySelector('.fp-val').addEventListener('input', e => {
      f.value = parseFloat(e.target.value) || 0;
      applyAndRender();
    });
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

  activeFilters.forEach(f => {
    const td = TRAIT_KEY_MAP[f.trait];
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

  dd.querySelectorAll('.preset-item').forEach(item => {
    item.addEventListener('click', e => {
      e.stopPropagation();
      const preset = item.dataset.preset;
      if (activePreset === preset) {
        activePreset = null;
      } else {
        activePreset = preset;
        /* Apply view-level overrides */
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
}

function syncPresetDropdownUI() {
  document.querySelectorAll('.preset-item').forEach(item => {
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
/*
 * cleanConviction — transforms formulaic engine conviction text into readable dashboard copy.
 * Parses the known output pattern from the Python pipeline and rebuilds as compact stat line.
 * Falls through to raw text if the pattern isn't recognized.
 */
function cleanConviction(raw) {
  if (!raw || !/venue-fit/.test(raw)) return raw;
  const vtsMatch    = raw.match(/VTS (\d+\.?\d*)/);
  const vfdMatch    = raw.match(/venue-fit (?:delta|drag) \(([+-]?\d+\.?\d*)\)/);
  const traitMatch  = raw.match(/lead trait ([A-Z0-9 _]+?) at TPC/);
  const roundsMatch = raw.match(/(\d+)-round course history/);

  const vts     = vtsMatch   ? parseFloat(vtsMatch[1])   : null;
  const vfd     = vfdMatch   ? parseFloat(vfdMatch[1])   : null;
  const rawKey  = traitMatch ? traitMatch[1].toLowerCase().replace(/ /g,'_') : null;
  const rounds  = roundsMatch ? parseInt(roundsMatch[1]) : null;

  const def       = rawKey ? TRAIT_KEY_MAP[rawKey] : null;
  const leadLabel = def ? def.label : rawKey ? rawKey.replace(/_/g,' ') : null;
  const leadWt    = def ? Math.round(def.weight * 100) : null;

  const parts = [];
  if (vts  !== null) parts.push(`VTS ${vts.toFixed(1)}`);
  if (vfd  !== null) { const s = vfd >= 0 ? '+' : ''; parts.push(`Fit ${s}${vfd.toFixed(1)}`); }
  if (leadLabel)     parts.push(leadWt ? `${leadLabel} leads (${leadWt}% wt)` : leadLabel);
  if (rounds)        parts.push(`${rounds} course rounds`);

  return parts.length ? parts.join(' &middot; ') : raw;
}

/* ── Display normalization helpers ──────────────────────────────────────
 * Single entry-point for all trait key / flag normalization in the UI.
 * Every render path that surfaces a key or flag string must call one of
 * these — prevents raw payload keys from leaking to the user-facing UI.
 */
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
  // Replace embedded trait-key patterns: ARG_Bunker, APP_Wedge, APP_100-150, etc.
  return text.replace(/\b([A-Z]{2,3}_[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*)\b/g, match => {
    const def = TRAIT_KEY_MAP[match.toLowerCase().replace(/-/g, '_')];
    return def ? def.label : match;
  });
}

function apTagsHTML(flagStr) {
  if (!flagStr || !flagStr.trim()) return '';
  return flagStr.split(';').map(f => {
    const key = f.trim().toLowerCase();   // normalize — payload may be lower or upper
    const meta = AP_META[key];
    if (meta) {
      return `<span class="ap-tag ${meta.cls}" title="${meta.tip}">${meta.label}<span class="ap-tooltip">${meta.tip}</span></span>`;
    }
    return `<span class="ap-tag">${cleanDisplayKey(f.trim())}</span>`;
  }).join('');
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
  return `<span class="tier-badge t${tier}">T${tier}</span>`;
}

/* ══════════════════════════════════════════════════════
   MODAL — player detail
══════════════════════════════════════════════════════ */
function openModal(p, brief) {
  const overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-player-name').textContent = p.player_name;
  document.getElementById('modal-player-sub').innerHTML =
    `${tierBadgeHTML(p.tier)} &nbsp; VTS ${(+p.vts_final).toFixed(1)} &nbsp;·&nbsp; ` +
    `R1: ${p.r1_tee_time || 'TBD'} ${p.r1_wave && p.r1_wave !== 'TBD' ? p.r1_wave : ''}`;

  const b = brief || {};
  const traitScores   = p.trait_scores   || b.trait_scores   || [];
  const cfExplain     = p.course_fit_explanation || b.course_fit_explanation || {};
  const formWindow    = p.form_window    || b.form_window    || '';
  const vhNarrative   = p.venue_history_narrative || b.venue_history_summary || '';
  const conviction    = p.conviction_statement || b.conviction_statement || p.tier_reason || '';
  const failureCond   = p.named_failure_condition || b.named_failure_condition || '';
  const penalties     = b.penalties_summary || '';

  const body = document.getElementById('modal-body');
  body.innerHTML = [
    sectionWhyFit(p, cfExplain),
    sectionImputedData(p),           /* ← imputation notice, shown only when relevant */
    sectionProbability(p),
    sectionCourseFit(cfExplain, p),
    sectionTraitBars(traitScores),
    sectionFormWindow(formWindow),
    sectionVenueHistory(vhNarrative),
    sectionConviction(conviction),
    sectionRiskFailure(p.risk_stressor_active, b.risk_vector || p.primary_driver, failureCond, b.anti_pattern_flags || p.anti_pattern_flags),
    sectionAuditAccordion(p, penalties),
  ].join('');

  overlay.classList.add('open');
  body.querySelector('.audit-toggle')?.addEventListener('click', function() {
    const panel = body.querySelector('.audit-panel');
    const open  = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    this.textContent = open ? '▶ Model trace' : '▼ Model trace';
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

/*
 * playerDataBadgeHTML — single badge that reflects the worst data-quality state.
 * Priority: unknown > low-conf > medium-imputed > slight-imputed
 */
function playerDataBadgeHTML(p) {
  if (!p.has_imputed && !p.has_unknown) return '';
  const band = p.confidence_band;

  let label, cls;
  if (p.has_unknown) {
    label = 'UNKNOWN';
    cls   = 'badge-imputed badge-imputed-low';  // red
  } else if (band === 'low') {
    label = 'LOW CONF';
    cls   = 'badge-imputed badge-imputed-low';
  } else if (band === 'medium') {
    label = 'IMPUTED';
    cls   = 'badge-imputed badge-imputed-medium';
  } else {
    label = 'IMPUTED';
    cls   = 'badge-imputed badge-imputed-slight';
  }

  const unknownList  = p.unknown_traits.map(t => `✗ ${t.label}: no data`).join('\n');
  const imputedList  = p.imputed_traits.map(t => `~ ${t.label}: ${t.imputed_value} (${t.from?.replace(/_/g,' ')})`).join('\n');
  const tooltip = [unknownList, imputedList].filter(Boolean).join('\n');

  return `<span class="${cls}" title="${tooltip}">${label}</span>`;
}

/* Alias kept for any direct callers */
function imputedBadgeHTML(p) { return playerDataBadgeHTML(p); }

/*
 * vtsDisplayHTML — VTS cell renderer.
 * Shows the raw pipeline VTS bar. When conf adjustment is active and penalty is
 * non-zero, appends "→ adj" secondary number to signal the confidence drag.
 */
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
      ${hasAdj ? `<span class="vts-adj-num" title="Conf-adjusted (${dragPct}% drag · ${Math.round(p.missing_trait_weight*100)}% missing weight)">→ ${adj.toFixed(1)}</span>` : ''}
    </div>
  </div>`;
}

/* ── Imputed-data modal section ── */
function sectionImputedData(p) {
  if (!p.has_imputed) return '';

  const band = p.confidence_band;
  const missingWtPct = Math.round(p.missing_trait_weight * 100);
  const confidencePct = Math.round(p.confidence_score * 100);

  const bandColors = { low: '#f87171', medium: '#fcd34d', slight: '#94a3b8' };
  const bandColor  = bandColors[band] || '#94a3b8';

  /* Observed traits */
  const observed = (p.trait_scores || []).filter(t => !t.imputed);
  const imputed  = p.imputed_traits;

  const observedHTML = observed.length
    ? observed.map(t => {
        const td = TRAIT_KEY_MAP[t.key];
        const wt = td ? Math.round(td.weight*100) : '';
        return `<div class="imputed-row observed-row">
          <span class="irow-label">${t.label}</span>
          <span class="irow-score">${(+t.score).toFixed(0)}</span>
          <span class="irow-src">${wt ? wt+'% wt' : ''}</span>
        </div>`;
      }).join('')
    : '<div style="font-size:.72rem;color:var(--muted)">—</div>';

  const imputedHTML = imputed.map(t => {
    const wt = Math.round(t.weight * 100);
    const srcLabel = t.from === 'field_avg' ? 'field avg'
      : t.from?.startsWith('tier_') ? `tier avg` : t.from || 'unknown';
    return `<div class="imputed-row">
      <span class="irow-label">${t.label}</span>
      <span class="irow-score imputed-score">~${t.imputed_value ?? '—'}</span>
      <span class="irow-src">${wt}% wt · ${srcLabel}</span>
    </div>`;
  }).join('');

  return `<div class="modal-section imputed-section" style="border-left: 3px solid ${bandColor}; padding-left: .75rem;">
    <h4 style="color:${bandColor}">Data Quality — ${band === 'low' ? 'Low' : band === 'medium' ? 'Medium' : 'Slight'} Confidence Profile</h4>
    <div class="stat-row" style="margin-bottom:.6rem">
      <span class="stat-pill"><span class="sk">Missing trait weight:</span> <span class="sv" style="color:${bandColor}">${missingWtPct}%</span></span>
      <span class="stat-pill"><span class="sk">Observed signal:</span> <span class="sv">${confidencePct}%</span></span>
      <span class="stat-pill"><span class="sk">Traits imputed:</span> <span class="sv">${imputed.length}</span></span>
    </div>
    <div class="imputed-grid">
      <div>
        <div class="imputed-col-label">Observed traits</div>
        ${observedHTML}
      </div>
      <div>
        <div class="imputed-col-label">Imputed traits <span style="font-size:.65rem;font-weight:400;color:var(--muted)">(~ estimated, not measured)</span></div>
        ${imputedHTML}
      </div>
    </div>
    <p style="font-size:.7rem;color:var(--muted);margin-top:.5rem;line-height:1.5">
      VTS was computed from pipeline data. These imputed values fill missing inputs for display only.
      Where imputation was applied, take rank outputs and trait bars as advisory.
      Missing weight of <b style="color:${bandColor}">${missingWtPct}%</b> reduces effective model signal.
    </p>
  </div>`;
}

/* ── Diagnostics toggle (footer link) ── */
function wireDiagnosticsToggle() {
  document.getElementById('diag-toggle')?.addEventListener('click', () => {
    const panel = document.getElementById('diag-panel');
    if (!panel) return;
    const open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    document.getElementById('diag-toggle').textContent = open ? '▶ Diagnostics' : '▼ Diagnostics';
  });
}

/* ── "Why this player" compact summary at top of modal ── */
function sectionWhyFit(p, cf) {
  const leadTrait = TRAIT_KEY_MAP[p.primary_driver?.toLowerCase().replace(/-/g,'_')] || null;
  const topTrait  = p.trait_scores?.slice().sort((a,b) => b.score - a.score)[0];
  const flagCount = p.flag_count || 0;

  const lead = leadTrait ? `Elite <b>${leadTrait.label}</b> profile for a course where this trait is weighted <b>${Math.round(leadTrait.weight*100)}%</b>.` :
    topTrait ? `Lead trait: <b>${topTrait.label}</b> (score ${(+topTrait.score).toFixed(0)}).` : '';
  const risk  = flagCount > 0 ? ` <span style="color:#f87171">${flagCount} risk flag${flagCount>1?'s':''} active.</span>` : ' No adverse flags.';
  const vfd   = cf?.net_vfd != null ? ` Course fit adjustment: <b>${fmtSigned(cf.net_vfd)}</b> VFD.` : '';

  if (!lead) return '';
  return `<div class="modal-section" style="background:var(--bg);border-radius:.5rem;padding:.65rem .85rem;">
    <div style="font-size:.78rem;line-height:1.6;color:var(--muted)">${lead}${vfd}${risk}</div>
  </div>`;
}

/* ── Modal sections (unchanged logic, tooltips enhanced) ── */
function sectionProbability(p) {
  const adjActive = VENUEDNA_CONFIG.confidencePenaltyMode !== 'none';
  const raw = p.vts_raw ?? +p.vts_final;
  const adj = p.vts_conf_adj ?? raw;
  const hasAdj = adjActive && (p.has_imputed || p.has_unknown) && adj < raw;

  const vtsRows = hasAdj
    ? [
        ['VTS (raw)',  `<span style="color:var(--accent)">${raw.toFixed(1)}</span>`],
        ['VTS (adj)',  `<span style="color:#fcd34d" title="Confidence-adjusted: ${Math.round(p.missing_trait_weight*100)}% missing trait weight">${adj.toFixed(1)}</span>`],
      ]
    : [['VTS', `<span style="color:var(--accent)">${raw.toFixed(1)}</span>`]];

  const probRows = [
    ['Win', fmtPct(p.win_pct)],
    ['Top 5', fmtPct(p.top5_pct)],
    ['Top 10', fmtPct(p.top10_pct)],
    ['Top 20', fmtPct(p.top20_pct)],
    ['Cut', 'N/A — no cut'],
  ];

  return `<div class="modal-section">
    <h4>Probability</h4>
    <div class="stat-row">
      ${[...vtsRows, ...probRows].map(([k,v]) => `<span class="stat-pill"><span class="sk">${k}:</span> <span class="sv">${v}</span></span>`).join('')}
    </div>
  </div>`;
}

function sectionCourseFit(cf, p) {
  if (!cf || (!cf.positive_drivers?.length && !cf.drag_traits?.length)) return '';
  const vfd = cf.net_vfd ?? p.vfd ?? 0;
  const conf = cf.confidence_band || '—';
  const posHTML  = (cf.positive_drivers || []).filter(Boolean).map(d => `<li class="fit-pos">✓ ${d}</li>`).join('');
  const dragHTML = (cf.drag_traits || []).filter(Boolean).map(d => `<li class="fit-drag">✗ ${d}</li>`).join('');
  return `<div class="modal-section">
    <h4>Course Fit at TPC River Highlands</h4>
    <div class="fit-meta">
      <span class="stat-pill"><span class="sk">Net VFD:</span> <span class="sv">${fmtSigned(vfd)}</span></span>
      <span class="stat-pill"><span class="sk">Confidence:</span> <span class="sv">${conf}</span></span>
      ${cf.comp_course_note ? `<span class="stat-pill fit-comp-note">${cf.comp_course_note}</span>` : ''}
    </div>
    <ul class="fit-list">${posHTML}${dragHTML}</ul>
  </div>`;
}

function sectionTraitBars(traits) {
  if (!traits || traits.length === 0) return '';
  const sorted = [...traits].sort((a,b) => b.weight - a.weight);
  const hasImputed = sorted.some(t => t.imputed);

  const bars = sorted.map(t => {
    const score   = t.score != null ? +t.score : null;
    const display = score != null ? score : 0;
    const pct     = Math.min(100, Math.max(0, display)).toFixed(0);
    const cls     = display >= 75 ? 'bar-elite' : display >= 50 ? 'bar-ok' : 'bar-weak';
    const imputedCls  = t.imputed ? ' bar-imputed' : '';
    const imputedTag  = t.imputed
      ? `<span class="trait-imputed-tag" title="Imputed from ${t.imputed_from?.replace('_',' ')} — original value was ${t.original_score ?? 'null'}">~</span>`
      : '';
    const scoreDisplay = score != null ? display.toFixed(0) : '—';

    return `<div class="trait-row${t.imputed ? ' trait-row-imputed' : ''}">
      <div class="trait-name" title="${t.label}">${t.label}${imputedTag}</div>
      <div class="trait-bar-wrap">
        <div class="trait-bar-bg">
          <div class="trait-bar-fill ${cls}${imputedCls}" style="width:${pct}%"></div>
        </div>
        <span class="trait-score${t.imputed ? ' imputed-score' : ''}">${scoreDisplay}</span>
        <span class="trait-pct-rank">${t.imputed ? `~${t.imputed_from?.split('_').slice(0,2).join('-')}` : (t.pct_rank || '')}</span>
      </div>
      <div class="trait-weight">${Math.round(t.weight*100)}%</div>
    </div>`;
  }).join('');

  return `<div class="modal-section">
    <h4>Trait Breakdown — Venue Weight × Player Score</h4>
    <div class="trait-legend">
      <span class="tl-item bar-elite-swatch"></span><span>≥75 elite</span>
      <span class="tl-item bar-ok-swatch"></span><span>50–74 ok</span>
      <span class="tl-item bar-weak-swatch"></span><span>&lt;50 drag</span>
      ${hasImputed ? `<span class="tl-item" style="background:transparent;border:1px solid var(--muted);border-style:dashed"></span><span style="color:var(--muted)">~ imputed</span>` : ''}
    </div>
    <div class="trait-bars">${bars}</div>
  </div>`;
}

function sectionFormWindow(text) {
  if (!text) return '';
  return `<div class="modal-section"><h4>Form Window</h4><p>${text}</p></div>`;
}

function sectionVenueHistory(text) {
  if (!text) return '';
  return `<div class="modal-section"><h4>Venue History</h4><p>${text}</p></div>`;
}

function sectionConviction(text) {
  if (!text) return '';
  return `<div class="modal-section"><h4>Conviction</h4><p>${cleanConviction(text)}</p></div>`;
}

function sectionRiskFailure(stressorActive, riskVec, failureCond, apFlags) {
  const parts = [];
  if (riskVec) parts.push(`<span class="stat-pill"><span class="sk">Primary risk:</span> <span class="sv">${cleanDisplayKey(riskVec)}</span></span>`);
  if (apFlags && apFlags.trim()) parts.push(`<span class="stat-pill"><span class="sk">AP flags:</span> <span class="sv">${apTagsHTML(apFlags)}</span></span>`);
  return `<div class="modal-section">
    <h4>Risk Vector &amp; Failure Condition</h4>
    ${parts.length ? `<div class="stat-row">${parts.join('')}</div>` : ''}
    ${failureCond ? `<p class="risk-text">${cleanRawKeys(failureCond)}</p>` : ''}
  </div>`;
}

function sectionAuditAccordion(p, penSummary) {
  const rows = [
    ['NeutralSG', fmtNum(p.neutral_sg)],
    ['VFD', fmtSigned(p.vfd)],
    ['VH rounds', p.vh_rounds ?? '—'],
    ['VH delta VTS', fmtSigned(p.vh_delta)],
    ['Pre-penalty VTS', fmtNum(p.vts_final)],
    ['VTS final', fmtNum(p.vts_final)],
    ['Win %', fmtPct(p.win_pct)],
    ['Penalties', penSummary || 'none'],
    ['Trace', p.trace_notes || '—'],
  ];
  const pills = rows.map(([k,v]) =>
    `<span class="stat-pill small"><span class="sk">${k}:</span> <span class="sv">${v}</span></span>`
  ).join('');
  return `<div class="modal-section audit-section">
    <button class="audit-toggle">▶ Model trace</button>
    <div class="audit-panel" style="display:none">
      <div class="stat-row">${pills}</div>
      ${p.trace_notes ? `<div class="trace-box">${p.trace_notes}</div>` : ''}
    </div>
  </div>`;
}

/* ══════════════════════════════════════════════════════
   BRIEF CARDS (T1/T2)
══════════════════════════════════════════════════════ */
function renderBriefs(briefs) {
  const grid = document.querySelector('.brief-grid');
  const players = [...(briefs.tier_1||[]), ...(briefs.tier_2||[])];
  grid.innerHTML = players.map(p => {
    const tc = p.tier <= 2 ? `t${p.tier}-card` : '';
    const posDrivers = p.course_fit_explanation?.positive_drivers?.slice(0,2) || [];
    const posHTML = posDrivers.length
      ? posDrivers.map(d => `<li class="fit-pos">${d}</li>`).join('')
      : '<li class="fit-pos">Fit analysis not available</li>';
    return `<div class="brief-card ${tc}">
      <div class="brief-name">${p.player_name} ${tierBadgeHTML(p.tier)}</div>
      <div class="brief-stats">VTS ${(+p.vts_final).toFixed(1)} · Win ${fmtPct(p.win_pct)} · Top10 ${fmtPct(p.top10_pct)}</div>
      <div class="brief-label">Course Fit Drivers</div>
      <ul class="fit-list fit-compact">${posHTML}</ul>
      <div class="brief-label">Venue History</div>
      <div class="brief-val">${p.venue_history_summary || '—'}</div>
      <div class="brief-label">Conviction</div>
      <div class="brief-val">${cleanConviction(p.conviction_statement) || '—'}</div>
      <div class="brief-risk">${cleanRawKeys(p.named_failure_condition?.split('|')[0]?.trim()) || ''}</div>
    </div>`;
  }).join('');
}

/* ══════════════════════════════════════════════════════
   ROUND LEARNING PANEL (generic — renders R1/R2/R3/Final)
══════════════════════════════════════════════════════ */
function renderRoundPanel(body, rData, roundNum) {
  const d = rData;
  if (!d || !d.model_performance || !d.trait_audit) {
    body.innerHTML = `<div class="ri-card" style="color:#f87171;padding:1.5rem">
      <b>Round ${roundNum} data is incomplete.</b><br>
      <span style="font-size:.75rem;color:var(--muted)">Missing model_performance or trait_audit block. Rebuild this round's analysis file.</span>
    </div>`;
    return;
  }
  const mp = d.model_performance;
  const ta = d.trait_audit;
  const sg = d.sg_leader_averages;

  /* ── helpers ── */
  const sgFmt   = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2);
  const scoreFmt = v => v == null ? '—' : v === 0 ? 'E' : (v > 0 ? '+' : '') + v.toFixed(0);
  const posOf  = r => r.r1_pos_str || r.r1_pos;
  const ciLoaded   = d.course_insights_loaded || false;
  const enrSummary = d.enrichment_summary;

  function signalBadge(sig) {
    const cls = { validated:'ri-sig-val', mixed:'ri-sig-mix', neutral:'ri-sig-neu', weak:'ri-sig-weak', not_testable:'ri-sig-nt' };
    const lbl = { validated:'VALIDATED', mixed:'MIXED', neutral:'NEUTRAL', weak:'WEAK', not_testable:'N/A' };
    return `<span class="ri-sig-badge ${cls[sig]||''}">${lbl[sig]||sig}</span>`;
  }

  function confBadge(conf) {
    const cls = { 'direct':'sc-direct', 'proxy-confirmed':'sc-proxy-confirmed', 'weak-proxy':'sc-weak-proxy', 'not-testable':'sc-not-testable' };
    const lbl = { 'direct':'DIRECT', 'proxy-confirmed':'PROXY', 'weak-proxy':'WEAK-PROXY', 'not-testable':'N/A' };
    return `<span class="sc-badge ${cls[conf]||'sc-not-testable'}">${lbl[conf]||conf||'—'}</span>`;
  }

  function supportingTags(conf, enr) {
    const confMap = {
      'direct':          { cls: 'sc-direct',          lbl: 'DIRECT',     title: 'Direct — stat directly tests this trait (e.g. Scrambling → ARG)' },
      'proxy-confirmed': { cls: 'sc-proxy-confirmed', lbl: 'PROXY',      title: 'Proxy-confirmed — SG dimension + supplemental data both point same direction' },
      'weak-proxy':      { cls: 'sc-weak-proxy',      lbl: 'WEAK-PROXY', title: 'Weak proxy — directional only; single SG dimension or limited enrichment' },
      'not-testable':    { cls: 'sc-not-testable',    lbl: 'N/A',        title: 'Not testable — insufficient round data to confirm or deny' },
    };
    const tags = [];
    const cm = confMap[conf] || confMap['not-testable'];
    tags.push(`<span class="sc-badge ${cm.cls}" title="${cm.title}">${cm.lbl}</span>`);
    if (enr?.available && enr.enrichment_signal === 'upgraded') {
      tags.push(`<span class="sc-badge ri-enr-up" title="${(enr.enrichment_note||'').replace(/"/g,'&quot;')}">UPGRADED</span>`);
    }
    return tags.join(' ');
  }

  function traitLabel(key) {
    const def = TRAIT_KEY_MAP[key];
    return def ? def.label : key.replace(/_/g,' ');
  }

  /* ── 0. Methodology Legend ── */
  const legendHTML = `
    <div class="ri-card ri-card-wide ri-method-legend">
      <div class="ri-method-header">Evidence confidence</div>
      <div class="ri-method-grid">
        <span>${confBadge('direct')}</span><span>Stat directly measures this trait (e.g., Scrambling % &rarr; ARG Rough, D. Accuracy &rarr; OTT Accuracy)</span>
        <span>${confBadge('proxy-confirmed')}</span><span>SG category and enrichment data both point the same direction</span>
        <span>${confBadge('weak-proxy')}</span><span>Directional only &mdash; limited to a single proxy dimension</span>
        <span>${confBadge('not-testable')}</span><span>Insufficient data to confirm or deny the pre-tournament thesis</span>
        <span class="sc-badge ri-enr-up">UPGRADED</span><span>DataGolf proxy promoted the signal one tier (e.g., weak &rarr; neutral)</span>
      </div>
    </div>`;

  /* ── 1. Model Performance Summary Strip ── */
  const pt10 = mp.groups.pt_top10;
  const pt20 = mp.groups.pt_top20;
  const t1   = mp.groups.tier1;
  const t2   = mp.groups.tier2;
  const rho  = mp.spearman_rho;
  const rhoColor = rho > 0.35 ? '#4ade80' : rho > 0.18 ? '#fcd34d' : '#f87171';

  const modelStripHTML = `
    <div class="ri-model-strip">
      <div class="ri-model-pill">
        <span class="ri-model-label">Rank Correlation</span>
        <span class="ri-model-val" style="color:${rhoColor}">${rho > 0 ? '+' : ''}${rho.toFixed(2)}</span>
        <span class="ri-model-sub">Spearman ρ</span>
      </div>
      <div class="ri-model-pill">
        <span class="ri-model-label">PT Top 10 &rarr; R${roundNum} Top 10</span>
        <span class="ri-model-val">${pt10.in_r1_top10}/${pt10.n}</span>
        <span class="ri-model-sub">avg pos ${pt10.avg_r1_pos?.toFixed(0)}</span>
      </div>
      <div class="ri-model-pill">
        <span class="ri-model-label">PT Top 10 &rarr; R${roundNum} Top 20</span>
        <span class="ri-model-val">${pt10.in_r1_top20}/${pt10.n}</span>
        <span class="ri-model-sub">avg score ${scoreFmt(pt10.avg_r1_score)}</span>
      </div>
      <div class="ri-model-pill">
        <span class="ri-model-label">Tier 1 Performance</span>
        <span class="ri-model-val">${t1.in_r1_top10}/${t1.n} in top 10</span>
        <span class="ri-model-sub">avg pos ${t1.avg_r1_pos?.toFixed(0)}</span>
      </div>
      <div class="ri-model-pill">
        <span class="ri-model-label">Tier 1+2</span>
        <span class="ri-model-val">${mp.groups.tier1_2.in_r1_top20}/${mp.groups.tier1_2.n} in top 20</span>
        <span class="ri-model-sub">avg score ${scoreFmt(mp.groups.tier1_2.avg_r1_score)}</span>
      </div>
    </div>`;

  /* ── 2. SG Leader summary (top 13 R1 = tied positions) ── */
  const sgTop = sg.top10;
  const sgF   = sg.full_field;
  const lln   = d.live_lean_notes || {};
  const puttNote = lln.putt_caution && lln.putt_outliers?.length
    ? `Birdie conversion; caution: outlier spikes (${lln.putt_outliers.map(p => `${p.player.split(' ').slice(-1)[0]} +${(p.sg_putt||0).toFixed(1)}`).join(', ')})`
    : 'Birdie conversion; check for outlier putting spikes before weighting';
  const sgRows = [
    ['SG: Approach', sgTop.sg_app, sgF.sg_app, 'Primary venue lever — APP distance bands'],
    ['SG: Putting',  sgTop.sg_putt, sgF.sg_putt, puttNote],
    ['SG: Around Green', sgTop.sg_arg, sgF.sg_arg, 'Scrambling — bunker + rough recovery'],
    ['SG: Off Tee',  sgTop.sg_ott, sgF.sg_ott, 'Positional driving; leaders modestly above field'],
  ].map(([label, top, field, note]) => {
    const d = (top != null && field != null) ? top - field : null;
    const dFmt = d == null ? '—' : (d >= 0 ? '+' : '') + d.toFixed(3);
    const clr  = d == null ? '' : d > 0.5 ? 'color:#4ade80' : d > 0 ? 'color:#fcd34d' : 'color:var(--muted)';
    const fieldFmt = field === 0 ? '<span title="SG is relative to field average — full-field mean is 0 by definition">0 (baseline)</span>' : sgFmt(field);
    return `<tr>
      <td style="font-weight:600">${label}</td>
      <td style="color:#4ade80">${sgFmt(top)}</td>
      <td style="color:var(--muted)">${fieldFmt}</td>
      <td style="${clr}">${dFmt}</td>
      <td style="font-size:.68rem;color:var(--muted)">${note}</td>
    </tr>`;
  }).join('');

  // CI proxy table for Trait Winners section
  let ciProxySection = '';
  if (ciLoaded) {
    const _appEnr  = ta.app_wedge?.enrichment;
    const _argEnr  = ta.arg_rough?.enrichment;
    const _accEnr  = ta.ott_accuracy?.enrichment;
    const _girEnr  = ta.app_150_200?.enrichment;
    const _distEnr = ta.ott_distance?.enrichment;
    if (_appEnr?.available && _argEnr?.available) {
      const SIG_THRESH = { '%': 10, 'ft': 2.0, 'yds': 3.0 };
      const ciRows2 = [
        { label:'Scrambling %', top:_argEnr.top10_primary, field:_argEnr.field_primary, delta:_argEnr.delta_primary, dir:'higher_better', unit:'%',   note:'ARG Rough / ARG Bunker' },
        { label:'D. Accuracy',  top:_accEnr?.top10_primary, field:_accEnr?.field_primary, delta:_accEnr?.delta_primary, dir:'higher_better', unit:'%',   note:'OTT Accuracy — direct' },
        { label:'GIR',          top:_girEnr?.top10_primary, field:_girEnr?.field_primary, delta:_girEnr?.delta_primary, dir:'higher_better', unit:'%',   note:'APP 150-200 / Par-5' },
        { label:'Fairway Prox', top:_appEnr.top10_primary  != null ? _appEnr.top10_primary/12  : null,
                                field:_appEnr.field_primary != null ? _appEnr.field_primary/12  : null,
                                delta:_appEnr.delta_primary != null ? _appEnr.delta_primary/12  : null,
                                dir:'lower_better', unit:'ft', note:'APP Wedge / APP 100-150' },
        { label:'D. Distance',  top:_distEnr?.top10_primary, field:_distEnr?.field_primary, delta:_distEnr?.delta_primary, dir:'higher_better', unit:'yds', note:'OTT Distance — gap negligible' },
      ].map(({label, top, field, delta, dir, unit, note}) => {
        const tf = v => v != null ? v.toFixed(1) + unit : '—';
        const df = (d2, u, direction) => {
          if (d2 == null) return '—';
          if (direction === 'lower_better') return `${d2.toFixed(1)}${u} closer`;
          return (d2 >= 0 ? '+' : '') + d2.toFixed(1) + u;
        };
        const clr = delta == null ? '' : delta > 0 ? (Math.abs(delta) >= (SIG_THRESH[unit] || 5) ? 'color:#4ade80' : 'color:#fcd34d') : 'color:#f87171';
        return `<tr>
          <td style="font-weight:600">${label}</td>
          <td style="color:#4ade80">${tf(top)}</td>
          <td style="color:var(--muted)">${tf(field)}</td>
          <td style="${clr}">${df(delta, unit, dir)}</td>
          <td style="font-size:.68rem;color:var(--muted)">${note}</td>
        </tr>`;
      }).join('');
      ciProxySection = `
        <div style="margin-top:.9rem">
          <div style="font-size:.7rem;font-weight:600;color:var(--accent);letter-spacing:.04em;margin-bottom:.35rem">
            COURSE INSIGHTS PROXY LAYER <span style="font-weight:400;color:var(--muted);font-size:.67rem">(DataGolf &middot; supplemental, not PGAT official)</span>
          </div>
          <table class="ri-sg-table">
            <thead><tr><th>Metric</th><th>Leaders avg</th><th>Field avg</th><th>Gap</th><th>Trait proxy</th></tr></thead>
            <tbody>${ciRows2}</tbody>
          </table>
        </div>`;
    }
  }

  const traitWinnersHTML = `
    <div class="ri-card ri-card-wide">
      <h4>Trait Winners — R${roundNum} SG Evidence</h4>
      <table class="ri-sg-table">
        <thead><tr><th>Category</th><th>Leaders avg</th><th>Field avg</th><th title="Delta = Leaders Avg − Field Avg. Positive = leaders gained more strokes than the field in this SG category.">Delta</th><th>Note</th></tr></thead>
        <tbody>${sgRows}</tbody>
      </table>
      ${ciProxySection}
      <div class="ri-note">
        Proxy mapping: SG:Approach &rarr; APP Wedge / APP 100-150 / APP 150-200 / Par-5.
        SG:Putting &rarr; Putt Short Conv / Putt Lag.
        SG:Around Green &rarr; ARG Rough / ARG Bunker.
        SG:OTT &rarr; OTT Accuracy / OTT Distance.
        Single-round SG contains high variance &mdash; treat as directional, not definitive.
      </div>
    </div>`;

  /* ── 3. Model vs Realized matrix ── */
  const traitOrder = ['app_wedge','app_100_150','app_150_200','ott_accuracy','ott_distance',
                      'putt_short_conv','putt_lag','arg_rough','arg_bunker','par5_scoring'];

  const mvRrows = traitOrder.map(tk => {
    const t = ta[tk];
    if (!t) return '';
    const wPct = Math.round(t.venue_weight * 100);
    const delta = t.trait_delta;
    const sg_d  = t.sg_delta;
    const dStr  = delta != null ? (delta >= 0 ? '+' : '') + delta.toFixed(1) : '—';
    const dClr  = delta == null ? '' : delta > 5 ? '#4ade80' : delta > 0 ? '#fcd34d' : '#f87171';
    return `<tr>
      <td>${traitLabel(tk)}</td>
      <td style="text-align:center">${wPct}%</td>
      <td style="text-align:center;color:${dClr};font-weight:600">${dStr}</td>
      <td style="text-align:center">${sg_d != null ? sgFmt(sg_d) : '—'}</td>
      <td class="mvr-signal-cell">${signalBadge(t.signal)}<div class="mvr-supp-tags">${supportingTags(t.source_confidence, t.enrichment)}</div></td>
    </tr>`;
  }).join('');

  const modelVsRealHTML = `
    <div class="ri-card">
      <h4>Model vs Realized</h4>
      <div class="ri-note" style="margin-bottom:.5rem">
        Trait delta: pre-tournament trait percentile avg for the round's top-10 leaders vs full field.
        Positive = leaders were already stronger in this trait before the event.
      </div>
      <div class="mvr-scroll">
        <table class="ri-mv-table">
          <thead><tr><th>Trait</th><th>Model Wt</th><th>Trait &Delta;</th><th>SG &Delta;</th><th>Signal</th></tr></thead>
          <tbody>${mvRrows}</tbody>
        </table>
      </div>
      <div class="ri-note" style="margin-top:.3rem">Evidence quality: DIRECT &middot; PROXY &middot; WEAK-PROXY &middot; N/A${ciLoaded ? ' &middot; UPGRADED = DataGolf proxy lifted the verdict' : ''}.</div>
    </div>`;

  /* ── 4. Weekend Risers ── */
  const slipNames = new Set((d.slippage_risk || []).map(r => r.r1_name));
  const validRisers = (d.weekend_risers || []).filter(r => (r.sg_app ?? 0) > 0.5 && !slipNames.has(r.r1_name));
  const risersHTML = validRisers.length === 0
    ? '<p class="ri-placeholder">No clear risers matching course-fit thesis.</p>'
    : validRisers.map(r => `
      <div class="ri-player-row">
        <div class="ri-player-name">${r.r1_name}</div>
        <div class="ri-player-meta">
          <span class="ri-pos-chip">${posOf(r)}</span>
          <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
          ${r.pt_tier ? `<span class="ri-tier-chip">T${r.pt_tier}</span>` : ''}
        </div>
        <div class="ri-player-sg">
          APP: <b style="color:${r.sg_app>0.5?'#4ade80':'var(--muted)'}">${sgFmt(r.sg_app)}</b>
          ARG: <b style="color:${r.sg_arg>0.3?'#4ade80':'var(--muted)'}">${sgFmt(r.sg_arg)}</b>
          PUTT: <b>${sgFmt(r.sg_putt)}</b>
          OTT: <b>${sgFmt(r.sg_ott)}</b>
        </div>
        <div class="ri-player-note">${r.thesis_note || ''}</div>
      </div>`).join('');

  const weekendRisersHTML = `
    <div class="ri-card">
      <h4>Weekend Risers</h4>
      <div class="ri-note" style="margin-bottom:.4rem">
        Players whose round stat profile validates the course-fit thesis (approach-led, &minus;3 or better).
        Not simply "who scored low" — filtered for SG:APP > +0.5 backing.
      </div>
      ${risersHTML}
    </div>`;

  /* ── 5. Slippage Risk ── */
  const slipHTML = d.slippage_risk.length === 0
    ? `<p class="ri-placeholder">No fragility flags in current R${roundNum} top 20.</p>`
    : d.slippage_risk.map(r => `
      <div class="ri-player-row ri-player-risk">
        <div class="ri-player-name">${r.r1_name}</div>
        <div class="ri-player-meta">
          <span class="ri-pos-chip">${posOf(r)}</span>
          <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
          ${r.pt_tier ? `<span class="ri-tier-chip">T${r.pt_tier}</span>` : `<span class="ri-tier-chip" style="background:#33415544">unranked</span>`}
        </div>
        <div class="ri-player-sg">
          APP: <b style="color:${r.sg_app!=null&&r.sg_app<0?'#f87171':'var(--muted)'}">${sgFmt(r.sg_app)}</b>
          PUTT: <b style="color:${r.sg_putt>2?'#fcd34d':'var(--muted)'}">${sgFmt(r.sg_putt)}</b>
          ARG: <b>${sgFmt(r.sg_arg)}</b>
          OTT: <b>${sgFmt(r.sg_ott)}</b>
        </div>
        <div class="ri-player-note ri-risk-note">${(r.risk_flags||[]).join(' | ')}</div>
      </div>`).join('');

  const slippageHTML = `
    <div class="ri-card">
      <h4>Slippage Risk</h4>
      <div class="ri-note" style="margin-bottom:.4rem">
        Top-20 players with fragile stat profiles. Round driven by putting spike (SG:PUTT > +2.0)
        while approach was weak — a pattern with high next-round regression risk at TPC River Highlands.
      </div>
      ${slipHTML}
    </div>`;

  /* ── 6. Favorites Tracker ── */
  const favNames = [...favorites];
  let favContent;
  if (favNames.length === 0) {
    favContent = '<p class="ri-placeholder">Star players in the field table to track them here.</p>';
  } else {
    const favRows = favNames.map(name => {
      // Find R1 position
      const r1Row = d.leaderboard_snapshot.find(r =>
        r.r1_name.toLowerCase().includes(name.split(',')[0]?.toLowerCase().trim() || '') ||
        name.toLowerCase().includes(r.r1_name.split(' ').slice(-1)[0]?.toLowerCase() || '')
      );
      const ptPlayer = allPlayers.find(p => p.player_name === name);
      const pos   = r1Row ? r1Row.r1_pos_str : 'TBD';
      const score = r1Row ? scoreFmt(r1Row.r1_score) : '—';
      const sgApp = r1Row ? sgFmt(r1Row.sg_app) : '—';
      const sgPutt = r1Row ? sgFmt(r1Row.sg_putt) : '—';
      const nameDisplay = name.split(',').reverse().join(' ').trim();
      return `<div class="ri-fav-row">
        <span class="ri-fav-name">★ ${nameDisplay}</span>
        <span class="ri-pos-chip">${pos}</span>
        <span class="ri-score-chip">${score}</span>
        <span style="font-size:.7rem;color:var(--muted)">APP ${sgApp} · PUTT ${sgPutt}</span>
        ${ptPlayer ? `<span style="font-size:.67rem;color:var(--muted)">VTS ${(+ptPlayer.vts_final).toFixed(1)} · T${ptPlayer.tier}</span>` : ''}
      </div>`;
    }).join('');
    favContent = favRows;
  }

  const favTrackerHTML = `
    <div class="ri-card">
      <h4>Favorites Tracker <span style="font-size:.62rem;color:var(--muted);font-weight:400;cursor:help" title="Favorites are session-only and reset on page reload — not persisted to browser storage">session-only</span></h4>
      ${favContent}
    </div>`;

  /* ── 7. Trait Reality Check ── */
  const appDelta    = ta.app_wedge?.trait_delta ?? ta.app_100_150?.trait_delta;
  const ottAccDelta = ta.ott_accuracy?.trait_delta;
  const ottDistSig  = ta.ott_distance?.signal;
  const argSignal   = ta.arg_rough?.signal;
  const par5Signal  = ta.par5_scoring?.signal;
  const argEnr      = ta.arg_rough?.enrichment;
  const par5Enr     = ta.par5_scoring?.enrichment;
  const argUpgraded = argEnr?.enrichment_signal === 'upgraded';
  const par5Upgraded = par5Enr?.enrichment_signal === 'upgraded';

  /* R3-specific reality check items (54-hole validation) */
  let r3RealityItems = '';
  if (roundNum >= 3) {
    const r2PuttOutliers  = (r2Data?.live_lean_notes?.putt_outliers  || []).map(p => p.player);
    const r2SlipWatch     = (r2Data?.live_lean_notes?.watch_next_round || []).filter(w => w.flag_type === 'slippage').map(w => w.player);
    const watchNames      = [...new Set([...r2PuttOutliers, ...r2SlipWatch])];

    const regressionConfirmed = watchNames.filter(name => {
      const r3Row = d.leaderboard_snapshot.find(r => r.r1_name === name);
      const r2Row = r2Data?.leaderboard_snapshot?.find(r => r.r1_name === name);
      return r3Row && r2Row && r3Row.r1_pos > r2Row.r1_pos + 2;
    });
    const regressionMissed = watchNames.filter(name => {
      const r3Row = d.leaderboard_snapshot.find(r => r.r1_name === name);
      const r2Row = r2Data?.leaderboard_snapshot?.find(r => r.r1_name === name);
      return r3Row && r2Row && r3Row.r1_pos <= r2Row.r1_pos;
    });
    const puttRegressionText = watchNames.length === 0
      ? 'No R2 putting outliers were flagged for R3 regression.'
      : regressionConfirmed.length > 0
        ? `Confirmed for ${regressionConfirmed.join(', ')} &mdash; fell in standings as expected.${regressionMissed.length ? ` Held position: ${regressionMissed.join(', ')}.` : ' All flagged players regressed.'}`
        : `R2 outliers (${watchNames.slice(0, 4).join(', ')}) did not regress significantly in R3 &mdash; putting spike may have sustained or model flag missed.`;

    const cl54 = cumulativeData;
    const par5Hist = cl54?.cumulative_signals?.par5_scoring?.signal_history || [];
    const par5Sustained = par5Hist.filter(s => ['validated', 'mixed'].includes(s)).length >= 2;
    const validatedCount = cl54?.cumulative_signals
      ? Object.values(cl54.cumulative_signals).filter(cs => cs.consensus === 'validated').length : 0;
    const cumulativeAppSg = sg.top10?.sg_app ?? 0;
    const app54Strong = cumulativeAppSg > 1.5;

    r3RealityItems = `
        <div class="ri-reality-item ${app54Strong ? 'ri-reality-yes' : 'ri-reality-mixed'}">
          <div class="ri-reality-q">Did approach dominate through 54 holes?</div>
          <div class="ri-reality-a">${app54Strong
            ? `Yes &mdash; cumulative SG:APP +${cumulativeAppSg.toFixed(2)} for 54-hole leaders vs field. Approach backed across all 3 rounds.`
            : `Mixed &mdash; cumulative SG:APP ${sgFmt(sg.top10?.sg_app)} for 54-hole leaders; approach was not a clear separator across all 3 rounds.`
          }</div>
        </div>
        <div class="ri-reality-item ${regressionConfirmed.length > 0 ? 'ri-reality-yes' : watchNames.length > 0 ? 'ri-reality-caution' : 'ri-reality-neutral'}">
          <div class="ri-reality-q">Putting regression confirmed (R2 outlier spikers)?</div>
          <div class="ri-reality-a">${puttRegressionText}</div>
        </div>
        <div class="ri-reality-item ${par5Sustained ? 'ri-reality-yes' : 'ri-reality-mixed'}">
          <div class="ri-reality-q">Par-5 scoring through R3?</div>
          <div class="ri-reality-a">${par5Sustained
            ? `Sustained &mdash; par-5 scoring signal ${par5Hist.slice(0, 3).join(' &rarr; ')} across ${par5Hist.length} round(s). Iron quality remained a differentiator through 54 holes.`
            : `Inconsistent &mdash; signal history: ${par5Hist.slice(0, 3).join(' &rarr; ') || 'insufficient data'}. Par-70 limits par-5 opportunity (only 2 holes).`
          }</div>
        </div>
        <div class="ri-reality-item ${validatedCount >= 6 ? 'ri-reality-yes' : validatedCount >= 4 ? 'ri-reality-mixed' : 'ri-reality-neutral'}">
          <div class="ri-reality-q">Course fit validation through 3 rounds?</div>
          <div class="ri-reality-a">${validatedCount >= 6
            ? `Strong &mdash; ${validatedCount}/10 traits validated cumulatively. TPC River Highlands rewarded the predicted trait profile across 3 rounds.`
            : validatedCount >= 4
              ? `Partial &mdash; ${validatedCount}/10 traits validated cumulatively. Core approach and OTT traits confirmed; secondary traits mixed.`
              : `Limited &mdash; ${validatedCount}/10 traits validated cumulatively. Pre-tournament model had partial course-fit confirmation.`
          }</div>
        </div>`;
  }

  const realityHTML = `
    <div class="ri-card ri-card-wide">
      <h4>Trait Reality Check</h4>
      <div class="ri-reality-grid">
        <div class="ri-reality-item ${(appDelta ?? 0) > 6 ? 'ri-reality-yes' : 'ri-reality-mixed'}">
          <div class="ri-reality-q">Did approach dominate?</div>
          <div class="ri-reality-a">${(appDelta ?? 0) > 6
            ? `Yes &mdash; APP trait delta +${appDelta?.toFixed(0)} favored round leaders; SG:APP +${(sg.top10.sg_app??0).toFixed(2)} vs field.${ciLoaded && ta.app_wedge?.enrichment?.available ? ` Fairway proximity: leaders hit approach ${(ta.app_wedge.enrichment.delta_primary/12).toFixed(1)}ft closer to pin.` : ''}`
            : 'Mixed evidence.'}</div>
        </div>
        <div class="ri-reality-item ${(sg.top10.sg_putt??0) > 0.8 ? 'ri-reality-caution' : 'ri-reality-mixed'}">
          <div class="ri-reality-q">Did putting carry the day?</div>
          <div class="ri-reality-a">${(sg.top10.sg_putt??0) > 0.8
            ? `Elevated &mdash; SG:PUTT +${(sg.top10.sg_putt??0).toFixed(2)} for R${roundNum} leaders${lln.putt_caution && lln.putt_outliers?.length ? `, but outlier spikes (${lln.putt_outliers.map(p=>`${p.player.split(' ').slice(-1)[0]} +${(p.sg_putt||0).toFixed(1)}`).join(', ')}) skew the avg &mdash; not uniformly the separator` : ''}.`
            : `Putting was not a primary separator in R${roundNum}.`}</div>
        </div>
        <div class="ri-reality-item ${ottAccDelta > 5 ? 'ri-reality-yes' : 'ri-reality-mixed'}">
          <div class="ri-reality-q">Accuracy &gt; Distance?</div>
          <div class="ri-reality-a">${ottAccDelta > 5
            ? `Yes &mdash; OTT Accuracy trait delta +${ottAccDelta?.toFixed(0)}.${ciLoaded && ta.ott_accuracy?.enrichment?.available ? ` Driving accuracy gap: top10 hit ${(ta.ott_accuracy.enrichment.delta_primary).toFixed(1)}pp more fairways.` : ''} OTT Distance was ${ottDistSig === 'weak' ? 'counter-productive (delta ' + (ta.ott_distance?.trait_delta?.toFixed(1) ?? '?') + ')' : 'neutral'}.`
            : 'Insufficient signal.'}</div>
        </div>
        <div class="ri-reality-item ${argSignal === 'validated' ? 'ri-reality-yes' : argSignal === 'mixed' ? 'ri-reality-mixed' : 'ri-reality-neutral'}">
          <div class="ri-reality-q">Around-green punch?</div>
          <div class="ri-reality-a">${argSignal === 'validated' && argUpgraded
            ? `Scrambling confirmed &mdash; top10=${argEnr.top10_primary?.toFixed(1)}% vs field=${argEnr.field_primary?.toFixed(1)}% (+${argEnr.delta_primary?.toFixed(1)}pp). ARG trait delta +${(ta.arg_rough?.trait_delta??0).toFixed(0)} (rough) / +${(ta.arg_bunker?.trait_delta??0).toFixed(0)} (bunker). Leaders who scrambled well (SG:ARG +${(sg.top10.sg_arg??0).toFixed(2)}) were a real separator.`
            : argSignal === 'validated'
            ? `Validated &mdash; ARG trait delta +${(ta.arg_rough?.trait_delta??0).toFixed(0)} (rough) / +${(ta.arg_bunker?.trait_delta??0).toFixed(0)} (bunker). SG:ARG +${(sg.top10.sg_arg??0).toFixed(2)} for leaders.`
            : `Mixed signal. ARG trait delta +${(ta.arg_rough?.trait_delta??0).toFixed(0)} (rough) / +${(ta.arg_bunker?.trait_delta??0).toFixed(0)} (bunker). SG:ARG +${(sg.top10.sg_arg??0).toFixed(2)} for leaders &mdash; meaningful but secondary to approach.`
          }</div>
        </div>
        <div class="ri-reality-item ${par5Signal === 'validated' ? 'ri-reality-mixed' : (ta.par5_scoring?.trait_delta??0) > 4 ? 'ri-reality-mixed' : 'ri-reality-neutral'}">
          <div class="ri-reality-q">Par-5 scoring?</div>
          <div class="ri-reality-a">${par5Upgraded
            ? `Supported via GIR gap (top10=${par5Enr.top10_primary?.toFixed(1)}% vs field=${par5Enr.field_primary?.toFixed(1)}%, +${par5Enr.delta_primary?.toFixed(1)}pp). Trait delta +${(ta.par5_scoring?.trait_delta??0).toFixed(0)} &mdash; iron quality rewarded. Par-70 limits scope (only 2 par-5s).`
            : `Trait delta +${(ta.par5_scoring?.trait_delta??0).toFixed(0)} &mdash; leaders had better par-5 profiles, directionally supporting the 3% weight. Short par-70 limits birdie opportunities on par-5s here (only 2 par-5s).`
          }</div>
        </div>
        ${r3RealityItems}
      </div>
    </div>`;

  /* ── 8. Round N+1 Live Lean (data-driven from live_lean_notes) ── */
  const leanUpItems = (lln.lean_up_traits || []).map(t => {
    const label   = traitLabel(t.trait);
    const delta   = t.delta != null ? `+${t.delta.toFixed(0)} pts` : '';
    const conf    = t.confidence || '';
    const enrNote = t.enr_signal === 'upgraded' ? ' · enrichment upgraded' : t.enr_signal === 'confirmed' ? ' · enrichment confirmed' : '';
    const parts   = [delta, conf].filter(Boolean).join(' · ');
    return `<li><b>${label}</b> &mdash; validated${parts ? ` (${parts}${enrNote})` : enrNote}</li>`;
  }).join('') || '<li>No traits reached validated threshold this round.</li>';

  const nextRoundStr = lln.next_round ? `R${lln.next_round}` : 'Final';
  const leanDownItems = (lln.lean_down_traits || []).map(t => {
    const label = traitLabel(t.trait);
    const delta = t.delta != null ? `${t.delta > 0 ? '+' : ''}${t.delta.toFixed(1)}` : '';
    return `<li><b>${label}</b> &mdash; weak${delta ? ` (${delta})` : ''}, deprioritize ${nextRoundStr}</li>`;
  }).join('');

  const puttCautionItem = lln.putt_caution
    ? `<li><b>Putt Short Conv / Putt Lag</b> &mdash; SG:PUTT leaders avg inflated by outlier rounds${lln.putt_outliers?.length ? ` (${lln.putt_outliers.map(p=>`${p.player.split(' ').slice(-1)[0]} +${(p.sg_putt||0).toFixed(1)}`).join(', ')})` : ''}. Pre-tournament putt profiles were neutral &mdash; don&apos;t over-weight the spike.</li>`
    : '';

  const watchItems = (lln.watch_next_round || []).map(w => {
    const score   = w.score != null ? (w.score === 0 ? 'E' : (w.score > 0 ? '+' : '') + w.score.toFixed(0)) : '';
    const appStr  = w.sg_app  != null ? ` APP ${w.sg_app  > 0 ? '+' : ''}${w.sg_app.toFixed(2)}`  : '';
    const puttStr = w.sg_putt != null ? ` PUTT ${w.sg_putt > 0 ? '+' : ''}${w.sg_putt.toFixed(2)}` : '';
    return `<li>${w.player} (${w.pos_str}, ${score}${appStr}${puttStr}) &mdash; ${w.note}</li>`;
  }).join('') || '<li>No fragility flags identified.</li>';

  const liveLeanHTML = `
    <div class="ri-card ri-card-wide ri-live-lean">
      <div class="ri-live-lean-header">
        <span class="ri-live-badge" ${lln.next_round === 4 ? 'style="background:#f5c518;color:#1a1a1a;border-color:#b8940f"' : ''}>${!lln.next_round ? 'FINAL ROUND RECAP' : lln.next_round === 4 ? 'FINAL ROUND LIVE LEAN' : `ROUND ${lln.next_round} LIVE LEAN`}</span>
        <span style="font-size:.68rem;color:var(--muted);margin-left:.5rem">
          Provisional in-tournament interpretation layer &mdash; not a permanent model rewrite
        </span>
      </div>
      <div class="ri-live-lean-grid">
        <div>
          <div class="ri-lean-label">Keep unchanged</div>
          <ul class="ri-lean-list">
            <li>Base VTS rankings and pre-tournament trait weights</li>
            <li>Confidence bands and imputation status</li>
            <li>Anti-pattern flags remain active</li>
          </ul>
        </div>
        <div>
          <div class="ri-lean-label">Lean up</div>
          <ul class="ri-lean-list ri-lean-up">${leanUpItems}</ul>
        </div>
        <div>
          <div class="ri-lean-label">Lean down</div>
          <ul class="ri-lean-list ri-lean-down">
            ${leanDownItems}
            ${puttCautionItem}
          </ul>
        </div>
        <div>
          <div class="ri-lean-label">${!lln.next_round ? 'Final assessment' : lln.next_round === 4 ? 'Watch for Final Round' : `Watch for R${lln.next_round}`}</div>
          <ul class="ri-lean-list">
            ${watchItems}
            <li>${lln.rho_note || `Rank correlation ρ = ${rho.toFixed(2)} &mdash; one round is noisy; field remains tightly bunched.`}</li>
          </ul>
        </div>
      </div>
    </div>`;

  /* ── 10. R2+ Detailed Assessment (collapsible) ── */
  let r2DetailedHTML = '';
  if (roundNum >= 2) {
    const traitOrderFull = ['app_wedge','app_100_150','app_150_200','ott_accuracy','ott_distance',
                            'putt_short_conv','putt_lag','arg_rough','arg_bunker','par5_scoring'];
    const wrisersMap = Object.fromEntries(d.weekend_risers.map(r => [r.r1_name, r]));

    function r2Status(r) {
      const p = r.pt_rank, pos = r.r1_pos;
      if (p != null && p <= 10 && pos <= 10)  return {cls:'r2-stat-val',   lbl:'Validated'};
      if (pos <= 10 && (p == null || p > 10)) return {cls:'r2-stat-over',  lbl:'Overperforming'};
      if (p != null && p <= 10 && pos > 20)  return {cls:'r2-stat-under', lbl:'Lagging'};
      if (pos <= 20 && p != null && p <= 20) return {cls:'r2-stat-track', lbl:'On Track'};
      return {cls:'', lbl:''};
    }

    /* Sub 1 — Leaderboard vs Pre-Tournament VTS Model */
    const vtsRows = [...d.leaderboard_snapshot]
      .sort((a,b) => a.r1_pos - b.r1_pos).slice(0, 20)
      .map(r => {
        const st = r2Status(r);
        const wr = wrisersMap[r.r1_name];
        const badge = st.lbl ? `<span class="r2-status-badge ${st.cls}">${st.lbl}</span>` : '&mdash;';
        return `<tr>
          <td>${r.r1_pos_str || r.r1_pos}</td>
          <td style="font-weight:600">${r.r1_name}</td>
          <td style="color:#4ade80">${scoreFmt(r.r1_score)}</td>
          <td style="color:var(--muted)">${r.pt_rank || '&mdash;'}</td>
          <td>${r.pt_vts != null ? r.pt_vts.toFixed(1) : '&mdash;'}</td>
          <td>${badge}</td>
          <td class="r2-thesis-col">${wr?.thesis_note || ''}</td>
        </tr>`;
      }).join('');

    const sub1HTML = `
      <div class="r2-subsection">
        <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
          <span class="r2-sub-chev">&#x25B8;</span> Leaderboard vs Pre-Tournament VTS Model
        </button>
        <div class="r2-sub-body">
          <p class="r2-sub-note">Top 20 by current position &middot; Status compares R${roundNum} result to pre-tournament model expectation.</p>
          <div class="r2-scroll">
            <table class="r2-vts-table">
              <thead><tr><th>Pos</th><th>Player</th><th>Score</th><th>PT Rank</th><th>VTS</th><th>Status</th><th>Thesis Note</th></tr></thead>
              <tbody>${vtsRows}</tbody>
            </table>
          </div>
        </div>
      </div>`;

    /* Sub 2 — Trait Reality Check Cards */
    const traitCards2 = traitOrderFull.map(tk => {
      const t = ta[tk];
      if (!t) return '';
      const w = Math.round(t.venue_weight * 100);
      const dStr = t.trait_delta != null ? (t.trait_delta >= 0 ? '+' : '') + t.trait_delta.toFixed(1) : '&mdash;';
      const evidence = t.enrichment?.enrichment_note
        ? t.enrichment.enrichment_note
        : `Trait Δ ${dStr} &middot; SG:${(t.sg_proxy || '').replace('sg_','').toUpperCase()} top10 ${sgFmt(t.sg_top10)} vs field ${sgFmt(t.sg_field || 0)}`;
      const bdrClr = {validated:'#4ade80',mixed:'#d97706',neutral:'#94a3b8',weak:'#f87171',not_testable:'#475569'}[t.signal] || '#475569';
      return `<div class="r2-trait-card" style="border-left-color:${bdrClr}">
        <div class="r2-trait-header">
          <span class="r2-trait-name">${traitLabel(tk)}</span>
          <span class="r2-trait-wt">${w}%</span>
          ${signalBadge(t.signal)}
        </div>
        <div class="r2-trait-ev">${evidence}</div>
        <div class="r2-trait-ft">${supportingTags(t.source_confidence, t.enrichment)}</div>
      </div>`;
    }).join('');

    const sub2HTML = `
      <div class="r2-subsection">
        <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
          <span class="r2-sub-chev">&#x25B8;</span> Trait Reality Check
        </button>
        <div class="r2-sub-body">
          <p class="r2-sub-note">All 10 venue traits &middot; R${roundNum} data vs pre-tournament model weights.</p>
          <div class="r2-trait-grid">${traitCards2}</div>
        </div>
      </div>`;

    /* Sub 3 — Model vs Realized Tier Table */
    const tierDefs2 = [
      {key:'tier1',    lbl:'Tier 1'},
      {key:'tier2',    lbl:'Tier 2'},
      {key:'tier1_2',  lbl:'T1+T2 Combined'},
      {key:'pt_top10', lbl:'PT Model Top 10'},
      {key:'pt_top20', lbl:'PT Model Top 20'},
      {key:'all_field',lbl:'Full Field'},
    ];
    const tierRows2 = tierDefs2.map(td => {
      const g = mp.groups[td.key];
      if (!g) return '';
      const posClr = g.avg_r1_pos <= 15 ? '#4ade80' : g.avg_r1_pos <= 30 ? '#fcd34d' : 'var(--muted)';
      return `<tr>
        <td>${td.lbl}</td>
        <td>${g.n}</td>
        <td style="color:${posClr}">${g.avg_r1_pos != null ? g.avg_r1_pos.toFixed(1) : '&mdash;'}</td>
        <td style="color:#4ade80">${scoreFmt(g.avg_r1_score)}</td>
        <td>${g.in_r1_top10}/${g.n}</td>
        <td>${g.in_r1_top20}/${g.n}</td>
      </tr>`;
    }).join('');

    const sub3HTML = `
      <div class="r2-subsection">
        <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
          <span class="r2-sub-chev">&#x25B8;</span> Model vs Realized &mdash; Tier Performance
        </button>
        <div class="r2-sub-body">
          <div class="r2-scroll">
            <table class="r2-tier-table">
              <thead><tr><th>Tier</th><th>n</th><th>Avg Pos</th><th>Avg Score</th><th>Top 10</th><th>Top 20</th></tr></thead>
              <tbody>${tierRows2}</tbody>
            </table>
          </div>
          <p class="r2-sub-note" style="margin-top:.35rem">Spearman &rho; = ${rho.toFixed(3)} after R${roundNum} &middot; ${roundNum >= 3 ? '54-hole cumulative correlation &mdash; model-field separation at peak before Final.' : 'Separation sharpens through R3/Final as field spreads.'}</p>
        </div>
      </div>`;

    /* Sub 4 — Weekend Projection */
    const projRiserRows = validRisers.length === 0
      ? '<p class="ri-placeholder">No risers matching course-fit thesis this round.</p>'
      : [...validRisers]
          .sort((a,b) => (b.thesis_score||0) - (a.thesis_score||0))
          .map(r => {
            const sgApp2 = r.sg_app ?? 0;
            const structScore2 = sgApp2 >= 2.0 ? 3 : sgApp2 >= 0.5 ? 2 : 1;
            const filled = structScore2;
            const dots = '●'.repeat(filled) + '○'.repeat(3 - filled);
            return `<div class="r2-proj-row">
              <div class="r2-proj-player">
                <span class="r2-proj-name">${r.r1_name}</span>
                <span class="ri-pos-chip">${r.r1_pos_str || r.r1_pos}</span>
                <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
                ${r.pt_tier ? `<span class="ri-tier-chip">T${r.pt_tier}</span>` : ''}
                <span class="r2-thesis-dots" title="Thesis score ${r.thesis_score||0}/3">${dots}</span>
              </div>
              <div class="r2-proj-sg">
                APP <b style="color:${r.sg_app > 0.5 ? '#4ade80' : 'var(--muted)'}">${sgFmt(r.sg_app)}</b>
                ARG <b style="color:${r.sg_arg > 0.3 ? '#4ade80' : 'var(--muted)'}">${sgFmt(r.sg_arg)}</b>
                PUTT <b>${sgFmt(r.sg_putt)}</b>
                OTT <b>${sgFmt(r.sg_ott)}</b>
              </div>
              <div class="r2-proj-note">${r.thesis_note || ''}</div>
            </div>`;
          }).join('');

    const projSlipRows = d.slippage_risk.length === 0
      ? '<p class="ri-placeholder">No fragility flags in current top 20.</p>'
      : d.slippage_risk.map(r => `
          <div class="r2-slip-row">
            <span class="r2-proj-name">${r.r1_name}</span>
            <span class="ri-pos-chip">${r.r1_pos_str || r.r1_pos}</span>
            <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
            <span class="r2-slip-flags">${(r.risk_flags||[]).join(' &middot; ')}</span>
          </div>`).join('');

    const sub4HTML = `
      <div class="r2-subsection">
        <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
          <span class="r2-sub-chev">&#x25B8;</span> ${roundNum >= 3 ? 'Final Round Projection' : 'Weekend Projection'}
        </button>
        <div class="r2-sub-body">
          <div class="r2-proj-lbl">${roundNum >= 3 ? 'Final Round Risers' : 'Course-fit validated risers'} <span class="r2-proj-lbl-sub">(&bull;&bull;&bull; = strongest thesis)</span></div>
          ${projRiserRows}
          <div class="r2-proj-lbl" style="margin-top:.65rem">Slippage risk${roundNum >= 3 ? ' &mdash; R4 regression candidates' : ''}</div>
          ${projSlipRows}
          <p class="r2-sub-note" style="margin-top:.45rem">Thesis score &bull;&bull;&bull; = approach-led + scrambling + pre-tournament model basis. Slippage = putting-driven without approach backing.</p>
        </div>
      </div>`;

    /* Sub 5 — Engine Learning Flags */
    const cl = cumulativeData;
    let sub5HTML;
    if (cl && cl.cumulative_signals) {
      const learnRows = traitOrderFull.map(tk => {
        const cs = cl.cumulative_signals[tk];
        if (!cs) return '';
        const sClrMap = {validated:'#4ade80',mixed:'#fcd34d',neutral:'#94a3b8',weak:'#f87171'};
        const consensus = cs.consensus || '&mdash;';
        const consCls = {validated:'ri-sig-val',mixed:'ri-sig-mix',neutral:'ri-sig-neu',weak:'ri-sig-weak'}[cs.consensus] || 'ri-sig-nt';
        const sigHist = (cs.signal_history||[]).map((s,i) => {
          const clr = sClrMap[s] || '#94a3b8';
          const rnd = (cs.rounds_observed||[])[i] || (i+1);
          return `<span style="color:${clr}">R${rnd}: ${s}</span>`;
        }).join(' &middot; ');
        const deltaHist = (cs.delta_history||[]).map((dv,i) => {
          const rnd = (cs.rounds_observed||[])[i] || (i+1);
          return `R${rnd}: ${dv > 0 ? '+' : ''}${dv.toFixed(1)}`;
        }).join(', ');
        return `<div class="r2-learn-row">
          <div class="r2-learn-trait">${traitLabel(tk)}</div>
          <div class="r2-learn-hist">${sigHist}</div>
          <div><span class="ri-sig-badge ${consCls}">${consensus.toUpperCase()}</span></div>
          <div class="r2-learn-deltas">${deltaHist}</div>
        </div>`;
      }).join('');

      sub5HTML = `
        <div class="r2-subsection">
          <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
            <span class="r2-sub-chev">&#x25B8;</span> Engine Learning Flags
          </button>
          <div class="r2-sub-body">
            <p class="r2-sub-note">Cumulative signals across ${cl.rounds_completed || roundNum} rounds &middot; Consensus = direction both rounds agreed on.</p>
            <div class="r2-learn-grid">${learnRows}</div>
          </div>
        </div>`;
    } else {
      sub5HTML = `
        <div class="r2-subsection">
          <button class="r2-sub-hdr" onclick="this.parentElement.classList.toggle('r2-sub-open')">
            <span class="r2-sub-chev">&#x25B8;</span> Engine Learning Flags
          </button>
          <div class="r2-sub-body"><p class="ri-placeholder">Cumulative learning data not yet available.</p></div>
        </div>`;
    }

    /* OTT Accuracy flag card — visible outside the collapsible when signal is mixed/neutral and weight >= 10% */
    let ottFlagCardHTML = '';
    if (cl && cl.cumulative_signals) {
      const traitWeights = { ott_accuracy: 0.14, ott_distance: 0.05, putt_lag: 0.10 };
      const flagCards = Object.entries(cl.cumulative_signals)
        .filter(([tk, cs]) => {
          const w = traitWeights[tk] ?? (TRAIT_KEY_MAP[tk]?.weight ?? 0);
          return w >= 0.10 && (cs.consensus === 'mixed' || cs.consensus === 'neutral');
        })
        .map(([tk, cs]) => {
          const w = traitWeights[tk] ?? (TRAIT_KEY_MAP[tk]?.weight ?? 0);
          const label = TRAIT_KEY_MAP[tk]?.label || tk.replace(/_/g,' ');
          const dHist = (cs.delta_history || []).map((dv, i) => `R${(cs.rounds_observed||[])[i]||i+1}: ${dv > 0 ? '+' : ''}${dv.toFixed(1)}`).join(' → ');
          return `<div class="ri-flag-card ri-flag-amber">
            <div class="ri-flag-card-title">⚠ Trait Signal Flag: <b>${label}</b> &middot; Model Weight: <b>${Math.round(w*100)}%</b></div>
            <div class="ri-flag-card-body">
              <span>3-Round Consensus: <b>${cs.consensus.toUpperCase()}</b></span>
              <span style="margin-left:.75rem">Signal trend: ${dHist}</span>
            </div>
            <div class="ri-flag-card-rec">Recommendation: Weight may be ${Math.round(w*100)-3}–${Math.round(w*100)-4}pp high; consider reallocation to APP families post-event.</div>
            <div class="ri-flag-card-status" style="color:#fcd34d;font-size:.65rem;margin-top:.2rem">STATUS: POST-EVENT REVIEW REQUIRED — do not change weights mid-tournament</div>
          </div>`;
        }).join('');
      if (flagCards) ottFlagCardHTML = flagCards;
    }

    r2DetailedHTML = `
      ${ottFlagCardHTML ? `<div class="ri-card ri-card-wide" style="padding:.75rem 1rem">${ottFlagCardHTML}</div>` : ''}
      <div class="ri-card ri-card-wide r2-assess-wrapper">
        <button class="r2-assess-toggle" onclick="this.nextElementSibling.classList.toggle('r2-open');this.classList.toggle('r2-open')">
          R${roundNum} Detailed Assessment <span class="r2-toggle-chev">&#x25B8;</span>
        </button>
        <div class="r2-assess-body">
          ${sub1HTML}
          ${sub2HTML}
          ${sub3HTML}
          ${sub4HTML}
          ${sub5HTML}
        </div>
      </div>`;
  }

  /* ── 9. Data diagnostics note ── */
  const ms = d.match_summary;
  const enrDiagNote = ciLoaded && enrSummary
    ? `<div><b>Course Insights (DataGolf proxy):</b> ${enrSummary.player_match_n}/${enrSummary.player_total} players matched &middot; data embedded in analysis JSON (no separate CSV fetch by the app)</div>
       <div>Traits upgraded: <b>${enrSummary.traits_upgraded.map(k=>traitLabel(k)).join(', ') || 'none'}</b> &middot; confirmed: ${enrSummary.traits_confirmed.map(k=>traitLabel(k)).join(', ') || 'none'}</div>
       ${(enrSummary.key_findings || []).map(f => `<div style="font-size:.68rem;color:var(--muted)">&bull; ${f}</div>`).join('')}
       <div>DataGolf SG correlated (~0.05–0.30 diff) but distinct from PGAT SG &mdash; supplemental proxy layer only.</div>`
    : '<div>Course Insights: not loaded for this round.</div>';
  const diagHTML = `
    <div class="ri-card ri-card-wide ri-diag-note">
      <h4>Round ${roundNum} Diagnostics</h4>
      <div class="ri-diag-grid">
        <div><b>${ms.matched}/${ms.total_r1}</b> players matched to pre-tournament model (${ms.match_rate_pct}%)</div>
        <div>Unmatched: ${ms.unmatched.join(', ') || 'none'}</div>
        <div>Sources: ${(d.round_sources || ['round_leaderboard.csv', 'round_player_strokes_gained.csv', 'trait_form_matrix.csv', 'event_payload.json']).join(' &middot; ')}</div>
        <div>Trait deltas: pre-tournament percentile avg (top-10 leaders vs field) from trait_form_matrix.csv. Zero-sentinels imputed from tier avg per QA policy.</div>
        <div>SG proxies: SG:APP &rarr; APP Wedge / APP 100-150 / APP 150-200 / Par-5 &middot; SG:PUTT &rarr; Putt Short Conv / Putt Lag &middot; SG:ARG &rarr; ARG Rough / ARG Bunker &middot; SG:OTT &rarr; OTT Accuracy / OTT Distance. Correlational proxies only.</div>
        <div>Spearman &rho;=${rho.toFixed(3)} between pre-tournament rank and R${roundNum} position (n=${ms.matched}). Low correlation expected early; sharpens through R3&ndash;Final.</div>
        ${enrDiagNote}
      </div>
    </div>`;

  /* ── Leaderboard snapshot strip (top 15) ── */
  const lbTop15 = d.leaderboard_snapshot.slice(0, 15);
  const lbHTML = `
    <div class="ri-card ri-card-wide">
      <h4>R${roundNum} Leaderboard Snapshot <span style="font-size:.7rem;color:var(--muted);font-weight:400">(top 15)</span></h4>
      <div class="ri-lb-scroll">
        <table class="ri-lb-table">
          <thead><tr><th>Pos</th><th>Player</th><th>R${roundNum}</th><th>PT Rank</th><th>Tier</th><th>VTS</th><th>SG:APP</th><th>SG:PUTT</th><th>SG:ARG</th><th>SG:OTT</th></tr></thead>
          <tbody>${lbTop15.map(r => {
            const isRiser  = (d.weekend_risers || []).some(x => x.r1_name === r.r1_name && (x.sg_app ?? 0) > 0.5 && !slipNames.has(x.r1_name));
            const isSlip   = (d.slippage_risk || []).some(x => x.r1_name === r.r1_name);
            const rowClass = isSlip ? 'ri-lb-slip' : isRiser ? 'ri-lb-riser' : '';
            const appClr   = r.sg_app > 1.0 ? '#4ade80' : r.sg_app < -0.5 ? '#f87171' : 'var(--muted)';
            const puttClr  = r.sg_putt > 2.0 ? '#fcd34d' : 'var(--muted)';
            return `<tr class="${rowClass}">
              <td>${r.r1_pos_str}</td>
              <td style="font-weight:600">${r.r1_name}</td>
              <td style="color:#4ade80">${scoreFmt(r.r1_score)}</td>
              <td style="color:var(--muted)">${r.pt_rank || '—'}</td>
              <td>${r.pt_tier ? `T${r.pt_tier}` : '—'}</td>
              <td>${r.pt_vts ? r.pt_vts.toFixed(1) : '—'}</td>
              <td style="color:${appClr}">${sgFmt(r.sg_app)}</td>
              <td style="color:${puttClr}">${sgFmt(r.sg_putt)}</td>
              <td>${sgFmt(r.sg_arg)}</td>
              <td>${sgFmt(r.sg_ott)}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
      <div class="ri-lb-legend">
        <span class="ri-lb-riser-dot"></span> Weekend riser (course-fit validated)
        <span class="ri-lb-slip-dot" style="margin-left:.75rem"></span> Slippage risk (putting-driven round)
      </div>
    </div>`;

  /* ── R2/R3 multi-round leaderboard (shows per-round scores alongside cumulative) ── */
  let lbMultiRoundHTML = '';
  if (roundNum >= 2) {
    const r1SnapMap = {};
    if (r1Data?.leaderboard_snapshot) {
      r1Data.leaderboard_snapshot.forEach(r => { r1SnapMap[r.r1_name] = r; });
    }
    const r2SnapMap = {};
    if (roundNum >= 3 && r2Data?.leaderboard_snapshot) {
      r2Data.leaderboard_snapshot.forEach(r => { r2SnapMap[r.r1_name] = r; });
    }
    const holeCount = roundNum >= 3 ? '54' : '36';
    const lbTop15M = [...d.leaderboard_snapshot].sort((a, b) => a.r1_pos - b.r1_pos).slice(0, 15);
    const multiRows = lbTop15M.map(r => {
      const isRiser = (d.weekend_risers || []).some(x => x.r1_name === r.r1_name && (x.sg_app ?? 0) > 0.5 && !slipNames.has(x.r1_name));
      const isSlip  = (d.slippage_risk || []).some(x => x.r1_name === r.r1_name);
      const rowClass = isSlip ? 'ri-lb-slip' : isRiser ? 'ri-lb-riser' : '';
      const r1Match  = r1SnapMap[r.r1_name];
      const r1Score  = r1Match?.r1_score ?? null;
      const total    = r.r1_score;
      const appClr   = r.sg_app != null ? (r.sg_app > 1.0 ? '#4ade80' : r.sg_app < -0.5 ? '#f87171' : 'var(--muted)') : 'var(--muted)';
      const puttClr  = r.sg_putt != null && r.sg_putt > 2.0 ? '#fcd34d' : 'var(--muted)';
      if (roundNum >= 3) {
        const r2Cum   = r2SnapMap[r.r1_name]?.r1_score ?? null;
        const r2Score = (r2Cum != null && r1Score != null) ? r2Cum - r1Score : null;
        const r3Score = (r2Cum != null && total != null) ? total - r2Cum : null;
        return `<tr class="${rowClass}">
          <td>${r.r1_pos_str}</td>
          <td style="font-weight:600">${r.r1_name}</td>
          <td style="color:var(--muted)">${scoreFmt(r1Score)}</td>
          <td style="color:var(--muted)">${scoreFmt(r2Score)}</td>
          <td style="color:#4ade80">${scoreFmt(r3Score)}</td>
          <td style="color:#4ade80;font-weight:600">${scoreFmt(total)}</td>
          <td>${r.pt_vts != null ? r.pt_vts.toFixed(1) : '—'}</td>
          <td style="color:${appClr}">${sgFmt(r.sg_app)}</td>
          <td style="color:${puttClr}">${sgFmt(r.sg_putt)}</td>
          <td>${sgFmt(r.sg_arg)}</td>
          <td>${sgFmt(r.sg_ott)}</td>
        </tr>`;
      }
      const r2Score = (r1Score != null && total != null) ? total - r1Score : null;
      return `<tr class="${rowClass}">
        <td>${r.r1_pos_str}</td>
        <td style="font-weight:600">${r.r1_name}</td>
        <td style="color:var(--muted)">${scoreFmt(r1Score)}</td>
        <td style="color:#4ade80">${scoreFmt(r2Score)}</td>
        <td style="color:#4ade80;font-weight:600">${scoreFmt(total)}</td>
        <td>${r.pt_vts != null ? r.pt_vts.toFixed(1) : '—'}</td>
        <td style="color:${appClr}">${sgFmt(r.sg_app)}</td>
        <td style="color:${puttClr}">${sgFmt(r.sg_putt)}</td>
        <td>${sgFmt(r.sg_arg)}</td>
        <td>${sgFmt(r.sg_ott)}</td>
      </tr>`;
    }).join('');
    const multiThead = roundNum >= 3
      ? `<thead><tr><th>Pos</th><th>Player</th><th>R1</th><th>R2</th><th>R3</th><th>54-Hole</th><th>VTS</th><th>SG:APP</th><th>SG:PUTT</th><th>SG:ARG</th><th>SG:OTT</th></tr></thead>`
      : `<thead><tr><th>Pos</th><th>Player</th><th>R1</th><th>R2</th><th>36-Hole</th><th>VTS</th><th>SG:APP</th><th>SG:PUTT</th><th>SG:ARG</th><th>SG:OTT</th></tr></thead>`;
    const multiLegendNote = roundNum >= 3
      ? 'SG values cumulative through R3 &middot; R3 = 54-Hole total minus R2 cum &middot; R2 = R2 cum minus R1'
      : 'R1 score from round 1 analysis &middot; R2 = cumulative minus R1 &middot; 36-Hole = total';
    lbMultiRoundHTML = `
      <div class="ri-card ri-card-wide">
        <h4>${holeCount}-Hole Leaderboard <span style="font-size:.7rem;color:var(--muted);font-weight:400">(top 15 &middot; individual round scores)</span></h4>
        <div class="ri-lb-scroll">
          <table class="ri-lb-table">
            ${multiThead}
            <tbody>${multiRows}</tbody>
          </table>
        </div>
        <div class="ri-lb-legend">
          <span class="ri-lb-riser-dot"></span> ${roundNum >= 3 ? 'Final round riser' : 'Weekend riser'}
          <span class="ri-lb-slip-dot" style="margin-left:.75rem"></span> Slippage risk
          <span style="margin-left:.75rem;font-size:.65rem;color:var(--muted)">${multiLegendNote}</span>
        </div>
      </div>`;
  }

  /* ── Model Accountability (R2+) ── */
  let modelAccountabilityHTML = '';
  if (roundNum >= 2) {
    const tier1InLb = d.leaderboard_snapshot.filter(r => r.pt_tier === 1)
      .sort((a, b) => (a.pt_rank || 99) - (b.pt_rank || 99));
    const tier1Rows = tier1InLb.length === 0
      ? '<tr><td colspan="6" style="color:var(--muted);text-align:center">No Tier 1 players matched in leaderboard data.</td></tr>'
      : tier1InLb.map(r => {
          const pos = r.r1_pos;
          const {cls, lbl} = roundNum >= 3
            ? (pos <= 5  ? {cls:'r2-stat-val',   lbl:'ON TARGET'}
             : pos <= 15 ? {cls:'r2-stat-track', lbl:'WATCH'}
             :             {cls:'r2-stat-under', lbl:'MISS'})
            : (pos <= 5  ? {cls:'r2-stat-val',   lbl:'On target'}
             : pos <= 15 ? {cls:'r2-stat-track', lbl:'In range'}
             : pos <= 30 ? {cls:'',              lbl:'Mixed'}
             :             {cls:'r2-stat-under', lbl:'Lagging'});
          return `<tr>
            <td style="font-weight:600">${r.r1_name}</td>
            <td style="color:var(--muted)">PT #${r.pt_rank}</td>
            <td>${r.pt_vts != null ? r.pt_vts.toFixed(1) : '—'}</td>
            <td>${r.r1_pos_str || r.r1_pos}</td>
            <td style="color:#4ade80">${scoreFmt(r.r1_score)}</td>
            <td><span class="r2-status-badge ${cls}">${lbl}</span></td>
          </tr>`;
        }).join('');

    const apList = eventMeta?.model_summary?.anti_patterns || [];
    const apSection = apList.length === 0 ? '' : (() => {
      // Build flag lookup from allPlayers (event_payload, Last,First keyed)
      const apFlagMap = {};
      for (const p of allPlayers) {
        apFlagMap[(p.player_name || '').toLowerCase()] = p.anti_pattern_flags || '';
      }
      // Convert "Patrick Cantlay" → "cantlay, patrick" for allPlayers lookup
      function toLastFirstLower(name) {
        const words = (name || '').trim().split(/\s+/);
        if (words.length < 2) return name.toLowerCase();
        return (words.slice(1).join(' ') + ', ' + words[0]).toLowerCase();
      }
      const top20snap = d.leaderboard_snapshot.filter(r => (r.r1_pos || 999) <= 20);
      const apRows = apList.map(ap => {
        const meta = AP_META[ap];
        const triggering = top20snap
          .filter(r => {
            const key = toLastFirstLower(r.r1_name);
            const flags = apFlagMap[key] || r.pt_flags || '';
            return flags.split(';').some(f => f.trim() === ap);
          })
          .sort((a, b) => (a.r1_pos - b.r1_pos) || ((a.pt_rank ?? 999) - (b.pt_rank ?? 999)))
          .map(r => r.r1_name.split(' ').slice(-1)[0]);
        return `<tr>
          <td><span class="ap-tag ${meta?.cls||''}">${meta?.label || ap}</span></td>
          <td style="font-size:.7rem;color:var(--muted)">${meta?.tip || ''}</td>
          <td style="color:${triggering.length ? '#fcd34d' : 'var(--muted)'}">${triggering.length ? triggering.join(', ') : 'none in current top 20'}</td>
        </tr>`;
      }).join('');
      return `<div style="margin-top:.7rem">
        <div class="r2-proj-lbl">Anti-Pattern Flags Active</div>
        <div class="r2-scroll">
          <table class="r2-vts-table">
            <thead><tr><th>Flag</th><th>Description</th><th>CURRENT TOP-20 AFFECTED</th></tr></thead>
            <tbody>${apRows}</tbody>
          </table>
        </div>
      </div>`;
    })();

    const misses = d.leaderboard_snapshot
      .filter(r => r.pt_tier != null && r.pt_tier <= 2 && r.r1_pos > 20)
      .sort((a, b) => (a.pt_rank || 99) - (b.pt_rank || 99))
      .slice(0, 5);
    const missHTML = misses.length === 0
      ? '<p class="ri-placeholder">No Tier 1/2 players significantly off expectations.</p>'
      : misses.map(r => {
          const tierLabel = r.pt_tier != null ? `T${r.pt_tier}` : 'Unmatched';
          const rankLabel = r.pt_rank != null ? `PT #${r.pt_rank}` : 'no PT rank';
          const vtsLabel  = r.pt_vts  != null ? `VTS ${r.pt_vts.toFixed(1)}` : 'VTS —';
          const posDelta  = r.pt_rank != null ? r.r1_pos - r.pt_rank : null;
          const verdict   = posDelta != null
            ? `Tier ${r.pt_tier} — underperforming by ${posDelta > 0 ? '+' : ''}${posDelta} positions vs model expectation`
            : `Tier ${r.pt_tier} — underperforming model expectation`;
          return `<div class="ri-player-row">
            <div class="ri-player-name">${r.r1_name}</div>
            <div class="ri-player-meta">
              <span class="ri-pos-chip">${r.r1_pos_str ?? r.r1_pos}</span>
              <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
              <span class="ri-tier-chip">${tierLabel}</span>
              <span style="font-size:.68rem;color:var(--muted)">${rankLabel} &middot; ${vtsLabel}</span>
            </div>
            <div class="ri-player-sg">
              APP: <b style="color:${(r.sg_app ?? 0) < 0 ? '#f87171' : 'var(--muted)'}">${sgFmt(r.sg_app)}</b>
              PUTT: <b>${sgFmt(r.sg_putt)}</b>
              ARG: <b>${sgFmt(r.sg_arg)}</b>
            </div>
            <div class="ri-player-note" style="font-size:.68rem;color:#fcd34d;margin-top:.2rem">${verdict}</div>
          </div>`;
        }).join('');

    modelAccountabilityHTML = `
      <div class="ri-card ri-card-wide">
        <h4>Model Accountability &mdash; R${roundNum}</h4>
        <div class="r2-proj-lbl">Tier 1 Check</div>
        <div class="r2-scroll">
          <table class="r2-vts-table">
            <thead><tr><th>Player</th><th>Pre-Tournament</th><th>VTS</th><th>Pos</th><th>Score</th><th>Status</th></tr></thead>
            <tbody>${tier1Rows}</tbody>
          </table>
        </div>
        ${apSection}
        <div style="margin-top:.7rem">
          <div class="r2-proj-lbl">Notable Misses (T1+2 outside top 30)</div>
          ${missHTML}
        </div>
      </div>`;
  }

  /* ── Weekend Projection (R2+) ── */
  let weekendProjectionHTML = '';
  if (roundNum >= 2) {
    const projRisers    = [...(d.weekend_risers || [])].filter(r => (r.sg_app ?? 0) > 0.5 && !slipNames.has(r.r1_name)).sort((a, b) => (b.thesis_score||0) - (a.thesis_score||0)).slice(0, 5);
    const watchAll      = lln.watch_next_round || [];
    const modelLeaders  = watchAll.filter(w => w.flag_type === 'sustainable');
    const slippageFlags = watchAll.filter(w => w.flag_type !== 'sustainable');

    const modelLeaderRows = modelLeaders.map(w => {
      const sc = w.score != null ? (w.score === 0 ? 'E' : (w.score > 0 ? '+' : '') + w.score.toFixed(0)) : '';
      const appStr  = w.sg_app  != null ? ` APP <b style="color:#4ade80">${w.sg_app  > 0 ? '+' : ''}${w.sg_app.toFixed(2)}</b>`  : '';
      const puttStr = w.sg_putt != null ? ` PUTT <b>${w.sg_putt > 0 ? '+' : ''}${w.sg_putt.toFixed(2)}</b>` : '';
      return `<div class="r2-proj-row">
          <div class="r2-proj-player">
            <span class="r2-proj-name">${w.player}</span>
            <span class="ri-pos-chip">${w.pos_str}</span>
            <span class="ri-score-chip">${sc}</span>
            <span class="r2-proj-dots" style="color:#4ade80" title="Approach-backed sustainable position">&#10003; MODEL</span>
          </div>
          <div class="r2-proj-sg">${appStr}${puttStr}</div>
          <div class="r2-proj-note" style="color:#86efac">${w.note}</div>
        </div>`;
    }).join('');

    const projRows = projRisers.length === 0
      ? '<p class="ri-placeholder">No course-fit validated risers this round.</p>'
      : projRisers.map(r => {
          const sgApp = r.sg_app ?? 0;
          const structuralScore = sgApp >= 2.0 ? 3 : sgApp >= 0.5 ? 2 : 1;
          const dots = '●'.repeat(structuralScore) + '○'.repeat(3 - structuralScore);
          const leader1Score = -20;
          const shotsBack = r.r1_score != null ? Math.abs(r.r1_score - leader1Score) : null;
          const shotsBackLabel = shotsBack != null && shotsBack > 0 ? `<span style="font-size:.62rem;color:var(--muted)" title="Shots behind leader">-${shotsBack}</span>` : '';
          return `<div class="r2-proj-row">
            <div class="r2-proj-player">
              <span class="r2-proj-name">${r.r1_name}</span>
              <span class="ri-pos-chip">${r.r1_pos_str || r.r1_pos}</span>
              <span class="ri-score-chip">${scoreFmt(r.r1_score)}</span>
              ${shotsBackLabel}
              <span class="r2-proj-dots" title="Structural SG fit: APP ≥2.0=●●● | APP ≥0.5=●●○ | marginal=●○○">${dots}</span>
            </div>
            <div class="r2-proj-sg">
              APP <b style="color:${sgApp > 0.5 ? '#4ade80' : 'var(--muted)'}">${sgFmt(r.sg_app)}</b>
              ARG <b style="color:${(r.sg_arg||0)>0.3?'#4ade80':'var(--muted)'}">${sgFmt(r.sg_arg)}</b>
              PUTT <b>${sgFmt(r.sg_putt)}</b>
            </div>
            <div class="r2-proj-note">${r.thesis_note || ''}</div>
          </div>`;
        }).join('');
    const slippageItems = slippageFlags.map(w => {
      const sc = w.score != null ? (w.score === 0 ? 'E' : (w.score > 0 ? '+' : '') + w.score.toFixed(0)) : '';
      const appStr  = w.sg_app  != null ? ` APP ${w.sg_app  > 0 ? '+' : ''}${w.sg_app.toFixed(2)}`  : '';
      const puttStr = w.sg_putt != null ? ` PUTT ${w.sg_putt > 0 ? '+' : ''}${w.sg_putt.toFixed(2)}` : '';
      return `<li><span style="color:#fcd34d">${w.player}</span> (${w.pos_str}, ${sc}${appStr}${puttStr}) &mdash; <span style="color:var(--muted)">${w.note}</span></li>`;
    }).join('') || `<li style="color:var(--muted)">No slippage risk identified.</li>`;
    weekendProjectionHTML = `
      <div class="ri-card ri-card-wide">
        <h4>${roundNum >= 3 ? 'Final Round Projection' : 'Weekend Projection'}</h4>
        ${modelLeaders.length ? `
        <div class="r2-proj-lbl" style="margin-bottom:.3rem;color:#4ade80">MODEL LEADERS &mdash; ${lln.next_round === 4 || !lln.next_round ? 'R4 (Final)' : `R${lln.next_round}`}</div>
        <div class="ri-note" style="margin-bottom:.4rem">Approach-backed, model-confirmed sustainable positions through 54 holes. Not putting-driven.</div>
        ${modelLeaderRows}
        <div style="border-top:1px solid var(--border);margin:.65rem 0"></div>` : ''}
        <div class="r2-proj-lbl" style="margin-bottom:.3rem">${roundNum >= 3 ? 'Final Round Risers' : 'Weekend Risers'} <span class="r2-proj-lbl-sub">(&bull;&bull;&bull; = strongest thesis)</span></div>
        <div class="ri-note" style="margin-bottom:.4rem">Players outperforming their pre-tournament rank with approach-backed SG${roundNum >= 3 ? ' through 54 holes' : ''}. Ranked by thesis strength.</div>
        ${projRows}
        ${slippageFlags.length ? `<div style="margin-top:.65rem">
          <div class="r2-proj-lbl" style="margin-bottom:.3rem">Slippage Risk &mdash; ${lln.next_round === 4 || !lln.next_round ? 'Final Round' : `R${lln.next_round}`}</div>
          <ul class="ri-lean-list">${slippageItems}</ul>
        </div>` : ''}
      </div>`;
  }

  /* ── Assemble all sections ── */
  body.innerHTML = `
    <div class="ri-r1-layout">
      <div class="ri-r1-header">
        <span class="ri-r1-label">${d.metadata?.round_label || `Round ${roundNum}`}${d.metadata?.is_final ? ' — Final' : ' Complete'}</span>
        <span class="ri-r1-sub">${d.metadata?.course_name || 'TPC River Highlands'} · Field avg ${scoreFmt(mp.groups.all_field.avg_r1_score)} · Par ${d.metadata?.par || 70}</span>
        <span class="ri-r1-meta">Built ${(d.build_timestamp || d.generated_at || '—').replace('T',' ')} &middot; ${d.match_summary?.matched ?? '?'}/${d.match_summary?.total_r1 ?? '?'} matched &middot; enrichment ${d.enrichment_used ? 'on' : 'off'}</span>
      </div>
      ${legendHTML}
      ${modelStripHTML}
      ${lbHTML}
      ${lbMultiRoundHTML}
      <div class="ri-r1-grid">
        ${traitWinnersHTML}
        ${modelVsRealHTML}
        ${weekendRisersHTML}
        ${slippageHTML}
        ${weekendProjectionHTML}
        ${modelAccountabilityHTML}
        ${favTrackerHTML}
        ${realityHTML}
        ${liveLeanHTML}
        ${r2DetailedHTML}
        ${diagHTML}
      </div>
    </div>`;
}

/* ══════════════════════════════════════════════════════
   ROUND INSIGHTS PANEL
══════════════════════════════════════════════════════ */
function renderRoundInsights(payload) {
  const ms = payload.model_summary;
  const body = document.getElementById('ri-body');
  showRoundPanel('pre', ms, body);

  /* Mark round tabs with LIVE (data present) or NO DATA (pending) status */
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
      showRoundPanel(tab.dataset.round, ms, body);
    });
  });
}

function showRoundPanel(round, ms, body) {
  /* Route to renderRoundPanel when round data is available */
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
          <span style="font-size:.75rem;color:var(--muted)">Data may be malformed or incomplete. See browser console for details.<br><code>${err.message}</code></span>
        </div>`;
      }
      return;
    }
  }
  if (round === 'pre') {
    const weights = ms.trait_weight_matrix;
    const bars = Object.entries(weights).map(([k,w]) => {
      const pct = Math.round(w * 100);
      const def = TRAIT_KEY_MAP[k];
      const label = def ? def.label : k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
      return `<div class="ri-weight-bar">
        <span class="ri-weight-label">${label}</span>
        <div class="ri-weight-bar-bg"><div class="ri-weight-bar-fill" style="width:${pct*4}%"></div></div>
        <span class="ri-weight-pct">${pct}%</span>
      </div>`;
    }).join('');

    const topFits = allPlayers.filter(p => p.tier <= 2).slice(0,5);
    const topHTML = topFits.map(p =>
      `<div style="display:flex;justify-content:space-between;font-size:.75rem;padding:.2rem 0;border-bottom:1px solid var(--border)">
        <span>${p.player_name.split(',').reverse().join(' ').trim()} ${tierBadgeHTML(p.tier)}</span>
        <span style="color:var(--accent)">${fmtPct(p.win_pct)} win</span>
      </div>`
    ).join('');

    body.innerHTML = `
      <div class="ri-pre-grid">
        <div class="ri-card">
          <h4>Course Trait Weights</h4>
          ${bars}
        </div>
        <div class="ri-card">
          <h4>Model Leaders</h4>
          ${topHTML}
        </div>
        <div class="ri-card">
          <h4>Anti-Patterns Active</h4>
          ${ms.anti_patterns.map(ap => {
            const meta = AP_META[ap];
            return `<div style="margin-bottom:.5rem">
              <div class="ap-tag ${meta?.cls||''}" style="display:inline-block;margin-bottom:.15rem">${meta?.label||ap.toUpperCase()}</div>
              <div style="font-size:.7rem;color:var(--muted);line-height:1.4">${meta?.tip||''}</div>
            </div>`;
          }).join('')}
        </div>
        <div class="ri-card">
          <h4>Venue Context</h4>
          <div style="font-size:.75rem;color:var(--muted);line-height:1.65">
            <p>TPC River Highlands is a short par-70 birdie-fest. The primary lever is wedge/short-iron proximity — a skill the model weights at 22%. Positional driving (14%) and birdie conversion (16%) are the two other high-weight factors. Distance is de-emphasized at 5%.</p>
            <p style="margin-top:.5rem">Track record (Jim Furyk 58 in 2016) illustrates scoring potential. Moderate rough limits raw distance advantage. Hole 15–17 lake stretch adds variance in weekend rounds.</p>
          </div>
        </div>
      </div>`;
  } else if (round === 'final') {
    const curLeader = r3Data?.leaderboard_snapshot?.[0];
    const leaderName = curLeader ? curLeader.r1_name : 'Viktor Hovland';
    const leaderScore = curLeader ? (curLeader.r1_score === 0 ? 'E' : (curLeader.r1_score > 0 ? '+' : '') + curLeader.r1_score.toFixed(0)) : '-20';
    const modelNo1 = eventMeta?.model_summary?.model_winner || 'Scottie Scheffler';
    const modelNo1Row = r3Data?.leaderboard_snapshot?.find(r => r.r1_name.includes(modelNo1.split(',')[0]));
    const modelScoreStr = modelNo1Row ? (modelNo1Row.r1_score === 0 ? 'E' : (modelNo1Row.r1_score > 0 ? '+' : '') + modelNo1Row.r1_score.toFixed(0)) : '-19';
    body.innerHTML = `
      <div class="ri-cards">
        <div class="ri-card" style="grid-column:1/-1">
          <div style="text-align:center;padding:2rem 1rem">
            <div style="font-size:2rem;margin-bottom:.75rem">🏁</div>
            <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:.5rem">Final Round in Progress</h3>
            <p style="color:var(--muted);font-size:.82rem;margin-bottom:.35rem">Round 4 data will populate here upon R4 build completion.</p>
            <p style="font-size:.75rem;color:#94a3b8">Current leader: <b style="color:#4ade80">${leaderName} (${leaderScore})</b> &middot; Model #1: <b style="color:var(--accent)">${modelNo1} (${modelScoreStr})</b></p>
          </div>
        </div>
      </div>`;
  } else {
    const roundLabels = { r1: 'Round 1', r2: 'Round 2', r3: 'Round 3' };
    const label = roundLabels[round] || round;
    body.innerHTML = `
      <div class="ri-cards">
        <div class="ri-card">
          <h4>Trait Winners Today <span class="ri-stub-badge">stub</span></h4>
          <p class="ri-placeholder">Which traits correlated with low scores in ${label}? Wire in round scoring data to populate.</p>
        </div>
        <div class="ri-card">
          <h4>Model vs Realized <span class="ri-stub-badge">stub</span></h4>
          <p class="ri-placeholder">Compare predicted trait importance vs actual scoring contribution after ${label}.</p>
        </div>
        <div class="ri-card">
          <h4>Weekend Risers <span class="ri-stub-badge">stub</span></h4>
          <p class="ri-placeholder">Players outperforming VTS projection through ${label}. Requires live leaderboard feed.</p>
        </div>
        <div class="ri-card">
          <h4>Slippage Risk <span class="ri-stub-badge">stub</span></h4>
          <p class="ri-placeholder">Players currently ahead of model floor with elevated weekend fade risk.</p>
        </div>
        <div class="ri-card">
          <h4>Favorites Tracker <span class="ri-stub-badge">stub</span></h4>
          ${favorites.size > 0
            ? [...favorites].map(n => `<div style="font-size:.75rem;padding:.2rem 0;border-bottom:1px solid var(--border)">${n.split(',').reverse().join(' ').trim()} — <span style="color:var(--muted)">position TBD</span></div>`).join('')
            : '<p class="ri-placeholder">Star players in the field table to track them here.</p>'}
        </div>
        <div class="ri-card">
          <h4>Trait Reality Check <span class="ri-stub-badge">stub</span></h4>
          <p class="ri-placeholder">Post-${label} audit: did APP Wedge or Putt Short Conv players lead the leaderboard? Update weights based on observed scoring patterns.</p>
        </div>
      </div>`;
  }
}

/* ══════════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════════ */
function renderFooter(payload) {
  const ms = payload.model_summary;
  document.querySelector('footer').innerHTML =
    `PGA VenueDNA · Spec v${ms.scoring_spec_version} · Venue file ${ms.venue_file_version} · ` +
    `Model iteration: ${ms.event_iteration} · Built ${new Date().toISOString().slice(0,10)}`;
}

/* ══════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════ */
function fmtPct(v) {
  if (v == null || v === 'N/A' || v === 'not_applicable') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return (n < 2 ? n.toFixed(1) : Math.round(n)) + '%';
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
function toNameKey(name) {
  const parts = (name || '').split(', ');
  return parts.length === 2
    ? `${parts[0].trim().toUpperCase()}_${parts[1].trim().toUpperCase()}`
    : (name || '').trim().toUpperCase().replace(/\s+/g,'_');
}

/* ── Run ── */
init().catch(err => {
  document.body.innerHTML = `<pre style="color:#f87171;padding:2rem">
Board data failed to load. Serve this folder over HTTP, not file://.

Error: ${err.message}

Quick start:  npx serve .   or   python -m http.server 8080</pre>`;
});
