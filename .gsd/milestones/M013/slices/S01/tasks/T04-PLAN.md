---
estimated_steps: 4
estimated_files: 1
---

# T04: Unit tests for dual-auth and well-known

**Slice:** S01 — Dual-Auth, CORS, nginx fix, and Well-Known Endpoint
**Milestone:** M013

## Description

Write unit tests verifying the dual-auth dependency logic and the well-known endpoint response schema. These tests run without Docker and validate the auth contract that all downstream endpoints depend on.

## Steps

1. Create `backend/tests/test_api_surface.py`
2. Add dual-auth dependency tests (mock `AuthService` and DB session):
   - `test_dual_auth_with_valid_session_cookie` — valid session → returns user
   - `test_dual_auth_with_valid_bearer_token` — valid Bearer token → returns user
   - `test_dual_auth_no_credentials` — no cookie + no header → raises 401
   - `test_dual_auth_invalid_bearer` — invalid Bearer token → raises 401
   - `test_dual_auth_wrong_scheme` — `Authorization: Basic xxx` → treated as no bearer, raises 401 if no cookie
   - `test_dual_auth_cookie_takes_precedence` — valid cookie + valid bearer → uses cookie path (cookie is tried first)
3. Add well-known endpoint tests (using httpx AsyncClient + FastAPI test app):
   - `test_well_known_returns_json` — returns 200 with correct content-type
   - `test_well_known_has_required_keys` — response contains version, endpoints, auth, capabilities
   - `test_well_known_endpoints_are_strings` — each endpoint value is a string URL path
   - `test_well_known_requires_auth` — request without auth returns 401
4. Run full test suite to verify no regressions: `python -m pytest tests/ -v --tb=short`

## Must-Haves

- [ ] ≥6 tests for dual-auth dependency covering all auth paths
- [ ] ≥4 tests for well-known endpoint covering response schema and auth requirement
- [ ] All tests pass without Docker dependency

## Verification

- `cd backend && python -m pytest tests/test_api_surface.py -v` — all tests green
- `cd backend && python -m pytest tests/ --tb=short -q` — no regressions in existing suite

## Observability Impact

- **Signals changed:** None — this task adds tests only, no runtime behavior changes.
- **Inspection surface:** `cd backend && python -m pytest tests/test_api_surface.py -v` — shows individual test pass/fail with names that describe the auth contract (e.g. `test_dual_auth_valid_bearer_returns_user`, `test_well_known_rejects_unauthenticated`).
- **Failure state:** A failing test in this file means the dual-auth contract or well-known response schema has regressed — downstream M013 endpoints relying on `get_current_user_or_api` may be broken.
- **Coverage indicator:** Test count should be ≥15 (8 bearer-extraction + 7 dual-auth + 8 well-known = 23 total). If count drops below the must-have thresholds (≥6 dual-auth, ≥4 well-known), the auth contract is under-tested.

## Inputs

- `backend/app/auth/dependencies.py` — `get_current_user_or_api` from T01
- `backend/app/api/router.py` — well-known endpoint from T03
- `backend/tests/conftest.py` — existing test fixtures and patterns

## Expected Output

- `backend/tests/test_api_surface.py` — ≥10 unit tests for auth and well-known
