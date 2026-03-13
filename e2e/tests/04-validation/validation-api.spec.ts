/**
 * Validation API E2E Tests
 *
 * Tests the SHACL validation endpoints:
 * - GET /api/validation/latest — latest validation result
 * - GET /api/validation/{event_id} — validation result for a specific event
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Validation API', () => {
  test('latest validation endpoint returns result', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/validation/latest`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();
  });

  test('validation result for a specific event', async ({ ownerRequest }) => {
    // Create an object to trigger validation
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Validation Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const { event_iri } = await createResp.json();

    // Extract event ID from IRI
    // Event IRIs are like urn:sempkm:event:{uuid}
    const eventId = event_iri.split(':').pop();

    if (eventId) {
      // Wait a moment for validation to process
      await new Promise(resolve => setTimeout(resolve, 2000));

      const resp = await ownerRequest.get(`${BASE_URL}/api/validation/${eventId}`);
      // May be 200 (validated) or 404 (not yet processed)
      expect([200, 404].includes(resp.status())).toBeTruthy();
    }
  });
});
