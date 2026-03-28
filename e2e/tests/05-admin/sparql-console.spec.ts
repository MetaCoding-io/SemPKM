/**
 * SPARQL Console E2E Tests
 *
 * Tests the /api/sparql POST endpoint for SPARQL query execution.
 * The admin SPARQL console UI was removed (Yasgui → workspace SPARQL panel).
 * The workspace SPARQL panel is tested in sparql-workspace.spec.ts.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('SPARQL Console', () => {

  test('SPARQL POST endpoint returns SPARQL JSON results', async ({ ownerPage }) => {
    // Navigate to workspace so we have an authenticated page context
    await ownerPage.goto(`${BASE_URL}/browser/`);

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
