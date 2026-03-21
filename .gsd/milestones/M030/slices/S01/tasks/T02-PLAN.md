---
estimated_steps: 6
estimated_files: 3
---

# T02: Write unit tests for pipeline fix and measure performance

**Slice:** S01 — Validation Pipeline Fix & Performance Measurement
**Milestone:** M030

## Description

Write unit tests proving the pipeline fix works and measure pyshacl performance with `advanced=True` to retire the roadmap risk. The test file exercises both the loader (shapes + rules merge) and the validation service (advanced flag), plus includes a functional test that proves SPARQLConstraint rules actually fire.

## Steps

1. Create `backend/tests/test_validation_pipeline.py`. Import the necessary modules:
   ```python
   from unittest.mock import AsyncMock, patch, MagicMock
   from rdflib import Graph, Namespace, Literal, URIRef
   from rdflib.namespace import RDF, XSD
   import pytest
   import time
   from app.services.models import model_shapes_loader
   from app.services.validation import ValidationService
   ```

2. Write test: **model_shapes_loader returns merged shapes+rules graph**. Mock `TriplestoreClient` with:
   - `.query()` returning a binding list with one model ID (e.g., `basic-pkm`)
   - `.construct()` returning canned Turtle for shapes (first call) and rules (second call)
   - Assert the returned graph contains triples from BOTH shapes and rules Turtle

3. Write test: **model_shapes_loader with no models returns empty graph**. Mock `.query()` returning empty bindings. Assert returned graph has length 0.

4. Write test: **model_shapes_loader with empty rules returns shapes only**. Mock `.construct()` returning valid shapes Turtle for first call, empty string for second call (rules). Assert returned graph contains shapes triples and has no error.

5. Write test: **ValidationService.validate passes advanced=True to pyshacl**. Patch `pyshacl.validate` with a MagicMock that returns `(True, Graph(), "")`. Create ValidationService with a mock shapes_loader returning a non-empty graph. Call `validate()`. Assert `pyshacl.validate` was called with `advanced=True` in its kwargs. Also assert `allow_infos=True` and `allow_warnings=True` are still present.

6. Write test: **SPARQLConstraint rules fire for overdue task (functional)**. This is the key proof that the fix works end-to-end with real pyshacl:
   - Load the real `models/basic-pkm/shapes/basic-pkm.ttl` and `models/basic-pkm/rules/basic-pkm.ttl` files into a combined rdflib Graph
   - Build a small data graph with one Task that has `bpkm:dueDate` set to yesterday and `bpkm:taskStatus "todo"` and `rdf:type bpkm:Task`
   - Call `pyshacl.validate(data_graph, shacl_graph=combined, advanced=True, allow_warnings=True)`
   - Assert `conforms` is False (warnings count as non-conforming when severity is Warning)
   - Parse the results graph for `sh:resultSeverity sh:Warning` and `sh:resultMessage` containing "overdue"
   - **Measure and log the execution time** using `time.perf_counter()` before/after the validate call. Print it: `print(f"pyshacl advanced=True execution time: {elapsed:.3f}s")`
   - Assert execution completes in <10 seconds (generous bound; expect <1s for small data)

   Note: The real shapes file is at `models/basic-pkm/shapes/basic-pkm.ttl` and rules at `models/basic-pkm/rules/basic-pkm.ttl`. Load both with `graph.parse(path, format="turtle")`. The shapes file defines `bpkm:Task` NodeShape and the rules file defines `bpkm:OverdueTaskValidationShape` with the SPARQLConstraint.

   Key namespace: `bpkm = Namespace("urn:sempkm:model:basic-pkm:")`. The Task needs:
   - `rdf:type bpkm:Task`
   - `bpkm:dueDate` as `Literal("2020-01-01", datatype=XSD.date)`
   - `bpkm:taskStatus` as `Literal("todo")`
   - `dcterms:title` as `Literal("Test overdue task")`

## Must-Haves

- [ ] Test proves loader merges shapes + rules graphs
- [ ] Test proves loader handles empty rules gracefully
- [ ] Test proves loader handles no-models case
- [ ] Test proves `advanced=True` is passed to pyshacl.validate
- [ ] Functional test proves SPARQLConstraint fires for overdue task
- [ ] Performance timing logged for pyshacl with advanced=True

## Verification

- `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` — all tests pass
- Test output includes performance timing line

## Inputs

- `backend/app/services/models.py` — updated `model_shapes_loader()` from T01
- `backend/app/services/validation.py` — updated `ValidationService.validate()` from T01
- `models/basic-pkm/shapes/basic-pkm.ttl` — real SHACL shapes for functional test
- `models/basic-pkm/rules/basic-pkm.ttl` — real SHACL-AF rules with SPARQLConstraint for functional test

## Expected Output

- `backend/tests/test_validation_pipeline.py` — new test file with 5+ tests covering loader, service, and functional validation
