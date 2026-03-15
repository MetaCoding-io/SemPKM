# S05: Interactive Dashboards — Cross-View Context — UAT

**Milestone:** M006
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed (artifact-driven for unit/backend, live-runtime for browser verification)
- Why this mode is sufficient: The cross-view context chain spans backend SPARQL injection and frontend event wiring — both layers need verification. Unit tests cover SPARQL safety; browser testing covers the full event→re-fetch→render chain.

## Preconditions

- Docker stack running: `docker compose up -d` (api, triplestore, frontend)
- At least one Mental Model installed (e.g. basic-pkm) with seed data
- Logged in as owner user
- At least 2 ViewSpecs exist that produce table results (e.g. a "Projects" view and a "Notes" view)

## Smoke Test

Navigate to a dashboard with two view-embed blocks configured for cross-view context. Click a row in the source block. The consumer block should re-render with filtered results. If this works, the core chain is proven.

## Test Cases

### 1. Create Dashboard with Cross-View Context

1. Open Command Palette (Ctrl+K) and type "Create Dashboard" or navigate to an existing dashboard builder
2. Set dashboard name to "Context Test Dashboard"
3. Choose "sidebar-main" layout
4. Add a view-embed block in the sidebar slot — select a ViewSpec that returns multiple rows (e.g. Projects table)
5. Check the **"Emits context"** checkbox for this block
6. Add a view-embed block in the main slot — select a ViewSpec that returns rows related to the sidebar view (e.g. Notes table)
7. In the **"Context variable"** text input, enter the SPARQL variable name that should be filtered (e.g. `project`)
8. Save the dashboard
9. **Expected:** Dashboard saves successfully. Both blocks render with data from the triplestore.

### 2. Row Click Triggers Context Change

1. Open the dashboard created in test 1
2. Open browser devtools → Network tab
3. Click a row in the source (sidebar) block
4. **Expected:**
   - The clicked row gets a `.context-selected` highlight (teal left border)
   - A network request fires for the consumer block's slot URL containing `context_iri=<clicked_iri>&context_var=project`
   - The consumer block re-renders (may show filtered results or same results depending on query structure)
   - No JavaScript errors in console

### 3. Clicking Different Row Updates Context

1. With the dashboard from test 1 open
2. Click a different row in the source block
3. **Expected:**
   - Previous row loses `.context-selected` highlight
   - New row gains `.context-selected` highlight
   - Consumer block re-fetches with the new `context_iri`
   - Network tab shows a new request with the updated IRI

### 4. Dashboard Builder Config Persistence

1. Open the dashboard builder for the dashboard from test 1
2. Verify the source block shows "Emits context" checkbox checked
3. Verify the consumer block shows "Context variable" field with the value entered in test 1
4. Change the context variable name (e.g. from `project` to `topic`)
5. Save
6. Reopen the builder
7. **Expected:** The updated context variable name persists

### 5. VALUES Injection Appears in Backend

1. With the dashboard open and a source row clicked
2. Check Docker backend logs: `docker compose logs backend --tail=50`
3. **Expected:** A log line containing `inject_values_binding: var=` appears (DEBUG level), showing the variable name and selected IRI

### 6. Dashboard Mode Suppresses Tab Opening

1. Open the dashboard from test 1
2. Click a row in the source block
3. **Expected:** No new workspace tab opens. The click emits context instead of calling `openTab()`.
4. For comparison: open the same ViewSpec as a standalone view (not in a dashboard). Click a row.
5. **Expected:** A workspace tab opens for the clicked object (normal behavior).

## Edge Cases

### Invalid IRI Graceful Degradation

1. In browser devtools console, manually dispatch a context event with an invalid IRI:
   ```javascript
   document.body.dispatchEvent(new CustomEvent('dashboardContextChanged', {
     detail: { iri: 'not<valid>iri', dashboardId: '<your-dashboard-id>' }
   }));
   ```
2. **Expected:** Consumer block re-fetches but renders unfiltered results (graceful degradation). Backend log shows `WARNING` with `rejected invalid IRI`. No error displayed to user.

### Empty Context IRI (No-Op)

1. Dispatch context event with empty IRI:
   ```javascript
   document.body.dispatchEvent(new CustomEvent('dashboardContextChanged', {
     detail: { iri: '', dashboardId: '<your-dashboard-id>' }
   }));
   ```
2. **Expected:** Consumer block re-fetches without context_iri param. Results show unfiltered. No error.

### Dashboard Without Context Config

1. Create a dashboard with two view-embed blocks but do NOT check "Emits context" or set "Context variable"
2. Open the dashboard
3. Click a row in either block
4. **Expected:** Row click opens a workspace tab (normal `openTab()` behavior, not context emission). No `dashboardContextChanged` event fires.

### Cross-Dashboard Isolation

1. Open two browser tabs, each with a different dashboard that has cross-view context configured
2. Click a row in dashboard A's source block
3. **Expected:** Only dashboard A's consumer block re-fetches. Dashboard B (in the other browser tab) is unaffected because `dashboardContextChanged` events carry `dashboardId` and consumers check it.

## Failure Signals

- Consumer block shows stale/unchanged data after clicking a source row — event wiring broken
- JavaScript error in console mentioning `dashboardContextChanged` or `htmx:configRequest` — event plumbing issue
- Row click opens a workspace tab instead of emitting context — `dashboard_mode` not being passed or template conditional broken
- Network request for consumer block missing `context_iri` param — htmx:configRequest listener not firing or not scoped correctly
- Backend log shows no `inject_values_binding` entry after click — context_iri not reaching the view endpoint
- Both dashboard blocks go blank after click — VALUES injection breaking the SPARQL query

## Requirements Proved By This UAT

- Cross-view context filtering via parameterized SPARQL with VALUES binding
- Dashboard context variables flow via custom events and htmx re-fetch
- Dashboard builder exposes emits_context and listens_to_context configuration
- Graceful degradation on invalid context IRI (no error, renders unfiltered)

## Not Proven By This UAT

- Card or graph renderers emitting context events (table only in v1)
- Multiple named context variables on a single dashboard
- End-to-end workflow context passing (S06/S07 scope)
- Performance under high-frequency context switching (rapid clicking)

## Notes for Tester

- The consumer block filtering depends on the SPARQL query containing a variable matching the `listens_to_context` name. If the query doesn't use `?project` (or whatever variable you configured), VALUES injection has no effect on results — this is correct behavior, not a bug.
- `dashboard_mode=1` is appended to all view-embed block URLs regardless of context config — this is intentional (ensures table rows always use context behavior in dashboards).
- The `.context-selected` row highlight uses a teal left border — subtle but visible in both light and dark themes.
