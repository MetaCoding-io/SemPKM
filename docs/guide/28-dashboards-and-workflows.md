# Chapter 28: Dashboards and Workflows

**Dashboards** let you combine multiple views, forms, markdown content, and SPARQL results into a single workspace tab with a configurable grid layout. **Workflows** let you define ordered sequences of steps that guide you through multi-step processes. Both are created, managed, and launched from the Explorer sidebar.

## Dashboards

A dashboard is a multi-block layout page. Instead of switching between separate view tabs, object editors, and forms, you arrange them side by side in a CSS Grid layout. Each block occupies a named slot in the grid, and blocks can communicate via cross-view context filtering.

### Layout Templates

When you create a dashboard, you choose one of five layout templates. The layout determines how many slots are available and how they are arranged.

| Layout | Slots | Description |
|--------|-------|-------------|
| **single** | main | One full-width block. Use for a single prominent view or large markdown panel. |
| **sidebar-main** | sidebar, main | A fixed 300px sidebar alongside a flexible main area. Ideal for a navigation list on the left and detail content on the right. |
| **grid-2x2** | top-left, top-right, bottom-left, bottom-right | Four equal quadrants. Good for comparing views or showing multiple data sources at once. |
| **grid-3** | left, center, right | Three equal columns. Useful for side-by-side comparisons or category groupings. |
| **top-bottom** | top, bottom | Two full-width rows stacked vertically. Suited for a summary on top and detail below. |

> **Tip:** The **sidebar-main** layout is the most versatile starting point. Place a list view in the sidebar with "emits context" enabled, and a filtered detail view in the main area to build a master-detail dashboard.

### Block Types

Each slot in a layout holds one block. Six block types are available:

| Block Type | Description |
|------------|-------------|
| **view-embed** | Embeds an existing view (table, card, or graph renderer). You select a view spec and renderer type. Supports cross-view context: can emit a context IRI on row click and/or listen to a context variable for filtering. |
| **markdown** | Renders static Markdown content. Use for headings, instructions, notes, or any explanatory text within the dashboard. |
| **object-embed** | Embeds a specific object's detail view by its IRI. Useful for pinning a reference object (e.g., a project brief) alongside related data. |
| **create-form** | Renders the SHACL-based creation form for a target class. Lets you create new objects directly from the dashboard without navigating to a separate form. |
| **sparql-result** | Runs a custom SPARQL query and displays the result with an optional label. Use for computed metrics, counts, or custom aggregations. |
| **divider** | A horizontal rule (`<hr>`) for visual separation. No configuration needed. |

### Creating a Dashboard

1. In the Explorer sidebar, find the **DASHBOARDS** section.
2. Click the **+** button in the section header.
3. The dashboard builder form opens in a new tab.
4. Enter a **Name** (required) and optional **Description**.
5. Select a **Layout** template from the radio button picker. The available slot names update to match your selection.
6. Click **Add Block** for each block you want. For each block:
   - Choose a **Type** from the dropdown (view-embed, markdown, etc.).
   - Choose a **Slot** to place the block in (the slots available depend on your chosen layout).
   - Fill in the type-specific configuration fields (e.g., select a view spec for view-embed, enter Markdown content for markdown).
7. Click **Save Dashboard**.

The dashboard opens as a new tab in the workspace, and the DASHBOARDS explorer list refreshes automatically.

> **Note:** Block types have different configuration fields. For **view-embed**, you select a view and renderer and optionally configure context options. For **markdown**, you enter content. For **create-form**, you provide the target class IRI. For **object-embed**, you provide the object IRI. For **sparql-result**, you write a SPARQL query and label.

### Editing a Dashboard

Click the **pencil icon** in the dashboard tab's header bar. This opens the dashboard builder form pre-populated with the existing name, description, layout, and blocks. Make your changes and click **Save Dashboard** to apply.

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

Suppose you have a **sidebar-main** layout:

- **Sidebar block:** A view-embed showing a table of all Projects, with "Emits context" enabled. Each row represents one project.
- **Main block:** A view-embed showing all Notes, with context variable `project`. The view's SPARQL query filters notes using `?project` (e.g., `?note :belongsTo ?project`).

When you click a project in the sidebar, the main area immediately refreshes to show only notes belonging to that project. Click a different project, and the notes update again.

> **Tip:** You can have multiple consumer blocks listening to the same context. For example, add a third block showing tasks filtered by the same `?project` variable.

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
| **Structure** | Grid layout with named slots | Ordered list of steps |
| **Content** | 6 block types (views, markdown, objects, forms, SPARQL, dividers) | 3 step types (views, dashboards, forms) |
| **Navigation** | All blocks visible at once | One step at a time with Previous/Next |
| **Interactivity** | Cross-view context filtering between blocks | Linear progression through steps |
| **Best for** | Side-by-side data comparison, master-detail layouts, operational dashboards | Onboarding sequences, review checklists, multi-step data entry |

> **Tip:** Workflows can include dashboard steps. Create a detailed dashboard first, then reference it as one step in a larger workflow. This combines the spatial layout of dashboards with the guided sequence of workflows.

---

**Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
