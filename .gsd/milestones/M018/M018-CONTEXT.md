---
depends_on: [M009, M011]
---

# M018: Google Calendar Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

First calendar provider integration. Bidirectional sync between Google Calendar and SemPKM's `bpkm:Event` type. Leverages Google's syncToken for efficient incremental sync and push notification channels for near-real-time updates. Attendees matched to existing Person/Contact objects by email.

## Why This Milestone

Calendar events are the most frequent structured data people interact with daily. Syncing Google Calendar into SemPKM connects meetings to Projects, generates Tasks (action items), and links attendees to CRM Contacts — relationships that exist nowhere in Google Calendar alone.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install the Google Calendar sync app and authenticate via Google OAuth
- Select which calendars to sync (Work, Personal, etc.)
- See calendar events as `bpkm:Event` objects with times, attendees, location, conference URLs
- See attendees matched to existing Person/Contact objects
- Add meeting notes and action items (linked Tasks) to events in SemPKM
- Change RSVP status in SemPKM and see it reflected in Google Calendar
- See events across all synced calendars in a unified view

### Entry point / environment

- Entry point: Admin > Applications > Install "Google Calendar Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Google Calendar API v3

## Completion Class

- Contract complete means: OAuth flow, syncToken-based incremental sync, field mapping per INTEGRATION-DOMAIN-MAPPING.md, recurrence handling, push-back of RSVP changes
- Integration complete means: events appear with correct times/attendees/location, attendees link to Person objects, conference URLs preserved
- Operational complete means: push notification channels for near-real-time, channel renewal, sync state persists across restarts

## Final Integrated Acceptance

- User syncs their Google Calendar, events from this week appear as bpkm:Event objects
- Event attendees match existing Person/Contact objects by email
- User adds meeting notes to a past event, notes persist in SemPKM (not pushed to Google)
- User changes RSVP from "tentative" to "accepted", Google Calendar reflects the change
- Recurring event series stores master with RRULE; individual exceptions stored separately

## Risks and Unknowns

- **Google OAuth complexity** — Google's consent flow is strict. Need verified OAuth client for production. Test with unverified client in dev.
- **Push notification renewal** — Google Calendar push channels expire after ~7 days. Must auto-renew.
- **Recurrence expansion** — Google expands recurring events on the client side. SemPKM should store only the master + exceptions, not all instances.

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Google Calendar — complete field mapping, status normalization, recurrence handling, sync architecture
- M016 — Linear sync establishes the app pattern
- M011 — basic-pkm v2 with bpkm:Event type

## Relevant Requirements

- New: SYNC-08 (Google Calendar OAuth), SYNC-09 (calendar event sync), SYNC-10 (attendee matching), SYNC-11 (RSVP push-back)

## Scope

### In Scope

- Google OAuth 2.0 authentication
- Calendar list and selection
- Event → bpkm:Event full field mapping
- syncToken-based incremental sync
- Push notification channels for near-real-time updates
- Attendee → Person/Contact matching by email
- Recurrence handling (master + exceptions, RRULE storage)
- RSVP status round-trip
- Conference URL extraction (Meet, Zoom links)
- Settings: calendar selection, sync direction, poll interval

### Out of Scope / Non-Goals

- Google Tasks (separate API, different data model)
- Google Meet integration (beyond URL extraction)
- Calendar sharing/permissions management
- Free/busy availability queries
- Travel time calculation

## Technical Constraints

- Google Calendar API v3 (REST)
- Rate limit: 1M queries/day, 500/100s/user
- App Platform SDK
- Requires bpkm:Event type from M011

## Integration Points

- **App Platform (M009)** — lifecycle, SDK, scheduler
- **bpkm:Event** — mapping target (M011)
- **Person/Contact matching** — email-based lookup
- **Google Calendar API v3** — external dependency
- **M016 patterns** — sync architecture, conflict resolution
