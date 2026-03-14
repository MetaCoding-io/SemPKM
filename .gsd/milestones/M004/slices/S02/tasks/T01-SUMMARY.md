---
id: T01
parent: S02
milestone: M004
provides:
  - delete_property() service method for removing user-created OWL properties
  - get_delete_class_info() service method returning pre-delete instance/subclass counts
  - _property_source() fix returning 'user' for user-types IRIs
key_files:
  - backend/app/ontology/service.py
  - backend/tests/test_class_creation.py
key_decisions: []
patterns_established:
  - delete_property uses same DELETE WHERE pattern as _build_delete_class_sparql
  - get_delete_class_info uses same parallel asyncio.gather pattern as get_class_detail
observability_surfaces:
  - logger.info("Deleted property %s", prop_iri) in delete_property()
  - SPARQL queries logged at debug level via existing client
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Add delete_property() service + get_delete_class_info() + unit tests

**Added service-layer methods for property deletion and pre-delete class inspection, plus fixed _property_source() for user-types IRIs.**

## What Happened

Three changes to `service.py`:

1. **Fixed `_property_source()`** — added a check for `urn:sempkm:user-types:` prefix before the generic `SEMPKM_NS` check, so user-created classes and properties get source label `'user'` instead of `'sempkm'`.

2. **Added `delete_property()`** — simple async method that runs `DELETE WHERE { GRAPH <user-types> { <prop_iri> ?p ?o . } }`, returns `{"property_iri": ..., "status": "deleted"}`, and logs at info level.

3. **Added `get_delete_class_info()`** — async method that runs three parallel SPARQL queries (label, subclass count across ontology graphs, instance count in default graph) using `asyncio.gather`, matching the same parallel-query pattern used in `get_class_detail()`. Returns `{"class_iri", "label", "instance_count", "subclass_count"}`.

Added 11 unit tests across 3 new test classes: `TestPropertySource` (6 tests), `TestDeleteProperty` (2 tests), `TestGetDeleteClassInfo` (3 tests).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_class_creation.py -v -k "PropertySource"` — 6/6 passed
- `cd backend && .venv/bin/python -m pytest tests/test_class_creation.py -v -k "delete_property or delete_class_info"` — 5/5 passed
- `cd backend && .venv/bin/python -m pytest tests/test_class_creation.py -v` — 42/45 passed (3 pre-existing failures in TestCreateClassEndpoint due to Form() parameter mismatch in router tests — unrelated to this task)
- `cd backend && .venv/bin/python -m pytest tests/test_ontology_service.py -v` — 44/44 passed (no regressions)

### Slice-level verification status (intermediate task):
- ✅ `pytest tests/test_class_creation.py -v` — new delete tests pass
- ✅ `pytest tests/test_ontology_service.py -v` — existing tests unbroken
- ⏳ Browser class delete flow — requires T02 (routes) and T03 (UI)
- ⏳ Browser property delete flow — requires T02 (routes) and T03 (UI)

## Diagnostics

- `delete_property()` logs `INFO "Deleted property %s"` on success
- SPARQL queries logged at DEBUG level by the triplestore client
- Call `delete_property()` or `get_delete_class_info()` directly to inspect behavior
- ValueError on invalid input, logged exceptions on SPARQL failures

## Deviations

None.

## Known Issues

- 3 pre-existing test failures in `TestCreateClassEndpoint` (test_create_class_missing_name_returns_422, test_create_class_success_returns_hx_trigger, test_create_class_updates_icon_cache) — these fail due to a `Form()` parameter mismatch in the router, not related to this task's changes.

## Files Created/Modified

- `backend/app/ontology/service.py` — fixed `_property_source()`, added `delete_property()`, added `get_delete_class_info()`
- `backend/tests/test_class_creation.py` — added `TestPropertySource`, `TestDeleteProperty`, `TestGetDeleteClassInfo` test classes (11 tests)
