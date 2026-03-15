---
estimated_steps: 5
estimated_files: 5
---

# T02: Wire DI and instrument model/inference/validation

**Slice:** S02 — Operations Log & PROV-O Foundation
**Milestone:** M005

## Description

Wire `OperationsLogService` into the FastAPI dependency injection system and add ops log calls at each of the four instrumentation points. Following the research recommendation (D-style: "log in the router, not the service"), model install/remove and inference are instrumented at the router level where user context is available. Validation is instrumented in the queue worker using `SYSTEM_ACTOR_IRI`.

All ops log calls are fire-and-forget — wrapped in try/except so a triplestore write failure never blocks the primary operation.

## Steps

1. In `backend/app/main.py` lifespan: import `OperationsLogService`, instantiate with `client`, store on `app.state.ops_log_service`
2. In `backend/app/dependencies.py`: add `get_ops_log_service()` dependency function following existing pattern
3. In `backend/app/admin/router.py`: import ops log dependency. In `admin_models_install()`, after the `model_service.install()` call, log activity with `activity_type="model.install"`, user IRI from `user.id`, model IRI as `used`, success/failure status. Same for `admin_models_remove()` with `activity_type="model.remove"`. Wrap in try/except.
4. In `backend/app/inference/router.py`: import ops log dependency. In `run_inference()`, after `service.run_inference()` returns, log activity with `activity_type="inference.run"`, user IRI, and a label summarizing the result counts. Wrap in try/except.
5. In `backend/app/validation/queue.py`: accept `ops_log_service` as optional constructor parameter (None = no logging, for backwards compat). In `_worker()`, after validation completes, call `log_activity()` with `activity_type="validation.run"`, `SYSTEM_ACTOR_IRI` as actor, and a label summarizing conforms/violations/warnings. Update `main.py` to pass the ops_log_service to `AsyncValidationQueue`. Wrap in try/except.

## Must-Haves

- [ ] `OperationsLogService` instantiated in lifespan and stored on `app.state`
- [ ] `get_ops_log_service()` in `dependencies.py`
- [ ] Model install success/failure logged with user IRI and model IRI
- [ ] Model remove success/failure logged with user IRI and model IRI
- [ ] Inference run logged with user IRI and result summary
- [ ] Validation run logged with system actor and result summary
- [ ] All ops log calls wrapped in try/except (never block primary operation)

## Verification

- `grep -rn "ops_log" backend/app/main.py backend/app/dependencies.py backend/app/admin/router.py backend/app/inference/router.py backend/app/validation/queue.py` — all 5 files show ops_log references
- Existing unit tests still pass: `cd backend && python -m pytest tests/ -v`
- No import errors: `cd backend && python -c "from app.services.ops_log import OperationsLogService"`

## Observability Impact

- Signals added: INFO-level log line on every `log_activity()` call; WARNING-level on log failure
- How a future agent inspects this: `grep "ops_log\|Logged ops activity" <docker_logs>` or SPARQL console query against `urn:sempkm:ops-log`
- Failure state exposed: if triplestore is down, WARNING log appears but primary operation still succeeds

## Inputs

- `backend/app/services/ops_log.py` — the service from T01
- `backend/app/main.py` — existing lifespan pattern for service instantiation
- `backend/app/dependencies.py` — existing DI pattern
- `backend/app/admin/router.py` — `admin_models_install()` and `admin_models_remove()` endpoints
- `backend/app/inference/router.py` — `run_inference()` endpoint
- `backend/app/validation/queue.py` — `AsyncValidationQueue._worker()` method

## Expected Output

- `backend/app/main.py` — ops_log_service instantiated in lifespan
- `backend/app/dependencies.py` — `get_ops_log_service()` added
- `backend/app/admin/router.py` — ops log calls in install/remove handlers
- `backend/app/inference/router.py` — ops log call after inference run
- `backend/app/validation/queue.py` — ops log call after validation completes
