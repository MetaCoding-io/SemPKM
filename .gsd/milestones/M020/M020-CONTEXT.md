---
depends_on: [M009, M011]
---

# M020: Outlook Calendar Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Microsoft Outlook/365 calendar sync via Microsoft Graph API. Bidirectional sync of events to `bpkm:Event` objects with delta query support for efficient incremental sync. Covers the enterprise/Microsoft 365 user segment.

## Why This Milestone

Outlook is the dominant enterprise calendar. Microsoft Graph API has delta queries (similar to Google's syncToken) and webhook subscriptions. Recurrence pattern-to-RRULE conversion is the main technical challenge.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install Outlook sync app and authenticate via Microsoft OAuth
- Select calendars to sync from their Microsoft 365 account
- See Outlook events as bpkm:Event objects with full field mapping
- See Outlook categories mapped to tags
- See showAs values (busy, free, out-of-office, working-elsewhere) preserved
- Change RSVP status in SemPKM, reflected in Outlook

### Entry point / environment

- Entry point: Admin > Applications > Install "Outlook Calendar Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Microsoft Graph API

## Completion Class

- Contract complete means: Microsoft OAuth, delta queries, field mapping per INTEGRATION-DOMAIN-MAPPING.md, recurrence pattern→RRULE conversion
- Integration complete means: events with attendees, showAs, categories all mapped correctly
- Operational complete means: webhook subscriptions with 3-day renewal, delta sync, error handling

## Final Integrated Acceptance

- User syncs Outlook calendar, events appear with correct times, attendees, locations
- Outlook recurrence pattern correctly converts to RFC 5545 RRULE
- Outlook categories appear as tags on events
- showAs values (out-of-office, working-elsewhere) preserved for Outlook-specific values

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Outlook — complete mapping tables, recurrence conversion, response status, sensitivity mapping
- M018 — Google Calendar sync app pattern

## Relevant Requirements

- New: SYNC-13 (Outlook calendar sync)

## Scope

### In Scope

- Microsoft Identity Platform OAuth 2.0
- Microsoft Graph REST API for calendar operations
- Event field mapping per design doc
- Recurrence pattern → RRULE conversion
- Delta queries for incremental sync
- Webhook subscriptions with auto-renewal
- Sensitivity → visibility mapping
- showAs → bpkm:showAs mapping (5 values including Outlook-specific)
- Categories → tags mapping
- Attendee → Person/Contact matching

### Out of Scope / Non-Goals

- Outlook Mail sync, Outlook Tasks (To Do), Teams chat, OneDrive

## Technical Constraints

- Microsoft Graph API, App Platform SDK, requires bpkm:Event type (M011)
- Webhook subscriptions expire after ~3 days — auto-renewal required

## Integration Points

- **App Platform (M009)**, **bpkm:Event (M011)**, **M018 patterns**, **Microsoft Graph API**
