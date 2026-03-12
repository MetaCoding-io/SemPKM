---
id: T03
parent: S03
milestone: M002
provides:
  - 31 unit tests for _validate_iri() covering acceptance, forbidden characters, structural invalidity, and injection payloads
key_files:
  - backend/tests/test_iri_validation.py
key_decisions: []
patterns_established:
  - Use pytest.mark.parametrize for systematic per-character forbidden character testing (10 chars × 1 parametrized test)
observability_surfaces:
  - "Run `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — test names describe the exact character or pattern being tested"
duration: 5m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Write IRI validation tests

**Wrote 31 tests for `_validate_iri()` covering valid IRI acceptance (http/https/urn), all 10 forbidden SPARQL injection characters, structural invalidity, and real-world injection payloads.**

## What Happened

Created `backend/tests/test_iri_validation.py` with 5 test classes organized by category:

- **TestValidIRIs** (7 tests): http, https, urn:sempkm, urn:isbn, https with fragment, https with query, urn seed IRI
- **TestEmptyAndMissing** (3 tests): empty string, missing scheme, scheme-only
- **TestForbiddenCharacters** (10 tests): parametrized test covering `<`, `>`, `"`, `\`, `{`, `}`, `\n`, `\r`, `\t`, space — each embedded in an otherwise-valid IRI to prove independent rejection
- **TestStructuralInvalidity** (6 tests): http without netloc, urn without path, ftp/javascript/data/file schemes
- **TestInjectionPayloads** (5 tests): angle-bracket DROP, script tag, newline comment injection, curly-brace SELECT, backslash escape

## Verification

- `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — 31 passed in 0.54s
- `cd backend && .venv/bin/pytest tests/ -v` — 88 passed across all 4 modules in 0.55s
- Must-haves: ≥5 valid acceptance (7), all 10 forbidden chars (10), structural (6), injection payloads (5), ≥20 total (31) ✅

### Slice-level verification (intermediate — T04 remaining):
- `cd backend && .venv/bin/pytest tests/ -v` — 88 passed, 0 failures ✅
- 4 of 5 test modules exist (test_auth_tokens.py pending in T04)
- No test requires Docker, triplestore, database, or running server ✅

## Diagnostics

- Run `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — each test name describes the exact character or pattern being tested
- Use `--tb=long` for full tracebacks on failure
- Parametrized test IDs show the character repr for easy identification

## Deviations

None — implemented exactly per plan.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_iri_validation.py` — created with 31 tests for `_validate_iri()` organized in 5 classes by category
