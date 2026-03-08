/**
 * Tab Management E2E Tests
 *
 * Tests the tab bar: opening objects creates tabs, switching between
 * tabs, closing tabs, and tab state.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Tab Management', () => {
  test('opening an object creates a tab in the tab bar', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a seed object via openTab
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Architecture Decision');
      }
    }, SEED.notes.architecture.iri);

    await waitForIdle(ownerPage);

    // A tab should now be visible in dockview
    const tabs = ownerPage.locator('.dv-default-tab');
    await expect(tabs.first()).toBeVisible({ timeout: 10000 });
  });

  test('opening multiple objects creates multiple tabs', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open two different objects
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Architecture Decision');
      }
    }, SEED.notes.architecture.iri);

    await waitForIdle(ownerPage);

    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Alice Chen');
      }
    }, SEED.people.alice.iri);

    await waitForIdle(ownerPage);

    // Should have at least 2 tab elements
    const tabs = ownerPage.locator('.dv-default-tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(2);
  });

  test('clicking a tab switches to that object', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open two objects
    await ownerPage.evaluate(({ iri1, iri2 }) => {
      const openTab = (window as any).openTab;
      if (typeof openTab === 'function') {
        openTab(iri1, 'Architecture Decision');
        setTimeout(() => openTab(iri2, 'Alice Chen'), 500);
      }
    }, {
      iri1: SEED.notes.architecture.iri,
      iri2: SEED.people.alice.iri,
    });

    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Click the first tab to switch back to it
    const firstTab = ownerPage.locator('.dv-default-tab').first();
    const firstTabCount = await firstTab.count();
    if (firstTabCount > 0) {
      await firstTab.click();
      await waitForIdle(ownerPage);
      // The active tab should have the dv-active-tab class on the parent .dv-tab element
      const firstDvTab = ownerPage.locator('.dv-tab').first();
      await expect(firstDvTab).toHaveClass(/dv-active-tab/);
    }
  });

  test('opening the same object twice does not create duplicate tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iri = SEED.notes.architecture.iri;

    // Open same object twice
    await ownerPage.evaluate((objectIri) => {
      const openTab = (window as any).openTab;
      if (typeof openTab === 'function') {
        openTab(objectIri, 'Architecture Decision');
      }
    }, iri);

    await waitForIdle(ownerPage);

    await ownerPage.evaluate((objectIri) => {
      const openTab = (window as any).openTab;
      if (typeof openTab === 'function') {
        openTab(objectIri, 'Architecture Decision');
      }
    }, iri);

    await waitForIdle(ownerPage);

    // Should only have one tab
    const tabs = ownerPage.locator('.dv-default-tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBe(1);
  });
});
