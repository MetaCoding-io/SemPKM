---
estimated_steps: 4
estimated_files: 3
skills_used:
  - frontend-design
  - make-interfaces-feel-better
---

# T03: Frontend quadrant renderer — CSS grid, drag-to-reclassify JS, dark mode

**Slice:** S01 — Eisenhower Matrix — Model Archive + Quadrant Renderer
**Milestone:** M036

## Description

Build the visual 2×2 quadrant grid and drag-to-reclassify interaction. The CSS uses a 2×2 Grid layout with axis labels along the borders. Each quadrant has a distinct color (following Eisenhower convention: green for Do First, blue for Schedule, orange for Delegate, red for Eliminate). Items are draggable between quadrants; dropping fires two `object.patch` commands (one per axis property) through the `/api/commands` endpoint.

The JS follows `kanban.js` patterns exactly: HTML5 drag events with `stopPropagation()` to prevent dockview interference, optimistic DOM move with revert on failure, toast on error.

## Steps

1. **Create `frontend/static/css/quadrant.css`** — CSS Grid layout for the quadrant board:
   - `.quadrant-board`: 2×2 CSS Grid (`grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr`), with axis labels using `::before`/`::after` pseudo-elements or dedicated `.axis-label` elements
   - `.quadrant-cell`: each cell with distinct background color (use CSS custom properties for theme support), padding, min-height for empty state, border radius
   - `.quadrant-cell-header`: quadrant label ("Do First", "Schedule", "Delegate", "Eliminate") + item count
   - `.quadrant-card`: card style matching kanban cards — border, padding, cursor:grab, hover state. Lucide icon + title text
   - `.quadrant-card.dragging`: opacity reduction during drag
   - `.quadrant-cell.drag-over`: highlight border/shadow when dragging over
   - `.axis-label-x`, `.axis-label-y`: axis labels positioned along grid edges ("Urgency →", "↑ Importance")
   - Dark mode support via `[data-theme="dark"]` selectors or CSS variables from the existing theme system
   - Use `.view-flex-column` wrapper pattern (from KNOWLEDGE.md) for full-height in dockview panels
   - SVG icons: `flex-shrink: 0; stroke: currentColor` per CLAUDE.md rules

2. **Create `frontend/static/js/quadrant.js`** — drag-to-reclassify module:
   - IIFE pattern matching kanban.js
   - `initQuadrant(boardEl)` function: attach dragstart/dragend to `.quadrant-card` elements, attach dragover/dragleave/drop to `.quadrant-cell` bodies
   - `onDragStart(e)`: set dataTransfer with IRI, add `.dragging` class, `e.stopPropagation()` to prevent dockview interference
   - `onDragEnd(e)`: remove `.dragging` class
   - `onDragOver(e)`: `preventDefault()`, `stopPropagation()`, add `.drag-over` class to cell
   - `onDragLeave(e)`: remove `.drag-over` only if cursor truly left (check `e.currentTarget.contains(e.relatedTarget)` per KNOWLEDGE.md pattern)
   - `onDrop(e)`: extract target cell's `data-x-value` and `data-y-value` attributes, compare with source cell, skip if same cell. Call `patchQuadrant()` with both axis values.
   - `patchQuadrant(iri, xPredicate, yPredicate, newXValue, newYValue, cardEl, targetCell, sourceCell, boardEl)`: optimistic DOM move (append card to target cell body), update cell counts, fire `fetch('/api/commands', ...)` with `object.patch` command containing both axis properties. On success: dispatch `sempkm:command-executed`. On failure: revert card to source, show toast.
   - `_updateCellCounts(boardEl)`: update `.quadrant-cell-count` span text for each cell
   - Export `window.initQuadrant = initQuadrant`
   - Scope sync listener for `sempkm:scope-changed` (same pattern as kanban.js)

3. **Update `quadrant_view.html` template** (created in T02) to reference the CSS and JS:
   - Add `<link rel="stylesheet" href="/css/quadrant.css">` (follows nginx path convention per KNOWLEDGE.md — no `/static/` prefix)
   - Structure: `.quadrant-board` container with `data-x-predicate` and `data-y-predicate` attributes storing the axis property IRIs
   - Each `.quadrant-cell` has `data-x-value` and `data-y-value` attributes
   - Axis labels positioned around the grid edges
   - Boot script at bottom: `(function() { function _boot() { initQuadrant(document.querySelector('.quadrant-board')); } if (typeof initQuadrant === 'function') { _boot(); } else { var s = document.createElement('script'); s.src = '/js/quadrant.js'; s.onload = _boot; document.head.appendChild(s); } })();` — lazy-load pattern per KNOWLEDGE.md (htmx swap of `<script src>` races)

4. **Verify visually** — Start the Docker stack, install the business-planning model, create seed data, open the quadrant view. Check: 4 quadrants render, items are in correct cells, drag works, dark mode works, dockview doesn't interfere with drags.

## Must-Haves

- [ ] 2×2 CSS Grid layout with 4 visually distinct quadrant cells
- [ ] Axis labels ("Urgency →", "↑ Importance") positioned around the grid
- [ ] Quadrant labels ("Do First", "Schedule", "Delegate", "Eliminate") with item counts
- [ ] Drag-to-reclassify updates both axis properties via object.patch command
- [ ] `stopPropagation()` on all drag events to prevent dockview interference
- [ ] `dragleave` flicker prevention via `contains(relatedTarget)` check
- [ ] Optimistic DOM move with revert on API failure
- [ ] Dark mode support via CSS variables
- [ ] JS uses `/js/quadrant.js` path (not `/static/js/`) per nginx convention
- [ ] CSS uses `/css/quadrant.css` path (not `/static/css/`) per nginx convention
- [ ] Lazy-load script pattern in template (not bare `<script src>`)

## Verification

- `test -f frontend/static/js/quadrant.js && test -f frontend/static/css/quadrant.css && echo OK`
- `rg 'stopPropagation' frontend/static/js/quadrant.js | wc -l` returns >= 3 (dragstart, dragover, drop)
- `rg 'contains.*relatedTarget' frontend/static/js/quadrant.js` returns at least 1 match (dragleave flicker fix)
- `rg 'object.patch' frontend/static/js/quadrant.js` returns at least 1 match
- `rg '/css/quadrant.css' backend/app/templates/browser/quadrant_view.html` — path uses `/css/` not `/static/css/`
- Visual: Docker stack with model installed shows 4 quadrants with correct layout

## Inputs

- `backend/app/templates/browser/quadrant_view.html` — base template from T02 to finalize
- `frontend/static/js/kanban.js` — reference drag-drop pattern (188 lines)
- `frontend/static/css/workspace.css` — reference for theme variables and existing view styles
- `backend/app/templates/browser/kanban_view.html` — reference template structure (38 lines)

## Observability Impact

- **JS console.error** on drag-patch failure: `"quadrant: failed to patch for <IRI> <error>"` — visible in browser devtools and E2E console log capture
- **Custom event** `sempkm:command-executed` dispatched on successful patch — downstream listeners (sync, scope) can react
- **Visual feedback**: `.dragging` class on source card (opacity 0.5), `.drag-over` class on target cell (dashed border highlight) — both are inspectable via DOM
- **Failure state**: on API error the card reverts to source cell + toast notification — visible without devtools
- **Cell counts** update optimistically on drop — `querySelectorAll('.quadrant-cell-count')` shows current distribution

## Expected Output

- `frontend/static/js/quadrant.js` — drag-to-reclassify module with dockview isolation
- `frontend/static/css/quadrant.css` — 2×2 grid layout with dark mode support
- `backend/app/templates/browser/quadrant_view.html` — finalized template with CSS/JS references and lazy-load boot
