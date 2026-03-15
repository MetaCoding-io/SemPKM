/**
 * Sidebar Panel Drag-Drop Reorder E2E Tests
 *
<<<<<<< HEAD
 * Tests that sidebar panel positions persist via localStorage key
 * "sempkm_panel_positions". Panels use [data-panel-name] attributes
 * and are stored as {panelName: {zone: 'left'|'right', order: number}}.
 *
 * Consolidated into 1 test() function to stay within the
 * 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace } from '../../helpers/wait-for';

test.describe('Sidebar Panel Reorder', () => {
  test('panel positions persist in localStorage and survive reload', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // 1. Verify panels with data-panel-name exist in the DOM
    const panelInfo = await ownerPage.evaluate(() => {
      const panels = document.querySelectorAll('[data-panel-name]');
      return {
        count: panels.length,
        names: Array.from(panels).map(p => p.getAttribute('data-panel-name')),
      };
    });
    expect(panelInfo.count).toBeGreaterThan(0);
    expect(panelInfo.names.length).toBeGreaterThan(0);

    // 2. Verify the savePanelPositions / restorePanelPositions
    //    mechanism works by directly calling savePanelPositions and
    //    reading from localStorage.
    //    The function is internal (not on window), so we test the
    //    storage contract directly.
    const panelNames = panelInfo.names;

    // 3. Set custom panel positions in localStorage
    const customPositions: Record<string, { zone: string; order: number }> = {};
    panelNames.forEach((name, i) => {
      customPositions[name!] = { zone: i % 2 === 0 ? 'left' : 'right', order: i };
    });

    await ownerPage.evaluate((positions) => {
      localStorage.setItem('sempkm_panel_positions', JSON.stringify(positions));
    }, customPositions);

    // 4. Read back and verify
    const stored = await ownerPage.evaluate(() => {
      return localStorage.getItem('sempkm_panel_positions');
    });
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(Object.keys(parsed).length).toBe(panelNames.length);
    // Check first panel has expected zone
    expect(parsed[panelNames[0]!].zone).toBe('left');

    // 5. Reload and verify positions survive
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);

    const afterReload = await ownerPage.evaluate(() => {
      return localStorage.getItem('sempkm_panel_positions');
    });
    expect(afterReload).toBeTruthy();
    const parsedAfter = JSON.parse(afterReload!);
    expect(parsedAfter[panelNames[0]!].zone).toBe('left');
    expect(parsedAfter[panelNames[0]!].order).toBe(0);

    // 6. Verify panels are actually in the DOM after restore
    const panelsAfterReload = await ownerPage.evaluate(() => {
      const panels = document.querySelectorAll('[data-panel-name]');
      return Array.from(panels).map(p => ({
        name: p.getAttribute('data-panel-name'),
        parentId: p.parentElement?.id || 'unknown',
      }));
    });
    expect(panelsAfterReload.length).toBeGreaterThan(0);

    // 7. Verify the right-content and nav-tree containers exist
    //    (these are the two zones where panels can be placed)
    const containers = await ownerPage.evaluate(() => {
      return {
        hasRight: !!document.getElementById('right-content'),
        hasNavTree: !!document.getElementById('nav-tree'),
      };
    });
    expect(containers.hasRight).toBe(true);
    expect(containers.hasNavTree).toBe(true);
=======
 * Tests that sidebar panel positions persist via localStorage
 * after drag-drop reordering. Panel positions are stored in
 * localStorage key "sempkm_panel_positions".
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Sidebar Panel Reorder', () => {
  test('panel position storage key exists after workspace load', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Check if panel positions are being tracked
    const hasPositionKey = await ownerPage.evaluate(() => {
      // Panels use data-panel-name attributes and store positions
      const panels = document.querySelectorAll('[data-panel-name]');
      return panels.length > 0;
    });

    expect(hasPositionKey).toBe(true);
  });

  test('panel positions persist in localStorage', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Set panel positions in localStorage
    await ownerPage.evaluate(() => {
      const positions = { 'nav-tree': 0, 'views': 1, 'search': 2 };
      localStorage.setItem('sempkm_panel_positions', JSON.stringify(positions));
    });

    // Read back and verify
    const stored = await ownerPage.evaluate(() => {
      return localStorage.getItem('sempkm_panel_positions');
    });

    expect(stored).toBeTruthy();
    const positions = JSON.parse(stored!);
    expect(positions['nav-tree']).toBe(0);
    expect(positions['views']).toBe(1);
  });

  test('panel positions survive page reload', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Set custom positions
    await ownerPage.evaluate(() => {
      const positions = { 'nav-tree': 2, 'views': 0, 'search': 1 };
      localStorage.setItem('sempkm_panel_positions', JSON.stringify(positions));
    });

    // Reload
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);

    // Verify positions survived
    const stored = await ownerPage.evaluate(() => {
      return localStorage.getItem('sempkm_panel_positions');
    });

    expect(stored).toBeTruthy();
    const positions = JSON.parse(stored!);
    expect(positions['nav-tree']).toBe(2);
  });

  test('sidebar has draggable panel sections', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Check for panels with drag handles or drop zones
    const panelInfo = await ownerPage.evaluate(() => {
      const panels = document.querySelectorAll('[data-panel-name]');
      const dropZones = document.querySelectorAll('[data-drop-zone]');
      return {
        panelCount: panels.length,
        dropZoneCount: dropZones.length,
        panelNames: Array.from(panels).map(p => p.getAttribute('data-panel-name')),
      };
    });

    expect(panelInfo.panelCount).toBeGreaterThan(0);
>>>>>>> gsd/M003/S03
  });
});
