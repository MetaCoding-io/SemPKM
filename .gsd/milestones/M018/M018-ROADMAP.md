# M018: Google Calendar Sync App

**Vision:** First calendar provider integration — bidirectional sync between Google Calendar and SemPKM's `bpkm:Event` type with OAuth 2.0, syncToken-based incremental sync, attendee matching, RSVP push-back, and recurrence handling.

## Success Criteria

- User installs the Google Calendar sync app from Admin > Applications
- User authenticates via Google OAuth 2.0 and sees their calendar list
- User selects calendars and triggers a sync — events from selected calendars appear as `bpkm:Event` objects with correct times, attendees, location, and conference URLs
- Event attendees are linked to existing Person/Contact objects by email
- User changes RSVP from "tentative" to "accepted" in SemPKM, Google Calendar reflects the change
- Recurring event series stores master with RRULE; individually modified instances stored as separate Events linked to master
- All-day events distinguished from timed events
- Conference URLs (Meet, Zoom) extracted and preserved
- syncToken enables efficient incremental sync on subsequent polls

## Key Risks / Unknowns

- **bpkm:Event type doesn't exist** — D152 deferred it. The ontology/shapes must serve not just Google but Outlook (M020) and CalDAV (M021). Getting the cross-provider property superset right is critical.
- **OAuth callback routing through app proxy** — No existing sync app uses OAuth callbacks. The proxy at `/app/{appId}/{path:path}` must forward query params (code, state) correctly. If it doesn't, OAuth fails.
- **Recurrence complexity** — Google returns RRULE as a string array, individual exceptions as separate events. Must not expand recurring events into individual objects.

## Proof Strategy

- **bpkm:Event type** → retire in S01 by building the complete ontology/shapes/views/seed and validating with pyshacl offline tests + Docker install lifecycle
- **OAuth callback routing** → retire in S02 by completing a real OAuth code exchange through the app proxy and displaying the authenticated user's calendar list
- **Recurrence** → retire in S04 by implementing master+exception storage with unit tests proving RRULE preservation and exception linking

## Verification Classes

- Contract verification: pytest unit tests for field mapping, auth, sync engine, recurrence handling; pyshacl offline validation for Event type
- Integration verification: Mock Google Calendar API server for E2E testing; Docker stack lifecycle (install → configure → sync → verify)
- Operational verification: syncToken persistence across restarts, token refresh on 401, sync state per-calendar
- UAT / human verification: none (mock API sufficient for automated verification)

## Milestone Definition of Done

This milestone is complete only when all are true:

- bpkm:Event type exists in basic-pkm with full OWL ontology, SHACL shapes, ViewSpecs, and seed data
- Google OAuth 2.0 flow works through the app proxy (code exchange, token storage, refresh)
- Pull sync creates bpkm:Event objects with correct field mapping for all ~22 properties
- Attendees resolved to Person objects via email-based SPARQL lookup
- RSVP push-back updates Google Calendar via API PATCH
- Recurring events stored as master + exceptions (no expansion)
- Settings UI allows calendar selection, sync direction, poll interval
- Mock Google Calendar API passes selftest
- Playwright E2E test passes against Docker stack (install → OAuth → sync → verify → RSVP push)
- User guide chapter documents the complete workflow
- Unit test count ≥150, all passing
- All GCAL and EVENT requirements validated

## Requirement Coverage

- Covers: EVENT-01, GCAL-01, GCAL-02, GCAL-03, GCAL-04, GCAL-05, GCAL-06, GCAL-07, GCAL-08, GCAL-09
- Partially covers: none
- Leaves for later: push notification channels (blocked by D200 — App Platform doesn't expose external routes), full event creation from SemPKM → Google (complex, low priority for v1)
- Orphan risks: none

| Requirement | Slice | Role |
|---|---|---|
| EVENT-01 | S01 | primary |
| GCAL-01 | S02 | primary |
| GCAL-02 | S02 | primary |
| GCAL-03 | S03 | primary |
| GCAL-04 | S03 | primary |
| GCAL-05 | S04 | primary |
| GCAL-06 | S04 | primary |
| GCAL-07 | S03 | primary |
| GCAL-08 | S03 | primary, supported by S04 |
| GCAL-09 | S05 | primary |

## Slices

- [x] **S01: bpkm:Event type in basic-pkm** `risk:high` `depends:[]`
  > After this: basic-pkm v2.1 has Event type with OWL ontology, SHACL shapes (22+ properties), ViewSpecs (table/cards/graph), seed data, and Lucide icon. Offline pyshacl validation passes. Model installs cleanly in Docker.

- [ ] **S02: Google OAuth 2.0 + calendar list** `risk:high` `depends:[]`
  > After this: User installs google-calendar app, completes OAuth consent flow, sees their calendar list with selection checkboxes. Auth tokens stored and refresh works. Proven by unit tests against mocked token exchange.

- [ ] **S03: Pull sync + field mapping + settings** `risk:medium` `depends:[S01,S02]`
  > After this: User triggers sync and events from selected calendars appear as bpkm:Event objects with correct fields — times, timezone, attendees linked to Person objects, conference URLs, location, all-day detection. Settings UI controls calendar selection, sync direction, poll interval. Proven by 100+ unit tests.

- [ ] **S04: RSVP push-back + recurrence handling** `risk:medium` `depends:[S03]`
  > After this: User changes RSVP status in SemPKM and it reflects in Google Calendar. Recurring events stored as master (RRULE) + exceptions (linked via recurringEventId). Proven by unit tests for push pipeline and recurrence storage.

- [ ] **S05: E2E tests + user guide** `risk:low` `depends:[S03,S04]`
  > After this: Mock Google Calendar API server passes selftest. Playwright E2E test proves install → OAuth → sync → verify → RSVP push lifecycle. Chapter 36 user guide documents full workflow. All GCAL/EVENT requirements validated.

## Boundary Map

### S01 → S03

Produces:
- `bpkm:Event` OWL class with ~22 properties in basic-pkm ontology (schema:startDate, schema:endDate, bpkm:timeZone, bpkm:eventStatus, bpkm:attendee, bpkm:organizer, bpkm:recurrenceRule, bpkm:conferenceUrl, bpkm:responseStatus, bpkm:allDay, bpkm:location, bpkm:visibility, bpkm:showAs, bpkm:reminderMinutes, bpkm:externalUrl, bpkm:externalId, bpkm:recurringEventId, bpkm:calendarName)
- SHACL NodeShape with property shapes, enums for status/visibility/showAs/responseStatus
- ViewSpecs for table/cards/graph rendering of Events
- Seed data with example events (timed, all-day, recurring)
- Lucide icon entry (`calendar` icon) in manifest

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `apps/google-calendar/` app directory with manifest, app.py skeleton, services/auth.py (OAuth helpers), services/gcal_client.py (REST client)
- OAuth code exchange through app proxy callback URL
- Token storage/refresh via StateClient (access_token, refresh_token, token_expiry)
- Calendar list endpoint returning user's calendars with selection state
- `refresh_if_expired()` helper for transparent token renewal

Consumes:
- nothing (first slice, parallel with S01)

### S03 → S04

Produces:
- `services/field_mapper.py` with `build_event_properties()` and all field transforms
- `services/sync_engine.py` with `pull_sync()` using two-phase bulk create, syncToken, per-calendar state
- `services/person_matcher.py` reusing M016/M017 email-based SPARQL lookup
- Settings routes and templates (calendar checkboxes, direction, interval, Sync Now)
- StateClient keys: `sync_token:{calendarId}`, `selected_calendars`, `sync_direction`, `poll_interval`

Consumes:
- bpkm:Event type from S01 (field mapping targets)
- Auth module from S02 (authenticated Google API client)

### S04 → S05

Produces:
- `push_sync()` for RSVP changes (SPARQL change detection → reverse field mapping → Google PATCH)
- `build_event_patch()` for RSVP reverse mapping
- Recurrence handling in pull_sync (master detection, exception linking, RRULE storage)
- Loop prevention via lastSyncedAt comparison
- push-changes task handler in app.py

Consumes:
- field_mapper, sync_engine, person_matcher from S03
- Auth client from S02

### S05 output

Produces:
- `e2e/mock-google-calendar-api/server.py` — mock REST API with canned responses + selftest
- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — multi-phase Playwright E2E
- `docs/guide/36-google-calendar-sync.md` — user guide chapter
- docker-compose.test.yml updated with mock-google-calendar service
- All GCAL/EVENT requirements moved to validated status

Consumes:
- Complete google-calendar app from S02+S03+S04
- bpkm:Event type from S01
