---
estimated_steps: 8
estimated_files: 7
---

# T01: Dashboard builder form — routes, template, and tab integration

**Slice:** S04 — Dashboard Builder UI & Explorer Integration
**Milestone:** M006

## Description

Add the form-based dashboard builder UI. Two new routes serve the builder template in create mode (`GET /browser/dashboard/new`) and edit mode (`GET /browser/dashboard/{id}/edit`). The template collects dashboard name, description, layout selection, and a dynamic list of block configurations. Submission goes via `fetch()` to the existing JSON API endpoints. On success, the builder opens the rendered dashboard tab and closes itself.

The builder opens as a workspace tab via a new `openDashboardBuilderTab()` JS function and a `dashboard-builder` specialType in workspace-layout.js.

## Steps

1. Add `GET /browser/dashboard/new` route to `dashboard/router.py` — renders `dashboard_builder.html` with empty fields and `LAYOUT_DEFINITIONS` context. No auth beyond `get_current_user`.
2. Add `GET /browser/dashboard/{id}/edit` route — loads dashboard via `DashboardService.get()`, renders same template pre-populated with existing name, description, layout, and blocks. 404 if not found.
3. Create `dashboard_builder.html` template:
   - Name input + description textarea
   - Layout picker: radio buttons for each layout in `LAYOUT_DEFINITIONS`, showing slot names as preview
   - Blocks section: repeating rows, each with type `<select>`, slot `<select>` (options from selected layout), and type-specific config fields
   - Type-specific fields shown/hidden via JS `onchange` on type select: view-embed shows spec_iri + renderer_type selects (populated via fetch to `/browser/views/available`), markdown shows textarea, create-form shows target_class select, object-embed shows text input, sparql-result shows textarea, divider shows nothing
   - Add Block / Remove Block buttons for dynamic rows
   - Save button with `fetch()` handler: builds JSON payload from form DOM, POSTs or PATCHes, opens dashboard tab on success, shows error on failure
   - Cancel button closes the builder tab
4. Add `openDashboardBuilderTab(dashboardId)` to workspace.js — `dashboardId` is optional (null/undefined for create). Tab key: `dashboard-builder:{id}` or `dashboard-builder:new`.
5. Add `dashboard-builder` specialType handling in workspace-layout.js — routes to `/browser/dashboard/new` for create or `/browser/dashboard/{id}/edit` for edit.
6. Add builder CSS to workspace.css — layout picker grid, block row styling, type-specific field containers. Follow existing `.form-field` / `.form-actions` patterns. Lucide SVGs in buttons need `flex-shrink: 0`.
7. Write `backend/tests/test_dashboard_builder.py` — test new route returns 200, edit route returns 200 with populated data, edit route returns 404 for missing dashboard.
8. Call `lucide.createIcons()` after dynamically adding block rows.

## Must-Haves

- [ ] Builder renders in create mode with empty fields
- [ ] Builder renders in edit mode with pre-populated fields from existing dashboard
- [ ] Layout picker updates available slot options in block rows when changed
- [ ] Block type selector shows/hides type-specific config fields
- [ ] View-embed config fetches available views for dropdown
- [ ] Save via `fetch()` to JSON API works for both create and edit
- [ ] On save success: opens dashboard tab, closes builder tab
- [ ] On save failure: displays error message from API response
- [ ] Unit tests for builder routes pass

## Verification

- `cd backend && python -m pytest tests/test_dashboard_builder.py -v` — all tests pass
- Docker: open builder via JS console `openDashboardBuilderTab()`, fill in name + layout + blocks, save — dashboard renders

## Inputs

- `backend/app/dashboard/router.py` — existing routes, `LAYOUT_DEFINITIONS`, service wiring
- `backend/app/dashboard/service.py` — `DashboardService.create()`, `.get()`, `.update()`
- `backend/app/dashboard/models.py` — `VALID_LAYOUTS`, `VALID_BLOCK_TYPES`
- `frontend/static/js/workspace.js` — `openDashboardTab()` pattern
- `frontend/static/js/workspace-layout.js` — `special-panel` handler pattern
- `backend/app/templates/browser/_vfs_settings.html` — reference for dynamic config fields

## Observability Impact

- **New signals:** Builder form validation errors shown inline; `fetch()` errors logged to console and displayed to user as error message below save button
- **Inspection:** Builder form state readable via DOM (input values, selected layout radio, block rows); fetch() calls visible in browser Network tab targeting `/api/dashboard`
- **Failure state:** API 400/422 responses surface `detail` field as user-visible error text; builder tab stays open on failure so user can correct and retry
- **Future agent:** Check `#builder-error` element for last error message; count `.block-row` elements for block count; read `input[name=layout]:checked` for selected layout

## Expected Output

- `backend/app/templates/browser/dashboard_builder.html` — new template
- `backend/app/dashboard/router.py` — two new routes added
- `frontend/static/js/workspace.js` — `openDashboardBuilderTab()` function added
- `frontend/static/js/workspace-layout.js` — `dashboard-builder` specialType routing added
- `frontend/static/css/workspace.css` — builder CSS added
- `backend/tests/test_dashboard_builder.py` — new test file
