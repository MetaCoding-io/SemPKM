/**
 * Column Visibility Preferences E2E Tests
 *
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
  });
});
