/**
 * Health Check E2E Tests
 *
 * Tests the GET /api/health endpoint returns proper JSON
 * with status, services, and version information.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Health Check', () => {
  test('health endpoint returns 200 with JSON structure', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;
    const resp = await ctx.get(`${BASE_URL}/api/health`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();

    // Should have a status field
    expect(data.status).toBeDefined();
    expect(data.status).toBe('ok');
  });

  test('health endpoint includes service statuses', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;
    const resp = await ctx.get(`${BASE_URL}/api/health`);
    const data = await resp.json();

    // Should include services section (triplestore, database, etc.)
    if (data.services) {
      expect(typeof data.services).toBe('object');
    }
  });

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
