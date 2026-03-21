---
estimated_steps: 3
estimated_files: 3
skills_used: []
---

# T02: Update user guide chapters 7, 21, and 28 for M031 features

**Slice:** S07 — E2E Tests + User Guide Docs
**Milestone:** M031

## Description

Three user guide chapters reference removed features or lack documentation for new M031 features. Chapter 7 (Browsing and Visualizing) documents the removed carousel. Chapter 21 (SPARQL Console) lacks the new graph visualization tab. Chapter 28 (Dashboards and Workflows) lacks the new contextual help text, IRI autocomplete, and simplified workflow view step.

## Steps

1. **Update Chapter 7 (`docs/guide/07-browsing-and-visualizing.md`)**:
   - **Replace intro paragraph** (line 5): Remove "how to switch between views using the carousel navigation bar" and update to mention the view toolbar with scope binding and variant selection.
   - **Delete the entire "Carousel View Navigation" section** (lines 33–45, the `## Carousel View Navigation` heading through the end of "### How the Carousel Differs from Opening New Tabs" subsection) — 13 lines that describe removed functionality.
   - **Insert replacement sections** after "### View Tabs" and before "## Table View":
     - **"## View Toolbar"** — Describes the toolbar that appears at the top of every generic view. Two key dropdowns: (1) **Model-Declared View Variants** dropdown — appears when a type filter pill is active, shows type-specific views like "Projects Table" defined by the Mental Model. (2) **Saved Query Scope** dropdown — lets users filter the current view by a saved SPARQL query. Groups queries into "My Queries" and "Model Queries". Mention the "Save View" button (bookmark-plus icon) that saves the current configuration.
     - **"## Kanban View"** — New view type rendering objects as status-based columns. Explain: open from explorer sidebar "Kanban View" entry, select a type with status properties (e.g., Task), objects group into columns by status value (todo, in-progress, done), drag cards between columns to change status. Mention SHACL-driven status field detection (any property with `sh:in` values).
     - **"## Saved Views"** — Explain the Saved Views folder in the explorer sidebar. Users can save any current view configuration via the Save View button. Saved views appear in the explorer's VIEWS section. Click to reopen. Unpin via right-click or the remove button.
     - **"## Multiple View Instances"** — Users can open multiple tabs of the same view type (e.g., two Table Views with different scopes). Each opens as a separate dockview tab. Scoped tabs (same query) deduplicate; unscoped tabs always create fresh instances. Tab labels differentiate: scoped tabs show query name, unscoped duplicates get numeric suffixes.
     - **"## Saved Queries in Explorer"** — The QUERIES section in the explorer sidebar lists all saved SPARQL queries. Click a query to open a scoped Table View. Drag a query onto the spatial canvas to create an embedded view widget.

2. **Update Chapter 21 (`docs/guide/21-sparql-console.md`)**:
   - **Add "## Graph Visualization" section** after the "## Saving and Managing Queries" section (or near the end of the results documentation). Content:
     - When a query returns triple-pattern results (variables like `?s ?p ?o`), a **Table/Graph** tab switcher appears above the results.
     - Click the "Graph" tab to see an interactive Cytoscape.js visualization of the query results as a node-link diagram.
     - Subject and object values become nodes; predicates become directed edges.
     - Uses dagre layout for small graphs (<30 nodes), fcose for larger ones.
     - "Triple pattern detected" hint appears when the graph tab is available.
     - Tip: Use `SELECT ?s ?p ?o WHERE { ... }` queries to explore relationship patterns visually.

3. **Update Chapter 28 (`docs/guide/28-dashboards-and-workflows.md`)**:
   - **Add "## Builder Help Text" section** — Every field in the dashboard and workflow builders now has contextual help text (`<small class="field-help">`) explaining what to enter. This follows the SHACL helptext pattern used elsewhere in the app. No user action needed — help text appears automatically below each field.
   - **Add "## IRI Autocomplete"** section — When a builder field requires a class IRI (e.g., Target Class in create-form blocks) or object IRI (e.g., Object IRI in object-embed blocks), an autocomplete dropdown suggests matching items as you type. Class fields search loaded ontology classes; object fields search across all object labels.
   - **Add "## Simplified Workflow View Step"** section — The "view" step type in workflow builder no longer shows a raw renderer dropdown. Instead, selecting a view from the view picker automatically sets the renderer type (shown as a read-only badge). This reduces confusion and prevents mismatched view/renderer combinations.
   - **Add "## Sample Dashboards and Workflows"** section — On first launch (after setup), SemPKM creates a "Getting Started" dashboard and a "Create & Review" workflow as examples. These appear automatically in the explorer sidebar. They can be edited or deleted like any user-created dashboard or workflow.

## Must-Haves

- [ ] No carousel references remain in chapter 7 (no "carousel" substring anywhere)
- [ ] Chapter 7 has sections for View Toolbar, Kanban View, Saved Views, Multiple View Instances, and Saved Queries in Explorer
- [ ] Chapter 21 has a Graph Visualization section describing the triple-pattern graph tab
- [ ] Chapter 28 has sections for Builder Help Text, IRI Autocomplete, Simplified Workflow View Step, and Sample Dashboards

## Verification

- `! grep -qi "carousel" docs/guide/07-browsing-and-visualizing.md` — no carousel references
- `grep -q "## View Toolbar" docs/guide/07-browsing-and-visualizing.md` — view toolbar section exists
- `grep -q "## Kanban View" docs/guide/07-browsing-and-visualizing.md` — kanban section exists
- `grep -q "## Saved Views" docs/guide/07-browsing-and-visualizing.md` — saved views section exists
- `grep -q "## Multiple View Instances" docs/guide/07-browsing-and-visualizing.md` — multi-instance section
- `grep -q "## Graph Visualization" docs/guide/21-sparql-console.md` — graph tab section
- `grep -q "## IRI Autocomplete\|## Autocomplete" docs/guide/28-dashboards-and-workflows.md` — autocomplete section
- `grep -q "Sample" docs/guide/28-dashboards-and-workflows.md` — sample data section

## Inputs

- `docs/guide/07-browsing-and-visualizing.md` — current chapter with carousel content to replace (222 lines)
- `docs/guide/21-sparql-console.md` — current SPARQL chapter needing graph tab section (150 lines)
- `docs/guide/28-dashboards-and-workflows.md` — current dashboards chapter needing builder UX sections (170 lines)
- `frontend/static/js/workspace.js` — reference for openGenericViewTab behavior (line 3217)
- `backend/app/templates/browser/view_toolbar.html` — reference for toolbar dropdown names
- `backend/app/templates/browser/kanban_view.html` — reference for kanban view behavior
- `frontend/static/js/sparql-console.js` — reference for graph tab feature
- `backend/app/templates/browser/dashboard_builder.html` — reference for help text and autocomplete

## Expected Output

- `docs/guide/07-browsing-and-visualizing.md` — updated with 5 new sections replacing carousel content
- `docs/guide/21-sparql-console.md` — updated with Graph Visualization section
- `docs/guide/28-dashboards-and-workflows.md` — updated with 4 new builder UX sections
