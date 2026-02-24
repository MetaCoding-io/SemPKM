/**
 * Authentication fixtures for SemPKM E2E tests.
 *
 * Provides:
 * - setupInstance(): One-time instance setup (claim with setup token)
 * - loginAsOwner(): Get an authenticated API context as the owner
 * - loginAsMember(): Get an authenticated API context as a member
 *
 * These work by calling the API directly (no UI interaction) so they're
 * fast and reliable for test arrangement.
 */
import { test as base, request, APIRequestContext, Page, BrowserContext, Browser } from '@playwright/test';
import { execSync } from 'child_process';
import { ApiClient } from '../helpers/api-client';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';
const OWNER_EMAIL = 'owner@test.local';
const MEMBER_EMAIL = 'member@test.local';

/** Resolve the repo root (one level up from e2e/) */
function repoRoot(): string {
  return execSync('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();
}

/** Read the setup token from the Docker API container */
function readSetupToken(): string {
  const root = repoRoot();
  try {
    return execSync(
      'docker compose -f docker-compose.test.yml exec -T api cat /app/data/.setup-token',
      { cwd: root, encoding: 'utf-8', timeout: 10000 },
    ).trim();
  } catch {
    // Fallback: grep from logs
    const logs = execSync(
      'docker compose -f docker-compose.test.yml logs api 2>&1',
      { cwd: root, encoding: 'utf-8', timeout: 10000 },
    );
    const match = logs.match(/Setup token:\s+(\S+)/);
    if (!match) throw new Error('Could not extract setup token from container');
    return match[1];
  }
}

/**
 * Complete instance setup if not already done.
 * Returns the session cookie value for the owner.
 */
async function ensureSetup(apiContext: APIRequestContext): Promise<string | null> {
  const statusResp = await apiContext.get(`${BASE_URL}/api/auth/status`);
  const status = await statusResp.json();

  if (status.setup_complete) {
    return null; // Already set up
  }

  const token = readSetupToken();
  const setupResp = await apiContext.post(`${BASE_URL}/api/auth/setup`, {
    data: { token, email: OWNER_EMAIL },
  });

  if (setupResp.status() !== 200) {
    const body = await setupResp.text();
    throw new Error(`Setup failed (${setupResp.status()}): ${body}`);
  }

  // Extract session cookie from Set-Cookie header
  const setCookie = setupResp.headers()['set-cookie'] || '';
  const match = setCookie.match(/sempkm_session=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Login via magic link (API-only, no UI).
 * Returns the session cookie value.
 */
async function loginViaApi(apiContext: APIRequestContext, email: string): Promise<string> {
  // Request magic link
  const mlResp = await apiContext.post(`${BASE_URL}/api/auth/magic-link`, {
    data: { email },
  });
  const mlData = await mlResp.json();

  if (!mlData.token) {
    throw new Error(`Magic link request did not return a token for ${email}`);
  }

  // Verify the token to create a session
  const verifyResp = await apiContext.post(`${BASE_URL}/api/auth/verify`, {
    data: { token: mlData.token },
  });

  if (verifyResp.status() !== 200) {
    const body = await verifyResp.text();
    throw new Error(`Token verification failed for ${email}: ${body}`);
  }

  // Extract session cookie
  const setCookie = verifyResp.headers()['set-cookie'] || '';
  const match = setCookie.match(/sempkm_session=([^;]+)/);
  if (!match) throw new Error(`No session cookie in verify response for ${email}`);
  return match[1];
}

/**
 * Create a browser context with an authenticated session cookie.
 */
async function authenticatedContext(
  browser: Browser,
  sessionToken: string,
): Promise<BrowserContext> {
  const context = await browser.newContext({
    baseURL: BASE_URL,
    storageState: {
      cookies: [
        {
          name: 'sempkm_session',
          value: sessionToken,
          domain: 'localhost',
          path: '/',
          httpOnly: true,
          secure: false,
          sameSite: 'Lax',
          expires: -1, // Session cookie
        },
      ],
      origins: [],
    },
  });
  return context;
}

// ---- Playwright Fixture Extension ----

type AuthFixtures = {
  /** API client with no auth — for setup and unauthenticated tests */
  anonApi: ApiClient;
  /** Perform instance setup, return owner session token */
  ownerSessionToken: string;
  /** A Playwright Page authenticated as the instance owner */
  ownerPage: Page;
  /** A Playwright Page authenticated as a member user */
  memberPage: Page;
};

export const test = base.extend<AuthFixtures>({
  anonApi: async ({}, use) => {
    const ctx = await request.newContext({ baseURL: BASE_URL });
    const client = new ApiClient(ctx, BASE_URL);
    await use(client);
    await ctx.dispose();
  },

  ownerSessionToken: async ({}, use) => {
    const ctx = await request.newContext({ baseURL: BASE_URL });

    // Ensure instance is set up
    const cookieFromSetup = await ensureSetup(ctx);

    let token: string;
    if (cookieFromSetup) {
      token = cookieFromSetup;
    } else {
      // Already set up — login as owner
      token = await loginViaApi(ctx, OWNER_EMAIL);
    }

    await use(token);
    await ctx.dispose();
  },

  ownerPage: async ({ browser, ownerSessionToken }, use) => {
    const context = await authenticatedContext(browser, ownerSessionToken);
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  memberPage: async ({ browser, ownerSessionToken }, use) => {
    // First ensure the member exists by inviting them
    const ownerCtx = await request.newContext({
      baseURL: BASE_URL,
      extraHTTPHeaders: {
        Cookie: `sempkm_session=${ownerSessionToken}`,
      },
    });

    // Invite member (ignore if already invited)
    await ownerCtx.post(`${BASE_URL}/api/auth/invite`, {
      data: { email: MEMBER_EMAIL, role: 'member' },
    });
    await ownerCtx.dispose();

    // Login as member
    const memberCtx = await request.newContext({ baseURL: BASE_URL });
    const memberToken = await loginViaApi(memberCtx, MEMBER_EMAIL);
    await memberCtx.dispose();

    // Create authenticated browser context
    const context = await authenticatedContext(browser, memberToken);
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
export { OWNER_EMAIL, MEMBER_EMAIL, BASE_URL };
