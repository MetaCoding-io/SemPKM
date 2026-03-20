---
id: T01
parent: S01
milestone: M022
provides:
  - Asana OAuth 2.0 + PAT auth module with full unit test coverage
key_files:
  - apps/asana-sync/services/auth.py
  - apps/asana-sync/services/__init__.py
  - backend/tests/test_asana_auth.py
key_decisions:
  - Asana OAuth omits scope param (implicit scopes) unlike Google Calendar pattern
  - PAT verification uses GET /users/me with Bearer header via ASANA_API_URL env var override
  - store_auth_tokens takes auth_method parameter to distinguish oauth vs pat storage
patterns_established:
  - AsanaAuthError fallback import chain mirrors GCalAuthError pattern (services.asana_client → asana_client → local class)
  - ASANA_TOKEN_URL and ASANA_API_URL env var overrides for mock testability
observability_surfaces:
  - Logger "asana.sync.auth" for auth events (exchange, refresh, store, clear, PAT verify)
  - get_connection_status() returns {connected, auth_method, asana_email, token_expiry}
  - AsanaAuthError carries status_code and response_body for diagnostics
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Asana OAuth/PAT auth module with unit tests

**Built Asana auth module with OAuth 2.0 URL builder, code exchange, token refresh with 5-min expiry buffer, PAT verification via /users/me, and state management — 30 unit tests passing.**

## What Happened

Cloned the Google Calendar OAuth pattern and adapted for Asana's endpoints. Key differences from the Google Calendar version: no `scope` parameter in the authorize URL (Asana uses implicit scopes), added `verify_pat()` for Personal Access Token authentication via `GET /users/me`, and `store_auth_tokens()` accepts an `auth_method` parameter to distinguish `"oauth"` vs `"pat"` flows.

The `AsanaAuthError` import uses the same try/except fallback chain as `GCalAuthError` — it tries `services.asana_client`, then `asana_client`, then defines the class locally. The canonical exception hierarchy will be defined in T02's `asana_client.py`.

Test file uses a stub `asana_client` module injected into `sys.modules` before loading `auth.py`, matching the gcal test pattern with importlib module loading.

## Verification

- `python -m pytest backend/tests/test_asana_auth.py -v --noconftest` — **30 tests passed** (target was ≥20)
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/auth.py').read())"` — no syntax errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest backend/tests/test_asana_auth.py -v --noconftest` | 0 | ✅ pass (30/30) | 2.5s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/auth.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python -m pytest backend/tests/test_asana_client.py -v` (slice-level) | — | ⏳ pending T02 | — |
| 4 | All app files present (slice-level) | — | ⏳ partial — services/auth.py and __init__.py present; manifest, app.py, templates pending T03/T04 | — |

## Diagnostics

- **Logger:** grep for `asana.sync.auth` in app logs to see auth event flow
- **Connection state:** Call `get_connection_status(state_client)` — returns `{connected: bool, auth_method: str, asana_email: str, token_expiry: str}`
- **Auth errors:** `AsanaAuthError` exceptions include `.status_code` and `.response_body` for diagnosing OAuth/PAT failures
- **Tests:** `python -m pytest backend/tests/test_asana_auth.py -v --noconftest` from worktree root

## Deviations

- `--noconftest` required when running tests from worktree because the `.env` file contains `ASANA_CLIENT_ID`/`ASANA_CLIENT_SECRET` which the backend's pydantic Settings model rejects as extra fields. This doesn't affect the test itself — it's self-contained with mocks.

## Known Issues

- The worktree `.env` has Asana OAuth credentials that will cause conftest import failures until the backend Settings model is updated to accept them (a later task concern, not T01's scope).

## Files Created/Modified

- `apps/asana-sync/services/__init__.py` — empty package init
- `apps/asana-sync/services/auth.py` — complete auth module (~300 lines) with OAuth 2.0 URL builder, code exchange, token refresh with 5-min buffer, PAT verification, state management
- `backend/tests/test_asana_auth.py` — 30 unit tests covering all auth paths (URL construction, exchange, refresh, expiry buffer, PAT verify, store, status, clear)
- `.gsd/milestones/M022/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
