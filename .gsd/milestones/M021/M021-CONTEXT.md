---
depends_on: [M009, M011]
---

# M021: CalDAV Calendar Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

CalDAV calendar sync app supporting any standards-compliant CalDAV server (Fastmail, Nextcloud, Synology, Radicale, etc.). Bidirectional sync via WebDAV protocol with native iCalendar format — the RRULE and VEVENT fields map most directly to bpkm:Event since both use RFC 5545.

## Why This Milestone

CalDAV covers the self-hosting crowd (Nextcloud, Synology) and privacy-focused email providers (Fastmail, Proton). These users are SemPKM's core audience — self-hosters who care about data ownership. Native iCalendar format means the cleanest field mapping of all calendar providers.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install CalDAV sync app and configure server URL + credentials
- Select calendars to sync
- See iCalendar events as bpkm:Event objects with direct RRULE storage
- See VEVENT fields (SUMMARY, DTSTART, DTEND, LOCATION, STATUS, ATTENDEE) mapped to SemPKM properties
- Edit events bidirectionally via CalDAV PUT

### Entry point / environment

- Entry point: Admin > Applications > Install "CalDAV Calendar Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: CalDAV server (external)

## Completion Class

- Contract complete means: CalDAV PROPFIND/REPORT/PUT, iCalendar parsing, sync-token incremental sync
- Integration complete means: events from Fastmail/Nextcloud sync correctly with all fields
- Operational complete means: polling-based sync, ETag-based conflict detection

## Final Integrated Acceptance

- User configures a Fastmail CalDAV URL, events sync into SemPKM
- RRULE from iCalendar stored directly (no conversion needed)
- Editing an event in SemPKM updates the .ics resource via CalDAV PUT

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § CalDAV — complete field mapping from iCalendar properties
- M018 — Google Calendar sync pattern

## Relevant Requirements

- New: SYNC-14 (CalDAV sync)

## Scope

### In Scope

- CalDAV discovery (well-known URLs, PROPFIND)
- Calendar list via PROPFIND
- Event sync via REPORT (sync-collection with sync-token)
- iCalendar (RFC 5545) parsing and generation
- Direct VEVENT → bpkm:Event field mapping
- ATTENDEE mailto: parsing → Person/Contact matching
- VALARM → reminderMinutes
- CATEGORIES → tags
- PUT for creating/updating events
- DELETE for removing events
- ETag-based optimistic concurrency
- HTTP Basic and OAuth 2.0 auth support

### Out of Scope / Non-Goals

- VTODO (CalDAV tasks), VJOURNAL, VFREEBUSY
- Apple-specific push notifications
- Calendar sharing/ACL management

## Technical Constraints

- CalDAV (WebDAV extension, RFC 4791), iCalendar (RFC 5545)
- `icalendar` Python library for parsing/generation
- Polling-based (no standard push mechanism except Apple)
- App Platform SDK

## Integration Points

- **App Platform (M009)**, **bpkm:Event (M011)**, **M018 patterns**, **CalDAV server (external)**
