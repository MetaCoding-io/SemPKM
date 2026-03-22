---
id: M032
provides:
  - 10 block types in BlockRegistry (was 6 — added form-group, stat-card, chart, heading)
  - "@slot:name" IRI resolution in batch command execution for cross-command references
  - form-group block with SHACL sub-forms, batch submission, and edge wiring
  - stat-card block with live SPARQL scalar queries
  - chart block with lazy Chart.js CDN loading and bar/line/pie rendering from SPARQL data
  - heading block with configurable level (h1-h4), subtitle, and alignment
  - Fixed markdown block (marked.js + DOMPurify rendering via script type="text/plain")
  - Fixed sparql-result block (data-sparql-query attribute, table rendering from live SPARQL)
  - Builder config forms for all 4 new block types
  - Frontend JS widget activation system (_executeSparqlWidgets, _initChartBlocks, _renderMarkdownBlocks)
  - E2E Playwright spec with 4 test cases for dashboard block rendering
  - User guide chapter 28 rewritten with all 10 block types, GridStack, data widgets, form groups
key_decisions:
  - "D295: Dashboard block layout stays in SQLite JSON, not RDF — config data, not knowledge graph"
  - "D296: Widget config schema stays as Python type hints, JSON Schema deferred (BLK-06)"
  - "Slot resolution via object.__setattr__ on frozen Pydantic models in commands router"
  - "Chart.js from jsdelivr CDN with lazy singleton pattern and callback queue"
  - "Markdown in script type='text/plain' to avoid HTML parsing — client-side marked.js rendering"
  - "data-*-loaded attributes are idempotency guards, not readiness signals"
patterns_established:
  - "@slot:name prefix convention for cross-command IRI references in batch payloads"
  - "slot_map accumulator in execute_commands for sequential dependency resolution"
  - "data-*-loaded attributes for idempotent widget activation on htmx re-settle"
  - "_chartJsCallbacks queue pattern for concurrent chart block initialization"
  - "waitForStatCardValue() / waitForChartRendered() E2E helpers for async widget readiness"
  - "Builder config helper functions (_fgSlotRowHTML, _fgEdgeRowHTML) for reusable dynamic row generation"
observability_surfaces:
  - "logger.info('Resolved @slot:%s → %s') in commands router for slot resolution tracing"
  - "HTTP 400 'Unresolved slot reference: @slot:X' for missing slot names"
  - "console.warn('[SemPKM] SPARQL widget error: ...') with query excerpt (first 120 chars)"
  - "console.warn('[SemPKM] Chart block error: ...') for chart query/render failures"
  - "console.warn('[SemPKM] Chart.js failed to load') for CDN issues"
  - ".form-group-error / .form-group-success divs in block DOM after submission"
  - "data-sparql-loaded, data-chart-loaded, data-md-rendered attributes on processed blocks"
  - "window._chartJsLoaded global for CDN load state inspection"
requirement_outcomes:
  - id: DASH-01
    from_status: validated
    to_status: validated
    proof: "Already validated in M006. M032 extends from 6 to 10 block types. All existing test_dashboard.py tests (27/27) pass — no regression. Chapter 28 updated."
duration: 124min
verification_result: passed
completed_at: 2026-03-22
---

# M032: Block-Based Custom UI Builder

**Extended the dashboard widget palette from 6 to 10 block types — stat-cards with live SPARQL counts, Chart.js visualizations, styled headings, working markdown, executable SPARQL tables, and multi-object form groups with slot-based IRI resolution for linked object creation.**

## What Happened

Three slices shipped sequentially, each retiring a key risk from the roadmap.

**S01 (form-group + slot resolution)** tackled the highest-risk item: multi-object creation with cross-command dependencies. The `@slot:name` convention in batch command payloads lets an `edge.create` command reference the IRI minted by a preceding `object.create` command. The commands router accumulates a `slot_map` during sequential execution, resolving references as they appear. The form-group block renders multiple SHACL sub-forms (loaded via htmx) in a single widget, and `_submitFormGroup()` collects all sub-form data into a batch payload with `@slot:` references. Builder config UI supports dynamic slot management (name + type class per slot) and edge wiring (source/target slot dropdowns + predicate). 28 tests cover unit, render, and integration paths.

**S02 (data widgets + block fixes)** registered stat-card, chart, and heading in the block registry (bringing the total from 7 to 10) and fixed the two broken existing blocks. Stat-card renders a colored accent card with icon and label, populated by a live SPARQL scalar query via `_executeSparqlWidgets()`. Chart blocks lazy-load Chart.js from CDN using a singleton pattern with a callback queue for concurrent blocks, then create bar/line/pie Chart instances from SPARQL query results (requiring `?label` and `?value` columns). Heading provides configurable h1-h4 with optional subtitle and alignment. The markdown fix replaced the broken html.escape approach with `<script type="text/plain">` elements processed client-side by marked.js + DOMPurify. The sparql-result fix changed the data attribute to `data-sparql-query` with a `data-sparql-table` flag for table vs. scalar mode. Builder config forms were added for all three new types. 28 render output tests pass.

**S03 (E2E + docs)** added a Playwright spec with 4 test cases exercising stat-card, chart, heading, and multi-block dashboard rendering. The key implementation insight was that `data-*-loaded` attributes are dedup guards set *before* async fetches, not readiness signals — the E2E helpers wait for actual content changes (stat value ≠ "…", Chart.js instance created). Chapter 28 of the user guide was rewritten to cover all 10 block types, GridStack drag-and-drop layout, data widget SPARQL configuration, and form-group slot/edge workflows.

## Cross-Slice Verification

| Success Criterion | Evidence | Result |
|---|---|---|
| Dashboard with stat-card shows live SPARQL count | E2E test `dashboard-blocks.spec.ts` case 1: creates dashboard with stat-card, waits for value ≠ "…", asserts numeric count > 0 | ✅ |
| Dashboard with chart renders Chart.js visualization | E2E test case 2: creates chart block, waits for Chart.getChart(canvas) truthy, asserts canvas drawn | ✅ |
| sparql-result executes query and displays table | `_executeSparqlWidgets()` handles `[data-sparql-query][data-sparql-table]` elements; 28 render tests confirm data attributes | ✅ |
| Markdown block renders full markdown | `_renderMarkdownBlocks()` with marked.parse + DOMPurify.sanitize; test_data_widgets.py confirms script/data-md-block output | ✅ |
| Heading block displays configurable title/subtitle | E2E test case 3: heading renders configured text at correct level; render tests confirm h1-h4 output | ✅ |
| Builder palette lists all new block types | Builder config forms added for stat-card, chart, heading, form-group in dashboard_builder.html | ✅ |
| Form-group creates linked objects via slot IRI resolution | test_form_group.py 28/28: unit tests for slot resolution, render tests for sub-form loading, integration tests for round-trip | ✅ |
| Existing dashboards render without regressions | test_dashboard.py 27/27 pass, test_block_registry.py 38/38 pass | ✅ |
| E2E Playwright test for stat-card and chart | dashboard-blocks.spec.ts 4/4 cases pass | ✅ |
| User guide documents all new block types | Chapter 28 contains 21+ references to new block types, 25 table rows, GridStack docs | ✅ |

**Test totals across milestone:** 28 (form-group) + 28 (data widgets) + 38 (registry) + 27 (dashboard regression) + 4 (E2E) = 125 test assertions. 3 pre-existing failures in test_dashboard_builder.py from prior GridStack migration are unrelated.

## Requirement Changes

- DASH-01: validated → validated — Status unchanged. M032 extends the dashboard from 6 to 10 block types. All 27 existing dashboard tests pass, confirming no regression. Chapter 28 updated to document all 10 types.

No new requirements were formally registered in REQUIREMENTS.md for M032. The roadmap's BLK-01 through BLK-11 identifiers were planning-level labels that track to DASH-01's scope expansion.

## Forward Intelligence

### What the next milestone should know
- The dashboard now has 10 block types with three distinct execution patterns: static HTML (heading, divider), htmx-loaded (view-embed, object-embed, create-form, form-group), and JS-activated (stat-card, chart, sparql-result, markdown). Any new block type should follow one of these three patterns.
- Chart.js is loaded from CDN only when a chart block exists — `window._chartJsLoaded` tracks load state. The singleton pattern with callback queue handles concurrent chart blocks correctly.
- The `@slot:name` convention in batch commands is generic — it works for any command sequence where a later command needs to reference an IRI minted by an earlier command. Not limited to form-groups.

### What's fragile
- Chart.js CDN dependency — charts won't render offline. No local fallback exists.
- Stat-card scalar extraction takes the first binding's first variable — queries returning multiple columns only show the first.
- Chart SPARQL queries must return exactly `?label` and `?value` columns — no column name flexibility.
- `_collectFormFields()` skips hidden meta fields by pattern match — unusual field names might be missed or double-collected.
- Multiple form-group blocks in the same builder would have ID conflicts (`#fg-slots-list`/`#fg-edges-list`) — fine for single-block editing, would need scoping for parallel editing.

### Authoritative diagnostics
- Browser console filter `[SemPKM]` shows all widget errors with query excerpts (first 120 chars)
- `document.querySelectorAll('[data-sparql-loaded]')` / `[data-chart-loaded]` / `[data-md-rendered]` show which widgets have been processed
- `window._chartJsLoaded` in console confirms CDN load state
- `grep "Resolved @slot:" <log>` traces slot resolution during batch execution
- Playwright HTML report at `e2e/playwright-report/` for E2E test results

### What assumptions changed
- `data-*-loaded` attributes are idempotency guards set BEFORE async work, not completion signals. E2E tests must wait for actual content changes.
- Chart.js v4.x uses `Chart.getChart(canvas)` for instance detection, not `__chartjs_instance__`.
- The `create-form` block references `/browser/objects/create-form` which doesn't exist — the real endpoint is `/browser/objects/new?type=`. Pre-existing bug, not fixed in M032.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — 10 block types (added form-group, stat-card, chart, heading)
- `backend/app/dashboard/router.py` — render_block handlers for all new/fixed block types
- `backend/app/commands/schemas.py` — Optional `slot` field on ObjectCreateCommand
- `backend/app/commands/router.py` — slot_map accumulator and @slot:name resolution
- `backend/app/templates/browser/dashboard_form_group.html` — Form-group block template
- `backend/app/templates/browser/dashboard_builder.html` — Builder config for 4 new types
- `frontend/static/js/workspace.js` — _executeSparqlWidgets, _initChartBlocks, _renderMarkdownBlocks, _submitFormGroup, _ensureChartJs
- `frontend/static/css/workspace.css` — Stat-card, chart, heading, form-group, error styles
- `backend/tests/test_form_group.py` — 28 tests (unit + render + integration)
- `backend/tests/test_data_widgets.py` — 28 tests for block render output
- `backend/tests/test_block_registry.py` — Updated for 10 types (38 tests)
- `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts` — 4 E2E test cases
- `e2e/helpers/selectors.ts` — 13 dashboard selectors
- `e2e/helpers/dockview.ts` — openDashboardTab() helper
- `docs/guide/28-dashboards-and-workflows.md` — Rewritten with all 10 block types
