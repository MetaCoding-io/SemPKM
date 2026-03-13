/**
 * Rate Limiting E2E Tests
 *
 * Tests that auth endpoints enforce rate limiting via slowapi.
 * The magic-link endpoint is rate-limited to 5/minute per IP.
 *
 * IMPORTANT: This test file is in 99-rate-limiting/ so it runs LAST in the suite.
 * Rate-limit tests exhaust the per-IP request budget, which would break auth fixtures
 * in subsequent test files if run earlier. By running last, nothing depends on the
 * endpoints being available afterward.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Rate Limiting', () => {
  test('magic-link endpoint returns 429 after exceeding rate limit, with error body', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;

    let got429 = false;
    let rateLimitBody = '';

    // Send rapid requests to trigger rate limiting (limit is 5/minute)
    for (let i = 0; i < 8; i++) {
      const resp = await ctx.post(`${BASE_URL}/api/auth/magic-link`, {
        data: { email: `ratelimit-test-${i}@example.com` },
      });

      if (resp.status() === 429) {
        got429 = true;
        rateLimitBody = await resp.text();
        break;
      }
    }

    // Verify we hit the rate limit
    expect(got429).toBe(true);

    // Verify the 429 response has a meaningful error body
    expect(rateLimitBody.length).toBeGreaterThan(0);
    // slowapi returns JSON with "Rate limit exceeded" message
    expect(rateLimitBody.toLowerCase()).toContain('rate limit');
  });
});
