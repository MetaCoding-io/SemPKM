/**
 * Admin Entailment Config E2E Tests
 *
 * Tests the inference entailment configuration page for a mental model:
 * page load, toggle rendering, type labels, ontology examples, save button.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Admin Entailment Config', () => {
  test('entailment config page loads for basic-pkm model', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/entailment`);
    const config = ownerPage.locator('.entailment-config');
    await expect(config).toBeVisible({ timeout: 15000 });

    // Page title should mention "Inference Settings"
    await expect(ownerPage.locator('h1')).toContainText('Inference Settings');
  });

  test('entailment toggles render with checkboxes', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/entailment`);
    await ownerPage.locator('.entailment-config').waitFor({ timeout: 15000 });

    const toggles = ownerPage.locator('.entailment-toggle');
    const count = await toggles.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // Each toggle should have a checkbox inside .entailment-label
    for (let i = 0; i < count; i++) {
      const toggle = toggles.nth(i);
      const checkbox = toggle.locator('.entailment-label input[type="checkbox"]');
      await expect(checkbox).toBeAttached();
    }
  });

  test('entailment type labels show owl:inverseOf and sh:rule', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/entailment`);
    await ownerPage.locator('.entailment-config').waitFor({ timeout: 15000 });

    const typeLabels = ownerPage.locator('.entailment-type-label');
    const allTexts = await typeLabels.allTextContents();

    expect(allTexts.some((t) => t.includes('owl:inverseOf'))).toBe(true);
    expect(allTexts.some((t) => t.includes('sh:rule'))).toBe(true);
  });

  test('ontology examples render for inverseOf', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/entailment`);
    await ownerPage.locator('.entailment-config').waitFor({ timeout: 15000 });

    // Find the toggle containing "inverseOf"
    const inverseToggle = ownerPage.locator('.entailment-toggle', {
      hasText: 'inverseOf',
    });
    await expect(inverseToggle).toBeVisible();

    // Should have examples (not "no examples")
    const examples = inverseToggle.locator('.entailment-examples');
    await expect(examples).toBeVisible();

    // At least one example span should be visible
    const exampleSpans = inverseToggle.locator('.entailment-example');
    const exampleCount = await exampleSpans.count();
    expect(exampleCount).toBeGreaterThanOrEqual(1);
  });

  test('save configuration button is present', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm/entailment`);
    await ownerPage.locator('.entailment-config').waitFor({ timeout: 15000 });

    const saveBtn = ownerPage.locator('button[type="submit"]', {
      hasText: 'Save Configuration',
    });
    await expect(saveBtn).toBeVisible();
  });
});
