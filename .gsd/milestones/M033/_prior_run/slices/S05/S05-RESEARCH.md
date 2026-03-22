# S05 Research: App Catalog Pages

**Slice:** S05 — App Catalog Pages
**Risk:** Low
**Depth:** Light — well-understood pattern using existing infrastructure

## Summary

This slice adds a browsable App Catalog to the workspace — a grid of all 11 apps (installed or not) with a detail page showing description, permissions, screenshots, and install/uninstall buttons. The entire feature follows established patterns: dockview special-panel tabs, htmx fragment loading, Jinja2 templates with Lucide icons, and the existing `docs-page` card grid CSS.

## Recommendation

Build it exactly like the Docs tab: a special-panel type that loads an htmx fragment from a new `catalog.py` browser sub-router. The catalog list is a card grid (reuse `docs-cards` pattern); the detail page is a full-panel view loaded via htmx navigation within the same tab. Install/uninstall actions use htmx POST to new browser-level endpoints (not admin-only — the catalog should be accessible to all users, with install/uninstall restricted to owners via dependency injection).

## Implementation Landscape

### Files to Create

| File | Purpose |
|---|---|
| `backend/app/browser/catalog.py` | Browser sub-router: `GET /catalog` (list), `GET /catalog/{app_id}` (detail), `POST /catalog/{app_id}/install`, `POST /catalog/{app_id}/uninstall` |
| `backend/app/templates/browser/catalog_page.html` | Catalog grid — card per app with icon, name, description, status badge |
| `backend/app/templates/browser/catalog_detail.html` | Detail page — back button, description, version, author, permissions, model deps, screenshots section, install/uninstall button |

### Files to Modify

| File | Change |
|---|---|
| `backend/app/browser/router.py` | Import and include `catalog_router` (before `objects_router` — catch-all path concern) |
| `frontend/static/js/workspace.js` | Add `openCatalogTab()` function following `openDocsTab()` pattern |
| `frontend/static/js/workspace-layout.js` | Add `specialType === 'catalog'` case to route to `/browser/catalog`, and `specialType === 'catalog-detail'` to route to `/browser/catalog/{appId}` |
| `backend/app/templates/browser/workspace.html` | Add "App Catalog" tree-leaf entry in the APPS explorer section body, OR add a static entry above the htmx-loaded app pages |
| `frontend/static/css/workspace.css` | Catalog-specific CSS (can largely reuse `.docs-*` patterns; add `.catalog-*` variants) |

### Existing Patterns to Follow

**Dockview special-panel tab** (lines 710-830 of `workspace.js`):
```javascript
function openCatalogTab() {
  var tabKey = 'special:catalog';
  // ... exact same pattern as openDocsTab()
  dv.api.addPanel({
    id: tabKey,
    component: 'special-panel',
    params: { specialType: 'catalog', isView: false, isSpecial: true },
    title: 'App Catalog'
  });
}
```

**workspace-layout.js special-panel routing** (line 210+):
- Default `url = '/browser/' + st` already works — `specialType: 'catalog'` → `/browser/catalog`
- Detail navigation within the catalog uses htmx `hx-target` on the panel container, same as docs viewer's back/chapter navigation

**Admin apps list** (`admin_router.py` lines 63-108):
- Already has logic to scan `apps_dir` for available (not installed) apps
- Already parses manifest YAML for display
- Catalog router can extract this into a shared helper or duplicate it (it's ~20 lines)

**Docs page template** (`docs_page.html`):
- Card grid pattern: `.docs-page` → `.docs-section` → `.docs-cards` → `.docs-card`
- Each card has icon, title, description, action button
- Catalog cards follow same structure with status badge (installed/available/running)

### App Discovery Logic

The catalog must show ALL apps, not just installed ones. Two data sources:

1. **Installed apps**: `app_manager.registry.list_apps()` → manifests in memory
2. **Available (not installed) apps**: Scan `app_manager._apps_dir` for directories with `manifest.yaml`, filter out installed ones

The admin router already does this (lines 82-108 of `admin_router.py`). Extract into a helper or replicate.

**Filter**: Exclude `test-app` from the catalog — it's a development/testing app. Check for `appId == "test-app"` or add a `catalog: false` flag to manifest schema (simpler to just hardcode the exclusion for v1).

### Manifest Fields Available for Detail Page

From `AppManifestSchema`:
- `appId`, `name`, `version`, `description`, `author.name`, `author.url`, `license`
- `dependencies.models[]` — model name + version range
- `dependencies.platform` — platform version requirement
- `permissions` — `commands[]`, `sparql.read`, `network[]`, `backgroundTasks`, `settings`
- `tasks[]` — background task descriptions
- `ui.pages[]` — navigable pages with labels and icons
- `settings[]` — configurable settings (labels only, not values)

### Screenshots

No per-app screenshots exist on disk. Two options:
1. **Create placeholder screenshots** — simple colored placeholder images per app
2. **Skip screenshots for v1** — show the detail page without a screenshots section; add screenshot capture in a follow-up

The roadmap says "Pre-captured and bundled" but no capture infrastructure exists for per-app screenshots (only platform-level screenshots in `docs/screenshots/`). The most pragmatic approach: create the detail page with a screenshots section that renders if screenshots exist, but don't block the slice on capturing screenshots for all 11 apps. A follow-up task or manual capture can populate them.

**Screenshot location**: `apps/{app_id}/screenshots/` directory, served via a new static route or the existing app-static serving. PNG files named `01.png`, `02.png`, etc.

### Install/Uninstall from Catalog

The admin router's install endpoint (`POST /admin/apps/install`) requires `owner` role and takes a filesystem path. The catalog should offer:

1. `POST /browser/catalog/{app_id}/install` — derives path from `apps_dir / app_id`, calls `app_manager.install()`. Requires `owner` role (same security as admin).
2. `POST /browser/catalog/{app_id}/uninstall` — calls `app_manager.uninstall()`. Requires `owner` role.

These return htmx fragments (re-render the detail page with updated status) instead of redirecting to admin.

### Explorer Entry

Two options for the sidebar:
1. **Static entry in workspace.html** — a hardcoded "App Catalog" tree-leaf before the htmx-loaded apps list, with `onclick="openCatalogTab()"`
2. **Separate section** — unlikely needed; the APPS section already exists

Option 1 is simpler and consistent — the catalog is a permanent navigation target, not dynamically loaded.

### Navigation Flow

1. User clicks "App Catalog" in APPS explorer section → `openCatalogTab()` → dockview panel → htmx loads `/browser/catalog`
2. Catalog page shows grid of app cards with status badges
3. User clicks an app card → htmx replaces panel content with `/browser/catalog/{app_id}` (detail view)
4. Detail page has "Back to Catalog" button (htmx back to `/browser/catalog`)
5. Detail page has Install/Uninstall button (htmx POST, re-renders detail with new status)

### Natural Task Decomposition

1. **T01: Backend catalog router + templates** — `catalog.py` with list/detail/install/uninstall endpoints, `catalog_page.html` and `catalog_detail.html` templates
2. **T02: Frontend integration** — `openCatalogTab()` in workspace.js, `specialType` routing in workspace-layout.js, explorer entry in workspace.html, CSS in workspace.css
3. **T03: Verification** — manual verification against running Docker stack (or unit tests for the router)

Given the low complexity, T01 and T02 could be a single task. The planner should decide based on context window budget.

### Constraints

- `catalog_router` must be included in `browser/router.py` BEFORE `objects_router` — the objects router has catch-all `:path` patterns that would consume `/catalog` URLs
- Install/uninstall require `owner` role — non-owners see the catalog as read-only (no install button)
- The `test-app` should be excluded from the catalog listing
- Screenshots section should gracefully handle missing screenshots (show nothing, not a broken grid)
- Lucide icons: follow CLAUDE.md rules — size via CSS, `flex-shrink: 0`, `stroke: currentColor`
