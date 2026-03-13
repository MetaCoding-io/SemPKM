---
estimated_steps: 5
estimated_files: 3
---

# T01: Unit tests + ShapesService FROM clause fix + OWL/SHACL triple generation

**Slice:** S08 — In-App Class Creation
**Milestone:** M003

## Description

Write failing tests first, then implement the core logic: fix ShapesService to include `urn:sempkm:user-types` in its FROM clauses, and add `create_class()` / `delete_class()` methods to OntologyService that generate valid OWL class triples + SHACL NodeShape triples. This is the foundation everything else in S08 depends on.

The critical validation is a round-trip test: generate SHACL triples → load into rdflib Graph → verify `ShapesService._extract_node_shape()` can parse them into a valid `NodeShapeForm` with correct properties.

## Steps

1. **Create `backend/tests/test_class_creation.py`** with test cases:
   - `test_shapes_from_clauses_include_user_types` — verify `_fetch_shapes_graph()` CONSTRUCT query includes `FROM <urn:sempkm:user-types>`
   - `test_generate_owl_class_triples` — verify output contains `owl:Class` type, `rdfs:label`, `rdfs:subClassOf`
   - `test_generate_shacl_shape_triples` — verify output contains `sh:NodeShape`, `sh:targetClass`, `sh:property` blocks with `sh:path`, `sh:name`, `sh:datatype`, `sh:order`
   - `test_shacl_round_trip_through_shapes_service` — generate triples, load into rdflib Graph, call `_extract_node_shape()`, verify resulting `NodeShapeForm` has correct `target_class`, `label`, and `properties` list with correct paths/names/datatypes
   - `test_iri_minting_uses_uuid` — verify class IRI contains UUID segment under `urn:sempkm:user-types:`
   - `test_validate_empty_name_rejected` — empty/whitespace name raises ValueError
   - `test_validate_invalid_parent_iri_rejected` — non-IRI parent raises ValueError
   - `test_generate_icon_triples` — verify `sempkm:typeIcon` and `sempkm:typeColor` triples when icon provided
   - `test_delete_class_sparql` — verify DELETE WHERE targets correct subject in `urn:sempkm:user-types`
   - `test_delete_class_shape_sparql` — verify DELETE WHERE also removes shape triples

2. **Fix `ShapesService._fetch_shapes_graph()`** — add `FROM <urn:sempkm:user-types>` to the CONSTRUCT query's FROM clauses (alongside model shapes graphs). This is a single line addition.

3. **Add `create_class()` to OntologyService** — accepts class name, icon name, icon color, parent class IRI, and a list of property definitions (name, predicate IRI, datatype IRI). Generates:
   - OWL class triples: `<classIRI> a owl:Class`, `rdfs:label`, `rdfs:subClassOf <parent>`, `sempkm:typeIcon`, `sempkm:typeColor`
   - SHACL NodeShape: `<shapeIRI> a sh:NodeShape`, `sh:targetClass <classIRI>`, `rdfs:label "{name} Shape"`, and for each property: blank-node `sh:property` with `sh:path`, `sh:name`, `sh:datatype`, `sh:order`
   - Writes to `urn:sempkm:user-types` via `_build_insert_data_sparql()` (reusing existing helper)
   - IRI minted as `urn:sempkm:user-types:{Slug}-{uuid4hex[:8]}` (e.g. `urn:sempkm:user-types:MyTask-a1b2c3d4`)

4. **Add `delete_class()` to OntologyService** — accepts class IRI. Executes `DELETE WHERE { GRAPH <urn:sempkm:user-types> { <classIRI> ?p ?o } }` plus `DELETE WHERE { GRAPH <urn:sempkm:user-types> { <shapeIRI> ?p ?o . ?prop ?pp ?oo . } }` to clean up both class and shape triples.

5. **Add input validation** — `_validate_class_input()` helper that checks: name is non-empty after strip, parent IRI starts with `http` or `urn:`, property names non-empty, property predicate IRIs are valid, datatypes from a known allowlist (xsd:string, xsd:integer, xsd:decimal, xsd:boolean, xsd:date, xsd:dateTime, xsd:anyURI).

## Must-Haves

- [ ] ShapesService FROM clause includes `urn:sempkm:user-types`
- [ ] OWL class triples generated with owl:Class, rdfs:label, rdfs:subClassOf
- [ ] SHACL NodeShape triples generated with sh:targetClass, sh:property blocks including sh:path, sh:name, sh:datatype, sh:order
- [ ] Round-trip test proves ShapesService can parse generated shapes into NodeShapeForm
- [ ] IRI minting uses UUID suffix for collision prevention
- [ ] Input validation rejects empty names and invalid IRIs
- [ ] Delete generates correct SPARQL to remove class + shape triples from user-types graph

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all 10+ tests pass
- Round-trip test is the critical one: generated SHACL → rdflib → `_extract_node_shape()` → valid `NodeShapeForm`

## Observability Impact

- Signals added/changed: `create_class()` and `delete_class()` methods log class IRI, triple count, and property count at INFO level
- How a future agent inspects this: run the unit tests; inspect generated SPARQL by calling helpers directly
- Failure state exposed: ValueError with descriptive message on validation failure; logged traceback on triplestore errors

## Inputs

- `backend/app/ontology/service.py` — existing `_build_insert_data_sparql()`, `_rdf_term_to_sparql()`, `USER_TYPES_GRAPH` constant
- `backend/app/services/shapes.py` — existing `_fetch_shapes_graph()` method, `_extract_node_shape()` for round-trip validation
- `models/basic-pkm/shapes/basic-pkm.jsonld` — reference SHACL shape structure that ShapesService expects

## Expected Output

- `backend/tests/test_class_creation.py` — 10+ passing unit tests covering all generation and validation logic
- `backend/app/ontology/service.py` — `create_class()`, `delete_class()`, `_validate_class_input()`, `_generate_class_triples()`, `_generate_shape_triples()` methods added
- `backend/app/services/shapes.py` — `_fetch_shapes_graph()` includes `FROM <urn:sempkm:user-types>` in CONSTRUCT query
