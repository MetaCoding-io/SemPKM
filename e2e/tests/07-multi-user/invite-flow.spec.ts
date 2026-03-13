/**
 * Auth Invite Flow E2E Tests
 *
 * Tests the owner invite flow: POST /api/auth/invite creates an invitation,
 * and the invited user can log in and gets the member role.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { request } from '@playwright/test';

test.describe('Invite Flow', () => {
  test('owner can invite a new user via API', async ({ ownerRequest }) => {
    const email = `invited-${Date.now()}@test.local`;

    const resp = await ownerRequest.post(`${BASE_URL}/api/auth/invite`, {
      data: { email, role: 'member' },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data).toBeDefined();
  });

  test('invited user can log in via magic link', async ({ ownerRequest }) => {
    const email = `invite-login-${Date.now()}@test.local`;

    // Owner invites the user
    const inviteResp = await ownerRequest.post(`${BASE_URL}/api/auth/invite`, {
      data: { email, role: 'member' },
    });
    expect(inviteResp.ok()).toBeTruthy();

    // Invited user requests a magic link
    const anonCtx = await request.newContext({ baseURL: BASE_URL });
    const mlResp = await anonCtx.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email },
    });
    expect(mlResp.ok()).toBeTruthy();
    const mlData = await mlResp.json();
    expect(mlData.token).toBeTruthy();

    // Verify the token to create a session
    const verifyResp = await anonCtx.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    expect(verifyResp.ok()).toBeTruthy();

    // Extract session cookie
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    expect(match).toBeTruthy();

    // Use the session to check the user's role
    const authedCtx = await request.newContext({
      baseURL: BASE_URL,
      extraHTTPHeaders: {
        Cookie: `sempkm_session=${match![1]}`,
      },
    });

    const meResp = await authedCtx.get(`${BASE_URL}/api/auth/me`);
    expect(meResp.ok()).toBeTruthy();
    const meData = await meResp.json();
    expect(meData.email).toBe(email);
    expect(meData.role).toBe('member');

    await anonCtx.dispose();
    await authedCtx.dispose();
  });

  test('member cannot invite other users (owner-only)', async ({ ownerRequest }) => {
    // First invite a member
    const memberEmail = `member-noinvite-${Date.now()}@test.local`;
    await ownerRequest.post(`${BASE_URL}/api/auth/invite`, {
      data: { email: memberEmail, role: 'member' },
    });

    // Login as member
    const anonCtx = await request.newContext({ baseURL: BASE_URL });
    const mlResp = await anonCtx.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: memberEmail },
    });
    const mlData = await mlResp.json();
    const verifyResp = await anonCtx.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    await anonCtx.dispose();

    const memberCtx = await request.newContext({
      baseURL: BASE_URL,
      extraHTTPHeaders: {
        Cookie: `sempkm_session=${match![1]}`,
      },
    });

    // Member tries to invite — should be forbidden
    const inviteResp = await memberCtx.post(`${BASE_URL}/api/auth/invite`, {
      data: { email: 'should-fail@test.local', role: 'member' },
    });
    expect(inviteResp.status()).toBeGreaterThanOrEqual(400);

    await memberCtx.dispose();
  });
});
