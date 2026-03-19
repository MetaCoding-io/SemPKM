---
estimated_steps: 5
estimated_files: 2
---

# T01: Build field mapper with all property transforms and exhaustive tests

**Slice:** S03 — Pull sync + field mapping + settings
**Milestone:** M018

## Description

Build the pure field mapping module that translates Google Calendar API event dicts into bpkm:Event property dicts. This is the domain logic core of S03 — every property transform, normalization, and extraction function lives here. All functions are side-effect-free (no network, no logging, no state), making them exhaustively testable with simple dict-in/dict-out assertions.

Follow the exact pattern established by `apps/linear-sync/services/field_mapper.py` and `apps/github-sync/services/field_mapper.py`. Load the module in tests via importlib (same technique as `backend/tests/test_github_field_mapper.py`).

## Steps

1. **Create `apps/google-calendar/services/field_mapper.py`** with:
   - Constants:
     - `BPKM = "urn:sempkm:model:basic-pkm:"` — full IRI prefix for basic-pkm properties
     - `STATUS_MAP = {"confirmed": "confirmed", "tentative": "tentative", "cancelled": "cancelled"}` — Google status → bpkm:eventStatus (1:1 mapping per INTEGRATION-DOMAIN-MAPPING.md §5)
     - `RESPONSE_STATUS_MAP = {"needsAction": "needs-action", "accepted": "accepted", "declined": "declined", "tentative": "tentative"}` — camelCase → kebab-case normalization
     - `VISIBILITY_MAP = {"public": "public", "private": "private", "confidential": "confidential"}` — "default" is explicitly excluded (omit property)
     - `TRANSPARENCY_MAP = {"opaque": "busy", "transparent": "free"}` — transparency → showAs mapping

   - Pure functions:
     - `compute_event_slug(calendar_id: str, event_id: str) -> str` — `hashlib.sha256(f"{calendar_id}:{event_id}".encode()).hexdigest()[:16]`. Deterministic 16-char hex slug.
     - `detect_all_day(event: dict) -> tuple[bool, str | None, str | None]` — returns `(is_all_day, start_value, end_value)`. If `event["start"].get("date")` exists → all-day (use date string directly). Else use `event["start"].get("dateTime")` → timed event.
     - `extract_conference_url(event: dict) -> str | None` — check `conferenceData.entryPoints` for first `entryPointType == "video"`, return its `uri`. Fall back to `event.get("hangoutLink")`. Return None if neither.
     - `extract_response_status(event: dict) -> str | None` — find the attendee dict where `self == True` in `event.get("attendees", [])`. Return `RESPONSE_STATUS_MAP.get(attendee["responseStatus"])`. Return None if no self-attendee.
     - `extract_rrule(event: dict) -> str | None` — from `event.get("recurrence", [])`, find the first string starting with `"RRULE:"` and return it with the `"RRULE:"` prefix stripped. Return None if no recurrence or no RRULE entry.
     - `strip_html_tags(text: str) -> str` — `re.sub(r'<[^>]+>', '', text).strip()`. Simple tag removal for HTML descriptions.
     - `build_event_properties(event: dict, calendar_name: str, sync_time: str) -> dict` — the main function. Builds a dict of `{full_iri: value}` pairs from a Google Calendar event dict. Must handle all fields from the INTEGRATION-DOMAIN-MAPPING.md §5 spec:
       - `dcterms:title` ← `event["summary"]` (or `"(No title)"` if missing)
       - `schema:startDate` ← from `detect_all_day()` start value
       - `schema:endDate` ← from `detect_all_day()` end value
       - `bpkm:allDay` ← `"true"` or `"false"` string (xsd:boolean serialization)
       - `bpkm:timeZone` ← `event["start"].get("timeZone")` (may be None for all-day)
       - `bpkm:eventStatus` ← `STATUS_MAP.get(event.get("status"), "confirmed")`
       - `bpkm:location` ← `event.get("location")` (omit if None)
       - `bpkm:visibility` ← `VISIBILITY_MAP.get(event.get("visibility"))` — omit if "default" or absent
       - `bpkm:showAs` ← `TRANSPARENCY_MAP.get(event.get("transparency"))` — omit if absent
       - `bpkm:conferenceUrl` ← from `extract_conference_url()`
       - `bpkm:recurrenceRule` ← from `extract_rrule()`
       - `bpkm:recurringEventId` ← `event.get("recurringEventId")` direct
       - `bpkm:responseStatus` ← from `extract_response_status()`
       - `bpkm:reminderMinutes` ← first `reminders.overrides[0]["minutes"]` as string, or omit if no overrides and `useDefault` is true
       - `bpkm:calendarName` ← `calendar_name` parameter
       - `bpkm:externalId` ← `event["id"]`
       - `bpkm:externalUrl` ← `event.get("htmlLink")`
       - `bpkm:externalProvider` ← `"google-calendar"` (hardcoded — NOT "google" or "gcal")
       - `bpkm:lastSyncedAt` ← `sync_time` parameter (ISO 8601)
       - `dcterms:created` ← `event.get("created")`
       - `dcterms:modified` ← `event.get("updated")`
     - Properties with None values must be excluded from the returned dict (don't include keys with None values).

   **IMPORTANT constraints:**
   - `externalProvider` must be exactly `"google-calendar"` per S01 forward intelligence
   - `bpkm:allDay` must be `"true"` / `"false"` as strings (xsd:boolean serialization)
   - When `visibility` is `"default"`, omit `bpkm:visibility` entirely (per INTEGRATION-DOMAIN-MAPPING.md)
   - `bpkm:showAs` maps from `transparency` field, not `showAs` — the field names don't match
   - Description/body content is NOT a property — it's set via `body.set` command in the sync engine. The field mapper should return the stripped description text separately or not at all. Add a helper: `extract_body(event: dict) -> str | None` that returns `strip_html_tags(event.get("description", ""))` or None if empty.

2. **Create `backend/tests/test_gcal_field_mapper.py`** with ≥40 tests using the importlib loading pattern from `test_github_field_mapper.py`. Load from `apps/google-calendar/services/field_mapper.py`. Test classes:
   - `TestComputeEventSlug` — deterministic, different calendar_ids produce different slugs, different event_ids produce different slugs (~3 tests)
   - `TestDetectAllDay` — timed event, all-day event, missing start (~3 tests)
   - `TestExtractConferenceUrl` — conferenceData with video entryPoint, hangoutLink fallback, no conference data, conferenceData with only phone entryPoint (~4 tests)
   - `TestExtractResponseStatus` — self attendee found, no self attendee, no attendees array, multiple attendees with self in non-first position (~4 tests)
   - `TestExtractRrule` — single RRULE, RRULE with EXDATE, no recurrence, recurrence with only EXDATE (~4 tests)
   - `TestStripHtmlTags` — simple HTML, nested tags, no HTML, empty string (~4 tests)
   - `TestExtractBody` — HTML description, plain text, empty, None (~3 tests)
   - `TestBuildEventProperties` — full timed event with all fields, all-day event, minimal event (summary only), event with conferenceData, event with hangoutLink, event with RRULE, event with recurring exception (recurringEventId), event with visibility "default" (omitted), event with transparency, event with reminders overrides, event with no reminders, event with self-attendee responseStatus, missing summary defaults to "(No title)", externalProvider always "google-calendar" (~15+ tests)

   Use `_make_event(**overrides)` fixture factory for building test event dicts with sensible defaults (same pattern as github_field_mapper tests).

3. **Run tests and verify:** `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v`

## Must-Haves

- [ ] `field_mapper.py` has `build_event_properties()`, `compute_event_slug()`, `extract_conference_url()`, `extract_response_status()`, `detect_all_day()`, `extract_rrule()`, `strip_html_tags()`, `extract_body()`
- [ ] All normalization maps (STATUS_MAP, RESPONSE_STATUS_MAP, VISIBILITY_MAP, TRANSPARENCY_MAP) match INTEGRATION-DOMAIN-MAPPING.md §5
- [ ] `externalProvider` is exactly `"google-calendar"`
- [ ] `visibility == "default"` → property omitted
- [ ] `transparency` → `bpkm:showAs` mapping (not `bpkm:transparency`)
- [ ] All-day events produce `bpkm:allDay = "true"` with date values, timed events produce `"false"` with dateTime values
- [ ] ≥40 tests pass in `test_gcal_field_mapper.py`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` — ≥40 tests pass
- `cd backend && .venv/bin/python -m pytest -x` — full suite passes (zero regressions)

## Inputs

- `apps/linear-sync/services/field_mapper.py` — reference implementation for structure, constants pattern, slug computation
- `apps/github-sync/services/field_mapper.py` — second reference confirming the pattern
- `backend/tests/test_github_field_mapper.py` — reference for importlib loading pattern and test structure
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5 — authoritative field mapping spec (Google Calendar Field → bpkm Property → Transform → Direction)
- S01 forward intelligence: Event property list (20 properties), externalProvider = "google-calendar", startDate/endDate lack sh:datatype (must write xsd:dateTime for timed, xsd:date for all-day)

## Expected Output

- `apps/google-calendar/services/field_mapper.py` — ~300 lines, all pure functions, zero side effects
- `backend/tests/test_gcal_field_mapper.py` — ~500 lines, ≥40 tests covering every field transform and edge case
