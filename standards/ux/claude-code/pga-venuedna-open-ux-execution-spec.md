# PGA VenueDNA Open UX Execution Spec

Version: 2026-07-18
Event context: 2026 Open Championship at Royal Birkdale
Purpose: convert the current static event app into an auditable, venue-native, interactive decision tool without contaminating the core model layer.

## Operating constraints

- Core projection logic remains upstream in source data artifacts, not in the browser.[file:21][file:22]
- Deploy package should stay static-site friendly: `index.html`, `styles.css`, `app.js`, and data payload files.[file:21]
- Any UX feature must preserve traceability between NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, tiers, and probabilities.[file:22]
- Derivative UX layers must not rewrite or obscure canonical model outputs.[file:22]
- Event-specific outputs should continue to conform to the deploy package structure in the artifact schema.[file:21]
- Sandbox deploys cannot rely on `localStorage`; ephemeral in-memory state is the safe default.[cite:1]

## Product decision

Use **Claude Code**, not Codex, as the execution agent for the next build cycle. Claude Code is the right fit here because the work is mostly refactor-heavy UI engineering, file-structure discipline, and controlled feature layering around an already opinionated data model.[cite:1]

## Build priorities

### Phase 1 — highest ROI, lowest dependency risk

1. Audit flag tooltip system
2. Fuzzy player and tag search
3. Mobile responsive overhaul
4. Player-card VTS sparklines
5. NSI vs VFS contention map
6. Scenario builder with model-lock state

### Phase 2 — live operations layer

1. Live scoreboard polling + rerank delta layer
2. Wave draw simulator
3. Watchlist and trigger alerts using in-memory session state
4. Natural-language query over structured local data filters

## Feature decisions

### 1. Audit flag tooltip system

Ship first. The artifact schema already expects anti-pattern flags, penalties, trigger traces, and related metadata in the scored field output, so the UI can expose this without changing scoring logic.[file:21]

Implementation:
- Hover and tap tooltip on every flag badge
- Show flag code, rule name, penalty magnitude, and trigger trace when present
- Use severity tint based on penalty magnitude only, not brand color guesswork
- On mobile, use click-to-pin tooltip drawer rather than hover-only behavior

Needs in payload:
- `antipatternflags`
- `antipatternpenaltytotal`
- `antipatterntriggertrace`
- optional human-readable glossary map

### 2. Fuzzy search and structured filters

Ship early because it improves navigation across a dense ranked field without changing model outputs. Search should work across player name, country, tier, flag, driver trait, risk tags, and probability bands.

Implementation:
- Fuse.js fuzzy search on client
- Structured chips for Tier, Flags, Win%, Make Cut%, Driver Trait, Debut, Risk
- Keyboard-first command bar pattern on desktop
- Results update the same canonical table and card views, not a separate derived ranking

### 3. Mobile responsive overhaul

This is mandatory, not optional. The current artifact schema explicitly supports a deployable static app, so the interface must survive phone usage during live rounds and sportsbook usage windows.[file:21]

Implementation:
- Replace wide-table-first view with responsive mode switching
- Desktop: sticky header + sortable table + side panel modal
- Mobile: stacked player cards, swipe-safe horizontal tier rail, collapsible conditions bar
- Keep one source of truth for row/card rendering to avoid rank mismatch

### 4. VTS sparkline history

Add as a read-only support signal, not as an input explanation shortcut. It should show trajectory, but the UI copy must not imply that trend replaces venue-fit logic.

Implementation:
- Mini inline sparkline using Chart.js or SVG path
- Use last 6 to 8 modeled events from existing historical or trend files when available
- Highlight current event point distinctly
- Tooltip should show event label and VTS value

### 5. Contention map

This should become the main visual summary for Tier 1 and Tier 2 interpretation. It is the cleanest way to expose the relationship between baseline strength and venue fit without collapsing the model into one fuzzy score, which the compact instructions explicitly prohibit.[file:22]

Implementation:
- X axis: NeutralSkill index or NSI proxy
- Y axis: VenueFit score or VFS proxy
- Bubble size: Win%
- Color: tier
- Click bubble to open player modal
- Toggle to highlight anti-pattern flags or debut status

### 6. Scenario builder

Build, but fence it hard. The official model output and user-adjusted view must never be visually conflated.

Implementation:
- Sliders for trait-weight families only
- Two states: `Official Model` and `Scenario Mode`
- Reset button restores canonical weights instantly
- Re-ranked scenario table must display `Unofficial user scenario` label persistently
- No overwriting of payload data files; scenario calculations remain client-side only

Guardrails:
- Lock non-user-editable penalty rules by default
- Show changed weights vs default
- Keep exported scenario results visually separate from canonical rankings

### 7. Live reranking

Add only after Phase 1 stabilizes. The artifact schema already defines live update artifacts such as round diagnostics and snapshot files, which means live UX should map to those concepts rather than invent a parallel system.[file:21]

Implementation:
- Poll leaderboard endpoint on interval
- Join live scores to canonical player IDs/names
- Render rank delta vs pre-tourney model rank
- Show `hold`, `promote`, `downgrade` candidate states as diagnostics, not automatic truth
- Preserve a frozen pre-event column for auditability

### 8. Wave draw simulator

Valuable because the week already has tee-time data and venue-specific wave effects. But this is a calculation tool layered on top of context, not a reason to mutate core pre-tournament rankings.

Implementation:
- Input player + round + wave assumption
- Apply course- and condition-specific adjustment model
- Output adjusted expected strokes and relative movement band
- Mark output as conditional estimate only

### 9. Watchlist and alerts

Do not use browser storage in the Space deploy context. Use in-memory state and optionally a downloadable JSON import/export later if persistence becomes necessary.[cite:1]

Implementation:
- Star players within current session
- Trigger toasts for rank-delta, flag-clear, flag-add, and tee-time wave change events
- Filter board to watched players only

### 10. Ask the Model

Do not start with an LLM-backed chat widget. Start with a deterministic natural-language parser over the local data model.

Implementation:
- Parse intents like `tier 2 without flags`, `win pct above 3`, `debut links specialists`, `show all R4 penalties`
- Map tokens to field names and filters
- Return filtered rows, not generated prose
- Only later add an external model layer if needed for summarization

Reason:
- Faster
- Cheaper
- No auth burden
- Fully auditable
- No risk of hallucinating unsupported player claims

## Data contract additions

Extend the event payload for UI richness while keeping scoring source-of-truth in canonical artifacts.[file:21]

Recommended additions:
- `uiGlossary.flags`
- `uiGlossary.traits`
- `playerTags`
- `driverTrait`
- `nsi`
- `vfs`
- `vhd`
- `vtsHistory[]`
- `liveStatus`
- `rankDelta`
- `watchEligible`
- `scenarioEligibleTraits[]`

## Front-end architecture

### Recommended structure

- `index.html` — app shell and semantic containers
- `styles.css` — tokens, table/card layouts, tooltip styles, responsive states
- `app.js` — bootstrap, store, render pipeline, event bus
- `data/eventpayload.json` — primary app payload
- `data/vtsfull.csv` — canonical field ranking data
- `data/playerbriefs.json` — player card content
- `data/links.json` — external references

This mirrors the deploy package expected by the artifact schema.[file:21]

### JavaScript modules inside app.js

Keep as logical sections if not splitting files:
- data loader
- store/state
- search and filter engine
- render table/cards
- tooltip system
- chart layer
- scenario engine
- live update adapter
- diagnostics logger

## UX guardrails

- Never let user scenarios replace official model outputs by default.
- Never let live-score movement hide pre-event thesis.
- Never use DFS, odds, or popularity to alter canonical rank display in the core model view.[file:22]
- Every visual shortcut must still expose structural reason, risk, and penalty trace where relevant.[file:22]
- If a chart can be interpreted as a rank, it must link back to the same underlying player record.

## First sprint definition

Build this first sprint in order:

1. Tooltip flag explainer
2. Fuzzy search + filter chips
3. Responsive board/card mode
4. Contention bubble chart
5. Player sparkline history
6. Scenario builder shell with official/scenario toggle

Definition of done:
- No scoring logic moved into presentation layer
- Mobile view is usable at 390px width
- Canonical ranks match source files across all UI views
- Flags, penalties, and risk traces are inspectable
- Scenario mode is visually fenced from official model mode
- All new features operate from existing data artifacts or explicit additive payload fields
