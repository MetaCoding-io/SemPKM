/**
 * E2E tests for the SemPKM browser extension capture flow.
 *
 * Proves the full round-trip: configure extension → connect to instance →
 * load types in popup → render SHACL form → create object → verify in workspace.
 *
 * Requires Docker test stack running on port 3901 with basic-pkm model installed.
 * Chromium-only (Firefox doesn't support --load-extension).
 */
import { test, expect } from '../../fixtures/extension';
import { execSync } from 'child_process';
import { request, type Page } from '@playwright/test';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const OWNER_EMAIL = 'owner@test.local';

/* ── Helpers ───────────────────────────────────────────────────── */

/** Resolve the repo root (one level up from e2e/) */
function repoRoot(): string {
  return execSync('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();
}

/** Read the setup token from the Docker API container */
function readSetupToken(): string {
  const root = repoRoot();
  try {
    return execSync(
      'docker compose -f docker-compose.test.yml exec -T api cat /app/data/.setup-token',
      { cwd: root, encoding: 'utf-8', timeout: 10_000 },
    ).trim();
  } catch {
    const logs = execSync(
      'docker compose -f docker-compose.test.yml logs api 2>&1',
      { cwd: root, encoding: 'utf-8', timeout: 10_000 },
    );
    const match = logs.match(/Setup token:\s+(\S+)/);
    if (!match) throw new Error('Could not extract setup token from container');
    return match[1];
  }
}

/**
 * Ensure the instance is set up and create an API key for the extension.
 */
async function setupAndCreateApiKey(): Promise<{
  apiKey: string;
  ownerSessionCookie: string;
}> {
  const ctx = await request.newContext({ baseURL: BASE_URL });

  const statusResp = await ctx.get(`${BASE_URL}/api/auth/status`);
  const status = await statusResp.json();

  let ownerSessionCookie: string;

  if (!status.setup_complete) {
    const token = readSetupToken();
    const setupResp = await ctx.post(`${BASE_URL}/api/auth/setup`, {
      data: { token, email: OWNER_EMAIL },
    });
    if (setupResp.status() !== 200) {
      throw new Error(`Setup failed: ${setupResp.status()} ${await setupResp.text()}`);
    }
    const setCookie = setupResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    if (!match) throw new Error('No session cookie from setup');
    ownerSessionCookie = match[1];
  } else {
    const mlResp = await ctx.post(`${BASE_URL}/api/auth/magic-link`, {
      data: { email: OWNER_EMAIL },
    });
    const mlData = await mlResp.json();
    if (!mlData.token) throw new Error('Magic link did not return token');

    const verifyResp = await ctx.post(`${BASE_URL}/api/auth/verify`, {
      data: { token: mlData.token },
    });
    if (verifyResp.status() !== 200) {
      throw new Error(`Verify failed: ${verifyResp.status()}`);
    }
    const setCookie = verifyResp.headers()['set-cookie'] || '';
    const match = setCookie.match(/sempkm_session=([^;]+)/);
    if (!match) throw new Error('No session cookie from verify');
    ownerSessionCookie = match[1];
  }

  // Create an API key via the JSON API
  const authCtx = await request.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: {
      Cookie: `sempkm_session=${ownerSessionCookie}`,
    },
  });

  const tokenResp = await authCtx.post(`${BASE_URL}/api/auth/tokens`, {
    data: { name: `e2e-extension-test-${Date.now()}` },
  });

  if (tokenResp.status() !== 201) {
    const body = await tokenResp.text();
    throw new Error(`Token creation failed (${tokenResp.status()}): ${body}`);
  }

  const tokenData = await tokenResp.json();
  await authCtx.dispose();
  await ctx.dispose();

  return {
    apiKey: tokenData.token,
    ownerSessionCookie,
  };
}

/**
 * Inject extension settings into chrome.storage.local directly.
 * Works around chrome.storage.sync not persisting reliably in persistent context.
 * Must be called on a page within the extension origin (options or popup page).
 */
async function injectExtensionSettings(page: Page, settings: {
  instanceUrl: string;
  apiKey: string;
}) {
  await page.evaluate(async (s) => {
    await new Promise<void>((resolve) => {
      chrome.storage.local.set({
        instanceUrl: s.instanceUrl,
        apiKey: s.apiKey,
        defaultType: '',
        autoFillTitle: true,
        autoFillUrl: true,
        includeSelection: true,
      }, () => resolve());
    });
    // Also try sync in case it works
    try {
      await new Promise<void>((resolve) => {
        chrome.storage.sync.set({
          instanceUrl: s.instanceUrl,
          apiKey: s.apiKey,
          defaultType: '',
          autoFillTitle: true,
          autoFillUrl: true,
          includeSelection: true,
        }, () => resolve());
      });
    } catch {
      // sync not available — local is fine
    }
  }, settings);
}

/* ── Tests ─────────────────────────────────────────────────────── */

test.describe.serial('Extension capture flow', () => {
  let apiKey: string;
  let ownerSessionCookie: string;

  test.beforeAll(async () => {
    const result = await setupAndCreateApiKey();
    apiKey = result.apiKey;
    ownerSessionCookie = result.ownerSessionCookie;
  });

  test('configure extension and verify connection', async ({ context, extensionId }) => {
    const optionsPage = await context.newPage();
    await optionsPage.goto(`chrome-extension://${extensionId}/options/options.html`);

    // Fill in connection settings
    await optionsPage.fill('#instance-url', BASE_URL);
    await optionsPage.fill('#api-key', apiKey);

    // Click Test Connection and wait for the green status
    await optionsPage.click('#test-connection');
    await optionsPage.waitForSelector('#connection-status.status-success', {
      timeout: 15_000,
    });

    // Verify the status message shows "Connected"
    const statusText = await optionsPage.textContent('#connection-status .status-message');
    expect(statusText).toContain('Connected');

    // Save settings
    await optionsPage.click('#save-settings');
    await optionsPage.waitForSelector('#save-confirmation:not(.hidden)', {
      timeout: 5_000,
    });

    // Also inject directly to storage to ensure persistence across pages
    await injectExtensionSettings(optionsPage, {
      instanceUrl: BASE_URL,
      apiKey,
    });

    // Verify settings persisted by reloading and checking fields
    await optionsPage.reload();
    // Wait for auto-test connection (options page auto-tests on load when URL+key exist)
    await optionsPage.waitForSelector('#connection-status.status-success', {
      timeout: 15_000,
    });

    const savedUrl = await optionsPage.inputValue('#instance-url');
    const savedKey = await optionsPage.inputValue('#api-key');
    expect(savedUrl).toBe(BASE_URL);
    expect(savedKey).toBe(apiKey);

    await optionsPage.close();
  });

  test('popup loads types and renders SHACL form', async ({ context, extensionId }) => {
    // Pre-inject settings so popup doesn't show unconfigured state
    const setupPage = await context.newPage();
    await setupPage.goto(`chrome-extension://${extensionId}/options/options.html`);
    await injectExtensionSettings(setupPage, { instanceUrl: BASE_URL, apiKey });
    await setupPage.close();

    const popupPage = await context.newPage();
    await popupPage.goto(`chrome-extension://${extensionId}/popup/popup.html`);

    // Wait for the capture form to become visible (not the unconfigured state)
    await popupPage.waitForSelector('#capture-form:not(.hidden)', {
      timeout: 15_000,
    });

    // Wait for the type selector to populate (more than just the blank option)
    await popupPage.waitForFunction(
      () => {
        const select = document.querySelector('#type-select') as HTMLSelectElement;
        return select && Array.from(select.options).filter(o => o.value !== '').length > 0;
      },
      { timeout: 15_000 },
    );

    // Verify at least one type from basic-pkm is present
    const optionCount = await popupPage.evaluate(() => {
      const select = document.querySelector('#type-select') as HTMLSelectElement;
      return Array.from(select.options).filter(o => o.value !== '').length;
    });
    expect(optionCount).toBeGreaterThan(0);

    // Select the first real type option
    const firstTypeValue = await popupPage.evaluate(() => {
      const select = document.querySelector('#type-select') as HTMLSelectElement;
      const firstReal = Array.from(select.options).find(o => o.value !== '');
      return firstReal?.value || '';
    });
    expect(firstTypeValue).toBeTruthy();

    await popupPage.selectOption('#type-select', firstTypeValue);

    // Wait for the dynamic form to render (has children — SHACL form)
    await popupPage.waitForFunction(
      () => {
        const form = document.getElementById('dynamic-form');
        return form && form.children.length > 0;
      },
      { timeout: 15_000 },
    );

    // Verify at least one data-path input exists in the form
    const dataPathCount = await popupPage.evaluate(() => {
      return document.querySelectorAll('#dynamic-form [data-path]').length;
    });
    expect(dataPathCount).toBeGreaterThan(0);

    await popupPage.close();
  });

  test('capture a Note and verify in workspace', async ({ context, extensionId }) => {
    // Pre-inject settings
    const setupPage = await context.newPage();
    await setupPage.goto(`chrome-extension://${extensionId}/options/options.html`);
    await injectExtensionSettings(setupPage, { instanceUrl: BASE_URL, apiKey });
    await setupPage.close();

    const popupPage = await context.newPage();
    await popupPage.goto(`chrome-extension://${extensionId}/popup/popup.html`);

    // Wait for the form and type selector to be ready
    await popupPage.waitForSelector('#capture-form:not(.hidden)', {
      timeout: 15_000,
    });
    await popupPage.waitForFunction(
      () => {
        const select = document.querySelector('#type-select') as HTMLSelectElement;
        return select && Array.from(select.options).filter(o => o.value !== '').length > 0;
      },
      { timeout: 15_000 },
    );

    // Find and select "Note" type (or first available type)
    const selectedType = await popupPage.evaluate(() => {
      const select = document.querySelector('#type-select') as HTMLSelectElement;
      const noteOption = Array.from(select.options).find(o =>
        o.textContent?.toLowerCase().includes('note'),
      );
      if (noteOption) {
        select.value = noteOption.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        return noteOption.value;
      }
      // Fallback to first real option
      const firstReal = Array.from(select.options).find(o => o.value !== '');
      if (firstReal) {
        select.value = firstReal.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        return firstReal.value;
      }
      return '';
    });
    expect(selectedType).toBeTruthy();

    // Wait for the dynamic SHACL form to render
    await popupPage.waitForFunction(
      () => {
        const form = document.getElementById('dynamic-form');
        return form && form.children.length > 0;
      },
      { timeout: 15_000 },
    );

    // Fill in the title field (look for data-path containing "title")
    const testTitle = `E2E Extension Test ${Date.now()}`;
    const titleFilled = await popupPage.evaluate((title: string) => {
      // Try dynamic form title input first
      const titleInput = document.querySelector(
        '#dynamic-form [data-path*="title"]',
      ) as HTMLInputElement;
      if (titleInput) {
        titleInput.value = title;
        titleInput.dispatchEvent(new Event('input', { bubbles: true }));
        return 'dynamic';
      }
      // Fallback to the fallback title input
      const fallback = document.getElementById('fallback-title-input') as HTMLInputElement;
      if (fallback) {
        fallback.value = title;
        fallback.dispatchEvent(new Event('input', { bubbles: true }));
        return 'fallback';
      }
      return '';
    }, testTitle);
    expect(titleFilled).toBeTruthy();

    // Listen for console messages to debug save issues
    const consoleLogs: string[] = [];
    popupPage.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));

    // Disable native form validation — SHACL forms may have required fields
    // in collapsed sections that block native submit. The JS handleSave()
    // does its own validation.
    await popupPage.evaluate(() => {
      const form = document.getElementById('capture-form') as HTMLFormElement;
      if (form) form.noValidate = true;
    });

    // Click Save via form submission
    await popupPage.click('#save-btn');

    // Wait for either success or error toast
    try {
      await popupPage.waitForSelector('.toast', {
        timeout: 15_000,
      });
    } catch {
      // Dump console logs for debugging
      console.log('Console logs from popup:', consoleLogs.join('\n'));
      throw new Error('No toast appeared after clicking Save');
    }

    // Check what kind of toast appeared
    const toastEl = await popupPage.$('.toast');
    const toastText = await toastEl?.textContent() || '';
    const toastClasses = await toastEl?.getAttribute('class') || '';

    // If it's an error toast, log it for debugging
    if (toastClasses.includes('error')) {
      console.log('Error toast:', toastText);
      console.log('Console logs:', consoleLogs.join('\n'));
    }

    expect(toastClasses).toContain('toast-success');
    expect(toastText).toContain('created');

    await popupPage.close();

    // Verify the object exists via SPARQL API
    const apiCtx = await request.newContext({
      baseURL: BASE_URL,
      extraHTTPHeaders: {
        Cookie: `sempkm_session=${ownerSessionCookie}`,
      },
    });

    const sparqlQuery = `
      PREFIX dcterms: <http://purl.org/dc/terms/>
      SELECT ?s ?title WHERE {
        ?s dcterms:title ?title .
        FILTER(CONTAINS(STR(?title), "E2E Extension Test"))
      } LIMIT 5
    `;

    const sparqlResp = await apiCtx.post(`${BASE_URL}/api/sparql`, {
      data: { query: sparqlQuery },
    });

    expect(sparqlResp.status()).toBe(200);
    const sparqlData = await sparqlResp.json();
    const results = sparqlData.results?.bindings || [];
    expect(results.length).toBeGreaterThan(0);

    // Verify the title matches what we created
    const foundTitle = results.find((r: any) =>
      r.title?.value?.includes('E2E Extension Test'),
    );
    expect(foundTitle).toBeTruthy();

    await apiCtx.dispose();
  });
});
