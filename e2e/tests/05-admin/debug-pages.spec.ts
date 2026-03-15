/**
 * Debug Pages Access Control E2E Tests
 *
<<<<<<< HEAD
 * Tests that debug pages (/sparql, /events) are:
 * - Accessible to the owner (200)
 * - Forbidden for members (403 or redirect)
 *
 * Note: Debug routes have no /debug/ prefix — they are mounted at
 * /sparql and /events directly from the debug router.
 *
 * Consolidated into 2 test() functions (1 owner, 1 member) to stay
 * within the 5/minute magic-link rate limit.
=======
 * Tests that debug pages (/debug/sparql, /debug/events) are:
 * - Accessible to the owner (200)
 * - Forbidden for members (403)
>>>>>>> gsd/M003/S03
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Debug Pages Access Control', () => {
<<<<<<< HEAD
  test('owner can access both debug pages', async ({ ownerRequest }) => {
    // 1. Owner can access /sparql — returns 200 with HTML content
    const sparqlResp = await ownerRequest.get(`${BASE_URL}/sparql`);
    expect(sparqlResp.ok()).toBeTruthy();
    const sparqlHtml = await sparqlResp.text();
    expect(sparqlHtml).toMatch(/<|<!DOCTYPE/i);
    // Should contain SPARQL-related content
    expect(sparqlHtml.toLowerCase()).toMatch(/sparql|query/i);

    // 2. Owner can access /events — returns 200 with HTML content
    const eventsResp = await ownerRequest.get(`${BASE_URL}/events`);
    expect(eventsResp.ok()).toBeTruthy();
    const eventsHtml = await eventsResp.text();
    expect(eventsHtml).toMatch(/<|<!DOCTYPE/i);
    // Should contain event-related content
    expect(eventsHtml.toLowerCase()).toMatch(/event|command|console/i);
  });

  test('member cannot access debug pages', async ({ memberPage }) => {
    // 1. Member tries to access /sparql — should get 403 or redirect
    const sparqlResp = await memberPage.goto(`${BASE_URL}/sparql`);
    if (sparqlResp) {
      // require_role("owner") raises 403 for non-owner users
      const status = sparqlResp.status();
      expect(
        status === 403 || status === 401 || status === 302 || status === 307 || status >= 400
      ).toBeTruthy();
    }

    // 2. Member tries to access /events — should get 403 or redirect
    const eventsResp = await memberPage.goto(`${BASE_URL}/events`);
    if (eventsResp) {
      const status = eventsResp.status();
      expect(
        status === 403 || status === 401 || status === 302 || status === 307 || status >= 400
      ).toBeTruthy();
=======
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
>>>>>>> gsd/M003/S03
    }
  });
});
