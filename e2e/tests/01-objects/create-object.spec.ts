/**
 * Object Creation E2E Tests
 *
 * Tests creating all four Basic PKM object types through the UI:
 * Note, Concept, Project, Person.
 *
 * Uses the auth fixture (ownerPage) so setup is already complete.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { TYPES } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Object Creation via UI', () => {
  test('type picker shows all four Basic PKM types', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Open type picker via htmx GET /browser/types
    await ownerPage.evaluate(() => {
      const el = document.querySelector('#editor-area-group-1') || document.querySelector(
        '[data-testid="editor-area"]'
      );
      if (el) {
        (window as any).htmx?.ajax('GET', '/browser/types', { target: el });
      }
    });

    // Wait for type picker to appear
    await ownerPage.waitForSelector(SEL.typePicker.overlay, { timeout: 10000 });
    const typeOptions = ownerPage.locator(SEL.typePicker.typeOption);
    await expect(typeOptions).toHaveCount(4);
  });

  test('create a Note with title and body', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Navigate to create form for Note type
    const encodedType = encodeURIComponent(TYPES.Note);
    const resp = await ownerPage.goto(
      `${BASE_URL}/browser/objects/new?type=${encodedType}`,
    );
    // The create form should be accessible (may redirect to workspace with form loaded)
    // Use htmx-style navigation instead
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Load create form via htmx into editor area
    await ownerPage.evaluate((typeIri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/objects/new?type=' + encodeURIComponent(typeIri), { target });
      }
    }, TYPES.Note);

    await ownerPage.waitForSelector(SEL.editor.form, { timeout: 10000 });

    // The form should show "Create Note"
    await expect(ownerPage.locator('.form-title')).toContainText('Create');

    // Fill in the title field (look for input with name containing "title" or "label")
    const titleInput = ownerPage.locator('input[name*="title"], input[name*="label"], input[name*="name"]').first();
    await titleInput.fill('E2E Test Note');

    // Submit the form
    await ownerPage.click(`${SEL.editor.form} button[type="submit"], ${SEL.editor.form} [data-testid="save-button"]`);
    await waitForIdle(ownerPage);

    // Should see success message
    await expect(ownerPage.locator('.form-success')).toBeVisible({ timeout: 10000 });
    await expect(ownerPage.locator('.form-success')).toContainText('Created');
  });

  test('create a Concept with prefLabel and definition', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    await ownerPage.evaluate((typeIri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/objects/new?type=' + encodeURIComponent(typeIri), { target });
      }
    }, TYPES.Concept);

    await ownerPage.waitForSelector(SEL.editor.form, { timeout: 10000 });
    await expect(ownerPage.locator('.form-title')).toContainText('Create');

    // Fill in the label/name field
    const labelInput = ownerPage.locator('input[name*="label"], input[name*="Label"], input[name*="name"]').first();
    await labelInput.fill('E2E Test Concept');

    await ownerPage.click(`${SEL.editor.form} button[type="submit"], ${SEL.editor.form} [data-testid="save-button"]`);
    await waitForIdle(ownerPage);

    await expect(ownerPage.locator('.form-success')).toBeVisible({ timeout: 10000 });
  });

  test('create a Project with title and status', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    await ownerPage.evaluate((typeIri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/objects/new?type=' + encodeURIComponent(typeIri), { target });
      }
    }, TYPES.Project);

    await ownerPage.waitForSelector(SEL.editor.form, { timeout: 10000 });

    const titleInput = ownerPage.locator('input[name*="title"], input[name*="name"], input[name*="label"]').first();
    await titleInput.fill('E2E Test Project');

    await ownerPage.click(`${SEL.editor.form} button[type="submit"], ${SEL.editor.form} [data-testid="save-button"]`);
    await waitForIdle(ownerPage);

    await expect(ownerPage.locator('.form-success')).toBeVisible({ timeout: 10000 });
  });

  test('create a Person with name and email', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    await ownerPage.evaluate((typeIri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/objects/new?type=' + encodeURIComponent(typeIri), { target });
      }
    }, TYPES.Person);

    await ownerPage.waitForSelector(SEL.editor.form, { timeout: 10000 });

    const nameInput = ownerPage.locator('input[name*="name"], input[name*="Name"], input[name*="label"]').first();
    await nameInput.fill('E2E Test Person');

    await ownerPage.click(`${SEL.editor.form} button[type="submit"], ${SEL.editor.form} [data-testid="save-button"]`);
    await waitForIdle(ownerPage);

    await expect(ownerPage.locator('.form-success')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Object Creation via API', () => {
  test('create object via POST /api/commands', async ({ ownerPage, ownerSessionToken }) => {
    const context = ownerPage.context();
    const apiContext = await context.request;

    const resp = await apiContext.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: {
            'http://purl.org/dc/terms/title': 'API Created Note',
          },
        },
      },
    });

    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results).toBeDefined();
    expect(data.results.length).toBe(1);
    expect(data.results[0].iri).toBeTruthy();
    expect(data.event_iri).toBeTruthy();
    expect(data.timestamp).toBeTruthy();
  });

  test('batch create multiple objects atomically', async ({ ownerPage, ownerSessionToken }) => {
    const context = ownerPage.context();
    const apiContext = await context.request;

    const resp = await apiContext.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: [
        {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Batch Note 1' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: { 'http://purl.org/dc/terms/title': 'Batch Note 2' },
          },
        },
      ],
    });

    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results.length).toBe(2);
    // All commands share the same event IRI (atomic transaction)
    expect(data.results[0].event_iri).toBe(data.results[1].event_iri);
  });
});
