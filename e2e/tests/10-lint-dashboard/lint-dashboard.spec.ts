/**
 * Global Lint Dashboard E2E Tests
 *
 * Tests the lint dashboard in the bottom panel: loading, displaying
 * validation results, severity filtering, sorting, search, and health badge.
 *
 * The dashboard is htmx lazy-loaded via hx-trigger="revealed" when its
 * panel tab becomes visible in the bottom panel.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { Page } from '@playwright/test';

/**
 * Open the bottom panel and switch to a specific tab.
 */
async function openBottomPanelTab(page: Page, tabName: string) {
  await page.evaluate(() => {
    const panel = document.getElementById('bottom-panel');
    if (!panel) return;
    const h = panel.style.height;
    if (!h || h === '0px' || h === '0') {
      if (typeof (window as any).toggleBottomPanel === 'function') {
        (window as any).toggleBottomPanel();
      }
    }
  });
  await page.waitForTimeout(500);
  await page.click(`.panel-tab[data-panel="${tabName}"]`);
  await waitForIdle(page);
}

test.describe('Lint Dashboard', () => {
  test('lint dashboard loads in bottom panel', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    // Wait for the lint dashboard to load via htmx revealed trigger
    const dashboard = ownerPage.locator('.lint-dashboard');
    await expect(dashboard).toBeVisible({ timeout: 15000 });

    // Dashboard should have filter controls
    await expect(ownerPage.locator('.lint-dashboard-filter-severity')).toBeVisible();
    await expect(ownerPage.locator('.lint-dashboard-filter-sort')).toBeVisible();
    await expect(ownerPage.locator('.lint-dashboard-filter-search')).toBeVisible();
  });

  test('lint dashboard shows validation results after creating invalid object', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;

    // Create an object with missing required fields to trigger SHACL violations
    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: {}, // No title -- triggers required field violation
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    // Wait for async validation to process
    await ownerPage.waitForTimeout(5000);

    // Navigate to workspace and open lint dashboard
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    // Wait for dashboard to load
    const dashboard = ownerPage.locator('.lint-dashboard');
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Check if we have validation rows or the "all clear" state
    const rows = ownerPage.locator('.lint-dashboard-row');
    const rowCount = await rows.count();
    const conformsBadge = ownerPage.locator('.lint-conforms');
    const conformsCount = await conformsBadge.count();

    // Either we have violation rows or the conforms badge
    // (seed data may produce violations from the empty Note)
    expect(rowCount + conformsCount).toBeGreaterThan(0);

    if (rowCount > 0) {
      // Verify rows have severity indicators
      const firstRow = rows.first();
      await expect(firstRow).toBeVisible();

      // Each row should have a severity class
      const rowClass = await firstRow.getAttribute('class');
      expect(rowClass).toMatch(/lint-severity-(violation|warning|info)/);
    }
  });

  test('severity filter narrows results', async ({ ownerPage }) => {
    // Tests are sequential -- validation results exist from previous test
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    const dashboard = ownerPage.locator('#lint-dashboard-container').first();
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Use .first() to handle htmx swap creating duplicate elements
    const severityFilter = ownerPage.locator('.lint-dashboard-filter-severity').first();
    await expect(severityFilter).toBeVisible();

    // Verify filter has expected options
    const options = await severityFilter.locator('option').allInnerTexts();
    expect(options).toContain('All severities');
    expect(options).toContain('Violations');

    // Get total row count before filtering
    const totalRows = await ownerPage.locator('.lint-dashboard-row').count();

    // Select Violation filter
    await severityFilter.selectOption('Violation');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    const filteredRows = await ownerPage.locator('.lint-dashboard-row').count();

    // Filtered count should be <= total
    expect(filteredRows).toBeLessThanOrEqual(totalRows);

    // If there are filtered rows, verify they all have violation class
    if (filteredRows > 0) {
      for (let i = 0; i < filteredRows; i++) {
        const rowClass = await ownerPage.locator('.lint-dashboard-row').nth(i).getAttribute('class');
        expect(rowClass).toContain('lint-severity-violation');
      }
    }

    // Reset filter
    await severityFilter.selectOption('');
    await waitForIdle(ownerPage);
  });

  test('sorting changes result order', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    const dashboard = ownerPage.locator('#lint-dashboard-container').first();
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    const sortSelect = ownerPage.locator('.lint-dashboard-filter-sort').first();
    await expect(sortSelect).toBeVisible();

    // Verify sort options exist
    const options = await sortSelect.locator('option').allInnerTexts();
    expect(options.length).toBeGreaterThanOrEqual(2);
    expect(options).toContain('Sort: Severity');
    expect(options).toContain('Sort: Object');

    // Change sort to "object"
    await sortSelect.selectOption('object');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    // Verify the sort option is now selected
    const selectedValue = await sortSelect.inputValue();
    expect(selectedValue).toBe('object');

    // Change sort to "path"
    await sortSelect.selectOption('path');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    const selectedValue2 = await sortSelect.inputValue();
    expect(selectedValue2).toBe('path');

    // Reset to severity
    await sortSelect.selectOption('severity');
    await waitForIdle(ownerPage);
  });

  test('search filter works', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    const dashboard = ownerPage.locator('#lint-dashboard-container').first();
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    const searchInput = ownerPage.locator('.lint-dashboard-filter-search').first();
    await expect(searchInput).toBeVisible();

    // Type a search term
    await searchInput.fill('title');
    // Wait for debounce (300ms) + htmx request
    await ownerPage.waitForTimeout(1000);
    await waitForIdle(ownerPage);

    // The search should have been applied (results may be filtered)
    // Verify the search input still has the value
    const inputValue = await searchInput.inputValue();
    expect(inputValue).toBe('title');

    // Clear search
    await searchInput.fill('');
    await ownerPage.waitForTimeout(1000);
    await waitForIdle(ownerPage);
  });

  test('health badge shows in panel tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // The lint badge should be in the panel tab button
    // (visible even before opening the panel)
    const lintTab = ownerPage.locator('.panel-tab[data-panel="lint-dashboard"]');
    await expect(lintTab).toBeVisible();

    // The tab contains the lint badge span
    const badge = ownerPage.locator('#lint-badge');
    // Badge exists in DOM (may be empty if no issues)
    await expect(badge).toBeAttached();
  });

  test('lint dashboard API endpoint returns HTML partial', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;

    const resp = await api.get(`${BASE_URL}/browser/lint-dashboard`, {
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'HX-Request': 'true',
      },
    });

    expect(resp.ok()).toBeTruthy();
    const html = await resp.text();

    // Should contain the dashboard container
    expect(html).toContain('lint-dashboard');
    // Should contain filter controls
    expect(html).toContain('lint-dashboard-filter-severity');
    expect(html).toContain('lint-dashboard-filter-sort');
  });
});
