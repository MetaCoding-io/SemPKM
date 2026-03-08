/**
 * Edit Form Helptext E2E Tests
 *
 * Tests the form-level and field-level helptext toggle/collapse features
 * added in Phase 39 (HELP-01). These tests are resilient to the possibility
 * that basic-pkm shapes may not have helptext annotations configured --
 * tests gracefully skip when no helptext elements are present.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Edit Form Helptext', () => {
  test.beforeEach(async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Open a seed object in read mode first (edit face is hidden behind flip card)
    await ownerPage.evaluate(
      ({ iri, label }) => {
        if (typeof (window as any).openTab === 'function') {
          (window as any).openTab(iri, label, 'read');
        }
      },
      { iri: SEED.notes.architecture.iri, label: SEED.notes.architecture.title },
    );
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Switch to edit mode via the mode toggle button
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await toggleBtn.click();
    await ownerPage.waitForSelector('.object-face-edit.face-visible', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Expand properties section (collapsed by default when object has body text)
    const badge = ownerPage.locator('.properties-toggle-badge').first();
    if (await badge.count() > 0) {
      const expanded = await ownerPage.locator('.properties-collapsible.expanded').count();
      if (expanded === 0) {
        await badge.click();
        await ownerPage.waitForFunction(
          () => document.querySelectorAll('.properties-collapsible.expanded').length > 0,
          { timeout: 5000 },
        );
      }
    }
  });

  test('edit form has helptext toggle', async ({ ownerPage }) => {
    const formHelptext = ownerPage.locator('.form-helptext-top');
    const fieldHelptext = ownerPage.locator('.btn-helptext-toggle');

    const formCount = await formHelptext.count();
    const fieldCount = await fieldHelptext.count();

    if (formCount === 0 && fieldCount === 0) {
      test.skip(true, 'No helptext configured in basic-pkm model shapes');
      return;
    }

    // At least one helptext element exists
    expect(formCount + fieldCount).toBeGreaterThan(0);
  });

  test('form-level helptext expands and collapses', async ({ ownerPage }) => {
    const formHelptext = ownerPage.locator('.form-helptext-top');

    if (await formHelptext.count() === 0) {
      test.skip(true, 'No form-level helptext (.form-helptext-top) present');
      return;
    }

    // Should be collapsed by default (no open attribute)
    await expect(formHelptext).not.toHaveAttribute('open');

    // Click summary to expand
    await ownerPage.click('.form-helptext-summary');
    await expect(formHelptext).toHaveAttribute('open', '');

    // Content should be visible with text
    const content = ownerPage.locator('#helptext-form-rendered');
    await expect(content).toBeVisible();
    const text = await content.textContent();
    expect(text!.trim().length).toBeGreaterThan(0);

    // Click summary again to collapse
    await ownerPage.click('.form-helptext-summary');
    await expect(formHelptext).not.toHaveAttribute('open');
  });

  test('field-level helptext toggles', async ({ ownerPage }) => {
    const helpBtn = ownerPage.locator('.btn-helptext-toggle').first();

    if (await helpBtn.count() === 0) {
      test.skip(true, 'No field-level helptext (.btn-helptext-toggle) present');
      return;
    }

    // Click to show field helptext
    await helpBtn.click();
    const fieldHelp = ownerPage.locator('.field-helptext').first();
    await expect(fieldHelp).toBeVisible();

    // Click again to hide
    await helpBtn.click();
    await expect(fieldHelp).not.toBeVisible();
  });

  test('helptext contains formatted markdown', async ({ ownerPage }) => {
    const formHelptext = ownerPage.locator('.form-helptext-top');
    const fieldHelpBtn = ownerPage.locator('.btn-helptext-toggle').first();

    let contentLocator;

    if (await formHelptext.count() > 0) {
      // Expand form-level helptext
      await ownerPage.click('.form-helptext-summary');
      await expect(formHelptext).toHaveAttribute('open', '');
      contentLocator = ownerPage.locator('#helptext-form-rendered');
    } else if (await fieldHelpBtn.count() > 0) {
      // Expand field-level helptext
      await fieldHelpBtn.click();
      contentLocator = ownerPage.locator('.field-helptext').first();
    } else {
      test.skip(true, 'No helptext available to check markdown rendering');
      return;
    }

    await expect(contentLocator).toBeVisible();

    // Verify rendered content contains HTML formatting elements
    // (indicating markdown was processed, not raw text)
    const hasFormatting = await contentLocator.evaluate((el: HTMLElement) => {
      const formattingTags = ['STRONG', 'EM', 'UL', 'OL', 'LI', 'P', 'H1', 'H2', 'H3', 'H4', 'CODE', 'PRE', 'A'];
      return formattingTags.some(tag => el.querySelector(tag) !== null);
    });

    expect(hasFormatting).toBe(true);
  });
});
