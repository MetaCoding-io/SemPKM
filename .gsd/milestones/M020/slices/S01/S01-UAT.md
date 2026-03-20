# S01: Microsoft OAuth + Graph API Client — UAT

**Milestone:** M020
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is a foundation slice — auth module, REST client, and route handlers are fully exercised by 65 unit tests. No live runtime needed because the app requires Azure AD credentials and a real Microsoft account to connect. Templates are verified by file existence, syntax checks, and htmx prefix grep.

## Preconditions

- Backend virtualenv available at `backend/.venv/`
- No Docker stack or running server needed
- All app files exist in `apps/outlook-calendar/`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v
```
Expected: 65 tests pass in under 1 second.

## Test Cases

### 1. Auth module unit tests pass

1. Run `cd backend && .venv/bin/python -m pytest tests/test_outlook_auth.py -v`
2. **Expected:** 41 tests pass covering: authorize URL construction (5 tests), code exchange success/failure (6 tests), token refresh with rotation (5 tests), refresh-if-expired with buffer and edge cases (8 tests), token storage (3 tests), connection status with masking (6 tests), clear state (2 tests), error class (2 tests), constants (4 tests)

### 2. Client module unit tests pass

1. Run `cd backend && .venv/bin/python -m pytest tests/test_outlook_client.py -v`
2. **Expected:** 24 tests pass covering: auth header injection (2 tests), calendar list with pagination (4 tests), delta queries with incremental sync (5 tests), patch event (2 tests), 401→refresh→retry (3 tests), error handling with status codes (5 tests), exception hierarchy (3 tests)

### 3. Manifest validates against AppManifestSchema

1. Run:
   ```bash
   cd backend && .venv/bin/python -c "
   import sys, yaml; sys.path.insert(0, '.')
   from app.apps.manifest import AppManifestSchema
   with open('../apps/outlook-calendar/manifest.yaml') as f:
       data = yaml.safe_load(f)
   m = AppManifestSchema(**data)
   print(f'Valid: appId={m.appId}, name={m.name}, version={m.version}')
   "
   ```
2. **Expected:** Prints `Valid: appId=outlook-calendar, name=Outlook Calendar Sync, version=0.1.0` with no ValidationError

### 4. No unprefixed htmx URLs in templates

1. Run: `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'`
2. **Expected:** No output (exit code 1) — all htmx URLs use `/app/outlook-calendar/` prefix

### 5. App.py syntax valid

1. Run: `python3 -c "import ast; ast.parse(open('apps/outlook-calendar/app.py').read())"`
2. **Expected:** No SyntaxError, exit code 0

### 6. All required files exist

1. Check existence of all 11 files:
   - `apps/outlook-calendar/manifest.yaml`
   - `apps/outlook-calendar/app.py`
   - `apps/outlook-calendar/services/__init__.py`
   - `apps/outlook-calendar/services/auth.py`
   - `apps/outlook-calendar/services/outlook_client.py`
   - `apps/outlook-calendar/frontend/templates/connect.html`
   - `apps/outlook-calendar/frontend/templates/connect_status.html`
   - `apps/outlook-calendar/frontend/templates/calendars.html`
   - `apps/outlook-calendar/frontend/static/styles.css`
   - `backend/tests/test_outlook_auth.py`
   - `backend/tests/test_outlook_client.py`
2. **Expected:** All 11 files exist

## Edge Cases

### Microsoft refresh token rotation

1. In test_outlook_auth.py, `TestRefreshIfExpired::test_stores_rotated_refresh_token` verifies: when Microsoft returns a different refresh_token in the refresh response, the new token is stored
2. `TestRefreshIfExpired::test_skips_refresh_token_store_when_unchanged` verifies: when the refresh_token is the same, no unnecessary write occurs
3. **Expected:** Both tests pass — this is a Microsoft-specific behavior not present in Google OAuth

### Connection status masking

1. `TestGetConnectionStatus::test_token_preview_masked` verifies the access token is masked to first 8 chars + `...`
2. `TestGetConnectionStatus::test_token_preview_short_token` verifies short tokens still mask correctly
3. **Expected:** No raw tokens exposed in connection status

### Delta query incremental sync

1. `TestGetEventsDelta::test_incremental_sync_with_delta_link` verifies: passing a stored deltaLink skips the initial full sync URL and hits the delta URL directly
2. `TestGetEventsDelta::test_delta_handles_deleted_events` verifies: events with `@removed` key pass through intact for the sync engine to process
3. **Expected:** Delta queries correctly distinguish initial vs incremental sync, and deleted events are visible

### 401 retry loop prevention

1. `TestTokenRefreshOnUnauthorized::test_no_infinite_refresh_loop` verifies: if the retry after refresh also returns 401, the client raises OutlookAuthError instead of looping
2. **Expected:** Single retry, then error — no infinite refresh loop

## Failure Signals

- Any test failure in the 65-test suite indicates a regression
- Manifest validation failure means schema mismatch (check manifest.yaml fields against AppManifestSchema)
- htmx prefix grep returning results means a template has an unprefixed URL that will 404 through the app proxy
- Python syntax error in app.py means the route handlers won't load

## Requirements Proved By This UAT

- None validated yet — S01 establishes infrastructure; end-to-end sync validation happens in S02+

## Not Proven By This UAT

- Actual Microsoft OAuth flow against real Azure AD (requires live credentials)
- Calendar list fetching from Microsoft Graph (requires authenticated session)
- Template rendering in the browser (requires running Docker stack with app platform)
- App installation and lifecycle management (requires running platform)
- Sync engine functionality (deferred to S02)

## Notes for Tester

- The `sync_now` handler in app.py imports `services.sync_engine` which doesn't exist yet — this is expected to fail at runtime until S02 creates it
- The test suite uses importlib to load modules from `apps/outlook-calendar/services/` — if Python path setup changes, tests may need the `sys.modules` registration pattern from test_outlook_client.py
- Microsoft OAuth requires an Azure AD app registration to test live — the unit tests mock all HTTP calls
