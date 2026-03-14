---
estimated_steps: 5
estimated_files: 4
---

# T04: Add Custom section to Mental Models page

**Slice:** S03 — Custom Section on Mental Models + Property Edit
**Milestone:** M004

## Description

Add the "Custom" section to the Mental Models admin page, rendering all user-created types and properties with inline edit and delete actions. Extend `admin_models()` to call `list_user_types()` and pass the result to the template. Render classes and properties as separate tables. Handle the empty state with an encouraging message. Edit/delete actions work: class edit links to the Ontology Viewer, property edit opens an htmx modal on the page itself (fetching the same `edit_property_form.html`), delete buttons use htmx with `hx-confirm`. Add a property-edit overlay to the admin page. Add CSS for the Custom section tables.

## Steps

1. **Extend `admin_models()` handler** — Import `OntologyService` dependency (already available via `get_ontology_service`). Call `ontology_service.list_user_types()` and pass the result as `custom_types` to the template context. Wrap in try/except so gist summary failure doesn't break the page.

2. **Add Custom section template block in `models.html`** — After the Installed Models section, add `<h3 class="section-label">Custom</h3>`. If `custom_types` has no classes and no properties, show empty state: a `<div class="custom-empty-state">` with text like "No custom types or properties yet" and a link to the Ontology Viewer's Create buttons.

3. **Render classes and properties tables** — If classes exist, render a table with columns: Name (with icon), Parent, Actions (edit link to `/browser/#ontology-viewer`, delete button with `hx-delete="/browser/ontology/delete-class"` + `hx-confirm`). If properties exist, render a table with columns: Name, Type (Object/Datatype badge), Domain, Range, Actions (edit button triggers modal, delete button with `hx-delete="/browser/ontology/delete-property"` + `hx-confirm`). Tables use `sparql-results` class for consistent styling.

4. **Add property-edit overlay + JS on admin page** — Add a `#admin-property-edit-overlay` div (same `ccf-overlay` / `ccf-modal` pattern). Add `openAdminPropertyEdit(encodedIri)` / `closeAdminPropertyEdit()` JS functions. On `propertyEdited` event, close modal and reload the Custom section via htmx (or page refresh). Include the overlay only when `custom_types` has properties (or always include for simplicity).

5. **Add CSS for Custom section** — Style `.custom-empty-state` with muted text and centered layout. Style `.custom-type-badge` for Object/Datatype type indicators. Style action buttons in Custom tables to match the admin page button patterns (`btn-sm`, `btn-warning`, `btn-danger`). Ensure tables are responsive at admin page widths.

## Must-Haves

- [ ] `admin_models()` passes `custom_types` to template
- [ ] Custom section renders after Installed Models with `<h3 class="section-label">Custom</h3>`
- [ ] Empty state shown when no user types or properties exist
- [ ] Classes table shows name, parent, edit/delete actions
- [ ] Properties table shows name, type, domain, range, edit/delete actions
- [ ] Property edit opens modal with `edit_property_form.html` (fetched via htmx)
- [ ] Delete actions use `hx-delete` with `hx-confirm` and trigger page/section refresh

## Verification

- Browser: navigate to Mental Models page → Custom section visible below Installed Models
- Browser: with no user types, Custom section shows empty state message with link to Ontology Viewer
- Browser: create a class + property in Ontology Viewer → navigate to Mental Models → Custom section shows both
- Browser: click edit on a property in Custom section → modal opens with pre-populated form
- Browser: delete a property from Custom section → property removed, section refreshes

## Observability Impact

- Signals added/changed: `list_user_types()` call logged at info level from T01; `logger.warning` on `list_user_types()` failure in admin handler
- How a future agent inspects this: inspect `custom_types` template context; view Mental Models page source for Custom section HTML
- Failure state exposed: if `list_user_types()` fails, Custom section shows graceful fallback (empty state or error message) rather than breaking the page

## Inputs

- `backend/app/admin/router.py` — existing `admin_models()` handler (line ~60) with `ontology_service` dependency already available
- `backend/app/templates/admin/models.html` — existing page structure with Upper Ontology and Installed Models sections
- `backend/app/ontology/service.py` — `list_user_types()` from T01
- `backend/app/ontology/router.py` — existing delete-class, delete-property routes consumed by htmx buttons
- T02 output: `/ontology/edit-property-form` route for the modal
- `frontend/static/css/style.css` — existing `.section-label`, `.upper-ontology-*` CSS classes

## Expected Output

- `backend/app/admin/router.py` — `admin_models()` extended to call `list_user_types()` and pass `custom_types`
- `backend/app/templates/admin/models.html` — Custom section added (~80 lines of Jinja2)
- `frontend/static/css/style.css` — Custom section CSS (~30 lines)
- `backend/app/templates/admin/models.html` — property-edit overlay + JS for admin page
