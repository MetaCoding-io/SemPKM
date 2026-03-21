/**
 * Notion Import E2E Tests (NOTION-01, NOTION-02, NOTION-03)
 *
 * Tests the full 7-step Notion import wizard:
 * upload → scan → type mapping → property mapping → relation mapping
 * → preview → execute → summary.
 *
 * Uses the synthetic notion-export.zip fixture (2 databases, 1 standalone page).
 * Depends on sequential test execution (single worker).
 */
import { test, expect } from '../../fixtures/auth';
import path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe.serial('Notion Import Wizard', () => {

  test('full import flow: upload through summary', async ({ ownerPage }) => {
    test.setTimeout(120_000);

    // Step 1: Navigate to the Notion import page
    await ownerPage.goto(`${BASE_URL}/browser/notion/import`);
    await ownerPage.waitForSelector('#import-container', { timeout: 15_000 });

    // Idempotent cleanup — discard any previous import
    const discardBtn = ownerPage.locator('button:has-text("Discard")');
    if (await discardBtn.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      ownerPage.once('dialog', dialog => dialog.accept());
      await discardBtn.first().click();
      await ownerPage.waitForSelector('.import-upload-zone', { timeout: 10_000 });
    }

    // Step 2: Upload the Notion export ZIP
    const uploadZone = ownerPage.locator('.import-upload-zone');
    await expect(uploadZone).toBeVisible({ timeout: 10_000 });

    const fileInput = ownerPage.locator('#notion-zip');
    const fixturePath = path.resolve(__dirname, '../../fixtures/notion-export.zip');
    await fileInput.setInputFiles(fixturePath);

    // Click "Upload & Scan" submit button
    const submitBtn = ownerPage.locator('.upload-selected-file button[type="submit"]');
    await expect(submitBtn).toBeVisible({ timeout: 5_000 });
    await submitBtn.click();

    // Step 3: Wait for scan results (stat cards appear)
    const statCards = ownerPage.locator('.import-stat-cards');
    await expect(statCards).toBeVisible({ timeout: 30_000 });

    // Step 4: Click "Continue to Type Mapping"
    const continueBtn = ownerPage.locator('button:has-text("Continue to Type Mapping")');
    await expect(continueBtn).toBeVisible({ timeout: 5_000 });
    await continueBtn.click();

    // Wait for type mapping table
    await ownerPage.waitForSelector('.type-mapping-table', { timeout: 10_000 });

    // Map each database to the first non-skip type option
    const selects = ownerPage.locator('.mapping-select');
    const selectCount = await selects.count();

    for (let i = 0; i < selectCount; i++) {
      const select = selects.nth(i);
      const options = select.locator('option');
      const optionCount = await options.count();

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

    // Step 5: Navigate to Property Mapping
    const propBtn = ownerPage.locator('button:has-text("Next: Property Mapping")');
    await expect(propBtn).toBeVisible({ timeout: 5_000 });
    await propBtn.click();
    await ownerPage.waitForTimeout(3_000);

    // Step 6: Navigate to Relation Mapping
    const relBtn = ownerPage.locator('button:has-text("Next: Relation Mapping")');
    await expect(relBtn).toBeVisible({ timeout: 10_000 });
    await relBtn.click();
    await ownerPage.waitForTimeout(3_000);

    // Step 7: Navigate to Preview
    const previewBtn = ownerPage.locator('button:has-text("Next: Preview")');
    await expect(previewBtn).toBeVisible({ timeout: 10_000 });
    await previewBtn.click();

    // Wait for preview content and Import button
    const importBtn = ownerPage.locator('.import-actions button:has-text("Import")');
    await expect(importBtn).toBeVisible({ timeout: 10_000 });
    await expect(importBtn).toBeEnabled();

    // Step 8: Click Import — triggers SSE-driven execution
    await importBtn.click();

    // Wait for "Import Complete" (SSE streams progress then htmx loads summary)
    const summaryTitle = ownerPage.locator('text=Import Complete');
    await expect(summaryTitle).toBeVisible({ timeout: 60_000 });

    // Verify all 4 stat cards in the summary
    const summaryStatCards = ownerPage.locator('.import-stat-card');
    await expect(summaryStatCards).toHaveCount(4, { timeout: 5_000 });

    // Verify Created count > 0 (objects were actually imported)
    const createdCard = ownerPage.locator('.import-stat-card').filter({ hasText: 'Created' });
    await expect(createdCard).toBeVisible();
    const createdVal = parseInt(await createdCard.locator('.stat-number').textContent() || '0');
    expect(createdVal).toBeGreaterThan(0);

    // Verify "Browse Imported Objects" button is visible
    const browseBtn = ownerPage.locator('button:has-text("Browse Imported Objects")');
    await expect(browseBtn).toBeVisible({ timeout: 5_000 });
  });

  test('verify imported objects exist in workspace', async ({ ownerPage }) => {
    // Navigate to the workspace browser
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('#nav-tree, .nav-tree', { timeout: 15_000 });

    // Wait for nav tree to populate via htmx
    await ownerPage.waitForTimeout(3_000);

    // Check that tree nodes exist (imported objects appear as tree items)
    const treeNodes = ownerPage.locator('[data-tree-node], .tree-node, #nav-tree li, #nav-tree button');
    const count = await treeNodes.count();
    expect(count).toBeGreaterThan(0);
  });

  test('cleanup: discard import', async ({ ownerPage }) => {
    // Navigate back to Notion import page
    await ownerPage.goto(`${BASE_URL}/browser/notion/import`);
    await ownerPage.waitForSelector('#import-container', { timeout: 15_000 });

    // Discard the import if Discard button is visible
    const discardBtn = ownerPage.locator('button:has-text("Discard")');
    if (await discardBtn.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      ownerPage.once('dialog', dialog => dialog.accept());
      await discardBtn.first().click();
      await ownerPage.waitForSelector('.import-upload-zone', { timeout: 10_000 });
    }
  });
});
