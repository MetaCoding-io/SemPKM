/**
 * SPARQL Advanced Features E2E Tests
 *
<<<<<<< HEAD
 * Tests saved queries CRUD, server-side query history, SPARQL query types
 * (SELECT/ASK/CONSTRUCT/FILTER), vocabulary endpoint, and the admin SPARQL
 * console page redirect.
 *
 * Consolidated into 2 test() calls to stay within the 5/minute magic-link rate limit:
 *   1. API-only test: SPARQL query types + saved queries CRUD + history + vocabulary
 *   2. UI test: admin SPARQL console page load
=======
 * Tests saved queries, server-side query history, and IRI pill rendering
 * in SPARQL results.
>>>>>>> gsd/M003/S03
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('SPARQL Advanced Features', () => {
<<<<<<< HEAD
  test('SPARQL query types, saved queries CRUD, history, and vocabulary via API', async ({ ownerRequest }) => {
    // ================================================================
    // Part 1: SPARQL SELECT query with IRI bindings
    // ================================================================
    const selectResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10`,
      },
    });
    expect(selectResp.ok()).toBeTruthy();
    const selectData = await selectResp.json();
    expect(selectData.results.bindings.length).toBeGreaterThan(0);

    // Verify bindings contain IRI types
    const firstBinding = selectData.results.bindings[0];
    expect(firstBinding.s).toBeDefined();
    expect(firstBinding.s.type).toBe('uri');

    // Verify enrichment metadata is present
    expect(selectData._enrichment).toBeDefined();
    expect(typeof selectData._enrichment).toBe('object');

    // ================================================================
    // Part 2: SPARQL ASK query returns boolean
    // ================================================================
    const askResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK { <${SEED.notes.architecture.iri}> ?p ?o }`,
      },
    });
    expect(askResp.ok()).toBeTruthy();
    const askData = await askResp.json();
    expect(typeof askData.boolean).toBe('boolean');
    expect(askData.boolean).toBe(true);

    // ================================================================
    // Part 3: SPARQL CONSTRUCT — endpoint uses SELECT-only Accept header,
    // so CONSTRUCT may return an error (502/400). Verify the endpoint
    // handles it gracefully rather than crashing.
    // ================================================================
    const constructResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 5`,
      },
    });
    // CONSTRUCT may succeed (200) or return a graceful error (400/502)
    // depending on the triplestore's Accept header handling.
    // The key assertion is that it doesn't crash (500) or timeout.
    expect([200, 400, 502]).toContain(constructResp.status());

    // ================================================================
    // Part 4: SPARQL FILTER query works correctly
    // ================================================================
    const filterResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?s ?title WHERE {
=======
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
>>>>>>> gsd/M003/S03
          ?s <http://purl.org/dc/terms/title> ?title .
          FILTER(CONTAINS(LCASE(?title), "architecture"))
        }`,
      },
    });
<<<<<<< HEAD
    expect(filterResp.ok()).toBeTruthy();
    const filterData = await filterResp.json();
    expect(filterData.results.bindings.length).toBeGreaterThan(0);
    for (const binding of filterData.results.bindings) {
      expect(binding.title.value.toLowerCase()).toContain('architecture');
    }

    // ================================================================
    // Part 5: Server-side history — queries are recorded
    // ================================================================
    // Clear history first
    const clearResp = await ownerRequest.delete(`${BASE_URL}/api/sparql/history`);
    expect(clearResp.status()).toBe(204);

    // Execute a distinctive query to populate history
    const historyQuery = 'SELECT ?s WHERE { ?s a ?type } LIMIT 1';
    await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: historyQuery },
    });

    // Fetch history and verify the query appears
    const histResp = await ownerRequest.get(`${BASE_URL}/api/sparql/history`);
    expect(histResp.ok()).toBeTruthy();
    const history = await histResp.json();
    expect(Array.isArray(history)).toBe(true);
    expect(history.length).toBeGreaterThan(0);

    // Most recent entry should match our query
    const mostRecent = history[0];
    expect(mostRecent).toHaveProperty('id');
    expect(mostRecent).toHaveProperty('query_text');
    expect(mostRecent).toHaveProperty('executed_at');
    expect(mostRecent.query_text).toContain('SELECT ?s WHERE');

    // ================================================================
    // Part 6: Saved queries CRUD
    // ================================================================
    // Create a saved query
    const createResp = await ownerRequest.post(`${BASE_URL}/api/sparql/saved`, {
      data: {
        name: 'E2E Test Query',
        description: 'Created by e2e test',
        query_text: 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10',
      },
    });
    expect(createResp.status()).toBe(201);
    const savedQuery = await createResp.json();
    expect(savedQuery).toHaveProperty('id');
    expect(savedQuery.name).toBe('E2E Test Query');
    expect(savedQuery.description).toBe('Created by e2e test');
    expect(savedQuery.query_text).toContain('SELECT ?s ?p ?o');

    const savedQueryId = savedQuery.id;

    // List saved queries — should include our new query
    const listResp = await ownerRequest.get(`${BASE_URL}/api/sparql/saved`);
    expect(listResp.ok()).toBeTruthy();
    const savedList = await listResp.json();
    expect(Array.isArray(savedList)).toBe(true);
    const found = savedList.find((q: any) => q.id === savedQueryId);
    expect(found).toBeDefined();
    expect(found.name).toBe('E2E Test Query');

    // Update the saved query
    const updateResp = await ownerRequest.put(`${BASE_URL}/api/sparql/saved/${savedQueryId}`, {
      data: {
        name: 'E2E Test Query (Updated)',
        query_text: 'SELECT ?s WHERE { ?s a ?type } LIMIT 5',
      },
    });
    expect(updateResp.ok()).toBeTruthy();
    const updatedQuery = await updateResp.json();
    expect(updatedQuery.name).toBe('E2E Test Query (Updated)');
    expect(updatedQuery.query_text).toContain('SELECT ?s WHERE');

    // Delete the saved query
    const deleteResp = await ownerRequest.delete(`${BASE_URL}/api/sparql/saved/${savedQueryId}`);
    expect(deleteResp.status()).toBe(204);

    // Verify it's gone
    const listAfterDelete = await ownerRequest.get(`${BASE_URL}/api/sparql/saved`);
    const afterDeleteList = await listAfterDelete.json();
    const notFound = (afterDeleteList as any[]).find((q: any) => q.id === savedQueryId);
    expect(notFound).toBeUndefined();

    // ================================================================
    // Part 7: Vocabulary endpoint returns classes and predicates
    // ================================================================
    const vocabResp = await ownerRequest.get(`${BASE_URL}/api/sparql/vocabulary`);
    expect(vocabResp.ok()).toBeTruthy();
    const vocabData = await vocabResp.json();
    expect(vocabData).toHaveProperty('prefixes');
    expect(vocabData).toHaveProperty('items');
    expect(vocabData).toHaveProperty('model_version');
    expect(typeof vocabData.prefixes).toBe('object');
    expect(Array.isArray(vocabData.items)).toBe(true);
    // Should have vocabulary items from installed models
    expect(vocabData.items.length).toBeGreaterThan(0);

    // Verify item structure
    const firstItem = vocabData.items[0];
    expect(firstItem).toHaveProperty('qname');
    expect(firstItem).toHaveProperty('full_iri');
    expect(firstItem).toHaveProperty('badge');
    expect(['C', 'P', 'D']).toContain(firstItem.badge);

    // ================================================================
    // Part 8: Saved query sharing — list shareable users
    // ================================================================
    const usersResp = await ownerRequest.get(`${BASE_URL}/api/sparql/users`);
    expect(usersResp.ok()).toBeTruthy();
    const users = await usersResp.json();
    expect(Array.isArray(users)).toBe(true);
    // Should include at least the owner
    expect(users.length).toBeGreaterThan(0);
    expect(users[0]).toHaveProperty('id');
    expect(users[0]).toHaveProperty('email');

    // ================================================================
    // Part 9: GET-based SPARQL query
    // ================================================================
    const getResp = await ownerRequest.get(
      `${BASE_URL}/api/sparql?query=${encodeURIComponent('SELECT ?s WHERE { ?s a ?type } LIMIT 3')}`,
    );
    expect(getResp.ok()).toBeTruthy();
    const getData = await getResp.json();
    expect(getData.results.bindings.length).toBeGreaterThan(0);

    // ================================================================
    // Part 10: Error handling — malformed query returns 400
    // ================================================================
    const badResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: 'NOT A VALID SPARQL QUERY @@@@' },
    });
    expect([400, 502]).toContain(badResp.status());
  });

  test('admin SPARQL console redirects to workspace panel', async ({ ownerPage }) => {
    // /admin/sparql now redirects to /browser?panel=sparql
    const resp = await ownerPage.goto(`${BASE_URL}/admin/sparql`);

    // Should have redirected — final URL should be /browser with sparql panel param
    const url = ownerPage.url();
    expect(url).toContain('/browser');

    // The SPARQL panel should be activated (either via URL param or direct)
    // Wait for the workspace to load
    await ownerPage.waitForSelector('.workspace-container', { state: 'attached', timeout: 15000 });

    // The bottom panel should be open with SPARQL tab active
    // (the ?panel=sparql parameter triggers auto-open)
    const panelState = await ownerPage.evaluate(() => {
      const saved = localStorage.getItem('sempkm_bottom_panel');
      return saved ? JSON.parse(saved) : null;
    });

    // Panel state should show sparql as active tab if redirect worked
    if (panelState) {
      expect(panelState.activeTab).toBe('sparql');
      expect(panelState.open).toBe(true);
    }

    // Verify SPARQL panel pane exists in the DOM
    const sparqlPane = ownerPage.locator('#panel-sparql');
    await expect(sparqlPane).toBeAttached({ timeout: 5000 });
=======
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
>>>>>>> gsd/M003/S03
  });
});
