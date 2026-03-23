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

## Task Templates

A **task template** is a reusable blueprint for creating objects with pre-filled properties and optional linked subtasks. Instead of filling out the same form fields every time you create a recurring type of task, project, or note, you define a template once and instantiate it whenever you need a new copy.

Templates are stored in the knowledge base as RDF data in a dedicated graph (`urn:sempkm:task-templates`), so they persist across sessions and are available to all features that use the command pipeline.

### What a Template Contains

Each template stores four pieces of information:

| Field | Description |
|-------|-------------|
| **Title** | A human-readable name for the template (e.g., "Bug Report", "Sprint Planning Task"). |
| **Target Class** | The RDF type IRI of the object to create (e.g., `bpkm:Task`, `bpkm:Note`). This determines which SHACL form is used. |
| **Default Properties** | A key→value map of properties that are pre-filled on every object created from this template. For example, a "Bug Report" template might set `bpkm:taskStatus` to "Open" and `dcterms:description` to a bug report outline. |
| **Subtask Definitions** | An optional list of linked objects created alongside the main object. Each subtask definition specifies a title, an optional type (defaults to the parent's target class), optional properties, and a relationship predicate (defaults to `sempkm:subtaskOf`). |

### Creating a Template

Templates are currently created via the REST API:

```
POST /api/task-templates
Content-Type: application/json

{
  "title": "Sprint Planning Task",
  "target_class": "urn:sempkm:model:basic-pkm:Task",
  "default_properties": {
    "bpkm:taskStatus": "Open",
    "dcterms:description": "Plan the upcoming sprint."
  },
  "subtask_definitions": [
    {
      "title": "Review backlog",
      "properties": { "bpkm:taskStatus": "Open" }
    },
    {
      "title": "Assign story points",
      "properties": { "bpkm:taskStatus": "Open" }
    }
  ]
}
```

This creates a template that, when instantiated, produces a main "Sprint Planning Task" plus two linked subtasks — "Review backlog" and "Assign story points" — each connected to the main task via `sempkm:subtaskOf`.

### Editing and Deleting Templates

Update any field on an existing template with a PATCH request:

```
PATCH /api/task-templates/{template_id}
Content-Type: application/json

{ "title": "Updated Template Name" }
```

Only the fields you include are changed; omitted fields retain their current values. Delete a template with:

```
DELETE /api/task-templates/{template_id}
```

Deleting a template does not affect objects that were previously created from it — they are independent objects in your knowledge base.

### Using "Create from Template" via the Command Palette

The most common way to instantiate a template is through the **command palette** (<kbd>Alt</kbd>+<kbd>K</kbd>):

1. Open the command palette with <kbd>Alt</kbd>+<kbd>K</kbd>.
2. Select **Create from Template** from the Objects section.
3. A submenu lists all available templates by name. Select the template you want.
4. The system instantiates the template — creating the main object and any subtasks — and opens the new object in a workspace tab.

The template submenu refreshes automatically when the workspace loads, so newly created templates appear immediately.

### How Instantiation Works

When you instantiate a template, the system builds a **batch command payload** that creates all objects in a single atomic operation:

1. **Main object:** An `object.create` command creates the primary object with the template's target class and default properties. This command registers its IRI in a slot named `"main"`.
2. **Subtasks:** For each subtask definition, an `object.create` command creates the subtask object, followed by an `edge.create` command that links it to the main object using `@slot:main` references.
3. **Atomic commit:** All commands are dispatched through the batch command pipeline and committed as a single event. If any part fails, the entire batch is rolled back.
4. **Overrides:** You can pass property overrides at instantiation time that are merged on top of the template's default properties. Overrides take precedence over defaults.

The `@slot:` reference convention lets subtask commands refer to the main object's IRI before it exists — the slot is resolved to the actual minted IRI at dispatch time. This is the same mechanism used by form-group blocks in dashboards (see [Form Groups](#form-groups) above).

> **Tip:** Templates complement form groups. Use a form group when you want a visual multi-form UI on a dashboard. Use a template when you want a one-click creation shortcut from the command palette with consistent defaults.

## Review Workflows

SemPKM ships with **seeded review workflows** that implement structured periodic reviews — a practice drawn from personal productivity methodologies like PPV (Pillars, Pipelines, Vaults). These workflows guide you through reviewing past work, logging new entries, and checking progress, all in a step-by-step sequence.

Review workflows are standard workflows (see [Workflows](#workflows) above) with steps pre-configured to reference views and forms from the **PPV Mental Model**. They are created automatically on first launch when the PPV model is installed.

### The Seeded Review Workflows

Five review workflows are seeded by default:

| Workflow | Steps | What It Guides You Through |
|----------|-------|---------------------------|
| **Create & Review** | 2 steps | A simple sample: create an item, then review it in a table view. Uses generic (non-PPV) views. |
| **Weekly Review** | 4 steps | (1) Review past weekly reviews → (2) Scan completed actions → (3) Create a new weekly review → (4) Confirm in a graph view. |
| **Monthly Review** | 4 steps | (1) Review past monthly entries → (2) Scan this month's weekly reviews → (3) Create a new monthly review → (4) Check goal progress. |
| **Quarterly Review** | 3 steps | (1) Review past quarterly entries → (2) Create a new quarterly review → (3) Assess goals overview. |
| **Yearly Review** | 3 steps | (1) Review past yearly entries → (2) Create a new yearly review → (3) See the full value-goal hierarchy in a graph. |

Each PPV review workflow uses views and forms that are defined in the PPV model's view specifications. The step labels describe the purpose — "Past Reviews", "Completed Work", "Create Review", "Goal Progress", etc. — so you always know what each step is for.

### Launching a Review from the Command Palette

The four PPV review workflows (Weekly, Monthly, Quarterly, Yearly) each have a dedicated command palette entry:

1. Open the command palette with <kbd>Alt</kbd>+<kbd>K</kbd>.
2. In the **Workflows** section, select one of:
   - **Run Weekly Review**
   - **Run Monthly Review**
   - **Run Quarterly Review**
   - **Run Yearly Review**
3. The workflow runner opens in a new workspace tab, starting at step 1.

Behind the scenes, the command palette fetches the workflow list from the API, finds the workflow by name, and opens it in the workflow runner. If the PPV model is not installed (and therefore the seeded workflows don't exist), a toast notification explains that the review workflow was not found.

### Stepping Through a Review

Once a review workflow is running, the workflow runner interface is the same as any other workflow:

- The **stepper bar** at the top shows all steps with labels. The current step is highlighted.
- The **step content area** loads the appropriate view or form for each step via htmx.
- **← Previous** and **Next →** buttons navigate between steps.
- The **step counter** shows your position (e.g., "Step 2 of 4").

A typical weekly review session looks like:

1. **Step 1 — Past Reviews:** A table view of previous weekly reviews. Scan what you wrote last time to maintain continuity.
2. **Step 2 — Completed Work:** A table view of actions/tasks. Check off what you accomplished this week.
3. **Step 3 — Create Review:** A SHACL creation form for `WeeklyReview`. Fill in your reflections, wins, and areas for improvement.
4. **Step 4 — Confirm:** A graph view showing the newly created review and its connections. Verify everything looks correct.

### Customizing Review Workflows

Because review workflows are standard workflows, you can edit them just like any other workflow:

- **Modify steps:** Open the workflow builder and add, remove, or reorder steps. For example, add a stat-card dashboard step that shows KPI metrics before the review form.
- **Change views:** Swap the default PPV views for custom views that better match your review process.
- **Delete and recreate:** If you delete a seeded review workflow, it will not be recreated automatically. Create a new workflow with your preferred steps to replace it.
- **Create your own:** Build entirely custom review workflows using any combination of view, dashboard, and form steps. The seeded workflows are starting points, not fixed processes.

> **Tip:** Pair review workflows with task templates. Create a "Weekly Review" task template that pre-fills common fields, then use the review workflow to guide the full review process. The template handles object creation; the workflow handles the review sequence.

### PPV Model Dependency

The Weekly, Monthly, Quarterly, and Yearly review workflows depend on the **PPV (Pillars, Pipelines, Vaults) Mental Model** being installed. Specifically, they reference:

- **PPV review types:** `WeeklyReview`, `MonthlyReview`, `QuarterlyReview`, `YearlyReview` — used as target classes in form steps.
- **PPV view specs:** Table and graph views for reviews, actions, goals, and the value-goal hierarchy — used in view steps.

If the PPV model is not installed, the seeded workflows are not created (they are seeded only when the model's views are available). The "Create & Review" sample workflow uses generic views and does not depend on PPV.

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
