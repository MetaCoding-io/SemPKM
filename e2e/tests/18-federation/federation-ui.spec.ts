/**
 * Federation UI Partials E2E Tests
 *
<<<<<<< HEAD
<<<<<<< HEAD
 * Tests federation UI endpoints in a single test() to stay within
 * the 5/minute magic-link rate limit:
=======
 * Tests federation UI endpoints:
>>>>>>> gsd/M003/S03
=======
 * Tests federation UI endpoints in a single test() to stay within
 * the 5/minute magic-link rate limit:
>>>>>>> gsd/M003/S10
 * - GET /api/federation/inbox-partial — inbox panel HTML
 * - GET /api/federation/collab-partial — collaboration panel HTML
 * - GET /api/federation/shared-graphs — shared graph list JSON
 * - GET /api/federation/contacts — contact list JSON
 * - GET /api/federation/shared-nav — shared nav tree HTML
<<<<<<< HEAD
<<<<<<< HEAD
 * - GET /api/inbox — inbox notifications JSON
=======
>>>>>>> gsd/M003/S03
=======
 * - GET /api/inbox — inbox notifications JSON
>>>>>>> gsd/M003/S10
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Federation UI Partials', () => {
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S10
  test('all federation partials and endpoints return valid responses', async ({ ownerRequest }) => {
    // 1. Inbox partial — returns HTML content for htmx swap
    const inboxResp = await ownerRequest.get(`${BASE_URL}/api/federation/inbox-partial`);
    expect(inboxResp.ok()).toBeTruthy();
    const inboxHtml = await inboxResp.text();
    expect(inboxHtml.length).toBeGreaterThan(0);
    // Should be HTML content (not JSON error)
    expect(inboxHtml).toMatch(/<|<!|class=|id=/i);
<<<<<<< HEAD

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
=======
  test('inbox partial returns HTML', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/federation/inbox-partial`);
    expect(resp.ok()).toBeTruthy();
=======
>>>>>>> gsd/M003/S10

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

<<<<<<< HEAD
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
>>>>>>> gsd/M003/S03
=======
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
>>>>>>> gsd/M003/S10
  });
});
