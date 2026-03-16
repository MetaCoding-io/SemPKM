---
id: T03
parent: S03
milestone: M008
provides:
  - Toolbar "Embed" button with tabbed dropdown picker for adding view, dashboard, and query embeds to the spatial canvas
key_files:
  - backend/app/templates/browser/canvas_page.html
  - frontend/static/js/canvas.js
  - frontend/static/css/workspace.css
key_decisions:
  - Picker is appended to an anchor <span> wrapper in the toolbar (position:relative) so it positions absolutely below the button without z-index gymnastics against the canvas layers
  - Outside-click handler uses pointerdown in capture phase (setTimeout(0) to skip the opening click) — simpler than mutation observers or focusout patterns
  - View embed URLs distinguish generic views (no target_class → /browser/views/generic/{renderer}) from model-declared views (target_class present → /browser/views/{renderer}/{spec_iri})
patterns_established:
  - openEmbedPicker/closeEmbedPicker pair with outside-click dismissal — reusable dropdown pattern for canvas toolbar
  - buildEmbedConfig(tab, item) centralizes URL construction for all three embed types
observability_surfaces:
  - Status bar shows "Embed added: <label>" on placement
  - Toast "Maximum of 8 embeds reached" on limit enforcement
  - Picker body shows "Failed to load" on API errors
  - SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed') for state inspection
duration: 25min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Toolbar embed picker

**Added "Embed" toolbar button with tabbed dropdown picker that fetches views, dashboards, and saved queries from existing APIs and places embed nodes on the canvas.**

## What Happened

Implemented the three planned changes:

1. **canvas_page.html** — Added an "Embed" button with Lucide `layout-grid` icon in the canvas toolbar, wrapped in a `<span class="canvas-embed-picker-anchor">` for positioning context.

2. **canvas.js** — Added `openEmbedPicker(anchorEl)` function that creates/toggles a tabbed dropdown with Views, Dashboards, and Queries tabs. Each tab fetches from real APIs (`/browser/views/available`, `/api/dashboard`, `/api/sparql/saved`), renders clickable items, and on click builds an `embedConfig` and calls `addEmbedNode()` with viewport center coordinates. The picker checks the max-8 embed limit before opening. Outside-click and toggle-click both close the picker. Exposed `openEmbedPicker` on the `window.SemPKMCanvas` public API.

3. **workspace.css** — Added complete picker styling: dropdown positioning, tab bar with active accent color, scrollable item body, hover highlights, text truncation, loading/empty states, and dark theme support.

## Verification

All must-haves verified in browser:

- ✅ "Embed" button visible in canvas toolbar with Lucide grid icon
- ✅ Picker opens with Views tab active, showing real data (Concepts Cards, Notes Graph, Notes Table, etc.)
- ✅ Dashboards tab fetches from API, shows "No items found" when empty
- ✅ Queries tab fetches from API, shows "No items found" when empty
- ✅ Clicking a view item places an embed node at viewport center with live iframe content — verified "Concepts Cards" embed loaded real cards view
- ✅ Picker closes after item placement
- ✅ Outside click (on sidebar) closes picker without placing anything
- ✅ Max-8 check: after adding 8 embeds, clicking Embed button shows toast and does not open picker
- ✅ `SemPKMCanvas.exportState()` returns 8 embed nodes with `nodeType: 'embed'` and `embedConfig`
- ✅ Unit tests in `test_canvas_embeds.py` all pass (URL construction, serialization, backward compat, max-embed logic)

### Slice-level checks (this task):
- ✅ Browser: place embed node via toolbar picker → iframe loads real content
- ✅ Browser: attempt 9th embed → toast rejection message
- ✅ `SemPKMCanvas.exportState()` includes `nodeType: 'embed'` and `embedConfig` for embed nodes

## Diagnostics

- **Picker state**: `document.querySelector('.canvas-embed-picker').style.display` — empty string = open, "none" = closed
- **API fetch failures**: Picker body shows "Failed to load" text; check browser network tab for 4xx/5xx
- **Embed count**: `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed').length`
- **Status bar**: `document.getElementById('spatial-canvas-status').textContent` — shows last embed action

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/canvas_page.html` — Added "Embed" button with Lucide icon in `.canvas-page-actions` toolbar
- `frontend/static/js/canvas.js` — Added `openEmbedPicker()`, `closeEmbedPicker()`, `fetchEmbedPickerTab()`, `buildEmbedConfig()` functions; exposed `openEmbedPicker` on public API
- `frontend/static/css/workspace.css` — Added `.canvas-embed-picker`, `.canvas-embed-picker-tabs`, `.canvas-embed-picker-item`, `.canvas-embed-picker-loading`, `.canvas-embed-picker-empty` styles with dark theme support
