/**
 * Table View Pagination E2E Tests
 *
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
      command: 'object.create',
      params: {
        type: TYPES.Note,
        properties: {
          'http://purl.org/dc/terms/title': `Pagination Test Note ${Date.now()}-${i}`,
        },
      },
    }));

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
  });
});
