# S03: Backend Test Foundation — Research

**Date:** 2026-03-12

## Summary

S03 establishes the backend pytest infrastructure and writes unit tests for four security/correctness-critical modules: SPARQL escaping/serialization, IRI validation, auth token logic, and `scope_to_current_graph` edge cases. This covers requirements TEST-01 through TEST-04, and provides supporting test coverage for SEC-04 and COR-02.

All four target modules are **synchronous pure functions** (except `EventStore.commit()` which is async but not a test target). The test functions under scope have minimal dependencies — `sparql/utils.py` has zero imports, `sparql/client.py` imports only `re`, `fastapi.HTTPException`, and namespace constants, `auth/tokens.py` depends on `itsdangerous` and `app.config.settings`, and `_validate_iri` in `browser/router.py` uses only `urllib.parse.urlparse`. This means tests can run outside Docker, with no triplestore, no database, and no running server — just the Python venv.

The primary recommendation is: create `backend/tests/` with a `conftest.py` that handles settings isolation (env vars for `SECRET_KEY`, `SECRET_KEY_PATH`, `SETUP_TOKEN_PATH` via `tmp_path`), add `[tool.pytest.ini_options]` to `pyproject.toml` with `asyncio_mode = "auto"`, and write four focused test modules — one per requirement.

## Recommendation

**Approach:** Pure-function unit tests running locally via `.venv/bin/pytest`. No Docker, no triplestore, no server.

**Why:** All four target areas are pure logic functions or functions with a single injectable dependency (settings). The test infrastructure should be lightweight and fast — these tests gate the S04 router refactor. Running them should take <2 seconds.

**Structure:**
```
backend/
  pyproject.toml          # Add [tool.pytest.ini_options] section
  tests/
    __init__.py
    conftest.py           # Settings isolation, tmp_path fixtures
    test_sparql_utils.py  # TEST-02: escape_sparql_regex()
    test_sparql_client.py # TEST-02: _strip_sparql_strings(), scope_to_current_graph(), check_member_query_safety()
    test_iri_validation.py # TEST-03: _validate_iri()
    test_auth_tokens.py   # TEST-04: magic link + invitation token lifecycle
    test_rdf_serialization.py # TEST-02: _serialize_rdf_term()
```

**Key design choices:**
1. `conftest.py` sets `SECRET_KEY` env var before any `app.config` import, and provides a fixture to reset the `_serializer` singleton between tests.
2. Test files import private functions directly (e.g., `from app.browser.router import _validate_iri`) — this is fine for unit tests of private functions that are the primary defense against SPARQL injection.
3. `asyncio_mode = "auto"` in pyproject.toml so async test functions just work without `@pytest.mark.asyncio` on every test. (pytest-asyncio 1.3.0 supports this.)
4. No mocks for external services — these are all pure function tests. The conftest provides tmp directories for auth token file operations.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| SPARQL regex escaping | `app.sparql.utils.escape_sparql_regex()` | Already created in S01 (D008). Test it directly. |
| SPARQL string stripping | `app.sparql.client._strip_sparql_strings()` | Created in S02 (D009). Private but importable for testing. |
| Signed token generation | `itsdangerous.URLSafeTimedSerializer` | Already used by `app.auth.tokens`. Don't re-implement; test the wrapper. |
| Settings isolation in tests | `monkeypatch.setenv()` or env vars before import | pytest's `monkeypatch` fixture handles env var isolation cleanly. |

## Existing Code and Patterns

- `backend/app/sparql/utils.py` — `escape_sparql_regex()`: standalone function, zero imports, pure string transformation. Perfect unit test target. Escapes 15 metacharacters for SPARQL REGEX() injection safety.
- `backend/app/sparql/client.py` — `_strip_sparql_strings()`: regex-based helper that blanks string literal interiors and comments. `scope_to_current_graph()`: injects FROM clauses before WHERE. `check_member_query_safety()`: rejects FROM/GRAPH for member role. All sync, all pure logic.
- `backend/app/browser/router.py:48` — `_validate_iri()`: validates IRI scheme (http/https/urn), rejects SPARQL injection chars (`<>"\\{}\n\r\t `), requires netloc for http/https, path for urn. Uses `urllib.parse.urlparse`.
- `backend/app/events/store.py:230` — `_serialize_rdf_term()`: serializes rdflib `URIRef`, `Literal`, `BNode`, `Variable` to SPARQL syntax. Escapes `\`, `"`, `\n`, `\r`, `\t` in literal values. Handles language tags and datatypes.
- `backend/app/auth/tokens.py` — Complete auth token module with: `create_magic_link_token()`, `verify_magic_link_token()` (10min expiry), `create_invitation_token()`, `verify_invitation_token()` (7 day expiry), `load_or_create_setup_token()`, `delete_setup_token()`. Uses module-level `_serializer` singleton (lazy-init) that must be reset between tests.
- `backend/app/validation/report.py:165` — `report_iri` property with SHA-256 fallback. Extractable test target for deterministic hash verification.
- `backend/pyproject.toml` — `pytest` and `pytest-asyncio` already in `[project.optional-dependencies] dev`. No `[tool.pytest.ini_options]` section yet.

## Constraints

- **Python 3.14 in .venv, 3.12 in Docker** — tests must run in the local .venv (Python 3.14). The Dockerfile uses `python:3.12-slim`. No 3.14-specific features should be assumed in the code under test.
- **`app.config.settings` is a module-level singleton** — `auth/tokens.py` imports `settings` at module level. The `_get_secret_key()` function reads `settings.secret_key` and `settings.secret_key_path`. Tests must set env vars *before* the settings object is imported, or use `monkeypatch` to override attributes.
- **`_serializer` is a module-level lazy singleton** — `auth/tokens.py` caches the `URLSafeTimedSerializer` in `_serializer`. After any settings change, `tokens._serializer` must be reset to `None` or tests will use a stale serializer.
- **No pytest config exists yet** — `pyproject.toml` has no `[tool.pytest.ini_options]`. Need to add `asyncio_mode`, `testpaths`, and `pythonpath` settings.
- **pytest-asyncio 1.3.0 installed** — supports `asyncio_mode = "auto"` and `@pytest_asyncio.fixture`. No version upgrade needed.
- **`_validate_iri` is private** — defined inside `browser/router.py` with a leading underscore. Importable for testing but should not be treated as a public API. If S04 moves it during the router refactor, test imports will need updating.

## Common Pitfalls

- **Settings singleton pollution across tests** — If `conftest.py` doesn't isolate `SECRET_KEY`, the lazy `_serializer` persists from the first test that triggers `_get_secret_key()`. All subsequent tests use the same key, which is fine for positive cases but hides bugs in key resolution. **Fix:** Reset `tokens._serializer = None` in a fixture's teardown.
- **`_get_secret_key()` writes to disk** — If `settings.secret_key` is empty and `secret_key_path` doesn't exist, it *generates and writes* a key file. In tests, `SETUP_TOKEN_PATH` and `SECRET_KEY_PATH` must point to tmp directories to avoid polluting the project. **Fix:** Set `SECRET_KEY` env var to a known test value, or point paths to `tmp_path`.
- **`_strip_sparql_strings` interior blanking is position-sensitive** — The function preserves string delimiters and replaces interiors with spaces. Tests that check the output should account for the space-padded result, not assume the string is removed entirely.
- **`scope_to_current_graph` checks for `CURRENT_GRAPH` string literal in the query** — The function does `if CURRENT_GRAPH in query:` as a raw substring check, meaning a query with `urn:sempkm:current` anywhere (even in a string literal) would skip scoping. This is a known edge case worth testing.
- **`_serialize_rdf_term` for `BNode`** — BNode serialization uses `_:` prefix. rdflib BNodes get auto-generated IDs that vary. Tests should create BNodes with explicit IDs.

## Open Risks

- **`_validate_iri` extraction in S04** — S04's router refactor will likely move `_validate_iri` to a shared module. S03 tests importing `from app.browser.router import _validate_iri` will break. This is acceptable — the test should be updated as part of S04. Alternatively, S03 could extract it proactively, but that increases scope.
- **pytest-asyncio `auto` mode may conflict with future test patterns** — `asyncio_mode = "auto"` makes all `async def test_*` functions async tests automatically. If a future slice adds tests that use a different event loop, this could conflict. Low risk for S03 since all tests are sync.
- **Token expiry testing with `max_age_seconds=0`** — Testing token expiry requires either `time.sleep()` (slow, flaky) or passing `max_age_seconds=0` to the verify function (clean but tests the wrapper API differently than production). Recommend using `max_age_seconds=0` for immediate expiry testing.
- **`check_member_query_safety` raises `HTTPException`** — Tests need to import `fastapi.HTTPException` and use `pytest.raises()`. This is a FastAPI dependency but doesn't require a running server.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| pytest | `github/awesome-copilot@pytest-coverage` | available (7K installs) — general coverage patterns |
| pytest | `bobmatnyc/claude-mpm-skills@pytest` | available (454 installs) — pytest patterns |
| FastAPI | `wshobson/agents@fastapi-templates` | available (6.1K installs) — FastAPI templates |
| FastAPI | `fastapi/fastapi@fastapi` | available (343 installs) — official FastAPI skill |

None of these are critical for this work. The test targets are pure functions with straightforward pytest patterns. No specialized skill needed.

## Sources

- `backend/pyproject.toml` — confirms pytest + pytest-asyncio in dev deps, no pytest config section yet
- `backend/app/sparql/utils.py` — `escape_sparql_regex()` source (18 LOC, zero deps)
- `backend/app/sparql/client.py` — `_strip_sparql_strings()`, `scope_to_current_graph()`, `check_member_query_safety()` source
- `backend/app/auth/tokens.py` — full token module (magic link, invitation, setup token lifecycle)
- `backend/app/browser/router.py:48-80` — `_validate_iri()` source
- `backend/app/events/store.py:230-270` — `_serialize_rdf_term()` source
- `backend/app/config.py` — Settings class, singleton pattern
- S01 task summaries — confirm `sparql/utils.py` created with `escape_sparql_regex()`
- S02 task summaries — confirm `_strip_sparql_strings()` helper and `scope_to_current_graph()` hardening
- Local verification — all four target functions run successfully outside Docker with `.venv/bin/python`
