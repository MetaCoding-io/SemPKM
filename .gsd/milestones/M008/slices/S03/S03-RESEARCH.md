# S03 — Research: Live Embeds — Infrastructure, Types & Add UX

**Date:** 2026-03-16

## Summary

S03 delivers four interrelated capabilities: embed infrastructure (dual-layer rendering + `base_embed.html` template), four embed content types (view, dashboard, SPARQL result, object read), add UX (toolbar picker + explorer drag-drop), and canvas persistence for the new node type. The riskiest piece is the dual-layer rendering (D124) — the current `renderNodes()` rebuilds `state.layer.innerHTML` every call, which destroys iframe state. Everything else is straightforward wiring of existing endpoints into iframe URLs with a lightweight embed template.

The codebase is well-prepared. View and dashboard templates are already HTML fragments (no base template inheritance) loaded via htmx. For embeds, a new `base_embed.html` wraps these fragments in a minimal full page (htmx + theme CSS only — no Cytoscape, dockview, CodeMirror, etc.). The existing `__canvasDragPayload` mechanism, `addNodeFromDrag()` function, and `onDrop()` handler need extension to handle a `type` field distinguishing embed payloads from object IRIs. Listing APIs already exist for all embed types: `/browser/views/available`, `/api/dashboard`, `/api/sparql/saved`, and `/api/canvas/search` (for objects).

This is targeted research — known patterns, some integration complexity, one architectural risk (dual-layer rendering).

## Recommendation

**Build in 5 tasks: (1) `base_embed.html` + embed endpoints, (2) dual-layer rendering + embed node type in canvas.js, (3) toolbar picker UI, (4) explorer drag-drop extension, (5) persistence + unit tests.**

Task 1 is backend-only and independently verifiable — create the embed template plus `?embed=1` support on view, dashboard, SPARQL, and object read endpoints. Task 2 is the riskiest (D124) — prove iframes survive drag operations by splitting rendering into a persistent embed layer and a dynamic node layer. Tasks 3-4 are independent add-UX paths. Task 5 verifies the full integration.

**SPARQL embed needs a new endpoint.** The current SPARQL console renders results client-side via JS (CodeMirror + custom table builder). There's no server-rendered HTML endpoint for saved query results. A new `GET /browser/sparql-result/{query_id}?embed=1` endpoint must execute the saved query and return an HTML result table using `base_embed.html`.

**Object read embed reuses `get_object()` with an `embed=1` flag** that skips the flip container, favorites, relations panel, and lint panel — returning just the property table + rendered markdown body wrapped in `base_embed.html`.

## Implementation Landscape

### Key Files

**Backend — embed infrastructure:**
- `backend/app/templates/base_embed.html` — **NEW.** Minimal base: doctype, `<html>`, theme CSS (`theme.css`, `style.css`, `workspace.css`), htmx CDN, Lucide CDN, `{% block content %}{% endblock %}`. No sidebar, no Cytoscape/dockview/CodeMirror/marked/etc. ~20 lines.
- `backend/app/templates/browser/embed_wrapper.html` — **NEW.** Extends `base_embed.html`, provides a content block that includes the inner fragment. Used by the embed endpoints to wrap existing fragment templates in a full page.
- `backend/app/views/router.py` — Add `embed: int = Query(default=0)` param to `generic_view()` (line 114) and existing spec-specific endpoints (`table_view`, `card_view`, `graph_view` at lines 426, 552, 706). When `embed=1`, render the fragment inside `embed_wrapper.html` instead of returning the bare fragment. ~15 lines per endpoint.
- `backend/app/dashboard/router.py` — Add `embed: int = Query(default=0)` to `render_dashboard()` (line 148). When embed=1, wrap `dashboard_page.html` in `base_embed.html`.
- `backend/app/sparql/router.py` — **NEW endpoint:** `GET /browser/sparql-result/{query_id}` that fetches saved query text, executes it, and renders results as an HTML table using `base_embed.html`. Reuses `_execute_sparql()` (line 144) and `_enrich_sparql_results()` (line 188) from the same module.
- `backend/app/browser/objects.py` — Add `embed: int = Query(default=0)` to `get_object()` (line 53). When embed=1, render a simplified read-only template (`object_embed.html`) extending `base_embed.html` — property table + markdown body, no flip container, no favorites, no form, no relations panel.
- `backend/app/templates/browser/object_embed.html` — **NEW.** Extends `base_embed.html`. Renders property table (reuse `object_read.html` include) + markdown body. Stripped of edit form, flip container, toolbar actions.
- `backend/app/templates/browser/sparql_result_embed.html` — **NEW.** Extends `base_embed.html`. Simple table of SPARQL results with IRI pills.

**Frontend — dual-layer rendering:**
- `frontend/static/js/canvas.js` — Core changes:
  - New state fields: `state.embedLayer` (DOM ref to persistent embed container), no `state.embedNodes` needed (embed nodes live in `state.nodes` with `nodeType: 'embed'`).
  - `mountCanvas()` (line 181): create `<div class="spatial-canvas-embed-layer">` sibling to `.spatial-canvas-layer`, assign to `state.embedLayer`. Both layers inside `.spatial-canvas-viewport` so pan/zoom transform applies equally.
  - `renderNodes()` (line 891): split into two paths. Regular nodes → `state.layer.innerHTML` (existing). Embed nodes → update position/size on persistent DOM elements in `state.embedLayer` via `style.left`/`style.top`/`style.width`/`style.height`. Create embed DOM elements only when they don't exist yet (keyed by `node.id`). Remove orphaned embed elements when nodes are deleted.
  - `addEmbedNode(embedConfig, clientX, clientY)` — **NEW.** Creates a node with `nodeType: 'embed'`, `embedConfig: {type, id, url, label}`, default width 400, height 300. Pushes to `state.nodes`, calls `renderNodes()`.
  - `getDocument()` (line 1221): serialize `nodeType` and `embedConfig` when present.
  - `applyDocument()` (line 1247): restore `nodeType` and `embedConfig` from saved data.
  - `removeNode()` (line 712): also remove the persistent embed DOM element from `state.embedLayer`.
  - Max embed count enforcement: before `addEmbedNode`, count nodes where `nodeType === 'embed'`; reject if >= 8 with `showToast()`.

**Frontend — embed node HTML structure:**
```html
<article class="spatial-node spatial-node-embed" data-node-id="..." style="left:Xpx; top:Ypx; width:Wpx; height:Hpx;">
  <header class="spatial-node-header">
    <span class="spatial-node-title">Table View</span>
    <button class="spatial-node-delete">✕</button>
  </header>
  <div class="spatial-node-embed-body">
    <iframe src="/browser/views/generic/table?embed=1" class="spatial-embed-iframe"></iframe>
    <div class="spatial-embed-loading">Loading...</div>
  </div>
  <div class="spatial-node-resize-handle"></div>
  <div class="spatial-node-resize-handle-right"></div>
  <div class="spatial-node-resize-handle-bottom"></div>
</article>
```

**Frontend — toolbar picker:**
- `backend/app/templates/browser/canvas_page.html` — Add "Add embed" button in `.canvas-page-actions`. Clicking opens a dropdown/popover.
- `frontend/static/js/canvas.js` — New function `openEmbedPicker()` renders a tabbed dropdown (Views | Dashboards | Queries | Objects). Each tab fetches from existing list APIs:
  - Views: `GET /browser/views/available` → JSON array of `{spec_iri, label, renderer_type}`
  - Dashboards: `GET /api/dashboard` → JSON array of `{id, name}`
  - Queries: `GET /api/sparql/saved` → JSON array of `{id, name, query_text}`
  - Objects: not needed for v1 (users drag objects from explorer)
  - Clicking an item calls `addEmbedNode()` with the appropriate `embedConfig`.

**Frontend — explorer drag-drop:**
- `backend/app/templates/browser/dashboard_explorer.html` — Add `draggable="true"` and `ondragstart` handler to dashboard tree-leaf divs. Set `window.__canvasDragPayload = { type: 'dashboard', id: '...', label: '...' }`.
- `backend/app/templates/browser/views_explorer.html` — Add `draggable="true"` to generic view entries. Set `window.__canvasDragPayload = { type: 'view', renderer: 'table', label: 'Table View' }`. Similarly for Cards/Graph. For Saved Views, add drag on individual saved view entries.
- `frontend/static/js/canvas.js` — Modify `onDrop()` (line 443) and `onDragEnd()` (line 477): check `payload.type` — if it's `'dashboard'`, `'view'`, `'query'`, or `'object-embed'`, call `addEmbedNode()` instead of `addNodeFromDrag()`.

**CSS:**
- `frontend/static/css/workspace.css` — New rules:
  - `.spatial-canvas-embed-layer` — same position/transform as `.spatial-canvas-layer`, higher z-index (or same z-index with DOM order).
  - `.spatial-node-embed` — override `.spatial-node` with no markdown body styling, iframe fills content area.
  - `.spatial-embed-iframe` — `width: 100%; height: calc(100% - header); border: none;`
  - `.spatial-embed-loading` — centered spinner/text, hidden once iframe `load` event fires.
  - `.canvas-embed-picker` — toolbar dropdown styles.

### Build Order

**T01: `base_embed.html` + embed endpoints (backend, independently testable)**
Create `base_embed.html` template. Add `?embed=1` support to view, dashboard, object read endpoints. Create new SPARQL result endpoint. Verify each endpoint returns a valid full HTML page when `embed=1` is set. Test by navigating to the URLs directly in a browser.

**T02: Dual-layer rendering + embed node type (highest risk, proves D124)**
This is the architectural crux. Add `state.embedLayer` in `mountCanvas()`. Split `renderNodes()` to handle embed nodes on the persistent layer. Prove that dragging a regular node doesn't destroy an iframe's loaded state. Prove that an embed node can be repositioned without iframe reload. Prove resize handles work on embed nodes. This task retires the "innerHTML rebuild destroys iframes" risk from the roadmap.

**T03: Toolbar picker UI (frontend, depends on T01 for URLs)**
"Add embed" button → tabbed dropdown → fetch from list APIs → click to place → `addEmbedNode()`. Enforce max 8 embeds. Pure frontend, can be tested with manual browser interaction.

**T04: Explorer drag-drop for embeds (frontend + template changes)**
Add `draggable="true"` to dashboard and view explorer entries. Extend `onDrop()`/`onDragEnd()` to detect embed payloads. Test by dragging a dashboard from the sidebar onto the canvas.

**T05: Persistence + unit tests**
Extend `getDocument()`/`applyDocument()` for `nodeType` and `embedConfig` (likely done in T02 but verified here). Backend unit tests for embed URL construction. Canvas document round-trip tests with embed nodes. Backward compat test — old sessions without nodeType load cleanly.

### Verification Approach

**Embed endpoints (T01):**
- Navigate to `http://localhost:3000/browser/views/generic/table?embed=1` — should render a full HTML page with table content, no sidebar, no CDN zoo.
- Navigate to `http://localhost:3000/browser/dashboard/{id}?embed=1` — should render dashboard with CSS Grid layout, functional htmx blocks, no sidebar.
- Navigate to `http://localhost:3000/browser/sparql-result/{query_id}?embed=1` — should render saved query results as HTML table.
- Navigate to `http://localhost:3000/browser/object/{iri}?embed=1` — should render read-only property table + markdown body, no edit form.

**Dual-layer rendering (T02):**
- Place an embed node (view) on canvas. Drag a regular node around. Verify the iframe doesn't flash/reload (check iframe's `contentWindow.document.readyState` or visual inspection).
- Resize the embed node. Verify iframe content scales/reflows.
- Delete an embed node. Verify its DOM element is removed from the embed layer.
- `SemPKMCanvas.exportState()` includes `nodeType: 'embed'` and `embedConfig` for embed nodes.

**Toolbar picker (T03):**
- Click "Add embed" → see tabbed dropdown with Views/Dashboards/Queries tabs.
- Select a dashboard → embed node appears at viewport center with loading state → iframe loads dashboard content.
- Try to add a 9th embed → see rejection toast.

**Explorer drag (T04):**
- Drag a dashboard entry from the DASHBOARDS section onto the canvas → embed node created.
- Drag a generic view entry (Table View) onto the canvas → embed node created.

**Full integration:**
- Canvas with mixed nodes: 2 regular objects (one resized), 1 property-flipped, 1 view embed, 1 dashboard embed. Save. Reload page. All nodes, sizes, states, and embeds restore correctly. Iframes reload their content from persisted URLs.

## Constraints

- **`renderNodes()` innerHTML rebuild** — The single biggest constraint. Every `renderNodes()` call sets `state.layer.innerHTML = nodesHtml`, destroying all DOM state. Embed iframes MUST live in a separate persistent layer that is never innerHTML-rebuilt. Only `style.left`/`style.top`/`style.width`/`style.height` updates on embed elements.
- **Same-origin iframes only** — All SemPKM pages served from `localhost:3000` via nginx. Session cookies are shared. `window.parent` is accessible. No CORS issues.
- **View templates are fragments** — `table_view.html`, `cards_view.html`, `graph_view.html`, `dashboard_page.html` are htmx fragments without a `<html>`/`<head>` wrapper. The embed endpoints must wrap them in `base_embed.html` to produce valid iframe-loadable pages.
- **No `hx-push-url` in view/dashboard templates** — Verified: zero occurrences. The iframe navigation escape risk from the M008 research is lower than expected. htmx swaps happen within the iframe's document, which is correct for filtering/pagination.
- **Vanilla JS, no framework** — Canvas is an IIFE. All DOM manipulation is manual. The embed picker and drag-drop extension follow the same pattern.
- **`base.html` loads ~18 CDN scripts** — Each iframe using `base.html` would load Cytoscape, dockview, CodeMirror, marked, DOMPurify, highlight.js, driver.js, split.js, ninja-keys. `base_embed.html` must load only htmx + theme CSS + Lucide + marked + DOMPurify (for markdown rendering in object read embeds).

## Common Pitfalls

- **Embed layer must receive the same CSS transform as the node layer** — Both `.spatial-canvas-layer` and `.spatial-canvas-embed-layer` must be children of `.spatial-canvas-viewport` which applies the pan/zoom transform via `applyTransform()`. If the embed layer is outside the viewport, embeds won't pan/zoom with regular nodes.

- **Resize handles on embed nodes** — Embed nodes in the persistent layer need the same resize handle HTML and pointer event wiring as regular nodes (from S01). The `onPointerDown` handler's `event.target.closest('.spatial-node-resize-handle')` must match elements in the embed layer too. Since the embed layer is a sibling of the node layer, the event bubbles to the viewport where `onPointerDown` is registered — this should work without changes.

- **`onPointerDown` must recognize embed node headers for drag** — Currently `event.target.closest('.spatial-node')` only finds nodes in `state.layer`. With the embed layer, it must also find nodes in `state.embedLayer`. Since both layers are children of `.spatial-canvas-viewport`, and `onPointerDown` is registered on `state.viewport`, `closest('.spatial-node')` will work — it traverses up from the event target regardless of which layer it's in. But `node.dataset.nodeId` must be readable from both regular and embed node DOM.

- **Edge rendering for embed nodes** — `renderNodes()` builds `nodeBoxes` by querying `.spatial-node` elements in `state.layer`. Embed nodes are in `state.embedLayer`. The `nodeBoxes` collection must include embed nodes too — query both layers, or query `.spatial-canvas-viewport .spatial-node` which covers both.

- **Iframe `load` event for loading state** — Attach `load` event listener when creating the iframe DOM element (not in `renderNodes()`). Remove the `.spatial-embed-loading` overlay on load. This listener persists because the embed element is never recreated.

- **Link clicks inside embeds** — Links in table rows (IRI pills) call `openTab()` which is defined on the parent page. Inside an iframe, `openTab` is undefined. For v1, clicking an IRI pill in an embedded view should do nothing or open in the iframe (natural behavior). Full link routing via `window.parent.openTab()` (D129) can be wired as a refinement: the embed template includes a script that overrides click handlers to call `window.parent.openTab(iri, label)`.

## Open Risks

- **Pointer event routing across two layers** — The embed layer sits on top of (or beside) the regular node layer. Pointer events for drag, resize, and click must correctly route to the right handler regardless of which layer the target element is in. If the embed layer has a higher z-index and covers regular nodes, clicks on regular nodes could be intercepted. Mitigation: set `pointer-events: none` on the embed layer container, `pointer-events: auto` on individual embed node elements. This lets clicks "pass through" the empty areas of the embed layer to the regular node layer below.

- **SPARQL result embed may lack CodeMirror for pretty display** — The current SPARQL panel uses CodeMirror for the query editor and a custom JS table builder for results. The new `sparql_result_embed.html` renders a plain HTML table — functional but less polished than the SPARQL panel's custom rendering. This is acceptable for v1.

- **Dashboard context filtering across iframe boundary** — `dashboardContextChanged` events dispatch on `document.body` inside the iframe. This is self-contained — each embedded dashboard has independent context filtering. Cross-dashboard context (parent canvas → embedded dashboard) is out of scope for v1.

## Sources

- Codebase inspection: `canvas.js` (1486 LOC post-S01/S02), `views/router.py`, `dashboard/router.py`, `sparql/router.py`, `objects.py`, `workspace-layout.js`, templates
- Decisions: D124 (dual-layer), D125 (base_embed.html), D128 (max 8 embeds), D129 (link routing via window.parent)
- S01 summary: resize handle system, pointer event priority chain, innerHTML rebuild pattern
