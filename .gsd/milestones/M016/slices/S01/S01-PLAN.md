# S01: OAuth + App Skeleton + Linear Client

**Goal:** Installable Linear Sync app that authenticates with Linear via OAuth or API key, proves API connectivity, and displays workspace info and team list on a settings page.
**Demo:** User installs the Linear Sync app from admin, opens the settings page, enters an API key (or completes OAuth), sees their Linear workspace name and a list of teams — proving auth, API connectivity, and the app skeleton work end-to-end through the App Platform.

## Must-Haves

- `apps/linear-sync/manifest.yaml` with correct permissions (object.create, object.patch, body.set, body.diff, edge.create), network domain (api.linear.app), background tasks, SPARQL read, and UI page declaration
- `apps/linear-sync/app.py` with App SDK skeleton: settings page fragment, OAuth callback route, lifecycle hooks
- `apps/linear-sync/services/linear_client.py` with `LinearClient` class: authenticated GraphQL queries, pagination, error handling, automatic token refresh on 401
- OAuth code exchange flow: redirect to Linear → receive code → exchange for access+refresh tokens → store via StateClient
- API key auth: user enters personal API key in settings → stored via StateClient → verified with `{ viewer { id name } }` query
- Settings page shows: connection status, workspace name, team list (fetched from Linear API) when connected; connect form when disconnected
- `apps/linear-sync/requirements.txt` — empty or minimal (httpx already in SDK)
- Unit tests for LinearClient (query construction, pagination, token refresh, error handling) and auth state management

## Proof Level

- This slice proves: integration (OAuth/API key → Linear API through App Platform proxy and SDK clients)
- Real runtime required: yes (app must install and run in Docker stack; Linear API calls can be against mock or real endpoint)
- Human/UAT required: yes (manual OAuth flow with real Linear workspace for full verification)

## Verification

- `cd backend && python -m pytest tests/test_linear_client.py -v` — LinearClient unit tests pass (query construction, pagination assembly, token refresh logic, error handling, auth state helpers)
- App installs successfully in Docker stack: `docker compose exec api python -c "..."` or admin UI shows linear-sync in app list
- Settings page loads at `/app/linear-sync/_fragments/connect` and shows the connect form

## Observability / Diagnostics

- Runtime signals: `logging.getLogger("linear_sync")` logs at DEBUG level for API calls, token refresh, auth state changes
- Inspection surfaces: StateClient keys `access_token`, `refresh_token`, `workspace_id`, `workspace_name`, `auth_method` — queryable via SPARQL on `urn:sempkm:app:linear-sync:state` graph
- Failure visibility: LinearClient raises typed exceptions (`LinearAuthError`, `LinearRateLimitError`, `LinearAPIError`) with status codes and response bodies. Settings page shows error message on failed connection test.
- Redaction constraints: OAuth tokens and API keys stored in StateClient must never appear in logs. Log key names only.

## Integration Closure

- Upstream surfaces consumed: App SDK (`sempkm_app_sdk`), App Platform (install/proxy/scheduler), `bpkm:Task` type definition (read-only, for future slices)
- New wiring introduced in this slice: `apps/linear-sync/` directory with manifest, entrypoint, and templates; registered as installable app via existing platform discovery
- What remains before the milestone is truly usable end-to-end: S02 (pull sync — actually creating Task objects), S03 (push sync), S04 (E2E tests + docs)

## Tasks

- [x] **T01: App manifest, skeleton, and settings page shell** `est:1h`
  - Why: Creates the installable app foundation — manifest, entrypoint, templates, requirements. Nothing else can run without this.
  - Files: `apps/linear-sync/manifest.yaml`, `apps/linear-sync/app.py`, `apps/linear-sync/requirements.txt`, `apps/linear-sync/frontend/templates/connect.html`, `apps/linear-sync/frontend/templates/connect_status.html`, `apps/linear-sync/frontend/static/styles.css`
  - Do: Create manifest with appId `linear-sync`, permissions for all command types needed by S02/S03 (object.create, object.patch, body.set, body.diff, edge.create), network domain `api.linear.app`, `linear.app` (for OAuth), sparql read, background tasks for `poll-tasks`. Create app.py with `App("linear-sync")` instance, settings page fragment route (`/_fragments/connect`), placeholder OAuth callback route (`/_fragments/oauth-callback`), startup/shutdown lifecycle hooks. Create connect.html template with two auth modes: API key input form + OAuth connect button. Create minimal CSS. Follow test-app manifest and app.py patterns exactly.
  - Verify: `cat apps/linear-sync/manifest.yaml | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin.read()); print('valid')"` parses cleanly. `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read()); print('ok')"` compiles.
  - Done when: manifest.yaml, app.py, requirements.txt, templates, and CSS all exist with correct structure matching test-app patterns.

- [x] **T02: LinearClient with GraphQL queries, pagination, token refresh, and unit tests** `est:2h`
  - Why: Core API client that all subsequent slices depend on. Pure logic with no platform dependencies — ideal for thorough unit testing.
  - Files: `apps/linear-sync/services/__init__.py`, `apps/linear-sync/services/linear_client.py`, `backend/tests/test_linear_client.py`
  - Do: Implement `LinearClient` class with: (1) constructor taking `http_client` (SDK HttpClient) and `state_client` (SDK StateClient) for token retrieval; (2) `async _get_headers()` that reads access_token from state and builds Authorization header; (3) `async query(graphql_query, variables)` that POSTs to `https://api.linear.app/graphql` with auth headers, handles errors; (4) `async _handle_token_refresh()` that exchanges refresh_token for new access+refresh tokens via `https://api.linear.app/oauth/token`; (5) automatic retry on 401 with token refresh (once only, to prevent loops); (6) `async query_paginated(graphql_query, variables, path_to_nodes, path_to_pageinfo)` for cursor-based pagination; (7) convenience methods: `async get_viewer()` → `{ viewer { id name email } }`, `async get_teams()` → team list, `async get_workspace()` → organization info. Include typed exception classes: `LinearAuthError`, `LinearRateLimitError`, `LinearAPIError`. Write comprehensive unit tests using pytest + httpx MockTransport: test query construction, test pagination assembly, test 401→refresh→retry flow, test rate limit (429) handling with retry-after, test error response parsing, test get_viewer/get_teams convenience methods. Use importlib to load the module from apps/ directory.
  - Verify: `cd backend && python -m pytest tests/test_linear_client.py -v` — all tests pass.
  - Done when: LinearClient handles authenticated queries, pagination, token refresh, and error cases; ≥15 unit tests pass.

- [ ] **T03: OAuth flow, API key auth, and connected settings page with workspace + team display** `est:2h`
  - Why: Wires LinearClient into the app's settings page. Completes the slice demo: user authenticates and sees workspace info.
  - Files: `apps/linear-sync/app.py`, `apps/linear-sync/services/auth.py`, `apps/linear-sync/frontend/templates/connect.html`, `apps/linear-sync/frontend/templates/connect_status.html`, `backend/tests/test_linear_auth.py`
  - Do: (1) Create `auth.py` with pure helper functions: `build_oauth_authorize_url(client_id, redirect_uri, state)`, `async exchange_code(http_client, code, client_id, client_secret, redirect_uri)` → returns `{access_token, refresh_token, expires_in}`, `async store_tokens(state_client, tokens, auth_method)` → saves to StateClient keys, `async get_auth_status(state_client)` → returns dict with `connected`, `auth_method`, `workspace_name`, `workspace_id`. (2) In app.py, implement the connect fragment route: if connected → render connect_status.html with workspace name + team list (fetched via LinearClient.get_teams()); if disconnected → render connect.html with API key form + OAuth button. (3) Implement API key save route (`POST /_fragments/connect/api-key`): store key → test with get_viewer() → store workspace info → return updated status fragment with HX-Trigger. (4) Implement OAuth callback route (`GET /_fragments/oauth-callback`): extract code+state params → exchange_code → store_tokens → fetch workspace info → redirect to settings. (5) Implement disconnect route (`POST /_fragments/connect/disconnect`): clear all auth state keys. (6) Update templates: connect.html with htmx forms for API key + OAuth URL link; connect_status.html showing workspace name, auth method badge, team list table, disconnect button. (7) Write unit tests for auth.py pure functions: build_oauth_authorize_url, exchange_code response parsing, store_tokens key mapping, get_auth_status with various states. Unit tests for app route handlers using test client.
  - Verify: `cd backend && python -m pytest tests/test_linear_auth.py -v` — all tests pass. Templates render without Jinja errors (checked via python import of jinja2 + render).
  - Done when: API key auth flow works end-to-end in tests (enter key → verify → show workspace); OAuth helpers tested; settings page shows connected state with workspace name and team list; disconnect clears state. ≥12 unit tests pass.

## Files Likely Touched

- `apps/linear-sync/manifest.yaml`
- `apps/linear-sync/app.py`
- `apps/linear-sync/requirements.txt`
- `apps/linear-sync/services/__init__.py`
- `apps/linear-sync/services/linear_client.py`
- `apps/linear-sync/services/auth.py`
- `apps/linear-sync/frontend/templates/connect.html`
- `apps/linear-sync/frontend/templates/connect_status.html`
- `apps/linear-sync/frontend/static/styles.css`
- `backend/tests/test_linear_client.py`
- `backend/tests/test_linear_auth.py`
