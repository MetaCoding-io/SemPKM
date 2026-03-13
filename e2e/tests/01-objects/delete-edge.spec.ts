/**
 * Edge Deletion E2E Tests
 *
 * Tests edge deletion via POST /browser/edge/delete.
 * Creates an edge between objects, deletes it, and verifies it is gone.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Edge Deletion', () => {
  test('delete an edge via API and verify it is removed', async ({ ownerRequest }) => {
    // Create two objects
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Edge Del Source' } } },
        { command: 'object.create', params: { type: TYPES.Concept, properties: { 'http://www.w3.org/2004/02/skos/core#prefLabel': 'Edge Del Target' } } },
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
          predicate: 'http://purl.org/dc/terms/subject',
        },
      },
    });
    expect(edgeResp.ok()).toBeTruthy();

    // Verify edge exists
    const checkResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${sourceIri}> <http://purl.org/dc/terms/subject> <${targetIri}> }`,
      },
    });
    const checkData = await checkResp.json();
    expect(checkData.boolean).toBe(true);

    // Delete the edge
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/edge/delete`, {
      data: {
        source: sourceIri,
        target: targetIri,
        predicate: 'http://purl.org/dc/terms/subject',
      },
    });
    expect(deleteResp.ok()).toBeTruthy();

    // Verify edge is gone
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${sourceIri}> <http://purl.org/dc/terms/subject> <${targetIri}> }`,
      },
    });
    const verifyData = await verifyResp.json();
    expect(verifyData.boolean).toBe(false);
  });
});
