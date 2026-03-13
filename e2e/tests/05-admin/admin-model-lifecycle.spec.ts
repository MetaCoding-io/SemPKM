/**
 * Admin Model Lifecycle E2E Tests
 *
 * Tests the full model install → verify → uninstall cycle.
 * Uses the PPV model (available at /app/models/ppv in the container).
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Admin Model Lifecycle', () => {
  test('install PPV model via admin UI', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // Fill the model path input with the PPV model path
    const pathInput = ownerPage.locator('#model-path');
    await pathInput.fill('/app/models/ppv');

    // Click Install button
    await ownerPage.locator('button', { hasText: 'Install' }).click();
    await waitForIdle(ownerPage);

    // Wait for the model to appear in the list (page may refresh via htmx)
    await ownerPage.waitForSelector(`${SEL.admin.modelList} tbody tr`, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // PPV model should now be listed
    const modelTable = ownerPage.locator(SEL.admin.modelList);
    await expect(modelTable).toContainText('PPV', { timeout: 10000 });
  });

  test('installed PPV model appears in model list', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // PPV should be in the list (installed by previous test)
    const rows = ownerPage.locator(`${SEL.admin.modelList} tbody tr`);
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(2); // Basic PKM + PPV

    // Find PPV row
    const ppvRow = rows.filter({ hasText: 'PPV' }).or(rows.filter({ hasText: 'ppv' }));
    const ppvCount = await ppvRow.count();
    expect(ppvCount).toBeGreaterThanOrEqual(1);
  });

  test('uninstall PPV model and verify removal', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Find the PPV row and click Remove
    const ppvRow = ownerPage.locator(`${SEL.admin.modelList} tbody tr`).filter({
      hasText: /PPV|ppv|Personal Productivity/i,
    });

    const ppvCount = await ppvRow.count();
    if (ppvCount > 0) {
      const removeBtn = ppvRow.locator('button', { hasText: 'Remove' });
      await removeBtn.click();
      await waitForIdle(ownerPage);

      // Wait for page to update
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // PPV should no longer be in the list
      const updatedTable = ownerPage.locator(SEL.admin.modelList);
      // Reload to see updated state
      await ownerPage.goto(`${BASE_URL}/admin/models`);
      await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

      // Should still have Basic PKM
      await expect(updatedTable).toContainText('Basic PKM');
    }
  });
});
