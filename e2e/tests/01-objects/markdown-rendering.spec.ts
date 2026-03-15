/**
 * Markdown Rendering Fidelity E2E Tests
 *
 * Tests that markdown body content renders correctly with headers, bold,
 * links, code blocks, and that XSS is sanitized by DOMPurify.
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S10
 *
 * Consolidated into 1 test() function (API create + endpoint verify +
 * UI rendering + XSS check) to stay within the 5/minute magic-link
 * rate limit.
 *
 * The body is stored via the urn:sempkm:body predicate, which the
 * client-side renderMarkdownBody() renders using marked.js + DOMPurify.
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S03
=======
>>>>>>> gsd/M003/S10
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';
import { openObjectTab } from '../../helpers/dockview';

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S10
const MARKDOWN_BODY = [
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

<<<<<<< HEAD
test.describe('Markdown Rendering', () => {
  test('markdown renders correctly, XSS is sanitized, and API returns body content', async ({ ownerRequest, ownerPage }) => {
    // --- Part 1: Create objects via API ---

    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
=======
=======
>>>>>>> gsd/M003/S10
test.describe('Markdown Rendering', () => {
  test('markdown renders correctly, XSS is sanitized, and API returns body content', async ({ ownerRequest, ownerPage }) => {
    // --- Part 1: Create objects via API ---

<<<<<<< HEAD
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
>>>>>>> gsd/M003/S03
=======
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
>>>>>>> gsd/M003/S10
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: {
<<<<<<< HEAD
<<<<<<< HEAD
            'http://purl.org/dc/terms/title': 'Markdown Render Test',
            'urn:sempkm:body': MARKDOWN_BODY,
=======
            'http://purl.org/dc/terms/title': 'Markdown Test Note',
            'http://purl.org/dc/terms/description': markdownBody,
>>>>>>> gsd/M003/S03
=======
            'http://purl.org/dc/terms/title': 'Markdown Render Test',
            'urn:sempkm:body': MARKDOWN_BODY,
>>>>>>> gsd/M003/S10
          },
        },
      },
    });
<<<<<<< HEAD
<<<<<<< HEAD
    expect(createResp.ok()).toBeTruthy();
    const data = await createResp.json();
    const testObjectIri = data.results[0].iri;
    expect(testObjectIri).toBeTruthy();

    // --- Part 2: Verify object read endpoint returns HTML with body ---

    const readResp = await ownerRequest.get(
      `${BASE_URL}/browser/object/${encodeURIComponent(testObjectIri)}`
    );
    expect(readResp.ok()).toBeTruthy();
    const html = await readResp.text();
    expect(html).toContain('Markdown Render Test');
    expect(html).toContain('Heading 1');

    // --- Part 3: Open in workspace, verify rendered markdown ---

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });
    await openObjectTab(ownerPage, testObjectIri, 'Markdown Render Test', 'read');
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Wait for markdown rendering (client-side via renderMarkdownBody)
    await ownerPage.waitForFunction(
      () => {
        const body = document.querySelector('.markdown-body');
        if (!body) return false;
        return body.querySelectorAll('h1, h2, strong, pre').length > 0;
      },
      { timeout: 10000 },
    );

    const mdBody = ownerPage.locator('.markdown-body');

    // Headers should render as h1/h2
    const h1Count = await mdBody.locator('h1').count();
    const h2Count = await mdBody.locator('h2').count();
    expect(h1Count + h2Count).toBeGreaterThan(0);

    // Bold text should render as strong
    expect(await mdBody.locator('strong').count()).toBeGreaterThan(0);

    // Code blocks should render as pre > code
    expect(await mdBody.locator('pre code').count()).toBeGreaterThan(0);

    // List items should render as li
    expect(await mdBody.locator('li').count()).toBeGreaterThanOrEqual(2);

    // Links should render as <a>
    expect(await mdBody.locator('a[href="https://example.com"]').count()).toBeGreaterThanOrEqual(1);

    // --- Part 4: Verify XSS is sanitized by DOMPurify ---

    // No <script> elements in the rendered markdown body
    const scriptCount = await ownerPage.evaluate(() => {
      const body = document.querySelector('.markdown-body');
      if (!body) return 0;
      return body.querySelectorAll('script').length;
    });
    expect(scriptCount).toBe(0);

    // No dangerous event handler attributes in the rendered body
    const dangerousAttrs = await ownerPage.evaluate(() => {
      const body = document.querySelector('.markdown-body');
      if (!body) return 0;
      return body.querySelectorAll('[onerror], [onclick], [onload], [onmouseover]').length;
=======
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    testObjectIri = data.results[0].iri;
=======
    expect(createResp.ok()).toBeTruthy();
    const data = await createResp.json();
    const testObjectIri = data.results[0].iri;
>>>>>>> gsd/M003/S10
    expect(testObjectIri).toBeTruthy();

    // --- Part 2: Verify object read endpoint returns HTML with body ---

    const readResp = await ownerRequest.get(
      `${BASE_URL}/browser/object/${encodeURIComponent(testObjectIri)}`
    );
    expect(readResp.ok()).toBeTruthy();
    const html = await readResp.text();
    expect(html).toContain('Markdown Render Test');
    expect(html).toContain('Heading 1');

    // --- Part 3: Open in workspace, verify rendered markdown ---

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });
    await openObjectTab(ownerPage, testObjectIri, 'Markdown Render Test', 'read');
    await waitForIdle(ownerPage);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Wait for markdown rendering (client-side via renderMarkdownBody)
    await ownerPage.waitForFunction(
      () => {
        const body = document.querySelector('.markdown-body');
        if (!body) return false;
        return body.querySelectorAll('h1, h2, strong, pre').length > 0;
      },
      { timeout: 10000 },
    );

    const mdBody = ownerPage.locator('.markdown-body');

    // Headers should render as h1/h2
    const h1Count = await mdBody.locator('h1').count();
    const h2Count = await mdBody.locator('h2').count();
    expect(h1Count + h2Count).toBeGreaterThan(0);

    // Bold text should render as strong
    expect(await mdBody.locator('strong').count()).toBeGreaterThan(0);

    // Code blocks should render as pre > code
    expect(await mdBody.locator('pre code').count()).toBeGreaterThan(0);

    // List items should render as li
    expect(await mdBody.locator('li').count()).toBeGreaterThanOrEqual(2);

    // Links should render as <a>
    expect(await mdBody.locator('a[href="https://example.com"]').count()).toBeGreaterThanOrEqual(1);

    // --- Part 4: Verify XSS is sanitized by DOMPurify ---

    // No <script> elements in the rendered markdown body
    const scriptCount = await ownerPage.evaluate(() => {
      const body = document.querySelector('.markdown-body');
      if (!body) return 0;
      return body.querySelectorAll('script').length;
    });
    expect(scriptCount).toBe(0);

    // No dangerous event handler attributes in the rendered body
    const dangerousAttrs = await ownerPage.evaluate(() => {
<<<<<<< HEAD
      const tab = document.querySelector('.object-tab');
      if (!tab) return 0;
      return tab.querySelectorAll('[onerror], [onclick], [onload]').length;
>>>>>>> gsd/M003/S03
=======
      const body = document.querySelector('.markdown-body');
      if (!body) return 0;
      return body.querySelectorAll('[onerror], [onclick], [onload], [onmouseover]').length;
>>>>>>> gsd/M003/S10
    });
    expect(dangerousAttrs).toBe(0);
  });
});
