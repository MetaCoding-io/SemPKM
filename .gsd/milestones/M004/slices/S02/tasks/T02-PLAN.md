---
estimated_steps: 5
estimated_files: 4
---

# T02: Add delete-property route + delete-class-check route + endpoint tests

**Slice:** S02 — Delete + Instance Warnings
**Milestone:** M004

## Description

Add the HTTP endpoints that connect the new service methods to the UI: `DELETE /ontology/delete-property` for property removal with namespace guard, and `GET /ontology/delete-class-check` that returns a confirmation HTML fragment with dynamic instance/subclass counts. Create the `delete_class_confirm.html` template. Write endpoint-level unit tests for both routes.

## Steps

1. Add `DELETE /ontology/delete-property` route to `router.py` — follows the existing `delete-class` pattern. Takes `property_iri` as Query param. Guards on `USER_TYPES_GRAPH:` prefix. Calls `ontology_service.delete_property()`. Returns 200 with `HX-Trigger: propertyDeleted` on success, 403 on namespace violation, 500 on error. Log warnings/errors.

2. Add `GET /ontology/delete-class-check` route to `router.py` — takes `class_iri` as Query param. Guards on `USER_TYPES_GRAPH:` prefix. Calls `ontology_service.get_delete_class_info()`. Renders `delete_class_confirm.html` template with the returned data. Returns 403 on namespace violation, 500 on error.

3. Create `delete_class_confirm.html` template — shows class label, instance count with warning message (e.g. "This class has N instances that will lose their type"), subclass count with warning (e.g. "N subclasses will become root classes"), and two buttons: "Cancel" (calls `closeDeleteConfirm()`) and "Confirm Delete" (uses `hx-delete` to call the existing delete-class endpoint with `hx-swap="none"`, and calls `closeDeleteConfirm()` on success via `hx-on::after-request`). Style warning counts with red/amber coloring.

4. Write endpoint test `TestDeletePropertyEndpoint` — test 403 rejection for non-user-types IRI, test 200 success with HX-Trigger header.

5. Write endpoint test `TestDeleteClassCheckEndpoint` — test 403 rejection for non-user-types IRI, test 200 success returns HTML containing instance count.

## Must-Haves

- [ ] `DELETE /ontology/delete-property` returns 200 + `HX-Trigger: propertyDeleted` on success
- [ ] `DELETE /ontology/delete-property` returns 403 for non-user-types IRI
- [ ] `GET /ontology/delete-class-check` returns HTML with instance count and subclass count
- [ ] `GET /ontology/delete-class-check` returns 403 for non-user-types IRI
- [ ] `delete_class_confirm.html` has Cancel and Confirm Delete buttons
- [ ] Confirm Delete button calls existing `DELETE /ontology/delete-class` endpoint
- [ ] All new endpoint tests pass

## Verification

- `cd backend && python -m pytest tests/test_class_creation.py -v -k "delete_property_endpoint or delete_class_check"` — all pass
- `cd backend && python -m pytest tests/test_class_creation.py -v` — all tests pass including existing ones

## Observability Impact

- Signals added/changed: `logger.warning` on namespace guard violations for delete-property; `logger.error` on SPARQL failures
- How a future agent inspects this: HTTP response status codes (200/403/500) and HX-Trigger headers
- Failure state exposed: 403 response body says "Only user-created properties can be deleted"; 500 body says "Server error"

## Inputs

- `backend/app/ontology/service.py` — `delete_property()` and `get_delete_class_info()` from T01
- `backend/app/ontology/router.py` — existing `delete_class` route as pattern
- `backend/tests/test_class_creation.py` — `TestDeleteClassEndpoint` pattern, `_make_fake_app_state()` helper

## Expected Output

- `backend/app/ontology/router.py` — two new routes added (`delete-property`, `delete-class-check`)
- `backend/app/templates/browser/ontology/delete_class_confirm.html` — confirmation fragment template
- `backend/tests/test_class_creation.py` — `TestDeletePropertyEndpoint`, `TestDeleteClassCheckEndpoint` test classes added
