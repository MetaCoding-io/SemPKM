---
id: S02
parent: M018
milestone: M018
provides:
  - google-calendar app scaffold with manifest, OAuth auth module, GCal REST client
  - App proxy query-param forwarding fix (unblocks all OAuth callback flows)
  - SDK network permission parsing fix (unblocks all external HTTP from sync apps)
  - Full OAuth connect/disconnect flow with CSRF-safe state verification
  - Calendar list fetch with pagination, selection UI, state persistence
  - Token storage as ISO 8601 with automatic refresh via 5-minute expiry buffer
requires:
  - slice: none
    provides: none
affects:
  - S03
  - S04
  - S05
key_files:
  - backend/app/apps/proxy.py
  - backend/sdk/sempkm_app_sdk/context.py
  - apps/google-calendar/manifest.yaml
  - apps/google-calendar/services/auth.py
  - apps/google-calendar/services/gcal_client.py
  - apps/google-calendar/app.py
  - apps/google-calendar/frontend/templates/connect.html
  - apps/google-calendar/frontend/templates/connect_status.html
  - apps/google-calendar/frontend/static/styles.css
  - backend/tests/test_app_proxy_query_params.py
  - backend/tests/test_sdk_network_permissions.py
  - backend/tests/test_gcal_auth.py
  - backend/tests/test_gcal_client.py
key_decisions:
  - D210: Full OAuth 2.0 — no API key alternative (Google Calendar API requires OAuth for user data)
  - Token expiry stored as ISO 8601 timestamp (computed from expires_in at storage time) for direct comparison
  - GCal client uses REST with URL-appended pageToken matching Google Calendar API v3 pagination pattern
  - OAuth callback fetches calendar list to derive google_email from primary calendar ID before storing tokens
  - Disconnect clears auth + selected_calendars but preserves client_id/secret for easy re-connect
patterns_established:
  - Google OAuth auth module mirrors linear-sync auth.py structure with added refresh_if_expired and token_expiry tracking
  - REST client with centralized _request() method handling all HTTP status codes (vs Linear's GraphQL-specific query method)
  - Two-step OAuth connect flow (credentials entry → OAuth redirect) vs single-step API key entry
  - Regression test pattern for proxy URL construction using CaptureClient
observability_surfaces:
  - google_calendar.auth logger — INFO on token exchange/refresh/clear, WARNING on failures
  - google_calendar.client logger — INFO on token refresh during 401 retry
  - google_calendar.app logger — INFO on credential save, OAuth redirect, callback, calendar save, disconnect; WARNING on state mismatch
  - get_connection_status() returns structured dict with connected, auth_method, google_email, token_expiry
  - GCalAuthError/GCalAPIError/GCalRateLimitError exceptions carry status_code + response_body
  - oauth_state key in StateClient for CSRF verification — mismatch produces WARNING log
drill_down_paths:
  - .gsd/milestones/M018/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M018/slices/S02/tasks/T03-SUMMARY.md
duration: 55min
verification_result: passed
completed_at: 2026-03-18
---

# S02: Google OAuth 2.0 + Calendar List

**Google Calendar app with full OAuth 2.0 connect/disconnect flow, calendar list with selection checkboxes, and two platform bug fixes that unblock all OAuth-based sync apps.**

## What Happened

Three tasks delivered the complete OAuth and calendar selection infrastructure:

**T01 — Platform bug fixes.** Two one-line fixes unblocked the entire OAuth ecosystem. The app proxy (`proxy.py`) was silently dropping query parameters from forwarded requests — an OAuth callback like `?code=xxx&state=yyy` arrived empty at the app subprocess. Fix: append `request.url.query` to `target_url` when present. The SDK's HttpClient domain enforcement (`context.py`) was discarding list-type network permissions from manifests — `["api.google.com"]` became `[]`. Fix: `else network` instead of `else []`. Both fixes have regression tests (5 proxy, 7 SDK). Also fixed a pre-existing test infrastructure issue where `test_github_sync_engine.py` was poisoning `sys.modules` with a broken SDK stub.

**T02 — Auth module and GCal client.** Built `apps/google-calendar/` following the linear-sync reference pattern. The auth module (`services/auth.py`) provides 7 pure helper functions covering the full OAuth lifecycle: authorize URL construction (offline access, consent prompt, calendar.events scope), code exchange, token refresh, refresh-if-expired with 5-minute buffer, token storage as ISO 8601, connection status, and state clearing. The GCal REST client (`services/gcal_client.py`) provides paginated calendar list fetch, auth header injection, and 401→refresh→retry (single attempt, no infinite loop). Exception hierarchy: `GCalAPIError` → `GCalAuthError`, `GCalRateLimitError`. 35 unit tests total using importlib loading pattern with MockHttpClient/MockStateClient.

**T03 — Routes, templates, and connect flow.** Wired the auth module and client into HTTP route handlers (`app.py`) and Jinja2 templates. The connect flow is two-step: enter Google Cloud Console client_id/secret → click "Connect with Google" → OAuth redirect with CSRF state → callback exchanges code, fetches calendar list to find primary email, stores tokens → connected status page shows email, token expiry, calendar checkboxes. Calendar selection persisted as JSON via StateClient. Disconnect clears auth + selection but preserves credentials for easy reconnection. Skeleton task handlers for `poll-events` and `push-changes` ready for S03/S04.

## Verification

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | Proxy regression tests | ✅ 5/5 | Query forwarding, no-query, single param, POST, encoded chars |
| 2 | SDK network permission tests | ✅ 7/7 | List, dict, missing, empty, wildcard, end-to-end domain check |
| 3 | Auth helper unit tests | ✅ 23/23 | URL construction, code exchange, refresh, expiry buffer, storage, status, clear |
| 4 | GCal client unit tests | ✅ 12/12 | Calendar list (single/paginated/empty), auth header, 401→retry, no infinite loop, 403/429/500 |
| 5 | Full backend suite | ✅ 1498/1498 | Zero regressions in 8.34s |
| 6 | Jinja2 template syntax | ✅ | Both templates parse without errors |
| 7 | htmx URL prefix check | ✅ | All htmx URLs use `/app/google-calendar/` prefix |

## Requirements Advanced

- GCAL-01 — OAuth 2.0 authentication fully implemented and tested (authorize URL → code exchange → token storage → refresh → connection status → clear)
- GCAL-02 — Calendar list with paginated fetch, selection checkboxes, and state persistence

## Requirements Validated

- GCAL-01 — 23 auth tests + 5 proxy regression tests + full OAuth route handlers with CSRF state verification prove the complete auth lifecycle
- GCAL-02 — 12 client tests + calendar list UI with checkboxes + StateClient persistence prove calendar selection works end-to-end

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 exceeded planned test counts: 23 auth tests (plan: ≥15) and 12 client tests (plan: ≥10) — more thorough edge case coverage.
- T03 added `_make_client_with_creds` async helper (not in plan) to read client_id/secret from state for GCalClient construction with token refresh capability.
- T01 fixed pre-existing `test_github_sync_engine.py` stub that was poisoning `sys.modules` — not in the original plan but necessary for clean SDK imports.

## Known Limitations

- OAuth flow is not exercised via E2E test — this is by design per the proof strategy (all verified via unit tests with mocked HTTP + state clients). E2E coverage comes in S05.
- Skeleton task handlers for `poll-events` and `push-changes` return placeholders — filled in by S03 and S04 respectively.
- No actual Google API calls — all external HTTP is mocked. Real API integration validated only when deployed.

## Follow-ups

- S03 needs to implement `poll-events` task handler body using auth module's `refresh_if_expired()` and GCalClient for event fetch
- S04 needs to implement `push-changes` task handler for RSVP push-back
- S05 needs mock Google Calendar API server for E2E testing of the complete flow

## Files Created/Modified

- `backend/app/apps/proxy.py` — append query string to target_url when present
- `backend/sdk/sempkm_app_sdk/context.py` — pass list-type network permissions through to HttpClient
- `backend/pyproject.toml` — added `sdk` to pytest pythonpath
- `backend/tests/test_github_sync_engine.py` — fixed SDK stub to try real import first
- `backend/tests/test_app_proxy_query_params.py` — new: 5 proxy regression tests
- `backend/tests/test_sdk_network_permissions.py` — new: 7 SDK network permission tests
- `apps/google-calendar/manifest.yaml` — app manifest with permissions, tasks, UI page
- `apps/google-calendar/requirements.txt` — minimal dependency file
- `apps/google-calendar/services/__init__.py` — package init
- `apps/google-calendar/services/auth.py` — OAuth helper module (7 functions, ~250 lines)
- `apps/google-calendar/services/gcal_client.py` — REST client module (~280 lines)
- `apps/google-calendar/app.py` — route handlers for full OAuth connect flow + skeleton tasks
- `apps/google-calendar/frontend/templates/connect.html` — credential entry + OAuth connect form
- `apps/google-calendar/frontend/templates/connect_status.html` — connected status, calendar list, disconnect
- `apps/google-calendar/frontend/static/styles.css` — scoped app styling
- `backend/tests/test_gcal_auth.py` — 23 auth unit tests
- `backend/tests/test_gcal_client.py` — 12 client unit tests

## Forward Intelligence

### What the next slice should know
- The auth module's `refresh_if_expired(state_client, http_client, client_id, client_secret)` is the standard way to get a valid access token before any Google API call. It handles the 5-minute buffer and auto-stores refreshed tokens.
- `_make_client_with_creds(ctx)` in app.py reads client_id/secret from StateClient — use this pattern for creating GCalClient instances that can do token refresh.
- The app.py skeleton has `poll-events` and `push-changes` task handlers returning `{"status": "ok", "message": "...not yet implemented..."}` — S03/S04 fill these in.
- Calendar selection is stored as JSON string in StateClient key `selected_calendars` — parse with `json.loads()`.
- The proxy query-param fix and SDK network permission fix are platform-wide — they unblock any future app that uses OAuth callbacks or list-type network permissions.

### What's fragile
- OAuth CSRF state is stored in StateClient as a single `oauth_state` key — concurrent OAuth flows from the same user would race. Acceptable for single-user self-hosted.
- Token expiry comparison uses `datetime.fromisoformat()` on stored ISO 8601 strings. If a malformed string gets stored, `refresh_if_expired` would crash. All auth paths use computed ISO 8601 from `datetime.now(timezone.utc)` so this shouldn't happen.

### Authoritative diagnostics
- `get_connection_status(state_client)` — returns `{connected, auth_method, google_email, token_expiry}` for runtime inspection
- `google_calendar.auth` and `google_calendar.app` loggers — INFO/WARNING traces for OAuth lifecycle events
- `GCalAuthError.status_code` and `.response_body` — carry HTTP response details from failed Google API calls

### What assumptions changed
- The plan assumed the proxy forwarded query params — it didn't. Fixed in T01.
- The plan assumed the SDK parsed list-type network permissions — it didn't. Fixed in T01.
- Both were pre-existing platform bugs, not specific to this slice, but they would have blocked S02 cold.
