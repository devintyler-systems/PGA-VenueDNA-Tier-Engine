# Codex Handoff — CodeQL Alerts #1 and #2

## OBJECTIVE
Resolve CodeQL alert #1 (workflow missing explicit permissions) and alert #2 (potential clear-text logging of DataGolf API credentials) with the smallest focused patch.

## ACTIVE EVENT
`NO_ACTIVE_EVENT` | Venue: N/A | Status source: `config/active_event.json`

This is event-neutral security maintenance. Do not initialize an event or create event-bound artifacts.

## FILES TO INSPECT
- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `.github/workflows/netlify-deploy-3m-open.yml`
- `engine/dg_api_harvester.py`
- `tests/` for existing harvester or workflow-adjacent tests
- `.github/workflows/codeql.yml` if present, only to identify available validation context; do not modify it

## AUTHORIZED TO MODIFY
- `.github/workflows/netlify-deploy-3m-open.yml`
- `engine/dg_api_harvester.py`
- A narrowly scoped test file under `tests/` only if an existing applicable test location exists and a regression test can be added without unrelated setup

## PROTECTED — DO NOT MODIFY
- `config/active_event.json`
- All `events/**`
- All `deploy/data/**`
- All scoring logic, weights, venue intelligence, artifact schemas, database schemas, and database files
- `config/db_config.json`
- `.env`, secrets, or GitHub repository/environment settings
- Any unrelated workflows, templates, or front-end files

## REQUIRED CHANGES

### Alert #1 — workflow permissions
Add an explicit top-level least-privilege permissions declaration to `.github/workflows/netlify-deploy-3m-open.yml`:

```yaml
permissions:
  contents: read
```

Do not add broader permissions. Preserve existing trigger, concurrency, Netlify token usage, deploy target, and deploy behavior.

### Alert #2 — sensitive logging
In `engine/dg_api_harvester.py`, eliminate any authenticated-request error log path that can expose an API key through a serialized request URL, request parameters, response body, or exception representation.

Requirements:
- Preserve the API request itself: DataGolf key remains supplied as the existing request parameter.
- On HTTP failure, log only non-secret diagnostics sufficient for operations, such as HTTP status and a static/sanitized endpoint identifier.
- Do not log `resp.url`, `resp.request.url`, the `params` dictionary, API key, or raw `resp.text` in the error path.
- Preserve exception behavior (`raise`) and all API, cache, SQLite, identity, and scoring behavior.
- Normal success logging must remain redacted; do not introduce any new secret-bearing diagnostic.

## EXPECTED OUTPUT
- Focused source patch resolving CodeQL alerts #1 and #2.
- Optional focused regression test only if supported by the existing test structure.
- No event artifact, scoring artifact, deploy payload, schema migration, or database artifact.

## ALLOWED IMPACT
- Scoring: none
- Payload/artifact contracts: none
- Player identity: none
- Deploy behavior: no functional change; workflow token scope is narrowed to `contents: read`
- Database: none
- Event state: none
- External API behavior: unchanged except sensitive error details are no longer logged

## VALIDATION COMMANDS
Run the narrowest available validation and report exact results:

```powershell
python -m compileall engine/dg_api_harvester.py
```

```powershell
python -c "from pathlib import Path; text=Path('engine/dg_api_harvester.py').read_text(encoding='utf-8'); assert 'body: %s' not in text; print('PASS: sensitive response-body logging removed')"
```

```powershell
python -c "from pathlib import Path; text=Path('.github/workflows/netlify-deploy-3m-open.yml').read_text(encoding='utf-8'); assert 'permissions:' in text and 'contents: read' in text; print('PASS: least-privilege workflow permissions present')"
```

If an existing targeted harvester test is identified, run it. Do not fabricate a broad test command or run the harvester against the live DataGolf API.

## STOP CONDITIONS
Stop and report without making broader changes if:
- The desired patch requires changing the DataGolf authentication method, configuration, database schema, scoring logic, an event artifact, or deploy payload.
- Existing local worktree changes conflict with either authorized file.
- A relevant test reveals an unrelated failure that cannot be isolated to this patch.
- The security alert’s actual data flow materially differs from this handoff’s inspected code.

## REQUIRED FINAL REPORT
Return:
1. Files changed.
2. Exact behavior changed.
3. Files intentionally not changed.
4. Validation commands and results.
5. Data-contract impact: explicitly state none.
6. Database migration impact: explicitly state none.
7. Manual deploy/artifact step: explicitly state none.
8. Whether CodeQL has been re-run by GitHub or remains pending after push.
9. Commit SHA and remote push status.

## COMMIT/PUSH AUTHORIZED
YES. Create one focused commit:

```text
fix: remediate CodeQL alerts #1 and #2 — security maintenance
```

Do not amend unrelated commits. Do not create a branch unless the local repository policy requires it; if a branch is required, report the branch name and open a pull request rather than merging automatically.
