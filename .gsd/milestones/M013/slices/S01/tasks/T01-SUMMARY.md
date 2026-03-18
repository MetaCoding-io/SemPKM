---
id: T01
parent: S01
milestone: M013
provides:
  - get_current_user_or_api FastAPI dependency (session cookie OR Bearer API token)
  - _extract_bearer_token helper function
  - test_api_surface.py test file with 15 tests for dual-auth
key_files:
  - backend/app/auth/dependencies.py
  - backend/tests/test_api_surface.py
key_decisions:
  - Cookie auth is tried first; Bearer is fallback (cookie precedence)
  - Invalid Bearer token gets specific "Invalid or expired API token" detail; missing credentials gets generic "Not authenticated"
  - AuthService accessed via request.app.state.auth_service (consistent with existing service wiring)
patterns_established:
  - Dual-auth dependency pattern for M013 API-surface endpoints
observability_surfaces:
  - DEBUG log "dual-auth resolved via session cookie" or "dual-auth resolved via Bearer token" in app.auth.dependencies logger
  - HTTP 401 detail field distinguishes auth failure mode (no credentials vs invalid token vs expired session)
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Build dual-auth FastAPI dependency

**Added `get_current_user_or_api` dependency that resolves a User from either session cookie or Bearer API token, with 15 passing tests**

## What Happened

Added two new functions to `backend/app/auth/dependencies.py`:

1. `_extract_bearer_token(authorization)` — parses the `Authorization` header, returns the token string if scheme is Bearer, `None` otherwise. Case-insensitive scheme matching, handles edge cases (empty token, wrong scheme, missing header).

2. `get_current_user_or_api(request, sempkm_session, authorization, db)` — the dual-auth dependency that:
   - First tries the session cookie path (same DB lookup + sliding window as `get_current_user`)
   - Falls back to Bearer token path via `request.app.state.auth_service.verify_api_token()`
   - Raises HTTP 401 with distinct messages: "Not authenticated" (no credentials) or "Invalid or expired API token" (bad bearer)

The existing `get_current_user`, `require_role`, `get_session_token`, and `optional_current_user` dependencies are completely untouched.

Created `backend/tests/test_api_surface.py` with 15 tests covering:
- 8 tests for `_extract_bearer_token` edge cases (valid bearer, case insensitivity, None, empty, wrong scheme, no space, empty token, spaces in token)
- 7 tests for `get_current_user_or_api` (valid cookie, expired cookie, valid bearer, invalid bearer, Basic scheme rejected, no credentials, cookie-over-bearer precedence)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` — 15/15 passed
- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "dual_auth"` — 6/6 passed
- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` — 7/7 passed (slice-level check)
- LSP diagnostics clean on `dependencies.py`
- `get_current_user` still referenced by 20+ existing routers — unchanged

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "dual_auth"` | 0 | ✅ pass | 0.38s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 0.40s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` | 0 | ✅ pass | 0.40s |

Slice-level checks status (T01 is task 1 of 4 — partial passes expected):
- ✅ `pytest tests/test_api_surface.py -v -k "auth or well_known"` — 7 passed (auth tests, no well_known tests yet)
- ⬜ `curl` checks for `/.well-known/sempkm` — endpoint not yet built (T03)
- ⬜ `curl` CORS preflight check — nginx not yet configured (T02)

## Diagnostics

- **Inspect auth path taken:** Set log level to DEBUG and watch `app.auth.dependencies` logger — logs which auth method resolved ("via session cookie" or "via Bearer token")
- **Inspect failure mode:** HTTP 401 `detail` field distinguishes "Not authenticated" (no creds), "Invalid or expired API token" (bad bearer), or "Invalid or expired session" (bad cookie forwarded from cookie path)
- **Verify bearer token usage:** Query `api_tokens.last_used_at` in DB — updated on successful bearer auth via `AuthService.verify_api_token`

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/auth/dependencies.py` — added `_extract_bearer_token` helper and `get_current_user_or_api` dependency; updated module docstring and imports (logging, Header, Request)
- `backend/tests/test_api_surface.py` — new test file with 15 tests for dual-auth dependency
- `.gsd/milestones/M013/slices/S01/S01-PLAN.md` — marked T01 done, added failure-path diagnostic verification step
- `.gsd/milestones/M013/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
