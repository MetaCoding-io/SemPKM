/**
 * Demo Instance E2E Tests — Read-Only Enforcement & Anonymous Access
 *
 * Proves two DEMO slice requirements against the live demo Docker stack:
 *   DEMO-01: Anonymous workspace access (no login, no setup wizard)
 *   DEMO-02: Write-method blocking (POST/PUT/DELETE/PATCH → 403 JSON)
 *
 * Target: http://localhost:3902 (docker-compose.demo.yml)
 * Auth: None — fresh browser context with no cookies.
 *
 * Prerequisites:
 *   cd <repo-root> && docker compose -f docker-compose.demo.yml up -d --build
 *   Wait for all services healthy before running.
 */
import { test, expect } from '@playwright/test';

const DEMO_URL = 'http://localhost:3902';

test.describe('Demo Instance — Read-Only Mode', () => {
  test.describe.configure({ mode: 'serial' });
  test.beforeAll(async () => {
    // Skip if demo stack is not running
    try {
      await fetch('http://localhost:3902/api/health', { signal: AbortSignal.timeout(2000) });
    } catch {
      test.skip(true, 'Demo stack not running (port 3902). Start with: docker compose -f docker-compose.demo.yml up -d --build');
    }
  });


  // ── DEMO-01: Anonymous workspace access ──────────────────────────

  test('anonymous user reaches workspace without login redirect', async ({ page }) => {
    const response = await page.goto(`${DEMO_URL}/browser/`);

    // HTTP 200, not a redirect chain ending at login
    expect(response).not.toBeNull();
    expect(response!.status()).toBe(200);

    // Final URL still contains /browser — no redirect to /login.html or /setup.html
    const url = page.url();
    expect(url).toContain('/browser');
    expect(url).not.toContain('/login.html');
    expect(url).not.toContain('/setup.html');

    // Workspace content is visible — the workspace container with data-testid="workspace"
    // only renders on the workspace page, not on login/setup pages.
    await expect(
      page.locator('[data-testid="workspace"]')
    ).toBeVisible({ timeout: 15_000 });
  });

  // ── DEMO-01 continued: Read routes return 200 ───────────────────

  test('GET read routes return 200 through demo nginx', async ({ request }) => {
    // /api/health — public health check
    const healthResp = await request.get(`${DEMO_URL}/api/health`);
    expect(healthResp.status()).toBe(200);
    const healthData = await healthResp.json();
    expect(healthData.status).toBeDefined();

    // /api/auth/status — public auth status (works without auth)
    const authResp = await request.get(`${DEMO_URL}/api/auth/status`);
    expect(authResp.status()).toBe(200);
    const authData = await authResp.json();
    expect(authData).toBeDefined();
  });

  // ── DEMO-02: Write methods blocked with 403 JSON ────────────────

  test('POST/PUT/DELETE/PATCH blocked with 403 and JSON error', async ({ request }) => {
    const readOnlyMsg = 'Demo instance is read-only';

    // POST /api/commands — the main write endpoint
    const postResp = await request.post(`${DEMO_URL}/api/commands`, {
      data: { type: 'object.create', data: { type_iri: 'test' } },
    });
    expect(postResp.status()).toBe(403);
    const postBody = await postResp.json();
    expect(postBody.error).toContain(readOnlyMsg);

    // PUT /api/dashboards/fake-id — dashboard write
    const putResp = await request.put(`${DEMO_URL}/api/dashboards/fake-id`, {
      data: {},
    });
    expect(putResp.status()).toBe(403);
    const putBody = await putResp.json();
    expect(putBody.error).toContain(readOnlyMsg);

    // DELETE /api/sparql/saved/fake-id — saved query deletion
    const deleteResp = await request.delete(`${DEMO_URL}/api/sparql/saved/fake-id`);
    expect(deleteResp.status()).toBe(403);
    const deleteBody = await deleteResp.json();
    expect(deleteBody.error).toContain(readOnlyMsg);

    // PATCH /api/commands — nginx blocks method before routing (endpoint doesn't exist)
    const patchResp = await request.patch(`${DEMO_URL}/api/commands`);
    expect(patchResp.status()).toBe(403);
    const patchBody = await patchResp.json();
    expect(patchBody.error).toContain(readOnlyMsg);

    // POST /browser/objects/test/body — htmx write route (also blocked)
    const htmxResp = await request.post(`${DEMO_URL}/browser/objects/test/body`, {
      data: 'test body content',
      headers: { 'Content-Type': 'text/plain' },
    });
    expect(htmxResp.status()).toBe(403);
    const htmxBody = await htmxResp.json();
    expect(htmxBody.error).toContain(readOnlyMsg);
  });

  // ── CORS preflight still works ──────────────────────────────────

  test('OPTIONS preflight returns 204 (not blocked by write guard)', async ({ request }) => {
    const optionsResp = await request.fetch(`${DEMO_URL}/api/commands`, {
      method: 'OPTIONS',
      headers: {
        'Origin': 'http://example.com',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
      },
    });
    // OPTIONS is in the nginx allow list — should get 204 CORS preflight response
    expect(optionsResp.status()).toBe(204);
  });
});
