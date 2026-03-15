---
id: S05
parent: M006
milestone: M006
provides:
  - inject_values_binding() for parameterized SPARQL with VALUES clause injection
  - Cross-view context propagation via dashboardContextChanged custom event
  - context_iri/context_var/dashboard_mode query params on table_view and cards_view endpoints
  - emits_context checkbox and listens_to_context text input in dashboard builder UI
  - Server-side context_iri forwarding in render_block for consumer view-embed blocks
requires:
  - slice: S03
    provides: DashboardSpec model, render_block(), dashboard_page.html template
affects:
  - S07
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_page.html
  - backend/app/templates/browser/table_view.html
  - backend/app/templates/browser/dashboard_builder.html
  - backend/tests/test_values_injection.py
  - backend/tests/test_dashboard.py
  - frontend/static/css/workspace.css
key_decisions:
  - D105: Single implicit IRI context variable per dashboard, not Retool-style named variables
  - D106: htmx:configRequest for context_iri URL injection, not hx-vals
  - D107: Context emission limited to table renderer for v1
  - D108: dashboard_mode query parameter for conditional row behavior
  - D109: dashboardContextChanged uses camelCase, not colon-namespaced (htmx parses colons as modifiers)
  - D110: Context params forwarded server-side in render_block, not purely client-side
patterns_established:
  - inject_values_binding(query, var_name, iri) pattern for parameterized SPARQL — reusable for any VALUES-based filtering
  - dashboardContextChanged event with {iri, dashboardId} detail for dashboard cross-view communication
  - htmx:configRequest on dashboard container for context param injection into slot re-fetches
  - dashboard_mode=1 query param for template-level behavior switching (context emit vs openTab)
observability_surfaces:
  - logger.debug("inject_values_binding: var=%s iri=%s") on successful injection
  - logger.warning("inject_values_binding: rejected invalid IRI/var_name") on validation failure
  - Browser devtools: body event listener for dashboardContextChanged
  - Network tab: context_iri= and context_var= params on re-fetch requests
  - DOM: .dashboard-container dataset.currentContextIri stores last-selected IRI
  - DOM: tr.context-selected class on active source row
drill_down_paths:
  - .gsd/milestones/M006/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M006/slices/S05/tasks/T03-SUMMARY.md
duration: 63m
verification_result: passed
completed_at: 2026-03-15
---

# S05: Interactive Dashboards — Cross-View Context

**Parameterized SPARQL VALUES injection + custom event wiring enables cross-view context filtering: click a row in one dashboard block and another block re-fetches with filtered results.**

## What Happened

**T01 — Parameterized SPARQL (18m):** Added `inject_values_binding(query, var_name, iri)` to ViewSpecService. It extracts the WHERE body via existing `_extract_where_body()`, validates the IRI via `_validate_iri()`, validates var_name with `^[A-Za-z_]\w*$` regex, prepends `VALUES ?{var_name} { <{iri}> }` to the WHERE body, and reassembles. Returns query unchanged for empty/invalid inputs (graceful degradation). Added `context_iri`, `context_var`, and `dashboard_mode` query params to both `table_view()` and `cards_view()`. Updated `render_block()` to append `dashboard_mode=1` to all view-embed block URLs and add `data-emits-context`, `data-listens-to-context`, `data-dashboard-id` attributes. Created 13 unit tests + 3 dashboard context attribute tests.

**T02 — Frontend Event Wiring (35m):** Wired `dashboardContextChanged` custom event chain. Dashboard page template: container gets `data-dashboard-id`, consumer slots get `hx-trigger="load, dashboardContextChanged from:body"`, inline script listens for `htmx:configRequest` to inject `context_iri`/`context_var` into slot re-fetches. Table view template: `dashboard_mode` triggers `emitDashboardContext(iri, el)` on row click instead of `openTab()`. Dashboard builder: added "Emits context" checkbox and "Context variable" text input to view-embed config. Updated `render_block()` to accept and forward `context_iri`/`context_var` server-side. Key deviation: event name changed from `sempkm:dashboard-context-changed` to `dashboardContextChanged` because htmx's hx-trigger parser uses colons as modifier separators.

**T03 — Edge Case Hardening (10m):** Added 12 edge case tests for VALUES injection (nested braces, subqueries, var_name rejection for dots/hyphens/spaces/SPARQL injection, long IRIs, unicode IRIs, no WHERE clause). Added 3 context config round-trip tests for dashboard service. Full suite: 631 passed, zero regressions.

## Verification

- `pytest tests/test_values_injection.py -v` — 25/25 passed (13 core + 12 edge cases)
- `pytest tests/test_dashboard.py -v` — 27/27 passed (19 existing + 5 context attrs + 3 round-trip)
- `pytest -x -q` — **631 passed**, 0 failures, 0 errors
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers
- Browser E2E: dashboard with sidebar-main layout, Projects Table (emits_context) and Notes Table (listens_to_context=project) — click project row → consumer block re-fetched with context_iri/context_var → filtered results displayed
- Invalid IRI graceful degradation: covered by unit tests (7 rejection cases), view renders unfiltered on bad input

## Requirements Advanced

- DASH-01 (Cross-view context filtering) — fully implemented: row click → event → re-fetch → VALUES injection → filtered results

## Requirements Validated

- None moved to validated (milestone-level validation deferred to S07 final integration)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Event name changed from `sempkm:dashboard-context-changed` (plan) to `dashboardContextChanged` — htmx hx-trigger parser uses colons as modifier separators, preventing colon-containing event names from being recognized (D109)
- Context params forwarded server-side in render_block rather than purely client-side via htmx:configRequest — nested htmx elements cause configRequest to fire twice, creating duplicate params (D110)
- htmx:configRequest scoped to `.dashboard-slot` elements only to avoid double-injection on inner view div requests

## Known Limitations

- Context emission limited to table renderer — card clicks trigger flip animation (conflict), graph nodes need Cytoscape event listeners (separate concern). Both deferred. (D107)
- Single implicit IRI context variable per dashboard — multiple named variables deferred. (D105)
- No visual indicator on consumer blocks that they are "listening" — user must configure via builder

## Follow-ups

- S07 needs to verify the full cross-view chain with real triplestore data as part of milestone completion
- Card and graph renderers could emit context events in a future milestone
- Multiple named context variables could enable more complex dashboard compositions

## Files Created/Modified

- `backend/app/views/service.py` — added `inject_values_binding()` function + `_validate_iri` import
- `backend/app/views/router.py` — added context_iri/context_var/dashboard_mode params to table_view and cards_view
- `backend/app/dashboard/router.py` — render_block adds dashboard_mode=1 and context data attributes, accepts/forwards context_iri/context_var
- `backend/app/templates/browser/dashboard_page.html` — data attributes, event wiring script (htmx:configRequest + dashboardContextChanged)
- `backend/app/templates/browser/table_view.html` — conditional dashboard_mode row click, emitDashboardContext function
- `backend/app/templates/browser/dashboard_builder.html` — emits_context checkbox + listens_to_context text input, checkbox handling
- `backend/tests/test_values_injection.py` — new file, 25 VALUES injection tests
- `backend/tests/test_dashboard.py` — extended with 8 context-related tests (attrs + passthrough + round-trip)
- `frontend/static/css/workspace.css` — .context-selected row highlight, .dashboard-row cursor style

## Forward Intelligence

### What the next slice should know
- The event contract is: `dashboardContextChanged` dispatched on `document.body` with `detail: {iri, dashboardId}`. Consumer blocks listen via `hx-trigger="load, dashboardContextChanged from:body"` and receive context via htmx:configRequest injection.
- `inject_values_binding()` is reusable for any VALUES-based SPARQL filtering — workflows (S06/S07) can use the same function for step-to-step context passing.

### What's fragile
- The htmx:configRequest listener targets `.dashboard-slot` elements via `evt.detail.elt.closest('.dashboard-slot')`. If dashboard HTML structure changes (e.g. removing the `.dashboard-slot` wrapper), context injection silently breaks.
- `_extract_where_body()` uses brace-counting to find the WHERE clause. Deeply nested SPARQL with unmatched braces in string literals could break it (mitigated by tests but not exhaustively).

### Authoritative diagnostics
- `grep -r "inject_values_binding" backend/` traces all injection points
- Browser devtools → Event Listeners on `body` → look for `dashboardContextChanged`
- Network tab: any request to `/browser/dashboard/*/render-block` with `context_iri=` confirms the chain is working
- `document.querySelector('.dashboard-container').dataset.currentContextIri` shows stored context in JS console

### What assumptions changed
- Plan assumed `sempkm:dashboard-context-changed` event name would work with htmx — colons are reserved in hx-trigger syntax, required camelCase rename
- Plan assumed client-side htmx:configRequest could handle all context injection — nested elements cause double-injection, required server-side forwarding in render_block
