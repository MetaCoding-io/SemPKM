---
id: T01
parent: S08
milestone: M003
provides:
  - OWL class triple generation (_generate_class_triples)
  - SHACL NodeShape triple generation (_generate_shape_triples)
  - IRI minting with UUID suffix (_mint_class_iris)
  - Input validation (_validate_class_input)
  - create_class() and delete_class() async methods on OntologyService
  - Delete SPARQL builders for class + shape cleanup
  - ShapesService FROM clause includes urn:sempkm:user-types
key_files:
  - backend/app/ontology/service.py
  - backend/app/services/shapes.py
  - backend/tests/test_class_creation.py
key_decisions:
  - IRI format uses urn:sempkm:user-types:{Slug}-{uuid4hex[:8]} for classes, urn:sempkm:user-types:{Slug}Shape-{hex} for shapes
  - Shape triples use blank nodes for sh:property entries (matching existing SHACL patterns)
  - SHACL shape rdfs:label follows "{Name} Shape" convention (matching basic-pkm model)
  - Allowed datatypes are a closed set of 7 XSD types
  - Shape deletion uses OPTIONAL to cascade blank-node property cleanup
patterns_established:
  - _generate_class_triples and _generate_shape_triples are static methods returning list[tuple] of rdflib terms, reusable for testing without triplestore
  - _validate_class_input is static and raises ValueError with descriptive messages
  - create_class() returns a structured dict with class_iri, shape_iri, triple_count, property_count
observability_surfaces:
  - create_class() logs class IRI, triple count, and property count at INFO level
  - delete_class() logs class IRI and shape IRI at INFO level
  - ValueError with descriptive messages on validation failure
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Unit tests + ShapesService FROM clause fix + OWL/SHACL triple generation

**Added OWL+SHACL triple generation, ShapesService FROM clause for user-types, IRI minting, validation, and delete logic — all verified by 15 unit tests including a round-trip SHACL→rdflib→ShapesService parse.**

## What Happened

1. Created `backend/tests/test_class_creation.py` with 15 tests covering all generation and validation logic
2. Fixed `ShapesService._fetch_shapes_graph()` to include `FROM <urn:sempkm:user-types>` in its CONSTRUCT query
3. Added to OntologyService: `_mint_class_iris()`, `_validate_class_input()`, `_generate_class_triples()`, `_generate_shape_triples()`, `_build_delete_class_sparql()`, `_build_delete_shape_sparql()`, `create_class()`, `delete_class()`
4. Added constants: `SEMPKM_TYPE_ICON`, `SEMPKM_TYPE_COLOR`, `ALLOWED_DATATYPES`

The critical round-trip test proves that generated SHACL triples load into an rdflib Graph and `ShapesService._extract_node_shape()` parses them into a valid `NodeShapeForm` with correct target_class, label, and property list with paths/names/datatypes/ordering.

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all 15 tests pass
- `cd backend && .venv/bin/pytest` — all 284 tests pass (no regressions)
- Round-trip test (the critical one): generates 3 properties, loads into rdflib, `_extract_node_shape()` returns NodeShapeForm with correct target_class, label ("Research Note Shape"), 3 properties with correct paths/names/datatypes, and sorted ordering

### Slice verification status (T01 is task 1 of 4):
- ✅ `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — 15/15 pass
- ⬜ `cd e2e && npx playwright test tests/23-class-creation/` — not yet created (T04)
- ⬜ Manual smoke test — not yet applicable (needs UI from T03)

## Diagnostics

- Run unit tests directly: `cd backend && .venv/bin/pytest tests/test_class_creation.py -v`
- Inspect generated triples: call `OntologyService._generate_class_triples()` and `_generate_shape_triples()` directly (static methods, no triplestore needed)
- Inspect SPARQL: call `_build_delete_class_sparql()` / `_build_delete_shape_sparql()` to see DELETE queries
- Validation errors: `_validate_class_input()` raises ValueError with descriptive messages

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_class_creation.py` — 15 unit tests covering FROM clause, OWL triples, SHACL triples, round-trip, IRI minting, validation, icon triples, delete SPARQL
- `backend/app/ontology/service.py` — Added create_class/delete_class methods, triple generation, IRI minting, validation, delete SPARQL builders, ALLOWED_DATATYPES and icon predicate constants
- `backend/app/services/shapes.py` — Added `FROM <urn:sempkm:user-types>` to _fetch_shapes_graph() CONSTRUCT query
