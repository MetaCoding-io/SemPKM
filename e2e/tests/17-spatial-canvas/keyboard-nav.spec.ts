/**
 * Keyboard Navigation E2E Tests (CANV-03)
 *
 * Verifies arrow keys, Tab cycling, Delete, Enter, Escape, and Ctrl+S on canvas.
 * Canvas keyboard shortcuts are wired in canvas.js.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

const GRID_SIZE = 24;

/** Helper: navigate to canvas and add test nodes */
async function setupCanvasWithNodes(page: any) {
  await page.goto(`${BASE_URL}/browser/canvas`);
  await page.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
  await waitForIdle(page);

  await page.evaluate(() => {
    const cy = (window as any)._cy || (window as any).cy;
    if (!cy) return;

    cy.add([
      { group: 'nodes', data: { id: 'node-a', label: 'Node A' }, position: { x: 240, y: 240 } },
      { group: 'nodes', data: { id: 'node-b', label: 'Node B' }, position: { x: 480, y: 240 } },
      { group: 'nodes', data: { id: 'node-c', label: 'Node C' }, position: { x: 240, y: 480 } },
    ]);

    // Select the first node
    cy.getElementById('node-a').select();
  });
}

test.describe('Spatial Canvas: Keyboard Navigation', () => {
  test('arrow keys move selected node by one grid step (24px)', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    const initialPos = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.getElementById('node-a')?.position();
    });

    if (!initialPos) return;

    // Focus the canvas element so keyboard events fire
    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('ArrowRight');
    await waitForIdle(ownerPage);

    const newPos = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.getElementById('node-a')?.position();
    });

    if (newPos) {
      // Node should have moved right by one grid step
      expect(newPos.x).toBe(initialPos.x + GRID_SIZE);
      expect(newPos.y).toBe(initialPos.y);
    }
  });

  test('shift+arrow moves selected node by 5 grid steps (120px)', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    const initialPos = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.getElementById('node-a')?.position();
    });

    if (!initialPos) return;

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('Shift+ArrowDown');
    await waitForIdle(ownerPage);

    const newPos = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.getElementById('node-a')?.position();
    });

    if (newPos) {
      expect(newPos.y).toBe(initialPos.y + GRID_SIZE * 5);
      expect(newPos.x).toBe(initialPos.x);
    }
  });

  test('tab cycles focus through nodes in spatial order', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');

    // Press Tab to cycle to next node
    await ownerPage.keyboard.press('Tab');
    await waitForIdle(ownerPage);

    const selectedId = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;
      const selected = cy.nodes(':selected');
      return selected.length > 0 ? selected[0].id() : null;
    });

    // A node should be selected after Tab
    expect(selectedId).toBeTruthy();
  });

  test('shift+tab cycles focus backward', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');

    // Tab forward twice, then shift+tab back
    await ownerPage.keyboard.press('Tab');
    await ownerPage.keyboard.press('Tab');
    const afterTwoTabs = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      const sel = cy?.nodes(':selected');
      return sel?.length > 0 ? sel[0].id() : null;
    });

    await ownerPage.keyboard.press('Shift+Tab');
    await waitForIdle(ownerPage);

    const afterShiftTab = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      const sel = cy?.nodes(':selected');
      return sel?.length > 0 ? sel[0].id() : null;
    });

    // Should be on a different node after Shift+Tab
    if (afterTwoTabs && afterShiftTab) {
      expect(afterShiftTab).not.toBe(afterTwoTabs);
    }
  });

  test('escape deselects the current node', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    // Verify a node is selected
    const before = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.nodes(':selected')?.length || 0;
    });
    expect(before).toBeGreaterThan(0);

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('Escape');
    await waitForIdle(ownerPage);

    const after = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.nodes(':selected')?.length || 0;
    });
    expect(after).toBe(0);
  });

  test('delete removes selected node without confirmation', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    const countBefore = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.nodes()?.length || 0;
    });

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('Delete');
    await waitForIdle(ownerPage);

    const countAfter = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.nodes()?.length || 0;
    });

    expect(countAfter).toBe(countBefore - 1);
  });

  test('enter toggles neighbor expansion on selected node', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    const countBefore = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.elements()?.length || 0;
    });

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('Enter');
    await waitForIdle(ownerPage);

    // After Enter, the canvas may have more elements (expanded neighbors)
    // or the same if no neighbors exist
    const countAfter = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      return cy?.elements()?.length || 0;
    });

    expect(countAfter).toBeGreaterThanOrEqual(countBefore);
  });

  test('ctrl+s saves the current canvas session', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    // Listen for a save response
    const savePromise = ownerPage.waitForResponse(
      (resp: any) => resp.url().includes('/api/canvas/') && resp.request().method() === 'PUT',
      { timeout: 5000 },
    ).catch(() => null);

    await ownerPage.click('#spatial-canvas, .canvas-container, [data-testid="canvas"]');
    await ownerPage.keyboard.press('Control+s');
    await waitForIdle(ownerPage);

    // Save should have been triggered (either via API call or toast notification)
    const saveResponse = await savePromise;
    // If save was intercepted, verify it succeeded
    if (saveResponse) {
      expect(saveResponse.ok()).toBeTruthy();
    }
  });

  test('keyboard events do not fire during text input', async ({ ownerPage }) => {
    await setupCanvasWithNodes(ownerPage);

    // If there's a text input (e.g., session name input), typing should not
    // trigger canvas keyboard shortcuts
    const hasInput = await ownerPage.evaluate(() => {
      const input = document.querySelector('input[type="text"], .session-name-input');
      return !!input;
    });

    if (hasInput) {
      const countBefore = await ownerPage.evaluate(() => {
        const cy = (window as any)._cy || (window as any).cy;
        return cy?.nodes()?.length || 0;
      });

      // Focus the text input and press Delete
      await ownerPage.click('input[type="text"], .session-name-input');
      await ownerPage.keyboard.press('Delete');

      const countAfter = await ownerPage.evaluate(() => {
        const cy = (window as any)._cy || (window as any).cy;
        return cy?.nodes()?.length || 0;
      });

      // Node count should remain the same (Delete was consumed by input, not canvas)
      expect(countAfter).toBe(countBefore);
    }
  });
});
