/**
 * Object Deletion E2E Tests
 *
 * Tests single and bulk object deletion via POST /browser/objects/delete.
 * Verifies objects are removed from the current-state graph after deletion.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Object Deletion', () => {
  test('delete a single object via API and verify it is gone', async ({ ownerRequest }) => {
    // Create an object
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Delete Me Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const { results } = await createResp.json();
    const objectIri = results[0].iri;

    // Confirm it exists via SPARQL
    const checkResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: `ASK FROM <urn:sempkm:current> { <${objectIri}> ?p ?o }` },
    });
    const checkData = await checkResp.json();
    expect(checkData.boolean).toBe(true);

    // Delete it
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/objects/delete`, {
      data: { iris: [objectIri] },
    });
    expect(deleteResp.ok()).toBeTruthy();

    // Verify it is gone
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: `ASK FROM <urn:sempkm:current> { <${objectIri}> ?p ?o }` },
    });
    const verifyData = await verifyResp.json();
    expect(verifyData.boolean).toBe(false);
  });

  test('bulk delete multiple objects via API', async ({ ownerRequest }) => {
    // Create 3 objects
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Bulk Del 1' } } },
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Bulk Del 2' } } },
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Bulk Del 3' } } },
      ],
    });
    expect(createResp.ok()).toBeTruthy();
    const { results } = await createResp.json();
    const iris = results.map((r: any) => r.iri);
    expect(iris).toHaveLength(3);

    // Bulk delete
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/objects/delete`, {
      data: { iris },
    });
    expect(deleteResp.ok()).toBeTruthy();

    // Verify all are gone
    for (const iri of iris) {
      const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
        data: { query: `ASK FROM <urn:sempkm:current> { <${iri}> ?p ?o }` },
      });
      const verifyData = await verifyResp.json();
      expect(verifyData.boolean).toBe(false);
    }
  });
});
