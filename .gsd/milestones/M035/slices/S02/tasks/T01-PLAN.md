---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T01: GraphContextService with neighborhood SPARQL and token-budgeted serialization

**Slice:** S02 — Graph Context Injection & Conversation Persistence
**Milestone:** M035

## Description

Create the backend service that queries a 1-hop graph neighborhood for any IRI from the triplestore and serializes it as human-readable text suitable for LLM system prompt injection. The service must enforce a configurable token budget (default 2000 tokens ≈ 8000 chars) with priority-based truncation. Wire it into the existing copilot chat endpoint so that when the frontend sends an `active_object_iri`, the graph context is injected into the system prompt alongside the existing schema context.

## Steps

1. **Create `backend/app/copilot/context.py`** with `GraphContextService` class:
   - Constructor accepts `TriplestoreClient`, `LabelService`, `PrefixRegistry` (same dependency pattern as `CopilotService`)
   - `async get_neighborhood(iri: str) -> dict` — runs SPARQL query against `urn:sempkm:current` graph to get: (a) the object's `rdf:type`, (b) literal property values (`FILTER(isLiteral(?o))`), (c) outbound object edges (`FILTER(isIRI(?o)) FILTER(?p != rdf:type)`), (d) inbound object edges (`?source ?p <iri>`)
   - Use a single UNION query for efficiency (see existing pattern in `backend/app/browser/objects.py` line 534+)
   - Return structured dict: `{"iri": str, "types": [str], "properties": {predicate: [value]}, "outbound": [(predicate, target_iri)], "inbound": [(source_iri, predicate)]}`
   - `async serialize_context(neighborhood: dict, token_budget: int = 2000) -> str` — resolves all IRIs to labels via `LabelService.resolve_batch()`, compacts predicates via `PrefixRegistry.compact()`, and builds human-readable text. Truncation priority: own literal properties first, then outbound edges, then inbound edges. Use `CHARS_PER_TOKEN = 4` from `service.py`.
   - Format example: `"## Current Context\nYou are looking at: Project 'Q1 Planning' (bpkm:Project)\n\nProperties:\n- title: Q1 Planning\n- dueDate: 2026-03-28\n\nOutbound relations:\n- hasTask → Task 'Review Goals'\n- hasTask → Task 'Budget Review'\n\nInbound relations:\n- Note 'Q1 Summary' → relatedTo → this"`

2. **Add `active_object_iri` to `CopilotChatRequest`** in `backend/app/copilot/schemas.py`:
   ```python
   active_object_iri: str | None = Field(None, description="IRI of the active object tab for graph context injection")
   ```

3. **Add `graph_context` parameter to `_build_system_prompt()`** in `backend/app/copilot/service.py`:
   - Change signature: `def _build_system_prompt(schema_context: str, graph_context: str | None = None) -> str`
   - When `graph_context` is provided, append it after the schema section and before the `## Instructions` section
   - Update the call site in `generate_sparql()` if it uses `_build_system_prompt` directly (check — it does)

4. **Wire graph context into `copilot_chat()` endpoint** in `backend/app/api/copilot.py`:
   - After building `copilot_svc`, check if `chat_req.active_object_iri` is not None
   - If present, create `GraphContextService` from `request.app.state` services, call `await ctx_svc.get_neighborhood(chat_req.active_object_iri)`, then `await ctx_svc.serialize_context(neighborhood)`
   - Pass the result to `_build_system_prompt(schema_context, graph_context=graph_context_text)`
   - Wrap in try/except — on failure, log warning and proceed without graph context (graceful degradation)
   - Update the `_build_system_prompt` import (it's a module-level function, not a method)

5. **Write unit tests** in `backend/tests/test_graph_context.py`:
   - Test `get_neighborhood()` with mocked triplestore returning sample bindings for properties, outbound, and inbound queries
   - Test `serialize_context()` with a sample neighborhood dict — verify human-readable output format, label resolution, predicate compaction
   - Test token budget truncation — provide a large neighborhood, verify output stays within budget
   - Test empty neighborhood (IRI with no triples) — should return minimal context
   - Test graceful handling when label resolution returns empty dict

## Must-Haves

- [ ] GraphContextService queries urn:sempkm:current graph for 1-hop neighborhood
- [ ] serialize_context produces human-readable text (not raw triples)
- [ ] Token budget is enforced with priority truncation (properties > outbound > inbound)
- [ ] `active_object_iri` accepted in chat request and wired to system prompt
- [ ] Graceful skip when active_object_iri is null or neighborhood query fails
- [ ] Unit tests pass with mocked triplestore

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` — all tests pass
- `cd backend && python -c "from app.copilot.context import GraphContextService; print('OK')"` — import succeeds
- `cd backend && python -c "from app.copilot.service import _build_system_prompt; print(_build_system_prompt('schema', graph_context='ctx'))"` — includes graph context section

## Observability Impact

- Signals added: `copilot.context.neighborhood` (iri, triple_count, estimated_tokens), `copilot.context.truncated` (iri, budget, actual_chars)
- How a future agent inspects this: grep backend logs for `copilot.context.` prefix
- Failure state exposed: graph context query failures logged as warnings with IRI and exception, chat proceeds without context

## Inputs

- `backend/app/copilot/service.py` — existing `_build_system_prompt()` function to extend with graph_context parameter, `CHARS_PER_TOKEN` constant
- `backend/app/copilot/schemas.py` — existing `CopilotChatRequest` to add `active_object_iri` field
- `backend/app/api/copilot.py` — existing `copilot_chat()` endpoint to wire in GraphContextService
- `backend/app/browser/objects.py` — reference for SPARQL UNION pattern querying current/inferred graphs (line 534+)
- `backend/app/services/labels.py` — `LabelService.resolve_batch()` for IRI label resolution
- `backend/app/services/prefixes.py` — `PrefixRegistry.compact()` for predicate display names

## Expected Output

- `backend/app/copilot/context.py` — new GraphContextService with get_neighborhood() and serialize_context()
- `backend/app/copilot/service.py` — modified _build_system_prompt() accepting graph_context parameter
- `backend/app/copilot/schemas.py` — modified CopilotChatRequest with active_object_iri field
- `backend/app/api/copilot.py` — modified copilot_chat() wiring GraphContextService
- `backend/tests/test_graph_context.py` — unit tests for GraphContextService
