/**
 * VFS Settings UI E2E Tests
 *
 * Tests the Virtual Filesystem settings panel: navigating to the VFS category,
 * WebDAV endpoint display, API token generation, and token revocation.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Open settings and switch to VFS category */
async function openVfsSettings(page: import('@playwright/test').Page) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);

  await page.evaluate(() => {
    if (typeof (window as any).openSettingsTab === 'function') {
      (window as any).openSettingsTab();
    }
  });

  await page.waitForSelector(SEL.settings.page, { timeout: 10000 });

  // Click the Virtual Filesystem category button
  const vfsBtn = page.locator('.settings-category-btn[data-category="virtual-filesystem"]');
  await vfsBtn.click();
  await expect(vfsBtn).toHaveClass(/active/);
}

test.describe('VFS Settings UI', () => {

  test('Virtual Filesystem category is visible and selectable', async ({ ownerPage }) => {
    await openVfsSettings(ownerPage);

    // VFS panel should be visible
    const vfsPanel = ownerPage.locator('#category-virtual-filesystem');
    await expect(vfsPanel).toBeVisible();

    // Should show the category title
    await expect(vfsPanel.locator('.settings-category-title')).toHaveText('Virtual Filesystem');
  });

  test('WebDAV endpoint URL is displayed', async ({ ownerPage }) => {
    await openVfsSettings(ownerPage);

    // Endpoint URL should be visible
    const endpointUrl = ownerPage.locator('#vfs-endpoint-url');
    await expect(endpointUrl).toBeVisible();

    // Should contain /dav in the URL
    const urlText = await endpointUrl.textContent();
    expect(urlText).toContain('/dav');
  });

  test('token generation form exists with input and button', async ({ ownerPage }) => {
    await openVfsSettings(ownerPage);

    // Token name input should exist
    const tokenInput = ownerPage.locator('#vfs-token-name');
    await expect(tokenInput).toBeVisible();
    await expect(tokenInput).toHaveAttribute('placeholder', /MacBook/i);

    // Generate button should exist
    const generateBtn = ownerPage.locator('#vfs-token-form button[type="submit"]');
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toHaveText('Generate Token');
  });

  test('generating a token shows the token value', async ({ ownerPage }) => {
    await openVfsSettings(ownerPage);

    // Fill in token name and submit
    const tokenInput = ownerPage.locator('#vfs-token-name');
    await tokenInput.fill('e2e-test-token-' + Date.now());

    const generateBtn = ownerPage.locator('#vfs-token-form button[type="submit"]');
    await generateBtn.click();

    // Wait for the token reveal to appear
    const tokenReveal = ownerPage.locator('.vfs-token-reveal');
    await expect(tokenReveal).toBeVisible({ timeout: 10000 });

    // Should show the warning message
    await expect(tokenReveal).toContainText('Copy this token now');

    // Token value should be non-empty
    const tokenValue = ownerPage.locator('.vfs-token-value');
    const tokenText = await tokenValue.textContent();
    expect(tokenText).toBeTruthy();
    expect(tokenText!.length).toBeGreaterThan(10);

    // Token should appear in the active tokens table
    const tokensTable = ownerPage.locator('.vfs-tokens-table');
    await expect(tokensTable).toBeVisible();
  });

  test('revoking a token removes it from the table', async ({ ownerPage, ownerSessionToken }) => {
    // First create a token via API so we have one to revoke
    const api = ownerPage.context().request;
    const createResp = await api.post(`${BASE_URL}/api/auth/tokens`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: { name: 'e2e-revoke-test-' + Date.now() },
    });
    const tokenData = await createResp.json();
    const tokenId = tokenData.id;

    // Navigate to VFS settings
    await openVfsSettings(ownerPage);

    // The token row should exist
    const tokenRow = ownerPage.locator(`#vfs-token-row-${tokenId}`);
    await expect(tokenRow).toBeVisible();

    // Handle the confirm dialog
    ownerPage.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Click revoke
    const revokeBtn = tokenRow.locator('.btn-danger-sm');
    await revokeBtn.click();

    // Row should be removed
    await expect(tokenRow).not.toBeVisible({ timeout: 5000 });
  });

  test('active tokens section shows correct structure', async ({ ownerPage }) => {
    await openVfsSettings(ownerPage);

    // Active tokens section should exist
    const tokensSection = ownerPage.locator('.vfs-tokens-section');
    await expect(tokensSection).toBeVisible();

    // Should have the section label
    await expect(tokensSection.locator('.settings-label')).toHaveText('Active API Tokens');

    // Either a table with tokens or the empty state message should be visible
    const hasTable = await ownerPage.locator('.vfs-tokens-table:not([style*="display:none"])').isVisible();
    const hasEmptyMsg = await ownerPage.locator('.vfs-no-tokens').isVisible();
    expect(hasTable || hasEmptyMsg).toBeTruthy();
  });
});
