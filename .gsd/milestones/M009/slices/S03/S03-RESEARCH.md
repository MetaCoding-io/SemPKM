# S03: Admin Portal & Docker/nginx Integration — Research

**Date:** 2026-03-16
**Researcher:** GSD auto-mode

## Summary

S03 is straightforward application of established admin patterns. The codebase already has a fully featured admin portal (`/admin/` prefix, `base.html` extends, htmx partial rendering, sidebar nav) with model list/detail pages as the reference implementation. The new work: a separate `admin_router.py` in the apps module (per D150), two admin templates (list + detail), nginx location blocks for `/app-static/` and `/app/{appId}/`, docker-compose `./apps` volume mount, sidebar nav entry, and admin index card.

All data surfaces already exist: `AppManager.get_status()` returns status/PID/uptime/restart_count/error_message/version, `get_logs()` returns the ring buffer, `AppRegistry.list_apps()` lists installed apps, and `AppManifestSchema` provides all manifest metadata (permissions, tasks, frontend contributions). The install flow calls `AppManager.install(path)` which is already atomic (validate → venv → deps → DB → start).

No new technology, no unfamiliar APIs. The main judgment call is how to structure the admin list/detail pages and install flow. The detail page in this slice shows permissions + data stats + logs + start/stop/restart/uninstall actions. Task history and renderer assignments are deferred to S05/S06 per D148.

## Recommendation

**4 tasks: admin router + templates, nginx config, docker-compose + static asset copying, sidebar/index wiring.**

Build order: admin router+templates first (most code), then nginx+docker config (short), then sidebar/index wiring (trivial). All tasks are independent except sidebar needs the router URL to exist.

## Implementation Landscape

### Key Files — Existing (to modify)

| File | What Changes |
|------|-------------|
| `backend/app/main.py` | Include `app_admin_router` before `browser_router` |
| `backend/app/templates/components/_sidebar.html` | Add "Applications" nav-link in Admin group |
| `backend/app/templates/admin/index.html` | Add "Applications" card |
| `frontend/nginx.conf` | Add `/app-static/` alias and `/app/{appId}/` proxy location |
| `docker-compose.yml` | Add `./apps:/app/apps:ro` volume mount to api service, add `/app/data/apps-static` path accessible from nginx |
| `backend/app/apps/manager.py` | Add `_copy_static_assets()` to install flow — copies `frontend/static/` to `/app/data/apps-static/{appId}/` |

### Key Files — New (to create)

| File | Purpose |
|------|---------|
| `backend/app/apps/admin_router.py` | Admin HTML routes: list, detail, install, start/stop/restart/uninstall actions |
| `backend/app/templates/admin/apps/list.html` | App list page showing all installed apps with status, version, uptime |
| `backend/app/templates/admin/apps/detail.html` | App detail page: permissions, data stats, logs, actions |
| `backend/tests/test_app_admin.py` | Unit tests for admin router endpoints |

### Build Order

**Task 1: Admin router + templates (~main work)**
- Create `backend/app/apps/admin_router.py` with `app_admin_router = APIRouter(prefix="/admin/apps")`
- Routes:
  - `GET /admin/apps` — list page (queries AppManager for all apps, gets status for each)
  - `GET /admin/apps/{app_id}` — detail page (status, manifest, permissions, logs)
  - `POST /admin/apps/install` — install from path (calls `AppManager.install()`)
  - `POST /admin/apps/{app_id}/start` — start action
  - `POST /admin/apps/{app_id}/stop` — stop action
  - `POST /admin/apps/{app_id}/restart` — restart action
  - `POST /admin/apps/{app_id}/uninstall` — uninstall action (with mode param for future data cleanup)
- All routes use `require_role("owner")`
- htmx partial rendering pattern: check `HX-Request` header, return `block_name="content"` for sidebar nav
- Create list template showing app cards with status badge, version, uptime, PID, and action buttons
- Create detail template showing: status section, permissions section (from manifest), logs section (from ring buffer), action buttons
- Follows model_detail.html pattern for layout structure

**Task 2: nginx + docker-compose + static asset support**
- Add to `frontend/nginx.conf`:
  ```nginx
  # App static assets served by nginx
  location /app-static/ {
      alias /app/data/apps-static/;
      expires 1h;
      add_header Cache-Control "public, immutable";
  }
  ```
- Add to `docker-compose.yml` api service volumes: `./apps:/app/apps:ro`
- Add to docker-compose.yml: share `sempkm_data` volume with frontend service so nginx can read `/app/data/apps-static/`
- Add `_copy_static_assets()` to `AppManager.install()` — copies `{app_dir}/frontend/static/` to `/app/data/apps-static/{app_id}/` if the directory exists

**Task 3: Main.py wiring, sidebar, and admin index**
- Include `app_admin_router` in `main.py` (after `admin_router`, before `browser_router`)
- Add "Applications" nav-link to sidebar `_sidebar.html` in the Admin group (after "Mental Models", owner-only)
- Add "Applications" card to `admin/index.html`

**Task 4: Unit tests**
- Test admin list endpoint returns correct template context
- Test admin detail endpoint includes status, manifest, permissions, logs
- Test install endpoint calls manager.install()
- Test start/stop/restart/uninstall endpoints
- Test require_role enforcement
- All tests mock AppManager and AppRegistry

### Verification Approach

**Unit tests:** `pytest tests/test_app_admin.py -v` — all endpoints return correct template context with mocked services.

**Manual Docker verification (S07 scope):** Admin list page at `/admin/apps` shows installed apps. Detail page shows correct permissions and logs. Install flow works. Start/stop/restart/uninstall actions update status correctly. nginx serves `/app-static/{appId}/` files. Sidebar shows "Applications" link.

## Constraints

- Admin router must be a **separate sub-module** at `backend/app/apps/admin_router.py`, not added to existing `admin/router.py` (D150, existing admin router is 1211 lines).
- Admin router uses `prefix="/admin/apps"` — no prefix stacking since it's included directly in `main.py`, not nested under existing admin router.
- The `/app-static/` nginx location needs access to the `sempkm_data` Docker volume where app static files are copied during install. The frontend (nginx) service doesn't currently mount this volume — it needs to be added.
- The `./apps` directory doesn't exist yet in the repo root — docker-compose mount must be tolerant of a missing directory, or we create a placeholder.
- AppManager methods are async — admin router endpoints must be async too.
- `get_status()` opens a DB session internally — no need for `get_db_session` dependency in admin routes for status.
- Task history and scheduler UI are **S05 scope** — the S03 detail page shows a placeholder "Tasks will appear here when scheduler is active" section.
- Renderer assignments are **S06 scope** — similarly placeholder in S03 detail page.

## Common Pitfalls

- **nginx `alias` vs `root` for app-static** — Must use `alias /app/data/apps-static/;` (with trailing slash) not `root`. With `root`, nginx would look for `/app/data/apps-static/app-static/{appId}/`, doubling the path. `alias` replaces the matched prefix entirely.
- **Docker volume sharing between services** — The `sempkm_data` volume is only mounted on the `api` service. For nginx to serve static files from it, the frontend service needs a read-only mount of the same volume (or the relevant subdirectory).
- **htmx partial rendering for admin pages** — Admin pages use `block_name="content"` for htmx swaps into `#app-content`. Must check `HX-Target` header to distinguish sidebar navigation (returns `content` block) from in-page actions (returns specific fragments). See `admin_ops_log` pattern (D083).
- **Missing apps directory** — `./apps:/app/apps:ro` mount will fail if `./apps/` doesn't exist. Create an empty `apps/.gitkeep` or use `:ro` with Docker's tolerance for missing source dirs (depends on Docker version).

## Sources

- `backend/app/admin/router.py` — existing admin pattern (1211 lines, model list/detail/install/actions)
- `backend/app/templates/admin/model_detail.html` — reference detail page layout
- `backend/app/templates/admin/index.html` — admin index card pattern
- `backend/app/templates/components/_sidebar.html` — sidebar nav structure
- `.gsd/design/APP-PLATFORM-DESIGN.md` §11 — admin portal wireframe
- `.gsd/design/APP-PLATFORM-DESIGN.md` §15 — disk layout, nginx config, static asset paths
