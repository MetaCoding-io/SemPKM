# S02: Pull Sync + Field Mapping + Person Matching

**Goal:** iCalendar events from selected CalDAV calendars sync into SemPKM as bpkm:Event objects with all VEVENT fields correctly mapped, attendees resolved to Person objects, sync-token incremental sync working, and app.py wired to real sync engine.
**Demo:** User clicks Sync Now → events from selected calendars appear as bpkm:Event objects with correct titles, dates (timed + all-day), timezone, status, visibility, location, description, RRULE, attendees, organizer, categories, and alarms. Second sync uses sync-token for incremental fetch.

## Must-Haves

- Field mapper with all ~20 iCalendar property extractions (SUMMARY, DTSTART, DTEND, STATUS, LOCATION, CLASS, TRANSP, RRULE, RECURRENCE-ID, ATTENDEE, ORGANIZER, VALARM, CATEGORIES, UID, CREATED, LAST-MODIFIED, URL, DESCRIPTION) with correct handling of icalendar library typed objects
- Sync engine with two-phase bulk create (phase 1: object.create, phase 2: body.set + edge.create), per-event error isolation, loop prevention via lastSyncedAt
- Sync-token extraction from multistatus root XML element for incremental sync, with 410 Gone recovery to full sync
- Person matcher cloned from Google Calendar pattern (email SPARQL lookup, create-on-miss, LRU cache)
- app.py stubs replaced with real sync_engine.pull_sync() calls in sync_now route and poll-events task
- push_sync() stub returning skipped result (real implementation in S03)
- `icalendar` library installed in backend test venv
- 100+ unit tests across field mapper, sync engine, and person matcher

## Proof Level

- This slice proves: contract (unit tests with mocks proving all field transforms and sync pipeline logic)
- Real runtime required: no (runtime proof deferred to S04 E2E)
- Human/UAT required: no

## Verification

- `cd backend && pip install icalendar && python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py -v` — all pass, 100+ tests total
- `cd backend && python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` — existing 62 S01 tests still pass (no regressions)
- Sync-token extraction: at least one test proves `get_events()` returns a non-None `new_sync_token` from sync-collection REPORT XML
- Field mapper: tests cover all ~20 iCalendar properties including edge cases (single vs list ATTENDEE, all-day vs timed DTSTART, RRULE passthrough, VALARM negative timedelta, missing properties)
- Sync engine: tests cover auth guard, no-calendars guard, new event creation (two-phase), existing event update, loop prevention, per-event error isolation, sync-token persistence, 410 recovery
- Person matcher: tests cover email match, cache hit, create-on-miss, None email

## Observability / Diagnostics

- Runtime signals: `caldav.sync.engine` logger — per-calendar event counts, sync-token incremental vs full, per-event errors; `caldav.sync.person_matcher` logger — email lookups, person creation
- Inspection surfaces: `last_pull_result` in StateClient — JSON with status/created/updated/unchanged/errors; `last_sync_at` timestamp; `sync_token:{calendar_href}` per-calendar sync tokens
- Failure visibility: per-event errors captured in result dict `errors` list with event href and error message; CalDAVError exceptions with status_code and response_body propagate through sync pipeline
- Redaction constraints: CalDAV passwords never in logs (auth module handles this from S01)

## Integration Closure

- Upstream surfaces consumed: `CalDAVClient.get_events()` from S01 (returns list of dicts with href/etag/calendar_data/status), `auth.get_connection_status()` and `auth.get_auth_headers()` from S01, `app.py` route/task stubs from S01
- New wiring introduced in this slice: `sync_now` route calls `pull_sync(ctx)` (optionally `push_sync(ctx)` for bidirectional); `poll_events` task calls `pull_sync(ctx)` then conditionally `push_sync(ctx)`; `push_changes` task calls `push_sync(ctx)` (stub)
- What remains before the milestone is truly usable end-to-end: S03 (push sync / bidirectional write), S04 (E2E test + user guide + docs)

## Tasks

- [x] **T01: Build iCalendar field mapper with exhaustive unit tests** `est:1h`
  - Why: The field mapper is the riskiest piece in S02 — the `icalendar` library returns typed objects (vDate, vDatetime, vCalAddress, vRecur) with different access patterns for single vs multi-valued properties. All ~20 VEVENT property extractions must be proven correct before the sync engine can use them. This task has zero dependencies on other S02 work.
  - Files: `apps/caldav-calendar/services/field_mapper.py`, `backend/tests/test_caldav_field_mapper.py`
  - Do: Install `icalendar` in backend venv. Build field_mapper.py with pure functions: `compute_event_slug()`, `build_event_properties()`, `build_event_patch()` (stub returning empty dict for S03), and extract helpers for each property. Include enum maps for STATUS, CLASS, TRANSP, PARTSTAT. Handle ATTENDEE single-vs-list normalization, RRULE `.to_ical()` decode with prefix stripping, DTSTART datetime/date type detection for all-day, VALARM negative timedelta→positive minutes, CATEGORIES single-vs-list. Follow Google Calendar field_mapper.py pattern.
  - Verify: `cd backend && python -m pytest tests/test_caldav_field_mapper.py -v` — 60+ tests pass covering all property extractions and edge cases
  - Done when: All ~20 iCalendar field extractions have at least one passing test each, edge cases (missing properties, empty values, single vs list ATTENDEE/CATEGORIES, all-day vs timed, timezone extraction) are covered

- [x] **T02: Build sync engine, person matcher, fix sync-token extraction, wire app.py** `est:1h30m`
  - Why: Completes the pull pipeline by connecting field mapper to CalDAVClient via sync engine, adding person matching for attendees/organizer, fixing the sync-token gap in caldav_client.py, and replacing app.py stubs with real sync calls. This is the integration task that makes the slice demo true.
  - Files: `apps/caldav-calendar/services/sync_engine.py`, `apps/caldav-calendar/services/person_matcher.py`, `apps/caldav-calendar/services/caldav_client.py`, `apps/caldav-calendar/app.py`, `backend/tests/test_caldav_sync_engine.py`, `backend/tests/test_caldav_person_matcher.py`
  - Do: (1) Add `_extract_sync_token(xml_text)` to caldav_client.py that parses root-level `<sync-token>` from multistatus XML. Update `_handle_response` to return `(entries, raw_xml)` tuple for REPORT responses (backward-compat: `_report()` still returns just entries, add `_report_with_raw()` for sync engine use). Update `get_events()` to use it. (2) Clone person_matcher.py from Google Calendar — same SPARQL email lookup, create-on-miss, LRU cache, only logger name changes. (3) Build sync_engine.py with `pull_sync(ctx)` following GCal pattern: auth check → selected calendars → for each calendar: get_events → parse .ics with icalendar.Calendar.from_ical() → walk VEVENT components → classify new/update/skip → build commands. Two-phase bulk create. Sync-token storage per calendar. 410 recovery. Per-event error isolation. `push_sync(ctx)` stub returning skipped. (4) Wire app.py: sync_now calls pull_sync + optional push_sync; poll_events task calls pull_sync + optional push_sync; push_changes task calls push_sync.
  - Verify: `cd backend && python -m pytest tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py tests/test_caldav_auth.py tests/test_caldav_client.py -v` — all pass with zero regressions on S01 tests
  - Done when: Sync engine tests cover auth guard, no-calendars guard, new event two-phase create, existing event update, loop prevention, per-event error isolation, sync-token persistence, 410 recovery. Person matcher tests cover email match, cache hit, create-on-miss, None email. app.py stubs replaced. 40+ new tests across sync engine + person matcher.

## Files Likely Touched

- `apps/caldav-calendar/services/field_mapper.py` (new)
- `apps/caldav-calendar/services/sync_engine.py` (new)
- `apps/caldav-calendar/services/person_matcher.py` (new)
- `apps/caldav-calendar/services/caldav_client.py` (sync-token extraction fix)
- `apps/caldav-calendar/app.py` (wire stubs to real sync)
- `backend/tests/test_caldav_field_mapper.py` (new)
- `backend/tests/test_caldav_sync_engine.py` (new)
- `backend/tests/test_caldav_person_matcher.py` (new)
