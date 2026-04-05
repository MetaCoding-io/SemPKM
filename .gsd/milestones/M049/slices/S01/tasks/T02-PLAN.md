---
estimated_steps: 30
estimated_files: 2
skills_used: []
---

# T02: Combine multi-graph property queries and consolidate label batches in get_object

## Description

The `get_object` handler in `backend/app/browser/objects.py` makes 3 separate SPARQL queries to fetch properties from current, inferred, and mirrored graphs — each is a sequential HTTP round-trip to RDF4J. It also makes up to 5 separate `label_service.resolve_batch()` calls sequentially.

Combine the 3 property queries into 1 UNION query (similar to how `get_relations` already uses UNION). Consolidate the 5 label batches into 1 combined batch after all IRIs are known.

## Steps

1. Read `backend/app/browser/objects.py` lines 100-310 (the `get_object` handler) to understand the current query sequence.

2. Replace the 3 separate property queries (props_sparql, inferred_props_sparql, mirrored_props_sparql) with a single UNION query that annotates each result with its source graph:
   ```sparql
   SELECT ?p ?o ?source WHERE {
     { GRAPH <urn:sempkm:current> { <IRI> ?p ?o } BIND("user" AS ?source) }
     UNION
     { GRAPH <urn:sempkm:inferred> { <IRI> ?p ?o } BIND("inferred" AS ?source) }
     UNION
     { GRAPH <urn:sempkm:mirrored> { <IRI> ?p ?o } BIND("mirrored" AS ?source) }
   }
   ```

3. Adjust the binding-processing logic to partition results by `?source` into `values`, `inferred_values`, and `mirrored_values` dicts (same structure as before). Preserve the existing deduplication logic (user > inferred > mirrored).

4. After all property processing and form resolution is done, collect ALL IRIs that need labels into a single set: ref_iris + type_class_iris + object/type iris + inferred iris + mirrored iris. Make ONE call to `label_service.resolve_batch(all_iris)`. Then extract sub-results from the single response dict.

5. Write a focused test in `backend/tests/test_object_query_opt.py` that mocks `TriplestoreClient.query` and `LabelService.resolve_batch`, calls a simplified version of the query logic, and asserts:
   - Only 1 SPARQL query is made for properties (not 3)
   - Only 1 label batch call is made (not 5)
   - Output structure (values, inferred_values, mirrored_values) is identical to the old behavior

## Must-Haves

- [ ] Single UNION query replaces 3 separate graph queries
- [ ] Single label batch replaces 5 separate batches
- [ ] Deduplication logic preserved: user values take precedence over inferred/mirrored
- [ ] Template context structure unchanged — no template modifications needed
- [ ] Test verifies query count reduction and output equivalence

## Verification

- `cd backend && python -m pytest tests/test_object_query_opt.py -v`
- `cd backend && python -m pytest tests/ -x --timeout=30` (no regressions)

## Inputs

- ``backend/app/browser/objects.py` — current get_object handler with sequential queries`
- ``backend/app/services/labels.py` — LabelService.resolve_batch interface`

## Expected Output

- ``backend/app/browser/objects.py` — get_object with UNION query and consolidated label batch`
- ``backend/tests/test_object_query_opt.py` — tests verifying query count reduction and output equivalence`

## Verification

cd backend && python -m pytest tests/test_object_query_opt.py -v && python -m pytest tests/ -x --timeout=60
