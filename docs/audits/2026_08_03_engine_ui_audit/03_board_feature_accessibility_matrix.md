# Board Feature and Accessibility Matrix

Scores: 1 absent, 3 usable but incomplete, 5 robust and contract-backed. Source review only; no browser interaction was performed.

| Capability | Rocket harness | 3M board | Open board | Evidence / retained pattern |
|---|---:|---:|---:|---|
| Visual hierarchy / venue identity | 4 | 4 | 4 | Retain event context and dense tier presentation. |
| Search / tier / trait filtering | 5 / 5 / 5 | 4 / 4 / 3 | 5 / 4 / 4 | Rocket `fixture_harness.html:119-164`, `.js:552-610` is strongest filter architecture. |
| Probability / badge / flag filtering | 2 / 2 / 3 | 4 / 3 / 3 | 5 / 3 / 4 | Rocket correctly disables unavailable badges rather than inferring them (`fixture_harness.js:426-454`). |
| Player comparison / biography / official links | 2 / 3 / 2 | 2 / 3 / 2 | 2 / 4 / 2 | No shared player-card contract or documented comparison workflow. |
| Narratives / visualization | 4 / 2 | 4 / 3 | 5 / 4 | Preserve Open’s rich decomposition, but only with canonical provenance. |
| Mobile / keyboard / screen reader | 4 / 4 / 3 | 3 / 3 / 2 | 3 / 2 / 2 | Rocket has responsive filter dialogs and keyboard rows (`fixture_harness.html:54,82,119-144`; `.js:669-690`). Open sort headers use inline click handlers in generated HTML (`open_2026_venuedna.html:711-713`), limiting keyboard semantics. |
| Dialog/drawer / sort semantics | 4 / 3 | 3 / 3 | 3 / 2 | Rocket uses native `<dialog>` for glossary; row-as-button requires focus testing. |
| Pre-event/live separation / scenario fencing | 5 / 4 | 4 / 3 | 4 / 3 | Rocket explicitly labels tabs; preserve it. |
| URL state / shareability | 1 / 1 | 1 / 1 | 1 / 1 | No `URLSearchParams`, history state, or stable player deep link found. |
| Maintainability / payload coupling / event hard-coding / tests | 2 / 2 / 2 / 3 | 2 / 2 / 1 / 2 | 1 / 2 / 1 / 1 | Open generator is explicitly event-specific and embeds data; three board models cannot share validation. |

### Accessibility findings

- **High:** Rocket uses text glyphs/emoji-like symbols for controls (`fixture_harness.html:50,125,185`), contrary to repository UI guidance’s consistent SVG-icon rule.
- **High:** Open’s clickable `<th onclick>` cells are not buttons and lack keyboard activation/ARIA sort state (`open_2026_venuedna.html:711-713`).
- **Medium:** no archive evidence of focus trap/return for custom filter dialogs, reduced-motion checks, automated accessibility tests, or 375/768/1024/1440 executed tests.
- **Medium:** static boards render HTML strings from payload data; maintain a single escaping/sanitization boundary and contract test.

The UI skill was discoverable and read. Its non-persistent audit search recommended a data-dense dashboard and emphasized focus visibility, contrast, reduced motion, and responsive widths. It did not authorize or cause a redesign.
