---
estimated_steps: 4
estimated_files: 3
---

# T04: Explorer drag-drop for embeds

**Slice:** S03 — Live Embeds — Infrastructure, Types & Add UX
**Milestone:** M008

## Description

The secondary add-UX path. Users who see dashboards and views in the explorer sidebar should be able to drag them onto the canvas, matching the existing object drag-drop pattern via `window.__canvasDragPayload`. This task extends the existing `onDrop()` / `onDragEnd()` handlers to detect embed-type payloads and route them to `addEmbedNode()` instead of `addNodeFromDrag()`.

## Steps

1. **Add draggable attributes to dashboard explorer entries.** In `backend/app/templates/browser/dashboard_explorer.html`, find the dashboard tree-leaf div elements (the clickable items that open dashboards). Add `draggable="true"` attribute and an `ondragstart` handler that sets the payload:
   ```html
   ondragstart="window.__canvasDragPayload = {type:'dashboard', id:'{{ dashboard.id }}', label:'{{ dashboard.name }}', url:'/browser/dashboard/{{ dashboard.id }}?embed=1'}"
   ```
   Ensure `event.dataTransfer.setData('text/plain', '{{ dashboard.name }}')` is also set for the drag preview. The existing pattern in the codebase uses `ondragstart` on tree-leaf elements (see nav_tree children for objects) — follow the same pattern.

2. **Add draggable attributes to view explorer entries.** In `backend/app/templates/browser/views_explorer.html`, find the generic view entries (Table View, Cards View, Graph View) and saved view entries. Add `draggable="true"` and `ondragstart` handlers:
   - For generic views: `window.__canvasDragPayload = {type:'view', id:'generic-table', label:'Table View', url:'/browser/views/generic/table?embed=1'}` (similarly for cards/graph).
   - For saved views in the Saved Views folder: these are htmx-loaded from `/browser/my-views`. The template is `my_views.html`. Add draggable to each saved view entry with `{type:'view', id: spec_iri, label: name, url: '/browser/views/table/' + encodeURIComponent(spec_iri) + '?embed=1'}` (use the correct renderer from the view spec).

3. **Extend `onDrop()` and `onDragEnd()` to detect embed payloads.** In `frontend/static/js/canvas.js`, modify both handlers:
   - In `onDrop()` (line 443): After the bulk-drop check and before the `event.dataTransfer.getData('text/iri')` line, check if `payload` has a `type` field that's one of `'dashboard'`, `'view'`, `'query'`, or `'object-embed'`. If so, build an embedConfig from the payload and call `addEmbedNode(embedConfig, event.clientX, event.clientY)`. Then `window.__canvasDragPayload = null; return;`. This short-circuits before the regular `addNodeFromDrag()` call.
   - In `onDragEnd()` (line 470): Same check in the fallback path. If `payload.type` is an embed type, call `addEmbedNode()` instead of `addNodeFromDrag()`.
   - **Backward compat**: Payloads without a `type` field (or with `type` not in the embed set) fall through to existing behavior — `addNodeFromDrag(payload.iri, payload.label, ...)`. This preserves regular object drag-drop unchanged.

4. **Test backward compatibility.** Verify that existing object drag from the nav tree still works unchanged — the tree_children.html template sets `window.__canvasDragPayload = {iri: '...', label: '...'}` without a `type` field, so it should fall through to `addNodeFromDrag()`.

## Must-Haves

- [ ] Dashboard explorer entries are draggable onto canvas → creates embed node with dashboard iframe
- [ ] Generic view entries (Table, Cards, Graph) are draggable → creates embed node with view iframe
- [ ] Regular object drag from nav tree still creates normal node (backward compat)
- [ ] Embed URLs in drag payloads include `?embed=1` query parameter

## Verification

- Browser: Drag a dashboard entry from DASHBOARDS explorer section onto canvas → embed node created with dashboard iframe URL
- Browser: Drag "Table View" from VIEWS explorer section onto canvas → embed node with `/browser/views/generic/table?embed=1`
- Browser: Drag a regular object from the nav tree → normal node created (not embed)
- Browser: Verify `SemPKMCanvas.exportState()` shows correct nodeType and embedConfig for dragged embeds

## Inputs

- T02's `addEmbedNode(embedConfig, clientX, clientY)` — available in canvas.js scope
- T01's embed URLs — URL patterns for views, dashboards, SPARQL results
- Existing `onDrop()` and `onDragEnd()` handlers in canvas.js (lines 443, 470) — handle `__canvasDragPayload` with `iri`/`label` fields
- Existing explorer templates: `dashboard_explorer.html`, `views_explorer.html`
- Existing drag pattern: `tree_children.html` sets `window.__canvasDragPayload = {iri, label}` — this is the backward compat baseline

## Expected Output

- `backend/app/templates/browser/dashboard_explorer.html` — draggable attributes on dashboard entries
- `backend/app/templates/browser/views_explorer.html` — draggable attributes on view entries
- `frontend/static/js/canvas.js` — embed type detection in `onDrop()` and `onDragEnd()`, routing to `addEmbedNode()`

## Observability Impact

- **Drag payload inspection:** After dragging a view/dashboard entry, `window.__canvasDragPayload` contains `{type, id, label, url}` — inspectable in devtools console before the drop event fires
- **Embed creation signal:** `addEmbedNode()` calls `setStatus('Embed added: ...')` on the canvas status bar — visible at the bottom of the canvas after a successful embed drop
- **State inspection:** `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed')` shows all embed nodes with their embedConfig including the URL that was set by the drag payload
- **Failure visibility:** If the payload `type` field doesn't match an embed type, the drop falls through to regular `addNodeFromDrag()` — observable as a regular node appearing instead of an embed node
