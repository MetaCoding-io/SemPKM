# M035: AI Copilot & LLM Test Harness

**Vision:** A workspace AI copilot that understands the user's knowledge graph — generates and executes SPARQL, provides grounded writing assistance, creates objects from conversation, and adapts behavior through personas — backed by a 3-tier test harness that makes AI features testable at every level.

## Success Criteria

- User opens the AI COPILOT tab and has a streaming conversation with an LLM
- User asks "How many projects do I have?" — copilot generates SPARQL, shows it for approval, executes, returns a prose answer with clickable object links
- User asks "Summarize my notes about X" while viewing an object — copilot fetches the object's 1-hop neighborhood and produces a contextual answer referencing specific objects by name
- User switches to "Research Assistant" persona — copilot behavior shifts (system prompt changes, tone changes)
- User says "Create a task: Review Q1 goals, due Friday" — copilot shows a confirmation, then creates the object via Command API
- Conversation history persists across tab switches and page reloads
- Mock LLM tests run in CI in <5s with deterministic assertions
- Ollama integration test runs locally with real LLM inference
- Cloud test runs with budget cap enforcement

## Key Risks / Unknowns

- **SPARQL generation quality** — LLMs produce plausible but invalid SPARQL (wrong predicates, missing prefixes, syntax errors). The copilot needs parse verification, predicate checking against installed schemas, and self-correction from error messages.
- **Context window management** — A Project with 50 linked objects can produce 500+ triples. Naive context injection blows the token budget. Need intelligent truncation with token estimation.
- **SSE streaming through existing proxy** — The existing `llm_chat_stream` in settings.py is a simple passthrough. The copilot needs system prompt injection, conversation history prepending, and schema context — all server-side before proxying to the LLM.

## Proof Strategy

- **SPARQL generation quality** → retire in S01 by proving the copilot generates valid SPARQL against real installed model schemas, executes it successfully, and self-corrects from at least one error scenario
- **Context window management** → retire in S02 by proving 1-hop neighborhood serialization stays within a configurable token budget and produces useful context for the LLM
- **SSE streaming architecture** → retire in S01 by proving a new `/api/copilot/chat` endpoint injects system prompt + schema context and streams responses to the chat UI

## Verification Classes

- Contract verification: pytest unit tests for SPARQL validation, context serialization, persona CRUD, token estimation, conversation persistence; mock LLM server for deterministic E2E
- Integration verification: copilot chat against real RDF4J triplestore with installed basic-pkm model; real SPARQL execution through scope_to_current_graph
- Operational verification: conversation history survives page reload; persona selection persists per user; copilot degrades gracefully when LLM not configured; budget cap halts cloud test suite
- UAT / human verification: copilot answers are contextually relevant to the user's graph data; persona tone shift is perceptible

## Milestone Definition of Done

This milestone is complete only when all are true:

- Copilot chat UI renders streaming messages with markdown and object pill links
- SPARQL generation produces valid queries from natural language questions about installed model data
- Query approval flow (show → approve/edit/reject) works end-to-end
- Self-correction loop retries failed SPARQL at least once with error feedback
- Graph context injection populates LLM context from the active object's 1-hop neighborhood
- Conversation history persists in SQLite across page reloads
- AI persona selector switches system prompts and 4 built-in personas are available
- Object creation from chat produces real objects via Command API with user confirmation
- Mock LLM E2E tests pass in CI with deterministic assertions
- All success criteria re-checked against live Docker stack with real triplestore data

## Requirement Coverage

- Covers: AI-01 (copilot chat UI), AI-02 (SPARQL generation), AI-03 (query approval flow), AI-04 (graph context injection), AI-05 (conversation persistence), AI-06 (AI personas), AI-07 (object creation from chat), AI-08 (mock LLM test harness), AI-09 (Ollama integration tests), AI-10 (cloud test tier with budget cap)
- Partially covers: none
- Leaves for later: embedding-based semantic search (pgvector), autonomous agent actions, multi-modal, voice I/O
- Orphan risks: none — all Active requirements for this milestone are new (AI-01 through AI-10)

## Slices

- [x] **S01: Copilot Chat with SPARQL Generation** `risk:high` `depends:[]`
  > After this: user opens AI COPILOT tab, asks "How many projects do I have?", sees the generated SPARQL query for approval, approves it, and gets a prose answer with clickable object links — all streaming in real time against real triplestore data
- [ ] **S02: Graph Context Injection & Conversation Persistence** `risk:medium` `depends:[S01]`
  > After this: copilot automatically includes the active object's 1-hop neighborhood in its context, user asks "Summarize this project" while viewing a Project and gets an answer referencing linked tasks and notes by name, and conversation history persists across page reloads in SQLite
- [ ] **S03: AI Personas & Object Creation from Chat** `risk:low` `depends:[S01]`
  > After this: user picks "Research Assistant" from the persona selector and copilot shifts to citation-heavy responses, user says "Create a task: Review Q1 goals, due Friday" and copilot shows a confirmation card then creates the object via Command API
- [ ] **S04: LLM Test Harness & E2E Integration** `risk:low` `depends:[S01,S02,S03]`
  > After this: mock LLM E2E tests run in CI in <5s with deterministic copilot assertions, Ollama docker-compose variant runs real inference locally, cloud tier enforces per-run budget cap and reports token costs

## Boundary Map

### S01 → S02

Produces:
- `POST /api/copilot/chat` endpoint accepting `{messages, conversation_id?, model?}` and returning SSE stream
- `CopilotService` class with `generate_sparql()`, `validate_query()`, `execute_and_format()` methods
- `_build_schema_context()` that serializes installed model schemas as system prompt text
- Chat UI in `#panel-ai-copilot` with message rendering (markdown + IRI pills), query approval widget, streaming display
- `copilot.js` client-side module handling SSE, message rendering, approval flow
- `copilot.css` styles for chat messages, approval cards, streaming indicators

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Same as S01 → S02 (copilot endpoint, service, chat UI)
- System prompt injection point in `CopilotService` where persona prompts will be inserted

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- `GraphContextService` with `get_neighborhood()` and `serialize_context()` methods
- Token estimation utility (`estimate_tokens(text) → int`)
- SQLAlchemy models: `CopilotConversation`, `CopilotMessage` tables (Alembic migration)
- `ConversationService` CRUD for conversation threads and message persistence
- Conversation selector UI (new/switch/delete threads)

Consumes:
- S01 copilot endpoint and chat UI

### S03 → S04

Produces:
- SQLAlchemy model: `AIPersona` table (Alembic migration)
- `AIPersonaService` CRUD with 4 built-in personas seeded on first run
- Persona selector dropdown in copilot header
- Persona prompt template system with slot variables (`{installed_models}`, `{type_schemas}`, `{current_context}`)
- Object creation flow: NL → structured command → confirmation card → Command API dispatch
- `copilot-create-confirm` UI component for pre-creation review

Consumes:
- S01 copilot endpoint (system prompt injection point)
- S01 chat UI (message rendering, streaming)

### S04

Produces:
- Extended `e2e/mock-llm-api/server.py` with copilot-specific canned responses (SPARQL generation, summarization, persona behavior, object creation)
- `docker-compose.test.yml` updated with mock-llm-api service
- `docker-compose.test-ollama.yml` for local Ollama integration tests
- `e2e/tests/copilot.spec.ts` — Playwright E2E tests for copilot chat, SPARQL generation, persona switching, object creation
- `backend/tests/test_copilot_service.py` — unit tests for SPARQL validation, context serialization, token estimation
- Cloud tier test helper with token counting and budget cap enforcement
- Cost report utility for test suite runs

Consumes:
- S01 copilot endpoint and service
- S02 context injection and conversation persistence
- S03 persona system and object creation flow
