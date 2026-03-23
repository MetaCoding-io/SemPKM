---
id: T01
parent: S01
milestone: M035
provides:
  - CopilotService class with build_schema_context, validate_query, execute_and_format, generate_sparql
  - Pydantic schemas for copilot chat request/response
  - Unit test suite for all CopilotService methods (32 tests)
key_files:
  - backend/app/copilot/__init__.py
  - backend/app/copilot/service.py
  - backend/app/copilot/schemas.py
  - backend/tests/test_copilot_service.py
key_decisions:
  - Mutation keyword check runs before read-keyword check so rejection errors name the specific forbidden keyword
  - Predicate validation is non-blocking (logs warning but does not reject query) to avoid false negatives from incomplete shape coverage
  - llm_call is injected as an async callable to keep CopilotService testable without HTTP dependencies
patterns_established:
  - Copilot service uses character-based token estimation (~4 chars/token) for schema context budget
  - SPARQL extraction from LLM responses: fenced code block first, then generic block, then heuristic line detection
  - Self-correction loop appends error feedback as user messages to the conversation
observability_surfaces:
  - Structured log events: copilot.schema_context.built, copilot.sparql.generated, copilot.sparql.validated, copilot.sparql.failed, copilot.sparql.retry, copilot.sparql.executed, copilot.sparql.formatted, copilot.sparql.unknown_predicates, copilot.sparql.generating
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Build CopilotService backend — schema context, SPARQL generation, validation, and self-correction

**Created CopilotService with schema context builder, SPARQL validation (read-only guard + mutation rejection + predicate checking), query execution with IRI pill formatting, and self-correction loop with max 2 retries — all passing 32 unit tests.**

## What Happened

Created the `backend/app/copilot/` module with three files:

1. **`__init__.py`** — module init.
2. **`schemas.py`** — Pydantic models: `CopilotChatRequest`, `CopilotMessage`, `SparqlGenerationResult`, `QueryExecutionResult`.
3. **`service.py`** — `CopilotService` class with four core methods:
   - `build_schema_context()` — queries ShapesService for all installed NodeShapes, serializes type names, property paths, datatypes, and constraint values as readable text with a prefix table. Truncates at a configurable token budget (default 4000 tokens, ~16K chars).
   - `validate_query()` — rejects mutation keywords (INSERT, DELETE, DROP, CLEAR, LOAD, CREATE, COPY, MOVE, ADD) with specific error messages, requires read keywords (SELECT, ASK, CONSTRUCT, DESCRIBE), and logs non-blocking warnings for unknown predicates.
   - `execute_and_format()` — runs SPARQL through `inject_prefixes()` + `scope_to_current_graph()` + `client.query()`, collects object IRIs matching `base_namespace`, resolves labels via LabelService, and formats prose with `[[iri|label]]` markers for frontend pill rendering.
   - `generate_sparql()` — orchestrates the self-correction loop: builds system prompt with schema context, calls LLM via injected callable, extracts SPARQL from response (code blocks or heuristic), validates, retries up to 2 times with error feedback.

Two module-level helpers: `_extract_sparql_from_response()` (three-tier extraction: fenced code block → generic block → heuristic line detection) and `_build_system_prompt()` (role description + schema context + formatting instructions).

Also created `backend/tests/test_copilot_service.py` with 32 unit tests covering all must-haves: schema context building, SPARQL validation (accept/reject), unknown predicate warnings, query execution/formatting with IRI markers, SPARQL extraction from various response formats, self-correction retry logic, LLM call failure handling, and Pydantic schema validation.

## Verification

- `cd backend && .venv/bin/python -c "from app.copilot.service import CopilotService; print('import ok')"` → **pass**
- `cd backend && .venv/bin/python -c "from app.copilot.schemas import CopilotChatRequest; print(CopilotChatRequest.model_json_schema())"` → **pass**
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` → **32 passed, 0 failed**

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.copilot.service import CopilotService; print('import ok')"` | 0 | ✅ pass | <1s |
| 2 | `cd backend && .venv/bin/python -c "from app.copilot.schemas import CopilotChatRequest; print(CopilotChatRequest.model_json_schema())"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass | 0.30s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_endpoint.py -v` | 4 | ⏳ expected (T04) | <1s |

### Slice-level verification status (intermediate — T01 of 4):
- `tests/test_copilot_service.py` — ✅ passes (32/32)
- `tests/test_copilot_endpoint.py` — ⏳ file not yet created (T04 responsibility)
- Manual browser verification — ⏳ requires T02 (endpoint) + T03 (frontend)

## Diagnostics

- **Structured logs:** All CopilotService methods emit structured log events with the `copilot.*` prefix. To inspect schema context building: grep for `copilot.schema_context.built`. To trace SPARQL generation attempts: grep for `copilot.sparql.generating`, `copilot.sparql.validated`, `copilot.sparql.retry`.
- **Failure visibility:** Validation rejections log the specific mutation keyword or missing read keyword. Unknown predicates log the full IRI list. Self-correction exhaustion logs the final error.
- **Test inspection:** `pytest tests/test_copilot_service.py -v --tb=short` shows all 32 test outcomes with assertion details.

## Deviations

- Reordered validation checks: mutation keyword check now runs before read-keyword check (plan listed them in the opposite order). This gives more specific error messages when a query contains only mutation keywords (e.g. "forbidden keyword: INSERT" instead of "no read keyword found").

## Known Issues

None.

## Files Created/Modified

- `backend/app/copilot/__init__.py` — empty module init
- `backend/app/copilot/schemas.py` — Pydantic models for copilot chat request/response
- `backend/app/copilot/service.py` — CopilotService with schema context, validation, execution, and self-correction
- `backend/tests/test_copilot_service.py` — 32 unit tests covering all service methods
- `.gsd/milestones/M035/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
