/**
 * Keyboard Shortcuts E2E Tests
 *
 * Tests workspace keyboard shortcuts: Ctrl+K for command palette,
 * Ctrl+N for type picker, Ctrl+, for settings.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Keyboard Shortcuts', () => {
  test('Ctrl+K opens command palette', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Press Ctrl+K to open command palette
    await ownerPage.keyboard.press('Control+k');

    // ninja-keys should become visible (it uses the open() method)
    await ownerPage.waitForTimeout(500);

    // Check if ninja-keys has opened state
    const isOpen = await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys') as any;
      return nk?.opened || nk?.getAttribute('opened') !== null || nk?.classList?.contains('visible');
    });

    // The command palette should be visible
    expect(isOpen).toBeTruthy();
  });

  test('Ctrl+N opens type picker via ninja-keys hotkey', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Ctrl+N is registered as a ninja-keys hotkey which calls showTypePicker()
    // showTypePicker() does htmx.ajax('GET', '/browser/types', ...) into editor area
    await ownerPage.keyboard.press('Control+n');
    await waitForIdle(ownerPage);

    // Type picker should appear in the editor area
    const picker = ownerPage.locator(SEL.typePicker.overlay);
    await expect(picker).toBeVisible({ timeout: 5000 });

    // Should show all four Basic PKM types
    const typeOptions = ownerPage.locator(SEL.typePicker.typeOption);
    const count = await typeOptions.count();
    expect(count).toBe(4);
  });

  test('Ctrl+, opens settings page', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Ctrl+, is handled directly in the keydown handler, calling openSettingsTab()
    await ownerPage.keyboard.press('Control+,');
    await waitForIdle(ownerPage);

    // Settings page should appear in the editor area
    const settingsPage = ownerPage.locator(SEL.settings.page);
    await expect(settingsPage).toBeVisible({ timeout: 10000 });

    // Should have category buttons
    const categoryBtns = ownerPage.locator('.settings-category-btn');
    const count = await categoryBtns.count();
    expect(count).toBeGreaterThan(0);
  });
});
