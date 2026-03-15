---
id: T02
parent: S05
milestone: M006
provides:
  - dashboardContextChanged custom event for cross-view context propagation
  - emitDashboardContext() function for dashboard-mode table row clicks
  - htmx:configRequest listener injecting context_iri/context_var into slot re-fetches
  - emits_context checkbox and listens_to_context text input in dashboard builder
  - render_block context_iri forwarding to view URLs
key_files:
  - backend/app/templates/browser/dashboard_page.html
  - backend/app/templates/browser/table_view.html
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/dashboard/router.py
  - backend/tests/test_dashboard.py
  - frontend/static/css/workspace.css
key_decisions:
  - Event name uses camelCase (dashboardContextChanged) not colon-namespaced (sempkm:...) because htmx uses colons as modifier separators and fails to parse colon-containing event names in hx-trigger
  - Context params forwarded server-side in render_block (not client-side htmx:configRequest on inner div) because htmx:configRequest on nested elements causes duplicate params
  - htmx:configRequest scoped to .dashboard-slot elements only to avoid double-injection on inner view divs
patterns_established:
  - dashboardContextChanged event with {iri, dashboardId} detail for dashboard cross-view communication
  - htmx:configRequest on dashboard container for injecting context params into slot re-fetches
  - Checkbox config in builder collected via el.type === 'checkbox' ? el.checked : el.value pattern
observability_surfaces:
  - Browser devtools Event Listeners on body for dashboardContextChanged
  - Network tab shows context_iri= and context_var= params on consumer slot re-fetch and view requests
  - DOM: .dashboard-container dataset.currentContextIri stores last-selected IRI
  - DOM: tr.context-selected class on active source row
  - htmx:beforeRequest/afterRequest events for debugging request chain
duration: 35m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Frontend Event Wiring and Builder UI

**Wired dashboardContextChanged event chain connecting source block row clicks to consumer block re-fetches with context filtering, plus builder config fields for emits_context/listens_to_context**

## What Happened

1. Updated `dashboard_page.html`:
   - Added `data-dashboard-id` on `.dashboard-container`
   - Consumer slots get `hx-trigger="load, dashboardContextChanged from:body"` + `data-listens-to-context` + `data-dashboard-id`
   - Source slots get `data-emits-context="1"`
   - Inline script: `htmx:configRequest` listener injects `context_iri`/`context_var` into slot re-fetches, scoped to `.dashboard-slot` elements only. `dashboardContextChanged` listener updates `container.dataset.currentContextIri`.

2. Updated `table_view.html`:
   - When `dashboard_mode` is truthy, first-column links call `emitDashboardContext(iri, el)` instead of `openTab()`
   - `emitDashboardContext` walks DOM to find `[data-dashboard-id]`, dispatches `dashboardContextChanged` on body with `{iri, dashboardId}`, highlights selected row with `.context-selected` class

3. Updated `dashboard_builder.html`:
   - Added "Emits context" checkbox (`data-key="emits_context"`) and "Context variable" text input (`data-key="listens_to_context"`) to view-embed block config
   - Updated `collectBlocks()` config serialization to handle checkboxes via `el.type === 'checkbox' ? el.checked : el.value`

4. Updated `render_block()` in `dashboard/router.py`:
   - Added `context_iri` and `context_var` query params
   - Forwards context params into the view URL for consumer blocks (using `urllib.parse.quote`)

5. Added CSS `.context-selected` and `.dashboard-row` styles in `workspace.css`

6. Added 2 new tests: `test_view_embed_context_iri_passthrough` and `test_view_embed_context_iri_not_forwarded_without_listens`

## Verification

- `pytest tests/test_dashboard.py -v` — 24/24 passed (5 context attribute tests)
- `pytest tests/test_values_injection.py -v` — 13/13 passed
- `pytest -x -q` — 617 passed, 0 failures
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers
- Browser E2E: created dashboard with sidebar-main layout, Projects Table (emits_context) and Notes Table (listens_to_context=project), clicked project row → consumer block re-fetched with `context_iri` and `context_var` params, row highlight applied, clicking different row updated context

### Slice-level verification status (T02 is 2nd of 3 tasks):
- ✅ `test_values_injection.py` — 13/13 pass
- ✅ `test_dashboard.py` — 24/24 pass (including 5 context attribute tests)
- ✅ E2E browser test — full click-to-refetch chain verified
- ✅ 0 conflict markers
- ⬜ Diagnostic failure path (invalid IRI graceful degradation) — needs dedicated test in T03

## Diagnostics

- Event chain: row click → `emitDashboardContext()` → `dashboardContextChanged` on body → htmx re-fetches slot → `htmx:configRequest` injects context_iri/context_var → render_block forwards to view URL → VALUES injection on backend
- Inspect `document.querySelector('.dashboard-container').dataset.currentContextIri` for stored context
- Check `tr.context-selected` in DOM for active source row
- Network tab: look for `context_iri=` in render_block and view endpoint requests

## Deviations

- Changed event name from `sempkm:dashboard-context-changed` (plan) to `dashboardContextChanged` because htmx's hx-trigger parser uses colons as modifier separators and cannot parse colon-containing custom event names
- Context params forwarded server-side in render_block rather than purely client-side via htmx:configRequest, because nested htmx elements cause configRequest to fire twice (duplicate params)
- Scoped htmx:configRequest to `.dashboard-slot` elements only to prevent injection on inner view div requests

## Known Issues

- None

## Files Created/Modified

- `backend/app/templates/browser/dashboard_page.html` — data attributes on container/slots, event wiring script (htmx:configRequest + dashboardContextChanged listener)
- `backend/app/templates/browser/table_view.html` — conditional dashboard_mode row click behavior, emitDashboardContext function
- `backend/app/templates/browser/dashboard_builder.html` — emits_context checkbox + listens_to_context text input in view-embed config, checkbox handling in collectBlocks
- `backend/app/dashboard/router.py` — render_block accepts context_iri/context_var params, forwards to view URL, added Query import and quote import
- `backend/tests/test_dashboard.py` — 2 new context_iri passthrough tests, updated existing tests for new render_block signature
- `frontend/static/css/workspace.css` — .context-selected row highlight, .dashboard-row cursor style
- `.gsd/milestones/M006/slices/S05/tasks/T02-PLAN.md` — added Observability Impact section
