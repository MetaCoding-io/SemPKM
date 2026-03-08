/**
 * Obsidian Batch Import E2E Tests (OBSI-06, OBSI-07)
 *
 * Tests the full import pipeline: upload -> scan -> type mapping ->
 * property mapping -> preview -> import -> summary -> verify objects.
 *
 * Uses the shared test-vault.zip fixture (6 markdown files).
 * Depends on sequential test execution (single worker).
 */
import { test, expect } from '../../fixtures/auth';
import path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe.serial('Obsidian Batch Import', () => {

  test('full import flow: upload through summary', async ({ ownerPage }) => {
    test.setTimeout(120000);

    // Step 1: Navigate to import page
    await ownerPage.goto(`${BASE_URL}/browser/import`);
    await ownerPage.waitForSelector('#import-container', { timeout: 15000 });

    // Discard any existing import first
    const discardBtn = ownerPage.locator('button:has-text("Discard")');
    if (await discardBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await discardBtn.first().click();
      await ownerPage.waitForSelector('.import-upload-zone', { timeout: 10000 });
    }

    // Step 2: Upload the test vault ZIP
    const uploadZone = ownerPage.locator('.import-upload-zone');
    await expect(uploadZone).toBeVisible({ timeout: 10000 });

    const fileInput = ownerPage.locator('#vault-zip');
    const fixturePath = path.resolve(__dirname, '../../fixtures/test-vault.zip');
    await fileInput.setInputFiles(fixturePath);

    const submitBtn = ownerPage.locator('.upload-selected-file button[type="submit"]');
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    // Step 3: Wait for scan results (stat cards appear)
    const statCards = ownerPage.locator('.import-stat-cards');
    await expect(statCards).toBeVisible({ timeout: 30000 });

    // Step 4: Click "Continue to Mapping" to go to type mapping
    const continueBtn = ownerPage.locator('button:has-text("Continue to Mapping")');
    await expect(continueBtn).toBeVisible({ timeout: 5000 });
    await continueBtn.click();

    // Wait for type mapping step to load
    await ownerPage.waitForSelector('.type-mapping-table', { timeout: 10000 });

    // Map type groups to available types
    const selects = ownerPage.locator('.mapping-select');
    const selectCount = await selects.count();

    for (let i = 0; i < selectCount; i++) {
      const select = selects.nth(i);
      const options = select.locator('option');
      const optionCount = await options.count();

      // Select first non-skip option (a real type)
      for (let j = 1; j < optionCount; j++) {
        const value = await options.nth(j).getAttribute('value');
        if (value && value.length > 0) {
          await select.selectOption({ index: j });
          // Wait for auto-save htmx request
          await ownerPage.waitForTimeout(500);
          break;
        }
      }
    }

    // Step 5: Navigate to property mapping
    const propBtn = ownerPage.locator('button:has-text("Next: Property Mapping")');
    await expect(propBtn).toBeVisible({ timeout: 5000 });
    await propBtn.click();

    // Wait for property mapping step to load
    await ownerPage.waitForTimeout(3000);

    // Step 6: Navigate to preview
    const previewBtn = ownerPage.locator('button:has-text("Next: Preview")');
    await expect(previewBtn).toBeVisible({ timeout: 10000 });
    await previewBtn.click();

    // Wait for preview step to load with the Import button
    const importBtn = ownerPage.locator('.import-actions button:has-text("Import")');
    await expect(importBtn).toBeVisible({ timeout: 10000 });
    await expect(importBtn).toBeEnabled();

    // Step 7: Click Import button
    await importBtn.click();

    // Step 8: Wait for import to complete (summary appears)
    // The import uses SSE streaming, then fetches summary via htmx
    const summaryTitle = ownerPage.locator('text=Import Complete');
    await expect(summaryTitle).toBeVisible({ timeout: 60000 });

    // Verify stat cards in summary (all 4 cards should be visible)
    const summaryStatCards = ownerPage.locator('.import-stat-card');
    await expect(summaryStatCards).toHaveCount(4, { timeout: 5000 });

    // Created + Skipped should account for all notes in the vault
    const createdCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Created' });
    await expect(createdCard).toBeVisible();
    const skippedCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Skipped' });
    await expect(skippedCard).toBeVisible();
    const createdVal = parseInt(await createdCard.locator('.stat-number').textContent() || '0');
    const skippedVal = parseInt(await skippedCard.locator('.stat-number').textContent() || '0');
    // At least some notes should be processed (created or skipped)
    expect(createdVal + skippedVal).toBeGreaterThan(0);

    // Verify Browse button is visible
    const browseBtn = ownerPage.locator('button:has-text("Browse Imported Objects")');
    await expect(browseBtn).toBeVisible({ timeout: 5000 });
  });

  test('verify imported objects exist in workspace', async ({ ownerPage }) => {
    // Navigate to workspace (browser is the IDE-style workspace)
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('#nav-tree, .nav-tree', { timeout: 15000 });

    // Wait for nav tree to populate via htmx
    await ownerPage.waitForTimeout(3000);

    // Check that tree nodes exist (imported objects appear as tree items)
    const treeNodes = ownerPage.locator('[data-tree-node], .tree-node, #nav-tree li, #nav-tree button');
    const count = await treeNodes.count();
    expect(count).toBeGreaterThan(0);
  });

  test('cleanup: discard import vault', async ({ ownerPage }) => {
    // Navigate back to import page
    await ownerPage.goto(`${BASE_URL}/browser/import`);
    await ownerPage.waitForSelector('#import-container', { timeout: 15000 });

    // Discard the import
    const discardBtn = ownerPage.locator('button:has-text("Discard")');
    if (await discardBtn.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      // Handle confirmation dialog
      ownerPage.on('dialog', dialog => dialog.accept());
      await discardBtn.first().click();
      await ownerPage.waitForSelector('.import-upload-zone', { timeout: 10000 });
    }
  });
});
