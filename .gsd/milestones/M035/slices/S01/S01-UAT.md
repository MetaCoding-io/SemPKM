# S01: Copilot Chat with SPARQL Generation — UAT

**Milestone:** M035
**Written:** 2026-03-23

## UAT Type

- UAT mode: mixed (artifact-driven unit tests + live-runtime copilot interaction)
- Why this mode is sufficient: Unit tests prove service logic deterministically. Live runtime tests prove the chat UI, SSE streaming, and SPARQL execution work against a real triplestore with real LLM.

## Preconditions

1. Docker stack running: `docker compose up -d` from project root
2. Basic-PKM model installed (provides Projects, Tasks, Notes, Concepts types)
3. At least 2-3 seed objects exist (e.g., a Project and a Task linked by an edge)
4. LLM provider configured in Settings (OpenAI, Anthropic, or Ollama — any model that can generate SPARQL)
5. User logged in to the workspace at `http://localhost:3901/browser/`

## Smoke Test

1. Open the workspace. Click the **AI COPILOT** tab in the bottom panel (or press Ctrl+J and select it).
2. **Expected:** Chat interface appears with an empty-state greeting message, a text input area, and a send button.

## Test Cases

### 1. LLM Not Configured State

**Precondition:** No LLM API key configured in Settings.

1. Open the AI COPILOT tab.
2. **Expected:** A card appears saying "AI features require an LLM connection" (or similar) with a link to Settings.
3. The text input should be disabled or the send button should indicate LLM is unavailable.

### 2. Basic Chat Streaming

**Precondition:** LLM configured and operational.

1. Open the AI COPILOT tab.
2. Type "Hello, what can you help me with?" and press Enter (or click Send).
3. **Expected:** A typing indicator (animated dots) appears briefly, then the assistant's response streams in token-by-token. The response mentions SPARQL, querying the knowledge graph, or similar copilot capabilities. Message appears left-aligned with markdown formatting.

### 3. SPARQL Generation and Approval

1. Type "How many projects do I have?" and send.
2. **Expected:** The response includes a SPARQL query displayed in a syntax-highlighted code block inside an approval card. The card shows Approve, Edit, and Reject buttons. The query should contain `SELECT` and reference project-related predicates.
3. Click **Approve**.
4. **Expected:** A loading spinner appears briefly. The query executes against the triplestore. A prose answer appears below the card (e.g., "You have 3 projects") with the count and possibly clickable object links.

### 4. SPARQL Query Rejection

1. Type "List all my tasks" and send.
2. **Expected:** A SPARQL query approval card appears.
3. Click **Reject**.
4. **Expected:** The card is greyed out. A "Query cancelled" message appears. No query is executed.

### 5. SPARQL Query Editing

1. Type "Show me all notes" and send.
2. **Expected:** A SPARQL query approval card appears.
3. Click **Edit**.
4. **Expected:** The query block is replaced by an editable textarea pre-filled with the generated query. "Run Edited Query" and "Cancel" buttons appear.
5. Modify the query slightly (e.g., add `LIMIT 5` at the end) and click **Run Edited Query**.
6. **Expected:** The edited query is validated and executed. Results appear as prose in the chat thread.

### 6. IRI Object Pill Links

1. Type "List my projects" and send. Approve the generated SPARQL query.
2. **Expected:** Results include clickable object pills (styled links showing object labels). 
3. Click one of the object pills.
4. **Expected:** The corresponding object opens in a new workspace tab (via `window.openTab()`).

### 7. Markdown Rendering in Responses

1. Type "Explain what a SPARQL SELECT query does" and send.
2. **Expected:** The response renders with proper markdown formatting — bold text, inline code, possibly bullet points or headings. Code snippets render in monospace. No raw markdown syntax visible.

### 8. Shift+Enter for Multiline Input

1. Click in the chat input textarea.
2. Type "First line", press **Shift+Enter**, then type "Second line".
3. **Expected:** The textarea grows to accommodate both lines. The message is NOT sent on Shift+Enter.
4. Press **Enter** (without Shift).
5. **Expected:** The full multiline message is sent.

### 9. Self-Correction Retry on Failure

**Note:** This is harder to trigger naturally. May require an LLM that generates slightly wrong SPARQL.

1. Ask a question that might produce invalid SPARQL (e.g., "How many items have a priority of high?" — assumes a property that may not exist exactly as the LLM guesses).
2. If the query fails on approval (Approve → error), observe:
3. **Expected:** An error message appears on the card with Retry, Edit, and Dismiss buttons. A system message shows "Self-correcting… attempt N of 3".
4. Click **Retry**.
5. **Expected:** The LLM generates a corrected query. If successful, the new query replaces the old one on the card. If it fails again after 2 retries, a message indicates retries exhausted and suggests rephrasing.

### 10. Schema Context Verification

1. Ask "What types of objects can I create?" and send.
2. **Expected:** The response mentions the types from the installed model (Project, Task, Note, Concept for basic-PKM). This proves the schema context was injected into the system prompt — the LLM knows about the installed model's types.

## Edge Cases

### Empty Message

1. Click the send button with an empty text input.
2. **Expected:** Nothing happens — the send button is disabled or the message is not sent.

### Rapid Messages

1. Send a message. While the response is still streaming, try to send another message.
2. **Expected:** The send button is disabled during streaming. The second message is blocked until the first response completes.

### Very Long Query Result

1. Ask something that returns many results (e.g., "List all objects" with many seed objects).
2. **Expected:** Results render correctly with scrolling. The chat thread auto-scrolls to show the latest content.

### Tab Switch Persistence

1. Send a message and receive a response.
2. Switch to the SPARQL CONSOLE tab in the bottom panel.
3. Switch back to the AI COPILOT tab.
4. **Expected:** The previous messages are still visible in the thread (in-memory persistence within the session). Note: cross-reload persistence is S02 scope.

## Failure Signals

- **AI COPILOT tab shows "coming in v2.1" placeholder** — workspace.html wasn't updated or copilot.css isn't loaded
- **"Failed to fetch" error in chat** — nginx SSE proxy config missing or copilot_router not wired in main.py
- **No SPARQL approval card appears** — SPARQL detection in the SSE stream isn't working; check backend logs for `copilot.chat.sparql_detected`
- **Approval card shows "Approve" but clicking does nothing** — /api/copilot/approve endpoint not reachable; check nginx config
- **Object pills are plain text, not clickable** — IRI pill conversion failed; check browser console for errors in `_convertIriPills`
- **Markdown renders as raw text** — `globalThis.marked` not available; check that the marked.js vendor script loads

## Requirements Proved By This UAT

- AI-01 — copilot chat UI renders streaming messages with markdown and object pill links (tests 2, 3, 6, 7)
- AI-02 — SPARQL generation produces valid queries from natural language questions (tests 3, 10)
- AI-03 — query approval flow (show → approve/edit/reject) works end-to-end (tests 3, 4, 5)
- AI-02 (partial) — self-correction loop retries failed SPARQL at least once with error feedback (test 9)

## Not Proven By This UAT

- AI-04 (graph context injection) — S02 scope; copilot does not yet include active object's data neighborhood
- AI-05 (conversation persistence) — S02 scope; messages are in-memory only, lost on reload
- AI-06 (AI personas) — S03 scope; no persona selector yet
- AI-07 (object creation from chat) — S03 scope; copilot cannot create objects yet
- AI-08, AI-09, AI-10 (test harness tiers) — S04 scope; only unit tests exist so far

## Notes for Tester

- The copilot's SPARQL quality depends entirely on the connected LLM. GPT-4 and Claude produce good SPARQL; smaller models (Llama 7B) may struggle with correct predicate names.
- If the LLM is slow, the streaming display and typing indicator are more visible — useful for testing the UX.
- The schema context in the system prompt is truncated at ~4000 tokens. With only basic-PKM installed, this is well within budget.
- The pre-existing `test_well_known_includes_ai_capabilities` test failure is unrelated to this slice — ignore it.
