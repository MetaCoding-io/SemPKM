# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Runner:**
- Playwright `^1.50.0` — E2E browser automation
- Config: `e2e/playwright.config.ts`
- TypeScript `^5.7.0` with `strict: true`

**Backend Unit Tests:**
- `pytest` + `pytest-asyncio` declared as dev dependencies in `backend/pyproject.toml`
- No unit test files currently exist in the repository (no `test_*.py` found)
- The test infrastructure is set up but no backend unit tests have been written

**Run Commands:**
```bash
# From e2e/ directory
npm test                          # Run all tests (chromium project)
npm run test:headed               # Run tests with visible browser
npm run test:debug                # Run with Playwright debugger
npm run test:ui                   # Run with Playwright UI mode
npm run screenshots               # Run screenshot capture suite
npm run report                    # Show HTML test report

# Environment management (run before tests)
npm run env:start                 # Start Docker test stack (port 3901)
npm run env:wait                  # Wait for health endpoint
npm run env:stop                  # Tear down test environment
```

## Test File Organization

**Location:** All tests in `e2e/tests/` with numbered directories for ordering

**Directory structure:**
```
e2e/
├── fixtures/
│   ├── auth.ts            # Authentication fixture extension (ownerPage, memberPage)
│   ├── seed-data.ts       # Seed data constants (IRIs, labels, counts)
│   └── test-harness.ts    # Global setup: verifies Docker stack is healthy
├── helpers/
│   ├── api-client.ts      # ApiClient class wrapping Playwright request context
│   ├── selectors.ts       # Shared CSS/data-testid selectors (SEL export)
│   └── wait-for.ts        # htmx-aware wait helpers
├── tests/
│   ├── 00-setup/          # Setup wizard and magic link auth
│   ├── 01-objects/        # CRUD operations (create, edit, batch, edges)
│   ├── 02-views/          # View renderers (table, cards, graph)
│   ├── 03-navigation/     # Workspace navigation (nav tree, tabs, keyboard)
│   ├── 04-validation/     # SHACL lint panel
│   ├── 05-admin/          # Admin portal (access control, models, webhooks)
│   ├── 06-settings/       # Dark mode, settings page
│   ├── 07-multi-user/     # Member permissions, session management
│   └── screenshots/       # Marketing screenshot capture suite
├── playwright.config.ts
└── package.json
```

**Naming:**
- Test files: `{subject}-{focus}.spec.ts` using kebab-case: `create-object.spec.ts`, `nav-tree.spec.ts`
- Test directories: numbered `NN-{area}/` for sequential ordering
- Fixtures: descriptive noun: `auth.ts`, `seed-data.ts`
- Helpers: descriptive noun: `selectors.ts`, `wait-for.ts`

## Test Structure

**Suite Organization:**

Tests are numbered and run sequentially (1 worker). Tests within a file use plain `test()` calls — no nested `describe()` blocks. File-level JSDoc explains the test scenario:

```typescript
/**
 * Object Creation E2E Tests
 *
 * Tests creating all four Basic PKM object types through the UI:
 * Note, Concept, Project, Person.
 *
 * Uses the auth fixture (ownerPage) so setup is already complete.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { TYPES } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

test('creates a note via type picker', async ({ ownerPage }) => {
  // ...
});
```

**Patterns:**
- Setup via auth fixture (no `beforeEach`/`afterAll` for auth — fixture handles it)
- Test arrangement via `ApiClient` methods (API-first, no UI clicks for setup)
- Assertions use Playwright's `expect()` with locators
- htmx interactions require explicit wait helpers before assertions

## Authentication Fixture

The custom `auth.ts` fixture extends Playwright's base `test` with four fixtures:

```typescript
type AuthFixtures = {
  anonApi: ApiClient;           // Unauthenticated API context
  ownerSessionToken: string;    // Owner session cookie value
  ownerPage: Page;              // Browser page authenticated as owner
  memberPage: Page;             // Browser page authenticated as member
};
```

**Usage pattern:**
```typescript
// Most tests use ownerPage
import { test, expect } from '../../fixtures/auth';

test('example test', async ({ ownerPage }) => {
  await ownerPage.goto('/');
  // ...
});

// Multi-user tests use both
test('member cannot access admin', async ({ ownerPage, memberPage }) => {
  // ...
});
```

Authentication is performed via direct API calls (not UI interaction) to get session cookies, then injected into the browser context. This is faster and more reliable than automating the login flow for every test.

## API Client Helper

`e2e/helpers/api-client.ts` provides an `ApiClient` class wrapping Playwright's `APIRequestContext`:

```typescript
export class ApiClient {
  constructor(private ctx: APIRequestContext, private sessionCookie?: string)

  // Auth
  async getAuthStatus(): Promise<{ setup_complete: boolean; setup_mode: boolean }>
  async setup(token: string, email?: string)
  async requestMagicLink(email: string)
  async verifyToken(token: string)
  async getMe()
  async logout()

  // Data operations
  async executeCommand(command: string, params: Record<string, unknown>)
  async createObject(type: string, properties: Record<string, string>)
  async createEdge(source: string, target: string, predicate: string)
  async sparql(query: string)
  async inviteUser(email: string, role?: string)
}
```

Use `ApiClient` for test arrangement (creating test data) rather than driving the UI. This decouples data setup from UI interaction and prevents test fragility.

## Selectors

`e2e/helpers/selectors.ts` exports a `SEL` object with all shared selectors:

```typescript
export const SEL = {
  // Auth pages
  setupForm: '[data-testid="setup-form"]',
  loginForm: '[data-testid="login-form"]',

  // Workspace layout
  workspaceContainer: '[data-testid="workspace-container"]',
  editorArea: '[data-testid="editor-area"]',

  // Navigation tree
  navTree: '[data-testid="nav-tree"]',
  navTypeNode: '[data-testid="nav-type-node"]',
  sidebarToggle: '.sidebar-toggle',  // No data-testid; uses CSS class

  // Views
  cards: '.card-grid',  // No data-testid; uses CSS class

  // ...
}
```

**Selector preference order:**
1. `data-testid` attribute (most stable)
2. Semantic role/label selectors
3. CSS class selectors (fallback when `data-testid` not present)

## htmx Wait Helpers

Since the UI uses htmx partial swaps instead of SPA navigation, `e2e/helpers/wait-for.ts` provides specialized wait functions:

```typescript
// Wait for an htmx swap to settle on a target element
export async function waitForHtmxSettle(page: Page, selector: string, timeoutMs = 10000)

// Wait for an element to appear after an htmx swap
export async function waitForElement(page: Page, selector: string, timeoutMs = 10000)

// Wait for text content to appear after an htmx swap
export async function waitForText(page: Page, text: string, timeoutMs = 10000)

// Wait for workspace to be fully loaded (workspace-container present + nav tree populated)
export async function waitForWorkspace(page: Page, timeoutMs = 15000)

// Wait for no active htmx requests (use before assertions)
export async function waitForIdle(page: Page, timeoutMs = 10000)
```

**Usage pattern:** Call `waitForIdle()` or `waitForWorkspace()` before making assertions when the test has triggered an htmx request:

```typescript
test('table view loads data rows', async ({ ownerPage }) => {
  await ownerPage.goto('/');
  await waitForWorkspace(ownerPage);
  // click nav item to trigger htmx load
  await ownerPage.click(SEL.tableViewLink);
  await waitForIdle(ownerPage);
  // now safe to assert
  const rows = ownerPage.locator('[data-testid="table-row"]');
  await expect(rows).toHaveCountGreaterThan(0);
});
```

## Seed Data Constants

`e2e/fixtures/seed-data.ts` exports typed constants matching the Basic PKM seed data:

```typescript
/** Total counts for assertions */
export const COUNTS = { notes: N, projects: N, concepts: N, persons: N };

/** Known seed object IRIs and titles */
export const SEED = {
  notes: { architectureDecision: { iri: '...', title: '...' }, ... },
  projects: { semPkmDevelopment: { iri: '...', title: '...' }, ... },
  // ...
};

/** Basic PKM type IRIs */
export const TYPES = {
  note: 'urn:sempkm:model:basic-pkm:Note',
  project: '...',
  // ...
};
```

Use these constants in tests instead of hardcoding IRI strings. This ensures tests break with clear errors if seed data changes.

## Playwright Configuration

Key settings in `e2e/playwright.config.ts`:

```typescript
// Sequential execution — app is stateful, tests share Docker stack
workers: 1,
fullyParallel: false,

// Retry once for flaky htmx timing
retries: 1,

// Generous timeouts for Docker-based tests
timeout: 60_000,         // Per-test timeout
actionTimeout: 15_000,   // Per-action timeout

// Artifacts on failure
screenshot: 'only-on-failure',
video: 'on-first-retry',
trace: 'on-first-retry',

// Global setup verifies Docker stack health
globalSetup: './fixtures/test-harness.ts',
```

**Two Playwright projects:**
- `chromium` — runs all tests in `tests/` (default: `npm test`)
- `screenshots` — runs only `tests/screenshots/capture.spec.ts`; no retries for deterministic output

## Mocking

**No mocking used.** Tests run against a live Docker test stack (`docker-compose.test.yml`) on port 3901. There is no stubbing of network requests or services.

**Test isolation:** The Docker stack uses separate volumes (`docker-compose.test.yml`) from the development stack. Tests are sequential and share a single stack instance. State accumulates across tests within a session — tests must account for seed data and data created by earlier tests.

**Fire-and-forget operations:** Some test assertions use `waitForTimeout()` explicitly to wait for async backend processes (e.g., SHACL validation queue):

```typescript
await ownerPage.waitForTimeout(3000); // Allow time for async validation
await ownerPage.waitForTimeout(5000); // Allow async validation to complete
```

This is acceptable but fragile. Prefer `waitForIdle()` when possible.

## Coverage

**Requirements:** None enforced. No coverage configuration exists.

**Backend (Python):**
- `pytest` + `pytest-asyncio` are declared as dev dependencies but no test files exist
- Zero unit test coverage of backend Python code
- All backend behavior is validated through E2E tests only

**E2E (Playwright):**
- 118/123 tests passing as of 2026-02-25 with `npx playwright test --project=chromium`
- 5 failing tests (`00-setup/01-setup-wizard.spec.ts`) require a fresh Docker stack
- No coverage reporting configured

## Test Types

**E2E Tests (only test type in use):**
- Scope: Full browser automation against a live Docker stack
- Location: `e2e/tests/`
- Run command: `npx playwright test --project=chromium` from `e2e/`
- Covers: Auth flows, object CRUD, view rendering, navigation, admin, settings, multi-user

**Screenshot Tests (separate project):**
- Scope: Marketing screenshot capture — not assertions, but UI state documentation
- Location: `e2e/tests/screenshots/capture.spec.ts`
- Run command: `npx playwright test --project=screenshots` from `e2e/`
- Output: `e2e/screenshots/*.png` (committed to repo)

**Unit Tests:** Not implemented. Infrastructure (pytest/pytest-asyncio) declared but unused.
**Integration Tests:** Not implemented separately — covered by E2E tests.

## Common Patterns

**Async Testing (TypeScript):**
```typescript
test('loads table view', async ({ ownerPage }) => {
  await ownerPage.goto('/');
  await waitForWorkspace(ownerPage);
  await ownerPage.click(SEL.tableViewLink);
  await waitForIdle(ownerPage);
  await expect(ownerPage.locator(SEL.tableRow)).toHaveCountGreaterThan(0);
});
```

**API-First Test Arrangement:**
```typescript
test('patch persists after reload', async ({ ownerPage }) => {
  // Arrange via API (fast, reliable)
  const client = new ApiClient(ownerPage.request);
  const { iri } = await client.createObject(TYPES.note, { title: 'Test Note' });

  // Act via UI
  await ownerPage.goto(`/?iri=${encodeURIComponent(iri)}`);
  await waitForWorkspace(ownerPage);
  // ... UI interaction
});
```

**Counting Seed Objects:**
```typescript
// Use COUNTS constants rather than hardcoded numbers
const count = await ownerPage.locator(SEL.navTypeNode).count();
expect(count).toBeGreaterThanOrEqual(4); // Note, Concept, Project, Person
```

**Error State Testing:**
```typescript
test('rejects invalid setup token', async ({ anonApi }) => {
  const resp = await anonApi.setup('invalid-token');
  expect(resp.status()).toBe(401);
});
```

---

*Testing analysis: 2026-02-25*
