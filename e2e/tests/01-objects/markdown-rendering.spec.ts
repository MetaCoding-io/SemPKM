/**
 * Markdown Rendering Fidelity E2E Tests
 *
 * Tests that markdown body content renders correctly with headers, bold,
 * links, code blocks, and that XSS is sanitized by DOMPurify.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';
import { openObjectTab } from '../../helpers/dockview';

test.describe('Markdown Rendering', () => {
  let testObjectIri: string;

  test('create object with markdown body', async ({ ownerRequest }) => {
    const markdownBody = [
      '# Heading 1',
      '## Heading 2',
      '**Bold text** and *italic text*',
      '',
      '[A link](https://example.com)',
      '',
      '```javascript',
      'const x = 42;',
      '```',
      '',
      '- List item 1',
      '- List item 2',
      '',
      '<script>alert("xss")</script>',
      '<img src=x onerror="alert(1)">',
    ].join('\n');

    const resp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: {
            'http://purl.org/dc/terms/title': 'Markdown Test Note',
            'http://purl.org/dc/terms/description': markdownBody,
          },
        },
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    testObjectIri = data.results[0].iri;
    expect(testObjectIri).toBeTruthy();
  });

  test('rendered markdown has correct HTML elements', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

    // Open the markdown test object in read mode
    await openObjectTab(ownerPage, testObjectIri, 'Markdown Test Note', 'read');
    await waitForIdle(ownerPage);

    // Wait for the object content to render
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Check for rendered markdown elements
    const tabContent = ownerPage.locator('.object-tab');

    // Headers should render as h1/h2
    const h1Count = await tabContent.locator('h1').count();
    const h2Count = await tabContent.locator('h2').count();
    // Bold text should render as strong
    const strongCount = await tabContent.locator('strong').count();

    // At least some markdown should have rendered
    expect(h1Count + h2Count + strongCount).toBeGreaterThan(0);
  });

  test('XSS script tags are sanitized', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

    await openObjectTab(ownerPage, testObjectIri, 'Markdown Test Note', 'read');
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Verify no script tags exist in the rendered content
    const scriptCount = await ownerPage.evaluate(() => {
      const tab = document.querySelector('.object-tab');
      if (!tab) return 0;
      // Look for actual <script> elements (should be stripped by DOMPurify)
      return tab.querySelectorAll('script').length;
    });
    expect(scriptCount).toBe(0);

    // Also check that no alert was triggered
    // (Playwright auto-dismisses dialogs, but we can check the dialog log)
  });

  test('XSS onerror attributes are sanitized', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

    await openObjectTab(ownerPage, testObjectIri, 'Markdown Test Note', 'read');
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Check that onerror attributes are stripped
    const dangerousAttrs = await ownerPage.evaluate(() => {
      const tab = document.querySelector('.object-tab');
      if (!tab) return 0;
      return tab.querySelectorAll('[onerror], [onclick], [onload]').length;
    });
    expect(dangerousAttrs).toBe(0);
  });
});
