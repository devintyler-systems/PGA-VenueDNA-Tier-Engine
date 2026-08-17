# Codex Handoff — CodeQL Alert #2 Logging Taint Fix

## OBJECTIVE
Resolve the remaining CodeQL alert `py/clear-text-logging-sensitive-data` in `engine/dg_api_harvester.py` by removing the static analyzer's sensitive-data flow from normal request logging.

## ACTIVE EVENT
`NO_ACTIVE_EVENT` | Venue: N/A | Status source: `config/active_event.json`

This is event-neutral security maintenance. Do not initialize an event or create event-bound artifacts.

## FILES TO INSPECT
- `AGENTS.md`
- `SYSTEM_HANDOFF_SPEC.md`
- `config/active_event.json`
- `engine/dg_api_harvester.py`
- Existing applicable tests under `tests/`, if any

## AUTHORIZED TO MODIFY
- `engine/dg_api_harvester.py`
- A narrowly scoped existing test file under `tests/` only if it can validate this change without introducing unrelated infrastructure

## PROTECTED — DO NOT MODIFY
- `config/active_event.json`
- All `.github/workflows/**`
- All `events/**` and `deploy/data/**`
- Scoring logic, weights, venue intelligence, artifact schemas, database schemas, database files, and `config/db_config.json`
- `.env`, repository secrets, and GitHub settings

## REQUIRED CHANGE
CodeQL flags the normal request log in `_fetch()` because it derives a logged dictionary from `params`, which contains `key: api_key`, even though the comprehension filters that key.

Replace the log construction with safe values that are never derived from the secret-bearing `params` object. Preserve endpoint visibility and optionally report only the sorted names of `extra` parameters. The final log call must not reference `params`, `api_key`, `url`, response objects, or request objects.

Recommended shape:

```python
log.info(
    "GET /%s (file_format=json, extra_params=%s)",
    endpoint,
    sorted((extra or {}).keys()),
)
```

Requirements:
- Do not change `params = {"key": api_key, "file_format": "json", **(extra or {})}`.
- Do not change `_rate_limited_get(url, params)` or HTTP/API behavior.
- Do not log key values, URL values, response bodies, or derived objects containing secrets.
- Preserve the existing sanitized HTTP-error behavior from commit `2d6ffbd`.

## EXPECTED OUTPUT
A minimal patch that removes CodeQL's taint path at the line currently reported as alert #2, with no other functional changes.

## ALLOWED IMPACT
- Scoring: none
- Payload/artifact contracts: none
- Player identity: none
- Deploy: none
- Database: none
- Event state: none
- DataGolf API request behavior: none
- Logging: normal request logging now contains endpoint and non-secret extra parameter names only

## VALIDATION COMMANDS
Run and report exact outputs:

```powershell
python -m compileall engine/dg_api_harvester.py
```

```powershell
python -c "from pathlib import Path; text=Path('engine/dg_api_harvester.py').read_text(encoding='utf-8'); assert 'params.items()' not in text; assert 'extra_params=' in text; print('PASS: normal request log has no params-derived taint path')"
```

If an existing narrowly targeted test exists, run it. Do not call the live DataGolf API.

## STOP CONDITIONS
Stop and report if resolving the alert would require changing authentication, API parameters, API request behavior, error semantics, database behavior, scoring logic, event artifacts, or any protected file.

## REQUIRED FINAL REPORT
1. Files changed.
2. Exact behavior changed.
3. Files intentionally not changed.
4. Validation commands and results.
5. Data-contract impact: explicitly state none.
6. Database migration impact: explicitly state none.
7. Manual deploy/artifact step: explicitly state none.
8. Whether CodeQL has re-run or remains pending.
9. Commit SHA and remote push status.

## COMMIT/PUSH AUTHORIZED
YES. Create one focused commit:

```text
fix: eliminate CodeQL log taint path — security maintenance
```

Do not amend unrelated commits or change files outside this handoff.
