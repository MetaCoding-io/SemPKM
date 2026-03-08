/**
 * Dockview integration helpers for E2E tests.
 *
 * After Phase 30 (dockview migration), the editor area is managed by
 * dockview-core. Tests must use window.openTab() and friends instead of
 * directly targeting #editor-area-group-1 with htmx.ajax().
 *
 * These helpers wrap the browser-side API calls and provide reliable
 * waiting patterns for dockview panel content to render.
 */
import { Page } from '@playwright/test';

/**
 * Open an object tab via the application's openTab() API.
 * Waits for the .object-tab element to appear in the DOM.
 */
export async function openObjectTab(
  page: Page,
  iri: string,
  label?: string,
  mode?: 'read' | 'edit',
  timeoutMs = 10000,
) {
  await page.evaluate(
    ({ iri, label, mode }) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, label || iri, mode || 'read');
      }
    },
    { iri, label, mode },
  );
  await page.waitForSelector('.object-tab', { timeout: timeoutMs });
}

/**
 * Open a view tab via the application's openViewTab() API.
 * Waits for the view container to appear.
 */
export async function openViewTab(
  page: Page,
  viewId: string,
  viewLabel: string,
  viewType: 'table' | 'card' | 'graph',
  waitSelector: string,
  timeoutMs = 15000,
) {
  await page.evaluate(
    ({ viewId, viewLabel, viewType }) => {
      if (typeof (window as any).openViewTab === 'function') {
        (window as any).openViewTab(viewId, viewLabel, viewType);
      }
    },
    { viewId, viewLabel, viewType },
  );
  await page.waitForSelector(waitSelector, { timeout: timeoutMs });
}

/**
 * Open the Settings tab via the application's openSettingsTab() API.
 * Waits for the settings page data-testid to appear.
 */
export async function openSettingsTab(page: Page, timeoutMs = 10000) {
  await page.evaluate(() => {
    if (typeof (window as any).openSettingsTab === 'function') {
      (window as any).openSettingsTab();
    }
  });
  await page.waitForSelector('[data-testid="settings-page"]', { timeout: timeoutMs });
}

/**
 * Open the Docs tab via the application's openDocsTab() API.
 * Waits for the docs page to appear.
 */
export async function openDocsTab(page: Page, timeoutMs = 10000) {
  await page.evaluate(() => {
    if (typeof (window as any).openDocsTab === 'function') {
      (window as any).openDocsTab();
    }
  });
  await page.waitForSelector('#docs-page', { timeout: timeoutMs });
}

/**
 * Open the type picker (new object form) via the application API.
 * Loads the type picker into the active dockview panel.
 */
export async function openTypePicker(page: Page, timeoutMs = 10000) {
  await page.evaluate(() => {
    const dv = (window as any)._dockview;
    if (!dv) return;
    // Create a temporary panel if none exist
    if (dv.panels.length === 0) {
      dv.addPanel({
        id: 'new-object-' + Date.now(),
        component: 'special-panel',
        params: { specialType: 'types', isView: false, isSpecial: true },
        title: 'New Object',
      });
    } else {
      // Load types into active panel
      const target = (window as any).getActiveEditorArea?.();
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/types', { target });
      }
    }
  });
  await page.waitForSelector('[data-testid="type-picker"]', { timeout: timeoutMs });
}

/**
 * Open a new object form for a specific type.
 */
export async function openNewObjectForm(
  page: Page,
  typeIri: string,
  timeoutMs = 10000,
) {
  await page.evaluate(
    ({ typeIri }) => {
      const dv = (window as any)._dockview;
      if (!dv) return;
      // Create a panel for the new object form
      const panelId = 'new-' + Date.now();
      dv.addPanel({
        id: panelId,
        component: 'special-panel',
        params: { specialType: 'objects/new?type=' + encodeURIComponent(typeIri), isView: false, isSpecial: true },
        title: 'New Object',
      });
    },
    { typeIri },
  );
  await page.waitForSelector('[data-testid="object-form"]', { timeout: timeoutMs });
}

/**
 * Get the number of open dockview panels.
 */
export async function getTabCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    const dv = (window as any)._dockview;
    return dv ? dv.panels.length : 0;
  });
}

/**
 * Get all dockview panel titles.
 */
export async function getTabTitles(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const dv = (window as any)._dockview;
    if (!dv) return [];
    return dv.panels.map((p: any) => p.title || p.id);
  });
}

/**
 * Check if a panel with a given ID exists and is active.
 */
export async function isPanelActive(page: Page, panelId: string): Promise<boolean> {
  return page.evaluate(
    (id) => {
      const dv = (window as any)._dockview;
      return dv?.activePanel?.id === id;
    },
    panelId,
  );
}
