# M009: App Platform

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

SemPKM gains a sandboxed app platform that lets third-party and first-party Python applications extend the system with custom UI, background tasks, external API integrations, and object renderer overrides — all running in isolated subprocesses communicating with the platform via HTTP-over-unix-socket IPC.

The platform implements every layer described in `.gsd/design/APP-PLATFORM-DESIGN.md`: manifest validation (Pydantic schema), subprocess lifecycle (venv creation, process supervision, health checks), the App SDK (`sempkm-app-sdk` in-repo package), 3-level frontend integration (standalone pages, workspace contributions, object renderer overrides), platform-owned task scheduler, permission enforcement (command scoping, network domain restrictions, IRI prefix enforcement), admin monitoring portal, and bulk EventStore extension.

This milestone builds the infrastructure only. The first app (RSS Reader) ships in M010.

## Why This Milestone

SemPKM has powerful data primitives (EventStore, SHACL forms, ViewSpecs, SPARQL) but no way for external code to leverage them. Features like RSS feed polling, annotation sync, or LLM-powered automation would require direct modifications to the platform codebase. An app platform decouples feature development from platform releases, lets users install only the capabilities they want, and creates a path toward a marketplace.

The design document is complete (2035 lines, 17 sections) and has been through review. All major architecture decisions are settled: subprocess isolation, HTTP/UDS IPC, platform-owned scheduling, fragment-only UI, shared model data in `urn:sempkm:current`.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install an app from the `apps/` directory via the admin portal (with permission approval dialog)
- See installed apps in Admin > Applications with status, uptime, memory, PID
- Start, stop, restart, and uninstall apps from the admin portal
- See app-contributed pages in a new [Apps] sidebar section in the workspace
- See app-contributed views in the [Views] section
- See app-contributed right-pane sections alongside Relations and Lint
- Use app-contributed command palette entries via Ctrl+K
- See custom object renderers when opening types that an app overrides
- Adjust app task intervals and see task execution history in the admin detail view
- View app logs in the admin detail page
- Uninstall apps with three options: app only, app + data, app + data + models

### Entry point / environment

- Entry point: `http://localhost:3000/admin/apps` (admin), `http://localhost:3000/workspace` (workspace with app contributions)
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, SQLite (app registry, task history, permissions)

## Completion Class

- Contract complete means: manifest validation passes for all field combinations, subprocess starts/stops cleanly, SDK clients (commands, graph, state, http, settings) enforce permissions, scheduler triggers tasks on interval, admin CRUD works
- Integration complete means: a minimal test app installs, starts, serves a fragment page, creates an object via SDK, runs a scheduled task, appears in admin with correct status — all within the Docker stack
- Operational complete means: apps survive platform restart (auto-start), handle crashes (restart with backoff), and clean up on uninstall

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A test app installs via admin UI (manifest validated, venv created, deps installed, process started)
- Test app's standalone page loads in workspace via htmx fragment
- Test app creates an object via `ctx.commands.execute()` and it appears in the object browser
- Test app's scheduled task fires at the configured interval and logs success in admin
- Test app's right pane section appears when viewing an object
- Test app's command palette entry works (dialog type opens a fragment)
- Admin shows app status (running, PID, uptime, task history, logs)
- App restarts automatically after crash (up to 3 retries with exponential backoff)
- Uninstall "app + data" removes all app-prefixed IRIs from `urn:sempkm:current`
- Platform restart auto-starts all previously running apps

## Risks and Unknowns

- **Subprocess startup time** — venv creation + pip install at install time could take 30-60s. Need clear progress feedback in admin UI.
- **Unix socket permissions in Docker** — The `/tmp/` directory inside the container should be fine, but socket file cleanup on crash needs handling.
- **JWT token rotation** — The per-app scoped JWT with hourly rotation needs a clean renewal mechanism in the SDK runner. If the token expires mid-request, the app gets a 401 — SDK must auto-retry after renewal.
- **htmx fragment isolation** — App-returned HTML fragments share the platform's CSS namespace. CSS class collisions are possible. Convention (app-prefixed class names) is the first defense; full isolation would require Shadow DOM which is incompatible with htmx.
- **Memory overhead** — Each app subprocess adds ~20-50MB baseline. With 5 apps, that's 100-250MB extra. Acceptable for personal tool; needs monitoring surface.
- **pip install inside Docker** — The API container needs `pip` and `python -m venv` available at runtime. Current Dockerfile may strip these for image size. Need to verify.

## Existing Codebase / Prior Art

- `backend/app/commands/dispatcher.py` — `HANDLER_REGISTRY` and `dispatch()` — apps use these command types via SDK
- `backend/app/events/store.py` — `EventStore.commit()` — needs `commit_bulk()` extension
- `backend/app/services/models.py` — `ModelService.install()/remove()` — reference for lifecycle management pattern
- `backend/app/services/settings.py` — `SettingsService` — app settings integrate with this
- `backend/app/main.py` — `lifespan()` — app manager starts/stops here
- `backend/app/models/manifest.py` — `ManifestSchema` — reference for manifest validation pattern, `browserVisible` field added here
- `backend/app/templates/browser/workspace.html` — sidebar sections — needs [Apps] section
- `frontend/nginx.conf` — needs `/app-static/` and `/app/` proxy rules
- `docker-compose.yml` — API service volumes need `./apps` mount
- `.gsd/design/APP-PLATFORM-DESIGN.md` — the 2035-line design document (canonical reference)
- `docs/research/rss-reader-hypothesis-integration.md` — RSS reader research validating the app model

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements to be created: APP-01 through APP-14 covering all platform subsystems
- MCP-01 (MCP Server) in QUEUE.md is separate scope — AI agent access, not app platform

## Scope

### In Scope

**Manifest & Validation:**
- `AppManifestSchema` Pydantic model (all 17 sections from design doc)
- `parse_app_manifest()` with full field validation
- `browserVisible` field added to Mental Model ManifestSchema

**Subprocess Lifecycle:**
- Per-app virtual environment creation (`python -m venv`)
- Dependency installation from `requirements.txt`
- Process start/stop/restart with SIGTERM/SIGKILL
- Crash recovery with exponential backoff (max 3 retries)
- Health check polling (`GET /_health`)
- Auto-start on platform boot

**App SDK (`sempkm-app-sdk`):**
- In-repo package at `backend/sdk/`
- `App` class with lifecycle decorators (`on_install`, `on_startup`, `on_shutdown`, `on_uninstall`)
- `AppContext` with scoped clients: `CommandClient`, `GraphClient`, `StateClient`, `HttpClient`, `SettingsClient`
- Task handler registration via `@app.task("task-id")`
- Route handler registration via `@app.route("/_fragments/...")`
- Template rendering via `ctx.render_template()`
- SDK runner (`sempkm_app_sdk.runner`) — starts HTTP server on unix socket

**IPC & Proxy:**
- HTTP-over-unix-domain-socket communication
- `AppProxy` in platform routes `/app/{appId}/*` to subprocess socket
- Per-app scoped JWT token generation and validation
- Token rotation (1-hour expiry, auto-renewal in SDK)

**Scheduler:**
- `AppScheduler` — triggers tasks via `POST /app/{appId}/_tasks/{taskId}`
- Interval parsing (shorthand + ISO 8601)
- Concurrency guard (skip if previous run still active)
- Retry policy with exponential backoff
- User-adjustable intervals stored in `app_task_config` table

**Permission Enforcement:**
- Command type whitelist in `CommandClient`
- IRI prefix enforcement (`urn:sempkm:app:{appId}:`)
- Network domain restriction in `HttpClient` (glob pattern matching)
- State graph scoping (`urn:sempkm:app:{appId}:state`)
- Task invocation auth (reject without valid `X-SemPKM-Task-Run`)

**Frontend Integration (3 levels):**
- Level 1: Standalone pages (`app_shell.html` template, [Apps] sidebar section, fragment loading)
- Level 2: Workspace contributions (right pane sections, view contributions, command palette entries)
- Level 3: Object renderer overrides (per-type read/edit fragment dispatch)

**Bulk EventStore:**
- `EventStore.commit_bulk()` method with summary metadata
- `sempkm:BulkEvent` type in event graph
- SDK `ctx.commands.bulk()` context manager
- Batch size limit (1000 operations default)

**Admin Portal:**
- App list page (`/admin/apps`) with status, version, uptime
- App detail page with task history, permissions, data stats, logs, renderer assignments
- Install flow with permission approval dialog
- Start/stop/restart/uninstall actions
- Task interval adjustment UI

**Database:**
- `app_instances` table (status, PID, socket, manifest hash, restart count)
- `app_task_runs` table (execution history with status, duration, error)
- `app_task_config` table (interval overrides, pause state)
- `app_renderer_prefs` table (user preference for renderer conflicts)
- `app_permissions` table (approved permissions snapshot)
- Alembic migrations for all tables

**Docker/nginx:**
- `apps/` volume mount in docker-compose.yml
- `/app-static/` nginx location for app static assets
- `/app/{appId}/` nginx proxy to API (which proxies to unix socket)

**Test App:**
- Minimal `test-app` in `apps/test-app/` for E2E validation
- Exercises: page fragment, command execution, scheduled task, right pane, command palette
- Used by E2E tests; documents the SDK contract by example

### Out of Scope / Non-Goals

- RSS Reader app (M010)
- App marketplace (future)
- Subdomain routing (future)
- App-to-app dependencies (future)
- WebSocket support for apps (future)
- Containerized app isolation / Docker-in-Docker (future)
- Multi-user per-app permissions (future)
- Model data migrations framework (future, separate concern)

## Technical Constraints

- Backend: Python + FastAPI — apps also use FastAPI (via SDK runner)
- Frontend: htmx + vanilla JS — app fragments must be plain HTML, no React
- Apps run in Python subprocesses within the API container — no Docker-in-Docker
- Unix domain sockets for IPC — no TCP ports consumed per app
- App data goes through EventStore (standard or bulk) — no direct SPARQL writes to `urn:sempkm:current`
- App state graph (`urn:sempkm:app:{appId}:state`) is direct CRUD — not event-sourced
- API Docker image must include `pip` and `venv` capability at runtime
- All app static assets served by nginx (no proxying to subprocess for CSS/JS/images)

## Integration Points

- **EventStore** — Extended with `commit_bulk()` for batch ingestion; apps call via SDK `CommandClient`
- **Command Dispatcher** — `HANDLER_REGISTRY` keys used as permission whitelist in manifest validation
- **ModelService** — Version checking for app model dependencies; cleanup cascade on model uninstall
- **SettingsService** — App settings rendered in platform settings UI alongside global settings
- **Workspace sidebar** — New [Apps] section with app page links
- **Right pane** — Dynamic section injection from running apps
- **Command palette** — ninja-keys data extended with app commands at workspace load
- **Object tab** — Renderer override dispatch checks `AppRegistry` before default SHACL form
- **Admin portal** — New `/admin/apps` section with list + detail views
- **nginx** — New location blocks for `/app-static/` and `/app/` proxy
- **Docker Compose** — `./apps` volume mount, possibly runtime pip availability
- **Lifespan** — `AppManager` initialized and apps auto-started during platform boot

## Open Questions

- **Static asset cache busting** — Should app static assets include a version hash in the URL? Simplest: use `?v={app_version}` query param on CSS/JS includes. Or rely on nginx `expires 1h` and accept stale cache during development.
- **App log storage** — Design shows "last 50 lines" in admin. Should logs go to SQLite (queryable, persistent) or just Docker stdout (simple, ephemeral)? Current thinking: capture subprocess stdout/stderr into a ring buffer in memory, plus forward to platform logger. No SQLite for logs.
- **Concurrent app installations** — Can two apps install simultaneously? Probably not an issue for v1 (personal tool, manual installs), but the install flow should use a lock to prevent venv creation races.
