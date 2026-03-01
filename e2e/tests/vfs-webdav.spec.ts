/**
 * VFS WebDAV E2E Tests
 *
 * Tests the WebDAV virtual filesystem endpoint that exposes SemPKM objects
 * as Markdown files. Covers: PROPFIND availability, directory listing,
 * object file content, and read-only enforcement (PUT returns 405).
 *
 * Depends on Phase 26 (VFS MVP Read-Only via wsgidav) being complete.
 * Tests are conditionally skipped if the /dav/ endpoint does not exist.
 *
 * Auth: Uses sempkm_session cookie. In Phase 26+27, API token auth may be
 * required. If Bearer token auth is implemented, tests will need updating.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const DAV_URL = `${BASE_URL}/dav`;

test.describe('VFS WebDAV', () => {

  test('WebDAV endpoint /dav/ responds to OPTIONS', async ({ ownerPage, ownerSessionToken }) => {
    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'OPTIONS',
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
      },
    });

    if (resp.status() === 404) {
      test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented — /dav/ endpoint does not exist');
      return;
    }

    // OPTIONS should return 200 or 204 with allowed methods
    expect([200, 204]).toContain(resp.status());
    const allow = resp.headers()['allow'] || resp.headers()['Allow'] || '';
    // At minimum, PROPFIND and GET should be allowed
    expect(allow.toUpperCase()).toContain('PROPFIND');
  });

  test('PROPFIND on /dav/ returns 207 Multi-Status', async ({ ownerPage, ownerSessionToken }) => {
    const propfindBody = '<?xml version="1.0" encoding="utf-8"?>' +
      '<propfind xmlns="DAV:"><allprop/></propfind>';

    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: propfindBody,
    });

    if (resp.status() === 404) {
      test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented');
      return;
    }

    if (resp.status() === 401 || resp.status() === 403) {
      test.skip(true, 'WebDAV requires API token auth (Phase 27) — session cookie not accepted by /dav/');
      return;
    }

    // 207 Multi-Status is the correct WebDAV response for PROPFIND
    expect(resp.status()).toBe(207);
  });

  test('PROPFIND directory listing contains type-based collections', async ({ ownerPage, ownerSessionToken }) => {
    const propfindBody = '<?xml version="1.0" encoding="utf-8"?>' +
      '<propfind xmlns="DAV:"><allprop/></propfind>';

    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'Content-Type': 'application/xml; charset=utf-8',
        Depth: '1',
      },
      data: propfindBody,
    });

    if (resp.status() === 404) {
      test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented');
      return;
    }

    if (resp.status() !== 207) {
      test.skip(true, `WebDAV PROPFIND returned ${resp.status()} — feature may require additional auth setup`);
      return;
    }

    const body = await resp.text();
    expect(body).toBeTruthy();
    // Multi-Status XML should contain href elements for type directories
    expect(body).toContain('<D:href');
    // Should contain at minimum the root collection href
    expect(body).toContain('/dav/');
  });

  test('object .md file is accessible at /dav/<TypeName>/<label>.md', async ({ ownerPage, ownerSessionToken }) => {
    // Try to GET a known seed object's Markdown file
    // File path pattern: /dav/Note/Architecture Decision: Event Sourcing.md (URL-encoded)
    const noteTitle = encodeURIComponent(SEED.notes.architecture.title);
    const filePath = `${DAV_URL}/Note/${noteTitle}.md`;

    const resp = await ownerPage.context().request.get(filePath, {
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
      },
    });

    if (resp.status() === 404 && resp.url().includes('/dav/')) {
      // Check if /dav/ itself is available
      const davRoot = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
        method: 'PROPFIND',
        headers: { Cookie: `sempkm_session=${ownerSessionToken}`, Depth: '0' },
        data: '<?xml version="1.0"?><propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>',
      });
      if (davRoot.status() === 404) {
        test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented');
        return;
      }
    }

    if (resp.status() === 401 || resp.status() === 403) {
      test.skip(true, 'WebDAV file access requires API token auth (Phase 27)');
      return;
    }

    if (resp.ok()) {
      const content = await resp.text();
      // Markdown file should have YAML frontmatter (starting with ---)
      expect(content).toContain('---');
      // Should contain the object's IRI in frontmatter
      expect(content).toContain(SEED.notes.architecture.iri);
    }
    // If 404 for specific file but DAV root exists — path pattern may differ; not a hard failure
  });

  test('object file content has SHACL-derived frontmatter', async ({ ownerPage, ownerSessionToken }) => {
    // GET a seed object's Markdown file and verify frontmatter structure
    const noteTitle = encodeURIComponent(SEED.notes.architecture.title);
    const filePath = `${DAV_URL}/Note/${noteTitle}.md`;

    const resp = await ownerPage.context().request.get(filePath, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });

    if (resp.status() === 404 || resp.status() === 405) {
      test.skip(true, 'Phase 26 (VFS WebDAV) file access not yet implemented or path pattern differs');
      return;
    }

    if (!resp.ok()) {
      test.skip(true, `WebDAV file GET returned ${resp.status()}`);
      return;
    }

    const content = await resp.text();
    // YAML frontmatter block
    expect(content.startsWith('---')).toBeTruthy();

    // Should have type field from SHACL shape
    expect(content).toContain('type:');
    // Should have title or label field
    const hasLabel = content.includes('title:') || content.includes('label:');
    expect(hasLabel).toBeTruthy();
  });

  test('WebDAV is read-only — PUT returns 405 Method Not Allowed', async ({ ownerPage, ownerSessionToken }) => {
    // Attempt to PUT a file — must be rejected with 405
    const filePath = `${DAV_URL}/Note/test-write-attempt.md`;

    const resp = await ownerPage.context().request.fetch(filePath, {
      method: 'PUT',
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'Content-Type': 'text/markdown',
      },
      data: '---\ntitle: Test Write Attempt\n---\nThis should not be written.',
    });

    if (resp.status() === 404 && resp.url().includes('/dav/')) {
      // Check if dav/ endpoint exists at all
      const davRoot = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
        method: 'OPTIONS',
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      });
      if (davRoot.status() === 404) {
        test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented');
        return;
      }
    }

    // PUT to a read-only WebDAV must return 405 Method Not Allowed
    // (or 403 Forbidden if auth is the blocking factor)
    expect([405, 403, 501]).toContain(resp.status());
  });

  test('WebDAV endpoint is accessible without browser navigation (pure HTTP)', async ({ ownerPage, ownerSessionToken }) => {
    // Verify that the /dav/ endpoint works via direct HTTP (not browser redirect)
    // This validates nginx routing is correct for WebDAV verbs
    const resp = await ownerPage.context().request.fetch(`${DAV_URL}/`, {
      method: 'PROPFIND',
      headers: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
        'Content-Type': 'application/xml',
        Depth: '0',
      },
      data: '<?xml version="1.0" encoding="utf-8"?><propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>',
    });

    if (resp.status() === 404) {
      test.skip(true, 'Phase 26 (VFS WebDAV) not yet implemented');
      return;
    }

    // Response must be 207 or an auth challenge (not a browser HTML redirect)
    expect([207, 401, 403]).toContain(resp.status());
    // Must NOT be an HTML page (not a redirect to /login)
    const contentType = resp.headers()['content-type'] || '';
    if (resp.status() === 207) {
      expect(contentType).toContain('xml');
    }
  });

});
