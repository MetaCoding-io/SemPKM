---
estimated_steps: 5
estimated_files: 5
---

# T01: Set up pytest infrastructure and write SPARQL escaping + serialization tests

**Slice:** S03 — Backend Test Foundation
**Milestone:** M002

## Description

Establish the pytest infrastructure that all subsequent tasks depend on: `[tool.pytest.ini_options]` in `pyproject.toml`, `backend/tests/__init__.py`, and `conftest.py` with settings isolation fixtures. Then write the first two test modules covering `escape_sparql_regex()` (SEC-04, TEST-02) and `_serialize_rdf_term()` (TEST-02).

## Steps

1. Add `[tool.pytest.ini_options]` section to `backend/pyproject.toml` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["."]`.
2. Create `backend/tests/__init__.py` (empty).
3. Create `backend/tests/conftest.py` with:
   - Module-level `os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"` **before** any `app.*` imports (prevents `_get_secret_key()` from writing files).
   - `@pytest.fixture(autouse=True)` `reset_serializer` fixture that sets `tokens._serializer = None` after each test (prevents singleton pollution).
   - `@pytest.fixture` `tmp_key_dir` using `tmp_path` for token file operations.
4. Create `backend/tests/test_sparql_utils.py` with tests for `escape_sparql_regex()`:
   - Test backslash escaping (must be first in sequence).
   - Test double-quote escaping.
   - Test each regex metacharacter: `.` `*` `+` `?` `^` `$` `{` `}` `(` `)` `|` `[` `]`.
   - Test passthrough of safe text (alphanumeric, spaces, underscores).
   - Test combined input with multiple metacharacters.
   - Test empty string input.
5. Create `backend/tests/test_rdf_serialization.py` with tests for `_serialize_rdf_term()`:
   - Test `URIRef` → `<uri>` wrapping.
   - Test plain `Literal` → `"value"`.
   - Test `Literal` with language tag → `"value"@en`.
   - Test `Literal` with datatype → `"value"^^<datatype>`.
   - Test `Literal` with special chars (backslash, quote, newline, carriage return, tab) → proper escaping.
   - Test `BNode` with explicit ID → `_:id` prefix.
   - Test `Variable` → `?name` prefix.
   - Test unsupported type raises `ValueError`.

## Must-Haves

- [ ] `[tool.pytest.ini_options]` in `pyproject.toml` with correct `asyncio_mode`, `testpaths`, `pythonpath`
- [ ] `conftest.py` sets `SECRET_KEY` env var before app imports
- [ ] `conftest.py` has autouse `reset_serializer` fixture
- [ ] `test_sparql_utils.py` covers all 15 metacharacters individually
- [ ] `test_rdf_serialization.py` covers URIRef, Literal (4 variants), BNode, Variable, error case

## Verification

- `cd backend && .venv/bin/pytest tests/test_sparql_utils.py tests/test_rdf_serialization.py -v` — all pass
- At least 6 tests in `test_sparql_utils.py` and 8 tests in `test_rdf_serialization.py`

## Observability Impact

- Signals added/changed: pytest config enables `pytest tests/ -v` as the standard test invocation from `backend/`
- How a future agent inspects this: run `cd backend && .venv/bin/pytest tests/ -v --tb=short` for quick status
- Failure state exposed: pytest assertion diffs show expected vs actual values per test

## Inputs

- `backend/app/sparql/utils.py` — `escape_sparql_regex()` function to test
- `backend/app/events/store.py` — `_serialize_rdf_term()` function to test (line 230)
- `backend/app/auth/tokens.py` — `_serializer` singleton that conftest must reset
- `backend/pyproject.toml` — needs pytest config section added

## Expected Output

- `backend/pyproject.toml` — updated with `[tool.pytest.ini_options]`
- `backend/tests/__init__.py` — created (empty)
- `backend/tests/conftest.py` — created with settings isolation and serializer reset fixtures
- `backend/tests/test_sparql_utils.py` — created with 6+ escape_sparql_regex tests
- `backend/tests/test_rdf_serialization.py` — created with 8+ _serialize_rdf_term tests
