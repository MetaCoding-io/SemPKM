# S01: OAuth + project selection + custom field mapping UI

**Goal:** User installs Asana Sync, authenticates via OAuth 2.0 or PAT, selects workspaces/projects, discovers custom fields, and configures status/priority mapping with persisted configuration. No sync yet — but the novel "configure before sync" pattern is proven end-to-end with unit tests.

**Demo:** After install, user enters OAuth credentials (or PAT), completes auth, selects projects to sync, then configures status mapping (choosing between completed-only, custom enum field, or section-based) and priority mapping (custom enum field). Configuration persists across page reloads.

## Must-Haves

- OAuth 2.0 auth flow (authorize URL → code exchange → token storage → refresh on expiry) with PAT fallback
- Asana REST client with opt_fields parameter support, offset-based pagination, and 429 rate limit backoff via Retry-After header
- Workspace listing and project listing via REST client
- Project selection UI with checkbox multi-select, persisted via StateClient
- Custom field discovery from selected projects (enum fields for status/priority, number fields for story points)
- Status source selection: completed_only / custom_field / section — with enum-value-to-bpkm mapping table when custom_field or section selected
- Priority mapping: custom enum field selection with value-to-bpkm mapping table
- Story points mapping: number field selection
- All configuration persisted as JSON in StateClient
- Auth unit tests (≥20 tests covering OAuth URL, code exchange, refresh, expiry buffer, PAT verification, store/clear/status)
- Client unit tests (≥20 tests covering opt_fields, pagination, rate limit, 401→refresh, workspace/project/section/custom-field endpoints)

## Proof Level

- This slice proves: contract + integration
- Real runtime required: no (unit tests with mocks prove the configuration flow)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py -v` — ≥20 tests pass
- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_client.py -v` — ≥20 tests pass
- All app files present: `apps/asana-sync/manifest.yaml`, `apps/asana-sync/app.py`, `apps/asana-sync/services/{auth,asana_client,__init__}.py`, `apps/asana-sync/frontend/templates/{connect,connect_status}.html`, `apps/asana-sync/frontend/static/styles.css`
- manifest.yaml has appId "asana-sync", network permissions for app.asana.com, OAuth task entries
- connect_status.html has project selection checkboxes, status source radio buttons, status mapping table, priority mapping table, story points field selector

## Observability / Diagnostics

- Runtime signals: `logging.getLogger("asana.sync.auth")` and `logging.getLogger("asana.sync.client")` structured log messages for auth events and API errors
- Inspection surfaces: `get_connection_status()` returns auth state dict; StateClient keys for all mapping configuration
- Failure visibility: `AsanaAuthError` and `AsanaRateLimitError` exceptions with status_code and response_body; token_expiry as ISO 8601 timestamp
- Redaction constraints: access_token, refresh_token, client_secret never logged — only key names and masked previews in UI

## Integration Closure

- Upstream surfaces consumed: App Platform SDK (`sempkm_app_sdk.App`, `AppContext`, `StateClient`, `HttpClient`), Asana REST API (`app.asana.com/api/1.0/`)
- New wiring introduced in this slice: `apps/asana-sync/` directory with manifest, app entrypoint, services, and templates — registered via manifest.yaml for platform discovery
- What remains before the milestone is truly usable end-to-end: S02 (pull sync with field transforms), S03 (push sync), S04 (E2E tests + docs)

## Tasks

- [x] **T01: Asana OAuth/PAT auth module with unit tests** `est:1h30m`
  - Why: Foundation for all API access — proves both OAuth 2.0 flow and PAT fallback authentication pattern
  - Files: `apps/asana-sync/services/__init__.py`, `apps/asana-sync/services/auth.py`, `backend/tests/test_asana_auth.py`
  - Do: Clone Google Calendar OAuth pattern (build_authorize_url, exchange_code, refresh_access_token, refresh_if_expired with 5-min buffer, store_auth_tokens, get_connection_status, clear_auth_state). Add PAT verification via GET /users/me. Asana OAuth URLs: authorize=`https://app.asana.com/-/oauth_authorize`, token=`https://app.asana.com/-/oauth_token`. No explicit scopes (implicit). Env var overrides for mock server testability (ASANA_TOKEN_URL). Write ≥20 unit tests using importlib loading pattern from test_gcal_auth.py.
  - Verify: `python -m pytest backend/tests/test_asana_auth.py -v` — ≥20 tests pass
  - Done when: Auth module handles OAuth URL building, code exchange, token refresh with expiry buffer, PAT verification, state storage/clear/status — all proven by unit tests

- [x] **T02: Asana REST client with opt_fields, pagination, rate limit backoff, and unit tests** `est:1h30m`
  - Why: Data access layer for all Asana API interactions — workspace listing, project listing, section listing, custom field discovery, task listing. The opt_fields pattern and rate limit handling are Asana-specific concerns not present in prior sync apps.
  - Files: `apps/asana-sync/services/asana_client.py`, `backend/tests/test_asana_client.py`
  - Do: Build AsanaClient class with: `_request()` method handling 401→refresh, 429→Retry-After backoff, `_get_headers()` for Bearer token. Implement endpoints: `get_workspaces()`, `get_projects(workspace_gid)`, `get_sections(project_gid)`, `get_custom_fields(project_gid)`, `get_tasks(project_gid, opt_fields, modified_since)`, `get_subtasks(task_gid, opt_fields)`, `get_user(user_gid)`, `patch_task(task_gid, data)`, `add_task_to_section(section_gid, task_gid)`. All endpoints use opt_fields parameter. Pagination via `next_page.offset` in response. Base URL: `https://app.asana.com/api/1.0`. Response data in `{"data": ...}` wrapper. Exception hierarchy: AsanaAPIError → AsanaAuthError, AsanaRateLimitError. Write ≥20 unit tests.
  - Verify: `python -m pytest backend/tests/test_asana_client.py -v` — ≥20 tests pass
  - Done when: Client handles opt_fields on every request, paginates via offset, backs off on 429 with Retry-After, refreshes token on 401, and provides typed exceptions — all proven by unit tests

- [x] **T03: App shell with manifest, OAuth/PAT routes, project selection, and connect templates** `est:1h30m`
  - Why: Wires auth module and client into the App Platform as a running app — proves OAuth redirect flow, PAT entry, workspace/project selection with persistence, and disconnect. Creates the visual foundation for T04's field mapping UI.
  - Files: `apps/asana-sync/manifest.yaml`, `apps/asana-sync/app.py`, `apps/asana-sync/requirements.txt`, `apps/asana-sync/frontend/templates/connect.html`, `apps/asana-sync/frontend/templates/connect_status.html`, `apps/asana-sync/frontend/static/styles.css`
  - Do: Create manifest.yaml (appId "asana-sync", network ["app.asana.com"], commands [object.create, object.patch, body.set, edge.create], sparql read, backgroundTasks, tasks poll-tasks/push-changes at 15m, ui pages settings with icon "check-square" nav "apps"). Create app.py with routes: `/_fragments/connect` (GET — connect form or status), `/_fragments/connect/credentials` (POST — save OAuth client_id/secret), `/_fragments/connect/asana` (POST — initiate OAuth redirect), `/_fragments/oauth-callback` (GET — code exchange with CSRF state), `/_fragments/connect/pat` (POST — PAT auth via client.get_user_me()), `/_fragments/connect/disconnect` (POST), `/_fragments/settings/projects` (POST — save selected projects). Build connect.html with two-section layout (OAuth credentials + connect button, divider, PAT entry form). Build initial connect_status.html with connection status badge, workspace/project selection checkboxes, and disconnect button. All htmx URLs must use `/app/asana-sync/` prefix per KNOWLEDGE.md. Create styles.css cloned from linear-sync with asana-sync class names. Create requirements.txt (markdownify).
  - Verify: All files exist with correct structure. `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` succeeds. manifest.yaml valid YAML with correct appId.
  - Done when: App shell is complete with OAuth + PAT dual auth flow, project selection UI, and all routes — ready for T04 to add field mapping sections

- [x] **T04: Custom field discovery, mapping UI, and configuration persistence** `est:2h`
  - Why: This is the novel, highest-risk piece — the "configure before sync" pattern that distinguishes Asana from all prior sync apps. Must discover custom fields from selected projects, present status/priority/story-points mapping UI, and persist configuration.
  - Files: `apps/asana-sync/app.py`, `apps/asana-sync/frontend/templates/connect_status.html`
  - Do: Add route `/_fragments/settings/discover-fields` (POST — calls client.get_custom_fields() for each selected project, unions results, returns field mapping UI). Add route `/_fragments/settings/field-mapping` (POST — saves status_source, status_field_gid, status_mapping JSON, priority_field_gid, priority_mapping JSON, story_points_field_gid). Extend connect_status.html with: (1) Status Mapping section — radio group for status_source (completed_only/custom_field/section), conditional display of enum field selector when custom_field selected, section name list when section selected, mapping table with bpkm:taskStatus dropdown for each enum option or section name; (2) Priority Mapping section — enum field selector, mapping table with bpkm:priority dropdown for each enum option; (3) Story Points section — number field selector. "Discover Fields" button triggers field discovery after projects are selected. All configuration round-trips through StateClient as JSON. Update `_render_connect_status()` to load and display persisted mapping configuration.
  - Verify: connect_status.html contains status source radios, mapping tables, priority section, story points selector. `python -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` succeeds. StateClient keys documented in code.
  - Done when: Full field mapping configuration flow works: discover fields → select status source → map enum values → select priority field → map priority values → select story points field → all persisted in StateClient — the "configure before sync" pattern is complete

## Files Likely Touched

- `apps/asana-sync/manifest.yaml`
- `apps/asana-sync/requirements.txt`
- `apps/asana-sync/app.py`
- `apps/asana-sync/services/__init__.py`
- `apps/asana-sync/services/auth.py`
- `apps/asana-sync/services/asana_client.py`
- `apps/asana-sync/frontend/templates/connect.html`
- `apps/asana-sync/frontend/templates/connect_status.html`
- `apps/asana-sync/frontend/static/styles.css`
- `backend/tests/test_asana_auth.py`
- `backend/tests/test_asana_client.py`
