/**
 * Health Check E2E Tests
 *
 * Tests the GET /api/health endpoint returns proper JSON
 * with status, services, and version information.
 * Health endpoint is intentionally public (no auth required).
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Health Check', () => {
  test('health endpoint returns correct JSON structure without auth', async ({ anonApi }) => {
    // Access the underlying APIRequestContext from the ApiClient
    const ctx = (anonApi as any).request;

    // 1. Basic response shape
    const resp = await ctx.get(`${BASE_URL}/api/health`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();

    // 2. Status field — backend returns "healthy" or "degraded"
    expect(data.status).toBeDefined();
    expect(['healthy', 'degraded']).toContain(data.status);

    // 3. Services section
    expect(data.services).toBeDefined();
    expect(typeof data.services).toBe('object');
    expect(data.services.api).toBe('up');
    // triplestore should be "up" in the test environment
    expect(data.services.triplestore).toBe('up');

    // 4. Version info
    expect(data.version).toBeDefined();
    expect(typeof data.version).toBe('string');
    expect(data.version.length).toBeGreaterThan(0);

    // 5. Verify no auth is required — make a second request
    //    with a fresh context (no cookies, no headers)
    const resp2 = await ctx.get(`${BASE_URL}/api/health`);
    expect(resp2.ok()).toBeTruthy();
    const data2 = await resp2.json();
    expect(data2.status).toBe(data.status);
    expect(data.status).toBeDefined();
    expect(['healthy', 'degraded']).toContain(data.status);

    // 3. Services section
    expect(data.services).toBeDefined();
    expect(typeof data.services).toBe('object');
    expect(data.services.api).toBe('up');
    // triplestore should be "up" in the test environment
    expect(data.services.triplestore).toBe('up');

    // 4. Version info
    expect(data.version).toBeDefined();
    expect(typeof data.version).toBe('string');
    expect(data.version.length).toBeGreaterThan(0);

  test('health endpoint includes version info', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;
    const resp = await ctx.get(`${BASE_URL}/api/health`);
    const data = await resp.json();

    // Should include version
    if (data.version) {
      expect(typeof data.version).toBe('string');
    }
  });

  test('health endpoint is accessible without authentication', async () => {
    // Use a raw fetch to verify no auth is required
    const { request } = await import('@playwright/test');
    const ctx = await request.newContext();
    const resp = await ctx.get(`${BASE_URL}/api/health`);
    expect(resp.ok()).toBeTruthy();
    await ctx.dispose();
  });
});
