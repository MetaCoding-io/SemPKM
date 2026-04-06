---
estimated_steps: 51
estimated_files: 1
skills_used: []
---

# T02: Body-appended hover popover on graph nodes

## Description

Add a hover popover to TBox graph nodes following the exact graph.js body-appended popover pattern (KNOWLEDGE.md: 'Popovers inside dockview panels must escape stacking context via document.body'). Shows class label, source badge, and IRI on hover. Correctly anchored via `position:fixed` + `getBoundingClientRect()`.

### Reference pattern from graph.js

The existing popover in `frontend/static/js/graph.js` (lines 430-585) establishes the proven pattern:
1. Create `div.graph-popover`, append to `document.body`
2. On `mouseover` node: start 250ms timer → build HTML → set `display:block`, position with `container.getBoundingClientRect()` + `node.renderedPosition()` + offset
3. Viewport overflow clamping: check `pRect.right > window.innerWidth - 8`, `pRect.bottom > window.innerHeight - 8`
4. On `mouseout` node: 100ms delayed hide, cancelled if mouse enters popover (`_popoverHovered` flag)
5. Popover has `mouseenter`/`mouseleave` handlers for the hover-into-popover UX
6. Cleanup: `registerCleanup()` removes popover from body

The CSS is fully reusable — `.graph-popover` in `frontend/static/css/views.css` already has `position:fixed`, `z-index:9999`, themed colors.

### Popover content for ontology nodes

Simpler than graph.js (no 'Open' button, no properties table):
- Header: class label (`.graph-popover-label`) + source badge (`.graph-popover-type`, text = source name, background-color = source color)
- Body: full IRI in monospace (`.graph-popover-iri`)
- No footer/open button — node tap already loads detail panel

## Steps

1. Read `frontend/static/js/ontology-graph.js` to find the exact location in `_renderTboxGraph()` after Cytoscape init.
2. In `_renderTboxGraph()`, after the cy instance is created:
   a. Create popover div: `var popover = document.createElement('div'); popover.className = 'graph-popover'; document.body.appendChild(popover);`
   b. Add `_popoverHovered` flag and `_hoverTimer` variable
   c. Add `mouseenter`/`mouseleave` on the popover div (same as graph.js)
3. Replace the existing `mouseover`/`mouseout` handlers on cy nodes:
   a. `mouseover`: clear any pending hide timer, start 250ms delay timer. On fire: build popover HTML, position using `container.getBoundingClientRect()` + `evt.target.renderedPosition()`, clamp to viewport, show.
   b. `mouseout`: clear hover timer, start 100ms delayed hide (check `_popoverHovered`).
4. Keep the existing `hovered` class add/remove for the size feedback (it's independent of the popover).
5. Build popover HTML:
   ```javascript
   var d = node.data();
   var html = '<div class="graph-popover-header">' +
     '<span class="graph-popover-label">' + _esc(d.label) + '</span>' +
     '<span class="graph-popover-type" style="background-color:' + d.sourceColor + '">' + _esc(d.source) + '</span>' +
   '</div>' +
   '<div style="padding:6px 14px 10px;"><span class="graph-popover-iri">' + _esc(d.id) + '</span></div>';
   ```
6. Add a simple `_esc()` HTML escaping function (same pattern as graph.js) if not already in scope.
7. In the cleanup registration, add `document.body.removeChild(popover)` to the cleanup callback.
8. Add one small CSS addition to `workspace.css`: `.tbox-graph-container .graph-popover-type` style for dynamic background-color override (the source badge needs inline `background-color` from `sourceColor` data, but the base `.graph-popover-type` has a fixed `background: var(--color-primary)` — the inline style will override correctly, but add a comment noting this intentional override).

## Must-Haves

- [ ] Popover appended to `document.body` (not inside the dockview panel)
- [ ] Positioned via `position:fixed` using `getBoundingClientRect()` + `renderedPosition()`
- [ ] Viewport overflow clamping (right edge, bottom edge)
- [ ] 250ms hover delay before showing (debounce)
- [ ] 100ms delayed hide with hover-into-popover cancellation
- [ ] Shows class label, source badge with source color, and full IRI
- [ ] `registerCleanup()` removes popover from body on panel destruction

## Verification

- `grep -q 'document.body.appendChild' frontend/static/js/ontology-graph.js && echo 'PASS: body-appended popover'`
- `grep -q 'graph-popover' frontend/static/js/ontology-graph.js && echo 'PASS: uses graph-popover class'`
- `grep -q 'getBoundingClientRect' frontend/static/js/ontology-graph.js && echo 'PASS: position:fixed anchoring'`
- `grep -q 'removeChild.*popover\|popover.*remove' frontend/static/js/ontology-graph.js && echo 'PASS: cleanup registered'`

## Inputs

- ``frontend/static/js/ontology-graph.js` — T01 output with filter functions added`
- ``frontend/static/css/views.css` — existing .graph-popover CSS (position:fixed, z-index:9999, themed colors)`

## Expected Output

- ``frontend/static/js/ontology-graph.js` — adds body-appended popover with hover delay, viewport clamping, cleanup`

## Verification

grep -q 'document.body.appendChild' frontend/static/js/ontology-graph.js && grep -q 'graph-popover' frontend/static/js/ontology-graph.js && grep -q 'getBoundingClientRect' frontend/static/js/ontology-graph.js && echo 'T02 PASS'
