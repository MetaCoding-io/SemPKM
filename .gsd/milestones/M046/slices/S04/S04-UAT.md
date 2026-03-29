# S04: Ontology Viewer — Locator Scoping for Dockview Panels — UAT

**Milestone:** M046
**Written:** 2026-03-29T02:36:15.279Z

## UAT: Ontology Viewer — Locator Scoping for Dockview Panels

### Preconditions
- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- At least one Mental Model installed (basic-pkm)
- Playwright E2E environment configured (`cd e2e && npm install`)

### Test 1: No Duplicate Element IDs in Ontology Template
**Steps:**
1. Run: `grep -c 'ontology-tab-content' backend/app/templates/browser/ontology/ontology_page.html`
2. For each of `ontology-tbox`, `ontology-rbox`, `ontology-abox`: run `grep -c 'id="<id>"' backend/app/templates/browser/ontology/ontology_page.html`
3. For each of `tbox-tree`, `rbox-legend`, `abox-browser`, `ontology-tab-abox`: run `grep -c 'data-testid="<attr>"' backend/app/templates/browser/ontology/ontology_page.html`

**Expected:** All counts are exactly 1. Zero duplicates.

### Test 2: ABox Tab Button Present in Tab Bar
**Steps:**
1. Open the ontology viewer page in the browser (navigate to any installed model's ontology page)
2. Inspect the `.ontology-tabs` container

**Expected:** Tab bar shows buttons in order: TBox, RBox, ABox, Create Class. ABox button has `data-tab="abox"` and `data-testid="ontology-tab-abox"`.

### Test 3: ABox Pane Lazy-Loads on Tab Click
**Steps:**
1. On the ontology page, click the ABox tab button
2. Observe the `#ontology-abox` pane

**Expected:** Pane shows loading state initially, then loads content via htmx GET to `/browser/ontology/abox`. The `hx-trigger="click once"` ensures only one fetch.

### Test 4: TBox E2E Test Passes Without Strict Mode Errors
**Steps:**
1. Run: `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts --reporter=list`
2. Check test output for any 'resolved to 2 elements' or 'strict mode violation'

**Expected:** TBox-related tests pass. Zero strict mode errors in output.

### Test 5: ABox E2E Test Passes Without Strict Mode Errors
**Steps:**
1. Run: `cd e2e && npx playwright test tests/22-ontology/ --reporter=list --grep "ABox"`
2. Check test output

**Expected:** ABox tab navigation test passes. The `[data-testid="abox-browser"]` selector resolves to exactly 1 element.

### Edge Cases
- **RBox test:** Known pre-existing failure due to data-testid naming mismatch (template appends source suffix). Not a regression from this slice.
- **Class creation test:** Known pre-existing failure waiting for `.success-message` element. Not a regression from this slice.
