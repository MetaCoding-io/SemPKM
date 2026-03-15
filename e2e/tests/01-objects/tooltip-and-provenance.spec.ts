/**
 * Object Tooltip & Edge Provenance E2E Tests
 *
 * Tests:
 * - GET /browser/tooltip/{iri} — returns HTML tooltip for an object
 * - GET /browser/edge-provenance — returns provenance data for an edge
<<<<<<< HEAD
<<<<<<< HEAD
 *
 * Consolidated into 2 test() functions to stay within the
 * 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('Object Tooltip & Edge Provenance', () => {
  test('tooltip endpoint returns HTML for seed objects and handles missing IRIs', async ({ ownerRequest }) => {
    // 1. Tooltip for a seed Note object
    const noteIri = encodeURIComponent(SEED.notes.architecture.iri);
    const noteResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${noteIri}`);
    expect(noteResp.ok()).toBeTruthy();
    const noteHtml = await noteResp.text();
    expect(noteHtml.length).toBeGreaterThan(0);
    // Should contain the object label
    expect(noteHtml.toLowerCase()).toMatch(/architecture|event sourcing/i);

    // 2. Tooltip for a seed Person object
    const personIri = encodeURIComponent(SEED.people.alice.iri);
    const personResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${personIri}`);
    expect(personResp.ok()).toBeTruthy();
    const personHtml = await personResp.text();
    expect(personHtml.toLowerCase()).toMatch(/alice|chen/i);

    // 3. Tooltip for a non-existent object — should return 200 with
    //    fallback content or 404, not 500
    const fakeIri = encodeURIComponent('urn:sempkm:does-not-exist-tooltip-test');
    const fakeResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${fakeIri}`);
    expect([200, 404].includes(fakeResp.status())).toBeTruthy();
    expect(fakeResp.status()).toBeLessThan(500);
  });

  test('edge provenance endpoint returns data for edges and handles missing edges', async ({ ownerRequest }) => {
    // 1. Create an edge between known seed objects
=======
=======
 *
 * Consolidated into 2 test() functions to stay within the
 * 5/minute magic-link rate limit.
>>>>>>> gsd/M003/S10
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('Object Tooltip & Edge Provenance', () => {
  test('tooltip endpoint returns HTML for seed objects and handles missing IRIs', async ({ ownerRequest }) => {
    // 1. Tooltip for a seed Note object
    const noteIri = encodeURIComponent(SEED.notes.architecture.iri);
    const noteResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${noteIri}`);
    expect(noteResp.ok()).toBeTruthy();
    const noteHtml = await noteResp.text();
    expect(noteHtml.length).toBeGreaterThan(0);
    // Should contain the object label
    expect(noteHtml.toLowerCase()).toMatch(/architecture|event sourcing/i);

    // 2. Tooltip for a seed Person object
    const personIri = encodeURIComponent(SEED.people.alice.iri);
    const personResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${personIri}`);
    expect(personResp.ok()).toBeTruthy();
    const personHtml = await personResp.text();
    expect(personHtml.toLowerCase()).toMatch(/alice|chen/i);

    // 3. Tooltip for a non-existent object — should return 200 with
    //    fallback content or 404, not 500
    const fakeIri = encodeURIComponent('urn:sempkm:does-not-exist-tooltip-test');
    const fakeResp = await ownerRequest.get(`${BASE_URL}/browser/tooltip/${fakeIri}`);
    expect([200, 404].includes(fakeResp.status())).toBeTruthy();
    expect(fakeResp.status()).toBeLessThan(500);
  });

<<<<<<< HEAD
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
>>>>>>> gsd/M003/S03
=======
  test('edge provenance endpoint returns data for edges and handles missing edges', async ({ ownerRequest }) => {
    // 1. Create an edge between known seed objects
>>>>>>> gsd/M003/S10
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

<<<<<<< HEAD
<<<<<<< HEAD
    // 2. Query edge provenance — uses subject/predicate/target query params
    const provenanceResp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
      params: {
        subject: SEED.projects.sempkm.iri,
        predicate: 'http://purl.org/dc/terms/creator',
        target: SEED.people.alice.iri,
      },
    });
    expect(provenanceResp.ok()).toBeTruthy();
    const provData = await provenanceResp.json();

    // Should have provenance fields
    expect(provData).toBeDefined();
    expect(provData.predicate_qname).toBeDefined();
    // Should have timestamp from the event that created the edge
    // (may be null if event lookup fails, but field should exist)
    expect('timestamp' in provData).toBeTruthy();
    expect('event_iri' in provData).toBeTruthy();
    expect('source' in provData).toBeTruthy();

    // 3. Edge provenance for a non-existent edge — should return
    //    gracefully (200 with null fields, or 404), not 500
    const fakeResp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
      params: {
        subject: 'urn:sempkm:fake:prov-test-source',
        predicate: 'http://purl.org/dc/terms/subject',
        target: 'urn:sempkm:fake:prov-test-target',
      },
    });
    expect([200, 404].includes(fakeResp.status())).toBeTruthy();
    if (fakeResp.status() === 200) {
      const fakeData = await fakeResp.json();
      // For non-existent edges, event_iri and timestamp should be null
      expect(fakeData.event_iri).toBeNull();
      expect(fakeData.timestamp).toBeNull();
    }
=======
    // Query edge provenance
    const resp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
=======
    // 2. Query edge provenance — uses subject/predicate/target query params
    const provenanceResp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
>>>>>>> gsd/M003/S10
      params: {
        subject: SEED.projects.sempkm.iri,
        predicate: 'http://purl.org/dc/terms/creator',
        target: SEED.people.alice.iri,
      },
    });
    expect(provenanceResp.ok()).toBeTruthy();
    const provData = await provenanceResp.json();

    // Should have provenance fields
    expect(provData).toBeDefined();
    expect(provData.predicate_qname).toBeDefined();
    // Should have timestamp from the event that created the edge
    // (may be null if event lookup fails, but field should exist)
    expect('timestamp' in provData).toBeTruthy();
    expect('event_iri' in provData).toBeTruthy();
    expect('source' in provData).toBeTruthy();

    // 3. Edge provenance for a non-existent edge — should return
    //    gracefully (200 with null fields, or 404), not 500
    const fakeResp = await ownerRequest.get(`${BASE_URL}/browser/edge-provenance`, {
      params: {
        subject: 'urn:sempkm:fake:prov-test-source',
        predicate: 'http://purl.org/dc/terms/subject',
        target: 'urn:sempkm:fake:prov-test-target',
      },
    });
<<<<<<< HEAD
    // Should handle gracefully (200 with empty or 404)
    expect([200, 404].includes(resp.status())).toBeTruthy();
>>>>>>> gsd/M003/S03
=======
    expect([200, 404].includes(fakeResp.status())).toBeTruthy();
    if (fakeResp.status() === 200) {
      const fakeData = await fakeResp.json();
      // For non-existent edges, event_iri and timestamp should be null
      expect(fakeData.event_iri).toBeNull();
      expect(fakeData.timestamp).toBeNull();
    }
>>>>>>> gsd/M003/S10
  });
});
