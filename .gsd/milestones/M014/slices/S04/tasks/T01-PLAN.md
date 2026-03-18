---
estimated_steps: 8
estimated_files: 2
---

# T01: Build reference-picker module with search-as-you-type and suggestion dropdown

**Slice:** S04 — Relationship Picker + Edge Creation
**Milestone:** M014

## Description

Create the standalone `reference-picker.js` ES module that enhances `.reference-field` elements in the extension popup with search-as-you-type behavior. This is the core new code for S04 — a ~150-200 line module that handles debounced API search, dropdown rendering, result filtering, selection management, and clear functionality. Also add the CSS for the suggestions dropdown to `popup.css`.

The module must be Chrome MV3 CSP-compliant (zero inline event handlers — all listeners via `addEventListener`). It integrates with the existing DOM structure produced by `shacl-renderer.js`:

```html
<div class="reference-field" data-target-class="urn:sempkm:model:crm:Company">
  <input type="text" class="form-input reference-search"
         placeholder="Search Company..."
         autocomplete="off"
         data-target-class="urn:sempkm:model:crm:Company">
  <input type="hidden" data-path="urn:sempkm:model:crm:worksAt">
</div>
```

The module uses `SemPKMClient.searchObjects(query)` which calls `POST /api/context-query` and returns an array of `{iri, label, type_iri, type_label, match_type, snippet}` objects.

## Steps

1. Create `extension/shared/reference-picker.js` with the module structure:
   - Export `initReferencePickers(container, client)` — finds all `.reference-field` elements in container and initializes each one
   - Export `initSinglePicker(element, client)` — initializes one `.reference-field` element (used for multi-value re-init)
   - Export `getSelectedReferences(container)` — returns `[{path, targetIri}]` for all reference fields that have a selected value

2. Implement the core picker logic inside `initSinglePicker(element, client)`:
   - Find the `.reference-search` text input and `input[type=hidden][data-path]` within the element
   - Read `data-target-class` from the wrapper for type filtering
   - Create a `.suggestions-dropdown` div and append it after the search input inside the `.reference-field` wrapper
   - Add `input` event listener on the search input with 300ms debounce (use a `setTimeout`/`clearTimeout` pattern)
   - Track the latest query string to discard stale responses (race condition guard)

3. Implement the search and render cycle:
   - On debounced input: if query is < 2 chars, hide dropdown; otherwise show loading state ("Searching...")
   - Call `client.searchObjects(query)` — this returns an array of results
   - Check if query still matches the latest (stale guard) — if not, discard
   - Filter results by `data-target-class` when present: keep only results where `type_iri === targetClass`
   - If no results after filtering, show "No matching {typeName} found" (extract type name from placeholder or target class local name)
   - Render results as `.suggestion-item` elements with label and `.suggestion-type` badge showing type_label

4. Implement selection handling:
   - On `.suggestion-item` click: set hidden input `.value` to the result's `iri`, set search input `.value` to the result's `label`
   - Add `.has-selection` class to the `.reference-field` wrapper
   - Hide the dropdown
   - Create a `.clear-selection` button (× icon) and append to the wrapper
   - Log `[SemPKM] Reference selected: {label} ({iri})`

5. Implement the clear button:
   - On × click: clear hidden input value, clear search input value, remove `.has-selection` class, remove the clear button
   - Re-enable the search input for new searches

6. Implement `getSelectedReferences(container)`:
   - Query all `.reference-field` elements in container
   - For each, check hidden input value — if non-empty, include `{path: hiddenInput.dataset.path, targetIri: hiddenInput.value}`
   - Return the array (may be empty)

7. Implement `initReferencePickers(container, client)`:
   - Query all `.reference-field` elements in container
   - Call `initSinglePicker(element, client)` for each
   - Log `[SemPKM] Reference picker initialized: N fields`

8. Add CSS to `extension/popup/popup.css`:
   - `.suggestions-dropdown` — `position: absolute; top: 100%; left: 0; right: 0; z-index: 10; max-height: 150px; overflow-y: auto; background: white; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);`
   - `.suggestion-item` — padding, cursor pointer, hover state with light indigo background
   - `.suggestion-item .suggestion-label` — primary text
   - `.suggestion-item .suggestion-type` — small badge with type label, muted color, right-aligned
   - `.suggestions-loading`, `.suggestions-empty` — italic muted text states
   - `.clear-selection` — positioned absolute right inside `.reference-field`, small × button, hover red
   - `.reference-field.has-selection .reference-search` — slightly muted background to indicate selected state

## Must-Haves

- [ ] `initReferencePickers(container, client)` exported and initializes all `.reference-field` elements
- [ ] `initSinglePicker(element, client)` exported for single-element initialization (multi-value re-init)
- [ ] `getSelectedReferences(container)` exported and returns `[{path, targetIri}]` for selected references
- [ ] 300ms debounce on search input with `clearTimeout`/`setTimeout`
- [ ] Race condition guard: stale responses from earlier queries are discarded
- [ ] Client-side type filtering by `data-target-class` when present
- [ ] Selection sets hidden input value to IRI and search input to label
- [ ] Clear button (×) resets selection and re-enables search
- [ ] Zero inline event handlers (`onclick`, `onchange`, `oninput`) — all via `addEventListener`
- [ ] CSS for dropdown positioning (absolute, max-height 150px, scroll), items, loading/empty states, clear button

## Verification

- `node --check extension/shared/reference-picker.js` — exits 0
- `grep -rn "onclick\|onchange\|oninput" extension/shared/reference-picker.js` — returns empty
- Node.js export check: `node -e "import('./extension/shared/reference-picker.js').then(m => { const fns = Object.keys(m); console.log(fns); if(!fns.includes('initReferencePickers') || !fns.includes('initSinglePicker') || !fns.includes('getSelectedReferences')) process.exit(1); })"` — exits 0
- CSS classes exist: `grep -c "suggestions-dropdown\|suggestion-item\|suggestion-type\|suggestions-loading\|suggestions-empty\|clear-selection" extension/popup/popup.css` — at least 6 matches

## Inputs

- `extension/shared/shacl-renderer.js` — produces `.reference-field` DOM structure with `data-target-class` and hidden `[data-path]` input (read-only reference, do not modify)
- `extension/shared/api-client.js` — `SemPKMClient.searchObjects(query)` returns `[{iri, label, type_iri, type_label, match_type, snippet}]` (read-only reference, do not modify)
- `extension/popup/popup.css` — existing styles include `.reference-field { position: relative; }` already set

## Expected Output

- `extension/shared/reference-picker.js` — New ~150-200 line ES module with 3 exported functions, zero inline handlers, full debounce/filter/select/clear lifecycle
- `extension/popup/popup.css` — Appended CSS for `.suggestions-dropdown`, `.suggestion-item`, `.suggestion-type`, loading/empty states, `.clear-selection` button, `.has-selection` indicator
