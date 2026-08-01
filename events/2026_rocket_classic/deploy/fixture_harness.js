/**
 * fixture_harness.js
 * VenueDNA Rocket Classic — fixture harness only.
 * Renders real event payload (142 scored players) with synthetic fixture fallback.
 * badge_policy.v1.json is the single source of truth — no badge constants here.
 */

(function () {
  "use strict";

  // ── Module state ────────────────────────────────────────────────────────────

  const S = {
    badgePolicy:    null,   // loaded from config/badge_policy.v1.json
    fixtures:       [],     // [{input, narrative}, ...]
    playerBriefs:   null,   // keyed by player_name; from data/2026_rocket_classic_player_briefs.json
    activeFilters:  {
      tier:         "All",
      badges:       [],
      traitRanges:  {},
      query:        "",
    },
    openPlayerId:   null,
    auditCompanion: null,

    // Live R2 diagnostic layer — read-only overlay, never mutates the fixtures above.
    currentView:       "pre-event",   // "pre-event" | "live"
    liveData:          null,          // parsed data/2026_rocket_classic_r2_live.json
    liveAvailable:     false,
    liveRendered:      false,
    liveKeyToPlayerId: {},            // client-computed name key -> fixture player_id
    playerIdToLiveKey: {},            // reverse of the above, for drawer injection lookups
    survivorsByKey:    {},            // player_key -> cut_survivors record (built once live data loads)
  };

  // ── Bootstrap ────────────────────────────────────────────────────────────────

  async function init() {
    try {
      S.badgePolicy = await loadJSON("config/badge_policy.v1.json");
    } catch {
      try {
        S.badgePolicy = await loadJSON("../../../../config/badge_policy.v1.json");
      } catch {
        console.error("badge_policy.v1.json not found. Badge glossary will be degraded.");
        S.badgePolicy = { badges: [] };
      }
    }

    try {
      const briefsRaw = await loadJSON("data/2026_rocket_classic_player_briefs.json");
      S.playerBriefs = briefsRaw.players || null;
    } catch {
      console.info("Player briefs not found — structural case will use reduced-detail fallback.");
    }

    let payloadLoaded = false;
    try {
      const payload = await loadJSON("data/2026_rocket_classic_event_payload.json");
      const players = (payload.players || []).filter((p) => p.data_depth !== "UNSCORED");
      for (const p of players) {
        try {
          const brief = S.playerBriefs ? (S.playerBriefs[p.player_name] || null) : null;
          S.fixtures.push(playerToFixture(p, payload, brief));
        } catch (e) {
          console.error("Failed to adapt player:", p.player_id, e);
        }
      }
      if (S.fixtures.length > 0) payloadLoaded = true;
    } catch (e) {
      console.warn("Event payload unavailable — loading synthetic test fixtures:", e);
    }

    if (!payloadLoaded) {
      const fixtureDefs = [
        { inputPath: "fixtures/fixture_elite_001_input.json",             narrativePath: "fixtures/fixture_elite_001_narrative.json" },
        { inputPath: "fixtures/fixture_volatile_001_input.json",          narrativePath: "fixtures/fixture_volatile_001_narrative.json" },
        { inputPath: "fixtures/fixture_thin_001_input.json",              narrativePath: "fixtures/fixture_thin_001_narrative.json" },
        { inputPath: "fixtures/fixture_structural_failure_001_input.json", narrativePath: "fixtures/fixture_structural_failure_001_narrative.json" },
      ];
      for (const def of fixtureDefs) {
        try {
          const [inp, nar] = await Promise.all([loadJSON(def.inputPath), loadJSON(def.narrativePath)]);
          S.fixtures.push({ input: inp, narrative: nar });
        } catch (e) {
          console.error("Failed to load fixture:", def, e);
        }
      }
    }

    renderBadgeFilters();
    renderTraitSliders();
    renderRoster();

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

    try {
      S.liveData = await loadJSON("data/2026_rocket_classic_r2_live.json");
      S.liveAvailable = true;
      indexLiveData();
    } catch (e) {
      console.warn("Live R2 data unavailable — Live: R2 Update view stays hidden.", e);
      S.liveAvailable = false;
    }

    const liveToggleBtn = document.getElementById("view-toggle-live");
    if (liveToggleBtn) liveToggleBtn.hidden = !S.liveAvailable;

    bindGlobalEvents();
  }

  // ── Data loading ─────────────────────────────────────────────────────────────

  function loadJSON(path) {
    return fetch(path).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${path}`);
      return r.json();
    });
  }

  // ── Real-payload adapter ──────────────────────────────────────────────────────

  const TRAIT_ID_MAP = {
    "SG: Approach":     "approach_play",
    "App 150-200":      "iron_play",
    "Total Driving":    "total_driving",
    "Course History":   "course_history",
    "Putting":          "putting",
    "SG: Putting":      "putting",
    "Par-5 Scoring":    "par5_scoring",
    "Par 5 Scoring":    "par5_scoring",
    "Driving Accuracy": "driving_accuracy",
    "Driving Distance": "driving_distance",
    "Recent Form":      "recent_form",
    "Closing Holes":    "closing_holes",
  };

  const FILTER_ELIGIBLE_TRAITS = new Set([
    "driving_distance",
    "driving_accuracy",
  ]);

  // Maps trait label → trait_availability key in per-player payload
  const TRAIT_AVAIL_KEY_MAP = {
    "SG: Approach":     "trait_approach_raw",
    "App 150-200":      "trait_long_iron_raw",
    "Total Driving":    "sg_base_composite",
    "Course History":   "ch_adjustment",
    "Recent Form":      "true_sg_l20",
    "Putting":          "putt_true",
    "SG: Putting":      "putt_true",
  };

  function evidenceStatusFromAvail(avail) {
    if (!avail) return "DERIVED";
    const a = avail.availability;
    const s = avail.source_status;
    if (a === "MEASURED" || a === "MEASURED_ZERO") return "MEASURED";
    if (a === "UNAVAILABLE" || a === "MISSING_ZERO_FILLED" || a === "DEBUT_ZERO" || s === "MISSING") return "UNAVAILABLE";
    return "DERIVED";
  }

  function convictionLabel(dataDepth) {
    if (dataDepth === "FULL")  return "High";
    if (dataDepth === "DEBUT") return "Medium";
    return "Low";
  }

  function validateEmittedBadges(rawBadges, badgePolicy) {
    if (!Array.isArray(rawBadges)) return [];
    const known = new Set((badgePolicy?.badges || []).map((b) => b.badge_id));
    return rawBadges.filter((b) => {
      if (!b || typeof b.badge_id !== "string") return false;
      if (!known.has(b.badge_id)) {
        console.error(`Badge validation error: unknown badge_id '${b.badge_id}' — omitting`);
        return false;
      }
      return true;
    });
  }

  function playerToFixture(p, payload, brief) {
    const traitAvail = p.trait_availability || {};

    const traits = (p.trait_scores || []).map((ts) => {
      const tid = TRAIT_ID_MAP[ts.label]
        || ts.label.toLowerCase().replace(/[^a-z0-9]+/g, "_");
      const availKey = TRAIT_AVAIL_KEY_MAP[ts.label];
      const avail = availKey ? (traitAvail[availKey] || null) : null;
      const isVenueHistory = avail
        ? !!(avail.narrative_context === "venue_history" || (avail.narrative_constraint || "").includes("venue-history"))
        : false;

      return {
        trait_id:              tid,
        label:                 ts.label,
        score:                 Number(ts.score ?? 0),
        weight:                ts.weight,
        venue_importance:      ts.weight,
        direction:             (ts.score ?? 0) >= 60 ? "strength" : (ts.score ?? 0) >= 40 ? "neutral" : "weakness",
        evidence_status:       evidenceStatusFromAvail(avail),
        venue_history_context: isVenueHistory,
      };
    });

    const SKIP_TAGS = ["No Clear Structural Risk", "unknown", "Unknown"];

    const strengths = (p.strength_tags || [])
      .filter((t) => !SKIP_TAGS.includes(t))
      .map((tag) => {
        const matched = traits.find((t) => tag.toLowerCase().includes(t.label.toLowerCase()));
        return { label: matched ? matched.label : tag, statement: tag, trait_id: matched ? matched.trait_id : null };
      });

    const weaknesses = (p.weakness_tags || [])
      .filter((t) => !SKIP_TAGS.includes(t))
      .map((tag) => {
        const matched = traits.find((t) => tag.toLowerCase().includes(t.label.toLowerCase()));
        return { label: matched ? matched.label : tag, statement: tag, trait_id: matched ? matched.trait_id : null };
      });

    let formNote = "";
    if (p.true_sg_l20 != null) {
      const sign = Number(p.true_sg_l20) >= 0 ? "+" : "";
      formNote = `Recent SG: ${sign}${Number(p.true_sg_l20).toFixed(2)} per round (last 20 rounds).`;
    } else {
      formNote = (p.strength_tags || []).find((t) => /form|streak|hot|cold/i.test(t))
        || "Form data not available.";
    }

    const venueHistNote = (p.ch_adjustment != null && p.ch_adjustment !== 0)
      ? `Course history adjustment: ${Number(p.ch_adjustment) >= 0 ? "+" : ""}${Number(p.ch_adjustment).toFixed(2)} strokes.`
      : "No prior starts at Detroit Golf Club on record.";

    const failureText = weaknesses.length > 0
      ? weaknesses.map((w) => w.statement).join(" ")
      : "The projection breaks if key scoring skills regress below field average.";

    const fieldSize = (payload.players || []).length;
    const tier = p.tier || "—";
    const isT1orT2 = tier === "T1" || tier === "T2";

    // T3–T5 cards use canonical event-brief fields where present, displayed as
    // reduced-detail rather than Tier 1/2 full-card detail. The schema formally
    // designates player briefs for T1/T2, but the JSON provides structural fields
    // across the full field; the "limited player brief" label reflects that
    // distinction, not the absence of brief data.
    const structuralCase = brief
      ? (brief.why_it_fits_structurally || brief.exact_mechanism || "")
      : "";
    const riskCondition = brief
      ? (brief.named_failure_condition || brief.key_risk_vector || "")
      : "";

    const antiPatternFlags = (p.anti_pattern_flags || []);

    const input = {
      schema_version: "1.0",
      event: {
        event_id:   "pga_rocket_classic_2026",
        event_name: "Rocket Classic",
        venue_id:   "detroit_golf_club",
        venue_name: "Detroit Golf Club",
      },
      player: {
        player_id:    String(p.player_id),
        display_name: p.player_name,
      },
      projection: {
        vts:                 Number(p.vts_final ?? 0),
        vts_rank:            p.rank,
        field_size:          fieldSize,
        tier,
        tier_rank:           p.rank,
        conviction:          convictionLabel(p.data_depth),
        confidence_label:    convictionLabel(p.data_depth),
        neutral_skill:       p.neutralSkillIndex,
        venue_fit_delta:     p.delta_fit,
        venue_history_delta: p.ch_adjustment,
        penalty_total:       0,
      },
      traits,
      badges:             validateEmittedBadges(p.badges || [], S.badgePolicy),
      anti_pattern_flags: antiPatternFlags,
      risk_factors: weaknesses.map((w, i) => ({
        risk_id:           `risk_${i}`,
        evidence_trait_id: w.trait_id,
        label:             w.label,
        severity:          "medium",
        description:       w.statement,
      })),
    };

    const narrative = {
      player_id:       String(p.player_id),
      event_id:        "pga_rocket_classic_2026",
      schema_version:  "1.0",
      headline:        p.headline || `${p.player_name} — ${tier}`,
      story_hook:      p.win_case || "",   // retained for synthetic fixture fallback
      structural_case: structuralCase,     // from player brief
      risk_condition:  riskCondition,      // from player brief
      has_full_brief:  isT1orT2 && !!brief,
      venue_fit: {
        text:      (p.strength_tags || []).filter((t) => !SKIP_TAGS.includes(t)).slice(0, 2).join(" • ") || "See scouting report.",
        trait_ids: strengths.map((s) => s.trait_id).filter(Boolean),
      },
      strengths,
      weaknesses,
      failure_scenario: failureText,
      projection_explainer: {
        text: `VTS ${Number(p.vts_final ?? 0).toFixed(1)} — ${tier} projection. `
            + `${(p.strength_tags || []).filter((t) => !SKIP_TAGS.includes(t)).slice(0, 2).join("; ") || "See full scouting report."}`,
        reason_codes:  [],
        component_ids: ["neutral_skill", "venue_fit_delta"],
      },
      form_note:          formNote,
      venue_history_note: venueHistNote,
      quality: {
        evidence_coverage:   p.data_depth === "FULL" ? "high" : "medium",
        needs_editor_review: false,
        validation_errors:   [],
      },
    };

    return { input, narrative };
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
      title="${esc(badgeObj.qualification_reason || def.description)}">
      ${esc(def.icon || "")} ${esc(def.label)}
    </span>`;
  }

  // ── Filter sidebar ────────────────────────────────────────────────────────────

  function renderBadgeFilters() {
    const DISABLED_HTML = `
      <div class="badge-unavailable-state" role="status">
        <div class="badge-unavailable-label">Playstyle badges unavailable for this event build</div>
        <div class="badge-unavailable-detail">Badge qualification was not emitted in the frozen event artifact; filters are disabled rather than inferred in-browser.</div>
        <button class="badge-glossary-link" data-glossary-open="true" type="button">What are playstyle badges?</button>
      </div>
    `;

    const presentIds = new Set();
    S.fixtures.forEach((f) => { (f.input.badges || []).forEach((b) => presentIds.add(b.badge_id)); });

    if (presentIds.size === 0) {
      ["badge-filter-list", "badge-filter-list-popover", "badge-filter-list-overlay"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = DISABLED_HTML;
      });
      return;
    }

    const badgeDefs = (S.badgePolicy?.badges || []).filter((b) => presentIds.has(b.badge_id));
    const checkboxHtml = badgeDefs.map((def) => `
      <label class="badge-filter-item">
        <input type="checkbox" class="badge-filter-checkbox" data-badge-id="${esc(def.badge_id)}" />
        <span class="badge-filter-label">${esc(def.icon || "")} ${esc(def.label)}</span>
      </label>
    `).join("");

    ["badge-filter-list", "badge-filter-list-popover", "badge-filter-list-overlay"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = checkboxHtml;
      el.querySelectorAll(".badge-filter-checkbox").forEach((cb) => {
        cb.addEventListener("change", () => {
          S.activeFilters.badges = [...new Set(
            [...document.querySelectorAll(".badge-filter-checkbox:checked")].map((c) => c.dataset.badgeId)
          )];
          renderRoster();
        });
      });
    });
  }

  function renderTraitSliders() {
    const CONTAINER_IDS = [
      "trait-slider-list",
      "trait-slider-list-popover",
      "trait-slider-list-overlay",
    ];

    if (S.fixtures.length === 0) {
      CONTAINER_IDS.forEach((cid) => {
        const el = document.getElementById(cid);
        if (el) el.innerHTML = "";
      });
      return;
    }

    const seen = new Map();
    S.fixtures.forEach((f) => {
      (f.input.traits || []).forEach((t) => {
        if (FILTER_ELIGIBLE_TRAITS.has(t.trait_id) && !seen.has(t.trait_id)) {
          seen.set(t.trait_id, t.label);
        }
      });
    });

    const buildSliderHtml = (tid, label) => {
      const [lo, hi] = S.activeFilters.traitRanges[tid] || [0, 100];
      return `
        <div class="trait-slider-item" data-trait-id="${esc(tid)}">
          <div class="trait-slider-label">
            <span>${esc(label)}</span>
            <span class="trait-slider-range-label" data-trait-range-label="${esc(tid)}">${lo} – ${hi}</span>
          </div>
          <div style="display:flex; gap:6px; align-items:center;">
            <input type="range" class="trait-slider"
              data-trait-id="${esc(tid)}" data-end="lo"
              min="0" max="100" value="${lo}" step="1" />
            <input type="range" class="trait-slider"
              data-trait-id="${esc(tid)}" data-end="hi"
              min="0" max="100" value="${hi}" step="1" />
          </div>
        </div>`;
    };

    const slidersHtml = seen.size > 0
      ? [...seen.entries()].map(([tid, label]) => buildSliderHtml(tid, label)).join("")
      : "";

    CONTAINER_IDS.forEach((cid) => {
      const el = document.getElementById(cid);
      if (!el) return;
      el.innerHTML = slidersHtml;
      el.querySelectorAll("input.trait-slider").forEach((slider) => {
        slider.addEventListener("input", onTraitSliderInput);
      });
    });
  }

  function onTraitSliderInput() {
    const tid = this.dataset.traitId;
    const item = this.closest(".trait-slider-item");
    const lo = parseInt(item.querySelector('[data-end="lo"]').value, 10);
    const hi = parseInt(item.querySelector('[data-end="hi"]').value, 10);
    if (lo === 0 && hi === 100) {
      delete S.activeFilters.traitRanges[tid];
    } else {
      S.activeFilters.traitRanges[tid] = [lo, hi];
    }
    syncTraitSliderDisplay(tid, lo, hi);
    renderRoster();
  }

  function syncTraitSliderDisplay(tid, lo, hi) {
    document.querySelectorAll(`[data-trait-range-label="${CSS.escape(tid)}"]`).forEach((el) => {
      el.textContent = `${lo} – ${hi}`;
    });
    document.querySelectorAll(`input.trait-slider[data-trait-id="${CSS.escape(tid)}"][data-end="lo"]`).forEach((sl) => {
      if (parseInt(sl.value, 10) !== lo) sl.value = String(lo);
    });
    document.querySelectorAll(`input.trait-slider[data-trait-id="${CSS.escape(tid)}"][data-end="hi"]`).forEach((sl) => {
      if (parseInt(sl.value, 10) !== hi) sl.value = String(hi);
    });
  }

  function updateFilterCount() {
    const visible = filteredFixtures().length;
    const total   = S.fixtures.length;
    const html = `Showing <strong>${visible}</strong> of <strong>${total}</strong> players`;
    const el  = document.getElementById("filter-count");
    if (el) el.innerHTML = html;
    const elP = document.getElementById("filter-count-popover");
    if (elP) elP.innerHTML = html;

    const activeCount =
      (S.activeFilters.tier !== "All" ? 1 : 0) +
      S.activeFilters.badges.length +
      Object.keys(S.activeFilters.traitRanges).length;
    const railBadge = document.getElementById("rail-active-count");
    if (railBadge) railBadge.textContent = activeCount > 0 ? String(activeCount) : "";
  }

  function filteredFixtures() {
    return S.fixtures.filter((f) => {
      const inp  = f.input;
      const tier = inp.projection.tier;

      if (S.activeFilters.tier !== "All" && tier !== S.activeFilters.tier) return false;

      if (S.activeFilters.query) {
        const name = (inp.player.display_name || "").toLowerCase();
        if (!name.includes(S.activeFilters.query)) return false;
      }

      if (S.activeFilters.badges.length > 0) {
        const playerBadgeIds = (inp.badges || []).map((b) => b.badge_id);
        if (!S.activeFilters.badges.some((bid) => playerBadgeIds.includes(bid))) return false;
      }

      const ranges = S.activeFilters.traitRanges;
      if (Object.keys(ranges).length > 0) {
        const traitMap = {};
        (inp.traits || []).forEach((t) => { traitMap[t.trait_id] = t.score; });
        for (const [tid, [lo, hi]] of Object.entries(ranges)) {
          const score = traitMap[tid];
          if (score == null) return false;
          if (score < lo || score > hi) return false;
        }
      }

      return true;
    });
  }

  // ── Reset filters ─────────────────────────────────────────────────────────────

  function resetFilters() {
    S.activeFilters.tier = "All";
    S.activeFilters.badges = [];
    S.activeFilters.traitRanges = {};
    S.activeFilters.query = "";
    const searchEl = document.getElementById("player-search");
    if (searchEl) searchEl.value = "";
    document.querySelectorAll(".badge-filter-checkbox").forEach((cb) => { cb.checked = false; });

    document.querySelectorAll(".tier-chip").forEach((c) => {
      c.classList.toggle("active", c.dataset.tier === "All");
    });

    document.querySelectorAll("input.trait-slider").forEach((slider) => {
      slider.value = slider.dataset.end === "lo" ? "0" : "100";
    });
    document.querySelectorAll(".trait-slider-range-label").forEach((el) => {
      el.textContent = "0 – 100";
    });

    renderRoster();
  }

  // ── Tier chip bindings ────────────────────────────────────────────────────────

  function bindTierChips() {
    document.querySelectorAll(".tier-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const tier = chip.dataset.tier;
        document.querySelectorAll(".tier-chip").forEach((c) => {
          c.classList.toggle("active", c.dataset.tier === tier);
        });
        S.activeFilters.tier = tier;
        renderRoster();
      });
    });
  }

  // ── Roster rendering ──────────────────────────────────────────────────────────

  function renderRoster() {
    const tbody = document.getElementById("roster-tbody");
    if (!tbody) return;

    const visible = filteredFixtures();

    if (S.openPlayerId) {
      if (!visible.some((f) => f.input.player.player_id === S.openPlayerId)) {
        closeDrawer();
      }
    }

    tbody.innerHTML = visible.map((f) => {
      const inp  = f.input;
      const pid  = inp.player.player_id;
      const name = inp.player.display_name;
      const tier = inp.projection.tier;
      const vts  = inp.projection.vts.toFixed(1);
      const conv = inp.projection.conviction;
      const badges = (inp.badges || []).map(renderBadgePill).join("");
      const hasAntiPattern = (inp.anti_pattern_flags || []).length > 0;

      const badgeCell = badges
        ? `<div class="badge-row">${badges}${hasAntiPattern ? '<span class="roster-anti-pattern" title="Anti-pattern flag — see player detail">⚠</span>' : ""}</div>`
        : `<div class="badge-row">${hasAntiPattern ? '<span class="roster-anti-pattern" title="Anti-pattern flag — see player detail">⚠</span>' : ""}</div>`;

      return `<tr class="roster-row" data-player-id="${esc(pid)}" tabindex="0" role="button" aria-label="View ${esc(name)}">
        <td><span class="player-name">${esc(name)}</span></td>
        <td><span class="vts-score">${esc(vts)}</span></td>
        <td><span class="tier-pill tier-${esc(tier)}">${esc(tier)}</span></td>
        <td><span style="font-size:12px; color:var(--color-text-muted);">${esc(conv)}</span></td>
        <td>${badgeCell}</td>
        <td><button class="open-btn" data-player-id="${esc(pid)}">View ›</button></td>
      </tr>`;
    }).join("");

    if (visible.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="roster-empty">
        No players match these filters.
        <button class="roster-reset-link" type="button">Reset Filters</button>
      </td></tr>`;
      const resetLink = tbody.querySelector(".roster-reset-link");
      if (resetLink) resetLink.addEventListener("click", resetFilters);
    }

    tbody.querySelectorAll(".roster-row").forEach((row) => {
      row.addEventListener("click", () => openDrawer(row.dataset.playerId));
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDrawer(row.dataset.playerId); }
      });
    });

    updateFilterCount();
  }

  // ── Venue Traits panel ────────────────────────────────────────────────────────

  function renderVenueTraits(traits) {
    if (!traits || traits.length === 0) return "";

    const scoringTraits = traits.filter((t) => !t.venue_history_context);
    const hasHistoryTraits = traits.some((t) => t.venue_history_context);

    const rows = scoringTraits.map((t) => {
      const score    = Number(t.score ?? 0);
      const weightPct = Math.round((t.weight || 0) * 100);
      const weightLabel = weightPct > 0
        ? `<span class="venue-trait-weight">${weightPct}%&thinsp;wt</span>`
        : `<span class="venue-trait-weight zero-wt">monitor</span>`;

      let evClass = "ev-derived";
      let evLabel = "Derived";
      if (t.evidence_status === "MEASURED")   { evClass = "ev-measured";   evLabel = "Measured"; }
      if (t.evidence_status === "UNAVAILABLE") { evClass = "ev-unavailable"; evLabel = "Unavailable"; }

      const barFill = t.evidence_status === "UNAVAILABLE"
        ? `<div class="trait-bar-fill bar-unavailable" style="width:${score.toFixed(1)}%"></div>`
        : `<div class="trait-bar-fill" style="width:${score.toFixed(1)}%"></div>`;

      return `<div class="venue-trait-row">
        <div class="venue-trait-header">
          <span class="venue-trait-label">${esc(t.label)}</span>
          ${weightLabel}
          <span class="venue-trait-ev ${esc(evClass)}">${esc(evLabel)}</span>
        </div>
        <div class="venue-trait-bar-row">
          <div class="trait-bar-bg">${barFill}</div>
          <span class="trait-bar-score">${score.toFixed(0)}</span>
        </div>
      </div>`;
    }).join("");

    const histNote = hasHistoryTraits
      ? `<div class="venue-trait-history-note">Course History excluded — venue-history context only. See Venue History section below.</div>`
      : "";

    return `<details class="venue-traits-panel">
      <summary class="venue-traits-summary">
        Venue traits <span class="venue-traits-count">(${scoringTraits.length} scored)</span>
      </summary>
      <div class="venue-traits-scale-note">VenueDNA trait component score (0–100) — higher values indicate stronger alignment on each individual scored trait. This is a pre-composite input; tier and rank reflect the full model including penalties and gates.</div>
      ${rows}
      ${histNote}
    </details>`;
  }

  // ── Drawer ─────────────────────────────────────────────────────────────────────

  function findFixture(playerId) {
    return S.fixtures.find((f) => f.input.player.player_id === playerId) || null;
  }

  function openDrawer(playerId) {
    const fixture = findFixture(playerId);
    if (!fixture) return;

    S.openPlayerId = playerId;

    document.querySelectorAll(".roster-row").forEach((r) => r.classList.remove("active"));
    const activeRow = document.querySelector(`.roster-row[data-player-id="${CSS.escape(playerId)}"]`);
    if (activeRow) activeRow.classList.add("active");

    renderDrawer(fixture.input, fixture.narrative);
    injectLiveSummaryIntoDrawer(playerId);

    const drawer = document.getElementById("player-drawer");
    drawer.classList.add("open");

    const backdrop = document.getElementById("overlay-backdrop");
    if (backdrop) backdrop.classList.add("active");

    const roster = document.getElementById("roster-panel");
    if (roster && window.innerWidth >= 1280) {
      roster.style.opacity = "0.45";
      roster.style.transition = "opacity 0.25s";
      roster.style.pointerEvents = "auto";
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
    if (roster) { roster.style.opacity = ""; roster.style.pointerEvents = ""; }
  }

  function renderDrawer(inputObj, narrativeObj) {
    const drawerInner = document.getElementById("drawer-inner");
    if (!drawerInner) return;

    const validationErrors = narrativeObj.quality?.validation_errors || [];
    const evidenceCoverage = narrativeObj.quality?.evidence_coverage || "high";

    // ── Structural validation failure ────────────────────────────────────────
    if (validationErrors.length > 0) {
      drawerInner.innerHTML = `
        <div class="drawer-close">
          <span style="font-size:13px; color:var(--color-text-muted);">${esc(inputObj.player.display_name)}</span>
          <button onclick="window.__harness.closeDrawer()" aria-label="Close">✕ Close</button>
        </div>
        <div class="narrative-unavailable">
          <strong>Narrative unavailable — structural validation failed</strong>
          ${validationErrors.length} validation error(s) blocked narrative generation.
          Player scoring data is available; prose content has been suppressed.
        </div>`;
      return;
    }

    // ── Evidence coverage banner ─────────────────────────────────────────────
    const evidenceBanner = evidenceCoverage !== "high"
      ? `<div class="evidence-banner low" role="status">⚠ Limited evidence — ${esc(evidenceCoverage)} confidence</div>`
      : "";

    // ── Badges: no active badges for this build ──────────────────────────────
    const badgePills = (inputObj.badges || []).map(renderBadgePill).join(" ");
    const badgesSection = badgePills
      ? `<div class="drawer-badges">${badgePills}</div>`
      : `<div class="drawer-badges-empty" role="status">
          No active playstyle badges were emitted for this player.
          <button class="inline-glossary-link" data-glossary-open="true" type="button">About badges</button>
        </div>`;

    // ── Anti-pattern flags ───────────────────────────────────────────────────
    const antiPatterns = inputObj.anti_pattern_flags || [];
    const antiPatternHtml = antiPatterns.length > 0
      ? `<div class="anti-pattern-section">
          <div class="drawer-section-label">Anti-Pattern Flags</div>
          ${antiPatterns.map((ap) => `
            <div class="anti-pattern-card">
              <span class="anti-pattern-icon" aria-hidden="true">⚠</span>
              <span>${esc(ap)}</span>
            </div>`).join("")}
        </div>`
      : "";

    // ── Structural Case ──────────────────────────────────────────────────────
    const tier = inputObj.projection.tier;
    const isT1orT2 = tier === "T1" || tier === "T2";
    const structuralText = narrativeObj.structural_case || narrativeObj.venue_fit?.text || "";
    const structuralLabel = isT1orT2 ? "Structural Case" : "Structural Case — limited player brief";
    const structuralFallbackNote = !isT1orT2 && structuralText
      ? `<div class="brief-fallback-note">Generated from the canonical event payload; a full Tier 1/2 brief was not available.</div>`
      : "";

    // ── Risk / Failure Condition ─────────────────────────────────────────────
    const riskText = narrativeObj.risk_condition || narrativeObj.failure_scenario || "";

    // ── Strengths ────────────────────────────────────────────────────────────
    const strengthsHtml = (narrativeObj.strengths || []).map((s) => {
      const traitData = (inputObj.traits || []).find((t) => t.trait_id === s.trait_id);
      const score = traitData ? traitData.score : null;
      const barHtml = score !== null
        ? `<div class="trait-bar-wrap">
            <div class="trait-bar-bg"><div class="trait-bar-fill" style="width:${score.toFixed(1)}%"></div></div>
            <span class="trait-bar-score">${score.toFixed(0)}</span>
          </div>`
        : "";
      return `<div class="strength-card">
        <div class="card-label">${esc(s.label)}</div>
        <div class="card-statement">${esc(s.statement)}</div>
        ${barHtml}
      </div>`;
    }).join("") || `<div class="drawer-prose no-content">No strength tags available.</div>`;

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
    }).join("") || `<div class="drawer-prose no-content">No structural risks identified.</div>`;

    drawerInner.innerHTML = `
      <div class="drawer-close">
        <span style="font-size:13px; color:var(--color-text-muted);">
          ${esc(inputObj.player.display_name)}
          <span class="tier-pill tier-${esc(tier)}" style="margin-left:6px;">${esc(tier)}</span>
        </span>
        <button onclick="window.__harness.closeDrawer()" aria-label="Close">✕ Close</button>
      </div>

      ${evidenceBanner}

      <div class="drawer-headline">${esc(narrativeObj.headline)}</div>

      ${badgesSection}

      ${antiPatternHtml}

      <div class="drawer-section">
        <div class="drawer-section-label">${esc(structuralLabel)}</div>
        ${structuralFallbackNote}
        <div class="drawer-prose">${esc(structuralText)}</div>
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

      <div class="drawer-section">
        <div class="drawer-section-label">Risk / Failure Condition</div>
        <div class="scenario-block failure">
          <div class="scenario-tag fail">Risk</div>
          ${esc(riskText)}
        </div>
      </div>

      <div class="drawer-divider"></div>

      ${renderVenueTraits(inputObj.traits)}

      <div class="drawer-divider"></div>

      <div class="drawer-section">
        <div class="drawer-section-label">Projection</div>
        <div class="drawer-prose">${esc(narrativeObj.projection_explainer?.text || "")}</div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Form</div>
        <div class="drawer-prose">${esc(narrativeObj.form_note || "")}</div>
      </div>

      <div class="drawer-section">
        <div class="drawer-section-label">Venue History</div>
        <div class="drawer-prose">${esc(narrativeObj.venue_history_note || "")}</div>
      </div>

      <div class="drawer-divider"></div>

      ${renderDetroitFit(inputObj.player.player_id)}
    `;

    // Bind inline glossary links injected into drawer HTML
    drawerInner.querySelectorAll("[data-glossary-open]").forEach((btn) => {
      btn.addEventListener("click", openGlossary);
    });
  }

  // ── Glossary ──────────────────────────────────────────────────────────────────

  function openGlossary() {
    const dialog = document.getElementById("glossary-dialog");
    if (dialog) dialog.showModal();
  }

  function closeGlossary() {
    const dialog = document.getElementById("glossary-dialog");
    if (dialog) dialog.close();
  }

  // ── Live R2 diagnostic layer ─────────────────────────────────────────────────
  //
  // Read-only overlay consuming data/2026_rocket_classic_r2_live.json. All tags,
  // buckets, and mechanism leaders are pre-computed by build_live_r2.py — nothing
  // here re-derives model logic, it only formats and renders what the builder emitted.
  // Never mutates S.fixtures / the pre-event payload.

  const NAME_TOKEN_RE = /[A-Za-z]+/g;
  const SUFFIX_TOKENS = new Set(["jr", "sr", "ii", "iii", "iv", "v"]);

  const TAG_LABELS = {
    structurally_live:    "Structurally Live",
    surviving_short_game: "Surviving on Short Game",
    fragile_survivor:     "Fragile Survivor",
    model_vindication:    "Model Vindication",
    model_miss_watch:     "Model Miss Watch",
  };
  const TAG_CHIP_CLASS = {
    structurally_live:    "chip-live",
    surviving_short_game: "chip-neutral",
    fragile_survivor:     "chip-danger",
    model_vindication:    "chip-success",
    model_miss_watch:     "chip-warning",
  };
  const BUCKET_LABELS = { promotion_watch: "Promotion Watch", hold: "Hold", downgrade_watch: "Downgrade Watch" };
  const BUCKET_CHIP_CLASS = { promotion_watch: "chip-success", hold: "chip-neutral", downgrade_watch: "chip-danger" };

  // Mirrors build_live_r2.py's normalize_name(): sorted alpha-token key, order-
  // and format-invariant across "Last, First" / "First Last" sources.
  function clientNameKey(raw) {
    const tokens = (String(raw || "").match(NAME_TOKEN_RE) || [])
      .map((t) => t.toLowerCase())
      .filter((t) => !SUFFIX_TOKENS.has(t));
    tokens.sort();
    return tokens.join("|");
  }

  function fmtScore(n) {
    if (n == null) return "—";
    const v = Math.round(n);
    if (v === 0) return "E";
    return v > 0 ? `+${v}` : String(v);
  }

  function fmtSigned(n) {
    if (n == null) return "—";
    const v = Number(n);
    return `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
  }

  function renderTagChips(tags) {
    return (tags || [])
      .map((t) => `<span class="live-chip ${TAG_CHIP_CLASS[t] || "chip-neutral"}">${esc(TAG_LABELS[t] || t)}</span>`)
      .join("");
  }

  function indexLiveData() {
    S.liveKeyToPlayerId = {};
    S.playerIdToLiveKey = {};
    S.fixtures.forEach((f) => {
      const key = clientNameKey(f.input.player.display_name);
      S.liveKeyToPlayerId[key] = f.input.player.player_id;
      S.playerIdToLiveKey[f.input.player.player_id] = key;
    });
    S.survivorsByKey = {};
    (S.liveData.cut_survivors || []).forEach((r) => { S.survivorsByKey[r.player_key] = r; });
  }

  function setView(view) {
    if (view === "live" && !S.liveAvailable) return;
    S.currentView = view;

    const layout = document.querySelector(".harness-layout");
    if (layout) layout.classList.toggle("view-live", view === "live");

    const preBtn  = document.getElementById("view-toggle-preevent");
    const liveBtn = document.getElementById("view-toggle-live");
    if (preBtn) {
      preBtn.classList.toggle("active", view === "pre-event");
      preBtn.setAttribute("aria-selected", String(view === "pre-event"));
    }
    if (liveBtn) {
      liveBtn.classList.toggle("active", view === "live");
      liveBtn.setAttribute("aria-selected", String(view === "live"));
    }

    if (S.openPlayerId) closeDrawer();
    const filterPopover = document.getElementById("filter-popover");
    const filterOverlay = document.getElementById("filter-overlay");
    if (filterPopover) filterPopover.classList.remove("open");
    if (filterOverlay) filterOverlay.classList.remove("open");

    const livePanel = document.getElementById("live-panel");
    if (livePanel) livePanel.hidden = view !== "live";

    if (view === "live" && !S.liveRendered) renderLivePanel();
  }

  function bindViewToggle() {
    document.querySelectorAll(".view-toggle-btn").forEach((btn) => {
      btn.addEventListener("click", () => setView(btn.dataset.view));
    });
  }

  function openLiveDrawer(playerKey) {
    const playerId = S.liveKeyToPlayerId[playerKey];
    if (!playerId) return; // no matching pre-event fixture for this player — nothing to open
    openDrawer(playerId);
  }

  function injectLiveSummaryIntoDrawer(playerId) {
    if (!S.liveAvailable) return;
    const drawerInner = document.getElementById("drawer-inner");
    if (!drawerInner) return;

    const key = S.playerIdToLiveKey[playerId];
    const rec = key ? S.survivorsByKey[key] : null;
    if (!rec) return;

    const closeRow = drawerInner.querySelector(".drawer-close");
    if (!closeRow) return;

    const tags = S.liveData.venue_mechanism_tags[key] || [];
    const block = document.createElement("div");
    block.className = "live-drawer-block";
    block.innerHTML = `
      <div class="live-drawer-block-title">Live R2 Snapshot — diagnostic, not an official rerank</div>
      <div>LB Pos <strong>${esc(rec.lb_pos_display)}</strong> · Total ${fmtScore(rec.total)} (R1 ${rec.r1 ?? "—"} / R2 ${rec.r2 ?? "—"})</div>
      ${rec.r3_teetime ? `<div>R3 tee: ${esc(rec.r3_teetime)} (${esc(rec.r3_wave || "—")})</div>` : ""}
      <div style="margin-top:6px;">${tags.length ? renderTagChips(tags) : '<span class="live-chip chip-neutral">unclassified</span>'}</div>
    `;
    closeRow.insertAdjacentElement("afterend", block);
  }

  function renderLiveSummary() {
    const ls = S.liveData.live_state;
    const genDate = ls.generated_at ? new Date(ls.generated_at) : null;
    const genLabel = genDate && !isNaN(genDate) ? genDate.toLocaleString() : (ls.generated_at || "—");

    return `
      <div class="live-audit-banner">
        <strong>Diagnostic overlay — not an official rerank.</strong>
        The pre-tournament VenueDNA model remains the canonical baseline; this view is observational and forward-looking only.
        Generated ${esc(genLabel)} · iteration <code>${esc(ls.event_iteration)}</code>.
      </div>
      <div class="live-section">
        <div class="live-section-title">Live State — Through Round ${esc(ls.through_round)}</div>
        <div class="live-stat-row">
          <div class="live-stat-tile"><div class="live-stat-label">Cut Line</div><div class="live-stat-value">${esc(ls.cut_line_display)}</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Made Cut</div><div class="live-stat-value">${esc(ls.players_through)}</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Missed Cut</div><div class="live-stat-value">${esc(ls.players_cut)}</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Withdrew</div><div class="live-stat-value">${esc(ls.players_wd)}</div></div>
        </div>
      </div>
    `;
  }

  function renderCutSurvivorsSection() {
    const rows = [...(S.liveData.cut_survivors || [])].sort(
      (a, b) => (a.lb_pos_numeric ?? 999) - (b.lb_pos_numeric ?? 999)
    );

    const body = rows.map((r) => {
      const tags = S.liveData.venue_mechanism_tags[r.player_key] || [];
      const matched = !!S.liveKeyToPlayerId[r.player_key];
      const deltaLabel = r.rank_delta == null ? "—" : (r.rank_delta > 0 ? `+${r.rank_delta}` : String(r.rank_delta));
      return `<tr data-player-key="${esc(r.player_key)}" data-matched="${matched}" tabindex="0" role="button" aria-label="View ${esc(r.player_name)}">
        <td>${esc(r.lb_pos_display)}</td>
        <td>${esc(r.player_name)}</td>
        <td>${fmtScore(r.total)}</td>
        <td>${r.r1 ?? "—"}</td>
        <td>${r.r2 ?? "—"}</td>
        <td>${r.model_rank ?? "—"}</td>
        <td>${r.model_tier ? `<span class="tier-pill tier-${esc(r.model_tier)}">${esc(r.model_tier)}</span>` : "—"}</td>
        <td>${deltaLabel}</td>
        <td>${r.r3_teetime ? esc(r.r3_teetime) : "—"}</td>
        <td>${r.r3_wave ? esc(r.r3_wave) : "—"}</td>
        <td>${tags.length ? renderTagChips(tags) : '<span class="live-chip chip-neutral">unclassified</span>'}</td>
      </tr>`;
    }).join("");

    return `
      <div class="live-section">
        <div class="live-section-title">Weekend Field <span class="live-section-sub">${rows.length} survivors — LB Pos is leaderboard standing, not VenueDNA rank</span></div>
        <div class="live-table-wrap">
          <table class="live-table">
            <thead><tr>
              <th>LB Pos</th><th>Player</th><th>Total</th><th>R1</th><th>R2</th>
              <th>Model Rank</th><th>Tier</th><th>Δ vs Model</th><th>R3 Tee</th><th>Wave</th><th>Diagnostic</th>
            </tr></thead>
            <tbody>${body || '<tr><td colspan="11" class="live-empty-state">No survivor data.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  function renderDiagnosticBucketsSection() {
    const buckets = S.liveData.diagnostic_buckets || {};
    const order = ["promotion_watch", "hold", "downgrade_watch"];

    const cards = order.map((b) => {
      const keys = buckets[b] || [];
      const rowsHtml = keys.map((k) => {
        const rec = S.survivorsByKey[k];
        if (!rec) return "";
        const tags = S.liveData.venue_mechanism_tags[k] || [];
        const primaryTag = tags[0];
        return `<div class="live-bucket-row" data-player-key="${esc(k)}" tabindex="0" role="button" aria-label="View ${esc(rec.player_name)}">
          <span>${esc(rec.lb_pos_display)} ${esc(rec.player_name)}</span>
          ${primaryTag ? `<span class="live-chip ${TAG_CHIP_CLASS[primaryTag] || "chip-neutral"}">${esc(TAG_LABELS[primaryTag] || primaryTag)}</span>` : ""}
        </div>`;
      }).join("") || `<div class="live-bucket-empty">None</div>`;

      return `<div class="live-bucket-card bucket-${b}">
        <div class="live-bucket-header"><span>${BUCKET_LABELS[b]}</span><span class="live-bucket-count">${keys.length}</span></div>
        ${rowsHtml}
      </div>`;
    }).join("");

    return `
      <div class="live-section">
        <div class="live-section-title">Diagnostic Buckets <span class="live-section-sub">live lens — not an official rerank</span></div>
        <div class="live-bucket-grid">${cards}</div>
      </div>
    `;
  }

  function renderMechanismLeadersSection() {
    const ml = S.liveData.mechanism_leaders || {};
    const metrics = [
      ["sg_total", "SG Total"], ["sg_ott", "SG OTT"], ["sg_app", "SG APP"],
      ["sg_arg", "SG ARG"], ["sg_putt", "SG PUTT"],
    ];

    const cards = metrics.map(([key, label]) => {
      const rows = (ml[key] || []).map((r) => `
        <div class="live-mech-row" data-player-key="${esc(r.player_key)}" tabindex="0" role="button" aria-label="View ${esc(r.player_name)}">
          <span>${esc(r.lb_pos_display)} ${esc(r.player_name)}</span>
          <span class="live-mech-value">${fmtSigned(r.value)}</span>
        </div>`).join("") || `<div class="live-bucket-empty">No data</div>`;
      return `<div class="live-mech-card"><div class="live-mech-title">${esc(label)}</div>${rows}</div>`;
    }).join("");

    return `
      <div class="live-section">
        <div class="live-section-title">Mechanism Leaders <span class="live-section-sub">two-round SG, cut survivors only</span></div>
        <div class="live-mech-grid">${cards}</div>
      </div>
    `;
  }

  function renderCourseObservationsSection() {
    const co = S.liveData.course_observations || {};
    const holesByNum = {};
    (co.holes || []).forEach((h) => { holesByNum[h.hole] = h; });

    const group = (label, nums, extra) => {
      const chips = (nums || []).map((n) => {
        const h = holesByNum[n];
        const detail = h ? `Par ${h.par} · ${extra(h)}` : "";
        return `<span class="live-hole-chip">Hole ${esc(n)}${detail ? ` — ${esc(detail)}` : ""}</span>`;
      }).join("");
      return `<div class="live-course-card"><div class="live-course-title">${esc(label)}</div>${chips || '<span class="live-empty-state">—</span>'}</div>`;
    };

    return `
      <div class="live-section">
        <div class="live-section-title">Course Through 2 Rounds — Detroit Golf Club</div>
        <div class="live-course-grid">
          ${group("Easiest Holes", co.easiest_holes, (h) => `${h.plus_minus > 0 ? "+" : ""}${h.plus_minus}`)}
          ${group("Hardest Holes", co.hardest_holes, (h) => `${h.plus_minus > 0 ? "+" : ""}${h.plus_minus}`)}
          ${group("Birdie-Heavy", co.birdie_heavy, (h) => `${h.birdies} birdies`)}
          ${group("Danger Holes", co.danger_holes, (h) => `${h.dbl_plus} dbl+`)}
        </div>
      </div>
    `;
  }

  function renderWeatherSection() {
    const w = S.liveData.round3_weather || {};
    let body;

    if (w.parse_status === "parsed") {
      const riskClass = w.risk_label === "low" ? "chip-success" : w.risk_label === "moderate" ? "chip-warning" : "chip-danger";
      body = `
        <div class="live-weather-stats">
          <div class="live-stat-tile"><div class="live-stat-label">Temp Range</div><div class="live-stat-value">${w.temp_range_f[0]}–${w.temp_range_f[1]}°F</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Wind Range</div><div class="live-stat-value">${w.wind_range_mph[0]}–${w.wind_range_mph[1]} mph</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Max Precip</div><div class="live-stat-value">${w.max_precip_pct}%</div></div>
          <div class="live-stat-tile"><div class="live-stat-label">Risk</div><div class="live-stat-value"><span class="live-chip ${riskClass}">${esc(w.risk_label)}</span></div></div>
        </div>
        <div class="live-weather-note">
          ${w.tee_time_window_summary ? `Tee window: ${esc(w.tee_time_window_summary)}<br>` : ""}
          Early (6–10 AM): ${esc(w.early_window_summary || "—")}<br>
          Late (11 AM–5 PM): ${esc(w.late_window_summary || "—")}
        </div>`;
    } else {
      body = `
        <div class="live-weather-note">Hourly forecast could not be reliably parsed — showing source text as-is.</div>
        <div class="live-weather-raw">${esc(w.raw_text || "No weather data available.")}</div>`;
    }

    return `
      <div class="live-section">
        <div class="live-section-title">R3 Weather — Detroit Golf Club</div>
        <div class="live-weather-card">${body}</div>
      </div>
    `;
  }

  function renderMatchIssuesSection() {
    const issues = S.liveData.match_issues || [];
    const rows = issues.slice(0, 20).map((i) => `
      <div class="live-issue-row">
        <strong>${esc(i.source_file)}</strong> — ${esc(i.raw_name)} <span class="live-section-sub">(${esc(i.reason)})</span>
      </div>`).join("") || `<div class="live-issue-row">No unresolved match issues.</div>`;

    return `
      <div class="live-section">
        <div class="live-section-title">Data Notes <span class="live-section-sub">${issues.length} match issue(s) logged</span></div>
        <div class="live-issues-list">${rows}</div>
      </div>
    `;
  }

  function renderLivePanel() {
    const panel = document.getElementById("live-panel");
    if (!panel || !S.liveData) return;

    panel.innerHTML = [
      renderLiveSummary(),
      renderCutSurvivorsSection(),
      renderDiagnosticBucketsSection(),
      renderMechanismLeadersSection(),
      renderCourseObservationsSection(),
      renderWeatherSection(),
      renderMatchIssuesSection(),
    ].join("");

    panel.querySelectorAll("[data-player-key]").forEach((el) => {
      el.addEventListener("click", () => openLiveDrawer(el.dataset.playerKey));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openLiveDrawer(el.dataset.playerKey); }
      });
    });

    S.liveRendered = true;
  }

  // ── Global events ─────────────────────────────────────────────────────────────

  function bindGlobalEvents() {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        const dialog = document.getElementById("glossary-dialog");
        if (dialog && dialog.open) return; // native dialog handles its own Escape
        if (S.openPlayerId) closeDrawer();
      }
    });

    const rosterPanel = document.getElementById("roster-panel");
    if (rosterPanel) {
      rosterPanel.addEventListener("click", (e) => {
        if (S.openPlayerId && !e.target.closest(".roster-row")) closeDrawer();
      });
    }

    const backdrop = document.getElementById("overlay-backdrop");
    if (backdrop) backdrop.addEventListener("click", () => closeDrawer());

    const filterToggle  = document.getElementById("filter-toggle-btn");
    const filterPopover = document.getElementById("filter-popover");
    const filterOverlay = document.getElementById("filter-overlay");

    if (filterToggle) {
      filterToggle.addEventListener("click", () => {
        if (filterPopover) filterPopover.classList.toggle("open");
        if (filterOverlay) filterOverlay.classList.toggle("open");
      });
    }

    // Rail button (900–1279px)
    const railBtn = document.getElementById("filter-rail-btn");
    if (railBtn && filterPopover) {
      railBtn.addEventListener("click", () => {
        const isOpen = filterPopover.classList.toggle("open");
        railBtn.setAttribute("aria-expanded", String(isOpen));
      });
    }

    // Glossary triggers (sidebar badge state + header button)
    document.querySelectorAll("[data-glossary-open]").forEach((btn) => {
      btn.addEventListener("click", openGlossary);
    });

    const glossaryClose = document.getElementById("glossary-close");
    if (glossaryClose) glossaryClose.addEventListener("click", closeGlossary);

    // Glossary backdrop click
    const glossaryDialog = document.getElementById("glossary-dialog");
    if (glossaryDialog) {
      glossaryDialog.addEventListener("click", (e) => {
        if (e.target === glossaryDialog) closeGlossary();
      });
    }

    // Reset filters
    document.querySelectorAll("[data-reset-filters]").forEach((btn) => {
      btn.addEventListener("click", resetFilters);
    });

    bindTierChips();
    bindViewToggle();

    const searchInput = document.getElementById("player-search");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        S.activeFilters.query = searchInput.value.trim().toLowerCase();
        renderRoster();
      });
    }

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

  // ── Public API ─────────────────────────────────────────────────────────────────

  window.__harness = {
    closeDrawer,
    resetFilters,
    openGlossary,
    closeGlossary,
    getActiveFilters:  () => ({ ...S.activeFilters, badges: [...S.activeFilters.badges] }),
    getOpenPlayerId:   () => S.openPlayerId,
    getFixtureCount:   () => S.fixtures.length,
    getFilteredCount:  () => filteredFixtures().length,
    setView,
    getCurrentView:    () => S.currentView,
    isLiveAvailable:   () => S.liveAvailable,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
