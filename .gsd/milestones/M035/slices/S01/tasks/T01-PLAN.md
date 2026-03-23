---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Build CopilotService backend — schema context, SPARQL generation, validation, and self-correction

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Create the `backend/app/copilot/` module with the core CopilotService class. This is the intelligence layer that:
1. Builds LLM system prompts containing installed model schema context (types, properties, prefixes)
2. Validates generated SPARQL queries (parse check, predicate verification, read-only guard)
3. Executes validated queries through the existing SPARQL pipeline (scope_to_current_graph + inject_prefixes)
4. Orchestrates a self-correction loop when generated SPARQL fails (max 2 retries, error message fed back to LLM)

The service does NOT handle HTTP/SSE — that's T02's job. This task produces pure Python service classes that T02's router will call.

## Steps

1. Create `backend/app/copilot/__init__.py` (empty module init).

2. Create `backend/app/copilot/schemas.py` with Pydantic models:
   - `CopilotChatRequest` — `messages: list[dict]`, `conversation_id: str | None`, `model: str | None`
   - `CopilotMessage` — `role: str`, `content: str`
   - `SparqlGenerationResult` — `query: str | None`, `error: str | None`, `retries: int`
   - `QueryExecutionResult` — `bindings: list[dict]`, `prose: str`, `object_iris: list[str]`

3. Create `backend/app/copilot/service.py` with `CopilotService` class:
   - Constructor takes `triplestore_client: TriplestoreClient`, `shapes_service: ShapesService`, `label_service: LabelService`, `prefix_registry: PrefixRegistry`
   - `async build_schema_context() -> str` — calls `shapes_service.get_node_shapes()` to get all installed type shapes, serializes each as "Type: {label} ({target_class})\n  Properties: {name} ({path}, datatype: {dt})\n  ..." text. Include prefix table from `prefix_registry.get_all_prefixes()`. Use character-based token estimation (~4 chars/token per D326) and truncate at configurable budget (default 4000 tokens = ~16000 chars).
   - `validate_query(query: str) -> tuple[bool, str | None]` — (a) regex check for SELECT, ASK, CONSTRUCT, DESCRIBE keywords (reject INSERT, DELETE, DROP, CLEAR, LOAD, CREATE), (b) extract predicate IRIs from the query and check against known predicates from `shapes_service.get_labels_for_predicates()` or the vocabulary endpoint pattern. Return `(True, None)` if valid, `(False, error_message)` if invalid.
   - `async execute_and_format(query: str) -> QueryExecutionResult` — run query through `inject_prefixes()` + `scope_to_current_graph()` + `client.query()`. Extract bindings, collect object IRIs (those matching base_namespace), resolve labels via `label_service.resolve_batch()`, format as prose string with IRI references marked as `[[iri|label]]` placeholders.
   - `async generate_sparql(user_message: str, schema_context: str, llm_call: Callable) -> SparqlGenerationResult` — build prompt with schema context + user question, call `llm_call` to get response, extract SPARQL from markdown code blocks or raw text, validate with `validate_query()`, if validation fails retry (max 2 per D324) with error feedback appended to messages. The `llm_call` parameter is a callable that takes messages and returns a string — this keeps the service testable without HTTP dependencies.

4. Add a `_extract_sparql_from_response(text: str) -> str | None` helper that extracts SPARQL from LLM response text — looks for ```sparql...``` or ```sql...``` code blocks first, falls back to heuristic detection (lines starting with SELECT/PREFIX/ASK/CONSTRUCT).

5. Add a `_build_system_prompt(schema_context: str) -> str` helper that constructs the full system prompt including: role description (SPARQL assistant for a semantic knowledge graph), schema context section, instruction to output SPARQL in a code block, instruction to wrap object IRIs in the answer as `[[iri|label]]` for pill rendering.

## Must-Haves

- [ ] `CopilotService.build_schema_context()` produces readable text with type names, property paths, and datatypes from ShapesService
- [ ] `CopilotService.validate_query()` accepts valid SELECT/ASK/CONSTRUCT and rejects INSERT/DELETE/DROP/CLEAR
- [ ] `CopilotService.validate_query()` warns on unknown predicates (non-blocking — query can still run)
- [ ] `CopilotService.execute_and_format()` runs SPARQL through scope_to_current_graph and returns prose with `[[iri|label]]` markers
- [ ] `CopilotService.generate_sparql()` implements self-correction loop with max 2 retries
- [ ] `_extract_sparql_from_response()` handles both code-block and raw-text SPARQL

## Verification

- `cd backend && .venv/bin/python -c "from app.copilot.service import CopilotService; print('import ok')"` — module imports without error
- `cd backend && .venv/bin/python -c "from app.copilot.schemas import CopilotChatRequest; print(CopilotChatRequest.model_json_schema())"` — schema validates

## Inputs

- `backend/app/services/shapes.py` — ShapesService.get_node_shapes() for type schema extraction
- `backend/app/services/labels.py` — LabelService.resolve_batch() for IRI→label resolution
- `backend/app/services/prefixes.py` — PrefixRegistry.get_all_prefixes() for prefix table
- `backend/app/sparql/client.py` — scope_to_current_graph(), inject_prefixes() for safe query execution
- `backend/app/triplestore/client.py` — TriplestoreClient.query() for SPARQL execution
- `backend/app/config.py` — settings.base_namespace for object IRI detection

## Observability Impact

- **New structured log events:** `copilot.schema_context.built` (token count, type count), `copilot.sparql.generated` (query text), `copilot.sparql.validated` (valid/invalid, error message), `copilot.sparql.failed` (query text, error), `copilot.sparql.retry` (attempt number, previous error), `copilot.sparql.executed` (binding count, IRI count)
- **Inspection:** Future agents can verify CopilotService behavior by checking structured log output for the above events. `build_schema_context` logs the estimated token count; `generate_sparql` logs each retry attempt with the error that triggered it.
- **Failure visibility:** SPARQL validation failures log the rejected query text and the reason (mutation keyword detected, unknown predicate). Self-correction loop exhaustion logs the final error after max retries.

## Expected Output

- `backend/app/copilot/__init__.py` — empty module init
- `backend/app/copilot/service.py` — CopilotService with build_schema_context, validate_query, execute_and_format, generate_sparql
- `backend/app/copilot/schemas.py` — Pydantic request/response models
