# S03: Pull sync + field mapping + settings — UAT

**Milestone:** M018
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All domain logic is pure functions tested with 111 unit tests. The sync engine uses mocked HTTP/state/graph clients. No Docker runtime needed — the test suite covers all field transforms, orchestration paths, and error cases.

## Preconditions

- Python 3.14+ with backend venv activated (`cd backend && source .venv/bin/activate`)
- All dependencies installed (`uv sync`)
- No running Docker containers needed

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py tests/test_gcal_sync_engine.py tests/test_gcal_person_matcher.py -v --tb=short
```

Expected: 111 tests pass (64 + 36 + 11), zero failures.

## Test Cases

### 1. Field mapper — basic timed event

1. Import field_mapper via `importlib` (same pattern as test file)
2. Call `build_event_properties()` with a minimal Google Calendar event dict: `{"id": "evt1", "summary": "Meeting", "start": {"dateTime": "2026-04-01T10:00:00-04:00", "timeZone": "America/New_York"}, "end": {"dateTime": "2026-04-01T11:00:00-04:00", "timeZone": "America/New_York"}, "status": "confirmed"}` and `calendar_id="cal1"`, `calendar_name="Work"`
3. **Expected:** Result dict contains `bpkm:allDay` = `"false"`, `schema:startDate` = `"2026-04-01T10:00:00-04:00"`, `bpkm:timeZone` = `"America/New_York"`, `bpkm:eventStatus` = `"confirmed"`, `bpkm:externalProvider` = `"google-calendar"`, `bpkm:calendarName` = `"Work"`

### 2. Field mapper — all-day event detection

1. Call `build_event_properties()` with event: `{"id": "evt2", "summary": "Holiday", "start": {"date": "2026-12-25"}, "end": {"date": "2026-12-26"}}`
2. **Expected:** `bpkm:allDay` = `"true"`, `schema:startDate` = `"2026-12-25"`, `schema:endDate` = `"2026-12-26"` (date format, not dateTime)

### 3. Field mapper — conference URL extraction

1. Call `extract_conference_url()` with event containing `conferenceData.entryPoints` with `[{"entryPointType": "video", "uri": "https://meet.google.com/abc-def-ghi"}]`
2. **Expected:** Returns `"https://meet.google.com/abc-def-ghi"`
3. Call again with no conferenceData but `hangoutLink: "https://meet.google.com/xyz"`
4. **Expected:** Returns `"https://meet.google.com/xyz"` (fallback path)

### 4. Field mapper — response status from self-attendee

1. Call `extract_response_status()` with attendees list containing `{"email": "me@example.com", "self": true, "responseStatus": "tentative"}`
2. **Expected:** Returns `"tentative"`
3. Call with attendees list where no entry has `self: true`
4. **Expected:** Returns `None`

### 5. Field mapper — status/visibility/transparency normalization

1. Call `build_event_properties()` with `status: "cancelled"`, `visibility: "private"`, `transparency: "opaque"`
2. **Expected:** `bpkm:eventStatus` = `"cancelled"`, `bpkm:visibility` = `"private"`, `bpkm:showAs` = `"busy"`
3. Call with `visibility: "default"`
4. **Expected:** No `bpkm:visibility` key in result (excluded per spec)

### 6. Field mapper — RRULE extraction

1. Call `extract_rrule()` with `recurrence: ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"]`
2. **Expected:** Returns `"FREQ=WEEKLY;BYDAY=MO,WE,FR"` (RRULE: prefix stripped)
3. Call with `recurrence: ["EXDATE;VALUE=DATE:20260401"]`
4. **Expected:** Returns `None` (no RRULE entry)

### 7. Slug determinism

1. Call `compute_event_slug("cal123", "evt456")` twice
2. **Expected:** Both calls return the same string, and it's a valid URL slug (lowercase hex hash prefix)
3. Call with different calendar_id: `compute_event_slug("cal999", "evt456")`
4. **Expected:** Returns a different slug (calendar_id participates in hash)

### 8. Person matcher — email lookup and creation

1. Create a MockGraphClient that returns a SPARQL result with a Person IRI for `alice@example.com`
2. Call `person_matcher.match_person("alice@example.com", "Alice Smith")`
3. **Expected:** Returns the existing Person IRI without creating a new object
4. Call `person_matcher.match_person("unknown@example.com", "Unknown Person")`
5. **Expected:** Creates a new Person via commands client and returns the new IRI
6. Call `person_matcher.match_person("alice@example.com", "Alice Smith")` again
7. **Expected:** Returns cached result without SPARQL query (cache hit)

### 9. Sync engine — full pull sync with one event

1. Set up mocks: state with selected_calendars=["cal1"], GCalClient returning one event, GraphClient returning no existing events
2. Call `pull_sync(ctx)`
3. **Expected:** Returns `{status: "success", created: 1, updated: 0, unchanged: 0, errors: []}`. State now has `sync_token:cal1` persisted.

### 10. Sync engine — incremental sync with syncToken

1. Set up mocks: state with `sync_token:cal1` already set, GCalClient returning one modified event
2. Call `pull_sync(ctx)`
3. **Expected:** GCalClient receives the syncToken in its call. Updated event increments `updated` count.

### 11. Sync engine — 410 Gone triggers full resync

1. Set up mocks: state with `sync_token:cal1` set, GCalClient raises 410 on first call, succeeds on second
2. Call `pull_sync(ctx)`
3. **Expected:** syncToken cleared, full sync executed, result shows correct counts from the retry.

### 12. Settings UI — template structure

1. Open `apps/google-calendar/frontend/templates/connect_status.html`
2. Search for `Sync Configuration`, `Manual Sync`, `Sync Stats` section headings
3. **Expected:** All three sections exist with correct htmx attributes
4. Verify all `hx-post` URLs start with `/app/google-calendar/`
5. **Expected:** 4 URLs all use the proxy prefix

### 13. Settings UI — sync direction options

1. In `connect_status.html`, find the sync direction radio inputs
2. **Expected:** Two options: `pull-only` (checked when `sync_direction` is "pull-only" or default) and `bidirectional`

### 14. Settings UI — poll interval options

1. In `connect_status.html`, find the poll interval `<select>`
2. **Expected:** Options include 5m, 15m (default), 30m, 1h

## Edge Cases

### HTML stripping in descriptions

1. Call `strip_html_tags()` with `"<p>Hello <b>World</b></p>"`
2. **Expected:** Returns `"Hello World"` (all tags removed)
3. Call with `None`
4. **Expected:** Returns `None` (graceful null handling)

### Missing fields in event

1. Call `build_event_properties()` with minimal event (only `id` and `summary`)
2. **Expected:** Returns dict with only the properties that have values. No KeyError, no None values in output.

### Empty calendar list

1. Set up mocks with `selected_calendars=[]`
2. Call `pull_sync(ctx)`
3. **Expected:** Returns immediately with `{status: "success", created: 0, ...}` — no API calls made.

### Per-event error isolation

1. Set up mocks: calendar with 3 events, second event causes a mapping error (e.g., invalid data)
2. Call `pull_sync(ctx)`
3. **Expected:** First and third events created successfully. Errors array contains one entry with the second event's ID and error message. Overall status is still "success" (partial success).

## Failure Signals

- `pytest tests/test_gcal_field_mapper.py` fails → field mapping logic broken
- `pytest tests/test_gcal_sync_engine.py` fails → sync orchestration or mock alignment broken
- `pytest tests/test_gcal_person_matcher.py` fails → email lookup or cache logic broken
- `pytest -x` shows regressions → S03 changes broke existing functionality
- Jinja2 template parse error → syntax error in connect_status.html
- htmx URLs missing `/app/google-calendar/` prefix → requests will bypass proxy and 404

## Requirements Proved By This UAT

- GCAL-03 — Pull sync creates bpkm:Event objects with correct field mapping (tests 1-6, 9-11)
- GCAL-04 — Attendee resolution to Person objects (test 8)
- GCAL-07 — All-day event detection with correct xsd:date/xsd:dateTime (test 2)
- GCAL-08 — Conference URL extraction from conferenceData + hangoutLink fallback (test 3)

## Not Proven By This UAT

- GCAL-05 (RSVP push-back) — S04 scope, push sync is a placeholder
- GCAL-06 (Recurrence handling: master + exceptions) — S04 scope, RRULE stored but exception linking not yet implemented
- Live runtime sync against real Google Calendar API — mocked only
- Settings UI visual appearance — template structure checked but no browser rendering

## Notes for Tester

- All tests use importlib to load app modules from `apps/google-calendar/services/`. If import errors occur, check that `apps/` is on the Python path (the test files handle this via `sys.path.insert`).
- The mock response queue pattern is order-sensitive. If you add a new HTTP call to the sync pipeline, you must add a corresponding mock response at the correct queue position in every affected test.
- The field mapper is pure (no I/O, no state) — the fastest path to debugging a mapping issue is to call the function directly with a sample event dict in a Python REPL.
