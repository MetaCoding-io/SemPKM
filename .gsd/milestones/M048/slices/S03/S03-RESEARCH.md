# S03: Object Delete UI — Research

**Researched:** 2026-04-05
**Depth:** Light — straightforward UI wiring to existing backend endpoint

---

## Summary

This slice adds single-object delete capability to three UI surfaces: the object toolbar (header bar), the explorer tree (hover action), and the command palette. The backend `POST /browser/objects/delete` endpoint already exists and works correctly for bulk deletion. The only backend change needed is adding **inbound edge cleanup** — the current implementation only deletes triples where the object is the subject (`<iri> ?p ?o`), not where it's the object (`?s ?p <iri>`), leaving dangling references. Decision D384 confirms this should be done.

All UI patterns needed are already established in the codebase — this is pure wiring.

---

## Recommendation

Three tasks:
1. **Backend: Inbound edge cleanup** — Add a second SPARQL query to `bulk_delete_objects()` in `objects.py` to also fetch and delete triples matching `?s ?p <iri>` from the current graph. Small, testable, unblocks correct delete behavior.
2. **Frontend: Delete button on object toolbar + command palette entry** — Add a trash button to `object_tab.html`, wire `SemPKM.deleteObject()` in `workspace.js` using existing `showConfirmDialog()` and `apiFetch('/browser/objects/delete', ...)`, close tab + refresh tree after success. Add "Delete Object" to the ninja-keys command palette.
3. **Frontend: Explorer tree hover delete action** — Add a `tree-leaf-action` trash button to `tree_children.html` (the pattern already exists in `dashboard_explorer.html`), wire click handler via `SemPKM.deleteObject()`.

---

## Implementation Landscape

### Backend — Existing Delete Endpoint

**File:** `backend/app/browser/objects.py` lines 1014–1111

- `POST /browser/objects/delete` accepts `{"iris": [...]}`, queries triples per IRI, creates `Operation` with `materialize_deletes`, commits via `EventStore`.
- **Gap:** Only queries `<iri> ?p ?o` (outbound triples). Does NOT query `?s ?p <iri>` (inbound edges). Per D384, inbound edge cleanup must be added.
- Fix: Add a second SPARQL query per IRI:
  ```sparql
  SELECT ?s ?p WHERE {
    GRAPH <urn:sempkm:current> {
      ?s ?p <{iri}> .
    }
  }
  ```
  Append those `(subject, pred, URIRef(iri))` triples to `materialize_deletes`.

### Frontend — Object Toolbar (Template)

**File:** `backend/app/templates/browser/object_tab.html`

- Toolbar actions div (`.object-toolbar-actions`) contains: star button, properties toggle badge, mode toggle ("Edit"), save button.
- **Add:** A delete button (`<button class="delete-btn" ...>`) with `<i data-lucide="trash-2"></i>`, placed after the star button and before the properties badge. Should call `SemPKM.deleteObject('{{ object_iri }}', '{{ object_label | e }}')`.
- Button needs `onclick="event.stopPropagation(); SemPKM.deleteObject(...)"`.
- Template has access to `object_iri` and `object_label` in its context.

### Frontend — Delete Function

**File:** `frontend/static/js/workspace.js`

New `deleteObject(iri, label)` function:
1. Call `showConfirmDialog()` (line 3341) — existing utility, default confirm text is "Delete".
2. On confirm: `apiFetch('/browser/objects/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({iris: [iri]}) })`.
3. On success: `closeTab(iri)` (line 177), `refreshNavTree()` (line 1457), `showToast('Object deleted')`.
4. Expose as `window.SemPKM.deleteObject = deleteObject`.

**Existing utilities (all in scope via closure or window.SemPKM):**
- `showConfirmDialog(title, message, itemList, onConfirm, confirmText)` — line 3341
- `apiFetch(resource, options)` — from `api-fetch.js`, available as `window.apiFetch`
- `closeTab(objectIri)` — line 177, closes dockview panel
- `refreshNavTree()` — line 1457, reloads explorer tree
- `showToast(message, duration)` — line 26

### Frontend — Command Palette Entry

**File:** `frontend/static/js/workspace.js` around line 1560–1750

The command palette is initialized with a `commands` array of `{id, title, section, handler}` objects passed to `ninja-keys`. Add:
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
    var label = /* get from DOM or tab meta */;
    deleteObject(iri, label);
  }
}
```
`getActiveTabIri()` (line 218) returns the active panel's IRI.

### Frontend — Explorer Tree Hover Action

**File:** `backend/app/templates/browser/tree_children.html`

The established pattern from `dashboard_explorer.html`:
```html
<button class="tree-leaf-action btn-icon" title="Delete object"
        onclick="event.stopPropagation(); SemPKM.deleteObject('{{ obj.iri }}', '{{ obj.label | e }}')">
  <i data-lucide="trash-2"></i>
</button>
```
Insert inside each `.tree-leaf` div, after the `<span class="tree-leaf-label">`.

**CSS already exists:** `.tree-leaf .tree-leaf-action` (workspace.css line 8855) — opacity 0 by default, opacity 1 on `.tree-leaf:hover`, color changes to `--color-error` on hover. SVG styling at line 8877.

### Frontend — Delete Button CSS

**File:** `frontend/static/css/workspace.css`

New `.delete-btn` styles for the object toolbar button, following `.star-btn` pattern (line 2342):
- `display: inline-flex; align-items: center; justify-content: center; padding: 4px; border: none; background: transparent; color: var(--color-text-muted); cursor: pointer; border-radius: 4px;`
- Hover: `color: var(--color-error)` (red on hover)
- SVG: `width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor;` (per CLAUDE.md flex-shrink rule)

---

## Boundary Contracts

| Surface | Trigger | Backend Call | Post-Action |
|---------|---------|-------------|-------------|
| Object toolbar button | Click trash icon | `POST /browser/objects/delete` `{iris: [iri]}` | Close tab, refresh tree, toast |
| Explorer tree hover | Click trash icon on leaf hover | Same endpoint | Close tab (if open), refresh tree, toast |
| Command palette | Select "Delete Object" | Same endpoint (active tab IRI) | Close tab, refresh tree, toast |

All three surfaces reuse the same `deleteObject(iri, label)` function.

---

## Files Likely Touched

| File | Change |
|------|--------|
| `backend/app/browser/objects.py` | Add inbound edge query to `bulk_delete_objects()` |
| `backend/app/templates/browser/object_tab.html` | Add delete button to toolbar |
| `backend/app/templates/browser/tree_children.html` | Add hover delete action button |
| `frontend/static/js/workspace.js` | Add `deleteObject()`, command palette entry, export |
| `frontend/static/css/workspace.css` | Add `.delete-btn` styles |

---

## Risks

None significant. All patterns are established. The only "new" code is the inbound edge SPARQL query (~10 lines) and the `deleteObject()` JS function (~20 lines).

---

## Skill Discovery

No external skills needed — this is standard htmx/JS/Python/SPARQL work using established codebase patterns.
