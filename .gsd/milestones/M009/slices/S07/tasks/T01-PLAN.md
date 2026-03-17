---
estimated_steps: 7
estimated_files: 12
---

# T01: Create test app and update Docker test infrastructure

**Slice:** S07 — Test App, E2E Tests & Integration Proof
**Milestone:** M009

## Description

Create `apps/test-app/` — a comprehensive test application that exercises all SDK features built across S01–S06. This is the fixture that all E2E tests will install, run, and interact with. Also update `docker-compose.test.yml` so the test Docker stack can see the app directory and SDK package.

The test app needs handlers for every SDK integration point: standalone page, right pane section, view tab, command palette dialog, object renderer override, scheduled task, and lifecycle hooks. Each handler returns minimal but distinct HTML so E2E tests can assert the right content loaded.

**Relevant skills:** `test` (for understanding test patterns)

## Steps

1. **Create `apps/test-app/manifest.yaml`** — Full manifest with all UI contribution types:
   - Identity: `appId: "test-app"`, name, version 1.0.0, description, author
   - Dependencies: `platform: ">=0.1.0"`
   - Permissions: `commands: ["object.create"]`, `sparql: { read: true }`, `backgroundTasks: true`, `network: []`
   - Backend: `entrypoint: "app:test_app"`
   - Tasks: one `heartbeat` task with `interval: "5m"` and `retryPolicy: { maxRetries: 1, backoff: "1s", maxBackoff: "10s" }`
   - Frontend: `staticDir: "frontend/static"`, `css: ["styles.css"]`, `js: ["app.js"]`
   - UI pages: one page `id: "main"`, `path: "/main"`, `label: "Test App"`, `icon: "flask-conical"`, `nav: "apps"`, `fragment: "main"`
   - UI contributions.rightPane: `id: "test-info"`, `label: "Test Info"`, `icon: "info"`, `fragment: "right-pane"`, `targetTypes: ["*"]`, `priority: 50`
   - UI contributions.views: `id: "test-view"`, `label: "Test View"`, `icon: "test-tubes"`, `fragment: "test-view"`
   - UI contributions.commandPalette: `id: "test-command"`, `label: "Test App Command"`, `keywords: ["test", "demo"]`, `actionType: "dialog"`, `fragment: "command-dialog"`
   - UI objectRenderers: `type: "urn:sempkm:test:TestRenderedType"`, `modes: { read: "read-renderer" }`

2. **Create `apps/test-app/app.py`** — SDK app with all handlers:
   ```python
   from sempkm_app_sdk import App, AppContext
   from starlette.requests import Request
   from starlette.responses import HTMLResponse
   import logging

   logger = logging.getLogger(__name__)
   test_app = App("test-app")

   @test_app.route("/_fragments/main")
   async def main_fragment(request: Request):
       ctx = request.app.state.ctx
       return HTMLResponse(ctx.render_template("main.html"))

   @test_app.route("/_fragments/right-pane")
   async def right_pane_fragment(request: Request):
       iri = request.query_params.get("iri", "unknown")
       ctx = request.app.state.ctx
       return HTMLResponse(ctx.render_template("right-pane.html", iri=iri))

   @test_app.route("/_fragments/test-view")
   async def test_view_fragment(request: Request):
       ctx = request.app.state.ctx
       return HTMLResponse(ctx.render_template("test-view.html"))

   @test_app.route("/_fragments/command-dialog")
   async def command_dialog_fragment(request: Request):
       ctx = request.app.state.ctx
       return HTMLResponse(ctx.render_template("command-dialog.html"))

   @test_app.route("/_fragments/read-renderer")
   async def read_renderer_fragment(request: Request):
       iri = request.query_params.get("iri", "unknown")
       ctx = request.app.state.ctx
       return HTMLResponse(ctx.render_template("read-renderer.html", iri=iri))

   @test_app.task("heartbeat")
   def heartbeat_task(ctx: AppContext, body: dict):
       logger.info("Heartbeat task executed for %s", ctx.app_id)
       return {"status": "alive"}

   @test_app.on_startup
   def on_startup(ctx: AppContext):
       logger.info("Test app started: %s", ctx.app_id)

   @test_app.on_shutdown
   def on_shutdown(ctx: AppContext):
       logger.info("Test app stopped: %s", ctx.app_id)
   ```

3. **Create `apps/test-app/requirements.txt`** — Empty file (SDK injected by platform).

4. **Create 5 frontend templates** in `apps/test-app/frontend/templates/`:
   - `main.html` — `<div id="test-app-main"><h2>Test Application</h2><p>This is the test app main page.</p></div>`
   - `right-pane.html` — `<div id="test-app-right-pane"><h4>Test Info</h4><p>Object: {{ iri }}</p></div>`
   - `command-dialog.html` — `<div id="test-app-command-dialog"><h3>Test Command</h3><p>This is a test command dialog.</p></div>`
   - `read-renderer.html` — `<div id="test-app-renderer"><h3>Custom Renderer</h3><p>Rendering: {{ iri }}</p></div>`
   - `test-view.html` — `<div id="test-app-view"><h2>Test View</h2><p>This is the test app view.</p></div>`

5. **Create frontend static assets** in `apps/test-app/frontend/static/`:
   - `styles.css` — Minimal CSS: `#test-app-main { padding: 1rem; }` (and similar for each container)
   - `app.js` — Minimal JS: `console.log('Test app loaded');`

6. **Update `docker-compose.test.yml`** — Add volume mounts to the `api` service:
   - `./apps:/app/apps:ro` (app source directories)
   - `./backend/sdk:/app/backend/sdk:ro` (SDK package for `uv pip install`)
   Add to the `frontend` service:
   - `sempkm_test_data:/app/data:ro` (for nginx to serve `/app-static/` from shared volume)

7. **Validate** — Run `parse_app_manifest()` against the new test app manifest to confirm it validates. Check docker-compose.test.yml syntax.

## Must-Haves

- [ ] `apps/test-app/manifest.yaml` validates against `AppManifestSchema` (all required fields present, all UI contribution types included)
- [ ] `apps/test-app/app.py` has handlers for all 5 fragment endpoints + 1 task + 2 lifecycle hooks
- [ ] All 5 frontend template files exist with unique `id` attributes for E2E assertion targeting
- [ ] `docker-compose.test.yml` has `./apps:/app/apps:ro` and `./backend/sdk:/app/backend/sdk:ro` on api service
- [ ] `docker-compose.test.yml` has `sempkm_test_data:/app/data:ro` on frontend service
- [ ] `apps/test-app/requirements.txt` exists (empty is fine)
- [ ] Static assets `styles.css` and `app.js` exist

## Verification

- `cd backend && python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/test-app'); print(f'OK: {m.name} v{m.version}, {len(m.ui.pages)} pages, {len(m.tasks)} tasks')"` — prints OK with correct counts
- `docker compose -f docker-compose.test.yml config --quiet` — exits 0 (valid compose syntax)
- `ls apps/test-app/frontend/templates/ | wc -l` — returns 5
- `grep -c "test-app" apps/test-app/manifest.yaml` — ≥1
- `python -c "import ast; ast.parse(open('apps/test-app/app.py').read())"` — syntax OK

## Inputs

- `backend/app/apps/manifest.py` — `AppManifestSchema` with all nested models defines what the manifest must contain
- `backend/sdk/sempkm_app_sdk/app.py` — `App` class with `route()`, `task()`, `on_startup`, `on_shutdown` decorators define the SDK API
- `backend/sdk/sempkm_app_sdk/context.py` — `AppContext.render_template()` loads templates from `{app_dir}/frontend/templates/`
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — Reference for a minimal valid manifest (but our test app needs ALL features, not just pages)
- `docker-compose.test.yml` — Current test stack config to extend with volume mounts

### Key Schema Constraints (from S01 research)
- `appId` must match `^[a-z][a-z0-9-]*[a-z0-9]$`
- `version` must be strict semver (e.g. "1.0.0")
- Task `interval` has 30s floor / 24h ceiling
- `retryPolicy.backoff` and `maxBackoff` also interval-validated
- Command palette `actionType: "dialog"` requires `fragment` field
- `objectRenderers[].type` must be a full IRI
- `objectRenderers[].modes` must have at least one of `read` or `edit`
- `permissions.backgroundTasks: true` required when `tasks` is non-empty
- `author` is an object with `name` field (not a bare string)
- `dependencies` requires `platform` field with semver range

## Expected Output

- `apps/test-app/manifest.yaml` — Comprehensive manifest exercising all SDK features
- `apps/test-app/app.py` — SDK app with 5 route handlers, 1 task handler, 2 lifecycle hooks
- `apps/test-app/requirements.txt` — Empty file
- `apps/test-app/frontend/templates/main.html` — Main page fragment with `id="test-app-main"`
- `apps/test-app/frontend/templates/right-pane.html` — Right pane fragment with `id="test-app-right-pane"`
- `apps/test-app/frontend/templates/command-dialog.html` — Command dialog fragment with `id="test-app-command-dialog"`
- `apps/test-app/frontend/templates/read-renderer.html` — Renderer fragment with `id="test-app-renderer"`
- `apps/test-app/frontend/templates/test-view.html` — View fragment with `id="test-app-view"`
- `apps/test-app/frontend/static/styles.css` — Minimal CSS
- `apps/test-app/frontend/static/app.js` — Minimal JS
- `docker-compose.test.yml` — Updated with 3 new volume mounts (2 on api, 1 on frontend)
