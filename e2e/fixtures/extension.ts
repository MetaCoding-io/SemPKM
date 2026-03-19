/**
 * Playwright fixture for testing the SemPKM browser extension.
 *
 * Extension testing requires `chromium.launchPersistentContext()` with
 * `--load-extension` args — fundamentally different from normal test flows.
 * The persistent context doesn't share cookies/state with other test projects.
 *
 * Provides:
 * - `context`: BrowserContext with extension loaded via persistent context
 * - `extensionId`: Dynamically extracted extension ID from service worker URL
 *
 * Usage:
 *   import { test, expect } from '../../fixtures/extension';
 *   test('my extension test', async ({ context, extensionId }) => { ... });
 */
import { test as base, chromium, type BrowserContext } from '@playwright/test';
import path from 'path';

const EXTENSION_PATH = path.resolve(__dirname, '../../extension');

type ExtensionFixtures = {
  /** Persistent browser context with the extension loaded */
  context: BrowserContext;
  /** Dynamically discovered extension ID */
  extensionId: string;
};

export const test = base.extend<ExtensionFixtures>({
  // eslint-disable-next-line no-empty-pattern
  context: async ({}, use) => {
    const args = [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`,
    ];

    // In CI, use the new headless mode that supports extensions
    if (process.env.CI) {
      args.push('--headless=new');
    }

    const context = await chromium.launchPersistentContext('', {
      headless: false,
      args,
    });

    await use(context);
    await context.close();
  },

  extensionId: async ({ context }, use) => {
    // Wait for the service worker to register — the extension's background
    // script registers as a service worker on load.
    let [sw] = context.serviceWorkers();
    if (!sw) {
      sw = await context.waitForEvent('serviceworker');
    }

    // Extension ID is the hostname in the service worker URL:
    // chrome-extension://<id>/background/service-worker.js
    const id = sw.url().split('/')[2];
    await use(id);
  },
});

export { expect } from '@playwright/test';
