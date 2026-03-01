## Decision

Embed `@zazuko/yasgui` v4.5.0 via CDN directly into a new SPARQL Console template, wired to the existing `/api/sparql` endpoint, with a custom YASR table cell renderer that transforms SemPKM data IRIs into object browser links, and localStorage persistence for query tabs and history (key: `sempkm-sparql`).

**Rationale:**
- Yasgui is the de facto standard SPARQL query UI (used by Apache Jena Fuseki, GraphDB, and dozens of triplestore products); integrating it gives a production-grade editor with syntax highlighting, autocomplete, result visualization, tabs, and persistence at zero backend development cost
- The Zazuko fork (`@zazuko/yasgui`) is fully MIT-licensed, actively maintained (v4.5.0, mid-2025), and CDN-loadable via unpkg — consistent with how SemPKM already loads htmx, Cytoscape, Split.js, Lucide, and marked
- The existing `/api/sparql` endpoint already speaks the SPARQL Protocol (POST + `application/x-www-form-urlencoded`); Yasgui requires zero backend changes
- Cookie-based auth (`sempkm_session`) is automatically included by the browser for same-origin requests — no special auth configuration needed
- Custom YASR table cell rendering allows SemPKM data IRIs to open in the object browser rather than navigating to raw URIs, providing a first-class integrated experience

**Alternatives ruled out:**
- **`@sib-swiss/sparql-editor` web component** — wraps Yasgui but adds VoID metadata as a prerequisite (SemPKM does not generate VoID); adds complexity for marginal autocomplete improvement; evaluate for a future enhancement phase
- **Comunica Web Client** — federated query engine designed for querying the open web, not a single endpoint; heavy bundle, no editor features; fundamentally misaligned with SemPKM's use case
- **SPARQL Playground (AtomGraph)** — client-side only against local RDF data, cannot query remote SPARQL endpoints at all
- **Custom build (CodeMirror 6 + vanilla JS)** — would require building syntax highlighting, autocomplete, result table rendering, export, error handling, persistence, and tabs from scratch; months of work for functionality Yasgui already provides
- **Iframe embed** — prevents deep JS integration needed for custom IRI rendering; cookie auth complexity across frame boundaries
- **Sidecar container** — Yasgui is a client-side JS library, not a server application; running it in a separate container is unnecessary and adds networking complexity
- **npm build step** — violates SemPKM's architectural principle of no build step; would require adding webpack/vite/esbuild to the stack
- **`@triply/yasgui` fork** — bundles proprietary result visualization plugins not available outside TriplyDB; not suitable for self-hosted embedding

---

# Phase 21: SPARQL Interface Research

**Project:** SemPKM
**Researched:** 2026-02-27
**Overall Confidence:** HIGH (Yasgui ecosystem is well-documented and stable)

---

## Executive Summary / Recommendation

**Use `@zazuko/yasgui` via CDN, embedded directly into the existing SPARQL Console page as a component.** Do not iframe it, do not run it as a sidecar, and do not build a custom editor from scratch. Yasgui is the de facto standard SPARQL query UI, used by GraphDB, Apache Jena Fuseki, and dozens of triplestore products. The Zazuko fork is MIT-licensed, actively maintained (v4.5.0, mid-2025), and designed for exactly this use case.

For result rendering "pills" (clickable IRI links that navigate into SemPKM's object browser), use a custom YASR plugin. YASR's plugin architecture is designed for this. The built-in table plugin already renders URIs, but a custom plugin can transform them into SemPKM-aware links that open objects in the browser.

For saved queries, start with Yasgui's built-in localStorage persistence (tabs + query text auto-saved). In a later phase, add server-side saved queries stored as RDF in the triplestore (user-scoped, using a `sempkm:SavedQuery` type). Do not over-engineer saved queries in Phase 21.

---

## 1. Zazuko Yasgui: Current State

### Overview

Yasgui ("Yet Another SPARQL GUI") is a suite of three components:

| Component | Role | Based On |
|-----------|------|----------|
| **YASQE** | SPARQL query editor | CodeMirror 5 |
| **YASR** | SPARQL result visualizer | Plugin architecture |
| **Yasgui** | Orchestrator (tabs, persistence, config) | Binds YASQE + YASR |

### Fork Landscape

There are two active forks:

| Fork | NPM Package | License | Status |
|------|-------------|---------|--------|
| **Zazuko** (recommended) | `@zazuko/yasgui` | MIT | Active, v4.5.0, Aug 2025 |
| **TriplyDB** | `@triply/yasgui` | MIT core + proprietary plugins | Active, but some plugins are TriplyDB-only |

**Use Zazuko.** It is fully MIT-licensed (including all plugins), actively maintained, and used by Apache Jena Fuseki's UI. The TriplyDB fork bundles proprietary result visualization plugins that are only free via yasgui.triply.cc or TriplyDB -- not suitable for self-hosted embedding.

### Maintenance Evidence (HIGH confidence)

- NPM: `@zazuko/yasgui` v4.5.0 published mid-2025
- Apache Jena Fuseki UI depends on `@zazuko/yasqe` and `@zazuko/yasr` (bumped to 4.5.0 in March 2025)
- Sub-packages: `@zazuko/yasqe`, `@zazuko/yasr` available separately
- 12 dependencies in the main package
- MIT license confirmed

### CDN Availability

Yasgui can be loaded via CDN without any build step:

```html
<!-- CSS -->
<link rel="stylesheet" href="https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.min.css" />

<!-- JS -->
<script src="https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.min.js"></script>
```

This aligns perfectly with SemPKM's existing pattern of loading libraries from unpkg (htmx, Cytoscape, Split.js, Lucide, etc. -- see `base.html`).

### Can It Be Embedded as a Component?

**YES.** Yasgui is designed for embedding. Initialization is straightforward:

```javascript
const yasgui = new Yasgui(document.getElementById("yasgui-container"), {
  requestConfig: {
    endpoint: "/api/sparql",
    method: "POST",
    headers: () => ({
      "Content-Type": "application/x-www-form-urlencoded",
      "Accept": "application/sparql-results+json"
    })
  },
  copyEndpointOnNewTab: false
});
```

You can also use YASQE and YASR independently (without the tab orchestrator) for a more minimal integration:

```javascript
// Editor only
const yasqe = new Yasqe(document.getElementById("editor"), {
  requestConfig: { endpoint: "/api/sparql" }
});

// Results only
const yasr = new Yasr(document.getElementById("results"));

// Wire them together
yasqe.on("queryResponse", (instance, response) => {
  yasr.setResponse(response);
});
```

**Confidence:** HIGH -- this is the documented primary use case.

---

## 2. Alternative SPARQL UIs

### Comparison Matrix

| Feature | @zazuko/yasgui | @sib-swiss/sparql-editor | Comunica Web Client | SPARQL Playground (AtomGraph) | Custom (CodeMirror 6 + vanilla) |
|---------|---------------|-------------------------|--------------------|-----------------------------|-------------------------------|
| **Syntax highlighting** | Yes (CodeMirror 5) | Yes (Yasgui-based) | Basic | No | Yes (codemirror-lang-sparql) |
| **Autocomplete** | Prefixes, properties, classes | Context-aware (VoID metadata) | No | No | Must build |
| **Result visualization** | Table, raw, chart plugins | Yasgui-based | Streaming table | Basic table | Must build |
| **Plugin architecture** | YASR plugins | Extends Yasgui | N/A | N/A | N/A |
| **Tabs** | Built-in | No | No | No | Must build |
| **Persistence** | localStorage (auto) | No | No | No | Must build |
| **License** | MIT | MIT | MIT | MIT | N/A |
| **CDN-loadable** | Yes | Yes (web component) | No (npm only) | Yes (static HTML) | Partial |
| **Bundle size** | ~300-400KB | ~400KB+ (wraps Yasgui) | Heavy (~1MB+) | Tiny | Varies |
| **Active maintenance** | Yes (Zazuko + Jena) | Yes (SIB Swiss) | Yes | Low activity | N/A |
| **Queries remote endpoint** | Yes | Yes | Yes (federated) | No (local RDF only) | Must build |

### Detailed Assessment

#### @sib-swiss/sparql-editor

A web component (`<sparql-editor>`) that wraps Yasgui with enhanced autocomplete powered by VoID metadata. It queries the endpoint to discover available classes and properties, then provides context-aware autocomplete based on the subject's class at the cursor position.

**Pros:** Best autocomplete out of the box, web component API, easy embedding.
**Cons:** Adds a dependency layer on top of Yasgui. Requires VoID descriptions in the triplestore. SemPKM does not currently generate VoID metadata. More opinionated about endpoint configuration.

**Verdict:** Interesting for future enhancement, but adds unnecessary complexity for Phase 21. The VoID metadata requirement is a non-trivial prerequisite. Evaluate for a future "SPARQL Autocomplete" enhancement phase.

#### Comunica Web Client

A federated SPARQL query engine that runs in the browser. It can query multiple heterogeneous sources (SPARQL endpoints, TPF, RDF files, Solid pods).

**Pros:** Federated querying, client-side execution.
**Cons:** Completely different architecture than what SemPKM needs. Heavy bundle. No editor features (syntax highlighting, autocomplete). Designed for querying the open web of data, not a single endpoint.

**Verdict:** Not appropriate. SemPKM has a single RDF4J endpoint.

#### SPARQL Playground (AtomGraph)

Client-side-only SPARQL execution against user-provided RDF data. Does not query remote endpoints.

**Verdict:** Not appropriate. It does not connect to SPARQL endpoints at all.

#### Custom Build (CodeMirror 6 + vanilla JS)

Build from scratch using CodeMirror 6 with `codemirror-lang-sparql` (Lezer-based SPARQL grammar) plus custom result rendering.

**Pros:** Full control, modern CodeMirror 6, no legacy CodeMirror 5 dependency, smallest possible bundle, perfect integration with existing vanilla JS.
**Cons:** Enormous effort for marginal benefit. Would need to build: syntax highlighting config, autocomplete, result table rendering, result export, error handling, persistence, tabs. Yasgui already does all of this.

**Verdict:** Only consider if Yasgui is abandoned or its CodeMirror 5 dependency causes conflicts. Currently not justified.

#### Ontotext Yasgui Web Component

GraphDB's customized Yasgui, built with Stencil framework. Adds features specific to GraphDB (inference toggles, concurrent query execution, horizontal/vertical layout modes).

**Verdict:** Tied to GraphDB's ecosystem. Not appropriate for SemPKM.

### Recommendation

**@zazuko/yasgui is the clear winner.** It is the industry standard, MIT-licensed, CDN-loadable, well-documented, and actively maintained. Every other option either wraps Yasgui (adding complexity) or requires building features Yasgui already provides.

---

## 3. Integration Approach

### Options Evaluated

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A. Direct CDN embed** | Load Yasgui JS/CSS from CDN, init in template | Zero build step, consistent with existing stack | CDN dependency |
| **B. Vendor bundle** | Download Yasgui JS/CSS to `/frontend/static/` | No CDN dependency, offline works | Manual updates, larger repo |
| **C. Iframe embed** | Host Yasgui on separate page, iframe into SemPKM | Total isolation | Cookie/auth complexity, no deep integration |
| **D. Sidecar container** | Run standalone Yasgui in separate Docker container | Complete independence | Networking complexity, auth proxy needed, overkill |
| **E. npm build** | Add package.json, bundler, build step | Modern JS tooling | Violates SemPKM's no-build-step philosophy |

### Recommendation: Option A (Direct CDN embed), with Option B as fallback

**Use Option A (CDN).** This is consistent with how SemPKM loads every other library: htmx from unpkg, Cytoscape from unpkg, Split.js from unpkg, Lucide from unpkg, marked from jsdelivr, etc. (see `base.html` lines 19-46).

If CDN availability is a concern for self-hosted/air-gapped deployments, provide Option B (vendored files in `/frontend/static/vendor/yasgui/`) as a documented alternative.

**Do NOT use Options C, D, or E:**
- **Iframe (C):** Authentication is handled via `sempkm_session` cookie. Same-origin iframes would work, but lose the ability to deeply integrate results (clickable IRIs opening objects, pills, etc.). The iframe boundary prevents JS communication without postMessage complexity.
- **Sidecar (D):** Massive over-engineering. Yasgui is a client-side JS library, not a server application.
- **npm build (E):** SemPKM deliberately avoids build steps. Adding webpack/vite/esbuild contradicts the project's architectural principles.

### Integration Architecture

```
base.html
  |-- Yasgui CSS (CDN link tag, loaded only on SPARQL page)
  |-- Yasgui JS (CDN script tag, loaded only on SPARQL page)

templates/sparql/console.html  (replaces debug/sparql.html)
  |-- <div id="yasgui-container"></div>
  |-- <script> init Yasgui with config </script>

/api/sparql (existing endpoint, no changes needed)
  |-- POST with query= form body (SPARQL Protocol standard)
  |-- Returns application/sparql-results+json
```

The existing `/api/sparql` endpoint already supports both GET and POST per the SPARQL Protocol, with both form-encoded and JSON body formats. Yasgui speaks the SPARQL Protocol natively, so **no backend changes are needed**.

### Authentication Handling

SemPKM uses cookie-based auth (`sempkm_session` cookie). Since Yasgui will be served from the same origin (the nginx frontend), the browser will automatically include the session cookie in all fetch requests to `/api/sparql`. **No special auth configuration is needed.**

The one caveat: Yasgui's `requestConfig` is cached in localStorage. If a user logs out and another user logs in, the cached config persists. This is fine for SemPKM because:
1. Authentication is cookie-based (not header-based), so the cookie changes automatically on login.
2. The endpoint URL (`/api/sparql`) is the same for all users.
3. There is no user-specific header to leak.

---

## 4. Autocomplete Capabilities

### What Yasgui Provides Out of the Box

YASQE provides autocomplete for:
- **SPARQL keywords** -- SELECT, WHERE, FILTER, OPTIONAL, etc.
- **Prefixes** -- Common RDF prefixes (rdf:, rdfs:, owl:, etc.)
- **Properties** -- Queries the endpoint with `SELECT DISTINCT ?p WHERE { ?s ?p ?o } LIMIT 100` (configurable)
- **Classes** -- Queries the endpoint with `SELECT DISTINCT ?class WHERE { ?s a ?class } LIMIT 100` (configurable)

The property/class autocomplete sends background queries to the configured endpoint. Since SemPKM's `/api/sparql` automatically injects prefixes and scopes to the current graph, these autocomplete queries will work correctly -- they will return only properties and classes from the user's current knowledge base.

### Customizing Autocomplete

YASQE's autocomplete is configurable:

```javascript
Yasgui.Yasqe.defaults.autocompleters = ["prefixes", "properties", "classes"];
```

Custom autocomplete providers can be added. For SemPKM, a future enhancement could add:
- **Instance autocomplete** -- Suggest specific object IRIs when typing in triple patterns
- **Prefix-aware completion** -- Use SemPKM's `COMMON_PREFIXES` to provide the project's namespace prefixes

### SIB Swiss Approach (Future Enhancement)

The `@sib-swiss/sparql-editor` provides superior context-aware autocomplete using VoID metadata. It filters property suggestions based on the class of the subject variable. For example, if the cursor is after `?person a <Person> ; `, it only suggests properties used with Person instances.

This requires:
1. Generating VoID descriptions from the triplestore
2. Uploading them to a metadata graph
3. The editor queries this metadata at startup

**This is a Phase 21+ enhancement**, not Phase 21 scope. The built-in Yasgui autocomplete is sufficient for v1.

---

## 5. "Pills" / Inline Object Rendering

### What Yasgui Provides

YASR's built-in **Table plugin** renders results as an HTML table. URIs are displayed as clickable links. By default, clicking a URI opens it in a new tab (the raw URI). This is functional but not integrated with SemPKM's object browser.

### Custom YASR Plugin for SemPKM

YASR has a well-documented plugin architecture. A custom plugin can:

1. **Transform URIs into SemPKM links** -- Instead of linking to the raw IRI, link to `/browser/objects/{encoded_iri}` to open the object in SemPKM's browser.

2. **Render "pills"** -- Display IRIs as styled badges/pills with the object's label (resolved via the label service) instead of raw URIs.

3. **Inline object cards** -- Show a mini-card for each URI result with type icon + label.

The Sparnatural YASR plugins project provides a reference implementation:

- **TableX plugin** -- Extends YASR's table with `uriHrefAdapter` (transforms URIs to custom links) and `bindingSetAdapter` (processes entire result rows).
- **Label merging** -- For columns `?x` and `?x_label`, it merges them so the URI is hidden behind the label text.

### Recommended Approach

**Phase 21:** Use Yasgui's built-in table rendering, but add a lightweight custom result cell renderer that:
1. Detects URIs matching the SemPKM data namespace (`https://example.org/data/` or the configured `BASE_NAMESPACE`)
2. Renders them as clickable links pointing to `/browser/objects/{iri}`
3. Shortens display using `shortenIri()` (already implemented in `app.js`)

**Phase 21+:** Add a custom YASR plugin that:
1. Resolves labels for result URIs via a batch label endpoint
2. Renders pills with type-colored badges
3. Supports hovering to show a tooltip with the full IRI

### Implementation Sketch

```javascript
// Custom cell renderer for the table plugin
function sempkmCellRenderer(binding, prefixes) {
  if (binding.type === "uri") {
    const iri = binding.value;
    const label = shortenIri(iri);
    // Check if this is a SemPKM data IRI
    if (iri.startsWith(BASE_NAMESPACE)) {
      const encoded = encodeURIComponent(iri);
      return `<a href="/browser/objects/${encoded}" class="sparql-pill"
                title="${iri}" data-iri="${iri}">${label}</a>`;
    }
    return `<a href="${iri}" target="_blank" title="${iri}">${label}</a>`;
  }
  return escapeHtml(binding.value);
}
```

---

## 6. Saved Queries and Query History

### Yasgui's Built-in Persistence

Yasgui stores the following in localStorage:
- **Tab state** -- Each tab's query text, endpoint, and results
- **Query history** -- Auto-saved as the user types
- **Persistence expiry** -- Configurable, default 30 days
- **Persistence prefix** -- Configurable to avoid collisions with other Yasgui instances

Configuration:

```javascript
const yasgui = new Yasgui(container, {
  persistenceId: "sempkm-sparql",      // localStorage key prefix
  persistencyExpire: 30 * 24 * 60 * 60, // 30 days in seconds
});
```

### Server-Side Saved Queries (Future Enhancement)

For a PKM tool, users will want to save useful queries with names and descriptions, accessible across devices. The pattern used by GraphDB and TopBraid:

1. **Model saved queries as RDF** -- `sempkm:SavedQuery` type with properties:
   ```turtle
   ex:my-query a sempkm:SavedQuery ;
     rdfs:label "Find all unlinked notes" ;
     sempkm:queryText "SELECT ?note ?label WHERE { ... }" ;
     sempkm:owner <user-iri> ;
     dcterms:created "2026-02-27T12:00:00Z"^^xsd:dateTime ;
     dcterms:modified "2026-02-27T12:00:00Z"^^xsd:dateTime .
   ```

2. **Store in a named graph** -- `urn:sempkm:queries` or per-user graph

3. **API endpoints:**
   - `GET /api/sparql/saved` -- list user's saved queries
   - `POST /api/sparql/saved` -- save a new query
   - `DELETE /api/sparql/saved/{id}` -- delete a saved query

4. **UI integration** -- Dropdown/sidebar in the SPARQL console that lists saved queries. Click to load into the editor.

### Recommendation

**Phase 21:** Use Yasgui's built-in localStorage persistence. This gives tabs, auto-save, and query history for free with zero backend work.

**Phase 21+:** Add server-side saved queries via the RDF pattern described above. This is a natural extension but not critical for the initial SPARQL console upgrade.

---

## 7. Integration with Existing `/sparql` Endpoint

### Current State

SemPKM already has a fully functional SPARQL endpoint:

- **Route:** `GET /api/sparql?query=...` and `POST /api/sparql`
- **POST formats:** `application/x-www-form-urlencoded` (SPARQL Protocol standard) and `application/json`
- **Auth:** Cookie-based (`sempkm_session`), requires authenticated user
- **Features:** Auto prefix injection, auto graph scoping to `urn:sempkm:current`
- **Response:** `application/sparql-results+json` (SPARQL standard)

### Yasgui Compatibility

Yasgui speaks the SPARQL Protocol natively. It sends queries as `POST` with `application/x-www-form-urlencoded` body (`query=...`), which is exactly what SemPKM's endpoint already accepts. **No backend changes are needed.**

### Configuration

```javascript
const yasgui = new Yasgui(document.getElementById("yasgui-container"), {
  requestConfig: {
    endpoint: "/api/sparql",
    method: "POST"
  },
  // Don't show endpoint selector (single endpoint)
  endpointCatalogueSize: 0,
  // Don't copy endpoint to new tabs (always same endpoint)
  copyEndpointOnNewTab: false,
  // Persistence
  persistenceId: "sempkm-sparql"
});
```

### Prefix Handling

SemPKM's backend automatically injects common prefixes if not present in the query. Yasgui's editor also manages prefixes (autocomplete, prefix declarations). These are complementary -- the backend injection catches any prefixes the user forgot, while the editor provides a good authoring experience.

To pre-populate the editor with SemPKM's prefixes, set the default query:

```javascript
Yasgui.Yasqe.defaults.value = `PREFIX sempkm: <urn:sempkm:>
PREFIX schema: <https://schema.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o
}
LIMIT 20`;
```

### Graph Scoping Transparency

The auto-scoping to `urn:sempkm:current` via `FROM` injection is invisible to the user. This is correct behavior -- users should query their knowledge base without thinking about internal graph structure. For advanced users, the existing `all_graphs` parameter is available via the JSON POST format.

Consider adding a small UI toggle in the SPARQL console: "Query all graphs (debug)" that sends `all_graphs: true`. This would require a thin wrapper around Yasgui's request mechanism.

---

## 8. UI Layout Recommendation

### Current Layout

The existing SPARQL Console (`/sparql`) is a basic page under the `debug/` router:
- Plain `<textarea>` for query input
- "Run Query" and "Add Prefixes" buttons
- Results rendered as HTML table below
- Uses `app.js` for execution and rendering
- Owner-role-only access

### Proposed Layout

Replace the current debug SPARQL page with a proper Yasgui-powered console. Promote it from "Debug" to "Apps" in the sidebar (it is already listed under Apps).

```
+------------------------------------------------------------------+
|  SemPKM SPARQL Console                              [All Graphs] |
+------------------------------------------------------------------+
|  [Tab 1: Query] [Tab 2: Saved] [+]                              |
+------------------------------------------------------------------+
|                                                                  |
|  YASQE Editor Area                                               |
|  (syntax highlighting, line numbers, autocomplete)               |
|                                                                  |
|  PREFIX sempkm: <urn:sempkm:>                                    |
|  SELECT ?s ?label ?type                                          |
|  WHERE {                                                         |
|    ?s a ?type ;                                                  |
|       rdfs:label ?label .                                        |
|  }                                                               |
|  LIMIT 50                                                        |
|                                                        [Run >>]  |
+------------------------------------------------------------------+
|  YASR Results Area                                               |
|  [Table] [Raw Response] [Download]                               |
|                                                                  |
|  | ?s                  | ?label        | ?type              |    |
|  |---------------------|---------------|---------------------|   |
|  | [Note/my-note]      | My First Note | data:Note          |    |
|  | [Person/alice]      | Alice         | data:Person        |    |
|                                                                  |
|  50 results                                                      |
+------------------------------------------------------------------+
```

Where `[Note/my-note]` is a clickable pill that links to `/browser/objects/...`.

### Template Structure

```
templates/sparql/console.html  (new, replaces debug/sparql.html)
  extends base.html
  block head:
    - Yasgui CSS (CDN)
    - Yasgui JS (CDN)
  block content:
    - <div id="yasgui-container">
    - <script> initialization code </script>
  block scripts:
    - Custom YASR plugin registration
    - SemPKM-specific helpers
```

### Route Changes

```python
# Move from debug router to sparql router or a new UI router
@router.get("/sparql")
async def sparql_console(request: Request, user: User = Depends(get_current_user)):
    """Render the SPARQL query console. Any authenticated user."""
    # No longer owner-only -- SPARQL queries are read-only, safe for all users
    ...
```

This is a deliberate change: the SPARQL endpoint is already read-only and scoped to the current graph. There is no reason to restrict the console to owners.

---

## 9. Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **CodeMirror 5 conflict** -- Yasgui uses CM5, SemPKM might add CM6 later | Low | Low | CM5 and CM6 coexist fine (different global names). Only an issue if bundling. |
| **CDN unavailability** -- unpkg down = broken SPARQL console | Medium | Low | Vendor the files as fallback. Or use jsdelivr as secondary CDN. |
| **localStorage bloat** -- Yasgui stores results in localStorage | Low | Medium | Set `persistencyExpire` to a reasonable value (7-14 days). Monitor. |
| **Cached endpoint config** -- User changes BASE_NAMESPACE, Yasgui still points to old endpoint | Low | Low | Endpoint is always `/api/sparql` (relative URL), never changes. |
| **Auto-scoping confusion** -- User writes a GRAPH clause, auto-scoping does not kick in, results differ | Medium | Medium | Document behavior clearly. Add a help tooltip explaining auto-scoping. |
| **Large result sets** -- User runs `SELECT * WHERE { ?s ?p ?o }` without LIMIT | Medium | High | Already mitigated server-side (queries are scoped to current graph). Add a client-side warning for queries without LIMIT. |
| **Dark mode theming** -- Yasgui's default CSS may not match SemPKM's dark theme | Low | High | Override Yasgui CSS variables. CodeMirror themes are well-documented. This is styling work, not a blocker. |
| **Bundle size** -- Yasgui is ~300-400KB | Low | Certain | Acceptable. Loaded only on the SPARQL console page, not globally. Only slightly larger than Cytoscape (~300KB) which is already loaded globally. |

---

## 10. Implementation Plan

### Phase 21 Scope (Recommended)

1. **Replace debug SPARQL page with Yasgui-powered console**
   - Load `@zazuko/yasgui` CSS + JS from CDN in the template
   - Initialize with `/api/sparql` endpoint
   - Pre-populate with SemPKM prefixes as default query
   - Configure persistence with `sempkm-sparql` prefix

2. **Custom result cell rendering**
   - Override YASR's table cell renderer to detect SemPKM data IRIs
   - Render data IRIs as links to `/browser/objects/{iri}`
   - Use `shortenIri()` for display text

3. **Dark mode CSS overrides**
   - Add Yasgui theme overrides to `theme.css` for `[data-theme="dark"]`
   - CodeMirror 5 has well-documented theme CSS

4. **Promote from debug to standard page**
   - Move route from debug router to sparql router
   - Change access from owner-only to any authenticated user
   - SPARQL Console already appears under "Apps" in sidebar

5. **Remove old SPARQL page**
   - Delete `debug/sparql.html` template
   - Delete `runSparqlQuery()` / `renderSparqlResults()` from `app.js` (or leave for backward compat)

### Phase 21+ (Future Enhancements)

- Server-side saved queries (RDF-stored, user-scoped)
- Batch label resolution for result URIs (pill rendering with labels)
- "All graphs" toggle in the UI
- Context-aware autocomplete (VoID metadata or custom endpoint)
- Export results to CSV/JSON from the UI
- Query templates / snippets panel
- Integration with keyboard shortcuts (Ctrl+Enter to run)

---

## 11. Dependencies Summary

### New Dependencies (Phase 21)

| Dependency | Version | Source | Size | Purpose |
|------------|---------|--------|------|---------|
| `@zazuko/yasgui` | 4.5.0 | unpkg CDN | ~350KB JS + ~50KB CSS | SPARQL query editor + result viewer |

### No Backend Dependencies

The existing `/api/sparql` endpoint requires zero changes. Yasgui is a pure frontend integration.

### No Build Step

Loaded via `<script>` and `<link>` tags, consistent with all other SemPKM dependencies.

---

## Sources

### Primary (HIGH confidence)
- [Zazuko Yasgui GitHub](https://github.com/zazuko/Yasgui) -- source repository, MIT license
- [Yasgui API Reference (Triply docs)](https://docs.triply.cc/yasgui-api/) -- requestConfig, persistence, plugin APIs
- [Apache Jena using @zazuko/yasqe](https://www.mail-archive.com/commits@jena.apache.org/msg23567.html) -- evidence of active use

### Secondary (MEDIUM confidence)
- [SIB Swiss SPARQL Editor](https://github.com/sib-swiss/sparql-editor) -- web component wrapper with VoID autocomplete
- [Sparnatural YASR Plugins](https://github.com/sparna-git/Sparnatural-yasgui-plugins) -- custom table rendering reference
- [Ontotext Yasgui Web Component](https://www.npmjs.com/package/ontotext-yasgui-web-component) -- GraphDB's Yasgui fork
- [Comunica Web Client](https://query.linkeddatafragments.org/) -- federated query client (not recommended)

### Codebase Context
- `/home/james/Code/SemPKM/backend/app/sparql/router.py` -- existing SPARQL endpoint
- `/home/james/Code/SemPKM/backend/app/sparql/client.py` -- prefix injection, graph scoping
- `/home/james/Code/SemPKM/backend/app/templates/debug/sparql.html` -- current SPARQL UI (to be replaced)
- `/home/james/Code/SemPKM/frontend/static/js/app.js` -- current query runner code
- `/home/james/Code/SemPKM/backend/app/templates/base.html` -- CDN loading pattern reference
- `/home/james/Code/SemPKM/backend/app/templates/components/_sidebar.html` -- sidebar with SPARQL Console link

---

## v2.2 Handoff

**Target:** v2.2 Data Discovery milestone (SPARQL-01, SPARQL-02, SPARQL-03)

### Prerequisites Before Implementation

1. **No backend changes required** — the existing `/api/sparql` endpoint (POST, `application/x-www-form-urlencoded`, `application/sparql-results+json`) is already Yasgui-compatible with zero modifications needed

2. **CDN availability** — Yasgui is loaded from unpkg (`https://unpkg.com/@zazuko/yasgui@4.5.0/`); for air-gapped deployments, vendor the files to `frontend/static/vendor/yasgui/` as a documented alternative

3. **Confirm `BASE_NAMESPACE`** — the custom YASR cell renderer uses `BASE_NAMESPACE` to detect SemPKM data IRIs; confirm the exact value from the application config before implementing the renderer

### First Steps

1. Create `backend/app/templates/sparql/console.html` — extends `base.html`; loads Yasgui CSS/JS from unpkg CDN in `{% block head %}`; contains `<div id="yasgui-container"></div>` and initialization script (see Section 7 and Section 8 for config and template structure)

2. Add SPARQL console route — move from `debug/` router to a `sparql/` router (or equivalent); change access from owner-only to any authenticated user (SPARQL queries are read-only and scoped to current graph)

3. Configure Yasgui initialization with: `endpoint: "/api/sparql"`, `method: "POST"`, `persistenceId: "sempkm-sparql"`, `copyEndpointOnNewTab: false`, `endpointCatalogueSize: 0`; pre-populate default query with SemPKM prefixes (see Section 7, Prefix Handling)

4. Implement custom YASR table cell renderer — override the default URI rendering to detect `BASE_NAMESPACE` IRIs and render them as `<a href="/browser/objects/{encodedIri}" class="sparql-pill">` links; use `shortenIri()` from `app.js` for display text (satisfies SPARQL-02)

5. Add dark mode CSS overrides for Yasgui — add `[data-theme="dark"] .yasgui` overrides to `theme.css`; CodeMirror 5 (used internally by Yasgui) has well-documented theme CSS variables

6. Requirements satisfied: SPARQL-01 (SPARQL query execution), SPARQL-02 (IRI links), SPARQL-03 (localStorage query history via Yasgui built-in)

### Phase 21+ Enhancements (Deferred)

- Server-side saved queries as RDF (`sempkm:SavedQuery` type, `urn:sempkm:queries` named graph) — see Section 6 for data model
- Batch label resolution for result URIs (pill rendering with object labels, not just shortened IRIs)
- "Query all graphs" debug toggle via `all_graphs` JSON POST parameter
- Context-aware autocomplete using `@sib-swiss/sparql-editor` VoID metadata (requires SemPKM to generate VoID descriptions)
