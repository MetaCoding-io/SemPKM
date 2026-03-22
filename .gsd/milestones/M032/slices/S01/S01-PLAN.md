# S01: GridStack Layout Engine + Block Registry

**Goal:** Replace the fixed CSS Grid dashboard layout system with a free-form GridStack.js 12-column canvas backed by a typed BlockRegistry, while auto-migrating all existing dashboards.

**Demo:** A user creates a dashboard in the builder by dragging blocks from a categorized palette onto a 12-column GridStack canvas, repositions and resizes them freely, saves the layout with `{x, y, w, h}` per block persisted in `blocks_json`, and sees it render correctly on the dashboard page. Existing dashboards auto-migrate from the 5 fixed CSS Grid layouts to GridStack positions on first load. All 6 existing block types work in the new layout.

## Must-Haves

- BlockRegistry declares all 6 existing block types with config schemas, icons, and categories
- Dashboard builder uses GridStack.js canvas with a block palette (drag-to-add)
- GridStack widget positions (`x, y, w, h`) are persisted per-block in `blocks_json`
- Dashboard page renders blocks using GridStack (read-only, no drag/resize)
- Layout auto-migration maps the 5 old CSS Grid layouts to GridStack `{x, y, w, h}` positions
- All 6 existing block types (view-embed, markdown, object-embed, create-form, sparql-result, divider) render correctly in GridStack widgets
- GridStack drag/drop events don't propagate to dockview panel management (`stopPropagation`)
- `layout: "gridstack"` is the new default; old layout values trigger auto-migration on read

## Proof Level

- This slice proves: integration (GridStack renders blocks, builder saves positions, page loads them)
- Real runtime required: yes (Docker stack for full integration; unit tests for registry/migration logic)
- Human/UAT required: yes (drag/drop/resize feel in dockview panels)

## Verification

- `cd backend && python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v` — unit tests pass for registry validation, config schema checks, and layout migration mapping
- `cd backend && python -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'bogus','config':{}})"` — must raise ValueError with descriptive message (failure-path check)
- Manual: open dashboard builder → drag a markdown block onto the canvas → resize it → save → open the dashboard page → block renders at the saved position with correct size
- Manual: edit an existing dashboard (created with old `grid-2x2` layout) → blocks appear at auto-migrated positions on the GridStack canvas

## Observability / Diagnostics

- Runtime signals: `logger.info("Auto-migrating dashboard %s from layout '%s' to gridstack", ...)` when migration runs
- Inspection surfaces: `GET /api/dashboard/{id}` returns `blocks` array with `x,y,w,h` fields after migration
- Failure visibility: `ValueError` exceptions from BlockRegistry for invalid block types/configs; migration logs old→new position mapping

## Integration Closure

- Upstream surfaces consumed: `dashboard/models.py`, `dashboard/service.py`, `dashboard/router.py`, `dashboard_builder.html`, `dashboard_page.html`, `workspace.js` (openDashboardTab/openDashboardBuilderTab), `workspace-layout.js` (special-panel URL resolution), `base.html` (script loading)
- New wiring introduced in this slice: `dashboard/registry.py` (BlockRegistry), `dashboard/migration.py` (layout auto-migrator), GridStack.js CDN in `base.html`, new builder/page templates using GridStack API
- What remains before the milestone is truly usable end-to-end: S02 adds new widget types (stat-card, chart, heading), S03 adds form-group multi-object blocks

## Tasks

- [x] **T01: BlockRegistry + model/service updates + layout migration utility** `est:2h`
  - Why: The backend foundation — defines the typed block registry, extends the model to support GridStack positions, updates service validation, and creates the auto-migration utility. All frontend work depends on this.
  - Files: `backend/app/dashboard/registry.py`, `backend/app/dashboard/models.py`, `backend/app/dashboard/service.py`, `backend/app/dashboard/migration.py`, `backend/tests/test_block_registry.py`, `backend/tests/test_layout_migration.py`
  - Do: Create BlockRegistry with typed declarations for all 6 block types (config schemas, icons, categories). Add "gridstack" to VALID_LAYOUTS. Update block schema to include optional `x,y,w,h` position fields. Update service validation to use registry. Create migration.py that maps each of the 5 old layouts to GridStack positions. Write pytest unit tests.
  - Verify: `cd backend && python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v` — all tests pass
  - Done when: BlockRegistry validates all 6 block types, service accepts GridStack positions in blocks, migration maps all 5 layouts correctly, tests prove it

- [x] **T02: GridStack-based dashboard builder with block palette** `est:2h`
  - Why: The builder UI — replaces the old block list + layout picker with a GridStack canvas and a categorized block palette. This is where users create and edit dashboard layouts.
  - Files: `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/base.html`, `backend/app/dashboard/router.py`, `frontend/static/css/workspace.css`
  - Do: Add GridStack.js + gridstack CSS CDN to base.html dev block. Rewrite dashboard_builder.html to use GridStack canvas with drag-from-palette block placement. Update router to pass BlockRegistry data to template context. Add `stopPropagation` on GridStack drag events to prevent dockview interference. Add CSS for builder palette and GridStack overrides.
  - Verify: Manual — open `/browser/dashboard/new` in a dockview tab, drag blocks from palette onto canvas, resize them, verify positions are visible and save button collects `{x,y,w,h}` from GridStack
  - Done when: Builder renders a 12-column GridStack canvas, blocks can be dragged from palette, repositioned, resized, and the save function serializes positions

- [x] **T03: GridStack dashboard page rendering + auto-migration on load** `est:1h30m`
  - Why: Closes the loop — the dashboard page renders saved GridStack layouts and auto-migrates old layouts on first access. Without this, saved dashboards can't be viewed.
  - Files: `backend/app/templates/browser/dashboard_page.html`, `backend/app/dashboard/router.py`, `frontend/static/css/workspace.css`
  - Do: Rewrite dashboard_page.html to render blocks in a static GridStack grid (no drag/resize) using positions from `blocks_json`. Update `render_dashboard` route to call auto-migration when `layout != "gridstack"` and persist the migrated result. Ensure all 6 existing block types render inside GridStack widgets (htmx load triggers, markdown, divider, etc.). Add CSS for read-only GridStack dashboard.
  - Verify: Manual — save a dashboard with 3 blocks at specific positions → open the dashboard page → blocks appear at correct GridStack positions. Create a dashboard with old `grid-2x2` layout via API → open it → blocks auto-migrate to GridStack positions.
  - Done when: Dashboard page renders GridStack layout with correct block positions, auto-migration converts all 5 old layouts on first load, all 6 block types render correctly inside GridStack widgets

## Files Likely Touched

- `backend/app/dashboard/registry.py` (NEW)
- `backend/app/dashboard/migration.py` (NEW)
- `backend/app/dashboard/models.py`
- `backend/app/dashboard/service.py`
- `backend/app/dashboard/router.py`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/dashboard_page.html`
- `backend/app/templates/base.html`
- `frontend/static/css/workspace.css`
- `backend/tests/test_block_registry.py` (NEW)
- `backend/tests/test_layout_migration.py` (NEW)
