/**
 * Bug Fix Regression E2E Tests
 *
 * Regression tests for bugs fixed in v2.4 (BUG-04 through BUG-09).
 * Tests verify the fixes remain in place by exercising the specific
 * UI behaviors that were broken.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Bug Fix Regressions', () => {
  test('BUG-04: type-specific accent colors on tabs', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Open a Note object
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Read accent color for Note type
    const noteColor = await ownerPage.evaluate(() => {
      const group = document.querySelector('.dv-active-group');
      return group ? getComputedStyle(group).getPropertyValue('--tab-accent-color').trim() : '';
    });

    // Open a Person object
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.people.alice.iri, label: SEED.people.alice.name },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Read accent color for Person type
    const personColor = await ownerPage.evaluate(() => {
      const group = document.querySelector('.dv-active-group');
      return group ? getComputedStyle(group).getPropertyValue('--tab-accent-color').trim() : '';
    });

    // Both should be non-empty and different
    expect(noteColor.length).toBeGreaterThan(0);
    expect(personColor.length).toBeGreaterThan(0);
    expect(noteColor).not.toBe(personColor);
  });

  test('BUG-05: card view borders render', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const cardSpec = specs.find((s: any) => s.renderer_type === 'card');

    if (!cardSpec) {
      test.skip(true, 'No card view spec available in seed data');
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(cardSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/card/' + iri, isView: true, isSpecial: true },
          title: 'Card View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('.card-grid, .flip-card', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const cards = ownerPage.locator(SEL.views.card);
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);

    // Verify at least one card front face has a visible border
    // Border is on .flip-card-front (child), not on .flip-card (data-testid="card-item")
    const cardFront = ownerPage.locator('.flip-card-front').first();
    const hasBorder = await cardFront.evaluate((el: HTMLElement) => {
      const style = getComputedStyle(el);
      const borderStyle = style.borderStyle;
      const borderWidth = parseFloat(style.borderWidth);
      return borderStyle !== 'none' && borderWidth > 0;
    });

    expect(hasBorder).toBe(true);
  });

  test('BUG-06: Alt+K opens command palette', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Press Alt+K to open command palette
    await ownerPage.keyboard.press('Alt+k');

    // Wait for ninja-keys to have the "opened" attribute (shadow DOM web component)
    const ninjaKeys = ownerPage.locator('ninja-keys');
    await expect(ninjaKeys).toHaveAttribute('opened', '', { timeout: 5000 });

    // Press Escape to close
    await ownerPage.keyboard.press('Escape');

    // Verify opened attribute is removed
    await ownerPage.waitForFunction(() => {
      const nk = document.querySelector('ninja-keys');
      return nk !== null && !nk.hasAttribute('opened');
    }, { timeout: 5000 });
  });

  test('BUG-07: inactive tabs do not show accent bleed', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Open two objects to create multiple tabs
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.people.alice.iri, label: SEED.people.alice.name },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Get all inactive tabs (not the active one)
    const inactiveTabs = ownerPage.locator('.dv-tab:not(.dv-active-tab)');
    const inactiveCount = await inactiveTabs.count();
    expect(inactiveCount).toBeGreaterThan(0);

    // Check that inactive tabs do NOT have a colored bottom border
    for (let i = 0; i < inactiveCount; i++) {
      const borderColor = await inactiveTabs.nth(i).evaluate((el: HTMLElement) => {
        return getComputedStyle(el).borderBottomColor;
      });
      // Inactive tab border should be transparent or match default (no accent)
      // Active tab accent is applied via CSS scoped to .dv-active-group .dv-active-tab
      const isTransparentOrDefault = borderColor === 'rgba(0, 0, 0, 0)' ||
        borderColor === 'transparent' ||
        borderColor === 'rgb(0, 0, 0)' || // default
        !borderColor;

      // The key assertion: inactive tab should NOT have a bright accent color
      // We check it's not the same as the active tab's accent
      const activeTabBorder = await ownerPage.evaluate(() => {
        const activeTab = document.querySelector('.dv-active-group .dv-tab.dv-active-tab');
        return activeTab ? getComputedStyle(activeTab).borderBottomColor : '';
      });

      // If active tab has an accent, inactive should differ
      if (activeTabBorder && activeTabBorder !== 'rgba(0, 0, 0, 0)' && activeTabBorder !== 'transparent') {
        expect(borderColor).not.toBe(activeTabBorder);
      }
    }
  });

  test('BUG-08: panel chevron icons visible', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Open a seed object to populate the right pane sections
    await ownerPage.evaluate(
      ({ iri, label }) => {
        (window as any).openTab(iri, label);
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Look for right-section-chevron or collapsible section headers with chevrons
    const chevrons = ownerPage.locator('.right-section-chevron');
    const chevronCount = await chevrons.count();

    if (chevronCount === 0) {
      // Fallback: check for any SVG chevron icons in the right panel section headers
      const sectionHeaders = ownerPage.locator('.right-section-header svg, .section-toggle svg');
      const svgCount = await sectionHeaders.count();
      expect(svgCount).toBeGreaterThan(0);

      // Verify at least one has non-zero dimensions
      const box = await sectionHeaders.first().boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThan(0);
      expect(box!.height).toBeGreaterThan(0);
      return;
    }

    // Verify at least one chevron is visible with non-zero dimensions
    const firstChevron = chevrons.first();
    await expect(firstChevron).toBeVisible();
    const box = await firstChevron.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(0);
    expect(box!.height).toBeGreaterThan(0);
  });

  test('BUG-09: concept search and linking', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Open command palette with Alt+K
    await ownerPage.keyboard.press('Alt+k');
    const ninjaKeys = ownerPage.locator('ninja-keys');
    await expect(ninjaKeys).toHaveAttribute('opened', '', { timeout: 5000 });

    // Type a concept name using keyboard (ninja-keys intercepts keyboard input)
    await ownerPage.keyboard.type(SEED.concepts.km.label, { delay: 50 });

    // Wait for FTS search debounce and results to render
    await ownerPage.waitForTimeout(2000);

    // Verify results contain the concept name by checking shadow DOM content
    const hasResults = await ownerPage.evaluate((label) => {
      const nk = document.querySelector('ninja-keys') as any;
      if (!nk) return false;

      // Check shadow DOM rendered action items
      if (nk.shadowRoot) {
        const items = nk.shadowRoot.querySelectorAll('[class*="action"]');
        for (const item of items) {
          if (item.textContent && item.textContent.includes(label)) return true;
        }
        // Also check all text content in the shadow root
        const allText = nk.shadowRoot.textContent || '';
        if (allText.includes(label)) return true;
      }

      // Check light DOM content
      const lightText = nk.textContent || '';
      if (lightText.includes(label)) return true;

      // Check ninja-keys data array (may have search results)
      if (nk._flatData || nk.data) {
        const data = nk._flatData || nk.data;
        return Array.isArray(data) && data.some((d: any) =>
          (d.title || d.label || '').includes(label)
        );
      }
      return false;
    }, SEED.concepts.km.label);

    expect(hasResults).toBe(true);

    // Close palette
    await ownerPage.keyboard.press('Escape');
  });
});
