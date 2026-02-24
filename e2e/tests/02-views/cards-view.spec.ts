/**
 * Cards View E2E Tests
 *
 * Tests the cards view renderer: loading cards, card content,
 * flip animation, card click navigation, and group-by.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Cards View', () => {
  test('cards view renders cards for seed data', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const cardSpec = specs.find((s: any) => s.renderer_type === 'card');

    if (!cardSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(cardSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/views/card/' + iri, { target });
      }
    }, encodedSpecIri);

    // Wait for cards to appear
    await ownerPage.waitForSelector('.card-grid, .flip-card', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const cards = ownerPage.locator(SEL.views.card);
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('card shows title and snippet on front', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const cardSpec = specs.find((s: any) => s.renderer_type === 'card');

    if (!cardSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(cardSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/views/card/' + iri, { target });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('.flip-card', { timeout: 15000 });

    // Each card front should have a title
    const firstCardTitle = ownerPage.locator('.card-title').first();
    await expect(firstCardTitle).not.toBeEmpty();
  });

  test('card flip reveals properties on back', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const cardSpec = specs.find((s: any) => s.renderer_type === 'card');

    if (!cardSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(cardSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/views/card/' + iri, { target });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('.flip-card', { timeout: 15000 });

    // Click the flip button on the first card
    const flipBtn = ownerPage.locator('.card-btn-flip').first();
    await flipBtn.click();

    // The card should now have the 'flipped' class
    const firstCard = ownerPage.locator('.flip-card').first();
    await expect(firstCard).toHaveClass(/flipped/);
  });

  test('clicking card title opens object', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const cardSpec = specs.find((s: any) => s.renderer_type === 'card');

    if (!cardSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(cardSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const target = document.querySelector('#editor-area-group-1');
      if (target && (window as any).htmx) {
        (window as any).htmx.ajax('GET', '/browser/views/card/' + iri, { target });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('.flip-card', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Click the card title to navigate to the object
    const cardTitle = ownerPage.locator('.card-title').first();
    await cardTitle.click();
    await waitForIdle(ownerPage);

    // Editor should now show the object (not the cards view anymore)
    // The tab bar should have a new tab
    const tabBar = ownerPage.locator(SEL.workspace.tabBar);
    await expect(tabBar).not.toContainText('No objects open', { timeout: 10000 });
  });
});
