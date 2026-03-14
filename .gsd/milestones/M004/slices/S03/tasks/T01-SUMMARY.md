---
id: T01
parent: S03
milestone: M004
provides:
  - list_user_types() service method for querying all user-created classes and properties
  - get_property_for_edit() service method with cross-graph label resolution
  - edit_property() service method with delete-then-reinsert pattern
  - _resolve_cross_graph_label() reusable helper for cross-graph label lookups
key_files:
  - backend/app/ontology/service.py
  - backend/tests/test_ontology_service.py
key_decisions:
  - Extracted _resolve_cross_graph_label() as reusable helper instead of inlining UNION label queries in each method
  - list_user_types() uses a single SPARQL query with FILTER on rdf:type to fetch all three categories at once
patterns_established:
  - Cross-graph label resolution via _resolve_cross_graph_label() UNION pattern (skos:prefLabel + rdfs:label)
observability_surfaces:
  - logger.info("list_user_types: %d classes, %d properties", ...) for query counts
  - logger.info("Edited property %s (%d triples)", ...) for edit events
  - ValueError raised with descriptive messages on invalid inputs
  - None return on property not found in get_property_for_edit()
duration: 1 step
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Add list_user_types(), get_property_for_edit(), edit_property() service methods + unit tests

**Added three OntologyService methods — list_user_types(), get_property_for_edit(), edit_property() — with cross-graph label resolution and 12 unit tests.**

## What Happened

Added three new async methods to `OntologyService`:

1. **`list_user_types()`** — Single SPARQL query against `FROM <urn:sempkm:user-types>` with FILTER on rdf:type (owl:Class, owl:ObjectProperty, owl:DatatypeProperty). Returns structured dict with `classes`, `object_properties`, `datatype_properties` lists. Each entry includes labels and optional metadata (icon/color for classes, domain/range labels for properties resolved within the user-types graph).

2. **`get_property_for_edit(property_iri)`** — Queries property metadata from user-types graph, determines prop_type from rdf:type (ObjectProperty vs DatatypeProperty), then resolves domain/range labels via `_resolve_cross_graph_label()` which uses the same UNION pattern (skos:prefLabel + rdfs:label) as get_class_for_edit's parent label resolution. Returns None if property not found.

3. **`edit_property(property_iri, name, prop_type, ...)`** — Validates inputs (non-empty name, valid prop_type, valid IRIs), deletes all triples for the property IRI in user-types graph, re-inserts via `_generate_property_triples()`. Property IRI is preserved. Returns `{property_iri, prop_type, triple_count}`.

Extracted `_resolve_cross_graph_label(iri)` as a reusable private method to avoid duplicating the cross-graph UNION label lookup pattern.

Added 12 unit tests across 3 new test classes covering query structure, empty results, categorization, not-found, happy paths, validation errors, delete-then-insert sequencing, IRI preservation, and triple counts.

## Verification

- `docker exec sempkm-api-1 pytest tests/test_ontology_service.py -x -q` — **56 passed** (44 existing + 12 new)
- `docker exec sempkm-api-1 pytest tests/test_ontology_service.py -x -q -k "TestListUserTypes or TestGetPropertyForEdit or TestEditProperty"` — **12 passed**

## Diagnostics

- Grep logs for `list_user_types:` to see class/property counts
- Grep logs for `Edited property` to see edit events
- `ValueError` with descriptive messages on invalid inputs (empty name, bad prop_type, invalid IRIs)
- `get_property_for_edit()` returns `None` for non-existent properties

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/ontology/service.py` — Added `list_user_types()`, `get_property_for_edit()`, `edit_property()`, `_resolve_cross_graph_label()` methods
- `backend/tests/test_ontology_service.py` — Added `TestListUserTypes` (4 tests), `TestGetPropertyForEdit` (3 tests), `TestEditProperty` (5 tests)
