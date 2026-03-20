---
id: T01
parent: S01
milestone: M021
provides:
  - CalDAV auth module with HTTP Basic credential management
  - CalDAVClient with WebDAV XML protocol (PROPFIND/REPORT/PUT/DELETE)
  - Full discovery chain (server → principal → calendar-home → calendar-list)
  - XML builders and multistatus response parser
key_files:
  - apps/caldav-calendar/services/caldav_client.py
  - apps/caldav-calendar/services/auth.py
  - backend/tests/test_caldav_client.py
  - backend/tests/test_caldav_auth.py
key_decisions:
  - Renamed auth.test_connection to auth.check_connection to prevent pytest collection conflict
  - Home collection filtered by resolving relative hrefs against absolute home_url before comparison
patterns_established:
  - CalDAV XML builders use stdlib xml.etree.ElementTree with registered namespace prefixes (d/c/cs)
  - _parse_multistatus handles both propstat-based and direct-status responses (for sync-collection deleted resources)
  - CalDAVClient uses http_client.request("PROPFIND", ...) for WebDAV methods not in standard HTTP
observability_surfaces:
  - caldav.auth logger — connection test results, credential storage events
  - caldav.client logger — PROPFIND/REPORT/GET/PUT/DELETE request URLs and response status codes, discovery chain progress
  - CalDAVError exception hierarchy with status_code and response_body on every error
duration: 30m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build CalDAV auth module and CalDAVClient with WebDAV XML protocol

**Built CalDAV protocol layer: auth module with HTTP Basic credential management, CalDAVClient with XML request builders/parsers, full discovery chain, and event CRUD with ETag concurrency — 62 unit tests passing.**

## What Happened

Created five files implementing the CalDAV protocol layer:

1. **`caldav_client.py`** (~400 lines) — Exception hierarchy (CalDAVError → CalDAVAuthError/NotFound/Conflict), XML namespace constants (DAV:/caldav:/calendarserver), three XML builder functions (_build_propfind_xml, _build_sync_collection_xml, _build_calendar_query_xml), multistatus XML response parser, and CalDAVClient class with PROPFIND/REPORT low-level methods, the full discovery chain (discover_principal → discover_calendar_home → discover_calendars), and event operations (get_events, get_event, put_event, delete_event).

2. **`auth.py`** (~130 lines) — HTTP Basic auth helpers: get_auth_headers (base64 encoding), store_credentials (with trailing slash stripping), check_connection (PROPFIND probe), get_connection_status (never exposes password), clear_auth_state.

3. **`test_caldav_auth.py`** (20 tests) — Covers base64 encoding with special characters, credential storage/trimming, connection testing for 207/401/404/500/exception paths, connection status with password redaction, state clearing.

4. **`test_caldav_client.py`** (42 tests) — Covers XML builders (propfind, sync-collection, calendar-query), XML parser (single/multiple/nested/deleted/empty/malformed), discovery chain with both Fastmail (absolute hrefs) and Nextcloud (relative hrefs) server variants, event operations (get/put/delete with ETag handling), and error handling (401/403/404/500, missing credentials).

Key fix during implementation: the Nextcloud discovery chain returns relative hrefs in Depth:1 responses — the home collection filter needed to urljoin before comparing, not string-match raw hrefs.

## Verification

- `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` — 62 passed in 0.15s
- All XML builders produce valid XML parseable by ET.fromstring()
- Password never appears in get_connection_status() output (tested explicitly)
- Discovery chain handles both absolute (Fastmail) and relative (Nextcloud) hrefs
- PUT sends If-None-Match: * for creates, If-Match for updates
- DELETE with 412 raises CalDAVConflictError, 404 silently succeeds

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` | 0 | ✅ pass | 0.15s |
| 2 | XML builder validity check (ET.fromstring on all 3 builders) | 0 | ✅ pass | <1s |
| 3 | Password redaction check (get_connection_status keys) | 0 | ✅ pass | <1s |

## Diagnostics

- **Logs:** `caldav.auth` logger emits connection test results and credential storage events. `caldav.client` logger emits method+URL+status for every WebDAV request, plus discovery chain progress.
- **Errors:** CalDAVError carries status_code and response_body. CalDAVAuthError on 401/403 or missing credentials. CalDAVNotFoundError on 404. CalDAVConflictError on 409/412 (ETag mismatch).
- **Inspection:** `get_connection_status()` returns {connected, auth_method, server_url, username} — password never included.

## Deviations

- Renamed `test_connection` → `check_connection` in auth.py to prevent pytest from collecting it as a test function (pytest scans all files in the path, including app source via importlib).
- Task plan specified `test_connection` as the function name — this is a naming-only change, behavior is identical.

## Known Issues

- `get_events()` currently returns `new_sync_token=None` because the sync-token for the next request lives in the multistatus root element, outside the per-response entries. The parser only extracts per-response data. A follow-up in S02 will need to extract the root-level `<sync-token>` from sync-collection responses.

## Files Created/Modified

- `apps/caldav-calendar/services/__init__.py` — Empty package init
- `apps/caldav-calendar/services/auth.py` — HTTP Basic auth helpers (credential storage, connection test, status)
- `apps/caldav-calendar/services/caldav_client.py` — CalDAVClient with WebDAV XML protocol
- `backend/tests/test_caldav_auth.py` — 20 auth unit tests
- `backend/tests/test_caldav_client.py` — 42 client unit tests with canned XML for Fastmail/Nextcloud variants
