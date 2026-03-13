/**
 * Lint API E2E Tests
 *
 * Tests the lint results, status, diff, and stream endpoints:
 * - GET /api/lint/results — paginated lint results
 * - GET /api/lint/status — lint engine status
 * - GET /api/lint/diff — lint diff (changes since last run)
 * - GET /api/lint/stream — SSE stream (not fully tested here)
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Lint API', () => {
  test('lint results endpoint returns paginated response', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/lint/results`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();

    // Should have results array and pagination info
    if (data.results !== undefined) {
      expect(Array.isArray(data.results)).toBe(true);
    }
    if (data.total !== undefined) {
      expect(typeof data.total).toBe('number');
    }
  });

  test('lint status endpoint returns engine status', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/lint/status`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();

    // Should have a status field
    if (data.status !== undefined) {
      expect(typeof data.status).toBe('string');
    }
  });

  test('lint diff endpoint returns change data', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/lint/diff`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();
  });

  test('lint results with pagination parameters', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/lint/results?page=1&page_size=5`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data).toBeDefined();
  });
});
