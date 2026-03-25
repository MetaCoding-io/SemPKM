---
estimated_steps: 7
estimated_files: 2
skills_used: []
---

# T01: Build SPARQLBuilder module with safe_iri() and safe_literal()

Create backend/app/sparql/builder.py with:

1. safe_iri(value: str) -> str: Validates the IRI, constructs rdflib.URIRef, calls .n3() to get properly escaped <iri> form. Raises ValueError on invalid IRIs. Subsumes _validate_iri() logic.
2. safe_literal(value: str, datatype: str|None = None, lang: str|None = None) -> str: Constructs rdflib.Literal, calls .n3() to get properly escaped string with datatype/language tags. Handles quotes, newlines, backslashes, tabs, carriage returns.
3. values_clause(var_name: str, iris: list[str]) -> str: Builds VALUES (?var) { (<iri1>) (<iri2>) ... } using safe_iri() for each entry.
4. triple_pattern(s: str, p: str, o: str) -> str: Builds a safe triple pattern where s/p/o can be variables (?x) or IRIs.
5. sparql_escape_string(value: str) -> str: Consolidated escape function covering \, ", ', \n, \r, \t — the authoritative replacement for all 9 scattered functions.

Unit tests in backend/tests/test_sparql_builder.py covering: valid IRIs, malicious IRI payloads (angle bracket breakout, comment injection, whitespace injection), literal escaping for all special characters, VALUES clause construction, empty/None edge cases.

## Inputs

- `backend/app/browser/_helpers.py (_validate_iri)`
- `backend/app/browser/search.py (_sparql_escape)`
- `backend/app/vfs/mount_service.py (_escape_sparql)`
- `backend/app/api/router.py (_sparql_escape_str)`

## Expected Output

- `backend/app/sparql/builder.py`
- `backend/tests/test_sparql_builder.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v
