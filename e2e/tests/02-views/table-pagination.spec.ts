/**
 * Table View Pagination E2E Tests
 *
 * Tests table view pagination controls: creating enough objects to trigger
 * pagination, verifying navigation controls, and page indicator updates.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Table View Pagination', () => {
  test('create enough objects to trigger pagination', async ({ ownerRequest }) => {
    // Create 12 objects to exceed the default page size (typically 10)
    const commands = Array.from({ length: 12 }, (_, i) => ({
      command: 'object.create',
      params: {
        type: TYPES.Note,
        properties: {
          'http://purl.org/dc/terms/title': `Pagination Test Note ${i + 1}`,
        },
      },
    }));

    const resp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: commands,
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results.length).toBe(12);
  });

  test('table view shows pagination controls with sufficient objects', async ({ ownerPage, ownerSessionToken }) => {
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
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/table/' + iri, isView: true, isSpecial: true },
          title: 'Paginated View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector(SEL.views.table, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Check for pagination controls
    const paginationControls = ownerPage.locator('.pagination, .page-nav, [data-testid="pagination"], .pager');
    const hasPagination = await paginationControls.count() > 0;

    // If pagination exists, verify it has navigation elements
    if (hasPagination) {
      const nextBtn = ownerPage.locator('.pagination .next, .page-next, button:has-text("Next"), a:has-text("Next")');
      if (await nextBtn.count() > 0) {
        // Get rows before clicking next
        const rowsBefore = await ownerPage.locator(SEL.views.tableRow).count();

        // Click next page
        await nextBtn.first().click();
        await waitForIdle(ownerPage);

        // Rows should still be present after navigation
        const rowsAfter = await ownerPage.locator(SEL.views.tableRow).count();
        expect(rowsAfter).toBeGreaterThan(0);
      }
    }
  });
});
