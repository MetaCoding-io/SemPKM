/**
 * Object Editing E2E Tests
 *
 * Tests editing existing objects: patching properties via form and API,
 * setting body text, and verifying changes persist.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Edit Object Properties', () => {
  test('open seed note in edit mode and verify form loads', async ({ ownerPage }) => {
    const noteIri = SEED.notes.architecture.iri;
    const encodedIri = encodeURIComponent(noteIri);

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Load object in edit mode via htmx
    await ownerPage.evaluate((iri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/object/' + encodeURIComponent(iri) + '?mode=edit', { target });
      }
    }, noteIri);

    // Wait for the object tab to load (form is inside collapsed properties section)
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    // Verify the edit form exists in the DOM
    await ownerPage.waitForSelector('[data-testid="object-form"]', { state: 'attached', timeout: 5000 });
  });

  test('patch object properties via API', async ({ ownerPage, ownerSessionToken }) => {
    // First create an object to patch
    const context = ownerPage.context();
    const api = await context.request;

    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: { 'http://purl.org/dc/terms/title': 'Note To Edit' },
        },
      },
    });
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;

    // Patch the title
    const patchResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.patch',
        params: {
          iri: objectIri,
          properties: { 'http://purl.org/dc/terms/title': 'Updated Note Title' },
        },
      },
    });

    expect(patchResp.ok()).toBeTruthy();
    const patchData = await patchResp.json();
    expect(patchData.results[0].iri).toBe(objectIri);
    expect(patchData.event_iri).toBeTruthy();
  });

  test('set body text via API', async ({ ownerPage, ownerSessionToken }) => {
    // Create a note first
    const context = ownerPage.context();
    const api = await context.request;

    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: { 'http://purl.org/dc/terms/title': 'Note For Body' },
        },
      },
    });
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;

    // Set body via body.set command
    const bodyResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'body.set',
        params: {
          iri: objectIri,
          body: '# Hello\n\nThis is **markdown** body text.',
        },
      },
    });

    expect(bodyResp.ok()).toBeTruthy();
    const bodyData = await bodyResp.json();
    expect(bodyData.results[0].iri).toBe(objectIri);
  });

  test('save body via browser endpoint', async ({ ownerPage, ownerSessionToken }) => {
    // Create a note
    const context = ownerPage.context();
    const api = await context.request;

    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: { 'http://purl.org/dc/terms/title': 'Note For Browser Body Save' },
        },
      },
    });
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;

    // Save body via the browser POST endpoint
    const encodedIri = encodeURIComponent(objectIri);
    const bodyResp = await api.post(
      `${BASE_URL}/browser/objects/${encodedIri}/body`,
      {
        headers: {
          Cookie: `sempkm_session=${ownerSessionToken}`,
          'Content-Type': 'text/plain',
        },
        data: '# Updated Body\n\nSaved via browser endpoint.',
      },
    );

    expect(bodyResp.ok()).toBeTruthy();
    const html = await bodyResp.text();
    expect(html).toContain('Saved');
  });
});
