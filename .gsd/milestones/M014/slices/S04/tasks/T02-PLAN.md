---
estimated_steps: 7
estimated_files: 3
---

# T02: Wire picker into popup lifecycle and implement two-step save with edge creation

**Slice:** S04 — Relationship Picker + Edge Creation
**Milestone:** M014

## Description

Connect the `reference-picker.js` module (built in T01) to the popup's lifecycle — initialize pickers after form rendering, modify the save flow for two-step creation (object.create → edge.create), and handle multi-value reference field re-initialization. This is the integration task where the full round-trip gets proven against the running Docker stack.

The save flow changes from:
```
1. getFormValues() → properties
2. createObject({type, properties}) → {results: [{iri}]}
3. Show success toast
```
To:
```
1. getFormValues() → properties (includes reference IRIs as property values)
2. createObject({type, properties}) → {results: [{iri}]}
3. getSelectedReferences() → [{path, targetIri}]
4. For each reference: createEdge({source: createdIri, target: targetIri, predicate: path})
5. Show success toast (or partial success warning if edges failed)
```

Reference IRIs go into `object.create` properties as direct triple values (the backend `_to_rdf_value()` converts URI strings to `URIRef` automatically). Edge creation adds first-class `sempkm:Edge` resources for relationship visibility in the Relations panel.

## Steps

1. Import the reference-picker module in `extension/popup/popup.js`:
   ```javascript
   import { initReferencePickers, initSinglePicker, getSelectedReferences } from '../shared/reference-picker.js';
   ```

2. Call `initReferencePickers($dynamicForm, client)` in `handleTypeChange()` after the form fragment is appended to the DOM. Place it after the `$dynamicForm.appendChild(fragment)` line and before `setVisible($formLoading, false)`. The call should be inside the `try` block, after `renderForm()` succeeds:
   ```javascript
   // In handleTypeChange(), after $dynamicForm.appendChild(fragment):
   initReferencePickers($dynamicForm, client);
   ```

3. Modify `handleSave()` to implement two-step creation. After the successful `createObject()` call:
   - Extract the created IRI: `const createdIri = result.results?.[0]?.iri`
   - Get selected references: `const refs = getSelectedReferences($dynamicForm)`
   - If `refs.length > 0` and `createdIri` exists, loop through each ref and call `client.createEdge({source: createdIri, target: ref.targetIri, predicate: ref.path})`
   - Track edge creation results: count successes and failures
   - If all edges succeed: show the normal success toast `"✓ Object created!"`
   - If some edges fail: show warning toast `"✓ Object created, but N relationship(s) failed to save"`
   - If no refs: show normal success toast (unchanged behavior)
   - Log each edge: `console.log('[SemPKM] Edge created: ' + createdIri + ' → ' + ref.path + ' → ' + ref.targetIri)` or `console.warn('[SemPKM] Edge creation failed: ...')` on error
   - Edge failures should NOT throw — catch individually and continue

4. Handle form reset after save: in the existing `setTimeout` reset block, after re-rendering the form via `renderForm(currentShape)`, call `initReferencePickers($dynamicForm, client)` again to re-attach picker behavior to the fresh form.

5. Wire multi-value reference field re-initialization in `extension/shared/shacl-renderer.js`. In the `wrapMultiValue()` function, inside the add button's click handler (after `list.appendChild(newItem)`), check if the new item contains a `.reference-field` and dispatch a custom event:
   ```javascript
   // After list.appendChild(newItem) in the add button handler:
   const refField = newItem.querySelector('.reference-field');
   if (refField) {
     newItem.dispatchEvent(new CustomEvent('sempkm:reference-field-added', {
       bubbles: true,
       detail: { element: refField }
     }));
   }
   ```

6. In `extension/popup/popup.js`, add an event listener on `$dynamicForm` for the custom event, calling `initSinglePicker()`:
   ```javascript
   $dynamicForm.addEventListener('sempkm:reference-field-added', (e) => {
     if (e.detail?.element && client) {
       initSinglePicker(e.detail.element, client);
     }
   });
   ```

7. Verify the full round-trip against Docker stack:
   - Ensure Docker stack is running (`docker compose -f docker-compose.test.yml ps`)
   - Use curl to create a Company object first (via POST /api/commands with Bearer token)
   - Use Node.js or curl to verify POST /api/context-query returns the Company when searched
   - Check `node --check` on all modified files
   - Verify `grep` for zero inline handlers on modified shacl-renderer.js

## Must-Haves

- [ ] `initReferencePickers()` called after form render in `handleTypeChange()`
- [ ] `getSelectedReferences()` called in `handleSave()` after successful `object.create`
- [ ] `createEdge()` called for each selected reference with correct source/target/predicate
- [ ] Edge creation failures caught individually — don't block object success toast
- [ ] Warning toast shown when edges partially fail: "Object created, but N relationship(s) failed"
- [ ] Pickers re-initialized after form reset in save success flow
- [ ] Custom event `sempkm:reference-field-added` dispatched from shacl-renderer on multi-value add
- [ ] Event listener in popup.js calls `initSinglePicker()` for dynamically added reference fields
- [ ] Console logs for edge creation success/failure with source → predicate → target detail

## Verification

- `node --check extension/popup/popup.js` — exits 0
- `node --check extension/shared/shacl-renderer.js` — exits 0
- `grep -rn "onclick\|onchange\|oninput" extension/shared/shacl-renderer.js` — returns empty (no new inline handlers)
- `grep "initReferencePickers\|getSelectedReferences\|initSinglePicker" extension/popup/popup.js` — at least 4 matches (import + usage sites)
- `grep "sempkm:reference-field-added" extension/shared/shacl-renderer.js extension/popup/popup.js` — at least 2 matches (dispatch + listener)
- `grep "createEdge" extension/popup/popup.js` — at least 1 match in handleSave
- API verification: `curl -s -X POST http://localhost:3001/api/context-query -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"keywords":"test"}' | jq '.results | length'` — returns a number (proves context-query works)

## Observability Impact

- Signals added: `[SemPKM] Edge created: {source} → {predicate} → {target}` on each successful edge, `[SemPKM] Edge creation failed: {error}` on each failure, warning toast text with failure count
- How a future agent inspects this: popup DevTools console filtered for `[SemPKM] Edge`, toast text visible in popup UI
- Failure state exposed: edge failure count in toast message, individual error details in console.warn

## Inputs

- `extension/shared/reference-picker.js` — T01 output: module exporting `initReferencePickers(container, client)`, `initSinglePicker(element, client)`, `getSelectedReferences(container)`
- `extension/popup/popup.js` — Current popup with `handleTypeChange()` (renders form at line ~228), `handleSave()` (creates object at line ~515), form reset in setTimeout
- `extension/shared/shacl-renderer.js` — `wrapMultiValue()` function with add button handler that appends new items (around line 330)
- `extension/shared/api-client.js` — `SemPKMClient.createEdge({source, target, predicate})` calls POST /api/commands with edge.create

## Expected Output

- `extension/popup/popup.js` — Modified: imports reference-picker, calls initReferencePickers after form render, implements two-step save with edge creation, handles multi-value event, re-inits pickers on form reset
- `extension/shared/shacl-renderer.js` — Modified: dispatches `sempkm:reference-field-added` custom event in multi-value add handler when the new item contains a reference field
