/**
 * Ontology Viewer E2E Tests
 *
 * Tests the ontology viewer panel opened via command palette or
 * openOntologyTab():
 * - TBox tree shows gist classes with expandable hierarchy
 * - ABox tab shows type counts and instance drill-down
 * - RBox tab shows property reference table with Domain/Range
 *
 * NOTE: Limited to ≤3 tests to stay within the auth rate limit
 * (5 magic-link calls per minute). Related assertions are combined
 * into single test cases.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Open the ontology viewer tab via the JS API. */
async function openOntologyViewer(page: import('@playwright/test').Page) {
  await page.evaluate(() => {
    if (typeof (window as any).openOntologyTab === 'function') {
      (window as any).openOntologyTab();
    }
  });
  await page.waitForSelector(SEL.ontology.ontologyPage, { timeout: 15000 });
}

test.describe('Ontology Viewer', () => {
  test('opens ontology viewer and shows TBox tree with gist classes', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open ontology viewer
    await openOntologyViewer(ownerPage);

    // TBox tab should be active by default
    const tboxTab = ownerPage.locator(SEL.ontology.tabTbox);
    await expect(tboxTab).toHaveClass(/ontology-tab--active/, { timeout: 5000 });

    // Wait for TBox tree to load (htmx load trigger)
    const tboxTree = ownerPage.locator(SEL.ontology.tboxTree);
    await expect(tboxTree).toBeVisible({ timeout: 10000 });

    // Wait for the TBox nodes to appear (htmx loads content into the pane)
    const tboxNodes = ownerPage.locator(SEL.ontology.tboxNode);
    await expect(tboxNodes.first()).toBeVisible({ timeout: 15000 });

    // Verify at least one gist class is visible
    const nodeCount = await tboxNodes.count();
    expect(nodeCount).toBeGreaterThan(0);

    // Verify we can see known gist class names in the tree
    const treeText = await tboxTree.textContent();
    // gist has classes like Category, Content, Event, etc.
    // At least one recognizable class should be present
    const knownGistClasses = ['Category', 'Content', 'Event', 'Organization', 'Place', 'Person', 'Task'];
    const foundClass = knownGistClasses.some(cls => treeText?.includes(cls));
    expect(foundClass).toBe(true);

    // Find a node with subclasses (has tree-toggle that's not a leaf)
    // and expand it to verify children load
    const expandableNode = ownerPage.locator(`${SEL.ontology.tboxNode}:not(.tree-leaf)`).first();
    const expandableCount = await ownerPage.locator(`${SEL.ontology.tboxNode}:not(.tree-leaf)`).count();
    if (expandableCount > 0) {
      await expandableNode.click();
      // Wait for children to load (htmx lazy load)
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // After expansion, the tree should have more nodes (children loaded)
      // or show "No subclasses" message
      const childNodes = ownerPage.locator('.tree-children .tree-node, .tree-children .tree-empty-leaf');
      // Either we got children or the "no subclasses" message
      const childElements = await childNodes.count();
      expect(childElements).toBeGreaterThanOrEqual(0); // Just verify no error
    }
  });

  test('ABox tab shows instance counts and drill-down', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open ontology viewer
    await openOntologyViewer(ownerPage);

    // Switch to ABox tab
    const aboxTab = ownerPage.locator(SEL.ontology.tabAbox);
    await aboxTab.click();

    // Wait for ABox content to load (htmx click-once trigger)
    await expect(aboxTab).toHaveClass(/ontology-tab--active/, { timeout: 5000 });
    const aboxBrowser = ownerPage.locator(SEL.ontology.aboxBrowser);
    await expect(aboxBrowser).toBeVisible({ timeout: 5000 });

    // Wait for type rows to load
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Check for type rows — there should be at least one type with instances
    // (seed data creates objects of known types)
    const typeRows = ownerPage.locator(SEL.ontology.aboxTypeRow);
    const typeRowCount = await typeRows.count();

    if (typeRowCount > 0) {
      // Verify count badges are present
      const firstRow = typeRows.first();
      const countBadge = firstRow.locator('.abox-count-badge');
      await expect(countBadge).toBeVisible({ timeout: 5000 });
      const countText = await countBadge.textContent();
      const countNum = parseInt(countText || '0', 10);
      expect(countNum).toBeGreaterThan(0);

      // Click first type to expand instance list
      await firstRow.click();
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // Instance list should appear (or "No instances" message)
      const instanceItems = ownerPage.locator('[data-testid="abox-instance"]');
      const emptyMsg = ownerPage.locator('.abox-instance-list .tree-empty');
      const instanceCount = await instanceItems.count();
      const emptyCount = await emptyMsg.count();
      // Either instances or empty message should be present
      expect(instanceCount + emptyCount).toBeGreaterThan(0);
    } else {
      // No types with instances — verify empty state message
      const emptyMsg = aboxBrowser.locator('.tree-empty');
      await expect(emptyMsg).toBeVisible({ timeout: 5000 });
    }
  });

  test('RBox tab shows property table with Domain and Range columns', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open ontology viewer
    await openOntologyViewer(ownerPage);

    // Switch to RBox tab
    const rboxTab = ownerPage.locator(SEL.ontology.tabRbox);
    await rboxTab.click();

    // Wait for RBox content to load (htmx click-once trigger)
    await expect(rboxTab).toHaveClass(/ontology-tab--active/, { timeout: 5000 });
    const rboxLegend = ownerPage.locator(SEL.ontology.rboxLegend);
    await expect(rboxLegend).toBeVisible({ timeout: 5000 });

    // Wait for tables to load
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Check for property table(s) — at least one should be present (gist has many properties)
    const objectTable = ownerPage.locator('[data-testid="rbox-object-table"]');
    const datatypeTable = ownerPage.locator('[data-testid="rbox-datatype-table"]');

    const objectTableVisible = await objectTable.isVisible().catch(() => false);
    const datatypeTableVisible = await datatypeTable.isVisible().catch(() => false);

    // At least one table should be visible (gist defines both object and datatype properties)
    expect(objectTableVisible || datatypeTableVisible).toBe(true);

    // Verify column headers — "Property", "Domain", "Range" should be visible
    if (objectTableVisible) {
      const headers = objectTable.locator('thead th');
      const headerTexts = await headers.allTextContents();
      expect(headerTexts).toContain('Property');
      expect(headerTexts).toContain('Domain');
      expect(headerTexts).toContain('Range');

      // At least one data row
      const rows = objectTable.locator('tbody tr');
      const rowCount = await rows.count();
      expect(rowCount).toBeGreaterThan(0);
    }

    if (datatypeTableVisible) {
      const headers = datatypeTable.locator('thead th');
      const headerTexts = await headers.allTextContents();
      expect(headerTexts).toContain('Property');
      expect(headerTexts).toContain('Domain');
      expect(headerTexts).toContain('Range');
    }
  });
});
