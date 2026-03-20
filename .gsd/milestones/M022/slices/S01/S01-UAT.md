# S01: OAuth + project selection + custom field mapping UI — UAT

**Milestone:** M022
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice builds the authentication and configuration pipeline — no sync runtime yet. All behavior is proven by 58 unit tests covering auth flows, API client, and structural checks on templates/manifest. Live runtime testing will happen in S04 (E2E tests).

## Preconditions

- Backend venv available at `/home/james/Code/SemPKM/backend/.venv/bin/python`
- Test files present in worktree at `backend/tests/test_asana_auth.py` and `backend/tests/test_asana_client.py`
- App files present at `apps/asana-sync/`

## Smoke Test

Run both test suites:
```
cd /home/james/Code/SemPKM/.gsd/worktrees/M018
/home/james/Code/SemPKM/backend/.venv/bin/python -m pytest backend/tests/test_asana_auth.py backend/tests/test_asana_client.py -v --noconftest
```
**Expected:** 58 tests pass (30 auth + 28 client), 0 failures.

## Test Cases

### 1. OAuth URL construction

1. Run: `pytest backend/tests/test_asana_auth.py::TestBuildAsanaAuthorizeUrl -v --noconftest`
2. **Expected:** 4 tests pass — URL includes client_id, redirect_uri, response_type=code, state parameter. No scope parameter (Asana uses implicit scopes).

### 2. OAuth code exchange and token refresh

1. Run: `pytest backend/tests/test_asana_auth.py::TestExchangeCode backend/tests/test_asana_auth.py::TestRefreshAccessToken -v --noconftest`
2. **Expected:** 6 tests pass — success returns token dict, failure raises AsanaAuthError, missing fields return empty strings, refresh sends correct body.

### 3. Token expiry buffer

1. Run: `pytest backend/tests/test_asana_auth.py::TestRefreshIfExpired -v --noconftest`
2. **Expected:** 6 tests pass — tokens expiring within 5 minutes trigger refresh, expired tokens trigger refresh, no-refresh-token raises error, missing/invalid expiry format triggers refresh.

### 4. PAT verification

1. Run: `pytest backend/tests/test_asana_auth.py::TestVerifyPat -v --noconftest`
2. **Expected:** 4 tests pass — success returns user data, sends Bearer header, 401 raises AsanaAuthError, handles missing data wrapper.

### 5. Auth state management

1. Run: `pytest backend/tests/test_asana_auth.py::TestStoreAuthTokens backend/tests/test_asana_auth.py::TestGetConnectionStatus backend/tests/test_asana_auth.py::TestClearAuthState -v --noconftest`
2. **Expected:** 10 tests pass — store_auth_tokens stores all fields with auth_method, computes ISO 8601 expiry, handles None expires_in. get_connection_status returns correct connected/disconnected state with auth_method and email. clear removes all auth keys.

### 6. Client auth header and data unwrapping

1. Run: `pytest backend/tests/test_asana_client.py::TestGetHeaders backend/tests/test_asana_client.py::TestRequest -v --noconftest`
2. **Expected:** 11 tests pass — Bearer token in header, no-token raises error, 200 extracts data wrapper (dict and list), 401 triggers refresh+retry (no infinite loop), 403 raises auth error, 429 raises rate limit with Retry-After (default 60s), 500 raises API error.

### 7. Pagination via offset

1. Run: `pytest backend/tests/test_asana_client.py::TestPaginatedGet -v --noconftest`
2. **Expected:** 3 tests pass — single page returns data, multi-page concatenates via offset cursor, empty results return empty list.

### 8. Resource endpoints

1. Run: `pytest backend/tests/test_asana_client.py::TestGetWorkspaces backend/tests/test_asana_client.py::TestGetProjects backend/tests/test_asana_client.py::TestGetSections backend/tests/test_asana_client.py::TestGetCustomFields backend/tests/test_asana_client.py::TestGetTasks backend/tests/test_asana_client.py::TestGetUserMe backend/tests/test_asana_client.py::TestPatchTask backend/tests/test_asana_client.py::TestAddTaskToSection -v --noconftest`
2. **Expected:** 11 tests pass — workspaces listed, projects filtered (non-archived), sections listed, custom_fields extracted from settings (skips entries without custom_field), tasks returned with opt_fields + modified_since, user_me returns data with auth header, patch sends JSON body, add_task_to_section sends nested data format.

### 9. Exception hierarchy

1. Run: `pytest backend/tests/test_asana_client.py::TestExceptionHierarchy -v --noconftest`
2. **Expected:** 3 tests pass — AsanaAuthError and AsanaRateLimitError are subclasses of AsanaAPIError, all carry status_code and response_body.

### 10. Manifest structure

1. Run:
```python
import yaml
m = yaml.safe_load(open('apps/asana-sync/manifest.yaml'))
assert m['appId'] == 'asana-sync'
assert 'app.asana.com' in m['permissions']['network']
assert {t['id'] for t in m['tasks']} == {'poll-tasks', 'push-changes'}
```
2. **Expected:** All assertions pass. appId is "asana-sync", network includes app.asana.com, two scheduled tasks defined.

### 11. Template htmx URL safety

1. Run: `grep -n 'hx-\(post\|get\|put\|delete\)' apps/asana-sync/frontend/templates/connect.html apps/asana-sync/frontend/templates/connect_status.html | grep -v '/app/asana-sync/'`
2. **Expected:** No output — all htmx URLs use the `/app/asana-sync/` proxy prefix.

### 12. Field mapping UI elements present

1. Run:
```
grep -c 'status_source' apps/asana-sync/frontend/templates/connect_status.html
grep -c 'priority_field_gid' apps/asana-sync/frontend/templates/connect_status.html
grep -c 'story_points_field_gid' apps/asana-sync/frontend/templates/connect_status.html
```
2. **Expected:** status_source ≥ 8 (radios + conditionals), priority_field_gid ≥ 3, story_points_field_gid ≥ 3.

## Edge Cases

### Rate limit with missing Retry-After header

1. Run: `pytest backend/tests/test_asana_client.py::TestRequest::test_429_defaults_retry_after_to_60 -v --noconftest`
2. **Expected:** When 429 response lacks Retry-After header, AsanaRateLimitError.retry_after defaults to 60 seconds.

### PAT with missing data wrapper

1. Run: `pytest backend/tests/test_asana_auth.py::TestVerifyPat::test_missing_data_wrapper -v --noconftest`
2. **Expected:** When /users/me response lacks `{"data": ...}` wrapper, verify_pat still returns the response body.

### Custom fields without custom_field sub-object

1. Run: `pytest backend/tests/test_asana_client.py::TestGetCustomFields::test_skips_settings_without_custom_field -v --noconftest`
2. **Expected:** Settings entries missing the `custom_field` key are silently skipped.

### 401 with no refresh token

1. Run: `pytest backend/tests/test_asana_client.py::TestRequest::test_401_no_refresh_token_raises -v --noconftest`
2. **Expected:** When 401 occurs and no refresh_token is stored, AsanaAuthError is raised immediately without attempting refresh.

## Failure Signals

- Any test failure in auth or client test suites — indicates broken auth flow or API client logic
- Missing app files (manifest.yaml, app.py, templates) — indicates incomplete app shell
- htmx URLs without `/app/asana-sync/` prefix — will cause 404 errors at runtime (requests bypass proxy)
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` fails — syntax error in route handlers
- manifest.yaml appId != "asana-sync" — app platform won't register the app correctly

## Requirements Proved By This UAT

- None directly — ASANA requirements will be registered as the full sync lifecycle is proven across S01–S04. This UAT proves the configuration pipeline prerequisite for all ASANA requirements.

## Not Proven By This UAT

- Live OAuth redirect flow (requires Asana developer app credentials + running app platform)
- Live field discovery from Asana API (requires authenticated connection to real workspace)
- Sync execution (pull/push) — deferred to S02/S03
- Docker runtime behavior — deferred to S04 E2E tests

## Notes for Tester

- Tests must be run with `--noconftest` flag because the backend Settings model doesn't recognize Asana env vars in the worktree `.env` file. This is expected and doesn't affect test validity — all tests are self-contained with mocks.
- The correct Python is at `/home/james/Code/SemPKM/backend/.venv/bin/python` — system python3 doesn't have pytest installed.
- The field mapping UI's conditional display logic is in inline JS — verifiable only via browser runtime (S04 E2E tests).
