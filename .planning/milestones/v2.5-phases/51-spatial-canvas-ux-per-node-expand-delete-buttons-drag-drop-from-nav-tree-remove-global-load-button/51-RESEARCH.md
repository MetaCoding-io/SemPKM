# Phase 51: Spatial Canvas UX - Research

**Researched:** 2026-03-08
**Domain:** Spatial canvas UX (vanilla JS, HTML5 drag-drop, session management)
**Confidence:** HIGH

## Summary

This phase refines the spatial canvas from a prototype with hardcoded demo nodes and global toolbar actions into a polished interactive experience. The work spans four domains: (1) per-node controls (expand/delete/collapse buttons in node headers), (2) HTML5 drag-drop from the nav tree to the canvas, (3) expand-with-provenance tracking for scoped collapse, and (4) named session management replacing the current single-canvas-id persistence.

The existing codebase provides strong foundations. `canvas.js` already has `mergeSubgraph()` with circular layout, `screenToWorld()` for coordinate conversion, `loadNeighbors()` calling `/api/canvas/subgraph`, and `setStatus()` for feedback. The workspace panel drag-drop pattern in `workspace.js` (lines 1585-1618) demonstrates the HTML5 drag-drop approach used throughout the app. The `CanvasService` stores documents as JSON in `UserSetting` rows keyed by `canvas.{canvas_id}.document` -- extending this to named sessions is straightforward.

**Primary recommendation:** Implement in three waves -- (1) node controls + empty canvas, (2) drag-drop from nav tree, (3) named sessions. Each wave is independently testable and the code changes are well-isolated.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Expand (+) and delete (x) buttons placed in header row, right-aligned alongside title
- Both buttons always visible (not hover-only)
- Replace text "Expand"/"Collapse" toggle with chevron icon (rotates) left of title
- Delete (x) removes node immediately with no confirmation -- canvas-only removal, not RDF deletion
- Only leaf items (individual objects) are draggable -- type header nodes are not
- New node appears at exact drop coordinates (screen-to-world conversion)
- Canvas shows drop zone highlight while dragging over it
- "Already on canvas" toast for duplicate drops
- Clicking (+) loads 1-hop neighbors via existing `/api/canvas/subgraph` endpoint
- (+) is a toggle: expand loads neighbors, second click collapses (removes those neighbors)
- Collapse is scoped: only removes nodes loaded by THAT specific expand action
- Track expand provenance per node
- Empty canvas shows blank with centered hint: "Drag items from the nav tree to start exploring"
- Remove hardcoded demo nodes entirely
- Remove global "Load Neighbors" and "Load" toolbar buttons
- Named sessions: "Save" becomes "Save as..." dialog with session name prompt
- Session dropdown in toolbar to switch between saved sessions
- Auto-restore last active session on canvas open

### Claude's Discretion
- Exact icon choices for (+), (x), and chevron from Lucide icon set
- Circular layout radius and spacing for expanded neighbors
- Toast notification duration and styling
- Session dropdown component styling and positioning
- How to handle "unsaved changes" case when switching sessions

### Deferred Ideas (OUT OF SCOPE)
- None
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (IIFE) | ES5/ES6 | Canvas logic | Existing `canvas.js` pattern, no framework |
| HTML5 Drag and Drop API | native | Nav tree to canvas | Used by workspace panel drag (workspace.js:1585) |
| Lucide Icons | current | Node control icons | Already used throughout the app |
| htmx | current | Template loading | Nav tree uses htmx for lazy-load children |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | current | Session list/CRUD endpoints | New API routes for named sessions |
| SQLAlchemy (UserSetting) | current | Session persistence | Extend existing `canvas.{id}.*` key pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTML5 Drag and Drop | Custom pointer events | HTML5 DnD already used in workspace, consistent |
| UserSetting JSON | Dedicated Canvas table | Over-engineering for key-value canvas docs |

## Architecture Patterns

### Existing Code Structure (canvas.js)
```
frontend/static/js/canvas.js     # All canvas logic (IIFE, ~611 lines)
frontend/static/css/workspace.css # Canvas styles (lines 2887-3065)
backend/app/canvas/router.py     # API: GET/PUT /{canvas_id}, GET /subgraph
backend/app/canvas/service.py    # Persistence via UserSetting
backend/app/canvas/schemas.py    # Pydantic models
backend/app/templates/browser/canvas_page.html  # Toolbar + mount point
backend/app/templates/browser/tree_children.html # Nav tree leaf nodes
```

### Pattern 1: Per-Node Controls in renderNodes()
**What:** Add expand (+), delete (x), and chevron toggle buttons to the HTML string built in `renderNodes()` (canvas.js:218-229).
**When to use:** All node rendering goes through this single function.
**Example:**
```javascript
// In renderNodes() node HTML generation:
'<header class="spatial-node-header">',
  '<button class="spatial-node-chevron', (node.collapsed ? '' : ' is-open'), '" type="button">',
    '<i data-lucide="chevron-right"></i>',
  '</button>',
  '<span class="spatial-node-title">', escapeHtml(node.title), '</span>',
  '<button class="spatial-node-expand" type="button" title="Expand neighbors">',
    '<i data-lucide="plus"></i>',
  '</button>',
  '<button class="spatial-node-delete" type="button" title="Remove from canvas">',
    '<i data-lucide="x"></i>',
  '</button>',
'</header>',
```

### Pattern 2: Click Delegation in onLayerClick()
**What:** Extend the existing `event.target.closest('.class')` pattern in `onLayerClick()` to handle new button clicks.
**When to use:** All interactive elements within the canvas layer.
**Example:**
```javascript
// In onLayerClick():
var deleteBtn = event.target.closest('.spatial-node-delete');
if (deleteBtn) {
  var nodeEl = deleteBtn.closest('.spatial-node');
  var nodeId = nodeEl.dataset.nodeId;
  removeNode(nodeId);
  return;
}

var expandBtn = event.target.closest('.spatial-node-expand');
if (expandBtn) {
  var nodeEl = expandBtn.closest('.spatial-node');
  var nodeId = nodeEl.dataset.nodeId;
  toggleExpand(nodeId);
  return;
}
```

### Pattern 3: Expand Provenance Tracking
**What:** Track which nodes were loaded by each expand action so collapse can be scoped.
**When to use:** Every expand action stores provenance; collapse uses it to determine which nodes to remove.
**Example:**
```javascript
// Add to state:
// expandProvenance: { [expandedNodeId]: [childNodeId1, childNodeId2, ...] }
state.expandProvenance = {};

function toggleExpand(nodeId) {
  if (state.expandProvenance[nodeId]) {
    // Collapse: remove only nodes loaded by this expand
    var toRemove = state.expandProvenance[nodeId].filter(function(childId) {
      // Only remove if no other expand also loaded this node
      var otherSources = Object.keys(state.expandProvenance).filter(function(k) {
        return k !== nodeId && state.expandProvenance[k].indexOf(childId) >= 0;
      });
      return otherSources.length === 0;
    });
    state.nodes = state.nodes.filter(function(n) { return toRemove.indexOf(n.id) < 0; });
    state.edges = state.edges.filter(function(e) {
      return toRemove.indexOf(e.source) < 0 && toRemove.indexOf(e.target) < 0;
    });
    delete state.expandProvenance[nodeId];
    renderNodes();
  } else {
    // Expand: load neighbors and track provenance
    expandNode(nodeId);
  }
}
```

### Pattern 4: HTML5 Drag-Drop from Nav Tree
**What:** Add `draggable="true"` to `.tree-leaf` elements and handle `dragstart`/`dragover`/`drop` between nav tree and canvas.
**When to use:** Cross-component drag from sidebar nav tree to canvas viewport.
**Example:**
```javascript
// In tree_children.html, add to .tree-leaf:
// draggable="true" ondragstart="event.dataTransfer.setData('text/iri', '{{ obj.iri }}'); event.dataTransfer.setData('text/label', '{{ obj.label }}')"

// In canvas.js, on the viewport:
state.viewport.addEventListener('dragover', function(e) {
  if (e.dataTransfer.types.indexOf('text/iri') >= 0) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    state.viewport.classList.add('canvas-drop-active');
  }
});

state.viewport.addEventListener('drop', function(e) {
  e.preventDefault();
  state.viewport.classList.remove('canvas-drop-active');
  var iri = e.dataTransfer.getData('text/iri');
  var label = e.dataTransfer.getData('text/label');
  if (!iri) return;
  if (findNode(iri)) {
    setStatus('Already on canvas');
    if (window.showToast) window.showToast('Already on canvas');
    return;
  }
  var world = screenToWorld(e.clientX, e.clientY);
  state.nodes.push({ id: iri, title: label, uri: iri, x: world.x, y: world.y, markdown: '', collapsed: false });
  renderNodes();
});
```

### Pattern 5: Named Sessions via UserSetting Keys
**What:** Extend `CanvasService` to support listing, creating, and switching named sessions.
**When to use:** Session management endpoints.
**Key pattern:** Use `canvas.sessions.index` key to store a JSON array of `{id, name, updated_at}` entries. Each session document stored at `canvas.{session_id}.document` as before.
**Example:**
```python
# New methods on CanvasService:
async def list_sessions(self, user_id, db) -> list[dict]:
    """Return all session metadata for a user."""
    row = await db.execute(
        select(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.key == "canvas.sessions.index",
        )
    )
    setting = row.scalar_one_or_none()
    if not setting:
        return []
    return json.loads(setting.value)

async def save_session_as(self, user_id, name, document, db) -> str:
    """Create a new named session, return its ID."""
    session_id = str(uuid.uuid4())[:8]
    # Save document
    await self.save_document(user_id, session_id, document, db)
    # Update index
    sessions = await self.list_sessions(user_id, db)
    sessions.append({"id": session_id, "name": name, "updated_at": datetime.now(tz=timezone.utc).isoformat()})
    await self._upsert_setting(db, user_id, "canvas.sessions.index", json.dumps(sessions))
    # Track active session
    await self._upsert_setting(db, user_id, "canvas.active_session", session_id)
    await db.commit()
    return session_id
```

### Anti-Patterns to Avoid
- **Nested `setTimeout` for drag feedback:** Use CSS transitions and class toggles for drop zone highlights, not JS timeouts.
- **Storing provenance in the DOM:** Keep provenance in `state.expandProvenance` (JS object), not as `data-*` attributes. The DOM is rebuilt on every `renderNodes()` call.
- **Drag-drop with `mousedown`/`mousemove`:** Use the native HTML5 DnD API (`dragstart`/`dragover`/`drop`) for cross-component drag. The canvas already uses `pointerdown`/`pointermove` for node dragging and panning -- mixing in custom drag-from-nav would conflict.
- **Inline Lucide icon styles:** Per CLAUDE.md, always size Lucide icons via CSS with `flex-shrink: 0`, never inline `style="width:..."`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular layout | Custom math | Existing `mergeSubgraph()` angle/radius pattern | Already tested, handles deduplication |
| Screen-to-world coords | Custom transform math | Existing `screenToWorld()` function | Already accounts for pan/zoom state |
| Toast notifications | Custom toast system | Existing `window.showToast()` | Already available from workspace.js |
| Node deduplication | Manual array search | Existing `findNode()` + `existingNodeIds` pattern in `mergeSubgraph()` | Handles edge dedup too |
| Canvas persistence | New DB table | Existing `UserSetting` key-value store | `CanvasService` already handles upsert pattern |

**Key insight:** The existing canvas code already has 80% of the building blocks. The main new work is wiring them together (per-node expand calls `loadNeighbors` logic for a specific node), adding provenance tracking (new `state.expandProvenance` object), and extending the persistence layer for named sessions.

## Common Pitfalls

### Pitfall 1: Lucide Icons Not Rendering After innerHTML Rebuild
**What goes wrong:** `renderNodes()` rebuilds `state.layer.innerHTML` on every frame. Lucide's `createIcons()` must be called after each rebuild to replace `<i data-lucide="...">` with `<svg>`.
**Why it happens:** Lucide scans the DOM once on page load. New elements inserted via `innerHTML` are not auto-processed.
**How to avoid:** Call `lucide.createIcons({nameAttr: 'data-lucide'})` at the end of `renderNodes()`, scoped to the canvas layer. Alternatively, inline SVG strings directly in the HTML (avoids the Lucide replacement step entirely and is faster for high-frequency renders).
**Warning signs:** Icon placeholders visible as empty `<i>` elements or text.
**Recommendation:** Use inline SVG strings for the 3 small icons (chevron, plus, x) rather than `data-lucide` attributes. This avoids the Lucide re-scan on every render and is more performant for a canvas that re-renders on every drag frame.

### Pitfall 2: HTML5 Drag-Drop dataTransfer Types Are Lowercase
**What goes wrong:** `dataTransfer.setData('text/IRI', ...)` becomes `text/iri` in some browsers. Type strings are lowercased per spec.
**Why it happens:** HTML5 DnD spec normalizes MIME-like type strings.
**How to avoid:** Always use lowercase type strings: `text/iri`, `text/label`.
**Warning signs:** `getData()` returns empty string despite `setData()` being called.

### Pitfall 3: Drag-Drop Conflicts with Canvas Panning
**What goes wrong:** Dropping from the nav tree onto the canvas triggers both the `drop` event AND the `pointerup` handler, causing unexpected pan state.
**Why it happens:** HTML5 DnD and Pointer Events are separate systems but can fire on the same gesture.
**How to avoid:** In `onPointerDown()`, check if the event originated from a drag operation and bail early. The `dragover` event calls `e.preventDefault()` which tells the browser to handle it as a drop, not a pointer interaction. The key is that `pointerdown` fires on the canvas viewport but the drag source is in the nav tree -- so the pointerdown on the canvas during a drag-over is actually fine because the user isn't clicking, they're dragging.
**Warning signs:** Canvas pans after a drop or viewport gets stuck in `is-panning` state.

### Pitfall 4: Scoped Collapse with Shared Nodes
**What goes wrong:** Node A expands and loads nodes [C, D]. Node B expands and loads nodes [D, E]. Collapsing A removes D, breaking B's expand state.
**Why it happens:** Multiple expands can load the same neighbor node.
**How to avoid:** Before removing a node during collapse, check if any OTHER expand provenance also references it. Only remove nodes that are exclusively "owned" by the collapsing expand.
**Warning signs:** Nodes disappear unexpectedly when collapsing one node's expansion.

### Pitfall 5: Session Save Race Condition
**What goes wrong:** User clicks "Save as..." then quickly switches sessions. The save completes after the switch, overwriting the new session's state.
**Why it happens:** Async save + async session switch without guards.
**How to avoid:** Disable the session dropdown while a save is in progress. Use a simple boolean flag `state.isSaving`.
**Warning signs:** Session content appears to "swap" or "merge" unpredictably.

### Pitfall 6: Provenance Not Persisted
**What goes wrong:** User expands node A, saves canvas, reloads. The provenance tracking is lost -- collapse no longer works correctly.
**Why it happens:** `state.expandProvenance` is JS-only runtime state, not included in `getDocument()`.
**How to avoid:** Include `expandProvenance` in the canvas document JSON. Add it to both `getDocument()` and `applyDocument()`.
**Warning signs:** After reload, the (+) button shows "expand" state for nodes that were already expanded.

## Code Examples

### Node Removal (Delete Button)
```javascript
function removeNode(nodeId) {
  state.nodes = state.nodes.filter(function(n) { return n.id !== nodeId; });
  state.edges = state.edges.filter(function(e) {
    return e.source !== nodeId && e.target !== nodeId;
  });
  // Clean up provenance: remove this node from any expand's child list
  Object.keys(state.expandProvenance).forEach(function(key) {
    state.expandProvenance[key] = state.expandProvenance[key].filter(function(id) {
      return id !== nodeId;
    });
  });
  // Also remove this node's own provenance if it was expanded
  delete state.expandProvenance[nodeId];
  renderNodes();
}
```

### Per-Node Expand (Reusing loadNeighbors Logic)
```javascript
async function expandNode(nodeId) {
  var node = findNode(nodeId);
  if (!node) return;
  try {
    var response = await fetch('/api/canvas/subgraph?root_uri=' + encodeURIComponent(node.uri) + '&depth=1');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    var data = await response.json();

    // Track which nodes are new (for provenance)
    var existingIds = {};
    state.nodes.forEach(function(n) { existingIds[n.id] = true; });
    var newNodeIds = [];

    // Position new nodes around the expanded node (not viewport center)
    var newNodes = (data.nodes || []).filter(function(n) { return n.id && !existingIds[n.id]; });
    newNodes.forEach(function(newNode, idx) {
      var angle = (idx / Math.max(newNodes.length, 1)) * Math.PI * 2;
      var radius = 200;
      state.nodes.push({
        id: newNode.id,
        title: newNode.label || newNode.id,
        uri: newNode.id,
        x: Math.round(node.x + Math.cos(angle) * radius),
        y: Math.round(node.y + Math.sin(angle) * radius),
        markdown: '',
        collapsed: false,
      });
      newNodeIds.push(newNode.id);
    });

    // Merge edges (reuse dedup pattern from mergeSubgraph)
    // ... same edge dedup as mergeSubgraph ...

    state.expandProvenance[nodeId] = newNodeIds;
    renderNodes();
    setStatus('Expanded ' + newNodeIds.length + ' neighbors');
  } catch (error) {
    setStatus('Expand failed', true);
  }
}
```

### Empty Canvas Hint (in canvas_page.html)
```html
<div id="spatial-canvas-root" class="spatial-canvas-root" data-canvas-id="default">
  <div class="spatial-canvas-viewport">
    <div class="spatial-canvas-layer"></div>
    <div class="spatial-canvas-hint" id="canvas-hint">
      Drag items from the nav tree to start exploring
    </div>
  </div>
</div>
```
```css
.spatial-canvas-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--color-text-faint);
  font-size: 15px;
  pointer-events: none;
  z-index: 1;
}
```
```javascript
// In renderNodes(), toggle hint visibility:
var hint = document.getElementById('canvas-hint');
if (hint) hint.style.display = state.nodes.length > 0 ? 'none' : '';
```

### Inline SVG for Performance (Instead of Lucide data-lucide)
```javascript
// Small inline SVGs avoid Lucide re-scan on every renderNodes() call
var SVG_CHEVRON = '<svg class="spatial-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>';
var SVG_PLUS = '<svg class="spatial-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>';
var SVG_X = '<svg class="spatial-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
```

### Session List API Endpoint
```python
@router.get("/sessions/list")
async def list_canvas_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: CanvasService = Depends(get_canvas_service),
):
    """List all named canvas sessions for the current user."""
    sessions = await service.list_sessions(user.id, db)
    active = await service.get_active_session_id(user.id, db)
    return {"sessions": sessions, "active_session_id": active}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded demo nodes in JS | Empty canvas + drag-drop | Phase 51 | Real user content only |
| Global "Load Neighbors" prompt | Per-node expand (+) button | Phase 51 | Contextual, no URI prompt |
| Single canvas per user | Named sessions | Phase 51 | Multiple views of knowledge graph |
| Text "Expand"/"Collapse" toggle | Rotating chevron icon | Phase 51 | Compact, standard tree-toggle UX |

## Open Questions

1. **Edge persistence for manually-added nodes**
   - What we know: Drag-drop adds nodes but no edges. The subgraph API returns edges between nodes.
   - What's unclear: Should dropping a node automatically fetch its edges to existing canvas nodes?
   - Recommendation: Do NOT auto-fetch edges on drop. Only the expand (+) action fetches edges. Users can manually expand the dropped node if they want connections. This keeps the interaction predictable.

2. **Session name uniqueness**
   - What we know: Sessions stored as JSON array in `canvas.sessions.index`
   - What's unclear: Should session names be unique per user?
   - Recommendation: Allow duplicate names (append session ID for disambiguation). Simpler, no validation needed.

3. **Canvas ID transition**
   - What we know: Current code uses `data-canvas-id="default"` and `state.canvasId = 'default'`
   - What's unclear: How to transition from the fixed "default" canvas to named sessions
   - Recommendation: On first load, if no sessions exist but a "default" canvas document exists, auto-migrate it as the first named session (e.g., "My Canvas"). Set it as active.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (Chromium) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test --project=chromium -g "canvas"` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P51-01 | Per-node expand loads neighbors | e2e | `npx playwright test --project=chromium -g "canvas expand"` | No - Wave 0 |
| P51-02 | Per-node delete removes node | e2e | `npx playwright test --project=chromium -g "canvas delete"` | No - Wave 0 |
| P51-03 | Drag-drop from nav tree adds node | e2e | `npx playwright test --project=chromium -g "canvas drag"` | No - Wave 0 |
| P51-04 | Empty canvas shows hint text | e2e | `npx playwright test --project=chromium -g "canvas hint"` | No - Wave 0 |
| P51-05 | Named session save/load | e2e | `npx playwright test --project=chromium -g "canvas session"` | No - Wave 0 |
| P51-06 | Scoped collapse only removes expand children | e2e | `npx playwright test --project=chromium -g "canvas collapse"` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** Manual browser verification (canvas interactions)
- **Per wave merge:** Full e2e suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/canvas-ux.spec.ts` -- covers P51-01 through P51-06
- No framework install needed (Playwright already configured)

## Sources

### Primary (HIGH confidence)
- `frontend/static/js/canvas.js` -- full canvas implementation reviewed (611 lines)
- `backend/app/canvas/router.py` -- API endpoints: subgraph, get/put canvas
- `backend/app/canvas/service.py` -- persistence via UserSetting
- `backend/app/templates/browser/canvas_page.html` -- toolbar and mount point
- `backend/app/templates/browser/tree_children.html` -- nav tree leaf structure
- `frontend/static/js/workspace.js` -- drag-drop pattern (lines 1585-1618), showToast, openCanvasTab
- `frontend/static/css/workspace.css` -- canvas styles (lines 2887-3065)

### Secondary (MEDIUM confidence)
- HTML5 Drag and Drop API -- well-established browser API, used in workspace.js already
- Lucide inline SVG approach -- standard practice for high-frequency render loops

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries and patterns already exist in codebase
- Architecture: HIGH - extending existing code with well-understood patterns
- Pitfalls: HIGH - identified from direct code review of canvas.js and workspace.js

**Research date:** 2026-03-08
**Valid until:** 2026-04-07 (stable codebase, no external dependencies changing)
