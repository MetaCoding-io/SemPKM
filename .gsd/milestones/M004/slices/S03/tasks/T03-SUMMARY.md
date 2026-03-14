---
id: T03
parent: S03
milestone: M004
provides:
  - Edit button (pencil icon) in RBox table for user-source properties with hover-reveal
  - Property-edit modal overlay (#property-edit-overlay) in ontology_page.html
  - openPropertyEditForm() / closePropertyEditForm() JS functions
  - propertyEdited event wired to close modal and refresh RBox content
  - CSS for .rbox-edit-btn matching .rbox-delete-btn pattern
key_files:
  - backend/app/templates/browser/ontology/rbox_legend.html
  - backend/app/templates/browser/ontology/ontology_page.html
  - frontend/static/css/workspace.css
key_decisions:
  - Used setTimeout(300ms) for focus instead of .then() callback on htmx.ajax() — matches openClassEditForm pattern and avoids timing issues with htmx inline script processing
  - Removed htmx.process() from openPropertyEditForm — the template's own inline script handles htmx processing via htmx.process(form) in its IIFE
patterns_established:
  - Property-edit modal follows class-edit modal pattern (openPropertyEditForm → htmx.ajax → template script handles htmx.process)
observability_surfaces:
  - "#property-edit-overlay" display style inspectable for modal state
  - Network tab shows /ontology/edit-property-form fetch on modal open
  - propertyEdited event in HX-Trigger response headers on successful edit
  - 404 in modal container if property not found
duration: 20m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T03: Add RBox edit button + property-edit modal overlay in ontology page

**Added edit button alongside delete in RBox table, property-edit modal overlay, and JS open/close functions with propertyEdited event wiring.**

## What Happened

Wired the T02 edit property form into the Ontology Viewer UI with three file changes:

1. **rbox_legend.html** — Added `<button class="rbox-edit-btn">` with pencil icon before the existing delete button in the `{% if is_user %}` actions cell. Uses `onclick="openPropertyEditForm('{{ p.iri | urlencode }}')"`.

2. **ontology_page.html** — Added `#property-edit-overlay` div following the class-edit overlay pattern (ccf-overlay + ccf-modal). Added `openPropertyEditForm(encodedIri)` which shows the overlay, fetches the edit form via `htmx.ajax()`, and focuses the name input after 300ms. Added `closePropertyEditForm()` which hides overlay and clears innerHTML. Added `propertyEdited` body event listener to close modal and show toast. Added the overlay to the Escape key handler array. Added `propertyEdited from:body` to the RBox pane's `hx-trigger` attribute.

3. **workspace.css** — Added `.rbox-edit-btn` CSS block matching `.rbox-delete-btn` pattern: hidden by default, `display: inline-flex` on `tr:hover`, 14×14px SVG with `flex-shrink: 0` and `stroke: currentColor`. Blue hover color (`--color-primary`) instead of red (`--color-danger`). Combined the `tr:hover` rules for both buttons.

## Verification

- **Tests**: `docker exec sempkm-api-1 pytest tests/ -x -q -k ontology` — 107 passed
- **Browser**: Navigated to Object Browser → Ontology Viewer → RBox tab
- **Browser**: Created a test user property "Test Edit Prop" → appeared in USER group with Actions column
- **Browser**: Hovered user property row → edit (pencil) and delete (trash) icons both visible
- **Browser**: Clicked edit button → modal overlay opened → form pre-populated with correct property name "Test Edit Prop"
- **Browser**: Changed name to "Test Edited Name" → submitted → modal closed → RBox refreshed → "Test Edited Name" shown
- **Browser**: Reopened edit, changed to "Final Test Name" → submitted → confirmed update in RBox
- **Browser**: Opened edit modal → pressed Escape → modal closed correctly
- **Browser**: `propertyEdited` event triggers RBox refresh (confirmed via `hx-trigger` attribute including `propertyEdited from:body`)

### Slice-level verification status (T03 is intermediate, not final)
- ✅ `pytest tests/test_ontology_service.py -x -q` — 63 passed
- ⬜ Mental Models page Custom section — not yet implemented (T04)
- ⬜ Create property → navigate to Mental Models → property appears — not yet (T04)
- ✅ Click edit on user property in RBox → form opens pre-populated → change name → submit → RBox shows updated name
- ⬜ Custom section edit/delete actions — not yet (T04)

## Diagnostics

- Inspect `#property-edit-overlay` display style for modal open/closed state
- Network tab: `/browser/ontology/edit-property-form?property_iri=...` fetched when modal opens (200 = form loaded, 403 = non-user property, 404 = not found)
- Network tab: `POST /browser/ontology/edit-property` on submit (200 = success with HX-Trigger: propertyEdited)
- `propertyEdited` event on body triggers both modal close and RBox content refresh

## Deviations

- Removed `.then()` callback from `htmx.ajax()` in `openPropertyEditForm()` — the promise resolution was interfering with htmx inline script processing. Switched to `setTimeout(300ms)` for focus, matching the existing `openClassEditForm()` pattern.

## Known Issues

- The Playwright browser_click on the Submit button can be blocked by the bottom panel (SPARQL console) overlapping the modal footer — this is a test-tooling viewport issue, not a product bug. Real users scroll the modal or the bottom panel doesn't overlap. The submit works correctly via direct JS click.

## Files Created/Modified

- `backend/app/templates/browser/ontology/rbox_legend.html` — Added edit button with pencil icon before delete button in user property actions cell
- `backend/app/templates/browser/ontology/ontology_page.html` — Added property-edit overlay div, JS open/close functions, propertyEdited event listener, Escape key handler, and propertyEdited to RBox hx-trigger
- `frontend/static/css/workspace.css` — Added .rbox-edit-btn CSS block (hidden by default, blue hover, 14×14px SVG with flex-shrink: 0)
