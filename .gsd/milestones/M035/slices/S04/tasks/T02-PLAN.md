---
estimated_steps: 5
estimated_files: 2
skills_used: []
---

# T02: Copilot E2E Playwright tests

**Slice:** S04 — LLM Test Harness & E2E Integration
**Milestone:** M035

## Description

Write Playwright E2E tests that exercise the full copilot stack against the Docker test stack with the mock-llm service. Tests configure the LLM to point at `http://mock-llm:8080` via the existing `PUT /browser/llm/config` API, then interact with the copilot UI to verify chat streaming, SPARQL generation + approval, conversation persistence, persona switching, and object creation.

The copilot tab is lazy-loaded — tests must click the AI COPILOT panel tab to activate it. The mock-llm returns deterministic canned responses based on message content, making assertions reliable.

## Steps

1. **Add copilot selectors to `e2e/helpers/selectors.ts`** in a new `copilot` section:
   - `container: '#copilot-container'`
   - `messages: '#copilot-messages'`
   - `input: '#copilot-input'`
   - `sendBtn: '#copilot-send-btn'`
   - `convHeader: '#copilot-conv-header'`
   - `convTitle: '#copilot-conv-title'`
   - `convDropdown: '#copilot-conv-dropdown'`
   - `msgAssistant: '.copilot-msg-assistant'`
   - `msgUser: '.copilot-msg-user'`
   - `approvalCard: '.copilot-approval-card'`
   - `approveBtn: '.copilot-approve-btn'` (verify actual class from `copilot.js`)
   - `personaSelector: '#copilot-persona-selector'`
   - `personaDropdown: '#copilot-persona-dropdown'`
   - `personaItem: '.copilot-persona-item'`
   - `createObjectCard: '.copilot-create-object-card'` (verify from `copilot.js`)
   - `iriPill: '.copilot-iri-pill'`

2. **Create `e2e/tests/46-copilot/copilot.spec.ts`** with test infrastructure:
   - Import from `../../fixtures/auth` (test, expect, BASE_URL)
   - Import `waitForWorkspace`, `waitForIdle` from `../../helpers/wait-for`
   - Import `SEL` from `../../helpers/selectors`
   - `test.describe('Copilot')` block
   - `test.beforeAll` — configure LLM via API:
     ```typescript
     await ownerRequest.put(`${BASE_URL}/browser/llm/config`, { data: { field: 'api_base_url', value: 'http://mock-llm:8080' }});
     await ownerRequest.put(`${BASE_URL}/browser/llm/config`, { data: { field: 'default_model', value: 'test-model' }});
     await ownerRequest.put(`${BASE_URL}/browser/llm/config`, { data: { field: 'api_key', value: 'sk-mock-test-key' }});
     ```
   - `test.afterAll` — clean up LLM config (set all three fields to empty string)
   - Helper: `openCopilotTab(page)` — navigate to `/browser/`, wait for workspace, click the AI COPILOT panel tab (find the tab by text content), wait for `#copilot-container` to appear

3. **Write test: basic chat flow**
   - Open copilot tab
   - Type a generic message in `#copilot-input` and click `#copilot-send-btn`
   - Wait for `.copilot-msg-user` to appear with the sent text
   - Wait for `.copilot-msg-assistant` to appear (streaming response from mock)
   - Assert assistant message contains text (not empty, not error)

4. **Write test: SPARQL generation and approval**
   - Open copilot tab
   - Send "How many projects do I have?"
   - Wait for the approval card to appear (`.copilot-approval-card` or equivalent selector — verify from `copilot.js` source)
   - Verify the card contains SPARQL text (look for `SELECT` text)
   - Click the Approve button
   - Wait for the approval card to show a result state (loading → result)
   - Verify no error is displayed (the query runs against real triplestore)

5. **Write test: conversation persistence**
   - Open copilot tab
   - Send a message and wait for response
   - Note the conversation title from `#copilot-conv-title`
   - Reload the page
   - Open copilot tab again
   - Verify the conversation selector shows the previous conversation (click the conversations menu button, verify a conversation item exists)

6. **Write test: persona switching**
   - Open copilot tab
   - Click the persona selector (`#copilot-persona-selector`)
   - Wait for persona dropdown (`#copilot-persona-dropdown`)
   - Verify at least 2 persona items are listed (`.copilot-persona-item`)
   - Click a non-active persona item
   - Verify the persona selector button text updates to show the new persona name

7. **Write test: object creation from chat**
   - Open copilot tab
   - Send "Please create a task called Review Q1 goals"
   - Wait for the create-object confirmation card to appear
   - Verify the card shows type and label information
   - Click the Create/Confirm button on the card
   - Wait for the card to show success state (a clickable pill link to the created object)

## Must-Haves

- [ ] Copilot selectors added to `SEL` object in `e2e/helpers/selectors.ts`
- [ ] Test configures LLM via API in beforeAll and cleans up in afterAll
- [ ] 5 test cases: basic chat, SPARQL approval, conversation persistence, persona switching, object creation
- [ ] Each test opens the copilot tab by activating the AI COPILOT panel
- [ ] Tests use the auth fixtures (`ownerPage`, `ownerRequest`) from `../../fixtures/auth`

## Verification

- `node -e "require('typescript').createProgram(['e2e/tests/46-copilot/copilot.spec.ts'], {noEmit:true, moduleResolution:2, target:99, module:199, esModuleInterop:true, skipLibCheck:true})"` — no TypeScript errors (or equivalent syntax validation)
- `grep -c "copilot" e2e/helpers/selectors.ts` — returns > 10 (copilot selectors present)
- File `e2e/tests/46-copilot/copilot.spec.ts` exists and contains 5+ `test(` declarations

## Inputs

- `e2e/mock-llm-api/server.py` — upgraded mock with SSE streaming and copilot responses (T01 output)
- `docker-compose.test.yml` — Docker stack with mock-llm service (T01 output)
- `e2e/helpers/selectors.ts` — existing selectors object
- `e2e/fixtures/auth.ts` — auth fixtures (ownerPage, ownerRequest, BASE_URL)
- `e2e/helpers/wait-for.ts` — wait helpers (waitForWorkspace, waitForIdle)
- `frontend/static/js/copilot.js` — copilot UI source (for discovering actual CSS classes and element IDs)
- `frontend/static/css/copilot.css` — copilot styles (for discovering actual CSS class names)
- `backend/app/api/copilot.py` — copilot API (for understanding SSE event types and endpoint contracts)

## Observability Impact

- **Playwright trace-on-retry:** When copilot E2E tests fail, Playwright's built-in trace captures the SSE stream state, approval card DOM, and conversation list — visible in `test-results/` directory.
- **Mock-LLM request logs:** During test runs, `docker compose logs mock-llm` shows `[mock-llm] POST /v1/chat/completions stream=true|false route=...` for each copilot request, enabling correlation between test actions and mock responses.
- **Conversation API inspection:** After a test run, `GET /api/copilot/conversations` on the test stack shows persisted conversations, useful for debugging conversation persistence test failures.
- **Test failure signals:** Each test has explicit `expect()` assertions on visible DOM elements — failures report the exact missing selector or mismatched text, not generic timeouts.

## Expected Output

- `e2e/tests/46-copilot/copilot.spec.ts` — Playwright E2E test spec with 5+ test cases
- `e2e/helpers/selectors.ts` — updated with `copilot` selector section
