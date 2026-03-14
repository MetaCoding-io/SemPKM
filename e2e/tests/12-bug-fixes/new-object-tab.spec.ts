/**
 * New-Object Tab Preservation E2E Tests
 *
 * Regression guard for the S04 fix: clicking "New Object" (showTypePicker)
 * must always open a fresh dockview tab, never overwrite an existing one.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('New Object Tab Preservation', () => {
  test('showTypePicker opens fresh tab without destroying existing tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a seed object tab
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await waitForIdle(ownerPage);

    // Assert the seed object tab is visible
    const seedTab = ownerPage.locator('.dv-default-tab', {
      hasText: SEED.notes.architecture.title,
    });
    await expect(seedTab).toBeVisible({ timeout: 10000 });

    // Record tab count before showTypePicker
    const tabsBefore = await ownerPage.locator('.dv-default-tab').count();
    expect(tabsBefore).toBeGreaterThanOrEqual(1);

    // Trigger showTypePicker — creates a temp "New Object" panel
    await ownerPage.evaluate(() => {
      (window as any).showTypePicker();
    });
    await waitForIdle(ownerPage);

    // Wait for the type picker content to load
    await ownerPage.waitForSelector('.type-picker', { timeout: 10000 });

    // Assert: the original seed object tab still exists in the tab bar
    await expect(seedTab).toBeVisible();

    // Assert: there are now at least 2 tabs (original + new-object temp)
    const tabsAfter = await ownerPage.locator('.dv-default-tab').count();
    expect(tabsAfter).toBeGreaterThanOrEqual(2);

    // Assert: a "New Object" tab exists
    const newObjectTab = ownerPage.locator('.dv-default-tab', {
      hasText: 'New Object',
    });
    await expect(newObjectTab).toBeVisible();
  });

  test('temp panel uses __new-object prefix and is trackable', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a seed object tab first
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await waitForIdle(ownerPage);

    // Trigger showTypePicker
    await ownerPage.evaluate(() => {
      (window as any).showTypePicker();
    });
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('.type-picker', { timeout: 10000 });

    // Assert: the temp panel has the __new-object- prefix in dockview
    const hasTempPanel = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      if (!dv || !dv.api) return false;
      return dv.api.panels.some(
        (p: any) => typeof p.id === 'string' && p.id.startsWith('__new-object-'),
      );
    });
    expect(hasTempPanel).toBe(true);

    // Assert: the temp panel can be closed programmatically
    // (verifies closeTab integration — objectCreated handler relies on this)
    const closedOk = await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      if (!dv || !dv.api) return false;
      const tempPanel = dv.api.panels.find(
        (p: any) => typeof p.id === 'string' && p.id.startsWith('__new-object-'),
      );
      if (!tempPanel) return false;
      try {
        (window as any).closeTab(tempPanel.id);
        return true;
      } catch { return false; }
    });
    expect(closedOk).toBe(true);
    await waitForIdle(ownerPage);

    // Assert: after closing the temp panel, no "New Object" tab remains
    const tempTabs = ownerPage.locator('.dv-default-tab', { hasText: 'New Object' });
    const tempCount = await tempTabs.count();
    expect(tempCount).toBe(0);

    // Assert: original seed object tab is still present
    const seedTab = ownerPage.locator('.dv-default-tab', {
      hasText: SEED.notes.architecture.title,
    });
    await expect(seedTab).toBeVisible();
  });
});
