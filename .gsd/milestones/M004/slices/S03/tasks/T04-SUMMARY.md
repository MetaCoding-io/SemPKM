---
id: T04
parent: S03
milestone: M004
provides:
  - Custom section on Mental Models admin page listing all user-created classes and properties
  - Property-edit modal overlay on admin page reusing edit_property_form.html
key_files:
  - backend/app/admin/router.py
  - backend/app/templates/admin/models.html
  - frontend/static/css/style.css
key_decisions:
  - Used window.location.reload() on propertyEdited and after delete to refresh the Custom section rather than htmx partial swap — simpler and avoids needing a dedicated partial endpoint for the custom section
  - Reused the same /browser/ontology/edit-property-form and /browser/ontology/delete-property endpoints from the Ontology Viewer rather than creating separate admin-prefixed routes
patterns_established:
  - Admin page modal overlay follows same ccf-overlay/ccf-modal pattern from workspace with page-specific ID prefix (admin-property-edit-)
observability_surfaces:
  - logger.warning on list_user_types() failure in admin_models() handler — Custom section degrades to empty state
  - Network tab: /browser/ontology/edit-property-form?property_iri=... fetched when edit modal opens
  - Network tab: DELETE /browser/ontology/delete-class and /browser/ontology/delete-property from Custom section
duration: 20min
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T04: Add Custom section to Mental Models page

**Added Custom section to Mental Models admin page showing user-created classes and properties with edit/delete actions and property-edit modal.**

## What Happened

Extended `admin_models()` to call `ontology_service.list_user_types()` and pass the result as `custom_types` to the template, wrapped in try/except for graceful degradation. Added the Custom section template block after Installed Models with three states: empty state (encouraging message + link to Ontology Viewer), classes table (name, parent, edit/delete), and properties table (name, type badge, domain, range, edit/delete). Property edit opens a modal overlay (`#admin-property-edit-overlay`) that fetches the same `edit_property_form.html` via htmx. Delete buttons use `hx-delete` with `hx-confirm` and reload the page on success. Added CSS for empty state, subsection labels, type badges (Object/Datatype), and action button spacing.

## Verification

- **Tests:** `pytest tests/test_ontology_service.py -x -q` — 63 passed
- **Browser (empty state):** Navigated to Mental Models page with no custom types → Custom section shows "No custom types or properties yet" with link to Ontology Viewer ✅
- **Browser (populated):** Created class (TestWidget) and property (testRelation) in Ontology Viewer → navigated to Mental Models → Custom section shows both in separate tables with correct columns ✅
- **Browser (property edit):** Clicked Edit on testRelation in Custom section → modal opens with pre-populated form (name, type, domain, range, description) ✅
- **Browser (modal close):** Pressed Escape → modal closes ✅
- **Assertions:** All 8 browser assertions passed (CUSTOM text, Classes/Properties subsections, TestWidget, testRelation, Object badge, table selectors)

### Slice-level checks:
- ✅ `pytest tests/test_ontology_service.py -x -q` — 63 passed (list_user_types, get_property_for_edit, edit_property tests)
- ✅ Browser: Mental Models page → Custom section visible with classes/properties or empty state
- ✅ Browser: create a property in Ontology Viewer → navigate to Mental Models → property appears in Custom section
- ✅ Browser: click edit on a user property in RBox (from T03) — verified in T03
- ✅ Browser: Custom section edit/delete actions trigger correct endpoints

## Diagnostics

- Inspect `custom_types` template context for class/property counts
- View Mental Models page source for Custom section HTML
- If `list_user_types()` fails, Custom section shows empty state with warning logged

## Deviations

- Used `hx-on::after-request="if(event.detail.successful) window.location.reload()"` on delete buttons instead of htmx partial swap — no dedicated partial endpoint exists for just the Custom section, and full page reload is simpler and ensures all counts/state are fresh.

## Known Issues

None.

## Files Created/Modified

- `backend/app/admin/router.py` — Extended `admin_models()` to call `list_user_types()` and pass `custom_types` to template context
- `backend/app/templates/admin/models.html` — Added Custom section with classes/properties tables, empty state, property-edit overlay, and JS functions
- `frontend/static/css/style.css` — Added Custom section CSS (~65 lines): empty state, subsection labels, type badges, type icons, action button spacing
