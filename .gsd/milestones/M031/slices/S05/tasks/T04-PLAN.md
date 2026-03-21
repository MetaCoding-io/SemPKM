---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T04: Full-height views and graph popover z-index fix

**Slice:** S05 — SPARQL + Ontology + Graph + Full-Height Polish
**Milestone:** M031

## Description

Two related view layout fixes: (1) Graph view and kanban view don't fill their available panel height — the graph uses a fragile `height: calc(100% - 90px)` while kanban has no height constraint at all. (2) The graph node popover gets clipped under toolbars when a node is near the top of the view, because it's absolutely positioned within `.graph-container` which creates a stacking context.

The root layout context: Dockview panels contain a `.group-editor-area` div with `width:100%; height:100%; overflow:auto` (set inline in `workspace-layout.js` line 153). View templates are loaded into this via htmx. For graph/kanban, the content needs to fill the full height without triggering an outer scroll.

## Steps

1. **Fix graph view height** — Wrap the graph view template content in a flex column. Edit `backend/app/templates/browser/graph_view.html`: add a wrapper div (e.g., `<div class="view-flex-column">`) around all template content (pills, toolbar, graph-toolbar, cy-container). In `frontend/static/css/views.css`, add:
   ```css
   .view-flex-column {
     display: flex;
     flex-direction: column;
     height: 100%;
     min-height: 0;
   }
   ```
   Change `.graph-container` from `height: calc(100% - 90px)` to `flex: 1; min-height: 0`. This lets the graph container fill whatever height remains after toolbars.

2. **Fix kanban view height** — Similarly wrap `backend/app/templates/browser/kanban_view.html` content in `.view-flex-column`. Make `.kanban-board` use `flex: 1; min-height: 0; overflow-x: auto` so it fills remaining height and scrolls horizontally for many columns.

3. **Verify table and cards views** — These views use natural vertical scrolling (the `.group-editor-area` container handles scrollbar). No flex wrapper needed. Read `backend/app/templates/browser/table_view.html` and `backend/app/templates/browser/cards_view.html` to confirm they don't need changes. If they already render fine with the outer scroll, leave them alone.

4. **Fix graph popover z-index** — The `.graph-popover` (z-index: 200) is inside `.graph-container` (position: relative), which creates a stacking context. When positioned near the top of the container, the popover overflows above the container bounds. The toolbars above `.graph-container` paint earlier in DOM order so the popover SHOULD be visible above them. The actual z-index issue is with dockview's tab chrome (which has its own high z-index). Fix by appending the popover element to `document.body` instead of inside the graph container, and use viewport-relative positioning. In `frontend/static/js/graph.js`:
   - Change popover creation (~line 313): `document.body.appendChild(popover)` instead of `container.appendChild(popover)`
   - Same for edgePopover (~line 318)
   - Update positioning math to use `container.getBoundingClientRect()` to convert from container-relative to viewport-relative coordinates
   - Set `position: fixed` on the popover (instead of `position: absolute`)
   - Add cleanup: remove the popover from body when the graph is destroyed (in the `dispose` handler or a MutationObserver)
   - Update `.graph-popover` CSS in `frontend/static/css/views.css`: change `position: absolute` to `position: fixed` and increase `z-index` to `9999`

5. **Validate layout** — Check that no `calc(100% - 90px)` remains in `.graph-container` CSS. Confirm `.view-flex-column` styles exist. Confirm popover z-index is elevated.

## Must-Haves

- [ ] Graph view fills available panel height via flex layout (no `calc(100% - 90px)`)
- [ ] Kanban view fills available panel height via flex layout
- [ ] Table and cards views are not broken by changes (still scroll naturally)
- [ ] Graph popover renders above all chrome (dockview tabs, toolbars) when near top of view
- [ ] Popover element is cleaned up when graph is destroyed

## Verification

- `grep -q "view-flex-column" frontend/static/css/views.css` — flex wrapper styles exist
- `grep -q "view-flex-column" backend/app/templates/browser/graph_view.html` — graph view uses wrapper
- `grep -q "view-flex-column" backend/app/templates/browser/kanban_view.html` — kanban view uses wrapper
- `! grep -q "calc(100% - 90px)" frontend/static/css/views.css` — fragile height calc removed from graph-container
- `grep -q "position.*fixed\|document\.body" frontend/static/js/graph.js` — popover uses fixed positioning or body attachment
- `grep -q "z-index.*9999\|z-index.*[5-9][0-9][0-9][0-9]" frontend/static/css/views.css` — elevated popover z-index

## Inputs

- `frontend/static/css/views.css` — `.graph-container` height, `.graph-popover` position/z-index, kanban styles
- `frontend/static/js/graph.js` — popover creation (~line 313), positioning (~line 393), edge popover (~line 418)
- `backend/app/templates/browser/graph_view.html` — graph view template structure
- `backend/app/templates/browser/kanban_view.html` — kanban view template structure
- `frontend/static/js/workspace-layout.js` — `.group-editor-area` inline styles (line 153, for reference only)

## Expected Output

- `frontend/static/css/views.css` — `.view-flex-column` styles, updated `.graph-container`, updated `.graph-popover`, updated kanban styles
- `frontend/static/js/graph.js` — popover appended to `document.body` with fixed positioning and cleanup
- `backend/app/templates/browser/graph_view.html` — wrapped in `.view-flex-column`
- `backend/app/templates/browser/kanban_view.html` — wrapped in `.view-flex-column`
