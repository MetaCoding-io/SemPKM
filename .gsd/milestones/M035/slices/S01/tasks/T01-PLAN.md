---
estimated_steps: 6
estimated_files: 2
skills_used:
  - test
  - review
---

# T01: Build CopilotService with schema context and SPARQL generation

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Create the core backend service class that powers the AI copilot. `CopilotService` is the brain: it builds schema context from installed Mental Models (so the LLM knows what types and predicates exist), generates SPARQL from natural language via LLM, validates the generated queries (parse check, read-only guard, predicate verification), executes them against the triplestore, formats results as prose with IRI references, and handles self-correction when queries fail.

This task focuses on the service layer only — no API endpoint, no frontend. The service will be consumed by T02's endpoint.

## Steps

1. **Create `backend/app/services/copilot.py`** with the `CopilotService` class. The constructor accepts `triplestore_client: TriplestoreClient`, `shapes_service: ShapesService`, `label_service: LabelService`, and `llm_config_service: LLMConfigService`.

2. **Implement `build_schema_context(db: AsyncSession) -> str`** — queries `ShapesService.get_types()` to get all installed type IRIs and labels, then for each type calls `ShapesService.get_form_for_type(type_iri)` to get property shapes. Serializes into a compact text block like:
   ```
   Available types and their properties:
   - Project (urn:sempkm:model:basic-pkm:Project): title, description, status [todo|in-progress|done], assignedTo → Person
   - Task (urn:sempkm:model:basic-pkm:Task): title, dueDate (date), priority [low|medium|high], status [todo|in-progress|done]
   ...
   ```
   Include property datatypes, enum constraints (sh:in values), and object reference target classes. Cap total output at ~3000 chars to stay within token budget. Use common SPARQL prefixes (dcterms, rdfs, rdf, bpkm) in the output.

3. **Implement `build_system_prompt(schema_context: str) -> str`** — constructs the system prompt that instructs the LLM to generate SPARQL queries. Key instructions: always use `GRAPH <urn:sempkm:current>` for scoping, use the exact predicate IRIs from the schema context, return SPARQL in a ```sparql code fence, use SELECT queries only, include PREFIX declarations. Provide 2-3 example question→SPARQL pairs using the schema context types.

4. **Implement `validate_query(sparql: str, known_predicates: set[str]) -> tuple[bool, str | None]`** — (a) regex check that query contains no INSERT/DELETE/DROP/CLEAR/CREATE/LOAD keywords outside string literals (reuse `_strip_sparql_strings` from `backend/app/sparql/client.py`); (b) basic parse: check balanced braces, contains SELECT keyword; (c) predicate verification: extract IRI-like tokens from the query and check they exist in `known_predicates` set (built from schema context). Returns `(True, None)` on success or `(False, "error message")` on failure.

5. **Implement `execute_query(sparql: str) -> dict`** — wraps the query with `scope_to_current_graph()` from `backend/app/sparql/client.py` then calls `triplestore_client.query()`. Catches exceptions and returns structured error dict.

6. **Implement `format_results(sparql_results: dict, db: AsyncSession) -> str`** — takes SPARQL JSON results, extracts all IRI values, batch-resolves labels via `LabelService.resolve_batch()`, then builds a markdown string where IRIs become `[Label](iri:full-iri)` references (the frontend will convert these to clickable pills). For count queries, produce natural language like "You have 5 projects." For tabular results, produce a markdown table with labeled columns.

7. **Implement `build_retry_prompt(original_query: str, error_message: str) -> list[dict]`** — constructs a messages array that shows the LLM the failed query and error, asking it to fix the SPARQL. Used by the self-correction loop in T04.

## Must-Haves

- [ ] `CopilotService` class with all 6 methods implemented
- [ ] `build_schema_context()` serializes installed model types and properties into compact text
- [ ] `validate_query()` rejects mutating queries (INSERT/DELETE/DROP)
- [ ] `validate_query()` checks predicates against known model schemas
- [ ] `execute_query()` uses `scope_to_current_graph()` for safety
- [ ] `format_results()` resolves IRI labels and produces markdown with IRI references
- [ ] Structured logging with `copilot.` prefix at key points

## Verification

- `cd backend && python -m pytest tests/test_copilot_service.py -v` — all tests pass
- `python -c "from app.services.copilot import CopilotService; print('import OK')"` (run from backend/) — module imports cleanly

## Inputs

- `backend/app/services/shapes.py` — ShapesService API for getting types and property shapes
- `backend/app/services/labels.py` — LabelService.resolve_batch() for IRI label resolution
- `backend/app/services/llm.py` — LLMConfigService for LLM config and API key
- `backend/app/sparql/client.py` — scope_to_current_graph(), _strip_sparql_strings()
- `backend/app/triplestore/client.py` — TriplestoreClient.query()

## Expected Output

- `backend/app/services/copilot.py` — new CopilotService class with all methods
- `backend/tests/test_copilot_service.py` — pytest unit tests with mocked dependencies (ShapesService, LabelService, TriplestoreClient, LLMConfigService)
