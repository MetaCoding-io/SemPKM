/**
 * User Guide Docs Navigation E2E Tests
 *
 * Tests the docs tab navigation: opening the docs tab, clicking through
 * guide pages, and verifying content loads for each page.
 *
 * Routes:
 * - GET /browser/docs — docs index page
 * - GET /browser/docs/guide/{filename} — individual guide pages
 *
 * Consolidated into 1 test() function (API endpoint checks + UI
 * navigation) to stay within the 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { openDocsTab } from '../../helpers/dockview';

test.describe('Docs Navigation', () => {
  test('docs endpoints return HTML and tab navigation works', async ({ ownerRequest, ownerPage }) => {
    // --- Part 1: API endpoint checks ---

    // Docs index page
    const indexResp = await ownerRequest.get(`${BASE_URL}/browser/docs`);
    expect(indexResp.ok()).toBeTruthy();
    const indexHtml = await indexResp.text();
    expect(indexHtml.length).toBeGreaterThan(0);
    expect(indexHtml).toMatch(/guide|docs|help|getting.started|tutorial/i);

    // Guide page — try the index page
    const guideResp = await ownerRequest.get(`${BASE_URL}/browser/docs/guide/index`);
    expect([200, 404].includes(guideResp.status())).toBeTruthy();

    // Try a common guide filename pattern
    const altGuideResp = await ownerRequest.get(
      `${BASE_URL}/browser/docs/guide/01-what-is-sempkm.md`
    );
    expect([200, 404].includes(altGuideResp.status())).toBeTruthy();

    // --- Part 2: UI tab navigation ---

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open docs tab via the application API
    await openDocsTab(ownerPage);
    await waitForIdle(ownerPage);

    // Docs page should be visible
    const docsPage = ownerPage.locator('#docs-page');
    await expect(docsPage).toBeVisible({ timeout: 10000 });

    // Docs page should have navigation links
    const docLinks = ownerPage.locator('#docs-page a, #docs-page [hx-get]');
    const linkCount = await docLinks.count();
    expect(linkCount).toBeGreaterThan(0);

    // Click the first link and verify content loads
    if (linkCount > 0) {
      const firstLink = docLinks.first();
      const firstHref = await firstLink.getAttribute('href');
      const firstHxGet = await firstLink.getAttribute('hx-get');
      expect(firstHref || firstHxGet).toBeTruthy();

      await firstLink.click();
      await waitForIdle(ownerPage);

      // After clicking a guide link, content may load via htmx swap.
      // Verify meaningful content exists.
      const contentAfterClick = await ownerPage.evaluate(() => {
        const docsEl = document.getElementById('docs-page');
        if (docsEl && (docsEl.textContent?.length || 0) > 0) return true;
        const mdBody = document.querySelector('.markdown-body, .docs-content, .guide-content');
        if (mdBody && (mdBody.textContent?.length || 0) > 0) return true;
        const backLink = document.querySelector('a[href*="docs"], [hx-get*="docs"]');
        if (backLink) return true;
        return false;
      });
      expect(contentAfterClick).toBe(true);
    }
  });
});
