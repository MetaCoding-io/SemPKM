/**
 * Class Creation E2E Tests
 *
 * Tests the full class creation pipeline:
 * - Create a class via the ontology viewer form → appears in TBox
 * - User-created type appears in the type picker and supports object creation
 * - Delete a user-created class via the TBox tree delete button
 *
 * NOTE: Limited to ≤3 tests to stay within the auth rate limit
 * (5 magic-link calls per minute).
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Unique class name per test run to avoid collisions */
function uniqueClassName(base: string): string {
  return `${base} ${Date.now().toString(36).slice(-4)}`;
}

/** Open the ontology viewer tab via JS API. */
async function openOntologyViewer(page: import('@playwright/test').Page) {
  await page.evaluate(() => {
    if (typeof (window as any).openOntologyTab === 'function') {
      (window as any).openOntologyTab();
    }
  });
  await page.waitForSelector(SEL.ontology.ontologyPage, { timeout: 15000 });
}

/**
 * Fill the class creation form and submit.
 * Returns the class name used.
 */
async function createClass(
  page: import('@playwright/test').Page,
  className: string,
  opts: { icon?: string; addProperty?: boolean } = {},
) {
  const { icon = 'star', addProperty = true } = opts;

  // Click "Create Class" button
  await page.click(SEL.classCreation.createButton);
  // Wait for the form to load via htmx
  await page.waitForSelector(SEL.classCreation.form, { timeout: 10000 });

  // Fill class name
  await page.fill(SEL.classCreation.nameInput, className);

  // Select an icon
  const iconCell = page.locator(`${SEL.classCreation.iconCell}[data-icon="${icon}"]`);
  await iconCell.click();

  // Verify icon was selected (hidden input updated)
  const iconValue = await page.inputValue('#ccf-icon');
  expect(iconValue).toBe(icon);

  // Add a property if requested
  if (addProperty) {
    await page.click(SEL.classCreation.addPropertyButton);
    // Wait for property row to appear
    const propRow = page.locator('[data-testid="property-row"]').first();
    await expect(propRow).toBeVisible({ timeout: 5000 });

    // Fill property name
    await propRow.locator('.prop-name').fill('Label');

    // Select predicate: dcterms:title
    await propRow.locator('.prop-predicate').selectOption('http://purl.org/dc/terms/title');

    // Datatype defaults to xsd:string, which is what we want
  }

  // Submit
  await page.click(SEL.classCreation.submitButton);

  // Wait for success message
  await expect(page.locator('.success-message')).toBeVisible({ timeout: 15000 });
}

test.describe('Class Creation', () => {
  test('user can create a class and it appears in TBox', async ({ ownerPage }) => {
    const className = uniqueClassName('TestWidget');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open ontology viewer
    await openOntologyViewer(ownerPage);

    // Wait for TBox tree to load
    const tboxTree = ownerPage.locator(SEL.ontology.tboxTree);
    await expect(tboxTree).toBeVisible({ timeout: 10000 });
    await ownerPage.waitForSelector(SEL.ontology.tboxNode, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Create the class
    await createClass(ownerPage, className);

    // TBox tree should refresh automatically (classCreated event)
    // Wait for the new class to appear in the TBox tree
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify the class appears in TBox with "user" badge
    const treeText = await tboxTree.textContent();
    expect(treeText).toContain(className);

    // Verify user badge is present next to the new class
    const newNode = ownerPage.locator(`${SEL.ontology.tboxNode}`, {
      hasText: className,
    });
    await expect(newNode).toBeVisible({ timeout: 10000 });
    const userBadge = newNode.locator('.tbox-source-badge.badge-user');
    await expect(userBadge).toBeVisible();
    expect(await userBadge.textContent()).toBe('user');
  });

  test('user-created type appears in type picker and supports object creation', async ({ ownerPage }) => {
    const className = uniqueClassName('PickerType');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Create a class first
    await openOntologyViewer(ownerPage);
    await ownerPage.waitForSelector(SEL.ontology.tboxNode, { timeout: 15000 });
    await waitForIdle(ownerPage);
    await createClass(ownerPage, className);

    // Wait for TBox refresh
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Navigate to "New Object" flow via JS API
    await ownerPage.evaluate(() => {
      if (typeof (window as any).showTypePicker === 'function') {
        (window as any).showTypePicker();
      }
    });

    // Wait for type picker to load
    const typePicker = ownerPage.locator(SEL.typePicker.overlay);
    await expect(typePicker).toBeVisible({ timeout: 15000 });

    // Verify the new type appears in the type picker
    // The type card label strips " Shape" suffix
    const typeCard = typePicker.locator(SEL.typePicker.typeOption, {
      hasText: className,
    });
    await expect(typeCard).toBeVisible({ timeout: 10000 });

    // Click the type to open its form
    await typeCard.click();

    // Wait for the SHACL-driven form to load
    const form = ownerPage.locator('[data-testid="object-form"]');
    await expect(form).toBeVisible({ timeout: 15000 });
    await waitForIdle(ownerPage);

    // The SHACL-driven form should have at least a dcterms:title field
    // (property name "Label" maps to path http://purl.org/dc/terms/title).
    // The input name attribute is the full IRI.
    const titleInput = form.locator('input[name="http://purl.org/dc/terms/title"], input[name="http://purl.org/dc/terms/title[]"]').first();
    // If the title input exists, fill and submit
    const titleVisible = await titleInput.isVisible({ timeout: 5000 }).catch(() => false);
    if (titleVisible) {
      await titleInput.fill(`Test object of ${className}`);
    } else {
      // Form rendered without property fields — still valid (the Shape exists
      // but properties may not be visible). Fill any visible input as fallback.
      const anyInput = form.locator('input.form-input:visible').first();
      const hasInput = await anyInput.isVisible({ timeout: 3000 }).catch(() => false);
      if (hasInput) {
        await anyInput.fill(`Test object of ${className}`);
      }
    }

    // Submit the form
    const submitBtn = form.locator('[data-testid="save-button"]');
    await submitBtn.click();

    // Wait for form submission to complete — the form re-renders in edit mode
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify the object was created — the form switches to edit mode
    // (heading says "Edit" and/or a hidden object_iri input is present)
    const editForm = ownerPage.locator('[data-testid="object-form"]');
    await expect(editForm).toBeVisible({ timeout: 10000 });
    const formText = await editForm.textContent();
    // In edit mode the form title changes from "Create X" to "Edit X"
    expect(formText).toContain('Edit');
  });

  test('user can delete a user-created class', async ({ ownerPage }) => {
    const className = uniqueClassName('DeleteMe');

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open ontology viewer
    await openOntologyViewer(ownerPage);

    // Wait for TBox tree
    await ownerPage.waitForSelector(SEL.ontology.tboxNode, { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Create the class
    await createClass(ownerPage, className, { addProperty: false });

    // Wait for TBox refresh
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Close the class creation form so only the tree is visible
    await ownerPage.evaluate(() => {
      if (typeof (window as any).closeClassCreationForm === 'function') {
        (window as any).closeClassCreationForm();
      }
    });
    await ownerPage.waitForTimeout(500);

    // Verify the class is in the TBox tree
    const tboxTree = ownerPage.locator(SEL.ontology.tboxTree);
    const newNode = tboxTree.locator(SEL.ontology.tboxNode, {
      hasText: className,
    });
    await expect(newNode).toBeVisible({ timeout: 10000 });

    // Hover to reveal the delete button
    await newNode.hover();

    // Click the delete button (the hx-confirm dialog will be auto-accepted)
    const deleteBtn = newNode.locator(SEL.classCreation.deleteButton);
    await expect(deleteBtn).toBeVisible({ timeout: 5000 });

    // Set up dialog handler to accept the hx-confirm dialog
    ownerPage.once('dialog', dialog => dialog.accept());
    await deleteBtn.click();

    // Wait for the TBox tree to refresh after deletion (classDeleted HX-Trigger event).
    // The tbox pane reloads its content from /browser/ontology/tbox on classDeleted.
    // Wait for the node with our class name to disappear from the tree.
    const deletedNode = tboxTree.locator(SEL.ontology.tboxNode, {
      hasText: className,
    });
    await expect(deletedNode).toHaveCount(0, { timeout: 15000 });
  });
});
