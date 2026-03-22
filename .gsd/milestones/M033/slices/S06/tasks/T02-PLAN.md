---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T02: Workspace catalog routes, templates, sidebar entry, and CSS

**Slice:** S06 — App Catalog Pages
**Milestone:** M033

## Description

Add workspace-side catalog browsing so users can discover and learn about apps without visiting the admin portal. This adds two new routes to the browser apps router, two new templates (catalog list grid + catalog detail), a `openCatalogTab()` JS function, a "Browse Catalog" entry in the APPS explorer sidebar section, and catalog-specific CSS styles.

The catalog list page shows all apps (installed + available on disk) in a searchable card grid. The catalog detail page shows description, features, permissions, model dependencies, and install/uninstall actions. Install/uninstall actions are only rendered for users with the owner role — regular users see read-only information.

## Steps

1. **Add catalog routes to `backend/app/browser/apps.py`:**
   - `GET /apps/catalog` — catalog list page. Collects all installed apps from `app_manager.registry.list_apps()` and available (not-installed) apps by scanning `app_manager._apps_dir`. For each, include: `app_id`, `name`, `description`, `version`, `category`, `features`, `status` (running/stopped/not_installed), `author`. Pass `user` from request state to template for role-based rendering. Return `catalog_list.html` template.
   - `GET /apps/catalog/{app_id}` — catalog detail page. Load manifest from registry (for installed apps) or parse from disk (for available apps). Include full manifest data, status info for installed apps, and user role. Return `catalog_detail.html` template.
   - Both routes should work for all authenticated users (no `require_role("owner")` — read-only browsing is open to all). The user object is available from `request.state.user` after auth middleware.
   - Import `User` from `app.auth.models` and `Depends` from fastapi. Use the existing auth dependency pattern from the codebase: `from app.auth.dependencies import get_current_user` and accept `user: User = Depends(get_current_user)`.

2. **Create `backend/app/templates/browser/catalog_list.html`:**
   - This is a standalone HTML fragment (no `{% extends %}`) loaded into a dockview panel via htmx.
   - Card grid layout using new `.catalog-grid` CSS class.
   - Each card shows: app name, version pill, status indicator (running/stopped/available), category pill if present, description (truncated to 2 lines), and a "View Details" link that calls `openCatalogDetailTab(appId)`.
   - Include a search/filter input at top that filters cards by name/description client-side using simple JS `input` event listener + display:none toggling.
   - The detail link should call a JS function: `onclick="openCatalogDetailTab('{{ app.app_id }}')"`.

3. **Create `backend/app/templates/browser/catalog_detail.html`:**
   - Standalone HTML fragment for dockview panel.
   - Header: app name (h2), version pill, status badge, category pill.
   - Description paragraph.
   - Features section: unordered list with checkmark icons (only if features list is non-empty).
   - Permissions section: table showing commands, network, SPARQL, backgroundTasks, settings (same pattern as admin detail.html permissions table).
   - Dependencies section: model dependency list if any.
   - Author section: author name + URL if present.
   - Actions section (only if `user.role == 'owner'`):
     - For installed + stopped apps: Start button (POST to `/admin/apps/{app_id}/start`)
     - For installed + running apps: Stop, Restart buttons
     - Uninstall button with confirm dialog
     - For not-installed apps: Install button (POST to `/admin/apps/install` with `app_path`)
   - A "Back to Catalog" link that calls `openCatalogTab()`.

4. **Update `frontend/static/js/workspace.js`:**
   - Add `openCatalogTab()` function that creates a dockview panel with `specialType: 'catalog'`, loading `/browser/apps/catalog` via htmx. Use `tabKey = 'catalog:list'`. Follow the `openAppPageTab()` pattern (lines 775-793).
   - Add `openCatalogDetailTab(appId)` function that creates a dockview panel with `specialType: 'catalog-detail'`, loading `/browser/apps/catalog/{appId}` via htmx. Use `tabKey = 'catalog:' + appId`.
   - Expose both on `window`.

5. **Update sidebar and CSS:**
   - In `backend/app/templates/browser/apps_explorer.html`: Add a "Browse Catalog" entry at the bottom of the section (after the app page list and the "No apps installed" message), as a tree-leaf with `onclick="openCatalogTab()"` and `data-lucide="layout-grid"` icon.
   - In `frontend/static/css/style.css`: Add catalog-specific styles at the end of the file:
     - `.catalog-grid` — CSS grid, `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`, gap 16px, padding 16px
     - `.catalog-card` — background, border, border-radius, padding, hover elevation
     - `.catalog-card-header` — flex row for name + badges
     - `.catalog-card-desc` — 2-line clamp with `-webkit-line-clamp: 2`
     - `.catalog-search` — full-width input with search icon styling
     - `.category-pill` — small colored pill (similar to version-pill but with accent color)
     - `.feature-list` — list with checkmark pseudo-elements, no bullets
     - `.permission-badge` — inline badge for permission indicators
     - `.catalog-detail` — max-width container for detail page
     - `.catalog-actions` — flex row for action buttons

## Must-Haves

- [ ] `GET /browser/apps/catalog` returns a card grid of all apps (installed + available)
- [ ] `GET /browser/apps/catalog/{app_id}` returns a detail page with description, features, permissions
- [ ] Install/uninstall actions only appear for users with owner role
- [ ] `openCatalogTab()` and `openCatalogDetailTab(appId)` functions exist on `window`
- [ ] "Browse Catalog" entry appears in APPS explorer sidebar section
- [ ] Catalog CSS styles are in `style.css`
- [ ] Cards work with existing manifests that have no `category`/`features`/`readme` fields

## Verification

- `grep -q 'openCatalogTab' frontend/static/js/workspace.js` — JS function exists
- `grep -q 'openCatalogDetailTab' frontend/static/js/workspace.js` — detail JS function exists
- `test -f backend/app/templates/browser/catalog_list.html` — list template exists
- `test -f backend/app/templates/browser/catalog_detail.html` — detail template exists
- `grep -q 'Browse Catalog' backend/app/templates/browser/apps_explorer.html` — sidebar entry
- `grep -q 'catalog-grid' frontend/static/css/style.css` — CSS exists
- `grep -q '/apps/catalog' backend/app/browser/apps.py` — route exists
- `cd backend && python -c "from app.browser.apps import apps_router; routes = [r.path for r in apps_router.routes]; assert '/apps/catalog' in routes; assert '/apps/catalog/{app_id}' in routes"` — routes registered

## Inputs

- `backend/app/browser/apps.py` — existing browser apps router to extend with catalog routes
- `backend/app/apps/manifest.py` — `AppManifestSchema` with `category`, `features`, `readme` fields (from T01)
- `backend/app/apps/admin_router.py` — reference for app listing pattern (scanning installed + available apps)
- `backend/app/templates/browser/apps_explorer.html` — existing sidebar template to add catalog entry
- `frontend/static/js/workspace.js` — existing workspace JS to add `openCatalogTab()`
- `frontend/static/css/style.css` — existing styles to extend with catalog CSS

## Expected Output

- `backend/app/browser/apps.py` — extended with catalog list + detail routes
- `backend/app/templates/browser/catalog_list.html` — new catalog grid template
- `backend/app/templates/browser/catalog_detail.html` — new catalog detail template
- `backend/app/templates/browser/apps_explorer.html` — "Browse Catalog" entry added
- `frontend/static/js/workspace.js` — `openCatalogTab()` and `openCatalogDetailTab()` added
- `frontend/static/css/style.css` — catalog-specific CSS added
