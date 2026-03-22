# M032 Research: Block-Based Custom UI Builder

## Executive Summary

M032 builds on a **substantial existing foundation**. The dashboard subsystem (shipped in M006, enhanced through M031) already has:
- GridStack v10 for interactive drag-drop-resize layout (builder) and static rendering (viewer)
- A `BlockRegistry` with 6 typed block declarations and config validation
- A builder UI with palette drag-in, click-to-add, per-block config forms, and save/load
- Layout migration from 5 legacy CSS Grid templates to GridStack positions
- 1,076 lines of existing tests across 4 test files

The work breaks into: (1) completing incomplete features (sparql-result execution, editable dashboard viewer), (2) new data-driven widgets (stat-card, chart, heading), (3) multi-object form groups with IRI slot resolution, and (4) widget config schema formalization.

## Codebase Exploration

### Existing Dashboard Architecture

**Backend** (`backend/app/dashboard/`):
- `registry.py` — `BlockRegistry` singleton with `BlockTypeSpec` dataclass (type_name, label, icon, category, config_schema, default_w, default_h). 6 types: view-embed, markdown, object-embed, create-form, sparql-result, divider.
- `models.py` — `DashboardSpec` SQLAlchemy model. `blocks_json` stores blocks as JSON array. Each block: `{type, config, x?, y?, w?, h?, slot?}`.
- `service.py` — Standard CRUD. Validates blocks against registry on create/update.
- `router.py` — Browser routes (htmx partials) + JSON API. Block rendering dispatches by type to inline HTML builders. Legacy layouts auto-migrate to GridStack on first access.
- `migration.py` — Maps slot names to `(x, y, w, h)` positions per layout template. Idempotent.
- `seed.py` — Creates "Getting Started" dashboard for new users.

**Frontend**:
- `dashboard_page.html` — Static GridStack grid (`gs-no-resize="true"`, `gs-no-move="true"`). Blocks load via htmx `hx-get="/browser/dashboard/{id}/block/{index}"`. Cross-block context passing via `dashboardContextChanged` custom event.
- `dashboard_builder.html` — Full GridStack builder with palette sidebar, drag-in via `GridStack.setupDragIn`, click-to-add, per-type config forms (view-embed gets ViewSpec dropdown, create-form gets class autocomplete, etc.), and JSON save to API.
- `workspace.css` — ~200 lines of dashboard CSS covering page rendering, builder layout, palette, widget styling, GridStack overrides, config forms.
- `workspace.js` — `openDashboardTab()` and `openDashboardBuilderTab()` for dockview integration.

**CDN dependency**: GridStack v10 loaded in `base.html` (both CSS and JS). Chart.js v4.4 loaded only on admin model detail page.

### Block Type Details

| Type | Category | Config Keys | Status |
|------|----------|-------------|--------|
| view-embed | data | spec_iri, renderer_type, height, emits_context, listens_to_context | **Working** — loads view via htmx, cross-block context |
| markdown | content | content | **Working** — basic paragraph rendering (no real markdown parser) |
| object-embed | data | object_iri, mode | **Working** — loads object detail via htmx |
| create-form | data | target_class, defaults | **Working** — loads SHACL form via htmx |
| sparql-result | data | query, label | **Incomplete** — renders `data-query` attribute but no JS executes the query |
| divider | layout | (none) | **Working** — renders `<hr>` |

### Gaps and Incomplete Features

1. **sparql-result block never executes its query.** The router renders `<span data-query="...">...</span>` but no frontend JS picks up `data-query` and calls `/api/sparql`. This is dead UI.

2. **Markdown rendering is basic.** Uses `html.escape` + paragraph splitting, not a real markdown parser. The workspace already has `marked.js` for body rendering — the dashboard markdown block should use it.

3. **Dashboard viewer is read-only.** GridStack is initialized with `staticGrid: true`, no resize/move. Making the viewer editable (inline editing mode) would give users a direct manipulation UX without opening the separate builder.

4. **No data-driven aggregation widgets.** The existing blocks are either content (markdown, divider) or embed-existing-things (view-embed, object-embed, create-form). There are no widgets that compute and display aggregate data (counts, sums, charts).

### SPARQL Query Execution Infrastructure

The `/api/sparql` POST endpoint accepts a `query` parameter and returns JSON results. It auto-injects prefixes and scopes to `urn:sempkm:current` graph. This is the right backend for stat-card and chart widgets — they'll POST a SPARQL query and render the scalar or tabular result.

Key constraints:
- Only read queries (SELECT, ASK, CONSTRUCT, DESCRIBE) — no UPDATE/DELETE
- Results are JSON with `head.vars` and `results.bindings` (standard SPARQL JSON format)
- IRI values in results include label/type/icon metadata enrichment

### Multi-Object Form Groups — Analysis

This is the most complex new feature. The concept: a dashboard widget that contains multiple SHACL forms for different types, where submitting the group creates all objects and links them together.

**Example use case:** A "New Meeting" form group with:
1. A Note form (meeting notes)
2. A Task form (action item)
3. An edge linking Task → Note via `bpkm:relatedTo`

**IRI slot resolution** means: when form B references an IRI from form A (e.g., the Task's `bpkm:relatedTo` property should point to the Note just created), the system needs to resolve that reference at submission time since the Note's IRI doesn't exist until it's created.

**Implementation approach:**
- Each form slot in the group gets a symbolic name (e.g., `"meeting-note"`, `"action-item"`)
- Edge definitions reference slots: `{source: "@meeting-note", target: "@action-item", predicate: "bpkm:relatedTo"}`
- On submit, the backend creates objects sequentially, replacing `@slot` references with actual IRIs
- The Command API already supports batch execution — `POST /api/commands` accepts an array of commands. However, current batch execution doesn't support cross-command IRI references.

**Backend change needed:** Either extend the batch Command API to support slot-based IRI resolution, or create a dedicated `/api/form-group` endpoint that handles the orchestration.

### Technology Choices

**GridStack v10** — Already integrated. Features available but unused:
- `save()` / `load()` for layout serialization (currently using custom JSON format)
- `resizecontent` event for responsive widget content
- Nested grids (could enable sub-layouts within widgets)
- `staticGrid` toggle (could enable inline editing in viewer mode)

**Chart.js v4.4** — Already loaded on admin pages. Needs to be available in workspace context for chart widgets. Currently loaded only via `<script>` tag in `admin/model_detail.html`. For dashboard chart widgets, it should be lazy-loaded when a chart block is first rendered.

**marked.js** — Already used for body markdown rendering. Should be reused for the markdown block instead of the current basic paragraph splitter.

## Risk Assessment

### High Risk: Multi-Object Form Groups
The slot-based IRI resolution requires either extending the Command API batch execution or building a new orchestration layer. Both approaches have edges:
- The Command API batch currently fires commands independently — no cross-reference between results
- A form group endpoint needs to handle partial failure (what if object 2 fails after object 1 succeeds?)
- The SHACL form rendering (create mode) is designed for single-object creation — embedding multiple forms in one widget needs careful DOM isolation

**Recommendation:** Prove the backend slot resolution in isolation before building the UI. A simple test: POST a batch with `@slot1` references, verify the backend resolves them correctly.

### Medium Risk: Chart Widget Configuration
Chart.js supports many chart types (bar, line, pie, doughnut, radar, etc.) with extensive configuration. The challenge is designing a chart config UI that's powerful enough to be useful but simple enough for non-technical users. The SPARQL query must return data in a shape Chart.js can consume (labels + datasets).

**Recommendation:** Start with a fixed set of chart presets (bar, line, pie) that accept a simple SPARQL query returning `?label` and `?value` columns. Don't try to expose full Chart.js config.

### Low Risk: Stat-Card and Heading Widgets
These are straightforward:
- Stat-card: Execute a SPARQL query, display the scalar result with a label and optional icon
- Heading: Render a title/subtitle with configurable size — pure content, no data

### Low Risk: GridStack Enhancement
GridStack is already fully working in the builder. Enhancements (inline editing in viewer, save/load via GridStack API) are incremental changes to existing working code.

## Slice Boundaries

Natural boundaries based on risk ordering:

### Slice 1: New Data-Driven Widgets (stat-card, chart, heading)
- Register 3 new block types in BlockRegistry
- stat-card: SPARQL query → scalar display (count, sum, etc.)
- chart: SPARQL query → Chart.js visualization (bar, line, pie)
- heading: Static title/subtitle display
- Fix sparql-result block (wire up actual query execution)
- Fix markdown block to use marked.js
- Backend block rendering + frontend JS for data fetching
- Tests for new registry types, rendering, and SPARQL execution

### Slice 2: Widget Config Schemas & Builder UX
- Formalize config schemas (currently just Python type hints in BlockTypeSpec)
- Add config form HTML generation for new widget types in builder
- Chart type selector + query input + preview in builder
- Stat-card config: query, label, icon, color
- Heading config: text, level (h1-h4), alignment
- Builder palette updates with new categories

### Slice 3: Multi-Object Form Groups
- Backend: Slot-based IRI resolution in Command API (or dedicated endpoint)
- New `form-group` block type with sub-form slots
- Edge definitions between slots
- Sequential object creation with IRI back-references
- Partial failure handling
- Builder UI for configuring form group slots and edges

### Slice 4: Polish, Migration & Docs
- Dashboard viewer inline editing toggle (switch GridStack out of static mode)
- Auto-migration of existing dashboards if schema changes
- E2E Playwright tests
- User guide chapter updates

## Existing Patterns to Reuse

1. **BlockRegistry pattern** — Adding new types follows the exact same `BLOCK_REGISTRY.register(BlockTypeSpec(...))` pattern. No new infrastructure needed.
2. **Builder config form pattern** — `getTypeConfigHTML()` switch statement in the builder template. New types add new cases.
3. **Block rendering pattern** — Router's `render_block()` dispatches by type. New types add new `elif` branches returning HTML.
4. **SPARQL execution pattern** — `/api/sparql` POST with JSON body. Frontend `fetch()` call, parse results.
5. **Autocomplete pattern** — `_builderAutocomplete()` for IRI search fields in builder config forms.
6. **Command API batch pattern** — `POST /api/commands` with array payload. Extend for slot resolution.
7. **htmx lazy loading pattern** — Blocks use `hx-get` with `hx-trigger="load"` for content loading.
8. **dockview stacking context escape** — Popovers/dropdowns inside builder widgets need `document.body` append (KNOWLEDGE.md).

## Constraints

1. **Dashboard data is in SQLite, not RDF.** The CONTEXT.md mentions "RDF data model for block layouts" but the existing system uses SQLAlchemy/JSON. Moving to RDF would be a major migration with no clear benefit — SQLite JSON is simpler for structured config data. **Recommend keeping SQLite for dashboard definitions.**

2. **GridStack v10 CDN dependency.** Currently loaded from jsdelivr CDN in base.html. M029 (Frontend Performance) may have vendored this — needs verification. Either way, GridStack is already globally available.

3. **Chart.js needs lazy loading.** Currently only on admin pages. For workspace dashboard chart widgets, it should load on demand (not in the global bundle) to avoid penalizing pages that don't use charts.

4. **SHACL form isolation.** The create-form block already embeds a SHACL form via htmx. Multi-object form groups need multiple such forms in one widget, each targeting a different type. The forms must not interfere with each other's DOM state (IDs, form submission targets, validation). Each sub-form likely needs an `<iframe>` or careful DOM namespacing.

5. **Event isolation in dockview.** The builder already handles this (stopPropagation on drag events). New widgets that use interactive elements (chart tooltips, form inputs) must follow the same pattern.

## Candidate Requirements

Based on the research, these should be considered for the requirements contract:

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| BLK-01 | stat-card block type: SPARQL COUNT/SUM query → scalar display with label and icon | Table stakes | Core value of data-driven dashboards |
| BLK-02 | chart block type: SPARQL query → Chart.js visualization (bar, line, pie) | Table stakes | Visual analytics on knowledge data |
| BLK-03 | heading block type: configurable title/subtitle display | Table stakes | Basic layout/organization primitive |
| BLK-04 | sparql-result block: actually execute the query and display results | Table stakes | Existing block type that's currently broken |
| BLK-05 | markdown block: use marked.js for proper rendering | Table stakes | Existing block renders incorrectly |
| BLK-06 | Widget config schema formalization with type-checked validation | Nice-to-have | Current Python type hints work; JSON Schema adds flexibility but complexity |
| BLK-07 | Multi-object form group with slot-based IRI resolution | High value, high risk | The differentiating feature — enables multi-step creation workflows |
| BLK-08 | Chart.js lazy loading for workspace context | Table stakes if BLK-02 ships | Performance requirement |
| BLK-09 | Dashboard viewer inline editing toggle | Nice-to-have | Users can already edit via builder tab |
| BLK-10 | E2E Playwright tests for new block types | Table stakes | Regression prevention |
| BLK-11 | User guide documentation for new block types and form groups | Table stakes | Feature discoverability |

**Scope question for user:** Should the "RDF data model for block layouts" from the CONTEXT.md be pursued? The existing SQLite JSON approach is simpler, works well, and has 1,076 lines of tests. Migrating to RDF would be significant effort with unclear benefit for a per-user config store.

## Technology Notes

### GridStack v10 API (already in use)
- `GridStack.init(options, el)` — initialize grid
- `GridStack.setupDragIn(selector, options)` — external palette drag
- `grid.addWidget(options)` — programmatic widget add
- `grid.removeWidget(el)` — remove widget
- `grid.getGridItems()` — enumerate widgets with `.gridstackNode` positions
- `grid.save({saveContent: true})` — serialize to JSON
- `grid.load(items)` — restore from JSON
- Events: `dropped`, `change`, `added`, `removed`, `resizecontent`
- `staticGrid: true/false` — toggle edit mode

### Chart.js v4.4 (already on admin pages)
- `new Chart(canvasEl, {type, data, options})` — create chart
- Types: bar, line, pie, doughnut, radar, polarArea, scatter, bubble
- Data shape: `{labels: [...], datasets: [{label, data: [...], ...}]}`
- Already proven in the codebase on admin model detail charts

### SPARQL Result Shape for Widgets
Standard JSON format from `/api/sparql`:
```json
{
  "head": {"vars": ["label", "value"]},
  "results": {"bindings": [
    {"label": {"type": "literal", "value": "Projects"}, "value": {"type": "literal", "value": "42"}}
  ]}
}
```
Stat-card: expects 1 row, 1 value column.
Chart: expects N rows with label + value columns (or label + multiple value columns for multi-dataset).

## What Should Be Proven First

1. **Stat-card SPARQL execution round-trip.** Register the type, render the block, fetch + display query result. This validates the data-driven widget pattern end-to-end and unblocks chart (same pattern, more rendering).

2. **Chart.js lazy loading in workspace.** Confirm Chart.js can be loaded on demand inside a dockview panel dashboard without conflicts.

3. **Multi-object form slot resolution.** A backend-only test: submit a batch with `@slot` references, verify sequential creation with IRI back-filling. This de-risks the hardest feature before building UI.
