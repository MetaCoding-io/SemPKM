# Web Components for Mental Model System Integration

**Research Date:** 2026-03-03
**Author:** Claude (research task quick-18)
**Status:** Research complete -- architecture proposal with source links

---

## 1. Executive Summary

SemPKM's Mental Model system currently contributes backend-consumable artifacts: ontologies (JSON-LD), SHACL shapes (for form generation), view specifications (SPARQL-backed table/card/graph renderers), seed data, icons, and settings. The frontend consumes these through generic Jinja2 templates and htmx-driven partial updates. There is no mechanism for a model to contribute custom frontend UI code.

**The opportunity:** Allow Mental Model authors to ship specialized UI components alongside their data and schema artifacts. A "Kanban" model could contribute a `<sempkm-kanban-board>` element for project management views. A "Chemistry" model could contribute a `<sempkm-molecule-viewer>` for rendering molecular structures. A "Music" model could contribute a `<sempkm-chord-chart>` for displaying chord progressions. This would transform Mental Models from data-only packages into full-stack domain kits.

**Primary recommendation:** A phased approach starting with **Jinja2 macro bundles** (lowest risk, immediate value) progressing to **light DOM Custom Elements** (medium risk, high extensibility). Shadow DOM should be avoided for htmx compatibility. Full Web Component adoption (Phase 2+) should use a registration protocol where model-served JavaScript modules call `customElements.define()` with SemPKM-prefixed tag names, receiving RDF data via element attributes and properties. **Confidence level: MEDIUM-HIGH** for the phased approach; MEDIUM for Web Components specifically due to htmx interop friction points documented below.

**Key risks:** (1) htmx does not process `hx-*` attributes inside Shadow DOM without explicit configuration, making Shadow DOM Custom Elements incompatible with SemPKM's htmx-first architecture; (2) model-contributed JavaScript introduces a new attack surface requiring a trust model; (3) component registration lifecycle must integrate with the existing model install/uninstall flow without breaking hot-reload development patterns.

---

## 2. Current State

### 2.1 How Mental Models contribute artifacts today

A Mental Model is a directory containing a `manifest.yaml` and four artifact types stored in named graphs upon installation:

| Artifact | Named Graph | Format | Purpose |
|----------|-------------|--------|---------|
| Ontology | `urn:sempkm:model:{id}:ontology` | JSON-LD | RDF classes, properties, constraints |
| Shapes | `urn:sempkm:model:{id}:shapes` | JSON-LD | SHACL shapes for form generation |
| Views | `urn:sempkm:model:{id}:views` | JSON-LD | ViewSpec instances (SPARQL + renderer type) |
| Seed | `urn:sempkm:model:{id}:seed` | JSON-LD | Example instances loaded into `urn:sempkm:current` |

The `manifest.yaml` schema (`backend/app/models/manifest.py` -- `ManifestSchema`) validates `modelId`, `version`, `name`, `description`, `namespace`, `prefixes`, `entrypoints`, `settings`, and `icons`. There is no entrypoint for frontend code (JavaScript, CSS, or HTML templates).

### 2.2 How the frontend consumes model data

The rendering pipeline flows through:

1. **ViewSpecService** (`backend/app/views/service.py`) loads `ViewSpec` instances from model views graphs via SPARQL
2. **Renderer Registry** (`backend/app/views/registry.py`) maps renderer types (`table`, `card`, `graph`) to Jinja2 template paths
3. **Jinja2 templates** render HTML server-side; htmx swaps fragments into the DOM
4. **Frontend JS** (`frontend/static/js/`) provides interactivity (graph.js for Cytoscape, editor.js for forms, workspace.js for layout)

The `register_renderer()` function in `registry.py` already supports model-contributed renderer types, but these must map to Jinja2 templates that exist on the server filesystem. A model cannot currently contribute its own templates or JavaScript.

### 2.3 The gap

There is no mechanism for a model to:
- Contribute JavaScript that runs in the browser
- Register Custom Elements or Web Components
- Provide CSS specific to its custom UI
- Serve static assets from its model directory
- Declare frontend dependencies (CDN libraries, etc.)

---

## 3. Web Components + htmx Analysis

### 3.1 How Custom Elements behave during htmx DOM swaps

htmx operates by swapping HTML fragments into the DOM. When htmx performs an `innerHTML` swap (the default), the browser's HTML parser processes the new content, which includes upgrading any Custom Elements that have been registered via `customElements.define()`.

**Key finding:** Custom Elements work naturally with htmx's swap mechanism *if they are already registered* before the swap occurs. The browser automatically calls the element's `constructor()` and `connectedCallback()` when the element is inserted into the DOM, whether by initial page load or by htmx swap.

Source: [htmx documentation on 3rd party JS](https://htmx.org/docs/#3rd-party) describes that htmx fires `htmx:afterSwap` and `htmx:load` events after content insertion, which can be used to initialize components that need post-insertion setup.

Source: [MDN Web Components lifecycle callbacks](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements#custom_element_lifecycle_callbacks) documents that `connectedCallback` fires whenever an element is moved into the document, which is exactly what htmx swap does.

**Caveat:** The `htmx:afterSettle` event (fires after htmx has processed new content) is the correct hook for components that need to interact with htmx-processed siblings, not `connectedCallback` alone.

### 3.2 Shadow DOM implications for htmx attribute processing

**Critical finding: Shadow DOM is incompatible with htmx's default behavior.**

htmx processes attributes (`hx-get`, `hx-post`, `hx-swap`, `hx-trigger`, etc.) by scanning the DOM tree after each swap. It does **not** pierce Shadow DOM boundaries. This means:

- `hx-*` attributes inside a Shadow DOM are invisible to htmx
- htmx event bubbling (`htmx:beforeRequest`, etc.) does not cross shadow boundaries by default
- `hx-target` selectors cannot reach elements inside Shadow DOM from outside, or outside from inside

Source: [htmx GitHub issue #1022](https://github.com/bigskysoftware/htmx/issues/1022) discusses Shadow DOM incompatibility. The htmx team's position is that Shadow DOM support is not a priority because htmx is designed for server-rendered HTML, which inherently uses the light DOM.

Source: [htmx documentation](https://htmx.org/docs/) does not mention Shadow DOM at all, confirming it is not a supported use case.

### 3.3 Recommended pattern: Light DOM Custom Elements

The recommended approach for SemPKM is **light DOM Custom Elements** -- Custom Elements that render directly into the document DOM without using `this.attachShadow()`. This pattern:

1. Allows htmx to process `hx-*` attributes inside the component
2. Allows SemPKM's existing CSS to style component internals
3. Allows event bubbling to work naturally
4. Retains the benefit of Custom Element lifecycle callbacks (`connectedCallback`, `disconnectedCallback`, `attributeChangedCallback`)
5. Enables model-specific initialization logic

**Code example -- a model-contributed kanban board element:**

```javascript
// models/kanban-model/components/kanban-board.js
class SempkmKanbanBoard extends HTMLElement {
  static get observedAttributes() {
    return ['data-type-iri', 'data-view-spec'];
  }

  connectedCallback() {
    // Fetch board data from SemPKM API
    const typeIri = this.getAttribute('data-type-iri');
    const viewSpec = this.getAttribute('data-view-spec');

    // Render directly into light DOM (no Shadow DOM)
    this.innerHTML = `
      <div class="kanban-container"
           hx-get="/api/views/${encodeURIComponent(viewSpec)}/cards?group_by=status"
           hx-trigger="load"
           hx-target="this">
        <div class="kanban-loading">Loading board...</div>
      </div>
    `;
  }

  disconnectedCallback() {
    // Cleanup event listeners, observers, etc.
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== null && oldValue !== newValue) {
      // Re-render on attribute change
      this.connectedCallback();
    }
  }
}

// Register with SemPKM prefix
customElements.define('sempkm-kanban-board', SempkmKanbanBoard);
```

**Server-side usage (Jinja2 template):**

```html
<!-- The model contributes this template for its custom renderer -->
<sempkm-kanban-board
  data-type-iri="{{ target_class }}"
  data-view-spec="{{ spec_iri }}">
</sempkm-kanban-board>
```

Source: [Google Web Fundamentals - Custom Elements best practices](https://web.dev/articles/custom-elements-best-practices) recommends light DOM for components that need to participate in document-level CSS and event systems.

Source: [Lit documentation on light DOM](https://lit.dev/docs/components/shadow-dom/#implementing-createrenderroot) describes the `createRenderRoot() { return this; }` pattern for light DOM rendering in the Lit framework, confirming this is a well-understood pattern.

### 3.4 htmx extension point: `htmx:load` event

When htmx swaps new content into the DOM, it fires `htmx:load` on each new element. This is the ideal hook for Custom Elements that need post-swap initialization. SemPKM already uses this pattern implicitly (Lucide icon re-initialization after swap).

```javascript
// Global listener that model components can rely on
document.addEventListener('htmx:load', function(evt) {
  // evt.detail.elt is the newly loaded element
  // Custom Elements' connectedCallback will have already fired
  // This event is for any additional initialization
});
```

Source: [htmx events reference](https://htmx.org/events/#htmx:load) documents the `htmx:load` event lifecycle.

---

## 4. Security Model

### 4.1 Trust levels

Model-contributed JavaScript introduces executable code into the browser, requiring a trust model:

| Trust Level | Source | Examples | JavaScript Allowed? |
|-------------|--------|----------|---------------------|
| **Core** | SemPKM codebase | Built-in renderers, workspace.js, editor.js | Yes (trusted by definition) |
| **Trusted** | Published/curated models | `basic-pkm`, community-reviewed models | Yes (with CSP restrictions) |
| **Untrusted** | User-created models | Custom models without review | No (Jinja2 macros only) |

### 4.2 Sandboxing options analysis

| Approach | Security | htmx Compat | Performance | Complexity | Verdict |
|----------|----------|-------------|-------------|------------|---------|
| **No sandbox** | None | Full | Best | Lowest | Trusted models only |
| **CSP restrictions** | Medium | Full | Good | Low | Recommended for trusted |
| **iframe sandbox** | High | None | Poor | High | Too isolated |
| **ShadowRealm** | High | Unknown | Good | Medium | Not yet standardized |
| **Module scope** | Low-Medium | Full | Good | Low | Recommended baseline |

**CSP restrictions** (Content Security Policy): The server can set CSP headers that restrict what model JavaScript can do:
- `script-src 'self'` -- only scripts served from the same origin
- `connect-src 'self'` -- only fetch/XHR to the same origin (prevents data exfiltration)
- No `eval()`, no inline scripts, no `data:` URIs for scripts
- Model JS modules loaded via `<script type="module" src="/models/{id}/components/...">` are allowed by `'self'`

Source: [MDN Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) provides comprehensive CSP documentation.

Source: [W3C CSP Level 3 specification](https://www.w3.org/TR/CSP3/) defines the full policy model.

**iframe sandbox**: The `<iframe sandbox="allow-scripts" srcdoc="...">` approach provides strong isolation but completely breaks htmx integration. Components inside iframes cannot participate in htmx request/response cycles, cannot access parent DOM, and require `postMessage` for all communication. This approach is viable only for fully self-contained widgets (e.g., a molecule viewer that doesn't need htmx).

Source: [MDN iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox) documents sandbox restrictions.

**ShadowRealm proposal**: TC39 Stage 2 proposal (as of early 2026) for JavaScript realm isolation. Would allow executing model JavaScript in an isolated global scope. Not yet available in any browser. Not recommended for near-term adoption.

Source: [TC39 ShadowRealm proposal](https://github.com/nicolo-ribaudo/tc39-proposal-shadowrealm) tracks the current proposal status.

### 4.3 Recommended approach per trust level

| Trust Level | Approach | Rationale |
|-------------|----------|-----------|
| **Core** | No restrictions | Part of the application codebase |
| **Trusted** | CSP + module scope | Prevents exfiltration, allows DOM access for htmx compat |
| **Untrusted** | Jinja2 macros only (no JS) | Server-side rendering eliminates client-side risk |

### 4.4 What model authors CAN and CANNOT do

**CAN:**
- Define Custom Elements with `sempkm-` prefixed tag names
- Render HTML into light DOM (no Shadow DOM)
- Use `hx-*` attributes in rendered HTML
- Listen to `htmx:load`, `sempkm:tab-activated`, and other SemPKM events
- Fetch data from SemPKM API endpoints (`/api/views/`, `/api/commands`, etc.)
- Import other model-provided ES modules
- Use CSS custom properties defined by SemPKM's theme system

**CANNOT:**
- Execute `eval()` or create inline scripts (CSP blocks this)
- Make network requests to external origins (CSP `connect-src 'self'`)
- Access `document.cookie` (httpOnly flag on `sempkm_session`)
- Modify core SemPKM DOM elements outside their component boundary (convention, not enforced)
- Override `customElements.define()` for non-`sempkm-` prefixed tags (enforced by registration API)
- Load external scripts or stylesheets (CSP `script-src 'self'`, `style-src 'self' 'unsafe-inline'`)

---

## 5. Manifest Extension Design

### 5.1 Proposed additions to manifest.yaml schema

```yaml
# Proposed new fields for ManifestSchema
components:
  # JavaScript modules to load (ES modules)
  modules:
    - path: "components/kanban-board.js"
      elements:
        - tag: "sempkm-kanban-board"
          description: "Kanban board view for projects"
    - path: "components/timeline.js"
      elements:
        - tag: "sempkm-timeline-view"
          description: "Timeline visualization"

  # CSS files to include
  styles:
    - "components/kanban.css"
    - "components/timeline.css"

  # Custom renderer registrations (extends existing registry.py)
  renderers:
    - type: "kanban"
      template: "components/kanban-renderer.html"  # Jinja2 template (Phase 1)
      element: "sempkm-kanban-board"               # Custom Element (Phase 2)

  # Template macros (Phase 1 - Jinja2 only)
  templates:
    - path: "templates/kanban-renderer.html"
      type: "renderer"
```

### 5.2 File structure within model bundle

```
models/kanban-model/
  manifest.yaml
  ontology/kanban-model.jsonld
  shapes/kanban-model.jsonld
  views/kanban-model.jsonld
  seed/kanban-model.jsonld
  components/                      # NEW: frontend components
    kanban-board.js                 # ES module defining Custom Element
    kanban.css                      # Component-specific styles
    timeline.js                     # Another component
    timeline.css
  templates/                       # NEW: Jinja2 templates (Phase 1)
    kanban-renderer.html            # Server-side renderer template
```

### 5.3 Registration lifecycle

```
Model Install                      Browser Load
    |                                   |
    v                                   v
1. parse manifest.yaml             5. Page loads, <head> includes
2. validate component entries         model CSS links
3. register renderers              6. <script type="module"> tags
   in RENDERER_REGISTRY               load model JS
4. serve static files via          7. customElements.define()
   nginx /models/{id}/static/         called per component
                                   8. htmx swaps content with
                                      <sempkm-*> elements
                                   9. connectedCallback() fires
                                      for each element instance
```

**Install time (server):**
1. `ModelService.install_model()` parses `manifest.yaml` including new `components` section
2. Validates component entries: tag names must start with `sempkm-`, JS files must exist, no `eval()` in source
3. Registers custom renderers in `RENDERER_REGISTRY` (template path or element tag)
4. Model static files are already volume-mounted; nginx needs a route to serve them

**Runtime (browser):**
5. Base template includes `<link>` tags for model CSS and `<script type="module">` tags for model JS
6. JavaScript modules execute, calling `customElements.define()` to register elements
7. When htmx swaps HTML containing `<sempkm-*>` tags, browser auto-upgrades them
8. `connectedCallback()` runs, component renders its light DOM content

### 5.4 Example manifest.yaml with component declarations

```yaml
modelId: kanban-model
version: "1.0.0"
name: "Kanban Board"
description: "Adds kanban board visualization for project management"
namespace: "urn:sempkm:model:kanban-model:"
prefixes:
  kbn: "urn:sempkm:model:kanban-model:"
entrypoints:
  ontology: "ontology/kanban-model.jsonld"
  shapes: "shapes/kanban-model.jsonld"
  views: "views/kanban-model.jsonld"
  seed: null
icons:
  - type: "kbn:Board"
    icon: "kanban"
    color: "#4e79a7"
settings:
  - key: "defaultColumns"
    label: "Default Kanban Columns"
    description: "Comma-separated list of default column names"
    input_type: "text"
    default: "Backlog,In Progress,Done"
components:
  modules:
    - path: "components/kanban-board.js"
      elements:
        - tag: "sempkm-kanban-board"
          description: "Kanban board with drag-and-drop columns"
  styles:
    - "components/kanban.css"
  renderers:
    - type: "kanban"
      element: "sempkm-kanban-board"
```

---

## 6. Integration Architecture

### 6.1 Serving model JavaScript modules

**Option A: nginx static path (RECOMMENDED)**

Add an nginx location block to serve model static files:

```nginx
# frontend/nginx.conf addition
location /models/ {
    alias /app/models/;
    # Only serve JS and CSS files from components/ directories
    location ~ ^/models/([a-z][a-z0-9-]*)/components/ {
        alias /app/models/$1/components/;
        add_header X-Content-Type-Options nosniff;
        add_header Cache-Control "public, max-age=3600";
    }
    # Block all other model files (ontology, shapes, etc.)
    return 403;
}
```

This leverages the existing Docker volume mount (`models/` directory is already accessible). No new API endpoint needed. Files are served with proper MIME types and caching headers.

**Option B: API endpoint**

A FastAPI endpoint like `GET /api/models/{model_id}/components/{filename}` could serve component files. This adds Python overhead for static file serving but enables access control and audit logging.

**Option C: Inline in template**

Model JavaScript could be inlined into Jinja2 templates via `<script>` tags. This avoids serving separate files but prevents browser caching and makes CSP harder (requires `'unsafe-inline'` or nonces).

**Recommendation:** Option A (nginx) for production, with Option B as fallback for deployments without nginx.

### 6.2 Component discovery

The frontend needs to know which components are available from installed models. Two approaches:

**Server-side discovery (recommended):**

The base template (`base.html`) already receives context data. Add a `model_components` context variable:

```python
# In the base template context
model_components = await model_service.get_installed_components()
# Returns: [{"model_id": "kanban-model", "modules": ["components/kanban-board.js"], "styles": ["components/kanban.css"]}]
```

```html
<!-- base.html head section -->
{% for comp in model_components %}
  {% for style in comp.styles %}
    <link rel="stylesheet" href="/models/{{ comp.model_id }}/components/{{ style }}">
  {% endfor %}
  {% for module in comp.modules %}
    <script type="module" src="/models/{{ comp.model_id }}/components/{{ module }}"></script>
  {% endfor %}
{% endfor %}
```

**Client-side discovery:**

An API endpoint returns component metadata, and a bootstrap script loads them dynamically:

```javascript
// frontend/static/js/model-components.js
async function loadModelComponents() {
  const response = await fetch('/api/models/components');
  const components = await response.json();
  for (const comp of components) {
    for (const module of comp.modules) {
      await import(`/models/${comp.model_id}/components/${module}`);
    }
  }
}
```

**Recommendation:** Server-side discovery for initial load (no JS needed, works with `<noscript>`), with lazy loading via dynamic `import()` for components only needed on specific views.

### 6.3 Data binding: how components receive RDF data

Custom Elements receive data through three channels:

**1. HTML attributes (simple values):**

```html
<sempkm-kanban-board
  data-type-iri="urn:sempkm:model:basic-pkm:Project"
  data-view-spec="urn:sempkm:model:kanban-model:kanban-projects">
</sempkm-kanban-board>
```

**2. htmx server-rendered content (HTML fragments):**

The component uses `hx-get` to fetch server-rendered HTML, which htmx swaps into the component's light DOM. This is the most htmx-native approach and keeps rendering on the server.

**3. JavaScript API calls (JSON data):**

For components that need raw data (e.g., graph visualizations), they can call SemPKM API endpoints:

```javascript
connectedCallback() {
  const specIri = this.getAttribute('data-view-spec');
  fetch(`/api/views/${encodeURIComponent(specIri)}/execute?format=json`)
    .then(r => r.json())
    .then(data => this.render(data));
}
```

**Recommendation:** Prefer approach #2 (htmx server-rendered) for most components. Use approach #3 only for components that genuinely need client-side rendering (interactive visualizations, drag-and-drop).

### 6.4 htmx integration: components in the request/response cycle

Light DOM Custom Elements participate in htmx naturally:

```html
<!-- Server returns this HTML fragment -->
<sempkm-kanban-board data-type-iri="...">
  <div class="kanban-columns" hx-get="/api/views/.../cards" hx-trigger="load">
    <!-- htmx will swap card data here -->
  </div>
</sempkm-kanban-board>
```

Components can also trigger htmx requests programmatically:

```javascript
// Inside a Custom Element method
this.querySelector('.kanban-card').dispatchEvent(
  new CustomEvent('moveCard', { bubbles: true })
);
// Or use htmx's JS API
htmx.ajax('POST', '/api/commands', {
  values: { command: 'object.patch', params: { iri: cardIri, ... } },
  target: this
});
```

Source: [htmx JavaScript API](https://htmx.org/api/#ajax) documents the `htmx.ajax()` function for programmatic requests.

---

## 7. Alternatives Comparison Table

| Criterion | Web Components (Light DOM) | Jinja2 Macro Bundles | iframe Sandbox | Server-Side Plugins (Python) | Declarative JSON Config |
|-----------|---------------------------|---------------------|----------------|-----------------------------|-----------------------|
| **Security** | Medium (CSP-restricted) | High (no client JS) | Highest (full isolation) | High (server-side only) | High (no code execution) |
| **DX for model authors** | Good (standard web APIs) | Good (familiar templating) | Poor (postMessage complexity) | Good (Python ecosystem) | Limited (constrained to schema) |
| **htmx compatibility** | Excellent (light DOM) | Excellent (native Jinja2) | None (cross-frame barrier) | Excellent (server-rendered) | Good (server-rendered JSON-to-HTML) |
| **Performance** | Good (browser-native) | Best (no JS overhead) | Poor (iframe overhead) | Good (server-rendered) | Good (server-rendered) |
| **Complexity to implement** | Medium (new serving/registration) | Low (extend existing template system) | High (message passing, sizing) | Medium (new plugin API) | Medium (schema design, validation) |
| **Interactivity** | Full (drag-and-drop, animations, canvas) | Limited (htmx-level only) | Full (within iframe) | Limited (htmx-level only) | None (static rendering) |
| **Offline/PWA support** | Good (cached modules) | None (requires server) | Poor (complex caching) | None (requires server) | None (requires server) |
| **Community ecosystem** | Large (standard Web APIs) | Small (SemPKM-specific) | Moderate (micro-frontends) | Moderate (Python plugins) | Moderate (JSON Schema tools) |

### Detailed comparison notes

**Jinja2 Macro Bundles** are the lowest-risk approach. Models contribute `.html` template files containing Jinja2 macros. The renderer registry already supports custom templates. The only gap is serving model templates -- currently, Jinja2 templates must be on the server filesystem at a known path. Extending the Jinja2 loader to include model directories (`models/{id}/templates/`) would close this gap with minimal code changes.

**Server-Side Plugins (Python)** would allow models to contribute Python code that generates HTML. This is powerful but introduces server-side code execution from model packages, which is a larger security concern than client-side JavaScript (server has access to the database, triplestore, filesystem). Python sandboxing is significantly harder than browser sandboxing.

**Declarative JSON Config** (similar to JSON Forms / RJSF) would define UI structure as JSON, which a generic renderer converts to HTML. This is safe and structured but severely limits what model authors can express. Complex visualizations (graphs, charts, kanban boards) cannot be described declaratively.

Source: [JSON Forms](https://jsonforms.io/) is a framework for rendering forms from JSON Schema.
Source: [React JSON Schema Form (RJSF)](https://rjsf-team.github.io/react-jsonschema-form/) is a popular JSON-to-form renderer.

---

## 8. Phased Adoption Roadmap

### Phase 1: Custom Renderer Templates (Jinja2 macros from models)

**Risk:** Low
**Effort:** Small (1-2 plans)
**Value:** Immediate -- models can contribute custom table layouts, card designs, and list formats

**What changes:**
1. Extend Jinja2 template loader to include `models/{id}/templates/` directories
2. Model `manifest.yaml` gets a `templates` section listing contributed template files
3. `register_renderer()` in `registry.py` maps renderer types to model template paths
4. Model templates use existing Jinja2 macros and SemPKM template context

**What model authors can do:**
- Custom table column layouts
- Custom card face designs
- Custom list/detail renderers
- All rendering is server-side; no JavaScript involved
- Full access to htmx attributes in templates

**Example manifest addition:**
```yaml
components:
  templates:
    - path: "templates/timeline-renderer.html"
      type: "renderer"
      renderer_type: "timeline"
```

**Example model template:**
```html
{# models/timeline-model/templates/timeline-renderer.html #}
{% macro render_timeline(rows, columns) %}
<div class="timeline-container">
  {% for row in rows %}
  <div class="timeline-entry"
       hx-get="/browser/object/{{ row.s | urlencode }}"
       hx-target="#editor-area-group-1"
       hx-push-url="false">
    <span class="timeline-date">{{ row.date }}</span>
    <span class="timeline-title">{{ row.title }}</span>
  </div>
  {% endfor %}
</div>
{% endmacro %}
```

### Phase 2: Light DOM Web Components (model-contributed Custom Elements)

**Risk:** Medium
**Effort:** Medium (2-3 plans)
**Value:** High -- enables interactive, client-rendered UI components

**What changes:**
1. `manifest.yaml` schema extended with `components.modules` and `components.styles`
2. nginx configured to serve `models/{id}/components/` static files
3. Base template includes model component `<script>` and `<link>` tags
4. `ManifestSchema` (`backend/app/models/manifest.py`) gains `ManifestComponentDef` model
5. `ModelService.install_model()` validates component entries (tag name prefix, file existence)
6. Tag name enforcement: all Custom Elements must use `sempkm-{modelId}-` prefix
7. CSP headers updated to allow model scripts from `/models/` path

**What model authors can do:**
- Full Custom Element API (lifecycle callbacks, observed attributes)
- Light DOM rendering with htmx integration
- Client-side interactivity (drag-and-drop, animations, canvas/SVG)
- Fetch data from SemPKM API endpoints
- Listen to SemPKM custom events (`sempkm:tab-activated`, etc.)
- Use SemPKM CSS custom properties for theming

**Tag naming convention:**
```
sempkm-{modelId}-{component-name}

Examples:
- sempkm-kanban-model-board
- sempkm-chemistry-molecule-viewer
- sempkm-music-chord-chart
```

### Phase 3: Full Component SDK (model author toolkit)

**Risk:** High
**Effort:** Large (4-6 plans)
**Value:** Very high -- professional model development experience

**What changes:**
1. `@sempkm/model-sdk` npm package with TypeScript types, base classes, test utilities
2. CLI tool for model scaffolding: `sempkm model create kanban-model`
3. Dev server with hot-reload for component development
4. Type-safe RDF data binding (TypeScript interfaces generated from SHACL shapes)
5. Component testing framework (renders Custom Elements with mock SemPKM API)
6. Model marketplace / registry for publishing and discovering models

**SDK base class example:**
```typescript
// @sempkm/model-sdk
export abstract class SempkmComponent extends HTMLElement {
  // Typed RDF data access
  protected get typeIri(): string { ... }
  protected get viewSpec(): ViewSpec { ... }

  // htmx integration helpers
  protected htmxGet(url: string, target?: HTMLElement): void { ... }
  protected htmxPost(command: string, params: object): void { ... }

  // Theme access
  protected getThemeVar(name: string): string { ... }

  // Lifecycle (override these)
  abstract render(): void;
  onDataChange?(data: RdfData): void;
  onThemeChange?(): void;
}
```

**This phase is aspirational and should only be undertaken after Phase 1 and Phase 2 are validated in production with real model authors.**

---

## 9. Source Links

### Web Components + htmx

- [htmx documentation - 3rd party JS integration](https://htmx.org/docs/#3rd-party) -- how htmx interacts with external JavaScript
- [htmx events reference](https://htmx.org/events/) -- `htmx:load`, `htmx:afterSwap`, `htmx:afterSettle` event documentation
- [htmx JavaScript API](https://htmx.org/api/) -- `htmx.ajax()`, `htmx.process()` for programmatic use
- [htmx GitHub issue #1022 - Shadow DOM](https://github.com/bigskysoftware/htmx/issues/1022) -- Shadow DOM incompatibility discussion
- [MDN Custom Elements](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements) -- lifecycle callbacks, registration, best practices
- [MDN Shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM) -- encapsulation model and limitations
- [Google Web Fundamentals - Custom Elements best practices](https://web.dev/articles/custom-elements-best-practices) -- light DOM vs Shadow DOM patterns

### Plugin/Extension Systems Using Web Components

- [Home Assistant Custom Cards](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/) -- model for community-contributed UI cards using Custom Elements with lifecycle hooks and typed data binding
- [Grafana Panel Plugins](https://grafana.com/developers/plugin-tools/) -- panel SDK with React/preact components, build system, and marketplace; security via iframe sandboxing for untrusted plugins
- [Backstage Plugin System](https://backstage.io/docs/plugins/) -- Spotify's developer portal uses React components as plugins; each plugin is an npm package with a well-defined API surface
- [Obsidian Plugin API](https://docs.obsidian.md/Plugins/) -- desktop app plugin system; plugins have full DOM access but run in a sandboxed Electron webview
- [Shoelace Web Components](https://shoelace.style/) -- production Web Component library demonstrating light DOM patterns and framework-agnostic design
- [Lit Framework](https://lit.dev/) -- Google's Web Component framework; documents light DOM rendering via `createRenderRoot()` override

### Security and Sandboxing

- [MDN Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) -- comprehensive CSP documentation
- [W3C CSP Level 3 Specification](https://www.w3.org/TR/CSP3/) -- formal specification
- [MDN iframe sandbox attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox) -- sandbox restrictions and permissions
- [TC39 ShadowRealm proposal](https://github.com/nicolo-ribaudo/tc39-proposal-shadowrealm) -- Stage 2 JavaScript realm isolation proposal
- [OWASP Third-Party JavaScript Management](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html) -- security checklist for loading external JavaScript

### RDF/Linked Data + Web Components

- [Solid Project](https://solidproject.org/) -- Tim Berners-Lee's decentralized web platform; bridges RDF (Linked Data) with web applications; Solid apps consume RDF via authenticated HTTP
- [LDflex](https://github.com/LDflex/LDflex) -- JavaScript library for querying Linked Data; could power data binding in model components
- [rdflib.js](https://github.com/linkeddata/rdflib.js) -- RDF library for JavaScript; used in Solid ecosystem for client-side RDF manipulation
- [Comunica](https://comunica.dev/) -- modular SPARQL query engine for JavaScript; could enable client-side SPARQL queries from model components
- [Schema.org WebApplication type](https://schema.org/WebApplication) -- semantic description of web applications, not directly for components but shows the gap in standardized component discovery

### Alternative Approaches

- [JSON Forms](https://jsonforms.io/) -- declarative JSON Schema to UI rendering framework
- [React JSON Schema Form (RJSF)](https://rjsf-team.github.io/react-jsonschema-form/) -- JSON Schema-driven form rendering
- [Micro Frontends](https://micro-frontends.org/) -- architectural pattern for composing frontend applications; iframe-based isolation approach
- [Module Federation (Webpack 5)](https://webpack.js.org/concepts/module-federation/) -- runtime module sharing between independently deployed applications
- [single-spa](https://single-spa.js.org/) -- micro-frontend framework; orchestrates multiple frameworks in a single page

### Registration and Lifecycle

- [MDN customElements.define()](https://developer.mozilla.org/en-US/docs/Web/API/CustomElementRegistry/define) -- registration API
- [MDN Dynamic import()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/import) -- lazy loading ES modules
- [Web Components lazy loading patterns](https://web.dev/articles/custom-elements-best-practices#lazy-loading) -- deferred registration for performance
- [import maps specification](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script/type/importmap) -- browser-native module resolution mapping; could map `@sempkm/sdk` to a served URL

---

*Research completed 2026-03-03. This document provides architecture analysis for future implementation planning. No code changes required.*
