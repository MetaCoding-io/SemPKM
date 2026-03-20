---
estimated_steps: 5
estimated_files: 2
---

# T02: Write Playwright E2E test for Outlook Calendar Sync lifecycle

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M020

## Description

Write a Playwright E2E test that proves the full Outlook Calendar Sync lifecycle against the Docker test stack with the mock Microsoft Graph API server from T01. Clone the structure from `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` and adapt for Outlook-specific selectors and OAuth simulation. Add the `outlookCalendarSync` selector block to `e2e/helpers/selectors.ts`.

The test follows the same phase structure as the Google Calendar E2E: cleanup → install basic-pkm → install outlook-calendar → credentials + OAuth → calendar selection → sync config → Sync Now → SPARQL verification → admin detail → uninstall.

**Relevant skill:** Load `~/.gsd/agent/skills/test/SKILL.md` if needed for Playwright patterns.

## Steps

1. **Add `outlookCalendarSync` selector block to `e2e/helpers/selectors.ts`** — insert before the closing `} as const;`. Selectors (verified from `apps/outlook-calendar/frontend/templates/connect.html` and `connect_status.html`):
   ```typescript
   outlookCalendarSync: {
     clientIdInput: '#outlook-client-id',
     clientSecretInput: '#outlook-client-secret',
     credentialsSubmitBtn: '.credentials-form button[type="submit"]',
     connectMicrosoftBtn: '.btn-microsoft',
     connectStatus: '.connection-status',
     accountEmail: '.account-email',
     calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
     saveCalendarsBtn: '.calendars-section button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```

2. **Create `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`** — clone from the Google Calendar E2E test (`e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts`, 399 lines). Use the same import pattern (`auth` fixtures, `SEL`, `waitForIdle`, `waitForWorkspace`). Single test: `'full lifecycle: install → OAuth → sync → verify → cleanup'`.

3. **Implement all 7 phases:**

   **Phase 0 — Cleanup:** Navigate to `/admin/apps`. If `outlook-calendar` is installed from prior run, navigate to admin detail and uninstall. Wait 3s for cleanup.

   **Phase 1 — Install basic-pkm model:** Navigate to `/admin/models`. If basic-pkm not installed, install it. Wait for "Installed" status.

   **Phase 2 — Install outlook-calendar app:** Navigate to `/admin/apps`. Enter `/app/apps/outlook-calendar` in install form, submit. Wait for app card with "Outlook Calendar" text. Navigate to admin detail. Poll until status shows "Running" (retry loop, max 30s). Then `waitForTimeout(5000)` for app subprocess startup (known timing issue per KNOWLEDGE.md).

   **Phase 3 — Enter credentials + simulate OAuth:**
   - Navigate to `/browser/`, wait for workspace, click APPS section header to expand it.
   - Click the Outlook Calendar app link to load the app page.
   - Retry loop for `#connect-content` visibility (app startup timing).
   - Fill `#outlook-client-id` with `mock-client-id`, `#outlook-client-secret` with `mock-client-secret`.
   - Submit credentials form.
   - Simulate OAuth: `ownerRequest.post()` to `${BASE_URL}/app/outlook-calendar/_fragments/connect/microsoft` with `maxRedirects: 0`. Extract `state` param from 303 redirect `Location` header. Navigate browser to callback URL: `${BASE_URL}/app/outlook-calendar/_fragments/oauth-callback?code=mock-auth-code&state=${state}`.
   - Wait for connection status to show the mock user's email.

   **Phase 4 — Select calendars + configure sync:**
   - Check calendar checkboxes (at least 1).
   - Submit calendar selection.
   - Select bidirectional sync direction radio.
   - Submit sync config form.

   **Phase 5 — Sync Now + verify events:**
   - Click `#sync-now-btn`.
   - Wait for sync stats to appear (poll with timeout).
   - Verify at least one stat value shows a non-zero count.

   **Phase 5b — Verify events via SPARQL:**
   - POST to `/api/sparql` to query for `bpkm:Event` objects with `schema:name` containing "Team Standup" (the timed event).
   - Assert at least 1 binding returned.
   - Second SPARQL query for `bpkm:recurrenceRule` — assert the value contains `RRULE:FREQ=WEEKLY`.

   **Phase 6 — Admin detail + cleanup:**
   - Navigate to `/admin/apps/outlook-calendar`.
   - Assert uninstall form is visible.
   - Click uninstall, wait for navigation back to apps list.
   - Best-effort uninstall basic-pkm model.

4. **Set test timeout to 240_000ms** (4 minutes) for Docker operations. Add `ownerPage.on('dialog', ...)` to auto-accept confirm dialogs (hx-confirm on uninstall).

5. **Verify** the file parses: `npx tsc --noEmit e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` or check for TypeScript syntax errors.

## Must-Haves

- [ ] `outlookCalendarSync` selector block added to `e2e/helpers/selectors.ts`
- [ ] E2E test covers all 7 phases: cleanup, basic-pkm install, app install, OAuth simulation, calendar selection, Sync Now, SPARQL verification (events + RRULE), admin uninstall
- [ ] OAuth simulation extracts state from redirect and navigates to callback (same pattern as Google Calendar)
- [ ] SPARQL verification queries for both event existence and RRULE string
- [ ] Retry loops for `#connect-content` visibility and app "Running" status (known timing issues)
- [ ] Test timeout set to 240s for Docker operations

## Verification

- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` exists with all 7 phases
- `grep "outlookCalendarSync" e2e/helpers/selectors.ts` — selector block exists
- File parses without TypeScript errors

## Inputs

- T01 output: `e2e/mock-outlook-api/server.py` — mock server with canned events (timed: "Team Standup", all-day, recurring with weekly pattern)
- T01 output: `docker-compose.test.yml` — `mock-outlook` service wired with env vars
- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — reference implementation (399 lines, same phase structure)
- `e2e/helpers/selectors.ts` — existing selector blocks ending with `googleCalendarSync` block at line 217
- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerRequest`, `BASE_URL`
- `apps/outlook-calendar/frontend/templates/connect.html` — form IDs: `#outlook-client-id`, `#outlook-client-secret`, `.btn-microsoft`
- `apps/outlook-calendar/frontend/templates/connect_status.html` — calendar checkboxes, sync config form, sync-now button
- `apps/outlook-calendar/app.py` — OAuth route at `/_fragments/connect/microsoft` (POST), callback at `/_fragments/oauth-callback`
- Known issues from KNOWLEDGE.md: workspace explorer sections start collapsed (need click to expand APPS), app subprocess startup needs `waitForTimeout(5000)` after "Running" status, Docker test stack volume mounts from worktree

## Observability Impact

- **E2E test phases:** Each phase (0–6) is delimited by comments in the spec file. Playwright's default reporter logs which `expect()` assertion fails, pinpointing the exact phase that broke.
- **Sync stats visibility:** Phase 5 asserts on `.sync-stats` DOM state — the sync result (created/updated counts, status) is rendered server-side and visible in the test's screenshot-on-failure artifact.
- **SPARQL verification:** Phase 5b uses direct API queries — failures report the exact SPARQL query, HTTP status, and response body for diagnosis.
- **Failure inspection:** Run `npx playwright test outlook-calendar-sync.spec.ts --reporter=list` for per-assertion output. Screenshot artifacts in `test-results/` on failure.
- **Mock server health:** `docker compose -f docker-compose.test.yml logs mock-outlook` shows request log for each mock endpoint hit during the test.

## Expected Output

- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — new file, ~400 lines, Playwright E2E test with 7 phases
- `e2e/helpers/selectors.ts` — modified with `outlookCalendarSync` selector block added
