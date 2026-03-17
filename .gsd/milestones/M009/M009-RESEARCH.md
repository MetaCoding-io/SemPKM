# M009: App Platform — Research

**Date:** 2026-03-16
**Researcher:** GSD auto-mode

## Summary

M009 is the largest single milestone in SemPKM's history — it introduces an entirely new subsystem spanning subprocess management, an in-repo SDK package, HTTP-over-UDS IPC, JWT-scoped permissions, a platform scheduler, 3-level frontend integration, bulk EventStore, 5 new SQLite tables, nginx/Docker config changes, and an admin monitoring portal. The 2035-line design document is thorough and internally consistent; all major architecture decisions are captured in DECISIONS.md (D138–D146).

The codebase is well-prepared. Existing patterns directly transfer: `ModelService.install()/remove()` gives a lifecycle management blueprint, `EventStore.commit()` is the base for `commit_bulk()`, `ManifestSchema` (Pydantic) is the reference for `AppManifestSchema`, admin router and browser sub-module patterns (D014) are proven, and the right-pane `<details class="right-section">` pattern is directly extensible. The workspace sidebar has OBJECTS/VIEWS/DASHBOARDS/WORKFLOWS sections — adding an APPS section is mechanical.

The critical path is subprocess lifecycle + IPC proxy + SDK. Everything else (scheduler, permissions, frontend integration, admin portal) depends on being able to start an app process and communicate with it. This should be proven first. The second risk cluster is the SDK — it's a new in-repo package with its own `pyproject.toml`, installed into per-app venvs, and it must provide a stable developer-facing API.

## Recommendation

**10–12 slices, bottom-up, proving subprocess lifecycle first.**

Slice ordering should follow dependency order:
1. **Manifest + DB schema** (low risk, unblocks everything) — Pydantic schema, Alembic migration, no runtime behavior
2. **Subprocess lifecycle** (highest risk, critical path) — venv creation, process start/stop, health check, crash recovery
3. **SDK package** (high risk, new territory) — in-repo package structure, App class, runner, unix socket HTTP server
4. **IPC proxy + JWT** (medium risk) — platform-side proxy routing, token generation/validation
5. **Permission enforcement** (medium risk) — SDK clients enforce command whitelist, IRI prefix, network domain restrictions
6. **Scheduler** (medium risk) — task triggering, concurrency guard, retry, task history
7. **Bulk EventStore** (low risk) — extension to existing well-understood code
8. **Frontend Level 1** (medium risk) — standalone pages, [Apps] sidebar, app_shell template
9. **Frontend Level 2+3** (medium risk) — right pane, views, command palette, renderer overrides
10. **Admin portal** (low risk) — list/detail views, actions, task history
11. **Test app + E2E** (validation) — proves all layers work together
12. **Docs** (standing requirement)

Slices 1-4 are the "prove it works" phase — if subprocess + IPC + SDK works, the rest is application of established patterns.

## Implementation Landscape

### Key Files — Existing (to modify)

| File | Lines | What Changes |
|------|-------|-------------|
| `backend/app/main.py` | 570 | Add `AppManager` init in `lifespan()`, include app router |
| `backend/app/events/store.py` | 365 | Add `commit_bulk()` method with summary metadata |
| `backend/app/models/manifest.py` | 139 | Add `browserVisible` field to type icon defs |
| `backend/app/commands/dispatcher.py` | 61 | Export `HANDLER_REGISTRY` keys for permission validation |
| `backend/app/admin/router.py` | 1211 | Extract app admin to sub-module (follows D014) |
| `backend/app/browser/router.py` | 35 | Include app-related browser sub-routers |
| `backend/app/templates/browser/workspace.html` | 218 | Add [APPS] sidebar section |
| `frontend/nginx.conf` | ~120 | Add `/app-static/` and `/app/{appId}/` locations |
| `docker-compose.yml` | ~65 | Add `./apps:/app/apps:ro` volume mount |
| `backend/Dockerfile` | ~30 | Verify `uv`/`venv` available at runtime (currently uses uv — should be fine) |
| `backend/pyproject.toml` | ~40 deps | Add `PyJWT`, `packaging` |

### Key Files — New (to create)

| File/Directory | Purpose |
|---------------|---------|
| `backend/app/apps/` | New domain module: manager, registry, proxy, scheduler, models |
| `backend/app/apps/manager.py` | `AppManager` — lifecycle orchestrator (install, start, stop, restart, uninstall) |
| `backend/app/apps/registry.py` | `AppRegistry` — in-memory manifest cache, renderer/contribution lookup |
| `backend/app/apps/proxy.py` | `AppProxy` — HTTP-over-UDS forwarding via httpx |
| `backend/app/apps/scheduler.py` | `AppScheduler` — timer-based task invocation with concurrency guard |
| `backend/app/apps/manifest.py` | `AppManifestSchema` Pydantic model (from design §14) |
| `backend/app/apps/tokens.py` | JWT generation/validation for per-app scoped tokens |
| `backend/app/apps/router.py` | Platform routes: `/app/{appId}/*` proxy, admin API endpoints |
| `backend/app/apps/admin_router.py` | Admin HTML routes: list, detail, install, actions |
| `backend/app/apps/models.py` | SQLAlchemy models for `app_instances`, `app_task_runs`, etc. |
| `backend/sdk/` | `sempkm-app-sdk` package: `App`, `AppContext`, clients, runner |
| `backend/sdk/pyproject.toml` | SDK package metadata and dependencies |
| `backend/sdk/sempkm_app_sdk/app.py` | `App` class with decorators |
| `backend/sdk/sempkm_app_sdk/context.py` | `AppContext` with scoped clients |
| `backend/sdk/sempkm_app_sdk/runner.py` | CLI runner: starts uvicorn on UDS |
| `backend/sdk/sempkm_app_sdk/clients/` | `CommandClient`, `GraphClient`, `StateClient`, `HttpClient`, `SettingsClient` |
| `apps/test-app/` | Minimal test app exercising all SDK features |
| `backend/app/templates/admin/apps/` | Admin list + detail templates |
| `backend/app/templates/browser/app_shell.html` | Standalone app page wrapper |
| `backend/migrations/versions/013_app_tables.py` | Alembic migration for 5 app tables |

### Build Order (6 phases)

**Phase 1: Foundation (no runtime behavior)**
- `AppManifestSchema` Pydantic model with full validation
- `browserVisible` field on ManifestSchema
- SQLAlchemy models + Alembic migration for 5 app tables
- `packaging` and `PyJWT` added to pyproject.toml
- Unit tests for manifest validation

**Phase 2: Subprocess Lifecycle (critical path)**
- `AppManager` with install/start/stop/restart/uninstall
- Per-app venv creation via `uv venv` + `uv pip install`
- Process supervision: `asyncio.create_subprocess_exec`
- Health check polling (`GET /_health`)
- Crash recovery with exponential backoff
- Auto-start on platform boot (in `lifespan()`)
- SIGTERM/SIGKILL shutdown sequence
- Unit tests for lifecycle state machine

**Phase 3: SDK + IPC**
- `sempkm-app-sdk` package structure with `pyproject.toml`
- `App` class with lifecycle/task/route decorators
- `runner.py` — starts uvicorn on unix socket
- `AppProxy` in platform — routes `/app/{appId}/*` to UDS via httpx
- JWT token generation (platform side) and validation (SDK side)
- Token rotation mechanism
- Integration test: start test app, proxy a request, get response

**Phase 4: Permissions + Scheduler + Bulk EventStore**
- SDK clients: `CommandClient` (command whitelist, IRI prefix enforcement)
- `GraphClient` (SPARQL read scoping)
- `HttpClient` (network domain enforcement via glob matching)
- `StateClient` (graph scoping to `urn:sempkm:app:{appId}:state`)
- `AppScheduler` with interval parsing, concurrency guard, retry
- `EventStore.commit_bulk()` with summary metadata
- SDK `ctx.commands.bulk()` context manager
- Unit tests for each enforcement layer

**Phase 5: Frontend + Admin**
- Level 1: `app_shell.html`, [Apps] sidebar section, fragment loading
- Level 2: right pane contributions, view contributions, command palette
- Level 3: object renderer overrides
- Admin list page (`/admin/apps`), detail page
- Install flow with permission approval
- Start/stop/restart/uninstall actions
- Task interval adjustment, task history view
- Log display (ring buffer, last 50 lines)
- nginx config additions
- docker-compose.yml volume mount

**Phase 6: Test App + E2E + Docs**
- `apps/test-app/` — minimal app exercising all SDK features
- E2E tests proving the full vertical: install → page → command → task → admin
- User guide chapter covering app platform

### Verification Approach

**Unit tests (per slice):**
- Manifest validation: all field constraints, cross-field validators, error messages
- Lifecycle state machine: install/start/stop/restart transitions, crash recovery logic
- SDK clients: permission enforcement, IRI prefix validation, domain glob matching
- Scheduler: interval parsing, concurrency guard, retry backoff calculation
- Bulk EventStore: summary metadata generation, batch size limit enforcement
- JWT: token generation, validation, expiry, claim structure

**Integration tests (Phase 3+):**
- Start a real subprocess on a UDS, proxy a request, verify response
- SDK clients make real HTTP calls to a mock platform API
- Scheduler triggers a real task handler and records result

**E2E tests (Phase 6):**
- Install test app via admin UI → verify status in admin
- Open app page → verify fragment loads
- Verify app sidebar entry appears
- Trigger task → verify execution in admin task history
- Restart app after stop → verify recovery
- Uninstall → verify cleanup

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| JWT token signing/validation | `PyJWT` (~=2.10) | Standard JWT library, supports HS256, claim validation, expiry |
| Semver range matching | `packaging.specifiers.SpecifierSet` | Already available (transitive dep), PEP 440 compatible |
| Unix socket HTTP client | `httpx.AsyncHTTPTransport(uds=...)` | Already pinned at ~=0.28.1, native UDS support |
| Unix socket HTTP server | `uvicorn` with `--uds` flag | SDK apps use uvicorn (already in platform deps) |
| Per-app venv creation | `uv venv` + `uv pip install` | `uv` binary already in Docker image (Dockerfile `COPY --from=ghcr.io/astral-sh/uv:0.9`) — 10-50x faster than stdlib `venv` + `pip` |
| YAML parsing | `pyyaml` (already pinned) | Used by ManifestSchema already |
| Process management | `asyncio.create_subprocess_exec` | stdlib, no external dep needed |
| Glob pattern matching | `fnmatch.fnmatch` | stdlib, matches the `*.hypothes.is` pattern from design |
| Interval parsing | Custom regex (from design §14) | Simple enough — shorthand + ISO 8601, already specified in Pydantic validator |

## Constraints

- **Dockerfile uses `uv` exclusively** — no `pip` or `venv` module installed. App venv creation must use `uv venv` and `uv pip install`, not `python -m venv` + `pip install`. This is an improvement over the design doc's assumption of stdlib venv.
- **Admin router is 1211 lines** — app admin routes should be a separate sub-module (`backend/app/apps/admin_router.py`), not added to the existing file. Follow D014 sub-router pattern.
- **Browser router has catch-all `{iri:path}` patterns** — app routes must be registered BEFORE `objects_router` (same as ontology, comments, sparql-result — per D052, D058, D136).
- **Right pane sections are hard-coded in workspace.html** — app contributions need dynamic injection. Best approach: htmx lazy-load the right pane section list from a new endpoint that merges platform + app contributions.
- **`httpx~=0.28.1` is already pinned** — UDS transport available via `httpx.AsyncHTTPTransport(uds=path)`.
- **No existing subprocess patterns in codebase** — `asyncio.create_subprocess_exec` will be new. Needs careful signal handling, especially in Docker (PID 1 concerns — but uvicorn is PID 1, not the platform code).
- **Tests run without Docker** (`backend/tests/` are pure unit tests, <5s) — app platform unit tests must follow this pattern. Integration tests needing subprocess + UDS need separate handling.
- **Platform version is `0.1.0`** (per `config.py`) — manifest `dependencies.platform` default of `>=0.1.0` will always pass.

## Common Pitfalls

- **UDS socket file cleanup on crash** — If app subprocess crashes, the socket file at `/tmp/sempkm-app-{appId}.sock` may linger. `AppManager` must delete the socket file before starting a new process. Check with `os.path.exists()` and `os.unlink()`.
- **venv creation in Docker volume** — `/app/data/apps/{appId}/venv/` lives on the `sempkm_data` Docker volume. If the volume persists across container rebuilds, stale venvs may have wrong Python version. The manifest hash check handles this — if hash changes, recreate venv.
- **`asyncio.create_subprocess_exec` and PID tracking** — The `Process.pid` from asyncio is the direct child PID. If the child spawns uvicorn which spawns workers, the PID may not be the one to signal. Using `--workers 1` and signaling the process group avoids this.
- **htmx fragment loading through proxy** — App fragments proxied via `/app/{appId}/_fragments/...` need the platform's CSRF cookie and session cookie forwarded. The proxy must pass cookies through. httpx UDS transport handles this if we forward headers.
- **Template rendering in SDK** — The SDK's `ctx.render_template()` uses Jinja2. The app's template directory must be configured relative to the app root, not the platform root. SDK runner sets this up from `--app-dir`.
- **JWT rotation race** — If a token expires during a bulk operation, the SDK must catch 401, request a new token, and retry. The renewal endpoint is `POST /api/apps/{appId}/token/renew` (platform-side). SDK should pre-emptively renew when token is within 5 minutes of expiry.
- **Signal handling in subprocess** — SIGTERM should trigger uvicorn graceful shutdown. The SDK runner should install a signal handler that calls the app's `on_shutdown` hook before exiting.
- **`uv` not on PATH inside app venv** — `uv` is at `/bin/uv` in the Docker image (from `COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/`). App processes need to use the full path or the platform can call `/bin/uv` directly from `AppManager`.

## Open Risks

- **Subprocess startup latency** — `uv venv` + `uv pip install` at install time could take 10-30s depending on dependency count. The admin UI needs a progress indicator (SSE or polling). This is UX risk, not technical risk.
- **Memory overhead** — Each app subprocess adds ~20-50MB baseline (Python interpreter + framework). With 5 apps running, that's 100-250MB extra. Acceptable for personal tool but needs monitoring surface in admin.
- **SDK API stability** — The SDK is the developer-facing contract. Once apps are written against it, breaking changes are costly. V1 should be minimal and conservative — add surface area later.
- **Concurrent install races** — Two apps installing simultaneously could compete for `uv` or filesystem resources. An install lock (`asyncio.Lock`) in `AppManager` is the simplest fix.
- **`uv pip install` inside Docker runtime** — `uv` may need network access to download packages. The Docker container must have outbound network access at app install time (not just build time). Docker default networking should handle this, but worth verifying.
- **Right pane dynamic injection** — The current right pane sections (Relations, Lint, Comments) are hard-coded in `workspace.html`. Making them dynamic requires either: (a) server-side injection at workspace render time (fast but ties workspace to app state), or (b) htmx lazy-load of the section list (more flexible, slightly more complex). Option (b) is recommended per the design's "fragments everywhere" philosophy.

## Requirements Analysis

### Table Stakes (must ship for platform to be useful)

- **APP-01** (manifest validation) — foundational, everything depends on it
- **APP-02** (subprocess lifecycle) — without this, nothing runs
- **APP-03** (SDK) — without this, apps can't be written
- **APP-04** (IPC) — without this, platform can't talk to apps
- **APP-13** (DB tables) — without this, no persistent state tracking
- **APP-14** (Docker/nginx) — without this, apps can't serve content

### Expected (users will assume these work)

- **APP-05** (permissions) — security boundary, users expect isolation
- **APP-06** (scheduler) — background tasks are a core app capability
- **APP-07** (standalone pages) — primary UI entry point for apps
- **APP-10** (admin portal) — visibility into what's running

### Valuable but Deferrable

- **APP-08** (Level 2 workspace contributions) — right pane sections, views, command palette are "nice to have" for v1. Could ship with just Level 1 pages and add Level 2 in a fast-follow.
- **APP-09** (Level 3 renderer overrides) — most complex frontend integration. Depends on having an app that actually needs custom renderers (RSS Reader in M010). Could defer to M010.
- **APP-11** (bulk EventStore) — needed for RSS feed polling performance, but the RSS app is M010. Could ship basic commit and add bulk later.
- **APP-12** (browserVisible) — minor enhancement, trivially implementable, but only matters once an app creates internal types.

### Candidate Requirements (not in current list)

1. **APP-PROG: Install progress feedback** — venv creation + pip install takes 10-30s. Without progress, user stares at a spinner with no indication of what's happening. Recommend: SSE stream from install endpoint showing step-by-step progress (creating venv → installing deps → starting process → health check).

2. **APP-LOG: App log capture and display** — Design shows "last 50 lines" in admin. This needs explicit implementation: ring buffer in `AppManager` capturing subprocess stdout/stderr, exposed via admin detail API. Not just "forward to platform logger" — admin needs queryable access.

3. **APP-AUTO: Auto-start previously running apps on platform boot** — Listed in CONTEXT.md acceptance criteria and design §10. Should be tracked as explicit requirement since it's a lifecycle behavior, not just a feature.

## Sources

- `.gsd/design/APP-PLATFORM-DESIGN.md` — 2035-line canonical design document (sections 1-17)
- `backend/Dockerfile` — confirms `uv` binary available at `/bin/uv` via multi-stage copy
- `backend/pyproject.toml` — current dependency list (httpx~=0.28.1 already pinned, PyJWT and packaging missing)
- `backend/app/main.py` — lifespan pattern for service initialization
- `backend/app/services/models.py` — lifecycle management pattern (install/remove/list)
- `backend/app/events/store.py` — commit pattern, extension point for bulk
- `backend/app/models/manifest.py` — ManifestSchema pattern for AppManifestSchema
- `backend/app/commands/dispatcher.py` — HANDLER_REGISTRY for permission validation
- `backend/app/browser/router.py` — sub-router coordinator pattern (D014)
- `backend/app/templates/browser/workspace.html` — sidebar sections and right pane structure
- `frontend/nginx.conf` — existing proxy patterns for new app routes
- `docker-compose.yml` — volume mount pattern for apps directory
- `backend/app/admin/router.py` — 1211 lines, needs sub-module extraction for app admin
- `backend/app/auth/tokens.py` — existing token pattern (itsdangerous, not JWT — new dep needed)
- `backend/migrations/versions/` — latest migration is 012, next will be 013
