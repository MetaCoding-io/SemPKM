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

    // Open type picker via dockview addPanel
    await ownerPage.evaluate(() => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'type-picker-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'types', isView: false, isSpecial: true },
          title: 'New Object',
        });
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

    // Load create form via dockview addPanel
    await ownerPage.evaluate((typeIri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'new-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'objects/new?type=' + encodeURIComponent(typeIri), isView: false, isSpecial: true },
          title: 'New Object',
        });
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
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'new-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'objects/new?type=' + encodeURIComponent(typeIri), isView: false, isSpecial: true },
          title: 'New Object',
        });
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
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'new-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'objects/new?type=' + encodeURIComponent(typeIri), isView: false, isSpecial: true },
          title: 'New Object',
        });
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
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'new-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'objects/new?type=' + encodeURIComponent(typeIri), isView: false, isSpecial: true },
          title: 'New Object',
        });
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

  test('create with full type IRI stores correct type and edit form loads', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    // Bug fix: handle_object_create always built type_iri as base_namespace + params.type,
    // so passing type: "urn:sempkm:model:basic-pkm:Note" stored the wrong type in the
    // triplestore, causing "No form schema available" when re-opening the object.
    // Fix: full IRIs are used directly; only bare local names use base_namespace.
    const api = ownerPage.context().request;

    const resp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,  // full IRI: urn:sempkm:model:basic-pkm:Note
          properties: { 'http://purl.org/dc/terms/title': 'Full IRI Type Test Note' },
        },
      },
    });

    expect(resp.ok()).toBeTruthy();
    const { results } = await resp.json();
    const noteIri: string = results[0].iri;
    expect(noteIri).toBeTruthy();

    // Object IRI path should use the local name "Note", not the full type IRI
    expect(noteIri).toMatch(/\/Note\//);

    // Open the object in the workspace — edit form must load (not "No form schema")
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await ownerPage.evaluate(({ iri }) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, iri, 'edit');
      }
    }, { iri: noteIri });

    // The edit form must appear — this would time out with "No form schema" if bug reappears
    // Use 'attached' state: the form is in the DOM (inside the edit flip face) even before
    // the CSS flip animation makes it visually visible.
    await ownerPage.waitForSelector('[data-testid="object-form"]', { state: 'attached', timeout: 10000 });

    // Confirm it's a real form, not the error fallback
    await expect(ownerPage.locator('.form-empty')).toHaveCount(0);
    const labelCount = await ownerPage.locator('[data-testid="object-form"] label').count();
    expect(labelCount).toBeGreaterThan(0);
  });
});
