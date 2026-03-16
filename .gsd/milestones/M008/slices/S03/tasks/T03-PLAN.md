---
estimated_steps: 5
estimated_files: 3
---

# T03: Toolbar embed picker

**Slice:** S03 — Live Embeds — Infrastructure, Types & Add UX
**Milestone:** M008

## Description

The primary add-UX path for embeds. An "Add embed" button in the canvas toolbar opens a tabbed dropdown with Views, Dashboards, and Queries tabs. Each tab fetches from existing list APIs and displays clickable items. Clicking an item builds an `embedConfig` and calls `addEmbedNode()` (from T02) to place the embed on the canvas.

## Steps

1. **Add "Add embed" button to canvas toolbar.** In `backend/app/templates/browser/canvas_page.html`, add a button in `.canvas-page-actions` (before or after the zoom controls): `<button class="btn-secondary canvas-embed-picker-btn" type="button" onclick="if(window.SemPKMCanvas) window.SemPKMCanvas.openEmbedPicker(this)">+ Embed</button>`. The button text should be short. Include a Lucide icon if desired (`<i data-lucide="layout-grid"></i>` or similar).

2. **Implement `openEmbedPicker(anchorEl)` function in canvas.js.** Creates or toggles a dropdown/popover positioned below the anchor button. The picker structure:
   ```html
   <div class="canvas-embed-picker">
     <div class="canvas-embed-picker-tabs">
       <button class="active" data-tab="views">Views</button>
       <button data-tab="dashboards">Dashboards</button>
       <button data-tab="queries">Queries</button>
     </div>
     <div class="canvas-embed-picker-body">
       <div class="canvas-embed-picker-loading">Loading...</div>
       <!-- Items rendered here -->
     </div>
   </div>
   ```
   On open: check if embed count >= 8, show toast and return if at limit. Otherwise, create the picker DOM (or show if already created), fetch the active tab's data, render items. Tab buttons switch the active tab and re-fetch. Click outside the picker closes it.

3. **Fetch data for each tab.** Use `fetch()` to call existing APIs:
   - **Views tab**: `GET /browser/views/available` → returns JSON array. Each item has `spec_iri` and `label`. For generic views, the URL is `/browser/views/generic/{renderer}?embed=1` where renderer is derived from the spec (table/cards/graph). For model-declared views, the URL is `/browser/views/{renderer}/{encoded_spec_iri}?embed=1` (use the existing URL patterns from the views router). Build embedConfig: `{type: 'view', id: spec_iri, url: embed_url, label: label}`.
   - **Dashboards tab**: `GET /api/dashboard` → returns JSON array. Each item has `id` and `name`. URL: `/browser/dashboard/${id}?embed=1`. Build embedConfig: `{type: 'dashboard', id: id, url: url, label: name}`.
   - **Queries tab**: `GET /api/sparql/saved` → returns JSON array. Each item has `id` and `name`. URL: `/browser/sparql-result/${id}?embed=1`. Build embedConfig: `{type: 'query', id: id, url: url, label: name}`.

4. **Render items as clickable rows.** Each item: `<div class="canvas-embed-picker-item" data-config='${JSON.stringify(config)}'>Label</div>`. On click, parse the config, call `addEmbedNode(config)` with viewport center coordinates (compute from `state.viewport.getBoundingClientRect()`, `state.translateX/Y`, `state.scale`). Close the picker. Show empty state ("No items found") when API returns empty array.

5. **Add CSS for picker.** In `frontend/static/css/workspace.css`:
   - `.canvas-embed-picker` — fixed/absolute position below the button, z-index above canvas, background, border, border-radius, box-shadow, max-height 300px with overflow-y auto, width ~280px.
   - `.canvas-embed-picker-tabs` — flex row of tab buttons, border-bottom, active state with accent color.
   - `.canvas-embed-picker-item` — padding, hover highlight, cursor pointer, text truncation.
   - `.canvas-embed-picker-loading` — centered, muted text.

## Must-Haves

- [ ] "Add embed" button visible in canvas toolbar
- [ ] Picker opens with three tabs (Views, Dashboards, Queries)
- [ ] Each tab fetches from real API and shows items
- [ ] Clicking an item places an embed node at viewport center
- [ ] Picker closes after placement
- [ ] Max 8 check prevents opening picker when at limit

## Verification

- Browser: Click "Add embed" → picker dropdown appears with "Views" tab active
- Browser: Switch to "Dashboards" tab → see dashboard items from API
- Browser: Click a dashboard item → embed node placed on canvas, picker closes, iframe loading
- Browser: With 8 embeds on canvas, click "Add embed" → toast message, no picker
- Browser: Click outside picker → picker closes without placing anything

## Inputs

- T02's `addEmbedNode(embedConfig, clientX, clientY)` function — must be available on `window.SemPKMCanvas`
- T01's embed URLs — `/browser/views/generic/{renderer}?embed=1`, `/browser/dashboard/{id}?embed=1`, `/browser/sparql-result/{id}?embed=1`
- Existing list APIs: `/browser/views/available` (views router line 50), `/api/dashboard` (dashboard router), `/api/sparql/saved` (sparql router line 463)
- `canvas_page.html` toolbar structure (`.canvas-page-actions`)

## Expected Output

- `backend/app/templates/browser/canvas_page.html` — "Add embed" button added to toolbar
- `frontend/static/js/canvas.js` — `openEmbedPicker()` function, tab switching, API fetching, item placement
- `frontend/static/css/workspace.css` — picker dropdown, tabs, items styling

## Observability Impact

- **Status bar**: `setStatus('Embed added: <label>')` fires on each successful placement — visible in `#spatial-canvas-status`.
- **Toast on limit**: `showToast('Maximum of 8 embeds reached')` fires when picker is opened at capacity — visible in toast overlay.
- **DOM inspection**: `.canvas-embed-picker` element's `style.display` indicates open/closed state. Tab buttons have `.active` class for current tab.
- **API failures**: Picker body shows "Failed to load" text when fetch fails — visible in DOM and network tab.
- **State inspection**: `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed')` returns all embed nodes with their `embedConfig`.

