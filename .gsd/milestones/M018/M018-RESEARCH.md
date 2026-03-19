# M018: Google Calendar Sync — Research

**Date:** 2026-03-18

## Summary

Google Calendar sync is the first calendar provider integration and follows the established sync app pattern from M016 (Linear) and M017 (GitHub). The field mapping is fully specified in `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5. The Google Calendar API v3 has excellent sync primitives — `syncToken` for efficient incremental sync and push notification channels for near-real-time updates. The API is REST-based with generous rate limits (1M queries/day, 500/100s/user).

The critical prerequisite is that **`bpkm:Event` does not yet exist** in basic-pkm. Decision D152 explicitly deferred it: "Event type has recurrence (RRULE), attendees, and timezone complexity. Without a calendar provider app to exercise it, it's dead schema." M018 is that calendar provider app — so the Event type must be created as the first slice.

The second major difference from M016/M017 is that **Google requires OAuth 2.0** — there's no API key shortcut. Google's consent screen has strict requirements (app verification for production), but unverified clients work for localhost/test use. This adds OAuth callback routing complexity that the existing sync apps avoided (D200, D206).

## Recommendation

**Prove the Event type first, then layer sync on top.** The highest-risk slice is the bpkm:Event ontology/shapes/views addition to basic-pkm — if the type model is wrong, everything downstream breaks. Second-highest risk is Google OAuth, since it's the first real OAuth flow in a sync app (Linear and GitHub both used API keys). Recurrence handling is complex but well-specified in the design doc.

Follow the M016/M017 app pattern exactly: services directory with client, field_mapper, sync_engine, auth, person_matcher modules. Reuse PersonMatcher from M016 (email-based SPARQL lookup with creation on miss). The field mapping from the design doc is comprehensive enough to code directly from.

Push notifications (webhook channels) should be deferred to a late slice or cut entirely for v1. The App Platform doesn't expose app routes to external traffic (same limitation noted in D200 for Linear webhooks). Polling with syncToken is sufficient and matches the existing pattern.

## Implementation Landscape

### Key Files

- `models/basic-pkm/` — Must be extended with Event type (ontology, shapes, views, seed data). Currently v2.0 with 6 types (Project, Person, Note, Concept, Task, Milestone). Event will be v2.1 or v2.2.
- `apps/linear-sync/` — Reference implementation for sync app pattern. `app.py` (~400 lines) defines routes and task handlers. `services/` contains `linear_client.py`, `auth.py`, `sync_engine.py`, `field_mapper.py`, `person_matcher.py`.
- `apps/github-sync/` — Second sync app, same structure. `services/` contains `github_client.py`, `auth.py`, `sync_engine.py`, `field_mapper.py`, `person_matcher.py`.
- `apps/linear-sync/manifest.yaml` — Reference manifest for task scheduler, permissions, frontend integration.
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5 — Complete Google Calendar → bpkm:Event field mapping with status normalization, recurrence handling, and API characteristics.
- `backend/sdk/` — App SDK with App class, AppContext, scoped clients (commands, graph, state, http, settings).
- `backend/app/apps/` — App Platform: manager.py (lifecycle), proxy.py (HTTP proxy), scheduler.py (task scheduling).

### Build Order

1. **bpkm:Event type in basic-pkm** — Ontology (OWL classes + properties), SHACL shapes, ViewSpecs, seed data. This must land first because the sync app maps to this type. Risk: getting the property set right for all calendar providers, not just Google.
2. **Google OAuth 2.0 + calendar list** — OAuth flow with token storage, refresh token handling, calendar list fetching. Proves the auth works before any sync logic. Risk: OAuth callback routing through the app proxy.
3. **Pull sync with syncToken** — Fetch events from selected calendars, map fields, create bpkm:Event objects via bulk EventStore. Attendee → Person matching. This is the core value delivery.
4. **Push sync (RSVP write-back)** — Detect responseStatus changes in SemPKM, push back to Google Calendar API. Narrow scope — only RSVP, not full event editing.
5. **Recurrence handling** — Store master events with RRULE, individual exceptions when modified. Do NOT expand recurrence. This is complex but well-specified.
6. **E2E tests + docs** — Mock Google Calendar API server, Playwright E2E test, user guide chapter.

### Verification Approach

- **Event type:** Offline pytest validation (same pattern as M011) — parse model, check shapes, run pyshacl.
- **OAuth:** Unit tests with mocked token exchange. E2E test using mock Google API server.
- **Pull sync:** Unit tests for field mapping (Google event JSON → bpkm:Event properties). Integration via mock API server returning canned event data.
- **Push sync:** Unit tests for reverse field mapping + RSVP mutation. Mock API echo-back.
- **Recurrence:** Unit tests for RRULE storage and exception handling.
- **Full lifecycle:** Playwright E2E test: install → OAuth connect → poll → verify events in SPARQL → RSVP change → verify push.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Person email matching | `PersonMatcher` from M016/M017 | Proven SPARQL lookup + creation + LRU cache pattern |
| Field mapping pattern | `field_mapper.py` from M016/M017 | `build_event_properties()` follows same shape as `build_task_properties()` |
| Sync engine pattern | `sync_engine.py` from M016/M017 | Two-phase bulk create, delta sync, lastSyncedAt loop prevention |
| HTTP client | SDK `HttpClient` via `ctx.http` | Domain-enforced, handles auth headers |
| State persistence | SDK `StateClient` via `ctx.state` | Key-value store for tokens, sync cursors, settings |
| iCalendar RRULE parsing | None needed for v1 | Google returns RRULE as string; store it as-is in `bpkm:recurrenceRule`. No need to parse or expand. |

## Constraints

- **bpkm:Event doesn't exist yet.** D152 explicitly deferred it. Must be created in basic-pkm as part of this milestone. The design doc specifies ~20 properties for Event including schema:startDate, schema:endDate, bpkm:timeZone, bpkm:eventStatus, bpkm:attendee, bpkm:organizer, bpkm:recurrenceRule, bpkm:conferenceUrl, bpkm:responseStatus, etc.
- **Google OAuth 2.0 is mandatory.** No API key alternative like Linear (D199) or GitHub PAT (D206). Need client_id and client_secret from Google Cloud Console. Test with unverified OAuth client in dev.
- **App Platform doesn't expose app routes externally** (D200). Google push notification channels require a publicly reachable webhook URL. Polling with syncToken is the v1 approach.
- **OAuth callback URL must route through the app proxy.** The callback URL will be something like `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`. The app proxy (`/app/{appId}/{path:path}`) already handles this pattern.
- **SDK IRI prefix enforcement** (D179). Platform-minted Event IRIs use `urn:sempkm:object:` prefix. Same bypass as M016 (D204) — use direct POST to `/api/commands/bulk` for body/edge commands on platform-minted IRIs.
- **basic-pkm upgrade must be additive** — existing v2.0 data untouched. Use model refresh (MIG-01) for schema update.
- **Google Calendar API quotas:** 1M queries/day, 500/100s/user. Generous, but initial sync of a busy calendar (years of events) should be paginated and respect syncToken for subsequent syncs.

## Common Pitfalls

- **OAuth token refresh** — Google access tokens expire after 1 hour. The app must handle 401 responses by refreshing the token using the refresh token. Linear sync didn't need this (API keys don't expire). The auth module needs a `refresh_if_expired()` helper.
- **All-day event detection** — Google uses `start.date` (no time) for all-day events and `start.dateTime` for timed events. The field mapper must detect which is present and set `bpkm:allDay` accordingly.
- **Timezone handling** — Google returns separate `start.timeZone` alongside `start.dateTime`. Store times as UTC in `schema:startDate`/`schema:endDate` but preserve original timezone in `bpkm:timeZone` for display fidelity.
- **Recurring event instances** — Google returns individual instances on list queries by default. The app should use `singleEvents=false` to get only masters, then handle exceptions individually. Must not create individual Event objects for every occurrence of a weekly meeting.
- **HTML description** — Google Calendar `description` field can contain HTML. Must convert to Markdown before storing in `dcterms:description`.
- **Conference URL extraction** — `conferenceData.entryPoints` is an array. Extract the first entry with `entryPointType: "video"`. Fallback to `hangoutLink` if `conferenceData` is absent.
- **Attendee self-detection** — The user's own RSVP status is in the attendees array where `self: true`. Must find this entry specifically for `bpkm:responseStatus`.
- **syncToken invalidation** — Google may return 410 Gone if syncToken is too old. Must handle by clearing the token and doing a full sync.

## Open Risks

- **OAuth callback routing in App Platform proxy** — No existing sync app has used OAuth callbacks through the proxy. The proxy's `_proxy_to_app()` function handles GET requests and passes query params, but the callback URL configuration with Google Cloud Console needs a fixed URL pattern. If the proxy doesn't forward query params correctly, OAuth will fail. This should be proven in S02 before building sync logic.
- **bpkm:Event property set stability** — The Event type must serve not just Google Calendar but also Outlook (M020) and CalDAV (M021). The design doc's cross-comparison matrix shows Google covers most fields but misses some Outlook-specific ones (showAs values: out-of-office, working-elsewhere). The ontology should include all enum values from the superset, even if Google doesn't use them all.
- **Google OAuth consent screen verification** — For production use, Google requires app verification with privacy policy, homepage, etc. Unverified apps are limited to 100 test users. Not a blocker for v1 (self-hosted, single user) but worth noting for future hosted deployments.
- **syncToken storage and multi-calendar sync** — Each calendar has its own syncToken. With multiple selected calendars, the app needs per-calendar sync state. StateClient stores key-value pairs, so this is straightforward (`sync_token:{calendarId}`) but must be designed correctly from the start.

## Candidate Requirements

Based on the M018-CONTEXT.md scope and INTEGRATION-DOMAIN-MAPPING.md field mapping:

| ID | Requirement | Class | Notes |
|---|---|---|---|
| GCAL-01 | Google OAuth 2.0 authentication with token refresh | core-capability | First real OAuth in a sync app. Client ID/secret from Google Cloud Console. |
| GCAL-02 | Calendar list and selection | core-capability | User picks which calendars to sync (Work, Personal, etc.) |
| GCAL-03 | Pull sync: Google events → bpkm:Event with full field mapping | core-capability | syncToken-based incremental sync. ~20 field mappings per design doc. |
| GCAL-04 | Attendee → Person/Contact matching by email | core-capability | Reuse PersonMatcher pattern from M016/M017. |
| GCAL-05 | Push sync: RSVP status write-back to Google | core-capability | Change responseStatus in SemPKM → update attendee response in Google. |
| GCAL-06 | Recurrence handling (master + exceptions, RRULE storage) | core-capability | Store RRULE string, link exceptions to master via recurringEventId. |
| GCAL-07 | Conference URL extraction (Meet, Zoom links) | core-capability | conferenceData.entryPoints[video].uri or hangoutLink fallback. |
| GCAL-08 | Settings UI (calendar selection, sync direction, poll interval) | core-capability | Follows M016/M017 settings pattern. |
| GCAL-09 | E2E tests + user guide | quality-attribute | Mock Google API server, Playwright E2E, Chapter 36 user guide. |
| EVENT-01 | bpkm:Event type added to basic-pkm | core-capability | Prerequisite. OWL + SHACL + ViewSpecs + seed data. |

**Not a requirement for M018 (future):**
- Push notification channels (webhook-based near-real-time) — blocked by App Platform not exposing external routes
- Full event creation from SemPKM → Google Calendar — complex and low priority for v1
- Meeting notes sync to Google — SemPKM-only field, explicitly listed as "not pushed to Google" in CONTEXT

## Sources

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5 — Complete Google Calendar → bpkm:Event field mapping
- `apps/linear-sync/` — Reference sync app implementation (manifest, app.py, services/)
- `apps/github-sync/` — Second sync app confirming the pattern
- Decision D152 — bpkm:Event deferred until calendar provider app exists
- Decision D200 — App Platform doesn't expose external webhook routes (applies to push notifications)
- Decision D204 — SDK IRI prefix bypass for platform-minted IRIs
- `models/basic-pkm/manifest.yaml` — Current v2.0 model (6 types, no Event)
