# Research: Custom Dashboards & Guided Workflows for SemPKM

**Date:** 2026-03-13
**Status:** Research & Plan
**Goal:** Enable users to (1) build custom interactive dashboards that compose views, objects, and creation forms, and (2) chain views into guided workflows (e.g., "Weekly Reflection" that walks through multiple screens).

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [State of the Art](#state-of-the-art)
3. [Key Projects & Tools Deep Dive](#key-projects--tools-deep-dive)
4. [What SemPKM Already Has](#what-sempkm-already-has)
5. [Architecture Design](#architecture-design)
6. [Implementation Plan](#implementation-plan)
7. [Open Questions](#open-questions)

---

## 1. Problem Statement

### Goal 1: Custom Dashboard Screens

Users should be able to compose **dashboard pages** that contain:

- **Embedded views** — existing ViewSpecs (tables, cards, graphs) rendered as panels within the dashboard
- **Embedded objects** — individual object read/edit views pinned to a dashboard
- **Creation forms** — inline object creation forms (driven by SHACL shapes) that write into the knowledge graph
- **Static content** — markdown text blocks, headers, dividers for organization
- **Layout control** — arranging these blocks in rows/columns/grids

This is the intersection of:
- **Notion** — pages composed of typed blocks (text, tables, databases, embeds)
- **Airtable** — multiple views on the same structured data with different rendering
- **Retool/Appsmith** — drag-and-drop low-code dashboards with data bindings

### Goal 2: Guided Workflows

Users should be able to chain screens into **sequential workflows**:

- A workflow defines an ordered sequence of steps
- Each step presents a view, a form, or a dashboard
- Users navigate forward/back through steps
- Context can flow between steps (e.g., "the project you selected in step 1 filters notes in step 2")
- Example: **Weekly Reflection** workflow → Step 1: Review inbox notes (table view) → Step 2: Tag/categorize (card view with edit) → Step 3: Link to projects (graph view) → Step 4: Write weekly summary (create Note form)

---

## 2. State of the Art

### 2.1 Notion's Block Model

Notion treats everything as a **block** — text, headings, images, databases, and embedded views are all blocks in a tree structure. A page is just a root block containing children.

**Key concepts for SemPKM:**
- Block = { type, properties, children[] }
- Database views are blocks that reference a "database" (= a typed collection) with a view configuration (table, board, calendar, gallery)
- Templates: blocks can be templated and instantiated
- Synced blocks: the same block can appear in multiple pages

**What to adopt:** The block-tree page model. A "Dashboard" is a page made of blocks. Each block type maps to a SemPKM primitive.

**What to skip:** Notion's database/view coupling is complex. SemPKM already has ViewSpecs backed by SPARQL which is more powerful.

### 2.2 Airtable's Interface Designer

Airtable separates **data** (tables/fields) from **interfaces** (custom screens). Interfaces use:
- A drag-and-drop canvas with a grid layout
- Widgets: record list, record detail, chart, button, text, filter bar
- Data binding: each widget is bound to a table + view + filter
- Conditional visibility and record-scoped views

**Key concepts for SemPKM:**
- Layout grid with widget slots
- Widgets bound to data queries (≈ ViewSpecs)
- Record context — clicking a row in one widget filters another
- Interface ≠ view — interfaces compose multiple views

**What to adopt:** The widget-on-grid model with data bindings. The concept of "record context" flowing between widgets.

**What to skip:** Airtable's rigid table model. SemPKM's RDF graph is far more flexible.

### 2.3 Retool / Appsmith (Low-Code App Builders)

These tools provide:
- A component palette (tables, forms, charts, text, buttons, modals)
- A property panel (configure each component's data source, appearance, behavior)
- Event handlers (onClick → run query, set variable, navigate)
- State management (temporary state variables, URL params)
- Query editor (SQL, REST API, GraphQL — for us, SPARQL)

**Key concepts for SemPKM:**
- Components are generic containers with typed configurations
- Events wire components together (selection in table A → filters in table B)
- Temporary state (selected_record, filter_value) enables cross-component communication
- Queries are first-class objects (SPARQL queries === data sources)

**What to adopt:** Event-driven component wiring and temporary state. The idea that SPARQL queries are parameterizable data sources.

**What to skip:** The full IDE experience. We want something simpler — closer to Notion's ease of use than Retool's power-user complexity.

### 2.4 BESSER-PEARL & Model-Driven Software Engineering (MDSE)

[BESSER](https://github.com/BESSER-PEARL) (Building bEtter Smart Software fastER) is Jordi Cabot's group's open-source low-code platform built on MDSE principles. Key components:

**B-UML (BESSER Unified Modeling Language):**
- A Python-based modeling language for defining domain models
- Classes, attributes, relationships, enumerations — similar to UML class diagrams
- Models are Python objects that can be programmatically transformed

**Code Generators:**
- From a B-UML model, BESSER generates: Django models, SQLAlchemy ORM, REST APIs, GUI (Streamlit), database schemas
- The key insight: **one model, many artifacts** — define the domain once, generate multiple representations

**BUML-to-GUI Pipeline:**
- Uses model transformations to generate Streamlit UIs from class diagrams
- Each class gets CRUD screens automatically
- Relationships generate navigation links between screens

**Relevance to SemPKM:**
- SemPKM's Mental Models (OWL ontology + SHACL shapes) already serve as the "domain model"
- SHACL shapes already drive form generation (like BESSER's BUML→GUI)
- ViewSpecs are essentially "view models" — declarative descriptions of how to render data
- **The gap:** SemPKM has the model→view pipeline for individual views, but lacks the **composition layer** (dashboard = multiple views arranged in a layout) and the **workflow layer** (sequence of screens with state flow)

**What to adopt from MDSE:**
- The principle of **model-driven composition**: dashboards and workflows should themselves be models (stored as RDF), not hardcoded templates
- **Metamodel-driven generation**: just as SHACL shapes drive form generation, a "DashboardSpec" schema should drive dashboard rendering
- **Transformation chains**: model → view → composed dashboard → workflow is a natural MDSE pipeline

### 2.5 Workflow Engines & PKM Automation

**Tana (PKM with workflows):**
- "Command nodes" chain operations: search → filter → transform → create
- Workflows are first-class objects in the knowledge graph
- Each step has inputs/outputs typed by the node schema

**Capacities (structured note-taking with workflows):**
- Daily workflow templates with sequenced pages
- Each page in a workflow can embed different views
- Progress indicator showing completion

**n8n / Temporal (general workflow engines):**
- Step = { action, input_schema, output_schema, next_step }
- Conditional branching (if/else on outputs)
- State passed as JSON between steps

**Key insight for SemPKM:** For PKM workflows, we don't need a full process engine. We need **guided navigation** — a sequence of screens where each screen can optionally filter based on prior screen selections. Think "wizard" more than "workflow engine."

### 2.6 Open-Source Projects at the Intersection

**Directus** — headless CMS with custom dashboards composed of panels (metrics, lists, charts). Dashboard layout stored as JSON. Each panel is a Vue component with a data source binding. Closest open-source model to what we want.

**Baserow** — open-source Airtable. Has views but no dashboard composition layer yet.

**NocoDB** — open-source Airtable. Same limitation.

**Plasmic** — visual builder that can compose React components. Overkill for our needs but interesting data binding approach.

**Ontology-based UI generation (academic):**
- OWL2UI (2020) — generates web forms from OWL ontologies
- RDFS-based UI adaptation (Semantic Web Journal, 2022) — adapts UI components based on RDF class properties
- These validate our approach: SHACL/OWL → UI generation is a recognized pattern

---

## 3. Key Projects & Tools Deep Dive

### 3.1 BESSER-PEARL: Full Architecture

[BESSER](https://github.com/BESSER-PEARL/BESSER) (Building bEtter Smart Software fastER) is a Python-based open-source low-code platform led by Jordi Cabot at the Luxembourg Institute of Science and Technology (LIST). Out of 151 surveyed open-source low-code tools, only 9 use any type of model — BESSER is one of them.

**B-UML (BESSER's Universal Modeling Language)** is the foundation — a Python-based simplified UML that's divided into sublanguages:

| Sublanguage | What It Models |
|---|---|
| **Structural model** | Classes, Properties, Associations, Generalizations (≈ UML class diagram) |
| **GUI model** | 4 layers: structural organization (GUIModel > Modules > Screens > ViewContainers), visual composition (ViewElements: buttons, forms, lists), presentation (Layout, Position, Size), interaction (data bindings, actions) |
| **State Machine model** | Events, Actions, States with Bodies (action sequences), Sessions, Conditions, Transitions |
| **Object model** | Instance-level specifications |
| **OCL specification** | Constraints |
| **Agent model** | AI agent specifications |

**Code Generators (Model-to-Text via Jinja):** Django (with admin + UI), Python classes, Java, Pydantic, SQLAlchemy, SQL schema, REST API, Flutter, **RDF** (outputs `vocabulary.ttl` in Turtle), JSON Schema, PyTorch, TensorFlow.

**The GUI Metamodel** is most relevant to us:
```
GUIModel > Module > Screen > ViewContainer > ViewElement
                                   ↓
                              Layout (Position, Size, Alignment)
                                   ↓
                              DataBindings + Actions
```

This is exactly the hierarchical structure we need for DashboardSpec. Each ViewContainer maps to a "slot" in our grid layout, each ViewElement maps to a block type.

**RDF Generator:** Transforms B-UML structural models into RDF/RDFS vocabularies — Classes → `rdfs:Class`, Properties → `rdf:Property` with `rdfs:domain`/`rdfs:range`. This proves B-UML ↔ RDF is viable, but the flow is currently one-directional (B-UML → RDF). SemPKM would need the reverse: **ontology → structural model → UI generation**.

**Model Building:** Models can be created via Python API, PlantUML grammar, Draw.io import, **image-to-model (LLM)**, and a browser-based graphical editor.

### 3.2 LinkedDataHub (Most Relevant Existing System)

[LinkedDataHub](https://github.com/AtomGraph/LinkedDataHub) by AtomGraph is the **only production system** that builds full applications directly from RDF data with a declarative UI layer:

- Applications defined as RDF data (not source code)
- Every document is a named graph in a Graph Store
- UI rendering via XSLT 3.0 declarative transformations
- Version 5 (2025) adds: block-centric content model (each block = RDF resource with its own URI), dual-phase rendering (server XHTML+RDFa, then client-side SaxonJS hydration), and **AI agent integration via Web-Algebra** (natural language → JSON-formatted RDF operations, with MCP support)

This is the closest existing system to what SemPKM is building. Key difference: they use XSLT for rendering, we use htmx + Jinja2.

### 3.3 NocoBase (Architecture Reference)

[NocoBase](https://github.com/nocobase/nocobase) is the closest open-source implementation to "model-driven custom views on structured data":

- Data models defined independently via a plugin microkernel
- UI defined as JSON schemas, **decoupled from data models**
- Pattern: **Collection (data model) → Block (UI component) → Page (layout)**

This maps naturally to SemPKM's: **Ontology class → ViewSpec/Block → Dashboard**

### 3.4 Open-Source Dashboard Builder Landscape (2026)

| Tool | Approach | Relevance |
|---|---|---|
| **ToolJet** | Drag-and-drop + data connectors, AI-native | Component model reference |
| **Appsmith** | Widget-based, strong JS customization | Event wiring patterns |
| **NocoBase** | Data-model-driven, plugin microkernel | Closest to MDSE principles |
| **Baserow** | Spreadsheet-first (Django/Vue), open Airtable | Pages/dashboards model |
| **Metabase** | BI/analytics, visual query builder | Data exploration UX |
| **Grafana** | Monitoring dashboards, multi-source | Panel layout system reference |
| **Directus** | Headless CMS, custom dashboard panels | Panel composition model |

### 3.5 Workflow-Relevant Tools

**BESSER State Machine model** — Events, States with Bodies, Conditions, Transitions, concurrent Sessions with private data. Suitable for multi-step PKM processes.

**BESSER Agentic BPMN** — BPMN extension for human-agent collaborative workflows (SEAA 2025).

**n8n** — 400+ integrations, AI-native workflow automation. Good for backend automation but too complex for guided user workflows.

**Tana** — "Command nodes" that chain search → filter → transform → create. Workflows are first-class objects in the knowledge graph.

### 3.6 Emerging Trend: Generative UI (2026)

The field is shifting toward AI agents dynamically generating interfaces. OpenAI's ChatKit, Anthropic's MCP Apps, and frameworks like Emergent allow LLMs to produce rich interactive UIs on the fly. This is a convergence of MDSE's "model → UI" pattern with LLM capabilities.

**Implication for SemPKM:** If DashboardSpecs are stored as structured data (RDF or JSON), an AI copilot could generate dashboard definitions from natural language: "Create a dashboard showing my untagged notes this week alongside my active projects."

### 3.7 Academic References

- **Dashboard metamodel pattern** (ACM 2024): Decomposes into user (role-based filtering), layout (pages > containers > rows/columns), and components (visualizations with marks, channels, scales). Maps well to our DashboardSpec.
- **OWL2UI** (2020): Generates web forms from OWL ontologies — validates our SHACL → form pipeline.
- **Sparnatural**: TypeScript component for visual SPARQL query building from SHACL specs. Demonstrates ontology-driven UI adaptation.

---

## 4. What SemPKM Already Has

### Existing Building Blocks

| Building Block | What It Does | Where |
|---|---|---|
| **ViewSpec** | Declarative view definitions (SPARQL + renderer type + columns) | `views/*.jsonld`, `views/service.py` |
| **Table/Card/Graph renderers** | 3 ways to render query results as htmx partials | `views/router.py`, templates |
| **SHACL-driven forms** | Auto-generated create/edit forms from SHACL shapes | `forms/`, `services/shapes.py` |
| **Spatial Canvas** | Prototype drag-drop spatial layout (pan/zoom/cards) | `canvas.js`, `canvas_page.html` |
| **Tab system (dockview)** | Multi-tab editor with panel management | `workspace-layout.js` |
| **Bottom panels** | Tabbed panel bar (event log, SPARQL, lint, AI) | `workspace.html` |
| **Command system** | Unified write path via POST /api/commands | `commands/dispatcher.py` |
| **Mental Models** | Pluggable domain schemas (ontology+shapes+views+rules) | `models/`, `services/models.py` |
| **Custom events** | `sempkm:tab-activated`, `sempkm:tabs-empty` | `workspace.js` |
| **Saved SPARQL queries** | User-defined queries stored in SQLite | `sparql/models.py` |
| **htmx fragment rendering** | Server renders partials, htmx swaps them in | All routes |

### The Gaps

1. **No composition layer** — can't arrange multiple views in a single screen
2. **No dashboard model** — no way to persist "this screen has a Notes table on the left and a Projects graph on the right"
3. **No cross-view state** — selecting a row in one view can't filter another view
4. **No workflow sequencing** — no concept of "step 1 → step 2 → step 3"
5. **No parameterized views** — ViewSpec SPARQL queries are static; can't inject `?selected_project` as a filter

---

## 5. Architecture Design

### 4.1 Core Concept: DashboardSpec

A **DashboardSpec** is a new model type (stored as RDF, like ViewSpec) that describes a composed screen:

```
sempkm:DashboardSpec
  rdfs:label          "Weekly Overview"
  sempkm:layout       "grid-2x2"          # layout template
  sempkm:blocks       [                    # ordered list of blocks
    {
      sempkm:blockType    "view-embed"
      sempkm:viewSpec     bpkm:view-note-table
      sempkm:gridPosition "row1-col1"
      sempkm:filter       "?created >= NOW() - P7D"
      sempkm:height       "400px"
    },
    {
      sempkm:blockType    "view-embed"
      sempkm:viewSpec     bpkm:view-project-card
      sempkm:gridPosition "row1-col2"
    },
    {
      sempkm:blockType    "object-embed"
      sempkm:objectIRI    <urn:sempkm:object:my-weekly-journal>
      sempkm:gridPosition "row2-col1-span2"
      sempkm:mode         "edit"
    },
    {
      sempkm:blockType    "create-form"
      sempkm:targetClass  bpkm:Note
      sempkm:gridPosition "row2-col2"
      sempkm:defaults     { "bpkm:noteType": "reflection" }
    },
    {
      sempkm:blockType    "markdown"
      sempkm:content      "## This Week's Focus\nReview and organize."
      sempkm:gridPosition "row1-header"
    }
  ]
```

### Block Types

| Block Type | Description | Data Source |
|---|---|---|
| `view-embed` | Renders an existing ViewSpec (table/card/graph) inline | ViewSpec IRI + optional filter |
| `object-embed` | Renders a single object (read or edit mode) | Object IRI |
| `create-form` | Inline creation form for a type | Target class IRI (SHACL drives fields) |
| `markdown` | Static rich text block | Inline markdown content |
| `sparql-result` | Raw SPARQL query result (for metrics/counts) | Inline SPARQL query |
| `divider` | Visual separator | None |

### Layout System

Rather than a full drag-and-drop builder (complex, fragile), use a **template-based grid** system:

- **Predefined layouts:** `single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom`, `dashboard-4`
- Each layout has named **slots** (e.g., `sidebar`, `main`, `top-left`, `top-right`)
- Blocks are assigned to slots
- CSS Grid handles the actual rendering
- Users pick a layout, then assign blocks to slots

This is simpler than freeform drag-and-drop but covers 90% of dashboard needs. The spatial canvas can evolve into the freeform option later.

### 4.2 Cross-View State & Data Binding

The key interaction pattern: **selecting something in one view filters another view.**

**Mechanism: Dashboard Context Variables**

```javascript
// Dashboard maintains a context object
dashboardContext = {
  selected_project: null,    // IRI of selected project
  selected_note: null,       // IRI of selected note
  date_range: "P7D",         // ISO 8601 duration
}

// When user clicks a row in the Projects table:
dashboardContext.selected_project = "urn:sempkm:object:abc123"
document.dispatchEvent(new CustomEvent('sempkm:dashboard-context-changed', {
  detail: { key: 'selected_project', value: 'urn:sempkm:object:abc123' }
}))

// Notes table block listens and re-fetches with filter:
// SPARQL injection: FILTER(?relatedProject = <${selected_project}>)
```

**How blocks consume context:**

In the DashboardSpec, blocks can declare **parameter bindings**:

```json
{
  "blockType": "view-embed",
  "viewSpec": "bpkm:view-note-table",
  "paramBindings": {
    "project_filter": { "source": "context", "key": "selected_project" }
  }
}
```

The ViewSpec's SPARQL query can include a `$project_filter` placeholder that gets injected at execution time.

**Implementation:** htmx makes this natural — when context changes, re-fetch the block's htmx endpoint with the new filter parameter. No client-side state framework needed.

### 4.3 WorkflowSpec (Guided Workflows)

A **WorkflowSpec** defines a multi-step guided experience:

```
sempkm:WorkflowSpec
  rdfs:label           "Weekly Reflection"
  sempkm:description   "Review, organize, and reflect on your week"
  sempkm:steps         [
    {
      sempkm:stepOrder     1
      sempkm:stepLabel     "Review Inbox"
      sempkm:stepType      "dashboard"
      sempkm:dashboard     sempkm:dash-inbox-review
      sempkm:outputs       ["selected_notes"]
    },
    {
      sempkm:stepOrder     2
      sempkm:stepLabel     "Categorize Notes"
      sempkm:stepType      "view"
      sempkm:viewSpec      bpkm:view-note-card
      sempkm:filter        "?s IN (${selected_notes})"
      sempkm:inputs        ["selected_notes"]
    },
    {
      sempkm:stepOrder     3
      sempkm:stepLabel     "Link to Projects"
      sempkm:stepType      "view"
      sempkm:viewSpec      bpkm:view-note-graph
    },
    {
      sempkm:stepOrder     4
      sempkm:stepLabel     "Write Summary"
      sempkm:stepType      "create-form"
      sempkm:targetClass   bpkm:Note
      sempkm:defaults      {
        "bpkm:noteType": "weekly-reflection",
        "dcterms:title": "Week of ${current_date}"
      }
    }
  ]
```

### Workflow UI

The workflow renders as:
1. A **step indicator** bar at the top (step 1 / 2 / 3 / 4) with labels
2. The **current step's content** in the main area (dashboard, view, or form)
3. **Previous / Next buttons** at the bottom
4. A **workflow context** sidebar showing accumulated state (selected items, created objects)

### Workflow State Machine

```
WORKFLOW_STATE = {
  workflow_iri: "...",
  current_step: 1,
  context: {
    selected_notes: ["urn:...", "urn:..."],
    created_objects: [],
  },
  completed_steps: [1],
}
```

State is client-side (sessionStorage or in-memory). Workflows are ephemeral sessions, not persisted — you run through a workflow, and the objects you create/modify persist in the knowledge graph, but the workflow progress itself doesn't need to be saved (though we could add that later for long-running workflows).

---

## 6. Implementation Plan

### Phase 1: Dashboard Foundation (Build)

**Goal:** Users can create and view dashboards composed of embedded views and static content.

#### 1a. DashboardSpec Schema & Storage

- Define `sempkm:DashboardSpec` vocabulary (RDF/JSON-LD)
- Add a `DashboardService` (parallel to `ViewSpecService`) that loads/saves dashboard specs
- Storage options:
  - **Option A:** Store in RDF like ViewSpecs (consistent with MDSE approach, queryable)
  - **Option B:** Store in SQLite JSON column (simpler, faster iteration)
  - **Recommendation:** Start with SQLite JSON (like saved SPARQL queries), migrate to RDF later

#### 1b. Dashboard Renderer

- New route: `GET /browser/dashboard/{dashboard_id}`
- Template: `dashboard_page.html` — CSS Grid container with named slot regions
- Each block rendered as an htmx-loaded partial in its slot
- Block types: `view-embed`, `markdown`, `divider` (start simple)

#### 1c. Dashboard Builder UI

- Route: `GET /browser/dashboard/{dashboard_id}/edit`
- Simple form-based builder (not drag-and-drop):
  - Pick a layout template
  - For each slot, pick a block type and configure it
  - Preview button to see the result
- Saves via POST /api/commands with new `dashboard.create` / `dashboard.patch` commands

#### 1d. Navigation Integration

- Add "Dashboards" section to the left sidebar explorer
- Add dashboards to the command palette
- Dashboards open as tabs in the workspace

**Estimated scope:** New service, 2-3 new routes, 3-4 new templates, new command handlers, CSS for grid layouts.

### Phase 2: Interactive Dashboards (Build)

**Goal:** Cross-view data binding and more block types.

#### 2a. Dashboard Context & Cross-View Filtering

- Implement dashboard context variables (JS)
- Add `sempkm:dashboard-context-changed` custom event
- ViewSpec blocks re-fetch via htmx when context changes
- Parameterized SPARQL: support `${variable}` placeholders in ViewSpec queries

#### 2b. Additional Block Types

- `object-embed` — render a specific object in read/edit mode within a dashboard slot
- `create-form` — inline object creation form (reuse existing SHACL form generation)
- `sparql-result` — single-value metric display (e.g., "12 untagged notes")

#### 2c. Block Interactivity

- Table row selection emits context variable
- Card click emits context variable
- Graph node selection emits context variable
- Form submission emits `object-created` event that refreshes relevant views

**Estimated scope:** Dashboard JS module (~500 LOC), modifications to existing view templates for embedded mode, parameterized SPARQL support in ViewSpecService.

### Phase 3: Guided Workflows (Build)

**Goal:** Users can define and run multi-step workflows.

#### 3a. WorkflowSpec Schema & Storage

- Define `sempkm:WorkflowSpec` vocabulary
- WorkflowService for CRUD
- Store in SQLite JSON (like dashboards)

#### 3b. Workflow Runner

- Route: `GET /browser/workflow/{workflow_id}/run`
- Template: `workflow_runner.html`
  - Step indicator bar (stepper component)
  - Step content area (loads dashboard/view/form via htmx)
  - Navigation buttons (prev/next/finish)
- Client-side workflow state machine in JS

#### 3c. Workflow Builder

- Form-based builder:
  - Add steps, reorder steps
  - For each step: pick type (view/dashboard/form), configure it
  - Define input/output variable mappings
- Saves as WorkflowSpec

#### 3d. Step Context Passing

- Step outputs flow into next step's inputs
- Example: selecting notes in step 1 → `selected_notes` array → step 2 filters by those IRIs
- Context displayed in a collapsible sidebar

#### 3e. Predefined Workflow Templates

- Ship with built-in workflow templates in Mental Models:
  - "Weekly Reflection" — review → categorize → link → summarize
  - "Research Capture" — create concept → link sources → write note
  - "Project Review" — view project → check tasks → update status

**Estimated scope:** New service, workflow JS module (~800 LOC), 3-4 new templates, stepper CSS component, workflow templates in mental models.

### Phase 4: Polish & Advanced Features (Later)

- **Dashboard templates** — pre-built dashboards in Mental Models
- **Freeform layout** — evolve spatial canvas into a dashboard layout option
- **Conditional workflow steps** — if/else based on context values
- **Workflow scheduling** — recurring workflows (e.g., "every Monday, prompt Weekly Reflection")
- **Collaborative dashboards** — shared dashboard definitions
- **Dashboard-as-homepage** — set a dashboard as the workspace landing page
- **Mobile-responsive layouts** — stack grid slots on small screens

---

## 7. Build vs. Integrate Decision Matrix

| Capability | Build | Integrate | Recommendation |
|---|---|---|---|
| Dashboard schema/storage | Build (fits our RDF/SPARQL model) | — | **Build** |
| Grid layout system | Build (CSS Grid + slot templates) | — | **Build** |
| Dashboard renderer | Build (htmx partial composition) | — | **Build** |
| Dashboard builder UI | Build (form-based, simple) | Integrate GrapesJS or similar | **Build** (simpler, consistent with htmx) |
| Cross-view data binding | Build (custom events + htmx re-fetch) | — | **Build** |
| Workflow runner | Build (stepper + htmx) | Integrate n8n/Temporal | **Build** (our workflows are UI-guided, not automation pipelines) |
| Parameterized SPARQL | Build (template substitution in ViewSpecService) | — | **Build** |
| Drag-and-drop layout | — | Integrate SortableJS or similar | **Integrate later** (Phase 4) |
| Charting/metrics blocks | — | Integrate Chart.js or Apache ECharts | **Integrate** (for sparql-result blocks) |

**Summary:** Almost everything should be built in-house because:
1. The htmx + server-rendered partial architecture means we can't easily drop in React-based dashboard builders
2. Our data layer (RDF/SPARQL) is unique — no off-the-shelf tool speaks it
3. The scope is deliberately constrained (template-based layouts, not freeform)
4. Mental Model integration requires tight coupling with our existing services

The only integration points are CSS/JS libraries for specific features (charting, drag-and-drop).

---

## 8. Open Questions

1. **Dashboard storage format:** SQLite JSON vs. RDF named graphs? JSON is faster to iterate on, RDF is more consistent with the architecture. Could start JSON, migrate later.

2. **SPARQL parameterization security:** Injecting user-selected IRIs into SPARQL queries has injection risk. Need a safe template system (bind variables, not string interpolation). RDF4J supports `VALUES` clause injection which is safe.

3. **Layout complexity ceiling:** How far do we go? Fixed templates (simple) vs. CSS Grid cell specification (medium) vs. freeform drag-and-drop (complex)? Recommend starting with fixed templates.

4. **Workflow state persistence:** Should in-progress workflows survive page refresh? If yes, need sessionStorage or server-side storage. If no, simpler but users lose progress.

5. **Mobile/responsive:** Do dashboards need to work on mobile? If yes, grid layouts need responsive breakpoints from day 1.

6. **Permissions:** Can all users create dashboards? Are some dashboards admin-defined and read-only for regular users?

---

## 9. Relation to MDSE Principles

The proposed architecture follows Model-Driven Software Engineering principles naturally:

```
Level 3 (Meta-metamodel):  RDF/OWL/SHACL standards
                                ↓
Level 2 (Metamodel):       SemPKM vocabulary (sempkm:ViewSpec, sempkm:DashboardSpec, sempkm:WorkflowSpec)
                                ↓
Level 1 (Model):           Mental Model instances (basic-pkm views, dashboards, workflows)
                                ↓
Level 0 (Data):            User's knowledge graph instances (notes, projects, people)
```

Each level defines the structure for the level below:
- OWL/SHACL defines what a ViewSpec/DashboardSpec/WorkflowSpec looks like
- Mental Models instantiate specific views/dashboards/workflows for a domain
- Users create data that flows through those views/dashboards/workflows

This is pure MDSE: **define once at the metamodel level, instantiate many times at the model level, render dynamically at runtime.** BESSER-PEARL does the same with B-UML → code generators. We do it with SHACL → form generators and ViewSpec → view renderers. DashboardSpec and WorkflowSpec are the natural next layer.

---

## 10. Summary

### What we're building

1. **DashboardSpec** — a new model type for composing views, objects, forms, and text into a single screen using template-based grid layouts, with cross-view data binding via context variables and htmx re-fetching.

2. **WorkflowSpec** — a new model type for defining multi-step guided experiences that sequence dashboards, views, and forms with state flowing between steps.

### Why build over integrate

SemPKM's unique combination of RDF data, SHACL-driven forms, SPARQL-backed views, and htmx-based rendering means off-the-shelf dashboard builders don't fit. The architecture already has 80% of the pieces — we're adding the composition and sequencing layers.

### Phasing

1. **Phase 1** — Static dashboards (view embeds + markdown in grid layouts)
2. **Phase 2** — Interactive dashboards (cross-view binding, forms, object embeds)
3. **Phase 3** — Guided workflows (stepper, context passing, templates)
4. **Phase 4** — Advanced features (freeform layout, scheduling, mobile)

---

## 11. Sources & References

- [BESSER GitHub](https://github.com/BESSER-PEARL/BESSER) — core platform
- [BESSER Documentation](https://besser.readthedocs.io/en/latest/) — B-UML sublanguages, generators
- [Building BESSER: An Open-Source Low-Code Platform (arXiv 2024)](https://arxiv.org/html/2405.13620v1)
- [BESSER GUI Model Docs](https://besser.readthedocs.io/en/latest/buml_language/model_types/gui.html)
- [BESSER State Machine Model Docs](https://besser.readthedocs.io/en/latest/buml_language/model_types/state_machine.html)
- [BESSER RDF Generator](https://besser.readthedocs.io/en/stable/generators/rdf.html)
- [BESSER Web Modeling Editor](https://github.com/BESSER-PEARL/BESSER-Web-Modeling-Editor)
- [BESSER Agentic BPMN](https://github.com/BESSER-PEARL/agentic-bpmn)
- [About Jordi Cabot](https://modeling-languages.com/about-jordi-cabot/)
- [Dashboard of Open Source Low-Code Tools](https://modeling-languages.com/dashboard-of-open-source-low-code-tools/)
- [Low-code and MDE: Two Sides of the Same Coin? (Springer)](https://link.springer.com/article/10.1007/s10270-021-00970-2)
- [LinkedDataHub by AtomGraph](https://github.com/AtomGraph/LinkedDataHub)
- [LinkedDataHub v5 Announcement](https://atomgraph.com/blog/linkeddatahub-5/)
- [Sparnatural Visual SPARQL Query Builder](https://sparnatural.eu/)
- [NocoBase](https://github.com/nocobase/nocobase)
- [Model-Driven Dashboard Generation (ACM 2024)](https://dl.acm.org/doi/pdf/10.1145/3643655.3643876)
- [n8n Workflow Automation](https://n8n.io/)
- [Directus Dashboards](https://directus.io/)
- [Grafana](https://grafana.com/)
