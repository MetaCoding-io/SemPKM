---
estimated_steps: 4
estimated_files: 1
skills_used:
  - test
---

# T04: Quadrant backend unit tests

**Slice:** S01 — Eisenhower Matrix — Model Archive + Quadrant Renderer
**Milestone:** M036

## Description

Write unit tests for the quadrant axis detection and query builder logic. These verify the SHACL-driven detection of two sh:in axis properties and the SPARQL query grouping independently of a running triplestore, ensuring the data pipeline is correct.

Follow the codebase test patterns — tests run from `backend/` directory using `.venv/bin/python -m pytest`. Mock the triplestore client for SPARQL responses.

**Important:** Per KNOWLEDGE.md, `pytest tests/test_quadrant.py` must be run from the `backend/` directory, not the project root (the root `.env` causes Pydantic Settings import failures).

## Steps

1. **Create `backend/tests/test_quadrant.py`** with test class structure:
   - Import ViewSpecService (or the relevant methods directly)
   - Import SHACL-related namespaces from rdflib (SH, RDF, RDFS, XSD)
   - Create helper fixtures for mock SHACL graphs

2. **Test `_detect_quadrant_axes()` — happy path**:
   - Build a minimal rdflib Graph with two SHACL PropertyShapes:
     - One with `sh:path bp:urgency` and `sh:in ("high", "low")`
     - One with `sh:path bp:importance` and `sh:in ("high", "low")`
   - Mock the triplestore client to return SPARQL results that describe these shapes
   - Call `_detect_quadrant_axes(type_iri)` and assert it returns two PropertyShape-like objects with correct paths
   - Verify the x-axis is the property containing "urgency" and y-axis contains "importance"

3. **Test `_detect_quadrant_axes()` — no quadrant properties**:
   - Build a SHACL graph with properties that have `sh:in` but not exactly 2 values (e.g., status with 4 values)
   - Call `_detect_quadrant_axes(type_iri)` and assert it returns `(None, None)`

4. **Test quadrant result grouping**:
   - Create mock SPARQL bindings with items having various (xValue, yValue) combinations
   - Call the grouping logic (either through `execute_quadrant_query` with mocked client, or test the grouping function directly)
   - Assert items are distributed into 4 quadrant buckets correctly
   - Assert items with missing axis values go into an "unset" bucket
   - Assert total count is correct

## Must-Haves

- [ ] Test axis detection with valid quadrant-compatible SHACL shapes
- [ ] Test axis detection returns None when no compatible shapes exist
- [ ] Test result grouping distributes items into 4 quadrant buckets
- [ ] Test items with missing axis values handled gracefully (unset bucket)
- [ ] All tests pass with `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all tests pass, 0 failures
- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v --tb=short 2>&1 | tail -5` — confirms pass count

## Inputs

- `backend/app/views/service.py` — `_detect_quadrant_axes()` and `execute_quadrant_query()` methods from T02
- `backend/app/views/router.py` — quadrant branches from T02
- `models/business-planning/shapes/business-planning.jsonld` — SHACL shapes with sh:in from T01

## Expected Output

- `backend/tests/test_quadrant.py` — unit tests for quadrant axis detection and result grouping
