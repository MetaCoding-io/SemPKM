---
estimated_steps: 6
estimated_files: 2
---

# T02: Playwright E2E test and selectors for CalDAV sync lifecycle

**Slice:** S04 — E2E Tests + User Guide + Docs
**Milestone:** M021

## Description

Create a Playwright E2E test that exercises the full CalDAV sync lifecycle: install basic-pkm model → install caldav-calendar app → enter credentials → select calendars → configure bidirectional sync → Sync Now → verify events via SPARQL → admin detail → cleanup. Follow the Outlook test pattern (`e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`) adapted for CalDAV's simpler auth (HTTP Basic — no OAuth redirect simulation).

Add CalDAV-specific selectors to the shared selectors file.

## Steps

1. **Add `caldavCalendarSync` selector block to `e2e/helpers/selectors.ts`:**
   ```typescript
   caldavCalendarSync: {
     serverUrlInput: '#caldav-server-url',
     usernameInput: '#caldav-username',
     passwordInput: '#caldav-password',
     credentialsSubmitBtn: '.credentials-form button[type="submit"]',
     connectStatus: '.connection-status',
     accountUsername: '.account-username',
     calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]',
     saveCalendarsBtn: '.calendars-section button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```
   Insert before the closing `} as const;`. Note: `accountUsername` (not `accountEmail`) — CalDAV template uses `.account-username` class.

2. **Create `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts`** following the Outlook test's structure. Import from `../../fixtures/auth` and `../../helpers/selectors` and `../../helpers/wait-for`.

3. **Implement Phase 0 (Cleanup):** Try to uninstall `caldav-calendar` app if already installed from a prior run. Use `ownerRequest.delete()` to `${BASE_URL}/admin/apps/caldav-calendar/uninstall` wrapped in try/catch (ignore 404). Accept confirm dialogs.

4. **Implement Phase 1 (Prerequisites) and Phase 2 (Install):**
   - Phase 1: POST to install `basic-pkm` model (skip if already installed — use `/admin/models` page check).
   - Phase 2: POST to install `caldav-calendar` app at path `/app/apps/caldav-calendar`. Navigate to Admin > Applications page, wait for the app card to appear with "Running" status. Click into the app detail page.

5. **Implement Phase 3 (Enter credentials) — this is the key difference from Outlook/Google:**
   - Navigate to `/browser/` workspace page.
   - Wait for workspace to load, expand APPS section (click the section header — sections start collapsed per KNOWLEDGE.md).
   - Click the CalDAV Calendar entry to open the app page.
   - Fill 3 form fields:
     - Server URL: `http://mock-caldav:8080/`
     - Username: `testuser`
     - Password: `testpassword`
   - Click the credentials submit button and wait for the connection status to appear.
   - Assert: `.connection-status` is visible, `.account-username` shows "testuser".
   
   **No OAuth redirect simulation needed** — CalDAV uses HTTP Basic auth, so the credential form POSTs directly to the app's connect endpoint.

6. **Implement Phases 4–6:**
   - **Phase 4 (Select calendars + configure sync):** Check the first calendar checkbox, click save. Select bidirectional sync direction, click save config.
   - **Phase 5 (Sync Now + verify via SPARQL):** Click the Sync Now button, wait for sync stats to appear (`.sync-stats` visible with a `.stat-value`). Then query SPARQL to verify events exist:
     ```sparql
     SELECT ?label WHERE {
       ?s a <urn:bpkm:Event> .
       ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label .
     } ORDER BY ?label
     ```
     Check that results include "Team Standup" and "Company Holiday" (the mock's canned events).
   - **Phase 6 (Admin detail + cleanup):** Navigate to Admin > Applications, click CalDAV Calendar card for detail. Verify task history section exists. Uninstall the app.

## Must-Haves

- [ ] CalDAV selectors in `e2e/helpers/selectors.ts` matching actual template IDs/classes
- [ ] 7-phase test structure: cleanup → prerequisites → install → credentials → calendars → sync+verify → cleanup
- [ ] Phase 3 fills form fields directly (no OAuth simulation)
- [ ] Phase 5 SPARQL verification checks for "Team Standup" event label
- [ ] Dialog auto-accept for hx-confirm on disconnect/uninstall
- [ ] Generous timeouts for Docker operations (120s test timeout, 30s per-action)

## Verification

- File exists at `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts`
- Selectors in `e2e/helpers/selectors.ts` include `caldavCalendarSync` section
- TypeScript syntax is valid: `node -e "const ts = require('typescript'); const src = require('fs').readFileSync('e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts', 'utf8'); const result = ts.transpileModule(src, {compilerOptions: {target: ts.ScriptTarget.ESNext, module: ts.ModuleKind.ESNext}}); console.log('OK');"` (or simply verify no obvious syntax errors by inspection)
- SPARQL query in the test is syntactically valid
- Selectors match actual HTML IDs: `#caldav-server-url`, `#caldav-username`, `#caldav-password`, `#sync-now-btn`

## Inputs

- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — Reference pattern for the 7-phase E2E test structure. CalDAV is simpler in phase 3 (no OAuth).
- `e2e/helpers/selectors.ts` — Existing selectors file to extend with CalDAV section
- `e2e/helpers/wait-for.ts` — `waitForIdle` and `waitForWorkspace` helpers
- `e2e/fixtures/auth.ts` — `ownerPage`, `ownerRequest`, `BASE_URL` exports
- `apps/caldav-calendar/frontend/templates/connect.html` — Template with form field IDs: `#caldav-server-url`, `#caldav-username`, `#caldav-password`
- `apps/caldav-calendar/frontend/templates/connect_status.html` — Template with `.connection-status`, `.account-username`, `#sync-now-btn`, `.sync-stats`, `.calendar-checkbox-item`
- T01 summary — Mock CalDAV server URL pattern and canned event data (Team Standup, Company Holiday, Weekly Review)
- KNOWLEDGE.md — "Workspace explorer sections start collapsed" — must click section header to expand APPS before interacting

## Observability Impact

- **New E2E test file:** `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — exercises the full CalDAV sync lifecycle. Run with `npx playwright test e2e/tests/39-caldav-calendar/` against the Docker test stack.
- **Failure diagnostics:** Test phases are labeled with comments. On failure, the Playwright trace and screenshot show which phase failed. SPARQL verification queries in Phase 5 return concrete event labels — empty results indicate sync engine or field mapper issues.
- **Selector registry:** `caldavCalendarSync` block in `e2e/helpers/selectors.ts` — future agents can find all CalDAV-specific CSS selectors here. If template IDs change, update selectors here and re-run the test.
- **Mock server dependency:** Test requires `mock-caldav` service in `docker-compose.test.yml` (from T01). Health: `curl http://mock-caldav:8080/health`.

## Expected Output

- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — ~350-400 line Playwright test with 7 phases
- `e2e/helpers/selectors.ts` — Modified with `caldavCalendarSync` selector block (~15 selectors)
