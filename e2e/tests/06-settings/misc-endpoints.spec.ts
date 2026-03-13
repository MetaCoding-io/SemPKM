/**
 * Miscellaneous Endpoints E2E Tests
 *
 * Tests remaining API endpoints with zero prior e2e coverage:
 * - GET /api/monitoring/config — PostHog config (public, no auth required)
 * - GET /browser/icons — icon mappings JSON (tree, tab, graph contexts)
 * - GET /browser/my-views — user's promoted view links HTML fragment
 * - GET /browser/nav-tree — nav tree HTML
 * - GET /browser/explorer/tree — explorer tree HTML
 *
 * Consolidated into 1 test() to stay within the 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test('misc endpoints return correct response shapes', async ({ ownerRequest }) => {
  // --- GET /api/monitoring/config (PostHog config — public endpoint) ---
  const monResp = await ownerRequest.get(`${BASE_URL}/api/monitoring/config`);
  expect(monResp.ok()).toBeTruthy();
  const monData = await monResp.json();
  // PostHogConfig model: enabled (bool), api_key (str), host (str)
  expect(typeof monData.enabled).toBe('boolean');
  expect(typeof monData.api_key).toBe('string');
  expect(typeof monData.host).toBe('string');

  // --- GET /browser/icons ---
  const iconsResp = await ownerRequest.get(`${BASE_URL}/browser/icons`);
  expect(iconsResp.ok()).toBeTruthy();
  const iconsData = await iconsResp.json();
  expect(iconsData).toBeDefined();
  // Icon map has tree, tab, graph contexts
  expect(typeof iconsData.tree).toBe('object');
  expect(typeof iconsData.tab).toBe('object');
  expect(typeof iconsData.graph).toBe('object');
  // At least one icon mapping should exist (from installed models)
  const allKeys = [
    ...Object.keys(iconsData.tree || {}),
    ...Object.keys(iconsData.tab || {}),
    ...Object.keys(iconsData.graph || {}),
  ];
  expect(allKeys.length).toBeGreaterThan(0);

  // --- GET /browser/my-views ---
  const viewsResp = await ownerRequest.get(`${BASE_URL}/browser/my-views`);
  expect(viewsResp.ok()).toBeTruthy();
  const viewsHtml = await viewsResp.text();
  expect(viewsHtml.length).toBeGreaterThan(0);
  // Returns either promoted view links or an empty-state message
  expect(viewsHtml).toMatch(/<div|<a|view|No promoted/i);

  // --- GET /browser/nav-tree ---
  const navResp = await ownerRequest.get(`${BASE_URL}/browser/nav-tree`);
  expect(navResp.ok()).toBeTruthy();
  const navHtml = await navResp.text();
  expect(navHtml.length).toBeGreaterThan(0);

  // --- GET /browser/explorer/tree ---
  const explorerResp = await ownerRequest.get(`${BASE_URL}/browser/explorer/tree`);
  expect(explorerResp.ok()).toBeTruthy();
  const explorerHtml = await explorerResp.text();
  expect(explorerHtml.length).toBeGreaterThan(0);
});
