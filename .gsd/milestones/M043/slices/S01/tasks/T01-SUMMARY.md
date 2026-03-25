---
id: T01
parent: S01
milestone: M043
key_files:
  - backend/app/sparql/builder.py
  - backend/tests/test_sparql_builder.py
key_decisions:
  - safe_iri() uses two-layer defense: custom pre-validation (forbidden chars, scheme allowlist) THEN rdflib URIRef.n3() — because rdflib alone passes tabs, CRs, backslashes, and exotic schemes
  - Allowed URI schemes restricted to http/https/urn/mailto — other schemes like javascript/data/file/ftp are rejected
  - sparql_escape_string() returns the inner escaped string without quotes, while safe_literal() returns the full N3 form with quotes — callers pick based on whether they construct their own string delimiters
duration: ""
verification_result: passed
completed_at: 2026-03-25T07:12:47.916Z
blocker_discovered: false
---

# T01: Add centralised SPARQLBuilder module with safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), and triple_pattern() backed by rdflib .n3()

**Add centralised SPARQLBuilder module with safe_iri(), safe_literal(), sparql_escape_string(), values_clause(), and triple_pattern() backed by rdflib .n3()**

## What Happened

Created `backend/app/sparql/builder.py` — the authoritative replacement for 9 scattered SPARQL escape/validation functions across the codebase. The module provides five public functions:

1. **`safe_iri(value)`** — Validates an IRI string through a two-layer defense: first a pre-validation pass that rejects forbidden characters (`<>"\\{}\n\r\t` and control chars), validates the scheme is in the allowed set (`http`, `https`, `urn`, `mailto`), and checks structural requirements (host for HTTP, path for URN). Then delegates to `rdflib.URIRef.n3()` for properly escaped `<iri>` output. Raises `ValueError` on invalid input.

2. **`safe_literal(value, datatype, lang)`** — Constructs an `rdflib.Literal` and calls `.n3()` for properly escaped string literals with optional datatype or language tag.

3. **`sparql_escape_string(value)`** — Consolidated escape function covering `\`, `"`, `'`, `\n`, `\r`, `\t`. Returns the inner string without surrounding quotes. This is the drop-in replacement for all 9 scattered `_sparql_escape`/`_escape_sparql` variants.

4. **`values_clause(var_name, iris)`** — Builds `VALUES (?var) { (<iri1>) (<iri2>) }` with each IRI validated through `safe_iri()`.

5. **`triple_pattern(s, p, o)`** — Builds safe triple patterns where each component can be a SPARQL variable (`?x`) or an IRI validated through `safe_iri()`.

Also includes `validate_iri()` as a boolean convenience wrapper (drop-in replacement for the old `_validate_iri()` helper).

The pre-validation in `safe_iri()` is critical because rdflib alone lets through tabs, carriage returns, backslashes, and arbitrary URI schemes like `javascript:`. Our layer rejects all of these before rdflib ever sees the value.

Created comprehensive test suite with 75 tests covering: valid IRIs (http, https, urn, mailto), malicious injection payloads (angle bracket breakout, comment injection, whitespace injection, null bytes, control chars), scheme validation (javascript, data, file, ftp rejected), edge cases (empty, None, whitespace-only, missing host/path), literal escaping for all special characters, datatype and language tags, VALUES clause construction, triple patterns, and the backslash-quote breakout vector from F-010.

## Verification

Ran `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` — all 75 tests pass in 0.11s. Verified that malicious IRI payloads (angle bracket breakout, comment injection, newline injection, tab injection, control chars) are all rejected with ValueError. Verified that the module imports cleanly and LSP diagnostics show no errors.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` | 0 | ✅ pass | 110ms |


## Deviations

Removed unused `from rdflib.namespace import XSD` import flagged by Pyright. Added `validate_iri()` boolean wrapper not explicitly in the plan but needed as a drop-in replacement for the existing `_validate_iri()` function. Added `data:` scheme clean test case separate from the angle-bracket-containing variant since those hit different validation paths.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/builder.py`
- `backend/tests/test_sparql_builder.py`
