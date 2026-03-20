---
estimated_steps: 5
estimated_files: 2
---

# T01: Build iCalendar field mapper with exhaustive unit tests

**Slice:** S02 — Pull Sync + Field Mapping + Person Matching
**Milestone:** M021

## Description

Build the pure-function field mapper that transforms parsed `icalendar.Event` components into bpkm:Event property dicts. This is the riskiest piece in S02 because the `icalendar` Python library returns typed objects (vDate, vDatetime, vCalAddress, vRecur) with different access patterns depending on single vs multi-valued properties. All ~20 VEVENT property extractions must be proven correct by exhaustive unit tests before the sync engine (T02) can use them.

The field mapper has zero dependencies on the sync engine or person matcher — it's pure functions operating on parsed icalendar components. This isolation makes it the natural first task.

**Reference implementation:** `apps/google-calendar/services/field_mapper.py` (258 lines) provides the architectural pattern. The CalDAV version is simpler in several ways: RRULE passes through directly (no Outlook-style pattern conversion), STATUS/CLASS/TRANSP are 1:1 enum maps, and ATTENDEE mailto: URIs give email addresses directly.

**Key icalendar library pitfalls** (from research):
- `component.get('ATTENDEE')` returns a single `vCalAddress` when one attendee, a list when multiple, `None` when absent — must normalize
- `component.get('RRULE')` returns a `vRecur` dict-like object — use `.to_ical().decode('utf-8')` and strip any `RRULE:` prefix
- `component.get('DTSTART').dt` returns `datetime` (timed) or `date` (all-day) — check `isinstance(dt, date) and not isinstance(dt, datetime)` because datetime subclasses date
- `alarm.get('TRIGGER').dt` returns a negative timedelta — take `abs(td.total_seconds()) / 60` for positive minutes
- `component.get('CATEGORIES')` can return a single value or list, each value's `.to_ical().decode()` gives comma-separated string

## Steps

1. **Install icalendar in backend test venv.** Run `cd backend && .venv/bin/pip install icalendar`. Verify with `cd backend && .venv/bin/python -c "from icalendar import Calendar; print('ok')"`.

2. **Create `apps/caldav-calendar/services/field_mapper.py`** (~200 lines) with:
   - Constants: `BPKM = "urn:sempkm:model:basic-pkm:"` prefix, enum maps for STATUS_MAP (`{"TENTATIVE": "tentative", "CONFIRMED": "confirmed", "CANCELLED": "cancelled"}`), CLASS_MAP (`{"PUBLIC": "public", "PRIVATE": "private", "CONFIDENTIAL": "confidential"}`), TRANSP_MAP (`{"OPAQUE": "busy", "TRANSPARENT": "free"}`), PARTSTAT_MAP (`{"NEEDS-ACTION": "needs-action", "ACCEPTED": "accepted", "DECLINED": "declined", "TENTATIVE": "tentative"}`), REVERSE_RESPONSE_STATUS_MAP (for S03 push-back)
   - `compute_event_slug(calendar_href: str, uid: str) -> str` — SHA-256 hash of `f"{calendar_href}:{uid}"`, take first 12 hex chars, prefix with `caldav-`
   - `detect_all_day(component) -> tuple[bool, str | None, str | None]` — check `isinstance(dt, date) and not isinstance(dt, datetime)`, return `(is_all_day, start_str, end_str)` with correct xsd:date vs xsd:dateTime formatting
   - `extract_timezone(component) -> str | None` — extract TZID from DTSTART params
   - `extract_status(component) -> str | None` — lookup in STATUS_MAP (case-insensitive)
   - `extract_visibility(component) -> str | None` — CLASS → CLASS_MAP
   - `extract_show_as(component) -> str | None` — TRANSP → TRANSP_MAP
   - `extract_rrule(component) -> str | None` — `.to_ical().decode('utf-8')`, strip `RRULE:` prefix if present
   - `extract_recurrence_id(component) -> str | None` — RECURRENCE-ID value as ISO string
   - `extract_attendees(component) -> list[dict]` — normalize single/list, return `[{"email": ..., "name": ..., "partstat": ...}]` from mailto: URIs and CN/PARTSTAT params
   - `extract_self_response_status(component, user_email: str | None) -> str | None` — find self attendee by email, return mapped PARTSTAT
   - `extract_organizer(component) -> dict | None` — return `{"email": ..., "name": ...}` from mailto: URI and CN param
   - `extract_reminder_minutes(component) -> int | None` — walk VALARM subcomponents, take first TRIGGER, convert negative timedelta to positive minutes
   - `extract_categories(component) -> list[str]` — normalize single/list, split comma-separated values, strip whitespace
   - `strip_html_tags(text: str) -> str` — regex strip for HTML in DESCRIPTION
   - `extract_body(component) -> str | None` — DESCRIPTION value, strip HTML if present
   - `build_event_properties(component, calendar_name: str, sync_time: str, user_email: str | None = None) -> dict` — orchestrator that calls all extract functions and assembles the full bpkm property dict with correct IRI keys. Include: dcterms:title, schema:startDate, schema:endDate, bpkm:allDay, bpkm:timeZone, bpkm:eventStatus, bpkm:location, bpkm:visibility, bpkm:showAs, bpkm:recurrenceRule, bpkm:recurringEventId, bpkm:responseStatus, bpkm:reminderMinutes, bpkm:tags, bpkm:externalId, bpkm:externalProvider ("caldav"), bpkm:calendarName, bpkm:lastSyncedAt, dcterms:created, dcterms:modified. Omit None values.
   - `build_event_patch(event_props: dict, user_email: str | None) -> dict` — stub returning empty dict (S03 will implement reverse mapping for push)

3. **Create `backend/tests/test_caldav_field_mapper.py`** (~600 lines) with exhaustive tests. Build iCalendar components in-test using `icalendar.Calendar()` / `icalendar.Event()` with `.add()` to set properties — do NOT mock library internals. Test categories:
   - `compute_event_slug`: deterministic output, different inputs produce different slugs
   - `detect_all_day`: timed event (datetime) → `(False, dateTime_str, dateTime_str)`, all-day event (date) → `(True, date_str, date_str)`, timezone-aware datetime
   - `extract_timezone`: TZID present, TZID absent, UTC
   - `extract_status`: each of TENTATIVE/CONFIRMED/CANCELLED, missing, unknown value
   - `extract_visibility`: PUBLIC/PRIVATE/CONFIDENTIAL, missing
   - `extract_show_as`: OPAQUE/TRANSPARENT, missing
   - `extract_rrule`: weekly rule, daily rule, missing, verify no `RRULE:` prefix in output
   - `extract_recurrence_id`: present (datetime), present (date), missing
   - `extract_attendees`: single attendee (vCalAddress not list), multiple attendees (list), zero attendees, attendee with CN and PARTSTAT params, mailto: prefix stripping
   - `extract_self_response_status`: self attendee found by email match, no self attendee, no user_email provided
   - `extract_organizer`: present with CN, present without CN, missing, mailto: stripping
   - `extract_reminder_minutes`: 15-min before (negative timedelta → 15), 1-hour before, no VALARM, multiple VALARMs (take first)
   - `extract_categories`: single category, multiple comma-separated, multiple CATEGORIES properties, missing
   - `extract_body`: plain text, HTML stripping, missing
   - `build_event_properties`: full event with all properties, minimal event (title only), all-day event, event with attendees/organizer extracted (as dicts, not IRIs — person matching is T02)
   - `build_event_patch`: returns empty dict (stub verification)

4. **Run tests and verify.** `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py -v` — all pass, 60+ tests. Fix any failures from icalendar library type surprises.

5. **Verify no regressions.** `cd backend && .venv/bin/python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` — all 62 S01 tests still pass.

## Must-Haves

- [ ] `icalendar` package installed in backend test venv and importable
- [ ] field_mapper.py with all ~20 property extraction functions, enum maps, and `build_event_properties` orchestrator
- [ ] ATTENDEE single-vs-list normalization correct (single vCalAddress, list of vCalAddress, None)
- [ ] DTSTART all-day detection correct (`isinstance(dt, date) and not isinstance(dt, datetime)`)
- [ ] RRULE output is clean RFC 5545 string without `RRULE:` prefix
- [ ] VALARM negative timedelta converted to positive minutes
- [ ] CATEGORIES single-vs-list normalization with comma splitting
- [ ] 60+ unit tests passing covering all extractions and edge cases
- [ ] Zero regressions on existing S01 tests

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_caldav_field_mapper.py -v` — 60+ tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` — 62 S01 tests pass
- `cd backend && .venv/bin/python -c "from icalendar import Calendar; print('icalendar available')"` — prints ok

## Inputs

- `apps/google-calendar/services/field_mapper.py` — reference pattern for function signatures, enum maps, property key format
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §7 — authoritative CalDAV/iCalendar → bpkm:Event field mapping table
- S01 Forward Intelligence: `get_events()` returns dicts with `calendar_data` key containing raw .ics text that this mapper will parse

## Observability Impact

This task produces a pure-function module with no runtime side effects — no logging, no network, no state. Observability signals:

- **Test coverage as verification surface:** 85 unit tests exercise all ~20 extraction functions and the orchestrator. A future agent can run `pytest tests/test_caldav_field_mapper.py -v` to verify correctness after any change.
- **Property dict structure:** `build_event_properties()` returns a dict with full IRI keys — T02's sync engine can log/inspect this dict to debug field mapping issues at runtime.
- **No runtime logging needed:** Pure functions don't produce runtime state. Diagnostic logging belongs in T02's sync engine which calls these functions.

## Expected Output

- `apps/caldav-calendar/services/field_mapper.py` — ~200 line pure-function module with all property extractors and build_event_properties orchestrator
- `backend/tests/test_caldav_field_mapper.py` — ~600 line test file with 60+ tests covering all field transforms and edge cases
