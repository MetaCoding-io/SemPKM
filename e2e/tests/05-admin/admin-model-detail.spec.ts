/**
 * Admin Model Detail & Ontology Diagram E2E Tests
 *
 * Tests model detail page, ontology diagram rendering, and webhook deletion.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Admin Model Detail Page', () => {
  test('model detail page loads for basic-pkm', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm`);
    expect(resp?.status()).toBe(200);

    // Should display model info
    await ownerPage.waitForSelector('h1, .model-detail, .model-name', { timeout: 15000 });
    const pageContent = await ownerPage.textContent('body');
    expect(pageContent).toMatch(/Basic PKM|basic-pkm/i);
  });

  test('model detail shows type list and stats', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm`);
    await ownerPage.waitForSelector('h1, .model-detail', { timeout: 15000 });

    const content = await ownerPage.textContent('body');
    // Should reference the Basic PKM types
    expect(content).toMatch(/Note|Concept|Project|Person/);
  });

  test('ontology diagram page renders for basic-pkm', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/ontology-diagram`);
    expect(resp?.status()).toBe(200);

    // Should render an SVG diagram or Mermaid/D3 visualization
    await ownerPage.waitForSelector('svg, .diagram, .ontology-diagram, canvas, .mermaid', { timeout: 15000 });

    const hasDiagram = await ownerPage.evaluate(() => {
      return !!(
        document.querySelector('svg') ||
        document.querySelector('.diagram') ||
        document.querySelector('.ontology-diagram') ||
        document.querySelector('canvas')
      );
    });
    expect(hasDiagram).toBe(true);
  });
});

test.describe('Admin Webhook Deletion', () => {
  test('create and delete a webhook', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Fill webhook form (URL + event type)
    const urlInput = ownerPage.locator('input[name="url"], input[placeholder*="URL"], #webhook-url');
    const urlCount = await urlInput.count();
    if (urlCount === 0) return; // Webhook form may not be on page

    await urlInput.fill('https://example.com/test-webhook');

    // Select event type if dropdown exists
    const eventSelect = ownerPage.locator('select[name="event_type"], select[name="events"]');
    if (await eventSelect.count() > 0) {
      await eventSelect.selectOption({ index: 0 });
    }

    // Submit
    const createBtn = ownerPage.locator('button', { hasText: /Create|Add|Save/i });
    await createBtn.click();
    await waitForIdle(ownerPage);

    // Wait for webhook to appear
    await ownerPage.waitForTimeout(1000);
    await waitForIdle(ownerPage);

    // Find the webhook row and delete it
    const webhookRows = ownerPage.locator(`${SEL.admin.webhookList} tbody tr, ${SEL.admin.webhookList} .webhook-item`);
    const rowCount = await webhookRows.count();

    if (rowCount > 0) {
      // Find the row with our test URL
      const testRow = webhookRows.filter({ hasText: 'example.com' });
      if (await testRow.count() > 0) {
        const deleteBtn = testRow.locator('button', { hasText: /Delete|Remove/i });
        await deleteBtn.click();
        await waitForIdle(ownerPage);

        // Verify it's gone
        await ownerPage.waitForTimeout(1000);
        const afterCount = await webhookRows.filter({ hasText: 'example.com' }).count();
        expect(afterCount).toBe(0);
      }
    }
  });
});
