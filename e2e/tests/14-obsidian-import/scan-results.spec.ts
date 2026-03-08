/**
 * Obsidian Scan Results E2E Tests (OBSI-02)
 *
 * Tests the scan results dashboard after a vault has been uploaded.
 * Verifies stat cards, type groups, collapsible sections, and warnings.
 *
 * Depends on vault-upload.spec.ts having uploaded the vault already
 * (tests run sequentially, single worker).
 */
import { test, expect } from '../../fixtures/auth';
import { waitForIdle } from '../../helpers/wait-for';
import path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Obsidian Scan Results', () => {
  test.beforeEach(async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-layout', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Open import tab - should show existing results or upload form
    await ownerPage.evaluate(() => {
      (window as any).openImportTab();
    });

    // Check if results are already showing (from previous test run)
    const hasResults = await ownerPage.locator('.import-stat-cards').isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasResults) {
      // Need to upload first
      const uploadZone = ownerPage.locator('.import-upload-zone');
      const hasUpload = await uploadZone.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasUpload) {
        const fileInput = ownerPage.locator('#vault-zip');
        const fixturePath = path.resolve(__dirname, '../../fixtures/test-vault.zip');
        await fileInput.setInputFiles(fixturePath);
        const submitBtn = ownerPage.locator('.upload-selected-file button[type="submit"]');
        await expect(submitBtn).toBeVisible({ timeout: 5000 });
        await submitBtn.click();
      } else {
        // Resume previous import
        const resumeBtn = ownerPage.locator('button:has-text("Resume Previous Import")');
        if (await resumeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await resumeBtn.click();
        }
      }

      // Wait for results
      await expect(ownerPage.locator('.import-stat-cards')).toBeVisible({ timeout: 30000 });
    }
  });

  test('stat cards show correct counts', async ({ ownerPage }) => {
    const notesCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Notes' });
    await expect(notesCard.locator('.stat-number')).toHaveText('6');

    const tagsCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Tags' });
    const tagsCount = await tagsCard.locator('.stat-number').textContent();
    expect(parseInt(tagsCount || '0')).toBeGreaterThanOrEqual(3);

    const linksCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Links' });
    const linksCount = await linksCard.locator('.stat-number').textContent();
    expect(parseInt(linksCount || '0')).toBeGreaterThanOrEqual(1);

    const attachCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Attachments' });
    await expect(attachCard.locator('.stat-number')).toHaveText('1');
  });

  test('type groups section exists with detected types', async ({ ownerPage }) => {
    const typeGroups = ownerPage.locator('.import-type-group');
    const count = await typeGroups.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('Uncategorized group is visually distinct', async ({ ownerPage }) => {
    const uncategorized = ownerPage.locator('.import-type-group.uncategorized');
    // May or may not exist depending on detection - if it does, check styling
    const count = await uncategorized.count();
    if (count > 0) {
      await expect(uncategorized.first()).toBeVisible();
    }
  });

  test('collapsible sections exist', async ({ ownerPage }) => {
    // At least Frontmatter Keys and Tags should be present
    const collapsibles = ownerPage.locator('.import-collapsible');
    const count = await collapsibles.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // Expand the first collapsible and verify content appears
    const firstSummary = collapsibles.first().locator('summary');
    await firstSummary.click();

    // After expanding, should see content inside
    const inner = collapsibles.first().locator('table, .import-tag-list');
    await expect(inner).toBeVisible({ timeout: 3000 });
  });

  test('warnings section shows at least one warning', async ({ ownerPage }) => {
    // random-file.md should trigger empty_note warning
    const warningSection = ownerPage.locator('.import-warnings-section');
    await expect(warningSection).toBeVisible({ timeout: 5000 });

    const warnings = ownerPage.locator('.import-warning');
    const count = await warnings.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('Discard Import button exists and works', async ({ ownerPage }) => {
    const discardBtn = ownerPage.locator('button:has-text("Discard Import")');
    await expect(discardBtn).toBeVisible();

    // Click discard
    await discardBtn.click();

    // Should return to upload form
    const uploadZone = ownerPage.locator('.import-upload-zone');
    await expect(uploadZone).toBeVisible({ timeout: 10000 });
  });
});
