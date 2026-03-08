/**
 * Object View Redesign E2E Tests (Phase 31)
 *
 * Verifies the body-first layout, properties toggle badge, localStorage
 * persistence, empty-body auto-expand, edit mode consistency, shared
 * collapse state across flip, and 3D flip regression.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Load an object into a dockview panel via the app's openTab API. */
async function loadObjectInEditor(page: any, iri: string, mode: 'read' | 'edit' = 'read') {
  await page.evaluate(({ iri, mode }: { iri: string; mode: string }) => {
    if (typeof (window as any).openTab === 'function') {
      (window as any).openTab(iri, iri, mode);
    }
  }, { iri, mode });
}

/** Open an object as a tab (adds to tab bar + loads content). */
async function openTab(page: any, iri: string, label: string, mode: 'read' | 'edit' = 'read') {
  await page.evaluate(
    ({ iri, label, mode }: { iri: string; label: string; mode: string }) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, label, mode);
      }
    },
    { iri, label, mode },
  );
}

/** Expand the properties panel if collapsed. */
async function expandProperties(page: any) {
  const badge = page.locator('.properties-toggle-badge').first();
  if (await badge.count() === 0) return;
  await badge.waitFor({ state: 'visible', timeout: 5000 });
  const expanded = await page.locator('.properties-collapsible.expanded').count();
  if (expanded > 0) return;
  await badge.click();
  // Use waitForFunction — read face may be hidden behind 3D flip, waitForSelector requires visibility
  await page.waitForFunction(
    () => document.querySelectorAll('.properties-collapsible.expanded').length > 0,
    { timeout: 5000 },
  );
}

/** Collapse the properties panel if expanded. */
async function collapseProperties(page: any) {
  const badge = page.locator('.properties-toggle-badge').first();
  if (await badge.count() === 0) return;
  const expanded = await page.locator('.properties-collapsible.expanded').count();
  if (expanded === 0) return;
  await badge.click();
  await page.waitForFunction(
    () => document.querySelectorAll('.properties-collapsible.expanded').length === 0,
    { timeout: 5000 },
  );
}

// ---------------------------------------------------------------------------

test.describe('Object View Redesign – Body-First Layout', () => {
  test('Markdown body visible immediately, properties collapsed', async ({ ownerPage }) => {
    // Architecture note has both properties and a Markdown body
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Markdown body should be visible immediately
    const body = ownerPage.locator('.object-face-read .markdown-body').first();
    await expect(body).toBeVisible({ timeout: 5000 });

    // Properties should be collapsed (no .expanded class)
    const expandedProps = await ownerPage.locator('.properties-collapsible.expanded').count();
    expect(expandedProps).toBe(0);

    // Property table should not be visible
    const propTable = ownerPage.locator('.property-table');
    await expect(propTable.first()).not.toBeVisible();
  });

  test('properties badge shows correct count in toolbar', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Badge should be visible and contain "propert" (matches "N properties" or "1 property")
    const badge = ownerPage.locator('.properties-toggle-badge');
    await expect(badge).toBeVisible({ timeout: 5000 });
    await expect(badge).toContainText(/\d+ propert/);
  });
});

// ---------------------------------------------------------------------------

test.describe('Object View Redesign – Properties Toggle', () => {
  test('clicking badge expands properties, clicking again collapses', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Initially collapsed
    let expandedCount = await ownerPage.locator('.properties-collapsible.expanded').count();
    expect(expandedCount).toBe(0);

    // Click to expand
    await expandProperties(ownerPage);
    const propTable = ownerPage.locator('.property-table');
    await expect(propTable.first()).toBeVisible({ timeout: 5000 });

    // Click to collapse
    await collapseProperties(ownerPage);
    await expect(propTable.first()).not.toBeVisible();
  });

  test('properties state persists across page reload via localStorage', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Open object and expand properties
    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);
    await expandProperties(ownerPage);

    // Verify localStorage has the preference
    const pref = await ownerPage.evaluate((iri: string) => {
      try {
        const data = JSON.parse(localStorage.getItem('sempkm_props_collapsed') || '{}');
        return data[iri];
      } catch { return undefined; }
    }, SEED.notes.architecture.iri);
    expect(pref).toBe(false); // false = expanded

    // Reload page
    await ownerPage.reload();
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Reopen the same object
    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Properties should still be expanded (preference restored)
    const expandedCount = await ownerPage.locator('.properties-collapsible.expanded').count();
    expect(expandedCount).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------

test.describe('Object View Redesign – Empty Body & Edit Mode', () => {
  test('properties auto-expand when object has no Markdown body', async ({ ownerPage }) => {
    // Person objects (Alice) have properties but typically no Markdown body
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Clear any stored preference for this object
    await ownerPage.evaluate((iri: string) => {
      try {
        const data = JSON.parse(localStorage.getItem('sempkm_props_collapsed') || '{}');
        delete data[iri];
        localStorage.setItem('sempkm_props_collapsed', JSON.stringify(data));
      } catch {}
    }, SEED.people.alice.iri);

    await loadObjectInEditor(ownerPage, SEED.people.alice.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Properties should be expanded by default (no body → auto-expand)
    const badge = ownerPage.locator('.properties-toggle-badge').first();
    if (await badge.count() > 0) {
      const expandedCount = await ownerPage.locator('.properties-collapsible.expanded').count();
      expect(expandedCount).toBeGreaterThan(0);
    }

    // "No content" placeholder or empty body area should be present
    const placeholder = ownerPage.locator('.body-placeholder');
    const markdownBody = ownerPage.locator('.markdown-body');
    const hasPlaceholder = await placeholder.count() > 0;
    const hasBody = await markdownBody.count() > 0;
    // Either placeholder is shown or there's simply no body section
    expect(hasPlaceholder || !hasBody).toBe(true);
  });

  test('edit mode: body editor primary, properties collapsible', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title, 'edit');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Editor section should be visible (body editor is primary in edit mode)
    const editorSection = ownerPage.locator('.object-editor-section');
    await expect(editorSection.first()).toBeVisible({ timeout: 5000 });

    // Properties badge should be available in edit mode
    const badge = ownerPage.locator('.properties-toggle-badge');
    await expect(badge.first()).toBeVisible({ timeout: 5000 });

    // Expand properties to access form
    await expandProperties(ownerPage);
    const form = ownerPage.locator('[data-testid="object-form"]');
    await expect(form).toBeVisible({ timeout: 5000 });
  });

  test('shared collapse state: expand in read mode carries to edit mode', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Expand properties in read mode
    await expandProperties(ownerPage);
    const readProps = ownerPage.locator('.object-face-read .properties-collapsible.expanded');
    await expect(readProps.first()).toBeAttached();

    // Flip to edit mode
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await toggleBtn.click();
    await ownerPage.waitForSelector('.object-face-edit.face-visible', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Properties should also be expanded on the edit face
    const editProps = ownerPage.locator('.object-face-edit .properties-collapsible.expanded');
    await expect(editProps.first()).toBeAttached();
  });
});

// ---------------------------------------------------------------------------

test.describe('Object View Redesign – Toolbar & Flip Regression', () => {
  test('toolbar layout: title left, controls right with type badge', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Title should be visible
    const title = ownerPage.locator('.object-toolbar-title');
    await expect(title.first()).toBeVisible({ timeout: 5000 });

    // Type badge should be visible
    const typeBadge = ownerPage.locator('.object-toolbar-type');
    await expect(typeBadge.first()).toBeVisible({ timeout: 5000 });

    // Mode toggle (Edit button) should be visible
    const modeToggle = ownerPage.locator('.mode-toggle');
    await expect(modeToggle.first()).toBeVisible({ timeout: 5000 });

    // Properties badge should be visible
    const propsBadge = ownerPage.locator('.properties-toggle-badge');
    await expect(propsBadge.first()).toBeVisible({ timeout: 5000 });
  });

  test('3D flip to edit mode still works after redesign', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Click Edit to trigger 3D flip
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await expect(toggleBtn).toHaveText('Edit');
    await toggleBtn.click();

    // Edit face should become visible
    await ownerPage.waitForSelector('.object-face-edit.face-visible', { timeout: 10000 });

    // Toggle should now say "Cancel"
    await expect(toggleBtn).toHaveText('Cancel');

    // Form should exist in DOM
    const form = ownerPage.locator('[data-testid="object-form"]');
    await expect(form).toBeAttached({ timeout: 5000 });

    // Click Cancel to flip back
    await toggleBtn.click();
    await ownerPage.waitForSelector('.object-face-read:not(.face-hidden)', { timeout: 10000 });

    // Should be back in read mode
    await expect(toggleBtn).toHaveText('Edit');

    // Markdown body should be visible again
    const body = ownerPage.locator('.markdown-body');
    await expect(body.first()).toBeVisible({ timeout: 5000 });
  });
});
