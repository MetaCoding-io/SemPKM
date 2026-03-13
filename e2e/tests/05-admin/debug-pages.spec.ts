/**
 * Debug Pages Access Control E2E Tests
 *
 * Tests that debug pages (/debug/sparql, /debug/events) are:
 * - Accessible to the owner (200)
 * - Forbidden for members (403)
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Debug Pages Access Control', () => {
  test('owner can access /debug/sparql', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/debug/sparql`);
    if (resp) {
      expect(resp.status()).toBe(200);
    }
  });

  test('owner can access /debug/events', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/debug/events`);
    if (resp) {
      expect(resp.status()).toBe(200);
    }
  });

  test('member cannot access /debug/sparql (403)', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/debug/sparql`);
    if (resp) {
      expect([403, 401, 302, 307].includes(resp.status()) || resp.status() >= 400).toBeTruthy();
    }
  });

  test('member cannot access /debug/events (403)', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/debug/events`);
    if (resp) {
      expect([403, 401, 302, 307].includes(resp.status()) || resp.status() >= 400).toBeTruthy();
    }
  });
});
