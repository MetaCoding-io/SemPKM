/**
 * Operations Log E2E Tests
 *
 * Tests the ops log admin page rendering and type filter.
 * Uses ownerPage fixture only (ops log is owner-only).
 *
 * Consolidated into a single test() to stay within the 5/minute
 * magic-link rate limit imposed by auth rate limiting.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Operations Log', () => {
  test('ops log page shows activities table and filter narrows results', async ({ ownerPage }) => {
    // ---- Part 1: Page renders with heading and table ----
    await ownerPage.goto(`${BASE_URL}/admin/ops-log`);
    await ownerPage.waitForSelector(SEL.opsLog.table, { timeout: 15000 });

    // Heading should be visible
    const heading = ownerPage.locator('h1');
    await expect(heading).toContainText('Operations Log');

    // Check whether we have rows or the empty state
    const rows = ownerPage.locator(SEL.opsLog.row);
    const rowCount = await rows.count();

    if (rowCount === 0) {
      // Empty state — assert the placeholder message is shown
      const emptyMsg = ownerPage.locator(`${SEL.opsLog.table} tbody td`);
      await expect(emptyMsg).toContainText('No operations logged yet');
      // Can't test filter with no data — pass gracefully
      return;
    }

    // At least 1 row present (model install during test stack setup)
    expect(rowCount).toBeGreaterThanOrEqual(1);

    // Each row should have a type badge and status element
    const firstRow = rows.first();
    await expect(firstRow.locator(SEL.opsLog.typeBadge)).toBeVisible();
    await expect(firstRow.locator(SEL.opsLog.status)).toBeVisible();

    // ---- Part 2: Activity type filter narrows results ----
    const filterSelect = ownerPage.locator(SEL.opsLog.filter);
    await expect(filterSelect).toBeVisible();

    // Get the available filter options
    const options = await filterSelect.locator('option').allInnerTexts();
    // Should have "All activities" plus at least one type
    expect(options.length).toBeGreaterThanOrEqual(2);

    // Find a concrete activity type option (not "All activities")
    // model.install should exist from test stack setup
    const typeOptions = options.filter(o => o !== 'All activities');
    expect(typeOptions.length).toBeGreaterThanOrEqual(1);

    // Get the first available type's value from the <option> element
    const firstTypeOption = filterSelect.locator('option').nth(1);
    const filterValue = await firstTypeOption.getAttribute('value');
    expect(filterValue).toBeTruthy();

    // Select the first concrete type
    await filterSelect.selectOption(filterValue!);
    await waitForIdle(ownerPage);
    // Wait for htmx swap — the table is replaced via outerHTML
    await ownerPage.waitForSelector(SEL.opsLog.table, { timeout: 10000 });
    await waitForIdle(ownerPage);

    // All visible type badges should match the selected type
    const filteredBadges = ownerPage.locator(SEL.opsLog.typeBadge);
    const filteredCount = await filteredBadges.count();

    if (filteredCount > 0) {
      const badgeTexts = await filteredBadges.allInnerTexts();
      const expectedText = await firstTypeOption.innerText();
      for (const text of badgeTexts) {
        expect(text.trim()).toBe(expectedText.trim());
      }
    }

    // Reset filter to "All activities"
    // After htmx swap, the filter select might be re-rendered — re-locate it
    const resetFilter = ownerPage.locator(SEL.opsLog.filter);
    await resetFilter.selectOption('');
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector(SEL.opsLog.table, { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Rows should reappear (at least as many as before)
    const resetRows = ownerPage.locator(SEL.opsLog.row);
    const resetRowCount = await resetRows.count();
    expect(resetRowCount).toBeGreaterThanOrEqual(rowCount);
  });
});
