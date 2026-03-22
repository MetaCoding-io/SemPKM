# M032: Block-Based Custom UI Builder

**Vision:** Users build custom dashboards from a richer widget palette — stat cards showing live SPARQL counts, Chart.js visualizations, styled headings, working markdown, executable SPARQL result tables — and can compose multi-object creation workflows where linked objects are created in one submission.

## Success Criteria

- A dashboard with a stat-card block shows a live SPARQL-derived count (e.g., total Projects) that updates on page load
- A dashboard with a chart block renders a bar/line/pie Chart.js visualization from SPARQL query results
- The sparql-result block actually executes its configured query and displays a results table
- The markdown block renders full markdown (headings, lists, code, links) via marked.js
- A heading block displays configurable title/subtitle text at the chosen heading level
- The dashboard builder palette lists all new block types with working config forms
- A form-group block creates multiple linked objects in one submission, with slot-based IRI resolution connecting them via edges
- Existing dashboards continue to render correctly with no migration required

## Key Risks / Unknowns

- **Slot-based IRI resolution in batch commands.** The Command API batch fires commands independently — no cross-command IRI reference. Extending it for `@slot` back-references requires careful sequencing and partial-failure handling.
- **Chart.js lazy loading in workspace.** Chart.js is only available on admin pages. Loading it on demand inside dockview dashboard panels must not conflict with existing GridStack or other widget JS.
- **Multi-SHACL-form DOM isolation.** The create-form block embeds one SHACL form via htmx. Form groups need multiple forms in one widget without ID collisions, validation interference, or htmx target conflicts.

## Proof Strategy

- Slot-based IRI resolution → retire in S01 by building the form-group block type end-to-end: backend batch extension, block registration, builder config UI, and a working dashboard that creates two linked objects in one submission
- Chart.js lazy loading → retire in S02 by shipping a chart block that lazy-loads Chart.js and renders in a dockview dashboard panel
- DOM isolation → retire in S01 by rendering multiple SHACL sub-forms inside one block with namespaced IDs and independent submission targets

## Verification Classes

- Contract verification: pytest for BlockRegistry (new types), batch slot resolution, render_block output; existing 70+ dashboard tests as regression guard
- Integration verification: running Docker stack with dashboard rendering SPARQL-driven widgets from triplestore data
- Operational verification: none (no new services or daemons)
- UAT / human verification: visual check of chart rendering, stat-card styling, form-group create flow

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 6 new/fixed block types (stat-card, chart, heading, markdown fix, sparql-result fix, form-group) register in BlockRegistry and render in dashboard viewer
- Dashboard builder has config forms for all new block types with working save/load
- Form-group block creates multiple objects with edges via slot IRI resolution
- Chart.js loads lazily only when a chart block is present
- Existing dashboards render without regressions (existing test suite passes)
- E2E Playwright test exercises at least stat-card and chart block rendering
- User guide documents all new block types

## Requirement Coverage

- Covers (new, to be added): BLK-01 (stat-card), BLK-02 (chart), BLK-03 (heading), BLK-04 (sparql-result fix), BLK-05 (markdown fix), BLK-07 (form-group), BLK-08 (Chart.js lazy load), BLK-10 (E2E tests), BLK-11 (user guide)
- Leaves for later: BLK-06 (JSON Schema formalization — Python type hints are sufficient), BLK-09 (viewer inline editing — users can already edit via builder tab)
- Partially covers: DASH-01 (extends existing dashboard with new block types), DASH-02 (existing cross-view context passes through unchanged)
- Orphan risks: none — all CONTEXT.md deliverables are mapped

## Slices

- [x] **S01: Multi-Object Form Groups with Slot IRI Resolution** `risk:high` `depends:[]`
  > After this: User opens a dashboard with a form-group block, fills two SHACL sub-forms (e.g., Note + Task), submits once, and both objects are created with an edge linking them — visible in the object browser.
- [x] **S02: Data-Driven Widgets (stat-card, chart, heading) + Block Fixes** `risk:medium` `depends:[]`
  > After this: A dashboard displays a stat-card with a live count from SPARQL, a Chart.js bar chart visualizing query results, a styled heading, working markdown with full rendering, and an executable sparql-result table — all configured through the builder.
- [x] **S03: E2E Tests and User Guide** `risk:low` `depends:[S01,S02]`
  > After this: Playwright E2E test verifies stat-card and chart rendering in a live dashboard. User guide documents all new block types with screenshots and configuration instructions.

## Boundary Map

### S01 → S03

Produces:
- `form-group` block type in BlockRegistry with config schema (`slots: list[dict]`, `edges: list[dict]`)
- `POST /api/commands` extended to accept `@slot:name` IRI references in batch payloads, resolving sequentially
- Builder config form for form-group (slot definition + edge wiring UI)
- `render_block()` handler for `form-group` type rendering multiple SHACL sub-forms

Consumes:
- Existing BlockRegistry pattern, SHACL form rendering, Command API batch, dashboard builder infrastructure

### S02 → S03

Produces:
- `stat-card`, `chart`, `heading` block types in BlockRegistry with config schemas
- `render_block()` handlers for all three types + fixed `markdown` and `sparql-result` handlers
- Frontend JS: `_executeSparqlWidget()` for stat-card/sparql-result, Chart.js lazy loader for chart blocks
- Builder config forms for all three new types (query input, chart type selector, heading level picker)
- Chart.js available in workspace context via lazy `<script>` injection

Consumes:
- Existing BlockRegistry pattern, `/api/sparql` endpoint, dashboard builder infrastructure, `marked.js` (global)

### S01, S02 → S03

Produces:
- E2E Playwright spec exercising dashboard creation with new block types
- User guide chapter covering all new block types and form-group workflows
- `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html` updated

Consumes:
- All new block types from S01 and S02 must be operational
- Running Docker test stack for E2E
