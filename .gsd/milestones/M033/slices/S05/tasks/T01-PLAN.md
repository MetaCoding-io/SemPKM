---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T01: Backend catalog router, templates, and unit tests

**Slice:** S05 — App Catalog Pages
**Milestone:** M033

## Description

Create the full backend for the app catalog: a browser sub-router with list, detail, install, and uninstall endpoints; two Jinja2 templates (card grid and detail page); and unit tests. The catalog shows ALL apps from the `apps/` directory (excluding `test-app`), merging manifest data with installed/running status from the app manager.

## Steps

1. **Create `backend/app/browser/catalog.py`** with a `catalog_router` (`APIRouter` with no prefix — routes are `/catalog`, `/catalog/{app_id}`, etc., mounted under the `/browser` prefix by `router.py`):
   - `GET /catalog` — Scans `Path("/app/apps")` for directories containing `manifest.yaml`. For each, parse the manifest via `parse_app_manifest()`. Check `request.app.state.app_manager.registry` for installed status and `app_manager.get_status()` for running/stopped. Exclude `test-app`. Sort by name. Render `catalog_page.html` with list of app dicts.
   - `GET /catalog/{app_id}` — Load a single manifest from `apps_dir / app_id / manifest.yaml`. Merge with install status. Render `catalog_detail.html`. Return 404 if app_id doesn't exist.
   - `POST /catalog/{app_id}/install` — Require owner role via `Depends(require_role("owner"))`. Call `app_manager.install(apps_dir / app_id)`. On success, re-render the detail page with updated status. On failure, render detail with error message.
   - `POST /catalog/{app_id}/uninstall` — Require owner role. Call `app_manager.uninstall(app_id)`. Re-render detail page.
   - The user object should be fetched via `Depends(get_current_user)` for the list/detail endpoints (to determine if install/uninstall buttons should appear based on role).

2. **Create `backend/app/templates/browser/catalog_page.html`** — Card grid following `docs_page.html` pattern:
   - Page header: "App Catalog" title with subtitle
   - Grid of cards (`.catalog-cards` → `.catalog-card`), each showing: Lucide icon (`package` as default), app name, short description, status badge (installed/running/available)
   - Each card is a clickable div using htmx: `hx-get="/browser/catalog/{app_id}"` with `hx-target="closest .group-editor-area"` and `hx-swap="innerHTML"` (same pattern as docs chapter navigation within the panel)
   - Script block calling `lucide.createIcons()` at the end

3. **Create `backend/app/templates/browser/catalog_detail.html`** — Full detail view:
   - Back button: `hx-get="/browser/catalog"` targeting same container
   - App name, version, author (with optional URL link), license, description
   - Permissions section: list which permissions are declared (sparql.read, network hosts, backgroundTasks, commands list, settings)
   - Model dependencies section: list required models with version ranges
   - Background tasks section: list task names/descriptions if any
   - Settings section: list setting labels (no values — catalog is read-only for config)
   - Install/Uninstall button (only for owners): htmx POST to install/uninstall endpoint, targeting same container to re-render. Show error if action failed (via `error` context variable).
   - Status badge (available/installed/running/stopped)
   - Script block calling `lucide.createIcons()`

4. **Mount `catalog_router` in `backend/app/browser/router.py`**:
   - Import: `from .catalog import catalog_router`
   - Include BEFORE `objects_router` line: `router.include_router(catalog_router)` — critical because `objects_router` has catch-all `:path` patterns

5. **Create `backend/tests/test_catalog.py`** with unit tests:
   - Test that `GET /catalog` returns HTML with app cards for available apps
   - Test that `GET /catalog/{app_id}` returns detail page for a valid app
   - Test that `GET /catalog/nonexistent` returns 404
   - Test that `test-app` is excluded from the listing
   - Test that install/uninstall endpoints require authentication

## Must-Haves

- [ ] `catalog_router` registered in `browser/router.py` before `objects_router`
- [ ] `GET /catalog` returns all apps except `test-app` with correct status badges
- [ ] `GET /catalog/{app_id}` returns full manifest detail page
- [ ] Install/uninstall endpoints require owner role
- [ ] Templates follow existing Lucide icon conventions (CSS sizing, `flex-shrink: 0`, `stroke: currentColor`)
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_catalog.py -v` — all tests pass
- `rg -c "catalog_router" backend/app/browser/router.py` returns 2

## Inputs

- `backend/app/browser/router.py` — existing browser router to mount catalog sub-router
- `backend/app/browser/pages.py` — reference for the docs page endpoint pattern
- `backend/app/templates/browser/docs_page.html` — reference for card grid template structure
- `backend/app/apps/manager.py` — `AppManager.install()`, `.uninstall()`, `.get_status()`, `.registry`
- `backend/app/apps/manifest.py` — `parse_app_manifest()`, `AppManifestSchema` fields
- `backend/app/apps/registry.py` — `AppRegistry.list_apps()`, `.get_manifest()`
- `backend/app/auth/dependencies.py` — `require_role("owner")`, `get_current_user`
- `apps/` — directory containing all 11 app subdirectories with `manifest.yaml` files

## Expected Output

- `backend/app/browser/catalog.py` — new catalog sub-router with 4 endpoints
- `backend/app/browser/router.py` — modified to import and include `catalog_router`
- `backend/app/templates/browser/catalog_page.html` — new catalog grid template
- `backend/app/templates/browser/catalog_detail.html` — new catalog detail template
- `backend/tests/test_catalog.py` — new unit tests for catalog endpoints
