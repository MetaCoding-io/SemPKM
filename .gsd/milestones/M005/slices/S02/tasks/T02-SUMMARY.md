---
id: T02
parent: S02
milestone: M005
provides:
  - OperationsLogService wired into FastAPI DI (get_ops_log_service dependency)
  - Fire-and-forget ops log instrumentation at model install/remove, inference run, and validation run
key_files:
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/app/admin/router.py
  - backend/app/inference/router.py
  - backend/app/validation/queue.py
key_decisions:
  - User actor IRI pattern is "urn:sempkm:user:{user.id}" — matches existing user IRI convention
  - ops_log_service passed to AsyncValidationQueue via constructor (optional param, None = no logging) for backwards compat
  - Validation queue uses SYSTEM_ACTOR_IRI string directly ("urn:sempkm:system") rather than importing from ops_log module
patterns_established:
  - Fire-and-forget ops logging pattern: try/except around ops_log.log_activity() with WARNING-level log on failure
  - Router-level instrumentation (D-style): log in the router where user context is available, not in the service
  - Queue-level instrumentation with optional service injection for background workers
observability_surfaces:
  - INFO log "Logged ops activity: {type}" on every successful log_activity() call
  - WARNING log "Failed to write ops log for ..." on triplestore write failure (never blocks primary op)
  - PROV-O activities queryable via SPARQL against urn:sempkm:ops-log named graph
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Wire DI and instrument model/inference/validation

**Wired OperationsLogService into FastAPI DI and added fire-and-forget ops log calls at all four instrumentation points (model install, model remove, inference run, validation run).**

## What Happened

1. **main.py lifespan**: Imported `OperationsLogService`, instantiated with `client`, stored on `app.state.ops_log_service`. Passed `ops_log_service` to `AsyncValidationQueue` constructor.

2. **dependencies.py**: Added `get_ops_log_service()` following the identical pattern of all other DI functions — reads from `request.app.state.ops_log_service`.

3. **admin/router.py**: Added `ops_log` dependency to `admin_models_install()` and `admin_models_remove()`. Both endpoints now log success and failure cases with `activity_type="model.install"` / `"model.remove"`, user IRI as `urn:sempkm:user:{user.id}`, model IRI as `used`, and appropriate status/error_message fields. All wrapped in try/except.

4. **inference/router.py**: Added `ops_log` dependency to `run_inference()`. After inference completes, logs `activity_type="inference.run"` with a label summarizing total inferred and new counts. Wrapped in try/except.

5. **validation/queue.py**: Added optional `ops_log_service` constructor parameter (defaults to None for backwards compat). In `_worker()`, after validation completes and callback fires, logs `activity_type="validation.run"` with `SYSTEM_ACTOR_IRI` as actor and a label summarizing conforms/violations/warnings. Wrapped in try/except.

## Verification

- `grep -rn "ops_log" backend/app/main.py backend/app/dependencies.py backend/app/admin/router.py backend/app/inference/router.py backend/app/validation/queue.py` — all 5 files show ops_log references (17 occurrences)
- All 452 existing unit tests pass: `cd backend && python -m pytest tests/ -v` — 452 passed
- All 5 modified files parse without syntax errors (verified via `ast.parse`)
- No conflict markers in any modified file
- Slice-level check: `grep -rn "ops_log" backend/app/admin/router.py backend/app/inference/router.py backend/app/validation/queue.py` confirms instrumentation wired (passes)

## Diagnostics

- Every `log_activity()` call emits `INFO "Logged ops activity: {type}"` to Python logger
- Failed ops log writes emit `WARNING "Failed to write ops log for ..."` with `exc_info=True`
- All ops log data lives in named graph `urn:sempkm:ops-log` — queryable via SPARQL console
- Primary operations (model install/remove, inference, validation) never blocked by ops log failures

## Deviations

None

## Known Issues

None

## Files Created/Modified

- `backend/app/main.py` — import OperationsLogService, instantiate in lifespan, pass to AsyncValidationQueue
- `backend/app/dependencies.py` — add get_ops_log_service() DI function
- `backend/app/admin/router.py` — add ops_log dependency and fire-and-forget logging to install/remove handlers
- `backend/app/inference/router.py` — add ops_log dependency and fire-and-forget logging after inference run
- `backend/app/validation/queue.py` — accept optional ops_log_service in constructor, log after validation completes
