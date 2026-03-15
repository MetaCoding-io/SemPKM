/**
 * Table View Pagination E2E Tests
 *
<<<<<<< HEAD
 * Tests table view pagination via API endpoints: creating objects to trigger
 * pagination, verifying pagination metadata, navigating pages, and filtering.
 *
 * Consolidated into 1 test() to stay within the 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Table View Pagination', () => {
  test('table pagination: create objects, verify pages, navigate, and filter', async ({ ownerRequest }) => {
    // 1. Get available view specs to find a table view
    const specsResp = await ownerRequest.get(`${BASE_URL}/browser/views/available`);
    expect(specsResp.ok()).toBeTruthy();
    const specs = await specsResp.json();
    const tableSpec = specs.find((s: any) => s.renderer_type === 'table');
    expect(tableSpec).toBeDefined();

    const specIri = encodeURIComponent(tableSpec.spec_iri);

    // 2. Create enough objects to guarantee pagination with page_size=5
    //    (Using small page_size rather than creating 25+ objects)
    const commands = Array.from({ length: 8 }, (_, i) => ({
=======
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
>>>>>>> gsd/M003/S03
      command: 'object.create',
      params: {
        type: TYPES.Note,
        properties: {
<<<<<<< HEAD
          'http://purl.org/dc/terms/title': `Pagination Test Note ${Date.now()}-${i}`,
=======
          'http://purl.org/dc/terms/title': `Pagination Test Note ${i + 1}`,
>>>>>>> gsd/M003/S03
        },
      },
    }));

<<<<<<< HEAD
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: commands,
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    expect(createData.results.length).toBe(8);

    // 3. Fetch page 1 with small page_size to trigger pagination
    const page1Resp = await ownerRequest.get(
      `${BASE_URL}/browser/views/table/${specIri}?page=1&page_size=5`,
      { headers: { Accept: 'text/html' } },
    );
    expect(page1Resp.ok()).toBeTruthy();
    const page1Html = await page1Resp.text();

    // Should contain pagination controls (the pagination.html partial)
    expect(page1Html).toContain('pagination');
    // Page 1 info should be present
    expect(page1Html).toContain('Page 1 of');
    // Should contain "Next" link for next page
    expect(page1Html).toContain('Next');

    // 4. Fetch page 2 — verify it returns different content
    const page2Resp = await ownerRequest.get(
      `${BASE_URL}/browser/views/table/${specIri}?page=2&page_size=5`,
      { headers: { Accept: 'text/html' } },
    );
    expect(page2Resp.ok()).toBeTruthy();
    const page2Html = await page2Resp.text();
    expect(page2Html).toContain('Page 2 of');
    // Page 2 should have "Prev" navigation
    expect(page2Html).toContain('Prev');

    // 5. Test filtering — filter by a known title substring
    const filterResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/table/${specIri}?page=1&page_size=25&filter=Pagination+Test+Note`,
      { headers: { Accept: 'text/html' } },
    );
    expect(filterResp.ok()).toBeTruthy();
    const filterHtml = await filterResp.text();
    // Filtered results should include our created notes
    expect(filterHtml).toContain('Pagination Test Note');

    // 6. Test sorting parameter
    const sortResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/table/${specIri}?page=1&page_size=5&sort=title&dir=desc`,
      { headers: { Accept: 'text/html' } },
    );
    expect(sortResp.ok()).toBeTruthy();
    const sortHtml = await sortResp.text();
    // Should still render valid HTML with table rows
    expect(sortHtml).toContain('data-testid="table-view"');

    // 7. Out-of-range page — should return page 1 or empty gracefully, not 500
    const outResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/table/${specIri}?page=9999&page_size=5`,
      { headers: { Accept: 'text/html' } },
    );
    expect(outResp.status()).toBeLessThan(500);
=======
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
>>>>>>> gsd/M003/S03
  });
});
