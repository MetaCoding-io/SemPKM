/**
 * Explorer Mode Switching E2E Tests
 *
 * Tests the explorer mode dropdown and mode-switching behavior:
 * - Dropdown visible with three mode options, by-type default shows nav sections
 * - Switching to hierarchy shows placeholder content
 * - Switching to by-tag shows placeholder, switching back restores real tree
 * - Lazy expansion works after mode round-trip
 * - Multi-select state clears on mode switch
 *
 * NOTE: Limited to 5 tests to stay within the auth rate limit (5 magic-link
 * calls per minute). Tests are combined where logically related.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Explorer Mode Switching', () => {
  test('dropdown visible with three mode options and by-type default shows nav sections', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // --- Dropdown visibility and options ---
    const dropdown = ownerPage.locator(SEL.explorer.modeSelect);
    await expect(dropdown).toBeVisible();

    const options = dropdown.locator('option');
    await expect(options).toHaveCount(3);

    // Verify option values
    await expect(options.nth(0)).toHaveAttribute('value', 'by-type');
    await expect(options.nth(1)).toHaveAttribute('value', 'hierarchy');
    await expect(options.nth(2)).toHaveAttribute('value', 'by-tag');

    // Verify option labels
    await expect(options.nth(0)).toHaveText('By Type');
    await expect(options.nth(1)).toHaveText('Hierarchy');
    await expect(options.nth(2)).toHaveText('By Tag');

    // --- By-type is default with nav sections ---
    await expect(dropdown).toHaveValue('by-type');

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const sections = treeBody.locator(SEL.nav.section);
    const count = await sections.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Placeholder should NOT be present in by-type mode
    const placeholder = treeBody.locator(SEL.explorer.placeholder);
    await expect(placeholder).toHaveCount(0);
  });

  test('switching to hierarchy shows placeholder', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Switch to hierarchy mode
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'hierarchy');
    await waitForIdle(ownerPage);

    // Wait for the placeholder to appear
    const placeholder = ownerPage.locator(SEL.explorer.placeholder);
    await expect(placeholder).toBeVisible({ timeout: 5000 });

    // Placeholder should mention "Hierarchy"
    await expect(placeholder).toContainText('Hierarchy');

    // Nav sections from by-type should NOT be present
    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const sections = treeBody.locator(SEL.nav.section);
    await expect(sections).toHaveCount(0);
  });

  test('switching to by-tag shows placeholder and switching back restores real tree', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // --- Switch to by-tag ---
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-tag');
    await waitForIdle(ownerPage);

    const placeholder = ownerPage.locator(SEL.explorer.placeholder);
    await expect(placeholder).toBeVisible({ timeout: 5000 });
    await expect(placeholder).toContainText('Tag');

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const sections = treeBody.locator(SEL.nav.section);
    await expect(sections).toHaveCount(0);

    // --- Switch back to by-type ---
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-type');
    await waitForIdle(ownerPage);

    // Wait for nav sections to reappear
    await expect(sections.first()).toBeVisible({ timeout: 5000 });
    const count = await sections.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Placeholder should be gone
    await expect(placeholder).toHaveCount(0);
  });

  test('lazy expansion works after mode round-trip', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Switch to hierarchy then back to by-type
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'hierarchy');
    await waitForIdle(ownerPage);
    await expect(ownerPage.locator(SEL.explorer.placeholder)).toBeVisible({ timeout: 5000 });

    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-type');
    await waitForIdle(ownerPage);

    // Wait for type nodes to load
    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const typeNodes = treeBody.locator(SEL.nav.section);
    await expect(typeNodes.first()).toBeVisible({ timeout: 5000 });

    // Click the first type node to trigger lazy expansion
    await typeNodes.first().click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // The tree-children container should have content loaded
    const childrenContainer = treeBody.locator('.tree-children').first();
    const content = await childrenContainer.innerHTML();
    expect(content.length).toBeGreaterThan(0);
  });

  test('multi-select clears on mode switch', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // First expand a type node to get tree-leaf items
    const typeNodes = ownerPage.locator(SEL.explorer.treeBody).locator(SEL.nav.section);
    await expect(typeNodes.first()).toBeVisible({ timeout: 5000 });
    await typeNodes.first().click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Look for tree-leaf items (objects in the expanded type)
    const leafItems = ownerPage.locator('#section-objects .tree-leaf[data-iri]');
    const leafCount = await leafItems.count();

    if (leafCount >= 1) {
      // Ctrl+click to create a selection
      await leafItems.nth(0).click({ modifiers: ['ControlOrMeta'] });

      if (leafCount >= 2) {
        await leafItems.nth(1).click({ modifiers: ['ControlOrMeta'] });
      }

      // Selection badge should be visible
      const badge = ownerPage.locator('#selection-badge');
      await expect(badge).toBeVisible();

      // Switch mode — selection should clear
      await ownerPage.selectOption(SEL.explorer.modeSelect, 'hierarchy');
      await waitForIdle(ownerPage);

      // Selection badge should be hidden
      await expect(badge).not.toBeVisible();
    } else {
      // No items to select — skip the selection part but verify mode switch works
      test.skip(true, 'No tree-leaf items available for multi-select test');
    }
  });
});
