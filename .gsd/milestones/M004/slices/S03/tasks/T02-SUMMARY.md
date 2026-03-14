---
id: T02
parent: S03
milestone: M004
provides:
  - GET /ontology/edit-property-form route with namespace guard and pre-populated template
  - POST /ontology/edit-property route with namespace guard, validation, and HX-Trigger
  - edit_property_form.html template with read-only type, domain/range pickers, epf- prefixed IDs
key_files:
  - backend/app/ontology/router.py
  - backend/app/templates/browser/ontology/edit_property_form.html
  - backend/tests/test_ontology_service.py
key_decisions:
  - Namespace guard on GET route (edit_property_form) in addition to POST, unlike edit_class_form which only guards on POST — prevents form rendering for non-user properties
  - Used epf- ID prefix throughout template to avoid collision with cpf- create form IDs
patterns_established:
  - Route-level tests calling async handler functions directly with mock Request/User objects (no HTTP test client needed)
observability_surfaces:
  - logger.warning on namespace guard violations for both GET and POST edit-property routes
  - logger.error with exc_info=True on SPARQL failures in POST route
  - HTTP 403 (namespace guard), 404 (property not found), 422 (validation), 500 (server error) with descriptive HTML bodies
  - HX-Trigger: propertyEdited header on successful edit
duration: 1 step
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Add edit-property routes + edit_property_form.html template

**Added GET/POST edit-property routes with namespace guards and created edit_property_form.html template with pre-populated fields, read-only property type, and domain/range pickers.**

## What Happened

Added two new route handlers to `backend/app/ontology/router.py`:

1. **`GET /ontology/edit-property-form`** — Takes `property_iri` query param, decodes it, guards on `USER_TYPES_GRAPH:` prefix (403 if not), calls `get_property_for_edit()` (404 if None), renders `edit_property_form.html` with property data. Follows `edit_class_form()` pattern but adds namespace guard on GET (not just POST).

2. **`POST /ontology/edit-property`** — Takes form fields (property_iri, name, prop_type, domain_iri, range_iri, description), guards on namespace prefix, calls `edit_property()` service method, returns 200 with `HX-Trigger: propertyEdited` on success. Returns 403/422/500 on guard/validation/server errors.

Created `edit_property_form.html` template based on `create_property_form.html` with these adaptations:
- Pre-populates name, description from `prop` context
- Property type shown as disabled radios with hidden input preserving value (read-only)
- Domain field shows selected item with label if `prop.domain_iri` exists, search hidden
- Range field: object properties show class picker (pre-populated), datatype properties show dropdown (pre-selected)
- All IDs use `epf-` prefix to avoid collision with `cpf-` create form
- `htmx.process(form)` called for dynamically loaded form
- `propertyEdited` event listener closes modal and shows toast
- Lucide icons re-initialized

Added 7 route-level tests across 2 test classes:
- `TestEditPropertyFormRoute`: namespace guard 403, not-found 404, success renders template
- `TestEditPropertyRoute`: namespace guard 403, success 200 with HX-Trigger, validation 422, server error 500

## Verification

- `docker exec sempkm-api-1 pytest tests/test_ontology_service.py -x -q` — **63 passed** (56 existing + 7 new)
- `docker exec sempkm-api-1 pytest tests/test_ontology_service.py -k "TestEditPropertyFormRoute or TestEditPropertyRoute" -v` — **7 passed**
- Template file exists at `backend/app/templates/browser/ontology/edit_property_form.html` with correct structure (40 epf- prefixed IDs)

### Slice-level verification status (intermediate task):
- ✅ `docker exec sempkm-api-1 pytest tests/test_ontology_service.py -x -q` — 63 passed
- ⏳ Browser: Mental Models Custom section — not yet (T04)
- ⏳ Browser: create property → Mental Models → property appears — not yet (T04)
- ⏳ Browser: click edit on user property in RBox → form opens → edit → submit — not yet (T03 wires modal)
- ⏳ Browser: Custom section edit/delete actions — not yet (T04)

## Diagnostics

- Network tab: `/ontology/edit-property-form?property_iri=...` returns 200/403/404
- Network tab: `POST /ontology/edit-property` returns 200/403/422/500
- HX-Trigger `propertyEdited` header present on 200 response
- Grep logs for `edit-property-form namespace guard` or `edit-property namespace guard` for guard violations
- Grep logs for `edit-property validation error` for form validation failures
- Grep logs for `edit-property failed for` for server errors

## Deviations

- Added namespace guard on GET route (`edit_property_form`) which `edit_class_form` doesn't have — prevents rendering the form at all for non-user properties rather than only blocking the POST.
- Tests had to be `docker cp`'d into the container since `backend/tests/` is not volume-mounted (only `backend/app/` is).

## Known Issues

- Tests directory not volume-mounted in docker-compose.yml — tests must be copied into container for execution. This is a pre-existing issue, not introduced by this task.

## Files Created/Modified

- `backend/app/ontology/router.py` — Added `edit_property_form()` and `edit_property()` route handlers (~100 lines)
- `backend/app/templates/browser/ontology/edit_property_form.html` — New template (~190 lines) with pre-populated fields, read-only type, domain/range pickers
- `backend/tests/test_ontology_service.py` — Added `TestEditPropertyFormRoute` (3 tests) and `TestEditPropertyRoute` (4 tests), plus `_make_mock_request()` and `_make_mock_user()` helpers
