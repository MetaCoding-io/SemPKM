# Phase 34: E2E Test Coverage - Research

**Researched:** 2026-03-03
**Domain:** Playwright E2E testing for htmx + dockview-core web application
**Confidence:** HIGH

## Summary

Phase 34 requires two categories of work: (1) fix existing tests that use `test.skip()` conditional guards for features that are now live (SPARQL console, FTS search, WebDAV VFS), and (2) write new Playwright tests for v2.3 features added in phases 29-33 (dockview panel management, carousel view switching, fuzzy FTS toggle, named layout save/restore).

The existing test infrastructure is mature and well-structured. Playwright 1.58.2 is installed with a sequential single-worker configuration running against a Docker stack on port 3901. Authentication fixtures, wait helpers, seed data constants, dockview helpers, and CSS selectors are all established. The test patterns are consistent: import from `../../fixtures/auth`, use `ownerPage` fixture, navigate to workspace, use `window._dockview` and `window.openTab()` APIs for programmatic panel/tab operations.

The key challenge is that the three "skip" test files have different skip patterns. The SPARQL console test (`sparql-console.spec.ts`) was deleted from the working tree but exists in HEAD -- it tests a Yasgui embed in the workspace bottom panel, but the actual SPARQL console is an admin-side page at `/admin/sparql`. The tests need to be rewritten to match the real implementation. The FTS search tests (`08-search/fts-search.spec.ts`) already have no `test.skip()` calls and may already pass. The VFS WebDAV tests (`vfs-webdav.spec.ts`) have conditional skips based on 404/403 responses -- since the `/dav/` endpoint is now live with wsgidav, these guards should be removed or converted to hard assertions.

**Primary recommendation:** Structure work into three plans: (1) fix SPARQL/FTS/VFS existing skipped tests, (2) write new v2.3 feature tests, organized to match existing test directory conventions.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | Playwright E2E tests for SPARQL console operations pass against live stack (no `test.skip()`) | SPARQL admin page at `/admin/sparql` uses Yasgui with `/api/sparql` POST endpoint. Old tests targeted non-existent bottom-panel embed -- must be rewritten to test actual admin page. See Architecture Patterns: SPARQL Console Testing. |
| TEST-02 | Playwright E2E tests for FTS keyword search pass against live stack (no `test.skip()`) | FTS tests at `08-search/fts-search.spec.ts` already have no `test.skip()`. Verify they pass, then add fuzzy toggle coverage per TEST-04. API: `GET /api/search?q=...&fuzzy=true`. See Code Examples: FTS and Fuzzy Toggle. |
| TEST-03 | Playwright E2E tests for WebDAV VFS operations pass against live stack (no `test.skip()`) | VFS WebDAV at `/dav/` is live (wsgidav mounted in main.py, nginx proxies /dav/). Tests use `ownerSessionToken` but wsgidav uses Basic auth via `SemPKMWsgiAuthenticator`. Must verify auth mechanism and remove conditional skips. See Architecture Patterns: VFS WebDAV Testing. |
| TEST-04 | Playwright E2E tests cover all v2.3 user-visible features (dockview panels, carousel view switching, fuzzy FTS, named layout save/restore) | New tests needed in directories matching convention. Dockview helper at `helpers/dockview.ts` provides `openObjectTab`, `openViewTab`, `getTabCount`. Named layouts API: `window.SemPKMLayouts.{save,restore,list,remove}`. Carousel: `.carousel-tab-bar` with `switchCarouselView()`. Fuzzy: `search-fuzzy-toggle` command in ninja-keys. See Code Examples. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | 1.58.2 | E2E browser testing framework | Already installed and configured in project |
| typescript | ^5.7.0 | Test file language | Already configured with tsconfig.json |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @types/node | ^25.3.0 | Node.js type definitions | Already installed |

### Alternatives Considered
None -- the test stack is already established. No new dependencies needed.

**Installation:** No new packages required. Everything is in place.

## Architecture Patterns

### Existing Test Directory Structure
```
e2e/
├── fixtures/
│   ├── auth.ts              # ownerPage, memberPage, ownerSessionToken fixtures
│   ├── seed-data.ts         # SEED constants, TYPES constants
│   └── test-harness.ts      # Global setup: health check
├── helpers/
│   ├── api-client.ts        # ApiClient class for direct API calls
│   ├── dockview.ts          # openObjectTab, openViewTab, getTabCount, etc.
│   ├── selectors.ts         # SEL constant with CSS selectors
│   └── wait-for.ts          # waitForWorkspace, waitForIdle, waitForHtmxSettle
├── tests/
│   ├── 00-setup/            # Setup wizard, magic link login
│   ├── 01-objects/          # CRUD, edit UI, object view redesign
│   ├── 02-views/            # Table, cards, graph views
│   ├── 03-navigation/       # Nav tree, tabs, split panes, layout
│   ├── 04-validation/       # Lint panel
│   ├── 05-admin/            # Models, webhooks, access control
│   ├── 06-settings/         # Settings, dark mode, tutorials
│   ├── 07-multi-user/       # Member permissions, sessions
│   ├── 08-search/           # FTS search (already exists)
│   ├── screenshots/         # Screenshot capture
│   └── vfs-webdav.spec.ts   # VFS WebDAV (root-level, not in subdirectory)
└── playwright.config.ts     # Sequential, single-worker, port 3901
```

### Pattern 1: Standard Test File Structure
**What:** Every test file follows the same import/fixture/pattern convention.
**When to use:** All new test files.
**Example:**
```typescript
// Source: existing pattern from e2e/tests/08-search/fts-search.spec.ts
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Feature Name', () => {
  test('specific behavior under test', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    // ... test body
  });
});
```

### Pattern 2: Dockview Panel Interaction via window APIs
**What:** Tests interact with dockview panels via `window._dockview` and application globals like `window.openTab()`, `window.SemPKMLayouts`, etc.
**When to use:** Any test that needs to open objects, views, or manipulate the workspace layout.
**Example:**
```typescript
// Source: existing pattern from e2e/tests/03-navigation/tab-management.spec.ts
await ownerPage.evaluate((iri) => {
  if (typeof (window as any).openTab === 'function') {
    (window as any).openTab(iri, 'Architecture Decision');
  }
}, SEED.notes.architecture.iri);
await waitForIdle(ownerPage);

// Verify tab appeared
const tabs = ownerPage.locator('.dv-default-tab');
await expect(tabs.first()).toBeVisible({ timeout: 10000 });
```

### Pattern 3: Admin Page Navigation (for SPARQL console)
**What:** The SPARQL console is at `/admin/sparql`, NOT in the workspace bottom panel. Tests must navigate there.
**When to use:** TEST-01 SPARQL tests.
**Example:**
```typescript
// Navigate to admin SPARQL console
await ownerPage.goto(`${BASE_URL}/admin/sparql`);
// Wait for Yasgui to initialize (it loads asynchronously from CDN)
await ownerPage.waitForSelector('#yasgui-admin .yasgui', { timeout: 15000 });
```

### Pattern 4: Carousel View Tab Switching
**What:** Object types with multiple views show `.carousel-tab-bar` with `.carousel-tab` buttons. Clicking switches the view body via htmx.
**When to use:** TEST-04 carousel view tests.
**Example:**
```typescript
// After opening a view that has multiple specs (e.g., Note type has table, card, graph)
const carouselBar = ownerPage.locator('.carousel-tab-bar');
await expect(carouselBar).toBeVisible();

// Click a different tab
const tabs = carouselBar.locator('.carousel-tab');
const secondTab = tabs.nth(1);
await secondTab.click();
await waitForIdle(ownerPage);

// Verify active tab changed
await expect(secondTab).toHaveClass(/active/);
```

### Pattern 5: Named Layout Save/Restore via window.SemPKMLayouts
**What:** Named layouts use `window.SemPKMLayouts` API backed by localStorage.
**When to use:** TEST-04 named layout tests.
**Example:**
```typescript
// Save current layout
const saved = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.save('Test Layout');
});
expect(saved).toBe(true);

// Verify layout is in the list
const layouts = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.list();
});
expect(layouts).toContainEqual(expect.objectContaining({ name: 'Test Layout' }));

// Restore a layout
const result = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.restore('Test Layout');
});
expect(result.success).toBe(true);
```

### SPARQL Console Testing Strategy
**What:** The old `sparql-console.spec.ts` tested a Yasgui embed in the workspace bottom panel that never existed. The actual SPARQL console lives at `/admin/sparql` as a full-page Yasgui instance configured with endpoint `/api/sparql` (POST method).
**Architecture details:**
- Yasgui CDN: `@zazuko/yasgui@4.5.0` (not the original Triply Yasgui)
- Container: `#yasgui-admin`
- Endpoint config: `{ endpoint: '/api/sparql', method: 'POST' }`
- Persistence: localStorage key `sempkm-sparql`
- Custom formatter: SemPKM object IRIs render as clickable links that call `window.openTab()`
- The admin SPARQL page requires owner role authentication

**Test approach:** Navigate to `/admin/sparql`, wait for Yasgui init, type a query, execute it, verify results. The old bottom-panel approach is completely wrong.

### VFS WebDAV Testing Strategy
**What:** The WebDAV endpoint at `/dav/` is live. Auth uses `SemPKMWsgiAuthenticator` which appears to accept session cookies forwarded by nginx.
**Key details from code:**
- The wsgidav app is mounted at `/dav` in FastAPI's main.py
- nginx proxies `/dav/` to the API with `proxy_pass_header Authorization`
- The auth config: `"domain_controller": SemPKMWsgiAuthenticator`
- The VFS tests use `ownerPage.context().request.fetch()` with cookie-based auth
- Current test skip conditions check for 404/403 -- with VFS live, these should now pass or need auth adjustment

**Important:** The VFS tests use HTTP verbs (OPTIONS, PROPFIND, GET, PUT) via `request.fetch()`, not browser navigation. The auth mechanism in the tests sends the session cookie via header. Need to verify this works with the wsgidav authenticator.

### Anti-Patterns to Avoid
- **Conditional `test.skip()` for features that exist:** The whole point of Phase 34 is to remove these. Tests should assert directly; if the feature is broken, the test should FAIL, not skip.
- **Duplicate `goto()` + `waitForWorkspace()` per test:** Use `test.beforeEach()` when all tests in a describe block share the same navigation.
- **Hardcoded waits instead of selectors:** Use `waitForSelector`, `waitForIdle`, or `waitForFunction` instead of `waitForTimeout` where possible. Existing tests use `waitForTimeout` in some places -- acceptable for debounce timing but prefer event-driven waits.
- **Testing via CSS classes that could change:** Prefer `data-testid` attributes where they exist (see `selectors.ts`). For dockview internals, `.dv-default-tab` and `.dv-active-tab` are stable public CSS classes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser auth setup | Custom cookie injection | `fixtures/auth.ts` ownerPage fixture | Already handles magic link flow, cookie injection, session management |
| Dockview panel operations | Direct DOM manipulation | `helpers/dockview.ts` helpers | Already wraps window._dockview API calls with proper waits |
| Workspace ready detection | `page.waitForTimeout(5000)` | `waitForWorkspace(page)` from helpers | Waits for `.workspace-container` to be attached |
| htmx idle detection | Manual polling | `waitForIdle(page)` from helpers | Watches for `.htmx-request` class removal |
| Seed data constants | Hardcoded IRIs/titles | `SEED` and `TYPES` from `fixtures/seed-data.ts` | Single source of truth for test data |

**Key insight:** The existing test infrastructure is comprehensive. Phase 34 should use existing helpers, not create new abstractions. The only possible new helper would be for command palette interaction (opening, typing, selecting items).

## Common Pitfalls

### Pitfall 1: SPARQL Console Test Targeting Wrong Page
**What goes wrong:** The deleted `sparql-console.spec.ts` tested for Yasgui in `#panel-sparql` (workspace bottom panel) which does not exist. The bottom panel only has EVENT LOG and AI COPILOT.
**Why it happens:** The old tests were written speculatively before the feature was implemented. The SPARQL console ended up as an admin page, not a bottom panel tab.
**How to avoid:** Test the actual `/admin/sparql` page where Yasgui is rendered in `#yasgui-admin`.
**Warning signs:** Tests looking for `#panel-sparql`, `.yasqe` in the workspace, or `.panel-tab[data-panel="sparql"]`.

### Pitfall 2: WebDAV Auth Mismatch
**What goes wrong:** VFS tests send session cookie but wsgidav may use Basic auth via `SemPKMWsgiAuthenticator`. If the authenticator only checks Basic auth headers, cookie-based requests will get 401.
**Why it happens:** wsgidav has its own auth layer separate from FastAPI's session middleware.
**How to avoid:** Check `vfs/auth.py` to verify the authenticator accepts session cookies forwarded in the Cookie header. If not, tests may need to use Basic auth or the auth may need examination.
**Warning signs:** 401/403 responses despite valid session cookie.

### Pitfall 3: Yasgui CDN Load Timing
**What goes wrong:** Yasgui loads from unpkg CDN asynchronously. Tests that assert on `.yasgui` or `.yasqe` classes before Yasgui initializes will fail.
**Why it happens:** The admin SPARQL page uses `setTimeout(initYasgui, 0)` and retries with `setTimeout(initYasgui, 200)` until the CDN script loads.
**How to avoid:** Use generous timeout (15s) when waiting for Yasgui container. Wait for `#yasgui-admin .yasgui` which only exists after initialization.
**Warning signs:** Intermittent failures with "element not found" for Yasgui selectors.

### Pitfall 4: Ninja-Keys Shadow DOM for Command Palette Tests
**What goes wrong:** `ninja-keys` is a web component with shadow DOM. Direct `page.locator('input')` won't find the search input inside it.
**Why it happens:** Shadow DOM encapsulation hides internal elements from standard selectors.
**How to avoid:** Use `page.evaluate()` to interact with ninja-keys internals, or use `page.keyboard.type()` after opening the palette (ninja-keys captures keyboard input). Existing FTS tests use `page.keyboard.type()` successfully.
**Warning signs:** "input not found" errors when trying to type in the command palette.

### Pitfall 5: Carousel View Requires Types with Multiple View Specs
**What goes wrong:** Carousel tab bar only renders when `all_specs|length > 1`. If a type has only one view spec, no carousel bar appears.
**Why it happens:** The template conditionally renders the carousel: `{% if all_specs|length > 1 %}`.
**How to avoid:** Use view types that the Basic PKM model defines multiple specs for. Check `/browser/views/available` API to find types with multiple renderers.
**Warning signs:** Tests looking for `.carousel-tab-bar` but finding none because the opened type has only one view.

### Pitfall 6: Sequential Test Execution and State Leaks
**What goes wrong:** Tests run sequentially with shared Docker state. localStorage, dockview layout state, or created objects persist between tests.
**Why it happens:** Single-worker mode with no test isolation beyond page-level.
**How to avoid:** Each test should navigate fresh (`ownerPage.goto()`). For localStorage-dependent tests, explicitly clear relevant keys at test start. Named layout tests should clean up created layouts.
**Warning signs:** Tests pass in isolation but fail when run as part of the full suite.

## Code Examples

Verified patterns from the existing codebase:

### Opening the Command Palette and Typing a Search
```typescript
// Source: e2e/tests/08-search/fts-search.spec.ts lines 42-53, 56-77
await ownerPage.keyboard.press('Control+k');
await ownerPage.waitForTimeout(500);

// Type into ninja-keys (captures keyboard input in its shadow DOM input)
await ownerPage.keyboard.type('note', { delay: 50 });

// Wait for debounce (300ms) + fetch
await ownerPage.waitForTimeout(800);
```

### Verifying Fuzzy Toggle Command in Palette
```typescript
// Source: workspace.js lines 1119-1131
// The fuzzy toggle command has id 'search-fuzzy-toggle' and section 'Search'
const hasFuzzyToggle = await ownerPage.evaluate(() => {
  const ninja = document.querySelector('ninja-keys') as any;
  if (!ninja || !ninja.data) return false;
  return ninja.data.some((d: any) => d.id === 'search-fuzzy-toggle');
});
expect(hasFuzzyToggle).toBe(true);
```

### Toggling Fuzzy and Verifying API Call Includes fuzzy=true
```typescript
// Source: workspace.js lines 1125-1129, 1148-1151
// Toggle fuzzy ON
await ownerPage.evaluate(() => {
  const ninja = document.querySelector('ninja-keys') as any;
  const toggle = ninja.data.find((d: any) => d.id === 'search-fuzzy-toggle');
  if (toggle && toggle.handler) toggle.handler();
});

// Intercept search request to verify fuzzy param
let fuzzyParamSent = false;
await ownerPage.route('**/api/search*', async (route) => {
  const url = route.request().url();
  if (url.includes('fuzzy=true')) fuzzyParamSent = true;
  await route.continue();
});
```

### Named Layout Save/Restore via API
```typescript
// Source: frontend/static/js/named-layouts.js
// Save
const saved = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.save('My Layout');
});
expect(saved).toBe(true);

// List
const layouts = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.list();
});
expect(layouts.length).toBeGreaterThan(0);

// Restore
const result = await ownerPage.evaluate(() => {
  return (window as any).SemPKMLayouts.restore('My Layout');
});
expect(result.success).toBe(true);

// Delete (cleanup)
await ownerPage.evaluate(() => {
  (window as any).SemPKMLayouts.remove('My Layout');
});
```

### Named Layout Command Palette Integration
```typescript
// Source: workspace.js lines 970-1005
// The command palette has these layout commands:
// - 'layout-save-as' (section: 'Layout') - parent with child 'layout-save-confirm'
// - 'layout-restore' (section: 'Layout') - parent with dynamic children 'layout-restore-{name}'

// Verify layout commands exist in palette
const hasLayoutCommands = await ownerPage.evaluate(() => {
  const ninja = document.querySelector('ninja-keys') as any;
  if (!ninja || !ninja.data) return false;
  return ninja.data.some((d: any) => d.id === 'layout-save-as') &&
         ninja.data.some((d: any) => d.id === 'layout-restore');
});
expect(hasLayoutCommands).toBe(true);
```

### Opening Dockview Panels and Checking State
```typescript
// Source: e2e/helpers/dockview.ts and e2e/tests/03-navigation/split-panes.spec.ts
// Wait for dockview initialization
await ownerPage.waitForFunction(() => {
  return (window as any)._dockview != null;
}, { timeout: 5000 });

// Get panel/group counts
const panelCount = await ownerPage.evaluate(() => {
  const dv = (window as any)._dockview;
  return dv ? dv.panels.length : 0;
});

const groupCount = await ownerPage.evaluate(() => {
  const dv = (window as any)._dockview;
  return dv ? dv.groups.length : 0;
});
```

### WebDAV PROPFIND Request Pattern
```typescript
// Source: e2e/tests/vfs-webdav.spec.ts lines 47-73
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
// Should return 207 Multi-Status (no longer skip on 404)
expect(resp.status()).toBe(207);
```

### Admin SPARQL Console Page
```typescript
// Source: backend/app/templates/admin/sparql.html
// Navigate to admin SPARQL page (requires owner role)
await ownerPage.goto(`${BASE_URL}/admin/sparql`);

// Wait for Yasgui to initialize from CDN
await ownerPage.waitForFunction(() => {
  const container = document.getElementById('yasgui-admin');
  return container && (container as any)._yasguiInstance != null;
}, { timeout: 15000 });

// Yasgui container should be visible
await expect(ownerPage.locator('#yasgui-admin .yasgui')).toBeVisible();
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `test.skip()` conditional guards for unimplemented features | Direct assertions (feature is live) | Phase 34 | Tests fail on regression instead of silently skipping |
| SPARQL in workspace bottom panel | SPARQL as admin page at `/admin/sparql` | Phase 23 implementation | Tests must navigate to admin page, not workspace |
| Split.js for editor panes | dockview-core 4.11.0 | Phase 30 | Tab selectors changed from custom to `.dv-default-tab`, `.dv-active-tab` |
| Single view per type | Carousel tab bar for multi-view types | Phase 32 | New `.carousel-tab-bar` and `.carousel-tab` selectors |
| Session-only layout | Named layouts in localStorage | Phase 33 | `window.SemPKMLayouts` API available for test interaction |
| Exact-only FTS | Fuzzy toggle in command palette | Phase 29 | `search-fuzzy-toggle` command, `&fuzzy=true` API param |

**Deprecated/outdated:**
- `sparql-console.spec.ts` at tests root: Was deleted from working tree. Based on incorrect assumption about SPARQL location. Must be rewritten for `/admin/sparql`.
- `fts-search.spec.ts` at tests root: Was deleted from working tree. Superseded by `08-search/fts-search.spec.ts`.

## Existing Skip Analysis

### Files with `test.skip()` calls that need resolution:

**1. `e2e/tests/vfs-webdav.spec.ts` (16 skip calls)**
- All skips are conditional: `if (resp.status() === 404) test.skip(...)` or `if (resp.status() === 401) test.skip(...)`
- With VFS live, 404 skips should no longer trigger
- Auth (401/403) skips need investigation: does wsgidav accept session cookies?
- **Action:** Remove all conditional skips. If auth fails, fix auth mechanism or adjust test auth approach.

**2. `e2e/tests/02-views/cards-view.spec.ts` (4 skip calls)**
- All skips are: `if (!cardSpec) { test.skip(); return; }` -- skip if no card view spec exists
- These are feature-detection skips, not "not implemented" skips
- With Basic PKM model installed, card specs SHOULD exist
- **Action:** Verify card spec exists in seed data. If it does, convert to hard assertion. If not, these are valid feature guards.

**3. `e2e/tests/02-views/graph-view.spec.ts` (4 skip calls)**
- Same pattern as cards: `if (!graphSpec) { test.skip(); return; }`
- **Action:** Same as cards -- verify spec exists, convert to assertion if it does.

**4. `e2e/tests/sparql-console.spec.ts` (deleted from working tree)**
- Was at root of tests/, tested non-existent bottom panel SPARQL
- All tests had multiple `test.skip()` paths for Yasgui/CodeMirror elements not found
- **Action:** Must create new file testing the actual admin SPARQL page. Place in `tests/05-admin/` directory.

### Files with NO skip calls (already clean):
- `e2e/tests/08-search/fts-search.spec.ts` -- 7 tests, no skips
- All `01-objects/`, `03-navigation/`, `04-validation/`, `06-settings/`, `07-multi-user/` tests

## New Test Coverage Needed (TEST-04)

### Dockview Panel Management
- Opening panels via `openTab()`, `openViewTab()`
- Panel count tracking (`dv.panels.length`)
- Active panel detection (`dv.activePanel`)
- Panel close behavior
- Note: Much of this is already covered in `03-navigation/tab-management.spec.ts` and `03-navigation/split-panes.spec.ts`. Focus on behaviors not yet tested.

### Carousel View Switching
- `.carousel-tab-bar` renders for multi-view types
- Clicking a `.carousel-tab` switches the view body
- Active tab class updates
- `sempkm_carousel_view` localStorage persistence
- View content actually changes after switch

### Fuzzy FTS Toggle
- `search-fuzzy-toggle` command exists in ninja-keys data
- Toggling changes the command title
- `sempkm_fts_fuzzy` localStorage persists toggle state
- Search request includes `&fuzzy=true` when enabled
- Fuzzy results differ from exact results for typo queries

### Named Layout Save/Restore
- `SemPKMLayouts.save()` stores layout in localStorage
- `SemPKMLayouts.list()` returns saved layouts
- `SemPKMLayouts.restore()` applies layout to dockview
- `SemPKMLayouts.remove()` deletes layout
- Command palette has `layout-save-as` and `layout-restore` commands
- Restore after opening tabs recreates the workspace state

## Open Questions

1. **WebDAV auth mechanism for tests**
   - What we know: wsgidav uses `SemPKMWsgiAuthenticator`, tests send session cookie via Cookie header
   - What's unclear: Does the authenticator accept session cookies, or only Basic auth? The existing tests' 401 skip paths suggest cookie auth may not work.
   - Recommendation: Read `vfs/auth.py` during implementation. If cookie auth works, remove skips. If Basic auth required, use `ownerPage.context().request` with Basic auth headers instead.

2. **View specs available for carousel testing**
   - What we know: Basic PKM model has Note, Concept, Project, Person types. View specs include table, card, graph renderers.
   - What's unclear: Do all types have multiple view specs, or only some? The carousel bar only shows for types with >1 spec.
   - Recommendation: Use `/browser/views/available` API to discover which types have multiple specs. The existing card/graph view tests already use this pattern.

3. **SPARQL admin page auth flow in tests**
   - What we know: Admin SPARQL page requires owner role (`require_role("owner")` on the route). The `ownerPage` fixture has owner session.
   - What's unclear: Whether navigating to `/admin/sparql` via `ownerPage.goto()` will work (it should since cookie is set).
   - Recommendation: Test navigation first. The admin sidebar link uses htmx, but direct URL navigation should also work.

## Sources

### Primary (HIGH confidence)
- Project codebase inspection: `e2e/` directory structure, all test files, helpers, fixtures
- `backend/app/templates/admin/sparql.html` -- actual SPARQL console implementation
- `backend/app/main.py` -- WebDAV mount at `/dav`
- `frontend/static/js/workspace.js` -- fuzzy toggle, carousel switching, command palette
- `frontend/static/js/named-layouts.js` -- named layouts API
- `backend/app/templates/browser/workspace.html` -- bottom panel structure (no SPARQL tab)

### Secondary (MEDIUM confidence)
- Playwright 1.58.2 installed version verified via `npx playwright --version`
- `@zazuko/yasgui@4.5.0` CDN version from admin/sparql.html template

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - exact versions verified from package.json and node_modules
- Architecture: HIGH - all patterns derived from reading actual test files and application code
- Pitfalls: HIGH - identified from concrete analysis of existing skip patterns and actual vs expected implementations
- New test coverage: HIGH - feature implementations verified in source code

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- test infrastructure and features are implemented)
