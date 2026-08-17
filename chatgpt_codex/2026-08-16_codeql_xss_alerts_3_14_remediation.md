# Codex Handoff — CodeQL XSS Alerts #3–#14 Remediation

## OBJECTIVE
Remediate the remaining 12 high-severity CodeQL findings on `main`:
- `js/xss-through-dom` / DOM text reinterpreted as HTML: alerts #3–#9
- `js/incomplete-sanitization` / incomplete string escaping or encoding: alerts #10–#14

Use one consistent, context-correct output-encoding strategy. Preserve each board's behavior, payload contract, and visual output.

## ACTIVE EVENT
`NO_ACTIVE_EVENT` | Venue: N/A | Status source: `config/active_event.json`

This is event-neutral security maintenance. Do not initialize an event or create event-bound artifacts. Archived boards are in scope only because CodeQL reports the alerts there.

## FILES TO INSPECT
- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `library/ui_templates/template_app.js`
- `events/2026_Finished_Events/2026_3m_open/deploy/app.js`
- `events/2026_Finished_Events/2026_the_open_championship/deploy/app.js`
- `events/2026_Finished_Events/2026_USOPEN/deploy/2026_usopen_vts_dashboard_STANDALONE.html`
- Each file's related `deploy/index.html` and `deploy/styles.css` only for compatibility inspection; do not modify unless an explicit safety-critical requirement makes that unavoidable and report before doing so
- All payload files fetched by each affected board, for read-only contract inspection only
- Existing test/fixture/browser validation tooling relevant to these boards

## ALERT-TO-FILE SCOPE
- #3, #10, #11: `events/2026_Finished_Events/2026_3m_open/deploy/app.js`
- #4, #5, #6, #7: `events/2026_Finished_Events/2026_USOPEN/deploy/2026_usopen_vts_dashboard_STANDALONE.html`
- #8, #12: `events/2026_Finished_Events/2026_the_open_championship/deploy/app.js`
- #9, #13, #14: `library/ui_templates/template_app.js`

Confirm exact alert locations in the GitHub Security UI or by local CodeQL SARIF/result data if available before changing code. If the live code differs materially from this mapping, stop and report the discrepancy.

## AUTHORIZED TO MODIFY
- `library/ui_templates/template_app.js`
- `events/2026_Finished_Events/2026_3m_open/deploy/app.js`
- `events/2026_Finished_Events/2026_the_open_championship/deploy/app.js`
- `events/2026_Finished_Events/2026_USOPEN/deploy/2026_usopen_vts_dashboard_STANDALONE.html`
- A narrowly scoped existing test or fixture file only if required to demonstrate encoding behavior without changing payloads or contracts

## PROTECTED — DO NOT MODIFY
- `config/active_event.json`
- All event `output/**`, `input/**`, and `deploy/data/**` artifacts
- Any JSON or CSV payload
- All scoring logic, model weights, player facts, venue intelligence, artifact schemas, databases, database schemas, and identity contracts
- `.github/workflows/**`, `engine/**`, and `config/**`
- Fetch URLs, payload filenames, and API/data contracts
- Any non-listed archived board or unrelated template

## REQUIRED SECURITY STANDARD

### 1. Treat all runtime payload-derived values as untrusted
This includes player names, ranks, tiers, flags, badges, narrative briefs, reasons, labels, tag text, tooltips, diagnostics, weather/context strings, and values pulled from JSON/CSV/fetch responses. Static source literals and deliberately constructed markup structure may remain HTML.

### 2. Apply context-correct encoding at every HTML sink
Where existing render methods use `innerHTML`, template literals, `insertAdjacentHTML`, or equivalent:
- Escape every dynamic interpolation for HTML text context.
- Escape every dynamic interpolation used in quoted HTML attribute context, including `data-*`, `title`, `aria-*`, `id`, `class`, and inline-style values when derived from data.
- Do not rely on partial escape functions, blacklist filters, string replacements limited to `<`/`>`, or an assumption that operator-produced JSON is trusted.
- Do not use a sanitizer that requires adding an unapproved dependency.

Preferred approach:
- Use `textContent`, `setAttribute`, `dataset`, and DOM construction for dynamic text/attributes where a focused change is practical.
- Where the mature board's renderer must retain an `innerHTML` template, define or strengthen one central `esc()`/`escapeHtml()` helper in that file to escape at minimum `&`, `<`, `>`, `"`, and `'`; then apply it to every data-derived interpolation in the relevant sink.
- Preserve escaping for static CSS variable values only when they are genuinely static source mappings; do not incorrectly alter working layout or styles.

Suggested helper implementation:

```js
function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
```

If a file already has an escaping helper, inspect it first. Do not create duplicate helpers or shadow an existing canonical helper. Strengthen the existing helper if required.

### 3. Fix flows, not just lines
CodeQL may track a payload value through helper functions. Trace each flagged source-to-sink flow and repair the actual unsafe interpolation. Do not only suppress alerts, add a comment, change variable names, or insert a CodeQL exclusion.

### 4. Preserve product behavior
- No changes to model rankings, tiers, probabilities, player facts, analytics, scoring, scenario calculations, fetch targets, payload shapes, or archived data.
- Do not convert static UI markup wholesale or redesign boards.
- Preserve click handlers, player drawer/modal behavior, filtering, charts, accessibility semantics, and mobile behavior.
- Do not make any event active or alter archived-event status.

## IMPLEMENTATION PLAN — MAXIMUM FIVE BULLETS
Before editing, state in the final report (or local task log):
1. The exact sinks and data flows found for each affected file.
2. The existing escaping/DOM-construction mechanisms in each file.
3. The smallest safe change per file.
4. The validation method for rendering and hostile-string handling.
5. Any unresolved false-positive rationale, if applicable.

## REQUIRED VALIDATION
Run the narrowest relevant checks available and report exact commands/results. At minimum:

```powershell
node --check library/ui_templates/template_app.js
node --check events/2026_Finished_Events/2026_3m_open/deploy/app.js
node --check events/2026_Finished_Events/2026_the_open_championship/deploy/app.js
```

For the standalone U.S. Open HTML file, use the repository's available HTML/JS validation or a deterministic extraction/syntax check. Do not claim browser validation unless it actually ran.

Perform a deterministic hostile-string regression for each changed renderer or helper, using values containing at minimum:

```text
<svg/onload=alert(1)>
" autofocus onfocus=alert(1) x="
' onclick='alert(1)
& < > " '
```

The result must render those sequences as literal text/attribute values and must not create executable elements, handlers, or attribute escapes.

If a fixture harness/browser test exists, run it against each affected board at least once. Validate all existing fetch targets remain unchanged. Test at 375px and 1440px only if a local browser workflow is already available; do not introduce a new browser-test stack for this patch.

Do not run or depend on live DataGolf/API calls.

## STOP CONDITIONS
Stop and report before changing anything further if:
- A reported alert requires a payload change, generated deploy-data rewrite, scoring/identity change, workflow modification, or event-state change.
- An affected file has no reliable distinction between static markup and dynamic data and a secure change would require a UI rewrite.
- A shared template change would require automatically regenerating archived deploy files not listed as authorized.
- The existing runtime/fixture environment cannot validate a change and the risk cannot be deterministically assessed from source.
- CodeQL reports a source/sink outside the four authorized files.

## EXPECTED OUTPUT
- A focused code patch limited to the four authorized front-end/template files (plus only an essential narrow test if one exists).
- All 12 existing alerts remediated in source without CodeQL suppressions.
- No generated payload/artifact changes.

## ALLOWED IMPACT
- Scoring: none
- Payload/data contract: none
- Player identity: none
- Database: none
- Event state: none
- Deploy rendering: security-only output encoding changes; no intended visual or functional change
- Archived boards: security-only rendering changes to alert-bearing source files

## REQUIRED FINAL REPORT
1. Implementation plan (five bullets or fewer).
2. Files changed and exact alert IDs addressed per file.
3. Each source-to-sink remediation and encoding strategy used.
4. Files intentionally not changed.
5. Validation commands and exact results, including hostile-string regression evidence.
6. Data-contract impact: explicitly state none.
7. Database migration impact: explicitly state none.
8. Manual deploy/artifact step: explicitly state none, or name any archived board redeploy required.
9. Any remaining open CodeQL alerts and rationale.
10. Commit SHA, remote push status, and whether CodeQL is pending.

## COMMIT/PUSH AUTHORIZED
YES. Create one focused commit:

```text
fix: remediate CodeQL XSS alerts #3–#14
```

Do not amend unrelated commits. Do not create a branch unless repository policy requires it; if a branch is required, report the branch name and open a pull request rather than merging automatically.
