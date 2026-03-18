---
id: T01
parent: S04
milestone: M014
provides:
  - reference-picker.js ES module with search-as-you-type, debounce, type filtering, selection, clear
  - CSS for suggestions dropdown, items, states, clear button in popup.css
key_files:
  - extension/shared/reference-picker.js
  - extension/popup/popup.css
key_decisions:
  - Made searchInput readOnly on selection to prevent accidental edits; clear button restores editability
patterns_established:
  - Document-level click listener to close dropdown when clicking outside the reference field
  - Stale query guard via latestQuery string comparison after async search resolves
observability_surfaces:
  - "[SemPKM] Reference picker initialized: N fields" console log on init
  - "[SemPKM] Search: \"query\" → M results (K after type filter)" console log per search cycle
  - "[SemPKM] Reference selected: {label} ({iri})" console log on selection
duration: 12m
verification_result: passed
blocker_discovered: false
---

# T01: Build reference-picker module with search-as-you-type and suggestion dropdown

**Created reference-picker.js ES module with 3 exports (initReferencePickers, initSinglePicker, getSelectedReferences) — full search/filter/select/clear lifecycle with 300ms debounce, stale query guard, type filtering, and CSP-compliant event handling. Added dropdown CSS to popup.css.**

## What Happened

Built `extension/shared/reference-picker.js` as a standalone ES module (~190 lines) with three exported functions. The module enhances `.reference-field` elements produced by shacl-renderer.js with:

- **Debounced search**: 300ms `setTimeout`/`clearTimeout` pattern on the input event. Queries shorter than 2 chars hide the dropdown.
- **Race condition guard**: Tracks `latestQuery` and discards responses where the query has changed during the async search call.
- **Type filtering**: When `data-target-class` is set on the wrapper, only results with matching `type_iri` are shown.
- **Dropdown rendering**: `.suggestions-dropdown` container with `.suggestion-item` elements (label + type badge), plus loading and empty states.
- **Selection**: Click sets hidden input to IRI, search input to label, adds `.has-selection` class, makes input readOnly, and creates a × clear button.
- **Clear**: Removes selection, restores editability, re-focuses the search input.
- **Outside click**: Document-level click listener hides dropdown when clicking outside the wrapper.

CSS appended to `popup.css` covers dropdown positioning (absolute, max-height 150px, scroll, shadow), suggestion item layout with hover state, type badge styling, loading/empty italic states, clear button (absolute right, hover red), and selected state background.

Also added the missing Observability Impact section to T01-PLAN.md as required by pre-flight.

## Verification

All four task-level verification commands pass. Slice-level checks 1, 3, 4 (syntax, CSP, exports) pass; checks 2, 5-8 depend on T02 (popup.js wiring, Docker stack integration).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/shared/reference-picker.js` | 0 | ✅ pass | <1s |
| 2 | `grep -rn "onclick\|onchange\|oninput" extension/shared/reference-picker.js` | 1 (no matches) | ✅ pass | <1s |
| 3 | `node -e "import('./extension/shared/reference-picker.js').then(m => ...)"` | 0 | ✅ pass | <1s |
| 4 | `grep -c "suggestions-dropdown\|suggestion-item\|..." extension/popup/popup.css` | 0 (9 matches) | ✅ pass | <1s |

## Diagnostics

- **Inspect exports**: `node -e "import('./extension/shared/reference-picker.js').then(m => console.log(Object.keys(m)))"`
- **In popup DevTools**: Filter console for `[SemPKM]` to trace init, search, and selection events
- **DOM inspection**: `document.querySelectorAll('.suggestions-dropdown')` shows initialized dropdowns; `.reference-field.has-selection` shows selected fields

## Deviations

None — implemented exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `extension/shared/reference-picker.js` — New ES module (~190 lines) with initReferencePickers, initSinglePicker, getSelectedReferences exports
- `extension/popup/popup.css` — Appended CSS for suggestions dropdown, suggestion items, type badge, loading/empty states, clear button, selected state
- `.gsd/milestones/M014/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
