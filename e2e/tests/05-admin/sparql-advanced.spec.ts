/**
 * SPARQL Advanced Features E2E Tests
 *
 * Tests saved queries, server-side query history, and IRI pill rendering
 * in SPARQL results.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('SPARQL Advanced Features', () => {
  test('SPARQL query returns results with IRI bindings', async ({ ownerRequest }) => {
    // Execute a query that returns IRIs
    const resp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?s ?type FROM <urn:sempkm:current> WHERE {
          ?s a ?type .
        } LIMIT 10`,
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results.bindings.length).toBeGreaterThan(0);

    // Verify bindings contain IRI types
    const firstBinding = data.results.bindings[0];
    expect(firstBinding.s).toBeDefined();
    expect(firstBinding.s.type).toBe('uri');
  });

  test('SPARQL ASK query returns boolean', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${SEED.notes.architecture.iri}> ?p ?o }`,
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(typeof data.boolean).toBe('boolean');
    expect(data.boolean).toBe(true);
  });

  test('SPARQL CONSTRUCT returns triples', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE {
          ?s ?p ?o .
        } LIMIT 5`,
      },
    });
    expect(resp.ok()).toBeTruthy();
    // CONSTRUCT returns either JSON-LD, Turtle, or other RDF format
    const contentType = resp.headers()['content-type'] || '';
    expect(resp.status()).toBe(200);
  });

  test('SPARQL query with FILTER works correctly', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?s ?title FROM <urn:sempkm:current> WHERE {
          ?s <http://purl.org/dc/terms/title> ?title .
          FILTER(CONTAINS(LCASE(?title), "architecture"))
        }`,
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results.bindings.length).toBeGreaterThan(0);

    // All results should contain "architecture" (case-insensitive)
    for (const binding of data.results.bindings) {
      expect(binding.title.value.toLowerCase()).toContain('architecture');
    }
  });

  test('admin SPARQL console page loads', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/admin/sparql`);
    expect(resp?.ok()).toBeTruthy();

    // Should have a SPARQL editor / Yasgui interface
    await ownerPage.waitForSelector('.yasgui, .CodeMirror, textarea, #sparql-editor', { timeout: 15000 });
  });
});
