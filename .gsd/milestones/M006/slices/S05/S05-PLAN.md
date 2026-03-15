# S05: Interactive Dashboards — Cross-View Context

**Goal:** Selecting a row in one view-embed block filters another view-embed block in the same dashboard via parameterized SPARQL with VALUES binding. Dashboard context variables flow via custom events and htmx re-fetch.

**Demo:** User opens a dashboard with two view-embed blocks (e.g. "Projects" table and "Notes" table). Clicking a project row in the first block filters the second block to show only notes related to that project. Clicking a different project re-filters. The flow is: table row click → `sempkm:dashboard-context-changed` custom event → htmx re-fetch with `?context_iri=<selected>` → backend injects `VALUES ?project { <iri> }` into the consumer view's SPARQL → filtered results render.

## Must-Haves

- `inject_values_binding(query, var_name, iri)` function in ViewSpecService that injects a `VALUES ?var { <iri> }` clause into a SPARQL WHERE body
- IRI validation via `_validate_iri()` before any VALUES injection — no string interpolation
- `context_iri` query parameter accepted by `table_view` and `cards_view` endpoints
- `emits_context` (bool) and `listens_to_context` (str) config keys on view-embed blocks
- `sempkm:dashboard-context-changed` custom event carrying `{ iri, dashboardId }`
- Table rows in dashboard-mode emit context event instead of opening tabs
- Consumer blocks re-fetch via htmx with `context_iri` injected into the request URL
- Dashboard-scoped events: consumer blocks only react to their own dashboard's context changes
- Dashboard builder UI exposes emits_context checkbox and listens_to_context text input for view-embed blocks

## Proof Level

- This slice proves: integration (event → re-fetch → parameterized SPARQL → filtered render)
- Real runtime required: yes (needs triplestore + real view specs)
- Human/UAT required: no (E2E browser test covers the chain)

## Verification

- `backend/tests/test_values_injection.py` — unit tests for `inject_values_binding()`: correct VALUES placement, IRI validation rejection, no-op for empty context, variable naming
- `backend/tests/test_dashboard.py` — extended with tests for context_iri passthrough in block rendering
- E2E browser test: create dashboard with two view-embed blocks, configure emits_context on source and listens_to_context on consumer, click a row, verify consumer block re-renders with filtered results
- 0 conflict markers: `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` returns empty
- Diagnostic failure path: pass an invalid IRI (e.g. `context_iri=not<valid>`) to a view endpoint with `context_var=x` — response must render unfiltered (graceful degradation), and `docker compose logs backend | grep "inject_values_binding"` shows a WARNING-level log line with the rejected IRI

## Observability / Diagnostics

- Runtime signals: `logger.debug("inject_values_binding: var=%s iri=%s", ...)` in ViewSpecService when VALUES clause injected; `logger.warning` when `_validate_iri()` rejects a context_iri
- Inspection surfaces: browser devtools custom event listener on `sempkm:dashboard-context-changed`; network tab shows `?context_iri=` param on re-fetch requests
- Failure visibility: if context_iri fails validation, view renders unfiltered (graceful degradation, not error)
- Redaction constraints: none (IRIs are not secrets)

## Integration Closure

- Upstream surfaces consumed: `DashboardSpec` model + `render_block()` from S03; `_extract_where_body()` and `execute_table_query()` from ViewSpecService; `_validate_iri()` from `browser/_helpers.py`; `table_view`/`cards_view` endpoints from views/router.py
- New wiring introduced: `sempkm:dashboard-context-changed` event system; `htmx:configRequest` listener for context_iri URL injection; `dashboard_mode` query param on view endpoints
- What remains before the milestone is truly usable end-to-end: S07 (workflow builder UI + final integration verification)

## Tasks

- [x] **T01: Parameterized SPARQL with VALUES injection** `est:1h`
  - Why: Foundation for cross-view filtering. Without safe VALUES injection, consumer blocks can't receive filtered queries.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/app/dashboard/router.py`, `backend/tests/test_values_injection.py`, `backend/tests/test_dashboard.py`
  - Do: Add `inject_values_binding(query, var_name, iri)` to ViewSpecService that extracts WHERE body, prepends `VALUES ?{var_name} { <{iri}> }`, and reassembles. Gate with `_validate_iri()`. Add `context_iri` and `context_var` query params to `table_view` and `cards_view` — when both present and valid, call `inject_values_binding` on the spec's query before execution. Update `render_block()` to pass `context_iri` through to view-embed block URLs when block config has `listens_to_context`. Add `dashboard_mode` query param to view endpoints so templates can detect dashboard embedding.
  - Verify: `cd backend && .venv/bin/pytest tests/test_values_injection.py tests/test_dashboard.py -v`
  - Done when: `inject_values_binding` correctly injects VALUES clause, rejects invalid IRIs, and view endpoints accept and apply context_iri parameter. All existing tests still pass.

- [x] **T02: Frontend event wiring and builder UI** `est:1.5h`
  - Why: Connects the backend parameterized queries to user interaction. Without event wiring, the backend changes are unreachable.
  - Files: `backend/app/templates/browser/dashboard_page.html`, `backend/app/templates/browser/table_view.html`, `backend/app/templates/browser/dashboard_builder.html`, `frontend/static/js/workspace.js`
  - Do: (1) Dashboard page template: add `data-dashboard-id` on container, add `<script>` block that listens for `sempkm:dashboard-context-changed` and uses `htmx:configRequest` to inject `context_iri` into re-fetch URLs for consumer blocks. Consumer blocks with `listens_to_context` get `hx-trigger="load, sempkm:dashboard-context-changed from:body"`. (2) Table view template: when `dashboard_mode=1`, table rows emit `sempkm:dashboard-context-changed` event with the row's `?s` IRI instead of calling `openTab()`. Detect via template variable passed from endpoint. (3) Dashboard builder: add "Emits context" checkbox and "Context variable" text input to view-embed block config section.
  - Verify: Start Docker stack, create a dashboard with two view-embed blocks, configure emits_context on one and listens_to_context on the other, verify in browser that clicking a row triggers filtered re-fetch.
  - Done when: Custom event fires on row click, consumer block re-fetches with context_iri, and filtered results display. Builder UI saves emits_context/listens_to_context in block config.

- [x] **T03: Integration test and edge case hardening** `est:45m`
  - Why: Proves the full chain works end-to-end and documents the contract for S07.
  - Files: `backend/tests/test_values_injection.py`, `backend/tests/test_dashboard.py`
  - Do: Add edge case unit tests: VALUES injection with nested WHERE braces, empty context_iri (no-op), context_iri with invalid characters (graceful rejection), multiple consumer blocks on same dashboard. Verify all 599+ existing tests still pass. Run conflict marker check.
  - Verify: `cd backend && .venv/bin/pytest -x -q` — all tests pass. `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` returns empty.
  - Done when: Full test suite passes with new tests covering edge cases. Zero regressions. Zero conflict markers.

## Files Likely Touched

- `backend/app/views/service.py` — `inject_values_binding()` function
- `backend/app/views/router.py` — `context_iri`, `context_var`, `dashboard_mode` query params on `table_view`/`cards_view`
- `backend/app/dashboard/router.py` — `render_block()` context_iri passthrough for view-embed blocks
- `backend/app/templates/browser/dashboard_page.html` — event wiring script, data attributes, hx-trigger on consumer blocks
- `backend/app/templates/browser/table_view.html` — conditional row click behavior (context emit vs openTab)
- `backend/app/templates/browser/dashboard_builder.html` — emits_context/listens_to_context config fields
- `backend/tests/test_values_injection.py` — new test file for VALUES injection
- `backend/tests/test_dashboard.py` — extended tests
