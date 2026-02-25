/**
 * Admin Models E2E Tests
 *
 * Tests the admin model management page: listing installed models,
 * model details display, and access control.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Admin Models Page', () => {
  test('models page loads and shows Basic PKM model', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // Should display the model list
    const modelList = ownerPage.locator(SEL.admin.modelList);
    await expect(modelList).toBeVisible();

    // Basic PKM model should be listed
    await expect(modelList).toContainText('Basic PKM');
  });

  test('model table shows name, version, and description columns', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // Table headers
    const headers = ownerPage.locator(`${SEL.admin.modelList} thead th`);
    const headerTexts = await headers.allInnerTexts();

    expect(headerTexts).toContain('Name');
    expect(headerTexts).toContain('Version');
    expect(headerTexts).toContain('Description');
  });

  test('model table has a row for Basic PKM with Remove button', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // Find the row containing "Basic PKM"
    const modelRow = ownerPage.locator(`${SEL.admin.modelList} tbody tr`).filter({
      hasText: 'Basic PKM',
    });
    await expect(modelRow).toBeVisible();

    // Should have a Remove button
    const removeBtn = modelRow.locator('button', { hasText: 'Remove' });
    await expect(removeBtn).toBeVisible();
  });

  test('install form is present with path input', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    // Install form elements
    await expect(ownerPage.locator('#model-path')).toBeVisible();
    await expect(ownerPage.locator('button', { hasText: 'Install' })).toBeVisible();
  });

  test('page title is "Mental Models"', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15000 });

    await expect(ownerPage.locator('h1')).toContainText('Mental Models');
  });
});
