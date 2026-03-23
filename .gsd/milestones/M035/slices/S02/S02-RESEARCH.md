# S02 Research: Graph Context Injection & Conversation Persistence

**Slice scope:** Two independent subsystems — (1) inject the active object's 1-hop graph neighborhood into the copilot's LLM context, (2) persist conversation threads in SQLite with CRUD endpoints and a frontend conversation selector.

**Requirements owned:** AI-04 (graph context injection), AI-05 (conversation persistence) — both referenced in the roadmap but not yet in REQUIREMENTS.md.

## Summary

This is **targeted research**. Both features follow established codebase patterns (SPARQL queries for graph data, SQLAlchemy models + Alembic migration + CRUD service for persistence, vanilla JS UI additions to the existing copilot panel). No unfamiliar technology. The main design decisions are around SPARQL neighborhood query shape, token budget enforcement for context serialization, and the conversation persistence data model.

## Recommendation

Build graph context injection first (riskier — SPARQL + token estimation + system prompt changes), then conversation persistence (straightforward CRUD, lower risk). Five tasks:

1. **GraphContextService** — service with `get_neighborhood(iri)` and `serialize_context(triples, token_budget)`. Pure service, no HTTP dependency. Unit-testable with mocked triplestore.
2. **Wire graph context into copilot endpoint** — accept `active_object_iri` from frontend, call GraphContextService, inject into `_build_system_prompt()`. Frontend sends the active panel's IRI with each chat request.
3. **Conversation data model + migration** — SQLAlchemy models (`CopilotConversation`, `CopilotMessage`), Alembic migration 016. ConversationService with create/list/get/delete/add_message.
4. **Conversation API endpoints** — REST endpoints for conversation CRUD. Wire into copilot chat flow: auto-create conversation on first message, load history on subsequent requests, save messages after each exchange.
5. **Conversation selector UI + persistence integration** — Frontend: conversation list sidebar, new/switch/delete controls. Connect `_messageThread` to backend storage. Load on init, save after each exchange.

## Implementation Landscape

### Graph Context Injection

**Where neighborhood data comes from:** The `get_relations()` endpoint in `backend/app/browser/objects.py` (lines ~180-250) already queries outbound + inbound edges across current/inferred/mirrored graphs using a UNION pattern. The GraphContextService needs the same query logic but returns structured data instead of rendering a template.

**SPARQL pattern for 1-hop neighborhood:**
```sparql
# Properties (literal values)
SELECT ?p ?o WHERE {
  GRAPH <urn:sempkm:current> { <{iri}> ?p ?o . FILTER(isLiteral(?o)) }
}

# Outbound object edges
SELECT ?p ?target WHERE {
  GRAPH <urn:sempkm:current> { <{iri}> ?p ?target . FILTER(isIRI(?target)) FILTER(?p != rdf:type) }
}

# Inbound object edges
SELECT ?source ?p WHERE {
  GRAPH <urn:sempkm:current> { ?source ?p <{iri}> . FILTER(isIRI(?source)) FILTER(?p != rdf:type) }
}

# Type of the focused object
SELECT ?type WHERE {
  GRAPH <urn:sempkm:current> { <{iri}> a ?type . }
}
```

These four queries can be combined into one UNION query for efficiency.

**Serialization format:** Human-readable text, not raw triples. The LLM doesn't need N-Triples syntax — it needs "Project 'Q1 Planning' has tasks: 'Review Goals' (due 2026-03-28), 'Budget Review' (due 2026-04-01)..." The serializer should:
- Use LabelService.resolve_batch() for all IRIs
- Use PrefixRegistry.compact() for predicate names
- Group by predicate (outbound edges grouped by relationship type)
- Include literal property values (title, description, dates)

**Token budget:** S01 established `CHARS_PER_TOKEN = 4` and `DEFAULT_TOKEN_BUDGET = 4000`. Graph context needs its own budget (default 2000 tokens = 8000 chars) separate from schema context. The `_build_system_prompt()` function should accept optional `graph_context: str` and inject it after the schema section.

**Where to inject in the system prompt:** `_build_system_prompt(schema_context)` → `_build_system_prompt(schema_context, graph_context=None)`. Add a `## Current Context` section after the schema section when graph_context is provided. The copilot router (`copilot_chat()` in `backend/app/api/copilot.py`) needs to accept `active_object_iri` from the request body, call `GraphContextService.get_neighborhood()`, serialize it, and pass it to `_build_system_prompt()`.

**Frontend → Backend context signal:** The `CopilotChatRequest` schema already has `conversation_id` and `model` fields. Add `active_object_iri: str | None = None`. The frontend reads `window._dockview.activePanel.id` (which is the object IRI for object tabs) and sends it with each chat request. The `sempkm:tab-activated` custom event fires on panel switches (workspace-layout.js line 344) — copilot.js should listen for this to track the active object IRI, not query it only at send time (avoids race conditions).

### Conversation Persistence

**Data model — per-message rows, not JSON blob:**
The roadmap's open question asked "messages JSON blob vs one row per message?" Per-message rows are the right choice for this codebase:
- Enables pagination (load last N messages without parsing a blob)
- Enables search across conversations
- Matches the SparqlQueryHistory per-record pattern
- Trivial to add message-level metadata later (SPARQL queries attached to messages, approval status, etc.)

**Tables:**
```
copilot_conversations:
  id          UUID PK
  user_id     UUID FK→users.id ON DELETE CASCADE (indexed)
  title       VARCHAR(255)  -- auto-set from first message, editable
  created_at  DATETIME(tz)
  updated_at  DATETIME(tz)

copilot_messages:
  id               UUID PK
  conversation_id  UUID FK→copilot_conversations.id ON DELETE CASCADE (indexed)
  role             VARCHAR(20)  -- 'user', 'assistant', 'system'
  content          TEXT
  created_at       DATETIME(tz)
```

**ConversationService methods:**
- `create_conversation(user_id, title?) → conversation`
- `list_conversations(user_id) → list[conversation]` (ordered by updated_at DESC)
- `get_conversation(conversation_id, user_id) → conversation + messages`
- `delete_conversation(conversation_id, user_id)`
- `add_message(conversation_id, role, content) → message`
- `update_title(conversation_id, title)`

**API endpoints:**
- `GET /api/copilot/conversations` — list user's conversations
- `POST /api/copilot/conversations` — create new conversation
- `GET /api/copilot/conversations/{id}` — get conversation with messages
- `DELETE /api/copilot/conversations/{id}` — delete conversation
- These can live in the existing `copilot_router` in `backend/app/api/copilot.py`.

**Chat flow integration:**
- `POST /api/copilot/chat` already accepts `conversation_id` in `CopilotChatRequest` (defined in S01, not yet consumed)
- On first message with `conversation_id=null`: auto-create a conversation, return `conversation_id` in a custom SSE event
- On subsequent messages: load conversation history from DB, prepend to messages (replacing the frontend's `_messageThread`)
- After stream completes: save both user message and assistant response to DB
- This means the backend becomes the source of truth for message history, not the frontend's `_messageThread` array

**Frontend conversation selector:**
- Add a header bar above the chat messages area with: conversation title, "New Chat" button, conversation list dropdown
- On init: fetch `GET /api/copilot/conversations`, display current or most recent
- On "New Chat": POST to create, clear messages area
- On switch: GET conversation with messages, re-render message thread
- On delete: DELETE conversation, switch to next or show empty state
- Store `_currentConversationId` in the module scope, send with each chat request

### File Inventory

**New files:**
- `backend/app/copilot/context.py` — GraphContextService
- `backend/app/copilot/models.py` — CopilotConversation + CopilotMessage SQLAlchemy models
- `backend/app/copilot/conversation.py` — ConversationService CRUD
- `backend/migrations/versions/016_copilot_conversations.py` — Alembic migration
- `backend/tests/test_graph_context.py` — unit tests for GraphContextService
- `backend/tests/test_conversation_service.py` — unit tests for ConversationService

**Modified files:**
- `backend/app/copilot/service.py` — add `graph_context` parameter to `_build_system_prompt()`
- `backend/app/copilot/schemas.py` — add `active_object_iri` to `CopilotChatRequest`
- `backend/app/api/copilot.py` — wire graph context into chat endpoint, add conversation CRUD endpoints, save messages
- `frontend/static/js/copilot.js` — track active object IRI, send with requests, conversation selector UI, load/save messages from backend
- `frontend/static/css/copilot.css` — styles for conversation selector header
- `backend/app/templates/browser/workspace.html` — possibly add conversation header HTML (or build entirely in JS)

### Constraints and Gotchas

1. **Token budget stacking:** Schema context already uses ~4000 tokens. Graph context should use a separate budget (default 2000). Total system prompt stays under typical context limits. The copilot endpoint should log total system prompt size for monitoring.

2. **Graph context for non-object tabs:** When the active panel is a view tab (kanban, table, etc.) or no tab is active, `active_object_iri` will be null. Graph context injection should gracefully skip — no error, just no `## Current Context` section in the prompt.

3. **Large neighborhoods:** A Project with 50 linked objects could produce thousands of characters. The serializer must truncate at the token budget. Prioritize: (a) the focused object's own literal properties first, (b) outbound edges, (c) inbound edges. Truncate inbound edges first if over budget.

4. **Label resolution is async:** `LabelService.resolve_batch()` is async and hits the triplestore. For a 50-edge neighborhood, that's 50+ IRIs to resolve. The batch query handles this in a single SPARQL call, so it's efficient, but it's still an additional roundtrip per chat request.

5. **Conversation auto-title:** Auto-generate title from the first user message (truncated to 50 chars). The title appears in the conversation list. Users shouldn't need to name conversations manually.

6. **Migration numbering:** Next migration is 016 (after 015_lint_filters.py).

7. **SSE event for conversation_id:** After auto-creating a conversation on the first message, the backend should emit a custom SSE event `event: conversation_created` with `{conversation_id, title}` so the frontend knows to store the ID for subsequent messages. This avoids a separate roundtrip.

### Verification Approach

- **Unit tests for GraphContextService:** Mock triplestore returns, verify serialized output format, verify token budget truncation, verify empty neighborhood handling.
- **Unit tests for ConversationService:** CRUD operations against an in-memory SQLite database (same pattern as existing test fixtures).
- **Integration check:** Import verification for all new modules, endpoint existence checks, migration validity check.
- **Structural verification script:** File existence, import chains, endpoint registration, migration file present.
