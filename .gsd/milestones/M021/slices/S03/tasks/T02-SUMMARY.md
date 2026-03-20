---
id: T02
parent: S03
milestone: M021
provides:
  - push_sync() full implementation with GET→modify→PUT ETag concurrency pipeline
  - _find_changed_events() SPARQL query for CalDAV events with local modifications
  - 21 new push sync tests (5 TestFindChangedEvents + 16 TestPushSync)
  - MockGraphClient extended with changed_events for push test infrastructure
key_files:
  - apps/caldav-calendar/services/sync_engine.py
  - backend/tests/test_caldav_sync_engine.py
key_decisions:
  - CalDAVConflictError (412) caught with continue (not re-raise) so per-event error isolation is maintained — conflicts are recorded but don't block subsequent events
patterns_established:
  - CalDAV push uses fetch-modify-PUT (not PATCH) — gets current .ics, modifies ATTENDEE PARTSTAT in-memory, PUTs full VCALENDAR back with If-Match ETag
observability_surfaces:
  - last_push_result in StateClient — JSON with status/pushed/skipped/errors/timestamp
  - caldav.sync.engine logger — push counts, per-event errors, ETag conflicts at INFO/WARNING
duration: 18min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Implement push_sync pipeline with change detection and ETag concurrency

**Replaced push_sync() stub with full CalDAV bidirectional push: SPARQL change detection, fetch-modify-PUT with ETag concurrency, per-event error isolation, and 21 new tests**

## What Happened

Added `_find_changed_events()` SPARQL query that finds CalDAV events where `dcterms:modified > bpkm:lastSyncedAt`, including the `externalUrl` field that CalDAV needs (unlike Google Calendar which uses calendarName+externalId for API calls).

Replaced the `push_sync()` stub with the full pipeline: auth check → direction check → find changed events → for each event: build reverse patch → check externalUrl → GET current .ics with ETag → modify ATTENDEE PARTSTAT → PUT with If-Match ETag → update lastSyncedAt. CalDAVConflictError (412) is caught distinctly from generic errors and recorded with a descriptive message. Per-event try/except ensures one failure doesn't block others.

Extended MockGraphClient with `changed_events` parameter and added `put`/`delete` methods to MockCalDAVHttpClient. Added `_make_push_state()` helper with `auth_method` (required by `get_connection_status()` which checks `bool(auth_method)`).

All stubs and S03 comments removed from sync_engine.py.

## Verification

- `pytest tests/test_caldav_sync_engine.py -v -x` — 51 tests pass (30 existing + 21 new)
- `pytest tests/test_caldav_*.py --co -q` — 229 tests collected across all CalDAV test files
- `rg "not yet implemented|stub|S03" sync_engine.py field_mapper.py` — zero matches
- `pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -k "error or conflict or fail or empty"` — 17 failure-path tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_caldav_sync_engine.py -v -x` | 0 | ✅ pass | 3.2s |
| 2 | `uv run python -m pytest tests/test_caldav_*.py --co -q` | 0 | ✅ pass (229 collected) | 2.7s |
| 3 | `rg "not yet implemented\|stub\|S03" sync_engine.py field_mapper.py` | 1 | ✅ pass (no matches) | 2.7s |
| 4 | `uv run python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` | 0 | ✅ pass (149 passed) | 3.6s |
| 5 | `uv run python -m pytest ... -k "error or conflict or fail or empty"` | 0 | ✅ pass (17 passed) | 3.6s |

## Diagnostics

- **State inspection:** `await state.get("last_push_result")` → JSON with `{status, pushed, skipped, errors, timestamp}`. Status is "ok" (all success), "partial" (mixed), "error" (all failed), or "skipped" (not connected / pull-only).
- **Error details:** Each error in the `errors` array has `event_iri` and `error` message. ETag conflicts contain "ETag conflict (412)" in the message.
- **Logger:** `caldav.sync.engine` at INFO for push counts, WARNING for per-event errors and ETag conflicts.

## Deviations

- `_make_push_state()` needed `auth_method: "basic"` — the plan's version omitted it, but `get_connection_status()` checks `bool(auth_method)` to determine connected state. Without it, the pull-only test hit the "not connected" path before reaching the direction check.
- Added `put` and `delete` methods to MockCalDAVHttpClient — the plan mentioned needing PUT support but didn't specify adding it to the mock class definition.
- Wrote 21 new tests instead of the estimated ~20 (5 find_changed + 16 push). Added extra tests for result storage on skip paths and ETag conflict non-blocking behavior.

## Known Issues

None.

## Files Created/Modified

- `apps/caldav-calendar/services/sync_engine.py` — Added `_find_changed_events()`, replaced `push_sync()` stub with full GET→modify→PUT pipeline, added imports for `build_event_patch`, `modify_vevent_partstat`, `CalDAVConflictError`
- `backend/tests/test_caldav_sync_engine.py` — Extended MockGraphClient with `changed_events`, added `put`/`delete` to MockCalDAVHttpClient, added `_make_push_state()`, replaced TestPushSyncStub with TestFindChangedEvents (5 tests) + TestPushSync (16 tests), added new imports
