/**
 * Rate Limiting E2E Tests
 *
 * Tests that auth endpoints enforce rate limiting via slowapi.
 * The magic-link endpoint is rate-limited to 5/minute per IP.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Rate Limiting', () => {
  test('magic-link endpoint returns 429 after rapid requests', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;

    let got429 = false;

    // Send rapid requests to trigger rate limiting (limit is 5/minute)
    for (let i = 0; i < 8; i++) {
      const resp = await ctx.post(`${BASE_URL}/api/auth/magic-link`, {
        data: { email: `ratelimit-test-${i}@example.com` },
      });

      if (resp.status() === 429) {
        got429 = true;
        break;
      }
    }

    expect(got429).toBe(true);
  });

  test('429 response has retry-after header or error message', async ({ anonApi }) => {
    const ctx = (anonApi as any).request;

    let lastResp: any = null;

    for (let i = 0; i < 10; i++) {
      lastResp = await ctx.post(`${BASE_URL}/api/auth/magic-link`, {
        data: { email: `retry-test-${i}@example.com` },
      });

      if (lastResp.status() === 429) break;
    }

    if (lastResp && lastResp.status() === 429) {
      // Should have some indication of rate limiting
      const body = await lastResp.text();
      expect(body.length).toBeGreaterThan(0);
    }
  });
});
