# Phase 57: Spatial Canvas - Research

**Researched:** 2026-03-10
**Domain:** Vanilla JS spatial canvas enhancement (snap-to-grid, keyboard navigation, wiki-link edges, bulk drag-drop)
**Confidence:** HIGH

## Summary

Phase 57 enhances the existing C0 spatial canvas prototype (`canvas.js`, 937 lines) with five requirement areas: snap-to-grid alignment, edge label display (already functional), keyboard navigation, bulk nav-tree drag-drop, and wiki-link edge rendering. The canvas is a framework-free vanilla JS implementation using HTML absolute positioning for nodes and inline SVG for edges, with pan/zoom via CSS transforms. All persistence uses `UserSetting` rows in SQLite.

The existing code provides strong foundations: nodes are rendered as `<article>` elements with `left/top` positioning, edges use SVG `<line>` elements with midpoint text labels, and a second-pass link detection already identifies markdown `<a href>` elements in node bodies and draws `spatial-edge-line-markdown` edges (class applied in JS but no CSS styling exists yet). The drag-drop from nav tree works via `text/iri` dataTransfer and a `__canvasDragPayload` window fallback for dockview interference.

**Primary recommendation:** Implement all five requirements as enhancements to the existing `canvas.js` IIFE -- no new libraries or frameworks needed. The main technical challenges are: (1) wiki-link resolution (converting `[[display text]]` to IRI links client-side), (2) bulk drag-drop requiring `selectedIris` exposure from workspace.js, and (3) a new backend endpoint for batch edge discovery between a set of IRIs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Snap-to-grid:** Always on, no toggle, 24px grid matching CSS background grid. All placement snaps (drag, expansion, nav tree drop). Shift+Arrow for 5-grid-step jumps.
- **Keyboard interaction:** Arrow keys move by one grid step (24px). Tab/Shift+Tab cycles focus. Escape deselects. Delete/Backspace removes node immediately (no confirm). Enter toggles expansion. Ctrl+S/Cmd+S saves session.
- **Wiki-link edge styling:** Dashed stroke + green color (distinct from solid blue RDF edges). Edge label shows link display text, not generic "wiki-link". Ghost nodes for missing targets -- small semi-transparent stubs. Click ghost to resolve (add full node). Enhance existing `md|` prefix and `.spatial-edge-line-markdown` class.
- **Bulk drag-drop:** Depends on Phase 55 OBUI-03 (multi-select -- DONE). 3-column grid layout at drop point, snapped to 24px. Auto-discover edges after placing nodes. Skip duplicates silently. Soft limit with confirm dialog above 20 nodes.
- **Edge labels:** Already implemented in canvas.js -- may need minor polish only.

### Claude's Discretion
- Focus ring styling (color, width, animation)
- Ghost node visual design (size, opacity, icon)
- Exact green color for wiki-link edges (CSS variable)
- Edge label collision/overlap handling
- Grid column count for bulk drop (3 suggested, may adjust based on node width + gap)
- Tab cycling order (DOM order vs spatial left-to-right/top-to-bottom)

### Deferred Ideas (OUT OF SCOPE)
- **tldraw-style diagramming tools** -- Free-form shapes, hand-drawn mind maps. Belongs in its own phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CANV-01 | Spatial canvas has snap-to-grid alignment | Snap function snaps x/y to multiples of 24. Applied in `onPointerMove` (node drag), `expandNode` (circular layout), `addNodeFromDrag` (nav tree drop). Grid already drawn via CSS `background-size: 24px 24px`. |
| CANV-02 | Spatial canvas shows edge labels between connected nodes | Already implemented -- `renderNodes()` second pass places `<text>` SVG elements at edge midpoints. May need minor polish for readability (background rect, collision avoidance). |
| CANV-03 | Spatial canvas has keyboard navigation support | New keyboard handler on viewport element. Arrow keys modify `node.x/y` by grid step. Tab cycling via sorted node array. Focus ring via CSS class on selected node. Ctrl+S intercepts save. |
| CANV-04 | User can multi-select objects in nav tree and drag-drop them onto canvas in bulk | `selectedIris` Set exists in workspace.js (Phase 55). Expose via `window.getSelectedIris()`. Modify `ondragstart` in `tree_children.html` to bundle multi-select. New `addNodesFromBulkDrop()` in canvas.js with 3-column grid placement + batch edge discovery via new backend endpoint. |
| CANV-05 | Wiki-links in markdown body parsed and rendered as edges with distinct styling | Pre-process body text in `renderMarkdown()` to convert `[[display text]]` to `<a href="IRI">display text</a>`. Existing second-pass link detection already draws edges for in-DOM links. Add CSS for `.spatial-edge-line-markdown` (dashed, green). Add ghost node rendering for unresolved targets. Need backend endpoint to resolve wiki-link text to IRIs. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS | ES5+ IIFE | Canvas logic | Existing pattern -- no framework, no build step |
| SVG (inline) | - | Edge rendering | Already used for edges, arrowheads, anchor dots |
| CSS Grid | - | Bulk drop layout calc | Pure math for 3-column positioning, no CSS Grid needed in DOM |
| marked.js | CDN (existing) | Markdown rendering | Already loaded, used in `renderMarkdown()` |
| DOMPurify | CDN (existing) | XSS sanitization | Already loaded, used after marked.js |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | Existing | New batch-edges endpoint | Backend API for bulk edge discovery |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla canvas | React Flow / xyflow | Would require full rewrite of 937-line IIFE; not justified for these enhancements |
| Custom wiki-link parser | marked.js extension | marked.js extensions are complex; simple regex pre-processing is cleaner and already proven in obsidian/scanner.py |

**Installation:**
No new dependencies needed. All enhancements use existing stack.

## Architecture Patterns

### Recommended Project Structure
No new files needed beyond modifying existing ones:
```
frontend/static/js/canvas.js       # Main canvas logic (all 5 requirements)
frontend/static/css/workspace.css  # Canvas CSS additions (wiki-link edges, ghost nodes, focus ring)
frontend/static/js/workspace.js    # Expose selectedIris getter for bulk drag
backend/app/canvas/router.py       # New batch-edges endpoint
backend/app/templates/browser/
  tree_children.html               # Multi-select drag payload
  canvas_page.html                 # Optional: keyboard shortcut help tooltip
```

### Pattern 1: Snap-to-Grid Function
**What:** A pure function that rounds coordinates to the nearest grid multiple.
**When to use:** Every place that sets `node.x` or `node.y`.
**Example:**
```javascript
var GRID = 24;

function snapToGrid(value) {
  return Math.round(value / GRID) * GRID;
}

// Usage in onPointerMove (node drag):
node.x = snapToGrid(world.x - state.nodeDragOffsetX);
node.y = snapToGrid(world.y - state.nodeDragOffsetY);

// Usage in expandNode (circular layout):
x: snapToGrid(model.x + Math.cos(angle) * radius),
y: snapToGrid(model.y + Math.sin(angle) * radius),

// Usage in addNodeFromDrag:
x: snapToGrid(world.x),
y: snapToGrid(world.y),
```

### Pattern 2: Keyboard Navigation via State Selection
**What:** Canvas maintains a `state.selectedNodeId` property. Keyboard events operate on the selected node.
**When to use:** All keyboard interactions.
**Example:**
```javascript
// Selection state
state.selectedNodeId = null;

function onKeyDown(event) {
  if (!state.selectedNodeId) return;
  var node = findNode(state.selectedNodeId);
  if (!node) return;

  switch (event.key) {
    case 'ArrowUp':    event.preventDefault(); node.y -= GRID; renderNodes(); break;
    case 'ArrowDown':  event.preventDefault(); node.y += GRID; renderNodes(); break;
    case 'ArrowLeft':  event.preventDefault(); node.x -= GRID; renderNodes(); break;
    case 'ArrowRight': event.preventDefault(); node.x += GRID; renderNodes(); break;
    case 'Tab':
      event.preventDefault();
      cycleSelection(event.shiftKey ? -1 : 1);
      break;
    case 'Delete':
    case 'Backspace':
      event.preventDefault();
      removeNode(state.selectedNodeId);
      state.selectedNodeId = null;
      break;
    case 'Enter':
      event.preventDefault();
      toggleExpand(state.selectedNodeId);
      break;
    case 'Escape':
      state.selectedNodeId = null;
      renderNodes();
      break;
    case 's':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        saveCanvas();
      }
      break;
  }
  // Shift+Arrow for 5-grid-step jumps
  if (event.shiftKey && event.key.startsWith('Arrow')) {
    // Already handled 1-step above; modify to 5-step when shift held
  }
}
```

### Pattern 3: Wiki-Link Pre-Processing
**What:** Regex replaces `[[display text]]` with `<a href="IRI">display text</a>` before markdown rendering.
**When to use:** In `renderMarkdown()` or as a pre-processing step in `fetchNodeBody`.
**Example:**
```javascript
// Client-side wiki-link regex (matches obsidian/scanner.py pattern)
var WIKILINK_RE = /(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]/g;

function resolveWikiLinks(markdownText, nodeIri) {
  // Replace [[target]] or [[target|alias]] with <a> tags
  // Uses a lookup map built from canvas nodes + a resolve API
  return markdownText.replace(WIKILINK_RE, function(match, target, alias) {
    var displayText = alias || target;
    var resolvedIri = findNodeByTitle(target);
    if (resolvedIri) {
      return '[' + displayText + '](' + resolvedIri + ')';
    }
    // Mark as unresolved wiki-link for ghost node rendering
    return '[' + displayText + '](wikilink:' + encodeURIComponent(target) + ')';
  });
}
```

### Pattern 4: Bulk Drag-Drop with Grid Placement
**What:** Drop handler receives array of IRIs, places them in a grid pattern, then fetches inter-node edges.
**When to use:** When `__canvasDragPayload` contains an `items` array.
**Example:**
```javascript
function addNodesFromBulkDrop(items, clientX, clientY) {
  var world = screenToWorld(clientX, clientY);
  var baseX = snapToGrid(world.x);
  var baseY = snapToGrid(world.y);
  var cols = 3;
  var colWidth = 260 + 24; // node width + 1 grid gap
  var rowHeight = 120 + 24; // estimated node height + gap

  var addedIris = [];
  items.forEach(function(item, idx) {
    if (findNode(item.iri)) return; // skip duplicates
    var col = idx % cols;
    var row = Math.floor(idx / cols);
    state.nodes.push({
      id: item.iri,
      title: item.label || 'Resource',
      uri: item.iri,
      x: snapToGrid(baseX + col * colWidth),
      y: snapToGrid(baseY + row * rowHeight),
      markdown: '',
      collapsed: false,
    });
    addedIris.push(item.iri);
    fetchNodeBody(item.iri);
  });

  if (addedIris.length > 0) {
    renderNodes();
    // Fetch edges between the dropped group
    fetchBulkEdges(addedIris);
  }
}
```

### Pattern 5: Ghost Node for Unresolved Wiki-Links
**What:** When a wiki-link target IRI is not on the canvas, render a small semi-transparent stub at the edge endpoint. Clicking resolves it to a full node.
**When to use:** In the wiki-link edge second-pass rendering.
**Example:**
```javascript
// During edge rendering, if target node not found:
if (!targetNode && href.startsWith('wikilink:')) {
  // Create a ghost node entry
  var ghostId = 'ghost:' + href;
  ghostNodes.push({
    id: ghostId,
    label: decodeURIComponent(href.replace('wikilink:', '')),
    x: sourceBox.x + sourceBox.width + 60,
    y: anchorY - 12,
    sourceId: sourceId,
  });
}
```

### Anti-Patterns to Avoid
- **Don't add a framework:** The canvas is 937 lines of vanilla JS. Adding React, Svelte, or any framework for these enhancements would require a full rewrite and break the htmx-driven architecture.
- **Don't compute wiki-link edges server-side only:** The body text is fetched client-side; wiki-link parsing must also happen client-side so edges update as nodes are added/removed.
- **Don't use `keypress` event:** Use `keydown` -- `keypress` is deprecated and doesn't fire for Arrow/Tab/Delete/Escape keys.
- **Don't snap during animation/panning:** Only snap on final placement (pointerup), not every frame during drag, to avoid jarring movement. Actually -- per the decision, snapping during drag is fine (snap in `onPointerMove`), which gives visual feedback of the grid.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wiki-link regex | Custom parser | Reuse pattern from `obsidian/scanner.py` | Proven regex: `(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]` handles aliases, headings, excludes embeds |
| Markdown rendering | Custom renderer | Existing `marked.js` + DOMPurify chain | Already loaded and working in `renderMarkdown()` |
| Multi-select state | New selection system | Existing `selectedIris` Set in workspace.js | Phase 55 already built Shift+click range and Ctrl+click toggle |
| Edge discovery | Client-side SPARQL | Backend `/api/canvas/batch-edges` endpoint | Server can efficiently query RDF store for edges between N nodes in one SPARQL query |

**Key insight:** Every requirement in this phase enhances existing code. The primary risk is modifying `canvas.js`'s rendering loop (`renderNodes()`) -- changes must preserve the two-pass rendering (nodes first, then SVG edges with DOM-measured boxes).

## Common Pitfalls

### Pitfall 1: Snap Disrupts Existing Node Positions on Load
**What goes wrong:** Loading a saved canvas where nodes were saved at non-grid-aligned positions (pre-snap sessions) causes them to jump to grid positions.
**Why it happens:** If snap is applied during `applyDocument()`, existing saved positions get rounded.
**How to avoid:** Only snap on NEW placement actions (drag, drop, keyboard move, expansion). Do NOT retroactively snap positions loaded from saved sessions. This preserves backward compatibility.
**Warning signs:** Nodes shift positions when loading an old canvas session.

### Pitfall 2: Keyboard Events Captured During Text Input
**What goes wrong:** Arrow keys and Delete/Backspace trigger canvas actions when user is typing in another element (e.g., session name prompt, search input).
**Why it happens:** Keyboard handler is too broad -- listens on `document` or `window` without checking active element.
**How to avoid:** Check `document.activeElement` -- if it's an `<input>`, `<textarea>`, or `<select>`, bail out of the keyboard handler. Only process canvas keyboard events when the canvas viewport has focus or no input is focused.
**Warning signs:** Typing in the session name prompt deletes canvas nodes.

### Pitfall 3: Dockview Swallows Drop Events for Bulk Drag
**What goes wrong:** Dockview's tab drag-drop system intercepts `drop` events before the canvas handler fires.
**Why it happens:** Known issue -- the existing code already works around this with `dragend` + `lastDragOverCanvas` fallback.
**How to avoid:** Extend the existing `__canvasDragPayload` + `dragend` fallback pattern to support multi-item payloads. Do NOT rely solely on `dataTransfer.getData()` -- use the window-level side channel.
**Warning signs:** Bulk drop silently fails, no nodes appear on canvas.

### Pitfall 4: Wiki-Link Resolution Timing
**What goes wrong:** Wiki-links are parsed before node bodies are fetched, so the link-to-IRI mapping is incomplete.
**Why it happens:** `fetchNodeBody()` is async. If rendering happens before bodies arrive, wiki-link edges won't appear until re-render.
**How to avoid:** The existing pattern already handles this -- `fetchNodeBody()` calls `renderNodes()` after updating `node.markdown`. Wiki-link edges will appear on that re-render. No additional work needed IF wiki-link parsing happens inside `renderMarkdown()`.
**Warning signs:** Wiki-link edges appear only after a manual action (not on initial load).

### Pitfall 5: Rendering Performance with Many Edges
**What goes wrong:** `renderNodes()` does a full `innerHTML` rebuild every call. With many nodes + wiki-link edges + ghost nodes, this can cause visible flicker.
**Why it happens:** The current approach is "re-render everything" -- no diffing.
**How to avoid:** For this phase, the full-rebuild approach is still fine (typical canvas has <50 nodes). If performance becomes an issue, optimize later with incremental updates. Don't prematurely optimize.
**Warning signs:** Visible flicker or lag during node drag with >30 nodes.

### Pitfall 6: selectedIris Not Exposed on Window
**What goes wrong:** `tree_children.html` `ondragstart` handler can't access the multi-select set because `selectedIris` is a closure variable in workspace.js's IIFE.
**Why it happens:** The IIFE deliberately encapsulates state.
**How to avoid:** Add `window.getSelectedIris = function() { return Array.from(selectedIris); };` to the workspace.js exports (alongside existing `window.handleTreeLeafClick` and `window.clearSelection`).
**Warning signs:** Bulk drag always sends single item.

## Code Examples

Verified patterns from existing codebase:

### Snap-to-Grid Application Points
```javascript
// Source: canvas.js lines 420-426 (onPointerMove - node drag)
// BEFORE:
node.x = Math.round(world.x - state.nodeDragOffsetX);
node.y = Math.round(world.y - state.nodeDragOffsetY);

// AFTER:
node.x = snapToGrid(world.x - state.nodeDragOffsetX);
node.y = snapToGrid(world.y - state.nodeDragOffsetY);
```

### Edge Label Already Working
```javascript
// Source: canvas.js lines 538-553 (renderNodes - edge rendering)
// This already renders edge labels as SVG <text> at midpoint:
'<text class="spatial-edge-label" x="', mx, '" y="', my, '">',
  escapeHtml(edge.label || ''), '</text>'
// CSS at workspace.css line 3203:
// .spatial-edge-label { fill: var(--color-text-muted); font-size: 11px; text-anchor: middle; }
```

### Existing Wiki-Link Edge Detection (Second Pass)
```javascript
// Source: canvas.js lines 507-534 (markdown link -> edge conversion)
// Already iterates DOM <a href> elements in rendered markdown,
// creates edges with 'md|' prefix and .spatial-edge-line-markdown class.
// CSS class IS applied but has NO styles yet -- that's CANV-05's task.
markdownEdges.push({
  id: 'md|' + sourceId + '|' + href + '|' + idx,
  source: sourceId,
  target: href,
  label: 'link',  // CANV-05: should be the display text from [[display text]]
  anchorX: anchorX,
  anchorY: anchorY,
});
```

### Multi-Select State in workspace.js
```javascript
// Source: workspace.js lines 987-1072 (Phase 55 multi-select)
var selectedIris = new Set(); // Closure variable -- not on window
// Exports on window: handleTreeLeafClick, clearSelection
// Need to add: window.getSelectedIris
```

### Drag Payload Side Channel
```javascript
// Source: tree_children.html line 13
// Single-item drag currently:
ondragstart="event.dataTransfer.setData('text/iri', '{{ obj.iri }}');
  event.dataTransfer.setData('text/label', '{{ obj.label }}');
  event.dataTransfer.effectAllowed = 'copy';
  window.__canvasDragPayload = { iri: '{{ obj.iri }}', label: '{{ obj.label }}' };"
// For bulk: check if selectedIris includes this IRI, bundle all selected items
```

### Backend Subgraph Endpoint Pattern
```python
# Source: canvas/router.py lines 46-104 (get_canvas_subgraph)
# Reuse ViewSpecService.expand_neighbors() pattern for batch edge discovery.
# New endpoint: POST /api/canvas/batch-edges
# Input: {"iris": ["iri1", "iri2", ...]}
# Output: {"edges": [{"source", "target", "predicate", "predicate_label"}]}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full-rebuild rendering | Full-rebuild rendering | N/A | Still adequate for <50 nodes; no change needed |
| Single-item drag-drop | Multi-select (Phase 55) | v2.6 Phase 55 | Enables CANV-04 bulk drop |
| No wiki-link rendering | `<a href>` detection in markdown | C0 prototype | Foundation for CANV-05 -- just needs CSS and ghost nodes |

**Deprecated/outdated:**
- None. The canvas is a recent C0 prototype with no deprecated patterns.

## Open Questions

1. **Wiki-link title-to-IRI resolution strategy**
   - What we know: The body text may contain `[[My Note Title]]` or `[[target|alias]]`. The obsidian importer regex is `(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]`. Objects on canvas already have titles. The FTS search API exists at `GET /api/search?q=...`.
   - What's unclear: Should resolution use only on-canvas nodes (fast, no API call) or also search the full knowledge base (requires API call per unique link target)?
   - Recommendation: Two-phase resolution: (1) match against on-canvas node titles first (O(n) scan, instant), (2) for unresolved links, batch-resolve via a new backend endpoint that does exact title match via SPARQL. This covers both scenarios without excessive API calls.

2. **Ghost node click resolution**
   - What we know: User decision says clicking a ghost node adds the full node at that position.
   - What's unclear: If the wiki-link text doesn't match any existing object, what happens on click? Show a toast "Object not found"? Create a new object?
   - Recommendation: Show toast "Object not found" and leave ghost node in place. Creating objects is out of scope.

3. **Tab cycling order**
   - What we know: Claude's discretion. Two options: DOM order (insertion order) or spatial order (left-to-right, top-to-bottom).
   - Recommendation: Spatial order (sorted by y then x) -- matches user's visual mental model. More intuitive than arbitrary insertion order.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.50+ (E2E) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "canvas"` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CANV-01 | Nodes snap to grid when dragged | E2E | `npx playwright test tests/17-spatial-canvas/snap-to-grid.spec.ts -x` | No -- Wave 0 |
| CANV-02 | Edge labels display between connected nodes | E2E | `npx playwright test tests/17-spatial-canvas/edge-labels.spec.ts -x` | No -- Wave 0 |
| CANV-03 | Keyboard navigation works | E2E | `npx playwright test tests/17-spatial-canvas/keyboard-nav.spec.ts -x` | No -- Wave 0 |
| CANV-04 | Bulk drag-drop from nav tree | E2E | `npx playwright test tests/17-spatial-canvas/bulk-drop.spec.ts -x` | No -- Wave 0 |
| CANV-05 | Wiki-link edges rendered with distinct styling | E2E | `npx playwright test tests/17-spatial-canvas/wiki-link-edges.spec.ts -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `npx playwright test --project=chromium --grep "canvas" -x` (canvas tests only)
- **Per wave merge:** `npx playwright test --project=chromium` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/17-spatial-canvas/` directory -- create for all canvas tests
- [ ] Test files for each requirement (5 spec files)
- [ ] Test data: need objects with wiki-links in body text for CANV-05 testing
- [ ] Note: No new framework install needed -- Playwright already configured

## Sources

### Primary (HIGH confidence)
- `frontend/static/js/canvas.js` -- Full 937-line source, all current canvas logic
- `frontend/static/css/workspace.css` lines 3001-3267 -- All canvas CSS rules
- `backend/app/canvas/router.py` -- Canvas API endpoints
- `backend/app/canvas/service.py` -- Canvas persistence service
- `backend/app/views/service.py` lines 730-776 -- `expand_neighbors()` for edge discovery
- `frontend/static/js/workspace.js` lines 987-1080 -- Multi-select state (Phase 55)
- `backend/app/templates/browser/tree_children.html` -- Drag-drop source template
- `backend/app/obsidian/scanner.py` line 32 -- Wiki-link regex pattern

### Secondary (MEDIUM confidence)
- `backend/app/services/search.py` -- FTS search that could aid wiki-link resolution
- `backend/app/templates/browser/canvas_page.html` -- Canvas page template

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing code
- Architecture: HIGH -- patterns directly match existing canvas.js structure
- Pitfalls: HIGH -- identified from actual code analysis (dockview interference, IIFE encapsulation, rendering approach)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- vanilla JS, no external dependency changes expected)