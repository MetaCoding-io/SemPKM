# S03: Backend Test Foundation

**Goal:** Establish pytest infrastructure in `backend/tests/` and deliver unit tests covering SPARQL escaping/serialization, IRI validation, auth token lifecycle, and `scope_to_current_graph` edge cases — all passing locally via `.venv/bin/pytest`.
**Demo:** `cd backend && .venv/bin/pytest tests/ -v` passes all tests in <5 seconds with zero Docker or triplestore dependency.

## Must-Haves

- `backend/tests/conftest.py` with settings isolation fixtures (env vars, tmp_path for key files, `_serializer` reset)
- `[tool.pytest.ini_options]` in `backend/pyproject.toml` with `asyncio_mode = "auto"`, `testpaths`, `pythonpath`
- Unit tests for `escape_sparql_regex()` covering all 15 metacharacters (TEST-02, SEC-04)
- Unit tests for `_serialize_rdf_term()` covering URIRef, Literal (plain, language, datatype, special chars), BNode, Variable (TEST-02)
- Unit tests for `_strip_sparql_strings()` and `scope_to_current_graph()` including string-literal edge cases (TEST-02, COR-02)
- Unit tests for `check_member_query_safety()` including string-literal false positive prevention (TEST-02)
- Unit tests for `_validate_iri()` covering http, https, urn, rejection of injection chars and unknown schemes (TEST-03)
- Unit tests for magic link token create/verify/expiry, invitation token create/verify/expiry, setup token lifecycle (TEST-04)

## Proof Level

- This slice proves: contract (pure-function unit tests with no external dependencies)
- Real runtime required: no (all targets are synchronous pure functions or functions with injectable settings)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — all tests pass
- `cd backend && .venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -5` — summary shows 0 failures
- At least 5 tests in each of the 5 test modules (25+ total tests)
- No test requires Docker, triplestore, database, or running server

## Observability / Diagnostics

- Runtime signals: pytest outputs structured pass/fail per test with assertion diffs on failure
- Inspection surfaces: `cd backend && .venv/bin/pytest tests/ -v` for per-test results; `--tb=long` for full tracebacks
- Failure visibility: pytest exit code 0/1 + detailed assertion messages with expected vs actual values
- Redaction constraints: test fixtures use fake `SECRET_KEY` values, never real secrets

## Integration Closure

- Upstream surfaces consumed: `app.sparql.utils.escape_sparql_regex()` (from S01), `app.sparql.client._strip_sparql_strings()` / `scope_to_current_graph()` (hardened in S02), `app.auth.tokens` (existing), `app.browser.router._validate_iri` (existing), `app.events.store._serialize_rdf_term` (existing)
- New wiring introduced in this slice: pytest config in `pyproject.toml`, `backend/tests/` directory with conftest and 5 test modules
- What remains before the milestone is truly usable end-to-end: S04 (router refactor using this test infra as safety net), S05 (dependency pinning), S06 (federation testing), S07 (Obsidian import)

## Tasks

- [x] **T01: Set up pytest infrastructure and write SPARQL escaping + serialization tests** `est:30m`
  - Why: Establishes the test foundation (TEST-01) and covers the first batch of pure-function targets (TEST-02 partial, SEC-04). Every subsequent task depends on conftest.py and pyproject.toml config.
  - Files: `backend/pyproject.toml`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_sparql_utils.py`, `backend/tests/test_rdf_serialization.py`
  - Do: Add `[tool.pytest.ini_options]` to pyproject.toml with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["."]`. Create `conftest.py` with a `SECRET_KEY` env var set before any app imports + `_serializer` reset fixture + `tmp_path`-based key file fixtures. Write `test_sparql_utils.py` testing all 15 metacharacters of `escape_sparql_regex()`. Write `test_rdf_serialization.py` testing `_serialize_rdf_term()` for URIRef, Literal (plain, language, datatype, special chars), BNode (explicit ID), Variable, and unsupported type error.
  - Verify: `cd backend && .venv/bin/pytest tests/test_sparql_utils.py tests/test_rdf_serialization.py -v` — all pass
  - Done when: pytest runs successfully from `backend/` with both test modules passing, conftest fixtures work

- [x] **T02: Write SPARQL client tests — string stripping, graph scoping, and member safety** `est:30m`
  - Why: Covers the core SPARQL safety functions including the S02-hardened `scope_to_current_graph()` edge cases (TEST-02, COR-02). These are the most injection-sensitive code paths.
  - Files: `backend/tests/test_sparql_client.py`
  - Do: Write tests for `_strip_sparql_strings()` — double-quoted strings, single-quoted, triple-quoted, hash comments, escaped quotes inside strings, mixed. Write tests for `scope_to_current_graph()` — basic injection, skip when `all_graphs=True`, skip when FROM already present, skip when GRAPH + CURRENT_GRAPH present, inferred graph inclusion, shared graphs, keyword-in-string-literal edge case (COR-02), no WHERE clause. Write tests for `check_member_query_safety()` — clean query passes, FROM rejected, GRAPH rejected, FROM/GRAPH in string literal NOT rejected (false positive prevention).
  - Verify: `cd backend && .venv/bin/pytest tests/test_sparql_client.py -v` — all pass
  - Done when: All string-stripping, graph-scoping, and member-safety tests pass including the COR-02 edge case

- [x] **T03: Write IRI validation tests** `est:20m`
  - Why: Covers the primary defense against SPARQL injection from user-controlled URL path segments (TEST-03).
  - Files: `backend/tests/test_iri_validation.py`
  - Do: Write tests for `_validate_iri()` — valid http/https IRIs, valid urn IRIs, empty string, missing scheme, relative path, each forbidden character (`<>"\\{}\n\r\t` and space), http without netloc, urn without path, unknown scheme (ftp, javascript), exception handling. Test both acceptance and rejection categories.
  - Verify: `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — all pass
  - Done when: Comprehensive acceptance/rejection tests for `_validate_iri()` all pass

- [x] **T04: Write auth token lifecycle tests** `est:25m`
  - Why: Covers security-critical auth token logic that is currently untested (TEST-04). Requires careful settings isolation to prevent singleton pollution.
  - Files: `backend/tests/test_auth_tokens.py`
  - Do: Write tests for magic link tokens — create returns string, verify roundtrip recovers email, expired token returns None (using `max_age_seconds=0`), tampered token returns None, wrong salt returns None. Write tests for invitation tokens — create returns string, verify roundtrip recovers email+role dict, expired returns None, tampered returns None. Write tests for setup tokens — `load_or_create_setup_token` creates file and returns token, second call returns same token, `delete_setup_token` removes file, load after delete creates new token. All token tests use the `reset_serializer` fixture from conftest to prevent cross-test pollution.
  - Verify: `cd backend && .venv/bin/pytest tests/test_auth_tokens.py -v` — all pass
  - Done when: Full token lifecycle (create/verify/expiry/tamper/setup) tests pass with proper settings isolation

## Files Likely Touched

- `backend/pyproject.toml`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_sparql_utils.py`
- `backend/tests/test_rdf_serialization.py`
- `backend/tests/test_sparql_client.py`
- `backend/tests/test_iri_validation.py`
- `backend/tests/test_auth_tokens.py`
