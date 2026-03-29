/**
 * Copilot E2E Tests
 *
 * Exercises the full copilot chat stack against the Docker test stack with
 * the mock-llm service. Covers: basic chat, SPARQL approval, conversation
 * persistence, persona switching, and object creation from chat.
 *
 * The mock-llm returns deterministic canned responses based on message
 * content keywords, making assertions reliable without real LLM inference.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { SEL } from '../../helpers/selectors';
import { Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Open the copilot tab in the bottom panel.
 * Navigates to /browser/, waits for workspace, clicks the AI COPILOT tab,
 * and waits for the copilot container to appear.
 */
async function openCopilotTab(page: Page) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);
  await waitForIdle(page);

  // Ensure the bottom panel is open before clicking the tab
  await page.evaluate(() => {
    const panel = document.getElementById('bottom-panel');
    if (panel && panel.getBoundingClientRect().height < 10) {
      (window as any).SemPKM.toggleBottomPanel();
    }
  });

  // Click the AI COPILOT tab button in the bottom panel
  const tabBtn = page.locator(SEL.copilot.tabBtn);
  await tabBtn.click();

  // Wait for the copilot container to load (lazy-loaded via dynamic import)
  await page.waitForSelector(SEL.copilot.container, { state: 'visible', timeout: 15000 });

  // Wait for copilot initialization — the conversation header renders
  // after the async fetch to /api/copilot/conversations completes
  await page.waitForSelector(SEL.copilot.convHeader, { state: 'attached', timeout: 10000 });

  // Small settle time for Lucide icons and persona selector to render
  await page.waitForTimeout(500);
}

/**
 * Send a message in the copilot chat and wait for the user message to render.
 */
async function sendMessage(page: Page, text: string) {
  const input = page.locator(SEL.copilot.input);
  await input.fill(text);

  const sendBtn = page.locator(SEL.copilot.sendBtn);
  await sendBtn.click();

  // Wait for the user message bubble to appear
  await page.waitForSelector(
    `${SEL.copilot.msgUser}:has-text("${text.substring(0, 30)}")`,
    { state: 'visible', timeout: 5000 },
  );
}

/**
 * Wait for a streaming assistant response to complete.
 * The typing indicator disappears and an assistant message appears.
 */
async function waitForAssistantResponse(page: Page, timeoutMs = 15000) {
  // Wait for typing indicator to disappear (if present)
  await page.waitForSelector(SEL.copilot.typing, { state: 'detached', timeout: timeoutMs })
    .catch(() => { /* may have already been removed */ });

  // Wait for at least one assistant message to be visible
  const assistantMsg = page.locator(SEL.copilot.msgAssistant).last();
  await assistantMsg.waitFor({ state: 'visible', timeout: timeoutMs });
  return assistantMsg;
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.describe('Copilot', () => {
  // Configure LLM to point at the mock-llm service before all tests
  test.beforeAll(async ({ ownerRequest }) => {
    // Set the API base URL to the mock-llm service (accessible within Docker network)
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_base_url', value: 'http://mock-llm:8080' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'default_model', value: 'test-model' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_key', value: 'sk-mock-test-key' },
    });
  });

  // Clean up LLM config after all tests
  test.afterAll(async ({ ownerRequest }) => {
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_base_url', value: '' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'default_model', value: '' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_key', value: '' },
    });
  });

  // Use serial mode — tests build on shared copilot state
  test.describe.configure({ mode: 'serial' });

  test('basic chat flow — send message and receive streaming response', async ({ ownerPage }) => {
    await openCopilotTab(ownerPage);

    // Send a generic message (triggers GENERIC_RESPONSE from mock)
    await sendMessage(ownerPage, 'Hello, what can you help me with?');

    // Wait for assistant response to stream in
    const assistantMsg = await waitForAssistantResponse(ownerPage);

    // The generic response contains "knowledge graph" — verify content arrived
    const text = await assistantMsg.textContent();
    expect(text).toBeTruthy();
    expect(text!.length).toBeGreaterThan(20);

    // Verify the response contains expected canned content keywords
    expect(text).toContain('knowledge graph');

    // Verify no error messages appeared
    const errors = ownerPage.locator(SEL.copilot.msgError);
    await expect(errors).toHaveCount(0);
  });

  test('SPARQL generation and approval flow', async ({ ownerPage }) => {
    await openCopilotTab(ownerPage);

    // Send a message that triggers the SPARQL canned response
    await sendMessage(ownerPage, 'How many projects do I have?');

    // Wait for the approval card to appear (the backend detects the SPARQL block
    // in the streamed response and emits a sparql_query SSE event)
    const approvalCard = ownerPage.locator(SEL.copilot.approvalCard).first();
    await approvalCard.waitFor({ state: 'visible', timeout: 15000 });

    // Verify the card shows SPARQL query text
    const queryBlock = approvalCard.locator(SEL.copilot.approvalQuery);
    await expect(queryBlock).toBeVisible();
    const queryText = await queryBlock.textContent();
    expect(queryText).toContain('SELECT');

    // Verify the Approve button is present
    const approveBtn = approvalCard.locator(SEL.copilot.approveBtn);
    await expect(approveBtn).toBeVisible();

    // Click Approve to execute the query
    await approveBtn.click();

    // Wait for the approval success indicator or a result message
    // The card shows "Query executed" on success
    const success = approvalCard.locator(SEL.copilot.approvalSuccess);
    await success.waitFor({ state: 'visible', timeout: 10000 });

    // Verify no error messages
    const errors = ownerPage.locator(SEL.copilot.msgError);
    await expect(errors).toHaveCount(0);
  });

  test('conversation persistence across page reload', async ({ ownerPage }) => {
    await openCopilotTab(ownerPage);

    // Create a new conversation by clicking the new-chat button
    const newBtn = ownerPage.locator(SEL.copilot.convNewBtn);
    await newBtn.click();
    await ownerPage.waitForTimeout(500);

    // Send a message to create conversation content
    await sendMessage(ownerPage, 'Tell me about my knowledge graph');
    await waitForAssistantResponse(ownerPage);

    // Wait for conversation to be created (the SSE event updates the header)
    await ownerPage.waitForTimeout(1000);

    // Note the conversation title
    const titleEl = ownerPage.locator(SEL.copilot.convTitle);
    const titleText = await titleEl.textContent();
    expect(titleText).toBeTruthy();

    // Reload the page completely
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Re-open the copilot tab
    const tabBtn = ownerPage.locator(SEL.copilot.tabBtn);
    await tabBtn.click();
    await ownerPage.waitForSelector(SEL.copilot.container, { state: 'visible', timeout: 15000 });
    await ownerPage.waitForSelector(SEL.copilot.convHeader, { state: 'attached', timeout: 10000 });
    await ownerPage.waitForTimeout(500);

    // Open the conversation dropdown to verify the conversation was persisted
    const menuBtn = ownerPage.locator(SEL.copilot.convMenuBtn);
    await menuBtn.click();
    await ownerPage.waitForSelector(SEL.copilot.convDropdown, { state: 'visible', timeout: 5000 });

    // Verify at least one conversation item exists in the dropdown
    const items = ownerPage.locator(SEL.copilot.convDropdownItem);
    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('persona switching', async ({ ownerPage }) => {
    await openCopilotTab(ownerPage);

    // The persona selector should be rendered in the conversation header
    const personaSelector = ownerPage.locator(SEL.copilot.personaSelector);

    // Check if persona selector exists (requires at least 2 personas)
    const selectorExists = await personaSelector.isVisible().catch(() => false);
    if (!selectorExists) {
      // If no persona selector, we need to create personas first via API
      // Create two personas for testing
      await ownerPage.request.post(`${BASE_URL}/api/copilot/personas`, {
        data: {
          name: 'Research Assistant',
          icon: '🔬',
          system_prompt: 'You are a research-focused assistant.',
        },
      });
      await ownerPage.request.post(`${BASE_URL}/api/copilot/personas`, {
        data: {
          name: 'Writing Coach',
          icon: '✍️',
          system_prompt: 'You help with writing and editing.',
        },
      });

      // Reload to pick up the new personas
      await ownerPage.reload();
      await waitForWorkspace(ownerPage);
      await waitForIdle(ownerPage);
      const tabBtn = ownerPage.locator(SEL.copilot.tabBtn);
      await tabBtn.click();
      await ownerPage.waitForSelector(SEL.copilot.container, { state: 'visible', timeout: 15000 });
      await ownerPage.waitForSelector(SEL.copilot.convHeader, { state: 'attached', timeout: 10000 });
      await ownerPage.waitForTimeout(500);
    }

    // Click the persona button to open the dropdown
    const personaBtn = ownerPage.locator(SEL.copilot.personaBtn);
    await personaBtn.click();

    // Wait for persona dropdown to appear
    const dropdown = ownerPage.locator(SEL.copilot.personaDropdown);
    await dropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Verify at least 2 persona items
    const personaItems = ownerPage.locator(SEL.copilot.personaItem);
    const personaCount = await personaItems.count();
    expect(personaCount).toBeGreaterThanOrEqual(2);

    // Get the currently active persona's name
    const activeItem = ownerPage.locator(SEL.copilot.personaItemActive);
    const activeName = await activeItem.locator(SEL.copilot.personaItemName).textContent();

    // Click a non-active persona item
    const nonActiveItems = ownerPage.locator(
      `${SEL.copilot.personaItem}:not(${SEL.copilot.personaItemActive})`,
    );
    const nonActiveCount = await nonActiveItems.count();
    expect(nonActiveCount).toBeGreaterThanOrEqual(1);

    const targetName = await nonActiveItems.first().locator(SEL.copilot.personaItemName).textContent();
    await nonActiveItems.first().click();

    // Wait for the dropdown to close and the persona name to update
    await ownerPage.waitForSelector(SEL.copilot.personaDropdown, { state: 'detached', timeout: 5000 });

    // Verify the persona button text changed to the newly selected persona
    const updatedName = ownerPage.locator(SEL.copilot.personaName);
    await expect(updatedName).toHaveText(targetName!, { timeout: 5000 });

    // The selected name should differ from the previously active one
    expect(targetName).not.toBe(activeName);
  });

  test('object creation from chat', async ({ ownerPage }) => {
    await openCopilotTab(ownerPage);

    // Send a message that triggers the create-object canned response
    await sendMessage(ownerPage, 'Please create a task called Review Q1 goals');

    // Wait for the create-object confirmation card to appear
    // The backend detects the create_object JSON block in the streamed response
    const createCard = ownerPage.locator(SEL.copilot.createCard).first();
    await createCard.waitFor({ state: 'visible', timeout: 15000 });

    // Verify the card shows "Create Object" label
    const label = createCard.locator(SEL.copilot.createLabel);
    await expect(label).toHaveText('Create Object');

    // Verify the type badge shows the object type
    const typeBadge = createCard.locator(SEL.copilot.createType);
    await expect(typeBadge).toBeVisible();
    const typeText = await typeBadge.textContent();
    expect(typeText).toBeTruthy();

    // Verify properties are shown
    const props = createCard.locator(SEL.copilot.createProps);
    await expect(props).toBeVisible();

    // Click the Create button (uses the same approve btn class)
    const createBtn = createCard.locator(SEL.copilot.approveBtn);
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // Wait for the success state — shows a checkmark and a clickable IRI pill
    const success = createCard.locator(SEL.copilot.createSuccess);
    await success.waitFor({ state: 'visible', timeout: 10000 });

    // Verify the success message contains an IRI pill link to the created object
    const pill = createCard.locator(SEL.copilot.iriPill);
    await expect(pill).toBeVisible();

    // Verify the pill text contains the label
    const pillText = await pill.textContent();
    expect(pillText).toContain('Review Q1 goals');
  });
});
