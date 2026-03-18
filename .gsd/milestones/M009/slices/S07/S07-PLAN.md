# S07: Test App, E2E Tests & Integration Proof

**Goal:** A comprehensive test app at `apps/test-app/` exercises all SDK features, Playwright E2E tests prove the full install → use → admin → uninstall flow, and all milestone success criteria are verified against the live Docker stack.
**Demo:** `npx playwright test --project=chromium e2e/tests/30-app-platform/` passes — proving app install via admin, standalone page in workspace, right pane section, command palette entry, admin task/status visibility, and clean uninstall with data cleanup.

## Must-Haves

- `apps/test-app/` with manifest.yaml exercising all UI contribution types (pages, rightPane, views, commands, objectRenderers, tasks)
- `apps/test-app/app.py` with SDK handlers for all fragment endpoints and task handler
- Test app frontend templates (main page, right pane, command dialog, read renderer, test view)
- `docker-compose.test.yml` updated with `./apps` and `./backend/sdk` volume mounts + `sempkm_test_data` on frontend
- `AppManager.uninstall()` gains `clean_data=True` parameter triggering triplestore SPARQL cleanup
- Admin uninstall endpoint passes `clean_data` form parameter
- Playwright E2E spec covering: install → status → app page → right pane → command palette → admin task config → uninstall
- All existing tests pass (zero regressions)

## Proof Level

- This slice proves: final-assembly (all 6 prior slices exercised end-to-end)
- Real runtime required: yes (Docker stack with real subprocess, UDS, nginx proxy)
- Human/UAT required: no (Playwright automation covers all verification points)

## Verification

- `pytest backend/tests/test_app_manifest.py -v -k "test_app"` — test app manifest parses against AppManifestSchema
- `docker compose -f docker-compose.test.yml config --services` — shows api, frontend, triplestore (config valid)
- `npx playwright test --project=chromium e2e/tests/30-app-platform/app-platform.spec.ts` — full E2E flow passes
- `pytest backend/tests/ -x --ignore=backend/tests/test_sdk_integration.py` — zero regressions in existing suite
- `grep -rn "^<<<<<<< " apps/ backend/app/apps/ e2e/tests/30-app-platform/` — zero conflict markers
- `cd backend && python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('../apps/test-app/manifest.yaml')"` — manifest validates without errors (failure-path: invalid YAML or schema violations raise ValueError with detail)
- `docker compose -f docker-compose.test.yml logs api 2>&1 | grep -i error` — no startup errors in api service (diagnostic surface for runtime failures)

## Observability / Diagnostics

- Runtime signals: App install/start/stop/uninstall logged at INFO via `app.apps.manager` logger; E2E test failures produce screenshots + traces via Playwright config
- Inspection surfaces: `/admin/apps` shows test app status; `/admin/apps/test-app` shows PID, uptime, task config, logs; `app_task_runs` table records scheduler executions
- Failure visibility: Playwright `--trace on-first-retry` captures full interaction trace; Docker logs via `docker compose -f docker-compose.test.yml logs api`
- Redaction constraints: none (test environment uses fixed secret key)

## Integration Closure

- Upstream surfaces consumed: All S01–S06 deliverables — AppManager lifecycle, SDK package, admin portal, frontend fragment loading, scheduler, permissions, workspace contributions, renderer overrides
- New wiring introduced in this slice: `clean_data` parameter on uninstall flow, `apps/test-app/` volume-mounted into Docker test stack
- What remains before the milestone is truly usable end-to-end: S08 (documentation only)

## Tasks

- [x] **T01: Create test app and update Docker test infrastructure** `est:45m`
  - Why: The test app is the fixture that all E2E tests exercise. Docker test stack needs volume mounts to see the app and SDK.
  - Files: `apps/test-app/manifest.yaml`, `apps/test-app/app.py`, `apps/test-app/requirements.txt`, `apps/test-app/frontend/templates/*.html` (5 templates), `apps/test-app/frontend/static/styles.css`, `apps/test-app/frontend/static/app.js`, `docker-compose.test.yml`
  - Do: Create `apps/test-app/` with a comprehensive manifest exercising all SDK UI contribution types (pages, rightPane, views, commands, objectRenderers, tasks). Write `app.py` with SDK route handlers for each fragment endpoint, a task handler, and lifecycle hooks. Create minimal but functional HTML templates for each fragment. Add `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` volume mounts to docker-compose.test.yml api service. Add `sempkm_test_data:/app/data:ro` to frontend service for app-static serving.
  - Verify: `cd backend && python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('$(pwd)/../apps/test-app')"` succeeds; `docker compose -f docker-compose.test.yml config --quiet` exits 0
  - Done when: Test app manifest validates, all 6 fragment templates exist, docker-compose.test.yml has required volume mounts

- [x] **T02: Implement uninstall data cleanup in AppManager** `est:20m`
  - Why: The success criterion "Uninstall app + data removes all app-prefixed IRIs from urn:sempkm:current" requires triplestore cleanup that `AppManager.uninstall()` doesn't yet perform. E2E tests need this to verify clean uninstall.
  - Files: `backend/app/apps/manager.py`, `backend/app/apps/admin_router.py`
  - Do: Add `clean_data: bool = False` parameter to `AppManager.uninstall()`. When True, execute three SPARQL queries via `self._triplestore_client` before deleting the DB row: (1) DELETE WHERE subjects with app IRI prefix, (2) DELETE WHERE objects with app IRI prefix, (3) CLEAR GRAPH for app state graph. Add `clean_data: bool = Form(False)` to the admin uninstall endpoint and pass it through to `manager.uninstall()`.
  - Verify: `python -c "import ast; ast.parse(open('backend/app/apps/manager.py').read())"` succeeds; `grep -c "clean_data" backend/app/apps/manager.py` returns ≥2; `grep -c "clean_data" backend/app/apps/admin_router.py` returns ≥2
  - Done when: `uninstall(app_id, clean_data=True)` executes SPARQL cleanup before DB deletion; admin endpoint accepts and passes through the `clean_data` form parameter

- [x] **T03: Write Playwright E2E specs for app platform** `est:1h`
  - Why: E2E tests are the milestone's proof that the full vertical works — install through admin, use in workspace, monitor in admin, uninstall with cleanup. Without this, all prior slice verification is contract-level only.
  - Files: `e2e/tests/30-app-platform/app-platform.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Create a single Playwright spec file with one long `test()` function (sequential, avoids rate limits). Steps: navigate to `/admin/apps` → install test app → wait for "running" status → check admin detail page → navigate to workspace → verify APPS sidebar → click app page → verify fragment content → open an object → verify right pane section → check command palette API endpoint → verify admin task config section → stop app → verify status → restart → verify recovery → uninstall with clean_data → verify removed from list → verify APPS sidebar empty. Add app-related selectors to `e2e/helpers/selectors.ts`.
  - Verify: `npx playwright test --project=chromium e2e/tests/30-app-platform/app-platform.spec.ts` passes
  - Done when: E2E spec exercises install → workspace page → right pane → admin monitoring → uninstall flow and all assertions pass

## Files Likely Touched

- `apps/test-app/manifest.yaml`
- `apps/test-app/app.py`
- `apps/test-app/requirements.txt`
- `apps/test-app/frontend/templates/main.html`
- `apps/test-app/frontend/templates/right-pane.html`
- `apps/test-app/frontend/templates/command-dialog.html`
- `apps/test-app/frontend/templates/read-renderer.html`
- `apps/test-app/frontend/templates/test-view.html`
- `apps/test-app/frontend/static/styles.css`
- `apps/test-app/frontend/static/app.js`
- `docker-compose.test.yml`
- `backend/app/apps/manager.py`
- `backend/app/apps/admin_router.py`
- `e2e/tests/30-app-platform/app-platform.spec.ts`
- `e2e/helpers/selectors.ts`
