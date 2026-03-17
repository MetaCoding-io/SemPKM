# S07: Test App, E2E Tests & Integration Proof — Research

**Date:** 2026-03-17
**Milestone:** M009 — App Platform

## Summary

S07 is a **low-risk integration proof slice** — all platform code (S01–S06) is already built and contract-tested with ~7300 lines of unit tests across 17 test files. The work is: (1) create `apps/test-app/` exercising all SDK features, (2) write Playwright E2E specs proving the full install → use → admin → uninstall vertical, and (3) update `docker-compose.test.yml` so the E2E environment supports apps.

The biggest practical concern is the **working tree split**: S01–S04 code lives on the `milestone/M009` branch (worktree at `.gsd/worktrees/M009`), and S05–S06 code was committed there too. The `main` branch has `.gsd/` summaries but only partial S05 code (T03 browserVisible). All S07 work must target the `milestone/M009` worktree at `.gsd/worktrees/M009/`.

The test app is straightforward — it's a small Python module using the SDK's decorator-based API (`@app.route`, `@app.task`, lifecycle hooks) plus a manifest.yaml declaring all contribution types. The E2E tests follow established patterns from 30+ existing spec files (auth fixtures, API client, dockview helpers, htmx wait utilities).

## Recommendation

**Three tasks, ordered by dependency:**

1. **Test app (`apps/test-app/`)** — manifest + backend + templates. Must exist before E2E tests can run.
2. **Docker test infrastructure** — `docker-compose.test.yml` needs `./apps` and `./backend/sdk` volume mounts. Without this, the test stack can't run apps.
3. **E2E Playwright specs** — a single consolidated spec file covering the full vertical flow.

Build the test app first since it's self-contained and verifiable via unit tests. Then update Docker config. Then write E2E tests.

## Implementation Landscape

### Key Files

**Working directory: `.gsd/worktrees/M009/` (the milestone worktree — NOT the main checkout)**

Existing platform code (read-only references for S07):
- `.gsd/worktrees/M009/backend/app/apps/manager.py` (614 lines) — `AppManager.install()` takes a `Path` to app dir, validates manifest, creates venv, installs deps + SDK, starts subprocess
- `.gsd/worktrees/M009/backend/app/apps/manifest.py` (294 lines) — `AppManifestSchema` with all nested models (pages, tasks, contributions, renderers, settings)
- `.gsd/worktrees/M009/backend/app/apps/admin_router.py` (480 lines) — admin CRUD: install, start, stop, restart, uninstall, task interval, task pause, renderer set/clear
- `.gsd/worktrees/M009/backend/app/browser/apps.py` (290 lines) — workspace integration: explorer, page, right-pane-sections, views/explorer, view tab, commands JSON
- `.gsd/worktrees/M009/backend/app/apps/registry.py` (137 lines) — `get_right_pane_contributions()`, `get_renderer()`, `get_renderer_for_app()`
- `.gsd/worktrees/M009/backend/sdk/sempkm_app_sdk/app.py` — `App` class with `@app.route()`, `@app.task()`, lifecycle decorators
- `.gsd/worktrees/M009/backend/sdk/sempkm_app_sdk/context.py` — `AppContext` with `.commands`, `.graph`, `.state`, `.http`, `.settings` clients
- `.gsd/worktrees/M009/backend/sdk/sempkm_app_sdk/runner.py` — CLI runner: reads manifest, imports entrypoint, builds ASGI app, starts uvicorn on UDS

Existing test infrastructure (patterns to follow):
- `e2e/fixtures/auth.ts` — `ownerPage`, `ownerRequest`, `memberPage` fixtures with magic-link auth
- `e2e/helpers/api-client.ts` — `ApiClient` class with `createObject()`, `sparql()`, `executeCommand()`
- `e2e/helpers/wait-for.ts` — `waitForIdle()`, `waitForWorkspace()`, `waitForHtmxSettle()`
- `e2e/helpers/dockview.ts` — `openObjectTab()`, `openViewTab()`, `getTabCount()`
- `e2e/helpers/selectors.ts` — `SEL` object with CSS selectors for all UI components
- `e2e/playwright.config.ts` — runs against port 3901, `docker-compose.test.yml` stack

Reference test: `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — install → verify → uninstall pattern for mental models. Closest existing analog to app lifecycle E2E.

Existing test fixture: `backend/tests/fixtures/test_sdk_app/` — minimal SDK app used in unit tests (1 route, 1 task, 1 lifecycle handler). S07 test app is the full-featured version.

**Files to create:**
```
apps/test-app/
  manifest.yaml                    # Full manifest exercising all features
  requirements.txt                 # Empty or minimal (SDK installed by platform)
  backend/
    app.py                         # SDK app with all handler types
  frontend/
    templates/
      main.html                    # Standalone page fragment
      info.html                    # Right pane section fragment
      command_dialog.html          # Command palette dialog fragment
      article_read.html            # Renderer override read fragment
    static/
      test-app.css                 # Minimal CSS (proves static serving)

docker-compose.test.yml            # Updated: add ./apps and ./backend/sdk mounts

e2e/tests/30-app-platform/
  app-lifecycle.spec.ts            # E2E: install → page → command → task → admin → uninstall
```

### Build Order

**T01 — Test app (`apps/test-app/`)**

Create the test app exercising all SDK features declared in the manifest schema:

1. `manifest.yaml` with:
   - `appId: "test-app"`, `version: "1.0.0"`, `name: "Test App"`
   - `permissions.commands: ["object.create"]` (for creating objects)
   - `permissions.backgroundTasks: true` (for scheduled task)
   - `permissions.sparql.read: true` (for graph queries)
   - `tasks:` — one task `"test-task"` with `interval: "5m"`, `configurable: true`
   - `ui.pages:` — one page `"main"` with `fragment: "main"`, `icon: "layout-dashboard"`, `nav: "apps"`
   - `ui.contributions.rightPane:` — one entry `"test-info"` with `fragment: "_fragments/info"`, `targetTypes: ["*"]`
   - `ui.contributions.commandPalette:` — one entry `"test-command"` with `actionType: "dialog"`, `fragment: "_fragments/command-dialog"`
   - `ui.objectRenderers:` — one renderer for a test type with `modes.read: "_fragments/article-read"`
   - `backend.entrypoint: "backend.app:test_app"`
   - `dependencies.platform: ">=0.1.0"`

2. `backend/app.py` with:
   - `test_app = App("test-app")`
   - `@test_app.route("/_fragments/main")` returning standalone page HTML
   - `@test_app.route("/_fragments/info")` returning right pane section HTML
   - `@test_app.route("/_fragments/command-dialog")` returning dialog HTML
   - `@test_app.route("/_fragments/article-read")` returning renderer HTML
   - `@test_app.task("test-task")` handler returning `{"result": "ok"}`
   - `@test_app.on_startup` handler logging startup
   - `@test_app.on_shutdown` handler logging shutdown

3. `frontend/templates/` with minimal Jinja2 templates for each fragment
4. `frontend/static/test-app.css` with minimal CSS
5. `requirements.txt` — empty (SDK installed by platform, no extra deps)

Verify: `python -c "from apps.test_app_manifest_check import check; check()"` — parse manifest with `AppManifestSchema`, confirm all fields valid. Or simpler: a unit test that calls `parse_app_manifest("apps/test-app/manifest.yaml")`.

**T02 — Docker test infrastructure**

Update `docker-compose.test.yml`:
- Add `./apps:/app/apps:ro` volume to `api` service (matches dev docker-compose.yml)
- Add `./backend/sdk:/app/backend/sdk:ro` volume to `api` service (SDK source for venv install)
- Add `sempkm_test_apps_data:/app/data/apps` volume for app venvs/data (writable)
- Ensure nginx `frontend` service gets the same nginx.conf (already has `/app-static/` and `/app/` blocks from S03)

The dev nginx.conf already has:
```
location /app-static/ { alias /app/data/apps-static/; ... }
location /app/ { proxy_pass http://api:8000/app/; ... }
```

But the test frontend container doesn't mount the data volume. The `app-static` location uses `alias /app/data/apps-static/` which requires the frontend container to access the API data volume. Two options:
- Share the data volume between api and frontend containers (cleanest — matches dev setup)
- Skip static asset verification in E2E (acceptable — static serving is an nginx config concern, not app logic)

Recommend: add a shared volume or skip static assertion. The E2E tests focus on fragment rendering (proxied through api), not static file serving.

Also add `selectors.ts` entries for app platform elements if needed.

**T03 — E2E Playwright specs**

Single spec file `e2e/tests/30-app-platform/app-lifecycle.spec.ts` covering:

1. **Navigate to admin apps page** — `GET /admin/apps` shows empty or existing list
2. **Install test app** — POST form with `app_path=/app/apps/test-app` → app appears in list with "running" status
3. **Verify admin detail** — click app → detail page shows version, status, PID, permissions, task list
4. **Navigate to workspace** — `GET /workspace` → [Apps] sidebar section shows "Main Page" entry
5. **Load app page** — click app page link → dockview tab opens with fragment content ("Hello from test-app" or similar)
6. **Check right pane** — open any object → right pane shows test-app section
7. **Check command palette** — open Ctrl+K → test command entry visible
8. **Verify task in admin** — navigate to admin detail → task history section shows runs (may need to wait or trigger manually)
9. **Stop app** — click Stop → status changes to "stopped"
10. **Restart app** — click Start → status changes to "running"
11. **Uninstall app** — click Uninstall → app removed from list

Pattern: use `ownerPage` fixture for admin actions, consolidated into 1-2 `test()` blocks to stay within magic-link rate limit (same pattern as `admin-model-lifecycle.spec.ts`).

Key considerations:
- App install takes time (venv creation, dep install) — use generous timeout (30-60s)
- Task scheduler checks every 60s — may not fire during test window. Verify task config exists rather than waiting for a run, OR trigger task manually via API
- Fragment content assertions should check for specific text rendered by the test app

### Verification Approach

**Unit verification (no Docker):**
- `parse_app_manifest("apps/test-app/manifest.yaml")` succeeds — confirms manifest valid
- Test app Python module imports without error: `python -c "from backend.app import test_app"`

**Integration verification (Docker stack):**
- `docker compose -f docker-compose.test.yml up -d --build` starts cleanly
- `curl http://localhost:3901/admin/apps` returns 200 (admin page)
- Install test app via API → app status becomes "running"
- `curl http://localhost:3901/app/test-app/_health` returns `{"status": "ok"}`
- `curl http://localhost:3901/app/test-app/_fragments/main` returns fragment HTML

**E2E verification (Playwright):**
- `cd e2e && npx playwright test tests/30-app-platform/ --project=chromium`
- All assertions pass for install → page → command → admin → uninstall flow

## Constraints

- **Worktree location**: All code changes MUST be made in `.gsd/worktrees/M009/`, not the main checkout. The milestone branch has the complete S01–S06 code.
- **App install path**: Inside Docker, the app directory is at `/app/apps/test-app` (due to `./apps:/app/apps:ro` mount). The admin install form takes this container path, not a host path.
- **SDK installed at install time**: `AppManager.install()` runs `uv pip install /app/backend/sdk` into the app's venv. The SDK source must be mounted at `/app/backend/sdk` in the container.
- **Test app requirements.txt**: Must exist (even if empty) since `AppManager.install()` checks for it via `manifest.backend.requirements`.
- **App subprocess needs writable `/tmp/`**: Socket files created at `/tmp/sempkm-app-{appId}.sock`. Docker containers have writable `/tmp/` by default.
- **App data directory**: `AppManager` creates `/app/data/apps/{appId}/venv/` — the data volume must be writable.
- **Rate limiting**: E2E tests share magic-link rate limit (5/min). Consolidate into minimal `test()` blocks.

## Common Pitfalls

- **Install timeout in E2E**: `AppManager.install()` creates venv + installs SDK. First run in a fresh container downloads packages. The E2E test must use a generous timeout (30–60s) for the install POST and subsequent status check. Use `page.waitForResponse` or poll status.
- **Task scheduler timing**: Scheduler checks every 60s. A test-task with `interval: "5m"` won't fire during a typical E2E run. Either: (a) set interval to `"30s"` (minimum allowed) and wait, (b) trigger task manually via `POST /app/test-app/_tasks/test-task` with app token, or (c) just verify task config exists in admin detail without waiting for execution. Recommend (c) — task execution is already proven by 31 scheduler unit tests.
- **Fragment content depends on running app**: Right pane sections, views explorer, and command palette all filter by `status == "running"`. If the app crashes during E2E, all workspace integrations silently disappear. Check app status before workspace assertions.
- **Admin install form uses hx-post**: The install form submits via htmx and redirects. Use `page.waitForURL` or `waitForIdle()` after submission.
- **Test app entrypoint format**: Manifest `backend.entrypoint` must be `"module:attribute"` format (e.g., `"backend.app:test_app"`). The runner imports `backend.app` module and reads `test_app` attribute. The app dir is added to `sys.path[0]`, so `backend.app` resolves to `{app_dir}/backend/app.py`.
- **docker-compose.test.yml volume for app data**: The `apps` mount is `:ro` but the app data dir (`/app/data/apps/`) needs to be writable for venv creation. Data goes in the existing `sempkm_test_data` volume which is already writable.

## Open Risks

- **First-run SDK install latency in CI**: `uv pip install /app/backend/sdk` into a fresh venv may take 10-20s depending on SDK dependencies (httpx, jinja2, uvicorn are transitive). If the E2E timeout is too tight, the install step will fail.
- **nginx app-static alias**: The test nginx container may not have access to `/app/data/apps-static/` since it only mounts `./frontend/static`. Static asset serving may 404 in the test environment. This is acceptable — fragment rendering (the critical path) goes through the API proxy, not nginx static.
