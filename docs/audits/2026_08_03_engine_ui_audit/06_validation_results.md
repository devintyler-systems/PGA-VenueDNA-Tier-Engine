# Validation Results

All commands were run read-only on 2026-08-03.

| Command | Exit | Result |
|---|---:|---|
| `python tools/preflight_event.py --phase pre_event` | 1 | Expected gate: `NO_ACTIVE_EVENT` cannot run pre-event validation. |
| `python tools/validate_deploy_contract.py --strict` | 1 | Expected gate: no active deploy root. |
| `pytest tests/test_enrich_cards.py` | 0 | 27 passed. |
| `python -m pytest tests/ -q` | 0 | 117 passed. |
| `node --check events/2026_Finished_Events/2026_rocket_classic/deploy/fixture_harness.js` | 0 | syntax pass. |
| `node --check events/2026_Finished_Events/2026_3m_open/deploy/app.js` | 0 | syntax pass. |
| `node --check events/2026_Finished_Events/2026_the_open_championship/deploy/app.js` | 0 | syntax pass; this is the located Open JavaScript equivalent. |
| `python tools/validate_deploy_contract.py --deploy-root events/2026_Finished_Events/2026_rocket_classic/deploy --strict` | 1 | Missing required `app.js` and `styles.css`; archive is harness-packaged. |
| `python tools/validate_deploy_contract.py --deploy-root events/2026_Finished_Events/2026_3m_open/deploy --strict` | 1 | Undeclared dynamic `url` and `data/r${r}_analysis.json`. |
| `python tools/validate_deploy_contract.py --deploy-root events/2026_Finished_Events/2026_the_open_championship/deploy --strict` | 1 | Undeclared dynamic `data/r${r}_analysis.json`; warning that the inline-styled HTML entry with external `app.js` has no literal stylesheet reference. |

These are historical validation observations only. This documentation-only correction did not exercise or change implementation behavior.

Payload inspection: Rocket (147), 3M (144), and Open (156) all had expected rounded win/top-N field totals and sampled monotonic ordering. This is an invariant check, not calibration evidence. No files outside this audit directory were modified.
