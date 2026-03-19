# S02: Google OAuth 2.0 + Calendar List — Research

**Date:** 2026-03-18

## Summary

S02 delivers OAuth 2.0 authentication for the Google Calendar sync app, calendar list display with selection checkboxes, and token storage with refresh support. This is the first real OAuth flow in a sync app — Linear used API keys (D199), GitHub used PATs (D206). Google Calendar API v3 has no API key path for user-data access, so OAuth is mandatory (D210).

The good news: the app scaffold (routes, templates, manifest, services directory) follows established patterns from `apps/linear-sync/` and `apps/github-sync/`. The OAuth code exchange, token storage, and refresh logic mirror what's already in `apps/linear-sync/services/auth.py` — just adapted for Google's endpoints.

The critical finding is that **the app proxy drops query parameters** when forwarding requests to app subprocesses. `proxy.py` line 63 constructs `target_url = f"http://localhost/{path}"` without appending the request's query string. This means an OAuth callback like `/app/google-calendar/_fragments/oauth-callback?code=xxx&state=yyy` arrives at the app with no `code` parameter. This must be fixed before OAuth can work.

A secondary issue: the SDK's `HttpClient` domain enforcement has a permissions parsing bug — `context.py` line 136-137 treats the manifest's `network` list as a dict, resulting in `allowed_domains=[]` which blocks all external HTTP requests. This affects all existing sync apps (Linear, GitHub) but is likely masked because E2E tests mock the HttpClient or use internal Docker networking. Fixing this is needed for the Google Calendar app to reach Google's token and API endpoints.

## Recommendation

**Fix the two platform bugs first, then build the app.** The proxy query-param fix is a one-line change in `proxy.py`. The HttpClient domain-enforcement fix is a one-line change in `context.py`. Both are required for OAuth to work at all. After that, the app follows the Linear sync pattern closely:

1. Create `apps/google-calendar/` directory structure (manifest, app.py, services/auth.py, services/gcal_client.py, templates)
2. Implement OAuth helpers (authorize URL builder, code exchange, token storage, refresh)
3. Implement calendar list fetching via Google Calendar API v3
4. Build connect/settings UI templates with OAuth button and calendar checkboxes
5. Write unit tests following the `test_linear_auth.py` / `test_linear_client.py` pattern

The Google OAuth flow is: (1) user clicks "Connect with Google" → (2) redirect to Google consent screen → (3) Google redirects back with `?code=xxx` to callback URL → (4) app exchanges code for tokens → (5) app stores tokens and fetches calendar list.

Client ID and client secret come from Google Cloud Console and are stored in the app's state (entered by the admin in a settings form). The callback URL is `http://localhost:3000/app/google-calendar/_fragments/oauth-callback` (goes through nginx → FastAPI → app proxy → app subprocess).

## Implementation Landscape

### Key Files

**Platform fixes:**
- `backend/app/apps/proxy.py` — Line 63: `target_url = f"http://localhost/{path}"` drops query string. Fix: append `request.url.query` when present. One-line change.
- `backend/sdk/sempkm_app_sdk/context.py` — Line 136-137: `network.get("domains", []) if isinstance(network, dict) else []` should use `else network` so that a plain list from the manifest is used directly as `allowed_domains`.

**New app files (follow linear-sync/github-sync pattern):**
- `apps/google-calendar/manifest.yaml` — App manifest with `appId: "google-calendar"`, permissions for commands + sparql + network (googleapis.com domains) + backgroundTasks, tasks for `poll-events` and `push-changes`, UI page for settings.
- `apps/google-calendar/requirements.txt` — No extra deps beyond what the SDK provides (httpx for HTTP, yaml).
- `apps/google-calendar/app.py` — Route handlers: `/_fragments/connect` (settings page), `/_fragments/connect/google` (start OAuth flow), `/_fragments/oauth-callback` (handle callback), `/_fragments/connect/disconnect` (clear auth), `/_fragments/settings/calendars` (save selected calendars). Skeleton task handlers for S03.
- `apps/google-calendar/services/__init__.py` — Empty init.
- `apps/google-calendar/services/auth.py` — Pure functions: `build_google_authorize_url()`, `exchange_code()`, `refresh_access_token()`, `refresh_if_expired()`, `store_auth_tokens()`, `get_connection_status()`, `clear_auth_state()`. State keys: `access_token`, `refresh_token`, `token_expiry`, `auth_method`, `google_email`, `google_client_id`, `google_client_secret`.
- `apps/google-calendar/services/gcal_client.py` — REST client wrapping `ctx.http` for Google Calendar API v3. Methods: `get_calendar_list()`, exception classes (`GCalAPIError`, `GCalAuthError`). Token refresh on 401 via `refresh_if_expired()` from auth module. Base URL: `https://www.googleapis.com/calendar/v3` (override via env var for testing).
- `apps/google-calendar/frontend/templates/connect.html` — Connect form with OAuth client ID/secret inputs and "Connect with Google" button. Follows linear-sync `connect.html` pattern.
- `apps/google-calendar/frontend/templates/connect_status.html` — Connected status showing Google email, calendar list with checkboxes, disconnect button. Follows linear-sync `connect_status.html` pattern.
- `apps/google-calendar/frontend/static/styles.css` — App-specific CSS (can start with a copy of linear-sync styles).

**Test files:**
- `backend/tests/test_gcal_auth.py` — Unit tests for auth helpers: URL construction, code exchange (success/failure), token storage (OAuth), token refresh (success/failure/expiry), connection status, clear state. Follow `test_linear_auth.py` pattern with MockHttpClient, MockStateClient.
- `backend/tests/test_gcal_client.py` — Unit tests for GCalClient: calendar list fetch, auth header construction, 401 → refresh → retry, rate limit handling, error responses. Follow `test_linear_client.py` / `test_github_client.py` pattern.
- `backend/tests/test_app_proxy_query_params.py` — Regression test for query parameter forwarding in proxy.

### Build Order

1. **Fix proxy query-param forwarding** — One-line fix in `proxy.py`. Without this, OAuth callbacks silently lose the authorization code. Add a regression test.
2. **Fix HttpClient domain-enforcement parsing** — One-line fix in `context.py`. Without this, the app can't reach Google's token endpoint or API. Add a test.
3. **Create app directory structure + manifest** — `apps/google-calendar/` with manifest.yaml. Proves the app installs.
4. **Build auth module** — `services/auth.py` with all OAuth helpers. Pure functions, fully testable with mocks.
5. **Build gcal_client** — `services/gcal_client.py` with calendar list fetching and token refresh. Testable with mock HTTP responses.
6. **Build app routes + templates** — `app.py` with connect flow, OAuth callback, calendar list display.
7. **Write unit tests** — Auth tests, client tests, template rendering tests.

### Verification Approach

- **Proxy fix:** Unit test sending a request with query params through the proxy and asserting they arrive at the target URL.
- **Auth module:** ~15 unit tests covering URL construction, code exchange (success/failure), token storage, token refresh (success/failure/lock), connection status (connected/disconnected/cleared), clear state.
- **GCal client:** ~10 unit tests covering calendar list fetch (paginated), auth header injection, 401 → refresh → retry, 403/429/500 error handling.
- **Templates:** Jinja2 rendering tests (connect form renders, status page renders with calendars, error display).
- **Integration:** Manual Docker test — install app, verify settings page loads. OAuth flow itself can only be tested against a real Google account or a mock OAuth server (deferred to S05 E2E tests).

## Constraints

- **Google OAuth scopes:** `https://www.googleapis.com/auth/calendar.readonly` for pull-only, `https://www.googleapis.com/auth/calendar.events` for bidirectional (RSVP push). S02 should request the broader scope upfront since S04 needs it.
- **Google token endpoint:** `https://oauth2.googleapis.com/token` (POST, form-encoded body, returns JSON with `access_token`, `refresh_token`, `expires_in`, `token_type`). Access tokens expire after 3600 seconds (1 hour).
- **Google authorize endpoint:** `https://accounts.google.com/o/oauth2/v2/auth` with params `client_id`, `redirect_uri`, `response_type=code`, `scope`, `access_type=offline` (required for refresh token), `state` (CSRF), `prompt=consent` (ensures refresh token is returned).
- **`access_type=offline`** is critical — without it, Google only returns an access_token with no refresh_token, and the app would need the user to re-authenticate every hour.
- **`prompt=consent`** is needed to force Google to return a refresh_token even on subsequent authorizations. Without it, Google only returns a refresh token on the first authorization.
- **Callback URL must match** — The redirect_uri passed to the authorize endpoint must exactly match what's registered in Google Cloud Console. For dev: `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`.
- **htmx URL prefix** — Per KNOWLEDGE.md, all htmx URLs in app templates must use the `/app/{app_id}/` prefix so requests route through the app proxy. Example: `hx-post="/app/google-calendar/_fragments/connect/disconnect"`.
- **StateClient has no delete** — Only `set(key, value)`. Clearing auth state means setting keys to empty string (same pattern as Linear/GitHub).
- **Google Calendar list endpoint:** `GET https://www.googleapis.com/calendar/v3/users/me/calendarList` returns `{kind, etag, nextPageToken, nextSyncToken, items: [{id, summary, primary, accessRole, ...}]}`. The `id` is the calendar email address. `primary: true` marks the user's main calendar.

## Common Pitfalls

- **Missing `access_type=offline`** — Without this param in the authorize URL, Google returns only an access_token (no refresh_token). The app would break after 1 hour when the access token expires. Always include `access_type=offline`.
- **Refresh token not returned on re-auth** — Google only returns a refresh_token on the first consent. If the user disconnects and reconnects, they won't get a new refresh token unless `prompt=consent` is included in the authorize URL.
- **Token expiry storage format** — Store `token_expiry` as an ISO 8601 timestamp (not `expires_in` seconds). Compute at token receipt: `now + expires_in seconds`. The `refresh_if_expired()` helper compares against current time with a buffer (e.g. 5 minutes before expiry).
- **OAuth state parameter** — Must generate a random `state` value, store it in app state, and verify it matches on callback. Prevents CSRF attacks. Linear's auth has this pattern.
- **Calendar list pagination** — `calendarList.list` can return a `nextPageToken`. Most users have <20 calendars so pagination is unlikely, but the client should handle it.
- **The `default` calendar ID** — Some users may have a calendar ID like `primary` or their email address. The `calendarList` endpoint returns the actual ID, so use that — don't assume the format.

## Open Risks

- **Proxy query-param fix scope** — The fix is straightforward but touches infrastructure that all apps use. Must not break existing Linear/GitHub sync apps. The change only adds query params that were previously dropped, so it should be backward-compatible.
- **Google Cloud Console setup** — The admin needs to create an OAuth 2.0 Client ID in Google Cloud Console and enter the client ID/secret in the app's settings. This is a manual step that can't be automated. The app UI should provide clear instructions.
- **HttpClient domain-enforcement fix** — Changing the `else []` to `else network` means a manifest with `network: ["api.linear.app"]` will pass that list directly as `allowed_domains`. This is the correct behavior but should be verified against existing apps.

## Sources

- Google OAuth 2.0 protocol: `https://developers.google.com/identity/protocols/oauth2/web-server`
- Google Calendar API v3 calendarList: `https://developers.google.com/calendar/api/v3/reference/calendarList/list`
- Google token endpoint: `https://oauth2.googleapis.com/token`
- Google authorize endpoint: `https://accounts.google.com/o/oauth2/v2/auth`
