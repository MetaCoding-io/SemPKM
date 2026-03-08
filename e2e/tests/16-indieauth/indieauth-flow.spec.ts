/**
 * IndieAuth Provider E2E Tests
 *
 * Covers IAUTH-01 through IAUTH-05:
 * - Metadata endpoint returns valid server metadata
 * - Well-known redirect to metadata
 * - Profile page includes indieauth-metadata link
 * - Full authorization code flow with PKCE
 * - Token introspection
 * - Deny flow returns error
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { createHash, randomBytes } from 'crypto';

function generatePKCE() {
  const verifier = randomBytes(32).toString('base64url');
  const challenge = createHash('sha256').update(verifier).digest('base64url');
  return { verifier, challenge };
}

test.describe.serial('IndieAuth Provider', () => {

  test('metadata endpoint returns valid IndieAuth server metadata', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(`${BASE_URL}/api/indieauth/metadata`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.issuer).toBeTruthy();
    expect(data.authorization_endpoint).toContain('/api/indieauth/authorize');
    expect(data.token_endpoint).toContain('/api/indieauth/token');
    expect(data.introspection_endpoint).toContain('/api/indieauth/introspect');
    expect(data.code_challenge_methods_supported).toContain('S256');
    expect(data.scopes_supported).toContain('profile');
  });

  test('well-known redirect points to metadata', async ({ ownerRequest }) => {
    const resp = await ownerRequest.fetch(`${BASE_URL}/.well-known/oauth-authorization-server`, {
      maxRedirects: 0,
    });
    expect(resp.status()).toBe(307);
    const location = resp.headers()['location'];
    expect(location).toContain('/api/indieauth/metadata');
  });

  test('profile page includes indieauth-metadata link', async ({ ownerRequest }) => {
    // First ensure the owner has a published WebID profile
    // Check if username is already set
    const profileResp = await ownerRequest.get(`${BASE_URL}/api/webid/profile`);
    const profile = await profileResp.json();

    if (!profile.username) {
      // Set username
      await ownerRequest.post(`${BASE_URL}/api/webid/username`, {
        data: { username: 'e2eindieauth' },
      });
    }

    if (!profile.published) {
      await ownerRequest.post(`${BASE_URL}/api/webid/publish`);
    }

    // Re-fetch to get the username
    const updatedResp = await ownerRequest.get(`${BASE_URL}/api/webid/profile`);
    const updatedProfile = await updatedResp.json();
    const username = updatedProfile.username;

    // Fetch the HTML profile page
    const htmlResp = await ownerRequest.get(`${BASE_URL}/users/${username}`, {
      headers: { 'Accept': 'text/html' },
    });
    expect(htmlResp.status()).toBe(200);
    const html = await htmlResp.text();
    expect(html).toContain('rel="indieauth-metadata"');

    // Check Link header
    const linkHeader = htmlResp.headers()['link'];
    expect(linkHeader).toContain('indieauth-metadata');
  });

  let accessToken: string;
  let refreshToken: string;

  test('full authorization code flow with PKCE', async ({ ownerPage, ownerRequest }) => {
    const { verifier, challenge } = generatePKCE();

    // Get the owner's username for profile URL construction
    const profileResp = await ownerRequest.get(`${BASE_URL}/api/webid/profile`);
    const profile = await profileResp.json();

    // Navigate to authorization endpoint (consent screen)
    const authUrl = `${BASE_URL}/api/indieauth/authorize?` +
      `response_type=code&` +
      `client_id=${encodeURIComponent('https://example.com/')}&` +
      `redirect_uri=${encodeURIComponent('https://example.com/callback')}&` +
      `scope=profile&` +
      `code_challenge=${challenge}&` +
      `code_challenge_method=S256&` +
      `state=teststate123`;

    // Intercept redirect to example.com to capture the auth code
    let redirectUrl: string | null = null;
    await ownerPage.route('**/example.com/**', async (route) => {
      redirectUrl = route.request().url();
      // Respond with a simple page instead of following the redirect
      await route.fulfill({ status: 200, body: 'Redirect captured' });
    });

    await ownerPage.goto(authUrl);
    await ownerPage.waitForLoadState('networkidle');

    // Should see consent page with app info
    const pageContent = await ownerPage.content();
    expect(pageContent).toContain('example.com');

    // Click approve button
    const approveBtn = ownerPage.locator('button[value="approve"], input[value="approve"], [name="action"][value="approve"]');
    if (await approveBtn.count() > 0) {
      await approveBtn.first().click();
    } else {
      // Try submitting the form with action=approve
      await ownerPage.locator('form').first().evaluate((form: HTMLFormElement) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'action';
        input.value = 'approve';
        form.appendChild(input);
        form.submit();
      });
    }

    // Wait for the redirect to be captured
    await ownerPage.waitForTimeout(2000);

    expect(redirectUrl).toBeTruthy();
    const url = new URL(redirectUrl!);
    expect(url.searchParams.get('state')).toBe('teststate123');
    expect(url.searchParams.get('code')).toBeTruthy();
    expect(url.searchParams.get('iss')).toBeTruthy();

    const code = url.searchParams.get('code')!;

    // Exchange code for token
    const tokenResp = await ownerRequest.post(`${BASE_URL}/api/indieauth/token`, {
      form: {
        grant_type: 'authorization_code',
        code: code,
        client_id: 'https://example.com/',
        redirect_uri: 'https://example.com/callback',
        code_verifier: verifier,
      },
    });
    expect(tokenResp.status()).toBe(200);
    const tokenData = await tokenResp.json();
    expect(tokenData.access_token).toBeTruthy();
    expect(tokenData.token_type).toBe('Bearer');
    expect(tokenData.scope).toContain('profile');
    expect(tokenData.me).toBeTruthy();

    accessToken = tokenData.access_token;
    refreshToken = tokenData.refresh_token;
  });

  test('token introspection', async ({ ownerRequest }) => {
    // Introspect valid token
    const resp = await ownerRequest.post(`${BASE_URL}/api/indieauth/introspect`, {
      form: { token: accessToken },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.active).toBe(true);
    expect(data.me).toBeTruthy();
    expect(data.client_id).toBe('https://example.com/');
    expect(data.scope).toContain('profile');

    // Introspect invalid token
    const invalidResp = await ownerRequest.post(`${BASE_URL}/api/indieauth/introspect`, {
      form: { token: 'invalid-token-value' },
    });
    expect(invalidResp.status()).toBe(200);
    const invalidData = await invalidResp.json();
    expect(invalidData.active).toBe(false);
  });

  test('deny returns error to client', async ({ ownerPage, ownerRequest }) => {
    const { verifier, challenge } = generatePKCE();

    const authUrl = `${BASE_URL}/api/indieauth/authorize?` +
      `response_type=code&` +
      `client_id=${encodeURIComponent('https://example.com/')}&` +
      `redirect_uri=${encodeURIComponent('https://example.com/callback')}&` +
      `scope=profile&` +
      `code_challenge=${challenge}&` +
      `code_challenge_method=S256&` +
      `state=denytest`;

    let redirectUrl: string | null = null;
    await ownerPage.route('**/example.com/**', async (route) => {
      redirectUrl = route.request().url();
      await route.fulfill({ status: 200, body: 'Redirect captured' });
    });

    await ownerPage.goto(authUrl);
    await ownerPage.waitForLoadState('networkidle');

    // Click deny button
    const denyBtn = ownerPage.locator('button[value="deny"], input[value="deny"], [name="action"][value="deny"]');
    if (await denyBtn.count() > 0) {
      await denyBtn.first().click();
    } else {
      await ownerPage.locator('form').first().evaluate((form: HTMLFormElement) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'action';
        input.value = 'deny';
        form.appendChild(input);
        form.submit();
      });
    }

    await ownerPage.waitForTimeout(2000);

    expect(redirectUrl).toBeTruthy();
    const url = new URL(redirectUrl!);
    expect(url.searchParams.get('error')).toBe('access_denied');
    expect(url.searchParams.get('state')).toBe('denytest');
  });

});
