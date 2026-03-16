# M008: Spatial Canvas — Resizable Nodes, Property Flip & Live Embeds

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution

## Project Description

The spatial canvas is currently a graph exploration surface — users drag objects from the explorer, see their markdown bodies, and expand neighbors. This milestone transforms it into a composable working surface where nodes are resizable, can flip between markdown and properties views, and where views, dashboards, SPARQL queries, and object embeds can be placed as live interactive panels alongside regular knowledge nodes.

## Why This Milestone

**Nodes are fixed-width.** Every node is 260px wide regardless of content. A note with one sentence and a note with 2000 words render identically constrained. Users can't size nodes to match their content importance or arrange a visual hierarchy.

**No property visibility on canvas.** Nodes show the markdown body but not the structured properties (tags, dates, references, custom fields). To see an object's properties, the user must leave the canvas and open the object in a tab. This breaks the spatial flow.

**Views and dashboards can't be placed on the canvas.** SemPKM has powerful view primitives (Table, Cards, Graph) and composable dashboards, but they only render inside dockview tabs. A user who wants a table of projects alongside a graph of concept relationships alongside sticky notes must juggle multiple tabs — they can't compose a spatial workspace from these primitives.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Drag the corner/edge of any canvas node to resize it freely — width and height stored per-node, persisted across sessions
- Click a flip button on any object node to see its SHACL-derived properties table instead of the markdown body, and flip back
- Place a View (Table, Cards, Graph, or model-declared ViewSpec) on the canvas as a resizable live iframe — with full interactivity (clickable rows, filtering)
- Place a Dashboard on the canvas as a resizable live iframe — with cross-view context filtering working inside it
- Place a SPARQL query result on the canvas as a live iframe
- Place an object read view (full properties + body) on the canvas as a live iframe
- Add embeds via a toolbar picker (select content type → choose specific view/dashboard/query → click to place) or by dragging from the explorer sidebar
- Resize any embedded panel by dragging its edges/corners
- Save and restore canvas sessions with all node sizes and embedded panels preserved

### Entry point / environment

- Entry point: `http://localhost:3000/workspace` → Spatial Canvas tab
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, SQLite (canvas sessions, dashboard/workflow specs)

## Completion Class

- Contract complete means: node resize persists in canvas document JSON; property flip fetches SHACL data and renders inline; embed iframes load correct content URLs; canvas save/load preserves all new node types and sizes
- Integration complete means: embedded views show real triplestore data; dashboard context filtering works inside canvas iframes; SPARQL results render live; property flip shows correct SHACL-derived properties for the object's type
- Operational complete means: all features work after Docker restart with persisted canvas sessions

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User resizes a node to 500px wide, saves canvas, reloads — node is still 500px wide
- User flips an object node to properties view, sees SHACL-derived property table with correct values, flips back to markdown
- User places a Table View on the canvas via toolbar picker, the iframe loads with real data, rows are clickable
- User drags a dashboard from the explorer onto the canvas, it renders as a resizable iframe with live content
- Canvas session with mixed node types (regular objects, views, dashboards, SPARQL) saves and restores correctly

## Risks and Unknowns

- **iframe isolation vs CSS leakage** — Iframes provide CSS/JS isolation but add overhead. Need to verify that SemPKM's htmx pages work correctly when loaded inside an iframe within the same origin. Cookie/session sharing should work (same origin), but htmx's `hx-target` and `hx-push-url` could cause navigation issues inside the iframe. May need `?embed=1` query param to suppress chrome (sidebar, toolbar).
- **Resize interaction conflicts with drag** — Node drag already uses pointer events. Resize handles on edges/corners must not conflict with the drag-to-move behavior on the header. Clear hit-target separation needed.
- **Canvas document schema migration** — Adding `width`, `height`, `type` (object vs embed), and `embedConfig` to the node model changes the persisted JSON schema. Existing sessions need graceful fallback (missing width → use default 260px).
- **Property flip data fetching** — Need a lightweight endpoint that returns SHACL-derived property values for an IRI without the full object_tab.html template. The existing `/browser/object/{iri}` returns the full page. May need a new `/api/canvas/properties?iri=...` endpoint.
- **Performance with multiple iframes** — Each iframe is a full page load. A canvas with 5+ embedded views could be heavy. May need lazy loading (only load iframes visible in viewport) or a maximum embed count.

## Existing Codebase / Prior Art

- `frontend/static/js/canvas.js` — Current canvas implementation: 700+ LOC IIFE with pan/zoom, node drag, expand/collapse, wiki-link resolution, bulk drop, session management. Node model: `{id, title, uri, x, y, markdown, collapsed}`. Render via innerHTML replacement.
- `frontend/static/css/workspace.css` — `.spatial-node` at 260px fixed width, absolute positioning, no resize handles.
- `backend/app/canvas/router.py` — Canvas API: subgraph expansion, body fetch, wiki-link resolution, batch edges, session CRUD.
- `backend/app/canvas/service.py` — `CanvasService` persisting canvas documents as JSON in `user_settings` table.
- `backend/app/canvas/schemas.py` — Pydantic schemas for canvas API.
- `backend/app/templates/browser/canvas_page.html` — Canvas page template with toolbar (zoom, sessions, save).
- `backend/app/templates/browser/object_read.html` — Object read view with SHACL property table and rendered markdown. Reference for the property flip content.
- `backend/app/dashboard/router.py` — Dashboard rendering pipeline with CSS Grid layouts and htmx block loading.
- `frontend/static/js/workspace-layout.js` — Dockview panel factory with `special-panel` type handling for dashboards, workflows, etc.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements to be created: CANVAS-01 (resizable nodes), CANVAS-02 (property flip), CANVAS-03 (view/dashboard embeds), CANVAS-04 (SPARQL/object embeds), CANVAS-05 (embed add UX — toolbar picker + drag)
- No existing active requirements are advanced by this milestone

## Scope

### In Scope

**Resizable Nodes:**
- Free resize via drag handles (corner and/or edges) on all node types
- Width and height stored per-node in canvas document JSON
- Minimum size constraints (e.g. 160px min width)
- Existing sessions gracefully handle missing width/height (default to current 260px)

**Property Flip:**
- Flip button on object node header toggles between markdown body and properties table
- Properties fetched via new lightweight API endpoint (SHACL-derived property values for an IRI)
- Properties rendered as compact label/value table inline in the node (no iframe needed)
- Flip state optionally persisted in canvas document

**Live Embeds (Views, Dashboards, SPARQL, Objects):**
- New "embed" node type in canvas model distinct from object nodes
- Embed renders as a resizable iframe loading the target content URL
- `?embed=1` (or similar) query param suppresses page chrome (sidebar, toolbar, breadcrumbs) for iframe-friendly rendering
- Supported embed types: ViewSpec (any renderer), DashboardSpec, saved SPARQL query, object read view
- Embed config stored per-node: `{type: "view"|"dashboard"|"sparql"|"object", id: string, url: string}`

**Embed Add UX:**
- Toolbar picker: button in canvas toolbar opens a dropdown/modal to select content type → specific item → place on canvas
- Drag from explorer: views, dashboards, and other embeddable items in the explorer sidebar can be dragged onto the canvas (extending existing drag-drop infrastructure)

**Persistence:**
- Canvas document schema extended with width, height, nodeType, embedConfig
- Save/load correctly handles mixed node types
- Backward compatibility: old sessions load without errors

### Out of Scope / Non-Goals

- Drag-and-drop node resize from multiple edges simultaneously (single handle is sufficient)
- Real-time collaborative canvas editing (CRDT)
- Canvas-to-canvas linking or nesting
- Embed editing (editing a dashboard's layout from within the canvas — user must open the builder separately)
- Mobile touch gesture support for resize
- Auto-layout algorithms (force-directed, tree, etc.)
- Canvas export to image/PDF

## Technical Constraints

- Frontend: vanilla JS (no React). Canvas is an IIFE in `canvas.js`.
- CSS `resize` property or custom pointer-event drag handles — no external resize library
- Iframes must be same-origin (SemPKM pages served from the same host) for session/cookie sharing
- Canvas document JSON schema must be backward-compatible (new fields optional, old sessions still load)
- Performance: lazy-load iframes that are off-screen or provide a max embed count

## Integration Points

- **Canvas document model** — Extended node schema: `{id, title, uri, x, y, width, height, markdown, collapsed, nodeType, embedConfig, showProperties}`
- **ShapesService / object read API** — New endpoint for compact property values (SHACL-derived) to power the property flip
- **ViewSpecService** — Existing view rendering endpoints loaded inside iframes
- **DashboardService** — Existing dashboard rendering loaded inside iframes
- **SPARQL console** — Existing Yasgui or saved query rendering loaded inside iframes
- **Explorer drag-drop** — Extended to support dragging view/dashboard entries onto the canvas
- **Canvas persistence** — `CanvasService.save_document()` / `load_document()` with extended schema
- **Template rendering** — New `?embed=1` mode for view/dashboard/object templates that strips page chrome

## Open Questions

- **Embed mode template approach** — Should `?embed=1` use a separate `base_embed.html` layout (minimal: just content, no sidebar/header), or conditionally hide elements in existing templates? Separate base template is cleaner but means maintaining two layouts.
- **Resize handle visual** — CSS `resize: both` on the node container (native browser handle, bottom-right only) vs custom drag handles on all corners/edges (more flexible, more code). CSS resize is simpler and may be sufficient given free resize was chosen.
- **Max iframe count** — Should there be a hard limit on embeds (e.g. max 6) or just a performance warning? Hard limit is safer for v1.
- **Property flip caching** — Should fetched properties be cached per-node in the canvas state to avoid re-fetching on every flip? Adds complexity but reduces network calls.
