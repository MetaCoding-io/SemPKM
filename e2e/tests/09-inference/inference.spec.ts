/**
 * OWL 2 RL Inference E2E Tests
 *
 * Tests the inference pipeline UI: panel loads, controls work, filters
 * exist, refresh triggers a run, and the API correctly processes
 * inference requests.
 *
 * Note: The basic-pkm seed data already includes both sides of inverseOf
 * relationships, so owl:inverseOf entailment produces no NEW triples with
 * current seed data. These tests focus on infrastructure verification
 * (panel rendering, filter controls, API endpoints) rather than specific
 * triple content.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { openObjectTab } from '../../helpers/dockview';
import { Page } from '@playwright/test';

/**
 * Open the bottom panel and switch to a specific tab.
 * Ensures the panel is visible before clicking the tab.
 */
async function openBottomPanelTab(page: Page, tabName: string) {
  await page.evaluate(() => {
    const panel = document.getElementById('bottom-panel');
    if (!panel) return;
    const h = panel.style.height;
    if (!h || h === '0px' || h === '0') {
      if (typeof (window as any).toggleBottomPanel === 'function') {
        (window as any).toggleBottomPanel();
      }
    }
  });
  await page.waitForTimeout(500);
  await page.click(`.panel-tab[data-panel="${tabName}"]`);
  await waitForIdle(page);
}

test.describe('Inference', () => {
  test('inference panel loads in bottom panel', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'inference');

    // The inference panel pane should be active
    const pane = ownerPage.locator('#panel-inference');
    await expect(pane).toHaveClass(/active/);

    // Wait for the inference panel content to load (htmx revealed)
    const panel = ownerPage.locator('.inference-panel');
    await expect(panel).toBeVisible({ timeout: 10000 });

    // Should have refresh button and filter controls
    await expect(ownerPage.locator('.inference-refresh-btn')).toBeVisible();
    await expect(ownerPage.locator('.inference-filter-type')).toBeVisible();
    await expect(ownerPage.locator('.inference-filter-status')).toBeVisible();
  });

  test('inference API run endpoint works', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;

    // Trigger inference via API (with default config: owl:inverseOf + sh:rule)
    const inferResp = await api.post(`${BASE_URL}/api/inference/run`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    expect(inferResp.ok()).toBeTruthy();
    const inferData = await inferResp.json();

    // Verify response structure
    expect(inferData).toHaveProperty('total_inferred');
    expect(inferData).toHaveProperty('run_timestamp');
    expect(inferData).toHaveProperty('by_entailment_type');

    // With seed data where both inverse directions already exist,
    // total_inferred may be 0 -- that's correct behavior
    expect(inferData.total_inferred).toBeGreaterThanOrEqual(0);
  });

  test('inference API triples endpoint returns results', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;

    // Get inferred triples via API
    const triplesResp = await api.get(`${BASE_URL}/api/inference/triples`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    expect(triplesResp.ok()).toBeTruthy();
    const triples = await triplesResp.json();

    // Response should be an array (may be empty if no triples were inferred)
    expect(Array.isArray(triples)).toBeTruthy();
  });

  test('inference panel filter controls are functional', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'inference');
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify all filter controls exist and are interactive
    const filterType = ownerPage.locator('.inference-filter-type');
    await expect(filterType).toBeVisible();

    const filterStatus = ownerPage.locator('.inference-filter-status');
    await expect(filterStatus).toBeVisible();

    // Verify entailment type filter has expected options
    const typeOptions = await filterType.locator('option').allInnerTexts();
    expect(typeOptions).toContain('All types');
    expect(typeOptions).toContain('owl:inverseOf');
    expect(typeOptions).toContain('sh:rule');

    // Verify status filter has expected options
    const statusOptions = await filterStatus.locator('option').allInnerTexts();
    expect(statusOptions).toContain('All statuses');
    expect(statusOptions).toContain('Active');
    expect(statusOptions).toContain('Dismissed');

    // Select a filter option -- should trigger htmx request
    await filterType.selectOption('owl:inverseOf');
    await waitForIdle(ownerPage);

    // Reset filter
    await filterType.selectOption('');
    await waitForIdle(ownerPage);

    // Select status filter
    await filterStatus.selectOption('active');
    await waitForIdle(ownerPage);

    // Reset
    await filterStatus.selectOption('');
    await waitForIdle(ownerPage);
  });

  test('inference refresh button triggers new run via htmx', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openBottomPanelTab(ownerPage, 'inference');
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // The refresh button should be visible and have the correct htmx attributes
    const refreshBtn = ownerPage.locator('.inference-refresh-btn');
    await expect(refreshBtn).toBeVisible();

    // Verify htmx attributes for the refresh button
    const hxPost = await refreshBtn.getAttribute('hx-post');
    expect(hxPost).toBe('/api/inference/run');

    const hxTarget = await refreshBtn.getAttribute('hx-target');
    expect(hxTarget).toBe('#inference-results');

    // Click refresh -- this triggers inference run via htmx
    await refreshBtn.click();

    // Wait for the request to complete
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // The inference results area should still exist (htmx swaps innerHTML)
    const results = ownerPage.locator('#inference-results');
    await expect(results).toBeAttached();
  });

  test('create one-sided relationship and verify inference materializes inverse', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // 1. Create fresh objects (not seed data — seed has both inverse sides)
    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: [
        {
          command: 'object.create',
          params: {
            type: 'urn:sempkm:model:basic-pkm:Project',
            properties: { 'http://purl.org/dc/terms/title': 'Inference Test Project' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: 'urn:sempkm:model:basic-pkm:Person',
            properties: { 'http://xmlns.com/foaf/0.1/name': 'Inference Test Person' },
          },
        },
      ],
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const projectIri = createData.results[0].iri;
    const personIri = createData.results[1].iri;
    expect(projectIri).toBeTruthy();
    expect(personIri).toBeTruthy();

    // 2. Add one-sided hasParticipant (direct triple, not reified edge)
    const patchResp = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: {
        command: 'object.patch',
        params: {
          iri: projectIri,
          properties: { 'urn:sempkm:model:basic-pkm:hasParticipant': personIri },
        },
      },
    });
    expect(patchResp.ok()).toBeTruthy();

    // 3. Run inference
    const inferResp = await api.post(`${BASE_URL}/api/inference/run`, { headers });
    expect(inferResp.ok()).toBeTruthy();
    const inferData = await inferResp.json();
    expect(inferData.total_inferred).toBeGreaterThan(0);

    // 4. Verify inverse triple was materialized
    const triplesResp = await api.get(`${BASE_URL}/api/inference/triples`, { headers });
    expect(triplesResp.ok()).toBeTruthy();
    const triples = await triplesResp.json();
    expect(Array.isArray(triples)).toBeTruthy();

    const inverseTriple = triples.find(
      (t: any) =>
        t.subject === personIri &&
        t.predicate.includes('participatesIn') &&
        t.object === projectIri
    );
    expect(inverseTriple).toBeTruthy();
  });

  test('inference config API returns entailment types', async ({ ownerPage, ownerSessionToken }) => {
    const api = ownerPage.context().request;

    // Get inference config
    const configResp = await api.get(`${BASE_URL}/api/inference/config`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    expect(configResp.ok()).toBeTruthy();
    const config = await configResp.json();

    // Verify config structure
    expect(config).toHaveProperty('entailment_types');
    expect(config).toHaveProperty('config');
    expect(config.entailment_types).toContain('owl:inverseOf');
    expect(config.entailment_types).toContain('sh:rule');
    expect(config.entailment_types).toContain('rdfs:domain/rdfs:range');

    // owl:inverseOf should be enabled by default
    expect(config.config['owl:inverseOf']).toBe(true);
  });
});
