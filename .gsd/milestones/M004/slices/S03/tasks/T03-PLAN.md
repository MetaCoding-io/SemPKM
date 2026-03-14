---
estimated_steps: 5
estimated_files: 3
---

# T03: Add RBox edit button + property-edit modal overlay in ontology page

**Slice:** S03 — Custom Section on Mental Models + Property Edit
**Milestone:** M004

## Description

Wire the edit property form into the Ontology Viewer UI. Add an edit button alongside the existing delete button in the RBox table for user-source properties. Add a property-edit modal overlay in `ontology_page.html` (same pattern as the class-edit overlay). Add JS functions to open/close the property-edit modal. Add CSS for the edit button. Wire the `propertyEdited` event to close the modal and refresh the RBox tab content.

## Steps

1. **Add edit button to `rbox_legend.html`** — Inside the `{% if is_user %}` actions cell, add an edit button before the delete button. Use `<button type="button" class="rbox-edit-btn" onclick="openPropertyEditForm('{{ p.iri | urlencode }}')">` with a `<i data-lucide="pencil"></i>` icon. The button follows the same hover-reveal pattern as the delete button.

2. **Add property-edit overlay to `ontology_page.html`** — Add a new `#property-edit-overlay` div following the class-edit overlay pattern. It should use `ccf-overlay` / `ccf-modal` classes. The container div gets `id="property-edit-container"`. No `hx-trigger` — content is loaded imperatively via `openPropertyEditForm()`.

3. **Add JS open/close functions** — `openPropertyEditForm(encodedIri)`: show overlay, fetch `/browser/ontology/edit-property-form?property_iri={encodedIri}` via htmx into `#property-edit-container`, then call `htmx.process()` on the loaded form. `closePropertyEditForm()`: hide overlay, clear container innerHTML. Wire `propertyEdited` body event to close modal, show toast, and trigger RBox refresh.

4. **Add CSS for `.rbox-edit-btn`** — Same pattern as `.rbox-delete-btn` (hidden by default, `display: inline-flex` on `tr:hover`). Use pencil icon, blue hover color instead of red. Size SVG at 14×14px with `flex-shrink: 0` and `stroke: currentColor` per CLAUDE.md rules.

5. **Wire RBox refresh on propertyEdited** — Add `propertyEdited from:body` to the RBox tab's `hx-trigger` attribute (alongside existing triggers like `propertyDeleted`) so the RBox content auto-refreshes after a property edit.

## Must-Haves

- [ ] Edit button visible on hover for user-source properties in RBox table
- [ ] Clicking edit button opens property-edit overlay with pre-populated form
- [ ] `closePropertyEditForm()` hides overlay and clears content
- [ ] `propertyEdited` event closes modal and refreshes RBox content
- [ ] CSS follows existing `.rbox-delete-btn` pattern with `flex-shrink: 0` on SVGs

## Verification

- Browser: open Ontology Viewer → RBox tab → hover a user-created property row → edit button (pencil icon) visible alongside delete button
- Browser: click edit button → modal overlay opens → form is pre-populated with correct property values
- Browser: submit edit → modal closes → RBox table shows updated property name

## Observability Impact

- Signals added/changed: `#property-edit-overlay` visibility state inspectable via `style.display`; network tab shows `/ontology/edit-property-form` fetch on modal open
- How a future agent inspects this: inspect `#property-edit-overlay` display state; check for `propertyEdited` event in HX-Trigger response headers
- Failure state exposed: 404 in modal container if property not found; network errors visible in browser console

## Inputs

- `backend/app/templates/browser/ontology/rbox_legend.html` — existing delete button pattern in `{% if is_user %}` block
- `backend/app/templates/browser/ontology/ontology_page.html` — existing 4 modal overlays (class-creation, property-creation, class-edit, delete-confirm) as pattern
- `frontend/static/css/workspace.css` — existing `.rbox-delete-btn` CSS (lines ~415-440) as pattern
- T02 output: `edit_property_form.html` template and `/ontology/edit-property-form` route

## Expected Output

- `backend/app/templates/browser/ontology/rbox_legend.html` — edit button added in user-property actions cell
- `backend/app/templates/browser/ontology/ontology_page.html` — property-edit overlay div + JS functions added
- `frontend/static/css/workspace.css` — `.rbox-edit-btn` CSS block added
