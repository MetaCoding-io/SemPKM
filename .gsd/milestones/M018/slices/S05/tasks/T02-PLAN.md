---
estimated_steps: 8
estimated_files: 2
---

# T02: Playwright E2E test for Google Calendar sync lifecycle

**Slice:** S05 — E2E tests + user guide
**Milestone:** M018

## Description

Build a Playwright E2E test that proves the full Google Calendar sync lifecycle against the Docker test stack with the mock Google Calendar API from T01. Follows the `e2e/tests/32-github-sync/github-sync.spec.ts` pattern. Also adds a `googleCalendarSync` selector block to `e2e/helpers/selectors.ts`.

**Critical constraint — OAuth flow simulation:** The `GOOGLE_AUTHORIZE_URL` in `auth.py` is hardcoded to `https://accounts.google.com/o/oauth2/v2/auth` (no env var override). The browser cannot redirect to the mock for the authorize step. However, the `GOOGLE_TOKEN_URL` IS overridable (pointed at the mock in docker-compose.test.yml). The E2E test must simulate OAuth by:

1. Fill and submit the credentials form (client_id, client_secret)
2. Use `ownerRequest` to POST to the app's `/_fragments/connect/google` endpoint — this returns a 303 redirect to the Google authorize URL
3. Extract the `state` parameter from the redirect Location header
4. Navigate the browser directly to the OAuth callback URL: `http://localhost:3901/app/google-calendar/_fragments/oauth-callback?code=mock-auth-code&state={extracted_state}`
5. The API container receives this callback, exchanges the code via the mock `GOOGLE_TOKEN_URL`, stores tokens, and returns a success page
6. Wait for the success page redirect to `/browser/`

After OAuth, the test selects calendars, configures sync, triggers Sync Now, and verifies events via SPARQL.

**Note on recurrence:** S04/T02 recurrence exception linking code is NOT present in the worktree (confirmed by grep — `_find_event_by_external_id` doesn't exist in sync_engine.py). Include a recurring event in canned data to test RRULE property storage on the master event, but do NOT assert on exception→master edge linking.

## Steps

1. **Add `googleCalendarSync` selector block to `e2e/helpers/selectors.ts`** following the `githubSync` and `linearSync` patterns:
   ```
   googleCalendarSync: {
     clientIdInput: '#gcal-client-id',
     clientSecretInput: '#gcal-client-secret',
     credentialsSubmitBtn: '.credentials-form button[type="submit"]',
     connectGoogleBtn: '.btn-google',
     connectStatus: '.connection-status',
     accountEmail: '.account-email',
     calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
     saveCalendarsBtn: '.calendars-section button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   }
   ```

2. **Create `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts`** with the test structure:
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { SEL } from '../../helpers/selectors';
   ```

3. **Phase 0 — Cleanup:** Remove google-calendar app if installed from prior run. Navigate to `/admin/apps`, check for "Google Calendar" card, uninstall if present. Same pattern as github-sync.spec.ts.

4. **Phase 1 — Install basic-pkm:** Navigate to `/admin/models`, install `/app/models/basic-pkm` if not already installed. Wait for it to appear in model list.

5. **Phase 2 — Install google-calendar app:** Navigate to `/admin/apps`, install `/app/apps/google-calendar`. Wait for status "Running". Wait 5 seconds for app subprocess to start UDS socket.

6. **Phase 3 — Enter credentials + simulate OAuth:**
   - Navigate to workspace `/browser/`
   - Expand APPS sidebar section (click header to toggle `.expanded` — per KNOWLEDGE.md, sections start collapsed)
   - Click the "Google Calendar" app entry to open it
   - Fill credentials form: client_id = `mock-client-id`, client_secret = `mock-client-secret`, submit
   - Wait for form to process
   - Simulate OAuth: use `ownerRequest.post()` to POST to `${BASE_URL}/app/google-calendar/_fragments/connect/google` (this returns a 303 redirect). Extract `state` param from the `location` header (parse the redirect URL).
   - Navigate browser to: `${BASE_URL}/app/google-calendar/_fragments/oauth-callback?code=mock-auth-code&state=${extracted_state}`
   - Wait for the success page (contains "Connected") then wait for redirect to `/browser/`
   - Navigate back to the app page, verify connection status shows "Connected" and account email shows `test@example.com`

7. **Phase 4 — Select calendars + configure sync:**
   - Check the calendar checkboxes (at least one calendar should appear from mock)
   - Save calendar selection
   - Select bidirectional sync direction
   - Save config

8. **Phase 5 — Sync Now + verify events:**
   - Click Sync Now button
   - Wait for sync to complete (wait for `.sync-stats` to appear with result data, or wait for stat-value elements)
   - Verify sync stats show created count ≥ 2 (timed + all-day at minimum)
   - Verify events exist via SPARQL query using `ownerRequest`: `SELECT ?label WHERE { ?s a <urn:bpkm:Event> ; rdfs:label ?label }` — should return at least "Team Standup" and "Company Holiday"
   - Verify one event has RRULE property: `SELECT ?rule WHERE { ?s <urn:bpkm:recurrenceRule> ?rule }` — should return the RRULE string

9. **Phase 6 — Admin detail + cleanup:**
   - Navigate to `/admin/apps/google-calendar` — verify app detail page loads with status info
   - Uninstall the google-calendar app
   - Optionally uninstall basic-pkm (best-effort, may fail if seed data exists)

Set `test.setTimeout(240_000)` for Docker operations. Accept dialog events for hx-confirm on disconnect/uninstall.

## Must-Haves

- [ ] `googleCalendarSync` selector block in `e2e/helpers/selectors.ts`
- [ ] E2E test covers: cleanup → install → OAuth simulation → calendar selection → Sync Now → SPARQL verification of Events → admin page → cleanup
- [ ] OAuth simulation works without redirecting browser to real Google (uses callback URL directly + mock token endpoint)
- [ ] SPARQL verification confirms at least 2 events created with correct labels
- [ ] SPARQL verification confirms RRULE property stored on recurring master

## Verification

- `npx playwright test e2e/tests/36-google-calendar-sync/ --project chromium` passes against Docker stack with mock-google-calendar
- Test exercises real OAuth code exchange flow (API container → mock token endpoint)
- Events verified via SPARQL, not just UI assertion

## Inputs

- `e2e/tests/32-github-sync/github-sync.spec.ts` — reference E2E test pattern (298 lines, 12 phases)
- `e2e/helpers/selectors.ts` — existing selector blocks (githubSync, linearSync)
- `e2e/fixtures/auth.ts` — ownerPage, ownerRequest, BASE_URL exports
- `apps/google-calendar/frontend/templates/connect.html` — CSS IDs: `#gcal-client-id`, `#gcal-client-secret`, `.credentials-form`, `.btn-google`
- `apps/google-calendar/frontend/templates/connect_status.html` — CSS classes: `.connection-status`, `.account-email`, `.calendar-checkbox-item`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`, `.stat-value`
- `apps/google-calendar/app.py` — OAuth flow: POST `/_fragments/connect/google` returns 303 redirect, GET `/_fragments/oauth-callback?code=X&state=Y` exchanges code
- `apps/google-calendar/services/auth.py` — `GOOGLE_AUTHORIZE_URL` hardcoded (line 17), `GOOGLE_TOKEN_URL` has env override (line 18)
- T01 mock server — provides canned responses at `GCAL_API_URL` and `GOOGLE_TOKEN_URL`
- KNOWLEDGE.md — "Workspace explorer sections start collapsed" (must click section header to expand APPS)
- KNOWLEDGE.md — "App template htmx URLs must use proxy prefix" (URLs already use `/app/google-calendar/` prefix in templates)

## Observability Impact

- **Test output:** Playwright HTML report at `e2e/playwright-report/` — shows per-phase timing, screenshots on failure, trace ZIP for replay
- **Failure screenshots:** Auto-captured by Playwright at `e2e/test-results/36-google-calendar-sync-*/test-failed-*.png` on assertion failure
- **Docker logs:** `docker compose -f docker-compose.test.yml logs api` shows the proxy→subprocess requests and any 500 errors from the google-calendar app subprocess
- **Mock server logs:** `docker compose -f docker-compose.test.yml logs mock-google-calendar` shows all `[mock-gcal] METHOD /path → STATUS` lines for debugging API interactions
- **SPARQL verification:** The test uses `ownerRequest.post('/api/sparql')` for event verification — failures show exact SPARQL response in the assertion error message

## Expected Output

- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — new, ~280-350 lines
- `e2e/helpers/selectors.ts` — modified with `googleCalendarSync` block
