/**
 * FTS Keyword Search E2E Tests
 *
 * Tests the GET /api/search endpoint and the Alt+K command palette
 * FTS integration. Requires a running stack with indexed seed data.
 *
 * Uses the auth fixture (ownerPage) for authenticated access.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('FTS Keyword Search', () => {
  test('/api/search endpoint returns valid JSON structure', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Use page.evaluate to fetch with session credentials
    const result = await ownerPage.evaluate(async () => {
      const resp = await fetch('/api/search?q=note', { credentials: 'same-origin' });
      if (!resp.ok) return { error: resp.status };
      return resp.json();
    });
    expect(result).toHaveProperty('results');
    expect(result).toHaveProperty('query', 'note');
    expect(result).toHaveProperty('count');
    expect(Array.isArray(result.results)).toBe(true);
  });

  test('/api/search rejects query shorter than 2 characters', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const result = await ownerPage.evaluate(async () => {
      const resp = await fetch('/api/search?q=n', { credentials: 'same-origin' });
      return { status: resp.status };
    });
    expect(result.status).toBe(422);
  });

  test('Alt+K opens command palette', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    const isOpen = await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys') as any;
      return nk?.opened || nk?.getAttribute('opened') !== null || nk?.classList?.contains('visible');
    });
    expect(isOpen).toBeTruthy();
  });

  test('typing 2+ characters in palette triggers FTS fetch', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Intercept the FTS fetch to verify it fires
    let ftsRequestFired = false;
    await ownerPage.route('**/api/search*', async (route) => {
      ftsRequestFired = true;
      await route.continue();
    });

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    // Type a query into ninja-keys (it captures keyboard input in its shadow DOM input)
    await ownerPage.keyboard.type('note', { delay: 50 });

    // Wait for debounce (300ms) + fetch
    await ownerPage.waitForTimeout(800);

    expect(ftsRequestFired).toBe(true);
  });

  test('query shorter than 2 characters does not trigger FTS', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Intercept the FTS fetch to verify it does NOT fire
    let ftsRequestFired = false;
    await ownerPage.route('**/api/search*', async (route) => {
      ftsRequestFired = true;
      await route.continue();
    });

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    // Type a single character
    await ownerPage.keyboard.type('n');
    await ownerPage.waitForTimeout(500);

    expect(ftsRequestFired).toBe(false);
  });

  test('search results appear in palette with Search section', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    await ownerPage.keyboard.type('note', { delay: 50 });

    // Wait for debounce (300ms) + fetch + render
    await ownerPage.waitForTimeout(1200);

    // Verify FTS results were injected into ninja.data with section='Search'
    const hasFtsResults = await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      if (!ninja || !ninja.data) return false;
      return ninja.data.some((d: any) => d.id.startsWith('fts-') && d.section === 'Search');
    });
    expect(hasFtsResults).toBe(true);
  });

  test('palette closes with Escape', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    // Verify it opened
    const isOpen = await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys') as any;
      return nk?.opened || nk?.getAttribute('opened') !== null;
    });
    expect(isOpen).toBeTruthy();

    await ownerPage.keyboard.press('Escape');
    await ownerPage.waitForTimeout(500);

    const isClosed = await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys') as any;
      return !nk?.opened && nk?.getAttribute('opened') === null;
    });
    expect(isClosed).toBeTruthy();
  });
});
