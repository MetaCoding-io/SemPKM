---
id: T02
parent: S08
milestone: M003
provides:
  - POST /browser/ontology/create-class endpoint with form data → OWL+SHACL creation
  - DELETE /browser/ontology/delete-class endpoint with user-types IRI guard
  - HX-Trigger headers (classCreated, classDeleted) for htmx TBox refresh
  - IconService.set_user_type_icons() for user-type icon overrides
  - IconService.get_type_icon() and get_icon_map() with user-type fallback
  - load_user_type_icons() async SPARQL loader for startup hydration
  - App-level user_type_icons cache on app.state
  - get_icon_service() dependency wired to pass user-type icons from app.state
key_files:
  - backend/app/ontology/router.py
  - backend/app/services/icons.py
  - backend/app/browser/_helpers.py
  - backend/app/main.py
  - backend/tests/test_class_creation.py
key_decisions:
  - Icon cache is app-level (app.state.user_type_icons dict), updated in-process on create/delete, hydrated from SPARQL at startup
  - IconService stays sync; user-type icons are injected via set_user_type_icons() from the get_icon_service() FastAPI dependency
  - get_icon_service() dependency now takes Request param to access app.state (was previously parameterless)
  - DELETE endpoint validates IRI prefix (urn:sempkm:user-types:) and returns 403 for non-user types
patterns_established:
  - _update_icon_cache() / _remove_from_icon_cache() helpers on the router for in-process icon cache management
  - load_user_type_icons(client) async standalone function in icons.py for SPARQL-based icon loading
  - Endpoint tests call router functions directly with MagicMock request objects (no TestClient needed)
observability_surfaces:
  - HTTP 422 with descriptive error message div on validation failure
  - HTTP 403 with message on non-user-types delete attempt
  - HX-Trigger headers (classCreated, classDeleted) for htmx event propagation
  - INFO log on successful class creation/deletion with class IRI (from OntologyService)
  - WARNING log on validation errors, non-user-types delete attempts
  - INFO log on user-type icon loading count at startup
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: IconService SPARQL fallback + create-class/delete-class endpoints

**Added POST/DELETE endpoints for class creation/deletion with HX-Trigger headers, extended IconService with user-type icon support via app-level cache and SPARQL loader, verified by 13 new tests (28 total).**

## What Happened

1. Added `POST /browser/ontology/create-class` endpoint to ontology_router — accepts form data (name, icon, icon_color, parent_iri, properties JSON), calls OntologyService.create_class(), returns HTML confirmation with HX-Trigger: classCreated header. Returns 422 on validation failure with descriptive error message.

2. Added `DELETE /browser/ontology/delete-class` endpoint — accepts class_iri query param, validates it starts with `urn:sempkm:user-types:` (returns 403 otherwise), calls OntologyService.delete_class(), returns HX-Trigger: classDeleted.

3. Extended IconService with `set_user_type_icons(icons)` method and updated `get_type_icon()` / `get_icon_map()` to check user-type icons as fallback after manifest cache. User-type icons don't override manifest icons.

4. Added `load_user_type_icons(client)` async function to icons.py — SPARQL query against urn:sempkm:user-types for sempkm:typeIcon and sempkm:typeColor predicates. Called at app startup to hydrate app.state.user_type_icons.

5. Updated `get_icon_service()` dependency in _helpers.py to inject user-type icons from app.state into each IconService instance.

6. Added `_update_icon_cache()` and `_remove_from_icon_cache()` helpers on the router for in-process icon cache management on create/delete.

7. Wired startup icon loading in main.py after ontology service setup.

8. Added 13 new tests: 4 endpoint tests (create validation, create success with HX-Trigger and icon cache, delete rejection, delete success), 4 IconService tests (user-type lookup, fallback, icon map merge, no manifest override), 3 load_user_type_icons tests (parse, empty, error handling), plus 2 additional endpoint edge cases (invalid JSON, icon cache update).

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all 28 tests pass (15 from T01 + 13 new)
- `cd backend && .venv/bin/pytest -x -q` — all 297 tests pass, no regressions
- Endpoint tests verify: 422 on empty name, 422 on malformed JSON, 200 + HX-Trigger on success, icon cache update on create, 403 on non-user-types delete, 200 + HX-Trigger + cache cleanup on delete

### Slice verification status (T02 is task 2 of 4):
- ✅ `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — 28/28 pass
- ⬜ `cd e2e && npx playwright test tests/23-class-creation/` — not yet created (T04)
- ⬜ Manual smoke test — not yet applicable (needs UI from T03)

## Diagnostics

- POST endpoint returns descriptive HTML error messages in `<div class="error-message">` on 422
- DELETE endpoint returns 403 with "Only user-created classes can be deleted" message
- Logger emits WARNING on validation errors and unauthorized delete attempts
- app.state.user_type_icons dict is inspectable at runtime for icon cache state
- load_user_type_icons() logs count of loaded icons at INFO level

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/ontology/router.py` — Added create_class and delete_class endpoints with HX-Trigger headers, icon cache helpers
- `backend/app/services/icons.py` — Added set_user_type_icons(), user-type fallback in get_type_icon()/get_icon_map(), load_user_type_icons() async loader
- `backend/app/browser/_helpers.py` — Updated get_icon_service() to inject user-type icons from app.state
- `backend/app/main.py` — Added startup user-type icon loading via load_user_type_icons()
- `backend/tests/test_class_creation.py` — Added 13 new tests for endpoints, IconService user-types, and SPARQL icon loader
