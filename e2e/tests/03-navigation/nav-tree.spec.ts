/**
 * Navigation Tree E2E Tests
 *
 * Tests the left sidebar navigation tree: type sections,
 * lazy-loading object children, clicking objects to open tabs.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Navigation Tree', () => {
  test('nav tree shows type nodes from Basic PKM model', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // The nav tree should have type nodes
    const navTree = ownerPage.locator(SEL.nav.tree);
    await expect(navTree).toBeVisible();

    const typeNodes = navTree.locator(SEL.nav.section);
    const count = await typeNodes.count();
    expect(count).toBeGreaterThanOrEqual(4); // Note, Concept, Project, Person
  });

  test('clicking type node lazy-loads children', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Click the first type node to expand it
    const firstTypeNode = ownerPage.locator(SEL.nav.section).first();
    await firstTypeNode.click();
    await waitForIdle(ownerPage);

    // Children container should be populated (htmx swaps content in)
    // The tree-children div should no longer be empty
    const childrenContainer = ownerPage.locator('.tree-children').first();
    // Wait a moment for htmx to load the children
    await ownerPage.waitForTimeout(2000);

    const content = await childrenContainer.innerHTML();
    // Should have loaded some content (tree items or empty state)
    expect(content.length).toBeGreaterThan(0);
  });

  test('type nodes have Lucide icons', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Each type node should have an icon
    const treeIcons = ownerPage.locator(`${SEL.nav.section} .tree-node-icon, ${SEL.nav.section} [data-lucide]`);
    const iconCount = await treeIcons.count();
    expect(iconCount).toBeGreaterThanOrEqual(4);
  });

  test('clicking an object node opens it in the editor', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Click a type node to expand
    const firstTypeNode = ownerPage.locator(SEL.nav.section).first();
    await firstTypeNode.click();
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    // Look for loaded tree item links
    const treeItems = ownerPage.locator('.tree-leaf, .tree-item, [data-testid="nav-item"]');
    const itemCount = await treeItems.count();

    if (itemCount > 0) {
      // Click first tree item to open it
      await treeItems.first().click();
      await waitForIdle(ownerPage);

      // Tab bar should now show a tab (not empty state)
      const tabBar = ownerPage.locator(SEL.workspace.tabBar);
      await expect(tabBar).not.toContainText('No objects open', { timeout: 10000 });
    }
  });

  test('section collapse/expand toggle works', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const objectsSection = ownerPage.locator('#section-objects');

    // Section should start expanded
    await expect(objectsSection).toHaveClass(/expanded/);

    // Click header to collapse
    await objectsSection.locator('.explorer-section-header').click();
    await expect(objectsSection).not.toHaveClass(/expanded/);

    // Click again to expand
    await objectsSection.locator('.explorer-section-header').click();
    await expect(objectsSection).toHaveClass(/expanded/);
  });
});
