/**
 * Setup Wizard E2E Tests
 *
 * Tests the first-run setup flow: fresh instance → setup wizard → instance claimed.
 * These tests MUST run first (before any auth fixture completes setup).
 *
 * The test order is:
 * 1. Fresh instance shows setup mode
 * 2. Setup wizard page loads correctly
 * 3. Submit setup token → instance claimed → redirected
 * 4. After setup, /api/auth/status reports setup_complete
 */
import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Read the setup token from the Docker API container */
function readSetupToken(): string {
  const root = execSync('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();
  try {
    return execSync(
      'docker compose -f docker-compose.test.yml exec -T api cat /app/data/.setup-token',
      { cwd: root, encoding: 'utf-8', timeout: 10000 },
    ).trim();
  } catch {
    const logs = execSync(
      'docker compose -f docker-compose.test.yml logs api 2>&1',
      { cwd: root, encoding: 'utf-8', timeout: 10000 },
    );
    const match = logs.match(/Setup token:\s+(\S+)/);
    if (!match) throw new Error('Could not extract setup token from container');
    return match[1];
  }
}

test.describe('Setup Wizard', () => {
  test('fresh instance reports setup_mode=true', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/auth/status`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data.setup_mode).toBe(true);
    expect(data.setup_complete).toBe(false);
  });

  test('navigating to root redirects to setup page', async ({ page }) => {
    // On a fresh instance, visiting / should eventually redirect to /setup.html
    // because the auth.js checkAuthStatus() detects setup_mode and redirects
    await page.goto(BASE_URL);
    await page.waitForURL('**/setup.html', { timeout: 10000 });
    expect(page.url()).toContain('/setup.html');
  });

  test('setup page shows the setup form', async ({ page }) => {
    await page.goto(`${BASE_URL}/setup.html`);

    // Check that the setup form elements are present
    await expect(page.locator('#setupForm')).toBeVisible();
    await expect(page.locator('#setup-token')).toBeVisible();
    await expect(page.locator('#setup-email')).toBeVisible();
    await expect(page.locator('#setupForm button[type="submit"]')).toBeVisible();

    // Verify the page title
    await expect(page.locator('h1')).toContainText('Welcome to SemPKM');
  });

  test('submitting invalid token shows error', async ({ page }) => {
    await page.goto(`${BASE_URL}/setup.html`);

    await page.fill('#setup-token', 'invalid-token-12345');
    await page.click('#setupForm button[type="submit"]');

    // Wait for error message to appear
    await expect(page.locator('#setup-message')).toContainText('Invalid setup token', { timeout: 5000 });
  });

  test('submitting valid token completes setup and redirects', async ({ page }) => {
    const token = readSetupToken();

    await page.goto(`${BASE_URL}/setup.html`);

    await page.fill('#setup-token', token);
    await page.fill('#setup-email', 'owner@test.local');
    await page.click('#setupForm button[type="submit"]');

    // Wait for success message
    await expect(page.locator('#setup-message')).toContainText('Instance claimed successfully', { timeout: 10000 });

    // The page redirects to / (dashboard) after ~2 seconds
    await page.waitForURL(url => !url.toString().includes('setup.html'), { timeout: 10000 });
  });

  test('after setup, auth status reports setup_complete=true', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/auth/status`);
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data.setup_complete).toBe(true);
    expect(data.setup_mode).toBe(false);
  });

  test('second setup attempt returns error', async ({ request }) => {
    // Try to set up again — should fail since instance is already claimed
    const resp = await request.post(`${BASE_URL}/api/auth/setup`, {
      data: { token: 'any-token', email: 'hacker@evil.com' },
    });
    expect(resp.status()).toBe(400);

    const data = await resp.json();
    expect(data.detail).toContain('Setup already completed');
  });
});
