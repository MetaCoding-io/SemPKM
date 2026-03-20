---
estimated_steps: 8
estimated_files: 5
---

# T01: Build CalDAV auth module and CalDAVClient with WebDAV XML protocol

**Slice:** S01 — Auth + CalDAV Client + Calendar Discovery
**Milestone:** M021

## Description

Build the CalDAV protocol layer — the core technical risk for this milestone. CalDAV uses XML-over-HTTP (PROPFIND, REPORT, PUT, DELETE) unlike the JSON REST APIs of all prior sync apps (Google, Outlook, Linear, GitHub, Todoist). This task creates the `auth.py` module for HTTP Basic credential management and the `caldav_client.py` module for WebDAV XML request generation, response parsing, and the full CalDAV discovery chain.

Follow the structural patterns from `apps/google-calendar/services/auth.py` and `apps/google-calendar/services/gcal_client.py` — same importlib-based module loading for tests, same exception hierarchy, same async patterns with SDK HttpClient. The key differences are: (1) auth is HTTP Basic instead of OAuth 2.0 (simpler), (2) requests/responses are XML instead of JSON (novel), (3) the discovery chain is multi-step PROPFIND instead of single REST endpoint.

**Decision D224** mandates hand-crafted XML with stdlib `xml.etree.ElementTree` + httpx via SDK HttpClient — no `caldav` library.

## Steps

1. **Create `apps/caldav-calendar/services/__init__.py`** — empty init file for the services package.

2. **Create `apps/caldav-calendar/services/auth.py`** — HTTP Basic auth helpers:
   - Constants: `AUTH_STATE_KEYS = ("server_url", "username", "password", "auth_method")`
   - `get_auth_headers(username: str, password: str) -> dict[str, str]` — returns `{"Authorization": "Basic <base64>"}` header using `base64.b64encode(f"{username}:{password}".encode()).decode()`
   - `async def store_credentials(state_client, server_url: str, username: str, password: str) -> None` — stores URL/username/password and sets auth_method="basic" via StateClient
   - `async def test_connection(http_client, server_url: str, username: str, password: str) -> dict` — sends PROPFIND to server_url with Depth:0, returns `{"success": True/False, "message": "...", "status_code": int}`. The PROPFIND body should request `DAV:current-user-principal`. A 207 response means success.
   - `async def get_connection_status(state_client) -> dict` — returns `{"connected": bool, "auth_method": str|None, "server_url": str|None, "username": str|None}` (never returns password)
   - `async def clear_auth_state(state_client) -> None` — sets all AUTH_STATE_KEYS to empty string
   - `CalDAVAuthError` import from `caldav_client` (same try/except pattern as Google Calendar)
   - Logger: `logging.getLogger("caldav.auth")`

3. **Create `apps/caldav-calendar/services/caldav_client.py`** — WebDAV/CalDAV client:
   - **Exception hierarchy**: `CalDAVError` (base), `CalDAVAuthError` (401/403), `CalDAVNotFoundError` (404), `CalDAVConflictError` (409/412 for ETag mismatch). Each stores `message`, `status_code`, `response_body`.
   - **XML namespace constants**:
     ```python
     DAV_NS = "DAV:"
     CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
     CS_NS = "http://calendarserver.org/ns/"
     ```
   - **XML builder helpers** (module-level functions):
     - `_build_propfind_xml(properties: list[tuple[str, str]]) -> str` — builds a PROPFIND XML body requesting the given namespace+property pairs. Example input: `[("DAV:", "current-user-principal")]`. Uses `xml.etree.ElementTree` to generate namespace-aware XML.
     - `_build_sync_collection_xml(sync_token: str | None, props: list[tuple[str, str]] | None = None) -> str` — builds a sync-collection REPORT body. Default props: `[(DAV_NS, "getetag"), (CALDAV_NS, "calendar-data")]`. Empty sync_token means full sync.
     - `_build_calendar_query_xml() -> str` — builds a calendar-query REPORT body requesting all VEVENTs with getetag and calendar-data.
   - **XML response parser**:
     - `_parse_multistatus(xml_text: str) -> list[dict]` — parses a WebDAV multistatus response. Returns list of dicts with `{"href": str, "status": str, "properties": dict}`. The properties dict has keys like `"getetag"`, `"calendar-data"`, `"displayname"`, `"current-user-principal"`, etc. Handle both `<propstat>` with `<status>` and direct `<status>` elements (for sync-collection deleted resources that have `<status>HTTP/1.1 404 Not Found</status>` instead of `<propstat>`).
   - **CalDAVClient class**:
     - `__init__(self, http_client, state_client)` — stores SDK HttpClient and StateClient references.
     - `async def _get_auth_headers(self) -> dict` — reads username/password from state, calls `get_auth_headers()` from auth module. Raises `CalDAVAuthError` if not configured.
     - `async def _propfind(self, url: str, body: str, depth: str = "0") -> list[dict]` — sends PROPFIND request with Content-Type: application/xml, Depth header. Parses response with `_parse_multistatus()`. Handles 207 (success), 401 (auth error), 403, 404, 5xx.
     - `async def _report(self, url: str, body: str) -> list[dict]` — sends REPORT request, same response handling as _propfind.
     - `async def discover_principal(self, server_url: str) -> str` — PROPFIND on server_url for `current-user-principal`, follows `href` to get principal URL. Handles relative URLs by resolving against server_url.
     - `async def discover_calendar_home(self, principal_url: str) -> str` — PROPFIND on principal_url for `calendar-home-set`, returns home URL.
     - `async def discover_calendars(self, server_url: str) -> list[dict]` — full chain: discover_principal → discover_calendar_home → PROPFIND Depth:1 on home for calendar list. Returns list of `{"href": str, "displayname": str, "ctag": str|None, "supported_components": list[str]}`. Filters to only VEVENT-supporting calendars.
     - `async def get_events(self, calendar_url: str, sync_token: str | None = None) -> tuple[list[dict], str | None]` — REPORT sync-collection (if sync_token) or calendar-query (if no token). Returns `(events, new_sync_token)` where each event is `{"href": str, "etag": str, "calendar_data": str, "status": str}`. For sync-collection, deleted resources have `status="HTTP/1.1 404 Not Found"` with no calendar_data.
     - `async def get_event(self, event_url: str) -> dict` — GET single .ics resource, returns `{"etag": str, "calendar_data": str}`.
     - `async def put_event(self, event_url: str, ics_data: str, etag: str | None = None) -> str` — PUT .ics data. If etag provided, sends `If-Match: "etag"` (update). If etag is None, sends `If-None-Match: *` (create). Returns new ETag from response. Raises `CalDAVConflictError` on 412.
     - `async def delete_event(self, event_url: str, etag: str | None = None) -> None` — DELETE resource. If etag provided, sends `If-Match: "etag"`. Raises `CalDAVConflictError` on 412.
   - URL resolution: use `urllib.parse.urljoin()` for resolving relative hrefs against base URLs.

4. **Create `backend/tests/test_caldav_auth.py`** — auth unit tests using importlib loading pattern from `backend/tests/test_gcal_auth.py`:
   - Load `caldav_client.py` first (for CalDAVAuthError), then `auth.py` via importlib
   - MockResponse class and MockStateClient class (dict-based async get/set)
   - MockHttpClient class with configurable responses
   - Tests (target ≥15):
     - `test_get_auth_headers_basic` — correct base64 encoding
     - `test_get_auth_headers_special_chars` — handles special characters in username/password
     - `test_store_credentials` — all 4 state keys set correctly
     - `test_store_credentials_trims_trailing_slash` — server_url trailing slash stripped
     - `test_test_connection_success` — 207 response returns `{"success": True}`
     - `test_test_connection_auth_failure` — 401 returns `{"success": False, "message": "..."}`
     - `test_test_connection_not_found` — 404 returns `{"success": False}`
     - `test_test_connection_server_error` — 500 returns `{"success": False}`
     - `test_test_connection_sends_propfind` — verifies PROPFIND method and XML body
     - `test_get_connection_status_connected` — returns correct dict when credentials present
     - `test_get_connection_status_disconnected` — returns `{"connected": False}` when no auth_method
     - `test_get_connection_status_never_returns_password` — password field not in returned dict
     - `test_clear_auth_state` — all keys set to empty string
     - `test_clear_auth_state_clears_all_keys` — verify each AUTH_STATE_KEY is cleared

5. **Create `backend/tests/test_caldav_client.py`** — client unit tests using importlib loading pattern:
   - Load `caldav_client.py` via importlib
   - Canned XML response strings for: multistatus with principal, multistatus with calendar-home-set, multistatus with calendar list (Depth:1), sync-collection response with changed/added/deleted events, simple propstat response
   - Cover multiple server variants: Fastmail-style (absolute hrefs), Nextcloud-style (relative hrefs)
   - MockHttpClient that records calls and returns canned responses based on URL/method
   - Tests (target ≥35):
     - XML builder tests:
       - `test_build_propfind_xml_single_prop` — correct namespace and element structure
       - `test_build_propfind_xml_multi_props` — multiple properties from different namespaces
       - `test_build_sync_collection_xml_with_token` — sync-token included in body
       - `test_build_sync_collection_xml_no_token` — empty sync-token for full sync
       - `test_build_calendar_query_xml` — VEVENT comp-filter present
     - XML parser tests:
       - `test_parse_multistatus_single_response` — one response element
       - `test_parse_multistatus_multiple_responses` — multiple response elements
       - `test_parse_multistatus_with_calendar_data` — extracts .ics text content
       - `test_parse_multistatus_deleted_resource` — status 404 without propstat
       - `test_parse_multistatus_nested_href` — extracts href from nested element
       - `test_parse_multistatus_empty_body` — handles empty or malformed XML gracefully
     - Discovery chain tests:
       - `test_discover_principal_absolute_url` — extracts principal URL from PROPFIND response
       - `test_discover_principal_relative_url` — resolves relative href against server URL
       - `test_discover_calendar_home_absolute` — extracts calendar-home-set href
       - `test_discover_calendar_home_relative` — resolves relative path
       - `test_discover_calendars_full_chain` — calls principal → home → list, returns calendar dicts
       - `test_discover_calendars_filters_vevent_only` — skips non-VEVENT calendars (e.g., VTODO-only)
       - `test_discover_calendars_fastmail_variant` — canned Fastmail XML response structure
       - `test_discover_calendars_nextcloud_variant` — canned Nextcloud XML response structure
     - Event operation tests:
       - `test_get_events_with_sync_token` — sends sync-collection REPORT, returns events + new token
       - `test_get_events_no_sync_token` — sends calendar-query REPORT for full sync
       - `test_get_events_includes_deleted` — deleted events have status 404 and no calendar_data
       - `test_get_event_single` — GET request returns etag + calendar_data
       - `test_put_event_create` — sends If-None-Match: *, returns new etag
       - `test_put_event_update` — sends If-Match with quoted etag
       - `test_put_event_conflict` — 412 raises CalDAVConflictError
       - `test_delete_event_with_etag` — sends If-Match header
       - `test_delete_event_conflict` — 412 raises CalDAVConflictError
     - Error handling tests:
       - `test_propfind_401_raises_auth_error` — CalDAVAuthError on 401
       - `test_propfind_403_raises_auth_error` — CalDAVAuthError on 403
       - `test_propfind_404_raises_not_found` — CalDAVNotFoundError on 404
       - `test_propfind_500_raises_error` — CalDAVError on 500
       - `test_report_401_raises_auth_error` — CalDAVAuthError on REPORT 401
       - `test_get_auth_headers_not_configured` — CalDAVAuthError when no credentials

6. **Verify all tests pass**: `python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v`

## Must-Haves

- [ ] CalDAVClient generates correct PROPFIND XML with DAV:/caldav:/calendarserver namespaces
- [ ] CalDAVClient parses multistatus XML responses correctly (including nested propstat, calendar-data, deleted resources)
- [ ] Discovery chain resolves: server_url → principal → calendar-home → calendar-list
- [ ] Discovery handles both absolute and relative href values in XML responses
- [ ] PUT/DELETE send correct If-Match/If-None-Match headers for ETag concurrency
- [ ] Auth module stores URL/username/password, produces correct Basic auth header, tests connection via PROPFIND
- [ ] Connection status never exposes password
- [ ] ≥50 unit tests pass across both test files

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` — all tests pass, ≥50 total
- Every XML builder produces valid XML parseable by ET.fromstring()
- Every XML parser test uses canned multi-line XML strings representative of real CalDAV server responses

## Observability Impact

- Signals added: `caldav.auth` logger (connection test results), `caldav.client` logger (discovery chain steps, request methods, response status codes)
- How a future agent inspects this: check logger output for step-by-step discovery progress; CalDAVError exceptions carry status_code and response_body
- Failure state exposed: CalDAVAuthError (bad credentials), CalDAVNotFoundError (wrong URL), CalDAVConflictError (ETag mismatch on PUT/DELETE)

## Inputs

- `apps/google-calendar/services/auth.py` — reference pattern for auth module structure (StateClient-based storage, connection status dict)
- `apps/google-calendar/services/gcal_client.py` — reference pattern for client class structure (exception hierarchy, authenticated requests, SDK HttpClient usage)
- `backend/tests/test_gcal_auth.py` — reference pattern for importlib-based module loading in tests, MockResponse/MockStateClient helpers
- `backend/tests/test_gcal_client.py` — reference pattern for client unit tests with canned responses
- `.gsd/milestones/M021/M021-RESEARCH.md` — CalDAV protocol details (XML namespaces, discovery chain, sync-collection REPORT format, iCalendar field extraction patterns)

## Expected Output

- `apps/caldav-calendar/services/__init__.py` — empty package init
- `apps/caldav-calendar/services/auth.py` — HTTP Basic auth helpers (~120 lines)
- `apps/caldav-calendar/services/caldav_client.py` — CalDAVClient with XML protocol (~350 lines)
- `backend/tests/test_caldav_auth.py` — ≥15 auth unit tests (~250 lines)
- `backend/tests/test_caldav_client.py` — ≥35 client unit tests (~600 lines)
