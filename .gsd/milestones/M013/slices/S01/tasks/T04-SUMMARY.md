---
id: T04
parent: S01
milestone: M013
provides:
  - 25 unit tests covering dual-auth dependency and well-known endpoint
  - Explicit content-type and endpoint-string-type assertions
key_files:
  - backend/tests/test_api_surface.py
key_decisions:
  - Tests split into TestExtractBearerToken (8), dual-auth classes (7), TestWellKnownEndpoint (10) for clear auth-contract coverage
patterns_established:
  - Well-known endpoint test pattern using httpx AsyncClient + ASGITransport + dependency_overrides
observability_surfaces:
  - pytest -v tests/test_api_surface.py — shows individual auth-contract test results; any failure means the dual-auth or well-known contract regressed
duration: 8m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: Unit tests for dual-auth and well-known

**Added content-type, required-keys, and endpoint-string-type tests to the existing 22-test suite, bringing total to 25 tests covering all dual-auth paths and well-known response schema**

## What Happened

The test file `backend/tests/test_api_surface.py` was already created during T01 and T03 with 22 tests. T04's role was to verify completeness against the plan requirements and add any missing coverage.

Three tests were added:
1. `test_well_known_returns_json_with_correct_content_type` — asserts `application/json` in response content-type header
2. `test_well_known_has_required_keys` — explicitly checks all four required top-level keys (version, endpoints, auth, capabilities)
3. `test_well_known_endpoints_are_strings` — iterates endpoint values asserting each is a string starting with `/`

These were explicitly called for in the task plan but were only implicitly covered by existing tests.

Final test count: 25 total (8 bearer extraction + 7 dual-auth + 10 well-known). Plan required ≥6 dual-auth and ≥4 well-known — both exceeded.

Also added the missing `## Observability Impact` section to `T04-PLAN.md` per pre-flight requirement.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` — 25/25 passed (0.62s)
- `cd backend && .venv/bin/python -m pytest tests/ --tb=short -q` — 971 passed, 0 failures (6.23s)
- `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` — 17 matched, all passed (slice-level verification check)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v --tb=short` | 0 | ✅ pass | 0.62s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/ --tb=short -q` | 0 | ✅ pass | 6.23s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v -k "auth or well_known"` | 0 | ✅ pass | 0.61s |

### Slice-Level Verification Status (T04 is final task)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Unit tests pass (`-k "auth or well_known"`) | ✅ pass | 17 matched, all green |
| 2 | `curl /.well-known/sempkm` returns JSON | ⏭ skip | Requires Docker stack |
| 3 | Bearer auth returns 200 | ⏭ skip | Requires Docker stack |
| 4 | Invalid bearer returns 401 | ⏭ skip | Requires Docker stack |
| 5 | CORS preflight returns headers | ⏭ skip | Requires Docker stack |
| 6 | Failure-path 401 with specific detail | ⏭ skip | Requires Docker stack |

Docker-dependent checks (2–6) were verified in T02 and T03 summaries. This task validates the unit-test gate only.

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_api_surface.py -v` to inspect individual test outcomes
- Test names map directly to auth-contract behaviors: `test_dual_auth_valid_cookie_returns_user`, `test_dual_auth_invalid_bearer_raises_401`, etc.
- If a test fails, the test class name indicates which auth path is broken (CookiePath, BearerPath, NoCredentials, Precedence)

## Deviations

None — the test file already existed from prior tasks; T04 added the three explicitly required tests from the plan that were missing.

## Known Issues

- httpx `DeprecationWarning` on per-request `cookies=` parameter (7 warnings). Not a bug — httpx plans to change cookie handling API. Current usage works correctly.

## Files Created/Modified

- `backend/tests/test_api_surface.py` — added 3 tests (content-type, required-keys, endpoints-are-strings); total 25
- `.gsd/milestones/M013/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section (pre-flight fix)
