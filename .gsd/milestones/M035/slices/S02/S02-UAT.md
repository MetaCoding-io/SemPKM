# S02: Graph Context Injection & Conversation Persistence — UAT

**Milestone:** M035
**Written:** 2026-03-23

## UAT Type

- UAT mode: mixed (artifact-driven for backend, live-runtime for frontend)
- Why this mode is sufficient: Backend logic is fully covered by 35 unit tests (13 graph context + 22 conversation). Frontend wiring and visual behavior require a running Docker stack with real triplestore data.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- basic-pkm Mental Model installed (provides Project, Task, Note types with seed data)
- At least one Project object exists with linked Tasks/Notes (seed data or manually created)
- User logged in to workspace at `http://localhost:3901/browser/`
- LLM provider configured in Settings > AI (Ollama or cloud endpoint)

## Smoke Test

1. Open the AI COPILOT tab in the bottom panel (Ctrl+J, click "AI COPILOT" tab)
2. Type "Hello" and press Enter
3. **Expected:** Response streams in. A conversation header bar appears above the messages with a title derived from your message. The conversation persists — refresh the page, reopen copilot, and the thread should reload.

## Test Cases

### 1. Graph context injection — object tab active

1. Open a Project object by clicking it in the explorer sidebar
2. Confirm the object tab is active (tab title shows the project name)
3. Open the AI COPILOT tab
4. Type "Summarize this project" and press Enter
5. **Expected:** The copilot response references the project's actual name and mentions linked tasks or notes by name. Backend log shows `copilot.context.neighborhood` with a positive triple count. The response is noticeably more specific than asking the same question without an active object.

### 2. Graph context injection — no active object

1. Click a non-object tab (e.g., a View tab or the explorer itself)
2. Open the AI COPILOT tab
3. Type "What do you know about my current context?" and press Enter
4. **Expected:** The copilot responds without object-specific context — no error, no crash. Backend log does NOT show `copilot.context.neighborhood`. The system prompt includes schema context but no graph context section.

### 3. Conversation auto-creation

1. Open the AI COPILOT tab with no existing conversations (or click the "+" new chat button)
2. Type a message and press Enter
3. **Expected:** The conversation header shows a title derived from your message (truncated to ~50 chars if long). The backend emits `copilot.conversation.created` log entry. The SSE stream includes a `conversation_created` event before the LLM response data.

### 4. Conversation persistence across page reload

1. Have an active conversation with at least 3 messages (user + assistant exchanges)
2. Note the conversation title and last message content
3. Reload the page (F5 or Ctrl+R)
4. Reopen the AI COPILOT tab
5. **Expected:** The previous conversation loads automatically. All messages are present with correct roles (user/assistant), correct content, and correct ordering. The conversation title matches what was shown before reload.

### 5. Conversation switching

1. Have at least 2 conversations (create via "+" new chat button)
2. Click the ☰ menu button in the conversation header
3. **Expected:** A dropdown shows all conversations with titles and relative timestamps (e.g., "2 min ago")
4. Click a different conversation than the currently active one
5. **Expected:** The message area clears and loads the selected conversation's full history. The header title updates.

### 6. Conversation deletion

1. Have at least 2 conversations
2. Open the conversation dropdown (☰ button)
3. Hover over a non-active conversation
4. **Expected:** A ✕ delete button appears on hover
5. Click the ✕ button
6. **Expected:** The conversation disappears from the dropdown. If the deleted conversation was the active one, the UI switches to the next available conversation or shows an empty state.

### 7. REST API — conversation list

1. In a browser tab or via curl, request `GET /api/copilot/conversations` (with auth cookie)
2. **Expected:** JSON array of conversations with `id`, `title`, `created_at`, `updated_at` fields. Conversations are ordered by most recent first. Only the current user's conversations appear.

### 8. REST API — conversation detail

1. Get a conversation ID from the list endpoint
2. Request `GET /api/copilot/conversations/{id}`
3. **Expected:** JSON object with conversation metadata and a `messages` array. Each message has `role` (user/assistant), `content`, and `created_at`. Messages are ordered chronologically.

## Edge Cases

### Long conversation thread

1. Have a conversation with 20+ message exchanges
2. Open the copilot tab and send another message
3. **Expected:** All history is loaded and sent with the request. The LLM still responds (may be slow due to large context). No truncation or loss of messages.

### Rapid message sending

1. Send a message, then immediately send another before the first response completes
2. **Expected:** The UI does not crash. The second message may wait for the first stream to complete. Both messages appear in the correct order.

### Active object changes during conversation

1. Start chatting about one Project
2. Switch to a different object tab (a Note or Task)
3. Send another message to the copilot
4. **Expected:** The copilot's context switches to the newly active object. The response should reference the new object's properties, not the previous one.

### Token budget truncation

1. View an object with many linked objects (>20 edges)
2. Ask the copilot to summarize it
3. **Expected:** Backend log shows `copilot.context.truncated` indicating the budget was hit. The copilot still responds with a useful summary — it just may not mention all linked objects.

## Failure Signals

- "Summarize this project" returns a generic answer with no specific object names → graph context not injected
- Page reload shows empty chat → conversation persistence broken
- Conversation dropdown is always empty → list endpoint failing or frontend not fetching
- Backend error `copilot.chat.graph_context_error` → triplestore query or label resolution failing
- `copilot.chat.message_save_error` in logs → conversation write path broken
- Auto-title never appears (conversation stays "New Conversation") → auto-title timing or check order wrong

## Requirements Proved By This UAT

- AI-04 (graph context injection) — test cases 1, 2, and the truncation edge case prove context flows from triplestore through service into LLM prompt
- AI-05 (conversation persistence) — test cases 3, 4, 5, 6, 7, 8 prove conversations survive reloads and support CRUD operations

## Not Proven By This UAT

- AI-01 through AI-03 (copilot chat, SPARQL generation, query approval) — proved by S01
- AI-06 (AI personas) — deferred to S03
- AI-07 (object creation from chat) — deferred to S03
- AI-08 through AI-10 (test harness tiers) — deferred to S04
- Long-thread summarization / context compression — not implemented (known limitation)

## Notes for Tester

- Graph context quality depends on the installed model's SHACL shapes and seed data. With basic-pkm, Projects with linked Tasks and Notes provide the best test surface.
- The copilot needs an LLM backend configured. Without one, chat requests will fail (expected). The conversation CRUD and graph context injection can still be verified via API and logs.
- Auto-titling only fires on the first user message in a conversation. Subsequent messages don't change the title.
- The conversation dropdown's delete button appears only on hover — check with mouse movement, not just visual inspection.
