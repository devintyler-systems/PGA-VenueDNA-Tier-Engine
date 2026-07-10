/**
 * VenueDNA — The Open Championship 2026 (Royal Troon)
 * app.js  —  Pre-tournament dashboard
 *
 * Data-depth classification (data_depth_class field from payload):
 *   FULL        — player has Royal Troon course history; Bayesian prior active.
 *   DEBUT       — no Royal Troon history; regressed to field-mean Tier 3 / Rank 38.
 *   ELITE_DEBUT — no history but VTS >= 90 or 6-month form rank <= 5;
 *                 imputed at Tier 1 / Rank 3. Elite performance profile maintained.
 *
 * Badge rendering: _depthBadge(r.data_depth_class) — never normalised, stripped,
 * or coerced elsewhere in the codebase. Filter and sort logic reads the raw field;
 * the DOM class name is derived from .toLowerCase() of the exact API string.
 */

'use strict';

// ── Data depth constants (mirror engine values exactly) ──────────────────────
const DEPTH_FULL        = 'FULL';
const DEPTH_DEBUT       = 'DEBUT';
const DEPTH_ELITE_DEBUT = 'ELITE_DEBUT';

// Synthetic filter token — not a data value, only used in filter state.
// DEPTH_IMPUTED couples DEBUT and ELITE_DEBUT under one "No History" path so
// neither subclass is silently dropped when the user selects the imputed view.
const DEPTH_IMPUTED     = 'IMPUTED';

// ── Module-level state ────────────────────────────────────────────────────────
let _payload     = null;   // pre_tournament_analysis.json
let _snapshot    = [];     // leaderboard_snapshot array
let _sortKey     = 'r1_pos';
let _sortAsc     = true;
let _depthFilter = 'ALL';
let _tierFilter  = 'ALL';
let _searchText  = '';     // free-text search; applied identically to all depth classes

// ── Helpers ───────────────────────────────────────────────────────────────────

function _fmt(v, decimals = 1) {
  const n = parseFloat(v);
  return isNaN(n) ? '—' : n.toFixed(decimals);
}

function _pctFmt(v) {
  const n = parseFloat(v);
  return isNaN(n) ? '—' : `${n.toFixed(2)}%`;
}

/**
 * Render a data-depth badge chip.
 *
 * The CSS class is derived from the raw data_depth_class string via toLowerCase(),
 * producing exactly: "full", "debut", or "elite-debut". The mapping is:
 *   FULL        → .depth-badge.full
 *   DEBUT       → .depth-badge.debut
 *   ELITE_DEBUT → .depth-badge.elite-debut   ← electric-indigo (#c084fc)
 *
 * This function is the SINGLE badge injection point. No other code path in this
 * file appends a depth-badge element — prevents filter/sort side-effects from
 * duplicating or overwriting the class string.
 */
function _depthBadge(depthClass) {
  if (!depthClass) return '';
  // ELITE_DEBUT → "elite-debut"  (hyphen form matches CSS selector exactly)
  const cssClass = depthClass === DEPTH_ELITE_DEBUT
    ? 'elite-debut'
    : depthClass.toLowerCase();
  const label = depthClass === DEPTH_ELITE_DEBUT ? 'ELITE DEBUT' : depthClass;
  return `<span class="depth-badge ${cssClass}">${label}</span>`;
}

function _tierBadge(tier) {
  if (tier == null) return '—';
  return `<span class="tier-badge t${tier}">T${tier}</span>`;
}

// ── Sort ──────────────────────────────────────────────────────────────────────

/**
 * Sort the snapshot array in-place. The data_depth_class field is read-only
 * throughout — sort logic never mutates it.
 */
function _sortSnapshot(key, asc) {
  _snapshot.sort((a, b) => {
    let av = a[key];
    let bv = b[key];
    // Numeric coercion for numeric fields; string fallback for name/class fields.
    const an = parseFloat(av);
    const bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) {
      return asc ? an - bn : bn - an;
    }
    av = String(av ?? '');
    bv = String(bv ?? '');
    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
  });
}

// ── Filter ────────────────────────────────────────────────────────────────────

/**
 * Return a filtered view of _snapshot.
 *
 * Depth filter states:
 *   'ALL'          — every entry regardless of depth class
 *   DEPTH_FULL     — only players with Royal Troon course history
 *   DEPTH_IMPUTED  — DEBUT ∪ ELITE_DEBUT (all no-history players; neither subclass
 *                    is dropped). This is the unified "No History" path that prevents
 *                    ELITE_DEBUT from being hidden when the user selects an imputed view.
 *   DEPTH_DEBUT    — standard mean-imputed only (Tier 3 / Rank 38 baseline)
 *   DEPTH_ELITE_DEBUT — elite talent gate only (Tier 1 / Rank 3 baseline)
 *
 * Text search: evaluated identically against r1_name and norm_name for every
 * depth class — FULL, DEBUT, and ELITE_DEBUT rows all pass through the same
 * lowercased substring match with no per-class branches.
 */
function _filteredSnapshot() {
  const q = _searchText.trim().toLowerCase();

  return _snapshot.filter(r => {
    // ── Depth filter ──────────────────────────────────────────────────────────
    if (_depthFilter === DEPTH_IMPUTED) {
      // IMPUTED couples both no-history subclasses; neither is dropped.
      if (r.data_depth_class !== DEPTH_DEBUT && r.data_depth_class !== DEPTH_ELITE_DEBUT) {
        return false;
      }
    } else if (_depthFilter !== 'ALL') {
      // Exact match for FULL / DEBUT / ELITE_DEBUT individual filters.
      if (r.data_depth_class !== _depthFilter) return false;
    }
    // 'ALL' falls through with no depth check.

    // ── Tier filter ───────────────────────────────────────────────────────────
    if (_tierFilter !== 'ALL' && String(r.pt_tier) !== _tierFilter) return false;

    // ── Text search — identical evaluation for all depth classes ─────────────
    if (q) {
      const name = (r.r1_name   ?? '').toLowerCase();
      const norm = (r.norm_name ?? '').toLowerCase();
      if (!name.includes(q) && !norm.includes(q)) return false;
    }

    return true;
  });
}

// ── Leaderboard render ────────────────────────────────────────────────────────

function renderLeaderboard() {
  const tbody = document.getElementById('lb-body');
  if (!tbody) return;

  const rows = _filteredSnapshot();

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:2rem">No players match the current filter.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(r => {
    const isEliteDebut = r.data_depth_class === DEPTH_ELITE_DEBUT;
    const rowClass     = isEliteDebut ? ' class="elite-debut-row"' : '';

    // _depthBadge is the sole injection point — not duplicated in any sort/filter path.
    const nameCellHtml = `${r.r1_name ?? '—'}${_depthBadge(r.data_depth_class)}`;

    const winPill  = `<span class="prob-pill win">${_pctFmt(r.win_pct)}</span>`;
    const t5Pill   = `<span class="prob-pill top5">${_pctFmt(r.top5_pct)}</span>`;
    const t10Pill  = `<span class="prob-pill top10">${_pctFmt(r.top10_pct)}</span>`;

    const sgOtt = parseFloat(r.sg_ott_positional ?? r.cumulative_sg_ott);
    const sgOttStr = isNaN(sgOtt) ? '—' : (sgOtt >= 0 ? '+' : '') + sgOtt.toFixed(3);
    const sgOttColor = sgOtt >= 0.5 ? 'var(--green)' : sgOtt >= 0 ? 'var(--text)' : 'var(--red)';

    const drvacc = parseFloat(r.driving_accuracy);
    const drvaccStr = isNaN(drvacc) ? '—' : (drvacc * 100).toFixed(1) + '%';

    return `<tr${rowClass}>
      <td class="col-pos">${r.r1_pos ?? '—'}</td>
      <td class="col-name">${nameCellHtml}</td>
      <td>${_tierBadge(r.pt_tier)}</td>
      <td class="col-num">${_fmt(r.pt_vts)}</td>
      <td class="col-num">${winPill}</td>
      <td class="col-num">${t5Pill}</td>
      <td class="col-num">${t10Pill}</td>
      <td class="col-num" style="color:${sgOttColor}">${sgOttStr}</td>
      <td class="col-num">${drvaccStr}</td>
    </tr>`;
  }).join('');
}

// ── Notes panel ───────────────────────────────────────────────────────────────

function renderNotes() {
  const container = document.getElementById('notes-container');
  if (!container || !_payload) return;

  const notes = _payload.live_lean_notes?.notes ?? [];
  if (!notes.length) { container.innerHTML = '<p style="color:var(--muted)">No notes available.</p>'; return; }

  const visibleNames = new Set(_filteredSnapshot().map(r => r.r1_name));

  container.innerHTML = notes
    .filter(n => visibleNames.has(n.player))
    .map(n => {
      const isEliteDebut = n.data_depth_class === DEPTH_ELITE_DEBUT;
      const cardClass    = isEliteDebut ? ' elite-debut-note' : '';
      const depthHtml    = _depthBadge(n.data_depth_class);
      return `<div class="note-card${cardClass}">
        <div class="note-header">
          <span class="note-player">${n.player}</span>${depthHtml}
          <span>PT${n.pt_rank ?? '—'}</span>
          <span>${_tierBadge(n.pre_tier)}</span>
        </div>
        <div class="note-text">${n.note ?? '—'}</div>
      </div>`;
    }).join('');
}

// ── Column sort wiring ────────────────────────────────────────────────────────

function wireSortHeaders() {
  document.querySelectorAll('.lb-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (!key) return;
      if (_sortKey === key) {
        _sortAsc = !_sortAsc;
      } else {
        _sortKey = key;
        _sortAsc = key === 'r1_pos'; // positional sorts ascending by default
      }
      _sortSnapshot(_sortKey, _sortAsc);
      renderLeaderboard();
    });
  });
}

// ── Filter wiring ─────────────────────────────────────────────────────────────

function wireFilters() {
  const depthSel  = document.getElementById('filter-depth');
  const tierSel   = document.getElementById('filter-tier');
  const searchInp = document.getElementById('filter-search');

  if (depthSel) {
    depthSel.addEventListener('change', () => {
      // Valid values: ALL / FULL / IMPUTED / DEBUT / ELITE_DEBUT
      // IMPUTED triggers the DEBUT ∪ ELITE_DEBUT coupled path in _filteredSnapshot.
      _depthFilter = depthSel.value;
      renderLeaderboard();
      renderNotes();
    });
  }
  if (tierSel) {
    tierSel.addEventListener('change', () => {
      _tierFilter = tierSel.value;
      renderLeaderboard();
      renderNotes();
    });
  }
  if (searchInp) {
    // Text search input — fires on every keystroke; applies identically to
    // FULL, DEBUT, and ELITE_DEBUT rows via the shared _filteredSnapshot path.
    searchInp.addEventListener('input', () => {
      _searchText = searchInp.value;
      renderLeaderboard();
      renderNotes();
    });
  }
}

// ── Model performance banner ──────────────────────────────────────────────────

function renderBanner() {
  const el = document.getElementById('model-banner');
  if (!el || !_payload) return;

  const meta = _payload.metadata ?? {};
  const mp   = _payload.model_performance ?? {};
  const snap = _payload.leaderboard_snapshot ?? [];

  const fullN  = snap.filter(s => s.data_depth_class === DEPTH_FULL).length;
  const edN    = snap.filter(s => s.data_depth_class === DEPTH_ELITE_DEBUT).length;
  const debN   = snap.filter(s => s.data_depth_class === DEPTH_DEBUT).length;

  el.innerHTML = `
    <span><b>Course:</b> ${meta.course_name ?? 'Royal Troon'}</span>
    <span><b>Par:</b> ${meta.par ?? 71}</span>
    <span><b>Yardage:</b> ${meta.yardage ?? '—'}</span>
    <span><b>Field:</b> ${_payload.field_size ?? '—'} players</span>
    <span><b>FULL:</b> ${fullN}</span>
    <span title="Tier 1 / Rank 3 imputation — elite talent gate triggered">${_depthBadge(DEPTH_ELITE_DEBUT)} ${edN}</span>
    <span>${_depthBadge(DEPTH_DEBUT)} ${debN}</span>
    <span><b>Effective scalar:</b> ${mp.effective_scalar ?? '—'} (prior coeff ${mp.prior_coefficient ?? '—'})</span>
  `;
}

// ── Round panel: live round analysis ─────────────────────────────────────────

/**
 * renderRoundPanel — renders a round-N analysis block into `body`.
 *
 * The depth-badge injection is the same _depthBadge() call used in renderLeaderboard().
 * No alternative code path exists that could overwrite or strip ELITE_DEBUT class names
 * during filter updates or column sorting, because:
 *   1. _depthBadge() always derives the CSS class from the raw data_depth_class string.
 *   2. Sort and filter only operate on _snapshot data; DOM is fully rebuilt on each render.
 *   3. ELITE_DEBUT is mapped to 'elite-debut' CSS class and 'ELITE DEBUT' label string
 *      exclusively inside _depthBadge() — never in sort/filter branches.
 */
function renderRoundPanel(body, rData, roundNum) {
  if (!rData || !rData.leaderboard_snapshot) {
    body.innerHTML = `<div style="color:var(--red);padding:1.5rem"><b>Round ${roundNum} data incomplete.</b></div>`;
    return;
  }

  const sgFmt    = v => v == null ? '—' : (v >= 0 ? '+' : '') + parseFloat(v).toFixed(3);
  const scoreFmt = v => { const n = +v; return isNaN(n) ? '—' : n === 0 ? 'E' : (n > 0 ? '+' : '') + n; };

  const lbTop = [...(rData.leaderboard_snapshot)]
    .sort((a, b) => (+a.r1_pos || 999) - (+b.r1_pos || 999))
    .slice(0, 20);

  const lbRows = lbTop.map(r => `<tr>
    <td class="col-pos">${r.r1_pos_str ?? r.r1_pos ?? '—'}</td>
    <td class="col-name" style="font-weight:600">${r.r1_name ?? '—'}${_depthBadge(r.data_depth_class)}</td>
    <td style="color:var(--green)">${scoreFmt(r.r1_score)}</td>
    <td style="color:var(--muted)">${r.pt_rank ?? '—'}</td>
    <td>${r.pt_tier ? `T${r.pt_tier}` : '—'}</td>
    <td>${_fmt(r.pt_vts)}</td>
    <td style="color:${(r.sg_app||0)>1.0?'var(--green)':'var(--muted)'}">${sgFmt(r.sg_app)}</td>
    <td style="color:${(r.sg_putt||0)>2.0?'var(--gold)':'var(--muted)'}">${sgFmt(r.sg_putt)}</td>
    <td>${sgFmt(r.sg_ott)}</td>
  </tr>`).join('');

  body.innerHTML = `
    <table class="lb-table" style="width:100%">
      <thead><tr>
        <th>Pos</th><th>Player</th><th>Score</th>
        <th>PT Rank</th><th>Tier</th><th>VTS</th>
        <th>SG:APP</th><th>SG:PUTT</th><th>SG:OTT</th>
      </tr></thead>
      <tbody>${lbRows}</tbody>
    </table>`;
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch('data/pre_tournament_analysis.json');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    _payload  = await resp.json();
    _snapshot = [...(_payload.leaderboard_snapshot ?? [])];
  } catch (err) {
    console.error('[VenueDNA] Failed to load pre_tournament_analysis.json:', err);
    const el = document.getElementById('lb-body');
    if (el) el.innerHTML = `<tr><td colspan="9" style="color:var(--red);padding:1.5rem">Failed to load data: ${err.message}</td></tr>`;
    return;
  }

  _sortSnapshot(_sortKey, _sortAsc);
  renderBanner();
  renderLeaderboard();
  renderNotes();
  wireSortHeaders();
  wireFilters();
}

document.addEventListener('DOMContentLoaded', init);
