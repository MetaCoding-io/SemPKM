/**
 * Session Management E2E Tests
 *
 * Tests session handling: expired sessions, multiple simultaneous
 * sessions, and logout behavior.
 */
import { test, expect, BASE_URL, OWNER_EMAIL } from '../../fixtures/auth';

test.describe('Session Management', () => {
  test('expired/invalid session returns 401 on /api/auth/me', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: 'sempkm_session=totally-bogus-token-12345' },
    });

    expect(resp.status()).toBe(401);
  });

  test('no session cookie returns 401 on /api/auth/me', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/auth/me`);
    expect(resp.status()).toBe(401);
  });

  test('logout invalidates the session', async ({ request }) => {
    // Login to get a session
    const mlResp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const mlData = await mlResp.json();

    const verifyResp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    expect(match).toBeTruthy();
    const sessionToken = match![1];

    // Verify session works
    const meResp = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${sessionToken}` },
    });
    expect(meResp.ok()).toBeTruthy();

    // Logout
    const logoutResp = await request.post(`${BASE_URL}/api/auth/logout`, {
      headers: { Cookie: `sempkm_session=${sessionToken}` },
    });
    expect(logoutResp.ok()).toBeTruthy();

    // Session should now be invalid
    const meAfterLogout = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${sessionToken}` },
    });
    expect(meAfterLogout.status()).toBe(401);
  });

  test('multiple login sessions can coexist', async ({ request }) => {
    // Create first session
    const ml1 = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const ml1Data = await ml1.json();
    const verify1 = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: ml1Data.token },
    });
    const cookie1 = (verify1.headers()['set-cookie'] || '').match(/sempkm_session=([^;]+)/);

    // Create second session
    const ml2 = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const ml2Data = await ml2.json();
    const verify2 = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: ml2Data.token },
    });
    const cookie2 = (verify2.headers()['set-cookie'] || '').match(/sempkm_session=([^;]+)/);

    expect(cookie1).toBeTruthy();
    expect(cookie2).toBeTruthy();

    // Both sessions should be valid
    const me1 = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${cookie1![1]}` },
    });
    expect(me1.ok()).toBeTruthy();

    const me2 = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${cookie2![1]}` },
    });
    expect(me2.ok()).toBeTruthy();

    // Tokens should be different
    expect(cookie1![1]).not.toBe(cookie2![1]);
  });

  test('unauthenticated command API returns 401', async ({ request }) => {
    const resp = await request.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: { 'http://purl.org/dc/terms/title': 'Unauthorized Note' },
        },
      },
    });

    // Should be rejected without auth
    expect(resp.status()).toBeGreaterThanOrEqual(400);
  });
});
