---
id: T02
parent: S07
milestone: M009
provides:
  - AppManager.uninstall() clean_data parameter — triplestore SPARQL cleanup on uninstall
  - Admin uninstall endpoint accepts clean_data form parameter
key_files:
  - backend/app/apps/manager.py
  - backend/app/apps/admin_router.py
key_decisions:
  - Best-effort triplestore cleanup (try/except) matches existing uninstall error-handling pattern — failures logged at WARNING, never block uninstall
patterns_established:
  - App IRI prefix convention: urn:sempkm:app:{app_id}: used for both subject/object filtering and state graph naming
observability_surfaces:
  - INFO log "Cleaning triplestore data for app %s" + "Triplestore data cleaned for app %s" on success path
  - WARNING log "Failed to clean triplestore data for app %s: %s" on failure path
  - Admin endpoint logs clean_data value alongside user id
duration: 8m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Implement uninstall data cleanup in AppManager

**Added `clean_data` parameter to `AppManager.uninstall()` with three SPARQL cleanup queries, and wired it through the admin uninstall endpoint.**

## What Happened

1. Verified `TriplestoreClient.update(sparql: str)` is the correct async SPARQL UPDATE method (confirmed in `backend/app/triplestore/client.py:47`).
2. Extended `AppManager.uninstall()` with `clean_data: bool = False` parameter. When True, executes three SPARQL queries before DB deletion: DELETE subjects with app IRI prefix, DELETE objects with app IRI prefix, CLEAR app state graph. Wrapped in try/except with WARNING log — best-effort, matching existing uninstall error-handling pattern.
3. Updated `app_uninstall` admin endpoint to accept `clean_data: bool = Form(False)` and pass it through. `Form` was already imported. Log message now includes `clean_data` value.
4. Added Observability Impact section to T02-PLAN.md per pre-flight requirement.

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/apps/manager.py').read())"` — ✅ syntax OK
- `python3 -c "import ast; ast.parse(open('backend/app/apps/admin_router.py').read())"` — ✅ syntax OK
- `grep -c "clean_data" backend/app/apps/manager.py` → 3 (≥3 required) ✅
- `grep -c "clean_data" backend/app/apps/admin_router.py` → 4 (≥2 required) ✅
- `grep "STRSTARTS" backend/app/apps/manager.py` → 2 lines (subject + object) ✅
- `grep "CLEAR GRAPH" backend/app/apps/manager.py` → 1 line ✅
- `grep -rn "^<<<<<<< " apps/ backend/app/apps/` → zero conflict markers ✅
- `parse_app_manifest('../apps/test-app/manifest.yaml')` → manifest validates ✅

### Slice-level verification (partial — intermediate task):
- ✅ `grep -rn "^<<<<<<< " apps/ backend/app/apps/` — zero conflict markers
- ✅ Manifest validates
- ⏳ Remaining checks depend on T03 (E2E tests, Docker stack runtime, pytest suite)

## Diagnostics

- **Logs:** `docker compose logs api 2>&1 | grep "Cleaning triplestore data"` — shows cleanup activity
- **Failure path:** `docker compose logs api 2>&1 | grep "Failed to clean triplestore data"` — shows WARNING if SPARQL cleanup failed
- **SPARQL verification:** After uninstall with clean_data=True, query triplestore: `SELECT * WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{app_id}:")) } }` should return zero results

## Deviations

None — implementation matched the plan exactly. `Form` was already imported in admin_router.py.

## Known Issues

None

## Files Created/Modified

- `backend/app/apps/manager.py` — Added `clean_data` parameter to `uninstall()` with SPARQL triplestore cleanup block
- `backend/app/apps/admin_router.py` — Added `clean_data: bool = Form(False)` to admin uninstall endpoint, updated log message
- `.gsd/milestones/M009/slices/S07/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
