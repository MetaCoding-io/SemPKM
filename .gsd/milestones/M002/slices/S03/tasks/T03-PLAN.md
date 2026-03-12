---
estimated_steps: 2
estimated_files: 1
---

# T03: Write IRI validation tests

**Slice:** S03 — Backend Test Foundation
**Milestone:** M002

## Description

Write comprehensive acceptance/rejection tests for `_validate_iri()` from `browser/router.py`. This function is the primary defense against SPARQL injection from user-controlled URL path segments. Tests must cover valid schemes (http, https, urn), all forbidden injection characters, missing components, and edge cases.

## Steps

1. Create `backend/tests/test_iri_validation.py` with import `from app.browser.router import _validate_iri`.
2. Write tests organized by category:
   - **Valid IRIs (acceptance):** `https://example.org/data/obj1`, `http://example.org/item`, `urn:sempkm:model:basic-pkm:Note`, `urn:isbn:0451450523`, https with path and fragment.
   - **Invalid — empty/missing:** empty string, missing scheme (`example.org/data`), scheme-only (`http://`).
   - **Invalid — forbidden characters:** each of `<`, `>`, `"`, `\`, `{`, `}`, `\n`, `\r`, `\t`, space — tested individually in an otherwise-valid IRI to prove each is independently rejected.
   - **Invalid — structural:** http without netloc (`http:///path`), urn without path (`urn:`), unknown scheme (`ftp://example.org`), `javascript:alert(1)`.
   - **Invalid — injection payloads:** `https://example.org/data/obj1> ; DROP`, `https://example.org/data/<script>`.

## Must-Haves

- [ ] At least 5 valid IRI acceptance tests (http, https, urn variants)
- [ ] Each of the 10 forbidden characters tested individually for rejection
- [ ] Structural rejection tests (missing netloc, missing path, unknown scheme)
- [ ] Injection payload rejection tests

## Verification

- `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — all pass
- At least 20 tests covering both acceptance and rejection categories

## Observability Impact

- Signals added/changed: None (pure test code)
- How a future agent inspects this: test names describe the exact character or pattern being tested
- Failure state exposed: boolean assertion failures clearly show which IRI was incorrectly accepted/rejected

## Inputs

- `backend/app/browser/router.py` — `_validate_iri()` function at line 48
- `backend/tests/conftest.py` — from T01, provides settings isolation (needed for module imports)

## Expected Output

- `backend/tests/test_iri_validation.py` — created with 20+ tests covering valid IRIs, forbidden characters, structural invalidity, and injection payloads
