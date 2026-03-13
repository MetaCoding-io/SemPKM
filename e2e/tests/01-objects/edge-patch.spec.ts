/**
 * Edge Patch E2E Tests
 *
 * Tests the edge.patch command: updating annotation properties on an
 * existing edge resource while source/target/predicate remain immutable.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Edge Patch', () => {
  test('patch an edge annotation property via API', async ({ ownerRequest }) => {
    // Create two objects
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Patch Edge Source' } } },
        { command: 'object.create', params: { type: TYPES.Person, properties: { 'http://xmlns.com/foaf/0.1/name': 'Patch Edge Target' } } },
      ],
    });
    expect(createResp.ok()).toBeTruthy();
    const { results } = await createResp.json();
    const sourceIri = results[0].iri;
    const targetIri = results[1].iri;

    // Create an edge
    const edgeResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'edge.create',
        params: {
          source: sourceIri,
          target: targetIri,
          predicate: 'http://purl.org/dc/terms/contributor',
        },
      },
    });
    expect(edgeResp.ok()).toBeTruthy();
    const edgeData = await edgeResp.json();
    // The edge.create result should return the edge IRI
    const edgeIri = edgeData.results[0].iri;
    expect(edgeIri).toBeTruthy();

    // Patch the edge with a description annotation
    const patchResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'edge.patch',
        params: {
          iri: edgeIri,
          properties: {
            'http://purl.org/dc/terms/description': 'Primary contributor',
          },
        },
      },
    });
    expect(patchResp.ok()).toBeTruthy();
    const patchData = await patchResp.json();
    expect(patchData.event_iri).toBeTruthy();

    // Verify the annotation persists via SPARQL
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?desc FROM <urn:sempkm:current> WHERE { <${edgeIri}> <http://purl.org/dc/terms/description> ?desc }`,
      },
    });
    expect(verifyResp.ok()).toBeTruthy();
    const verifyData = await verifyResp.json();
    expect(verifyData.results.bindings.length).toBe(1);
    expect(verifyData.results.bindings[0].desc.value).toBe('Primary contributor');
  });
});
