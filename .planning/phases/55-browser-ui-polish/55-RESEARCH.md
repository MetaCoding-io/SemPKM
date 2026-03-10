# Phase 55: Browser UI Polish - Research

**Researched:** 2026-03-10
**Domain:** Frontend UI polish (nav tree controls, multi-select, edge inspector, VFS preview)
**Confidence:** HIGH

## Summary

Phase 55 adds polish and productivity features across two browser surfaces: the Object Browser (workspace nav tree + Relations panel) and the VFS File Browser. The Object Browser gets nav tree header actions (refresh/create), shift-click multi-select with bulk delete, and an expandable edge inspector in the Relations panel. The VFS browser gets a side-by-side raw/rendered preview mode and file operation polish (dirty indicators, loading states, consistent icons).

All work is frontend-heavy with modest backend changes. The nav tree header and multi-select are purely client-side JS/CSS additions to the existing `workspace.js` + `nav_tree.html` + `tree_children.html` templates. The edge inspector requires a new backend API endpoint to query edge provenance from event named graphs. The VFS preview is a layout change within `vfs-browser.js` reusing the existing `marked.js` + `DOMPurify` stack. Bulk delete requires a new backend endpoint since the command API has no `object.delete` command yet -- the existing `object.create.undo` compensation pattern (via `build_compensation`) provides the mechanism to remove all triples for an object.

**Primary recommendation:** Split into 4-5 plans: (1) nav tree header controls + command palette "Create" entries, (2) multi-select + bulk delete, (3) edge inspector + provenance API, (4) VFS side-by-side preview, (5) VFS file operation polish. Plans 1-2 are tightly coupled to the nav tree; plan 3 is self-contained; plans 4-5 are VFS-specific.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Nav tree header: Refresh and plus buttons in **OBJECTS section header**, right-aligned, **show on hover only** (VS Code Explorer pattern)
- Refresh does full reload: re-fetches type list and collapses all expanded children (lazy-load on click)
- Plus button opens the command palette (Ctrl+K)
- Rename existing "New Object" to **"Create new object"**; add per-type create entries ("Create Note", "Create Project", etc.) all prefixed with "Create"
- Create form opens in a **dockview tab** (not inline/overlay)
- Multi-select: **Shift-click** for range, **Ctrl+click** for toggle -- standard OS file manager pattern
- No checkboxes -- selection via **background highlight color**
- Selection **independent from tab navigation**: shift/ctrl+click selects without opening tabs; regular click opens tabs as before
- When items selected: OBJECTS section header shows **"[N selected]" count badge + trash icon** (next to refresh/plus)
- Delete confirmation: modal dialog listing selected objects -- "Delete N objects? This cannot be undone." with Cancel/Delete buttons
- Deleted objects' open tabs are **not automatically closed**
- Edge inspector: **Click to expand inline** (no navigation); separate **open icon** navigates to target
- Expanded detail shows: predicate IRI as QName, creation timestamp + author, source (user-asserted vs OWL-inferred), edge event link (opens Event Log filtered to that event)
- **Delete button** (trash icon) for user-asserted edges only (not inferred), with confirmation
- VFS preview: **Side-by-side horizontal split** (raw CodeMirror left, rendered markdown right), resize handle between
- Preview **toggled via button** in file tab bar (default off, showing only raw editor)
- Markdown uses **existing marked.js + DOMPurify** from `markdown-render.js`
- VFS file operation polish: save indicator (dot on tab when dirty, "Saved" flash), edit/read toggle (Lucide lock/unlock icon), loading states (spinner), error feedback (toast/inline)
- Inline VFS help: info section or tooltip explaining how to connect OS to WebDAV endpoint

### Claude's Discretion
- Exact CSS values for selection highlight, hover animations, transition timing
- Spinner implementation choice (CSS animation vs Lucide loader icon)
- Edge provenance API query strategy (single SPARQL query vs event store lookup)
- VFS help text content and placement (tooltip, collapsible section, or info banner)
- Modal dialog styling and animation

### Deferred Ideas (OUT OF SCOPE)
- Full Driver.js guided tour for VFS setup -- a tutorial is a new capability, belongs in its own phase. Inline help text is in scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBUI-01 | Nav tree header has a refresh button to reload the object list | Extend `explorer-section-header` in `workspace.html`; JS handler re-fetches `/browser/tree` htmx partial. Existing `loadTree()` pattern in VFS browser for reference. |
| OBUI-02 | Nav tree header has a plus button to jump to create new object flow | Plus button calls `showTypePicker()` (already exists in `workspace.js`). Per CONTEXT: opens command palette instead. Add per-type "Create X" entries to `ninja.data`. |
| OBUI-03 | User can select multiple objects via shift-click in the nav tree | Add multi-select state tracking in `workspace.js`. Modify `tree_children.html` onclick to support shift/ctrl modifiers. Selection highlight via CSS class `.tree-leaf.selected`. |
| OBUI-04 | User can bulk delete selected objects | New backend endpoint for object deletion (materialize all triples as deletes). Frontend calls it for each selected IRI (or single batch endpoint). |
| OBUI-05 | Clicking a relationship in Relations panel expands to show edge provenance | New backend API endpoint to query edge provenance from event graphs. Frontend converts `relation-item` from simple click-to-open to expandable detail with inline metadata display. |
| VFSX-01 | VFS browser shows side-by-side view for open files with raw content and rendered markdown preview | Modify `vfs-browser.js` `openFile()` to create horizontal split layout. Reuse `marked.js` + `DOMPurify` for rendering. Add resize handle between panes. |
| VFSX-02 | VFS browser file operations are polished (consistent icons, loading states) | Modify `vfs-browser.js` toolbar: replace text edit/save buttons with Lucide lock/unlock icons, add spinner states, add toast notifications for save success/failure. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| htmx | (existing CDN) | Nav tree reload, relation panel updates | Already drives all DOM updates in workspace |
| ninja-keys | (existing CDN) | Command palette extension with "Create X" entries | Already loaded in workspace.html |
| Lucide | (existing CDN) | Icons for all new buttons (refresh-cw, plus, trash-2, lock, unlock, loader, etc.) | Already used throughout; CLAUDE.md has specific sizing rules |
| marked.js | (existing CDN) | VFS markdown preview rendering | Already loaded globally; used by `markdown-render.js` and `vfs-browser.js` |
| DOMPurify | (existing CDN) | Sanitize rendered markdown HTML | Already loaded globally; used alongside marked.js |
| CodeMirror 6 | (esm.sh CDN) | VFS raw editor pane | Already dynamically imported in `vfs-browser.js` |
| Split.js | (existing CDN) | VFS preview resize handle (or custom implementation) | Already used for workspace pane resizing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rdflib (Python) | (existing) | Edge provenance SPARQL queries | Backend API for edge inspector metadata |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom resize handle for VFS preview | Split.js | VFS browser already has its own custom resize handle (`initResize()`); extending that pattern is simpler than adding Split.js to the VFS page |
| Native confirm() for delete dialog | Custom modal | CONTEXT says "modal dialog" -- use a styled HTML modal for consistency, not browser native confirm() |
| Separate delete endpoints per object | Batch endpoint | Batch is better -- a single POST that accepts an array of IRIs avoids N sequential requests |

## Architecture Patterns

### Recommended Project Structure

No new files needed beyond existing structure. All changes go into existing files:

```
backend/app/
  browser/router.py           # New endpoints: /browser/edge-provenance/, /browser/objects/delete
  commands/handlers/           # (optional: new object_delete.py if creating a formal command)
  events/query.py              # Query for edge creation events
  templates/browser/
    nav_tree.html              # Section header buttons
    tree_children.html         # Multi-select data attributes
    properties.html            # Expandable relation items with provenance detail
    workspace.html             # (minor: section header structure)
frontend/static/
  js/workspace.js              # Multi-select state, bulk delete, edge inspector, command palette entries
  js/vfs-browser.js            # Side-by-side preview, file operation polish
  css/workspace.css            # Selection highlight, edge detail expansion, modal dialog
  css/vfs-browser.css          # Side-by-side layout, icon polish, help banner
```

### Pattern 1: Nav Tree Header Actions (Hover-Reveal)

**What:** Add refresh and plus buttons to the OBJECTS section header that appear on hover.
**When to use:** Extending the explorer section header pattern.
**Example:**
```html
<!-- workspace.html: extend explorer-section-header -->
<div class="explorer-section-header" draggable="true"
     onclick="this.parentElement.classList.toggle('expanded')">
    <i data-lucide="grip-vertical" class="panel-grip"></i>
    <span class="explorer-section-chevron">&#9656;</span>
    <span class="explorer-section-title">OBJECTS</span>
    <!-- NEW: hover-reveal action buttons -->
    <span class="explorer-header-actions" id="objects-header-actions">
        <span class="selection-badge" id="selection-badge" style="display:none">
            <span id="selection-count"></span>
        </span>
        <button class="panel-btn explorer-action-btn" id="bulk-delete-btn"
                onclick="event.stopPropagation(); bulkDeleteSelected()"
                title="Delete selected" style="display:none">
            <i data-lucide="trash-2"></i>
        </button>
        <button class="panel-btn explorer-action-btn"
                onclick="event.stopPropagation(); refreshNavTree()"
                title="Refresh">
            <i data-lucide="refresh-cw"></i>
        </button>
        <button class="panel-btn explorer-action-btn"
                onclick="event.stopPropagation(); openCommandPalette()"
                title="New Object">
            <i data-lucide="plus"></i>
        </button>
    </span>
</div>
```
```css
/* Hover-reveal pattern (VS Code style) */
.explorer-header-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    margin-left: auto;
    opacity: 0;
    transition: opacity 0.15s;
}
.explorer-section-header:hover .explorer-header-actions,
.explorer-header-actions:has(.selection-badge:not([style*="display:none"])) {
    opacity: 1;
}
```

### Pattern 2: Multi-Select State Machine

**What:** Track selected tree-leaf items using a Set, with shift-click for range and ctrl-click for toggle.
**When to use:** Multi-select in the nav tree.
**Key considerations:**
- Selection state is purely client-side (a `Set<string>` of IRIs)
- Regular click (no modifier) opens tab as before AND clears selection
- Shift-click: select range from last-clicked to current (requires ordered item list)
- Ctrl-click: toggle individual item in/out of selection
- The `lastClickedLeaf` reference tracks the anchor for shift-ranges
- Selected items get `.selected` CSS class (distinct from `.active` which means "open in tab")

```javascript
// Multi-select state
var selectedIris = new Set();
var lastClickedLeaf = null;

function handleTreeLeafClick(e, iri, label) {
    if (e.shiftKey && lastClickedLeaf) {
        // Range select: all items between lastClickedLeaf and this
        selectRange(lastClickedLeaf, iri);
    } else if (e.ctrlKey || e.metaKey) {
        // Toggle individual
        toggleSelection(iri);
        lastClickedLeaf = iri;
    } else {
        // Normal click: open tab, clear selection
        clearSelection();
        openTab(iri, label);
        lastClickedLeaf = iri;
    }
    updateSelectionUI();
}
```

### Pattern 3: Edge Provenance Query

**What:** Query edge creation event from event named graphs for a given subject-predicate-object triple.
**When to use:** Edge inspector expansion in the Relations panel.
**Recommendation (Claude's Discretion):** Use a single SPARQL query against event named graphs. This is more efficient than an event store lookup because we can match the triple pattern directly.

```sparql
PREFIX sempkm: <urn:sempkm:>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?event ?timestamp ?performedBy ?edgeIri WHERE {
  GRAPH ?event {
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp .
    OPTIONAL { ?event sempkm:performedBy ?performedBy }

    # Match the specific edge resource that created this triple
    ?edgeIri a sempkm:Edge ;
             sempkm:source <SUBJECT_IRI> ;
             sempkm:predicate <PREDICATE_IRI> ;
             sempkm:target <OBJECT_IRI> .
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY DESC(?timestamp)
LIMIT 1
```

For inferred edges (source = "inferred"), provenance comes from the inference engine, not from an event. Show "Inferred by OWL 2 RL reasoning" instead of event metadata.

### Pattern 4: VFS Side-by-Side Preview

**What:** Horizontal split with CodeMirror left, rendered markdown right, toggle button in tab bar.
**When to use:** VFS file tabs for `.md` files.
**Key change:** Replace the current "Preview/Source" toggle tabs (which show one OR the other) with a side-by-side layout (showing BOTH simultaneously). The existing VFS browser already has Preview/Source tabs -- this replaces that mutually-exclusive view with a simultaneous split.

```javascript
// In openFile(), replace the viewTabsHtml and panel layout:
// Instead of separate preview/source views, create a split container
var splitHtml =
    '<div class="vfs-split-container" id="vfs-split-' + _pathId(path) + '">' +
    '  <div class="vfs-split-left">' +
    '    <div class="vfs-cm-container" id="vfs-cm-' + _pathId(path) + '"></div>' +
    '  </div>' +
    '  <div class="vfs-split-handle"></div>' +
    '  <div class="vfs-split-right" style="display:none">' +
    '    <div class="vfs-preview-container" id="vfs-preview-' + _pathId(path) + '">' +
    '      <div class="markdown-body"></div>' +
    '    </div>' +
    '  </div>' +
    '</div>';
```

### Anti-Patterns to Avoid

- **event.stopPropagation() missing on header buttons:** The section header has an `onclick` that toggles expand/collapse. All buttons inside MUST call `event.stopPropagation()` or the section will collapse on every button click.
- **Inline styles on Lucide icons:** Per CLAUDE.md, always size Lucide icons via CSS with `flex-shrink: 0`, never inline `style="width:Xpx"`.
- **Selection state leaking across tree reloads:** When the nav tree is refreshed (htmx partial swap), all DOM elements are replaced. The `selectedIris` Set persists in JS, but DOM classes are lost. Re-apply `.selected` class after htmx swap using `htmx:afterSwap` listener.
- **Hardcoded setTimeout for VFS split resize:** Use the existing drag pattern from `initResize()` in `vfs-browser.js`.
- **Buttons inside `<label>` elements:** Firefox silently strips them (per CLAUDE.md / MEMORY.md).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom markdown parser | `marked.js` + `DOMPurify` (already loaded globally) | Consistent with object read view; handles edge cases |
| Command palette | Custom dropdown/modal | `ninja-keys` (already in workspace.html) | Keyboard-driven, fuzzy search, extensible `data` array |
| Object deletion | Custom SPARQL DELETE | Extend the compensation/undo pattern from `EventQueryService.build_compensation()` | Maintains event-sourced audit trail; deletion is just "undo all creation events" |
| Modal dialog | Browser `confirm()` | Custom HTML modal with CSS | CONTEXT specifies modal dialog with Cancel/Delete buttons and styled listing |
| Icon library | Custom SVGs | Lucide icons (already loaded) | Consistent with entire UI; just use `data-lucide="icon-name"` |
| Resize handle | CSS `resize` property | Custom drag handler (existing pattern in VFS browser) | CSS `resize` doesn't work well in flex layouts; custom drag is already proven in codebase |

**Key insight:** This phase is almost entirely about extending existing patterns. Every major capability (htmx partials, Lucide icons, ninja-keys, marked.js, event compensation) already exists in the codebase. The work is wiring them together with new UI interactions.

## Common Pitfalls

### Pitfall 1: Object Delete Without Event Source
**What goes wrong:** Deleting objects via raw SPARQL DELETE bypasses the event store, breaking the immutable audit log.
**Why it happens:** The command API has no `object.delete` command. Tempting to just run SPARQL DELETE.
**How to avoid:** Create a proper `object.delete` operation type that uses `materialize_deletes` to remove all triples for the object from `urn:sempkm:current`. This creates an event graph with full audit trail.
**Warning signs:** No event_iri returned from the delete operation.

### Pitfall 2: Shift-Click Range Selection Across Type Groups
**What goes wrong:** Shift-click between items in different type groups (e.g., selecting from a Note to a Project) is ambiguous -- which items are "between" them?
**Why it happens:** Tree leaves are nested under type nodes; there's no single flat ordered list.
**How to avoid:** Flatten all visible `.tree-leaf` elements into an ordered array using `document.querySelectorAll('#section-objects .tree-leaf')`. The DOM order IS the visual order. Shift-click selects all leaves between the two indices regardless of type group boundaries.
**Warning signs:** Selection skips items or selects wrong range.

### Pitfall 3: htmx Partial Swap Destroys Selection State
**What goes wrong:** When a type node's children are loaded via htmx (`hx-trigger="click once"`), the innerHTML is replaced. Any `.selected` class applied to existing leaves is lost.
**Why it happens:** htmx swaps replace DOM elements; JS Set persists but DOM is new.
**How to avoid:** Listen for `htmx:afterSwap` on the nav tree container. After any swap, re-apply `.selected` class to all `.tree-leaf` elements whose IRI matches the `selectedIris` Set.
**Warning signs:** Selection visually disappears after expanding a type node.

### Pitfall 4: Edge Provenance Query Returns No Results for Direct Triples
**What goes wrong:** The relations panel currently queries direct triples (`<subject> ?predicate ?object`) in `urn:sempkm:current`. But event graphs store edge RESOURCES (with `sempkm:Edge` type, `sempkm:source`, `sempkm:target`, `sempkm:predicate`). A direct triple in the current graph was materialized from an edge resource.
**Why it happens:** Confusion between the edge resource IRI and the materialized triple.
**How to avoid:** The provenance query must search for edge resources in event graphs, NOT for the direct triple. Search for `?edge sempkm:source <subject>; sempkm:predicate <predicate>; sempkm:target <object>`. Note: the current relations SPARQL queries `<subject> ?predicate ?object` directly -- these are NOT edge resources. The relations endpoint needs enhancement to also return the predicate IRI (not just label) and the full subject/object IRIs to support the provenance lookup.
**Warning signs:** Provenance query returns empty results for edges that clearly exist.

### Pitfall 5: VFS Preview Not Updating After Edits
**What goes wrong:** User edits markdown in CodeMirror, but the side-by-side preview stays stale.
**Why it happens:** The preview is rendered once on file open, not on every keystroke.
**How to avoid:** Add a debounced `EditorView.updateListener` that re-renders the markdown preview when `update.docChanged` fires. Use 300ms debounce to avoid performance issues on large files.
**Warning signs:** Preview content doesn't match editor content after typing.

### Pitfall 6: Relations Panel Doesn't Pass IRI Data for Provenance Lookup
**What goes wrong:** The current `properties.html` template renders relation items with `onclick="openTab('iri', 'label')"` but doesn't include the predicate IRI, subject IRI, or source in the DOM. The edge inspector needs all of these for the provenance API call.
**Why it happens:** The template was designed for simple click-to-navigate; data attributes for subject, predicate, target, and source were never needed.
**How to avoid:** Extend the template to include `data-subject-iri`, `data-predicate-iri`, `data-target-iri`, and `data-source` attributes on each relation item.
**Warning signs:** Edge inspector click handler has no IRI data to query.

## Code Examples

### Nav Tree Refresh (htmx-based)
```javascript
// Source: existing pattern in workspace.js initCommandPalette + VFS browser loadTree
function refreshNavTree() {
    var body = document.querySelector('#section-objects .explorer-section-body');
    if (!body) return;
    // Clear selection state on refresh
    selectedIris.clear();
    lastClickedLeaf = null;
    updateSelectionUI();
    // htmx reload of nav tree partial
    htmx.ajax('GET', '/browser/nav-tree', { target: body, swap: 'innerHTML' });
}
```

### Bulk Delete via Event Store
```python
# Source: based on build_compensation pattern in events/query.py
# New endpoint in browser/router.py
@router.post("/objects/delete")
async def bulk_delete_objects(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
):
    body = await request.json()
    iris = body.get("iris", [])
    operations = []
    for iri in iris:
        # Query all triples for this object in current graph
        # Build materialize_deletes for each
        op = Operation(
            operation_type="object.delete",
            affected_iris=[iri],
            description=f"Deleted object: {iri}",
            data_triples=[],  # event graph records the deletion
            materialize_inserts=[],
            materialize_deletes=triples_to_delete,
        )
        operations.append(op)
    event_result = await event_store.commit(operations, performed_by=user_iri)
    return JSONResponse({"event_iri": str(event_result.event_iri)})
```

### Command Palette Per-Type Create Entries
```javascript
// Source: based on existing initCommandPalette pattern in workspace.js
// After initial ninja.data setup, fetch types and add "Create X" entries
fetch('/browser/types')
    .then(function(r) { return r.json(); })
    .then(function(types) {
        types.forEach(function(type) {
            ninja.data = ninja.data.concat([{
                id: 'create-' + type.label.toLowerCase().replace(/\s+/g, '-'),
                title: 'Create ' + type.label,
                section: 'Objects',
                handler: function() {
                    // Open create form in dockview tab
                    var panelId = '__create-' + type.iri + '-' + Date.now();
                    window._tabMeta[panelId] = { label: 'Create ' + type.label };
                    window._dockview.api.addPanel({
                        id: panelId,
                        component: 'object-editor',
                        params: { createType: type.iri },
                        title: 'Create ' + type.label
                    });
                }
            }]);
        });
    });
```

### Edge Inspector: Expandable Relation Item
```html
<!-- Source: extending properties.html relation-item pattern -->
<div class="relation-item" data-subject-iri="{{ object_iri }}"
     data-predicate-iri="{{ predicate_iri }}" data-target-iri="{{ obj.iri }}"
     data-source="{{ obj.source }}">
    <span class="relation-arrow">&#8594;</span>
    <span class="relation-item-label">{{ obj.label }}</span>
    {% if obj.source == "inferred" %}
    <span class="inferred-badge">inferred</span>
    {% endif %}
    <button class="relation-open-btn panel-btn" onclick="event.stopPropagation(); openTab('{{ obj.iri }}', '{{ obj.label }}')" title="Open in tab">
        <i data-lucide="external-link"></i>
    </button>
</div>
<div class="relation-detail" style="display:none">
    <!-- Loaded on click via fetch to /browser/edge-provenance/ -->
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| VFS Preview/Source toggle tabs | Side-by-side simultaneous display | Phase 55 | Users see rendered output while editing |
| Single-click-only nav tree | Shift/Ctrl multi-select | Phase 55 | Enables batch operations on objects |
| Simple click-to-navigate relations | Expandable inline edge inspector | Phase 55 | Full provenance visibility without leaving context |
| Text "Edit"/"Read" buttons in VFS | Lucide lock/unlock icons | Phase 55 | Consistent icon-based UI across workspace |

**Current state of object deletion:** There is no `object.delete` command or endpoint in the codebase. The only way to "delete" is to undo the `object.create` event via the Event Log's Undo button. Phase 55 introduces proper bulk delete.

## Open Questions

1. **Edge provenance for pre-edge-resource triples**
   - What we know: Edges created via `edge.create` command are first-class resources with `sempkm:Edge` type. The event graph contains the edge resource triples.
   - What's unclear: What about properties set during `object.create` or `object.patch` that create direct triples (not edge resources)? These appear in the Relations panel but have no corresponding `sempkm:Edge` resource.
   - Recommendation: For non-edge-resource triples, search event graphs for the direct triple in `data_triples`. For these, show the event timestamp and author but label them as "property-based relationship" rather than "edge". This covers both edge resources and direct property triples.

2. **Types list endpoint for command palette**
   - What we know: `nav_tree.html` receives `types` from the workspace route context. The `/browser/type-picker` endpoint exists but returns HTML.
   - What's unclear: No JSON endpoint for type list exists.
   - Recommendation: Either add a simple `/browser/types.json` endpoint, or extract type data from the existing nav tree DOM (each `.tree-node` has `data-type-iri` attribute + label in `.tree-label` span). DOM extraction is simpler and avoids a new endpoint.

3. **Delete confirmation modal pattern**
   - What we know: The codebase uses `window.confirm()` for undo confirmation (`sempkmUndoEvent`).
   - What's unclear: No existing custom modal dialog component exists in the codebase.
   - Recommendation: Create a minimal reusable `showConfirmDialog(title, message, onConfirm)` function that renders a styled HTML modal. This can be used for bulk delete and edge delete confirmations. Use `<dialog>` element for native focus trapping and escape-to-close behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (Chromium project) |
| Config file | `/home/james/Code/SemPKM/e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "PATTERN" -x` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBUI-01 | Nav tree refresh button reloads objects | manual-only | Visual verification via playwright-cli | N/A - UI polish, verify interactively |
| OBUI-02 | Plus button opens command palette with Create entries | manual-only | Visual verification via playwright-cli | N/A - UI polish, verify interactively |
| OBUI-03 | Shift-click selects range in nav tree | manual-only | Visual verification via playwright-cli | N/A - JS interaction, verify interactively |
| OBUI-04 | Bulk delete removes selected objects | smoke | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium --grep "delete" -x` | Likely no existing test |
| OBUI-05 | Edge inspector expands with provenance | manual-only | Visual verification via playwright-cli | N/A - UI polish, verify interactively |
| VFSX-01 | VFS side-by-side preview | manual-only | Visual verification via playwright-cli | N/A - VFS not in existing test suite |
| VFSX-02 | VFS consistent icons and loading states | manual-only | Visual verification via playwright-cli | N/A - UI polish, verify interactively |

### Sampling Rate
- **Per task commit:** Interactive verification via playwright-cli (open browser, navigate, test interactions)
- **Per wave merge:** `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -x` (ensure no regressions)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- this phase is UI polish with primarily manual/interactive verification. Existing e2e test infrastructure is sufficient. No new test files or framework setup needed. The existing test suite covers the base functionality (nav tree navigation, object creation, etc.) that this phase extends. Regression testing via the full suite is the primary safety net.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `workspace.html`, `workspace.js`, `workspace.css`, `nav_tree.html`, `tree_children.html`, `properties.html`, `event_log.html`, `vfs-browser.js`, `vfs-browser.css`, `vfs_browser.html`, `markdown-render.js`
- Backend analysis: `browser/router.py` (relations endpoint, event detail, undo), `commands/router.py` (command API), `commands/schemas.py` (command types), `commands/handlers/edge_create.py` (edge model), `events/store.py` (Operation dataclass), `events/query.py` (EventQueryService, compensation), `events/models.py` (event metadata predicates), `rdf/namespaces.py` (SEMPKM namespace)

### Secondary (MEDIUM confidence)
- CONTEXT.md user decisions -- all implementation choices locked by user

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- all patterns extend existing codebase patterns with clear integration points
- Pitfalls: HIGH -- identified from direct codebase analysis (htmx swap behavior, edge resource model, Firefox label restriction)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable -- no external dependency changes expected)
