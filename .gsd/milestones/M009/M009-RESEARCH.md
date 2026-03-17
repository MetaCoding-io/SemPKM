# M009 — Research

**Date:** 2026-03-16
**Milestone:** App Platform

## Summary

M009 is the largest and most architecturally complex milestone in the project's history. It introduces a new subsystem — the App Platform — spanning subprocess lifecycle management, an in-repo SDK package, HTTP-over-unix-socket IPC, JWT-scoped permissions, a platform-owned task scheduler, 3-level frontend integration, a bulk EventStore extension, 5 new SQLite tables, nginx/Docker changes, and a comprehensive admin portal. The 2035-line design document (`.gsd/design/APP-PLATFORM-DESIGN.md`) is thorough and internally consistent, with a complete Pydantic schema, concrete examples, and decision rationale for every major choice.

The codebase is well-prepared for this work. Existing patterns for model lifecycle management (`ModelService.install()/remove()`), domain-module structure (canvas/, lint/, vfs/, dashboard/, workflow/), Alembic migrations (12 existing), admin portal templates, and browser sub-router coordination provide clear templates. The design document's Pydantic schema can be dropped into the codebase almost verbatim. The main technical risks are: (1) ensuring `pip` and `python -m venv` work inside the Docker container (the current Dockerfile uses `uv` and may strip pip), (2) unix socket lifecycle in Docker's `/tmp/`, and (3) JWT token generation requiring a new dependency (`PyJWT` or similar) since the codebase currently uses `itsdangerous` only for signed tokens.

The recommended approach is to build bottom-up: manifest validation first (pure functions, easy to test), then database tables, then subprocess lifecycle, then SDK, then IPC/proxy, then scheduler, then frontend integration (3 levels in order), then admin portal, then the test app, and finally E2E tests and docs. The manifest validation and database slices are risk-free and unblock everything. Subprocess lifecycle + SDK is the critical path — it must be proven before frontend integration can work. The test app should be built incrementally, exercising each capability as it ships.

## Recommendation

**Slice the work into 10-12 slices**, ordered to prove the riskiest pieces first while keeping each slice independently verifiable:

1. **Manifest + Schema** — Pure Pydantic validation, `parse_app_manifest()`, unit tests. Zero runtime dependencies. Unblocks everything.
2. **Database tables + Alembic migration** — 5 new SQLite tables. Pure schema work.
3. **Subprocess lifecycle (AppManager core)** — venv creation, process start/stop/restart, health check, crash recovery. Docker verification required. This is the critical risk slice.
4. **App SDK package** — `backend/sdk/` in-repo package with App class, AppContext stubs, SDK runner (HTTP server on unix socket). Can test standalone outside Docker.
5. **IPC + Proxy + JWT** — `AppProxy` routing `/app/{appId}/*` to unix socket. JWT token generation and validation. Adds `PyJWT` dependency.
6. **Permission enforcement + State/Graph/Command clients** — SDK clients with scoping. Bulk EventStore extension (`commit_bulk()`).
7. **Scheduler** — `AppScheduler` with interval parsing, concurrency guard, retry policy, task invocation protocol.
8. **Frontend Level 1 + Admin portal** — `app_shell.html`, `[Apps]` sidebar section for app pages, admin list/detail views, nginx config.
9. **Frontend Level 2 + Level 3** — Right pane sections, view contributions, command palette entries, object renderer overrides, `browserVisible` field.
10. **Test app + integration** — `apps/test-app/` exercising all capabilities. Docker stack verification.
11. **E2E tests** — Playwright specs for app install, page load, task execution, admin portal, uninstall.
12. **User guide docs** — Chapter covering all app platform features.

## Implementation Landscape

### Key Files

- `backend/app/main.py` — `lifespan()` function needs `AppManager` initialization and app auto-start. ~340 lines. Add after validation queue start, before yield.
- `backend/app/commands/dispatcher.py` — `HANDLER_REGISTRY` keys are the whitelist for app command permissions. 5 registered types: `object.create`, `object.patch`, `body.set`, `edge.create`, `edge.patch`.
- `backend/app/events/store.py` — `EventStore` class needs `commit_bulk()` method alongside existing `commit()`. ~280 lines. Extend with summary-only metadata path.
- `backend/app/models/manifest.py` — `ManifestSchema` needs `browserVisible` field added per type. Reference for manifest validation patterns (Pydantic, camelCase, YAML parsing).
- `backend/app/services/models.py` — `ModelService.install()/remove()` is the lifecycle management reference. Follow the same transactional pattern for app install/uninstall.
- `backend/app/services/settings.py` — `SettingsService` with layered resolution. App settings will integrate here (app settings displayed alongside model/core settings).
- `backend/app/browser/router.py` — Sub-router coordinator. New `apps_router` will be included here (before `objects_router` per D052/D058 pattern).
- `backend/app/templates/browser/workspace.html` — Right pane sections (relations, lint, comments) at lines 178-207. App right-pane sections inject here dynamically.
- `backend/app/templates/components/_sidebar.html` — `[Apps]` sidebar group at line 83. Currently has Object Browser, File Browser, Import Vault, etc. App pages will be added dynamically.
- `frontend/nginx.conf` — Needs `/app-static/` location for app assets and `/app/{appId}/` proxy. Add before the catch-all `location /` block.
- `docker-compose.yml` — API service needs `./apps:/app/apps:ro` volume mount. Currently has 6 volume mounts.
- `backend/Dockerfile` — Uses `uv sync --frozen --no-dev`. May strip pip/venv capability. **Critical risk**: need to verify `python -m venv` works inside the built image, or add `pip` installation step.
- `backend/app/admin/router.py` — 1211 lines with model CRUD, webhooks, ops log. App admin routes should be a separate sub-module (`backend/app/admin/apps_router.py`) to avoid growing this file further.
- `backend/app/auth/tokens.py` — Uses `itsdangerous` for signed tokens, not JWT. App-scoped JWT is a new concern — needs `PyJWT` dependency.
- `backend/app/dependencies.py` — FastAPI DI providers. Add `get_app_manager()` provider.
- `backend/pyproject.toml` — Current 24 dependencies. Needs `PyJWT~=2.7.0` and `packaging~=24.0.0` (for semver range checking in manifest validation).

### New Files to Create

```
backend/app/apps/                    # New domain module
  __init__.py
  manager.py                         # AppManager: install, start, stop, restart, uninstall
  registry.py                        # AppRegistry: manifest cache, running app state, renderer lookups
  scheduler.py                       # AppScheduler: task scheduling, concurrency, retry
  proxy.py                           # AppProxy: HTTP request proxying to unix sockets
  router.py                          # API routes for app admin CRUD, task triggers, commands API
  jwt.py                             # Per-app JWT token generation and validation
  models.py                          # SQLAlchemy ORM models (app_instances, app_task_runs, etc.)
  manifest.py                        # Already exists in design: AppManifestSchema + parse_app_manifest()

backend/sdk/                         # In-repo SDK package
  pyproject.toml                     # Package metadata
  sempkm_app_sdk/
    __init__.py                      # App class, AppContext
    app.py                           # App class with lifecycle decorators
    context.py                       # AppContext with scoped clients
    clients/
      commands.py                    # CommandClient (permission-scoped)
      graph.py                       # GraphClient (SPARQL query)
      state.py                       # StateClient (app state graph CRUD)
      http.py                        # HttpClient (network-permission-scoped)
      settings.py                    # SettingsClient
    runner.py                        # SDK runner: uvicorn on unix socket

backend/migrations/versions/013_app_tables.py  # Alembic migration for 5 app tables

backend/app/templates/admin/apps.html           # App list page
backend/app/templates/admin/app_detail.html     # App detail page
backend/app/templates/admin/app_install.html    # Permission approval dialog
backend/app/templates/browser/app_shell.html    # Level 1 standalone page shell
backend/app/templates/browser/app_view_tab.html # Level 2 view contribution tab

apps/test-app/                       # Test app for E2E validation
  manifest.yaml
  requirements.txt
  backend/
    app.py
  frontend/
    templates/
    static/
```

### Build Order

**Phase 1: Foundation (no runtime, pure validation)**
1. `AppManifestSchema` Pydantic model + `parse_app_manifest()` — copy from design doc §14, add unit tests. All field validators, nested models, cross-field validators. This is 100% pure function work.
2. `browserVisible` field on Mental Model `ManifestSchema` — single field addition.
3. Alembic migration 013 — 5 new SQLite tables (`app_instances`, `app_task_runs`, `app_task_config`, `app_renderer_prefs`, `app_permissions`). SQLAlchemy ORM models.

**Phase 2: Core runtime (critical path)**
4. Subprocess lifecycle — `AppManager` with venv creation, process start/stop, health check, crash recovery with exponential backoff. Docker verification: confirm `python -m venv` works in the API container.
5. SDK package — `App` class, `AppContext`, SDK runner (uvicorn on unix socket). Can test independently.
6. IPC proxy — `AppProxy` routes `/app/{appId}/*` to unix socket via `httpx.AsyncClient` with unix socket transport. JWT token generation (`PyJWT`).

**Phase 3: Enforcement + EventStore**
7. Permission enforcement in SDK clients (CommandClient, GraphClient, HttpClient, StateClient). Bulk EventStore `commit_bulk()`.

**Phase 4: Scheduler**
8. `AppScheduler` — interval parsing, concurrency guard, task invocation via HTTP, retry policy. Task history recording to SQLite.

**Phase 5: Frontend**
9. Level 1 frontend — `app_shell.html`, sidebar [Apps] section, nginx `/app-static/` and `/app/` locations.
10. Level 2 + Level 3 frontend — right pane contributions, view contributions, command palette, object renderer overrides.

**Phase 6: Admin + Test app + E2E + Docs**
11. Admin portal — app list/detail pages, install flow, start/stop/restart/uninstall actions.
12. Test app + integration testing in Docker stack.
13. E2E Playwright tests.
14. User guide documentation.

### Verification Approach

**Unit tests (no Docker):**
- Manifest validation: all field combinations, edge cases, cross-field validators, error messages
- Interval parsing: shorthand + ISO 8601, floor/ceiling enforcement
- Permission checking: command whitelist, IRI prefix enforcement, network domain glob matching
- Bulk EventStore: summary metadata generation, batch size limits
- Scheduler: interval calculation, concurrency guard logic, retry backoff computation

**Integration tests (Docker stack):**
- App install: manifest validated → venv created → deps installed → process started → health check passes
- IPC proxy: platform routes request to unix socket → app responds with fragment
- Task scheduling: scheduler triggers task → app receives HTTP POST → result recorded
- Uninstall: app stopped → data cleaned up → venv removed → DB records deleted
- Auto-start: platform restart → all previously running apps start automatically

**E2E tests (Playwright):**
- Admin > Applications page shows installed apps
- Install test app via admin UI
- Test app page loads in workspace
- Test app creates object (appears in object browser)
- Test app task fires and logs in admin
- Uninstall test app (data cleanup verified)

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| JWT token generation/validation | `PyJWT` (~2.7.0) | Industry standard, handles claims, expiry, signing. `itsdangerous` (current dep) is for URL-safe signed tokens, not JWT. |
| Semver range checking | `packaging.specifiers.SpecifierSet` | Already referenced in design doc §14. `packaging` is a pip dependency (already available in Python ecosystem). Need to add as explicit dependency. |
| YAML parsing | `pyyaml` (already in deps) | Already used for Mental Model manifests. |
| Unix socket HTTP transport | `httpx` (already in deps) with `httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=...))` | httpx natively supports unix domain socket transport. No additional library needed. |
| Process supervision | `asyncio.create_subprocess_exec` | stdlib. No need for supervisord or circus. Simple enough for 1-5 app processes. |
| Subprocess health check | `httpx` GET to unix socket `/_health` | Same library, same transport. |
| Template rendering in SDK | `jinja2` (already in deps) | SDK needs lightweight template rendering for app fragments. |

## Constraints

- **Dockerfile uses `uv` not `pip`**: The `backend/Dockerfile` runs `uv sync --frozen --no-dev`. The resulting image may not have `pip` or `venv` module. The platform needs `python -m venv` at runtime for per-app venvs and `pip install` for app dependencies. **Either**: (a) add `RUN apt-get install python3-venv && pip install pip` to Dockerfile, or (b) use `uv` for venv creation and dep installation in app venvs too (requires `uv` binary in the image, which it already is via `COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/`). **Recommendation**: use `uv` — it's already in the image, faster than pip, and handles venv creation (`uv venv`) and dep install (`uv pip install`).
- **No `PyJWT` or `packaging` in current dependencies**: Both need to be added to `pyproject.toml`. `packaging` is a transitive dep of `pip`/`setuptools` but should be explicit. `PyJWT` is new.
- **Admin router is 1211 lines**: Adding app admin routes inline would push it past 1500 lines. Follow the browser sub-router pattern (D014) — create `backend/app/admin/apps_router.py` and include it.
- **5 existing right-pane sections** (relations, lint, comments, inbox, collaboration): App contributions insert alongside these. The workspace.html template hard-codes these. Need a dynamic section injection mechanism.
- **ninja-keys command palette** initialized in `workspace.js` lines 1286+: App commands must be injected after initial setup. Design shows `fetch('/api/apps/commands')` — need an API endpoint returning registered app commands.
- **Object tab routing** goes through `objects_router` in `browser/objects.py`: Renderer overrides need to intercept before the default SHACL form renders. Check `AppRegistry.get_renderer(type, mode)` in the object tab handler.
- **SDK package installed into app venvs**: The platform must `uv pip install /app/sdk` (or equivalent) into each app venv at install time. The SDK source lives in-repo at `backend/sdk/`.

## Common Pitfalls

- **venv creation inside Docker**: `python -m venv` needs the `venv` module. Python slim images strip it. The current Dockerfile uses `python:3.12-slim` which *does* include `ensurepip` and `venv` module. However, `uv`'s virtual environment at `/app/.venv` is not a standard venv — verify `python -m venv` works from the uv-managed Python. **Mitigation**: Use `uv venv /app/data/apps/{appId}/venv` instead, since `uv` is already available in the image.
- **Unix socket cleanup on crash**: If an app crashes, its socket file at `/tmp/sempkm-app-{appId}.sock` remains. The platform must delete stale socket files before starting a new app instance. `os.path.exists(sock_path) → os.unlink(sock_path)` before `subprocess.exec`.
- **httpx unix socket transport**: `httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds="/tmp/sempkm-app-{appId}.sock"))` — the `uds` parameter is supported in httpx 0.28+. Current dep is `httpx~=0.28.1`. Confirmed compatible.
- **JWT secret rotation**: Design says tokens rotate hourly. The SDK runner must handle 401 → re-request token → retry. The platform needs a token refresh endpoint or re-generation mechanism. Keep it simple: platform generates new token and passes via `POST /app/{appId}/_lifecycle/token-refresh`.
- **Alembic migration numbering**: Current latest is `012_workflow_specs.py`. Next must be `013_app_tables.py`.
- **Template rendering in SDK**: The SDK runner serves Jinja2 templates from the app's `frontend/templates/` directory. This is a separate Jinja2 environment from the platform's — no template name collisions. The SDK should initialize its own `jinja2.Environment(loader=FileSystemLoader(app_dir / "frontend" / "templates"))`.
- **SIGTERM propagation in Docker**: `docker compose stop` sends SIGTERM to PID 1 (uvicorn). The platform's lifespan shutdown must SIGTERM all app subprocesses. Current shutdown already sets `shutdown_event` — add app process termination before `sql_engine.dispose()`.
- **Right pane dynamic sections**: Current right pane is hard-coded HTML. To inject app contributions, either: (a) render them server-side in the workspace template (requires passing app contributions to every workspace render), or (b) use an htmx lazy-load pattern — add a `<div hx-get="/browser/app-pane-sections?iri={iri}" hx-trigger="load">` placeholder that fetches app sections dynamically. Option (b) is cleaner and doesn't couple workspace rendering to app state.

## Open Risks

- **Subprocess startup latency**: venv creation + `uv pip install` could take 10-30 seconds for apps with many dependencies. The admin UI needs a progress indicator (SSE or polling) during install. If the install is synchronous and the browser times out, the user sees a blank response.
- **Memory overhead**: Each Python subprocess adds ~20-50MB baseline RAM. With the API container itself at ~200-300MB, 5 apps would push total to 400-550MB. Acceptable for personal tool but worth monitoring. The admin detail view should show per-app memory (read from `/proc/{pid}/status`).
- **SDK API stability**: The SDK is installed into app venvs from in-repo source. If the SDK API changes between platform versions, existing app venvs have the old SDK. **Mitigation**: Re-install SDK into all app venvs on platform upgrade. Track SDK version hash in `app_instances.manifest_hash`.
- **Concurrent installs**: Two simultaneous installs could race on venv creation. The design mentions using a lock. Use `asyncio.Lock()` in AppManager for the install flow.
- **App-contributed CSS class collisions**: App HTML fragments share the platform's CSS namespace. App-prefixed class names (e.g., `.rss-reader-article`) are the convention, but not enforced. Shadow DOM would solve this but is incompatible with htmx.

## Requirements Analysis

### Table Stakes (must have, no negotiation)
- **APP-01 (Manifest validation)**: Foundation for everything. The Pydantic schema in §14 is production-ready.
- **APP-02 (Subprocess lifecycle)**: Core runtime. Without this, nothing works.
- **APP-03 (SDK)**: Developer-facing API. Without this, apps can't be written.
- **APP-04 (IPC)**: Communication channel. Without this, platform can't talk to apps.
- **APP-13 (Database tables)**: State persistence. Without this, no app tracking.
- **APP-14 (Docker/nginx)**: Deployment infrastructure. Without this, apps can't serve content.

### Expected Behaviors (strongly expected, would disappoint if missing)
- **APP-05 (Permissions)**: Users expect sandboxing. Without permission enforcement, the "sandboxed" claim is hollow.
- **APP-06 (Scheduler)**: Background tasks are a primary value proposition for apps.
- **APP-07 (Level 1 frontend)**: App pages are the minimum visible outcome.
- **APP-10 (Admin portal)**: Admin needs to manage apps. Table stakes for operability.
- **APP-11 (Bulk EventStore)**: Feed polling would be unusably slow without bulk mode.

### Valuable but Deferrable (nice to have, could ship without)
- **APP-08 (Level 2 contributions)**: Right pane, views, command palette. Enhances integration but apps work without them.
- **APP-09 (Level 3 renderer overrides)**: Custom object renderers. Rich feature but not needed for basic app functionality.
- **APP-12 (browserVisible)**: UX polish. Types remain queryable without it; just clutters the browser.

### Candidate Requirements Not in Current List
- **APP-15 (Install progress feedback)**: SSE or polling-based progress during venv creation + dep install. Without this, 30-second installs look broken.
- **APP-16 (App logs in admin)**: Design §11 shows last 50 lines of logs. Need a ring buffer or subprocess stdout capture mechanism. Currently not a requirement but is in the design.
- **APP-17 (Platform restart auto-start)**: Listed in acceptance criteria but not a separate requirement. Should be explicit — it's the "operational complete" criterion.

These are advisory — the roadmap planner should decide whether to add them or fold them into existing requirements.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | Available in `<available_skills>` | None specific to FastAPI found; codebase patterns are sufficient |
| Python subprocess management | N/A | stdlib `asyncio.create_subprocess_exec` — no skill needed |
| PyJWT | N/A | Well-documented, simple API — no skill needed |
| htmx | N/A | Established codebase patterns — no skill needed |

No professional agent skills are directly relevant to this milestone. The technologies involved (FastAPI, subprocess management, JWT, htmx) are all well-established in the codebase or have simple, well-documented APIs.

## Sources

- Design document: `.gsd/design/APP-PLATFORM-DESIGN.md` (2035 lines, 17 sections)
- RSS reader research: `docs/research/rss-reader-hypothesis-integration.md` (validates the app model)
- httpx unix socket docs: httpx natively supports `uds` parameter in `AsyncHTTPTransport` (version 0.28+)
- PyJWT: Standard library for JWT in Python — `encode()`/`decode()` with HS256 signing
- `packaging.specifiers`: Python packaging library for semver range matching — `SpecifierSet(">=1.0.0").contains("1.2.3")`
