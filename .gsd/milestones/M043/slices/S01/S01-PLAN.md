# S01: SPARQL Injection & Escape Consolidation

**Goal:** Close all SPARQL injection vectors (F-006/F-007/F-008/F-009/F-010) by building a central SPARQLBuilder using rdflib's .n3() for safe IRI/literal serialization, then migrating all exploitable and likely-exploitable modules to use it.
**Demo:** Crafted IRI payloads to /browser/views/generic/table?type=PAYLOAD, /browser/apps/right-pane-sections?iri=PAYLOAD, and VFS mount creation all return 400. Favorites rejects malicious IRIs at storage time.

## Must-Haves

- SPARQLBuilder module exists at backend/app/sparql/builder.py with safe_iri(), safe_literal(), values_clause(), triple_pattern() methods\n- All 9 scattered escape functions replaced with imports from builder\n- _validate_iri() logic absorbed into builder.safe_iri() with rdflib URIRef.n3() as the serialization layer\n- Confirmed-exploitable modules migrated: views/service.py, views/router.py, browser/apps.py, vfs/mount_router.py\n- Likely-exploitable modules migrated: browser/events.py, browser/favorites.py, api/ai.py, api/router.py\n- Unit tests: malicious IRI payloads return 400, escape function handles all special chars\n- Exploit regression tests: exact payloads from F-006/F-007/F-008 audit findings verified blocked

## Proof Level

- This slice proves: Unit tests for builder primitives + exploit regression tests + all existing tests green

## Integration Closure

No downstream dependencies — this slice only tightens existing endpoints. All existing tests must pass.

## Verification

- 400 responses on invalid IRI payloads logged with source IP and attempted value for security monitoring.

## Tasks

- [x] **T01: Build SPARQLBuilder module with safe_iri() and safe_literal()** `est:3h`
  Create backend/app/sparql/builder.py with:

1. safe_iri(value: str) -> str: Validates the IRI, constructs rdflib.URIRef, calls .n3() to get properly escaped <iri> form. Raises ValueError on invalid IRIs. Subsumes _validate_iri() logic.
2. safe_literal(value: str, datatype: str|None = None, lang: str|None = None) -> str: Constructs rdflib.Literal, calls .n3() to get properly escaped string with datatype/language tags. Handles quotes, newlines, backslashes, tabs, carriage returns.
3. values_clause(var_name: str, iris: list[str]) -> str: Builds VALUES (?var) { (<iri1>) (<iri2>) ... } using safe_iri() for each entry.
4. triple_pattern(s: str, p: str, o: str) -> str: Builds a safe triple pattern where s/p/o can be variables (?x) or IRIs.
5. sparql_escape_string(value: str) -> str: Consolidated escape function covering \, ", ', \n, \r, \t — the authoritative replacement for all 9 scattered functions.

Unit tests in backend/tests/test_sparql_builder.py covering: valid IRIs, malicious IRI payloads (angle bracket breakout, comment injection, whitespace injection), literal escaping for all special characters, VALUES clause construction, empty/None edge cases.
  - Files: `backend/app/sparql/builder.py`, `backend/tests/test_sparql_builder.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v

- [x] **T02: Migrate confirmed-exploitable modules to SPARQLBuilder** `est:4h`
  Replace all f-string SPARQL IRI interpolation in the 4 confirmed-exploitable modules with SPARQLBuilder calls:

1. views/service.py (~45 <{iri}> patterns): Replace type_iri interpolation in build_dynamic_query(), _build_default_select(), execute_graph_query(), etc. with safe_iri(). Replace VALUES clause construction with values_clause().
2. views/router.py (~31 patterns): Add safe_iri() validation on all type/iri query parameters at endpoint entry point before any service call. This is the primary injection boundary.
3. browser/apps.py (~20 patterns): Replace raw f"<{iri}>" in right_pane_sections() and other endpoints with safe_iri().
4. vfs/mount_router.py (~41 patterns in mount_service + 72 in mount_router): Replace IRI field interpolation in mount creation/update SPARQL INSERT DATA with safe_iri(). Replace string interpolation with safe_literal().

For each module: remove the local escape function, import from sparql.builder, verify the module's existing tests pass.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/app/browser/apps.py`, `backend/app/vfs/mount_router.py`, `backend/app/vfs/mount_service.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60

- [x] **T03: Migrate likely-exploitable modules and remove all legacy escape functions** `est:3h`
  1. Migrate likely-exploitable modules:
   - browser/events.py: Replace bare replace('"', '\\"') with safe_literal() from builder
   - browser/favorites.py: Add safe_iri() validation on object_iri in toggle_favorite() before SQL storage
   - api/ai.py: Replace _sparql_escape_str with sparql_escape_string from builder
   - api/router.py: Replace _sparql_escape_str with sparql_escape_string from builder

2. Migrate remaining safe-but-inconsistent modules that use local escape functions:
   - browser/search.py: Replace _sparql_escape
   - browser/workspace.py: Replace _sparql_escape
   - federation/inbox.py: Replace _escape_sparql_string
   - federation/service.py: Replace _escape_sparql
   - services/webhooks.py: Replace _escape_sparql
   - task_templates/service.py: Replace _escape_sparql_string

3. Delete all 9 now-unused local escape functions.
4. Verify zero remaining local escape function definitions via grep.
  - Files: `backend/app/browser/events.py`, `backend/app/browser/favorites.py`, `backend/app/api/ai.py`, `backend/app/api/router.py`, `backend/app/browser/search.py`, `backend/app/browser/workspace.py`, `backend/app/federation/inbox.py`, `backend/app/federation/service.py`, `backend/app/services/webhooks.py`, `backend/app/task_templates/service.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60 && rg 'def _sparql_escape|def _escape_sparql' app/ -g '*.py' | grep -v builder.py | wc -l | xargs test 0 -eq

- [ ] **T04: Exploit regression tests — verify audit payloads are blocked** `est:2h`
  Create backend/tests/test_sparql_injection_regression.py with exact exploit payloads from the M042 audit:

1. F-006: GET /browser/views/generic/table?type=x>%20.%20?s%20?p%20?o%20}%20%23 → must return 400 or sanitized result (no data leak)
2. F-007: GET /browser/apps/right-pane-sections?iri=x>%20.%20?s%20?p%20?o%20}%20%23 → must return 400 (now also requires auth)
3. F-008: POST /browser/vfs/mounts with crafted group_by_property → must return 400
4. F-009: POST /browser/favorites with crafted object_iri → must return 400 or reject at validation
5. F-010: events.py search with backslash-quote breakout → must not leak data

Tests use FastAPI TestClient with authenticated sessions. Each test verifies the specific payload from the audit finding is rejected.
  - Files: `backend/tests/test_sparql_injection_regression.py`
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py -v

## Files Likely Touched

- backend/app/sparql/builder.py
- backend/tests/test_sparql_builder.py
- backend/app/views/service.py
- backend/app/views/router.py
- backend/app/browser/apps.py
- backend/app/vfs/mount_router.py
- backend/app/vfs/mount_service.py
- backend/app/browser/events.py
- backend/app/browser/favorites.py
- backend/app/api/ai.py
- backend/app/api/router.py
- backend/app/browser/search.py
- backend/app/browser/workspace.py
- backend/app/federation/inbox.py
- backend/app/federation/service.py
- backend/app/services/webhooks.py
- backend/app/task_templates/service.py
- backend/tests/test_sparql_injection_regression.py
