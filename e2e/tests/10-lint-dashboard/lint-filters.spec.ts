/**
 * Lint Filter System E2E Tests
 *
 * Exercises the full M030 acceptance criteria against the Docker test stack:
 * 1. Pipeline fix (S01): SHACL-AF rules fire with advanced=True
 * 2. Data quality rules (S02): Warnings/infos appear for real objects
 * 3. Lint filter system (S03): Suppress, dismiss, presets, settings management
 *
 * Tests are serial — each builds on state created by the previous one.
 * API-driven arrangement with selective browser verification for UI outcomes.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

/** Open the bottom panel and switch to a specific tab. */
async function openBottomPanelTab(page: Page, tabName: string) {
  await page.evaluate(() => {
    const panel = document.getElementById('bottom-panel');
    if (!panel) return;
    const h = panel.style.height;
    if (!h || h === '0px' || h === '0') {
      if (typeof (window as any).SemPKM.toggleBottomPanel === 'function') {
        (window as any).SemPKM.toggleBottomPanel();
      }
    }
  });
  await page.waitForTimeout(500);
  await page.click(`.panel-tab[data-panel="${tabName}"]`);
  await waitForIdle(page);
}

// Shared state across serial tests
let createdNoteNoBodyIri: string;
let createdNoteCommaTagsIri: string;
const EMPTY_BODY_SHAPE = 'urn:sempkm:model:basic-pkm:EmptyBodyValidationShape';
const COMMA_TAGS_SHAPE = 'urn:sempkm:model:basic-pkm:CommaInTagsValidationShape';
let presetId: string;

test.describe('Lint Filter System', () => {

  test('setup: clear stale filters from prior test runs', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Clear any stale suppressions/dismissals from previous incomplete runs
    await api.delete(`${BASE_URL}/api/lint/suppressions`, { headers });
    await api.delete(`${BASE_URL}/api/lint/dismissals`, { headers });

    // Delete any stale presets
    const presetsResp = await api.get(`${BASE_URL}/api/lint/presets`, { headers });
    if (presetsResp.ok()) {
      const presets = await presetsResp.json();
      for (const p of presets) {
        await api.delete(`${BASE_URL}/api/lint/presets/${p.id}`, { headers });
      }
    }
  });

  test('create objects that trigger data quality rules and verify lint results', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    test.setTimeout(90000); // Extended timeout for validation polling
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Create a Note with title but NO body → triggers EmptyBodyValidationShape (Info)
    const resp1 = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: {
            'dcterms:title': 'Lint Test Note - No Body',
          },
        },
      },
    });
    expect(resp1.ok()).toBeTruthy();
    const result1 = await resp1.json();
    createdNoteNoBodyIri = result1.results?.[0]?.iri;
    expect(createdNoteNoBodyIri).toBeTruthy();

    // Create a Note with a comma-in-tags → triggers CommaInTagsValidationShape (Warning)
    const resp2 = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: {
            'dcterms:title': 'Lint Test Note - Comma Tags',
            'urn:sempkm:model:basic-pkm:tags': 'tag-one, tag-two',
          },
        },
      },
    });
    expect(resp2.ok()).toBeTruthy();
    const result2 = await resp2.json();
    createdNoteCommaTagsIri = result2.results?.[0]?.iri;
    expect(createdNoteCommaTagsIri).toBeTruthy();

    // Wait for async validation pipeline — poll until CommaInTags results appear
    // Each object creation triggers a separate validation run (~5s each).
    // Poll for up to 30s to allow both validations to complete.
    let lintData: any;
    let commaTagResults: Array<{ focus_node: string; source_shape: string | null; severity: string }> = [];
    for (let attempt = 0; attempt < 6; attempt++) {
      await ownerPage.waitForTimeout(5000);
      const lintResp = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
        headers,
      });
      if (!lintResp.ok()) {
        const errText = await lintResp.text();
        console.error(`lint/results failed (${lintResp.status()}): ${errText.slice(0, 500)}`);
        continue;
      }
      lintData = await lintResp.json();
      if (lintData.total === 0) continue;

      commaTagResults = lintData.results.filter(
        (r: any) => r.source_shape === COMMA_TAGS_SHAPE && r.focus_node === createdNoteCommaTagsIri,
      );
      if (commaTagResults.length > 0) break;
    }

    expect(lintData).toBeDefined();
    expect(lintData.total).toBeGreaterThan(0);

    const results: Array<{ focus_node: string; source_shape: string | null; severity: string }> =
      lintData.results;

    // Verify EmptyBody rule fired on the no-body note
    const emptyBodyResults = results.filter(
      (r) => r.source_shape === EMPTY_BODY_SHAPE && r.focus_node === createdNoteNoBodyIri,
    );
    expect(emptyBodyResults.length).toBeGreaterThanOrEqual(1);

    // Verify CommaInTags rule fired on the comma-tags note
    expect(commaTagResults.length).toBeGreaterThanOrEqual(1);
  });

  test('suppress a rule type via API and verify filtering', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Suppress CommaInTags rule
    const suppressResp = await api.post(`${BASE_URL}/api/lint/suppress`, {
      headers,
      data: { rule_source_iri: COMMA_TAGS_SHAPE },
    });
    expect(suppressResp.status()).toBe(201);

    // Verify suppression appears in listing
    const listResp = await api.get(`${BASE_URL}/api/lint/suppressions`, { headers });
    expect(listResp.ok()).toBeTruthy();
    const suppressions = await listResp.json();
    const found = suppressions.find(
      (s: { rule_source_iri: string }) => s.rule_source_iri === COMMA_TAGS_SHAPE,
    );
    expect(found).toBeTruthy();

    // Verify lint results no longer include CommaInTags results
    const lintResp = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
      headers,
    });
    expect(lintResp.ok()).toBeTruthy();
    const lintData = await lintResp.json();
    const commaResults = lintData.results.filter(
      (r: { source_shape: string | null }) => r.source_shape === COMMA_TAGS_SHAPE,
    );
    expect(commaResults.length).toBe(0);

    // EmptyBody results should still be present
    const emptyBodyResults = lintData.results.filter(
      (r: { source_shape: string | null }) => r.source_shape === EMPTY_BODY_SHAPE,
    );
    expect(emptyBodyResults.length).toBeGreaterThanOrEqual(1);

    // Browser verification: open lint dashboard, verify suppressed results absent
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    const dashboard = ownerPage.locator('#lint-dashboard-container').first();
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // CommaInTags specific message should NOT appear in dashboard (rule is suppressed)
    // Note: "Comma" appears in object names, so match the specific rule message
    const commaRuleMsg = ownerPage.locator('.lint-dashboard-row', {
      hasText: 'Tag value contains a comma',
    });
    await expect(commaRuleMsg).toHaveCount(0);
  });

  test('dismiss a specific result via API and verify filtering', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Dismiss EmptyBody rule for the specific no-body note
    const dismissResp = await api.post(`${BASE_URL}/api/lint/dismiss`, {
      headers,
      data: {
        object_iri: createdNoteNoBodyIri,
        rule_source_iri: EMPTY_BODY_SHAPE,
      },
    });
    expect(dismissResp.status()).toBe(201);

    // Verify dismissal appears in listing
    const listResp = await api.get(`${BASE_URL}/api/lint/dismissals`, { headers });
    expect(listResp.ok()).toBeTruthy();
    const dismissals = await listResp.json();
    const found = dismissals.find(
      (d: { object_iri: string; rule_source_iri: string }) =>
        d.object_iri === createdNoteNoBodyIri && d.rule_source_iri === EMPTY_BODY_SHAPE,
    );
    expect(found).toBeTruthy();

    // Verify that specific (object+rule) pair is excluded from lint results
    const lintResp = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
      headers,
    });
    expect(lintResp.ok()).toBeTruthy();
    const lintData = await lintResp.json();
    const dismissed = lintData.results.filter(
      (r: { focus_node: string; source_shape: string | null }) =>
        r.focus_node === createdNoteNoBodyIri && r.source_shape === EMPTY_BODY_SHAPE,
    );
    expect(dismissed.length).toBe(0);

    // Other EmptyBody results (for different objects, e.g. seed data) should remain
    // (We can't guarantee seed data triggers this, so just verify the dismissed one is gone)
  });

  test('preset save, clear, and apply cycle restores filter state', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Current state: CommaInTags suppressed, EmptyBody dismissed for one note
    // Save current suppressions as a preset
    const createPresetResp = await api.post(`${BASE_URL}/api/lint/presets`, {
      headers,
      data: {
        name: 'E2E Test Preset',
        suppressed_rules: [COMMA_TAGS_SHAPE],
      },
    });
    expect(createPresetResp.status()).toBe(201);
    const presetData = await createPresetResp.json();
    presetId = presetData.id;
    expect(presetId).toBeTruthy();
    expect(presetData.name).toBe('E2E Test Preset');
    expect(presetData.suppressed_rules).toContain(COMMA_TAGS_SHAPE);

    // Verify preset appears in listing
    const listPresetsResp = await api.get(`${BASE_URL}/api/lint/presets`, { headers });
    expect(listPresetsResp.ok()).toBeTruthy();
    const presets = await listPresetsResp.json();
    const savedPreset = presets.find((p: { id: string }) => p.id === presetId);
    expect(savedPreset).toBeTruthy();

    // Clear all suppressions
    const clearResp = await api.delete(`${BASE_URL}/api/lint/suppressions`, { headers });
    expect(clearResp.ok()).toBeTruthy();

    // Verify suppressions are now empty
    const emptySuppResp = await api.get(`${BASE_URL}/api/lint/suppressions`, { headers });
    const emptySupp = await emptySuppResp.json();
    expect(emptySupp.length).toBe(0);

    // Verify CommaInTags results are back in lint results (no longer suppressed)
    const lintRespBefore = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
      headers,
    });
    const lintBefore = await lintRespBefore.json();
    const commaResultsBefore = lintBefore.results.filter(
      (r: { source_shape: string | null }) => r.source_shape === COMMA_TAGS_SHAPE,
    );
    expect(commaResultsBefore.length).toBeGreaterThanOrEqual(1);

    // Apply the preset to restore suppressions
    const applyResp = await api.post(`${BASE_URL}/api/lint/presets/${presetId}/apply`, {
      headers,
    });
    expect(applyResp.ok()).toBeTruthy();

    // Verify suppressions are restored
    const restoredSuppResp = await api.get(`${BASE_URL}/api/lint/suppressions`, { headers });
    const restoredSupp = await restoredSuppResp.json();
    expect(restoredSupp.length).toBeGreaterThanOrEqual(1);
    const restoredRule = restoredSupp.find(
      (s: { rule_source_iri: string }) => s.rule_source_iri === COMMA_TAGS_SHAPE,
    );
    expect(restoredRule).toBeTruthy();

    // Verify CommaInTags results are excluded again
    const lintRespAfter = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
      headers,
    });
    const lintAfter = await lintRespAfter.json();
    const commaResultsAfter = lintAfter.results.filter(
      (r: { source_shape: string | null }) => r.source_shape === COMMA_TAGS_SHAPE,
    );
    expect(commaResultsAfter.length).toBe(0);
  });

  test('lint settings management section renders correctly in browser', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    // Navigate to workspace and open lint dashboard
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await openBottomPanelTab(ownerPage, 'lint-dashboard');

    const dashboard = ownerPage.locator('#lint-dashboard-container').first();
    await expect(dashboard).toBeVisible({ timeout: 15000 });
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Click "Manage Filters" link to open settings
    const manageLink = ownerPage.locator('.lint-manage-filters-link');
    await expect(manageLink).toBeVisible({ timeout: 5000 });
    await manageLink.click();
    await ownerPage.waitForTimeout(1500);
    await waitForIdle(ownerPage);

    // Verify lint settings container rendered
    const settings = ownerPage.locator('#lint-settings-container');
    await expect(settings).toBeVisible({ timeout: 10000 });

    // Verify sections exist (use specific headings to avoid strict mode violations)
    await expect(settings.locator('summary:has-text("Suppressions")')).toBeVisible();
    await expect(settings.locator('summary:has-text("Dismissals")')).toBeVisible();
    await expect(settings.locator('summary:has-text("Presets")')).toBeVisible();

    // Verify our suppression is listed (CommaInTags was re-applied via preset)
    const suppressionItems = settings.locator('.lint-settings-section').first().locator('.lint-settings-item');
    await expect(suppressionItems).toHaveCount(1, { timeout: 5000 });

    // Verify our dismissal is listed
    const dismissalSection = settings.locator('.lint-settings-section').nth(1);
    const dismissalItems = dismissalSection.locator('.lint-settings-item');
    await expect(dismissalItems).toHaveCount(1, { timeout: 5000 });

    // Verify our preset is listed
    const presetSection = settings.locator('.lint-settings-section').nth(2);
    await expect(presetSection.locator('text=E2E Test Preset')).toBeVisible();

    // Click "Back to Dashboard" to return
    const backLink = ownerPage.locator('.lint-settings-back');
    await backLink.click();
    await ownerPage.waitForTimeout(1000);
    await waitForIdle(ownerPage);

    // Verify we're back to the dashboard
    await expect(ownerPage.locator('#lint-dashboard-container').first()).toBeVisible({ timeout: 10000 });
  });

  test('cleanup: remove all test filters and presets', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // Clear all suppressions
    const clearSuppResp = await api.delete(`${BASE_URL}/api/lint/suppressions`, { headers });
    expect(clearSuppResp.ok()).toBeTruthy();

    // Clear all dismissals
    const clearDismResp = await api.delete(`${BASE_URL}/api/lint/dismissals`, { headers });
    expect(clearDismResp.ok()).toBeTruthy();

    // Delete the test preset
    if (presetId) {
      const deletePresetResp = await api.delete(`${BASE_URL}/api/lint/presets/${presetId}`, {
        headers,
      });
      expect(deletePresetResp.ok()).toBeTruthy();
    }

    // Verify all filters are cleared
    const suppResp = await api.get(`${BASE_URL}/api/lint/suppressions`, { headers });
    expect((await suppResp.json()).length).toBe(0);

    const dismResp = await api.get(`${BASE_URL}/api/lint/dismissals`, { headers });
    expect((await dismResp.json()).length).toBe(0);

    // Verify lint results now include all rules again (unfiltered)
    const lintResp = await api.get(`${BASE_URL}/api/lint/results?page=1&per_page=200`, {
      headers,
    });
    expect(lintResp.ok()).toBeTruthy();
    const lintData = await lintResp.json();
    // Both test objects should produce results now
    const commaResults = lintData.results.filter(
      (r: { source_shape: string | null }) => r.source_shape === COMMA_TAGS_SHAPE,
    );
    expect(commaResults.length).toBeGreaterThanOrEqual(1);
  });
});
