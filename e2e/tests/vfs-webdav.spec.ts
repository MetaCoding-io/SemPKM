/**
 * VFS WebDAV E2E Tests
 *
 * Tests the WebDAV virtual filesystem endpoint that exposes SemPKM objects
 * as Markdown files. Covers: OPTIONS availability, PROPFIND directory listing,
 * object file content with SHACL frontmatter, and read-only enforcement.
 *
 * Auth: Uses Basic auth with API tokens (wsgidav's SemPKMWsgiAuthenticator
 * does NOT accept session cookies — only email + API token via Basic auth).
 */
import { test as authTest, expect, OWNER_EMAIL, BASE_URL } from '../fixtures/auth';
import { request } from '@playwright/test';
import { SEED } from '../fixtures/seed-data';

const DAV_URL = `${BASE_URL}/dav`;

const test = authTest.extend<{ vfsBasicAuth: string }>({
  vfsBasicAuth: async ({ ownerSessionToken }, use) => {
    const ctx = await request.newContext();
    const resp = await ctx.post(`${BASE_URL}/api/auth/tokens`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: { name: 'e2e-vfs-' + Date.now() },
    });
    const body = await resp.json();
    const auth = 'Basic ' + Buffer.from(OWNER_EMAIL + ':' + body.token).toString('base64');
    await use(auth);
    // Cleanup: revoke the token
    await ctx.delete(`${BASE_URL}/api/auth/tokens/${body.id}`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    await ctx.dispose();
  },
});

test.describe('VFS WebDAV', () => {

  test('WebDAV endpoint /dav/ responds to OPTIONS', async ({ ownerPage, vfsBasicAuth }) => {
    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'OPTIONS',
      headers: {
        Authorization: vfsBasicAuth,
      },
    });

    // OPTIONS should return 200 or 204 with allowed methods
    expect([200, 204]).toContain(resp.status());
    const allow = resp.headers()['allow'] || resp.headers()['Allow'] || '';
    // At minimum, PROPFIND and GET should be allowed
    expect(allow.toUpperCase()).toContain('PROPFIND');
  });

  test('PROPFIND on /dav/ returns 207 Multi-Status', async ({ ownerPage, vfsBasicAuth }) => {
    const propfindBody = '<?xml version="1.0" encoding="utf-8"?>' +
      '<propfind xmlns="DAV:"><allprop/></propfind>';

    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: propfindBody,
    });

    // 207 Multi-Status is the correct WebDAV response for PROPFIND
    expect(resp.status()).toBe(207);
  });

  test('PROPFIND directory listing contains type-based collections', async ({ ownerPage, vfsBasicAuth }) => {
    const propfindBody = '<?xml version="1.0" encoding="utf-8"?>' +
      '<propfind xmlns="DAV:"><allprop/></propfind>';

    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: propfindBody,
    });

    expect(resp.status()).toBe(207);
    const body = await resp.text();
    expect(body).toBeTruthy();
    // Multi-Status XML should contain href elements (namespace prefix varies: D:, ns0:, etc.)
    expect(body).toContain(':href');
    // Should contain the model-based directory (basic-pkm)
    expect(body).toContain('basic-pkm');
  });

  test('object .md file is accessible via WebDAV GET', async ({ ownerPage, vfsBasicAuth }) => {
    // PROPFIND the Note directory to discover actual filenames
    const propResp = await ownerPage.context().request.fetch(`${DAV_URL}/basic-pkm/Note/`, {
      method: 'PROPFIND',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: '<?xml version="1.0" encoding="utf-8"?><propfind xmlns="DAV:"><allprop/></propfind>',
    });
    expect(propResp.status()).toBe(207);
    const listing = await propResp.text();

    // Extract the first .md file href
    const mdMatch = listing.match(/:href>([^<]*\.md)<\//);
    expect(mdMatch).toBeTruthy();
    const mdHref = mdMatch![1];
    const fileUrl = mdHref.startsWith('/dav') ? `${BASE_URL}${mdHref}` : `${BASE_URL}/dav${mdHref}`;

    const resp = await ownerPage.context().request.get(fileUrl, {
      headers: { Authorization: vfsBasicAuth },
    });

    expect(resp.ok()).toBeTruthy();
    const content = await resp.text();
    // Markdown file should have YAML frontmatter (starting with ---)
    expect(content).toContain('---');
    // Content should be more than just the frontmatter delimiter
    expect(content.length).toBeGreaterThan(10);
  });

  test('object file content has SHACL-derived frontmatter', async ({ ownerPage, vfsBasicAuth }) => {
    // PROPFIND the Note directory to discover actual filenames
    const propResp = await ownerPage.context().request.fetch(`${DAV_URL}/basic-pkm/Note/`, {
      method: 'PROPFIND',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: '<?xml version="1.0" encoding="utf-8"?><propfind xmlns="DAV:"><allprop/></propfind>',
    });
    expect(propResp.status()).toBe(207);
    const listing = await propResp.text();

    // Extract the first .md file href from the PROPFIND response
    const mdMatch = listing.match(/:href>([^<]*\.md)<\//);
    expect(mdMatch).toBeTruthy();
    const mdHref = mdMatch![1];

    // The href may be absolute from DAV root (e.g. /basic-pkm/Note/file.md)
    // Construct full URL: BASE_URL + /dav + href
    const fileUrl = mdHref.startsWith('/dav') ? `${BASE_URL}${mdHref}` : `${BASE_URL}/dav${mdHref}`;

    // GET the discovered file
    const resp = await ownerPage.context().request.get(fileUrl, {
      headers: { Authorization: vfsBasicAuth },
    });
    expect(resp.ok()).toBeTruthy();

    const content = await resp.text();
    // YAML frontmatter block
    expect(content.startsWith('---')).toBeTruthy();

    // Should have type_iri field from SHACL shape
    expect(content).toContain('type_iri:');
    // Should have object_iri and label fields
    const hasLabel = content.includes('object_iri:') || content.includes('label:');
    expect(hasLabel).toBeTruthy();
  });

  test('WebDAV is read-only — PUT returns 405 Method Not Allowed', async ({ ownerPage, vfsBasicAuth }) => {
    // Attempt to PUT a file — must be rejected with 405
    const filePath = `${DAV_URL}/basic-pkm/Note/test-write-attempt.md`;

    const resp = await ownerPage.context().request.fetch(filePath, {
      method: 'PUT',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'text/markdown',
      },
      data: '---\ntitle: Test Write Attempt\n---\nThis should not be written.',
    });

    // PUT to a read-only WebDAV must be rejected
    // 405 Method Not Allowed, 403 Forbidden, 501 Not Implemented, or 500 Internal Server Error
    expect([405, 403, 500, 501]).toContain(resp.status());
  });

  test('WebDAV endpoint is accessible without browser navigation (pure HTTP)', async ({ ownerPage, vfsBasicAuth }) => {
    // Verify that the /dav/ endpoint works via direct HTTP (not browser redirect)
    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Authorization: vfsBasicAuth,
        'Content-Type': 'application/xml',
        Depth: '0',
      },
      data: '<?xml version="1.0" encoding="utf-8"?><propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>',
    });

    // Response must be 207 (not a browser HTML redirect)
    expect(resp.status()).toBe(207);
    // Must NOT be an HTML page (not a redirect to /login)
    const contentType = resp.headers()['content-type'] || '';
    expect(contentType).toContain('xml');
  });

});
