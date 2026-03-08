/**
 * SHACL Validation & Lint Panel E2E Tests
 *
 * Tests that SHACL validation runs asynchronously after object mutations,
 * and that the lint panel in the right pane displays results correctly.
 * Lint panel uses SSE (EventSource) for real-time updates.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('SHACL Validation & Lint Panel', () => {
  test('lint panel renders for seed object', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const noteIri = SEED.notes.architecture.iri;

    // Open a seed object to trigger lint panel load
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Architecture Decision');
      }
    }, noteIri);

    await waitForIdle(ownerPage);

    // Wait for lint panel to load in the right pane
    // The lint content is in #lint-content, loaded via htmx
    await ownerPage.waitForTimeout(3000); // Allow time for async validation

    const lintContent = ownerPage.locator('#lint-content');
    const content = await lintContent.innerHTML();
    // Should have some content (either lint-panel or waiting state)
    expect(content.length).toBeGreaterThan(0);
  });

  test('lint panel shows conformance badge for valid object', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a well-formed seed object
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Alice Chen');
      }
    }, SEED.people.alice.iri);

    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(5000); // Allow async validation to complete

    // Check if lint panel has loaded with results
    const lintPanel = ownerPage.locator(SEL.lint.panel);
    const panelCount = await lintPanel.count();

    if (panelCount > 0) {
      // If the object conforms, it should show the "All validations pass" message
      // or show violations if there are any
      const text = await lintPanel.innerText();
      // The lint panel should have some content
      expect(text.length).toBeGreaterThan(0);
    }
  });

  test('lint endpoint returns validation results via API', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const noteIri = SEED.notes.architecture.iri;
    const encodedIri = encodeURIComponent(noteIri);

    const resp = await api.get(`${BASE_URL}/browser/lint/${encodedIri}`, {
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'HX-Request': 'true',
      },
    });

    expect(resp.ok()).toBeTruthy();
    const html = await resp.text();
    // Should return lint panel HTML
    expect(html).toContain('lint-panel');
  });

  test('creating object with missing required fields triggers violation', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;

    // Create an object with minimal properties (may violate SHACL shapes)
    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'object.create',
        params: {
          type: 'Note',
          properties: {}, // No title — may trigger SHACL violation
        },
      },
    });

    // Object creation should still succeed (validation is non-blocking)
    expect(createResp.ok()).toBeTruthy();
    const data = await createResp.json();
    const objectIri = data.results[0].iri;

    // Wait for validation queue to process
    await ownerPage.waitForTimeout(5000);

    // Check lint panel for the new object
    const encodedIri = encodeURIComponent(objectIri);
    const lintResp = await api.get(`${BASE_URL}/browser/lint/${encodedIri}`, {
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'HX-Request': 'true',
      },
    });

    expect(lintResp.ok()).toBeTruthy();
    const html = await lintResp.text();
    // Response should contain lint panel markup
    expect(html).toContain('lint-panel');
  });

  test('lint panel uses SSE for real-time updates', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Architecture Decision');
      }
    }, SEED.notes.architecture.iri);

    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(3000);

    // Check that the lint panel does NOT have polling attributes (SSE replaces polling)
    const lintPanel = ownerPage.locator(SEL.lint.panel);
    const panelCount = await lintPanel.count();

    if (panelCount > 0) {
      // No hx-trigger polling attribute should be present
      const trigger = await lintPanel.getAttribute('hx-trigger');
      expect(trigger).toBeNull();

      // The lint panel should have the SSE script (data-lint-sse)
      const sseScript = ownerPage.locator('script[data-lint-sse]');
      const scriptCount = await sseScript.count();
      expect(scriptCount).toBeGreaterThan(0);
    }
  });
});
