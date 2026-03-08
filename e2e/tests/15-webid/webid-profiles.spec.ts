/**
 * WebID Profile E2E Tests
 *
 * Covers WBID-01 through WBID-06:
 * - WBID-01: Username claim and key generation
 * - WBID-02: Profile published at /users/{username} (HTML), 404 when unpublished
 * - WBID-03: Content negotiation (Turtle + JSON-LD)
 * - WBID-04: rel="me" links in HTML head
 * - WBID-05: Ed25519 key pair generation
 * - WBID-06: Public key included in RDF
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

const TEST_USERNAME = 'e2ewebid';

test.describe.serial('WebID Profiles', () => {

  test('Username claim and key generation (WBID-01, WBID-05)', async ({ ownerPage }) => {
    // Navigate to Settings
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');

    // Click WebID Profile category
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);

    // Check if username is already set (from a previous test run)
    const profileSection = ownerPage.locator('#webid-profile');
    const setupSection = ownerPage.locator('#webid-setup');

    const profileVisible = await profileSection.isVisible();
    if (profileVisible) {
      // Username already claimed in a previous run -- verify display
      const usernameDisplay = ownerPage.locator('#webid-username-display');
      await expect(usernameDisplay).toBeVisible();
      const username = await usernameDisplay.textContent();
      expect(username).toBeTruthy();

      // Verify WebID URI is shown
      const uriDisplay = ownerPage.locator('#webid-uri-display');
      await expect(uriDisplay).toBeVisible();
      const uri = await uriDisplay.textContent();
      expect(uri).toContain('/users/');
      expect(uri).toContain('#me');

      // Verify fingerprint is displayed
      const fingerprint = ownerPage.locator('#webid-fingerprint');
      await expect(fingerprint).toBeVisible();
      const fpText = await fingerprint.textContent();
      expect(fpText).toMatch(/[0-9a-f]{2}(:[0-9a-f]{2})+/);
      return;
    }

    // Setup section should be visible -- claim a username
    await expect(setupSection).toBeVisible();

    const usernameInput = ownerPage.locator('#webid-username-input');
    await usernameInput.fill(TEST_USERNAME);
    await ownerPage.click('button:has-text("Claim Username")');

    // Wait for profile to appear
    await expect(profileSection).toBeVisible({ timeout: 10000 });

    // Verify username is displayed as read-only
    const usernameDisplay = ownerPage.locator('#webid-username-display');
    await expect(usernameDisplay).toBeVisible();
    const displayedUsername = await usernameDisplay.textContent();
    expect(displayedUsername).toBeTruthy();

    // Verify WebID URI is shown
    const uriDisplay = ownerPage.locator('#webid-uri-display');
    await expect(uriDisplay).toBeVisible();
    const uri = await uriDisplay.textContent();
    expect(uri).toContain('/users/');
    expect(uri).toContain('#me');

    // Verify key fingerprint is displayed (colon-separated hex)
    const fingerprint = ownerPage.locator('#webid-fingerprint');
    await expect(fingerprint).toBeVisible();
    const fpText = await fingerprint.textContent();
    expect(fpText).toMatch(/[0-9a-f]{2}(:[0-9a-f]{2})+/);
  });

  test('Publish profile and verify HTML response (WBID-02)', async ({ ownerPage }) => {
    // Go to Settings > WebID Profile
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);

    // Wait for profile section to load
    await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });

    // Get the username
    const username = await ownerPage.locator('#webid-username-display').textContent();

    // Ensure published toggle is checked
    const toggle = ownerPage.locator('#webid-published-toggle');
    const isChecked = await toggle.isChecked();
    if (!isChecked) {
      await toggle.check();
      await ownerPage.waitForTimeout(1000);
    }

    // Navigate to the public profile page
    await ownerPage.goto(`${BASE_URL}/users/${username}`);
    await ownerPage.waitForLoadState('networkidle');

    // Verify: page shows SemPKM branding
    await expect(ownerPage.locator('.brand-name')).toContainText('SemPKM');

    // Verify: page contains WebID URI text
    await expect(ownerPage.locator('#webid-uri')).toBeVisible();
    const webidUri = await ownerPage.locator('#webid-uri').textContent();
    expect(webidUri).toContain(`/users/${username}#me`);
  });

  test('Add rel="me" links and verify on public profile (WBID-04)', async ({ ownerPage }) => {
    // Go to Settings > WebID Profile
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);
    await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });

    const username = await ownerPage.locator('#webid-username-display').textContent();

    // Click Add Link
    await ownerPage.click('button:has-text("Add Link")');
    await ownerPage.waitForTimeout(500);

    // Fill in the link URL
    const linkInput = ownerPage.locator('.webid-link-input').last();
    await linkInput.fill('https://mastodon.social/@testuser');

    // Click Save Links
    await ownerPage.click('#webid-save-links-btn');
    await ownerPage.waitForTimeout(1000);

    // Navigate to public profile
    await ownerPage.goto(`${BASE_URL}/users/${username}`);
    await ownerPage.waitForLoadState('networkidle');

    // Verify: the link appears on the profile page
    const linkEl = ownerPage.locator('a[href="https://mastodon.social/@testuser"]');
    await expect(linkEl).toBeVisible();

    // Verify: HTML source contains rel="me" link tag in head
    const content = await ownerPage.content();
    expect(content).toContain('<link rel="me" href="https://mastodon.social/@testuser">');
  });

  test('Content negotiation - Turtle (WBID-02, WBID-03, WBID-06)', async ({ ownerPage }) => {
    // Get the username from settings
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);
    await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });

    const username = await ownerPage.locator('#webid-username-display').textContent();

    // Use API request context with Accept: text/turtle
    const response = await ownerPage.request.get(`${BASE_URL}/users/${username}`, {
      headers: { 'Accept': 'text/turtle' },
    });

    expect(response.status()).toBe(200);
    const contentType = response.headers()['content-type'] || '';
    expect(contentType).toContain('text/turtle');

    const body = await response.text();
    expect(body).toContain('PersonalProfileDocument');
    expect(body).toContain('primaryTopic');
    expect(body).toContain('Ed25519');
  });

  test('Content negotiation - JSON-LD (WBID-03)', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);
    await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });

    const username = await ownerPage.locator('#webid-username-display').textContent();

    const response = await ownerPage.request.get(`${BASE_URL}/users/${username}`, {
      headers: { 'Accept': 'application/ld+json' },
    });

    expect(response.status()).toBe(200);
    const contentType = response.headers()['content-type'] || '';
    expect(contentType).toContain('application/ld+json');

    const json = await response.json();
    expect(json).toHaveProperty('@context');
  });

  test('Unpublished profile returns 404 (WBID-02)', async ({ ownerPage }) => {
    // Go to settings, unpublish
    await ownerPage.goto(`${BASE_URL}/browser/settings`);
    await ownerPage.waitForLoadState('networkidle');
    await ownerPage.click('button[data-category="webid-profile"]');
    await ownerPage.waitForTimeout(1000);
    await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });

    const username = await ownerPage.locator('#webid-username-display').textContent();

    // Unpublish
    const toggle = ownerPage.locator('#webid-published-toggle');
    const isChecked = await toggle.isChecked();
    if (isChecked) {
      await toggle.uncheck();
      await ownerPage.waitForTimeout(1000);
    }

    // Request profile -- should be 404
    const response = await ownerPage.request.get(`${BASE_URL}/users/${username}`);
    expect(response.status()).toBe(404);

    // Re-publish for any subsequent tests
    if (isChecked) {
      await ownerPage.goto(`${BASE_URL}/browser/settings`);
      await ownerPage.waitForLoadState('networkidle');
      await ownerPage.click('button[data-category="webid-profile"]');
      await ownerPage.waitForTimeout(1000);
      await expect(ownerPage.locator('#webid-profile')).toBeVisible({ timeout: 10000 });
      await ownerPage.locator('#webid-published-toggle').check();
      await ownerPage.waitForTimeout(1000);
    }
  });

  test('Nonexistent username returns 404', async ({ ownerPage }) => {
    const response = await ownerPage.request.get(`${BASE_URL}/users/nonexistentuser12345`);
    expect(response.status()).toBe(404);
  });

});
