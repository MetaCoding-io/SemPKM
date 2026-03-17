# S07: Test App, E2E Tests & Integration Proof — Research

**Date:** 2026-03-17
**Researcher:** GSD auto-mode

## Summary

S07 is the integration proof slice — it builds a comprehensive test app at `apps/test-app/` that exercises all SDK features (page, command, task, right pane, command palette, renderer override), writes Playwright E2E tests proving the full install → page → command → task → admin → uninstall flow, and verifies all milestone success criteria against the live Docker stack.

This is straightforward application work. All infrastructure exists: 372 unit tests across S01–S06 prove the individual subsystems. The E2E test framework is mature (Playwright, auth fixtures, helpers, 50+ existing spec files). The test app is a small Python module + manifest.yaml + templates. The Docker test stack needs minor updates (add `apps` and `sdk` volume mounts to `docker-compose.test.yml`).

The main gap discovered during research: **the uninstall "app + data" flow doesn't yet clean up app-prefixed IRIs from the triplestore** — `AppManager.uninstall()` has a `_triplestore_client` reference but never uses it. The design doc specifies SPARQL DELETE WHERE + CLEAR GRAPH queries (§4 "Cleanup on uninstall"). This needs implementation before the E2E test can verify the success criterion "Uninstall 'app + data' removes all app-prefixed IRIs from `urn:sempkm:current`."

## Recommendation

**4 tasks: (1) test app, (2) docker-compose.test.yml updates, (3) uninstall data cleanup implementation, (4) Playwright E2E specs.**

Build order:
1. **Test app** first — it's the fixture everything depends on. Must have manifest.yaml with all UI contribution types, app.py with SDK handlers, and frontend templates/static assets.
2. **docker-compose.test.yml** — add `./apps` and `./backend/sdk` volume mounts to the test stack's api service, add `sempkm_test_data` read-only mount to frontend service for app-static serving.
3. **Uninstall data cleanup** — implement triplestore cleanup in `AppManager.uninstall()` with an optional `clean_data=True` parameter. Add admin endpoint parameter.
4. **E2E specs** — Playwright test file covering: install test app via admin → verify status → open app page in workspace → verify app sidebar entry → verify right pane section → verify command palette entry → check admin task history → uninstall → verify cleanup.

## Implementation Landscape

### Key Files — To Create

| File | Purpose |
|------|---------|
| `apps/test-app/manifest.yaml` | Full manifest exercising all SDK features (pages, tasks, rightPane, views, commands, objectRenderers) |
| `apps/test-app/app.py` | SDK app with route handlers for fragments, task handler, lifecycle hooks |
| `apps/test-app/requirements.txt` | Empty or minimal — SDK injected by platform |
| `apps/test-app/frontend/templates/main.html` | Main page fragment template |
| `apps/test-app/frontend/templates/right-pane.html` | Right pane section fragment |
| `apps/test-app/frontend/templates/command-dialog.html` | Command palette dialog fragment |
| `apps/test-app/frontend/templates/read-renderer.html` | Object renderer read view fragment |
| `apps/test-app/frontend/static/styles.css` | Minimal CSS for test app |
| `apps/test-app/frontend/static/app.js` | Minimal JS for test app |
| `e2e/tests/30-app-platform/app-platform.spec.ts` | E2E spec proving full install→use→uninstall flow |

### Key Files — To Modify

| File | What Changes |
|------|-------------|
| `docker-compose.test.yml` | Add `./apps:/app/apps:ro`, `./backend/sdk:/app/backend/sdk:ro`, `sempkm_test_data:/app/data:ro` on frontend |
| `backend/app/apps/manager.py` | Add `clean_data` param to `uninstall()` with triplestore SPARQL cleanup |
| `backend/app/apps/admin_router.py` | Add `clean_data` form param to uninstall endpoint |
| `e2e/helpers/selectors.ts` | Add `admin.appList`, `admin.appDetail`, `admin.appInstallForm` selectors |

### Test App Manifest Structure

The test app manifest needs to exercise every UI contribution point built across S01-S06:

```yaml
appId: "test-app"
name: "Test Application"
version: "1.0.0"
description: "Exercises all SDK features for E2E validation"
author:
  name: "SemPKM"
dependencies:
  platform: ">=0.1.0"
permissions:
  commands: ["object.create"]
  network: []
  sparql:
    read: true
  backgroundTasks: true
backend:
  entrypoint: "app:test_app"
tasks:
  - id: "heartbeat"
    description: "Periodic heartbeat for testing"
    interval: "5m"
frontend:
  staticDir: "frontend/static"
  css: ["styles.css"]
  js: ["app.js"]
ui:
  pages:
    - id: "main"
      path: "/main"
      label: "Test App"
      icon: "flask-conical"
      nav: "apps"
      fragment: "main"
  contributions:
    rightPane:
      - id: "test-info"
        label: "Test Info"
        icon: "info"
        fragment: "right-pane"
        targetTypes: ["*"]
        priority: 50
    views:
      - id: "test-view"
        label: "Test View"
        icon: "test-tubes"
        fragment: "test-view"
    commandPalette:
      - id: "test-command"
        label: "Test App Command"
        keywords: ["test", "demo"]
        actionType: "dialog"
        fragment: "command-dialog"
  objectRenderers:
    - type: "urn:sempkm:test:TestRenderedType"
      modes:
        read: "read-renderer"
```

### Test App SDK Code

The `app.py` needs handlers for:
- `@app.route("/_fragments/main")` — standalone page content
- `@app.route("/_fragments/right-pane")` — right pane section content (receives `?iri=` param)
- `@app.route("/_fragments/test-view")` — view tab content
- `@app.route("/_fragments/command-dialog")` — command palette dialog content
- `@app.route("/_fragments/read-renderer")` — object renderer read view (receives `?iri=` param)
- `@app.task("heartbeat")` — task handler returning success
- `@app.on_startup` — log startup
- `@app.on_shutdown` — log shutdown

### Docker Test Stack Updates

`docker-compose.test.yml` api service needs:
```yaml
volumes:
  - ./apps:/app/apps:ro         # App source directories
  - ./backend/sdk:/app/backend/sdk:ro  # SDK package
```

Frontend service needs `sempkm_test_data` read-only mount for app-static serving (matching main docker-compose):
```yaml
volumes:
  - sempkm_test_data:/app/data:ro
```

### Uninstall Data Cleanup

`AppManager.uninstall()` currently does: stop → delete socket → remove data dir → delete DB row → unregister. It stores a `_triplestore_client` but never uses it.

The design doc (§4) specifies:
```sparql
DELETE WHERE {
  GRAPH <urn:sempkm:current> {
    ?s ?p ?o FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{appId}:"))
  }
};
DELETE WHERE {
  GRAPH <urn:sempkm:current> {
    ?s ?p ?o FILTER(STRSTARTS(STR(?o), "urn:sempkm:app:{appId}:"))
  }
};
CLEAR GRAPH <urn:sempkm:app:{appId}:state>
```

Add `clean_data: bool = False` parameter to `uninstall()`. When True, execute the three SPARQL queries before deleting the DB row. Admin endpoint passes form param through.

### E2E Test Structure

Single spec file following the admin-model-lifecycle pattern (one long `test()` to avoid rate limits). Steps:

1. Navigate to `/admin/apps`, verify empty state or clean up prior test app
2. Install test app via form POST (path: `/app/apps/test-app`)
3. Wait for status badge to show "running"
4. Verify admin detail page shows PID, version, permissions
5. Navigate to workspace, verify APPS sidebar section contains "Test App"
6. Click app page, verify fragment content loads
7. Open an object, verify "Test Info" right pane section appears
8. Check command palette API returns test-command entry
9. Check admin task history after waiting for scheduler tick (may need to invoke manually)
10. Stop app via admin, verify status changes to "stopped"
11. Restart app, verify status returns to "running"
12. Uninstall with clean_data, verify app removed from list
13. Verify workspace APPS sidebar is empty

### Build Order

1. **Test app first** — blocks everything. Simple code, no risk.
2. **docker-compose.test.yml** — trivial edits, required for Docker stack to see the test app.
3. **Uninstall cleanup** — small backend change, needed for E2E cleanup verification.
4. **E2E specs** — depends on all above. Most time-consuming (Playwright interaction patterns).

### Verification Approach

**Test app works in unit tests:**
- `parse_app_manifest("apps/test-app/manifest.yaml")` succeeds
- Test app fixture `app.py` imports and has expected handlers

**Docker stack proof:**
- `npm run env:start` in `e2e/` starts the test stack with apps mounted
- `curl http://localhost:3901/admin/apps` (after auth) shows empty page
- Install test app via admin form, verify JSON status response

**E2E Playwright:**
- `npx playwright test --project=chromium e2e/tests/30-app-platform/` — full flow passes
- All success criteria verified against live behavior

## Constraints

- **E2E tests run against port 3901** (docker-compose.test.yml), not the dev stack. Auth uses `readSetupToken()` from Docker container.
- **Tests must be sequential** — app install/uninstall is stateful. Single `test()` function avoids parallel execution issues and rate limit problems.
- **Scheduler tick interval is 60s** — E2E can't wait that long. Either invoke the task directly via API (`POST /app/test-app/_tasks/heartbeat`) with appropriate auth, or check that the scheduler recorded a task config row rather than waiting for execution. Alternatively, reduce CHECK_INTERVAL for tests or directly call the admin task history endpoint.
- **Test app needs network access during install** for `uv pip install` of SDK deps. Docker test stack has outbound network by default.
- **The existing test fixture at `backend/tests/fixtures/test_sdk_app/`** is for unit/integration tests only. The E2E test app at `apps/test-app/` is a separate, more comprehensive app.

## Common Pitfalls

- **App install takes 10-30s** — E2E test must use generous timeouts when waiting for "running" badge after install. `page.waitForSelector('.badge-success', { timeout: 60000 })` or polling.
- **htmx partial rendering in admin** — Admin pages use `HX-Request` to decide whether to return full page or content block only. E2E tests use full page navigation (`page.goto()`), which returns the full page. If testing htmx interactions (sidebar clicks), need to wait for `htmx-settling` to complete.
- **Workspace fragment loading** — App page content loads via htmx `hx-get` from `/app/test-app/_fragments/main`. This goes through nginx → API → AppProxy → UDS → SDK app. If the app isn't running when the fragment loads, the proxy returns 503 and the content area shows an error. Wait for app status="running" before navigating to workspace.
- **Right pane loads dynamically** — The right pane uses `loadRightPane(objectIri)` which fetches `/browser/apps/right-pane-sections?iri=...`. Must open an object first and wait for the right pane content to load before asserting app section presence.

## Open Risks

- **Scheduler task verification in E2E** — The scheduler ticks every 60s. The test app task interval is "5m". Within the E2E test's ~60s window, the scheduler may not fire the task. Options: (a) verify task config exists in admin detail rather than actual execution, (b) reduce test app interval to "1m" and wait, (c) call the task endpoint directly via API to prove it works. Option (c) is most reliable.
- **uv pip install network dependency** — If the test Docker stack can't reach PyPI during app install, the install will fail on SDK dependency installation. The SDK's deps (fastapi, httpx, uvicorn, pyyaml) should already be available in the container's pip cache, but not guaranteed in the test container's app venv.
