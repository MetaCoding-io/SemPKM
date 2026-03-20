# S02: Pull Sync + Field Mapping + Person Matching — Research

**Date:** 2026-03-19

## Summary

S02 builds the pull pipeline: iCalendar field mapper, sync engine with sync-token incremental sync, and email-based person matching. This is well-understood work — the Google Calendar (M018) and Outlook (M020) sync apps provide battle-tested patterns to follow. The CalDAV variant is architecturally *simpler* than both predecessors: iCalendar RRULE strings pass through directly (no Outlook-style 18-combination pattern→RRULE conversion), STATUS/CLASS/TRANSP are direct 1:1 enum maps, and ATTENDEE mailto: URIs give email addresses directly (no nested JSON structures).

The one novel piece is iCalendar property extraction via the `icalendar` Python library. The library returns typed objects (vDate, vDatetime, vCalAddress, vRecur) with different access patterns depending on whether a property is single-valued or multi-valued. ATTENDEE is the most dangerous: `component.get('ATTENDEE')` returns a single `vCalAddress` when there's one attendee, but a list when there are multiple. RRULE's `.to_ical()` includes a `RRULE:` prefix that must be stripped.

The other gap from S01 is that `get_events()` returns `new_sync_token=None` — the sync-token for incremental sync lives in the multistatus root `<sync-token>` element, outside the per-response entries that `_parse_multistatus` currently extracts. S02 needs a small fix in `caldav_client.py` to extract this.

## Recommendation

Clone the Google Calendar sync engine pattern exactly, with three CalDAV-specific adaptations:

1. **Field mapper** — Replace JSON dict key access with `icalendar` library property extraction. Simpler enum maps (iCalendar STATUS values are already lowercase-able to match bpkm enum values). Direct RRULE passthrough instead of Google's `recurrence` array parsing or Outlook's pattern conversion.

2. **Sync engine** — Same two-phase bulk create pattern. Replace `gcal_client.get_events()` (JSON list) with CalDAV `client.get_events()` (list of dicts with `calendar_data` as raw .ics text). Parse each `.ics` with `icalendar.Calendar.from_ical()` and walk VEVENT components. Fix sync-token extraction to enable incremental sync.

3. **Person matcher** — Copy verbatim from Google Calendar. Same SPARQL email lookup, same create-on-miss, same LRU cache. Only the logger name changes.

Wire `sync_now` route and task handlers (`poll-events`, `push-changes` stub) in `app.py` to the real sync engine, replacing the current stubs.

## Implementation Landscape

### Key Files

**New files to create:**

- `apps/caldav-calendar/services/field_mapper.py` (~200 lines) — Pure functions: `compute_event_slug()`, `build_event_properties()`, `extract_*()` helpers for each iCalendar property. Enum maps for STATUS, CLASS, TRANSP, PARTSTAT. `build_event_patch()` stub returning empty dict (push-back is S03). All functions take parsed `icalendar.Event` components, not raw text.

- `apps/caldav-calendar/services/sync_engine.py` (~400 lines) — `pull_sync(ctx)` following the Google Calendar pattern: auth check → read selected calendars → for each calendar: `client.get_events()` → parse .ics → classify new/update/skip → build commands. Two-phase bulk create. Sync-token storage per calendar. `push_sync(ctx)` stub for S03 (returns skipped result). Loop prevention via `lastSyncedAt` comparison.

- `apps/caldav-calendar/services/person_matcher.py` (~140 lines) — Verbatim copy of `apps/google-calendar/services/person_matcher.py` with logger name changed to `caldav.sync.person_matcher`.

- `backend/tests/test_caldav_field_mapper.py` (~600 lines) — Pure function tests for all ~20 field extractions: SUMMARY, DTSTART (timed + all-day + timezone), DTEND, STATUS (3 values), LOCATION, CLASS (3 values), TRANSP (2 values), RRULE (direct passthrough), RECURRENCE-ID, ATTENDEE (single + list + self-PARTSTAT), ORGANIZER (mailto extraction), VALARM (timedelta → minutes), CATEGORIES (single + multi), UID, CREATED, LAST-MODIFIED, URL, DESCRIPTION. Edge cases: missing properties, empty values, no-title fallback.

- `backend/tests/test_caldav_sync_engine.py` (~800 lines) — Mock-based tests for pull_sync: auth guard, no-calendars guard, new event creation (two-phase), existing event update, loop prevention (lastSyncedAt skip), per-event error isolation, sync-token persistence, 410 recovery (full sync fallback). Route handler tests for sync_now and poll_events. Push_sync stub test.

- `backend/tests/test_caldav_person_matcher.py` (~200 lines) — Same pattern as `test_gcal_person_matcher.py`: email match, cache hit, create-on-miss, None email, display name slugification, empty email.

**Existing files to modify:**

- `apps/caldav-calendar/services/caldav_client.py` — Two changes:
  1. Add `_extract_sync_token(xml_text: str) -> str | None` — parse the root-level `<d:sync-token>` element from sync-collection REPORT responses.
  2. Update `get_events()` to call `_extract_sync_token()` on the raw response XML and return the extracted token instead of `None`. This requires `_report()` to return both the parsed entries and the raw XML, or a separate raw-text path. Simplest: have `_report()` return `(entries, raw_xml)` tuple, or add a `_report_raw()` method that returns the response text alongside parsed entries.

- `apps/caldav-calendar/app.py` — Replace sync stubs:
  1. `sync_now` route: import and call real `pull_sync(ctx)`, optionally `push_sync(ctx)` if bidirectional. Match Google Calendar pattern exactly.
  2. `poll_events` task: same — call `pull_sync`, optionally `push_sync`.
  3. `push_changes` task: call `push_sync(ctx)` (which returns a stub result until S03 implements it).

### Build Order

**T01: Field mapper + unit tests** — Build `field_mapper.py` with all iCalendar property extraction functions and `build_event_properties()`. Build `test_caldav_field_mapper.py` with exhaustive pure-function tests. This is the riskiest piece due to `icalendar` library typed-object edge cases. No dependencies on sync engine or person matcher.

**T02: Sync engine + person matcher + wiring + unit tests** — Build `sync_engine.py` and `person_matcher.py`. Fix sync-token extraction in `caldav_client.py`. Wire `app.py` stubs to real sync engine. Build `test_caldav_sync_engine.py` and `test_caldav_person_matcher.py`. Depends on field mapper from T01.

### Verification Approach

- All unit tests run via `cd backend && python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py tests/test_caldav_person_matcher.py -v`
- Target: ~100+ tests across the three test files
- Field mapper tests are pure (no mocks needed) — construct `icalendar.Event` components in tests, pass to extraction functions, assert output
- Sync engine tests use mock clients (MockStateClient, MockGraphClient, MockHttpClient) matching the established pattern from `test_gcal_sync_engine.py`
- Person matcher tests use async stubs matching `test_gcal_person_matcher.py`
- Existing S01 tests (62 tests in test_caldav_auth.py + test_caldav_client.py) must still pass — no regressions

## Constraints

- **`icalendar` library not installed in test venv** — It's listed in `apps/caldav-calendar/requirements.txt` but the backend test environment may not have it. Tests need `pip install icalendar` or conditional skip. Check whether the existing test runner (`backend/pyproject.toml`) includes it as a test dependency.
- **sync-token extraction requires raw XML access** — `_report()` currently returns only parsed multistatus entries (losing the root-level sync-token element). Modifying `_report()` changes the contract that S01's tests rely on. Keep backward compat by adding a new method or optional return.
- **IRI prefix bypass** — Bulk commands must post directly to `/api/commands/bulk` via `ctx.commands._client` (same pattern as Google Calendar D204). Do not use the SDK's `CommandClient.execute()` which enforces IRI prefix checks.
- **`icalendar` library installs as `icalendar` package** — `from icalendar import Calendar` is the import. The PyPI package name matches the import name.

## Common Pitfalls

- **ATTENDEE single vs list** — `component.get('ATTENDEE')` returns a `vCalAddress` when there's one attendee, a list of `vCalAddress` when there are multiple, and `None` when there are none. Must normalize: `attendees = component.get('ATTENDEE', [])`, then `if not isinstance(attendees, list): attendees = [attendees]`.
- **RRULE `.to_ical()` prefix** — The `icalendar` library's `vRecur.to_ical()` returns bytes like `b'FREQ=WEEKLY;BYDAY=MO,WE,FR'` (no prefix) OR in some cases `b'RRULE:FREQ=...'`. Strip any `RRULE:` prefix after decoding. Actually, `component.get('RRULE')` returns a `vRecur` dict-like object — use `.to_ical().decode('utf-8')` and strip prefix if present.
- **DTSTART timezone detection** — `component.get('DTSTART').dt` returns `datetime` (timed) or `date` (all-day). Check `isinstance(dt, date) and not isinstance(dt, datetime)` because `datetime` is a subclass of `date`. For timezone: `component.get('DTSTART').params.get('TZID')` returns the IANA timezone string.
- **VALARM TRIGGER sign** — `component.walk('VALARM')` returns nested alarm components. `alarm.get('TRIGGER').dt` returns a `timedelta` (typically negative, e.g., `-0:15:00` for 15 minutes before). Take `abs(td.total_seconds()) / 60` to get positive minutes.
- **CATEGORIES may be `vCategory` or list** — Similar to ATTENDEE, `component.get('CATEGORIES')` can return a single value or a list. Each value's `.to_ical().decode()` gives the comma-separated string. Split on comma and strip whitespace.
- **Sync-token 410 recovery** — When a sync-token expires, the CalDAV server returns 410 Gone. The sync engine must catch this, clear the stored token, and retry with a full calendar-query REPORT. Match the Google Calendar pattern in `pull_sync()`.
- **`_report()` contract change** — Modifying `_report()` return type to include raw XML will break the 42 existing S01 client tests if done carelessly. Either add a new `_report_with_token()` method or make the change backward-compatible.

## Open Risks

- **`icalendar` library version compatibility** — The research assumes standard API patterns, but minor version differences could affect typed object behavior. The `icalendar` library is well-maintained (v6.x as of 2024) but edge cases exist. Mitigate by testing against constructed iCalendar text, not mocked library objects.
- **DESCRIPTION content type** — Some CalDAV servers (Nextcloud) store HTML in DESCRIPTION fields. The `icalendar` library returns the raw text. The field mapper should pass it through as-is (like Google's `extract_body` strips HTML tags). Decision: strip HTML if present, same as Google Calendar pattern.

## Sources

- iCalendar field mapping: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §7 (CalDAV/iCalendar → bpkm:Event)
- Google Calendar sync engine pattern: `apps/google-calendar/services/sync_engine.py` (634 lines)
- Google Calendar field mapper: `apps/google-calendar/services/field_mapper.py` (258 lines)
- Google Calendar person matcher: `apps/google-calendar/services/person_matcher.py` (139 lines)
- S01 Forward Intelligence: sync-token extraction gap, `get_events()` return format, `put_event()` API
