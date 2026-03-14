---
estimated_steps: 5
estimated_files: 6
---

# T03: Wire delete confirmation modal + RBox delete buttons in templates

**Slice:** S02 — Delete + Instance Warnings
**Milestone:** M004

## Description

Connect the backend endpoints to the frontend UI. Replace the static `hx-confirm` on TBox delete buttons with an `onclick` handler that opens a confirmation modal (fetching dynamic instance/subclass counts). Add delete buttons for user-created properties in the RBox table. Update the RBox `hx-trigger` to auto-refresh on `propertyDeleted`. Add CSS for RBox delete buttons.

## Steps

1. Add delete-confirmation overlay to `ontology_page.html` — new `#delete-confirm-overlay` div following the existing overlay pattern (class-creation, property-creation, class-edit). Add JS functions: `openDeleteClassConfirm(classIri)` fetches `/ontology/delete-class-check?class_iri=...` into `#delete-confirm-container` and shows the overlay; `closeDeleteConfirm()` hides it. Register in the Escape key handler array. Register an htmx `afterRequest` listener on the container that closes the overlay and triggers TBox refresh after successful deletion.

2. Replace TBox delete buttons in `tbox_tree.html` — remove `hx-delete` and `hx-confirm` attributes from the delete button for user-types classes. Replace with `onclick="event.stopPropagation(); openDeleteClassConfirm('{{ cls.iri }}')"`. Same change in `tbox_children.html`.

3. Add delete buttons for user properties in `rbox_legend.html` — inside the `render_property_table` macro, add a conditional delete button column for rows where `'user-types' in p.iri`. Button uses `hx-delete="/browser/ontology/delete-property?property_iri={{ p.iri | urlencode }}"` with `hx-confirm="Delete this property? It will be removed from the ontology."` and `hx-swap="none"`. Add the "Actions" column header conditionally.

4. Update RBox `hx-trigger` in `ontology_page.html` — change `hx-trigger="propertyCreated from:body"` to `hx-trigger="propertyCreated from:body, propertyDeleted from:body"`.

5. Add `.rbox-delete-btn` CSS to `workspace.css` — follow the `.tbox-delete-btn` pattern: hidden by default, visible on row hover, red on hover, `flex-shrink: 0` for Lucide SVG, `stroke: currentColor`.

## Must-Haves

- [ ] TBox delete button opens confirmation modal (not browser `confirm()`)
- [ ] Confirmation modal shows instance count and subclass count from server
- [ ] Confirming in modal deletes class and refreshes TBox tree
- [ ] Cancel or Escape closes confirmation modal without deletion
- [ ] RBox shows delete button on user-created property rows
- [ ] RBox deleting a property triggers `propertyDeleted` and RBox auto-refreshes
- [ ] Lucide icons render correctly in new buttons (flex-shrink: 0, stroke: currentColor)
- [ ] `_property_source` returning `'user'` causes RBox to show `user` badge for user-types properties

## Verification

- Docker up → open Ontology Viewer → verify TBox delete button on user class opens modal with counts → cancel works → confirm deletes and TBox refreshes
- Switch to RBox → verify delete button appears on user-created property rows → delete and confirm → RBox refreshes
- Press Escape while modal open → modal closes
- Verify no console errors after all operations

## Observability Impact

- Signals added/changed: None (frontend template changes only; backend signals already in T01/T02)
- How a future agent inspects this: inspect `#delete-confirm-overlay` visibility state; check htmx `hx-trigger` on RBox for `propertyDeleted`; check network tab for `/ontology/delete-class-check` requests
- Failure state exposed: Modal shows error message if check endpoint returns 403/500; htmx swap shows error div on delete failure

## Inputs

- `backend/app/ontology/router.py` — `GET /ontology/delete-class-check` and `DELETE /ontology/delete-property` routes from T02
- `backend/app/templates/browser/ontology/delete_class_confirm.html` — confirmation template from T02
- `backend/app/templates/browser/ontology/ontology_page.html` — existing overlay pattern
- `frontend/static/css/workspace.css` — existing `.tbox-delete-btn` styles as pattern

## Expected Output

- `backend/app/templates/browser/ontology/ontology_page.html` — delete confirmation overlay + JS functions + updated RBox hx-trigger
- `backend/app/templates/browser/ontology/tbox_tree.html` — delete buttons use `onclick` instead of `hx-delete`/`hx-confirm`
- `backend/app/templates/browser/ontology/tbox_children.html` — same change as tbox_tree.html
- `backend/app/templates/browser/ontology/rbox_legend.html` — delete buttons on user property rows
- `frontend/static/css/workspace.css` — `.rbox-delete-btn` styles added
