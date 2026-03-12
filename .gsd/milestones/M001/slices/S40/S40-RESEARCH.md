# Phase 40: E2E Test Coverage for v2.4 - Research

**Researched:** 2026-03-05
**Domain:** Playwright E2E testing for htmx + dockview workspace UI
**Confidence:** HIGH

## Summary

Phase 40 is pure test authoring -- no feature work. The existing E2E infrastructure (Playwright 1.50+, auth fixtures, seed data, dockview helpers, wait helpers) is mature with 124/129 passing tests. New tests must follow established patterns: sequential execution, single worker, `ownerPage` fixture, `waitForIdle()` after htmx actions, and `page.evaluate()` for calling workspace JS APIs.

The key challenge is testing v2.4 features that involve asynchronous processing (inference runs, async validation) and bottom-panel interactions (inference panel, lint dashboard). Tests must account for htmx lazy-loading (`hx-trigger="revealed"`), SSE-based updates, and the panel tab switching mechanism. All target UI elements have been identified with their CSS selectors and DOM structure.

**Primary recommendation:** Create 4 new test directories (`09-inference/`, `10-lint-dashboard/`, `11-helptext/`, `12-bug-fixes/`) following existing numbered conventions. Use API client for test setup (create edges, trigger inference) and UI assertions for verification.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New numbered directories for major features: `09-inference/`, `10-lint-dashboard/`
- Helptext tests in a new `11-helptext/` directory or extend `01-objects/` -- Claude's discretion
- Bug verification tests in a single `bug-fixes.spec.ts` file (could go in `09-bug-fixes/` or similar)
- All tests run under the existing `chromium` Playwright project -- no separate project config
- Use existing seed data from `fixtures/seed-data.ts`; inference tests create edges and trigger inference to verify
- Functional assertions only for bug tests -- no dual-theme testing (test in default theme only)
- Admin entailment config toggle testing -- DEFERRED to a later phase

### Claude's Discretion
- Exact test file naming and directory placement within the numbered structure
- Which seed objects to use for each test scenario
- Whether to add new seed data fixtures or reuse existing ones
- Assertion strategies (CSS property checks, data attribute checks, text content checks)
- Test ordering and any shared setup between test files
- Whether lint dashboard tests need to trigger validation first or rely on existing state

### Deferred Ideas (OUT OF SCOPE)
- Admin entailment config toggle testing -- deferred to a later E2E phase
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-05 | Playwright E2E tests cover all v2.4 user-visible features (inference bidirectional links, lint dashboard filtering/sorting, edit form helptext, bug fix verifications) | Full selector mapping, API endpoints, DOM structure, and test patterns documented below |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | ^1.50.0 | E2E test framework | Already installed and configured |
| TypeScript | ^5.7.0 | Test authoring language | Existing convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Custom auth fixtures | N/A | `ownerPage`, `ownerSessionToken`, `anonApi` | Every test file |
| Custom seed-data | N/A | `SEED` constants, `TYPES` constants | Referencing known objects |
| Custom selectors | N/A | `SEL` constants | Common UI element targeting |
| Custom wait helpers | N/A | `waitForIdle()`, `waitForWorkspace()` | After htmx interactions |
| Custom dockview helpers | N/A | `openObjectTab()`, `openViewTab()` | Opening tabs programmatically |
| Custom api-client | N/A | `ApiClient` with `createEdge()`, `executeCommand()` | Test data arrangement via API |

### No New Dependencies Needed
All required infrastructure exists. No npm installs necessary.

## Architecture Patterns

### Test Directory Structure
```
e2e/tests/
├── 09-inference/
│   └── inference.spec.ts          # OWL inference + SHACL-AF rules
├── 10-lint-dashboard/
│   └── lint-dashboard.spec.ts     # Global lint dashboard UI
├── 11-helptext/
│   └── helptext.spec.ts           # Edit form helptext toggle/render
└── 12-bug-fixes/
    └── bug-fixes.spec.ts          # BUG-04 through BUG-09 regressions
```

### Pattern 1: Bottom Panel Interaction
**What:** Opening bottom panel and switching to a specific tab
**When to use:** Inference panel tests, lint dashboard tests
**Example:**
```typescript
// Source: workspace.js panel tab logic + workspace.html template
// Open bottom panel and switch to inference tab
await ownerPage.evaluate(() => {
  // Ensure panel is open
  const panel = document.getElementById('bottom-panel');
  if (panel && panel.style.height === '0px' || !panel?.style.height) {
    (window as any).toggleBottomPanel();
  }
});

// Click the inference tab
await ownerPage.click('.panel-tab[data-panel="inference"]');
await waitForIdle(ownerPage);
```

### Pattern 2: Inference Run + Verify Flow
**What:** Trigger inference via API or UI, then verify results appear
**When to use:** Inference tests
**Example:**
```typescript
// Source: inference_panel.html, inference/router.py
// Create edge via API
const api = ownerPage.context().request;
await api.post(`${BASE_URL}/api/commands`, {
  headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
  data: {
    command: 'edge.create',
    params: {
      source: SEED.projects.sempkm.iri,
      target: SEED.people.alice.iri,
      predicate: 'http://purl.org/dc/terms/contributor',
    },
  },
});

// Trigger inference via API
await api.post(`${BASE_URL}/api/inference/run`, {
  headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
});

// Wait for inference to complete
await ownerPage.waitForTimeout(5000);

// Verify inferred triples appear in inference panel
const results = ownerPage.locator('#inference-results');
await expect(results).toContainText('owl:inverseOf');
```

### Pattern 3: Lint Dashboard Filter Interaction
**What:** Use lint dashboard filter dropdowns and verify results update
**When to use:** Lint dashboard tests
**Example:**
```typescript
// Source: lint_dashboard.html
// Switch to lint dashboard tab
await ownerPage.click('.panel-tab[data-panel="lint-dashboard"]');
await waitForIdle(ownerPage);

// Wait for htmx lazy-load (hx-trigger="revealed")
await ownerPage.waitForSelector('.lint-dashboard', { timeout: 15000 });

// Filter by severity
await ownerPage.selectOption('.lint-dashboard-filter-severity', 'Violation');
await waitForIdle(ownerPage);

// Verify filtered results
const rows = ownerPage.locator('.lint-dashboard-row');
```

### Pattern 4: Edit Form Helptext
**What:** Open object in edit mode, find helptext toggle, verify expand/collapse
**When to use:** Helptext tests
**Example:**
```typescript
// Source: object_form.html, _field.html
// Open object in edit mode
await ownerPage.evaluate(({ iri }) => {
  (window as any).openTab(iri, 'Test Object', 'edit');
}, { iri: SEED.notes.architecture.iri });

// Wait for form to render
await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });

// Check form-level helptext (if present)
const formHelptext = ownerPage.locator('.form-helptext-top');
// Check field-level helptext toggle button
const helpToggle = ownerPage.locator('.btn-helptext-toggle').first();
```

### Anti-Patterns to Avoid
- **Hard-coded waits without waitForIdle:** Always call `waitForIdle()` after htmx actions, supplement with `waitForTimeout()` only for async processes (inference, validation queue)
- **Direct DOM manipulation for assertions:** Use Playwright locators, not `page.evaluate()` for assertions
- **Skipping test isolation:** Tests are sequential and share state -- create test-specific objects via API when needed to avoid cross-test contamination
- **Polling for SSE updates:** Use `waitForTimeout()` with generous timeout rather than polling loops for async validation

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authentication | Custom cookie setup | `ownerPage` fixture from `auth.ts` | Handles setup, magic link, session cookies |
| Object creation for test data | Direct SPARQL inserts | `ApiClient.createObject()` / `ApiClient.createEdge()` | Matches real user flow, triggers validation |
| Tab opening | Direct htmx.ajax() calls | `openObjectTab()` from `dockview.ts` | Handles dockview panel lifecycle |
| Waiting for htmx | `page.waitForTimeout()` alone | `waitForIdle()` + timeout | More reliable, handles htmx-request class |

## Common Pitfalls

### Pitfall 1: htmx Lazy-Load Timing
**What goes wrong:** Bottom panel content not loaded because `hx-trigger="revealed"` only fires when element scrolls into view
**Why it happens:** Panel panes are hidden by default; switching tabs may not trigger "revealed"
**How to avoid:** After clicking a panel tab, wait for the actual content selector (e.g., `.lint-dashboard`, `.inference-panel`) rather than just the panel pane
**Warning signs:** Tests pass locally but fail in CI; empty panel content

### Pitfall 2: Inference Async Processing Time
**What goes wrong:** Assertions run before inference completes
**Why it happens:** `POST /api/inference/run` triggers owlrl computation which takes 2-5 seconds
**How to avoid:** Use `waitForTimeout(5000)` after triggering inference, then assert on results. Check `#inference-summary` for "N inferred triples" text
**Warning signs:** Flaky tests that pass on retry

### Pitfall 3: Bottom Panel Not Open
**What goes wrong:** Panel tab clicks do nothing because bottom panel has height 0
**Why it happens:** Bottom panel is collapsed by default; `_applyPanelState()` reads from localStorage
**How to avoid:** Always ensure panel is open before clicking tabs: check `panelState.open` or call `toggleBottomPanel()` if closed
**Warning signs:** Panel tab tests consistently fail

### Pitfall 4: Stale Lint Data
**What goes wrong:** Lint dashboard shows no results or stale results
**Why it happens:** Async validation queue processes after `EventStore.commit()`; no results until first object save
**How to avoid:** The test Docker stack should have seed data that triggered validation on initial setup. If not, create/save an object via API first, then wait for validation queue
**Warning signs:** `.lint-dashboard-empty` showing "No validation results yet"

### Pitfall 5: CSS Property Assertions
**What goes wrong:** `toHaveCSS()` fails due to computed vs. specified value differences
**Why it happens:** CSS variables resolve to computed values; `border-bottom-color` becomes rgb(), not hex or var()
**How to avoid:** Use `toHaveCSS()` with computed color values (rgb format), or check for existence of CSS class / data attribute instead of specific color values. For accent color tests, verify the accent is *different* between two types rather than checking exact color values
**Warning signs:** Tests with hard-coded hex color assertions

### Pitfall 6: Dockview Active Tab Class
**What goes wrong:** Wrong CSS class used for active tab assertions
**Why it happens:** Dockview uses `.dv-active-group` and `.dv-tab.dv-active-tab` (with hyphens, NOT `.dv-activegroup`)
**How to avoid:** Use exact selectors: `.dv-active-group .dv-tab.dv-active-tab`
**Warning signs:** Tab accent assertions always fail

## Code Examples

### Opening Bottom Panel and Switching Tabs
```typescript
// Verified from: workspace.js toggleBottomPanel(), initPanelTabs()
async function openBottomPanelTab(page: Page, tabName: string) {
  // Ensure bottom panel is visible
  await page.evaluate(() => {
    const panel = document.getElementById('bottom-panel');
    if (!panel) return;
    const h = panel.style.height;
    if (!h || h === '0px' || h === '0') {
      if (typeof (window as any).toggleBottomPanel === 'function') {
        (window as any).toggleBottomPanel();
      }
    }
  });
  // Click desired tab
  await page.click(`.panel-tab[data-panel="${tabName}"]`);
  await waitForIdle(page);
}
```

### Creating Edge and Triggering Inference
```typescript
// Verified from: api-client.ts, inference/router.py
async function createEdgeAndRunInference(
  page: Page,
  sessionToken: string,
  source: string,
  target: string,
  predicate: string,
) {
  const api = page.context().request;
  const baseUrl = process.env.TEST_BASE_URL || 'http://localhost:3901';

  // Create edge
  await api.post(`${baseUrl}/api/commands`, {
    headers: { Cookie: `sempkm_session=${sessionToken}` },
    data: {
      command: 'edge.create',
      params: { source, target, predicate },
    },
  });

  // Trigger inference
  await api.post(`${baseUrl}/api/inference/run`, {
    headers: { Cookie: `sempkm_session=${sessionToken}` },
  });

  // Wait for inference processing
  await page.waitForTimeout(5000);
}
```

### Asserting Inferred Badge Exists
```typescript
// Verified from: inference_triple_row.html
// Look for .inferred-badge elements with entailment type text
const badges = page.locator('.inferred-badge');
await expect(badges.first()).toBeVisible();
await expect(badges.first()).toContainText('owl:inverseOf');
```

### Asserting Lint Dashboard Filters Work
```typescript
// Verified from: lint_dashboard.html
// Select severity filter
await page.selectOption('.lint-dashboard-filter-severity', 'Violation');
await waitForIdle(page);

// Verify all visible rows have violation severity
const rows = page.locator('.lint-dashboard-row');
const count = await rows.count();
for (let i = 0; i < count; i++) {
  await expect(rows.nth(i)).toHaveClass(/lint-severity-violation/);
}
```

### Asserting Type-Specific Accent Color
```typescript
// Verified from: dockview-sempkm-bridge.css, workspace-layout.js
// Open two objects of different types
await page.evaluate(({ iri, label }) => {
  (window as any).openTab(iri, label);
}, { iri: SEED.notes.architecture.iri, label: 'Architecture' });
await waitForIdle(page);

// Get accent color for first type
const tab1Color = await page.evaluate(() => {
  const group = document.querySelector('.dv-active-group');
  return group ? getComputedStyle(group).getPropertyValue('--tab-accent-color').trim() : '';
});

// Open second type and compare
await page.evaluate(({ iri, label }) => {
  (window as any).openTab(iri, label);
}, { iri: SEED.people.alice.iri, label: 'Alice Chen' });
await waitForIdle(page);

const tab2Color = await page.evaluate(() => {
  const group = document.querySelector('.dv-active-group');
  return group ? getComputedStyle(group).getPropertyValue('--tab-accent-color').trim() : '';
});

// Colors should differ between types
expect(tab1Color).not.toBe(tab2Color);
```

### Asserting Helptext Toggle
```typescript
// Verified from: object_form.html, _field.html
// Form-level helptext uses <details> element
const formGuide = page.locator('.form-helptext-top');
if (await formGuide.count() > 0) {
  // Should be collapsed by default (details element without open attr)
  await expect(formGuide).not.toHaveAttribute('open');

  // Click summary to expand
  await page.click('.form-helptext-summary');
  await expect(formGuide).toHaveAttribute('open', '');
  await expect(page.locator('#helptext-form-rendered')).toBeVisible();
}

// Field-level helptext uses display:none toggle
const helpBtn = page.locator('.btn-helptext-toggle').first();
if (await helpBtn.count() > 0) {
  await helpBtn.click();
  // The helptext div should become visible
  const fieldHelp = page.locator('.field-helptext').first();
  await expect(fieldHelp).toBeVisible();
}
```

## Key Selectors Reference

| Feature | Selector | Notes |
|---------|----------|-------|
| Bottom panel | `#bottom-panel` | Height 0 when collapsed |
| Panel tabs | `.panel-tab[data-panel="..."]` | Values: event-log, inference, ai-copilot, lint-dashboard |
| Panel panes | `#panel-inference`, `#panel-lint-dashboard` | `.active` class when visible |
| Inference refresh | `.inference-refresh-btn` | `hx-post="/api/inference/run"` |
| Inference results | `#inference-results` | htmx lazy-loaded |
| Inference filter (type) | `.inference-filter-type` | name="entailment_type" |
| Inference filter (status) | `.inference-filter-status` | name="triple_status" |
| Inference summary | `#inference-summary` | Shows "N inferred triples" |
| Inferred badge | `.inferred-badge` | Shows entailment type |
| Inference dismiss btn | `.inference-dismiss-btn` | On active triples |
| Inference promote btn | `.inference-promote-btn` | On active triples |
| Lint dashboard | `.lint-dashboard` / `#lint-dashboard-container` | htmx lazy-loaded via revealed |
| Lint severity filter | `.lint-dashboard-filter-severity` | Options: Violation, Warning, Info |
| Lint type filter | `.lint-dashboard-filter-type` | Dynamic options from shapes |
| Lint search input | `.lint-dashboard-filter-search` | Debounced keyup (300ms) |
| Lint sort select | `.lint-dashboard-filter-sort` | Options: severity, object, path |
| Lint result rows | `.lint-dashboard-row` | Has `.lint-severity-{level}` class |
| Lint conforms badge | `.lint-conforms` | Shows checkmark when all clear |
| Lint badge (nav) | `#lint-badge` | In panel tab button |
| Form helptext (form-level) | `.form-helptext-top` | `<details>` element |
| Form helptext summary | `.form-helptext-summary` | Click to toggle |
| Form helptext content | `#helptext-form-rendered` | Markdown rendered |
| Field helptext toggle | `.btn-helptext-toggle` | Per-field `?` button |
| Field helptext content | `.field-helptext` | display:none by default |
| Active dockview tab | `.dv-active-group .dv-tab.dv-active-tab` | Has accent border |
| Tab accent color | `--tab-accent-color` on group element | CSS variable |
| Card view | `.card-grid` | Card container |
| Card item | `[data-testid="card-item"]` | Individual card |
| Command palette | `ninja-keys` | Web component |
| Panel chevron icons | `.right-section-chevron` | Lucide chevron-right |
| Panel controls (maximize/close) | `.panel-btn` | Has SVG icons |

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/inference/run` | POST | Trigger inference run |
| `/api/inference/triples` | GET | List inferred triples (filterable) |
| `/api/inference/triples/{hash}/dismiss` | POST | Dismiss an inferred triple |
| `/api/inference/triples/{hash}/promote` | POST | Promote triple to permanent |
| `/api/inference/config` | GET | Get entailment config |
| `/browser/lint-dashboard` | GET | Get lint dashboard HTML partial |
| `/browser/lint/{iri}` | GET | Get per-object lint panel HTML |
| `/api/commands` | POST | Execute commands (object.create, edge.create) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling for lint updates | SSE via EventSource | Phase 37 | Lint panel uses `window._lintSSE` |
| Per-tab inline accent style | CSS variable on group element | Phase 39 | `--tab-accent-color` on `.dv-active-group` |
| Manual inverse entry | OWL 2 RL inference | Phase 35 | Automatic `owl:inverseOf` materialization |

## Open Questions

1. **Seed data validation state**
   - What we know: Seed data is loaded on first setup; async validation runs after `EventStore.commit()`
   - What's unclear: Whether the test Docker stack will have validation results ready by the time lint dashboard tests run
   - Recommendation: Add a setup step that creates/saves an object via API and waits, ensuring validation queue has processed at least once

2. **SHACL-AF rule test data**
   - What we know: basic-pkm v1.1.0 includes SHACL-AF rules (e.g., `hasRelatedNote`)
   - What's unclear: Which exact SHACL-AF rules produce observable triples with current seed data
   - Recommendation: Create a specific edge that triggers a SHACL-AF rule (e.g., linking two notes) and verify `sh:rule` entailment type appears

3. **Helptext availability in seed data**
   - What we know: `sempkm:editHelpText` annotation property exists on SHACL shapes; form renders it
   - What's unclear: Whether basic-pkm model shapes have `sempkm:editHelpText` annotations on any fields
   - Recommendation: Check if seed data shapes include helptext; if not, test can verify the infrastructure (toggle button absence means no helptext configured, which is valid)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright ^1.50.0 |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test --project=chromium --grep "PATTERN"` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-05a | Inference bidirectional links | e2e | `cd e2e && npx playwright test tests/09-inference/ -x` | Wave 0 |
| TEST-05b | Lint dashboard filtering/sorting | e2e | `cd e2e && npx playwright test tests/10-lint-dashboard/ -x` | Wave 0 |
| TEST-05c | Edit form helptext | e2e | `cd e2e && npx playwright test tests/11-helptext/ -x` | Wave 0 |
| TEST-05d | Bug fix verifications (BUG-04 to BUG-09) | e2e | `cd e2e && npx playwright test tests/12-bug-fixes/ -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** Run the specific spec file being worked on
- **Per wave merge:** `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/09-inference/inference.spec.ts` -- covers TEST-05a
- [ ] `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` -- covers TEST-05b
- [ ] `e2e/tests/11-helptext/helptext.spec.ts` -- covers TEST-05c
- [ ] `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` -- covers TEST-05d

## Sources

### Primary (HIGH confidence)
- `e2e/playwright.config.ts` -- test framework configuration
- `e2e/fixtures/auth.ts` -- authentication fixture patterns
- `e2e/fixtures/seed-data.ts` -- seed data constants
- `e2e/helpers/selectors.ts` -- shared selectors
- `e2e/helpers/wait-for.ts` -- wait helper patterns
- `e2e/helpers/dockview.ts` -- dockview interaction patterns
- `e2e/helpers/api-client.ts` -- API client for test setup
- `backend/app/templates/browser/inference_panel.html` -- inference panel DOM structure
- `backend/app/templates/browser/inference_triple_row.html` -- triple row structure
- `backend/app/templates/browser/lint_dashboard.html` -- lint dashboard DOM structure
- `backend/app/templates/browser/lint_panel.html` -- per-object lint panel
- `backend/app/templates/browser/workspace.html` -- bottom panel tabs and panes
- `backend/app/templates/forms/object_form.html` -- form-level helptext
- `backend/app/templates/forms/_field.html` -- field-level helptext
- `frontend/static/css/dockview-sempkm-bridge.css` -- tab accent CSS
- `frontend/static/js/workspace-layout.js` -- accent color JS logic
- `frontend/static/js/workspace.js` -- bottom panel, keyboard shortcuts
- `backend/app/inference/router.py` -- inference API endpoints

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- using existing infrastructure, no new deps
- Architecture: HIGH -- all DOM selectors and API endpoints verified from source code
- Pitfalls: HIGH -- based on established patterns from 124 passing tests and project memory

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable -- test infrastructure unlikely to change)