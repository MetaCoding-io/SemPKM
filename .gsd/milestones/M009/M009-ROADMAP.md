# M009: App Platform

**Vision:** SemPKM gains a sandboxed app platform where third-party and first-party Python apps extend the system with custom UI, background tasks, external API integrations, and object renderer overrides — all running in isolated subprocesses communicating via HTTP-over-unix-socket IPC.

## Success Criteria

- A test app installs from the `apps/` directory via the admin portal — manifest validated, venv created, deps installed, process started, health check passes
- The test app's standalone page loads in the workspace via htmx fragment through the platform proxy
- The test app creates an object via `ctx.commands.execute()` and it appears in the object browser
- The test app's scheduled task fires at the configured interval and logs success in admin task history
- The test app's right pane section appears when viewing an object
- The test app's command palette entry opens a fragment dialog
- Admin shows app status (running/stopped/error), PID, uptime, task history, logs, permissions, renderer assignments
- App restarts automatically after crash (up to 3 retries with exponential backoff)
- Uninstall "app + data" removes all app-prefixed IRIs from `urn:sempkm:current`
- Platform restart auto-starts all previously running apps
- App static assets served by nginx at `/app-static/{appId}/`
- Types with `browserVisible: false` are hidden from object browser but queryable via SPARQL

## Key Risks / Unknowns

- **Subprocess lifecycle + health check reliability** — `asyncio.create_subprocess_exec` for process supervision with health polling is new territory in this codebase. Signal handling in Docker, socket cleanup on crash, venv creation via `uv` — all untested. This is the critical path.
- **SDK package structure + UDS HTTP server** — The SDK is an in-repo Python package installed into per-app venvs. uvicorn on UDS, JWT validation, template rendering, scoped clients — the developer-facing contract must be right first time.
- **IPC proxy reliability** — httpx UDS transport, cookie/header forwarding through the proxy, JWT token rotation — the platform↔app communication channel must be solid.
- **Frontend fragment injection** — 3 levels of htmx fragment integration (standalone pages, workspace contributions, renderer overrides) sharing the platform CSS namespace. Right pane dynamic injection requires changing the currently hard-coded section list.

## Proof Strategy

- **Subprocess lifecycle** → retire in S01 by installing a minimal app, watching it start, health-check pass, crash-recover, and auto-start on platform reboot. Real Docker stack, real `uv venv`, real process.
- **SDK + IPC** → retire in S02 by having a test app serve an HTML fragment that the platform proxy routes to the workspace. Real UDS, real JWT, real httpx transport.
- **Frontend integration** → retire in S04 by loading an app's standalone page in the workspace sidebar, with fragment content served through the proxy chain.
- **Scheduler + permissions** → retire in S05 by having a scheduled task fire, execute through the permission-enforced SDK, and record results in admin.

## Verification Classes

- Contract verification: pytest unit tests for manifest validation, permission enforcement, interval parsing, bulk EventStore, JWT claims, IRI prefix validation — all run without Docker in <5s
- Integration verification: test app subprocess starts on real UDS, serves fragment through proxy, creates object via SDK, task fires via scheduler — requires Docker stack
- Operational verification: crash recovery with backoff, auto-start on platform boot, clean uninstall with data cleanup, socket file cleanup
- UAT / human verification: admin portal shows accurate app state, workspace sidebar has [Apps] section, right pane sections appear, command palette entries work

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 8 slice deliverables are complete (S01–S08)
- Test app installs, starts, serves pages, creates objects, runs scheduled tasks, and appears in admin — all exercised through the Docker stack
- Admin portal shows accurate live app status with task history, logs, and uninstall actions
- Workspace integrates app contributions at all 3 levels (pages, workspace widgets, renderer overrides)
- Crash recovery and auto-start verified in Docker environment
- E2E Playwright tests cover the install → page → command → task → admin → uninstall flow
- User guide documents the app platform for both users (installing/managing apps) and developers (building apps with the SDK)
- Success criteria re-checked against live behavior in the Docker stack

## Requirement Coverage

- Covers: APP-01, APP-02, APP-03, APP-04, APP-05, APP-06, APP-07, APP-08, APP-09, APP-10, APP-11, APP-12, APP-13, APP-14
- Partially covers: none
- Leaves for later: RSS-01 through RSS-08 (M010 — first real app on the platform)
- Orphan risks: none — all 14 APP requirements mapped to slices below

| Requirement | Primary Slice | Supporting Slices |
|-------------|--------------|-------------------|
| APP-01 (manifest validation) | S01 | — |
| APP-02 (subprocess lifecycle) | S01 | S02 |
| APP-03 (App SDK) | S02 | S05 |
| APP-04 (IPC via HTTP/UDS) | S02 | S03 |
| APP-05 (permission enforcement) | S05 | — |
| APP-06 (task scheduler) | S05 | — |
| APP-07 (frontend L1 — standalone pages) | S04 | — |
| APP-08 (frontend L2 — workspace contributions) | S06 | — |
| APP-09 (frontend L3 — renderer overrides) | S06 | — |
| APP-10 (admin monitoring portal) | S03 | S05, S06 |
| APP-11 (bulk EventStore) | S05 | — |
| APP-12 (browserVisible) | S05 | — |
| APP-13 (DB tables + migrations) | S01 | S05 |
| APP-14 (Docker/nginx integration) | S03 | — |

## Slices

- [x] **S01: Manifest, DB Schema & Subprocess Lifecycle** `risk:high` `depends:[]`
  > After this: admin can install an app from disk (manifest validated, venv created, deps installed, process started), see its status (running/stopped/error with PID), stop/restart it, and watch it auto-restart after crash — all in the Docker stack.

- [x] **S02: App SDK & IPC Proxy** `risk:high` `depends:[S01]`
  > After this: a test app built with the SDK starts on a unix socket, the platform proxies HTTP requests to it via httpx UDS transport with JWT auth, and the app can call back to the platform API (commands, graph queries) through scoped SDK clients.

- [x] **S03: Admin Portal & Docker/nginx Integration** `risk:medium` `depends:[S01,S02]`
  > After this: admin portal at `/admin/apps` shows app list with status/version/uptime, detail page with permissions and data stats, start/stop/restart/uninstall actions. nginx proxies `/app/{appId}/` and serves `/app-static/{appId}/`. docker-compose.yml mounts `./apps`.

- [x] **S04: Frontend Level 1 — Standalone Pages & Sidebar** `risk:medium` `depends:[S02,S03]`
  > After this: installed apps with page declarations appear in the workspace [Apps] sidebar section. Clicking an app page loads the app's fragment content through the platform proxy into the workspace via htmx. App CSS/JS loaded when app UI is active.

- [x] **S05: Scheduler, Permissions, Bulk EventStore & browserVisible** `risk:medium` `depends:[S02]`
  > After this: platform scheduler triggers app tasks at configured intervals with concurrency guard and retry. SDK clients enforce command whitelist, IRI prefix, and network domain restrictions. `commit_bulk()` records summary metadata. Types with `browserVisible: false` hidden from browser.

- [x] **S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides** `risk:medium` `depends:[S04,S05]`
  > After this: app right-pane sections appear alongside Relations/Lint when viewing objects. App views appear in Views section. App command palette entries registered with ninja-keys. Apps can override default SHACL form with custom read/edit renderers for specific types.

- [x] **S07: Test App, E2E Tests & Integration Proof** `risk:low` `depends:[S01,S02,S03,S04,S05,S06]`
  > After this: `apps/test-app/` exercises all SDK features (page, command, task, right pane, command palette, renderer override). Playwright E2E tests prove the full vertical: install → page → command → task → admin → uninstall. All success criteria verified against the live Docker stack.

- [x] **S08: User Guide Documentation** `risk:low` `depends:[S07]`
  > After this: `docs/guide/` has pages covering app management (installing, monitoring, uninstalling from admin) and app development (SDK reference, manifest format, frontend integration levels). Glossary updated.

## Boundary Map

### S01 → S02

Produces:
- `AppManifestSchema` Pydantic model with full validation (`backend/app/apps/manifest.py`)
- `AppManager` with `install()`, `start()`, `stop()`, `restart()`, `uninstall()`, `get_status()` (`backend/app/apps/manager.py`)
- `AppRegistry` in-memory manifest cache with `get_app()`, `list_apps()`, `get_manifest()` (`backend/app/apps/registry.py`)
- SQLAlchemy models for `app_instances`, `app_task_runs`, `app_task_config`, `app_renderer_prefs`, `app_permissions` (`backend/app/apps/models.py`)
- Alembic migration 013 creating all 5 app tables
- `AppManager` integrated into platform `lifespan()` in `main.py`
- `PyJWT` and `packaging` added to `pyproject.toml`
- Per-app unix socket at `/tmp/sempkm-app-{appId}.sock` (created by subprocess, cleaned by manager)

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `sempkm-app-sdk` package at `backend/sdk/` with `App` class, lifecycle decorators, route/task decorators
- `AppContext` with `CommandClient`, `GraphClient`, `StateClient`, `HttpClient`, `SettingsClient` stubs (permission enforcement deferred to S05)
- SDK runner (`sempkm_app_sdk.runner`) starting uvicorn on UDS with `/_health` endpoint
- `AppProxy` routing `/app/{appId}/*` to subprocess UDS via httpx (`backend/app/apps/proxy.py`)
- JWT token generation on app start, validation in SDK, platform-side token renewal endpoint (`backend/app/apps/tokens.py`)
- Platform API routes for app proxy (`backend/app/apps/router.py`)

Consumes:
- S01: `AppManager` (to get socket path, app status), `AppRegistry` (to get manifest), `AppManifestSchema`, SQLAlchemy models

### S03 → S04

Produces:
- Admin list page (`/admin/apps`) with status, version, uptime, PID, memory
- Admin detail page with permissions display, data stats, start/stop/restart/uninstall actions
- Install flow endpoint (calls `AppManager.install()`)
- nginx config: `/app-static/{appId}/` location, `/app/{appId}/` proxy to API
- `docker-compose.yml`: `./apps:/app/apps` volume mount
- Admin app router (`backend/app/apps/admin_router.py`) + templates (`backend/app/templates/admin/apps/`)

Consumes:
- S01: `AppManager`, `AppRegistry`, SQLAlchemy models
- S02: `AppProxy` (for status verification), JWT tokens (for app communication)

### S04 → S06

Produces:
- `app_shell.html` template wrapping app fragment content in platform chrome
- [Apps] sidebar section in workspace with links to installed app pages
- htmx fragment loading from `/app/{appId}/_fragments/{page}` through proxy
- App CSS/JS loading when app page is active
- Browser sub-router for app pages (`backend/app/browser/apps.py`)

Consumes:
- S02: `AppProxy` (fragment proxying), SDK route handlers
- S03: nginx proxy config (requests reach API), admin install flow (apps are installed)

### S05 → S06

Produces:
- `AppScheduler` with interval parsing, concurrency guard, retry, task history recording (`backend/app/apps/scheduler.py`)
- SDK `CommandClient` with command whitelist + IRI prefix enforcement
- SDK `GraphClient` with SPARQL read scoping
- SDK `HttpClient` with network domain restriction (glob matching)
- SDK `StateClient` scoped to `urn:sempkm:app:{appId}:state`
- `EventStore.commit_bulk()` with summary metadata + SDK `ctx.commands.bulk()` context manager
- `browserVisible` field on `ManifestSchema` + object browser filtering
- `app_task_config` table population with user-adjustable intervals
- Task history in `app_task_runs` table
- Admin detail page extended with task history and interval adjustment

Consumes:
- S02: SDK client stubs (now given real enforcement), `AppProxy` (scheduler triggers tasks via HTTP), JWT tokens

### S06 → S07

Produces:
- Dynamic right pane sections from app contributions (endpoint merging platform + app sections)
- App view contributions in Views explorer section
- App command palette entries registered with ninja-keys at workspace load
- Object renderer override dispatch: `AppRegistry` checked before default SHACL form, with user preference for conflicts
- `app_renderer_prefs` table usage for conflict resolution

Consumes:
- S04: app_shell.html pattern, [Apps] sidebar, fragment loading
- S05: `AppRegistry` renderer/contribution metadata, scheduler running, permissions enforced

### S07 → S08

Produces:
- `apps/test-app/` exercising: standalone page, command execution, scheduled task, right pane section, command palette entry, renderer override
- Playwright E2E spec files proving full install → use → admin → uninstall flow
- All success criteria verified against live Docker stack

Consumes:
- All prior slices: full platform assembled

### S08 (terminal)

Produces:
- User guide chapter(s) in `docs/guide/` for app management and app development
- Glossary entries for App Platform, App Manifest, App SDK, App Sandbox
- README TOC update

Consumes:
- S07: verified behavior to document accurately
