# Phase 57: Spatial Canvas - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Spatial canvas becomes a productive visual thinking tool with alignment aids, rich edge display, and keyboard-driven interaction. The existing C0 prototype (canvas.js, 937 lines) already supports nodes, edges with labels, wiki-link edge detection, single-item drag-drop, pan/zoom, and named sessions. This phase enhances it with snap-to-grid, keyboard navigation, wiki-link edge visual distinction + ghost nodes, and bulk drag-drop from nav tree.

</domain>

<decisions>
## Implementation Decisions

### Snap-to-grid
- Always on — no toggle, no modifier key required
- Grid size: 24px, matching the existing CSS background grid
- All node placement snaps: manual drag, neighbor expansion (circular layout), and nav tree drag-drop
- No alignment guides or snap lines — grid snapping alone is sufficient
- Shift+Arrow for larger jumps (e.g. 5 grid steps)

### Keyboard interaction
- Arrow keys move the selected node by one grid step (24px)
- Tab / Shift+Tab cycles focus through nodes (visible focus ring on selected node)
- Escape deselects (clears focus ring and selection state)
- Delete / Backspace removes selected node immediately — no confirmation dialog
- Enter toggles neighbor expansion on the selected node
- Ctrl+S / Cmd+S saves the current canvas session (prevents browser default)

### Wiki-link edge styling
- Dashed stroke + different color (green) to distinguish from RDF edges (solid blue/accent)
- Two visual signals: line pattern AND color — clear at a glance, even zoomed out
- Edge label shows the link text from the markdown `[[display text]]`, not a generic "wiki-link" label
- Stub/ghost nodes for missing targets: when a wiki-link target isn't on canvas, show a small ghost node at the edge end
- Clicking a ghost node adds the full node card to canvas at that position (resolves the stub)
- The JS already applies a `md|` prefix and `.spatial-edge-line-markdown` class — enhance existing implementation

### Bulk drag-drop
- Depends on Phase 55 OBUI-03 (nav tree multi-select with Shift+click range / Ctrl+click toggle)
- Grid layout at drop point: 3-column grid, snapped to 24px grid positions
- Auto-discover edges: after placing nodes, fetch RDF relationships and wiki-link connections between the dropped group and render edges automatically
- Skip duplicates silently — if a node is already on canvas, don't add it again, no toast
- Soft limit with warning: confirmation dialog above 20 nodes ("Drop N nodes? This may crowd the canvas.")

### Edge labels (existing)
- Edge labels between connected nodes already implemented in canvas.js (SVG text at midpoint)
- CANV-02 success criterion is already met by existing code — may need minor polish only

### Claude's Discretion
- Focus ring styling (color, width, animation)
- Ghost node visual design (size, opacity, icon)
- Exact green color for wiki-link edges (CSS variable)
- Edge label collision/overlap handling
- Grid column count for bulk drop (3 suggested, may adjust based on node width + gap)
- Tab cycling order (DOM order vs spatial left-to-right/top-to-bottom)

</decisions>

<specifics>
## Specific Ideas

- Wiki-link ghost nodes should feel like "potential connections" — semi-transparent, inviting click to resolve
- Bulk drop auto-edge-discovery is the key value: "drop a bunch of notes and instantly see how they connect"
- Keyboard navigation should feel like navigating a diagram in Figma or Miro — arrow keys for precision, Tab to jump between elements

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `canvas.js` (937 lines): Full spatial canvas with nodes, edges, pan/zoom, sessions, expansion, wiki-link detection
- `edgePoint()` function (canvas.js:583): SVG box-edge termination for proper edge rendering
- `.spatial-edge-line-markdown` class: Already applied in JS (canvas.js:551) but no CSS styling yet
- `fetchNodeBody()` (canvas.js:132): Fetches markdown body for wiki-link parsing
- Session management (canvas.js:752-864): Save/load/list/activate/delete named sessions
- `screenToWorld()` (canvas.js:606): Coordinate conversion for drop positioning

### Established Patterns
- Inline SVG for canvas icons (avoids Lucide re-scan overhead)
- Custom MIME types for drag-drop: `text/iri` and `text/label` in dataTransfer
- `window.__canvasDragPayload` fallback for dockview tab drag interference
- `expandProvenance` map tracks which nodes were added by expansion (for clean collapse)
- Canvas document stored as JSON in UserSetting (`canvas.{id}.document`)

### Integration Points
- `tree_children.html`: Drag source — currently single-item, needs multi-item support from Phase 55
- `canvas_page.html`: Toolbar — may need keyboard shortcut hints or help tooltip
- `/api/canvas/subgraph`: Endpoint for neighbor/relationship discovery — reuse for bulk edge discovery
- `/api/canvas/body`: Endpoint for fetching markdown body (wiki-link source)
- `workspace.css` lines 2814-3081: All canvas CSS rules

</code_context>

<deferred>
## Deferred Ideas

- **tldraw-style diagramming tools** — Free-form shapes (rectangles, circles, arrows), hand-drawn mind maps with integrated notes. A substantial drawing/diagramming capability that would make the canvas a full visual thinking workspace. Belongs in its own phase.

</deferred>

---

*Phase: 57-spatial-canvas*
*Context gathered: 2026-03-10*
