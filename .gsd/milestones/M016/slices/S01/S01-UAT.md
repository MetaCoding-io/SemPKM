# S01: OAuth + App Skeleton + Linear Client — UAT

**Milestone:** M016
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for Docker install and settings page)
- Why this mode is sufficient: Unit tests prove all pure logic (LinearClient, auth helpers, templates). Live runtime verifies the app installs and settings page loads through the App Platform proxy.

## Preconditions

- Docker stack running: `docker compose up -d` from project root
- Linear Sync app directory exists at `apps/linear-sync/` with all files
- Backend venv available at `backend/.venv/` for running unit tests
- (Optional) A real Linear API key for full connectivity test — without one, only the UI and error handling can be verified

## Smoke Test

Run `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` — expect 39/39 pass in <1s.

## Test Cases

### 1. Unit tests pass

1. `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py -v`
2. **Expected:** 22/22 tests pass — covering query construction, auth header resolution, error handling (401/403/429/500/GraphQL), token refresh with retry, pagination cursor chaining, and convenience methods (get_viewer, get_teams, get_organization).

3. `cd backend && .venv/bin/python3 -m pytest tests/test_linear_auth.py -v`
4. **Expected:** 17/17 tests pass — covering OAuth URL builder, code exchange success/failure, token storage (OAuth and API key), workspace info storage, connection status (connected/disconnected/after-clear), auth state clearing, and template rendering (connect with/without error, connect_status with/without teams).

### 2. Manifest is valid and complete

1. `python3 -c "import yaml; m=yaml.safe_load(open('apps/linear-sync/manifest.yaml')); print(m['appId'], m['version'])"`
2. **Expected:** Prints `linear-sync 0.1.0`
3. Verify permissions include all 5 command types: `object.create`, `object.patch`, `body.set`, `body.diff`, `edge.create`
4. Verify network domains: `api.linear.app`, `linear.app`
5. Verify `sparql.read: true`, `backgroundTasks: true`
6. Verify task `poll-tasks` is declared
7. Verify ui page `settings` is declared with correct fragment path
8. **Expected:** All permission types, network domains, features, and UI declarations present.

### 3. App installs in Docker stack

1. Navigate to admin page in browser (http://localhost:3000/admin/)
2. Go to Applications section
3. Find `linear-sync` in available apps list
4. Click Install
5. Accept permissions dialog (5 command permissions, 2 network domains)
6. **Expected:** App installs successfully, shows status "running" in admin apps list.

### 4. Settings page loads (disconnected state)

1. After app is installed, navigate to the app's settings page (via admin app detail or direct URL)
2. The settings fragment loads at `/_fragments/connect` through the app proxy
3. **Expected:** Page shows two sections:
   - "API Key Authentication" with a password input field, a "Connect" button
   - "OAuth Authentication" with a "not yet configured" note
   - No error messages visible

### 5. API key auth — invalid key shows error

1. On the settings page (disconnected state), enter an invalid API key like `lin_api_invalid123`
2. Click "Connect"
3. **Expected:** An error alert appears (red box) indicating the connection failed. The page stays in disconnected state (connect form still visible).

### 6. API key auth — valid key connects and shows workspace info

1. On the settings page, enter a valid Linear personal API key
2. Click "Connect"
3. **Expected:** Page switches to connected state showing:
   - Green "Connected" badge
   - Auth method badge showing "API Key"
   - Workspace name (your Linear workspace name)
   - Table listing your Linear teams (team name, team key)
   - "Disconnect" button

### 7. Disconnect clears auth state

1. From the connected state settings page, click "Disconnect"
2. **Expected:** Page switches back to disconnected state (connect form visible, no workspace info, no team list). The "Connected" badge is gone.

### 8. Reconnect after disconnect

1. After disconnecting, enter the same valid API key again
2. Click "Connect"
3. **Expected:** Successfully reconnects — shows workspace name and team list again.

## Edge Cases

### API key with whitespace

1. Enter an API key with leading/trailing whitespace: `  lin_api_xxxxx  `
2. Click "Connect"
3. **Expected:** Either trims whitespace and connects, or shows a clear error — should not crash or show a generic 500 error.

### Empty API key submission

1. Leave the API key field empty and click "Connect"
2. **Expected:** HTML5 form validation prevents submission (field is required), or the server returns a clear "no key provided" error.

### Double-click Connect button

1. Enter a valid API key and rapidly double-click "Connect"
2. **Expected:** Only one request processes — no duplicate state writes or UI glitches. The htmx indicator shows loading state during the request.

## Failure Signals

- Settings page returns 404 or 502 — app proxy routing not working, check `docker compose logs api | grep linear`
- Settings page shows raw HTML/Jinja template syntax — template rendering error, check app logs
- Unit tests fail with ImportError on `linear_client` — check that `apps/linear-sync/services/linear_client.py` exists
- Unit tests fail with ImportError on `auth` — check the try/except import chain in `apps/linear-sync/services/auth.py`
- API key connection hangs — check app logs for httpx timeout connecting to api.linear.app
- "Connected" badge shows but no teams — `get_teams()` failed silently; check app logs for GraphQL errors

## Requirements Proved By This UAT

- SYNC-01 (auth) — Test cases 5-8 prove API key auth end-to-end. OAuth code exchange is unit-tested but OAuth initiation UI is a placeholder.

## Not Proven By This UAT

- OAuth full flow — requires Linear OAuth app registration with client_id/secret, which is not configured in this slice
- Token refresh under real conditions — unit-tested with mocks but not exercised against a real expired Linear OAuth token
- App auto-start on platform boot — requires restart cycle testing
- Push sync, pull sync, field mapping — all S02+ concerns

## Notes for Tester

- If you don't have a Linear API key, tests 1-5 and 7 still work. Tests 6 and 8 require a real key.
- The OAuth section will show "not yet configured" — this is expected and documented. The OAuth code exchange helper is fully tested via unit tests.
- The app's CSS is scoped under `.linear-sync-settings` so it shouldn't affect other workspace styling.
- The poll-tasks background task will log "poll-tasks executed (noop)" until S02 implements actual sync logic.
