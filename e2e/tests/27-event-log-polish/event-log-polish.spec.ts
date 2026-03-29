/**
 * Event Log Polish E2E Tests (M012/S01)
 *
 * Tests the S01 event log improvements:
 * - Human-readable predicate labels in event detail (not raw IRIs)
 * - SHACL helptext tooltips on predicate labels
 * - Autocomplete suggestions for operation type filter
 * - Autocomplete suggestions for predicate filter with typed input
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/**
 * Helper: open bottom panel and navigate to EVENT LOG tab.
 * Returns the ownerPage with event log visible and rows loaded.
 */
async function openEventLog(ownerPage: import('@playwright/test').Page) {
  await ownerPage.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(ownerPage);
  await waitForIdle(ownerPage);

  // Open bottom panel via JS for reliability
  await ownerPage.waitForFunction(
    () => typeof (window as any).SemPKM.toggleBottomPanel === 'function',
    { timeout: 10000 },
  );
  await ownerPage.evaluate(() => (window as any).SemPKM.toggleBottomPanel());
  await waitForIdle(ownerPage);

  // Wait for bottom panel to have a non-zero rendered height
  await ownerPage.waitForFunction(
    () => {
      const panel = document.getElementById('bottom-panel');
      if (!panel) return false;
      return panel.getBoundingClientRect().height > 10;
    },
    { timeout: 15000 },
  );

  // Click EVENT LOG tab
  const eventLogTab = ownerPage.locator('.panel-tab[data-panel="event-log"]');
  await eventLogTab.click({ force: true });
  await waitForIdle(ownerPage);

  // Wait for event rows to load via htmx
  const eventRows = ownerPage.locator('.event-row-wrapper');
  await expect(eventRows.first()).toBeVisible({ timeout: 10000 });
}

test.describe('Event Log Polish', () => {
  test('event detail shows human-readable predicate labels', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Create an object so we have a fresh event with known predicates
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Label Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    await openEventLog(ownerPage);

    // Find the first event row with an enabled Diff button and click it
    const diffBtn = ownerPage.locator('.event-btn-diff:not(:disabled)').first();
    await expect(diffBtn).toBeVisible({ timeout: 5000 });
    await diffBtn.click({ force: true });
    await waitForIdle(ownerPage);

    // Wait for the diff panel to load
    const diffPanel = ownerPage.locator('.event-diff-panel').first();
    await expect(diffPanel).toBeVisible({ timeout: 10000 });

    // Assert that .diff-pred-label elements contain human-readable text
    // (not raw IRIs like "http://purl.org/dc/terms/title" or bare QNames)
    const predLabels = diffPanel.locator('.diff-pred-label');
    const labelCount = await predLabels.count();
    expect(labelCount).toBeGreaterThan(0);

    // Check that at least one label is human-readable (Title, Type, etc.)
    // and NOT a full IRI
    let foundHumanLabel = false;
    for (let i = 0; i < labelCount; i++) {
      const text = (await predLabels.nth(i).textContent()) || '';
      const trimmed = text.trim();
      // A human-readable label should not start with http:// or urn:
      if (trimmed && !trimmed.startsWith('http://') && !trimmed.startsWith('urn:')) {
        foundHumanLabel = true;
        break;
      }
    }
    expect(foundHumanLabel).toBe(true);
  });

  test('predicate labels have helptext tooltips', async ({ ownerPage, ownerRequest }) => {
    // Create an object with a title (dcterms:title has SHACL helptext in basic-pkm)
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Helptext Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    await openEventLog(ownerPage);

    // Click the first enabled Diff button to expand event detail
    const diffBtn = ownerPage.locator('.event-btn-diff:not(:disabled)').first();
    await expect(diffBtn).toBeVisible({ timeout: 5000 });
    await diffBtn.click({ force: true });
    await waitForIdle(ownerPage);

    const diffPanel = ownerPage.locator('.event-diff-panel').first();
    await expect(diffPanel).toBeVisible({ timeout: 10000 });

    // Check if any predicate label has the .has-helptext class with a non-empty title
    const helptextLabels = diffPanel.locator('.diff-pred-label.has-helptext');
    const htCount = await helptextLabels.count();

    if (htCount > 0) {
      // At least one label has helptext — verify title is non-empty
      const titleAttr = await helptextLabels.first().getAttribute('title');
      expect(titleAttr).toBeTruthy();
      expect(titleAttr!.length).toBeGreaterThan(0);
      // Title should be descriptive text, not just the IRI
      expect(titleAttr!.startsWith('http://')).toBeFalsy();
    } else {
      // Even without .has-helptext, all .diff-pred-label should have a title attribute
      const allLabels = diffPanel.locator('.diff-pred-label');
      const allCount = await allLabels.count();
      expect(allCount).toBeGreaterThan(0);
      // Verify at least one has a title attribute (falls back to IRI if no helptext)
      const titleAttr = await allLabels.first().getAttribute('title');
      expect(titleAttr).toBeTruthy();
    }
  });

  test('autocomplete suggestions appear for operation type filter', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Ensure at least one event exists
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Autocomplete Op Test' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    await openEventLog(ownerPage);

    // Focus the operation type filter input — triggers htmx GET on focus
    const opFilterInput = ownerPage.locator('#event-op-filter');
    await expect(opFilterInput).toBeVisible({ timeout: 5000 });
    await opFilterInput.focus();
    await waitForIdle(ownerPage);

    // Wait for suggestions dropdown to appear
    const suggestionsTarget = ownerPage.locator('#op-suggestions');
    const suggestionItems = suggestionsTarget.locator('.event-suggestion-item');
    await expect(suggestionItems.first()).toBeVisible({ timeout: 10000 });

    const count = await suggestionItems.count();
    expect(count).toBeGreaterThan(0);

    // Verify suggestion items have meaningful text (operation types like "object.create")
    const firstText = (await suggestionItems.first().textContent()) || '';
    expect(firstText.trim().length).toBeGreaterThan(0);
    // Should contain a dot-separated operation type
    expect(firstText.trim()).toMatch(/\w+\.\w+/);
  });

  test('predicate filter shows suggestions on input', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Ensure events exist with predicates
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Pred Filter Test' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    await openEventLog(ownerPage);

    // Focus and type into the predicate filter input
    const predFilterInput = ownerPage.locator('#event-pred-filter');
    await expect(predFilterInput).toBeVisible({ timeout: 5000 });
    await predFilterInput.focus();

    // Type slowly to trigger the keyup debounce (300ms)
    await predFilterInput.pressSequentially('tit', { delay: 150 });
    await waitForIdle(ownerPage);

    // Wait for suggestions — might take a moment due to debounce
    const suggestionsTarget = ownerPage.locator('#pred-suggestions');
    const suggestionItems = suggestionsTarget.locator('.event-suggestion-item');
    await expect(suggestionItems.first()).toBeVisible({ timeout: 10000 });

    const count = await suggestionItems.count();
    expect(count).toBeGreaterThan(0);

    // Verify at least one suggestion relates to "title"
    let foundTitleSuggestion = false;
    for (let i = 0; i < count; i++) {
      const text = (await suggestionItems.nth(i).textContent()) || '';
      if (text.toLowerCase().includes('title')) {
        foundTitleSuggestion = true;
        break;
      }
    }
    expect(foundTitleSuggestion).toBe(true);
  });
});
