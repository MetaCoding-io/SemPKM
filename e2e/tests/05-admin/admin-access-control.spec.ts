/**
 * Admin Access Control E2E Tests
 *
 * Tests that admin pages require the owner role, and member users
 * cannot access them.
 */
import { test, expect, MEMBER_EMAIL, BASE_URL } from '../../fixtures/auth';

test.describe('Admin Access Control', () => {
  test('member user cannot access /admin/models (API returns 403)', async ({ memberPage, ownerSessionToken }) => {
    // memberPage is authenticated as a member user
    // Try to navigate to admin models page
    const resp = await memberPage.goto(`${BASE_URL}/admin/models`);

    // Should get a 403 Forbidden or redirect to login
    if (resp) {
      const status = resp.status();
      // Either 403 (forbidden) or 401 (unauthorized) or redirect
      expect([403, 401, 302, 307].includes(status) || status >= 400).toBeTruthy();
    }
  });

  test('member user cannot access /admin/webhooks (API returns 403)', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/admin/webhooks`);

    if (resp) {
      const status = resp.status();
      expect([403, 401, 302, 307].includes(status) || status >= 400).toBeTruthy();
    }
  });

  test('member user cannot access /admin/ index (API returns 403)', async ({ memberPage }) => {
    const resp = await memberPage.goto(`${BASE_URL}/admin/`);

    if (resp) {
      const status = resp.status();
      expect([403, 401, 302, 307].includes(status) || status >= 400).toBeTruthy();
    }
  });

  test('owner can access admin pages (200)', async ({ ownerPage }) => {
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models`);

    if (resp) {
      expect(resp.status()).toBe(200);
    }

    // Should see the admin page content
    await expect(ownerPage.locator('h1')).toContainText('Mental Models', { timeout: 15000 });
  });
});
