# S07 UAT: E2E Tests + User Guide Docs

## Preconditions

- Docker test stack is **not** required for these checks — S07 deliverables are E2E test files and documentation files
- Repository is checked out with the M031/S07 branch merged
- Node.js and TypeScript available for compilation checks

---

## Test Case 1: Carousel E2E Spec Retired

**Goal:** Confirm the stale carousel test file is deleted and no longer runnable.

1. Run `ls e2e/tests/02-views/carousel-views.spec.ts`
2. **Expected:** "No such file or directory" — file does not exist
3. Run `grep -r "carousel-views" e2e/` 
4. **Expected:** Zero matches — no references to the deleted spec remain

---

## Test Case 2: M031 E2E Spec Exists with Correct Test Coverage

**Goal:** Confirm the new spec covers all 6 M031 features.

1. Run `cat e2e/tests/02-views/m031-views.spec.ts`
2. **Expected:** File exists, contains `test(` blocks
3. Run `grep -c "test(" e2e/tests/02-views/m031-views.spec.ts`
4. **Expected:** Returns `6` (exactly 6 test cases)
5. Verify these 6 test names appear:
   - `carousel tab bar is absent from generic views`
   - `generic view tab opens from explorer sidebar click`
   - `kanban view renders board with status columns`
   - `view scope dropdown is present on generic views`
   - `save view button is present on generic views`
   - `multiple instances of same view type create separate tabs`

---

## Test Case 3: Seed Data Includes Task Type

**Goal:** Kanban E2E tests can reference the Task type.

1. Run `grep "Task:" e2e/fixtures/seed-data.ts`
2. **Expected:** Line contains `Task: 'urn:sempkm:model:basic-pkm:Task'`

---

## Test Case 4: View Selectors Added to Centralised Registry

**Goal:** All 6 M031 view selectors exist in the shared selectors file.

1. Run `grep -E "kanbanBoard|kanbanColumn|kanbanCard|scopeSelect|variantSelect|saveViewBtn" e2e/helpers/selectors.ts`
2. **Expected:** 6 lines, each mapping a selector name to a CSS class:
   - `kanbanBoard: '.kanban-board'`
   - `kanbanColumn: '.kanban-column'`
   - `kanbanCard: '.kanban-card'`
   - `scopeSelect: '.view-scope-select'`
   - `variantSelect: '.view-variant-select'`
   - `saveViewBtn: '.save-view-btn'`

---

## Test Case 5: openGenericViewTab Helper Exists

**Goal:** E2E tests can programmatically open view tabs.

1. Run `grep "openGenericViewTab" e2e/helpers/dockview.ts`
2. **Expected:** Function export with `renderer`, `waitSelector`, optional `scopeQuery`, `scopeLabel`, `timeoutMs` parameters
3. Verify it calls `window.openGenericViewTab()` via `page.evaluate()`

---

## Test Case 6: TypeScript Compilation (M031 Files)

**Goal:** No TypeScript errors in M031-touched E2E files.

1. Run `npx tsc --noEmit --project e2e/tsconfig.json 2>&1 | grep -E "m031-views|dockview|selectors|seed-data"`
2. **Expected:** Zero output (no errors in M031 files)
3. **Note:** Pre-existing errors in other files are acceptable — only M031 files must be clean

---

## Test Case 7: Chapter 7 — No Carousel References, New Sections Present

**Goal:** User guide accurately reflects carousel removal and new features.

1. Run `grep -i "carousel" docs/guide/07-browsing-and-visualizing.md`
2. **Expected:** Zero matches — no carousel references remain
3. Run `grep "^## " docs/guide/07-browsing-and-visualizing.md`
4. **Expected:** At least 8 H2 sections, including:
   - `## View Toolbar`
   - `## Kanban View`
   - `## Saved Views`
   - `## Multiple View Instances`
   - `## Saved Queries in Explorer`
5. Verify View Toolbar section mentions variant dropdown, scope dropdown, and save button
6. Verify Kanban View section mentions status columns and drag-drop
7. Verify Saved Views section mentions saving current view configuration

---

## Test Case 8: Chapter 21 — Graph Visualization Section

**Goal:** SPARQL graph visualization tab is documented.

1. Run `grep "^## Graph Visualization" docs/guide/21-sparql-console.md`
2. **Expected:** Exactly one match
3. Read the section content
4. **Expected:** Mentions triple-pattern detection, Table/Graph tab switcher, Cytoscape.js, and layout selection (dagre for small graphs, fcose for larger)

---

## Test Case 9: Chapter 28 — Builder UX Sections

**Goal:** Dashboard/workflow builder improvements are documented.

1. Run `grep "^## " docs/guide/28-dashboards-and-workflows.md`
2. **Expected:** Sections include:
   - `## Builder Help Text`
   - `## IRI Autocomplete`
   - `## Simplified Workflow View Step`
   - `## Sample Dashboards and Workflows`
3. Verify Builder Help Text section explains contextual field-help pattern
4. Verify IRI Autocomplete section mentions class search and object search endpoints
5. Verify Sample section references seed data fixtures

---

## Edge Cases

### EC1: Selector-to-DOM Alignment
- The selectors in `SEL.views` (`.kanban-board`, `.kanban-column`, `.kanban-card`, `.view-scope-select`, `.view-variant-select`, `.save-view-btn`) must match actual CSS classes in `view_toolbar.html` and `kanban_view.html`
- Run: `grep -r "kanban-board\|kanban-column\|kanban-card\|view-scope-select\|view-variant-select\|save-view-btn" frontend/templates/browser/views/ backend/app/templates/browser/views/`
- **Expected:** Each class appears at least once in a template file

### EC2: No Stale Carousel References in Other Docs
- Run: `grep -ri "carousel" docs/guide/`
- **Expected:** Zero matches across all guide chapters (not just ch7)

### EC3: Documentation Internal Consistency
- All features described in ch7/21/28 should reference features that were actually implemented in S01–S06
- Spot-check: "drag cards between columns" in ch7 Kanban section → corresponds to kanban drag-drop in S04
- Spot-check: "Graph Visualization" in ch21 → corresponds to SPARQL graph tab in S05
- Spot-check: "IRI Autocomplete" in ch28 → corresponds to builder autocomplete in S06
