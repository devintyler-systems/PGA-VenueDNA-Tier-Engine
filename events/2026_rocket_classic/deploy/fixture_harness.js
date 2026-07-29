/**
 * fixture_harness.js
 * VenueDNA Rocket Classic — fixture harness only.
 * Renders three fixture players, player drawer, badge system, evidence states.
 * Does not contain the full board (tabs, leaderboard, filter sidebar, spotlight).
 * badge_policy.v1.json is the single source of truth — no badge constants here.
 */

(function () {
  "use strict";

  // ── Module state ────────────────────────────────────────────────────────────

  const S = {
    badgePolicy:    null,   // loaded from config/badge_policy.v1.json
    fixtures:       [],     // [{input, narrative}, ...]
    activeFilters:  {       // filter state — never mutated by drawer open/close
      tier:         "All",
      badges:       [],     // array of active badge_ids
    },
    openPlayerId:   null,   // currently open drawer player_id
    auditCompanion: null,   // loaded from data/2026_rocket_classic_tripod_audit.json
  };

  // ── Bootstrap ────────────────────────────────────────────────────────────────

  async function init() {
    try {
      S.badgePolicy = await loadJSON("config/badge_policy.v1.json");
    } catch {
      // Fallback: legacy repo-root-relative path (dev server only)
      try {
        S.badgePolicy = await loadJSON("../../../../config/badge_policy.v1.json");
      } catch {
        console.error("badge_policy.v1.json not found. Badge rendering will be degraded.");
        S.badgePolicy = { badges: [] };
      }
    }

    const fixtureDefs = [
      {
        inputPath:     "fixtures/fixture_elite_001_input.json",
        narrativePath: "fixtures/fixture_elite_001_narrative.json",
      },
      {
        inputPath:     "fixtures/fixture_volatile_001_input.json",
        narrativePath: "fixtures/fixture_volatile_001_narrative.json",
      },
      {
        inputPath:     "fixtures/fixture_thin_001_input.json",
        narrativePath: "fixtures/fixture_thin_001_narrative.json",
      },
      {
        inputPath:     "fixtures/fixture_structural_failure_001_input.json",
        narrativePath: "fixtures/fixture_structural_failure_001_narrative.json",
      },
    ];

    for (const def of fixtureDefs) {
      try {
        const [inp, nar] = await Promise.all([
          loadJSON(def.inputPath),
          loadJSON(def.narrativePath),
        ]);
        S.fixtures.push({ input: inp, narrative: nar });
      } catch (e) {
        console.error("Failed to load fixture:", def, e);
      }
    }

    renderBadgeFilters();
    renderRoster();
    // Load tripod audit companion — graceful fallback if absent or malformed
    try {
      S.auditCompanion = await loadJSON("data/2026_rocket_classic_tripod_audit.json");
    } catch {
      try {
        S.auditCompanion = await loadJSON("../deploy/data/2026_rocket_classic_tripod_audit.json");
      } catch {
        console.info("Tripod audit companion not found — Detroit Fit section will show unavailable.");
        S.auditCompanion = null;
      }
    }

    bindGlobalEvents();
  }

  // ── Data loading ─────────────────────────────────────────────────────────────

  function loadJSON(path) {
    return fetch(path).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${path}`);
      return r.json();
    });
  }

  // ── Detroit Fit helpers ───────────────────────────────────────────────────────

  function getAuditRecord(playerId) {
    if (!S.auditCompanion) return null;
    return (S.auditCompanion.players || []).find((p) => p.player_id === playerId) || null;
  }

  function renderDetroitFit(playerId) {
    const TOOLTIP = "Detroit tripod is a venue-fit audit: SG: Approach, App 150–200, and Total Driving. "
                  + "It does not alter the current model rank, tier, or probabilities.";
    const rec = getAuditRecord(playerId);

    if (!rec) {
      return `<div class="detroit-fit-section detroit-fit-unavailable">
        <div class="detroit-fit-label">Detroit Fit
          <span class="detroit-fit-info" title="${esc(TOOLTIP)}" aria-label="${esc(TOOLTIP)}">&#x24D8;</span>
        </div>
        <span class="detroit-fit-status-text">Detroit Fit data not available for this player.</span>
      </div>`;
    }

    if (rec.tripod_eligibility === "UNAVAILABLE") {
      return `<div class="detroit-fit-section detroit-fit-unavailable">
        <div class="detroit-fit-label">Detroit Fit
          <span class="detroit-fit-info" title="${esc(TOOLTIP)}" aria-label="${esc(TOOLTIP)}">&#x24D8;</span>
        </div>
        <span class="detroit-fit-status-text">${esc(rec.audit_interpretation || "Tripod traits unavailable.")}</span>
      </div>`;
    }

    const qualified = rec.tripod_qualified;
    const supported = rec.tripod_supported;

    let statusClass = "detroit-fit-incomplete";
    let statusText  = "Tripod traits incomplete";
    if (qualified)      { statusClass = "detroit-fit-qualified"; statusText = "Tripod-qualified (audit)"; }
    else if (supported) { statusClass = "detroit-fit-supported"; statusText = "Tripod-supported (audit)"; }

    const cp = rec.component_percentiles || {};
    const compHtml = `
      <div class="detroit-fit-components">
        <span class="detroit-fit-comp">SG: App <em>${cp.sg_approach != null ? cp.sg_approach + "p" : "—"}</em></span>
        <span class="detroit-fit-comp">App 150–200 <em>${cp.app_150_200 != null ? cp.app_150_200 + "p" : "—"}</em></span>
        <span class="detroit-fit-comp">Total Drv <em>${cp.total_driving != null ? cp.total_driving + "p" : "—"}</em></span>
      </div>`;

    const formRisk = (rec.recent_form_risk_flag === true)
      ? `<div class="detroit-fit-form-risk">⚠ Form risk noted (audit only)</div>`
      : "";

    return `<div class="detroit-fit-section">
      <div class="detroit-fit-label">Detroit Fit
        <span class="detroit-fit-info" title="${esc(TOOLTIP)}" aria-label="${esc(TOOLTIP)}">&#x24D8;</span>
      </div>
      <span class="detroit-fit-status ${esc(statusClass)}">${esc(statusText)}</span>
      ${compHtml}
      <div class="detroit-fit-interpretation">${esc(rec.audit_interpretation || "")}</div>
      ${formRisk}
    </div>`;
  }

  // ── Badge policy helpers ──────────────────────────────────────────────────────

  function getBadgeDef(badgeId) {
    if (!S.badgePolicy) return null;
    return S.badgePolicy.badges.find((b) => b.badge_id === badgeId) || null;
  }

  function renderBadgePill(badgeObj) {
    const def = getBadgeDef(badgeObj.badge_id);
    if (!def) {
      console.warn(`badge_id '${badgeObj.badge_id}' not found in badge_policy — omitting`);
      return "";
    }
    const color = def.color || "#6B7280";
    return `<span class="badge-pill"
      style="background:${color}22; border-color:${color}55; color:${color};"
      title="${esc(badgeObj.qualification_reason)}">
      ${esc(def.icon || "")} ${esc(def.label)}
    </span>`;
  }

  // ── Filter sidebar ────────────────────────────────────────────────────────────

  function renderBadgeFilters() {
    const container = document.getElementById("badge-filter-list");
    if (!container || !S.badgePolicy) return;

    const sorted = [...S.badgePolicy.badges].sort(
      (a, b) => (a.display_order || 99) - (b.display_order || 99)
    );

    container.innerHTML = sorted.map((b) => `
      <label class="badge-filter-item">
        <input type="checkbox" data-badge-id="${esc(b.badge_id)}" />
        <span style="color:${esc(b.color || '#888')};">${esc(b.icon || "")} ${esc(b.label)}</span>
      </label>
    `).join("");

    container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const bid = cb.dataset.badgeId;
        if (cb.checked) {
          if (!S.activeFilters.badges.includes(bid)) S.activeFilters.badges.push(bid);
        } else {
          S.activeFilters.badges = S.activeFilters.badges.filter((b) => b !== bid);
        }
        updateFilterCount();
        // Drawer does NOT close or reset on filter change
      });
    });
  }

  function updateFilterCount() {
    const visible = filteredFixtures().length;
    const el = document.getElementById("filter-count");
    if (el) el.innerHTML = `Showing <strong>${visible}</strong> of <strong>${S.fixtures.length}</strong> players`;
  }

  function filteredFixtures() {
    return S.fixtures.filter((f) => {
      const inp = f.input;
      const tier = inp.projection.tier;

      if (S.activeFilters.tier !== "All" && tier !== S.activeFilters.tier) return false;

      if (S.activeFilters.badges.length > 0) {
        const playerBadgeIds = (inp.badges || []).map((b) => b.badge_id);
        const hasAll = S.activeFilters.badges.every((bid) => playerBadgeIds.includes(bid));
        if (!hasAll) return false;
      }

      return true;
    });
  }

  // ── Tier chip bindings ────────────────────────────────────────────────────────

  function bindTierChips() {
    document.querySelectorAll(".tier-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll(".tier-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        S.activeFilters.tier = chip.dataset.tier;
        updateFilterCount();
        // Drawer does NOT close or reset on filter change
      });
    });
  }

  // ── Roster rendering ──────────────────────────────────────────────────────────

  function renderRoster() {
    const tbody = document.getElementById("roster-tbody");
    if (!tbody) return;

    tbody.innerHTML = S.fixtures.map((f) => {
      const inp = f.input;
      const pid = inp.player.player_id;
      const name = inp.player.display_name;
      const tier = inp.projection.tier;
      const vts  = inp.projection.vts.toFixed(1);
      const badges = (inp.badges || []).map(renderBadgePill).join("");
      const conv  = inp.projection.conviction;

      return `<tr class="roster-row" data-player-id="${esc(pid)}" tabindex="0" role="button" aria-label="View ${esc(name)}">
        <td><span class="player-name">${esc(name)}</span></td>
        <td><span class="vts-score">${esc(vts)}</span></td>
        <td><span class="tier-pill tier-${esc(tier)}">${esc(tier)}</span></td>
        <td><span style="font-size:12px; color:var(--color-text-muted);">${esc(conv)}</span></td>
        <td><div class="badge-row">${badges}</div></td>
        <td><button class="open-btn" data-player-id="${esc(pid)}">View ›</button></td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll(".roster-row").forEach((row) => {
      row.addEventListener("click", () => openDrawer(row.dataset.playerId));
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") openDrawer(row.dataset.playerId);
      });
    });

    updateFilterCount();
  }

  // ── Drawer ─────────────────────────────────────────────────────────────────────

  function findFixture(playerId) {
    return S.fixtures.find((f) => f.input.player.player_id === playerId) || null;
  }

  function openDrawer(playerId) {
    const fixture = findFixture(playerId);
    if (!fixture) return;

    S.openPlayerId = playerId;

    // Update active row styling
    document.querySelectorAll(".roster-row").forEach((r) => r.classList.remove("active"));
    const activeRow = document.querySelector(`.roster-row[data-player-id="${CSS.escape(playerId)}"]`);
    if (activeRow) activeRow.classList.add("active");

    renderDrawer(fixture.input, fixture.narrative);

    const drawer = document.getElementById("player-drawer");
    drawer.classList.add("open");

    // Mobile: show backdrop
    const backdrop = document.getElementById("overlay-backdrop");
    if (backdrop) backdrop.classList.add("active");

    // Dim roster on desktop (opacity stays >0 so board is still visible)
    const roster = document.getElementById("roster-panel");
    if (roster && window.innerWidth >= 1280) {
      roster.style.opacity = "0.45";
      roster.style.transition = "opacity 0.25s";
      roster.style.pointerEvents = "auto"; // still interactive
    }
  }

  function closeDrawer() {
    S.openPlayerId = null;

    const drawer = document.getElementById("player-drawer");
    drawer.classList.remove("open");

    document.querySelectorAll(".roster-row").forEach((r) => r.classList.remove("active"));

    const backdrop = document.getElementById("overlay-backdrop");
    if (backdrop) backdrop.classList.remove("active");

    const roster = document.getElementById("roster-panel");
    if (roster) {
      roster.style.opacity = "";
      roster.style.pointerEvents = "";
    }
    // activeFilters is NOT reset here — per spec
  }

  function renderDrawer(inputObj, narrativeObj) {
    const drawerInner = document.getElementById("drawer-inner");
    if (!drawerInner) return;

    const validationErrors = narrativeObj.quality?.validation_errors || [];
    const evidenceCoverage = narrativeObj.quality?.evidence_coverage || "high";

    // ── Structural validation failure state ──────────────────────────────────
    if (validationErrors.length > 0) {
      drawerInner.innerHTML = `
        <div class="drawer-close">
          <span style="font-size:13px; color:var(--color-text-muted);">
            ${esc(inputObj.player.display_name)}
          </span>
          <button onclick="window.__harness.closeDrawer()" aria-label="Close">✕ Close</button>
        </div>
        <div class="narrative-unavailable">
          <strong>Narrative unavailable — structural validation failed</strong>
          ${validationErrors.length} validation error(s) blocked narrative generation.
          Player scoring data is available; prose content has been suppressed.
        </div>
      `;
      return;
    }

    // ── Evidence coverage banner ─────────────────────────────────────────────
    const evidenceBanner = evidenceCoverage !== "high"
      ? `<div class="evidence-banner low" role="status">
          ⚠ Limited evidence — ${evidenceCoverage} confidence
        </div>`
      : "";

    // ── Badges ───────────────────────────────────────────────────────────────
    const badgePills = (inputObj.badges || []).map(renderBadgePill).join(" ");

    // ── Strengths ────────────────────────────────────────────────────────────
    const strengthsHtml = (narrativeObj.strengths || []).map((s) => {
      const traitData = (inputObj.traits || []).find((t) => t.trait_id === s.trait_id);
      const score = traitData ? traitData.score : null;
      const barHtml = score !== null
        ? `<div class="trait-bar-wrap">
            <div class="trait-bar-bg">
              <div class="trait-bar-fill" style="width:${score.toFixed(1)}%"></div>
            </div>
            <span class="trait-bar-score">${score.toFixed(0)}</span>
          </div>`
        : "";
      return `<div class="strength-card">
        <div class="card-label">${esc(s.label)}</div>
        <div class="card-statement">${esc(s.statement)}</div>
        ${barHtml}
      </div>`;
    }).join("");

    // ── Weaknesses ────────────────────────────────────────────────────────────
    const weaknessesHtml = (narrativeObj.weaknesses || []).map((w) => {
      const riskData = (inputObj.risk_factors || []).find(
        (r) => r.risk_id === w.trait_id || r.evidence_trait_id === w.trait_id
      );
      const severity = riskData?.severity || "medium";
      return `<div class="weakness-card severity-${esc(severity)}">
        <div class="card-label">${esc(w.label)}</div>
        <div class="card-statement">${esc(w.statement)}</div>
      </div>`;
    }).join("");

    drawerInner.innerHTML = `
      <div class="drawer-close">
        <span style="font-size:13px; color:var(--color-text-muted);">
          ${esc(inputObj.player.display_name)}
          <span class="tier-pill tier-${esc(inputObj.projection.tier)}" style="margin-left:6px;">
            ${esc(inputObj.projection.tier)}
          </span>
        </span>
        <button onclick="window.__harness.closeDrawer()" aria-label="Close">✕ Close</button>
      </div>

      ${evidenceBanner}

      <div class="drawer-headline">${esc(narrativeObj.headline)}</div>

      <div class="drawer-badges">${badgePills}</div>

      <div class="drawer-section">
        <div class="drawer-section-label">Story</div>
        <div class="drawer-prose">${esc(narrativeObj.story_hook)}</div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">At Detroit Golf Club</div>
        <div class="drawer-prose">${esc(narrativeObj.venue_fit.text)}</div>
      </div>

      <div class="drawer-divider"></div>

      <div class="drawer-section">
        <div class="drawer-section-label">Strengths</div>
        ${strengthsHtml}
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Risks</div>
        ${weaknessesHtml}
      </div>

      <div class="drawer-divider"></div>

      <div class="drawer-section">
        <div class="drawer-section-label">Win Scenario</div>
        <div class="scenario-block win">
          <div class="scenario-tag win">To Win</div>
          ${esc(narrativeObj.win_scenario)}
        </div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Failure Scenario</div>
        <div class="scenario-block failure">
          <div class="scenario-tag fail">Risk</div>
          ${esc(narrativeObj.failure_scenario)}
        </div>
      </div>

      <div class="drawer-divider"></div>

      <div class="drawer-section">
        <div class="drawer-section-label">Projection</div>
        <div class="drawer-prose">${esc(narrativeObj.projection_explainer.text)}</div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Form</div>
        <div class="drawer-prose">${esc(narrativeObj.form_note)}</div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Venue History</div>
        <div class="drawer-prose">${esc(narrativeObj.venue_history_note)}</div>
      </div>

      <div class="drawer-divider"></div>

      ${renderDetroitFit(inputObj.player.player_id)}
    `;
  }

  // ── Global events ─────────────────────────────────────────────────────────────

  function bindGlobalEvents() {
    // Escape key closes drawer
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && S.openPlayerId) closeDrawer();
    });

    // Click outside drawer on roster panel closes it (desktop)
    const rosterPanel = document.getElementById("roster-panel");
    if (rosterPanel) {
      rosterPanel.addEventListener("click", (e) => {
        // Only close if click was on the dimmed roster background, not on a row
        if (S.openPlayerId && !e.target.closest(".roster-row")) {
          closeDrawer();
        }
      });
    }

    // Mobile backdrop click closes drawer
    const backdrop = document.getElementById("overlay-backdrop");
    if (backdrop) {
      backdrop.addEventListener("click", () => closeDrawer());
    }

    // Filter toggle (mid/mobile)
    const filterToggle = document.getElementById("filter-toggle-btn");
    const filterPopover = document.getElementById("filter-popover");
    const filterOverlay = document.getElementById("filter-overlay");

    if (filterToggle) {
      filterToggle.addEventListener("click", () => {
        if (filterPopover) filterPopover.classList.toggle("open");
        if (filterOverlay) filterOverlay.classList.toggle("open");
      });
    }

    bindTierChips();
    updateFilterCount();
  }

  // ── Utility ────────────────────────────────────────────────────────────────────

  function esc(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ── Public API (for Playwright verify access) ─────────────────────────────────

  window.__harness = {
    closeDrawer,
    getActiveFilters: () => ({ ...S.activeFilters, badges: [...S.activeFilters.badges] }),
    getOpenPlayerId: () => S.openPlayerId,
  };

  // ── Init ───────────────────────────────────────────────────────────────────────

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
