---
id: T01
parent: S01
milestone: M043
key_files:
  - backend/app/sparql/builder.py
  - backend/tests/test_sparql_builder.py
key_decisions:
  - Used rdflib URIRef.n3() as the serialization layer for IRI safety — catches malformed IRIs that manual regex might miss
  - Added defence-in-depth pre-validation with forbidden character regex before rdflib — provides clear error messages for SPARQL-specific injection characters
  - sparql_escape_string covers \, ", ', \n, \r, \t — superset of all 9 scattered functions, ensuring no escape gaps when modules are migrated
duration: ""
verification_result: passed
completed_at: 2026-03-25T07:47:11.439Z
blocker_discovered: false
---

# T01: SPARQLBuilder module with safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), and triple_pattern() — plus 66 unit tests covering injection payloads, edge cases, and all special characters

**SPARQLBuilder module with safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), and triple_pattern() — plus 66 unit tests covering injection payloads, edge cases, and all special characters**

## What Happened

The SPARQLBuilder module at `backend/app/sparql/builder.py` and its comprehensive test suite at `backend/tests/test_sparql_builder.py` were already fully implemented from prior work. Verified that both files match every requirement in the task plan:

1. **safe_iri(value)** — validates IRI structure (scheme, netloc/path, forbidden chars via regex), then serializes through `rdflib.URIRef.n3()`. Rejects all SPARQL injection vectors: angle bracket breakout, double-quote injection, whitespace/newline/tab injection, backslash injection, curly brace injection. Supports http, https, and urn schemes. Subsumes the old `_validate_iri()` logic from `browser/_helpers.py`.

2. **safe_literal(value, datatype, lang)** — constructs `rdflib.Literal` and calls `.n3()` for proper escaping. Handles datatype URIs and language tags. Rejects None values.

3. **sparql_escape_string(value)** — consolidated escape function covering `\`, `"`, `'`, `\n`, `\r`, `\t`. Superset of all 9 scattered escape functions: covers the `\r` and `\t` that several local versions missed, plus `'` escaping. This is the authoritative replacement.

4. **values_clause(var_name, iris)** — builds `VALUES (?var) { (<iri1>) (<iri2>) ... }` using `safe_iri()` for each entry. Validates non-empty list and var name.

5. **triple_pattern(s, p, o)** — builds `s p o .` patterns where each term is either a SPARQL variable (`?x`/`$x`) passed through as-is, or an IRI validated via `safe_iri()`.

Test suite covers: valid IRIs (http, https, urn with paths/fragments/query params), empty/None edge cases, all SPARQL injection payload types, literal escaping for every special character, VALUES clause construction with valid/invalid/malicious IRIs, triple patterns with mixed variables and IRIs.

Confirmed that `sparql_escape_string` is a strict superset of every scattered escape function: `_sparql_escape` (search.py, workspace.py), `_escape_sparql` (mount_service.py, webhooks.py, federation/service.py), `_sparql_escape_str` (api/router.py, api/ai.py), `_escape_sparql_string` (task_templates/service.py, federation/inbox.py). The scattered versions variously missed `\r`, `\t`, and/or `'` escaping.

## Verification

Ran `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` — all 66 tests pass in 0.11s. Verified all 5 public APIs are importable and that safe_iri rejects every injection vector that _validate_iri handles plus additional vectors (curly braces, complex multi-statement payloads). Verified sparql_escape_string produces correct output for combined special characters.

Slice-level verification (400 responses on invalid IRI payloads with logging) is not yet applicable — that requires T02-T04 to wire the builder into HTTP endpoints.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` | 0 | ✅ pass | 3900ms |


## Deviations

None. The builder module and test suite were already implemented in prior work, matching every task plan requirement. No code changes needed.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/builder.py`
- `backend/tests/test_sparql_builder.py`
