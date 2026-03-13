/**
 * Miscellaneous Endpoints E2E Tests
 *
 * Tests remaining API endpoints with zero e2e coverage:
 * - GET /api/monitoring/config — PostHog config
 * - GET /browser/icons — icon mappings JSON
 * - GET /browser/my-views — user's view links HTML
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Monitoring Config', () => {
  test('monitoring config endpoint returns PostHog configuration', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/monitoring/config`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();
    // PostHog config may have api_key (possibly empty/null) and host fields
    // The response shape matches the PostHogConfig pydantic model
  });
});

test.describe('Icons Endpoint', () => {
  test('icons endpoint returns JSON with icon mappings', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/icons`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();
    expect(typeof data).toBe('object');

    // Should have at least one icon mapping (for the installed model types)
    const keys = Object.keys(data);
    expect(keys.length).toBeGreaterThan(0);
  });
});

test.describe('My Views Endpoint', () => {
  test('my-views endpoint returns HTML fragment', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/my-views`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
    // Should contain view links or view menu items
    expect(html).toMatch(/<|view|table|card|graph/i);
  });
});

test.describe('Nav Tree Endpoint', () => {
  test('nav-tree endpoint returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/nav-tree`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
  });
});

test.describe('Explorer Tree Endpoint', () => {
  test('explorer tree endpoint returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/browser/explorer/tree`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
  });
});
