/**
 * Admin Webhooks E2E Tests
 *
 * Tests the webhook configuration page: creating, listing,
 * toggling, and deleting webhooks.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Admin Webhooks Page', () => {
  test('webhooks page loads with create form', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Page title
    await expect(ownerPage.locator('h1')).toContainText('Webhooks');

    // Create form elements
    await expect(ownerPage.locator('#webhook-url')).toBeVisible();
    await expect(ownerPage.locator('button', { hasText: 'Create' })).toBeVisible();

    // Event type checkboxes
    const checkboxes = ownerPage.locator('.checkbox-group input[type="checkbox"]');
    const checkboxCount = await checkboxes.count();
    expect(checkboxCount).toBeGreaterThanOrEqual(3); // object.changed, edge.changed, validation.completed
  });

  test('create a webhook', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Fill in the form
    await ownerPage.fill('#webhook-url', 'https://example.com/e2e-test-webhook');

    // Check at least one event type
    await ownerPage.locator('.checkbox-group input[value="object.changed"]').check();

    // Submit
    await ownerPage.click('button:has-text("Create")');
    await waitForIdle(ownerPage);

    // Should see success message or the webhook in the list
    await ownerPage.waitForTimeout(2000);

    const webhookList = ownerPage.locator(SEL.admin.webhookList);
    // The webhook should appear in the list
    await expect(webhookList).toContainText('example.com/e2e-test-webhook', { timeout: 10000 });
  });

  test('webhook list shows target URL and events', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // If webhooks exist from previous test, verify columns
    const table = ownerPage.locator(`${SEL.admin.webhookList} table`);
    const tableCount = await table.count();

    if (tableCount > 0) {
      const headers = await table.locator('thead th').allInnerTexts();
      expect(headers).toContain('Target URL');
      expect(headers).toContain('Events');
      expect(headers).toContain('Status');
      expect(headers).toContain('Actions');
    }
  });

  test('toggle webhook enabled/disabled', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Find a toggle button (if webhooks exist)
    const toggleBtn = ownerPage.locator('.btn-toggle').first();
    const toggleCount = await toggleBtn.count();

    if (toggleCount > 0) {
      const initialText = await toggleBtn.innerText();
      await toggleBtn.click();
      await waitForIdle(ownerPage);
      await ownerPage.waitForTimeout(2000);

      // After toggle, the button text should change
      const newToggleBtn = ownerPage.locator('.btn-toggle').first();
      const newText = await newToggleBtn.innerText();

      // Should have toggled between "Enable" and "Disable"
      expect(newText).not.toBe(initialText);
    }
  });

  test('delete a webhook', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Count webhooks before delete
    const deleteButtons = ownerPage.locator(`${SEL.admin.webhookList} button:has-text("Delete")`);
    const beforeCount = await deleteButtons.count();

    if (beforeCount > 0) {
      // Accept the confirmation dialog
      ownerPage.on('dialog', (dialog) => dialog.accept());

      await deleteButtons.first().click();
      await waitForIdle(ownerPage);
      await ownerPage.waitForTimeout(2000);

      // The webhook should be removed
      const afterDeleteButtons = ownerPage.locator(`${SEL.admin.webhookList} button:has-text("Delete")`);
      const afterCount = await afterDeleteButtons.count();
      expect(afterCount).toBeLessThan(beforeCount);
    }
  });

  test('creating webhook without event type shows error', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Fill URL but don't check any event types
    await ownerPage.fill('#webhook-url', 'https://example.com/no-events');

    // Make sure no checkboxes are checked
    const checkboxes = ownerPage.locator('.checkbox-group input[type="checkbox"]');
    const count = await checkboxes.count();
    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).uncheck();
    }

    await ownerPage.click('button:has-text("Create")');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    // Should see error message about events
    const webhookList = ownerPage.locator(SEL.admin.webhookList);
    await expect(webhookList).toContainText('event', { timeout: 5000 });
  });
});
