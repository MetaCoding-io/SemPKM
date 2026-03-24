---
estimated_steps: 5
estimated_files: 4
skills_used:
  - frontend-design
  - review
---

# T02: Persona Selector UI + Object Creation from Chat

**Slice:** S03 — AI Personas & Object Creation from Chat
**Milestone:** M035

## Description

Wire the frontend persona selector into the copilot header bar and implement the full object creation flow: system prompt instructions tell the LLM to output structured JSON for object creation, the backend detects it in the SSE stream and emits a custom event, the frontend renders a confirmation card, and user approval dispatches to the Command API.

## Steps

1. **Persona selector in copilot.js**: Add `_activePersonaId` and `_personas` state vars. On init (after `_loadConversations()`), call `_loadPersonas()` → `GET /api/copilot/personas`. Create `_renderPersonaSelector()` — a dropdown button inserted into the `.copilot-conv-header` between the conv title and new-chat button. Shows active persona icon + name. Clicking opens a dropdown listing all personas with radio-style selection. Selecting calls `POST /api/copilot/personas/{id}/activate`, updates `_activePersonaId`, closes dropdown. Include `_activePersonaId` as `persona_id` in the chat request body (in `_streamCopilotResponse()` fetch call).

2. **Object creation instructions in system prompt**: In `backend/app/copilot/service.py`, add object creation instructions to `_build_system_prompt()` (after the existing SPARQL instructions). Tell the LLM: when the user asks to create an object, output a JSON block with `{"action": "create_object", "type": "<type_iri>", "properties": {"predicate": "value"}}` inside a ` ```json ` code fence. The system will show a confirmation card.

3. **Create_object SSE detection in copilot.py**: In the `event_stream()` generator within `copilot_chat()`, after the SPARQL block detection logic, add detection for create_object JSON blocks. Scan `accumulated_content` for ` ```json ` code fences containing `"action": "create_object"`. When found, parse the JSON, emit `event: create_object` SSE with the parsed payload. Log `copilot.chat.create_object_detected`. Add a helper function `_detect_create_object_blocks()` following the same pattern as `_detect_sparql_blocks()`.

4. **Create_object confirmation card in copilot.js**: In the SSE parser (inside `processChunk()`), handle `event: create_object` events — call `_renderCreateObjectCard(data, assistantEl)`. The card shows: type label (from data.type), property list as key-value rows, "Create" button (primary) and "Cancel" button (secondary). Create button sends `POST /api/commands` with body `{"command": "object.create", "params": {"type": data.type, "properties": data.properties}}`. On 200 response, show success state with created object IRI as a clickable pill link. On error, show error message in card. Cancel greys out the card. Add a system message to the thread: "Created [Type]: [[iri|label]]".

5. **CSS for persona selector and create-object card in copilot.css**: Persona selector: `.copilot-persona-btn` (compact button with icon+name), `.copilot-persona-dropdown` (positioned below button, max-height with scroll, similar style to conversation dropdown). Create-object card: `.copilot-create-card` (similar to `.copilot-approval-card` — bordered card within assistant message), `.copilot-create-props` (key-value table), `.copilot-create-actions` (Create/Cancel buttons), `.copilot-create-success` (green checkmark + pill link).

## Must-Haves

- [ ] Persona selector renders in copilot header between title and new-chat button
- [ ] Switching persona calls the activate endpoint and updates local state
- [ ] `persona_id` sent with every chat request
- [ ] System prompt includes object creation instructions
- [ ] `event: create_object` SSE emitted when JSON block detected in LLM response
- [ ] Confirmation card shows type + properties + Create/Cancel
- [ ] Create button dispatches to `POST /api/commands` with correct payload
- [ ] Success state shows created object as clickable pill

## Verification

- `node --check frontend/static/js/copilot.js` — no syntax errors
- `rg "persona" frontend/static/js/copilot.js | wc -l` — at least 10 occurrences (selector logic)
- `rg "create_object" frontend/static/js/copilot.js` — handler present
- `rg "create_object" backend/app/api/copilot.py` — SSE emission present
- `rg "create_object" backend/app/copilot/service.py` — instructions in system prompt
- `rg "copilot-persona" frontend/static/css/copilot.css` — styles present
- `rg "copilot-create" frontend/static/css/copilot.css` — card styles present

## Inputs

- `frontend/static/js/copilot.js` — existing copilot UI module (SSE parser, header rendering, message rendering)
- `frontend/static/css/copilot.css` — existing copilot styles (conversation header, approval card patterns to follow)
- `backend/app/copilot/service.py` — existing `_build_system_prompt()` (add creation instructions)
- `backend/app/api/copilot.py` — existing `copilot_chat()` SSE stream (add create_object detection)
- `backend/app/copilot/personas.py` — T01 output: AIPersonaService for persona list/activate calls
- `backend/app/copilot/schemas.py` — T01 output: CopilotChatRequest with persona_id field

## Expected Output

- `frontend/static/js/copilot.js` — modified: persona selector, create_object confirmation card, Command API dispatch
- `frontend/static/css/copilot.css` — modified: persona selector styles, create-object card styles
- `backend/app/copilot/service.py` — modified: object creation instructions in system prompt
- `backend/app/api/copilot.py` — modified: create_object JSON detection + SSE event emission in stream
