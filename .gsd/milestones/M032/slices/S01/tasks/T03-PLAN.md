---
estimated_steps: 4
estimated_files: 3
skills_used:
  - frontend-design
  - review
---

# T03: GridStack dashboard page rendering + auto-migration on load

**Slice:** S01 — GridStack Layout Engine + Block Registry
**Milestone:** M032

## Description

Close the loop by making the dashboard page render blocks at their GridStack positions and auto-migrating old layouts on first access. Without this, saved dashboards can't be viewed. The dashboard page renders a static (non-draggable) GridStack grid — users view content but don't edit layout here.

This task depends on T01 (migration utility, model changes) and T02 (GridStack CDN already added).

## Steps

1. **Update `render_dashboard` route in `backend/app/dashboard/router.py`** — Before rendering, check if `dashboard.layout != "gridstack"`. If so:
   - Call `migrate_layout_to_gridstack(dashboard.layout, dashboard.blocks)` to get blocks with `{x, y, w, h}` positions
   - Persist the migrated blocks and `layout="gridstack"` back to the database via `service.update()` (requires the current user's ID for auth)
   - Log the migration: `logger.info("Auto-migrated dashboard %s from layout '%s' to gridstack", dashboard.id, dashboard.layout)`
   - Use the migrated blocks for rendering
   
   Update the template context: replace the old `layout` dict and `block_slots` with a flat `blocks` list where each block has `x, y, w, h, type, config, index`. Remove the `LAYOUT_DEFINITIONS` dependency from `render_dashboard`.

2. **Rewrite `backend/app/templates/browser/dashboard_page.html`** — Replace the CSS Grid container with a static GridStack grid:
   - Initialize GridStack in static mode (`staticGrid: true`) so widgets can't be dragged/resized by viewers
   - For each block in the `blocks` context, create a `<div class="grid-stack-item" gs-x="..." gs-y="..." gs-w="..." gs-h="...">` with an inner `<div class="grid-stack-item-content">` containing the htmx `hx-get` trigger for the block's render endpoint
   - Preserve the existing block rendering URL: `hx-get="/browser/dashboard/{{ dashboard_id }}/block/{{ block.index }}"`
   - Preserve the dashboard header (title + edit button)
   - Preserve the context-passing mechanism (`dashboardContextChanged` event, `data-listens-to-context`, `htmx:configRequest` handler)
   - Preserve the `embed=1` wrapper for canvas embed mode
   
   The GridStack instance should use `cellHeight: 80` (or similar) for consistent widget sizing, `column: 12` for the standard grid, and `animate: true` for smooth appearance.

3. **Add read-only dashboard CSS to `frontend/static/css/workspace.css`** — Style the dashboard page's static GridStack:
   - `.dashboard-page .grid-stack` — full height, overflow auto
   - `.dashboard-page .grid-stack-item-content` — background, border, border-radius matching the app theme
   - `.dashboard-block-loading` inside GridStack items — centered spinner/text
   - Ensure blocks with `overflow:auto` work for scrollable content (view-embed tables, etc.)

4. **Verify all 6 block types render inside GridStack widgets** — The existing `render_block` route returns HTML for each block type. Verify that:
   - `view-embed`: htmx loads the view inside the widget (the `style="height:..."` on the inner div should still work, or be replaced by GridStack's cell height)
   - `markdown`: inline HTML renders correctly
   - `create-form`: htmx loads the SHACL form
   - `object-embed`: htmx loads the object detail
   - `sparql-result`: the query/label display renders
   - `divider`: `<hr>` renders inside the widget
   
   The key concern is that htmx `hx-trigger="load"` fires correctly inside GridStack widgets (it should, since the elements are in the DOM). If any block type needs CSS adjustments for GridStack widget sizing, add them.

## Must-Haves

- [ ] Dashboard page renders blocks at correct GridStack positions (x, y, w, h)
- [ ] GridStack is in static mode (no drag/resize on the view page)
- [ ] Auto-migration runs and persists on first access for old-layout dashboards
- [ ] All 6 existing block types render correctly inside GridStack widgets
- [ ] Cross-block context passing (dashboardContextChanged) still works
- [ ] Dashboard embed mode (`embed=1`) still works for canvas embeds
- [ ] Migration is logged for observability

## Verification

- Manual: create a dashboard with 3 blocks at specific GridStack positions (via builder from T02) → open the dashboard page → blocks appear at correct positions
- Manual: use the API to create a dashboard with `layout: "grid-2x2"` and 4 blocks with slot assignments → open it → blocks auto-migrate to GridStack positions → re-fetch via API confirms `layout: "gridstack"` and blocks have `x,y,w,h`
- Manual: verify each block type: add one of each type in the builder → save → open dashboard page → all 6 render correctly
- `cd backend && python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v` — regression check, still passes

## Observability Impact

- **New runtime signal:** `logger.info("Auto-migrated dashboard %s from layout '%s' to gridstack", dashboard.id, old_layout)` emitted on first access of a legacy-layout dashboard — confirms migration ran.
- **Inspection surface:** After migration, `GET /api/dashboard/{id}` returns `layout: "gridstack"` and every block in the `blocks` array has `x, y, w, h` fields — verifiable via API or DB inspection.
- **Failure visibility:** If `migrate_layout_to_gridstack()` raises `ValueError` (unknown layout), the render route returns 500 — visible in server logs. If `service.update()` fails during migration persistence, the error propagates and is logged.
- **Template diagnostic:** The dashboard page's GridStack `<div>` elements carry `gs-x`, `gs-y`, `gs-w`, `gs-h` attributes readable in DevTools — confirms positions rendered correctly.

## Inputs

- `backend/app/dashboard/migration.py` — migration utility from T01
- `backend/app/dashboard/registry.py` — BlockRegistry from T01
- `backend/app/dashboard/router.py` — updated with registry context from T02
- `backend/app/templates/browser/dashboard_page.html` — current CSS Grid template to rewrite
- `backend/app/templates/base.html` — already has GridStack CDN from T02
- `frontend/static/css/workspace.css` — extended with builder styles from T02

## Expected Output

- `backend/app/templates/browser/dashboard_page.html` — rewritten with static GridStack rendering
- `backend/app/dashboard/router.py` — render_dashboard updated with auto-migration and GridStack context
- `frontend/static/css/workspace.css` — extended with read-only dashboard GridStack styles
