# Phase 51: Spatial Canvas UX - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve spatial canvas node interactions: add per-node expand/delete buttons, enable drag-drop from nav tree to canvas, implement named session management, and remove the global Load Neighbors button. The canvas already works for panning, zooming, node dragging, and edge rendering — this phase refines the UX for adding, removing, and exploring nodes.

</domain>

<decisions>
## Implementation Decisions

### Node Controls
- Expand (+) and delete (x) buttons placed in the header row, right-aligned alongside the title
- Both buttons are always visible (not hover-only) — works on touch devices too
- Replace the text "Expand"/"Collapse" toggle with a chevron icon (rotates) placed left of the title
- Delete (x) removes the node immediately with no confirmation — the node is only removed from the canvas view, not deleted from the RDF store

### Drag-Drop from Nav Tree
- Only leaf items (individual objects) are draggable — type header nodes are not draggable
- New node appears at the exact drop coordinates on the canvas (screen-to-world conversion)
- Canvas shows a drop zone highlight (subtle border/background change) while dragging over it
- If an object already exists on the canvas, show an "Already on canvas" toast and do not create a duplicate

### Expand Behavior
- Clicking (+) loads 1-hop neighbors via the existing `/api/canvas/subgraph` endpoint
- New neighbor nodes are positioned in a circle/arc around the expanded node (matches existing `mergeSubgraph()` circular layout pattern)
- The (+) button is a toggle: first click expands (loads neighbors), second click collapses (removes those neighbors)
- Collapse is scoped: only removes nodes that were loaded by THAT specific expand action — preserves manually-added or separately-expanded nodes
- Track expand provenance per node (which nodes came from which expand) to support scoped collapse

### Canvas Bootstrapping & Sessions
- Empty/fresh canvas shows blank canvas with centered hint text: "Drag items from the nav tree to start exploring"
- Remove hardcoded demo nodes entirely
- Remove the global "Load Neighbors" toolbar button (replaced by per-node expand)
- Remove the global "Load" toolbar button (replaced by session management)
- Named sessions: "Save" button becomes "Save as..." dialog (prompts for session name)
- Session dropdown in toolbar to switch between saved sessions
- Auto-restore last active session on canvas open

### Claude's Discretion
- Exact icon choices for (+), (x), and chevron from Lucide icon set
- Circular layout radius and spacing for expanded neighbors
- Toast notification duration and styling
- Session dropdown component styling and positioning
- How to handle the "unsaved changes" case when switching sessions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `canvas.js` `mergeSubgraph()` (line 522-571): Already implements circular layout for new nodes and edge deduplication — reuse for expand
- `canvas.js` `loadNeighbors()` (line 573-590): Calls `/api/canvas/subgraph` endpoint — reuse the fetch logic for per-node expand
- `canvas.js` `screenToWorld()`: Converts screen coordinates to world coordinates — needed for drag-drop positioning
- Workspace panel drag-drop (workspace.js:1556-1618): HTML5 drag-drop pattern — reference for nav tree drag implementation
- Lucide icon set: Already used throughout the app — use for (+), (x), chevron icons
- `workspace.css` `.panel-btn svg` block: Reference implementation for Lucide icon sizing with flex-shrink

### Established Patterns
- Node rendering: String concatenation HTML in `renderNodes()` (canvas.js:218-229) — new buttons go here
- Click delegation: `onLayerClick()` uses `event.target.closest('.class')` pattern — extend for new button clicks
- Canvas state: `state.nodes[]` and `state.edges[]` arrays — extend node model for expand provenance tracking
- Nav tree: `onclick="openTab(iri, label)"` on `.tree-leaf` elements — add `draggable="true"` and dragstart handler
- Toast/status: `setStatus(msg, isError)` already exists in canvas.js — reuse for "Already on canvas" feedback

### Integration Points
- `canvas_page.html` toolbar: Remove Load Neighbors button, add session dropdown
- `nav_tree.html` + `tree_children.html`: Add `draggable="true"` to `.tree-leaf` elements, add dragstart handler
- `canvas/router.py`: May need new endpoints for listing/managing named sessions (currently single canvas per ID)
- `canvas/service.py`: Extend to support multiple named sessions per user (currently keyed by canvas_id)
- `workspace.css`: Canvas-related styles at lines 2923-3065 — extend for new button styles, drop zone highlight

</code_context>

<specifics>
## Specific Ideas

- The expand toggle should feel like a tree node toggle — click to reveal children, click again to hide them
- Named sessions let users maintain different "views" of their knowledge graph for different purposes (e.g., "Project A relations", "Reading notes map")

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 51-spatial-canvas-ux*
*Context gathered: 2026-03-08*
