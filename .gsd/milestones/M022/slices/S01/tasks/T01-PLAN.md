---
estimated_steps: 6
estimated_files: 3
---

# T01: Asana OAuth/PAT auth module with unit tests

**Slice:** S01 — OAuth + project selection + custom field mapping UI
**Milestone:** M022

## Description

Build the Asana authentication module supporting both OAuth 2.0 and Personal Access Token (PAT) flows. This is the foundation for all API access in the Asana Sync app.

Clone the Google Calendar OAuth pattern (`apps/google-calendar/services/auth.py`) which has: `build_authorize_url()`, `exchange_code()`, `refresh_access_token()`, `refresh_if_expired()` with 5-minute buffer, `store_auth_tokens()`, `get_connection_status()`, `clear_auth_state()`. Adapt for Asana's OAuth endpoints and add PAT verification support.

Asana OAuth has no explicit scopes — the scope parameter is omitted. Token endpoint requires `grant_type`, `code`/`refresh_token`, `client_id`, `client_secret`, `redirect_uri`.

## Steps

1. Create `apps/asana-sync/services/__init__.py` (empty).

2. Create `apps/asana-sync/services/auth.py` with:
   - Constants: `ASANA_AUTHORIZE_URL = "https://app.asana.com/-/oauth_authorize"`, `ASANA_TOKEN_URL = os.environ.get("ASANA_TOKEN_URL", "https://app.asana.com/-/oauth_token")`, `AUTH_STATE_KEYS` tuple.
   - `build_asana_authorize_url(client_id, redirect_uri, state)` → URL string. No scope parameter (Asana implicit scopes). Include `response_type=code`.
   - `exchange_code(http_client, code, client_id, client_secret, redirect_uri)` → dict with access_token, refresh_token, expires_in. POST to ASANA_TOKEN_URL with `grant_type=authorization_code`.
   - `refresh_access_token(http_client, refresh_token, client_id, client_secret)` → dict with access_token, expires_in. POST with `grant_type=refresh_token`.
   - `refresh_if_expired(http_client, state_client, client_id, client_secret)` → access_token string. 5-minute buffer before expiry. Reads/writes token_expiry as ISO 8601.
   - `verify_pat(http_client, pat)` → dict with user email/name. GET `https://app.asana.com/api/1.0/users/me` with Bearer token. Uses env var `ASANA_API_URL` for mock testability.
   - `store_auth_tokens(state_client, access_token, refresh_token, expires_in, asana_email, auth_method)` — persists tokens and metadata.
   - `get_connection_status(state_client)` → dict with connected, auth_method, asana_email, token_expiry.
   - `clear_auth_state(state_client)` — sets all AUTH_STATE_KEYS to empty string.
   - Import `AsanaAuthError` from `asana_client` module with the same try/except/fallback pattern used in `apps/google-calendar/services/auth.py`.

3. Create `backend/tests/test_asana_auth.py` using the importlib module-loading pattern from `backend/tests/test_gcal_auth.py`. Load `asana_client` first (for `AsanaAuthError`), then `auth`. Use `MockResponse` and `MockStateClient` helpers.
   - Test `build_asana_authorize_url`: correct base URL, query params include client_id/redirect_uri/state/response_type=code, no scope param.
   - Test `exchange_code`: success returns tokens, failure raises AsanaAuthError.
   - Test `refresh_access_token`: success returns new token, failure raises AsanaAuthError.
   - Test `refresh_if_expired`: token still valid (returns cached), token expired (refreshes), no expiry recorded (refreshes), no refresh token (raises), invalid expiry format (refreshes).
   - Test `verify_pat`: success returns user data, 401 raises AsanaAuthError.
   - Test `store_auth_tokens`: all keys set including computed token_expiry ISO 8601.
   - Test `get_connection_status`: connected state, disconnected state.
   - Test `clear_auth_state`: all keys set to empty.
   - Target: ≥20 tests.

4. Note: The `AsanaAuthError` class will be defined in `asana_client.py` (T02). For T01, create a minimal stub at the top of `auth.py` with a try/except import that falls back to defining the class locally if the import fails, matching the Google Calendar pattern exactly.

5. Verify: `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py -v`

6. Commit: `feat(asana-sync): add OAuth/PAT auth module with unit tests`

## Must-Haves

- [ ] OAuth 2.0 URL builder with Asana endpoints (no scope parameter)
- [ ] Code exchange with error handling
- [ ] Token refresh with error handling
- [ ] refresh_if_expired with 5-minute buffer and ISO 8601 token_expiry
- [ ] PAT verification via GET /users/me
- [ ] Token storage, connection status, clear — all via StateClient
- [ ] Env var overrides for ASANA_TOKEN_URL and ASANA_API_URL (mock testability)
- [ ] ≥20 unit tests covering all auth paths

## Verification

- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py -v` — ≥20 tests pass
- `python -c "import ast; ast.parse(open('apps/asana-sync/services/auth.py').read())"` — no syntax errors

## Observability Impact

- **New logger:** `logging.getLogger("asana.sync.auth")` — emits INFO on token exchange/refresh/store/clear, WARNING on failed token exchange/refresh
- **Inspection surface:** `get_connection_status(state_client)` returns `{connected, auth_method, asana_email, token_expiry}` — queryable at runtime to check auth state
- **Failure signals:** `AsanaAuthError` exceptions carry `status_code` and `response_body` for diagnosing OAuth/PAT failures
- **Redaction:** access_token, refresh_token, client_secret values never appear in log output — only key names and status codes
- **How a future agent inspects this task:** Run `python -m pytest backend/tests/test_asana_auth.py -v` to verify all auth paths. Check `get_connection_status()` return dict for auth state. grep for `asana.sync.auth` in logs.

## Inputs

- `apps/google-calendar/services/auth.py` — OAuth 2.0 pattern to clone (authorize URL, code exchange, refresh, store, status, clear)
- `apps/google-calendar/services/gcal_client.py` — exception class pattern (GCalAuthError)
- `backend/tests/test_gcal_auth.py` — test pattern with importlib module loading, MockResponse, MockStateClient

## Expected Output

- `apps/asana-sync/services/__init__.py` — empty init
- `apps/asana-sync/services/auth.py` — complete auth module (~250 lines) with OAuth 2.0 + PAT support
- `backend/tests/test_asana_auth.py` — ≥20 unit tests proving all auth paths
