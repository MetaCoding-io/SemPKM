---
estimated_steps: 30
estimated_files: 2
skills_used: []
---

# T02: Add dcterms:created timestamp to object.create handler

## Description

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

## Inputs

- ``backend/app/commands/handlers/object_create.py` — the handler to modify`
- ``backend/app/commands/schemas.py` — ObjectCreateParams definition for test setup`

## Expected Output

- ``backend/app/commands/handlers/object_create.py` — modified to inject dcterms:created and dcterms:modified triples`
- ``backend/tests/test_object_create_timestamps.py` — new test file verifying timestamp presence and format`

## Verification

cd backend && python -m pytest tests/test_object_create_timestamps.py -v
