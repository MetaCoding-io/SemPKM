/**
 * Federation UI Partials E2E Tests
 *
 * Tests federation UI endpoints in a single test() to stay within
 * the 5/minute magic-link rate limit:
 * - GET /api/federation/inbox-partial — inbox panel HTML
 * - GET /api/federation/collab-partial — collaboration panel HTML
 * - GET /api/federation/shared-graphs — shared graph list JSON
 * - GET /api/federation/contacts — contact list JSON
 * - GET /api/federation/shared-nav — shared nav tree HTML
 * - GET /api/inbox — inbox notifications JSON
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Federation UI Partials', () => {
  test('all federation partials and endpoints return valid responses', async ({ ownerRequest }) => {
    // 1. Inbox partial — returns HTML content for htmx swap
    const inboxResp = await ownerRequest.get(`${BASE_URL}/api/federation/inbox-partial`);
    expect(inboxResp.ok()).toBeTruthy();
    const inboxHtml = await inboxResp.text();
    expect(inboxHtml.length).toBeGreaterThan(0);
    // Should be HTML content (not JSON error)
    expect(inboxHtml).toMatch(/<|<!|class=|id=/i);

    // 2. Collab partial — returns HTML content for collaboration panel
    const collabResp = await ownerRequest.get(`${BASE_URL}/api/federation/collab-partial`);
    expect(collabResp.ok()).toBeTruthy();
    const collabHtml = await collabResp.text();
    expect(collabHtml.length).toBeGreaterThan(0);
    // Should contain HTML structure
    expect(collabHtml).toMatch(/<|<!|class=|id=/i);

    // 3. Shared graphs — returns JSON array (empty if no shared graphs)
    const graphsResp = await ownerRequest.get(`${BASE_URL}/api/federation/shared-graphs`);
    expect(graphsResp.ok()).toBeTruthy();
    const graphsData = await graphsResp.json();
    expect(Array.isArray(graphsData)).toBe(true);

    // 4. Contacts — returns JSON array (empty if no contacts)
    const contactsResp = await ownerRequest.get(`${BASE_URL}/api/federation/contacts`);
    expect(contactsResp.ok()).toBeTruthy();
    const contactsData = await contactsResp.json();
    expect(Array.isArray(contactsData)).toBe(true);

    // 5. Shared nav — returns HTML (may be empty if no shared graphs)
    const navResp = await ownerRequest.get(`${BASE_URL}/api/federation/shared-nav`);
    expect(navResp.ok()).toBeTruthy();
    const navHtml = await navResp.text();
    expect(typeof navHtml).toBe('string');

    // 6. Inbox notifications — returns JSON array via LDN inbox endpoint
    const notifResp = await ownerRequest.get(`${BASE_URL}/api/inbox`);
    expect(notifResp.ok()).toBeTruthy();
    const notifData = await notifResp.json();
    expect(Array.isArray(notifData)).toBe(true);
    // Each notification should have expected fields if any exist
    if (notifData.length > 0) {
      const first = notifData[0];
      expect(first.id).toBeDefined();
      expect(first.type).toBeDefined();
      expect(first.state).toBeDefined();
      expect(first.receivedAt).toBeDefined();
    }
  });
});
