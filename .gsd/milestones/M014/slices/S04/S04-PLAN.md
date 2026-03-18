# S04: Relationship Picker + Edge Creation

**Goal:** Object reference fields in the extension popup render search-as-you-type inputs that query existing objects, and saving creates both the object and typed edges for each reference.
**Demo:** User opens the extension popup, selects "Contact" type, types in the "Works At" reference field → sees Company suggestions from the context-query API → selects one → saves → Contact is created with a direct `worksAt` property triple AND a `sempkm:Edge` resource linking source to target.

## Must-Haves

- Search-as-you-type on all `.reference-field` inputs with 300ms debounce calling `client.searchObjects(query)`
- Suggestions dropdown with object label + type badge, filtered by `data-target-class` when present
- Selection populates hidden IRI input, shows label in search field, provides clear (×) button
- Multi-value reference fields get picker behavior on dynamically added entries
- Save flow creates object first, then calls `client.createEdge()` for each reference field with a value
- Edge creation failures show warning toast but don't block object success
- Race condition guard: stale responses from earlier queries are ignored
- Zero inline event handlers (Chrome MV3 CSP compliance)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (API calls against Docker stack)
- Human/UAT required: no

## Verification

- `node --check extension/shared/reference-picker.js` — syntax valid
- `node --check extension/popup/popup.js` — syntax valid after modification
- `grep -rn "onclick\|onchange\|oninput" extension/shared/reference-picker.js` — returns empty (MV3 CSP)
- Node.js smoke test: `reference-picker.js` exports `initReferencePickers` and `getSelectedReferences` functions
- API integration against Docker stack: POST /api/context-query with Bearer token returns results
- End-to-end flow: create a Company → open popup for Contact → type in reference field → see Company in dropdown → select → save → verify object + edge via workspace UI
- Console log: `[SemPKM] Reference picker initialized: N fields` on form render
- Console log: `[SemPKM] Edge created: {source} → {predicate} → {target}` after save

## Observability / Diagnostics

- Runtime signals: `[SemPKM] Reference picker initialized: N fields` log, `[SemPKM] Search: "query" → M results (K after type filter)` log, `[SemPKM] Edge created: ...` / `[SemPKM] Edge creation failed: ...` logs
- Inspection surfaces: popup DevTools console filtered for `[SemPKM]`, Elements panel `.suggestions-dropdown` visibility
- Failure visibility: stale query rejection logged, edge creation errors shown as warning toasts with count
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `extension/shared/api-client.js` (searchObjects, createEdge), `extension/shared/shacl-renderer.js` (`.reference-field` DOM structure with `data-target-class`, `cloneEmptyInput` multi-value add), `extension/popup/popup.js` (handleTypeChange, handleSave flow)
- New wiring introduced in this slice: `reference-picker.js` module imported into `popup.js`, `initReferencePickers()` called after shape render, `getSelectedReferences()` called in save flow, custom event `sempkm:reference-field-added` dispatched from shacl-renderer for multi-value re-init
- What remains before the milestone is truly usable end-to-end: S05 (Firefox manifest, Alt+S shortcut, E2E tests, user guide)

## Tasks

- [x] **T01: Build reference-picker module with search-as-you-type and suggestion dropdown** `est:45m`
  - Why: Core new module — the search-as-you-type UI for object reference fields. Must be standalone, CSP-compliant, and handle debounce, dropdown rendering, selection, clear, type filtering, and race conditions. Also needs CSS for dropdown positioning in the 380px popup.
  - Files: `extension/shared/reference-picker.js`, `extension/popup/popup.css`
  - Do: Create `reference-picker.js` exporting `initReferencePickers(container, client)` and `getSelectedReferences(container)`. Debounced input handler (300ms) calls `client.searchObjects(query)`, filters by `data-target-class`, renders `.suggestions-dropdown` with `.suggestion-item` elements (label + type badge). Selection sets hidden input value to IRI, search input to label, adds `.has-selection` class, shows × clear button. Track latest query to discard stale responses. Empty/loading/no-match states. Also add `initSinglePicker(element, client)` export for multi-value re-init. Add CSS to `popup.css` for dropdown (absolute positioned, max-height 150px, scroll, shadow).
  - Verify: `node --check extension/shared/reference-picker.js` passes; `grep -rn "onclick\|onchange\|oninput" extension/shared/reference-picker.js` returns empty; Node.js `import()` confirms 3 named exports
  - Done when: Module exports 3 functions, has zero inline handlers, dropdown CSS exists

- [x] **T02: Wire picker into popup lifecycle and implement two-step save with edge creation** `est:45m`
  - Why: Integration task — connects the picker module to the popup's type-change and save flows, handles multi-value re-init, and implements the object.create → edge.create two-step pattern. This is where the full round-trip gets proven.
  - Files: `extension/popup/popup.js`, `extension/shared/shacl-renderer.js`
  - Do: Import `initReferencePickers`, `initSinglePicker`, `getSelectedReferences` in popup.js. Call `initReferencePickers($dynamicForm, client)` after `$dynamicForm.appendChild(fragment)` in `handleTypeChange()`. In `handleSave()`, after successful `createObject()`, call `getSelectedReferences($dynamicForm)` and loop with `client.createEdge({source: createdIri, target: ref.targetIri, predicate: ref.path})` for each. Show partial success toast if edges fail. In `shacl-renderer.js`, dispatch `sempkm:reference-field-added` custom event (with the new element in `detail`) from the multi-value add button handler. In `reference-picker.js` (or popup.js), listen for this event and call `initSinglePicker()` on the new element. Verify against running Docker stack.
  - Verify: `node --check extension/popup/popup.js` and `extension/shared/shacl-renderer.js` pass; end-to-end test against Docker stack: create Company, then create Contact with "Works At" → Company selected → save → object created + edge created; console shows `[SemPKM] Edge created` log
  - Done when: Full round-trip works — reference picker shows suggestions, selection persists, save creates object + edge, multi-value add gets picker behavior

## Files Likely Touched

- `extension/shared/reference-picker.js` (new)
- `extension/popup/popup.js` (modified)
- `extension/popup/popup.css` (modified)
- `extension/shared/shacl-renderer.js` (modified — event dispatch for multi-value)
