# S03: Live Embeds — Infrastructure, Types & Add UX — UAT

**Milestone:** M008
**Written:** 2026-03-16

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for browser verification)
- Why this mode is sufficient: Embed infrastructure requires both backend endpoint testing and live browser interaction to verify iframe loading, dual-layer rendering, and drag-drop UX

## Preconditions

- Docker Compose stack running (`docker compose up -d`)
- At least one saved SPARQL query exists (navigate to SPARQL console, run a query, save it)
- At least one object exists in the triplestore (for object embed testing)
- Canvas page accessible at `/browser/views/generic/graph` or via Spatial Canvas in explorer

## Smoke Test

Open the spatial canvas. Click the "Embed" button in the toolbar. The picker dropdown appears with Views tab showing entries (Table View, Cards View, Graph View, etc.). Click any entry — an embed node appears on the canvas with a loading overlay that fades when the iframe loads real content.

## Test Cases

### 1. Embed endpoint — Table View

1. Navigate to `/browser/views/generic/table?embed=1`
2. **Expected:** Full HTML page with table content. No sidebar. No Cytoscape/dockview/CodeMirror scripts. Title contains "SemPKM Embed".

### 2. Embed endpoint — Object Read

1. Open any object in the workspace to get its IRI
2. Navigate to `/browser/object/{iri}?embed=1`
3. **Expected:** Stripped-down object page with type label, property table, and rendered markdown body. No edit form, no favorites star, no sidebar.

### 3. Embed endpoint — SPARQL Result

1. Save a SPARQL query via the SPARQL console (e.g. `SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10`)
2. Note the query ID from the saved queries list
3. Navigate to `/browser/sparql-result/{query_id}`
4. **Expected:** HTML table showing query results with column headers. Enriched labels where available.

### 4. Embed endpoint — 404 handling

1. Navigate to `/browser/sparql-result/nonexistent-id`
2. **Expected:** 404 response, not 500 server error

### 5. X-Embed-Mode response header

1. Open browser devtools Network tab
2. Navigate to `/browser/views/generic/table?embed=1`
3. Inspect response headers
4. **Expected:** `X-Embed-Mode: 1` header present
5. Navigate to `/browser/views/generic/table` (no embed param)
6. **Expected:** No `X-Embed-Mode` header

### 6. Toolbar picker — open and browse tabs

1. Open the spatial canvas
2. Click the "Embed" button in the toolbar
3. **Expected:** Dropdown opens with "Views" tab active, showing items from the API
4. Click "Dashboards" tab
5. **Expected:** Tab switches, shows dashboard entries or "No items found"
6. Click "Queries" tab
7. **Expected:** Tab switches, shows saved query entries or "No items found"

### 7. Toolbar picker — place embed node

1. Open the spatial canvas
2. Click "Embed" → Views tab → click "Table View"
3. **Expected:** Embed node appears at viewport center. Iframe loads with live table content (rows of real data). Picker closes after placement. Status bar shows "Embed added: Table View".

### 8. Dual-layer iframe persistence

1. Place an embed node (Table View) on the canvas
2. Wait for the iframe to fully load (loading overlay disappears)
3. Drag a regular object node around the canvas
4. **Expected:** The embed iframe does NOT flash, reload, or lose its loaded content. The regular node moves normally.

### 9. Embed node resize

1. Place an embed node on the canvas
2. Hover over a corner/edge of the embed node
3. Drag to resize
4. **Expected:** Node resizes. Iframe content adjusts to fill the new size. Minimum size enforced (160×80).

### 10. Explorer drag — View entry

1. Open the spatial canvas
2. In the VIEWS explorer section, drag "Table View" onto the canvas
3. **Expected:** Embed node created with Table View iframe content. Status bar shows "Embed added: Table View".

### 11. Explorer drag — Dashboard entry

1. Create a dashboard if none exist (via DASHBOARDS section "+" button)
2. Open the spatial canvas
3. Drag the dashboard entry from DASHBOARDS explorer section onto the canvas
4. **Expected:** Embed node created with dashboard iframe content

### 12. Explorer drag — regular object (backward compat)

1. Open the spatial canvas
2. Drag a regular object from the OBJECTS explorer section onto the canvas
3. **Expected:** Regular node created (NOT an embed node). Node shows object title and markdown body.

### 13. Max 8 embed enforcement

1. Open the spatial canvas
2. Add 8 embed nodes via the toolbar picker (any combination of types)
3. Click "Embed" button again
4. **Expected:** Toast message "Maximum of 8 embeds reached". Picker does NOT open.

### 14. Save/load round-trip

1. Open the spatial canvas
2. Add 2 regular object nodes and 2 embed nodes (one view, one SPARQL result)
3. Save the canvas session (File → Save or Ctrl+S)
4. Reload the page (F5)
5. **Expected:** All 4 nodes restore at their original positions and sizes. Embed nodes show iframes reloading their content. Regular nodes show markdown bodies.

### 15. Export state inspection

1. Open the spatial canvas with at least one embed node
2. Open browser devtools console
3. Run: `SemPKMCanvas.exportState()`
4. **Expected:** Returned object has `nodes` array. Embed nodes have `nodeType: 'embed'` and `embedConfig: {type, id, url, label}`. Regular nodes have no `nodeType` field.

### 16. Backward compat — old sessions

1. Open browser console
2. Import a document with no nodeType fields:
   ```js
   SemPKMCanvas.importState({nodes:[{id:'old-1', x:100, y:100, title:'Old Node', markdown:'test'}], edges:[]})
   ```
3. **Expected:** Node renders normally with no errors. No `nodeType` contamination on export.

## Edge Cases

### Embed node deletion

1. Place an embed node on the canvas
2. Select it, press Delete (or use the delete button in the header)
3. **Expected:** Embed node removed from both visual canvas and internal state. `SemPKMCanvas.exportState()` no longer includes it. Embed layer DOM child count decreases by 1.

### Pan/zoom with embeds

1. Place an embed node on the canvas
2. Pan the canvas (click and drag on empty space)
3. Zoom in/out (scroll wheel)
4. **Expected:** Embed nodes move and scale in sync with regular nodes. No visual offset between layers.

### Rapid embed placement

1. Quickly add 5 embed nodes in succession via the toolbar picker
2. **Expected:** All 5 appear at viewport center (may overlap). All iframes load. No JS console errors.

## Failure Signals

- Iframe shows blank white or perpetual loading overlay → embed URL incorrect or endpoint returning error
- Embed node disappears when dragging a regular node → innerHTML rebuild is destroying embed layer (dual-layer broken)
- "Maximum of 8 embeds reached" appears before 8 embeds → embed count logic counting regular nodes
- Errors in console mentioning `embedConfig` or `TypeError: Cannot read properties of undefined` → malformed embed guard not working
- Explorer drag creates regular node instead of embed → drag payload type field not being detected
- Save/reload loses embed nodes → nodeType/embedConfig not serialized in getDocument()

## Requirements Proved By This UAT

- CANVAS-03 — Tests 1, 2, 7, 8, 10, 11, 14 prove view and dashboard embeds render as live iframes, survive drag operations, and persist across save/load
- CANVAS-04 — Tests 2, 3, 4 prove SPARQL result and object read embeds render correctly
- CANVAS-05 — Tests 6, 7, 10, 11, 13 prove toolbar picker and explorer drag-drop both create embed nodes, with max-8 enforcement

## Not Proven By This UAT

- E2E Playwright automation of embed workflows (deferred to S04)
- User guide documentation of embed features (deferred to S04)
- Embed link routing (clicks inside iframes opening in parent workspace) — deferred beyond M008
- Lazy loading of off-screen embeds — deferred, covered by max-8 limit

## Notes for Tester

- If no saved SPARQL queries exist, create one before testing embed endpoint test case 3. Navigate to the SPARQL console, run `SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10`, and save it.
- The dashboard embed test (case 11) requires at least one dashboard to exist. Create one via the DASHBOARDS section "+" button if needed.
- When testing save/load (case 14), the canvas auto-saves to the active session. Simply reloading the page should restore the session.
- The "Embed" button is in the canvas toolbar row alongside other canvas controls (e.g., zoom, grid toggle).
