---
id: T01
parent: S03
milestone: M002
provides:
  - pytest infrastructure (config, conftest, fixtures)
  - escape_sparql_regex() unit tests (19 tests)
  - _serialize_rdf_term() unit tests (15 tests)
key_files:
  - backend/pyproject.toml
  - backend/tests/conftest.py
  - backend/tests/test_sparql_utils.py
  - backend/tests/test_rdf_serialization.py
key_decisions:
  - Used os.environ["SECRET_KEY"] at module level in conftest.py (before imports) to prevent settings validation from triggering file I/O during test collection
patterns_established:
  - conftest.py sets SECRET_KEY before app imports; all test modules inherit this
  - autouse reset_serializer fixture prevents token singleton pollution between tests
  - Test classes group related tests; individual metacharacters get individual test methods for clear failure isolation
observability_surfaces:
  - "cd backend && .venv/bin/pytest tests/ -v" shows per-test pass/fail with assertion diffs
duration: 8m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Set up pytest infrastructure and write SPARQL escaping + serialization tests

**Established pytest infrastructure and wrote 34 passing tests covering escape_sparql_regex() and _serialize_rdf_term().**

## What Happened

Added `[tool.pytest.ini_options]` to `backend/pyproject.toml` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["."]`. Created `backend/tests/__init__.py`, and `conftest.py` with `SECRET_KEY` env var set before any app imports, an autouse `reset_serializer` fixture that nulls `tokens._serializer` after each test, and a `tmp_key_dir` fixture for file-based token operations.

Wrote `test_sparql_utils.py` with 19 tests: individual tests for all 15 metacharacters (backslash, double-quote, `.` `*` `+` `?` `^` `$` `{` `}` `(` `)` `|` `[` `]`), plus safe-text passthrough, combined metacharacters, empty string, and backslash-before-other-escapes ordering.

Wrote `test_rdf_serialization.py` with 15 tests: URIRef angle-bracket wrapping, plain Literal, Literal with language tag, Literal with datatype, 5 individual escape tests (backslash, quote, newline, carriage return, tab), combined special chars, BNode with explicit ID, Variable with `?` prefix, unsupported type ValueError, and two edge cases combining special chars with language tags and datatypes.

## Verification

- `cd backend && .venv/bin/pytest tests/test_sparql_utils.py tests/test_rdf_serialization.py -v` — **34 passed in 0.15s**
- `test_sparql_utils.py`: 19 tests (≥6 required ✓)
- `test_rdf_serialization.py`: 15 tests (≥8 required ✓)
- `cd backend && .venv/bin/pytest tests/ -v --tb=short` — 34 passed, 0 failures
- No Docker, triplestore, database, or running server required

### Slice-level verification (partial — T01 of 4):
- ✅ `cd backend && .venv/bin/pytest tests/ -v` — all tests pass
- ✅ `--tb=short` summary shows 0 failures
- ⬜ At least 5 tests in each of 5 test modules (2/5 modules exist so far)
- ✅ No test requires Docker, triplestore, database, or running server

## Diagnostics

- Run `cd backend && .venv/bin/pytest tests/ -v` for per-test results
- Run `cd backend && .venv/bin/pytest tests/ -v --tb=long` for full tracebacks on failure
- pytest exit code 0 = all pass, 1 = failures present

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/pyproject.toml` — added `[tool.pytest.ini_options]` section
- `backend/tests/__init__.py` — created (empty package marker)
- `backend/tests/conftest.py` — created with SECRET_KEY, reset_serializer, tmp_key_dir fixtures
- `backend/tests/test_sparql_utils.py` — created with 19 escape_sparql_regex tests
- `backend/tests/test_rdf_serialization.py` — created with 15 _serialize_rdf_term tests
