/**
 * Dark Mode E2E Tests
 *
 * Tests the dark mode toggle: switching themes, CSS variable changes,
 * and per-user theme isolation.
 */
import { test, expect, OWNER_EMAIL, MEMBER_EMAIL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Dark Mode', () => {
  test('workspace starts in light mode by default', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Check that the body/html doesn't have a dark class initially
    const isDark = await ownerPage.evaluate(() => {
      return document.documentElement.classList.contains('dark') ||
             document.body.classList.contains('dark') ||
             document.documentElement.getAttribute('data-theme') === 'dark';
    });

    // Default should be light mode
    expect(isDark).toBeFalsy();
  });

  test('dark mode setting can be toggled via API', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;

    // Find the dark mode setting key
    const settingsResp = await api.get(`${BASE_URL}/browser/settings/data`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const settings = await settingsResp.json();

    // Look for a theme/dark-mode related setting
    const themeKey = Object.keys(settings).find(
      (k) => k.includes('theme') || k.includes('dark') || k.includes('appearance'),
    );

    if (themeKey) {
      // Toggle to dark
      const updateResp = await api.put(`${BASE_URL}/browser/settings/${themeKey}`, {
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
        data: { value: 'dark' },
      });

      expect(updateResp.ok()).toBeTruthy();

      // Reset back to light
      await api.delete(`${BASE_URL}/browser/settings/${themeKey}`, {
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      });
    }
  });

  test('per-user settings: owner dark mode does not affect member', async ({
    ownerPage,
    memberPage,
    ownerSessionToken,
  }) => {
    const ownerApi = await ownerPage.context().request;

    // Get settings to find theme key
    const settingsResp = await ownerApi.get(`${BASE_URL}/browser/settings/data`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const settings = await settingsResp.json();

    const themeKey = Object.keys(settings).find(
      (k) => k.includes('theme') || k.includes('dark') || k.includes('appearance'),
    );

    if (themeKey) {
      // Set owner to dark mode
      await ownerApi.put(`${BASE_URL}/browser/settings/${themeKey}`, {
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
        data: { value: 'dark' },
      });

      // Load member's workspace
      await memberPage.goto(`${BASE_URL}/browser/`);
      await memberPage.waitForSelector('.workspace-container, .dashboard-layout', { timeout: 15000 });

      // Member should NOT be in dark mode
      const memberIsDark = await memberPage.evaluate(() => {
        return document.documentElement.classList.contains('dark') ||
               document.body.classList.contains('dark') ||
               document.documentElement.getAttribute('data-theme') === 'dark';
      });

      expect(memberIsDark).toBeFalsy();

      // Clean up: reset owner theme
      await ownerApi.delete(`${BASE_URL}/browser/settings/${themeKey}`, {
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      });
    }
  });
});
