# Phase 4: Admin Shell and Object Creation - Research

**Researched:** 2026-02-22
**Domain:** htmx dashboard shell, SHACL-driven form generation, IDE-style workspace layout, command palette, Markdown editing, webhook configuration, validation lint panel
**Confidence:** HIGH

## Summary

Phase 4 transforms SemPKM from a backend-only API into a fully interactive application. It introduces three major frontend surface areas: (1) an htmx-based admin portal for model management and webhook configuration, (2) an IDE-style object browser workspace with resizable panes, tabs, navigation tree, and command palette, and (3) SHACL-driven form generation that translates shape metadata (sh:property, sh:group, sh:order, sh:datatype, sh:class, sh:in, sh:defaultValue) into editable HTML forms with inline validation feedback.

The existing codebase already has the backend infrastructure needed: ModelService with install/remove/list APIs, EventStore with command dispatch (object.create, object.patch, body.set), ValidationService with pyshacl, LabelService, and PrefixRegistry. The frontend is currently a vanilla htmx + JS dev console (health, SPARQL, commands pages) served via nginx. Jinja2 and jinja2-fragments are already in pyproject.toml dependencies, and the Jinja2Blocks integration enables partial template rendering for htmx -- the key building block for server-rendered fragment architecture.

The primary technical challenge is server-side SHACL shape traversal: querying shape graphs from the triplestore via SPARQL CONSTRUCT, parsing the rdflib Graph to extract sh:PropertyShape metadata (path, datatype, group, order, constraints), and rendering Jinja2 templates that produce the correct form widgets. This is a Python-side concern -- no client-side SHACL parsing needed. For the IDE workspace layout, Split.js (2KB, zero deps) handles resizable panes, and ninja-keys (web component) provides the command palette. CodeMirror 6 serves as the Markdown editor but requires a build step or CDN bundling since it ships as ESM modules.

**Primary recommendation:** Server-side SHACL shape traversal with rdflib producing Jinja2-rendered form HTML fragments. htmx handles all dynamic UI interactions (partial swaps, lazy loading, form submission). Split.js for resizable panes, ninja-keys for command palette, CodeMirror 6 (via ESM CDN) for Markdown editing. No React -- the entire phase uses htmx + vanilla JS.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Dashboard Architecture**: Root `/` is an htmx dashboard with a two-column layout: left sidebar with app links, right area shows the selected app. Apps hosted by the dashboard: Admin (`/admin/`), Object Browser (IDE workspace), Health Check (existing). Left sidebar uses simple icon + label links -- no badges or status indicators.
- **Workspace Layout**: Three-column layout: navigation tree (left) + editor/form (center) + properties/details (right) -- like VS Code or JetBrains. Left navigation tree organizes objects by type -- top-level nodes are object types (Person, Note, Project...), objects nested under their type. Persistent tabs -- each opened object gets its own tab, stays open until explicitly closed. Command palette supports full workspace control: object actions + toggle panels, switch views, run validation, manage models -- everything reachable from keyboard.
- **SHACL Form Generation**: Type selection: both a type picker dialog (browse-and-choose) and command palette ("New Object" inline) for keyboard-first users. Property groups (sh:group) render as collapsible sections -- all expanded by default, user can collapse to focus. Required fields shown first; optional fields collapsed in an "Advanced" section. sh:in constraints use dropdown select (standard dropdown for single values, multi-select for lists). sh:class references use search-as-you-type dropdown with "Create new..." option that opens a nested form for the target type. sh:defaultValue pre-filled in form fields, visually distinguishable (e.g., lighter text) until user modifies. Multi-valued properties use add/remove button pattern -- each value has a remove button, "+" button below to add another. sh:order defines default field order, but users can drag to reorder (preference saved per user). Date/time properties (xsd:date, xsd:dateTime) get calendar picker widgets. Human-readable labels (sh:name, rdfs:label) shown everywhere; hovering reveals the full URI/prefixed name as a tooltip.
- **Object Editing & View**: Objects open in always-editable mode -- no separate view/edit toggle. Center pane uses split view: properties form on top, Markdown body editor below -- both visible at once. Markdown body uses a rich editor (CodeMirror or similar) with syntax highlighting, toolbar, and live preview side-by-side. Explicit save (Ctrl+S or Save button) -- unsaved changes indicated by a dot on the tab. Object detail page shows properties + body + related objects (inbound + outbound edges). Related objects listed in the right pane -- always visible alongside the object.
- **Admin Portal**: Model management: table listing installed models with Install, Remove, and View Details actions per row. Webhook configuration: target URL + event selection (object.changed, edge.changed, validation.completed) + optional filters (e.g., only fire for specific object types or namespaces).
- **Validation & Lint Panel**: SHACL validation runs live as the user types, with debounce -- instant feedback. Lint panel lives as a tab in the right pane alongside properties/relations. Violations and warnings distinguished by color-coded icons: red circle for violations, yellow triangle for warnings. Clicking an issue jumps to and highlights the offending field, plus shows the validation message inline below the field. Violations block conformance-required operations (export); warnings never block.

### Claude's Discretion
- Exact resizing behavior for panes (min widths, drag handles, etc.)
- Loading states and skeleton designs
- Error handling patterns (network errors, save failures)
- Exact CodeMirror configuration and toolbar buttons
- Command palette search/fuzzy-matching implementation
- Dashboard visual styling and spacing

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMN-02 | User can manage Mental Models (install/remove/list) through an htmx-based admin portal | Jinja2Blocks partial rendering + htmx hx-get/hx-delete for CRUD operations against existing `/api/models` endpoints. Server-rendered model table with inline actions. |
| ADMN-03 | User can configure simple outbound webhooks that fire on events (object.changed, edge.changed, validation.completed) | New WebhookService storing webhook configs as RDF triples in a dedicated named graph. httpx.AsyncClient for async POST delivery. CRUD admin UI via htmx forms. |
| SHCL-02 | User can see validation results in a lint panel showing violations and warnings per object | Extend existing ValidationService to return per-object grouped results. Render lint panel as htmx fragment in right pane tab. Color-coded severity icons. |
| SHCL-03 | User can create objects via forms auto-generated from SHACL shapes | New ShapesService extracts sh:PropertyShape metadata from shapes graph via SPARQL. Jinja2 macros render form fields by datatype. htmx form POST to `/api/commands`. |
| SHCL-04 | User can edit existing objects via SHACL-driven forms | Same form generation as SHCL-03, pre-populated with current values from SPARQL query on urn:sempkm:current graph. Submits object.patch commands. |
| SHCL-06 | Violations block conformance-required operations (export); warnings never block | Check validation conforms status before export. UI disables/grays export button when violations exist. Warning count shown but non-blocking. |
| OBJ-01 | User can create new objects by selecting a type and filling out a SHACL-driven form | Type picker dialog listing sh:NodeShape targetClasses. Command palette "New Object" action. Form rendered from shape metadata. |
| OBJ-02 | User can edit an object's properties through its SHACL-driven form | Object opens in center pane tab. Properties form rendered from shape + current data. Saves via object.patch command. |
| OBJ-03 | User can write and edit an object's Markdown body via an embedded editor | CodeMirror 6 editor with markdown language support. Saves via body.set command. Live preview panel optional (Claude's discretion). |
| VIEW-04 | User can view a single object's details (properties, body, related objects) | Object page renders in center pane. Properties form on top, Markdown body below. Related objects in right pane via SPARQL query for inbound/outbound edges. |
| VIEW-05 | User can work in an IDE-style workspace with resizable panes and tabs | Split.js for three-column resizable layout. Tab bar with open/close/dirty indicators. State managed via htmx + sessionStorage. |
| VIEW-06 | User can navigate and execute commands via a command palette and keyboard shortcuts | ninja-keys web component. Registered actions: new object, open object, toggle panels, run validation, switch views, manage models. Ctrl+K/Cmd+K to open. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| htmx | 2.0.4 | Hypermedia-driven UI interactions | Already in project (index.html loads from unpkg CDN). Handles partial swaps, lazy loading, form submission. |
| Jinja2 | (bundled with FastAPI) | Server-side HTML template rendering | Already in pyproject.toml. Powers template composition and block rendering. |
| jinja2-fragments | 1.11+ | Partial block rendering for htmx | Already in pyproject.toml. Jinja2Blocks enables returning individual template blocks as htmx responses. |
| Split.js | 1.6.5 | Resizable pane layout | ~2KB gzipped, zero dependencies, CSS-based resizing, supports flex layout. Used by JSFiddle, Babylon.js. CDN: unpkg.com/split.js |
| ninja-keys | latest | Command palette web component | Lit-based web component, works with vanilla JS, Ctrl+K/Cmd+K default hotkey. CDN: unpkg.com/ninja-keys |
| CodeMirror 6 | 6.65+ | Markdown editor with syntax highlighting | Industry standard code editor. Requires ESM bundling -- use esm.sh CDN with pinned versions or a pre-built bundle. |
| rdflib | 7.5.0+ | SHACL shape graph traversal (server-side) | Already in project. Used to parse shapes graphs and extract sh:PropertyShape metadata for form generation. |
| httpx | 0.28+ | Outbound webhook HTTP delivery | Already in project. AsyncClient for non-blocking webhook POST requests. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hyperscript | 0.9.12 | Declarative client-side interactions | For small UI behaviors (toggling classes, animations) that don't warrant vanilla JS. Optional -- htmx attributes + minimal JS may suffice. |
| Sortable.js | latest | Drag-to-reorder for field order preferences | Only if implementing the user-reorderable fields feature (sh:order override). CDN available. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Split.js | CSS resize property | CSS resize is limited to single elements, no collaborative resizing of adjacent panes, no min/max constraints |
| ninja-keys | Custom command palette | ninja-keys is 5KB, battle-tested web component with fuzzy search. Building custom adds complexity for no gain. |
| CodeMirror 6 | textarea + markdown-it | Loses syntax highlighting, toolbar, and live preview. CodeMirror is the standard for web editors. |
| Server-side form generation | Client-side SHACL form (ULB-Darmstadt shacl-form) | Client-side SHACL parsing adds JS bundle weight and requires shipping shape graphs to browser. Server-side keeps shapes on backend, renders HTML fragments, consistent with htmx architecture. |

**Installation:**
CDN links in HTML templates (no npm/build step required for the htmx frontend):
```html
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://unpkg.com/split.js@1.6.5/dist/split.min.js"></script>
<script type="module" src="https://unpkg.com/ninja-keys?module"></script>
```

For CodeMirror 6, use a pre-bundled ESM module via esm.sh or a local Rollup build:
```html
<script type="module">
  import {EditorView, basicSetup} from "https://esm.sh/codemirror@6.65.7"
  import {markdown} from "https://esm.sh/@codemirror/lang-markdown@6"
  // Initialize editor...
</script>
```

Backend dependency already satisfied -- jinja2, jinja2-fragments, rdflib, httpx all in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── static/
│   ├── index.html          # Dashboard shell (existing, to be restructured)
│   ├── css/
│   │   ├── style.css       # Global styles (existing)
│   │   ├── workspace.css   # IDE workspace layout styles
│   │   └── forms.css       # SHACL form styles
│   └── js/
│       ├── app.js          # Existing JS utilities
│       ├── workspace.js    # Pane resizing, tab management, keyboard shortcuts
│       └── editor.js       # CodeMirror initialization and save handling
backend/
├── app/
│   ├── admin/              # NEW: Admin portal routes
│   │   └── router.py       # htmx-rendered admin pages (models, webhooks)
│   ├── browser/            # NEW: Object browser routes
│   │   └── router.py       # htmx-rendered workspace, object pages, forms
│   ├── services/
│   │   ├── shapes.py       # NEW: SHACL shape extraction service
│   │   └── webhooks.py     # NEW: Webhook configuration and dispatch
│   ├── templates/          # NEW: Jinja2 templates directory
│   │   ├── base.html       # Dashboard shell layout
│   │   ├── admin/
│   │   │   ├── models.html # Model management page
│   │   │   └── webhooks.html # Webhook configuration page
│   │   ├── browser/
│   │   │   ├── workspace.html # IDE workspace shell
│   │   │   ├── nav_tree.html  # Navigation tree (htmx partial)
│   │   │   ├── object_tab.html # Object editor tab (htmx partial)
│   │   │   ├── properties.html # Right pane properties (htmx partial)
│   │   │   └── lint_panel.html # Validation results (htmx partial)
│   │   ├── forms/
│   │   │   ├── _field.html    # Form field macro (dispatches by datatype)
│   │   │   ├── _group.html    # Collapsible property group
│   │   │   └── object_form.html # Complete SHACL-driven form
│   │   └── components/
│   │       ├── _tabs.html     # Tab bar component
│   │       └── _command_palette.html # ninja-keys setup
│   └── ...existing modules...
```

### Pattern 1: Server-Side SHACL Shape Extraction
**What:** A ShapesService that queries the shapes graph from the triplestore, parses it with rdflib, and returns structured Python dataclasses representing form metadata.
**When to use:** Every time a form needs to be rendered (create or edit object).
**Example:**
```python
# Source: Custom pattern combining rdflib graph traversal with SHACL vocabulary
from dataclasses import dataclass, field
from rdflib import Graph, URIRef
from rdflib.namespace import SH, RDF, RDFS, XSD

@dataclass
class PropertyShape:
    path: str           # IRI of the property
    name: str           # sh:name human-readable label
    datatype: str | None  # sh:datatype IRI (xsd:string, xsd:date, etc.)
    target_class: str | None  # sh:class IRI for object references
    order: float        # sh:order for sorting
    group: str | None   # sh:group IRI
    min_count: int      # sh:minCount (0 = optional)
    max_count: int | None  # sh:maxCount (None = unlimited)
    in_values: list[str]  # sh:in enumerated options
    default_value: str | None  # sh:defaultValue
    description: str | None  # sh:description

@dataclass
class PropertyGroup:
    iri: str
    label: str
    order: float

@dataclass
class NodeShapeForm:
    shape_iri: str
    target_class: str
    label: str
    groups: list[PropertyGroup]
    properties: list[PropertyShape]

class ShapesService:
    """Extract SHACL shape metadata for form generation."""

    SHAPES_QUERY = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?shape ?targetClass ?shapeLabel
    WHERE {
      ?shape a sh:NodeShape ;
             sh:targetClass ?targetClass .
      OPTIONAL { ?shape rdfs:label ?shapeLabel }
    }
    """

    PROPERTIES_QUERY = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?prop ?path ?name ?datatype ?class ?order ?group
           ?minCount ?maxCount ?defaultValue ?description
    WHERE {
      <%s> sh:property ?prop .
      ?prop sh:path ?path .
      OPTIONAL { ?prop sh:name ?name }
      OPTIONAL { ?prop sh:datatype ?datatype }
      OPTIONAL { ?prop sh:class ?class }
      OPTIONAL { ?prop sh:order ?order }
      OPTIONAL { ?prop sh:group ?group }
      OPTIONAL { ?prop sh:minCount ?minCount }
      OPTIONAL { ?prop sh:maxCount ?maxCount }
      OPTIONAL { ?prop sh:defaultValue ?defaultValue }
      OPTIONAL { ?prop sh:description ?description }
    }
    ORDER BY ?order
    """

    async def get_node_shapes(self) -> list[NodeShapeForm]:
        """Query all NodeShapes from installed model shapes graphs."""
        ...

    async def get_form_for_type(self, type_iri: str) -> NodeShapeForm:
        """Get form metadata for a specific target class."""
        ...
```

### Pattern 2: Jinja2Blocks Partial Rendering for htmx
**What:** Use jinja2-fragments' Jinja2Blocks to render individual template blocks as htmx fragment responses. Full page loads render the entire template; htmx requests render only the targeted block.
**When to use:** Every htmx endpoint that updates part of the page.
**Example:**
```python
# Source: jinja2-fragments FastAPI integration
from jinja2_fragments.fastapi import Jinja2Blocks

templates = Jinja2Blocks(directory="app/templates")

@router.get("/admin/models")
async def admin_models(
    request: Request,
    model_service: ModelService = Depends(get_model_service),
):
    models = await model_service.list_models()
    context = {"request": request, "models": models}
    # htmx requests get just the content block; full page loads get everything
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "admin/models.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "admin/models.html", context)
```

### Pattern 3: htmx Navigation Tree with Lazy Loading
**What:** Navigation tree with type nodes that expand on click to load objects via htmx GET. Objects are loaded lazily per-type.
**When to use:** Left pane of the workspace.
**Example:**
```html
<!-- Type node: click to expand and load objects -->
<div class="tree-node" hx-get="/browser/tree/Person"
     hx-trigger="click" hx-target="#children-Person"
     hx-swap="innerHTML">
  <span class="tree-icon">&#9656;</span>
  <span>Person</span>
</div>
<div id="children-Person"></div>

<!-- Server returns list of objects as tree children -->
<!-- Each child links to open the object in a tab -->
<div class="tree-leaf"
     hx-get="/browser/object/https%3A%2F%2Fexample.org%2Fdata%2FPerson%2Falice"
     hx-target="#editor-area"
     hx-swap="innerHTML"
     hx-push-url="false">
  <span>Alice Smith</span>
</div>
```

### Pattern 4: Tab Management with htmx + Vanilla JS
**What:** Client-side tab state managed in JS (sessionStorage for persistence), with htmx loading tab content from the server.
**When to use:** Center pane tab bar for open objects.
**Example:**
```javascript
// Tab state in sessionStorage
const TAB_KEY = "sempkm_open_tabs";

function openTab(objectIri, label) {
  const tabs = JSON.parse(sessionStorage.getItem(TAB_KEY) || "[]");
  if (!tabs.find(t => t.iri === objectIri)) {
    tabs.push({ iri: objectIri, label: label, dirty: false });
    sessionStorage.setItem(TAB_KEY, JSON.stringify(tabs));
  }
  renderTabBar();
  // htmx loads the object content into the editor area
  htmx.ajax('GET', `/browser/object/${encodeURIComponent(objectIri)}`,
            { target: '#editor-area', swap: 'innerHTML' });
}
```

### Pattern 5: Webhook Service with Background Dispatch
**What:** Simple webhook config stored as RDF triples, dispatch via httpx fire-and-forget.
**When to use:** After EventStore.commit() for subscribed events.
**Example:**
```python
# Webhook dispatch after command execution
async def dispatch_webhooks(event_type: str, payload: dict):
    """Fire outbound webhooks for matching event subscriptions."""
    configs = await webhook_service.get_configs_for_event(event_type)
    async with httpx.AsyncClient(timeout=5.0) as client:
        for config in configs:
            try:
                await client.post(config.target_url, json=payload)
            except Exception:
                logger.warning("Webhook delivery failed: %s", config.target_url)
```

### Anti-Patterns to Avoid
- **Client-side SHACL parsing:** Don't ship shape graphs to the browser for client-side form generation. Server-side rendering with Jinja2 is simpler, faster, and consistent with the htmx architecture.
- **Storing tab/pane state in the backend:** Tab state and pane sizes are ephemeral UI concerns. Use sessionStorage/localStorage, not server sessions or database storage.
- **Blocking webhook delivery:** Never wait for webhook delivery before responding to the user. Fire-and-forget with logging. Advanced delivery guarantees are explicitly out of scope (v3).
- **Full page reloads for admin actions:** Use htmx hx-swap for model install/remove/list operations. The model table should update in-place without full page reload.
- **Building a custom command palette:** ninja-keys is a mature, accessible web component. Building custom adds accessibility issues and weeks of work for no benefit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resizable panes | Custom mousedown/mousemove handlers | Split.js | Edge cases: min widths, touch support, nested splits, gutter styling. 2KB solves it. |
| Command palette | Custom dialog + fuzzy search + keyboard nav | ninja-keys web component | Accessibility (ARIA, focus management), fuzzy matching, keyboard navigation, nested groups. |
| Markdown editor | textarea with preview | CodeMirror 6 | Syntax highlighting, undo/redo, keybindings, scrollbar sync, mobile support, extensibility. |
| Partial template rendering | Custom response splitting | jinja2-fragments Jinja2Blocks | Correct handling of template inheritance, block nesting, multiple block rendering for OOB swaps. |
| SHACL widget mapping | Custom if/else chain | Datatype-to-widget mapping table | The DASH specification defines a scoring system (datashapes.org). Use a simple dict mapping datatype IRIs to input types and Jinja2 macro names. |

**Key insight:** Phase 4 is a UI-intensive phase where the temptation to hand-roll is highest. Every UI component (panes, command palette, editor, form fields) has edge cases that take 10x the estimated time. Use established libraries and focus implementation effort on the SHACL-to-form mapping logic, which is the unique value of this project.

## Common Pitfalls

### Pitfall 1: CodeMirror 6 ESM Import Hell
**What goes wrong:** CodeMirror 6 ships as a set of ESM packages under the @codemirror scope. Each depends on @codemirror/state, and CDN auto-bundlers (esm.run, skypack) can load duplicate versions of shared dependencies, causing instanceof checks to fail at runtime.
**Why it happens:** CodeMirror 6 is designed for npm bundlers (Rollup, webpack), not CDN script tags. The ESM module graph has shared singletons that break when loaded from different URLs.
**How to avoid:** Either (a) use esm.sh with explicit pinned versions and `?external=@codemirror/state` to force deduplication, (b) create a local Rollup bundle of the needed CM6 packages and serve the single file, or (c) use a pre-bundled wrapper like ink-mde which ships as a single file.
**Warning signs:** "Invalid state" errors, extensions not applying, editor appearing blank.

### Pitfall 2: SHACL sh:in List Traversal in SPARQL
**What goes wrong:** sh:in uses an RDF list (rdf:first/rdf:rest chain). Extracting list items via SPARQL requires either property paths or recursive queries. A naive `?prop sh:in ?list` only gives the list head node.
**Why it happens:** JSON-LD's `@list` serializes to RDF list structures. The triplestore stores them as linked blank nodes.
**How to avoid:** Use rdflib's `Collection` class to traverse the list after CONSTRUCT, or use a SPARQL property path pattern: `?prop sh:in/rdf:rest*/rdf:first ?value`. The rdflib approach (fetching the shapes graph via CONSTRUCT and traversing in Python) is more reliable than complex SPARQL patterns.
**Warning signs:** sh:in dropdown showing blank or only one item.

### Pitfall 3: htmx Swap Targets with Dynamic Content
**What goes wrong:** When htmx swaps content into a container, any htmx attributes in the new content need the htmx library to process them. If content is swapped into a part of the DOM that htmx hasn't initialized, attributes like hx-get won't work.
**Why it happens:** htmx processes the document on DOMContentLoaded. New content added via innerHTML needs htmx to re-scan it. htmx does this automatically for its own swaps but not for content inserted by other JS.
**How to avoid:** Always use htmx's own swap mechanisms (hx-swap, hx-target). If inserting content via vanilla JS, call `htmx.process(element)` on the new content. Use `htmx:afterSwap` event for post-swap initialization (e.g., CodeMirror editors, Split.js).
**Warning signs:** Buttons and links in swapped content not working, htmx attributes being ignored.

### Pitfall 4: Race Conditions in Live Validation
**What goes wrong:** Debounced validation on keystroke fires while the previous validation is still running. Multiple concurrent validation requests can return out of order, showing stale results.
**Why it happens:** The user decision says "SHACL validation runs live as the user types, with debounce." But the backend ValidationService validates the entire current graph, not just the form being edited. Re-validation after every keystroke (even debounced) could be expensive.
**How to avoid:** Two-tier validation: (1) Client-side lightweight validation (required fields, datatype format) runs instantly with JS. (2) Server-side SHACL validation triggers on save (or on a longer debounce, e.g., 2-3 seconds after last keystroke). The lint panel shows the latest completed server validation. A "validating..." spinner indicates when server validation is pending.
**Warning signs:** Lint panel flickering, outdated results showing after edits, high CPU from constant re-validation.

### Pitfall 5: Nginx Routing for Template-Served Pages
**What goes wrong:** The current nginx.conf only serves static files from `/usr/share/nginx/html` and proxies `/api/` to the backend. Template-rendered pages need to be served by FastAPI, not nginx.
**Why it happens:** Phase 4 introduces Jinja2-rendered pages alongside the existing static HTML. Both need to coexist.
**How to avoid:** Update nginx.conf to proxy all non-static, non-API routes to FastAPI. Keep `/css/`, `/js/`, and specific static files served by nginx for performance. Route `/admin/`, `/browser/`, and the root `/` through FastAPI for template rendering.
**Warning signs:** 404 errors when navigating to /admin/ or /browser/, templates returning raw text instead of HTML.

### Pitfall 6: Object Reference Search (sh:class) Requires Async SPARQL
**What goes wrong:** sh:class properties need a "search-as-you-type" dropdown showing instances of the target class. This requires SPARQL queries as the user types, which must be debounced and performant.
**Why it happens:** The user decision requires a search dropdown with a "Create new..." option for sh:class references. This is fundamentally async and needs both a backend search endpoint and frontend debounced input handling.
**How to avoid:** Create a dedicated `/api/search/instances?type=X&q=text` endpoint that queries the current graph with a FILTER regex on labels. Use htmx hx-trigger="input changed delay:300ms" on the search input to debounce. Return results as HTML option elements for the dropdown.
**Warning signs:** Dropdown not populating, excessive API calls on every keystroke, slow search for large datasets.

## Code Examples

### SHACL Datatype to HTML Input Type Mapping
```python
# Source: DASH datashapes.org specification mapping + project-specific additions
DATATYPE_WIDGET_MAP: dict[str, dict] = {
    "http://www.w3.org/2001/XMLSchema#string": {
        "input_type": "text",
        "template": "forms/_text_field.html",
    },
    "http://www.w3.org/2001/XMLSchema#integer": {
        "input_type": "number",
        "template": "forms/_number_field.html",
        "attrs": {"step": "1"},
    },
    "http://www.w3.org/2001/XMLSchema#decimal": {
        "input_type": "number",
        "template": "forms/_number_field.html",
        "attrs": {"step": "0.01"},
    },
    "http://www.w3.org/2001/XMLSchema#boolean": {
        "input_type": "select",
        "template": "forms/_boolean_field.html",
    },
    "http://www.w3.org/2001/XMLSchema#date": {
        "input_type": "date",
        "template": "forms/_date_field.html",
    },
    "http://www.w3.org/2001/XMLSchema#dateTime": {
        "input_type": "datetime-local",
        "template": "forms/_datetime_field.html",
    },
    "http://www.w3.org/2001/XMLSchema#anyURI": {
        "input_type": "url",
        "template": "forms/_url_field.html",
    },
}
```

### Extracting sh:in Values with rdflib Collection
```python
# Source: rdflib documentation for RDF list traversal
from rdflib import Graph, Collection
from rdflib.namespace import SH

def extract_in_values(shapes_graph: Graph, prop_node) -> list[str]:
    """Extract sh:in list values from a property shape node."""
    in_list_heads = list(shapes_graph.objects(prop_node, SH['in']))
    if not in_list_heads:
        return []
    # rdflib Collection traverses rdf:first/rdf:rest chains
    collection = Collection(shapes_graph, in_list_heads[0])
    return [str(item) for item in collection]
```

### Jinja2 Form Field Macro
```html
{# Source: Custom pattern for SHACL-driven form rendering #}
{% macro render_field(prop, value=None) %}
<div class="form-field{% if prop.min_count > 0 %} required{% endif %}"
     id="field-{{ prop.path | urlencode }}">
  <label title="{{ prop.path }}">
    {{ prop.name }}
    {% if prop.min_count > 0 %}<span class="required-marker">*</span>{% endif %}
  </label>

  {% if prop.in_values %}
    {# sh:in -> dropdown select #}
    <select name="{{ prop.path }}">
      <option value="">-- Select --</option>
      {% for opt in prop.in_values %}
        <option value="{{ opt }}" {% if opt == value %}selected{% endif %}
                {% if opt == prop.default_value and not value %}selected{% endif %}>
          {{ opt }}
        </option>
      {% endfor %}
    </select>

  {% elif prop.target_class %}
    {# sh:class -> search-as-you-type reference dropdown #}
    <input type="text" name="{{ prop.path }}"
           value="{{ value or '' }}"
           hx-get="/api/search/instances?type={{ prop.target_class | urlencode }}"
           hx-trigger="input changed delay:300ms"
           hx-target="#suggestions-{{ prop.path | urlencode }}"
           placeholder="Search {{ prop.name }}...">
    <div id="suggestions-{{ prop.path | urlencode }}" class="suggestions-dropdown"></div>

  {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#date' %}
    <input type="date" name="{{ prop.path }}" value="{{ value or '' }}">

  {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#dateTime' %}
    <input type="datetime-local" name="{{ prop.path }}" value="{{ value or '' }}">

  {% elif prop.datatype == 'http://www.w3.org/2001/XMLSchema#boolean' %}
    <select name="{{ prop.path }}">
      <option value="true" {% if value == 'true' %}selected{% endif %}>Yes</option>
      <option value="false" {% if value == 'false' %}selected{% endif %}>No</option>
    </select>

  {% else %}
    {# Default: text input #}
    <input type="text" name="{{ prop.path }}"
           value="{{ value or prop.default_value or '' }}"
           {% if prop.default_value and not value %}class="default-value"{% endif %}
           placeholder="{{ prop.description or '' }}">
  {% endif %}

  <div class="field-validation" id="validation-{{ prop.path | urlencode }}"></div>
</div>
{% endmacro %}
```

### Split.js IDE Layout Initialization
```javascript
// Source: Split.js documentation
// Three-column workspace: nav tree | editor | properties
const splitInstance = Split(['#nav-tree', '#editor-area', '#right-pane'], {
  sizes: [20, 50, 30],        // Initial percentage sizes
  minSize: [180, 300, 200],    // Minimum pixel widths
  gutterSize: 6,               // Drag handle width
  cursor: 'col-resize',
  onDragEnd: function(sizes) {
    // Persist sizes to localStorage for session persistence
    localStorage.setItem('sempkm_pane_sizes', JSON.stringify(sizes));
  }
});

// Restore saved sizes on load
const saved = localStorage.getItem('sempkm_pane_sizes');
if (saved) {
  splitInstance.setSizes(JSON.parse(saved));
}
```

### ninja-keys Command Palette Registration
```javascript
// Source: ninja-keys documentation
const ninja = document.querySelector('ninja-keys');
ninja.data = [
  {
    id: 'new-object',
    title: 'New Object',
    icon: 'add_circle',
    section: 'Objects',
    handler: () => showTypePicker()
  },
  {
    id: 'run-validation',
    title: 'Run Validation',
    icon: 'check_circle',
    section: 'Tools',
    hotkey: 'ctrl+shift+v',
    handler: () => triggerValidation()
  },
  {
    id: 'toggle-nav',
    title: 'Toggle Navigation Panel',
    icon: 'view_sidebar',
    section: 'View',
    hotkey: 'ctrl+b',
    handler: () => togglePane('nav-tree')
  },
  // Dynamic entries added when objects are loaded
];
```

### Webhook Configuration Storage (RDF)
```python
# Source: Custom pattern for webhook config as RDF triples
WEBHOOKS_GRAPH = "urn:sempkm:webhooks"

# Webhook config triple pattern:
# <urn:sempkm:webhook:{uuid}> a sempkm:Webhook ;
#     sempkm:targetUrl "https://example.com/hook" ;
#     sempkm:event "object.changed" ;
#     sempkm:event "edge.changed" ;
#     sempkm:filter "bpkm:Person" ;  # optional type filter
#     sempkm:enabled "true"^^xsd:boolean .
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React SPA for all UI | htmx + server-rendered for admin; React reserved for complex interactive views | 2023-2025 | Massive simplification for CRUD-heavy admin UIs. SemPKM admin + forms are ideal htmx candidates. |
| Client-side SHACL form libs | Server-side shape extraction + template rendering | Ongoing | Client-side libs (shacl-form) parse Turtle in the browser. Server-side keeps complexity on the backend where rdflib excels. |
| CodeMirror 5 | CodeMirror 6 | 2023+ | CM6 is modular, tree-sitter based, better performance. But ESM-only distribution makes CDN usage harder. |
| Custom keyboard shortcuts | Web component command palettes (ninja-keys, cmdk) | 2022+ | Standardized UX pattern. Users expect Ctrl+K. |
| CSS Grid manual resizing | Split.js / dedicated split libraries | 2014+ | CSS Grid + resize handles is possible but lacks collaborative resizing, min/max constraints, and gutter UX. |

**Deprecated/outdated:**
- CodeMirror 5: Still on cdnjs but no longer actively developed. Use CM6.
- jQuery UI Resizable: jQuery dependency is unnecessary. Split.js is lighter and framework-free.
- Bootstrap tabs: Overweight for htmx architecture. Use htmx HATEOAS tabs pattern.

## Open Questions

1. **CodeMirror 6 CDN Strategy**
   - What we know: CM6 requires ESM modules. esm.sh works but has version deduplication issues.
   - What's unclear: Whether esm.sh will reliably resolve all CM6 dependencies without conflicts in production.
   - Recommendation: Start with esm.sh and pinned versions. If issues arise, create a local Rollup bundle (add a build step just for the CM6 bundle, keeping the rest build-free). Alternatively, evaluate ink-mde (pre-bundled CM6 wrapper).

2. **Live Validation Scope**
   - What we know: User wants "SHACL validation runs live as the user types." Backend validates the entire current graph via pyshacl.
   - What's unclear: Whether re-validating the entire graph on debounced keystrokes is performant enough for real-time feedback.
   - Recommendation: Implement two-tier: instant client-side validation for required fields and datatype constraints, plus server-side SHACL validation on save (or longer debounce). Show server validation results in the lint panel after each save. This matches the existing AsyncValidationQueue pattern.

3. **htmx vs React for Object Browser**
   - What we know: PROJECT.md says "htmx shell + React IDE (iframe)" but Phase 4 CONTEXT.md decisions describe the workspace entirely without mentioning React. The existing frontend is pure htmx + vanilla JS.
   - What's unclear: Whether the user intends to use React for the IDE workspace or stay with htmx throughout Phase 4.
   - Recommendation: Implement Phase 4 entirely with htmx + vanilla JS. The workspace (resizable panes, tabs, forms, Markdown editor) is achievable with htmx + Split.js + ninja-keys + CodeMirror. If Phase 5's graph visualization or complex interaction patterns require React, it can be introduced then. This avoids premature architectural complexity.

4. **Drag-to-Reorder Field Preferences**
   - What we know: User decision says "sh:order defines default field order, but users can drag to reorder (preference saved per user)."
   - What's unclear: Where to persist per-user field order preferences in a single-user v1 system.
   - Recommendation: Use localStorage for field order preferences. This is sufficient for single-user v1. The draggable reorder feature itself can use Sortable.js if needed, but consider deferring drag-reorder to focus on the core form generation first.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `/home/james/Code/SemPKM/backend/app/` -- full review of services, models, commands, validation, triplestore client
- Existing SHACL shapes: `/home/james/Code/SemPKM/models/basic-pkm/shapes/basic-pkm.jsonld` -- verified sh:property, sh:group, sh:order, sh:in, sh:class, sh:defaultValue, sh:datatype usage
- jinja2-fragments documentation: https://jinja2-fragments.readthedocs.io/ -- Jinja2Blocks API for FastAPI partial rendering
- DASH Form Generation spec: https://datashapes.org/forms.html -- SHACL-to-widget mapping reference
- htmx documentation: https://htmx.org/ -- hx-swap, hx-trigger, lazy loading, HATEOAS tabs patterns
- Split.js: https://split.js.org/ -- resizable pane library API
- ninja-keys: https://github.com/ssleptsov/ninja-keys -- command palette web component
- CodeMirror 6 lang-markdown: https://github.com/codemirror/lang-markdown -- Markdown language support

### Secondary (MEDIUM confidence)
- FastAPI + htmx + Jinja2 patterns: https://testdriven.io/blog/fastapi-htmx/ -- verified with official FastAPI templates docs
- ULB-Darmstadt shacl-form: https://github.com/ULB-Darmstadt/shacl-form -- client-side SHACL form generation reference (used for constraint mapping research, not for direct use)
- CodeMirror 6 ESM CDN discussion: https://discuss.codemirror.net/t/esm-compatible-codemirror-build-directly-importable-in-browser/5933 -- ESM import challenges and workarounds

### Tertiary (LOW confidence)
- esm.sh reliability for CM6: Needs runtime validation -- known issues with version deduplication

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via official docs, most already in project
- Architecture: HIGH -- htmx + Jinja2 + server-side rendering is well-documented pattern, consistent with existing codebase
- SHACL form generation: HIGH -- DASH spec provides authoritative mapping, existing shapes use all required properties
- IDE workspace layout: MEDIUM-HIGH -- Split.js and ninja-keys are proven, but the specific combination with htmx needs implementation validation
- CodeMirror 6 CDN: MEDIUM -- ESM import strategy needs runtime testing
- Webhook system: HIGH -- simple httpx POST pattern, no complex delivery guarantees needed

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days -- stable ecosystem, no fast-moving dependencies)
