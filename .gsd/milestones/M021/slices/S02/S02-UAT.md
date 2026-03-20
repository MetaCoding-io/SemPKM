# S02: Pull Sync + Field Mapping + Person Matching — UAT

**Milestone:** M021
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice produces pure-function modules (field mapper, sync engine, person matcher) tested via 134 unit tests with mocks. Runtime proof is deferred to S04's E2E test with mock CalDAV server. No live server needed for contract verification.

## Preconditions

- Backend venv has `icalendar` installed: `cd backend && .venv/bin/python -c "from icalendar import Calendar; print('ok')"`
- All CalDAV service modules exist: `ls apps/caldav-calendar/services/{field_mapper,sync_engine,person_matcher,caldav_client,auth}.py`
- Backend test venv has pytest available: `cd backend && .venv/bin/python -m pytest --version`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py tests/test_caldav_auth.py tests/test_caldav_client.py -v --tb=short
```

**Expected:** 196 tests pass, 0 failures, 0 errors. Runtime <1s.

## Test Cases

### 1. Field mapper extracts all ~20 VEVENT properties correctly

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py -v`
2. **Expected:** 85 tests pass covering: SUMMARY→title, DTSTART datetime→xsd:dateTime, DTSTART date→xsd:date with allDay=true, DTEND, LOCATION, STATUS enum mapping (CONFIRMED→confirmed, TENTATIVE→tentative, CANCELLED→cancelled), CLASS→visibility (PUBLIC→public, PRIVATE→private, CONFIDENTIAL→confidential), TRANSP→showAs (OPAQUE→busy, TRANSPARENT→free), RRULE passthrough with prefix stripping, RECURRENCE-ID extraction, ATTENDEE single-vs-list normalization with PARTSTAT extraction, ORGANIZER email extraction, VALARM negative timedelta→positive minutes, CATEGORIES single-vs-list, UID, CREATED/LAST-MODIFIED→ISO 8601, URL, DESCRIPTION extraction.

### 2. Field mapper handles edge cases

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py -k "missing or empty or none" -v`
2. **Expected:** Tests pass proving: missing SUMMARY→"Untitled Event", missing LOCATION/URL/DESCRIPTION→property omitted, empty ATTENDEE list→attendees key excluded, empty CATEGORIES→categories key excluded, None property values→graceful skip.

### 3. Sync engine pull pipeline creates new events (two-phase)

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py -k "new_event" -v`
2. **Expected:** Tests pass proving: phase 1 creates object.create command with correct type/slug/properties, phase 2 creates body.set command when description present, phase 2 creates edge.create commands for attendees/organizer. Slug uses `caldav-` prefix + SHA-256 of calendar_href+UID.

### 4. Sync engine handles incremental sync via sync-token

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py -k "sync_token" -v`
2. **Expected:** Tests pass proving: sync token extracted from multistatus XML, stored in StateClient as `sync_token:{calendar_href}`, passed to subsequent get_events() calls for incremental fetch.

### 5. Sync engine recovers from 410 Gone

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py -k "410" -v`
2. **Expected:** Test passes proving: when get_events() returns 410, sync engine clears stored sync token and retries with full sync (two REPORT calls total).

### 6. Sync engine isolates per-event errors

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py -k "malformed" -v`
2. **Expected:** Test passes proving: a malformed .ics in the event list is captured in the result `errors` array while other valid events are still processed successfully.

### 7. Sync engine prevents re-import loops

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_sync_engine.py -k "not_modified_since_last_sync" -v`
2. **Expected:** Test passes proving: events whose LAST-MODIFIED timestamp is before lastSyncedAt generate no commands (classified as "unchanged").

### 8. Person matcher resolves attendees by email

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_person_matcher.py -v`
2. **Expected:** 18 tests pass proving: email SPARQL lookup (foaf:mbox + crm:email), cache hit on second query for same email (case-insensitive), Person created on miss with email-derived slug and foaf:mbox property, None/empty email returns None without SPARQL query.

### 9. S01 tests pass with zero regressions

1. Run `cd backend && .venv/bin/python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v`
2. **Expected:** 62 tests pass. No failures, no errors. The _report_raw() addition did not break existing _report() callers.

### 10. app.py stubs fully replaced

1. Run `grep -rni "stub\|not yet implemented\|placeholder" apps/caldav-calendar/app.py`
2. **Expected:** No matches. All three route/task handlers (sync_now, poll_events, push_changes) call real sync functions.

## Edge Cases

### Missing SUMMARY field

1. Build an iCalendar event without SUMMARY property
2. Call `build_event_properties(event, "test-cal", "test-slug")`
3. **Expected:** Returns `title: "Untitled Event"` (not KeyError or None)

### All-day event detection

1. Build iCalendar event with `DTSTART;VALUE=DATE:20260320` (date, not datetime)
2. Call `extract_dtstart(event)`
3. **Expected:** Returns `("2026-03-20", "xsd:date", True)` — third value `True` indicates all-day

### Single ATTENDEE (not a list)

1. Build iCalendar event with exactly one ATTENDEE
2. Call `extract_attendees(event)`
3. **Expected:** Returns a list with one dict (not a bare dict, not error)

### RRULE prefix stripping

1. Build iCalendar event with `RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR`
2. Call `extract_rrule(event)`
3. **Expected:** Returns `"FREQ=WEEKLY;BYDAY=MO,WE,FR"` (no `RRULE:` prefix, no `b'` bytes marker)

### VALARM negative duration to positive minutes

1. Build iCalendar event with VALARM having `TRIGGER:-PT15M`
2. Call `extract_alarms(event)`
3. **Expected:** Returns `[{"trigger_minutes": 15, "action": "DISPLAY"}]` — positive integer

## Failure Signals

- Any test failure in the three new test files indicates a field mapping or sync logic regression
- `ImportError` on `from icalendar import Calendar` → icalendar not installed in venv
- `ImportError` when loading sync_engine or field_mapper → module path or importlib configuration wrong
- Stubs found in app.py → wiring incomplete
- S01 test failures → backward compat broken by caldav_client.py modifications

## Requirements Proved By This UAT

- None validated — this UAT proves contract correctness via unit tests only. CDAV requirements need runtime proof (S04 E2E).

## Not Proven By This UAT

- CDAV-03 (Pull sync creates bpkm:Event objects) — contract-proven but not runtime-proven
- CDAV-04 (VEVENT field mapping correctness) — contract-proven but not runtime-proven
- CDAV-05 (Attendee resolution to Person objects) — contract-proven but not runtime-proven
- CDAV-06 (RSVP push-back) — stub only, S03 scope
- CDAV-07 (Recurrence handling) — field extraction proven, full pull tested, but no E2E
- Any integration with real CalDAV servers — deferred to S04

## Notes for Tester

- All tests use real `icalendar.Event` components built via `.add()` — they exercise the actual library, not mocked interfaces.
- The `PhaseAwareGraphClient` in sync engine tests is a test helper that tracks per-slug query counts to simulate the two-phase create path. It's not production code.
- The person matcher is a near-clone of the Google Calendar person matcher — same SPARQL pattern, just different logger name. This is intentional (consistency across sync apps).
- `push_sync()` intentionally returns `{"status": "skipped"}` — this is correct for S02. S03 will implement real push.
