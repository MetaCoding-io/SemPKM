# S06: App Catalog Pages

**Goal:** Each app has a rich detail page showing description, features, permissions, and install/uninstall actions. The catalog is browsable from both the admin portal and the workspace sidebar.
**Demo:** Navigate to admin app detail → see description, features list, permissions summary at top with operational info collapsed below. Open workspace → click "Browse Catalog" in the APPS explorer section → see a catalog grid of all apps with search. Click an app → see its detail page with install/uninstall actions (owner-only).

## Must-Haves

- `AppManifestSchema` extended with optional `category`, `features`, and `readme` fields (backward-compatible — existing manifests continue to validate)
- Admin app detail page redesigned: catalog showcase (description, features list, permissions) at top, operational sections (PID, uptime, logs, tasks) collapsed in `<details>`
- Admin app list page shows category badges when populated
- Workspace-side catalog list route (`GET /browser/apps/catalog`) with grid layout showing all apps (installed + available on disk)
- Workspace-side catalog detail route (`GET /browser/apps/catalog/{app_id}`) with description, features, permissions, and install/uninstall actions (owner-only)
- `openCatalogTab()` JS function wired from APPS explorer section in workspace sidebar
- Catalog-specific CSS: feature list, permission badges, category pills, card grid

## Verification

- `cd backend && python -c "from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(appId='test', version='1.0.0', name='Test', backend={'entrypoint': 'x:Y'}); assert m.category == ''; assert m.features == []; assert m.readme == ''"` — schema defaults work
- `cd backend && python -c "from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(appId='test', version='1.0.0', name='Test', backend={'entrypoint': 'x:Y'}, category='sync', features=['Feature 1'], readme='# Hello'); assert m.category == 'sync'"` — extended fields parse
- `grep -q 'openCatalogTab' frontend/static/js/workspace.js` — JS function exists
- `grep -q 'catalog' backend/app/browser/apps.py` — catalog routes exist
- `test -f backend/app/templates/browser/catalog_list.html` — workspace catalog list template exists
- `test -f backend/app/templates/browser/catalog_detail.html` — workspace catalog detail template exists
- `grep -q 'Operations' backend/app/templates/admin/apps/detail.html` — admin detail has collapsed ops section
- `grep -q 'Browse Catalog' backend/app/templates/browser/apps_explorer.html` — sidebar entry exists

## Observability / Diagnostics

- **Schema validation**: Invalid `category`/`features`/`readme` values produce `pydantic.ValidationError` at manifest parse time — visible in install logs and admin list error messages.
- **Admin detail page**: Features/permissions render at top; ops sections inside `<details>`. Collapse state is browser-local. Inspect via `grep '<details>' backend/app/templates/admin/apps/detail.html`.
- **Catalog routes (T02)**: HTTP 404 for unknown app_id, logged at WARNING level. Install/uninstall actions produce structured log entries with user email and app_id.
- **Redaction**: No secrets in manifest fields. Category/features/readme are user-facing metadata only.

## Tasks

- [x] **T01: Extend schema and redesign admin catalog pages** `est:1h`
  - Why: Add optional catalog metadata to the manifest schema and transform the admin app detail page from ops-monitoring-focused to catalog-showcase-first, keeping operational sections accessible but collapsed.
  - Files: `backend/app/apps/manifest.py`, `backend/app/templates/admin/apps/detail.html`, `backend/app/templates/admin/apps/list.html`
  - Do: Add `category: str = ""`, `features: list[str] = []`, `readme: str = ""` to `AppManifestSchema`. Redesign admin detail.html: prominent description, features list with checkmark bullets, permissions summary table at top. Push PID/uptime/logs/task-history into a collapsible `<details>` "Operations" section. Add category badge display to list.html cards. All changes must be backward-compatible — existing 11 app manifests with no new fields must render correctly.
  - Verify: `cd backend && python -c "from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(appId='t', version='1.0.0', name='T', backend={'entrypoint': 'x:Y'}); assert m.features == []"` and `grep -q 'Operations' backend/app/templates/admin/apps/detail.html`
  - Done when: Schema validates with and without new fields; admin detail page shows catalog-first layout with ops collapsed

- [x] **T02: Workspace catalog routes, templates, sidebar entry, and CSS** `est:1.5h`
  - Why: Make the app catalog browsable from within the workspace — the second half of the CAT-02 requirement. Users should be able to discover and learn about apps without going to the admin portal.
  - Files: `backend/app/browser/apps.py`, `backend/app/templates/browser/catalog_list.html`, `backend/app/templates/browser/catalog_detail.html`, `backend/app/templates/browser/apps_explorer.html`, `frontend/static/js/workspace.js`, `frontend/static/css/style.css`
  - Do: Add `GET /apps/catalog` and `GET /apps/catalog/{app_id}` routes to the browser apps router. Create `catalog_list.html` with a card grid showing all apps (installed + available on disk) with search filtering. Create `catalog_detail.html` with description, features, permissions, and conditional install/uninstall actions (only for owner role). Add `openCatalogTab()` to workspace.js that opens a dockview tab loading the catalog list via htmx. Add a "Browse Catalog" tree-leaf entry to `apps_explorer.html`. Add catalog CSS (`.catalog-grid`, `.catalog-card`, `.feature-list`, `.permission-badge`, `.category-pill`) to `style.css`.
  - Verify: `grep -q 'openCatalogTab' frontend/static/js/workspace.js && test -f backend/app/templates/browser/catalog_list.html && test -f backend/app/templates/browser/catalog_detail.html && grep -q 'Browse Catalog' backend/app/templates/browser/apps_explorer.html`
  - Done when: Catalog list and detail are browsable from the workspace sidebar; install/uninstall only rendered for owners; all 11 apps render correctly with existing manifest fields

## Files Likely Touched

- `backend/app/apps/manifest.py`
- `backend/app/apps/admin_router.py`
- `backend/app/browser/apps.py`
- `backend/app/templates/admin/apps/detail.html`
- `backend/app/templates/admin/apps/list.html`
- `backend/app/templates/browser/catalog_list.html`
- `backend/app/templates/browser/catalog_detail.html`
- `backend/app/templates/browser/apps_explorer.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/style.css`
