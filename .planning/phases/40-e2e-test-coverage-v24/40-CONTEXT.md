# Phase 40: E2E Test Coverage for v2.4 - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Playwright E2E tests covering all v2.4 user-visible features: OWL 2 RL inference, SHACL-AF rules, global lint dashboard, edit form helptext, type-aware accent colors, and verification of already-fixed bugs (BUG-05 through BUG-09). No feature work — testing only.

</domain>

<decisions>
## Implementation Decisions

### Test organization
- New numbered directories for major features: `09-inference/`, `10-lint-dashboard/`
- Helptext tests in a new `11-helptext/` directory or extend `01-objects/` — Claude's discretion
- Bug verification tests in a single `bug-fixes.spec.ts` file (could go in `09-bug-fixes/` or similar)
- All tests run under the existing `chromium` Playwright project — no separate project config
- Use existing seed data from `fixtures/seed-data.ts`; inference tests create edges and trigger inference to verify

### Inference test scenarios (Phases 35 + 36)
- **Core flow:** Create edge → trigger inference → verify inverse appears on target object's detail page
- **Lifecycle:** Delete source edge → re-run inference → verify inferred triple removed
- **Bottom panel:** Verify inference panel shows results, filters by object type and date work, dismiss/promote actions work
- **Visual distinctions:** Verify inferred badges and dashed graph edges via CSS/attribute assertions
- **Admin config:** Test toggling entailment types on/off in admin panel and verify effect on inference results
- **SHACL-AF rules:** Separate test verifying rule-derived triples (e.g., `hasRelatedNote`) appear alongside OWL-derived triples

### Lint dashboard test scenarios (Phases 37 + 38)
- Dashboard loads and shows validation results
- Severity filter works (filter by violations, warnings, infos)
- Sorting by column works (severity, object name, property path)
- Matches success criteria #2 from roadmap

### Helptext test scenarios (Phase 39)
- Verify helptext toggle exists on edit form (both form-level and field-level)
- Clicking toggle expands helptext content
- Content appears (presence assertion, not rendered HTML structure)
- Helptext collapsed by default

### Bug verification tests (BUG-05 through BUG-09)
- Functional assertions in both light and dark themes (theme-specific bugs like card borders, dark chevrons)
- **BUG-05:** Card view borders render correctly in both themes
- **BUG-06:** Ctrl+K opens ninja-keys command palette (Chromium only — Firefox fix is cross-browser preventDefault)
- **BUG-07:** Tab accent bar does not bleed into adjacent inactive tabs
- **BUG-08:** Panel chevron icons visible in dark mode
- **BUG-09:** Concept search/linking works end-to-end

### Type accent color verification (BUG-04 / Phase 39 feature)
- Verify active tab shows type-specific accent color (not uniform teal)
- Test with at least 2 different object types to confirm colors differ

### Claude's Discretion
- Exact test file naming and directory placement within the numbered structure
- Which seed objects to use for each test scenario
- Whether to add new seed data fixtures or reuse existing ones
- Assertion strategies (CSS property checks, data attribute checks, text content checks)
- Test ordering and any shared setup between test files
- Whether lint dashboard tests need to trigger validation first or rely on existing state

</decisions>

<specifics>
## Specific Ideas

- Inference test should follow the user journey: create a relationship → click "Refresh" in inference panel → navigate to target object → see inverse link
- Bug verification tests grouped in one file makes it easy to run just the regression checks: `npx playwright test bug-fixes`
- Both-themes testing for visual bugs (BUG-05, BUG-07, BUG-08) catches regressions that only appear in one theme

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `e2e/fixtures/auth.ts`: Authentication fixture with `ownerPage` for logged-in tests
- `e2e/fixtures/seed-data.ts`: SEED constants with known IRIs for Notes, Projects, Persons, Concepts
- `e2e/helpers/selectors.ts`: SEL constants for common UI selectors
- `e2e/helpers/wait-for.ts`: `waitForWorkspace()`, `waitForIdle()` helpers
- `e2e/helpers/dockview.ts`: Dockview-specific test helpers (new in v2.3)
- `e2e/helpers/api-client.ts`: Direct API client for test setup/teardown

### Established Patterns
- Tests use `ownerPage.evaluate()` to call workspace JS functions like `openTab()`
- `waitForIdle()` after actions to let htmx settle
- Seed data accessed via `SEED.notes.architecture.iri` etc.
- Dark mode toggled via `ownerPage.evaluate()` calling theme toggle function
- Bottom panel accessed via `.panel-tab[data-panel="..."]` selectors

### Integration Points
- Inference panel: new bottom panel tab "Inference" — needs selector pattern
- Lint dashboard: new bottom panel tab "LINT" — needs selector pattern
- Helptext: edit form `?` icon and collapsible section — new UI elements to select
- Admin entailment config: admin panel page — needs navigation path
- Type accent colors: dockview tab border-bottom CSS — attribute/style assertion

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-e2e-test-coverage-v24*
*Context gathered: 2026-03-05*
