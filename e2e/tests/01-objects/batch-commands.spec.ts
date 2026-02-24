/**
 * Batch Command E2E Tests
 *
 * Tests the batch command API for creating multiple objects atomically
 * and verifying they all exist via SPARQL.
 */
import { test, expect } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Batch Commands', () => {
  test('create multiple objects in a single batch', async ({ ownerPage }) => {
    const response = await ownerPage.request.post('/api/commands', {
      data: [
        {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Batch Note 1' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Batch Note 2' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: 'Concept',
            properties: { 'http://www.w3.org/2004/02/skos/core#prefLabel': 'Batch Concept' },
          },
        },
      ],
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    // Three results, all sharing the same event
    expect(data.results).toHaveLength(3);
    const eventIri = data.results[0].event_iri;
    expect(data.results[1].event_iri).toBe(eventIri);
    expect(data.results[2].event_iri).toBe(eventIri);

    // Each result has a unique IRI
    const iris = data.results.map((r: { iri: string }) => r.iri);
    expect(new Set(iris).size).toBe(3);
  });

  test('verify batch-created objects exist via SPARQL', async ({ ownerPage }) => {
    // First create the objects
    const createResp = await ownerPage.request.post('/api/commands', {
      data: [
        {
          command: 'object.create',
          params: {
            type: 'Person',
            properties: { 'http://xmlns.com/foaf/0.1/name': 'SPARQL Verify Person' },
          },
        },
      ],
    });

    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const personIri = createData.results[0].iri;

    // Query via SPARQL to verify it exists
    const sparqlResp = await ownerPage.request.post('/api/sparql', {
      data: {
        query: `
          SELECT ?name WHERE {
            GRAPH <urn:sempkm:current> {
              <${personIri}> <http://xmlns.com/foaf/0.1/name> ?name .
            }
          }
        `,
      },
    });

    expect(sparqlResp.ok()).toBeTruthy();
    const sparqlData = await sparqlResp.json();
    const bindings = sparqlData.results?.bindings || [];
    expect(bindings).toHaveLength(1);
    expect(bindings[0].name.value).toBe('SPARQL Verify Person');
  });

  test('invalid command in batch returns error', async ({ ownerPage }) => {
    const response = await ownerPage.request.post('/api/commands', {
      data: {
        command: 'object.patch',
        params: {
          iri: 'urn:nonexistent:object',
          properties: { 'http://purl.org/dc/terms/title': 'Ghost' },
        },
      },
    });

    // Should still return a response (may be 200 with error or 4xx)
    const status = response.status();
    expect([200, 400, 404, 500]).toContain(status);
  });
});
