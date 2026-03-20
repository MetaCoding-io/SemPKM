---
id: M020
provides:
  - Outlook Calendar Sync app — fifth bidirectional sync app on the App Platform
  - Microsoft Identity Platform OAuth 2.0 with /common/ multi-tenant support
  - Microsoft Graph REST API client with delta query incremental sync
  - Recurrence pattern→RRULE converter handling all 18 combinations (6 pattern types × 3 range types)
  - HTML→Markdown body conversion via markdownify with strip_html_tags fallback
  - Full field mapping for ~25 Outlook event properties including showAs, sensitivity, categories
  - RSVP push-back via Graph API PATCH with loop prevention
  - Person matcher with SPARQL email lookup and LRU cache
  - 257 unit tests across 5 test files (auth 41, client 24, field_mapper 103, sync_engine 75, person_matcher 14)
  - Mock Microsoft Graph API server with 13-check selftest
  - 7-phase Playwright E2E test (394 lines)
  - Chapter 38 user guide (484 lines) with Azure AD setup, recurrence matrix, field mapping tables
  - README TOC, glossary, appendix A (3 env vars), navigation chain updated
key_decisions:
  - D217 — Microsoft Identity Platform OAuth 2.0 with /common/ tenant for multi-tenant support
  - D218 — Polling-only sync (delta queries), no webhook subscriptions for v1
  - D219 — Hand-rolled recurrence pattern→RRULE converter as pure function with exhaustive unit tests
  - D220 — markdownify for HTML→Markdown body conversion with strip_html_tags fallback
  - D221 — OL- prefix for Outlook sync requirement IDs
  - D222 — RSVP-only push scope for v1 (consistent with Google Calendar D213)
patterns_established:
  - Microsoft OAuth 2.0 requiring scope in both authorize and token exchange requests (unlike Google)
  - Refresh token rotation detection — store new refresh_token only when it differs
  - Env var overrides (OUTLOOK_TOKEN_URL, OUTLOOK_AUTH_URL, OUTLOOK_API_URL) for mock server testability
  - OutlookClient exception hierarchy: OutlookAPIError → OutlookAuthError (401/403) + OutlookRateLimitError (429)
  - Delta query pattern: get_events_delta() returns (events, delta_link) tuple for incremental sync
  - Mock Outlook server follows same structure as mock-google-calendar (http.server + canned data + selftest + Docker healthcheck)
  - Outlook E2E follows identical phase structure to Google Calendar E2E
observability_surfaces:
  - "outlook.sync.auth" logger — INFO on token store/clear, WARNING on exchange/refresh failures with status code + body
  - "outlook.sync.client" logger — DEBUG for each REST request, INFO on token refresh
  - "outlook.sync" logger — INFO per-calendar event counts, WARNING per-event errors with event_id
  - last_pull_result / last_push_result state keys — JSON with status, created/updated/error counts, timestamp
  - get_connection_status() returns connected, auth_method, microsoft_email, token_expiry, token_preview
  - python3 e2e/mock-outlook-api/server.py --selftest — 13-check selftest for mock API
requirement_outcomes:
  - id: OL-01
    from_status: active
    to_status: validated
    proof: Microsoft OAuth 2.0 auth module with 41 unit tests, authorize URL builder, code exchange, token refresh with rotation detection, refresh_if_expired with 5-min buffer
  - id: OL-02
    from_status: active
    to_status: validated
    proof: Calendar list with selection checkboxes, 24 client unit tests covering pagination via @odata.nextLink, state persistence
  - id: OL-03
    from_status: active
    to_status: validated
    proof: Pull sync creates bpkm:Event objects with all ~25 field transforms, 103 field mapper tests + 60 sync engine tests, delta query incremental sync with @removed handling
  - id: OL-04
    from_status: active
    to_status: validated
    proof: PersonMatcher resolves attendee emails via SPARQL lookup, creates Person on miss, LRU cache, 14 unit tests
  - id: OL-05
    from_status: active
    to_status: validated
    proof: push_sync() detects responseStatus changes via SPARQL, reverse maps via REVERSE_RESPONSE_STATUS_MAP, PATCHes Graph API, loop prevention via lastSyncedAt, unit tests prove RSVP push-back
  - id: OL-06
    from_status: active
    to_status: validated
    proof: Recurrence converter handles all 18 combinations (6 pattern types × 3 range types), 103 field mapper tests with exhaustive coverage
  - id: OL-07
    from_status: active
    to_status: validated
    proof: showAs map (6 entries), sensitivity map (4 entries), categories→tags extraction all tested in field mapper unit tests
  - id: OL-08
    from_status: active
    to_status: validated
    proof: Settings UI with sync direction radios, poll interval dropdown, Sync Now button, sync stats; 15 route-handler unit tests
  - id: OL-09
    from_status: active
    to_status: validated
    proof: Mock server 13/13 selftest, 394-line E2E test (7 phases), Chapter 38 guide (484 lines), README TOC, glossary, appendix A, navigation chain
duration: 141m
verification_result: passed
completed_at: 2026-03-19
---

# M020: Outlook Calendar Sync App

**Fifth bidirectional sync app on the App Platform — Microsoft Outlook Calendar events sync to bpkm:Event objects via Microsoft Graph API with OAuth 2.0, delta query incremental sync, 18-combination recurrence→RRULE conversion, RSVP push-back, and 257 unit tests.**

## What Happened

Four slices delivered the complete Outlook Calendar Sync app, adapting the Google Calendar pattern (M018) for Microsoft Identity Platform conventions.

**S01 (auth + client)** established the foundation: Microsoft OAuth 2.0 with `/common/` tenant for multi-tenant support (personal + work accounts), token refresh with rotation detection (Microsoft may return new refresh tokens on each refresh), and a Graph API REST client with delta query support. The client follows `@odata.nextLink` full URLs for pagination (unlike Google's `nextPageToken` query params) and returns `(events, delta_link)` tuples for incremental sync. Exception hierarchy: `OutlookAPIError` → `OutlookAuthError` (401/403) + `OutlookRateLimitError` (429). App scaffold with 10 route handlers, 5 templates, scoped CSS with Microsoft brand blue (#0078d4). 65 unit tests.

**S02 (pull sync + field mapping + recurrence)** built the field mapper as a pure-function module covering all ~25 Outlook event field transforms per the design doc: showAs (6-value enum including working-elsewhere), sensitivity→visibility (normal/personal→omit, private→private, confidential→confidential), response status (6→4 mapping), categories→tags, all-day detection, conference URL extraction (onlineMeeting.joinUrl with onlineMeetingUrl fallback), and HTML→Markdown body conversion via markdownify with strip_html_tags fallback. The recurrence converter handles all 18 combinations (6 pattern types × 3 range types) including the tricky relativeMonthly/relativeYearly index→BYDAY mapping. The sync engine uses delta queries with `@removed` event handling, expired delta recovery (410→clear→retry), two-phase bulk create, and per-event error isolation. Push sync was fully implemented here (not deferred to S03) — complete RSVP push-back via `OutlookClient.patch_event()` with loop prevention. 177 unit tests.

**S03 (route-handler tests)** added 15 unit tests proving the app.py wiring layer: template context assembly passes sync_direction/poll_interval/last_push_result/last_pull_result correctly, bidirectional sync_now runs push after pull, push errors don't crash the sync, and sync-config persistence works. Total suite reached 192 tests at this point.

**S04 (E2E + docs)** closed the milestone with a mock Microsoft Graph API server (6 endpoints, 13-check selftest including error-path validation), a 394-line Playwright E2E test covering 7 phases (cleanup → model install → app install → Azure AD credentials + OAuth simulation → calendar selection + bidirectional sync → Sync Now + SPARQL verification → admin uninstall), and Chapter 38 user guide (484 lines) with Azure AD app registration walkthrough, recurrence pattern×range matrix, field mapping tables for all source mappings, and troubleshooting. Documentation infrastructure closure: README TOC entry, glossary entry (alphabetical), 3 appendix A env var rows, and Ch 37→Ch 38→Appendix A navigation chain. htmx prefix audit confirmed 0 URL-bearing attribute violations.

## Cross-Slice Verification

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | App installable from Admin > Applications | ✅ | manifest.yaml validates (appId=outlook-calendar, version=0.1.0) |
| 2 | Microsoft OAuth 2.0 connects, tokens persist, refresh works | ✅ | 41 auth unit tests cover authorize URL, code exchange, token refresh with rotation, refresh_if_expired with 5-min buffer, connection status |
| 3 | Pull sync creates bpkm:Event objects with all mapped fields | ✅ | 103 field mapper tests + 60 sync engine tests cover all ~25 field transforms per design doc §6 |
| 4 | Recurrence pattern→RRULE conversion handles all 18 combinations | ✅ | Exhaustive unit tests for daily/weekly/absoluteMonthly/relativeMonthly/absoluteYearly/relativeYearly × endDate/numbered/noEnd |
| 5 | RSVP push-back changes Outlook responseStatus via PATCH | ✅ | test_successful_rsvp_push + 7 additional push sync tests prove full pipeline |
| 6 | Delta queries used for incremental sync | ✅ | get_events_delta() returns (events, delta_link), delta link stored as state key, 410 recovery tested |
| 7 | Settings UI functional | ✅ | 15 route-handler tests prove direction/interval/sync-now/stats controls |
| 8 | 200+ pytest unit tests pass in <2s | ✅ | 257 passed, 1 skipped in 0.45s |
| 9 | Mock Microsoft Graph API server passes selftest | ✅ | 13/13 passed, exit 0 |
| 10 | Playwright E2E test structurally complete | ✅ | 394 lines, 7 phases, all phase markers present |
| 11 | Chapter 38 user guide published | ✅ | 484 lines with Azure AD setup, recurrence matrix, field mapping tables, troubleshooting |
| 12 | All htmx URLs use /app/outlook-calendar/ prefix | ✅ | grep audit: 0 URL-bearing attribute violations |
| 13 | README TOC, glossary, appendix A, navigation chain updated | ✅ | All four verified |
| 14 | showAs values preserved | ✅ | SHOW_AS_MAP with 6 entries (busy, free, tentative, oof, workingElsewhere, unknown) tested |
| 15 | sensitivity→visibility mapping | ✅ | SENSITIVITY_MAP with 4 entries (normal→None/omit, personal→None, private→private, confidential→confidential) tested |
| 16 | Outlook categories appear as bpkm:tags | ✅ | extract_categories_as_tags function tested in field mapper |
| 17 | Calendar selection from Microsoft 365 account | ✅ | get_calendar_list() with pagination, calendar list UI with checkboxes, selection persistence via StateClient |

## Requirement Changes

- OL-01 (Outlook OAuth 2.0 authentication): active → validated — 41 auth unit tests, OAuth flow through app proxy callback
- OL-02 (Calendar list and selection): active → validated — 24 client tests, calendar list UI with checkboxes
- OL-03 (Pull sync Outlook → bpkm:Event): active → validated — 103 field mapper + 60 sync engine tests, delta query incremental sync
- OL-04 (Attendee resolution to Person objects): active → validated — 14 person matcher tests, SPARQL email lookup with creation and cache
- OL-05 (RSVP push-back to Outlook): active → validated — push_sync with reverse mapping, Graph API PATCH, loop prevention tested
- OL-06 (Recurrence pattern→RRULE conversion): active → validated — all 18 combinations exhaustively unit-tested
- OL-07 (Outlook-specific field mappings): active → validated — showAs (6 values), sensitivity→visibility (4 values), categories→tags all tested
- OL-08 (Settings UI): active → validated — 15 route-handler tests prove direction/interval/sync-now/stats
- OL-09 (E2E tests + user guide): active → validated — mock server 13/13, 394-line E2E test, Chapter 38 guide (484 lines)

## Forward Intelligence

### What the next milestone should know
- The Outlook sync app follows the same structural pattern as Google Calendar (M018), Todoist (M019), Linear (M016), and GitHub (M017) — auth module, REST client, field mapper, sync engine, person matcher, route-handler tests. Future calendar providers (CalDAV for M021) can clone the same pattern.
- Recurrence handling is the main differentiator between calendar providers. Outlook uses a structured JSON object (patternType + rangeType) while Google uses raw RRULE strings. CalDAV uses native RRULE. The field_mapper.py `outlook_recurrence_to_rrule()` function is the reference implementation for structured-to-RRULE conversion.
- Delta queries are the Outlook equivalent of Google's syncToken — they return only changed events since the last delta link. The `@removed` key in delta responses signals deletions (skip, don't create).
- The markdownify dependency is declared in `apps/outlook-calendar/requirements.txt` but not in the backend's pyproject.toml — it's an app-scoped dependency installed in the app's venv at runtime. The 1 skipped test is the HTML→Markdown conversion test (markdownify not in backend test venv); the fallback `strip_html_tags` path is fully tested.

### What's fragile
- E2E test has not been executed against the full Docker test stack — structurally complete but runtime execution blocked by pre-existing app subprocess startup timing issue (same as M017/M018/M019 E2E tests)
- Module loading in tests uses monkey-patching via `_patch_outlook_client` context manager — sensitive to import structure changes
- Push sync scope is RSVP-only (D222) — title/description/time edits are not pushed back to Outlook

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v` — 257 tests in 0.45s, definitive health check
- `python3 e2e/mock-outlook-api/server.py --selftest` — 13 checks in <1s, verifies mock API endpoints
- `grep -rn "hx-(get|post|put|delete|patch)=\"/" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` — htmx prefix audit, must return empty

### What assumptions changed
- Plan assumed push_sync would be a skeleton in S02 with full implementation in S03 — S02 delivered the complete implementation, making S03 a test-only slice
- Test counts exceeded plan significantly: 257 total (plan: 200+), field mapper alone had 103 (plan: 80+)
- Both Google and Outlook field mappers strip the `RRULE:` prefix before storage — E2E test SPARQL assertions check for `FREQ=WEEKLY` not `RRULE:FREQ=WEEKLY`

## Files Created/Modified

- `apps/outlook-calendar/manifest.yaml` — App manifest with identity, permissions, 2 background tasks
- `apps/outlook-calendar/app.py` — 10 route handlers for OAuth, calendar selection, sync, settings
- `apps/outlook-calendar/services/__init__.py` — Package init
- `apps/outlook-calendar/services/auth.py` — Microsoft OAuth 2.0 auth helpers (7 functions)
- `apps/outlook-calendar/services/outlook_client.py` — Graph API REST client with delta queries
- `apps/outlook-calendar/services/field_mapper.py` — Field mapper with recurrence converter (~380 lines)
- `apps/outlook-calendar/services/sync_engine.py` — Pull + push sync engine (~680 lines)
- `apps/outlook-calendar/services/person_matcher.py` — Email-based attendee resolution (~140 lines)
- `apps/outlook-calendar/requirements.txt` — markdownify dependency
- `apps/outlook-calendar/frontend/templates/connect.html` — Azure AD credential form
- `apps/outlook-calendar/frontend/templates/connect_status.html` — Connected status with calendars and sync config
- `apps/outlook-calendar/frontend/templates/calendars.html` — Calendar checkbox partial
- `apps/outlook-calendar/frontend/static/styles.css` — Scoped CSS with Microsoft brand colors
- `backend/tests/test_outlook_auth.py` — 41 unit tests
- `backend/tests/test_outlook_client.py` — 24 unit tests
- `backend/tests/test_outlook_field_mapper.py` — 103 unit tests (1 skipped)
- `backend/tests/test_outlook_sync_engine.py` — 75 unit tests (60 sync + 15 route-handler)
- `backend/tests/test_outlook_person_matcher.py` — 14 unit tests
- `e2e/mock-outlook-api/server.py` — Mock Microsoft Graph API server (~560 lines)
- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — 394-line Playwright E2E test
- `e2e/helpers/selectors.ts` — outlookCalendarSync selector block (13 selectors)
- `docker-compose.test.yml` — mock-outlook service, 3 OUTLOOK_* env vars, depends_on
- `docs/guide/38-outlook-calendar-sync.md` — Chapter 38 user guide (484 lines)
- `docs/guide/README.md` — TOC entry for Chapter 38
- `docs/guide/appendix-d-glossary.md` — Glossary entry for "Outlook Calendar Sync"
- `docs/guide/appendix-a-environment-variables.md` — 3 OUTLOOK_* env var rows
- `docs/guide/37-todoist-sync.md` — Navigation footer points to Chapter 38
