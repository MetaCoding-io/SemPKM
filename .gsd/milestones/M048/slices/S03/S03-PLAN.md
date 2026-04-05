# S03: Object Delete UI

**Goal:** Single-object delete works from three UI surfaces (object toolbar, explorer tree hover, command palette), with backend inbound edge cleanup so no dangling references remain.
**Demo:** After this: Click delete button on object toolbar → confirmation dialog → object removed from explorer tree, views, and SPARQL. Also accessible via command palette 'Delete Object' command.

## Tasks
- [x] **T01: Added inbound edge SPARQL query to bulk_delete_objects() so deleting an object also removes all triples referencing it, preventing dangling references** — ## Why

The existing `bulk_delete_objects()` endpoint only queries and deletes triples where the deleted IRI is the **subject** (`<iri> ?p ?o`). It does NOT delete triples where the IRI is the **object** (`?s ?p <iri>`), leaving dangling references. Decision D384 requires fixing this.

## Steps

1. Open `backend/app/browser/objects.py`, find the `bulk_delete_objects()` function (starts at line 1014).

2. Inside the `for iri in iris:` loop, after the existing outbound SPARQL query and binding processing (which collects triples matching `<iri> ?p ?o`), add a second SPARQL query for inbound edges:
   ```sparql
   SELECT ?s ?p WHERE {
     GRAPH <urn:sempkm:current> {
       ?s ?p <{iri}> .
     }
   }
   ```

3. Process the inbound bindings: for each result, create `(URIRef(s_value), URIRef(p_value), URIRef(iri))` and append to `materialize_deletes`. The subject (`?s`) will always be a URI since blank nodes don't typically reference other resources by IRI.

4. Wrap in the same try/except pattern as the outbound query (log warning on failure, continue).

5. Create `backend/tests/test_object_delete_inbound.py` with tests:
   - Test that inbound edge triples are included in `materialize_deletes` when present
   - Test that outbound triples are still included (no regression)
   - Test that when no inbound edges exist, delete still works
   - Mock the triplestore client's `query()` to return controlled bindings

6. Run: `cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v`

## Key constraint
The inbound triples must be appended to the SAME `materialize_deletes` list as the outbound triples, so they're part of the same `Operation` and same event audit trail.
  - Estimate: 25m
  - Files: backend/app/browser/objects.py, backend/tests/test_object_delete_inbound.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v
- [x] **T02: Added deleteObject() JS function with confirmation dialog, wired into object toolbar button, command palette 'Delete Object' entry, and explorer tree hover action** — ## Why

The UI currently has no way to delete a single object. This task adds the shared `deleteObject(iri, label)` JS function and wires it into three surfaces: the object toolbar, the command palette, and the explorer tree hover action.

## Steps

1. **Add `deleteObject()` to `frontend/static/js/workspace.js`:**
   - Place it near the existing `bulkDeleteSelected()` function (around line 1460).
   - Implementation:
     ```javascript
     function deleteObject(iri, label) {
       showConfirmDialog(
         'Delete object',
         'Delete "' + (label || iri) + '"? This cannot be undone.',
         null,
         function() {
           apiFetch('/browser/objects/delete', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ iris: [iri] }),
             silent: true
           })
           .then(function(resp) { return resp.json(); })
           .then(function() {
             closeTab(iri);
             refreshNavTree();
             showToast('Object deleted');
           })
           .catch(function(err) {
             showToast('Failed to delete: ' + err.message);
           });
         }
       );
     }
     ```
   - Export: Add `window.SemPKM.deleteObject = deleteObject;` near the other exports (around line 3811).

2. **Add delete button to object toolbar in `backend/app/templates/browser/object_tab.html`:**
   - Inside `.object-toolbar-actions` div, after the star button and before the properties-toggle-badge, add:
     ```html
     <button class="delete-btn"
             onclick="event.stopPropagation(); SemPKM.deleteObject('{{ object_iri }}', '{{ object_label | e }}')"
             title="Delete object">
       <i data-lucide="trash-2"></i>
     </button>
     ```

3. **Add `.delete-btn` CSS to `frontend/static/css/workspace.css`:**
   - Place after the `.star-btn` block (after line ~2372). Follow the `.star-btn` pattern:
     ```css
     .delete-btn {
         display: inline-flex;
         align-items: center;
         justify-content: center;
         padding: 4px;
         border: none;
         background: transparent;
         color: var(--color-text-muted);
         cursor: pointer;
         border-radius: 4px;
         transition: color 0.2s;
     }
     .delete-btn:hover {
         color: var(--color-error);
     }
     .delete-btn svg {
         width: 16px;
         height: 16px;
         flex-shrink: 0;
         stroke: currentColor;
     }
     ```
   - Per CLAUDE.md: size via CSS not inline styles, include `flex-shrink: 0`, use `stroke: currentColor`.

4. **Add command palette entry in `frontend/static/js/workspace.js`:**
   - In the `commands` array (around line 1635), after the `toggle-edit-mode` entry, add:
     ```javascript
     {
       id: 'delete-object',
       title: 'Delete Object',
       section: 'Objects',
       handler: function () {
         var iri = getActiveTabIri();
         if (!iri || iri.indexOf('view:') === 0) {
           showToast('No object selected');
           return;
         }
         var meta = window.SemPKM._tabMeta ? window.SemPKM._tabMeta[iri] : null;
         var label = meta ? meta.label : iri;
         deleteObject(iri, label);
       }
     },
     ```
   - Uses `getActiveTabIri()` (line 218) to get active panel IRI. Skips `view:` prefixed tabs. Gets label from `_tabMeta`.

5. **Add explorer tree hover delete action in `backend/app/templates/browser/tree_children.html`:**
   - Inside each `.tree-leaf` div, after the `<span class="tree-leaf-label">` element, add:
     ```html
     <button class="tree-leaf-action btn-icon" title="Delete object"
             onclick="event.stopPropagation(); SemPKM.deleteObject('{{ obj.iri }}', '{{ obj.label | e }}')">
       <i data-lucide="trash-2"></i>
     </button>
     ```
   - CSS already exists at `.tree-leaf .tree-leaf-action` (workspace.css line 8855): opacity 0 by default, opacity 1 on hover, red on action hover. SVG sizing at line 8877.
   - Pattern matches `dashboard_explorer.html` (line 13).

6. **Verify:**
   - `grep -q 'deleteObject' frontend/static/js/workspace.js` — function exists
   - `grep -q 'delete-btn' backend/app/templates/browser/object_tab.html` — toolbar button exists
   - `grep -q 'delete-object' frontend/static/js/workspace.js` — command palette entry exists
   - `grep -q 'deleteObject' backend/app/templates/browser/tree_children.html` — tree action exists
   - `grep -q '.delete-btn' frontend/static/css/workspace.css` — CSS exists
  - Estimate: 30m
  - Files: frontend/static/js/workspace.js, backend/app/templates/browser/object_tab.html, backend/app/templates/browser/tree_children.html, frontend/static/css/workspace.css
  - Verify: grep -q 'function deleteObject' frontend/static/js/workspace.js && grep -q 'delete-btn' backend/app/templates/browser/object_tab.html && grep -q 'delete-object' frontend/static/js/workspace.js && grep -q 'deleteObject' backend/app/templates/browser/tree_children.html && grep -q '.delete-btn' frontend/static/css/workspace.css && echo 'All checks pass'
