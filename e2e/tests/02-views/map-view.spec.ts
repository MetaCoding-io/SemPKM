/**
 * Map View E2E Tests — S04, M033
 *
 * Validates the Leaflet-based map view renderer:
 *   - Empty state when no type has geo properties
 *   - Map View sidebar entry exists
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace } from '../../helpers/wait-for';

test.describe('Map View', () => {
  /**
   * Empty state: when opening the map view without a type that has geo
   * properties, the view should show a .view-empty-state message explaining
   * what geographic coordinates are needed.
   */
  test('shows empty state for type without geo properties', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clear any previously stored type so the map starts without a type
    await ownerPage.evaluate(() => {
      localStorage.removeItem('sempkm_generic_type_map');
    });

    // Open map view — expect the empty state to appear (either "Select a type"
    // or the instructive geo-properties message)
    await openGenericViewTab(ownerPage, 'map', '.view-empty-state', undefined, undefined, 20000);
    await expect(ownerPage.locator('.view-empty-state')).toBeVisible({ timeout: 10000 });

    // The empty state should mention geographic coordinates or lat/lng
    const emptyText = await ownerPage.locator('.view-empty-state').textContent();
    // Either "Select a type to use Map View" or the geo-properties instructive text
    expect(
      emptyText?.includes('Map View') ||
      emptyText?.includes('geographic coordinates') ||
      emptyText?.includes('latitude/longitude')
    ).toBe(true);
  });

  /**
   * Sidebar: the Map View entry should be present in the VIEWS explorer
   * section of the workspace sidebar.
   */
  test('map view sidebar entry exists', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Expand the VIEWS explorer section (sections start collapsed)
    const viewsSection = ownerPage.locator('#section-views');
    const isExpanded = await viewsSection.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded) {
      await viewsSection.locator('.explorer-section-header').click();
      // Wait for htmx to load the views explorer content
      await ownerPage.waitForSelector('#views-tree .view-leaf', { timeout: 10000 });
    }

    // The VIEWS section should contain a "Map View" link
    const mapEntry = ownerPage.locator('.view-leaf', { hasText: 'Map View' });
    await expect(mapEntry).toBeVisible({ timeout: 10000 });
  });
});
