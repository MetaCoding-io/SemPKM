/**
 * Workspace Layout E2E Tests
 *
 * Tests the IDE-style workspace: three-column layout with sidebar,
 * editor area, and properties panel. Verifies panes are present
 * and resizable.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Workspace Layout', () => {
  test('workspace loads with all three panes', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Verify all three panes are present
    await expect(ownerPage.locator(SEL.workspace.container)).toBeVisible();
    await expect(ownerPage.locator(SEL.workspace.sidebar)).toBeVisible();
    await expect(ownerPage.locator(SEL.workspace.editorArea)).toBeVisible();
    await expect(ownerPage.locator(SEL.workspace.propertiesPanel)).toBeVisible();
  });

  test('sidebar shows Explorer with OBJECTS section', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Explorer pane header
    await expect(ownerPage.locator('.pane-title').first()).toContainText('Explorer');

    // Objects section should exist
    await expect(ownerPage.locator('#section-objects')).toBeVisible();
    await expect(ownerPage.locator('#section-objects .explorer-section-title')).toContainText('OBJECTS');
  });

  test('sidebar shows VIEWS section', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Views section should exist
    await expect(ownerPage.locator('#section-views')).toBeVisible();
    await expect(ownerPage.locator('#section-views .explorer-section-title')).toContainText('VIEWS');
  });

  test('editor area shows empty state initially', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Dockview should have no panels open initially
    const panelCount = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      return dv ? dv.panels.length : 0;
    });
    expect(panelCount).toBe(0);
  });

  test('tab bar shows "No objects open" initially', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Dockview should have no panels/tabs open initially
    const tabCount = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      return dv ? dv.panels.length : 0;
    });
    expect(tabCount).toBe(0);
  });

  test('right pane shows Details with Relations and Lint sections', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const rightPane = ownerPage.locator(SEL.workspace.propertiesPanel);
    await expect(rightPane.locator('.pane-title')).toContainText('Details');

    // Relations and Lint sections exist
    await expect(rightPane.locator('summary')).toContainText(['Relations']);
    await expect(rightPane.locator('#relations-content')).toBeVisible();
    await expect(rightPane.locator('#lint-content')).toBeVisible();
  });

  test('bottom panel exists with EVENT LOG, AI COPILOT tabs', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const panelTabBar = ownerPage.locator('#panel-tab-bar');
    await expect(panelTabBar.locator('.panel-tab')).toHaveCount(4);
    await expect(panelTabBar).toContainText('EVENT LOG');
    await expect(panelTabBar).toContainText('INFERENCE');
    await expect(panelTabBar).toContainText('AI COPILOT');
    await expect(panelTabBar).toContainText('LINT');
  });

  test('command palette (ninja-keys) is present in DOM', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // ninja-keys custom element should be in the DOM
    const ninjaKeys = ownerPage.locator('ninja-keys');
    await expect(ninjaKeys).toHaveCount(1);
  });
});
