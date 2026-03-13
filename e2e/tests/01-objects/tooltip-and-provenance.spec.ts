/**
 * Object Tooltip & Edge Provenance E2E Tests
 *
 * Tests:
 * - GET /browser/tooltip/{iri} — returns HTML tooltip for an object
 * - GET /browser/edge-provenance — returns provenance data for an edge
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';

test.describe('Object Tooltip', () => {
  test('tooltip endpoint returns HTML for a seed object', async ({ ownerRequest }) => {
    const encodedIri = encodeURIComponent(SEED.notes.architecture.iri);
    const resp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${encodedIri}`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);

    // Should contain the object's label/title
    expect(html).toMatch(/Architecture|Event Sourcing/i);
  });

  test('tooltip endpoint returns HTML for a person object', async ({ ownerRequest }) => {
    const encodedIri = encodeURIComponent(SEED.people.alice.iri);
    const resp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${encodedIri}`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html).toMatch(/Alice|Chen/i);
  });

  test('tooltip for non-existent object returns gracefully', async ({ ownerRequest }) => {
    const fakeIri = encodeURIComponent('urn:sempkm:does-not-exist');
    const resp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${fakeIri}`);
    // Should return 200 with empty/fallback content, or 404
    expect([200, 404].includes(resp.status())).toBeTruthy();
  });
});

test.describe('Edge Provenance', () => {
  test('edge provenance endpoint returns data for existing edge', async ({ ownerRequest }) => {
    // First create an edge between known objects
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'edge.create',
        params: {
          source: SEED.projects.sempkm.iri,
          target: SEED.people.alice.iri,
          predicate: 'http://purl.org/dc/terms/creator',
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();

    // Query edge provenance
    const resp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
      params: {
        source: SEED.projects.sempkm.iri,
        target: SEED.people.alice.iri,
        predicate: 'http://purl.org/dc/terms/creator',
      },
    });
    expect(resp.ok()).toBeTruthy();

    const data = await resp.text();
    expect(data.length).toBeGreaterThan(0);
  });

  test('edge provenance for non-existent edge returns gracefully', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
      params: {
        source: 'urn:sempkm:fake:source',
        target: 'urn:sempkm:fake:target',
        predicate: 'http://purl.org/dc/terms/subject',
      },
    });
    // Should handle gracefully (200 with empty or 404)
    expect([200, 404].includes(resp.status())).toBeTruthy();
  });
});
