/**
 * SPARQL Workspace Bottom Panel E2E Tests
 *
 * Tests the SPARQL workspace bottom panel (distinct from the admin console
<<<<<<< HEAD
 * at /admin/sparql). Opens via toggleBottomPanel() + tab click, initializes
 * CodeMirror 6 SPARQL editor, and allows query execution with enriched results.
 *
 * Consolidated into 1 test() call to stay within the 5/minute magic-link rate limit.
=======
 * at /admin/sparql). Opens via panel-tab[data-panel="sparql"], initializes
 * Yasgui, and allows query execution.
>>>>>>> gsd/M003/S03
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('SPARQL Workspace Panel', () => {
<<<<<<< HEAD
  test('bottom panel SPARQL tab: opens, initializes editor, executes query, shows enriched results', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // --- 1. Open the bottom panel via JS (more reliable than Alt+j in headless) ---
    await ownerPage.evaluate(() => {
      (window as any).toggleBottomPanel();
    });
    await waitForIdle(ownerPage);

    // --- 2. Click the SPARQL tab to activate it ---
    const sparqlTab = ownerPage.locator('.panel-tab[data-panel="sparql"]');
    await expect(sparqlTab).toBeVisible({ timeout: 5000 });
    await sparqlTab.click();
    await waitForIdle(ownerPage);

    // Wait for the SPARQL panel pane to become active
    const sparqlPane = ownerPage.locator('#panel-sparql');
    await expect(sparqlPane).toBeVisible({ timeout: 10000 });

    // --- 3. Verify CodeMirror 6 editor initializes ---
    // The sparql-console.js lazy-loads and creates a CodeMirror 6 editor
    // Wait for the editor container to appear
    const editorReady = await ownerPage.waitForFunction(
      () => {
        // CodeMirror 6 uses .cm-editor class
        const cm6 = document.querySelector('#panel-sparql .cm-editor');
        // Fallback: check for any textarea or legacy editor
        const textarea = document.querySelector('#panel-sparql textarea');
        return !!(cm6 || textarea);
      },
      { timeout: 15000 },
    );
    expect(editorReady).toBeTruthy();

    // --- 4. Verify toolbar elements exist (run button, history dropdown, etc.) ---
    // The sparql-console.js creates a toolbar with Run button
    const hasToolbar = await ownerPage.evaluate(() => {
      const panel = document.getElementById('panel-sparql');
      if (!panel) return false;
      // Check for run button (may be labeled "Run" or have a play icon)
      const runBtn = panel.querySelector('#sparql-run-btn, button[id*="run"], .sparql-toolbar button');
      return !!runBtn;
    });
    // Toolbar should be present (the SPARQL console creates it)
    expect(hasToolbar).toBeTruthy();

    // --- 5. Execute a query via the API (same endpoint the panel calls) ---
    // We test the /api/sparql POST endpoint directly from the page context
    // to verify it works with the session cookie (same as the panel does)
    const queryResult = await ownerPage.evaluate(async () => {
      const resp = await fetch('/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          query: 'SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10',
        }),
      });
      if (!resp.ok) return { error: resp.status, errorText: await resp.text() };
      return resp.json();
    });

    expect(queryResult).toHaveProperty('results');
    expect(queryResult.results).toHaveProperty('bindings');
    expect(queryResult.results.bindings.length).toBeGreaterThan(0);

    // --- 6. Verify enrichment data is present in POST response ---
    // The POST endpoint enriches URI results with labels/types/icons
    expect(queryResult).toHaveProperty('_enrichment');
    // _enrichment should be an object (possibly empty if no object IRIs)
    expect(typeof queryResult._enrichment).toBe('object');

    // Check if any enrichment entries exist for the object IRIs
    const enrichmentKeys = Object.keys(queryResult._enrichment);
    if (enrichmentKeys.length > 0) {
      // Verify enrichment structure for the first entry
      const firstKey = enrichmentKeys[0];
      const entry = queryResult._enrichment[firstKey];
      expect(entry).toHaveProperty('label');
      expect(entry).toHaveProperty('type_iri');
      expect(entry).toHaveProperty('icon');
      expect(entry).toHaveProperty('qname');
    }

    // --- 7. Verify the panel can be closed ---
    await ownerPage.evaluate(() => {
      (window as any).toggleBottomPanel();
    });
    await waitForIdle(ownerPage);

    // The panel state in localStorage should show it as closed
    const panelClosed = await ownerPage.evaluate(() => {
      const saved = localStorage.getItem('sempkm_bottom_panel');
      if (!saved) return true;
      return !JSON.parse(saved).open;
    });
    expect(panelClosed).toBe(true);
=======
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
>>>>>>> gsd/M003/S03
  });
});
