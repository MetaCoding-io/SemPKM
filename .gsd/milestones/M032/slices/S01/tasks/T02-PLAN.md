---
estimated_steps: 5
estimated_files: 4
skills_used:
  - frontend-design
  - accessibility
  - review
---

# T02: GridStack-based dashboard builder with block palette

**Slice:** S01 — GridStack Layout Engine + Block Registry
**Milestone:** M032

## Description

Replace the current dashboard builder's block list + layout picker UI with a GridStack.js canvas and a categorized block palette. Users drag blocks from the palette onto the canvas, then position and resize them freely. The save function serializes each block's GridStack position (`x, y, w, h`) alongside its type and config.

This task depends on T01's BlockRegistry and model changes being complete.

## Steps

1. **Add GridStack.js CDN to `backend/app/templates/base.html`** — In the dev-mode CDN block (inside `{% else %}` of `asset_manifest_available`), add:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/gridstack@10/dist/gridstack-all.js"></script>
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridstack@10/dist/gridstack.min.css">
   ```
   GridStack 10.x is the current stable. `gridstack-all.js` includes drag-drop and resize handlers. Place after the existing CDN scripts, before `posthog.js`.

2. **Update `backend/app/dashboard/router.py`** — In `dashboard_builder_new()` and `dashboard_builder_edit()`, replace `valid_block_types` context with data from BlockRegistry: pass `block_types` (list of dicts with `type_name`, `label`, `icon`, `category`, `default_w`, `default_h`, `config_schema`) so the template can render a categorized palette. Remove `layout_definitions` from builder context (no longer needed — GridStack replaces the layout picker). Keep the `LAYOUT_DEFINITIONS` dict itself since it's still used by dashboard_page.html (for now — T03 will update that).

3. **Rewrite `backend/app/templates/browser/dashboard_builder.html`** — Replace the entire builder with:
   - **Header section**: Name input, description textarea (keep existing markup, no layout picker)
   - **Block palette sidebar**: Renders available block types from `block_types` context, grouped by category. Each palette item shows the Lucide icon + label, is draggable, and carries `data-type`, `data-default-w`, `data-default-h` attributes. Use HTML5 drag API or GridStack's external drag API (`GridStack.setupDragIn()`).
   - **GridStack canvas**: A `<div class="grid-stack">` container initialized as a 12-column grid. When a block is dragged from the palette, a new widget is created with the block's default size. Each widget contains a config panel (matching the existing config forms — reuse `getTypeConfigHTML()` logic). Widget header shows the block type name + a remove button.
   - **Save logic**: `_builderSave()` iterates all GridStack widgets (`grid.getGridItems()`), reads their `gs-x, gs-y, gs-w, gs-h` attributes and the config form data, serializes to the blocks array with `{type, config, x, y, w, h}` (no `slot` field for gridstack layouts), and POSTs/PATCHes to the API with `layout: "gridstack"`.
   - **Edit mode**: When `dashboard` context is set and its blocks have `x,y,w,h`, initialize GridStack with those positions. If blocks don't have positions (old format), call migration.py via a helper endpoint or handle client-side with defaults.
   - **Event isolation**: Add `mousedown`/`pointerdown` `stopPropagation()` on the GridStack container to prevent dockview from intercepting drag events. Pattern from `canvas.js` and `kanban.js`.
   - The existing config field patterns (view-embed select, class search autocomplete, markdown textarea, etc.) should be preserved inside each widget's config panel.

4. **Add CSS to `frontend/static/css/workspace.css`** — Add styles for:
   - `.dashboard-builder` layout: flex row with sidebar palette (250px) + GridStack canvas (flex: 1)
   - `.block-palette` styling: categorized list with draggable items
   - `.block-palette-item` with icon + label, hover state, cursor:grab
   - `.grid-stack` overrides for dark theme: widget background, border, handle colors matching the app's `--color-*` CSS custom properties
   - `.gs-widget .block-config-container` for config forms inside widgets
   - `.gs-widget .widget-header` with type label + remove button
   - Lucide SVGs in palette: `flex-shrink: 0` per CLAUDE.md convention

5. **Test the builder** — Open the builder in a browser, verify: palette shows all 6 block types grouped by category, dragging a block onto the canvas creates a widget, widgets can be repositioned and resized, config forms inside widgets are functional, save serializes correct `{x,y,w,h}` positions, edit mode pre-populates the canvas.

## Must-Haves

- [ ] GridStack.js loaded from CDN in dev mode
- [ ] Block palette shows all 6 types grouped by category with Lucide icons
- [ ] Dragging from palette to GridStack canvas creates a widget at the correct default size
- [ ] Widgets are repositionable and resizable on the 12-column grid
- [ ] Config forms inside widgets work (view-embed select, markdown textarea, etc.)
- [ ] Save serializes `layout: "gridstack"` and `blocks` array with `{type, config, x, y, w, h}`
- [ ] Edit mode populates GridStack with existing block positions
- [ ] GridStack drag events don't interfere with dockview panel management (stopPropagation)

## Verification

- Manual: navigate to dashboard builder → palette shows 6 block types in categories → drag markdown block onto canvas → block appears as a resizable widget → enter content in config textarea → click Save → API call succeeds with `layout:"gridstack"` and correct positions in payload
- Manual: drag and resize multiple blocks → save → re-open builder in edit mode → blocks appear at saved positions
- `grep -q "gridstack-all.js" backend/app/templates/base.html` — GridStack CDN added
- `grep -q "grid-stack" backend/app/templates/browser/dashboard_builder.html` — GridStack container present

## Inputs

- `backend/app/dashboard/registry.py` — BlockRegistry from T01 (provides block type metadata for palette)
- `backend/app/dashboard/models.py` — updated model accepting "gridstack" layout and x,y,w,h fields from T01
- `backend/app/dashboard/router.py` — current router to extend with registry context
- `backend/app/templates/browser/dashboard_builder.html` — current builder template to rewrite
- `backend/app/templates/base.html` — base template for CDN script loading
- `frontend/static/css/workspace.css` — existing CSS to extend

## Expected Output

- `backend/app/templates/base.html` — updated with GridStack.js CDN
- `backend/app/templates/browser/dashboard_builder.html` — rewritten with GridStack canvas + palette
- `backend/app/dashboard/router.py` — updated builder routes with BlockRegistry context
- `frontend/static/css/workspace.css` — extended with builder palette and GridStack theme styles

## Observability Impact

- **Console logging**: `[dashboard-builder] Saved dashboard <id> with N blocks at gridstack positions` logged on successful save; `[dashboard-builder] Save error:` on failure — visible in browser DevTools console.
- **Network**: Save action POSTs/PATCHes to `/api/dashboard` with `layout: "gridstack"` and `blocks` array containing `{x, y, w, h}` per block — inspectable in browser Network tab.
- **Inspection**: After save, `GET /api/dashboard/{id}` returns the blocks array with serialized GridStack positions.
- **Failure visibility**: `showError()` displays validation/save errors inline in the builder UI; builder-error div becomes visible with the error message.
