---
estimated_steps: 38
estimated_files: 3
skills_used: []
---

# T01: Fix PREFIX-dropping bug in execute_table_query and execute_cards_query

## Description

The `execute_table_query` and `execute_cards_query` methods in `backend/app/views/service.py` extract the WHERE body and FROM clause from the original SPARQL query, then reconstruct new count/data/subjects queries. These reconstructed queries **drop all PREFIX declarations** from the original query. Since the WHERE body uses prefixed names like `rdf:type`, `rdfs:label|dcterms:title`, `dcterms:created`, and `dcterms:modified`, the RDF4J triplestore rejects the queries with SPARQL parse errors. The exceptions are silently caught (logged as warnings), resulting in zero results and the "No objects found" empty state.

**Root cause**: Lines ~592-637 (`execute_table_query`) and ~743-777 (`execute_cards_query`) construct queries like:
```
SELECT (COUNT(*) AS ?total)
FROM <urn:sempkm:current>
WHERE {
  ?s rdf:type ?type .
  OPTIONAL { ?s rdfs:label|dcterms:title ?label }
  ...
}
```
...without any PREFIX declarations. The `rdf:`, `rdfs:`, and `dcterms:` prefixes are undefined.

**Fix**: Import `inject_prefixes` from `app.sparql.client` and apply it to every reconstructed query before sending to the triplestore. This function checks which prefixes are missing and prepends them.

## Steps

1. In `backend/app/views/service.py`, add `inject_prefixes` to the import from `app.sparql.client` (line 29, change `from app.sparql.client import scope_to_current_graph` to `from app.sparql.client import scope_to_current_graph, inject_prefixes`)
2. In `execute_table_query` (~line 592), wrap the `count_query` with `inject_prefixes(count_query)` before passing to `self._client.query()`. Similarly wrap the `data_query` (~line 637).
3. In `execute_cards_query` (~line 743), wrap the `count_query` with `inject_prefixes(count_query)`. Wrap the `subjects_query` (~line 770) with `inject_prefixes(subjects_query)`.
4. Write unit tests in `backend/tests/test_view_prefix_fix.py` that verify:
   - The reconstructed count query from `execute_table_query` includes PREFIX declarations
   - The reconstructed data query includes PREFIX declarations
   - The reconstructed subjects query from `execute_cards_query` includes PREFIX declarations
   - Both methods return non-empty results when the triplestore mock returns valid SPARQL results

## Must-Haves

- [ ] `inject_prefixes` imported in `backend/app/views/service.py`
- [ ] All reconstructed queries in `execute_table_query` are wrapped with `inject_prefixes()`
- [ ] All reconstructed queries in `execute_cards_query` are wrapped with `inject_prefixes()`
- [ ] Unit tests verify prefix injection and non-empty results

## Verification

- `cd backend && python -m pytest tests/test_view_prefix_fix.py -v` passes
- `cd backend && python -m pytest tests/test_view_scope.py -v` passes (no regressions)

## Inputs

- `backend/app/views/service.py` — contains the broken execute methods
- `backend/app/sparql/client.py` — provides inject_prefixes()
- `backend/tests/test_view_scope.py` — existing test pattern to follow

## Expected Output

- `backend/app/views/service.py` — modified with inject_prefixes applied to reconstructed queries
- `backend/tests/test_view_prefix_fix.py` — new test file verifying prefix injection

## Inputs

- ``backend/app/views/service.py` — contains the broken execute_table_query and execute_cards_query methods`
- ``backend/app/sparql/client.py` — provides inject_prefixes() function`
- ``backend/tests/test_view_scope.py` — existing test pattern to follow`

## Expected Output

- ``backend/app/views/service.py` — modified with inject_prefixes applied to all reconstructed queries`
- ``backend/tests/test_view_prefix_fix.py` — new test file verifying prefix injection and non-empty results`

## Verification

cd backend && python -m pytest tests/test_view_prefix_fix.py tests/test_view_scope.py -v
