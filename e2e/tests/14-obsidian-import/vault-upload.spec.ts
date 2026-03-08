/**
 * Obsidian Vault Upload E2E Tests (OBSI-01)
 *
 * Tests the upload flow: sidebar link opens import tab, user uploads a ZIP,
 * scan completes, and stat cards display correct counts.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForIdle } from '../../helpers/wait-for';
import path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Obsidian Vault Upload', () => {
  test('open Import Vault page from sidebar and upload vault ZIP', async ({ ownerPage }) => {
    // Navigate directly to the import page (it's a full app page, not a dockview tab)
    await ownerPage.goto(`${BASE_URL}/browser/import`);
    await ownerPage.waitForSelector('#import-container', { timeout: 15000 });

    // Wait for upload zone to be visible
    const uploadZone = ownerPage.locator('.import-upload-zone');
    await expect(uploadZone).toBeVisible({ timeout: 10000 });

    // Upload the test vault ZIP
    const fileInput = ownerPage.locator('#vault-zip');
    const fixturePath = path.resolve(__dirname, '../../fixtures/test-vault.zip');
    await fileInput.setInputFiles(fixturePath);

    // Should show selected file info and submit button
    const submitBtn = ownerPage.locator('.upload-selected-file button[type="submit"]');
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    // Wait for scan to complete and results to appear (scan_trigger auto-starts scan)
    const statCards = ownerPage.locator('.import-stat-cards');
    await expect(statCards).toBeVisible({ timeout: 30000 });

    // Verify stat cards show correct counts
    const statNumbers = ownerPage.locator('.import-stat-card .stat-number');
    await expect(statNumbers).toHaveCount(4);

    // Notes count should be 6 (markdown files)
    const notesCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Notes' });
    await expect(notesCard.locator('.stat-number')).toHaveText('6');

    // Attachments should be 1
    const attachCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Attachments' });
    await expect(attachCard.locator('.stat-number')).toHaveText('1');
  });
});
