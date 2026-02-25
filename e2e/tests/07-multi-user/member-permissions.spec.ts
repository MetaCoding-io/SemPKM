/**
 * Member Permissions E2E Tests
 *
 * Tests that member users can perform allowed operations (create, edit)
 * but cannot access admin features.
 */
import { test, expect, MEMBER_EMAIL, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Member Permissions', () => {
  test('member can access the workspace', async ({ memberPage }) => {
    await memberPage.goto(`${BASE_URL}/browser/`);
    await memberPage.waitForSelector('.workspace-container, .dashboard-layout', { timeout: 15000 });

    // Workspace should load normally for members
    await expect(memberPage.locator('.workspace-container, .dashboard-layout')).toBeVisible();
  });

  test('member can create objects via API', async ({ memberPage }) => {
    const api = await memberPage.context().request;

    // Get the member's session cookie from the page context
    const cookies = await memberPage.context().cookies();
    const sessionCookie = cookies.find((c) => c.name === 'sempkm_session');

    if (sessionCookie) {
      const resp = await api.post(`${BASE_URL}/api/commands`, {
        headers: { Cookie: `sempkm_session=${sessionCookie.value}` },
        data: {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Member Created Note' },
          },
        },
      });

      expect(resp.ok()).toBeTruthy();
      const data = await resp.json();
      expect(data.results[0].iri).toBeTruthy();
    }
  });

  test('member can edit objects via API', async ({ memberPage }) => {
    const api = await memberPage.context().request;
    const cookies = await memberPage.context().cookies();
    const sessionCookie = cookies.find((c) => c.name === 'sempkm_session');

    if (sessionCookie) {
      // Create an object first
      const createResp = await api.post(`${BASE_URL}/api/commands`, {
        headers: { Cookie: `sempkm_session=${sessionCookie.value}` },
        data: {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Note to Patch by Member' },
          },
        },
      });
      const createData = await createResp.json();
      const objectIri = createData.results[0].iri;

      // Patch it
      const patchResp = await api.post(`${BASE_URL}/api/commands`, {
        headers: { Cookie: `sempkm_session=${sessionCookie.value}` },
        data: {
          command: 'object.patch',
          params: {
            iri: objectIri,
            properties: { 'http://purl.org/dc/terms/title': 'Patched by Member' },
          },
        },
      });

      expect(patchResp.ok()).toBeTruthy();
    }
  });

  test('member cannot access admin models page', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/admin/models`);

    if (resp) {
      const status = resp.status();
      expect([403, 401].includes(status) || status >= 400).toBeTruthy();
    }
  });

  test('member cannot access admin webhooks page', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/admin/webhooks`);

    if (resp) {
      const status = resp.status();
      expect([403, 401].includes(status) || status >= 400).toBeTruthy();
    }
  });

  test('member cannot invite other users', async ({ memberPage }) => {
    const api = await memberPage.context().request;
    const cookies = await memberPage.context().cookies();
    const sessionCookie = cookies.find((c) => c.name === 'sempkm_session');

    if (sessionCookie) {
      const resp = await api.post(`${BASE_URL}/api/auth/invite`, {
        headers: { Cookie: `sempkm_session=${sessionCookie.value}` },
        data: { email: 'unauthorized@test.local', role: 'member' },
      });

      // Invite requires owner role — should be forbidden
      expect(resp.status()).toBeGreaterThanOrEqual(400);
    }
  });
});
