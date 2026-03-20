# M020: Outlook Calendar Sync — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

M020 is a close structural clone of M018 (Google Calendar Sync). The INTEGRATION-DOMAIN-MAPPING.md design doc provides complete Outlook/Microsoft Graph field mapping tables, recurrence pattern→RRULE conversion rules, response status normalization, showAs/sensitivity mappings, and API characteristics. The bpkm:Event type shipped in M018/S01 was explicitly designed as a cross-provider superset (D212) — all Outlook-specific enum values (showAs: out-of-office, working-elsewhere; visibility: confidential) are already present in the SHACL shape.

The main technical differences from Google Calendar are: (1) Microsoft Identity Platform OAuth 2.0 instead of Google OAuth, (2) delta queries (`$deltaToken`) instead of syncToken for incremental sync, (3) Outlook's structured recurrence pattern object must be converted to RFC 5545 RRULE strings (the most complex piece), (4) richer showAs/sensitivity enums, (5) categories→tags mapping (Google has no categories), and (6) `@odata.nextLink` pagination instead of `nextPageToken`.

The recommendation is to clone the M018 app structure verbatim — manifest.yaml, app.py, services/{auth,client,field_mapper,sync_engine,person_matcher}.py — and adapt each module for Microsoft Graph API specifics. The recurrence conversion is the only genuinely new algorithm; everything else is mapping table differences that the design doc already specifies.

## Recommendation

Follow the M018 Google Calendar pattern exactly, adapting for Microsoft Graph API differences. Slice by the same risk ordering: (1) auth + client, (2) pull sync + field mapping, (3) push sync + recurrence, (4) E2E + docs. The recurrence pattern→RRULE converter is the highest-risk piece and should be in the pull sync slice so it's proven before push needs it.

No new platform code changes needed. The bpkm:Event type, App Platform SDK, proxy routing, and all infrastructure from M009/M018 are reused directly.

## Implementation Landscape

### Key Files

**Clone from M018 (apps/google-calendar/) → apps/outlook-calendar/:**

- `manifest.yaml` — Change appId to "outlook-calendar", name, network permissions to `graph.microsoft.com` and `login.microsoftonline.com`, icon to "calendar-clock" or similar
- `app.py` — Adapt OAuth flow from Google to Microsoft Identity Platform. Redirect URI changes to `/app/outlook-calendar/_fragments/oauth-callback`. Microsoft uses `https://login.microsoftonline.com/common/oauth2/v2.0/authorize` and `/token` endpoints. Calendar selection via `GET /me/calendars`
- `services/auth.py` — Microsoft OAuth 2.0 helpers: authorize URL builder, code exchange, token refresh. Microsoft access tokens expire after ~1 hour (same as Google). Scopes: `Calendars.ReadWrite` (or `Calendars.Read` for pull-only)
- `services/outlook_client.py` (was `gcal_client.py`) — REST client for Microsoft Graph API (`https://graph.microsoft.com/v1.0`). Key endpoints: `GET /me/calendars`, `GET /me/calendars/{id}/events/delta` (delta queries), `PATCH /me/events/{id}`. Pagination via `@odata.nextLink`. Rate limit: 10,000 req/10min/mailbox
- `services/field_mapper.py` — The most different module. Maps Outlook field names to bpkm:Event properties per the design doc's §6 table. Key transforms: `subject`→`dcterms:title`, `body.content`→`dcterms:description` (HTML→Markdown), `start.dateTime`+`start.timeZone`→`schema:startDate`+`bpkm:timeZone`, `isAllDay` direct boolean, `showAs`→`bpkm:showAs` (5-value enum with `oof`→`out-of-office`, `workingElsewhere`→`working-elsewhere`), `sensitivity`→`bpkm:visibility` (normal/personal→omit, private→private, confidential→confidential), `categories`→`bpkm:tags`, `recurrence.pattern`+`range`→`bpkm:recurrenceRule` (RRULE conversion), `responseStatus.response`→`bpkm:responseStatus` (6-value mapping), `onlineMeeting.joinUrl`→`bpkm:conferenceUrl`, `seriesMasterId`→`bpkm:recurringEventId`
- `services/sync_engine.py` — Same structure as M018: `pull_sync()` with delta queries, `push_sync()` for RSVP push-back. Delta queries return `@odata.deltaLink` instead of syncToken — functionally identical. 410 Gone equivalent is likely a similar token-expired error requiring full re-sync
- `services/person_matcher.py` — Identical to M018. Email-based SPARQL lookup for attendees/organizer with LRU cache
- `frontend/templates/connect.html` — Microsoft OAuth credential form (Application (client) ID + Client Secret from Azure AD app registration). Different from Google's client_id/client_secret in naming only
- `frontend/templates/connect_status.html` — Calendar list with checkboxes, sync config, sync stats. Same UI pattern as M018
- `frontend/static/styles.css` — Copy from M018

**Test files (backend/tests/):**

- `test_outlook_auth.py` — OAuth flow tests (authorize URL, code exchange, refresh, store tokens)
- `test_outlook_client.py` — REST client tests (calendar list, delta events, patch, pagination, 401→refresh, rate limit)
- `test_outlook_field_mapper.py` — Field mapping tests (all ~25 fields, showAs 6 values, sensitivity 4 values, recurrence conversion 6 pattern types × 3 range types, response status 6 values, all-day detection, conference URL)
- `test_outlook_sync_engine.py` — Sync engine tests (pull with delta, push RSVP, loop prevention, error isolation)
- `test_outlook_person_matcher.py` — Person matcher tests (email lookup, creation, cache)

**E2E and mock server:**

- `e2e/mock-outlook-api/` — Mock Microsoft Graph API server (Express.js like M018's mock-google-calendar-api). Endpoints: `GET /me/calendars`, `GET /me/calendars/{id}/events/delta`, `PATCH /me/events/{id}`, `POST /common/oauth2/v2.0/token`
- `e2e/tests/XX-outlook-sync/outlook-calendar-sync.spec.ts` — Playwright E2E test mirroring M018's google-calendar-sync.spec.ts

**Docs:**

- `docs/guide/38-outlook-calendar-sync.md` — User guide chapter (field mapping tables, Azure AD setup, troubleshooting)

### Build Order

1. **Auth + Client (highest risk):** Microsoft OAuth 2.0 flow through app proxy callback. Prove token exchange, refresh, and authenticated Graph API calls work. Calendar list fetching confirms the client works end-to-end. This unblocks all sync work.

2. **Pull Sync + Field Mapping (second risk — recurrence conversion):** Delta query-based pull sync with all field transforms. The recurrence pattern→RRULE conversion is the most complex algorithm — 6 pattern types × 3 range types with day-of-week mapping. Proving this works unblocks push.

3. **Push Sync + Settings UI (lower risk):** RSVP push-back via PATCH, same pattern as M018. Settings UI for calendar selection, sync direction, poll interval. Low risk — direct adaptation.

4. **E2E + Docs (verification):** Mock Microsoft Graph API server, Playwright E2E test, user guide chapter. Follows M018 pattern exactly.

### Verification Approach

- Unit tests: `cd backend && python -m pytest tests/test_outlook_*.py -v` — target 200+ tests covering auth, client, field mapper (emphasis on recurrence conversion), sync engine, person matcher
- Mock API server selftest: `node e2e/mock-outlook-api/server.js --selftest`
- E2E: `npx playwright test outlook-calendar-sync.spec.ts` against Docker test stack with mock API
- Recurrence conversion specifically: exhaustive unit tests for all 6 pattern types (daily, weekly, absoluteMonthly, relativeMonthly, absoluteYearly, relativeYearly) × 3 range types (endDate, numbered, noEnd) = 18 combinations minimum

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTML→Markdown for body.content | `markdownify` (Python library) | Outlook body.content can be HTML (body.contentType=html). Google Calendar's description is plain text. Need a lightweight HTML→Markdown converter for round-trip fidelity. |
| Recurrence RRULE generation | Manual conversion per design doc tables | No library covers Outlook's pattern object→RRULE. The conversion is a pure function with well-defined mapping tables. Unit test coverage is the safety net. |

## Constraints

- Microsoft Graph API delta queries use `@odata.deltaLink` / `@odata.nextLink` — different JSON structure from Google's syncToken/nextPageToken but functionally equivalent
- Microsoft OAuth requires `tenant` parameter in authorize URL — use `/common/` for multi-tenant (personal + work accounts)
- App proxy query-param forwarding fix from M018 (already landed) is required for OAuth callback to work
- SDK IRI prefix enforcement bypass pattern from D204 is required for bulk create (platform-minted IRIs)
- `markdownify` or equivalent needs to be added to `requirements.txt` for HTML→Markdown body conversion
- Outlook webhook subscriptions expire after ~3 days — but we're polling-only for v1 (D211 pattern), so this is out of scope

## Common Pitfalls

- **Outlook eventStatus is derived, not a direct field** — unlike Google's `status` enum, Outlook derives event status from `isCancelled` + `responseStatus.response`. The field mapper must implement the derivation logic (isCancelled=true → cancelled, tentativelyAccepted → tentative, else → confirmed)
- **Outlook body is HTML by default** — Google Calendar description is plain text. Must check `body.contentType` and convert HTML→Markdown when needed. Plain text bodies should pass through unchanged
- **Outlook sensitivity ≠ Google visibility** — `normal` and `personal` both map to omitting bpkm:visibility (treating as public). `private` and `confidential` are distinct values. Don't conflate them
- **Recurrence daysOfWeek uses lowercase full names** — Outlook uses `["monday", "wednesday"]` while RRULE uses `MO,WE`. Need a lookup map
- **Outlook relativeMonthly/relativeYearly use index + daysOfWeek** — e.g. "second Tuesday" = `{index: "second", daysOfWeek: ["tuesday"]}`. Maps to RRULE `BYDAY=2TU`. The index values are: first/second/third/fourth/last mapping to 1/2/3/4/-1
- **Delta token expiration** — if the delta token has expired, Microsoft Graph returns an error (likely 410 or specific error code). Must handle by falling back to full sync, same as M018's syncToken 410 Gone handling
- **Categories are string arrays** — Outlook categories are simple string arrays, directly mappable to bpkm:tags. Simpler than Google's colorId-only approach
- **App template htmx URLs must use proxy prefix** — per KNOWLEDGE.md, all htmx URLs in templates must be prefixed with `/app/outlook-calendar/` (same fix applied in M016/M018)

## Open Risks

- **Microsoft Identity Platform OAuth complexity** — Azure AD app registration has more configuration than Google Cloud Console (redirect URIs, API permissions, tenant type). The user guide must cover this clearly. For local dev, an "unverified" app works but shows a consent warning
- **Delta query behavior for recurring events** — unclear whether delta returns only the series master or also individual occurrences/exceptions. M018 uses `singleEvents=false` to get masters only. Outlook's `calendarView` endpoint expands recurrence but the `events` endpoint with delta may not. Needs testing during S02
- **HTML body round-trip fidelity** — converting Outlook's HTML body to Markdown and back may lose formatting. Acceptable for v1 — body is supplementary to structured event data
- **`markdownify` dependency** — needs to be installable in the app's venv. If it has heavy C dependencies (unlikely), may need an alternative. Fallback: strip HTML tags with a simple regex

## Sources

- Outlook field mapping, recurrence conversion, response status, sensitivity mapping: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §6
- Calendar sync architecture, conflict resolution: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §Calendar Sync Architecture
- Cross-provider field coverage matrix: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §Calendar Provider Cross-Comparison
- M018 Google Calendar app pattern: `apps/google-calendar/` (manifest, app.py, services/*, frontend/*)
- Microsoft Graph Calendar API: `https://learn.microsoft.com/en-us/graph/api/resources/calendar`
- Microsoft Identity Platform OAuth 2.0: `https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow`
- Outlook recurrence patterns: `https://learn.microsoft.com/en-us/graph/api/resources/recurrencepattern`
