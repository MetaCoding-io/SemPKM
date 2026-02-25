/**
 * Magic Link Login E2E Tests
 *
 * Tests the passwordless authentication flow after setup is complete.
 * These tests run AFTER setup-wizard.spec.ts (which claims the instance).
 *
 * Since SMTP is not configured, magic link tokens are returned directly
 * in the API response, enabling fully automated login testing.
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const OWNER_EMAIL = 'owner@test.local';

test.describe('Magic Link Authentication', () => {
  test('request magic link returns token directly (no SMTP)', async ({ request }) => {
    const resp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    // Without SMTP configured, the token should be returned directly
    expect(data.token).toBeTruthy();
    expect(typeof data.token).toBe('string');
    expect(data.token.length).toBeGreaterThan(10);
  });

  test('verify valid token creates session', async ({ request }) => {
    // Get a magic link token
    const mlResp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const mlData = await mlResp.json();

    // Verify the token
    const verifyResp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    expect(verifyResp.ok()).toBeTruthy();

    const verifyData = await verifyResp.json();
    expect(verifyData.email).toBe(OWNER_EMAIL);
    expect(verifyData.role).toBe('owner');

    // Session cookie should be set
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    expect(setCookie).toContain('sempkm_session');
  });

  test('verify invalid token returns 400', async ({ request }) => {
    const resp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: 'bogus-invalid-token' },
    });
    expect(resp.status()).toBe(400);

    const data = await resp.json();
    expect(data.detail).toContain('Invalid or expired');
  });

  test('/api/auth/me works with valid session', async ({ request }) => {
    // Login to get a session
    const mlResp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const mlData = await mlResp.json();

    const verifyResp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });

    // Extract session cookie
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    expect(match).toBeTruthy();

    // Use session to call /me
    const meResp = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${match![1]}` },
    });
    expect(meResp.ok()).toBeTruthy();

    const meData = await meResp.json();
    expect(meData.email).toBe(OWNER_EMAIL);
    expect(meData.role).toBe('owner');
  });

  test('login flow via UI: email → auto-verify → redirect to workspace', async ({ page }) => {
    await page.goto(`${BASE_URL}/login.html`);

    // Verify login page elements
    await expect(page.locator('#loginForm')).toBeVisible();
    await expect(page.locator('#login-email')).toBeVisible();

    // Fill email and submit
    await page.fill('#login-email', OWNER_EMAIL);
    await page.click('#loginForm button[type="submit"]');

    // Without SMTP, the UI auto-verifies the token and redirects
    // Wait for either success message or redirect to workspace
    await expect(page.locator('#login-message')).toContainText(
      /Login successful|Logging in/,
      { timeout: 10000 },
    );

    // Should redirect to workspace (or root)
    await page.waitForURL(url => !url.toString().includes('login.html'), { timeout: 15000 });
  });

  test('logout clears session and redirects to login', async ({ page, request }) => {
    // First log in via API to set the cookie
    const mlResp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const mlData = await mlResp.json();

    const verifyResp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);

    // Navigate to workspace with session cookie
    await page.context().addCookies([{
      name: 'sempkm_session',
      value: match![1],
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto(`${BASE_URL}/browser/`);
    await page.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Call logout via API
    const logoutResp = await request.post(`${BASE_URL}/api/auth/logout`, {
      headers: { Cookie: `sempkm_session=${match![1]}` },
    });
    expect(logoutResp.ok()).toBeTruthy();

    // Verify the old session is now invalid
    const meResp = await request.get(`${BASE_URL}/api/auth/me`, {
      headers: { Cookie: `sempkm_session=${match![1]}` },
    });
    expect(meResp.status()).toBe(401);
  });

  test('new user gets "member" role via magic link', async ({ request }) => {
    const newEmail = 'newuser@test.local';

    // Request magic link for a brand new user
    const mlResp = await request.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: newEmail },
    });
    const mlData = await mlResp.json();
    expect(mlData.token).toBeTruthy();

    // Verify — should auto-create user with member role
    const verifyResp = await request.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    expect(verifyResp.ok()).toBeTruthy();

    const verifyData = await verifyResp.json();
    expect(verifyData.email).toBe(newEmail);
    expect(verifyData.role).toBe('member');
  });
});
