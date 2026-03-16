---
id: T04
parent: S03
milestone: M008
provides:
  - Explorer drag-drop for embedding views and dashboards onto the spatial canvas
key_files:
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/browser/my_views.html
  - frontend/static/js/canvas.js
key_decisions:
  - Embed-type payloads are detected by checking payload.type against a whitelist array ['dashboard', 'view', 'query', 'object-embed'] — payloads without a type field (regular objects) fall through unchanged
  - View entries use <a> tags which are natively draggable, so ondragstart is sufficient without needing draggable="true" on div wrappers
patterns_established:
  - Drag payload convention: embed drags set {type, id, label, url} on window.__canvasDragPayload; regular object drags set {iri, label} — the type field presence/absence is the discriminator
observability_surfaces:
  - window.__canvasDragPayload inspectable in devtools during drag operations
  - Canvas status bar shows "Embed added: {label}" after successful embed drop
  - SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed') returns all embed nodes with embedConfig
duration: 30min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T04: Explorer drag-drop for embeds

**Added draggable attributes to dashboard/view explorer entries and embed-type detection in canvas onDrop/onDragEnd handlers**

## What Happened

Three template files got draggable attributes with ondragstart handlers that set `window.__canvasDragPayload` with embed-type payloads (`{type, id, label, url}`). The canvas.js `onDrop()` and `onDragEnd()` functions now check for embed-type payloads between the bulk-drop check and the regular object path, routing them to `addEmbedNode()`.

Templates modified:
- `dashboard_explorer.html`: Dashboard tree-leaf divs now have `draggable="true"` and ondragstart setting dashboard embed payload with `/browser/dashboard/{id}?embed=1` URL
- `views_explorer.html`: Table View, Cards View, Graph View `<a>` entries now have `draggable="true"` and ondragstart with corresponding embed payloads
- `my_views.html`: Saved view entries now have `draggable="true"` and ondragstart with per-spec renderer URLs

Canvas.js changes:
- `onDrop()`: After bulk-drop check, new embed-type detection block checks `payload.type` against `['dashboard', 'view', 'query', 'object-embed']`. Match → `addEmbedNode()` + return. No match → falls through to regular `addNodeFromDrag()`.
- `onDragEnd()`: Same detection in the fallback path as an `else if` branch between bulk and regular handlers.

## Verification

- **Template validity:** Jinja2 parsed all three templates without error
- **Unit tests:** 13/13 tests pass in `test_canvas_embeds.py`
- **Browser — view entries draggable:** All 3 generic view entries (Table, Cards, Graph) have `draggable=true` and `ondragstart` with `embed=1` URLs and `type:'view'`
- **Browser — embed detection logic present:** Both `onDrop` and `onDragEnd` contain embed-type detection blocks confirmed via source inspection
- **Browser — backward compat:** Regular object payload `{iri, label}` correctly falls through to addNodeFromDrag (no type field = not an embed)
- **Browser — addEmbedNode works:** Programmatic addEmbed with view and dashboard configs both created embed nodes with correct embedConfig in exportState()
- **Browser — embed URLs include ?embed=1:** All embed nodes in exportState have URLs containing `embed=1`

### Slice-level verification status (T04 is final task of S03)

- ✅ `test_canvas_embeds.py` — 13/13 passed
- ✅ Browser: embed node placement via toolbar picker (T03, verified via addEmbed API)
- ✅ Browser: `SemPKMCanvas.exportState()` includes `nodeType: 'embed'` and `embedConfig`
- ⬜ Browser: navigate to `/browser/views/generic/table?embed=1` — not tested this session (T01 verified)
- ⬜ Browser: drag regular node around → iframe doesn't flash/reload — requires live iframe content, deferred to integration
- ⬜ Browser: save canvas, reload → embed nodes restore — requires save endpoint interaction
- ⬜ Browser: attempt 9th embed → toast rejection — verified in T02 via unit logic
- ⬜ Browser: embed endpoints return X-Embed-Mode header — verified in T01

## Diagnostics

- **Drag payload inspection:** During a drag operation, `window.__canvasDragPayload` is inspectable in devtools — should contain `{type, id, label, url}` for embed drags
- **Embed creation confirmation:** Canvas status bar at the bottom shows "Embed added: {label}" after successful embed drop
- **State audit:** `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed')` returns all embed nodes with full embedConfig
- **Backward compat check:** Drag a regular nav-tree object → `exportState()` shows a node without `nodeType` (regular node, not embed)

## Deviations

- Also modified `my_views.html` (saved views template) — not explicitly listed in the plan's Expected Output but called out in Step 2 as the htmx-loaded template for saved views. Added draggable attributes following the same pattern.

## Known Issues

- No dashboards exist in the test environment, so dashboard drag couldn't be tested end-to-end in the browser. The template has the correct attributes and the JS detection path is verified.
- `<a>` tags in views_explorer.html have native browser link-drag behavior alongside the custom ondragstart. The custom payload takes precedence since the canvas handler reads `__canvasDragPayload` first, but the browser also adds `text/uri-list` to dataTransfer (harmless, never read).

## Files Created/Modified

- `backend/app/templates/browser/dashboard_explorer.html` — Added draggable="true" and ondragstart with embed payload to dashboard tree-leaf divs
- `backend/app/templates/browser/views_explorer.html` — Added draggable="true" and ondragstart with embed payloads to Table/Cards/Graph View entries
- `backend/app/templates/browser/my_views.html` — Added draggable="true" and ondragstart with per-spec embed payloads to saved view entries
- `frontend/static/js/canvas.js` — Added embed-type detection in onDrop() and onDragEnd() routing to addEmbedNode()
