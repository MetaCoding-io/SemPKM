/**
 * Carousel View Switching E2E Tests
 *
 * Tests the carousel tab bar that renders for types with multiple view specs
 * (table, card, graph). Verifies dockview initialization, tab bar rendering,
 * view switching, and localStorage persistence.
 *
 * Uses dockview helpers (openViewTab, getTabCount) per TEST-04 requirements.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { openViewTab, getTabCount } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/** Fetch view specs from the API and find a table spec for Notes. */
async function getNoteTableSpec(ownerPage: any, ownerSessionToken: string) {
  const api = ownerPage.context().request;
  const resp = await api.get(`${BASE_URL}/browser/views/available`, {
    headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
  });
  const specs = await resp.json();
  // Find a table spec for a type that should have carousel (Notes have table+card+graph)
  // API returns target_class (not type_iri)
  const noteTable = specs.find(
    (s: any) => s.target_class === TYPES.Note && s.renderer_type === 'table',
  );
  return noteTable;
}

test.describe('Carousel View Switching', () => {
  test('dockview is initialized and openViewTab helper works', async ({ ownerPage, ownerSessionToken }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Assert window._dockview is available
    await ownerPage.waitForFunction(
      () => (window as any)._dockview != null,
      { timeout: 5000 },
    );

    // Check initial tab count via helper
    const initialCount = await getTabCount(ownerPage);
    expect(initialCount).toBeGreaterThanOrEqual(0);

    // Fetch the actual spec IRI from the API
    const noteTable = await getNoteTableSpec(ownerPage, ownerSessionToken);
    expect(noteTable).toBeDefined();

    // Open view using the dockview helper (not raw dv.addPanel)
    await openViewTab(
      ownerPage,
      noteTable.spec_iri,
      'Notes Table',
      'table',
      '.carousel-tab-bar',
      15000,
    );

    // getTabCount should have increased
    const newCount = await getTabCount(ownerPage);
    expect(newCount).toBeGreaterThan(initialCount);
  });

  test('carousel tab bar renders for types with multiple views', async ({ ownerPage, ownerSessionToken }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const noteTable = await getNoteTableSpec(ownerPage, ownerSessionToken);
    expect(noteTable).toBeDefined();

    await openViewTab(
      ownerPage,
      noteTable.spec_iri,
      'Notes Table',
      'table',
      '.carousel-tab-bar',
      15000,
    );

    // Carousel tab bar should be visible
    const carouselBar = ownerPage.locator('.carousel-tab-bar');
    await expect(carouselBar).toBeVisible({ timeout: 15000 });

    // Should have at least 2 tabs (table + card minimum)
    const tabCount = await ownerPage.locator('.carousel-tab').count();
    expect(tabCount).toBeGreaterThanOrEqual(2);

    // Exactly one tab should be active
    const activeTab = ownerPage.locator('.carousel-tab.active');
    await expect(activeTab).toHaveCount(1);
  });

  test('clicking carousel tab switches view content', async ({ ownerPage, ownerSessionToken }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const noteTable = await getNoteTableSpec(ownerPage, ownerSessionToken);
    expect(noteTable).toBeDefined();

    await openViewTab(
      ownerPage,
      noteTable.spec_iri,
      'Notes Table',
      'table',
      '.carousel-tab-bar',
      15000,
    );

    await expect(ownerPage.locator('.carousel-tab-bar')).toBeVisible({ timeout: 15000 });

    // Identify active and non-active tabs
    const activeTabText = await ownerPage.locator('.carousel-tab.active').textContent();
    const nonActiveTabs = ownerPage.locator('.carousel-tab:not(.active)');
    const nonActiveCount = await nonActiveTabs.count();
    expect(nonActiveCount).toBeGreaterThanOrEqual(1);

    // Click a non-active tab
    const targetTab = nonActiveTabs.first();
    const targetTabText = await targetTab.textContent();
    await targetTab.click();

    // Wait for htmx swap to complete
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(500);

    // The clicked tab should now be active
    const newActiveText = await ownerPage.locator('.carousel-tab.active').textContent();
    expect(newActiveText).toBe(targetTabText);

    // The previously active tab should no longer be active
    if (activeTabText !== targetTabText) {
      expect(newActiveText).not.toBe(activeTabText);
    }
  });

  test('carousel view selection persists in localStorage', async ({ ownerPage, ownerSessionToken }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clear carousel localStorage
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_carousel_view'));

    const noteTable = await getNoteTableSpec(ownerPage, ownerSessionToken);
    expect(noteTable).toBeDefined();

    await openViewTab(
      ownerPage,
      noteTable.spec_iri,
      'Notes Table',
      'table',
      '.carousel-tab-bar',
      15000,
    );

    await expect(ownerPage.locator('.carousel-tab-bar')).toBeVisible({ timeout: 15000 });

    // Click a non-default carousel tab (switch away from current)
    const nonActiveTab = ownerPage.locator('.carousel-tab:not(.active)').first();
    await nonActiveTab.click();
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(500);

    // Read localStorage and verify persistence
    const stored = await ownerPage.evaluate(() => {
      const raw = localStorage.getItem('sempkm_carousel_view');
      if (!raw) return null;
      try { return JSON.parse(raw); } catch { return raw; }
    });

    expect(stored).not.toBeNull();

    // Clean up
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_carousel_view'));
  });
});
