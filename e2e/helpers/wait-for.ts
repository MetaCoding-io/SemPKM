/**
 * Custom wait helpers for htmx-based SemPKM UI.
 *
 * Since SemPKM uses htmx (not a SPA), many interactions result in partial
 * DOM swaps rather than full page navigations. These helpers account for
 * the htmx lifecycle.
 */
import { Page, expect } from '@playwright/test';

/**
 * Wait for an htmx swap to complete on a target element.
 * htmx adds the `htmx-settling` class during the swap settling phase.
 * We wait for the settling class to be added then removed.
 */
export async function waitForHtmxSettle(page: Page, selector: string, timeoutMs = 10000) {
  await page.waitForFunction(
    ({ sel, timeout }) => {
      return new Promise<boolean>((resolve) => {
        const el = document.querySelector(sel);
        if (!el) { resolve(false); return; }

        // If there's no pending htmx request, content is already settled
        if (!el.classList.contains('htmx-request') && !el.classList.contains('htmx-settling')) {
          resolve(true);
          return;
        }

        // Wait for settling to finish
        const observer = new MutationObserver(() => {
          if (!el.classList.contains('htmx-request') && !el.classList.contains('htmx-settling')) {
            observer.disconnect();
            resolve(true);
          }
        });
        observer.observe(el, { attributes: true, attributeFilter: ['class'] });

        setTimeout(() => { observer.disconnect(); resolve(false); }, timeout);
      });
    },
    { sel: selector, timeout: timeoutMs },
    { timeout: timeoutMs + 1000 },
  );
}

/**
 * Wait for an element to appear in the DOM after an htmx swap.
 * More reliable than page.waitForSelector for htmx partials since
 * the element might be swapped into a target that already exists.
 */
export async function waitForElement(page: Page, selector: string, timeoutMs = 10000) {
  await page.waitForSelector(selector, { state: 'attached', timeout: timeoutMs });
}

/**
 * Wait for text content to appear somewhere on the page.
 * Useful for verifying htmx-swapped content loaded correctly.
 */
export async function waitForText(page: Page, text: string, timeoutMs = 10000) {
  await expect(page.getByText(text)).toBeVisible({ timeout: timeoutMs });
}

/**
 * Wait for the workspace to be fully loaded.
 * The workspace is ready when the nav tree and editor area are present.
 */
export async function waitForWorkspace(page: Page, timeoutMs = 15000) {
  // The workspace page has a .dashboard-layout container
  await page.waitForSelector('.dashboard-layout', { state: 'attached', timeout: timeoutMs });
}

/**
 * Wait for no active htmx requests on the page.
 * Useful before making assertions to ensure all swaps are complete.
 */
export async function waitForIdle(page: Page, timeoutMs = 10000) {
  await page.waitForFunction(
    () => document.querySelectorAll('.htmx-request').length === 0,
    { timeout: timeoutMs },
  );
}
