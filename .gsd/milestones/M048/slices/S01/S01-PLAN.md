# S01: Fix Table & Cards Views + Creation Timestamps

**Goal:** Table View and Cards View render objects, and newly created objects get a dcterms:created timestamp.
**Demo:** After this: Open Table View from explorer → objects listed with label, type, created, modified. Open Cards View → cards render. Create a new object → dcterms:created appears in the table.

## Tasks
- [x] **T01: Added inject_prefixes() to all 4 reconstructed SPARQL queries in execute_table_query and execute_cards_query so prefixed names are declared before triplestore execution** — ## Description

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
  - Estimate: 45m
  - Files: backend/app/views/service.py, backend/app/sparql/client.py, backend/tests/test_view_prefix_fix.py
  - Verify: cd backend && python -m pytest tests/test_view_prefix_fix.py tests/test_view_scope.py -v
- [ ] **T02: Add dcterms:created timestamp to object.create handler** — ## Description

The `handle_object_create` function in `backend/app/commands/handlers/object_create.py` creates objects with `rdf:type` and user-supplied property triples, but never adds a `dcterms:created` timestamp. This means the Table View's "created" column is always empty for objects created through the UI.

**Fix**: After building the property triples, add a `dcterms:created` triple with the current UTC datetime as an `xsd:dateTime` literal. Also add `dcterms:modified` with the same value so newly created objects show both timestamps.

## Steps

1. In `backend/app/commands/handlers/object_create.py`, import `datetime` from stdlib and `DCTERMS` from rdflib (or use a URIRef for `http://purl.org/dc/terms/created`).
2. After the property triples loop (after line ~107), add:
   ```python
   from rdflib.namespace import XSD
   now = datetime.now(timezone.utc).isoformat()
   triples.append((subject, URIRef('http://purl.org/dc/terms/created'), Literal(now, datatype=XSD.dateTime)))
   triples.append((subject, URIRef('http://purl.org/dc/terms/modified'), Literal(now, datatype=XSD.dateTime)))
   ```
3. Write a unit test in `backend/tests/test_object_create_timestamps.py` that calls `handle_object_create` and verifies:
   - The returned Operation's `data_triples` contain a triple with predicate `dcterms:created`
   - The `dcterms:created` value is a Literal with `xsd:dateTime` datatype
   - The `dcterms:modified` triple is also present
   - User-supplied properties are NOT overwritten if the user explicitly passes `dcterms:created`

## Must-Haves

- [ ] `handle_object_create` adds `dcterms:created` and `dcterms:modified` triples
- [ ] Timestamps use UTC ISO 8601 format with `xsd:dateTime` datatype
- [ ] User-supplied `dcterms:created` in properties takes precedence (no double-write)
- [ ] Unit test verifies timestamp presence and format

## Verification

- `cd backend && python -m pytest tests/test_object_create_timestamps.py -v` passes

## Inputs

- `backend/app/commands/handlers/object_create.py` — the handler to modify
- `backend/app/commands/schemas.py` — ObjectCreateParams definition

## Expected Output

- `backend/app/commands/handlers/object_create.py` — modified to inject dcterms:created and dcterms:modified
- `backend/tests/test_object_create_timestamps.py` — new test file verifying timestamps
  - Estimate: 30m
  - Files: backend/app/commands/handlers/object_create.py, backend/tests/test_object_create_timestamps.py
  - Verify: cd backend && python -m pytest tests/test_object_create_timestamps.py -v
