---
depends_on: [M033]
---

# M035: AI Copilot & LLM Test Harness

**Gathered:** 2026-03-21
**Status:** Queued — pending auto-mode execution

## Project Description

Build the workspace AI Copilot — a conversational interface in the existing "AI COPILOT" bottom panel that understands the user's knowledge graph, generates and executes SPARQL queries, provides writing assistance grounded in existing objects, and adapts its behavior through configurable personas. Alongside the copilot, build a 3-tier LLM test harness (mock server for CI, local Ollama for dev, cloud provider with budget caps) that makes AI features testable at every level without surprise costs.

## Why This Milestone

The workspace has an empty "AI COPILOT" tab placeholder (added in v2.0, still showing "coming in v2.1"). The LLM proxy infrastructure exists — SSE streaming to OpenAI-compatible endpoints via POST /browser/settings/llm/chat/stream. M028 built 6 AI API endpoints for the browser extension (claim detection, matching, relationship suggestion, summarization) but they're extension-facing and not wired into the workspace. The copilot panel is where users will spend the most time with AI — it needs to understand their graph deeply, not just forward prompts.

The test harness problem is urgent. The mock LLM server from M028 was recovered (e2e/mock-llm-api/server.py, 348 lines) but returns canned responses — fine for deterministic E2E tests but useless for evaluating prompt quality. Local LLM testing via Ollama avoids cloud costs but runs slowly on CPU. Cloud providers give the best quality but every test run costs money. The harness must let developers choose the right tradeoff per test type.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open the AI COPILOT tab in the workspace bottom panel and start a conversation
- Ask "What projects did I work on this week?" and get an answer derived from SPARQL query results
- Ask "Summarize my notes about machine learning" and get a summary that references specific Note objects by name
- Say "Create a task: Review Q1 goals, due Friday, high priority" and have the copilot create the object via Command API
- See the SPARQL query the copilot generated before it executes (with approve/edit/reject controls)
- Switch between AI personas: "Research Assistant" (citation-heavy, evidence chains), "Project Manager" (action-oriented, task generation), "Writing Coach" (style feedback, editing suggestions)
- Create and edit custom personas with system prompt templates
- See relevant graph context automatically injected into conversations (when discussing a Project, the copilot knows its tasks, people, and notes)
- Configure context depth (1-hop vs 2-hop neighborhood) in copilot settings

### Entry point / environment

- Entry point: http://localhost:3000/browser/ — AI COPILOT tab in bottom panel
- Environment: Docker Compose (api + triplestore + frontend/nginx + optional Ollama)
- Live dependencies involved: RDF4J triplestore, LLM provider (local Ollama or cloud OpenAI/Anthropic)

## Completion Class

- Contract complete means: copilot chat renders messages, SPARQL generation produces valid queries, persona system stores and applies system prompts, graph context injection populates the LLM context window, 3-tier test harness runs at all levels
- Integration complete means: copilot queries real triplestore data, creates real objects via Command API, persona prompts reference real schema information, context injection pulls real graph neighborhoods
- Operational complete means: conversation history persists across tab switches, persona selection persists per user, test harness works in CI (mock), local dev (Ollama), and cloud (capped), copilot degrades gracefully when LLM unavailable

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User asks "How many tasks are overdue?" — copilot generates SPARQL, shows it for approval, executes, returns "3 tasks are overdue" with links to each task
- User asks "Write a summary of the ML project" while viewing a Project object — copilot fetches the project's linked notes, concepts, and tasks via 1-hop SPARQL, produces a contextual summary
- User switches to "Research Assistant" persona — copilot responses shift to academic tone with citations to specific objects
- Mock LLM test runs in CI in <5s with deterministic assertions
- Ollama test runs locally with real LLM (llama3.2:1b) producing valid SPARQL
- Cloud test runs with OpenAI, costs <$0.10, fails if budget exceeded

## Risks and Unknowns

- **SPARQL generation quality** — LLMs generate plausible but wrong SPARQL. The copilot needs a validation layer: parse the generated query, check it references real predicates from installed models, and sandbox execution (read-only, timeout). If the query fails, the copilot should iterate (self-correct from the error message) rather than showing the user a stack trace.
- **Context window management** — Injecting graph triples into the LLM context bloats the prompt. A Project with 50 linked objects could produce 500+ triples. Need to be smart about what to include: prioritize by recency, relevance (type match), and proximity (1-hop only unless user asks for deeper). Token counting against the model's context limit is essential.
- **Ollama in Docker without GPU** — Standard Docker containers don't pass through GPU. Ollama runs on CPU for small models (llama3.2:1b ~700MB RAM, ~2-5 tokens/sec). Acceptable for integration tests but too slow for interactive use. GPU passthrough exists but requires nvidia-container-toolkit and host-side drivers.
- **Conversation state management** — Where does conversation history live? Options: (a) browser-side in sessionStorage (simplest, lost on refresh), (b) server-side in SQLite per user (persistent), (c) RDF in triplestore (queryable but overkill). Server-side SQLite is the right balance for v1.
- **Persona prompt engineering** — System prompts that produce consistently good results across different LLM providers (OpenAI, Anthropic, Ollama/Llama) need careful testing. A prompt that works great on GPT-4 may fail on Llama 3.2. The persona templates should include provider-specific variants or be tested across providers.
- **Cost tracking for cloud tests** — OpenAI/Anthropic APIs don't report cost per request directly. Need to estimate from token counts (input + output) × model pricing. The budget cap is approximate, not exact.

## Existing Codebase / Prior Art

- `backend/app/templates/browser/workspace.html` — AI COPILOT tab placeholder at line with "AI Copilot — coming in v2.1" message. Panel ID: panel-ai-copilot. Verified on main.
- `backend/app/browser/settings.py` — POST /browser/settings/llm/chat/stream SSE streaming proxy to OpenAI-compatible endpoints. Cookie auth only. Handles model selection, error streaming, connection test. Verified on main.
- `backend/app/services/llm.py` — LLMConfigService: encrypted API key storage, config CRUD, Fernet symmetric encryption. Verified on main (125 lines).
- `backend/app/api/ai.py` — 1119-line AI router recovered from M028 worktree. 6 endpoints: POST /api/llm/stream (dual-auth SSE proxy), GET /api/llm/status, POST /api/ai/detect-claims, POST /api/ai/match-claims, POST /api/ai/suggest-relationships, POST /api/ai/summarize. NOT wired into main.py. Verified on main (just recovered).
- `e2e/mock-llm-api/server.py` — 348-line mock OpenAI-compatible server recovered from M028. Canned claim detection responses. 5-check selftest. Verified on main (just recovered).
- `backend/tests/test_ai_endpoints.py`, `test_claim_detection.py`, `test_claim_matching.py`, `test_llm_proxy.py` — M028 AI test files. Present on main. 59 tests total.
- `extension/tests/test-ai-client.js` — 22 Node.js tests for extension AI client methods. Present on main.
- `backend/app/sparql/client.py` — scope_to_current_graph(), check_member_query_safety(). Read-only query execution path. The copilot SPARQL execution should use this same path.
- `backend/app/sparql/router.py` — SPARQL API endpoints. Reference for query execution + result formatting.
- `backend/app/persona/` — Persona model (SQLAlchemy), service, router from M012. Workspace layout personas. NOT AI personas — but the pattern (CRUD, SQLite storage, user-scoped) is reusable.
- `backend/app/commands/dispatcher.py` — HANDLER_REGISTRY for Command API dispatch. The copilot creates objects through this same path.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New requirements to be created: AI-01 through AI-10+ covering copilot chat, SPARQL generation, graph context injection, persona system, object creation from chat, conversation persistence, test harness (3 tiers)
- Existing deferred advanced: "AI Copilot (chat about data, SPARQL generation, writing assistance)" in Future Candidates

## Scope

### In Scope

**Workspace AI Copilot Chat:**
- Replace "coming in v2.1" placeholder with functional chat interface
- Message thread UI (user messages, assistant responses, system messages)
- Markdown rendering in responses with object pill links (reuse SPARQL console IRI pill pattern)
- Conversation history per user in SQLite (Alembic migration)
- Multiple conversation threads with new/switch/delete
- SSE streaming responses (reuse existing LLM proxy pattern)
- Graceful degradation when LLM not configured

**SPARQL Generation & Execution:**
- System prompt includes installed model schemas (type IRIs, property paths, SHACL shape summaries)
- User question → LLM generates SPARQL → display for approval → execute → format results conversationally
- Query validation before execution: parse check, predicate verification against known schemas, read-only guard
- Self-correction: if query fails, feed error back to LLM for retry (max 2 retries)
- Results formatted as prose with clickable object links, not raw SPARQL bindings

**Graph Context Injection:**
- When user mentions or views an object, fetch its 1-hop neighborhood via SPARQL (outgoing edges, incoming edges, properties)
- Serialize neighborhood as readable text (not raw triples) using LabelService for human names
- Token budget management: estimate context size, truncate if over model limit (configurable, default 4000 tokens for context)
- Configurable depth: 1-hop (default) or 2-hop (opt-in, much larger context)
- Context sources: focused object (if object tab active), recent conversation objects, user's pinned/favorite objects

**AI Personas:**
- CRUD for persona definitions (name, icon, system prompt template, model preference, temperature)
- Persona selector in copilot header (dropdown or tab bar)
- Built-in personas: "General Assistant", "Research Assistant", "Project Manager", "Writing Coach"
- System prompt templates with slot variables: {user_name}, {installed_models}, {type_schemas}, {current_context}, {recent_objects}
- Custom persona creation/editing UI in copilot settings
- Per-persona conversation history separation

**Object Creation from Chat:**
- Copilot can create objects via Command API when user requests it
- "Create a task: Review Q1 goals, due Friday, high priority" → object.create + object.patch
- Confirmation step: copilot shows what it will create before executing
- Created objects link back to the conversation (provenance)

**3-Tier LLM Test Harness:**

Tier 1 — Mock LLM Server (CI):
- Extend existing e2e/mock-llm-api/server.py with configurable response fixtures
- Canned responses per prompt pattern (SPARQL generation, summarization, persona behavior)
- Deterministic — same input always produces same output
- Runs as Docker service in docker-compose.test.yml
- All E2E AI tests use this by default
- Target: <5s per test, zero cost

Tier 2 — Local Ollama (Development):
- docker-compose.test-ollama.yml adds Ollama service with llama3.2:1b pre-pulled
- OLLAMA_API_URL env var overrides LLM config in test stack
- Integration tests run real inference for prompt quality evaluation
- CPU-only (~2-5 tok/s for 1b model), no GPU required
- Target: <60s per test, zero cost, non-deterministic

Tier 3 — Cloud Provider (Evaluation):
- Configurable via OPENAI_API_KEY / ANTHROPIC_API_KEY env vars
- Per-test-run token counting and cost estimation
- Budget cap per test suite run (configurable, default $1.00)
- Test fails with clear message if budget exceeded
- Cost report at end of test run: total tokens, estimated cost, per-test breakdown
- Target: most realistic responses, $0.01-0.10 per test

**Test Harness Infrastructure:**
- Test helper that auto-selects tier based on available env vars (cloud key > Ollama URL > mock)
- Shared assertion helpers for AI response quality (contains_sparql, references_object, tone_matches_persona)
- Prompt quality regression tests: saved "golden" responses compared against new LLM output

### Out of Scope / Non-Goals

- Autonomous agent actions (auto-create objects without user confirmation) — user must approve
- Embedding-based semantic search (pgvector) — use FTS + SPARQL for now
- Voice input/output
- Multi-modal (image understanding)
- Fine-tuning or training custom models
- Real-time collaborative AI (multiple users sharing copilot session)
- Browser extension AI features (already in M028, separate from workspace copilot)

## Technical Constraints

- Frontend: htmx + vanilla JS. Chat UI is vanilla DOM manipulation with SSE for streaming.
- LLM communication via existing SSE proxy pattern (POST /browser/settings/llm/chat/stream or new /api/copilot/chat endpoint)
- SPARQL execution through existing scope_to_current_graph() — copilot cannot bypass graph scoping
- Persona storage in SQLite (alongside workspace personas from M012 — different table, same pattern)
- Conversation history in SQLite (not RDF — conversations are user state, not knowledge graph data)
- Ollama Docker image is ~1.2GB for the base + ~700MB for llama3.2:1b. Test stack must handle this gracefully (pull on first run, cache in Docker volume).
- Cloud cost tracking is approximate (token count × known model pricing) — not exact billing API integration

## Integration Points

- **LLM proxy (settings.py)** — existing SSE streaming to OpenAI-compatible endpoints. Copilot uses same LLM config.
- **M028 AI endpoints (api/ai.py)** — 6 endpoints to wire into main.py. Copilot may reuse summarize and detect-claims internally.
- **SPARQL client** — scope_to_current_graph for safe query execution. check_member_query_safety for read-only guard.
- **Command API** — object creation from chat through standard dispatcher
- **LabelService** — readable names for graph context injection
- **ShapesService** — type schemas for SPARQL generation system prompts
- **ViewSpecService** — type IRIs and properties for schema context
- **Workspace personas (M012)** — pattern reference for SQLite CRUD, but separate table for AI personas
- **Mock LLM server (M028)** — extend for copilot-specific canned responses
- **FullCalendar/Kanban/Views** — copilot may reference visible data ("What's on my calendar today?")

## Open Questions

- **Copilot endpoint path** — New /api/copilot/chat with dual-auth, or reuse /browser/settings/llm/chat/stream with extended message format? New endpoint is cleaner — different system prompt injection, conversation history, persona context.
- **Schema context size** — How much type schema to include in system prompt? All types from all models could be 2000+ tokens. Option: only include schemas for types the user has data for, or types mentioned in conversation.
- **Conversation persistence** — SQLite conversations table with user_id, persona_id, messages JSON blob? Or one row per message with foreign key to conversation? Per-message rows allow pagination and search but are more complex.
- **SPARQL self-correction loop** — How many retries before giving up? 2 retries (3 total attempts) with the error message fed back. After 3 failures, show the error and suggest the user try rephrasing.
- **Ollama model selection** — llama3.2:1b for fast CPU inference in tests. Should the test stack also support larger models (3b, 8b) for developers with GPUs? Configurable via OLLAMA_MODEL env var, default to 1b.
