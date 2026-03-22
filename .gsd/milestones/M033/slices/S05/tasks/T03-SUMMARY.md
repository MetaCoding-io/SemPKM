---
id: T03
parent: S05
milestone: M033
provides:
  - Comprehensive unit tests for federation config persistence (18 tests)
  - Full API integration tests for federation endpoint CRUD (13 tests)
  - Fixed 6 broken tests in test_mirror_service.py caused by T01's validate_endpoint refactor
key_files:
  - backend/tests/test_federation_config.py
  - backend/tests/test_federation_endpoints_api.py
  - backend/tests/test_mirror_service.py
key_decisions:
  - Override get_current_user (not require_role) in API test dependency overrides — require_role creates fresh closures so direct override keys don't match
patterns_established:
  - Use _patch_env_endpoints() helper with MockSettings for federation_config.py unit tests
  - Override get_current_user dependency for owner/member API test fixtures — require_role's inner closure picks up the injected user and checks its role correctly
observability_surfaces:
  - Test suite itself is the observability surface — 66 tests across 4 files covering persistence, API, mirror service, and federation discovery
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Unit and API tests for federation features

**Expanded federation test suite to 65 tests (13 API tests rewritten, 6 fixed mirror tests) covering persistence, CRUD API, access control, and env-var protection**

## What Happened

1. **Fixed 6 broken tests in `test_mirror_service.py`:** T01's refactor changed `validate_endpoint()` from using `settings.get_allowed_endpoints()` directly to calling `get_merged_endpoints()` which returns `{url, source, removable}` dicts. The existing tests mocked `app.sparql.mirror.settings` which no longer exists as an import in `mirror.py`. Updated `TestValidateEndpoint` (4 tests) and `TestMirrorRouter` (2 tests) to mock `app.sparql.mirror.get_merged_endpoints` instead, with the correct dict-list return shape.

2. **Rewrote `test_federation_endpoints_api.py` with correct dependency override pattern and 13 tests:** The original 6 tests used `app.dependency_overrides[require_role("owner")]` which doesn't match because `require_role()` creates a fresh closure each call. Fixed by overriding `get_current_user` instead — `require_role("owner")`'s inner closure calls `get_current_user` (now returning the mock user) and checks role normally. Added 7 new tests:
   - `test_get_accessible_by_member` — confirms GET is not owner-restricted
   - `test_add_http_url_accepted` — plain http:// URLs work
   - `test_add_duplicate_endpoint_is_idempotent` — same URL twice → 1 entry
   - `test_add_endpoint_owner_only` — member POST → 403
   - `test_delete_then_get_reflects_removal` — delete + GET consistency
   - `test_delete_endpoint_owner_only` — member DELETE → 403
   - `test_remove_nonexistent_returns_409` — missing URL → 409
   - `test_get_returns_merged_list` — verifies source annotations for env/admin entries

3. **Existing test_federation_config.py (18 tests) confirmed passing** — no changes needed, T01 wrote these correctly.

4. **test_federation_discovery.py (8 tests) confirmed passing** — no changes needed, unaffected by T01/T02 changes.

## Verification

All 65 tests across 4 files pass with zero failures:
- `test_federation_config.py`: 18 passed
- `test_federation_endpoints_api.py`: 13 passed
- `test_mirror_service.py`: 26 passed
- `test_federation_discovery.py`: 8 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py tests/test_federation_endpoints_api.py tests/test_mirror_service.py tests/test_federation_discovery.py -v` | 0 | ✅ pass | 0.8s |

## Diagnostics

- **Test structure:** Unit tests use `tmp_path` fixture for isolated file I/O and `_patch_env_endpoints()` for mocking frozen Pydantic Settings. API tests use `httpx.AsyncClient` + `ASGITransport` with dependency overrides on `get_current_user`.
- **Access control coverage:** Both POST and DELETE owner-only routes are verified to return 403 for member-role users. GET /endpoints is verified accessible to members.
- **Env-var protection:** DELETE of env-sourced endpoints returns 409 with descriptive error message.

## Deviations

- Rewrote the API test file from scratch instead of extending the existing 6 tests. The original fixture pattern (`app.dependency_overrides[require_role("owner")]`) was fundamentally broken — `require_role()` returns a new closure each call so the override key never matches the one stored in FastAPI's route. The correct pattern is overriding `get_current_user`.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_federation_endpoints_api.py` — rewrote with correct auth override pattern and 14 tests (was 6)
- `backend/tests/test_mirror_service.py` — fixed 6 tests: updated mocks from `settings` to `get_merged_endpoints` with dict-list return shape
