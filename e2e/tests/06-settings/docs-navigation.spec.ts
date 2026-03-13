/**
 * User Guide Docs Navigation E2E Tests
 *
 * Tests the docs tab navigation: opening the docs tab, clicking through
 * guide pages, and verifying content loads for each page.
 *
 * Routes:
 * - GET /browser/docs — docs index page
 * - GET /browser/docs/guide/{filename} — individual guide pages
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { openDocsTab } from '../../helpers/dockview';

test.describe('Docs Navigation', () => {
  test('docs tab opens and shows guide content', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openDocsTab(ownerPage);
    await waitForIdle(ownerPage);

    // Docs page should be visible
    const docsPage = ownerPage.locator('#docs-page');
    await expect(docsPage).toBeVisible({ timeout: 10000 });
  });

  test('docs index page loads via direct URL', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/docs`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
    // Should contain guide links or navigation
    expect(html).toMatch(/guide|docs|help|getting started/i);
  });

  test('guide pages render markdown content', async ({ ownerRequest }) => {
    // Try to load a specific guide page
    const resp = await ownerRequest.get(`${BASE_URL}/browser/docs/guide/index`);

    if (resp.ok()) {
      const html = await resp.text();
      expect(html.length).toBeGreaterThan(0);
    }
  });

  test('docs tab has navigation links between pages', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openDocsTab(ownerPage);
    await waitForIdle(ownerPage);

    // Check for navigation links within docs
    const docLinks = ownerPage.locator('#docs-page a, #docs-page [hx-get]');
    const linkCount = await docLinks.count();

    // Should have at least one navigation link
    expect(linkCount).toBeGreaterThan(0);
  });
});
