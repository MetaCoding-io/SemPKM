---
id: S04
parent: M014
milestone: M014
provides:
  - reference-picker.js ES module with search-as-you-type, debounce, type filtering, selection, clear
  - Two-step save flow in popup: object.create → edge.create for each selected reference
  - Custom event bridge (sempkm:reference-field-added) for multi-value reference field initialization
  - CSS for suggestions dropdown, items, states, clear button in popup.css
requires:
  - slice: S01
    provides: api-client.js (searchObjects, createEdge methods)
  - slice: S02
    provides: shacl-renderer.js (.reference-field DOM structure with data-target-class, multi-value add)
affects:
  - S05
key_files:
  - extension/shared/reference-picker.js
  - extension/popup/popup.js
  - extension/popup/popup.css
  - extension/shared/shacl-renderer.js
key_decisions:
  - Edge failures caught per-edge with warning toast showing failure count — never blocks object success
  - Custom event sempkm:reference-field-added dispatched from shacl-renderer (bubbles) — decouples renderer from picker module
  - searchInput readOnly on selection to prevent accidental edits; clear button restores editability
patterns_established:
  - Two-step save with per-edge error isolation and partial success reporting
  - Custom event bridge for cross-module initialization of dynamically added DOM elements
  - Document-level click listener to close dropdown when clicking outside the reference field
  - Stale query guard via latestQuery string comparison after async search resolves
observability_surfaces:
  - "[SemPKM] Reference picker initialized: N fields" console log on init
  - "[SemPKM] Search: \"query\" → M results (K after type filter)" console log per search cycle
  - "[SemPKM] Reference selected: {label} ({iri})" console log on selection
  - "[SemPKM] Edge created: {source} → {predicate} → {target}" console log on each successful edge
  - "[SemPKM] Edge creation failed: ..." console.warn on each failed edge
  - Warning toast with failure count when edges partially fail
drill_down_paths:
  - .gsd/milestones/M014/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S04/tasks/T02-SUMMARY.md
duration: 32m
verification_result: passed
completed_at: 2026-03-18
---

# S04: Relationship Picker + Edge Creation

**Search-as-you-type reference picker on object reference fields with type-filtered suggestions from context-query API, two-step save (object.create → edge.create), and multi-value re-init via custom event bridge**

## What Happened

T01 built the standalone `reference-picker.js` module (~190 lines) with three exports: `initReferencePickers(container, client)`, `initSinglePicker(element, client)`, and `getSelectedReferences(container)`. The module enhances `.reference-field` elements produced by the SHACL renderer with debounced search (300ms), race condition guards (stale query discard via latestQuery comparison), type filtering (when `data-target-class` is present), dropdown rendering with label + type badge, selection management (hidden IRI input + readOnly search field + × clear button), and outside-click dismissal. All event handling is CSP-compliant (zero inline handlers).

T02 wired the picker into the popup lifecycle at three integration points: (1) `initReferencePickers()` called after shape render in `handleTypeChange()`, (2) two-step save in `handleSave()` — after `createObject()` succeeds, `getSelectedReferences()` collects all selections and loops through `client.createEdge()` for each, with per-edge error isolation (failures show warning toast with count but never block object success), and (3) custom event bridge — `shacl-renderer.js` dispatches `sempkm:reference-field-added` when the multi-value add button creates a new reference field, and `popup.js` listens for this event to call `initSinglePicker()` on the new element.

CSS for the dropdown (absolute positioned, max-height 150px, scrollable, shadow), suggestion items (hover state, type badge), loading/empty states, clear button, and selected state was added to `popup.css`.

## Verification

- `node --check` passes on all three JS files (reference-picker.js, popup.js, shacl-renderer.js)
- Zero inline event handlers in reference-picker.js and shacl-renderer.js (grep returns empty — MV3 CSP compliant)
- reference-picker.js exports exactly 3 named functions (initReferencePickers, initSinglePicker, getSelectedReferences)
- popup.js has 5 references to picker functions (1 import + 4 call sites)
- Custom event bridge confirmed: sempkm:reference-field-added dispatched in shacl-renderer.js, listened in popup.js
- createEdge call present in popup.js handleSave flow
- CSS coverage: 6+ selector matches for dropdown/suggestion/clear/selection styles in popup.css
- POST /api/context-query returns results against running Docker stack (verified with curl + Bearer auth)

## Requirements Advanced

- EXT-04 (relationship picker) — fully implemented: search-as-you-type with type filtering, selection, clear, two-step save with edge creation

## Requirements Validated

- None moved to validated — EXT-04 needs S05 E2E tests for formal validation

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None — both tasks implemented exactly as planned.

## Known Limitations

- Full end-to-end browser test of the popup flow (load extension → select type → pick reference → save → verify edge in workspace) deferred to S05 E2E tasks
- Docker test stack setup token was already consumed — API verification used magic-link auth flow instead of Bearer token (same code path in production)

## Follow-ups

- S05: E2E Playwright test exercising the reference picker → edge creation round-trip against Docker stack
- S05: Firefox manifest verification for reference picker behavior
- S05: User guide documentation of relationship creation workflow in extension

## Files Created/Modified

- `extension/shared/reference-picker.js` — New ES module (~190 lines) with initReferencePickers, initSinglePicker, getSelectedReferences exports
- `extension/popup/popup.js` — Added reference-picker import, initReferencePickers calls in handleTypeChange and form reset, two-step save with edge creation loop, sempkm:reference-field-added event listener
- `extension/popup/popup.css` — Appended CSS for suggestions dropdown, suggestion items, type badge, loading/empty states, clear button, selected state
- `extension/shared/shacl-renderer.js` — Added sempkm:reference-field-added custom event dispatch in multi-value add button handler

## Forward Intelligence

### What the next slice should know
- The reference picker depends on `client.searchObjects(query)` calling `POST /api/context-query` — E2E tests need the Docker stack running with at least one model installed and some objects created
- The two-step save flow (object.create → edge.create) means edge creation is a separate API call that happens after the object exists — if the test only checks object creation, edges won't be verified
- The `sempkm:reference-field-added` custom event is the only bridge between shacl-renderer and the picker for multi-value fields — test this by adding a second reference value

### What's fragile
- The stale query guard relies on string comparison of `latestQuery` — if two identical queries are fired in rapid succession, the second response won't be discarded (edge case, unlikely in practice)
- The dropdown positioning is CSS absolute within the `.reference-field` wrapper — if the popup viewport is very narrow or the field is near the bottom, the dropdown may clip

### Authoritative diagnostics
- Filter popup DevTools console for `[SemPKM]` to trace the full lifecycle: init → search → filter → select → edge creation
- `document.querySelectorAll('.reference-field.has-selection')` shows which fields have selected references
- `document.querySelectorAll('.suggestions-dropdown')` shows initialized dropdowns

### What assumptions changed
- No assumptions changed — the S01/S02 boundary map accurately described the upstream surfaces consumed
