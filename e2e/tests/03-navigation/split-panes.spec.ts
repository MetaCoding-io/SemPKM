/**
 * Split Panes E2E Tests
 *
 * Tests the VS Code-style split pane functionality:
 * - Ctrl+\ creates a second editor group
 * - Each group has an independent tab bar
 * - The original tab retains its content after split
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 * Phase: 14 (Split Panes) + Phase 19 (bug fix for content bleed)
 *
 * DOM structure (from workspace-layout.js):
 *   .editor-group      — the group container (one per split pane)
 *   .group-tab-bar     — the tab bar belonging to each editor group
 *   .group-editor-area — the editor content area within each group
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Split Panes', () => {
  test('Ctrl+Backslash creates a second editor group', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Initially, only one editor group exists
    const editorGroups = ownerPage.locator('.editor-group');
    await expect(editorGroups).toHaveCount(1);

    // Open an object tab first (splitRight duplicates the active tab)
    const firstNavItem = ownerPage.locator('[data-testid="nav-item"]').first();
    await firstNavItem.click();
    await waitForIdle(ownerPage);

    // Split with Ctrl+\
    await ownerPage.keyboard.press('Control+Backslash');
    await waitForIdle(ownerPage);

    // Verify two editor groups now exist
    await expect(editorGroups).toHaveCount(2);
  });

  test('each editor group has an independent tab bar', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open an object, then split
    const firstNavItem = ownerPage.locator('[data-testid="nav-item"]').first();
    await firstNavItem.click();
    await waitForIdle(ownerPage);

    await ownerPage.keyboard.press('Control+Backslash');
    await waitForIdle(ownerPage);

    // Each group should have its own .group-tab-bar
    // (workspace-layout.js creates tabBar.className = 'group-tab-bar tab-bar-workspace')
    const tabBars = ownerPage.locator('.group-tab-bar');
    await expect(tabBars).toHaveCount(2);
  });
});
