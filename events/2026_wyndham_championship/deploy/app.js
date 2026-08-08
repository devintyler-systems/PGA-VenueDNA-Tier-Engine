/**
 * VenueDNA — Wyndham Retrospective Fixture Board Shell
 *
 * RETROSPECTIVE DEVELOPMENT FIXTURE — NOT OFFICIAL — NOT PRE_EVENT — NOT LIVE
 * — NOT DEPLOYABLE
 *
 * This file makes no network requests, reads no browser storage, and reads
 * no query string or external endpoint of any kind. It renders a small,
 * synthetic, in-memory fixture only, to validate scored-vs-UNSCORED
 * board-shell UI behavior for the fenced 2026 Wyndham Championship
 * retrospective fixture. It does not read
 * events/2026_wyndham_championship/deploy/data/, output/, or audit/, all of
 * which remain empty by doctrine. No real player identity, rank, score, or
 * probability appears anywhere in this file.
 */

(function () {
  "use strict";

  // ── Synthetic in-memory fixture ─────────────────────────────────────────
  // All "scored" values below are fabricated for UI validation only and are
  // rendered with an explicit "Synthetic UI fixture values" label. They do
  // not represent any real Wyndham Championship projection.
  var FIXTURE_PLAYERS = [
    { id: "scored-a", name: "Fixture Scored A", status: "scored", rank: 1, tier: "T1", score: 92.7, win: 9.8, top5: 27.4, top10: 41.2, top20: 58.9 },
    { id: "scored-b", name: "Fixture Scored B", status: "scored", rank: 2, tier: "T1", score: 90.1, win: 8.1, top5: 24.6, top10: 38.0, top20: 55.3 },
    { id: "scored-c", name: "Fixture Scored C", status: "scored", rank: 3, tier: "T2", score: 84.3, win: 5.6, top5: 19.2, top10: 31.4, top20: 48.7 },
    { id: "scored-d", name: "Fixture Scored D", status: "scored", rank: 4, tier: "T2", score: 81.6, win: 4.9, top5: 17.5, top10: 28.9, top20: 45.1 },
    { id: "scored-e", name: "Fixture Scored E", status: "scored", rank: 5, tier: "T3", score: 74.2, win: 3.1, top5: 12.8, top10: 22.6, top20: 37.8 },
    { id: "scored-f", name: "Fixture Scored F", status: "scored", rank: 6, tier: "T3", score: 71.8, win: 2.7, top5: 11.3, top10: 20.4, top20: 34.9 },
    { id: "scored-g", name: "Fixture Scored G", status: "scored", rank: 7, tier: "T4", score: 63.5, win: 1.4, top5: 7.2, top10: 14.1, top20: 25.6 },
    { id: "scored-h", name: "Fixture Scored H", status: "scored", rank: 8, tier: "T5", score: 48.9, win: 0.4, top5: 2.9, top10: 6.5, top20: 13.2 },
    {
      id: "unscored-venuefit",
      name: "Fixture Missing VenueFit",
      status: "unscored",
      mechanism: "Missing required VenueFit evidence",
      detail: "All three all-course NeutralSkill horizons present; all three similar-course VenueFit horizons absent."
    },
    {
      id: "unscored-neutralskill",
      name: "Fixture Missing NeutralSkill",
      status: "unscored",
      mechanism: "Missing required NeutralSkill evidence",
      detail: "All three similar-course VenueFit horizons present; all three all-course NeutralSkill horizons absent."
    },
    {
      id: "unscored-mixed-a",
      name: "Fixture Mixed Horizon A",
      status: "unscored",
      mechanism: "Mixed VenueFit horizons — non-computable",
      detail: "L6 and L12 are source-native zero-observation DEBUT rows; L24 carries observed finite similar-course evidence. The fixed three-horizon rule never renormalizes or partially blends across horizons."
    },
    {
      id: "unscored-mixed-b",
      name: "Fixture Mixed Horizon B",
      status: "unscored",
      mechanism: "Mixed VenueFit horizons — non-computable",
      detail: "L6 and L12 are source-native zero-observation DEBUT rows; L24 carries observed finite similar-course evidence. The fixed three-horizon rule never renormalizes or partially blends across horizons."
    }
  ];

  var UNSCORED_ICON =
    '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">' +
    '<path fill="currentColor" d="M11 7h2v7h-2V7Zm0 8.5h2v2h-2v-2ZM12 2 1 21h22L12 2Z"/></svg>';

  function formatPercent(value) {
    return value.toFixed(1) + "%";
  }

  function tierChipClass(tier) {
    return "tier-chip tier-chip-" + tier.toLowerCase();
  }

  function playerRowHtml(player) {
    if (player.status === "unscored") {
      return (
        '<tr class="row-unscored" data-status="unscored">' +
        '<td data-col="rank">—</td>' +
        '<td data-col="player">' +
        "<span class=\"player-name\">" + player.name + "</span>" +
        '<span class="mechanism-chip">' + UNSCORED_ICON + " " + player.mechanism + "</span>" +
        '<span class="mechanism-detail">' + player.detail + "</span>" +
        "</td>" +
        '<td data-col="tier">—</td>' +
        '<td data-col="score">—</td>' +
        '<td data-col="win">—</td>' +
        '<td data-col="top5">—</td>' +
        '<td data-col="top10">—</td>' +
        '<td data-col="top20">—</td>' +
        '<td data-col="status">' +
        '<span class="status-chip status-chip-unscored">' + UNSCORED_ICON + " UNSCORED</span>" +
        '<span class="status-reason">incomplete required evidence</span>' +
        "</td>" +
        "</tr>"
      );
    }

    return (
      '<tr class="row-scored" data-status="scored" data-tier="' + player.tier + '">' +
      '<td data-col="rank">' + player.rank + "</td>" +
      '<td data-col="player">' +
      "<span class=\"player-name\">" + player.name + "</span>" +
      '<span class="badge-synthetic">Synthetic UI fixture values</span>' +
      "</td>" +
      '<td data-col="tier"><span class="' + tierChipClass(player.tier) + '">' + player.tier + "</span></td>" +
      '<td data-col="score">' + player.score.toFixed(1) + "</td>" +
      '<td data-col="win">' + formatPercent(player.win) + "</td>" +
      '<td data-col="top5">' + formatPercent(player.top5) + "</td>" +
      '<td data-col="top10">' + formatPercent(player.top10) + "</td>" +
      '<td data-col="top20">' + formatPercent(player.top20) + "</td>" +
      '<td data-col="status"><span class="status-chip status-chip-scored">Scored</span></td>' +
      "</tr>"
    );
  }

  function filterPlayers(players, filterValue) {
    if (filterValue === "all") {
      return players.slice();
    }
    if (filterValue === "official") {
      return players.filter(function (p) { return p.status === "scored"; });
    }
    if (filterValue === "unscored") {
      return players.filter(function (p) { return p.status === "unscored"; });
    }
    // T1..T5 — official tier filters must only ever include scored records.
    return players.filter(function (p) { return p.status === "scored" && p.tier === filterValue; });
  }

  function sortPlayers(players, sortMode) {
    var scored = players.filter(function (p) { return p.status === "scored"; });
    var unscored = players.filter(function (p) { return p.status === "unscored"; });

    if (sortMode === "score") {
      scored.sort(function (a, b) { return b.score - a.score; });
    } else {
      // "default" and "rank" both order scored records by ascending rank.
      scored.sort(function (a, b) { return a.rank - b.rank; });
    }

    // UNSCORED records always sort after every scored record, under every
    // sort mode, and are never assigned a synthetic rank or score to sort by.
    return scored.concat(unscored);
  }

  function describeView(filterValue, sortMode, visibleCount) {
    var filterLabel = {
      all: "All records",
      official: "Official tiers only",
      unscored: "UNSCORED / incomplete evidence only",
      T1: "Tier T1 only",
      T2: "Tier T2 only",
      T3: "Tier T3 only",
      T4: "Tier T4 only",
      T5: "Tier T5 only"
    }[filterValue] || "All records";

    var sortLabel = {
      default: "default rank order",
      score: "VenueDNA Score, high to low",
      rank: "rank, low to high"
    }[sortMode] || "default rank order";

    return filterLabel + ", sorted by " + sortLabel + " — " + visibleCount + " fixture record" + (visibleCount === 1 ? "" : "s") + " shown.";
  }

  function render() {
    var tierSelect = document.getElementById("tier-select");
    var sortSelect = document.getElementById("sort-select");
    var tbody = document.getElementById("player-tbody");
    var status = document.getElementById("result-status");

    var filterValue = tierSelect.value;
    var sortMode = sortSelect.value;

    var visible = sortPlayers(filterPlayers(FIXTURE_PLAYERS, filterValue), sortMode);

    tbody.innerHTML = visible.map(playerRowHtml).join("");
    status.textContent = describeView(filterValue, sortMode, visible.length);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var tierSelect = document.getElementById("tier-select");
    var sortSelect = document.getElementById("sort-select");

    tierSelect.addEventListener("change", render);
    sortSelect.addEventListener("change", render);

    render();
  });
})();
