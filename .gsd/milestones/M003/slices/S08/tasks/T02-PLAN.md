---
estimated_steps: 5
estimated_files: 5
---

# T02: IconService SPARQL fallback + create-class/delete-class endpoints

**Slice:** S08 — In-App Class Creation
**Milestone:** M003

## Description

Wire the OntologyService class creation/deletion logic from T01 into HTTP endpoints on the ontology router. Extend IconService to resolve user-created type icons from the triplestore (SPARQL query on `urn:sempkm:user-types`) as a fallback when filesystem manifest cache misses. Store icon metadata as triples alongside the class definition.

## Steps

1. **Add `POST /browser/ontology/create-class` endpoint** to `ontology_router`:
   - Accepts form data: `name` (str), `icon` (str, Lucide icon name), `icon_color` (str, CSS color), `parent_iri` (str), `properties` (JSON string — list of `{name, predicate, datatype}` dicts)
   - Calls `ontology_service.create_class()` from T01
   - Returns `HX-Trigger: classCreated` header for TBox auto-refresh
   - Returns HTML snippet confirming creation (class name + IRI) for htmx swap
   - Returns HTTP 422 with error message on validation failure

2. **Add `DELETE /browser/ontology/delete-class` endpoint** to `ontology_router`:
   - Accepts query param `class_iri` (str)
   - Validates IRI starts with `urn:sempkm:user-types:` (only user-created classes can be deleted)
   - Calls `ontology_service.delete_class()`
   - Returns `HX-Trigger: classDeleted` header
   - Returns HTTP 403 if IRI is not a user-types class

3. **Extend IconService with SPARQL-based fallback** in `get_type_icon()`:
   - Add `_user_type_icons` cache dict (populated lazily)
   - Add `_load_user_type_icons()` method that queries `urn:sempkm:user-types` for `sempkm:typeIcon` and `sempkm:typeColor` triples
   - Since IconService is currently sync and per-request (created via FastAPI Depends), the simplest approach is to make `_load_user_type_icons()` a sync SPARQL query using the requests library against the triplestore HTTP endpoint, OR refactor `get_type_icon()` to check the user-types icon data passed in from the caller. Evaluate which is simpler — likely: add an optional `user_type_icons` dict parameter to `get_type_icon()` that callers can pre-populate from an async query.
   - Alternative (simpler): add `invalidate()` call path that also reloads user icons, and store user icon triples as a simple in-memory dict on the icon service, populated by a startup hook or on-demand async load. The key constraint is that IconService is currently sync.
   - **Chosen approach**: Add a `set_user_type_icons(icons: dict)` method to IconService that callers (the ontology router) can call after creating a class. The `get_type_icon()` method checks `_user_type_icons` dict before returning fallback. The `_user_type_icons` is populated lazily from SPARQL by a new async `load_user_type_icons(client)` classmethod/standalone function.

4. **Add endpoint-level unit tests** to `test_class_creation.py`:
   - Test POST endpoint validation (missing name → 422)
   - Test POST endpoint success path (mock OntologyService, verify HX-Trigger header)
   - Test DELETE endpoint rejects non-user-types IRIs
   - Test DELETE endpoint success path
   - Test IconService user-type icon lookup

5. **Wire icon loading into the create-class and TBox rendering paths** — after class creation, update the icon cache so the TBox tree immediately shows the correct icon. The `get_icon_service()` dependency in `_helpers.py` may need a small extension to support user-type icon loading.

## Must-Haves

- [ ] POST endpoint creates class and returns HX-Trigger: classCreated
- [ ] POST endpoint returns 422 on validation failure with error message
- [ ] DELETE endpoint removes class+shape triples and returns HX-Trigger: classDeleted
- [ ] DELETE endpoint rejects non-user-types IRIs with 403
- [ ] IconService resolves user-created type icons from triplestore data
- [ ] Endpoint tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all tests pass including new endpoint tests
- Manual: `curl -X POST /browser/ontology/create-class` with test data returns 200 with classCreated trigger

## Observability Impact

- Signals added/changed: HTTP 422 structured error response on validation failure; HX-Trigger headers for htmx event propagation; INFO log on successful class creation/deletion with class IRI
- How a future agent inspects this: check HTTP response headers for HX-Trigger; check response body for error messages; query `urn:sempkm:user-types` graph via SPARQL console
- Failure state exposed: 422 validation errors with field-level messages; 403 for unauthorized delete attempts; 500 with server log on triplestore errors

## Inputs

- `backend/app/ontology/service.py` — `create_class()`, `delete_class()` from T01
- `backend/app/ontology/router.py` — existing ontology router structure
- `backend/app/services/icons.py` — existing IconService with filesystem-only cache
- `backend/app/browser/_helpers.py` — `get_icon_service()` dependency

## Expected Output

- `backend/app/ontology/router.py` — two new endpoints: POST create-class, DELETE delete-class
- `backend/app/services/icons.py` — extended with user-type icon support
- `backend/app/browser/_helpers.py` — possible extension for user-type icon loading
- `backend/tests/test_class_creation.py` — extended with endpoint + icon tests
