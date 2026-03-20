# S02: Pull Sync + Field Mapping + Recurrence Conversion

**Goal:** Outlook events sync into SemPKM as bpkm:Event objects with correct field mapping for all ~25 properties, recurrence pattern→RRULE conversion for all 18 combinations, HTML→Markdown body conversion, and delta query-based incremental sync.
**Demo:** User triggers sync → Outlook events appear as bpkm:Event objects with correct times, attendees, categories as tags, showAs, sensitivity→visibility, and RRULE-converted recurrence. HTML bodies converted to Markdown.

## Must-Haves

- `field_mapper.py` with all ~25 field transforms from design doc §6 Outlook field mapping table
- `convert_recurrence_to_rrule()` handling all 18 combinations (6 pattern types × 3 range types)
- HTML→Markdown body conversion via markdownify with `strip_html_tags()` fallback
- Outlook-specific showAs (6 values), sensitivity→visibility (4 values), responseStatus (6 values), and derived eventStatus mappings
- Categories→tags mapping
- `sync_engine.py` with `pull_sync()` using delta queries (`@odata.deltaLink`), per-event error isolation, two-phase bulk create, and `push_sync()` skeleton for S03
- `person_matcher.py` resolving attendee/organizer emails via SPARQL lookup with create-on-miss
- `requirements.txt` listing markdownify dependency
- 130+ unit tests across three test files (80+ field mapper, 40+ sync engine, 12+ person matcher)

## Proof Level

- This slice proves: contract (all field transforms + sync orchestration via unit tests with mocks)
- Real runtime required: no (pure functions + async mocks)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_outlook_field_mapper.py -v` — 80+ tests pass
- `cd backend && python -m pytest tests/test_outlook_sync_engine.py -v` — 40+ tests pass
- `cd backend && python -m pytest tests/test_outlook_person_matcher.py -v` — 12+ tests pass
- `cd backend && python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 130+ total, all green
- At least one sync engine test verifies that per-event errors are isolated (one bad event doesn't abort the sync) and that `last_pull_result` contains the error detail — proving the diagnostic surface works
- At least one test verifies expired delta token recovery (sync engine clears stored delta link and retries with full sync)

## Observability / Diagnostics

- Runtime signals: `outlook.sync` logger — INFO per-calendar event counts, WARNING per-event errors with event_id + traceback; `outlook.sync.person_matcher` logger — DEBUG cache hits, person creation
- Inspection surfaces: `last_pull_result` and `last_push_result` state keys store JSON with status, created/updated/error counts, timestamp
- Failure visibility: per-event errors captured in result `errors` list with event_id + error string; expired delta token logged at INFO then auto-recovered
- Redaction constraints: no secrets in sync logs (tokens handled by auth module)

## Integration Closure

- Upstream surfaces consumed: `services/auth.py` (get_connection_status, refresh_if_expired), `services/outlook_client.py` (OutlookClient, OutlookAPIError), S01 state keys (selected_calendars, client_id, client_secret, access_token)
- New wiring introduced in this slice: field_mapper + person_matcher + sync_engine modules complete the pull pipeline; `app.py` sync_now/task handlers already import sync_engine (skeleton from S01)
- What remains before the milestone is truly usable end-to-end: S03 (push sync + settings UI), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Build Outlook field mapper with recurrence converter and 80+ unit tests** `est:1h30m`
  - Why: The field mapper is the highest-risk piece — the recurrence pattern→RRULE converter is a new algorithm with 18 combinations. All functions are pure with zero I/O, making this ideal for proving first with exhaustive testing.
  - Files: `apps/outlook-calendar/services/field_mapper.py`, `backend/tests/test_outlook_field_mapper.py`
  - Do: Create field_mapper.py with all constant maps (SHOW_AS_MAP, SENSITIVITY_MAP, RESPONSE_STATUS_MAP and reverses), extraction helpers (detect_all_day, extract_conference_url, extract_response_status, extract_body with HTML→Markdown, extract_categories_as_tags, derive_event_status, convert_recurrence_to_rrule), compute_event_slug, build_event_properties, build_event_patch. Recurrence converter handles 6 pattern types (daily, weekly, absoluteMonthly, relativeMonthly, absoluteYearly, relativeYearly) × 3 range types (endDate, numbered, noEnd) with day-of-week and index mappings. Test file covers all 18 recurrence combos + edge cases, all 6 showAs values, all 4 sensitivity values, all 6 response statuses, body extraction (HTML/text/empty), conference URL paths, categories, slug determinism, and full build_event_properties/build_event_patch integration.
  - Verify: `cd backend && python -m pytest tests/test_outlook_field_mapper.py -v` — 80+ tests, all pass
  - Done when: 80+ tests pass covering every mapping table entry and all 18 recurrence combinations

- [x] **T02: Build sync engine + person matcher with 52+ unit tests** `est:1h30m`
  - Why: Wires the field mapper into the pull pipeline with delta query handling, two-phase bulk create, per-event error isolation, and attendee resolution. Completes the pull sync contract.
  - Files: `apps/outlook-calendar/services/sync_engine.py`, `apps/outlook-calendar/services/person_matcher.py`, `apps/outlook-calendar/requirements.txt`, `backend/tests/test_outlook_sync_engine.py`, `backend/tests/test_outlook_person_matcher.py`
  - Do: Clone person_matcher.py from Google Calendar with logger name change. Build sync_engine.py adapting Google's pattern for Outlook delta queries (get_events_delta returns (events, delta_link), delta_link stored via StateClient as `delta_link:{calendar_id}`, expired delta recovery clears link and retries). Handle `@removed` key for deleted events. push_sync skeleton with RSVP push-back structure (full implementation in S03). Create requirements.txt with markdownify. Test sync engine: not-connected skip, no-calendars skip, new event creation, existing event update, deleted event handling, loop prevention via lastSyncedAt, delta link storage/retrieval, expired delta recovery, per-event error isolation, attendee/organizer edge creation, batching. Test person matcher: slugify, email_local_part, cache hit, SPARQL match, create new, None email.
  - Verify: `cd backend && python -m pytest tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 52+ tests, all pass; then full suite `cd backend && python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 130+ total, all green
  - Done when: 52+ sync engine + person matcher tests pass, requirements.txt exists, full 130+ test suite green, at least one test proves error isolation and at least one proves expired delta recovery

## Files Likely Touched

- `apps/outlook-calendar/services/field_mapper.py`
- `apps/outlook-calendar/services/sync_engine.py`
- `apps/outlook-calendar/services/person_matcher.py`
- `apps/outlook-calendar/requirements.txt`
- `backend/tests/test_outlook_field_mapper.py`
- `backend/tests/test_outlook_sync_engine.py`
- `backend/tests/test_outlook_person_matcher.py`
