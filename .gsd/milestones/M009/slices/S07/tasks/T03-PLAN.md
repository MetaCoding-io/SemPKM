---
estimated_steps: 5
estimated_files: 2
---

# T03: Write Playwright E2E specs for app platform

**Slice:** S07 — Test App, E2E Tests & Integration Proof
**Milestone:** M009

## Description

Write a Playwright E2E spec file that proves the full app platform vertical — install → workspace page → right pane → command palette → admin monitoring → uninstall. This is the milestone's integration proof. Uses a single `test()` function to maintain sequential execution and avoid rate limit issues (matching the established pattern from `admin-model-lifecycle.spec.ts`).

The test runs against the Docker test stack on port 3901. It uses the `ownerPage` fixture from `e2e/fixtures/auth.ts` for authenticated browser context and `ownerRequest` for direct API calls.

**Relevant skills:** `test` (for test patterns)

## Steps

1. **Add app platform selectors to `e2e/helpers/selectors.ts`** — Add a new `apps` section to the `SEL` object:
   ```typescript
   apps: {
     adminList: '/admin/apps',
     adminDetail: '/admin/apps/test-app',
     installForm: 'form[action*="install"]',
     statusBadge: '.badge',
     appCard: '.app-card',
     sidebarAppsSection: 'details:has(> summary .explorer-section-title)',
     workspaceAppPage: '#test-app-main',
     rightPaneSection: '#test-app-right-pane',
     commandDialog: '#test-app-command-dialog',
   },
   ```
   Keep it minimal — these are CSS selectors used in the spec, not data-testid (those don't exist yet for app platform elements).

2. **Create `e2e/tests/30-app-platform/app-platform.spec.ts`** — Single spec file with one `test.describe` and one long sequential `test()`:

   **Imports:**
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   ```

   **Test structure** — one `test()` covering these phases:

   **Phase 1: Install test app via admin**
   - Navigate to `${BASE_URL}/admin/apps`
   - Verify page loads (h1 contains "Applications")
   - Look for an install form. The admin list page has a form that POSTs to `/admin/apps/install` with `app_path` field.
   - Fill the app_path input with `test-app` (the relative path under `/app/apps/`)
   - Submit the install form
   - Wait for the page to settle (redirect back to `/admin/apps` or to detail page)
   - Use generous timeout (60s) — app install includes venv creation and SDK install
   - Verify the test app appears in the app list with a status badge

   **Phase 2: Verify admin detail page**
   - Navigate to `${BASE_URL}/admin/apps/test-app`
   - Wait for page load
   - Verify the page shows the app name "Test Application"
   - Verify a PID or status indicator is visible
   - Verify the Permissions section is visible (should mention "object.create")
   - Verify the Tasks section is visible (should mention "heartbeat")

   **Phase 3: Verify app page in workspace**
   - Navigate to `${BASE_URL}/` (workspace)
   - Wait for the workspace to load (sidebar visible)
   - Find the APPS section in the left sidebar (look for text "APPS" in the sidebar)
   - Wait for the APPS explorer content to load (htmx lazy-load)
   - Verify "Test App" appears in the APPS explorer section
   - Click on "Test App" to open the app page tab
   - Wait for the app page content to load in the editor area
   - Verify `#test-app-main` is visible (the fragment content from the SDK app)
   - Verify text "Test Application" appears in the content

   **Phase 4: Verify right pane section**
   - The right pane sections load dynamically when viewing an object. We need an object in the workspace.
   - Navigate to create a new object or open an existing one — use the workspace URL for a known type
   - Wait for the right pane dynamic content to load
   - Look for a `<details>` element containing "Test Info" in the right pane area
   - Note: The right pane uses `GET /browser/apps/right-pane-sections?iri=<IRI>` which merges platform + app sections. The test app's right pane targets `["*"]` so it should appear for any object.

   **Phase 5: Verify command palette API**
   - Use `ownerPage.evaluate` or the `ownerRequest` fixture to check `GET /api/apps/commands`
   - Verify the response JSON includes an entry with `id: "test-command"` and `label: "Test App Command"`
   - This is an API check, not a UI check — the command palette UI integration is verified by the API returning correct data

   **Phase 6: Admin actions (stop/restart)**
   - Navigate to `${BASE_URL}/admin/apps/test-app`
   - Click the "Stop" button
   - Wait for the page to refresh/update
   - Verify status shows "stopped"
   - Click the "Start" button (or "Restart")
   - Wait for status to return to "running" (with generous timeout for health check)

   **Phase 7: Uninstall**
   - On the admin detail page, find the uninstall form
   - The uninstall form POSTs to `/admin/apps/test-app/uninstall`
   - Check the `clean_data` checkbox if present, or submit the form with clean_data=true
   - Wait for redirect to `/admin/apps` list
   - Verify the test app no longer appears in the list
   - Navigate to workspace and verify APPS section is empty or doesn't show "Test App"

3. **Handle timing and reliability:**
   - App install takes 10-30s in Docker — use `{ timeout: 60000 }` for install-related waits
   - Health check polling takes up to 30s after start — use `{ timeout: 45000 }` for "running" status waits
   - htmx content loads are async — use `waitForSelector` or `waitForResponse` for fragment loads
   - Right pane loads via `fetch()` + `innerHTML` swap — may need `page.waitForResponse('**/right-pane-sections**')`
   - Between navigation steps, use `page.waitForLoadState('networkidle')` or similar

4. **Handle admin page form submission patterns:**
   - Admin pages use standard HTML forms with POST, not htmx
   - Install form: `<form method="POST" action="/admin/apps/install">` with `<input name="app_path">`
   - Stop/Start: `<form method="POST" action="/admin/apps/{id}/stop">` and `/start`
   - Uninstall: `<form method="POST" action="/admin/apps/{id}/uninstall">`
   - After form submission, the server responds with `RedirectResponse(status_code=303)` → browser follows redirect

5. **Clean up considerations:**
   - If the test app is already installed from a previous run, the test should handle this gracefully
   - At the start of the test, check if test-app exists and uninstall it first
   - At the end, always uninstall (even if earlier steps failed) — but since this is a single test() function, normal test flow handles this

## Must-Haves

- [ ] `e2e/tests/30-app-platform/app-platform.spec.ts` exists with a single sequential `test()`
- [ ] Test installs test-app via admin form and waits for "running" status
- [ ] Test verifies admin detail page shows app metadata (name, PID, permissions, tasks)
- [ ] Test verifies "Test App" appears in workspace APPS sidebar section
- [ ] Test verifies app page fragment loads in workspace (`#test-app-main` visible)
- [ ] Test verifies command palette API returns test-command entry
- [ ] Test exercises stop/restart lifecycle via admin
- [ ] Test uninstalls app and verifies removal from admin list
- [ ] All assertions use explicit selectors or text content, not screenshot comparison
- [ ] `e2e/helpers/selectors.ts` updated with app platform selectors

## Verification

- `npx playwright test --project=chromium e2e/tests/30-app-platform/app-platform.spec.ts` — passes
- The spec file imports from `../../fixtures/auth` and uses `ownerPage` fixture
- `grep -c "expect" e2e/tests/30-app-platform/app-platform.spec.ts` — ≥10 assertions

## Inputs

- `apps/test-app/` — Created in T01, this is the app that gets installed and tested
- `backend/app/apps/manager.py` — Modified in T02, `uninstall()` now accepts `clean_data` parameter
- `backend/app/apps/admin_router.py` — Modified in T02, uninstall endpoint accepts `clean_data` form param
- `e2e/fixtures/auth.ts` — Provides `ownerPage` (authenticated Page), `ownerRequest` (authenticated APIRequestContext), `BASE_URL`
- `e2e/helpers/selectors.ts` — Existing selector constants to extend

### Key page structures (from S03/S04/S06 summaries):
- **Admin apps list** (`/admin/apps`): H1 "Applications", app cards with status badges, install form
- **Admin apps detail** (`/admin/apps/{id}`): Stats bar, permissions table, task management section, log viewer, action buttons (Start/Stop/Restart/Uninstall)
- **Workspace sidebar**: APPS `<details>` section with `hx-trigger="load, appsRefreshed from:body"` loading from `/browser/apps/explorer`
- **App page in workspace**: Rendered via dockview `special-panel` with `app-page` type, content loaded from `/app/test-app/_fragments/main`
- **Right pane**: Dynamic `#right-pane-dynamic` container loaded from `/browser/apps/right-pane-sections?iri=<IRI>`
- **Command palette API**: `GET /api/apps/commands` returns JSON array with `{id, label, keywords, actionType, fragment, appId}` entries

### Auth fixture pattern (from existing specs):
```typescript
import { test, expect, BASE_URL } from '../../fixtures/auth';
test.describe('App Platform', () => {
  test('full lifecycle', async ({ ownerPage }) => {
    // ownerPage is authenticated as the instance owner
    // Use generous timeouts for Docker-based operations
  });
});
```

### Admin form patterns (from S03 templates):
- Install: POST `/admin/apps/install` with `app_path` form field
- Stop: POST `/admin/apps/{id}/stop`
- Start: POST `/admin/apps/{id}/start`
- Restart: POST `/admin/apps/{id}/restart`
- Uninstall: POST `/admin/apps/{id}/uninstall` with optional `clean_data` form field

## Observability Impact

- **Playwright traces:** On first retry, full interaction trace is captured via `trace: 'on-first-retry'` in playwright.config.ts — inspect with `npx playwright show-trace`
- **Screenshots on failure:** `screenshot: 'only-on-failure'` saves viewport captures to `e2e/test-results/`
- **Video on failure:** `video: 'retain-on-failure'` captures full test video for flaky debugging
- **Inspection:** `npx playwright test --project=chromium e2e/tests/30-app-platform/ --reporter=list` shows per-phase progress
- **Failure visibility:** Each phase has explicit `expect()` assertions — failures pinpoint exactly which integration point broke (install, workspace, admin, uninstall)
- **Docker logs:** App lifecycle events logged at INFO in `app.apps.manager` logger — correlate with `docker compose -f docker-compose.test.yml logs api`

## Expected Output

- `e2e/tests/30-app-platform/app-platform.spec.ts` — Comprehensive E2E spec proving full app platform vertical
- `e2e/helpers/selectors.ts` — Updated with `apps` selector section
