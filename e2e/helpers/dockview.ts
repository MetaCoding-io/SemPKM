/**
 * Dockview integration helpers for E2E tests.
 *
 * After Phase 30 (dockview migration), the editor area is managed by
 * dockview-core. Tests must use window.SemPKM.openTab() and friends instead of
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
      if (typeof (window as any).SemPKM?.openTab === 'function') {
        (window as any).SemPKM.openTab(iri, label || iri, mode || 'read');
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
      if (typeof (window as any).SemPKM?.openViewTab === 'function') {
        (window as any).SemPKM.openViewTab(viewId, viewLabel, viewType);
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
    if (typeof (window as any).SemPKM?.openSettingsTab === 'function') {
      (window as any).SemPKM.openSettingsTab();
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
    if (typeof (window as any).SemPKM?.openDocsTab === 'function') {
      (window as any).SemPKM.openDocsTab();
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
    const dv = (window as any).SemPKM?._dockview;
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
      const target = (window as any).SemPKM?.getActiveEditorArea?.();
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
      const dv = (window as any).SemPKM?._dockview;
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
    const dv = (window as any).SemPKM?._dockview;
    return dv ? dv.panels.length : 0;
  });
}

/**
 * Get all dockview panel titles.
 */
export async function getTabTitles(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const dv = (window as any).SemPKM?._dockview;
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
      const dv = (window as any).SemPKM?._dockview;
      return dv?.activePanel?.id === id;
    },
    panelId,
  );
}

/**
 * Open a generic view tab via the application's openGenericViewTab() API.
 *
 * This wraps `window.SemPKM.openGenericViewTab(renderer, scopeQuery, scopeLabel)`,
 * the M031 entry point that opens table/card/graph/kanban tabs from the
 * explorer sidebar or programmatically.
 *
 * @param page        Playwright page
 * @param renderer    One of 'table', 'card', 'graph', 'kanban'
 * @param waitSelector CSS selector to wait for after the panel opens
 * @param scopeQuery  Optional SPARQL query to scope the view
 * @param scopeLabel  Optional label for scoped tab title
 * @param timeoutMs   Max wait time for the panel to appear (default 15s)
 */
export async function openGenericViewTab(
  page: Page,
  renderer: 'table' | 'card' | 'graph' | 'kanban' | 'calendar' | 'map' | 'timeline' | 'quadrant' | 'bmc' | 'okr' | 'decision-matrix',
  waitSelector: string,
  scopeQuery?: string,
  scopeLabel?: string,
  timeoutMs = 15000,
) {
  await page.evaluate(({ renderer, scopeQuery, scopeLabel }) => {
    if (typeof (window as any).SemPKM?.openGenericViewTab === 'function') {
      (window as any).SemPKM.openGenericViewTab(renderer, scopeQuery || '', scopeLabel || '');
    }
  }, { renderer, scopeQuery, scopeLabel });
  await page.waitForSelector(waitSelector, { timeout: timeoutMs });
}

/**
 * Open a dashboard tab via the application's openDashboardTab() API.
 *
 * Wraps `window.SemPKM.openDashboardTab(id, name)` and waits for the GridStack
 * container to appear, indicating the dashboard page has loaded.
 *
 * @param page           Playwright page
 * @param dashboardId    Dashboard UUID string
 * @param dashboardName  Display name for the tab title
 * @param timeoutMs      Max wait time for the GridStack container (default 15s)
 */
export async function openDashboardTab(
  page: Page,
  dashboardId: string,
  dashboardName: string,
  timeoutMs = 15000,
) {
  await page.evaluate(
    ({ id, name }) => {
      if (typeof (window as any).SemPKM?.openDashboardTab === 'function') {
        (window as any).SemPKM.openDashboardTab(id, name);
      }
    },
    { id: dashboardId, name: dashboardName },
  );
  // Wait for GridStack container to appear in the dockview panel
  await page.waitForSelector('.grid-stack', { timeout: timeoutMs });
}
