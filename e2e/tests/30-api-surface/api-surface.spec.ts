/**
 * API Surface E2E Tests
 *
 * Exercises all four M013 API-surface endpoints through the full Docker
 * Compose stack (nginx → FastAPI → triplestore):
 *
 *   1. GET  /.well-known/sempkm   — instance discovery
 *   2. GET  /api/types            — list available types
 *   3. GET  /api/shapes/{iri}     — property shapes for a real type
 *   4. GET  /api/shapes/{iri}     — 404 for a nonexistent type
 *   5. POST /api/context-query    — keyword search
 *   6. POST /api/context-query    — validation (empty body → 400)
 *
 * All requests use `ownerRequest` (authenticated APIRequestContext with
 * session cookie) — no browser navigation needed.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('API Surface', () => {
  // -------------------------------------------------------------------
  // 1. Instance discovery
  // -------------------------------------------------------------------
  test('GET /.well-known/sempkm returns discovery document', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/.well-known/sempkm`);
    expect(resp.status()).toBe(200);

    const data = await resp.json();

    // Version
    expect(data.version).toBeDefined();
    expect(typeof data.version).toBe('string');
    expect(data.version.length).toBeGreaterThan(0);

    // Endpoints map — must include the four M013 endpoints
    expect(data.endpoints).toBeDefined();
    expect(data.endpoints.types).toBe('/api/types');
    expect(data.endpoints.shapes).toBe('/api/shapes/{type_iri}');
    expect(data.endpoints.context_query).toBe('/api/context-query');

    // Capabilities list
    expect(data.capabilities).toBeDefined();
    expect(Array.isArray(data.capabilities)).toBe(true);
    expect(data.capabilities).toContain('types');
    expect(data.capabilities).toContain('shapes');
    expect(data.capabilities).toContain('context-query');

    // Auth section
    expect(data.auth).toBeDefined();
    expect(data.auth.session).toBe(true);
    expect(data.auth.api_key).toBe(true);
  });

  test('GET /.well-known/sempkm requires authentication', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;
    const resp = await ctx.get(`${BASE_URL}/.well-known/sempkm`);
    // Unauthenticated → 401 or redirect
    expect([401, 403].includes(resp.status()) || resp.status() >= 300).toBeTruthy();
  });

  // -------------------------------------------------------------------
  // 2. Types listing
  // -------------------------------------------------------------------
  test('GET /api/types returns array with iri and label', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/types`);
    expect(resp.status()).toBe(200);

    const data = await resp.json();
    expect(data.types).toBeDefined();
    expect(Array.isArray(data.types)).toBe(true);

    // At least one Mental Model must be installed in the test stack
    expect(data.types.length).toBeGreaterThanOrEqual(1);

    // Every type entry has required fields
    for (const t of data.types) {
      expect(t.iri).toBeDefined();
      expect(typeof t.iri).toBe('string');
      expect(t.iri.length).toBeGreaterThan(0);

      expect(t.label).toBeDefined();
      expect(typeof t.label).toBe('string');
      expect(t.label.length).toBeGreaterThan(0);
    }
  });

  // -------------------------------------------------------------------
  // 3. Shapes for a real type
  // -------------------------------------------------------------------
  test('GET /api/shapes/{type_iri} returns properties for a real type', async ({
    ownerRequest,
  }) => {
    // First, get a real type IRI from /api/types
    const typesResp = await ownerRequest.get(`${BASE_URL}/api/types`);
    expect(typesResp.status()).toBe(200);
    const typesData = await typesResp.json();
    expect(typesData.types.length).toBeGreaterThanOrEqual(1);

    const realTypeIri = typesData.types[0].iri;

    // Now fetch shapes for that type
    const shapesResp = await ownerRequest.get(
      `${BASE_URL}/api/shapes/${encodeURIComponent(realTypeIri)}`,
    );
    expect(shapesResp.status()).toBe(200);

    const shapesData = await shapesResp.json();

    // Must have a properties array
    expect(shapesData.properties).toBeDefined();
    expect(Array.isArray(shapesData.properties)).toBe(true);
    // A real type should have at least one property shape
    expect(shapesData.properties.length).toBeGreaterThanOrEqual(1);

    // Each property has at minimum an iri (path) and label
    for (const prop of shapesData.properties) {
      expect(prop.path).toBeDefined();
      expect(typeof prop.path).toBe('string');
    }
  });

  // -------------------------------------------------------------------
  // 4. Shapes 404 for nonexistent type
  // -------------------------------------------------------------------
  test('GET /api/shapes/{type_iri} returns 404 for nonexistent type', async ({
    ownerRequest,
  }) => {
    const resp = await ownerRequest.get(
      `${BASE_URL}/api/shapes/${encodeURIComponent('urn:nonexistent:FakeType')}`,
    );
    expect(resp.status()).toBe(404);
  });

  // -------------------------------------------------------------------
  // 5. Context-query keyword search
  // -------------------------------------------------------------------
  test('POST /api/context-query with keywords returns results array', async ({
    ownerRequest,
  }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/context-query`, {
      data: { keywords: 'test' },
    });
    expect(resp.status()).toBe(200);

    const data = await resp.json();

    // Response shape: { results: [...], total: N }
    expect(data.results).toBeDefined();
    expect(Array.isArray(data.results)).toBe(true);
    expect(typeof data.total).toBe('number');
    expect(data.total).toBe(data.results.length);

    // If there are results, verify each has the expected fields
    for (const r of data.results) {
      expect(r.iri).toBeDefined();
      expect(typeof r.iri).toBe('string');
      expect(r.match_type).toBeDefined();
      expect(typeof r.match_type).toBe('string');
    }
  });

  // -------------------------------------------------------------------
  // 6. Context-query validation — empty body → 400
  // -------------------------------------------------------------------
  test('POST /api/context-query with empty body returns 400', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/context-query`, {
      data: {},
    });
    expect(resp.status()).toBe(400);

    const data = await resp.json();
    expect(data.detail).toBeDefined();
    expect(typeof data.detail).toBe('string');
    // Error message should mention that at least one field is required
    expect(data.detail.toLowerCase()).toContain('required');
  });
});
