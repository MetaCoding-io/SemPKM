---
estimated_steps: 8
estimated_files: 6
---

# T03: OAuth flow, API key auth, and connected settings page with workspace + team display

**Slice:** S01 — OAuth + App Skeleton + Linear Client
**Milestone:** M016

## Description

Wires the LinearClient (from T02) into the app's settings page via two auth paths: API key entry and OAuth code exchange. After authenticating, the settings page displays the connected workspace name, auth method, and a list of Linear teams. This completes the slice demo: user installs app → authenticates → sees workspace info and teams.

The auth flow helpers live in a separate `auth.py` module for testability. The app.py routes from T01 are upgraded from placeholders to real implementations that use LinearClient and auth helpers.

## Steps

1. Create `apps/linear-sync/services/auth.py` with pure helper functions:
   - `build_oauth_authorize_url(client_id: str, redirect_uri: str, state: str) -> str`:
     Returns `https://linear.app/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}&scope=read,write`
   - `async exchange_code(http_client, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict`:
     POSTs to `https://api.linear.app/oauth/token` with `grant_type=authorization_code`, `code`, `client_id`, `client_secret`, `redirect_uri`. Returns `{"access_token": ..., "refresh_token": ..., "expires_in": ...}`. Raises `LinearAuthError` on failure.
   - `async store_auth_tokens(state_client, access_token: str, refresh_token: str | None, auth_method: str) -> None`:
     Stores `access_token`, `refresh_token` (if present), `auth_method` ("oauth" or "api_key") via state_client.set()
   - `async store_workspace_info(state_client, workspace_name: str, workspace_id: str) -> None`:
     Stores `workspace_name`, `workspace_id` via state_client.set()
   - `async get_connection_status(state_client) -> dict`:
     Returns `{"connected": bool, "auth_method": str|None, "workspace_name": str|None, "workspace_id": str|None}` by reading state keys
   - `async clear_auth_state(state_client) -> None`:
     Removes all auth-related state keys: access_token, refresh_token, api_key, auth_method, workspace_name, workspace_id

2. Update `apps/linear-sync/app.py` — replace T01 placeholder routes with real implementations:
   - **`GET /_fragments/connect`**: Read connection status via `get_connection_status()`. If connected: create LinearClient, fetch teams via `get_teams()`, render `connect_status.html` with workspace_name, auth_method, teams. If disconnected: render `connect.html`. Wrap in try/except — if LinearClient fails (expired token), show connect.html with error message.
   - **`POST /_fragments/connect/api-key`**: Read `api_key` from form body. Store as `api_key` in StateClient. Create LinearClient with the key. Call `get_viewer()` to verify. Call `get_organization()` for workspace name. Store workspace info. Return rendered `connect_status.html` with `HX-Trigger: linearConnected` header for UI refresh. On failure: return error HTML.
   - **`GET /_fragments/oauth-callback`**: Read `code` and `state` from query params. Call `exchange_code()`. Call `store_auth_tokens()`. Create LinearClient. Fetch viewer + organization. Store workspace info. Return HTML with success message and redirect script to settings page. On failure: return error HTML.
   - **`POST /_fragments/connect/disconnect`**: Call `clear_auth_state()`. Return rendered `connect.html` (disconnected state).
   - Import LinearClient from `services.linear_client` and auth helpers from `services.auth`

3. Update `apps/linear-sync/frontend/templates/connect.html`:
   - Wrap in `<div class="linear-sync-settings" id="connect-content">`
   - **API Key section**: `<h3>Connect with API Key</h3>`, form with `<input type="password" name="api_key" placeholder="lin_api_...">`, submit button. Use `hx-post="/_fragments/connect/api-key"` `hx-target="#connect-content"` `hx-swap="innerHTML"`. Add loading indicator via `hx-indicator`.
   - **OAuth section**: `<h3>Connect with OAuth</h3>`, paragraph explaining OAuth, `<a>` link to OAuth authorize URL (constructed server-side or via JS). Note: OAuth requires client_id/secret configured — show "OAuth not configured" message if missing.
   - **Error display**: `{% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}`
   - Guidance text: "Enter your Linear API key (Settings → API → Personal API keys in Linear)"

4. Update `apps/linear-sync/frontend/templates/connect_status.html`:
   - Wrap in `<div class="linear-sync-settings" id="connect-content">`
   - **Connection badge**: green dot + "Connected" + auth method badge ("API Key" or "OAuth")
   - **Workspace info**: `<h3>{{ workspace_name }}</h3>`
   - **Team list**: `<table>` with columns: Team Name, Key. Loop `{% for team in teams %}`. Show "(No teams found)" if empty.
   - **Disconnect button**: `<button hx-post="/_fragments/connect/disconnect" hx-target="#connect-content" hx-swap="innerHTML" hx-confirm="Disconnect from Linear?">Disconnect</button>`

5. Update `apps/linear-sync/frontend/static/styles.css`:
   - `.linear-sync-settings` base container with max-width, padding
   - `.connection-badge` with green/red dot indicator
   - `.auth-method-badge` inline label
   - Form inputs matching SemPKM admin styling patterns
   - Team table with zebra striping
   - `.alert-error` for error messages
   - All rules scoped under `.linear-sync-settings` to avoid conflicts

6. Write `backend/tests/test_linear_auth.py` with unit tests:
   - Use `importlib.util.spec_from_file_location` to load both `auth.py` and `app.py` modules
   - **Auth helper tests:**
     - `test_build_oauth_authorize_url` — correct URL with all params
     - `test_build_oauth_authorize_url_encodes_redirect` — URL-encodes redirect_uri
     - `test_exchange_code_success` — parses token response correctly
     - `test_exchange_code_failure` — raises LinearAuthError on non-200
     - `test_store_auth_tokens_oauth` — stores access_token, refresh_token, auth_method="oauth"
     - `test_store_auth_tokens_api_key` — stores api_key, auth_method="api_key", no refresh_token
     - `test_get_connection_status_connected` — returns connected=True with workspace info
     - `test_get_connection_status_disconnected` — returns connected=False when no tokens
     - `test_clear_auth_state` — all state keys removed
   - **App route handler tests (optional, if feasible with importlib):**
     - `test_connect_fragment_disconnected` — returns connect form HTML
     - `test_connect_fragment_connected` — returns status with workspace name
     - `test_api_key_save_success` — stores key, verifies with get_viewer, returns status
   - Target: ≥12 unit tests
   - Mock pattern: Create `MockStateClient` class with `dict` backing store and async get/set methods. Create `MockHttpClient` class that records requests and returns preset responses.

7. Validate all templates render without Jinja errors:
   - Test that `connect.html` renders with `error=None` context
   - Test that `connect_status.html` renders with `workspace_name="Test"`, `auth_method="api_key"`, `teams=[{"name": "Engineering", "key": "ENG"}]`

8. Run full test suite to ensure no regressions:
   - `cd backend && python -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v`

## Must-Haves

- [ ] API key auth: enter key → verify via get_viewer() → store → show workspace info
- [ ] OAuth helpers: build_oauth_authorize_url, exchange_code, store_auth_tokens all work
- [ ] Settings page: disconnected state shows connect form; connected state shows workspace name + team list
- [ ] Disconnect clears all auth state
- [ ] Error handling: failed auth shows error message, doesn't crash the settings page
- [ ] ≥12 unit tests passing in test_linear_auth.py

## Verification

- `cd backend && python -m pytest tests/test_linear_auth.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` — both test files pass
- Templates render cleanly: `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('apps/linear-sync/frontend/templates'), autoescape=True); print(env.get_template('connect.html').render(error=None)); print(env.get_template('connect_status.html').render(workspace_name='Test', auth_method='api_key', teams=[{'name': 'Eng', 'key': 'ENG'}]))"` — no errors

## Inputs

- `apps/linear-sync/app.py` — T01 skeleton with placeholder routes to replace
- `apps/linear-sync/services/linear_client.py` — T02 LinearClient class with `get_viewer()`, `get_teams()`, `get_organization()`
- `apps/linear-sync/frontend/templates/connect.html` — T01 basic template to enhance
- `apps/linear-sync/frontend/templates/connect_status.html` — T01 basic template to enhance
- `backend/sdk/sempkm_app_sdk/clients/state.py` — StateClient API: `async get(key)`, `async set(key, value)`
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient API for OAuth token exchange
- Linear OAuth flow: authorize at `https://linear.app/oauth/authorize`, token exchange at `https://api.linear.app/oauth/token`

## Expected Output

- `apps/linear-sync/services/auth.py` — auth helper functions (~80-100 lines)
- `apps/linear-sync/app.py` — updated with real route implementations (~120-150 lines)
- `apps/linear-sync/frontend/templates/connect.html` — enhanced with htmx forms and error display
- `apps/linear-sync/frontend/templates/connect_status.html` — enhanced with workspace info and team table
- `apps/linear-sync/frontend/static/styles.css` — polished scoped styles
- `backend/tests/test_linear_auth.py` — ≥12 unit tests for auth helpers and connection flow

## Observability Impact

- **Auth state keys:** `access_token`, `refresh_token`, `api_key`, `auth_method`, `workspace_name`, `workspace_id` stored in `urn:sempkm:app:linear-sync:state` graph via StateClient. Inspect with: `await ctx.state.get("auth_method")`.
- **Logger:** `logging.getLogger("linear_sync")` — INFO for auth state changes (connect/disconnect), DEBUG for route entry. Token values are never logged — only key names and auth_method.
- **Error visibility:** Failed API key verification and OAuth exchange return rendered HTML with error messages (`.alert-error` div). No silent failures — all auth errors surface to the user.
- **Route diagnostics:** `GET /_fragments/connect` — returns connect form or status page depending on state. If LinearClient throws during team fetch, falls back to connect form with error message.
- **Inspection:** Future agent can verify auth state by checking StateClient keys or by hitting `/_fragments/connect` to see whether the connected or disconnected template renders.
