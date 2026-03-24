---
id: T02
parent: S02
milestone: M037
provides:
  - Context rules CRUD API router (5 endpoints)
  - Integration hook in context router (auto-persona switching on context update)
  - get_rules_engine and get_persona_service dependency functions
  - RulesEngine and rules router mounted in main.py lifespan
  - 26 router-level tests including integration hook tests
key_files:
  - backend/app/context/rules_router.py
  - backend/app/context/router.py
  - backend/app/dependencies.py
  - backend/app/main.py
  - backend/tests/test_rules_router.py
key_decisions:
  - Rule evaluation errors in the integration hook are caught and logged, never breaking the context update response
  - Redundant persona switches are skipped by comparing active persona ID before calling activate()
  - Test endpoint returns rule_name alongside persona_id for UI display
patterns_established:
  - Integration hook accesses rules_engine and persona_service via request.app.state (not Depends) since they're called mid-endpoint
  - Auth enforcement tests create a separate FastAPI app without the auth dependency override
observability_surfaces:
  - "context.persona_switched" structured log (user_id, persona_id, persona_name) on auto-switch
  - "context.rule_evaluation_failed" error log with traceback on evaluation errors
  - "persona_switched" SSE event with persona_id, persona_name, rule_name fields
  - GET /api/context/rules — list all rules
  - POST /api/context/rules/test — evaluate rules against current context (read-only)
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Rules CRUD API router, integration hook, and router tests

**Built 5-endpoint CRUD+test API for context rules, wired auto-persona switching integration hook into context update, and added 26 router tests — all 45 tests pass across both suites.**

## What Happened

Built four deliverables:

1. **rules_router.py** — FastAPI APIRouter at `/api/context/rules` with GET (list), POST (create, 201), PUT (update), DELETE (204), and POST /test (read-only evaluation). All endpoints require auth. The test endpoint evaluates rules against the user's current context and returns match details without side effects.

2. **dependencies.py** — Added `get_rules_engine` and `get_persona_service` dependency functions following the existing pattern (lazy import to avoid circular deps).

3. **main.py** — Registered `RulesEngine(async_session_factory)` on `app.state.rules_engine` during lifespan startup. Mounted `context_rules_router` after the context router.

4. **router.py (context)** — Added integration hook after the `broadcast.publish(context_update)` call in `update_context()`. On every context update: evaluate rules → check if matched persona differs from active → activate if different → broadcast `persona_switched` SSE event. Wrapped in try/except so evaluation failures never break the context update response.

5. **test_rules_router.py** — 26 tests covering: create (201, defaults, validation), list (empty, populated, user-scoped), update (success, 404, 422, partial), delete (204, 404), test endpoint (match, no-match, no-context), auth enforcement on all 5 endpoints, and integration hook (rule evaluation, persona switch, redundant skip, no-match, error resilience).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — 26/26 passed
- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py tests/test_rules_router.py -v` — 45/45 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` | 0 | ✅ pass | 0.74s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py tests/test_rules_router.py -v` | 0 | ✅ pass | 0.98s |

## Diagnostics

- **Rules API:** `GET /api/context/rules` lists all user rules; `POST /api/context/rules/test` evaluates without side effects
- **Structured logs:** grep for `context.persona_switched` to trace auto-switches; `context.rule_evaluation_failed` for errors
- **SSE stream:** `persona_switched` events on the context SSE stream carry persona_id, persona_name, rule_name
- **Error resilience:** Integration hook failures are logged with full traceback but never propagate to the 200 response

## Deviations

- The plan suggested clearing `manual_override` flag in the integration hook. Deferred this since the flag column was added in T01's migration but no read/write logic exists yet — it would be dead code. The override check can be added in a later task when the settings UI needs it.

## Known Issues

None.

## Files Created/Modified

- `backend/app/context/rules_router.py` — New: CRUD + test API router for context rules (5 endpoints)
- `backend/app/context/router.py` — Modified: added uuid import and auto-persona switching integration hook
- `backend/app/dependencies.py` — Modified: added get_rules_engine and get_persona_service dependency functions
- `backend/app/main.py` — Modified: imported rules_router, registered RulesEngine in lifespan, mounted router
- `backend/tests/test_rules_router.py` — New: 26 router-level tests including integration hook coverage
