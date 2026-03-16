# M008 — Research: Spatial Canvas — Resizable Nodes, Property Flip & Live Embeds

**Date:** 2026-03-15

## Summary

M008 transforms the spatial canvas from a read-only graph exploration surface into a composable working surface with resizable nodes, property inspection, and live embedded panels. The existing `canvas.js` (1316 LOC IIFE) is well-structured with clear state management, and the node model (`{id, title, uri, x, y, markdown, collapsed}`) is straightforward to extend with `width`, `height`, `nodeType`, `embedConfig`, and `showProperties` fields. The canvas document is persisted as untyped JSON blobs in `user_settings` — no Pydantic validation on the document shape — so schema extension is zero-migration.

The riskiest pieces are: (1) resize handle pointer events conflicting with the existing drag-to-move system, (2) the property flip needing a new lightweight API endpoint since the existing `get_object` builds full page context including favorites, form metadata, and template rendering — far too heavy for an inline canvas flip, and (3) iframe embed mode requiring either a new `base_embed.html` template or conditional chrome suppression across `base.html`, the sidebar component, and page-specific toolbars.

The recommended approach is: prove resize first (pure frontend, unblocks everything else), then property flip (new API endpoint + inline rendering), then embed infrastructure (`?embed=1` query param + `base_embed.html`), then embed UX (toolbar picker + explorer drag).

## Recommendation

**Build order: Resize → Property Flip → Embed Infrastructure → Embed Types → Embed UX → Persistence + E2E + Docs**

Resize is pure frontend with no backend changes and establishes the foundation (nodes with variable dimensions affect edge rendering, drop placement, and all subsequent features). Property flip needs a new backend endpoint but renders inline in the node (no iframe). Embeds require the most new infrastructure (embed mode templates, iframe management, new node type) and should come after the simpler features prove the node model extension works.

**Use a separate `base_embed.html` template** rather than conditional hiding in `base.html`. The current `base.html` loads 15+ CDN scripts (Cytoscape, dockview, CodeMirror, marked, etc.), the sidebar component, and the workspace layout. An embed page needs only htmx, theme CSS, and the content. A separate lightweight base saves significant iframe payload and avoids the fragility of hiding elements with CSS in a template that other features depend on.

**Property flip should NOT use iframes.** The SHACL-derived property data is lightweight (10-30 key/value pairs). A compact table rendered directly inside the node from a new JSON API endpoint is faster, lighter, and avoids iframe overhead for the most common flip action. Only views, dashboards, SPARQL results, and object read views need iframe embeds.

## Implementation Landscape

### Key Files

- `frontend/static/js/canvas.js` (1316 LOC) — Core canvas IIFE. Node model lives in `state.nodes[]`, rendering in `renderNodes()`, drag in `onPointerDown`/`onPointerMove`/`onPointerUp`, serialization in `getDocument()`/`applyDocument()`. All new features touch this file. Width 260px is hardcoded in the HTML template via `renderNodes()` (inline `style="left:X; top:Y"`) and in CSS via `.spatial-node { width: 260px }`.
- `frontend/static/css/workspace.css` (line 4816+) — `.spatial-node` fixed at 260px width. Needs: remove fixed width, add min/max constraints, add resize handle styling, add embed node styling, property flip table styling.
- `backend/app/canvas/router.py` (361 LOC) — Canvas API. Needs: new `/api/canvas/properties` endpoint for property flip data.
- `backend/app/canvas/service.py` (250 LOC) — `CanvasService` persisting JSON blobs via `UserSetting`. No schema validation on document — just `json.dumps(document)`. Schema extension is automatic; old docs missing new fields get defaults in `applyDocument()`.
- `backend/app/canvas/schemas.py` (78 LOC) — Pydantic schemas for canvas API. The `CanvasPutBody.document` is `dict[str, Any]` — no inner validation. Could add typed node schema for the properties endpoint response.
- `backend/app/templates/browser/canvas_page.html` — Canvas page template with toolbar. Needs: "Add embed" button in toolbar, embed type picker UI.
- `backend/app/templates/base.html` — Full page base layout with sidebar, 15+ CDN scripts. A new `base_embed.html` is needed for lightweight iframe content.
- `backend/app/browser/objects.py` — `get_object()` handler (lines 41-175) builds full page context with ~8 queries. The property flip needs a stripped-down version that returns JSON: `{properties: [{name, value, datatype, source}], type_label}`.
- `backend/app/services/shapes.py` — `ShapesService` with `get_form_for_type()` → `NodeShapeForm` with `PropertyShape` list. Property flip endpoint reuses this to get form metadata, then queries property values.
- `backend/app/views/router.py` — View rendering endpoints. Need `?embed=1` support to switch base template.
- `backend/app/dashboard/router.py` — Dashboard rendering. `render_dashboard()` returns HTML via `dashboard_page.html`. Need embed mode support.
- `frontend/static/js/workspace.js` — `openTab` and `openGenericViewTab` functions. Explorer drag infrastructure uses `window.__canvasDragPayload`. Needs: extend drag payload to support view/dashboard/query types, not just object IRIs.
- `backend/app/templates/browser/tree_children.html` — Sets `window.__canvasDragPayload` on `ondragstart`. Currently only handles object IRIs. Needs extension for view/dashboard/query drag sources.

### Build Order

**1. Resize (prove first — pure frontend, zero backend)**
Why first: Every subsequent feature depends on nodes having variable dimensions. Edge rendering (`edgePoint()`) already uses `el.offsetWidth`/`el.offsetHeight` — if CSS width becomes dynamic, edges adapt automatically. Drop placement (`addNodeFromDrag`, `addNodesFromBulkDrop`) hardcodes `260 + GRID` column width — needs parameterization. The `renderNodes()` function sets `style="left:X; top:Y"` but not width/height — adding `width:Wpx; height:Hpx` in the style string is the integration point.

Key changes:
- Remove `width: 260px` from CSS `.spatial-node`, add `min-width: 160px; min-height: 80px`
- Add resize handle element(s) to node HTML in `renderNodes()`
- Add `pointerdown` handler on resize handle that sets a `state.resizingNodeId` flag
- In `onPointerMove`, if `state.resizingNodeId`, calculate new width/height from pointer delta (respecting min constraints)
- Update node model: `node.width`, `node.height` (default 260, undefined means 260)
- `getDocument()` / `applyDocument()` serialize/deserialize width/height with fallback defaults

**2. Property flip (new API endpoint + inline rendering)**
Why second: Self-contained addition to the node header. Needs new backend endpoint but no template changes outside canvas.

Key changes:
- New `GET /api/canvas/properties?iri=<IRI>` endpoint in `canvas/router.py`
  - Reuses `ShapesService.get_form_for_type()` for form metadata
  - Queries `urn:sempkm:current` and `urn:sempkm:inferred` for property values (same pattern as `get_object()` lines 73-110, but returns JSON, not HTML)
  - Returns `{properties: [{name, path, value, datatype, source}], type_label}`
- New flip button in node header HTML (between expand and delete buttons)
- `node.showProperties` boolean in state, toggled by flip button click
- When `showProperties === true`, `renderNodes()` replaces the markdown div with a compact property table built from cached fetch result
- Cache properties per-node in `state.propertyCache[nodeId]` to avoid re-fetching on every flip

**3. Embed infrastructure (new template + iframe node type)**
Why third: Foundation for all embed types. Must be proven before specific embed types are wired up.

Key changes:
- New `backend/app/templates/base_embed.html` — minimal: doctype, theme CSS, htmx, `{% block content %}`, no sidebar, no CDN library zoo
- `?embed=1` query parameter check in view, dashboard, and SPARQL endpoints — conditionally uses `base_embed.html` instead of `base.html`
- New embed node type in canvas state: `node.nodeType = 'embed'`, `node.embedConfig = {type, id, url}`
- `renderNodes()` renders embed nodes as a container with a header bar (title, resize handle, close button) and an `<iframe src="...">` body
- CSS for `.spatial-node-embed` — overflow hidden, iframe fills the content area below the header

**4. Embed types (view, dashboard, SPARQL, object read)**
Why fourth: Wires up specific content types into the embed infrastructure.

Key changes per type:
- **View embed**: iframe src = `/browser/views/generic/{renderer}?type={type}&embed=1`
- **Dashboard embed**: iframe src = `/browser/dashboard/{id}?embed=1`
- **SPARQL embed**: iframe src = `/browser/sparql-result/{query_id}?embed=1` (may need a new endpoint if saved query rendering isn't standalone)
- **Object read embed**: iframe src = `/browser/object/{iri}?embed=1` (needs embed mode in `get_object` to return read-only view without dockview/flip infrastructure)

**5. Embed add UX (toolbar picker + explorer drag)**
Why fifth: The embed infrastructure must work before the add UX is built.

Key changes:
- Toolbar "Add embed" button → dropdown/modal with content type tabs (Views, Dashboards, Queries, Objects)
- Each tab fetches available items from existing API endpoints (`/api/dashboard/list`, `/browser/views/available`, `/api/sparql/saved`)
- Clicking an item creates an embed node at center of viewport
- Explorer drag extension: views, dashboards, queries in explorer sidebar get `draggable="true"` with appropriate `__canvasDragPayload` metadata
- Canvas `onDrop`/`onDragEnd` detect embed payloads (by checking `payload.type`) and create embed nodes instead of object nodes

**6. Persistence + E2E + Docs**
Why last: Verification and documentation after all features work.

Key changes:
- Verify `getDocument()` serializes all new fields, `applyDocument()` deserializes with defaults
- Verify save/load round-trip with mixed node types
- E2E tests: resize persists, property flip shows data, embed renders in iframe, save/load with embeds
- User guide page for canvas features

### Verification Approach

**Resize**: Open canvas, add a node, resize it to 500px wide, save canvas, reload page, verify node is still 500px wide. Check that edges connect correctly to resized nodes.

**Property flip**: Add a typed object (e.g., a Note with properties) to canvas. Click flip button. Verify SHACL-derived properties appear in a table. Click flip again to return to markdown.

**Embeds**: Place a Table View on canvas via toolbar picker. Verify iframe loads with real data. Verify rows are clickable inside the iframe. Place a dashboard, verify context filtering works. Save canvas with embeds, reload, verify all embeds restore.

**Persistence**: Create a session with mixed node types (2 regular objects resized, 1 property-flipped, 1 view embed, 1 dashboard embed). Save. Reload the page. Verify all node sizes, states, and embeds restore correctly.

**Backend tests**: Unit tests for the new `/api/canvas/properties` endpoint (mock ShapesService + triplestore). Unit tests for embed URL construction.

**E2E**: Playwright tests for resize interaction, property flip toggle, embed placement, save/load round-trip.

## Constraints

- **No external resize library** — CSS `resize: both` or custom pointer-event handlers only. The codebase is vanilla JS throughout (D004 pattern).
- **No React** — canvas.js is an IIFE. All DOM is innerHTML-based. Embed nodes use `<iframe>` for isolation, not React portals.
- **Canvas document is untyped JSON** — `CanvasPutBody.document` is `dict[str, Any]`. This is both a constraint (no server-side validation) and a freedom (schema extension is zero-cost). Old documents missing `width`/`height`/`nodeType`/`embedConfig` must degrade gracefully via `applyDocument()` defaults.
- **Same-origin iframes only** — SemPKM pages served from `localhost:3000` via nginx. Cookie/session sharing works. But htmx's `hx-push-url` and `hx-target` inside iframes could cause the iframe to navigate away from the embedded content. `?embed=1` templates must NOT include `hx-push-url`.
- **base.html loads ~15 CDN scripts** — iframes using `base.html` would each load Cytoscape, dockview, CodeMirror, marked, etc. A lightweight `base_embed.html` is essential for performance.
- **Dashboard context filtering uses `document.body` event listeners** — `dashboardContextChanged` events dispatched on `document.body` inside an iframe won't bubble to the parent canvas. Dashboard embeds will have self-contained context filtering (which is correct — each embedded dashboard is independent).
- **Edge rendering uses DOM measurement** — `edgePoint()` reads `el.offsetWidth` and `el.offsetHeight` from the rendered DOM. When node sizes change (resize, property flip expanding content), edges update automatically on the next `renderNodes()` call. This is a good thing — no special edge recalculation needed.

## Common Pitfalls

- **Resize vs drag pointer event conflict** — Both resize handles and the node header use `pointerdown`. The fix is clear hit-target separation: resize handles are positioned at node edges/corners and must `stopPropagation()` on `pointerdown` to prevent the drag handler from firing. The node header area initiates drag; the resize handles initiate resize. Never both.

- **iframe navigation escape** — htmx links inside iframes (e.g., clicking an object IRI pill in a table view) could navigate the iframe to a full workspace page, breaking the embed. The `?embed=1` mode must: (a) suppress `hx-push-url`, (b) open links in the parent frame or in a new dockview tab via `window.parent.openTab()`, (c) override link click handlers to use `postMessage` or `window.parent` for cross-frame communication.

- **renderNodes() innerHTML replacement destroys iframes** — The current `renderNodes()` rebuilds `state.layer.innerHTML` on every call (every drag frame, every state change). Iframe elements recreated via innerHTML lose their loaded page state. **This is the single biggest technical risk.** Embed nodes must be rendered differently — either: (a) exempt embed nodes from innerHTML replacement by using persistent DOM elements outside the layer, or (b) split rendering into a "static layer" (iframes, persisted) and a "dynamic layer" (regular nodes, rebuilt). Option (b) is cleaner — a separate `<div>` for embed nodes that are created/moved via `style.left`/`style.top` updates rather than innerHTML replacement.

- **Property flip increases node height** — A property table with 10+ rows could be much taller than the markdown content. This changes the node's bounding box, which affects edge rendering. Since `edgePoint()` reads from the DOM, this self-corrects on the next `renderNodes()` call. But if the user has sized the node to a specific height, the property table should scroll within that height, not expand the node.

- **Embed content loading delay** — Iframes load asynchronously. The canvas should show a loading placeholder in the iframe area until the content loads. A `load` event listener on the iframe element triggers placeholder removal.

- **Max iframe count for performance** — Each iframe is a full page load. With 5+ embeds, the canvas could become sluggish. Recommend a soft limit (warn at 4, hard-cap at 8) for v1, with lazy loading (only render iframes for nodes visible in the current viewport) as a follow-up optimization if needed.

## Open Risks

- **innerHTML rebuild vs iframe persistence** — The biggest unknown. The current rendering model (`state.layer.innerHTML = nodesHtml`) destroys and recreates all DOM elements on every state change. This works fine for static HTML nodes but will destroy iframe state. The dual-layer approach (static embed layer + dynamic node layer) is the likely solution, but it adds complexity to positioning, z-ordering, and selection highlighting. This should be the first thing proven in the embed infrastructure slice.

- **htmx inside iframes** — htmx in the embedded page will try to swap elements, push URLs, and listen for events within the iframe's document. Most of this should work (same-origin), but `hx-push-url` would change the iframe's URL, potentially confusing history navigation. Need to verify that `?embed=1` pages with `hx-push-url="false"` (or no `hx-push-url` at all) work correctly for paginated table views, filter changes, and dashboard context filtering.

- **SPARQL embed rendering** — The current SPARQL console uses Yasgui CDN, which is a heavy library. A "SPARQL result" embed should probably render just the result table, not the full Yasgui editor. This may need a new endpoint (`/browser/sparql-result/{id}?embed=1`) that executes the saved query and renders the results as a plain HTML table, without Yasgui.

- **Drag-from-explorer for non-object types** — The current drag infrastructure in `tree_children.html` is tightly coupled to object IRIs. View specs, dashboard specs, and query specs are different entity types (ViewSpec IRIs, dashboard UUIDs, query URIs). The drag payload needs a `type` field to distinguish them, and the canvas drop handler needs to route accordingly. This is straightforward but touches multiple template files.

## Candidate Requirements (advisory)

These are behaviors implied by the context doc that aren't in the active requirements:

1. **CANVAS-06 (candidate): Embed max count / performance guard** — Hard limit on simultaneous embeds (e.g., 8) or performance warning. Affects UX and prevents browser tab crashes. Consider as part of CANVAS-03/04.

2. **CANVAS-07 (candidate): Iframe lazy loading** — Only render iframes for nodes visible in the current viewport. Reduces initial load for canvases with many embeds. Could be deferred to a fast-follow.

3. **CANVAS-08 (candidate): Embed link routing** — Clicking a link inside an embedded view/dashboard opens the target in a new dockview tab in the parent workspace, not inside the iframe. This is essential for usability but not explicitly stated in CANVAS-03/04.

4. **CANVAS-09 (candidate): Embed mode for object read view** — `?embed=1` on `/browser/object/{iri}` renders the read-only properties + markdown body without the flip container, form, favorites, relations panel, and lint panel. Lighter than the full object tab. Needed for CANVAS-04's "object read embed."

These are all table-stakes behaviors for the embed feature to be usable. Recommend folding them into CANVAS-03/04 acceptance criteria rather than creating separate requirements.

## Skills Discovered

No external skills are relevant. This is entirely codebase-internal work: vanilla JS canvas manipulation, FastAPI endpoint creation, Jinja2 templates, and CSS. No new libraries or frameworks needed.

## Sources

- Codebase inspection: `canvas.js` (1316 LOC), `canvas/router.py` (361 LOC), `canvas/service.py` (250 LOC), `workspace-layout.js` (604 LOC), `workspace.js` (~2900 LOC), `objects.py` (~580 LOC), `shapes.py` (~300 LOC)
- Existing decisions: D108 (dashboard_mode query param), D114 (special-panel pattern), D066 (lazy init on flip)
- Existing patterns: `__canvasDragPayload` for drag-drop, `special-panel` for non-object dockview tabs, `ShapesService.get_form_for_type()` for SHACL metadata
