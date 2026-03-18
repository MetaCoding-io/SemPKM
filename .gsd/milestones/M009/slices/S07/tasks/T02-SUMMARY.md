---
id: T02
parent: S07
milestone: M009
provides:
  - AppManager.uninstall() with clean_data parameter for triplestore data cleanup
  - Admin uninstall endpoint accepts clean_data form parameter
key_files:
  - backend/app/apps/manager.py
  - backend/app/apps/admin_router.py
key_decisions:
  - Triplestore cleanup is best-effort (try/except with WARNING log) — uninstall proceeds even if SPARQL queries fail
patterns_established:
  - App data IRI prefix convention: urn:sempkm:app:{app_id}: for both subject and object cleanup
  - App state graph convention: urn:sempkm:app:{app_id}:state
observability_surfaces:
  - INFO log "Cleaning triplestore data for app {app_id}" on start
  - INFO log "Triplestore data cleaned for app {app_id}" on success
  - WARNING log "Failed to clean triplestore data for app {app_id}: {exc}" on failure
  - Admin endpoint logs clean_data value alongside user email
duration: 5min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Implement uninstall data cleanup in AppManager

**Added clean_data parameter to AppManager.uninstall() with three SPARQL cleanup queries and wired it through the admin uninstall endpoint**

## What Happened

Added `clean_data: bool = False` parameter to `AppManager.uninstall()`. When True, executes three SPARQL UPDATE queries before DB row deletion: (1) DELETE triples where subject starts with the app's IRI prefix, (2) DELETE triples where object starts with the app's IRI prefix, (3) CLEAR the app's state graph. All three are best-effort — wrapped in try/except with WARNING-level logging on failure. The admin endpoint at `/admin/apps/{app_id}/uninstall` now accepts `clean_data: bool = Form(False)` and passes it through. `Form` was already imported.

## Verification

All plan-specified checks pass:

- `ast.parse` succeeds on both modified files
- `grep -c "clean_data" manager.py` → 3 (parameter, conditional, log message)
- `grep -c "clean_data" admin_router.py` → 4 (parameter, pass-through, 2× log lines)
- `grep "STRSTARTS" manager.py` → 2 lines (subject + object cleanup)
- `grep "CLEAR GRAPH" manager.py` → 1 line
- Zero conflict markers in apps/ and backend/app/apps/

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/apps/manager.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/apps/admin_router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -c "clean_data" backend/app/apps/manager.py` (≥3) | 0 | ✅ pass (3) | <1s |
| 4 | `grep -c "clean_data" backend/app/apps/admin_router.py` (≥2) | 0 | ✅ pass (4) | <1s |
| 5 | `grep "STRSTARTS" backend/app/apps/manager.py` (2 lines) | 0 | ✅ pass | <1s |
| 6 | `grep "CLEAR GRAPH" backend/app/apps/manager.py` (1 line) | 0 | ✅ pass | <1s |
| 7 | `grep -rn "^<<<<<<< " apps/ backend/app/apps/` | 1 | ✅ pass (0 markers) | <1s |

## Diagnostics

- After uninstall with `clean_data=True`, verify cleanup: `SELECT * WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{app_id}:")) } }` should return zero results
- Check `docker compose logs api | grep "Cleaning triplestore data"` for execution trace
- If cleanup fails, WARNING log appears but uninstall completes — orphaned triples remain

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/manager.py` — Added `clean_data` parameter and SPARQL cleanup block to `uninstall()`
- `backend/app/apps/admin_router.py` — Added `clean_data: bool = Form(False)` parameter to admin uninstall endpoint, updated log message
