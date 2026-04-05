---
estimated_steps: 22
estimated_files: 2
skills_used: []
---

# T01: Add inbound edge cleanup to bulk_delete_objects()

## Why

The existing `bulk_delete_objects()` endpoint only queries and deletes triples where the deleted IRI is the **subject** (`<iri> ?p ?o`). It does NOT delete triples where the IRI is the **object** (`?s ?p <iri>`), leaving dangling references. Decision D384 requires fixing this.

## Steps

1. Open `backend/app/browser/objects.py`, find the `bulk_delete_objects()` function (starts at line 1014).

2. Inside the `for iri in iris:` loop, after the existing outbound SPARQL query and binding processing (which collects triples matching `<iri> ?p ?o`), add a second SPARQL query for inbound edges:
   ```sparql
   SELECT ?s ?p WHERE {
     GRAPH <urn:sempkm:current> {
       ?s ?p <{iri}> .
     }
   }
   ```

3. Process the inbound bindings: for each result, create `(URIRef(s_value), URIRef(p_value), URIRef(iri))` and append to `materialize_deletes`. The subject (`?s`) will always be a URI since blank nodes don't typically reference other resources by IRI.

4. Wrap in the same try/except pattern as the outbound query (log warning on failure, continue).

5. Create `backend/tests/test_object_delete_inbound.py` with tests:
   - Test that inbound edge triples are included in `materialize_deletes` when present
   - Test that outbound triples are still included (no regression)
   - Test that when no inbound edges exist, delete still works
   - Mock the triplestore client's `query()` to return controlled bindings

6. Run: `cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v`

## Key constraint
The inbound triples must be appended to the SAME `materialize_deletes` list as the outbound triples, so they're part of the same `Operation` and same event audit trail.

## Inputs

- ``backend/app/browser/objects.py` — existing bulk_delete_objects() function starting at line 1014`

## Expected Output

- ``backend/app/browser/objects.py` — modified with inbound edge SPARQL query in bulk_delete_objects()`
- ``backend/tests/test_object_delete_inbound.py` — new test file verifying inbound edge cleanup`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_object_delete_inbound.py -v
