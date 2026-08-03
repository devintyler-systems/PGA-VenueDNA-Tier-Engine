# 3M Open 2026 Board — Bug Ticket Pack

Date: 2026-07-26
Artifact: VenueDNA — 3M Open 2026 board
URL: https://2026-3m-open.netlify.app/2026_3m_open_board.html

## Scope
This ticket pack converts the latest QA review into dev-ready issues with reproduction steps, expected behavior, actual behavior, suspected root cause, and acceptance criteria. The board should now treat Rd 3 and Rd 4 as active supported surfaces, not placeholders.

---

## P0-01 — Tier Intelligence click opens wrong player card

**Severity:** P0  
**Area:** Tier Intelligence → player card modal  
**Status:** Open  
**Tag:** `identity-resolution` `modal` `player_id`

### Reproduction
1. Open the 3M Open 2026 board.
2. Go to the main board area and locate the **Tier Intelligence** section.
3. Click a known top player card such as Scottie Scheffler.
4. Observe the modal header, tier, pre-tournament status, trait profile, and odds fields.

### Actual
- The modal can open the wrong player context.
- Example behavior reported and previously reproduced: Scheffler resolves as a Tier 5 / no pre-tournament data / alternate-style fallback profile instead of his real record.
- Trait and scoring sections then inherit fallback or mismatched data.

### Expected
- Clicking a player in Tier Intelligence must open that exact player's modal.
- Name, tier, VTS, win probability, trait profile, and briefing must all belong to the clicked player.

### Suspected root cause
A shared modal resolver is not binding strictly to canonical `player_id`, or is receiving stale/incorrect keys from Tier Intelligence cards and falling into a default fallback profile.

### Engineering notes
- Audit click handler payload on Tier Intelligence cards.
- Verify DOM data attributes carry canonical `player_id` only.
- Remove any fallback resolution order that prefers name strings over `player_id`.
- Log a hard integrity error in QA if modal hydration cannot resolve a valid player object.

### Acceptance criteria
- Clicking 10 sampled players across T1-T5 opens the correct player card every time.
- Modal identity fields match source card identity for all samples.
- No known player can render the alternate/debut fallback card from Tier Intelligence.

---

## P0-02 — Round table click opens wrong player card

**Severity:** P0  
**Area:** Rd 1 / Rd 2 / Rd 3 / R4 Final tables → player card modal  
**Status:** Open  
**Tag:** `identity-resolution` `round-context` `modal`

### Reproduction
1. Open the board.
2. Navigate to **Rd 1**.
3. Scroll to the lower leaderboard/table area.
4. Click a player such as Scottie Scheffler or Ben Kohles.
5. Repeat the same check on **Rd 2**, **Rd 3**, and **R4 Final**.

### Actual
- The modal can open a mismatched player card.
- Reported examples include Ben Kohles and Scottie Scheffler showing Tier 5 / no pre-tourney data / no tier scoring.
- Baseline traits, odds, and status fields can be replaced by fallback values rather than real player data.

### Expected
- Any player clicked from any round table opens the exact same identity baseline used pre-tournament, plus only the correct round-context live deltas.

### Suspected root cause
Round rows are likely passing a non-canonical identifier or partial row object into the modal open function, causing the baseline hydration path to fail and fall back to default alternate/debut card state.

### Engineering notes
- Compare payloads passed from pre-tournament rows vs round rows.
- Confirm all round tables pass only canonical `player_id` and selected round context.
- Decouple modal baseline lookup from round stat lookup so identity is resolved first, then round data is layered in.

### Acceptance criteria
- For one top-tier, one mid-tier, and one bottom-tier player, modal identity and pre-tournament baseline remain identical no matter whether opened from Pre-Tournament, Tier Intelligence, Rd 1, Rd 2, Rd 3, or R4 Final.
- Only round-specific fields change by tab context.

---

## P0-03 — Known-player lookup failures silently render alternate/debut fallback card

**Severity:** P0  
**Area:** Modal fallback behavior  
**Status:** Open  
**Tag:** `fallback` `error-handling` `integrity`

### Reproduction
1. Trigger a player-card lookup from any known broken surface.
2. Observe whether unresolved identity states render a generic fallback card.

### Actual
- Failed lookups appear to render a plausible but wrong fallback state such as alternate entry, debut profile, no pre-tournament data, default trait scores, and null odds.
- This masks the underlying failure and makes QA harder.

### Expected
- A failed identity lookup should never impersonate a real player profile.
- It should render a clear integrity error state for QA and optionally a clean user-facing unavailable state in production.

### Suspected root cause
Fallback template is acting as a catch-all resolver target rather than a narrowly gated template for true alternates/debuts.

### Engineering notes
- Gate fallback rendering to explicitly flagged alternates only.
- Add an integrity assertion: if clicked row contains a player present in canonical field registry but modal cannot hydrate, raise a visible QA error.
- Record unresolved `player_id` and source surface in console logs or a debug badge.

### Acceptance criteria
- Known players never render alternate/debut fallback unless event data explicitly marks them as such.
- Failed lookups surface as an explicit error state in QA mode.

---

## P1-01 — Tee-Times section is round-state broken

**Severity:** P1  
**Area:** Tee-Times section  
**Status:** Open  
**Tag:** `state-management` `tee-times` `routing`

### Reproduction
1. Open the board.
2. Click the **Tee-Times** tab.
3. Scroll to the tee-time content area.
4. Observe default loaded round.
5. Click **Rd 1**, **Rd 2**, and other round selectors inside Tee-Times.

### Actual
- Tee-Times defaults to showing Rd 3 only.
- Selecting other rounds does not show tee times for those rounds.
- Instead, the panel swaps to post-day recap content.

### Expected
- Each round selector in Tee-Times should display that round's tee sheet if available.
- If a round has no tee-time data, show an explicit unavailable-state card.
- Tee-Times should never swap into recap content.

### Suspected root cause
Tee-Times view state is coupled to the general round recap controller, so round switches are routed to recap payloads instead of tee-time datasets.

### Engineering notes
- Give Tee-Times its own internal controller and dataset map by round.
- Separate `selectedBoardRound` from `selectedTeeTimeRound`.
- Add a defensive render guard so missing tee-time datasets cannot fall through to recap components.

### Acceptance criteria
- Rd 1 selector shows Rd 1 tee times or explicit unavailable state.
- Rd 2 selector shows Rd 2 tee times or explicit unavailable state.
- Rd 3 selector shows Rd 3 tee times.
- No round selection inside Tee-Times can render recap content.

---

## P1-02 — Round-status labels may not reflect tournament state cleanly

**Severity:** P1  
**Area:** Round labels / status badges  
**Status:** Open  
**Tag:** `status-labels` `ux-copy`

### Reproduction
1. Review round tabs and any in-panel round labels after round completion.
2. Compare displayed labels to actual tournament state.

### Actual
- Prior review found labels such as “R1 Live” persisting after round completion.
- User flagged this as incorrect.

### Expected
- Completed round: “Final” or equivalent locked-state label.
- Current in-progress round: “Live”.
- Future round: “Pending” or equivalent.

### Suspected root cause
Round labels are hardcoded or not driven by a single event-status state object.

### Engineering notes
- Centralize status mapping in one event state helper.
- Prevent per-component hardcoded label strings.

### Acceptance criteria
- All round labels derive from one canonical event-status source and remain consistent across tabs, headers, and subpanels.

---

## P1-03 — Baseline and live layers are not safely separated in modal rendering

**Severity:** P1  
**Area:** Player card data composition  
**Status:** Open  
**Tag:** `data-composition` `baseline-vs-live`

### Reproduction
1. Open the same player from Pre-Tournament.
2. Open the same player from a round table.
3. Compare identity, baseline tiering, trait profile, odds, and live-round metrics.

### Actual
- Some paths appear to mix baseline briefing text with fallback trait/odds layers.
- The user can see a card that looks partly correct and partly broken.

### Expected
- Modal should render from a canonical baseline object plus a separate round-context overlay.
- If either layer is missing, only that section should fail gracefully; identity must remain correct.

### Suspected root cause
Modal sections are hydrating from separate sources without a strict composition contract.

### Engineering notes
- Define modal schema as:
  - identity
  - baseline projection
  - briefing
  - round overlay
  - availability flags
- Render sections only when their required schema pieces are satisfied.

### Acceptance criteria
- No modal can display mismatched identity and baseline/live sections.
- Missing round data does not overwrite or null out valid baseline data.

---

## P2-01 — Missing-data and error states are not standardized

**Severity:** P2  
**Area:** Shared UI state handling  
**Status:** Open  
**Tag:** `empty-states` `error-states` `consistency`

### Reproduction
1. Navigate across sections with incomplete or missing datasets.
2. Observe how the board responds in each area.

### Actual
- Some areas leak unrelated content.
- Some areas show fallback records.
- Some areas appear blank or misleading rather than intentionally unavailable.

### Expected
- All missing-data states should use one consistent component pattern with:
  - title
  - explanation
  - data status
  - next expected update or reason unavailable

### Suspected root cause
No shared empty/error state component contract exists across board modules.

### Engineering notes
- Implement a reusable empty/error-state component.
- Require all sections to explicitly choose between `loaded`, `loading`, `empty`, `error`, and `unavailable`.

### Acceptance criteria
- No blank panels, no hidden fallthroughs, no unrelated content leakage when datasets are absent.

---

## Regression checklist

Run after every deploy:

1. **Identity regression**
   - Click same player from Pre-Tournament, Tier Intelligence, Rd 1, Rd 2, Rd 3, R4 Final.
   - Confirm identical identity and baseline fields.

2. **Tier regression**
   - Sample one player from each tier and confirm clicked card tier equals source surface tier.

3. **Fallback regression**
   - Verify no known player renders alternate/debut fallback card.

4. **Tee-time regression**
   - In Tee-Times, switch every round selector.
   - Confirm no selector routes to recap content.

5. **Status-label regression**
   - Confirm completed rounds show final/complete, active round shows live, future round shows pending.

6. **Schema regression**
   - Brief text, traits, odds, and live metrics must all belong to the same player record.

---

## Engineering recommendation

Do not continue expanding feature surface area until identity resolution and round-state ownership are stable. The board is now at the stage where **interaction trust** is the product: every click must preserve player identity, baseline projection, and round context, or the rest of the VenueDNA layer becomes unauditable.
