---
id: T01
parent: S04
milestone: M006
provides:
  - Dashboard builder form (create and edit modes)
  - openDashboardBuilderTab() JS function
  - dashboard-builder specialType routing
  - Builder route tests
key_files:
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_builder.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/tests/test_dashboard_builder.py
key_decisions:
  - Builder uses inline script in template (same pattern as other partials) rather than a separate JS file
  - Client-side validation for empty name before fetch; server-side validation still applies
  - View-embed spec list fetched lazily from /browser/views/available and cached in-memory
patterns_established:
  - dashboard-builder specialType in workspace-layout.js with dashboardId param routing
  - Block row dynamic creation with type-specific config field switching via onchange
observability_surfaces:
  - "#builder-error" element shows last save error message
  - fetch() errors logged to browser console with "Dashboard save error:" prefix
  - "#builder-saving" indicator visible during save operation
  - Block count inspectable via ".block-row" selector count
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Dashboard builder form — routes, template, and tab integration

**Added form-based dashboard builder with create/edit modes, layout picker, dynamic block configuration, and fetch()-based save that opens the rendered dashboard on success.**

## What Happened

Added two new browser routes to `dashboard/router.py`: `GET /browser/dashboard/new` (create mode) and `GET /browser/dashboard/{id}/edit` (edit mode). Both render `dashboard_builder.html` with `LAYOUT_DEFINITIONS` and `valid_block_types` in context.

The builder template includes: name input with required validation, description textarea, a radio-button layout picker showing all 5 layouts with their slot names, a dynamic blocks section with add/remove, and save/cancel actions. Each block row has a type select and slot select. Type-specific config fields appear/hide via JS onchange — markdown shows a content textarea, view-embed shows spec_iri select (lazily fetched from `/browser/views/available`) and renderer_type select, create-form and object-embed show IRI text inputs, sparql-result shows query textarea + label input, divider shows nothing.

Save uses `fetch()` to POST (create) or PATCH (edit) the JSON API. On success, `openDashboardTab()` opens the rendered dashboard and the builder tab closes. On failure, the error message from the API response displays in a `#builder-error` element.

Added `openDashboardBuilderTab(dashboardId)` to workspace.js following the existing `openDashboardTab()` pattern. Added `dashboard-builder` specialType routing in workspace-layout.js that routes to `/browser/dashboard/new` or `/browser/dashboard/{id}/edit`.

Builder CSS follows existing `.form-field` / `.form-actions` patterns with layout picker grid, block row cards, and proper Lucide SVG sizing with `flex-shrink: 0`.

## Verification

- `cd backend && python -m pytest tests/test_dashboard_builder.py -v` — 6/6 tests pass
- `cd backend && python -m pytest tests/test_dashboard_builder.py tests/test_dashboard.py -v` — 25/25 pass
- Docker browser: opened builder via `openDashboardBuilderTab()`, filled name "Test Dashboard", selected sidebar-main layout, added markdown block with content, saved → dashboard tab opened with rendered content
- Docker browser: opened edit mode via `openDashboardBuilderTab(id)` → form pre-populated with name, description, layout, and blocks from existing dashboard
- Docker browser: submitted with empty name → "Name is required." error displayed inline
- Zero conflict markers: `grep -rn "^<<<<<<< " backend/ frontend/` returns empty

### Slice-level verification (partial — T01 of 2):
- ✅ `backend/tests/test_dashboard_builder.py` — unit tests pass (6/6)
- ✅ Docker manual check: created dashboard through builder, verified it renders
- ✅ Zero conflict markers
- ✅ Failure-path: empty name shows error inline
- ✅ Diagnostic: `GET /api/dashboard` returns created dashboard
- ⬜ Explorer section (T02)
- ⬜ Dashboard appears in explorer after create (T02)

## Diagnostics

- `#builder-error` element: inspect `.textContent` for last save error
- Browser console: search for "Dashboard save error:" for fetch failures
- `GET /api/dashboard` returns all dashboards with IDs for inspection
- `.block-row` count in DOM = number of configured blocks
- `input[name=layout]:checked` value = selected layout

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/router.py` — added `GET /browser/dashboard/new` and `GET /browser/dashboard/{id}/edit` routes
- `backend/app/templates/browser/dashboard_builder.html` — new builder form template with layout picker, dynamic blocks, fetch save
- `frontend/static/js/workspace.js` — added `openDashboardBuilderTab()` function
- `frontend/static/js/workspace-layout.js` — added `dashboard-builder` specialType routing
- `frontend/static/css/workspace.css` — added builder CSS (layout picker, block rows, config fields, error display)
- `backend/tests/test_dashboard_builder.py` — new test file with 6 route-level tests
- `.gsd/milestones/M006/slices/S04/S04-PLAN.md` — added failure-path verification step
- `.gsd/milestones/M006/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
