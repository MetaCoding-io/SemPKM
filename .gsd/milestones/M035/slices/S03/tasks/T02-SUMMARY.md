---
id: T02
parent: S03
milestone: M035
provides:
  - Persona selector dropdown in copilot header with activate-on-click
  - persona_id sent with every chat request body
  - Object creation instructions in LLM system prompt
  - create_object JSON block detection in SSE stream with custom event emission
  - Confirmation card UI with type, properties, Create/Cancel buttons
  - Create button dispatches to POST /api/commands with object.create payload
  - Success state shows created object as clickable pill link
  - Full CSS for persona selector and create-object card
key_files:
  - frontend/static/js/copilot.js
  - frontend/static/css/copilot.css
  - backend/app/copilot/service.py
  - backend/app/api/copilot.py
key_decisions:
  - Persona selector placed between title and new-chat button using insertBefore; dropdown anchored right to avoid overflow
  - Create object instructions in system prompt use double-braced JSON example to avoid f-string interpolation conflicts
  - JSON fence detection reuses the same _FENCE_CLOSE regex as SPARQL detection; only blocks with "action":"create_object" are emitted
  - Confirmation card reuses copilot-approval-btn styles for Create/Cancel buttons — consistent look, no new button classes needed
  - Label auto-populated as dcterms:title in command payload when not already present in properties
patterns_established:
  - _detect_create_object_blocks() follows identical structure to _detect_sparql_blocks() — scan for fence open, find close, parse content, filter by action type
  - _iriLocalName() utility extracts local name from IRI using hash/slash/colon fallback — reusable for any IRI display
observability_surfaces:
  - "copilot.chat.create_object_detected" log with type and property keys
  - "copilot.chat.create_object_parse_error" log with raw content on JSON parse failure
  - "event: create_object" SSE event emitted to frontend with parsed JSON payload
  - Browser console logs persona activation and object creation events
  - Command API errors surfaced directly in confirmation card UI
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Persona Selector UI + Object Creation from Chat

**Added persona selector dropdown to copilot header, create_object JSON detection in SSE stream, and confirmation card with Command API dispatch**

## What Happened

Implemented all 5 steps from the task plan:

1. **Persona selector in copilot.js**: Added `_activePersonaId` and `_personas` state vars. `_loadPersonas()` fetches from `GET /api/copilot/personas` on init, finds the active persona, and calls `_renderPersonaSelector()`. The selector is a compact button (icon + name + chevron) inserted between the conv title and new-chat button. Clicking opens a dropdown listing all personas with radio-style selection and active checkmark. Selecting calls `POST /api/copilot/personas/{id}/activate`, updates local state, and re-renders. `persona_id` is included in every chat request body.

2. **Object creation instructions in system prompt**: Added a full "Object Creation" section to `_build_system_prompt()` in `service.py` after the SPARQL instructions. Tells the LLM to output `{"action": "create_object", "type": "...", "label": "...", "properties": {...}}` inside a ```json fence. Includes 7 rules for correct output formatting.

3. **Create_object SSE detection in copilot.py**: Added `_JSON_FENCE_OPEN` regex and `_detect_create_object_blocks()` function following the same pattern as `_detect_sparql_blocks()`. In `event_stream()`, after SPARQL block detection, scans for complete JSON fences, parses them, filters for `"action": "create_object"`, and emits `event: create_object` SSE with the parsed payload. Parse failures are logged with raw content.

4. **Create_object confirmation card in copilot.js**: Added SSE handler for `create_object` events in `processChunk()`. `_renderCreateObjectCard()` shows: type badge (local name from IRI), property key-value table, Create (primary) and Cancel (secondary) buttons. Create dispatches to `POST /api/commands` with `object.create` command payload. On success, shows green checkmark + clickable pill link to the created object. On error, shows error message in card. Cancel greys out the card.

5. **CSS in copilot.css**: Added persona selector styles (`.copilot-persona-btn`, `.copilot-persona-dropdown`, `.copilot-persona-item-*`) and create-object card styles (`.copilot-create-card`, `.copilot-create-props`, `.copilot-create-success`, `.copilot-create-error`). All follow existing copilot design patterns — same border radius, colors, transitions.

## Verification

- `node --check frontend/static/js/copilot.js` — no syntax errors
- `rg "persona" frontend/static/js/copilot.js | wc -l` → 51 occurrences (≥10 required)
- `rg "create_object" frontend/static/js/copilot.js` — handler present
- `rg "create_object" backend/app/api/copilot.py` — SSE emission present (9 matches)
- `rg "create_object" backend/app/copilot/service.py` — instructions in system prompt
- `rg "copilot-persona" frontend/static/css/copilot.css` — 16 style rules present
- `rg "copilot-create" frontend/static/css/copilot.css` — 14 style rules present
- `test_ai_personas.py`: 33/33 passed
- `test_copilot_service.py`: 48/48 passed (S01 regression clean)
- `test_conversation_service.py`: 22/22 passed (S02 regression clean)
- `test_ai_personas.py -k "reject"`: 2/2 passed (failure-path)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check frontend/static/js/copilot.js` | 0 | ✅ pass | <1s |
| 2 | `rg "persona" frontend/static/js/copilot.js \| wc -l` | 0 | ✅ pass (51) | <1s |
| 3 | `rg "create_object" frontend/static/js/copilot.js` | 0 | ✅ pass | <1s |
| 4 | `rg "create_object" backend/app/api/copilot.py` | 0 | ✅ pass | <1s |
| 5 | `rg "create_object" backend/app/copilot/service.py` | 0 | ✅ pass | <1s |
| 6 | `rg "copilot-persona" frontend/static/css/copilot.css` | 0 | ✅ pass | <1s |
| 7 | `rg "copilot-create" frontend/static/css/copilot.css` | 0 | ✅ pass | <1s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v` | 0 | ✅ pass (33/33) | 1.03s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass (48/48) | 0.36s |
| 10 | `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` | 0 | ✅ pass (22/22) | 0.64s |
| 11 | `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v -k "reject"` | 0 | ✅ pass (2/2) | 0.47s |

## Diagnostics

- `GET /api/copilot/personas` — list personas with is_active flag for UI state
- `POST /api/copilot/personas/{id}/activate` — switch active persona
- Log key `copilot.chat.create_object_detected` — type and property keys when JSON block found
- Log key `copilot.chat.create_object_parse_error` — raw content on parse failure
- Browser console: `copilot: persona activated id=..., name=...` on switch
- Browser console: `copilot: object created iri=...` on successful Command API dispatch
- Command API errors rendered directly in `.copilot-create-error` card element

## Deviations

- Added a `label` field to the create_object JSON schema beyond just type+properties — gives the LLM a way to specify a human-readable name that gets set as `dcterms:title` on the created object.
- The `_iriLocalName()` utility function was added as a general helper, not planned but necessary for displaying readable type names and property keys from full IRIs.

## Known Issues

- T03 (`test_object_creation_chat.py`) and `verify-s03.sh` not yet written — those are the next task's responsibility.

## Files Created/Modified

- `frontend/static/js/copilot.js` — added persona state vars, _loadPersonas(), _renderPersonaSelector(), _togglePersonaDropdown(), _activatePersona(), persona_id in chat request, create_object SSE handler, _renderCreateObjectCard(), _handleCreateObject(), _handleCancelCreate(), _iriLocalName()
- `frontend/static/css/copilot.css` — added persona selector styles (16 rules) and create-object card styles (14 rules)
- `backend/app/copilot/service.py` — added object creation instructions section to _build_system_prompt()
- `backend/app/api/copilot.py` — added _JSON_FENCE_OPEN regex, _detect_create_object_blocks() helper, create_object SSE emission in event_stream()
- `.gsd/milestones/M035/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight requirement
