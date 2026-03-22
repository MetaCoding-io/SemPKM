# Chapter 28: Dashboards and Workflows

**Dashboards** let you combine multiple views, forms, markdown content, data widgets, and SPARQL results into a single workspace tab with a drag-and-drop grid layout. **Workflows** let you define ordered sequences of steps that guide you through multi-step processes. Both are created, managed, and launched from the Explorer sidebar.

## Dashboards

A dashboard is a multi-block layout page. Instead of switching between separate view tabs, object editors, and forms, you arrange them side by side on a responsive grid. Each block can be freely positioned and resized, and blocks can communicate via cross-view context filtering.

### GridStack Layout

Dashboards use a **GridStack drag-and-drop layout** built on a 12-column responsive grid. Unlike the previous fixed layout templates, GridStack lets you place blocks anywhere on the grid and resize them freely.

- **12-column grid:** Blocks snap to a 12-column grid. A block can span 1–12 columns wide and any number of rows tall.
- **Drag to reposition:** Click and drag any block to move it to a new position on the grid. Other blocks rearrange automatically to avoid overlap.
- **Resize by dragging:** Drag any block's corners or edges to resize it. Minimum and maximum sizes are enforced per block type.
- **Default dimensions:** Each block type has sensible default dimensions (e.g., stat-cards default to 3 columns wide × 2 rows tall, dividers span the full 12 columns). You can adjust these after placement.

> **Note:** Dashboards created with the previous CSS Grid layout templates (single, sidebar-main, grid-2x2, grid-3, top-bottom) continue to work. They are displayed using their original fixed layouts. New dashboards always use the GridStack layout.

### Block Types

Each block on a dashboard has a type that determines what it displays and how it is configured. Ten block types are available:

| Block Type | Description |
|------------|-------------|
| **view-embed** | Embeds an existing view (table, card, or graph renderer). You select a view spec and renderer type. Supports cross-view context: can emit a context IRI on row click and/or listen to a context variable for filtering. |
| **markdown** | Renders full Markdown content using marked.js — headings, lists, code blocks, links, and inline formatting. Content is sanitized via DOMPurify. |
| **object-embed** | Embeds a specific object's detail view by its IRI. Useful for pinning a reference object (e.g., a project brief) alongside related data. |
| **create-form** | Renders the SHACL-based creation form for a target class. Lets you create new objects directly from the dashboard without navigating to a separate form. |
| **sparql-result** | Executes a SPARQL SELECT query and displays results in an interactive table. The query runs live against your knowledge base on load. |
| **divider** | A horizontal rule for visual separation between sections. No configuration needed. Spans the full 12-column width by default. |
| **stat-card** | Displays a single numeric value from a SPARQL query — ideal for counts, totals, and KPIs. Configure a SPARQL query that returns one value, a label, a Lucide icon, and an optional accent color. |
| **chart** | Renders a Chart.js visualization (bar, line, or pie chart) from SPARQL query results. The query must return `?label` and `?value` columns. Chart.js is loaded on demand only when a chart block is present. |
| **heading** | Displays a configurable title and optional subtitle at heading levels h1–h4 with text alignment. Use for section dividers and dashboard headers. |
| **form-group** | Creates multiple linked objects in one submission. Contains two or more SHACL sub-forms (slots), with edges automatically created between the resulting objects. |

### Data Widgets

Three block types — **stat-card**, **chart**, and **sparql-result** — execute live SPARQL queries to display data from your knowledge base. Each has different configuration requirements.

#### Stat Card

A stat card shows a single numeric value with a label and icon. Use it for KPIs, counts, and summary metrics.

**Configuration:**

- **Query:** A SPARQL SELECT query that returns one row with one value. Typically a COUNT or SUM aggregation.
- **Label:** A short descriptive label displayed below the number (e.g., "Active Projects").
- **Icon:** A Lucide icon name displayed alongside the value (e.g., `folder`, `check-circle`, `alert-triangle`).
- **Color:** An optional CSS accent color for the icon and value (e.g., `#10b981` for green, `#f59e0b` for amber).

**Example query:**

```sparql
SELECT (COUNT(*) AS ?count) WHERE { ?s a bpkm:Project }
```

This counts all Project objects in your knowledge base and displays the result as a large number with your chosen label and icon.

#### Chart

A chart block renders a Chart.js visualization — bar chart, line chart, or pie chart — from query results.

**Configuration:**

- **Query:** A SPARQL SELECT query that returns `?label` and `?value` columns. Each row becomes one data point.
- **Chart type:** One of `bar`, `line`, or `pie`.
- **Label:** An optional title displayed above the chart.

**Example query:**

```sparql
SELECT ?label (COUNT(*) AS ?value) WHERE {
  ?s a ?type .
  BIND(STRAFTER(STR(?type), "#") AS ?label)
} GROUP BY ?label
```

This counts objects by type and displays the result as a chart, with type names as labels and counts as values.

> **Tip:** Chart.js is only loaded when a dashboard contains at least one chart block, so dashboards without charts have no extra overhead.

#### SPARQL Result Table

A SPARQL result block runs any SELECT query and displays the results in a sortable table with column headers derived from query variable names.

**Configuration:**

- **Query:** Any SPARQL SELECT query. Column headers are taken from the query variable names (e.g., `?name`, `?created`).
- **Label:** An optional title displayed above the results table.

**Example query:**

```sparql
SELECT ?name ?created WHERE {
  ?s a bpkm:Note ;
     dcterms:title ?name ;
     dcterms:created ?created .
} ORDER BY DESC(?created) LIMIT 10
```

This shows the 10 most recently created notes with their titles and creation dates.

### Form Groups

A **form-group** block lets you create multiple linked objects in a single submission. Instead of creating each object separately and then manually adding relationships between them, a form group handles everything at once.

#### Concepts

- **Slots:** A form group contains two or more slots. Each slot renders a SHACL creation form for a specific target class (e.g., one slot for a Note, another for a Task).
- **Edges:** You configure edges between slots that define relationships. An edge specifies a source slot, a target slot, and a predicate IRI. When the form group is submitted, the system automatically creates RDF triples linking the new objects.
- **Batch creation:** All objects and their connecting edges are created in a single batch operation via the Command API. If any part fails, the entire batch is rolled back.
- **Slot-based IRI resolution:** When configuring edges, you reference slots by their index (Slot 1, Slot 2, etc.). The system resolves these to the actual IRIs of the newly created objects at submission time.

#### Example: Note + Task Form Group

A practical form group might contain:

1. **Slot 1:** A Note creation form (target class: `bpkm:Note`)
2. **Slot 2:** A Task creation form (target class: `bpkm:Task`)
3. **Edge:** Slot 1 → Slot 2 via predicate `bpkm:relatedTo`

When a user fills out both forms and clicks **Submit**, the system:
1. Creates the Note object from Slot 1's form data
2. Creates the Task object from Slot 2's form data
3. Creates a triple linking the Note to the Task: `<note-iri> bpkm:relatedTo <task-iri>`

This is especially useful for workflows where objects are always created together — like meeting notes with action items, or requirements with test cases.

### Creating a Dashboard

1. In the Explorer sidebar, find the **DASHBOARDS** section.
2. Click the **+** button in the section header.
3. The dashboard builder form opens in a new tab.
4. Enter a **Name** (required) and optional **Description**.
5. Add blocks to your dashboard. For each block:
   - Choose a **Type** from the block palette (stat-card, chart, markdown, etc.).
   - Fill in the type-specific configuration fields (e.g., enter a SPARQL query for stat-card, choose a chart type for chart, enter Markdown content for markdown).
6. Arrange your blocks on the grid by dragging them to the desired position and resizing as needed.
7. Click **Save Dashboard**.

The dashboard opens as a new tab in the workspace, and the DASHBOARDS explorer list refreshes automatically.

> **Note:** Block types have different configuration fields. For **view-embed**, you select a view and renderer and optionally configure context options. For **stat-card** and **chart**, you write a SPARQL query. For **create-form**, you provide the target class IRI. For **heading**, you enter a title, level, and optional subtitle.

### Editing a Dashboard

Click the **pencil icon** in the dashboard tab's header bar. This opens the dashboard builder form pre-populated with the existing name, description, and blocks. Rearrange blocks by dragging, resize them, add new blocks, or remove existing ones. Click **Save Dashboard** to apply.

### Deleting a Dashboard

In the Explorer sidebar under **DASHBOARDS**, hover over the dashboard you want to remove and click the **trash icon**. A confirmation dialog appears. Confirm to permanently delete the dashboard.

### Cross-View Context Filtering

Cross-view context filtering lets one block drive the data shown in other blocks. This is the mechanism for building master-detail dashboards.

**How it works:**

1. A **source block** (a view-embed with "Emits context" checked) publishes a context IRI when the user clicks a row.
2. One or more **consumer blocks** (view-embeds with a "Context variable" set) re-fetch their data with the context IRI bound to the specified SPARQL variable.

**Configuration:**

- On the source block: check the **Emits context** checkbox. When a user clicks a row in this view, the row's IRI becomes the dashboard's current context.
- On each consumer block: enter a **Context variable** name (e.g., `project`). The consumer block's view query should use this variable — when context is set, the view re-fetches with `?project` bound to the selected IRI.

**Practical example — Project dashboard:**

- **Left block:** A view-embed showing a table of all Projects, with "Emits context" enabled. Each row represents one project.
- **Right block:** A view-embed showing all Notes, with context variable `project`. The view's SPARQL query filters notes using `?project` (e.g., `?note :belongsTo ?project`).

When you click a project on the left, the right side immediately refreshes to show only notes belonging to that project. Click a different project, and the notes update again.

> **Tip:** You can have multiple consumer blocks listening to the same context. For example, add a stat-card that counts tasks filtered by the same `?project` variable.

## Workflows

A workflow is an ordered sequence of steps that guides you through a multi-step process. Each step opens a view, dashboard, or form. A stepper bar shows your progress, and Previous/Next buttons let you navigate between steps.

### Step Types

Each step in a workflow has a type that determines what it displays:

| Step Type | Description |
|-----------|-------------|
| **view** | Opens an existing view (table, card, or graph). You select a view spec and renderer type. |
| **dashboard** | Opens an existing dashboard by its ID. The full dashboard renders inside the workflow step, including any cross-view context filtering. |
| **form** | Opens a SHACL-based creation form for a target class. Use for data entry steps in the workflow. |

### Creating a Workflow

1. In the Explorer sidebar, find the **WORKFLOWS** section.
2. Click the **+** button in the section header.
3. The workflow builder form opens in a new tab.
4. Enter a **Name** (required) and optional **Description**.
5. Click **Add Step** for each step in the workflow. For each step:
   - Enter an optional **Step label** (displayed in the stepper bar, e.g., "Review Projects", "Create Note").
   - Choose a **Type** (view, dashboard, or form).
   - Fill in the type-specific configuration (select a view, pick a dashboard, or enter a target class IRI).
6. Click **Save Workflow**.

The workflow opens in the runner view, and the WORKFLOWS explorer list refreshes automatically.

> **Note:** Steps execute in the order you add them. The first step loads automatically when the workflow opens.

### Running a Workflow

Click a workflow in the Explorer sidebar to open it. The workflow runner displays:

- **Stepper bar** — A horizontal row of numbered step indicators with labels. The current step is highlighted as active. Completed steps (those you've moved past) show as completed.
- **Step content area** — The view, dashboard, or form for the current step loads here via htmx.
- **Navigation buttons** — **← Previous** and **Next →** buttons move between steps. The Previous button is disabled on the first step; the Next button is disabled on the last step.
- **Step counter** — Shows "Step X of Y" below the content area.

To work through the workflow, complete the action in each step (review data, fill a form, etc.), then click **Next →** to advance. Use **← Previous** to go back and revisit an earlier step.

### Editing a Workflow

Open the workflow builder by clicking the edit action on a workflow. The builder loads pre-populated with existing steps. Add, remove, or reorder steps, then click **Save Workflow**.

### Deleting a Workflow

In the Explorer sidebar under **WORKFLOWS**, hover over the workflow and click the **trash icon**. Confirm the deletion in the dialog that appears.

## Builder Help Text

Every field in the dashboard and workflow builders includes **contextual help text** — a short description that appears directly below the field, explaining what to enter and how it is used. This follows the same pattern as SHACL-generated help text used elsewhere in SemPKM (e.g., object edit forms).

Help text is displayed automatically as small, muted text beneath each input field. No user action is required — the guidance is always visible while you are building or editing a dashboard or workflow. Examples include:

- **Name field:** "A short, descriptive name for this dashboard."
- **Query field:** "A SPARQL SELECT query. For stat-cards, return one row with one value."
- **View spec field:** "The view definition to embed. It determines what data and columns appear."
- **Target Class field:** "The RDF type IRI for the object creation form (e.g. a class from your model)."

## IRI Autocomplete

When a builder field requires a **class IRI** or **object IRI**, an autocomplete dropdown appears as you type, suggesting matching items from your knowledge base.

### Class IRI Autocomplete

Fields that expect a class IRI — such as the **Target Class** field in create-form blocks, form-group slots, or workflow form steps — search across all classes loaded from your installed ontologies. Start typing a class name (e.g., "Project" or "Note") and a dropdown lists matching classes with their full IRIs. Click a suggestion to populate the field.

### Object IRI Autocomplete

Fields that expect a specific object IRI — such as the **Object IRI** field in object-embed blocks — search across all objects in your knowledge base by their labels. Start typing an object's name and the dropdown shows matching objects. Click a suggestion to fill the field with the object's IRI.

> **Tip:** Autocomplete searches are case-insensitive and match against object labels, so you do not need to know the full IRI. Just type part of the name.

## Simplified Workflow View Step

The **view** step type in the workflow builder has been simplified. Previously, selecting a view and a renderer type were separate choices, which could lead to mismatched combinations (e.g., picking a table view with a graph renderer).

Now, selecting a view from the view picker **automatically sets the renderer type**, which is displayed as a read-only badge next to the view name (e.g., "(table)" or "(graph)"). You no longer need to manually choose a renderer — the correct one is determined by the view specification itself. This reduces configuration errors and makes the workflow builder easier to use.

## Sample Dashboards and Workflows

On first launch (after initial setup), SemPKM automatically creates two sample items to help new users get started:

- **"Getting Started" dashboard** — A layout with a welcome message (Markdown block) and an embedded table view. This demonstrates how dashboards combine different block types into a single workspace view.
- **"Create & Review" workflow** — A two-step workflow: the first step opens a creation form, and the second step opens a table view for reviewing items. This demonstrates how workflows guide users through multi-step processes.

Both samples appear automatically in the Explorer sidebar under the DASHBOARDS and WORKFLOWS sections. They can be edited or deleted just like any user-created dashboard or workflow. If you delete them, they will not be recreated.

## Explorer Sidebar Sections

The Explorer sidebar includes dedicated sections for dashboards and workflows:

### DASHBOARDS Section

- **Header:** Displays "DASHBOARDS" with a **+** button to create a new dashboard.
- **Listing:** Shows all dashboards for the current user. Click a dashboard name to open it as a tab.
- **Actions:** Each dashboard entry has a **trash icon** for deletion (with confirmation).
- **Auto-refresh:** The list refreshes automatically after creating, editing, or deleting a dashboard.

### WORKFLOWS Section

- **Header:** Displays "WORKFLOWS" with a **+** button to create a new workflow.
- **Listing:** Shows all workflows for the current user. Click a workflow name to open the runner.
- **Actions:** Each workflow entry has a **trash icon** for deletion (with confirmation).
- **Auto-refresh:** The list refreshes automatically after creating, editing, or deleting a workflow.

Both sections support the Explorer's drag-to-reorder panel positioning and the expand/collapse chevron toggle.

## Dashboard vs. Workflow

| | Dashboard | Workflow |
|---|---|---|
| **Purpose** | Combine multiple content blocks into one view | Guide a user through ordered steps |
| **Structure** | Drag-and-drop GridStack layout (12-column grid) | Ordered list of steps |
| **Content** | 10 block types (views, stat-cards, charts, headings, markdown, objects, forms, form-groups, SPARQL results, dividers) | 3 step types (views, dashboards, forms) |
| **Navigation** | All blocks visible at once | One step at a time with Previous/Next |
| **Interactivity** | Cross-view context filtering between blocks | Linear progression through steps |
| **Best for** | KPI dashboards, master-detail layouts, data visualization, multi-object creation | Onboarding sequences, review checklists, multi-step data entry |

> **Tip:** Workflows can include dashboard steps. Create a detailed dashboard first, then reference it as one step in a larger workflow. This combines the spatial layout of dashboards with the guided sequence of workflows.

---

**Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Chapter 29: App Platform](29-app-platform.md)
