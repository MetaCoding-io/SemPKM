/**
 * Mental Model Documentation E2E Tests (issue #54)
 *
 * Verifies that the Markdown documentation bundled inside a model archive
 * (entrypoints.docs / README.md) is served by the API and rendered on the
 * admin model detail page via the Documentation tab.
 *
 * Uses basic-pkm, which is pre-installed on every test stack.
 *
 * Consolidated into a single test() to stay within the 5/minute
 * magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('Mental Model Documentation', () => {
  test('bundled README is served by the API and rendered on the detail page', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // ---- Part A: raw Markdown API ----
    const apiResp = await ownerRequest.get(`${BASE_URL}/api/models/basic-pkm/docs`);
    expect(apiResp.status()).toBe(200);
    expect(apiResp.headers()['content-type']).toContain('text/markdown');
    const markdown = await apiResp.text();
    expect(markdown.trimStart().startsWith('# Basic PKM')).toBe(true);
    expect(markdown).toContain('`basic-pkm`');

    // Unknown model → 404
    const missing = await ownerRequest.get(`${BASE_URL}/api/models/does-not-exist/docs`);
    expect(missing.status()).toBe(404);

    // ---- Part A2: the user guide mirror of the same README ----
    // docs/guide/model-{id}.md is generated from models/{id}/README.md and served
    // by the guide static mount, so the in-app Docs hub and the public site can show it.
    const mirror = await ownerRequest.get(`${BASE_URL}/docs/guide/model-basic-pkm.md`);
    expect(mirror.status()).toBe(200);
    const mirrorText = await mirror.text();
    expect(mirrorText).toContain('<!-- GENERATED FILE');
    expect(mirrorText).toContain('# Basic PKM');
    expect(mirrorText).toContain(markdown.trim());

    // ---- Part B: Documentation tab on the admin detail page ----
    const resp = await ownerPage.goto(`${BASE_URL}/admin/models/basic-pkm`);
    expect(resp?.status()).toBe(200);
    await ownerPage.waitForSelector('h1', { timeout: 15000 });

    const docsTab = ownerPage.locator('.model-tab[data-tab="docs"]');
    await expect(docsTab).toBeVisible();
    await docsTab.click();

    // The partial is loaded via htmx and rendered client-side with marked + DOMPurify.
    const rendered = ownerPage.locator('#docs-panel .model-docs-content');
    await expect(rendered).toBeVisible({ timeout: 20000 });

    // Rendered HTML (not raw Markdown): an H1 with the model name and at least one table.
    const heading = rendered.locator('h1').first();
    await expect(heading).toHaveText(/Basic PKM/, { timeout: 15000 });
    await expect(rendered.locator('table').first()).toBeVisible();
    await expect(rendered.locator('h2', { hasText: /Types/ })).toBeVisible();

    // No raw Markdown syntax leaked into the rendered panel.
    const text = (await rendered.innerText()).trim();
    expect(text.startsWith('# ')).toBe(false);
    expect(text).not.toContain('|-------|');

    // The docs tab is active and the schema panel is hidden.
    await expect(docsTab).toHaveClass(/active/);
    await expect(ownerPage.locator('#schema-panel')).toBeHidden();

    // Switching back to Schema restores the type cards.
    await ownerPage.locator('.model-tab[data-tab="schema"]').click();
    await expect(ownerPage.locator('#schema-panel')).toBeVisible();
    await expect(ownerPage.locator('#docs-panel')).toBeHidden();
  });
});
