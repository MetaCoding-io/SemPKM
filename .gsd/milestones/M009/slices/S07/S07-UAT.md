# S07: Test App, E2E Tests & Integration Proof — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: This slice's entire purpose is proving the full vertical works against a live Docker stack. Artifact-only verification would miss the integration gaps this slice is designed to catch.

## Preconditions

1. Docker test stack running from the project root:
   ```bash
   docker compose -f docker-compose.test.yml up -d --build
   ```
2. Stack is healthy: `docker compose -f docker-compose.test.yml ps` shows all 3 services (api, frontend, triplestore) as "Up"
3. API service can reach the triplestore: `docker compose -f docker-compose.test.yml logs api | grep -i "ready"` shows startup success
4. `apps/test-app/` directory exists and is volume-mounted into the api container
5. `backend/sdk/` directory exists and is volume-mounted into the api container
6. Test app is NOT currently installed (clean state). If installed from a prior run, uninstall first via admin UI.

## Smoke Test

Navigate to `http://localhost:3901/admin/apps`. The Applications page loads with an install form visible. Enter `/app/apps/test-app` in the path input and click Install. Within 60 seconds, the test app card should appear with "running" status badge.

## Test Cases

### 1. Install test app via admin portal

1. Navigate to `http://localhost:3901/admin/apps`
2. Verify the "Applications" heading is visible
3. Enter `/app/apps/test-app` in the "App Directory" input
4. Click "Install"
5. Wait up to 120 seconds, refreshing the page periodically
6. **Expected:** A card labeled "Test Application" appears with a green "running" status badge

### 2. Verify admin detail page

1. Click on the "Test Application" card or navigate to `http://localhost:3901/admin/apps/test-app`
2. **Expected:** Page shows:
   - "Test Application" in h1
   - Status badge shows "running"
   - PID stat box shows a numeric value (not "—")
   - Permissions section lists "object.create"
   - Task History section shows "heartbeat" task

### 3. Verify workspace APPS sidebar

1. Navigate to `http://localhost:3901/browser/`
2. Wait for workspace to load
3. Click the "APPS" section header in the left sidebar to expand it
4. **Expected:** A tree-leaf entry labeled "Test App" appears inside the APPS section

### 4. Load app page fragment in workspace

1. Click the "Test App" tree-leaf in the APPS sidebar section
2. Wait up to 30 seconds for content to load
3. **Expected:** A panel opens showing content with the text "Test Application" and an element with `id="test-app-main"` is visible

### 5. Verify right pane section via API

1. In a browser or curl, request: `GET http://localhost:3901/browser/apps/right-pane-sections?iri=urn:sempkm:test:example`
2. **Expected:** Response is HTTP 200 with HTML containing "test-app-right-pane" and "Test Info"

### 6. Verify command palette API

1. Request: `GET http://localhost:3901/api/apps/commands`
2. **Expected:** JSON array containing an object with `id: "test-command"`, `label: "Test App Command"`, `appId: "test-app"`

### 7. Stop and restart app

1. Navigate to `http://localhost:3901/admin/apps/test-app`
2. Click the "Stop" button
3. **Expected:** Status badge changes to "stopped"
4. Click the "Start" button
5. Wait up to 60 seconds, refreshing periodically
6. **Expected:** Status badge changes back to "running"

### 8. Uninstall app and verify removal

1. Navigate to `http://localhost:3901/admin/apps/test-app`
2. Click the "Uninstall" button and accept the confirmation dialog
3. **Expected:** Redirected to `/admin/apps` list page
4. **Expected:** "Test Application" card is no longer present
5. Navigate to `http://localhost:3901/browser/`
6. Expand the APPS sidebar section
7. **Expected:** No "Test App" tree-leaf entry visible
8. Request: `GET http://localhost:3901/api/apps/commands`
9. **Expected:** No command with `id: "test-command"` in the response

### 9. Run Playwright E2E spec

1. From the project root, run:
   ```bash
   npx playwright test --project=chromium e2e/tests/30-app-platform/app-platform.spec.ts
   ```
2. **Expected:** All 7 phases pass (40 assertions). Test duration 60–180 seconds depending on Docker performance.

## Edge Cases

### Re-install after uninstall

1. After test case 8 (uninstall), repeat test case 1 (install)
2. **Expected:** App installs cleanly, fresh venv created, running status achieved

### Install with already-installed app

1. With test app running, navigate to admin apps page
2. Enter `/app/apps/test-app` and click Install
3. **Expected:** Error message or redirect with notice that app is already installed

### Uninstall with clean_data=True

1. Install the test app
2. Via curl or direct form POST: `POST /admin/apps/test-app/uninstall` with `clean_data=true`
3. Check Docker API logs: `docker compose -f docker-compose.test.yml logs api | grep "Cleaning triplestore data"`
4. **Expected:** Log shows "Cleaning triplestore data for app test-app" followed by "Triplestore data cleaned for app test-app"

## Failure Signals

- "Applications" page shows no install form → admin router not mounted, check api startup logs
- Install hangs past 120 seconds → venv creation or SDK install failing, check `docker compose logs api | grep test-app`
- Status badge stuck on "installing" → subprocess failed to start, check for socket errors in api logs
- "Test App" not appearing in workspace APPS section → `apps_explorer` endpoint returning empty, check if section htmx-loaded content is present but hidden (section collapsed)
- Right pane API returns 404 → browser apps router not mounted
- Command palette API returns empty → app registry not populated after install
- E2E spec fails at Phase 3 → sidebar section not expanded, check if `.expanded` class toggle is being handled

## Requirements Proved By This UAT

- APP-01 — manifest validates (test app exercises all fields)
- APP-02 — subprocess lifecycle (install, start, stop, restart, uninstall)
- APP-03 — SDK used (decorators, route handlers, task handler, lifecycle hooks)
- APP-04 — IPC proxy (fragment content served through platform proxy)
- APP-07 — standalone page (APPS sidebar → fragment in workspace)
- APP-08 — workspace contributions (right pane section, command palette entry via API)
- APP-09 — renderer override declared (manifest declares urn:sempkm:test:TestRenderedType)
- APP-10 — admin monitoring (list card, detail page, stop/start/uninstall actions)
- APP-13 — DB tables (app_instances created/deleted during lifecycle)
- APP-14 — Docker integration (volume mounts, nginx proxy verified by E2E)

## Not Proven By This UAT

- APP-05 (permission enforcement runtime) — test app declares permissions but enforcement is not exercised end-to-end (would need the app to make a forbidden API call and verify rejection)
- APP-06 (task scheduler execution) — task config is visible in admin but actual task firing/recording not verified in E2E (would need waiting for scheduler interval to elapse)
- APP-11 (bulk EventStore) — test app does not exercise ctx.commands.bulk()
- APP-12 (browserVisible) — test app does not declare types with browserVisible: false
- APP-09 (renderer override execution) — manifest declares the renderer but no test object of type urn:sempkm:test:TestRenderedType is created to verify the override renders

## Notes for Tester

- **First run timing**: The first install takes longer (30–60s) because Docker needs to create the venv and pip-install the SDK. Subsequent installs after uninstall reuse cached pip packages.
- **Collapsed sections**: The workspace sidebar sections start collapsed. You must click the section header (e.g., "APPS") to expand it before looking for tree-leaf entries.
- **Docker stack sync**: If running from a worktree, ensure the Docker test stack sees the current backend code. Volume mounts resolve from the CWD where docker-compose was started.
- **Known rough edge**: The uninstall confirmation dialog uses `hx-confirm` which triggers a browser `confirm()` dialog. If the dialog is dismissed, uninstall is cancelled.
