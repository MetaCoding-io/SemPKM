# S06 Research: App Catalog Pages

## Summary

Straightforward UI work: extend `AppManifestSchema` with optional catalog metadata fields, redesign the admin app detail template from monitoring-focused to catalog-showcase, add a catalog list+detail page accessible from the workspace sidebar, and wire a workspace-side route. All patterns are established in the codebase. No new libraries, no risky integrations.

## Requirement Coverage

Requirements CAT-01 (rich app detail pages) and CAT-02 (browsable catalog from admin + workspace) are defined in the M033 roadmap but not yet in REQUIREMENTS.md. This slice delivers both.

## Recommendation

Light research confirmed this is standard template + schema extension work. Three tasks:

1. **Schema extension** — add optional `category`, `features`, `readme` fields to `AppManifestSchema`
2. **Admin catalog redesign** — transform `detail.html` from ops-monitoring into a catalog showcase with description, features, permissions, and install/uninstall; keep operational sections behind a collapsible `<details>` for owners
3. **Workspace catalog** — new route + template for browsing apps from within the workspace, plus sidebar entry

## Implementation Landscape

### Files to Change

**Backend:**
- `backend/app/apps/manifest.py` — add optional fields to `AppManifestSchema`: `category: str = ""`, `features: list[str] = []`, `readme: str = ""`
- `backend/app/apps/admin_router.py` — minor: pass any new manifest fields through to template context (they're already available via `manifest` object, so this may be zero changes)
- `backend/app/browser/apps.py` — add new route `GET /apps/catalog` (catalog list) and `GET /apps/catalog/{app_id}` (catalog detail) for workspace-side browsing
- `backend/app/main.py` — no changes needed; `apps_router` is already mounted under `/browser` prefix

**Templates:**
- `backend/app/templates/admin/apps/detail.html` — redesign: add features list, prominent description, permissions summary at top; push PID/uptime/logs into a collapsible "Operations" section
- `backend/app/templates/admin/apps/list.html` — minor: add category badges if populated
- `backend/app/templates/browser/catalog_list.html` — NEW: workspace catalog grid showing all apps (installed + available) with search/filter
- `backend/app/templates/browser/catalog_detail.html` — NEW: workspace catalog detail showing description, features, permissions, install/uninstall actions
- `backend/app/templates/browser/workspace.html` — update APPS explorer section or add a "Browse Catalog" link

**Frontend:**
- `frontend/static/js/workspace.js` — add `openCatalogTab()` function + wire it from explorer or command palette
- `frontend/static/css/style.css` — catalog-specific styles (feature list, permission badges, category pills)

### Existing Patterns to Follow

1. **Admin page pattern:** All admin pages extend `base.html`, use `.admin-page` wrapper, `.detail-section` for groupings, `.dashboard-cards` for card grids, `.stats-bar` for stat boxes, `.version-pill` and `.status-badge` for inline indicators. CSS is in `style.css` lines 1178-1460+.

2. **Workspace tab pattern:** `openAppPageTab(appId, pageId, label)` in `workspace.js:775` creates dockview tabs with `specialType: 'app-page'`. The catalog could use a similar `specialType: 'catalog'` or open as a standalone page tab.

3. **Explorer sidebar pattern:** The APPS section in `workspace.html:128-142` loads content via `hx-get="/browser/apps/explorer"`. The catalog entry could be either (a) a static link in the explorer section body, or (b) a tree-leaf entry that opens a catalog tab.

4. **Manifest schema:** `AppManifestSchema` in `manifest.py` uses Pydantic BaseModel with camelCase field names matching YAML keys. New optional fields with defaults won't break existing manifests (additive, backward-compatible).

5. **Router mounting:** `apps_router` lives in `backend/app/browser/apps.py` and is mounted at `/browser/apps/` via the browser router coordinator (`backend/app/browser/router.py:32`). New catalog routes go on this same router.

### Key Constraints

- **All 11 apps lack catalog metadata.** `features`, `category`, and `readme` fields don't exist in any manifest today. The catalog must look good with only the fields that exist: `name`, `description`, `version`, `author`, `permissions`, `dependencies`. Extended metadata is a progressive enhancement.
- **Admin detail page serves dual purpose.** It's both operational monitoring (PID, uptime, logs, task history) and now needs to be app-showcase. Keep both — catalog info at top, ops info collapsed below.
- **Workspace catalog should NOT require owner role.** Admin pages require `require_role("owner")`. The workspace catalog should be accessible to all authenticated users (read-only browsing). Install/uninstall actions should only appear for owners.
- **htmx rendering:** The admin templates use htmx block rendering (`block_name="content"` for htmx requests). The workspace catalog templates need to work both as dockview panel content and as htmx partials.

### Task Decomposition Suggestion

**T01: Schema + Admin Catalog Redesign** (~1hr)
- Add `category`, `features`, `readme` to `AppManifestSchema`
- Redesign `admin/apps/detail.html`: description + features + permissions at top, ops collapsed
- Update `admin/apps/list.html` with category badges
- Verify: existing apps still parse, admin pages render correctly

**T02: Workspace Catalog Route + Templates** (~1.5hr)
- Add `GET /browser/apps/catalog` and `GET /browser/apps/catalog/{app_id}` routes
- Create `catalog_list.html` and `catalog_detail.html` templates
- Add `openCatalogTab()` to workspace.js
- Add catalog entry point in workspace sidebar (tree-leaf in APPS section or dedicated link)
- Add CSS for catalog grid, feature lists, permission badges
- Verify: catalog browsable from workspace, install/uninstall only for owners

**T03: Verification** (~30min)
- Browser verification: navigate admin app list → detail, workspace catalog list → detail
- Check all 11 apps render correctly in catalog with existing manifest fields
- Verify install/uninstall actions work from both admin and workspace catalog
