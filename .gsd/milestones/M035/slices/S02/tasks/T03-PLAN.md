---
estimated_steps: 5
estimated_files: 4
skills_used:
  - frontend-design
  - best-practices
---

# T03: Frontend conversation selector, active-object tracking, and slice verification

**Slice:** S02 — Graph Context Injection & Conversation Persistence
**Milestone:** M035

## Description

Connect the two backend features (graph context injection from T01, conversation persistence from T02) to the copilot frontend. Track the active object IRI via the `sempkm:tab-activated` custom event and send it with each chat request. Build a conversation selector header bar for creating, switching, and deleting conversation threads. Integrate `_messageThread` with the backend persistence layer. Write the slice-level verification script.

The existing `copilot.js` uses `_messageThread` as an in-memory array and sends `{messages, conversation_id?, model?}` to `POST /api/copilot/chat`. T02 added backend persistence and a `conversation_created` SSE event. This task connects those pieces to the UI.

## Steps

1. **Add active-object IRI tracking** to `copilot.js`:
   - Add module-level `var _activeObjectIri = null;`
   - In `initCopilotChat()`, add a `document.addEventListener('sempkm:tab-activated', ...)` listener
   - When `detail.isObjectTab` is true, set `_activeObjectIri = detail.tabId` (the panel ID is the object IRI for object tabs)
   - When `detail.isObjectTab` is false, set `_activeObjectIri = null`
   - In `_streamCopilotResponse()`, include `active_object_iri: _activeObjectIri` in the fetch body alongside `messages` and `conversation_id`

2. **Add conversation state variables and init logic**:
   - Add `var _currentConversationId = null;` and `var _conversations = [];`
   - In `initCopilotChat()`, call `_loadConversations()` which fetches `GET /api/copilot/conversations`
   - If conversations exist, load the most recent one (first in the list, already sorted by updated_at DESC) via `GET /api/copilot/conversations/{id}` and populate `_messageThread` from the response messages
   - If no conversations exist, show the existing empty state
   - Render the conversation selector header

3. **Build conversation selector header** (HTML built in JS, inserted above `#copilot-messages`):
   - Layout: `[☰ dropdown btn] [conversation title text] [+ New Chat btn]`
   - Dropdown: clicking ☰ opens a list of conversations (title + relative time), clicking one calls `_switchConversation(id)`
   - New Chat: clears `_messageThread`, creates a new conversation via POST, updates `_currentConversationId`, clears messages area, shows empty state
   - Delete: each conversation in the dropdown has a small ✕ delete button, calls `DELETE /api/copilot/conversations/{id}`, removes from list, switches to next or shows empty
   - Style the header in `copilot.css`: compact bar, same color scheme as the panel, border-bottom separator

4. **Wire conversation persistence into chat flow**:
   - In `_streamCopilotResponse()`, include `conversation_id: _currentConversationId` in the fetch body
   - Handle the `conversation_created` SSE event: parse `{conversation_id, title}`, set `_currentConversationId = data.conversation_id`, update the conversation selector title text, add to `_conversations` array
   - After stream completes (in `_finishStream`), the backend already saves messages (T02) — no additional save call needed from frontend
   - When loading a conversation, re-render all messages from the loaded thread using existing `_renderMessage()`

5. **Write slice verification script** `.gsd/milestones/M035/slices/S02/verify-s02.sh`:
   - Check file existence: `context.py`, `models.py`, `conversation.py`, migration 016, both test files, verify-s02.sh itself
   - Check imports: `from app.copilot.context import GraphContextService`, `from app.copilot.models import CopilotConversation, CopilotMessage`, `from app.copilot.conversation import ConversationService`
   - Check endpoint registration: grep copilot.py for `"/conversations"` routes (GET, POST, DELETE)
   - Check migration: verify `016_copilot_conversations.py` contains `copilot_conversations` and `copilot_messages`
   - Check schema field: grep schemas.py for `active_object_iri`
   - Check system prompt: grep service.py for `graph_context`
   - Check frontend wiring: grep copilot.js for `_activeObjectIri`, `_currentConversationId`, `conversation_created`, `sempkm:tab-activated`
   - Each check prints PASS/FAIL, script exits 0 only if all pass

## Must-Haves

- [ ] Active object IRI tracked via `sempkm:tab-activated` event and sent with chat requests
- [ ] Conversation selector header rendered with title, new chat button, and conversation list dropdown
- [ ] Switching conversations loads messages from backend and re-renders
- [ ] New Chat creates a conversation, clears messages, shows empty state
- [ ] Delete removes conversation and switches to next
- [ ] `conversation_created` SSE event handled — stores conversation ID for subsequent messages
- [ ] Verification script checks all structural requirements

## Verification

- `bash .gsd/milestones/M035/slices/S02/verify-s02.sh` — all checks pass
- `grep -q '_activeObjectIri' frontend/static/js/copilot.js` — active object tracking present
- `grep -q '_currentConversationId' frontend/static/js/copilot.js` — conversation state present
- `grep -q 'conversation_created' frontend/static/js/copilot.js` — SSE event handler present

## Inputs

- `frontend/static/js/copilot.js` — existing chat module with `_messageThread`, `_streamCopilotResponse()`, `_renderMessage()`, `_finishStream()`, `initCopilotChat()`
- `frontend/static/css/copilot.css` — existing copilot styles
- `frontend/static/js/workspace-layout.js` — reference for `sempkm:tab-activated` event shape (`detail: {tabId, groupId, isObjectTab}`)
- `backend/app/api/copilot.py` — T02's conversation REST endpoints and `conversation_created` SSE event format
- `backend/app/copilot/schemas.py` — T01's `active_object_iri` field on CopilotChatRequest

## Observability Impact

- **Frontend console logging**: `copilot: conversations loaded (count=N)`, `copilot: switched conversation (id=X)`, `copilot: new chat created`, `copilot: conversation deleted (id=X)`, `copilot: active object tracking (iri=X|null)`
- **Inspection surface**: The conversation selector dropdown displays all threads with titles and relative timestamps — visible state of persistence without needing dev tools
- **Failure visibility**: Network fetch errors for conversation CRUD are caught and logged to console; the UI degrades gracefully (empty state shown, chat still works without persistence)
- **Active object tracking**: `_activeObjectIri` value is included in every chat POST body — backend logs show `copilot.chat.graph_context` or `copilot.chat.graph_context_error` confirming the frontend→backend wiring

## Expected Output

- `frontend/static/js/copilot.js` — modified with active-object tracking, conversation selector, persistence integration
- `frontend/static/css/copilot.css` — modified with conversation selector styles
- `.gsd/milestones/M035/slices/S02/verify-s02.sh` — slice verification script
