# S05: E2E tests + user guide — Research

**Date:** 2026-03-19

## Summary

S05 is straightforward application of two well-established patterns: (1) mock API server + Playwright E2E test (done for Linear in M016/S04 and GitHub in M017/S04), and (2) user guide chapter (done for both at chapters 34 and 35). The Google Calendar variant adds one twist: the E2E test must simulate an **OAuth 2.0 flow** rather than a simple API key paste, since GCal is the first sync app using OAuth. The mock server needs to handle both the token exchange endpoint and the Calendar REST API.

**Key finding:** S04/T02 (recurrence exception linking) code is **not present** in the current worktree. The commit `825ce955` (state-rebuild) only contains T01 (RSVP push-back). The sync_engine.py has 634 lines / 57 tests, matching the T01-only state. The T02 summary claims 71 tests and `_find_event_by_external_id` helper — neither exist in the file. The E2E test and user guide should document recurrence as specified in the roadmap but the mock server canned data and E2E assertions should focus on what actually works: pull sync, RSVP push, field mapping. Include a recurring event in canned data to test RRULE storage on the master, but don't assert on exception→master linking since that code is missing.

**Approach:** Three independent tasks — mock server (standalone, selftest-verifiable), E2E test (depends on mock server + docker-compose wiring), and user guide (independent of code). Build order: mock server first (unblocks E2E), then E2E and guide can be parallel or sequential.

## Recommendation

Follow the M017/S04 pattern exactly. Three tasks:

1. **Mock Google Calendar API server** — Python `http.server` at `e2e/mock-google-calendar-api/server.py`. Must handle: `GET /health`, `POST /oauth/token` (code exchange + refresh), `GET /calendar/v3/users/me/calendarList`, `GET /calendar/v3/calendars/{id}/events` (with syncToken pagination), `PATCH /calendar/v3/calendars/{id}/events/{id}` (RSVP echo-back). Selftest mode with `--selftest` flag. Docker service in `docker-compose.test.yml` mapped via `GCAL_API_URL` and `GOOGLE_TOKEN_URL` env vars.

2. **Playwright E2E test** — `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts`. Phases: cleanup → install basic-pkm → install google-calendar → enter OAuth credentials → simulate OAuth (direct state injection since redirect flow can't hit mock in browser) → select calendars → configure sync → Sync Now → verify Events via SPARQL → verify RSVP push → admin detail → cleanup.

3. **User guide** — `docs/guide/36-google-calendar-sync.md`. Chapter 36 following chapter 35 structure: prerequisites, installation, OAuth setup, calendar selection, sync configuration, field mapping tables, RSVP push-back, recurrence handling, admin monitoring, troubleshooting. Plus README TOC, glossary entries, appendix-a env var, navigation chain update.

## Implementation Landscape

### Key Files

**Mock server:**
- `e2e/mock-google-calendar-api/server.py` — **new**. Same pattern as `e2e/mock-github-api/server.py` (404 lines). Needs ~6 endpoints. Canned event data should include: one timed event with attendees + conference URL, one all-day event, one recurring master with RRULE. Return `nextSyncToken` on events list. PATCH echoes back merged data (for RSVP verification).
- `docker-compose.test.yml` — **modify**. Add `mock-google-calendar` service (same shape as `mock-github`), add `GCAL_API_URL` and `GOOGLE_TOKEN_URL` env vars to `api` service, add `mock-google-calendar` to `depends_on`.

**E2E test:**
- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — **new**. ~250 lines following `32-github-sync/github-sync.spec.ts` pattern.
- `e2e/helpers/selectors.ts` — **modify**. Add `googleCalendarSync` selector block (CSS IDs/classes from `connect.html` and `connect_status.html`).

**User guide:**
- `docs/guide/36-google-calendar-sync.md` — **new**. ~300 lines following chapter 35 structure.
- `docs/guide/README.md` — **modify**. Add chapter 36 to TOC.
- `docs/guide/appendix-d-glossary.md` — **modify**. Add "Google Calendar Sync" entry.
- `docs/guide/appendix-a-environment-variables.md` — **modify**. Add `GCAL_API_URL` and `GOOGLE_TOKEN_URL` entries.
- `docs/guide/35-github-sync.md` — **modify**. Update navigation footer: Next → Chapter 36.

**Requirements:**
- `.gsd/REQUIREMENTS.md` — **modify**. Move GCAL-05, GCAL-06, GCAL-09 to validated (GCAL-05/06 proven by existing unit tests; GCAL-09 proven by this slice).

### Build Order

1. **Mock server + docker-compose wiring** (T01) — unblocks T02. Build the canned response data, selftest, and Docker service definition. Verify with `python server.py --selftest`.

2. **E2E test** (T02) — depends on T01 for mock server. The trickiest part is the OAuth flow simulation. The browser can't complete a real OAuth redirect to the mock (the redirect URL goes through the app proxy which renders an HTML page). Two options:
   - **Direct state injection via API** — After installing the app, use `ownerRequest` to POST credentials to the app's credentials endpoint, then inject OAuth tokens directly into app state by calling the connect endpoint with pre-exchanged tokens. The mock's `/oauth/token` endpoint returns valid tokens when the API container calls it.
   - **Credential + OAuth initiate** — Enter client_id/secret via the credentials form, then POST to the `connect/google` route which redirects to the mock's authorize URL. The mock redirects back to the callback URL with a code. The callback handler exchanges the code via the mock's token endpoint.
   
   The second approach is cleaner — the mock server should have a `/authorize` endpoint that immediately redirects back with `?code=mock-auth-code&state={state}`. The app's OAuth callback then exchanges the code via the mock token endpoint. This tests the real OAuth flow end-to-end.

3. **User guide** (T03) — independent of T01/T02. Pure documentation following chapter 35 pattern.

### Verification Approach

- **Mock server:** `python e2e/mock-google-calendar-api/server.py --selftest` — must pass all endpoint checks (≥8 checks).
- **E2E test:** `npx playwright test e2e/tests/36-google-calendar-sync/ --project chromium` against Docker stack with mock service.
- **User guide:** File exists at correct path, README TOC updated, glossary entries present, navigation chain intact (Ch 35 → Ch 36 → Appendix A).
- **Requirements:** GCAL-05, GCAL-06, GCAL-09 moved to validated in REQUIREMENTS.md with proof references.

## Constraints

- **OAuth redirect flow in E2E** — The real OAuth flow redirects the browser to Google. In the E2E test, the mock must handle the authorize URL pattern. The `GCAL_API_URL` env var overrides the Calendar API base URL but the authorize URL is hardcoded in `auth.py` to `https://accounts.google.com/o/oauth2/v2/auth`. The E2E test can't redirect to Google. Solution: the mock token endpoint at `GOOGLE_TOKEN_URL` handles code exchange without the browser redirect — inject credentials + tokens via the app's form endpoints and API state, or add a `GOOGLE_AUTHORIZE_URL` env var override.
- **`GOOGLE_TOKEN_URL` already has env var override** — `auth.py` line 18: `GOOGLE_TOKEN_URL = os.environ.get("GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")`. This means the Docker test stack can point token exchange at the mock.
- **`GCAL_API_URL` already has env var override** — `gcal_client.py` line 17: `GCAL_BASE_URL = os.environ.get("GCAL_API_URL", "https://www.googleapis.com/calendar/v3")`. Calendar API calls can be redirected to the mock.
- **No `GOOGLE_AUTHORIZE_URL` env var** — `auth.py` line 17 hardcodes `GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"`. The browser redirect can't reach the mock. The E2E test must simulate OAuth by: (a) entering credentials, (b) directly calling the mock token endpoint to get tokens, then (c) storing tokens in app state via the app's callback URL with a mock code. Since the API container (not the browser) calls the token endpoint, and the token URL IS overridable, the real code exchange flow works container-to-container. The browser just needs to navigate to the callback URL with the right query params.
- **S04/T02 recurrence linking code missing from worktree** — The `_find_event_by_external_id` helper and recurrence linking phase are not in `sync_engine.py`. Mock data should include a recurring event to test RRULE property storage, but don't assert on exception→master edge linking.
- **Selectors** — `connect.html` uses: `#connect-content`, `#gcal-client-id`, `#gcal-client-secret`, `.credentials-form`, `.btn-google`. `connect_status.html` uses: `.connection-status`, `.account-email`, `.calendar-checkbox-item`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`, `.stat-group`, `.stat-row`.

## Common Pitfalls

- **OAuth flow in E2E vs container** — The browser redirect to Google's authorize URL can't be intercepted. The cleanest E2E approach: (1) fill credentials form, (2) use `ownerRequest` to POST directly to the `/_fragments/connect/google` route which returns a redirect, (3) extract the state param from the redirect URL, (4) navigate directly to the app's callback URL with `?code=mock-auth-code&state={extracted_state}`. The API container then calls the mock token endpoint to exchange the code. This tests the full auth pipeline without needing to redirect the browser to an external URL.
- **htmx URL prefix** — Per KNOWLEDGE.md, all htmx URLs in app templates must use `/app/google-calendar/` prefix. The connect.html and connect_status.html templates already have this. The E2E test must interact through the proxy.
- **Explorer sections start collapsed** — Per KNOWLEDGE.md, the APPS sidebar section is collapsed by default. The E2E test must click the section header to expand before clicking the app leaf.
- **Mock server response format** — Google Calendar API returns `{"kind": "calendar#calendarList", "items": [...]}` and `{"kind": "calendar#events", "items": [...], "nextSyncToken": "..."}`. The mock must match this structure exactly because `GCalClient` parses `items`, `nextPageToken`, and `nextSyncToken` fields.
- **RSVP push verification** — After Sync Now with bidirectional, the E2E test should verify push stats show in the UI. But actually triggering a push requires modifying an event's responseStatus after pull — which means a second sync. Simpler: just verify pull works and push stats section appears. The push pipeline is proven by 32 unit tests.

## Open Risks

- **OAuth callback in E2E browser** — The callback URL `http://localhost:3000/app/google-calendar/_fragments/oauth-callback?code=X&state=Y` must work when navigated to directly. The app proxy must forward the query params (proven in S02 — D210 fixed this). But the callback handler renders an HTML page that auto-redirects to `/browser/` — the E2E test needs to wait for this redirect before checking connection status.
- **App subprocess startup time** — Per existing E2E patterns (GitHub/Linear), there's a 5-second wait after installation for the app to start its UDS socket. Google Calendar app is similar complexity, so the same wait applies.

## Sources

- `e2e/mock-github-api/server.py` — Reference mock server (404 lines, 9 selftest checks, REST)
- `e2e/mock-linear-api/server.py` — Reference mock server (GraphQL variant)
- `e2e/tests/32-github-sync/github-sync.spec.ts` — Reference E2E test (12 phases, 299 lines)
- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — Reference E2E test (similar structure)
- `docs/guide/35-github-sync.md` — Reference user guide chapter (310 lines, field mapping tables, troubleshooting)
- `e2e/helpers/selectors.ts` — Selector registry pattern (`githubSync`, `linearSync` blocks)
- `apps/google-calendar/frontend/templates/connect.html` — CSS IDs for credential form
- `apps/google-calendar/frontend/templates/connect_status.html` — CSS classes for status display
