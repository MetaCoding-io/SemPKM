/**
 * Named Layout Save/Restore E2E Tests
 *
 * Tests the window.SemPKMLayouts API for saving, listing, restoring,
 * and removing named workspace layouts. Also verifies layout commands
 * exist in the command palette.
 *
 * Uses dockview helpers (openObjectTab, getTabCount) for panel state assertions.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { openObjectTab, getTabCount } from '../../helpers/dockview';
import { waitForWorkspace } from '../../helpers/wait-for';

test.describe('Named Layouts', () => {
  test('SemPKMLayouts API is available on window', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const apiAvailable = await ownerPage.evaluate(() => {
      const layouts = (window as any).SemPKMLayouts;
      if (!layouts) return false;
      return (
        typeof layouts.save === 'function' &&
        typeof layouts.restore === 'function' &&
        typeof layouts.remove === 'function' &&
        typeof layouts.list === 'function'
      );
    });
    expect(apiAvailable).toBe(true);
  });

  test('save and list named layout', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a tab to create some state
    await openObjectTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);

    // Save a named layout
    const saveResult = await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.save('Test Layout E2E');
    });
    expect(saveResult).toBe(true);

    // List layouts and verify our layout is present
    const layouts = await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.list();
    });
    const found = layouts.find((l: any) => l.name === 'Test Layout E2E');
    expect(found).toBeDefined();
    expect(found.savedAt).toBeTruthy();

    // Clean up
    await ownerPage.evaluate(() => {
      (window as any).SemPKMLayouts.remove('Test Layout E2E');
    });
  });

  test('restore named layout', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open two object tabs to create layout state
    await openObjectTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await openObjectTab(ownerPage, SEED.notes.kickoff.iri, SEED.notes.kickoff.title);

    // Save the layout
    await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.save('Restore Test E2E');
    });

    // Close all panels
    await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      if (dv) {
        const panels = [...dv.panels];
        panels.forEach((p: any) => p.api.close());
      }
    });
    await ownerPage.waitForTimeout(500);

    // Verify panels are closed
    const countAfterClose = await getTabCount(ownerPage);
    expect(countAfterClose).toBe(0);

    // Restore the layout
    const result = await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.restore('Restore Test E2E');
    });

    // Wait for layout restore + content load
    await ownerPage.waitForTimeout(2000);

    expect(result.success).toBe(true);

    // Panels should be restored (count > 0)
    const countAfterRestore = await getTabCount(ownerPage);
    expect(countAfterRestore).toBeGreaterThan(0);

    // Clean up
    await ownerPage.evaluate(() => {
      (window as any).SemPKMLayouts.remove('Restore Test E2E');
    });
  });

  test('remove named layout', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Save a layout to delete
    await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.save('Delete Test E2E');
    });

    // Verify it exists
    const beforeList = await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.list();
    });
    expect(beforeList.some((l: any) => l.name === 'Delete Test E2E')).toBe(true);

    // Remove it
    await ownerPage.evaluate(() => {
      (window as any).SemPKMLayouts.remove('Delete Test E2E');
    });

    // Verify it's gone
    const afterList = await ownerPage.evaluate(() => {
      return (window as any).SemPKMLayouts.list();
    });
    expect(afterList.some((l: any) => l.name === 'Delete Test E2E')).toBe(false);
  });

  test('layout commands exist in command palette', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.keyboard.press('Control+k');
    await ownerPage.waitForTimeout(500);

    const hasCommands = await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      if (!ninja || !ninja.data) return { saveAs: false, restore: false };
      return {
        saveAs: ninja.data.some(
          (d: any) => d.id === 'layout-save-as' && d.section === 'Layout',
        ),
        restore: ninja.data.some(
          (d: any) => d.id === 'layout-restore' && d.section === 'Layout',
        ),
      };
    });
    expect(hasCommands.saveAs).toBe(true);
    expect(hasCommands.restore).toBe(true);
  });
});
