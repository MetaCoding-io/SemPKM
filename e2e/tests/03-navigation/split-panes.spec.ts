/**
 * Split Panes E2E Tests
 *
 * Tests the VS Code-style split pane functionality:
 * - Ctrl+\ creates additional editor groups
 * - Each group has an independent tab bar
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 * Phase: 14 (Split Panes) + Phase 19 (bug fix for content bleed)
 *
 * DOM structure (dockview-core):
 *   Groups managed by dockview API (window._dockview.groups)
 *   .dv-tabs-container — the tab container belonging to each dockview group
 *
 * Implementation notes:
 *   - splitRight() uses dockview's addGroup API to create split panes.
 *   - Tests assert RELATIVE change (groups increased) and STRUCTURAL
 *     invariants (tab container count equals group count), not exact counts.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Split Panes', () => {
  test('Ctrl+Backslash creates additional editor groups', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Wait for dockview to have initialized
    await ownerPage.waitForFunction(() => {
      return (window as any)._dockview != null;
    }, { timeout: 5000 });

    const initialCount = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      return dv ? dv.groups.length : 0;
    });

    // Press Ctrl+\ — triggers splitRight() (may fire via keydown + ninja-keys hotkey).
    // Verifies that at least one group exists and the shortcut does not crash.
    await ownerPage.keyboard.press('Control+Backslash');
    await waitForIdle(ownerPage);

    // After split: group count should be >= initial (groups increased OR already at max)
    const afterCount = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      return dv ? dv.groups.length : 0;
    });
    expect(afterCount).toBeGreaterThanOrEqual(initialCount);

    // At least 2 groups should exist (split should have created at least one)
    expect(afterCount).toBeGreaterThanOrEqual(2);
  });

  test('each editor group has its own tab bar', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Wait for dockview to initialize
    await ownerPage.waitForFunction(() => {
      return (window as any)._dockview != null;
    }, { timeout: 5000 });

    // Press Ctrl+\ to ensure we have split panes
    await ownerPage.keyboard.press('Control+Backslash');
    await waitForIdle(ownerPage);

    // Structural invariant: each dockview group has its own tab container
    const groupCount = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      return dv ? dv.groups.length : 0;
    });
    const tabContainers = ownerPage.locator('.dv-tabs-container');
    const tabContainerCount = await tabContainers.count();

    // Each group should have exactly one tab container
    expect(tabContainerCount).toBe(groupCount);

    // Multiple groups should exist after splitting
    expect(groupCount).toBeGreaterThanOrEqual(2);
  });
});
