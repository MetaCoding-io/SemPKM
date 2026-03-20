# S03: Push Sync + Bidirectional Write — Research

**Date:** 2026-03-19

## Summary

Push sync for CalDAV follows the exact same pipeline as Google Calendar (M018/S04) and Outlook (M020/S02) with one structural difference: CalDAV uses fetch-modify-PUT (full .ics body replacement) instead of JSON PATCH. The stubs are already in place — `push_sync()` in `sync_engine.py` returns a skipped result, `build_event_patch()` in `field_mapper.py` returns `{}`, and `_find_changed_events()` doesn't exist yet. The CalDAVClient already has `get_event()`, `put_event()`, and `delete_event()` from S01 with full ETag/If-Match handling.

The RSVP push-back cycle is: (1) SPARQL query finds caldav events where `dcterms:modified > bpkm:lastSyncedAt`, (2) for each, `get_event()` fetches current .ics + ETag, (3) parse with `icalendar`, modify the ATTENDEE PARTSTAT, (4) `put_event()` sends the full modified VCALENDAR with `If-Match: etag`. The `REVERSE_RESPONSE_STATUS_MAP` is already defined in field_mapper.py. Loop prevention uses the same `lastSyncedAt` comparison already proven in pull_sync.

The test infrastructure (MockAppContext, MockGraphClient, MockResponse) is established from S02's 31 sync engine tests. Push tests follow the Google Calendar test pattern exactly — replace the PATCH mock with a GET+PUT sequence mock.

## Recommendation

**Approach:** Implement push_sync by cloning the Google Calendar push pipeline structure, adapting for CalDAV's fetch-modify-PUT cycle. Two tasks: (1) `build_event_patch()` reverse mapping in field_mapper.py with tests, (2) `push_sync()` + `_find_changed_events()` in sync_engine.py with tests.

**Why this approach:**
- Google Calendar's push_sync has 7 clear steps — CalDAV needs the same 7 with step 6 changed from "PATCH event" to "GET .ics → modify PARTSTAT → PUT .ics"
- The existing CalDAVClient methods (`get_event`, `put_event`, `delete_event`) handle all HTTP/ETag complexity — push_sync just orchestrates
- REVERSE_RESPONSE_STATUS_MAP already exists — `build_event_patch()` just needs to use it
- `_find_changed_events()` SPARQL is identical to Google's except `externalProvider = "caldav"` instead of `"google-calendar"`

## Implementation Landscape

### Key Files

- `apps/caldav-calendar/services/field_mapper.py` (443 lines) — `build_event_patch()` stub at line 432 needs real implementation. `REVERSE_RESPONSE_STATUS_MAP` at line 55 maps bpkm response statuses back to iCalendar PARTSTAT values. Needs a helper to modify ATTENDEE PARTSTAT within a parsed iCalendar VEVENT.
- `apps/caldav-calendar/services/sync_engine.py` (550 lines) — `push_sync()` stub at line 188 needs full implementation. `_find_changed_events()` needs creation (copy `_find_existing_event` SPARQL pattern at line 59, adapt to Google's `_find_changed_events` at line 184). `_submit_commands_batched` at line 158 already available for lastSyncedAt updates.
- `apps/caldav-calendar/services/caldav_client.py` — `get_event()` (line 612) returns `{etag, calendar_data}`. `put_event()` (line 657) accepts `(event_url, ics_data, etag)` and returns new ETag. `delete_event()` (line 722) accepts `(event_url, etag)`. All three are fully implemented with error classes.
- `apps/caldav-calendar/app.py` — Already wired: `sync_now` calls `push_sync()` when direction is bidirectional (line 222), `poll_events` does the same (line 241), `push_changes` task calls `push_sync()` directly (line 248). **No changes needed.**
- `backend/tests/test_caldav_field_mapper.py` — Has stub tests for `build_event_patch` at line 758 (2 tests returning `{}`). Replace with real reverse mapping tests.
- `backend/tests/test_caldav_sync_engine.py` — Has `TestPushSyncStub` at line 1020 (1 test). Replace with full push pipeline tests following Google Calendar's `TestPushSync` pattern (6 tests at line 1139 of test_gcal_sync_engine.py).

### Reference Implementations

| CalDAV Push Need | Google Calendar Reference | CalDAV Difference |
|---|---|---|
| `_find_changed_events()` | `apps/google-calendar/services/sync_engine.py:184` | Change `externalProvider` from `"google-calendar"` to `"caldav"`, add `externalUrl` to results (needed for CalDAV PUT URL) |
| `push_sync()` pipeline | `apps/google-calendar/services/sync_engine.py:223` | Replace step 4 (OAuth refresh) with no-op (HTTP Basic auth). Replace step 6 PATCH with GET→modify→PUT cycle |
| `build_event_patch()` | `apps/google-calendar/services/field_mapper.py:220` | Returns modified iCalendar VEVENT properties dict instead of Google JSON PATCH body. CalDAV modifies the full .ics, so this returns only the changes to apply to the parsed component. |
| Push tests | `backend/tests/test_gcal_sync_engine.py:1139` | Mock GET returning .ics text + ETag, then assert PUT was called with modified .ics |

### Build Order

**T01: `build_event_patch()` reverse mapping + iCalendar modification helper** (~15 tests)

Implement the reverse field mapper first because push_sync depends on it. Two functions needed:

1. `build_event_patch(event_props, user_email) -> dict` — Extracts pushable changes from bpkm properties. For v1, only responseStatus is pushable (same as Google/Outlook). Returns `{"responseStatus": "ACCEPTED"}` or `{}` if no pushable change.

2. `modify_vevent_partstat(ics_text, user_email, new_partstat) -> str` — Parses .ics with `icalendar.Calendar.from_ical()`, walks to VEVENT, finds the ATTENDEE matching `user_email`, updates its PARTSTAT param, returns `.to_ical().decode()`. This is the CalDAV-specific function — Google/Outlook don't need it because they use PATCH.

Test cases:
- `build_event_patch` returns `{}` for no responseStatus
- `build_event_patch` returns `{}` for unmapped responseStatus
- `build_event_patch` returns correct PARTSTAT for each of the 4 mapped statuses
- `modify_vevent_partstat` modifies single attendee
- `modify_vevent_partstat` modifies correct attendee when multiple present
- `modify_vevent_partstat` returns unchanged .ics when user_email not found in attendees
- `modify_vevent_partstat` handles case-insensitive mailto: comparison
- Round-trip: modify → parse → extract matches expected value

**T02: `push_sync()` + `_find_changed_events()` + tests** (~20 tests)

Implement the push pipeline and SPARQL query. Steps:

1. `_find_changed_events(graph_client) -> list[dict]` — SPARQL query for caldav events where `dcterms:modified > bpkm:lastSyncedAt`. Returns `{iri, externalId, externalUrl, calendarName, responseStatus, lastSyncedAt}`. Note: `externalUrl` is the CalDAV resource URL needed for GET/PUT — Google doesn't need this because it constructs URLs from calendarId + eventId.

2. `push_sync(ctx) -> dict` — Full pipeline:
   - Auth check → skip if not connected
   - Direction check → skip if pull-only
   - Read user_email from state
   - Build CalDAVClient
   - Call `_find_changed_events()` → skip if empty
   - For each event: `build_event_patch()` → skip if empty → `get_event(url)` → `modify_vevent_partstat(ics, email, partstat)` → `put_event(url, modified_ics, etag)` → update lastSyncedAt via commands
   - Store `last_push_result` in state
   - Return structured result `{status, pushed, skipped, errors, timestamp}`

Test cases (following Google Calendar pattern):
- Not connected → skips
- Pull-only direction → skips
- No changed events → ok with 0 pushed
- Successful RSVP push (assert GET + PUT called with correct args)
- lastSyncedAt updated after push (assert object.patch command posted)
- Error isolation per event (first fails, second succeeds)
- Missing externalUrl → error captured, not crash
- ETag conflict (412) → error captured with conflict message
- `_find_changed_events` returns correct bindings shape
- `_find_changed_events` filters by externalProvider "caldav"
- `last_push_result` stored in state after push

### Verification Approach

```bash
# Run all CalDAV push tests (T01 + T02)
cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x

# Run full CalDAV test suite (should be 196 existing + ~35 new = ~230+ tests)
cd /home/james/Code/SemPKM/.gsd/worktrees/M018/backend && python -m pytest tests/test_caldav_*.py -v --tb=short

# Verify no stubs remain
rg "S03|not yet implemented|stub" apps/caldav-calendar/services/sync_engine.py apps/caldav-calendar/services/field_mapper.py
```

## Common Pitfalls

- **CalDAV PUT requires full VCALENDAR** — Unlike Google/Outlook PATCH which sends partial JSON, CalDAV PUT replaces the entire .ics resource. The `modify_vevent_partstat()` function must parse, modify one property, and regenerate the complete VCALENDAR. The `icalendar` library's `.to_ical()` handles this but may reorder properties (cosmetic, not functional).
- **ATTENDEE matching is case-insensitive** — `mailto:User@Example.com` and `mailto:user@example.com` refer to the same person. The `modify_vevent_partstat()` function must do case-insensitive comparison on the email portion of the vCalAddress.
- **ATTENDEE single-vs-list normalization** — Same `_normalize_to_list()` issue from S02. When modifying ATTENDEE in a parsed component, the `component['ATTENDEE']` getter returns a single vCalAddress or a list depending on count. Use `_normalize_to_list()` for the read, but when writing back must preserve the original format (list or single).
- **ETag quoting** — ETags from `get_event()` response headers include surrounding double quotes (e.g., `"abc123"`). `put_event()` sends these in the If-Match header as-is. Don't strip or add quotes — the CalDAVClient already handles this correctly.
- **externalUrl vs externalId** — Google/Outlook construct API URLs from calendarId + eventId. CalDAV stores the full resource URL in `bpkm:externalUrl` (e.g., `https://cal.example.com/calendars/user/default/event-uid.ics`). The `_find_changed_events` SPARQL must include `externalUrl` — this is the URL passed to `get_event()` and `put_event()`.

## Constraints

- `build_event_patch()` returns only responseStatus changes for v1 (same scope as Google/Outlook push — RSVP only). Full property push-back (title, time edits, etc.) would require a more complex reverse mapping that regenerates the entire VEVENT from bpkm properties. Not in scope per roadmap ("RSVP push-back via PUT").
- CalDAVClient's `put_event()` raises `CalDAVConflictError` on 412 — push_sync must catch this and record as an error, not crash.
- The `_submit_commands_batched()` helper in sync_engine.py posts to `/api/commands/bulk` via the raw httpx client (D204 bypass). Use this for the lastSyncedAt update, same as Google Calendar does.
