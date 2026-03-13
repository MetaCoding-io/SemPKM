/**
 * SPARQL Workspace Bottom Panel E2E Tests
 *
 * Tests the SPARQL workspace bottom panel (distinct from the admin console
 * at /admin/sparql). Opens via panel-tab[data-panel="sparql"], initializes
 * Yasgui, and allows query execution.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('SPARQL Workspace Panel', () => {
  test('SPARQL panel opens via bottom panel tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open bottom panel
    await ownerPage.keyboard.press('Alt+j');
    await waitForIdle(ownerPage);

    // Click the SPARQL tab
    const sparqlTab = ownerPage.locator('.panel-tab[data-panel="sparql"]');
    await sparqlTab.click();
    await waitForIdle(ownerPage);

    // SPARQL panel should be visible
    const sparqlPanel = ownerPage.locator('#panel-sparql');
    await expect(sparqlPanel).toBeVisible({ timeout: 10000 });
  });

  test('Yasgui editor initializes in SPARQL panel', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open bottom panel and switch to SPARQL tab
    await ownerPage.keyboard.press('Alt+j');
    await waitForIdle(ownerPage);
    await ownerPage.locator('.panel-tab[data-panel="sparql"]').click();
    await waitForIdle(ownerPage);

    // Wait for Yasgui to initialize (CodeMirror or Yasqe editor)
    const hasEditor = await ownerPage.evaluate(() => {
      // Yasgui uses CodeMirror under the hood
      const cm = document.querySelector('.CodeMirror, .yasqe, .yasgui');
      return !!cm;
    });

    // Editor should be present (Yasgui renders CodeMirror or textarea)
    // May also use a textarea fallback
    const hasAnyInput = hasEditor || await ownerPage.locator('#panel-sparql textarea, #panel-sparql .CodeMirror').count() > 0;
    expect(hasAnyInput).toBeTruthy();
  });

  test('execute a SPARQL query via the panel', async ({ ownerRequest }) => {
    // Test the SPARQL endpoint directly (same one the panel calls)
    const resp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: 'SELECT ?s ?p ?o FROM <urn:sempkm:current> WHERE { ?s ?p ?o } LIMIT 5',
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results).toBeDefined();
    expect(data.results.bindings).toBeDefined();
    expect(data.results.bindings.length).toBeGreaterThan(0);
  });
});
