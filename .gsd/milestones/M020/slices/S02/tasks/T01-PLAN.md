---
estimated_steps: 8
estimated_files: 2
---

# T01: Build Outlook field mapper with recurrence converter and 80+ unit tests

**Slice:** S02 — Pull Sync + Field Mapping + Recurrence Conversion
**Milestone:** M020

## Description

Create the Outlook Calendar field mapper — all pure functions that transform Microsoft Graph API event dicts into bpkm:Event properties. The centerpiece is `convert_recurrence_to_rrule()`, a hand-rolled converter mapping Outlook's structured recurrence object (6 pattern types × 3 range types = 18 combinations) to RFC 5545 RRULE strings. Also includes HTML→Markdown body conversion, Outlook-specific showAs/sensitivity/responseStatus enum mappings, categories→tags, derived eventStatus logic, and the full property builder.

All functions are pure — no network, no async, no state. This makes them immediately testable with 80+ unit tests covering every mapping table entry and all recurrence combinations.

**Clone source:** `apps/google-calendar/services/field_mapper.py` (258 lines) — adapt the structure but replace Google-specific transforms with Outlook equivalents per design doc §6.

## Steps

1. **Read the Google Calendar field_mapper.py** at `apps/google-calendar/services/field_mapper.py` for the structural pattern (constants, extraction helpers, property builder, reverse mapping). The Outlook version follows the same architecture.

2. **Create `apps/outlook-calendar/services/field_mapper.py`** with these components:

   **Constants:**
   - `BPKM = "urn:sempkm:model:basic-pkm:"`
   - `SHOW_AS_MAP`: `{"free": "free", "tentative": "tentative", "busy": "busy", "oof": "out-of-office", "workingElsewhere": "working-elsewhere", "unknown": "busy"}`
   - `SENSITIVITY_MAP`: `{"normal": None, "personal": None, "private": "private", "confidential": "confidential"}` — None means omit the property
   - `RESPONSE_STATUS_MAP`: `{"none": "needs-action", "organizer": "accepted", "tentativelyAccepted": "tentative", "accepted": "accepted", "declined": "declined", "notResponded": "needs-action"}`
   - `REVERSE_RESPONSE_STATUS_MAP`: reverse of above (for push in S03)
   - `DAY_OF_WEEK_MAP`: `{"sunday": "SU", "monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR", "saturday": "SA"}`
   - `RELATIVE_INDEX_MAP`: `{"first": 1, "second": 2, "third": 3, "fourth": 4, "last": -1}`

   **Extraction helpers (all pure, return None on missing data):**
   - `compute_event_slug(calendar_id, event_id)` — same SHA-256 pattern as Google: `hashlib.sha256(f"{calendar_id}:{event_id}".encode()).hexdigest()[:16]`
   - `detect_all_day(event)` — reads `isAllDay` boolean directly. Returns `(is_all_day, start_value, end_value)`. Outlook start/end are `event["start"]["dateTime"]` and `event["end"]["dateTime"]`
   - `extract_conference_url(event)` — checks `onlineMeeting.joinUrl` then `onlineMeetingUrl` fallback
   - `extract_response_status(event)` — reads `responseStatus.response` directly (NOT from attendees like Google)
   - `derive_event_status(event)` — `isCancelled=True → "cancelled"`, `responseStatus.response=="tentativelyAccepted" → "tentative"`, else `"confirmed"`
   - `extract_body(event)` — checks `body.contentType`: if "html", convert via markdownify (with conditional import + strip_html_tags fallback); if "text", pass through. Returns None if empty/absent
   - `strip_html_tags(text)` — same regex approach as Google: `re.sub(r"<[^>]+>", "", text).strip()`
   - `extract_categories_as_tags(event)` — returns `categories` array joined with `,` or None if empty/missing
   - `extract_rrule(event)` — wrapper that calls `convert_recurrence_to_rrule(event.get("recurrence"))`

   **Recurrence converter (the new algorithm):**
   - `convert_recurrence_to_rrule(recurrence)` — pure function. Input: Outlook recurrence dict `{"pattern": {...}, "range": {...}}` or None. Output: RRULE string (without `RRULE:` prefix) or None.
   - Pattern type → FREQ mapping:
     - `daily` → `FREQ=DAILY`
     - `weekly` → `FREQ=WEEKLY` + `BYDAY=` from `daysOfWeek`
     - `absoluteMonthly` → `FREQ=MONTHLY` + `BYMONTHDAY=` from `dayOfMonth`
     - `relativeMonthly` → `FREQ=MONTHLY` + `BYDAY=` with position prefix (e.g. `2TU` for second Tuesday)
     - `absoluteYearly` → `FREQ=YEARLY` + `BYMONTH=` from `month` + `BYMONTHDAY=` from `dayOfMonth`
     - `relativeYearly` → `FREQ=YEARLY` + `BYMONTH=` from `month` + `BYDAY=` with position prefix
   - `interval > 1` → add `INTERVAL=<n>`
   - Range type mapping:
     - `endDate` → `UNTIL=<endDate formatted as YYYYMMDD>T000000Z`
     - `numbered` → `COUNT=<numberOfOccurrences>`
     - `noEnd` → omit (no UNTIL or COUNT)
   - For relativeMonthly/relativeYearly: `index` from RELATIVE_INDEX_MAP + first day in `daysOfWeek` → e.g. `BYDAY=2TU` (positive index) or `BYDAY=-1FR` (last)

   **Property builder:**
   - `build_event_properties(event, calendar_name, sync_time)` — assembles all properties into a dict. Keys use full BPKM IRIs. Strip None values. Key differences from Google:
     - `schema:startDate` from `event["start"]["dateTime"]`
     - `bpkm:timeZone` from `event["start"]["timeZone"]`
     - `bpkm:eventStatus` from `derive_event_status(event)` (not a direct status field)
     - `bpkm:showAs` from `SHOW_AS_MAP.get(event.get("showAs", ""))`
     - `bpkm:visibility` from `SENSITIVITY_MAP.get(event.get("sensitivity", ""))` — None values excluded
     - `bpkm:tags` from `extract_categories_as_tags(event)`
     - `bpkm:recurrenceRule` from `extract_rrule(event)`
     - `bpkm:recurringEventId` from `event.get("seriesMasterId")`
     - `bpkm:conferenceUrl` from `extract_conference_url(event)`
     - `bpkm:responseStatus` from `extract_response_status(event)`
     - `bpkm:reminderMinutes` from `event.get("reminderMinutesBeforeStart")` if `event.get("isReminderOn")`
     - `bpkm:externalId` from `event.get("id")`
     - `bpkm:externalUrl` from `event.get("webLink")`
     - `bpkm:externalProvider` = `"outlook-calendar"`
     - `dcterms:created` from `event.get("createdDateTime")`
     - `dcterms:modified` from `event.get("lastModifiedDateTime")`

   **Reverse mapping (for S03 push):**
   - `build_event_patch(event_props, microsoft_email)` — RSVP push-back only (per D222). Constructs partial attendees array for PATCH.

3. **Create `backend/tests/test_outlook_field_mapper.py`** using the importlib pattern from `backend/tests/test_gcal_field_mapper.py`. Load from `apps/outlook-calendar/services/field_mapper.py`. Test categories:

   - `compute_event_slug` (2 tests): deterministic, different inputs differ
   - `detect_all_day` (3 tests): isAllDay=true, isAllDay=false, missing field defaults to false
   - `extract_conference_url` (3 tests): onlineMeeting.joinUrl, onlineMeetingUrl fallback, neither
   - `extract_response_status` (7 tests): all 6 responseStatus.response values + missing responseStatus
   - `derive_event_status` (3 tests): isCancelled=true, tentativelyAccepted, default confirmed
   - `extract_body` (4 tests): HTML body with markdownify available, plain text body, empty body, missing body
   - `extract_categories_as_tags` (3 tests): array with items, empty array, missing
   - `strip_html_tags` (2 tests): basic HTML, nested tags
   - `SHOW_AS_MAP` (6 tests): all 6 values
   - `SENSITIVITY_MAP` (4 tests): all 4 values including None cases
   - `convert_recurrence_to_rrule` (25+ tests):
     - 6 pattern types × 3 range types = 18 basic combinations
     - Edge cases: interval > 1, multiple daysOfWeek, None/missing recurrence, relativeMonthly with "last" index, relativeYearly with month + index, daily with endDate
   - `build_event_properties` (5+ tests): full event with all fields, minimal event, Outlook-specific fields, sensitivity None exclusion, categories as tags
   - `build_event_patch` (4 tests): RSVP reverse mapping, no status → empty dict, valid status, unknown status → empty dict

   Create a `_make_event(**overrides)` factory for building Outlook event dicts with sensible defaults.

4. **Handle markdownify conditional import** in field_mapper.py: Use `try: from markdownify import markdownify as md; except ImportError: md = None`. In `extract_body`, if `md` is None and content is HTML, fall back to `strip_html_tags()`. In tests, test both code paths — one where md is available (if installed in test env) and always test the strip_html_tags fallback explicitly.

5. **Run all tests** and iterate until 80+ tests pass with zero failures.

## Must-Haves

- [ ] `field_mapper.py` with all constant maps matching design doc §6 Outlook tables
- [ ] `convert_recurrence_to_rrule()` handles all 18 pattern×range combinations correctly
- [ ] `derive_event_status()` implements the 3-way derived logic (isCancelled, tentativelyAccepted, default)
- [ ] `extract_body()` converts HTML via markdownify with strip_html_tags fallback
- [ ] `build_event_properties()` outputs correct full IRI keys with None values excluded
- [ ] `build_event_patch()` reverse maps RSVP status for push-back
- [ ] 80+ unit tests covering every mapping table entry and all 18 recurrence combinations
- [ ] Conditional markdownify import (no hard dependency in test env)

## Verification

- `cd backend && python -m pytest tests/test_outlook_field_mapper.py -v` — 80+ tests, all pass
- `python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('fm', 'apps/outlook-calendar/services/field_mapper.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('OK')"` — imports without error

## Observability Impact

- **No runtime signals added** — this task produces only pure functions with zero I/O, logging, or state. There are no runtime log lines, metrics, or diagnostic surfaces.
- **Test coverage is the inspection surface:** 103 unit tests verify every mapping table entry and all 18 recurrence combinations. A future agent can re-run `pytest tests/test_outlook_field_mapper.py -v` to verify field mapper correctness.
- **Failure visibility:** If a mapping table is wrong or a recurrence combination regresses, the specific failing test name identifies the exact broken path (e.g., `TestConvertRecurrenceToRrule::test_relative_yearly_end_date`).

## Inputs

- `apps/google-calendar/services/field_mapper.py` — structural pattern to adapt
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §6 — authoritative field mapping tables for Outlook
- S01 outputs: `apps/outlook-calendar/services/auth.py`, `apps/outlook-calendar/services/outlook_client.py` — imported by sync_engine in T02 but not needed here (field_mapper is pure)

## Expected Output

- `apps/outlook-calendar/services/field_mapper.py` — Complete field mapper with all transforms, recurrence converter, and property builders (~300-400 lines)
- `backend/tests/test_outlook_field_mapper.py` — 80+ passing unit tests (~600-800 lines)
