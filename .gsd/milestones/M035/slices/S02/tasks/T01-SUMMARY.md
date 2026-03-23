---
id: T01
parent: S02
milestone: M035
provides:
  - GraphContextService with 1-hop neighborhood SPARQL query
  - Token-budgeted human-readable serialization for LLM context
  - active_object_iri field on CopilotChatRequest
  - Graph context injection wired into copilot_chat() endpoint
key_files:
  - backend/app/copilot/context.py
  - backend/app/copilot/service.py
  - backend/app/copilot/schemas.py
  - backend/app/api/copilot.py
  - backend/tests/test_graph_context.py
key_decisions:
  - Single UNION SPARQL query for types + literals + outbound + inbound (efficiency over 4 separate queries)
  - Priority truncation order: header always included, then properties, outbound, inbound (highest-value context first)
  - Graceful degradation — graph context failures logged as warnings, chat proceeds without context
patterns_established:
  - GraphContextService dependency injection pattern (TriplestoreClient, LabelService, PrefixRegistry) matches CopilotService
  - _build_system_prompt() now accepts optional graph_context parameter — backward compatible, no existing callers broken
observability_surfaces:
  - copilot.context.neighborhood log (iri, triple_count, type/prop/outbound/inbound counts)
  - copilot.context.truncated log (iri, budget, actual_chars) when token budget exceeded
  - copilot.chat.graph_context log (iri, chars) on successful injection
  - copilot.chat.graph_context_error log (iri, error) on failure with graceful skip
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: GraphContextService with neighborhood SPARQL and token-budgeted serialization

**Created GraphContextService that queries 1-hop graph neighborhood via SPARQL UNION and serializes it as human-readable LLM context with priority-based token budget truncation, wired into the copilot chat endpoint via active_object_iri**

## What Happened

Built `GraphContextService` in `backend/app/copilot/context.py` with two async methods:

1. `get_neighborhood(iri)` — runs a single SPARQL UNION query against `urn:sempkm:current` to fetch types, literal properties, outbound object edges, and inbound edges for any IRI. Returns a structured dict.

2. `serialize_context(neighborhood, token_budget)` — resolves all IRIs to human-readable labels via `LabelService.resolve_batch()`, compacts predicates via `PrefixRegistry.compact()`, and assembles a text block with priority truncation: header (always), properties, outbound edges, inbound edges. Budget defaults to 2000 tokens (~8000 chars).

Extended `_build_system_prompt()` in `service.py` with an optional `graph_context` parameter — when provided, it's inserted between the schema context and the Instructions section. All existing callers pass no second argument, so backward compatibility is preserved.

Added `active_object_iri: str | None` to `CopilotChatRequest` in `schemas.py`.

Wired the full flow in `copilot_chat()` — when `active_object_iri` is present, instantiates `GraphContextService`, queries the neighborhood, serializes it, and injects into the system prompt. Wrapped in try/except for graceful degradation.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` — 13/13 tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` — 48/48 existing tests still pass (no regressions)
- Import check: `from app.copilot.context import GraphContextService` succeeds
- System prompt check: `_build_system_prompt('schema', graph_context='ctx')` includes context before Instructions section
- LSP diagnostics: clean (no errors) on context.py and copilot.py after reload

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` | 0 | ✅ pass | 0.29s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass | 0.32s |
| 3 | `cd backend && .venv/bin/python -c "from app.copilot.context import GraphContextService; print('OK')"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -c "from app.copilot.service import _build_system_prompt; ..."` | 0 | ✅ pass | <1s |

## Diagnostics

- Grep backend logs for `copilot.context.` prefix to see neighborhood queries, truncation events, and errors
- `copilot.context.neighborhood` logs include IRI, triple_count, and breakdown by category
- `copilot.context.truncated` fires when serialized text exceeds char budget
- `copilot.chat.graph_context_error` fires on query failure with IRI and exception (chat proceeds without context)

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/copilot/context.py` — new GraphContextService with get_neighborhood() and serialize_context()
- `backend/app/copilot/service.py` — modified _build_system_prompt() to accept optional graph_context parameter
- `backend/app/copilot/schemas.py` — added active_object_iri field to CopilotChatRequest
- `backend/app/api/copilot.py` — added GraphContextService import and wiring in copilot_chat() endpoint
- `backend/tests/test_graph_context.py` — 13 unit tests covering neighborhood parsing, serialization, truncation, empty/error cases, and system prompt integration
- `.gsd/milestones/M035/slices/S02/S02-PLAN.md` — added diagnostic verification step per pre-flight, marked T01 done
