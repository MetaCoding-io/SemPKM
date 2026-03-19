---
id: S01
parent: M016
milestone: M016
provides:
  - Installable Linear Sync app skeleton with manifest, entrypoint, settings page templates, and scoped CSS
  - LinearClient class with authenticated GraphQL queries, cursor-based pagination, automatic OAuth token refresh on 401, typed exceptions (LinearAuthError, LinearRateLimitError, LinearAPIError, LinearQueryError)
  - Auth helpers module (OAuth URL builder, code exchange, token storage, workspace info, connection status, state cleanup)
  - Real route implementations for API key auth, OAuth callback, connect fragment, disconnect — replacing T01 placeholders
  - 39 unit tests (22 LinearClient + 17 auth/template rendering)
requires:
  - slice: none
    provides: First slice in M016
affects:
  - S02 (pull sync consumes LinearClient for GraphQL queries + StateClient token storage for authenticated API calls)
  - S03 (push sync consumes LinearClient mutation methods)
key_files:
  - apps/linear-sync/manifest.yaml
  - apps/linear-sync/app.py
  - apps/linear-sync/services/linear_client.py
  - apps/linear-sync/services/auth.py
  - apps/linear-sync/frontend/templates/connect.html
  - apps/linear-sync/frontend/templates/connect_status.html
  - apps/linear-sync/frontend/static/styles.css
  - backend/tests/test_linear_client.py
  - backend/tests/test_linear_auth.py
key_decisions:
  - D199 — Both OAuth and API key auth supported; API key for quick local setup, OAuth for multi-user production
  - D201 — httpx direct via SDK HttpClient for GraphQL, no gql library
  - D203 — importlib.util.spec_from_file_location to load app modules from apps/ into backend test suite
  - StateClient has no delete operation — clear_auth_state sets keys to empty string; get_connection_status uses bool() check
  - Copy variables dict on each query execution to prevent mutation during pagination cursor chaining
patterns_established:
  - importlib + MockHttpClient/MockStateClient pattern for testing SDK-dependent app code without platform runtime
  - App route pattern: /_fragments/connect for settings page, /_fragments/connect/{action} for sub-actions
  - Two-template pattern: connect.html (disconnected) and connect_status.html (connected), swapped via htmx
  - Auth state keys centralized in AUTH_STATE_KEYS tuple for consistent clear/status operations
  - Route error handling: catch LinearAuthError for auth failures, generic Exception for unexpected, always render HTML
observability_surfaces:
  - Logger "linear_sync.client" — DEBUG for GraphQL requests, INFO for token refresh events, WARNING for rate limits
  - Logger "linear_sync.auth" — INFO on token store/clear, WARNING on exchange failures
  - Logger "linear_sync" — INFO on connect/disconnect and lifecycle, WARNING on verification failures
  - Typed exceptions carry status_code, message, response_body for structured error diagnostics
  - StateClient keys: access_token, refresh_token, api_key, auth_method, workspace_name, workspace_id
  - HX-Trigger "linearConnected" header on successful API key connection for UI refresh
drill_down_paths:
  - .gsd/milestones/M016/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M016/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M016/slices/S01/tasks/T03-SUMMARY.md
duration: 63min
verification_result: passed
completed_at: 2026-03-18
---

# S01: OAuth + App Skeleton + Linear Client

**Installable Linear Sync app with manifest, LinearClient (GraphQL queries, pagination, token refresh), auth helpers (OAuth + API key), and settings page showing connection status, workspace info, and team list — 39 unit tests passing.**

## What Happened

Three tasks built the Linear Sync app foundation bottom-up.

**T01** created the app skeleton: manifest.yaml declaring all permissions needed by downstream slices (object.create, object.patch, body.set, body.diff, edge.create, sparql read, network access to api.linear.app and linear.app), Python entrypoint with `App("linear-sync")` instance, four placeholder fragment routes, poll-tasks background task, startup/shutdown lifecycle hooks, and two settings page templates (disconnected form + connected status). CSS fully scoped under `.linear-sync-settings`.

**T02** built `LinearClient` (~270 lines) — the core API client all subsequent slices depend on. Exception hierarchy with `LinearAuthError` (401/403), `LinearRateLimitError` (429 with retry_after), `LinearQueryError` (GraphQL-level errors). Auth header resolution checks access_token first (OAuth), falls back to api_key. Query execution handles 401 (token refresh + single retry), 429 (rate limit), and all other HTTP/GraphQL errors. Token refresh acquires asyncio.Lock to prevent concurrent refreshes and stores new tokens via StateClient. Cursor-based pagination with dot-delimited paths and 50-page safety limit. Convenience methods: get_viewer(), get_teams(), get_organization(). Two bugs found and fixed during testing: pagination variable mutation across mock calls (fixed by copying variables dict) and retry-path 401s falling through to generic handler (fixed by handling 401 before generic check).

**T03** wired everything together: auth.py with six pure helper functions (build_oauth_authorize_url, exchange_code, store_auth_tokens, store_workspace_info, get_connection_status, clear_auth_state), real route implementations replacing all T01 placeholders, and enhanced templates with htmx forms, error display, connection status badges, and team table. Import compatibility between runtime (app dir on sys.path) and tests (importlib) solved with try/except import chain.

## Verification

- `cd backend && python -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` — **39/39 tests pass** (22 LinearClient + 17 auth/template)
- Manifest parses as valid YAML with all required permissions (5 commands, 2 network domains, sparql read, backgroundTasks, ui page)
- All Python files compile via `ast.parse` — confirmed
- Template rendering verified via Jinja2 for all context combinations (connected/disconnected, error/no-error, teams/empty-teams)
- All 11 files exist at expected paths — confirmed

## Requirements Advanced

- SYNC-01 (auth) — OAuth helpers and API key auth flow fully implemented and unit-tested. OAuth code exchange function ready; API key verification proves connectivity via get_viewer(). Both auth methods store credentials via StateClient. Not yet validated (requires Docker stack runtime verification).

## Requirements Validated

- None — this slice proves auth logic via unit tests but runtime integration (Docker install, actual Linear API connectivity) is deferred to UAT / S02 integration.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- OAuth UI shows "not yet configured" placeholder instead of a live OAuth link. The exchange_code helper and callback route are fully implemented and tested, but the initiation UI requires client_id/secret configuration which is a future concern. This is noted in the plan as acceptable.
- StateClient has no delete operation — clear_auth_state sets keys to empty string rather than removing them. get_connection_status handles this correctly via bool() check.

## Known Limitations

- OAuth flow cannot be initiated from the settings page yet — requires client_id/secret configuration (settings UI for OAuth credentials not built). The code exchange and callback handling are ready.
- No E2E Playwright test for this slice — pure unit test coverage only. Docker stack integration verification is deferred to S04.
- No user guide docs for this slice — docs are planned for S04 as the terminal slice.

## Follow-ups

- S02 will consume LinearClient.query_paginated() for bulk issue fetching and LinearClient.get_teams() for team selection UI.
- S03 will need LinearClient mutation methods (issue update GraphQL) — not yet implemented; LinearClient currently only has read queries.
- OAuth initiation UI (client_id/secret input fields, redirect URL display) should be added when OAuth is prioritized.

## Files Created/Modified

- `apps/linear-sync/manifest.yaml` — App manifest with full permissions, task, and UI page config
- `apps/linear-sync/app.py` — App entrypoint with real route implementations (connect, api-key, oauth-callback, disconnect) and lifecycle hooks (271 lines)
- `apps/linear-sync/requirements.txt` — Empty dependency file (SDK provides httpx)
- `apps/linear-sync/services/__init__.py` — Empty package init for services module
- `apps/linear-sync/services/linear_client.py` — LinearClient with GraphQL queries, pagination, token refresh, typed exceptions (~270 lines)
- `apps/linear-sync/services/auth.py` — Auth helpers: OAuth URL builder, code exchange, token/workspace storage, connection status, state cleanup (199 lines)
- `apps/linear-sync/frontend/templates/connect.html` — Disconnected state: htmx API key form with error display, OAuth placeholder
- `apps/linear-sync/frontend/templates/connect_status.html` — Connected state: status badge, auth method badge, workspace name, team table, disconnect button
- `apps/linear-sync/frontend/static/styles.css` — Scoped CSS for settings page components including alerts, badges, tables, htmx indicators
- `backend/tests/test_linear_client.py` — 22 unit tests covering query construction, auth header, errors, token refresh, pagination, convenience methods
- `backend/tests/test_linear_auth.py` — 17 unit tests covering all auth helpers and template rendering

## Forward Intelligence

### What the next slice should know
- LinearClient is imported via `from services.linear_client import LinearClient` at runtime (app dir on sys.path) or via `importlib.util.spec_from_file_location` in tests. The MockHttpClient/MockStateClient pattern in test_linear_client.py is the reference for testing.
- StateClient keys are: `access_token`, `refresh_token`, `api_key`, `auth_method` ("api_key" or "oauth"), `workspace_name`, `workspace_id`. S02 will add `last_sync_at` and `sync_teams`.
- LinearClient.query_paginated() returns a flat list of all nodes across pages. It takes dot-delimited paths like "issues.nodes" and "issues.pageInfo" to navigate the GraphQL response structure.
- The app registers a `poll-tasks` scheduled task that currently returns a noop dict. S02 will implement the actual sync logic there.

### What's fragile
- The try/except import chain in auth.py (`from services.linear_client import ...` with fallback to `from linear_client import ...`) works but is a code smell. If the app's directory structure changes, both import paths need updating.
- StateClient empty-string-as-None pattern means any code checking state values must use `bool()` or truthy checks, never `is not None`.

### Authoritative diagnostics
- `cd backend && python -m pytest tests/test_linear_client.py tests/test_linear_auth.py -v` — 39 tests in <0.1s, covers all pure logic
- `python3 -c "import yaml; yaml.safe_load(open('apps/linear-sync/manifest.yaml'))"` — manifest validity
- Logger `linear_sync.client` at DEBUG level shows every GraphQL request payload and response status

### What assumptions changed
- Plan assumed OAuth UI would be fully wired — in practice, the OAuth code exchange and callback are implemented but the initiation link is a placeholder since client_id/secret config UI doesn't exist yet. All OAuth logic is tested and ready for when the config UI is added.
