/**
 * Admin Model Detail, Ontology Diagram & Webhook Deletion E2E Tests
 *
 * Tests model detail page (info, stats, types), ontology diagram rendering
 * via the Relationships tab, and webhook creation + deletion.
 *
 * Consolidated into a single test() to stay within the 5/minute
 * magic-link rate limit when running alongside admin-model-lifecycle.spec.ts.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Admin Model Detail & Webhook CRUD', () => {
  test('model detail page with stats, types, ontology diagram, and webhook create/delete', async ({ ownerPage }) => {
    // ---- Part A: Model Detail Page ----
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm`);
    expect(resp?.status()).toBe(200);

    // Should display the model name
    await ownerPage.waitForSelector('h1', { timeout: 15000 });
    const h1Text = await ownerPage.locator('h1').innerText();
    expect(h1Text).toMatch(/Basic PKM/i);

    // Verify stats bar
    const statsBar = ownerPage.locator('.stats-bar');
    await expect(statsBar).toBeVisible({ timeout: 10000 });

    // Stats should show Types, Properties, Views, Shapes counts (CSS may uppercase)
    const statLabels = (await ownerPage.locator('.stat-label').allInnerTexts())
      .map((t) => t.toLowerCase());
    expect(statLabels).toContain('types');
    expect(statLabels).toContain('properties');
    expect(statLabels).toContain('views');
    expect(statLabels).toContain('shapes');

    // At least 1 type listed
    const typeCount = await ownerPage.locator('.stat-value').first().innerText();
    expect(parseInt(typeCount)).toBeGreaterThanOrEqual(1);

    // Verify type list shows Basic PKM types
    const content = await ownerPage.textContent('body');
    expect(content).toMatch(/Note|Concept|Project|Person/);

    // Verify type cards are present
    const typeCards = ownerPage.locator('.type-detail-card');
    const cardCount = await typeCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(1);

    // Verify version pill and meta row
    await expect(ownerPage.locator('.version-pill')).toBeVisible();
    await expect(ownerPage.locator('.model-meta-row')).toBeVisible();

    // ---- Part B: Ontology Diagram (Relationships tab) ----
    const relationshipsTab = ownerPage.locator('.model-tab[data-tab="relationships"]');
    await expect(relationshipsTab).toBeVisible();
    await relationshipsTab.click();
    await waitForIdle(ownerPage);

    // Wait for the diagram to load via htmx
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // The ontology diagram panel should now be visible
    const diagramPanel = ownerPage.locator('.ontology-diagram-panel');
    await expect(diagramPanel).toBeVisible({ timeout: 15000 });

    // Should have either a Cytoscape container or "no relationships" message
    const hasCytoscape = await ownerPage.locator('#ontology-cy').count();
    const hasEmptyMsg = await ownerPage.locator('.diagram-empty').count();
    expect(hasCytoscape + hasEmptyMsg).toBeGreaterThanOrEqual(1);

    if (hasCytoscape > 0) {
      const cyContainer = ownerPage.locator('#ontology-cy');
      await expect(cyContainer).toBeVisible();

      // Verify Cytoscape initialized (has child elements)
      const hasChildren = await ownerPage.evaluate(() => {
        const cy = document.getElementById('ontology-cy');
        return cy ? cy.children.length > 0 : false;
      });
      expect(hasChildren).toBe(true);
    }

    // Verify Technical Details section
    const schemaTab = ownerPage.locator('.model-tab[data-tab="schema"]');
    await schemaTab.click();
    await ownerPage.waitForTimeout(500);

    const techDetails = ownerPage.locator('.tech-details');
    await expect(techDetails).toBeVisible();

    // Expand tech details
    await techDetails.locator('summary').click();
    await ownerPage.waitForTimeout(500);

    const techContent = await techDetails.textContent();
    expect(techContent).toContain('basic-pkm');

    // ---- Part C: Webhook Create & Delete ----
    // Register dialog handler for hx-confirm
    ownerPage.on('dialog', (dialog) => dialog.accept());

    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Create a webhook
    await ownerPage.fill('#webhook-url', 'https://example.com/e2e-lifecycle-test');
    await ownerPage.locator('.checkbox-group input[value="object.changed"]').check();
    await ownerPage.click('button:has-text("Create")');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify webhook appears
    await expect(ownerPage.locator(SEL.admin.webhookList)).toContainText(
      'example.com/e2e-lifecycle-test',
      { timeout: 10000 },
    );

    // Delete the webhook
    const testRow = ownerPage.locator(`${SEL.admin.webhookList} tbody tr`).filter({
      hasText: 'e2e-lifecycle-test',
    });
    const deleteBtn = testRow.locator('button:has-text("Delete")');
    await deleteBtn.click();
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Reload and verify webhook is gone
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    const remainingRows = await ownerPage.locator(`${SEL.admin.webhookList} tbody tr`).filter({
      hasText: 'e2e-lifecycle-test',
    }).count();
    expect(remainingRows).toBe(0);
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm`);
    expect(resp?.status()).toBe(200);

    // Should display the model name
    await ownerPage.waitForSelector('h1', { timeout: 15000 });
    const h1Text = await ownerPage.locator('h1').innerText();
    expect(h1Text).toMatch(/Basic PKM/i);

    // Verify stats bar
    const statsBar = ownerPage.locator('.stats-bar');
    await expect(statsBar).toBeVisible({ timeout: 10000 });

    // Stats should show Types, Properties, Views, Shapes counts (CSS may uppercase)
    const statLabels = (await ownerPage.locator('.stat-label').allInnerTexts())
      .map((t) => t.toLowerCase());
    expect(statLabels).toContain('types');
    expect(statLabels).toContain('properties');
    expect(statLabels).toContain('views');
    expect(statLabels).toContain('shapes');

    // At least 1 type listed
    const typeCount = await ownerPage.locator('.stat-value').first().innerText();
    expect(parseInt(typeCount)).toBeGreaterThanOrEqual(1);

    // Verify type list shows Basic PKM types
    const content = await ownerPage.textContent('body');
    expect(content).toMatch(/Note|Concept|Project|Person/);

    // Verify type cards are present
    const typeCards = ownerPage.locator('.type-detail-card');
    const cardCount = await typeCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(1);

    // Verify version pill and meta row
    await expect(ownerPage.locator('.version-pill')).toBeVisible();
    await expect(ownerPage.locator('.model-meta-row')).toBeVisible();

    // ---- Part B: Ontology Diagram (Relationships tab) ----
    const relationshipsTab = ownerPage.locator('.model-tab[data-tab="relationships"]');
    await expect(relationshipsTab).toBeVisible();
    await relationshipsTab.click();
    await waitForIdle(ownerPage);

    // Wait for the diagram to load via htmx
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // The ontology diagram panel should now be visible
    const diagramPanel = ownerPage.locator('.ontology-diagram-panel');
    await expect(diagramPanel).toBeVisible({ timeout: 15000 });

    // Should have either a Cytoscape container or "no relationships" message
    const hasCytoscape = await ownerPage.locator('#ontology-cy').count();
    const hasEmptyMsg = await ownerPage.locator('.diagram-empty').count();
    expect(hasCytoscape + hasEmptyMsg).toBeGreaterThanOrEqual(1);

    if (hasCytoscape > 0) {
      const cyContainer = ownerPage.locator('#ontology-cy');
      await expect(cyContainer).toBeVisible();

      // Verify Cytoscape initialized (has child elements)
      const hasChildren = await ownerPage.evaluate(() => {
        const cy = document.getElementById('ontology-cy');
        return cy ? cy.children.length > 0 : false;
      });
      expect(hasChildren).toBe(true);
    }

    // Verify Technical Details section
    const schemaTab = ownerPage.locator('.model-tab[data-tab="schema"]');
    await schemaTab.click();
    await ownerPage.waitForTimeout(500);

    const techDetails = ownerPage.locator('.tech-details');
    await expect(techDetails).toBeVisible();

    // Expand tech details
    await techDetails.locator('summary').click();
    await ownerPage.waitForTimeout(500);

    const techContent = await techDetails.textContent();
    expect(techContent).toContain('basic-pkm');

    // ---- Part C: Webhook Create & Delete ----
    // Register dialog handler for hx-confirm
    ownerPage.on('dialog', (dialog) => dialog.accept());

    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    // Create a webhook
    await ownerPage.fill('#webhook-url', 'https://example.com/e2e-lifecycle-test');
    await ownerPage.locator('.checkbox-group input[value="object.changed"]').check();
    await ownerPage.click('button:has-text("Create")');
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify webhook appears
    await expect(ownerPage.locator(SEL.admin.webhookList)).toContainText(
      'example.com/e2e-lifecycle-test',
      { timeout: 10000 },
    );

    // Delete the webhook
    const testRow = ownerPage.locator(`${SEL.admin.webhookList} tbody tr`).filter({
      hasText: 'e2e-lifecycle-test',
    });
    const deleteBtn = testRow.locator('button:has-text("Delete")');
    await deleteBtn.click();
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Reload and verify webhook is gone
    await ownerPage.goto(`${BASE_URL}/admin/webhooks`);
    await ownerPage.waitForSelector(SEL.admin.webhookList, { timeout: 15000 });

    if (rowCount > 0) {
      // Find the row with our test URL
      const testRow = webhookRows.filter({ hasText: 'example.com' });
      if (await testRow.count() > 0) {
        const deleteBtn = testRow.locator('button', { hasText: /Delete|Remove/i });
        await deleteBtn.click();
        await waitForIdle(ownerPage);

        // Verify it's gone
        await ownerPage.waitForTimeout(1000);
        const afterCount = await webhookRows.filter({ hasText: 'example.com' }).count();
        expect(afterCount).toBe(0);
      }
    }
  });
});
