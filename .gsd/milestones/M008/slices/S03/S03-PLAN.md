# S03: Live Embeds — Infrastructure, Types & Add UX

**Goal:** Canvas supports live iframe embeds for views, dashboards, SPARQL results, and object read views — addable via toolbar picker or explorer drag-drop, with dual-layer rendering that survives innerHTML rebuilds.

**Demo:** User clicks "Add embed" in canvas toolbar, picks a Table View → embed node appears with live iframe. User drags a dashboard from the explorer sidebar onto canvas → second embed node. Both iframes show real content. User drags a regular object node — iframes don't flash or reload. Save, reload page — all embed nodes restore with iframes reloading their URLs. 9th embed attempt shows rejection toast.

## Must-Haves

- `base_embed.html` template — minimal HTML page (htmx + theme CSS + Lucide + marked/DOMPurify) for iframe content
- `?embed=1` support on view, dashboard, object read, and SPARQL result endpoints
- New `GET /browser/sparql-result/{query_id}?embed=1` endpoint for saved query results
- Dual-layer rendering: persistent embed layer for iframes + dynamic layer for regular nodes
- Embed nodes survive `renderNodes()` innerHTML rebuild (iframes don't lose loaded state)
- `addEmbedNode()` function with `nodeType: 'embed'` and `embedConfig: {type, id, url, label}`
- Toolbar "Add embed" button → tabbed picker (Views / Dashboards / Queries) → place on canvas
- Explorer drag-drop extended for view and dashboard entries onto canvas
- `getDocument()`/`applyDocument()` serialize/restore `nodeType` and `embedConfig`
- Max 8 simultaneous embeds enforced with toast rejection
- `pointer-events: none` on embed layer container, `auto` on individual embeds (click pass-through)
- Edges render correctly for embed nodes (nodeBoxes queries both layers)
- Old canvas sessions without `nodeType` load without errors

## Proof Level

- This slice proves: integration (iframes with real content survive drag operations and persist across save/load)
- Real runtime required: yes (iframes load real endpoints from the running app)
- Human/UAT required: yes (iframe interactivity, drag feel, visual rendering of embedded content)

## Verification

- `docker compose exec api python -m pytest tests/test_canvas_embeds.py -v` — unit tests for embed URL construction, document serialization with embed nodes, backward compat
- Browser: navigate to `/browser/views/generic/table?embed=1` → renders full HTML page with table content, no sidebar
- Browser: navigate to `/browser/dashboard/{id}?embed=1` → renders dashboard, no sidebar
- Browser: navigate to `/browser/sparql-result/{query_id}?embed=1` → renders saved query results as HTML table
- Browser: place embed node via toolbar picker → iframe loads real content
- Browser: drag regular node around → iframe doesn't flash/reload
- Browser: save canvas, reload → embed nodes restore, iframes reload content
- Browser: attempt 9th embed → toast rejection message
- Browser: `SemPKMCanvas.exportState()` includes `nodeType: 'embed'` and `embedConfig` for embed nodes
- Browser: navigate to `/browser/views/generic/table?embed=1` with invalid class IRI → returns 200 with empty table (no 500)
- Browser: navigate to `/browser/sparql-result/nonexistent-id` → returns 404 page, not 500
- Diagnostic: embed endpoints return X-Embed-Mode response header for agent inspection

## Observability / Diagnostics

- Runtime signals: `addEmbedNode()` calls `setStatus('Embed added: ...')` for successful placement; toast on max-embed rejection
- Inspection surfaces: `SemPKMCanvas.exportState()` returns full document including nodeType/embedConfig per embed node; embed iframes have `data-embed-type` attribute for DOM inspection; `state.embedLayer` visible in devtools
- Failure visibility: iframe `load` event removes loading overlay — stale loading overlay indicates failed iframe load; embed endpoint 404/500 visible in browser network tab
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S01 resize handle system (pointer events, stopPropagation pattern, min constraints CSS), S01 width/height fields in node model, S01/S02 `getDocument()`/`applyDocument()` serialization pattern, existing view/dashboard/SPARQL/object endpoints
- New wiring introduced: `base_embed.html` template, `?embed=1` query param on 4 endpoint families, `state.embedLayer` in canvas.js, dual-layer rendering split in `renderNodes()`, embed payload detection in `onDrop()`/`onDragEnd()`, toolbar picker event wiring, explorer draggable attributes on view/dashboard entries
- What remains before the milestone is truly usable end-to-end: S04 (E2E Playwright tests + user guide documentation)

## Tasks

- [x] **T01: Embed template and endpoint support** `est:1.5h`
  - Why: Backend infrastructure that makes views, dashboards, SPARQL results, and object read views loadable as standalone HTML pages for iframe embedding. Independent of frontend — verifiable by direct URL navigation.
  - Files: `backend/app/templates/base_embed.html`, `backend/app/templates/browser/embed_wrapper.html`, `backend/app/templates/browser/sparql_result_embed.html`, `backend/app/templates/browser/object_embed.html`, `backend/app/views/router.py`, `backend/app/dashboard/router.py`, `backend/app/sparql/router.py`, `backend/app/browser/objects.py`
  - Do: Create `base_embed.html` (minimal: doctype, html, theme CSS, htmx CDN, Lucide CDN, marked+DOMPurify for object read, content block). Create `embed_wrapper.html` extending it. Add `embed: int = Query(default=0)` to `generic_view()`, `render_dashboard()`, `get_object()`. When embed=1, render inside embed_wrapper. Create new `GET /browser/sparql-result/{query_id}` endpoint in sparql router that executes saved query and renders HTML table. Create `object_embed.html` for stripped-down object read. Create `sparql_result_embed.html` for tabular query results.
  - Verify: Navigate to each embed URL directly in browser — each returns a valid full HTML page with real content, no sidebar, no heavy CDN scripts.
  - Done when: All 4 embed endpoint families return valid standalone HTML pages when `?embed=1` is set, with no sidebar and minimal script payload.

- [x] **T02: Dual-layer rendering and embed node type** `est:2h`
  - Why: The architectural crux — proves that iframe embeds survive the innerHTML rebuild in `renderNodes()`. Without this, every node drag would destroy iframe state. Also defines the embed node data model and wires resize/edge rendering for the new layer.
  - Files: `frontend/static/js/canvas.js`, `frontend/static/css/workspace.css`, `backend/app/templates/browser/canvas_page.html`
  - Do: In `mountCanvas()`, create `<div class="spatial-canvas-embed-layer">` inside viewport (sibling to `.spatial-canvas-layer`). Split `renderNodes()`: regular nodes → innerHTML rebuild on `state.layer` (existing); embed nodes → create/update persistent DOM elements in `state.embedLayer` via style.left/top/width/height (never innerHTML). Add `addEmbedNode(embedConfig, clientX, clientY)` that creates node with `nodeType:'embed'`, default 400×300, max 8 check with toast. Extend `removeNode()` to clean up embed DOM. Extend `getDocument()`/`applyDocument()` for nodeType/embedConfig serialization. Extend nodeBoxes collection to query both layers for edge rendering. Add CSS: embed layer positioning/transform inheritance, embed node article structure, iframe sizing, loading overlay, pointer-events pass-through. Add embed layer div to `canvas_page.html` template.
  - Verify: In browser — add an embed node via console (`SemPKMCanvas` API or manual state manipulation), drag a regular node, confirm iframe doesn't flash. Export state shows nodeType/embedConfig. Delete embed node, confirm DOM cleanup.
  - Done when: Embed nodes render as persistent iframes that survive regular node drag/renderNodes() calls. Resize handles work on embed nodes. Edges connect correctly to embed nodes. Save/load round-trips embed node data.

- [x] **T03: Toolbar embed picker** `est:1h`
  - Why: Primary add UX path — users need a discoverable way to add embeds without drag-drop. Picker fetches from existing list APIs and calls `addEmbedNode()`.
  - Files: `frontend/static/js/canvas.js`, `frontend/static/css/workspace.css`, `backend/app/templates/browser/canvas_page.html`
  - Do: Add "Add embed" button in `.canvas-page-actions`. On click, open a dropdown/popover with three tabs (Views / Dashboards / Queries). Each tab fetches from existing API: Views → `GET /browser/views/available`, Dashboards → `GET /api/dashboard`, Queries → `GET /api/sparql/saved`. Render items as clickable rows with label. On click, build appropriate embedConfig ({type, id, url, label}) and call `addEmbedNode()`. Close picker after placement. Enforce max 8 check before opening picker if at limit. Add CSS for picker dropdown (`.canvas-embed-picker`), tabs, item rows.
  - Verify: Browser — click "Add embed" → picker opens with tabs. Switch tabs, see items from each API. Click a view → embed node placed on canvas with correct iframe URL. Click a dashboard → embed node with dashboard URL.
  - Done when: All three tabs populate from live APIs. Clicking any item places an embed node at viewport center. Picker closes after placement.

- [x] **T04: Explorer drag-drop for embeds** `est:45m`
  - Why: Secondary add UX path — users who see dashboards and views in the sidebar should be able to drag them onto the canvas, matching the existing object drag-drop pattern.
  - Files: `backend/app/templates/browser/views_explorer.html`, `backend/app/templates/browser/dashboard_explorer.html`, `frontend/static/js/canvas.js`
  - Do: Add `draggable="true"` and `ondragstart` to dashboard entries in `dashboard_explorer.html` — set `window.__canvasDragPayload = {type:'dashboard', id:'...', label:'...'}`. Add `draggable="true"` and `ondragstart` to generic view entries and saved view entries in `views_explorer.html` — set payload with `type:'view'`. Modify `onDrop()` and `onDragEnd()` in canvas.js: check `payload.type` — if it's `'dashboard'`, `'view'`, or `'query'`, build embedConfig and call `addEmbedNode()` instead of `addNodeFromDrag()`. Preserve existing object drag behavior for payloads without a type field (backward compat).
  - Verify: Browser — drag a dashboard entry from DASHBOARDS explorer section onto canvas → embed node created with dashboard iframe. Drag a generic view entry (Table View) from VIEWS section → embed node with view iframe. Drag a regular object → still creates normal node (backward compat).
  - Done when: Dashboard and view entries draggable onto canvas. Embed nodes created with correct URLs. Regular object drag unaffected.

- [x] **T05: Persistence round-trip and unit tests** `est:1h`
  - Why: Formal verification that the full integration works — embed nodes survive save/load, backward compat holds, embed URLs are correct, max embed enforcement is tested.
  - Files: `backend/tests/test_canvas_embeds.py`, `frontend/static/js/canvas.js`
  - Do: Write backend unit tests: canvas document JSON serialization round-trip with embed nodes (nodeType + embedConfig preserved), backward compat (old sessions without nodeType load cleanly), embed URL construction validation for each embed type, max embed count enforcement logic, mixed node types in one document. Verify full browser round-trip: save canvas with mixed regular + embed nodes, reload page, confirm all nodes restore with correct positions/sizes/types, iframes reload content from persisted URLs.
  - Verify: `docker compose exec api python -m pytest tests/test_canvas_embeds.py -v` — all tests pass. Browser: save → reload → verify embed nodes restored with iframe content.
  - Done when: All unit tests pass. Manual browser verification confirms save/load round-trip with mixed node types preserves embed state.

## Files Likely Touched

- `backend/app/templates/base_embed.html` — NEW
- `backend/app/templates/browser/embed_wrapper.html` — NEW
- `backend/app/templates/browser/sparql_result_embed.html` — NEW
- `backend/app/templates/browser/object_embed.html` — NEW
- `backend/app/views/router.py` — embed param on generic_view
- `backend/app/dashboard/router.py` — embed param on render_dashboard
- `backend/app/sparql/router.py` — new sparql-result endpoint
- `backend/app/browser/objects.py` — embed param on get_object
- `frontend/static/js/canvas.js` — dual-layer rendering, addEmbedNode, picker, drag-drop extension, persistence
- `frontend/static/css/workspace.css` — embed layer, embed node, picker styles
- `backend/app/templates/browser/canvas_page.html` — embed layer div, "Add embed" button
- `backend/app/templates/browser/views_explorer.html` — draggable attributes
- `backend/app/templates/browser/dashboard_explorer.html` — draggable attributes
- `backend/tests/test_canvas_embeds.py` — NEW
