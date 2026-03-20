# S01: Auth + CalDAV Client + Calendar Discovery — UAT

**Milestone:** M021
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is a contract-verification slice — all work is proven by unit tests against canned XML responses. No live CalDAV server needed. Runtime integration is deferred to S04 E2E.

## Preconditions

- Working directory: `/home/james/Code/SemPKM/.gsd/worktrees/M018`
- Python venv at `backend/.venv/` with dependencies installed
- No Docker stack or live server required

## Smoke Test

Run the full unit test suite:
```bash
backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v
```
Expected: 62 tests pass, 0 failures, <1s.

## Test Cases

### 1. Auth module — credential storage and retrieval

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py::TestStoreCredentials -v`
2. **Expected:** 3 tests pass — credentials stored with correct keys, trailing slashes trimmed from server URL

### 2. Auth module — base64 encoding correctness

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py::TestGetAuthHeaders -v`
2. **Expected:** 4 tests pass — correct base64 encoding for normal, special-char username, unicode password, and empty password cases

### 3. Auth module — connection test probes server

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py::TestTestConnection -v`
2. **Expected:** 6 tests pass — PROPFIND sent, 207 succeeds, 401/404/500 fail with appropriate messages, exceptions handled gracefully

### 4. Auth module — password never exposed in status

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_auth.py::TestGetConnectionStatus -v`
2. **Expected:** 4 tests pass — status dict contains `connected`, `server_url`, `username` but NEVER `password`

### 5. CalDAV client — XML builder correctness

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestBuildPropfindXml backend/tests/test_caldav_client.py::TestBuildSyncCollectionXml backend/tests/test_caldav_client.py::TestBuildCalendarQueryXml -v`
2. **Expected:** 7 tests pass — XML valid, correct namespaces (DAV:, caldav:, calendarserver), correct property elements

### 6. CalDAV client — multistatus XML parser

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestParseMultistatus -v`
2. **Expected:** 8 tests pass — single/multiple responses, nested href, calendar-data extraction, deleted resources (direct status without propstat), empty body returns [], malformed XML returns [], supported-calendar-component-set parsing

### 7. CalDAV client — discovery chain with server variants

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestDiscoverPrincipal backend/tests/test_caldav_client.py::TestDiscoverCalendarHome backend/tests/test_caldav_client.py::TestDiscoverCalendars -v`
2. **Expected:** 6 tests pass — principal discovery (absolute + relative URL), calendar home discovery (absolute + relative), full chain from server root → calendar list, VEVENT-only filtering, Fastmail variant (absolute hrefs), Nextcloud variant (relative hrefs resolved via urljoin)

### 8. CalDAV client — event operations with ETag

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestGetEvents backend/tests/test_caldav_client.py::TestGetEvent backend/tests/test_caldav_client.py::TestPutEvent backend/tests/test_caldav_client.py::TestDeleteEvent -v`
2. **Expected:** 10 tests pass — get_events with/without sync-token, deleted events included, etag+data extraction, single event GET, PUT with If-None-Match (create) and If-Match (update), 412 conflict raises CalDAVConflictError, DELETE with etag, 404 on delete silently succeeds

### 9. CalDAV client — error handling

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestPropfindErrors backend/tests/test_caldav_client.py::TestReportErrors backend/tests/test_caldav_client.py::TestAuthNotConfigured -v`
2. **Expected:** 6 tests pass — 401/403 → CalDAVAuthError, 404 → CalDAVNotFoundError, 500 → CalDAVError, missing credentials → CalDAVAuthError

### 10. App manifest valid YAML

1. Run `backend/.venv/bin/python -c "import yaml; m = yaml.safe_load(open('apps/caldav-calendar/manifest.yaml')); assert m['appId'] == 'caldav-calendar'; assert m['network'] == ['*']; print('OK')"` 
2. **Expected:** Prints `OK` — valid YAML, correct appId and network wildcard

### 11. htmx URL prefix audit

1. Run `grep -r "hx-post\|hx-get\|hx-delete\|hx-put" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"`
2. **Expected:** Zero output (exit code 1) — all htmx URLs correctly prefixed with `/app/caldav-calendar/`

### 12. App entry point has all expected route handlers

1. Run `grep -c "async def" apps/caldav-calendar/app.py`
2. **Expected:** At least 8 (6 route handlers + 2 task handlers)

## Edge Cases

### Nextcloud vs Fastmail discovery chain divergence

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestDiscoverCalendars::test_fastmail_variant backend/tests/test_caldav_client.py::TestDiscoverCalendars::test_nextcloud_variant -v`
2. **Expected:** Both pass — Fastmail returns absolute hrefs, Nextcloud returns relative hrefs. Parser handles both via urljoin resolution.

### Deleted resources in sync-collection REPORT

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestParseMultistatus::test_deleted_resource_without_propstat -v`
2. **Expected:** Pass — deleted resources return `<d:status>HTTP/1.1 404 Not Found</d:status>` without a `<d:propstat>` wrapper. Parser extracts href + status correctly.

### ETag conflict on PUT (412 Precondition Failed)

1. Run `backend/.venv/bin/python -m pytest backend/tests/test_caldav_client.py::TestPutEvent::test_conflict_raises -v`
2. **Expected:** Pass — 412 response raises CalDAVConflictError with status_code=412.

## Failure Signals

- Any test failure in the 62-test suite indicates a regression in XML generation, parsing, or auth logic
- `grep -r "password" apps/caldav-calendar/services/auth.py | grep -v "store\|clear\|get_state\|#\|log"` showing password in get_connection_status output means a credential leak
- `grep -r "hx-" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returning any results means broken proxy routing

## Requirements Proved By This UAT

- none fully validated — S01 proves contract correctness (XML protocol, discovery chain, auth helpers) via unit tests. Full requirement validation requires live runtime proof in S04 E2E.

## Not Proven By This UAT

- Live CalDAV server connectivity (real PROPFIND/REPORT against a running server)
- App installation via Admin > Applications
- Calendar selection UI rendering in the workspace
- Sync engine integration (pull/push — S02/S03)
- ETag-based concurrency under real race conditions

## Notes for Tester

- All tests use mocked HTTP clients and canned XML — no network access required
- The `check_connection` function (formerly `test_connection`) was renamed to avoid pytest collection. If you see a pytest warning about collecting a test from `auth.py`, the rename may have regressed.
- `get_events()` currently returns `new_sync_token=None` — this is a known limitation, not a bug. S02 will add sync-token extraction.
