---
id: T03
parent: S01
milestone: M016
provides:
  - Auth helpers module (auth.py) with OAuth URL builder, code exchange, token storage, workspace info, connection status, and state cleanup
  - Real route implementations in app.py replacing all T01 placeholders — API key auth, OAuth callback, connect fragment, disconnect
  - Enhanced templates with htmx forms, error display, connection status with auth method badge, and team table
  - 17 unit tests covering all auth helpers and template rendering
key_files:
  - apps/linear-sync/services/auth.py
  - apps/linear-sync/app.py
  - apps/linear-sync/frontend/templates/connect.html
  - apps/linear-sync/frontend/templates/connect_status.html
  - apps/linear-sync/frontend/static/styles.css
  - backend/tests/test_linear_auth.py
key_decisions:
  - Used try/except import chain in auth.py for LinearAuthError to support both runtime (app dir on sys.path) and test (importlib spec_from_file_location) contexts
  - StateClient has no delete — clear_auth_state sets keys to empty string; get_connection_status uses bool(auth_method) not is-not-None check
  - OAuth section shows "not yet configured" placeholder — full OAuth flow requires client_id/secret configuration which is a future slice concern
patterns_established:
  - Auth state keys centralized in AUTH_STATE_KEYS tuple for consistent clear/status operations
  - Route error handling pattern: catch LinearAuthError specifically for auth failures, generic Exception for unexpected errors, always render HTML (never crash the settings page)
  - _oauth_result_page() generates standalone HTML for the OAuth callback redirect flow (not an htmx fragment)
observability_surfaces:
  - "linear_sync.auth" logger — INFO on token store/clear, WARNING on exchange failures
  - "linear_sync" logger — INFO on connect/disconnect, WARNING on verification failures
  - StateClient keys: access_token, refresh_token, api_key, auth_method, workspace_name, workspace_id
  - HX-Trigger "linearConnected" header on successful API key connection for UI refresh
duration: 18min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: OAuth flow, API key auth, and connected settings page with workspace + team display

**Implemented auth helpers, real route handlers, enhanced templates with htmx forms and team display, and 17 unit tests — completing the S01 settings page auth flow**

## What Happened

Created `auth.py` with six pure helper functions: `build_oauth_authorize_url`, `exchange_code`, `store_auth_tokens`, `store_workspace_info`, `get_connection_status`, and `clear_auth_state`. These handle all state management through the SDK StateClient.

Replaced all four placeholder routes in `app.py` with real implementations. The connect fragment reads connection status and renders either the connect form (disconnected) or the status page with teams (connected). API key auth verifies the key via `get_viewer()`, fetches org info, and stores everything. The OAuth callback exchanges codes for tokens. Disconnect clears all state.

Enhanced both templates: `connect.html` now has htmx-powered API key form with loading indicator and error display. `connect_status.html` shows a connected badge, auth method badge, workspace name, and team table with disconnect button.

One import challenge: the app runner puts the app dir on sys.path (absolute imports like `from services.auth import ...`), but tests load modules via `spec_from_file_location`. Solved with a try/except import chain in `auth.py` that tries `services.linear_client` first, then `linear_client` as fallback.

## Verification

- `cd backend && python -m pytest tests/test_linear_auth.py -v` — 17/17 pass
- `cd backend && python -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` — 39/39 pass (22 + 17)
- Template rendering verified via Jinja2: both templates render cleanly with all context combinations

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -m pytest tests/test_linear_auth.py -v` | 0 | ✅ pass | 0.08s |
| 2 | `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` | 0 | ✅ pass | 0.07s |
| 3 | Template render check (connect.html error=None, connect_status.html with teams) | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python3 -m pytest tests/test_linear_client.py -v` (slice check) | 0 | ✅ pass | 0.03s |

## Diagnostics

- **Auth state inspection:** Check stored state via `await ctx.state.get("auth_method")` — returns `"api_key"`, `"oauth"`, or `""` (disconnected)
- **Logger:** `logging.getLogger("linear_sync.auth")` for token storage/clearing, `logging.getLogger("linear_sync")` for route-level operations
- **Error visibility:** All auth failures render as `.alert-error` divs in the connect form — never silent
- **Route check:** `GET /_fragments/connect` returns either connect form or status page depending on state

## Deviations

- OAuth section shows "not yet configured" placeholder instead of a live OAuth link — the plan noted OAuth requires client_id/secret configuration, which isn't implemented yet. The `exchange_code` helper and OAuth callback route are fully implemented and tested, but the UI link to start the OAuth flow is deferred until OAuth config UI exists.
- Added `_oauth_result_page()` helper for OAuth callback — generates standalone HTML rather than an htmx fragment since the OAuth redirect lands on a new page, not within the settings fragment.

## Known Issues

- StateClient has no `delete` operation — `clear_auth_state` sets keys to empty string `""`, not `None`. The `get_connection_status` function uses `bool()` check to handle this correctly.
- OAuth flow end-to-end requires client_id/secret configuration (future slice work) — the helpers and callback route are ready but the initiation UI is a placeholder.

## Files Created/Modified

- `apps/linear-sync/services/auth.py` — new auth helper module (199 lines) with OAuth URL builder, code exchange, token/workspace storage, connection status, and state cleanup
- `apps/linear-sync/app.py` — replaced all 4 placeholder routes with real implementations using LinearClient and auth helpers (271 lines)
- `apps/linear-sync/frontend/templates/connect.html` — enhanced with htmx API key form, loading indicator, error display, OAuth placeholder section
- `apps/linear-sync/frontend/templates/connect_status.html` — enhanced with connection badge, auth method badge, workspace name, team table
- `apps/linear-sync/frontend/static/styles.css` — added alert-error, auth-method-badge, form-actions, htmx-indicator, oauth-note, zebra striping styles
- `backend/tests/test_linear_auth.py` — 17 unit tests covering all auth helpers and template rendering
- `.gsd/milestones/M016/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
