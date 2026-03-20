# M021: CalDAV Calendar Sync App

**Vision:** Sixth sync app on the App Platform — CalDAV calendar events sync bidirectionally with bpkm:Event objects via WebDAV protocol and native iCalendar format, supporting any standards-compliant CalDAV server (Fastmail, Nextcloud, Synology, Radicale).

## Success Criteria

- User installs CalDAV sync app from Admin > Applications and configures server URL + HTTP Basic credentials
- User sees their CalDAV calendar list and selects which to sync
- Synced iCalendar events appear as bpkm:Event objects with all VEVENT fields mapped (SUMMARY, DTSTART, DTEND, LOCATION, STATUS, ATTENDEE, RRULE, VALARM, CATEGORIES, etc.)
- RRULE from iCalendar stored directly as RFC 5545 strings (no conversion needed)
- Editing an event's RSVP status in SemPKM updates the .ics resource via CalDAV PUT with ETag concurrency
- 200+ unit tests pass in <2s covering all field transforms, sync engine, auth, client, and person matcher
- Mock CalDAV server passes selftest and Playwright E2E test exercises install → configure → sync → verify → push lifecycle
- User guide Chapter 39 documents CalDAV setup, field mapping, and troubleshooting

## Key Risks / Unknowns

- **WebDAV XML protocol complexity** — CalDAV uses multi-step XML-over-HTTP (PROPFIND, REPORT, PUT, DELETE) with multiple XML namespaces, unlike the JSON REST APIs of prior sync apps. Hand-crafted XML generation/parsing is error-prone.
- **iCalendar parsing edge cases** — The `icalendar` library returns typed objects (vDate, vDatetime, vCalAddress, vRecur) with different access patterns depending on single vs. multi-value. ATTENDEE can be a single value or list. RRULE's `.to_ical()` includes a prefix that must be stripped.
- **CalDAV server discovery chain varies** — Fastmail, Nextcloud, and Radicale use slightly different XML structures for the well-known → principal → calendar-home → calendar-list discovery. Must handle variants.

## Proof Strategy

- **WebDAV XML protocol** → retire in S01 by building CalDAVClient with real PROPFIND/REPORT/PUT/DELETE XML handling, unit-tested against canned server responses covering Fastmail/Nextcloud variants
- **iCalendar parsing** → retire in S02 by building field mapper with `icalendar` library, exhaustive unit tests for all VEVENT property extraction including edge cases (single vs list ATTENDEE, timezone variants, all-day detection)
- **Discovery chain** → retire in S01 by implementing full well-known → principal → calendar-home → calendar-list chain with unit tests covering multiple server response variants

## Verification Classes

- Contract verification: pytest unit tests for all modules (auth, client XML, field mapper, sync engine, person matcher)
- Integration verification: mock CalDAV server with canned XML/ICS responses + Playwright E2E test through Docker stack
- Operational verification: polling-based sync, ETag-based conflict detection, sync-token incremental sync
- UAT / human verification: none (mock server substitutes for real CalDAV)

## Milestone Definition of Done

This milestone is complete only when all are true:

- CalDAV app installs from admin, credential form accepts URL/username/password
- Calendar discovery chain works (well-known → principal → home → list)
- Pull sync creates bpkm:Event objects with correct field mapping for all VEVENT properties
- Push sync sends RSVP changes back via PUT with ETag concurrency
- 200+ pytest unit tests pass in <2s
- Mock CalDAV server passes selftest
- Playwright E2E test exercises full lifecycle
- Chapter 39 user guide published with field mapping tables
- README TOC, glossary, appendix A, navigation chain updated
- All htmx URLs use `/app/caldav-calendar/` prefix (grep audit: 0 violations)
- All CDAV requirements validated

## Requirement Coverage

- Covers: CDAV-01, CDAV-02, CDAV-03, CDAV-04, CDAV-05, CDAV-06, CDAV-07, CDAV-08, CDAV-09, CDAV-10
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [x] **S01: Auth + CalDAV Client + Calendar Discovery** `risk:high` `depends:[]`
  > After this: user installs CalDAV app, enters server URL + credentials, and sees their calendar list with selection checkboxes. CalDAVClient speaks WebDAV XML (PROPFIND/REPORT/PUT/DELETE) with unit tests proving protocol correctness.
- [x] **S02: Pull Sync + Field Mapping + Person Matching** `risk:medium` `depends:[S01]`
  > After this: user triggers sync and iCalendar events from selected calendars appear as bpkm:Event objects with all VEVENT fields correctly mapped. Settings UI controls sync direction and poll interval.
- [x] **S03: Push Sync + Bidirectional Write** `risk:medium` `depends:[S02]`
  > After this: user changes RSVP status in SemPKM and the change is written back to the CalDAV server via PUT with ETag concurrency. Full event create/delete via PUT/DELETE works with loop prevention.
- [x] **S04: E2E Tests + User Guide + Docs** `risk:low` `depends:[S01,S02,S03]`
  > After this: mock CalDAV server passes selftest, Playwright E2E test proves full install → configure → sync → verify → push lifecycle, Chapter 39 user guide documents everything, README/glossary/appendix updated.

## Boundary Map

### S01 → S02

Produces:
- `apps/caldav-calendar/services/caldav_client.py` — CalDAVClient with `discover_calendars()`, `get_events()` (sync-collection REPORT), `get_event()`, `put_event()`, `delete_event()`. Returns parsed XML as Python dicts.
- `apps/caldav-calendar/services/auth.py` — HTTP Basic credential storage (URL, username, password) via StateClient, connection test via PROPFIND, `get_auth_headers()` returning Authorization header
- `apps/caldav-calendar/app.py` — route handlers for connect, disconnect, calendar selection, static asset serving
- `apps/caldav-calendar/manifest.yaml` — app manifest with `network: ["*"]` wildcard, task definitions
- `apps/caldav-calendar/frontend/templates/connect.html` — credential entry form
- `apps/caldav-calendar/frontend/templates/connect_status.html` — connected status with calendar checkboxes
- `backend/tests/test_caldav_auth.py` — auth unit tests
- `backend/tests/test_caldav_client.py` — WebDAV XML request/response unit tests

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `apps/caldav-calendar/services/field_mapper.py` — `ical_event_to_bpkm()` and `bpkm_to_ical_event()` transforms with all VEVENT↔bpkm:Event property mappings
- `apps/caldav-calendar/services/sync_engine.py` — `pull_sync()` with sync-token incremental sync, two-phase bulk create, per-event error isolation
- `apps/caldav-calendar/services/person_matcher.py` — email-based SPARQL attendee resolution with LRU cache
- Settings UI (sync direction, poll interval, Sync Now, sync stats)
- `backend/tests/test_caldav_field_mapper.py` — all field transform tests
- `backend/tests/test_caldav_sync_engine.py` — pull sync + route handler tests
- `backend/tests/test_caldav_person_matcher.py` — person matching tests

Consumes:
- CalDAVClient from S01 (get_events returns parsed iCalendar data)
- Auth module from S01 (credentials and auth headers)

### S03 → S04

Produces:
- `push_sync()` in sync_engine.py — RSVP push-back via PUT, full event create/update/delete
- `bpkm_to_ical_event()` in field_mapper.py — reverse mapping for .ics generation
- ETag-based optimistic concurrency (If-Match/If-None-Match headers)
- Loop prevention via lastSyncedAt comparison
- Push sync unit tests in test_caldav_sync_engine.py
- Reverse field mapper tests in test_caldav_field_mapper.py

Consumes:
- CalDAVClient.put_event(), delete_event() from S01
- Field mapper forward transforms from S02
- Sync engine pull pipeline from S02

### S04 (terminal)

Produces:
- `e2e/mock-caldav/server.py` — mock CalDAV server with canned XML/ICS responses and selftest
- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — Playwright E2E test
- `docs/guide/39-caldav-calendar-sync.md` — Chapter 39 user guide
- README TOC, glossary, appendix A, navigation chain updates

Consumes:
- Complete CalDAV app from S01-S03
