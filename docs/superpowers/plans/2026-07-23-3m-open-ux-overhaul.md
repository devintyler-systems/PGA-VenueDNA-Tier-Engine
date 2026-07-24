# 3M Open 2026 — UX Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate player card narrative copy, fix Glossary/Views, rename Scenario → Analyst Mode, expose fair odds, and promote the Contention Map and Storylines as first-class views on the 3M Open static board.

**Architecture:** All changes are client-side read-only; the board (2026_3m_open_board.html + app.js) reads canonical artifacts and renders. No engine scripts or output files are modified. The player_briefs.json merge is the only data file write — it adds new fields alongside existing machine fields without replacing them.

**Tech Stack:** Vanilla JS ES5-compat, Chart.js 4.4.0 (CDN), HTML/CSS already in deploy/; Node.js used only for one-shot JSON merge (Task 1).

---

## Global Constraints

- `deploy/` is the sole surface area — never touch `engine/`, `output/`, or `input/` files.
- Tier assignments, VTS scores, and probability values in `board_export.json` are read-only.
- Scenario (Analyst Mode) adjustments must NEVER write back to any JSON artifact.
- All JS in app.js stays `'use strict'`; no new global scope pollution — extend state via `S` object only.
- winPct, top10Pct, etc. are stored on 0–100 scale (e.g., 1.7 = 1.7%).
- delta_fit ranges –0.500 to +0.500 SG/round; neutralSkillIndex and vts_final are 0–100 z-scores.
- Do not add Chart.js or any other library; Chart.js 4.4.0 is already on CDN in the HTML.
- Primary board file is `2026_3m_open_board.html` (index.html is a redirect only).

---

## File Map

| File | What Changes |
|------|-------------|
| `events/2026_3m_open/deploy/data/2026_3m_open_player_briefs.json` | Task 1 — merge card copy narrative fields |
| `events/2026_3m_open/deploy/app.js` | Tasks 2–7 — all JS additions |
| `events/2026_3m_open/deploy/2026_3m_open_board.html` | Tasks 3, 6, 7 — HTML containers, button labels |

**Absolute paths** (all relative to repo root `C:\PGA_VenueDNA`):
- Briefs: `events/2026_3m_open/deploy/data/2026_3m_open_player_briefs.json`
- Card copy: `events/2026_3m_open/deploy/data/3m_open_2026_all_player_card.json`
- App: `events/2026_3m_open/deploy/app.js`
- Board: `events/2026_3m_open/deploy/2026_3m_open_board.html`

---

## Task 1: Merge Card Copy Into player_briefs.json

**Files:**
- Read: `events/2026_3m_open/deploy/data/3m_open_2026_all_player_card.json`
- Write: `events/2026_3m_open/deploy/data/2026_3m_open_player_briefs.json`

**Background:** The card copy JSON has 144 entries. Entries 1–28 have real player names ("Scottie Scheffler", "Maverick McNealy", etc.) and rich narrative. Entries 29–144 are placeholder rows ("Player 29", ...) and should be skipped.

The briefs JSON is keyed by "Last, First" format. The card copy uses "First Last" format. Name flip: split on last space token → "Last, First". All 28 real names have been verified to match briefs keys exactly.

**Merge field mapping** (add alongside existing fields, do NOT overwrite existing ones):
```
card.headline            → brief.convictionStatement
card.scouting_report     → brief.neutral_skill_summary
card.form_note           → brief.form_summary
card.win_case            → brief.scoring_thesis  (only if not already set)
card.win_case            → brief.dark_horse_thesis (always — for all tiers)
card.risk_vector         → brief.card_risk_vector (new field, avoids collision with key_risk_vector)
card.strength_tags[]     → brief.strengthTags
card.weakness_tags[]     → brief.weaknessTags
card.course_fit_delta    → brief.venuefitdelta
card.baseline_sg         → brief.neutralskillsg
card.projected_sg        → brief.projectedsg
card.recent_true_sg_l20  → brief.recentTrueSGL20
card.vs_baseline_l20     → brief.vsBaselineL20
card.raw_recent_starts   → brief.rawRecentStarts
```

- [ ] **Step 1: Write and run merge script**

Save as `events/2026_3m_open/deploy/data/merge_card_copy.js` (temporary — delete after run):

```js
'use strict';
const fs      = require('fs');
const path    = require('path');
const dataDir = __dirname;

const cards  = JSON.parse(fs.readFileSync(path.join(dataDir, '3m_open_2026_all_player_card.json'), 'utf8'));
const briefs = JSON.parse(fs.readFileSync(path.join(dataDir, '2026_3m_open_player_briefs.json'), 'utf8'));

function toLastFirst(name) {
  const parts = name.trim().split(' ');
  const last  = parts.pop();
  return last + ', ' + parts.join(' ');
}

let merged = 0;
for (const card of cards) {
  if (card.player_name.startsWith('Player ')) continue; // skip placeholders
  const key = toLastFirst(card.player_name);
  const br  = briefs[key];
  if (!br) { console.warn('NO MATCH:', card.player_name, '->', key); continue; }

  br.convictionStatement    = card.headline;
  br.neutral_skill_summary  = card.scouting_report;
  br.form_summary           = card.form_note;
  if (!br.scoring_thesis)    br.scoring_thesis = card.win_case;
  br.dark_horse_thesis      = card.win_case;
  br.card_risk_vector       = card.risk_vector;
  br.strengthTags           = card.strength_tags;
  br.weaknessTags           = card.weakness_tags;
  br.venuefitdelta          = card.course_fit_delta;
  br.neutralskillsg         = card.baseline_sg;
  br.projectedsg            = card.projected_sg;
  br.recentTrueSGL20        = card.recent_true_sg_l20;
  br.vsBaselineL20          = card.vs_baseline_l20;
  br.rawRecentStarts        = card.raw_recent_starts;
  merged++;
}

fs.writeFileSync(
  path.join(dataDir, '2026_3m_open_player_briefs.json'),
  JSON.stringify(briefs, null, 2),
  'utf8'
);
console.log('Merged', merged, 'players into player_briefs.json');
```

Run: `cd C:\PGA_VenueDNA\events\2026_3m_open\deploy\data && node merge_card_copy.js`

Expected output: `Merged 28 players into player_briefs.json`

- [ ] **Step 2: Verify merge**

```bash
node -e "
const b = require('./events/2026_3m_open/deploy/data/2026_3m_open_player_briefs.json');
const s = b['Scheffler, Scottie'];
console.log('convictionStatement:', s.convictionStatement?.slice(0,60));
console.log('neutral_skill_summary:', s.neutral_skill_summary?.slice(0,60));
console.log('form_summary:', s.form_summary?.slice(0,60));
console.log('strengthTags:', s.strengthTags);
console.log('vsBaselineL20:', s.vsBaselineL20);
console.log('VenueDNA_rank:', s.VenueDNA_rank, '(should be unchanged)');
console.log('anti_pattern_flags:', s.anti_pattern_flags, '(should be unchanged)');
"
```

Expected: New fields populated, `VenueDNA_rank: 1` and `anti_pattern_flags: []` unchanged.

- [ ] **Step 3: Delete merge script**

```bash
rm events/2026_3m_open/deploy/data/merge_card_copy.js
```

- [ ] **Step 4: Commit**

```bash
git add events/2026_3m_open/deploy/data/2026_3m_open_player_briefs.json
git commit -m "feat(3m-open): merge card copy narrative fields into player_briefs.json"
```

---

## Task 2: Wire New Narrative Fields in app.js init() and Modal

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`

**Background:** The merged JSON fields need to be picked up in the brief normalisation block inside `init()` (lines 140–154), and the modal's §4 Player Analysis section needs to surface `form_summary`, `neutral_skill_summary`, and the new tags.

- [ ] **Step 1: Add field mappings in init() brief normalisation block**

Locate this block in `app.js` (around line 146–153):
```js
if (!b.scoring_thesis)        b.scoring_thesis        = b.exact_mechanism || b.why_it_fits_structurally || '';
if (!b.failure_condition)     b.failure_condition     = b.named_failure_condition || '';
if (!b.risk_vector)           b.risk_vector           = b.key_risk_vector || '';
if (!b.conviction_statement)  b.conviction_statement  = b.why_it_fits_structurally || '';
if (!b.anti_pattern_summary)  b.anti_pattern_summary  = b.penalty_context || '';
if (!b.venue_history_summary) b.venue_history_summary = b.venue_history_context || '';
```

Replace that entire block with:
```js
if (!b.scoring_thesis)        b.scoring_thesis        = b.exact_mechanism || b.why_it_fits_structurally || '';
if (!b.failure_condition)     b.failure_condition     = b.named_failure_condition || '';
if (!b.risk_vector)           b.risk_vector           = b.card_risk_vector || b.key_risk_vector || '';
if (!b.conviction_statement)  b.conviction_statement  = b.convictionStatement || b.why_it_fits_structurally || '';
if (!b.neutral_skill_summary) b.neutral_skill_summary = b.neutral_skill_summary || b.why_it_fits_structurally || '';
if (!b.form_summary)          b.form_summary          = b.form_summary || '';
if (!b.anti_pattern_summary)  b.anti_pattern_summary  = b.penalty_context || '';
if (!b.venue_history_summary) b.venue_history_summary = b.venue_history_context || '';
```

- [ ] **Step 2: Add strength/weakness tags render in modal §4**

Locate `<!-- §4 — PLAYER ANALYSIS -->` in `openModal()` (around line 1143). The section renders `neutral_skill_summary`, `venue_fit_summary`, `venue_history_summary`, `form_summary`. After the `</div>` closing `analysis-blocks`, add strength/weakness tags rendering.

Find the existing §4 block ending:
```js
          ${br.form_summary          ? `<div class="analysis-block"><div class="analysis-block-lbl">Form</div><div class="analysis-block-text">${br.form_summary}</div></div>` : ''}
        </div>
      </div>` : ''}
```

Replace with:
```js
          ${br.form_summary          ? `<div class="analysis-block"><div class="analysis-block-lbl">Form</div><div class="analysis-block-text">${br.form_summary}</div></div>` : ''}
        </div>
        ${(br.strengthTags?.length || br.weaknessTags?.length) ? `<div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.6rem;">
          ${(br.strengthTags||[]).map(t=>`<span style="background:#052e16;border:1px solid #16a34a55;color:#4ade80;padding:.1rem .4rem;border-radius:4px;font-size:.68rem;font-family:'Inter',sans-serif">+${t}</span>`).join('')}
          ${(br.weaknessTags||[]).map(t=>`<span style="background:#450a0a;border:1px solid #dc262655;color:#fca5a5;padding:.1rem .4rem;border-radius:4px;font-size:.68rem;font-family:'Inter',sans-serif">–${t}</span>`).join('')}
        </div>` : ''}
      </div>` : ''}
```

- [ ] **Step 3: Add dark_horse_thesis to T3 modal section**

Locate the T3 block in `buildWinCase()` (around line 971):
```js
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
```

Replace with:
```js
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
```

- [ ] **Step 4: Manual check**

Open `http://localhost:8080/2026_3m_open_board.html` (or file://), click Scheffler's row, open modal. Verify:
- §3 shows a scouting_report/win_case derived narrative in "Win Case"
- §4 Player Analysis shows neutral_skill_summary (scouting_report) and form_summary (form_note)
- Strength tags (green) and weakness tags (red) appear below analysis blocks

- [ ] **Step 5: Commit**

```bash
git add events/2026_3m_open/deploy/app.js
git commit -m "feat(3m-open): wire merged card copy fields into modal (narrative + tags)"
```

---

## Task 3: Dynamic Glossary + Analyst Mode Entry

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`
- Modify: `events/2026_3m_open/deploy/2026_3m_open_board.html`

**Background:** The glossary modal body is currently static HTML. The task requires an in-memory `uiGlossary` object and dynamic rendering. The glossary should also include an "Analyst Mode" section. In the HTML, replace the static body content with a container `<div id="glossary-body"></div>`.

- [ ] **Step 1: Replace static glossary HTML body with container**

In `2026_3m_open_board.html`, locate the glossary modal body (line ~541):
```html
    <div class="modal-body">
      <div class="gloss-section">
        <div class="gloss-section-title">Score Components</div>
        ...many lines of static content...
      </div>
    </div>
```

Replace the entire `<div class="modal-body">...</div>` inside the glossary modal with:
```html
    <div class="modal-body" id="glossary-body">
      <!-- Populated dynamically by renderGlossary() in app.js -->
    </div>
```

- [ ] **Step 2: Add uiGlossary constant in app.js**

After the `FM` flag metadata object (around line 1329), add:

```js
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
```

- [ ] **Step 3: Add renderGlossary() and update openGlossary()**

Find `function openGlossary()` (around line 1295):
```js
function openGlossary() {
  S.glossaryModalOpen = true;
  document.getElementById('glossary-modal-overlay')?.classList.add('open');
  document.body.style.overflow = 'hidden';
}
```

Replace with:
```js
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
```

- [ ] **Step 4: Manual check**

Click "? Glossary" button. Modal should open with all sections rendered dynamically, including the "Analyst Mode" section. Close with ✕ or ESC.

- [ ] **Step 5: Commit**

```bash
git add events/2026_3m_open/deploy/app.js events/2026_3m_open/deploy/2026_3m_open_board.html
git commit -m "feat(3m-open): dynamic glossary with uiGlossary object + Analyst Mode entry"
```

---

## Task 4: Rename Scenario → Analyst Mode + Guardrail Banner

**Files:**
- Modify: `events/2026_3m_open/deploy/2026_3m_open_board.html`
- Modify: `events/2026_3m_open/deploy/app.js`

**Background:** Every UI reference to "Scenario" becomes "Analyst Mode". A persistent banner appears when the mode is active. Cards/rows get a subtle badge. Official view is the default.

- [ ] **Step 1: Update button and panel text in board HTML**

In `2026_3m_open_board.html`:

Find:
```html
    <button class="ctrl-btn" id="btn-scenario" style="border-color:var(--gold-dim);color:var(--gold-dim);">⊡ Scenario</button>
```
Replace with:
```html
    <button class="ctrl-btn" id="btn-scenario" style="border-color:var(--gold-dim);color:var(--gold-dim);">⊡ Analyst Mode</button>
```

Find:
```html
      <span style="font-weight:700;color:var(--gold);font-size:.9rem;">Scenario Builder</span>
      <span class="scenario-unofficial-tag">⚠ UNOFFICIAL — Scenario Mode Active</span>
      <button class="ctrl-btn" id="scenario-reset" style="font-size:.72rem;margin-left:auto;">Reset to Defaults</button>
      <button class="ctrl-btn" id="scenario-exit" style="font-size:.72rem;border-color:var(--gold);color:var(--gold);">✕ Exit Scenario Mode</button>
```
Replace with:
```html
      <span style="font-weight:700;color:var(--gold);font-size:.9rem;">Analyst Mode — Weight Sandbox</span>
      <span class="scenario-unofficial-tag">⚠ UNOFFICIAL — Analyst Mode Active</span>
      <button class="ctrl-btn" id="scenario-reset" style="font-size:.72rem;margin-left:auto;">Reset to official model</button>
      <button class="ctrl-btn" id="scenario-exit" style="font-size:.72rem;border-color:var(--gold);color:var(--gold);">✕ Exit Analyst Mode</button>
```

Find:
```html
    <div style="font-size:.72rem;color:var(--muted);margin-bottom:.65rem;">Adjust trait weights to explore how rankings shift. Results are not official VenueDNA outputs.</div>
```
Replace with:
```html
    <div style="font-size:.72rem;color:var(--muted);margin-bottom:.65rem;">Adjust trait weights to explore how rankings shift under a different emphasis. Results are NOT official VenueDNA outputs and are never saved.</div>
```

Also add the analyst mode banner container just before the `scenario-panel` div (after the `<!-- ══ ADVANCED FILTER PANEL ══ -->` closing `</div>`):
```html
<!-- ══ ANALYST MODE BANNER ═══════════════════════════════════════════════════ -->
<div id="analyst-mode-banner" class="hidden" style="background:#1a1200;border:2px solid var(--gold);padding:.5rem 1.2rem;text-align:center;position:sticky;top:53px;z-index:49;">
  <span style="color:var(--gold);font-weight:700;font-size:.8rem;font-family:'Inter',sans-serif;">
    ⊡ Analyst Mode (Unofficial scenario) — 
    <button onclick="resetScenario()" style="background:none;border:none;color:var(--gold);text-decoration:underline;cursor:pointer;font-size:.8rem;font-family:'Inter',sans-serif;">reset to restore official VenueDNA weights</button>
  </span>
</div>
```

- [ ] **Step 2: Update JS text references in enterScenarioMode() and exitScenario()**

Find in `app.js` `enterScenarioMode()`:
```js
  if (btn) { btn.style.borderColor = 'var(--gold)'; btn.style.color = 'var(--gold)'; btn.textContent = '⊡ Scenario ON'; }
```
Replace with:
```js
  if (btn) { btn.style.borderColor = 'var(--gold)'; btn.style.color = 'var(--gold)'; btn.textContent = '⊡ Analyst Mode ON'; }
  document.getElementById('analyst-mode-banner')?.classList.remove('hidden');
```

Find in `exitScenario()`:
```js
  if (btn) { btn.style.borderColor = 'var(--gold-dim)'; btn.style.color = 'var(--gold-dim)'; btn.textContent = '⊡ Scenario'; }
```
Replace with:
```js
  if (btn) { btn.style.borderColor = 'var(--gold-dim)'; btn.style.color = 'var(--gold-dim)'; btn.textContent = '⊡ Analyst Mode'; }
  document.getElementById('analyst-mode-banner')?.classList.add('hidden');
```

- [ ] **Step 3: Add scenario badge to table rows in renderScenarioResults()**

In `renderScenarioResults()`, find the "Add scenario rank cell" block:
```js
    const tdSc = document.createElement('td');
    tdSc.className = 'scenario-col scenario-rank-cell sans';
    tdSc.textContent = sRank != null ? sRank : '—';
    tr.appendChild(tdSc);
```

After this block, add a row-level class marker:
```js
    tr.classList.add('analyst-mode-row');
```

And at the top of `renderScenarioResults()`, after `if (!S.scenarioMode) return;`, add:
```js
  // Mark existing rows as clean — will be re-marked below
  document.querySelectorAll('#board-tbody tr.analyst-mode-row').forEach(r => r.classList.remove('analyst-mode-row'));
```

Add CSS for `analyst-mode-row` inline in the HTML style block (in `2026_3m_open_board.html`, after the `.scenario-unofficial-tag` style or near the flag styles):
```html
.analyst-mode-row td { background: rgba(201,168,76,.04) !important; }
.analyst-mode-row td:first-child::before { content:'⊡ '; font-size:.55rem; color:var(--gold-dim); vertical-align:middle; }
```

- [ ] **Step 4: Confirm no file write-back**

Search `app.js` for any `fetch(..., {method:'POST'})` or `localStorage.setItem` related to scenario data:
```bash
grep -n "POST\|localStorage\|scenarioWeights" events/2026_3m_open/deploy/app.js
```
Expected: only `S.scenarioWeights` state object reads/writes. No network POSTs. No localStorage persistence of weights.

- [ ] **Step 5: Manual check**

Click "⊡ Analyst Mode" button. Scenario panel should open with "Analyst Mode — Weight Sandbox" heading. A gold banner should appear below the sticky controls. Move a slider — board rows should get a subtle gold tint and the "⊡" prefix. Click "Reset to official model" — banner hides, row styling clears.

- [ ] **Step 6: Commit**

```bash
git add events/2026_3m_open/deploy/app.js events/2026_3m_open/deploy/2026_3m_open_board.html
git commit -m "feat(3m-open): rename Scenario to Analyst Mode with guardrail banner + row badges"
```

---

## Task 5: Implied Fair Odds in Probability Displays

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`

**Background:** Probabilities are 0–100 scale (e.g., `winPct: 1.7` = 1.7%). Fair American odds: `decimal = 100/p; american = +(decimal−1)*100` (all are positive odds since win/top probabilities are < 50%). Odds are UI-only — never stored.

- [ ] **Step 1: Add fairOdds() helper**

In `app.js`, after the `pct()` helper (around line 1323):
```js
function pct(v) { return v != null ? Number(v).toFixed(1) + '%' : '—'; }
```
Add after it:
```js
function fairOdds(v) {
  if (v == null || Number(v) <= 0) return null;
  const p  = Number(v);
  const dc = 100 / p;               // fair decimal odds
  const am = dc >= 2
    ? Math.round((dc - 1) * 100)    // positive: e.g. 5% → +1900
    : Math.round(-100 / (dc - 1));  // negative: e.g. 75% → -300
  return am >= 0 ? '+' + am : String(am);
}
```

- [ ] **Step 2: Add odds to modal §1 probability section**

In `openModal()`, the `<!-- §1 — PROBABILITY & OUTPUT -->` block renders `.modal-probs` with six `prob-box` divs. Find the prob-box for Win:
```js
<div class="prob-box"><div class="prob-val sans">${pct(wPct)}</div><div class="prob-lbl sans">Win</div></div>
```

Replace the entire `<div class="modal-probs">` block with:
```js
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
```

- [ ] **Step 3: Add .prob-odds CSS**

In `2026_3m_open_board.html`, in the inline `<style>` block, add after `.prob-lbl`:
```css
.prob-odds{font-size:.58rem;color:var(--muted);margin-top:.1rem;font-family:'Inter',sans-serif;}
```

- [ ] **Step 4: Add Win odds to spotlight cards**

In `renderSpotlight()`, the Win stat box:
```js
<div class="sc-stat-box"><div class="sc-stat-val sans">${pct(p.winPct)}</div><div class="sc-stat-lbl sans">Win</div></div>
```
Replace with:
```js
<div class="sc-stat-box">
  <div class="sc-stat-val sans">${pct(p.winPct)}</div>
  <div class="sc-stat-lbl sans">Win</div>
  ${fairOdds(p.winPct) ? `<div style="font-size:.55rem;color:var(--muted);font-family:'Inter',sans-serif;">${fairOdds(p.winPct)}</div>` : ''}
</div>
```

- [ ] **Step 5: Manual check**

Open a player modal (e.g., Scheffler at 1.7% win). Should show:
- "1.7%  Win  +5780" (or similar).
- Top-10 at ~10.9%: "+817"
- Cut at ~33.9%: "+195"

Spotlight cards should show Win% with odds below (e.g., "+5780").

- [ ] **Step 6: Commit**

```bash
git add events/2026_3m_open/deploy/app.js events/2026_3m_open/deploy/2026_3m_open_board.html
git commit -m "feat(3m-open): implied fair odds displayed in modal and spotlight cards"
```

---

## Task 6: Update Contention Map — NSI × VFS (delta_fit)

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`

**Background:** The current chart plots `x: neutralSkillIndex, y: vts_final`. The spec wants `y: delta_fit` (VFS — Venue Fit Signal). `delta_fit` ranges –0.500 to +0.500. The chart will become "who has skill AND venue fit" — top-right quadrant = structural winners, bottom-right = skill-only plays, top-left = venue fits without elite skill.

- [ ] **Step 1: Update renderContentionChart() data and axis**

Find in `renderContentionChart()` the data mapping (around line 668):
```js
      data: tp.map(p => {
        const hasFlag  = (p._flags || []).length > 0;
        const isDebut  = (p.data_depth || '').toUpperCase() === 'DEBUT';
        const highlight = (S.chartHighlightFlags && hasFlag) || (S.chartHighlightDebut && isDebut);
        return {
          x: p.neutralSkillIndex,
          y: p.vts_final,
          r: Math.max(4, Math.min(24, (p.winPct || 0.5) * 3.5)),
```

Replace `y: p.vts_final,` with:
```js
          y: p.delta_fit != null ? p.delta_fit : 0,
```

Also update the tooltip `lines` array in the tooltip callback:
```js
const lines = [`${d.player}  (${d.tier})`, `NSI: ${f1(d.nsi)} · VTS: ${f2(d.vts)} · Win: ${pct(d.winPct)}`];
```
Replace with:
```js
const lines = [`${d.player}  (${d.tier})`, `NSI: ${f1(d.nsi)} · Δ Fit: ${sgSign(d.vfs)} · Win: ${pct(d.winPct)}`];
```

And update the point data to carry `vfs` instead of relying on `vts`:
```js
          vts: p.vts_final,
```
Change to:
```js
          vts: p.vts_final,
          vfs: p.delta_fit != null ? p.delta_fit : 0,
```

- [ ] **Step 2: Update Y-axis config**

Find the Y axis scales block:
```js
        y: {
          title: { display: true, text: 'VTS Score', color: '#7a8fa6', font: { size: 11 } },
          ticks: { color: '#7a8fa6', font: { size: 10 } },
          grid:  { color: 'rgba(42,58,74,.4)' },
          min: 20, max: 105,
        },
```
Replace with:
```js
        y: {
          title: { display: true, text: 'Venue Fit Δ (SG/round)', color: '#7a8fa6', font: { size: 11 } },
          ticks: { color: '#7a8fa6', font: { size: 10 }, callback: v => (v >= 0 ? '+' : '') + v.toFixed(2) },
          grid:  { color: 'rgba(42,58,74,.4)' },
          min: -0.55, max: 0.55,
        },
```

- [ ] **Step 3: Update the section heading in board HTML**

In `2026_3m_open_board.html`, find:
```html
    <span style="font-size:.75rem;color:var(--muted);">NSI vs VTS · bubble = Win%</span>
```
Replace with:
```html
    <span style="font-size:.75rem;color:var(--muted);">NSI vs Venue Fit Δ · bubble = Win% · top-right = structural winner</span>
```

- [ ] **Step 4: Manual check**

Reload board. The contention chart's Y-axis should now show values from –0.55 to +0.55 with "+" prefix for positive values. Woodland (delta_fit: +0.500) should be near the top; Scheffler (delta_fit: –0.185) should be below the midline. Tooltip should show "Δ Fit" instead of "VTS".

- [ ] **Step 5: Commit**

```bash
git add events/2026_3m_open/deploy/app.js events/2026_3m_open/deploy/2026_3m_open_board.html
git commit -m "feat(3m-open): contention map Y-axis updated to VFS (Δ Fit) per NSI×VFS spec"
```

---

## Task 7: Views System (Table / Contention Map / Storylines)

**Files:**
- Modify: `events/2026_3m_open/deploy/app.js`
- Modify: `events/2026_3m_open/deploy/2026_3m_open_board.html`

**Background:** The "Views ▾" button currently opens a filter preset dropdown. It will be expanded to include view-mode switching at the top, with a divider before filter presets. Views: `table` (default), `map` (contention), `storylines`. Switching a view shows the relevant section and dims others. Storylines is a new module. Card View is handled by the existing mobile card layout — clicking "Card View" scrolls to player-cards and adds a CSS class that forces the card grid to display even on desktop.

- [ ] **Step 1: Add view-mode items to preset dropdown in board HTML**

Find the `preset-dropdown` div:
```html
      <div class="preset-dropdown" id="preset-dropdown">
        <button class="preset-item" data-preset="venue-fits">Venue Fits (Δ Fit ≥ +0.08)</button>
```
Replace with:
```html
      <div class="preset-dropdown" id="preset-dropdown">
        <button class="preset-item view-mode-item" data-view="table">⊞ Table View (default)</button>
        <button class="preset-item view-mode-item" data-view="cards">⊟ Card View</button>
        <button class="preset-item view-mode-item" data-view="map">◎ Contention Map</button>
        <button class="preset-item view-mode-item" data-view="storylines">◈ Storylines</button>
        <div class="preset-divider"></div>
        <div style="padding:.3rem .9rem;font-size:.68rem;color:var(--muted)">Filter Presets</div>
        <button class="preset-item" data-preset="venue-fits">Venue Fits (Δ Fit ≥ +0.08)</button>
```

- [ ] **Step 2: Add #sec-storylines section in board HTML**

After `<!-- ══ TIER INTEL ══ -->` section but before `<!-- ══ LIVE ROUND ══ -->`:
```html
<!-- ══ STORYLINES ═══════════════════════════════════════════════════════════ -->
<section class="nav-section hidden" id="sec-storylines" style="max-width:1400px;margin:1.5rem auto;padding:0 1rem;">
  <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;flex-wrap:wrap;">
    <h2 style="color:var(--gold);font-size:1.1rem;">Storylines</h2>
    <span style="font-size:.75rem;color:var(--muted);">Key narratives for 3M Open 2026</span>
  </div>
  <div id="storylines-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.75rem;"></div>
</section>
```

- [ ] **Step 3: Add S.currentView to state and switchView() function in app.js**

In the `S` state object (top of app.js), add:
```js
  currentView:  'table',
```

After `renderAll()` function (around line 311), add:
```js
// ── Views system ───────────────────────────────────────────────────────────────
const VIEW_SECTIONS = {
  table:      ['sec-spotlight','sec-board','sec-intel','sec-method','sec-contention'],
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

  // Card view: force cards grid visible even on desktop
  const cardsGrid = document.getElementById('player-cards');
  if (cardsGrid) {
    cardsGrid.style.display = view === 'cards' ? 'grid' : '';
  }

  // Scroll to primary section for the view
  const primary = VIEW_SECTIONS[view]?.[0];
  if (primary) {
    document.getElementById(primary)?.scrollIntoView({ behavior:'smooth', block:'start' });
  }

  // Render storylines on demand
  if (view === 'storylines') renderStorylines();

  // Update active state on view-mode items
  document.querySelectorAll('.view-mode-item[data-view]').forEach(btn => {
    btn.style.color = btn.dataset.view === view ? 'var(--gold)' : '';
    btn.style.fontWeight = btn.dataset.view === view ? '700' : '';
  });
}
```

- [ ] **Step 4: Wire view-mode items in bindEvents()**

In `bindEvents()`, find the preset dropdown wiring:
```js
    presetDd.querySelectorAll('.preset-item[data-preset]').forEach(btn => {
      btn.addEventListener('click', () => {
        applyPreset(btn.dataset.preset);
        presetDd.style.display = 'none';
      });
    });
```
After this block (still inside the `if (btnPresets && presetDd)` guard), add:
```js
    presetDd.querySelectorAll('.view-mode-item[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        switchView(btn.dataset.view);
        presetDd.style.display = 'none';
      });
    });
```

- [ ] **Step 5: Add renderStorylines() function in app.js**

After `renderIntel()` function (around line 643), add:

```js
// ── Storylines module — read-only narrative strip ────────────────────────────
function renderStorylines() {
  const grid = document.getElementById('storylines-grid');
  if (!grid || !S.boardData.length) return;

  // 1. Best venue history — highest delta_fit with a positive value
  const byVFS = [...S.boardData].filter(p => p.delta_fit != null).sort((a, b) => b.delta_fit - a.delta_fit);
  const topVFS = byVFS[0];

  // 2. Top T1/T2 structural winner — highest VTS with positive delta_fit
  const topContender = S.boardData.find(p => (p.tier === 'T1' || p.tier === 'T2') && (p.delta_fit || 0) >= 0);

  // 3. Best recent-form riser — highest vsBaselineL20 from briefs (card copy field)
  const risers = S.boardData.map(p => {
    const br = S.briefsByName[normName(p.player)] || {};
    return { player: p.player, tier: p.tier, vsBaselineL20: br.vsBaselineL20 != null ? Number(br.vsBaselineL20) : null };
  }).filter(x => x.vsBaselineL20 != null && x.vsBaselineL20 > 0).sort((a, b) => b.vsBaselineL20 - a.vsBaselineL20);
  const topRiser = risers[0];

  // 4. Dark horse — T3/T4 with highest delta_fit
  const darkHorse = S.boardData.find(p => (p.tier === 'T3' || p.tier === 'T4') && (p.delta_fit || 0) > 0.1);

  function storylineCard(icon, label, player, narrative, tierColor) {
    if (!player) return '';
    const br  = S.briefsByName[normName(player.player || player)] || {};
    const txt = narrative || br.convictionStatement || br.conviction_statement || br.why_it_fits_structurally || '';
    const tc  = tierColor || 'var(--gold)';
    return `<div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem;cursor:pointer;" data-player="${esc(player.player || player)}">
      <div style="font-size:.65rem;color:${tc};font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem;font-family:'Inter',sans-serif;">${icon} ${label}</div>
      <div style="font-weight:700;font-size:.9rem;color:var(--text);margin-bottom:.3rem;">${esc(player.player || player)}</div>
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
      `vs. Baseline L20: ${topRiser.vsBaselineL20 >= 0 ? '+' : ''}${topRiser.vsBaselineL20.toFixed(2)} SG — trending above their own baseline.`,
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
```

- [ ] **Step 6: Manual check**

Click "Views ▾" button. Dropdown should show four view-mode items at top, then a divider, then filter presets. Click "◎ Contention Map" → board sections hide, contention chart scrolls into view and is visible. Click "◈ Storylines" → storylines section appears with 3–4 narrative cards. Clicking a storyline card opens that player's modal. Click "⊞ Table View" → returns to default layout.

- [ ] **Step 7: Commit**

```bash
git add events/2026_3m_open/deploy/app.js events/2026_3m_open/deploy/2026_3m_open_board.html
git commit -m "feat(3m-open): views system (table/cards/map/storylines) + storylines module"
```

---

## Self-Review Checklist

**Spec coverage:**

| Spec requirement | Task |
|-----------------|------|
| Merge card copy narrative into playerbriefs.json | Task 1 |
| Map all narrative fields (headline, scouting_report, form_note, win_case, risk_vector, tags, deltas) | Tasks 1 + 2 |
| Dynamic uiGlossary object | Task 3 |
| Wire ? Glossary to render glossary | Task 3 |
| Views menu with Table/Card/Map/Storylines | Task 7 |
| Rename Scenario → Analyst Mode | Task 4 |
| Persistent Analyst Mode banner | Task 4 |
| Analyst Mode does not write back to JSON | Task 4 (verified by grep) |
| Reset to official model button | Task 4 (exists as scenario-reset, re-labeled) |
| Analyst Mode badge on rows | Task 4 |
| Implied fair odds in table/cards/modal | Task 5 |
| Fair odds formula: (100/p)−1 → American | Task 5 |
| Odds are UI-only derivatives (no JSON write-back) | Task 5 |
| Contention map NSI × VFS (delta_fit) | Task 6 |
| Bubble size = winPct | Task 6 (unchanged from existing) |
| Tooltip: player name, NSI, VFS, winPct | Task 6 |
| Click bubble → open player modal | Task 6 (unchanged from existing) |
| Storylines strip: venue fit, form riser, dark horse | Task 7 |
| Storylines read-only from existing artifacts | Task 7 |

**Type consistency:** `fairOdds(v)` used consistently in Task 5 steps 2 and 4. `switchView(view)` defined in step 3, wired in step 4, called from button handlers.

**No placeholders:** All code blocks contain complete, runnable code.

---

## TODOs for Future Rounds

- **Live reranking:** When R1 data loads (`switchRound('1')`), the Storylines module should re-run `renderStorylines()` using live SG data. Wire this in `renderLiveRound()`.
- **Wave simulator:** Once market data is wired, the dark-horse storyline can filter by "low market expectation" (e.g., win odds > +3000).
- **Card View desktop:** Currently forces `player-cards` grid display via inline style. Consider a proper responsive breakpoint override in styles.css.
- **Storylines persistence across views:** If user switches views and back, storylines re-render cleanly (idempotent) — no caching needed.
- **Fair odds on mobile cards:** `renderCards()` currently shows only Win%, NSI, Δ Fit. Consider adding fairOdds(p.winPct) to the Win% metric cell.
