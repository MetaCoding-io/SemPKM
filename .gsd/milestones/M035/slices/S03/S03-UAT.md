# S03 UAT: AI Personas & Object Creation from Chat

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm)
- LLM configured in Settings (or mock LLM endpoint)
- User logged in to workspace

---

## Test 1: Persona List Loads on Copilot Open

1. Open the AI COPILOT tab in the workspace
2. Observe the copilot header area

**Expected:** A persona selector button appears in the header between the conversation title and the new-chat button. It shows the active persona icon and name (default: "🤖 General Assistant"). No console errors on load.

---

## Test 2: Persona Selector Dropdown

1. Click the persona selector button in the copilot header
2. Observe the dropdown that appears

**Expected:** Dropdown lists 4 personas with icons:
- 🤖 General Assistant (checkmark indicating active)
- 🔬 Research Assistant
- 📋 Project Manager
- ✍️ Writing Coach

---

## Test 3: Switch Active Persona

1. Open the persona selector dropdown
2. Click "🔬 Research Assistant"
3. Observe the selector button and dropdown state

**Expected:** Selector button updates to show "🔬 Research Assistant". Reopening the dropdown shows the checkmark next to Research Assistant. The switch persists — reloading the page and reopening the copilot still shows Research Assistant as active.

---

## Test 4: Persona Affects System Prompt

1. Activate "Research Assistant" persona
2. Ask the copilot: "Tell me about my projects"
3. Activate "Writing Coach" persona
4. Ask the same question: "Tell me about my projects"

**Expected:** Research Assistant response emphasizes citations, evidence, and structured analysis. Writing Coach response emphasizes clarity, tone, and narrative structure. The behavioral difference is perceptible (tone, structure, framing differ).

---

## Test 5: Object Creation — Happy Path

1. Activate "General Assistant" persona
2. Type: "Create a task called Review Q1 Goals, due next Friday"
3. Observe the copilot response stream

**Expected:** The LLM response includes a JSON block with `{"action": "create_object", ...}`. The copilot renders a confirmation card showing:
- Type badge (e.g., "Task")
- Property table listing the task name and due date
- "Create" (primary) and "Cancel" (secondary) buttons

4. Click "Create"

**Expected:** The card updates to show a success state with a green checkmark and a clickable pill link to the created object. Clicking the pill link opens the object in a new workspace tab.

---

## Test 6: Object Creation — Cancel

1. Ask the copilot to create an object (e.g., "Create a note called Test Note")
2. When the confirmation card appears, click "Cancel"

**Expected:** The card is greyed out / dismissed. No object is created. No entry appears in the object browser for "Test Note".

---

## Test 7: Object Creation — Command API Error

1. Ask the copilot to create an object with an invalid type IRI (e.g., manually craft a scenario where the type doesn't match an installed model)

**Expected:** The confirmation card shows an error message from the Command API (red text) rather than silently failing. The error is human-readable.

---

## Test 8: Persona REST API — List

1. Open browser devtools Network tab
2. Open the copilot tab

**Expected:** `GET /api/copilot/personas` returns 200 with JSON array of 4 personas. Each has: id, name, icon, system_prompt_template, is_builtin (true), is_active (one true), temperature, created_at, updated_at.

---

## Test 9: Persona REST API — Built-in Protection

1. Via devtools or curl, send `DELETE /api/copilot/personas/{builtin_id}` for a built-in persona

**Expected:** Returns 400 with error message indicating built-in personas cannot be deleted. The persona remains in the list.

2. Send `PUT /api/copilot/personas/{builtin_id}` with `{"name": "Custom Name"}`

**Expected:** Returns 400 with error message indicating built-in personas cannot be modified.

---

## Test 10: Persona Persists Across Chat Requests

1. Switch to "📋 Project Manager" persona
2. Send a chat message — observe the persona_id is included in the request body (Network tab)
3. Switch conversations (new chat or select existing)
4. Send another message

**Expected:** The persona_id field is present in every `POST /api/copilot/chat` request body. The active persona persists across conversations within the same session.

---

## Test 11: Persona Selector with Multiple Users (Isolation)

1. Log in as User A — check personas list
2. Log in as User B — check personas list

**Expected:** Each user has their own set of 4 built-in personas. Activating a persona as User A does not affect User B's active persona.

---

## Edge Cases

### E1: Copilot Degrades Without LLM Config
1. Remove LLM configuration from Settings
2. Open copilot, observe persona selector still loads
3. Send a message — expect graceful error about LLM not configured, not a crash

### E2: Malformed JSON in LLM Response
If the LLM produces a JSON fence with invalid JSON, the copilot should log the parse error and continue rendering the rest of the response as normal text — no confirmation card appears, no crash.

### E3: Rapid Persona Switching
Click through all 4 personas quickly in succession. The selector should settle on the last-clicked persona without race conditions or stale state.
