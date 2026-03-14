---
estimated_steps: 5
estimated_files: 2
---

# T01: Add list_user_types(), get_property_for_edit(), edit_property() service methods + unit tests

**Slice:** S03 — Custom Section on Mental Models + Property Edit
**Milestone:** M004

## Description

Add three new service methods to `OntologyService`: `list_user_types()` to query all user-created classes and properties from `urn:sempkm:user-types`, `get_property_for_edit()` to fetch property metadata for the edit form (following the `get_class_for_edit()` pattern), and `edit_property()` to update a property via delete-then-reinsert (following the `edit_class()` pattern). All methods include input validation, namespace guarding, and logging. Unit tests cover happy paths, edge cases, and validation errors.

## Steps

1. **Add `list_user_types()`** — Single SPARQL query against `FROM <urn:sempkm:user-types>` that returns `{"classes": [...], "object_properties": [...], "datatype_properties": [...]}`. Each class has `iri`, `label`, `icon`, `color`, `parent_label`. Each property has `iri`, `label`, `type` (object/datatype), `domain_label`, `range_label`. Log class and property counts at info level.

2. **Add `get_property_for_edit()`** — Query property metadata from user-types graph: `iri`, `label`, `prop_type` (object/datatype based on `rdf:type`), `domain_iri`, `domain_label`, `range_iri`, `range_label`, `description`. Use cross-graph label resolution for domain/range (same UNION pattern as `get_class_for_edit()` parent label resolution). Return `None` if property not found.

3. **Add `edit_property()`** — Validate inputs (non-empty name, valid prop_type, valid IRIs). Delete all triples for the property IRI in user-types graph (`DELETE WHERE { GRAPH <user-types> { <prop_iri> ?p ?o . } }`). Re-insert using `_generate_property_triples()`. Property IRI is preserved, property type is preserved (passed through but not changed). Log edit at info level. Return `{"property_iri", "prop_type", "triple_count"}`.

4. **Add unit tests for `list_user_types()`** — Test the SPARQL query structure includes correct FROM clause, returns empty dicts when no results, correctly categorizes object vs datatype properties.

5. **Add unit tests for `get_property_for_edit()` and `edit_property()`** — Test not-found returns None, happy path returns correct dict shape, edit calls delete then insert, edit preserves IRI, validation rejects empty name and invalid prop_type.

## Must-Haves

- [ ] `list_user_types()` returns structured dict with classes, object_properties, datatype_properties
- [ ] `get_property_for_edit()` returns property metadata dict or None if not found
- [ ] `edit_property()` uses delete-then-reinsert pattern, preserves IRI, validates inputs
- [ ] Cross-graph label resolution for domain/range in `get_property_for_edit()`
- [ ] Unit tests cover all three methods (≥8 new tests)

## Verification

- `docker exec sempkm-backend pytest tests/test_ontology_service.py -x -q` — all tests pass including new ones
- `docker exec sempkm-backend pytest tests/test_ontology_service.py -x -q -k "list_user_types or get_property_for_edit or edit_property"` — new tests specifically pass

## Observability Impact

- Signals added/changed: `logger.info` in `list_user_types()` and `edit_property()` for query counts and edit events
- How a future agent inspects this: grep logs for "list_user_types" or "Edited property" messages
- Failure state exposed: `ValueError` raised on invalid inputs with descriptive messages; `None` return on not-found

## Inputs

- `backend/app/ontology/service.py` — existing `get_class_for_edit()` (line ~1757) as pattern for `get_property_for_edit()`; existing `edit_class()` (line ~1856) as pattern for `edit_property()`; existing `_generate_property_triples()` (line ~1558) for triple generation; existing `delete_property()` (line ~1661) for the DELETE SPARQL pattern
- `backend/tests/test_ontology_service.py` — existing test classes (e.g. `TestEditClass`, `TestGetClassForEdit`) as patterns for new tests

## Expected Output

- `backend/app/ontology/service.py` — three new async methods added to `OntologyService` class
- `backend/tests/test_ontology_service.py` — ≥8 new unit tests across 3 new test classes
