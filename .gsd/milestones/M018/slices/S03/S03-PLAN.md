# S03: Pull sync + field mapping + settings

**Goal:** Events from selected Google Calendars sync into SemPKM as bpkm:Event objects with correct field mapping for all ~22 properties, attendees linked to Person objects, and a settings UI controlling sync behavior.
**Demo:** User triggers Sync Now on the Google Calendar app settings page. Events appear as bpkm:Event objects with times, timezone, status, attendees (linked to Person objects by email), conference URLs, location, all-day detection, recurrence rules, and visibility/showAs normalization. Settings control calendar selection, sync direction, and poll interval.

## Must-Haves

- `field_mapper.py` with `build_event_properties()` covering all ~22 field transforms from the INTEGRATION-DOMAIN-MAPPING.md §5 spec
- `compute_event_slug()` for deterministic IRI slug from calendar_id + event_id
- All-day detection via `start.date` vs `start.dateTime` with correct `xsd:date` vs `xsd:dateTime` output
- Conference URL extraction from `conferenceData.entryPoints[type=video].uri` with `hangoutLink` fallback
- Status, visibility, transparency, and responseStatus normalization maps
- RRULE extraction from `recurrence` array (store only, no expansion — S04 handles exceptions)
- HTML tag stripping for description field
- Attendee self-detection for `bpkm:responseStatus` (find `self: true` in attendees array)
- `person_matcher.py` (copy from linear-sync, change logger namespace)
- `GCalClient.get_events()` with syncToken pagination and 410 Gone → full resync handling
- `sync_engine.py` with `pull_sync()` using two-phase bulk create, per-calendar iteration, syncToken state
- Settings UI with sync direction radios, poll interval dropdown, Sync Now button, and sync stats panel
- Task handler `poll-events` wired to real `pull_sync()` call
- `push-changes` task handler remains skeleton (S04 scope)
- `externalProvider` set to `"google-calendar"` on all created Events
- ≥40 field mapper tests, ≥30 sync engine tests, ≥8 person matcher tests

## Proof Level

- This slice proves: contract + integration (all field transforms + async orchestration tested via mocks)
- Real runtime required: no (mocked HTTP, state, graph clients — same pattern as M016/M017)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` — ≥40 pure function tests
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` — ≥30 orchestration tests
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` — ≥8 person matcher tests
- `cd backend && .venv/bin/python -m pytest -x` — full suite must pass with zero regressions
- Jinja2 template syntax check for `connect_status.html`
- All htmx URLs in templates use `/app/google-calendar/` prefix (knowledge: App template htmx URLs must use proxy prefix)

## Observability / Diagnostics

- Runtime signals: `google_calendar.sync` logger — INFO per calendar sync (events fetched, created, updated, errors), WARNING on per-event failures, INFO on syncToken state transitions (fresh sync, incremental, 410 reset)
- Inspection surfaces: `pull_sync()` returns structured dict with `status`, `created`, `updated`, `unchanged`, `errors` per calendar — surfaced in Settings UI sync stats section
- Failure visibility: Per-event error isolation (one bad event doesn't block the calendar), errors array in sync result with event_id + error message, syncToken preserved on partial success
- Redaction constraints: none (no secrets in sync data)

## Integration Closure

- Upstream surfaces consumed: `services/auth.py` (refresh_if_expired, get_connection_status), `services/gcal_client.py` (GCalClient, GCalAPIError), `models/basic-pkm/` (bpkm:Event property IRIs), `_make_client_with_creds()` in app.py
- New wiring introduced in this slice: `poll-events` task handler calls real `pull_sync()`, settings routes save direction/interval/trigger manual sync, `_render_connect_status()` extended with sync config and stats context
- What remains before the milestone is truly usable end-to-end: S04 (RSVP push-back + recurrence exception handling), S05 (E2E tests + user guide)

## Tasks

- [x] **T01: Build field mapper with all property transforms and exhaustive tests** `est:45m`
  - Why: Pure domain logic with zero dependencies — the largest body of complexity in S03. Every Google Calendar API field transform lives here. Tests validate every mapping path independently before the sync engine integrates them.
  - Files: `apps/google-calendar/services/field_mapper.py`, `backend/tests/test_gcal_field_mapper.py`
  - Do: Create `field_mapper.py` with constants (BPKM prefix, STATUS_MAP, RESPONSE_STATUS_MAP, VISIBILITY_MAP, TRANSPARENCY_MAP), `build_event_properties()`, `compute_event_slug()`, `extract_conference_url()`, `extract_response_status()`, `detect_all_day()`, `strip_html_tags()`, `extract_rrule()`. Write ≥40 tests covering: slug determinism, all-day vs timed detection, timezone extraction, status/visibility/transparency/responseStatus normalization, conference URL extraction (conferenceData + hangoutLink fallback), RRULE extraction, HTML stripping, reminder extraction, missing/null field handling, externalProvider = "google-calendar".
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` — ≥40 tests pass
  - Done when: All field transforms from INTEGRATION-DOMAIN-MAPPING.md §5 are implemented and tested

- [x] **T02: Build person matcher, extend GCalClient with get_events, and build sync engine with tests** `est:1h`
  - Why: The sync engine orchestrates field mapper + person matcher + GCalClient into a complete pull pipeline. GCalClient needs `get_events()` with syncToken support. Person matcher is a copy+adapt from linear-sync. All three are testable together with mocked async clients.
  - Files: `apps/google-calendar/services/person_matcher.py`, `apps/google-calendar/services/gcal_client.py`, `apps/google-calendar/services/sync_engine.py`, `backend/tests/test_gcal_person_matcher.py`, `backend/tests/test_gcal_sync_engine.py`
  - Do: (1) Copy `apps/linear-sync/services/person_matcher.py` → adapt logger to `google_calendar.person_matcher`. (2) Add `get_events(calendar_id, sync_token=None)` to GCalClient with `singleEvents=false`, syncToken pagination, 410 Gone handling (clear token + retry as full sync). (3) Build `sync_engine.py` with `pull_sync(ctx)` — iterate selected_calendars, fetch events per calendar, map via field_mapper, match attendees/organizer via person_matcher, two-phase bulk create (object.create → SPARQL discover IRI → body.set + edge.create), update existing events, persist syncToken per calendar. (4) Write ≥8 person matcher tests, ≥30 sync engine tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py tests/test_gcal_sync_engine.py -v` — all pass; `cd backend && .venv/bin/python -m pytest -x` — full suite passes
  - Done when: `pull_sync()` creates/updates bpkm:Event objects with correct properties, attendee/organizer edges, body content, per-calendar syncToken state, and per-event error isolation — all proven by mocked tests

- [x] **T03: Wire settings UI, sync routes, and poll-events task handler** `est:30m`
  - Why: Connects the sync engine to the user-facing UI. Settings let users control sync behavior. The task handler enables scheduled sync. Without this, the sync engine exists but can't be triggered.
  - Files: `apps/google-calendar/app.py`, `apps/google-calendar/frontend/templates/connect_status.html`, `apps/google-calendar/frontend/static/styles.css`
  - Do: (1) Extend `connect_status.html` with Sync Configuration section (direction radios: pull-only/bidirectional, poll interval dropdown: 5m/15m/30m/1h), Manual Sync section (Sync Now button), and Sync Stats section (last sync time, pull result counts, errors). Copy structure from linear-sync's connect_status.html. (2) Add routes in app.py: `POST /_fragments/settings/sync-config` (save direction + interval), `POST /_fragments/sync-now` (run pull_sync and re-render). (3) Wire `poll-events` task handler to call real `pull_sync()`. (4) Extend `_render_connect_status()` with sync config and stats context variables. (5) Verify all htmx URLs use `/app/google-calendar/` prefix.
  - Verify: Jinja2 template syntax check passes; `cd backend && .venv/bin/python -m pytest -x` — full suite passes with no regressions
  - Done when: Settings page shows sync direction, poll interval, Sync Now button, and sync stats; poll-events handler calls real pull_sync

## Files Likely Touched

- `apps/google-calendar/services/field_mapper.py` — new: pure field mapping functions
- `apps/google-calendar/services/person_matcher.py` — new: email-based Person resolution
- `apps/google-calendar/services/sync_engine.py` — new: pull sync orchestration
- `apps/google-calendar/services/gcal_client.py` — modified: add get_events()
- `apps/google-calendar/app.py` — modified: wire task handlers + settings routes
- `apps/google-calendar/frontend/templates/connect_status.html` — modified: add sync config/stats sections
- `apps/google-calendar/frontend/static/styles.css` — modified: add sync config styles
- `backend/tests/test_gcal_field_mapper.py` — new: ≥40 pure function tests
- `backend/tests/test_gcal_sync_engine.py` — new: ≥30 orchestration tests
- `backend/tests/test_gcal_person_matcher.py` — new: ≥8 person matcher tests
