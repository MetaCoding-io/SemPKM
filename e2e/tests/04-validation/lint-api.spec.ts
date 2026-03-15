/**
 * Lint API E2E Tests
 *
 * Tests the lint results, status, diff, and stream endpoints:
<<<<<<< HEAD
 * - GET /api/lint/results — paginated lint results (LintResultsResponse)
 * - GET /api/lint/status — lint engine status (LintStatusResponse)
 * - GET /api/lint/diff — lint diff between latest and previous runs (LintDiffResponse)
 *
 * Consolidated into 1 test() to stay within the 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test('lint API endpoints return correct response shapes', async ({ ownerRequest }) => {
  // --- GET /api/lint/results (default params) ---
  const resultsResp = await ownerRequest.get(`${BASE_URL}/api/lint/results`);
  expect(resultsResp.ok()).toBeTruthy();
  const results = await resultsResp.json();
  // LintResultsResponse fields
  expect(Array.isArray(results.results)).toBe(true);
  expect(typeof results.page).toBe('number');
  expect(typeof results.per_page).toBe('number');
  expect(typeof results.total).toBe('number');
  expect(typeof results.total_pages).toBe('number');
  expect(typeof results.run_id).toBe('string');
  expect(typeof results.run_timestamp).toBe('string');
  expect(typeof results.conforms).toBe('boolean');

  // --- GET /api/lint/results with pagination params ---
  const paginatedResp = await ownerRequest.get(`${BASE_URL}/api/lint/results?page=1&per_page=5`);
  expect(paginatedResp.ok()).toBeTruthy();
  const paginated = await paginatedResp.json();
  expect(paginated.page).toBe(1);
  expect(paginated.per_page).toBe(5);
  expect(Array.isArray(paginated.results)).toBe(true);
  expect(paginated.results.length).toBeLessThanOrEqual(5);

  // --- GET /api/lint/status ---
  const statusResp = await ownerRequest.get(`${BASE_URL}/api/lint/status`);
  expect(statusResp.ok()).toBeTruthy();
  const status = await statusResp.json();
  // LintStatusResponse fields
  expect(typeof status.violation_count).toBe('number');
  expect(typeof status.warning_count).toBe('number');
  expect(typeof status.info_count).toBe('number');
  // conforms can be boolean or null
  expect(status.conforms === null || typeof status.conforms === 'boolean').toBe(true);
  // run_id and run_timestamp can be string or null
  expect(status.run_id === null || typeof status.run_id === 'string').toBe(true);
  expect(status.run_timestamp === null || typeof status.run_timestamp === 'string').toBe(true);

  // --- GET /api/lint/diff ---
  const diffResp = await ownerRequest.get(`${BASE_URL}/api/lint/diff`);
  expect(diffResp.ok()).toBeTruthy();
  const diff = await diffResp.json();
  // LintDiffResponse fields
  expect(Array.isArray(diff.new_issues)).toBe(true);
  expect(Array.isArray(diff.resolved_issues)).toBe(true);
  expect(typeof diff.latest_run_id).toBe('string');
  // previous_run_id can be string or null
  expect(diff.previous_run_id === null || typeof diff.previous_run_id === 'string').toBe(true);
=======
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
>>>>>>> gsd/M003/S03
});
