---
estimated_steps: 7
estimated_files: 4
---

# T02: Frontend Event Wiring and Builder UI

**Slice:** S05 — Interactive Dashboards — Cross-View Context
**Milestone:** M006

## Description

Wire the frontend event system that connects source blocks (row click → context event) to consumer blocks (context event → re-fetch with filter). Add the `sempkm:dashboard-context-changed` custom event, `htmx:configRequest` listener for injecting `context_iri` into re-fetch URLs, conditional row click behavior in table views, and emits_context/listens_to_context config fields in the dashboard builder.

## Steps

1. Update `backend/app/templates/browser/dashboard_page.html`:
   - Add `data-dashboard-id="{{ dashboard_id }}"` on the `.dashboard-container` div
   - For consumer blocks (those with `listens_to_context` in their config): change `hx-trigger` from `"load"` to `"load, sempkm:dashboard-context-changed from:body"`, and add `data-listens-to-context="{{ block.config.listens_to_context }}"` and `data-dashboard-id="{{ dashboard_id }}"` attributes
   - For source blocks (those with `emits_context`): add `data-emits-context="1"` attribute
   - Add inline `<script>` at the bottom of the template:
     - Listen for `htmx:configRequest` on the dashboard container
     - When the triggering element has `data-listens-to-context`, inject `context_iri` and `context_var` params from the dashboard's current context state
     - Store current context IRI in a JS variable scoped to the dashboard container (e.g., `dashboardContainer.dataset.currentContextIri`)
     - On `sempkm:dashboard-context-changed`, check dashboardId matches, then update the stored context IRI

2. Update `backend/app/templates/browser/table_view.html`:
   - Accept `dashboard_mode` template variable
   - When `dashboard_mode` is truthy, replace row `onclick="openTab(...)"` with `onclick="emitDashboardContext('{{ row.s }}', this)"` 
   - Add `emitDashboardContext(iri, el)` function: walks up DOM to find `[data-dashboard-id]`, dispatches `sempkm:dashboard-context-changed` custom event on `document.body` with `detail: { iri, dashboardId }`, highlights the selected row with `.context-selected` class

3. Update `backend/app/views/router.py` `table_view()`:
   - Pass `dashboard_mode` to the template context so the template can conditionally render row click handlers

4. Add CSS for `.context-selected` row highlight in dashboard context (either inline in template or in workspace.css):
   - Subtle background color to indicate the active context source row

5. Update `backend/app/templates/browser/dashboard_builder.html`:
   - In the view-embed block config section, add:
     - "Emits context" checkbox: `<input type="checkbox" class="block-config-emits" data-key="emits_context">`
     - "Context variable" text input: `<input type="text" class="block-config-context-var" data-key="listens_to_context" placeholder="e.g. project">`
   - Wire these into the existing `collectBlocks()` function that serializes block config for the fetch() submit

6. Update `render_block()` in `backend/app/dashboard/router.py`:
   - The block wrapper HTML for view-embed blocks should include the data attributes from T01, but also the `hx-trigger` modification for consumer blocks
   - Ensure the hx-get URL for view-embed blocks includes `dashboard_mode=1`

7. Manual verification in browser — start Docker, create a test dashboard with two view-embed blocks, configure one as emits_context and the other with listens_to_context, click a row, verify the consumer block re-fetches with filtered data.

## Must-Haves

- [ ] `sempkm:dashboard-context-changed` event carries `{ iri, dashboardId }` in detail
- [ ] Consumer blocks only react to events from their own dashboard (dashboardId check)
- [ ] Table rows in dashboard mode emit context event, not openTab
- [ ] `htmx:configRequest` injects context_iri and context_var into re-fetch URL params
- [ ] Dashboard builder saves emits_context and listens_to_context in block config JSON
- [ ] Selected row gets visual highlight (`.context-selected` class)

## Verification

- Start Docker stack, open workspace in browser
- Create dashboard with sidebar-main layout
- Add view-embed block in sidebar: pick a type-list view, check "Emits context"
- Add view-embed block in main: pick a related-objects view, set "Context variable" to the relevant SPARQL variable
- Open the dashboard, click a row in the sidebar block
- Verify main block re-renders with filtered results
- Verify clicking a different row updates the filter

## Inputs

- T01 output: `inject_values_binding()` in ViewSpecService, `context_iri`/`context_var`/`dashboard_mode` params on view endpoints, data attributes on render_block output
- S03 output: dashboard_page.html template structure, render_block dispatch, dashboard builder form
- Research: htmx `hx-trigger="event from:body"` pattern (proven in D048/favorites), `htmx:configRequest` for param injection (proven in D087/tag autocomplete)

## Observability Impact

- **Custom event:** `sempkm:dashboard-context-changed` dispatched on `document.body` with `detail: { iri, dashboardId }` — inspectable via browser devtools Event Listeners panel on body
- **Network signal:** Consumer block re-fetch requests include `?context_iri=<selected>&context_var=<varname>` — visible in Network tab
- **DOM state:** `dashboardContainer.dataset.currentContextIri` stores the last-selected context IRI — readable via `document.querySelector('.dashboard-container').dataset.currentContextIri`
- **Visual signal:** `.context-selected` class applied to the active source row — visible in Elements panel
- **Failure visibility:** If no `[data-dashboard-id]` ancestor exists when a row click fires `emitDashboardContext`, the event silently no-ops (no error, no re-fetch). Consumer blocks without a matching dashboardId ignore context events.

## Expected Output

- `backend/app/templates/browser/dashboard_page.html` — event wiring script, data attributes, conditional hx-trigger
- `backend/app/templates/browser/table_view.html` — conditional row click behavior for dashboard mode
- `backend/app/templates/browser/dashboard_builder.html` — emits_context/listens_to_context config fields
- `backend/app/dashboard/router.py` — render_block hx-trigger modification for consumer blocks
