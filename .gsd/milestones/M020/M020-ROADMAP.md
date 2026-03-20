# M020: Outlook Calendar Sync App

**Vision:** Microsoft 365 users can install the Outlook Calendar Sync app, authenticate via Microsoft OAuth, select calendars, and see their Outlook events as bpkm:Event objects with full field mapping — including Outlook-specific showAs values, sensitivity levels, categories as tags, and recurrence pattern→RRULE conversion.

## Success Criteria

- User installs "Outlook Calendar Sync" from Admin > Applications and connects via Microsoft OAuth 2.0
- User selects calendars from their Microsoft 365 account and triggers sync
- Outlook events appear as bpkm:Event objects with correct times, timezone, attendees, location, conference URLs
- Outlook categories appear as bpkm:tags on synced events
- showAs values (busy, free, tentative, out-of-office, working-elsewhere) preserved on events
- sensitivity→visibility mapping works (normal/personal→omit, private→private, confidential→confidential)
- Outlook recurrence patterns (6 types × 3 range types) correctly convert to RFC 5545 RRULE strings
- RSVP status changes in SemPKM push back to Outlook via Graph API PATCH
- Delta queries provide efficient incremental sync (only changed events fetched)
- Settings UI offers calendar selection, sync direction, poll interval, Sync Now
- 200+ unit tests covering auth, client, field mapper (emphasis on recurrence), sync engine, person matcher
- Mock Microsoft Graph API server passes selftest
- Playwright E2E test structurally complete
- User guide Chapter 38 documents Outlook sync with field mapping tables and Azure AD setup

## Key Risks / Unknowns

- **Microsoft Identity Platform OAuth 2.0** — First MS OAuth in the project. Different endpoints (`login.microsoftonline.com`), tenant parameter (`/common/` for multi-tenant), and slightly different token exchange semantics. Must work through the existing app proxy callback path.
- **Recurrence pattern→RRULE conversion** — Outlook uses a structured JSON object (pattern type + range type) that must be converted to RFC 5545 RRULE strings. 6 pattern types × 3 range types = 18 combinations. No library covers this; it's a hand-rolled pure function using the design doc's mapping tables. The relativeMonthly/relativeYearly index→BYDAY mapping is the trickiest part.
- **HTML body conversion** — Outlook `body.content` can be HTML (unlike Google's plain text). Needs `markdownify` or equivalent for HTML→Markdown conversion. Risk is dependency installation in Docker and round-trip fidelity.

## Proof Strategy

- MS OAuth 2.0 → retire in S01 by proving token exchange, refresh, and authenticated Graph API calls through the app proxy callback
- Recurrence conversion → retire in S02 by exhaustive unit tests covering all 18 combinations (6 patterns × 3 ranges) plus edge cases
- HTML body → retire in S02 by proving markdownify works in the app context with representative HTML samples

## Verification Classes

- Contract verification: pytest unit tests (200+ target), mock API server selftest
- Integration verification: Playwright E2E test against Docker stack with mock Graph API
- Operational verification: delta sync token management, token refresh on 401, error isolation per event
- UAT / human verification: none (automated verification sufficient for sync app)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All four slices complete (S01 auth+client, S02 pull+field mapping, S03 push+settings, S04 E2E+docs)
- App installable from Admin > Applications (manifest validates)
- Microsoft OAuth 2.0 connects, tokens persist, refresh works
- Pull sync creates bpkm:Event objects with all mapped fields from design doc §6
- Recurrence pattern→RRULE conversion handles all 18 combinations
- RSVP push-back changes Outlook responseStatus via PATCH
- Delta queries used for incremental sync
- Settings UI functional (calendar selection, direction, interval, Sync Now)
- 200+ pytest unit tests pass in <2s
- Mock Microsoft Graph API server passes selftest
- Playwright E2E test structurally complete
- Chapter 38 user guide published with field mapping tables and Azure AD setup guide
- All htmx URLs use `/app/outlook-calendar/` prefix (grep-verified)
- README TOC, glossary, appendix A env vars, navigation chain updated

## Requirement Coverage

- Covers: SYNC-13 (Outlook calendar sync — new, to be registered during execution)
- Uses existing validated: EVENT-01 (bpkm:Event type), APP-01–14 (App Platform)
- Leaves for later: webhook subscriptions with 3-day auto-renewal (polling-only for v1, per D211 pattern)

## Slices

- [x] **S01: Microsoft OAuth + Graph API Client** `risk:high` `depends:[]`
  > After this: user installs the app, connects via Microsoft OAuth, sees their calendar list with selection checkboxes. Token refresh proven by unit tests.

- [x] **S02: Pull Sync + Field Mapping + Recurrence Conversion** `risk:high` `depends:[S01]`
  > After this: user triggers sync and Outlook events appear as bpkm:Event objects with correct times, attendees, categories as tags, showAs, sensitivity, and RRULE-converted recurrence. HTML bodies converted to Markdown.

- [x] **S03: Push Sync + Settings UI** `risk:low` `depends:[S02]`
  > After this: user changes RSVP status in SemPKM and it pushes to Outlook. Settings UI offers sync direction, poll interval, Sync Now, and sync stats.

- [x] **S04: E2E Tests + User Guide** `risk:low` `depends:[S03]`
  > After this: mock Microsoft Graph API server passes selftest, Playwright E2E test proves install→OAuth→sync→verify→RSVP push lifecycle, Chapter 38 user guide documents everything including Azure AD setup.

## Boundary Map

### S01 → S02

Produces:
- `apps/outlook-calendar/manifest.yaml` — app identity, permissions for `graph.microsoft.com` and `login.microsoftonline.com`
- `apps/outlook-calendar/app.py` — OAuth route handlers (authorize redirect, callback, disconnect), calendar list/selection endpoints
- `apps/outlook-calendar/services/auth.py` — Microsoft OAuth helpers (authorize URL, code exchange, token refresh, store/clear)
- `apps/outlook-calendar/services/outlook_client.py` — REST client for Microsoft Graph API (get_calendar_list, get_events_delta, patch_event) with 401→refresh→retry
- `apps/outlook-calendar/frontend/templates/connect.html` — Azure AD credential form (client ID + secret)
- `apps/outlook-calendar/frontend/templates/connect_status.html` — calendar list with checkboxes
- Unit tests: `test_outlook_auth.py`, `test_outlook_client.py`

### S02 → S03

Produces:
- `apps/outlook-calendar/services/field_mapper.py` — bidirectional field mapping (all ~25 fields per design doc §6), recurrence pattern→RRULE converter, HTML→Markdown body conversion
- `apps/outlook-calendar/services/sync_engine.py` — pull_sync() with delta queries, per-event error isolation, syncToken management
- `apps/outlook-calendar/services/person_matcher.py` — email-based SPARQL attendee/organizer resolution
- Unit tests: `test_outlook_field_mapper.py`, `test_outlook_sync_engine.py`, `test_outlook_person_matcher.py`

### S03 → S04

Produces:
- push_sync() in sync_engine.py — RSVP push-back via Graph API PATCH, loop prevention via lastSyncedAt
- Settings UI — sync direction, poll interval, Sync Now button, sync stats
- Updated `app.py` route handlers for sync-config, sync-now, push-changes
- Additional push-specific unit tests

### S04 (terminal)

Produces:
- `e2e/mock-outlook-api/` — Mock Microsoft Graph API server
- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — Playwright E2E test
- `docs/guide/38-outlook-calendar-sync.md` — user guide Chapter 38
- Docker compose config updates for mock-outlook service
