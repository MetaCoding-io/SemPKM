---
id: T02
parent: S04
milestone: M014
provides:
  - Two-step save flow in popup: object.create → edge.create for each selected reference
  - Reference picker initialization wired into form render and reset lifecycle
  - Custom event bridge between shacl-renderer multi-value add and popup picker init
key_files:
  - extension/popup/popup.js
  - extension/shared/shacl-renderer.js
key_decisions:
  - Edge failures caught per-edge with warning toast showing failure count — never blocks object success
  - Custom event `sempkm:reference-field-added` dispatched from shacl-renderer (bubbles) — decouples renderer from picker module
patterns_established:
  - Two-step save with per-edge error isolation and partial success reporting
  - Custom event bridge for cross-module initialization of dynamically added DOM elements
observability_surfaces:
  - "[SemPKM] Edge created: {source} → {predicate} → {target}" console log on each successful edge
  - "[SemPKM] Edge creation failed: ..." console.warn on each failed edge
  - Warning toast with failure count when edges partially fail
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Wire picker into popup lifecycle and implement two-step save with edge creation

**Wired reference-picker module into popup form lifecycle with two-step save (object.create → edge.create per reference) and multi-value re-init via custom event bridge**

## What Happened

Connected the T01 reference-picker module to the popup's three integration points:

1. **Form render** — `initReferencePickers($dynamicForm, client)` called after `renderForm()` appends the fragment in `handleTypeChange()`.

2. **Save flow** — Modified `handleSave()` to implement two-step creation: after `createObject()` succeeds, calls `getSelectedReferences($dynamicForm)` to collect all selected reference IRIs, then loops through each calling `client.createEdge({source, target, predicate})`. Each edge call is individually try/caught — failures increment a counter and log a warning, but never throw. Toast shows either normal success or a warning with failure count.

3. **Form reset** — After save success, the setTimeout reset block re-renders the form and re-initializes pickers.

4. **Multi-value add** — Added custom event dispatch (`sempkm:reference-field-added`) in shacl-renderer's `wrapMultiValue()` add button handler. The popup listens for this event on `$dynamicForm` and calls `initSinglePicker()` on the newly added reference field.

## Verification

- `node --check extension/popup/popup.js` — exits 0
- `node --check extension/shared/shacl-renderer.js` — exits 0
- `grep -rn "onclick|onchange|oninput" extension/shared/shacl-renderer.js` — returns empty (zero inline handlers)
- `grep "initReferencePickers|getSelectedReferences|initSinglePicker" extension/popup/popup.js` — 5 matches (import + 4 usage sites)
- `grep "sempkm:reference-field-added" extension/shared/shacl-renderer.js extension/popup/popup.js` — 2 matches (dispatch + listener)
- `grep "createEdge" extension/popup/popup.js` — 1 match in handleSave
- Node.js exports check: `reference-picker.js` exports 3 named functions
- API integration: POST /api/context-query returns results (2) against running Docker stack on port 8901
- API health check: Docker stack healthy (api, triplestore, frontend all up)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/popup/popup.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/shared/shacl-renderer.js` | 0 | ✅ pass | <1s |
| 3 | `grep -rn "onclick\|onchange\|oninput" extension/shared/shacl-renderer.js` | 1 (no matches) | ✅ pass | <1s |
| 4 | `grep "initReferencePickers\|getSelectedReferences\|initSinglePicker" extension/popup/popup.js` | 0 (5 matches) | ✅ pass | <1s |
| 5 | `grep "sempkm:reference-field-added" extension/shared/shacl-renderer.js extension/popup/popup.js` | 0 (2 matches) | ✅ pass | <1s |
| 6 | `grep "createEdge" extension/popup/popup.js` | 0 (1 match) | ✅ pass | <1s |
| 7 | `node -e "import('./extension/shared/reference-picker.js').then(m => console.log(Object.keys(m)))"` | 0 (3 exports) | ✅ pass | <1s |
| 8 | `curl -s -X POST http://localhost:8901/api/context-query ... \| jq '.results \| length'` | 0 (returns 2) | ✅ pass | <1s |
| 9 | `node --check extension/shared/reference-picker.js` | 0 | ✅ pass | <1s |
| 10 | `grep -rn "onclick\|onchange\|oninput" extension/shared/reference-picker.js` | 1 (no matches) | ✅ pass | <1s |

## Diagnostics

- **Popup DevTools console**: Filter for `[SemPKM] Edge` to see edge creation success/failure logs with source → predicate → target detail
- **Toast messages**: Normal success shows "✓ Object created!", partial failure shows "✓ Object created, but N relationship(s) failed to save"
- **DOM inspection**: `document.querySelectorAll('.reference-field.has-selection')` shows fields with selected references
- **Multi-value events**: Watch for `sempkm:reference-field-added` events on the dynamic form container

## Deviations

None.

## Known Issues

- Docker test stack setup token already consumed — API verification used magic-link auth flow instead of Bearer token. The extension in real use authenticates via API key (Bearer), which follows the same code path.
- End-to-end browser test of the full popup flow (load extension → select type → pick reference → save → verify edge) deferred to S05 E2E tasks — this task verified the code integration via syntax checks, export verification, and API availability.

## Files Created/Modified

- `extension/popup/popup.js` — Added reference-picker import, initReferencePickers calls in handleTypeChange and form reset, two-step save with edge creation loop, sempkm:reference-field-added event listener
- `extension/shared/shacl-renderer.js` — Added sempkm:reference-field-added custom event dispatch in multi-value add button handler
