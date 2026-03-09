/**
 * Fuzzy FTS Toggle E2E Tests
 *
 * Tests the fuzzy search toggle command in the command palette,
 * localStorage persistence, and that fuzzy=true is sent in search requests.
 *
 * Uses the auth fixture (ownerPage) for authenticated access.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Fuzzy FTS Toggle', () => {
  test('fuzzy toggle command exists in palette', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    const hasToggle = await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      if (!ninja || !ninja.data) return false;
      return ninja.data.some(
        (d: any) => d.id === 'search-fuzzy-toggle' && d.section === 'Search',
      );
    });
    expect(hasToggle).toBe(true);
  });

  test('toggling fuzzy updates localStorage', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clear any existing state
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_fts_fuzzy'));

    // Toggle fuzzy ON via the command handler
    await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      const toggle = ninja.data.find((d: any) => d.id === 'search-fuzzy-toggle');
      if (toggle && toggle.handler) toggle.handler();
    });
    await ownerPage.waitForTimeout(300);

    const afterOn = await ownerPage.evaluate(() => localStorage.getItem('sempkm_fts_fuzzy'));
    expect(afterOn).toBe('true');

    // Toggle fuzzy OFF
    await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      const toggle = ninja.data.find((d: any) => d.id === 'search-fuzzy-toggle');
      if (toggle && toggle.handler) toggle.handler();
    });
    await ownerPage.waitForTimeout(300);

    const afterOff = await ownerPage.evaluate(() => localStorage.getItem('sempkm_fts_fuzzy'));
    // When toggled off, value should be 'false' or removed
    expect(afterOff === 'false' || afterOff === null).toBe(true);

    // Clean up
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_fts_fuzzy'));
  });

  test('fuzzy search sends fuzzy=true parameter', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Enable fuzzy mode
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_fts_fuzzy'));
    await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      const toggle = ninja.data.find((d: any) => d.id === 'search-fuzzy-toggle');
      if (toggle && toggle.handler) toggle.handler();
    });
    await ownerPage.waitForTimeout(300);

    // Set up route interception to capture search URL
    let capturedUrl = '';
    await ownerPage.route('**/api/search*', async (route) => {
      capturedUrl = route.request().url();
      await route.continue();
    });

    // Open palette and type a search query
    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);
    await ownerPage.keyboard.type('note', { delay: 50 });

    // Wait for debounce + fetch
    await ownerPage.waitForTimeout(1000);

    expect(capturedUrl).toContain('fuzzy=true');

    // Clean up
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_fts_fuzzy'));
  });

  test('fuzzy search finds results with typos', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Enable fuzzy mode
    await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      const toggle = ninja.data.find((d: any) => d.id === 'search-fuzzy-toggle');
      if (toggle && toggle.handler) toggle.handler();
    });
    await ownerPage.waitForTimeout(300);

    // Open palette and type a misspelled query
    // 'knowlege' is missing the 'd' from 'knowledge'
    // Seed data has 'Knowledge Management' concept
    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);
    await ownerPage.keyboard.type('knowlege', { delay: 50 });

    // Wait for debounce + fetch + render
    await ownerPage.waitForTimeout(1200);

    // Check if any FTS results appear with Search section
    const hasFtsResults = await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      if (!ninja || !ninja.data) return false;
      return ninja.data.some((d: any) => d.id.startsWith('fts-') && d.section === 'Search');
    });
    expect(hasFtsResults).toBe(true);

    // Clean up
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_fts_fuzzy'));
  });
});
