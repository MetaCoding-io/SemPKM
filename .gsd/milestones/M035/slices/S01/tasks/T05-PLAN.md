---
estimated_steps: 3
estimated_files: 3
skills_used:
  - test
  - review
---

# T05: Unit tests for CopilotService and integration verification script

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Write comprehensive pytest unit tests for CopilotService and an integration verification script that confirms the full S01 delivery: files exist, routers are wired, nginx is configured, placeholder is replaced, and unit tests pass. This task closes the slice's verification loop.

## Steps

1. **Extend `backend/tests/test_copilot_service.py`** (created in T01 with initial tests) with comprehensive coverage. All tests use mocked dependencies (no Docker or triplestore needed). Test structure follows existing test files in `backend/tests/` (pytest-asyncio, AsyncMock, in-memory SQLite):

   - **Schema context tests:**
     - `test_build_schema_context_with_types`: mock `ShapesService.get_types()` returning 3 types, mock `get_form_for_type()` returning property shapes. Assert the output string contains type names, property paths, datatypes, and enum values.
     - `test_build_schema_context_truncation`: mock many types, assert output stays under 3500 chars.
     - `test_build_schema_context_empty`: mock empty types list, assert returns a fallback message.

   - **Query validation tests:**
     - `test_validate_query_valid_select`: valid `SELECT ?s WHERE { ... }` returns `(True, None)`.
     - `test_validate_query_rejects_insert`: query with INSERT returns `(False, "...")`.
     - `test_validate_query_rejects_delete`: query with DELETE returns `(False, "...")`.
     - `test_validate_query_rejects_drop`: query with DROP returns `(False, "...")`.
     - `test_validate_query_allows_delete_in_string`: query with "DELETE" inside a string literal returns `(True, None)` — validates that string stripping works.
     - `test_validate_query_checks_predicates`: query referencing unknown predicate returns `(False, "Unknown predicate: ...")`.
     - `test_validate_query_accepts_known_predicates`: query using predicates from the known set returns `(True, None)`.

   - **Result formatting tests:**
     - `test_format_results_count_query`: SPARQL results with `COUNT(*)` produce "You have N items" style prose.
     - `test_format_results_tabular`: SPARQL results with multiple bindings produce a markdown table with labels.
     - `test_format_results_resolves_iris`: IRI values in results are resolved via LabelService mock.

   - **System prompt tests:**
     - `test_build_system_prompt_includes_schema`: assert schema context appears in the system message.
     - `test_build_system_prompt_includes_instructions`: assert key instructions (GRAPH clause, SELECT only) present.

   - **Retry prompt tests:**
     - `test_build_retry_prompt_includes_error`: assert error message appears in retry prompt.
     - `test_build_retry_prompt_includes_original_query`: assert original query in prompt.

2. **Create `.gsd/milestones/M035/slices/S01/verify-s01.sh`** — executable bash script that performs all slice-level verification:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   PASS=0; FAIL=0
   check() { if eval "$2"; then echo "✓ $1"; ((PASS++)); else echo "✗ $1"; ((FAIL++)); fi; }

   check "copilot.js exists" "test -f frontend/static/js/copilot.js"
   check "copilot.css exists" "test -f frontend/static/css/copilot.css"
   check "CopilotService module exists" "test -f backend/app/services/copilot.py"
   check "Copilot API module exists" "test -f backend/app/api/copilot.py"
   check "ai_router in main.py" "grep -q 'ai_router' backend/app/main.py"
   check "copilot_router in main.py" "grep -q 'copilot_router' backend/app/main.py"
   check "nginx copilot SSE config" "grep -q 'api/copilot' frontend/nginx.conf"
   check "placeholder removed" "! grep -q 'coming in v2.1' backend/app/templates/browser/workspace.html"
   check "copilot container in template" "grep -q 'copilot-container' backend/app/templates/browser/workspace.html"
   check "lazy-load in workspace.js" "grep -q 'copilot' frontend/static/js/workspace.js"

   echo ""; echo "Results: $PASS passed, $FAIL failed"
   [ "$FAIL" -eq 0 ]
   ```

3. **Run all verification** — execute the pytest suite and the verification script. Ensure all tests pass and the script exits 0. Fix any issues found.

## Must-Haves

- [ ] At least 15 unit tests covering schema context, query validation, result formatting, system prompt, and retry prompt
- [ ] All tests use mocked dependencies (no Docker/triplestore required)
- [ ] Tests follow existing `backend/tests/` patterns (pytest-asyncio, AsyncMock)
- [ ] Verification script checks all S01 deliverables and exits 0

## Verification

- `cd backend && python -m pytest tests/test_copilot_service.py -v` — all tests pass, 15+ tests
- `bash .gsd/milestones/M035/slices/S01/verify-s01.sh` — script exits 0 with all checks passing

## Inputs

- `backend/app/services/copilot.py` — CopilotService from T01
- `backend/app/api/copilot.py` — copilot endpoint from T02
- `frontend/static/js/copilot.js` — chat UI from T03
- `frontend/static/css/copilot.css` — styles from T03
- `backend/app/main.py` — router wiring from T02
- `frontend/nginx.conf` — SSE config from T02
- `backend/app/templates/browser/workspace.html` — template from T03
- `frontend/static/js/workspace.js` — lazy-load from T03

## Expected Output

- `backend/tests/test_copilot_service.py` — comprehensive test suite (15+ tests)
- `.gsd/milestones/M035/slices/S01/verify-s01.sh` — integration verification script
