---
estimated_steps: 104
estimated_files: 4
skills_used: []
---

# T02: Add deleteObject() function, toolbar button, command palette entry, and explorer tree action

## Why

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

## Inputs

- ``frontend/static/js/workspace.js` — existing workspace JS with bulkDeleteSelected(), showConfirmDialog(), closeTab(), refreshNavTree(), showToast(), getActiveTabIri(), SemPKM exports`
- ``backend/app/templates/browser/object_tab.html` — object tab template with .object-toolbar-actions div and star button`
- ``backend/app/templates/browser/tree_children.html` — tree leaf template with .tree-leaf divs`
- ``frontend/static/css/workspace.css` — existing .star-btn CSS (line 2342) and .tree-leaf-action CSS (line 8855)`
- ``backend/app/templates/browser/dashboard_explorer.html` — reference pattern for tree-leaf-action button (line 13)`

## Expected Output

- ``frontend/static/js/workspace.js` — modified with deleteObject() function, SemPKM.deleteObject export, and 'Delete Object' command palette entry`
- ``backend/app/templates/browser/object_tab.html` — modified with delete-btn in toolbar`
- ``backend/app/templates/browser/tree_children.html` — modified with tree-leaf-action delete button`
- ``frontend/static/css/workspace.css` — modified with .delete-btn styles`

## Verification

grep -q 'function deleteObject' frontend/static/js/workspace.js && grep -q 'delete-btn' backend/app/templates/browser/object_tab.html && grep -q 'delete-object' frontend/static/js/workspace.js && grep -q 'deleteObject' backend/app/templates/browser/tree_children.html && grep -q '.delete-btn' frontend/static/css/workspace.css && echo 'All checks pass'
