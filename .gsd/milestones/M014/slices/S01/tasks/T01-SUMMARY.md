---
id: T01
parent: S01
milestone: M014
provides:
  - require_role_or_api factory in backend/app/auth/dependencies.py
  - POST /api/commands accepts Bearer token auth
key_files:
  - backend/app/auth/dependencies.py
  - backend/app/commands/router.py
  - backend/tests/test_commands_bearer_auth.py
key_decisions: []
patterns_established:
  - "Use require_role_or_api for API endpoints that need Bearer token support; keep require_role for cookie-only htmx routes"
observability_surfaces:
  - "Existing dual-auth debug logs in get_current_user_or_api cover this change; 401/403 responses carry distinct detail messages"
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Create `require_role_or_api` factory and wire commands endpoint to dual-auth

**Added `require_role_or_api` factory that chains to `get_current_user_or_api` and switched `POST /api/commands` to use it, unblocking Bearer token auth for the browser extension.**

## What Happened

Added `require_role_or_api(*roles)` factory function in `backend/app/auth/dependencies.py`, immediately after the existing `require_role` function. It mirrors `require_role` exactly but uses `get_current_user_or_api` (dual-auth) as its inner dependency instead of `get_current_user` (cookie-only). Updated `backend/app/commands/router.py` to import and use `require_role_or_api("owner", "member")` instead of `require_role("owner", "member")`. The original `require_role` function and all other files importing it are completely unchanged.

Created `backend/tests/test_commands_bearer_auth.py` with 10 tests covering: Bearer token acceptance, cookie acceptance, wrong role rejection (403), no-credentials rejection (401), invalid Bearer rejection (401), and integration tests for the commands endpoint with mocked EventStore/dispatch.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py -v` — 10/10 passed
- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` — 62/62 passed (no regression)
- `cd backend && .venv/bin/python -m pytest tests/ -v --tb=short` — 1018/1018 passed (full suite clean)
- `git diff` confirmed `require_role` function is untouched — only an insertion of the new factory

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_commands_bearer_auth.py -v` | 0 | ✅ pass | 0.69s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 1.43s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -v --tb=short` | 0 | ✅ pass | 7.28s |

## Diagnostics

- **Auth path tracing:** `get_current_user_or_api` already logs `"dual-auth resolved via Bearer token"` and `"dual-auth resolved via session cookie"` at DEBUG level — these fire for all `/api/commands` requests now.
- **Error differentiation:** 401 responses carry distinct `detail` messages: `"Not authenticated"` (no credentials), `"Invalid or expired API token"` (bad Bearer), `"Invalid or expired session"` (bad cookie). 403 responses say `"Requires role: owner, member"`.
- **Test inspection:** `test_commands_bearer_auth.py` test names map 1:1 to auth scenarios for quick diagnosis.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/auth/dependencies.py` — Added `require_role_or_api(*roles)` factory function (~20 lines)
- `backend/app/commands/router.py` — Changed import from `require_role` to `require_role_or_api`, updated dependency on `execute_commands`
- `backend/tests/test_commands_bearer_auth.py` — 10 tests covering factory unit tests and commands endpoint integration
- `.gsd/milestones/M014/slices/S01/S01-PLAN.md` — Added diagnostic verification step per pre-flight
- `.gsd/milestones/M014/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section per pre-flight
