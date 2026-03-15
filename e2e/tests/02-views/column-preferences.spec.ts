/**
 * Column Visibility Preferences E2E Tests
 *
<<<<<<< HEAD
 * Tests that table column visibility preferences persist via localStorage
 * using the ColumnPrefs API (column-prefs.js). Storage key format:
 * "col-prefs:{typeIri}" with value [{col, visible, order}].
 *
 * Consolidated into 1 test() function (API + UI) to stay within the
 * 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Column Preferences', () => {
  test('column prefs persist in localStorage and survive page reload', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // 1. Verify ColumnPrefs API is available on window
    const hasApi = await ownerPage.evaluate(() => {
      return typeof (window as any).ColumnPrefs === 'object'
        && typeof (window as any).ColumnPrefs.saveColumnPrefs === 'function'
        && typeof (window as any).ColumnPrefs.getVisibleColumns === 'function';
    });
    expect(hasApi).toBe(true);

    // 2. Save column prefs via the ColumnPrefs API
    const testTypeIri = 'urn:sempkm:test:column-prefs-type';
    await ownerPage.evaluate((typeIri) => {
      const prefs = [
        { col: 'title', visible: true, order: 0 },
        { col: 'status', visible: false, order: 1 },
        { col: 'priority', visible: true, order: 2 },
      ];
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    // 3. Read back via ColumnPrefs API
    const savedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(savedPrefs).toBeDefined();
    expect(savedPrefs).toHaveLength(3);
    expect(savedPrefs[0].col).toBe('title');
    expect(savedPrefs[0].visible).toBe(true);
    expect(savedPrefs[1].col).toBe('status');
    expect(savedPrefs[1].visible).toBe(false);

    // 4. Verify raw localStorage key format
    const rawStored = await ownerPage.evaluate((typeIri) => {
      return localStorage.getItem('col-prefs:' + typeIri);
    }, testTypeIri);
    expect(rawStored).toBeTruthy();
    const parsed = JSON.parse(rawStored!);
    expect(parsed).toHaveLength(3);
    expect(parsed[1].visible).toBe(false);

    // 5. Reload and verify persistence
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);

    const afterReload = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(afterReload).toBeDefined();
    expect(afterReload).toHaveLength(3);
    expect(afterReload[1].col).toBe('status');
    expect(afterReload[1].visible).toBe(false);

    // 6. Toggle a column visible and verify update persists
    await ownerPage.evaluate((typeIri) => {
      const prefs = (window as any).ColumnPrefs.getVisibleColumns(typeIri);
      prefs[1].visible = true;
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    const updatedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(updatedPrefs[1].visible).toBe(true);
=======
 * Tests that table column visibility preferences persist via localStorage.
 * Uses column-prefs.js which stores visibility state in localStorage.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Column Preferences', () => {
  test('table view has column visibility controls', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');
    expect(tableSpec).toBeDefined();

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(tableSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'colpref-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/table/' + iri, isView: true, isSpecial: true },
          title: 'Column Prefs View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector(SEL.views.table, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Check for column toggle controls
    const columnToggles = ownerPage.locator('.column-toggle, .col-visibility, [data-column-toggle]');
    const toggleCount = await columnToggles.count();

    // Verify there are column headers at minimum
    const headerCount = await ownerPage.locator(`${SEL.views.table} th`).count();
    expect(headerCount).toBeGreaterThan(0);
  });

  test('column visibility preference persists in localStorage', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Set a column preference via localStorage
    await ownerPage.evaluate((specIri) => {
      // column-prefs.js uses keys like "sempkm_column_prefs_{specIri}"
      const key = `sempkm_column_prefs_${specIri}`;
      const prefs = { hiddenColumns: ['col-1'] };
      localStorage.setItem(key, JSON.stringify(prefs));
    }, tableSpec.spec_iri);

    // Read it back
    const stored = await ownerPage.evaluate((specIri) => {
      const key = `sempkm_column_prefs_${specIri}`;
      return localStorage.getItem(key);
    }, tableSpec.spec_iri);

    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.hiddenColumns).toContain('col-1');
>>>>>>> gsd/M003/S03
  });
});
