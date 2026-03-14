---
estimated_steps: 5
estimated_files: 3
---

# T01: Add delete_property() service + get_delete_class_info() + unit tests

**Slice:** S02 — Delete + Instance Warnings
**Milestone:** M004

## Description

Add the service-layer methods that S02's routes and UI depend on: `delete_property()` for removing user-created OWL properties, `get_delete_class_info()` for pre-delete instance/subclass counts, and fix `_property_source()` to return `'user'` for user-types IRIs. All methods get unit tests following existing patterns in `test_class_creation.py`.

## Steps

1. Fix `_property_source()` in `service.py` — add a check for `urn:sempkm:user-types:` IRIs to return `'user'` instead of falling through to the generic `sempkm` case. Must come before the existing `SEMPKM_NS` check since user-types IRIs also start with `urn:sempkm:`. Add a unit test verifying `_property_source` returns `'user'` for user-types IRIs and still returns `'sempkm'` for other sempkm-namespace IRIs.

2. Add `delete_property()` to `OntologyService` — a simple async method that takes `property_iri: str` and runs `DELETE WHERE { GRAPH <user-types> { <prop_iri> ?p ?o . } }`. Returns `{"property_iri": prop_iri, "status": "deleted"}`. Log with `logger.info`. Add a unit test `test_delete_property_sparql` in a new `TestDeleteProperty` class verifying the generated SPARQL contains the correct IRI and graph.

3. Add `get_delete_class_info()` to `OntologyService` — async method that takes `class_iri: str` and runs two parallel SPARQL queries (same patterns as `get_class_detail()`): one for `SELECT COUNT(?sub)` subclasses across ontology graphs, one for `SELECT COUNT(?inst)` instances in the default graph. Also retrieves the class label via a simple SPARQL query (or COALESCE rdfs:label/skos:prefLabel/localname). Returns `{"class_iri": str, "label": str, "instance_count": int, "subclass_count": int}`. Add unit tests in a new `TestGetDeleteClassInfo` class.

4. Write unit tests for `delete_property()` SPARQL generation — verify it targets the correct IRI in the user-types graph.

5. Write unit tests for `get_delete_class_info()` — mock `_client.query` to return canned results, verify the method parses instance and subclass counts correctly.

## Must-Haves

- [ ] `_property_source("urn:sempkm:user-types:MyProp-abc123")` returns `'user'`
- [ ] `_property_source("urn:sempkm:ns/someProp")` still returns `'sempkm'`
- [ ] `delete_property()` generates correct `DELETE WHERE` targeting user-types graph
- [ ] `get_delete_class_info()` returns dict with `instance_count`, `subclass_count`, `label`
- [ ] All new unit tests pass: `pytest tests/test_class_creation.py -v`

## Verification

- `cd backend && python -m pytest tests/test_class_creation.py -v -k "delete_property or delete_class_info or property_source"` — all pass
- `cd backend && python -m pytest tests/test_class_creation.py -v` — all existing tests still pass (no regressions)

## Observability Impact

- Signals added/changed: `logger.info("Deleted property %s", prop_iri)` in `delete_property()`
- How a future agent inspects this: call `delete_property()` or `get_delete_class_info()` directly; SPARQL queries are logged at debug level
- Failure state exposed: ValueError on invalid input, logged exceptions on SPARQL failures

## Inputs

- `backend/app/ontology/service.py` — existing `delete_class()`, `_build_delete_class_sparql()`, `_property_source()`, and `get_class_detail()` instance/subclass count patterns
- `backend/tests/test_class_creation.py` — existing `TestDeleteClass` test class pattern, `_make_ontology_service()` helper

## Expected Output

- `backend/app/ontology/service.py` — `_property_source()` fixed, `delete_property()` added, `get_delete_class_info()` added
- `backend/tests/test_class_creation.py` — `TestDeleteProperty`, `TestGetDeleteClassInfo`, `TestPropertySource` test classes added
