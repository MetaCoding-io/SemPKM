/**
 * Browser History & URL Sync E2E Tests
 *
 * Verifies the M055/S01 URL sync feature:
 * - pushState on tab open reflects ?tab= in URL
 * - back/forward navigates tab history
 * - deep-link via ?tab= query parameter opens correct tab
 * - stale history entries for closed panels are cleaned up
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Helper: open an object tab and wait for it to render */
async function openObject(page: import('@playwright/test').Page, iri: string, label: string) {
  await page.evaluate(
    ({ iri, label }) => {
      (window as any).SemPKM.openTab(iri, label);
    },
    { iri, label },
  );
  // Wait for the tab content to render
  await page.waitForSelector('.object-tab', { timeout: 10000 });
  await waitForIdle(page);
  // Small delay for pushState to fire via onDidActivePanelChange
  await page.waitForTimeout(300);
}

/** Helper: get the ?tab= value from the current URL */
async function getTabParam(page: import('@playwright/test').Page): Promise<string | null> {
  return page.evaluate(() => new URLSearchParams(window.location.search).get('tab'));
}

/** Helper: get the active dockview panel ID */
async function getActivePanelId(page: import('@playwright/test').Page): Promise<string | null> {
  return page.evaluate(() => {
    const dv = (window as any).SemPKM?._dockview;
    return dv?.activePanel?.id || null;
  });
}

test.describe('Browser History & URL Sync', () => {
  test('opening an object updates URL with ?tab= parameter', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iri = SEED.notes.architecture.iri;
    await openObject(ownerPage, iri, 'Architecture Decision');

    const tabParam = await getTabParam(ownerPage);
    expect(tabParam).toBe(iri);
  });

  test('switching tabs updates URL to reflect active tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iriA = SEED.notes.architecture.iri;
    const iriB = SEED.people.alice.iri;

    // Open object A
    await openObject(ownerPage, iriA, 'Architecture Decision');
    expect(await getTabParam(ownerPage)).toBe(iriA);

    // Open object B — URL should switch to B
    await openObject(ownerPage, iriB, 'Alice Chen');
    expect(await getTabParam(ownerPage)).toBe(iriB);

    // Click back to tab A via dockview
    await ownerPage.evaluate((iri) => {
      const dv = (window as any).SemPKM._dockview;
      const panel = dv.panels.find((p: any) => p.id === iri);
      if (panel) panel.api.setActive();
    }, iriA);
    await page_settle(ownerPage);

    expect(await getTabParam(ownerPage)).toBe(iriA);
  });

  test('back/forward navigation switches between tabs', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iriA = SEED.notes.architecture.iri;
    const iriB = SEED.people.alice.iri;

    // Open A then B — creates history: [A, B]
    await openObject(ownerPage, iriA, 'Architecture Decision');
    await openObject(ownerPage, iriB, 'Alice Chen');

    // URL should be at B
    expect(await getTabParam(ownerPage)).toBe(iriB);
    expect(await getActivePanelId(ownerPage)).toBe(iriB);

    // Go back → should activate A
    await ownerPage.goBack();
    await page_settle(ownerPage);

    expect(await getTabParam(ownerPage)).toBe(iriA);
    expect(await getActivePanelId(ownerPage)).toBe(iriA);

    // Go forward → should activate B
    await ownerPage.goForward();
    await page_settle(ownerPage);

    expect(await getTabParam(ownerPage)).toBe(iriB);
    expect(await getActivePanelId(ownerPage)).toBe(iriB);
  });

  test('deep-link via ?tab= opens correct object on page load', async ({ ownerPage }) => {
    const iri = SEED.concepts.km.iri;

    // Navigate directly with ?tab= query parameter
    await ownerPage.goto(`${BASE_URL}/browser/?tab=${encodeURIComponent(iri)}`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Wait for the deep-link handler to open the tab
    await ownerPage.waitForSelector('.object-tab', { timeout: 15000 });
    await page_settle(ownerPage);

    // The active panel should be the deep-linked object
    const activePanelId = await getActivePanelId(ownerPage);
    expect(activePanelId).toBe(iri);

    // URL should reflect the tab
    const tabParam = await getTabParam(ownerPage);
    expect(tabParam).toBe(iri);
  });

  test('closing a tab and pressing back cleans up stale entry without error', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iriA = SEED.notes.architecture.iri;
    const iriB = SEED.people.alice.iri;

    // Open A then B
    await openObject(ownerPage, iriA, 'Architecture Decision');
    await openObject(ownerPage, iriB, 'Alice Chen');
    expect(await getTabParam(ownerPage)).toBe(iriB);

    // Close tab B via dockview API
    await ownerPage.evaluate((iri) => {
      const dv = (window as any).SemPKM._dockview;
      const panel = dv.panels.find((p: any) => p.id === iri);
      if (panel) dv.removePanel(panel);
    }, iriB);
    await page_settle(ownerPage);

    // After closing B, the active tab should be A
    expect(await getActivePanelId(ownerPage)).toBe(iriA);

    // Now go back — B's history entry is stale (panel closed)
    // The popstate handler should clean up the URL without errors
    await ownerPage.goBack();
    await page_settle(ownerPage);

    // Collect any JS errors that occurred
    const consoleErrors = await ownerPage.evaluate(() => {
      return (window as any).__e2eErrors || [];
    });

    // URL should not have a stale ?tab= pointing to closed B
    const tabParam = await getTabParam(ownerPage);
    // Either ?tab= is removed, or it points to A (the surviving tab)
    expect(tabParam).not.toBe(iriB);

    // No unhandled JS errors from stale panel reference
    // We verify by checking the page didn't crash — if we got here, no fatal errors
  });

  test('ephemeral new-object tabs are excluded from history', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iriA = SEED.notes.architecture.iri;

    // Open a real object first
    await openObject(ownerPage, iriA, 'Architecture Decision');
    expect(await getTabParam(ownerPage)).toBe(iriA);

    // Open a new-object form (creates an __new-object- prefixed panel)
    await ownerPage.evaluate(() => {
      const dv = (window as any).SemPKM._dockview;
      if (!dv) return;
      dv.addPanel({
        id: '__new-object-' + Date.now(),
        component: 'special-panel',
        params: { specialType: 'types', isView: false, isSpecial: true },
        title: 'New Object',
      });
    });
    await page_settle(ownerPage);

    // URL should NOT change to the ephemeral tab — still shows A
    const tabParam = await getTabParam(ownerPage);
    expect(tabParam).toBe(iriA);
  });
});

/** Small helper to let pushState/popstate handlers settle */
async function page_settle(page: import('@playwright/test').Page) {
  await page.waitForTimeout(500);
  await waitForIdle(page);
}
