/**
 * SPARQL Console E2E Tests
 *
 * Tests the admin SPARQL console page at /admin/sparql which uses
 * Yasgui (@zazuko/yasgui) for query editing and execution.
 * Also tests the /api/sparql POST endpoint directly.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('SPARQL Admin Console', () => {

  test('SPARQL admin page loads Yasgui', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/sparql`);

    // Wait for Yasgui to initialize on the #yasgui-admin container
    await ownerPage.waitForFunction(
      () => (document.getElementById('yasgui-admin') as any)?._yasguiInstance != null,
      { timeout: 15000 },
    );

    // The Yasgui widget should be visible
    await expect(ownerPage.locator('#yasgui-admin .yasgui')).toBeVisible();
  });

  test('SPARQL query executes and returns results', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/sparql`);

    // Wait for Yasgui init
    await ownerPage.waitForFunction(
      () => (document.getElementById('yasgui-admin') as any)?._yasguiInstance != null,
      { timeout: 15000 },
    );

    // Set the query programmatically
    await ownerPage.evaluate(() => {
      const yasgui = (document.getElementById('yasgui-admin') as any)._yasguiInstance;
      const tab = yasgui.getTab();
      tab.setQuery('SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5');
    });

    // Click the run button to execute the query
    await ownerPage.locator('.yasqe_queryButton').click();

    // Wait for results to appear in the YASR container (table rows)
    await ownerPage.waitForFunction(
      () => {
        const rows = document.querySelectorAll('.yasr table tbody tr, .yasr .dataTable tbody tr');
        return rows.length > 0;
      },
      { timeout: 15000 },
    );

    // Verify we got result rows
    const rowCount = await ownerPage.evaluate(() => {
      const rows = document.querySelectorAll('.yasr table tbody tr, .yasr .dataTable tbody tr');
      return rows.length;
    });
    expect(rowCount).toBeGreaterThan(0);
  });

  test('SPARQL POST endpoint returns SPARQL JSON results', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/sparql`);

    // POST directly to /api/sparql from the page context (inherits session cookie)
    const result = await ownerPage.evaluate(async () => {
      const resp = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'same-origin',
        body: 'query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5',
      });
      if (!resp.ok) return { error: resp.status };
      return resp.json();
    });

    expect(result).toHaveProperty('results');
    expect(result.results).toHaveProperty('bindings');
    expect(Array.isArray(result.results.bindings)).toBe(true);
    expect(result.results.bindings.length).toBeGreaterThan(0);
  });

});
