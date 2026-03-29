# S02: Copilot Bottom Panel — Z-Index Fix — UAT

**Milestone:** M046
**Written:** 2026-03-29T01:52:08.124Z

## UAT: Copilot Bottom Panel — Z-Index Fix

### Preconditions
- Docker test stack running at localhost:3901
- Mock LLM API server running
- basic-pkm model installed
- Authenticated as admin user

### Test 1: AI COPILOT tab opens from collapsed bottom panel
1. Navigate to `/browser/`
2. Collapse the bottom panel via the toggle button (panel height goes to 0)
3. Click the AI COPILOT tab button in the bottom panel bar
4. **Expected:** Bottom panel auto-opens AND the copilot tab is active with the chat container visible

### Test 2: Editor-empty watermark does not block bottom panel tabs
1. Navigate to `/browser/` with no object tabs open (editor area shows the watermark with "Open an item..." text)
2. Click the AI COPILOT tab button
3. **Expected:** Click reaches the tab button — the copilot container loads. The watermark does not intercept the click.

### Test 3: Basic chat flow
1. Open the AI COPILOT tab
2. Type a message in the chat input and press Enter
3. **Expected:** User message appears in the conversation. Streaming response from mock LLM renders in the assistant message bubble.

### Test 4: SPARQL generation and approval
1. Open the AI COPILOT tab
2. Send a message that triggers SPARQL generation (e.g., "show me all tasks")
3. **Expected:** SPARQL code block renders with an approval button. Clicking approve executes the query.

### Test 5: Conversation persistence
1. Open the AI COPILOT tab, send a message
2. Reload the page
3. Re-open the AI COPILOT tab
4. **Expected:** Previous conversation is listed and messages are preserved.

### Test 6: Persona switching
1. Open the AI COPILOT tab
2. Switch the persona selector to a different persona
3. **Expected:** Persona changes without error. The selected persona persists.

### Test 7: Object creation from chat
1. Open the AI COPILOT tab
2. Send a message that triggers object creation
3. **Expected:** Object is created and confirmed in the chat response.

### Edge Cases
- **Rapid tab switching:** Click AI COPILOT, then Event Log, then AI COPILOT again quickly — copilot should re-render without duplication or errors.
- **Panel toggle during copilot use:** While copilot is active, collapse and re-expand the bottom panel — copilot content should remain intact.
