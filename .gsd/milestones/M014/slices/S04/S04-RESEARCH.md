# S04: Relationship Picker + Edge Creation — Research

**Date:** 2026-03-18
**Status:** Complete

## Summary

S04 adds search-as-you-type to object reference fields in the extension popup and wires the save flow to persist relationships. The SHACL renderer (S02) already produces `.reference-field` wrappers with `data-target-class` attributes and hidden IRI inputs — S04 enhances these with a dropdown that queries the context-query API as the user types. The save flow splits into two phases: `object.create` for the main object (including reference IRIs as direct property triples), then `edge.create` for each reference field to create first-class `sempkm:Edge` resources (making relationships visible in the Relations panel's edge inspector).

The API surface is ready: `SemPKMClient.searchObjects(query)` calls `POST /api/context-query` with Bearer auth, returning `{iri, label, type_iri, type_label, match_type, snippet}` objects. `SemPKMClient.createEdge({source, target, predicate})` calls `POST /api/commands` with `edge.create`. Both methods exist in S01's `api-client.js` and are untouched.

This is straightforward integration work — no new APIs needed, no backend changes, no unfamiliar technology. The main implementation is the search-as-you-type UI module and the save flow modification.

## Recommendation

**Build a standalone `reference-picker.js` module** that enhances all `.reference-field` elements in the popup with search-as-you-type behavior. Keep it separate from `shacl-renderer.js` — the renderer produces the DOM structure, the picker enhances it with behavior. This separation means the renderer stays a pure DOM builder with no side effects, and the picker can be tested independently.

**Use direct property triples as the primary persistence mechanism.** Reference field IRI values go into the `object.create` properties dict (the hidden input's `data-path` maps to the property predicate). The `_to_rdf_value()` handler in `object_create.py` already converts URIs to `URIRef` — this is exactly what the web app does. These direct triples show up in the Relations panel automatically.

**Additionally create `edge.create` resources for explicit relationship tracking.** After `object.create` returns the new IRI, send `edge.create` for each reference field that has a value. This creates first-class `sempkm:Edge` resources with source/target/predicate that enable edge provenance, edge inspector, and bidirectional traversal. This matches the slice description's "two-step creation" (D170).

**Client-side type filtering** for context-query results. The context-query endpoint doesn't support a `type` parameter, but returns `type_iri` on each result. When a reference field has `data-target-class`, filter results client-side to show only matching types. This is sufficient for v1 result sets (≤20 items) and avoids a backend change.

## Implementation Landscape

### Key Files

**New files:**
- `extension/shared/reference-picker.js` — Search-as-you-type module. Exports `initReferencePickers(container, client)` that finds all `.reference-field` elements, attaches `input` event listeners with 300ms debounce, calls `client.searchObjects(query)`, renders dropdown, handles selection (set hidden IRI + display label). Also exports `getSelectedReferences(container)` returning `[{path, targetIri, predicate}]` for edge creation.

**Modified files:**
- `extension/popup/popup.js` — Import `initReferencePickers` and `getSelectedReferences`. Call `initReferencePickers($dynamicForm, client)` after shape rendering in `handleTypeChange()`. In `handleSave()`, after `object.create` succeeds, loop through `getSelectedReferences()` and call `client.createEdge()` for each.
- `extension/popup/popup.css` — Add styles for `.suggestions-dropdown`, `.suggestion-item`, `.suggestion-item:hover`, `.suggestion-item .suggestion-type`, loading/empty states.

**Unchanged but relevant:**
- `extension/shared/shacl-renderer.js` — Already renders `.reference-field` with `data-target-class` on wrapper and search input, hidden `input[data-path]` for IRI. No changes needed.
- `extension/shared/api-client.js` — `searchObjects(query)` and `createEdge({source, target, predicate})` already implemented. No changes needed.
- `backend/app/api/router.py` — `POST /api/context-query` returns `{results: [{iri, label, type_iri, type_label, match_type, snippet}]}`. No changes needed.
- `backend/app/commands/handlers/edge_create.py` — Accepts `{source, target, predicate}`. No changes needed.
- `backend/app/commands/handlers/object_create.py` — `_to_rdf_value()` converts URI strings to `URIRef`. Reference field values (IRIs) submitted as properties will become direct triples automatically. No changes needed.

### Reference DOM Structure (from shacl-renderer.js)

The SHACL renderer produces this for each object reference field:
```html
<div class="reference-field" data-target-class="urn:sempkm:model:crm:Company">
  <input type="text" class="form-input reference-search"
         placeholder="Search Company..."
         autocomplete="off"
         data-target-class="urn:sempkm:model:crm:Company">
  <input type="hidden" data-path="urn:sempkm:model:crm:worksAt">
</div>
```

The picker module enhances this by:
1. Adding a `.suggestions-dropdown` div after the search input
2. Listening for `input` events on `.reference-search` with 300ms debounce
3. Calling `client.searchObjects(query)` and filtering by `data-target-class`
4. Rendering results as clickable `.suggestion-item` elements
5. On selection: setting hidden input value to IRI, search input value to label, closing dropdown
6. Adding a clear button (×) to reset the selection

### Multi-Value Reference Fields

`cloneEmptyInput()` in `shacl-renderer.js` already rebuilds the full `.reference-field` wrapper for multi-value add. After `initReferencePickers()` runs on the form container, newly added multi-value reference fields need picker behavior too. Solution: use a MutationObserver on `$dynamicForm` or re-init pickers after add-value clicks. Simpler approach: have the add-value handler dispatch a custom event that `reference-picker.js` listens for.

### Save Flow Modification

Current flow in `handleSave()`:
```
1. getFormValues($dynamicForm) → properties (includes reference IRIs)
2. client.createObject({type, properties}) → {results: [{iri}]}
3. Show success toast
```

New flow:
```
1. getFormValues($dynamicForm) → properties (includes reference IRIs)
2. client.createObject({type, properties}) → {results: [{iri}]}
3. Get created IRI from results[0].iri
4. getSelectedReferences($dynamicForm) → [{path, targetIri}]
5. For each reference: client.createEdge({source: createdIri, target: targetIri, predicate: path})
6. Show success toast (or partial success if edges failed)
```

Edge creation failures should not block the success toast — the object exists. Show a warning toast: "Object created, but N relationship(s) failed to save."

### Context-Query Response Shape

```json
{
  "results": [
    {
      "iri": "urn:sempkm:obj:abc123",
      "label": "Acme Corporation",
      "type_iri": "urn:sempkm:model:crm:Company",
      "type_label": "Company",
      "match_type": "keyword",
      "snippet": null
    }
  ],
  "total": 1
}
```

Client-side type filtering: when `data-target-class` is set, filter `results` to only those where `type_iri === targetClass`. When no target class, show all results.

### Build Order

1. **`reference-picker.js` module** — Core search-as-you-type logic. Debounced input handler, API call, dropdown rendering, selection handling, clear button. This is the main new code. ~150-200 lines.
2. **CSS for suggestions dropdown** — Absolute-positioned dropdown below reference input, suggestion items with label + type badge, hover/active states, loading spinner, empty state.
3. **Wire into popup.js** — Import and call `initReferencePickers()` after shape render. Handle multi-value add by re-initing pickers on new fields. Modify `handleSave()` for two-step creation.
4. **Verify end-to-end** — Create a Contact with a Company reference against running Docker stack. Confirm both the direct property triple and the sempkm:Edge appear.

### Verification Approach

- `node --check extension/shared/reference-picker.js` — syntax valid
- `node --check extension/popup/popup.js` — syntax valid after modification
- Grep for zero inline handlers in new code (Chrome MV3 CSP)
- API integration test against Docker stack:
  1. Create a Company object first (via curl or extension)
  2. Open extension popup, select Contact type
  3. Type in "Works At" reference field → verify suggestions dropdown appears with the Company
  4. Select the Company → verify hidden input populated with IRI
  5. Save → verify object created (check workspace)
  6. Verify Relations panel shows the "worksAt" relationship
- Check popup DevTools console for `[SemPKM]` lifecycle logs
- Verify multi-value reference add works (if CRM has any multi-value reference fields)

## Constraints

- **Chrome MV3 CSP** — No inline event handlers. All listeners via `addEventListener`. The `reference-picker.js` module must follow this rule strictly.
- **380px popup viewport** — Suggestions dropdown must not overflow the popup. Use `max-height` with scroll, position absolutely below the input.
- **Context-query is FTS-based, not type-filtered** — Results include all types. Client-side filtering by `data-target-class` may return empty when the search term matches objects of the wrong type. Show "No matching {TypeLabel} found" rather than an empty dropdown.

## Common Pitfalls

- **Dropdown positioning in popup** — The popup has fixed height (~600px). Suggestions near the bottom will clip. Use `position: absolute` on the dropdown with `max-height: 150px; overflow-y: auto`. The `.reference-field` wrapper already has `position: relative`.
- **Race conditions on fast typing** — Debounce handles most cases, but if the user types quickly and results arrive out of order, the dropdown may show stale results. Track the latest request query and ignore responses that don't match.
- **Multi-value re-initialization** — When the user clicks "+ Add" on a multi-value reference field, `cloneEmptyInput()` creates a new `.reference-field` without picker behavior. Need to init the picker on the new element. Best approach: after `shacl-renderer.js`'s add-value handler clones the input, call `initSinglePicker(newElement, client)`.
- **Edge creation with reference IRI values** — `getFormValues()` already returns the IRI from hidden inputs. Need to identify which values are reference IRIs (not regular string properties) for edge creation. The `.reference-field` wrapper's `data-target-class` attribute is the signal — only inputs inside `.reference-field` wrappers produce edges.
