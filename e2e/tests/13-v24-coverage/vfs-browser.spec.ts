/**
 * VFS Browser E2E Tests
 *
 * Tests the Virtual File System browser page: direct URL load, sidebar
 * navigation, model/type/object tree hierarchy with lazy-loading.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('VFS Browser', () => {
  test('VFS browser page loads from direct URL', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/vfs`);
    const container = ownerPage.locator('[data-testid="vfs-browser"]');
    await expect(container).toBeVisible({ timeout: 15000 });

    const treeBody = ownerPage.locator('#vfs-tree-body');
    await expect(treeBody).toBeVisible();
  });

  test('VFS browser loads from sidebar navigation', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

    // Click the VFS link in the sidebar
    const vfsLink = ownerPage.locator('a[href="/browser/vfs"]');
    await vfsLink.click();

    const container = ownerPage.locator('[data-testid="vfs-browser"]');
    await expect(container).toBeVisible({ timeout: 15000 });
  });

  test('VFS tree shows model nodes after loading', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/vfs`);
    await ownerPage.locator('[data-testid="vfs-browser"]').waitFor({ timeout: 15000 });

    // Wait for loading spinner to disappear and tree nodes to render
    await ownerPage.waitForFunction(
      () => {
        const body = document.getElementById('vfs-tree-body');
        if (!body) return false;
        return body.querySelectorAll('.vfs-tree-node').length > 0;
      },
      { timeout: 15000 },
    );

    // The tree should contain at least one node with "basic-pkm" text (model ID)
    const treeBody = ownerPage.locator('#vfs-tree-body');
    await expect(treeBody).toContainText('basic-pkm', { timeout: 10000 });
  });

  test('clicking a model node expands types', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/vfs`);
    await ownerPage.locator('[data-testid="vfs-browser"]').waitFor({ timeout: 15000 });

    // Wait for tree to load
    await ownerPage.waitForFunction(
      () => {
        const body = document.getElementById('vfs-tree-body');
        return body && body.querySelectorAll('.vfs-tree-node').length > 0;
      },
      { timeout: 15000 },
    );

    // The model node is auto-expanded (expanded: true in JS).
    // Type nodes should be visible as children of the model node.
    const treeBody = ownerPage.locator('#vfs-tree-body');

    // Verify at least one type label is visible (Note, Project, Concept, or Person)
    const typeLabels = treeBody.locator('.vfs-tree-label');
    const allLabels = await typeLabels.allTextContents();
    const typeNames = ['Note', 'Project', 'Concept', 'Person'];
    const foundTypes = typeNames.filter((t) => allLabels.some((l) => l.includes(t)));
    expect(foundTypes.length).toBeGreaterThanOrEqual(1);
  });

  test('clicking a type node shows objects', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/vfs`);
    await ownerPage.locator('[data-testid="vfs-browser"]').waitFor({ timeout: 15000 });

    // Wait for tree to load
    await ownerPage.waitForFunction(
      () => {
        const body = document.getElementById('vfs-tree-body');
        return body && body.querySelectorAll('.vfs-tree-node').length > 0;
      },
      { timeout: 15000 },
    );

    // Find the type node for "Note" and expand it
    const treeBody = ownerPage.locator('#vfs-tree-body');
    const noteRow = treeBody.locator('.vfs-tree-row', { hasText: 'Note' }).first();
    await noteRow.click();
    await ownerPage.waitForTimeout(500);

    // After expanding, object file nodes should appear
    // Look for seed note titles in the tree
    const allLabels = await treeBody.locator('.vfs-tree-label').allTextContents();
    // At least one of the seed note titles should appear
    const hasNoteObject = allLabels.some(
      (l) =>
        l.includes('Architecture') ||
        l.includes('Kickoff') ||
        l.includes('Graph'),
    );
    expect(hasNoteObject).toBe(true);
  });
});
