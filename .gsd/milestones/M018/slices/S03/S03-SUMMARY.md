---
id: S03
parent: M018
milestone: M018
provides:
  - field_mapper.py — pure Google Calendar → bpkm:Event property transforms (8 functions, 4 normalization maps)
  - person_matcher.py — email-based Person/Contact resolution via SPARQL with LRU cache
  - sync_engine.py — pull_sync() orchestration with two-phase bulk create, per-calendar syncToken, per-event error isolation
  - GCalClient.get_events() — syncToken pagination, singleEvents=false, 410 Gone handling
  - Settings UI — sync direction, poll interval, Sync Now, sync stats display
  - poll-events task handler wired to real pull_sync()
requires:
  - slice: S01
    provides: bpkm:Event OWL class with ~20 properties, SHACL shapes, enum constraints (property IRIs used as field mapping targets)
  - slice: S02
    provides: OAuth auth module (refresh_if_expired, get_connection_status), GCalClient base class, token storage via StateClient
affects:
  - S04 (consumes field_mapper, sync_engine, person_matcher for RSVP push-back and recurrence exception handling)
  - S05 (consumes complete google-calendar app for E2E tests and user guide)
key_files:
  - apps/google-calendar/services/field_mapper.py
  - apps/google-calendar/services/person_matcher.py
  - apps/google-calendar/services/sync_engine.py
  - apps/google-calendar/services/gcal_client.py
  - apps/google-calendar/app.py
  - apps/google-calendar/frontend/templates/connect_status.html
  - apps/google-calendar/frontend/static/styles.css
  - backend/tests/test_gcal_field_mapper.py
  - backend/tests/test_gcal_sync_engine.py
  - backend/tests/test_gcal_person_matcher.py
key_decisions:
  - "externalProvider hardcoded to 'google-calendar' — consistent with linear-sync ('linear') and github-sync ('github') patterns"
  - "visibility='default' excluded from VISIBILITY_MAP — property omitted per INTEGRATION-DOMAIN-MAPPING spec"
  - "transparency maps to bpkm:showAs (not bpkm:transparency) — Google's transparency field represents availability semantics"
  - "Attendees stored as edges (bpkm:attendee, bpkm:organizer) to Person IRIs via edge.create commands — not as string properties"
  - "Push sync in sync-now and poll-events returns a skipped placeholder when bidirectional — S04 scope"
  - "token_expiry set to 2099 in test fixtures means refresh_if_expired skips HTTP call — tests mock only the GCal events API"
patterns_established:
  - "Same importlib loading pattern as github-sync and linear-sync for test module imports"
  - "Same BPKM full-IRI constant pattern and None-stripping dict comprehension for property builders"
  - "Same sync settings UI pattern as linear-sync: direction radios, poll interval select, sync-now form, sync-stats section"
  - "MockExternalHttpClient with sequential response queue (no token_resp needed when token_expiry is far future)"
observability_surfaces:
  - "google_calendar.sync logger: INFO per calendar (events fetched/created/updated/unchanged), WARNING on per-event failures, INFO on syncToken state transitions"
  - "google_calendar.person_matcher logger: DEBUG on cache hits/misses and person creation"
  - "pull_sync() returns {status, created, updated, unchanged, errors} per calendar — errors array has event_id + error"
  - "State keys: sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result — queryable via ctx.state.get()"
  - "Settings UI Sync Stats section surfaces last sync time, pull result counts, and error details"
drill_down_paths:
  - .gsd/milestones/M018/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M018/slices/S03/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Pull sync + field mapping + settings

**Complete Google Calendar pull sync pipeline — field mapper with 20+ property transforms, person matcher with email SPARQL lookup, sync engine with two-phase bulk create and syncToken incremental sync, settings UI with sync controls and stats — 111 tests all passing, 1609 total suite green.**

## What Happened

Three tasks built the full pull sync pipeline in dependency order:

**T01 (field mapper)** created the pure domain logic in `field_mapper.py` — 8 public functions covering all ~22 Google Calendar → bpkm:Event property transforms. Four normalization maps (`STATUS_MAP`, `RESPONSE_STATUS_MAP`, `VISIBILITY_MAP`, `TRANSPARENCY_MAP`) match the INTEGRATION-DOMAIN-MAPPING.md §5 spec exactly. The `build_event_properties()` function handles all-day detection (xsd:date vs xsd:dateTime), timezone extraction, conference URL extraction (conferenceData with hangoutLink fallback), RRULE extraction, HTML tag stripping for descriptions, reminder minutes, and self-attendee response status detection. 64 tests cover every transform path and edge case.

**T02 (person matcher + GCalClient + sync engine)** built three modules that compose into the pull pipeline. `person_matcher.py` was adapted from linear-sync with the same SPARQL email lookup pattern (foaf:mbox + crm:email), person creation on miss, and in-memory LRU cache. `GCalClient.get_events()` was added with syncToken-based incremental fetching, `singleEvents=false` to get master recurring events, pagination via nextPageToken, and 410 Gone → full resync propagation. `sync_engine.py` implements `pull_sync()` with per-calendar iteration, two-phase bulk create (object.create → SPARQL discover IRI → body.set + edge.create for attendees/organizer), existing-event detection via SPARQL externalId lookup, syncToken persistence per calendar, and per-event error isolation so one bad event doesn't block the calendar. 47 tests cover all pipeline paths.

**T03 (settings UI + routes)** connected the pipeline to the user-facing UI. The `connect_status.html` template gained three new sections: Sync Configuration (direction radios, poll interval dropdown), Manual Sync (Sync Now button with htmx loading indicator), and Sync Stats (last sync time, pull result counts, error display). Two new routes handle settings persistence and manual sync trigger. The `poll-events` task handler was wired to call real `pull_sync()` with state persistence and structured logging.

## Verification

| # | Check | Result | Details |
|---|-------|--------|---------|
| 1 | Field mapper tests (≥40 required) | ✅ 64 passed | `pytest tests/test_gcal_field_mapper.py -v` |
| 2 | Sync engine tests (≥30 required) | ✅ 36 passed | `pytest tests/test_gcal_sync_engine.py -v` |
| 3 | Person matcher tests (≥8 required) | ✅ 11 passed | `pytest tests/test_gcal_person_matcher.py -v` |
| 4 | Full test suite | ✅ 1609 passed | `pytest -x` — zero regressions |
| 5 | Jinja2 template syntax | ✅ OK | Template parsed without errors |
| 6 | htmx URL prefix check | ✅ All 4 URLs use `/app/google-calendar/` | grep confirmed proxy-safe paths |

## Requirements Advanced

- GCAL-03 (Pull sync) — pull_sync() creates bpkm:Event objects with correct field mapping for all ~22 properties, syncToken incremental sync, per-event error isolation. Proven by 36 sync engine tests + 64 field mapper tests.
- GCAL-04 (Attendee resolution) — PersonMatcher resolves attendee/organizer emails to bpkm:Person IRIs via SPARQL lookup, creates on miss, caches per run. Proven by 11 person matcher tests.
- GCAL-07 (All-day detection) — `detect_all_day()` returns `("true", xsd:date)` for `start.date` events and `("false", xsd:dateTime)` for `start.dateTime` events. Proven by 4 dedicated tests.
- GCAL-08 (Conference URL extraction) — `extract_conference_url()` extracts from `conferenceData.entryPoints[type=video].uri` with `hangoutLink` fallback. Proven by 6 dedicated tests.

## Requirements Validated

- GCAL-03 — Pull sync creates bpkm:Event objects with correct times, timezone, attendees, conference URLs, location, all-day, status. 100 tests cover all field transforms and sync orchestration.
- GCAL-04 — Attendees resolved to Person objects by email via SPARQL. 11 person matcher tests cover email match, login fallback, cache, creation.
- GCAL-07 — All-day events produce xsd:date, timed events produce xsd:dateTime. 4 dedicated tests plus full-event integration tests.
- GCAL-08 — Conference URLs extracted from conferenceData + hangoutLink fallback. 6 dedicated tests plus full-event integration tests.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. All three tasks executed cleanly following the plan. The only minor implementation note was that T02 initially had 17 test failures due to mock response queue alignment — the test fixtures set `token_expiry: "2099-..."` which means `refresh_if_expired` returns without consuming a mock HTTP response, so the response queues needed adjustment. This was resolved within T02's execution.

## Known Limitations

- Push sync is a placeholder returning `{"status": "skipped", "message": "Push sync not yet implemented (S04)"}` when bidirectional mode is selected — S04 will implement real RSVP push-back.
- Recurrence handling stores RRULE on master events but does not yet handle individual exception events linked via recurringEventId — S04 scope.
- The sync engine uses direct `/api/commands/bulk` POST bypassing SDK IRI prefix checks, which works for the current app but couples to internal API structure.

## Follow-ups

- S04 must implement push_sync() for RSVP changes and recurrence exception handling (recurringEventId linking).
- S05 needs mock Google Calendar API server for E2E testing — should model the syncToken pagination behavior tested here.

## Files Created/Modified

- `apps/google-calendar/services/field_mapper.py` — new: 8 pure functions, 4 normalization maps, ~165 lines
- `apps/google-calendar/services/person_matcher.py` — new: PersonMatcher class with SPARQL email lookup, creation, LRU cache, ~140 lines
- `apps/google-calendar/services/sync_engine.py` — new: pull_sync() orchestration with two-phase bulk create, ~350 lines
- `apps/google-calendar/services/gcal_client.py` — modified: added get_events() with syncToken, pagination, 410 handling, ~65 new lines
- `apps/google-calendar/app.py` — modified: sync-config route, sync-now route, poll-events handler, extended _render_connect_status()
- `apps/google-calendar/frontend/templates/connect_status.html` — modified: Sync Configuration, Manual Sync, Sync Stats sections
- `apps/google-calendar/frontend/static/styles.css` — modified: sync-config, sync-now, sync-stats CSS sections
- `backend/tests/test_gcal_field_mapper.py` — new: 64 tests across 10 test classes
- `backend/tests/test_gcal_sync_engine.py` — new: 36 tests covering find_existing_event, command builders, batch submission, full pull_sync
- `backend/tests/test_gcal_person_matcher.py` — new: 11 tests covering email lookup, cache, edge cases, slugify

## Forward Intelligence

### What the next slice should know
- `pull_sync()` returns a structured dict `{status, created, updated, unchanged, errors}` per calendar — S04's push_sync should return the same shape for UI consistency.
- Attendees are stored as edges (bpkm:attendee to Person IRI) not as string properties — RSVP push-back in S04 needs to query these edges to find the self-attendee's Person IRI and map back to Google's attendee list.
- The sync engine already handles `recurringEventId` as a property on pulled events — S04 just needs to add the exception→master linking logic.
- The person matcher is copied from linear-sync. All three sync apps now have identical copies — a future refactor could extract to a shared SDK utility.

### What's fragile
- **Mock response queue alignment** — Tests use a sequential `MockExternalHttpClient` response queue. Adding any HTTP call to the sync pipeline (e.g., for push sync) requires adding corresponding mock responses to every test's queue. The `token_expiry: "2099"` trick avoids token refresh responses but any new API call in the flow will break all existing tests if not accounted for.
- **Direct /api/commands/bulk POST** — The sync engine bypasses SDK IRI prefix checks by posting directly to the commands API. If the commands API changes its bulk endpoint shape, the sync engine breaks silently.

### Authoritative diagnostics
- `pytest tests/test_gcal_field_mapper.py -v` — 64 tests for all property transforms, run in <0.1s. If a field mapping is wrong, this test file pinpoints exactly which transform function failed.
- `pytest tests/test_gcal_sync_engine.py -v` — 36 tests for the full pipeline. `TestPullSync*` classes test the end-to-end flow including person matching, body creation, and syncToken state.
- State key `last_pull_result` in app state contains the full sync result dict — inspect this first when debugging a sync failure.

### What assumptions changed
- No assumptions changed. The S03 plan was accurate and all implementation decisions from S01/S02 (property IRIs, auth module API, GCalClient base) held up cleanly.
