---
estimated_steps: 7
estimated_files: 2
---

# T02: Asana REST client with opt_fields, pagination, rate limit backoff, and unit tests

**Slice:** S01 — OAuth + project selection + custom field mapping UI
**Milestone:** M022

## Description

Build the Asana REST client that wraps the SDK HttpClient for authenticated requests to Asana's REST API. This client is the data access layer for all Asana interactions — workspace listing, project listing, section listing, custom field discovery, task listing, and mutations.

Key Asana-specific concerns not present in prior sync apps:
- **opt_fields parameter**: Every GET request must include `opt_fields=field1,field2,...` to get more than minimal data. Without it, responses return only `gid` and `resource_type`.
- **Response wrapper**: All responses are wrapped in `{"data": [...]}` (list) or `{"data": {...}}` (single resource).
- **Pagination**: Uses `next_page.offset` (not `nextPageToken` like Google or `@odata.nextLink` like Outlook). `next_page` is `null` when no more pages.
- **Rate limiting**: Cost-based (~1500 units/min). 429 responses include `Retry-After` header. Must sleep and retry.

Clone the structure from `apps/google-calendar/services/gcal_client.py` but adapt for Asana's API patterns.

## Steps

1. Create `apps/asana-sync/services/asana_client.py` with:
   - Constants: `ASANA_BASE_URL = os.environ.get("ASANA_API_URL", "https://app.asana.com/api/1.0")`, `MAX_PAGINATION_PAGES = 50`.
   - Exception hierarchy: `AsanaAPIError` (base, with message, status_code, response_body), `AsanaAuthError(AsanaAPIError)`, `AsanaRateLimitError(AsanaAPIError)` with `retry_after` attribute.
   - `AsanaClient` class with `__init__(self, http_client, state_client, client_id=None, client_secret=None)`.
   - `_get_headers()` → `{"Authorization": "Bearer {token}", "Accept": "application/json"}`.
   - `_request(method, url, *, allow_refresh=True, **kwargs)` — handles 401 (token refresh via `_handle_token_refresh()` + single retry), 429 (parse `Retry-After`, raise `AsanaRateLimitError`), 403, 5xx. Extracts `data` from response JSON wrapper.
   - `_handle_token_refresh()` — acquires asyncio.Lock, reads refresh_token from state, POSTs to ASANA_TOKEN_URL, stores new access_token.
   - `_paginated_get(url, opt_fields=None, params=None)` → list. Handles `next_page.offset` pagination. Builds `?opt_fields=...&limit=100&offset=...` query string.

2. Implement resource endpoints:
   - `get_workspaces()` → list of workspace dicts (gid, name). `GET /workspaces`. opt_fields: `name`.
   - `get_projects(workspace_gid)` → list of project dicts (gid, name, archived). `GET /workspaces/{gid}/projects`. opt_fields: `name,archived`. Filter out archived projects.
   - `get_sections(project_gid)` → list of section dicts (gid, name). `GET /projects/{gid}/sections`. opt_fields: `name`.
   - `get_custom_fields(project_gid)` → list of custom field dicts. `GET /projects/{gid}/custom_field_settings`. opt_fields: `custom_field,custom_field.name,custom_field.resource_subtype,custom_field.enum_options,custom_field.enum_options.name`. Returns the `custom_field` sub-object from each setting.
   - `get_tasks(project_gid, opt_fields, modified_since=None)` → list of task dicts. `GET /projects/{gid}/tasks`. Modified_since as ISO 8601 query param for incremental sync.
   - `get_subtasks(task_gid, opt_fields)` → list of subtask dicts. `GET /tasks/{gid}/subtasks`.
   - `get_user_me()` → user dict (gid, email, name). `GET /users/me`. opt_fields: `name,email`. Used for PAT verification and connection identity.
   - `patch_task(task_gid, data)` → updated task dict. `PATCH /tasks/{gid}` with JSON body.
   - `add_task_to_section(section_gid, task_gid)` → None. `POST /sections/{gid}/addTask` with `{"data": {"task": task_gid}}`. Used for section-based status push.

3. Create `backend/tests/test_asana_client.py` using the importlib module-loading pattern from `backend/tests/test_gcal_client.py`:
   - MockResponse with `json()`, `text`, `status_code`, `headers`.
   - MockHttpClient that records calls and returns pre-configured responses.
   - MockStateClient for token retrieval.
   - Test `_get_headers`: returns Bearer token from state, raises AsanaAuthError when no token.
   - Test `_request`: 200 success (extracts data wrapper), 401→refresh→retry, 401→refresh fail→raise, 403 raise, 429 raise with Retry-After, 5xx raise.
   - Test `_paginated_get`: single page, multi-page with next_page.offset, empty results.
   - Test `get_workspaces`: returns workspace list with correct opt_fields.
   - Test `get_projects`: returns non-archived projects, correct opt_fields.
   - Test `get_sections`: returns section list with correct opt_fields.
   - Test `get_custom_fields`: extracts custom_field from settings, correct opt_fields.
   - Test `get_user_me`: returns user data, auth header correct.
   - Test `patch_task`: sends correct JSON body.
   - Test `add_task_to_section`: sends correct nested data.
   - Target: ≥20 tests.

4. Verify: `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_client.py -v`

5. Verify auth tests still pass: `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py -v`

6. Verify no syntax errors: `python -c "import ast; ast.parse(open('apps/asana-sync/services/asana_client.py').read())"`

7. Commit: `feat(asana-sync): add REST client with opt_fields, pagination, rate limit backoff`

## Must-Haves

- [ ] AsanaClient with _request() handling 401/429/403/5xx
- [ ] opt_fields parameter support on all GET endpoints
- [ ] Offset-based pagination via next_page.offset
- [ ] Response data wrapper extraction ({"data": ...})
- [ ] Rate limit backoff via Retry-After header on 429
- [ ] Token refresh on 401 with asyncio.Lock and single retry
- [ ] Endpoints: get_workspaces, get_projects, get_sections, get_custom_fields, get_tasks, get_subtasks, get_user_me, patch_task, add_task_to_section
- [ ] Exception hierarchy: AsanaAPIError → AsanaAuthError, AsanaRateLimitError
- [ ] Env var override for ASANA_API_URL (mock testability)
- [ ] ≥20 unit tests covering all client paths

## Verification

- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_client.py -v` — ≥20 tests pass
- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_asana_auth.py -v` — still pass (no regression)
- `python -c "import ast; ast.parse(open('apps/asana-sync/services/asana_client.py').read())"` — no syntax errors

## Inputs

- `apps/asana-sync/services/auth.py` (from T01) — auth module importing AsanaAuthError
- `apps/google-calendar/services/gcal_client.py` — client pattern to clone (request, refresh, pagination, exception hierarchy)
- `backend/tests/test_gcal_client.py` — test pattern with importlib, MockResponse, MockHttpClient
- `.gsd/milestones/M022/M022-RESEARCH.md` — Asana API specifics (opt_fields, pagination via next_page.offset, data wrapper, rate limiting)

## Observability Impact

- **Logger:** `logging.getLogger("asana.sync.client")` — logs token refresh events, API error status codes, pagination progress
- **Diagnostics:** `AsanaAPIError`, `AsanaAuthError`, `AsanaRateLimitError` all carry `.status_code` and `.response_body` attributes for structured error inspection
- **Rate limit visibility:** `AsanaRateLimitError.retry_after` exposes the Retry-After value from 429 responses — callers can log/surface the backoff window
- **Token refresh lock:** `AsanaClient._refreshing` asyncio.Lock prevents concurrent refresh races — contention visible via lock.locked() state
- **Failure inspection:** Any `_request()` call that fails exposes the HTTP status and raw response body through the exception hierarchy — no silent swallowing of error details

## Expected Output

- `apps/asana-sync/services/asana_client.py` — complete REST client (~350 lines) with opt_fields, pagination, rate limit, all endpoints
- `backend/tests/test_asana_client.py` — ≥20 unit tests proving all client paths
