/**
 * Tutorials and Docs E2E Tests
 *
 * Tests the Docs & Tutorials page functionality:
 * - openDocsTab() opens the docs tab in the active editor group
 * - The docs page renders inside the group editor area
 * - Tutorial "Start Tour" buttons are visible and clickable
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 * Phase: 18 (Tutorials and Documentation) + Phase 19 (link fix)
 *
 * DOM structure (from workspace.html + docs_page.html):
 *   [data-tab-id="special:docs"]  — the tab element in the group-tab-bar
 *   .tab-label                    — text label inside the tab element
 *   #docs-page / .docs-page       — the docs content rendered in group-editor-area
 *   .docs-card-btn                — "Start Tour" buttons in the interactive tutorials section
 *
 * Note: The Docs & Tutorials sidebar nav link calls openDocsTab() onclick.
 *   The link lives inside .sidebar-group[data-group="meta"] which may be collapsed
 *   (state persisted in localStorage). Tests call openDocsTab() directly via JS
 *   evaluation to avoid sidebar-state dependency.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Tutorials and Docs', () => {
  test('openDocsTab opens a docs tab in the editor group', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Call openDocsTab() directly (same as clicking the sidebar nav link)
    // Cast to any: openDocsTab is registered on window by workspace.js at runtime
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    // A tab with data-tab-id="special:docs" should appear in the tab bar
    // (workspace-layout.js: tabEl.setAttribute('data-tab-id', tabId))
    const docsTab = ownerPage.locator('[data-tab-id="special:docs"]');
    await expect(docsTab).toBeVisible({ timeout: 10000 });

    // The tab label should read "Docs & Tutorials"
    const tabLabel = docsTab.locator('.tab-label');
    await expect(tabLabel).toContainText('Docs');
  });

  test('tutorial start buttons are visible in the docs page', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open docs tab via JS
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    // Wait for docs page content to render
    // docs_page.html renders inside the group-editor-area as #docs-page / .docs-page
    const docsPage = ownerPage.locator('#docs-page');
    await expect(docsPage).toBeVisible({ timeout: 10000 });

    // "Start Tour" buttons should be present (docs_page.html: <button class="btn docs-card-btn">Start Tour</button>)
    const tourButtons = ownerPage.locator('.docs-card-btn');
    await expect(tourButtons.first()).toBeVisible();

    const count = await tourButtons.count();
    expect(count).toBeGreaterThan(0);
  });
});
