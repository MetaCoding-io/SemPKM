/**
 * Body Diff E2E Tests (M012/S02)
 *
 * Tests the body.diff feature:
 * - body.diff event appears after editing an existing body
 * - body.diff detail shows diff highlighting (add/remove lines)
 * - First body set creates body.set event (not body.diff)
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/**
 * Helper: open bottom panel and navigate to EVENT LOG tab.
 */
async function openEventLog(page: import('@playwright/test').Page) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);
  await waitForIdle(page);

  // Open bottom panel via JS
  await page.waitForFunction(
    () => typeof (window as any).SemPKM.toggleBottomPanel === 'function',
    { timeout: 10000 },
  );
  await page.evaluate(() => (window as any).SemPKM.toggleBottomPanel());
  await waitForIdle(page);

  // Wait for bottom panel to have a non-zero rendered height
  await page.waitForFunction(
    () => {
      const panel = document.getElementById('bottom-panel');
      if (!panel) return false;
      return panel.getBoundingClientRect().height > 10;
    },
    { timeout: 5000 },
  );

  // Click EVENT LOG tab
  const eventLogTab = page.locator('.panel-tab[data-panel="event-log"]');
  await eventLogTab.click({ force: true });
  await waitForIdle(page);

  // Wait for event rows to load via htmx
  const eventRows = page.locator('.event-row-wrapper');
  await expect(eventRows.first()).toBeVisible({ timeout: 10000 });
}

test.describe('Body Diff', () => {
  test('body.diff event appears after editing existing body', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Step 1: Create a Note object
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Body Diff Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;

    // Step 2: Set the first body text (creates body.set event)
    const encodedIri = encodeURIComponent(objectIri);
    const firstBodyResp = await ownerRequest.post(
      `${BASE_URL}/browser/objects/${encodedIri}/body`,
      {
        data: 'This is the original body text.\nWith two lines.',
        headers: { 'Content-Type': 'text/plain' },
      },
    );
    expect(firstBodyResp.ok()).toBeTruthy();

    // Step 3: Update the body text (creates body.diff event)
    const secondBodyResp = await ownerRequest.post(
      `${BASE_URL}/browser/objects/${encodedIri}/body`,
      {
        data: 'This is the updated body text.\nWith two lines.\nAnd a third line.',
        headers: { 'Content-Type': 'text/plain' },
      },
    );
    expect(secondBodyResp.ok()).toBeTruthy();

    // Step 4: Open event log and find the body.diff event
    await openEventLog(ownerPage);

    // Look for an event row with "body.diff" operation badge
    const bodyDiffBadge = ownerPage.locator('.event-op-badge', { hasText: 'body.diff' });
    await expect(bodyDiffBadge.first()).toBeVisible({ timeout: 10000 });
  });

  test('body.diff detail shows diff highlighting', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Create a Note and set + update body to generate body.diff event
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Diff Highlight Test' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;
    const encodedIri = encodeURIComponent(objectIri);

    // First body set
    await ownerRequest.post(`${BASE_URL}/browser/objects/${encodedIri}/body`, {
      data: 'Line one of original.\nLine two stays the same.',
      headers: { 'Content-Type': 'text/plain' },
    });

    // Update body to create body.diff
    await ownerRequest.post(`${BASE_URL}/browser/objects/${encodedIri}/body`, {
      data: 'Line one changed.\nLine two stays the same.\nLine three is new.',
      headers: { 'Content-Type': 'text/plain' },
    });

    await openEventLog(ownerPage);

    // Find the body.diff event row and click its Diff button
    const bodyDiffRow = ownerPage
      .locator('.event-row-wrapper')
      .filter({ has: ownerPage.locator('.event-op-badge', { hasText: 'body.diff' }) })
      .first();
    await expect(bodyDiffRow).toBeVisible({ timeout: 10000 });

    const diffBtn = bodyDiffRow.locator('.event-btn-diff:not(:disabled)');
    await expect(diffBtn).toBeVisible({ timeout: 5000 });
    await diffBtn.click({ force: true });
    await waitForIdle(ownerPage);

    // Wait for the diff panel to render (htmx loads content into .event-diff-container)
    const diffContainer = bodyDiffRow.locator('.event-diff-container');
    const diffPanel = diffContainer.locator('.event-diff-panel');
    await expect(diffPanel).toBeVisible({ timeout: 15000 });

    // Assert that the diff shows both add and remove lines
    const addLines = diffPanel.locator('.diff-line-add');
    const removeLines = diffPanel.locator('.diff-line-remove');

    await expect(addLines.first()).toBeVisible({ timeout: 5000 });
    await expect(removeLines.first()).toBeVisible({ timeout: 5000 });

    // Verify the diff has meaningful content
    const addCount = await addLines.count();
    const removeCount = await removeLines.count();
    expect(addCount).toBeGreaterThan(0);
    expect(removeCount).toBeGreaterThan(0);
  });

  test('first body set creates body.set event, not body.diff', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Create a new Note
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'First Body Set Test' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;
    const encodedIri = encodeURIComponent(objectIri);

    // Set body for the first time only (no prior body exists)
    const bodyResp = await ownerRequest.post(
      `${BASE_URL}/browser/objects/${encodedIri}/body`,
      {
        data: 'This is the first body ever set.',
        headers: { 'Content-Type': 'text/plain' },
      },
    );
    expect(bodyResp.ok()).toBeTruthy();

    await openEventLog(ownerPage);

    // The most recent body-related event for our object should be "body.set"
    // We verify via the event log UI: look for a body.set badge
    const bodySetBadge = ownerPage.locator('.event-op-badge', { hasText: 'body.set' });
    await expect(bodySetBadge.first()).toBeVisible({ timeout: 10000 });

    // Now verify that "body.diff" does NOT appear at the top of the list
    // (the most recent event should be body.set, not body.diff)
    // We check the first few event rows to confirm body.set precedes any body.diff
    const firstFewRows = ownerPage.locator('.event-row-wrapper').locator('nth=0 >> nth=4');
    const allBadges = ownerPage.locator('.event-row-wrapper .event-op-badge');
    const badgeCount = await allBadges.count();

    // Find the first body-related event (searching from the top = most recent)
    let firstBodyEventType = '';
    for (let i = 0; i < Math.min(badgeCount, 10); i++) {
      const text = (await allBadges.nth(i).textContent()) || '';
      const trimmed = text.trim();
      if (trimmed.startsWith('body.')) {
        firstBodyEventType = trimmed;
        break;
      }
    }

    // The first (most recent) body event should be body.set
    expect(firstBodyEventType).toBe('body.set');
  });
});
