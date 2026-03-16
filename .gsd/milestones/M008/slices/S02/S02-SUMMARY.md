---
id: S02
parent: M008
milestone: M008
provides:
  - GET /api/canvas/properties?iri=<IRI> endpoint returning SHACL-derived property JSON
  - build_property_list() pure-function helper for property data transformation
  - Flip button in canvas node headers toggling between markdown body and property table
  - fetchNodeProperties() + state.propertyCache in-memory cache
  - buildPropertyTable() renderer for property JSON to inline HTML
  - showProperties serialization in getDocument()/applyDocument() for save/load persistence
  - CSS styles for flip button active state and compact property table layout
requires:
  - slice: none
affects:
  - S04
key_files:
  - backend/app/canvas/router.py
  - backend/tests/test_canvas_properties.py
  - frontend/static/js/canvas.js
  - frontend/static/css/workspace.css
key_decisions:
  - D131: propertyCache is memory-only — re-fetched on session load for flipped nodes
  - D132: build_property_list extracted as pure function for direct unit testing without mocks
patterns_established:
  - Pure-function extraction pattern for complex endpoint logic in canvas router
  - Conditional body rendering in renderNodes() — check node state flag + cache availability before choosing render path
  - fetchNodeProperties follows same fetch/cache/renderNodes pattern as fetchNodeBody
observability_surfaces:
  - GET /api/canvas/properties?iri=<IRI> callable directly for debugging
  - .spatial-node-flip.is-flipped class visible in DOM for flipped nodes
  - showProperties field present in saved session JSON
  - window.SemPKMCanvas.exportState() returns serialized doc with showProperties
drill_down_paths:
  - .gsd/milestones/M008/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S02/tasks/T02-SUMMARY.md
duration: 1.75h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Property Flip on Object Nodes

**Object nodes on the spatial canvas now have a flip button that toggles between markdown body and a SHACL-derived property table fetched from a lightweight JSON endpoint, with state persisted across save/load.**

## What Happened

**T01 (Backend):** Added `GET /api/canvas/properties?iri=<IRI>` to the canvas router. The endpoint queries both `urn:sempkm:current` and `urn:sempkm:inferred` graphs, resolves types via `ShapesService.get_form_for_type()`, builds an ordered property list from SHACL form properties, appends unmatched predicates with local-name labels, tags inferred properties with `source: "inferred"`, and resolves IRI reference labels via `LabelService.resolve_batch()`. Body properties excluded (both `urn:sempkm:body` and SHACL body detection). Core logic extracted into `build_property_list()` pure function — all 26 unit tests are pure-function tests with zero mocking.

**T02 (Frontend):** Added flip button between expand and delete in the node header with `is-flipped` active state CSS. Click handler toggles `node.showProperties` and calls `fetchNodeProperties()` on first flip (following the existing `fetchNodeBody` fetch/cache/renderNodes pattern). `buildPropertyTable()` renders type label header + compact prop-row label/value pairs with multi-value pill formatting, boolean ✓/✗, and empty-state dashes. `showProperties` serialized in `getDocument()` (only when true) and restored in `applyDocument()` with auto-fetch for flipped nodes on reload. CSS: button group inclusion, accent color active state, property table layout with overflow-y auto, `flex-shrink: 0` per project convention.

## Verification

- **Unit tests:** `pytest tests/test_canvas_properties.py -v` — 26/26 passed (0.49s)
- **Browser: flip button visible** — `.spatial-node-flip` in header between expand and delete
- **Browser: click toggles** — markdown → property table → markdown
- **Browser: property table** — type header, rows for title/description/created/creator, body excluded
- **Browser: active state** — `.is-flipped` has accent color
- **Browser: save/load** — saved session, reloaded, node restored with property table re-fetched
- **Browser: old session compat** — new node without showProperties defaults to markdown, no JS errors
- **Browser assertions** — 8/8 PASS (selector_visible × 5, text_visible × 3)

## Requirements Advanced

- CANVAS-02 — Fully implemented: flip button, SHACL-derived property table with real triplestore values, inline rendering, save/load persistence. Ready for validation.

## Requirements Validated

- CANVAS-02 — Property flip on canvas object nodes: flip button toggles between markdown body and SHACL-derived property table. Properties fetched via lightweight `/api/canvas/properties` endpoint. Compact label/value table rendered inline. Flip back returns to markdown. 26 unit tests + 8 browser assertions confirm functionality, persistence, and backward compatibility.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None — plan followed exactly across both tasks.

## Known Limitations

- Property cache is memory-only — flipped nodes re-fetch properties on every page reload (by design, keeps session JSON small)
- No E2E Playwright tests yet — deferred to S04 per milestone roadmap
- No user guide documentation yet — deferred to S04 per milestone roadmap

## Follow-ups

- none — S03 (live embeds) and S04 (E2E tests + docs) are already planned in the roadmap

## Files Created/Modified

- `backend/app/canvas/router.py` — Added imports, `build_property_list()` helper, `get_node_properties()` endpoint, constants
- `backend/tests/test_canvas_properties.py` — New file with 26 unit tests across 9 test classes
- `frontend/static/js/canvas.js` — Added propertyCache, SVG_FLIP, flip button, conditional property table, buildPropertyTable(), flip handler, fetchNodeProperties(), showProperties serialization
- `frontend/static/css/workspace.css` — Added .spatial-node-flip to button group, .is-flipped active state, property table styles

## Forward Intelligence

### What the next slice should know
- The property flip is entirely inline (no iframe) — contrast with S03's embed nodes which use iframes. The conditional rendering in `renderNodes()` (check `node.showProperties && cache`) is a new pattern that S03 should be aware of when adding embed node rendering conditions.
- `state.propertyCache` is keyed by `nodeId`, not by IRI. If the same object appears on multiple canvases, each canvas has its own cache.

### What's fragile
- `renderNodes()` now has three rendering paths for the node body: (1) showProperties + cached → property table, (2) showProperties + no cache → loading state / will render after fetch, (3) default → markdown. The `fetchNodeProperties` callback calls `renderNodes()` again which rebuilds innerHTML. This is the same pattern as `fetchNodeBody` but any changes to the innerHTML rebuild in S03 (dual-layer rendering) must account for both fetch callbacks.

### Authoritative diagnostics
- `GET /api/canvas/properties?iri=<IRI>` — callable directly, returns full JSON shape including type_label and property array. Invalid IRI → 400, unknown IRI → empty properties array.
- `document.querySelectorAll('.spatial-node-flip.is-flipped').length` — count of currently flipped nodes in DOM.

### What assumptions changed
- No assumptions changed. The SHACL property discovery via `ShapesService.get_form_for_type()` worked exactly as expected. The `fetchNodeBody` pattern was directly reusable for `fetchNodeProperties`.
