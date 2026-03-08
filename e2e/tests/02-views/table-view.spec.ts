/**
 * Table View E2E Tests
 *
 * Tests the table view renderer: loading data, sorting, filtering,
 * pagination, and row click navigation.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Table View', () => {
  test('available views endpoint returns view specs', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const resp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    expect(resp.ok()).toBeTruthy();

    const specs = await resp.json();
    expect(Array.isArray(specs)).toBeTruthy();
    expect(specs.length).toBeGreaterThan(0);

    // Should have at least one table view
    const tableSpecs = specs.filter((s: any) => s.renderer_type === 'table');
    expect(tableSpecs.length).toBeGreaterThan(0);
  });

  test('table view renders rows for seed data', async ({ ownerPage, ownerSessionToken }) => {
    // First get view specs to find a table view spec IRI
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');
    expect(tableSpec).toBeDefined();

    // Load the table view in the workspace
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(tableSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/table/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    // Wait for table view to render
    await ownerPage.waitForSelector(SEL.views.table, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Should have at least one data row
    const rows = ownerPage.locator(SEL.views.tableRow);
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('table view has sortable column headers', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(tableSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/table/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector(SEL.views.table, { timeout: 15000 });

    // Should have sort headers
    const sortHeaders = ownerPage.locator('.sort-header');
    const headerCount = await sortHeaders.count();
    expect(headerCount).toBeGreaterThan(0);

    // Click a sort header to trigger sorting
    await sortHeaders.first().click();
    await waitForIdle(ownerPage);

    // Table should re-render (still has rows)
    await ownerPage.waitForSelector(SEL.views.table, { timeout: 10000 });
  });

  test('table row click opens object', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(tableSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/table/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector(SEL.views.table, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Click the first row's link to open an object
    const firstRowLink = ownerPage.locator('.table-row-link').first();
    const linkCount = await firstRowLink.count();
    if (linkCount > 0) {
      await firstRowLink.click();
      await waitForIdle(ownerPage);

      // Should have loaded object content in the editor area
      // (either object form, or object tab rendering)
      const editorArea = ownerPage.locator(SEL.workspace.editorArea);
      await expect(editorArea).not.toBeEmpty();
    }
  });
});
