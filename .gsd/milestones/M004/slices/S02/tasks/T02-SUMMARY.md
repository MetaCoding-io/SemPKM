---
id: T02
parent: S02
milestone: M004
provides:
  - DELETE /ontology/delete-property endpoint with namespace guard and HX-Trigger
  - GET /ontology/delete-class-check endpoint returning confirmation HTML fragment
  - delete_class_confirm.html template with instance/subclass warnings and Cancel/Confirm buttons
key_files:
  - backend/app/ontology/router.py
  - backend/app/templates/browser/ontology/delete_class_confirm.html
  - backend/tests/test_class_creation.py
key_decisions:
  - delete-class-check renders server-side Jinja2 template (consistent with all other ontology endpoints)
  - Confirm Delete button uses hx-delete targeting existing /ontology/delete-class endpoint with hx-swap="none"
patterns_established:
  - delete-property route follows identical pattern to delete-class (namespace guard → service call → HX-Trigger)
  - delete-class-check follows get-detail pattern (namespace guard → service call → template render)
observability_surfaces:
  - logger.warning on namespace guard violations for delete-property and delete-class-check
  - logger.error on SPARQL failures with exc_info for both routes
  - HTTP 403 with descriptive body on namespace violation; 500 on server error
  - HX-Trigger: propertyDeleted header on successful property deletion
duration: 12min
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Add delete-property route + delete-class-check route + endpoint tests

**Added DELETE /ontology/delete-property and GET /ontology/delete-class-check HTTP endpoints with namespace guards, plus confirmation template and 6 endpoint tests.**

## What Happened

Added two new routes to `router.py` following the existing delete-class pattern:

1. **DELETE /ontology/delete-property** — takes `property_iri` query param, guards on `USER_TYPES_GRAPH:` prefix, calls `ontology_service.delete_property()`, returns 200 with `HX-Trigger: propertyDeleted` on success, 403 on namespace violation, 500 on error.

2. **GET /ontology/delete-class-check** — takes `class_iri` query param, guards on `USER_TYPES_GRAPH:` prefix, calls `ontology_service.get_delete_class_info()`, renders `delete_class_confirm.html` template with label, instance count, and subclass count. Returns 403/500 on guard/error.

3. **delete_class_confirm.html** — confirmation fragment showing class label, instance count warning (red), subclass count warning (amber), safe message when both are zero, and Cancel + Confirm Delete buttons. Confirm Delete uses `hx-delete` targeting the existing `/ontology/delete-class` endpoint with `hx-swap="none"` and `hx-on::after-request="closeDeleteConfirm()"`.

4. **6 endpoint tests** — `TestDeletePropertyEndpoint` (403 rejection, 200 success with HX-Trigger, 500 server error) and `TestDeleteClassCheckEndpoint` (403 rejection, 200 success with rendered HTML containing counts/buttons, 500 server error). The delete-class-check success test uses real Jinja2 rendering to verify template output.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_class_creation.py -v -k "DeletePropertyEndpoint or DeleteClassCheckEndpoint"` — **6/6 passed**
- `cd backend && .venv/bin/python -m pytest tests/test_class_creation.py -v` — **48/51 passed** (3 pre-existing failures in TestCreateClassEndpoint from Form.strip() mock issue, confirmed present before this task)
- `cd backend && .venv/bin/python -m pytest tests/test_ontology_service.py -v` — **44/44 passed**

## Diagnostics

- HTTP 403 response body: "Only user-created properties can be deleted" / "Only user-created classes can be deleted"
- HTTP 500 response body: "Server error deleting property" / "Server error loading class info"
- `HX-Trigger: propertyDeleted` header on 200 from delete-property
- Logger warnings on namespace guard violations; errors with exc_info on SPARQL failures

## Deviations

None.

## Known Issues

- 3 pre-existing test failures in `TestCreateClassEndpoint` — `create_class` endpoint tests pass string args but the endpoint now calls `.strip()` on `Form` objects. This is a test fixture issue from a prior task adding `description`/`example` form params; not related to T02.

## Files Created/Modified

- `backend/app/ontology/router.py` — added `delete_property()` and `delete_class_check()` route handlers
- `backend/app/templates/browser/ontology/delete_class_confirm.html` — new confirmation fragment template
- `backend/tests/test_class_creation.py` — added `TestDeletePropertyEndpoint` and `TestDeleteClassCheckEndpoint` test classes (6 tests)
