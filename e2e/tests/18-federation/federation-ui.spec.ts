/**
 * Federation UI Partials E2E Tests
 *
 * Tests federation UI endpoints:
 * - GET /api/federation/inbox-partial — inbox panel HTML
 * - GET /api/federation/collab-partial — collaboration panel HTML
 * - GET /api/federation/shared-graphs — shared graph list JSON
 * - GET /api/federation/contacts — contact list JSON
 * - GET /api/federation/shared-nav — shared nav tree HTML
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Federation UI Partials', () => {
  test('inbox partial returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/inbox-partial`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
    // Should be HTML content (not JSON)
    expect(html).toMatch(/<|<!|class=|id=/i);
  });

  test('collab partial returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/collab-partial`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    expect(html.length).toBeGreaterThan(0);
  });

  test('shared graphs endpoint returns JSON array', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/shared-graphs`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('contacts endpoint returns JSON array', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/contacts`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('shared nav endpoint returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/shared-nav`);
    expect(resp.ok()).toBeTruthy();

    const html = await resp.text();
    // May be empty if no shared graphs exist, but should return 200
    expect(typeof html).toBe('string');
  });

  test('inbox notifications endpoint returns JSON', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/inbox`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    // Should return notifications array or object
    expect(data).toBeDefined();
  });
});
